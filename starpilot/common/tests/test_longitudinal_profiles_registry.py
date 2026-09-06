from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_longitudinal_profiles_is_a_persistent_nonlogged_json_param():
  source = (ROOT / "common/params_keys.h").read_text(encoding="utf-8")
  declaration = '{"LongitudinalPersonalityProfiles", {PERSISTENT | DONT_LOG, JSON, "{}", "{}"}}'
  assert declaration in source
  assert source.count('{"LongitudinalPersonalityProfiles"') == 1


def test_longitudinal_profiles_is_listed_as_feasible_without_removing_legacy_keys():
  feasible = (ROOT / "tools/StarPilot/feasibleparams.txt").read_text(encoding="utf-8")
  keys = set(feasible.splitlines())
  assert "LongitudinalPersonalityProfiles" in keys
  assert {"TrafficPersonalityProfile", "AggressivePersonalityProfile", "StandardPersonalityProfile", "RelaxedPersonalityProfile"} <= keys
  assert "Total globally registered C++ keys:  546" in feasible
  assert "Total Editable/Toggleable targets:   391" in feasible
