# Copyright (c) 2026, firestar5683 and StarPilot contributors
# SPDX-License-Identifier: MIT
"""Actual controller trace capture and replay inputs.

Controls attaches recorder before LaC.update and calls finish after. Learning
process exact selected-policy replay converts this trace into ControlEvidence.
"""

from dataclasses import dataclass
import math

REVISION = 'torque-selected-stage-snapshot-v1'


@dataclass(frozen=True)
class StageSnapshot:
  speed: float
  setpoint: float
  jerk: float
  baseline_ff: float
  learned_ff: float
  threshold: float
  learned_threshold: float
  applied_coordinates: tuple[float, ...]


class TorqueObservation:
  def __init__(self):
    self.stage = None

  def begin_frame(self):
    self.stage = None

  def observe_stage(self, frame, learned_ff, applied_coordinates, learned_threshold=None):
    self.stage = StageSnapshot(
      frame.speed,
      frame.setpoint,
      frame.jerk,
      frame.baseline_ff,
      float(learned_ff),
      frame.baseline_threshold,
      frame.baseline_threshold if learned_threshold is None else float(learned_threshold),
      tuple(applied_coordinates),
    )

  def finish_frame(self, controller, log, *, selected_command, prior_policy_output=0.0, prior_policy_ff=0.0):
    if self.stage is None:
      return None
    s = self.stage
    tune = controller.torque_params
    # Actual PID.f includes downstream FF transformations. Pre-stage residual
    # remains explicit; replay must route it through those same transformations.
    values = (
      ('speed', s.speed),
      ('setpoint', s.setpoint),
      ('jerk', s.jerk),
      ('baseline_ff', s.baseline_ff),
      ('learned_ff', s.learned_ff),
      ('threshold', s.threshold),
      ('learned_threshold', s.learned_threshold),
      ('pid_p', float(log.p)),
      ('pid_i', float(log.i)),
      ('pid_d', float(log.d)),
      ('pid_f', float(log.f)),
      ('pid_pos_limit', float(controller.pid.pos_limit)),
      ('pid_neg_limit', float(controller.pid.neg_limit)),
      ('effective_factor', float(tune.latAccelFactor)),
      ('offset', float(tune.latAccelOffset)),
      ('friction', float(tune.friction)),
      ('selected_command', float(selected_command)),
      ('prior_policy_output', float(prior_policy_output)),
      ('prior_policy_ff', float(prior_policy_ff)),
    )
    if not all(math.isfinite(v) for _, v in values):
      return None
    return REVISION, values, s.applied_coordinates
