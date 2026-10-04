from types import SimpleNamespace

from openpilot.selfdrive.controls.plannerd import traffic_observation


def test_current_decision_stamp_preserves_raw_provenance_and_denies_unknown_authority():
  verdict = SimpleNamespace(effective=True, requested=True, profile_mode=True, reason='active', source_mono_ns=1)
  observed = traffic_observation(verdict, model_ns=1_000_000_000)
  assert observed.value is True and observed.observed_mono_ns == 1_000_000_000
  assert verdict.source_mono_ns == 1
  for reason in ('authority_unavailable', 'can_unavailable', 'settings_unavailable'):
    verdict.effective, verdict.requested, verdict.profile_mode, verdict.reason = None, False, False, reason
    assert traffic_observation(verdict, model_ns=1_000_000_000) is None
  verdict.effective, verdict.requested, verdict.profile_mode, verdict.reason = None, True, None, 'authority_unavailable'
  assert traffic_observation(verdict, model_ns=1_000_000_000) is None
  assert traffic_observation(None, model_ns=1_000_000_000) is None
  assert traffic_observation(None, model_ns=0, owner_present=False) is None

  verdict.reason = 'unsupported_car'
  verdict.requested, verdict.profile_mode = False, False
  assert traffic_observation(verdict, model_ns=1_000_000_000).value is False
