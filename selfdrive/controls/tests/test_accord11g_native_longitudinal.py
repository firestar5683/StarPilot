from types import SimpleNamespace

import pytest

from openpilot.selfdrive.controls.lib.longitudinal_vehicle_tunes import (
  get_honda_accord_11g_accel_clip_slew_step,
  get_honda_accord_11g_cruise_accel_max,
  get_honda_accord_11g_min_action_delay,
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
