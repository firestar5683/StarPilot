import pyray as rl

from openpilot.selfdrive.ui.ui_state import UIStatus, UIState

CEM_DISABLED_OVERRIDE_STATUSES = {1}
CEM_MANUAL_OVERRIDE_STATUSES = {1, 2}
CEM_ACTIVE_STATUSES = {3, 4, 5, 6, 7, 8}

DISENGAGED_COLOR = rl.Color(18, 40, 57, 255)
AOL_COLOR = rl.Color(10, 186, 181, 255)
ENGAGED_COLOR = rl.Color(22, 127, 64, 255)
OVERRIDE_COLOR = rl.Color(137, 146, 141, 255)
EXPERIMENTAL_COLOR = rl.Color(218, 111, 37, 255)
HYBRID_EXPERIMENTAL_COLOR = rl.Color(0, 153, 255, 255)
CEM_OVERRIDE_COLOR = rl.Color(255, 214, 0, 255)
SWITCHBACK_COLOR = rl.Color(139, 108, 197, 255)
TRAFFIC_COLOR = rl.Color(201, 34, 49, 255)
LONGITUDINAL_ONLY_COLOR = rl.Color(255, 105, 180, 255)


def is_longitudinal_only_active(state: UIState) -> bool:
  """Return true when control is enabled but lateral control is inactive.

  Do not use carControl.longActive here: stock-cruise cars intentionally leave
  that field false while the vehicle's own longitudinal controller is active.
  """
  car_control = state.sm["carControl"]
  return bool(state.sm["selfdriveState"].enabled and not car_control.latActive)


def _is_hybrid_experimental_mode(state: UIState) -> bool:
  """True when HEM (hybrid experimental) is the active longitudinal mode."""
  return bool(state.starpilot_toggles.get("hybrid_experimental_mode", False))


def _hem_exp_dominant(state: UIState) -> bool:
  """True when the fused output tracks the E2E/vision input more than chill ACC.

  Uses the planner's per-frame comparison (HEMExpDominant), which reflects the
  active fusion regime rather than a raw vision weight.
  """
  params_memory = getattr(state, "params_memory", None)
  if params_memory is None:
    return False
  try:
    return bool(int(params_memory.get("HEMExpDominant") or 0))
  except (TypeError, ValueError):
    return False


def _hem_border_color(state: UIState) -> rl.Color:
  """Blue when chill dominates the fusion, orange when experimental/vision dominates (like CEM)."""
  return EXPERIMENTAL_COLOR if _hem_exp_dominant(state) else HYBRID_EXPERIMENTAL_COLOR


def _override_color_applies(state: UIState) -> bool:
  """Only gray the status when the active control mode is being overridden."""
  if state.status != UIStatus.OVERRIDE:
    return False

  events = state.sm["onroadEvents"]
  lateral_override = any(getattr(event, "overrideLateral", False) for event in events)
  longitudinal_override = any(getattr(event, "overrideLongitudinal", False) for event in events)

  if is_longitudinal_only_active(state):
    return longitudinal_override
  if state.always_on_lateral_active and not state.sm["selfdriveState"].enabled:
    return lateral_override
  return lateral_override or longitudinal_override


def get_border_color(state: UIState):
  enabled = state.sm["selfdriveState"].enabled
  lateral_active = enabled or state.always_on_lateral_active
  if _override_color_applies(state):
    return OVERRIDE_COLOR
  if is_longitudinal_only_active(state):
    return LONGITUDINAL_ONLY_COLOR
  if state.switchback_mode_enabled and lateral_active:
    return SWITCHBACK_COLOR
  if state.traffic_mode_enabled and enabled:
    return TRAFFIC_COLOR
  if state.always_on_lateral_active:
    return AOL_COLOR
  # Only color the border for CEM/experimental while actually enabled.
  if enabled and _is_hybrid_experimental_mode(state):
    return _hem_border_color(state)
  if enabled and state.conditional_status in CEM_DISABLED_OVERRIDE_STATUSES:
    return CEM_OVERRIDE_COLOR
  if enabled and state.sm["selfdriveState"].experimentalMode:
    return EXPERIMENTAL_COLOR
  if state.status == UIStatus.ENGAGED:
    return ENGAGED_COLOR
  return DISENGAGED_COLOR


def get_path_edge_color(state: UIState):
  if state.sm["selfdriveState"].enabled and _is_hybrid_experimental_mode(state):
    return _hem_border_color(state)
  if state.conditional_status in CEM_ACTIVE_STATUSES:
    return EXPERIMENTAL_COLOR
  return get_border_color(state)


def get_screen_edge_color(state: UIState):
  enabled = state.sm["selfdriveState"].enabled
  lateral_active = enabled or state.always_on_lateral_active
  if _override_color_applies(state):
    return OVERRIDE_COLOR
  if is_longitudinal_only_active(state):
    return LONGITUDINAL_ONLY_COLOR
  if state.switchback_mode_enabled and lateral_active:
    return SWITCHBACK_COLOR
  if state.always_on_lateral_active:
    return AOL_COLOR
  # Keep the screen edge disengaged-blue when experimental mode is only the
  # requested longitudinal mode, not the active driving state.
  if enabled and _is_hybrid_experimental_mode(state):
    return _hem_border_color(state)
  if enabled and state.conditional_status in CEM_DISABLED_OVERRIDE_STATUSES:
    return CEM_OVERRIDE_COLOR
  if enabled and state.sm["selfdriveState"].experimentalMode:
    return EXPERIMENTAL_COLOR
  if state.traffic_mode_enabled and enabled:
    return TRAFFIC_COLOR
  return get_border_color(state)


def get_experimental_mode_banner_text(state: UIState):
  conditional_enabled = state.params.get_bool("ConditionalExperimental")

  # With CEM enabled, only surface banner text for explicit manual override states.
  # Automatic CEM transitions should only be reflected by path/border coloring.
  if conditional_enabled:
    if state.conditional_status in CEM_MANUAL_OVERRIDE_STATUSES:
      return "OVERRIDDEN"
    return None

  if state.sm["selfdriveState"].experimentalMode:
    return "EXPERIMENTAL"
  return "CHILL"


def get_mode_transition_banner_text(state: UIState):
  enabled = state.sm["selfdriveState"].enabled
  lateral_active = enabled or state.always_on_lateral_active
  conditional_enabled = state.params.get_bool("ConditionalExperimental")

  if state.status == UIStatus.OVERRIDE:
    return "OVERRIDE"
  if state.switchback_mode_enabled and lateral_active:
    return "SWITCHBACK"
  if conditional_enabled and enabled and state.conditional_status in CEM_MANUAL_OVERRIDE_STATUSES:
    return "OVERRIDDEN"
  if enabled and state.sm["selfdriveState"].experimentalMode:
    return "EXPERIMENTAL"
  if enabled:
    return "CHILL"
  return None
