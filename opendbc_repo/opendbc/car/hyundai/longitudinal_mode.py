"""Reached HKG acceleration PID and ACC/blended transition shaping."""
import numpy as np


class HKGModePolicy:
  def init_mode(self, dt):
    self.dt = dt
    self.prev_mode = 'acc'
    self.current_mode = 'acc'
    self.mode_timer = 0.0
    self.transitioning = False

  def prepare_pid(self, pid, a_target, error, CS, context):
    if type(context.experimental_mode) is bool:
      mode = 'blended' if context.experimental_mode else 'acc'
      if mode != self.current_mode:
        self.prev_mode = self.current_mode
        self.current_mode = mode
        self.mode_timer = 0.0
        self.transitioning = True
    if self.transitioning:
      self.mode_timer += self.dt
      if self.mode_timer >= 1.0:
        self.transitioning = False
    if (pid.i > 0.0 and a_target < -.05 and error < -.25 and
        not (CS.vEgo <= .35 and a_target > -.40)):
      pid.i *= float(np.interp(abs(error), [.25, .75, 1.5], [.55, .25, 0.]))
    # Source CP KF defaults to zero, which original LoC interpreted as gain1.
    return a_target, self.transitioning and self.prev_mode == 'blended' and self.current_mode == 'acc'

  def shape_output(self, output, a_target, error, CS, last_output):
    if (output > 0.0 and a_target < -.10 and error < -.35 and
        not (CS.vEgo <= .35 and a_target > -.40)):
      output = min(output, float(np.interp(a_target, [-1.5, -.6, -.1], [0., 0., .05])))
    if self.transitioning and self.prev_mode == 'blended' and self.current_mode == 'acc':
      if output > last_output:
        output = last_output + (output - last_output) * min(1., self.mode_timer)
    elif self.transitioning and self.prev_mode == 'acc' and self.current_mode == 'blended':
      if output < 0.0 and output < last_output:
        urgency = min(1., abs(output / -4.) ** .4)
        blend = 1. - (1. - min(1., self.mode_timer)) * (1. - urgency)
        output = last_output + (output - last_output) * blend
    return output
