"""Saved retention policy through Maps, the native planner, and the driving UI."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib import longitudinal_planner as native
from openpilot.selfdrive.controls.plannerd import SavedSlcLifecycle
from openpilot.starpilot.speed_limits import offset_document as od
from openpilot.starpilot.speed_limits import physical_actions
from openpilot.starpilot.speed_limits.runtime import Action, Runtime
from openpilot.starpilot.speed_limits.runtime_settings import read_params
from openpilot.starpilot.speed_limits.tests.test_maps_runtime import BOOT, packet
from openpilot.starpilot.ui.onroad_compact_widgets import CompactHudRenderer
from openpilot.starpilot.ui.onroad_state import AlertSize, ObservationKind, OnroadInput, SlcActionKind, slc_controls
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.shell import ShellMode
from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW, RuntimeSnapshotAdapter, ui_fake
from openpilot.starpilot.ui.tests.test_slc_ui_runtime import publish_request, replay_inputs
from openpilot.starpilot.ui.unified_speed_presentation import resolve_unified_speed

MPH = .44704


@pytest.mark.parametrize('document', [False, True])
@pytest.mark.parametrize('offset,delta', [(-25, 0), (-30, 0), (-24, 2), (-5, 0)])
def test_negative_offsets_cannot_remove_the_native_slc_ceiling(tmp_path, document, offset, delta):
  drive = RetentionDrive(tmp_path)
  params = Params(str(tmp_path))
  if document:
    params.put('SLCOffsetSchedule', od.to_value(od.adopt_legacy(False, (offset, 0, 0, 0, 0, 0, 0))), block=True)
  else:
    params.put('Offset1', float(offset), block=True)
  drive.runtime = Runtime(read_params(params))
  drive.sm['carState'].vEgoCluster += delta
  output, _, target = drive.step(0, limit=25)
  adjusted = 20 * MPH if offset == -5 else 25 * MPH
  assert not output.result.errors
  assert output.message.slcState.hasCeiling
  assert output.message.slcState.acceptedAdjustedLimit == pytest.approx(adjusted)
  assert output.message.slcState.effectiveClusterTarget == pytest.approx(adjusted)
  assert target == pytest.approx((adjusted - delta) / MPH)


@pytest.mark.parametrize('confirm', [False, True])
@pytest.mark.parametrize('source_gap', [False, True])
def test_live_offset_edits_keep_the_accepted_limit_and_native_ceiling(tmp_path, confirm, source_gap):
  drive = RetentionDrive(tmp_path, confirm=confirm)
  params = Params(str(tmp_path))
  lifecycle = SavedSlcLifecycle(params, drive.cp, {'SLC_REPLAY_RUNTIME': '1'})
  runtime, _ = lifecycle.refresh(NOW)
  assert runtime is not None
  drive.runtime = runtime
  first, _, _ = drive.step(0)
  output, _, _ = drive.step(50, request=Action(runtime.session_id, 1, first.message.slcState.decisionId, 0, 'accept') if confirm else None)
  accepted = output.result.state.acceptance.accepted
  session = runtime.session_id
  for milliseconds, offset in ((1000, 5), (2000, -5)):
    params.put('SLCOffsetSchedule', od.to_value(od.adopt_legacy(False, (0, 0, 0, offset, 0, 0, 0))), block=True)
    actions, cruise = [object()], [object()]
    refreshed, changed = lifecycle.refresh(NOW + milliseconds * 1_000_000, pending_actions=actions, pending_cruise=cruise)
    assert changed and refreshed is runtime
    assert not actions and not cruise
    output, _, target = drive.step(milliseconds, received=not source_gap)
    assert not output.result.errors
    assert runtime.session_id == session
    assert output.result.state.acceptance.accepted == accepted
    assert not output.message.slcState.hasPending
    assert output.message.slcState.hasCeiling
    assert target == pytest.approx(45 + offset)


@pytest.mark.parametrize('accepted_first', [False, True])
def test_offset_edits_invalidate_old_prompts_without_accepting_a_new_limit(tmp_path, accepted_first):
  drive = RetentionDrive(tmp_path, confirm=True)
  params = Params(str(tmp_path))
  lifecycle = SavedSlcLifecycle(params, drive.cp, {'SLC_REPLAY_RUNTIME': '1'})
  runtime, _ = lifecycle.refresh(NOW)
  assert runtime is not None
  drive.runtime = runtime
  first, _, _ = drive.step(0)
  if accepted_first:
    drive.step(50, request=Action(runtime.session_id, 1, first.message.slcState.decisionId, 0, 'accept'))
  old, _, _ = drive.step(100, limit=50)
  old_id = old.message.slcState.decisionId
  params.put('SLCOffsetSchedule', od.to_value(od.adopt_legacy(False, (0, 0, 0, 5, 0, 0, 0))), block=True)
  assert lifecycle.refresh(NOW + 1_000_000_000)[0] is runtime
  stale = Action(runtime.session_id, 2, old_id, old.message.slcState.presentationId, 'accept')
  output, _, target = drive.step(1000, limit=50, request=stale)
  assert not output.result.errors
  assert output.message.slcState.hasPending
  assert output.message.slcState.decisionId != old_id
  assert output.message.slcState.presentationId != old.message.slcState.presentationId
  assert output.message.slcState.hasAccepted == accepted_first
  assert target == pytest.approx(50 if accepted_first else 70)


def test_offset_edits_preserve_rejected_limits(tmp_path):
  drive = RetentionDrive(tmp_path, confirm=True)
  params = Params(str(tmp_path))
  lifecycle = SavedSlcLifecycle(params, drive.cp, {'SLC_REPLAY_RUNTIME': '1'})
  runtime, _ = lifecycle.refresh(NOW)
  assert runtime is not None
  drive.runtime = runtime
  first, _, _ = drive.step(0)
  drive.step(50, request=Action(runtime.session_id, 1, first.message.slcState.decisionId, 0, 'accept'))
  proposed, _, _ = drive.step(100, limit=50)
  drive.step(150, limit=50, request=Action(runtime.session_id, 2, proposed.message.slcState.decisionId, 0, 'reject'))
  rejected = runtime.state.acceptance.rejected
  params.put('SLCOffsetSchedule', od.to_value(od.adopt_legacy(False, (0, 0, 0, 5, 0, 0, 0))), block=True)
  assert lifecycle.refresh(NOW + 1_000_000_000)[0] is runtime
  output, _, target = drive.step(1000, limit=50)
  assert not output.message.slcState.hasPending
  assert output.result.state.acceptance.rejected == rejected
  assert output.message.slcState.acceptedSpeedLimit == pytest.approx(45 * MPH)
  assert target == pytest.approx(50)


class RetentionDrive:
  def __init__(self, path, *, keep=True, confirm=False, dashboard=False):
    params = Params(str(path))
    for key, value in {'SpeedLimitController': True, 'SLCConfirmation': confirm,
                       'SLCConfirmationHigher': False, 'SLCConfirmationLower': False,
                       'SLCPriority1': 'Map Data', 'SLCPriority2': 'Dashboard' if dashboard else 'Map Data',
                       'SLCFallback': 2 if keep else 0}.items():
      params.put(key, value, block=True)
    self.runtime = Runtime(read_params(params), session_id='retention-drive')
    assert not self.runtime.settings.errors
    self.sm, self.cp = replay_inputs()
    car = self.sm['carState']
    car.vEgo = car.vEgoCluster = 45 * MPH
    car.vCruise = car.vCruiseCluster = 70 * MPH * 3.6
    self.sm['slcDashboardObservation'].speedMps = 70 * MPH
    self.ui = ui_fake()
    self.ui.CP = self.cp
    self.ui.sm['carState'].canValid, self.ui.sm['carState'].canTimeout = True, False
    self.ui.sm['carControl'].enabled = self.ui.sm['selfdriveState'].enabled = True
    self.ui.sm['carControl'].longActive = True
    self.adapter = RuntimeSnapshotAdapter(self.ui)
    self.planner = native.LongitudinalPlanner(self.cp, init_v=45 * MPH)

  def step(self, milliseconds, *, received=True, alive=True, status='matchedLimit', limit=45, request=None, **changes):
    now, boot = NOW + milliseconds * 1_000_000, BOOT + milliseconds * 1_000_000
    previous_stamp = self.sm.logMonoTime.get('mapdOut', BOOT)
    self.sm.advance(now)
    dashboard = self.sm['slcDashboardObservation']
    dashboard.observedMonoTime, dashboard.validUntilMonoTime = now - 1, now + 1_000_000_000
    if received:
      event = packet(speedLimit=limit * MPH, computedMonoTime=boot, gpsMonoTime=boot - 100_000_000)
      event.logMonoTime, event.mapdOut.roadStatus = boot, status
      if status in ('noGps', 'noCoverage', 'noMatch'):
        event.valid = False
        event.mapdOut.speedLimit, event.mapdOut.wayId, event.mapdOut.tileLoaded = 0., 0, False
      if status == 'noGps':
        event.mapdOut.gpsSource, event.mapdOut.gpsMonoTime, event.mapdOut.sourceGeneration = 'none', 0, 2
      if status == 'matchedNoLimit':
        event.mapdOut.speedLimit = 0.
      for field, value in changes.items():
        setattr(event.mapdOut, field, value)
      self.sm.data['mapdOut'] = event.mapdOut
      self.sm.valid['mapdOut'], self.sm.logMonoTime['mapdOut'] = bool(event.valid), boot
    else:
      self.sm.logMonoTime['mapdOut'] = previous_stamp
    self.sm.updated['mapdOut'], self.sm.alive['mapdOut'] = received, alive
    output = self.runtime.step(self.sm, self.cp, now_ns=now, now_boot_ns=boot, request=request)
    self.ui.sm.put('slcState', output.message.slcState)
    self.ui.sm['carState'].vCruiseCluster = self.sm['carState'].vCruiseCluster
    for service in ('slcState', 'carState', 'carControl', 'selfdriveState'):
      self.ui.sm.logMonoTime[service] = now
      self.ui.sm.recv_time[service] = now / 1e9
    view = self.adapter.build(ShellMode.ONROAD, now_ns=now).onroad
    with patch.object(native, 'get_cruise_accel', wraps=native.get_cruise_accel) as cruise:
      self.planner.update(self.sm, cruise_ceiling=output.result.ceiling, now_ns=now)
    return output, view, cruise.call_args.args[1] / MPH


@pytest.mark.parametrize('answer', ['reject', 'timeout'])
@pytest.mark.parametrize('metric', [False, True])
@pytest.mark.parametrize('limit', [40, 50])
def test_compact_rejection_or_timeout_dismisses_actions_and_retains_the_native_ceiling(tmp_path, answer, metric, limit):
  drive = RetentionDrive(tmp_path, confirm=True)
  params = Params(str(tmp_path))
  params.put('SLCOffsetSchedule', od.to_value(od.adopt_legacy(False, (5.0,) * 7)), block=True)
  drive.runtime = Runtime(read_params(params))
  drive.ui.is_metric = metric
  first, _, _ = drive.step(0)
  approved, _, target = drive.step(50, request=Action(drive.runtime.session_id, 1, first.message.slcState.decisionId, 0, 'accept'))
  accepted = approved.result.state.acceptance.accepted
  assert target == pytest.approx(50)

  proposed, view, target = drive.step(100, limit=limit)
  factor = MPH * (3.6 if metric else 2.2369362921)
  assert [control.label for control in slc_controls(Profile.COMPACT, view)] == [
    f'Apply {round((limit + 5) * factor)}', f'Keep {round(50 * factor)}']
  assert target == pytest.approx(50)
  request = None
  if answer == 'reject':
    # Use the visible Keep button, including its normal dispatcher validation.
    emitted = []
    touch = OnroadInput(emitted.append, Profile.COMPACT)
    touch.press(380, 205, view)
    touch.release(380, 205, view)
    reject, = emitted
    assert reject.kind == SlcActionKind.REJECT
    request = publish_request(proposed.message.slcState, reject, NOW + 100_000_000)
  elapsed = 150 if answer == 'reject' else 30_150
  rejected, view, target = drive.step(elapsed, limit=limit, request=request)
  assert not rejected.result.errors
  assert rejected.result.acceptance.basis == ('driver_reject' if answer == 'reject' else 'timeout_reject')
  assert not rejected.message.slcState.hasPending
  candidate = rejected.result.state.acceptance.observation.candidate
  assert candidate in rejected.result.state.acceptance.rejected
  assert view.alert.size == AlertSize.NONE
  assert view.speed_limit.kind == ObservationKind.VALID and view.speed_limit.action_enabled
  assert slc_controls(Profile.COMPACT, view) == ()
  assert target == pytest.approx(50)

  # The former recovery area cannot claim a tap or adopt the rejected limit.
  emitted = []
  touch = OnroadInput(emitted.append, Profile.COMPACT)
  touch.press(315, 205, view)
  assert not touch.claimed
  touch.release(315, 205, view)
  assert not emitted
  for delay, status in ((50, 'matchedLimit'), (100, 'noCoverage'), (150, 'matchedLimit')):
    output, view, target = drive.step(elapsed + delay, limit=limit, status=status)
    assert not output.result.errors
    assert output.result.state.acceptance.accepted == accepted
    assert candidate in output.result.state.acceptance.rejected
    assert not output.message.slcState.hasPending
    assert slc_controls(Profile.COMPACT, view) == ()
    assert target == pytest.approx(50)
    assert physical_actions.pending_confirmation(drive.ui.sm, NOW + (elapsed + delay) * 1_000_000,
                                               long_active=True, pcm_cruise=False) is None
  # A different candidate still gets the normal two-choice confirmation.
  output, view, target = drive.step(elapsed + 200, limit=55)
  assert output.message.slcState.hasPending
  assert [control.request.kind for control in slc_controls(Profile.COMPACT, view)] == [SlcActionKind.ACCEPT, SlcActionKind.REJECT]
  assert target == pytest.approx(50)


@pytest.mark.parametrize('keep', [False, True])
@pytest.mark.parametrize('loss', ['noCoverage', 'noMatch', 'noGps', 'matchedNoLimit', 'missingTile',
                                 'lookahead', 'stopped', 'deadTransport', 'externalGpsStale'])
def test_maps_loss_retains_only_accepted_limit_when_enabled(tmp_path, keep, loss):
  drive = RetentionDrive(tmp_path, keep=keep)
  drive.step(0)
  changes = {'status': loss}
  if loss in ('stopped', 'deadTransport'):
    changes = {'received': False, 'alive': loss == 'stopped'}
  elif loss == 'missingTile':
    changes = {'tileLoaded': False}
  elif loss == 'lookahead':
    changes = {'waySelectionType': 'possible'}
  elif loss == 'externalGpsStale':
    changes = {'gpsMonoTime': BOOT - 300_000_000}
  output, view, target = drive.step(251, **changes)
  assert target == pytest.approx(45 if keep else 70)
  assert output.message.slcState.acceptedSpeedLimit == pytest.approx(45 * MPH)
  assert output.message.slcState.hasCeiling == keep
  assert output.message.slcState.hasAcceptedAdjustedLimit
  assert output.message.slcState.acceptedAdjustedLimit == pytest.approx(45 * MPH)
  assert view.speed_limit.kind != ObservationKind.VALID
  shown = resolve_unified_speed(view)
  assert (shown.max_text, shown.posted_text, shown.status) == ('70', '45' if keep else '–',
                                                           'Using previous limit' if keep else 'Unavailable')
  assert all(slc_controls(profile, view) == () for profile in Profile)
  assert not output.message.slcState.hasPending


@pytest.mark.parametrize('answer', ['accept', 'reject', 'timeout'])
@pytest.mark.parametrize('limit', [40, 50])
def test_long_gap_confirmation_and_recovery_keep_the_accepted_limit(tmp_path, answer, limit):
  drive = RetentionDrive(tmp_path, confirm=True)
  first, _, _ = drive.step(0)
  assert first.message.slcState.hasPending and not first.message.slcState.hasAccepted
  drive.step(50, request=Action(drive.runtime.session_id, 1, first.message.slcState.decisionId, 0, 'accept'))
  _, _, target = drive.step(100, status='noCoverage')
  assert target == pytest.approx(45)
  _, view, target = drive.step(35_000, received=False)
  assert target == pytest.approx(45)
  assert resolve_unified_speed(view).status == 'Using previous limit'
  pending, _, target = drive.step(40_000, limit=limit, wayId=124)
  assert target == pytest.approx(45) and pending.message.slcState.hasPending
  action = None if answer == 'timeout' else Action(drive.runtime.session_id, 2, pending.message.slcState.decisionId, 0, answer)
  drive.step(71_000 if answer == 'timeout' else 40_050, limit=limit, wayId=124, request=action)
  output, view, target = drive.step(300_000, received=False)
  assert target == pytest.approx(limit if answer == 'accept' else 45)
  assert not output.message.slcState.hasPending
  assert resolve_unified_speed(view).posted_text == (str(limit) if answer == 'accept' else '45')
  # A dead SLC publisher cannot make the widget claim retained control indefinitely.
  drive.ui.sm.alive['slcState'] = False
  expired = drive.adapter.build(ShellMode.ONROAD, now_ns=NOW + 300_001_000_000).onroad
  assert resolve_unified_speed(expired).active_side == 'none'


def test_unchanged_map_speed_does_not_accept_new_identity_or_keep_old_prompt(tmp_path):
  drive = RetentionDrive(tmp_path, confirm=True)
  first, _, _ = drive.step(0)
  accepted, _, _ = drive.step(50, request=Action(drive.runtime.session_id, 1, first.message.slcState.decisionId, 0, 'accept'))
  unchanged, _, target = drive.step(100, wayId=124)
  assert target == pytest.approx(45)
  assert not unchanged.message.slcState.hasPending
  assert unchanged.result.acceptance.history_write is None
  assert unchanged.result.acceptance.state.accepted == accepted.result.acceptance.state.accepted
  pending, _, _ = drive.step(150, limit=50, wayId=124)
  assert pending.message.slcState.hasPending
  recovered, _, target = drive.step(200)
  assert target == pytest.approx(45) and not recovered.message.slcState.hasPending
  assert not drive.step(250)[0].result.errors


def test_retention_respects_lower_max_secondary_source_and_reset(tmp_path):
  drive = RetentionDrive(tmp_path / 'max')
  drive.step(0)
  drive.sm['carState'].vCruise = drive.sm['carState'].vCruiseCluster = 40 * MPH * 3.6
  _, view, target = drive.step(300, received=False)
  assert target == pytest.approx(40)
  assert resolve_unified_speed(view).status == 'Using set speed'
  drive.runtime.reset()
  output, _, _ = drive.step(400, received=False)
  assert not output.message.slcState.hasAccepted and output.result.ceiling is None
  secondary = RetentionDrive(tmp_path / 'secondary', dashboard=True)
  secondary.step(0)
  output, _, target = secondary.step(300, status='noCoverage')
  assert target == pytest.approx(70)
  assert output.message.slcState.acceptedSource == 'dashboard'


def test_compact_sign_keeps_accepted_value_without_pulsing_on_recovery(tmp_path):
  drive = RetentionDrive(tmp_path)
  _, before, _ = drive.step(0)
  _, held, _ = drive.step(300, received=False)
  _, recovered, _ = drive.step(400)
  fonts = Mock()
  fonts.measure.return_value = Mock(width=20, height=20)
  renderer = CompactHudRenderer(fonts, Path('/unused'))
  with patch('openpilot.starpilot.ui.onroad_compact_widgets.rl.draw_rectangle_rounded_lines_ex'), \
       patch('openpilot.starpilot.ui.onroad_compact_widgets.rl.draw_circle'), \
       patch('openpilot.starpilot.ui.onroad_compact_widgets.rl.draw_ring'):
    for view in (before, held, recovered):
      renderer._speed_limit_sign(replace(view, appearance=replace(view.appearance, show_speed_limit_sign=True)))
  assert any(call.args[0] == '45' for call in fonts.draw.call_args_list)
  assert renderer._speed_limit_pulse.start_time == NOW / 1e9
