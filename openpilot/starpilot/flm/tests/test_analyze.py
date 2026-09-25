"""The desktop report joins real local-file admission, decompression and events."""

import json

import pytest
import zstandard as zstd

from openpilot.cereal import messaging
from openpilot.starpilot.flm import analyze
from openpilot.starpilot.flm.local_logs import LocalLogUnavailable


SEGMENT = "1234abcd--0123456789--0"


def test_desktop_report_for_missing_controller_is_honest_and_source_bound(tmp_path, monkeypatch, capsys):
  monkeypatch.setattr(analyze, "PC", True)
  folder = tmp_path / SEGMENT
  folder.mkdir()
  event = messaging.new_message("carState", valid=True)
  event.logMonoTime = 100
  (folder / "rlog.zst").write_bytes(zstd.compress(event.to_bytes()))
  assert analyze.main(["--log-root", str(tmp_path.resolve()), SEGMENT]) == 0
  report = json.loads(capsys.readouterr().out)
  assert report["purpose"] == "offline_tracking_diagnostics"
  assert report["vehicleQualification"] is False and report["tuneRecommendation"] is None
  segment = report["segments"][0]
  assert segment["analysis"]["status"] == "missing_car_params"
  assert segment["analysis"]["mean_abs_error"] is None
  assert len(segment["source"]["sha256"]) == 64
  assert segment["source"]["segmentName"] == SEGMENT
  output = tmp_path / "report.json"
  args = ["--log-root", str(tmp_path.resolve()), "--output", str(output), SEGMENT]
  assert analyze.main(args) == 0
  assert json.loads(output.read_text()) == report
  original = output.read_bytes()
  assert analyze.main(args) == 1
  assert output.read_bytes() == original


def test_device_duplicate_and_failed_second_segment_never_emit_partial_report(tmp_path, monkeypatch, capsys):
  monkeypatch.setattr(analyze, "PC", False)
  with pytest.raises(ValueError, match="desktop"):
    analyze.analyze_local(tmp_path.resolve(), [SEGMENT])
  monkeypatch.setattr(analyze, "PC", True)
  with pytest.raises(ValueError, match="distinct"):
    analyze.analyze_local(tmp_path.resolve(), [SEGMENT, SEGMENT])
  folder = tmp_path / SEGMENT
  folder.mkdir()
  event = messaging.new_message("carState", valid=True)
  (folder / "rlog.zst").write_bytes(zstd.compress(event.to_bytes()))
  assert analyze.main(["--log-root", str(tmp_path.resolve()), SEGMENT, "1234abcd--0123456789--1"]) == 1
  assert capsys.readouterr().out == ""
  with pytest.raises(LocalLogUnavailable):
    analyze.analyze_local(tmp_path.resolve(), [SEGMENT], cancelled=lambda: True)
