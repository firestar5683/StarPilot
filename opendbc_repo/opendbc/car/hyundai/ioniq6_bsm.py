"""Exact Ioniq 6 HDA-II blind-spot status from physical corner and lamp sources."""

from dataclasses import dataclass


CORNER_MAX_AGE_NS = 100_000_000
LAMP_MAX_AGE_NS = 1_500_000_000
LAMP_HOLD_NS = 500_000_000

REAR_NEUTRAL_BODY = bytes.fromhex("000000000000008000000000000000000000000000000000")
FRONT_NEUTRAL_BODY = bytes.fromhex("00000000000000000000000100000000")


@dataclass(frozen=True)
class BlindspotStatus:
  left: int
  right: int


def rear_body(status: BlindspotStatus) -> bytes:
  """Return the frozen Ioniq 6 indication body; integrity bytes remain zero."""
  left, right = status.left, status.right
  if left not in (0, 1, 2) or right not in (0, 1, 2):
    raise ValueError("invalid blind-spot indication")
  body = bytearray(REAR_NEUTRAL_BODY)
  body[3] = int(bool(left or right)) | (left << 6)
  body[4] = right
  body[5] = left << 1
  body[6] = right << 5
  body[7] = 0x80 | (max(left, right) << 3)
  body[16] = left | (right << 2)
  return bytes(body)


class Ioniq6BlindspotSources:
  """One-source-clock status gate for paired dashboard frames.

  CANParser only updates source timestamps for checksum-valid corner frames.
  Repeated parser values do not extend a blinker transition's hold.
  """

  def __init__(self) -> None:
    self.lamp_source_ns = 0
    self.left_lamp = False
    self.right_lamp = False
    self.left_off_ns = 0
    self.right_off_ns = 0
    self.corner_source_ns = 0
    self.corner_state = 0

  def observe(self, *, corner_source_ns: int, corner_state: int, lamp_source_ns: int,
              left_lamp: bool, right_lamp: bool) -> None:
    if corner_source_ns > self.corner_source_ns:
      self.corner_source_ns = corner_source_ns
      self.corner_state = corner_state
    if lamp_source_ns > self.lamp_source_ns:
      if self.lamp_source_ns > 0 and lamp_source_ns - self.lamp_source_ns > LAMP_MAX_AGE_NS:
        # A pre-gap illuminated lamp cannot authorize a new post-gap hold.
        self.left_lamp = self.right_lamp = False
        self.left_off_ns = self.right_off_ns = 0
      if self.left_lamp and not left_lamp:
        self.left_off_ns = lamp_source_ns
      if self.right_lamp and not right_lamp:
        self.right_off_ns = lamp_source_ns
      self.left_lamp = left_lamp
      self.right_lamp = right_lamp
      self.lamp_source_ns = lamp_source_ns

  def status(self, now_ns: int) -> BlindspotStatus | None:
    if not (self.corner_source_ns > 0 and 0 <= now_ns - self.corner_source_ns <= CORNER_MAX_AGE_NS and
            self.lamp_source_ns > 0 and 0 <= now_ns - self.lamp_source_ns <= LAMP_MAX_AGE_NS):
      return None
    left_present = bool(self.corner_state & 0x10)
    right_present = bool(self.corner_state & 0x08)
    left_blinking = self.left_lamp or (self.left_off_ns > 0 and 0 <= now_ns - self.left_off_ns <= LAMP_HOLD_NS)
    right_blinking = self.right_lamp or (self.right_off_ns > 0 and 0 <= now_ns - self.right_off_ns <= LAMP_HOLD_NS)
    return BlindspotStatus(1 + int(left_blinking) if left_present else 0,
                           1 + int(right_blinking) if right_present else 0)
