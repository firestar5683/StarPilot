"""Identity-bound passive residual identification; adapters retain authority."""
from dataclasses import dataclass, replace
import math
from typing import TypeGuard


@dataclass(frozen=True)
class Parameter:
  name: str
  stage_revision: str
  low: float
  high: float
  max_step: float
  slew_per_s: float
  excitation_floor: float = .01


@dataclass(frozen=True)
class Sample:
  mono_ns: int
  control_ns: int
  applied_ns: int
  features: tuple[float, ...]  # actual adapter stage inputs, not desired trajectory alone
  residual_target: float  # identified adapter response inverse, physical measurement
  weight: float
  active: bool = True
  override: bool = False
  fault: bool = False
  saturated: bool = False
  native_allowed: bool = True
  physical_valid: bool = True
  stage_valid: bool = True
  model_wobble: bool = False
  controller_chatter: bool = False


@dataclass(frozen=True)
class Block:
  identity: str
  block_id: str
  cohort: str  # adapter's speed/direction/phase cohort
  stage_revision: str
  response_revision: str  # independently qualified response conversion
  samples: tuple[Sample, ...]


@dataclass(frozen=True)
class Profile:
  identity: str
  sequence: int
  observed_ns: int
  expires_ns: int
  parameters: tuple[Parameter, ...]
  coefficients: tuple[float, ...]
  train_ids: tuple[str, ...]
  heldout_ids: tuple[str, ...]
  baseline_loss: float
  candidate_loss: float
  cohort_improvements: tuple[tuple[str, float], ...]
  policy: str = 'passive_stage_ridge_v1'


@dataclass(frozen=True)
class Result:
  status: str
  reason: str
  profile: Profile | None = None


def finite(value) -> TypeGuard[float]:
  return type(value) in (int, float) and math.isfinite(value)


def solve(matrix, rhs):
  rows = [list(row) + [value] for row, value in zip(matrix, rhs, strict=True)]
  for column in range(len(rhs)):
    pivot = max(range(column, len(rhs)), key=lambda row: abs(rows[row][column]))
    if abs(rows[pivot][column]) < 1e-12:
      raise ValueError('unidentified_features')
    rows[column], rows[pivot] = rows[pivot], rows[column]
    value = rows[column][column]
    rows[column] = [item / value for item in rows[column]]
    for row in range(len(rhs)):
      if row != column:
        factor = rows[row][column]
        rows[row] = [a - factor * b for a, b in zip(rows[row], rows[column], strict=True)]
  return tuple(row[-1] for row in rows)


def loss(samples, coefficients):
  return sum(row.weight * (row.residual_target - sum(a * b for a, b in zip(row.features, coefficients, strict=True))) ** 2
             for row in samples) / sum(row.weight for row in samples)


def evaluate(identity, parameters, blocks, *, now_ns, required_cohorts, response_revision, sequence=1, ridge=.01, prior=None):
  """Fit a logged stage response residual; never generates exploration commands."""
  if (type(identity) is not str or len(identity) != 64 or type(now_ns) is not int or now_ns <= 0 or
      not required_cohorts or not response_revision or type(sequence) is not int or sequence <= 0 or
      not 1 <= len(parameters) <= 8 or not 8 <= len(blocks) <= 24 or not finite(ridge) or ridge <= 0):
    return Result('unavailable', 'contract')
  count = len(parameters)
  if any(not all(finite(v) for v in (p.low, p.high, p.max_step, p.slew_per_s, p.excitation_floor)) or
         not p.low <= 0 <= p.high or p.max_step <= 0 or p.slew_per_s <= 0 or p.excitation_floor <= 0 for p in parameters):
    return Result('unavailable', 'parameter_bounds')
  if prior is not None and (type(prior) is not tuple or len(prior) != count or
                            any(not finite(value) or not parameter.low <= value <= parameter.high or
                                abs(value) > parameter.max_step for parameter, value in zip(parameters, prior, strict=True))):
    return Result('unavailable', 'historical_prior')
  centre = (0.,) * count if prior is None else prior
  ids = set()
  previous = 0
  for block in blocks:
    if (block.identity != identity or block.block_id in ids or block.cohort not in required_cohorts or block.response_revision != response_revision or
        any(p.stage_revision != block.stage_revision for p in parameters) or not 40 <= len(block.samples) <= 240):
      return Result('unavailable', 'provenance')
    ids.add(block.block_id)
    for row in block.samples:
      if (not row.active or row.override or row.fault or row.saturated or not row.native_allowed or
          not row.physical_valid or not row.stage_valid or row.model_wobble or row.controller_chatter or
          len(row.features) != count or not all(finite(v) for v in (*row.features, row.residual_target, row.weight)) or
          row.weight <= 0 or not 0 < row.control_ns <= row.applied_ns <= row.mono_ns <= now_ns or row.mono_ns <= previous):
        return Result('unavailable', 'evidence')
      previous = row.mono_ns
  split = len(blocks) // 2
  train, heldout = blocks[:split], blocks[split:]
  cohorts = set(required_cohorts)
  if any(sum(b.cohort == cohort for b in train) < 2 or sum(b.cohort == cohort for b in heldout) < 2 for cohort in cohorts):
    return Result('collecting', 'independent_cohorts')
  rows = tuple(row for block in train for row in block.samples)
  # Reject confounded stage bases before ridge can disguise rank deficiency.
  gram = [[sum(row.weight * row.features[i] * row.features[j] for row in rows) for j in range(count)] for i in range(count)]
  try:
    diagonal = [gram[i][i] for i in range(count)]
    if any(value / len(rows) < parameter.excitation_floor ** 2 for value, parameter in zip(diagonal, parameters, strict=True)):
      raise ValueError("insufficient_excitation")
    normalized = [[gram[i][j] / math.sqrt(diagonal[i] * diagonal[j]) for j in range(count)] for i in range(count)]
    # Inverse amplification bounds poor excitation independently of ridge.
    for i in range(count):
      inverse_column = solve(normalized, [float(j == i) for j in range(count)])
      if max(abs(value) for value in inverse_column) > 100:
        raise ValueError("confounded_features")
    regularized = [[value + (ridge * len(rows) if i == j else 0) for j, value in enumerate(row)] for i, row in enumerate(gram)]
    coefficients = solve(regularized, [sum(row.weight * row.features[i] * row.residual_target for row in rows) +
                                       ridge * len(rows) * centre[i] for i in range(count)])
  except ValueError:
    return Result('collecting', 'confounded_stage')
  if any(not p.low <= value <= p.high or abs(value) > p.max_step for p, value in zip(parameters, coefficients, strict=True)):
    return Result('rejected', 'coordinate_envelope')
  zero = (0.,) * count
  improvements = []
  for cohort in sorted(cohorts):
    independent = [loss(b.samples, zero) - loss(b.samples, coefficients) for b in heldout if b.cohort == cohort]
    mean = sum(independent) / len(independent)
    variance = sum((x - mean) ** 2 for x in independent) / (len(independent) - 1)
    lower = mean - 12.707 * math.sqrt(variance / len(independent))
    if lower <= 0:
      return Result('rejected', 'heldout_cohort_regression_or_noise')
    improvements.append((cohort, lower))
  held_rows = tuple(row for block in heldout for row in block.samples)
  base, candidate = loss(held_rows, zero), loss(held_rows, coefficients)
  profile = Profile(identity, sequence, now_ns, now_ns + 500_000_000, tuple(parameters), coefficients,
                    tuple(b.block_id for b in train), tuple(b.block_id for b in heldout), base, candidate, tuple(improvements))
  return Result('qualified', 'passive_response_fit', profile)


@dataclass(frozen=True)
class ReplayValidation:
  profile: Profile
  baseline_revision: str
  physical_model_revision: str
  no_saturation_regression: bool
  no_slew_regression: bool
  worst_cohort_improvement: float


def replay_accepts(validation, profile):
  return (isinstance(validation, ReplayValidation) and validation.profile == profile and
          bool(validation.baseline_revision) and bool(validation.physical_model_revision) and
          validation.no_saturation_regression is True and validation.no_slew_regression is True and
          finite(validation.worst_cohort_improvement) and validation.worst_cohort_improvement > 0)


class ProfileOwner:
  """Logical residual owner; zero restores the adapter's unchanged fallback stages."""
  def __init__(self, identity, parameters, *, baseline_revision, physical_model_revision):
    self.identity, self.parameters = identity, tuple(parameters)
    self.baseline_revision = baseline_revision
    self.physical_model_revision = physical_model_revision
    self.applied = (0.,) * len(parameters)
    self.last_ns = None
    self.sequence = 0
    self.last_profile = None

  def tick(self, profile, *, now_ns, active, enabled, manual, healthy, replay_validation):
    valid_clock = type(now_ns) is int and now_ns > 0 and (self.last_ns is None or 0 < now_ns - self.last_ns <= 50_000_000)
    dt = .01 if self.last_ns is None or not valid_clock else (now_ns - self.last_ns) / 1e9
    self.last_ns = now_ns if type(now_ns) is int and now_ns > 0 else None
    valid = (valid_clock and active and enabled and not manual and healthy and replay_accepts(replay_validation, profile) and
             replay_validation.baseline_revision == self.baseline_revision and
             replay_validation.physical_model_revision == self.physical_model_revision and
             isinstance(profile, Profile) and profile.identity == self.identity and profile.parameters == self.parameters and
             profile.policy == 'passive_stage_ridge_v1' and type(profile.sequence) is int and profile.sequence > 0 and profile.sequence >= self.sequence and
             (profile.sequence != self.sequence or profile == self.last_profile) and
             0 < profile.observed_ns <= now_ns <= profile.expires_ns <= profile.observed_ns + 500_000_000 and
             len(profile.coefficients) == len(self.parameters) and all(finite(v) for v in (profile.candidate_loss, profile.baseline_loss)) and
             0 <= profile.candidate_loss < profile.baseline_loss and bool(profile.cohort_improvements) and
             all(finite(value) and value > 0 for _, value in profile.cohort_improvements) and
             len(set(profile.train_ids + profile.heldout_ids)) == len(profile.train_ids) + len(profile.heldout_ids) and
             len(profile.train_ids) >= 4 and len(profile.heldout_ids) >= 4 and
             all(finite(v) and p.low <= v <= p.high and abs(v) <= p.max_step
                 for p, v in zip(self.parameters, profile.coefficients, strict=True)))
    if valid:
      self.sequence = profile.sequence
      self.last_profile = profile
    target = profile.coefficients if valid else (0.,) * len(self.parameters)
    if not valid:
      self.applied = target
    else:
      self.applied = tuple(min(max(value, old - p.slew_per_s * dt), old + p.slew_per_s * dt)
                           for p, old, value in zip(self.parameters, self.applied, target, strict=True))
    return self.applied


@dataclass(frozen=True)
class ApplicationOutcome:
  identity: str
  profile_sequence: int
  observed_ns: int
  status: str
  actual_coordinates: tuple[float, ...]
  reason: str
  baseline_revision: str
  physical_model_revision: str


@dataclass(frozen=True)
class CurrentAdmission:
  identity: str
  baseline_revision: str
  physical_model_revision: str
  source_ns: int
  healthy: bool
  enabled: bool
  manual: bool
  context_unchanged: bool


def readmit_profile(fit, validation, admission, *, now_ns, sequence):
  """Fresh source admission renews a retained fit, never its training evidence."""
  if (not isinstance(fit, Profile) or not replay_accepts(validation, fit) or
      not isinstance(admission, CurrentAdmission) or type(now_ns) is not int or
      type(sequence) is not int or sequence <= fit.sequence or
      admission.identity != fit.identity or admission.baseline_revision != validation.baseline_revision or
      admission.physical_model_revision != validation.physical_model_revision or
      not admission.healthy or not admission.enabled or admission.manual or not admission.context_unchanged or
      type(admission.source_ns) is not int or not 0 < admission.source_ns <= now_ns <= admission.source_ns + 100_000_000):
    return None
  fresh = replace(fit, sequence=sequence, observed_ns=now_ns, expires_ns=now_ns + 500_000_000)
  return fresh, replace(validation, profile=fresh)
