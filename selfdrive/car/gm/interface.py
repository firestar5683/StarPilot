#!/usr/bin/env python3
from cereal import car, custom
from math import fabs, exp
import numpy as np
from panda import Panda

from openpilot.common.conversions import Conversions as CV
from openpilot.selfdrive.car import create_button_events, get_safety_config
from openpilot.selfdrive.car.gm.radar_interface import RADAR_HEADER_MSG
from openpilot.selfdrive.car.gm.values import CAR, CruiseButtons, CarControllerParams, EV_CAR, CAMERA_ACC_CAR, CanBus, GMFlags, CC_ONLY_CAR, SDGM_CAR, ASCM_INT, set_red_panda_canbus
from openpilot.selfdrive.car.interfaces import CarInterfaceBase, TorqueFromLateralAccelCallbackType, FRICTION_THRESHOLD, LateralAccelFromTorqueCallbackType, get_friction_threshold
from openpilot.selfdrive.controls.lib.drive_helpers import get_friction

ButtonType = car.CarState.ButtonEvent.Type
FrogPilotButtonType = custom.FrogPilotCarState.ButtonEvent.Type
EventName = car.CarEvent.EventName
FrogPilotEventName = custom.FrogPilotCarEvent.EventName
GearShifter = car.CarState.GearShifter
TransmissionType = car.CarParams.TransmissionType
NetworkLocation = car.CarParams.NetworkLocation
BUTTONS_DICT = {CruiseButtons.RES_ACCEL: ButtonType.accelCruise, CruiseButtons.DECEL_SET: ButtonType.decelCruise,
                CruiseButtons.MAIN: ButtonType.altButton3, CruiseButtons.CANCEL: ButtonType.cancel}

PEDAL_MSG = 0x201
CAM_MSG = 0x320  # AEBCmd
                 # TODO: Is this always linked to camera presence?
ACCELERATOR_POS_MSG = 0xbe

VOLT_LIKE_CARS = {
  CAR.CHEVROLET_VOLT,
  CAR.CHEVROLET_VOLT_2019,
  CAR.CHEVROLET_VOLT_CC,
  CAR.CHEVROLET_VOLT_CAMERA,
  CAR.CHEVROLET_VOLT_ASCM,
  CAR.CHEVROLET_MALIBU,
  CAR.CHEVROLET_MALIBU_ASCM,
  CAR.CHEVROLET_MALIBU_SDGM,
  CAR.CHEVROLET_MALIBU_CC,
  CAR.CHEVROLET_MALIBU_HYBRID_CC,
}

NON_LINEAR_TORQUE_PARAMS = {
  CAR.CHEVROLET_BOLT_ACC_2022_2023: {
    "left": [2.6531724862969748, 1.1, 0.1919764879840985, 0.0],
    "right": [2.7031724862969748, 1.0, 0.1469764879840985, 0.0],
  },
  CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL: {
    "left": [2.6531724862969748, 1.1, 0.1919764879840985, 0.0],
    "right": [2.7031724862969748, 1.0, 0.1469764879840985, 0.0],
  },
  CAR.CHEVROLET_BOLT_CC_2022_2023: {
    "left": [2.6531724862969748, 1.1, 0.1919764879840985, 0.0],
    "right": [2.7031724862969748, 1.0, 0.1469764879840985, 0.0],
  },
  CAR.CHEVROLET_BOLT_CC_2019_2021: {
    "left": [1.8, 1.1, 0.27, 0.0],
    "right": [2.0, 1.0, 0.205, 0.0],
  },
  CAR.CHEVROLET_BOLT_CC_2017: {
    "left": [2.15, 1.0, 0.21, 0.0],
    "right": [2.15, 1.0, 0.21, 0.0],
  },
  CAR.GMC_ACADIA: {
    "left": [4.78003305, 1.0, 0.3122, 0.05591772],
    "right": [4.78003305, 1.0, 0.3122, 0.05591772],
  },
  CAR.CHEVROLET_SILVERADO: {
    "left": [3.8, 0.81, 0.24, 0.0465122],
    "right": [3.8, 0.81, 0.24, 0.0465122],
  },
}


class CarInterface(CarInterfaceBase):
  def __init__(self, CP, FPCP, CarController, CarState):
    super().__init__(CP, FPCP, CarController, CarState)
    self.steer_offset = 0.0

  @staticmethod
  def get_pid_accel_limits(CP, current_speed, cruise_speed):
    return CarControllerParams.ACCEL_MIN, CarControllerParams.ACCEL_MAX

  # Determined by iteratively plotting and minimizing error for f(angle, speed) = steer.
  @staticmethod
  def get_steer_feedforward_volt(desired_angle, v_ego):
    desired_angle *= 0.02904609
    sigmoid = desired_angle / (1 + fabs(desired_angle))
    return 0.10006696 * sigmoid * (v_ego + 3.12485927)

  def get_steer_feedforward_function(self):
    if self.CP.carFingerprint in VOLT_LIKE_CARS:
      return self.get_steer_feedforward_volt
    else:
      return CarInterfaceBase.get_steer_feedforward_default

  def get_lataccel_torque_siglin(self) -> float:

    def torque_from_lateral_accel_siglin_func(lateral_acceleration: float) -> float:
      # The "lat_accel vs torque" relationship is assumed to be the sum of "sigmoid + linear" curves
      # An important thing to consider is that the slope at 0 should be > 0 (ideally >1)
      # This has big effect on the stability about 0 (noise when going straight)
      non_linear_torque_params = NON_LINEAR_TORQUE_PARAMS.get(self.CP.carFingerprint)
      assert non_linear_torque_params, "The params are not defined"
      # Left is positive
      side_key = "left" if lateral_acceleration >= 0 else "right"
      a, b, c, d = non_linear_torque_params[side_key]
      sig_input = a * lateral_acceleration
      sig = np.sign(sig_input) * (1 / (1 + exp(-fabs(sig_input))) - 0.5)
      steer_torque = (sig * b) + (lateral_acceleration * c) + d
      return float(steer_torque)

    lataccel_values = np.arange(-5.0, 5.0, 0.01)
    torque_values = [torque_from_lateral_accel_siglin_func(x) for x in lataccel_values]
    assert min(torque_values) < -1 and max(torque_values) > 1, "The torque values should cover the range [-1, 1]"
    return torque_values, lataccel_values

  def torque_from_lateral_accel(self) -> TorqueFromLateralAccelCallbackType:
    if self.CP.carFingerprint in NON_LINEAR_TORQUE_PARAMS:
      torque_values, lataccel_values = self.get_lataccel_torque_siglin()

      def torque_from_lateral_accel_siglin(lateral_acceleration: float, torque_params: car.CarParams.LateralTorqueTuning):
        return float(np.interp(lateral_acceleration, lataccel_values, torque_values) + self.steer_offset)
      return torque_from_lateral_accel_siglin
    else:
      def torque_from_lateral_accel_linear(lateral_acceleration: float, torque_params: car.CarParams.LateralTorqueTuning):
        return self.torque_from_lateral_accel_linear(lateral_acceleration, torque_params) + self.steer_offset
      return torque_from_lateral_accel_linear

  def lateral_accel_from_torque(self) -> LateralAccelFromTorqueCallbackType:
    if self.CP.carFingerprint in NON_LINEAR_TORQUE_PARAMS:
      torque_values, lataccel_values = self.get_lataccel_torque_siglin()

      def lateral_accel_from_torque_siglin(torque: float, torque_params: car.CarParams.LateralTorqueTuning):
        return np.interp(torque - self.steer_offset, torque_values, lataccel_values)
      return lateral_accel_from_torque_siglin
    else:
      def lateral_accel_from_torque_linear(torque: float, torque_params: car.CarParams.LateralTorqueTuning):
        return self.lateral_accel_from_torque_linear(torque - self.steer_offset, torque_params)
      return lateral_accel_from_torque_linear

  def update(self, c: car.CarControl, can_strings: list[bytes], frogpilot_toggles) -> car.CarState:
    self.steer_offset = float(getattr(frogpilot_toggles, "steer_offset", 0.0))
    return super().update(c, can_strings, frogpilot_toggles)

  @staticmethod
  def _get_params(ret, candidate, fingerprint, car_fw, experimental_long, docs, frogpilot_toggles):
    ret.carName = "gm"
    red_panda = getattr(frogpilot_toggles, "red_panda", False)
    set_red_panda_canbus(red_panda)

    ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.gm)]
    if red_panda:
      ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.noOutput), ret.safetyConfigs[0]]
    gm_safety_cfg = ret.safetyConfigs[-1] if red_panda else ret.safetyConfigs[0]
    ret.autoResumeSng = False
    ret.enableBsm = 0x142 in fingerprint.get(CanBus.POWERTRAIN, {})

    def has_sascm(fingerprint):
      return 0x2FF in fingerprint.get(CanBus.POWERTRAIN, {})

    # Detect Beartech SASCM allows openpilot longitudinal control on SDGM and ASCM_INT vehicles
    if has_sascm(fingerprint):
      ret.flags |= GMFlags.SASCM.value

    if PEDAL_MSG in fingerprint.get(CanBus.POWERTRAIN, {}):
      ret.enableGasInterceptor = True
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_GAS_INTERCEPTOR
      if candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023:
        # Hard-block pedal interceptor for ACC fingerprinted Bolts
        ret.enableGasInterceptor = False
        gm_safety_cfg.safetyParam &= ~Panda.FLAG_GM_GAS_INTERCEPTOR
      else:
        # When a pedal interceptor is present, always use normal longitudinal (block stock cruise)
        experimental_long = False

    if candidate in EV_CAR:
      ret.transmissionType = TransmissionType.direct
    else:
      ret.transmissionType = TransmissionType.automatic

    kaofui_cars = SDGM_CAR | ASCM_INT | VOLT_LIKE_CARS | {CAR.CHEVROLET_MALIBU_HYBRID_CC}
    ret.longitudinalTuning.kiBP = [5., 35.] if candidate in kaofui_cars else [5., 35., 60.]

    is_bolt_2022_2023_pedal = candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL and ret.enableGasInterceptor

    kaofui_camera_cars = {
      CAR.CHEVROLET_VOLT_CAMERA,
      CAR.CHEVROLET_VOLT_CC,
      CAR.CHEVROLET_MALIBU_HYBRID_CC,
    }
    bolt_cc_camera_cars = {
      CAR.CHEVROLET_BOLT_CC_2017,
      CAR.CHEVROLET_BOLT_CC_2019_2021,
      CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
      CAR.CHEVROLET_BOLT_CC_2022_2023,
    }
    is_camera_acc = candidate in CAMERA_ACC_CAR and candidate not in kaofui_cars and \
                    (candidate not in CC_ONLY_CAR or candidate in bolt_cc_camera_cars)
    if candidate in kaofui_camera_cars:
      # Keep Volt/Malibu camera path functionally aligned with kaofui.
      ret.experimentalLongitudinalAvailable = candidate not in (CC_ONLY_CAR | ASCM_INT | SDGM_CAR) or has_sascm(fingerprint)
      ret.networkLocation = NetworkLocation.fwdCamera
      ret.radarUnavailable = 0x460 not in fingerprint.get(CanBus.OBSTACLE, {})
      ret.pcmCruise = True
      ret.minEnableSpeed = 5 * CV.KPH_TO_MS
      ret.minSteerSpeed = 10 * CV.KPH_TO_MS
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_HW_CAM

      # Tuning for experimental long
      ret.longitudinalTuning.kiV = [0.5, 0.5]
      ret.stoppingDecelRate = 1.0  # reach brake quickly after enabling
      ret.vEgoStopping = 0.25
      ret.vEgoStarting = 0.25
      ret.stopAccel = -0.25

      if ret.experimentalLongitudinalAvailable and experimental_long:
        ret.pcmCruise = False
        ret.openpilotLongitudinalControl = True
        gm_safety_cfg.safetyParam |= Panda.FLAG_GM_HW_CAM_LONG
    elif is_camera_acc:
      # TorqueTune camera-ACC behavior
      ret.experimentalLongitudinalAvailable = (candidate not in CC_ONLY_CAR) and not ret.enableGasInterceptor
      ret.networkLocation = NetworkLocation.fwdCamera
      ret.radarUnavailable = True  # no radar
      ret.pcmCruise = not ret.enableGasInterceptor
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_HW_CAM
      ret.minEnableSpeed = 5 * CV.KPH_TO_MS
      ret.minSteerSpeed = 10 * CV.KPH_TO_MS

      # Tuning for experimental long
      ret.longitudinalTuning.kiV = [0.5, 0.5, 0.5]
      ret.vEgoStopping = 0.1
      ret.vEgoStarting = 0.1

      ret.stoppingDecelRate = 1.0  # reach brake quickly after enabling
      ret.vEgoStopping = 0.25
      ret.vEgoStarting = 0.25
      ret.stopAccel = -0.25

      if ret.experimentalLongitudinalAvailable and experimental_long:
        ret.pcmCruise = False
        ret.openpilotLongitudinalControl = True
        gm_safety_cfg.safetyParam |= Panda.FLAG_GM_HW_CAM_LONG
    elif candidate in SDGM_CAR:
      # kaofui parity: SDGM cars require SASCM for experimental long
      ret.experimentalLongitudinalAvailable = candidate not in (CC_ONLY_CAR | ASCM_INT | SDGM_CAR) or has_sascm(fingerprint)
      ret.networkLocation = NetworkLocation.fwdCamera
      ret.radarUnavailable = 0x460 not in fingerprint.get(CanBus.OBSTACLE, {})
      ret.pcmCruise = True
      ret.minEnableSpeed = -1.  # engage speed is decided by pcm
      ret.minSteerSpeed = 7 * CV.MPH_TO_MS
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_HW_SDGM
      # Use C9 brake bit on SDGM variants that lack 0xBE (ECMAcceleratorPos),
      # so panda brake_pressed source matches carstate.
      if ACCELERATOR_POS_MSG not in fingerprint.get(CanBus.POWERTRAIN, {}):
        gm_safety_cfg.safetyParam |= Panda.FLAG_GM_FORCE_BRAKE_C9
        ret.flags |= GMFlags.FORCE_BRAKE_C9.value

      # Tuning for experimental long
      ret.longitudinalTuning.kiV = [0.5, 0.5] if candidate in kaofui_cars else [0.5, 0.5, 0.5]
      ret.vEgoStopping = 0.1
      ret.vEgoStarting = 0.1

      ret.stoppingDecelRate = 1.0  # reach brake quickly after enabling
      ret.vEgoStopping = 0.25
      ret.vEgoStarting = 0.25
      ret.stopAccel = -0.25

      if ret.experimentalLongitudinalAvailable and experimental_long:
        ret.pcmCruise = False
        ret.openpilotLongitudinalControl = True
        gm_safety_cfg.safetyParam |= Panda.FLAG_GM_HW_CAM_LONG
      if is_bolt_2022_2023_pedal:
        ret.experimentalLongitudinalAvailable = False
        ret.pcmCruise = False
    elif candidate in ASCM_INT:
      # kaofui parity: ASCM_INT cars require SASCM for experimental long
      ret.experimentalLongitudinalAvailable = candidate not in (CC_ONLY_CAR | ASCM_INT | SDGM_CAR) or has_sascm(fingerprint)
      ret.networkLocation = NetworkLocation.fwdCamera
      ret.radarUnavailable = 0x460 not in fingerprint.get(CanBus.OBSTACLE, {})
      ret.pcmCruise = True
      ret.minEnableSpeed = 5 * CV.KPH_TO_MS
      ret.minSteerSpeed = 7 * CV.MPH_TO_MS
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_HW_CAM
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_ASCM_INT

      # Tuning for experimental long
      ret.longitudinalTuning.kiV = [0.5, 0.5] if candidate in kaofui_cars else [0.5, 0.5, 0.5]
      ret.vEgoStopping = 0.1
      ret.vEgoStarting = 0.1

      ret.stoppingDecelRate = 1.0  # reach brake quickly after enabling
      ret.vEgoStopping = 0.25
      ret.vEgoStarting = 0.25
      ret.stopAccel = -0.25

      if ret.experimentalLongitudinalAvailable and experimental_long:
        ret.pcmCruise = False
        ret.openpilotLongitudinalControl = True
        gm_safety_cfg.safetyParam |= Panda.FLAG_GM_HW_CAM_LONG
      if is_bolt_2022_2023_pedal:
        ret.experimentalLongitudinalAvailable = False
        ret.pcmCruise = False
    else:  # ASCM, OBD-II harness
      ret.openpilotLongitudinalControl = not frogpilot_toggles.disable_openpilot_long
      ret.networkLocation = NetworkLocation.gateway
      ret.radarUnavailable = RADAR_HEADER_MSG not in fingerprint.get(CanBus.OBSTACLE, {}) and not docs
      ret.pcmCruise = False  # stock non-adaptive cruise control is kept off
      # supports stop and go, but initial engage must (conservatively) be above 18mph
      ret.minEnableSpeed = 18 * CV.MPH_TO_MS
      ret.minSteerSpeed = 7 * CV.MPH_TO_MS

      # Tuning
      ret.longitudinalTuning.kiV = [0.5, 0.5] if candidate in kaofui_cars else [0.5, 0.5, 0.5]
      if candidate in kaofui_cars:
        ret.stoppingDecelRate = 3
        ret.vEgoStopping = 0.75
        ret.vEgoStarting = 0.75
        ret.stopAccel = -1.5

      if ret.enableGasInterceptor:
        # Need to set ASCM long limits when using pedal interceptor, instead of camera ACC long limits
        gm_safety_cfg.safetyParam |= Panda.FLAG_GM_HW_ASCM_LONG

    if getattr(frogpilot_toggles, "remote_start_boots_comma", False):
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_REMOTE_START_BOOTS_COMMA

    # Start with a baseline tuning for all GM vehicles. Override tuning as needed in each model section below.
    ret.lateralTuning.pid.kiBP, ret.lateralTuning.pid.kpBP = [[0.], [0.]]
    ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.2], [0.00]]
    ret.lateralTuning.pid.kf = 0.00004   # full torque for 20 deg at 80mph means 0.00007818594
    ret.steerActuatorDelay = 0.1  # Default delay, not measured yet
    ret.longitudinalTuning.deadzoneBP = [0.]
    ret.longitudinalTuning.deadzoneV  = [0.]

    ret.steerLimitTimer = 0.4
    ret.radarTimeStep = 0.0667  # GM radar runs at 15Hz instead of standard 20Hz
    ret.longitudinalActuatorDelay = 0.5  # large delay to initially start braking

    if candidate in (CAR.CHEVROLET_VOLT, CAR.CHEVROLET_VOLT_CC, CAR.CHEVROLET_VOLT_CAMERA):
      ret.minEnableSpeed = -1

    if candidate == CAR.CHEVROLET_VOLT_2019 and not ret.openpilotLongitudinalControl:
      ret.minEnableSpeed = -1

    if candidate in VOLT_LIKE_CARS:
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)
      ret.steerActuatorDelay = 0.2
      if candidate == CAR.CHEVROLET_MALIBU_HYBRID_CC and ret.enableGasInterceptor:
        ret.flags |= GMFlags.PEDAL_LONG.value

    elif candidate == CAR.GMC_ACADIA:
      ret.minEnableSpeed = -1.  # engage speed is decided by pcm
      ret.steerActuatorDelay = 0.2
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate == CAR.BUICK_LACROSSE:
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate == CAR.CADILLAC_ESCALADE:
      ret.minEnableSpeed = -1.  # engage speed is decided by pcm
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate in (CAR.CADILLAC_ESCALADE_ESV, CAR.CADILLAC_ESCALADE_ESV_2019):
      ret.minEnableSpeed = -1.  # engage speed is decided by pcm

      if candidate == CAR.CADILLAC_ESCALADE_ESV:
        ret.lateralTuning.pid.kiBP, ret.lateralTuning.pid.kpBP = [[10., 41.0], [10., 41.0]]
        ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.13, 0.24], [0.01, 0.02]]
        ret.lateralTuning.pid.kf = 0.000045
      else:
        ret.steerActuatorDelay = 0.2
        CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate in (CAR.CHEVROLET_BOLT_ACC_2022_2023, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL, CAR.CHEVROLET_BOLT_CC_2022_2023, CAR.CHEVROLET_BOLT_CC_2019_2021, CAR.CHEVROLET_BOLT_CC_2017):
      ret.steerActuatorDelay = 0.2
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

      # Bolt-only lateral tuning overrides
      ret.lateralTuning.torque.kp = 1.03
      ret.lateralTuning.torque.ki = 1.07
      ret.lateralTuning.torque.kd = 0.93
      ret.lateralTuning.torque.kfDEPRECATED = 0.02

      if candidate == CAR.CHEVROLET_BOLT_CC_2017:
        gm_safety_cfg.safetyParam |= Panda.FLAG_GM_BOLT_2017

      if ret.enableGasInterceptor:
        # ACC Bolts use pedal for full longitudinal control, not just sng
        ret.flags |= GMFlags.PEDAL_LONG.value

    # Enable pedal interceptor for ACC models when detected
    if is_bolt_2022_2023_pedal:
      ret.flags |= GMFlags.PEDAL_LONG.value
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_NO_ACC
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_BOLT_2022_PEDAL

    if candidate == CAR.CHEVROLET_SILVERADO:
      # On the Bolt, the ECM and camera independently check that you are either above 5 kph or at a stop
      # with foot on brake to allow engagement, but this platform only has that check in the camera.
      # TODO: check if this is split by EV/ICE with more platforms in the future
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate in (CAR.CHEVROLET_EQUINOX, CAR.CHEVROLET_EQUINOX_CC):
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate in (CAR.CHEVROLET_TRAILBLAZER, CAR.CHEVROLET_TRAILBLAZER_CC):
      ret.steerActuatorDelay = 0.2
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate in (CAR.CHEVROLET_SUBURBAN, CAR.CHEVROLET_SUBURBAN_CC):
      ret.steerActuatorDelay = 0.075
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate == CAR.GMC_YUKON_CC:
      ret.steerActuatorDelay = 0.2
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate == CAR.CADILLAC_XT6:
      ret.steerActuatorDelay = 0.2
      ret.minSteerSpeed = 7 * CV.MPH_TO_MS
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate == CAR.CADILLAC_XT4:
      ret.steerActuatorDelay = 0.2
      if not ret.openpilotLongitudinalControl:
        ret.minEnableSpeed = -1.  # engage speed is decided by pcm
      ret.minSteerSpeed = 30 * CV.MPH_TO_MS
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate == CAR.CADILLAC_XT5_CC:
      ret.steerActuatorDelay = 0.2
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate in (CAR.CHEVROLET_TRAVERSE, CAR.CHEVROLET_BLAZER):
      ret.steerActuatorDelay = 0.2
      if not ret.openpilotLongitudinalControl:
        ret.minEnableSpeed = -1.  # engage speed is decided by pcm
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)
      if candidate == CAR.CHEVROLET_BLAZER:
        ret.minEnableSpeed = 5 * CV.KPH_TO_MS

    elif candidate == CAR.BUICK_BABYENCLAVE:
      ret.steerActuatorDelay = 0.2
      if not ret.openpilotLongitudinalControl:
        ret.minEnableSpeed = -1.  # engage speed is decided by pcm
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate == CAR.CADILLAC_CT6_CC:
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate == CAR.CHEVROLET_MALIBU_CC:
      ret.steerActuatorDelay = 0.2
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    elif candidate == CAR.CHEVROLET_TRAX:
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    if ret.enableGasInterceptor and frogpilot_toggles.gm_pedal_longitudinal:
      ret.networkLocation = NetworkLocation.fwdCamera
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_HW_CAM
      ret.minEnableSpeed = -1
      ret.pcmCruise = False
      ret.openpilotLongitudinalControl = not frogpilot_toggles.disable_openpilot_long
      ret.stoppingControl = True
      ret.autoResumeSng = True

      if candidate in CC_ONLY_CAR or (candidate in CAMERA_ACC_CAR and ret.enableGasInterceptor): #pedal interceptor tuning
        ret.flags |= GMFlags.PEDAL_LONG.value
        gm_safety_cfg.safetyParam |= Panda.FLAG_GM_PEDAL_LONG
        # Note: Low speed, stop and go not tested. Should be fairly smooth on highway
        if candidate in (CAR.CHEVROLET_MALIBU_CC, CAR.CHEVROLET_MALIBU_HYBRID_CC):
          ret.longitudinalTuning.kiBP = [0.0, 5., 35.]
          ret.longitudinalTuning.kiV = [0.0, 0.35, 0.5]
          ret.longitudinalTuning.kfDEPRECATED = 0.15
          ret.stoppingDecelRate = 0.8
          ret.minEnableSpeed = -1
          ret.pcmCruise = False
          ret.openpilotLongitudinalControl = not frogpilot_toggles.disable_openpilot_long
        else:
          ret.longitudinalTuning.kiBP = [0., 3., 6., 35.]
          ret.longitudinalTuning.kiV = [0.125, 0.175, 0.225, 0.33]
          ret.longitudinalTuning.kfDEPRECATED = 0.25
          ret.stoppingDecelRate = 0.8
      else:  # Pedal used for SNG, ACC for longitudinal control otherwise
        gm_safety_cfg.safetyParam |= Panda.FLAG_GM_HW_CAM_LONG
        ret.startingState = True
        ret.vEgoStopping = 0.25
        ret.vEgoStarting = 0.25

    if ret.enableGasInterceptor and candidate == CAR.CHEVROLET_MALIBU_HYBRID_CC:
      ret.flags |= GMFlags.PEDAL_LONG.value
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_PEDAL_LONG
      ret.longitudinalTuning.kiBP = [0.0, 5., 35.]
      ret.longitudinalTuning.kiV = [0.0, 0.18, 0.25]
      ret.longitudinalTuning.kfDEPRECATED = 0.15
      ret.stoppingDecelRate = 0.8
      ret.minEnableSpeed = -1
      ret.pcmCruise = False
      ret.openpilotLongitudinalControl = not frogpilot_toggles.disable_openpilot_long

    elif candidate in CC_ONLY_CAR and not ret.enableGasInterceptor:
      ret.flags |= GMFlags.CC_LONG.value
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_CC_LONG
      ret.radarUnavailable = True
      ret.experimentalLongitudinalAvailable = False
      ret.minEnableSpeed = 24 * CV.MPH_TO_MS
      ret.openpilotLongitudinalControl = not frogpilot_toggles.disable_openpilot_long
      ret.pcmCruise = False

      if not ret.enableGasInterceptor and candidate in CC_ONLY_CAR: #redneck tuning
        if candidate == CAR.CHEVROLET_MALIBU_HYBRID_CC:
          pass
        else:
          ret.longitudinalTuning.kpBP = [10.7, 10.8, 28.]  # 10.7 m/s == 24 mph
          ret.longitudinalTuning.kpV = [0., 5., 2.]  # set lower end to 0 since we can't drive below that speed
          ret.longitudinalTuning.deadzoneBP = [0., 1.]
          ret.longitudinalTuning.deadzoneV = [0.9, 0.9]  # == 2 km/h/s, 1.25 mph/s
          ret.longitudinalActuatorDelay = 1.  # TODO: measure this
          if candidate == CAR.CHEVROLET_MALIBU_CC:
            ret.longitudinalTuning.kpV = [0., 20., 20.]
          ret.longitudinalTuning.kiBP = [0.]
          ret.longitudinalTuning.kiV = [0.1]
          ret.stoppingDecelRate = 11.18  # == 25 mph/s (.04 rate)

    if candidate in CC_ONLY_CAR:
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_NO_ACC

    # Exception for flashed cars, or cars whose camera was removed
    if (ret.networkLocation == NetworkLocation.fwdCamera or candidate in CC_ONLY_CAR) and CAM_MSG not in fingerprint.get(CanBus.CAMERA, {}) and candidate not in SDGM_CAR:
      ret.flags |= GMFlags.NO_CAMERA.value
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_NO_CAMERA

    if ACCELERATOR_POS_MSG not in fingerprint.get(CanBus.POWERTRAIN, {}):
      ret.flags |= GMFlags.NO_ACCELERATOR_POS_MSG.value

    use_panda_3d1_sched = (
      ret.openpilotLongitudinalControl and
      ret.enableGasInterceptor and
      bool(ret.flags & GMFlags.PEDAL_LONG.value) and
      candidate in CC_ONLY_CAR and
      candidate != CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL
    )
    if use_panda_3d1_sched:
      gm_safety_cfg.safetyParam |= Panda.FLAG_GM_PANDA_3D1_SCHED

    return ret

  # returns a car.CarState
  def _update(self, c, frogpilot_toggles):
    ret, fp_ret = self.CS.update(self.cp, self.cp_cam, self.cp_loopback, frogpilot_toggles)

    # Don't add event if transitioning from INIT, unless it's to an actual button
    if self.CS.cruise_buttons != CruiseButtons.UNPRESS or self.CS.prev_cruise_buttons != CruiseButtons.INIT:
      ret.buttonEvents = [
        *create_button_events(self.CS.cruise_buttons, self.CS.prev_cruise_buttons, BUTTONS_DICT,
                              unpressed_btn=CruiseButtons.UNPRESS),
        *create_button_events(self.CS.distance_button, self.CS.prev_distance_button,
                              {1: ButtonType.gapAdjustCruise}),
        *create_button_events(self.CS.lkas_enabled, self.CS.lkas_previously_enabled,
                              {1: FrogPilotButtonType.lkas}),
      ]

    # The ECM allows enabling on falling edge of set, but only rising edge of resume
    events = self.create_common_events(ret, extra_gears=[GearShifter.sport, GearShifter.low,
                                                         GearShifter.eco, GearShifter.manumatic],
                                       pcm_enable=self.CP.pcmCruise, enable_buttons=(ButtonType.decelCruise,))
    if not self.CP.pcmCruise:
      if any(b.type == ButtonType.accelCruise and b.pressed for b in ret.buttonEvents):
        events.add(EventName.buttonEnable)

    # Enabling at a standstill with brake is allowed
    # TODO: verify 17 Volt can enable for the first time at a stop and allow for all GMs
    below_min_enable_speed = ret.vEgo < self.CP.minEnableSpeed or self.CS.moving_backward
    if below_min_enable_speed and not (ret.standstill and ret.brake >= 20 and
                                       (self.CP.networkLocation == NetworkLocation.fwdCamera and
                                        (self.CP.carFingerprint in VOLT_LIKE_CARS or self.CP.carFingerprint in {CAR.CHEVROLET_BLAZER, CAR.CHEVROLET_MALIBU_SDGM, CAR.CHEVROLET_TRAVERSE} or self.CP.carFingerprint not in SDGM_CAR))):
      events.add(EventName.belowEngageSpeed)
    if ret.cruiseState.standstill and not self.CP.autoResumeSng:
      events.add(EventName.resumeRequired)
    if ret.vEgo < self.CP.minSteerSpeed:
      events.add(EventName.belowSteerSpeed)

    if (self.CP.flags & GMFlags.CC_LONG.value) and ret.vEgo < self.CP.minEnableSpeed:
      if ret.cruiseState.enabled or self.CS.out.cruiseState.enabled:
        events.add(EventName.speedTooLow)

    if (self.CP.flags & GMFlags.PEDAL_LONG.value) and \
      self.CP.transmissionType == TransmissionType.direct and \
      self.CP.carFingerprint != CAR.CHEVROLET_MALIBU_HYBRID_CC and \
      not self.CS.single_pedal_mode and \
      c.longActive:
      events.add(FrogPilotEventName.pedalInterceptorNoBrake)

    if self.CS.lkas_status == 3:
      events.add(EventName.steerUnavailable)

    ret.events = events.to_msg()

    return ret, fp_ret
