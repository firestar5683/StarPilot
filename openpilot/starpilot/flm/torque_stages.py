# Copyright (c) 2026, firestar5683 and StarPilot contributors
# SPDX-License-Identifier: MIT
"""Bounded torque stage hooks; the common owner admits profiles.

Existing selected tune/shaping/conversion/output caps remain authoritative.
No Params, PID, factor, table, inverse or final actuator writes.
"""

from dataclasses import dataclass
import math

REVISION = 'torque-post-baseline-prefriction-v1'


@dataclass(frozen=True)
class StageFrame:
  speed: float
  setpoint: float
  jerk: float
  baseline_ff: float
  baseline_threshold: float
  active: bool
  driver_override: bool
  limited: bool

  def valid(self):
    return (
      all(math.isfinite(v) for v in (self.speed, self.setpoint, self.jerk, self.baseline_ff, self.baseline_threshold))
      and 0 <= self.speed <= 90
      and self.baseline_threshold > 0
    )


def apply_stages(parent, cs, setpoint, jerk, ff, threshold, *, active, limited):
  """One selected-policy call after baseline FF/threshold, before friction.

  Missing source and inactive/manual/off source emit exact unchanged baseline.
  Source methods are owned by core and may only return admitted residuals.
  """
  source = getattr(parent, 'automatic_flm_stages', None)
  frame = StageFrame(float(cs.vEgo), float(setpoint), float(jerk), float(ff), float(threshold), bool(active), bool(cs.steeringPressed), bool(limited))
  observer = getattr(parent, 'automatic_flm_observation', None)
  if observer is not None and frame.valid():
    observer.observe_stage(frame, ff, (0.0, 0.0))
  if source is None:
    return ff, threshold
  if not frame.valid() or not frame.active or frame.driver_override or frame.limited:
    return ff, threshold
  try:
    # Core owns monotonic tick, identity/manual/TTL/policy validation and slew.
    # delta is relative to this selected controller's fully shaped baseline.
    delta_ff, delta_threshold = source.torque_residual(frame, stage_revision=REVISION)
    if not all(type(v) in (float, int) and math.isfinite(v) for v in (delta_ff, delta_threshold)) or abs(delta_ff) > 0.03 or abs(delta_threshold) > 0.03:
      return ff, threshold
    candidate_ff = ff if delta_ff == 0 else ff * (1 + delta_ff)
    candidate_threshold = threshold if delta_threshold == 0 else threshold * (1 + delta_threshold)
    if not math.isfinite(candidate_ff) or not math.isfinite(candidate_threshold) or candidate_threshold <= 0:
      return ff, threshold
    if observer is not None:
      observer.observe_stage(frame, candidate_ff, tuple(source.applied_coordinates), candidate_threshold)
    return candidate_ff, candidate_threshold
  except (AttributeError, TypeError, ValueError, OverflowError):
    return ff, threshold


def extra_deadband(parent, cs, *, active, limited):
  """Separate proven center coordinate; absent evidence is exactly zero.

  Core must not derive this from scalar response slope or ordinary FF evidence.
  Existing steering angle deadzone and any manual FLM contribution stay intact.
  """
  source = getattr(parent, 'automatic_flm_stages', None)
  if source is None or not active or limited or cs.steeringPressed:
    return 0.0
  try:
    delta = source.torque_deadband(float(cs.vEgo), stage_revision=REVISION)
    return float(delta) if type(delta) in (float, int) and math.isfinite(delta) and 0 <= delta <= 0.01 else 0.0
  except (AttributeError, TypeError, ValueError, OverflowError):
    return 0.0
