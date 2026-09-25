"""Speed-limit change highlight shared by both native layouts."""

import math

import pyray as rl

from openpilot.starpilot.ui.onroad_state import ObservationKind, OnroadState


class SpeedLimitPulse:
  def __init__(self):
    self.last_limit = 0.0
    self.start_time = -math.inf
    self._started_frame: int | None = None

  def update(self, state: OnroadState, now: float, *, visible: bool = True) -> None:
    if state.drive_frame != self._started_frame:
      self.last_limit = 0.0
      self.start_time = -math.inf
      self._started_frame = state.drive_frame
    observation = state.speed_limit
    if not visible:
      self.start_time = -math.inf
      return
    if observation.kind != ObservationKind.VALID or observation.speed_limit_mps is None:
      return
    limit = observation.speed_limit_mps
    conversion = 3.6 if state.metric else 2.2369362921
    if round(limit * conversion) != round(self.last_limit * conversion):
      self.start_time = now
    self.last_limit = limit

  def color(self, base: rl.Color, now: float) -> rl.Color:
    if isinstance(base, (tuple, list)):
      base = rl.Color(*base)
    elapsed = now - self.start_time
    if not 0.0 <= elapsed < 1.0:
      return base
    fraction = math.sin(math.pi * elapsed)
    return rl.Color(*(round(value + (target - value) * fraction)
                      for value, target in zip((base.r, base.g, base.b), (188, 132, 255), strict=True)), base.a)
