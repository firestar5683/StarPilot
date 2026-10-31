"""Pending choices are source independent; selected-speed commands are not."""

import math

import pytest

from openpilot.cereal import messaging
from openpilot.selfdrive.car.cruise import SlcPendingConfirmation
from openpilot.starpilot.speed_limits import physical_actions
from openpilot.starpilot.speed_limits.selection import Source
from openpilot.starpilot.speed_limits.tests.test_runtime_replay import ReplaySM


NOW = 2_000_000_000


@pytest.fixture
def sm():
  state = messaging.new_message('slcState').slcState
  state.enabled, state.observationKind, state.source = True, 'valid', 'map'
  state.sessionId, state.frameMonoTime = 'drive', NOW
  state.hasPending, state.pendingSpeedLimit, state.speedLimit = True, 25.0, 25.0
  state.decisionId, state.presentationId = 1, 2
  return ReplaySM({'slcState': state}, NOW)


@pytest.mark.parametrize('source', tuple(Source))
def test_confirm_any_source_without_dashboard_evidence(sm, source):
  sm['slcState'].source = source.value
  assert physical_actions.pending_confirmation(sm, NOW, long_active=True) == SlcPendingConfirmation('drive', 1, 2)
  # A pending choice alone must never qualify a selected-speed command.
  current = physical_actions.state_current(sm, None, 'card', NOW)
  assert (current is not None) == (source is not Source.DASHBOARD)


def test_retained_choice_still_consumes_a_press_as_its_published_deadline_passes(sm):
  state = sm['slcState']
  state.observationKind, state.source, state.pendingSource = 'unknown', 'none', 'map'
  state.presentationId, state.pendingSinceMonoTime = 0, NOW
  published = NOW + 9_990_000_000
  state.frameMonoTime = sm.logMonoTime['slcState'] = published
  # The fresh displayed frame still has the choice; a late press must not adjust SET.
  assert physical_actions.pending_confirmation(sm, published + 20_000_000, long_active=True) is not None
  assert physical_actions.pending_confirmation(sm, published + physical_actions.STATE_MAX_AGE_NS + 1, long_active=True) is None
  assert physical_actions.state_current(sm, None, 'card', published) is None


@pytest.mark.parametrize('field,value', [
  ('enabled', False), ('displayOnly', True), ('observationKind', 'unknown'), ('observationKind', 'absent'),
  ('observationKind', 'stale'), ('source', 'none'), ('source', ''), ('source', 'unsupported'), ('sessionId', ''),
  ('frameMonoTime', 0), ('frameMonoTime', NOW + 1), ('frameMonoTime', NOW - physical_actions.STATE_MAX_AGE_NS - 1),
  ('hasPending', False), ('decisionId', 0), ('presentationId', 0), ('pendingSpeedLimit', 0.0),
  ('pendingSpeedLimit', math.nan), ('pendingSpeedLimit', math.inf), ('pendingSpeedLimit', 26.0), ('speedLimit', math.nan),
])
def test_reject_invalid_or_unavailable_pending_decision(sm, field, value):
  setattr(sm['slcState'], field, value)
  assert physical_actions.pending_confirmation(sm, NOW, long_active=True) is None


@pytest.mark.parametrize('valid,alive,stamp', [
  (False, True, NOW), (True, False, NOW), (True, True, 0), (True, True, NOW + 1),
  (True, True, NOW - physical_actions.STATE_MAX_AGE_NS - 1),
])
def test_reject_invalid_or_stale_transport(sm, valid, alive, stamp):
  sm.valid['slcState'], sm.alive['slcState'], sm.logMonoTime['slcState'] = valid, alive, stamp
  assert physical_actions.pending_confirmation(sm, NOW, long_active=True) is None


@pytest.mark.parametrize('long_active,after_ns', [(False, 0), (True, NOW)])
def test_preserve_authority_and_configuration_barriers(sm, long_active, after_ns):
  assert physical_actions.pending_confirmation(sm, NOW, long_active=long_active, after_ns=after_ns) is None


def test_fresh_post_configuration_decision_qualifies(sm):
  assert physical_actions.pending_confirmation(sm, NOW, long_active=True, after_ns=NOW - 1) is not None


@pytest.mark.parametrize('field,value', [
  ('enabled', False), ('displayOnly', True), ('observationKind', 'stale'), ('source', 'online'),
  ('presentationId', 0), ('frameMonoTime', NOW - physical_actions.STATE_MAX_AGE_NS - 1),
  ('hasPresentationAdjustedLimit', False), ('presentationAdjustedLimit', 0.),
  ('presentationAdjustedLimit', math.nan), ('presentationAdjustedLimit', math.inf),
  ('presentationAdjustedLimit', 146 / 3.6), ('presentationAdjustedLimit', 7 / 3.6),
])
def test_engagement_rejects_unqualified_current_target(sm, field, value):
  sm['slcState'].hasPresentationAdjustedLimit, sm['slcState'].presentationAdjustedLimit = True, 25.
  setattr(sm['slcState'], field, value)
  assert physical_actions.engagement_state(sm, None, 'card', NOW) is None


@pytest.mark.parametrize('target', [8 / 3.6, 145 / 3.6])
def test_engagement_accepts_float32_cruise_boundaries(sm, target):
  sm['slcState'].hasPresentationAdjustedLimit, sm['slcState'].presentationAdjustedLimit = True, target
  assert physical_actions.engagement_state(sm, None, 'card', NOW) is not None
