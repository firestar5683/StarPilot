"""Receive-only GM distance-button samples on the physical powertrain bus."""

from dataclasses import dataclass


DISTANCE_ADDRESS = 0x1E1
SOURCE_MAX_GAP_NS = 300_000_000


@dataclass(frozen=True)
class DistanceSample:
  held: bool
  source_boot_ns: int


@dataclass(frozen=True)
class DistanceObservation:
  samples: tuple[DistanceSample, ...]
  parser_boot_ns: int
  source_epoch: int
  valid: bool


class GMDistanceButtons:
  def __init__(self):
    self.epoch = 0
    self.last_batch_ns = 0
    self.last_source_ns = 0

  def _invalid(self, stamp):
    self.epoch += 1
    self.last_source_ns = 0
    self.last_batch_ns = stamp
    return DistanceObservation((), stamp, self.epoch, False)

  def update(self, packets) -> DistanceObservation:
    samples = []
    batch_ns, source_ns = self.last_batch_ns, self.last_source_ns
    if not packets:
      return self._invalid(batch_ns)
    for stamp, frames in packets:
      if type(stamp) is not int or stamp <= 0 or stamp < batch_ns:
        return self._invalid(batch_ns)
      batch_ns = stamp
      for address, data, bus in frames:
        if address != DISTANCE_ADDRESS or bus != 0:
          continue
        if (type(address) is not int or type(bus) is not int or not isinstance(data, (bytes, bytearray)) or
            len(data) != 7 or stamp <= source_ns or source_ns and stamp - source_ns > SOURCE_MAX_GAP_NS):
          return self._invalid(batch_ns)
        # ASCMSteeringButton.DistanceButton, Motorola bit 22.
        samples.append(DistanceSample(bool(data[2] & 0x40), stamp))
        source_ns = stamp
    if source_ns <= 0 or batch_ns - source_ns > SOURCE_MAX_GAP_NS:
      return self._invalid(batch_ns)
    self.last_batch_ns, self.last_source_ns = batch_ns, source_ns
    return DistanceObservation(tuple(samples), batch_ns, self.epoch, True)
