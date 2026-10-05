from contextvars import ContextVar
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.long_profile_feature import LongProfileFeature
from openpilot.starpilot.ui.slc_offset_feature import _capability


class ConfigurationLongitudinalTests(unittest.TestCase):
  def test_configuration_capability_does_not_mutate_factory_ownership(self):
    cp = SimpleNamespace(carFingerprint='saved model', openpilotLongitudinalControl=False, pcmCruise=True,
                         passive=False, notCar=False, dashcamOnly=False, carVin='')
    before = vars(cp).copy()
    owner = object.__new__(FeatureSettingsOwner)
    owner._snapshot_vehicle = ContextVar("configuration_test_vehicle", default=None)
    owner.vehicle_params = lambda: cp
    enabled = [False]
    owner.configuration_longitudinal = lambda: enabled[0]
    owner.params = Mock()
    feature = LongProfileFeature(owner)
    self.assertFalse(owner.longitudinal_available())
    self.assertIsNone(feature.capability())
    self.assertIsNone(_capability(cp))
    enabled[0] = True
    self.assertTrue(owner.longitudinal_available())
    capability = feature.capability()
    offsets = _capability(cp, True)
    assert capability is not None and offsets is not None
    self.assertEqual(capability[1:3], (True, False))
    self.assertEqual(offsets[1:3], (True, False))
    cp.dashcamOnly = True
    self.assertIsNone(feature.capability())
    self.assertIsNone(_capability(cp, True))
    cp.dashcamOnly = False
    enabled[0] = False
    self.assertIsNone(feature.capability())
    self.assertEqual(vars(cp), before)

  def test_live_longitudinal_does_not_require_configuration_callback(self):
    cp = SimpleNamespace(carFingerprint='live model', openpilotLongitudinalControl=True, pcmCruise=False,
                         passive=False, notCar=False, dashcamOnly=False, carVin='')
    owner = object.__new__(FeatureSettingsOwner)
    owner._snapshot_vehicle = ContextVar("configuration_test_vehicle", default=None)
    owner.vehicle_params = lambda: cp
    owner.configuration_longitudinal = lambda: False
    owner.params = Mock()
    self.assertTrue(owner.longitudinal_available())
    capability = LongProfileFeature(owner).capability()
    assert capability is not None
    self.assertEqual(capability[1:3], (True, False))
