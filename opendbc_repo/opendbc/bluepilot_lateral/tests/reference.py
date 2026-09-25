"""Hash-bound upstream angle execution and current-curvature controller oracle.

Only imports are removed from the upstream angle/human module AST; every other
statement and function remains exact. Glue supplies current ABI types, source
fixed defaults and the source's no-op lazy-init/yaw-default adapter. No BluePilot
curvature strategy is loaded. Its diagnostic limiter cannot affect angle output.
"""
import ast
from collections import namedtuple
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from opendbc.car import structs, DT_CTRL
from opendbc.car.ford.values import CAR, CarControllerParams
from opendbc.car.ford.fordcan import CanBus
from opendbc.car.lateral import AngleSteeringLimits, apply_std_steer_angle_limits
from openpilot.selfdrive.modeld.constants import ModelConstants

ROOT = Path(__file__).with_name("reference")
MANIFEST = json.loads((ROOT / "manifest.json").read_text())


def source(name):
  raw = (ROOT / (name + ".py.txt")).read_bytes()
  if hashlib.sha256(raw).hexdigest() != MANIFEST[name]["sha256"]:
    raise AssertionError("Reference source differs from its pinned manifest: " + name)
  return ast.parse(raw.decode(), filename=MANIFEST[name]["origin"])


def execute(tree, namespace, *, names=None):
  body = []
  for node in tree.body:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
      continue
    if names is not None:
      assigned = [target.id for target in node.targets if isinstance(target, ast.Name)] if isinstance(node, ast.Assign) else []
      if getattr(node, "name", None) not in names and not any(name in names for name in assigned):
        continue
    body.append(node)
  exec(compile(ast.Module(body=body, type_ignores=[]), "<pinned source>", "exec"), namespace)


def angle():
  LateralResult = namedtuple("LateralResult", "apply_curvature curvature_rate path_offset path_angle ramp_type precision_type lateralUncertainty")
  namespace = {"np": np, "clip": np.clip, "interp": np.interp, "DT_CTRL": DT_CTRL,
               "CAR": CAR, "CarControllerParams": CarControllerParams, "ModelConstants": ModelConstants,
               "LateralResult": LateralResult, "AngleSteeringLimits": AngleSteeringLimits,
               "apply_std_steer_angle_limits": apply_std_steer_angle_limits}
  execute(source("human"), namespace)
  execute(source("values"), namespace, names={"_BP_ANGLE_RATE_UP", "_BP_ANGLE_RATE_DOWN", "BP_ANGLE_LIMITS"})
  execute(source("angle"), namespace)
  return namespace["LateralAngleExt"]


def builders():
  namespace = {"CanBus": CanBus, "structs": structs}
  execute(source("fordcan"), namespace, names={"calculate_lat_ctl2_checksum"})
  execute(source("builders"), namespace, names={"create_lka_msg", "create_lat_ctl_msg", "create_lat_ctl2_msg", "_BP_LKA_SHADOW_CURVATURE_SCALE"})
  return namespace


def curvature_controller():
  # Full exact pre-angle production controller, with unchanged current imports.
  namespace = {"__name__": "ford_curvature_pre_angle_reference"}
  exec(compile(source("starpilot_curvature_controller"), "<current pre-angle controller>", "exec"), namespace)
  return namespace["CarController"]


class Angle:
  def __init__(self, identity):
    self.controller = angle()()
    self.controller.CP = SimpleNamespace(carFingerprint=identity)
    self.controller._ensure_lateral_curv_initialized = lambda _cp: None  # Exact source guard is a no-op.
    self.controller.get_current_curvature = lambda cs: -cs.out.yawRate / max(cs.out.vEgoRaw, .1)
    self.controller.path_angle_last = 0.
    self.controller.lp = None  # Read but unused by the source angle strategy.
    self.controller.lane_change_factor_bp = [0., 50.]
    self.controller.lane_change_factor_low = 1.
    self.controller.model = None
    self.controller.update_angle_params(None)

  def step(self, inputs):
    c = self.controller
    c.sm = {"liveDelay": SimpleNamespace(lateralDelay=inputs.lateral_delay)}
    c.model = SimpleNamespace(orientationRate=SimpleNamespace(z=list(inputs.yaw_predictions)),
                             meta=SimpleNamespace(laneChangeState=1 if inputs.lane_change else 0,
                                                  laneChangeDirection=inputs.lane_direction)) if inputs.yaw_predictions else None
    cc = SimpleNamespace(latActive=inputs.active)
    cs = SimpleNamespace(out=SimpleNamespace(vEgoRaw=inputs.speed, yawRate=-inputs.measured_curvature * inputs.speed,
                                            steeringPressed=inputs.steering_pressed, steeringAngleDeg=inputs.steering_angle),
                         lat_ctl_lim_stat=inputs.limit_status)
    return c.update_angle_strategy(cc, cs, SimpleNamespace(curvature=inputs.desired_curvature), c.CP)


def trim():
  namespace = {"np": np, "interp": np.interp}
  execute(source("bpdev_trim"), namespace)
  return namespace["LaneCenterTrim"]
