"""One shared saved steering-controller choice with exact source and CP guards."""

from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR as HYUNDAI
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.common.params import Params
from openpilot.starpilot.lateral.controller_selection import (
  DOCUMENT_KEY, ControllerMode, parse_document, read_selection,
)
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest, row_change
from openpilot.starpilot.galaxy.settings import (
  AuthorityContext, SettingsChanged, SettingsGateway, _onroad_preference, _projection,
)


class TestControllerFeature(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.params = Params(self.temp.name)
    self.cp = interfaces[HYUNDAI.HYUNDAI_IONIQ_6].get_non_essential_params(HYUNDAI.HYUNDAI_IONIQ_6)
    self.permitted = True
    self.owner = FeatureSettingsOwner(self.params, lambda group: self.permitted and group == 'preferences',
                                      vehicle_fingerprint=lambda: str(self.cp.carFingerprint),
                                      vehicle_params=lambda: self.cp)

  def row(self, key=DOCUMENT_KEY):
    state = self.owner.snapshot('torque', parked=False, system_long=False, lateral_context=False, metric=False)
    return next((row for row in state.rows if row.key == key), None)

  def test_exact_choice_visible_without_manual_tuning_or_park_lock(self):
    for vehicle in (HYUNDAI.HYUNDAI_IONIQ_6, HYUNDAI.GENESIS_G70_2020, TOYOTA.TOYOTA_COROLLA_TSS2):
      with self.subTest(vehicle=vehicle):
        self.cp = interfaces[vehicle].get_non_essential_params(vehicle)
        row = self.row()
        self.assertIsNotNone(row)
        self.assertTrue(row.available)
        self.assertEqual((row.label, row.value), ('Torque controller', 'StarPilot vehicle tune'))
        self.assertEqual(row.choices, ('Standard openpilot', 'StarPilot vehicle tune'))
        self.assertIn('next drive', row.reason)
        self.assertNotIn('active', row.reason.lower())
        self.assertEqual(_projection(row, 'torque')['choices'], list(row.choices))
    self.assertTrue(_onroad_preference('torque', DOCUMENT_KEY))
    self.assertFalse(self.params.get_bool('AdvancedLateralTune'))
    self.cp = interfaces[HYUNDAI.KIA_EV6].get_non_essential_params(HYUNDAI.KIA_EV6)
    self.assertIsNone(self.row())
    self.cp = interfaces[HYUNDAI.HYUNDAI_IONIQ_6].get_non_essential_params(HYUNDAI.HYUNDAI_IONIQ_6)
    self.cp.notCar = True
    self.assertIsNone(self.row())

  def test_write_preserves_other_vehicle_and_manual_preferences(self):
    self.params.put_bool('AdvancedLateralTune', True, block=True)
    self.params.put_bool('ForceAutoTuneOff', True, block=True)
    first = self.row()
    request = row_change(first)
    self.assertEqual(request.value, 'Standard openpilot')
    self.assertTrue(self.owner.apply(request))
    raw = Path(self.params.get_param_path(DOCUMENT_KEY)).read_bytes()
    self.assertEqual(parse_document(raw)['vehicles']['HYUNDAI_IONIQ_6']['mode'], 'standard')
    self.assertEqual(read_selection(self.params, self.cp).mode, ControllerMode.STANDARD)
    self.cp = interfaces[TOYOTA.TOYOTA_COROLLA_TSS2].get_non_essential_params(TOYOTA.TOYOTA_COROLLA_TSS2)
    other = self.row()
    self.assertEqual(other.value, 'StarPilot vehicle tune')
    self.assertTrue(self.owner.apply(row_change(other)))
    after = parse_document(Path(self.params.get_param_path(DOCUMENT_KEY)).read_bytes())['vehicles']
    self.assertEqual(after['HYUNDAI_IONIQ_6']['mode'], 'standard')
    self.assertEqual(after['TOYOTA_COROLLA_TSS2']['mode'], 'standard')
    self.assertTrue(self.params.get_bool('AdvancedLateralTune'))
    self.assertTrue(self.params.get_bool('ForceAutoTuneOff'))

  def test_stale_document_cp_and_authority_rejected(self):
    row = self.row()
    request = row_change(row)
    self.cp.lateralTuning.torque.latAccelFactor *= 1.05
    self.assertFalse(self.owner.apply(request))
    self.cp = interfaces[HYUNDAI.HYUNDAI_IONIQ_6].get_non_essential_params(HYUNDAI.HYUNDAI_IONIQ_6)
    row = self.row()
    request = row_change(row)
    self.permitted = False
    self.assertFalse(self.owner.apply(request))
    self.permitted = True
    row = self.row()
    request = row_change(row)
    self.cp = interfaces[HYUNDAI.GENESIS_G70_2020].get_non_essential_params(HYUNDAI.GENESIS_G70_2020)
    self.assertFalse(self.owner.apply(request))
    self.cp = interfaces[HYUNDAI.HYUNDAI_IONIQ_6].get_non_essential_params(HYUNDAI.HYUNDAI_IONIQ_6)
    request = row_change(self.row())
    Path(self.params.get_param_path(DOCUMENT_KEY)).write_bytes(b'{"version":1,"vehicles":{}}')
    self.assertFalse(self.owner.apply(request))

  def test_starpilot_disables_learning_and_standard_requires_explicit_enable(self):
    self.params.put('SteerLatAccel', 3.3, block=True)
    self.params.put('SteerFriction', 0.12, block=True)
    self.assertFalse(self.row('ForceAutoTuneOff').available)
    self.assertEqual(self.row('ForceAutoTuneOff').value, 'Off')
    self.assertIn('contact StarPilot', self.row('ForceAutoTuneOff').reason)
    self.assertTrue(self.owner.apply(row_change(self.row())))  # Standard
    self.assertEqual(self.row('ForceAutoTuneOff').value, 'Off')
    self.assertTrue(self.owner.apply(row_change(self.row('ForceAutoTuneOff'))))
    self.assertEqual(self.row('ForceAutoTuneOff').value, 'On')
    self.assertTrue(self.owner.apply(row_change(self.row())))  # StarPilot
    self.assertTrue(self.params.get_bool('ForceAutoTuneOff'))
    self.assertFalse(self.params.get_bool('AdvancedLateralTune'))
    self.assertEqual(self.params.get('SteerLatAccel'), 3.3)
    self.assertEqual(self.params.get('SteerFriction'), 0.12)
    self.assertFalse(self.row('ForceAutoTuneOff').available)
    self.assertTrue(self.owner.apply(row_change(self.row())))  # Standard does not opt in to learning
    learning = self.row('ForceAutoTuneOff')
    self.assertTrue(learning.available)
    self.assertEqual(learning.value, 'Off')
    self.assertTrue(self.owner.apply(row_change(learning)))
    self.assertFalse(self.params.get_bool('ForceAutoTuneOff'))

  def test_learning_source_and_controller_changes_revoke_requests(self):
    self.assertTrue(self.owner.apply(row_change(self.row())))
    self.assertTrue(self.owner.apply(row_change(self.row('ForceAutoTuneOff'))))
    request = row_change(self.row())
    self.params.put_bool('ForceAutoTuneOff', True, block=True)
    self.assertFalse(self.owner.apply(request))
    learning = row_change(self.row('ForceAutoTuneOff'))
    self.assertTrue(self.owner.apply(row_change(self.row())))
    self.assertFalse(self.owner.apply(learning))
    Path(self.params.get_param_path('ForceAutoTuneOff')).write_bytes(b'invalid')
    self.assertFalse(self.row().available)
    self.assertFalse(self.row('ForceAutoTuneOff').available)

  def test_interrupted_starpilot_save_leaves_learning_off_without_changing_controller(self):
    self.assertTrue(self.owner.apply(row_change(self.row())))
    self.assertTrue(self.owner.apply(row_change(self.row('ForceAutoTuneOff'))))
    request = row_change(self.row())
    from openpilot.starpilot.ui import controller_feature
    commit = controller_feature.commit_exact

    def revoke_after_learning(**kwargs):
      result = commit(self.params, **kwargs)
      if kwargs['key'] == 'ForceAutoTuneOff':
        self.permitted = False
      return result

    with mock.patch.object(controller_feature, 'commit_exact', side_effect=lambda _params, **kwargs: revoke_after_learning(**kwargs)):
      self.assertFalse(self.owner.apply(request))
    self.assertTrue(self.params.get_bool('ForceAutoTuneOff'))
    self.assertEqual(read_selection(self.params, self.cp).mode, ControllerMode.STANDARD)

  def test_corrupt_or_unreadable_document_fails_closed_without_overwrite(self):
    path = Path(self.params.get_param_path(DOCUMENT_KEY))
    for raw in (b'not-json', b'{"version":1,"vehicles":{},"vehicles":{}}',
                b'{"version":2,"vehicles":{}}', b'x' * 4097):
      with self.subTest(raw=raw[:30]):
        path.write_bytes(raw)
        row = self.row()
        self.assertFalse(row.available)
        self.assertEqual(row.value, 'Invalid saved controller choice')
        self.assertFalse(self.owner.apply(FeatureSettingsRequest(DOCUMENT_KEY, raw, 'Standard openpilot',
                                                                 vehicle_fingerprint=str(self.cp.carFingerprint),
                                                                 capability=row.capability)))
        self.assertEqual(path.read_bytes(), raw)

  def test_galaxy_onroad_saved_choice_preview_confirm_and_revocation(self):
    current = SimpleNamespace(parked=False, cp=self.cp, raw=b'current-cp')
    context = SimpleNamespace(sample=lambda: AuthorityContext(current.parked, current.cp, current.raw))
    gateway = SettingsGateway(self.params, context, clock=lambda: 10)

    def preview():
      page = gateway.page('torque', 'session', b'generation')
      index = next(i for i, row in enumerate(page['rows']) if row['label'] == 'Torque controller')
      return gateway.preview(page['view'], index, 0, 'session', b'generation', value='Standard openpilot')

    intent = preview()
    self.assertIn('next drive', intent['question'])
    self.assertTrue(gateway.confirm(intent['intent'], 'session', b'generation'))
    self.assertEqual(read_selection(self.params, self.cp).mode, ControllerMode.STANDARD)
    self.assertFalse(current.parked)  # Saved preference did not require a Park state.

    stale = preview()
    path = Path(self.params.get_param_path(DOCUMENT_KEY))
    path.write_bytes(b'{"version":1,"vehicles":{}}')
    self.assertFalse(gateway.confirm(stale['intent'], 'session', b'generation'))

    fresh = preview()
    current.raw = b'changed-cp'
    with self.assertRaises(SettingsChanged):
      gateway.confirm(fresh['intent'], 'session', b'generation')
    current.raw = b'current-cp'

    expired = preview()
    with self.assertRaises(SettingsChanged):
      gateway.confirm(expired['intent'], 'session', b'other-generation')
    current.cp.lateralTuning.torque.latAccelFactor *= 1.05
    self.assertFalse(gateway.confirm(expired['intent'], 'session', b'generation'))


if __name__ == '__main__':
  unittest.main()
