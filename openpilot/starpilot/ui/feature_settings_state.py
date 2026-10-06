"""Immutable saved-feature settings presentation and guarded user intent."""

from dataclasses import dataclass
from enum import StrEnum
import math
from collections import deque
from collections.abc import Callable

FEATURE_HEADER_HEIGHT = 88
FEATURE_BACK_WIDTH = 190
FEATURE_ROW_TOP = 112
FEATURE_ROW_HEIGHT = 154
FEATURE_VISIBLE_ROWS = 5
FEATURE_CONTROL_LEFT = 1748
FEATURE_CONTROL_RIGHT = 2118
FEATURE_BUTTON_TOP = 64
FEATURE_BUTTON_HEIGHT = 80
FEATURE_ACTION_MARGIN = 36
FEATURE_TAP_SLOP = 36
FEATURE_SWIPE_DISTANCE = 120
FEATURE_FLICK_DISTANCE = 60
FEATURE_FLICK_VELOCITY = 800
FEATURE_FLICK_WINDOW = 0.1
FEATURE_FLICK_PAUSE = 0.06


def is_long_confirm_action(key: str) -> bool:
  return key.startswith(("long_repair:", "long_reset:"))


class FeaturePage(StrEnum):
  HUB = "hub"
  VEHICLE = "vehicle"
  SLC = "slc"
  LANE = "lane"
  LANE_CHANGE = "lane_change"
  PROFILES = "profiles"
  AGGRESSIVE = "aggressive"
  STANDARD = "standard"
  RELAXED = "relaxed"
  TRAFFIC = "traffic"
  CURVE = "curve"
  TORQUE = "torque"
  AOL = "aol"
  WHEEL = "wheel"
  CONDITIONAL = "conditional"
  CONDITIONAL_CEM = "conditional/cem"
  CONDITIONAL_CCM = "conditional/ccm"


TORQUE_CONFIRM_ACTIONS = frozenset(("torque_adopt", "torque_reset", "torque_reset_profile", "torque_rebase", "torque_prepare_firestar", "torque_gain_rebase"))
SLC_CONFIRM_ACTIONS = frozenset(("slc_adopt", "slc_reset"))
LANE_CHANGE_CONFIRM_ACTIONS = frozenset(("lane_change:reset",))
CURVE_CONFIRM_ACTIONS = frozenset(("curve_reset",))
CONDITIONAL_CONFIRM_ACTIONS = frozenset(("conditional:reset", "conditional:manual_reset"))
FEATURE_CONFIRM_ACTIONS = (TORQUE_CONFIRM_ACTIONS | SLC_CONFIRM_ACTIONS | LANE_CHANGE_CONFIRM_ACTIONS |
                           CURVE_CONFIRM_ACTIONS | CONDITIONAL_CONFIRM_ACTIONS | {"reset_profiles", "pip:reset", "sentry:reset"})


@dataclass(frozen=True)
class FeatureRow:
  key: str
  label: str
  value: str
  source: bytes | None = None
  choices: tuple[str, ...] = ()
  step: float = 0.0
  minimum: float = 0.0
  maximum: float = 0.0
  unit: str = ""
  available: bool = False
  reason: str = ""
  page: str = ""
  related_source: bytes | None = None
  vehicle_fingerprint: str | None = None
  capability: tuple | None = None
  dependencies: tuple[tuple[str, bytes | None], ...] = ()
  display_unit: str = ""
  repair_value: str = ""
  default_value: str | None = None
  default_key: str = ""
  actions: tuple[tuple[str, bool], ...] = ()


@dataclass(frozen=True)
class FeatureSettingsState:
  page: str = FeaturePage.HUB
  title: str = "Driving Controls"
  subtitle: str = ""
  rows: tuple[FeatureRow, ...] = ()
  parked: bool = False
  scroll: int = 0
  sidebar_expanded: bool = True
  parent_title: str = "StarPilot"


def feature_row_top(state: FeatureSettingsState) -> int:
  return FEATURE_ROW_TOP + (52 if state.subtitle else 0)


def feature_parent_page(page: str) -> str | None:
  if page == FeaturePage.HUB:
    return None
  if "/" in page:
    return page.split("/", maxsplit=1)[0]
  if page in (FeaturePage.AGGRESSIVE, FeaturePage.STANDARD, FeaturePage.RELAXED, FeaturePage.TRAFFIC):
    return FeaturePage.PROFILES
  return FeaturePage.HUB


def feature_parent_title(page: str) -> str:
  parent = feature_parent_page(page)
  return {None: "StarPilot", FeaturePage.HUB: "Driving Controls", FeaturePage.PROFILES: "Long Planner",
          FeaturePage.CONDITIONAL: "Conditional Driving Modes"}.get(parent, (parent or "").replace("_", " ").title())


def boolean_value(row: FeatureRow) -> bool | None:
  if (not row.key or row.page or row.actions or row.repair_value or row.step or row.key in FEATURE_CONFIRM_ACTIONS or
      row.key.startswith("pip:format:") or is_long_confirm_action(row.key) or row.choices != ("Off", "On")):
    return None
  if row.value in ("Off", "On"):
    return row.value == "On"
  if row.key == "SLCFallback" and row.value == "Off (saved mode 0 or 1)":
    return False
  return None


def feature_action_left(row: FeatureRow) -> int:
  return FEATURE_CONTROL_LEFT - max(0, len(row.actions) - 1) * (FEATURE_CONTROL_RIGHT - FEATURE_CONTROL_LEFT + 16)


def feature_scroll(scroll: int, direction: int, row_count: int) -> int:
  last_page = max(0, row_count - 1) // FEATURE_VISIBLE_ROWS * FEATURE_VISIBLE_ROWS
  return max(0, min(last_page, scroll + direction * FEATURE_VISIBLE_ROWS))


@dataclass(frozen=True)
class FeatureSettingsRequest:
  key: str
  expected: bytes | None
  value: str
  confirmation: bool = False
  related_source: bytes | None = None
  vehicle_fingerprint: str | None = None
  capability: tuple | None = None
  dependencies: tuple[tuple[str, bytes | None], ...] = ()
  display_unit: str = ""
  direction: int = 0


@dataclass(frozen=True)
class FeatureUiAction:
  kind: str
  row: FeatureRow | None = None
  direction: int = 1


class FeatureInput:
  """One touch: movement cancels its tap; a horizontal body swipe pages on release."""

  def __init__(self, emit: Callable[[FeatureUiAction], None]):
    self.emit = emit
    self.held: tuple[float, float, FeatureUiAction | None, int, str, bool] | None = None
    self._samples: deque[tuple[float, float]] = deque(maxlen=16)

  @staticmethod
  def _in_body(x: float, y: float, state: FeatureSettingsState) -> bool:
    left = 520 if state.sidebar_expanded else 20
    return left + 25 <= x <= 2125 and feature_row_top(state) <= y < feature_row_top(state) + FEATURE_VISIBLE_ROWS * FEATURE_ROW_HEIGHT

  @staticmethod
  def target(x: float, y: float, state: FeatureSettingsState) -> FeatureUiAction | None:
    left = 520 if state.sidebar_expanded else 20
    row_top = feature_row_top(state)
    if not left <= x <= 2140:
      return None
    if 12 <= y <= 12 + FEATURE_HEADER_HEIGHT:
      return FeatureUiAction("back" if x < left + FEATURE_BACK_WIDTH else "details")
    if 12 + FEATURE_HEADER_HEIGHT < y < row_top:
      return FeatureUiAction("details") if state.subtitle else None
    if 980 <= y <= 1050:
      return FeatureUiAction("scroll", direction=-1 if x < 1320 else 1)
    if not row_top <= y < row_top + FEATURE_VISIBLE_ROWS * FEATURE_ROW_HEIGHT:
      return None
    visible = int((y - row_top) // FEATURE_ROW_HEIGHT)
    index = state.scroll + visible
    if 0 <= index < len(state.rows):
      row = state.rows[index]
      if row.actions:
        local_y = y - row_top - visible * FEATURE_ROW_HEIGHT
        if FEATURE_ACTION_MARGIN <= local_y <= FEATURE_ROW_HEIGHT - FEATURE_ACTION_MARGIN:
          width = FEATURE_CONTROL_RIGHT - FEATURE_CONTROL_LEFT
          for action, (_, enabled) in enumerate(row.actions):
            left = feature_action_left(row) + action * (width + 16)
            if left <= x <= left + width:
              return FeatureUiAction("action", row, action) if row.available and enabled else None
        return FeatureUiAction("details", row) if x < feature_action_left(row) else None
      if row.page and row.available:
        return FeatureUiAction("open", row)
      if FEATURE_CONTROL_LEFT <= x <= FEATURE_CONTROL_RIGHT:
        if not row.available:
          return None
        local_y = y - row_top - visible * FEATURE_ROW_HEIGHT
        if row.key in FEATURE_CONFIRM_ACTIONS or row.key.startswith("pip:format:") or is_long_confirm_action(row.key):
          return FeatureUiAction("reset", row) if FEATURE_ACTION_MARGIN <= local_y <= FEATURE_ROW_HEIGHT - FEATURE_ACTION_MARGIN else None
        if row.repair_value:
          return FeatureUiAction("change", row) if FEATURE_ACTION_MARGIN <= local_y <= FEATURE_ROW_HEIGHT - FEATURE_ACTION_MARGIN else None
        if boolean_value(row) is not None:
          return FeatureUiAction("change", row, -1 if x < 1930 else 1) if 18 <= local_y <= FEATURE_ROW_HEIGHT - 18 else None
        if row.key and FEATURE_BUTTON_TOP <= local_y <= FEATURE_BUTTON_TOP + FEATURE_BUTTON_HEIGHT:
          if 1760 <= x <= 1915 or 1940 <= x <= 2095:
            return FeatureUiAction("change", row, -1 if x < 1930 else 1)
      if row.key or row.value or row.reason:
        return FeatureUiAction("details", row)
    return None

  def press(self, x: float, y: float, state: FeatureSettingsState) -> None:
    self.cancel()
    target = self.target(x, y, state)
    self.held = (x, y, target, state.scroll, state.page, state.sidebar_expanded) if target is not None or self._in_body(x, y, state) else None

  def move(self, x: float, y: float, state: FeatureSettingsState, now: float | None = None) -> None:
    if self.held is not None:
      px, py, action, scroll, page, sidebar = self.held
      if state.scroll != scroll or state.page != page or state.sidebar_expanded != sidebar:
        self.cancel()
        return
      dx, dy = abs(x - px), abs(y - py)
      moved = max(dx, dy) > FEATURE_TAP_SLOP
      body = self._in_body(px, py, state)
      if body and (not self._in_body(x, y, state) or (moved and dy > dx)):
        self.cancel()
        return
      if action is not None and (moved or self.target(x, y, state) != action):
        self.held = (px, py, None, scroll, page, sidebar) if body else None
      if body and now is not None:
        if self._samples and now <= self._samples[-1][0]:
          self._samples.clear()
        self._samples.append((now, x))
        while now - self._samples[0][0] > FEATURE_FLICK_WINDOW:
          self._samples.popleft()

  def _is_flick(self, px: float, dx: float, now: float | None) -> bool:
    samples = self._samples
    if (now is None or len(samples) < 3 or not 0 <= now - samples[-1][0] <= FEATURE_FLICK_PAUSE or
        samples[-1][0] - samples[0][0] < 0.01):
      return False
    travel = samples[-1][1] - px
    reversal = samples[-1][1] - min(x for _, x in samples) if dx < 0 else max(x for _, x in samples) - samples[-1][1]
    if abs(travel) < FEATURE_FLICK_DISTANCE or travel * dx <= 0 or reversal > FEATURE_TAP_SLOP:
      return False
    # Fit recent movement to reduce polling jitter; release positions are never sampled.
    mean_t = sum(t for t, _ in samples) / len(samples)
    mean_x = sum(x for _, x in samples) / len(samples)
    velocity = sum((t - mean_t) * (x - mean_x) for t, x in samples) / sum((t - mean_t) ** 2 for t, _ in samples)
    return abs(velocity) >= FEATURE_FLICK_VELOCITY and velocity * dx > 0

  def release(self, x: float, y: float, state: FeatureSettingsState, now: float | None = None) -> None:
    self.move(x, y, state)
    action = None
    if self.held is not None:
      px, py, action, *_ = self.held
      dx, dy = x - px, abs(y - py)
      direction = 1 if dx < 0 else -1
      swipe = abs(dx) >= FEATURE_SWIPE_DISTANCE or (abs(dx) >= FEATURE_FLICK_DISTANCE and self._is_flick(px, dx, now))
      if (self._in_body(px, py, state) and swipe and abs(dx) >= 2 * dy and
          feature_scroll(state.scroll, direction, len(state.rows)) != state.scroll):
        action = FeatureUiAction("scroll", direction=direction)
    self.cancel()
    if action is not None:
      self.emit(action)

  def cancel(self) -> None:
    self.held = None
    self._samples.clear()


def row_change(row: FeatureRow, direction: int = 1) -> FeatureSettingsRequest | None:
  """Bind a press to the displayed source, never a later refreshed value."""
  if not row.available:
    return None
  if row.key in ("Offset1", "Offset2", "Offset3", "Offset4", "Offset5", "Offset6", "Offset7"):
    if direction not in (-1, 1):
      return None
    return FeatureSettingsRequest(row.key, row.source, "", related_source=row.related_source,
                                  vehicle_fingerprint=row.vehicle_fingerprint, capability=row.capability,
                                  dependencies=row.dependencies, display_unit=row.display_unit, direction=direction)
  if row.repair_value:
    value = row.repair_value
  elif row.choices and not (row.choices == ("Auto",) and row.step and row.value != "Auto"):
    if row.key == "SLCFallback":
      value = "Off" if row.value == "On" else "On"
    else:
      if row.value not in row.choices:
        return None
      value = row.choices[(row.choices.index(row.value) + direction) % len(row.choices)]
  elif row.step:
    try:
      current = float(row.value)
    except ValueError:
      return None
    precision = 8 if row.key.startswith("torque:") else 4
    value = str(round(max(row.minimum, min(row.maximum, current + row.step * direction)), precision))
    if float(value) == current:
      return None
  else:
    return None
  return FeatureSettingsRequest(row.key, row.source, value, related_source=row.related_source,
                                vehicle_fingerprint=row.vehicle_fingerprint, capability=row.capability,
                                dependencies=row.dependencies, display_unit=row.display_unit)


def row_default(row: FeatureRow) -> FeatureSettingsRequest | None:
  if not row.available or not row.key or row.page or row.default_value is None:
    return None
  if not row.default_key and row.default_value not in row.choices:
    if row.step:
      try:
        number = float(row.default_value)
      except ValueError:
        return None
      if not math.isfinite(number) or not row.minimum <= number <= row.maximum:
        return None
    elif row.choices:
      return None
  return FeatureSettingsRequest(row.default_key or row.key, row.source, row.default_value, confirmation=True,
                                related_source=row.related_source, vehicle_fingerprint=row.vehicle_fingerprint,
                                capability=row.capability, dependencies=row.dependencies, display_unit=row.display_unit)
