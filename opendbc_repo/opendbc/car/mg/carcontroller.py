from opendbc.can.packer import CANPacker
from opendbc.car import Bus
from opendbc.car.lateral import apply_driver_steer_torque_limits
from opendbc.car.interfaces import CarControllerBase
from opendbc.car.mg.mgcan import create_lka_steering
from opendbc.car.mg.values import CarControllerParams


class CarController(CarControllerBase):
  def __init__(self, dbc_names, CP):
    super().__init__(dbc_names, CP)
    self.packer = CANPacker(dbc_names[Bus.pt])

    self.apply_torque_last = 0

  def update(self, CC, CS, now_nanos):
    _projection = self.learning_projection_observer
    if _projection is not None:
      _projection.begin(CC.actuators.torque, self.frame)
    actuators = CC.actuators
    can_sends = []

    # steering command
    if self.frame % CarControllerParams.STEER_STEP == 0:
      if CC.latActive:
        new_torque = int(round(actuators.torque * CarControllerParams.STEER_MAX))
        if _projection is not None:
          _projection.input(new_torque, CarControllerParams.STEER_MAX, self.apply_torque_last, CS.out.steeringTorque, CarControllerParams, limiter='driver')
        apply_torque = apply_driver_steer_torque_limits(new_torque, self.apply_torque_last, CS.out.steeringTorque, CarControllerParams)
      else:
        apply_torque = 0

      self.apply_torque_last = apply_torque
      can_sends.append(create_lka_steering(self.packer, (self.frame // CarControllerParams.STEER_STEP) % 16, apply_torque, CC.latActive))
      if _projection is not None:
        _projection.emit('mg.FVCM_HSC2_FrP03', apply_torque, CC.latActive, can_sends[-1])

    new_actuators = actuators.as_builder()
    new_actuators.torque = self.apply_torque_last / CarControllerParams.STEER_MAX
    new_actuators.torqueOutputCan = self.apply_torque_last

    self.frame += 1
    if _projection is not None:
      _projection.finish(new_actuators.torque)
    return new_actuators, can_sends
