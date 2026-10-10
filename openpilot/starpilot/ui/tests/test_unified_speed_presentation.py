"""UI decisions with deliberately conflicting selected/accepted source and units."""

from types import SimpleNamespace as N
import unittest
from openpilot.starpilot.ui import unified_speed_presentation as m


def state(**changes):
  obs = N(
    kind='valid',
    source='vision',
    speed_limit_mps=30,
    accepted_speed_limit_mps=20,
    accepted_source='dashboard',
    pending_speed_limit_mps=None,
    pending_source='none',
    offset_mps=2,
    effective_cluster_target_mps=22,
    action_enabled=True,
    limiting_max_set=True,
    driver_override_active=False,
  )
  st = N(
    speed_limit=obs, metric=True, appearance=N(hide_max_speed=False), cruise_kph=100, cruise_active=True, longitudinal_overridden=False, show_slc_offset=True
  )
  for key, value in changes.items():
    if hasattr(st, key):
      setattr(st, key, value)
    else:
      setattr(obs, key, value)
  return st


class PresentationTest(unittest.TestCase):
  def test_row_feedback_tracks_source_without_contradicting_rounded_values(self):
    for metric in (True, False):
      s = state(metric=metric, cruise_kph=79.2, accepted_adjusted_limit_mps=22)
      for target, active, max_status, limit_status in (
          (23, 'max', 'Using set speed', 'Above set speed'),
          (22.01, 'max', 'Using set speed', 'Matches set speed'),
          (22, 'shared', 'Matches speed limit', 'Matches set speed'),
          (21.99, 'slc', 'Your ceiling', 'Using speed limit')):
        with self.subTest(metric=metric, target=target):
          s.speed_limit.accepted_adjusted_limit_mps = target
          p = m.resolve_unified_speed(s)
          self.assertEqual((p.active_side, p.max_status, p.limit_status), (active, max_status, limit_status))
      s.appearance.hide_max_speed = True
      s.speed_limit.accepted_adjusted_limit_mps = 23
      self.assertEqual(m.resolve_unified_speed(s).limit_status, 'Using set speed')

  def test_row_feedback_preserves_override_and_inactive_states(self):
    for changes, max_status, limit_status in (
        ({'driver_override_active': True, 'override_basis': 'persistent'}, 'Using set speed', 'Overridden'),
        ({'driver_override_active': True, 'override_basis': 'pedal'}, 'Your ceiling', 'Using accelerator'),
        ({'longitudinal_overridden': True}, 'Your ceiling', 'Using accelerator'),
        ({'cruise_active': False}, 'Your ceiling', 'Cruise off'),
        ({'cruise_active': False, 'cruise_kph': None}, 'Not set', 'Cruise off'),
        ({'action_enabled': False}, 'Your ceiling', 'Display only'),
        ({'status': 'display_hold'}, 'Your ceiling', 'Unavailable'),
        ({'kind': 'stale'}, 'Your ceiling', 'Unavailable')):
      with self.subTest(changes=changes):
        p = m.resolve_unified_speed(state(**({'cruise_kph': 79.2} | changes)))
        self.assertEqual((p.max_status, p.limit_status), (max_status, limit_status))

  def test_reselected_vision_never_relabels_accepted_dashboard(self):
    p = m.resolve_unified_speed(state())
    self.assertEqual((p.posted_text, p.source, p.offset_text, p.mode, p.active_side), ('72', 'dashboard', '+7', 'split', 'slc'))

  def test_pending_preserves_accepted_value_and_source(self):
    s = state(pending_speed_limit_mps=25, pending_source='map')
    p = m.resolve_unified_speed(s)
    self.assertEqual((p.posted_text, p.limit_text, p.source, p.pending, p.proposal_text), ('72', '79', 'dashboard', True, '90'))
    s.appearance.hide_max_speed = True

  def test_equal_values_keep_both_roles(self):
    p = m.resolve_unified_speed(state(cruise_kph=79.2))
    self.assertEqual((p.mode, p.max_text, p.limit_text, p.active_side, p.status), ('split', '79', '79', 'shared', 'Matches set speed'))

  def test_limiting_role_uses_adjusted_target_instead_of_raw_publisher_flag(self):
    for cruise, flag, active, status in ((100, False, 'slc', 'Using speed limit'),
                                         (72, True, 'max', 'Using set speed'),
                                         (79.2, False, 'shared', 'Matches set speed')):
      with self.subTest(cruise=cruise):
        p = m.resolve_unified_speed(state(cruise_kph=cruise, accepted_adjusted_limit_mps=22,
                                           limiting_max_set=flag, pending_speed_limit_mps=30,
                                           pending_adjusted_limit_mps=32))
        self.assertEqual((p.active_side, p.status), (active, status))

  def test_shared_comparison_is_independent_of_units_and_tolerates_transport_noise(self):
    for metric in (False, True):
      p = m.resolve_unified_speed(state(metric=metric, cruise_kph=79.2,
                                        accepted_adjusted_limit_mps=22.000001))
      self.assertEqual((p.active_side, p.status), ('shared', 'Matches set speed'))

  def test_equal_rounded_numbers_are_not_necessarily_shared(self):
    for target, active in ((21.99, 'slc'), (22.01, 'max')):
      p = m.resolve_unified_speed(state(cruise_kph=79.2, accepted_adjusted_limit_mps=target))
      self.assertEqual((p.max_text, p.limit_text, p.active_side), ('79', '79', active))

  def test_equal_information_does_not_bypass_control_status(self):
    for changes, status in (({'cruise_active': False}, 'Cruise off'),
                            ({'action_enabled': False}, 'Display only'),
                            ({'longitudinal_overridden': True}, 'Using accelerator'),
                            ({'driver_override_active': True}, 'Override'),
                            ({'effective_cluster_target_mps': None}, 'Unavailable'),
                            ({'status': 'display_hold'}, 'Unavailable')):
      with self.subTest(changes=changes):
        p = m.resolve_unified_speed(state(cruise_kph=79.2, accepted_adjusted_limit_mps=22, **changes))
        self.assertEqual((p.active_side, p.status), ('none', status))

  def test_missing_max_preserves_publisher_limiting_evidence(self):
    p = m.resolve_unified_speed(state(cruise_kph=None))
    self.assertEqual((p.active_side, p.status), ('slc', 'Using speed limit'))
    p = m.resolve_unified_speed(state(cruise_kph=None, limiting_max_set=False))
    self.assertEqual((p.max_status, p.limit_status), ('Not set', 'Using set speed'))

  def test_set_speed_caps_posted_limit_plus_offset(self):
    for metric, factor in ((True, 3.6), (False, 2.2369362921)):
      with self.subTest(metric=metric):
        p = m.resolve_unified_speed(state(metric=metric, cruise_kph=40 / factor * 3.6,
                                          accepted_speed_limit_mps=40 / factor,
                                          accepted_adjusted_limit_mps=45 / factor,
                                          effective_cluster_target_mps=45 / factor,
                                          limiting_max_set=True))
        self.assertEqual((p.max_text, p.limit_text, p.posted_text, p.offset_text), ('40', '45', '40', '+5'))
        self.assertEqual((p.active_side, p.status), ('max', 'Using set speed'))

  def test_display_only_never_merges_or_claims_slc_control(self):
    p = m.resolve_unified_speed(state(cruise_kph=79.2, action_enabled=False))
    self.assertEqual((p.mode, p.active_side), ('split', 'none'))

  def test_overrides_clear_activity_without_removing_sign(self):
    for change in ({'driver_override_active': True}, {'longitudinal_overridden': True}):
      p = m.resolve_unified_speed(state(**change))
      self.assertEqual((p.active_side, p.posted_text), ('none', '72'))

  def test_stale_and_absent_cannot_retain_pending_or_accepted(self):
    for kind in ('unknown', 'stale', 'absent'):
      p = m.resolve_unified_speed(state(kind=kind, pending_speed_limit_mps=25))
      self.assertEqual((p.mode, p.posted_text, p.pending, p.source), ('split' if kind == 'stale' else 'max_only', '–', False, 'none'))

  def test_imperial_and_hidden_max(self):
    p = m.resolve_unified_speed(state(metric=False, cruise_kph=None))
    self.assertEqual((p.max_text, p.posted_text, p.offset_text, p.unit), ('–', '45', '+4', 'mph'))
    s = state()
    s.appearance.hide_max_speed = True
    self.assertEqual(m.resolve_unified_speed(s).mode, 'limit_only')
    s.speed_limit.kind = 'stale'
    self.assertEqual(m.resolve_unified_speed(s).mode, 'limit_only')

  def test_older_message_cannot_misattribute_different_accepted_source(self):
    p = m.resolve_unified_speed(state(accepted_source='none'))
    self.assertEqual(p.source, 'unknown')

  def test_hidden_offset_preference_applies_to_split_and_merged_cards(self):
    for cruise in (100, 79.2):
      p = m.resolve_unified_speed(state(cruise_kph=cruise, show_slc_offset=False))
      self.assertIsNone(p.offset_text)

  def test_same_speed_selected_provider_cannot_supply_missing_provenance(self):
    for change in ({'accepted_source': 'none', 'speed_limit_mps': 20}, {'accepted_source': 'none', 'pending_source': 'none', 'pending_speed_limit_mps': 30}):
      p = m.resolve_unified_speed(state(**change))
      self.assertEqual(p.source, 'unknown')

  def test_malformed_auxiliary_values_use_the_same_valid_sign_for_pulse(self):
    for invalid in (-2, 0, float("nan"), float("inf")):
      s = state(accepted_speed_limit_mps=invalid, pending_speed_limit_mps=invalid)
      self.assertEqual(m.displayed_limit_mps(s.speed_limit), 30)
      self.assertEqual(m.resolve_unified_speed(s).posted_text, '108')
    s = state(kind='stale')
    self.assertIsNone(m.displayed_limit_mps(s.speed_limit))

  def test_zero_offset_omitted_and_invalid_effective_does_not_merge(self):
    p = m.resolve_unified_speed(state(offset_mps=0, effective_cluster_target_mps=20))
    self.assertEqual((p.mode, p.offset_text), ('split', None))
  def test_information_does_not_grant_control_activity(self):
    p = m.resolve_unified_speed(state(accepted_adjusted_limit_mps=22, effective_cluster_target_mps=None))
    self.assertEqual((p.limit_text, p.active_side, p.status), ('79', 'none', 'Unavailable'))

  def test_display_only_uses_qualified_presentation_without_accepting_it(self):
    p = m.resolve_unified_speed(state(accepted_speed_limit_mps=None, effective_cluster_target_mps=None,
                                     presentation_adjusted_limit_mps=32, action_enabled=False))
    self.assertEqual((p.limit_text, p.status, p.active_side), ('115', 'Display only', 'none'))

  def test_override_basis_and_retention_are_explicit(self):
    for basis, expected in (('pedal', 'Using accelerator'), ('persistent', 'Set-speed override'), ('unknown', 'Override')):
      self.assertEqual(m.resolve_unified_speed(state(driver_override_active=True, override_basis=basis)).status, expected)
    self.assertIn('Override saved', m.resolve_unified_speed(state(cruise_active=False, retained_override=True)).status)

  def test_set_speed_override_selects_max_even_when_displayed_targets_match(self):
    factor = 2.2369362921
    for max_speed in (40, 45):
      for basis, active, status in (('persistent', 'max', 'Set-speed override'),
                                    ('pedal', 'none', 'Using accelerator'),
                                    ('unknown', 'none', 'Override')):
        with self.subTest(max_speed=max_speed, basis=basis):
          p = m.resolve_unified_speed(state(metric=False, cruise_kph=max_speed / factor * 3.6,
                                            accepted_speed_limit_mps=35 / factor,
                                            accepted_adjusted_limit_mps=40 / factor,
                                            effective_cluster_target_mps=40 / factor,
                                            driver_override_active=True, override_basis=basis))
          self.assertEqual((p.active_side, p.status), (active, status))
          self.assertEqual((p.limit_text, p.posted_text, p.offset_text), ('40', '35', '+5'))

  def test_set_speed_override_cannot_claim_max_without_control_evidence(self):
    for changes in ({'cruise_active': False}, {'cruise_kph': None},
                    {'effective_cluster_target_mps': None}, {'action_enabled': False},
                    {'status': 'display_hold'}, {'longitudinal_overridden': True}, {'kind': 'stale'}):
      with self.subTest(changes=changes):
        p = m.resolve_unified_speed(state(driver_override_active=True, override_basis='persistent', **changes))
        self.assertEqual(p.active_side, 'none')


if __name__ == '__main__':
  unittest.main()
