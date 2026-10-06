"""Mode-transition output shaping for admitted Bolt longitudinal owners."""


class BoltModeTransition:
  def __init__(self):
    self.prev_mode = 'acc'
    self.current_mode = 'acc'
    self.timer = 0.0
    self.duration = 1.0
    self.transitioning = False

  def update(self, experimental_mode, dt):
    # Lost mode telemetry cannot create a new transition. A current transition
    # still advances under the caller's active PID ownership.
    if type(experimental_mode) is bool:
      mode = 'blended' if experimental_mode else 'acc'
      if mode != self.current_mode:
        self.prev_mode = self.current_mode
        self.current_mode = mode
        self.transitioning = True
        self.timer = 0.0
    if self.transitioning:
      self.timer += dt
      if self.timer >= self.duration:
        self.transitioning = False

  @property
  def leaving_experimental(self):
    return self.transitioning and self.prev_mode == 'blended' and self.current_mode == 'acc'

  def shape(self, output, last_output):
    if self.leaving_experimental:
      if output > last_output:
        progress = min(1.0, self.timer / max(self.duration, 1e-3))
        output = last_output + (output - last_output) * progress
    elif self.transitioning and self.prev_mode == 'acc' and self.current_mode == 'blended':
      if output < 0.0 and output < last_output:
        progress = min(1.0, self.timer / self.duration)
        urgency = abs(output / -4.0)
        urgency_smooth = min(1.0, urgency ** 0.4)
        blend = 1.0 - (1.0 - progress) * (1.0 - urgency_smooth)
        output = last_output + (output - last_output) * blend
    return output


def policy_for(cp):
  from opendbc.car.structs import CarParams
  from opendbc.car.gm.values import (CAR, GMFlags, GMSafetyFlags, is_bolt_cc_profile, is_bolt_euv_longitudinal,
                                      is_ordinary_cc_profile, is_ordinary_camera_profile, is_conventional_cc_pedal_profile)
  from opendbc.car.gm.longitudinal import policy_for as pedal_policy_for

  if not cp.openpilotLongitudinalControl:
    return None
  if (is_conventional_cc_pedal_profile(cp) or is_ordinary_camera_profile(cp, longitudinal=True) or
      is_ordinary_cc_profile(cp) or is_bolt_cc_profile(cp) or is_bolt_euv_longitudinal(cp)):
    return BoltModeTransition()
  from opendbc.car.gm.values import gm_control_word
  base = GMSafetyFlags.HW_CAM | GMSafetyFlags.EV | GMSafetyFlags.PEDAL_LONG | GMSafetyFlags.PADDLE_SCHED
  words = {
    CAR.CHEVROLET_BOLT_CC_2017: base | GMSafetyFlags.NO_ACC | GMSafetyFlags.BOLT_2017,
    CAR.CHEVROLET_BOLT_CC_2018_2021: base | GMSafetyFlags.NO_ACC,
    CAR.CHEVROLET_BOLT_CC_2022_2023: base | GMSafetyFlags.NO_ACC | GMSafetyFlags.BOLT_GEN2,
    CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL: base | GMSafetyFlags.BOLT_ACC_PEDAL | GMSafetyFlags.BOLT_GEN2,
  }
  if (pedal_policy_for(cp) is not None and not cp.flags & GMFlags.CC_LONG.value and
      len(cp.safetyConfigs) == 1 and
      cp.networkLocation == CarParams.NetworkLocation.fwdCamera and
      gm_control_word(cp) == words.get(cp.carFingerprint)):
    return BoltModeTransition()
  return None
