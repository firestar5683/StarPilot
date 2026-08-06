import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
LAYOUT_PATH = REPO_ROOT / "starpilot/system/the_galaxy/assets/components/tools/device_settings_layout.json"
PARAM_KEYS_PATH = REPO_ROOT / "common/params_keys.h"


def _layout():
  return json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))


def _params_by_section(layout):
  return {
    section["name"]: {param["key"]: param for param in section.get("params", [])}
    for section in layout
  }


def _declared_default(key):
  params_source = PARAM_KEYS_PATH.read_text(encoding="utf-8")
  match = re.search(
    rf'\{{"{re.escape(key)}",\s*\{{[^\n]*?\b(?:BOOL|INT|FLOAT|STRING|JSON),\s*"([^"]*)"',
    params_source,
  )
  assert match is not None, f"Missing param declaration for {key}"
  return match.group(1)


def test_galaxy_layout_removes_obsolete_and_duplicate_controls():
  layout = _layout()
  sections = _params_by_section(layout)
  all_keys = {key for params in sections.values() for key in params}

  assert "Model & Customization" not in sections
  assert {"HumanAcceleration", "ReverseCruise", "DisableWideRoad"}.isdisjoint(all_keys)


def test_galaxy_layout_contains_basic_mode_controls():
  sections = _params_by_section(_layout())

  assert {"AlwaysOnLateral", "LaneChanges", "QOLLateral"} <= sections["Lateral (Steering)"].keys()
  assert {
    "ConditionalExperimental",
    "CurveSpeedController",
    "AccelerationProfile",
    "DecelerationProfile",
    "HumanLaneChanges",
    "QOLLongitudinal",
  } <= sections["Longitudinal (Speed & Following)"].keys()
  assert {"GalaxyDeveloperMode", "UseOldUI"} <= sections["Developer"].keys()


def test_curve_speed_controller_no_lead_toggle_is_nested_under_csc():
  csc_no_lead = _params_by_section(_layout())["Longitudinal (Speed & Following)"]["CurveSpeedControllerNoLead"]

  assert csc_no_lead["parent_key"] == "CurveSpeedController"
  assert csc_no_lead["data_type"] == "bool"
  assert _declared_default("CurveSpeedControllerNoLead") == "0"


def test_every_galaxy_setting_has_a_shared_settings_tier():
  layout = _layout()
  tiers = {
    param.get("settings_tier")
    for section in layout
    for param in section.get("params", [])
  }

  assert tiers <= {"simple", "advanced"}
  assert None not in tiers


def test_requested_simple_and_advanced_settings_tiers():
  sections = _params_by_section(_layout())
  lateral = sections["Lateral (Steering)"]
  longitudinal = sections["Longitudinal (Speed & Following)"]
  developer = sections["Developer"]

  for section_name in (
    "Visual (Display & UI)",
    "Sounds & Alerts",
    "Vehicle",
    "Wheel Controls",
    "Device & Data",
  ):
    assert {param["settings_tier"] for param in sections[section_name].values()} == {"simple"}

  for key in ("AlwaysOnLateral", "LaneChanges", "QOLLateral"):
    assert lateral[key]["settings_tier"] == "simple"
  for key in ("AdvancedLateralTune", "LateralTune", "NavDesiresAllowed", "NavLanePositioningAllowed"):
    assert lateral[key]["settings_tier"] == "advanced"

  for key in (
    "ConditionalExperimental",
    "CurveSpeedController",
    "LongitudinalTune",
    "AccelerationProfile",
    "DecelerationProfile",
    "HumanLaneChanges",
    "QOLLongitudinal",
  ):
    assert longitudinal[key]["settings_tier"] == "simple"
  for key in (
    "AdvancedLongitudinalTune",
    "CustomPersonalities",
    "LeadDetectionThreshold",
    "TacoTune",
    "NavLongitudinalAllowed",
    "SpeedLimitController",
    "ConditionalChill",
  ):
    assert longitudinal[key]["settings_tier"] == "advanced"

  assert developer["GalaxyDeveloperMode"]["settings_tier"] == "simple"
  assert developer["UseOldUI"]["settings_tier"] == "simple"
  assert developer["DeveloperUI"]["settings_tier"] == "advanced"


def test_hidden_feature_defaults_remain_enabled():
  assert _declared_default("GalaxyDeveloperMode") == "0"
  assert _declared_default("NavDesiresAllowed") == "1"
  assert _declared_default("NavLanePositioningAllowed") == "0"
  assert _declared_default("NavLongitudinalAllowed") == "1"

  for key in (
    "TrafficPersonalityProfile",
    "AggressivePersonalityProfile",
    "StandardPersonalityProfile",
    "RelaxedPersonalityProfile",
  ):
    assert _declared_default(key) == "1"


def test_human_acceleration_param_is_removed():
  params_source = PARAM_KEYS_PATH.read_text(encoding="utf-8")
  assert '{"HumanAcceleration",' not in params_source


def test_vasm_is_default_off_and_configured_only_in_galaxy():
  sections = _params_by_section(_layout())
  lateral = sections["Lateral (Steering)"]

  assert {"VASMEnabled", "VASMConfidenceThreshold", "VASMSmoothSeconds"} <= lateral.keys()
  assert _declared_default("VASMEnabled") == "0"

  physical_settings = (
    REPO_ROOT / "selfdrive/ui/layouts/settings/starpilot/aethergrid.py",
    REPO_ROOT / "selfdrive/ui/layouts/settings/starpilot/lateral.py",
  )
  assert all("VASM" not in path.read_text(encoding="utf-8") for path in physical_settings)


def test_pip_preview_is_under_driving_screen_widgets_and_configured_only_in_galaxy():
  sections = _params_by_section(_layout())
  visual = sections["Visual (Display & UI)"]

  assert {"PIPPreviewEnabled", "PIPPreviewShowOnBlinker", "PIPPreviewShowOnBSM"} <= visual.keys()
  assert visual["PIPPreviewEnabled"]["parent_key"] == "CustomUI"
  assert visual["PIPPreviewShowOnBlinker"]["parent_key"] == "PIPPreviewEnabled"
  assert visual["PIPPreviewShowOnBSM"]["parent_key"] == "PIPPreviewEnabled"
  assert visual["PIPPreviewEnabled"]["settings_tier"] == "simple"

  assert _declared_default("PIPPreviewEnabled") == "0"
  assert _declared_default("PIPPreviewShowOnBlinker") == "0"
  assert _declared_default("PIPPreviewShowOnBSM") == "0"
  assert '"{\\"width\\":1928,\\"height\\":1208,\\"center_left\\":[315,548],\\"center_right\\":[1571,539],\\"crop_size\\":580}"' in PARAM_KEYS_PATH.read_text(encoding="utf-8")

  physical_settings = (
    REPO_ROOT / "selfdrive/ui/layouts/settings/starpilot/aethergrid.py",
    REPO_ROOT / "selfdrive/ui/layouts/settings/starpilot/lateral.py",
    REPO_ROOT / "selfdrive/ui/layouts/settings/starpilot/appearance.py",
  )
  assert all("PIPPreview" not in path.read_text(encoding="utf-8") for path in physical_settings)
