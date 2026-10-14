"""Passive centre/friction objective. No exploration, PID, tune or actuator writes.

The caller provides an exact selected-controller replay on immutable snapshots.
A frozen, independently fitted command/physical model validates the baseline
before any counterfactual is scored. A symptom bucket grants no authority.
"""

from dataclasses import dataclass
import math
from openpilot.starpilot.flm.adaptive_profile import Parameter, Profile, ProfileOwner, Result, ReplayValidation, ApplicationOutcome
from openpilot.starpilot.flm.physical_response import PhysicalModel

REVISION = 'selected-centre-prefriction-v1'


def band(speed):
  return 'low' if speed < 6 else 'mid' if speed < 15 else 'fast' if speed < 25 else 'highway'


@dataclass(frozen=True)
class CentreObjective:
  coordinate: str
  speed_band: str

  def __post_init__(self):
    if self.coordinate not in ('threshold', 'deadband') or self.speed_band not in ('low', 'mid', 'fast', 'highway'):
      raise ValueError('unknown centre objective')

  @property
  def parameters(self):
    lo, hi, slew = (-0.03, 0.03, 0.005) if self.coordinate == 'threshold' else (0.0, 0.01, 0.002)
    return tuple(Parameter(f'centre.{self.coordinate}.{self.speed_band}.{side}', REVISION, lo, hi, hi, slew) for side in ('left', 'right'))

  @property
  def grid(self):
    return (-0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03) if self.coordinate == 'threshold' else (0.0, 0.0025, 0.005, 0.0075, 0.01)


@dataclass(frozen=True)
class StageTrace:
  baseline_revision: str
  speed: float
  setpoint: float
  jerk: float
  friction_error: float  # exact AFTER selected jerk/low-speed shaping
  baseline_ff: float  # exact AFTER baseline FF shaping, BEFORE friction
  baseline_threshold: float
  baseline_deadzone: float  # lateral acceleration units
  deadzone_accel_per_degree: float  # frozen VM at same speed, roll zero
  baseline_friction: float  # AFTER selected friction multiplier
  selected_command: float  # same domain/sign as physical model
  active: bool = True
  override: bool = False
  fault: bool = False
  saturated: bool = False
  limited: bool = False
  native_allowed: bool = True
  model_wobble: bool = False

  def valid(self):
    return (
      bool(self.baseline_revision)
      and all(
        type(v) in (int, float) and math.isfinite(v)
        for v in (
          self.speed,
          self.setpoint,
          self.jerk,
          self.friction_error,
          self.baseline_ff,
          self.baseline_threshold,
          self.baseline_deadzone,
          self.deadzone_accel_per_degree,
          self.baseline_friction,
          self.selected_command,
        )
      )
      and 2 <= self.speed <= 90
      and self.baseline_threshold > 0
      and self.baseline_deadzone >= 0
      and self.deadzone_accel_per_degree > 0
      and self.active
      and not self.override
      and not self.fault
      and not self.saturated
      and not self.limited
      and self.native_allowed
      and not self.model_wobble
    )

  @property
  def direction(self):
    return 'left' if self.friction_error > 0 else 'right'


@dataclass(frozen=True)
class CentreRow:
  control_ns: int
  applied_ns: int
  response_ns: int
  trace: StageTrace
  context: str
  physical_response: float  # independently observed yaw/angle at response_ns
  reference_response: float  # calm request at response_ns, never observed yaw
  snapshot: object  # immutable selected controller snapshot owned by adapter


@dataclass(frozen=True)
class CentreBlock:
  identity: str
  block_id: str
  speed_band: str
  direction: str
  rows: tuple[CentreRow, ...]
  symptom_bucket: str  # actual gm_evidence bucket; routes evidence, not tuning


@dataclass(frozen=True)
class ReplayPoint:
  command: float
  saturated: bool
  friction_output: float | None = None


def _prediction(model, command):
  # Raw final CC sign is preserved in replay/wire; physical projection is the
  # explicit torque domain orientation, never a tuning/table inverse.
  command = -command if model.domain == 'normalized_torque' else command
  if not math.isfinite(command) or not model.command_low <= command <= model.command_high:
    raise ValueError('physical_support')
  return model.slope * command + model.intercept


def evaluate_centre(
  identity,
  objective,
  blocks,
  model,
  replay,
  *,
  now_ns,
  baseline_revision,
  physical_model_revision,
  sequence=1,
  prediction_tolerance=0.01,
  min_sensitivity=1e-6,
  prior_coefficients=None,
):
  """Replay(snapshot, threshold_delta, extra_deadband_deg) -> ReplayPoint.

  Replay must call the ACTUAL selected friction implementation or the full
  selected controller with frozen state; native table inverses are forbidden.
  Fit/search uses training blocks only. Exact nonlinear heldout replay follows.
  Linear lag models are accepted only within independent heldout validity and
  matching baseline response; hysteresis/model mismatch remains collecting.
  """
  if (
    not isinstance(objective, CentreObjective)
    or not isinstance(model, PhysicalModel)
    or len(identity) != 64
    or model.identity != identity
    or model.domain not in ('torque', 'normalized_torque')
    or not all(math.isfinite(v) for v in (model.slope, model.intercept, model.command_low, model.command_high, model.heldout_rmse))
    or model.slope <= 0
    or not model.command_low < model.command_high
    or not 0 <= model.heldout_rmse <= prediction_tolerance
    or not 0 < model.lag_ns <= 500_000_000
    or len(model.train_blocks) < 4
    or len(model.heldout_blocks) < 4
    or set(model.train_blocks) & set(model.heldout_blocks)
    or not baseline_revision
    or not physical_model_revision
    or not 8 <= len(blocks) <= 24
    or type(now_ns) is not int
    or now_ns <= 0
    or type(sequence) is not int
    or sequence <= 0
    or not math.isfinite(prediction_tolerance)
    or not 0 < prediction_tolerance <= 0.05
    or not math.isfinite(min_sensitivity)
    or min_sensitivity <= 0
  ):
    return Result('collecting', 'centre_contract'), None
  if prior_coefficients is not None and (type(prior_coefficients) is not tuple or len(prior_coefficients) != 2):
    return Result('collecting', 'centre_prior_scope'), None
  calibration_ids = set(model.train_blocks + model.heldout_blocks)
  ids = set()
  previous = 0
  for block in blocks:
    if (
      block.identity != identity
      or block.block_id in ids
      or block.block_id in calibration_ids
      or block.speed_band != objective.speed_band
      or block.direction not in ('left', 'right', 'mixed')
      or block.symptom_bucket != 'center_chatter'
      or not 40 <= len(block.rows) <= 240
    ):
      return Result('collecting', 'centre_provenance'), None
    ids.add(block.block_id)
    reference = [r.reference_response for r in block.rows]
    # Same calm-path reversal definition as gm_evidence: significant deltas,
    # including a weave that never crosses zero.
    steps = [b - a for a, b in zip(reference, reference[1:], strict=False) if abs(b - a) >= 0.008]
    reversals = sum((a > 0) != (b > 0) for a, b in zip(steps, steps[1:], strict=False))
    if not all(math.isfinite(v) for v in reference) or max(reference) - min(reference) > 0.18 or reversals > 3:
      return Result('collecting', 'model_wobble'), None
    for row in block.rows:
      t = row.trace
      if (
        not isinstance(t, StageTrace)
        or not t.valid()
        or t.baseline_revision != baseline_revision
        or band(t.speed) != objective.speed_band
        or block.direction != 'mixed'
        and t.direction != block.direction
        or row.context != model.context
        or not 0 < row.control_ns <= row.applied_ns < row.response_ns <= now_ns
        or not 0 <= row.response_ns - model.lag_ns - row.applied_ns <= 30_000_000
        or row.response_ns <= previous
        or now_ns - row.response_ns > 600_000_000_000
        or not math.isfinite(row.physical_response)
        or abs(t.setpoint) > 0.18
        or abs(t.jerk) > 0.5
      ):
        return Result('collecting', 'centre_ineligible'), None
      previous = row.response_ns
      try:
        base = replay(row.snapshot, 0.0, 0.0)
        if (
          not isinstance(base, ReplayPoint)
          or base.saturated
          or abs(base.command - t.selected_command) > 1e-9
          or abs(_prediction(model, base.command) - row.physical_response) > max(prediction_tolerance, 3 * model.heldout_rmse)
        ):
          return Result('collecting', 'physical_baseline_mismatch'), None
      except (ValueError, TypeError, AttributeError, OverflowError):
        return Result('collecting', 'missing_selected_replay'), None
  train, held = blocks[: len(blocks) // 2], blocks[len(blocks) // 2 :]

  def directed(block, side):
    from dataclasses import replace

    rows = tuple(r for r in block.rows if r.trace.direction == side)
    return replace(block, rows=rows, direction=side) if rows else None

  if any(
    sum(directed(b, side) is not None for b in group) < 2 or sum(r.trace.direction == side for b in group for r in b.rows) < 80
    for group in (train, held)
    for side in ('left', 'right')
  ):
    return Result('collecting', 'centre_independent_directions'), None

  def block_loss(block, delta, check_slew=False):
    errors = []
    base_commands = []
    candidate_commands = []
    for row in block.rows:
      threshold, deadband = (delta, 0.0) if objective.coordinate == 'threshold' else (0.0, delta)
      point = replay(row.snapshot, threshold, deadband)
      if not isinstance(point, ReplayPoint) or point.saturated:
        raise ValueError('candidate_saturation')
      errors.append((_prediction(model, point.command) - row.reference_response) ** 2)
      base_commands.append(row.trace.selected_command)
      candidate_commands.append(point.command)
    if check_slew and any(
      abs(y - x) > abs(b - a) + 1e-9 for a, b, x, y in zip(base_commands, base_commands[1:], candidate_commands, candidate_commands[1:], strict=False)
    ):
      raise ValueError('candidate_slew')
    return sum(errors) / len(errors), max(abs(a - b) for a, b in zip(base_commands, candidate_commands, strict=True))

  values = []
  try:
    for coordinate_index, side in enumerate(('left', 'right')):
      group = [item for b in train if (item := directed(b, side)) is not None]
      prior = None
      if prior_coefficients is not None:
        p = objective.parameters[coordinate_index]
        value = prior_coefficients[coordinate_index]
        if type(value) in (int, float) and math.isfinite(value) and p.low <= value <= p.high and abs(value) <= p.max_step:
          prior = value
      grid = objective.grid if prior is None else tuple(sorted({*objective.grid, prior}))
      losses = [(sum(block_loss(b, d)[0] for b in group) / len(group), d) for d in grid]
      _, best = min(losses, key=lambda item: (item[0], abs(item[1] - (prior or 0.0)), abs(item[1])))
      if best == 0 or max(block_loss(b, best)[1] for b in group) < min_sensitivity:
        return Result('collecting', 'centre_knob_unidentified'), None
      values.append(best)
    improvements = []
    total_base = []
    total_candidate = []
    for side, value in zip(('left', 'right'), values, strict=True):
      gains = []
      for block in held:
        block = directed(block, side)
        if block is None:
          continue
        base = block_loss(block, 0.0)[0]
        candidate = block_loss(block, value, True)[0]
        gains.append(base - candidate)
        total_base.append(base)
        total_candidate.append(candidate)
      mean = sum(gains) / len(gains)
      variance = sum((g - mean) ** 2 for g in gains) / (len(gains) - 1)
      lower = mean - 12.707 * math.sqrt(variance / len(gains))
      if lower <= 0:
        return Result('rejected', 'centre_heldout_regression_or_noise'), None
      improvements.append((f'{objective.speed_band}.{side}.center', lower))
  except (TypeError, ValueError, AttributeError, OverflowError):
    return Result('collecting', 'centre_counterfactual_outside_support'), None
  # Replay mixed sign transitions in their actual chronological order, not
  # just within directional subsets. Joint heldout slew/saturation must hold.
  try:
    for block in held:
      last_base = last_candidate = None
      for row in block.rows:
        delta = values[0 if row.trace.friction_error > 0 else 1]
        threshold, deadband = (delta, 0.0) if objective.coordinate == 'threshold' else (0.0, delta)
        point = replay(row.snapshot, threshold, deadband)
        if not isinstance(point, ReplayPoint) or point.saturated:
          return Result('rejected', 'centre_mixed_saturation'), None
        _prediction(model, point.command)
        if last_base is not None and abs(point.command - last_candidate) > abs(row.trace.selected_command - last_base) + 1e-9:
          return Result('rejected', 'centre_mixed_slew'), None
        last_base, last_candidate = row.trace.selected_command, point.command
  except (AttributeError, TypeError, ValueError, OverflowError):
    return Result('collecting', 'centre_counterfactual_outside_support'), None
  profile = Profile(
    identity,
    sequence,
    now_ns,
    now_ns + 500_000_000,
    objective.parameters,
    tuple(values),
    tuple(b.block_id for b in train),
    tuple(b.block_id for b in held),
    sum(total_base) / len(total_base),
    sum(total_candidate) / len(total_candidate),
    tuple(improvements),
  )
  validation = ReplayValidation(profile, baseline_revision, physical_model_revision, True, True, min(v for _, v in improvements))
  return Result('qualified', 'centre_selected_replay_heldout', profile), validation


class CentreStageOwner:
  """Current common lease + exact local replay; every invalid tick restores zero."""

  def __init__(self, identity, objective, *, baseline_revision, physical_model_revision):
    self.objective = objective
    self.owner = ProfileOwner(identity, objective.parameters, baseline_revision=baseline_revision, physical_model_revision=physical_model_revision)
    self.baseline_revision = baseline_revision
    self.physical_model_revision = physical_model_revision

  def tick(self, trace, profile, validation, *, now_ns, enabled, manual, healthy):
    exact = (
      isinstance(validation, ReplayValidation)
      and validation.baseline_revision == self.baseline_revision
      and validation.physical_model_revision == self.physical_model_revision
      and isinstance(trace, (StageTrace, CentreFrame))
      and trace.valid()
      and trace.baseline_revision == self.baseline_revision
      and band(trace.speed) == self.objective.speed_band
      and abs(trace.setpoint) <= 0.18
      and abs(trace.jerk) <= 0.5
    )
    values = self.owner.tick(
      profile, now_ns=now_ns, active=exact, enabled=enabled, manual=manual, healthy=healthy, replay_validation=validation if exact else None
    )
    value = values[0 if trace.friction_error > 0 else 1] if exact else 0.0
    return (value, 0.0) if self.objective.coordinate == 'threshold' else (0.0, value)


@dataclass(frozen=True)
class CentreFrame:
  baseline_revision: str
  speed: float
  setpoint: float
  jerk: float
  friction_error: float
  active: bool
  override: bool
  limited: bool

  def valid(self):
    return (
      bool(self.baseline_revision)
      and all(type(v) in (int, float) and math.isfinite(v) for v in (self.speed, self.setpoint, self.jerk, self.friction_error))
      and 2 <= self.speed <= 90
      and self.active
      and not self.override
      and not self.limited
    )


def apply_centre(parent, cs, setpoint, jerk, error, threshold, deadzone, degree_derivative, *, active, limited, friction_scale=1.0, parent_friction=True):
  """Call once AFTER selected shaping and BEFORE its one existing friction call.

  No absent-source arithmetic, and no second live friction/filter invocation.
  This changes only threshold and EXTRA deadzone in the selected speed band.
  Source binds one current admission via centre_residual and common lease owner.
  """
  source = getattr(parent, 'automatic_flm_centre', None)
  observer = getattr(source, 'observe_centre_stage', None)
  if callable(observer):
    try:
      observer(
        speed=float(cs.vEgo),
        setpoint=float(setpoint),
        jerk=float(jerk),
        friction_error=float(error),
        baseline_threshold=float(threshold),
        baseline_deadzone=float(deadzone),
        friction_scale=float(friction_scale),
        friction_parent_wrapper=float(bool(parent_friction)),
      )
    except (AttributeError, TypeError, ValueError, OverflowError):
      return threshold, deadzone
  if source is None or not active or limited or cs.steeringPressed:
    return threshold, deadzone
  try:
    frame = CentreFrame(
      source.baseline_revision, float(cs.vEgo), float(setpoint), float(jerk), float(error), bool(active), bool(cs.steeringPressed), bool(limited)
    )
    if not frame.valid():
      return threshold, deadzone
    delta, extra = source.centre_residual(frame, stage_revision=REVISION)
    if callable(degree_derivative):
      degree_derivative = degree_derivative() if extra else 1.0
    if (
      not all(type(v) in (int, float) and math.isfinite(v) for v in (delta, extra, degree_derivative))
      or abs(delta) > 0.03
      or not 0 <= extra <= 0.01
      or degree_derivative <= 0
    ):
      return threshold, deadzone
    new_threshold = threshold if delta == 0 else threshold * (1 + delta)
    new_deadzone = deadzone if extra == 0 else deadzone + extra * degree_derivative
    if not math.isfinite(new_threshold) or new_threshold <= 0 or not math.isfinite(new_deadzone) or new_deadzone < 0:
      return threshold, deadzone
    return new_threshold, new_deadzone
  except (AttributeError, TypeError, ValueError, OverflowError):
    return threshold, deadzone


@dataclass(frozen=True)
class CentreAdmission:
  profile: Profile | None
  validation: ReplayValidation | None
  now_ns: int
  enabled: bool
  manual: bool
  healthy: bool


class CentreSource:
  """One current prepared admission per controller cycle; no cached live lease."""

  def __init__(self, identity, objective, *, baseline_revision, physical_model_revision):
    if not baseline_revision or not physical_model_revision:
      raise ValueError('exact replay revisions required')
    self.baseline_revision = baseline_revision
    self.owner = CentreStageOwner(identity, objective, baseline_revision=baseline_revision, physical_model_revision=physical_model_revision)
    self.admission = None
    self.used = False
    self.status = 'collecting'
    self.outcome = None

  def prepare(self, admission):
    if not isinstance(admission, CentreAdmission):
      raise ValueError('current typed admission required')
    self.admission = admission
    self.used = False
    self.status = 'collecting'
    self.outcome = None

  def centre_residual(self, frame, *, stage_revision):
    if stage_revision != REVISION or self.admission is None or self.used:
      self.status = 'collecting'
      return 0.0, 0.0
    self.used = True
    a = self.admission
    result = self.owner.tick(frame, a.profile, a.validation, now_ns=a.now_ns, enabled=a.enabled, manual=a.manual, healthy=a.healthy)
    self.status = 'admitted' if any(result) else 'collecting'
    value = result[0] if self.owner.objective.coordinate == 'threshold' else result[1]
    coords = (value, 0.0) if frame.friction_error > 0 else (0.0, value)
    self.outcome = ApplicationOutcome(
      self.owner.owner.identity,
      a.profile.sequence if isinstance(a.profile, Profile) else 0,
      a.now_ns,
      'baseline',
      coords,
      'centre_stage_effect_pending' if any(result) else 'centre_fallback',
      self.baseline_revision,
      self.owner.physical_model_revision,
    )
    return result

  def finish_frame(self, *, actual_stage_effect):
    # The actual selected controller/runtime owns the final stage-effect witness.
    # Admission or a changed threshold alone never advertises Applied.
    if self.outcome is not None:
      from dataclasses import replace

      effect = actual_stage_effect is True and self.status == 'admitted'
      self.status = 'applied' if effect else 'collecting'
      self.outcome = replace(
        self.outcome,
        status='applied' if effect else 'baseline',
        reason='actual_centre_stage_used' if effect else 'centre_no_stage_effect',
        actual_coordinates=self.outcome.actual_coordinates if effect else (0.0, 0.0),
      )
    return self.outcome
