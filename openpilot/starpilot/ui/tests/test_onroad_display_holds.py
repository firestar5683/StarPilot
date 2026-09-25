"""Display-only continuity across bounded transport gaps."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock

from openpilot.starpilot.ui.onroad_compact_widgets import CompactHudRenderer
from openpilot.starpilot.ui.onroad_state import ObservationKind, OnroadState, SpeedLimitObservation
from openpilot.starpilot.ui.shell import ShellMode
from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW, RuntimeSnapshotAdapter, ui_fake


def unknown_slc(session='uuid-text', *, pending=False):
  return NS(enabled=True, displayOnly=False, observationKind='unknown', source='none', status='unknown',
            sessionId=session, hasPending=pending)


def display_ui():
  ui = ui_fake()
  ui.sm.messages['slcState'].decisionId = 0
  return ui


def test_one_frame_unknown_slc_keeps_only_display_sign_and_expires():
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
  ui.sm.logMonoTime['slcState'] = NOW + 151_000_000
  assert adapter.build(ShellMode.ONROAD, now_ns=NOW + 151_000_000).onroad.speed_limit.kind == ObservationKind.UNKNOWN


def test_slc_hold_rejects_pending_foreign_session_and_new_drive():
  for replacement in (unknown_slc(pending=True), unknown_slc(session='another')):
    ui = display_ui()
    adapter = RuntimeSnapshotAdapter(ui)
    adapter.build(ShellMode.ONROAD, now_ns=NOW)
    ui.sm.messages['slcState'] = replacement
    ui.sm.logMonoTime['slcState'] = NOW + 50_000_000
    assert adapter.build(ShellMode.ONROAD, now_ns=NOW + 50_000_000).onroad.speed_limit.kind == ObservationKind.UNKNOWN
  ui = display_ui()
  adapter = RuntimeSnapshotAdapter(ui)
  adapter.build(ShellMode.ONROAD, now_ns=NOW)
  ui.started_frame = 2
  ui.sm.messages['slcState'] = unknown_slc()
  ui.sm.logMonoTime['slcState'] = NOW + 50_000_000
  assert adapter.build(ShellMode.ONROAD, now_ns=NOW + 50_000_000).onroad.speed_limit.kind == ObservationKind.UNKNOWN
  ui = ui_fake()  # A live decision must not be retained as a display-only sign.
  adapter = RuntimeSnapshotAdapter(ui)
  adapter.build(ShellMode.ONROAD, now_ns=NOW)
  ui.sm.messages['slcState'] = unknown_slc()
  ui.sm.logMonoTime['slcState'] = NOW + 50_000_000
  assert adapter.build(ShellMode.ONROAD, now_ns=NOW + 50_000_000).onroad.speed_limit.kind == ObservationKind.UNKNOWN


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
