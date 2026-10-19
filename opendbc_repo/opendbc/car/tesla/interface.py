from opendbc.car import Bus, get_safety_config, structs
from opendbc.car.interfaces import CarInterfaceBase
from opendbc.car.tesla.carcontroller import CarController
from opendbc.car.tesla.carstate import CarState
from opendbc.car.tesla.radar_interface import RadarInterface
from opendbc.car.tesla.values import TeslaFlags, TeslaSafetyFlags, CANBUS, CAR, DBC, LEGACY_CARS
from opendbc.car.tesla.preap.interface import get_preap_accel_limits, get_preap_params


class CarInterface(CarInterfaceBase):
  CarState = CarState
  CarController = CarController
  RadarInterface = RadarInterface

  @staticmethod
  def get_pid_accel_limits(CP, current_speed, cruise_speed):
    if CP.carFingerprint == CAR.TESLA_MODEL_S_PREAP:
      return get_preap_accel_limits(current_speed)
    return CarInterfaceBase.get_pid_accel_limits(CP, current_speed, cruise_speed)

  @classmethod
  def get_params(cls, candidate, fingerprint, car_fw, alpha_long, is_release, docs, starpilot_toggles):
    ret = super().get_params(candidate, fingerprint, car_fw, alpha_long, is_release, docs, starpilot_toggles)
    if candidate == CAR.TESLA_MODEL_3 and getattr(starpilot_toggles, "tesla_cooperative_steering", False):
      ret.safetyConfigs[0].safetyParam |= TeslaSafetyFlags.COOP_STEERING.value
    if (ret.flags & TeslaFlags.HAS_VEHICLE_BUS and
        getattr(starpilot_toggles, "tesla_aol_screen_tap_requested", False)):
      ret.flags |= TeslaFlags.AOL_SCREEN_BUTTON.value
      ret.safetyConfigs[0].safetyParam |= TeslaSafetyFlags.AOL_SCREEN_BUTTON.value
      if getattr(starpilot_toggles, "tesla_aol_screen_brake_disengage_requested", False):
        ret.safetyConfigs[0].safetyParam |= TeslaSafetyFlags.AOL_SCREEN_DISENGAGE_ON_BRAKE.value
    return ret

  @staticmethod
  def _get_params(ret: structs.CarParams, candidate, fingerprint, car_fw, alpha_long, is_release, docs) -> structs.CarParams:
    ret.brand = "tesla"

    if candidate == CAR.TESLA_MODEL_S_PREAP:
      return get_preap_params(ret)

    if candidate in LEGACY_CARS:
      ret.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.tesla, TeslaSafetyFlags.FLAG_HW1.value)]
      ret.steerLimitTimer = 0.4
      ret.steerActuatorDelay = 0.1
      ret.steerAtStandstill = True
      ret.steerControlType = structs.CarParams.SteerControlType.angle
      ret.radarUnavailable = Bus.radar not in DBC[candidate]
      ret.radarTimeStepDEPRECATED = 0.125
      ret.alphaLongitudinalAvailable = True

      if alpha_long:
        ret.openpilotLongitudinalControl = True
        ret.safetyConfigs[0].safetyParam |= TeslaSafetyFlags.LONG_CONTROL.value
      return ret

    ret.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.tesla)]

    if candidate in (CAR.TESLA_MODEL_3, CAR.TESLA_MODEL_Y) and fingerprint[CANBUS.vehicle].get(0x3DF) == 8:
      ret.flags |= TeslaFlags.HAS_VEHICLE_BUS.value

    ret.steerLimitTimer = 0.4
    ret.steerActuatorDelay = 0.1
    ret.steerAtStandstill = True

    ret.steerControlType = structs.CarParams.SteerControlType.angle
    ret.radarUnavailable = True

    ret.alphaLongitudinalAvailable = True
    if alpha_long:
      ret.openpilotLongitudinalControl = True
      ret.safetyConfigs[0].safetyParam |= TeslaSafetyFlags.LONG_CONTROL.value

      ret.vEgoStopping = 0.1
      ret.vEgoStarting = 0.1
      ret.stoppingDecelRate = 0.3

    ret.dashcamOnly = candidate in (CAR.TESLA_MODEL_X) # dashcam only, pending find invalidLkasSetting signal

    return ret
