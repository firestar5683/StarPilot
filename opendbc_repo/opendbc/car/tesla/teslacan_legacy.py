from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.interfaces import V_CRUISE_MAX
from opendbc.car.tesla.values import CANBUS, CarControllerParams


class ModelSHW1CAN:
  """Legacy Model S command encoding, separate from modern FSD protocols."""

  def __init__(self, packer):
    self.packer = packer
    self.jerk_upper = CarControllerParams.JERK_LIMIT_MAX
    self.jerk_lower = CarControllerParams.JERK_LIMIT_MIN

  @staticmethod
  def checksum(address, data):
    return ((address & 0xFF) + ((address >> 8) & 0xFF) + sum(data)) & 0xFF

  def _command(self, name, values, checksum_signal):
    address, data, _ = self.packer.make_can_msg(name, CANBUS.party, values)
    values[checksum_signal] = self.checksum(address, data[:-1])
    return self.packer.make_can_msg(name, CANBUS.party, values)

  def create_steering_control(self, counter, angle, enabled):
    return self._command("DAS_steeringControl", {
      "DAS_steeringControlCounter": counter % 16,
      "DAS_steeringAngleRequest": -angle,
      "DAS_steeringHapticRequest": 0,
      "DAS_steeringControlType": 1 if enabled else 0,
    }, "DAS_steeringControlChecksum")

  def create_longitudinal_command(self, acc_state, accel, counter, v_ego, active, gas_pressed):
    active = active and acc_state != 13
    accel = min(max(accel, CarControllerParams.ACCEL_MIN), CarControllerParams.ACCEL_MAX) if active else 0.0
    set_speed = (0 if accel < 0 else V_CRUISE_MAX) if active else max(v_ego * CV.MS_TO_KPH, 0)
    if gas_pressed:
      self.jerk_upper = self.jerk_lower = 0.0
    else:
      # The legacy ramp advances once per 25 Hz command, including after gas release.
      step = CarControllerParams.JERK_LIMIT_MAX * 0.002
      self.jerk_lower = max(self.jerk_lower - step, CarControllerParams.JERK_LIMIT_MIN)
      self.jerk_upper = min(self.jerk_upper + step, CarControllerParams.JERK_LIMIT_MAX)
    return self._command("DAS_control", {
      "DAS_setSpeed": set_speed,
      "DAS_accState": acc_state,
      "DAS_aebEvent": 0,
      "DAS_jerkMin": self.jerk_lower,
      "DAS_jerkMax": self.jerk_upper,
      "DAS_accelMin": accel,
      "DAS_accelMax": max(accel, 0),
      "DAS_controlCounter": counter % 8,
    }, "DAS_controlChecksum")
