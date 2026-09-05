import csv
import sys
from types import ModuleType, SimpleNamespace

# cpu_capture -> starpilot_variables -> cereal.messaging pulls the native msgq
# extension, which won't load on non-device dev machines. Stub it so the pure
# helpers under test can be imported. run_capture_loop imports messaging lazily
# and is tested below with a fake SubMaster.
if "cereal.messaging" not in sys.modules:
  _messaging_stub = ModuleType("cereal.messaging")
  _messaging_stub.SubMaster = object
  sys.modules["cereal.messaging"] = _messaging_stub

import pytest

from openpilot.starpilot.system.the_galaxy import cpu_capture


def _proc(pid, name, cpu_user, cpu_system=0.0):
  return SimpleNamespace(pid=pid, name=name, cpuUser=cpu_user, cpuSystem=cpu_system)


def test_first_sample_seeds_totals_without_usage():
  procs = [_proc(1, "selfdrived", 10.0), _proc(2, "modeld", 5.0)]
  usage, totals = cpu_capture.compute_process_cpu(procs, {}, dt=None)
  assert usage == []
  assert totals == {1: 10.0, 2: 5.0}


def test_second_sample_computes_sorted_percent():
  prev = {1: 10.0, 2: 5.0, 3: 0.0}
  # over 2s: selfdrived +1.2s cpu -> 60%, modeld +0.4s -> 20%, idle proc +0 -> dropped
  procs = [_proc(1, "selfdrived", 10.8, 0.4), _proc(2, "modeld", 5.4), _proc(3, "idle", 0.0)]
  usage, totals = cpu_capture.compute_process_cpu(procs, prev, dt=2.0)
  assert [name for name, _ in usage] == ["selfdrived", "modeld"]
  assert usage[0][1] == pytest.approx(60.0)
  assert usage[1][1] == pytest.approx(20.0)
  assert totals[1] == pytest.approx(11.2)


def test_percent_clamped_to_max():
  prev = {1: 0.0}
  procs = [_proc(1, "busy", 100.0)]
  usage, _ = cpu_capture.compute_process_cpu(procs, prev, dt=1.0, max_pct=400.0)
  assert usage == [("busy", 400.0)]


def test_format_top_procs_limits_and_sanitizes():
  usage = [("a b", 31.4), ("c:d", 12.6), ("e", 5.0), ("f", 1.0)]
  assert cpu_capture.format_top_procs(usage, top_n=2) == "a_b:31 cd:13"


def test_build_capture_fields():
  ds = SimpleNamespace(
    cpuUsagePercent=[55, 38, 40, 35],
    cpuTempC=[60.1, 62.4, 61.0],
    gpuTempC=[58.0],
    memoryUsagePercent=48,
    started=True,
  )
  fields = cpu_capture.build_capture_fields("2026-09-04T12:00:00", ds, "selfdrived:31")
  assert fields == ["2026-09-04T12:00:00", 42, "[55,38,40,35]", 62.4, 58.0, 48, "onroad", "selfdrived:31"]


def test_build_capture_fields_handles_missing_data():
  ds = SimpleNamespace(cpuUsagePercent=[], cpuTempC=[], gpuTempC=None, memoryUsagePercent=None, started=False)
  fields = cpu_capture.build_capture_fields("t", ds, "")
  assert fields == ["t", "", "[]", "", "", "", "offroad", ""]


def test_append_row_writes_header_once_and_counts(tmp_path):
  path = tmp_path / "cap.csv"
  cpu_capture.append_capture_row(["t1", 10, "[10]", 50, 40, 20, "onroad", "a:1"], path=path)
  cpu_capture.append_capture_row(["t2", 20, "[20]", 51, 41, 21, "onroad", "b:2"], path=path)

  contents = path.read_text().splitlines()
  assert contents[0] == cpu_capture.CSV_HEADER
  assert len(contents) == 3

  status = cpu_capture.capture_status(path)
  assert status["exists"] is True
  assert status["rows"] == 2


def test_cores_with_commas_are_quoted(tmp_path):
  path = tmp_path / "cap.csv"
  cpu_capture.append_capture_row(["t", 42, "[55,38,40,35]", 60, 50, 30, "onroad", "x:1 y:2"], path=path)
  # Round-trips through csv without splitting the bracketed core list into extra columns.
  import csv
  with open(path, newline="") as f:
    rows = list(csv.reader(f))
  assert rows[1][2] == "[55,38,40,35]"
  assert len(rows[1]) == 8


def test_rolling_cap_drops_oldest(tmp_path):
  path = tmp_path / "cap.csv"
  # Tiny cap forces frequent trims; oldest rows should fall off, header stays.
  for i in range(200):
    cpu_capture.append_capture_row([f"t{i}", i, "[0]", 0, 0, 0, "onroad", ""], path=path, max_bytes=400)

  assert path.stat().st_size <= 400
  lines = path.read_text().splitlines()
  assert lines[0] == cpu_capture.CSV_HEADER
  # Newest row retained, an early row evicted.
  assert any(line.startswith("t199,") for line in lines[1:])
  assert not any(line.startswith("t0,") for line in lines[1:])


def test_rolling_cap_drops_row_that_cannot_fit(tmp_path):
  path = tmp_path / "cap.csv"
  cpu_capture.append_capture_row(["t", 42, "[0]", 0, 0, 0, "onroad", "x" * 500], path=path, max_bytes=200)

  assert path.stat().st_size <= 200
  assert path.read_text() == f"{cpu_capture.CSV_HEADER}\n"


def test_drive_marker_written_and_excluded_from_row_count(tmp_path):
  path = tmp_path / "cap.csv"
  cpu_capture.append_drive_marker("2026-09-04T12:00:00", path=path)
  cpu_capture.append_capture_row(["t1", 10, "[10]", 50, 40, 20, "onroad", "a:1"], path=path)
  cpu_capture.append_capture_row(["t2", 20, "[20]", 51, 41, 21, "onroad", "b:2"], path=path)

  with open(path, newline="") as f:
    rows = list(csv.reader(f))
  assert rows[0] == cpu_capture.CSV_HEADER.split(",")
  assert all(len(row) == 8 for row in rows)
  assert rows[1][0] == "2026-09-04T12:00:00"
  assert rows[1][6] == cpu_capture.DRIVE_MARKER_STATE

  # Marker row is valid CSV but is not counted as a sample.
  assert cpu_capture.capture_status(path)["rows"] == 2

  # Every physical row remains rectangular for ordinary CSV readers.
  data_rows = [row for row in rows[1:] if row[6] != cpu_capture.DRIVE_MARKER_STATE]
  assert len(data_rows) == 2


def test_marker_survives_rolling_trim(tmp_path):
  path = tmp_path / "cap.csv"
  cpu_capture.append_drive_marker("t0", path=path, max_bytes=400)
  for i in range(200):
    cpu_capture.append_capture_row([f"t{i}", i, "[0]", 0, 0, 0, "onroad", ""], path=path, max_bytes=400)

  # Trim keeps the header first and never corrupts it, even with a marker present.
  lines = path.read_text().splitlines()
  assert lines[0] == cpu_capture.CSV_HEADER
  assert path.stat().st_size <= 400


def test_capture_status_handles_legacy_comment_marker(tmp_path):
  path = tmp_path / "cap.csv"
  path.write_text(f"{cpu_capture.CSV_HEADER}\n# ==== NEW DRIVE 2026-09-04T12:00:00\nt1,10,[10],50,40,20,onroad,a:1\n")

  assert cpu_capture.capture_status(path)["rows"] == 1


def test_capture_status_missing_file(tmp_path):
  status = cpu_capture.capture_status(tmp_path / "nope.csv")
  assert status["exists"] is False
  assert status["rows"] == 0
  assert status["intervalS"] == cpu_capture.CAPTURE_INTERVAL_S


def test_device_path_detection_handles_agnos_marker(monkeypatch, tmp_path):
  monkeypatch.setattr(cpu_capture, "PC", True)
  agnos = tmp_path / "AGNOS"
  agnos.touch()

  assert cpu_capture._is_comma_device_runtime(marker_paths=(agnos,), model_path=tmp_path / "model")


def test_capture_loop_ignores_stale_device_state(monkeypatch, tmp_path):
  class Stop:
    stopped = False

    def is_set(self):
      return self.stopped

  stop = Stop()

  class FakeSubMaster:
    def __init__(self, services):
      assert services == ["deviceState", "procLog"]
      self.valid = {"deviceState": True, "procLog": True}
      self.alive = {"deviceState": False, "procLog": False}

    def update(self, _timeout_ms):
      stop.stopped = True

  monkeypatch.setitem(sys.modules, "cereal.messaging", SimpleNamespace(SubMaster=FakeSubMaster))
  monkeypatch.setattr(cpu_capture, "append_capture_row", lambda *args, **kwargs: pytest.fail("stale device state was captured"))
  monkeypatch.setattr(cpu_capture, "append_drive_marker", lambda *args, **kwargs: pytest.fail("stale drive marker was captured"))

  path = tmp_path / "cap.csv"
  cpu_capture.run_capture_loop(stop_event=stop, path=path)

  assert not path.exists()
