"""Removed acceleration setting and refusal of stale configurable requests."""

from pathlib import Path
import tempfile
import unittest

from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.common.params import Params
from openpilot.starpilot.galaxy.settings import AuthorityContext, SettingsGateway
from openpilot.starpilot.longitudinal.output_max import KEY
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest


class Context:
  def __init__(self, cp):
    self.value = AuthorityContext(False, cp, b'current-cp')

  def sample(self):
    return self.value


class OutputMaximumFeatureTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    self.context = Context(self.cp)
    self.gateway = SettingsGateway(self.params, self.context, clock=lambda: 10.)
    self.owner = FeatureSettingsOwner(self.params, lambda group: True,
                                      vehicle_fingerprint=lambda: getattr(self.context.value.cp, 'carFingerprint', None),
                                      vehicle_params=lambda: self.context.value.cp)

  def test_setting_absent_onroad_and_parked_with_saved_legacy_value(self):
    path = Path(self.params.get_param_path(KEY))
    for raw in (b'0.5', b'4.0', b'broken'):
      path.write_bytes(raw)
      for parked in (False, True):
        for cp in (self.cp, None):
          with self.subTest(raw=raw, parked=parked, cp=cp):
            self.context.value = AuthorityContext(parked, cp, b'current-cp')
            page = self.gateway.page('profiles', 'session', b'generation')
            self.assertFalse(any(row['label'] == 'Maximum acceleration' for row in page['rows']))
            rows = self.owner.snapshot('profiles', parked=parked, system_long=False, lateral_context=False, metric=False).rows
            self.assertFalse(any(row.key == KEY for row in rows))
            self.assertEqual(path.read_bytes(), raw)

  def test_stale_numeric_repair_and_default_requests_cannot_write(self):
    path = Path(self.params.get_param_path(KEY))
    for raw in (b'0.5', b'broken'):
      path.write_bytes(raw)
      for value in ('0.1', '4.0', 'nan'):
        for confirmed in (False, True):
          request = FeatureSettingsRequest(KEY, raw, value, confirmation=confirmed)
          self.assertFalse(self.owner.apply(request))
          self.assertEqual(path.read_bytes(), raw)
