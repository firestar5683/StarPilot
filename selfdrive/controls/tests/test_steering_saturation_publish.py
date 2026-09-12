from types import SimpleNamespace

import pytest

from cereal import car, custom, log
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.values import CAR, TeslaSafetyFlags
from openpilot.selfdrive.controls import controlsd
from openpilot.selfdrive.controls.controlsd import Controls


REQUESTED_ANGLE = -14.5
OUTPUT_ANGLE = -9.0
SAMPLE_TIME_NANOS = 1_000_000_000
FRESH_TIME_NANOS = SAMPLE_TIME_NANOS + 20_000_000
STALE_TIME_NANOS = SAMPLE_TIME_NANOS + 100_000_001
HOST_TIME_NANOS = 9_000_000_000
CAR_STATE_TIME_NANOS = 7_000_000_000


class CapturePubMaster:
  def __init__(self):
    self.sent = {}

  def send(self, service, message):
    self.sent[service] = message


class PublishSubMaster:
  def __init__(self, car_output, selfdrive_time_nanos, output_healthy=True):
    car_state = car.CarState.new_message()
    car_state.canValid = True

    long_plan = log.LongitudinalPlan.new_message()
    long_plan.speeds = []

    selfdrive_state = log.SelfdriveState.new_message()
    selfdrive_state.active = True

    self.messages = {
      "carState": car_state.as_reader(),
      "longitudinalPlan": long_plan.as_reader(),
      "starpilotCarState": custom.StarPilotCarState.new_message().as_reader(),
      "selfdriveState": selfdrive_state.as_reader(),
      "carOutput": car_output.as_reader(),
      "driverAssistance": log.DriverAssistance.new_message().as_reader(),
      "driverMonitoringState": log.DriverMonitoringState.new_message().as_reader(),
    }
    self.valid = {"carOutput": output_healthy, "driverAssistance": False}
    self.alive = {"carOutput": output_healthy}
    self.freq_ok = {"carOutput": output_healthy}
    self.logMonoTime = {
      "selfdriveState": selfdrive_time_nanos,
      "carState": CAR_STATE_TIME_NANOS,
      "longitudinalPlan": 0,
      "modelV2": 0,
    }

  def __getitem__(self, service):
    return self.messages[service]


def make_car_params():
  cp = CarInterface.get_non_essential_params(CAR.TESLA_MODEL_3)
  cp.safetyConfigs[0].safetyParam |= TeslaSafetyFlags.COOP_STEERING.value
  return cp.as_reader()


def make_car_output(real_limit_error=0.0):
  output = car.CarOutput.new_message()
  output.actuatorsOutput.steeringAngleDeg = OUTPUT_ANGLE
  info = output.actuatorsOutput.steeringLimitInfo
  info.valid = True
  info.monoTime = SAMPLE_TIME_NANOS
  info.cooperativeOffsetDeg = 5.5
  info.modelLimitErrorDeg = real_limit_error
  info.combinedLimitErrorDeg = real_limit_error
  return output


def make_controls(car_output, selfdrive_time_nanos, output_healthy=True):
  controls = Controls.__new__(Controls)
  controls.CP = make_car_params()
  controls.sm = PublishSubMaster(car_output, selfdrive_time_nanos, output_healthy)
  controls.pm = CapturePubMaster()
  controls.curvature = 0.0
  controls.calibrated_pose = None
  controls.desired_curvature = 0.0
  controls.LoC = SimpleNamespace(
    long_control_state=car.CarControl.Actuators.LongControlState.off,
    pid=SimpleNamespace(p=0.0, i=0.0, f=0.0),
  )
  controls.LaC = SimpleNamespace()
  controls.starpilot_toggles = SimpleNamespace()
  controls.steer_limited_by_safety = False
  return controls


def run_publish(monkeypatch, replay, selfdrive_time_nanos, host_time_nanos=HOST_TIME_NANOS,
                output_healthy=True, real_limit_error=0.0):
  monkeypatch.setattr(controlsd, "REPLAY", replay, raising=False)
  monkeypatch.setattr(controlsd.time, "monotonic_ns", lambda: host_time_nanos)
  controls = make_controls(make_car_output(real_limit_error), selfdrive_time_nanos, output_healthy)
  cc = car.CarControl.new_message()
  cc.enabled = True
  cc.latActive = True
  cc.actuators.steeringAngleDeg = REQUESTED_ANGLE
  lac_log = log.ControlsState.LateralAngleState.new_message()

  controls.publish(cc, lac_log)
  return controls


def test_replay_uses_current_poll_timestamp_for_fresh_diagnostics(monkeypatch):
  controls = run_publish(monkeypatch, True, FRESH_TIME_NANOS)

  assert not controls.steer_limited_by_safety


def test_replay_stale_diagnostics_still_use_legacy_fallback(monkeypatch):
  controls = run_publish(monkeypatch, True, STALE_TIME_NANOS)

  assert controls.steer_limited_by_safety


@pytest.mark.parametrize(("selfdrive_time_nanos", "expected_limited"), (
  (SAMPLE_TIME_NANOS + 100_000_000, False),
  (SAMPLE_TIME_NANOS + 100_000_001, True),
  (SAMPLE_TIME_NANOS - 1, True),
  (0, True),
))
def test_replay_publish_preserves_diagnostic_age_boundaries(monkeypatch, selfdrive_time_nanos, expected_limited):
  controls = run_publish(monkeypatch, True, selfdrive_time_nanos)

  assert controls.steer_limited_by_safety is expected_limited


def test_live_uses_monotonic_clock_instead_of_message_clock(monkeypatch):
  controls = run_publish(monkeypatch, False, FRESH_TIME_NANOS, host_time_nanos=STALE_TIME_NANOS)

  assert controls.steer_limited_by_safety


def test_unhealthy_car_output_still_uses_legacy_fallback(monkeypatch):
  controls = run_publish(monkeypatch, True, FRESH_TIME_NANOS, output_healthy=False)

  assert controls.steer_limited_by_safety


def test_replay_genuine_limiter_error_remains_visible(monkeypatch):
  controls = run_publish(monkeypatch, True, FRESH_TIME_NANOS, real_limit_error=3.0)

  assert controls.steer_limited_by_safety
