import pytest

from openpilot.common.constants import CV
from openpilot.selfdrive.ui.onroad.starpilot.unified_speed_presentation import resolve_unified_speed


def slc_state(posted_mph=65, offset_mph=0, source="Map Data", *, pending_mph=0,
              enabled=True, limiting=False, overridden=False, metric=False):
  conversion = CV.MS_TO_KPH if metric else CV.MS_TO_MPH
  return {
    "accepted_speed_limit_ms": posted_mph / conversion,
    "effective_target_ms": max(0, posted_mph + offset_mph) / conversion,
    "offset_ms": offset_mph / conversion,
    "speed_conversion": conversion,
    "unconfirmed_speed_limit": pending_mph,
    "unconfirmed_valid": pending_mph > 0,
    "speed_limit_changed": pending_mph > 0,
    "presented_source": source,
    "slc_enabled": enabled,
    "slc_is_limiting_max_set": limiting,
    "slc_overridden_speed": 1.0 if overridden else 0.0,
  }


@pytest.mark.parametrize("max_speed,posted,offset,expected_mode", [
  (80, 65, 5, "split"),
  (70, 70, 0, "merged"),
  (70, 65, 5, "merged"),
  (70, 65, 4, "split"),
  (65, 70, -5, "merged"),
])
def test_split_and_merge_use_effective_accepted_limit(max_speed, posted, offset, expected_mode):
  result = resolve_unified_speed(True, True, max_speed, slc_state(posted, offset), True, False)
  assert result.mode == expected_mode
  assert result.posted_speed_text == str(posted)
  assert result.effective_speed_text == str(posted + offset)
  assert result.offset_text == (f"{offset:+d}" if offset else None)


def test_pending_candidate_forces_split_without_replacing_accepted_target():
  state = slc_state(65, 5, source="Vision", pending_mph=75)
  result = resolve_unified_speed(True, True, 70, state, True, False)
  assert result.mode == "split"
  assert result.confirmation_pending
  assert result.posted_speed_text == "75"
  assert result.effective_speed_text == "70"
  assert result.source == "Vision"


def test_resolution_after_confirmation_uses_same_equality_rule():
  state = slc_state(65, 5, pending_mph=75)
  assert resolve_unified_speed(True, True, 70, state, True, False).mode == "split"
  state["speed_limit_changed"] = state["unconfirmed_valid"] = False
  assert resolve_unified_speed(True, True, 70, state, True, False).mode == "merged"
  assert resolve_unified_speed(True, True, 80, state, True, False).mode == "split"


def test_source_change_and_override_do_not_change_layout():
  state = slc_state(65, 5)
  assert resolve_unified_speed(True, True, 70, state, True, False).mode == "merged"
  state["presented_source"] = "Vision"
  result = resolve_unified_speed(True, True, 70, state, True, False)
  assert result.mode == "merged"
  assert result.source == "Vision"
  state["presented_source"] = "Dashboard"
  state["slc_overridden_speed"] = 40.0
  result = resolve_unified_speed(True, True, 70, state, True, False)
  assert result.mode == "merged"
  assert result.source == "Dashboard"


def test_source_target_change_recomputes_layout_independently():
  state = slc_state(65, 5, source="Map Data")
  assert resolve_unified_speed(True, True, 70, state, True, False).mode == "merged"
  state.update(slc_state(55, 5, source="Vision"))
  result = resolve_unified_speed(True, True, 70, state, True, False)
  assert result.mode == "split"
  assert result.source == "Vision"


def test_active_side_uses_published_control_semantic():
  state = slc_state(65, 5, limiting=True)
  assert resolve_unified_speed(True, True, 80, state, True, False).active_side == "slc"
  state["slc_is_limiting_max_set"] = False
  assert resolve_unified_speed(True, True, 80, state, True, False).active_side == "max"
  state["slc_overridden_speed"] = 40.0
  assert resolve_unified_speed(True, True, 80, state, True, False).active_side == "none"


def test_display_only_speed_limit_stays_split():
  result = resolve_unified_speed(True, True, 70, slc_state(70, enabled=False), False, False)
  assert result.mode == "split"


def test_disabled_confirmation_does_not_force_split():
  state = slc_state(65, 5, pending_mph=75)
  state["speed_limit_changed"] = False
  assert resolve_unified_speed(True, True, 70, state, True, False).mode == "merged"


def test_missing_limit_never_renders_zero_or_a_stale_source():
  result = resolve_unified_speed(True, True, 70, slc_state(0, source="None"), True, False)
  assert result.mode == "split"
  assert result.posted_speed_text == "–"
  assert result.effective_speed_text == "–"
  assert result.source == "None"


def test_missing_limit_with_slc_disabled_allows_max_only():
  result = resolve_unified_speed(True, True, 70, slc_state(0, source="None", enabled=False), False, False)
  assert result.mode == "max_only"


@pytest.mark.parametrize("show_max,expected_mode", [(True, "split"), (False, "limit_only")])
def test_stale_slc_data_keeps_speed_limit_region(show_max, expected_mode):
  result = resolve_unified_speed(show_max, True, 70, None, True, False)
  assert result.mode == expected_mode
  assert result.posted_speed_text == "–"
  assert result.effective_speed_text == "–"
  assert result.source == "None"


def test_missing_data_with_slc_disabled_uses_max_only():
  assert resolve_unified_speed(True, True, 70, None, False, False).mode == "max_only"


def test_persisted_previous_limit_without_source_remains_visible():
  result = resolve_unified_speed(True, True, 70, slc_state(45, source="Previous Limit"), True, False)
  assert result.mode == "split"
  assert result.posted_speed_text == "45"
  assert result.source == "Previous Limit"


def test_low_limit_with_large_negative_offset_preserves_configured_offset():
  result = resolve_unified_speed(True, True, 70, slc_state(5, -99), True, False)
  assert result.mode == "split"
  assert result.posted_speed_text == "5"
  assert result.effective_speed_text == "–"
  assert result.offset_text == "-99"


def test_metric_and_rounding_follow_the_displayed_value():
  state = slc_state(65.4, 4.4, metric=True)
  result = resolve_unified_speed(True, True, 70, state, True, True)
  assert result.mode == "merged"
  assert result.posted_speed_text == "65"
  assert result.offset_text == "+4"
  assert result.unit_text == "km/h"


def test_invisible_fraction_does_not_keep_card_split():
  state = slc_state(65.1, 5.2)
  result = resolve_unified_speed(True, True, 70.4, state, True, False)
  assert result.mode == "merged"


def test_hidden_max_still_shows_posted_limit():
  result = resolve_unified_speed(False, True, 70, slc_state(65), True, False)
  assert result.mode == "limit_only"
  result = resolve_unified_speed(False, True, 70, slc_state(65, enabled=False), False, False)
  assert result.mode == "limit_only"


def test_confirmation_forces_split_even_when_max_is_hidden():
  result = resolve_unified_speed(False, True, 70, slc_state(65, pending_mph=75), True, False)
  assert result.mode == "split"
  assert result.max_speed_text == "70"
  assert result.confirmation_pending


def test_offset_max_pending_and_source_transitions_recompute_mode():
  state = slc_state(65)
  assert resolve_unified_speed(True, True, 70, state, True, False).mode == "split"
  state.update(slc_state(65, 5))
  assert resolve_unified_speed(True, True, 70, state, True, False).mode == "merged"
  assert resolve_unified_speed(True, True, 75, state, True, False).mode == "split"
  state.update(slc_state(65, 5, pending_mph=75))
  assert resolve_unified_speed(True, True, 70, state, True, False).mode == "split"
  state.update(slc_state(65, 5))
  assert resolve_unified_speed(True, True, 70, state, True, False).mode == "merged"
  state.update(slc_state(0, source="None"))
  missing = resolve_unified_speed(True, True, 70, state, True, False)
  assert missing.mode == "split"
  assert missing.posted_speed_text == "–"
  state.update(slc_state(65, 5))
  assert resolve_unified_speed(True, True, 70, state, True, False).mode == "merged"
