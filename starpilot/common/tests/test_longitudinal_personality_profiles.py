import json
import math
from pathlib import Path

import numpy as np
import pytest

import openpilot.starpilot.common.longitudinal_personality_profiles as lpp

from openpilot.starpilot.common.accel_profile import (
  ACCELERATION_PROFILES,
  get_accel_profile_curve_values,
  interpolate_accel_profile,
)
from openpilot.starpilot.common.longitudinal_personality_profiles import (
  ACCELERATION_SPEEDS_MPH,
  BRAKING_SPEEDS_MPH,
  CURVE_BOUNDS,
  FOLLOWING_PRESET_CURVES,
  FOLLOWING_SPEEDS_MPH,
  PERSONALITY_IDS,
  PROFILE_SCHEMA_VERSION,
  active_personality_id,
  category_curve,
  default_personality_profiles,
  initial_custom_curve,
  is_truck_fingerprint,
  interpolate_category_curve,
  load_personality_profiles,
  profile_document,
  resolve_personality_profile,
  serialize_personality_profiles,
  strict_personality_profiles,
  update_personality_profile,
)


def test_document_is_versioned_disabled_and_declares_exact_axes_and_units():
  document = profile_document(default_personality_profiles(False), enabled=False)

  assert document["schemaVersion"] == PROFILE_SCHEMA_VERSION == 2
  assert document["enabled"] is False
  assert document["axes"] == {
    "acceleration": {
      "speed": {"unit": "mph", "values": list(ACCELERATION_SPEEDS_MPH)},
      "value": {"unit": "m/s^2", "meaning": "maximum_requested_acceleration"},
    },
    "braking": {
      "speed": {"unit": "mph", "values": list(BRAKING_SPEEDS_MPH)},
      "value": {"unit": "m/s^2", "meaning": "cruise_slc_deceleration_magnitude"},
    },
    "following": {
      "speed": {"unit": "mph", "values": list(FOLLOWING_SPEEDS_MPH)},
      "value": {"unit": "s", "meaning": "base_time_headway"},
    },
  }
  assert set(document["profiles"]) == set(PERSONALITY_IDS)
  for profile in document["profiles"].values():
    assert set(profile) == {"acceleration", "braking", "following"}


@pytest.mark.parametrize("fingerprint", [
  "RAM 1500 5TH GEN",
  "RAM HD 5TH GEN",
  "FORD F-150 14TH GEN",
  "FORD MAVERICK 1ST GEN",
  "FORD RANGER 2ND GEN",
  "CHEVROLET SILVERADO 1500 2020",
  "HONDA RIDGELINE 2017",
  "HYUNDAI SANTA CRUZ 2025",
])
def test_supported_truck_fingerprints_select_the_truck_curve(fingerprint):
  assert is_truck_fingerprint(fingerprint) is True


@pytest.mark.parametrize("fingerprint", [None, "", "HONDA CIVIC 2022", "FORD EXPLORER 6TH GEN"])
def test_non_truck_fingerprints_do_not_select_the_truck_curve(fingerprint):
  assert is_truck_fingerprint(fingerprint) is False


def test_enabling_without_a_stored_document_creates_standard_medium_defaults():
  document = lpp.synchronise_profile_document_enabled(None, True, ev_tuning=False, truck_tuning=False)
  assert document == profile_document(default_personality_profiles(False), enabled=True)


def test_enabling_does_not_overwrite_a_malformed_stored_document():
  assert lpp.synchronise_profile_document_enabled({"schemaVersion": 99}, True, False, False) is None


def test_disabling_without_a_stored_document_does_not_create_one():
  assert lpp.synchronise_profile_document_enabled(None, False, ev_tuning=False, truck_tuning=False) is None


def test_every_state_affecting_personality_param_is_parked_only():
  assert lpp.PERSONALITY_PARKED_PARAM_KEYS == (
    lpp.PERSONALITY_ADVANCED_PARAM_KEYS
    | lpp.PERSONALITY_FOLLOW_PARAM_KEYS
    | lpp.PERSONALITY_PROFILE_ENABLE_PARAM_KEYS
    | {"CustomPersonalities"}
  )
  assert len(lpp.PERSONALITY_PARKED_PARAM_KEYS) == 32


def test_legacy_follow_values_reject_coercion_and_out_of_range_inputs():
  for invalid in (True, "1.25", math.nan, math.inf, 0.49, 3.01):
    with pytest.raises(ValueError):
      lpp.validate_personality_follow_value(invalid)
  assert lpp.validate_personality_follow_value(0.5) == 0.5
  assert lpp.validate_personality_follow_value(1.25) == 1.25
  assert lpp.validate_personality_follow_value(3) == 3.0


def test_advanced_personality_values_reject_coercion_and_out_of_range_inputs():
  for invalid in (True, "50", math.nan, math.inf, 24.9, 200.1):
    with pytest.raises(ValueError):
      lpp.validate_personality_advanced_value(invalid)
  assert lpp.validate_personality_advanced_value(50) == 50.0
  assert lpp.validate_personality_advanced_value(100.0) == 100.0
  assert lpp.validate_personality_advanced_value(72.34567) == 72.3457


def test_runtime_loader_uses_detected_truck_curve_without_changing_legacy_truck_flag():
  source = (Path(__file__).parents[1] / "starpilot_variables.py").read_text(encoding="utf-8")
  assert "toggle.longitudinal_personality_profiles = migrate_profile_document(profile_settings_raw) or {}" in source
  assert "is_truck_fingerprint(CP.carFingerprint) or truck_tuning_param" in source
  assert ") and not toggle.personality_ev_tuning" in source
  assert "toggle.truck_tuning = truck_tuning_param" in source


def test_runtime_loader_maps_each_personality_enable_param_to_the_exact_runtime_boolean():
  loader = getattr(lpp, "load_personality_profile_enable_values", None)
  assert callable(loader)
  persisted = {
    "TrafficPersonalityProfile": True,
    "AggressivePersonalityProfile": False,
    "StandardPersonalityProfile": True,
    "RelaxedPersonalityProfile": False,
  }
  requested = []

  def get_value(key):
    requested.append(key)
    return persisted[key]

  assert loader(get_value) == {
    "traffic_personality_profile": True,
    "aggressive_personality_profile": False,
    "standard_personality_profile": True,
    "relaxed_personality_profile": False,
  }
  assert requested == list(persisted)


def test_acceleration_presets_select_truck_automatically_and_ev_wins_if_both_are_true():
  config = {"preset": "sport", "curve": []}
  assert category_curve("acceleration", config, False, True) == get_accel_profile_curve_values(2, False, True)
  assert category_curve("acceleration", config, True, True) == get_accel_profile_curve_values(2, True, False)


def test_declared_custom_axes_use_exact_ten_mph_breakpoints():
  assert ACCELERATION_SPEEDS_MPH == tuple(range(0, 91, 10))
  assert BRAKING_SPEEDS_MPH == ACCELERATION_SPEEDS_MPH


def test_boolean_axis_values_are_not_accepted_as_numeric_breakpoints():
  invalid = profile_document(default_personality_profiles(False), enabled=True)
  invalid["axes"]["acceleration"]["speed"]["values"][0] = False
  assert lpp.strict_profile_document(invalid) is None


def test_strict_document_rejects_unversioned_partial_extra_or_axis_changes():
  valid = profile_document(default_personality_profiles(False), enabled=True)
  assert strict_personality_profiles(valid) == valid["profiles"]
  assert strict_personality_profiles(json.dumps(valid)) == valid["profiles"]

  invalid_documents = [
    valid["profiles"],
    {**valid, "schemaVersion": 99},
    {**valid, "enabled": 1},
    {**valid, "extra": True},
    {key: value for key, value in valid.items() if key != "axes"},
  ]
  wrong_axis = json.loads(json.dumps(valid))
  wrong_axis["axes"]["acceleration"]["speed"]["values"][0] = 1
  invalid_documents.append(wrong_axis)
  partial = json.loads(json.dumps(valid))
  del partial["profiles"]["standard"]["braking"]
  invalid_documents.append(partial)

  for invalid in invalid_documents:
    assert strict_personality_profiles(invalid) is None


def test_strict_document_rejects_boolean_non_finite_fractional_and_out_of_range_values():
  for value in (True, False, math.nan, math.inf, -math.inf, "1.0", 6.1):
    invalid = profile_document(default_personality_profiles(False), enabled=True)
    invalid["profiles"]["standard"]["acceleration"] = {"preset": "custom", "curve": [1.0] * 10}
    invalid["profiles"]["standard"]["acceleration"]["curve"][0] = value
    assert strict_personality_profiles(invalid) is None


def test_custom_curve_bounds_preserve_low_acceleration_and_enforce_requested_ceilings():
  valid = profile_document(default_personality_profiles(False), enabled=True)
  valid["profiles"]["standard"]["acceleration"] = {"preset": "custom", "curve": [0.35] + [3.5] * 9}
  valid["profiles"]["standard"]["braking"] = {"preset": "custom", "curve": [2.0] * 10}
  assert strict_personality_profiles(valid) == valid["profiles"]

  # A saved v2 curve can exceed the new-authoring ceiling; new points cannot.
  with pytest.raises(ValueError):
    update_personality_profile(valid["profiles"], "standard", "acceleration", "custom", [3.51] * 10, False)

  invalid_braking = json.loads(json.dumps(valid))
  invalid_braking["profiles"]["standard"]["braking"]["curve"][0] = 2.01
  assert strict_personality_profiles(invalid_braking) is None


@pytest.mark.parametrize("value", [3.51, 4.0, 5.0, 6.0])
@pytest.mark.parametrize("enabled", [False, True])
def test_saved_v2_high_acceleration_keeps_schema_and_runtime_behaviour(value, enabled):
  document = profile_document(default_personality_profiles(False), enabled=enabled)
  curve = [value, 3.5, 2.0, 1.5, 1.0, 0.8, 0.6, 0.4, 0.2, 0.0]
  document["profiles"]["aggressive"]["acceleration"] = {"preset": "custom", "curve": curve}
  raw = json.dumps(document)

  assert lpp.strict_profile_document(raw) == document
  assert lpp.migrate_profile_document(raw) == document
  assert load_personality_profiles(raw, False) == document["profiles"]
  assert json.loads(serialize_personality_profiles(document["profiles"], False, enabled=enabled)) == document
  assert lpp.synchronise_profile_document_enabled(raw, not enabled, False) == {**document, "enabled": not enabled}
  resolved = resolve_personality_profile(raw, False, 0)
  assert resolved == (document["profiles"]["aggressive"] if enabled else None)
  if enabled:
    assert resolved is not None
    for speed_mph in (-1.0, 0.0, 2.5, 5.0, 10.0, 25.0, 90.0, 100.0):
      assert interpolate_category_curve("acceleration", speed_mph * 0.44704, resolved["acceleration"], False) == pytest.approx(
        interpolate_accel_profile(speed_mph * 0.44704, curve, [speed * 0.44704 for speed in ACCELERATION_SPEEDS_MPH])
      )
  assert json.dumps(document) == raw


@pytest.mark.parametrize("value", [3.51, 4.0, 5.0, 6.0])
def test_edit_saved_v2_high_point_preserves_other_points_and_profiles(value):
  profiles = default_personality_profiles(False)
  profiles["aggressive"]["acceleration"] = {"preset": "custom", "curve": [value] * 10}
  raw = json.dumps(profiles)
  curve = [3.0] + [value] * 9
  updated = update_personality_profile(profiles, "aggressive", "acceleration", "custom", curve, False)
  assert updated["aggressive"]["acceleration"] == {"preset": "custom", "curve": curve}
  assert json.dumps(profiles) == raw
  for profile_id in ("traffic", "standard", "relaxed"):
    assert updated[profile_id] == profiles[profile_id]
  with pytest.raises(ValueError):
    update_personality_profile(updated, "aggressive", "acceleration", "custom", [value] * 10, False)


def test_saved_high_points_cannot_be_created_moved_increased_or_rounded_into_permission():
  profiles = default_personality_profiles(False)
  profiles["aggressive"]["acceleration"] = {"preset": "custom", "curve": [4.0] + [1.0] * 9}
  for curve in ([4.1] + [1.0] * 9, [4.00001] + [1.0] * 9, [1.0, 4.0] + [1.0] * 8):
    with pytest.raises(ValueError):
      update_personality_profile(profiles, "aggressive", "acceleration", "custom", curve, False)
  with pytest.raises(ValueError):
    update_personality_profile(profiles, "standard", "acceleration", "custom", [4.0] + [1.0] * 9, False)
  malformed = json.loads(json.dumps(profiles))
  malformed["relaxed"]["following"]["curve"] = [True]
  with pytest.raises(ValueError):
    update_personality_profile(malformed, "aggressive", "acceleration", "custom", [4.0] + [1.0] * 9, False)


def test_disabled_document_never_resolves_an_override():
  disabled = profile_document(default_personality_profiles(False), enabled=False)
  for traffic, personality in ((True, 0), (False, 0), (False, 1), (False, 2)):
    assert resolve_personality_profile(disabled, traffic, personality) is None


def test_context_mapping_is_traffic_first_then_cereal_zero_one_two():
  assert active_personality_id(True, 99) == "traffic"
  assert active_personality_id(False, 0) == "aggressive"
  assert active_personality_id(False, 1) == "standard"
  assert active_personality_id(False, 2) == "relaxed"
  for invalid in (-1, 3, 0.5, True, False, math.nan, math.inf, "1", None):
    assert active_personality_id(False, invalid) is None
  for malformed_traffic in (1, 0, "1", "0", "true", "false", None):
    assert active_personality_id(malformed_traffic, 0) is None


def test_enabled_document_resolves_each_profile_and_revalidates_runtime_boundary():
  document = profile_document(default_personality_profiles(False), enabled=True)
  assert resolve_personality_profile(document, True, 2) == document["profiles"]["traffic"]
  assert resolve_personality_profile(document, False, 0) == document["profiles"]["aggressive"]
  assert resolve_personality_profile(document, False, 1) == document["profiles"]["standard"]
  assert resolve_personality_profile(document, False, 2) == document["profiles"]["relaxed"]

  malformed = json.loads(json.dumps(document))
  malformed["profiles"]["standard"]["acceleration"]["curve"] = [math.nan] * 7
  assert resolve_personality_profile(malformed, False, 1) is None
  assert resolve_personality_profile(document, False, 1.0) is None


def test_acceleration_presets_match_dom_curves_for_gas_ev_and_truck():
  profile_ids = {
    "standard": ACCELERATION_PROFILES["STANDARD"],
    "eco": ACCELERATION_PROFILES["ECO"],
    "sport": ACCELERATION_PROFILES["SPORT"],
    "sport_plus": ACCELERATION_PROFILES["SPORT_PLUS"],
  }
  for ev_tuning, truck_tuning in ((False, False), (True, False), (False, True)):
    for preset, profile_id in profile_ids.items():
      config = {"preset": preset, "curve": []}
      assert category_curve("acceleration", config, ev_tuning, truck_tuning) == get_accel_profile_curve_values(
        profile_id, ev_tuning, truck_tuning
      )


def test_custom_initialisation_seeds_from_selected_acceleration_preset():
  current = {"preset": "sport", "curve": []}
  assert initial_custom_curve("acceleration", current, ev_tuning=False, truck_tuning=False) == \
    lpp._sample_config_on_custom_axis("acceleration", current, False, False)
  truck_curve = lpp._sample_config_on_custom_axis("acceleration", current, False, True)
  assert max(truck_curve) > CURVE_BOUNDS["acceleration"][1]
  assert initial_custom_curve("acceleration", current, ev_tuning=False, truck_tuning=True) == [
    min(max(value, CURVE_BOUNDS["acceleration"][0]), CURVE_BOUNDS["acceleration"][1])
    for value in truck_curve
  ]


def test_custom_initialisation_uses_ev_over_truck_when_both_flags_are_set():
  current = {"preset": "standard", "curve": []}
  assert initial_custom_curve("acceleration", current, ev_tuning=True, truck_tuning=True) == \
    lpp._sample_config_on_custom_axis("acceleration", current, True, False)


def test_truck_detection_accepts_live_canonical_fingerprint_identifiers():
  for fingerprint in (
    "RAM_1500_5TH_GEN",
    "RAM_HD_5TH_GEN",
    "FORD_F_150_MK14",
    "FORD_MAVERICK_MK1",
    "FORD_RANGER_MK2",
    "CHEVROLET_SILVERADO",
    "HONDA_RIDGELINE",
    "HYUNDAI_SANTA_CRUZ_2025",
  ):
    assert is_truck_fingerprint(fingerprint), fingerprint

  assert not is_truck_fingerprint("HYUNDAI_SANTA_FE_2022")
  assert not is_truck_fingerprint(None)


def test_custom_initialisation_seeds_braking_from_selected_preset():
  assert initial_custom_curve(
    "braking", {"preset": "eco", "curve": []}, ev_tuning=True, truck_tuning=True
  ) == [0.5] * 10
  assert initial_custom_curve(
    "braking", {"preset": "sport", "curve": []}, ev_tuning=False, truck_tuning=False
  ) == [2.0] * 10


def test_dom_default_custom_initialisation_uses_effective_legacy_curve():
  legacy_curve = [1.1, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5]
  current = {"preset": "dom_default", "curve": []}
  assert initial_custom_curve("acceleration", current, True, True, legacy_curve=legacy_curve) == [
    round(lpp._linear_interp(speed, lpp._V1_ACCELERATION_SPEEDS_MPH, legacy_curve), 4)
    for speed in ACCELERATION_SPEEDS_MPH
  ]


def test_existing_custom_curve_is_never_reseeded():
  curve = [round(1.0 + index * 0.1, 4) for index in range(10)]
  current = {"preset": "custom", "curve": curve}
  assert initial_custom_curve("acceleration", current, True, True) == curve


def test_profile_update_is_atomic_and_accepts_bounded_following_category():
  profiles = default_personality_profiles(True)
  curve = [round(1.0 + index * 0.1, 4) for index in range(10)]
  updated = update_personality_profile(profiles, "standard", "acceleration", "custom", curve, True, False)
  assert profiles["standard"]["acceleration"]["preset"] == "standard"
  assert updated["standard"]["acceleration"] == {"preset": "custom", "curve": curve}

  following = [0.75 + index * 0.1 for index in range(10)]
  updated = update_personality_profile(updated, "standard", "following", "custom", following, True, False)
  assert profiles["standard"]["following"]["preset"] == "medium"
  assert updated["standard"]["following"] == {"preset": "custom", "curve": [round(value, 4) for value in following]}
  for invalid in ([0.74] * 10, [3.01] * 10, [math.nan] * 10, [True] * 10, [1.0] * 9):
    with pytest.raises(ValueError):
      update_personality_profile(updated, "standard", "following", "custom", invalid, True, False)


def test_serialization_requires_explicit_enabled_state_and_preserves_it():
  profiles = default_personality_profiles(False)
  with pytest.raises(TypeError):
    serialize_personality_profiles(profiles, False)
  encoded = serialize_personality_profiles(profiles, False, enabled=False)
  document = json.loads(encoded)
  assert document == profile_document(profiles, enabled=False)
  assert strict_personality_profiles(encoded) is None
  assert " " not in encoded


def test_loader_is_ui_only_fallback_and_does_not_partially_repair_persisted_document():
  defaults = default_personality_profiles(False)
  assert load_personality_profiles(None, False) == defaults
  malformed = profile_document(defaults, enabled=True)
  malformed["profiles"]["standard"]["acceleration"] = {"preset": "custom", "curve": [1.0] * 7}
  malformed["profiles"]["standard"]["acceleration"]["curve"][0] = math.nan
  assert load_personality_profiles(malformed, False) == defaults
  assert strict_personality_profiles(malformed) is None


def test_custom_interpolation_uses_ten_mph_dom_segments_and_clamps_endpoints():
  config = {"preset": "custom", "curve": [1.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0]}
  breakpoints = [speed * 0.44704 for speed in ACCELERATION_SPEEDS_MPH]
  assert interpolate_category_curve("acceleration", -1.0, config, False, False) == 1.0
  assert interpolate_category_curve("acceleration", 2.5 * 0.44704, config, False, False) == pytest.approx(
    interpolate_accel_profile(2.5 * 0.44704, config["curve"], breakpoints)
  )
  assert interpolate_category_curve("acceleration", 5.0 * 0.44704, config, False, False) == pytest.approx(1.5)
  assert interpolate_category_curve("acceleration", 100.0, config, False, False) == pytest.approx(2.0)


def test_named_presets_are_canonical_without_unused_curve_points():
  profiles = default_personality_profiles(False)
  updated = update_personality_profile(profiles, "traffic", "acceleration", "eco", [], False, False)
  assert updated["traffic"]["acceleration"] == {"preset": "eco", "curve": []}
  document = profile_document(updated, enabled=True)
  assert strict_personality_profiles(document) == updated


def test_following_presets_and_custom_curve_use_exact_ten_mph_linear_axis():
  for preset, curve in FOLLOWING_PRESET_CURVES.items():
    assert category_curve("following", {"preset": preset, "curve": []}, False, False) == list(curve)

  assert FOLLOWING_SPEEDS_MPH == tuple(range(0, 91, 10))
  config = {"preset": "custom", "curve": [0.75 + 0.1 * index for index in range(10)]}
  assert interpolate_category_curve("following", 0.0, config, False, False) == pytest.approx(0.75)
  assert interpolate_category_curve("following", 5.0 * 0.44704, config, False, False) == pytest.approx(0.80)
  assert interpolate_category_curve("following", 90.0 * 0.44704, config, False, False) == pytest.approx(1.65)


def test_following_custom_initialisation_uses_effective_legacy_curve():
  legacy_curve = [1.0 + index * 0.05 for index in range(10)]
  current = {"preset": "dom_default", "curve": []}
  assert initial_custom_curve("following", current, False, False, legacy_curve=legacy_curve) == legacy_curve


def test_v2_uses_one_shared_ten_mph_custom_axis():
  assert PROFILE_SCHEMA_VERSION == 2
  expected = tuple(range(0, 91, 10))
  assert ACCELERATION_SPEEDS_MPH == expected
  assert BRAKING_SPEEDS_MPH == expected
  assert FOLLOWING_SPEEDS_MPH == expected


def test_fresh_profiles_select_standard_standard_and_medium():
  profiles = default_personality_profiles(False)
  for profile in profiles.values():
    assert profile == {
      "acceleration": {"preset": "standard", "curve": []},
      "braking": {"preset": "standard", "curve": []},
      "following": {"preset": "medium", "curve": []},
    }


def test_following_presets_match_stock_dom_personalities_exactly():
  assert FOLLOWING_PRESET_CURVES == {
    "close": (1.25,) * 10,
    "medium": (1.45,) * 10,
    "far": (1.75,) * 10,
  }


@pytest.mark.parametrize("category", ["acceleration", "braking"])
def test_custom_longitudinal_curves_interpolate_on_exact_ten_mph_points(category):
  curve = [0.75 + index * 0.1 for index in range(10)]
  config = {"preset": "custom", "curve": curve}
  assert interpolate_category_curve(category, 20 * 0.44704, config, False, False) == pytest.approx(curve[2])
  assert interpolate_category_curve(category, 25 * 0.44704, config, False, False) == pytest.approx((curve[2] + curve[3]) / 2)


def test_named_acceleration_presets_keep_native_dom_interpolation():
  config = {"preset": "sport", "curve": []}
  native_curve = get_accel_profile_curve_values(ACCELERATION_PROFILES["SPORT"], False, False)
  for speed_mps in (0.0, 2.5, 7.5, 17.5, 32.0, 45.0):
    assert interpolate_category_curve("acceleration", speed_mps, config, False, False) == pytest.approx(
      interpolate_accel_profile(speed_mps, native_curve)
    )


def test_reference_curves_are_profile_specific_and_use_the_custom_axis():
  references = lpp.personality_reference_curves(False, False)
  assert references["traffic"]["acceleration"] != references["aggressive"]["acceleration"]
  assert references["aggressive"]["following"] == [1.25] * 10
  assert references["standard"]["following"] == [1.45] * 10
  assert references["relaxed"]["following"] == [1.75] * 10
  for profile in references.values():
    for curve in profile.values():
      assert len(curve) == 10
      assert all(math.isfinite(value) for value in curve)


def test_exact_v1_document_migrates_whole_or_not_at_all():
  legacy_axes = {
    "acceleration": {
      "speed": {"unit": "mph", "values": [0.0, 11.184681, 22.369363, 33.554044, 44.738726, 55.923407, 89.477452]},
      "value": {"unit": "m/s^2", "meaning": "maximum_requested_acceleration"},
    },
    "braking": {
      "speed": {"unit": "mph", "values": [0.0, 11.184681, 22.369363, 33.554044, 44.738726, 55.923407, 89.477452]},
      "value": {"unit": "m/s^2", "meaning": "cruise_slc_deceleration_magnitude"},
    },
    "following": {
      "speed": {"unit": "mph", "values": list(range(0, 91, 10))},
      "value": {"unit": "s", "meaning": "base_time_headway"},
    },
  }
  legacy_profiles = {
    personality: {
      "acceleration": {"preset": "standard", "curve": []},
      "braking": {"preset": "standard", "curve": []},
      "following": {"preset": "medium", "curve": []},
    }
    for personality in PERSONALITY_IDS
  }
  legacy_profiles["aggressive"]["acceleration"] = {"preset": "custom", "curve": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]}
  legacy = {"schemaVersion": 1, "enabled": True, "axes": legacy_axes, "profiles": legacy_profiles}

  migrated = lpp.migrate_profile_document(legacy)
  assert migrated is not None
  assert migrated["schemaVersion"] == 2
  assert migrated["enabled"] is True
  migrated_acceleration = migrated["profiles"]["aggressive"]["acceleration"]
  assert migrated_acceleration["preset"] == "custom"
  assert len(migrated_acceleration["curve"]) == 10
  assert max(migrated_acceleration["curve"]) == CURVE_BOUNDS["acceleration"][1]
  assert migrated_acceleration["legacyCurve"] == legacy_profiles["aggressive"]["acceleration"]["curve"]
  assert interpolate_category_curve("acceleration", 40.0, migrated_acceleration, False, False) == 4.0
  assert migrated["profiles"]["standard"] == legacy_profiles["standard"]

  malformed = json.loads(json.dumps(legacy))
  malformed["profiles"]["aggressive"]["acceleration"]["curve"][0] = True
  assert lpp.migrate_profile_document(malformed) is None


def test_migrated_custom_acceleration_and_braking_preserve_v1_runtime_behaviour():
  source_axis_ms = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 40.0]
  for category, legacy_curve in (
    ("acceleration", [1.0, 1.4, 1.8, 2.2, 2.6, 3.0, 3.4]),
    ("braking", [0.5, 0.65, 0.8, 0.95, 1.1, 1.25, 1.4]),
  ):
    display_curve = [round(float(value), 4) for value in np.interp(np.array(ACCELERATION_SPEEDS_MPH) * 0.44704, source_axis_ms, legacy_curve)]
    config = {"preset": "custom", "curve": display_curve, "legacyCurve": legacy_curve}
    for speed_mps in np.linspace(0.0, 40.0, 161):
      expected = float(np.interp(speed_mps, source_axis_ms, legacy_curve))
      assert interpolate_category_curve(category, float(speed_mps), config, False, False) == pytest.approx(expected)


def test_v2_legacy_curve_is_strictly_scoped_to_valid_custom_acceleration_and_braking():
  profiles = default_personality_profiles(False)
  profiles["aggressive"]["acceleration"] = {
    "preset": "custom", "curve": [1.0] * 10, "legacyCurve": [1.0] * 7,
  }
  assert lpp.strict_profile_document(profile_document(profiles, enabled=True)) is not None

  invalid_named = json.loads(json.dumps(profiles))
  invalid_named["aggressive"]["acceleration"] = {"preset": "sport", "curve": [], "legacyCurve": [1.0] * 7}
  assert lpp.strict_profile_document(profile_document(invalid_named, enabled=True)) is None

  invalid_following = json.loads(json.dumps(profiles))
  invalid_following["aggressive"]["following"] = {
    "preset": "custom", "curve": [1.25] * 10, "legacyCurve": [1.25] * 7,
  }
  assert lpp.strict_profile_document(profile_document(invalid_following, enabled=True)) is None

  invalid_boolean = json.loads(json.dumps(profiles))
  invalid_boolean["aggressive"]["acceleration"]["legacyCurve"][0] = True
  assert lpp.strict_profile_document(profile_document(invalid_boolean, enabled=True)) is None


def test_noop_custom_update_keeps_saved_legacy_runtime_curve():
  profiles = default_personality_profiles(False)
  profiles["aggressive"]["acceleration"] = {
    "preset": "custom", "curve": [3.5] * 10, "legacyCurve": [4.0] * 7,
  }
  updated = update_personality_profile(profiles, "aggressive", "acceleration", "custom", [3.5] * 10, False)
  assert updated == profiles
  assert interpolate_category_curve("acceleration", 10.0, updated["aggressive"]["acceleration"], False) == 4.0


def test_editing_a_migrated_custom_curve_retires_the_legacy_runtime_contract():
  profiles = default_personality_profiles(False)
  profiles["aggressive"]["acceleration"] = {
    "preset": "custom", "curve": [1.0] * 10, "legacyCurve": [1.0] * 7,
  }
  updated = update_personality_profile(
    profiles, "aggressive", "acceleration", "custom", [1.2] * 10, False, False,
  )
  assert updated["aggressive"]["acceleration"] == {"preset": "custom", "curve": [1.2] * 10}


def test_initial_custom_curve_resamples_named_preset_to_custom_axis():
  curve = initial_custom_curve("acceleration", {"preset": "sport", "curve": []}, False, False)
  assert len(curve) == 10
  config = {"preset": "sport", "curve": []}
  for speed_mph, value in zip(ACCELERATION_SPEEDS_MPH, curve, strict=True):
    assert value == pytest.approx(interpolate_category_curve("acceleration", speed_mph * 0.44704, config, False, False), abs=5e-5)
