import cereal.messaging as messaging

from cereal import car
from openpilot.selfdrive.car.card import _build_starpilot_car_control


def test_steering_diagnostics_use_reserved_custom_message():
  values = {
    "valid": True,
    "modelLimitErrorDeg": 1.25,
    "resumeLimitErrorDeg": 0.5,
    "cooperativeLimitErrorDeg": 2.0,
    "cooperativeOffsetDeg": -4.5,
    "monoTime": 1_234_567_890,
    "combinedLimitErrorDeg": 3.75,
  }

  message = _build_starpilot_car_control(values, True)
  restored = messaging.log_from_bytes(message.to_bytes())
  info = restored.starpilotCarControl.steeringLimitInfo

  assert restored.valid
  for field, value in values.items():
    assert getattr(info, field) == value


def test_stock_car_output_has_no_fork_specific_fields():
  actuators = car.CarOutput.new_message().actuatorsOutput

  assert "steeringLimitInfo" not in actuators.to_dict()
