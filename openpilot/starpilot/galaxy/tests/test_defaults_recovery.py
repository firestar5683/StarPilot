from dataclasses import replace
from unittest import TestCase
from openpilot.starpilot.galaxy.defaults_recovery import DefaultsRecovery
from openpilot.starpilot.galaxy.settings import SettingsChanged
from openpilot.starpilot.galaxy.tests import test_settings as fixtures


class TestCanonicalRecovery(TestCase):
  def setUp(self):
    fixtures.SettingsGatewayTest.setUp(self)
    from opendbc.car.car_helpers import interfaces
    from opendbc.car.toyota.values import CAR
    cp = interfaces[CAR.TOYOTA_COROLLA_TSS2].get_non_essential_params(CAR.TOYOTA_COROLLA_TSS2)
    cp.openpilotLongitudinalControl = True
    cp.pcmCruise = False
    self.context.value = replace(self.context.value, cp=cp)


  def recovery(self):
    return DefaultsRecovery(self.gateway)

  def test_real_owner_defaults_and_selected_reset_preserve_runtime_state(self):
    self.params.put_bool('ShowBrakeStatus', True, block=True)
    self.params.put_bool('PedalsOnUI', True, block=True)
    self.params.put_bool('StockConfidenceBallWidget', True, block=True)
    self.params.put_bool('IsOffroad', True, block=True)
    recovery = self.recovery()
    view = recovery.snapshot(self.session, self.generation)
    selected = [row['id'] for row in view['rows'] if row['label'] == 'Wheel brake and acceleration colors']
    self.assertEqual(len(selected), 1)
    row = next(row for row in view['rows'] if row['id'] == selected[0])
    self.assertEqual(row['default'], 'Off')
    self.assertNotIn('IsOffroad', [row['label'] for row in view['rows']])
    pending = recovery.preview(view['view'], selected, self.session, self.generation)
    self.assertTrue(self.params.get_bool('ShowBrakeStatus'))
    result = recovery.confirm(pending['intent'], self.session, self.generation)
    self.assertTrue(result['saved'])
    self.assertFalse(self.params.get_bool('ShowBrakeStatus'))
    self.assertFalse(self.params.get_bool('PedalsOnUI'))
    self.assertTrue(self.params.get_bool('StockConfidenceBallWidget'))
    self.assertTrue(self.params.get_bool('IsOffroad'))
    refreshed = recovery.snapshot(self.session, self.generation)
    self.assertNotIn(row['label'], [r['label'] for r in refreshed['rows']])

  def test_confirmation_rechecks_real_saved_sources_before_any_reset(self):
    self.params.put_bool('ShowBrakeStatus', True, block=True)
    recovery = self.recovery()
    view = recovery.snapshot(self.session, self.generation)
    selected = [row['id'] for row in view['rows'] if row['label'] == 'Wheel brake and acceleration colors']
    pending = recovery.preview(view['view'], selected, self.session, self.generation)
    self.params.put_bool('PedalsOnUI', True, block=True)
    with self.assertRaises(SettingsChanged):
      recovery.confirm(pending['intent'], self.session, self.generation)
    self.assertTrue(self.params.get_bool('ShowBrakeStatus'))

  def test_selected_and_all_reset_use_the_same_owner_rows(self):
    self.params.put_bool('ShowBrakeStatus', True, block=True)
    self.params.put_bool('StockConfidenceBallWidget', True, block=True)
    recovery = self.recovery()
    view = recovery.snapshot(self.session, self.generation)
    pending = recovery.preview(view['view'], [r['id'] for r in view['rows']], self.session, self.generation)
    self.assertTrue(recovery.confirm(pending['intent'], self.session, self.generation)['saved'])
    self.assertEqual(recovery.snapshot(self.session, self.generation)['count'], 0)

  def test_disabled_master_children_remain_visible_and_reset_without_enabling_master(self):
    self.params.put_bool('SLCConfirmation', False, block=True)
    self.params.put_bool('SLCConfirmationLower', True, block=True)
    self.params.put_bool('SLCConfirmationHigher', True, block=True)
    recovery = self.recovery()
    view = recovery.snapshot(self.session, self.generation)
    children = [row for row in view['rows'] if row['label'] in ('Confirm lower limits', 'Confirm higher limits')]
    self.assertEqual(len(children), 2)
    self.assertTrue(all(not row['available'] for row in children))
    pending = recovery.preview(view['view'], [row['id'] for row in children], self.session, self.generation)
    self.assertTrue(recovery.confirm(pending['intent'], self.session, self.generation)['saved'])
    self.assertFalse(self.params.get_bool('SLCConfirmation'))
    self.assertFalse(self.params.get_bool('SLCConfirmationLower'))
    self.assertFalse(self.params.get_bool('SLCConfirmationHigher'))

  def test_reset_all_master_and_children_does_not_leave_hidden_customization(self):
    for key in ('SLCConfirmation', 'SLCConfirmationLower', 'SLCConfirmationHigher'):
      self.params.put_bool(key, True, block=True)
    recovery = self.recovery()
    view = recovery.snapshot(self.session, self.generation)
    selected = [row['id'] for row in view['rows'] if row['label'] in
                ('Require confirmation', 'Confirm lower limits', 'Confirm higher limits')]
    self.assertEqual(len(selected), 3)
    pending = recovery.preview(view['view'], selected, self.session, self.generation)
    self.assertTrue(recovery.confirm(pending['intent'], self.session, self.generation)['saved'])
    for key in ('SLCConfirmation', 'SLCConfirmationLower', 'SLCConfirmationHigher'):
      self.assertFalse(self.params.get_bool(key))

  def test_unsupported_rows_remain_visible_but_cannot_block_available_reset_all(self):
    from dataclasses import replace
    self.params.put_bool('SLCConfirmation', True, block=True)
    self.params.put_bool('ShowBrakeStatus', True, block=True)
    self.context.value = replace(self.context.value, cp=None, cp_raw=None)
    recovery = self.recovery()
    view = recovery.snapshot(self.session, self.generation)
    unsupported = next(row for row in view['rows'] if row['label'] == 'Require confirmation')
    self.assertFalse(unsupported['resetAvailable'])
    with self.assertRaises(SettingsChanged):
      recovery.preview(view['view'], [unsupported['id']], self.session, self.generation)
    selected = [row['id'] for row in view['rows'] if row['resetAvailable']]
    self.assertTrue(selected)
    pending = recovery.preview(view['view'], selected, self.session, self.generation)
    self.assertTrue(recovery.confirm(pending['intent'], self.session, self.generation)['saved'])
    self.assertTrue(self.params.get_bool('SLCConfirmation'))
    self.assertFalse(self.params.get_bool('ShowBrakeStatus'))

  def test_other_canonical_inactive_children_reset_without_turning_their_masters_on(self):
    self.params.put_bool('LaneCentering', False, block=True)
    self.params.put_bool('LaneCenteringPauseOnSignal', False, block=True)
    self.params.put_bool('ForceStops', False, block=True)
    self.params.put('ForceStopDistanceOffset', 5, block=True)
    recovery = self.recovery()
    view = recovery.snapshot(self.session, self.generation)
    selected = [row['id'] for row in view['rows'] if row['label'] in ('Pause on signal', 'Stop Distance Adjustment')]
    self.assertEqual(len(selected), 2)
    self.assertTrue(all(row['resetAvailable'] for row in view['rows'] if row['id'] in selected))
    pending = recovery.preview(view['view'], selected, self.session, self.generation)
    self.assertTrue(recovery.confirm(pending['intent'], self.session, self.generation)['saved'])
    self.assertFalse(self.params.get_bool('LaneCentering'))
    self.assertTrue(self.params.get_bool('LaneCenteringPauseOnSignal'))
    self.assertFalse(self.params.get_bool('ForceStops'))
    self.assertEqual(self.params.get('ForceStopDistanceOffset'), 0)
