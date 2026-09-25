"""The selected Ray policy gains reach actual LongControl and pedal CAN output."""

import pytest

from opendbc.can import CANParser
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.ray_pedal import RAY_PEDAL_COMMAND_CAP, longitudinal_policy_for, ray_pedal_enabled
from opendbc.car.hyundai.tests import test_ray_pedal as fixtures
from opendbc.car.hyundai.values import CAR, RAY_PEDAL_SAFETY_PARAM
from openpilot.selfdrive.controls.lib.longcontrol import LongControl


@pytest.mark.parametrize('speed, kp, ki', [(0.0, 0.095, 0.07), (5.0, 0.085, 0.13333333333333333), (15.0, 0.065, 0.17793103448275863), (35.0, 0.05, 0.24)])
def test_factory_selected_pid_is_consumed_and_actual_pedal_stays_bounded(speed, kp, ki):
  cp, controller, cc, cs = fixtures.ray_controller()
  assert ray_pedal_enabled(cp)
  assert cp.safetyConfigs[-1].safetyParam == RAY_PEDAL_SAFETY_PARAM == 0x9805
  assert list(cp.longitudinalTuning.kiBP) == [0.0, 3.0, 6.0, 35.0]
  assert list(cp.longitudinalTuning.kiV) == pytest.approx([0.07, 0.10, 0.15, 0.24])
  cs.out.vEgo = speed
  cs.out.aEgo = 0.0
  cs.out.canValid = True
  long_control = LongControl(cp)
  assert long_control.extension is not None
  assert long_control.extension.kp == ((0.0, 5.0, 15.0, 35.0), (0.095, 0.085, 0.065, 0.05))
  limits = CarInterface.get_pid_accel_limits(cp, speed, 20.0)
  requested = long_control.update(True, cs.out, 0.3, False, limits)
  assert long_control.pid.k_p == pytest.approx(kp)
  assert long_control.pid.k_i == pytest.approx(ki)
  assert long_control.pid.p == pytest.approx(kp * 0.3)
  assert long_control.pid.f == pytest.approx(0.3)
  assert limits[0] <= requested <= limits[1]
  cc.actuators.accel = float(requested)
  cc.hudControl.setSpeed = min(speed + 2.0, 40.0)
  controller.frame = 4
  output, messages = controller.update(cc.as_reader(), cs, 1_000_000_000)
  pedal = [m for m in messages if m[0] == 0x200]
  assert len(pedal) == 1
  parser = CANParser('hyundai_kia_ray_pedal', [('GAS_COMMAND', 0)], 0)
  parser.update([(1_000_000_000, pedal)])
  assert parser.vl['GAS_COMMAND']['ENABLE'] in (0, 1)
  assert 0.0 <= controller._ray_pedal_gas_last <= RAY_PEDAL_COMMAND_CAP
  assert cp.safetyConfigs[-1].safetyParam == 0x9805
  assert output.accel == pytest.approx(requested)
  cc.longActive = False
  controller.frame = 8
  _, messages = controller.update(cc.as_reader(), cs, 1_010_000_000)
  parser.update([(1_010_000_000, [m for m in messages if m[0] == 0x200])])
  assert parser.vl['GAS_COMMAND']['ENABLE'] == 0
  assert controller._ray_pedal_gas_last == 0.0


@pytest.mark.parametrize('sensor, lfa', [(8, 8), (6, 4)])
def test_missing_physical_ray_layout_does_not_select_pid_owner(sensor, lfa):
  cp = CarInterface.get_params(CAR.KIA_RAY_EV, fixtures.ray_fingerprint(sensor=sensor, lfa=lfa), [], False, False, False)
  assert not ray_pedal_enabled(cp)
  assert longitudinal_policy_for(cp) is None
  assert not cp.openpilotLongitudinalControl
  assert cp.pcmCruise


@pytest.mark.parametrize('field', ['passive', 'dashcamOnly', 'notCar'])
def test_startup_denial_never_selects_ray_owner(field):
  cp, _, _, _ = fixtures.ray_controller()
  setattr(cp, field, True)
  assert not ray_pedal_enabled(cp)
  assert longitudinal_policy_for(cp) is None
