"""Reached mixed-Palisade stopping behavior from pinned original 86599a27."""
import numpy as np

from opendbc.car.structs import car
from opendbc.car.hyundai import blended_longitudinal
from opendbc.car.hyundai.values import HyundaiFlags
from opendbc.car.hyundai.longitudinal_mode import HKGModePolicy

LongCtrlState = car.CarControl.Actuators.LongControlState


def eligible(cp):
  if not blended_longitudinal.BLENDED_ALPHA_STARTUP_ENABLED or not blended_longitudinal.alpha_eligible(cp):
    return False
  word = 0x2014 if cp.flags & HyundaiFlags.CANFD_LKA_STEER_MSG else 0x2004
  if (not cp.openpilotLongitudinalControl or cp.pcmCruise or cp.passive or
      len(cp.safetyConfigs) != 1 or cp.safetyConfigs[0].safetyParam != word):
    return False
  return True


def policy_for(cp, dt):
  return BlendedStoppingPolicy(dt) if eligible(cp) else None


class BlendedStoppingPolicy(HKGModePolicy):
  # Preserve the original CarParams Float32 representation.
  stopping_decel_rate = float(np.float32(.35))

  def __init__(self, dt):
    self.dt = dt
    self.release_frames = int(round(.35 / dt))
    self.init_mode(dt)
    self.reset()

  def reset(self):
    self.release_counter = 0

  def transition(self, native_state, previous_state, active, CS, a_target, should_stop, *, has_lead):
    # Original mixed platform startingState is false: stopping releases to PID.
    if previous_state != LongCtrlState.stopping or not active:
      self.reset()
      return native_state
    if should_stop or CS.brakePressed:
      self.reset()
      return LongCtrlState.stopping
    if (CS.vEgo > .5 or (has_lead and a_target > .15) or
        (a_target >= .45 and not CS.cruiseState.standstill)):
      self.release_counter = self.release_frames
    elif a_target > .15:
      self.release_counter = min(self.release_counter + 1, self.release_frames)
    else:
      self.reset()
    return LongCtrlState.pid if self.release_counter >= self.release_frames else LongCtrlState.stopping

  def stopping_output(self, output, a_target, should_stop, CS):
    # Original other-vehicle stopping tune branches are no-ops for this identity.
    follow_min_speed = max(1.5, .35 + 1.0)
    if not should_stop or CS.brakePressed or CS.vEgo <= follow_min_speed:
      return output
    if a_target >= output - .25:
      return output
    step = np.interp(CS.vEgo, [follow_min_speed, 3., 6., 10.], [.02, .03, .05, .07])
    return max(float(a_target), output - float(step))

