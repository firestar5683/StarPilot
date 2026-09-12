import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from cereal import car
from opendbc.car import gen_empty_fingerprint
from opendbc.car.tesla.carcontroller import CarController
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.values import CAR, DBC, TeslaSafetyFlags


BASELINE_SHA = "a80064be4fdf4b8765a5e9dec44d8a5c266f48a8"
BASELINE_SOURCE_SHA256 = {
  "opendbc_repo/opendbc/car/tesla/coop_steering.py": "9c9d60bbfae2aaa0d8c1fca203a9fa19a14a19feef5aa89e85ecaa6f6502a9f0",
  "opendbc_repo/opendbc/car/tesla/carcontroller.py": "1ef3cf646bc4b3c398bd12010e624b90e083426152d632fafb5b2e93fd3d8661",
}
BASELINE_FIXTURE = Path(__file__).parent / "fixtures" / "coop_steering_baseline_a80064be.json"


def make_params(candidate=CAR.TESLA_MODEL_3, cooperative=True):
  toggles = SimpleNamespace(tesla_cooperative_steering=cooperative, trailer_load_kg=0.0)
  return CarInterface.get_params(candidate, gen_empty_fingerprint(), [], False, False, False, toggles)


def make_car_state(torque=0.0, speed=15.0, angle=0.0, steering_disengage=False):
  return SimpleNamespace(
    out=SimpleNamespace(
      steeringTorque=torque,
      steeringAngleDeg=angle,
      steeringDisengage=steering_disengage,
      vEgo=speed,
      vEgoRaw=speed,
      gasPressed=False,
    ),
    hands_on_level=0,
    das_control={"DAS_controlCounter": 0},
  )


def make_control(requested_angle=0.0, lat_active=True):
  control = car.CarControl.new_message()
  control.latActive = lat_active
  control.actuators.steeringAngleDeg = requested_angle
  return control.as_reader()


def make_controller(candidate=CAR.TESLA_MODEL_3, cooperative=True):
  params = make_params(candidate, cooperative)
  return CarController(DBC[candidate], params)


def run_frame(controller, requested_angle=0.0, torque=0.0, speed=15.0, measured_angle=0.0,
              lat_active=True, steering_disengage=False, now_nanos=1_000_000_000):
  return controller.update(
    make_control(requested_angle, lat_active),
    make_car_state(torque, speed, measured_angle, steering_disengage),
    now_nanos,
    SimpleNamespace(),
  )


def legacy_actuator_dict(actuators):
  values = actuators.to_dict()
  values.pop("steeringLimitInfo", None)
  return values


def test_steering_limit_info_defaults_to_invalid():
  actuators = car.CarControl.Actuators.new_message()

  assert not actuators.steeringLimitInfo.valid


def test_steering_limit_info_round_trips_through_car_output():
  output = car.CarOutput.new_message()
  info = output.actuatorsOutput.steeringLimitInfo
  info.valid = True
  info.modelLimitErrorDeg = 1.25
  info.resumeLimitErrorDeg = 0.5
  info.cooperativeLimitErrorDeg = 2.0
  info.cooperativeOffsetDeg = -4.5
  info.monoTime = 1_234_567_890
  info.combinedLimitErrorDeg = 3.75

  with car.CarOutput.from_bytes(output.to_bytes()) as restored:
    restored_info = restored.actuatorsOutput.steeringLimitInfo
    assert restored_info.valid
    assert restored_info.modelLimitErrorDeg == 1.25
    assert restored_info.resumeLimitErrorDeg == 0.5
    assert restored_info.cooperativeLimitErrorDeg == 2.0
    assert restored_info.cooperativeOffsetDeg == -4.5
    assert restored_info.monoTime == 1_234_567_890
    assert restored_info.combinedLimitErrorDeg == 3.75


def test_active_cooperative_controller_publishes_r_n_a_t_f_diagnostics():
  controller = make_controller()
  requested_angle = 20.0
  now_nanos = 1_234_567_890

  actuators, _ = run_frame(controller, requested_angle, torque=0.9, measured_angle=0.0, now_nanos=now_nanos)

  info = actuators.steeringLimitInfo
  assert info.valid
  assert info.monoTime == now_nanos
  assert info.modelLimitErrorDeg == pytest.approx(abs(requested_angle - controller.apply_angle_last), abs=1e-5)
  assert info.resumeLimitErrorDeg == pytest.approx(controller.coop_steer.resume_limit_error_deg, abs=1e-5)
  assert info.cooperativeLimitErrorDeg == pytest.approx(controller.coop_steer.cooperative_limit_error_deg, abs=1e-5)
  assert info.cooperativeOffsetDeg == pytest.approx(controller.coop_steer.cooperative_offset_deg, abs=1e-5)
  assert info.combinedLimitErrorDeg == pytest.approx(
    abs(requested_angle + info.cooperativeOffsetDeg - actuators.steeringAngleDeg), abs=1e-5,
  )
  assert info.modelLimitErrorDeg > 2.5
  assert info.cooperativeOffsetDeg > 0.0
  assert info.combinedLimitErrorDeg > 2.5
  errors = (info.modelLimitErrorDeg, info.resumeLimitErrorDeg,
            info.cooperativeLimitErrorDeg, info.combinedLimitErrorDeg)
  assert all(math.isfinite(error) and error >= 0.0 for error in errors)


def test_cooperative_offset_alone_does_not_become_limiter_error():
  controller = make_controller()
  actuators = None

  for frame in range(200):
    actuators, _ = run_frame(controller, torque=0.9, now_nanos=1_000_000_000 + frame * 10_000_000)

  assert actuators is not None
  info = actuators.steeringLimitInfo
  assert info.valid
  assert info.cooperativeOffsetDeg > 2.5
  assert info.modelLimitErrorDeg < 2.5
  assert info.resumeLimitErrorDeg < 2.5
  assert info.cooperativeLimitErrorDeg < 2.5
  assert info.combinedLimitErrorDeg < 2.5


def test_combined_error_keeps_two_same_direction_small_limits_visible():
  controller = make_controller()
  # Prime the resume limiter to the first-stage output for this literal input.
  controller.coop_steer.reset_resume_state(-0.9954867959022522)

  actuators, _ = run_frame(controller, -2.5, torque=-1.5, speed=12.5, measured_angle=0.0)

  info = actuators.steeringLimitInfo
  assert info.modelLimitErrorDeg == pytest.approx(1.5045133, abs=1e-5)
  assert info.resumeLimitErrorDeg == pytest.approx(0.0, abs=1e-5)
  assert info.cooperativeLimitErrorDeg == pytest.approx(1.5045133, abs=1e-5)
  assert info.modelLimitErrorDeg < 2.5
  assert info.cooperativeLimitErrorDeg < 2.5
  assert info.combinedLimitErrorDeg == pytest.approx(3.0090265, abs=1e-5)
  assert info.combinedLimitErrorDeg > 2.5


def test_intervening_100hz_frame_retains_matching_50hz_sample():
  controller = make_controller()
  first, _ = run_frame(controller, 8.0, torque=0.9, now_nanos=1_000_000_000)
  first_info = first.steeringLimitInfo.to_dict()

  second, _ = run_frame(controller, -40.0, torque=-1.5, now_nanos=1_010_000_000)

  assert second.steeringLimitInfo.to_dict() == first_info
  assert second.steeringLimitInfo.monoTime == 1_000_000_000


def test_inactive_interval_clears_sample_until_next_steering_update():
  controller = make_controller()
  active, _ = run_frame(controller, 8.0, torque=0.9, now_nanos=1_000_000_000)
  assert active.steeringLimitInfo.valid

  inactive, _ = run_frame(controller, 8.0, torque=0.9, lat_active=False, now_nanos=1_010_000_000)
  assert not inactive.steeringLimitInfo.valid
  assert inactive.steeringLimitInfo.monoTime == 0

  resumed, _ = run_frame(controller, 8.0, torque=0.9, now_nanos=1_020_000_000)
  assert resumed.steeringLimitInfo.valid
  assert resumed.steeringLimitInfo.monoTime == 1_020_000_000


@pytest.mark.parametrize(("candidate", "cooperative", "steering_disengage"), (
  (CAR.TESLA_MODEL_3, False, False),
  (CAR.TESLA_MODEL_Y, True, False),
  (CAR.TESLA_MODEL_3, True, True),
))
def test_diagnostics_invalid_when_not_in_supported_active_path(candidate, cooperative, steering_disengage):
  controller = make_controller(candidate, cooperative)

  actuators, _ = run_frame(controller, torque=1.5, steering_disengage=steering_disengage)

  assert not actuators.steeringLimitInfo.valid
  assert actuators.steeringLimitInfo.monoTime == 0


def test_actual_actuators_and_steering_can_match_pinned_baseline_fixture():
  fixture = json.loads(BASELINE_FIXTURE.read_text())
  assert fixture["metadata"] == {
    "schemaVersion": 1,
    "baselineSha": BASELINE_SHA,
    "baselineSourceSha256": BASELINE_SOURCE_SHA256,
    "frameCount": 386,
  }

  candidate = make_controller()
  for expected in fixture["frames"]:
    inputs = expected["input"]
    candidate_actuators, candidate_can = run_frame(
      candidate,
      inputs["requestedAngleDeg"],
      inputs["torqueNm"],
      inputs["speedMps"],
      inputs["measuredAngleDeg"],
      inputs["latActive"],
      inputs["steeringDisengage"],
      inputs["nowNanos"],
    )

    assert legacy_actuator_dict(candidate_actuators) == expected["actuators"]
    assert [[address, data.hex(), bus] for address, data, bus in candidate_can] == expected["can"]
