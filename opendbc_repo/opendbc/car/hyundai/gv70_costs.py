"""Electrified GV70's absolute planner cost projection.

Input context belongs to the current-drive planner owner. This module does not
change the solver recipe, actuator limits, or other vehicles' default costs.
"""
from dataclasses import dataclass
import math

from opendbc.car.hyundai.values import CAR


@dataclass(frozen=True)
class CostContext:
  speed_mps: float
  lead_distance_m: float
  uncertainty: float
  mode: str
  acceleration_factor: float
  speed_factor: float
  danger_factor: float
  stop_approach: bool
  tracked_lead: bool
  previous_accel_constraint: bool


@dataclass(frozen=True)
class CostWeights:
  stage: tuple[float, ...]
  constraints: tuple[float, ...]


def eligible(cp):
  return (cp.carFingerprint == CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN and
          cp.openpilotLongitudinalControl and not cp.passive and
          not cp.dashcamOnly and not cp.notCar)


def _interpolate(speed_mph, values):
  points = (0., 35., 55., 70.)
  if speed_mph <= points[0]:
    return values[0]
  for i in range(1, len(points)):
    if speed_mph <= points[i]:
      fraction = (speed_mph - points[i - 1]) / (points[i] - points[i - 1])
      return values[i - 1] + fraction * (values[i] - values[i - 1])
  return values[-1]


def project(context):
  numeric = (context.speed_mps, context.lead_distance_m, context.uncertainty,
             context.acceleration_factor, context.speed_factor, context.danger_factor)
  if not all(type(v) in (int, float) and math.isfinite(v) for v in numeric):
    raise ValueError('invalid GV70 cost context')
  if context.speed_mps < 0 or min(context.acceleration_factor, context.speed_factor, context.danger_factor) <= 0:
    raise ValueError('invalid GV70 cost context')
  mph = context.speed_mps * 3.6 / 1.609344
  distance_factor = 1. + _interpolate(mph, (0., .06, .06, .05)) * (20. / max(context.lead_distance_m, 5.))
  # Original publisher gives stop/approach priority over tracked following.
  scale = .20 if context.stop_approach else 1.75 if context.tracked_lead else 1.
  acceleration = 250. * context.acceleration_factor * scale * distance_factor
  speed = 5.5 * context.speed_factor * distance_factor
  danger = 100. * context.danger_factor * distance_factor
  if .45 <= context.uncertainty < .60:
    speed *= 1.2 + (context.uncertainty - .45) / .15 * .3
  if context.mode == 'acc':
    stage = (_interpolate(mph, (3., 3., 2.5, 2.)), 0., 0., 0.,
             acceleration if context.previous_accel_constraint else 0., speed)
  elif context.mode == 'blended':
    stage = (0., .1, .2, 5., 40. if context.previous_accel_constraint else 0., 1.)
  else:
    raise ValueError('unsupported GV70 planner mode')
  return CostWeights(stage, (1e6, 1e6, 1e6, danger))
