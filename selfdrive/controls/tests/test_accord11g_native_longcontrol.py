from types import SimpleNamespace

import pytest
from cereal import car
from opendbc.car.honda.values import CAR as HONDA_CAR
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.longcontrol import (
  LongControl,
  LongCtrlState,
  honda_accord_11g_long_control_state_trans,
)


def make_cp(*, brand="honda", fingerprint=HONDA_CAR.HONDA_ACCORD_11G):
  CP = car.CarParams.new_message()
  CP.brand = brand
  CP.carFingerprint = fingerprint
  CP.stopAccel = -2.0
  CP.vEgoStarting = 0.5
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.0]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.0]
  return CP


def make_car_state(v_ego=10.0, a_ego=0.0, *, brake_pressed=False, standstill=False):
  CS = car.CarState.new_message()
  CS.vEgo = v_ego
  CS.aEgo = a_ego
  CS.brakePressed = brake_pressed
  CS.cruiseState.standstill = standstill
  return CS


@pytest.mark.parametrize(
  "active,state,should_stop,brake_pressed,standstill,expected",
  [
    (False, LongCtrlState.pid, False, False, False, LongCtrlState.off),
    (True, LongCtrlState.off, False, False, False, LongCtrlState.pid),
    (True, LongCtrlState.off, True, False, False, LongCtrlState.stopping),
    (True, LongCtrlState.off, False, True, False, LongCtrlState.stopping),
    (True, LongCtrlState.off, False, False, True, LongCtrlState.stopping),
    (True, LongCtrlState.stopping, False, False, False, LongCtrlState.pid),
    (True, LongCtrlState.pid, True, False, False, LongCtrlState.stopping),
  ],
)
def test_accord11g_native_longcontrol_state_machine(active, state, should_stop, brake_pressed, standstill, expected):
  CP = make_cp()
  result = honda_accord_11g_long_control_state_trans(
    CP, active, state, should_stop, brake_pressed, standstill,
  )
  assert result == expected
  assert result != LongCtrlState.starting


def test_accord11g_native_longcontrol_pid_ignores_shared_shaping_inputs():
  controller = LongControl(make_cp())
  CS = make_car_state()

  output = controller.update(
    True, CS, 0.8, False, [-3.5, 2.0], object(),
    has_lead=True, traffic_mode_enabled=True, profile_max_accel=0.1,
    pedal_override=True, leads=[object()],
  )
  assert controller.honda_accord_11g
  assert controller.long_control_state == LongCtrlState.pid
  assert output == pytest.approx(0.8)

  output = controller.update(
    True, CS, -0.6, False, [-3.5, 2.0], object(),
    has_lead=True, traffic_mode_enabled=True, profile_max_accel=0.1,
  )
  assert output == pytest.approx(-0.6)


def test_accord11g_native_longcontrol_stopping_ramp_hold_release_and_off():
  controller = LongControl(make_cp())
  CS = make_car_state(v_ego=0.1)
  controller.last_output_accel = 0.4

  assert controller.update(True, CS, -1.0, True, [-3.5, 2.0], object()) == pytest.approx(-DT_CTRL)
  assert controller.long_control_state == LongCtrlState.stopping

  for _ in range(400):
    controller.update(True, CS, -1.0, True, [-3.5, 2.0], object())
  assert controller.last_output_accel == pytest.approx(controller.CP.stopAccel)

  assert controller.update(True, CS, 0.3, False, [-3.5, 2.0], object()) == pytest.approx(0.3)
  assert controller.long_control_state == LongCtrlState.pid
  assert controller.update(False, CS, 0.3, False, [-3.5, 2.0], object()) == pytest.approx(0.0)
  assert controller.long_control_state == LongCtrlState.off


def test_non_accord_longcontrol_remains_on_native_dom_path():
  civic = LongControl(make_cp(fingerprint=HONDA_CAR.HONDA_CIVIC_BOSCH))
  assert not civic.honda_accord_11g

  toggles = SimpleNamespace(
    vEgoStarting=0.5,
    stopAccel=-2.0,
    stoppingDecelRate=0.2,
    startAccel=1.0,
    custom_accel_profile=False,
  )
  civic.CP.startingState = True
  output = civic.update(True, make_car_state(v_ego=0.0), 0.5, False, [-3.5, 2.0], toggles)

  assert civic.long_control_state == LongCtrlState.starting
  assert output == pytest.approx(toggles.startAccel)
