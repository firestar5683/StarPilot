"""Bounded identification of an already-supported linear torque conversion.

Applied torque and bank-corrected, lag-aligned physical response identify only
latAccelFactor. Held-out model fit is not a prediction of closed-loop tracking.
Offset, friction, feedback gains, native limits and rich surfaces stay fixed.
"""
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
import statistics

from openpilot.starpilot.flm.gm_evidence import FLMSample

MAX_WINDOWS = 24
MAX_CONTROL_SAMPLES = 240
MAX_RESPONSE_POINTS = 240
VERSION = 1
LINEAR_POLICY_ID = 'linear_inverse_v1'
# Existing full-rate torqued maturity and vehicle factor envelope, not qlog thresholds.
MIN_TOTAL_POINTS = 4000
MIN_TRAIN_POINTS = 2000
TORQUE_BUCKETS = ((-.5, -.3), (-.3, -.2), (-.2, -.1), (-.1, 0),
                 (0, .1), (.1, .2), (.2, .3), (.3, .5))
MIN_BUCKET_POINTS = (100, 300, 500, 500, 500, 500, 300, 100)
ENGAGED_NS = 2_000_000_000
# Conservative upper-rounded two-sided 95% Student-t quantiles for df1..23.
# Intervals assume independent, approximately normal block estimates; they are
# statistical model evidence, not physical safety limits or tracking guarantees.
T95 = (12.707, 4.303, 3.183, 2.777, 2.571, 2.447, 2.365, 2.307,
       2.263, 2.229, 2.202, 2.179, 2.161, 2.145, 2.132, 2.120,
       2.110, 2.102, 2.094, 2.087, 2.080, 2.074, 2.069)


@dataclass(frozen=True)
class PhysicalPoint:
  mono_ns: int
  applied_torque: float
  lateral_accel: float  # calibrated v*yaw - g*sin(roll), aligned using frozen lag


@dataclass(frozen=True)
class EvidenceWindow:
  identity_sha256: str
  block_id: str
  controls: tuple[FLMSample, ...]  # sampled metrics, never 100 Hz symptom classification
  response: tuple[PhysicalPoint, ...]
  active_since_ns: int  # uninterrupted active/no-override history, before alignment
  alignment_lag_ns: int  # learned outside this fit and frozen before holdout


@dataclass(frozen=True)
class AcceptancePolicy:
  identifier: str = LINEAR_POLICY_ID
  max_step_fraction: float = .3


LINEAR_POLICY = AcceptancePolicy()


def linear_policy() -> AcceptancePolicy:
  """Implemented algorithm contract, with callback/controller qualification external."""
  return LINEAR_POLICY


@dataclass(frozen=True)
class AutomaticResult:
  identity_sha256: str
  status: str
  reason: str
  candidate: tuple[tuple[str, float], ...] = ()
  metrics: tuple[tuple[str, float], ...] = ()
  acceptance_policy_id: str = ''
  family: str = 'linearFactor'
  version: int = VERSION


def _finite(value):
  return type(value) in (int, float) and math.isfinite(value)


def identity_digest(identity: Mapping) -> str:
  if not isinstance(identity, Mapping):
    raise ValueError('source_identity')
  return hashlib.sha256(json.dumps(dict(identity), sort_keys=True, allow_nan=False,
                                   separators=(',', ':')).encode()).hexdigest()


def admit_linear_factor(value, vehicle_factor, baseline_factor, max_step_fraction):
  return bool(all(_finite(x) for x in (value, vehicle_factor, baseline_factor, max_step_fraction)) and
              vehicle_factor > 0 and baseline_factor > 0 and 0 < max_step_fraction <= .3 and
              .7 * vehicle_factor <= value <= 1.3 * vehicle_factor and
              (1 - max_step_fraction) * baseline_factor <= value <= (1 + max_step_fraction) * baseline_factor)


def _window(window, identity):
  if (not isinstance(window, EvidenceWindow) or window.identity_sha256 != identity or
      type(window.block_id) is not str or not 1 <= len(window.block_id) <= 128 or
      not 40 <= len(window.controls) <= MAX_CONTROL_SAMPLES or
      not 40 <= len(window.response) <= MAX_RESPONSE_POINTS or
      type(window.active_since_ns) is not int or window.active_since_ns <= 0 or
      type(window.alignment_lag_ns) is not int or not 0 <= window.alignment_lag_ns <= 500_000_000):
    raise ValueError('window_source')
  rows = window.controls
  route = rows[0].route, rows[0].segment
  band = 'fast' if rows[0].v_ego < 25 else 'highway'
  for index, row in enumerate(rows):
    if (not isinstance(row, FLMSample) or (row.route, row.segment) != route or
        not all(_finite(x) for x in (row.t, row.v_ego, row.actual_la, row.desired_la, row.desired_jerk)) or
        not row.lat_active or row.steering_pressed or row.saturated or not 15 < row.v_ego <= 90 or
        ('fast' if row.v_ego < 25 else 'highway') != band):
      raise ValueError('window_control')
    if index and not 5_000_000 <= round(row.t * 1e9) - round(rows[index - 1].t * 1e9) <= 100_000_000:
      raise ValueError('control_cadence_or_gap')
  points = []
  cursor = 0
  direction = None
  for point in window.response:
    if (not isinstance(point, PhysicalPoint) or type(point.mono_ns) is not int or point.mono_ns <= 0 or
        not _finite(point.applied_torque) or not _finite(point.lateral_accel) or
        not .02 < abs(point.applied_torque) or not -.5 <= point.applied_torque < .5 or abs(point.lateral_accel) > 1 or
        point.mono_ns - window.alignment_lag_ns - window.active_since_ns < ENGAGED_NS or
        points and not 0 < point.mono_ns - points[-1].mono_ns <= 100_000_000):
      raise ValueError('response_source_or_engagement')
    while cursor + 1 < len(rows) and round(rows[cursor + 1].t * 1e9) <= point.mono_ns:
      cursor += 1
    if (not round(rows[0].t * 1e9) <= point.mono_ns or
        not 0 <= point.mono_ns - round(rows[cursor].t * 1e9) <= 30_000_000):
      raise ValueError('response_join')
    side = 'left' if point.applied_torque > 0 else 'right'
    if direction is not None and side != direction:
      raise ValueError('mixed_direction')
    direction = side
    points.append(point)
  mean_t = statistics.mean(p.applied_torque for p in points)
  mean_a = statistics.mean(p.lateral_accel for p in points)
  centered = tuple((p.applied_torque - mean_t, p.lateral_accel - mean_a) for p in points)
  energy = sum(t * t for t, _ in centered)
  if energy <= 0:
    raise ValueError('response_unexcited')
  slope = sum(t * a for t, a in centered) / energy
  if not _finite(slope) or slope <= 0:
    raise ValueError('response_unidentifiable')
  return direction, band, centered, slope


def _loss(centered, factor):
  return statistics.mean((actual - factor * torque) ** 2 for torque, actual in centered)


def _mean_radius(values):
  return T95[len(values) - 2] * statistics.stdev(values) / math.sqrt(len(values))


def _lower_mean(values):
  return statistics.mean(values) - _mean_radius(values)


def evaluate_linear_factor(identity: Mapping, windows: tuple[EvidenceWindow, ...], *,
                           baseline_factor: float, vehicle_factor: float,
                           linear_conversion_verified: bool,
                           policy: AcceptancePolicy | None = LINEAR_POLICY) -> AutomaticResult:
  source = identity_digest(identity)

  def result(status, reason, *, candidate=(), metrics=()):
    return AutomaticResult(source, status, reason, candidate, metrics,
                           policy.identifier if policy is not None else '')

  if linear_conversion_verified is not True:
    return result('unavailable', 'conversion_not_identified')
  if policy != linear_policy():
    return result('unavailable', 'algorithm_policy_not_admitted')
  assert policy is not None
  if not admit_linear_factor(baseline_factor, vehicle_factor, baseline_factor, policy.max_step_fraction):
    return result('unavailable', 'baseline_outside_vehicle_bounds')
  if (type(windows) is not tuple or len(windows) > MAX_WINDOWS or
      any(not isinstance(w, EvidenceWindow) for w in windows) or
      len({w.block_id for w in windows}) != len(windows)):
    return result('rejected', 'window_limit_or_duplicate')
  if len(windows) < 16:
    return result('collecting', 'independent_blocks_insufficient')
  try:
    ranges = {}
    for window in windows:
      key = window.controls[0].route
      start = round(window.controls[0].t * 1e9)
      end = max(round(window.controls[-1].t * 1e9), window.response[-1].mono_ns)
      if key in ranges and start <= ranges[key]:
        raise ValueError('overlapping_or_reordered_windows')
      ranges[key] = end
    parsed = [_window(window, source) for window in windows]
  except (AttributeError, IndexError, OverflowError, TypeError, ValueError, ZeroDivisionError):
    return result('rejected', 'invalid_or_unidentifiable_evidence')
  if len({w.alignment_lag_ns for w in windows}) != 1:
    return result('rejected', 'alignment_changed_across_holdout')
  counts = [sum(low <= point.applied_torque < high for w in windows for point in w.response)
            for low, high in TORQUE_BUCKETS]
  if sum(len(w.response) for w in windows) < MIN_TOTAL_POINTS or any(
      count < minimum for count, minimum in zip(counts, MIN_BUCKET_POINTS, strict=True)):
    return result('collecting', 'physical_excitation_insufficient')
  # Complete chronological blocks are split before fitting; heldout never
  # adjusts lag or the candidate factor. Per-block centering is the same fixed
  # nuisance-removal objective for baseline and candidate, not an offset update.
  split = len(windows) // 2
  train, heldout = parsed[:split], parsed[split:]
  if sum(len(w.response) for w in windows[:split]) < MIN_TRAIN_POINTS:
    return result('collecting', 'training_points_insufficient')
  cohorts = tuple((side, band) for side in ('left', 'right') for band in ('fast', 'highway'))
  if any(sum(row[:2] == cohort for row in partition) < 2 for partition in (train, heldout) for cohort in cohorts):
    return result('collecting', 'independent_direction_speed_support_insufficient')
  slopes = [row[3] for row in train]
  factor = statistics.mean(slopes)
  slope_radius = _mean_radius(slopes)
  if any(not admit_linear_factor(value, vehicle_factor, baseline_factor, policy.max_step_fraction)
         for value in (factor - slope_radius, factor, factor + slope_radius)):
    return result('rejected', 'factor_envelope_or_step')
  if factor - slope_radius <= baseline_factor <= factor + slope_radius:
    return result('collecting', 'factor_change_not_identified')
  base_losses = [_loss(row[2], baseline_factor) for row in heldout]
  fit_losses = [_loss(row[2], factor) for row in heldout]
  improvement = [before - after for before, after in zip(base_losses, fit_losses, strict=True)]
  metrics = (('trainWindows', float(len(train))), ('heldoutWindows', float(len(heldout))),
             ('trainBaselineMSE', statistics.mean(_loss(row[2], baseline_factor) for row in train)),
             ('trainFitMSE', statistics.mean(_loss(row[2], factor) for row in train)),
             ('heldoutBaselineMSE', statistics.mean(base_losses)), ('heldoutFitMSE', statistics.mean(fit_losses)),
             ('factorEstimate', factor), ('factorBlockIntervalRadius', slope_radius),
             ('heldoutImprovementLowerBound', _lower_mean(improvement)))
  if dict(metrics)['trainFitMSE'] >= dict(metrics)['trainBaselineMSE']:
    return result('rejected', 'training_response_fit_insufficient', metrics=metrics)
  for cohort in cohorts:
    cohort_improvement = [value for row, value in zip(heldout, improvement, strict=True) if row[:2] == cohort]
    if _lower_mean(cohort_improvement) < 0:
      return result('rejected', 'heldout_direction_speed_regression', metrics=metrics)
  if _lower_mean(improvement) <= 0:
    return result('rejected', 'heldout_response_fit_insufficient', metrics=metrics)
  return result('qualified_fit', 'measured_linear_response_fit', candidate=(('latAccelFactor', factor),), metrics=metrics)
