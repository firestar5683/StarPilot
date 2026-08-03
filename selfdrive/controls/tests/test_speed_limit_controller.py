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
    "speed_limit_controller_override_manual": True,
    "speed_limit_controller_override_set_speed": False,
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
  }
  defaults.update(overrides)
  return SimpleNamespace(**defaults)


def make_sm(*, gas_pressed, enabled=True, accel_pressed=False, decel_pressed=False, long_active=True, v_cruise_kph=255.0):
  return {
    "carControl": SimpleNamespace(longActive=long_active),
    "carState": SimpleNamespace(gasPressed=gas_pressed, steeringAngleDeg=0.0, vCruise=v_cruise_kph),
    "liveParameters": SimpleNamespace(angleOffsetDeg=0.0),
    "mapdOut": SimpleNamespace(nextSpeedLimitDistance=0.0, nextSpeedLimit=0.0, speedLimit=0.0, waySelectionType=0),
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


def test_new_source_limit_clears_override_until_gas_release():
  controller = make_controller()
  try:
    controller.source = "Dashboard"
    controller.target = mph(55)
    controller.previous_source = "Dashboard"
    controller.previous_target = mph(55)
    controller.overridden_speed = mph(65)

    sm = make_sm(gas_pressed=True)
    controller.update_limits(mph(45), datetime.now(timezone.utc), False, mph(75), mph(65), sm)
    controller.update_override(mph(75), 0.0, mph(65), 0.0, sm)

    assert controller.target == pytest.approx(mph(45))
    assert controller.source == "Dashboard"
    assert controller.overridden_speed == 0
    assert not controller.override_slc

    controller.update_limits(mph(45), datetime.now(timezone.utc), False, mph(75), mph(65), sm)
    controller.update_override(mph(75), 0.0, mph(65), 0.0, sm)

    assert controller.overridden_speed == 0
    assert not controller.override_slc

    controller.update_override(mph(75), 0.0, mph(65), 0.0, make_sm(gas_pressed=False))
    controller.update_override(mph(75), 0.0, mph(65), 0.0, sm)

    assert controller.overridden_speed == pytest.approx(mph(65))
    assert controller.override_slc

    # --- Dropout / Fallback Test Condition ---
    controller.starpilot_toggles = make_toggles(slc_fallback_set_speed=True)
    # No limit available → falls back to v_cruise (75 mph) with source "None".
    # Override persists because target_to_use resolves to last_valid_limit (45 mph) which is
    # below overridden_speed (65 mph) — the sticky override_slc chain stays True.
    controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(75), mph(65), sm)
    controller.update_override(mph(75), 0.0, mph(65), 0.0, sm)

    assert controller.target == pytest.approx(mph(75))
    assert controller.source == "None"
    assert controller.overridden_speed == pytest.approx(mph(65))
    assert controller.override_slc

    # Recovery to a confirmed limit (55 mph) clears the override: this is a genuinely new
    # speed zone (55 != last_valid 45), so clear_override_for_source_limit fires correctly.
    controller.update_limits(mph(55), datetime.now(timezone.utc), False, mph(75), mph(65), sm)
    controller.update_override(mph(75), 0.0, mph(65), 0.0, sm)

    assert controller.target == pytest.approx(mph(55))
    assert controller.source == "Dashboard"
    assert controller.overridden_speed == 0
    assert not controller.override_slc

      # --- Override Clipping Check (set-speed fallback) ---
      # Separate controller: active override, then fallback to v_cruise that is BELOW the override.
      # overridden_speed clips to v_cruise (override_slc stays True via sticky chain, but
      # np.clip clamps overridden_speed to the new target+offset).
    clip_controller = make_controller(slc_fallback_set_speed=True)
    try:
      clip_controller.source = "Dashboard"
      clip_controller.target = mph(55)
      clip_controller.previous_source = "Dashboard"
      clip_controller.previous_target = mph(55)
      clip_controller.last_valid_limit = mph(55)
      clip_controller.override_slc = True
      clip_controller.overridden_speed = mph(65)

      sm_no_gas = make_sm(gas_pressed=False)
      # v_cruise = 30 mph (below last_valid 55), so target_to_use returns mph(30).
      # override_slc sticky: overridden_speed=65 > 30+0=30 > 0 — still True from chain.
      # np.clip(65, 30, 30) = 30, so overridden_speed clips to mph(30).
      clip_controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(30), mph(30), sm_no_gas)
      clip_controller.update_override(mph(30), 0.0, mph(30), 0.0, sm_no_gas)

      assert clip_controller.target == pytest.approx(mph(30))
      # Clipped to v_cruise — not locked at mph(55) or mph(65)
      assert clip_controller.overridden_speed == pytest.approx(mph(30))
      assert clip_controller.override_slc
    finally:
      clip_controller.shutdown()

    # --- Lost Speed Limit (no fallback) clears target to 0 ---
    # When all limit sources drop to 0 with no fallback, target becomes 0
    # and override_slc is False (target_to_use=0, chain evaluates False).
    lost_controller = make_controller(slc_fallback_set_speed=False, slc_fallback_previous_speed_limit=False)
    try:
      lost_controller.source = "Dashboard"
      lost_controller.target = mph(45)
      lost_controller.previous_source = "Dashboard"
      lost_controller.previous_target = mph(45)

      sm_on = make_sm(gas_pressed=False)
      lost_controller.update_limits(0.0, datetime.now(timezone.utc), False, mph(75), mph(65), sm_on)
      lost_controller.update_override(mph(75), 0.0, mph(65), 0.0, sm_on)

      assert lost_controller.target == 0
      assert lost_controller.overridden_speed == 0
      assert not lost_controller.override_slc
    finally:
      lost_controller.shutdown()
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


def test_higher_limit_does_not_clear_override():
  controller = make_controller()
  try:
    controller.source = "Dashboard"
    controller.target = mph(35)
    controller.previous_source = "Dashboard"
    controller.previous_target = mph(35)
    controller.overridden_speed = mph(55)
    controller.override_slc = True

    sm = make_sm(gas_pressed=True)
    controller.update_limits(mph(45), datetime.now(timezone.utc), False, mph(75), mph(55), sm)
    controller.update_override(mph(75), 0.0, mph(55), 0.0, sm)

    assert controller.target == pytest.approx(mph(45))
    assert controller.source == "Dashboard"
    assert controller.overridden_speed == pytest.approx(mph(55))
    assert controller.override_slc

    controller_overridden_below = make_controller()
    try:
      controller_overridden_below.source = "Dashboard"
      controller_overridden_below.target = mph(35)
      controller_overridden_below.previous_source = "Dashboard"
      controller_overridden_below.previous_target = mph(35)
      controller_overridden_below.overridden_speed = mph(40)
      controller_overridden_below.override_slc = True

      sm = make_sm(gas_pressed=True)
      controller_overridden_below.update_limits(mph(45), datetime.now(timezone.utc), False, mph(75), mph(55), sm)
      controller_overridden_below.update_override(mph(75), 0.0, mph(55), 0.0, sm)

      assert controller_overridden_below.target == pytest.approx(mph(45))
      assert controller_overridden_below.overridden_speed == 0
      assert not controller_overridden_below.override_slc
    finally:
      controller_overridden_below.shutdown()
  finally:
    controller.shutdown()


def test_set_speed_mode_overrides_on_raise_without_gas():
  # Max Set Speed mode: raising the set speed (+/-) above the posted limit must override
  # the SLC hold with no gas pedal, targeting the set speed.
  controller = make_controller(
    speed_limit_controller_override_manual=False,
    speed_limit_controller_override_set_speed=True,
  )
  try:
    controller.source = "Dashboard"
    controller.target = mph(45)
    controller.last_valid_limit = mph(45)

    # Baseline frame at the limit establishes the previous set speed (no rising edge yet).
    controller.update_override(mph(45), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    assert not controller.override_slc

    # Driver presses + to 60 (rising edge): override arms and targets the set speed.
    controller.update_override(mph(60), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(60))

    # Holding 60 with no further press: override stays latched.
    controller.update_override(mph(60), 0.0, mph(58), 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(60))
  finally:
    controller.shutdown()


def test_set_speed_override_clears_on_new_speed_zone():
  # Entering a new (lower) posted limit clears the override; a steady high set speed must not
  # re-arm it. Only a fresh +/- press re-arms.
  controller = make_controller(
    speed_limit_controller_override_manual=False,
    speed_limit_controller_override_set_speed=True,
  )
  try:
    controller.source = "Dashboard"
    controller.target = mph(45)
    controller.previous_source = "Dashboard"
    controller.previous_target = mph(45)
    controller.last_valid_limit = mph(45)

    controller.update_override(mph(45), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    controller.update_override(mph(60), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc

    # New lower zone (35): update_limits clears the override for the new segment.
    controller.update_limits(mph(35), datetime.now(timezone.utc), False, mph(60), mph(58), make_sm(gas_pressed=False))
    controller.update_override(mph(60), 0.0, mph(58), 0.0, make_sm(gas_pressed=False))
    assert controller.target == pytest.approx(mph(35))
    # Set speed unchanged at 60 -> no rising edge -> override stays cleared (car slows to 35).
    assert not controller.override_slc
    assert controller.overridden_speed == 0

    # A fresh + press (60 -> 65) re-arms against the new limit.
    controller.update_override(mph(65), 0.0, mph(35), 0.0, make_sm(gas_pressed=False))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(65))
  finally:
    controller.shutdown()


def test_gas_pedal_mode_ignores_set_speed_without_gas():
  # Set With Gas Pedal mode: a high set speed alone must NOT override; gas is still required.
  controller = make_controller(
    speed_limit_controller_override_manual=True,
    speed_limit_controller_override_set_speed=False,
  )
  try:
    controller.source = "Dashboard"
    controller.target = mph(45)
    controller.last_valid_limit = mph(45)

    controller.update_override(mph(60), 0.0, mph(45), 0.0, make_sm(gas_pressed=False))
    assert not controller.override_slc
    assert controller.overridden_speed == 0

    controller.update_override(mph(60), 0.0, mph(50), 0.0, make_sm(gas_pressed=True))
    assert controller.override_slc
    assert controller.overridden_speed == pytest.approx(mph(50))
  finally:
    controller.shutdown()


def test_manual_override_survives_brief_enabled_flicker():
  controller = make_controller()
  try:
    controller.source = "Dashboard"
    controller.target = mph(45)
    controller.previous_source = "Dashboard"
    controller.previous_target = mph(45)
    controller.overridden_speed = mph(55)
    controller.override_slc = True

    disabled_sm = make_sm(gas_pressed=False, enabled=False)
    for _ in range(int(0.5 / DT_MDL)):
      controller.update_override(mph(75), 0.0, mph(65), 0.0, disabled_sm)

    assert controller.overridden_speed == pytest.approx(mph(55))
    assert controller.override_slc

    controller.update_override(mph(75), 0.0, mph(65), 0.0, make_sm(gas_pressed=False, enabled=True))

    assert controller.overridden_speed == pytest.approx(mph(55))
    assert controller.override_slc
  finally:
    controller.shutdown()


def test_manual_override_clears_after_sustained_disengage():
  controller = make_controller()
  try:
    controller.source = "Dashboard"
    controller.target = mph(45)
    controller.previous_source = "Dashboard"
    controller.previous_target = mph(45)
    controller.overridden_speed = mph(55)
    controller.override_slc = True
    controller.override_requires_gas_release = True

    disabled_sm = make_sm(gas_pressed=False, enabled=False)
    for _ in range(int(1.0 / DT_MDL) + 1):
      controller.update_override(mph(75), 0.0, mph(65), 0.0, disabled_sm)

    assert controller.overridden_speed == 0
    assert not controller.override_slc
    assert not controller.override_requires_gas_release
  finally:
    controller.shutdown()
