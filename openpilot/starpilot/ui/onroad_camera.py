"""Drive-scoped reverse camera choice from bounded display evidence."""

from dataclasses import dataclass


REVERSE_DWELL_NS = 500_000_000


@dataclass
class ReverseDriverCamera:
  drive_key: tuple[int, int] | None = None
  reverse_since_ns: int | None = None
  last_ns: int | None = None

  def step(self, *, now_ns: int, drive_key: tuple[int, int] | None, enabled: bool,
           car_fresh: bool, reverse: bool) -> bool:
    if drive_key is None or (self.last_ns is not None and now_ns < self.last_ns):
      self.drive_key = None
      self.reverse_since_ns = None
      if drive_key is None:
        self.last_ns = None
        return False
    self.last_ns = now_ns
    if drive_key != self.drive_key:
      self.drive_key = drive_key
      self.reverse_since_ns = None
    if not enabled or not car_fresh or not reverse:
      self.reverse_since_ns = None
      return False
    if self.reverse_since_ns is None:
      self.reverse_since_ns = now_ns
    return now_ns - self.reverse_since_ns >= REVERSE_DWELL_NS
