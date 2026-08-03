from openpilot.common.params import UnknownKeyName
from openpilot.starpilot.common.safe_mode import (
  SAFE_MODE_BACKUP_PARAM,
  SAFE_MODE_MANAGED_KEYS,
  apply_safe_mode,
  restore_safe_mode,
  _apply_value,
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
