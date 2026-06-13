from __future__ import annotations

from openpilot.system.hardware import HARDWARE
from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog

from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import _SettingsPage
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  SettingRow, SettingSection, AetherSettingsView, COMPACT_PANEL_METRICS,
)
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  AETHER_LIST_METRICS,
  AetherSliderDialog,
  panel_style_from_color,
)


PANEL_STYLE = panel_style_from_color("#3B82F6")


def _confirm_reboot_toggle(params, key, state):
  params.put_bool(key, state)
  from openpilot.selfdrive.ui.ui_state import ui_state
  if ui_state.started:
    gui_app.push_widget(ConfirmDialog(
      tr("Reboot required. Reboot now?"), tr("Reboot"), tr("Cancel"),
      callback=lambda res: HARDWARE.reboot() if res == DialogResult.CONFIRM else None,
    ))


# ═══════════════════════════════════════════════════════════════
# StarPilotAdvancedLateralLayout
# ═══════════════════════════════════════════════════════════════

class StarPilotAdvancedLateralLayout(_SettingsPage):
  def __init__(self):
    super().__init__()
    self._build_view()

  def _advanced_enabled(self):
    return self._params.get_bool("AdvancedLateralTune")

  def _using_nnff(self):
    return starpilot_state.car_state.hasNNFFLog and self._params.get_bool("LateralTune") and self._params.get_bool("NNFF")

  def _forcing_auto_tune(self):
    return not starpilot_state.car_state.hasAutoTune and self._params.get_bool("ForceAutoTune")

  def _forcing_auto_tune_off(self):
    return starpilot_state.car_state.hasAutoTune and self._params.get_bool("ForceAutoTuneOff")

  def _forcing_torque_controller(self):
    return not starpilot_state.car_state.isAngleCar and self._params.get_bool("ForceTorqueController")

  def _torque_tuning_active(self):
    return starpilot_state.car_state.isTorqueCar or self._forcing_torque_controller() or self._using_nnff()

  def _manual_tuning_values_enabled(self):
    if starpilot_state.car_state.hasAutoTune:
      return self._forcing_auto_tune_off()
    return not self._forcing_auto_tune()

  def _build_view(self):
    adv = self._advanced_enabled
    torque = self._torque_tuning_active
    manual = self._manual_tuning_values_enabled
    nnff = self._using_nnff

    sections = [
      SettingSection(tr_noop("Steering Tuning"), [
        SettingRow("SteerDelay", "value", tr_noop("Actuator Delay"),
                   subtitle=tr_noop("The time between openpilot's steering command and the vehicle's response."),
                   get_value=lambda: f"{self._params.get_float('SteerDelay'):.2f}s",
                   on_click=lambda: self._show_slider("SteerDelay", 0.01, 1.0, step=0.01, unit="s", value_type="float"),
                   visible=lambda: adv() and starpilot_state.car_state.steerActuatorDelay != 0),
        SettingRow("SteerFriction", "value", tr_noop("Friction"),
                   subtitle=tr_noop("Compensates for steering friction around center."),
                   get_value=lambda: f"{self._params.get_float('SteerFriction'):.3f}",
                   on_click=lambda: self._show_slider("SteerFriction", 0.0, max(1.0, starpilot_state.car_state.friction * 1.5), step=0.01, value_type="float"),
                   visible=lambda: adv() and starpilot_state.car_state.friction != 0 and torque() and not nnff() and manual()),
        SettingRow("SteerKP", "value", tr_noop("Kp Factor"),
                   subtitle=tr_noop("How strongly openpilot corrects lateral position."),
                   get_value=lambda: f"{self._params.get_float('SteerKP'):.2f}",
                   on_click=lambda: self._show_slider("SteerKP", max(0.01, starpilot_state.car_state.steerKp) * 0.5, max(0.01, starpilot_state.car_state.steerKp) * 1.5, step=0.01, value_type="float"),
                   visible=lambda: adv() and starpilot_state.car_state.steerKp != 0 and torque() and not starpilot_state.car_state.isAngleCar),
        SettingRow("SteerLatAccel", "value", tr_noop("Lateral Acceleration"),
                   subtitle=tr_noop("Maps steering torque to turning response."),
                   get_value=lambda: f"{self._params.get_float('SteerLatAccel'):.2f}",
                   on_click=lambda: self._show_slider("SteerLatAccel", max(0.01, starpilot_state.car_state.latAccelFactor) * 0.5, max(0.01, starpilot_state.car_state.latAccelFactor) * 1.5, step=0.01, value_type="float"),
                   visible=lambda: adv() and starpilot_state.car_state.latAccelFactor != 0 and torque() and not nnff() and manual()),
        SettingRow("SteerRatio", "value", tr_noop("Steer Ratio"),
                   subtitle=tr_noop("Adjust the relationship between steering wheel input and road-wheel angle."),
                   get_value=lambda: f"{self._params.get_float('SteerRatio'):.2f}",
                   on_click=lambda: self._show_slider("SteerRatio", max(0.01, starpilot_state.car_state.steerRatio) * 0.5, max(0.01, starpilot_state.car_state.steerRatio) * 1.5, step=0.01, value_type="float"),
                   visible=lambda: adv() and starpilot_state.car_state.steerRatio != 0 and manual()),
        SettingRow("ForceAutoTune", "toggle", tr_noop("Force Auto-Tune On"),
                   subtitle=tr_noop("Force-enable live auto-tuning for friction and lateral acceleration."),
                   get_state=lambda: self._params.get_bool("ForceAutoTune"),
                   set_state=lambda s: (self._params.put_bool("ForceAutoTune", s), s and self._params.put_bool("ForceAutoTuneOff", False)),
                   visible=lambda: adv() and not starpilot_state.car_state.hasAutoTune and not starpilot_state.car_state.isAngleCar and torque()),
        SettingRow("ForceAutoTuneOff", "toggle", tr_noop("Force Auto-Tune Off"),
                   subtitle=tr_noop("Force-disable live auto-tuning and use your set values instead."),
                   get_state=lambda: self._params.get_bool("ForceAutoTuneOff"),
                   set_state=lambda s: (self._params.put_bool("ForceAutoTuneOff", s), s and self._params.put_bool("ForceAutoTune", False)),
                   visible=lambda: adv() and starpilot_state.car_state.hasAutoTune and not starpilot_state.car_state.isAngleCar),
        SettingRow("ForceTorqueController", "toggle", tr_noop("Force Torque Controller"),
                   subtitle=tr_noop("Use torque-based steering control instead of the stock steering mode when supported."),
                   get_state=lambda: self._params.get_bool("ForceTorqueController"),
                   set_state=lambda s: _confirm_reboot_toggle(self._params, "ForceTorqueController", s),
                   visible=lambda: adv() and not starpilot_state.car_state.isAngleCar and not starpilot_state.car_state.isTorqueCar),
      ]),
    ]
    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr_noop("Advanced Lateral Tuning"),
      header_subtitle=tr_noop("Adjust steering response, torque controller behavior, and auto-tuning controls."),
      panel_style=PANEL_STYLE,
      metrics=COMPACT_PANEL_METRICS,
    )


# ═══════════════════════════════════════════════════════════════
# StarPilotLateralLayout — top-level hub with 3 tabs
# ═══════════════════════════════════════════════════════════════

class StarPilotLateralLayout(_SettingsPage):
  def __init__(self):
    super().__init__()

    self._sub_panels = {
      "advanced_lateral": StarPilotAdvancedLateralLayout(),
    }
    self._wire_sub_panels()
    self._build_view()

  def _build_view(self):
    tab_defs = [
      {"id": "steering", "title": tr_noop("Steering"), "subtitle": tr_noop("Steering modes")},
      {"id": "lane", "title": tr_noop("Lane"), "subtitle": tr_noop("Lane changes")},
      {"id": "tune", "title": tr_noop("Tune"), "subtitle": tr_noop("Advanced controls")},
    ]

    sections = [
      # ── Steering tab ──
      SettingSection(tr_noop("Steering Modes"), [
        SettingRow("AlwaysOnLateral", "toggle", tr_noop("Always On Lateral"),
                   subtitle=tr_noop("Keep lateral control active even without openpilot engaged."),
                   get_state=lambda: self._params.get_bool("AlwaysOnLateral"),
                   set_state=lambda s: _confirm_reboot_toggle(self._params, "AlwaysOnLateral", s) if s else self._params.put_bool("AlwaysOnLateral", False)),
        SettingRow("PauseAOLOnBrake", "value", tr_noop("Pause Below"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int('PauseAOLOnBrake')} mph",
                   on_click=lambda: self._show_slider("PauseAOLOnBrake", 0, 100, unit=" mph"),
                   visible=lambda: self._params.get_bool("AlwaysOnLateral")),
        SettingRow("QOLLateral", "toggle", tr_noop("Quality of Life"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("QOLLateral"),
                   set_state=lambda s: self._params.put_bool("QOLLateral", s)),
        SettingRow("PauseLateralSpeed", "value", tr_noop("Pause Steering Below"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int('PauseLateralSpeed')} mph",
                   on_click=lambda: self._show_slider("PauseLateralSpeed", 0, 100, unit=" mph"),
                   visible=lambda: self._params.get_bool("QOLLateral")),
        SettingRow("PauseLateralOnSignal", "toggle", tr_noop("Turn Signal Only"),
                   subtitle=tr_noop("Only pause steering when the turn signal is active."),
                   get_state=lambda: self._params.get_bool("PauseLateralOnSignal"),
                   set_state=lambda s: self._params.put_bool("PauseLateralOnSignal", s),
                   visible=lambda: self._params.get_bool("QOLLateral") and self._params.get_int("PauseLateralSpeed") > 0),
        SettingRow("LateralResumeDelay", "value", tr_noop("Lateral Resume Delay"),
                   subtitle=tr_noop("Delay before steering resumes after the turn signal turns off. Set to 0 to disable."),
                   get_value=lambda: "Off" if self._params.get_float("LateralResumeDelay") == 0 else f"{self._params.get_float('LateralResumeDelay'):.1f}s",
                   on_click=lambda: self._show_slider("LateralResumeDelay", 0.0, 5.0, step=0.1, unit=" s", value_type="float"),
                   visible=lambda: self._params.get_bool("QOLLateral") and self._params.get_int("PauseLateralSpeed") > 0 and self._params.get_bool("PauseLateralOnSignal")),
      ], tab_key="steering"),

      # ── Lane tab ──
      SettingSection("", [
        SettingRow("LaneChanges", "toggle", tr_noop("Lane Changes"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("LaneChanges"),
                   set_state=lambda s: self._params.put_bool("LaneChanges", s)),
        SettingRow("NudgelessLaneChange", "toggle", tr_noop("Automatic Lane Changes"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("NudgelessLaneChange"),
                   set_state=lambda s: self._params.put_bool("NudgelessLaneChange", s),
                   visible=lambda: self._params.get_bool("LaneChanges")),
        SettingRow("LaneChangeTime", "value", tr_noop("Lane Change Delay"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_float('LaneChangeTime'):.1f}s",
                   on_click=lambda: self._show_slider("LaneChangeTime", 0.0, 5.0, step=0.1, unit="s", value_type="float"),
                   visible=lambda: self._params.get_bool("LaneChanges") and self._params.get_bool("NudgelessLaneChange")),
        SettingRow("MinimumLaneChangeSpeed", "value", tr_noop("Min Lane Change Speed"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_int('MinimumLaneChangeSpeed')} mph",
                   on_click=lambda: self._show_slider("MinimumLaneChangeSpeed", 0, 100, unit=" mph"),
                   visible=lambda: self._params.get_bool("LaneChanges")),
        SettingRow("LaneDetectionWidth", "value", tr_noop("Minimum Lane Width"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_float('LaneDetectionWidth'):.1f} ft",
                   on_click=lambda: self._show_slider("LaneDetectionWidth", 0.0, 15.0, step=0.1, unit=" ft", value_type="float"),
                   visible=lambda: self._params.get_bool("LaneChanges") and self._params.get_bool("NudgelessLaneChange")),
        SettingRow("OneLaneChange", "toggle", tr_noop("One Lane Change Per Signal"),
                   subtitle="",
                   get_state=lambda: self._params.get_bool("OneLaneChange"),
                   set_state=lambda s: self._params.put_bool("OneLaneChange", s),
                   visible=lambda: self._params.get_bool("LaneChanges")),
        SettingRow("LaneChangeSmoothing", "value", tr_noop("Lane Change Smoothing"),
                   subtitle=tr_noop("How smoothly openpilot commits to a lane change. 10 is stock; lower values produce a gentler, more gradual maneuver."),
                   get_value=lambda: f"{self._params.get_int('LaneChangeSmoothing')}",
                   on_click=self._show_modal_pace_selector,
                   visible=lambda: self._params.get_bool("LaneChanges")),
      ], tab_key="lane"),

      # ── Tune tab ──
      SettingSection(tr_noop("Advanced Lateral Tuning"), [
        SettingRow("AdvancedLateralTune", "toggle", tr_noop("Advanced Lateral Tuning"),
                   subtitle=tr_noop("Advanced steering control changes to fine-tune how openpilot drives."),
                   get_state=lambda: self._params.get_bool("AdvancedLateralTune"),
                   set_state=lambda s: self._params.put_bool("AdvancedLateralTune", s)),
        SettingRow("AdvancedConfigure", "value", tr_noop("Configure"),
                   subtitle=tr_noop("Adjust steering response, torque controller behavior, and auto-tuning controls."),
                   get_value=lambda: tr_noop("Settings"),
                   navigate_to="advanced_lateral",
                   enabled=lambda: self._params.get_bool("AdvancedLateralTune"),
                   disabled_label=tr_noop("Enable First")),
      ], tab_key="tune"),
      SettingSection(tr_noop("Lateral Tuning"), [
        SettingRow("LateralTune", "toggle", tr_noop("Lateral Tuning"),
                   subtitle=tr_noop("Miscellaneous steering control changes such as turn desires and NNFF modes."),
                   get_state=lambda: self._params.get_bool("LateralTune"),
                   set_state=lambda s: self._params.put_bool("LateralTune", s)),
        SettingRow("TurnDesires", "toggle", tr_noop("Force Turn Desires Below Lane Change Speed"),
                   subtitle=tr_noop("Allow openpilot to follow turn intent below the minimum lane change speed when signaling."),
                   get_state=lambda: self._params.get_bool("TurnDesires"),
                   set_state=lambda s: self._params.put_bool("TurnDesires", s),
                   visible=lambda: self._params.get_bool("LateralTune")),
        SettingRow("NavDesiresAllowed", "toggle", tr_noop("Use Route Desires"),
                   subtitle=tr_noop("Allow an active navigation route to request keep-left, keep-right, and low-speed turn desires."),
                   get_state=lambda: self._params.get_bool("NavDesiresAllowed"),
                   set_state=lambda s: self._params.put_bool("NavDesiresAllowed", s),
                   visible=lambda: self._params.get_bool("LateralTune")),
        SettingRow("NNFF", "toggle", tr_noop("Neural Network Feedforward (NNFF)"),
                   subtitle=tr_noop("Use the full neural-network feedforward steering controller when available."),
                   get_state=lambda: self._params.get_bool("NNFF"),
                   set_state=lambda s: (self._params.put_bool("NNFF", s), s and self._params.put_bool("NNFFLite", False)),
                   visible=lambda: self._params.get_bool("LateralTune") and starpilot_state.car_state.hasNNFFLog and not starpilot_state.car_state.isAngleCar),
        SettingRow("NNFFLite", "toggle", tr_noop("Neural Network Feedforward (NNFF) Lite"),
                   subtitle=tr_noop("Use the lightweight NNFF steering logic when the full model is off."),
                   get_state=lambda: self._params.get_bool("NNFFLite"),
                   set_state=lambda s: _confirm_reboot_toggle(self._params, "NNFFLite", s),
                   visible=lambda: self._params.get_bool("LateralTune") and not self._params.get_bool("NNFF") and not starpilot_state.car_state.isAngleCar),
      ], tab_key="tune"),
    ]

    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr_noop("Steering"),
      header_subtitle=tr_noop("Fine-tune lateral control, lane changes, and steering behavior."),
      tab_defs=tab_defs,
      panel_style=PANEL_STYLE,
      metrics=COMPACT_PANEL_METRICS,
    )

  def _show_modal_pace_selector(self):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_int("LaneChangeSmoothing", int(val))
    current = self._params.get_int("LaneChangeSmoothing") if self._params.get_int("LaneChangeSmoothing") > 0 else 10
    gui_app.push_widget(AetherSliderDialog(tr("Lane Change Smoothing"), 1, 10, 1, current, on_close, color=PANEL_STYLE.accent))
