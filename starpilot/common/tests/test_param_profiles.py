import json

import pytest

from openpilot.common.params import ParamKeyFlag, ParamKeyType
from openpilot.starpilot.common import param_profiles


class FakeParams:
  def __init__(self):
    persistent = ParamKeyFlag.PERSISTENT
    self.definitions = {
      "BooleanSetting": (True, ParamKeyType.BOOL, persistent),
      "NumericSetting": (1.5, ParamKeyType.FLOAT, persistent),
      "JsonSetting": ({"mode": "default"}, ParamKeyType.JSON, persistent),
      "SecretSetting": ("", ParamKeyType.STRING, persistent | ParamKeyFlag.DONT_LOG),
      "TransientSetting": (False, ParamKeyType.BOOL, ParamKeyFlag.CLEAR_ON_MANAGER_START),
    }
    self.values = {
      "BooleanSetting": False,
      "NumericSetting": 2.75,
      "JsonSetting": {"mode": "custom"},
      "SecretSetting": "secret",
      "TransientSetting": True,
    }

  def all_keys(self):
    return list(self.definitions)

  def get(self, key, return_default=False):
    default = self.definitions[key][0] if return_default else None
    return self.values.get(key, default)

  def get_default_value(self, key):
    return self.definitions[key][0]

  def get_key_flag(self, key):
    return self.definitions[key][2]

  def get_type(self, key):
    return self.definitions[key][1]

  def put(self, key, value):
    self.values[key] = value


def test_profile_slots_round_trip_only_eligible_settings(tmp_path):
  params = FakeParams()

  status = param_profiles.save_profile(params, "a", profile_root=tmp_path)
  payload = json.loads((tmp_path / ".params-profile-a.json").read_text())

  assert status["saved"] is True
  assert status["settingsCount"] == 3
  assert set(payload["settings"]) == {"BooleanSetting", "NumericSetting", "JsonSetting"}

  params.values.update({
    "BooleanSetting": True,
    "NumericSetting": 9.0,
    "JsonSetting": {"mode": "changed"},
    "SecretSetting": "new-secret",
    "TransientSetting": False,
  })
  result = param_profiles.load_profile(params, "a", profile_root=tmp_path)

  assert result["restoredCount"] == 3
  assert result["skippedCount"] == 0
  assert params.values["BooleanSetting"] is False
  assert params.values["NumericSetting"] == 2.75
  assert params.values["JsonSetting"] == {"mode": "custom"}
  assert params.values["SecretSetting"] == "new-secret"
  assert params.values["TransientSetting"] is False


def test_prepare_profile_decodes_without_writes_and_preserves_type_filtering(tmp_path):
  params = FakeParams()
  param_profiles.save_profile(params, "a", profile_root=tmp_path)
  params.values.clear()
  params.definitions["NumericSetting"] = (0, ParamKeyType.INT, ParamKeyFlag.PERSISTENT)

  prepared = param_profiles.prepare_profile(params, "a", profile_root=tmp_path)

  assert params.values == {}
  assert prepared["settings"] == {"BooleanSetting": False, "JsonSetting": {"mode": "custom"}}
  assert prepared["skippedCount"] == 1
  assert prepared["slot"] == "a"
  result = param_profiles.load_profile(params, "a", profile_root=tmp_path)
  assert result["restoredCount"] == 2
  assert result["skippedCount"] == 1
  assert params.values == prepared["settings"]


def test_profile_slots_report_missing_and_damaged_profiles(tmp_path):
  params = FakeParams()

  with pytest.raises(param_profiles.ParamProfileError, match="has not been saved"):
    param_profiles.load_profile(params, "b", profile_root=tmp_path)
  with pytest.raises(param_profiles.ParamProfileError, match="Unknown"):
    param_profiles.save_profile(params, "c", profile_root=tmp_path)

  (tmp_path / ".params-profile-b.json").write_text("not json")
  assert param_profiles.profile_status("b", profile_root=tmp_path)["invalid"] is True
  with pytest.raises(param_profiles.ParamProfileError, match="damaged"):
    param_profiles.load_profile(params, "b", profile_root=tmp_path)
