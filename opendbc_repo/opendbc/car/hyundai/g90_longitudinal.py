import numpy as np

from opendbc.car.structs import CarControl
from opendbc.car.hyundai.values import CAR

LongCtrlState = CarControl.Actuators.LongControlState

HOLD_SPEED = (0.0, 0.03, 0.08, 0.16, 0.3, 0.5, 0.8, 1.2, 2.0, 3.0)
HOLD_ACCEL = (-0.10, -0.10, -0.12, -0.18, -0.30, -0.50, -0.75, -1.00, -1.40, -1.80)
RELAX_SPEED = (0.0, 0.08, 0.16, 0.3, 0.5, 0.8, 1.2, 2.0, 3.0)
RELAX_STEP = (0.10, 0.10, 0.08, 0.06, 0.04, 0.035, 0.03, 0.022, 0.018)
RELEASE_SPEED = (0.0, 0.3, 0.6)
RELEASE_ACCEL_STEP = (0.05, 0.07, 0.11)
RELEASE_DECEL_STEP = (0.16, 0.18, 0.18)
RELEASE_MAX_SPEED = 0.8


def stopping_decel_rate(cp):
  return 0.55 if cp.carFingerprint == CAR.GENESIS_G90 and cp.openpilotLongitudinalControl else None


def forecast_should_stop(cp, speeds, time_indices, action_t):
  """G90's original two-horizon stopping decision; no acceleration shaping."""
  if cp.carFingerprint != CAR.GENESIS_G90 or not cp.openpilotLongitudinalControl:
    return None
  if len(speeds) == len(time_indices):
    target = np.interp(action_t, time_indices, speeds)
    target_one_second = np.interp(action_t + 1.0, time_indices, speeds)
  else:
    target = target_one_second = 0.0
  # The original CarParams field was Float32 before its planner toggle copy.
  threshold = float(np.float32(0.8))
  return bool(target < threshold and target_one_second < threshold)


class G90LongitudinalPolicy:
  """G90 stop hold and launch shaping at the controller's 100 Hz cadence."""

  def __init__(self):
    self.actual_accel = 0.0
    self.release_active = False
    self.last_state = LongCtrlState.off

  def update(self, accel, speed, state, active):
    if not active:
      self.actual_accel = 0.0
      self.release_active = False
    elif state == LongCtrlState.stopping and speed <= HOLD_SPEED[-1]:
      self.release_active = False
      target = min(0.0, max(accel, float(np.interp(speed, HOLD_SPEED, HOLD_ACCEL))))
      if self.actual_accel < target:
        self.actual_accel = min(self.actual_accel + float(np.interp(speed, RELAX_SPEED, RELAX_STEP)), target)
      else:
        self.actual_accel = target
    else:
      if self.last_state == LongCtrlState.stopping and state == LongCtrlState.pid and accel > 0.0 and speed < RELEASE_MAX_SPEED:
        self.release_active = True
      if self.release_active:
        accel_step = float(np.interp(speed, RELEASE_SPEED, RELEASE_ACCEL_STEP))
        decel_step = float(np.interp(speed, RELEASE_SPEED, RELEASE_DECEL_STEP))
        self.actual_accel = float(np.clip(accel, self.actual_accel - decel_step, self.actual_accel + accel_step))
        if speed >= RELEASE_MAX_SPEED or accel <= 0.0 or self.actual_accel >= accel - 1e-3:
          self.release_active = False
      else:
        self.actual_accel = accel
    self.last_state = state
    return self.actual_accel
