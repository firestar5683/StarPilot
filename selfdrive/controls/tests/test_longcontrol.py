from types import SimpleNamespace

from cereal import car
import pytest

import openpilot.selfdrive.controls.lib.longcontrol as longcontrol
from opendbc.car.gm.values import CAR, GMFlags
from openpilot.selfdrive.controls.lib.longcontrol import (
  LongControl,
  LongCtrlState,
  long_control_state_trans,
)


def make_toggles(**overrides):
  defaults = {
    "custom_accel_profile": False,
    "human_acceleration": False,
    "startAccel": 1.5,
    "stopAccel": -0.5,
    "stoppingDecelRate": 0.8,
    "vEgoStarting": 0.5,
    "vEgoStopping": 0.5,
  }
  defaults.update(overrides)
  return SimpleNamespace(**defaults)


def make_longcontrol_cp(**overrides):
  CP = car.CarParams.new_message()
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.0]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.0]
  CP.longitudinalTuning.kfDEPRECATED = 1.0

  for key, value in overrides.items():
    setattr(CP, key, value)

  return CP


class TestLongControlStateTransition:

  def test_stay_stopped(self):
    CP = car.CarParams.new_message()
    toggles = make_toggles()
    active = True
    current_state = LongCtrlState.stopping
    next_state = long_control_state_trans(CP, active, current_state, v_ego=0.1,
                             should_stop=True, brake_pressed=False, cruise_standstill=False, starpilot_toggles=toggles)
    assert next_state == LongCtrlState.stopping
    next_state = long_control_state_trans(CP, active, current_state, v_ego=0.1,
                             should_stop=False, brake_pressed=True, cruise_standstill=False, starpilot_toggles=toggles)
    assert next_state == LongCtrlState.stopping
    next_state = long_control_state_trans(CP, active, current_state, v_ego=0.1,
                             should_stop=False, brake_pressed=False, cruise_standstill=True, starpilot_toggles=toggles,
                             allow_stopping_release=False)
    assert next_state == LongCtrlState.stopping
    next_state = long_control_state_trans(CP, active, current_state, v_ego=1.0,
                             should_stop=False, brake_pressed=False, cruise_standstill=False, starpilot_toggles=toggles)
    assert next_state == LongCtrlState.pid
    active = False
    next_state = long_control_state_trans(CP, active, current_state, v_ego=1.0,
                             should_stop=False, brake_pressed=False, cruise_standstill=False, starpilot_toggles=toggles)
    assert next_state == LongCtrlState.off


def test_engage():
  CP = car.CarParams.new_message()
  toggles = make_toggles()
  active = True
  current_state = LongCtrlState.off
  next_state = long_control_state_trans(CP, active, current_state, v_ego=0.1,
                             should_stop=True, brake_pressed=False, cruise_standstill=False, starpilot_toggles=toggles)
  assert next_state == LongCtrlState.stopping
  next_state = long_control_state_trans(CP, active, current_state, v_ego=0.1,
                             should_stop=False, brake_pressed=True, cruise_standstill=False, starpilot_toggles=toggles)
  assert next_state == LongCtrlState.stopping
  next_state = long_control_state_trans(CP, active, current_state, v_ego=0.1,
                             should_stop=False, brake_pressed=False, cruise_standstill=True, starpilot_toggles=toggles)
  assert next_state == LongCtrlState.stopping
  next_state = long_control_state_trans(CP, active, current_state, v_ego=0.1,
                             should_stop=False, brake_pressed=False, cruise_standstill=False, starpilot_toggles=toggles)
  assert next_state == LongCtrlState.pid


def test_starting():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  toggles = make_toggles(vEgoStarting=0.5)
  active = True
  current_state = LongCtrlState.starting
  next_state = long_control_state_trans(CP, active, current_state, v_ego=0.1,
                             should_stop=False, brake_pressed=False, cruise_standstill=False, starpilot_toggles=toggles)
  assert next_state == LongCtrlState.starting
  next_state = long_control_state_trans(CP, active, current_state, v_ego=1.0,
                             should_stop=False, brake_pressed=False, cruise_standstill=False, starpilot_toggles=toggles)
  assert next_state == LongCtrlState.pid


def test_stopping_release_hysteresis_blocks_immediate_launch():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  toggles = make_toggles(vEgoStarting=0.5)
  active = True
  current_state = LongCtrlState.stopping

  next_state = long_control_state_trans(CP, active, current_state, v_ego=0.0,
                             should_stop=False, brake_pressed=False, cruise_standstill=False, starpilot_toggles=toggles,
                             allow_stopping_release=False)
  assert next_state == LongCtrlState.stopping


def test_stopping_release_allows_launch_while_cruise_standstill_latched():
  CP = car.CarParams.new_message()
  toggles = make_toggles(vEgoStarting=0.5)
  active = True
  current_state = LongCtrlState.stopping

  next_state = long_control_state_trans(CP, active, current_state, v_ego=0.0,
                             should_stop=False, brake_pressed=False, cruise_standstill=True, starpilot_toggles=toggles,
                             allow_stopping_release=True)
  assert next_state == LongCtrlState.pid


def test_starting_accel_unchanged_when_custom_profile_disabled():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=0.1,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(startAccel=1.5),
  )

  assert lc.long_control_state == LongCtrlState.starting
  assert output_accel == 1.5


def test_ev9_starting_uses_vehicle_specific_accel_and_speed():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5, startAccel=0.2)
  CP.carFingerprint = "KIA_EV9"
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False
  toggles = make_toggles(startAccel=1.0, vEgoStarting=0.1)

  output_accel = lc.update(True, CS, 1.0, False, (-3.0, 2.0), toggles)
  assert lc.long_control_state == LongCtrlState.starting
  assert output_accel == pytest.approx(0.2)

  CS.vEgo = 0.2
  output_accel = lc.update(True, CS, 1.0, False, (-3.0, 2.0), toggles)
  assert lc.long_control_state == LongCtrlState.starting
  assert output_accel == pytest.approx(0.2)

  CS.vEgo = 0.6
  lc.update(True, CS, 1.0, False, (-3.0, 2.0), toggles)
  assert lc.long_control_state == LongCtrlState.pid


def test_starting_accel_obeys_a_target_cap_when_custom_profile_enabled():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=0.1,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(startAccel=1.5, custom_accel_profile=True),
  )

  assert lc.long_control_state == LongCtrlState.starting
  assert output_accel == 0.1


def test_update_requires_sustained_moderate_positive_target_to_leave_stopping():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.stopping
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  release_frames = int(round(longcontrol.STOPPING_RELEASE_HYSTERESIS / longcontrol.DT_CTRL))
  for _ in range(release_frames - 1):
    output_accel = lc.update(
      active=True,
      CS=CS,
      a_target=longcontrol.STOPPING_RELEASE_STRONG_ACCEL - 0.01,
      should_stop=False,
      accel_limits=(-3.0, 2.0),
      starpilot_toggles=make_toggles(startAccel=1.5),
    )
    assert lc.long_control_state == LongCtrlState.stopping
    assert output_accel <= 0.0

  lc.update(
    active=True,
    CS=CS,
    a_target=longcontrol.STOPPING_RELEASE_STRONG_ACCEL - 0.01,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(startAccel=1.5),
  )

  assert lc.long_control_state == LongCtrlState.starting


def test_update_releases_stopping_immediately_on_strong_positive_target():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.stopping
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=longcontrol.STOPPING_RELEASE_STRONG_ACCEL,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(startAccel=1.5),
  )

  assert lc.long_control_state == LongCtrlState.starting
  assert output_accel > 0.0


def test_update_releases_stopping_on_small_sustained_positive_target():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.stopping
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  release_frames = int(round(longcontrol.STOPPING_RELEASE_HYSTERESIS / longcontrol.DT_CTRL))
  for _ in range(release_frames - 1):
    output_accel = lc.update(
      active=True,
      CS=CS,
      a_target=0.16,
      should_stop=False,
      accel_limits=(-3.0, 2.0),
      starpilot_toggles=make_toggles(startAccel=1.5),
    )
    assert lc.long_control_state == LongCtrlState.stopping
    assert output_accel <= 0.0

  lc.update(
    active=True,
    CS=CS,
    a_target=0.16,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(startAccel=1.5),
  )

  assert lc.long_control_state == LongCtrlState.starting


def test_update_releases_stopping_immediately_after_confirmed_lead_departure():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.stopping
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = True

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=0.16,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(startAccel=1.5),
    has_lead=True,
  )

  assert lc.long_control_state == LongCtrlState.starting
  assert output_accel > 0.0


@pytest.mark.parametrize(("should_stop", "brake_pressed"), [(True, False), (False, True)])
def test_confirmed_lead_departure_does_not_override_stop_or_driver_brake(should_stop, brake_pressed):
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.stopping
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=brake_pressed)
  CS.cruiseState.standstill = True

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=0.5,
    should_stop=should_stop,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(startAccel=1.5),
    has_lead=True,
  )

  assert lc.long_control_state == LongCtrlState.stopping
  assert output_accel <= 0.0


def test_update_releases_stopping_with_cruise_standstill_latched():
  CP = car.CarParams.new_message(vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.stopping
  lc.last_output_accel = -2.003
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = True

  release_frames = int(round(longcontrol.STOPPING_RELEASE_HYSTERESIS / longcontrol.DT_CTRL))
  for _ in range(release_frames - 1):
    output_accel = lc.update(
      active=True,
      CS=CS,
      a_target=0.5,
      should_stop=False,
      accel_limits=(-3.0, 2.0),
      starpilot_toggles=make_toggles(startAccel=1.5),
    )
    assert lc.long_control_state == LongCtrlState.stopping
    assert output_accel <= 0.0

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=0.5,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(startAccel=1.5),
  )

  assert lc.long_control_state == LongCtrlState.pid
  assert output_accel > 0.0


def test_stopping_state_follows_stronger_moving_stop_target():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.stopping
  lc.last_output_accel = -1.40
  CS = car.CarState.new_message(vEgo=4.0, aEgo=-1.2, brakePressed=False)
  CS.cruiseState.standstill = False

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=-3.5,
    should_stop=True,
    accel_limits=(-3.5, 2.0),
    starpilot_toggles=make_toggles(stopAccel=-0.5, stoppingDecelRate=0.8, vEgoStopping=0.5),
  )

  assert lc.long_control_state == LongCtrlState.stopping
  assert output_accel < -1.43


def test_volt_testing_ground_handoff_freezes_integrator(monkeypatch):
  CP = car.CarParams.new_message()
  CP.brand = "gm"
  CP.enableGasInterceptorDEPRECATED = True
  CP.carFingerprint = "CHEVROLET_VOLT_ASCM"
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  monkeypatch.setattr(longcontrol, "testing_ground", SimpleNamespace(use_2=True))

  lc = LongControl(CP)
  freeze = lc._get_pedal_long_freeze(a_target=0.7, error=0.7, v_ego=8.0, accel_limits=(-3.0, 2.0))

  assert freeze
  assert lc.integrator_hold_frames > 0


def test_non_interceptor_volt_testing_ground_handoff_freezes_integrator(monkeypatch):
  CP = car.CarParams.new_message()
  CP.brand = "gm"
  CP.enableGasInterceptorDEPRECATED = False
  CP.carFingerprint = "CHEVROLET_VOLT_ASCM"
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  monkeypatch.setattr(longcontrol, "testing_ground", SimpleNamespace(use_2=True))

  lc = LongControl(CP)
  freeze = lc._get_pedal_long_freeze(a_target=0.7, error=0.7, v_ego=8.0, accel_limits=(-3.0, 2.0))

  assert freeze
  assert lc.integrator_hold_frames > 0


def test_negative_target_unwinds_positive_accel_command_after_sign_flip():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.pid
  lc.last_output_accel = 1.2
  lc.pid.i = 1.2
  CS = car.CarState.new_message(vEgo=30.0, aEgo=0.9, brakePressed=False, gasPressed=False)
  CS.cruiseState.standstill = False

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=-0.5,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(),
  )

  assert lc.long_control_state == LongCtrlState.pid
  assert output_accel <= 0.01


def test_negative_target_unwinds_positive_accel_command_at_low_speed():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.pid
  lc.last_output_accel = 0.9
  lc.pid.i = 0.9
  CS = car.CarState.new_message(vEgo=1.3, aEgo=0.35, brakePressed=False, gasPressed=False)
  CS.cruiseState.standstill = False

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=-1.2,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(),
  )

  assert lc.long_control_state == LongCtrlState.pid
  assert output_accel <= 0.01


def test_negative_target_creep_guard_keeps_mild_crawl_request():
  capped = LongControl._cap_positive_output_on_negative_target(
    output_accel=0.18,
    a_target=-0.2,
    error=-0.5,
    CS=car.CarState.new_message(vEgo=0.2, aEgo=0.0),
  )

  assert capped == pytest.approx(0.18)


def test_pedal_long_brake_bias_adds_small_negative_nudge_for_strong_decel_request():
  CP = car.CarParams.new_message()
  CP.brand = "gm"
  CP.enableGasInterceptorDEPRECATED = True
  CP.flags = 1
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  CS = car.CarState.new_message(vEgo=20.0, aEgo=0.0, brakePressed=False)

  biased = lc._apply_pedal_long_brake_bias(-1.0, -3.0, CS)

  assert biased < -1.0
  assert biased == pytest.approx(-1.15, abs=0.03)


def test_pedal_long_brake_bias_does_not_touch_non_pedal_or_mild_decel():
  CP = car.CarParams.new_message()
  CP.brand = "gm"
  CP.enableGasInterceptorDEPRECATED = False
  CP.flags = 0
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  CS = car.CarState.new_message(vEgo=20.0, aEgo=0.0, brakePressed=False)

  assert lc._apply_pedal_long_brake_bias(-1.0, -3.0, CS) == -1.0
  assert lc._apply_pedal_long_brake_bias(-0.4, -0.6, CS) == -0.4


def test_bolt_acc_pedal_friction_feedforward_preserves_regen_scaling_within_envelope():
  CP = make_longcontrol_cp(
    brand="gm",
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  )
  CP.longitudinalTuning.kfDEPRECATED = 0.20

  lc = LongControl(CP)

  assert lc._get_longitudinal_feedforward(-1.8, 4.73) == pytest.approx(-0.36)


def test_bolt_acc_pedal_friction_feedforward_restores_full_gain_beyond_regen_envelope():
  CP = make_longcontrol_cp(
    brand="gm",
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  )
  CP.longitudinalTuning.kfDEPRECATED = 0.20

  lc = LongControl(CP)

  assert lc._get_longitudinal_feedforward(-3.22, 4.73) == pytest.approx(-3.22)


def test_bolt_acc_pedal_friction_feedforward_blends_back_in_for_small_friction_request():
  CP = make_longcontrol_cp(
    brand="gm",
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  )
  CP.longitudinalTuning.kfDEPRECATED = 0.20

  lc = LongControl(CP)
  pedal_regen_limit = float(longcontrol.interp(20.0, longcontrol.BOLT_ACC_PEDAL_REGEN_LIMIT_BP,
                                               longcontrol.BOLT_ACC_PEDAL_REGEN_LIMIT_V))
  a_target = pedal_regen_limit - 0.10
  expected_gain = longcontrol.get_bolt_acc_pedal_feedforward_gain(0.20, a_target, 20.0, pedal_regen_limit, 0.0)
  expected = a_target * expected_gain

  assert lc._get_longitudinal_feedforward(a_target, 20.0) == pytest.approx(expected)


def test_bolt_acc_pedal_friction_floor_holds_friction_only_authority():
  pedal_regen_limit = float(longcontrol.interp(9.85, longcontrol.BOLT_ACC_PEDAL_REGEN_LIMIT_BP,
                                               longcontrol.BOLT_ACC_PEDAL_REGEN_LIMIT_V))
  floor = longcontrol.get_bolt_acc_pedal_friction_floor(-3.47, 9.85, pedal_regen_limit)

  assert floor is not None
  assert floor < pedal_regen_limit
  assert floor > -3.47


def test_bolt_acc_pedal_friction_bias_applies_floor_only_on_experimental_fingerprint():
  pedal_cp = make_longcontrol_cp(
    brand="gm",
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  )
  bolt_cc_cp = make_longcontrol_cp(
    brand="gm",
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    carFingerprint=CAR.CHEVROLET_BOLT_CC_2022_2023,
  )

  pedal_lc = LongControl(pedal_cp)
  bolt_cc_lc = LongControl(bolt_cc_cp)
  CS = car.CarState.new_message(vEgo=9.85, aEgo=-2.0, brakePressed=False)

  pedal_regen_limit = float(longcontrol.interp(CS.vEgo, longcontrol.BOLT_ACC_PEDAL_REGEN_LIMIT_BP,
                                               longcontrol.BOLT_ACC_PEDAL_REGEN_LIMIT_V))
  floor = longcontrol.get_bolt_acc_pedal_friction_floor(-3.47, CS.vEgo, pedal_regen_limit)
  assert floor is not None

  pedal_biased = pedal_lc._apply_pedal_long_brake_bias(-1.85, -3.47, CS)
  bolt_cc_biased = bolt_cc_lc._apply_pedal_long_brake_bias(-1.85, -3.47, CS)

  assert pedal_biased == pytest.approx(floor)
  assert bolt_cc_biased > pedal_biased + 0.5


def test_bolt_acc_pedal_feedforward_gain_stays_base_for_mild_regen():
  gain = longcontrol.get_bolt_acc_pedal_feedforward_gain(0.2, -1.0, 10.0, -2.75, -0.4)

  assert gain == pytest.approx(0.2)


def test_bolt_acc_pedal_feedforward_gain_restores_for_authority_gap():
  gain = longcontrol.get_bolt_acc_pedal_feedforward_gain(0.2, -1.83, 12.38, -2.79, -0.70)

  assert gain > 0.55


def test_bolt_acc_pedal_feedforward_gain_restores_near_friction_handoff():
  gain = longcontrol.get_bolt_acc_pedal_feedforward_gain(0.2, -2.63, 9.35, -2.69, -1.30)

  assert gain > 0.45


def test_bolt_cc_pedal_friction_feedforward_remains_fully_scaled_by_kf():
  CP = make_longcontrol_cp(
    brand="gm",
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    carFingerprint=CAR.CHEVROLET_BOLT_CC_2022_2023,
  )
  CP.longitudinalTuning.kfDEPRECATED = 0.20

  lc = LongControl(CP)

  assert lc._get_longitudinal_feedforward(-3.22, 4.73) == pytest.approx(-0.644)


def test_gm_stock_truck_positive_i_bleeds_on_coast_request():
  CP = car.CarParams.new_message()
  CP.brand = "gm"
  CP.carFingerprint = "CHEVROLET_SILVERADO"
  CP.enableGasInterceptorDEPRECATED = False
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.02]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.28]

  lc = LongControl(CP)
  lc.pid.i = 0.25
  lc.last_output_accel = 0.20
  CS = car.CarState.new_message(vEgo=20.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  lc._trim_gm_truck_positive_hold_integrator(-0.02, -0.02, CS)

  assert lc.pid.i < 0.25


def test_gm_stock_truck_positive_i_bleeds_during_light_highway_accel_request():
  CP = car.CarParams.new_message()
  CP.brand = "gm"
  CP.carFingerprint = "CHEVROLET_SILVERADO"
  CP.enableGasInterceptorDEPRECATED = False
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.02]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.28]

  lc = LongControl(CP)
  lc.pid.i = 0.25
  lc.last_output_accel = 0.20
  CS = car.CarState.new_message(vEgo=20.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  lc._trim_gm_truck_positive_hold_integrator(0.05, 0.05, CS)

  assert lc.pid.i < 0.25


def test_gm_stock_truck_positive_i_trim_keeps_meaningful_accel_request():
  CP = car.CarParams.new_message()
  CP.brand = "gm"
  CP.carFingerprint = "CHEVROLET_SILVERADO"
  CP.enableGasInterceptorDEPRECATED = False
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.02]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.28]

  lc = LongControl(CP)
  lc.pid.i = 0.25
  lc.last_output_accel = 0.20
  CS = car.CarState.new_message(vEgo=20.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  lc._trim_gm_truck_positive_hold_integrator(0.12, 0.12, CS)

  assert lc.pid.i == pytest.approx(0.25, abs=1e-9)


def test_gm_stock_truck_positive_i_trim_preserves_low_speed_launch():
  CP = car.CarParams.new_message()
  CP.brand = "gm"
  CP.carFingerprint = "CHEVROLET_SILVERADO"
  CP.enableGasInterceptorDEPRECATED = False
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.02]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.28]

  lc = LongControl(CP)
  lc.pid.i = 0.25
  lc.last_output_accel = 0.20
  CS = car.CarState.new_message(vEgo=5.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  lc._trim_gm_truck_positive_hold_integrator(0.05, 0.05, CS)

  assert lc.pid.i == pytest.approx(0.25, abs=1e-9)
