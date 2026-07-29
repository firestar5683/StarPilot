import time
from dataclasses import dataclass
from enum import IntEnum, IntFlag
from opendbc.car import CanData, get_safety_config, structs, uds
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai import hyundaicanfd
from opendbc.car.hyundai.values import HyundaiFlags, CAR, CarControllerParams, \
                                                   CANFD_UNSUPPORTED_LONGITUDINAL_CAR, \
                                                   CANFD_SECURITYACCESS_CAR, \
                                                   CANFD_ANGLE_LONGITUDINAL_CAR, \
                                                   CANFD_RADAR_LIVE_LONGITUDINAL_CAR, \
                                                   RADAR_LIVE_LONGITUDINAL_CAR, \
                                                   UNSUPPORTED_LONGITUDINAL_CAR, HyundaiSafetyFlags, \
                                                   LEGACY_LONGITUDINAL_CAR, \
                                                   HyundaiStarPilotSafetyFlags, \
                                                   hyundai_cancel_button_enables_cruise, \
                                                   kia_ev6_gt_line_longitudinal_tuning
from opendbc.car.hyundai.radar_interface import get_radar_track_config, radar_tracks_available
from opendbc.car.hyundai.ev9_longitudinal import EV9_START_ACCEL, EV9_STARTING_SPEED
from opendbc.car.interfaces import CarInterfaceBase, ACCEL_MIN
from opendbc.car.disable_ecu import disable_ecu, ecu_log
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.radar_interface import RadarInterface

ButtonType = structs.CarState.ButtonEvent.Type
Ecu = structs.CarParams.Ecu

# Cancel button can sometimes be ACC pause/resume button, main button can also enable on some cars
ENABLE_BUTTONS = (ButtonType.accelCruise, ButtonType.decelCruise, ButtonType.cancel, ButtonType.mainCruise)

# Track when ECU disable happened - used to permanently suppress CAN errors from disabled ECU
ECU_DISABLE_TIMESTAMP = 0.0
EV9_EARLY_SUPPRESSION_ACTIVE = False
KONA_NON_SCC_FCA_RADAR_ADDR = 0x602
EV9_PANDA_PREINIT_STATUS_VERSION = 4
EV9_COMMUNICATION_CONTROL_REQUEST = b"\x28\x01\x01"
EV9_COMMUNICATION_CONTROL_RESTORE = b"\x28\x00\x01"
EV9_PRODUCTION_SAFETY_PARAM = 0x495
EV9_OPTIONAL_SAFETY_PARAM = 0x800


class EV9PandaPreinitState(IntEnum):
  COLLECTING = 0
  WAIT_SESSION = 1
  WAIT_COMM_CONTROL = 2
  WAIT_SUPPRESSION = 3
  ACTIVE = 4
  HANDOFF = 5
  ABORTED = 6
  RESTORING = 7
  READY_PENDING_RESPONSE = 8


class EV9PandaPreinitFlags(IntFlag):
  IDENTITY_VALID = 0x01
  START_INTENT = 0x02
  SUPPRESSION_CONFIRMED = 0x04
  BRIDGE_ACTIVE = 0x08
  HOST_HANDOFF = 0x10
  DEADLINE_MISSED = 0x20
  RESTORE_SENT = 0x40
  INTERNAL_TX_REJECTED = 0x80


class EV9PandaPreinitOwner(IntEnum):
  NONE = 0
  PANDA_PENDING = 1
  PANDA = 2
  HOST = 3
  FAILED = 4


@dataclass(frozen=True)
class EV9PandaPreinitHandoff:
  owner: EV9PandaPreinitOwner = EV9PandaPreinitOwner.NONE
  state: int = -1
  flags: EV9PandaPreinitFlags = EV9PandaPreinitFlags(0)
  resident: bool = False
  sample_valid: bool = False
  reason: str = "no live Panda preinit status"

  @property
  def knockout_owned(self) -> bool:
    """A live Panda/host transaction must never be duplicated from card."""
    return self.owner in (EV9PandaPreinitOwner.PANDA_PENDING, EV9PandaPreinitOwner.PANDA,
                          EV9PandaPreinitOwner.HOST)

  @property
  def adoptable(self) -> bool:
    return self.owner in (EV9PandaPreinitOwner.PANDA, EV9PandaPreinitOwner.HOST)

  @property
  def host_uds_veto(self) -> bool:
    """Resident firmware may still own 0x730 even without adoptable proof."""
    return self.resident or self.knockout_owned


EV9_PANDA_PREINIT_HANDOFF = EV9PandaPreinitHandoff()


def _ev9_preinit_statuses(panda_states) -> list:
  statuses = []
  for panda_state in panda_states or ():
    status = getattr(panda_state, "ev9LongPreinitStatus", None)
    # A resident marker survives a failed USB status read. Treat a valid status
    # as resident too for compatibility with logs produced before that marker.
    if status is not None and (bool(getattr(status, "resident", False)) or
                               bool(getattr(status, "valid", False))):
      statuses.append(status)
  return statuses


def update_ev9_panda_preinit_handoff(panda_states) -> EV9PandaPreinitHandoff:
  """Consume the current, non-persistent PandaState ownership proof.

  The firmware-selection Param is deliberately not evidence of a successful
  knockout. Only the live versioned status can transfer ownership to card.
  """
  global EV9_PANDA_PREINIT_HANDOFF
  statuses = _ev9_preinit_statuses(panda_states)
  if len(statuses) == 0:
    EV9_PANDA_PREINIT_HANDOFF = EV9PandaPreinitHandoff()
    return EV9_PANDA_PREINIT_HANDOFF
  if len(statuses) != 1:
    EV9_PANDA_PREINIT_HANDOFF = EV9PandaPreinitHandoff(
      owner=EV9PandaPreinitOwner.FAILED, resident=True,
      reason="ambiguous resident status from multiple Pandas",
    )
    return EV9_PANDA_PREINIT_HANDOFF

  status = statuses[0]
  resident = bool(getattr(status, "resident", False)) or bool(getattr(status, "valid", False))
  sample_valid = bool(getattr(status, "valid", False))
  if not sample_valid:
    EV9_PANDA_PREINIT_HANDOFF = EV9PandaPreinitHandoff(
      owner=EV9PandaPreinitOwner.FAILED, resident=resident,
      reason="resident Panda preinit status read was invalid",
    )
    return EV9_PANDA_PREINIT_HANDOFF

  version = int(getattr(status, "version", -1))
  state_value = int(getattr(status, "state", -1))
  flags = EV9PandaPreinitFlags(int(getattr(status, "flags", 0)))
  communication_type = int(getattr(status, "communicationType", -1))
  timing_valid = bool(getattr(status, "timingValid", False))
  try:
    state = EV9PandaPreinitState(state_value)
  except ValueError:
    state = None
  if version != EV9_PANDA_PREINIT_STATUS_VERSION:
    owner, reason = EV9PandaPreinitOwner.FAILED, f"unsupported status version {version}"
  elif communication_type != 0x01:
    owner, reason = EV9PandaPreinitOwner.FAILED, f"unexpected communication type 0x{communication_type:02x}"
  elif not timing_valid:
    # The main status and the extended timing block are separate USB control
    # reads. Keep the resident UDS veto but withhold adoptable ownership until
    # both came from one coherent publication.
    owner, reason = EV9PandaPreinitOwner.PANDA_PENDING, "Panda timing proof is temporarily unavailable"
  elif state == EV9PandaPreinitState.RESTORING:
    # Timeout restoration legitimately carries DEADLINE_MISSED. It still owns
    # the diagnostic transaction until restore converges and therefore vetoes
    # every host request, but it is never adoptable as a successful knockout.
    owner, reason = EV9PandaPreinitOwner.PANDA_PENDING, "Panda is restoring ECU communication"
  elif flags & (EV9PandaPreinitFlags.DEADLINE_MISSED | EV9PandaPreinitFlags.INTERNAL_TX_REJECTED):
    owner, reason = EV9PandaPreinitOwner.FAILED, "Panda missed a bridge deadline or rejected an internal TX"
  else:
    clean_common = bool(flags & EV9PandaPreinitFlags.IDENTITY_VALID) and \
      bool(flags & EV9PandaPreinitFlags.SUPPRESSION_CONFIRMED)
    if state == EV9PandaPreinitState.ACTIVE and clean_common and flags & EV9PandaPreinitFlags.BRIDGE_ACTIVE:
      owner, reason = EV9PandaPreinitOwner.PANDA, "Panda owns confirmed suppression and bridge"
    elif state == EV9PandaPreinitState.HANDOFF and clean_common and \
        flags & EV9PandaPreinitFlags.BRIDGE_ACTIVE and flags & EV9PandaPreinitFlags.HOST_HANDOFF:
      owner, reason = EV9PandaPreinitOwner.HOST, "host handoff already confirmed"
    elif state == EV9PandaPreinitState.ABORTED:
      owner, reason = EV9PandaPreinitOwner.FAILED, "Panda preinit ended in ABORTED"
    elif state in (EV9PandaPreinitState.COLLECTING, EV9PandaPreinitState.WAIT_SESSION,
                   EV9PandaPreinitState.WAIT_COMM_CONTROL, EV9PandaPreinitState.WAIT_SUPPRESSION,
                   EV9PandaPreinitState.READY_PENDING_RESPONSE):
      owner, reason = EV9PandaPreinitOwner.PANDA_PENDING, f"Panda transaction is still {state.name}"
    else:
      owner, reason = EV9PandaPreinitOwner.FAILED, "inconsistent Panda preinit ownership proof"

  EV9_PANDA_PREINIT_HANDOFF = EV9PandaPreinitHandoff(
    owner=owner, state=state_value, flags=flags, resident=resident, sample_valid=True, reason=reason,
  )
  return EV9_PANDA_PREINIT_HANDOFF


def invalidate_ev9_panda_preinit_handoff(reason: str) -> EV9PandaPreinitHandoff:
  """Conservatively retain transaction ownership when fresh proof is unavailable."""
  global EV9_PANDA_PREINIT_HANDOFF
  EV9_PANDA_PREINIT_HANDOFF = EV9PandaPreinitHandoff(
    owner=EV9PandaPreinitOwner.PANDA_PENDING,
    resident=EV9_PANDA_PREINIT_HANDOFF.resident,
    reason=reason,
  )
  return EV9_PANDA_PREINIT_HANDOFF


def ev9_panda_preinit_baselines(messages: list) -> list:
  """Normalize Panda-returned bus numbers, including physical-only observations."""
  return [CanData(msg.address, msg.dat, msg.src - 0x80 if 0x80 <= msg.src < 0xC0 else msg.src) for msg in messages]


def apply_platform_longitudinal_params(ret: structs.CarParams) -> None:
  if not (ret.flags & HyundaiFlags.CANFD):
    return

  ret.startingState = True
  ret.startAccel = 1.0
  ret.longitudinalActuatorDelay = 0.5
  ret.vEgoStopping = 0.3
  ret.vEgoStarting = 0.1
  ret.stoppingDecelRate = 0.4


def apply_kia_ev6_gt_line_longitudinal_params(ret: structs.CarParams) -> None:
  ret.startAccel = 1.4
  ret.longitudinalActuatorDelay = 0.35
  ret.vEgoStarting = 0.5


def apply_kia_ev9_longitudinal_params(ret: structs.CarParams) -> None:
  """Use a comfort-biased EV9 launch target while retaining family limits."""
  ret.startAccel = EV9_START_ACCEL
  ret.vEgoStarting = EV9_STARTING_SPEED


def apply_ecu_disable_failure_fallback(CP: structs.CarParams, params) -> None:
  params.put_bool("EcuDisableFailed", True)
  CP.safetyConfigs[-1].safetyParam &= ~HyundaiSafetyFlags.LONG.value
  if CP.safetyConfigs[-1].safetyModel == structs.CarParams.SafetyModel.hyundaiCanfdEv9:
    CP.safetyConfigs[-1].safetyModel = structs.CarParams.SafetyModel.hyundaiCanfd
  CP.openpilotLongitudinalControl = False
  CP.pcmCruise = True


def detect_kona_non_scc_radar_fca(candidate, fingerprint, car_fw) -> bool:
  if candidate != CAR.HYUNDAI_KONA_NON_SCC:
    return False

  if any(fw.ecu == Ecu.fwdRadar for fw in car_fw):
    return True

  # Some non-SCC Kona trims have FCA radar tracks without SCC. Use PT FCA11
  # status on those cars; camera-bus FCA11 is not continuously published.
  return KONA_NON_SCC_FCA_RADAR_ADDR in fingerprint[1]


def ev9_panda_preinit_armed(params) -> bool:
  """Return the explicit production gate shared by pandad, card, and the interface."""
  try:
    return (params.get_bool("EV9LongPreinitPanda") and
            params.get_bool("OpenpilotEnabledToggle") and
            params.get_bool("AlphaLongitudinalEnabled"))
  except Exception:
    return False


def ev9_cached_safety_profile_supported(cached_params) -> bool:
  """Validate the persisted host profile before any pre-fingerprint UDS TX."""
  try:
    config = cached_params.safetyConfigs[-1]
    required_flags = (HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_LKA_STEERING |
                      HyundaiFlags.CANFD_LKA_STEERING_ALT | HyundaiFlags.CANFD_ANGLE_STEERING)
    return (config.safetyModel == structs.CarParams.SafetyModel.hyundaiCanfdEv9 and
            (int(config.safetyParam) & ~EV9_OPTIONAL_SAFETY_PARAM) == EV9_PRODUCTION_SAFETY_PARAM and
            (int(cached_params.flags) & int(required_flags)) == int(required_flags))
  except (AttributeError, IndexError, TypeError):
    return False


def attempt_ev9_pre_fingerprint_suppression(cached_params, params, can_recv=None, can_send=None,
                                            initial_can_messages: list | None = None) -> bool:
  """Adopt Panda ownership or attempt the legacy host knockout before fingerprinting.

  This is deliberately narrower than normal fingerprinting: it requires a
  verified cached EV9 identity, cached ADAS firmware at 0x730, and the exact
  production safety profile. When Panda preinit is armed, a live
  versioned PandaState is the only acceptable ownership proof; card never races
  an in-flight or failed firmware transaction with a duplicate UDS request.
  """
  global EV9_EARLY_SUPPRESSION_ACTIVE
  EV9_EARLY_SUPPRESSION_ACTIVE = False
  hyundaicanfd.set_ev9_adrv_baselines([])
  if cached_params is None or str(cached_params.carFingerprint) != str(CAR.KIA_EV9) or cached_params.brand != "hyundai":
    return False
  if not params.get_bool("AlphaLongitudinalEnabled") or not cached_params.openpilotLongitudinalControl or cached_params.pcmCruise:
    return False
  if not ev9_cached_safety_profile_supported(cached_params):
    return False

  has_adas_fw = any(fw.ecu == Ecu.adas and fw.address == 0x730 for fw in cached_params.carFw)
  if not has_adas_fw:
    return False

  observed_can_messages = list(initial_can_messages or [])

  handoff = EV9_PANDA_PREINIT_HANDOFF
  if params.get_bool("EV9LongPreinitPanda") or handoff.host_uds_veto:
    if ev9_panda_preinit_armed(params) and handoff.adoptable:
      EV9_EARLY_SUPPRESSION_ACTIVE = True
      hyundaicanfd.set_ev9_adrv_baselines(ev9_panda_preinit_baselines(observed_can_messages))
      ecu_log(f"=== EV9 PANDA PREINIT HANDOFF accepted: {handoff.reason} ===")
      return True

    # The persistent arm Param selects firmware; it is never proof that this
    # boot actually suppressed the ECU. Likewise, live Panda ownership vetoes
    # a duplicate host request even if the persistent arm was just cleared.
    ecu_log(f"=== EV9 PANDA PREINIT HANDOFF rejected: {handoff.reason} ===")
    return False

  def observing_can_recv(wait_for_one=False):
    packets = can_recv(wait_for_one=wait_for_one)
    for packet in packets:
      observed_can_messages.extend(packet)
    return packets

  ecu_log("=== EV9 PRE-FINGERPRINT SUPPRESSION ATTEMPT ===")
  observed_recv = observing_can_recv if can_recv is not None else can_recv
  EV9_EARLY_SUPPRESSION_ACTIVE = disable_ecu(
    observed_recv, can_send, bus=CanBus(cached_params).ECAN, addr=0x730,
    com_cont_req=EV9_COMMUNICATION_CONTROL_REQUEST, session_delay=0.0,
  )
  if EV9_EARLY_SUPPRESSION_ACTIVE:
    normalized_messages = ev9_panda_preinit_baselines(observed_can_messages)
    hyundaicanfd.set_ev9_adrv_baselines(normalized_messages)
    baseline_addresses = {0x160, 0x161, 0x162, 0x1A0, 0x1BA, 0x1DA, 0x1E0, 0x1E5, 0x1EA, 0x200, 0x345, 0x38C, 0x57A}
    observed_addresses = sorted({msg.address for msg in normalized_messages if msg.src == 1 and msg.address in baseline_addresses})
    ecu_log(f"=== EV9 READY BASELINES captured={[hex(address) for address in observed_addresses]} ===")
  else:
    hyundaicanfd.set_ev9_adrv_baselines([])
  ecu_log(f"=== EV9 PRE-FINGERPRINT SUPPRESSION result={EV9_EARLY_SUPPRESSION_ACTIVE} ===")
  return EV9_EARLY_SUPPRESSION_ACTIVE


class CarInterface(CarInterfaceBase):
  CarState = CarState
  CarController = CarController
  RadarInterface = RadarInterface

  @staticmethod
  def get_pid_accel_limits(CP, current_speed, cruise_speed):
    return ACCEL_MIN, CarControllerParams.ACCEL_MAX

  @staticmethod
  def apply_post_fingerprint_params(CP: structs.CarParams, candidate, fingerprint, car_fw) -> None:
    if kia_ev6_gt_line_longitudinal_tuning(CP.carFingerprint, CP.carVin):
      apply_kia_ev6_gt_line_longitudinal_params(CP)

  @staticmethod
  def _get_params(ret: structs.CarParams, candidate, fingerprint, car_fw, alpha_long, is_release, docs) -> structs.CarParams:
    ret.brand = "hyundai"

    # "LKA steering" if LKAS or LKAS_ALT messages are seen coming from the camera.
    # Generally means our LKAS message is forwarded to another ECU (commonly ADAS ECU)
    # that finally retransmits our steering command in LFA or LFA_ALT to the MDPS.
    # "LFA steering" if camera directly sends LFA to the MDPS
    cam_can = CanBus(None, fingerprint).CAM
    lka_steering = 0x50 in fingerprint[cam_can] or 0x110 in fingerprint[cam_can]
    CAN = CanBus(None, fingerprint, lka_steering)

    if ret.flags & HyundaiFlags.CANFD:
      # Shared configuration for CAN-FD cars
      ret.alphaLongitudinalAvailable = candidate not in CANFD_UNSUPPORTED_LONGITUDINAL_CAR or candidate == CAR.KIA_EV9
      if lka_steering and Ecu.adas not in [fw.ecu for fw in car_fw] and candidate not in CANFD_SECURITYACCESS_CAR and \
          candidate != CAR.KIA_EV9:
        # this needs to be figured out for cars without an ADAS ECU
        # Cars in CANFD_SECURITYACCESS_CAR are known to have ADAS ECUs that work with SecurityAccess
        ret.alphaLongitudinalAvailable = False
      if lka_steering and ret.flags & HyundaiFlags.CANFD_ANGLE_STEERING and candidate not in CANFD_ANGLE_LONGITUDINAL_CAR and \
          candidate != CAR.KIA_EV9:
        # Most angle-steering LKA platforms still need stock longitudinal validation.
        ret.alphaLongitudinalAvailable = False

      # EV9 production suppression can remove ADAS-originated 0x1BA before
      # live fingerprinting. The platform is known to have BSM and its parser
      # keeps accepting the reconstructed status message.
      ret.enableBsm = 0x1ba in fingerprint[CAN.ECAN] or candidate == CAR.KIA_EV9

      # Check if the car is hybrid. Only HEV/PHEV cars have 0xFA on E-CAN.
      if 0xFA in fingerprint[CAN.ECAN]:
        ret.flags |= HyundaiFlags.HYBRID.value

      if lka_steering:
        # detect LKA steering
        ret.flags |= HyundaiFlags.CANFD_LKA_STEERING.value
        if 0x110 in fingerprint[CAN.CAM]:
          ret.flags |= HyundaiFlags.CANFD_LKA_STEERING_ALT.value
      else:
        # no LKA steering
        if 0x1cf not in fingerprint[CAN.ECAN]:
          ret.flags |= HyundaiFlags.CANFD_ALT_BUTTONS.value
        if not ret.flags & HyundaiFlags.RADAR_SCC:
          ret.flags |= HyundaiFlags.CANFD_CAMERA_SCC.value
        if 0xCB in fingerprint[CAN.CAM]:
          ret.flags |= HyundaiFlags.SEND_LFA.value

      # Some LKA steering cars have alternative messages for gear checks
      # ICE cars do not have 0x130; GEARS message on 0x40 or 0x70 instead
      if 0x130 not in fingerprint[CAN.ECAN]:
        if 0x40 not in fingerprint[CAN.ECAN]:
          ret.flags |= HyundaiFlags.CANFD_ALT_GEARS_2.value
        else:
          ret.flags |= HyundaiFlags.CANFD_ALT_GEARS.value

      cfgs = [get_safety_config(structs.CarParams.SafetyModel.hyundaiCanfd), ]
      if CAN.ECAN >= 4:
        cfgs.insert(0, get_safety_config(structs.CarParams.SafetyModel.noOutput))
      ret.safetyConfigs = cfgs

      if ret.flags & HyundaiFlags.CANFD_LKA_STEERING:
        ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.CANFD_LKA_STEERING.value
        if ret.flags & HyundaiFlags.CANFD_LKA_STEERING_ALT:
          ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.CANFD_LKA_STEERING_ALT.value
      if ret.flags & HyundaiFlags.CANFD_ALT_BUTTONS:
        ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.CANFD_ALT_BUTTONS.value
      if ret.flags & HyundaiFlags.CANFD_CAMERA_SCC:
        ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.CAMERA_SCC.value
      if ret.flags & HyundaiFlags.CANFD_ANGLE_STEERING:
        ret.steerControlType = structs.CarParams.SteerControlType.angle
        ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.CANFD_ANGLE_STEERING.value
        if candidate == CAR.KIA_EV9:
          ret.steerAtStandstill = True
      if ret.flags & HyundaiFlags.CCNC and not ret.flags & HyundaiFlags.CANFD_LKA_STEERING:
        ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.CCNC.value

    else:
      # Shared configuration for non CAN-FD cars
      ret.alphaLongitudinalAvailable = candidate not in UNSUPPORTED_LONGITUDINAL_CAR or candidate in LEGACY_LONGITUDINAL_CAR
      ret.enableBsm = 0x58b in fingerprint[CAN.ECAN]

      # Send LFA message on cars with HDA
      if 0x485 in fingerprint[CAN.CAM]:
        ret.flags |= HyundaiFlags.SEND_LFA.value

      # These cars use the FCA11 message for the AEB and FCW signals, all others use SCC12
      if 0x38d in fingerprint[CAN.ECAN] or 0x38d in fingerprint[CAN.CAM]:
        ret.flags |= HyundaiFlags.USE_FCA.value
      if detect_kona_non_scc_radar_fca(candidate, fingerprint, car_fw):
        ret.flags |= HyundaiFlags.NON_SCC_RADAR_FCA.value

      if ret.flags & HyundaiFlags.LEGACY:
        # these cars require a special panda safety mode due to missing counters and checksums in the messages
        ret.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.hyundaiLegacy)]
      else:
        ret.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.hyundai, 0)]

      if ret.flags & HyundaiFlags.CAMERA_SCC:
        ret.safetyConfigs[0].safetyParam |= HyundaiSafetyFlags.CAMERA_SCC.value

      # These cars expose an LKAS/LFA steering-wheel button that StarPilot can customize.
      if 0x391 in fingerprint[0] or ret.flags & HyundaiFlags.CAN_CANFD_BLENDED:
        ret.safetyConfigs[-1].safetyParam |= HyundaiStarPilotSafetyFlags.HAS_LDA_BUTTON.value
      if ret.flags & HyundaiFlags.CAN_CANFD_BLENDED:
        ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.CAN_CANFD_BLENDED.value
      if hyundai_cancel_button_enables_cruise(candidate):
        ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.CANCEL_BTN_ENABLE.value

    # Common lateral control setup

    ret.centerToFront = ret.wheelbase * 0.4
    ret.steerActuatorDelay = 0.1
    ret.steerLimitTimer = 0.4
    if not (ret.flags & HyundaiFlags.CANFD_ANGLE_STEERING):
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    if ret.flags & HyundaiFlags.ALT_LIMITS:
      ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.ALT_LIMITS.value

    if ret.flags & HyundaiFlags.ALT_LIMITS_2:
      ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.ALT_LIMITS_2.value

      # see https://github.com/commaai/opendbc/pull/1137/
      ret.dashcamOnly = True

    if ret.flags & HyundaiFlags.NON_SCC:
      ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.NON_SCC.value

    # Common longitudinal control setup

    radar_config = get_radar_track_config(ret.carFingerprint, ret.flags)
    radar_available = radar_tracks_available(radar_config, fingerprint)
    ret.radarUnavailable = not radar_available
    if ret.flags & HyundaiFlags.NON_SCC:
      ret.alphaLongitudinalAvailable = False
    ret.openpilotLongitudinalControl = alpha_long and ret.alphaLongitudinalAvailable
    if ret.openpilotLongitudinalControl and not (candidate in RADAR_LIVE_LONGITUDINAL_CAR and radar_available):
      ret.radarUnavailable = True
    ret.pcmCruise = not ret.openpilotLongitudinalControl
    apply_platform_longitudinal_params(ret)

    if ret.openpilotLongitudinalControl:
      ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.LONG.value
    if ret.flags & HyundaiFlags.HYBRID:
      ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.HYBRID_GAS.value
    elif ret.flags & HyundaiFlags.EV:
      ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.EV_GAS.value
    elif ret.flags & HyundaiFlags.FCEV:
      ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.FCEV_GAS.value

    # The expanded reconstruction/diagnostic allowlist is exclusive to the
    # explicitly armed EV9 longitudinal profile. Lateral-only EV9 operation and
    # every other Hyundai retain the generic CAN-FD model.
    if candidate == CAR.KIA_EV9 and ret.openpilotLongitudinalControl:
      ret.safetyConfigs[-1].safetyModel = structs.CarParams.SafetyModel.hyundaiCanfdEv9

    # Car specific configuration overrides

    if candidate == CAR.GENESIS_G90:
      ret.stoppingDecelRate = 0.55
      ret.vEgoStopping = 0.8

    if candidate == CAR.HYUNDAI_PALISADE_2023:
      ret.startAccel = 1.3
      ret.stopAccel = -0.85
      ret.stoppingDecelRate = 0.35
      ret.vEgoStarting = 0.5
      ret.vEgoStopping = 0.35

    if candidate == CAR.HYUNDAI_IONIQ_6:
      ret.longitudinalActuatorDelay = 0.6

    if candidate == CAR.KIA_EV9 and ret.openpilotLongitudinalControl:
      apply_kia_ev9_longitudinal_params(ret)

    if candidate == CAR.KIA_NIRO_PHEV_2022:
      ret.stopAccel = -1.4
      ret.stoppingDecelRate = 0.5
      ret.vEgoStopping = 0.7

    if candidate == CAR.KIA_OPTIMA_G4_FL:
      ret.steerActuatorDelay = 0.2

    # Dashcam cars are missing a test route, or otherwise need validation
    # TODO: Optima Hybrid 2017 uses a different SCC12 checksum
    if candidate in (CAR.KIA_OPTIMA_H,):
      ret.dashcamOnly = True

    return ret

  @staticmethod
  def init(CP, can_recv, can_send, communication_control=None, params=None):
    global ECU_DISABLE_TIMESTAMP, EV9_EARLY_SUPPRESSION_ACTIVE
    normal_init = communication_control is None
    if params is None:
      from openpilot.common.params import Params
      params = Params()
    ev9_long = CP.carFingerprint == CAR.KIA_EV9 and CP.openpilotLongitudinalControl
    ev9_preinit_requested = ev9_long and params.get_bool("EV9LongPreinitPanda")
    ev9_preinit_armed = ev9_long and ev9_panda_preinit_armed(params)

    if communication_control is None:
      if CP.carFingerprint in CANFD_RADAR_LIVE_LONGITUDINAL_CAR or ev9_long:
        # Don't use 0x80 suppress bit so we can read the ECU response.
        # Keep ADAS reception enabled while blocking its normal output. This preserves the
        # inputs needed to study BSM, but does not itself preserve ADAS-originated BSM output.
        communication_control = bytes([uds.SERVICE_TYPE.COMMUNICATION_CONTROL, uds.CONTROL_TYPE.ENABLE_RX_DISABLE_TX, uds.MESSAGE_TYPE.NORMAL])
      else:
        # 0x80 silences response for other cars (original behavior)
        communication_control = bytes([uds.SERVICE_TYPE.COMMUNICATION_CONTROL, 0x80 | uds.CONTROL_TYPE.DISABLE_RX_DISABLE_TX, uds.MESSAGE_TYPE.NORMAL])

    if normal_init and ev9_long:
      # All successful EV9 routes used EnableRx/DisableTx for normal messages.
      # Keep the positive response unsuppressed so ownership is explicit.
      communication_control = EV9_COMMUNICATION_CONTROL_REQUEST

    init_log = f"=== init() called: opLong={CP.openpilotLongitudinalControl}, flags=0x{CP.flags:x}, "
    init_log += f"safetyParam={CP.safetyConfigs[-1].safetyParam} ==="
    ecu_log(init_log)

    if CP.openpilotLongitudinalControl and not (CP.flags & (HyundaiFlags.CANFD_CAMERA_SCC | HyundaiFlags.CAMERA_SCC)):
      addr, bus = 0x7d0, CanBus(CP).ECAN if CP.flags & (HyundaiFlags.CANFD | HyundaiFlags.CAN_CANFD_BLENDED) else 0
      if CP.flags & HyundaiFlags.CANFD_LKA_STEERING.value:
        addr, bus = 0x730, CanBus(CP).ECAN

      # A direct OFF -> READY start may have completed the exact same verified
      # request before fingerprinting. Prove the bus is live and stock SCC is
      # still absent before accepting that handoff.
      ecu_disabled = False
      resume_early_suppression = normal_init and CP.carFingerprint == CAR.KIA_EV9 and EV9_EARLY_SUPPRESSION_ACTIVE and \
        not ev9_preinit_requested and not EV9_PANDA_PREINIT_HANDOFF.host_uds_veto
      resume_panda_suppression = normal_init and ev9_preinit_armed and EV9_PANDA_PREINIT_HANDOFF.adoptable
      panda_transaction_owned = normal_init and EV9_PANDA_PREINIT_HANDOFF.host_uds_veto
      EV9_EARLY_SUPPRESSION_ACTIVE = False
      if resume_early_suppression or resume_panda_suppression:
        # This flag can only be set by a positive 0x68 response in this same
        # card process, or by a live, versioned PandaState with confirmed
        # suppression and bridge ownership. Do not add a receive-only verifier
        # delay: reconstruction must be primed before the next missed deadline.
        ecu_disabled = True
        ecu_log(f"=== EV9 PRE-FINGERPRINT SUPPRESSION HANDOFF accepted: {EV9_PANDA_PREINIT_HANDOFF.reason} ===")
      elif normal_init and (ev9_preinit_requested or panda_transaction_owned):
        # Any in-progress state still owns the diagnostic transaction, while a
        # missing/failed state is not proof of suppression. Both cases forbid a
        # duplicate host request and fall back to stock longitudinal control.
        apply_ecu_disable_failure_fallback(CP, params)
        ecu_log(f"=== EV9 PANDA PREINIT unavailable; no duplicate knockout: {EV9_PANDA_PREINIT_HANDOFF.reason} ===")
        return

      # Try ECU disable. If it succeeds (IGN-ON mode), enable longitudinal.
      # If it fails (READY mode returns NRC 0x22, or timeout), strip LONG safety flag
      # so panda forwards stock SCC messages normally (lateral-only mode).
      if not ecu_disabled:
        ecu_log(f"=== ECU DISABLE attempt: addr=0x{addr:x}, bus={bus} ===")
      if not ecu_disabled:
        ecu_disabled = disable_ecu(can_recv, can_send, bus=bus, addr=addr, com_cont_req=communication_control,
                                   reset=CP.carFingerprint != CAR.KIA_EV9 and bool(CP.flags & HyundaiFlags.CAN_CANFD_BLENDED))

      if ecu_disabled and ev9_long:
        active_log = "".join((
          f"=== EV9 PERSISTENT COMMUNICATION CONTROL ACTIVE - request={communication_control.hex()}; ",
          "controller Tester Present required ===",
        ))
        ecu_log(active_log)

      if CP.carFingerprint == CAR.HYUNDAI_IONIQ_6:
        # Ioniq 6: track success/failure to auto-switch between openpilot long and stock ACC
        if ecu_disabled:
          ECU_DISABLE_TIMESTAMP = time.monotonic()
          params.put_bool("EcuDisableFailed", False)
          params.put_bool("ExperimentalMode", True)
          ecu_log("=== ECU DISABLE SUCCESS - Longitudinal + Experimental ENABLED ===")
        else:
          apply_ecu_disable_failure_fallback(CP, params)
          ecu_log(f"=== ECU DISABLE FAILED - safetyParam stripped to {CP.safetyConfigs[-1].safetyParam}, lateral-only mode ===")
      else:
        if ecu_disabled:
          params.put_bool("EcuDisableFailed", False)
          ecu_log("=== ECU DISABLE SUCCESS ===")
        else:
          apply_ecu_disable_failure_fallback(CP, params)
          ecu_log(f"=== ECU DISABLE FAILED - safetyParam stripped to {CP.safetyConfigs[-1].safetyParam}, lateral-only mode ===")

    # for blinkers
    if CP.flags & HyundaiFlags.ENABLE_BLINKERS:
      disable_ecu(can_recv, can_send, bus=CanBus(CP).ECAN, addr=0x7B1, com_cont_req=communication_control)

  @staticmethod
  def deinit(CP, can_recv, can_send):
    if CP.carFingerprint == CAR.KIA_EV9 and EV9_PANDA_PREINIT_HANDOFF.host_uds_veto:
      ecu_log("=== EV9 resident Panda owns communication restore; skipping host 28 00 01 ===")
      return
    communication_control = EV9_COMMUNICATION_CONTROL_RESTORE if CP.carFingerprint == CAR.KIA_EV9 else \
      bytes([uds.SERVICE_TYPE.COMMUNICATION_CONTROL, 0x80 | uds.CONTROL_TYPE.ENABLE_RX_ENABLE_TX, uds.MESSAGE_TYPE.NORMAL])
    CarInterface.init(CP, can_recv, can_send, communication_control)

  def update(self, can_packets, starpilot_toggles):
    ret, fp_ret = super().update(can_packets, starpilot_toggles)

    global ECU_DISABLE_TIMESTAMP
    if self.CP.carFingerprint != CAR.KIA_EV9 and ECU_DISABLE_TIMESTAMP > 0 and not ret.canValid:
      # Check if any parser has counter/checksum errors (real CAN issues)
      has_counter_errors = False
      for cp in self.can_parsers.values():
        if cp is not None:
          for state in cp.message_states.values():
            if state.counter_fail >= 5:  # MAX_BAD_COUNTER from parser.py
              has_counter_errors = True
              ecu_log(f"REAL CAN ERROR: {state.name} counter_fail={state.counter_fail}")
              break
        if has_counter_errors:
          break

      if has_counter_errors:
        # Real CAN error - don't suppress, let it through
        ecu_log("ECU_DISABLE: NOT suppressing canValid - counter errors detected")
      else:
        # Only timeout errors (expected after ECU disable) - suppress silently
        ret.canValid = True

    return ret, fp_ret
