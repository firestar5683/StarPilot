"""Keep only the replay presentation visible while its final audio drains."""
import json
import math
from pathlib import Path
import time


class ReplayDisplayHold:
  def __init__(self, marker=None, enabled=False, clock=time.monotonic, maximum_hold=20.):
    self.marker = Path(marker) if marker else None
    self.enabled = bool(enabled and marker)
    self.clock = clock
    self.started_at = clock()
    self.maximum_hold = maximum_hold
    self.seen_onroad = False
    self.holding_since = None
    self.released = False

  def apply(self, started):
    if not self.enabled or self.released:
      return started
    now = self.clock()
    try:
      value = json.loads(self.marker.read_text())
      wall = value.get('wall')
      if (isinstance(wall, (int, float)) and math.isfinite(wall)
          and self.started_at <= wall <= now and type(value.get('drained')) is bool):
        self.released = True
        return started
    except (OSError, ValueError, TypeError):
      pass
    if started:
      self.seen_onroad = True
      self.holding_since = None
      return True
    if not self.seen_onroad:
      return False
    if self.holding_since is None:
      self.holding_since = now
    if now - self.holding_since >= self.maximum_hold:
      self.released = True
      return False
    return True
