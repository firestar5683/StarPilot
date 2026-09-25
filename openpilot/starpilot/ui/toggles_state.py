"""Supplied toggle values and request-only interaction for the offline shell."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class ToggleKey(StrEnum):
  ENABLED = "enabled"
  EXPERIMENTAL = "experimental"
  SAFE_MODE = "safe_mode"
  DISENGAGE_ACCELERATOR = "disengage_accelerator"
  LANE_DEPARTURE = "lane_departure"
  ALWAYS_ON_DM = "always_on_dm"
  RIGHT_HAND_DRIVING = "right_hand_driving"
  RECORD_FRONT = "record_front"
  RECORD_AUDIO = "record_audio"
  METRIC = "metric"


class Personality(StrEnum):
  AGGRESSIVE = "aggressive"
  STANDARD = "standard"
  RELAXED = "relaxed"


@dataclass(frozen=True)
class TogglesState:
  enabled: bool = True
  experimental: bool = False
  safe_mode: bool = False
  disengage_accelerator: bool = False
  lane_departure: bool = False
  always_on_dm: bool = False
  right_hand_driving: bool = False
  record_front: bool = False
  record_audio: bool = False
  metric: bool = False
  personality: Personality = Personality.STANDARD
  scroll_y: float = 0.0
  unavailable: frozenset[ToggleKey] = frozenset()

  def __post_init__(self) -> None:
    if not 0 <= self.scroll_y <= 1000:
      raise ValueError("Toggle scroll position must stay within the content")


@dataclass(frozen=True)
class ToggleRequest:
  key: ToggleKey | None = None
  value: bool | None = None
  personality: Personality | None = None


class TogglesInput:
  def __init__(self, emit: Callable[[ToggleRequest], None]):
    self.emit = emit
    self._pressed: tuple[float, float, ToggleRequest, float] | None = None

  def _target(self, x: float, y: float, state: TogglesState) -> ToggleRequest | None:
    if not 500 <= x < 2160 or not 50 <= y < 1030:
      return None
    row = int((y - 50 + state.scroll_y) // 171)
    rows = (ToggleKey.ENABLED, ToggleKey.EXPERIMENTAL, ToggleKey.SAFE_MODE,
            ToggleKey.DISENGAGE_ACCELERATOR, None, ToggleKey.LANE_DEPARTURE,
            ToggleKey.ALWAYS_ON_DM, ToggleKey.RIGHT_HAND_DRIVING, ToggleKey.RECORD_FRONT,
            ToggleKey.RECORD_AUDIO, ToggleKey.METRIC)
    if 0 <= row < len(rows) and rows[row] is not None and x >= 1790:
      key = rows[row]
      if key in state.unavailable:
        return None
      return ToggleRequest(key=key, value=not getattr(state, key.value))
    if row == 4 and 1300 <= x < 2110:
      index = min(2, int((x - 1300) // 270))
      return ToggleRequest(personality=tuple(Personality)[index])
    return None

  def press(self, x: float, y: float, state: TogglesState) -> None:
    target = self._target(x, y, state)
    self._pressed = (x, y, target, state.scroll_y) if target else None

  def move(self, x: float, y: float, state: TogglesState) -> None:
    if self._pressed:
      _, _, target, scroll_y = self._pressed
      if state.scroll_y != scroll_y or self._target(x, y, state) != target:
        self.cancel()

  def release(self, x: float, y: float, state: TogglesState) -> None:
    self.move(x, y, state)
    if self._pressed:
      self.emit(self._pressed[2])
    self.cancel()

  def cancel(self) -> None:
    self._pressed = None
