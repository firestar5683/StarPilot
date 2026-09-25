from dataclasses import replace
import tempfile
import unittest

from openpilot.common.params import Params
from openpilot.starpilot.ui.appearance_owner import AppearanceOwner
from openpilot.starpilot.ui.display_owner import DisplayOwner
from openpilot.starpilot.ui.feature_settings_state import row_change, row_default
from openpilot.starpilot.ui.pip_owner import PiPOwner
from openpilot.starpilot.ui.power_owner import PowerOwner
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.sentry_owner import SentryOwner, SENSITIVITY, WARNING
from openpilot.starpilot.ui.sounds_owner import SoundsOwner
from openpilot.starpilot.ui.vasm_owner import VASMOwner


class StandaloneDefaultsTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.parked = True

  def test_scalar_metadata_matches_owner_defaults_and_actions_have_none(self):
    def parked():
      return self.parked
    owners = (SoundsOwner(self.params, parked), SentryOwner(self.params, parked),
              PowerOwner(self.params, parked), VASMOwner(self.params, parked),
              PiPOwner(self.params, parked, lambda: True))
    for owner in owners:
      for row in owner.snapshot().rows:
        with self.subTest(owner=type(owner).__name__, key=row.key):
          if isinstance(owner, PiPOwner) and row.step:
            self.assertIsNone(row.default_value)
          elif row.choices or row.step:
            self.assertIsNotNone(row.default_value)
          elif row.page or not row.key:
            self.assertIsNone(row.default_value)
    for profile in (Profile.LARGE, Profile.COMPACT):
      for owner in (AppearanceOwner(self.params, parked), DisplayOwner(self.params, parked)):
        for row in owner.snapshot(profile).rows:
          if isinstance(owner, PiPOwner) and row.step:
            self.assertIsNone(row.default_value)
          elif row.choices or row.step:
            self.assertIsNotNone(row.default_value, row.key)

  def test_appearance_reset_preserves_unrelated_choice_and_paired_encoding(self):
    self.params.put_bool('ShowBrakeStatus', True, block=True)
    self.params.put_bool('PedalsOnUI', True, block=True)
    self.params.put_bool('RainbowPath', True, block=True)
    owner = AppearanceOwner(self.params, lambda: self.parked)
    row = next(row for row in owner.snapshot(Profile.COMPACT).rows if row.key == 'ShowBrakeStatus')
    request = row_default(row)
    assert request is not None
    self.assertEqual(request.dependencies, row.dependencies)
    self.assertTrue(owner.apply(request))
    self.assertEqual(self.params.get('ShowBrakeStatus'), False)
    self.assertEqual(self.params.get('PedalsOnUI'), False)
    self.assertEqual(self.params.get('RainbowPath'), True)
    self.assertFalse(owner.apply(request))

  def test_json_field_reset_preserves_neighbor_and_rechecks_parked(self):
    owner = SentryOwner(self.params, lambda: self.parked)
    warning = next(row for row in owner.snapshot().rows if row.key == WARNING)
    change = row_change(warning)
    assert change is not None
    self.assertTrue(owner.apply(replace(change, confirmation=True)))
    rows = owner.snapshot().rows
    sensitivity = next(row for row in rows if row.key == SENSITIVITY)
    request = row_default(sensitivity)
    assert request is not None
    self.parked = False
    self.assertFalse(owner.apply(request))
    self.parked = True
    self.assertTrue(owner.apply(request))
    self.assertEqual(next(row.value for row in owner.snapshot().rows if row.key == WARNING), change.value)
