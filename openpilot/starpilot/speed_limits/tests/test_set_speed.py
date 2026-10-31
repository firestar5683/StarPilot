"""The live adoption path owns one card set speed, including PCM system long."""
from types import SimpleNamespace
from dataclasses import replace
from unittest.mock import patch

import pytest

from opendbc.car.dashboard_speed_limit import Status
from opendbc.car.structs import car
from openpilot.common.constants import CV
from openpilot.selfdrive.car.cruise import VCruiseHelper, slc_target_kph
from openpilot.selfdrive.controls.lib import longitudinal_planner as planner
from openpilot.starpilot.speed_limits import acceptance as acc, physical_actions
from openpilot.starpilot.speed_limits.runtime import Action, CruiseEvent, Runtime
from openpilot.starpilot.speed_limits.runtime_settings import parse
from openpilot.starpilot.speed_limits.tests.test_runtime_replay import ReplaySM
from openpilot.starpilot.speed_limits.tests import test_runtime_replay as replay_fixture
from openpilot.starpilot.speed_limits.speed_domain import OffsetBand, OffsetSchedule

START = 2_000_000_000


@pytest.fixture
def drive():
  fixture = replay_fixture.RuntimeReplayTests()
  fixture.setUp()
  fixture.sm['carState'].vCruise = fixture.sm['carState'].vCruiseCluster = 60.
  return fixture.sm, fixture.cp


def tick(runtime, sm, cp, seconds, **kwargs):
  now = START + round(seconds * 1e9)
  sm.advance(now)
  sm['slcDashboardObservation'].validUntilMonoTime = now + 1_000_000_000
  return runtime.step(sm, cp, now_ns=now, **kwargs)


def command_receipt(runtime, command, seconds, previous, selected, *, applied=True, event_id=1):
  stamp = START + round(seconds * 1e9)
  return CruiseEvent(event_id, stamp, previous / 3.6, selected / 3.6, '', 'card-producer', stamp,
                     'commandApplied' if applied else 'commandRejected', runtime.session_id,
                     command.decisionId, command.presentationId, command.commandId)


@pytest.mark.parametrize('wheel', [False, True])
def test_retained_confirmation_reject_uses_the_original_choice_without_a_speed_command(drive, wheel):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': True}))
  first = tick(runtime, sm, cp, 0).message.slcState
  sm['slcDashboardObservation'].status = 'unknown'
  lost = tick(runtime, sm, cp, .05)
  held = lost.message.slcState
  assert held.hasPending and held.decisionId == first.decisionId
  assert held.pendingSinceMonoTime == first.pendingSinceMonoTime
  assert held.presentationId == 0 and lost.command is None
  invalid_accept = Action(runtime.session_id, 1, held.decisionId, 0, 'accept')
  denied = tick(runtime, sm, cp, .075, request=invalid_accept)
  assert denied.command is None and denied.message.slcState.hasPending
  if wheel:
    card_sm = ReplaySM({'slcState': held}, START + 50_000_000)
    pending = physical_actions.pending_confirmation(card_sm, START + 50_000_000, long_active=True)
    assert pending is not None and pending.presentation_id == 0
    helper = VCruiseHelper(cp)
    helper.v_cruise_kph = helper.v_cruise_cluster_kph = 60.
    cs = car.CarState(cruiseState={'available': True},
                      buttonEvents=[car.CarState.ButtonEvent(type='decelCruise', pressed=True)])
    helper.update_v_cruise(cs, True, False, pending, slc_enabled=True)
    assert helper.slc_consumed_button is not None and helper.v_cruise_kph == 60.
    event = CruiseEvent(1, START + 100_000_000, 0., 0., 'decel', 'card-producer', START + 100_000_000,
                        'confirmationReject', runtime.session_id, held.decisionId, 0)
    result = tick(runtime, sm, cp, .1, cruise_event=event)
  else:
    request = Action(runtime.session_id, 2, held.decisionId, 0, 'reject')
    result = tick(runtime, sm, cp, .1, request=request)
  assert not result.result.errors and result.message.slcState.actionStatus == 'reject'
  assert not result.message.slcState.hasPending and result.command is None
  sm['slcDashboardObservation'].status = 'valid'
  recovered = tick(runtime, sm, cp, .15)
  assert not recovered.message.slcState.hasPending and recovered.command is None


@pytest.mark.parametrize('manual', [False, True])
def test_provider_flapping_and_vision_gaps_do_not_repeat_adoption_or_confirmation(drive, manual):
  from openpilot.cereal import messaging
  from openpilot.starpilot.speed_limits.vision.observation import MODEL_ID

  sm, cp = drive
  envelope = messaging.new_message('slcVisionObservation')
  vision = envelope.slcVisionObservation.vision
  vision.producerSessionId, vision.modelId, vision.stream = 'vision-producer', MODEL_ID, 'road'
  vision.speedMps, vision.confidence, vision.supportCount, vision.episode = 35 * CV.MPH_TO_MS, .95, 2, 4
  sm = ReplaySM({**sm.data, 'slcVisionObservation': envelope.slcVisionObservation}, START)
  sm['slcDashboardObservation'].speedMps = 30 * CV.MPH_TO_MS
  selected = slc_target_kph(30 * CV.MPH_TO_MS, False)
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = selected
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard',
                          'SLCPriority2': 'Vision', 'SLCConfirmation': manual}),
                    vision_enabled=True, vision_control_qualified=True)

  def observe(seconds, dashboard=False, available=True, **kwargs):
    now = START + round(seconds * 1e9)
    sm['slcDashboardObservation'].status = 'valid' if dashboard else 'unknown'
    vision.status = 'valid' if available else 'stale'
    vision.observedMonoTime = vision.cameraFrameEofBootTime = now
    vision.validUntilMonoTime = now + 2_000_000_000
    vision.frameId += 1
    return tick(runtime, sm, cp, seconds, now_boot_ns=now, **kwargs)

  initial = observe(0, dashboard=True)
  assert initial.message.slcState.hasAccepted and initial.command is None
  for seconds, primary in ((.1, False), (.5, True), (1., False), (1.5, True), (2., False)):
    output = observe(seconds, dashboard=primary)
    assert output.command is None and not output.message.slcState.hasPending
    assert output.message.slcState.acceptedMonoTime == initial.message.slcState.acceptedMonoTime
  settled = observe(4.)
  assert not settled.result.errors
  assert settled.message.slcState.hasPending == manual
  if not manual:
    assert settled.command is not None
    selected = slc_target_kph(settled.command.slcCruiseCommand.targetMps, False)
    sm['carState'].vCruise = sm['carState'].vCruiseCluster = selected
    receipt = command_receipt(runtime, settled.command.slcCruiseCommand, 4.01,
                              30 * CV.MPH_TO_KPH, selected)
    assert observe(4.01, cruise_event=receipt).command is None
  lost = observe(4.05, available=False)
  recovered = observe(4.15)
  assert lost.command is None and recovered.command is None
  assert lost.message.slcState.hasPending == recovered.message.slcState.hasPending == manual
  assert recovered.message.slcState.acceptedMonoTime == settled.message.slcState.acceptedMonoTime
  if manual:
    assert lost.message.slcState.presentationId == 0
    assert lost.message.slcState.decisionId == recovered.message.slcState.decisionId == settled.message.slcState.decisionId
    assert lost.message.slcState.pendingSinceMonoTime == recovered.message.slcState.pendingSinceMonoTime == settled.message.slcState.pendingSinceMonoTime
  vision.speedMps = 40 * CV.MPH_TO_MS
  changed = observe(4.2)
  assert changed.message.slcState.hasPending == manual
  assert (changed.command is not None) == (not manual)
  if manual:
    assert changed.message.slcState.decisionId != settled.message.slcState.decisionId


@pytest.mark.parametrize('button,kind', [('accel', 'confirmationAccept'), ('decel', 'confirmationReject')])
def test_wheel_confirmation_does_not_follow_same_step_source_replacement(drive, button, kind):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': True}))
  pending = tick(runtime, sm, cp, 0).message.slcState
  sm['slcDashboardObservation'].episode += 1
  sm['slcDashboardObservation'].observedMonoTime = START + 40_000_000
  event = CruiseEvent(1, START + 50_000_000, 0.0, 0.0, button, 'card-producer', START + 50_000_000,
                      kind, runtime.session_id, pending.decisionId, pending.presentationId)
  output = tick(runtime, sm, cp, .05, cruise_event=event)
  assert output.message.slcState.hasPending and not output.message.slcState.hasAccepted
  assert output.message.slcState.actionStatus == 'different_presentation'
  assert output.command is None and runtime.ledger.transactions == ()


@pytest.mark.parametrize('confirmation', [False, True])
@pytest.mark.parametrize('metric,limit,offset', [(False, 45., 0.), (False, 45., 5.), (False, 45., -.4),
                                              (True, 72., 0.), (True, 72., 5.), (True, 72., -.4)])
def test_matching_set_needs_neither_confirmation_nor_command(drive, confirmation, metric, limit, offset):
  sm, cp = drive
  conversion = CV.KPH_TO_MS if metric else CV.MPH_TO_MS
  settings = replace(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': confirmation}),
                     offsets=OffsetSchedule((OffsetBand(0., None, offset * conversion),)))
  runtime = Runtime(settings, is_metric=metric)
  sm['slcDashboardObservation'].speedMps = limit * conversion
  selected = slc_target_kph((limit + offset) * conversion, metric)
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = selected
  selected = float(sm['carState'].vCruise)
  for seconds in (0, .05, 11):
    output = tick(runtime, sm, cp, seconds)
    assert not output.result.errors and not output.message.slcState.hasPending
    assert output.message.slcState.hasAccepted and output.command is None
    assert output.message.slcState.commandStatus == 'applied'
    assert sm['carState'].vCruise == selected


def test_half_unit_offset_uses_the_rounding_card_gets_after_float32_transport(drive):
  sm, cp = drive
  settings = replace(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': True}),
                     offsets=OffsetSchedule((OffsetBand(0., None, .5 / 3.6),)))
  runtime = Runtime(settings, is_metric=True)
  sm['slcDashboardObservation'].speedMps = 72 / 3.6
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = 72.
  pending = tick(runtime, sm, cp, 0).message.slcState
  assert pending.hasPending and not pending.hasAccepted
  accepted = tick(runtime, sm, cp, .05,
    request=Action(runtime.session_id, 1, pending.decisionId, pending.presentationId, 'accept'))
  assert accepted.command is not None
  helper = VCruiseHelper(cp)
  helper.apply_slc_target(accepted.command.slcCruiseCommand.targetMps, True)
  assert helper.v_cruise_kph == 73.


@pytest.mark.parametrize('confirmation', [False, True])
def test_commute_changes_only_set_speed_and_keeps_confirmation_policy(drive, confirmation):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': confirmation}))
  helper = VCruiseHelper(cp)
  selected = slc_target_kph(35 * CV.MPH_TO_MS, False)
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = selected
  for index, mph in enumerate((35, 45, 65, 55, 65, 35, 30)):
    source = sm['slcDashboardObservation']
    source.speedMps = mph * CV.MPH_TO_MS
    source.episode = index + 1
    source.observedMonoTime = START + index * 1_000_000_000
    output = tick(runtime, sm, cp, index)
    if index == 0:
      assert not output.message.slcState.hasPending and output.command is None
      continue
    if confirmation:
      pending = output.message.slcState
      assert pending.hasPending and output.command is None
      assert sm['carState'].vCruise == pytest.approx(selected)
      output = tick(runtime, sm, cp, index + .01,
        request=Action(runtime.session_id, index, pending.decisionId, pending.presentationId, 'accept'))
    assert output.command is not None
    command = output.command.slcCruiseCommand
    helper.apply_slc_target(command.targetMps, False)
    previous, selected = selected, helper.v_cruise_kph
    assert round(selected * CV.KPH_TO_MPH) == mph
    sm['carState'].vCruise = sm['carState'].vCruiseCluster = selected
    applied = tick(runtime, sm, cp, index + .02,
      cruise_event=command_receipt(runtime, command, index + .02, previous, selected, event_id=index))
    assert not applied.message.slcState.hasPending and applied.command is None


@pytest.mark.parametrize('source_name', ['Maps', 'Vision'])
def test_secondary_source_matching_set_skips_confirmation_and_command(drive, source_name):
  from openpilot.cereal import messaging
  from openpilot.starpilot.speed_limits.selection import Source
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': source_name, 'SLCConfirmation': True}),
                    vision_enabled=True, vision_control_qualified=True)
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = slc_target_kph(65 * CV.MPH_TO_MS, False)
  source = Source.MAP if source_name == 'Maps' else Source.VISION
  observations = dict.fromkeys(Source, acc.Observation(acc.ObservationKind.UNKNOWN))
  observations[source] = acc.Observation(acc.ObservationKind.VALID, acc.Candidate(source.value,
    acc.ObservationIdentity(acc.IdentityKind.GEOGRAPHIC, value='current-road'), 65 * CV.MPH_TO_MS))
  vision = messaging.new_message('slcVisionObservation').slcVisionObservation
  sm.data['slcVisionObservation'] = vision
  with patch.object(runtime, '_observations', return_value=observations):
    aligned = tick(runtime, sm, cp, 0)
  assert aligned.message.slcState.acceptedSource == source.value
  assert not aligned.message.slcState.hasPending and aligned.command is None


@pytest.mark.parametrize('selected', [65., 70.])
def test_returned_limit_only_prompts_when_it_would_change_set(drive, selected):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': True}))
  sm['slcDashboardObservation'].speedMps = 65 * CV.MPH_TO_MS
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = slc_target_kph(65 * CV.MPH_TO_MS, False)
  first = tick(runtime, sm, cp, 0).message.slcState
  tick(runtime, sm, cp, .05, request=Action(runtime.session_id, 1, 0, first.presentationId, 'adopt'))
  sm['slcDashboardObservation'].speedMps = 55 * CV.MPH_TO_MS
  assert tick(runtime, sm, cp, .1).message.slcState.hasPending
  assert tick(runtime, sm, cp, 10.1).result.acceptance.basis == 'timeout_reject'
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = slc_target_kph(selected * CV.MPH_TO_MS, False)
  sm['slcDashboardObservation'].speedMps = 65 * CV.MPH_TO_MS
  returned = tick(runtime, sm, cp, 10.2)
  assert returned.message.slcState.hasPending == (selected != 65.)
  assert returned.command is None


@pytest.mark.parametrize('action_kind', ['accept', 'reject'])
@pytest.mark.parametrize('seconds', [.05, 10.])
def test_presented_driver_choice_wins_when_set_reaches_the_proposal(drive, action_kind, seconds):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': True}))
  sm['slcDashboardObservation'].speedMps = 55 * CV.MPH_TO_MS
  pending = tick(runtime, sm, cp, 0).message.slcState
  selected = slc_target_kph(55 * CV.MPH_TO_MS, False)
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = selected
  output = tick(runtime, sm, cp, seconds,
    request=Action(runtime.session_id, 1, pending.decisionId, pending.presentationId, action_kind))
  assert output.result.acceptance.action_receipt.consumed
  assert output.result.acceptance.basis == ('driver_accept' if action_kind == 'accept' else 'driver_reject')
  assert output.command is None and sm['carState'].vCruise == selected
  held = tick(runtime, sm, cp, seconds + .05)
  assert not held.message.slcState.hasPending and held.command is None
  if action_kind == 'reject':
    assert held.result.acceptance.basis == 'rejected' and not held.message.slcState.hasAccepted


@pytest.mark.parametrize('seconds', [10., 10.001, 11.])
def test_set_alignment_cannot_accept_an_expired_confirmation(drive, seconds):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': True}))
  sm['slcDashboardObservation'].speedMps = 55 * CV.MPH_TO_MS
  pending = tick(runtime, sm, cp, 0)
  assert pending.message.slcState.hasPending
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = slc_target_kph(55 * CV.MPH_TO_MS, False)
  expired = tick(runtime, sm, cp, seconds)
  assert expired.result.acceptance.basis == 'timeout_reject'
  assert not expired.message.slcState.hasAccepted and not expired.message.slcState.hasPending
  assert expired.command is None


@pytest.mark.parametrize('resolution', ['applied', 'rejected', 'expired'])
def test_alignment_waits_for_the_previous_command_and_newer_set_evidence(drive, resolution):
  from openpilot.starpilot.speed_limits.selection import Source
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Maps', 'SLCConfirmation': True}))
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = slc_target_kph(65 * CV.MPH_TO_MS, False)
  previous = sm['carState'].vCruise
  observations = dict.fromkeys(Source, acc.Observation(acc.ObservationKind.UNKNOWN))

  def limit(mph):
    observations[Source.MAP] = acc.Observation(acc.ObservationKind.VALID, acc.Candidate('map',
      acc.ObservationIdentity(acc.IdentityKind.GEOGRAPHIC, value=f'road-{mph}'), mph * CV.MPH_TO_MS))

  with patch.object(runtime, '_observations', return_value=observations):
    limit(55)
    pending = tick(runtime, sm, cp, 0).message.slcState
    issued = tick(runtime, sm, cp, .05,
      request=Action(runtime.session_id, 1, pending.decisionId, pending.presentationId, 'accept'))
    command = issued.command.slcCruiseCommand
    limit(65)
    waiting = tick(runtime, sm, cp, .06)
    assert waiting.command is None and waiting.message.slcState.commandStatus == 'issued'
    assert runtime.commanded_acceptance.candidate.speed_mps == pytest.approx(55 * CV.MPH_TO_MS)
    if resolution != 'expired':
      selected = slc_target_kph(command.targetMps, False) if resolution == 'applied' else previous
      sm['carState'].vCruise = sm['carState'].vCruiseCluster = selected
      received = tick(runtime, sm, cp, .07, cruise_event=command_receipt(
        runtime, command, .07, previous, selected, applied=resolution == 'applied'))
      assert received.command is None
      settled = tick(runtime, sm, cp, .08)
    else:
      # An expired command could have applied after this older (still fresh) SET sample.
      now = START + 151_000_000
      sm.advance(now)
      sm.logMonoTime['carState'] = command.expiresMonoTime
      sm.logMonoTime['slcDashboardObservation'] = command.expiresMonoTime
      sm['slcDashboardObservation'].carStateLogMonoTime = command.expiresMonoTime
      stale_set = runtime.step(sm, cp, now_ns=now)
      assert stale_set.command is None and stale_set.message.slcState.commandStatus == 'expired'
      settled = tick(runtime, sm, cp, .16)
    if resolution == 'applied':
      assert settled.message.slcState.hasPending and settled.message.slcState.commandStatus == 'applied'
      assert settled.message.slcState.acceptedSpeedLimit == pytest.approx(55 * CV.MPH_TO_MS)
    else:
      assert not settled.message.slcState.hasPending and settled.command is None
      assert settled.message.slcState.acceptedSpeedLimit == pytest.approx(65 * CV.MPH_TO_MS)


def test_session_reset_does_not_forget_an_in_flight_speed_change(drive):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': True}))
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = slc_target_kph(65 * CV.MPH_TO_MS, False)
  sm['slcDashboardObservation'].speedMps = 55 * CV.MPH_TO_MS
  pending = tick(runtime, sm, cp, 0).message.slcState
  issued = tick(runtime, sm, cp, .05,
    request=Action(runtime.session_id, 1, pending.decisionId, pending.presentationId, 'accept'))
  assert issued.command is not None
  runtime.reset()
  sm['slcDashboardObservation'].speedMps = 65 * CV.MPH_TO_MS
  waiting = tick(runtime, sm, cp, .06)
  assert not waiting.message.slcState.hasAccepted and waiting.command is None
  settled = tick(runtime, sm, cp, .16)
  assert settled.message.slcState.hasAccepted and not settled.message.slcState.hasPending
  assert settled.command is None


@pytest.mark.parametrize('unavailable', ['off', 'lateral', 'stock', 'stale_set', 'stale_ego', 'unset', 'force_decel'])
def test_set_alignment_requires_current_system_speed_authority(drive, unavailable):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': True}))
  sm['slcDashboardObservation'].speedMps = 65 * CV.MPH_TO_MS
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = slc_target_kph(65 * CV.MPH_TO_MS, False)
  sm.advance(START)
  if unavailable in ('off', 'lateral', 'stock'):
    sm['carControl'].longActive = False
    sm['controlsState'].longControlState = 'off'
    if unavailable == 'stock':
      cp.openpilotLongitudinalControl = False
      sm['carState'].cruiseState.enabled = True
    else:
      sm['carControl'].enabled = sm['selfdriveState'].enabled = False
      sm['carControl'].latActive = unavailable == 'lateral'
  elif unavailable == 'stale_set':
    sm.valid['carState'] = False
  elif unavailable == 'stale_ego':
    sm['carState'].vEgoCluster = float('nan')
  elif unavailable == 'unset':
    sm['carState'].vCruise = sm['carState'].vCruiseCluster = 255.
  else:
    sm['controlsState'].forceDecel = True
  output = runtime.step(sm, cp, now_ns=START)
  assert not output.message.slcState.hasAccepted and output.command is None


def test_reaching_actual_speed_does_not_accept_a_different_set_target(drive):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': True}))
  sm['slcDashboardObservation'].speedMps = 45 * CV.MPH_TO_MS
  sm['carState'].vEgo = sm['carState'].vEgoCluster = 45 * CV.MPH_TO_MS
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = slc_target_kph(65 * CV.MPH_TO_MS, False)
  output = tick(runtime, sm, cp, 0)
  assert output.message.slcState.hasPending and not output.message.slcState.hasAccepted and output.command is None


def test_matching_new_limit_reconciles_an_old_manual_override_without_changing_set(drive):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': True}))
  sm['slcDashboardObservation'].speedMps = 65 * CV.MPH_TO_MS
  baseline = slc_target_kph(65 * CV.MPH_TO_MS, False)
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = baseline
  first = tick(runtime, sm, cp, 0)
  assert not first.message.slcState.hasPending
  selected = slc_target_kph(70 * CV.MPH_TO_MS, False)
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = selected
  selected = float(sm['carState'].vCruise)
  changed = tick(runtime, sm, cp, .05, cruise_event=CruiseEvent(1, START + 50_000_000,
    baseline / 3.6, selected / 3.6, 'accel', 'card-producer', START + 50_000_000))
  assert changed.message.slcState.driverOverrideActive and changed.command is None
  sm['slcDashboardObservation'].speedMps = 70 * CV.MPH_TO_MS
  aligned = tick(runtime, sm, cp, .1)
  assert not aligned.message.slcState.hasPending and not aligned.message.slcState.driverOverrideActive
  assert aligned.command is None and sm['carState'].vCruise == selected


@pytest.mark.parametrize('direction', [-1, 1])
def test_matching_limit_keeps_wheel_buttons_available_for_normal_set_changes(drive, direction):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': True}))
  sm['slcDashboardObservation'].speedMps = 65 * CV.MPH_TO_MS
  selected = slc_target_kph(65 * CV.MPH_TO_MS, False)
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = selected
  output = tick(runtime, sm, cp, 0)
  pending = physical_actions.pending_confirmation(ReplaySM({'slcState': output.message.slcState}, START), START, long_active=True)
  assert pending is None
  helper = VCruiseHelper(cp)
  helper.v_cruise_kph = selected
  button = 'accelCruise' if direction > 0 else 'decelCruise'
  cs = car.CarState(cruiseState={'available': True}, buttonEvents=[car.CarState.ButtonEvent(type=button, pressed=True)])
  helper.update_v_cruise(cs, True, False, pending, slc_enabled=True)
  assert helper.slc_consumed_button is None
  cs.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=False)]
  helper.update_v_cruise(cs, True, False, slc_enabled=True)
  assert helper.v_cruise_kph == pytest.approx(round(selected + direction * round(CV.MPH_TO_KPH, 1), 1))


@pytest.mark.parametrize('failure', ['source_refresh', 'expiry'])
def test_failed_adoption_retries_with_current_evidence_and_stops_after_application(drive, failure):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': True}))
  pending = tick(runtime, sm, cp, 0).message.slcState
  first = tick(runtime, sm, cp, 1, request=Action(runtime.session_id, 17, pending.decisionId, pending.presentationId, 'accept'))
  command = first.command.slcCruiseCommand
  sm['slcDashboardObservation'].observedMonoTime = START + 1_010_000_000
  if failure == 'source_refresh':
    retry = tick(runtime, sm, cp, 1.05, cruise_event=command_receipt(runtime, command, 1.05, 60., 60., applied=False))
  else:
    retry = tick(runtime, sm, cp, 1.15)
  assert retry.command is not None
  current = retry.message.slcState
  retried = retry.command.slcCruiseCommand
  assert retried.commandId > command.commandId
  assert current.commandActionSequenceId == 17
  evidence = sm['slcDashboardObservation']
  observation = SimpleNamespace(status=Status.VALID, speed_mps=evidence.speedMps, episode=evidence.episode,
                                observed_ns=evidence.observedMonoTime, valid_until_ns=evidence.validUntilMonoTime)
  assert physical_actions.command_applicable(retried, current, observation, 'card-producer',
    int(retry.message.logMonoTime), 60 / 3.6, long_active=True, button_event=False)
  applied_at = 1.2 if failure == 'expiry' else 1.1
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = 90.
  applied = tick(runtime, sm, cp, applied_at,
    cruise_event=command_receipt(runtime, retried, applied_at, 60., 90., event_id=2))
  assert applied.message.slcState.commandStatus == 'applied' and applied.command is None
  assert tick(runtime, sm, cp, 2).command is None


@pytest.mark.parametrize('change', ['manual', 'unclassified', 'source', 'returned_source', 'disengaged'])
def test_expired_adoption_does_not_revive_superseded_commands(drive, change):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard'}))
  tick(runtime, sm, cp, 0)
  old_command = tick(runtime, sm, cp, 3).command.slcCruiseCommand
  kwargs = {}
  if change in ('manual', 'unclassified'):
    sm['carState'].vCruise = sm['carState'].vCruiseCluster = 61.
    if change == 'manual':
      kwargs['cruise_event'] = CruiseEvent(1, START + 3_200_000_000, 60 / 3.6, 61 / 3.6,
                                          'accel', 'card-producer', START + 3_200_000_000)
  elif change == 'source':
    sm['slcDashboardObservation'].speedMps = 20.
  elif change == 'returned_source':
    sm['slcDashboardObservation'].speedMps = 20.
    tick(runtime, sm, cp, 3.05)
    sm['slcDashboardObservation'].speedMps = 25.
  else:
    sm['selfdriveState'].enabled = sm['carControl'].enabled = sm['carControl'].longActive = False
    sm['controlsState'].longControlState = 'off'
  result = tick(runtime, sm, cp, 3.2, **kwargs)
  if change in ('source', 'returned_source'):
    assert result.message.slcState.acceptedMonoTime == START + 3_200_000_000
    assert result.command.slcCruiseCommand.commandId > old_command.commandId
    assert result.command.slcCruiseCommand.targetMps == (20. if change == 'source' else 25.)
  else:
    assert result.command is None


@pytest.mark.parametrize('failure', ['rejected', 'expired'])
@pytest.mark.parametrize('response', ['reject', 'timeout'])
def test_returned_limit_cannot_retry_an_older_adoption_after_decline(drive, failure, response):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': True}))
  pending = tick(runtime, sm, cp, 0).message.slcState
  first = tick(runtime, sm, cp, 1, request=Action(runtime.session_id, 1, pending.decisionId, pending.presentationId, 'accept'))
  command = first.command.slcCruiseCommand
  sm['slcDashboardObservation'].speedMps = 20.
  receipt = command_receipt(runtime, command, 1.05, 60., 60., applied=False) if failure == 'rejected' else None
  tick(runtime, sm, cp, 1.05, cruise_event=receipt)
  sm['slcDashboardObservation'].speedMps = 25.
  pending = tick(runtime, sm, cp, 4).message.slcState
  action = Action(runtime.session_id, 2, pending.decisionId, pending.presentationId, 'reject') if response == 'reject' else None
  seconds = 5 if action else 14
  declined = tick(runtime, sm, cp, seconds, request=action)
  assert declined.result.acceptance.basis == ('driver_reject' if action else 'timeout_reject')
  assert declined.command is None
  held = tick(runtime, sm, cp, seconds + .1)
  assert not held.result.errors and not runtime.state.reset_required and held.command is None
  assert sm['carState'].vCruise == 60.
  # An explicit later adoption remains available after declining the new decision.
  current = declined.message.slcState
  readopted = tick(runtime, sm, cp, seconds + .2,
    request=Action(runtime.session_id, 3, 0, current.presentationId, 'adopt'))
  assert readopted.command is not None and readopted.command.slcCruiseCommand.targetMps == 25.


@pytest.mark.parametrize('limit,offset,bounded', [(140., 10., 145.), (10., -5., 8.)])
@pytest.mark.parametrize('metric', [False, True])
def test_adoption_and_display_use_existing_cruise_bounds(drive, limit, offset, bounded, metric):
  sm, cp = drive
  sm['slcDashboardObservation'].speedMps = limit / 3.6
  settings = replace(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard'}),
                     offsets=OffsetSchedule((OffsetBand(0., None, offset / 3.6),)))
  runtime = Runtime(settings)
  tick(runtime, sm, cp, 0)
  output = tick(runtime, sm, cp, 3)
  assert not output.result.errors and output.command is not None
  command, state = output.command.slcCruiseCommand, output.message.slcState
  assert command.targetMps == pytest.approx(bounded / 3.6)
  assert state.acceptedAdjustedLimit == pytest.approx(bounded / 3.6)
  assert state.offset == pytest.approx((bounded - limit) / 3.6)
  evidence = sm['slcDashboardObservation']
  observation = SimpleNamespace(status=Status.VALID, speed_mps=evidence.speedMps, episode=evidence.episode,
                                observed_ns=evidence.observedMonoTime, valid_until_ns=evidence.validUntilMonoTime)
  assert physical_actions.command_applicable(command, state, observation, 'card-producer', START + 3_000_000_000,
                                             60 / 3.6, long_active=True, button_event=False)
  helper = VCruiseHelper(cp)
  helper.apply_slc_target(command.targetMps, metric)
  assert 8 <= helper.v_cruise_kph <= 145


@pytest.mark.parametrize('metric,display', [(True, 72), (False, 55), (False, 60), (False, 65), (False, 70)])
@pytest.mark.parametrize('direction', [-1, 1])
def test_manual_override_compares_against_the_applied_rounded_set_speed(drive, metric, display, direction):
  sm, cp = drive
  cp.pcmCruise = False
  sm['slcDashboardObservation'].speedMps = 45 * CV.MPH_TO_MS if metric else display * CV.MPH_TO_MS
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'IsMetric': metric}))
  tick(runtime, sm, cp, 0)
  adopted = tick(runtime, sm, cp, 3)
  helper = VCruiseHelper(cp)
  helper.apply_slc_target(adopted.command.slcCruiseCommand.targetMps, metric)
  baseline = helper.v_cruise_kph
  conversion = 1 if metric else CV.KPH_TO_MPH
  assert round(baseline * conversion) == display
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = baseline
  tick(runtime, sm, cp, 3.05, cruise_event=command_receipt(runtime, adopted.command.slcCruiseCommand, 3.05, 60., baseline))
  for event_id, (step, distance) in enumerate(zip((direction, direction, -direction, -direction), (1, 2, 1, 0), strict=True), 2):
    previous = float(helper.v_cruise_kph)
    helper.adjust_v_cruise(car.CarState.ButtonEvent.Type.accelCruise if step > 0 else
                          car.CarState.ButtonEvent.Type.decelCruise, sm['carState'], metric)
    chosen = float(helper.v_cruise_kph)
    assert round(chosen * conversion) == display + direction * distance
    sm['carState'].vCruise = sm['carState'].vCruiseCluster = chosen
    seconds = 3.05 + event_id * .05
    stamp = START + round(seconds * 1e9)
    output = tick(runtime, sm, cp, seconds, cruise_event=CruiseEvent(event_id, stamp, previous / 3.6,
      chosen / 3.6, 'accel' if chosen > previous else 'decel', 'card-producer', stamp))
    assert output.result.override.event_receipt.consumed
    assert output.message.slcState.driverOverrideActive == (distance != 0)
    assert output.command is None
  assert helper.v_cruise_kph == pytest.approx(baseline, abs=1e-6)


@pytest.mark.parametrize('fallback', [0, 1, 2, None])
def test_source_loss_preserves_latest_received_limit_and_offset_without_actions(drive, fallback):
  from openpilot.starpilot.ui.onroad_state import OnroadState, speed_limit_from_message, slc_controls
  from openpilot.starpilot.ui.presentation import Profile
  from openpilot.starpilot.ui.unified_speed_presentation import resolve_unified_speed
  sm, cp = drive
  settings = replace(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': True, 'SLCFallback': fallback}),
                     offsets=OffsetSchedule((OffsetBand(0., None, 2 / 3.6),)))
  runtime = Runtime(settings)
  first = tick(runtime, sm, cp, 0).message.slcState
  tick(runtime, sm, cp, 1, request=Action(runtime.session_id, 1, first.decisionId, first.presentationId, 'accept'))
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = 92.
  sm['slcDashboardObservation'].speedMps = 20.
  newer = tick(runtime, sm, cp, 2).message.slcState
  tick(runtime, sm, cp, 2.1, request=Action(runtime.session_id, 2, newer.decisionId, newer.presentationId, 'reject'))
  sm['slcDashboardObservation'].status = 'unknown'
  lost = tick(runtime, sm, cp, 2.2)
  observation = speed_limit_from_message(lost.message.slcState)
  screen = OnroadState(True, False, 20., 92., observation, metric=True)
  shown = resolve_unified_speed(screen)
  assert (shown.posted_text, shown.offset_text, shown.source, shown.status) == ('72', '+2', 'dashboard', 'Unavailable')
  assert not shown.pending and lost.command is None
  for profile in Profile:
    assert not slc_controls(profile, replace(screen, slc_prompt_open=True))
  runtime.reset()
  reset = tick(runtime, sm, cp, 2.3)
  assert resolve_unified_speed(replace(screen, speed_limit=speed_limit_from_message(reset.message.slcState))).posted_text == '–'


@pytest.mark.parametrize('limit', [12., 25.])
@pytest.mark.parametrize('pcm', [False, True])
def test_automatic_adoption_updates_set_speed_up_or_down_immediately(drive, limit, pcm):
  from openpilot.starpilot.ui.onroad_state import OnroadState, speed_limit_from_message
  from openpilot.starpilot.ui.speed_limit_pulse import SpeedLimitPulse
  sm, cp = drive
  cp.pcmCruise = pcm
  sm['slcDashboardObservation'].speedMps = limit
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard'}))
  adopted = tick(runtime, sm, cp, 0)
  assert adopted.message.slcState.hasAccepted
  assert not adopted.message.slcState.automaticAdoptionPending
  assert adopted.message.slcState.pendingSinceMonoTime == 0
  assert adopted.command is not None
  assert adopted.command.slcCruiseCommand.targetMps == pytest.approx(limit)
  assert adopted.result.ceiling is None and not adopted.message.slcState.hasCeiling
  assert not adopted.message.slcState.hasPending
  state = adopted.message.slcState
  evidence = sm['slcDashboardObservation']
  observation = SimpleNamespace(status=Status.VALID, speed_mps=limit, episode=evidence.episode,
                                observed_ns=evidence.observedMonoTime, valid_until_ns=evidence.validUntilMonoTime)
  current = physical_actions.state_current(ReplaySM({'slcState': state}, START), observation, 'card-producer', START)
  assert physical_actions.command_applicable(adopted.command.slcCruiseCommand, current, observation, 'card-producer',
    START, 60 / 3.6, long_active=True, button_event=False)
  helper = VCruiseHelper(cp)
  helper.v_cruise_kph = 60.
  helper.apply_slc_target(limit, True)
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = helper.v_cruise_kph
  assert helper.v_cruise_kph == round(limit * 3.6)
  pulse = SpeedLimitPulse()
  pulse.update(OnroadState(True, False, 20., helper.v_cruise_kph, speed_limit_from_message(state)), START / 1e9)
  assert not pulse.display_pulsing and pulse.start_time == -float('inf')
  assert tick(runtime, sm, cp, 0.05).command is None


@pytest.mark.parametrize('response', ['accept', 'reject', 'timeout'])
def test_confirmation_outcomes_preserve_set_speed_until_acceptance(drive, response):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCConfirmation': True, 'SLCPriority1': 'Dashboard'}))
  pending = tick(runtime, sm, cp, 0).message.slcState
  assert pending.hasPending and not pending.automaticAdoptionPending
  action = Action(runtime.session_id, 1, pending.decisionId, pending.presentationId, response) if response != 'timeout' else None
  output = tick(runtime, sm, cp, 10 if action is None else 1, request=action)
  assert not output.message.slcState.hasPending
  assert (output.command is not None) == (response == 'accept')
  assert sm['carState'].vCruise == 60.
  if response == 'accept':
    sm['carState'].vCruise = sm['carState'].vCruiseCluster = 90.
    tick(runtime, sm, cp, 1.05, cruise_event=command_receipt(runtime, output.command.slcCruiseCommand, 1.05, 60., 90.))
  assert tick(runtime, sm, cp, 11).command is None
  assert not tick(runtime, sm, cp, 12).message.slcState.hasPending


@pytest.mark.parametrize('selected', [50., 100.])
def test_new_limits_still_adopt_during_manual_override_in_either_direction(drive, selected):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard'}))
  tick(runtime, sm, cp, 0)
  tick(runtime, sm, cp, 3)
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = selected
  changed = tick(runtime, sm, cp, 3.1, cruise_event=CruiseEvent(1, START + 3_100_000_000, 90 / 3.6,
    selected / 3.6, 'accel' if selected > 90 else 'decel', 'card-producer', START + 3_100_000_000))
  assert changed.message.slcState.driverOverrideActive
  sm['slcDashboardObservation'].speedMps = 18.
  adopted = tick(runtime, sm, cp, 3.2)
  assert not adopted.message.slcState.hasPending
  assert adopted.command.slcCruiseCommand.targetMps == pytest.approx(18.)
  assert not adopted.message.slcState.driverOverrideActive


def test_accelerator_does_not_change_set_speed_or_manual_override_and_release_keeps_profile(drive):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard'}))
  tick(runtime, sm, cp, 0)
  tick(runtime, sm, cp, 3)
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = 90.
  sm['carState'].gasPressed = True
  sm['carState'].vEgo = sm['carState'].vEgoCluster = 30.
  pressed = tick(runtime, sm, cp, 4)
  assert not pressed.message.slcState.driverOverrideActive
  assert sm['carState'].vCruise == 90. and pressed.command is None
  sm['carState'].gasPressed = False
  released = tick(runtime, sm, cp, 5)
  assert not released.message.slcState.driverOverrideActive and released.result.ceiling is None
  native = planner.LongitudinalPlanner(cp)
  with patch.object(planner, 'get_cruise_accel', wraps=planner.get_cruise_accel) as cruise:
    native.update(sm, global_braking_response='eco')
  assert cruise.call_args.args[1] == 25.
  assert cruise.call_args.kwargs['base_brake_floor'] == -.6
  assert native.last_cruise_ceiling_status == 'absent'


def test_pcm_software_set_speed_survives_native_speed_and_consumes_confirmation(drive):
  _, cp = drive
  cp.pcmCruise = True
  helper = VCruiseHelper(cp)
  cs = car.CarState(cruiseState={'available': True, 'enabled': True, 'speed': 60 / 3.6})
  helper.update_v_cruise(cs, True, True, slc_enabled=True)
  helper.apply_slc_target(25., True)
  helper.update_v_cruise(cs, True, True, slc_enabled=True)
  assert helper.v_cruise_kph == helper.v_cruise_cluster_kph == 90.
  from openpilot.selfdrive.car.cruise import SlcPendingConfirmation
  pending = SlcPendingConfirmation('drive', 1, 1)
  cs.buttonEvents = [car.CarState.ButtonEvent(type='decelCruise', pressed=True)]
  helper.update_v_cruise(cs, True, True, pending, slc_enabled=True)
  assert helper.slc_consumed_button.button == 'decel'
  cs.cruiseState.speed = 59 / 3.6
  cs.buttonEvents = [car.CarState.ButtonEvent(type='decelCruise', pressed=False)]
  helper.update_v_cruise(cs, True, True, slc_enabled=True)
  assert helper.v_cruise_kph == 90.
  helper.update_v_cruise(cs, True, True, slc_enabled=False)
  assert helper.v_cruise_kph == pytest.approx(59.)


@pytest.mark.parametrize('pending', [False, True])
@pytest.mark.parametrize('signal,direction,normal_speed', [
  ('CcAslButtnSetIncPress', 'accel', 61.), ('CcAslButtnSetDecPress', 'decel', 59.),
])
def test_ford_parser_buttons_adjust_set_speed_or_confirm_without_a_second_step(pending, signal, direction, normal_speed):
  from opendbc.can import CANPacker
  from opendbc.car import Bus, gen_empty_fingerprint
  from opendbc.car.ford.carstate import CarState
  from opendbc.car.ford.interface import CarInterface
  from opendbc.car.ford.values import CAR, DBC
  from openpilot.selfdrive.car.cruise import CRUISE_LONG_PRESS, SlcPendingConfirmation

  cp = CarInterface.get_params(CAR.FORD_ESCAPE_MK4, gen_empty_fingerprint(), [], True, False, False)
  source = CarState(cp)
  parsers = source.get_can_parsers(cp)
  packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
  helper = VCruiseHelper(cp)
  choice = SlcPendingConfirmation('drive', 1, 1) if pending else None
  now_ns = START

  def frame(pressed, decision=None):
    nonlocal now_ns
    parsers[Bus.pt].update([(now_ns, [
      packer.make_can_msg('Steering_Data_FD1', parsers[Bus.pt].bus, {signal: pressed}),
      packer.make_can_msg('EngBrakeData', parsers[Bus.pt].bus, {'CcStat_D_Actl': 4, 'Veh_V_DsplyCcSet': 60}),
    ])])
    now_ns += 10_000_000
    helper.update_v_cruise(source.update(parsers), True, True, decision, slc_enabled=True)

  for _ in range(3):
    frame(0)
  helper.apply_slc_target(60. / 3.6, True)
  frame(1, choice)
  consumed = helper.slc_consumed_button
  assert (consumed is not None) == pending
  if pending:
    assert consumed.pending == choice and consumed.button == direction
    if direction == 'accel':
      helper.apply_slc_target(25., True)
    for _ in range(CRUISE_LONG_PRESS + 1):
      frame(1)
      assert helper.slc_consumed_button is None and helper.slc_cruise_change is None
  frame(0)
  assert helper.v_cruise_kph == (90. if pending and direction == 'accel' else 60. if pending else normal_speed)
  assert (helper.slc_cruise_change is None) == pending


def test_automatic_adoption_does_not_consume_confirmation_actions_and_late_manual_accept_is_declined():
  candidate = acc.Candidate('dashboard', acc.ObservationIdentity(acc.IdentityKind.SESSION_VALUE, session_id='drive'), 20.)
  observation = acc.Observation(acc.ObservationKind.VALID, candidate)
  authority = acc.Authority(acc.Mode.LONGITUDINAL_ONLY, acc.LongitudinalOwner.SYSTEM, False, True, False, False)
  for automatic in (False, True):
    policy = acc.Policy(not automatic, not automatic)
    first = acc.step(acc.new_session('drive'), observation, authority, policy, now_ns=0)
    action = acc.DriverAction('drive', 1, first.state.next_decision_id - 1, acc.ActionKind.ACCEPT)
    output = acc.step(first.state, observation, authority, policy, now_ns=1 if automatic else acc.CONFIRMATION_NS + 1, action=action)
    assert not output.action_receipt.consumed
    assert (output.state.accepted is not None) == automatic


@pytest.mark.parametrize('source_name', ['map', 'vision'])
def test_map_and_vision_adoption_commands_bind_the_current_source_without_dashboard_limit(drive, source_name):
  from openpilot.cereal import messaging
  from openpilot.starpilot.speed_limits.selection import Source
  sm, cp = drive
  sm['slcDashboardObservation'].status = 'unknown'
  evidence = messaging.new_message('slcVisionObservation').slcVisionObservation
  evidence.vision.producerSessionId = 'vision-producer'
  evidence.vision.episode = 1
  evidence.vision.observedMonoTime = START
  evidence.vision.validUntilMonoTime = START + 10_000_000_000
  sm.data['slcVisionObservation'] = evidence
  source = Source(source_name)
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Maps' if source == Source.MAP else 'Vision'}),
                    vision_enabled=True, vision_control_qualified=True)
  candidate = acc.Candidate(source_name, acc.ObservationIdentity(acc.IdentityKind.GEOGRAPHIC, value='qualified-source'), 20.)
  observations = dict.fromkeys(Source, acc.Observation(acc.ObservationKind.ABSENT))
  observations[source] = acc.Observation(acc.ObservationKind.VALID, candidate)
  with patch.object(runtime, '_observations', return_value=observations):
    tick(runtime, sm, cp, 0)
    output = tick(runtime, sm, cp, 3)
  assert output.command is not None, (output.result.errors, output.result.status, output.result.acceptance, runtime.settings.errors)
  command = output.command.slcCruiseCommand
  assert command.source == source_name
  current = physical_actions.state_current(ReplaySM({'slcState': output.message.slcState}, START + 3_000_000_000),
                                           None, 'card-producer', START + 3_000_000_000)
  assert physical_actions.command_applicable(command, current, None, 'card-producer', START + 3_000_000_000,
                                             60 / 3.6, long_active=True, button_event=False)
  command.source = 'dashboard'
  assert not physical_actions.command_applicable(command, current, None, 'card-producer', START + 3_000_000_000,
                                                 60 / 3.6, long_active=True, button_event=False)


def test_offset_edit_does_not_cancel_manual_override(drive):
  from openpilot.starpilot.speed_limits.speed_domain import OffsetBand, OffsetSchedule
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard'}))
  tick(runtime, sm, cp, 0)
  tick(runtime, sm, cp, 3)
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = 100.
  tick(runtime, sm, cp, 3.1, cruise_event=CruiseEvent(1, START + 3_100_000_000, 90 / 3.6, 100 / 3.6, 'accel',
                                                   'card-producer', START + 3_100_000_000))
  runtime.update_offsets(OffsetSchedule((OffsetBand(0., None, 1.),)))
  output = tick(runtime, sm, cp, 3.2)
  assert output.command is None and output.message.slcState.driverOverrideActive
  assert sm['carState'].vCruise == 100.


@pytest.mark.parametrize('confirmation', [False, True])
def test_new_limit_can_be_adopted_while_accelerator_temporarily_suspends_longitudinal_output(drive, confirmation):
  sm, cp = drive
  sm['carState'].gasPressed = True
  sm['carControl'].longActive = False
  sm['controlsState'].longControlState = 'off'
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCConfirmation': confirmation}))
  first = tick(runtime, sm, cp, 0).message.slcState
  action = Action(runtime.session_id, 1, first.decisionId, first.presentationId, 'accept') if confirmation else None
  output = tick(runtime, sm, cp, 1 if confirmation else 3, request=action)
  assert output.command is not None
  assert output.command.slcCruiseCommand.targetMps == 25.
  assert not output.message.slcState.driverOverrideActive
  assert not output.result.acceptance.authority.longitudinal_active
  assert output.result.acceptance.authority.accelerator_override
  assert output.result.ceiling is None


def test_manual_changes_during_source_loss_remain_overrides_after_reconnection(drive):
  sm, cp = drive
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard', 'SLCFallback': 0}))
  tick(runtime, sm, cp, 0)
  tick(runtime, sm, cp, 3)
  sm['slcDashboardObservation'].status = 'unknown'
  tick(runtime, sm, cp, 3.1)
  sm['carState'].vCruise = sm['carState'].vCruiseCluster = 100.
  tick(runtime, sm, cp, 3.2, cruise_event=CruiseEvent(1, START + 3_200_000_000, 90 / 3.6, 100 / 3.6, 'accel',
                                                   'card-producer', START + 3_200_000_000))
  sm['slcDashboardObservation'].status = 'valid'
  output = tick(runtime, sm, cp, 3.3)
  assert output.message.slcState.driverOverrideActive and output.command is None
  assert sm['carState'].vCruise == 100.


def test_pcm_confirmation_release_is_retired_even_if_slc_is_switched_off(drive):
  from openpilot.selfdrive.car.cruise import SlcPendingConfirmation
  _, cp = drive
  cp.pcmCruise = True
  helper = VCruiseHelper(cp)
  cs = car.CarState(cruiseState={'available': True, 'speed': 20.},
                     buttonEvents=[car.CarState.ButtonEvent(type='accelCruise', pressed=True)])
  helper.update_v_cruise(cs, True, True, SlcPendingConfirmation('drive', 1, 1), slc_enabled=True)
  assert helper.slc_suppressed_buttons
  cs.buttonEvents = [car.CarState.ButtonEvent(type='accelCruise', pressed=False)]
  helper.update_v_cruise(cs, True, True, slc_enabled=False)
  assert not helper.slc_suppressed_buttons
  assert not any(helper.button_timers.values())
