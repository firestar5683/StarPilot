from __future__ import annotations

from openpilot.system.hardware import HARDWARE
from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult

from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import _SettingsPage
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  DEFAULT_PANEL_STYLE,
  AetherSettingsView,
  CardHubManagerView,
  ParentToggle,
  SettingRow,
  SettingSection,
  AetherSliderDialog,
)


def _confirm_reboot_toggle(params, key, state):
  params.put_bool(key, state)
  from openpilot.selfdrive.ui.ui_state import ui_state
  if ui_state.started:
    from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
    gui_app.push_widget(ConfirmDialog(
      tr("Reboot required. Reboot now?"), tr("Reboot"), tr("Cancel"),
      callback=lambda res: HARDWARE.reboot() if res == DialogResult.CONFIRM else None,
    ))


PANEL_STYLE = DEFAULT_PANEL_STYLE
_LATERAL_TUNE_KEYS = ["TurnDesires", "NNFF", "NNFFLite", "ForceTorqueController"]
_ADVANCED_LATERAL_KEYS = ["ForceAutoTune", "ForceAutoTuneOff"]


def _sync_parent(params, parent_key, child_keys):
  if any(params.get_bool(k) for k in child_keys):
    if not params.get_bool(parent_key):
      params.put_bool(parent_key, True)
  else:
    if params.get_bool(parent_key):
      params.put_bool(parent_key, False)


# ═══════════════════════════════════════════════════════════════
# SteeringManagerView — 3-card category hub
# ═══════════════════════════════════════════════════════════════

class SteeringManagerView(CardHubManagerView):
  def __init__(self, controller, **kwargs):
    super().__init__(controller, [], **kwargs)

  def _build_cards(self):
    return [
      {
        "title": tr("Steering Behavior"),
        "desc": tr("Configure Always On Lateral (AOL), pause speed thresholds, and turn signal behaviors."),
        "icon": "steering",
        "on_click": lambda: self._controller._navigate_to("behavior"),
      },
      {
        "title": tr("Lane Changes"),
        "desc": tr("Configure automatic lane changes, speed/width thresholds, and smoothing parameters."),
        "icon": "road",
        "on_click": lambda: self._controller._navigate_to("lane_changes"),
      },
      {
        "title": tr("Advanced Lateral Tuning"),
        "desc": tr("Adjust actuator delay, steer ratio, Kp, friction, and neural network feedforward controllers."),
        "icon": "system",
        "on_click": lambda: self._controller._navigate_to("advanced"),
      },
    ]


# ═══════════════════════════════════════════════════════════════
# StarPilotLateralLayout — controller
# ═══════════════════════════════════════════════════════════════

class StarPilotLateralLayout(_SettingsPage):

  def __init__(self):
    super().__init__()
    self._build_panels()

  def _make_parent(self, key: str, label: str, subtitle: str = "") -> ParentToggle:
    return ParentToggle(
      label=label,
      subtitle=subtitle,
      get_state=lambda k=key: self._params.get_bool(k),
      set_state=lambda s, k=key: self._params.put_bool(k, s),
    )

  def _build_panels(self):
    p = self._params
    cs = starpilot_state.car_state

    def alt_on():
      return p.get_bool("AdvancedLateralTune")

    def aol_on():
      return p.get_bool("AlwaysOnLateral")

    def lc_on():
      return p.get_bool("LaneChanges")

    def nlc_on():
      return lc_on() and p.get_bool("NudgelessLaneChange")

    def close_gap_on():
      return lc_on() and p.get_bool("LaneChangeCloseGap")

    def pos_on():
      return p.get_bool("PauseLateralOnSignal")

    # ── 1. Steering Behavior ──
    self._behavior_rows = [
      SettingRow(
        "PauseAOLOnBrake", "value", tr_noop("Pause AOL On Brake"),
        subtitle=tr_noop("Pause AOL below this speed while brake is pressed."),
        get_value=lambda: f"{p.get_int('PauseAOLOnBrake')} mph",
        on_click=lambda: self._show_slider("PauseAOLOnBrake", 0, 100, unit=" mph"),
        visible=aol_on,
      ),
      SettingRow(
        "PauseLateralSpeed", "value", tr_noop("Pause Lateral Below"),
        subtitle=tr_noop("Pause steering below the set speed."),
        get_value=lambda: f"{p.get_int('PauseLateralSpeed')} mph",
        on_click=self._on_pause_lateral_speed_clicked,
      ),
      SettingRow(
        "PauseLateralOnSignal", "toggle", tr_noop("Turn Signal Only"),
        subtitle=tr_noop("Only pause steering when turn signal is active."),
        get_state=lambda: p.get_bool("PauseLateralOnSignal"),
        set_state=lambda s: p.put_bool("PauseLateralOnSignal", s),
      ),
      SettingRow(
        "LateralResumeDelay", "value", tr_noop("Resume Delay"),
        subtitle=tr_noop("Delay before lateral resumes after signal off. 0 = Off."),
        get_value=self._get_resume_delay_display,
        on_click=lambda: self._show_slider("LateralResumeDelay", 0.0, 5.0, step=0.1, unit="s", value_type="float"),
        visible=pos_on,
      ),
      SettingRow(
        "NavDesiresAllowed", "toggle", tr_noop("Use Route Desires"),
        subtitle=tr_noop("Allow navigation to request lane keep and turns."),
        get_state=lambda: p.get_bool("NavDesiresAllowed"),
        set_state=lambda s: p.put_bool("NavDesiresAllowed", s),
      ),
    ]

    # ── 2. Lane Changes ──
    self._lane_change_rows = [
      SettingRow(
        "NudgelessLaneChange", "toggle", tr_noop("Auto Lane Changes"),
        subtitle=tr_noop("Signal triggers automatic lane change."),
        get_state=lambda: p.get_bool("NudgelessLaneChange"),
        set_state=lambda s: p.put_bool("NudgelessLaneChange", s),
        visible=lc_on,
      ),
      SettingRow(
        "OneLaneChange", "toggle", tr_noop("One Per Signal"),
        subtitle=tr_noop("One lane change per signal activation."),
        get_state=lambda: p.get_bool("OneLaneChange"),
        set_state=lambda s: p.put_bool("OneLaneChange", s),
        visible=nlc_on,
      ),
      SettingRow(
        "MinimumLaneChangeSpeed", "value", tr_noop("Min Lane Change Speed"),
        subtitle=tr_noop("Lowest speed at which openpilot will change lanes."),
        get_value=lambda: f"{p.get_int('MinimumLaneChangeSpeed')} mph",
        on_click=lambda: self._show_slider("MinimumLaneChangeSpeed", 0, 100, unit=" mph"),
        visible=lc_on,
      ),
      SettingRow(
        "LaneChangeTime", "value", tr_noop("Lane Change Delay"),
        subtitle=tr_noop("Delay before the start of an automatic lane change. 0 = Instant."),
        get_value=self._get_lane_change_delay_display,
        on_click=lambda: self._show_slider("LaneChangeTime", 0.0, 5.0, step=0.1, unit="s", value_type="float"),
        visible=nlc_on,
      ),
      SettingRow(
        "LaneDetectionWidth", "value", tr_noop("Min Lane Width"),
        subtitle=tr_noop("Prevent lane changes into narrower lanes."),
        get_value=lambda: f"{p.get_float('LaneDetectionWidth'):.1f} ft",
        on_click=lambda: self._show_slider("LaneDetectionWidth", 0.0, 15.0, step=0.1, unit=" ft", value_type="float"),
        visible=nlc_on,
      ),
      SettingRow(
        "LaneChangeSmoothing", "value", tr_noop("Lane Change Smoothing"),
        subtitle=tr_noop("Smoothness of lane change commit. 10 = Stock, 1 = Smoothest."),
        get_value=self._get_lane_change_smoothing_display,
        on_click=self._show_lane_smoothing,
        visible=lc_on,
      ),
      SettingRow(
        "LaneChangeCloseGap", "toggle", tr_noop("Close Gap On Lane Change"),
        subtitle=tr_noop("Allows for a temporary shorter follow distance behind lead so that openpilot merges smoothly out of current lane, it will allow car to accelerate as it changes lanes."),
        get_state=lambda: p.get_bool("LaneChangeCloseGap"),
        set_state=lambda s: p.put_bool("LaneChangeCloseGap", s),
        visible=lc_on,
      ),
      SettingRow(
        "LaneChangeCloseGapSeconds", "value", tr_noop("Temporary Follow Distance"),
        subtitle=tr_noop("Follow distance to hold while changing lanes. Only applied when shorter than your normal gap."),
        get_value=self._get_lane_change_close_gap_display,
        on_click=lambda: self._show_slider("LaneChangeCloseGapSeconds", 0.5, 3.0, step=0.05, unit="s", value_type="float"),
        visible=close_gap_on,
      ),
    ]

    # ── 3. Advanced Lateral Tuning ──
    self._advanced_rows = [
      SettingRow(
        "NNFF", "toggle", tr_noop("NNFF"),
        subtitle=tr_noop("Neural net feedforward steering controller."),
        get_state=lambda: p.get_bool("NNFF"),
        set_state=lambda s: (p.put_bool("NNFF", s),
                             s and p.put_bool("NNFFLite", False),
                             _sync_parent(p, "LateralTune", _LATERAL_TUNE_KEYS)),
        enabled=lambda: cs.hasNNFFLog and not cs.isAngleCar,
        disabled_label=tr_noop("Not Available"),
        visible=alt_on,
      ),
      SettingRow(
        "NNFFLite", "toggle", tr_noop("NNFF Lite"),
        subtitle=tr_noop("Lightweight NNFF when full model is off."),
        get_state=lambda: p.get_bool("NNFFLite"),
        set_state=lambda s: (p.put_bool("NNFFLite", s),
                             _sync_parent(p, "LateralTune", _LATERAL_TUNE_KEYS)),
        enabled=lambda: not cs.isAngleCar,
        disabled_label=tr_noop("Not Available"),
        visible=alt_on,
      ),
      SettingRow(
        "ForceTorqueController", "toggle", tr_noop("Force Torque Ctrl"),
        subtitle=tr_noop("Torque-based steering for smoother lane keeping."),
        get_state=lambda: p.get_bool("ForceTorqueController"),
        set_state=lambda s: (p.put_bool("ForceTorqueController", s),
                             _sync_parent(p, "LateralTune", _LATERAL_TUNE_KEYS)),
        enabled=lambda: not cs.isTorqueCar and not cs.isAngleCar,
        disabled_label=tr_noop("Not Available"),
        visible=alt_on,
      ),
      SettingRow(
        "TurnDesires", "toggle", tr_noop("Force Turn Desires"),
        subtitle=tr_noop("Follow turn intent below min lane change speed."),
        get_state=lambda: p.get_bool("TurnDesires"),
        set_state=lambda s: (p.put_bool("TurnDesires", s),
                             _sync_parent(p, "LateralTune", _LATERAL_TUNE_KEYS)),
        visible=alt_on,
      ),
      SettingRow(
        "ForceAutoTune", "toggle", tr_noop("Force Auto-Tune On"),
        subtitle=tr_noop("Force-enable live auto-tuning for friction and lateral accel."),
        get_state=lambda: p.get_bool("ForceAutoTune"),
        set_state=lambda s: (p.put_bool("ForceAutoTune", s),
                             s and p.put_bool("ForceAutoTuneOff", False),
                             _sync_parent(p, "AdvancedLateralTune", _ADVANCED_LATERAL_KEYS)),
        enabled=lambda: not cs.hasAutoTune and cs.isTorqueCar and not cs.isAngleCar,
        disabled_label=tr_noop("Not Available"),
        visible=alt_on,
      ),
      SettingRow(
        "ForceAutoTuneOff", "toggle", tr_noop("Force Auto-Tune Off"),
        subtitle=tr_noop("Force-disable learned lateral values and use your set values."),
        get_state=lambda: p.get_bool("ForceAutoTuneOff"),
        set_state=lambda s: (p.put_bool("ForceAutoTuneOff", s),
                             s and p.put_bool("ForceAutoTune", False),
                             _sync_parent(p, "AdvancedLateralTune", _ADVANCED_LATERAL_KEYS)),
        enabled=lambda: cs.isTorqueCar and not cs.isAngleCar,
        disabled_label=tr_noop("Not Available"),
        visible=alt_on,
      ),
      SettingRow(
        "UseAutoSteerDelay", "toggle", tr_noop("Use Auto-Learned Delay"),
        subtitle=tr_noop("Learn the full steering delay automatically. The manual value below is ignored while enabled."),
        get_state=lambda: p.get_bool("UseAutoSteerDelay"),
        set_state=lambda s: p.put_bool("UseAutoSteerDelay", s),
        visible=lambda: alt_on() and cs.steerActuatorDelay != 0,
      ),
      SettingRow(
        "SteerDelay", "value", tr_noop("Actuator Delay"),
        subtitle=tr_noop("Exact full delay between steering command and vehicle response."),
        get_value=lambda: f"{p.get_float('SteerDelay'):.2f}s",
        on_click=lambda: self._show_slider("SteerDelay", 0.01, 1.0, step=0.01, unit="s", value_type="float"),
        enabled=lambda: not p.get_bool("UseAutoSteerDelay"),
        disabled_label=tr_noop("Disabled while auto-learned delay is enabled."),
        visible=lambda: alt_on() and cs.steerActuatorDelay != 0,
      ),
      SettingRow(
        "SteerFriction", "value", tr_noop("Friction"),
        subtitle=tr_noop("Compensates for steering friction around center."),
        get_value=lambda: f"{p.get_float('SteerFriction'):.2f}",
        on_click=lambda: self._show_slider("SteerFriction", 0.0, max(1.0, cs.friction * 1.5), step=0.01, value_type="float"),
        visible=lambda: alt_on() and cs.friction != 0 and cs.isTorqueCar and not cs.isAngleCar,
      ),
      SettingRow(
        "SteerKP", "value", tr_noop("Kp Factor"),
        subtitle=tr_noop("How strongly openpilot corrects lateral position."),
        get_value=lambda: f"{p.get_float('SteerKP'):.2f}",
        on_click=lambda: self._show_slider("SteerKP", max(0.01, cs.steerKp) * 0.5, max(0.01, cs.steerKp) * 1.5, step=0.01, value_type="float"),
        visible=lambda: alt_on() and cs.steerKp != 0 and cs.isTorqueCar and not cs.isAngleCar,
      ),
      SettingRow(
        "SteerLatAccel", "value", tr_noop("Lateral Acceleration"),
        subtitle=tr_noop("Maps steering torque to turning response."),
        get_value=lambda: f"{p.get_float('SteerLatAccel'):.2f}",
        on_click=lambda: self._show_slider("SteerLatAccel", max(0.01, cs.latAccelFactor) * 0.5, max(0.01, cs.latAccelFactor) * 1.5, step=0.01, value_type="float"),
        visible=lambda: alt_on() and cs.latAccelFactor != 0 and cs.isTorqueCar and not cs.isAngleCar,
      ),
      SettingRow(
        "SteerRatio", "value", tr_noop("Steer Ratio"),
        subtitle=tr_noop("Relationship between steering wheel and road-wheel angle."),
        get_value=lambda: f"{p.get_float('SteerRatio'):.1f}",
        on_click=lambda: self._show_slider("SteerRatio", max(0.01, cs.steerRatio) * 0.5, max(0.01, cs.steerRatio) * 1.5, step=0.01, value_type="float"),
        visible=lambda: alt_on() and cs.steerRatio != 0,
      ),
    ]

    self._manager_view = SteeringManagerView(
      self,
      header_title=tr_noop("Steering"),
      header_subtitle=tr_noop("Configure steering behavior and lane changes."),
    )

    p = self._params
    pt_behavior = ParentToggle(
      label="Always On Lateral",
      subtitle="Steering stays active when ACC is off.",
      get_state=lambda: p.get_bool("AlwaysOnLateral"),
      set_state=lambda s: _confirm_reboot_toggle(p, "AlwaysOnLateral", s) if s else p.put_bool("AlwaysOnLateral", False),
    )
    pt_lane_changes = self._make_parent("LaneChanges", "Lane Changes",
      "Allow openpilot to change lanes.")
    pt_advanced = self._make_parent("AdvancedLateralTune", "Advanced Lateral Tuning",
      "Fine-tune steering response and auto-tuning.")

    # Register subpanels for Level 2 slide transitions
    self._sub_panels["behavior"] = AetherSettingsView(
      self,
      [SettingSection(title="", rows=self._behavior_rows)],
      header_title=tr_noop("Steering Behavior"),
      header_subtitle=tr_noop("Configure Always On Lateral (AOL), pause speed thresholds, and turn signal behaviors."),
      parent_toggle=pt_behavior,
      panel_style=PANEL_STYLE,
    )
    self._sub_panels["lane_changes"] = AetherSettingsView(
      self,
      [SettingSection(title="", rows=self._lane_change_rows)],
      header_title=tr_noop("Lane Changes"),
      header_subtitle=tr_noop("Configure automatic lane changes, speed/width thresholds, and smoothing parameters."),
      parent_toggle=pt_lane_changes,
      panel_style=PANEL_STYLE,
    )
    self._sub_panels["advanced"] = AetherSettingsView(
      self,
      [SettingSection(title="", rows=self._advanced_rows)],
      header_title=tr_noop("Advanced Lateral Tuning"),
      header_subtitle=tr_noop("Adjust actuator delay, steer ratio, Kp, friction, and neural network feedforward controllers."),
      parent_toggle=pt_advanced,
      panel_style=PANEL_STYLE,
    )
    self._wire_sub_panels()

  def _on_pause_lateral_speed_clicked(self):
    def on_speed_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_int("PauseLateralSpeed", int(val))
        self._params.put_bool("QOLLateral", int(val) > 0)
    current = self._params.get_int("PauseLateralSpeed")
    gui_app.push_widget(AetherSliderDialog(
      tr("Pause Lateral Below"), 0, 100, 1, current, on_speed_close,
      unit=" mph", color=self.SLIDER_COLOR))

  def _get_resume_delay_display(self) -> str:
    val = self._params.get_float("LateralResumeDelay")
    if val == 0.0:
      return tr("Off")
    return f"{val:.1f}s"

  def _get_lane_change_delay_display(self) -> str:
    val = self._params.get_float("LaneChangeTime")
    if val == 0.0:
      return tr("Instant")
    return f"{val:.1f}s"

  def _get_lane_change_smoothing_display(self) -> str:
    val = self._params.get_int("LaneChangeSmoothing")
    if val == 0 or val == 10:
      return tr("Stock")
    return str(val)

  def _get_lane_change_close_gap_display(self) -> str:
    return f"{self._params.get_float('LaneChangeCloseGapSeconds'):.2f}s"

  def _show_lane_smoothing(self):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_int("LaneChangeSmoothing", int(val))
    current = self._params.get_int("LaneChangeSmoothing") if self._params.get_int("LaneChangeSmoothing") > 0 else 5
    gui_app.push_widget(AetherSliderDialog(tr("Lane Change Smoothing"), 1, 10, 1, current, on_close,
                                            color=self.SLIDER_COLOR))
