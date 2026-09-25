"""Firmware buffer representation must not change the selected Ioniq 6 controller."""

from types import SimpleNamespace

import pytest

from opendbc.car import structs
from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.starpilot.lateral.controller_selection import ControllerMode
from openpilot.starpilot.lateral.ioniq6_policy import is_ioniq_6_2025_model
from openpilot.starpilot.lateral.torque_extension import selected_policy


class FirmwareReader:
  """Expose a bytes-like firmware boundary while preserving the real factory CarParams."""

  def __init__(self, cp, versions):
    self.cp = cp
    self.carFw = [SimpleNamespace(fwVersion=version) for version in versions]

  def __getattr__(self, name):
    return getattr(self.cp, name)


@pytest.mark.parametrize('buffer_type', [bytes, bytearray, memoryview])
@pytest.mark.parametrize('versions, expected', [([b'IONIQ6-230915', b'IONIQ6-240206'], True), ([b'IONIQ6-230915'], False), ([], False)])
def test_real_controller_firmware_selection_and_output_match_bytes(buffer_type, versions, expected):
  cp = interfaces[CAR.HYUNDAI_IONIQ_6].get_non_essential_params(CAR.HYUNDAI_IONIQ_6)
  native = cp.init('carFw', len(versions))
  for fw, version in zip(native, versions, strict=True):
    fw.fwVersion = version
  ci = interfaces[CAR.HYUNDAI_IONIQ_6](cp)
  wrapped = FirmwareReader(cp.as_reader(), [buffer_type(version) for version in versions])
  assert is_ioniq_6_2025_model(wrapped) is expected
  baseline = LatControlTorque(cp.as_reader(), ci, DT_CTRL, controller_mode=ControllerMode.STARPILOT)
  actual = LatControlTorque(wrapped, ci, DT_CTRL, controller_mode=ControllerMode.STARPILOT)
  actual_policy = selected_policy(actual)
  baseline_policy = selected_policy(baseline)
  assert actual_policy is not None and baseline_policy is not None
  assert actual_policy.is_2025 is expected
  assert baseline_policy.is_2025 is expected
  assert actual.torque_params.to_dict() == baseline.torque_params.to_dict()
  assert (actual.pid.pos_limit, actual.pid.neg_limit) == (baseline.pid.pos_limit, baseline.pid.neg_limit)
  state = structs.CarState()
  state.gearShifter = structs.CarState.GearShifter.drive
  params = SimpleNamespace(angleOffsetDeg=0.0, roll=0.0)
  for speed, curvature, pressed in ((2.0, 0.0001, False), (12.0, -0.0003, False), (20.0, 0.0004, True)):
    state.vEgo = speed
    state.steeringPressed = pressed
    args = (True, state, VehicleModel(cp), params, False, curvature, False, 0.1)
    actual_output = actual.update(*args)
    baseline_output = baseline.update(*args)
    assert actual_output[0:2] == baseline_output[0:2]
    assert actual_output[2].to_dict() == baseline_output[2].to_dict()


@pytest.mark.parametrize(
  'cp',
  [
    SimpleNamespace(carFingerprint=CAR.HYUNDAI_IONIQ_6),
    SimpleNamespace(carFingerprint=CAR.HYUNDAI_IONIQ_6, carFw=None),
    SimpleNamespace(carFingerprint=CAR.HYUNDAI_IONIQ_5, carFw=[SimpleNamespace(fwVersion=b'230915 240206')]),
  ],
)
def test_missing_or_other_vehicle_firmware_keeps_standard_gate(cp):
  assert not is_ioniq_6_2025_model(cp)
