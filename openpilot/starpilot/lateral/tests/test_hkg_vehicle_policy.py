import pytest

from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.starpilot.lateral.controller_selection import ControllerMode, default_selection, replace_mode, selection_from_bytes
from openpilot.starpilot.lateral.hkg_vehicle_policy import HKGVehicleTorquePolicy, PROFILES, policy_for


CASES = [(vehicle, profile, factor) for profile, (vehicles, factor) in PROFILES.items() for vehicle in sorted(vehicles, key=str)]


@pytest.mark.parametrize('vehicle,profile,factor', CASES)
def test_available_exact_profile_preserves_standard_default_and_requires_saved_opt_in(vehicle, profile, factor):
  cp = interfaces[vehicle].get_non_essential_params(vehicle)
  assert policy_for(cp) == profile
  assert default_selection(cp).mode == ControllerMode.STANDARD
  for raw in (b'{', b'{"version":true,"vehicles":{}}', b'{"version":1,"vehicles":{},"vehicles":{}}', b'x' * 4097):
    assert selection_from_bytes(cp, raw).mode == ControllerMode.STANDARD
  saved = replace_mode(None, cp, ControllerMode.STARPILOT)
  choice = selection_from_bytes(cp, saved)
  assert choice.mode == ControllerMode.STARPILOT
  assert choice.policy == profile
  ci = interfaces[vehicle](cp)
  standard = LatControlTorque(cp.as_reader(), ci, 0.01)
  assert standard.starpilot_extension is None
  controller = LatControlTorque(cp.as_reader(), ci, 0.01, controller_mode=choice.mode)
  policy = controller.starpilot_extension.policy
  assert isinstance(policy, HKGVehicleTorquePolicy)
  assert policy.profile == profile
  assert controller.torque_params.latAccelFactor == pytest.approx(cp.lateralTuning.torque.latAccelFactor * factor)
  assert controller.pid.pos_limit == pytest.approx(controller.lateral_accel_from_torque(controller.steer_max, cp.lateralTuning.torque))
  for _ in range(3):
    controller.update_torque_parameters(3.0, 0.02, 0.12)
    assert controller.torque_params.latAccelFactor == pytest.approx(3.0 * factor)
    assert controller.torque_params.latAccelOffset == pytest.approx(0.02)
    assert controller.torque_params.friction == pytest.approx(0.12)
  assert selection_from_bytes(cp, replace_mode(saved, cp, ControllerMode.STANDARD)).mode == ControllerMode.STANDARD


@pytest.mark.parametrize('vehicle,profile,factor', CASES)
def test_unadmitted_and_cross_vehicle_choices_are_not_applied(vehicle, profile, factor):
  cp = interfaces[vehicle].get_non_essential_params(vehicle)
  for field in ('passive', 'dashcamOnly', 'notCar'):
    other = cp.as_reader().as_builder()
    setattr(other, field, True)
    assert policy_for(other) is None
  cp.brand = 'gm'
  assert policy_for(cp) is None
  cp.brand = 'hyundai'
  saved = replace_mode(None, cp, ControllerMode.STARPILOT)
  other = interfaces[CAR.HYUNDAI_IONIQ_5].get_non_essential_params(CAR.HYUNDAI_IONIQ_5)
  if vehicle != CAR.HYUNDAI_IONIQ_5:
    assert selection_from_bytes(other, saved).mode == ControllerMode.STANDARD


@pytest.mark.parametrize('vehicle,profile,factor', CASES)
def test_invalid_torque_contract_cannot_select_vehicle_policy(vehicle, profile, factor):
  cp = interfaces[vehicle].get_non_essential_params(vehicle)
  for field, value in (('latAccelFactor', 0.0), ('latAccelFactor', float('nan')), ('latAccelOffset', float('inf')), ('friction', -1.0)):
    other = cp.as_reader().as_builder()
    setattr(other.lateralTuning.torque, field, value)
    assert policy_for(other) is None
    assert selection_from_bytes(other, None).mode == ControllerMode.STANDARD
  cp.lateralTuning.init('pid')
  assert policy_for(cp) is None
