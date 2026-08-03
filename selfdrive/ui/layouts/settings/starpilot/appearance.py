from __future__ import annotations
import re

from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog

from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import _SettingsPage
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
    AetherSliderDialog,
    DEFAULT_PANEL_STYLE,
    ParentToggle,
    SettingRow,
    SettingSection,
    AetherSettingsView,
    CardHubManagerView,
)
from openpilot.selfdrive.ui.layouts.settings.starpilot.simple_download_manager import SimpleDownloadManager
from openpilot.starpilot.common.starpilot_variables import THEME_SAVE_PATH

PANEL_STYLE = DEFAULT_PANEL_STYLE

THEME_KEY_CONFIG = {
    "BootLogo": {
        "default": "starpilot",
        "extra": [],
    },
}

COLOR_PRESETS = ["Stock", "#FFFFFF", "#178644", "#3B82F6", "#E63956", "#8B5CF6", "#F59E0B"]
CAMERA_VIEWS = ["Auto", "Driver", "Standard", "Wide"]

# Mirrors starpilot/ui/qt/offroad/developer_panel.cc:200-218.
# Keys are the int values stored in DeveloperSidebarMetric{1..7}; values are the
# human-readable labels shown in both the row value and the picker dialog.
DEVELOPER_SIDEBAR_METRIC_OPTIONS: dict[int, str] = {
  0:  "None",
  1:  "Acceleration: Current",
  2:  "Acceleration: Max",
  3:  "Auto Tune: Actuator Delay",
  4:  "Auto Tune: Friction",
  5:  "Auto Tune: Lateral Acceleration",
  6:  "Auto Tune: Steer Ratio",
  7:  "Auto Tune: Stiffness Factor",
  8:  "Engagement %: Lateral",
  9:  "Engagement %: Longitudinal",
  10: "Lateral Control: Steering Angle",
  11: "Lateral Control: Torque % Used",
  12: "Longitudinal Control: Actuator Acceleration Output",
  13: "Longitudinal MPC: Danger Factor",
  14: "Longitudinal MPC Jerk: Acceleration",
  15: "Longitudinal MPC Jerk: Danger Zone",
  16: "Longitudinal MPC Jerk: Speed Control",
  17: "Model Name",
}

def _theme_display_name(value: str) -> str:
    if not value:
        return "Stock"
    if value.lower() == "stock":
        return "Stock"
    if value.lower() == "none":
        return "None"
    base, creator = (value.split("~", 1) + [""])[:2] if "~" in value else (value, "")
    user_created_suffixes = ("-user_created", "_user_created", "-user-created", "_user-created")
    user_created = False
    for suffix in user_created_suffixes:
        if base.endswith(suffix):
            base = base[:-len(suffix)]
            user_created = True
            break
    parts = [part for part in re.split(r"[-_]+", base) if part]
    display = " ".join(part[:1].upper() + part[1:] for part in parts) if parts else value
    if user_created:
        display += " (User Created)"
    if creator:
        display += f" - by: {creator}"
    return display

# ═══════════════════════════════════════════════════════════════
# AppearanceManagerView — 6-card category hub
# ═══════════════════════════════════════════════════════════════

class AppearanceManagerView(CardHubManagerView):
    def __init__(self, controller, sections, **kwargs):
        super().__init__(controller, sections, **kwargs)

    def _build_cards(self):
        return [
            {
                "title": tr("Model & Path Visualization"),
                "desc": tr("Customize dynamic lane paths, road edges, and colors."),
                "icon": "steering",
                "on_click": lambda: self._controller._navigate_to("model"),
            },
            {
                "title": tr("Driving Widgets & HUD"),
                "desc": tr("Configure compass, dynamic pedals, signals, and screen borders."),
                "icon": "display",
                "on_click": lambda: self._controller._navigate_to("hud"),
            },
            {
                "title": tr("Screen Declutter & Visibility"),
                "desc": tr("Toggle speed limits, alert banners, and driver monitoring icon."),
                "icon": "system",
                "on_click": lambda: self._controller._navigate_to("declutter"),
            },
            {
                "title": tr("Navigation & Mapping"),
                "desc": tr("Configure road names, Vienna signs, and offroad routes."),
                "icon": "navigate",
                "on_click": lambda: self._controller._navigate_to("nav"),
            },
            {
                "title": tr("Camera & System Startup"),
                "desc": tr("Manage driver monitoring cameras, boot logos, and startup sounds."),
                "icon": "vehicle",
                "on_click": lambda: self._controller._navigate_to("system"),
            },
            {
                "title": tr("Advanced Metrics"),
                "desc": tr("Adjust radar plots, lead vehicle info, and stop sign metrics."),
                "icon": "sound",
                "on_click": lambda: self._controller._navigate_to("dev"),
            },
        ]


class StarPilotAppearanceLayout(_SettingsPage):
    def __init__(self):
        super().__init__()
        self._build_view()

    def _make_parent(self, key: str, label: str, subtitle: str = "") -> ParentToggle:
        return ParentToggle(
            label=label,
            subtitle=subtitle,
            get_state=lambda k=key: self._params.get_bool(k),
            set_state=lambda s, k=key: self._params.put_bool(k, s),
        )

    def _show_lead_detection_threshold_selector(self):
        def on_close(res, val):
            if res == DialogResult.CONFIRM:
                self._params.put_int("LeadDetectionThreshold", int(val))
        gui_app.push_widget(
            AetherSliderDialog(
                tr("Lead Detection Threshold"),
                25.0, 100.0, 1.0,
                float(self._params.get_int("LeadDetectionThreshold", return_default=True, default=35)),
                on_close,
                presets=[25.0, 50.0, 75.0, 100.0],
                unit="%",
                color=PANEL_STYLE.accent,
            )
        )

    def _set_developer_sidebar(self, enabled):
        self._params.put_bool("DeveloperSidebar", enabled)
        if enabled:
            self._params.put_bool("DeveloperUI", True)

    def _set_developer_metrics(self, enabled):
        self._params.put_bool("DeveloperMetrics", enabled)
        if enabled:
            self._params.put_bool("DeveloperUI", True)

    def _build_view(self):
        po = lambda: self._params.get_bool("PedalsOnUI")
        ol = lambda: starpilot_state.car_state.hasOpenpilotLongitudinal
        bsm = lambda: starpilot_state.car_state.hasBSM
        model_on = lambda: self._params.get_bool("ModelUI")
        hud_on = lambda: self._params.get_bool("CustomUI")
        dev_metrics_on = lambda: self._params.get_bool("DeveloperMetrics")
        dev_sidebar_on = lambda: self._params.get_bool("DeveloperSidebar")

        # ═══ 1. Model & Path Visualization ═══
        self._model_rows = [
            SettingRow("DynamicPathWidth", "toggle", tr_noop("Dynamic Path"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("DynamicPathWidth"),
                       set_state=lambda s: self._params.put_bool("DynamicPathWidth", s),
                       visible=model_on),
            SettingRow("LaneLinesWidth", "value", tr_noop("Lane Line Width"),
                       subtitle="",
                       get_value=self._get_lane_lines_display,
                       on_click=lambda: self._show_int_selector("LaneLinesWidth", 0, 24, self._get_lane_lines_unit()),
                       visible=model_on),
            SettingRow("LaneLinesColor", "value", tr_noop("Lane Line Color"),
                       subtitle="",
                       get_value=lambda: self._get_color_display("LaneLinesColor"),
                       on_click=lambda: self._show_color_selector("LaneLinesColor"),
                       visible=model_on),
            SettingRow("PathWidth", "value", tr_noop("Path Width"),
                       subtitle="",
                       get_value=self._get_path_width_display,
                       on_click=self._show_path_width_selector,
                       visible=model_on),
            SettingRow("PathEdgeWidth", "value", tr_noop("Path Edge Width"),
                       subtitle="",
                       get_value=lambda: f"{self._params.get_int('PathEdgeWidth')}%",
                       on_click=lambda: self._show_int_selector("PathEdgeWidth", 0, 100, "%"),
                       visible=model_on),
            SettingRow("PathEdgesColor", "value", tr_noop("Path Edge Color"),
                       subtitle="",
                       get_value=lambda: self._get_color_display("PathEdgesColor"),
                       on_click=lambda: self._show_color_selector("PathEdgesColor"),
                       visible=model_on),
            SettingRow("PathColor", "value", tr_noop("Path Color"),
                       subtitle="",
                       get_value=lambda: self._get_color_display("PathColor"),
                       on_click=lambda: self._show_color_selector("PathColor"),
                       visible=model_on),
            SettingRow("RoadEdgesWidth", "value", tr_noop("Road Edge Width"),
                       subtitle="",
                       get_value=self._get_road_edges_display,
                       on_click=lambda: self._show_int_selector("RoadEdgesWidth", 0, 24, self._get_road_edges_unit()),
                       visible=model_on),
            SettingRow("RainbowPath", "toggle", tr_noop("Rainbow Path"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("RainbowPath"),
                       set_state=lambda s: self._params.put_bool("RainbowPath", s),
                       visible=model_on),
            SettingRow("AccelerationPath", "toggle", tr_noop("Acceleration Path"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("AccelerationPath"),
                       set_state=lambda s: self._params.put_bool("AccelerationPath", s),
                       enabled=ol,
                       visible=model_on),
            SettingRow("AdjacentPath", "toggle", tr_noop("Adjacent Lanes"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("AdjacentPath"),
                       set_state=lambda s: self._params.put_bool("AdjacentPath", s),
                       visible=model_on),
            SettingRow("AdjacentPathMetrics", "toggle", tr_noop("Adjacent Lane Metrics"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("AdjacentPathMetrics"),
                       set_state=lambda s: self._params.put_bool("AdjacentPathMetrics", s),
                       visible=model_on),
            SettingRow("BlindSpotPath", "toggle", tr_noop("Blind Spot Path"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("BlindSpotPath"),
                       set_state=lambda s: self._params.put_bool("BlindSpotPath", s),
                       enabled=bsm,
                       visible=model_on),
        ]

        # ═══ 2. Driving Widgets & HUD ═══
        self._hud_rows = [
            SettingRow("Compass", "toggle", tr_noop("Compass"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("Compass"),
                       set_state=lambda s: self._params.put_bool("Compass", s),
                       visible=hud_on),
            SettingRow("OnroadDistanceButton", "toggle", tr_noop("Personality Button"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("OnroadDistanceButton"),
                       set_state=lambda s: self._params.put_bool("OnroadDistanceButton", s),
                       visible=hud_on),
            SettingRow("RotatingWheel", "toggle", tr_noop("Rotating Wheel"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("RotatingWheel"),
                       set_state=lambda s: self._params.put_bool("RotatingWheel", s),
                       visible=hud_on),
            SettingRow("ShowSteering", "toggle", tr_noop("Steering Torque Indicator"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("ShowSteering"),
                       set_state=lambda s: self._params.put_bool("ShowSteering", s),
                       visible=hud_on),
            SettingRow("EnableTorqueBarWidget", "toggle", tr_noop("Torque Bar"),
                       subtitle=tr_noop("Show a curved torque-utilization indicator at the bottom of the driving screen."),
                       get_state=lambda: self._params.get_bool("EnableTorqueBarWidget"),
                       set_state=lambda s: self._params.put_bool("EnableTorqueBarWidget", s),
                       visible=hud_on),
            SettingRow("SignalMetrics", "toggle", tr_noop("Turn Signal Borders"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("SignalMetrics"),
                       set_state=lambda s: self._params.put_bool("SignalMetrics", s),
                       visible=hud_on),
            SettingRow("BlindSpotMetrics", "toggle", tr_noop("Blind Spot Borders"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("BlindSpotMetrics"),
                       set_state=lambda s: self._params.put_bool("BlindSpotMetrics", s),
                       enabled=bsm,
                       visible=hud_on),
            SettingRow("WheelSpeed", "toggle", tr_noop("Wheel Speed"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("WheelSpeed"),
                       set_state=lambda s: self._params.put_bool("WheelSpeed", s),
                       visible=hud_on),
            SettingRow("BorderWidth", "value", tr_noop("Border Width"),
                       subtitle="",
                       get_value=lambda: f"{int(round(self._params.get_float('BorderWidth')))}%",
                       on_click=lambda: self._show_float_selector("BorderWidth", 25, 250, 5, "%"),
                       visible=hud_on),
            SettingRow("PedalsOnUI", "toggle", tr_noop("Pedal Indicators"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("PedalsOnUI"),
                       set_state=lambda s: self._params.put_bool("PedalsOnUI", s),
                       enabled=ol,
                       visible=hud_on),
            SettingRow("DynamicPedalsOnUI", "toggle", tr_noop("Dynamic Pedals"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("DynamicPedalsOnUI"),
                       set_state=lambda s: self._set_exclusive_pedal("DynamicPedalsOnUI", "StaticPedalsOnUI", s),
                       enabled=lambda: po() and ol(),
                       visible=hud_on),
            SettingRow("StaticPedalsOnUI", "toggle", tr_noop("Static Pedals"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("StaticPedalsOnUI"),
                       set_state=lambda s: self._set_exclusive_pedal("StaticPedalsOnUI", "DynamicPedalsOnUI", s),
                       enabled=lambda: po() and ol(),
                       visible=hud_on),
            SettingRow("StoppedTimer", "toggle", tr_noop("Stopped Timer"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("StoppedTimer"),
                       set_state=lambda s: self._params.put_bool("StoppedTimer", s)),
            SettingRow("ShowCSCStatus", "toggle", tr_noop("CSC Status Widget"),
                       subtitle=tr_noop("Show the Curve Speed Controller target speed and ambient border glow."),
                       get_state=lambda: self._params.get_bool("ShowCSCStatus"),
                       set_state=lambda s: self._params.put_bool("ShowCSCStatus", s),
                       visible=hud_on),
        ]

        # ═══ 3. Screen Declutter & Visibility ═══
        self._declutter_rows = [
            SettingRow("HideSpeed", "toggle", tr_noop("Hide Speed"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("HideSpeed"),
                       set_state=lambda s: self._params.put_bool("HideSpeed", s)),
            SettingRow("HideMaxSpeed", "toggle", tr_noop("Hide Max Speed"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("HideMaxSpeed"),
                       set_state=lambda s: self._params.put_bool("HideMaxSpeed", s)),
            SettingRow("HideSpeedLimit", "toggle", tr_noop("Hide Speed Limit"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("HideSpeedLimit"),
                       set_state=lambda s: self._params.put_bool("HideSpeedLimit", s),
                       visible=lambda: ol() and self._params.get_bool("SpeedLimitController")),
            SettingRow("HideAlerts", "toggle", tr_noop("Hide Alerts"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("HideAlerts"),
                       set_state=lambda s: self._params.put_bool("HideAlerts", s)),
            SettingRow("HideSteeringWheel", "toggle", tr_noop("Hide Steering Wheel"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("HideSteeringWheel"),
                       set_state=lambda s: self._params.put_bool("HideSteeringWheel", s)),
            SettingRow("HideDMIcon", "toggle", tr_noop("Hide Driver Monitoring Icon"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("HideDMIcon"),
                       set_state=lambda s: self._params.put_bool("HideDMIcon", s)),
            SettingRow("HideLeadMarker", "toggle", tr_noop("Hide Lead Marker"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("HideLeadMarker"),
                       set_state=lambda s: self._params.put_bool("HideLeadMarker", s),
                       visible=ol),
            SettingRow("HideChangingLanesBanner", "toggle", tr_noop("Hide Changing Lanes Banner"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("HideChangingLanesBanner"),
                       set_state=lambda s: self._params.put_bool("HideChangingLanesBanner", s)),
            SettingRow("HideDistanceProfileBanner", "toggle", tr_noop("Hide Distance Profile Banner"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("HideDistanceProfileBanner"),
                       set_state=lambda s: self._params.put_bool("HideDistanceProfileBanner", s)),
            SettingRow("HideTurningBanner", "toggle", tr_noop("Hide Turning Banner"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("HideTurningBanner"),
                       set_state=lambda s: self._params.put_bool("HideTurningBanner", s)),
        ]

        # ═══ 4. Navigation & Mapping ═══
        self._nav_rows = [
            SettingRow("NavigationUI", "toggle", tr_noop("Navigation Widgets"),
                       subtitle=tr_noop("Show navigation info on the driving screen."),
                       get_state=lambda: self._params.get_bool("NavigationUI"),
                       set_state=lambda s: self._params.put_bool("NavigationUI", s)),
            SettingRow("ClearNavOnOffroad", "toggle", tr_noop("Clear Route When Offroad"),
                       subtitle=tr_noop("Clear the active navigation destination when the device goes offroad."),
                       get_state=lambda: self._params.get_bool("ClearNavOnOffroad"),
                       set_state=lambda s: self._params.put_bool("ClearNavOnOffroad", s)),
            SettingRow("RoadNameUI", "toggle", tr_noop("Road Name"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("RoadNameUI"),
                       set_state=lambda s: self._params.put_bool("RoadNameUI", s)),
            SettingRow("ShowSpeedLimits", "toggle", tr_noop("Speed Limits"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("ShowSpeedLimits"),
                       set_state=lambda s: self._params.put_bool("ShowSpeedLimits", s),
                       visible=lambda: not (self._params.get_bool("SpeedLimitController") and ol())),
            SettingRow("UseVienna", "toggle", tr_noop("Vienna Signs"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("UseVienna"),
                       set_state=lambda s: self._params.put_bool("UseVienna", s),
                       visible=lambda: self._params.get_bool("ShowSpeedLimits") or self._params.get_bool("SpeedLimitController")),
            SettingRow("QOLVisuals", "toggle", tr_noop("Quality of Life"),
                       subtitle=tr_noop("Convenience features for everyday driving."),
                       get_state=lambda: self._params.get_bool("QOLVisuals"),
                       set_state=lambda s: self._params.put_bool("QOLVisuals", s)),
        ]

        # ═══ 5. Camera & System Startup ═══
        self._system_rows = [
            SettingRow("CameraView", "value", tr_noop("Camera View"),
                       subtitle="",
                       get_value=lambda: tr(CAMERA_VIEWS[self._params.get_int("CameraView")]),
                       on_click=self._show_camera_view_selector),
            SettingRow("DriverCamera", "toggle", tr_noop("Driver Camera"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("DriverCamera"),
                       set_state=lambda s: self._params.put_bool("DriverCamera", s)),
            SettingRow("BootLogo", "value", tr_noop("Boot Logo"),
                       subtitle="",
                       get_value=lambda: self._get_theme_value("BootLogo"),
                       on_click=self._show_boot_logo_manager),
            SettingRow("StartupAlert", "value", tr_noop("Startup Alert"),
                       subtitle="",
                       get_value=self._get_startup_alert_display,
                       on_click=self._show_startup_alert_selector),
        ]

        # ═══ 6. Advanced Metrics ═══
        self._dev_rows = [
            SettingRow("DeveloperSidebar", "toggle", tr_noop("Developer Sidebar"),
                       subtitle=tr_noop("Driving metrics panel on the right"),
                       get_state=lambda: self._params.get_bool("DeveloperSidebar"),
                       set_state=lambda s: self._set_developer_sidebar(s)),
            SettingRow("LeadDetectionThreshold", "value", tr_noop("Lead Detection Threshold"),
                       subtitle="",
                       get_value=lambda: f"{self._params.get_int('LeadDetectionThreshold', return_default=True, default=35)}%",
                       on_click=self._show_lead_detection_threshold_selector,
                       enabled=ol),
            SettingRow("LeadInfo", "toggle", tr_noop("Lead Vehicle Metrics"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("LeadInfo"),
                       set_state=lambda s: self._params.put_bool("LeadInfo", s),
                       enabled=ol),
            SettingRow("RadarTracksUI", "toggle", tr_noop("Radar Point Display"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("RadarTracksUI"),
                       set_state=lambda s: self._params.put_bool("RadarTracksUI", s),
                       enabled=lambda: starpilot_state.car_state.hasRadar),
            SettingRow("ShowStoppingPoint", "toggle", tr_noop("Show Stop Sign"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("ShowStoppingPoint"),
                       set_state=lambda s: self._params.put_bool("ShowStoppingPoint", s),
                       enabled=ol),
            SettingRow("ShowStoppingPointMetrics", "toggle", tr_noop("Stop Distance"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("ShowStoppingPointMetrics"),
                       set_state=lambda s: self._params.put_bool("ShowStoppingPointMetrics", s),
                       enabled=lambda: self._params.get_bool("ShowStoppingPoint") and ol()),
            SettingRow("DeveloperMetrics", "toggle", tr_noop("Developer Metrics"),
                       subtitle=tr_noop("Performance data, sensor readings, and system metrics."),
                       get_state=lambda: self._params.get_bool("DeveloperMetrics"),
                       set_state=lambda s: self._set_developer_metrics(s)),
            SettingRow("FPSCounter", "toggle", tr_noop("FPS Display"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("FPSCounter"),
                       set_state=lambda s: self._params.put_bool("FPSCounter", s),
                       visible=dev_metrics_on),
            SettingRow("ShowCPU", "toggle", tr_noop("CPU Metrics"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("ShowCPU"),
                       set_state=lambda s: self._params.put_bool("ShowCPU", s),
                       visible=dev_metrics_on),
            SettingRow("ShowGPU", "toggle", tr_noop("GPU Metrics"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("ShowGPU"),
                       set_state=lambda s: self._params.put_bool("ShowGPU", s),
                       visible=dev_metrics_on),
            SettingRow("NumericalTemp", "toggle", tr_noop("Temperature Metrics"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("NumericalTemp"),
                       set_state=lambda s: self._params.put_bool("NumericalTemp", s),
                       visible=dev_metrics_on),
            SettingRow("ShowMemoryUsage", "toggle", tr_noop("RAM Metrics"),
                       subtitle="",
                       get_state=lambda: self._params.get_bool("ShowMemoryUsage"),
                       set_state=lambda s: self._params.put_bool("ShowMemoryUsage", s),
                       visible=dev_metrics_on),
            SettingRow("DeveloperSidebarMetrics", "value", tr_noop("Developer Sidebar Metrics"),
                       subtitle=tr_noop("Pick which metrics appear in the developer sidebar on the driving screen."),
                       get_value=lambda: tr("Manage"),
                       on_click=lambda: self._navigate_to("dev_sidebar"),
                       visible=dev_sidebar_on),
        ]

        self._dev_sidebar_rows = [
            SettingRow(
                f"DeveloperSidebarMetric{i}",
                "value",
                tr_noop(f"Metric #{i}"),
                subtitle="",
                get_value=lambda i=i: self._get_developer_sidebar_metric_display(i),
                on_click=lambda i=i: self._show_developer_sidebar_metric_selector(i),
                visible=dev_sidebar_on,
            )
            for i in range(1, 8)
        ]

        self._manager_view = AppearanceManagerView(
            self, [],
            header_title=tr_noop("Appearance"),
            header_subtitle=tr_noop("Customize your display, driving widgets, model visualization, and themes."),
            tab_defs=None,
            panel_style=PANEL_STYLE,
        )

        pt_model = self._make_parent("ModelUI", "Model UI",
            "Display the driving model path, lanes, and road edges.")
        pt_hud = self._make_parent("CustomUI", "Driving Screen Widgets",
            "Show interactive indicators on the driving screen.")
        pt_declutter = self._make_parent("AdvancedCustomUI", "Advanced UI Controls",
            "Fine-tune which elements appear on screen.")

        # Register subpanels for Level 2 slide transitions
        self._sub_panels["model"] = AetherSettingsView(
            self,
            [SettingSection(title="", rows=self._model_rows)],
            header_title=tr_noop("Model & Path Visualization"),
            header_subtitle=tr_noop("Customize dynamic lane paths, road edges, and colors."),
            parent_toggle=pt_model,
            panel_style=PANEL_STYLE,
        )
        self._sub_panels["hud"] = AetherSettingsView(
            self,
            [SettingSection(title="", rows=self._hud_rows)],
            header_title=tr_noop("Driving Widgets & HUD"),
            header_subtitle=tr_noop("Configure compass, dynamic pedals, signals, and screen borders."),
            parent_toggle=pt_hud,
            panel_style=PANEL_STYLE,
        )
        self._sub_panels["declutter"] = AetherSettingsView(
            self,
            [SettingSection(title="", rows=self._declutter_rows)],
            header_title=tr_noop("Screen Declutter & Visibility"),
            header_subtitle=tr_noop("Toggle speed limits, alert banners, and driver monitoring icon."),
            parent_toggle=pt_declutter,
            panel_style=PANEL_STYLE,
        )
        self._sub_panels["nav"] = AetherSettingsView(
            self,
            [SettingSection(title="", rows=self._nav_rows)],
            header_title=tr_noop("Navigation & Mapping"),
            header_subtitle=tr_noop("Configure road names, Vienna signs, and offroad routes."),
            panel_style=PANEL_STYLE,
        )
        self._sub_panels["system"] = AetherSettingsView(
            self,
            [SettingSection(title="", rows=self._system_rows)],
            header_title=tr_noop("Camera & System Startup"),
            header_subtitle=tr_noop("Manage driver monitoring cameras, boot logos, and startup sounds."),
            panel_style=PANEL_STYLE,
        )
        self._sub_panels["dev"] = AetherSettingsView(
            self,
            [SettingSection(title="", rows=self._dev_rows)],
            header_title=tr_noop("Advanced Metrics"),
            header_subtitle=tr_noop("Adjust radar plots, lead vehicle info, and stop sign metrics."),
            panel_style=PANEL_STYLE,
        )
        self._sub_panels["dev_sidebar"] = AetherSettingsView(
            self,
            [SettingSection(title="", rows=self._dev_sidebar_rows)],
            header_title=tr_noop("Developer Sidebar Metrics"),
            header_subtitle=tr_noop("Pick which metrics appear in the developer sidebar on the driving screen."),
            panel_style=PANEL_STYLE,
        )
        self._wire_sub_panels()

    # ── Theme helpers ──

    def _build_theme_options(self, key: str) -> tuple[list[str], dict[str, str], str]:
        config = THEME_KEY_CONFIG[key]
        options_map = {display: slug for slug, display in config["extra"]}
        current_slug = self._params.get(key, encoding='utf-8') or config["default"]
        current_display = _theme_display_name(current_slug)
        if current_display not in options_map:
            options_map[current_display] = current_slug
        options = sorted(options_map.keys(), key=str.casefold)
        return options, options_map, current_display

    def _get_theme_value(self, key: str) -> str:
        default = THEME_KEY_CONFIG[key]["default"]
        return _theme_display_name(self._params.get(key, encoding='utf-8') or default)

    def _show_theme_selector(self, key):
        themes, option_map, current = self._build_theme_options(key)
        if not themes:
            return

        def on_select(res):
            if res == DialogResult.CONFIRM and dialog.selection:
                selected_slug = option_map.get(dialog.selection)
                if selected_slug is None:
                    return
                self._params.put(key, selected_slug)

        dialog = MultiOptionDialog(tr(key), themes, current, callback=on_select)
        gui_app.push_widget(dialog)

    # ── Widget helpers ──

    def _set_exclusive_pedal(self, key, other_key, state):
        self._params.put_bool(key, state)
        if state:
            self._params.put_bool(other_key, False)

    # ── Camera view ──

    def _show_camera_view_selector(self):
        current = self._params.get_int("CameraView")

        def on_select(res):
            if res == DialogResult.CONFIRM and dialog.selection:
                idx = CAMERA_VIEWS.index(dialog.selection)
                self._params.put_int("CameraView", idx)

        dialog = MultiOptionDialog(tr("Camera View"), CAMERA_VIEWS, CAMERA_VIEWS[current], callback=on_select)
        gui_app.push_widget(dialog)

    # ── Color selectors ──

    def _get_color_display(self, key):
        val = self._params.get(key, encoding='utf-8') or ""
        if not val:
            return "Stock"
        return val.upper()

    def _show_color_selector(self, key):
        current = self._params.get(key, encoding='utf-8') or "Stock"

        def on_select(res):
            if res == DialogResult.CONFIRM and dialog.selection:
                if dialog.selection == "Stock":
                    self._params.remove(key)
                else:
                    self._params.put(key, dialog.selection)

        dialog = MultiOptionDialog(tr(key), COLOR_PRESETS, current, callback=on_select)
        gui_app.push_widget(dialog)

    # ── Numeric sliders (int / float) ──

    def _show_int_selector(self, key, min_v, max_v, unit=""):
        def on_close(res, val):
            if res == DialogResult.CONFIRM:
                self._params.put_int(key, int(val))
        gui_app.push_widget(AetherSliderDialog(tr(key), min_v, max_v, 1, self._params.get_int(key), on_close,
                                                 unit=unit, color=PANEL_STYLE.accent))

    def _show_float_selector(self, key, min_v, max_v, step, unit="", convert=None, unconvert=None):
        current = self._params.get_float(key)
        if convert:
            current = convert(current)

        def on_close(res, val):
            if res == DialogResult.CONFIRM:
                v = float(val)
                if unconvert:
                    v = unconvert(v)
                self._params.put_float(key, v)

        gui_app.push_widget(AetherSliderDialog(tr(key), min_v, max_v, step, current, on_close,
                                                 unit=unit, color=PANEL_STYLE.accent))

    # ── Unit-aware display helpers ──

    def _is_metric(self):
        return self._params.get_bool("IsMetric")

    def _get_lane_lines_unit(self):
        return "cm" if self._is_metric() else "in"

    def _get_lane_lines_display(self):
        val = self._params.get_int("LaneLinesWidth")
        if self._is_metric():
            return f"{int(val * 2.54)}cm"
        return f"{val}in"

    def _get_road_edges_unit(self):
        return "cm" if self._is_metric() else "in"

    def _get_road_edges_display(self):
        val = self._params.get_int("RoadEdgesWidth")
        if self._is_metric():
            return f"{int(val * 2.54)}cm"
        return f"{val}in"

    def _get_path_width_display(self):
        val = self._params.get_float("PathWidth")
        if self._is_metric():
            return f"{val / 3.28084:.1f}m"
        return f"{val:.1f}ft"

    def _show_path_width_selector(self):
        if self._is_metric():
            self._show_float_selector("PathWidth", 0, 10, 0.1, "m", convert=lambda v: v / 3.28084, unconvert=lambda v: v * 3.28084)
        else:
            self._show_float_selector("PathWidth", 0, 10, 0.1, "ft")

    # ── Startup alert ──

    def _get_startup_alert_display(self):
        current_top = self._params.get("StartupMessageTop", encoding='utf-8') or ""
        if current_top == "Be ready to take over at any time":
            return "Stock"
        if current_top == "Hop in and buckle up!":
            return "StarPilot"
        return "Clear"

    def _show_startup_alert_selector(self):
        options = ["Stock", "StarPilot", "Clear"]
        current = self._get_startup_alert_display()

        def on_select(res):
            if res == DialogResult.CONFIRM and dialog.selection:
                if dialog.selection == "Stock":
                    self._params.put("StartupMessageTop", "Be ready to take over at any time")
                    self._params.put("StartupMessageBottom", "Always keep hands on wheel and eyes on road")
                elif dialog.selection == "StarPilot":
                    self._params.put("StartupMessageTop", "Hop in and buckle up!")
                    self._params.put("StartupMessageBottom", "Human-tested, frog-approved")
                else:
                    self._params.remove("StartupMessageTop")
                    self._params.remove("StartupMessageBottom")

        dialog = MultiOptionDialog(tr("Startup Alert"), options, current, callback=on_select)
        gui_app.push_widget(dialog)

    # ── Developer sidebar metric selectors ──

    def _show_developer_sidebar_metric_selector(self, idx: int):
        key = f"DeveloperSidebarMetric{idx}"
        current_int = self._params.get_int(key)
        options = list(DEVELOPER_SIDEBAR_METRIC_OPTIONS.values())
        current_display = DEVELOPER_SIDEBAR_METRIC_OPTIONS.get(current_int, tr("None"))

        def on_select(res):
            if res == DialogResult.CONFIRM and dialog.selection:
                selected_int = next(
                    (k for k, v in DEVELOPER_SIDEBAR_METRIC_OPTIONS.items() if v == dialog.selection),
                    0,
                )
                self._params.put_int(key, selected_int)

        dialog = MultiOptionDialog(tr(f"Metric #{idx}"), options, current_display, callback=on_select)
        gui_app.push_widget(dialog)

    def _get_developer_sidebar_metric_display(self, idx: int) -> str:
        val = self._params.get_int(f"DeveloperSidebarMetric{idx}")
        return tr(DEVELOPER_SIDEBAR_METRIC_OPTIONS.get(val, "None"))

    # ── Boot logo manager ──

    def _show_boot_logo_manager(self):
        def on_close(res, val):
            pass

        gui_app.push_widget(SimpleDownloadManager(
            title=tr("Boot Logo"),
            asset_type="boot logo",
            directory=THEME_SAVE_PATH / "bootlogos",
            asset_param="BootLogo",
            download_param="BootLogoToDownload",
            downloadable_list_param="DownloadableBootLogos",
            params=self._params,
            params_memory=self._params_memory,
            on_close=on_close,
        ))
