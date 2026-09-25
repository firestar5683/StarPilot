from opendbc.car import Bus, structs, get_safety_config, uds
from opendbc.car.toyota.carstate import CarState
from opendbc.car.toyota.carcontroller import CarController
from opendbc.car.toyota.radar_interface import RadarInterface
from opendbc.car.toyota.values import Ecu, CAR, DBC, ToyotaFlags, CarControllerParams, MIN_ACC_SPEED, \
                                                  EPS_SCALE, ToyotaSafetyFlags, TOYOTA_AUTO_HOLD_CARS, TOYOTA_AUTO_HOLD_AEB_CARS
from opendbc.car.disable_ecu import disable_ecu
from opendbc.car.interfaces import CarInterfaceBase
from opendbc.safety import ALTERNATIVE_EXPERIENCE

SteerControlType = structs.CarParams.SteerControlType


def toyota_auto_hold_supported(CP) -> bool:
  return bool(CP.brand == "toyota" and CP.carFingerprint in TOYOTA_AUTO_HOLD_CARS and
              CP.openpilotLongitudinalControl and not CP.flags & ToyotaFlags.SECOC and
              not CP.notCar and not CP.dashcamOnly and not CP.passive and len(CP.safetyConfigs) == 1 and
              CP.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.toyota and
              (CP.safetyConfigs[0].safetyParam & 0xFF) == EPS_SCALE[CP.carFingerprint] and
              not CP.safetyConfigs[0].safetyParam & ~(0xFF | int(ToyotaSafetyFlags.ALT_BRAKE) | int(ToyotaSafetyFlags.LTA)))


def apply_toyota_auto_hold(CP, enabled: bool) -> bool:
  if CP.brand != "toyota":
    return False
  CP.flags &= ~int(ToyotaFlags.AUTO_BRAKE_HOLD)
  CP.alternativeExperience &= ~(ALTERNATIVE_EXPERIENCE.TOYOTA_AUTO_HOLD | ALTERNATIVE_EXPERIENCE.TOYOTA_AEB_HOLD)
  admitted = enabled and toyota_auto_hold_supported(CP)
  if admitted:
    CP.flags |= int(ToyotaFlags.AUTO_BRAKE_HOLD)
    CP.alternativeExperience |= (ALTERNATIVE_EXPERIENCE.TOYOTA_AEB_HOLD if CP.carFingerprint in TOYOTA_AUTO_HOLD_AEB_CARS
                                 else ALTERNATIVE_EXPERIENCE.TOYOTA_AUTO_HOLD)
  return bool(admitted)


class CarInterface(CarInterfaceBase):
  CarState = CarState
  CarController = CarController
  RadarInterface = RadarInterface

  DRIVABLE_GEARS = (structs.CarState.GearShifter.sport,)

  @staticmethod
  def get_pid_accel_limits(CP, current_speed, cruise_speed):
    return CarControllerParams(CP).ACCEL_MIN, CarControllerParams(CP).ACCEL_MAX

  @staticmethod
  def _get_params(ret: structs.CarParams, candidate, fingerprint, car_fw, alpha_long, is_release, docs) -> structs.CarParams:
    ret.brand = "toyota"
    ret.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.toyota)]
    ret.safetyConfigs[0].safetyParam = EPS_SCALE[candidate]

    # BRAKE_MODULE is on a different address for these cars
    if DBC[candidate][Bus.pt] == "toyota_new_mc_pt_generated":
      ret.safetyConfigs[0].safetyParam |= ToyotaSafetyFlags.ALT_BRAKE.value

    if ret.flags & ToyotaFlags.SECOC.value:
      ret.secOcRequired = True
      ret.safetyConfigs[0].safetyParam |= ToyotaSafetyFlags.SECOC.value
      ret.dashcamOnly = is_release

    if ret.flags & ToyotaFlags.ANGLE_CONTROL:
      ret.steerControlType = SteerControlType.angle
      ret.safetyConfigs[0].safetyParam |= ToyotaSafetyFlags.LTA.value

      # LTA control can be more delayed and winds up more often
      ret.steerActuatorDelay = 0.18
      ret.steerLimitTimer = 0.8
    else:
      CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

      ret.steerActuatorDelay = 0.12  # Default delay, Prius has larger delay
      ret.steerLimitTimer = 0.4

    stop_and_go = bool(ret.flags & ToyotaFlags.TSS2)

    # In TSS2 cars, the camera does long control
    found_ecus = [fw.ecu for fw in car_fw]

    if Ecu.hybrid in found_ecus:
      ret.flags |= ToyotaFlags.HYBRID.value

    if candidate in (CAR.TOYOTA_PRIUS, CAR.TOYOTA_PRIUS_RETROFIT):
      stop_and_go = True
      if candidate == CAR.TOYOTA_PRIUS_RETROFIT:
        ret.flags |= ToyotaFlags.HYBRID.value
      # Only give steer angle deadzone to for bad angle sensor prius
      for fw in car_fw:
        if fw.ecu == "eps" and not fw.fwVersion == b'8965B47060\x00\x00\x00\x00\x00\x00':
          retrofit = candidate == CAR.TOYOTA_PRIUS_RETROFIT
          ret.steerActuatorDelay = 0.14 if retrofit else 0.25
          CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning, steering_angle_deadzone_deg=0.3 if retrofit else 0.2)
        # 2021+ TSS2 steering rack swapped into a TSS-P car, not supported
        if candidate == CAR.TOYOTA_PRIUS and fw.ecu == "eps" and fw.fwVersion == b'8965B47070\x00\x00\x00\x00\x00\x00':
          ret.dashcamOnly = True

    elif candidate in (CAR.LEXUS_RX, CAR.LEXUS_RX_TSS2):
      stop_and_go = True
      ret.wheelSpeedFactor = 1.035

    elif candidate in (CAR.TOYOTA_AVALON, CAR.TOYOTA_AVALON_2019, CAR.TOYOTA_AVALON_TSS2):
      # starting from 2019, all Avalon variants have stop and go
      # https://engage.toyota.com/static/images/toyota_safety_sense/TSS_Applicability_Chart.pdf
      stop_and_go = candidate != CAR.TOYOTA_AVALON

    elif candidate in (CAR.TOYOTA_CHR, CAR.TOYOTA_CAMRY, CAR.TOYOTA_SIENNA, CAR.LEXUS_CTH, CAR.LEXUS_LS, CAR.LEXUS_NX):
      # TODO: Some of these platforms are not advertised to have full range ACC, do they really all have sng?
      stop_and_go = True

    ret.centerToFront = ret.wheelbase * 0.44

    # TODO: Some TSS-P platforms have BSM, but are flipped based on region or driving direction.
    # Detect flipped signals and enable for C-HR and others
    if 0x3F6 in fingerprint[0] and ret.flags & ToyotaFlags.TSS2:
      ret.flags |= ToyotaFlags.HAS_BSM.value

    ret.radarUnavailable = Bus.radar not in DBC[candidate]

    # since we don't yet parse radar on TSS2 radar-based ACC cars, gate longitudinal behind alpha toggle
    if ret.flags & ToyotaFlags.RADAR_ACC:
      ret.alphaLongitudinalAvailable = True

      if alpha_long:
        ret.flags |= ToyotaFlags.DISABLE_RADAR.value

    # openpilot longitudinal enabled by default:
    #  - TSS2 cars with camera sending ACC_CONTROL where we can block it
    # openpilot longitudinal behind alpha long toggle:
    #  - TSS2 radar ACC cars (disables radar)

    ret.openpilotLongitudinalControl = ((bool(ret.flags & ToyotaFlags.TSS2) and not (ret.flags & ToyotaFlags.RADAR_ACC)) or
                                        bool(ret.flags & ToyotaFlags.DISABLE_RADAR.value))

    if candidate in (CAR.TOYOTA_MATRIX_RETROFIT, CAR.TOYOTA_PRIUS_RETROFIT):
      # These manually selected retrofits currently own stock PCM longitudinal.
      # Observed takeover hardware needs its paired controller/native port.
      camera_fp = fingerprint.get(2, {})
      late_camera = candidate == CAR.TOYOTA_PRIUS_RETROFIT and any(
        fw.ecu == Ecu.fwdCamera and bytes(fw.fwVersion).startswith(b"8646F4705") for fw in car_fw)
      bypass = 0x343 in camera_fp or 0x4CB in camera_fp
      if late_camera:
        bypass = ((0x343 in camera_fp and not any(0x343 in fingerprint.get(bus, {}) for bus in (0, 1))) or
                  (0x4CB in camera_fp and 0x4CB not in fingerprint[0]))
      takeover = 0x2FF in fingerprint[0] or bypass
      if takeover:
        ret.dashcamOnly = True
      ret.openpilotLongitudinalControl = False
      ret.alphaLongitudinalAvailable = False

    ret.autoResumeSng = ret.openpilotLongitudinalControl

    if not ret.openpilotLongitudinalControl:
      ret.safetyConfigs[0].safetyParam |= ToyotaSafetyFlags.STOCK_LONGITUDINAL.value

    # min speed to enable ACC. if car can do stop and go, then set enabling speed
    # to a negative value, so it won't matter.
    ret.minEnableSpeed = -1. if stop_and_go else MIN_ACC_SPEED

    if ret.flags & ToyotaFlags.TSS2:
      ret.flags |= ToyotaFlags.RAISED_ACCEL_LIMIT.value

      # Hybrids have much quicker longitudinal actuator response
      if ret.flags & ToyotaFlags.HYBRID.value:
        ret.longitudinalActuatorDelay = 0.05

    return ret

  @staticmethod
  def init(CP, can_recv, can_send, communication_control=None):
    # disable radar if alpha longitudinal toggled on radar-ACC car
    if CP.flags & ToyotaFlags.DISABLE_RADAR.value:
      if communication_control is None:
        communication_control = bytes([uds.SERVICE_TYPE.COMMUNICATION_CONTROL, uds.CONTROL_TYPE.ENABLE_RX_DISABLE_TX, uds.MESSAGE_TYPE.NORMAL])
      disable_ecu(can_recv, can_send, bus=0, addr=0x750, sub_addr=0xf, com_cont_req=communication_control)

  @staticmethod
  def deinit(CP, can_recv, can_send):
    # re-enable radar if alpha longitudinal toggled on radar-ACC car
    communication_control = bytes([uds.SERVICE_TYPE.COMMUNICATION_CONTROL, uds.CONTROL_TYPE.ENABLE_RX_ENABLE_TX, uds.MESSAGE_TYPE.NORMAL])
    CarInterface.init(CP, can_recv, can_send, communication_control)
