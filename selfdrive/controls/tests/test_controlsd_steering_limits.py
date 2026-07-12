import ast
from pathlib import Path
from types import SimpleNamespace

from cereal import car

STEER_ANGLE_SATURATION_THRESHOLD = 2.5


def load_steering_limit_helper():
  # controlsd imports target-built messaging and transformation extensions.
  # Load the pure helper directly from its source so this regression remains
  # runnable on development hosts without importing those unrelated modules.
  source_path = Path(__file__).parents[1] / "controlsd.py"
  tree = ast.parse(source_path.read_text())
  helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and
                node.name == "get_steer_limited_by_safety")
  namespace = {"car": car, "STEER_ANGLE_SATURATION_THRESHOLD": STEER_ANGLE_SATURATION_THRESHOLD}
  exec(compile(ast.Module(body=[helper], type_ignores=[]), source_path, "exec"), namespace)
  return namespace[helper.name]


get_steer_limited_by_safety = load_steering_limit_helper()


def actuators(*, angle=0.0, torque=0.0):
  return SimpleNamespace(steeringAngleDeg=angle, torque=torque)


def test_angle_limit_refreshes_during_aol_while_selfdrive_inactive():
  # selfdriveState.active is intentionally absent: AOL authority is expressed
  # by latActive and must still refresh the limit state.
  requested = actuators(angle=12.0)
  output = actuators(angle=8.0)

  assert get_steer_limited_by_safety(car.CarParams.SteerControlType.angle, True, requested, output)


def test_lateral_inactive_clears_stale_limit_state():
  requested = actuators(angle=12.0)
  output = actuators(angle=8.0)

  assert get_steer_limited_by_safety(car.CarParams.SteerControlType.angle, True, requested, output)
  assert not get_steer_limited_by_safety(car.CarParams.SteerControlType.angle, False, requested, output)


def test_normal_active_angle_and_torque_limits():
  assert not get_steer_limited_by_safety(
    car.CarParams.SteerControlType.angle, True, actuators(angle=10.0), actuators(angle=8.0),
  )
  assert get_steer_limited_by_safety(
    car.CarParams.SteerControlType.torque, True, actuators(torque=0.5), actuators(torque=0.4),
  )
