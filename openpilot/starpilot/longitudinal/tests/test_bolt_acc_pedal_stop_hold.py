"""The registered Bolt interceptor controller keeps admitted stops pedal-neutral."""

import pytest

from opendbc.can import CANParser
from opendbc.car import Bus, structs
from opendbc.car.gm import gmcan
from opendbc.car.gm.tests import test_bolt_acc_pedal_friction as fixtures
from opendbc.car.gm.values import BOLT_PEDAL_WORDS, CAR, DBC, is_bolt_pedal_profile

NOW = 1_000_000_000
STOPPING = structs.CarControl.Actuators.LongControlState.stopping
PID = structs.CarControl.Actuators.LongControlState.pid


def stop_fixture(candidate=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL):
  fixture = fixtures.TestBoltAccPedalFriction(methodName='runTest').fixture(candidate)
  controller, control, state, _ = fixture
  assert is_bolt_pedal_profile(controller.CP)
  assert controller.CP.safetyConfigs[0].safetyParam == BOLT_PEDAL_WORDS[candidate]
  state.canValid = True
  state.vEgo = 0.0
  state.standstill = True
  control.actuators.accel = 0.0
  control.actuators.longControlState = STOPPING
  return fixture


def step(fixture, frame):
  controller, control, state, cs = fixture
  controller.frame = frame
  cs.out = state.as_reader()
  return controller.update(control.as_reader(), cs, NOW)


def pedal_fields(controller, messages, frame):
  pedal = [message for message in messages if message[0] == 0x200]
  assert len(pedal) == 1
  message = pedal[0]
  assert message[2] == 0
  assert len(message[1]) == 6
  assert message[1][5] == gmcan.pedal_crc(message[1])
  parser = CANParser(DBC[controller.CP.carFingerprint][Bus.pt], [('GAS_COMMAND', 0)], 0)
  parser.update([(NOW, pedal)])
  fields = parser.vl['GAS_COMMAND']
  assert fields['COUNTER_PEDAL'] == (frame // 4) % 16
  return message[1], fields


def neutral(controller, output, messages, frame):
  raw, fields = pedal_fields(controller, messages, frame)
  assert fields['ENABLE'] == 0
  assert raw[:4] == bytes(4)  # Native inactive encoding, rather than decoded offset-valued fields.
  assert output.gas == 0.0
  assert controller.pedal_steady == 0.0


def test_stop_hold_enters_and_survives_standstill_signal_release():
  fixture = stop_fixture()
  controller, _, state, _ = fixture
  for frame, standstill in ((4, True), (8, False), (12, False)):
    state.standstill = standstill
    output, messages = step(fixture, frame)
    neutral(controller, output, messages, frame)
    assert controller.bolt_acc_pedal_stop_hold


@pytest.mark.parametrize('resume, long_state', [(True, STOPPING), (False, PID)])
def test_explicit_launch_releases_hold_and_existing_calculation(resume, long_state):
  fixture = stop_fixture()
  controller, control, state, _ = fixture
  output, messages = step(fixture, 4)
  neutral(controller, output, messages, 4)
  state.standstill = False
  control.cruiseControl.resume = resume
  control.actuators.longControlState = long_state
  output, messages = step(fixture, 8)
  _, fields = pedal_fields(controller, messages, 8)
  assert not controller.bolt_acc_pedal_stop_hold
  assert fields['ENABLE'] == 1
  assert output.gas > 0.0


@pytest.mark.parametrize(
  'gate', ['long_inactive', 'gas', 'brake', 'regen', 'stock_acc', 'main_off', 'gear', 'sensor_bad', 'sensor_stale', 'stock_stale', 'gear_stale', 'main_stale']
)
def test_admission_loss_clears_hold_and_never_sends_active_pedal(gate):
  fixture = stop_fixture()
  controller, control, state, cs = fixture
  output, messages = step(fixture, 4)
  neutral(controller, output, messages, 4)
  state.standstill = False
  if gate == 'long_inactive':
    control.longActive = False
  elif gate == 'gas':
    state.gasPressed = True
  elif gate == 'brake':
    state.brakePressed = True
  elif gate == 'regen':
    state.regenBraking = True
  elif gate == 'stock_acc':
    state.cruiseState.enabled = True
  elif gate == 'main_off':
    state.cruiseState.available = False
  elif gate == 'gear':
    state.gearShifter = structs.CarState.GearShifter.neutral
  elif gate == 'sensor_bad':
    cs.pedal_sensor_healthy = False
  else:
    name = {
      'sensor_stale': 'pedal_sensor_ts_nanos',
      'stock_stale': 'stock_acc_status_ts_nanos',
      'gear_stale': 'bolt_pedal_gear_ts_nanos',
      'main_stale': 'bolt_pedal_main_ts_nanos',
    }[gate]
    setattr(cs, name, 1)
  # The state is cleared even on the 100 Hz tick with no 25 Hz interceptor emission.
  _, messages = step(fixture, 5)
  assert not controller.bolt_acc_pedal_stop_hold
  assert not any(message[0] == 0x200 for message in messages)
  output, messages = step(fixture, 8)
  neutral(controller, output, messages, 8)
  assert not controller.bolt_acc_pedal_stop_hold


def test_moving_stopping_does_not_start_hold():
  fixture = stop_fixture()
  controller, _, state, _ = fixture
  state.standstill = False
  state.vEgo = 1.0
  output, messages = step(fixture, 4)
  _, fields = pedal_fields(controller, messages, 4)
  assert not controller.bolt_acc_pedal_stop_hold
  assert fields['ENABLE'] == 1
  assert output.gas > 0.0


def test_no_acc_fixed_stop_keeps_existing_memory_semantics():
  fixture = stop_fixture(CAR.CHEVROLET_BOLT_CC_2022_2023)
  controller = fixture[0]
  controller.pedal_steady = 0.2
  controller.pedal_active_last = True
  output, messages = step(fixture, 4)
  raw, fields = pedal_fields(controller, messages, 4)
  assert not controller.bolt_acc_pedal_stop_hold
  assert controller.pedal_steady == 0.2
  assert output.gas == 0.0
  assert fields['ENABLE'] == 0
  assert raw[:4] == bytes(4)
