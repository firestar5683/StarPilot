"""Original EV9 normal LongControl start/release policy in the modern extension."""
import numpy as np
from opendbc.car.structs import car
from opendbc.car.hyundai.ev9_longitudinal import qualified
from opendbc.car.hyundai.longitudinal_mode import HKGModePolicy

LongCtrlState = car.CarControl.Actuators.LongControlState
START_ACCEL = float(np.float32(.2))
START_SPEED = float(np.float32(.5))
STOP_SPEED = float(np.float32(.3))


def policy_for(cp, dt):
  return EV9StoppingPolicy(dt) if qualified(cp) else None


class EV9StoppingPolicy(HKGModePolicy):
  stopping_decel_rate = float(np.float32(.4))

  def __init__(self, dt):
    self.init_mode(dt)
    self.release_frames = int(round(.35 / dt))
    self.reset()

  def reset(self):
    self.release_counter = 0

  def transition(self, native_state, previous_state, active, CS, a_target, should_stop, *, has_lead):
    # Original Toyota stopped-lead hold branch is unreachable for this identity.
    if previous_state != LongCtrlState.stopping:
      self.release_counter = 0
      ready = True
    elif should_stop or CS.brakePressed:
      self.release_counter = 0
      ready = False
    elif (CS.vEgo > START_SPEED or (has_lead and a_target > .15) or
          (a_target >= .45 and not CS.cruiseState.standstill)):
      self.release_counter = self.release_frames
      ready = True
    else:
      self.release_counter = min(self.release_counter + 1, self.release_frames) if a_target > .15 else 0
      ready = self.release_counter >= self.release_frames
    if not active:
      return LongCtrlState.off
    if previous_state == LongCtrlState.off:
      return LongCtrlState.starting if not (should_stop or CS.brakePressed or CS.cruiseState.standstill) else LongCtrlState.stopping
    if previous_state == LongCtrlState.stopping:
      return LongCtrlState.starting if not should_stop and not CS.brakePressed and ready else LongCtrlState.stopping
    if should_stop:
      return LongCtrlState.stopping
    return LongCtrlState.pid if CS.vEgo > START_SPEED else previous_state

  def starting_output(self, a_target, accel_limits, context):
    # Missing carrier data cannot be interpreted as a request for a launch shove.
    if (context.traffic_mode is None or context.custom_acceleration is None or context.has_lead is None or
        context.profile_max_accel is None):
      output = float(np.clip(a_target, 0., START_ACCEL))
    elif context.traffic_mode or context.custom_acceleration or (context.has_lead and a_target <= .25):
      output = float(np.clip(a_target, 0., START_ACCEL))
    elif context.profile_max_accel > 0.:
      output = min(START_ACCEL, context.profile_max_accel)
    else:
      output = START_ACCEL
    self.reset()  # Original starting branch resets the release hysteresis.
    return float(np.clip(output, *accel_limits))

  def stopping_output(self, output, a_target, should_stop, CS):
    follow_min_speed = max(1.5, STOP_SPEED + 1.)
    if not should_stop or CS.brakePressed or CS.vEgo <= follow_min_speed or a_target >= output - .25:
      return output
    step = np.interp(CS.vEgo, [follow_min_speed, 3., 6., 10.], [.02, .03, .05, .07])
    return max(float(a_target), output - float(step))

