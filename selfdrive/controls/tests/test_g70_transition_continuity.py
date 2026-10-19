import pytest

from openpilot.selfdrive.controls.lib import latcontrol_vehicle_tunes as tunes


@pytest.mark.parametrize('direction', [-1, 1])
@pytest.mark.parametrize('boundary', ['overshoot', 'jerk', 'center'])
@pytest.mark.parametrize('helper', ['get_genesis_g70_unwind_ff_scale', 'get_genesis_g70_high_speed_error_scale'])
def test_no_step_at_phase_boundary(direction, boundary, helper):
  values = []
  for epsilon in [-1e-7, 1e-7]:
    desired, actual, jerk = 0.8, 1.0, -0.5
    if boundary == 'overshoot':
      actual = desired + epsilon
    elif boundary == 'jerk':
      jerk = epsilon
    else:
      desired = epsilon
    values.append(getattr(tunes, helper)(direction * desired, direction * actual, direction * jerk, 30))
  assert abs(values[1] - values[0]) < 1e-5


@pytest.mark.parametrize('direction', [-1, 1])
def test_unwind_deadzone_continuity(direction):
  for boundary in ['overshoot', 'jerk', 'center']:
    values = []
    for epsilon in [-1e-7, 1e-7]:
      desired, actual, jerk = 0.8, 1.0, -0.5
      if boundary == 'overshoot':
        actual = desired + epsilon
      elif boundary == 'jerk':
        jerk = epsilon
      else:
        desired = epsilon
      values.append(tunes.get_genesis_g70_friction_jerk_deadzone(
        30, direction * desired, direction * jerk, direction * actual))
    assert abs(values[1] - values[0]) < 1e-5


@pytest.mark.parametrize('helper', ['get_genesis_g70_unwind_ff_scale', 'get_genesis_g70_high_speed_error_scale'])
def test_scales_bounded_symmetric_and_inactive_without_overshoot(helper):
  fn = getattr(tunes, helper)
  for desired in [0, 0.05, 0.2, 0.8, 2.0]:
    for actual in [-1, 0, 0.1, 1.0, 2.5]:
      for jerk in [-1, -0.1, 0, 0.1, 1]:
        scale = fn(desired, actual, jerk, 30)
        assert 0.66 <= scale <= 1.0
        assert scale == pytest.approx(fn(-desired, -actual, -jerk, 30))
        if actual <= desired or desired <= 0.1:
          assert scale == 1.0


def test_full_overshoot_blend_preserves_large_error_protection():
  assert tunes.get_genesis_g70_overshoot_blend(0.8, 1.0) == 1.0
  assert tunes.get_genesis_g70_overshoot_blend(-0.8, -1.0) == 1.0
  assert tunes.get_genesis_g70_unwind_ff_scale(0.8, 1.0, -0.5, 30) < 1.0


@pytest.mark.parametrize('direction', [-1, 1])
def test_highway_turn_in_taper_only_near_tracking_target(direction):
  scale = tunes.get_genesis_g70_highway_turn_in_output_scale
  args = (-direction * 0.35, direction * 1.2, direction * 1.08, direction * 0.6, 32.0)
  assert scale(*args) == pytest.approx(0.88)
  assert scale(*args[:-1], 20.0) == 1.0
  assert scale(args[0], args[1], direction * 0.5, args[3], args[4]) == 1.0
  assert scale(args[0], args[1], direction * 1.32, args[3], args[4]) == 1.0
  assert scale(args[0], args[1], args[2], -args[3], args[4]) == 1.0
  assert scale(-args[0], args[1], args[2], args[3], args[4]) == 1.0


@pytest.mark.parametrize('direction', [-1, 1])
def test_highway_turn_in_taper_continuous_at_tracking_boundary(direction):
  scale = tunes.get_genesis_g70_highway_turn_in_output_scale
  values = [scale(-direction * 0.35, direction * 1.2, direction * (1.2 + epsilon),
                  direction * 0.6, 32.0) for epsilon in [-1e-7, 1e-7]]
  assert abs(values[1] - values[0]) < 1e-5
