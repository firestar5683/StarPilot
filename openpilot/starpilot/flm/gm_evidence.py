"""Frozen Dom evidence classification and trial generation; no learner or Params writer."""
from dataclasses import dataclass
from typing import Any, TypedDict
import math
import numpy as np
from openpilot.starpilot.flm.gm_recommend import (FLM_FRICTION_SPEED_KNOTS, get_flm_supported_vehicle_knobs,
  get_gm_base_friction_threshold, get_standard_friction_threshold, get_hkg_canfd_base_friction_threshold, normalize_flm_overrides)
class GenericParamMetadata(TypedDict):
  min: float
  max: float
  precision: float
  deltaType: str
  safeLiveTrial: bool


GENERIC_PARAM_METADATA: dict[str, GenericParamMetadata] = {
  "SteerDelay": {"min": 0.01, "max": 1.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "SteerFriction": {"min": 0.0, "max": 1.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "SteerKP": {"min": 0.1, "max": 1.5, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "SteerLatAccel": {"min": 0.5, "max": 5.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "SteerRatio": {"min": 5.0, "max": 25.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
}

FLM_PATH_SPECS = {
  "baseline_fix": {
    "title": "Baseline Fix",
    "description": "Use the broad knobs first to get the car into the right zip code before touching narrower cleanup layers.",
    "whenToUse": "Use this when the car is broadly wrong: repeated line riding, multi-band under/oversteer, saturation, or obvious whole-car mismatch.",
    "alternateHint": "If the car is already mostly good and only one band is bothering you, switch to Cleanup Pass instead.",
  },
  "cleanup_pass": {
    "title": "Cleanup Pass",
    "description": "Use the narrow band-specific knobs first so you can clean up one behavior without disturbing the rest of the tune.",
    "whenToUse": "Use this when the car is already mostly in the right zip code and the misses are localized to one phase or speed band.",
    "alternateHint": "If the car is still broadly wrong after this, step back and run Baseline Fix first.",
  },
}

FLM_DRIVER_OVERRIDE_PRE_BUFFER_S = 0.35

FLM_DRIVER_OVERRIDE_POST_BUFFER_S = 1.0

FLM_CHATTER_FRICTION_DELTAS = {
  "low": [0.012, 0.020, 0.008, 0.0, 0.0],
  "mid": [0.0, 0.012, 0.020, 0.008, 0.0],
  "fast": [0.0, 0.0, 0.010, 0.020, 0.010],
  "highway": [0.0, 0.0, 0.0, 0.012, 0.025],
  "mixed": [0.0, 0.010, 0.018, 0.022, 0.025],
}

FLM_CHATTER_DEADBAND_SUFFIX = {
  "low": "center_deadband_low_deg",
  "mid": "center_deadband_mid_deg",
  "fast": "center_deadband_fast_deg",
  "highway": "center_deadband_highway_deg",
  "mixed": "center_deadband_mid_deg",
}

FLM_CHATTER_DEADBAND_DELTA = {
  "low": 0.035,
  "mid": 0.025,
  "fast": 0.018,
  "highway": 0.012,
  "mixed": 0.020,
}

FLM_CHATTER_THRESHOLD_PASS_MIN_DELTA = 0.012

@dataclass(slots=True)
class FLMSample:
  route: str
  segment: int
  t: float
  v_ego: float
  lat_active: bool
  steering_pressed: bool
  saturated: bool
  actual_la: float
  desired_la: float
  desired_jerk: float
  error: float | None
  error_rate: float | None
  p: float | None
  i: float | None
  d: float | None
  f: float | None
  output: float
  steering_angle_deg: float
  steering_torque: float | None
  cmd_torque: float | None
  out_torque: float | None
  roll_deg: float | None


def _speed_band_label(v_ego: float) -> str:
  if v_ego < 6.0:
    return "low"
  if v_ego < 15.0:
    return "mid"
  if v_ego < 25.0:
    return "fast"
  return "highway"


def _route_label(route: str, segment: int) -> str:
  return f"{route}/{segment}"


def _event_direction(samples: list[FLMSample]) -> str:
  mean_desired = float(np.mean([sample.desired_la for sample in samples]))
  if mean_desired > 0.02:
    return "left"
  if mean_desired < -0.02:
    return "right"
  return "center"


def _group_masked_events(samples: list[FLMSample], mask: list[bool], score_series: list[float], min_points: int = 5) -> list[dict[str, Any]]:
  events: list[dict[str, Any]] = []
  start_idx = None
  for idx, active in enumerate(mask + [False]):
    if active and start_idx is None:
      start_idx = idx
      continue
    if active:
      continue
    if start_idx is None:
      continue
    end_idx = idx - 1
    event_samples = samples[start_idx:end_idx + 1]
    if len(event_samples) >= min_points:
      event_scores = score_series[start_idx:end_idx + 1]
      peak_offset = int(np.argmax(event_scores))
      peak_idx = start_idx + peak_offset
      peak_sample = samples[peak_idx]
      direction = _event_direction(event_samples)
      events.append({
        "startIdx": start_idx,
        "endIdx": end_idx,
        "peakIdx": peak_idx,
        "peakScore": float(event_scores[peak_offset]),
        "route": peak_sample.route,
        "segment": peak_sample.segment,
        "speedBand": _speed_band_label(float(np.mean([sample.v_ego for sample in event_samples]))),
        "direction": direction,
        "supportCount": len(event_samples),
      })
    start_idx = None
  return events


def _analysis_eligibility_mask(samples: list[FLMSample]) -> list[bool]:
  eligible = [bool(sample.lat_active) for sample in samples]
  group_start = 0
  while group_start < len(samples):
    group_key = (samples[group_start].route, samples[group_start].segment)
    group_end = group_start + 1
    while group_end < len(samples) and (samples[group_end].route, samples[group_end].segment) == group_key:
      group_end += 1

    last_override = -math.inf
    for idx in range(group_start, group_end):
      sample = samples[idx]
      if sample.steering_pressed:
        last_override = sample.t
      if sample.steering_pressed or (sample.t - last_override) <= FLM_DRIVER_OVERRIDE_POST_BUFFER_S:
        eligible[idx] = False

    next_override = math.inf
    for idx in range(group_end - 1, group_start - 1, -1):
      sample = samples[idx]
      if sample.steering_pressed:
        next_override = sample.t
      if sample.steering_pressed or (next_override - sample.t) <= FLM_DRIVER_OVERRIDE_PRE_BUFFER_S:
        eligible[idx] = False

    # Force an event boundary between route segments even when lateral control stays active.
    eligible[group_start] = False
    eligible[group_end - 1] = False
    group_start = group_end

  return eligible


def _build_plot_data(samples: list[FLMSample], event: dict[str, Any], eligibility: list[bool] | None = None) -> dict[str, Any]:
  start_idx = int(event["startIdx"])
  end_idx = int(event["endIdx"])
  event_route = samples[start_idx].route
  event_segment = samples[start_idx].segment

  # Add a small amount of context without crossing an intervention buffer or
  # segment boundary. The highlighted region remains the classified event.
  for _ in range(12):
    candidate = start_idx - 1
    if candidate < 0 or (eligibility is not None and not eligibility[candidate]):
      break
    if samples[candidate].route != event_route or samples[candidate].segment != event_segment:
      break
    start_idx = candidate
  for _ in range(12):
    candidate = end_idx + 1
    if candidate >= len(samples) or (eligibility is not None and not eligibility[candidate]):
      break
    if samples[candidate].route != event_route or samples[candidate].segment != event_segment:
      break
    end_idx = candidate

  window = samples[start_idx:end_idx + 1]
  if len(window) < 2:
    return {}

  # Keep reports lightweight on unusually long windows while preserving both ends.
  if len(window) > 160:
    indices = np.linspace(0, len(window) - 1, 160, dtype=int)
    window = [window[int(idx)] for idx in indices]

  times = np.array([sample.t for sample in window], dtype=float)
  desired = np.array([sample.desired_la for sample in window], dtype=float)
  actual = np.array([sample.actual_la for sample in window], dtype=float)
  relative_times = times - float(times[0])
  event_start_time = max(float(samples[int(event["startIdx"])].t - times[0]), 0.0)
  event_end_time = max(float(samples[int(event["endIdx"])].t - times[0]), event_start_time)

  return {
    "times": [round(float(value), 3) for value in relative_times],
    "desired": [round(float(value), 4) for value in desired],
    "actual": [round(float(value), 4) for value in actual],
    "windowDurationSec": round(float(relative_times[-1]), 2),
    "eventStartSec": round(event_start_time, 2),
    "eventEndSec": round(event_end_time, 2),
    "eventDurationSec": round(max(event_end_time - event_start_time, 0.0), 2),
    "meanSpeedMph": round(float(np.mean([sample.v_ego for sample in window])) * 2.236936, 1),
    "route": event_route,
    "segment": event_segment,
    "segmentLabel": _route_label(event_route, event_segment),
    "direction": str(event.get("direction", "center")),
    "speedBand": str(event.get("speedBand", "mixed")),
    "driverOverrideFree": bool(eligibility is None or all(eligibility[start_idx:end_idx + 1])),
  }


def _build_plot_svg(plot_data: dict[str, Any]) -> str:
  times = np.array(plot_data.get("times", []), dtype=float)
  desired = np.array(plot_data.get("desired", []), dtype=float)
  actual = np.array(plot_data.get("actual", []), dtype=float)
  if len(times) < 2 or len(desired) != len(times) or len(actual) != len(times):
    return ""

  time_span = max(float(times.max()), 1e-3)
  y_min = float(min(np.min(desired), np.min(actual)))
  y_max = float(max(np.max(desired), np.max(actual)))
  y_pad = max((y_max - y_min) * 0.10, 0.1)
  y_min -= y_pad
  y_max += y_pad
  y_span = max(y_max - y_min, 1e-3)

  def _points(series):
    coords = []
    for t_val, y_val in zip(times, series, strict=True):
      x = (float(t_val) / time_span) * 380.0
      y = 120.0 - (((float(y_val) - y_min) / y_span) * 120.0)
      coords.append(f"{x:.1f},{y:.1f}")
    return " ".join(coords)

  return (
    "<svg viewBox='0 0 380 140' class='flm-plot' preserveAspectRatio='none'>" +
    "<rect x='0' y='0' width='380' height='140' rx='8' ry='8' fill='#0f172a'/>" +
    "<line x1='0' y1='120' x2='380' y2='120' stroke='#334155' stroke-width='1'/>" +
    f"<polyline fill='none' stroke='#ef4444' stroke-width='2' points='{_points(desired)}'/>" +
    f"<polyline fill='none' stroke='#38bdf8' stroke-width='2' points='{_points(actual)}'/>" +
    "</svg>"
  )


def _baseline_family_curve(family: str) -> list[float]:
  getter = {
    "gm": get_gm_base_friction_threshold,
    "standard": get_standard_friction_threshold,
    "hkg_canfd": get_hkg_canfd_base_friction_threshold,
  }.get(family, get_standard_friction_threshold)
  return [round(float(getter(knot)), 4) for knot in FLM_FRICTION_SPEED_KNOTS]


def _current_family_curve(family: str, current: dict[str, Any]) -> list[float]:
  active_overrides = current.get("FLMActiveOverrides", {}) if isinstance(current, dict) else {}
  payload = active_overrides.get("baseFrictionThresholds", {}).get(family, {}) if isinstance(active_overrides, dict) else {}
  values = payload.get("values", []) if isinstance(payload, dict) else []
  if isinstance(values, list) and len(values) == len(FLM_FRICTION_SPEED_KNOTS):
    try:
      return [round(float(value), 4) for value in values]
    except Exception:
      pass
  return _baseline_family_curve(family)


def _center_chatter_friction_adjustment(family: str, speed_band: str, severity: float,
                                        current: dict[str, Any]) -> dict[str, Any]:
  current_curve = _current_family_curve(family, current)
  deltas = FLM_CHATTER_FRICTION_DELTAS.get(speed_band, FLM_CHATTER_FRICTION_DELTAS["mixed"])
  scale = min(max(severity, 0.45), 1.2)
  suggested = [round(current_curve[idx] + (delta * scale), 4) for idx, delta in enumerate(deltas)]
  return {
    "type": "friction_curve",
    "symbol": f"base_friction_threshold.{family}",
    "family": family,
    "current": current_curve,
    "suggested": suggested,
    "delta": [round(suggested[idx] - current_curve[idx], 4) for idx in range(len(current_curve))],
    "stage": "friction_threshold",
    "speedBand": speed_band,
  }


def _center_chatter_threshold_pass_applied(family: str, speed_band: str, current: dict[str, Any]) -> bool:
  baseline = _baseline_family_curve(family)
  active = _current_family_curve(family, current)
  target_indexes = {
    "low": (0, 1),
    "mid": (1, 2),
    "fast": (2, 3),
    "highway": (3, 4),
    "mixed": tuple(range(len(FLM_FRICTION_SPEED_KNOTS))),
  }.get(speed_band, tuple(range(len(FLM_FRICTION_SPEED_KNOTS))))
  return max((active[idx] - baseline[idx] for idx in target_indexes), default=0.0) >= FLM_CHATTER_THRESHOLD_PASS_MIN_DELTA


def _center_chatter_deadband_adjustment(capabilities: dict[str, Any], speed_band: str, severity: float,
                                        current: dict[str, Any]) -> dict[str, Any] | None:
  rich_profile = capabilities.get("richProfileKey")
  suffix = FLM_CHATTER_DEADBAND_SUFFIX.get(speed_band, FLM_CHATTER_DEADBAND_SUFFIX["mixed"])
  if not rich_profile or not _rich_profile_supports_knob(capabilities, suffix):
    return None
  adjustment = _vehicle_knob_adjustment(
    f"{rich_profile}.{suffix}",
    FLM_CHATTER_DEADBAND_DELTA.get(speed_band, FLM_CHATTER_DEADBAND_DELTA["mixed"]) * min(max(severity, 0.5), 1.2),
    current,
  )
  if adjustment is not None:
    adjustment["stage"] = "center_deadband"
    adjustment["speedBand"] = speed_band
  return adjustment


def _direction_reversal_count(values: np.ndarray, min_step: float) -> int:
  if len(values) < 3:
    return 0
  deltas = np.diff(values)
  significant = deltas[np.abs(deltas) >= min_step]
  if len(significant) < 2:
    return 0
  return int(np.sum(np.sign(significant[1:]) != np.sign(significant[:-1])))


def _clamp(value: float, lower: float, upper: float) -> float:
  return min(max(float(value), lower), upper)


def _round_to_precision(value: float, precision: float) -> float:
  if precision <= 0:
    return float(value)
  steps = round(float(value) / precision)
  return round(steps * precision, 6)


def _current_vehicle_knob_value(symbol: str, current: dict[str, Any]) -> float | None:
  knob = get_flm_supported_vehicle_knobs().get(symbol)
  if knob is None:
    return None

  active_overrides = current.get("FLMActiveOverrides", {}) if isinstance(current, dict) else {}
  vehicle_knobs = active_overrides.get("vehicleKnobs", {}) if isinstance(active_overrides, dict) else {}
  try:
    return float(vehicle_knobs.get(symbol, knob["defaultValue"]))
  except Exception:
    return float(knob["defaultValue"])


def _vehicle_knob_adjustment(symbol: str, delta: float, current: dict[str, Any] | None = None) -> dict[str, Any] | None:
  knob = get_flm_supported_vehicle_knobs().get(symbol)
  if knob is None:
    return None
  current_value = _current_vehicle_knob_value(symbol, current or {})
  if current_value is None:
    return None
  suggested_value = _round_to_precision(_clamp(current_value + delta, knob["min"], knob["max"]), knob["precision"])
  if math.isclose(current_value, suggested_value, abs_tol=max(float(knob["precision"]) / 2.0, 1e-6)):
    return None
  return {
    "type": "vehicle_knob",
    "symbol": symbol,
    "current": current_value,
    "suggested": suggested_value,
    "delta": round(suggested_value - current_value, 4),
  }


def _rich_profile_supports_knob(capabilities: dict[str, Any], suffix: str) -> bool:
  rich_profile = capabilities.get("richProfileKey")
  if not rich_profile:
    return False
  return f"{rich_profile}.{suffix}" in get_flm_supported_vehicle_knobs()


def _build_event_summaries(samples: list[FLMSample]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
  eligibility = _analysis_eligibility_mask(samples)
  active_samples = [sample for sample, allowed in zip(samples, eligibility, strict=True) if allowed]
  if not active_samples:
    return [], {"sampleCount": 0}

  over_error = [abs(sample.actual_la) - abs(sample.desired_la) for sample in samples]
  desired = [sample.desired_la for sample in samples]
  jerk = [sample.desired_jerk for sample in samples]
  angle = [sample.steering_angle_deg for sample in active_samples]
  output = [sample.output for sample in active_samples]

  entry_phase = [(abs(d) > 0.30 and abs(j) > 0.25 and d * j > 0.0) for d, j in zip(desired, jerk, strict=True)]
  unwind_phase = [(abs(d) > 0.25 and abs(j) > 0.20 and d * j < 0.0) for d, j in zip(desired, jerk, strict=True)]
  steady_curve_phase = [(abs(d) > 0.35 and abs(j) < 0.18) for d, j in zip(desired, jerk, strict=True)]
  saturation_phase = [
    bool(allowed and sample.saturated and abs(sample.desired_la) > 0.30 and (abs(sample.desired_jerk) > 0.16 or abs(sample.actual_la) > 0.45))
    for sample, allowed in zip(samples, eligibility, strict=True)
  ]

  base_masks = {
    "understeer": [(allowed and phase and (ov < -0.20)) for allowed, phase, ov in zip(eligibility, steady_curve_phase, over_error, strict=True)],
    "oversteer": [(allowed and phase and (ov > 0.20)) for allowed, phase, ov in zip(eligibility, steady_curve_phase, over_error, strict=True)],
    "late_turn_in": [(allowed and phase and ov < -0.16) for allowed, phase, ov in zip(eligibility, entry_phase, over_error, strict=True)],
    "early_turn_in": [(allowed and phase and ov > 0.16) for allowed, phase, ov in zip(eligibility, entry_phase, over_error, strict=True)],
    "unwind_too_slow": [(allowed and phase and ov > 0.14) for allowed, phase, ov in zip(eligibility, unwind_phase, over_error, strict=True)],
    "unwind_too_fast": [(allowed and phase and ov < -0.14) for allowed, phase, ov in zip(eligibility, unwind_phase, over_error, strict=True)],
    "low_speed_unwillingness": [
      bool(allowed and sample.v_ego < 6.0 and abs(sample.desired_la) > 0.30 and abs(sample.desired_jerk) > 0.18 and
           (abs(sample.actual_la) + 0.18) < abs(sample.desired_la))
      for sample, allowed in zip(samples, eligibility, strict=True)
    ],
    "saturation_limited": saturation_phase,
  }
  score_map = {
    "understeer": [max((-ov), 0.0) for ov in over_error],
    "oversteer": [max(ov, 0.0) for ov in over_error],
    "late_turn_in": [max((-ov), 0.0) + abs(j) * 0.1 for ov, j in zip(over_error, jerk, strict=True)],
    "early_turn_in": [max(ov, 0.0) + abs(j) * 0.1 for ov, j in zip(over_error, jerk, strict=True)],
    "unwind_too_slow": [max(ov, 0.0) for ov in over_error],
    "unwind_too_fast": [max((-ov), 0.0) for ov in over_error],
    "low_speed_unwillingness": [max(abs(d) - abs(sample.actual_la), 0.0) for d, sample in zip(desired, samples, strict=True)],
    "saturation_limited": [1.0 if sample.saturated else 0.0 for sample in samples],
  }

  # Detect controller-driven center chatter independently in each speed band.
  # The desired path must remain calm while steering angle and either output or
  # tracking error repeatedly reverse direction.
  straight_windows = []
  angle_thresholds = {"low": 0.80, "mid": 0.55, "fast": 0.38, "highway": 0.28}
  error_thresholds = {"low": 0.16, "mid": 0.12, "fast": 0.09, "highway": 0.07}
  output_thresholds = {"low": 0.055, "mid": 0.045, "fast": 0.035, "highway": 0.025}
  for start_idx in range(0, max(len(samples) - 20, 1), 10):
    window = samples[start_idx:start_idx + 40]
    if len(window) < 20:
      continue
    if not all(eligibility[start_idx:start_idx + len(window)]):
      continue
    mean_speed = float(np.mean([sample.v_ego for sample in window]))
    if mean_speed < 2.0:
      continue
    speed_band = _speed_band_label(mean_speed)
    desired_series = np.array([sample.desired_la for sample in window])
    if float(np.mean(np.abs(desired_series))) > (0.14 if speed_band == "low" else 0.18):
      continue
    desired_span = float(np.ptp(desired_series))
    desired_reversals = _direction_reversal_count(desired_series, 0.008)
    if desired_span > 0.18 or desired_reversals > 3:
      continue

    angle_series = np.array([sample.steering_angle_deg for sample in window])
    angle_trend = np.linspace(angle_series[0], angle_series[-1], len(angle_series))
    centered_angles = angle_series - angle_trend
    error_series = np.array([sample.actual_la - sample.desired_la for sample in window])
    output_series = np.array([sample.output for sample in window])
    angle_p2p = float(np.ptp(centered_angles))
    error_p2p = float(np.ptp(error_series))
    output_p2p = float(np.ptp(output_series))
    angle_reversals = _direction_reversal_count(centered_angles, max(angle_thresholds[speed_band] * 0.08, 0.025))
    error_reversals = _direction_reversal_count(error_series, max(error_thresholds[speed_band] * 0.08, 0.006))
    output_reversals = _direction_reversal_count(output_series, max(output_thresholds[speed_band] * 0.08, 0.002))
    angle_evidence = angle_p2p >= angle_thresholds[speed_band] and angle_reversals >= 3
    error_evidence = error_p2p >= error_thresholds[speed_band] and error_reversals >= 3
    output_evidence = output_p2p >= output_thresholds[speed_band] and output_reversals >= 3
    if angle_evidence and (error_evidence or output_evidence):
      chatter_score = min(1.5, (
        0.30 * (angle_p2p / angle_thresholds[speed_band]) +
        0.18 * (error_p2p / error_thresholds[speed_band]) +
        0.18 * (output_p2p / output_thresholds[speed_band]) +
        0.025 * min(angle_reversals + error_reversals + output_reversals, 14)
      ))
      straight_windows.append({
        "startIdx": start_idx,
        "endIdx": start_idx + len(window) - 1,
        "peakIdx": start_idx + int(len(window) / 2),
        "peakScore": chatter_score,
        "route": window[0].route,
        "segment": window[0].segment,
        "speedBand": speed_band,
        "direction": "center",
        "supportCount": len(window),
        "metrics": {
          "meanSpeedMps": round(mean_speed, 3),
          "steeringAngleP2P": round(angle_p2p, 4),
          "trackingErrorP2P": round(error_p2p, 4),
          "outputP2P": round(output_p2p, 4),
          "steeringReversals": angle_reversals,
          "trackingErrorReversals": error_reversals,
          "outputReversals": output_reversals,
          "desiredP2P": round(desired_span, 4),
          "desiredReversals": desired_reversals,
        },
      })

  curve_windows = []
  for start_idx in range(0, max(len(samples) - 20, 1), 8):
    window = samples[start_idx:start_idx + 36]
    if len(window) < 18:
      continue
    if not all(eligibility[start_idx:start_idx + len(window)]):
      continue
    if float(np.mean([sample.v_ego for sample in window])) < 15.0:
      continue
    desired_sign = float(np.mean([sample.desired_la for sample in window]))
    if abs(desired_sign) < 0.35:
      continue
    if any((sample.desired_la * desired_sign) < 0.0 for sample in window):
      continue
    error_series = np.array([sample.actual_la - sample.desired_la for sample in window])
    sign_changes = int(np.sum(np.sign(error_series[1:]) != np.sign(error_series[:-1])))
    amplitude = float(np.max(error_series) - np.min(error_series))
    if amplitude > 0.22 and sign_changes >= 4:
      curve_windows.append({
        "startIdx": start_idx,
        "endIdx": start_idx + len(window) - 1,
        "peakIdx": start_idx + int(np.argmax(np.abs(error_series))),
        "peakScore": amplitude + sign_changes * 0.03,
        "route": window[0].route,
        "segment": window[0].segment,
        "speedBand": _speed_band_label(float(np.mean([sample.v_ego for sample in window]))),
        "direction": "left" if desired_sign > 0.0 else "right",
        "supportCount": len(window),
      })

  summaries: list[dict[str, Any]] = []
  for bucket, mask in base_masks.items():
    events = _group_masked_events(samples, mask, score_map[bucket])
    if events:
      summaries.extend(_summaries_from_events(bucket, samples, events, eligibility))
  if straight_windows:
    summaries.extend(_summaries_from_events("center_chatter", samples, straight_windows, eligibility))
  if curve_windows:
    summaries.extend(_summaries_from_events("notchy_mid_curve", samples, curve_windows, eligibility))

  left_errors = [abs(sample.actual_la) - abs(sample.desired_la) for sample in active_samples if sample.desired_la > 0.25]
  right_errors = [abs(sample.actual_la) - abs(sample.desired_la) for sample in active_samples if sample.desired_la < -0.25]
  summary_stats = {
    "sampleCount": len(active_samples),
    "excludedDriverOverrideSamples": sum(1 for sample, allowed in zip(samples, eligibility, strict=True) if sample.lat_active and not allowed),
    "qlogFallback": False,
    "meanDesiredAbs": round(float(np.mean(np.abs([sample.desired_la for sample in active_samples]))), 4),
    "meanErrorAbs": round(float(np.mean(np.abs([sample.actual_la - sample.desired_la for sample in active_samples]))), 4),
    "leftBias": round(float(np.mean(left_errors)), 4) if left_errors else 0.0,
    "rightBias": round(float(np.mean(right_errors)), 4) if right_errors else 0.0,
    "highwayStraightAngleP2P": round(float(np.percentile(np.abs(angle), 95) - np.percentile(np.abs(angle), 5)), 4) if angle else 0.0,
    "meanOutputAbs": round(float(np.mean(np.abs(output))), 4) if output else 0.0,
  }

  if summary_stats["meanErrorAbs"] < 0.08 and not any(summary["severity"] > 0.65 for summary in summaries):
    summaries.append({
      "bucket": "model_limited",
      "dimensionId": "model_limited:overall",
      "direction": "center",
      "speedBand": "mixed",
      "count": 1,
      "severity": 0.25,
      "evidence": {
        "speedBand": "mixed",
        "directionBias": "center",
        "eventCount": 1,
        "segments": [],
      },
      "events": [],
      "plotSvg": "",
      "plotData": {},
    })

  return sorted(summaries, key=lambda item: item["severity"], reverse=True), summary_stats


def _summaries_from_events(bucket: str, samples: list[FLMSample], events: list[dict[str, Any]],
                           eligibility: list[bool] | None = None) -> list[dict[str, Any]]:
  grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
  for event in events:
    event_speed_band = event["speedBand"] if bucket == "center_chatter" else "mixed"
    key = (bucket, event["direction"], event_speed_band)
    grouped.setdefault(key, []).append(event)

  summaries = []
  for (bucket_name, direction, _group_speed_band), grouped_events in grouped.items():
    grouped_events.sort(key=lambda item: item["peakScore"], reverse=True)
    strongest = grouped_events[:3]
    strongest_labels = [
      {
        "route": event["route"],
        "segment": event["segment"],
        "label": _route_label(event["route"], event["segment"]),
        "score": round(float(event["peakScore"]), 3),
      }
      for event in strongest
    ]
    top_event = strongest[0]
    top_speed_band = top_event["speedBand"]
    plot_data = _build_plot_data(samples, top_event, eligibility)
    summaries.append({
      "bucket": bucket_name,
      "dimensionId": f"{bucket_name}:{direction}:{top_speed_band}",
      "direction": direction,
      "speedBand": top_speed_band,
      "count": len(grouped_events),
      "severity": round(float(min(1.5, np.mean([event["peakScore"] for event in strongest]))), 3),
      "evidence": {
        "speedBand": top_speed_band,
        "directionBias": direction,
        "eventCount": len(grouped_events),
        "segments": strongest_labels,
        "chatterMetrics": top_event.get("metrics", {}),
      },
      "events": grouped_events,
      "plotSvg": _build_plot_svg(plot_data),
      "plotData": plot_data,
    })
  return summaries


def _primary_delta_from_summary(summary: dict[str, Any], capabilities: dict[str, Any], current: dict[str, Any],
                                strategy: str = "cleanup") -> dict[str, Any] | None:
  bucket = summary["bucket"]
  direction = summary["direction"]
  severity = max(float(summary["severity"]), 0.2)
  speed_band = str(summary.get("speedBand", "mixed"))
  rich_profile = capabilities.get("richProfileKey")
  family = capabilities.get("frictionFamily", "standard")
  side = "left" if direction != "right" else "right"
  curvy_band = speed_band in ("mid", "fast")
  supports_low_speed_assist = _rich_profile_supports_knob(capabilities, "low_speed_angle_assist_max_torque")
  supports_crawl_turn_in = _rich_profile_supports_knob(capabilities, f"crawl_turn_in_ff_boost_{side}")
  supports_turn_in_boost = _rich_profile_supports_knob(capabilities, f"turn_in_boost_{side}")
  supports_unwind_taper = _rich_profile_supports_knob(capabilities, f"unwind_taper_{side}")
  supports_curvy_turn_in_trim = _rich_profile_supports_knob(capabilities, f"curvy_turn_in_trim_{side}")
  supports_curvy_turn_in_speed = _rich_profile_supports_knob(capabilities, "curvy_turn_in_trim_speed_max")
  supports_curvy_speed_max = _rich_profile_supports_knob(capabilities, "curvy_speed_max")
  supports_curvy_unwind_extra = _rich_profile_supports_knob(capabilities, f"curvy_unwind_extra_reduction_{side}")
  supports_curvy_unwind_floor = _rich_profile_supports_knob(capabilities, f"curvy_unwind_floor_relief_{side}")
  supports_ff_gain = _rich_profile_supports_knob(capabilities, f"ff_gain_{side}")
  nonlinear_map = capabilities.get("nonlinearTorqueMap", {})
  asymmetric_nonlinear_map = bool(isinstance(nonlinear_map, dict) and nonlinear_map.get("asymmetric"))

  if bucket == "model_limited":
    return None

  if strategy == "baseline":
    if bucket == "center_chatter":
      return _center_chatter_friction_adjustment(family, speed_band, severity, current)

    if bucket == "notchy_mid_curve":
      current_curve = _current_family_curve(family, current)
      deltas = [0.0, 0.0, 0.015, 0.02, 0.02]
      scale = min(max(severity, 0.4), 1.2)
      suggested = [round(current_curve[idx] + (delta * scale), 4) for idx, delta in enumerate(deltas)]
      return {
        "type": "friction_curve",
        "symbol": f"base_friction_threshold.{family}",
        "family": family,
        "current": current_curve,
        "suggested": suggested,
        "delta": [round(suggested[idx] - current_curve[idx], 4) for idx in range(len(current_curve))],
      }

    if bucket == "low_speed_unwillingness":
      current_curve = _current_family_curve(family, current)
      deltas = [-0.03, -0.025, -0.015, -0.005, 0.0]
      scale = min(max(severity, 0.5), 1.2)
      suggested = [round(max(0.05, current_curve[idx] + (delta * scale)), 4) for idx, delta in enumerate(deltas)]
      return {
        "type": "friction_curve",
        "symbol": f"base_friction_threshold.{family}",
        "family": family,
        "current": current_curve,
        "suggested": suggested,
        "delta": [round(suggested[idx] - current_curve[idx], 4) for idx in range(len(current_curve))],
      }

    if bucket in ("understeer", "late_turn_in", "saturation_limited"):
      if asymmetric_nonlinear_map and direction in ("left", "right") and supports_ff_gain:
        adjustment = _vehicle_knob_adjustment(f"{rich_profile}.ff_gain_{side}", 0.025 * severity, current)
        if adjustment is not None:
          return adjustment
      current_value = float(current["SteerLatAccel"])
      scale = 0.04 if bucket == "saturation_limited" else 0.03
      suggested_value = round(_clamp(current_value + max(scale, current_value * scale * severity), 0.5, 5.0), 4)
      return {"type": "generic_param", "paramKey": "SteerLatAccel",
              "current": current_value, "suggested": suggested_value, "delta": round(suggested_value - current_value, 4)}

    if bucket in ("oversteer", "early_turn_in"):
      if asymmetric_nonlinear_map and direction in ("left", "right") and supports_ff_gain:
        adjustment = _vehicle_knob_adjustment(f"{rich_profile}.ff_gain_{side}", -0.025 * severity, current)
        if adjustment is not None:
          return adjustment
      current_value = float(current["SteerLatAccel"])
      suggested_value = round(_clamp(current_value - max(0.03, current_value * 0.03 * severity), 0.5, 5.0), 4)
      return {"type": "generic_param", "paramKey": "SteerLatAccel",
              "current": current_value, "suggested": suggested_value, "delta": round(suggested_value - current_value, 4)}

    if bucket in ("unwind_too_slow", "unwind_too_fast"):
      current_value = float(current["SteerFriction"])
      direction_mult = -1.0 if bucket == "unwind_too_slow" else 1.0
      suggested_value = round(_clamp(current_value + (0.015 * severity * direction_mult), 0.0, 1.0), 4)
      return {"type": "generic_param", "paramKey": "SteerFriction",
              "current": current_value, "suggested": suggested_value, "delta": round(suggested_value - current_value, 4)}

  if bucket == "center_chatter":
    if _center_chatter_threshold_pass_applied(family, speed_band, current):
      deadband_adjustment = _center_chatter_deadband_adjustment(capabilities, speed_band, severity, current)
      if deadband_adjustment is not None:
        return deadband_adjustment
    return _center_chatter_friction_adjustment(family, speed_band, severity, current)

  if bucket == "notchy_mid_curve":
    current_curve = _current_family_curve(family, current)
    deltas = [0.0, 0.0, 0.015, 0.02, 0.02]
    scale = min(max(severity, 0.4), 1.2)
    suggested = [round(current_curve[idx] + (delta * scale), 4) for idx, delta in enumerate(deltas)]
    return {
      "type": "friction_curve",
      "symbol": f"base_friction_threshold.{family}",
      "family": family,
      "current": current_curve,
      "suggested": suggested,
      "delta": [round(suggested[idx] - current_curve[idx], 4) for idx in range(len(current_curve))],
    }

  if bucket == "low_speed_unwillingness":
    current_curve = _current_family_curve(family, current)
    deltas = [-0.03, -0.025, -0.015, -0.005, 0.0]
    scale = min(max(severity, 0.5), 1.2)
    if supports_low_speed_assist:
      adjustment = _vehicle_knob_adjustment(f"{rich_profile}.low_speed_angle_assist_max_torque", 0.04 * scale, current)
      if adjustment is not None:
        return adjustment
    if supports_crawl_turn_in:
      adjustment = _vehicle_knob_adjustment(f"{rich_profile}.crawl_turn_in_ff_boost_{side}", 0.03 * scale, current)
      if adjustment is not None:
        return adjustment
    if rich_profile and supports_turn_in_boost:
      adjustment = _vehicle_knob_adjustment(f"{rich_profile}.turn_in_boost_{side}", 0.025 * scale, current)
      if adjustment is not None:
        return adjustment
    suggested = [round(max(0.05, current_curve[idx] + (delta * scale)), 4) for idx, delta in enumerate(deltas)]
    return {
      "type": "friction_curve",
      "symbol": f"base_friction_threshold.{family}",
      "family": family,
      "current": current_curve,
      "suggested": suggested,
      "delta": [round(suggested[idx] - current_curve[idx], 4) for idx in range(len(current_curve))],
    }

  if bucket in ("understeer", "late_turn_in"):
    if bucket == "understeer" and asymmetric_nonlinear_map and direction in ("left", "right") and supports_ff_gain:
      adjustment = _vehicle_knob_adjustment(f"{rich_profile}.ff_gain_{side}", 0.025 * severity, current)
      if adjustment is not None:
        return adjustment
    if curvy_band and speed_band == "fast" and bucket == "late_turn_in" and supports_curvy_turn_in_speed:
      adjustment = _vehicle_knob_adjustment(f"{rich_profile}.curvy_turn_in_trim_speed_max", 1.6 * severity, current)
      if adjustment is not None:
        return adjustment
    if curvy_band and supports_curvy_turn_in_trim:
      adjustment = _vehicle_knob_adjustment(f"{rich_profile}.curvy_turn_in_trim_{side}", -0.018 * severity, current)
      if adjustment is not None:
        return adjustment
    if rich_profile and supports_turn_in_boost:
      adjustment = _vehicle_knob_adjustment(f"{rich_profile}.turn_in_boost_{side}", 0.02 * severity, current)
      if adjustment is not None:
        return adjustment
    current_value = float(current["SteerLatAccel"])
    suggested_value = round(_clamp(current_value + max(0.03, current_value * 0.03 * severity), 0.5, 5.0), 4)
    return {"type": "generic_param", "paramKey": "SteerLatAccel",
              "current": current_value, "suggested": suggested_value, "delta": round(suggested_value - current_value, 4)}

  if bucket in ("oversteer", "early_turn_in"):
    if bucket == "oversteer" and asymmetric_nonlinear_map and direction in ("left", "right") and supports_ff_gain:
      adjustment = _vehicle_knob_adjustment(f"{rich_profile}.ff_gain_{side}", -0.025 * severity, current)
      if adjustment is not None:
        return adjustment
    if curvy_band and supports_curvy_turn_in_trim:
      adjustment = _vehicle_knob_adjustment(f"{rich_profile}.curvy_turn_in_trim_{side}", 0.018 * severity, current)
      if adjustment is not None:
        return adjustment
    if rich_profile and supports_turn_in_boost:
      adjustment = _vehicle_knob_adjustment(f"{rich_profile}.turn_in_boost_{side}", -0.02 * severity, current)
      if adjustment is not None:
        return adjustment
    current_value = float(current["SteerLatAccel"])
    suggested_value = round(_clamp(current_value - max(0.03, current_value * 0.03 * severity), 0.5, 5.0), 4)
    return {"type": "generic_param", "paramKey": "SteerLatAccel",
              "current": current_value, "suggested": suggested_value, "delta": round(suggested_value - current_value, 4)}

  if bucket in ("unwind_too_slow", "unwind_too_fast"):
    if curvy_band and supports_curvy_unwind_extra:
      if bucket == "unwind_too_slow" and speed_band == "fast" and supports_curvy_speed_max:
        adjustment = _vehicle_knob_adjustment(f"{rich_profile}.curvy_speed_max", 1.8 * severity, current)
        if adjustment is not None:
          return adjustment
      direction_mult = 1.0 if bucket == "unwind_too_slow" else -1.0
      adjustment = _vehicle_knob_adjustment(f"{rich_profile}.curvy_unwind_extra_reduction_{side}", 0.03 * severity * direction_mult, current)
      if adjustment is not None:
        return adjustment
    if rich_profile and supports_unwind_taper:
      direction_mult = 1.0 if bucket == "unwind_too_slow" else -1.0
      adjustment = _vehicle_knob_adjustment(f"{rich_profile}.unwind_taper_{side}", 0.08 * severity * direction_mult, current)
      if adjustment is not None:
        return adjustment
    current_value = float(current["SteerFriction"])
    direction_mult = -1.0 if bucket == "unwind_too_slow" else 1.0
    suggested_value = round(_clamp(current_value + (0.015 * severity * direction_mult), 0.0, 1.0), 4)
    return {"type": "generic_param", "paramKey": "SteerFriction",
              "current": current_value, "suggested": suggested_value, "delta": round(suggested_value - current_value, 4)}

  if bucket == "saturation_limited":
    if curvy_band and supports_curvy_unwind_floor:
      adjustment = _vehicle_knob_adjustment(f"{rich_profile}.curvy_unwind_floor_relief_{side}", 0.04 * severity, current)
      if adjustment is not None:
        return adjustment
    current_value = float(current["SteerLatAccel"])
    suggested_value = round(_clamp(current_value + max(0.04, current_value * 0.04 * severity), 0.5, 5.0), 4)
    return {"type": "generic_param", "paramKey": "SteerLatAccel",
              "current": current_value, "suggested": suggested_value, "delta": round(suggested_value - current_value, 4)}

  return None


def _observed_behavior(summary: dict[str, Any]) -> str:
  bucket = summary["bucket"]
  direction = summary["direction"]
  speed_band = summary["speedBand"]
  direction_text = "" if direction == "center" else f" on {direction} {speed_band} inputs"
  mapping = {
    "understeer": f"The car is not matching requested lateral accel{direction_text}; it stays wider than plan before recovery.",
    "oversteer": f"The car is exceeding requested lateral accel{direction_text}; it is stepping past plan before correcting back.",
    "late_turn_in": f"Turn-in is late{direction_text}; desired lateral accel is already building while actual response lags.",
    "early_turn_in": f"Turn-in is too eager{direction_text}; actual response jumps ahead of the plan during entry.",
    "unwind_too_slow": f"Unwind is hanging on too long{direction_text}; the car keeps steering after the plan starts releasing.",
    "unwind_too_fast": f"Unwind is releasing too quickly{direction_text}; the wheel gives back steering sooner than the plan wants.",
    "center_chatter": f"The car is doing repeated micro-corrections around center in the {speed_band} speed band while the requested path stays calm.",
    "notchy_mid_curve": "Mid-curve tracking is correcting in steps instead of flowing through the same steering band cleanly.",
    "low_speed_unwillingness": "At low speed the controller is slow to wake up even though the turn request is already there.",
    "saturation_limited": "The controller is spending meaningful time at or near its steering authority ceiling.",
    "model_limited": "The controller is largely matching the commanded path; this sample does not show a strong tuning mismatch.",
  }
  return mapping.get(bucket, "The controller is showing a repeatable mismatch against the requested path.")


def _likely_interpretation(summary: dict[str, Any], adjustment: dict[str, Any]) -> str:
  bucket = summary["bucket"]
  if adjustment["type"] == "friction_curve":
    if bucket == "low_speed_unwillingness":
      return "The near-center friction threshold is too high in the crawl-speed band, so small requests are being muted."
    return (
      'This looks more like a friction-threshold problem than a whole-tune problem; the ' +
      'controller is busy around center and needs a calmer deadzone slope.'
    )
  if adjustment["type"] == "vehicle_knob":
    symbol = adjustment["symbol"]
    if "center_deadband_" in symbol:
      return (
        "A friction-threshold pass is already active in this speed band, but controller-driven reversals remain. " +
        "The residual motion is narrow enough for a small deadband cleanup instead of another broad friction increase."
      )
    if "ff_gain_" in symbol:
      return (
        'This car has a directional nonlinear torque map, and the mismatch is concentrated on one ' +
        "side. Correct that side's feedforward layer before moving global authority."
      )
    if "low_speed_angle_assist_max_torque" in symbol:
      return "The main torque path is waking up too late below about 8 mph, so the low-speed assist layer needs a little more authority."
    if "crawl_turn_in_ff_boost" in symbol:
      return "The crawl-speed turn-in band is still too lazy, even before the broader tune needs to move."
    if "curvy_speed_max" in symbol:
      return "The curvy unwind band is dropping out too early at higher speed, so the curve-specific release cleanup is not staying active long enough."
    if "curvy_turn_in_trim_speed_max" in symbol:
      return "The fast-curve entry trim band is fading out too early, so the controller is falling back to the base path before the curve is done."
    if "curvy_turn_in_trim" in symbol:
      return "This is a curve-band entry problem, not a whole-car turn-in problem; the mid-speed trim needs to move without touching the rest of the tune."
    if "curvy_unwind" in symbol:
      return "This is a curve-band release problem, not a global unwind problem; the mid-speed unwind cleanup needs to move on its own."
  if bucket in ("understeer", "late_turn_in", "low_speed_unwillingness", "saturation_limited"):
    return "Primary turn-in authority is too low for the way this car is reacting in that band."
  if bucket in ("oversteer", "early_turn_in"):
    return "Entry authority is too aggressive for the speed band being hit here."
  if bucket == "unwind_too_slow":
    return "Exit steering is being held too long after the plan starts backing out of the curve."
  if bucket == "unwind_too_fast":
    return "Exit steering is tapering away too quickly once unwind starts."
  return "The mismatch is consistent enough to justify a direct tuning pass."


def _why_this_knob(adjustment: dict[str, Any]) -> str:
  if adjustment["type"] == "friction_curve":
    return "This changes the threshold that maps small lateral-accel error into friction compensation without pretending the whole torque slope is wrong."
  if adjustment["type"] == "vehicle_knob":
    symbol = adjustment["symbol"]
    if "center_deadband_" in symbol:
      return (
        "This adds a small steering-angle deadband only around the affected speed knot, interpolated into neighboring speeds, " +
        "without reducing normal curve authority."
      )
    if "ff_gain_" in symbol:
      return "This compensates the affected side without flattening the car's separate left/right nonlinear torque response into one global value."
    if "low_speed_angle_assist_max_torque" in symbol:
      return "This directly raises the crawl-speed assist ceiling that fills the gap before the normal torque path wakes up."
    if "crawl_turn_in_ff_boost" in symbol:
      return "This only touches the crawl-speed turn-in band instead of disturbing normal-speed behavior."
    if "curvy_speed_max" in symbol:
      return "This keeps the dedicated curvy unwind helper alive deeper into faster curves instead of globally changing the whole unwind map."
    if "curvy_turn_in_trim_speed_max" in symbol:
      return "This extends the fast-curve trim band instead of making the whole car more eager to turn everywhere."
    if "curvy_turn_in_trim" in symbol:
      return "This trims entry only in the dedicated curvy speed band instead of flattening turn-in everywhere."
    if "curvy_unwind" in symbol:
      return "This cleans up release only in the dedicated curvy speed band instead of changing global unwind behavior."
    if "turn_in_boost" in symbol:
      return "This targets entry behavior directly instead of disturbing the whole tune."
    if "unwind_taper" in symbol:
      return "This targets release behavior directly instead of flattening the whole response."
    if "threshold" in symbol:
      return "This adjusts the transition deadzone for the specific phase that is misbehaving."
    return "This is the closest car-specific knob to the symptom being shown."
  return "This is the smallest generic user-facing change that moves the car in the right direction without inventing a new code path."


def _render_adjustment_line(adjustment: dict[str, Any]) -> str:
  if adjustment["type"] == "friction_curve":
    curve = ", ".join(f"{value:.3f}" for value in adjustment["suggested"])
    return f"Adjust {adjustment['family']} friction threshold curve at {FLM_FRICTION_SPEED_KNOTS} m/s to [{curve}]."
  if adjustment["type"] == "vehicle_knob":
    suffix = " as the second-stage center-chatter cleanup." if adjustment.get("stage") == "center_deadband" else "."
    return f"Move `{adjustment['symbol']}` from {adjustment['current']:.3f} to {adjustment['suggested']:.3f}{suffix}"
  return f"Move `{adjustment['paramKey']}` from {adjustment['current']:.3f} to {adjustment['suggested']:.3f}."


def _what_not_to_touch_yet(summary: dict[str, Any], adjustment: dict[str, Any] | None, strategy: str) -> str:
  if summary.get("bucket") == "center_chatter":
    if adjustment and adjustment.get("stage") == "friction_threshold":
      return "Do not add deadband or center taper yet. First verify whether the speed-localized friction threshold removes the repeated reversals."
    if adjustment and adjustment.get("stage") == "center_deadband":
      return (
        "Do not raise the whole friction curve again or reduce global feedforward. " +
        "This pass is only for the residual near-center motion in the affected speed band."
      )
  if strategy == "baseline":
    if adjustment and adjustment.get("type") in ("generic_param", "friction_curve"):
      return "Do not jump straight into phase-specific cleanup knobs yet. Get the broad authority and friction behavior into the right zip code first."
    return "Do not start layering narrow cleanup knobs onto a car that is still broadly wrong."
  if adjustment and adjustment.get("type") == "generic_param":
    return "Do not widen this into a whole-car ratio or delay change first. This symptom can usually be cleaned up without global geometry edits."
  return "Do not change unrelated center-taper or steer-ratio behavior first. This symptom has a narrower cause than that."


def _if_that_was_wrong(summary: dict[str, Any], adjustment: dict[str, Any], strategy: str) -> str:
  if summary.get("bucket") == "center_chatter":
    if adjustment.get("stage") == "friction_threshold":
      return (
        "If chatter remains after this threshold pass, re-analyze the next drive. FLM will move to a bounded deadband cleanup " +
        "for the same speed band rather than repeatedly raising the whole threshold curve."
      )
    if adjustment.get("stage") == "center_deadband":
      return (
        "If steering becomes reluctant around center, use the conservative profile or halve this deadband step; " +
        "leave the completed friction-threshold pass in place."
      )
  if strategy == "baseline":
    return (
      'If this gets the car broadly closer but leaves one specific phase ugly, stop here and switch to ' +
      f"Cleanup Pass for that band. {_why_this_knob(adjustment)}"
    )
  return (
    'If this cleans up the main symptom but introduces the opposite behavior, keep half the change and ' +
    f"move to the next phase-specific knob. {_why_this_knob(adjustment)}"
  )


def _log_support(summary: dict[str, Any]) -> str:
  evidence = summary.get("evidence", {})
  segment_labels = ", ".join(item["label"] for item in evidence.get("segments", [])[:3]) or "none"
  base = f"Matched in {evidence.get('eventCount', 0)} event(s); strongest samples: {segment_labels}"
  metrics = evidence.get("chatterMetrics", {})
  if summary.get("bucket") != "center_chatter" or not metrics:
    return base

  return (
    f"{base}. Strongest window: steering moved {metrics.get('steeringAngleP2P', 0.0):.2f} deg peak-to-peak " +
    f"with {metrics.get('steeringReversals', 0)} steering reversal(s) and {metrics.get('outputReversals', 0)} output reversal(s), " +
    f"while the desired path moved only {metrics.get('desiredP2P', 0.0):.3f} m/s^2 peak-to-peak"
  )


def build_suggestions(summaries: list[dict[str, Any]], capabilities: dict[str, Any], current: dict[str, Any],
                      strategy: str = "cleanup") -> list[dict[str, Any]]:
  suggestions = []
  for summary in summaries:
    adjustment = _primary_delta_from_summary(summary, capabilities, current, strategy=strategy)
    evidence = summary.get("evidence", {})
    if adjustment is None:
      suggestions.append({
        "dimensionId": summary["dimensionId"],
        "bucket": summary["bucket"],
        "severity": float(summary.get("severity", 0.0)),
        "evidence": evidence,
        "currentVsSuggested": None,
        "observedBehavior": _observed_behavior(summary),
        "likelyInterpretation": _likely_interpretation(summary, {"type": "generic_param", "paramKey": "none"}),
        "primaryAdjustment": "Do not change the tune yet.",
        "whatNotToTouchYet": "Do not start cutting or adding turn-in. This sample does not show a clean controller-side miss.",
        "ifThatWasWrong": "If a stronger sample later shows actual lateral accel lagging or overshooting the plan, revisit with that route.",
        "strategy": strategy,
        "plotSvg": summary.get("plotSvg", ""),
        "plotData": summary.get("plotData", {}),
      })
      continue

    if adjustment["type"] == "friction_curve":
      current_vs_suggested = {
        "type": "friction_curve",
        "family": adjustment["family"],
        "current": adjustment["current"],
        "suggested": adjustment["suggested"],
      }
    elif adjustment["type"] == "vehicle_knob":
      current_vs_suggested = {
        "type": "vehicle_knob",
        "symbol": adjustment["symbol"],
        "current": adjustment["current"],
        "suggested": adjustment["suggested"],
      }
    else:
      current_vs_suggested = {
        "type": "generic_param",
        "paramKey": adjustment["paramKey"],
        "current": adjustment["current"],
        "suggested": adjustment["suggested"],
      }

    suggestions.append({
      "dimensionId": summary["dimensionId"],
      "bucket": summary["bucket"],
      "severity": float(summary.get("severity", 0.0)),
      "evidence": evidence,
      "currentVsSuggested": current_vs_suggested,
      "primaryAdjustmentRaw": adjustment,
      "strategy": strategy,
      "observedBehavior": _observed_behavior(summary),
      "likelyInterpretation": _likely_interpretation(summary, adjustment),
      "primaryAdjustment": _render_adjustment_line(adjustment),
      "whatNotToTouchYet": _what_not_to_touch_yet(summary, adjustment, strategy),
      "ifThatWasWrong": _if_that_was_wrong(summary, adjustment, strategy),
      "driverFeel": _observed_behavior(summary),
      "logSupport": _log_support(summary),
      "whyThisKnob": _why_this_knob(adjustment),
      "plotSvg": summary.get("plotSvg", ""),
      "plotData": summary.get("plotData", {}),
    })
  return suggestions


def _clamp_generic_param(param_key: str, value: float) -> float:
  meta = GENERIC_PARAM_METADATA[param_key]
  return _round_to_precision(_clamp(value, meta["min"], meta["max"]), meta["precision"])


def _merge_primary_adjustments(suggestions: list[dict[str, Any]], multiplier: float) -> tuple[dict[str, Any], dict[str, Any], bool]:
  params_delta: dict[str, Any] = {"AdvancedLateralTune": True}
  requires_force_auto_tune_off = False
  generic_targets: dict[str, dict[str, Any]] = {}
  vehicle_targets: dict[str, dict[str, Any]] = {}
  friction_targets: dict[str, dict[str, Any]] = {}

  for suggestion in suggestions:
    adjustment = suggestion.get("primaryAdjustmentRaw")
    if not isinstance(adjustment, dict):
      continue
    weight = max(float(suggestion.get("severity", 0.0)), 0.25)
    if adjustment["type"] == "generic_param":
      param_key = adjustment["paramKey"]
      bucket = generic_targets.setdefault(param_key, {
        "current": float(adjustment["current"]),
        "weightedDelta": 0.0,
        "weight": 0.0,
      })
      bucket["weightedDelta"] += float(adjustment["delta"]) * weight
      bucket["weight"] += weight
      if param_key in ("SteerFriction", "SteerLatAccel", "SteerKP", "SteerDelay", "SteerRatio"):
        requires_force_auto_tune_off = True
    elif adjustment["type"] == "vehicle_knob":
      symbol = adjustment["symbol"]
      bucket = vehicle_targets.setdefault(symbol, {
        "current": float(adjustment["current"]),
        "weightedDelta": 0.0,
        "weight": 0.0,
      })
      bucket["weightedDelta"] += float(adjustment["delta"]) * weight
      bucket["weight"] += weight
      requires_force_auto_tune_off = True
    elif adjustment["type"] == "friction_curve":
      family = adjustment["family"]
      delta_curve = [float(value) for value in adjustment["delta"]]
      bucket = friction_targets.setdefault(family, {
        "current": [float(value) for value in adjustment["current"]],
        "weightedDelta": [0.0] * len(delta_curve),
        "weights": [0.0] * len(delta_curve),
      })
      for idx, value in enumerate(delta_curve):
        if math.isclose(value, 0.0, abs_tol=1e-9):
          continue
        bucket["weightedDelta"][idx] += value * weight
        bucket["weights"][idx] += weight
      requires_force_auto_tune_off = True

  overrides: dict[str, Any] = {"schemaVersion": 1, "baseFrictionThresholds": {}, "vehicleKnobs": {}}
  for param_key, bucket in generic_targets.items():
    avg_delta = (bucket["weightedDelta"] / bucket["weight"]) * multiplier if bucket["weight"] > 0 else 0.0
    next_value = _clamp_generic_param(param_key, float(bucket["current"]) + avg_delta)
    precision = float(GENERIC_PARAM_METADATA[param_key]["precision"])
    if not math.isclose(float(bucket["current"]), next_value, abs_tol=max(precision / 2.0, 1e-6)):
      params_delta[param_key] = next_value

  if "SteerDelay" in params_delta:
    params_delta["UseAutoSteerDelay"] = False

  supported_knobs = get_flm_supported_vehicle_knobs()
  for symbol, bucket in vehicle_targets.items():
    meta = supported_knobs.get(symbol)
    if meta is None or bucket["weight"] <= 0:
      continue
    avg_delta = (bucket["weightedDelta"] / bucket["weight"]) * multiplier
    next_value = _round_to_precision(_clamp(float(bucket["current"]) + avg_delta, meta["min"], meta["max"]), meta["precision"])
    if not math.isclose(float(bucket["current"]), next_value, abs_tol=max(float(meta["precision"]) / 2.0, 1e-6)):
      overrides["vehicleKnobs"][symbol] = next_value

  for family, bucket in friction_targets.items():
    if not any(weight > 0.0 for weight in bucket["weights"]):
      continue
    avg_delta_curve = [
      value / bucket["weights"][idx] if bucket["weights"][idx] > 0.0 else 0.0
      for idx, value in enumerate(bucket["weightedDelta"])
    ]
    values = [
      round(max(0.05, float(bucket["current"][idx]) + (avg_delta_curve[idx] * multiplier)), 4)
      for idx in range(len(bucket["current"]))
    ]
    if any(not math.isclose(float(bucket["current"][idx]), values[idx], abs_tol=1e-6) for idx in range(len(values))):
      overrides["baseFrictionThresholds"][family] = {"speedKnots": list(FLM_FRICTION_SPEED_KNOTS), "values": values}

  overrides = normalize_flm_overrides(overrides)
  return params_delta, overrides, requires_force_auto_tune_off


def _resolve_conflicting_actionable_suggestions(suggestions: list[dict[str, Any]]) -> list[dict[str, Any]]:
  families = {
    "understeer": ("turn_in", "more"),
    "late_turn_in": ("turn_in", "more"),
    "oversteer": ("turn_in", "less"),
    "early_turn_in": ("turn_in", "less"),
    "unwind_too_slow": ("unwind", "more"),
    "unwind_too_fast": ("unwind", "less"),
  }
  grouped: dict[tuple[str, str, str], dict[str, list[dict[str, Any]]]] = {}
  passthrough: list[dict[str, Any]] = []

  for suggestion in suggestions:
    bucket = str(suggestion.get("bucket", ""))
    family_info = families.get(bucket)
    if family_info is None:
      passthrough.append(suggestion)
      continue
    evidence = suggestion.get("evidence", {})
    key = (
      family_info[0],
      str(evidence.get("directionBias", "center")),
      str(evidence.get("speedBand", "mixed")),
    )
    grouped.setdefault(key, {"more": [], "less": []})[family_info[1]].append(suggestion)

  resolved = list(passthrough)
  for polarities in grouped.values():
    more = polarities["more"]
    less = polarities["less"]
    if not more or not less:
      resolved.extend(more or less)
      continue

    def score(items: list[dict[str, Any]]) -> float:
      total = 0.0
      for item in items:
        severity = max(float(item.get("severity", 0.0)), 0.25)
        event_count = max(int(item.get("evidence", {}).get("eventCount", 0)), 1)
        total += severity * math.log1p(event_count)
      return total

    more_score = score(more)
    less_score = score(less)
    if more_score >= less_score * 1.2:
      resolved.extend(more)
    elif less_score >= more_score * 1.2:
      resolved.extend(less)

  return sorted(resolved, key=lambda item: float(item.get("severity", 0.0)), reverse=True)


def _bucket_tuning_family(bucket: str) -> str:
  if bucket in ("understeer", "late_turn_in", "oversteer", "early_turn_in", "saturation_limited", "low_speed_unwillingness"):
    return "authority"
  if bucket in ("unwind_too_slow", "unwind_too_fast"):
    return "release"
  if bucket in ("center_chatter", "notchy_mid_curve"):
    return "stability"
  return "other"


def _select_primary_tuning_path_unlocked(summaries: list[dict[str, Any]], summary_stats: dict[str, Any]) -> dict[str, Any]:
  actionable = [
    summary for summary in summaries
    if summary.get("bucket") not in ("model_limited", "angle_control_diagnostic")
    and float(summary.get("severity", 0.0)) >= 0.4
  ]
  if not actionable:
    return {
      "primaryPathKey": "cleanup_pass",
      "alternatePathKey": "baseline_fix",
      "reason": "This sample does not show a broad controller-side miss. Start with the narrower cleanup path if you test anything.",
      "baselineScore": 0,
    }

  mean_error = float(summary_stats.get("meanErrorAbs", 0.0) or 0.0)
  families = {_bucket_tuning_family(str(summary.get("bucket", ""))) for summary in actionable}
  major_events = [summary for summary in actionable if float(summary.get("severity", 0.0)) >= 0.8]
  severe_global = [
    summary for summary in actionable
    if summary.get("bucket") in ("understeer", "oversteer", "late_turn_in", "early_turn_in", "saturation_limited")
    and float(summary.get("severity", 0.0)) >= 0.85
  ]
  severe_global_bands = {
    (str(summary.get("direction", "center")), str(summary.get("speedBand", "mixed")))
    for summary in severe_global
  }
  severe_global_segments = {
    str(segment.get("label", ""))
    for summary in severe_global
    for segment in summary.get("evidence", {}).get("segments", [])
    if segment.get("label")
  }
  severe_saturation = any(
    summary.get("bucket") == "saturation_limited" and float(summary.get("severity", 0.0)) >= 0.85
    for summary in actionable
  )

  if mean_error < 0.08 and not severe_saturation and not (
    len(severe_global_bands) >= 2 and len(severe_global_segments) >= 2
  ):
    return {
      "primaryPathKey": "cleanup_pass",
      "alternatePathKey": "baseline_fix",
      "reason": ('Overall lateral-accel tracking is already strong. The remaining misses are isolated ' +
        'enough that changing the base tune would disturb more good behavior than it fixes.'),
      "baselineScore": 0,
    }

  baseline_score = 0
  if mean_error >= 0.14:
    baseline_score += 2
  elif mean_error >= 0.11:
    baseline_score += 1
  if len(actionable) >= 4:
    baseline_score += 1
  if len(families - {"other"}) >= 3:
    baseline_score += 1
  if len(major_events) >= 2:
    baseline_score += 1
  if severe_global:
    baseline_score += 1

  if baseline_score >= 3:
    return {
      "primaryPathKey": "baseline_fix",
      "alternatePathKey": "cleanup_pass",
      "reason": ('This route looks broadly wrong across enough bands that the right first move is to fix ' +
        'base authority and friction behavior before touching narrower cleanup layers.'),
      "baselineScore": baseline_score,
    }

  return {
    "primaryPathKey": "cleanup_pass",
    "alternatePathKey": "baseline_fix",
    "reason": "This route is already close enough overall that the better first move is a narrow cleanup pass instead of a broad whole-car reset.",
    "baselineScore": baseline_score,
  }


def select_primary_tuning_path(summaries: list[dict[str, Any]], summary_stats: dict[str, Any],
                               cleanup_progress_locked: bool = False) -> dict[str, Any]:
  decision = _select_primary_tuning_path_unlocked(summaries, summary_stats)
  if not cleanup_progress_locked:
    return decision

  raw_primary_path = decision["primaryPathKey"]
  if raw_primary_path == "baseline_fix":
    return {
      **decision,
      "primaryPathKey": "cleanup_pass",
      "alternatePathKey": "baseline_fix",
      "reason": (
        "This vehicle already progressed to Cleanup Pass. This route contains broader misses, but FLM will not automatically " +
        "reset a tune that already reached fine adjustment. Review Baseline Fix manually if the regression is real and repeatable."
      ),
      "rawPrimaryPathKey": raw_primary_path,
      "automaticBaselineDemotionBlocked": True,
      "cleanupProgressLocked": True,
    }

  return {
    **decision,
    "rawPrimaryPathKey": raw_primary_path,
    "cleanupProgressLocked": True,
  }


def build_trial_profiles(report_id: str, suggestions: list[dict[str, Any]], feedback: dict[str, Any], capabilities: dict[str, Any],
                         path_key: str = "cleanup_pass", path_label: str = "Cleanup Pass") -> list[dict[str, Any]]:
  ignored = {str(item) for item in feedback.get("ignoredDimensions", [])}
  accepted = {str(item) for item in feedback.get("acceptedDimensions", [])}
  has_feedback_decisions = bool(ignored or accepted)

  considered = [
    suggestion for suggestion in suggestions
    if suggestion.get("dimensionId") not in ignored and (
      not accepted or suggestion.get("dimensionId") in accepted
    )
  ]
  if not considered and not has_feedback_decisions:
    considered = [suggestion for suggestion in suggestions if suggestion.get("primaryAdjustmentRaw")]
  actionable = [
    suggestion for suggestion in considered
    if suggestion.get("primaryAdjustmentRaw")
  ]
  actionable = _resolve_conflicting_actionable_suggestions(actionable)

  profiles = []
  profile_defs = [
    ("conservative", "Conservative", 0.6),
    ("recommended", "Recommended", 1.0),
    ("assertive", "Assertive", 1.35),
  ]
  for suffix, label, multiplier in profile_defs:
    params_delta, overrides, force_auto_tune_off = _merge_primary_adjustments(actionable, multiplier)
    if not overrides and len(params_delta) <= 1:
      continue
    profile = {
      "id": f"{report_id}:{path_key}:{suffix}",
      "reportId": report_id,
      "label": label,
      "pathKey": path_key,
      "pathLabel": path_label,
      "description": f"{label} {path_label.lower()} trial generated from {len(actionable)} confirmed symptom dimension(s).",
      "genericParams": params_delta,
      "flmOverrides": overrides,
      "requiresForceAutoTuneOff": bool(force_auto_tune_off),
      "capabilities": capabilities,
    }
    if force_auto_tune_off:
      profile["genericParams"]["ForceAutoTuneOff"] = True
      profile["genericParams"]["ForceAutoTune"] = False
    profiles.append(profile)

  return profiles[:3]


def build_recommendation_paths(report_id: str, summaries: list[dict[str, Any]], summary_stats: dict[str, Any],
                               capabilities: dict[str, Any], current: dict[str, Any],
                               feedback: dict[str, Any], cleanup_progress_locked: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
  decision = select_primary_tuning_path(summaries, summary_stats, cleanup_progress_locked)
  all_suggestions = {
    "baseline_fix": build_suggestions(summaries, capabilities, current, strategy="baseline"),
    "cleanup_pass": build_suggestions(summaries, capabilities, current, strategy="cleanup"),
  }

  ordered_keys = [decision["primaryPathKey"], decision["alternatePathKey"]]
  paths = []
  for path_key in ordered_keys:
    spec = FLM_PATH_SPECS[path_key]
    suggestions = all_suggestions[path_key]
    profiles = build_trial_profiles(report_id, suggestions, feedback, capabilities, path_key=path_key, path_label=spec["title"])
    paths.append({
      "key": path_key,
      "title": spec["title"],
      "description": spec["description"],
      "whenToUse": spec["whenToUse"],
      "alternateHint": spec["alternateHint"],
      "isPrimary": path_key == decision["primaryPathKey"],
      "whySelected": decision["reason"] if path_key == decision["primaryPathKey"] else spec["alternateHint"],
      "suggestions": suggestions,
      "profiles": profiles,
    })
  return paths, decision
