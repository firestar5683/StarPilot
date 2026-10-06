"""Temporary steering output pauses, independent of driver authorization."""

from dataclasses import dataclass
import math

from openpilot.common.constants import CV
from openpilot.starpilot.saved_source import read_saved

KEYS = ('PauseLateralSpeed', 'PauseLateralOnSignal', 'LateralResumeDelay')


@dataclass(frozen=True)
class PauseSettings:
  speed_mps: float = 0.0
  signal_only: bool = False
  delay_s: float = 0.0


def read_settings(params) -> PauseSettings | None:
  values = {key: read_saved(params, key, 128) for key in (*KEYS, 'IsMetric')}
  if not all(readable for _, readable in values.values()):
    return None
  try:
    speed_raw = values[KEYS[0]][0]
    speed = float(b'0' if speed_raw is None else speed_raw)
    signal = values[KEYS[1]][0]
    delay_raw = values[KEYS[2]][0]
    delay = float(b'0' if delay_raw is None else delay_raw)
    metric = values['IsMetric'][0]
    if (signal not in (None, b'0', b'1') or metric not in (None, b'0', b'1') or
        not math.isfinite(speed) or not 0 <= speed <= 100 or not math.isfinite(delay) or not 0 <= delay <= 5):
      return None
    return PauseSettings(speed * (CV.KPH_TO_MS if metric == b'1' else CV.MPH_TO_MS), signal == b'1', delay)
  except (ValueError, OverflowError):
    return None


class LateralPause:
  def __init__(self, settings: PauseSettings | None, params=None):
    self.settings = settings or PauseSettings()
    self.params = params
    self._refresh_ns = 0
    self._drive_id = 0
    self.reset()

  def reset(self) -> None:
    self._blinker = False
    self._minimum = math.inf
    self._release_ns = 0
    self._last_ns = 0

  def refresh(self, now_ns: int) -> None:
    if self.params is not None and (now_ns < self._refresh_ns or now_ns - self._refresh_ns >= 1_000_000_000):
      settings = read_settings(self.params)
      if settings is not None:
        if settings != self.settings:
          self.reset()
        self.settings = settings
      self._refresh_ns = now_ns

  def allowed(self, cs, *, now_ns: int, source_ns: int, drive_id: int | None = None) -> bool:
    self.refresh(now_ns)
    if self.settings.speed_mps == 0:
      self.reset()
      return True
    if now_ns < self._last_ns:
      self.reset()
      return False
    self._last_ns = now_ns
    if drive_id is not None:
      if drive_id <= 0:
        return False
      if drive_id != self._drive_id:
        self.reset()
        self._drive_id = drive_id
        self._last_ns = now_ns
    if (not cs.canValid or cs.canTimeout or not math.isfinite(cs.vEgo) or
        not 0 < source_ns <= now_ns or now_ns - source_ns > 250_000_000):
      return False
    signal = bool(cs.leftBlinker or cs.rightBlinker)
    if signal:
      self._minimum = min(self._minimum, cs.vEgo) if self._blinker else cs.vEgo
      self._release_ns = 0
    elif self._blinker:
      self._release_ns = now_ns
    self._blinker = signal
    delayed = (self.settings.signal_only and self._release_ns > 0 and
               self._minimum < self.settings.speed_mps / 2 and
               now_ns - self._release_ns < self.settings.delay_s * 1e9)
    return bool((cs.vEgo >= self.settings.speed_mps or self.settings.signal_only and not signal) and not delayed)
