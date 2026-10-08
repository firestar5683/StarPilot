from types import SimpleNamespace

from opendbc.car.hyundai.values import CAR
from openpilot.starpilot.car.hyundai.button_migration import MIGRATION_KEY, migrate_lkas_default


class Saved:
  def __init__(self, action):
    self.values = {'LKASButtonControl': action, 'AlwaysOnLateral': False}
  def get(self, key, **kwargs):
    return self.values.get(key)
  def get_bool(self, key):
    return bool(self.values.get(key, False))
  def get_param_path(self, key):
    return '/path-that-does-not-exist-for-test/' + key
  def put(self, key, value, **kwargs):
    self.values[key] = value
  def put_bool(self, key, value, **kwargs):
    self.values[key] = value


def test_sonata_migration_is_once_and_preserves_postmigration_choice():
  cp = SimpleNamespace(brand='hyundai', carFingerprint=CAR.HYUNDAI_SONATA_HYBRID)
  saved = Saved(None)
  assert migrate_lkas_default(cp, saved)
  assert saved.get('LKASButtonControl') == 9
  assert not saved.get_bool('AlwaysOnLateral')
  saved.put('LKASButtonControl', b'5')
  assert not migrate_lkas_default(cp, saved)
  assert saved.get('LKASButtonControl') == b'5'
  assert saved.get_bool(MIGRATION_KEY)


def test_unknown_carparams_never_reads_or_writes_saved_settings():
  class Unused:
    def get_bool(self, *_):
      raise AssertionError('Unknown identity must not access settings')
  for cp in (None, object(), SimpleNamespace(), SimpleNamespace(brand='hyundai')):
    assert not migrate_lkas_default(cp, Unused())


def test_custom_mapping_and_ioniq_are_preserved():
  cp = SimpleNamespace(brand='hyundai', carFingerprint=CAR.HYUNDAI_SONATA_HYBRID)
  for action in (b'0', b'3', b'4', b'5', b'9', b'garbage'):
    saved = Saved(action)
    assert migrate_lkas_default(cp, saved)
    assert saved.get('LKASButtonControl') == action
  cp.carFingerprint = CAR.HYUNDAI_IONIQ_6
  saved = Saved(b'5')
  assert not migrate_lkas_default(cp, saved)
  assert saved.get('LKASButtonControl') == b'5'
  assert not saved.get_bool(MIGRATION_KEY)
