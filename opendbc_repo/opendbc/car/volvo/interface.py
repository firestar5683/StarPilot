from opendbc.car import structs, get_safety_config
from opendbc.car.interfaces import CarInterfaceBase
from opendbc.car.volvo.carstate import CarState
from opendbc.car.volvo.carcontroller import CarController
from opendbc.car.volvo.values import VolvoSafetyFlags


class CarInterface(CarInterfaceBase):
  CarState = CarState
  CarController = CarController

  @staticmethod
  def _get_params(ret, candidate, fingerprint, car_fw, alpha_long, is_release, docs):
    ret.brand = 'volvo'
    ret.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.volvo, VolvoSafetyFlags.C1.value)]
    ret.steerActuatorDelay = 0.2
    ret.steerLimitTimer = 0.1
    ret.steerAtStandstill = False
    ret.steerControlType = structs.CarParams.SteerControlType.angle
    ret.radarUnavailable = True
    ret.alphaLongitudinalAvailable = False
    ret.pcmCruise = True
    ret.transmissionType = structs.CarParams.TransmissionType.automatic
    return ret
