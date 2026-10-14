import numpy as np
from opendbc.car import rate_limit

RAY_PEDAL_COMMAND_CAP = 0.70
RAY_PEDAL_CAP_SPEED_BP = [0.0, 12.0, 20.0, 25.0]
RAY_PEDAL_CAP_V = [0.55, 0.55, 0.65, RAY_PEDAL_COMMAND_CAP]
RAY_PEDAL_OFFSET_SPEED_BP = [0.0, 2.0, 4.0, 8.0, 12.0, 16.0, 20.0, 25.0]
RAY_PEDAL_OFFSET_V = [0.08, 0.13, 0.20, 0.32, 0.42, 0.51, 0.565, 0.60]
RAY_PEDAL_ACCEL_GAIN = 0.22
RAY_PEDAL_DECEL_GAIN = 0.55
RAY_PEDAL_RATE_UP = 0.02
RAY_PEDAL_RATE_DOWN = 0.06
RAY_PEDAL_OVERSPEED_CUTOFF = 0.5
RAY_PEDAL_TAPER_BELOW_TARGET = 0.75


def ray_pedal_enabled(CP):
  from opendbc.car.hyundai.values import CAR, RAY_PEDAL_SAFETY_PARAM
  from opendbc.car import structs
  return (CP.brand == "hyundai" and CP.carFingerprint == CAR.KIA_RAY_EV and CP.openpilotLongitudinalControl and
          not CP.passive and not CP.dashcamOnly and not CP.notCar and len(CP.safetyConfigs) == 1 and
          CP.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.hyundai and
          CP.safetyConfigs[0].safetyParam == RAY_PEDAL_SAFETY_PARAM)


def pedal_checksum(address, sig, data):
  crc = 0xFF
  for value in reversed(data[:-1]):
    crc ^= value
    for _ in range(8):
      crc = ((crc << 1) ^ 0xD5) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
  return crc


def create_ray_pedal_command(packer, gas_amount, idx):
  enable = gas_amount > 0.001
  values = {"ENABLE": enable, "COUNTER_PEDAL": idx & 0xF}
  if enable:
    values.update(GAS_COMMAND=gas_amount * 255., GAS_COMMAND2=gas_amount * 255.)
  return packer.make_can_msg("GAS_COMMAND", 0, values)


def get_ray_pedal_target(accel, speed, set_speed):
  if not all(np.isfinite(x) for x in (accel, speed, set_speed)) or not 1.0 <= set_speed <= 40.0:
    return 0.0
  speed_error = set_speed - speed
  if speed_error <= -RAY_PEDAL_OVERSPEED_CUTOFF:
    return 0.0
  pedal_offset = float(np.interp(speed, RAY_PEDAL_OFFSET_SPEED_BP, RAY_PEDAL_OFFSET_V))
  pedal_cap = float(np.interp(speed, RAY_PEDAL_CAP_SPEED_BP, RAY_PEDAL_CAP_V))
  gain = RAY_PEDAL_DECEL_GAIN if accel < 0.0 else RAY_PEDAL_ACCEL_GAIN
  target = float(np.clip(pedal_offset + accel * gain, 0.0, pedal_cap))
  if speed_error < 0.0:
    target *= float(np.clip(0.65 * (1.0 + speed_error / RAY_PEDAL_OVERSPEED_CUTOFF), 0.0, 1.0))
  elif speed_error < RAY_PEDAL_TAPER_BELOW_TARGET:
    target *= 0.65 + 0.35 * speed_error / RAY_PEDAL_TAPER_BELOW_TARGET
  return target


def ray_pedal_gas(last, speed, accel, set_speed):
  target = get_ray_pedal_target(accel, speed, set_speed)
  if target <= 0.001:
    return 0.0
  return min(rate_limit(target, last, -RAY_PEDAL_RATE_DOWN, RAY_PEDAL_RATE_UP), target)


class RayPedalLongitudinalPolicy:
  """Own the selected Ray proportional gains and consume its supported factory integral gains."""

  friction_variant = False
  stopping_decel_rate = 1.0

  def __init__(self, cp):
    self.kp = ((0.0, 5.0, 15.0, 35.0), (0.095, 0.085, 0.065, 0.050))
    self.ki = (tuple(cp.longitudinalTuning.kiBP), tuple(cp.longitudinalTuning.kiV))

  def reset(self):
    pass

  def feedforward(self, target, _speed, _last_output):
    return target

  def prepare_pid(self, _pid, _target, _error, _speed, _last_output, _limits, *, should_stop, has_lead):
    return False

  def shape_output(self, output, _target, _error, _speed):
    return output


def longitudinal_policy_for(cp):
  return RayPedalLongitudinalPolicy(cp) if ray_pedal_enabled(cp) else None
