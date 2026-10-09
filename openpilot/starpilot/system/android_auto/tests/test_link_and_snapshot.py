"""Streaming survives a slow Wi-Fi check, and the log bundle carries the device's side of a failure."""

import io
import json
import time
import zipfile

from openpilot.starpilot.system.android_auto import compat_report, system_snapshot
from openpilot.starpilot.system.android_auto.supervisor import LinkWatch, _where


class Recorder:
  def __init__(self):
    self.events = []

  def __call__(self, name, **values):
    self.events.append({"event": name, **values})

  def named(self, name):
    return [event for event in self.events if event["event"] == name]


def wait_until(condition, timeout=2.0):
  deadline = time.monotonic() + timeout
  while time.monotonic() < deadline:
    if condition():
      return True
    time.sleep(0.01)
  return False


class SlowLease:
  """NetworkManager not answering: jeepney's Future.result raises a bare TimeoutError."""
  def __init__(self):
    self.calls = 0

  def still_connected(self):
    self.calls += 1
    raise TimeoutError()


class DroppedLease:
  lost = "Lost the car's Wi-Fi network"

  def still_connected(self):
    return False


def test_link_check_timeout_is_logged_with_its_location_but_does_not_end_the_session():
  log = Recorder()
  lease = SlowLease()
  watch = LinkWatch(lease, log, interval=0.01).start()
  try:
    assert wait_until(lambda: lease.calls >= 3)
  finally:
    watch.stop()
  assert watch.lost == ""
  failure = log.named("link_check_failed")[0]
  assert failure["kind"] == "TimeoutError" and failure["error"] == "TimeoutError"
  assert failure["where"][-1].startswith("test_link_and_snapshot.py:")


def test_a_definite_disconnect_is_still_reported():
  log = Recorder()
  watch = LinkWatch(DroppedLease(), log, interval=0.01).start()
  assert wait_until(lambda: watch.lost)
  watch.stop()
  assert watch.lost == "Lost the car's Wi-Fi network"
  assert log.named("link_lost")


def test_where_names_the_innermost_frames():
  def inner():
    raise TimeoutError()
  try:
    inner()
  except TimeoutError as error:
    where = _where(error)
  assert where[-1].endswith(" inner") and where[-1].startswith("test_link_and_snapshot.py:")


def test_redact_masks_hardware_addresses_to_their_last_byte():
  text = b'dev_B0_D8_88_7D_AD_EC bssid B2:d8:88:7D:AE:EA mac 00-11-22-33-44-55 at 16:27:56.158 id deadbeefcafe'
  masked = system_snapshot.redact(text).decode()
  assert "dev_xx_xx_xx_xx_xx_EC" in masked and "xx:xx:xx:xx:xx:EA" in masked and "xx-xx-xx-xx-xx-55" in masked
  assert "B0_D8" not in masked and "16:27:56.158" in masked and "deadbeefcafe" in masked


def test_window_starts_before_the_oldest_session_and_at_most_a_day_back():
  from datetime import datetime
  now = 1_800_000_000.0
  oldest = "2027-01-15T08:00:00+00:00"
  start = datetime.fromisoformat(oldest).timestamp()
  assert system_snapshot.window_start([oldest, "", "bad"], now=start + 3600) == start - system_snapshot.WINDOW_MARGIN_SECONDS
  assert system_snapshot.window_start([oldest], now=start + 5 * 86400) == start + 4 * 86400
  assert system_snapshot.window_start([], now=now) == now - system_snapshot.DEFAULT_WINDOW_SECONDS


def test_collect_runs_commands_together_under_one_deadline():
  started = time.monotonic()
  files = system_snapshot.collect(0.0, deadline=1.0, command_set={
    "fast.txt": ["sh", "-c", "echo peer AA:BB:CC:DD:EE:01"],
    "hung.txt": ["sh", "-c", "echo partial; sleep 30"],
    "slow.txt": ["sh", "-c", "sleep 0.5; echo done"],
    "missing.txt": ["/nonexistent/aa-tool"],
  })
  assert time.monotonic() - started < 4.0
  assert files["fast.txt"] == b"peer xx:xx:xx:xx:xx:01\n"
  assert files["slow.txt"] == b"done\n"
  manifest = json.loads(files["manifest.json"])["commands"]
  assert manifest["fast.txt"]["exit"] == 0
  assert "timed out" in manifest["hung.txt"]["error"]
  assert manifest["missing.txt"]["error"]
  assert "proc.txt" in files


def test_bundle_adds_the_snapshot_and_masks_addresses_in_session_logs(tmp_path):
  logs = tmp_path / "logs"
  logs.mkdir()
  (logs / "session-000001-20261008-122756.jsonl").write_text("".join(json.dumps(event) + "\n" for event in (
    {"t": "2026-10-08T16:27:56.158+00:00", "event": "session_start", "receiver": "Boobli", "trigger": "onroad"},
    {"t": "2026-10-08T16:27:56.414+00:00", "event": "hfp_connected", "device": "dev_B0_D8_88_7D_AD_EC"},
    {"t": "2026-10-08T16:28:18.521+00:00", "event": "attempt_failed", "stage": "streaming", "error": "projecting: TimeoutError",
     "kind": "TimeoutError", "where": ["supervisor.py:1067 _stream", "network.py:112 _get"]},
    {"t": "2026-10-08T16:28:18.600+00:00", "event": "stream_stall", "ms": 8000, "focused": False, "pending": 0},
  )))
  windows = []

  def snapshot(since):
    windows.append(since)
    return {"journal_network.log": b"wlan0: associated\n", "manifest.json": b"{}"}

  with zipfile.ZipFile(io.BytesIO(compat_report.bundle(logs, tmp_path / "config.json", snapshot=snapshot))) as archive:
    assert archive.read("system/journal_network.log") == b"wlan0: associated\n"
    session = archive.read("logs/session-000001-20261008-122756.jsonl").decode()
    report = archive.read("REPORT.txt").decode()
  assert "B0_D8" not in session and "dev_xx_xx_xx_xx_xx_EC" in session
  assert "[at network.py:112 _get]" in report and "stream stall x1 (max 8000 ms)" in report
  from datetime import datetime
  assert windows == [datetime.fromisoformat("2026-10-08T16:27:56.158+00:00").timestamp() - system_snapshot.WINDOW_MARGIN_SECONDS] \
    or windows[0] >= datetime.now().timestamp() - system_snapshot.MAX_WINDOW_SECONDS - 5


def test_snapshot_that_does_not_fit_is_left_out(tmp_path, monkeypatch):
  monkeypatch.setattr(compat_report, "MAX_BUNDLE_BYTES", 4096)
  data = compat_report.bundle(tmp_path, tmp_path / "config.json", snapshot=lambda since: {"big.log": b"x" * 8192})
  with zipfile.ZipFile(io.BytesIO(data)) as archive:
    assert "system/big.log" not in archive.namelist()
