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
  assert "HumanAcceleration" not in all_keys
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


def test_ford_lateral_controls_are_ford_only_and_galaxy_only():
  lateral = _params_by_section(_layout())["Lateral (Steering)"]
  ford_keys = {
    "FordHumanTurnDetection",
    "FordHandsFreeCluster",
    "FordCurvatureBlendLow",
    "FordCurvatureBlendHigh",
    "FordCurvatureLaneChangeFactor",
  }
  retired_ford_keys = {
    "FordLateralMode",
    "FordAngleBlend",
    "FordAngleLowSpeedFactor",
    "FordAngleHighSpeedFactor",
    "FordAngleHighSpeedDamping",
    "FordAngleLaneChangeFactor",
  }

  assert ford_keys <= lateral.keys()
  assert retired_ford_keys.isdisjoint(lateral)
  assert all(lateral[key]["galaxy_only"] is True for key in ford_keys)
  assert all(lateral[key]["vehicle_makes"] == ["Ford"] for key in ford_keys)
  assert all(lateral[key]["settings_tier"] == "simple" for key in ford_keys)
  assert all("visible_when_key" not in lateral[key] for key in ford_keys)
  assert all("parent_key" not in lateral[key] for key in ford_keys)

  device_ui_root = REPO_ROOT / "selfdrive/ui"
  for path in device_ui_root.rglob("*.py"):
    source = path.read_text(encoding="utf-8")
    assert all(key not in source for key in ford_keys)


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


def test_curve_speed_controller_readouts_are_display_only_and_nested():
  csc = _params_by_section(_layout())["Longitudinal (Speed & Following)"]

  for key, unit in (("CalibratedLateralAcceleration", " m/s²"), ("CalibrationProgress", "%")):
    readout = csc[key]
    assert readout["ui_type"] == "readout"
    assert readout["parent_key"] == "CurveSpeedController"
    assert readout["unit"] == unit
    assert readout["settings_tier"] == "simple"


def test_custom_accel_profile_exposes_variable_breakpoints():
  longitudinal = _params_by_section(_layout())["Longitudinal (Speed & Following)"]
  point_count = longitudinal["CustomAccelProfilePointCount"]

  assert point_count["parent_key"] == "CustomAccelProfile"
  assert point_count["min"] == 2
  assert point_count["max"] == 12
  assert _declared_default("CustomAccelProfilePointCount") == "7"

  for point in range(1, 13):
    speed = longitudinal[f"CustomAccelProfileBreakpoint{point}MPH"]
    accel = longitudinal[f"CustomAccelProfilePoint{point}Accel"]
    assert speed["parent_key"] == "CustomAccelProfile"
    assert accel["parent_key"] == "CustomAccelProfile"
    assert _declared_default(speed["key"]) is not None
    assert _declared_default(accel["key"]) is not None

    if point > 2:
      expected_counts = list(range(point, 13))
      assert speed["visible_when_values"] == expected_counts
      assert accel["visible_when_values"] == expected_counts


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


def test_turn_steering_limit_mute_speed_is_galaxy_developer_only():
  sections = _params_by_section(_layout())
  setting = sections["Developer"]["TurnSteeringLimitMuteSpeed"]

  assert setting["parent_key"] == "GalaxyDeveloperMode"
  assert setting["settings_tier"] == "advanced"
  assert setting["data_type"] == "int"
  assert setting["min"] == 0.0
  assert setting["max"] == 99.0
  assert _declared_default("TurnSteeringLimitMuteSpeed") == "0"

  physical_settings = (
    REPO_ROOT / "selfdrive/ui/layouts/settings/starpilot/sounds.py",
    REPO_ROOT / "selfdrive/ui/layouts/settings/starpilot/aethergrid.py",
  )
  assert all("TurnSteeringLimitMuteSpeed" not in path.read_text(encoding="utf-8") for path in physical_settings)


def test_honda_pid_scale_controls_use_galaxy_fine_granularity():
  developer = _params_by_section(_layout())["Developer"]

  for key in ("HondaLateralPidKpScale", "HondaLateralPidKiScale"):
    setting = developer[key]
    assert setting["step"] == 0.01
    assert setting["precision"] == 2
    assert setting["settings_tier"] == "advanced"


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


def test_toyota_auto_hold_is_galaxy_only():
  setting = _params_by_section(_layout())["Vehicle"]["ToyotaAutoHold"]
  assert setting["galaxy_only"] is True
  assert setting["ui_type"] == "toggle"
  assert setting["data_type"] == "bool"


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

  assert {"PIPPreviewEnabled", "PIPPreviewShowOnBlinker", "PIPPreviewShowOnBSM", "PIPPreviewInvert"} <= visual.keys()
  assert visual["PIPPreviewEnabled"]["parent_key"] == "CustomUI"
  assert visual["PIPPreviewShowOnBlinker"]["parent_key"] == "PIPPreviewEnabled"
  assert visual["PIPPreviewShowOnBSM"]["parent_key"] == "PIPPreviewEnabled"
  assert visual["PIPPreviewInvert"]["parent_key"] == "PIPPreviewEnabled"
  assert visual["PIPPreviewEnabled"]["settings_tier"] == "advanced"
  assert visual["PIPPreviewShowOnBlinker"]["settings_tier"] == "advanced"
  assert visual["PIPPreviewShowOnBSM"]["settings_tier"] == "advanced"
  assert visual["PIPPreviewInvert"]["settings_tier"] == "advanced"

  assert _declared_default("PIPPreviewEnabled") == "0"
  assert _declared_default("PIPPreviewShowOnBlinker") == "0"
  assert _declared_default("PIPPreviewShowOnBSM") == "0"
  assert _declared_default("PIPPreviewInvert") == "0"
  annotation_default = (
    '"{\\"width\\":1928,\\"height\\":1208,\\"center_left\\":[315,548],' +
    '\\"center_right\\":[1571,539],\\"crop_size\\":580}"'
  )
  assert annotation_default in PARAM_KEYS_PATH.read_text(encoding="utf-8")

  physical_settings = (
    REPO_ROOT / "selfdrive/ui/layouts/settings/starpilot/aethergrid.py",
    REPO_ROOT / "selfdrive/ui/layouts/settings/starpilot/lateral.py",
    REPO_ROOT / "selfdrive/ui/layouts/settings/starpilot/appearance.py",
  )
  assert all("PIPPreview" not in path.read_text(encoding="utf-8") for path in physical_settings)
