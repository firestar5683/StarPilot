from types import SimpleNamespace

from cereal import car
import pytest

import openpilot.selfdrive.controls.lib.longcontrol as longcontrol
import openpilot.selfdrive.controls.lib.longcontrol_vehicle_tunes as vehicle_tunes
from opendbc.car.gm.values import CAR, GMFlags
from opendbc.car.subaru.values import CAR as SUBARU_CAR
from opendbc.car.toyota.values import CAR as TOYOTA_CAR
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.longcontrol import (
  LongControl,
  LongCtrlState,
  long_control_state_trans,
)


def make_toggles(**overrides):
  defaults = {
    "custom_accel_profile": False,
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


def test_starting_accel_uses_small_planner_target_for_lead_gap_settle():
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
    a_target=0.18,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(startAccel=1.5),
    has_lead=True,
  )

  assert lc.long_control_state == LongCtrlState.starting
  assert output_accel == pytest.approx(0.18)


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


def test_starting_accel_obeys_a_target_cap_when_traffic_mode_enabled():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  # Large manually-tuned startAccel override (e.g. 3.5) should not fire a raw
  # launch kick while Traffic Mode is active; output must track the soft a_target.
  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=1.10,
    should_stop=False,
    accel_limits=(-3.0, 4.0),
    starpilot_toggles=make_toggles(startAccel=3.5),
    traffic_mode_enabled=True,
  )

  assert lc.long_control_state == LongCtrlState.starting
  assert output_accel == pytest.approx(1.10)


def test_starting_accel_uses_raw_start_accel_when_no_profile_ceiling():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  # No usable profile ceiling published (e.g. a stale/zero starpilotPlan) -> keep the
  # raw StartAccel shove so a publish gap never zeroes out the launch.
  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=1.10,
    should_stop=False,
    accel_limits=(-3.0, 4.0),
    starpilot_toggles=make_toggles(startAccel=3.5),
    traffic_mode_enabled=False,
    profile_max_accel=0.0,
  )

  assert lc.long_control_state == LongCtrlState.starting
  assert output_accel == pytest.approx(3.5)


def test_starting_accel_capped_by_profile_ceiling():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  # A large StartAccel override (3.5) must be capped to the selected profile's launch
  # ceiling (e.g. Eco = 1.5) so a soft profile launches soft.
  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=1.10,
    should_stop=False,
    accel_limits=(-3.0, 4.0),
    starpilot_toggles=make_toggles(startAccel=3.5),
    traffic_mode_enabled=False,
    profile_max_accel=1.5,
  )

  assert lc.long_control_state == LongCtrlState.starting
  assert output_accel == pytest.approx(1.5)


def test_starting_accel_keeps_start_accel_shove_below_profile_ceiling():
  CP = car.CarParams.new_message(startingState=True, vEgoStarting=0.5)
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  lc = LongControl(CP)
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  # StartAccel below the profile ceiling (e.g. Sport+ = 3.5) is preserved in full -
  # the cap only trims launches that exceed the profile, it does not weaken the shove.
  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=1.10,
    should_stop=False,
    accel_limits=(-3.0, 4.0),
    starpilot_toggles=make_toggles(startAccel=1.5),
    traffic_mode_enabled=False,
    profile_max_accel=3.5,
  )

  assert lc.long_control_state == LongCtrlState.starting
  assert output_accel == pytest.approx(1.5)


def test_bolt_acc_pedal_starting_handoff_keeps_small_positive_command():
  CP = make_longcontrol_cp(
    brand="gm",
    startingState=True,
    vEgoStarting=0.35,
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  )
  CP.longitudinalTuning.kpV = [0.8]

  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.starting
  lc.last_output_accel = 0.55
  CS = car.CarState.new_message(vEgo=0.4, aEgo=1.5, brakePressed=False)
  CS.cruiseState.standstill = False

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=0.55,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(vEgoStarting=0.35),
    has_lead=True,
  )

  assert lc.long_control_state == LongCtrlState.pid
  assert output_accel == pytest.approx(0.188, abs=0.01)


def test_tesla_pedal_override_keeps_longitudinal_state_warm_for_release():
  CP = make_longcontrol_cp(
    brand="tesla",
    carFingerprint="TESLA_MODEL_3",
    startingState=True,
    vEgoStarting=0.35,
  )
  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.pid
  lc.last_output_accel = 0.8

  CS = car.CarState.new_message(vEgo=12.0, aEgo=0.8, brakePressed=False, gasPressed=True)
  CS.cruiseState.standstill = False
  override_output = lc.update(
    active=False,
    CS=CS,
    a_target=0.6,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(),
    pedal_override=True,
  )

  assert override_output == 0.0
  assert lc.long_control_state == LongCtrlState.pid
  assert lc.last_output_accel == pytest.approx(0.8)

  CS.gasPressed = False
  release_output = lc.update(
    active=True,
    CS=CS,
    a_target=0.6,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(),
  )

  assert release_output >= 0.6


def test_tesla_pedal_release_guard_blocks_mild_regen_pulse():
  CP = make_longcontrol_cp(
    brand="tesla",
    carFingerprint="TESLA_MODEL_3",
    startingState=True,
    vEgoStarting=0.35,
  )
  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.pid
  CS = car.CarState.new_message(vEgo=12.0, aEgo=0.8, brakePressed=False, gasPressed=True)
  CS.cruiseState.standstill = False
  lc.update(False, CS, -0.2, False, (-3.0, 2.0), make_toggles(), pedal_override=True)

  CS.gasPressed = False
  release_output = lc.update(True, CS, -0.2, False, (-3.0, 2.0), make_toggles())

  assert release_output == 0.0


@pytest.mark.parametrize(("a_target", "should_stop"), ((-0.2, False), (0.55, True)))
def test_bolt_acc_pedal_starting_handoff_never_overrides_stop_request(a_target, should_stop):
  CP = make_longcontrol_cp(
    brand="gm",
    startingState=True,
    vEgoStarting=0.35,
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  )

  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.starting
  lc.last_output_accel = 0.55
  CS = car.CarState.new_message(vEgo=0.4, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=a_target,
    should_stop=should_stop,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(vEgoStarting=0.35),
    has_lead=True,
  )

  assert output_accel <= 0.0


def test_bolt_acc_pedal_starting_handoff_floor_clears_when_lead_brakes_again():
  CP = make_longcontrol_cp(
    brand="gm",
    startingState=True,
    vEgoStarting=0.35,
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  )
  CP.longitudinalTuning.kpV = [0.8]

  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.starting
  lc.last_output_accel = 0.55
  CS = car.CarState.new_message(vEgo=0.4, aEgo=1.5, brakePressed=False)
  CS.cruiseState.standstill = False
  toggles = make_toggles(vEgoStarting=0.35)

  launch_output = lc.update(True, CS, 0.55, False, (-3.0, 2.0), toggles, has_lead=True)
  assert launch_output > 0.0

  CS.vEgo = 0.5
  CS.aEgo = 0.0
  brake_output = lc.update(True, CS, -0.5, True, (-3.0, 2.0), toggles, has_lead=True)
  assert lc.long_control_state == LongCtrlState.stopping
  assert brake_output < 0.0
  assert lc.vehicle_tuning.bolt_start_handoff_frames == 0


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


def test_corolla_tss2_stop_release_ramps_positive_target():
  CP = make_longcontrol_cp(
    brand="toyota",
    carFingerprint=TOYOTA_CAR.TOYOTA_COROLLA_TSS2,
  )
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)
  tuning.reset()

  first_target = tuning.shape_toyota_corolla_accel_target(1.5, 0.0, False, -0.15)
  assert first_target < 0.0
  assert first_target < 1.5

  target = first_target
  for _ in range(100):
    target = tuning.shape_toyota_corolla_accel_target(1.5, 0.0, False, target)
  assert target > 1.4

  for _ in range(100):
    target = tuning.shape_toyota_corolla_accel_target(1.5, 0.0, False, target)
  assert target == pytest.approx(1.5, abs=0.01)


def test_corolla_tss2_target_filter_does_not_delay_hard_braking():
  CP = make_longcontrol_cp(
    brand="toyota",
    carFingerprint=TOYOTA_CAR.TOYOTA_COROLLA_TSS2,
  )
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)
  tuning.shape_toyota_corolla_accel_target(1.0, 1.0, False, 0.0)

  assert tuning.shape_toyota_corolla_accel_target(-1.0, 1.0, False, 0.5) == -1.0


def test_corolla_tss2_longcontrol_release_does_not_step_to_full_accel():
  CP = make_longcontrol_cp(
    brand="toyota",
    carFingerprint=TOYOTA_CAR.TOYOTA_COROLLA_TSS2,
  )
  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.stopping
  lc.last_output_accel = -0.15
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=1.5,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(vEgoStarting=0.1),
  )

  assert lc.long_control_state == LongCtrlState.pid
  assert output_accel < 0.0


def test_subaru_impreza_stop_release_caps_launch_accel():
  CP = make_longcontrol_cp(
    brand="subaru",
    carFingerprint=SUBARU_CAR.SUBARU_IMPREZA_2020,
    vEgoStarting=0.5,
  )
  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.stopping
  CS = car.CarState.new_message(vEgo=0.0, aEgo=0.0, brakePressed=False)
  CS.cruiseState.standstill = False

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=1.8,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(vEgoStarting=0.5),
  )

  assert lc.long_control_state == LongCtrlState.pid
  assert output_accel == pytest.approx(vehicle_tunes.SUBARU_IMPREZA_STOP_RELEASE_MAX_ACCEL)


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


def test_elantra_lead_stop_releases_stale_hard_brake_after_target_eases():
  CP = make_longcontrol_cp(brand="hyundai", carFingerprint="HYUNDAI_ELANTRA_2021")
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)

  assert tuning.shape_stopping_accel(-1.20, -0.25, True, 1.0, True, -0.85) == pytest.approx(-0.85)
  assert tuning.shape_stopping_accel(-1.20, -1.50, True, 1.0, True, -0.85) == pytest.approx(-1.20)
  assert tuning.shape_stopping_accel(-1.20, -0.25, True, 1.0, False, -0.85) == pytest.approx(-1.20)


def test_elantra_stopped_lead_handoff_holds_braking_direction_without_touching_brakes():
  CP = make_longcontrol_cp(brand="hyundai", carFingerprint="HYUNDAI_ELANTRA_2021")
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)
  stopped_lead = SimpleNamespace(status=True, vLead=0.1, dRel=14.0)

  assert tuning.shape_hyundai_elantra_lead_target(0.14, 1.1, False, (stopped_lead,)) == pytest.approx(0.05)
  assert tuning.cap_hyundai_elantra_lead_output(0.14, 1.1, False, (stopped_lead,)) == pytest.approx(0.05)
  assert tuning.cap_hyundai_elantra_lead_output(-0.5, 1.1, False, (stopped_lead,)) == pytest.approx(-0.5)


def test_elantra_stopped_lead_handoff_releases_for_moving_lead_and_other_cars():
  elantra = vehicle_tunes.LongControlVehicleTuning(
    make_longcontrol_cp(brand="hyundai", carFingerprint="HYUNDAI_ELANTRA_2021")
  )
  other_car = vehicle_tunes.LongControlVehicleTuning(
    make_longcontrol_cp(brand="hyundai", carFingerprint="HYUNDAI_SONATA")
  )
  moving_lead = SimpleNamespace(status=True, vLead=0.8, dRel=14.0)
  stopped_lead = SimpleNamespace(status=True, vLead=0.1, dRel=14.0)

  assert elantra.shape_hyundai_elantra_lead_target(0.14, 1.1, False, (moving_lead,)) == pytest.approx(0.14)
  assert elantra.shape_hyundai_elantra_lead_target(0.14, 1.1, True, (stopped_lead,)) == pytest.approx(0.14)
  assert other_car.shape_hyundai_elantra_lead_target(0.14, 1.1, False, (stopped_lead,)) == pytest.approx(0.14)


def test_volt_testing_ground_handoff_freezes_integrator(monkeypatch):
  CP = car.CarParams.new_message()
  CP.brand = "gm"
  CP.enableGasInterceptorDEPRECATED = True
  CP.carFingerprint = "CHEVROLET_VOLT_ASCM"
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  monkeypatch.setattr(vehicle_tunes, "testing_ground", SimpleNamespace(use_2=True))

  lc = LongControl(CP)
  freeze = lc.vehicle_tuning.get_integrator_freeze(
    lc.last_output_accel, a_target=0.7, error=0.7, v_ego=8.0, accel_limits=(-3.0, 2.0),
  )

  assert freeze
  assert lc.vehicle_tuning.integrator_hold_frames > 0


def test_non_interceptor_volt_testing_ground_handoff_freezes_integrator(monkeypatch):
  CP = car.CarParams.new_message()
  CP.brand = "gm"
  CP.enableGasInterceptorDEPRECATED = False
  CP.carFingerprint = "CHEVROLET_VOLT_ASCM"
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.1]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.03]

  monkeypatch.setattr(vehicle_tunes, "testing_ground", SimpleNamespace(use_2=True))

  lc = LongControl(CP)
  freeze = lc.vehicle_tuning.get_integrator_freeze(
    lc.last_output_accel, a_target=0.7, error=0.7, v_ego=8.0, accel_limits=(-3.0, 2.0),
  )

  assert freeze
  assert lc.vehicle_tuning.integrator_hold_frames > 0


def test_volt_cruise_integrator_releases_stale_negative_bias():
  CP = car.CarParams.new_message()
  CP.brand = "gm"
  CP.carFingerprint = "CHEVROLET_VOLT_ASCM"
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.0]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.5]

  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.pid
  lc.pid.i = -0.20
  CS = car.CarState.new_message(vEgo=18.0, aEgo=0.0, brakePressed=False, gasPressed=False)
  CS.cruiseState.standstill = False

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=0.0,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(),
    has_lead=False,
  )

  assert lc.pid.i > -0.20
  assert output_accel > -0.20


@pytest.mark.parametrize("kwargs", [
  {"has_lead": True},
  {"should_stop": True},
  {"a_target": -0.25},
  {"aEgo": 0.25},
  {"vEgo": 4.0},
])
def test_volt_cruise_integrator_does_not_release_outside_settled_open_road(kwargs):
  CP = car.CarParams.new_message()
  CP.brand = "gm"
  CP.carFingerprint = "CHEVROLET_VOLT_ASCM"
  CP.longitudinalTuning.kpBP = [0.0]
  CP.longitudinalTuning.kpV = [0.0]
  CP.longitudinalTuning.kiBP = [0.0]
  CP.longitudinalTuning.kiV = [0.5]

  lc = LongControl(CP)
  pid = SimpleNamespace(i=-0.20)
  v_ego = kwargs.get("vEgo", 18.0)
  a_ego = kwargs.get("aEgo", 0.0)
  a_target = kwargs.get("a_target", 0.0)
  lc.vehicle_tuning.trim_volt_cruise_integrator(
    pid,
    a_target=a_target,
    error=a_target - a_ego,
    v_ego=v_ego,
    should_stop=kwargs.get("should_stop", False),
    has_lead=kwargs.get("has_lead", False),
  )

  assert pid.i == pytest.approx(-0.20)


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

  biased = lc.vehicle_tuning.apply_pedal_long_brake_bias(-1.0, -3.0, CS)

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

  assert lc.vehicle_tuning.apply_pedal_long_brake_bias(-1.0, -3.0, CS) == -1.0
  assert lc.vehicle_tuning.apply_pedal_long_brake_bias(-0.4, -0.6, CS) == -0.4


def test_bolt_acc_pedal_friction_feedforward_preserves_regen_scaling_within_envelope():
  CP = make_longcontrol_cp(
    brand="gm",
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  )
  CP.longitudinalTuning.kfDEPRECATED = 0.20

  lc = LongControl(CP)

  assert lc.vehicle_tuning.get_longitudinal_feedforward(
    lc.feedforward_gain, lc.last_output_accel, -1.8, 4.73,
  ) == pytest.approx(-0.36)


def test_bolt_acc_pedal_friction_feedforward_restores_full_gain_beyond_regen_envelope():
  CP = make_longcontrol_cp(
    brand="gm",
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  )
  CP.longitudinalTuning.kfDEPRECATED = 0.20

  lc = LongControl(CP)

  assert lc.vehicle_tuning.get_longitudinal_feedforward(
    lc.feedforward_gain, lc.last_output_accel, -3.22, 4.73,
  ) == pytest.approx(-3.22)


def test_bolt_acc_pedal_friction_feedforward_blends_back_in_for_small_friction_request():
  CP = make_longcontrol_cp(
    brand="gm",
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  )
  CP.longitudinalTuning.kfDEPRECATED = 0.20

  lc = LongControl(CP)
  pedal_regen_limit = float(vehicle_tunes.interp(20.0, vehicle_tunes.BOLT_ACC_PEDAL_REGEN_LIMIT_BP,
                                                 vehicle_tunes.BOLT_ACC_PEDAL_REGEN_LIMIT_V))
  a_target = pedal_regen_limit - 0.10
  expected_gain = vehicle_tunes.get_bolt_acc_pedal_feedforward_gain(0.20, a_target, 20.0, pedal_regen_limit, 0.0)
  expected = a_target * expected_gain

  assert lc.vehicle_tuning.get_longitudinal_feedforward(
    lc.feedforward_gain, lc.last_output_accel, a_target, 20.0,
  ) == pytest.approx(expected)


def test_bolt_acc_pedal_friction_floor_holds_friction_only_authority():
  pedal_regen_limit = float(vehicle_tunes.interp(9.85, vehicle_tunes.BOLT_ACC_PEDAL_REGEN_LIMIT_BP,
                                                 vehicle_tunes.BOLT_ACC_PEDAL_REGEN_LIMIT_V))
  floor = vehicle_tunes.get_bolt_acc_pedal_friction_floor(-3.47, 9.85, pedal_regen_limit)

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

  pedal_regen_limit = float(vehicle_tunes.interp(CS.vEgo, vehicle_tunes.BOLT_ACC_PEDAL_REGEN_LIMIT_BP,
                                                 vehicle_tunes.BOLT_ACC_PEDAL_REGEN_LIMIT_V))
  floor = vehicle_tunes.get_bolt_acc_pedal_friction_floor(-3.47, CS.vEgo, pedal_regen_limit)
  assert floor is not None

  pedal_biased = pedal_lc.vehicle_tuning.apply_pedal_long_brake_bias(-1.85, -3.47, CS)
  bolt_cc_biased = bolt_cc_lc.vehicle_tuning.apply_pedal_long_brake_bias(-1.85, -3.47, CS)

  assert pedal_biased == pytest.approx(floor)
  assert bolt_cc_biased > pedal_biased + 0.5


def test_bolt_acc_pedal_feedforward_gain_stays_base_for_mild_regen():
  gain = vehicle_tunes.get_bolt_acc_pedal_feedforward_gain(0.2, -1.0, 10.0, -2.75, -0.4)

  assert gain == pytest.approx(0.2)


def test_bolt_acc_pedal_feedforward_gain_restores_for_authority_gap():
  gain = vehicle_tunes.get_bolt_acc_pedal_feedforward_gain(0.2, -1.83, 12.38, -2.79, -0.70)

  assert gain > 0.55


def test_bolt_acc_pedal_feedforward_gain_restores_near_friction_handoff():
  gain = vehicle_tunes.get_bolt_acc_pedal_feedforward_gain(0.2, -2.63, 9.35, -2.69, -1.30)

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

  assert lc.vehicle_tuning.get_longitudinal_feedforward(
    lc.feedforward_gain, lc.last_output_accel, -3.22, 4.73,
  ) == pytest.approx(-0.644)


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

  lc.vehicle_tuning.trim_gm_truck_positive_hold_integrator(
    lc.pid, lc.last_output_accel, -0.02, -0.02, CS,
  )

  assert lc.pid.i < 0.25


def test_gm_stock_truck_target_filter_smooths_mild_follow_reversals():
  CP = make_longcontrol_cp(
    brand="gm",
    carFingerprint=CAR.CHEVROLET_SILVERADO,
    enableGasInterceptorDEPRECATED=False,
  )
  tuning = LongControl(CP).vehicle_tuning

  assert tuning.shape_gm_truck_accel_target(0.25, 20.0, False) == pytest.approx(0.25)
  filtered_brake = tuning.shape_gm_truck_accel_target(-0.10, 20.0, False)
  filtered_accel = tuning.shape_gm_truck_accel_target(0.25, 20.0, False)

  assert -0.10 < filtered_brake < 0.25
  assert filtered_brake < filtered_accel < 0.25


def test_gm_stock_truck_target_filter_uses_comfort_slew_for_mild_braking():
  CP = make_longcontrol_cp(
    brand="gm",
    carFingerprint=CAR.CHEVROLET_SILVERADO,
    enableGasInterceptorDEPRECATED=False,
  )
  tuning = LongControl(CP).vehicle_tuning

  tuning.shape_gm_truck_accel_target(0.30, 25.0, False)
  filtered = tuning.shape_gm_truck_accel_target(-0.10, 25.0, False)
  expected = 0.30 + vehicle_tunes.DT_CTRL / (vehicle_tunes.GM_TRUCK_TARGET_FILTER_DOWN_TAU + vehicle_tunes.DT_CTRL) * (-0.40)

  assert filtered == pytest.approx(expected)
  assert filtered > -0.10


def test_gm_stock_truck_target_filter_bypasses_urgent_braking():
  CP = make_longcontrol_cp(
    brand="gm",
    carFingerprint=CAR.CHEVROLET_SILVERADO,
    enableGasInterceptorDEPRECATED=False,
  )
  tuning = LongControl(CP).vehicle_tuning

  tuning.shape_gm_truck_accel_target(0.40, 20.0, False)

  assert tuning.shape_gm_truck_accel_target(-0.70, 20.0, False) == pytest.approx(-0.70)

  tuning.reset()
  tuning.shape_gm_truck_accel_target(0.40, 20.0, False)
  assert tuning.shape_gm_truck_accel_target(-0.10, 20.0, False) == pytest.approx(-0.10)

  tuning.reset()
  tuning.shape_gm_truck_accel_target(0.25, 20.0, False)
  assert tuning.shape_gm_truck_accel_target(0.10, 20.0, True) == pytest.approx(0.10)


def test_gm_stock_truck_target_filter_bypasses_low_speed_and_other_cars():
  truck_cp = make_longcontrol_cp(
    brand="gm",
    carFingerprint=CAR.CHEVROLET_SILVERADO,
    enableGasInterceptorDEPRECATED=False,
  )
  truck_tuning = LongControl(truck_cp).vehicle_tuning
  truck_tuning.shape_gm_truck_accel_target(0.40, 20.0, False)

  bolt_cp = make_longcontrol_cp(
    brand="gm",
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023,
    enableGasInterceptorDEPRECATED=False,
  )
  bolt_tuning = LongControl(bolt_cp).vehicle_tuning

  assert truck_tuning.shape_gm_truck_accel_target(-0.10, 10.0, False) == pytest.approx(-0.10)
  assert bolt_tuning.shape_gm_truck_accel_target(-0.10, 20.0, False) == pytest.approx(-0.10)


def test_santa_fe_final_stop_cap_softens_only_last_kmh():
  CP = make_longcontrol_cp(brand="hyundai", carFingerprint="HYUNDAI_SANTA_FE_2022")
  tuning = LongControl(CP).vehicle_tuning

  assert tuning.shape_stopping_accel(-2.0, -0.2, True, 0.2, False, -2.0) == pytest.approx(-0.30)
  assert tuning.shape_stopping_accel(-2.0, -0.2, True, 1.5, False, -2.0) == pytest.approx(-2.0)
  assert tuning.shape_stopping_accel(-2.0, 0.3, False, 0.2, False, -2.0) == pytest.approx(-2.0)


def test_toyota_sienna_target_filter_smooths_mild_high_speed_handoffs():
  CP = make_longcontrol_cp(brand="toyota", carFingerprint=TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)

  assert tuning.shape_toyota_sienna_accel_target(0.30, 20.0, False) == pytest.approx(0.30)
  filtered = tuning.shape_toyota_sienna_accel_target(-0.20, 20.0, False)

  assert -0.20 < filtered < 0.30


def test_toyota_sienna_2019_target_filter_smooths_mild_high_speed_handoffs():
  CP = make_longcontrol_cp(brand="toyota", carFingerprint="TOYOTA_SIENNA")
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)

  assert tuning.shape_toyota_sienna_accel_target(0.30, 20.0, False) == pytest.approx(0.30)
  filtered = tuning.shape_toyota_sienna_accel_target(-0.20, 20.0, False)

  assert -0.20 < filtered < 0.30


def test_toyota_sienna_target_filter_smooths_nonurgent_low_speed_lead_braking():
  CP = make_longcontrol_cp(brand="toyota", carFingerprint=TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)
  lead = SimpleNamespace(status=True, yRel=0.0, dRel=10.0, vLead=3.5, aLeadK=-0.4)

  tuning.shape_toyota_sienna_accel_target(0.45, 5.0, False, leads=(lead,))
  filtered = tuning.shape_toyota_sienna_accel_target(-1.0, 5.0, False, leads=(lead,))

  assert -1.0 < filtered < 0.45


def test_toyota_sienna_target_filter_keeps_urgent_low_speed_braking():
  CP = make_longcontrol_cp(brand="toyota", carFingerprint=TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)
  lead = SimpleNamespace(status=True, yRel=0.0, dRel=5.0, vLead=0.0, aLeadK=-1.5)

  filtered = tuning.shape_toyota_sienna_accel_target(-1.0, 3.0, False, leads=(lead,))

  assert filtered == pytest.approx(-1.0)


def test_toyota_sienna_target_filter_ramps_out_of_low_speed_braking_with_lead_present():
  CP = make_longcontrol_cp(brand="toyota", carFingerprint=TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)
  lead = SimpleNamespace(status=True, yRel=0.0, dRel=6.5, vLead=1.5, aLeadK=-0.2)

  tuning.shape_toyota_sienna_accel_target(-0.8, 1.5, False, leads=(lead,))
  release = tuning.shape_toyota_sienna_accel_target(0.2, 1.5, False, leads=(lead,))

  assert -0.8 < release < 0.0


def test_toyota_sienna_target_filter_unwinds_braking_before_acceleration():
  CP = make_longcontrol_cp(brand="toyota", carFingerprint=TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)

  tuning.shape_toyota_sienna_accel_target(-1.2, 20.0, False)
  recovering = tuning.shape_toyota_sienna_accel_target(1.2, 20.0, False)

  assert recovering == pytest.approx(-1.1272727273)


def test_toyota_sienna_target_filter_ramps_low_speed_acceleration():
  CP = make_longcontrol_cp(brand="toyota", carFingerprint=TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)

  first = tuning.shape_toyota_sienna_accel_target(1.5, 2.0, False)
  assert 0.0 < first < 1.5

  for _ in range(100):
    filtered = tuning.shape_toyota_sienna_accel_target(1.5, 3.0, False)
  assert filtered < 1.5

  assert tuning.shape_toyota_sienna_accel_target(-1.5, 3.0, False) == pytest.approx(-1.5)


def test_toyota_sienna_caps_acceleration_for_nearby_departing_lead():
  CP = make_longcontrol_cp(brand="toyota", carFingerprint=TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)
  lead = SimpleNamespace(status=True, yRel=0.0, dRel=9.0, vLead=3.0, aLeadK=0.0)

  capped = tuning.cap_toyota_sienna_lead_departure_accel(1.9, 0.8, leads=(lead,))

  assert capped == pytest.approx(1.12)


def test_toyota_sienna_departure_cap_does_not_change_stopped_lead_or_braking():
  CP = make_longcontrol_cp(brand="toyota", carFingerprint=TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)
  stopped_lead = SimpleNamespace(status=True, yRel=0.0, dRel=9.0, vLead=0.0, aLeadK=-1.0)

  assert tuning.cap_toyota_sienna_lead_departure_accel(1.9, 0.8, leads=(stopped_lead,)) == pytest.approx(1.9)
  assert tuning.cap_toyota_sienna_lead_departure_accel(-2.0, 0.8, leads=(stopped_lead,)) == pytest.approx(-2.0)


def test_toyota_sienna_departure_cap_does_not_change_other_vehicles():
  CP = make_longcontrol_cp(brand="toyota", carFingerprint=TOYOTA_CAR.TOYOTA_CAMRY)
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)
  lead = SimpleNamespace(status=True, yRel=0.0, dRel=9.0, vLead=3.0, aLeadK=0.0)

  assert tuning.cap_toyota_sienna_lead_departure_accel(1.9, 0.8, leads=(lead,)) == pytest.approx(1.9)


def test_toyota_sienna_target_filter_bypasses_stop_and_urgent_braking():
  CP = make_longcontrol_cp(brand="toyota", carFingerprint=TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)

  tuning.shape_toyota_sienna_accel_target(0.30, 20.0, False)
  assert tuning.shape_toyota_sienna_accel_target(-0.80, 20.0, False) == pytest.approx(-0.80)
  assert tuning.shape_toyota_sienna_accel_target(-0.20, 20.0, True) == pytest.approx(-0.20)


def test_toyota_sienna_target_filter_smooths_comfortable_lead_braking():
  CP = make_longcontrol_cp(brand="toyota", carFingerprint=TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)
  lead = SimpleNamespace(status=True, yRel=0.0, dRel=24.0, vLead=9.0, aLeadK=-1.2)

  tuning.shape_toyota_sienna_accel_target(0.50, 10.0, False, leads=(lead,))
  filtered = tuning.shape_toyota_sienna_accel_target(-1.5, 10.0, False, leads=(lead,))

  assert -1.5 < filtered < 0.50


def test_toyota_sienna_target_filter_keeps_authority_when_lead_is_urgent():
  CP = make_longcontrol_cp(brand="toyota", carFingerprint=TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)
  lead = SimpleNamespace(status=True, yRel=0.0, dRel=12.0, vLead=2.0, aLeadK=-2.0)

  tuning.shape_toyota_sienna_accel_target(0.50, 12.0, False, leads=(lead,))
  urgent = tuning.shape_toyota_sienna_accel_target(-1.5, 12.0, False, leads=(lead,))

  assert urgent == pytest.approx(-1.5)


def test_toyota_sienna_target_filter_does_not_change_other_vehicles():
  CP = make_longcontrol_cp(brand="toyota", carFingerprint=TOYOTA_CAR.TOYOTA_CAMRY)
  tuning = vehicle_tunes.LongControlVehicleTuning(CP)

  assert tuning.shape_toyota_sienna_accel_target(-0.20, 20.0, False) == pytest.approx(-0.20)


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

  lc.vehicle_tuning.trim_gm_truck_positive_hold_integrator(
    lc.pid, lc.last_output_accel, 0.05, 0.05, CS,
  )

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

  lc.vehicle_tuning.trim_gm_truck_positive_hold_integrator(
    lc.pid, lc.last_output_accel, 0.12, 0.12, CS,
  )

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

  lc.vehicle_tuning.trim_gm_truck_positive_hold_integrator(
    lc.pid, lc.last_output_accel, 0.05, 0.05, CS,
  )

  assert lc.pid.i == pytest.approx(0.25, abs=1e-9)


def test_gm_stock_truck_negative_i_unwinds_when_already_overbraking():
  CP = make_longcontrol_cp(
    brand="gm",
    carFingerprint=CAR.CHEVROLET_SILVERADO,
    enableGasInterceptorDEPRECATED=False,
  )
  lc = LongControl(CP)
  lc.pid.i = -0.22
  lc.last_output_accel = -0.66
  CS = car.CarState.new_message(vEgo=29.6, aEgo=-0.49, brakePressed=False)

  lc.vehicle_tuning.trim_gm_truck_negative_hold_integrator(
    lc.pid, lc.last_output_accel, -0.44, 0.05, CS,
  )

  assert -0.22 < lc.pid.i < 0.0


def test_gm_stock_truck_negative_i_stays_when_decel_is_not_achieved():
  CP = make_longcontrol_cp(
    brand="gm",
    carFingerprint=CAR.CHEVROLET_SILVERADO,
    enableGasInterceptorDEPRECATED=False,
  )
  lc = LongControl(CP)
  lc.pid.i = -0.22
  lc.last_output_accel = -0.66
  CS = car.CarState.new_message(vEgo=29.6, aEgo=0.05, brakePressed=False)

  lc.vehicle_tuning.trim_gm_truck_negative_hold_integrator(
    lc.pid, lc.last_output_accel, -0.44, -0.49, CS,
  )

  assert lc.pid.i == pytest.approx(-0.22, abs=1e-9)


def test_gm_stock_truck_negative_i_stays_for_urgent_braking():
  CP = make_longcontrol_cp(
    brand="gm",
    carFingerprint=CAR.CHEVROLET_SILVERADO,
    enableGasInterceptorDEPRECATED=False,
  )
  lc = LongControl(CP)
  lc.pid.i = -0.22
  lc.last_output_accel = -1.30
  CS = car.CarState.new_message(vEgo=29.6, aEgo=-1.20, brakePressed=False)

  lc.vehicle_tuning.trim_gm_truck_negative_hold_integrator(
    lc.pid, lc.last_output_accel, -1.00, 0.20, CS,
  )

  assert lc.pid.i == pytest.approx(-0.22, abs=1e-9)


def test_gm_stock_truck_negative_i_trim_does_not_affect_other_gm_cars():
  CP = make_longcontrol_cp(
    brand="gm",
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023,
    enableGasInterceptorDEPRECATED=False,
  )
  lc = LongControl(CP)
  lc.pid.i = -0.22
  lc.last_output_accel = -0.66
  CS = car.CarState.new_message(vEgo=29.6, aEgo=-0.49, brakePressed=False)

  lc.vehicle_tuning.trim_gm_truck_negative_hold_integrator(
    lc.pid, lc.last_output_accel, -0.44, 0.05, CS,
  )

  assert lc.pid.i == pytest.approx(-0.22, abs=1e-9)


def test_gm_stock_truck_update_gradually_releases_stale_brake_integral():
  CP = make_longcontrol_cp(
    brand="gm",
    carFingerprint=CAR.CHEVROLET_SILVERADO,
    enableGasInterceptorDEPRECATED=False,
  )
  lc = LongControl(CP)
  lc.pid.i = -0.22
  lc.last_output_accel = -0.66
  CS = car.CarState.new_message(vEgo=29.6, aEgo=-0.49, brakePressed=False)
  CS.cruiseState.standstill = False

  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=-0.44,
    should_stop=False,
    accel_limits=(-3.5, 2.0),
    starpilot_toggles=make_toggles(),
    has_lead=True,
  )

  assert -0.66 < output_accel < -0.44


def test_leaving_experimental_slews_positive_accel():
  CP = make_longcontrol_cp()
  lc = LongControl(CP)
  lc.long_control_state = LongCtrlState.pid
  lc.experimental_mode = True
  lc.current_mode = "blended"
  lc.prev_mode = "acc"
  lc.last_output_accel = 0.05
  CS = car.CarState.new_message(vEgo=20.0, aEgo=0.05, brakePressed=False)
  CS.cruiseState.standstill = False

  lc.experimental_mode = False
  output_accel = lc.update(
    active=True,
    CS=CS,
    a_target=1.5,
    should_stop=False,
    accel_limits=(-3.0, 2.0),
    starpilot_toggles=make_toggles(),
  )

  assert lc.current_mode == "acc"
  assert lc.transitioning
  assert output_accel > 0.05
  assert output_accel < 0.25


def test_leaving_experimental_does_not_reset_mode_transition_timer():
  CP = make_longcontrol_cp()
  lc = LongControl(CP)
  lc.current_mode = "blended"

  lc.update_mpc_mode(False)
  first = lc.mode_transition_timer
  lc.update_mpc_mode(False)

  assert lc.current_mode == "acc"
  assert lc.transitioning
  assert first == pytest.approx(DT_CTRL)
  assert lc.mode_transition_timer == pytest.approx(2.0 * DT_CTRL)

  for _ in range(int(lc.mode_transition_duration / DT_CTRL)):
    lc.update_mpc_mode(False)

  assert not lc.transitioning

