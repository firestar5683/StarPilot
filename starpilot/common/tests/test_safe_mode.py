import ast
from pathlib import Path

import pytest

from openpilot.common.params import UnknownKeyName
from openpilot.starpilot.common.safe_mode import (
  SAFE_MODE_BACKUP_PARAM,
  SAFE_MODE_MANAGED_KEYS,
  apply_safe_mode,
  restore_safe_mode,
  _apply_value,
)
from openpilot.starpilot.common.longitudinal_personality_profiles import (
  PERSONALITY_PROFILES_PARAM,
  default_personality_profiles,
  profile_document,
  strict_profile_document,
)


class RemovedParamStore:
  def get(self, key):
    raise UnknownKeyName(key)


class FakeParamStore:
  def __init__(self, values=None):
    self.values = dict(values or {})

  def get(self, key):
    return self.values.get(key)

  def get_stock_value(self, key):
    return None

  def get_bool(self, key):
    return bool(self.values.get(key, False))

  def put(self, key, value):
    self.values[key] = value

  def put_bool(self, key, value):
    self.values[key] = bool(value)

  def remove(self, key):
    self.values.pop(key, None)


def test_apply_value_ignores_removed_param():
  assert not _apply_value(RemovedParamStore(), "RemovedParam", "stale value")


def test_safe_mode_does_not_manage_manual_fingerprint():
  assert "ForceFingerprint" not in SAFE_MODE_MANAGED_KEYS


def test_safe_mode_migrates_saved_manual_fingerprint_out_of_backup():
  params = FakeParamStore()
  params_raw = FakeParamStore({
    "ForceFingerprint": False,
    SAFE_MODE_BACKUP_PARAM: {
      "ForceFingerprint": {"present": True, "value": True},
    },
  })

  apply_safe_mode(params, params_raw)

  assert params_raw.get("ForceFingerprint") is True
  assert "ForceFingerprint" not in params_raw.get(SAFE_MODE_BACKUP_PARAM)


def test_safe_mode_restore_ignores_stale_manual_fingerprint_backup():
  params_raw = FakeParamStore({
    "ForceFingerprint": True,
    SAFE_MODE_BACKUP_PARAM: {
      "ForceFingerprint": {"present": True, "value": False},
    },
  })

  restore_safe_mode(params_raw)

  assert params_raw.get("ForceFingerprint") is True


def test_safe_mode_backs_up_and_enforces_a_valid_disabled_profile_document_repeatedly():
  profiles = default_personality_profiles(False)
  profiles["standard"]["acceleration"] = {"preset": "sport", "curve": []}
  original = profile_document(profiles, enabled=True)
  params = FakeParamStore()
  params_raw = FakeParamStore({PERSONALITY_PROFILES_PARAM: original})

  assert apply_safe_mode(params, params_raw)
  safe_document = strict_profile_document(params_raw.get(PERSONALITY_PROFILES_PARAM))
  assert safe_document is not None and safe_document["enabled"] is False
  assert params_raw.get(SAFE_MODE_BACKUP_PARAM)[PERSONALITY_PROFILES_PARAM] == {
    "present": True, "value": original,
  }

  params_raw.put(PERSONALITY_PROFILES_PARAM, original)
  assert apply_safe_mode(params, params_raw)
  assert strict_profile_document(params_raw.get(PERSONALITY_PROFILES_PARAM))["enabled"] is False
  assert params_raw.get(SAFE_MODE_BACKUP_PARAM)[PERSONALITY_PROFILES_PARAM]["value"] == original


def test_safe_mode_restores_profile_document_exactly():
  original = profile_document(default_personality_profiles(False), enabled=True)
  params = FakeParamStore()
  params_raw = FakeParamStore({
    PERSONALITY_PROFILES_PARAM: original,
    "IsOnroad": False,
    "IsOffroad": True,
  })
  apply_safe_mode(params, params_raw)

  assert restore_safe_mode(params_raw)
  assert params_raw.get(PERSONALITY_PROFILES_PARAM) == original
  assert params_raw.get(SAFE_MODE_BACKUP_PARAM) is None


def test_safe_mode_restore_waits_for_confirmed_offroad_state():
  original = profile_document(default_personality_profiles(False), enabled=True)

  for road_state in (
    {"IsOnroad": True, "IsOffroad": True},
    {"IsOnroad": False, "IsOffroad": False},
    {"IsOnroad": True, "IsOffroad": False},
  ):
    params = FakeParamStore()
    params_raw = FakeParamStore({PERSONALITY_PROFILES_PARAM: original, **road_state})
    apply_safe_mode(params, params_raw)
    safe_document = params_raw.get(PERSONALITY_PROFILES_PARAM)
    backup = params_raw.get(SAFE_MODE_BACKUP_PARAM)

    assert restore_safe_mode(params_raw) is False
    assert params_raw.get(PERSONALITY_PROFILES_PARAM) == safe_document
    assert params_raw.get(SAFE_MODE_BACKUP_PARAM) == backup


@pytest.mark.parametrize("unreadable_key", ["IsOnroad", "IsOffroad"])
def test_safe_mode_restore_fails_closed_when_either_road_state_cannot_be_read(unreadable_key):
  class UnreadableRoadStateParamStore(FakeParamStore):
    def get_bool(self, key):
      if key == unreadable_key:
        raise RuntimeError(f"cannot read {key}")
      return super().get_bool(key)

  backup = {PERSONALITY_PROFILES_PARAM: {"present": True, "value": {}}}
  params_raw = UnreadableRoadStateParamStore({
    SAFE_MODE_BACKUP_PARAM: backup,
    "IsOnroad": False,
    "IsOffroad": True,
  })

  assert restore_safe_mode(params_raw) is False
  assert params_raw.get(SAFE_MODE_BACKUP_PARAM) == backup


def test_starpilot_process_retries_restore_while_backup_remains_including_after_restart():
  process_path = Path(__file__).resolve().parents[2] / "starpilot_process.py"
  tree = ast.parse(process_path.read_text(encoding="utf-8"), filename=str(process_path))
  function = next(
    (node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "update_safe_mode_state"),
    None,
  )
  assert function is not None

  restore_calls = []
  namespace = {
    "SAFE_MODE_BACKUP_PARAM": SAFE_MODE_BACKUP_PARAM,
    "safe_mode_enabled": lambda _params: False,
    "apply_safe_mode": lambda *_args, **_kwargs: None,
    "restore_safe_mode": lambda *_args: restore_calls.append(True),
  }
  exec(compile(ast.Module(body=[function], type_ignores=[]), str(process_path), "exec"), namespace)
  update_safe_mode_state = namespace["update_safe_mode_state"]
  backup = {PERSONALITY_PROFILES_PARAM: {"present": True, "value": {}}}
  params_raw = FakeParamStore({SAFE_MODE_BACKUP_PARAM: backup})

  safe_mode_active = update_safe_mode_state(None, params_raw, None, False)
  safe_mode_active = update_safe_mode_state(None, params_raw, None, safe_mode_active)

  assert safe_mode_active is True
  assert restore_calls == [True, True]
