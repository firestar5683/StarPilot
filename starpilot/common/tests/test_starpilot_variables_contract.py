"""Source-contract tests for lane-centering Params (run without importing spv).

These tests assert the exact loader contract by scanning starpilot_variables.py.
They run standalone without heavy native dependencies (msgq/ipc_pyx.so).
The loaders are kept in one AdvancedLateralTune block with explicit bounds.
"""

import re
from pathlib import Path

import pytest


_STARPILOT_VARIABLES_SOURCE = (
  Path(__file__).resolve().parent.parent / "starpilot_variables.py"
).read_text(encoding="utf-8")


def _advanced_lateral_block(source: str = _STARPILOT_VARIABLES_SOURCE) -> str:
  start = source.find("advanced_lateral_tuning = ")
  assert start != -1, "advanced_lateral_tuning block not found"
  end = source.find("advanced_longitudinal_tuning = ", start)
  assert end != -1, "advanced_longitudinal_tuning boundary not found"
  return source[start:end]


def _loader_window(block: str, key: str, before: int = 400, after: int = 400) -> str:
  idx = block.find(f'"{key}"')
  assert idx != -1, f"{key} must be loaded inside AdvancedLateralTune block"
  return block[max(0, idx - before): idx + after]


def test_lane_centering_bool_loader_wired_under_advanced_lateral_gate():
  block = _advanced_lateral_block()
  window = _loader_window(block, "LaneCentering", before=120, after=200)
  assert "get_value" in window, "LaneCentering must be loaded via get_value"
  assert "cast=float" not in window, "LaneCentering must be a bool loader, not float"


def test_lane_center_offset_float_loader_clamped_to_half_meter():
  window = _loader_window(_advanced_lateral_block(), "LaneCenterOffset", before=0, after=400)
  assert "cast=float" in window, "LaneCenterOffset must be cast to float"
  assert "min=-0.5" in window, "LaneCenterOffset must clamp min=-0.5"
  assert "max=0.5" in window, "LaneCenterOffset must clamp max=0.5"


def test_lane_centering_loaders_appear_once_each():
  for key in ("LaneCentering", "LaneCenterOffset"):
    count = _STARPILOT_VARIABLES_SOURCE.count(f'"{key}"')
    assert count == 1, f"{key} must be loaded exactly once (got {count})"


@pytest.mark.parametrize(
  "key, lo, hi",
  [
    ("LaneCenterOffset", -0.5, 0.5),
  ],
)
def test_offset_keys_use_symmetric_clamps(key, lo, hi):
  window = _loader_window(_advanced_lateral_block(), key, before=0, after=400)
  assert f"min={lo}" in window, f"{key} must clamp min={lo}"
  assert f"max={hi}" in window, f"{key} must clamp max={hi}"
