from types import SimpleNamespace
from unittest import mock

import pytest
from opendbc.car import structs
from openpilot.starpilot.controllers import wheel_actions


@pytest.mark.parametrize('reason', ('passive', 'not_car', 'dashcam', 'invalid_can', 'can_timeout', 'drive_zero'))
def test_rejected_source_does_not_read_assignment_files(reason):
  owner = wheel_actions.WheelPublisher()
  cp = SimpleNamespace(notCar=reason == 'not_car', passive=reason == 'passive',
                       dashcamOnly=reason == 'dashcam', carFingerprint='HYUNDAI IONIQ 6 2023')
  state = structs.CarState(canValid=reason != 'invalid_can', canTimeout=reason == 'can_timeout')
  drive = 0 if reason == 'drive_zero' else 1
  with mock.patch.object(wheel_actions, 'capture', side_effect=AssertionError('rejected source entered filesystem')) as reads:
    assert owner.observe(object(), cp, state, now_ns=10, drive_id=drive) == ()
  reads.assert_not_called()
  assert owner.mapping is None and owner.checked_ns == 10
  assert owner.tracker.distance_held is False


def test_eligible_source_still_reads_and_failed_read_denies():
  owner = wheel_actions.WheelPublisher()
  cp = SimpleNamespace(notCar=False, passive=False, dashcamOnly=False, carFingerprint='HYUNDAI IONIQ 6 2023')
  with mock.patch.object(wheel_actions, 'capture', return_value=None) as reads:
    assert owner.observe(object(), cp, structs.CarState(canValid=True), now_ns=10, drive_id=1) == ()
  reads.assert_called_once()
  assert owner.mapping is None and owner.checked_ns == 10


@pytest.fixture
def real_context(tmp_path):
  from openpilot.common.params import Params
  from openpilot.selfdrive.car.tests.test_hyundai_aol import candidate
  params = Params(str(tmp_path))
  _, cp = candidate(False)
  return params, cp


def test_invalid_source_recovery_recaptures_and_rejects_held_release(real_context):
  from openpilot.starpilot.controllers.tests.test_wheel_actions import DRIVE, NOW, state
  params, cp = real_context
  params.put('DistanceButtonControl', 8, block=True)
  owner = wheel_actions.WheelPublisher()
  owner.observe(params, cp, state(), now_ns=NOW, drive_id=DRIVE)
  owner.observe(params, cp, state(True), now_ns=NOW + 10_000_000, drive_id=DRIVE)
  assert owner.tracker.distance_held
  invalid = state()
  invalid.canValid = False
  with mock.patch.object(wheel_actions, 'capture', wraps=wheel_actions.capture) as reads:
    assert owner.observe(params, cp, invalid, now_ns=NOW + 20_000_000, drive_id=DRIVE) == ()
  reads.assert_not_called()
  assert owner.mapping is None and not owner.tracker.distance_held
  params.put('DistanceButtonControl', 12, block=True)
  with mock.patch.object(wheel_actions, 'capture', wraps=wheel_actions.capture) as reads:
    commands = owner.observe(params, cp, state(False), now_ns=NOW + 30_000_000, drive_id=DRIVE)
  reads.assert_called_once_with(params)
  assert owner.mapping['DistanceButtonControl'] == 12
  assert not any(action for _, action in commands)
  owner.observe(params, cp, state(True), now_ns=NOW + 40_000_000, drive_id=DRIVE)
  assert owner.observe(params, cp, state(False), now_ns=NOW + 50_000_000, drive_id=DRIVE) == (('DistanceButtonControl', 12),)


def test_invalid_drive_new_drive_recaptures_current_mapping(real_context):
  from openpilot.starpilot.controllers.tests.test_wheel_actions import DRIVE, NOW, state
  params, cp = real_context
  owner = wheel_actions.WheelPublisher()
  with mock.patch.object(wheel_actions, 'capture', wraps=wheel_actions.capture) as reads:
    assert owner.observe(params, cp, state(), now_ns=NOW, drive_id=0) == ()
  reads.assert_not_called()
  assert owner.mapping is None
  params.put('DistanceButtonControl', 11, block=True)
  with mock.patch.object(wheel_actions, 'capture', wraps=wheel_actions.capture) as reads:
    commands = owner.observe(params, cp, state(), now_ns=NOW + 10_000_000, drive_id=DRIVE + 1)
  reads.assert_called_once_with(params)
  assert owner.mapping is not None
  assert owner.drive == DRIVE + 1 and owner.mapping['DistanceButtonControl'] == 11
  assert not any(action for _, action in commands)
  owner.observe(params, cp, state(True), now_ns=NOW + 20_000_000, drive_id=DRIVE + 1)
  assert owner.observe(params, cp, state(False), now_ns=NOW + 30_000_000, drive_id=DRIVE + 1) == (('DistanceButtonControl', 11),)
