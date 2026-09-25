import pytest

from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.starpilot.lateral.controller_selection import ControllerMode, default_selection, replace_mode, selection_from_bytes
from openpilot.starpilot.lateral.sonata_hybrid_policy import SonataHybridTorquePolicy, supported_cp
from openpilot.starpilot.lateral import sonata_hybrid_shaping as shaping


@pytest.mark.parametrize('speed,accel,jerk,ff,threshold,center,output', [
  [2.0, 0.18, 0.3, 1.0029066557938373, 0.3172954212921375, 0.9974817827847016, 0.9989658177814709],
  [8.0, -0.25, -0.45, 0.8335966434725148, 0.3099892527937427, 0.9999609835312265, 0.9960715403512586],
  [22.0, 0.8, -0.6, 0.8570825555968928, 0.3, 0.9999999999996189, 0.9999994360166975],
  [33.0, -1.4, 0.8, 0.8442122416154261, 0.3, 1.0, 0.9999999999964582],
])
def test_frozen_phase_side_and_center_vectors(speed, accel, jerk, ff, threshold, center, output):
  actual = (shaping.get_sonata_hybrid_ff_scale(accel, jerk, speed), shaping.get_sonata_hybrid_friction_threshold(speed, accel),
            shaping.get_sonata_hybrid_center_taper_scale(accel, speed), shaping.get_sonata_hybrid_center_output_scale(accel, speed))
  assert actual == pytest.approx((ff, threshold, center, output), abs=1e-14, rel=0)


def test_default_startup_raw_limits_and_live_factor_exactly_once():
  cp = interfaces[CAR.HYUNDAI_SONATA_HYBRID].get_non_essential_params(CAR.HYUNDAI_SONATA_HYBRID)
  ci = interfaces[cp.carFingerprint](cp)
  controller = LatControlTorque(cp.as_reader(), ci, .01)
  assert default_selection(cp).policy == 'sonata_hybrid'
  assert isinstance(controller.starpilot_extension.policy, SonataHybridTorquePolicy)
  assert controller.torque_params.latAccelFactor == pytest.approx(cp.lateralTuning.torque.latAccelFactor * 1.05)
  assert controller.pid.pos_limit == pytest.approx(controller.lateral_accel_from_torque(controller.steer_max, cp.lateralTuning.torque))
  for _ in range(3):
    controller.update_torque_parameters(3., .02, .12)
    assert controller.torque_params.latAccelFactor == pytest.approx(3.15)
    assert controller.torque_params.latAccelOffset == pytest.approx(.02)
    assert controller.torque_params.friction == pytest.approx(.12)
  saved = replace_mode(None, cp, ControllerMode.STANDARD)
  assert selection_from_bytes(cp, saved).mode == ControllerMode.STANDARD
  assert LatControlTorque(cp.as_reader(), ci, .01, controller_mode=ControllerMode.STANDARD).starpilot_extension is None


def test_unrelated_and_unadmitted_do_not_select_hybrid_policy():
  cp = interfaces[CAR.HYUNDAI_SONATA_HYBRID].get_non_essential_params(CAR.HYUNDAI_SONATA_HYBRID)
  for field in ('passive', 'dashcamOnly', 'notCar'):
    other = cp.as_reader().as_builder()
    setattr(other, field, True)
    assert not supported_cp(other)
  cp.carFingerprint = CAR.HYUNDAI_SONATA
  assert not supported_cp(cp)
