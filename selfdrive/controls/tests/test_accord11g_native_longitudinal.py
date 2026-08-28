from types import SimpleNamespace

import numpy as np
import pytest

from openpilot.selfdrive.controls.lib.longitudinal_planner import (
  CONTROL_N_T_IDX,
  get_accel_from_plan,
  get_max_accel,
  limit_accel_in_turns,
)
from openpilot.selfdrive.controls.lib.longitudinal_vehicle_tunes import (
  get_honda_accord_11g_accel_clip_slew_step,
  get_honda_accord_11g_allow_throttle,
  get_honda_accord_11g_cruise_accel_max,
  get_honda_accord_11g_min_action_delay,
  get_honda_accord_11g_no_throttle_accel_max,
  get_honda_accord_11g_reduction_only_v_cruise,
  get_honda_accord_11g_throttle_policy,
  get_honda_accord_11g_total_accel_max,
  is_honda_accord_11g,
)


def make_cp(brand="honda", fingerprint="HONDA_ACCORD_11G"):
  return SimpleNamespace(brand=brand, carFingerprint=fingerprint)


@pytest.mark.parametrize("brand, fingerprint", [
  ("honda", "HONDA_ACCORD"),
  ("honda", "HONDA_CIVIC_BOSCH"),
  ("toyota", "HONDA_ACCORD_11G"),
  ("toyota", "TOYOTA_RAV4"),
])
def test_accord11g_native_contract_is_exactly_platform_scoped(brand, fingerprint):
  other = make_cp(brand, fingerprint)

  assert not is_honda_accord_11g(other)
  assert get_honda_accord_11g_cruise_accel_max(other, 10.0) is None
  assert get_honda_accord_11g_total_accel_max(other, 20.0) is None
  assert get_honda_accord_11g_throttle_policy(other) is None
  assert get_honda_accord_11g_min_action_delay(other) is None
  assert get_honda_accord_11g_accel_clip_slew_step(other) is None
  assert get_honda_accord_11g_reduction_only_v_cruise(other, 20.0, 15.0) is None


@pytest.mark.parametrize("v_ego, expected", [
  (-1.0, 1.6),
  (0.0, 1.6),
  (5.0, 1.4),
  (10.0, 1.2),
  (17.5, 1.0),
  (25.0, 0.8),
  (32.5, 0.7),
  (40.0, 0.6),
  (50.0, 0.6),
])
def test_accord11g_cruise_accel_ceiling_matches_validated_curve(v_ego, expected):
  assert get_honda_accord_11g_cruise_accel_max(make_cp(), v_ego) == pytest.approx(expected)


@pytest.mark.parametrize("v_ego, expected", [
  (0.0, 1.7),
  (20.0, 1.7),
  (30.0, 2.45),
  (40.0, 3.2),
  (50.0, 3.2),
])
def test_accord11g_total_accel_envelope_matches_validated_curve(v_ego, expected):
  assert get_honda_accord_11g_total_accel_max(make_cp(), v_ego) == pytest.approx(expected)


def test_accord11g_scalar_planner_contract_matches_road_validated_values():
  accord = make_cp()

  assert is_honda_accord_11g(accord)
  assert get_honda_accord_11g_throttle_policy(accord) == pytest.approx((0.4, 2.5))
  assert get_honda_accord_11g_min_action_delay(accord) == pytest.approx(0.3)
  assert get_honda_accord_11g_accel_clip_slew_step(accord) == pytest.approx(0.05)


@pytest.mark.parametrize("starpilot_v_cruise, expected", [
  (15.0, 15.0),
  (20.0, 20.0),
  (25.0, 20.0),
  (float("nan"), 20.0),
  (-1.0, 20.0),
])
def test_accord11g_starpilot_v_cruise_is_reduction_only(starpilot_v_cruise, expected):
  assert get_honda_accord_11g_reduction_only_v_cruise(make_cp(), 20.0, starpilot_v_cruise) == pytest.approx(expected)


@pytest.mark.parametrize("throttle_prob, v_ego, expected", [
  (0.41, 10.0, True),
  (0.40, 10.0, False),
  (0.0, 2.5, True),
  (0.0, 2.51, False),
])
def test_accord11g_throttle_gate_matches_validated_policy(throttle_prob, v_ego, expected):
  assert get_honda_accord_11g_allow_throttle(make_cp(), throttle_prob, v_ego) is expected
  assert get_honda_accord_11g_allow_throttle(make_cp(fingerprint="HONDA_CIVIC_BOSCH"), throttle_prob, v_ego) is None


@pytest.mark.parametrize("v_ego, accel_coast, expected", [
  (2.5, -0.3, 1.6),
  (3.75, -0.3, 0.65),
  (5.0, -0.3, -0.3),
  (5.0, -5.0, -3.5),
])
def test_accord11g_no_throttle_coast_cap_matches_validated_interpolation(v_ego, accel_coast, expected):
  assert get_honda_accord_11g_no_throttle_accel_max(
    make_cp(), v_ego, accel_min=-3.5, accel_max=1.6, accel_coast=accel_coast,
  ) == pytest.approx(expected)
  assert get_honda_accord_11g_no_throttle_accel_max(
    make_cp(fingerprint="HONDA_CIVIC_BOSCH"), v_ego, accel_min=-3.5, accel_max=1.6, accel_coast=accel_coast,
  ) is None


def test_native_planner_uses_accord11g_acceleration_envelopes_only_for_accord():
  accord = SimpleNamespace(brand="honda", carFingerprint="HONDA_ACCORD_11G", steerRatio=15.0, wheelbase=2.8)
  civic = SimpleNamespace(brand="honda", carFingerprint="HONDA_CIVIC_BOSCH", steerRatio=15.0, wheelbase=2.8)

  assert get_max_accel(17.5, accord) == pytest.approx(1.0)
  assert get_max_accel(17.5, civic) == pytest.approx(1.1875)
  assert limit_accel_in_turns(30.0, 0.0, [-3.5, 10.0], accord) == pytest.approx([-3.5, 2.45])
  assert limit_accel_in_turns(30.0, 0.0, [-3.5, 10.0], civic) == pytest.approx([-3.5, 3.35])


def test_native_plan_projection_uses_accord11g_stable_delay_without_changing_default():
  control_t = np.asarray(CONTROL_N_T_IDX)
  speeds = 10.0 + control_t ** 2
  accels = np.zeros_like(control_t)
  action_t = 0.2
  stable_delay = 0.3
  stable_speed = float(np.interp(stable_delay, CONTROL_N_T_IDX, speeds))
  expected_stable_target = float(speeds[0] + (action_t / stable_delay) * (stable_speed - speeds[0]))
  expected_stable_accel = 2.0 * (expected_stable_target - speeds[0]) / action_t
  expected_default_target = float(np.interp(action_t, CONTROL_N_T_IDX, speeds))
  expected_default_accel = 2.0 * (expected_default_target - speeds[0]) / action_t

  stable_accel, stable_should_stop = get_accel_from_plan(
    speeds, accels, action_t=action_t, min_stable_delay=stable_delay,
  )
  default_accel, default_should_stop = get_accel_from_plan(speeds, accels, action_t=action_t)

  assert stable_accel == pytest.approx(expected_stable_accel)
  assert default_accel == pytest.approx(expected_default_accel)
  assert stable_accel != pytest.approx(default_accel)
  assert not stable_should_stop
  assert not default_should_stop
