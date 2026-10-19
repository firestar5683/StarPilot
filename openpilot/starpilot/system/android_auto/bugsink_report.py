"""Bounded Android Auto diagnostics for a separately configured Bugsink project."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from openpilot.starpilot.system.android_auto import identity as identity_store
from openpilot.starpilot.system.android_auto.bugsink_diagnosis import attempt_records, diagnosis, elapsed, sanitize
from openpilot.starpilot.system.android_auto.bugsink_summary import batch_summary, pairing_summary, session_summary, software_tags

STATE_PATH = identity_store.DATA_DIR / "bugsink_report.json"
PAIRING_PATH = identity_store.LOG_DIR / "pairing.jsonl"
PAIRING_MAX_BYTES = 64 << 10
INTERVAL_S = 60.0
LOG_SETTLE_S = 120         # a log written this recently may still be a live session, unless it already ended
MAX_SESSIONS = 20          # per drive report; the rest go in the next one
MAX_FAILURES = 5           # distinct failures detailed per drive report
MAX_BREADCRUMBS = 100
FINISHED_EVENT = '"event": "session_stop"'
OUTCOME_RANK = ("streamed", "recovered", "stopped", "dropped", "failed")

def scrub(text: str, limit: int = 300) -> str:
  return sanitize(str(text))[:limit]


def _number(value) -> float | None:
  return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _session_number(path: Path) -> int:
  match = re.fullmatch(r"session-(\d{6})-.*\.jsonl", path.name)
  return int(match[1]) if match else 0


def _percentile(values: list[float], fraction: float) -> float | None:
  if not values:
    return None
  ordered = sorted(values)
  return ordered[min(len(ordered) - 1, int(len(ordered) * fraction))]


def stage_timings(events: list[dict]) -> list[dict]:
  """Each connection stage in the order it was first entered, with seconds since the session started."""
  from openpilot.starpilot.system.android_auto.compat_report import STAGE_ORDER
  seen: dict[str, float | None] = {}
  for event in events:
    state = event.get("state")
    if event["event"] == "stage" and state in STAGE_ORDER and state not in seen:
      seen[state] = elapsed(events[0], event)
  return [{"stage": stage, "at_s": at} for stage, at in seen.items()]


def video_summary(events: list[dict]) -> dict:
  """The video mode and the frame rate delivered while the car showed StarPilot, from the 30 s stats lines."""
  ready = next((event for event in reversed(events) if event["event"] == "projection_ready"), {})
  pipeline = next((event for event in reversed(events) if event["event"] == "frame_pipeline"), {})
  mode = ready.get("mode") if isinstance(ready.get("mode"), dict) else {}
  stats = [event for event in events if event["event"] == "stats" and event.get("focused") is not False]
  fps = [value for event in stats if (value := _number(event.get("fps"))) is not None]
  encode = [value for event in stats if (value := _number(event.get("encode_ms"))) is not None]
  peaks = [value for event in stats if (value := _number(event.get("encode_peak_ms"))) is not None]
  ages = [value for event in stats if (value := _number(event.get("frame_age_p95_ms"))) is not None]
  wifi = [value for event in stats if (value := _number(event.get("wifi_dbm"))) is not None]
  summary = {
    "resolution": f"{mode['width']}x{mode['height']}" if mode.get("width") and mode.get("height") else None,
    "car_fps": mode.get("fps"),
    "margins": f"{mode.get('margin_width')}x{mode.get('margin_height')}" if mode else None,
    "target_fps": pipeline.get("target_fps"),
    "encoder": pipeline.get("encoder"),
    "nv12": pipeline.get("nv12"),
    "samples": len(fps),
    "fps_avg": round(sum(fps) / len(fps), 1) if fps else None,
    "fps_min": min(fps) if fps else None,
    "fps_p10": _percentile(fps, 0.1),
    "encode_ms_avg": round(sum(encode) / len(encode), 1) if encode else None,
    "encode_peak_ms": max(peaks) if peaks else None,
    "frame_age_p95_ms_max": max(ages) if ages else None,
    "wifi_dbm_min": min(wifi) if wifi else None,
    "encoder_recoveries": max((int(event.get("encoder_recoveries") or 0) for event in stats), default=0),
    "frames_sent": max((int(event.get("frames_sent") or 0) for event in stats), default=0),
  }
  return {key: value for key, value in summary.items() if value is not None}


def session_record(path: Path) -> dict:
  """One finished session log reduced to its outcome, stage timings, video and the car it talked to."""
  from openpilot.starpilot.system.android_auto import compat_report
  events = compat_report.load_events(path)
  report = compat_report.summarize(events)
  started = events[0].get("t", "") if events else ""
  attempts = attempt_records(events)
  relevant = [a for a in attempts if not a["after_car_shutdown"]]
  failures = [a for a in relevant if a.get("error_kind") or a.get("error")]
  streamed = [a for a in relevant if a["video_acknowledged"]]
  drops = [a for a in failures if a["video_acknowledged"]]
  if streamed:
    outcome = "recovered" if failures and relevant[-1]["video_acknowledged"] and relevant[-1] not in failures else "streamed"
    if failures and relevant[-1] in failures:
      outcome = "dropped"
  else:
    outcome = "failed" if failures else "stopped"
  last_failure = failures[-1] if failures else {}
  first_frame = next((e for e in events if e["event"] == "video_acknowledged"), None)
  car_ended = any(a["ended_by_car"] for a in attempts)
  car = report["car"]
  start = next((e for e in events if e["event"] == "session_start"), {})
  software, settings = start.get("software", {}), start.get("settings")
  return {
    "software": {key: str(software.get(key) or "unknown") for key in ("commit", "branch")} if isinstance(software, dict) else {},
    "settings": settings if isinstance(settings, dict) else {},
    "seq": _session_number(path),
    "name": path.name,
    "started": started,
    "transport": report["transport"],
    "trigger": report["trigger"],
    "outcome": outcome,
    "furthest_stage": report["furthest_stage"],
    "failed_stage": str(last_failure.get("failed_stage", "")),
    "error_kind": str(last_failure.get("error_kind", "")),
    "error": scrub(last_failure.get("error", "")),
    "failures": len(failures),
    "drops": len(drops),
    "ended_by_car": car_ended,
    "attempts": attempts,
    "timing_source": "monotonic" if events and all("mono_s" in e for e in events) else "wall clock (legacy log)",
    "time_to_first_frame_s": elapsed(events[0], first_frame) if first_frame else None,
    "streamed_s": round(sum(a["streamed_s"] or 0 for a in attempts), 1) if first_frame else None,
    "stages": stage_timings(events),
    "video": video_summary(events),
    "focus_lost": report["focus"]["lost"],
    "stalls": report["health"],
    "wifi_security": report["wifi"].get("security") or None,
    "tls": report["tls"].get("version") or None,
    "head_unit": {key: car[key] for key in ("head_unit_make", "head_unit_model", "head_unit_software_version",
                                            "car_make", "car_model", "car_year") if car.get(key)},
    "_report": report,
    "_names": [car.get("bluetooth_name", ""), car.get("display_name", "")],
  }


def _finished(path: Path) -> bool:
  with path.open("rb") as log:
    log.seek(0, os.SEEK_END)
    log.seek(max(0, log.tell() - 512))
    lines = log.read().decode(errors="replace").strip().splitlines()
  return bool(lines) and FINISHED_EVENT in lines[-1]


def new_sessions(log_dir: Path, last_seq: int, now: float) -> list[dict]:
  """Finished sessions newer than ``last_seq``, oldest first; a log still being written stops the scan."""
  sessions = []
  for path in sorted(log_dir.glob("session-*.jsonl"), key=identity_store.session_log_order):
    if _session_number(path) <= last_seq:
      continue
    if len(sessions) >= MAX_SESSIONS:
      break
    try:
      if now - path.stat().st_mtime < LOG_SETTLE_S and not _finished(path):
        break
      sessions.append(session_record(path))
    except (OSError, ValueError, TypeError, KeyError):
      continue
  return sessions


def drive_summary(sessions: list[dict]) -> dict:
  """Totals across a batch of completed sessions, with sample-weighted frame rate."""
  weighted = [(s["video"]["fps_avg"], s["video"]["samples"]) for s in sessions if s["video"].get("fps_avg") is not None]
  samples = sum(count for _, count in weighted)
  outcome = max((s["outcome"] for s in sessions), key=OUTCOME_RANK.index)
  return {
    "sessions": len(sessions),
    "outcome": outcome,
    "streamed_sessions": sum(1 for s in sessions if s["time_to_first_frame_s"] is not None),
    "streamed_s": round(sum(s["streamed_s"] or 0 for s in sessions), 1),
    "failures": sum(s["failures"] for s in sessions),
    "drops": sum(s["drops"] for s in sessions),
    "fps_avg": round(sum(fps * count for fps, count in weighted) / samples, 1) if samples else None,
    "fps_min": min((s["video"]["fps_min"] for s in sessions if "fps_min" in s["video"]), default=None),
    "resolutions": sorted({s["video"]["resolution"] for s in sessions if s["video"].get("resolution")}),
    "time_to_first_frame_s": next((s["time_to_first_frame_s"] for s in sessions if s["time_to_first_frame_s"] is not None), None),
    "transport": sessions[-1]["transport"] if len({s["transport"] for s in sessions}) == 1 else "mixed",
  }


def _head_unit_label(head_unit: dict) -> str:
  return " ".join(head_unit.get(key, "") for key in ("head_unit_make", "head_unit_model")).strip() or "unknown head unit"


def _car_label(head_unit: dict) -> str:
  return " ".join(head_unit.get(key, "") for key in ("car_year", "car_make", "car_model")).strip() or "unknown car"


def _public(session: dict) -> dict:
  result = {key: value for key, value in session.items() if not key.startswith("_")}
  result["attempt_count"] = len(result.get("attempts", []))
  result["attempts_omitted"] = max(0, result["attempt_count"] - 20)
  result["attempts"] = result.get("attempts", [])[-20:]
  return sanitize(result, session.get("_names", ()))


def failure_signature(session: dict) -> str:
  return f"{diagnosis(session)['category']}:{session['failed_stage'] or 'start'}:{session['error_kind'] or 'none'}"


def failure_records(sessions):
  for session in reversed(sessions):
    for attempt in reversed(session["attempts"]):
      if attempt["after_car_shutdown"] or not (attempt.get("error") or attempt.get("error_kind")):
        continue
      yield {**session, "failed_stage": attempt.get("failed_stage", ""), "error_kind": attempt.get("error_kind", ""),
             "error": attempt.get("error", ""), "failed_attempt": attempt["attempt"]}


def drive_failures(sessions: list[dict]) -> list[dict]:
  """Distinct failures across the batch, newest first."""
  seen, failures = set(), []
  for failure in failure_records(sessions):
    signature = failure_signature(failure)
    if signature not in seen:
      seen.add(signature)
      failures.append(failure)
  return failures[:MAX_FAILURES]


def failure_detail(session: dict) -> dict:
  from openpilot.starpilot.system.android_auto import compat_report
  stage = session["failed_stage"] or session["furthest_stage"] or "start"
  kind = session["error_kind"] or "no error"
  assessment = diagnosis(session)
  names = session.get("_names", ())
  report = dict(session["_report"])
  report["car"] = {key: value for key, value in report["car"].items() if key not in ("bluetooth_name", "display_name")}
  report["errors"] = [{**error, "error": scrub(error.get("error", ""))} for error in report["errors"]]
  report["ended"] = [scrub(reason) for reason in report["ended"]]
  report["tls"] = {key: value for key, value in report["tls"].items() if key != "head_unit"}
  return {
    "title": f"{assessment['category']} at {stage}: {kind}",
    "session": session["seq"],
    "attempt": session.get("failed_attempt"),
    "cause": assessment["category"], "stage": stage, "error_kind": kind,
    "summary": sanitize(session_summary(session, assessment), names),
    "diagnosis": sanitize(assessment, names),
    "compat_report": sanitize(compat_report.render_text(report), names),
  }


def _attempt_time(session: dict, at_s) -> str | None:
  try:
    return (datetime.fromisoformat(session["started"]) + timedelta(seconds=at_s or 0)).isoformat()
  except (TypeError, ValueError):
    return None


def attempt_breadcrumbs(sessions: list[dict]) -> list[dict]:
  """Every attempt in the batch, oldest first; failures are errors so they stand out in the timeline."""
  crumbs = []
  for session in sessions:
    for attempt in session["attempts"]:
      failed = bool(attempt.get("error") or attempt.get("error_kind"))
      if failed:
        failure = {**session, "failed_stage": attempt.get("failed_stage", ""), "error_kind": attempt.get("error_kind", "")}
        message = f"{diagnosis(failure)['category']} at {attempt.get('failed_stage') or 'start'}: {attempt.get('error_kind') or 'no error'}"
        if attempt["video_acknowledged"]:
          message = (f"streamed {attempt['streamed_s']}s, then " if attempt["streamed_s"] is not None else "streamed, then ") + message
      elif attempt["video_acknowledged"]:
        message = f"streamed {attempt['streamed_s']}s" if attempt["streamed_s"] is not None else "streamed"
      else:
        message = f"stopped at {attempt['stages'][-1]['stage'] if attempt['stages'] else 'start'}"
      if attempt["after_car_shutdown"]:
        message += " (after car shutdown)"
      level = "info" if not failed else "debug" if attempt["after_car_shutdown"] else "error"
      crumb = {"category": f"session {session['seq']}", "message": f"Attempt {attempt['attempt']}: {message}", "level": level,
               "data": {key: attempt[key] for key in ("error", "failed_at_s") if attempt.get(key)}}
      if (timestamp := _attempt_time(session, attempt.get("failed_at_s") if failed else attempt.get("at_s"))) is not None:
        crumb["timestamp"] = timestamp
      crumbs.append(sanitize(crumb, session.get("_names", ())))
  return crumbs[-MAX_BREADCRUMBS:]


def drive_event(sessions: list[dict]) -> dict:
  """One report per batch: totals, every session, and each distinct failure, grouped by head unit."""
  summary = drive_summary(sessions)
  head_unit = next((s["head_unit"] for s in reversed(sessions) if s["head_unit"]), {})
  video = next((s["video"] for s in reversed(sessions) if s["video"].get("resolution")), {})
  label = _head_unit_label(head_unit)
  failures = [failure_detail(failure) for failure in drive_failures(sessions)]
  heading = "failures" if failures else "sessions"
  message = f"Android Auto {heading}: {label} ({summary['transport'] or 'unknown'})\n\n" + batch_summary(sessions, summary)
  if failures:
    message += "\n\nFailures:\n" + "\n".join(f"  {index}. {failure['title']} (session {failure['session']})"
                                               for index, failure in enumerate(failures, 1))
    message += "".join(f"\n\n--- {index}. {failure['title']} ---\n{failure['summary']}" for index, failure in enumerate(failures, 1))
  latest = failures[0] if failures else {}
  return {
    "message": message,
    "level": {"streamed": "info", "recovered": "info", "failed": "error"}.get(summary["outcome"], "warning"),
    "fingerprint": ["android-auto-drive", summary["transport"] or "unknown", label] + (["failures"] if failures else []),
    "tags": {**software_tags(sessions), "aa.report": "drive", "aa.outcome": summary["outcome"], "aa.transport": summary["transport"] or "unknown",
             "aa.head_unit": label, "aa.car": _car_label(head_unit), "aa.resolution": video.get("resolution", "none"),
             "aa.encoder": video.get("encoder", "unknown"),
             "aa.fps": str(summary["fps_avg"]) if summary["fps_avg"] is not None else "none",
             "aa.failures": str(len(failures)),
             **({"aa.cause": latest["cause"], "aa.stage": latest["stage"], "aa.error_kind": latest["error_kind"]} if latest else {})},
    "breadcrumbs": {"values": attempt_breadcrumbs(sessions)},
    "contexts": {"android_auto_drive": summary, "android_auto_head_unit": head_unit,
                 **{f"android_auto_session_{index + 1}": _public(session) for index, session in enumerate(sessions)},
                 **{f"android_auto_failure_{index + 1}": {key: value for key, value in failure.items() if key != "summary"}
                    for index, failure in enumerate(failures)}},
  }


def record_pairing(record: dict, path: Path = PAIRING_PATH) -> None:
  """Append one finished pairing attempt; the journal keeps only its newest lines."""
  try:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lines = path.read_text().splitlines() if path.exists() else []
    seq = 1 + max((json.loads(line).get("seq", 0) for line in lines if line.strip()), default=0)
    lines.append(json.dumps({"seq": seq, **record}, default=str))
    while len(lines) > 1 and sum(len(line) + 1 for line in lines) > PAIRING_MAX_BYTES:
      lines.pop(0)
    _write_atomic(path, "\n".join(lines) + "\n")
  except (OSError, ValueError):
    pass


def new_pairings(last_seq: int, path: Path = PAIRING_PATH) -> list[dict]:
  try:
    lines = path.read_text().splitlines()
  except OSError:
    return []
  records = []
  for line in lines:
    try:
      record = json.loads(line)
    except ValueError:
      continue
    if isinstance(record, dict) and int(record.get("seq", 0)) > last_seq:
      records.append(record)
  return records


def pairing_event(record: dict) -> dict:
  result = str(record.get("result", "unknown"))
  return {
    "message": f"Android Auto pairing {result}\n\n" + sanitize(pairing_summary(record)),
    "level": "info" if result == "paired" else "warning",
    "fingerprint": ["android-auto-pairing", result],
    "tags": {**software_tags([record]), "aa.report": "pairing", "aa.pairing": result, "aa.transport": record.get("transport", "unknown")},
    "contexts": {"android_auto_pairing": sanitize(record)},
  }


class PairingAttempt:
  """The steps of one pairing window, with seconds since it opened; ``finish`` writes it to the journal."""

  def __init__(self, seconds: float, clock: Callable[[], float] = time.monotonic, sink: Callable[[dict], None] = record_pairing):
    from openpilot.starpilot.system.android_auto.bugsink_transport import device_metadata
    software = device_metadata()
    self._clock, self._sink = clock, sink
    self._opened = clock()
    self.record: dict = {"started": datetime.now().astimezone().isoformat(timespec="seconds"), "window_s": seconds, "steps": [],
                         "transport": "wireless", "software": {key: software.get(key, "unknown") for key in ("commit", "branch")}}
    self.step("opened")

  def step(self, name: str, **values) -> None:
    self.record["steps"].append({"step": name, "at_s": round(self._clock() - self._opened, 1), **values})
    if len(self.record["steps"]) > 100:
      self.record["steps"].pop(0)
      self.record["steps_omitted"] = self.record.get("steps_omitted", 0) + 1

  def finish(self, result: str, **values) -> None:
    self.step(result, **values)
    self._sink({**self.record, "result": result, "duration_s": round(self._clock() - self._opened, 1)})


def _load_state(path: Path) -> dict:
  try:
    state = json.loads(path.read_text())
    return state if isinstance(state, dict) else {}
  except (OSError, ValueError):
    return {}


def _write_atomic(path: Path, text: str) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temporary:
    temporary_path = Path(temporary.name)
    try:
      temporary.write(text)
      temporary.flush()
      os.fsync(temporary.fileno())
      os.replace(temporary_path, path)
    finally:
      temporary_path.unlink(missing_ok=True)


def send_reports(capture: Callable[..., bool], flush: Callable[[], None] = lambda: None, *, state_path: Path = STATE_PATH,
                 log_dir: Path | None = None, pairing_path: Path = PAIRING_PATH, now: float | None = None) -> int:
  """Send what is new since the last call; returns how many reports were queued.

  Capture must return True only after the server accepts the event."""
  now = datetime.now(UTC).timestamp() if now is None else now
  state = _load_state(state_path)
  last_seq, pairing_seq = int(state.get("last_seq", 0)), int(state.get("pairing_seq", 0))
  queued = 0

  for record in new_pairings(pairing_seq, pairing_path):
    if not capture(**pairing_event(record)):
      break
    pairing_seq, queued = int(record["seq"]), queued + 1

  sessions = new_sessions(log_dir or identity_store.LOG_DIR, last_seq, now)
  if sessions and capture(**drive_event(sessions)):
    last_seq, queued = sessions[-1]["seq"], queued + 1

  if queued:
    flush()
    _write_atomic(state_path, json.dumps({"last_seq": last_seq, "pairing_seq": pairing_seq}))
  return queued


class Reporter:
  """Background thread in android_autod: every minute, while parked, sends what is new."""

  def __init__(self, parked: Callable[[], bool], interval: float = INTERVAL_S):
    self._parked, self._interval = parked, interval
    self._stop = threading.Event()
    self._thread: threading.Thread | None = None

  def start(self) -> Reporter:
    self._thread = threading.Thread(target=self._run, name="aa_bugsink_report", daemon=True)
    self._thread.start()
    return self

  def close(self) -> None:
    self._stop.set()

  def _run(self) -> None:
    from openpilot.starpilot.system.android_auto.bugsink_transport import configured_sender
    while not self._stop.wait(self._interval):
      try:
        if self._parked():
          capture = configured_sender(active=lambda: not self._stop.is_set() and self._parked())
          if capture is not None:
            send_reports(capture)
      except Exception as error:
        print(json.dumps({"event": "bugsink_report_failed", "error_kind": type(error).__name__}), flush=True)
