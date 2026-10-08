import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpilot.common.params import Params
from openpilot.starpilot.galaxy.settings import LiveContextSource, PAGES, SettingsChanged, SettingsGateway
from openpilot.starpilot.vehicle_selection import encode


class TestOffroadConfigurationPages(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.params.put('LateralControllerSelection', {
      'vehicles': {'HYUNDAI_IONIQ_6': {'brand': 'hyundai', 'mode': 'starpilot'}}, 'version': 1,
    }, block=True)
    self.params.put('TorqueOverrideDocument', {'schemaVersion': 1, 'vehicles': {'HYUNDAI_IONIQ_6': {
      'basis': {'friction': 0.09000000357627869, 'latAccelFactor': 3.0, 'latAccelOffset': 0.0},
      'factor': {'customValue': 2.1, 'mode': 'source'}, 'friction': {'customValue': None, 'mode': 'source'},
    }}}, block=True)
    self.params.put_bool('OpenpilotEnabledToggle', True, block=True)
    self.params.put_bool('AlphaLongitudinalEnabled', True, block=True)
    self.params.put_bool('ForceAutoTuneOff', True, block=True)
    self.context = LiveContextSource(self.params)
    self.gateway = SettingsGateway(self.params, self.context)
    self.addCleanup(self.gateway.close)
    offroad = patch.object(self.context, 'offroad', return_value=True)
    self.offroad = offroad.start()
    self.addCleanup(offroad.stop)

  def page(self, name):
    return self.gateway.page(name, 'session', b'generation')

  @staticmethod
  def editable_inventory(page):
    return [(row['label'], row['available'], tuple(row['choices']), row['step'], row['minimum'], row['maximum'])
            for row in page['rows'] if row['choices'] or row['step']]

  def assert_no_car_cache(self):
    for key in ('CarParams', 'CarParamsPersistent', 'CarParamsCache'):
      self.assertFalse(Path(self.params.get_param_path(key)).exists(), key)

  def test_every_registered_page_matches_manual_configuration_without_cache(self):
    for alpha in (False, True):
      with self.subTest(alpha=alpha):
        self.params.put_bool('AlphaLongitudinalEnabled', alpha, block=True)
        self.params.put('VehicleSelection', json.loads(encode(None)), block=True)
        saved = {name: self.editable_inventory(self.page(name)) for name in sorted(PAGES)}
        self.params.put('VehicleSelection', json.loads(encode('HYUNDAI_IONIQ_6')), block=True)
        for name in sorted(PAGES):
          with self.subTest(page=name):
            self.assertEqual(saved[name], self.editable_inventory(self.page(name)))
        self.assert_no_car_cache()

  def test_stock_ioniq_configuration_can_save_slc_without_enabling_longitudinal(self):
    self.params.put_bool('AlphaLongitudinalEnabled', False, block=True)
    self.params.put('VehicleSelection', json.loads(encode('HYUNDAI_IONIQ_6')), block=True)
    context = self.context.sample()
    self.assertFalse(context.cp.openpilotLongitudinalControl)
    self.assertTrue(context.configuration_longitudinal)
    page = self.page('slc')
    index = next(i for i, row in enumerate(page['rows']) if row['label'] == 'Adopt fixed offsets')
    self.assertTrue(page['rows'][index]['available'])
    intent = self.gateway.preview(page['view'], index, 0, 'session', b'generation')
    self.assertTrue(self.gateway.confirm(intent['intent'], 'session', b'generation'))
    self.assertTrue(next(row for row in self.page('slc')['rows'] if row['label'] == 'Speed Limit Controller')['available'])
    self.assertFalse(self.params.get_bool('AlphaLongitudinalEnabled'))
    self.assertFalse(self.context.sample().cp.openpilotLongitudinalControl)
    self.assert_no_car_cache()

  def test_saved_and_manual_contexts_expose_expected_core_settings(self):
    offsets = self.page('slc')
    index = next(i for i, row in enumerate(offsets['rows']) if row['label'] == 'Adopt fixed offsets')
    intent = self.gateway.preview(offsets['view'], index, 0, 'session', b'generation')
    self.assertTrue(self.gateway.confirm(intent['intent'], 'session', b'generation'))
    expected = {
      'aol': ('Enable Always On Lateral', 'Brake pause below'),
      'conditional': ('Saved driving mode',),
      'conditional/cem': ('Speed threshold', 'Speed with lead', 'Stop lights'),
      'lane_change': ('Allow lane changes', 'Minimum lane-change speed', 'Automatic Lane Changes', 'Lane Change Speed'),
      'slc': ('Speed Limit Controller', 'Require confirmation', 'Previous accepted limit'),
      'profiles': ('Short press', 'Hold', 'Force Stop', 'Selected Acceleration Profile', 'Selected Deceleration Profile'),
      'torque': ('Steering Controller', 'Turn Assist', 'Lat Accel', 'Friction'),
      'wheel': ('Distance long press', 'MODE press', 'Star button'),
    }
    for selection in (None, 'HYUNDAI_IONIQ_6'):
      self.params.put('VehicleSelection', json.loads(encode(selection)), block=True)
      for name, labels in expected.items():
        with self.subTest(selection=selection, page=name):
          rows = {row['label']: row for row in self.page(name)['rows']}
          for label in labels:
            self.assertIn(label, rows)
            self.assertTrue(rows[label]['available'], (name, label))
            self.assertTrue(rows[label]['choices'] or rows[label]['step'], (name, label))
      self.assert_no_car_cache()

  def test_fixed_ioniq6_cruise_buttons_remain_outside_remapping_catalog(self):
    from openpilot.starpilot.car.hyundai.settings import configuration_wheel_policy
    cp = self.context.sample().cp
    policy = configuration_wheel_policy(cp)
    assert policy is not None
    self.assertTrue(policy.fixed_cruise_buttons)
    self.assertFalse(policy.lkas_button_supported)
    self.params.put('LKASButtonControl', 9, block=True)
    self.params.put('MainCruiseButtonControl', 10, block=True)
    labels = {row['label'] for row in self.page('wheel')['rows']}
    self.assertNotIn('LKAS press', labels)
    self.assertNotIn('Main cruise press', labels)
    self.assertIn('Distance long press', labels)
    self.assertEqual(self.params.get('LKASButtonControl'), 9)
    self.assertEqual(self.params.get('MainCruiseButtonControl'), 10)
    self.assert_no_car_cache()

  def test_every_advertised_default_is_accepted_by_its_owner(self):
    checked = 0
    for name in sorted(PAGES):
      count = len(self.page(name)['rows'])
      for index in range(count):
        page = self.page(name)
        if index >= len(page['rows']):
          break
        row = page['rows'][index]
        if not row['resetAvailable']:
          continue
        with self.subTest(page=name, label=row['label']):
          intent = self.gateway.preview(page['view'], index, 0, 'session', b'generation', reset_default=True)
          self.assertTrue(self.gateway.confirm(intent['intent'], 'session', b'generation'), (name, row['label'], row['defaultValue']))
          checked += 1
    self.assertGreater(checked, 100)
    self.assert_no_car_cache()

  def test_saved_configuration_cruise_force_stop_and_wheel_edits(self):
    selection = self.params.get('VehicleSelection')
    profiles = self.page('profiles')
    rows = {row['label']: row for row in profiles['rows']}
    for label in ('Short press', 'Hold', 'Force Stop'):
      self.assertTrue(rows[label]['available'], label)
    for label, key in (('Short press', 'CustomCruise'), ('Hold', 'CustomCruiseLong')):
      current = self.page('profiles')
      index = next(i for i, row in enumerate(current['rows']) if row['label'] == label)
      before = float(current['rows'][index]['value'])
      intent = self.gateway.preview(current['view'], index, 1, 'session', b'generation')
      self.assertTrue(self.gateway.confirm(intent['intent'], 'session', b'generation'))
      self.assertEqual(float(self.params.get(key)), before + 1.0)
    profiles = self.page('profiles')
    offset = next(row for row in profiles['rows'] if row['label'] == 'Stop Distance Adjustment')
    self.assertFalse(offset['available'])
    index = next(i for i, row in enumerate(profiles['rows']) if row['label'] == 'Force Stop')
    intent = self.gateway.preview(profiles['view'], index, 1, 'session', b'generation')
    self.assertTrue(self.gateway.confirm(intent['intent'], 'session', b'generation'))
    self.assertTrue(self.params.get_bool('ForceStops'))
    self.assertTrue(next(row for row in self.page('profiles')['rows'] if row['label'] == 'Stop Distance Adjustment')['available'])
    for label, key in (('Distance long press', 'LongDistanceButtonControl'), ('MODE press', 'ModeButtonControl'),
                       ('Star button', 'StarButtonControl')):
      wheel = self.page('wheel')
      index = next(i for i, row in enumerate(wheel['rows']) if row['label'] == label)
      self.assertTrue(wheel['rows'][index]['available'], label)
      before = self.params.get(key)
      intent = self.gateway.preview(wheel['view'], index, 1, 'session', b'generation')
      self.assertTrue(self.gateway.confirm(intent['intent'], 'session', b'generation'))
      self.assertNotEqual(self.params.get(key), before)
    self.assertEqual(self.params.get('VehicleSelection'), selection)
    self.assert_no_car_cache()

  def test_alpha_off_allows_saved_long_preferences_without_runtime_activation(self):
    self.params.put_bool('AlphaLongitudinalEnabled', False, block=True)
    rows = {row['label']: row for row in self.page('profiles')['rows']}
    for label in ('Short press', 'Hold', 'Force Stop'):
      self.assertTrue(rows[label]['available'], label)
    self.assertFalse(self.context.sample().cp.openpilotLongitudinalControl)
    self.assertFalse(self.params.get_bool('AlphaLongitudinalEnabled'))
    self.assert_no_car_cache()

  def test_saved_configuration_edit_is_revoked_by_onroad_or_selection_change(self):
    for change in ('onroad', 'selection'):
      with self.subTest(change=change):
        self.offroad.return_value = True
        self.params.put('VehicleSelection', json.loads(encode(None)), block=True)
        page = self.page('wheel')
        index = next(i for i, row in enumerate(page['rows']) if row['label'] == 'MODE press')
        before = self.params.get('ModeButtonControl')
        intent = self.gateway.preview(page['view'], index, 1, 'session', b'generation')
        if change == 'onroad':
          self.offroad.return_value = False
        else:
          self.params.put('VehicleSelection', json.loads(encode('CHEVROLET_BOLT_CC_2018_2021')), block=True)
        with self.assertRaises(SettingsChanged):
          self.gateway.confirm(intent['intent'], 'session', b'generation')
        self.assertEqual(self.params.get('ModeButtonControl'), before)
        self.assert_no_car_cache()
