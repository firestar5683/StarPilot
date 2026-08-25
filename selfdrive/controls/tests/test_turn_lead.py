import math
import types

from cereal import car

import pytest

from openpilot.selfdrive.controls.controlsd import (TWITCH_GUARD_FLOOR, TWITCH_GUARD_MAX_SPEED,
                                                    get_control_lateral_smooth_seconds,
                                                    limit_curvature_to_plan, turn_lead_allowed)


LateralControlMode = car.CarControl.Actuators.LateralControlMode


def _plan(xs, ys):
  return types.SimpleNamespace(position=types.SimpleNamespace(x=xs, y=ys))


STRAIGHT_PLAN = _plan([i * 0.5 for i in range(200)], [0.0] * 200)
STANDSTILL_STUB_PLAN = _plan([0.0, 0.3], [0.0, 0.0])


def _arc_plan(radius):
  return _plan([radius * math.sin(t * 0.006) for t in range(200)],
               [radius * (1.0 - math.cos(t * 0.006)) for t in range(200)])


def test_turn_lead_is_suppressed_only_during_applied_angle_control():
  assert not turn_lead_allowed("rivian", LateralControlMode.angle)
  assert turn_lead_allowed("rivian", LateralControlMode.torque)
  assert turn_lead_allowed("rivian", LateralControlMode.torqueRecovering)
  assert turn_lead_allowed("rivian", LateralControlMode.inactive)
  assert turn_lead_allowed("ford", LateralControlMode.angle)


@pytest.mark.parametrize("v_ego", [0.0, 5.0, 30.0])
def test_non_rivian_control_smoothing_matches_starpilot(v_ego):
  assert get_control_lateral_smooth_seconds("toyota", v_ego, 0.0) == 0.1


@pytest.mark.parametrize(("v_ego", "expected"), [
  (0.0, 0.4),
  (5.0, 0.2),
  (30.0, 0.0),
])
def test_rivian_control_smoothing_remains_speed_scheduled(v_ego, expected):
  assert get_control_lateral_smooth_seconds("rivian", v_ego, 0.4) == pytest.approx(expected)


@pytest.mark.parametrize("curvature", [0.0155, -0.0155])
def test_twitch_against_a_straight_plan_is_clamped_to_the_floor(curvature):
  guarded = limit_curvature_to_plan(STRAIGHT_PLAN, curvature, 1.2)
  assert abs(guarded) == pytest.approx(TWITCH_GUARD_FLOOR)
  assert math.copysign(1.0, guarded) == math.copysign(1.0, curvature)


def test_command_already_below_the_floor_is_untouched():
  assert limit_curvature_to_plan(STRAIGHT_PLAN, 0.0015, 1.2) == pytest.approx(0.0015)


@pytest.mark.parametrize("v_ego", [TWITCH_GUARD_MAX_SPEED, 6.0, 30.0])
def test_guard_is_inactive_above_its_speed_band(v_ego):
  assert limit_curvature_to_plan(STRAIGHT_PLAN, 0.0155, v_ego) == pytest.approx(0.0155)


def test_guard_fades_out_across_the_speed_band():
  full = limit_curvature_to_plan(STRAIGHT_PLAN, 0.0155, 1.2)
  half = limit_curvature_to_plan(STRAIGHT_PLAN, 0.0155, 3.5)
  assert full < half < 0.0155


# turning authority must never be reduced: a real turn's action agrees with its own plan
@pytest.mark.parametrize("ratio", [0.8, 1.0, 2.0, 2.6])
def test_real_turns_tracking_their_own_plan_are_untouched(ratio):
  plan = _arc_plan(7.0)
  action = 0.1428 * ratio
  assert limit_curvature_to_plan(plan, action, 1.2) == pytest.approx(action)


def test_degenerate_plans_do_not_raise_and_still_bound_the_command():
  for plan in (STANDSTILL_STUB_PLAN, _plan([], [])):
    assert abs(limit_curvature_to_plan(plan, 0.0155, 0.4)) == pytest.approx(TWITCH_GUARD_FLOOR)


def test_zero_command_stays_zero():
  assert limit_curvature_to_plan(STRAIGHT_PLAN, 0.0, 1.2) == 0.0
