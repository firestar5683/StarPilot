"""Source/JSON contract tests for LaneCentering + LaneCenterOffset UI wiring.

Lightweight: scans Qt sources, the Galaxy layout JSON, and the_galaxy.py
without importing heavy native dependencies.
"""

import json
import re
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]

_QT_CC = (_REPO_ROOT / "starpilot/ui/qt/offroad/lateral_settings.cc").read_text(encoding="utf-8")
_QT_H = (_REPO_ROOT / "starpilot/ui/qt/offroad/lateral_settings.h").read_text(encoding="utf-8")
_GALAXY_PY = (_REPO_ROOT / "starpilot/system/the_galaxy/the_galaxy.py").read_text(encoding="utf-8")
_GALAXY_LAYOUT = json.loads(
  (_REPO_ROOT / "starpilot/system/the_galaxy/assets/components/tools/device_settings_layout.json").read_text(encoding="utf-8")
)


def _lateral_section_params():
  for section in _GALAXY_LAYOUT:
    if section.get("name") == "Lateral (Steering)":
      return {p["key"]: p for p in section["params"]}
  raise AssertionError("Lateral (Steering) section not found in Galaxy layout")


def test_galaxy_lane_centering_toggle_under_advanced_lateral():
  entry = _lateral_section_params()["LaneCentering"]
  assert entry["data_type"] == "bool"
  assert entry["ui_type"] == "toggle"
  assert entry["parent_key"] == "AdvancedLateralTune"
  assert entry.get("is_parent_toggle") is True, "LaneCentering must parent LaneCenterOffset"


def test_galaxy_lane_center_offset_numeric_contract():
  entry = _lateral_section_params()["LaneCenterOffset"]
  assert entry["data_type"] == "float"
  assert entry["ui_type"] == "numeric"
  assert entry["min"] == -0.5
  assert entry["max"] == 0.5
  assert entry["step"] == 0.01
  assert entry["precision"] == 2
  assert entry["parent_key"] == "LaneCentering", "offset must nest under LaneCentering so it only shows when enabled"


def test_qt_tuple_entries_and_constructor_contract():
  assert '{"LaneCentering"' in _QT_CC, "LaneCentering tuple entry missing"
  assert '{"LaneCenterOffset"' in _QT_CC, "LaneCenterOffset tuple entry missing"

  idx = _QT_CC.find('param == "LaneCenterOffset"')
  assert idx != -1, "LaneCenterOffset constructor branch missing"
  window = _QT_CC[idx:idx + 400]
  assert "StarPilotParamValueControl" in window
  assert re.search(r"-0\.5,\s*0\.5", window), "LaneCenterOffset range must be -0.5..0.5"
  assert "0.01" in window, "LaneCenterOffset step must be 0.01"


def test_qt_camera_offset_numeric_contract():
  assert '{"CameraOffset"' in _QT_CC, "CameraOffset tuple entry missing"

  idx = _QT_CC.find('param == "CameraOffset"')
  assert idx != -1, "CameraOffset constructor branch missing"
  window = _QT_CC[idx:idx + 400]
  assert "StarPilotParamValueControl" in window
  assert re.search(r"-0\.35,\s*0\.35", window), "CameraOffset range must be -0.35..0.35"
  assert "0.01" in window, "CameraOffset step must be 0.01"


def test_qt_offset_visibility_gated_on_lane_centering():
  idx = _QT_CC.find('key == "LaneCenterOffset"')
  assert idx != -1, "LaneCenterOffset updateToggles branch missing"
  window = _QT_CC[idx:idx + 300]
  assert 'params.getBool("LaneCentering")' in window, "offset must only show when centering is enabled"

  keys_idx = _QT_CC.find("forceUpdateKeys")
  assert '"LaneCentering"' in _QT_CC[keys_idx:keys_idx + 300], "LaneCentering must trigger updateToggles"


def test_qt_header_advanced_lateral_keys():
  idx = _QT_H.find("advancedLateralTuneKeys")
  assert idx != -1
  window = _QT_H[idx:idx + 400]
  assert '"LaneCentering"' in window
  assert '"LaneCenterOffset"' in window
  assert '"CameraOffset"' in window


def test_galaxy_troubleshoot_advanced_lateral_keys():
  start = _GALAXY_PY.find("_TROUBLESHOOT_ADVANCED_LATERAL_KEYS")
  assert start != -1
  end = _GALAXY_PY.find("]", start)
  block = _GALAXY_PY[start:end]
  assert '"LaneCentering"' in block
  assert '"LaneCenterOffset"' in block
