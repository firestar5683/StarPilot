from types import SimpleNamespace as NS
from unittest.mock import Mock
from typing import cast

import pytest

from openpilot.starpilot.drive_state.control import DriveStateControl
from openpilot.starpilot.drive_state.owner import DriveStateOwner, Mode, Rejected
from openpilot.starpilot.drive_state.tests.test_owner import Params, BOOT
from openpilot.starpilot.drive_state.evidence import PhysicalSource
from openpilot.starpilot.drive_state.tests.test_evidence import Messages


@pytest.fixture
def fixture():
  now = [1_000_000_000, 10_000_000_000]
  messages = Messages()
  source = PhysicalSource(messages, mono=lambda: now[0], boot=lambda: sum(now))
  now[0] = 2_100_000_000
  try:
    yield NS(now=now, sm=messages, source=source)
  finally:
    source.close()


def test_force_onroad_never_uses_park_admission(tmp_path):
  params = Params()
  owner = DriveStateOwner(params, tmp_path / 'owner', alive=lambda _: True)
  owner.initialize(pid=1, birth=2, boot=BOOT)
  physical = Mock(side_effect=AssertionError('Onroad does not require Park'))
  revision = owner.snapshot().revision
  assert revision is not None
  state = owner.request('onroad', expected_revision=revision,
                        authorized=lambda: True, override_allowed=physical)
  assert state.mode == Mode.ONROAD
  physical.assert_not_called()


def test_force_offroad_rechecks_actual_park_before_commit(tmp_path):
  params = Params()
  owner = DriveStateOwner(params, tmp_path / 'owner', alive=lambda _: True)
  owner.initialize(pid=1, birth=2, boot=BOOT)
  baseline = list(params.writes)
  revision = owner.snapshot().revision
  assert revision is not None
  with pytest.raises(Rejected, match='Park'):
    owner.request('offroad', expected_revision=revision,
                  authorized=lambda: True, override_allowed=lambda: False)
  assert params.writes == baseline
  values = iter((True, False))
  revision = owner.snapshot().revision
  assert revision is not None
  with pytest.raises(Rejected):
    owner.request('offroad', expected_revision=revision,
                  authorized=lambda: True, override_allowed=lambda: next(values))
  assert params.writes == baseline


def test_requested_mode_never_claims_actual_update_authority(tmp_path):
  params = Params()
  owner = DriveStateOwner(params, tmp_path / 'owner', alive=lambda _: True)
  owner.initialize(pid=1, birth=2, boot=BOOT)
  physical = NS(allowed=lambda: False)
  control = DriveStateControl(owner, physical, effective=lambda: False)
  state = control.snapshot()
  assert not state['overrideAllowed']
  assert control.next_mode(state) == Mode.ONROAD
  control.change('onroad', state['revision'], lambda: True)
  assert control.snapshot()['mode'] == 'onroad'
  assert control.snapshot()['effective'] == 'offroad'


def test_normal_garage_flow_current_nooutput_and_manager_offroad(fixture):
  f = fixture
  f.sm.values['deviceState'] = NS(started=False)
  for table, value in ((f.sm.seen, True), (f.sm.alive, True), (f.sm.valid, True),
                       (f.sm.logMonoTime, 2_000_000_000), (f.sm.recv_time, 2.0)):
    table['deviceState'] = value
  assert f.source.allowed()
  assert f.source.update_ready(True)
  assert not f.source.update_ready(False)
  f.sm.values['deviceState'].started = True
  assert not f.source.update_ready(True)
  f.sm.values['deviceState'].started = False
  f.sm.values['pandaStates'][0].controlsAllowed = True
  assert not f.source.update_ready(True)


def test_forced_offroad_does_not_borrow_old_park_while_ignition_on(fixture):
  f = fixture
  f.sm.values['pandaStates'][0].ignitionLine = True
  f.sm.values['deviceState'] = NS(started=False)
  f.sm.logMonoTime['carState'] = 1_000_000_000
  status = f.source.update_status(True)
  assert not status['allowed']
  assert 'ignition' in status['reason']
  f.sm.values['pandaStates'][0].ignitionLine = False
  for table, value in ((f.sm.seen, True), (f.sm.alive, True), (f.sm.valid, True),
                       (f.sm.logMonoTime, 2_000_000_000), (f.sm.recv_time, 2.0)):
    table['deviceState'] = value
  assert f.source.update_ready(True)


@pytest.mark.parametrize('fault', ['moving', 'drive_gear', 'can_invalid', 'enabled', 'active'])
def test_live_park_guards_remain_authoritative(fixture, fault):
  f = fixture
  f.sm.values['pandaStates'][0].ignitionLine = True
  if fault == 'moving':
    f.sm.values['carState'].standstill = False
  elif fault == 'drive_gear':
    f.sm.values['carState'].gearShifter = 'drive'
  elif fault == 'can_invalid':
    f.sm.values['carState'].canValid = False
  else:
    setattr(f.sm.values['selfdriveState'], fault, True)
  assert not f.source.allowed()


def test_authenticated_remote_force_drive_modes_use_shared_owner():
  from contextlib import ExitStack
  from openpilot.starpilot.drive_state.tests.test_http import ForceHttpTest
  case = ForceHttpTest(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    case.setUp()
    case.allowed = False
    result = case.drive_action('onroad', remote=True)
    assert result[0] == 200 and result[1]['mode'] == 'onroad'
    assert result[1]['effective'] == 'offroad'
    assert case.drive_action('offroad', remote=True)[0] == 409
    assert case.drive.snapshot().mode == Mode.ONROAD
    case.allowed = True
    result = case.drive_action('offroad', remote=True)
    assert result[0] == 200 and result[1]['mode'] == 'offroad'


def test_update_snapshot_keeps_one_admission_and_matching_reason():
  from contextlib import ExitStack
  from openpilot.starpilot.galaxy.tests.test_software_operations import SoftwareOperationsTest
  case = SoftwareOperationsTest(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    case.setUp()
    context = NS(update_status=Mock(side_effect=[{'allowed': False, 'reason': 'Current Panda status is stale'},
                                               {'allowed': True, 'reason': None}]), close=Mock())
    case.owner.context = cast(PhysicalSource, context)
    case.owner.parked = lambda: context.update_status(True)['allowed']
    view = case.owner.snapshot(include_history=False)
    assert not view['parked'] and not view['canFastUpdate'] and not view['canInstall']
    assert view['reason'] == 'Current Panda status is stale'
    context.update_status.assert_called_once_with(True)
