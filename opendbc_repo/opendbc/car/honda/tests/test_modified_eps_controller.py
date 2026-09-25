import pytest

from opendbc.car import structs
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.tests.test_modified_eps import KNOWN_CASES, eps, params
from opendbc.car.honda.values import CAR


@pytest.mark.parametrize("identity,firmware", KNOWN_CASES)
def test_actual_modified_factory_controller_consumes_separate_lookup(identity, firmware):
  cp = params(identity, [eps(firmware)])
  ci = CarInterface(cp)
  ci.update([])
  cc = structs.CarControl(latActive=True)
  cc.actuators.torque = 1.0
  emitted = []
  for tick in range(250):
    actuators, frames = ci.apply(cc.as_reader(), 1_000_000_000 + tick * 10_000_000)
    assert frames
    emitted.append(actuators.torqueOutputCan)
  expected_max = 3840 if identity in (CAR.HONDA_CIVIC, CAR.HONDA_CRV_5G) else ci.CC.params.STEER_MAX
  assert max(abs(value) for value in emitted) <= expected_max
  assert abs(emitted[-1]) >= expected_max - 1
  assert (ci.CC.modified_civic_steering is not None) == (identity == CAR.HONDA_CIVIC_BOSCH)


def test_actual_modified_civic_driver_override_and_inactive_reset():
  cp = params(CAR.HONDA_CIVIC_BOSCH, [eps(b'39990-TGG,A020\x00\x00')])
  ci = CarInterface(cp)
  ci.update([])
  cc = structs.CarControl(latActive=True)
  cc.actuators.torque = 0.8
  for tick in range(20):
    ci.CS.out = structs.CarState(vEgo=15.0, steeringPressed=True, steeringTorque=-1.0).as_reader()
    ci.apply(cc.as_reader(), 1_000_000_000 + tick * 10_000_000)
  owner = ci.CC.modified_civic_steering
  assert owner.steering_pressed_robust_prev
  assert owner.torque_lpf == owner.prev_torque_cmd == 0.0
  cc.latActive = False
  ci.apply(cc.as_reader(), 1_200_000_000)
  assert owner.steering_pressed_filter_s == 0.0
  assert not owner.steering_pressed_robust_prev


def test_ordinary_civic_has_no_modified_filter_owner():
  ci = CarInterface(params(CAR.HONDA_CIVIC_BOSCH, [eps(b'39990-TBA-C120\x00\x00')]))
  assert ci.CC.modified_civic_steering is None
