"""Exact first-generation Electrified GV70 captured ADRV speed recipe."""
from dataclasses import dataclass
import math

from opendbc.car.can_definitions import CanData
from opendbc.car.hyundai.captured_adrv import CapturedADRVTemplate


@dataclass(frozen=True)
class GV70Template(CapturedADRVTemplate):
  def frame(self, frame: int, drive_gear: bool, bus: int = 0, *, speed: float | None = None) -> CanData:
    data = self._frame_data(frame, drive_gear, bus)
    if speed is not None and math.isfinite(speed):
      raw = min(max(round(speed * 100.0), 0), 65534)
      data[8:10] = raw.to_bytes(2, 'little')
    return self._finish(data, bus)
