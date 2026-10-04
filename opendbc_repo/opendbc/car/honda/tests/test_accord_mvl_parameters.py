import pytest

from opendbc.car import gen_empty_fingerprint, STD_CARGO_KG
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR


@pytest.mark.parametrize("alpha", (False, True))
@pytest.mark.parametrize("release", (False, True))
@pytest.mark.parametrize("alternate_brake", (False, True))
def test_original_accord11_geometry_and_stock_controller_parameters(alpha, release, alternate_brake):
  fp = gen_empty_fingerprint()
  fp[0][0x1A3] = 8
  if alternate_brake:
    fp[0][0x1BE] = 3
  cp = CarInterface.get_params(CAR.HONDA_ACCORD_11G, fp, [], alpha, release, False)
  assert cp.steerRatio == pytest.approx(16.7)
  assert cp.mass == pytest.approx(3477 * CV.LB_TO_KG + STD_CARGO_KG)
  assert cp.wheelbase == pytest.approx(2.83)
  assert cp.centerToFront == pytest.approx(2.83 * 0.39)
  assert cp.tireStiffnessFactor == pytest.approx(1.0)
  assert cp.steerActuatorDelay == pytest.approx(0.3)
  assert cp.longitudinalActuatorDelay == pytest.approx(0.05)
  assert cp.lateralTuning.which() == "pid"
  assert cp.lateralTuning.pid.kf == pytest.approx(0.000035)
  assert list(cp.lateralTuning.pid.kpBP) == [0.0]
  assert list(cp.lateralTuning.pid.kiBP) == [0.0]
  assert list(cp.lateralTuning.pid.kpV) == pytest.approx([0.115])
  assert list(cp.lateralTuning.pid.kiV) == pytest.approx([0.052])
  assert cp.safetyConfigs[-1].safetyParam == (81 if alternate_brake else 80)
  assert cp.pcmCruise and not cp.openpilotLongitudinalControl
  assert not cp.alphaLongitudinalAvailable
  ci = CarInterface(cp)
  assert ci.CC.CP.steerRatio == pytest.approx(16.7)
  assert ci.CC.accord_mvl_stock is not None
  assert ci.CC.params.STEER_MAX == 12789
  assert ci.CC.params.STEER_LOOKUP == [-12789, 0, 12789]
  assert ci.CC.params.STEER_LOOKUP_V == [-12789, 0, 12789]

  assert ci.CC.params.BOSCH_GAS_LOOKUP_BP == [0.0, 2.0]
  from opendbc.can import CANParser
  from opendbc.car import Bus, structs
  from opendbc.car.honda.values import DBC
  ci.update([])
  command = structs.CarControl(enabled=True, latActive=True)
  command.actuators.torque = 0.6
  parser = CANParser(DBC[CAR.HONDA_ACCORD_11G][Bus.pt], [("STEERING_CONTROL", 100)], ci.CC.CAN.lkas)
  limited = 0.0
  for tick in range(25):
    now = 1_000_000_000 + tick * 10_000_000
    _, messages = ci.apply(command.as_reader(), now)
    steering = [message for message in messages if message[0] == 0xE4]
    assert len(steering) == 1
    parser.update([(now, steering)])
    limited = min(0.6, limited + 0.03)
    assert parser.vl["STEERING_CONTROL"]["STEER_TORQUE"] == int(-limited * 12789)
