import math
import sys
from enum import IntEnum
from types import ModuleType, SimpleNamespace

import pytest

from openpilot.starpilot.common.accel_profile import ACCELERATION_PROFILES, DECELERATION_PROFILES, get_accel_profile_curve_values
from openpilot.starpilot.common.longitudinal_personality_profiles import default_personality_profiles, profile_document


def _module(name, **attributes):
  module = ModuleType(name)
  for key, value in attributes.items():
    setattr(module, key, value)
  return module


class _Params:
  def __init__(self, *args, **kwargs):
    self.writes = []

  def put_nonblocking(self, key, value):
    self.writes.append((key, value))

  def put_bool(self, key, value):
    self.writes.append((key, value))


sys.modules["openpilot.common.constants"] = _module(
  "openpilot.common.constants", CV=SimpleNamespace(KPH_TO_MS=1 / 3.6, MPH_TO_MS=0.44704),
)
sys.modules["openpilot.common.params"] = _module("openpilot.common.params", Params=_Params)
sys.modules["openpilot.selfdrive.car.cruise"] = _module(
  "openpilot.selfdrive.car.cruise", V_CRUISE_MAX=145, V_CRUISE_UNSET=255,
)
sys.modules["openpilot.selfdrive.controls.lib.longitudinal_planner"] = _module(
  "openpilot.selfdrive.controls.lib.longitudinal_planner", A_CRUISE_MIN=-1.0, get_max_accel=lambda _v_ego: 2.0,
)
sys.modules["openpilot.starpilot.controls.lib.starpilot_vcruise"] = _module(
  "openpilot.starpilot.controls.lib.starpilot_vcruise",
  get_active_slc_control_target=lambda enabled, set_speed_limit, target, offset, overridden_speed, *_args, **_kwargs: (
    float(overridden_speed or target) + float(offset) if enabled and set_speed_limit else 0.0
  ),
)

from openpilot.starpilot.controls.lib.starpilot_acceleration import StarPilotAcceleration


class Personality(IntEnum):
  aggressive = 0
  standard = 1
  relaxed = 2


def _sm(*, traffic=False, personality=Personality.standard, lead=False, force_decel=False):
  lead_state = SimpleNamespace(status=lead, vLead=0.0, aLeadK=-1.0 if lead else 0.0, dRel=10.0 if lead else 1000.0)
  return {
    "carControl": SimpleNamespace(orientationNED=[0.0, 0.0, 0.0]),
    "carState": SimpleNamespace(vCruise=80.0, vEgoCluster=0.0, standstill=False),
    "controlsState": SimpleNamespace(forceDecel=force_decel),
    "radarState": SimpleNamespace(leadOne=lead_state, leadTwo=SimpleNamespace(status=False, vLead=0.0, aLeadK=0.0, dRel=1000.0)),
    "selfdriveState": SimpleNamespace(personality=personality),
    "starpilotCarState": SimpleNamespace(
      ecoGear=False, forceCoast=False, pulseAndGlide=False, sportGear=False, trafficModeEnabled=traffic,
    ),
  }


def _planner(v_cruise=20.0):
  return SimpleNamespace(
    starpilot_cem=SimpleNamespace(stop_light_detected=False),
    starpilot_following=SimpleNamespace(disable_throttle=False),
    starpilot_vcruise=SimpleNamespace(slc_target=0.0, slc_offset=0.0, slc=SimpleNamespace(overridden_speed=0.0), forcing_stop=False),
    starpilot_weather=SimpleNamespace(weather_id=0, reduce_acceleration=0.0),
    v_cruise=v_cruise,
  )


def _toggles(document):
  return SimpleNamespace(
    acceleration_profile=ACCELERATION_PROFILES["STANDARD"],
    custom_accel_profile=False,
    custom_accel_profile_breakpoints=[0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 40.0],
    custom_accel_profile_values=[],
    custom_personalities=True,
    deceleration_profile=DECELERATION_PROFILES["STANDARD"],
    ev_tuning=False,
    longitudinal_personality_profiles=document,
    map_acceleration=False,
    map_deceleration=False,
    personality_ev_tuning=False,
    personality_truck_tuning=False,
    pulse_glide_speed_delta=0.0,
    redneck_cruise=False,
    set_speed_limit=False,
    set_speed_offset=0.0,
    speed_limit_controller=False,
    speed_limit_controller_override_set_speed=False,
    truck_tuning=False,
  )


def _document(*, enabled=True):
  return profile_document(default_personality_profiles(False), enabled=enabled)


@pytest.mark.parametrize(
  ("profile", "personality", "traffic_mode", "acceleration", "braking"),
  [
    ("aggressive", Personality.aggressive, False, 1.10, 0.60),
    ("standard", Personality.standard, False, 1.25, 0.75),
    ("relaxed", Personality.relaxed, False, 1.40, 0.90),
    ("traffic", Personality.aggressive, True, 1.55, 1.05),
  ],
)
def test_real_enum_shaped_personality_selects_each_explicit_profile_override(
  profile, personality, traffic_mode, acceleration, braking,
):
  document = _document()
  document["profiles"][profile]["acceleration"] = {"preset": "custom", "curve": [acceleration] * 10}
  document["profiles"][profile]["braking"] = {"preset": "custom", "curve": [braking] * 10}
  controller = StarPilotAcceleration(_planner(v_cruise=5.0))

  controller.update(10.0, _sm(traffic=traffic_mode, personality=personality), _toggles(document))

  assert controller.max_accel == pytest.approx(acceleration)
  assert controller.min_accel == pytest.approx(-braking)


def test_master_toggle_disables_profile_document_overrides():
  document = _document()
  document["profiles"]["standard"]["acceleration"] = {"preset": "custom", "curve": [1.25] * 10}
  toggles = _toggles(document)
  toggles.custom_personalities = False

  controller = StarPilotAcceleration(_planner())
  controller.update(0.0, _sm(personality=Personality.standard), toggles)

  assert controller.max_accel == pytest.approx(2.0)


@pytest.mark.parametrize(
  ("profile", "personality", "traffic_mode", "legacy_max_accel", "legacy_min_accel"),
  [
    ("traffic", Personality.aggressive, True, 1.1, -0.35),
    ("aggressive", Personality.aggressive, False, 2.0, -1.0),
    ("standard", Personality.standard, False, 2.0, -1.0),
    ("relaxed", Personality.relaxed, False, 2.0, -1.0),
  ],
)
def test_disabled_active_profile_keeps_legacy_acceleration_path(
  profile, personality, traffic_mode, legacy_max_accel, legacy_min_accel,
):
  document = _document()
  document["profiles"][profile]["acceleration"] = {"preset": "custom", "curve": [1.25] * 10}
  document["profiles"][profile]["braking"] = {"preset": "custom", "curve": [0.75] * 10}
  toggles = _toggles(document)
  setattr(toggles, f"{profile}_personality_profile", False)
  controller = StarPilotAcceleration(_planner())

  controller.update(0.0, _sm(traffic=traffic_mode, personality=personality), toggles)

  assert controller.max_accel == pytest.approx(legacy_max_accel)
  assert controller.min_accel == pytest.approx(legacy_min_accel)


def test_detected_truck_curve_is_used_without_enabling_legacy_truck_tuning():
  document = _document()
  document["profiles"]["standard"]["acceleration"] = {"preset": "sport_plus", "curve": []}
  toggles = _toggles(document)
  toggles.personality_truck_tuning = True

  controller = StarPilotAcceleration(_planner())
  controller.update(0.0, _sm(personality=Personality.standard), toggles)

  expected = get_accel_profile_curve_values(ACCELERATION_PROFILES["SPORT_PLUS"], False, True)[0]
  assert controller.max_accel == pytest.approx(expected)


def test_fresh_profile_defaults_select_standard_acceleration_and_braking():
  document = _document()
  toggles = _toggles(document)
  toggles.custom_accel_profile = True
  toggles.custom_accel_profile_values = [3.0] * 7
  controller = StarPilotAcceleration(_planner())

  controller.update(0.0, _sm(personality=Personality.aggressive), toggles)
  assert controller.max_accel == pytest.approx(2.0)
  assert controller.min_accel == pytest.approx(-1.0)

  controller.update(0.0, _sm(traffic=True), toggles)
  assert controller.max_accel == pytest.approx(2.0)
  assert controller.min_accel == pytest.approx(-0.35)


def test_absent_disabled_malformed_partial_wrong_version_and_nonfinite_use_legacy_path():
  candidates = [None, {}, _document(enabled=False), _document(), _document(), _document()]
  candidates[3]["schemaVersion"] = 99
  del candidates[4]["profiles"]["standard"]["braking"]
  candidates[5]["profiles"]["standard"]["acceleration"] = {"preset": "custom", "curve": [math.nan] * 10}

  for candidate in candidates:
    toggles = _toggles(candidate)
    toggles.custom_accel_profile = True
    toggles.custom_accel_profile_values = [3.0] * 7
    controller = StarPilotAcceleration(_planner())
    controller.update(0.0, _sm(), toggles)
    assert controller.max_accel == pytest.approx(3.0)
    assert controller.min_accel == pytest.approx(-1.0)


def test_map_gear_force_coast_and_weather_precedence_remains_explicit():
  document = _document()
  document["profiles"]["standard"]["acceleration"] = {"preset": "custom", "curve": [3.5] * 10}
  document["profiles"]["standard"]["braking"] = {"preset": "custom", "curve": [2.0] * 10}
  toggles = _toggles(document)
  toggles.map_acceleration = True
  toggles.map_deceleration = True
  sm = _sm()
  sm["starpilotCarState"].ecoGear = True
  planner = _planner()
  planner.starpilot_weather.weather_id = 1
  planner.starpilot_weather.reduce_acceleration = 0.25
  controller = StarPilotAcceleration(planner)

  controller.update(0.0, sm, toggles)
  assert controller.max_accel == pytest.approx(1.5 * 0.75)
  assert controller.min_accel == pytest.approx(-0.5)
  assert all(key != "LongitudinalPersonalityProfiles" for key, _value in controller.params.writes)

  sm["starpilotCarState"].forceCoast = True
  controller.update(0.0, sm, toggles)
  assert controller.min_accel == pytest.approx(-0.5)


def test_custom_acceleration_and_braking_use_the_selected_twenty_mph_point():
  document = _document()
  document["profiles"]["standard"]["acceleration"] = {
    "preset": "custom", "curve": [1.0 + 0.1 * index for index in range(10)],
  }
  document["profiles"]["standard"]["braking"] = {
    "preset": "custom", "curve": [0.75 + 0.1 * index for index in range(10)],
  }
  controller = StarPilotAcceleration(_planner(v_cruise=5.0))

  controller.update(20.0 * 0.44704, _sm(), _toggles(document))

  assert controller.max_accel == pytest.approx(1.2)
  assert controller.min_accel == pytest.approx(-0.95)


def test_custom_braking_only_shapes_explicit_cruise_deceleration_and_never_reduces_hazard_authority():
  document = _document()
  document["profiles"]["standard"]["braking"] = {"preset": "custom", "curve": [0.5] * 10}
  toggles = _toggles(document)
  controller = StarPilotAcceleration(_planner(v_cruise=30.0))

  controller.update(10.0, _sm(lead=False), toggles)
  assert controller.min_accel <= -1.0

  controller = StarPilotAcceleration(_planner(v_cruise=5.0))
  controller.update(10.0, _sm(lead=False), toggles)
  assert controller.min_accel == pytest.approx(-0.5)

  controller.update(10.0, _sm(lead=True), toggles)
  assert controller.min_accel <= -1.0

  controller.update(10.0, _sm(force_decel=True), toggles)
  assert controller.min_accel <= -1.0
