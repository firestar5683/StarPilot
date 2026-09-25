"""Monotonic, drive-scoped C4 standstill duration for the saved Visuals choice."""

from dataclasses import dataclass


SHOW_AFTER_DRIVE_NS = 60_000_000_000
SECOND_NS = 1_000_000_000
ENGAGED = (22, 127, 64)
EXPERIMENTAL = (218, 111, 37)
TRAFFIC = (201, 34, 49)


@dataclass
class StoppedTimer:
  drive_key: tuple[int, int] | None = None
  drive_started_ns: int | None = None
  standstill_started_ns: int | None = None
  last_ns: int | None = None

  def reset(self) -> None:
    self.drive_key = None
    self.drive_started_ns = None
    self.standstill_started_ns = None
    self.last_ns = None

  def step(self, *, now_ns: int, drive_key: tuple[int, int] | None, car_fresh: bool,
           standstill: bool, reverse: bool, enabled: bool) -> int | None:
    if drive_key is None or (self.last_ns is not None and now_ns < self.last_ns):
      self.reset()
      if drive_key is None:
        return None
    self.last_ns = now_ns
    if drive_key != self.drive_key:
      self.drive_key = drive_key
      self.drive_started_ns = now_ns
      self.standstill_started_ns = None
    if not enabled or not car_fresh or not standstill or reverse:
      self.standstill_started_ns = None
      return None
    if self.standstill_started_ns is None:
      self.standstill_started_ns = now_ns
    if self.drive_started_ns is None or now_ns - self.drive_started_ns < SHOW_AFTER_DRIVE_NS:
      return None
    seconds = (now_ns - self.standstill_started_ns) // SECOND_NS
    return seconds if seconds > 0 else None


def duration_text(seconds: int) -> tuple[str, str]:
  minutes, remainder = divmod(seconds, 60)
  return (f"{minutes} minute{'s' if minutes != 1 else ''}",
          f"{remainder} second{'s' if remainder != 1 else ''}")


def duration_color(seconds: int) -> tuple[int, int, int]:
  if seconds < 60:
    return ENGAGED
  if seconds < 150:
    start, end, amount = ENGAGED, EXPERIMENTAL, (seconds - 60) / 90
  elif seconds < 300:
    start, end, amount = EXPERIMENTAL, TRAFFIC, (seconds - 150) / 150
  else:
    return TRAFFIC
  return (int(start[0] + amount * (end[0] - start[0])),
          int(start[1] + amount * (end[1] - start[1])),
          int(start[2] + amount * (end[2] - start[2])))
