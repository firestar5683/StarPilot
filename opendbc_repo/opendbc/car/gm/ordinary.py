"""Ordinary GM interception demand in normalized GM wire units."""

import math
import numpy as np


def demands(accel, speed, orientation, cp, *, min_gas=-650, max_gas=2041, inactive_gas=-650, brake_threshold=-0.1, stop_speed=0.25):
  pitch = 0.0
  if orientation is not None and len(orientation) == 3 and speed > stop_speed and math.isfinite(orientation[1]):
    pitch = math.sin(orientation[1]) * 9.81
    pitch = 0.0 if pitch > 0.0 and accel > 0.0 else min(pitch, 0.20)
  radius = 0.075 * cp.wheelbase + 0.1453
  frontal = 1.05 * cp.wheelbase + 0.0679
  command = float(np.clip(accel + pitch, -4.0, 2.0))
  torque = radius * (cp.mass * command + 0.5 * 0.30 * frontal * 1.225 * speed ** 2)
  gas = int(round(np.clip(torque + 6150, min_gas + 6150, max_gas + 6150))) - 6150
  brake = int(round(np.interp(min(torque / (radius * cp.mass), 0), [-4.0, brake_threshold], [400, 0])))
  return (inactive_gas if brake > 0 else gas), brake
