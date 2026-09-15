import json
from copy import deepcopy

import pytest

from openpilot.starpilot.common import longitudinal_personality_profiles as lpp


@pytest.mark.parametrize("personality", lpp.PERSONALITY_IDS)
@pytest.mark.parametrize("category,preset", [("acceleration", "eco"), ("braking", "sport"), ("following", "far")])
def test_custom_survives_preset_changes_serialization_and_reload(personality, category, preset):
  profiles = lpp.default_personality_profiles(False)
  curve = [round(1.0 + i * 0.05, 4) for i in range(10)]
  profiles = lpp.update_personality_profile(profiles, personality, category, "custom", curve, False)
  other_profiles = deepcopy(profiles)
  for selected in (preset, "dom_default", preset):
    profiles = lpp.update_personality_profile(profiles, personality, category, selected, [], False)
    profiles = lpp.load_personality_profiles(lpp.serialize_personality_profiles(profiles, False, enabled=True), False)
    assert profiles[personality][category] == {"preset": selected, "curve": curve}
    if selected != "dom_default":
      assert lpp.category_curve(category, profiles[personality][category], False) == lpp.category_curve(category, {"preset": selected, "curve": []}, False)
  seed = lpp.initial_custom_curve(category, profiles[personality][category], False, False, legacy_curve=[2.0] * 10)
  profiles = lpp.update_personality_profile(profiles, personality, category, "custom", seed, False)
  assert profiles == other_profiles


def test_switching_preserves_high_points_and_legacy_runtime_only_for_custom():
  profiles = lpp.default_personality_profiles(False)
  saved = {"preset": "custom", "curve": [4.0] * 10, "legacyCurve": [5.0] * 7}
  profiles["aggressive"]["acceleration"] = deepcopy(saved)
  profiles = lpp.update_personality_profile(profiles, "aggressive", "acceleration", "eco", [], False)
  assert profiles["aggressive"]["acceleration"]["legacyCurve"] == saved["legacyCurve"]
  assert lpp.interpolate_category_curve("acceleration", 12, profiles["aggressive"]["acceleration"], False) == lpp.interpolate_category_curve("acceleration", 12, {"preset": "eco", "curve": []}, False)
  profiles = lpp.update_personality_profile(profiles, "aggressive", "acceleration", "custom", [4.0] * 10, False)
  assert profiles["aggressive"]["acceleration"] == saved


def test_v2_load_is_lossless_and_next_write_uses_new_version():
  document = lpp.profile_document(lpp.default_personality_profiles(False), enabled=True)
  document["schemaVersion"] = 2
  document["profiles"]["standard"]["acceleration"] = {"preset": "custom", "curve": [4.0] * 10}
  loaded = lpp.strict_profile_document(document)
  assert loaded is not None
  assert loaded["profiles"] == document["profiles"]
  assert json.loads(lpp.serialize_personality_profiles(loaded["profiles"], False, enabled=True))["schemaVersion"] > 2
  document["profiles"]["standard"]["acceleration"]["preset"] = "eco"
  assert lpp.strict_profile_document(document) is None  # v2 never allowed dormant curves


@pytest.mark.parametrize("curve", [[True] * 10, [float("nan")] * 10, [1.0] * 9, [7.0] * 10])
def test_dormant_curves_are_validated(curve):
  profiles = lpp.default_personality_profiles(False)
  profiles["standard"]["acceleration"] = {"preset": "eco", "curve": curve}
  assert lpp.strict_profile_document(lpp.profile_document(profiles, enabled=True)) is None
