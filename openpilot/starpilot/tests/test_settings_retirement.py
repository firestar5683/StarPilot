import unittest
import tempfile
import json
from openpilot.starpilot.lateral.tests.test_inferred_torque_overrides import SavedParams
from openpilot.starpilot.settings_retirement import retire_settings, PROFILE_FLAGS
from openpilot.starpilot.longitudinal.profile_document import default_personality_profiles, profile_document, migrate_profile_document


class TestSettingsRetirement(unittest.TestCase):
  def setUp(self):
    self.directory = tempfile.TemporaryDirectory()
    self.addCleanup(self.directory.cleanup)
    self.params = SavedParams(self.directory.name)
  def test_inactive_cruise_features_do_not_become_enabled(self):
    self.params.put_bool('QOLLongitudinal', False)
    self.params.put_bool('ForceStops', True)
    self.params.put_bool('ReverseCruise', True)
    self.params.put('CustomCruise', 7.0)
    retire_settings(self.params)
    self.assertEqual(self.params.get('ForceStops'), b'0')
    self.assertEqual(self.params.get('ReverseCruise'), b'0')
    self.assertEqual(self.params.get('CustomCruise'), b'1.0')
    self.assertIsNone(self.params.get('QOLLongitudinal'))
    self.params.put_bool('ForceStops', True)
    retire_settings(self.params)
    self.assertEqual(self.params.get('ForceStops'), b'1')
  def test_active_cruise_values_and_steering_values_survive(self):
    self.params.put_bool('QOLLongitudinal', True)
    self.params.put_bool('ForceStops', True)
    self.params.put('CustomCruise', 7.0)
    self.params.put('SteerLatAccel', 3.2)
    self.params.put_bool('AdvancedLateralTune', False)
    retire_settings(self.params)
    self.assertEqual(self.params.get('ForceStops'), b'1')
    self.assertEqual(self.params.get('CustomCruise'), b'7.0')
    self.assertEqual(self.params.get('SteerLatAccel'), b'3.2')
    self.assertIsNone(self.params.get('AdvancedLateralTune'))
  def test_inactive_legacy_curve_does_not_activate(self):
    profiles = default_personality_profiles(False)
    profiles['standard']['following'] = {'preset': 'custom', 'curve': [2.0]*10}
    profiles['standard']['acceleration'] = {'preset': 'sport', 'curve': [], 'legacyActivation': True}
    profiles['relaxed']['following'] = {'preset': 'custom', 'curve': [2.5]*10}
    document = profile_document(profiles, enabled=True)
    self.params.put('LongitudinalPersonalityProfiles', document)
    self.params.put_bool('StandardPersonalityProfile', False)
    self.params.put_bool('RelaxedPersonalityProfile', True)
    retire_settings(self.params)
    result = migrate_profile_document(self.params.get('LongitudinalPersonalityProfiles'))
    self.assertIsNotNone(result)
    self.assertEqual(result['profiles']['standard']['following']['preset'], 'dom_default')
    self.assertEqual(result['profiles']['standard']['acceleration']['preset'], 'selected_profile')
    self.assertEqual(result['profiles']['relaxed']['following']['curve'], [2.5]*10)
    self.assertTrue(all(self.params.get(key) is None for key in PROFILE_FLAGS))
    before = self.params.get('LongitudinalPersonalityProfiles')
    retire_settings(self.params)
    self.assertEqual(self.params.get('LongitudinalPersonalityProfiles'), before)
  def test_invalid_documents_retained_and_unconfigured_allowed(self):
    self.params.put_bool('StandardPersonalityProfile', False)
    self.params.put('LongitudinalPersonalityProfiles', 'bad')
    self.assertTrue(retire_settings(self.params))
    self.assertEqual(self.params.get('LongitudinalPersonalityProfiles'), b'bad')
    self.assertIsNone(self.params.get('StandardPersonalityProfile'))
    self.params.put('LongitudinalPersonalityProfiles', {})
    retire_settings(self.params)
    self.assertIsNone(self.params.get('StandardPersonalityProfile'))
  def test_unsafe_switch_and_invalid_evidence_are_bounded_and_preserved(self):
    self.params.put('RetiredSettingsEvidence', 'not-json')
    self.params.put('QOLLongitudinal', 'x' * 100000)
    self.params.put_bool('ForceStops', True)
    issues = retire_settings(self.params)
    self.assertTrue(any('existing evidence retained' in issue for issue in issues))
    self.assertEqual(self.params.get('RetiredSettingsEvidence'), b'not-json')
    self.assertEqual(self.params.get('ForceStops'), b'0')
    self.assertIsNone(self.params.get('QOLLongitudinal'))

  def test_absent_parent_is_off_only_on_first_reconciliation(self):
    self.params.put_bool('ForceStops', True)
    self.params.put_bool('ReverseCruise', True)
    profiles = default_personality_profiles(False)
    profiles['standard']['following'] = {'preset': 'custom', 'curve': [2.0]*10}
    self.params.put('LongitudinalPersonalityProfiles', profile_document(profiles, enabled=True))
    retire_settings(self.params)
    self.assertEqual(self.params.get('ForceStops'), b'0')
    self.assertEqual(self.params.get('ReverseCruise'), b'0')
    result = migrate_profile_document(self.params.get('LongitudinalPersonalityProfiles'))
    self.assertEqual(result['profiles']['standard']['following']['preset'], 'dom_default')
    self.params.put_bool('ForceStops', True)
    self.params.put_bool('ReverseCruise', True)
    self.params.put('LongitudinalPersonalityProfiles', profile_document(profiles, enabled=True))
    retire_settings(self.params)
    self.assertEqual(self.params.get('ForceStops'), b'1')
    self.assertEqual(self.params.get('ReverseCruise'), b'1')
    result = migrate_profile_document(self.params.get('LongitudinalPersonalityProfiles'))
    self.assertEqual(result['profiles']['standard']['following']['curve'], [2.0]*10)

  def test_fresh_namespace_completes_and_preserves_later_choice(self):
    retire_settings(self.params)
    state = json.loads(self.params.get('SettingsRetirementState'))
    self.assertEqual(set(state['completed']), {'cruise', 'profiles'})
    self.params.put_bool('ForceStops', True)
    retire_settings(self.params)
    self.assertEqual(self.params.get('ForceStops'), b'1')


if __name__ == '__main__':
  unittest.main()
