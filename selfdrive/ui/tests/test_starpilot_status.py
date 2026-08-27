from types import SimpleNamespace

from openpilot.selfdrive.ui.lib.starpilot_status import (
  DISENGAGED_COLOR,
  ENGAGED_COLOR,
  EXPERIMENTAL_COLOR,
  HYBRID_EXPERIMENTAL_COLOR,
  LONGITUDINAL_ONLY_COLOR,
  AOL_COLOR,
  OVERRIDE_COLOR,
  get_border_color,
  get_path_edge_color,
  get_screen_edge_color,
)
from openpilot.selfdrive.ui.ui_state import UIStatus


def _state(*, enabled=False, lat_active=False, aol=False, status=None, events=(), hybrid=False, hem_exp_dominant=None):
  params_memory = {"HEMExpDominant": b"1"} if hem_exp_dominant else {}
  return SimpleNamespace(
    sm={
      "selfdriveState": SimpleNamespace(enabled=enabled, experimentalMode=False),
      "carControl": SimpleNamespace(latActive=lat_active),
      "onroadEvents": events,
    },
    status=status if status is not None else (UIStatus.ENGAGED if enabled else UIStatus.DISENGAGED),
    always_on_lateral_active=aol,
    switchback_mode_enabled=False,
    traffic_mode_enabled=False,
    conditional_status=0,
    starpilot_toggles={"hybrid_experimental_mode": hybrid},
    params_memory=SimpleNamespace(get=lambda key, default=None: params_memory.get(key, default)),
  )


def _rgb(color):
  return color.r, color.g, color.b


def test_cruise_only_uses_pink_for_border_and_screen_edge():
  state = _state(enabled=True, lat_active=False)

  assert _rgb(get_border_color(state)) == _rgb(LONGITUDINAL_ONLY_COLOR)
  assert _rgb(get_screen_edge_color(state)) == _rgb(LONGITUDINAL_ONLY_COLOR)


def test_lateral_active_colors_remain_unchanged():
  assert _rgb(get_border_color(_state(enabled=True, lat_active=True))) == _rgb(ENGAGED_COLOR)
  assert _rgb(get_border_color(_state(aol=True))) == _rgb(AOL_COLOR)
  assert _rgb(get_border_color(_state())) == _rgb(DISENGAGED_COLOR)


def test_hybrid_experimental_mode_uses_blue_border():
  state = _state(enabled=True, lat_active=True, hybrid=True)

  assert _rgb(get_border_color(state)) == _rgb(HYBRID_EXPERIMENTAL_COLOR)
  assert _rgb(get_screen_edge_color(state)) == _rgb(HYBRID_EXPERIMENTAL_COLOR)
  assert _rgb(get_path_edge_color(state)) == _rgb(HYBRID_EXPERIMENTAL_COLOR)


def test_hybrid_experimental_mode_uses_orange_when_exp_dominates():
  state = _state(enabled=True, lat_active=True, hybrid=True, hem_exp_dominant=True)

  assert _rgb(get_border_color(state)) == _rgb(EXPERIMENTAL_COLOR)
  assert _rgb(get_screen_edge_color(state)) == _rgb(EXPERIMENTAL_COLOR)
  assert _rgb(get_path_edge_color(state)) == _rgb(EXPERIMENTAL_COLOR)


def test_hybrid_experimental_mode_keeps_blue_when_chill_dominates():
  state = _state(enabled=True, lat_active=True, hybrid=True, hem_exp_dominant=False)

  assert _rgb(get_border_color(state)) == _rgb(HYBRID_EXPERIMENTAL_COLOR)
  assert _rgb(get_screen_edge_color(state)) == _rgb(HYBRID_EXPERIMENTAL_COLOR)
  assert _rgb(get_path_edge_color(state)) == _rgb(HYBRID_EXPERIMENTAL_COLOR)


def test_hybrid_experimental_mode_requires_enabled():
  assert _rgb(get_border_color(_state(hybrid=True))) == _rgb(DISENGAGED_COLOR)
  assert _rgb(get_border_color(_state(enabled=True, lat_active=True))) == _rgb(ENGAGED_COLOR)


def test_override_color_matches_active_control_mode():
  lateral_override = SimpleNamespace(overrideLateral=True, overrideLongitudinal=False)
  longitudinal_override = SimpleNamespace(overrideLateral=False, overrideLongitudinal=True)
  override = UIStatus.OVERRIDE

  # Green: either active-control override is gray.
  assert _rgb(get_border_color(_state(enabled=True, lat_active=True, status=override, events=[lateral_override]))) == _rgb(OVERRIDE_COLOR)
  assert _rgb(get_border_color(_state(enabled=True, lat_active=True, status=override, events=[longitudinal_override]))) == _rgb(OVERRIDE_COLOR)

  # Pink: steering is already inactive, so only a longitudinal override is gray.
  pink_state = _state(enabled=True, status=override, events=[lateral_override])
  assert _rgb(get_border_color(pink_state)) == _rgb(LONGITUDINAL_ONLY_COLOR)
  assert _rgb(get_border_color(_state(enabled=True, status=override, events=[longitudinal_override]))) == _rgb(OVERRIDE_COLOR)

  # Blue/AOL: longitudinal override is inactive, so only steering is gray.
  assert _rgb(get_border_color(_state(aol=True, status=override, events=[lateral_override]))) == _rgb(OVERRIDE_COLOR)
  assert _rgb(get_border_color(_state(aol=True, status=override, events=[longitudinal_override]))) == _rgb(AOL_COLOR)
