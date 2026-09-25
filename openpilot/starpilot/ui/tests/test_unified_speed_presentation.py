"""UI decisions with deliberately conflicting selected/accepted source and units."""
from types import SimpleNamespace as N
import unittest
from openpilot.starpilot.ui import unified_speed_presentation as m


def state(**changes):
  obs = N(kind='valid', source='vision', speed_limit_mps=30, accepted_speed_limit_mps=20,
          accepted_source='dashboard', pending_speed_limit_mps=None, pending_source='none',
          offset_mps=2, effective_cluster_target_mps=22, action_enabled=True,
          limiting_max_set=True, driver_override_active=False)
  st = N(speed_limit=obs, metric=True, appearance=N(hide_max_speed=False),
         cruise_kph=100, cruise_active=True, longitudinal_overridden=False, show_slc_offset=True)
  for key, value in changes.items():
    if hasattr(st, key): setattr(st, key, value)
    else: setattr(obs, key, value)
  return st


class PresentationTest(unittest.TestCase):
  def test_reselected_vision_never_relabels_accepted_dashboard(self):
    p=m.resolve_unified_speed(state())
    self.assertEqual((p.posted_text,p.source,p.offset_text,p.mode,p.active_side),('72','dashboard','+7','split','slc'))

  def test_pending_is_its_own_source_and_hides_accepted_offset(self):
    s=state(pending_speed_limit_mps=25,pending_source='map')
    p=m.resolve_unified_speed(s)
    self.assertEqual((p.posted_text,p.source,p.pending,p.offset_text,p.mode),('90','map',True,None,'split'))
    self.assertEqual(m.large_limit_bounds(s),(88,271,264,486))
    s.appearance.hide_max_speed=True
    self.assertEqual(m.large_limit_bounds(s),(88,75,264,290))

  def test_merge_compares_cluster_target_not_raw_cap_or_posted_sign(self):
    s=state(cruise_kph=79.2)
    s.speed_limit.effective_cap_mps=19 # deliberately different raw coordinate
    p=m.resolve_unified_speed(s)
    self.assertEqual((p.mode,p.max_text,p.posted_text,p.active_side),('merged','79','72','shared'))

  def test_display_only_never_merges_or_claims_slc_control(self):
    p=m.resolve_unified_speed(state(cruise_kph=79.2,action_enabled=False))
    self.assertEqual((p.mode,p.active_side),('split','max'))

  def test_overrides_clear_activity_without_removing_sign(self):
    for change in ({'driver_override_active':True},{'longitudinal_overridden':True}):
      p=m.resolve_unified_speed(state(**change))
      self.assertEqual((p.active_side,p.posted_text),('none','72'))

  def test_stale_and_absent_cannot_retain_pending_or_accepted(self):
    for kind in ('unknown','stale','absent'):
      p=m.resolve_unified_speed(state(kind=kind,pending_speed_limit_mps=25))
      self.assertEqual((p.mode,p.posted_text,p.pending,p.source),('max_only','–',False,'none'))

  def test_imperial_and_hidden_max(self):
    p=m.resolve_unified_speed(state(metric=False,cruise_kph=None))
    self.assertEqual((p.max_text,p.posted_text,p.offset_text,p.unit),('–','45','+4','mph'))
    s=state();s.appearance.hide_max_speed=True
    self.assertEqual(m.resolve_unified_speed(s).mode,'limit_only')
    s.speed_limit.kind='stale'
    self.assertEqual(m.resolve_unified_speed(s).mode,'hidden')

  def test_older_message_cannot_misattribute_different_accepted_source(self):
    p=m.resolve_unified_speed(state(accepted_source='none'))
    self.assertEqual(p.source,'unknown')

  def test_hidden_offset_preference_applies_to_split_and_merged_cards(self):
    for cruise in (100,79.2):
      p=m.resolve_unified_speed(state(cruise_kph=cruise,show_slc_offset=False))
      self.assertIsNone(p.offset_text)

  def test_same_speed_selected_provider_cannot_supply_missing_provenance(self):
    for change in ({'accepted_source':'none','speed_limit_mps':20},
                   {'pending_source':'none','pending_speed_limit_mps':30}):
      p=m.resolve_unified_speed(state(**change))
      self.assertEqual(p.source,'unknown')

  def test_malformed_auxiliary_values_use_the_same_valid_sign_for_pulse(self):
    for invalid in (-2, 0, float("nan"), float("inf")):
      s=state(accepted_speed_limit_mps=invalid,pending_speed_limit_mps=invalid)
      self.assertEqual(m.displayed_limit_mps(s.speed_limit),30)
      self.assertEqual(m.resolve_unified_speed(s).posted_text,'108')
    s=state(kind='stale')
    self.assertIsNone(m.displayed_limit_mps(s.speed_limit))

  def test_zero_offset_omitted_and_invalid_effective_does_not_merge(self):
    p=m.resolve_unified_speed(state(offset_mps=0,effective_cluster_target_mps=float('nan')))
    self.assertEqual((p.mode,p.offset_text),('split',None))


if __name__=='__main__': unittest.main()
