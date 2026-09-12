from types import SimpleNamespace

import cereal.messaging as messaging
import pytest

from cereal import car, custom, log
from opendbc.car import DT_CTRL, gen_empty_fingerprint
from opendbc.car.tesla.carcontroller import CarController
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.values import CAR, DBC
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib.latcontrol_angle import LatControlAngle
from openpilot.selfdrive.controls.lib.steering_saturation import is_angle_steering_limited
from openpilot.selfdrive.selfdrived.events import ET
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD


REPRO_REQUESTED_ANGLE = -14.505379676818848
REPRO_MEASURED_ANGLE = -10.0
REPRO_SPEED = 12.509657859802246
REPRO_TORQUE = 0.8999999761581421
REPRO_DESIRED_CURVATURE = 0.006728461943566799
REPRO_ACTUAL_CURVATURE = 0.004746654070913792
START_NANOS = 1_000_000_000


def make_params():
  toggles = SimpleNamespace(tesla_cooperative_steering=True, trailer_load_kg=0.0)
  return CarInterface.get_params(CAR.TESLA_MODEL_3, gen_empty_fingerprint(), [], False, False, False, toggles)


def make_controller_state(torque, speed, measured_angle, steering_disengage=False):
  return SimpleNamespace(
    out=SimpleNamespace(
      steeringTorque=torque,
      steeringAngleDeg=measured_angle,
      steeringDisengage=steering_disengage,
      vEgo=speed,
      vEgoRaw=speed,
      gasPressed=False,
    ),
    hands_on_level=0,
    das_control={"DAS_controlCounter": 0},
  )


def make_car_control(requested_angle, lat_active=True):
  control = car.CarControl.new_message()
  control.enabled = lat_active
  control.latActive = lat_active
  control.actuators.steeringAngleDeg = requested_angle
  return control


def run_controller_frame(controller, requested_angle, torque, speed, measured_angle, frame,
                         lat_active=True, steering_disengage=False):
  now_nanos = START_NANOS + frame * 10_000_000
  actuators, _ = controller.update(
    make_car_control(requested_angle, lat_active).as_reader(),
    make_controller_state(torque, speed, measured_angle, steering_disengage),
    now_nanos,
    SimpleNamespace(),
  )
  event = messaging.new_message("carOutput", valid=True)
  event.carOutput.actuatorsOutput = actuators
  restored = messaging.log_from_bytes(event.to_bytes())
  return restored.carOutput, now_nanos


def make_lateral_car_state(speed, measured_angle):
  state = car.CarState.new_message()
  state.canValid = True
  state.vEgo = speed
  state.vEgoRaw = speed
  state.steeringAngleDeg = measured_angle
  state.gearShifter = car.CarState.GearShifter.drive
  state.cruiseState.available = True
  state.cruiseState.enabled = True
  return state


def advance_angle_counter(controller, CP, state, limited, desired_curvature):
  live_params = log.LiveParametersData.new_message()
  live_params.steerRatio = CP.steerRatio
  live_params.stiffnessFactor = 1.0
  live_params.roll = 0.0
  live_params.angleOffsetDeg = 0.0
  _, _, angle_log = controller.update(
    True, state.as_reader(), VehicleModel(CP), live_params.as_reader(), limited,
    desired_curvature, False, 0.2, None, None, SimpleNamespace(),
  )
  return angle_log


def controls_state_with_angle_log(angle_log, actual_curvature):
  controls_state = log.ControlsState.new_message()
  controls_state.curvature = actual_curvature
  controls_state.lateralControlState.angleState = angle_log
  return controls_state


def configure_selfdrived(CP):
  fpcp = custom.StarPilotCarParams.new_message()
  Params().put("StarPilotCarParams", fpcp.to_bytes())
  selfdrived = SelfdriveD(CP.as_reader())
  selfdrived.initialized = True
  selfdrived.enabled = True
  selfdrived.active = True
  selfdrived.startup_event = None
  selfdrived.last_steering_pressed_frame = 0
  selfdrived.sm.frame = 300

  for service in selfdrived.sm.data:
    selfdrived.sm.valid[service] = True
    selfdrived.sm.alive[service] = True
    selfdrived.sm.freq_ok[service] = True
    selfdrived.sm.seen[service] = True
    selfdrived.sm.updated[service] = False
    selfdrived.sm.recv_frame[service] = selfdrived.sm.frame

  device_state = log.DeviceState.new_message()
  device_state.started = True
  device_state.freeSpacePercent = 100.0
  device_state.memoryUsagePercent = 0
  selfdrived.sm.data["deviceState"] = device_state.as_reader()

  live_calibration = log.LiveCalibrationData.new_message()
  live_calibration.calStatus = log.LiveCalibrationData.Status.calibrated
  selfdrived.sm.data["liveCalibration"] = live_calibration.as_reader()

  live_parameters = log.LiveParametersData.new_message()
  live_parameters.valid = True
  selfdrived.sm.data["liveParameters"] = live_parameters.as_reader()

  panda_states = messaging.new_message("pandaStates", 0)
  selfdrived.sm.data["pandaStates"] = panda_states.pandaStates
  return selfdrived


def run_selfdrived_warning_path(selfdrived, state, angle_log, actual_curvature, desired_curvature,
                                requested_angle=REPRO_REQUESTED_ANGLE):
  controls_state = controls_state_with_angle_log(angle_log, actual_curvature)
  model = log.ModelDataV2.new_message()
  model.action.desiredCurvature = desired_curvature
  selfdrived.sm.data["controlsState"] = controls_state.as_reader()
  selfdrived.sm.data["modelV2"] = model.as_reader()
  selfdrived.sm.data["carControl"] = make_car_control(requested_angle).as_reader()
  selfdrived.CS_prev = state.as_reader()
  selfdrived.update_events(state.as_reader())
  alerts = selfdrived.events.create_alerts([ET.WARNING])
  return selfdrived.events.names, [alert.alert_type for alert in alerts]


def test_recorded_light_torque_reproduction_no_longer_reaches_warning():
  CP = make_params()
  tesla_controller = CarController(DBC[CAR.TESLA_MODEL_3], CP)
  lateral_state = make_lateral_car_state(REPRO_SPEED, REPRO_MEASURED_ANGLE)
  baseline_counter = LatControlAngle(CP.as_reader(), None, DT_CTRL)
  corrected_counter = LatControlAngle(CP.as_reader(), None, DT_CTRL)

  baseline_log = corrected_log = None
  output = None
  now_nanos = 0
  for frame in range(260):
    output, now_nanos = run_controller_frame(
      tesla_controller, REPRO_REQUESTED_ANGLE, REPRO_TORQUE, REPRO_SPEED, REPRO_MEASURED_ANGLE, frame,
    )
    if frame >= 210:
      legacy_limited = abs(REPRO_REQUESTED_ANGLE - output.actuatorsOutput.steeringAngleDeg) > 2.5
      corrected_limited = is_angle_steering_limited(
        CP.as_reader(), REPRO_REQUESTED_ANGLE, output, True, now_nanos,
      )
      baseline_log = advance_angle_counter(
        baseline_counter, CP, lateral_state, legacy_limited, REPRO_DESIRED_CURVATURE,
      )
      corrected_log = advance_angle_counter(
        corrected_counter, CP, lateral_state, corrected_limited, REPRO_DESIRED_CURVATURE,
      )

  info = output.actuatorsOutput.steeringLimitInfo
  errors = (info.modelLimitErrorDeg, info.resumeLimitErrorDeg,
            info.cooperativeLimitErrorDeg, info.combinedLimitErrorDeg)
  assert info.valid
  assert info.cooperativeOffsetDeg > 2.5
  assert max(errors) <= 2.5
  assert baseline_log.saturated
  assert not corrected_log.saturated

  selfdrived = configure_selfdrived(CP)
  baseline_events, baseline_alert_types = run_selfdrived_warning_path(
    selfdrived, lateral_state, baseline_log, REPRO_ACTUAL_CURVATURE, REPRO_DESIRED_CURVATURE,
  )
  assert log.OnroadEvent.EventName.steerSaturated in baseline_events
  assert "steerSaturated/warning" in baseline_alert_types

  selfdrived.sm.frame += 1
  events, alert_types = run_selfdrived_warning_path(
    selfdrived, lateral_state, corrected_log, REPRO_ACTUAL_CURVATURE, REPRO_DESIRED_CURVATURE,
  )
  assert log.OnroadEvent.EventName.steerSaturated not in events
  assert "steerSaturated/warning" not in alert_types


def test_persistent_real_model_limiting_with_light_torque_still_warns():
  CP = make_params()
  tesla_controller = CarController(DBC[CAR.TESLA_MODEL_3], CP)
  speed = 22.0
  requested_angle = 40.0
  lateral_state = make_lateral_car_state(speed, 0.0)
  angle_counter = LatControlAngle(CP.as_reader(), None, DT_CTRL)

  angle_log = None
  output = None
  for frame in range(60):
    output, now_nanos = run_controller_frame(
      tesla_controller, requested_angle, REPRO_TORQUE, speed, 0.0, frame,
    )
    limited = is_angle_steering_limited(CP.as_reader(), requested_angle, output, True, now_nanos)
    angle_log = advance_angle_counter(angle_counter, CP, lateral_state, limited, 0.01)

  info = output.actuatorsOutput.steeringLimitInfo
  assert info.valid
  assert info.modelLimitErrorDeg > 2.5
  assert info.combinedLimitErrorDeg > 2.5
  assert angle_log.saturated

  selfdrived = configure_selfdrived(CP)
  events, alert_types = run_selfdrived_warning_path(
    selfdrived, lateral_state, angle_log, 0.003, 0.01, requested_angle,
  )
  assert log.OnroadEvent.EventName.steerSaturated in events
  assert "steerSaturated/warning" in alert_types


def test_default_old_output_uses_legacy_warning_path():
  CP = make_params()
  output_event = messaging.new_message("carOutput", valid=True)
  output_event.carOutput.actuatorsOutput.steeringAngleDeg = REPRO_MEASURED_ANGLE
  output = messaging.log_from_bytes(output_event.to_bytes()).carOutput
  lateral_state = make_lateral_car_state(REPRO_SPEED, REPRO_MEASURED_ANGLE)
  angle_counter = LatControlAngle(CP.as_reader(), None, DT_CTRL)

  for frame in range(50):
    limited = is_angle_steering_limited(
      CP.as_reader(), REPRO_REQUESTED_ANGLE, output, True, START_NANOS + frame * 10_000_000,
    )
    angle_log = advance_angle_counter(
      angle_counter, CP, lateral_state, limited, REPRO_DESIRED_CURVATURE,
    )

  assert not output.actuatorsOutput.steeringLimitInfo.valid
  assert angle_log.saturated
  selfdrived = configure_selfdrived(CP)
  events, _ = run_selfdrived_warning_path(
    selfdrived, lateral_state, angle_log, REPRO_ACTUAL_CURVATURE, REPRO_DESIRED_CURVATURE,
  )
  assert log.OnroadEvent.EventName.steerSaturated in events


def test_stale_real_offset_sample_uses_legacy_warning_path():
  CP = make_params()
  tesla_controller = CarController(DBC[CAR.TESLA_MODEL_3], CP)
  lateral_state = make_lateral_car_state(REPRO_SPEED, REPRO_MEASURED_ANGLE)
  angle_counter = LatControlAngle(CP.as_reader(), None, DT_CTRL)

  for frame in range(260):
    output, now_nanos = run_controller_frame(
      tesla_controller, REPRO_REQUESTED_ANGLE, REPRO_TORQUE, REPRO_SPEED, REPRO_MEASURED_ANGLE, frame,
    )

  assert not is_angle_steering_limited(CP.as_reader(), REPRO_REQUESTED_ANGLE, output, True, now_nanos)
  stale_now_nanos = output.actuatorsOutput.steeringLimitInfo.monoTime + 100_000_001
  for _ in range(50):
    limited = is_angle_steering_limited(
      CP.as_reader(), REPRO_REQUESTED_ANGLE, output, True, stale_now_nanos,
    )
    angle_log = advance_angle_counter(
      angle_counter, CP, lateral_state, limited, REPRO_DESIRED_CURVATURE,
    )

  assert angle_log.saturated
  selfdrived = configure_selfdrived(CP)
  events, _ = run_selfdrived_warning_path(
    selfdrived, lateral_state, angle_log, REPRO_ACTUAL_CURVATURE, REPRO_DESIRED_CURVATURE,
  )
  assert log.OnroadEvent.EventName.steerSaturated in events


def test_inactive_interval_clears_diagnostics_before_reengagement():
  CP = make_params()
  tesla_controller = CarController(DBC[CAR.TESLA_MODEL_3], CP)

  active, _ = run_controller_frame(tesla_controller, 0.0, REPRO_TORQUE, REPRO_SPEED, 0.0, 0)
  inactive, _ = run_controller_frame(
    tesla_controller, 0.0, REPRO_TORQUE, REPRO_SPEED, 0.0, 1, lat_active=False,
  )
  resumed, resumed_now = run_controller_frame(
    tesla_controller, 0.0, REPRO_TORQUE, REPRO_SPEED, 0.0, 2,
  )
  overridden, _ = run_controller_frame(
    tesla_controller, 0.0, REPRO_TORQUE, REPRO_SPEED, 0.0, 3, steering_disengage=True,
  )

  assert active.actuatorsOutput.steeringLimitInfo.valid
  assert not inactive.actuatorsOutput.steeringLimitInfo.valid
  assert inactive.actuatorsOutput.steeringLimitInfo.monoTime == 0
  assert resumed.actuatorsOutput.steeringLimitInfo.valid
  assert resumed.actuatorsOutput.steeringLimitInfo.monoTime == resumed_now
  assert not overridden.actuatorsOutput.steeringLimitInfo.valid
  assert overridden.actuatorsOutput.steeringLimitInfo.monoTime == 0


@pytest.mark.parametrize(("fault_field", "expected_event"), (
  ("steerFaultTemporary", log.OnroadEvent.EventName.steerTempUnavailableSilent),
  ("steerFaultPermanent", log.OnroadEvent.EventName.steerUnavailable),
))
def test_existing_steering_fault_events_remain_present(fault_field, expected_event):
  CP = make_params()
  state = make_lateral_car_state(REPRO_SPEED, REPRO_MEASURED_ANGLE)
  setattr(state, fault_field, True)
  angle_counter = LatControlAngle(CP.as_reader(), None, DT_CTRL)
  angle_log = advance_angle_counter(
    angle_counter, CP, state, False, REPRO_DESIRED_CURVATURE,
  )

  selfdrived = configure_selfdrived(CP)
  events, _ = run_selfdrived_warning_path(
    selfdrived, state, angle_log, REPRO_ACTUAL_CURVATURE, REPRO_DESIRED_CURVATURE,
  )
  assert expected_event in events
