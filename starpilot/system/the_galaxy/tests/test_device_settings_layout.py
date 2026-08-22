import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
LAYOUT_PATH = REPO_ROOT / "starpilot/common/assets/device_settings_layout.json"
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
  assert {"HumanAcceleration", "ReverseCruise"}.isdisjoint(all_keys)
  assert "DisableWideRoad" in sections["Visual (Display & UI)"]
  assert sum(
    param.get("key") == "DisableWideRoad"
    for section in layout
    for param in section.get("params", [])
  ) == 1


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
  assert "Vision Speed Limits" in sections
  assert "VisionSpeedLimitDetection" not in sections["Longitudinal (Speed & Following)"]
  assert "RedneckCruise" not in sections["Longitudinal (Speed & Following)"].keys()
  assert sections["Developer"]["RedneckCruise"]["parent_key"] == "GalaxyDeveloperMode"
  assert sections["Longitudinal (Speed & Following)"]["PulseGlideSpeedDelta"]["parent_key"] == "QOLLongitudinal"
  assert sections["Longitudinal (Speed & Following)"]["PulseGlideSpeedDelta"]["settings_tier"] == "advanced"
  assert "PulseGlideSpeedDelta" not in sections["Developer"]
  assert {"AlphaLongitudinalEnabled", "ForceOffroad", "GalaxyDeveloperMode"} <= sections["Developer"].keys()


def test_device_shutdown_uses_literal_hours():
  device_shutdown = _params_by_section(_layout())["Device & Data"]["DeviceShutdown"]

  assert _declared_default("DeviceShutdown") == "6"
  assert device_shutdown["min"] == 1
  assert device_shutdown["max"] == 30
  assert device_shutdown["step"] == 1


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


def test_every_setting_parent_exposes_a_manage_control():
  layout = _layout()

  for section in layout:
    params = section.get("params", [])
    parent_keys = {param.get("parent_key") for param in params if param.get("parent_key")}
    params_by_key = {param["key"]: param for param in params}
    for parent_key in parent_keys:
      assert params_by_key[parent_key].get("is_parent_toggle") is True, (
        f"{section['name']} parent {parent_key} must expose its child settings"
      )


def test_requested_simple_and_advanced_settings_tiers():
  sections = _params_by_section(_layout())
  lateral = sections["Lateral (Steering)"]
  longitudinal = sections["Longitudinal (Speed & Following)"]
  vision = sections["Vision Speed Limits"]
  developer = sections["Developer"]

  for section_name in (
    "Visual (Display & UI)",
    "Sounds & Alerts",
    "Vehicle",
    "Wheel Controls",
    "Device & Data",
  ):
    params = sections[section_name].values()
    if section_name == "Visual (Display & UI)":
      params = [
        param for param in params
        if not param["key"].startswith("PIPPreview")
        and param["key"] != "DisableWideRoad"
        and param["key"] != "HomeScreenName"
      ]
    assert {param["settings_tier"] for param in params} == {"simple"}

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
  assert sections["Longitudinal (Speed & Following)"]["CEOpenRoad"]["settings_tier"] == "simple"
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
  assert longitudinal["PulseGlideSpeedDelta"]["settings_tier"] == "advanced"

  assert vision["VisionSpeedLimitDetection"]["settings_tier"] == "advanced"
  assert vision["VisionSpeedLimitLowLimitFilter"]["settings_tier"] == "advanced"
  assert vision["VisionSpeedLimitLowLimitThreshold"]["settings_tier"] == "advanced"

  assert developer["GalaxyDeveloperMode"]["settings_tier"] == "simple"
  assert developer["AlphaLongitudinalEnabled"]["parent_key"] == "GalaxyDeveloperMode"
  assert developer["AlphaLongitudinalEnabled"]["requires_offroad"] is True
  assert developer["AlphaLongitudinalEnabled"]["settings_tier"] == "advanced"
  assert developer["ForceOffroad"]["parent_key"] == "GalaxyDeveloperMode"
  assert developer["ForceOffroad"]["requires_parked"] is True
  assert developer["ForceOffroad"]["settings_tier"] == "advanced"
  assert developer["DeveloperUI"]["settings_tier"] == "advanced"
  assert developer["RedneckCruise"]["settings_tier"] == "advanced"
  assert sections["Visual (Display & UI)"]["DisableWideRoad"]["settings_tier"] == "advanced"
  assert sections["Visual (Display & UI)"]["HomeScreenName"]["settings_tier"] == "advanced"
  assert sections["Visual (Display & UI)"]["HomeScreenName"]["max_length"] == 12


def test_hidden_feature_defaults_remain_enabled():
  assert _declared_default("GalaxyDeveloperMode") == "0"
  assert _declared_default("NavDesiresAllowed") == "1"
  assert _declared_default("NavLanePositioningAllowed") == "0"
  assert _declared_default("NavLongitudinalAllowed") == "1"
  assert _declared_default("CEOpenRoad") == "0"

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


def test_rivian_angle_control_is_harness_gated():
  sections = _params_by_section(_layout())
  setting = sections["Vehicle"]["RivianAngleControl"]

  assert setting["ui_type"] == "toggle"
  assert setting["data_type"] == "bool"
  assert setting["requires_capability"] == "HasRivianAngleHarness"
  assert "reboot" not in setting["description"].lower()
  assert _declared_default("RivianAngleControl") == "0"


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


def test_low_vision_limit_filter_is_default_off_and_configured_only_in_galaxy():
  sections = _params_by_section(_layout())
  vision = sections["Vision Speed Limits"]
  toggle = vision["VisionSpeedLimitLowLimitFilter"]
  threshold = vision["VisionSpeedLimitLowLimitThreshold"]

  assert vision["VisionSpeedLimitDetection"]["is_parent_toggle"] is True
  assert vision["VisionSpeedLimitAutoBookmark"]["is_parent_toggle"] is True
  assert "VisionSpeedLimitDetection" not in sections["Longitudinal (Speed & Following)"]
  assert toggle["is_parent_toggle"] is True
  assert toggle["parent_key"] == "VisionSpeedLimitDetection"
  assert threshold["parent_key"] == "VisionSpeedLimitLowLimitFilter"
  assert threshold["min"] == 5
  assert threshold["max"] == 80
  assert threshold["step"] == 5
  assert _declared_default("VisionSpeedLimitLowLimitFilter") == "0"
  assert _declared_default("VisionSpeedLimitLowLimitThreshold") == "25"
  assert _declared_default("VisionSpeedLimitDetection") == "1"

  physical_settings = (
    REPO_ROOT / "selfdrive/ui/layouts/settings/starpilot/longitudinal.py",
    REPO_ROOT / "selfdrive/ui/layouts/settings/starpilot/aethergrid.py",
  )
  assert all("VisionSpeedLimitLowLimit" not in path.read_text(encoding="utf-8") for path in physical_settings)


def test_pip_preview_is_under_driving_screen_widgets_and_configured_only_in_galaxy():
  sections = _params_by_section(_layout())
  visual = sections["Visual (Display & UI)"]

  assert {"PIPPreviewEnabled", "PIPPreviewShowOnBlinker", "PIPPreviewShowOnBSM"} <= visual.keys()
  assert visual["PIPPreviewEnabled"]["parent_key"] == "CustomUI"
  assert visual["PIPPreviewShowOnBlinker"]["parent_key"] == "PIPPreviewEnabled"
  assert visual["PIPPreviewShowOnBSM"]["parent_key"] == "PIPPreviewEnabled"
  assert visual["PIPPreviewEnabled"]["settings_tier"] == "advanced"
  assert visual["PIPPreviewShowOnBlinker"]["settings_tier"] == "advanced"
  assert visual["PIPPreviewShowOnBSM"]["settings_tier"] == "advanced"

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
