from copy import deepcopy

import numpy as np
import pytest

from openpilot.starpilot.common import longitudinal_personality_profiles as lpp


@pytest.mark.parametrize("preset,breakpoints,values", [
  ("close", [45.0, 70.0], [1.25, 1.0]),
  ("medium", [45.0, 70.0], [1.45, 1.2]),
  ("far", [45.0, 70.0], [1.6, 1.4]),
  ("traffic", [0.0, 25.0 / 0.44704], [0.75, 1.6]),
])
def test_named_following_presets_match_dom_at_and_between_native_breakpoints(preset, breakpoints, values):
  config = {"preset": preset, "curve": []}
  for mph in sorted(set([0, 10, 44.9, 45, 45.1, 50, 55, 55.9234073, 60, 65, 69.9, 70, 70.1, 90, 120, *breakpoints])):
    expected = float(np.interp(mph, breakpoints, values))
    assert lpp.interpolate_category_curve("following", mph * 0.44704, config, False) == pytest.approx(expected, abs=1e-12)
  sampled = lpp.initial_custom_curve("following", config, False, False)
  assert sampled == [round(float(np.interp(mph, breakpoints, values)), 4) for mph in lpp.FOLLOWING_SPEEDS_MPH]


def test_close_medium_far_keep_their_order_at_every_speed():
  for mph in np.linspace(0, 120, 481):
    values = [lpp.interpolate_category_curve("following", mph * 0.44704, {"preset": p, "curve": []}, False) for p in ("close", "medium", "far")]
    assert values[0] < values[1] < values[2]


@pytest.mark.parametrize("preset,value", [("close", 1.25), ("medium", 1.45), ("far", 1.75)])
def test_old_named_selection_keeps_fixed_distance_after_load_save_and_reload(preset, value):
  original = lpp.profile_document(lpp.default_personality_profiles(False), enabled=True)
  original["schemaVersion"] = 2
  original["profiles"]["standard"]["following"] = {"preset": preset, "curve": []}
  saved = deepcopy(original)
  loaded = lpp.strict_profile_document(original)
  assert original == saved
  config = loaded["profiles"]["standard"]["following"]
  assert config == {"preset": "legacy_" + preset, "curve": []}
  for mph in (0, 45, 60, 70, 100):
    assert lpp.interpolate_category_curve("following", mph * 0.44704, config, False) == value
  reloaded = lpp.strict_profile_document(lpp.serialize_personality_profiles(loaded["profiles"], False, enabled=True))
  assert reloaded == loaded
  updated = lpp.update_personality_profile(loaded["profiles"], "standard", "following", preset, [], False)
  assert updated["standard"]["following"] == {"preset": preset, "curve": []}
  assert lpp.interpolate_category_curve("following", 70 * 0.44704, updated["standard"]["following"], False) != value


@pytest.mark.parametrize("preset", ["traffic", "legacy_close", "legacy_medium", "legacy_far"])
def test_old_schema_cannot_smuggle_new_preset_names(preset):
  document = lpp.profile_document(lpp.default_personality_profiles(False), enabled=True)
  document["schemaVersion"] = 2
  document["profiles"]["standard"]["following"]["preset"] = preset
  assert lpp.strict_profile_document(document) is None


def test_named_following_switches_keep_remembered_custom_points():
  profiles = lpp.default_personality_profiles(False)
  custom = [1.55] * 10
  profiles["traffic"]["following"] = {"preset": "custom", "curve": custom}
  for preset in ("close", "medium", "far", "traffic", "dom_default"):
    profiles = lpp.update_personality_profile(profiles, "traffic", "following", preset, [], False)
    assert profiles["traffic"]["following"]["curve"] == custom
  restored = lpp.initial_custom_curve("following", profiles["traffic"]["following"], False, False)
  assert restored == custom
