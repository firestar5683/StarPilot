import time
from opendbc.car import get_safety_config, structs, uds
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.values import HyundaiFlags, CAR, CarControllerParams, \
                                                   CANFD_UNSUPPORTED_LONGITUDINAL_CAR, \
                                                   CANFD_SECURITYACCESS_CAR, \
                                                   CANFD_RADAR_LIVE_LONGITUDINAL_CAR, \
                                                   RADAR_LIVE_LONGITUDINAL_CAR, \
                                                   UNSUPPORTED_LONGITUDINAL_CAR, HyundaiSafetyFlags, \
                                                   LEGACY_LONGITUDINAL_CAR, \
                                                   HyundaiStarPilotSafetyFlags, \
                                                   hyundai_cancel_button_enables_cruise
from opendbc.car.hyundai.radar_interface import get_radar_track_config, radar_tracks_available
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
KONA_NON_SCC_FCA_RADAR_ADDR = 0x602


def apply_platform_longitudinal_params(ret: structs.CarParams) -> None:
  if not (ret.flags & HyundaiFlags.CANFD):
    return

  ret.startingState = True
  ret.startAccel = 1.0
  ret.longitudinalActuatorDelay = 0.5
  ret.vEgoStopping = 0.3
  ret.vEgoStarting = 0.1
  ret.stoppingDecelRate = 0.4


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


class CarInterface(CarInterfaceBase):
  CarState = CarState
  CarController = CarController
  RadarInterface = RadarInterface

  @staticmethod
  def get_pid_accel_limits(CP, current_speed, cruise_speed):
    return ACCEL_MIN, CarControllerParams.ACCEL_MAX

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
      ret.alphaLongitudinalAvailable = candidate not in CANFD_UNSUPPORTED_LONGITUDINAL_CAR
      if lka_steering and Ecu.adas not in [fw.ecu for fw in car_fw] and candidate not in CANFD_SECURITYACCESS_CAR:
        # this needs to be figured out for cars without an ADAS ECU
        # Cars in CANFD_SECURITYACCESS_CAR are known to have ADAS ECUs that work with SecurityAccess
        ret.alphaLongitudinalAvailable = False
      if lka_steering and ret.flags & HyundaiFlags.CANFD_ANGLE_STEERING:
        # Angle-steering LKA platforms still need stock longitudinal validation.
        ret.alphaLongitudinalAvailable = False

      ret.enableBsm = 0x1ba in fingerprint[CAN.ECAN]

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
    global ECU_DISABLE_TIMESTAMP
    from openpilot.common.params import Params
    params = Params()

    if communication_control is None:
      if CP.carFingerprint in CANFD_RADAR_LIVE_LONGITUDINAL_CAR:
        # Don't use 0x80 suppress bit so we can read the ECU response.
        # Use ENABLE_RX_DISABLE_TX (0x01) so the ECU can still receive from rear radars for BSM
        # while blocking SCC TX.
        communication_control = bytes([uds.SERVICE_TYPE.COMMUNICATION_CONTROL, uds.CONTROL_TYPE.ENABLE_RX_DISABLE_TX, uds.MESSAGE_TYPE.NORMAL])
      else:
        # 0x80 silences response for other cars (original behavior)
        communication_control = bytes([uds.SERVICE_TYPE.COMMUNICATION_CONTROL, 0x80 | uds.CONTROL_TYPE.DISABLE_RX_DISABLE_TX, uds.MESSAGE_TYPE.NORMAL])

    ecu_log(f"=== init() called: opLong={CP.openpilotLongitudinalControl}, flags=0x{CP.flags:x}, safetyParam={CP.safetyConfigs[-1].safetyParam} ===")

    if CP.openpilotLongitudinalControl and not (CP.flags & (HyundaiFlags.CANFD_CAMERA_SCC | HyundaiFlags.CAMERA_SCC)):
      addr, bus = 0x7d0, CanBus(CP).ECAN if CP.flags & (HyundaiFlags.CANFD | HyundaiFlags.CAN_CANFD_BLENDED) else 0
      if CP.flags & HyundaiFlags.CANFD_LKA_STEERING.value:
        addr, bus = 0x730, CanBus(CP).ECAN

      # Try ECU disable. If it succeeds (IGN-ON mode), enable longitudinal.
      # If it fails (READY mode returns NRC 0x22, or timeout), strip LONG safety flag
      # so panda forwards stock SCC messages normally (lateral-only mode).
      ecu_log(f"=== ECU DISABLE attempt: addr=0x{addr:x}, bus={bus} ===")
      ecu_disabled = disable_ecu(can_recv, can_send, bus=bus, addr=addr, com_cont_req=communication_control,
                                 reset=bool(CP.flags & HyundaiFlags.CAN_CANFD_BLENDED))

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
