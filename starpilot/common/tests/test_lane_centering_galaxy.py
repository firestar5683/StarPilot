import json
from pathlib import Path


_LAYOUT_PATH = Path(__file__).resolve().parents[2] / "system/the_galaxy/assets/components/tools/device_settings_layout.json"


def _sections():
  layout = json.loads(_LAYOUT_PATH.read_text(encoding="utf-8"))
  return {
    section["name"]: {param["key"]: param for param in section["params"]}
    for section in layout
  }


def test_lane_centering_is_only_in_galaxy_developer_section():
  sections = _sections()
  keys = {"LaneCentering", "LaneCenterOffset", "LaneCenteringPauseOnSignal", "LaneCenteringE2EAuthority"}

  assert keys <= sections["Developer"].keys()
  for name, params in sections.items():
    if name != "Developer":
      assert keys.isdisjoint(params)

  for key in keys:
    assert sections["Developer"][key]["settings_tier"] == "advanced"


def test_lane_centering_galaxy_controls():
  developer = _sections()["Developer"]
  centering = developer["LaneCentering"]
  offset = developer["LaneCenterOffset"]
  pause_on_signal = developer["LaneCenteringPauseOnSignal"]
  e2e_authority = developer["LaneCenteringE2EAuthority"]

  assert centering["ui_type"] == "toggle"
  assert centering["is_parent_toggle"] is True

  assert pause_on_signal["ui_type"] == "toggle"
  assert pause_on_signal["parent_key"] == "LaneCentering"

  assert offset["parent_key"] == "LaneCentering"
  assert offset["min"] == -0.3
  assert offset["max"] == 0.3
  assert offset["step"] == 0.01

  assert e2e_authority["parent_key"] == "LaneCentering"
  assert e2e_authority["min"] == 0.0
  assert e2e_authority["max"] == 1.0
  assert e2e_authority["step"] == 0.05
