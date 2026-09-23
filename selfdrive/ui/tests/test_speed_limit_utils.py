import importlib.util
import sys
import unittest
from types import SimpleNamespace
from pathlib import Path

from openpilot.common.constants import CV


UI_SPEED_LIMIT_PATH = Path(__file__).resolve().parents[1] / "lib" / "speed_limit.py"
UI_SPEED_LIMIT_SPEC = importlib.util.spec_from_file_location("ui_speed_limit_under_test", UI_SPEED_LIMIT_PATH)
UI_SPEED_LIMIT = importlib.util.module_from_spec(UI_SPEED_LIMIT_SPEC)
assert UI_SPEED_LIMIT_SPEC is not None and UI_SPEED_LIMIT_SPEC.loader is not None
sys.modules[UI_SPEED_LIMIT_SPEC.name] = UI_SPEED_LIMIT
UI_SPEED_LIMIT_SPEC.loader.exec_module(UI_SPEED_LIMIT)
speed_limit_override_mode = UI_SPEED_LIMIT.speed_limit_override_mode
max_matches_speed_limit = UI_SPEED_LIMIT.max_matches_speed_limit
pending_speed_limit_offset = UI_SPEED_LIMIT.pending_speed_limit_offset

MICI_SPEED_LIMIT_PATH = Path(__file__).resolve().parents[1] / "mici" / "onroad" / "speed_limit_utils.py"
MICI_SPEED_LIMIT_SPEC = importlib.util.spec_from_file_location("mici_speed_limit_under_test", MICI_SPEED_LIMIT_PATH)
MICI_SPEED_LIMIT = importlib.util.module_from_spec(MICI_SPEED_LIMIT_SPEC)
assert MICI_SPEED_LIMIT_SPEC is not None and MICI_SPEED_LIMIT_SPEC.loader is not None
sys.modules[MICI_SPEED_LIMIT_SPEC.name] = MICI_SPEED_LIMIT
MICI_SPEED_LIMIT_SPEC.loader.exec_module(MICI_SPEED_LIMIT)
resolve_display_speed_limit_ms = MICI_SPEED_LIMIT.resolve_display_speed_limit_ms


class TestSpeedLimitUtils(unittest.TestCase):
  def test_resolve_display_speed_limit_prefers_slc_target(self):
    speed_limit = resolve_display_speed_limit_ms(
      slc_speed_limit=24.6,
      speed_limit_source="Dashboard",
      source_limits={
        "Dashboard": 22.4,
        "Map Data": 20.1,
        "Vision": 0.0,
        "Mapbox": 0.0,
      },
      primary_priority="Map Data",
      secondary_priority="Dashboard",
    )

    self.assertEqual(speed_limit, 24.6)

  def test_max_and_pedal_override_are_displayed_separately(self):
    limit = 65 * CV.MPH_TO_MS
    plan = SimpleNamespace(
      slcSpeedLimit=limit,
      slcSpeedLimitOffset=0.0,
      slcSpeedLimitSource="Dashboard",
      slcOverriddenSpeed=70 * CV.MPH_TO_MS,
      unconfirmedSlcSpeedLimit=0.0,
      speedLimitChanged=False,
    )

    pedal_mode = speed_limit_override_mode(plan, True)
    manual_mode = speed_limit_override_mode(plan, False)

    self.assertEqual(pedal_mode, "pedal")
    self.assertEqual(manual_mode, "manual")
    self.assertTrue(max_matches_speed_limit(plan, 65 * CV.MPH_TO_KPH, False, fallback_mode=2))

  def test_max_stays_visible_while_a_different_limit_is_pending(self):
    limit = 65 * CV.MPH_TO_MS
    plan = SimpleNamespace(
      slcSpeedLimit=limit,
      slcSpeedLimitOffset=-2 * CV.MPH_TO_MS,
      slcSpeedLimitSource="None",
      slcOverriddenSpeed=0.0,
      unconfirmedSlcSpeedLimit=70 * CV.MPH_TO_MS,
      speedLimitChanged=True,
    )

    matches = max_matches_speed_limit(plan, 63 * CV.MPH_TO_KPH, False, fallback_mode=2)

    self.assertFalse(matches)
    plan.speedLimitChanged = False
    self.assertTrue(max_matches_speed_limit(plan, 63 * CV.MPH_TO_KPH, False, fallback_mode=2))

  def test_set_speed_offset_makes_effective_max_distinct_from_limit(self):
    target = 65 * CV.MPH_TO_MS
    plan = SimpleNamespace(
      slcSpeedLimit=target,
      slcSpeedLimitOffset=0.0,
      slcSpeedLimitSource="Dashboard",
      slcOverriddenSpeed=0.0,
      unconfirmedSlcSpeedLimit=0.0,
      speedLimitChanged=False,
    )

    raw_max_speed_kph = 65 * CV.MPH_TO_KPH
    set_speed_offset_kph = 2 * CV.MPH_TO_KPH

    self.assertTrue(max_matches_speed_limit(plan, raw_max_speed_kph, False, fallback_mode=2))
    self.assertFalse(
      max_matches_speed_limit(plan, raw_max_speed_kph + set_speed_offset_kph, False, fallback_mode=2)
    )

  def test_cruise_fallback_hides_duplicate_max_when_it_matches_target(self):
    target = 65 * CV.MPH_TO_MS
    plan = SimpleNamespace(
      slcSpeedLimit=target,
      slcSpeedLimitOffset=0.0,
      slcSpeedLimitSource="None",
      slcOverriddenSpeed=0.0,
      unconfirmedSlcSpeedLimit=0.0,
      speedLimitChanged=False,
    )

    matches = max_matches_speed_limit(plan, 65 * CV.MPH_TO_KPH, False, fallback_mode=0)

    self.assertTrue(matches)

  def test_pending_limit_uses_its_own_speed_band_offset(self):
    toggles = {
      "speed_limit_offset3": 2 * CV.MPH_TO_MS,
      "speed_limit_offset4": 5 * CV.MPH_TO_MS,
    }

    offset = pending_speed_limit_offset(45 * CV.MPH_TO_MS, False, toggles)

    self.assertAlmostEqual(offset, 5 * CV.MPH_TO_MS)

  def test_pending_limit_offset_is_returned_in_meters_per_second(self):
    toggles = {"speed_limit_offset2": -3 * CV.KPH_TO_MS}

    offset = pending_speed_limit_offset(45 * CV.KPH_TO_MS, True, toggles)

    self.assertAlmostEqual(offset, -3 * CV.KPH_TO_MS)

  def test_resolve_display_speed_limit_ignores_unconfigured_active_source(self):
    speed_limit = resolve_display_speed_limit_ms(
      slc_speed_limit=0.0,
      speed_limit_source="Dashboard",
      source_limits={
        "Dashboard": 22.4,
        "Map Data": 20.1,
        "Vision": 0.0,
        "Mapbox": 0.0,
      },
      primary_priority="Map Data",
      secondary_priority="Vision",
    )

    self.assertEqual(speed_limit, 20.1)

  def test_resolve_display_speed_limit_uses_configured_active_source_when_display_only(self):
    speed_limit = resolve_display_speed_limit_ms(
      slc_speed_limit=0.0,
      speed_limit_source="Dashboard",
      source_limits={
        "Dashboard": 22.4,
        "Map Data": 20.1,
        "Vision": 0.0,
        "Mapbox": 0.0,
      },
      primary_priority="Map Data",
      secondary_priority="Dashboard",
    )

    self.assertEqual(speed_limit, 22.4)

  def test_resolve_display_speed_limit_honors_priority_order(self):
    speed_limit = resolve_display_speed_limit_ms(
      slc_speed_limit=0.0,
      speed_limit_source="None",
      source_limits={
        "Dashboard": 22.4,
        "Map Data": 20.1,
        "Vision": 24.6,
        "Mapbox": 0.0,
      },
      primary_priority="Map Data",
      secondary_priority="Vision",
    )

    self.assertEqual(speed_limit, 20.1)

  def test_resolve_display_speed_limit_falls_back_to_mapbox(self):
    speed_limit = resolve_display_speed_limit_ms(
      slc_speed_limit=0.0,
      speed_limit_source="None",
      source_limits={
        "Dashboard": 0.0,
        "Map Data": 0.0,
        "Vision": 0.0,
        "Mapbox": 17.9,
      },
      primary_priority="Map Data",
      secondary_priority="Dashboard",
    )

    self.assertEqual(speed_limit, 17.9)

  def test_resolve_display_speed_limit_does_not_fallback_to_dashboard_when_vision_only(self):
    speed_limit = resolve_display_speed_limit_ms(
      slc_speed_limit=0.0,
      speed_limit_source="None",
      source_limits={
        "Dashboard": 22.4,
        "Map Data": 0.0,
        "Vision": 0.0,
        "Mapbox": 0.0,
      },
      primary_priority="Vision",
      secondary_priority="None",
    )

    self.assertEqual(speed_limit, 0.0)
