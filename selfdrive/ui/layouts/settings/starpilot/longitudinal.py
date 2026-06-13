from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Callable

import pyray as rl

from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.system.ui.lib.application import FontWeight, MouseEvent, MousePos, gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.lib.scroll_panel2 import GuiScrollPanel2
from openpilot.system.ui.widgets import DialogResult, Widget
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
from openpilot.system.ui.widgets.keyboard import Keyboard
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog

from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import StarPilotPanel, _SettingsPage

from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  AETHER_LIST_METRICS,
  AetherInteractiveMixin,
  AetherListColors,
  AetherScrollbar,
  AetherSliderDialog,
  panel_style_from_color,
  _point_hits,
  draw_list_group_shell,
  draw_list_scroll_fades,
  draw_section_header,
  draw_selection_list_row,
  draw_settings_list_row,
  draw_settings_panel_header,
  draw_tab_bar,
  init_list_panel,
)

from openpilot.starpilot.common.accel_profile import (
  ACCELERATION_PROFILES,
  DECELERATION_PROFILES,
  normalize_acceleration_profile,
  normalize_deceleration_profile,
)
from openpilot.starpilot.common.experimental_state import sync_persist_experimental_state


PANEL_STYLE = panel_style_from_color("#3B82F6")
COMPACT_PANEL_METRICS = replace(AETHER_LIST_METRICS, header_height=96)  # noqa: re-exported
SECTION_GAP = AETHER_LIST_METRICS.section_gap
SECTION_HEADER_HEIGHT = AETHER_LIST_METRICS.section_header_height
SECTION_HEADER_GAP = AETHER_LIST_METRICS.section_header_gap
ROW_HEIGHT = AETHER_LIST_METRICS.row_height

ACCELERATION_PROFILE_OPTIONS = [
  (ACCELERATION_PROFILES["STANDARD"], "Standard"),
  (ACCELERATION_PROFILES["ECO"], "Eco"),
  (ACCELERATION_PROFILES["SPORT"], "Sport"),
  (ACCELERATION_PROFILES["SPORT_PLUS"], "Sport+"),
]

DECELERATION_PROFILE_OPTIONS = [
  (DECELERATION_PROFILES["STANDARD"], "Standard"),
  (DECELERATION_PROFILES["ECO"], "Eco"),
  (DECELERATION_PROFILES["SPORT"], "Sport"),
]


# Backward-compat re-exports (these symbols now live in aethergrid.py)
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  SettingRow, SettingSection, AetherSettingsView,
)


# ═══════════════════════════════════════════════════════════════
# Top-level layout — StarPilotLongitudinalLayout
# ═══════════════════════════════════════════════════════════════

class StarPilotLongitudinalLayout(_SettingsPage):
  def __init__(self):
    super().__init__()

    longitudinal_tune_panel = StarPilotLongitudinalTuneLayout()
    advanced_longitudinal_panel = StarPilotAdvancedLongitudinalLayout()
    personalities_panel = StarPilotPersonalitiesLayout()
    traffic_profile = StarPilotPersonalityProfileLayout("Traffic")
    aggressive_profile = StarPilotPersonalityProfileLayout("Aggressive")
    standard_profile = StarPilotPersonalityProfileLayout("Standard")
    relaxed_profile = StarPilotPersonalityProfileLayout("Relaxed")

    conditional_panel = StarPilotConditionalExperimentalLayout()
    curve_panel = StarPilotCurveSpeedLayout()
    weather_panel = StarPilotWeatherLayout()
    weather_low = StarPilotWeatherBase("LowVisibility")
    weather_rain = StarPilotWeatherBase("Rain")
    weather_rainstorm = StarPilotWeatherBase("RainStorm")
    weather_snow = StarPilotWeatherBase("Snow")

    slc_offsets = StarPilotSLCOffsetsLayout()
    slc_qol = StarPilotSLCQOLLayout()
    slc_visuals = StarPilotSLCVisualsLayout()

    self._sub_panels = {
      "tuning": longitudinal_tune_panel,
      "advanced": advanced_longitudinal_panel,
      "personalities": personalities_panel,
      "traffic_personality": traffic_profile,
      "aggressive_personality": aggressive_profile,
      "standard_personality": standard_profile,
      "relaxed_personality": relaxed_profile,
      "conditional": conditional_panel,
      "curve": curve_panel,
      "weather": weather_panel,
      "low_visibility": weather_low,
      "rain": weather_rain,
      "rainstorm": weather_rainstorm,
      "snow": weather_snow,
      "slc_offsets": slc_offsets,
      "slc_qol": slc_qol,
      "slc_visuals": slc_visuals,
    }

    self._wire_sub_panels()
    self._build_view()

  def _build_view(self):
    tab_defs = [
      {"id": "tune", "title": tr_noop("Tune"), "subtitle": tr_noop("Tuning profiles")},
      {"id": "adaptive", "title": tr_noop("Adaptive"), "subtitle": tr_noop("Road-aware speed control")},
      {"id": "limits", "title": tr_noop("Limits"), "subtitle": tr_noop("Speed limit controller")},
      {"id": "daily", "title": tr_noop("Daily"), "subtitle": tr_noop("Quality of life tweaks")},
    ]

    sections: list[SettingSection] = [
      # ── Tune tab ──
      SettingSection(tr_noop("Longitudinal Tuning"), [
        SettingRow("LongitudinalTune", "toggle", tr_noop("Longitudinal Tuning"),
                   subtitle=tr_noop("Acceleration and braking control changes to fine-tune how openpilot drives."),
                   get_state=lambda: self._params.get_bool("LongitudinalTune"),
                   set_state=lambda s: self._params.put_bool("LongitudinalTune", s)),
        SettingRow("TuneConfigure", "value", tr_noop("Configure"),
                   subtitle=tr_noop("Open acceleration profiles, human-like behavior, lead detection, and turn-speed controls."),
                   get_value=lambda: tr_noop("Manage"),
                   navigate_to="tuning",
                   enabled=lambda: self._params.get_bool("LongitudinalTune"),
                   disabled_label=tr_noop("Enable First")),
      ], tab_key="tune"),
      SettingSection(tr_noop("Advanced"), [
        SettingRow("AdvancedTune", "toggle", tr_noop("Advanced Longitudinal Tuning"),
                   subtitle=tr_noop("Advanced acceleration and braking changes for refining launch, stopping, and actuator response."),
                   get_state=lambda: self._params.get_bool("AdvancedLongitudinalTune"),
                   set_state=lambda s: self._params.put_bool("AdvancedLongitudinalTune", s)),
        SettingRow("AdvancedConfigure", "value", tr_noop("Configure"),
                   subtitle=tr_noop("Adjust actuator delay, launch and stop behavior, and powertrain-specific tuning options."),
                   get_value=lambda: tr_noop("Manage"),
                   navigate_to="advanced",
                   enabled=lambda: self._params.get_bool("AdvancedLongitudinalTune"),
                   disabled_label=tr_noop("Enable First")),
      ], tab_key="tune"),
      SettingSection(tr_noop("Driving Personalities"), [
        SettingRow("PersonalitiesConfigure", "value", tr_noop("Configure"),
                   subtitle=tr_noop("Customize the Traffic, Aggressive, Standard, and Relaxed profiles to match your driving style."),
                   get_value=lambda: tr_noop("Manage"),
                   navigate_to="personalities"),
      ], tab_key="tune"),

      # ── Adaptive tab ──
      SettingSection(tr_noop("Adaptive"), [
        SettingRow("ConditionalNav", "value", tr_noop("Conditional Experimental"),
                   subtitle=tr_noop("Automatically engage Experimental Mode under configurable conditions."),
                   get_value=lambda: tr_noop("Configure"),
                   navigate_to="conditional"),
        SettingRow("CurveNav", "value", tr_noop("Curve Speed"),
                   subtitle=tr_noop("Automatically slow down for upcoming curves based on learned road data."),
                   get_value=lambda: tr_noop("Configure"),
                   navigate_to="curve"),
        SettingRow("WeatherNav", "value", tr_noop("Weather"),
                   subtitle=tr_noop("Adjust following distance, acceleration, and curve speed for weather conditions."),
                   get_value=lambda: tr_noop("Configure"),
                   navigate_to="weather"),
      ], tab_key="adaptive"),

      # ── Limits tab ──
      SettingSection(tr_noop("Speed Limit Controller"), [
        SettingRow("SLC", "toggle", tr_noop("Speed Limit Controller"),
                   subtitle=tr_noop("Limit the car's maximum speed to the current speed limit."),
                   get_state=lambda: self._params.get_bool("SpeedLimitController"),
                   set_state=lambda s: self._params.put_bool("SpeedLimitController", s)),
        SettingRow("SLCOffsetsNav", "value", tr_noop("SLC Offsets"),
                   subtitle=tr_noop("Set per-limit offsets for adjusting the speed limit."),
                   get_value=lambda: tr_noop("Configure"),
                   navigate_to="slc_offsets"),
        SettingRow("SLCQOLNav", "value", tr_noop("SLC Quality of Life"),
                   subtitle=tr_noop("Auto-match, confirmation behavior, and lookahead settings."),
                   get_value=lambda: tr_noop("Configure"),
                   navigate_to="slc_qol"),
        SettingRow("SLCVisualsNav", "value", tr_noop("SLC Visuals"),
                   subtitle=tr_noop("Display options for the speed limit controller."),
                   get_value=lambda: tr_noop("Configure"),
                   navigate_to="slc_visuals"),
      ], tab_key="limits", column_pair="limits"),
      SettingSection(tr_noop("Override & Fallback"), [
        SettingRow("SLCFallback", "value", tr_noop("Fallback Speed"),
                   subtitle="",
                   get_value=lambda: self._params.get("SLCFallback", encoding="utf-8") or "Set Speed",
                   on_click=lambda: self._show_string_select("SLCFallback", ["Set Speed", "Experimental Mode", "Previous Limit"])),
        SettingRow("SLCOverride", "value", tr_noop("Override Speed"),
                   subtitle="",
                   get_value=lambda: self._params.get("SLCOverride", encoding="utf-8") or "None",
                   on_click=lambda: self._show_string_select("SLCOverride", ["None", "Set With Gas Pedal", "Max Set Speed"])),
        SettingRow("SLCPriority", "value", tr_noop("Source Priority"),
                   subtitle="",
                   get_value=self._get_priority_value,
                   on_click=self._on_priority_clicked),
      ], tab_key="limits", column_pair="limits"),

      # ── Daily tab ──
      SettingSection(tr_noop("Cruise & Stops"), [
        SettingRow("QOLToggle", "toggle", tr_noop("Quality of Life"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("QOLLongitudinal"),
                   set_state=lambda s: self._params.put_bool("QOLLongitudinal", s)),
        SettingRow("CustomCruise", "value", tr_noop("Cruise Interval"),
                   subtitle="",
                   get_value=lambda: f"{max(1, self._params.get_int('CustomCruise'))} mph",
                   on_click=lambda: self._show_slider("CustomCruise", 1, 100, unit=" mph",
                                                      current_value=max(1, self._params.get_int("CustomCruise"))),
                   visible=lambda: self._params.get_bool("QOLLongitudinal")),
        SettingRow("CustomCruiseLong", "value", tr_noop("Cruise Long"),
                   subtitle="",
                   get_value=lambda: f"{max(1, self._params.get_int('CustomCruiseLong'))} mph",
                   on_click=lambda: self._show_slider("CustomCruiseLong", 1, 100, unit=" mph",
                                                      current_value=max(1, self._params.get_int("CustomCruiseLong"))),
                   visible=lambda: self._params.get_bool("QOLLongitudinal")),
         SettingRow("ForceStops", "toggle", tr_noop("Force Stops"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("ForceStops"),
                   set_state=lambda s: self._params.put_bool("ForceStops", s),
                   visible=lambda: self._params.get_bool("QOLLongitudinal")),
        SettingRow("ForceStopDist", "value", tr_noop("Force Stop Offset"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int('ForceStopDistanceOffset'):+d} ft",
                   on_click=lambda: self._show_slider("ForceStopDistanceOffset", -20, 20, unit=" ft"),
                   visible=lambda: self._params.get_bool("QOLLongitudinal") and self._params.get_bool("ForceStops")),
        SettingRow("RadarTakeoffs", "toggle", tr_noop("Radar for Takeoffs"),
                   subtitle=tr_noop("Turns on/off using radar data to track leads at standstill, making following/takeoffs more responsive once leads move."),
                   get_state=lambda: self._params.get_bool("RadarTakeoffs"),
                   set_state=lambda s: self._params.put_bool("RadarTakeoffs", s),
                   visible=lambda: self._params.get_bool("QOLLongitudinal") and starpilot_state.car_state.hasRadar),
      ], tab_key="daily", column_pair="daily"),
      SettingSection(tr_noop("Standstill & Gears"), [
        SettingRow("ForceStandstill", "toggle", tr_noop("Force Standstill"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("ForceStandstill"),
                   set_state=lambda s: self._params.put_bool("ForceStandstill", s),
                   visible=lambda: self._params.get_bool("QOLLongitudinal")),
        SettingRow("IncStoppedDist", "value", tr_noop("Stopped Distance"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int('IncreasedStoppedDistance')} ft",
                   on_click=lambda: self._show_slider("IncreasedStoppedDistance", 0, 10, unit=" ft"),
                   visible=lambda: self._params.get_bool("QOLLongitudinal")),
        SettingRow("SetSpeedOffset", "value", tr_noop("Set Speed Offset"),
                   subtitle="",
                   get_value=lambda: f"+{self._params.get_int('SetSpeedOffset')} mph",
                   on_click=lambda: self._show_slider("SetSpeedOffset", 0, 99, unit=" mph"),
                   visible=lambda: self._params.get_bool("QOLLongitudinal")),
        SettingRow("MapGears", "toggle", tr_noop("Map Gears"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("MapGears"),
                   set_state=lambda s: self._params.put_bool("MapGears", s),
                   visible=lambda: self._params.get_bool("QOLLongitudinal")),
        SettingRow("MapAccel", "toggle", tr_noop("Map Acceleration"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("MapAcceleration"),
                   set_state=lambda s: self._params.put_bool("MapAcceleration", s),
                   visible=lambda: self._params.get_bool("QOLLongitudinal") and self._params.get_bool("MapGears")),
        SettingRow("MapDecel", "toggle", tr_noop("Map Deceleration"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("MapDeceleration"),
                   set_state=lambda s: self._params.put_bool("MapDeceleration", s),
                   visible=lambda: self._params.get_bool("QOLLongitudinal") and self._params.get_bool("MapGears")),
       ], tab_key="daily", column_pair="daily"),
    ]

    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr_noop("Gas/Brake"),
      header_subtitle=tr_noop("Fine-tune acceleration, braking, and driving behavior."),
      tab_defs=tab_defs,
    )

  def _get_priority_value(self):
    primary = self._params.get("SLCPriority1", encoding="utf-8") or "Map Data"
    secondary = self._params.get("SLCPriority2", encoding="utf-8") or "None"
    if primary in ("Highest", "Lowest") or secondary in ("", "None", primary):
      return primary
    return f"{primary}, {secondary}"

  def _on_priority_clicked(self):
    primary_options = ["Dashboard", "Map Data", "Vision", "Highest", "Lowest"]
    current_primary = self._params.get("SLCPriority1", encoding="utf-8") or "Map Data"
    current_secondary = self._params.get("SLCPriority2", encoding="utf-8") or "None"

    def on_secondary_select(primary, dialog, res):
      if res == DialogResult.CONFIRM and dialog.selection:
        self._params.put("SLCPriority1", primary)
        self._params.put("SLCPriority2", dialog.selection)

    def show_secondary_dialog(primary):
      secondary_options = ["None"] + [option for option in ("Dashboard", "Map Data", "Vision") if option != primary]
      selected_secondary = current_secondary if current_secondary in secondary_options else "None"
      secondary_dialog = MultiOptionDialog(tr("SLC Secondary Priority"), secondary_options, selected_secondary,
                                           callback=lambda res: on_secondary_select(primary, secondary_dialog, res))
      gui_app.push_widget(secondary_dialog)

    def on_primary_select(res):
      if res != DialogResult.CONFIRM or not primary_dialog.selection:
        return
      if primary_dialog.selection in ("Highest", "Lowest"):
        self._params.put("SLCPriority1", primary_dialog.selection)
        self._params.put("SLCPriority2", "None")
        return
      show_secondary_dialog(primary_dialog.selection)

    primary_dialog = MultiOptionDialog(tr("SLC Primary Priority"), primary_options, current_primary, callback=on_primary_select)
    gui_app.push_widget(primary_dialog)


# ═══════════════════════════════════════════════════════════════
# StarPilotLongitudinalTuneLayout
# ═══════════════════════════════════════════════════════════════

class StarPilotLongitudinalTuneLayout(_SettingsPage):
  def __init__(self):
    super().__init__()
    self._build_view()

  def _longitudinal_enabled(self):
    return self._params.get_bool("LongitudinalTune")

  def _build_view(self):
    sections: list[SettingSection] = [
      SettingSection(tr_noop("Profiles"), [
        SettingRow("AccelProfile", "value", tr_noop("Acceleration Profile"),
                   subtitle=tr_noop("Choose how quickly openpilot speeds up."),
                   get_value=self._get_acceleration_profile_label,
                   on_click=self._show_acceleration_profile_selector,
                   visible=self._longitudinal_enabled),
        SettingRow("DecelProfile", "value", tr_noop("Deceleration Profile"),
                   subtitle=tr_noop("Choose how firmly openpilot slows the car down."),
                   get_value=self._get_deceleration_profile_label,
                   on_click=self._show_deceleration_profile_selector,
                   visible=self._longitudinal_enabled),
      ]),
      SettingSection(tr_noop("Human-Like Driving"), [
        SettingRow("CoastUpToLeads", "toggle", tr_noop("Coast Up To Leads"),
                   subtitle=tr_noop("Keep optional far-lead comfort logic on. Recommended unless your car shows lead-follow stutter or springy gas/brake behavior."),
                   get_state=lambda: self._params.get_bool("CoastUpToLeads"),
                   set_state=lambda s: self._params.put_bool("CoastUpToLeads", s),
                   visible=self._longitudinal_enabled),
      ], column_pair="human_driving"),
      SettingSection(tr_noop("Lane Changes"), [
        SettingRow("HumanLaneChanges", "toggle", tr_noop("Human-Like Lane Changes"),
                   subtitle=tr_noop("Radar-informed behavior during lane changes."),
                   get_state=lambda: self._params.get_bool("HumanLaneChanges"),
                   set_state=lambda s: self._params.put_bool("HumanLaneChanges", s),
                   visible=lambda: self._longitudinal_enabled() and starpilot_state.car_state.hasRadar),
      ], column_pair="human_driving"),
      SettingSection(tr_noop("Detection"), [
        SettingRow("LeadDetection", "value", tr_noop("Lead Detection Sensitivity"),
                   subtitle=tr_noop("Control how aggressively openpilot detects and reacts to vehicles ahead."),
                   get_value=lambda: f"{self._params.get_int('LeadDetectionThreshold')}%",
                   on_click=lambda: self._show_slider("LeadDetectionThreshold", 25, 50, unit="%"),
                   visible=self._longitudinal_enabled),
      ], column_pair="detection_tune"),
      SettingSection(tr_noop("Tuning"), [
        SettingRow("NavLongitudinalAllowed", "toggle", tr_noop("Use Route Speed Control"),
                   subtitle=tr_noop("Allow an active navigation route to reduce cruise speed for upcoming turns, ramps, and roundabouts."),
                   get_state=lambda: self._params.get_bool("NavLongitudinalAllowed"),
                   set_state=lambda s: self._params.put_bool("NavLongitudinalAllowed", s),
                   visible=self._longitudinal_enabled),
      ], column_pair="detection_tune"),
    ]
    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr_noop("Longitudinal Tuning"),
      header_subtitle=tr_noop("Acceleration profiles, human-like behavior, and detection sensitivity."),
    )

  def _get_acceleration_profile_label(self):
    value = normalize_acceleration_profile(self._params.get("AccelerationProfile", encoding="utf-8"))
    return self._profile_label_for_value(value, ACCELERATION_PROFILE_OPTIONS)

  def _get_deceleration_profile_label(self):
    value = normalize_deceleration_profile(self._params.get("DecelerationProfile", encoding="utf-8"))
    return self._profile_label_for_value(value, DECELERATION_PROFILE_OPTIONS)

  def _show_acceleration_profile_selector(self):
    self._show_labeled_select("Acceleration Profile", "AccelerationProfile", ACCELERATION_PROFILE_OPTIONS,
                              normalize_acceleration_profile(self._params.get("AccelerationProfile", encoding="utf-8")))

  def _show_deceleration_profile_selector(self):
    self._show_labeled_select("Deceleration Profile", "DecelerationProfile", DECELERATION_PROFILE_OPTIONS,
                              normalize_deceleration_profile(self._params.get("DecelerationProfile", encoding="utf-8")))

  def _profile_label_for_value(self, value, options):
    for option_value, option_label in options:
      if option_value == value:
        return tr(option_label)
    return tr(options[0][1])


# ═══════════════════════════════════════════════════════════════
# StarPilotAdvancedLongitudinalLayout
# ═══════════════════════════════════════════════════════════════

class StarPilotAdvancedLongitudinalLayout(_SettingsPage):
  def __init__(self):
    super().__init__()
    self._build_view()

  def _advanced_enabled(self):
    return self._params.get_bool("AdvancedLongitudinalTune")

  def _using_human_acceleration(self):
    return self._params.get_bool("LongitudinalTune") and self._params.get_bool("HumanAcceleration")

  def _show_stop_tuning_values(self):
    return self._advanced_enabled() and not (starpilot_state.car_state.isToyota and self._params.get_bool("FrogsGoMoosTweak"))

  def _build_view(self):
    adv = self._advanced_enabled
    sections: list[SettingSection] = [
      SettingSection(tr_noop("Drivetrain"), [
        SettingRow("EVTuning", "toggle", tr_noop("EV Tuning"),
                   subtitle=tr_noop("Acceleration tuning for EV and direct-drive vehicles."),
                   get_state=lambda: self._params.get_bool("EVTuning"),
                   set_state=self._set_ev_tuning,
                   visible=adv,
                   enabled=lambda: not self._params.get_bool("TruckTuning"),
                   disabled_label=tr_noop("Truck Active")),
        SettingRow("TruckTuning", "toggle", tr_noop("Truck Tuning"),
                   subtitle=tr_noop("Stronger launch and acceleration for heavier vehicles."),
                   get_state=lambda: self._params.get_bool("TruckTuning"),
                   set_state=self._set_truck_tuning,
                   visible=adv,
                   enabled=lambda: not self._params.get_bool("EVTuning"),
                   disabled_label=tr_noop("EV Active")),
        SettingRow("ActuatorDelay", "value", tr_noop("Actuator Delay"),
                   subtitle=tr_noop("Time between command and the vehicle's response."),
                   get_value=lambda: f"{self._params.get_float('LongitudinalActuatorDelay'):.2f}s",
                   on_click=lambda: self._show_slider("LongitudinalActuatorDelay", 0.0, 1.0, step=0.01, unit="s", value_type="float"),
                   visible=adv),
        SettingRow("MaxAccel", "value", tr_noop("Maximum Acceleration"),
                   subtitle=tr_noop("Strongest acceleration openpilot is allowed to command."),
                   get_value=lambda: f"{self._params.get_float('MaxDesiredAcceleration'):.1f}m/s",
                   on_click=lambda: self._show_slider("MaxDesiredAcceleration", 0.1, 4.0, step=0.1, unit="m/s", value_type="float"),
                   visible=adv),
        SettingRow("StartAccel", "value", tr_noop("Start Acceleration"),
                   subtitle=tr_noop("Extra acceleration when moving away from a stop."),
                   get_value=lambda: f"{self._params.get_float('StartAccel'):.2f}m/s",
                   on_click=lambda: self._show_slider("StartAccel", 0.0, 4.0, step=0.01, unit="m/s", value_type="float"),
                   visible=lambda: adv() and not self._using_human_acceleration()),
      ]),
      SettingSection(tr_noop("Braking"), [
        SettingRow("StopAccel", "value", tr_noop("Stop Acceleration"),
                   subtitle=tr_noop("Brake force to hold the vehicle at a complete stop."),
                   get_value=lambda: f"{self._params.get_float('StopAccel'):.2f}m/s",
                   on_click=lambda: self._show_slider("StopAccel", -4.0, 0.0, step=0.01, unit="m/s", value_type="float"),
                   visible=adv),
        SettingRow("StoppingRate", "value", tr_noop("Stopping Rate"),
                   subtitle=tr_noop("How quickly braking ramps up to bring the car to a stop."),
                   get_value=lambda: f"{self._params.get_float('StoppingDecelRate'):.3f}m/s",
                   on_click=lambda: self._show_slider("StoppingDecelRate", 0.001, 1.0, step=0.001, unit="m/s", value_type="float"),
                   visible=self._show_stop_tuning_values),
      ], column_pair="adv_brake_speed"),
      SettingSection(tr_noop("Speed"), [
        SettingRow("StartSpeed", "value", tr_noop("Start Speed"),
                   subtitle=tr_noop("Speed where openpilot exits the stopped state."),
                   get_value=lambda: f"{self._params.get_float('VEgoStarting'):.2f}m/s",
                   on_click=lambda: self._show_slider("VEgoStarting", 0.01, 1.0, step=0.01, unit="m/s", value_type="float"),
                   visible=self._show_stop_tuning_values),
        SettingRow("StopSpeed", "value", tr_noop("Stop Speed"),
                   subtitle=tr_noop("Speed where openpilot considers the vehicle fully stopped."),
                   get_value=lambda: f"{self._params.get_float('VEgoStopping'):.2f}m/s",
                   on_click=lambda: self._show_slider("VEgoStopping", 0.01, 1.0, step=0.01, unit="m/s", value_type="float"),
                   visible=self._show_stop_tuning_values),
      ], column_pair="adv_brake_speed"),
    ]
    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr_noop("Advanced Longitudinal Tuning"),
      header_subtitle=tr_noop("Actuator delay, launch, stop behavior, and powertrain options."),
    )

  def _set_ev_tuning(self, state: bool):
    self._params.put_bool("EVTuning", state)
    if state:
      self._params.put_bool("TruckTuning", False)

  def _set_truck_tuning(self, state: bool):
    self._params.put_bool("TruckTuning", state)
    if state:
      self._params.put_bool("EVTuning", False)


# ═══════════════════════════════════════════════════════════════
# StarPilotConditionalExperimentalLayout
# ═══════════════════════════════════════════════════════════════

class StarPilotConditionalExperimentalLayout(_SettingsPage):
  def __init__(self):
    super().__init__()
    self._build_view()

  def _build_view(self):
    ce_on = lambda: self._params.get_bool("ConditionalExperimental")
    ce_lead = lambda: ce_on() and self._params.get_bool("CELead")
    sections: list[SettingSection] = [
      SettingSection(tr_noop("Triggers"), [
        SettingRow("ConditionalExperimental", "toggle", tr_noop("Conditional Experimental Mode"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("ConditionalExperimental"),
                   set_state=lambda s: self._params.put_bool("ConditionalExperimental", s)),
        SettingRow("PersistExp", "toggle", tr_noop("Persist Experimental State"),
                   subtitle=tr_noop("Keep override through reboots until manually cleared."),
                   get_state=lambda: self._params.get_bool("PersistExperimentalState"),
                   set_state=self._set_persist_experimental_state,
                   visible=ce_on),
        SettingRow("CESpeed", "value", tr_noop("Below Speed"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int('CESpeed')} mph",
                   on_click=lambda: self._show_slider("CESpeed", 0, 100, unit=" mph"),
                   visible=ce_on),
        SettingRow("CECurves", "toggle", tr_noop("Curves"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("CECurves"),
                   set_state=lambda s: self._params.put_bool("CECurves", s),
                   visible=ce_on),
        SettingRow("CECurvesLead", "toggle", tr_noop("Curves Lead"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("CECurvesLead"),
                   set_state=lambda s: self._params.put_bool("CECurvesLead", s),
                   visible=lambda: self._params.get_bool("CECurves")),
        SettingRow("CEStopLights", "toggle", tr_noop("Stop Lights"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("CEStopLights"),
                   set_state=lambda s: self._params.put_bool("CEStopLights", s),
                   visible=ce_on),
        SettingRow("CELead", "toggle", tr_noop("Lead Detected"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("CELead"),
                   set_state=lambda s: self._params.put_bool("CELead", s),
                   visible=ce_on),
      ], column_pair="ce"),
      SettingSection(tr_noop("Conditions"), [
        SettingRow("CESlowerLead", "toggle", tr_noop("Slower Lead"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("CESlowerLead"),
                   set_state=lambda s: self._params.put_bool("CESlowerLead", s),
                   visible=ce_lead),
        SettingRow("CEStoppedLead", "toggle", tr_noop("Stopped Lead"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("CEStoppedLead"),
                   set_state=lambda s: self._params.put_bool("CEStoppedLead", s),
                   visible=ce_lead),
        SettingRow("CEModelStopTime", "value", tr_noop("Predicted Stop"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int('CEModelStopTime')}s",
                   on_click=lambda: self._show_slider("CEModelStopTime", 0, 10, unit="s"),
                   visible=ce_on),
        SettingRow("CESignalSpeed", "value", tr_noop("Signal Below"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int('CESignalSpeed')} mph",
                   on_click=lambda: self._show_slider("CESignalSpeed", 0, 100, unit=" mph"),
                   visible=ce_on),
        SettingRow("CESpeedLead", "value", tr_noop("Speed Lead"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int('CESpeedLead')} mph",
                   on_click=lambda: self._show_slider("CESpeedLead", 0, 100, unit=" mph"),
                   visible=ce_on),
        SettingRow("CESignalLaneDetection", "toggle", tr_noop("Signal Lane Detection"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("CESignalLaneDetection"),
                   set_state=lambda s: self._params.put_bool("CESignalLaneDetection", s),
                   visible=lambda: self._params.get_int("CESignalSpeed") > 0),
        SettingRow("ShowCEMStatus", "toggle", tr_noop("Status Widget"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("ShowCEMStatus"),
                   set_state=lambda s: self._params.put_bool("ShowCEMStatus", s),
                   visible=ce_on),
      ], column_pair="ce"),
    ]
    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr_noop("Conditional Experimental"),
      header_subtitle=tr_noop("Automatically engage Experimental Mode under configurable conditions."),
    )

  def _set_persist_experimental_state(self, state: bool):
    sync_persist_experimental_state(self._params, self._params_memory, state)


# ═══════════════════════════════════════════════════════════════
# StarPilotCurveSpeedLayout
# ═══════════════════════════════════════════════════════════════

class StarPilotCurveSpeedLayout(_SettingsPage):
  def __init__(self):
    super().__init__()
    self._build_view()

  def _build_view(self):
    csc_on = lambda: self._params.get_bool("CurveSpeedController")
    sections: list[SettingSection] = [
      SettingSection(tr_noop("Curve Speed Controller"), [
        SettingRow("CurveSpeed", "toggle", tr_noop("Curve Speed Controller"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("CurveSpeedController"),
                   set_state=lambda s: self._params.put_bool("CurveSpeedController", s)),
        SettingRow("ShowCSCStatus", "toggle", tr_noop("Status Widget"),
                   subtitle=tr_noop("Show the Curve Speed Controller ambient effect on the driving screen."),
                   get_state=lambda: self._params.get_bool("ShowCSCStatus"),
                   set_state=lambda s: self._params.put_bool("ShowCSCStatus", s),
                   visible=csc_on),
        SettingRow("CalibratedLatAccel", "value", tr_noop("Calibrated Lateral Accel"),
                   subtitle=tr_noop("The learned lateral acceleration from collected driving data. Higher values allow faster cornering."),
                   get_value=lambda: f"{self._params_memory.get_float('CalibratedLateralAcceleration'):.2f} m/s",
                   on_click=None,
                   visible=csc_on),
        SettingRow("CalibrationProgress", "value", tr_noop("Calibration Progress"),
                   subtitle=tr_noop("How much curve data has been collected. Normal for the value to stay low."),
                   get_value=lambda: f"{self._params_memory.get_float('CalibrationProgress'):.2f}%",
                   on_click=None,
                   visible=csc_on),
        SettingRow("ResetCurve", "action", tr_noop("Reset Curve Data"),
                   subtitle=tr_noop("Reset collected user data for Curve Speed Controller."),
                   action_text=tr_noop("Reset"),
                   action_danger=True,
                   on_click=lambda: self._reset_curve_data(),
                   visible=csc_on),
      ]),
    ]
    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr_noop("Curve Speed"),
      header_subtitle=tr_noop("Slow down for upcoming curves based on learned data."),
    )

  def _reset_curve_data(self):
    def on_close(res):
      if res == DialogResult.CONFIRM:
        self._params.put_float("CalibratedLateralAcceleration", 2.00)
        self._params.remove("CalibrationProgress")
        self._params.remove("CurvatureData")

    gui_app.push_widget(ConfirmDialog(tr_noop("Reset Curve Data?"), tr_noop("Confirm"), callback=on_close))


# ═══════════════════════════════════════════════════════════════
# StarPilotPersonalitiesLayout
# ═══════════════════════════════════════════════════════════════

class StarPilotPersonalitiesLayout(_SettingsPage):
  def __init__(self):
    super().__init__()
    self._sub_panels = {
      "traffic_personality": StarPilotPersonalityProfileLayout("Traffic"),
      "aggressive_personality": StarPilotPersonalityProfileLayout("Aggressive"),
      "standard_personality": StarPilotPersonalityProfileLayout("Standard"),
      "relaxed_personality": StarPilotPersonalityProfileLayout("Relaxed"),
    }

    self._wire_sub_panels()
    self._build_view()

  def _build_view(self):
    sections: list[SettingSection] = [
      SettingSection(tr_noop("Driving Personalities"), [
        SettingRow("PersonalitiesToggle", "toggle", tr_noop("Driving Personalities"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("CustomPersonalities"),
                   set_state=lambda s: self._params.put_bool("CustomPersonalities", s)),
        SettingRow("Traffic", "value", tr_noop("Traffic"),
                   subtitle=tr_noop("Configure follow distance, smoothness, and response for traffic conditions."),
                   get_value=lambda: tr_noop("Configure"),
                   navigate_to="traffic_personality"),
        SettingRow("Aggressive", "value", tr_noop("Aggressive"),
                   subtitle=tr_noop("Configure follow distance, smoothness, and response for aggressive driving."),
                   get_value=lambda: tr_noop("Configure"),
                   navigate_to="aggressive_personality"),
        SettingRow("Standard", "value", tr_noop("Standard"),
                   subtitle=tr_noop("Configure follow distance, smoothness, and response for everyday driving."),
                   get_value=lambda: tr_noop("Configure"),
                   navigate_to="standard_personality"),
        SettingRow("Relaxed", "value", tr_noop("Relaxed"),
                   subtitle=tr_noop("Configure follow distance, smoothness, and response for relaxed driving."),
                   get_value=lambda: tr_noop("Configure"),
                   navigate_to="relaxed_personality"),
      ]),
    ]
    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr_noop("Driving Personalities"),
      header_subtitle=tr_noop("Customize each profile to match your driving style."),
    )


# ═══════════════════════════════════════════════════════════════
# StarPilotPersonalityProfileLayout
# ═══════════════════════════════════════════════════════════════

class StarPilotPersonalityProfileLayout(_SettingsPage):
  def __init__(self, profile: str):
    super().__init__()
    self._profile = profile
    follow_min = 1.0 if profile == "Traffic" else 0.5
    follow_max = 2.5 if profile == "Traffic" else 3.0
    self._follow_min = follow_min
    self._follow_max = follow_max
    self._build_view()

  def _build_view(self):
    p = self._profile
    sections: list[SettingSection] = [
      SettingSection(tr_noop(f"{p} — Distance"), [
        SettingRow(f"{p}Follow", "value", tr_noop("Follow Distance"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_float(p + 'Follow'):.2f}s",
                   on_click=lambda: self._show_slider(p + "Follow", self._follow_min, self._follow_max, step=0.05, unit="s", value_type="float")),
        SettingRow(f"{p}FollowHigh", "value", tr_noop("Follow High"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_float(p + 'FollowHigh'):.2f}s",
                   on_click=lambda: self._show_slider(p + "FollowHigh", 1.0, 3.0, step=0.05, unit="s", value_type="float"),
                   visible=lambda: self._profile != "Traffic"),
        SettingRow(f"{p}JerkAccel", "value", tr_noop("Accel Smoothness"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int(p + 'JerkAcceleration')}%",
                   on_click=lambda: self._show_slider(p + "JerkAcceleration", 25, 200, step=5, unit="%")),
        SettingRow(f"{p}JerkDecel", "value", tr_noop("Brake Smoothness"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int(p + 'JerkDeceleration')}%",
                   on_click=lambda: self._show_slider(p + "JerkDeceleration", 25, 200, step=5, unit="%")),
      ], column_pair=p),
      SettingSection(tr_noop(f"{p} — Behavior"), [
        SettingRow(f"{p}JerkDanger", "value", tr_noop("Safety Gap Bias"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int(p + 'JerkDanger')}%",
                   on_click=lambda: self._show_slider(p + "JerkDanger", 25, 200, step=5, unit="%")),
        SettingRow(f"{p}JerkSpeedDec", "value", tr_noop("Slowdown Response"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int(p + 'JerkSpeedDecrease')}%",
                   on_click=lambda: self._show_slider(p + "JerkSpeedDecrease", 25, 200, step=5, unit="%")),
        SettingRow(f"{p}JerkSpeed", "value", tr_noop("Speed-Up Response"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int(p + 'JerkSpeed')}%",
                   on_click=lambda: self._show_slider(p + "JerkSpeed", 25, 200, step=5, unit="%")),
        SettingRow(f"{p}Reset", "action", tr_noop("Reset to Defaults"),
                   subtitle="",
                   action_text=tr_noop("Reset"),
                   action_danger=True,
                   on_click=lambda: self._reset_profile()),
      ], column_pair=p),
    ]
    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr_noop(f"{p} Profile"),
      header_subtitle=tr_noop("Customize follow distance and smoothness for this driving personality."),
    )

  def _reset_profile(self):
    def on_close(res):
      if res == DialogResult.CONFIRM:
        for key in ["Follow", "FollowHigh", "JerkAcceleration", "JerkDeceleration", "JerkDanger", "JerkSpeedDecrease", "JerkSpeed"]:
          self._params.remove(self._profile + key)

    gui_app.push_widget(ConfirmDialog(tr_noop("Reset to Defaults?"), tr_noop("Confirm"), callback=on_close))


# ═══════════════════════════════════════════════════════════════
# StarPilotSLCOffsetsLayout
# ═══════════════════════════════════════════════════════════════

class StarPilotSLCOffsetsLayout(_SettingsPage):
  def __init__(self):
    super().__init__()
    self._build_view()

  def _is_metric(self):
    return self._params.get_bool("IsMetric")

  def _speed_unit(self):
    return " km/h" if self._is_metric() else " mph"

  def _speed_range(self):
    return (-150, 150) if self._is_metric() else (-99, 99)

  def _build_view(self):
    rows: list[SettingRow] = []
    for i in range(1, 8):
      key = f"Offset{i}"
      rows.append(SettingRow(
        f"Offset{i}", "value", tr_noop(f"Offset {i}"),
        subtitle="",
        get_value=lambda k=key: f"{self._params.get_int(k)}{self._speed_unit()}",
        on_click=lambda k=key: self._show_slider(k, *self._speed_range(), unit=self._speed_unit()),
      ))

    sections: list[SettingSection] = [
      SettingSection(tr_noop("SLC Offsets"), rows),
    ]
    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr_noop("SLC Offsets"),
      header_subtitle=tr_noop("Per-limit speed adjustments for the Speed Limit Controller."),
    )


# ═══════════════════════════════════════════════════════════════
# StarPilotSLCQOLLayout
# ═══════════════════════════════════════════════════════════════

class StarPilotSLCQOLLayout(_SettingsPage):
  def __init__(self):
    super().__init__()
    self._build_view()

  def _build_view(self):
    confirmation_on = lambda: self._params.get_bool("SLCConfirmation")
    sections: list[SettingSection] = [
      SettingSection(tr_noop("SLC Quality of Life"), [
        SettingRow("SetSpeedLimit", "toggle", tr_noop("Auto Match Speed Limits"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("SetSpeedLimit"),
                   set_state=lambda s: self._params.put_bool("SetSpeedLimit", s)),
        SettingRow("SLCConfirmation", "toggle", tr_noop("Confirm New Limits"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("SLCConfirmation"),
                   set_state=lambda s: self._params.put_bool("SLCConfirmation", s)),
        SettingRow("SLCConfirmationLower", "toggle", tr_noop("Confirm Lower"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("SLCConfirmationLower"),
                   set_state=lambda s: self._params.put_bool("SLCConfirmationLower", s),
                   visible=confirmation_on),
        SettingRow("SLCConfirmationHigher", "toggle", tr_noop("Confirm Higher"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("SLCConfirmationHigher"),
                   set_state=lambda s: self._params.put_bool("SLCConfirmationHigher", s),
                   visible=confirmation_on),
        SettingRow("SLCLookHigher", "value", tr_noop("Higher Lookahead"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int('SLCLookaheadHigher')}s",
                   on_click=lambda: self._show_slider("SLCLookaheadHigher", 0, 30, unit="s")),
        SettingRow("SLCLookLower", "value", tr_noop("Lower Lookahead"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int('SLCLookaheadLower')}s",
                   on_click=lambda: self._show_slider("SLCLookaheadLower", 0, 30, unit="s")),
        SettingRow("SLCMapbox", "toggle", tr_noop("Mapbox Fallback"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("SLCMapboxFiller"),
                     set_state=lambda s: self._params.put_bool("SLCMapboxFiller", s)),
        SettingRow("VisionSpeedLimit", "toggle", tr_noop("Vision Detection"),
                   subtitle=tr_noop("Use the road camera to detect speed limit signs for SLC."),
                   get_state=lambda: self._params.get_bool("VisionSpeedLimitDetection"),
                   set_state=lambda s: self._params.put_bool("VisionSpeedLimitDetection", s)),
      ]),
    ]
    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr_noop("SLC Quality of Life"),
      header_subtitle=tr_noop("Auto-match, confirmations, and lookahead settings."),
    )


# ═══════════════════════════════════════════════════════════════
# StarPilotSLCVisualsLayout
# ═══════════════════════════════════════════════════════════════

class StarPilotSLCVisualsLayout(_SettingsPage):
  def __init__(self):
    super().__init__()
    self._build_view()

  def _build_view(self):
    sections: list[SettingSection] = [
      SettingSection(tr_noop("SLC Visuals"), [
        SettingRow("ShowSLCOffset", "toggle", tr_noop("Show SLC Offset"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("ShowSLCOffset"),
                   set_state=lambda s: self._params.put_bool("ShowSLCOffset", s)),
        SettingRow("ShowSources", "toggle", tr_noop("Show Sources"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("SpeedLimitSources"),
                   set_state=lambda s: self._params.put_bool("SpeedLimitSources", s)),
      ]),
    ]
    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr_noop("SLC Visuals"),
      header_subtitle=tr_noop("Display options for the Speed Limit Controller."),
    )


# ═══════════════════════════════════════════════════════════════
# StarPilotWeatherLayout
# ═══════════════════════════════════════════════════════════════

class StarPilotWeatherLayout(_SettingsPage):
  def __init__(self):
    super().__init__()
    self._keyboard = Keyboard(min_text_size=1)
    self._sub_panels = {
      "low_visibility": StarPilotWeatherBase("LowVisibility"),
      "rain": StarPilotWeatherBase("Rain"),
      "rainstorm": StarPilotWeatherBase("RainStorm"),
      "snow": StarPilotWeatherBase("Snow"),
    }

    self._wire_sub_panels()
    self._build_view()

  def _build_view(self):
    sections: list[SettingSection] = [
      SettingSection(tr_noop("Weather Conditions"), [
        SettingRow("LowVisibility", "value", tr_noop("Low Visibility"),
                   subtitle=tr_noop("Adjust parameters for fog, mist, and poor visibility conditions."),
                   get_value=lambda: tr_noop("Configure"),
                   navigate_to="low_visibility"),
        SettingRow("Rain", "value", tr_noop("Rain"),
                   subtitle=tr_noop("Adjust parameters for light to moderate rain."),
                   get_value=lambda: tr_noop("Configure"),
                   navigate_to="rain"),
        SettingRow("RainStorm", "value", tr_noop("Rainstorms"),
                   subtitle=tr_noop("Adjust parameters for heavy rain and storms."),
                   get_value=lambda: tr_noop("Configure"),
                   navigate_to="rainstorm"),
        SettingRow("Snow", "value", tr_noop("Snow"),
                   subtitle=tr_noop("Adjust parameters for snowy and icy conditions."),
                   get_value=lambda: tr_noop("Configure"),
                   navigate_to="snow"),
      ]),
      SettingSection(tr_noop("API"), [
        SettingRow("WeatherKey", "action", tr_noop("Set Weather Key"),
                   subtitle=tr_noop("Enter or remove your weather data API key."),
                   action_text=tr_noop("Set Key"),
                   on_click=lambda: self._set_weather_key()),
      ]),
    ]
    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr_noop("Weather"),
      header_subtitle=tr_noop("Adjust driving parameters based on weather conditions."),
    )

  def _set_weather_key(self):
    options = ["ADD", "REMOVE"]

    def on_select(res):
      if res == DialogResult.CONFIRM and dialog.selection:
        if dialog.selection == "ADD":

          def on_key(res, text):
            if res == DialogResult.CONFIRM:
              self._params.put("WeatherAPIKey", text)

          self._keyboard.reset(min_text_size=1)
          self._keyboard.set_title(tr_noop("Weather API Key"), "")
          self._keyboard.set_text("")
          self._keyboard.set_callback(lambda result: on_key(result, self._keyboard.text))
          gui_app.push_widget(self._keyboard)
        elif dialog.selection == "REMOVE":

          def on_confirm(res):
            if res == DialogResult.CONFIRM:
              self._params.remove("WeatherAPIKey")

          gui_app.push_widget(ConfirmDialog(tr_noop("Remove API Key?"), tr_noop("Confirm"), callback=on_confirm))

    dialog = MultiOptionDialog(tr_noop("Weather API Key"), options, "ADD", callback=on_select)
    gui_app.push_widget(dialog)


# ═══════════════════════════════════════════════════════════════
# StarPilotWeatherBase
# ═══════════════════════════════════════════════════════════════

class StarPilotWeatherBase(_SettingsPage):
  def __init__(self, suffix: str):
    super().__init__()
    self._suffix = suffix
    self._build_view()

  def _build_view(self):
    s = self._suffix
    title_map = {
      "LowVisibility": tr_noop("Low Visibility"),
      "Rain": tr_noop("Rain"),
      "RainStorm": tr_noop("Rainstorms"),
      "Snow": tr_noop("Snow"),
    }
    sections: list[SettingSection] = [
      SettingSection(tr_noop("Adjustments"), [
        SettingRow(f"Follow{s}", "value", tr_noop("Following Distance"),
                   subtitle="",
                   get_value=lambda: f"+{self._params.get_int('IncreaseFollowing' + s)}s",
                   on_click=lambda: self._show_slider("IncreaseFollowing" + s, 0, 3, step=0.5, unit="s")),
        SettingRow(f"StoppedDist{s}", "value", tr_noop("Stopped Distance"),
                   subtitle="",
                   get_value=lambda: f"+{self._params.get_int('IncreasedStoppedDistance' + s)} ft",
                   on_click=lambda: self._show_slider("IncreasedStoppedDistance" + s, 0, 10, unit=" ft")),
        SettingRow(f"ReduceAccel{s}", "value", tr_noop("Reduce Accel"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int('ReduceAcceleration' + s)}%",
                   on_click=lambda: self._show_slider("ReduceAcceleration" + s, 0, 99, unit="%")),
        SettingRow(f"ReduceLateral{s}", "value", tr_noop("Reduce Curve Speed"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int('ReduceLateralAcceleration' + s)}%",
                   on_click=lambda: self._show_slider("ReduceLateralAcceleration" + s, 0, 99, unit="%")),
      ]),
    ]
    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr(title_map.get(s, s)),
      header_subtitle=tr_noop("Adjust driving parameters for this weather condition."),
    )
