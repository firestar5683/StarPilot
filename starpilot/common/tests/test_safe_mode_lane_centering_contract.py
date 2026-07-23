from pathlib import Path


_SOURCE = (Path(__file__).resolve().parent.parent / "safe_mode.py").read_text(encoding="utf-8")


def test_safe_mode_manages_lane_centering_settings():
  block = _SOURCE[_SOURCE.index("SAFE_MODE_MANAGED_KEYS = ("):_SOURCE.index(")", _SOURCE.index("SAFE_MODE_MANAGED_KEYS = ("))]
  assert chr(34) + "LaneCentering" + chr(34) in block
  assert chr(34) + "LaneCenterOffset" + chr(34) in block
