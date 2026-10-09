"""Explicit, immutable observations for the offline onroad presentation.

The producer owns freshness and units. A missing observation is never inferred
from a zero-valued speed or a default-initialized message.
"""

from openpilot.starpilot.ui.onroad_customization import PROFILES, default_document, offset, placement, widget_size

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
import math
from typing import Protocol

from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.appearance_preferences import OnroadAppearance
from openpilot.starpilot.curve_speed.status import CurveObservation
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.ui.conditional_status import ConditionalDisplay
from openpilot.starpilot.ui.traffic_status import TrafficDisplay
from openpilot.starpilot.ui.developer_preview import OnroadVisualPreview
from openpilot.starpilot.ui.wheel_feedback import WheelFeedback
from openpilot.starpilot.ui.navigation_state import NavigationDisplay
from openpilot.starpilot.ui.live_developer_sidebar import DeveloperMetric


class ObservationKind(StrEnum):
  VALID = "valid"
  ABSENT = "absent"
  UNKNOWN = "unknown"
  STALE = "stale"


class AlertSize(StrEnum):
  NONE = "none"
  SMALL = "small"
  MID = "mid"
  FULL = "full"


class SlcActionKind(StrEnum):
  ACCEPT = "accept"
  REJECT = "reject"
  ADOPT = "adopt"


@dataclass(frozen=True)
class SlcUiRequest:
  kind: SlcActionKind
  session_id: str
  decision_id: int
  presentation_id: int
  candidate_speed_mps: float


@dataclass(frozen=True)
class SlcControl:
  request: SlcUiRequest
  label: str
  bounds: tuple[int, int, int, int]


@dataclass(frozen=True)
class SourceReading:
  source: str
  enabled: bool
  kind: str
  speed_mps: float | None = None


@dataclass(frozen=True)
class SpeedLimitObservation:
  kind: ObservationKind = ObservationKind.UNKNOWN
  source: str = "none"
  speed_limit_mps: float | None = None
  offset_mps: float | None = None
  pending_speed_limit_mps: float | None = None
  effective_cap_mps: float | None = None
  accepted_speed_limit_mps: float | None = None
  accepted_source: str = "none"
  pending_source: str = "none"
  effective_cluster_target_mps: float | None = None
  limiting_max_set: bool = False
  driver_override_active: bool = False
  session_id: str | None = None
  decision_id: int | None = None
  presentation_id: int | None = None
  status: str = ""
  action_enabled: bool = False
  action_sequence_id: int = 0
  action_status: str = ""
  source_readings: tuple[SourceReading, ...] = ()
  accepted_adjusted_limit_mps: float | None = None
  pending_adjusted_limit_mps: float | None = None
  presentation_adjusted_limit_mps: float | None = None
  override_basis: str = 'none'
  retained_override: bool = False
  command_action_sequence_id: int = 0
  command_status: str = ''
  action_feedback: str = ''

  def __post_init__(self) -> None:
    for value in (self.speed_limit_mps, self.offset_mps, self.pending_speed_limit_mps,
                  self.effective_cap_mps, self.accepted_speed_limit_mps, self.effective_cluster_target_mps,
                  self.accepted_adjusted_limit_mps, self.pending_adjusted_limit_mps, self.presentation_adjusted_limit_mps):
      if value is not None and not math.isfinite(value):
        raise ValueError("Speed-limit values must be finite")
    for value in (self.accepted_adjusted_limit_mps, self.pending_adjusted_limit_mps, self.presentation_adjusted_limit_mps):
      if value is not None and value <= 0:
        raise ValueError('Adjusted limits must be positive')
    if self.kind != ObservationKind.VALID and self.speed_limit_mps is not None:
      raise ValueError("Only a valid observation can carry a speed limit")
    if self.kind == ObservationKind.VALID and (self.speed_limit_mps is None or self.speed_limit_mps <= 0):
      raise ValueError("A valid observation needs a positive speed limit")


@dataclass(frozen=True)
class OnroadAlert:
  size: AlertSize = AlertSize.NONE
  text1: str = ""
  text2: str = ""
  critical: bool = False
  alert_type: str = ""
  user_prompt: bool = False
  visual_alert: int = 0


def is_lane_change_notice(alert: OnroadAlert) -> bool:
  return (alert.alert_type in ("preLaneChangeLeft/warning", "preLaneChangeRight/warning", "laneChange/warning") and
          alert.size in (AlertSize.SMALL, AlertSize.MID) and not alert.critical and not alert.user_prompt and alert.visual_alert == 0)


def is_personality_notice(alert: OnroadAlert) -> bool:
  return (alert.alert_type == "personalityChanged/warning" and alert.size in (AlertSize.SMALL, AlertSize.MID) and
          not alert.critical and not alert.user_prompt and alert.visual_alert == 0)


@dataclass(frozen=True)
class BorderSignals:
  left_blinker: bool
  right_blinker: bool
  left_blindspot: bool
  right_blindspot: bool


@dataclass(frozen=True)
class OnroadState:
  engaged: bool
  camera_available: bool
  speed_mps: float | None
  cruise_kph: float | None
  speed_limit: SpeedLimitObservation
  appearance: OnroadAppearance = field(default_factory=OnroadAppearance)
  alert: OnroadAlert = OnroadAlert()
  metric: bool = False
  show_slc_offset: bool = True
  experimental_available: bool = False
  experimental_enabled: bool = False
  torque_utilization: float = 0.0
  personality: int = 1
  switchback_mode: bool = False
  traffic_mode: bool = False
  traffic_display: TrafficDisplay | None = None
  lateral_active: bool = False
  longitudinal_active: bool = False
  longitudinal_overridden: bool = False
  stock_cruise_active: bool = False
  slc_system_long_available: bool = False
  curve: CurveObservation | None = None
  show_curve_status: bool = False
  conditional_configured: ModeChoice | None = None
  navigation: NavigationDisplay | None = None
  conditional_perception: ConditionalDisplay | None = None
  conditional_effective: ConditionalDisplay | None = None
  visual_preview: OnroadVisualPreview | None = None
  border_signals: BorderSignals | None = None
  stopped_duration_s: int | None = None
  reverse_driver_camera: bool = False
  reversing: bool = False
  stock_confidence_source_fresh: bool = False
  stock_confidence_source_stamp_ns: int | None = None
  stock_confidence_drive_frame: int | None = None
  model_confidence: float | None = None
  lead_indicator_source_fresh: bool = False
  customization: dict = field(default_factory=default_document)
  wheel_feedback: WheelFeedback = field(default_factory=WheelFeedback)
  torque_source_available: bool = True
  torque_drive_frame: int | None = None
  experimental_action_token: str = ""
  drive_frame: int | None = None
  observed_ns: int = 0
  viewport_width: float = 1860.0
  developer_metrics: tuple[DeveloperMetric, ...] = ()

  @property
  def cruise_active(self) -> bool:
    return self.longitudinal_active or self.longitudinal_overridden or self.stock_cruise_active

  def __post_init__(self) -> None:
    if self.speed_mps is not None and (not math.isfinite(self.speed_mps) or self.speed_mps < 0):
      raise ValueError("Speed must be finite and nonnegative")
    if self.cruise_kph is not None and (not math.isfinite(self.cruise_kph) or self.cruise_kph < 0):
      raise ValueError("Cruise speed must be finite and nonnegative")
    if not math.isfinite(self.torque_utilization) or not -1.0 <= self.torque_utilization <= 1.0:
      raise ValueError("Torque utilization must be normalized")
    if not 0 <= self.personality <= 2:
      raise ValueError("Personality must be aggressive, standard, or relaxed")
    if self.stopped_duration_s is not None and (type(self.stopped_duration_s) is not int or self.stopped_duration_s <= 0):
      raise ValueError("Stopped duration must be a positive whole second")
    if self.model_confidence is not None and (not math.isfinite(self.model_confidence) or
                                               not 0 <= self.model_confidence <= 1):
      raise ValueError("Model confidence must be normalized")


@dataclass(frozen=True)
class OnroadRequest:
  kind: str
  value: bool | None = None
  action_token: str = ""


def _default_slc_controls(profile: Profile, state: OnroadState) -> tuple[SlcControl, ...]:
  """Only render/accept actions backed by a displayed live SLC decision."""
  observation = state.speed_limit
  if (state.alert.size != AlertSize.NONE or not state.longitudinal_active or not state.slc_system_long_available or
      not observation.action_enabled or
      observation.kind != ObservationKind.VALID or not observation.session_id):
    return ()
  pending = observation.pending_speed_limit_mps
  if pending is not None and pending > 0 and observation.decision_id is not None and observation.decision_id > 0:
    def request(kind: SlcActionKind) -> SlcUiRequest:
      return SlcUiRequest(kind, observation.session_id or "", observation.decision_id or 0,
                          observation.presentation_id or 0, pending)
    if profile == Profile.LARGE:
      from openpilot.starpilot.ui.large_speed_geometry import WIDTH, ACTION_HEIGHT, ACTION_X, ACTION_Y, ACTION_HEADER_HEIGHT
      target = observation.pending_adjusted_limit_mps
      label = f'Apply {round(target * (3.6 if state.metric else 2.2369362921))}' if target is not None and target > 0 else 'Apply'
      return (SlcControl(request(SlcActionKind.ACCEPT), label,
                         (ACTION_X, ACTION_Y + ACTION_HEADER_HEIGHT, ACTION_X + WIDTH // 2 - 6, ACTION_Y + ACTION_HEIGHT)),
              SlcControl(request(SlcActionKind.REJECT), 'Keep',
                         (ACTION_X + WIDTH // 2 + 6, ACTION_Y + ACTION_HEADER_HEIGHT, ACTION_X + WIDTH, ACTION_Y + ACTION_HEIGHT)))
    return (SlcControl(request(SlcActionKind.ACCEPT), "ACCEPT", (174, 180, 310, 234)),
            SlcControl(request(SlcActionKind.REJECT), "REJECT", (320, 180, 456, 234)))
  if (pending is None and observation.speed_limit_mps is not None and
      observation.presentation_id is not None and observation.presentation_id > 0):
    if profile == Profile.COMPACT:
      return ()
    request = SlcUiRequest(SlcActionKind.ADOPT, observation.session_id, observation.decision_id or 0,
                           observation.presentation_id, observation.speed_limit_mps)
    from openpilot.starpilot.ui.large_speed_geometry import WIDTH, ACTION_HEIGHT, ACTION_X, ACTION_Y, ACTION_HEADER_HEIGHT
    header = ACTION_HEADER_HEIGHT if observation.action_feedback else 0
    bounds = (ACTION_X, ACTION_Y + header, ACTION_X + WIDTH, ACTION_Y + header + ACTION_HEIGHT - ACTION_HEADER_HEIGHT)
    target = observation.presentation_adjusted_limit_mps
    label = f'Use limit {round(target * (3.6 if state.metric else 2.2369362921))}' if target is not None else 'USE LIMIT'
    return (SlcControl(request, label, bounds),)
  return ()


def slc_controls(profile: Profile, state: OnroadState) -> tuple[SlcControl, ...]:
  if not placement(state.customization, profile, "speed_limit_actions")["enabled"]:
    return ()
  dx, dy = offset(state.customization, profile, "speed_limit_actions")
  return tuple(SlcControl(item.request, item.label,
                         (item.bounds[0] + dx, item.bounds[1] + dy, item.bounds[2] + dx, item.bounds[3] + dy))
               for item in _default_slc_controls(profile, state))


def _inside_widget(x, y, state, widget, bounds):
  if not placement(state.customization, Profile.LARGE, widget)["enabled"]:
    return False
  dx, dy = offset(state.customization, Profile.LARGE, widget)
  left, top, right, bottom = bounds
  if widget == "steering_wheel":
    left += state.viewport_width - 1860
    size, _ = widget_size(state.customization, Profile.LARGE, widget)
    right, bottom = left + size, top + size
  return left + dx <= x <= right + dx and top + dy <= y <= bottom + dy


def compact_sign_obscured_by_actions(state: OnroadState) -> bool:
  """Use the complete pending presentation, including its header, for visibility."""
  if not slc_controls(Profile.COMPACT, state):
    return False
  sign = placement(state.customization, "compact", "speed_limit")
  actions = placement(state.customization, "compact", "speed_limit_actions")
  widgets = PROFILES["compact"]["widgets"]
  area, sign_area = widgets["speed_limit_actions"], widgets["speed_limit"]
  inset = area["visualInsetTop"]
  top = actions["y"] - inset if actions["y"] >= inset else actions["y"]
  bottom = actions["y"] + area["height"] + (inset if actions["y"] < inset else 0)
  return (sign["x"] < actions["x"] + area["width"] and sign["x"] + sign_area["width"] > actions["x"] and
          sign["y"] < bottom and sign["y"] + sign_area["height"] > top)


class OnroadInput:
  """The onroad wheel emits intent only; the supplied state must be refreshed."""

  def __init__(self, emit: Callable[[OnroadRequest | SlcUiRequest], None], profile: Profile = Profile.LARGE):
    self.emit = emit
    self.profile = profile
    self._press: tuple[float, float, bool, str] | None = None
    self._slc_press: tuple[float, float, SlcUiRequest] | None = None
    self._source_press = None

  def _source_target(self, x, y, state):
    if (self.profile != Profile.LARGE or state.alert.size != AlertSize.NONE or
        state.speed_limit.kind != ObservationKind.VALID or not state.speed_limit.session_id or
        not placement(state.customization, 'large', 'cruise_limits')['enabled']):
      return False
    from openpilot.starpilot.ui.large_speed_geometry import source_toggle_bounds
    left, top, right, bottom = source_toggle_bounds(state)
    return left <= x <= right and top <= y <= bottom

  @property
  def source_pressed(self):
    return self._source_press is not None

  @property
  def pressed_action(self):
    return self._slc_press[2] if self._slc_press else None

  @property
  def claimed(self) -> bool:
    return self._press is not None or self._slc_press is not None or self._source_press is not None

  def press(self, x: float, y: float, state: OnroadState) -> None:
    self.cancel()
    controls = slc_controls(self.profile, state)
    for control in controls:
      left, top, right, bottom = control.bounds
      if left <= x <= right and top <= y <= bottom:
        self._slc_press = (x, y, control.request)
        return
    if self._source_target(x, y, state):
      self._source_press = (x, y, state.speed_limit.session_id, state.customization.get('speedSources', False))
      return
    # Only the large-profile wheel is an experimental-mode touch target.
    if self.profile != Profile.LARGE:
      self.cancel()
      return
    inside = _inside_widget(x, y, state, "steering_wheel", (1588, 75, 1780, 267)) and not state.appearance.hide_steering_wheel
    self._press = (x, y, state.experimental_enabled, state.experimental_action_token) if inside and state.experimental_available else None

  def move(self, x: float, y: float, state: OnroadState) -> None:
    if self._source_press:
      px, py, session, opened = self._source_press
      if (abs(x - px) > 5 or abs(y - py) > 5 or session != state.speed_limit.session_id or
          opened != state.customization.get('speedSources', False) or not self._source_target(x, y, state)):
        self.cancel()
      return
    if self._slc_press:
      px, py, request = self._slc_press
      current = next((item for item in slc_controls(self.profile, state) if item.request == request), None)
      in_control = current is not None and current.bounds[0] <= x <= current.bounds[2] and current.bounds[1] <= y <= current.bounds[3]
      if current is None or abs(x - px) > 5 or abs(y - py) > 5 or not in_control:
        self.cancel()
      return
    if self._press:
      px, py, previous, token = self._press
      if (abs(x - px) > 5 or abs(y - py) > 5 or not (_inside_widget(x, y, state, "steering_wheel", (1588, 75, 1780, 267)))
          or previous != state.experimental_enabled or token != state.experimental_action_token or not state.experimental_available or
          state.appearance.hide_steering_wheel):
        self.cancel()

  def release(self, x: float, y: float, state: OnroadState) -> None:
    self.move(x, y, state)
    if self._source_press:
      self.emit(OnroadRequest('set_speed_sources', not self._source_press[3]))
    if self._slc_press:
      self.emit(self._slc_press[2])
    if self._press:
      self.emit(OnroadRequest("set_experimental", not self._press[2], self._press[3]))
    self.cancel()

  def cancel(self) -> None:
    self._press = None
    self._slc_press = None
    self._source_press = None


class SlcStateMessage(Protocol):
  """The small UI-facing subset of the planned SLC schema message."""

  observationKind: str
  source: str
  speedLimit: float
  offset: float
  pendingSpeedLimit: float
  effectiveCap: float
  acceptedSpeedLimit: float
  hasPending: bool
  hasCeiling: bool
  hasAccepted: bool
  sessionId: str
  decisionId: int
  presentationId: int
  status: str
  enabled: bool
  actionSequenceId: int
  actionStatus: str


def source_readings_from_message(message):
  rows = []
  for row in getattr(message, 'sourceReadings', ()):
    source, kind = str(row.source), str(row.observationKind)
    if source not in ('dashboard', 'map', 'vision', 'online') or source in {item.source for item in rows}:
      continue
    value = float(row.speedLimit) if kind == 'valid' else None
    if value is not None and (not math.isfinite(value) or value <= 0):
      kind, value = 'unknown', None
    rows.append(SourceReading(source, bool(row.enabled), kind, value))
  return tuple(rows)


def speed_limit_from_message(message: SlcStateMessage | None) -> SpeedLimitObservation:
  """Map explicit SLC observation semantics without assuming a live service.

  The caller checks message freshness and passes ``None`` for missing or stale
  transport. Native numeric defaults cannot become a valid speed limit here.
  """
  if message is None:
    return SpeedLimitObservation(kind=ObservationKind.UNKNOWN)
  try:
    kind = ObservationKind(message.observationKind)
  except (ValueError, AttributeError):
    return SpeedLimitObservation(kind=ObservationKind.UNKNOWN, status="Invalid SLC observation kind")
  if kind != ObservationKind.VALID:
    return SpeedLimitObservation(kind=kind, source=message.source, status=message.status)
  try:
    return SpeedLimitObservation(kind=kind, source=message.source, speed_limit_mps=message.speedLimit,
                                 source_readings=source_readings_from_message(message),
                                 offset_mps=message.offset,
                                 pending_speed_limit_mps=message.pendingSpeedLimit if message.hasPending else None,
                                 effective_cap_mps=message.effectiveCap if message.hasCeiling else None,
                                 accepted_speed_limit_mps=message.acceptedSpeedLimit if message.hasAccepted else None,
                                 accepted_source=str(getattr(message, "acceptedSource", "none")) or "none",
                                 pending_source=str(getattr(message, "pendingSource", "none")) or "none",
                                 effective_cluster_target_mps=(getattr(message, "effectiveClusterTarget", None)
                                   if getattr(message, "hasEffectiveClusterTarget", False) else None),
                                 limiting_max_set=bool(getattr(message, "isLimitingMaxSet", False)),
                                 driver_override_active=bool(getattr(message, "driverOverrideActive", False)),
                                 session_id=message.sessionId, decision_id=message.decisionId,
                                 presentation_id=message.presentationId, status=message.status,
                                 action_enabled=bool(getattr(message, "enabled", False)),
                                 action_sequence_id=int(getattr(message, "actionSequenceId", 0)),
                                 action_status=str(getattr(message, "actionStatus", "")),
                                 accepted_adjusted_limit_mps=(getattr(message, 'acceptedAdjustedLimit', None)
                                   if getattr(message, 'hasAcceptedAdjustedLimit', False) else None),
                                 pending_adjusted_limit_mps=(getattr(message, 'pendingAdjustedLimit', None)
                                   if getattr(message, 'hasPendingAdjustedLimit', False) else None),
                                 presentation_adjusted_limit_mps=(getattr(message, 'presentationAdjustedLimit', None)
                                   if getattr(message, 'hasPresentationAdjustedLimit', False) else None),
                                 override_basis=str(getattr(message, 'overrideBasis', 'none')),
                                 retained_override=bool(getattr(message, 'retainedOverride', False)),
                                 command_action_sequence_id=int(getattr(message, 'commandActionSequenceId', 0)),
                                 command_status=str(getattr(message, 'commandStatus', '')))
  except (ValueError, TypeError, AttributeError, OverflowError):
    return SpeedLimitObservation(kind=ObservationKind.UNKNOWN, source=message.source,
                                 status="Invalid SLC numeric observation")
