# Copyright (c) 2026, firestar5683 and StarPilot contributors
# SPDX-License-Identifier: MIT
"""Selected objective torque bridge; core fits and local replay qualifies each family.

No physical inverse inferred from native controller table; no factor/PID writes.
Two direction cells per speed/phase session fit inside 24 maneuver bound.
"""

from dataclasses import dataclass
import math
from openpilot.starpilot.flm.adaptive_profile import Parameter, ProfileOwner, ReplayValidation
from openpilot.starpilot.flm.torque_stages import REVISION


@dataclass(frozen=True)
class Objective:
  stage: str
  speed_band: str
  phase: str

  def __post_init__(self):
    if (
      self.stage not in ('feedforward', 'friction', 'center')
      or self.speed_band not in ('low', 'high')
      or self.phase not in ('steady', 'turn_in', 'unwind', 'center')
    ):
      raise ValueError('unknown objective')
    if (self.stage == 'center') != (self.phase == 'center'):
      raise ValueError('center requires separate objective')

  @property
  def parameters(self):
    low, high, slew = (0.0, 0.01, 0.002) if self.stage == 'center' else (-0.03, 0.03, 0.005)
    return tuple(Parameter(f'{self.stage}.{self.speed_band}.{side}.{self.phase}', REVISION, low, high, high, slew) for side in ('left', 'right'))

  @property
  def required_cohorts(self):
    return tuple(f'{self.speed_band}.{side}.{self.phase}' for side in ('left', 'right'))


def gates(objective, speed, setpoint, jerk):
  if not all(math.isfinite(v) for v in (speed, setpoint, jerk)) or not 0 <= speed <= 90:
    raise ValueError('bad frame')
  high = min(max((speed - 10.0) / 15.0, 0.0), 1.0)
  speed_gate = high if objective.speed_band == 'high' else 1 - high
  if objective.phase == 'center':
    phase_gate = max(0.0, 1 - abs(setpoint) / 0.25) * max(0.0, 1 - abs(jerk) / 0.5)
  else:
    phase = setpoint * jerk
    if objective.phase == 'steady':
      phase_gate = max(0.0, 1 - abs(phase) / 0.15)
    elif objective.phase == 'turn_in':
      phase_gate = min(max(phase / 0.15, 0.0), 1.0)
    else:
      phase_gate = min(max(-phase / 0.15, 0.0), 1.0)
    phase_gate *= min(abs(setpoint) / 0.25, 1.0)
  return tuple(speed_gate * phase_gate * (1.0 if (setpoint > 0 if side == 'left' else setpoint < 0) else 0.0) for side in ('left', 'right'))


def features(objective, frame, *, center_response_basis=None):
  weights = gates(objective, frame.speed, frame.setpoint, frame.jerk)
  if objective.stage == 'feedforward':
    base = frame.baseline_ff
  elif objective.stage == 'friction':
    # Actual selected friction derivative belongs to separate physical objective;
    # threshold value alone cannot represent command sensitivity.
    raise ValueError('use independently measured friction stage sensitivity')
  elif center_response_basis is not None and math.isfinite(center_response_basis):
    base = center_response_basis
  else:
    raise ValueError('center physical sensitivity missing')
  return tuple(base * w for w in weights)


@dataclass(frozen=True)
class Admission:
  profile: object | None
  now_ns: int
  enabled: bool
  manual: bool
  healthy: bool
  replay_validation: ReplayValidation | None


class TorqueStageOwner:
  def __init__(self, identity, objective, *, baseline_revision, physical_model_revision):
    if not baseline_revision or not physical_model_revision:
      raise ValueError('exact local revisions required')
    self.objective = objective
    self.owner = ProfileOwner(identity, objective.parameters, baseline_revision=baseline_revision, physical_model_revision=physical_model_revision)
    self.baseline_revision, self.physical_model_revision = baseline_revision, physical_model_revision
    self.admission = None
    self.used = False
    self.status = 'collecting'

  @property
  def applied_coordinates(self):
    return self.owner.applied

  def prepare(self, admission):
    if not isinstance(admission, Admission):
      raise ValueError('bad admission')
    self.admission, self.used = admission, False

  def _tick(self, active):
    a = self.admission
    v = a.replay_validation
    exact = isinstance(v, ReplayValidation) and v.baseline_revision == self.baseline_revision and v.physical_model_revision == self.physical_model_revision
    return self.owner.tick(
      a.profile, now_ns=a.now_ns, active=active, enabled=a.enabled, manual=a.manual, healthy=a.healthy, replay_validation=v if exact else None
    )

  def torque_residual(self, frame, *, stage_revision):
    if stage_revision != REVISION or self.admission is None or self.used or self.objective.stage == 'center':
      return 0.0, 0.0
    self.used = True
    values = self._tick(frame.active)
    delta = sum(a * b for a, b in zip(values, gates(self.objective, frame.speed, frame.setpoint, frame.jerk), strict=True))
    self.status = 'applied' if delta else 'collecting'
    return (delta, 0.0) if self.objective.stage == 'feedforward' else (0.0, delta)

  def torque_deadband(self, speed, *, stage_revision, setpoint=0.0, jerk=0.0):
    # Existing hook has only speed; center application must supply actual frame
    # inputs through revised center hook before this objective can apply.
    if stage_revision != REVISION or self.admission is None or self.used or self.objective.stage != 'center':
      return 0.0
    self.used = True
    values = self._tick(True)
    return sum(a * b for a, b in zip(values, gates(self.objective, speed, setpoint, jerk), strict=True))
