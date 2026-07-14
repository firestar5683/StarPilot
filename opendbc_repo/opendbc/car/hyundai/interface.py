import time
from opendbc.car import get_safety_config, structs, uds
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
from opendbc.car.hyundai.ev9_longitudinal import EV9_LONG_PROBE_HOLD_SECONDS, EV9_START_ACCEL, EV9_STARTING_SPEED, \
                                                       EV9LongitudinalProbeMode, \
                                                       EV9LongitudinalTestStage, ev9_communication_control_requests, \
                                                       get_ev9_longitudinal_test_config
from opendbc.car.interfaces import CarInterfaceBase, ACCEL_MIN
from opendbc.car.disable_ecu import disable_ecu, ecu_log, run_diagnostic_session_probe
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
EV9_LONG_DISABLE_VERIFY_ADDRS = (0x1A0,)
EV9_LONG_DISABLE_VERIFY_SECONDS = 1.0


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


def ecu_messages_present(can_recv, bus: int, addresses: tuple[int, ...], timeout: float) -> bool:
  """Return whether an ECU-originated message is still arriving after CommunicationControl."""
  if can_recv is None:
    return False

  deadline = time.monotonic() + timeout
  while time.monotonic() < deadline:
    for packet in can_recv(wait_for_one=True):
      if any(msg.src == bus and msg.address in addresses for msg in packet):
        return True
  return False


def ecu_suppression_verified(can_recv, bus: int, addresses: tuple[int, ...], timeout: float,
                             minimum_bus_frames: int = 20) -> bool:
  """Require live bus traffic while every suppressed address remains absent."""
  if can_recv is None:
    return False

  bus_frames = 0
  deadline = time.monotonic() + timeout
  while time.monotonic() < deadline:
    for packet in can_recv(wait_for_one=True):
      for msg in packet:
        if msg.src != bus:
          continue
        bus_frames += 1
        if msg.address in addresses:
          return False
  return bus_frames >= minimum_bus_frames


def attempt_ev9_pre_fingerprint_suppression(cached_params, params, can_recv, can_send,
                                            initial_can_messages: list | None = None) -> bool:
  """Attempt the parked EV9 stage-15 knockout immediately after first CAN.

  This is deliberately narrower than normal fingerprinting: it requires a
  verified cached EV9 identity, cached ADAS firmware at 0x730, and the complete
  non-actuating reconstruction stage. A positive response is re-verified after
  fingerprinting before longitudinal ownership is accepted.
  """
  global EV9_EARLY_SUPPRESSION_ACTIVE
  EV9_EARLY_SUPPRESSION_ACTIVE = False
  hyundaicanfd.set_ev9_adrv_baselines([])
  if cached_params is None or str(cached_params.carFingerprint) != str(CAR.KIA_EV9) or cached_params.brand != "hyundai":
    return False
  if not params.get_bool("AlphaLongitudinalEnabled") or not cached_params.openpilotLongitudinalControl or cached_params.pcmCruise:
    return False

  has_adas_fw = any(fw.ecu == Ecu.adas and fw.address == 0x730 for fw in cached_params.carFw)
  test = get_ev9_longitudinal_test_config(params)
  if not has_adas_fw or test.stage < EV9LongitudinalTestStage.STEERING_KEEPALIVE or \
      not test.persistent_suppression_allowed:
    return False

  request, _ = ev9_communication_control_requests(test.probe_mode)
  observed_can_messages = list(initial_can_messages or [])

  def observing_can_recv(wait_for_one=False):
    packets = can_recv(wait_for_one=wait_for_one)
    for packet in packets:
      observed_can_messages.extend(packet)
    return packets

  ecu_log("=== EV9 PRE-FINGERPRINT SUPPRESSION ATTEMPT ===")
  observed_recv = observing_can_recv if can_recv is not None else can_recv
  EV9_EARLY_SUPPRESSION_ACTIVE = disable_ecu(observed_recv, can_send, bus=1, addr=0x730, com_cont_req=request,
                                              session_delay=0.0)
  if EV9_EARLY_SUPPRESSION_ACTIVE:
    hyundaicanfd.set_ev9_adrv_baselines(observed_can_messages)
    baseline_addresses = {0x160, 0x161, 0x162, 0x1A0, 0x1BA, 0x1DA, 0x1E0, 0x1E5, 0x1EA, 0x200, 0x345, 0x38C, 0x57A}
    observed_addresses = sorted({msg.address for msg in observed_can_messages if msg.src == 1 and msg.address in baseline_addresses})
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
    ev9_long_test = get_ev9_longitudinal_test_config() if candidate == CAR.KIA_EV9 else None
    ev9_long_test_armed = ev9_long_test is not None and ev9_long_test.armed

    # "LKA steering" if LKAS or LKAS_ALT messages are seen coming from the camera.
    # Generally means our LKAS message is forwarded to another ECU (commonly ADAS ECU)
    # that finally retransmits our steering command in LFA or LFA_ALT to the MDPS.
    # "LFA steering" if camera directly sends LFA to the MDPS
    cam_can = CanBus(None, fingerprint).CAM
    lka_steering = 0x50 in fingerprint[cam_can] or 0x110 in fingerprint[cam_can]
    CAN = CanBus(None, fingerprint, lka_steering)

    if ret.flags & HyundaiFlags.CANFD:
      # Shared configuration for CAN-FD cars
      ret.alphaLongitudinalAvailable = candidate not in CANFD_UNSUPPORTED_LONGITUDINAL_CAR
      if lka_steering and Ecu.adas not in [fw.ecu for fw in car_fw] and candidate not in CANFD_SECURITYACCESS_CAR and \
          not ev9_long_test_armed:
        # this needs to be figured out for cars without an ADAS ECU
        # Cars in CANFD_SECURITYACCESS_CAR are known to have ADAS ECUs that work with SecurityAccess
        ret.alphaLongitudinalAvailable = False
      if lka_steering and ret.flags & HyundaiFlags.CANFD_ANGLE_STEERING and candidate not in CANFD_ANGLE_LONGITUDINAL_CAR and \
          not ev9_long_test_armed:
        # Most angle-steering LKA platforms still need stock longitudinal validation.
        ret.alphaLongitudinalAvailable = False

      # Stage-15 suppression can remove ADAS-originated 0x1BA before live
      # fingerprinting. The EV9 platform is known to have BSM and its parser
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

    if candidate == CAR.KIA_EV9 and ev9_long_test_armed:
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
  def init(CP, can_recv, can_send, communication_control=None):
    global ECU_DISABLE_TIMESTAMP, EV9_EARLY_SUPPRESSION_ACTIVE
    from openpilot.common.params import Params
    params = Params()
    ev9_long_test = get_ev9_longitudinal_test_config(params) if CP.carFingerprint == CAR.KIA_EV9 else None

    # Defense in depth: an EV9 CarParams cache must never retain longitudinal
    # ownership after the explicit developer gate is removed.
    if communication_control is None and CP.carFingerprint == CAR.KIA_EV9 and CP.openpilotLongitudinalControl and \
        (ev9_long_test is None or not ev9_long_test.armed):
      apply_ecu_disable_failure_fallback(CP, params)
      ecu_log("EV9 longitudinal test gate is not armed; retaining stock SCC")
      return

    if communication_control is None and CP.carFingerprint == CAR.KIA_EV9 and CP.openpilotLongitudinalControl and \
        ev9_long_test is not None and ev9_long_test.probe_mode == EV9LongitudinalProbeMode.DIAGNOSTIC_SESSION_ONLY:
      bus = CanBus(CP).ECAN
      entered, restored = run_diagnostic_session_probe(can_recv, can_send, bus=bus, addr=0x730)
      apply_ecu_disable_failure_fallback(CP, params)
      ecu_log(f"EV9 diagnostic-only probe finished: entered={entered}, restored={restored}; stock SCC retained")
      return

    if communication_control is None:
      if CP.carFingerprint in CANFD_RADAR_LIVE_LONGITUDINAL_CAR or \
          (ev9_long_test is not None and ev9_long_test.stage >= EV9LongitudinalTestStage.TX_DISABLE):
        # Don't use 0x80 suppress bit so we can read the ECU response.
        # Keep ADAS reception enabled while blocking its normal output. This preserves the
        # inputs needed to study BSM, but does not itself preserve ADAS-originated BSM output.
        communication_control = bytes([uds.SERVICE_TYPE.COMMUNICATION_CONTROL, uds.CONTROL_TYPE.ENABLE_RX_DISABLE_TX, uds.MESSAGE_TYPE.NORMAL])
      else:
        # 0x80 silences response for other cars (original behavior)
        communication_control = bytes([uds.SERVICE_TYPE.COMMUNICATION_CONTROL, 0x80 | uds.CONTROL_TYPE.DISABLE_RX_DISABLE_TX, uds.MESSAGE_TYPE.NORMAL])

    ev9_restore_communication = None
    if ev9_long_test is not None and ev9_long_test.armed:
      communication_control, ev9_restore_communication = ev9_communication_control_requests(ev9_long_test.probe_mode)

    stage_log = f", ev9TestStage={ev9_long_test.stage.name}" if ev9_long_test is not None else ""
    init_log = f"=== init() called: opLong={CP.openpilotLongitudinalControl}, flags=0x{CP.flags:x}, "
    init_log += f"safetyParam={CP.safetyConfigs[-1].safetyParam}{stage_log} ==="
    ecu_log(init_log)

    if CP.openpilotLongitudinalControl and not (CP.flags & (HyundaiFlags.CANFD_CAMERA_SCC | HyundaiFlags.CAMERA_SCC)):
      addr, bus = 0x7d0, CanBus(CP).ECAN if CP.flags & (HyundaiFlags.CANFD | HyundaiFlags.CAN_CANFD_BLENDED) else 0
      if CP.flags & HyundaiFlags.CANFD_LKA_STEERING.value:
        addr, bus = 0x730, CanBus(CP).ECAN

      # A direct OFF -> READY start may have completed the exact same verified
      # request before fingerprinting. Prove the bus is live and stock SCC is
      # still absent before accepting that handoff.
      ecu_disabled = False
      resume_early_suppression = CP.carFingerprint == CAR.KIA_EV9 and EV9_EARLY_SUPPRESSION_ACTIVE and \
        ev9_long_test is not None and ev9_long_test.persistent_suppression_allowed
      EV9_EARLY_SUPPRESSION_ACTIVE = False
      if resume_early_suppression:
        # This flag can only be set by a positive 0x68 response in this same
        # card process. Mode 2 has also been validated on-route to remove stock
        # SCC_CONTROL. Avoid another 250 ms receive-only window here: Panda
        # cannot accept the replacement set until ControlsReady changes safety,
        # and that gap is enough for EV9 startup DTCs to latch.
        ecu_disabled = True
        ecu_log("=== EV9 PRE-FINGERPRINT SUPPRESSION HANDOFF accepted positive response ===")

      # Try ECU disable. If it succeeds (IGN-ON mode), enable longitudinal.
      # If it fails (READY mode returns NRC 0x22, or timeout), strip LONG safety flag
      # so panda forwards stock SCC messages normally (lateral-only mode).
      if not ecu_disabled:
        ecu_log(f"=== ECU DISABLE attempt: addr=0x{addr:x}, bus={bus} ===")
      ev9_reset_probe = ev9_long_test is not None and \
        ev9_long_test.probe_mode == EV9LongitudinalProbeMode.RESET_TX_DISABLE_ALL_MESSAGE_TYPES
      ev9_full_disable_transition = ev9_long_test is not None and \
        ev9_long_test.probe_mode == EV9LongitudinalProbeMode.FULL_DISABLE_THEN_RX_ENABLE
      if not ecu_disabled and ev9_full_disable_transition:
        # Some ECUs accept TX-disable only as a transition from a fully muted
        # communication state. Verify both positive responses; if the second
        # step fails, explicitly restore normal communication before fallback.
        full_disable = bytes([uds.SERVICE_TYPE.COMMUNICATION_CONTROL,
                              uds.CONTROL_TYPE.DISABLE_RX_DISABLE_TX,
                              uds.MESSAGE_TYPE.NORMAL_AND_NETWORK_MANAGEMENT])
        ecu_log(f"=== EV9 FULL-DISABLE TRANSITION START - request={full_disable.hex()} ===")
        ecu_disabled = disable_ecu(can_recv, can_send, bus=bus, addr=addr, com_cont_req=full_disable)
        if ecu_disabled:
          ecu_log(f"=== EV9 RE-ENABLE RX TRANSITION - request={communication_control.hex()} ===")
          ecu_disabled = disable_ecu(can_recv, can_send, bus=bus, addr=addr, com_cont_req=communication_control)
          if not ecu_disabled:
            restore_request = bytes([uds.SERVICE_TYPE.COMMUNICATION_CONTROL,
                                     uds.CONTROL_TYPE.ENABLE_RX_ENABLE_TX,
                                     uds.MESSAGE_TYPE.NORMAL_AND_NETWORK_MANAGEMENT])
            ecu_log(f"=== EV9 TRANSITION FAILED - restoring={restore_request.hex()} ===")
            disable_ecu(can_recv, can_send, bus=bus, addr=addr, com_cont_req=restore_request, retry=1)
      elif not ecu_disabled:
        ecu_disabled = disable_ecu(can_recv, can_send, bus=bus, addr=addr, com_cont_req=communication_control,
                                   reset=bool(CP.flags & HyundaiFlags.CAN_CANFD_BLENDED) or ev9_reset_probe)

      if ecu_disabled and ev9_long_test is not None and ev9_long_test.armed and \
          not ev9_long_test.persistent_suppression_allowed:
        # Probe only: the tested EV9 firmware acknowledges 28 01 01 with 68 01 but
        # continues transmitting SCC_CONTROL at 50 Hz. IsoTP drains the card CAN
        # socket while waiting for the response, so a local silence check alone is
        # not authoritative. Always bound the probe, restore communication, and
        # fall back to stock before controls become ready.
        ecu_log(f"holding EV9 probe {communication_control.hex()} for {EV9_LONG_PROBE_HOLD_SECONDS:.1f} seconds")
        time.sleep(EV9_LONG_PROBE_HOLD_SECONDS)
        stock_scc_present = ecu_messages_present(can_recv, bus, EV9_LONG_DISABLE_VERIFY_ADDRS,
                                                 EV9_LONG_DISABLE_VERIFY_SECONDS)
        outcome = "stock 0x1A0 observed" if stock_scc_present else "no local 0x1A0 observation"
        ecu_log(f"=== EV9 COMMUNICATION CONTROL PROBE COMPLETE - {outcome}; restoring communication ===")
        disable_ecu(can_recv, can_send, bus=bus, addr=addr, com_cont_req=ev9_restore_communication, retry=1)
        ecu_disabled = False
      elif ecu_disabled and ev9_long_test is not None and ev9_long_test.persistent_suppression_allowed:
        persistent_log = f"=== EV9 PERSISTENT COMMUNICATION CONTROL ACTIVE - request={communication_control.hex()}, "
        persistent_log += f"stage={ev9_long_test.stage.name}; controller Tester Present required ==="
        ecu_log(persistent_log)

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
    communication_control = bytes([uds.SERVICE_TYPE.COMMUNICATION_CONTROL, 0x80 | uds.CONTROL_TYPE.ENABLE_RX_ENABLE_TX, uds.MESSAGE_TYPE.NORMAL])
    CarInterface.init(CP, can_recv, can_send, communication_control)

  def update(self, can_packets, starpilot_toggles):
    ret, fp_ret = super().update(can_packets, starpilot_toggles)

    # When ECU disable was skipped (READY mode boot) or failed, suppress CAN timeout errors.
    # Keep checking param until it's True (init() sets it AFTER first update() call),
    # then cache to avoid per-frame param reads.
    if not getattr(self, '_ecu_disable_failed_cached', False):
      from openpilot.common.params import Params
      self._ecu_disable_failed_cached = Params().get_bool("EcuDisableFailed")
    if self._ecu_disable_failed_cached and not ret.canValid:
      ret.canValid = True

    global ECU_DISABLE_TIMESTAMP
    if ECU_DISABLE_TIMESTAMP > 0 and not ret.canValid:
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
