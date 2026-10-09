import pytest

from openpilot.common.constants import CV
from openpilot.common.pid import PIDController
from openpilot.selfdrive.controls.lib.latcontrol_vehicle_tunes import get_honda_crv_5g_pid_kp_scale


@pytest.mark.parametrize('mph', [0.0, 3.0, 6.0, 8.0, 11.0])
@pytest.mark.parametrize('angle', [-6.0, -3.0, 0.0, 3.0, 6.0])
def test_low_speed_center_gain(mph, angle):
  assert get_honda_crv_5g_pid_kp_scale(angle, mph * CV.MPH_TO_MS) == 0.5


@pytest.mark.parametrize('mph', [18.0, 25.0, 45.0, 70.0])
@pytest.mark.parametrize('angle', [-30.0, -6.0, 0.0, 6.0, 30.0])
def test_normal_speed_gain_unchanged(mph, angle):
  assert get_honda_crv_5g_pid_kp_scale(angle, mph * CV.MPH_TO_MS) == 1.0


@pytest.mark.parametrize('mph', [0.0, 8.0, 14.0])
@pytest.mark.parametrize('angle', [-90.0, -30.0, -18.0, 18.0, 30.0, 90.0])
def test_real_turn_gain_unchanged(mph, angle):
  assert get_honda_crv_5g_pid_kp_scale(angle, mph * CV.MPH_TO_MS) == 1.0


def test_gain_is_bounded_symmetric_and_monotonic():
  for mph in [0, 8, 11, 12, 14, 16, 18, 45]:
    scales = [get_honda_crv_5g_pid_kp_scale(angle, mph * CV.MPH_TO_MS) for angle in [0, 6, 9, 12, 15, 18, 30]]
    assert scales == sorted(scales)
    assert all(0.5 <= value <= 1.0 for value in scales)
    for angle in [0, 6, 9, 12, 15, 18, 30]:
      assert get_honda_crv_5g_pid_kp_scale(angle, mph * CV.MPH_TO_MS) == get_honda_crv_5g_pid_kp_scale(-angle, mph * CV.MPH_TO_MS)
  scales = [get_honda_crv_5g_pid_kp_scale(0.0, mph * CV.MPH_TO_MS) for mph in [0, 8, 11, 12, 14, 16, 18, 45]]
  assert scales == sorted(scales)


@pytest.mark.parametrize('mph', [11.0, 18.0])
def test_speed_boundary_continuity(mph):
  left = get_honda_crv_5g_pid_kp_scale(0.0, (mph - 1e-7) * CV.MPH_TO_MS)
  right = get_honda_crv_5g_pid_kp_scale(0.0, (mph + 1e-7) * CV.MPH_TO_MS)
  assert abs(left - right) < 1e-7


@pytest.mark.parametrize('angle', [-18.0, -6.0, 6.0, 18.0])
def test_angle_boundary_continuity(angle):
  left = get_honda_crv_5g_pid_kp_scale(angle - 1e-7, 8.0 * CV.MPH_TO_MS)
  right = get_honda_crv_5g_pid_kp_scale(angle + 1e-7, 8.0 * CV.MPH_TO_MS)
  assert abs(left - right) < 1e-7


def test_gain_reduces_feedback_before_saturation_without_changing_feedforward_or_integral():
  base = PIDController(0.64, 0.192, pos_limit=1, neg_limit=-1)
  tuned = PIDController(0.64 * get_honda_crv_5g_pid_kp_scale(3.0, 8.0 * CV.MPH_TO_MS), 0.192, pos_limit=1, neg_limit=-1)
  base.i = tuned.i = -0.019
  base_output = base.update(2.0, feedforward=0.004, freeze_integrator=True)
  tuned_output = tuned.update(2.0, feedforward=0.004, freeze_integrator=True)
  assert base_output == 1.0
  assert tuned_output == pytest.approx(0.625)
  assert tuned.p == pytest.approx(base.p * 0.5)
  assert tuned.i == base.i
  assert tuned.f == base.f
