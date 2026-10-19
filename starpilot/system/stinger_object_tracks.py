"""Read-only candidate object decoding for Stinger validation logging, not control."""

import math
from dataclasses import dataclass


BUS = 1
START_ADDRESS = 0x238
SLOT_COUNT = 10
MAX_TRIPLET_SPAN_NS = 20_000_000
MAX_EGO_AGE_NS = 100_000_000


def _field(dat: bytes, start: int, size: int) -> int:
  return (int.from_bytes(dat, "big") >> (64 - start - size)) & ((1 << size) - 1)


@dataclass(frozen=True)
class CandidateObject:
  slot: int
  object_id: int
  cycle: int
  type_raw: int
  distance: float
  lateral_raw: float
  absolute_speed: float

  def relative_speed(self, ego_speed: float) -> float:
    if not math.isfinite(ego_speed):
      raise ValueError("ego speed must be finite")
    return self.absolute_speed - ego_speed


def decode_triplet(slot: int, payloads: tuple[bytes, ...]) -> CandidateObject | None:
  if not 0 <= slot < SLOT_COUNT or len(payloads) != 3 or any(len(dat) != 8 for dat in payloads):
    return None
  a, b, c = payloads
  cycle = _field(a, 44, 2)
  object_id = _field(a, 56, 7)
  if cycle != _field(b, 0, 2) or cycle != _field(c, 0, 2):
    return None
  if object_id != _field(b, 57, 7) or object_id != _field(c, 43, 7):
    return None
  distance_raw = _field(a, 0, 13)
  if object_id == 0 or distance_raw == 0:
    return None

  return CandidateObject(
    slot=slot, object_id=object_id, cycle=cycle, type_raw=_field(a, 13, 3),
    distance=distance_raw * 0.05, lateral_raw=_field(a, 16, 12) * 0.05 - 102.4,
    absolute_speed=_field(a, 32, 12) * 0.05 - 100.0,
  )


class StingerObjectDecoder:
  def __init__(self):
    self.frames: dict[tuple[int, int], tuple[int, bytes]] = {}

  def update(self, timestamp_ns: int, address: int, dat: bytes, bus: int) -> CandidateObject | None:
    if bus != BUS or not START_ADDRESS <= address < START_ADDRESS + 3 * SLOT_COUNT or len(dat) != 8:
      return None
    slot, part = divmod(address - START_ADDRESS, 3)
    self.frames[slot, part] = (timestamp_ns, dat)
    if part != 2 or any((slot, i) not in self.frames for i in range(3)):
      return None
    triple = [self.frames[slot, i] for i in range(3)]
    times = [t for t, _ in triple]
    if max(times) != timestamp_ns or max(times) - min(times) > MAX_TRIPLET_SPAN_NS:
      return None

    # Consume the complete cycle so repeated final frames cannot reuse old parts.
    for i in range(3):
      del self.frames[slot, i]
    return decode_triplet(slot, tuple(dat for _, dat in triple))
