"""Display-only continuity across bounded transport gaps."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from openpilot.starpilot.ui.onroad_compact_widgets import CompactHudRenderer
from openpilot.starpilot.ui.onroad_state import ObservationKind, OnroadState, SpeedLimitObservation
from openpilot.starpilot.ui.shell import ShellMode
from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW, RuntimeSnapshotAdapter, ui_fake
from openpilot.starpilot.ui.unified_speed_presentation import resolve_unified_speed


def unknown_slc(session='uuid-text', *, pending=False):
  return NS(enabled=True, displayOnly=False, observationKind='unknown', source='none', status='unknown',
            sessionId=session, hasPending=pending)


def display_ui():
  ui = ui_fake()
  ui.sm.messages['slcState'].decisionId = 0
  return ui


def test_unknown_slc_keeps_only_display_sign_until_session_changes():
  ui = display_ui()
  adapter = RuntimeSnapshotAdapter(ui)
  valid = adapter.build(ShellMode.ONROAD, now_ns=NOW).onroad.speed_limit
  assert valid.kind == ObservationKind.VALID
  ui.sm.messages['slcState'] = unknown_slc()
  ui.sm.logMonoTime['slcState'] = NOW + 50_000_000
  held = adapter.build(ShellMode.ONROAD, now_ns=NOW + 50_000_000).onroad.speed_limit
  assert (held.kind, held.speed_limit_mps, held.source, held.status) == (
    ObservationKind.VALID, valid.speed_limit_mps, valid.source, 'display_hold')
  assert not held.action_enabled
  assert all(value is None for value in (held.session_id, held.decision_id, held.presentation_id,
                                         held.pending_speed_limit_mps, held.effective_cap_mps))
  # A long gap with no source information keeps the sign steady instead of flickering.
  ui.sm.logMonoTime['slcState'] = NOW + 60_000_000_000
  long_held = adapter.build(ShellMode.ONROAD, now_ns=NOW + 60_000_000_000).onroad.speed_limit
  assert (long_held.kind, long_held.speed_limit_mps, long_held.status) == (
    ObservationKind.VALID, valid.speed_limit_mps, 'display_hold')


@pytest.mark.parametrize('metric', [False, True])
@pytest.mark.parametrize('target_kind', ['accepted', 'effective', 'presentation'])
def test_unknown_gap_preserves_large_slc_number_offset_and_source(metric, target_kind):
  ui = display_ui()
  ui.is_metric = metric
  slc = ui.sm.messages['slcState']
  slc.speedLimit, slc.source = 30.0, 'vision'
  if target_kind != 'presentation':
    slc.hasAccepted, slc.acceptedSpeedLimit, slc.acceptedSource = True, 20.0, 'dashboard'
  if target_kind == 'accepted':
    slc.hasAcceptedAdjustedLimit, slc.acceptedAdjustedLimit = True, 22.0
  elif target_kind == 'effective':
    slc.hasEffectiveClusterTarget, slc.effectiveClusterTarget = True, 22.0
  else:
    slc.hasPresentationAdjustedLimit, slc.presentationAdjustedLimit = True, 32.0
  adapter = RuntimeSnapshotAdapter(ui)
  before_state = adapter.build(ShellMode.ONROAD, now_ns=NOW).onroad
  before = resolve_unified_speed(before_state)
  assert before.limit_text != '–'
  assert before.offset_text is not None
  ui.sm.messages['slcState'] = unknown_slc()
  for age in (50_000_000, 100_000_000, 150_000_000):
    ui.sm.logMonoTime['slcState'] = NOW + age
    held_state = adapter.build(ShellMode.ONROAD, now_ns=NOW + age).onroad
    held = resolve_unified_speed(held_state)
    assert (held.mode, held.posted_text, held.limit_text, held.offset_text, held.source) == (
      before.mode, before.posted_text, before.limit_text, before.offset_text, before.source)
    assert (held.active_side, held.status, held.pending) == ('none', 'Unavailable', False)
    obs = held_state.speed_limit
    assert not obs.action_enabled
    assert all(value is None for value in (obs.effective_cap_mps, obs.effective_cluster_target_mps,
                                           obs.accepted_speed_limit_mps, obs.session_id, obs.decision_id,
                                           obs.presentation_id, obs.pending_speed_limit_mps))
  # The hold does not expire on its own; only a new session or drive clears it.
  ui.sm.logMonoTime['slcState'] = NOW + 150_000_001
  still = resolve_unified_speed(adapter.build(ShellMode.ONROAD, now_ns=NOW + 150_000_001).onroad)
  assert (still.limit_text, still.posted_text) == (before.limit_text, before.posted_text)
  ui.sm.messages['slcState'] = slc
  ui.sm.logMonoTime['slcState'] = NOW + 160_000_000
  recovered = resolve_unified_speed(adapter.build(ShellMode.ONROAD, now_ns=NOW + 160_000_000).onroad)
  assert recovered == before


def test_slc_hold_rejects_pending_foreign_session_and_new_drive():
  for replacement in (unknown_slc(pending=True), unknown_slc(session='another')):
    ui = display_ui()
    adapter = RuntimeSnapshotAdapter(ui)
    adapter.build(ShellMode.ONROAD, now_ns=NOW)
    ui.sm.messages['slcState'] = replacement
    ui.sm.logMonoTime['slcState'] = NOW + 50_000_000
    assert adapter.build(ShellMode.ONROAD, now_ns=NOW + 50_000_000).onroad.speed_limit.kind == ObservationKind.STALE
  ui = display_ui()
  adapter = RuntimeSnapshotAdapter(ui)
  adapter.build(ShellMode.ONROAD, now_ns=NOW)
  ui.started_frame = 2
  ui.sm.messages['slcState'] = unknown_slc()
  ui.sm.logMonoTime['slcState'] = NOW + 50_000_000
  assert adapter.build(ShellMode.ONROAD, now_ns=NOW + 50_000_000).onroad.speed_limit.kind == ObservationKind.STALE
  ui = ui_fake()  # A live decision may seed the sign, but never survives as an action identity.
  adapter = RuntimeSnapshotAdapter(ui)
  adapter.build(ShellMode.ONROAD, now_ns=NOW)
  ui.sm.messages['slcState'] = unknown_slc()
  ui.sm.logMonoTime['slcState'] = NOW + 50_000_000
  held = adapter.build(ShellMode.ONROAD, now_ns=NOW + 50_000_000).onroad.speed_limit
  assert held.decision_id is None and held.pending_speed_limit_mps is None and not held.action_enabled


def test_compact_max_hides_during_gap_without_restarting_same_value_fade():
  renderer = CompactHudRenderer(Mock(), Path('/unused'))
  active = OnroadState(True, True, 20.0, 80.0, SpeedLimitObservation(), longitudinal_active=True)
  assert renderer._set_speed_opacity(active, 1_000_000_000) == 0.0
  assert renderer._set_speed_opacity(active, 1_020_000_000) > 0.0
  before = renderer._set_speed_alpha.x
  unavailable = replace(active, cruise_kph=None)
  assert renderer._set_speed_opacity(unavailable, 1_050_000_000) == 0.0
  assert renderer._set_speed_alpha.x == before
  assert renderer._set_speed_opacity(active, 1_080_000_000) > before
  renderer._set_speed_opacity(replace(active, cruise_kph=90.0), 1_100_000_000)
  assert renderer._set_speed_changed_ns == 1_100_000_000
  assert renderer._set_speed_opacity(unavailable, 1_300_000_000) == 0.0
  assert renderer._set_speed_alpha.x == 0.0


def test_compact_max_expires_once_and_short_gap_does_not_rearm_it():
  renderer = CompactHudRenderer(Mock(), Path('/unused'))
  active = OnroadState(True, True, 20.0, 80.0, SpeedLimitObservation(), longitudinal_active=True)
  for frame in range(200):
    renderer._set_speed_opacity(active, 1_000_000_000 + frame * 20_000_000)
  assert renderer._set_speed_alpha.x < .01
  renderer._set_speed_opacity(replace(active, cruise_kph=None), 5_000_000_000)
  assert renderer._set_speed_opacity(active, 5_040_000_000) < .01
  assert renderer._set_speed_changed_ns == 1_000_000_000
  renderer._set_speed_opacity(replace(active, cruise_kph=90.0), 5_060_000_000)
  assert renderer._set_speed_opacity(replace(active, cruise_kph=90.0), 5_080_000_000) > .01


def test_new_drive_rearms_max_without_an_intervening_render():
  renderer = CompactHudRenderer(Mock(), Path('/unused'))
  active = OnroadState(True, True, 20.0, 80.0, SpeedLimitObservation(), longitudinal_active=True, drive_frame=100)
  renderer._set_speed_opacity(active, 1_000_000_000)
  renderer._set_speed_opacity(active, 1_020_000_000)
  new_drive = replace(active, drive_frame=200)
  assert renderer._set_speed_opacity(new_drive, 9_000_000_000) == 0
  assert renderer._set_speed_changed_ns == 9_000_000_000
  assert renderer._set_speed_opacity(new_drive, 9_020_000_000) > 0


def test_sources_row_keeps_each_source_while_no_limit_is_known():
  readings = [NS(source='dashboard', enabled=True, observationKind='unknown', speedLimit=0.0),
              NS(source='map', enabled=True, observationKind='unknown', speedLimit=0.0)]
  # Held sign and a session with nothing to hold both keep the per-source rows up.
  for replacement in (unknown_slc(), unknown_slc(session='another')):
    ui = display_ui()
    adapter = RuntimeSnapshotAdapter(ui)
    adapter.build(ShellMode.ONROAD, now_ns=NOW)
    replacement.sourceReadings = readings
    ui.sm.messages['slcState'] = replacement
    ui.sm.logMonoTime['slcState'] = NOW + 50_000_000
    shown = adapter.build(ShellMode.ONROAD, now_ns=NOW + 50_000_000).onroad.speed_limit
    assert [(row.source, row.kind) for row in shown.source_readings] == [('dashboard', 'unknown'), ('map', 'unknown')]
