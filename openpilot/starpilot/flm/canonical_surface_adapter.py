# Copyright (c) 2018, Comma.ai, Inc.
# Copyright (c) 2026, firestar5683 and StarPilot contributors
# SPDX-License-Identifier: MIT
"""Original-bound automatic effects using the existing Dom universal FLM equations."""

import hashlib
import math
import re
import struct
from functools import lru_cache
from types import MappingProxyType

REVISION = 'torque-selected-effect-v2'
MANIFEST_REVISION = 'dom-universal-30-original-effects-v5'
DOM_REVISION = 'b220a37f4bd119e402225a7aa16a7cd84878d0af'
NAMES = (
  'ff_gain_left',
  'ff_gain_right',
  'turn_in_boost_left',
  'turn_in_boost_right',
  'unwind_taper_left',
  'unwind_taper_right',
  'center_taper_max',
  'highway_center_taper_max',
  'center_deadband_crawl_deg',
  'center_deadband_low_deg',
  'center_deadband_mid_deg',
  'center_deadband_fast_deg',
  'center_deadband_highway_deg',
  'turn_in_threshold_reduction_left',
  'turn_in_threshold_reduction_right',
  'unwind_threshold_increase_left',
  'unwind_threshold_increase_right',
  'crawl_turn_in_ff_boost_left',
  'crawl_turn_in_ff_boost_right',
  'low_speed_angle_assist_max_torque',
  'curvy_speed_min',
  'curvy_speed_max',
  'curvy_turn_in_trim_speed_min',
  'curvy_turn_in_trim_speed_max',
  'curvy_turn_in_trim_left',
  'curvy_turn_in_trim_right',
  'curvy_unwind_floor_relief_left',
  'curvy_unwind_floor_relief_right',
  'curvy_unwind_extra_reduction_left',
  'curvy_unwind_extra_reduction_right',
)
WINDOWS = ('curvy_speed_min', 'curvy_speed_max', 'curvy_turn_in_trim_speed_min', 'curvy_turn_in_trim_speed_max')
DEADBANDS = tuple(n for n in NAMES if n.startswith('center_deadband_'))
GROUPS = {
  'ff.left': ('ff_gain_left', 'turn_in_boost_left', 'unwind_taper_left', 'crawl_turn_in_ff_boost_left'),
  'ff.right': ('ff_gain_right', 'turn_in_boost_right', 'unwind_taper_right', 'crawl_turn_in_ff_boost_right'),
  'center': ('center_taper_max', 'highway_center_taper_max'),
  'friction.left': ('turn_in_threshold_reduction_left', 'unwind_threshold_increase_left'),
  'friction.right': ('turn_in_threshold_reduction_right', 'unwind_threshold_increase_right'),
  'turn.window.left': ('curvy_turn_in_trim_speed_min', 'curvy_turn_in_trim_speed_max', 'curvy_turn_in_trim_left'),
  'turn.window.right': ('curvy_turn_in_trim_speed_min', 'curvy_turn_in_trim_speed_max', 'curvy_turn_in_trim_right'),
  'unwind.window.left': ('curvy_speed_min', 'curvy_speed_max', 'curvy_unwind_floor_relief_left', 'curvy_unwind_extra_reduction_left'),
  'unwind.window.right': ('curvy_speed_min', 'curvy_speed_max', 'curvy_unwind_floor_relief_right', 'curvy_unwind_extra_reduction_right'),
  'angle.assist': ('low_speed_angle_assist_max_torque',),
  'deadband.low': ('center_deadband_crawl_deg', 'center_deadband_low_deg', 'center_deadband_mid_deg'),
  'deadband.high': ('center_deadband_fast_deg', 'center_deadband_highway_deg'),
}
# Exact existing Dom universal raw domains, frozen without controller imports.
# This prevents adaptive_profile -> canonical -> torque_surface -> policy ->
# torque_stages -> selected_effects import cycles. Tests compare every row to
# the actual selected source constructor; changing its bounds changes manifest.
RAW_DOMAINS = (
  ('ff_gain_left', 0.0, (-0.4, 0.6)),
  ('ff_gain_right', 0.0, (-0.4, 0.6)),
  ('turn_in_boost_left', 0.0, (-0.1, 2.8)),
  ('turn_in_boost_right', 0.0, (-0.1, 2.8)),
  ('unwind_taper_left', 0.0, (0.0, 12.0)),
  ('unwind_taper_right', 0.0, (0.0, 12.0)),
  ('center_taper_max', 0.0, (0.0, 0.18)),
  ('highway_center_taper_max', 0.0, (0.0, 0.18)),
  ('center_deadband_crawl_deg', 0.0, (0.0, 0.3)),
  ('center_deadband_low_deg', 0.0, (0.0, 0.3)),
  ('center_deadband_mid_deg', 0.0, (0.0, 0.2)),
  ('center_deadband_fast_deg', 0.0, (0.0, 0.12)),
  ('center_deadband_highway_deg', 0.0, (0.0, 0.08)),
  ('turn_in_threshold_reduction_left', 0.0, (0.0, 2.0)),
  ('turn_in_threshold_reduction_right', 0.0, (0.0, 2.0)),
  ('unwind_threshold_increase_left', 0.0, (0.0, 12.0)),
  ('unwind_threshold_increase_right', 0.0, (0.0, 12.0)),
  ('crawl_turn_in_ff_boost_left', 0.0, (0.0, 0.5)),
  ('crawl_turn_in_ff_boost_right', 0.0, (0.0, 0.5)),
  ('low_speed_angle_assist_max_torque', 0.0, (0.0, 0.8)),
  ('curvy_speed_min', 7.2, (4.0, 12.0)),
  ('curvy_speed_max', 21.5, (14.0, 25.0)),
  ('curvy_turn_in_trim_speed_min', 11.5, (8.0, 16.0)),
  ('curvy_turn_in_trim_speed_max', 20.5, (14.0, 25.0)),
  ('curvy_turn_in_trim_left', 0.0, (0.0, 0.2)),
  ('curvy_turn_in_trim_right', 0.0, (0.0, 0.2)),
  ('curvy_unwind_floor_relief_left', 0.0, (0.0, 0.45)),
  ('curvy_unwind_floor_relief_right', 0.0, (0.0, 0.45)),
  ('curvy_unwind_extra_reduction_left', 0.0, (0.0, 0.45)),
  ('curvy_unwind_extra_reduction_right', 0.0, (0.0, 0.45)),
)
MANIFEST_SHA256 = hashlib.sha256(
  repr(
    (MANIFEST_REVISION, DOM_REVISION, NAMES, GROUPS, RAW_DOMAINS, 'window=original*(1+coordinate);dynamic=coordinate*physical-normalizer;direct=coordinate')
  ).encode()
).hexdigest()


def finite(v):
  return type(v) in (int, float) and math.isfinite(v)


def canonical_names(names):
  if not 1 <= len(names) <= 4 or len(set(names)) != len(names) or any(n not in NAMES for n in names):
    raise ValueError('one to four canonical FLM knobs per trial')
  return tuple(n for n in NAMES if n in names)


_RAW_BY_NAME = MappingProxyType({name: (value, limits) for name, value, limits in RAW_DOMAINS})


def _coordinate_bounds_static(name) -> tuple[float, float]:
  if name not in NAMES:
    raise ValueError('unknown canonical coordinate')
  original, (raw_low, raw_high) = _RAW_BY_NAME[name]
  # Dynamic degree/torque fields are normalized against own-vehicle physical
  # units at their actual hook. Their raw domains must be checked THERE; .25 is
  # not itself degrees/normalized torque when the normalizer differs from one.
  if name in DEADBANDS or name == 'low_speed_angle_assist_max_torque':
    return 0.0, 0.25
  if name in WINDOWS:
    return max(-0.25, raw_low / original - 1), min(0.25, raw_high / original - 1)
  return max(-0.25, raw_low), min(0.25, raw_high)


_COORDINATE_BOUNDS = MappingProxyType({name: _coordinate_bounds_static(name) for name in NAMES})


def coordinate_bounds(name) -> tuple[float, float]:
  if type(name) is not str or name not in _COORDINATE_BOUNDS:
    raise ValueError('unknown canonical coordinate')
  return _COORDINATE_BOUNDS[name]


def dynamic_coordinate_bounds(name, physical_normalizer):
  if name not in DEADBANDS and name != 'low_speed_angle_assist_max_torque':
    raise ValueError('not a physically normalized coordinate')
  if not finite(physical_normalizer) or physical_normalizer < 0:
    raise ValueError('actual physical normalizer')
  if physical_normalizer == 0:
    return 0.0, 0.0
  _, (raw_low, raw_high) = _RAW_BY_NAME[name]
  low, high = coordinate_bounds(name)
  return max(low, raw_low / physical_normalizer), min(high, raw_high / physical_normalizer)


def validate_trial(coordinates):
  if type(coordinates) is not dict:
    raise ValueError('keyed original-effect coordinates')
  names = canonical_names(tuple(coordinates))
  for name, value in coordinates.items():
    low, high = coordinate_bounds(name)
    if not finite(value) or not low <= value <= high:
      raise ValueError('original effect envelope')
  return tuple((name, float(coordinates[name])) for name in names)


def parameters_for(names):
  canonical = canonical_names(names)
  if tuple(names) != canonical:
    raise ValueError('noncanonical profile order')
  return _parameters_for_cached(MANIFEST_SHA256, canonical)


@lru_cache(maxsize=64)
def _parameters_for_cached(manifest, names):
  from openpilot.starpilot.flm.adaptive_profile import Parameter

  return tuple(Parameter('effect.universal.' + n, REVISION, *coordinate_bounds(n), 0.25, 0.005) for n in names)


def full_original_anchor(baseline_revision):
  if type(baseline_revision) is not str or re.fullmatch('[a-f0-9]{64}', baseline_revision) is None:
    raise ValueError('actual original selected source baseline')
  return _full_original_anchor_cached(MANIFEST_SHA256, baseline_revision)


@lru_cache(maxsize=32)
def _full_original_anchor_cached(manifest, baseline_revision):
  original = tuple((name, float(value)) for name, value, _ in RAW_DOMAINS)
  return hashlib.sha256(repr((manifest, baseline_revision, original)).encode()).hexdigest()


def original_anchor(baseline_revision, names):
  names = canonical_names(names)
  return _original_anchor_cached(full_original_anchor(baseline_revision), names)


@lru_cache(maxsize=32)
def _original_anchor_cached(full_anchor, names):
  return hashlib.sha256(repr((full_anchor, names)).encode()).hexdigest()


def full_profile_sha256(baseline_revision, coordinates):
  values = dict(coordinates)
  if set(values) != set(NAMES):
    raise ValueError('exact full30 original coordinates')
  ordered = []
  for name in NAMES:
    value = values[name]
    low, high = coordinate_bounds(name)
    if not finite(value) or not low <= value <= high:
      raise ValueError('full30 original effect envelope')
    ordered.append(float(value))
  # Packed content keys distinguish signed zero and avoid cache aliasing bool/int
  # or retaining caller-owned mutable maps. The original wire digest is unchanged.
  return _full_profile_sha256_cached(full_original_anchor(baseline_revision), struct.pack('!30d', *ordered))


@lru_cache(maxsize=128)
def _full_profile_sha256_cached(full_anchor, packed):
  ordered = tuple(zip(NAMES, struct.unpack('!30d', packed), strict=True))
  return hashlib.sha256(repr((full_anchor, ordered)).encode()).hexdigest()


class CanonicalSurfaceEffects:
  """Admitted automatic surface effects for controller execution and replay.

 Admission binds full_profile_sha256, manifest,
 the selected baseline, native delivery, and trial dimensions in its proof.
 No Params, fitting, JSON, cloned controller or native writes belong here.
 """

  def __init__(self, coordinates, source_baseline_revision, *, accumulated=None):
    from openpilot.starpilot.flm import torque_surface as surface_math

    trial = validate_trial(coordinates)
    values = dict.fromkeys(NAMES, 0.0)
    if accumulated is not None:
      if type(accumulated) is not dict or any(n not in NAMES for n in accumulated):
        raise ValueError('accumulated canonical profile')
      for n, v in accumulated.items():
        low, high = coordinate_bounds(n)
        if not finite(v) or not low <= v <= high:
          raise ValueError('accumulated original effect envelope')
      values.update(accumulated)
    values.update(dict(trial))
    self.values = values
    self.names = tuple(n for n, _ in trial)
    self.applied_coordinates = tuple(v for _, v in trial)
    self.original_effect_anchor = original_anchor(source_baseline_revision, self.names)
    self.full_original_anchor = full_original_anchor(source_baseline_revision)
    self.full_profile_sha256 = full_profile_sha256(source_baseline_revision, values)
    self.math = surface_math
    # Existing Dom UNIVERSAL neutral defaults: zero amplitude; shared window
    # domains are exactly the already-global source's domains, not Ioniq gains.
    raw = dict(surface_math._GM_NEUTRAL)
    for n, value in values.items():
      if n in WINDOWS:
        raw[n] = raw[n] * (1 + value)
      elif n in DEADBANDS or n == 'low_speed_angle_assist_max_torque':
        raw[n] = 0.0  # Own-vehicle physical normalizer supplied at actual hook.
      else:
        raw[n] = value
    self.surface = surface_math.GmSurface('torque_universal', raw)
    self.stage_calls = self.friction_calls = self.deadzone_calls = self.output_calls = 0
    self.frame_ns = 0

  def begin_frame(self, control_ns):
    if type(control_ns) is not int or control_ns <= self.frame_ns:
      raise ValueError('nonmonotonic effect frame')
    self.frame_ns = control_ns
    self.stage_calls = self.friction_calls = self.deadzone_calls = self.output_calls = 0

  def _check(self, anchor):
    if anchor != self.original_effect_anchor:
      raise ValueError('foreign original FLM anchor')

  @property
  def pid_error_calls(self):
    return self.deadzone_calls

  def selected_pid_error(self, frame, *, original_anchor):
    from openpilot.starpilot.flm.pid_stages import canonical_error

    return canonical_error(self, frame, original_anchor=original_anchor)

  def selected_pid_stage(self, frame, *, original_anchor):
    from openpilot.starpilot.flm.pid_stages import canonical_feedforward

    return canonical_feedforward(self, frame, original_anchor=original_anchor)

  def selected_stage(self, frame, *, original_anchor):
    self._check(original_anchor)
    self.stage_calls += 1
    if self.stage_calls != 1:
      raise ValueError('duplicate actual FLM stage')
    if not frame.valid() or not frame.active or frame.driver_override or frame.limited:
      return frame.baseline_ff, frame.baseline_threshold
    m, s = self.math, self.surface
    # Exact existing Dom universal controller order; notably no invented reciprocal
    # center compensation or substituted speed/phase/shape equations.
    center = m._gm_get_flm_full_surface_center_taper_scale(s, s.profile, frame.setpoint, frame.speed, True)
    scale = m._gm_get_flm_full_surface_ff_scale(s, s.profile, frame.setpoint, frame.jerk, frame.speed, True) * center
    threshold = m._gm_get_flm_full_surface_friction_threshold(s, s.profile, frame.baseline_threshold, frame.speed, frame.setpoint, frame.jerk, True)
    ff = frame.baseline_ff if scale == 1 else frame.baseline_ff * scale
    if (
      not finite(ff)
      or not finite(threshold)
      or threshold <= 0
      or abs(ff - frame.baseline_ff) > 0.25 * abs(frame.baseline_ff) + 1e-12
      or abs(threshold - frame.baseline_threshold) > 0.25 * frame.baseline_threshold + 1e-12
    ):
      raise ValueError('composed original selected effect envelope')
    return ff, threshold

  def selected_friction(self, baseline, *, original_anchor):
    self._check(original_anchor)
    self.friction_calls += 1
    if self.friction_calls != 1 or not finite(baseline):
      raise ValueError('actual friction stage')
    # All canonical friction controls use actual threshold/deadzone. No invented31st gain.
    return baseline

  def selected_deadzone(self, speed, baseline_accel, accel_per_degree, friction_accel, requested_accel, *, original_anchor):
    self._check(original_anchor)
    self.deadzone_calls += 1
    if (
      self.deadzone_calls != 1
      or not all(finite(v) for v in (speed, baseline_accel, accel_per_degree, friction_accel, requested_accel))
      or baseline_accel < 0
      or accel_per_degree <= 0
    ):
      raise ValueError('actual selected VM/friction deadzone')
    if not any(self.values[n] for n in DEADBANDS):
      return baseline_accel
    raw = dict(self.surface.knobs)
    normalizer = abs(friction_accel) / accel_per_degree
    for n in DEADBANDS:
      low, high = dynamic_coordinate_bounds(n, normalizer)
      if not low <= self.values[n] <= high:
        raise ValueError('actual angular hardbound')
      raw[n] = self.values[n] * normalizer
    surface = self.math.GmSurface('torque_universal', raw)  # Exact existing angular hardbounds retained.
    extra_deg = self.math._gm_get_flm_full_surface_center_deadband_deg(surface, surface.profile, speed)
    delta = extra_deg * accel_per_degree
    if abs(delta) > 0.25 * abs(friction_accel) + 1e-12:
      raise ValueError('original friction-scaled deadzone envelope')
    return baseline_accel + delta

  def selected_output(self, speed, setpoint, desired_angle_deg, actual_angle_deg, baseline_torque, friction_torque, *, original_anchor):
    self._check(original_anchor)
    self.output_calls += 1
    if self.output_calls != 1 or not all(finite(v) for v in (speed, setpoint, desired_angle_deg, actual_angle_deg, baseline_torque, friction_torque)):
      raise ValueError('actual selected angle-assist stage')
    value = self.values['low_speed_angle_assist_max_torque']
    if value == 0 or speed < 0.1 * 0.44704:
      return baseline_torque
    # Additional automatic bound uses own selected torque/friction. Dom raw max
    # and source tracking/unwind gates remain unchanged, including its branch
    # discontinuity. Actual replay must reject a candidate failing this envelope.
    normalizer = max(abs(baseline_torque), abs(friction_torque))
    if normalizer == 0:
      return baseline_torque
    low, high = dynamic_coordinate_bounds('low_speed_angle_assist_max_torque', normalizer)
    if not low <= value <= high:
      raise ValueError('actual assist torque hardbound')
    raw = dict(self.surface.knobs)
    raw['low_speed_angle_assist_max_torque'] = value * normalizer
    surface = self.math.GmSurface('torque_universal', raw)
    # Dom passes its internal output_torque directly into this helper before the
    # final return-sign conversion. Common owner supplies that SAME policy sign.
    candidate = self.math._gm_get_flm_full_surface_low_speed_angle_assist_torque(
      surface, surface.profile, desired_angle_deg, actual_angle_deg, baseline_torque, speed
    )
    if not finite(candidate) or abs(candidate - baseline_torque) > 0.25 * normalizer + 1e-12:
      raise ValueError('actual angle-assist original effect envelope')
    return candidate

  def metadata(self):
    return (MANIFEST_SHA256, self.original_effect_anchor, self.full_profile_sha256, self.names)
