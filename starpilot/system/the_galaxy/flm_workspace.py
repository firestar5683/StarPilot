#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import shutil
import signal
import subprocess
import sys
import threading
import time

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from cereal import car
from opendbc.car.hyundai.values import HyundaiFlags
from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib.latcontrol_torque import KP
from openpilot.selfdrive.controls.lib.latcontrol_vehicle_tunes import (
  FLM_FRICTION_SPEED_KNOTS,
  get_flm_capabilities,
  get_flm_rich_profile_key,
  get_flm_supported_vehicle_knobs,
  get_gm_base_friction_threshold,
  get_hkg_canfd_base_friction_threshold,
  get_standard_friction_threshold,
  normalize_flm_overrides,
)
from openpilot.starpilot.common.lateral_delay import full_lateral_delay
from openpilot.system.hardware import PC
from openpilot.system.hardware.hw import Paths
from openpilot.tools.lib.logreader import LogReader
from openpilot.starpilot.system.the_galaxy import utilities


FLM_STATUS_PATH = Path("/tmp/galaxy_flm_status.json")
FLM_LOG_PATH = Path("/tmp/galaxy_flm.log")
FLM_STATUS_MAX_AGE_SECONDS = 3600.0
FLM_ANALYZER_ROUTE_LIMIT = 8
FLM_ANALYZER_PROCESS = None
FLM_ANALYZER_LOCK = threading.Lock()
FLM_PROGRESS_FILENAME = "progress.json"
FLM_ONROAD_POLL_INTERVAL_SECONDS = 0.25
FLM_SEGMENT_TIMEOUT_SECONDS = 60.0


class FLMAnalysisCancelled(RuntimeError):
  pass


class FLMSegmentTimeout(RuntimeError):
  pass


TRIAL_PARAM_SPECS = {
  "AdvancedLateralTune": "bool",
  "ForceAutoTune": "bool",
  "ForceAutoTuneOff": "bool",
  "UseAutoSteerDelay": "bool",
  "SteerDelay": "float",
  "SteerFriction": "float",
  "SteerKP": "float",
  "SteerLatAccel": "float",
  "SteerRatio": "float",
  "FLMActiveProfileId": "string",
  "FLMActiveOverrides": "json",
  "FLMTrialApplied": "bool",
}

FLM_ADVANCED_LATERAL_PARAM_KEYS = {
  "AdvancedLateralTune",
  "ForceAutoTune",
  "ForceAutoTuneOff",
  "UseAutoSteerDelay",
  "SteerDelay",
  "SteerFriction",
  "SteerKP",
  "SteerLatAccel",
  "SteerRatio",
}
FLM_TRIAL_BASELINE_PARAM = "FLMTrialBaseline"

GENERIC_PARAM_METADATA = {
  "SteerDelay": {"min": 0.01, "max": 1.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "SteerFriction": {"min": 0.0, "max": 1.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "SteerKP": {"min": 0.1, "max": 1.5, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "SteerLatAccel": {"min": 0.5, "max": 5.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
  "SteerRatio": {"min": 5.0, "max": 25.0, "precision": 0.001, "deltaType": "absolute", "safeLiveTrial": True},
}

FLM_REFERENCE_MODEL = {
  "version": 1,
  "families": {
    "turn_in_boost": {
      "reason": "Used when the car waits too long to initiate torque even though desired lateral accel is already rising.",
      "too_low": "Turn starts late or feels unwilling.",
      "too_high": "Car dives into the curve too early or spikes past the plan on entry.",
    },
    "unwind_taper": {
      "reason": "Used when the car holds steering too long or drops it too quickly on exit.",
      "too_low": "Unwind drags and the car keeps steering past the intended release.",
      "too_high": "Unwind snaps back and the wheel releases too aggressively.",
    },
    "friction_threshold_curve": {
      "reason": "Used to calm chatter or wake up low-speed response without pretending the whole torque map is wrong.",
      "too_low": "Tiny errors create twitch and correction chatter.",
      "too_high": "Controller feels reluctant near center and can hesitate at low speed.",
    },
    "center_taper": {
      "reason": "Used only when the problem is calm-road or near-center nibbling, not general curve response.",
      "too_low": "Straight-road wheel activity stays busy.",
      "too_high": "Car feels lazy around center and can miss light corrections.",
    },
  },
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


@dataclass(slots=True)
class RouteSource:
  route: str
  footage_path: str
  segment: str
  segment_num: int
  log_path: str
  used_qlog: bool


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
  error: float
  error_rate: float
  p: float
  i: float
  d: float
  f: float
  output: float
  steering_angle_deg: float
  steering_torque: float
  cmd_torque: float
  out_torque: float
  roll_deg: float


def _get_galaxy_dir() -> Path:
  return Path(Paths.comma_home()) / "starpilot" / "data" / "galaxy" if PC else Path("/data/galaxy")


def get_flm_workspace_root() -> Path:
  return _get_galaxy_dir() / "flm"


def _legacy_workspace_root() -> Path:
  return _get_galaxy_dir() / "".join(("f", "t", "m"))


def _migrate_legacy_payload(value):
  legacy_upper = "".join(("F", "T", "M"))
  legacy_lower = legacy_upper.lower()
  if isinstance(value, dict):
    migrated = {}
    for key, item in value.items():
      migrated_key = str(key)
      if migrated_key.startswith(legacy_upper):
        migrated_key = f"FLM{migrated_key[len(legacy_upper):]}"
      elif migrated_key.startswith(legacy_lower):
        migrated_key = f"flm{migrated_key[len(legacy_lower):]}"
      migrated[migrated_key] = _migrate_legacy_payload(item)
    return migrated
  if isinstance(value, list):
    return [_migrate_legacy_payload(item) for item in value]
  if isinstance(value, str):
    legacy_method_name = "Firestar " + "Tuning Method"
    return value.replace(legacy_method_name, "Firestar Lateral Method").replace(legacy_upper, "FLM")
  return value


def _migrate_legacy_workspace(root: Path) -> None:
  marker = root / ".flm_rebrand_v1"
  if marker.exists():
    return

  legacy_root = _legacy_workspace_root()
  if legacy_root.is_dir() and legacy_root != root:
    root.parent.mkdir(parents=True, exist_ok=True)
    if root.exists():
      shutil.copytree(legacy_root, root, dirs_exist_ok=True)
      shutil.rmtree(legacy_root)
    else:
      legacy_root.replace(root)

  if not root.exists():
    return

  legacy_lower = "".join(("f", "t", "m"))
  legacy_reference = root / "reference" / f"{legacy_lower}_reference.json"
  current_reference = root / "reference" / "flm_reference.json"
  if legacy_reference.is_file() and not current_reference.exists():
    legacy_reference.replace(current_reference)

  for path in root.rglob("*.json"):
    try:
      payload = json.loads(path.read_text(encoding="utf-8"))
      migrated = _migrate_legacy_payload(payload)
      if migrated != payload:
        path.write_text(json.dumps(migrated, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
      continue

  legacy_upper = legacy_lower.upper()
  for path in root.rglob("*.html"):
    try:
      content = path.read_text(encoding="utf-8")
      content = content.replace(legacy_upper, "FLM").replace(legacy_lower, "flm")
      path.write_text(content, encoding="utf-8")
    except Exception:
      continue

  marker.touch()


def _workspace_paths() -> dict[str, Path]:
  root = get_flm_workspace_root()
  return {
    "root": root,
    "reports": root / "reports",
    "profiles": root / "profiles",
    "feedback": root / "feedback",
    "snapshots": root / "snapshots",
    "savedTunes": root / "saved_tunes",
    "reference": root / "reference",
  }


def ensure_flm_workspace() -> dict[str, Path]:
  _migrate_legacy_workspace(get_flm_workspace_root())
  paths = _workspace_paths()
  for key, path in paths.items():
    if key != "root":
      path.mkdir(parents=True, exist_ok=True)
  reference_path = paths["reference"] / "flm_reference.json"
  if not reference_path.exists():
    reference_path.write_text(json.dumps(FLM_REFERENCE_MODEL, indent=2, sort_keys=True), encoding="utf-8")
  return paths


def _read_json(path: Path, default):
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except Exception:
    return default


def _write_json(path: Path, payload) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp_path = path.with_suffix(path.suffix + ".tmp")
  tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
  tmp_path.replace(path)


def _progress_path() -> Path:
  return get_flm_workspace_root() / FLM_PROGRESS_FILENAME


def _record_cleanup_progress(car_fingerprint: str, source_report_id: str = "") -> None:
  fingerprint = str(car_fingerprint or "").strip()
  if not fingerprint:
    return

  progress = _read_json(_progress_path(), {})
  if not isinstance(progress, dict):
    progress = {}
  vehicles = progress.get("vehicles", {})
  if not isinstance(vehicles, dict):
    vehicles = {}
  vehicles[fingerprint] = {
    "minimumPathKey": "cleanup_pass",
    "sourceReportId": str(source_report_id or ""),
    "updatedAt": time.time(),
  }
  _write_json(_progress_path(), {"version": 1, "vehicles": vehicles})


def _cleanup_progress_locked(car_fingerprint: str) -> bool:
  fingerprint = str(car_fingerprint or "").strip()
  if not fingerprint:
    return False

  progress = _read_json(_progress_path(), {})
  vehicle_progress = progress.get("vehicles", {}).get(fingerprint, {}) if isinstance(progress, dict) else {}
  if isinstance(vehicle_progress, dict) and vehicle_progress.get("minimumPathKey") == "cleanup_pass":
    return True

  # Bootstrap workspaces created before progression tracking was added.
  for path in _workspace_paths()["reports"].glob("*.json"):
    report = _read_json(path, {})
    if not isinstance(report, dict):
      continue
    car_info = report.get("car", {})
    if (
      isinstance(car_info, dict)
      and str(car_info.get("carFingerprint", "")) == fingerprint
      and car_info.get("controlPath") == "torque"
      and report.get("primaryPathKey") == "cleanup_pass"
    ):
      _record_cleanup_progress(fingerprint, str(report.get("reportId", path.stem)))
      return True
  return False


def _worker_env(repo_root: Path) -> dict[str, str]:
  env = os.environ.copy()
  pythonpath = [
    "/usr/local/venv/lib/python3.12/site-packages",
    str(repo_root / "starpilot" / "third_party"),
    str(repo_root),
  ]
  if env.get("PYTHONPATH"):
    pythonpath.append(env["PYTHONPATH"])
  env["PYTHONPATH"] = os.pathsep.join(pythonpath)
  env.setdefault("OPENBLAS_NUM_THREADS", "1")
  env.setdefault("OMP_NUM_THREADS", "1")
  env.setdefault("MKL_NUM_THREADS", "1")
  env.setdefault("NUMEXPR_NUM_THREADS", "1")
  return env


def read_flm_status() -> dict[str, Any]:
  data = _read_json(FLM_STATUS_PATH, {})
  return data if isinstance(data, dict) else {}


def _write_flm_status(payload: dict[str, Any]) -> None:
  payload = dict(payload)
  payload["updatedAt"] = time.time()
  tmp_path = FLM_STATUS_PATH.with_suffix(".tmp")
  tmp_path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
  tmp_path.replace(FLM_STATUS_PATH)


def clear_flm_status() -> None:
  try:
    FLM_STATUS_PATH.unlink()
  except FileNotFoundError:
    pass
  except OSError:
    pass


def _require_flm_offroad(params: Params | None = None) -> None:
  params = params or Params(return_defaults=True)
  if params.get_bool("IsOnroad"):
    raise FLMAnalysisCancelled("FLM analysis stopped because the vehicle went onroad.")


def flm_analyzer_running() -> bool:
  process = FLM_ANALYZER_PROCESS
  if process is not None and process.poll() is None:
    return True

  status = read_flm_status()
  pid = int(status.get("pid") or 0)
  started_at = float(status.get("startedAt") or 0.0)
  if pid <= 0 or started_at <= 0:
    return False
  if (time.time() - started_at) > FLM_STATUS_MAX_AGE_SECONDS:
    clear_flm_status()
    return False
  try:
    os.kill(pid, 0)
  except ProcessLookupError:
    clear_flm_status()
    return False
  except PermissionError:
    return True
  except OSError:
    return False
  return True


def _terminate_flm_process(process) -> None:
  try:
    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
  except (AttributeError, ProcessLookupError, PermissionError, OSError):
    try:
      process.terminate()
    except (AttributeError, ProcessLookupError, OSError):
      pass

  try:
    process.wait(timeout=2.0)
  except subprocess.TimeoutExpired:
    try:
      os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (AttributeError, ProcessLookupError, PermissionError, OSError):
      try:
        process.kill()
      except (AttributeError, ProcessLookupError, OSError):
        pass
    try:
      process.wait(timeout=1.0)
    except (AttributeError, subprocess.TimeoutExpired):
      pass


def _write_flm_cancelled_status(status: dict[str, Any], reason: str) -> None:
  _write_flm_status({
    **status,
    "pid": 0,
    "running": False,
    "state": "cancelled_onroad" if reason == "onroad" else "cancelled",
    "error": "FLM analysis stopped because the vehicle went onroad." if reason == "onroad" else "",
  })


def stop_flm_background_analysis(reason: str = "") -> bool:
  global FLM_ANALYZER_PROCESS

  with FLM_ANALYZER_LOCK:
    process = FLM_ANALYZER_PROCESS
    status = read_flm_status()
    pid = int(status.get("pid") or 0)

    if process is not None and process.poll() is None:
      _terminate_flm_process(process)
      FLM_ANALYZER_PROCESS = None
      if reason:
        _write_flm_cancelled_status(status, reason)
      else:
        clear_flm_status()
      return True

    if pid > 0:
      try:
        os.killpg(pid, signal.SIGTERM)
      except ProcessLookupError:
        pass
      except PermissionError:
        try:
          os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
          return False
      except OSError:
        try:
          os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
          return False
      if reason:
        _write_flm_cancelled_status(status, reason)
      else:
        clear_flm_status()
      return True

  return False


def _watch_flm_process_for_onroad(process) -> None:
  params = Params(return_defaults=True)
  while process.poll() is None:
    if params.get_bool("IsOnroad"):
      stop_flm_background_analysis(reason="onroad")
      return
    time.sleep(FLM_ONROAD_POLL_INTERVAL_SECONDS)


def _watch_flm_worker_for_onroad() -> None:
  params = Params(return_defaults=True)
  while True:
    if params.get_bool("IsOnroad"):
      _write_flm_cancelled_status(read_flm_status(), "onroad")
      # Workers are launched as process-group leaders. Terminate the entire group
      # so any log decompression helpers cannot survive the onroad transition.
      if os.getpgrp() == os.getpid():
        try:
          os.killpg(os.getpgrp(), signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
          pass
      os._exit(0)
    time.sleep(FLM_ONROAD_POLL_INTERVAL_SECONDS)


def cancel_flm_if_onroad() -> bool:
  if not Params(return_defaults=True).get_bool("IsOnroad"):
    return False
  if not flm_analyzer_running():
    return False
  return stop_flm_background_analysis(reason="onroad")


def _optional_segment_number(value: Any) -> int | None:
  if value is None or str(value).strip() == "":
    return None
  number = int(value)
  if number < 0:
    raise ValueError("Segment numbers cannot be negative.")
  return number


def normalize_segment_ranges(route_names: list[str], segment_ranges: Any) -> dict[str, dict[str, int | None]]:
  if not isinstance(segment_ranges, dict):
    return {}

  normalized: dict[str, dict[str, int | None]] = {}
  valid_routes = set(route_names)
  for route, raw_range in segment_ranges.items():
    route_name = str(route).strip()
    if route_name not in valid_routes or not isinstance(raw_range, dict):
      continue
    start = _optional_segment_number(raw_range.get("start"))
    end = _optional_segment_number(raw_range.get("end"))
    if start is not None and end is not None and start > end:
      raise ValueError(f"{route_name}: the first segment cannot be after the last segment.")
    if start is not None or end is not None:
      normalized[route_name] = {"start": start, "end": end}
  return normalized


def start_flm_background_analysis(route_names: list[str], footage_paths: list[str],
                                  segment_ranges: dict[str, dict[str, int | None]] | None = None) -> bool:
  global FLM_ANALYZER_PROCESS

  route_names = [str(route) for route in route_names if str(route).strip()]
  if not route_names:
    return False
  segment_ranges = normalize_segment_ranges(route_names, segment_ranges)
  try:
    _require_flm_offroad()
  except FLMAnalysisCancelled:
    return False

  ensure_flm_workspace()
  process_to_watch = None
  with FLM_ANALYZER_LOCK:
    if flm_analyzer_running():
      return True

    repo_root = Path(__file__).resolve().parents[3]
    command = [
      "nice",
      "-n",
      "19",
      sys.executable or "python3",
      str(Path(__file__).resolve()),
      "worker",
      json.dumps({
        "routes": route_names[:FLM_ANALYZER_ROUTE_LIMIT],
        "footagePaths": [str(path) for path in footage_paths],
        "segmentRanges": {
          route: segment_range
          for route, segment_range in segment_ranges.items()
          if route in route_names[:FLM_ANALYZER_ROUTE_LIMIT]
        },
      }),
    ]
    log_file = None
    try:
      log_file = open(FLM_LOG_PATH, "ab")
      FLM_ANALYZER_PROCESS = subprocess.Popen(
        command,
        cwd=str(repo_root),
        env=_worker_env(repo_root),
        stdout=log_file,
        stderr=log_file,
        start_new_session=True,
      )
      process_to_watch = FLM_ANALYZER_PROCESS
      _write_flm_status({
        "pid": FLM_ANALYZER_PROCESS.pid,
        "startedAt": time.time(),
        "running": True,
        "state": "queued",
        "routes": route_names[:FLM_ANALYZER_ROUTE_LIMIT],
        "segmentRanges": segment_ranges,
        "progress": 0,
        "total": len(route_names[:FLM_ANALYZER_ROUTE_LIMIT]),
      })
    except Exception:
      FLM_ANALYZER_PROCESS = None
      return False
    finally:
      if log_file is not None:
        log_file.close()

  if process_to_watch is not None:
    threading.Thread(target=_watch_flm_process_for_onroad, args=(process_to_watch,), daemon=True).start()

  return flm_analyzer_running()


def _parse_segment_num(segment_name: str) -> int:
  try:
    return int(str(segment_name).rsplit("--", 1)[1])
  except Exception:
    return 0


def resolve_route_sources(route_names: list[str], footage_paths: list[str],
                          segment_ranges: dict[str, dict[str, int | None]] | None = None) -> tuple[list[RouteSource], list[str]]:
  sources: list[RouteSource] = []
  warnings: list[str] = []
  segment_ranges = normalize_segment_ranges(route_names, segment_ranges)
  for route in route_names:
    route_added = False
    segment_range = segment_ranges.get(route, {})
    segment_start = segment_range.get("start")
    segment_end = segment_range.get("end")
    for footage_path in footage_paths:
      segments = utilities.get_segments_in_route(route, footage_path)
      if not segments:
        continue
      for segment in segments:
        segment_num = _parse_segment_num(segment)
        if segment_start is not None and segment_num < segment_start:
          continue
        if segment_end is not None and segment_num > segment_end:
          continue
        segment_path = Path(footage_path) / segment
        rlog_path = None
        qlog_path = None
        for candidate in ("rlog.zst", "rlog.bz2", "rlog"):
          candidate_path = segment_path / candidate
          if candidate_path.exists():
            rlog_path = candidate_path
            break
        for candidate in ("qlog.zst", "qlog.bz2", "qlog"):
          candidate_path = segment_path / candidate
          if candidate_path.exists():
            qlog_path = candidate_path
            break
        log_path = rlog_path or qlog_path
        if log_path is None:
          continue
        if rlog_path is None and qlog_path is not None:
          warnings.append(f"{route} segment {segment} fell back to qlog.")
        sources.append(RouteSource(
          route=route,
          footage_path=str(footage_path),
          segment=segment,
          segment_num=segment_num,
          log_path=str(log_path),
          used_qlog=rlog_path is None,
        ))
        route_added = True
      if route_added:
        break
    if not route_added:
      if segment_range:
        start_label = segment_start if segment_start is not None else "first"
        end_label = segment_end if segment_end is not None else "last"
        warnings.append(f"{route} had no local logs in the selected segment range {start_label}-{end_label}.")
      else:
        warnings.append(f"{route} could not be resolved to a local route with logs.")
  sources.sort(key=lambda source: (source.route, source.segment_num))
  return sources, warnings


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
    "<svg viewBox='0 0 380 140' class='flm-plot' preserveAspectRatio='none'>"
    "<rect x='0' y='0' width='380' height='140' rx='8' ry='8' fill='#0f172a'/>"
    "<line x1='0' y1='120' x2='380' y2='120' stroke='#334155' stroke-width='1'/>"
    f"<polyline fill='none' stroke='#ef4444' stroke-width='2' points='{_points(desired)}'/>"
    f"<polyline fill='none' stroke='#38bdf8' stroke-width='2' points='{_points(actual)}'/>"
    "</svg>"
  )


def _decode_init_param(init, key: str) -> str:
  params = getattr(init, "params", None)
  if isinstance(params, dict):
    value = params.get(key, b"")
  else:
    value = next((entry.value for entry in getattr(params, "entries", []) if entry.key == key), b"")

  try:
    return bytes(value).decode("utf-8", errors="replace")
  except (TypeError, ValueError):
    return str(value or "")


def _car_params_control_path(car_params) -> str:
  angle_type = getattr(car.CarParams.SteerControlType, "angle", None)
  if angle_type is not None and getattr(car_params, "steerControlType", None) == angle_type:
    return "angle"

  lateral_tuning = getattr(car_params, "lateralTuning", None)
  tuning_type = lateral_tuning.which() if lateral_tuning is not None else ""
  return tuning_type if tuning_type in ("torque", "pid") else "unknown"


def _effective_control_path(car_params, observed_states: dict[str, int]) -> tuple[str, str]:
  state_paths = {
    "torqueState": "torque",
    "pidState": "pid",
    "angleState": "angle",
  }
  observed_paths = {
    path for state, path in state_paths.items()
    if int(observed_states.get(state, 0) or 0) > 0
  }
  if len(observed_paths) == 1:
    return observed_paths.pop(), "controlsState"
  if len(observed_paths) > 1:
    return "mixed", "controlsState"
  return _car_params_control_path(car_params), "carParams"


def _effective_torque_car_params(car_params):
  if _car_params_control_path(car_params) == "torque":
    return car_params

  try:
    from opendbc.car.interfaces import CarInterfaceBase

    builder = car_params.as_builder()
    CarInterfaceBase.configure_torque_tune(builder.carFingerprint, builder.lateralTuning)
    return builder
  except (AttributeError, KeyError, TypeError, ValueError):
    return car_params


def _segment_samples(segment_source: RouteSource, params: Params | None = None) -> tuple[list[FLMSample], car.CarParams | None, dict[str, str], dict[str, int]]:
  samples: list[FLMSample] = []
  car_params = None
  init_data: dict[str, str] = {}
  control_states: dict[str, int] = {}
  latest: dict[str, Any] = {}
  params = params or Params(return_defaults=True)
  last_offroad_check = 0.0

  _require_flm_offroad(params)

  for msg in LogReader(segment_source.log_path):
    now = time.monotonic()
    if now - last_offroad_check >= FLM_ONROAD_POLL_INTERVAL_SECONDS:
      _require_flm_offroad(params)
      last_offroad_check = now

    which = msg.which()
    if which == "carParams":
      car_params = msg.carParams
      continue
    if which == "initData":
      init = msg.initData
      init_data = {
        "gitCommit": str(getattr(init, "gitCommit", "") or ""),
        "gitBranch": str(getattr(init, "gitBranch", "") or ""),
        "ForceTorqueController": _decode_init_param(init, "ForceTorqueController"),
      }
      continue
    if which == "carState":
      latest["carState"] = msg.carState
      continue
    if which == "carControl":
      latest["carControl"] = msg.carControl
      continue
    if which == "carOutput":
      latest["carOutput"] = msg.carOutput
      continue
    if which == "liveParameters":
      latest["liveParameters"] = msg.liveParameters
      continue
    if which != "controlsState":
      continue

    controls_state = msg.controlsState
    lateral_state = controls_state.lateralControlState
    lateral_state_name = lateral_state.which()
    control_states[lateral_state_name] = control_states.get(lateral_state_name, 0) + 1
    if lateral_state_name != "torqueState" or "carState" not in latest or "carControl" not in latest:
      continue

    torque_state = lateral_state.torqueState
    car_state = latest["carState"]
    car_control = latest["carControl"]
    live_parameters = latest.get("liveParameters")
    car_output = latest.get("carOutput")
    roll_deg = math.degrees(float(getattr(live_parameters, "roll", 0.0) or 0.0)) if live_parameters is not None else 0.0
    out_torque = float(getattr(getattr(car_output, "actuatorsOutput", None), "torque", 0.0) or 0.0) if car_output is not None else 0.0

    samples.append(FLMSample(
      route=segment_source.route,
      segment=segment_source.segment_num,
      t=float(msg.logMonoTime) / 1e9,
      v_ego=float(getattr(car_state, "vEgo", 0.0) or 0.0),
      lat_active=bool(getattr(car_control, "latActive", False)),
      steering_pressed=bool(getattr(car_state, "steeringPressed", False)),
      saturated=bool(getattr(torque_state, "saturated", False)),
      actual_la=float(getattr(torque_state, "actualLateralAccel", 0.0) or 0.0),
      desired_la=float(getattr(torque_state, "desiredLateralAccel", 0.0) or 0.0),
      desired_jerk=float(getattr(torque_state, "desiredLateralJerk", 0.0) or 0.0),
      error=float(getattr(torque_state, "error", 0.0) or 0.0),
      error_rate=float(getattr(torque_state, "errorRate", 0.0) or 0.0),
      p=float(getattr(torque_state, "p", 0.0) or 0.0),
      i=float(getattr(torque_state, "i", 0.0) or 0.0),
      d=float(getattr(torque_state, "d", 0.0) or 0.0),
      f=float(getattr(torque_state, "f", 0.0) or 0.0),
      output=float(getattr(torque_state, "output", 0.0) or 0.0),
      steering_angle_deg=float(getattr(car_state, "steeringAngleDeg", 0.0) or 0.0),
      steering_torque=float(getattr(car_state, "steeringTorque", 0.0) or 0.0),
      cmd_torque=float(getattr(getattr(car_control, "actuators", None), "torque", 0.0) or 0.0),
      out_torque=out_torque,
      roll_deg=roll_deg,
    ))

  return samples, car_params, init_data, control_states


def _segment_samples_with_timeout(segment_source: RouteSource, params: Params,
                                  timeout_seconds: float = FLM_SEGMENT_TIMEOUT_SECONDS):
  if (
    timeout_seconds <= 0.0
    or threading.current_thread() is not threading.main_thread()
    or not hasattr(signal, "SIGALRM")
    or not hasattr(signal, "setitimer")
  ):
    return _segment_samples(segment_source, params=params)

  def handle_timeout(_signum, _frame):
    raise FLMSegmentTimeout(
      f"{segment_source.route} segment {segment_source.segment_num} exceeded the {timeout_seconds:.0f}-second read limit."
    )

  previous_handler = signal.getsignal(signal.SIGALRM)
  signal.signal(signal.SIGALRM, handle_timeout)
  previous_timer = signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
  try:
    return _segment_samples(segment_source, params=params)
  finally:
    signal.setitimer(signal.ITIMER_REAL, 0.0)
    signal.signal(signal.SIGALRM, previous_handler)
    if previous_timer[0] > 0.0:
      signal.setitimer(signal.ITIMER_REAL, previous_timer[0], previous_timer[1])


def _current_param_state(CP, params: Params) -> dict[str, Any]:
  advanced_enabled = params.get_bool("AdvancedLateralTune")
  torque_tune = CP.lateralTuning.torque if CP.lateralTuning.which() == "torque" else None
  stock_delay = full_lateral_delay(float(getattr(CP, "steerActuatorDelay", 0.0) or 0.0))
  stock_ratio = float(getattr(CP, "steerRatio", 0.0) or 0.0)
  stock_friction = float(getattr(torque_tune, "friction", 0.0) or 0.0) if torque_tune is not None else 0.0
  stock_lat_accel = float(getattr(torque_tune, "latAccelFactor", 0.0) or 0.0) if torque_tune is not None else 0.0
  return {
    "AdvancedLateralTune": advanced_enabled,
    "ForceAutoTune": params.get_bool("ForceAutoTune"),
    "ForceAutoTuneOff": params.get_bool("ForceAutoTuneOff"),
    "UseAutoSteerDelay": params.get_bool("UseAutoSteerDelay"),
    "SteerDelay": params.get_float("SteerDelay", return_default=True, default=stock_delay) if advanced_enabled else stock_delay,
    "SteerFriction": params.get_float("SteerFriction", return_default=True, default=stock_friction) if advanced_enabled else stock_friction,
    "SteerKP": params.get_float("SteerKP", return_default=True, default=KP) if advanced_enabled else KP,
    "SteerLatAccel": params.get_float("SteerLatAccel", return_default=True, default=stock_lat_accel) if advanced_enabled else stock_lat_accel,
    "SteerRatio": params.get_float("SteerRatio", return_default=True, default=stock_ratio) if advanced_enabled else stock_ratio,
    "FLMActiveProfileId": params.get("FLMActiveProfileId", encoding="utf-8") or "",
    "FLMActiveOverrides": normalize_flm_overrides(params.get("FLMActiveOverrides", encoding="utf-8") or "{}"),
    "FLMTrialApplied": params.get_bool("FLMTrialApplied"),
  }


def _stock_param_state(CP, capabilities: dict[str, Any]) -> dict[str, Any]:
  torque_tune = CP.lateralTuning.torque if CP.lateralTuning.which() == "torque" else None
  friction_family = str(capabilities.get("frictionFamily", "standard"))
  rich_profile = capabilities.get("richProfileKey")
  rich_knobs = {
    symbol: float(meta["defaultValue"])
    for symbol, meta in get_flm_supported_vehicle_knobs().items()
    if rich_profile and meta.get("profile") == rich_profile
  }
  return {
    "UseAutoSteerDelay": True,
    "SteerDelay": full_lateral_delay(float(getattr(CP, "steerActuatorDelay", 0.0) or 0.0)),
    "SteerFriction": float(getattr(torque_tune, "friction", 0.0) or 0.0) if torque_tune is not None else 0.0,
    "SteerKP": float(KP),
    "SteerLatAccel": float(getattr(torque_tune, "latAccelFactor", 0.0) or 0.0) if torque_tune is not None else 0.0,
    "SteerRatio": float(getattr(CP, "steerRatio", 0.0) or 0.0),
    "FLMBaseFrictionThresholds": {
      friction_family: {
        "speedKnots": list(FLM_FRICTION_SPEED_KNOTS),
        "values": _baseline_family_curve(friction_family),
      },
    } if torque_tune is not None else {},
    "FLMVehicleKnobs": rich_knobs,
  }


def _nonlinear_torque_map(CP) -> dict[str, Any]:
  if str(getattr(CP, "brand", "") or "") != "gm":
    return {}

  try:
    from opendbc.car.gm.interface import NON_LINEAR_TORQUE_PARAM_ALIASES, get_nonlinear_torque_params
  except (ImportError, AttributeError):
    return {}

  raw_params = get_nonlinear_torque_params(CP.carFingerprint)
  if raw_params is None:
    return {}

  if isinstance(raw_params, dict):
    left = [float(value) for value in raw_params.get("left", [])]
    right = [float(value) for value in raw_params.get("right", [])]
  else:
    left = [float(value) for value in raw_params]
    right = list(left)

  if len(left) != 4 or len(right) != 4:
    return {}

  return {
    "type": "siglin",
    "left": left,
    "right": right,
    "asymmetric": any(not math.isclose(left[idx], right[idx], abs_tol=1e-9) for idx in range(4)),
    "sourceFingerprint": str(NON_LINEAR_TORQUE_PARAM_ALIASES.get(CP.carFingerprint, CP.carFingerprint)),
    "learnedByLiveTorque": False,
  }


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


def classify_torque_samples(samples: list[FLMSample]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
  return _build_event_summaries(samples)


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
      return {"type": "generic_param", "paramKey": "SteerLatAccel", "current": current_value, "suggested": suggested_value, "delta": round(suggested_value - current_value, 4)}

    if bucket in ("oversteer", "early_turn_in"):
      if asymmetric_nonlinear_map and direction in ("left", "right") and supports_ff_gain:
        adjustment = _vehicle_knob_adjustment(f"{rich_profile}.ff_gain_{side}", -0.025 * severity, current)
        if adjustment is not None:
          return adjustment
      current_value = float(current["SteerLatAccel"])
      suggested_value = round(_clamp(current_value - max(0.03, current_value * 0.03 * severity), 0.5, 5.0), 4)
      return {"type": "generic_param", "paramKey": "SteerLatAccel", "current": current_value, "suggested": suggested_value, "delta": round(suggested_value - current_value, 4)}

    if bucket in ("unwind_too_slow", "unwind_too_fast"):
      current_value = float(current["SteerFriction"])
      direction_mult = -1.0 if bucket == "unwind_too_slow" else 1.0
      suggested_value = round(_clamp(current_value + (0.015 * severity * direction_mult), 0.0, 1.0), 4)
      return {"type": "generic_param", "paramKey": "SteerFriction", "current": current_value, "suggested": suggested_value, "delta": round(suggested_value - current_value, 4)}

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
    return {"type": "generic_param", "paramKey": "SteerLatAccel", "current": current_value, "suggested": suggested_value, "delta": round(suggested_value - current_value, 4)}

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
    return {"type": "generic_param", "paramKey": "SteerLatAccel", "current": current_value, "suggested": suggested_value, "delta": round(suggested_value - current_value, 4)}

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
    return {"type": "generic_param", "paramKey": "SteerFriction", "current": current_value, "suggested": suggested_value, "delta": round(suggested_value - current_value, 4)}

  if bucket == "saturation_limited":
    if curvy_band and supports_curvy_unwind_floor:
      adjustment = _vehicle_knob_adjustment(f"{rich_profile}.curvy_unwind_floor_relief_{side}", 0.04 * severity, current)
      if adjustment is not None:
        return adjustment
    current_value = float(current["SteerLatAccel"])
    suggested_value = round(_clamp(current_value + max(0.04, current_value * 0.04 * severity), 0.5, 5.0), 4)
    return {"type": "generic_param", "paramKey": "SteerLatAccel", "current": current_value, "suggested": suggested_value, "delta": round(suggested_value - current_value, 4)}

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
    return "This looks more like a friction-threshold problem than a whole-tune problem; the controller is busy around center and needs a calmer deadzone slope."
  if adjustment["type"] == "vehicle_knob":
    symbol = adjustment["symbol"]
    if "center_deadband_" in symbol:
      return (
        "A friction-threshold pass is already active in this speed band, but controller-driven reversals remain. "
        "The residual motion is narrow enough for a small deadband cleanup instead of another broad friction increase."
      )
    if "ff_gain_" in symbol:
      return "This car has a directional nonlinear torque map, and the mismatch is concentrated on one side. Correct that side's feedforward layer before moving global authority."
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
        "This adds a small steering-angle deadband only around the affected speed knot, interpolated into neighboring speeds, "
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
        "Do not raise the whole friction curve again or reduce global feedforward. "
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
        "If chatter remains after this threshold pass, re-analyze the next drive. FLM will move to a bounded deadband cleanup "
        "for the same speed band rather than repeatedly raising the whole threshold curve."
      )
    if adjustment.get("stage") == "center_deadband":
      return (
        "If steering becomes reluctant around center, use the conservative profile or halve this deadband step; "
        "leave the completed friction-threshold pass in place."
      )
  if strategy == "baseline":
    return f"If this gets the car broadly closer but leaves one specific phase ugly, stop here and switch to Cleanup Pass for that band. {_why_this_knob(adjustment)}"
  return f"If this cleans up the main symptom but introduces the opposite behavior, keep half the change and move to the next phase-specific knob. {_why_this_knob(adjustment)}"


def _log_support(summary: dict[str, Any]) -> str:
  evidence = summary.get("evidence", {})
  segment_labels = ", ".join(item["label"] for item in evidence.get("segments", [])[:3]) or "none"
  base = f"Matched in {evidence.get('eventCount', 0)} event(s); strongest samples: {segment_labels}"
  metrics = evidence.get("chatterMetrics", {})
  if summary.get("bucket") != "center_chatter" or not metrics:
    return base

  return (
    f"{base}. Strongest window: steering moved {metrics.get('steeringAngleP2P', 0.0):.2f} deg peak-to-peak "
    f"with {metrics.get('steeringReversals', 0)} steering reversal(s) and {metrics.get('outputReversals', 0)} output reversal(s), "
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
      "reason": "Overall lateral-accel tracking is already strong. The remaining misses are isolated enough that changing the base tune would disturb more good behavior than it fixes.",
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
      "reason": "This route looks broadly wrong across enough bands that the right first move is to fix base authority and friction behavior before touching narrower cleanup layers.",
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
        "This vehicle already progressed to Cleanup Pass. This route contains broader misses, but FLM will not automatically "
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
  ignored = set(str(item) for item in feedback.get("ignoredDimensions", []))
  accepted = set(str(item) for item in feedback.get("acceptedDimensions", []))
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


def _add_parameters_start_here(capabilities: dict[str, Any], suggestions: list[dict[str, Any]], primary_path_key: str) -> list[str]:
  lines = ["Turn on Advanced Lateral Tune before trying any suggested profile."]
  if primary_path_key == "baseline_fix":
    lines.append("This route looks broadly wrong enough that the first move should be a baseline fix, not a surgical cleanup pass.")
    lines.append("Start with the broad knobs this report suggests. Once the car is in the right zip code, re-run analysis and switch to Cleanup Pass for the leftovers.")
  else:
    lines.append("This route is already mostly in the right zip code, so start with cleanup changes before reaching for broader whole-car adjustments.")

  if any(suggestion.get("primaryAdjustmentRaw", {}).get("type") == "generic_param" for suggestion in suggestions if suggestion.get("primaryAdjustmentRaw")):
    lines.append("Generic advanced lateral params are in play on this pass, so apply those first before deciding you need deeper code-level changes.")
  if any(suggestion.get("primaryAdjustmentRaw", {}).get("type") == "friction_curve" for suggestion in suggestions if suggestion.get("primaryAdjustmentRaw")):
    lines.append("Friction-threshold changes are active in this pass because the logs point to small-signal steering behavior, not just whole-tune authority.")
  if not capabilities.get("richProfileKey"):
    lines.append("This car does not expose richer live FLM knobs yet, so generic advanced params and friction-threshold trials are the first code-level moves to test.")
  return lines


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


def _render_report_html(report: dict[str, Any]) -> str:
  report_paths = [path for path in report.get("paths", []) if isinstance(path, dict)]
  selected_path_key = str(report.get("selectedPathKey") or report.get("primaryPathKey") or "")
  primary_path = next((path for path in report_paths if path.get("key") == selected_path_key), None)
  if primary_path is None:
    primary_path = next((path for path in report_paths if path.get("isPrimary")), report_paths[0] if report_paths else {})
  findings_html = []
  for suggestion in report.get("suggestions", []):
    evidence = suggestion.get("evidence", {})
    current_vs_suggested = suggestion.get("currentVsSuggested")
    if current_vs_suggested is None:
      delta_html = "<p class='flm-muted'>No trial adjustment suggested for this dimension.</p>"
    elif current_vs_suggested["type"] == "friction_curve":
      delta_html = (
        f"<p><strong>Current:</strong> {current_vs_suggested['current']}</p>"
        f"<p><strong>Suggested:</strong> {current_vs_suggested['suggested']}</p>"
      )
    else:
      label = current_vs_suggested.get("paramKey") or current_vs_suggested.get("symbol")
      delta_html = (
        f"<p><strong>{label}</strong>: {float(current_vs_suggested['current']):.3f} -> {float(current_vs_suggested['suggested']):.3f}</p>"
      )
    findings_html.append(
      "<section class='flm-card'>"
      f"<h3>{suggestion['bucket'].replace('_', ' ').title()}</h3>"
      f"<p><strong>Observed behavior:</strong> {suggestion['observedBehavior']}</p>"
      f"<p><strong>Likely interpretation:</strong> {suggestion['likelyInterpretation']}</p>"
      f"<p><strong>Primary adjustment:</strong> {suggestion['primaryAdjustment']}</p>"
      f"<p><strong>What not to touch yet:</strong> {suggestion['whatNotToTouchYet']}</p>"
      f"<p><strong>If that was wrong, next thing to try:</strong> {suggestion['ifThatWasWrong']}</p>"
      f"<p><strong>Evidence:</strong> speed={evidence.get('speedBand', 'mixed')}, direction={evidence.get('directionBias', 'center')}, events={evidence.get('eventCount', 0)}</p>"
      f"<p><strong>Strongest segments:</strong> {', '.join(item['label'] for item in evidence.get('segments', [])[:3]) or 'none'}</p>"
      f"{delta_html}"
      f"{suggestion.get('plotSvg', '')}"
      "</section>"
    )

  path_html = []
  for path in report_paths:
    badges = []
    if path.get("isPrimary"):
      badges.append("Analyzer recommended")
    if path.get("key") == selected_path_key:
      badges.append("Active")
    badge = " / ".join(badges) or "Alternate"
    path_html.append(
      "<section class='flm-card'>"
      f"<h3>{path.get('title', 'Path')}</h3>"
      f"<p><strong>{badge}:</strong> {path.get('description', '')}</p>"
      f"<p><strong>Why this path:</strong> {path.get('whySelected', '')}</p>"
      f"<p><strong>When to use it:</strong> {path.get('whenToUse', '')}</p>"
      "</section>"
    )

  profile_html = []
  for path in report_paths:
    path_profiles = path.get("profiles", [])
    cards = []
    for profile in path_profiles:
      generic_lines = []
      for key, value in profile.get("genericParams", {}).items():
        if key == "AdvancedLateralTune":
          continue
        generic_lines.append(f"<li><code>{key}</code>: {value}</li>")
      override_lines = []
      for family, payload in profile.get("flmOverrides", {}).get("baseFrictionThresholds", {}).items():
        override_lines.append(f"<li><code>{family}</code> curve: {payload.get('values', [])}</li>")
      for key, value in profile.get("flmOverrides", {}).get("vehicleKnobs", {}).items():
        override_lines.append(f"<li><code>{key}</code>: {value}</li>")
      cards.append(
        "<section class='flm-card'>"
        f"<h3>{profile['label']}</h3>"
        f"<p>{profile['description']}</p>"
        f"<p><strong>Generic params:</strong></p><ul>{''.join(generic_lines) or '<li>None</li>'}</ul>"
        f"<p><strong>FLM overrides:</strong></p><ul>{''.join(override_lines) or '<li>None</li>'}</ul>"
        "</section>"
      )
    path_profiles_html = "".join(cards) or "<p class='flm-muted'>No trial profiles generated for this path.</p>"
    profile_html.append(
      f"<h3>{path.get('title', 'Path')} Profiles</h3>"
      f"{path_profiles_html}"
    )

  start_here_lines = "".join(f"<li>{line}</li>" for line in report.get("addTheseParametersAndStartHere", []))
  start_here_html = f"<section class='flm-card'><h3>Add These Parameters And Start Here</h3><ul>{start_here_lines}</ul></section>" if start_here_lines else ""
  findings_block = "".join(findings_html) or "<p class='flm-muted'>No strong findings.</p>"
  profiles_block = "".join(profile_html) or "<p class='flm-muted'>No trial profiles generated.</p>"
  return (
    "<!doctype html><html><head><meta charset='utf-8'>"
    "<title>FLM Tuning Report</title>"
    "<style>"
    "body{font-family:system-ui,sans-serif;background:#020617;color:#e2e8f0;margin:0;padding:24px;}"
    ".flm-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;}"
    ".flm-card{background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:16px;margin-bottom:16px;}"
    ".flm-muted{color:#94a3b8;}"
    "code{background:#111827;padding:2px 6px;border-radius:6px;}"
    ".flm-plot{width:100%;height:140px;margin-top:12px;}"
    "</style></head><body>"
    f"<h1>FLM Tuning Report</h1>"
    f"<p>{report['car']['carFingerprint']} | {report['car'].get('gitBranch', '')} {report['car'].get('gitCommit', '')}</p>"
    f"<div class='flm-grid'><section class='flm-card'><h3>Routes</h3><p>{', '.join(report.get('routeNames', []))}</p></section>"
    f"<section class='flm-card'><h3>Control Path</h3><p>{report['car'].get('controlPath', 'unknown')}</p></section>"
    f"<section class='flm-card'><h3>Friction Family</h3><p>{report['capabilities'].get('frictionFamily', 'standard')}</p></section>"
    f"<section class='flm-card'><h3>Nonlinear Torque Map</h3><p>{'Asymmetric left/right siglin' if report['capabilities'].get('nonlinearTorqueMap', {}).get('asymmetric') else ('Symmetric siglin' if report['capabilities'].get('nonlinearTorqueMap') else 'Not detected')}</p></section></div>"
    f"{''.join(path_html)}"
    f"{start_here_html}"
    f"<h2>Active Findings: {primary_path.get('title', 'Recommendations')}</h2>"
    f"{findings_block}"
    "<h2>Trial Profiles</h2>"
    f"{profiles_block}"
    "</body></html>"
  )


def analyze_routes(route_names: list[str], footage_paths: list[str], feedback: dict[str, Any] | None = None,
                   report_id: str | None = None, segment_ranges: dict[str, dict[str, int | None]] | None = None) -> dict[str, Any]:
  ensure_flm_workspace()
  params = Params(return_defaults=True)
  _require_flm_offroad(params)
  report_id = report_id or f"flm-{int(time.time())}"
  feedback = feedback or {}
  segment_ranges = normalize_segment_ranges(route_names, segment_ranges)

  sources, warnings = resolve_route_sources(route_names, footage_paths, segment_ranges)
  if not sources:
    raise RuntimeError("No local routes with qlogs or rlogs were found for the selected routes.")

  all_samples: list[FLMSample] = []
  car_params_candidates = []
  init_data: dict[str, str] = {}
  observed_control_states: dict[str, int] = {}
  used_qlog = False
  processed_segments = 0
  skipped_segments = 0
  last_skipped_segment = ""
  last_skip_reason = ""
  for idx, source in enumerate(sources, start=1):
    _require_flm_offroad(params)
    _write_flm_status({
      "pid": os.getpid(),
      "startedAt": time.time(),
      "running": True,
      "state": "analyzing",
      "routes": route_names,
      "segmentRanges": segment_ranges,
      "progress": idx - 1,
      "total": len(sources),
      "currentSegment": source.segment,
      "segmentTimeoutSeconds": FLM_SEGMENT_TIMEOUT_SECONDS,
      "skippedSegments": skipped_segments,
      "lastSkippedSegment": last_skipped_segment,
      "lastSkipReason": last_skip_reason,
    })
    try:
      segment_samples, segment_car_params, segment_init, segment_control_states = _segment_samples_with_timeout(source, params)
    except FLMAnalysisCancelled:
      raise
    except FLMSegmentTimeout as error:
      warnings.append(str(error) + " The segment was skipped.")
      skipped_segments += 1
      last_skipped_segment = source.segment
      last_skip_reason = str(error)
      _write_flm_status({
        "pid": os.getpid(),
        "startedAt": time.time(),
        "running": True,
        "state": "analyzing",
        "routes": route_names,
        "segmentRanges": segment_ranges,
        "progress": idx,
        "total": len(sources),
        "currentSegment": "",
        "segmentTimeoutSeconds": FLM_SEGMENT_TIMEOUT_SECONDS,
        "skippedSegments": skipped_segments,
        "lastSkippedSegment": last_skipped_segment,
        "lastSkipReason": last_skip_reason,
      })
      continue
    except Exception as error:
      last_skipped_segment = source.segment
      last_skip_reason = f"Could not be read ({type(error).__name__})."
      warnings.append(f"{source.route} segment {source.segment_num} {last_skip_reason} The segment was skipped.")
      skipped_segments += 1
      continue
    _require_flm_offroad(params)
    if segment_car_params is not None:
      car_params_candidates.append(segment_car_params)
    if segment_init and not init_data:
      init_data = segment_init
    for state_name, count in segment_control_states.items():
      observed_control_states[state_name] = observed_control_states.get(state_name, 0) + count
    if source.used_qlog:
      used_qlog = True
    all_samples.extend(segment_samples)
    processed_segments += 1

  if not car_params_candidates:
    raise RuntimeError("No carParams were found in the selected routes.")

  _require_flm_offroad(params)
  car_params = car_params_candidates[-1]
  control_path, control_path_source = _effective_control_path(car_params, observed_control_states)
  matching_car_params = [candidate for candidate in car_params_candidates if _car_params_control_path(candidate) == control_path]
  if matching_car_params:
    car_params = matching_car_params[-1]
  if control_path == "torque":
    car_params = _effective_torque_car_params(car_params)
  torque_control = control_path == "torque"
  hyundai_canfd = bool(getattr(car_params, "flags", 0) & HyundaiFlags.CANFD)
  capabilities = get_flm_capabilities(
    car_params.carFingerprint,
    brand=str(getattr(car_params, "brand", "") or ""),
    hyundai_canfd=hyundai_canfd,
    torque_control=torque_control,
  )
  capabilities = dict(capabilities)
  capabilities["nonlinearTorqueMap"] = _nonlinear_torque_map(car_params)
  current_params = _current_param_state(car_params, params)
  stock_params = _stock_param_state(car_params, capabilities)
  car_fingerprint = str(car_params.carFingerprint)

  if torque_control:
    raw_summaries, summary_stats = classify_torque_samples(all_samples)
    summaries = _resolve_conflicting_actionable_suggestions(raw_summaries)
    cleanup_progress_locked = _cleanup_progress_locked(car_fingerprint)
    paths_payload, path_decision = build_recommendation_paths(
      report_id,
      summaries,
      summary_stats,
      capabilities,
      current_params,
      feedback,
      cleanup_progress_locked=cleanup_progress_locked,
    )
    primary_path = next((path for path in paths_payload if path.get("isPrimary")), paths_payload[0] if paths_payload else {})
    suggestions = list(primary_path.get("suggestions", []))
    profiles = [profile for path in paths_payload for profile in path.get("profiles", [])]
  else:
    force_torque_requested = init_data.get("ForceTorqueController", "").strip().lower() in ("1", "true", "yes", "on")
    if control_path == "pid":
      observed_behavior = "This route logged the PID lateral controller, so torque-specific FLM trial profiles do not apply to this drive."
      likely_interpretation = (
        "Force Torque Controller was stored, but this route still ran PID. "
        + "That override is applied at startup; reboot and record a fresh route before analyzing it."
        if force_torque_requested else
        "This Honda uses torque steering commands, but the software controller in this route was PID. "
        + "Enable Force Torque Controller, reboot, then record a fresh route."
      )
      primary_adjustment = "Run FLM again on a route that logs torqueState."
      what_not_to_touch = "Do not apply torque-controller trial values to PID data."
    elif control_path == "mixed":
      observed_behavior = "The selected routes contain more than one lateral controller path."
      likely_interpretation = "Torque, PID, or angle-controller samples were mixed together, so one tune cannot be inferred safely."
      primary_adjustment = "Analyze routes from one controller configuration at a time."
      what_not_to_touch = "Do not generate one torque profile from mixed controller data."
    else:
      observed_behavior = "This route logged an angle-control path, so torque-specific FLM trial profiles do not apply."
      likely_interpretation = "A true angle-command path cannot be converted into torque control by the Force Torque Controller setting."
      primary_adjustment = "Keep this route in diagnostic-only mode."
      what_not_to_touch = "Do not write torque-controller override blobs for an angle-control path."

    summary_stats = {
      "sampleCount": len(all_samples),
      "qlogFallback": used_qlog,
      "observedLateralControlStates": observed_control_states,
    }
    summaries = [{
      "bucket": "controller_path_diagnostic",
      "dimensionId": "controller_path_diagnostic:overall",
      "direction": "center",
      "speedBand": "mixed",
      "count": 1,
      "severity": 0.0,
      "evidence": {"speedBand": "mixed", "directionBias": "center", "eventCount": 1, "segments": []},
      "events": [],
      "plotSvg": "",
      "plotData": {},
    }]
    suggestions = [{
      "dimensionId": "controller_path_diagnostic:overall",
      "bucket": "controller_path_diagnostic",
      "evidence": summaries[0]["evidence"],
      "currentVsSuggested": None,
      "observedBehavior": observed_behavior,
      "likelyInterpretation": likely_interpretation,
      "primaryAdjustment": primary_adjustment,
      "whatNotToTouchYet": what_not_to_touch,
      "ifThatWasWrong": "If the route actually ran torque control, verify it contains torqueState and re-run FLM on that fresh route.",
      "plotSvg": "",
      "plotData": {},
    }]
    path_decision = {
      "primaryPathKey": "cleanup_pass",
      "alternatePathKey": "baseline_fix",
      "reason": f"{control_path.title()} controller data does not participate in the torque trial workflow.",
      "baselineScore": 0,
    }
    paths_payload = [{
      "key": "cleanup_pass",
      "title": "Diagnostic Only",
      "description": observed_behavior,
      "whenToUse": "Use this report only for diagnostic review.",
      "alternateHint": "",
      "isPrimary": True,
      "whySelected": path_decision["reason"],
      "suggestions": suggestions,
      "profiles": [],
    }]
    profiles = []

  report = {
    "reportId": report_id,
    "createdAt": time.time(),
    "routeNames": route_names,
    "segmentRanges": segment_ranges,
    "warnings": warnings,
    "feedback": feedback,
    "car": {
      "carFingerprint": car_fingerprint,
      "brand": str(getattr(car_params, "brand", "") or ""),
      "controlPath": control_path,
      "controlPathSource": control_path_source,
      "observedLateralControlStates": observed_control_states,
      "gitBranch": init_data.get("gitBranch", ""),
      "gitCommit": init_data.get("gitCommit", ""),
      "steerControlType": str(getattr(car_params, "steerControlType", car.CarParams.SteerControlType.torque)),
    },
    "capabilities": capabilities,
    "stockParams": stock_params,
    "currentParams": current_params,
    "summary": {
      **summary_stats,
      "processedSegments": processed_segments,
      "skippedSegments": skipped_segments,
      "usedQlogFallback": used_qlog,
    },
    "primaryPathKey": path_decision["primaryPathKey"],
    "selectedPathKey": path_decision["primaryPathKey"],
    "pathSelectionSource": "auto",
    "pathDecision": path_decision,
    "paths": paths_payload,
    "findings": summaries,
    "rawFindings": raw_summaries if torque_control else summaries,
    "suggestions": suggestions,
    "profiles": profiles,
    "addTheseParametersAndStartHere": _add_parameters_start_here(capabilities, suggestions, path_decision["primaryPathKey"]),
  }

  _require_flm_offroad(params)
  paths = ensure_flm_workspace()
  html = _render_report_html(report)
  _require_flm_offroad(params)
  report["htmlPath"] = str(paths["reports"] / f"{report_id}.html")
  report["jsonPath"] = str(paths["reports"] / f"{report_id}.json")
  (paths["reports"] / f"{report_id}.html").write_text(html, encoding="utf-8")
  _write_json(paths["reports"] / f"{report_id}.json", report)
  _write_json(paths["profiles"] / f"{report_id}.json", profiles)
  if torque_control and path_decision["primaryPathKey"] == "cleanup_pass":
    _record_cleanup_progress(car_fingerprint, report_id)
  _write_flm_status({
    "pid": os.getpid(),
    "startedAt": time.time(),
    "running": False,
    "state": "complete",
    "routes": route_names,
    "segmentRanges": segment_ranges,
    "progress": len(sources),
    "total": len(sources),
    "skippedSegments": skipped_segments,
    "reportId": report_id,
  })
  return report


def load_report(report_id: str) -> dict[str, Any]:
  paths = ensure_flm_workspace()
  report_path = paths["reports"] / f"{report_id}.json"
  report = _read_json(report_path, {})
  if not isinstance(report, dict) or not report:
    raise FileNotFoundError(report_id)
  html_path = paths["reports"] / f"{report_id}.html"
  report["html"] = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
  return report


def select_report_path(report_id: str, path_key: str) -> dict[str, Any]:
  paths = ensure_flm_workspace()
  report = load_report(report_id)
  report_paths = [path for path in report.get("paths", []) if isinstance(path, dict)]
  selected_path = next((path for path in report_paths if path.get("key") == path_key), None)
  if selected_path is None:
    raise ValueError(f"Unknown FLM path: {path_key}")

  report["selectedPathKey"] = path_key
  report["pathSelectionSource"] = "manual"
  report["suggestions"] = list(selected_path.get("suggestions", []))
  report["addTheseParametersAndStartHere"] = _add_parameters_start_here(
    report.get("capabilities", {}),
    report["suggestions"],
    path_key,
  )
  report.pop("html", None)
  (paths["reports"] / f"{report_id}.html").write_text(_render_report_html(report), encoding="utf-8")
  _write_json(paths["reports"] / f"{report_id}.json", report)
  if path_key == "cleanup_pass" and report.get("car", {}).get("controlPath") == "torque":
    _record_cleanup_progress(str(report.get("car", {}).get("carFingerprint", "")), report_id)
  return {
    "message": f"Using {selected_path.get('title', path_key)} for this report.",
    "report": load_report(report_id),
  }


def _active_trial_display_state(paths: dict[str, Path], snapshot: Any) -> dict[str, Any] | None:
  if not isinstance(snapshot, dict) or not snapshot:
    return None
  if "appliedGenericParams" in snapshot:
    return snapshot

  report_id = str(snapshot.get("reportId", "") or "")
  profile_id = str(snapshot.get("profileId", "") or "")
  profiles = _read_json(paths["profiles"] / f"{report_id}.json", []) if report_id else []
  profile = next((
    item for item in profiles
    if isinstance(item, dict) and item.get("id") == profile_id
  ), None) if isinstance(profiles, list) else None
  if profile is None:
    return snapshot

  generic_params = dict(profile.get("genericParams", {}))
  flm_overrides = normalize_flm_overrides(profile.get("flmOverrides", {}))
  return {
    **snapshot,
    "profileLabel": str(profile.get("label", "FLM") or "FLM"),
    "pathKey": str(profile.get("pathKey", "") or ""),
    "pathLabel": str(profile.get("pathLabel", "") or ""),
    "appliedGenericParams": {
      key: value for key, value in generic_params.items()
      if key in FLM_ADVANCED_LATERAL_PARAM_KEYS
    },
    "appliedFrictionThresholds": flm_overrides.get("baseFrictionThresholds", {}),
    "appliedVehicleKnobs": flm_overrides.get("vehicleKnobs", {}),
  }


def _current_car_identity(params: Params) -> dict[str, str]:
  cp_bytes = params.get("CarParamsPersistent")
  if not cp_bytes:
    return {"carFingerprint": "", "brand": ""}
  try:
    with car.CarParams.from_bytes(cp_bytes) as car_params:
      return {
        "carFingerprint": str(getattr(car_params, "carFingerprint", "") or "").strip(),
        "brand": str(getattr(car_params, "brand", "") or "").strip(),
      }
  except Exception:
    return {"carFingerprint": "", "brand": ""}


def _normalize_saved_tune_name(name: str) -> str:
  normalized = " ".join(str(name or "").split())
  if not normalized:
    raise ValueError("A saved tune name is required.")
  if len(normalized) > 64:
    raise ValueError("Saved tune names must be 64 characters or fewer.")
  return normalized


def _load_saved_tune(tune_id: str, paths: dict[str, Path] | None = None) -> dict[str, Any]:
  paths = paths or ensure_flm_workspace()
  tune = _read_json(paths["savedTunes"] / f"{tune_id}.json", {})
  if not isinstance(tune, dict) or not tune:
    raise FileNotFoundError(tune_id)
  return tune


def list_saved_tunes(paths: dict[str, Path] | None = None, active_tune_id: str = "") -> list[dict[str, Any]]:
  paths = paths or ensure_flm_workspace()
  saved_tunes = []
  for path in paths["savedTunes"].glob("*.json"):
    payload = _read_json(path, {})
    if not isinstance(payload, dict) or not payload:
      continue
    flm_overrides = normalize_flm_overrides(payload.get("flmOverrides", {}))
    saved_tunes.append({
      "tuneId": str(payload.get("tuneId", path.stem) or path.stem),
      "name": str(payload.get("name", "Saved Tune") or "Saved Tune"),
      "createdAt": float(payload.get("createdAt", path.stat().st_mtime) or path.stat().st_mtime),
      "updatedAt": float(payload.get("updatedAt", path.stat().st_mtime) or path.stat().st_mtime),
      "carFingerprint": str(payload.get("carFingerprint", "") or ""),
      "brand": str(payload.get("brand", "") or ""),
      "sourceReportId": str(payload.get("sourceReportId", "") or ""),
      "pathLabel": str(payload.get("pathLabel", "") or ""),
      "genericParamCount": len(payload.get("genericParams", {})) if isinstance(payload.get("genericParams"), dict) else 0,
      "frictionCurveCount": len(flm_overrides.get("baseFrictionThresholds", {})),
      "vehicleKnobCount": len(flm_overrides.get("vehicleKnobs", {})),
      "active": str(payload.get("tuneId", path.stem) or path.stem) == active_tune_id,
    })
  return sorted(saved_tunes, key=lambda tune: (tune["updatedAt"], tune["createdAt"]), reverse=True)


def list_workspace() -> dict[str, Any]:
  paths = ensure_flm_workspace()
  reports = []
  for path in sorted(paths["reports"].glob("*.json"), reverse=True):
    payload = _read_json(path, {})
    if not isinstance(payload, dict) or not payload:
      continue
    reports.append({
      "reportId": payload.get("reportId", path.stem),
      "createdAt": payload.get("createdAt", path.stat().st_mtime),
      "carFingerprint": payload.get("car", {}).get("carFingerprint", ""),
      "routeNames": payload.get("routeNames", []),
      "controlPath": payload.get("car", {}).get("controlPath", ""),
    })
  feedback_files = sorted(paths["feedback"].glob("*.json"), reverse=True)
  params = Params(return_defaults=True)
  current_profile_id = params.get("FLMActiveProfileId", encoding="utf-8") or ""
  raw_active_snapshot = _read_json(paths["snapshots"] / "active.json", {})
  if params.get_bool("FLMTrialApplied"):
    active_payload = raw_active_snapshot if isinstance(raw_active_snapshot, dict) else {}
    baseline_snapshot = _find_revert_snapshot(paths, raw_active_snapshot, current_profile_id, params)
    if baseline_snapshot is not None:
      raw_active_snapshot = {
        **active_payload,
        "params": baseline_snapshot["params"],
        "profileId": current_profile_id or active_payload.get("profileId", ""),
        "recoveryNeeded": baseline_snapshot is not raw_active_snapshot,
        "rollbackAvailable": True,
      }
    else:
      raw_active_snapshot = {
        **active_payload,
        "profileId": current_profile_id or active_payload.get("profileId", ""),
        "recoveryNeeded": True,
        "rollbackAvailable": False,
      }
    if current_profile_id.startswith("saved:"):
      saved_tune_id = current_profile_id.split(":", 1)[1]
      saved_tune = _read_json(paths["savedTunes"] / f"{saved_tune_id}.json", {})
      if isinstance(saved_tune, dict) and saved_tune:
        saved_overrides = normalize_flm_overrides(saved_tune.get("flmOverrides", {}))
        raw_active_snapshot = {
          **raw_active_snapshot,
          "savedTuneId": saved_tune_id,
          "profileLabel": str(saved_tune.get("name", "Saved Tune") or "Saved Tune"),
          "carFingerprint": str(saved_tune.get("carFingerprint", "") or ""),
          "appliedGenericParams": dict(saved_tune.get("genericParams", {})),
          "appliedFrictionThresholds": saved_overrides.get("baseFrictionThresholds", {}),
          "appliedVehicleKnobs": saved_overrides.get("vehicleKnobs", {}),
        }
  active_snapshot = _active_trial_display_state(paths, raw_active_snapshot)
  active_tune_id = str(active_snapshot.get("savedTuneId", "") or "") if isinstance(active_snapshot, dict) else ""
  current_car = _current_car_identity(params)
  return {
    "reports": reports[:20],
    "savedTunes": list_saved_tunes(paths, active_tune_id),
    "currentCarFingerprint": current_car["carFingerprint"],
    "feedbackCount": len(feedback_files),
    "activeTrial": active_snapshot,
    "status": read_flm_status(),
  }


def delete_report(report_id: str) -> dict[str, Any]:
  paths = ensure_flm_workspace()
  params = Params(return_defaults=True)
  if params.get_bool("FLMTrialApplied"):
    raise RuntimeError("Revert or keep the active FLM trial before deleting tuning reports.")
  active_snapshot = _read_json(paths["snapshots"] / "active.json", {})
  if isinstance(active_snapshot, dict) and active_snapshot.get("reportId") == report_id:
    raise RuntimeError("Revert the active FLM trial before deleting its source report.")

  removed = []
  direct_paths = [
    paths["reports"] / f"{report_id}.json",
    paths["reports"] / f"{report_id}.html",
    paths["profiles"] / f"{report_id}.json",
    paths["feedback"] / f"{report_id}.json",
  ]
  for path in direct_paths:
    if path.exists():
      path.unlink()
      removed.append(str(path))

  for path in paths["snapshots"].glob(f"{report_id}-*.json"):
    path.unlink()
    removed.append(str(path))

  if not removed:
    raise FileNotFoundError(report_id)

  status = read_flm_status()
  if not status.get("running") and status.get("reportId") == report_id:
    clear_flm_status()

  return {
    "message": f"Deleted tuning report {report_id}.",
    "removed": removed,
    "workspace": list_workspace(),
  }


def clear_workspace() -> dict[str, Any]:
  paths = ensure_flm_workspace()
  status = read_flm_status()
  if status.get("running"):
    raise RuntimeError("Stop the active FLM analysis before clearing the workspace.")

  params = Params(return_defaults=True)
  active_snapshot = _read_json(paths["snapshots"] / "active.json", {})
  if params.get_bool("FLMTrialApplied") or (isinstance(active_snapshot, dict) and active_snapshot.get("params")):
    params.put_bool("FLMTrialApplied", False)
    params.put("FLMActiveProfileId", "")
    params.put("FLMActiveOverrides", {})
    _clear_persistent_trial_baseline(params)
    Params(memory=True).put_bool("StarPilotTogglesUpdated", True)

  removed = []
  for key in ("reports", "profiles", "feedback", "snapshots"):
    for path in paths[key].glob("*"):
      if path.is_file():
        path.unlink()
        removed.append(str(path))

  progress_path = _progress_path()
  if progress_path.is_file():
    progress_path.unlink()
    removed.append(str(progress_path))

  _clear_persistent_trial_baseline(params)
  clear_flm_status()

  return {
    "message": "Cleared saved tuning reports, feedback, profiles, and snapshots.",
    "removedCount": len(removed),
    "workspace": list_workspace(),
  }


def _snapshot_current_trial_state(params: Params) -> dict[str, Any]:
  snapshot = {}
  for key, kind in TRIAL_PARAM_SPECS.items():
    if kind == "bool":
      snapshot[key] = params.get_bool(key)
    elif kind == "float":
      snapshot[key] = params.get_float(key, return_default=True)
    elif kind == "json":
      snapshot[key] = normalize_flm_overrides(params.get(key, encoding="utf-8") or "{}")
    else:
      snapshot[key] = params.get(key, encoding="utf-8") or ""
  return snapshot


def _read_persistent_trial_baseline(params: Params) -> dict[str, Any] | None:
  raw = params.get(FLM_TRIAL_BASELINE_PARAM, encoding="utf-8") or {}
  if isinstance(raw, str):
    try:
      raw = json.loads(raw)
    except (TypeError, ValueError):
      return None
  if not isinstance(raw, dict) or not isinstance(raw.get("params"), dict):
    return None
  if raw["params"].get("FLMTrialApplied", False):
    return None
  return raw


def _persist_trial_baseline(params: Params, snapshot: dict[str, Any]) -> None:
  if isinstance(snapshot.get("params"), dict) and not snapshot["params"].get("FLMTrialApplied", False):
    params.put(FLM_TRIAL_BASELINE_PARAM, snapshot)


def _clear_persistent_trial_baseline(params: Params) -> None:
  params.remove(FLM_TRIAL_BASELINE_PARAM)


def _profile_report_id(profile_id: str) -> str:
  return str(profile_id or "").split(":", 1)[0]


def _recover_report_baseline(paths: dict[str, Path], profile_id: str,
                             visited_profiles: set[str] | None = None) -> dict[str, Any] | None:
  profile_id = str(profile_id or "")
  if not profile_id:
    return None

  visited_profiles = set(visited_profiles or set())
  if profile_id in visited_profiles:
    return None
  visited_profiles.add(profile_id)

  report_id = _profile_report_id(profile_id)
  report = _read_json(paths["reports"] / f"{report_id}.json", {})
  report_params = report.get("currentParams") if isinstance(report, dict) else None
  if not isinstance(report_params, dict) or not report_params:
    return None

  baseline_params = {
    key: value for key, value in report_params.items()
    if key in TRIAL_PARAM_SPECS
  }
  if not baseline_params:
    return None
  if not baseline_params.get("FLMTrialApplied", False):
    baseline_params["FLMTrialApplied"] = False
    baseline_params.setdefault("FLMActiveProfileId", "")
    return {
      "reportId": report_id,
      "profileId": profile_id,
      "capturedAt": float(report.get("createdAt", 0.0) or 0.0),
      "params": baseline_params,
      "recoverySource": "report",
    }

  previous_profile_id = str(baseline_params.get("FLMActiveProfileId", "") or "")
  if previous_profile_id and previous_profile_id != profile_id:
    return _recover_report_baseline(paths, previous_profile_id, visited_profiles)
  return None


def _apply_param_bundle(params: Params, bundle: dict[str, Any]) -> None:
  for key, value in bundle.items():
    kind = TRIAL_PARAM_SPECS.get(key)
    if kind == "bool":
      params.put_bool(key, bool(value))
    elif kind == "float":
      params.put_float(key, float(value))
    elif kind == "json":
      params.put(key, normalize_flm_overrides(value))
    elif kind == "string":
      params.put(key, str(value or ""))

  Params(memory=True).put_bool("StarPilotTogglesUpdated", True)


def _merge_flm_override_state(base: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
  base = normalize_flm_overrides(base)
  delta = normalize_flm_overrides(delta)
  merged = {
    "schemaVersion": 1,
    "baseFrictionThresholds": {
      **base.get("baseFrictionThresholds", {}),
      **delta.get("baseFrictionThresholds", {}),
    },
    "vehicleKnobs": {
      **base.get("vehicleKnobs", {}),
      **delta.get("vehicleKnobs", {}),
    },
  }
  return normalize_flm_overrides(merged)


def _find_revert_snapshot(paths: dict[str, Path], active_snapshot: dict[str, Any],
                          current_profile_id: str = "", params: Params | None = None) -> dict[str, Any] | None:
  if isinstance(active_snapshot, dict) and isinstance(active_snapshot.get("params"), dict):
    if not active_snapshot["params"].get("FLMTrialApplied", False):
      return active_snapshot

  if params is not None:
    persistent_baseline = _read_persistent_trial_baseline(params)
    if persistent_baseline is not None:
      return persistent_baseline

  cutoff = float(active_snapshot.get("capturedAt", math.inf) or math.inf) if isinstance(active_snapshot, dict) else math.inf
  candidates = []
  for path in paths["snapshots"].glob("*.json"):
    if path.name == "active.json":
      continue
    candidate = _read_json(path, {})
    candidate_params = candidate.get("params", {}) if isinstance(candidate, dict) else {}
    if not isinstance(candidate_params, dict) or candidate_params.get("FLMTrialApplied", False):
      continue
    captured_at = float(candidate.get("capturedAt", 0.0) or 0.0)
    if captured_at > cutoff:
      continue
    candidates.append(candidate)

  if candidates:
    matching = [candidate for candidate in candidates if current_profile_id and candidate.get("profileId") == current_profile_id]
    pool = matching or candidates
    return max(pool, key=lambda candidate: float(candidate.get("capturedAt", 0.0) or 0.0))

  return _recover_report_baseline(paths, current_profile_id)


def _active_trial_adjustments(paths: dict[str, Path], params: Params,
                              active_snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
  current_state = _snapshot_current_trial_state(params)
  display_state = _active_trial_display_state(paths, active_snapshot) or {}
  baseline_snapshot = _find_revert_snapshot(
    paths,
    active_snapshot,
    str(current_state.get("FLMActiveProfileId", "") or ""),
    params,
  )
  baseline_params = baseline_snapshot.get("params", {}) if isinstance(baseline_snapshot, dict) else {}

  generic_params = {}
  display_generic = display_state.get("appliedGenericParams", {})
  if not isinstance(display_generic, dict):
    display_generic = {}
  for key in FLM_ADVANCED_LATERAL_PARAM_KEYS:
    if key not in current_state:
      continue
    if key in baseline_params:
      if current_state[key] != baseline_params[key]:
        generic_params[key] = current_state[key]
    elif key in display_generic:
      generic_params[key] = current_state[key]

  current_overrides = normalize_flm_overrides(current_state.get("FLMActiveOverrides", {}))
  baseline_overrides = normalize_flm_overrides(baseline_params.get("FLMActiveOverrides", {}))
  display_friction = display_state.get("appliedFrictionThresholds", {})
  display_knobs = display_state.get("appliedVehicleKnobs", {})
  if not isinstance(display_friction, dict):
    display_friction = {}
  if not isinstance(display_knobs, dict):
    display_knobs = {}

  friction_thresholds = {}
  for family, payload in current_overrides.get("baseFrictionThresholds", {}).items():
    if family in display_friction or payload != baseline_overrides.get("baseFrictionThresholds", {}).get(family):
      friction_thresholds[family] = payload
  vehicle_knobs = {}
  for symbol, value in current_overrides.get("vehicleKnobs", {}).items():
    if symbol in display_knobs or value != baseline_overrides.get("vehicleKnobs", {}).get(symbol):
      vehicle_knobs[symbol] = value

  return generic_params, normalize_flm_overrides({
    "schemaVersion": 1,
    "baseFrictionThresholds": friction_thresholds,
    "vehicleKnobs": vehicle_knobs,
  })


def _active_trial_car_fingerprint(paths: dict[str, Path], active_snapshot: dict[str, Any]) -> str:
  fingerprint = str(active_snapshot.get("carFingerprint", "") or "")
  if fingerprint:
    return fingerprint
  report_id = str(active_snapshot.get("reportId", "") or "")
  report = _read_json(paths["reports"] / f"{report_id}.json", {}) if report_id else {}
  return str(report.get("car", {}).get("carFingerprint", "") or "") if isinstance(report, dict) else ""


def save_active_trial_as_tune(name: str) -> dict[str, Any]:
  paths = ensure_flm_workspace()
  params = Params(return_defaults=True)
  if not params.get_bool("FLMTrialApplied"):
    raise RuntimeError("Apply an FLM trial before saving it as a tune.")

  active_snapshot = _read_json(paths["snapshots"] / "active.json", {})
  if not isinstance(active_snapshot, dict):
    active_snapshot = {}
  display_state = _active_trial_display_state(paths, active_snapshot) or {}
  generic_params, flm_overrides = _active_trial_adjustments(paths, params, active_snapshot)
  current_state = _snapshot_current_trial_state(params)
  baseline_snapshot = _find_revert_snapshot(
    paths,
    active_snapshot,
    str(current_state.get("FLMActiveProfileId", "") or ""),
    params,
  )
  baseline_params = dict(baseline_snapshot.get("params", {})) if isinstance(baseline_snapshot, dict) else {}
  report_id = str(display_state.get("reportId", "") or "")
  report = _read_json(paths["reports"] / f"{report_id}.json", {}) if report_id else {}
  report_car = report.get("car", {}) if isinstance(report, dict) else {}
  current_car = _current_car_identity(params)
  car_fingerprint = current_car["carFingerprint"] or str(report_car.get("carFingerprint", "") or "")
  brand = current_car["brand"] or str(report_car.get("brand", "") or "")
  now = time.time()
  tune_id = f"tune-{time.time_ns()}"
  tune = {
    "schemaVersion": 1,
    "tuneId": tune_id,
    "name": _normalize_saved_tune_name(name),
    "createdAt": now,
    "updatedAt": now,
    "carFingerprint": car_fingerprint,
    "brand": brand,
    "sourceReportId": report_id,
    "sourceProfileId": str(display_state.get("profileId", "") or ""),
    "pathKey": str(display_state.get("pathKey", "") or ""),
    "pathLabel": str(display_state.get("pathLabel", "") or ""),
    "baselineParams": baseline_params,
    "genericParams": generic_params,
    "flmOverrides": flm_overrides,
  }
  _write_json(paths["savedTunes"] / f"{tune_id}.json", tune)
  active_snapshot.update({
    "profileId": f"saved:{tune_id}",
    "savedTuneId": tune_id,
    "profileLabel": tune["name"],
    "carFingerprint": car_fingerprint,
    "updatedAt": now,
  })
  _write_json(paths["snapshots"] / "active.json", active_snapshot)
  _apply_param_bundle(params, {"FLMActiveProfileId": f"saved:{tune_id}"})
  return {
    "message": f"Saved {tune['name']}.",
    "tune": tune,
    "workspace": list_workspace(),
  }


def apply_saved_tune(tune_id: str) -> dict[str, Any]:
  paths = ensure_flm_workspace()
  tune = _load_saved_tune(tune_id, paths)
  params = Params(return_defaults=True)
  current_car = _current_car_identity(params)
  tune_fingerprint = str(tune.get("carFingerprint", "") or "")
  if current_car["carFingerprint"] and tune_fingerprint and current_car["carFingerprint"] != tune_fingerprint:
    raise RuntimeError(
      f"This tune is for {tune_fingerprint}, but the connected car is {current_car['carFingerprint']}."
    )

  current_state = _snapshot_current_trial_state(params)
  raw_active_snapshot = _read_json(paths["snapshots"] / "active.json", {})
  if not isinstance(raw_active_snapshot, dict):
    raw_active_snapshot = {}
  previous_display_state = _active_trial_display_state(paths, raw_active_snapshot) or {}
  if current_state.get("FLMTrialApplied", False):
    active_fingerprint = _active_trial_car_fingerprint(paths, raw_active_snapshot)
    changing_cars = bool(current_car["carFingerprint"] and active_fingerprint and current_car["carFingerprint"] != active_fingerprint)
    if changing_cars:
      saved_baseline = tune.get("baselineParams", {})
      if not isinstance(saved_baseline, dict) or not saved_baseline or saved_baseline.get("FLMTrialApplied", False):
        raise RuntimeError("This saved tune does not contain a clean baseline for the connected car. Revert before changing cars, then save the tune again.")
      baseline_params = saved_baseline
      session_started_at = time.time()
    else:
      baseline_snapshot = _find_revert_snapshot(
        paths,
        raw_active_snapshot,
        str(current_state.get("FLMActiveProfileId", "") or ""),
        params,
      )
      if baseline_snapshot is None:
        raise RuntimeError("The active FLM trial has no recoverable rollback baseline. Keep the current tune as the new baseline before switching tunes.")
      baseline_params = baseline_snapshot["params"]
      session_started_at = float(baseline_snapshot.get("sessionStartedAt", baseline_snapshot.get("capturedAt", time.time())) or time.time())
  else:
    baseline_params = current_state
    session_started_at = time.time()

  generic_params = {
    key: value for key, value in tune.get("genericParams", {}).items()
    if key in FLM_ADVANCED_LATERAL_PARAM_KEYS
  } if isinstance(tune.get("genericParams"), dict) else {}
  flm_overrides = normalize_flm_overrides(tune.get("flmOverrides", {}))
  profile_id = f"saved:{tune_id}"
  now = time.time()
  snapshot = {
    "reportId": str(tune.get("sourceReportId", "") or ""),
    "profileId": profile_id,
    "profileLabel": str(tune.get("name", "Saved Tune") or "Saved Tune"),
    "savedTuneId": tune_id,
    "carFingerprint": tune_fingerprint,
    "pathKey": str(tune.get("pathKey", "") or ""),
    "pathLabel": str(tune.get("pathLabel", "") or ""),
    "capturedAt": session_started_at,
    "updatedAt": now,
    "sessionStartedAt": session_started_at,
    "revisionCount": int(previous_display_state.get("revisionCount", 0) or 0) + 1,
    "params": baseline_params,
    "appliedGenericParams": generic_params,
    "appliedFrictionThresholds": flm_overrides.get("baseFrictionThresholds", {}),
    "appliedVehicleKnobs": flm_overrides.get("vehicleKnobs", {}),
  }
  _write_json(paths["snapshots"] / "active.json", snapshot)
  _write_json(paths["snapshots"] / f"saved-{tune_id}-{time.time_ns()}.json", snapshot)
  _persist_trial_baseline(params, snapshot)

  # Start from the original manual baseline on every switch so values from the
  # previously active saved tune cannot leak into this one.
  bundle = {
    key: baseline_params[key] for key in FLM_ADVANCED_LATERAL_PARAM_KEYS
    if key in baseline_params
  }
  bundle.update(generic_params)
  bundle["FLMActiveProfileId"] = profile_id
  bundle["FLMActiveOverrides"] = flm_overrides
  bundle["FLMTrialApplied"] = True
  _apply_param_bundle(params, bundle)
  if tune.get("pathKey") == "cleanup_pass" and tune_fingerprint:
    _record_cleanup_progress(tune_fingerprint, str(tune.get("sourceReportId", "") or ""))
  return {
    "message": f"Applied saved tune {tune.get('name', 'Saved Tune')}.",
    "tune": tune,
    "workspace": list_workspace(),
  }


def rename_saved_tune(tune_id: str, name: str) -> dict[str, Any]:
  paths = ensure_flm_workspace()
  tune = _load_saved_tune(tune_id, paths)
  tune["name"] = _normalize_saved_tune_name(name)
  tune["updatedAt"] = time.time()
  _write_json(paths["savedTunes"] / f"{tune_id}.json", tune)
  active_snapshot_path = paths["snapshots"] / "active.json"
  active_snapshot = _read_json(active_snapshot_path, {})
  if isinstance(active_snapshot, dict) and active_snapshot.get("savedTuneId") == tune_id:
    active_snapshot["profileLabel"] = tune["name"]
    active_snapshot["updatedAt"] = time.time()
    _write_json(active_snapshot_path, active_snapshot)
  return {
    "message": f"Renamed saved tune to {tune['name']}.",
    "tune": tune,
    "workspace": list_workspace(),
  }


def delete_saved_tune(tune_id: str) -> dict[str, Any]:
  paths = ensure_flm_workspace()
  tune = _load_saved_tune(tune_id, paths)
  active_snapshot = _read_json(paths["snapshots"] / "active.json", {})
  params = Params(return_defaults=True)
  current_profile_id = params.get("FLMActiveProfileId", encoding="utf-8") or ""
  if (
    (isinstance(active_snapshot, dict) and active_snapshot.get("savedTuneId") == tune_id)
    or (params.get_bool("FLMTrialApplied") and current_profile_id == f"saved:{tune_id}")
  ):
    raise RuntimeError("Revert or switch away from this saved tune before deleting it.")
  (paths["savedTunes"] / f"{tune_id}.json").unlink()
  return {
    "message": f"Deleted saved tune {tune.get('name', 'Saved Tune')}.",
    "workspace": list_workspace(),
  }


def apply_trial_profile(report_id: str, profile_id: str) -> dict[str, Any]:
  paths = ensure_flm_workspace()
  params = Params(return_defaults=True)
  profiles = _read_json(paths["profiles"] / f"{report_id}.json", [])
  if not isinstance(profiles, list):
    raise FileNotFoundError(profile_id)
  profile = next((item for item in profiles if isinstance(item, dict) and item.get("id") == profile_id), None)
  if profile is None:
    raise FileNotFoundError(profile_id)

  generic_params = dict(profile.get("genericParams", {}))
  flm_overrides = normalize_flm_overrides(profile.get("flmOverrides", {}))
  current_state = _snapshot_current_trial_state(params)
  raw_active_snapshot = _read_json(paths["snapshots"] / "active.json", {})
  previous_display_state = _active_trial_display_state(paths, raw_active_snapshot) or {}
  trial_already_active = bool(current_state.get("FLMTrialApplied", False))

  if trial_already_active:
    baseline_snapshot = _find_revert_snapshot(
      paths,
      raw_active_snapshot,
      str(current_state.get("FLMActiveProfileId", "") or ""),
      params,
    )
    if baseline_snapshot is None:
      raise RuntimeError("The active FLM trial has no recoverable rollback baseline. Keep the current tune as the new baseline before applying another profile.")
    baseline_params = baseline_snapshot["params"]
    session_started_at = float(baseline_snapshot.get("sessionStartedAt", baseline_snapshot.get("capturedAt", time.time())) or time.time())
  else:
    baseline_params = current_state
    session_started_at = time.time()

  previous_generic_params = dict(previous_display_state.get("appliedGenericParams", {}))
  for key in FLM_ADVANCED_LATERAL_PARAM_KEYS:
    if key in current_state and current_state.get(key) != baseline_params.get(key):
      previous_generic_params[key] = current_state[key]

  baseline_overrides = normalize_flm_overrides(baseline_params.get("FLMActiveOverrides", {}))
  current_overrides = normalize_flm_overrides(current_state.get("FLMActiveOverrides", {}))
  previous_friction_thresholds = dict(previous_display_state.get("appliedFrictionThresholds", {}))
  for family, payload in current_overrides.get("baseFrictionThresholds", {}).items():
    if payload != baseline_overrides.get("baseFrictionThresholds", {}).get(family):
      previous_friction_thresholds[family] = payload
  previous_vehicle_knobs = dict(previous_display_state.get("appliedVehicleKnobs", {}))
  for symbol, value in current_overrides.get("vehicleKnobs", {}).items():
    if value != baseline_overrides.get("vehicleKnobs", {}).get(symbol):
      previous_vehicle_knobs[symbol] = value

  applied_generic_params = {
    **previous_generic_params,
    **{
      key: value for key, value in generic_params.items()
      if key in FLM_ADVANCED_LATERAL_PARAM_KEYS
    },
  }
  applied_friction_thresholds = {
    **previous_friction_thresholds,
    **flm_overrides.get("baseFrictionThresholds", {}),
  }
  applied_vehicle_knobs = {
    **previous_vehicle_knobs,
    **flm_overrides.get("vehicleKnobs", {}),
  }
  now = time.time()
  snapshot = {
    "reportId": report_id,
    "profileId": profile_id,
    "profileLabel": str(profile.get("label", "FLM") or "FLM"),
    "pathKey": str(profile.get("pathKey", "") or ""),
    "pathLabel": str(profile.get("pathLabel", "") or ""),
    "capturedAt": session_started_at,
    "updatedAt": now,
    "sessionStartedAt": session_started_at,
    "revisionCount": int(previous_display_state.get("revisionCount", 0) or 0) + 1,
    "params": baseline_params,
    "appliedGenericParams": applied_generic_params,
    "appliedFrictionThresholds": applied_friction_thresholds,
    "appliedVehicleKnobs": applied_vehicle_knobs,
  }
  _write_json(paths["snapshots"] / "active.json", snapshot)
  _write_json(paths["snapshots"] / f"{report_id}-{profile_id.replace(':', '_')}.json", snapshot)
  _persist_trial_baseline(params, snapshot)

  bundle = generic_params
  bundle["FLMActiveProfileId"] = profile_id
  bundle["FLMActiveOverrides"] = _merge_flm_override_state(
    current_state.get("FLMActiveOverrides", {}),
    flm_overrides,
  )
  bundle["FLMTrialApplied"] = True
  _apply_param_bundle(params, bundle)
  if profile.get("pathKey") == "cleanup_pass":
    report = _read_json(paths["reports"] / f"{report_id}.json", {})
    _record_cleanup_progress(str(report.get("car", {}).get("carFingerprint", "")), report_id)
  return {
    "message": f"Applied {profile.get('label', 'FLM')} profile.",
    "profile": profile,
  }


def revert_trial_profile() -> dict[str, Any]:
  paths = ensure_flm_workspace()
  snapshot_path = paths["snapshots"] / "active.json"
  snapshot = _read_json(snapshot_path, {})
  params = Params(return_defaults=True)
  current_profile_id = params.get("FLMActiveProfileId", encoding="utf-8") or ""
  revert_snapshot = _find_revert_snapshot(paths, snapshot if isinstance(snapshot, dict) else {}, current_profile_id, params)
  if revert_snapshot is None:
    params.put_bool("FLMTrialApplied", False)
    params.put("FLMActiveProfileId", "")
    params.put("FLMActiveOverrides", {})
    _clear_persistent_trial_baseline(params)
    try:
      snapshot_path.unlink()
    except FileNotFoundError:
      pass
    Params(memory=True).put_bool("StarPilotTogglesUpdated", True)
    return {"message": "Recovered the incomplete FLM trial; no rollback snapshot was available.", "recovered": True}
  _apply_param_bundle(params, revert_snapshot["params"])
  _clear_persistent_trial_baseline(params)
  try:
    snapshot_path.unlink()
  except FileNotFoundError:
    pass
  return {
    "message": "Reverted the complete FLM trial session to its original baseline.",
    "snapshot": {
      **(snapshot if isinstance(snapshot, dict) else {}),
      "params": revert_snapshot["params"],
      "recoveredBaseline": revert_snapshot is not snapshot,
    },
  }


def accept_trial_as_baseline() -> dict[str, Any]:
  paths = ensure_flm_workspace()
  params = Params(return_defaults=True)
  active_snapshot = _read_json(paths["snapshots"] / "active.json", {})
  if not params.get_bool("FLMTrialApplied") and not (isinstance(active_snapshot, dict) and active_snapshot):
    raise FileNotFoundError("active trial")

  params.put_bool("FLMTrialApplied", False)
  params.put("FLMActiveProfileId", "")
  _clear_persistent_trial_baseline(params)
  Params(memory=True).put_bool("StarPilotTogglesUpdated", True)
  for path in paths["snapshots"].glob("*.json"):
    path.unlink()

  return {
    "message": "Kept the current tuning values and made them the new FLM baseline.",
    "workspace": list_workspace(),
  }


def record_feedback(report_id: str, feedback: dict[str, Any]) -> dict[str, Any]:
  paths = ensure_flm_workspace()
  normalized = {
    "acceptedDimensions": [str(item) for item in feedback.get("acceptedDimensions", [])],
    "ignoredDimensions": [str(item) for item in feedback.get("ignoredDimensions", [])],
    "notes": str(feedback.get("notes", "") or "").strip(),
    "updatedAt": time.time(),
  }
  _write_json(paths["feedback"] / f"{report_id}.json", normalized)
  report = load_report(report_id)
  report["feedback"] = normalized
  if isinstance(report.get("paths"), list) and report.get("paths"):
    selected_path_key = str(report.get("selectedPathKey") or report.get("primaryPathKey") or "")
    flattened_profiles = []
    for path in report["paths"]:
      if not isinstance(path, dict):
        continue
      profiles = build_trial_profiles(
        report_id,
        path.get("suggestions", []),
        normalized,
        report.get("capabilities", {}),
        path_key=str(path.get("key", "cleanup_pass")),
        path_label=str(path.get("title", "Cleanup Pass")),
      )
      path["profiles"] = profiles
      flattened_profiles.extend(profiles)
      if path.get("key") == selected_path_key:
        report["suggestions"] = list(path.get("suggestions", []))
    report["profiles"] = flattened_profiles
  else:
    report["profiles"] = build_trial_profiles(report_id, report.get("suggestions", []), normalized, report.get("capabilities", {}))
  (paths["reports"] / f"{report_id}.html").write_text(_render_report_html(report), encoding="utf-8")
  report.pop("html", None)
  _write_json(paths["reports"] / f"{report_id}.json", report)
  _write_json(paths["profiles"] / f"{report_id}.json", report["profiles"])
  return {
    "message": "Saved FLM feedback.",
    "feedback": normalized,
    "profiles": report["profiles"],
    "report": load_report(report_id),
  }


def run_worker(payload_json: str) -> None:
  payload = json.loads(payload_json)
  routes = [str(route) for route in payload.get("routes", [])]
  footage_paths = [str(path) for path in payload.get("footagePaths", [])]
  segment_ranges = normalize_segment_ranges(routes, payload.get("segmentRanges", {}))
  ensure_flm_workspace()
  _write_flm_status({
    "pid": os.getpid(),
    "startedAt": time.time(),
    "running": True,
    "state": "starting",
    "routes": routes,
    "segmentRanges": segment_ranges,
    "progress": 0,
    "total": len(routes),
  })
  threading.Thread(target=_watch_flm_worker_for_onroad, daemon=True).start()
  try:
    _require_flm_offroad()
    report = analyze_routes(routes, footage_paths, segment_ranges=segment_ranges)
    processed_segments = int(report.get("summary", {}).get("processedSegments", 0) or 0)
    skipped_segments = int(report.get("summary", {}).get("skippedSegments", 0) or 0)
    total_segments = processed_segments + skipped_segments
    _write_flm_status({
      "pid": os.getpid(),
      "startedAt": time.time(),
      "running": False,
      "state": "complete",
      "routes": routes,
      "segmentRanges": segment_ranges,
      "progress": total_segments,
      "total": total_segments,
      "skippedSegments": skipped_segments,
      "reportId": report["reportId"],
    })
  except FLMAnalysisCancelled as error:
    _write_flm_status({
      "pid": 0,
      "startedAt": time.time(),
      "running": False,
      "state": "cancelled_onroad",
      "routes": routes,
      "segmentRanges": segment_ranges,
      "progress": 0,
      "total": len(routes),
      "error": str(error),
    })
  except Exception as error:
    _write_flm_status({
      "pid": os.getpid(),
      "startedAt": time.time(),
      "running": False,
      "state": "failed",
      "routes": routes,
      "segmentRanges": segment_ranges,
      "progress": 0,
      "total": len(routes),
      "error": str(error),
    })
    raise


def main() -> None:
  if len(sys.argv) >= 3 and sys.argv[1] == "worker":
    run_worker(sys.argv[2])
    return
  if len(sys.argv) >= 2 and sys.argv[1] == "analyze":
    routes = sys.argv[2:]
    footage_paths = [str(Paths.log_root(HD=True, raw=True)), str(Paths.log_root(konik=True, raw=True)), str(Paths.log_root(raw=True))]
    report = analyze_routes(routes, footage_paths)
    print(json.dumps({"reportId": report["reportId"], "htmlPath": report["htmlPath"], "jsonPath": report["jsonPath"]}, indent=2))
    return
  print("Usage: flm_workspace.py analyze <route> [<route>...]")


if __name__ == "__main__":
  main()
