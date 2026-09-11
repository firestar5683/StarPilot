from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from openpilot.common.constants import CV
from openpilot.common.realtime import DT_MDL
from openpilot.starpilot.controls.lib.speed_limit_controller import SpeedLimitController


class FakeParams:
  def __init__(self, initial=None):
    self.values = dict(initial or {})

  def get(self, key, encoding=None):
    return self.values.get(key)

  def get_bool(self, key):
    return bool(self.values.get(key, False))

  def get_float(self, key):
    return float(self.values.get(key, 0) or 0)

  def get_int(self, key):
    return int(self.values.get(key, 0) or 0)

  def put_float(self, key, value):
    self.values[key] = value

  def put_int(self, key, value):
    self.values[key] = value

  def put_nonblocking(self, key, value):
    self.values[key] = value

  def remove(self, key):
    self.values.pop(key, None)


def make_toggles(**overrides):
  defaults = {
    "is_metric": False,
    "map_speed_lookahead_higher": 0.0,
    "map_speed_lookahead_lower": 0.0,
    "slc_fallback_previous_speed_limit": False,
    "slc_fallback_set_speed": False,
    "slc_mapbox_filler": False,
    "speed_limit_confirmation_higher": False,
    "speed_limit_confirmation_lower": False,
    "redneck_cruise": False,
    "speed_limit_filler": False,
    "speed_limit_offset1": 0.0,
    "speed_limit_offset2": 0.0,
    "speed_limit_offset3": 0.0,
    "speed_limit_offset4": 0.0,
    "speed_limit_offset5": 0.0,
    "speed_limit_offset6": 0.0,
    "speed_limit_offset7": 0.0,
    "speed_limit_priority1": "Dashboard",
    "speed_limit_priority2": "Map Data",
    "speed_limit_priority_highest": False,
    "speed_limit_priority_lowest": False,
    "vision_speed_limit_detection": False,
    "vision_speed_limit_low_limit_filter": False,
    "vision_speed_limit_low_limit_threshold": mph(25),
  }
  defaults.update(overrides)
  return SimpleNamespace(**defaults)


def make_sm(*, gas_pressed, enabled=True, accel_pressed=False, decel_pressed=False, long_active=True, v_cruise_kph=255.0):
  return {
    "carControl": SimpleNamespace(longActive=long_active),
    "carState": SimpleNamespace(gasPressed=gas_pressed, steeringAngleDeg=0.0, vCruise=v_cruise_kph),
    "liveParameters": SimpleNamespace(angleOffsetDeg=0.0),
    "mapdOut": SimpleNamespace(nextSpeedLimitDistance=0.0, nextSpeedLimit=0.0, speedLimit=0.0, waySelectionType=0, roadName=""),
    "selfdriveState": SimpleNamespace(enabled=enabled),
    "starpilotCarState": SimpleNamespace(accelPressed=accel_pressed, decelPressed=decel_pressed),
  }


def make_controller(**toggle_overrides):
  params = FakeParams()
  planner = SimpleNamespace(
    gps_position={},
    gps_valid=False,
    params=params,
    params_memory=FakeParams(),
  )
  controller = SpeedLimitController(SimpleNamespace(starpilot_planner=planner))
  controller.starpilot_toggles = make_toggles(**toggle_overrides)
  return controller


def mph(value):
  return value * CV.MPH_TO_MS


@pytest.mark.parametrize("limit_mph", [15, 25])
def test_low_vision_limit_filter_blocks_configured_boundary(limit_mph):
  controller = make_controller(
    speed_limit_priority1="Vision",
    vision_speed_limit_detection=True,
    vision_speed_limit_low_limit_filter=True,
    vision_speed_limit_low_limit_threshold=mph(25),
  )
  try:
    controller.starpilot_planner.params_memory.put_float("VisionSpeedLimit", mph(limit_mph))
    sm = make_sm(gas_pressed=False, v_cruise_kph=25 * CV.MPH_TO_KPH)

    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(25), mph(20), sm)

    assert controller.vision_limit == pytest.approx(mph(limit_mph))
    assert controller.target == 0
    assert controller.source == "None"
  finally:
    controller.shutdown()


def test_low_vision_limit_filter_allows_limit_above_threshold():
  controller = make_controller(
    speed_limit_priority1="Vision",
    vision_speed_limit_detection=True,
    vision_speed_limit_low_limit_filter=True,
    vision_speed_limit_low_limit_threshold=mph(25),
  )
  try:
    controller.starpilot_planner.params_memory.put_float("VisionSpeedLimit", mph(30))
    sm = make_sm(gas_pressed=False, v_cruise_kph=30 * CV.MPH_TO_KPH)

    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(30), mph(25), sm)

    assert controller.target == pytest.approx(mph(30))
    assert controller.source == "Vision"
  finally:
    controller.shutdown()


def test_low_vision_limit_filter_is_action_only_for_display():
  controller = make_controller(
    speed_limit_priority1="Vision",
    vision_speed_limit_detection=True,
    vision_speed_limit_low_limit_filter=True,
    vision_speed_limit_low_limit_threshold=mph(25),
  )
  try:
    controller.starpilot_planner.params_memory.put_float("VisionSpeedLimit", mph(15))
    sm = make_sm(gas_pressed=False, v_cruise_kph=20 * CV.MPH_TO_KPH)

    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(20), mph(15), sm, display_only=True)

    assert controller.target == pytest.approx(mph(15))
    assert controller.source == "Vision"
  finally:
    controller.shutdown()


def test_low_vision_limit_filter_does_not_filter_dashboard_source():
  controller = make_controller(
    speed_limit_priority1="Vision",
    speed_limit_priority2="Dashboard",
    vision_speed_limit_detection=True,
    vision_speed_limit_low_limit_filter=True,
    vision_speed_limit_low_limit_threshold=mph(25),
  )
  try:
    controller.starpilot_planner.params_memory.put_float("VisionSpeedLimit", mph(15))
    sm = make_sm(gas_pressed=False, v_cruise_kph=20 * CV.MPH_TO_KPH)

    controller.update_limits(mph(15), datetime.now(timezone.utc), False, mph(20), mph(15), sm)

    assert controller.target == pytest.approx(mph(15))
    assert controller.source == "Dashboard"
  finally:
    controller.shutdown()


def test_low_vision_limit_filter_does_not_restore_filtered_vision_fallback():
  controller = make_controller(
    speed_limit_priority1="Vision",
    slc_fallback_previous_speed_limit=True,
    vision_speed_limit_detection=True,
    vision_speed_limit_low_limit_filter=True,
    vision_speed_limit_low_limit_threshold=mph(25),
  )
  try:
    controller.previous_source = "Vision"
    controller.previous_target = mph(15)
    controller.starpilot_planner.params_memory.put_float("VisionSpeedLimit", mph(15))
    sm = make_sm(gas_pressed=False, v_cruise_kph=20 * CV.MPH_TO_KPH)

    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(20), mph(15), sm)

    assert controller.target == 0
    assert controller.source == "None"
  finally:
    controller.shutdown()


def test_large_vision_delta_requires_three_detector_frames():
  controller = make_controller(
    speed_limit_priority1="Vision",
    vision_speed_limit_detection=True,
  )
  try:
    controller.starpilot_planner.params_memory.put_float("VisionSpeedLimit", mph(15))
    controller.starpilot_planner.params_memory.put_float("VisionSpeedLimitSupportSpeed", mph(15))
    controller.starpilot_planner.params_memory.put_int("VisionSpeedLimitSupportCount", 2)
    sm = make_sm(gas_pressed=False, v_cruise_kph=75 * CV.MPH_TO_KPH)

    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(75), mph(70), sm)
    assert controller.target == 0

    controller.starpilot_planner.params_memory.put_int("VisionSpeedLimitSupportCount", 3)
    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(75), mph(70), sm)
    assert controller.target == pytest.approx(mph(15))
    assert controller.source == "Vision"
  finally:
    controller.shutdown()


def test_normal_vision_delta_keeps_fast_path():
  controller = make_controller(
    speed_limit_priority1="Vision",
    vision_speed_limit_detection=True,
  )
  try:
    controller.starpilot_planner.params_memory.put_float("VisionSpeedLimit", mph(50))
    sm = make_sm(gas_pressed=False, v_cruise_kph=75 * CV.MPH_TO_KPH)

    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(75), mph(70), sm)
    assert controller.target == pytest.approx(mph(50))
    assert controller.source == "Vision"
  finally:
    controller.shutdown()


def test_inactive_valid_cruise_still_applies_large_delta_guard():
  controller = make_controller(
    speed_limit_priority1="Vision",
    vision_speed_limit_detection=True,
  )
  try:
    controller.starpilot_planner.params_memory.put_float("VisionSpeedLimit", mph(20))
    sm = make_sm(gas_pressed=False, long_active=False, v_cruise_kph=60 * CV.MPH_TO_KPH)

    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(60), mph(25), sm)
    assert controller.target == 0
    assert controller.source == "None"
  finally:
    controller.shutdown()


def test_unset_active_cruise_uses_vehicle_speed():
  controller = make_controller(
    speed_limit_priority1="Vision",
    vision_speed_limit_detection=True,
  )
  try:
    controller.starpilot_planner.params_memory.put_float("VisionSpeedLimit", mph(55))
    sm = make_sm(gas_pressed=False)

    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(90), mph(50), sm)
    assert controller.target == pytest.approx(mph(55))
    assert controller.source == "Vision"
  finally:
    controller.shutdown()


def test_unset_cruise_applies_vehicle_speed_large_delta_guard():
  controller = make_controller(
    speed_limit_priority1="Vision",
    vision_speed_limit_detection=True,
  )
  try:
    controller.starpilot_planner.params_memory.put_float("VisionSpeedLimit", mph(15))
    controller.starpilot_planner.params_memory.put_float("VisionSpeedLimitSupportSpeed", mph(15))
    controller.starpilot_planner.params_memory.put_int("VisionSpeedLimitSupportCount", 2)
    sm = make_sm(gas_pressed=False)

    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(90), mph(75), sm)
    assert controller.target == 0
    assert controller.source == "None"

    controller.starpilot_planner.params_memory.put_int("VisionSpeedLimitSupportCount", 3)
    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(90), mph(75), sm)
    assert controller.target == pytest.approx(mph(15))
    assert controller.source == "Vision"
  finally:
    controller.shutdown()


def test_display_only_applies_large_delta_guard():
  controller = make_controller(
    speed_limit_priority1="Vision",
    vision_speed_limit_detection=True,
  )
  try:
    controller.starpilot_planner.params_memory.put_float("VisionSpeedLimit", mph(15))
    controller.starpilot_planner.params_memory.put_float("VisionSpeedLimitSupportSpeed", mph(15))
    controller.starpilot_planner.params_memory.put_int("VisionSpeedLimitSupportCount", 1)
    sm = make_sm(gas_pressed=False, v_cruise_kph=75 * CV.MPH_TO_KPH)

    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(75), mph(70), sm, display_only=True)
    assert controller.target == 0
    assert controller.source == "None"

    controller.starpilot_planner.params_memory.put_int("VisionSpeedLimitSupportCount", 3)
    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(75), mph(70), sm, display_only=True)
    assert controller.target == pytest.approx(mph(15))
    assert controller.source == "Vision"
  finally:
    controller.shutdown()


def test_set_speed_override_survives_source_changes_and_fallback_until_driver_clears():
  controller = make_controller(
    speed_limit_priority1="Map Data",
    speed_limit_priority2="Dashboard",
    slc_fallback_set_speed=True,
  )
  try:
    controller.source = "Dashboard"
    controller.target = mph(45)
    controller.previous_source = "Dashboard"
    controller.previous_target = mph(45)
    controller.last_valid_limit = mph(45)

    controller.update_override(mph(45), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    controller.update_override(mph(55), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc

    # Dashboard 45 -> Map Data 45 is not a new speed zone.
    map_sm = make_sm(gas_pressed=False)
    map_sm["mapdOut"].speedLimit = mph(45)
    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(55), mph(50), map_sm)
    controller.update_override(mph(55), 0.0, mph(50), 0.0, map_sm)
    assert controller.source == "Map Data"
    assert controller.overridden_speed == pytest.approx(mph(55))
    assert controller.override_slc

    # A temporary fallback, and even a complete source dropout, do not clear the override.
    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(55), mph(50), make_sm(gas_pressed=False))
    controller.update_override(mph(55), 0.0, mph(50), 0.0, make_sm(gas_pressed=False))
    assert controller.source == "None"
    assert controller.target == pytest.approx(mph(55))
    assert controller.overridden_speed == pytest.approx(mph(55))
    assert controller.override_slc

    controller.starpilot_toggles.slc_fallback_set_speed = False
    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(55), mph(50), make_sm(gas_pressed=False))
    controller.update_override(mph(55), 0.0, mph(50), 0.0, make_sm(gas_pressed=False))
    assert controller.target == 0
    assert controller.overridden_speed == pytest.approx(mph(55))
    assert controller.override_slc

    controller.update_limits(mph(45), datetime.now(timezone.utc), False, mph(55), mph(50), make_sm(gas_pressed=False))
    controller.update_override(mph(55), 0.0, mph(50), 0.0, make_sm(gas_pressed=False))
    assert controller.source == "Dashboard"
    assert controller.overridden_speed == pytest.approx(mph(55))
    assert controller.override_slc

    # Set-speed fallback does not clear passively, but a fresh - to the retained target does.
    controller.starpilot_toggles.slc_fallback_set_speed = True
    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(55), mph(50), make_sm(gas_pressed=False))
    controller.update_override(mph(55), 0.0, mph(50), 0.0, make_sm(gas_pressed=False))
    controller.update_override(mph(45), 0.0, mph(50), 0.0, make_sm(gas_pressed=False))
    assert not controller.override_slc
    assert controller.overridden_speed == 0
  finally:
    controller.shutdown()


def test_unconfirmed_lower_limit_keeps_existing_override():
  # First, verify startup behavior where target is 0 and priority limit is detected
  startup_controller = make_controller(
    speed_limit_priority1="Dashboard",
    slc_fallback_previous_speed_limit=True,
  )
  try:
    startup_controller.previous_target = mph(55)
    startup_controller.previous_source = "Dashboard"
    startup_controller.target = 0

    sm = make_sm(gas_pressed=False)
    startup_controller.update_limits(mph(45), datetime.now(timezone.utc), False, mph(75), mph(65), sm)

    assert startup_controller.target == pytest.approx(mph(45))
    assert startup_controller.source == "Dashboard"
  finally:
    startup_controller.shutdown()

  # Verify Bug 3: Fallback transitions should bypass confirmation checks
  fallback_confirm_controller = make_controller(
    slc_fallback_set_speed=True,
    speed_limit_confirmation_higher=True
  )
  try:
    fallback_confirm_controller.source = "Dashboard"
    fallback_confirm_controller.target = mph(35)
    fallback_confirm_controller.previous_target = mph(35)

    sm = make_sm(gas_pressed=False)
    fallback_confirm_controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(60), mph(35), sm)

    assert fallback_confirm_controller.target == pytest.approx(mph(60))
    assert fallback_confirm_controller.source == "None"
    assert fallback_confirm_controller.unconfirmed_speed_limit == 0
  finally:
    fallback_confirm_controller.shutdown()

  # Verify Bug 1: Boundaries are correctly mapped and not falling back to 0
  boundary_controller = make_controller()
  boundary_controller.starpilot_toggles.speed_limit_offset1 = 1.0
  boundary_controller.starpilot_toggles.speed_limit_offset2 = 2.0

  # Exact boundary speed: 11.2 m/s is the *start* of band 2 (25–34 mph range).
  # With low <= target < high: 11.2 <= 11.2 < 15.2 → True → maps to offset2 (not 0).
  offset = boundary_controller.get_offset(11.2)
  assert offset != 0.0

  controller = make_controller(speed_limit_confirmation_lower=True)
  try:
    controller.source = "Dashboard"
    controller.target = mph(55)
    controller.previous_source = "Dashboard"
    controller.previous_target = mph(55)
    controller.overridden_speed = mph(65)

    sm = make_sm(gas_pressed=True)
    controller.update_limits(mph(45), datetime.now(timezone.utc), False, mph(75), mph(65), sm)
    controller.update_override(mph(75), 0.0, mph(65), 0.0, sm)

    assert controller.target == pytest.approx(mph(55))
    assert controller.unconfirmed_speed_limit == pytest.approx(mph(45))
    assert controller.overridden_speed == pytest.approx(mph(65))
    assert controller.override_slc
  finally:
    controller.shutdown()


def test_set_speed_override_handles_higher_limit_changes():
  controller = make_controller()
  try:
    controller.source = "Dashboard"
    controller.target = mph(35)
    controller.previous_source = "Dashboard"
    controller.previous_target = mph(35)
    controller.last_valid_limit = mph(35)

    controller.update_override(mph(35), 0.0, mph(35), 0.0, make_sm(gas_pressed=False))
    controller.update_override(mph(55), 0.0, mph(35), 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(55))

    # A higher limit below the selected override preserves it.
    controller.update_limits(mph(45), datetime.now(timezone.utc), False, mph(55), mph(50), make_sm(gas_pressed=False))
    controller.update_override(mph(55), 0.0, mph(50), 0.0, make_sm(gas_pressed=False))

    assert controller.target == pytest.approx(mph(45))
    assert controller.source == "Dashboard"
    assert controller.overridden_speed == pytest.approx(mph(55))
    assert controller.override_slc

    # A higher effective target that reaches the override clears it without re-arming.
    controller.update_limits(mph(55), datetime.now(timezone.utc), False, mph(55), mph(50), make_sm(gas_pressed=False))
    controller.update_override(mph(55), 0.0, mph(50), 0.0, make_sm(gas_pressed=False))
    assert controller.target == pytest.approx(mph(55))
    assert controller.overridden_speed == 0
    assert not controller.override_slc
  finally:
    controller.shutdown()


def test_pedal_and_set_speed_overrides_are_independent():
  controller = make_controller()
  try:
    controller.source = "Dashboard"
    controller.target = mph(45)
    controller.last_valid_limit = mph(45)

    # A pedal pass is temporary; a set-speed increase is the fixed persistent action.
    controller.update_override(mph(45), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    controller.update_override(mph(45), 0.0, mph(55), 0.0, make_sm(gas_pressed=True))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(55))

    controller.update_override(mph(45), 0.0, mph(55), 0.0, make_sm(gas_pressed=False))
    assert not controller.override_slc
    assert controller.overridden_speed == 0

    # A fresh + above the effective SLC target arms the override.
    controller.update_override(mph(55), 0.0, mph(55), 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(55))

    # Pedaling temporarily takes priority, then returns to the selected set speed.
    controller.update_override(mph(55), 0.0, mph(60), 0.0, make_sm(gas_pressed=True))
    assert controller.overridden_speed == pytest.approx(mph(60))

    controller.update_override(mph(55), 0.0, mph(60), 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(55))

    controller.update_override(mph(60), 0.0, mph(58), 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(60))

    controller.update_override(mph(50), 0.0, mph(50), 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(50))

    # Returning to the effective SLC target ends the persistent override.
    controller.update_override(mph(45), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    assert not controller.override_slc
    assert controller.overridden_speed == 0
  finally:
    controller.shutdown()


def test_persistent_override_waits_until_above_slc_target_with_offset():
  controller = make_controller(
    is_metric=True,
    speed_limit_offset2=3 * CV.KPH_TO_MS,
  )
  try:
    controller.source = "Dashboard"
    controller.target = 30 * CV.KPH_TO_MS
    controller.last_valid_limit = controller.target

    controller.update_override(30 * CV.KPH_TO_MS, 0.0, 30 * CV.KPH_TO_MS, 0.0, make_sm(gas_pressed=False))
    controller.update_override(33 * CV.KPH_TO_MS, 0.0, 30 * CV.KPH_TO_MS, 0.0, make_sm(gas_pressed=False))
    assert not controller.override_slc

    controller.update_override(35 * CV.KPH_TO_MS, 0.0, 30 * CV.KPH_TO_MS, 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(35 * CV.KPH_TO_MS)

    controller.update_override(33 * CV.KPH_TO_MS, 0.0, 30 * CV.KPH_TO_MS, 0.0, make_sm(gas_pressed=False))
    assert not controller.override_slc
    assert controller.overridden_speed == 0
  finally:
    controller.shutdown()


def test_set_speed_override_clears_on_new_speed_zone():
  # Entering a new (lower) posted limit clears the override; a steady high set speed must not
  # re-arm it. Only a fresh +/- press re-arms.
  controller = make_controller()
  try:
    controller.source = "Dashboard"
    controller.target = mph(45)
    controller.previous_source = "Dashboard"
    controller.previous_target = mph(45)
    controller.last_valid_limit = mph(45)

    controller.update_override(mph(45), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    controller.update_override(mph(60), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc

    # A 1 mph lower zone takes the same-limit fast path but still clears the override.
    controller.update_limits(mph(44), datetime.now(timezone.utc), False, mph(60), mph(58), make_sm(gas_pressed=False))
    controller.update_override(mph(60), 0.0, mph(58), 0.0, make_sm(gas_pressed=False))
    assert controller.target == pytest.approx(mph(44))
    # Set speed unchanged at 60 -> no rising edge -> override stays cleared (car slows to 44).
    assert not controller.override_slc
    assert controller.overridden_speed == 0

    # A fresh + press (60 -> 65) re-arms against the new limit.
    controller.update_override(mph(65), 0.0, mph(44), 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(65))
  finally:
    controller.shutdown()


def test_confirmation_accel_press_does_not_arm_set_speed_override():
  controller = make_controller(
    speed_limit_confirmation_higher=True,
  )
  try:
    controller.source = "Dashboard"
    controller.target = mph(45)
    controller.previous_source = "Dashboard"
    controller.previous_target = mph(45)
    controller.last_valid_limit = mph(45)

    controller.update_override(mph(45), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    controller.update_limits(mph(50), datetime.now(timezone.utc), False, mph(45), mph(45), make_sm(gas_pressed=False))
    assert controller.source == "None"
    assert controller.unconfirmed_speed_limit == pytest.approx(mph(50))

    # The button arrives before the corresponding cruise-speed update. This + accepts the
    # pending 50 mph limit, but its delayed 55 mph set-speed update must not arm an override.
    confirm_sm = make_sm(gas_pressed=False, accel_pressed=True, v_cruise_kph=45 * CV.MPH_TO_KPH)
    controller.update_limits(mph(50), datetime.now(timezone.utc), False, mph(45), mph(45), confirm_sm)
    controller.update_override(mph(45), 0.0, mph(45), 0.0, confirm_sm)
    assert controller.source == "Dashboard"
    assert controller.target == pytest.approx(mph(50))
    assert not controller.override_slc
    assert controller.overridden_speed == 0

    delayed_speed_sm = make_sm(gas_pressed=False, v_cruise_kph=55 * CV.MPH_TO_KPH)
    controller.update_limits(mph(50), datetime.now(timezone.utc), False, mph(55), mph(45), delayed_speed_sm)
    controller.update_override(mph(55), 0.0, mph(45), 0.0, delayed_speed_sm)
    assert not controller.override_slc
    assert controller.overridden_speed == 0

    # A second fresh + is allowed to establish the override.
    second_press_sm = make_sm(gas_pressed=False, accel_pressed=True, v_cruise_kph=60 * CV.MPH_TO_KPH)
    controller.update_limits(mph(50), datetime.now(timezone.utc), False, mph(60), mph(45), second_press_sm)
    controller.update_override(mph(60), 0.0, mph(45), 0.0, second_press_sm)
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(60))
  finally:
    controller.shutdown()


def test_adopt_speed_limit_clears_complete_override_state():
  controller = make_controller()
  try:
    controller.source = "Dashboard"
    controller.target = mph(45)
    controller.previous_source = "Dashboard"
    controller.previous_target = mph(45)
    controller.last_valid_limit = mph(45)
    controller.override_slc = True
    controller.overridden_speed = mph(55)
    controller._slc_adopt_counter = 3
    controller.starpilot_planner.params_memory.values["SLCAdoptSpeedLimit"] = True

    controller.update_limits(mph(45), datetime.now(timezone.utc), False, mph(55), mph(50), make_sm(gas_pressed=False))

    assert controller.overridden_speed == 0
    assert not controller.override_slc
  finally:
    controller.shutdown()


def test_redneck_set_speed_override_is_bidirectional():
  controller = make_controller(
    redneck_cruise=True,
  )
  try:
    controller.source = "Dashboard"
    controller.target = mph(45)
    controller.last_valid_limit = mph(45)

    controller.update_override(mph(45), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    controller.update_override(mph(60), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(60))

    # A manual decrease below the posted limit must become the new redneck target.
    controller.update_override(mph(35), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(35))
  finally:
    controller.shutdown()


def test_manual_override_tracks_current_speed_and_ends_on_release():
  controller = make_controller()
  try:
    controller.source = "Dashboard"
    controller.target = mph(45)
    controller.last_valid_limit = mph(45)

    controller.update_override(mph(60), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    assert not controller.override_slc
    assert controller.overridden_speed == 0

    controller.update_override(mph(60), 0.0, mph(55), 0.0, make_sm(gas_pressed=True))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(55))

    # The temporary override follows the current speed rather than a historical peak.
    controller.update_override(mph(60), 0.0, mph(50), 0.0, make_sm(gas_pressed=True))
    assert controller.overridden_speed == pytest.approx(mph(50))

    controller.update_override(mph(60), 0.0, mph(50), 0.0, make_sm(gas_pressed=False))
    assert not controller.override_slc
    assert controller.overridden_speed == 0
  finally:
    controller.shutdown()


def test_manual_override_survives_brief_enabled_flicker():
  controller = make_controller()
  try:
    controller.source = "Dashboard"
    controller.target = mph(45)
    controller.previous_source = "Dashboard"
    controller.previous_target = mph(45)
    controller.last_valid_limit = mph(45)
    controller.update_override(mph(60), 0.0, mph(55), 0.0, make_sm(gas_pressed=True))

    disabled_sm = make_sm(gas_pressed=True, enabled=False)
    for _ in range(int(0.5 / DT_MDL)):
      controller.update_override(mph(60), 0.0, mph(55), 0.0, disabled_sm)

    assert controller.overridden_speed == pytest.approx(mph(55))
    assert controller.override_slc

    controller.update_override(mph(60), 0.0, mph(55), 0.0, make_sm(gas_pressed=True, enabled=True))

    assert controller.overridden_speed == pytest.approx(mph(55))
    assert controller.override_slc
  finally:
    controller.shutdown()


def test_override_clears_after_sustained_disengage():
  controller = make_controller()
  try:
    controller.source = "Dashboard"
    controller.target = mph(45)
    controller.previous_source = "Dashboard"
    controller.previous_target = mph(45)
    controller.last_valid_limit = mph(45)
    controller.overridden_speed = mph(55)
    controller.override_slc = True

    disabled_sm = make_sm(gas_pressed=False, enabled=False)
    for _ in range(int(1.0 / DT_MDL) + 1):
      controller.update_override(mph(75), 0.0, mph(65), 0.0, disabled_sm)

    assert controller.overridden_speed == 0
    assert not controller.override_slc
  finally:
    controller.shutdown()
