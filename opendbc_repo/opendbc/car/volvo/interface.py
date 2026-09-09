from opendbc.car import structs, get_safety_config
from opendbc.car.interfaces import CarInterfaceBase
from opendbc.car.volvo.carcontroller import CarController
from opendbc.car.volvo.carstate import CarState
from opendbc.car.volvo.values import CAR, VolvoC1PlatformConfig, VolvoSafetyFlags, VolvoSPAPlatformConfig

TransmissionType = structs.CarParams.TransmissionType

SAFETY_VOLVO = structs.CarParams.SafetyModel.volvo


class CarInterface(CarInterfaceBase):
  CarState = CarState
  CarController = CarController

  @staticmethod
  def _get_params(ret: structs.CarParams, candidate, fingerprint, car_fw, alpha_long, is_release, docs) -> structs.CarParams:
    ret.brand = 'volvo'

    platform = CAR(candidate).config
    safety_param = 0
    if isinstance(platform, VolvoSPAPlatformConfig):
      safety_param = VolvoSafetyFlags.SPA.value
    elif isinstance(platform, VolvoC1PlatformConfig):
      safety_param = VolvoSafetyFlags.C1.value
    ret.safetyConfigs = [get_safety_config(SAFETY_VOLVO, safety_param)]
    #ret.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.noOutput)]

    ret.dashcamOnly = False

    ret.steerActuatorDelay = 0.2 if isinstance(platform, VolvoC1PlatformConfig) else 0.3
    ret.steerLimitTimer = 0.1
    ret.steerAtStandstill = not isinstance(platform, VolvoC1PlatformConfig)

    # Use angle-based steering control for Volvo CMA platform
    ret.steerControlType = structs.CarParams.SteerControlType.angle
    # Note: No lateral tuning configuration needed for basic angle control
    ret.radarUnavailable = True

    ret.alphaLongitudinalAvailable = False

    ret.pcmCruise = True

    if isinstance(platform, VolvoC1PlatformConfig):
      ret.transmissionType = TransmissionType.automatic

    return ret
