"""Mapped previews through the actual runtime, confirmations and Card guards."""
from dataclasses import replace
from pathlib import Path
import base64
import json

import pytest

from openpilot.common.params import Params
from openpilot.selfdrive.car.cruise import VCruiseHelper
from openpilot.starpilot.speed_limits import acceptance as acc, physical_actions as pa
from openpilot.starpilot.speed_limits.map_source import decode_event
from openpilot.starpilot.speed_limits.map_observation import MapSource, copy_frame
from openpilot.starpilot.speed_limits.runtime import Action, CruiseEvent, Runtime
from openpilot.starpilot.speed_limits.runtime_settings import parse, read_params
from openpilot.starpilot.speed_limits.speed_domain import OffsetBand, OffsetSchedule
from openpilot.starpilot.speed_limits.tests.test_maps_runtime import packet
from openpilot.starpilot.speed_limits.tests.test_runtime_replay import ReplaySM
from openpilot.starpilot.ui.onroad_state import speed_limit_from_message
from openpilot.starpilot.ui.tests.test_slc_ui_runtime import START, replay_inputs
from openpilot.starpilot.ui.unified_speed_presentation import resolve_unified_speed


BOUNDARY = 'a' * 64
STEP = 50_000_000


class Drive:
  def __init__(self, *, confirm=False, seconds=5):
    self.sm, self.cp = replay_inputs()
    self.now = START
    self.sm['carState'].canValid = True
    self.sm['carState'].vCruise = self.sm['carState'].vCruiseCluster = 79.2
    settings = replace(parse({'SpeedLimitController': True, 'SLCPriority1': 'Maps',
      'SLCPriority2': 'Dashboard', 'SLCAdvanceSeconds': seconds}), offsets=OffsetSchedule((OffsetBand(0., None, 2.),)))
    self.runtime = Runtime(settings, session_id='drive', is_metric=True)
    self.tick(target=0.)
    assert self.runtime.state.acceptance.accepted.candidate.speed_mps == 20.
    self.runtime.settings = replace(settings, acceptance=acc.Policy(confirm_lower=confirm, confirm_higher=confirm))

  def tick(self, *, current=20., target=15., distance=60., way=1, target_way=2, speed=20., stopped=False,
           alive=True, producer=41, boundary=BOUNDARY, action=None, event=None, at=None, dashboard=None):
    self.now = self.now + STEP if at is None else at
    self.sm.advance(self.now)
    boot = self.now + 4_000_000_000
    road = packet(speedLimit=current, previewSpeedLimit=target, previewDistance=distance,
      previewBoundaryId=boundary if target else '', previewWayId=target_way, wayId=way, producerSession=producer,
      gpsMonoTime=boot-50_000_000, computedMonoTime=boot)
    road.logMonoTime = boot
    self.sm.data['mapdOut'] = road.mapdOut
    for values in (self.sm.valid, self.sm.alive, self.sm.updated):
      values['mapdOut'] = alive
    self.sm.logMonoTime['mapdOut'] = boot
    self.sm['carState'].vEgo = self.sm['carState'].vEgoCluster = speed
    self.sm['carState'].standstill = stopped
    source = self.sm['slcDashboardObservation']
    source.status, source.speedMps = ('unknown', 0.) if dashboard is None else ('valid', dashboard)
    source.observedMonoTime, source.validUntilMonoTime = self.now, self.now+1_000_000_000
    return self.runtime.step(self.sm, self.cp, now_ns=self.now, now_boot_ns=boot, request=action, cruise_event=event)

  def action(self, state, kind):
    return Action(self.runtime.session_id, self.now+STEP, state.decisionId, state.presentationId, kind)

  def apply(self, output):
    command = output.command.slcCruiseCommand
    card_sm = ReplaySM({'slcState': output.message.slcState}, self.now)
    approved = pa.state_current(card_sm, None, 'card-producer', self.now)
    previous = self.sm['carState'].vCruise / 3.6
    assert pa.command_applicable(command, approved, None, 'card-producer', self.now,
      previous, long_active=True, button_event=False)
    helper = VCruiseHelper(self.cp)
    helper.v_cruise_kph = helper.v_cruise_cluster_kph = previous*3.6
    helper.apply_slc_target(command.targetMps, True)
    self.sm['carState'].vCruise = helper.v_cruise_kph
    self.sm['carState'].vCruiseCluster = helper.v_cruise_cluster_kph
    event = CruiseEvent(1, self.now+STEP, previous, helper.v_cruise_kph/3.6, 'unknown',
      'card-producer', self.now+STEP, 'commandApplied', self.runtime.session_id, command_id=command.commandId)
    return self.tick(event=event)


@pytest.mark.parametrize('target', [15., 25.])
def test_threshold_uses_physical_speed_for_both_directions(target):
  drive = Drive()
  outside = drive.tick(target=target, distance=100.01)
  assert outside.command is None and not outside.message.slcState.upcomingBoundaryId
  inside = drive.tick(target=target, distance=100.)
  state = inside.message.slcState
  assert state.speedLimit == 20. and state.upcomingSpeedLimit == target
  assert state.acceptedSpeedLimit == target and state.acceptedAdjustedLimit == target+2.
  assert inside.command.slcCruiseCommand.targetMps == target+2.


@pytest.mark.parametrize('speed,stopped', [(0., True), (0., False), (20., True)])
def test_no_first_offer_at_standstill(speed, stopped):
  drive = Drive()
  output = drive.tick(speed=speed, stopped=stopped, distance=1.)
  assert output.command is None and not output.message.slcState.upcomingBoundaryId


def test_off_preserves_current_limit_behavior():
  drive = Drive(seconds=0)
  assert drive.tick().message.slcState.acceptedSpeedLimit == 20.
  output = drive.tick(current=15., target=0., way=2)
  assert output.message.slcState.acceptedSpeedLimit == 15.
  assert output.command is not None


@pytest.mark.parametrize('primary,dashboard,target,early', [
  ('Dashboard', 25., 15., False), ('Highest', 25., 15., False), ('Lowest', 10., 15., False),
  ('Highest', 25., 25., False), ('Highest', 22., 25., True), ('Lowest', 22., 15., True),
])
def test_preview_respects_existing_source_selection(primary, dashboard, target, early):
  drive = Drive()
  drive.runtime.settings = replace(drive.runtime.settings,
    selection=parse({'SLCPriority1': primary, 'SLCPriority2': 'Maps'}).selection)
  output = drive.tick(dashboard=dashboard, target=target)
  assert bool(output.message.slcState.upcomingBoundaryId) == early
  if early:
    command, state = output.command.slcCruiseCommand, output.message.slcState
    assert command.source == 'map'
    assert pa.command_applicable(command, state, None, 'card-producer', drive.now,
      22., long_active=True, button_event=False)


def test_reverse_and_inactive_control_do_not_start_advance():
  for reason in ('reverse', 'inactive', 'stale_car'):
    drive = Drive()
    if reason == 'reverse':
      drive.sm['carState'].gearShifter = 'reverse'
    elif reason == 'inactive':
      drive.sm['carControl'].longActive = False
    else:
      drive.sm['carState'].canTimeout = True
    assert not drive.tick(distance=1.).message.slcState.upcomingBoundaryId


def test_confirmation_latches_on_slowdown_and_stop_then_times_out_once():
  drive = Drive(confirm=True)
  first = drive.tick().message.slcState
  start = drive.runtime.advance.encounter.started_ns
  assert start is not None
  slower = drive.tick(speed=1., distance=59.).message.slcState
  stopped = drive.tick(speed=0., stopped=True, distance=59.).message.slcState
  assert first.decisionId == slower.decisionId == stopped.decisionId
  expired = drive.tick(at=start+acc.CONFIRMATION_NS, speed=0., stopped=True).message.slcState
  assert expired.actionStatus in ('', 'timeout_reject') and not expired.hasPending
  crossed = drive.tick(current=15., target=0., way=2)
  assert not crossed.message.slcState.hasPending and crossed.command is None


@pytest.mark.parametrize('kind', ['accept', 'reject'])
def test_exact_deadline_action_wins_and_crossing_does_not_repeat(kind):
  drive = Drive(confirm=True)
  state = drive.tick().message.slcState
  start = drive.runtime.advance.encounter.started_ns
  assert start is not None
  action = drive.action(state, kind)
  output = drive.tick(at=start+acc.CONFIRMATION_NS, action=action)
  assert output.message.slcState.actionStatus == kind
  assert (output.command is not None) == (kind == 'accept')
  if kind == 'accept':
    drive.sm['carState'].vCruise = drive.sm['carState'].vCruiseCluster = 61.2
  crossed = drive.tick(current=15., target=0., way=2)
  assert not crossed.message.slcState.hasPending and crossed.command is None


def test_recovery_renews_presentation_without_restarting_confirmation():
  drive = Drive(confirm=True)
  first = drive.tick().message.slcState
  start = drive.runtime.advance.encounter.started_ns
  assert start is not None
  lost = drive.tick(alive=False)
  assert lost.message.slcState.hasPending and lost.command is None
  assert lost.message.slcState.decisionId == first.decisionId and lost.message.slcState.presentationId == 0
  recovered = drive.tick(at=start+9_000_000_000, producer=42).message.slcState
  assert recovered.hasPending and recovered.presentationId != first.presentationId
  expired = drive.tick(at=start+acc.CONFIRMATION_NS+1)
  assert not expired.message.slcState.hasPending and expired.command is None


def test_disengagement_cancels_early_confirmation_and_reengagement_gets_a_fresh_deadline():
  drive = Drive(confirm=True)
  first = drive.tick().message.slcState
  start = drive.now
  drive.sm['carControl'].enabled = drive.sm['carControl'].longActive = False
  drive.sm['selfdriveState'].enabled = False
  drive.sm['controlsState'].longControlState = 'off'
  inactive = drive.tick(at=start+2_000_000_000)
  assert not inactive.message.slcState.hasPending and inactive.command is None
  assert not drive.runtime.advance.encounter.declined
  drive.sm['carControl'].enabled = drive.sm['carControl'].longActive = True
  drive.sm['selfdriveState'].enabled = True
  drive.sm['controlsState'].longControlState = 'pid'
  resumed = drive.tick(at=start+20_000_000_000).message.slcState
  assert resumed.hasPending and resumed.decisionId != first.decisionId
  assert resumed.pendingSinceMonoTime == drive.now
  restarted = drive.now
  stale_action = drive.tick(action=drive.action(first, 'accept'))
  assert stale_action.message.slcState.hasPending and stale_action.command is None
  assert drive.tick(at=restarted+9_000_000_000).message.slcState.hasPending
  assert not drive.tick(at=restarted+acc.CONFIRMATION_NS).message.slcState.hasPending
  assert drive.runtime.advance.encounter.declined


def test_fresh_different_boundary_supersedes_without_accepting_stale_action():
  drive = Drive(confirm=True)
  first = drive.tick().message.slcState
  changed = drive.tick(boundary='b'*64, target=25., target_way=3, action=drive.action(first, 'accept'))
  assert changed.message.slcState.hasPending and changed.message.slcState.decisionId != first.decisionId
  assert changed.message.slcState.pendingSpeedLimit == 25. and changed.command is None


def test_short_zone_can_qualify_exit_immediately_without_hidden_dwell():
  drive = Drive()
  drive.apply(drive.tick())
  exit_offer = drive.tick(current=15., way=2, target=20., target_way=3, boundary='b'*64, distance=10.)
  assert exit_offer.message.slcState.speedLimit == 15.
  assert exit_offer.message.slcState.acceptedSpeedLimit == 20.
  assert exit_offer.command.slcCruiseCommand.targetMps == 22.


def test_time_edits_keep_decision_and_off_withdraws_without_set_rollback():
  drive = Drive(confirm=True)
  first = drive.tick().message.slcState
  drive.runtime.update_advance(1)
  second = drive.tick(distance=60.).message.slcState
  assert second.decisionId == first.decisionId and second.pendingSinceMonoTime == first.pendingSinceMonoTime
  drive.runtime.update_advance(0)
  assert not drive.tick().message.slcState.hasPending
  drive.runtime.update_advance(10)
  assert not drive.tick().message.slcState.hasPending
  assert drive.tick(current=15., target=0., way=2).message.slcState.hasPending


def test_applied_set_survives_off_source_loss_and_crossing_without_reissue():
  drive = Drive()
  applied = drive.apply(drive.tick())
  assert applied.command is None and applied.message.slcState.commandStatus == 'applied'
  drive.runtime.update_advance(0)
  for changes in ({}, {'alive': False}, {'current': 15., 'target': 0., 'way': 2}):
    output = drive.tick(**changes)
    assert output.command is None and drive.sm['carState'].vCruise == 61.


def test_wheel_adopt_keeps_meaning_the_current_displayed_limit():
  drive = Drive()
  applied = drive.apply(drive.tick())
  adopted = drive.tick(action=drive.action(applied.message.slcState, 'adopt'))
  assert not adopted.result.errors
  assert adopted.message.slcState.acceptedSpeedLimit == 20.
  assert adopted.message.slcState.actionStatus == 'adopt'
  assert adopted.command.slcCruiseCommand.targetMps == 22.
  assert not adopted.message.slcState.upcomingBoundaryId


def test_stale_current_adopt_cannot_cancel_or_replace_a_fresh_producer_proposal():
  drive = Drive()
  applied = drive.apply(drive.tick())
  rejected = drive.tick(producer=42, action=drive.action(applied.message.slcState, 'adopt'))
  assert not rejected.result.errors and rejected.command is None
  assert rejected.message.slcState.acceptedSpeedLimit == 15.
  assert rejected.message.slcState.upcomingBoundaryId == BOUNDARY
  assert not drive.runtime.advance.encounter.disabled


def test_manual_set_override_and_current_adoption_survive_boundary():
  drive = Drive()
  drive.apply(drive.tick())
  previous = drive.sm['carState'].vCruise / 3.6
  drive.sm['carState'].vCruise = drive.sm['carState'].vCruiseCluster = 80.
  event = CruiseEvent(2, drive.now+STEP, previous, 80./3.6, 'accel', 'card-producer', drive.now+STEP)
  overridden = drive.tick(event=event)
  assert overridden.message.slcState.driverOverrideActive and overridden.command is None
  withdrawn = drive.tick()
  assert withdrawn.message.slcState.presentationId > 0
  current = drive.tick(action=drive.action(withdrawn.message.slcState, 'adopt'))
  assert not current.result.errors
  assert current.message.slcState.acceptedSpeedLimit == 20.
  assert current.message.slcState.actionStatus == 'adopt'
  assert not current.message.slcState.driverOverrideActive


def test_offset_edit_uses_upcoming_band_without_changing_decision_or_current_sign():
  drive = Drive()
  first = drive.tick()
  accepted_at = first.message.slcState.acceptedMonoTime
  drive.runtime.update_offsets(OffsetSchedule((OffsetBand(0., 18., 1.), OffsetBand(18., None, 3.))))
  output = drive.tick(at=drive.now+200_000_000)
  state = output.message.slcState
  assert state.acceptedMonoTime == accepted_at and not state.hasPending
  assert state.speedLimit == 20. and state.presentationAdjustedLimit == 23.
  assert state.acceptedAdjustedLimit == 16. and output.command.slcCruiseCommand.targetMps == 16.


def test_upcoming_commands_bind_boundary_and_preserve_card_fences():
  drive = Drive()
  output = drive.tick()
  state, command = output.message.slcState, output.command.slcCruiseCommand
  def applies(**changes):
    return pa.command_applicable(command, state, None, 'card-producer', drive.now,
      changes.pop('selected', 22.), long_active=changes.pop('active', True), button_event=changes.pop('button', False))
  assert applies()
  assert not applies(selected=23.) and not applies(active=False) and not applies(button=True)
  command.upcomingBoundaryId = 'b' * 64
  assert not applies()
  command.upcomingBoundaryId = ''
  assert not applies()
  command.upcomingBoundaryId = BOUNDARY
  state.upcomingSpeedLimit = float('nan')
  assert not applies()


def test_existing_confirmation_resolver_shows_proposal_without_changing_current_sign():
  from openpilot.starpilot.ui.onroad_state import OnroadState
  drive = Drive(confirm=True)
  state = drive.tick().message.slcState
  obs = speed_limit_from_message(state)
  shown_state = OnroadState(True, False, 20., 79.2, obs, metric=True, show_slc_offset=True)
  normal = resolve_unified_speed(shown_state)
  prompt = resolve_unified_speed(shown_state, confirmation=True)
  assert normal.posted_text == '72' and normal.offset_text == '+7'
  assert prompt.posted_text == '54' and prompt.proposal_text == '61' and prompt.offset_text == '+7'


@pytest.mark.parametrize('field,value', [('previewSpeedLimit', float('nan')), ('previewDistance', -1.),
  ('previewDistance', 501.), ('previewBoundaryId', 'bad'), ('previewWayId', 0)])
def test_bad_optional_preview_cannot_disable_or_authorize_current_map(field, value):
  event = packet()
  event.mapdOut.previewSpeedLimit = 15.
  event.mapdOut.previewDistance = 50.
  event.mapdOut.previewBoundaryId = BOUNDARY
  event.mapdOut.previewWayId = 2
  setattr(event.mapdOut, field, value)
  source = MapSource()
  current = source.step(copy_frame(event.mapdOut, event_valid=True, event_boot_ns=event.logMonoTime),
    received=True, now_boot_ns=event.logMonoTime, transport_alive=True, drive_session='drive', car_fingerprint='car')
  assert current.kind is acc.ObservationKind.VALID and source.upcoming is None


def test_actual_go_fixture_qualifies_current_and_upcoming_fields_with_host_schema():
  root = Path(__file__).resolve().parents[4]
  fixture = json.loads((root / 'mapd_repo/cereal/testdata/mapd_preview_wire.json').read_text())
  frame = decode_event(base64.b64decode(fixture['event_base64']))
  source = MapSource()
  current = source.step(frame, received=True, now_boot_ns=frame.event_mono_ns, transport_alive=True,
    drive_session='drive', car_fingerprint='car')
  assert current.candidate.speed_mps == 20.
  assert source.upcoming.observation.candidate.speed_mps == 15.
  assert source.upcoming.boundary_id == BOUNDARY and source.upcoming.way_id == 2 and source.upcoming.distance_m == 60.


@pytest.mark.parametrize('raw', [b'0', b'5', b'10', b'-1', b'11', b'1.5', b'broken', b'\xff', b'5\n', b'05'])
def test_saved_advance_values_are_optional_bounded_and_not_rewritten(tmp_path, raw):
  params = Params(str(tmp_path))
  params.put_bool('SpeedLimitController', True, block=True)
  path = Path(params.get_param_path('SLCAdvanceSeconds'))
  path.write_bytes(raw)
  settings = read_params(params)
  assert settings.enabled and not settings.errors
  assert settings.advance_seconds == ({b'5': 5, b'10': 10}.get(raw, 0))
  assert path.read_bytes() == raw


def test_time_only_lifecycle_refresh_keeps_session_decision_deadline_and_decline(tmp_path):
  from openpilot.selfdrive.controls.plannerd import SavedSlcLifecycle
  params = Params(str(tmp_path))
  for key, value in {'SpeedLimitController': True, 'SLCConfirmation': True, 'IsMetric': True}.items():
    params.put_bool(key, value, block=True)
  params.put('SLCPriority1', 'Map Data', block=True)
  params.put('SLCAdvanceSeconds', 5, block=True)
  drive = Drive()
  lifecycle = SavedSlcLifecycle(params, drive.cp, {'SLC_REPLAY_RUNTIME': '1'})
  runtime, _ = lifecycle.refresh(START)
  drive.runtime = runtime
  drive.sm['carState'].vCruise = drive.sm['carState'].vCruiseCluster = 72.
  drive.tick(target=0.)
  first = drive.tick().message.slcState
  assert first.hasPending
  params.put('SLCAdvanceSeconds', 1, block=True)
  now = drive.now+1_000_000_000
  assert lifecycle.refresh(now)[0] is runtime
  pending = drive.tick(at=now).message.slcState
  assert pending.decisionId == first.decisionId and pending.pendingSinceMonoTime == first.pendingSinceMonoTime
  drive.tick(action=drive.action(pending, 'reject'))
  params.put('SLCAdvanceSeconds', 10, block=True)
  now = drive.now+1_000_000_000
  assert lifecycle.refresh(now)[0] is runtime
  assert not drive.tick(at=now).message.slcState.hasPending
  crossed = drive.tick(current=15., target=0., way=2)
  assert not crossed.message.slcState.hasPending and crossed.command is None


def test_existing_settings_owner_saves_guards_and_repairs_one_timing_option(tmp_path):
  from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
  from openpilot.starpilot.ui.feature_settings_state import row_change, row_default
  params = Params(str(tmp_path))
  params.put_bool('SpeedLimitController', True, block=True)
  drive = Drive()
  allowed = [True]
  owner = FeatureSettingsOwner(params, lambda group: allowed[0], vehicle_fingerprint=lambda: drive.cp.carFingerprint)
  owner.vehicle_params = lambda: drive.cp
  owner.configuration_vehicle = lambda: True
  def rows():
    return owner.snapshot('slc', parked=True, system_long=True, lateral_context=True, metric=True).rows
  def row():
    return next(item for item in rows() if item.key == 'SLCAdvanceSeconds')
  keys = [item.key for item in rows()]
  assert keys.index('SLCAdvanceSeconds') == keys.index('SLCConfirmation')+1
  assert row().available and row().value == 'Off'
  request = row_change(row())
  assert request is not None
  assert owner.apply(request)
  assert read_params(params).advance_seconds == 1
  assert not owner.apply(request)
  request = row_change(row())
  assert request is not None
  allowed[0] = False
  assert not owner.apply(request)
  allowed[0] = True
  Path(params.get_param_path('SLCAdvanceSeconds')).write_bytes(b'broken')
  assert row().choices == ('Off',)
  request = row_default(row())
  assert request is not None and owner.apply(request)
  assert read_params(params).advance_seconds == 0 and read_params(params).enabled
