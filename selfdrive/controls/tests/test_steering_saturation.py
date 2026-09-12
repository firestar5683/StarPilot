import math

import pytest

from cereal import car
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.values import CAR, TeslaSafetyFlags
from openpilot.selfdrive.controls.lib.steering_saturation import is_angle_steering_limited


REQUESTED_ANGLE = -14.5
OUTPUT_ANGLE = -9.0
SAMPLE_TIME_NANOS = 1_000_000_000
FRESH_TIME_NANOS = SAMPLE_TIME_NANOS + 20_000_000
MAX_DIAGNOSTIC_AGE_NANOS = 100_000_000
NEXT_FLOAT32_AFTER_2_5 = 2.500000238418579
ERROR_FIELDS = (
  "modelLimitErrorDeg",
  "resumeLimitErrorDeg",
  "cooperativeLimitErrorDeg",
  "combinedLimitErrorDeg",
)
NUMERIC_FIELDS = ERROR_FIELDS + ("cooperativeOffsetDeg",)


def make_case(candidate=CAR.TESLA_MODEL_3, cooperative_enabled=True):
  cp = CarInterface.get_non_essential_params(candidate)
  for safety_config in cp.safetyConfigs:
    if cooperative_enabled:
      safety_config.safetyParam |= TeslaSafetyFlags.COOP_STEERING.value
    else:
      safety_config.safetyParam &= ~TeslaSafetyFlags.COOP_STEERING.value

  output = car.CarOutput.new_message()
  output.actuatorsOutput.steeringAngleDeg = OUTPUT_ANGLE
  info = output.actuatorsOutput.steeringLimitInfo
  info.valid = True
  info.monoTime = SAMPLE_TIME_NANOS
  info.cooperativeOffsetDeg = 5.5
  return cp, output


def detect(cp, output, requested_angle=REQUESTED_ANGLE, output_healthy=True, now_nanos=FRESH_TIME_NANOS):
  return is_angle_steering_limited(cp.as_reader(), requested_angle, output.as_reader(), output_healthy, now_nanos)


def test_light_offset_does_not_count_as_limiting():
  cp, output = make_case()

  assert not detect(cp, output)


@pytest.mark.parametrize("field", ERROR_FIELDS)
def test_each_genuine_limit_is_visible_during_cooperation(field):
  cp, output = make_case()
  setattr(output.actuatorsOutput.steeringLimitInfo, field, 3.0)

  assert detect(cp, output)


def test_combined_small_limits_remain_visible():
  cp, output = make_case()
  info = output.actuatorsOutput.steeringLimitInfo
  info.modelLimitErrorDeg = 1.5
  info.cooperativeLimitErrorDeg = 1.5
  info.combinedLimitErrorDeg = 3.0

  assert detect(cp, output)


@pytest.mark.parametrize(("error", "expected"), (
  (2.5, False),
  (NEXT_FLOAT32_AFTER_2_5, True),
))
def test_diagnostic_threshold_is_strictly_greater(error, expected):
  cp, output = make_case()
  output.actuatorsOutput.steeringLimitInfo.modelLimitErrorDeg = error

  assert detect(cp, output) is expected


@pytest.mark.parametrize("age_nanos", (0, MAX_DIAGNOSTIC_AGE_NANOS))
def test_diagnostic_age_bounds_are_inclusive(age_nanos):
  cp, output = make_case()

  assert not detect(cp, output, now_nanos=SAMPLE_TIME_NANOS + age_nanos)


def test_signed_cooperative_offset_is_valid_data():
  cp, output = make_case()
  output.actuatorsOutput.steeringLimitInfo.cooperativeOffsetDeg = -5.5

  assert not detect(cp, output)


@pytest.mark.parametrize("scenario", (
  "default_message",
  "invalid_flag",
  "zero_timestamp",
  "future_timestamp",
  "stale_timestamp",
  "unhealthy_output",
  "unsupported_model",
  "cooperative_mode_disabled",
))
def test_unusable_diagnostics_keep_legacy_warning(scenario):
  cp, output = make_case()
  output_healthy = True
  now_nanos = FRESH_TIME_NANOS

  if scenario == "default_message":
    output = car.CarOutput.new_message()
    output.actuatorsOutput.steeringAngleDeg = OUTPUT_ANGLE
  elif scenario == "invalid_flag":
    output.actuatorsOutput.steeringLimitInfo.valid = False
  elif scenario == "zero_timestamp":
    output.actuatorsOutput.steeringLimitInfo.monoTime = 0
  elif scenario == "future_timestamp":
    output.actuatorsOutput.steeringLimitInfo.monoTime = now_nanos + 1
  elif scenario == "stale_timestamp":
    output.actuatorsOutput.steeringLimitInfo.monoTime = now_nanos - MAX_DIAGNOSTIC_AGE_NANOS - 1
  elif scenario == "unhealthy_output":
    output_healthy = False
  elif scenario == "unsupported_model":
    cp, output = make_case(CAR.TESLA_MODEL_Y)
  elif scenario == "cooperative_mode_disabled":
    cp, output = make_case(cooperative_enabled=False)

  assert detect(cp, output, output_healthy=output_healthy, now_nanos=now_nanos)


@pytest.mark.parametrize(("requested_angle", "expected"), (
  (OUTPUT_ANGLE - 2.5, False),
  (OUTPUT_ANGLE - NEXT_FLOAT32_AFTER_2_5, True),
))
def test_fallback_preserves_legacy_strict_threshold(requested_angle, expected):
  cp, output = make_case()
  output.actuatorsOutput.steeringLimitInfo.valid = False

  assert detect(cp, output, requested_angle=requested_angle) is expected


@pytest.mark.parametrize("field", NUMERIC_FIELDS)
@pytest.mark.parametrize(("bad_value", "requested_angle", "legacy_result"), (
  (math.nan, REQUESTED_ANGLE, True),
  (math.inf, OUTPUT_ANGLE, False),
  (-math.inf, OUTPUT_ANGLE, False),
))
def test_nonfinite_diagnostic_values_use_legacy_fallback(field, bad_value, requested_angle, legacy_result):
  cp, output = make_case()
  setattr(output.actuatorsOutput.steeringLimitInfo, field, bad_value)

  assert detect(cp, output, requested_angle=requested_angle) is legacy_result


@pytest.mark.parametrize("field", ERROR_FIELDS)
def test_negative_error_values_use_legacy_fallback(field):
  cp, output = make_case()
  setattr(output.actuatorsOutput.steeringLimitInfo, field, -0.1)

  assert detect(cp, output)
