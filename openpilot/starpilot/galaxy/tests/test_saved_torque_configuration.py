import json
from pathlib import Path
import tempfile
import unittest

from openpilot.common.params import Params
from openpilot.starpilot.galaxy.vehicle_configuration import saved_torque_context
from openpilot.starpilot.lateral.controller_selection import KNOWN_POLICIES
from openpilot.starpilot.lateral.torque_settings import FieldChoice, PlatformProfile, serialize_document
from openpilot.starpilot.vehicle_selection import encode


class TestSavedTorqueConfiguration(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.params.put('LateralControllerSelection', json.loads(
      '{"vehicles":{"HYUNDAI_IONIQ_6":{"brand":"hyundai","mode":"starpilot"}},"version":1}'), block=True)
    self.params.put('TorqueOverrideDocument', json.loads(
      '{"schemaVersion":1,"vehicles":{"HYUNDAI_IONIQ_6":{"basis":{"friction":0.09000000357627869,' +
      '"latAccelFactor":3.0,"latAccelOffset":0.0},"factor":{"customValue":2.1,"mode":"source"},' +
      '"friction":{"customValue":null,"mode":"source"}}}}'), block=True)

  def save(self, identities, factor=1.8, mode='starpilot'):
    controller = {'version': 1, 'vehicles': {identity: {'brand': KNOWN_POLICIES[identity], 'mode': mode} for identity in identities}}
    self.params.put('LateralControllerSelection', controller, block=True)
    document = serialize_document({identity: PlatformProfile((1.8, 0.0, 0.1), FieldChoice('custom', factor), FieldChoice())
                                   for identity in identities})
    self.params.put('TorqueOverrideDocument', json.loads(document), block=True)

  def test_retained_single_profile_can_edit_without_current_vehicle(self):
    cp, token = saved_torque_context(self.params)
    self.assertEqual(cp.carFingerprint, 'HYUNDAI_IONIQ_6')
    self.assertTrue(token.startswith(b'saved-torque-configuration:'))
    self.assertFalse(Path(self.params.get_param_path('VehicleSelection')).exists())
    for key in ('CarParams', 'CarParamsPersistent', 'CarParamsCache'):
      self.assertFalse(Path(self.params.get_param_path(key)).exists())

  def test_normal_profile_edits_do_not_invalidate_configuration_token(self):
    _, token = saved_torque_context(self.params)
    self.save(('HYUNDAI_IONIQ_6',), factor=2.0, mode='standard')
    self.assertEqual(saved_torque_context(self.params)[1], token)
    self.params.put_bool('AlphaLongitudinalEnabled', True, block=True)
    self.assertNotEqual(saved_torque_context(self.params)[1], token)

  def test_ambiguous_or_malformed_saved_documents_fail_closed(self):
    self.save(('HYUNDAI_IONIQ_6', 'CHEVROLET_BOLT_CC_2018_2021'))
    self.assertEqual(saved_torque_context(self.params), (None, None))
    for key in ('TorqueOverrideDocument', 'LateralControllerSelection'):
      self.save(('HYUNDAI_IONIQ_6',))
      self.params.put(key, {}, block=True)
      self.assertEqual(saved_torque_context(self.params), (None, None))

  def test_unreadable_missing_or_manual_selected_are_not_fallback_contexts(self):
    self.params.put('VehicleSelection', json.loads(encode('HYUNDAI_IONIQ_6')), block=True)
    self.assertEqual(saved_torque_context(self.params), (None, None))
    self.params.put('VehicleSelection', json.loads(encode(None)), block=True)
    self.params.remove('TorqueOverrideDocument')
    self.assertEqual(saved_torque_context(self.params), (None, None))
    self.save(('HYUNDAI_IONIQ_6',))
    path = Path(self.params.get_param_path('TorqueOverrideDocument'))
    path.unlink()
    path.symlink_to('LateralControllerSelection')
    self.assertEqual(saved_torque_context(self.params), (None, None))

  def test_each_document_must_name_the_same_single_vehicle(self):
    self.params.put('LateralControllerSelection', {'version': 1, 'vehicles': {}}, block=True)
    self.assertEqual(saved_torque_context(self.params), (None, None))
    self.save(('HYUNDAI_IONIQ_6',))
    self.params.put('TorqueOverrideDocument', {'schemaVersion': 1, 'vehicles': {}}, block=True)
    self.assertEqual(saved_torque_context(self.params), (None, None))
