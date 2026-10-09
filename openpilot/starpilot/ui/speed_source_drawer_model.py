"""Reversible reveal progress for the display-only source panel."""

OPEN_SECONDS = 0.18
CLOSE_SECONDS = 0.14


class DrawerMotion:
  def __init__(self):
    self.reset()

  def reset(self) -> None:
    self.progress = 0.0
    self._open = False
    self._start_progress = 0.0
    self._start_time = 0.0

  def update(self, opened: bool, now: float) -> None:
    # Sample the old transition first so a second tap reverses without jumping.
    target = float(self._open)
    if self.progress != target:
      duration = OPEN_SECONDS if self._open else CLOSE_SECONDS
      phase = min(1.0, max(0.0, (now - self._start_time) / duration))
      self.progress = target + (self._start_progress - target) * (1 - phase) ** 4
    if opened != self._open:
      self._open = opened
      self._start_progress = self.progress
      self._start_time = now

