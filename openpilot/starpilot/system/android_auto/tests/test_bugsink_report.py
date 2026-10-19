"""Android Auto drive, failure and pairing reports for Bugsink, built from session logs without a network."""

import json
import os
from datetime import UTC, datetime

from openpilot.starpilot.system.android_auto import bugsink_report as br


def write_session(log_dir, number, events, finished=True):
  log_dir.mkdir(parents=True, exist_ok=True)
  path = log_dir / f"session-{number:06d}-20261016-120000.jsonl"
  lines = [{"t": f"2026-10-16T12:{minute:02d}:{second:02d}.000+00:00", "event": name, **values}
           for minute, second, name, values in events]
  if finished:
    lines.append({"t": "2026-10-16T12:59:00.000+00:00", "event": "session_stop"})
  path.write_text("".join(json.dumps(line) + "\n" for line in lines))
  return path


STREAMED = [
  (0, 0, "session_start", {"receiver": "Honda HFL", "trigger": "auto"}),
  (0, 1, "stage", {"state": "connecting_bluetooth"}),
  (0, 3, "stage", {"state": "rfcomm"}),
  (0, 6, "stage", {"state": "joining_wifi"}),
  (0, 9, "stage", {"state": "authenticating"}),
  (0, 10, "discovered", {"head_unit": {"2": ["Honda"], "3": ["Civic"], "4": ["2022"], "7": ["Alpine"], "8": ["HU-1"],
                                       "14": ["Danny's Civic"]}, "channels": []}),
  (0, 11, "projection_ready", {"mode": {"width": 1280, "height": 720, "fps": 30, "margin_width": 0, "margin_height": 0}}),
  (0, 11, "frame_pipeline", {"nv12": True, "async_readback": True, "target_fps": 30, "encoder": "v4l2"}),
  (0, 12, "stage", {"state": "streaming"}),
  (0, 12, "video_acknowledged", {}),
  (0, 42, "stats", {"fps": 30.0, "encode_ms": 6.0, "encode_peak_ms": 9.0, "frame_age_p95_ms": 40, "wifi_dbm": -50,
                    "focused": True, "frames_sent": 900, "encoder_recoveries": 0}),
  (1, 12, "stats", {"fps": 20.0, "encode_ms": 8.0, "encode_peak_ms": 15.0, "frame_age_p95_ms": 90, "wifi_dbm": -70,
                    "focused": True, "frames_sent": 1500, "encoder_recoveries": 1}),
  (1, 42, "stats", {"fps": 0.0, "focused": False}),
]

FAILED = [
  (0, 0, "session_start", {"receiver": "Honda HFL", "trigger": "manual"}),
  (0, 1, "stage", {"state": "connecting_bluetooth"}),
  (0, 4, "stage", {"state": "joining_wifi"}),
  (0, 30, "attempt_failed", {"stage": "joining_wifi", "error": "Joining Wi-Fi: no route to 192.168.1.4 from AA:BB:CC:DD:EE:FF",
                             "kind": "TimeoutError"}),
]


def test_session_record_reports_stages_resolution_and_fps(tmp_path):
  record = br.session_record(write_session(tmp_path, 1, STREAMED))
  assert record["outcome"] == "streamed" and record["transport"] == "wireless"
  assert record["time_to_first_frame_s"] == 12.0
  assert [stage["stage"] for stage in record["stages"]] == ["connecting_bluetooth", "rfcomm", "joining_wifi", "authenticating", "streaming"]
  assert record["stages"][2]["at_s"] == 6.0
  video = record["video"]
  assert video["resolution"] == "1280x720" and video["car_fps"] == 30 and video["target_fps"] == 30 and video["encoder"] == "v4l2"
  assert video["samples"] == 2 and video["fps_avg"] == 25.0 and video["fps_min"] == 20.0  # the unfocused sample is left out
  assert video["encode_peak_ms"] == 15.0 and video["wifi_dbm_min"] == -70 and video["encoder_recoveries"] == 1
  assert record["head_unit"] == {"head_unit_make": "Alpine", "head_unit_model": "HU-1", "car_make": "Honda",
                                 "car_model": "Civic", "car_year": "2022"}


def test_drive_event_groups_sessions_by_head_unit_and_weights_fps(tmp_path):
  sessions = [br.session_record(write_session(tmp_path, 1, STREAMED)), br.session_record(write_session(tmp_path, 2, FAILED))]
  event = br.drive_event(sessions)
  assert event["fingerprint"] == ["android-auto-drive", "wireless", "Alpine HU-1"]
  assert event["level"] == "warning" and event["tags"]["aa.outcome"] == "failed"
  assert event["tags"]["aa.resolution"] == "1280x720" and event["tags"]["aa.fps"] == "25.0"
  drive = event["contexts"]["android_auto_drive"]
  assert drive["sessions"] == 2 and drive["failures"] == 1 and drive["fps_avg"] == 25.0 and drive["resolutions"] == ["1280x720"]
  assert "_report" not in event["contexts"]["android_auto_session_1"]
  assert "Danny's Civic" not in json.dumps(event)


def test_failure_event_hides_names_and_addresses(tmp_path):
  session = br.session_record(write_session(tmp_path, 1, FAILED))
  event = br.failure_event(session)
  assert event["message"].splitlines()[0] == "Android Auto wifi_join_failed at joining_wifi: TimeoutError"
  assert event["fingerprint"] == ["android-auto-failure", "wifi_join_failed", "joining_wifi", "TimeoutError"]
  text = json.dumps(event)
  for secret in ("AA:BB:CC:DD:EE:FF", "192.168.1.4", "Honda HFL"):
    assert secret not in text
  assert "Stages: connecting_bluetooth > joining_wifi" in event["contexts"]["android_auto_compat_report"]["text"]


def test_send_reports_once_and_rate_limits_failures(tmp_path):
  logs, state = tmp_path / "logs", tmp_path / "state.json"
  write_session(logs, 1, STREAMED)
  for number in range(2, 4):
    write_session(logs, number, FAILED)
  captured, flushes = [], []

  def capture(**event):
    captured.append(event)
    return True

  queued = br.send_reports(capture, lambda: flushes.append(1), state_path=state, log_dir=logs, pairing_path=tmp_path / "p.jsonl")
  assert queued == 2 and len(flushes) == 1  # one drive report, and one failure report for two failures of the same kind
  assert [event["tags"]["aa.report"] for event in captured] == ["drive", "failure"]
  assert json.loads(state.read_text())["last_seq"] == 3

  assert br.send_reports(capture, state_path=state, log_dir=logs, pairing_path=tmp_path / "p.jsonl") == 0
  write_session(logs, 4, FAILED)
  captured.clear()
  br.send_reports(capture, state_path=state, log_dir=logs, pairing_path=tmp_path / "p.jsonl")
  assert [event["tags"]["aa.report"] for event in captured] == ["drive"]  # the same failure was reported today already


def test_unaccepted_reports_are_retried(tmp_path):
  logs, state = tmp_path / "logs", tmp_path / "state.json"
  write_session(logs, 1, STREAMED)
  assert br.send_reports(lambda **_: False, state_path=state, log_dir=logs, pairing_path=tmp_path / "p.jsonl") == 0
  assert not state.exists()
  assert br.send_reports(lambda **_: True, state_path=state, log_dir=logs, pairing_path=tmp_path / "p.jsonl") == 1


def test_live_session_waits_until_finished(tmp_path):
  logs = tmp_path / "logs"
  path = write_session(logs, 1, STREAMED, finished=False)
  assert br.new_sessions(logs, 0, datetime.now(UTC).timestamp()) == []
  old = datetime.now(UTC).timestamp() - br.LOG_SETTLE_S - 1
  os.utime(path, (old, old))
  assert len(br.new_sessions(logs, 0, datetime.now(UTC).timestamp())) == 1


def test_pairing_attempts_are_journaled_and_reported(tmp_path):
  journal = tmp_path / "pairing.jsonl"
  clock = iter([0.0, 0.0, 4.0, 9.5, 12.0, 12.0])
  attempt = br.PairingAttempt(180.0, clock=lambda: next(clock), sink=lambda record: br.record_pairing(record, journal))
  attempt.step("pair_requested")
  attempt.step("status", state="paired", prompt=False, approved=True)
  attempt.finish("paired")
  records = br.new_pairings(0, journal)
  assert len(records) == 1 and records[0]["result"] == "paired" and records[0]["duration_s"] == 12.0
  assert [step["step"] for step in records[0]["steps"]] == ["opened", "pair_requested", "status", "paired"]

  captured = []
  assert br.send_reports(lambda **event: captured.append(event) or True, state_path=tmp_path / "s.json",
                         log_dir=tmp_path / "logs", pairing_path=journal) == 1
  assert captured[0]["fingerprint"] == ["android-auto-pairing", "paired"] and captured[0]["level"] == "info"
  assert br.new_pairings(json.loads((tmp_path / "s.json").read_text())["pairing_seq"], journal) == []


def test_pairing_journal_stays_bounded(tmp_path):
  journal = tmp_path / "pairing.jsonl"
  for index in range(400):
    br.record_pairing({"result": "expired", "steps": [{"step": "opened", "at_s": 0}] * 4, "index": index}, journal)
  assert journal.stat().st_size <= br.PAIRING_MAX_BYTES
  assert br.new_pairings(0, journal)[-1]["seq"] == 400


def test_recovered_attempts_still_report_the_original_failure(tmp_path):
  path = write_session(tmp_path / "logs", 1, FAILED + [(1, 0, "attempt_start", {})] + STREAMED[1:])
  session = br.session_record(path)
  assert session["outcome"] == "recovered"
  assert len(session["attempts"]) == 2
  events = []
  br.send_reports(lambda **e: events.append(e) or True, state_path=tmp_path / "state.json", log_dir=path.parent,
                  pairing_path=tmp_path / "pairing.jsonl")
  failure = events[-1]
  assert failure["tags"]["aa.report"] == "failure"
  assert failure["contexts"]["android_auto_diagnosis"]["recovered"] is True
  assert failure["contexts"]["android_auto_diagnosis"]["confidence"] == "suspected"


def test_shutdown_does_not_turn_later_retries_into_stream_drops(tmp_path):
  session = br.session_record(write_session(tmp_path, 1, STREAMED + [
    (2, 0, "session_ended", {"reason": "Head unit ended projection: shutdown"}),
    (2, 2, "stage", {"state": "connecting_bluetooth"}),
    (2, 10, "attempt_failed", {"stage": "connecting_bluetooth", "kind": "OSError", "error": "Host is down"}),
  ]))
  assert session["outcome"] == "streamed" and session["ended_by_car"]
  assert session["failures"] == session["drops"] == 0
  assert session["streamed_s"] == 108
  assert session["attempts"][-1]["after_car_shutdown"]


def test_clock_correction_uses_monotonic_order_and_durations(tmp_path):
  path = write_session(tmp_path, 1, STREAMED)
  events = [json.loads(line) for line in path.read_text().splitlines()]
  for i, event in enumerate(events):
    event["mono_s"] = 20.0 + i
    event["t"] = "2026-07-01T00:00:00+00:00" if i < 5 else "2026-10-19T00:00:00+00:00"
  path.write_text("".join(json.dumps(event) + "\n" for event in events))
  session = br.session_record(path)
  assert session["time_to_first_frame_s"] == 9
  assert session["streamed_s"] == 4
  assert session["timing_source"] == "monotonic"


def test_failed_failure_upload_does_not_advance_session_cursor(tmp_path):
  logs, state = tmp_path / "logs", tmp_path / "state.json"
  write_session(logs, 1, FAILED)
  br.send_reports(lambda **e: e["tags"]["aa.report"] == "drive", state_path=state, log_dir=logs,
                  pairing_path=tmp_path / "pairing.jsonl")
  assert json.loads(state.read_text())["last_seq"] == 0
  captured = []
  br.send_reports(lambda **e: captured.append(e) or True, state_path=state, log_dir=logs,
                  pairing_path=tmp_path / "pairing.jsonl")
  assert captured[-1]["tags"]["aa.report"] == "failure"
  assert json.loads(state.read_text())["last_seq"] == 1


def test_distinct_failures_within_one_session_are_actionable(tmp_path):
  path = write_session(tmp_path / "logs", 1, FAILED + [
    (1, 0, "stage", {"state": "authenticating"}),
    (1, 20, "attempt_failed", {"stage": "authenticating", "kind": "TimeoutError", "error": "timed out"}),
  ])
  events = []
  br.send_reports(lambda **e: events.append(e) or True, state_path=tmp_path / "state.json", log_dir=path.parent,
                  pairing_path=tmp_path / "pairing.jsonl")
  assert {e["tags"].get("aa.cause") for e in events[1:]} == {"wifi_join_failed", "authentication_incomplete"}


def test_nested_pairing_and_failure_fields_are_scrubbed(tmp_path):
  event = br.pairing_event({"result": "failed", "steps": [{"error": "peer fe80::1234 password=secret ssid='My Car'"}]})
  assert "fe80::1234" not in json.dumps(event) and "secret" not in json.dumps(event) and "My Car" not in json.dumps(event)
  path = write_session(tmp_path, 1, FAILED + [(0, 31, "attempt_failed", {
    "stage": "joining_wifi", "kind": "OSError", "error": "Honda HFL password=secret",
  })])
  event = br.failure_event(br.session_record(path))
  assert "Honda HFL" not in json.dumps(event) and "secret" not in json.dumps(event)


def test_unmanaged_is_observed_but_scan_contention_is_only_suspected(tmp_path):
  session = br.session_record(write_session(tmp_path, 1, FAILED))
  session["error"] = "wlan0 is strictly unmanaged"
  observed = br.diagnosis(session)
  assert observed["category"] == "wifi_not_ready" and observed["confidence"] == "observed"
  session["error"] = "Wi-Fi join timed out"
  suspected = br.diagnosis(session)
  assert suspected["category"] == "wifi_join_failed" and suspected["confidence"] == "suspected"


def test_companion_tablet_modes_keep_their_transport(tmp_path):
  for index, transport in enumerate(("headunitpad", "openheadunit"), 1):
    events = [(0, 0, "session_start", {"receiver": transport})] + FAILED[1:]
    session = br.session_record(write_session(tmp_path, index, events))
    assert session["transport"] == transport
    assert br.failure_event(session)["tags"]["aa.transport"] == transport


def test_readable_summary_uses_session_commit_and_wired_connection(tmp_path):
  events = [(0, 0, "session_start", {"receiver": "usb", "software": {"commit": "abc123-session", "branch": "session-branch"}})] + FAILED[1:]
  session = br.session_record(write_session(tmp_path, 1, events))
  event = br.failure_event(session)
  assert "Connection: Wired USB" in event["message"]
  assert "Session commit: abc123-session" in event["message"]
  assert "Branch: session-branch" in event["message"]
  assert "Attempt timeline:" in event["message"] and "Next steps:" in event["message"]
  assert event["tags"]["commit"] == "abc123-session"


def test_legacy_summary_does_not_guess_commit(tmp_path):
  event = br.failure_event(br.session_record(write_session(tmp_path, 1, FAILED)))
  assert "Connection: Wireless" in event["message"]
  assert "Session commit: unknown" in event["message"]
  assert event["tags"]["commit"] == "unknown"


def test_batch_with_different_builds_and_connections_is_explicit(tmp_path):
  sessions = []
  for number, receiver, commit in ((1, "usb", "old-build"), (2, "Car", "new-build")):
    events = [(0, 0, "session_start", {"receiver": receiver, "software": {"commit": commit}})] + FAILED[1:]
    sessions.append(br.session_record(write_session(tmp_path, number, events)))
  event = br.drive_event(sessions)
  assert event["tags"]["aa.transport"] == "mixed" and event["tags"]["commit"] == "mixed"
  assert "Session commit: mixed" in event["message"]
  assert "Wired USB" in event["message"] and "Wireless" in event["message"]
  assert "old-build" in event["message"] and "new-build" in event["message"]


def test_pairing_records_software_when_window_opens(monkeypatch):
  from openpilot.starpilot.system.android_auto import bugsink_transport
  monkeypatch.setattr(bugsink_transport, "device_metadata", lambda: {"commit": "pairing-build", "branch": "pairing-branch"})
  records = []
  attempt = br.PairingAttempt(180, sink=records.append)
  attempt.finish("paired")
  event = br.pairing_event(records[0])
  assert "Session commit: pairing-build" in event["message"]
  assert "Connection: Wireless" in event["message"]
  assert event["tags"]["commit"] == "pairing-build"


def test_supervisor_records_build_at_session_start(monkeypatch):
  import threading
  from openpilot.starpilot.system.android_auto import supervisor, bugsink_transport
  monkeypatch.setattr(bugsink_transport, "device_metadata", lambda: {"commit": "session-build", "branch": "session-branch"})
  records = []

  class Log:
    def open(self):
      pass

    def close(self):
      pass

    def __call__(self, name, **values):
      records.append({"event": name, **values})

  sup = object.__new__(supervisor.Supervisor)
  sup.log = Log()
  sup.config = {"connection": "wired", "receiver_name": ""}
  sup._stop = threading.Event()
  sup._stop.set()
  sup._set = lambda **_: None
  sup._count_dedicated = lambda _: None
  sup._release_phone = lambda: None
  sup._run(1)
  assert records[0]["software"] == {"commit": "session-build", "branch": "session-branch"}
