import math
from pathlib import Path
from types import SimpleNamespace
import tempfile
from unittest.mock import patch

import pytest
from opendbc.car import structs
from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.starpilot.lateral.torque_extension import selected_policy
from openpilot.starpilot.lateral.controller_selection import ControllerMode, turn_assist_supported
from openpilot.starpilot.lateral import ioniq6_policy as policy
from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences


def controller(enabled=False, mode=None, minimum=0.):
  cp = interfaces[CAR.HYUNDAI_IONIQ_6].get_non_essential_params(CAR.HYUNDAI_IONIQ_6)
  cp.minSteerSpeed = minimum
  lac = LatControlTorque(cp.as_reader(), interfaces[CAR.HYUNDAI_IONIQ_6](cp), DT_CTRL,
                         controller_mode=mode, turn_assist=enabled)
  cs = structs.CarState.new_message()
  cs.gearShifter = structs.CarState.GearShifter.drive
  cs.vEgo = 1.
  return cp, lac, cs


def test_default_off_preserves_other_controller_math():
  cp, off, cs = controller()
  _, on, _ = controller(True)
  vm = VehicleModel(cp)
  params = SimpleNamespace(angleOffsetDeg=0., roll=0.)
  original = policy.get_ioniq_6_low_speed_angle_assist_torque
  with patch.object(policy, 'get_ioniq_6_low_speed_angle_assist_torque', wraps=original) as assist:
    off_output, _, off_state = off.update(True, cs, vm, params, False, -.001, False, .1)
    assist.assert_not_called()
    on_output, _, on_state = on.update(True, cs, vm, params, False, -.001, False, .1)
    assert assist.call_count == 1
  for field in ('p', 'i', 'd', 'f', 'error', 'desiredLateralAccel', 'desiredLateralJerk'):
    assert getattr(off_state, field) == getattr(on_state, field)
  assert off_output != on_output
  assert math.isfinite(off_output) and abs(on_output) <= 1.


@pytest.mark.parametrize('field,value', [
  ('vEgo', 0.), ('vEgo', .044703), ('vEgo', -1.), ('vEgo', float('nan')),
  ('vEgo', float('inf')), ('standstill', True), ('steeringPressed', True),
  ('steerFaultTemporary', True), ('steerFaultPermanent', True),
  ('gearShifter', structs.CarState.GearShifter.reverse),
  ('gearShifter', structs.CarState.GearShifter.unknown),
])
def test_assist_rejects_nonrolling_or_faulted_state(field, value):
  _, lac, cs = controller(True)
  setattr(cs, field, value)
  assert not selected_policy(lac).turn_assist_active(cs)


def test_exact_rolling_threshold_and_vehicle_minimum():
  _, lac, cs = controller(True)
  cs.vEgo = .044704
  assert selected_policy(lac).turn_assist_active(cs)
  _, lac, cs = controller(True, minimum=2.)
  assert not selected_policy(lac).turn_assist_active(cs)
  cs.vEgo = 2.
  assert selected_policy(lac).turn_assist_active(cs)


def test_stock_and_unsupported_interfaces_never_gain_policy():
  cp, lac, _ = controller(True, ControllerMode.STANDARD)
  assert selected_policy(lac) is None
  assert turn_assist_supported(cp)
  cp.passive = True
  assert not turn_assist_supported(cp)
  cp.passive = False
  cp.steerControlType = structs.CarParams.SteerControlType.angle
  assert not turn_assist_supported(cp)


def test_startup_saved_exact_on_defaults_and_safe_mode():
  assert not VehicleStartupPreferences().turn_assist
  snapshot = VehicleStartupPreferences(toyota_auto_hold=True)
  assert snapshot.toyota_auto_hold and not snapshot.turn_assist
  with tempfile.TemporaryDirectory() as root:
    source = SimpleNamespace(get_param_path=lambda key: str(Path(root) / key))
    for raw in (None, b'0', b'1', b'', b'true', b'1\n', b'1'*20):
      path = Path(root) / 'TurnAssist'
      path.unlink(missing_ok=True)
      if raw is not None:
        path.write_bytes(raw)
      snapshot = VehicleStartupPreferences.read(source, enabled=True)
      assert snapshot.turn_assist == (raw == b'1')
      path.write_bytes(b'0')
      assert snapshot.turn_assist == (raw == b'1')
    path.write_bytes(b'1')
    assert not VehicleStartupPreferences.read(source, enabled=False).turn_assist
    (Path(root) / 'SafeMode').write_bytes(b'1')
    assert not VehicleStartupPreferences.read(source, enabled=True).turn_assist


def test_enabled_helper_retains_original_large_turn_and_unwind():
  _, lac, cs = controller(True)
  assert selected_policy(lac).turn_assist_active(cs)
  assert policy.get_ioniq_6_low_speed_angle_assist_torque(10., 0., 0., cs.vEgo) == -.39409320626365096
  assert policy.get_ioniq_6_low_speed_angle_assist_torque(0., 10., 0., cs.vEgo) == .07246171113121364


def test_nonfinite_minimum_does_not_admit_assist():
  for minimum in (float('nan'), float('inf')):
    _, lac, cs = controller(True, minimum=minimum)
    assert not selected_policy(lac).turn_assist_active(cs)
