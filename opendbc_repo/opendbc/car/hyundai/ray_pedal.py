import numpy as np
from opendbc.car import rate_limit

RAY_PEDAL_COMMAND_CAP = 0.55
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


def ray_pedal_gas(last, speed, accel, set_speed):
  if not np.isfinite(set_speed) or not 1.0 <= set_speed <= 40.0:
    return 0.0
  speed_error = set_speed - speed
  if speed_error <= -RAY_PEDAL_OVERSPEED_CUTOFF:
    return 0.0
  pedal_offset = float(np.interp(speed, [0., 2., 4., 8., 12., 20.], [0.08, 0.13, 0.20, 0.32, 0.42, 0.48]))
  target = float(np.clip(pedal_offset + accel * (2.0 if accel < 0.0 else 0.22), 0.0, RAY_PEDAL_COMMAND_CAP))
  if speed_error < 0.0:
    target *= float(np.clip(0.65 * (1.0 + speed_error / RAY_PEDAL_OVERSPEED_CUTOFF), 0.0, 1.0))
  elif speed_error < RAY_PEDAL_TAPER_BELOW_TARGET:
    target *= 0.65 + 0.35 * speed_error / RAY_PEDAL_TAPER_BELOW_TARGET
  if target <= 0.001:
    return 0.0
  return min(rate_limit(target, last, -RAY_PEDAL_RATE_DOWN, RAY_PEDAL_RATE_UP), target)
