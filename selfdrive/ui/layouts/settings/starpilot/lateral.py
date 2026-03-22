from __future__ import annotations
from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
from openpilot.system.ui.widgets.selection_dialog import SelectionDialog
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import StarPilotPanel
from openpilot.selfdrive.ui.layouts.settings.starpilot.metro import SliderDialog

class StarPilotAdvancedLateralLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {"title": tr_noop("Actuator Delay"), "type": "value", "get_value": lambda: f"{self._params.get_float('SteerDelay'):.2f}s", "on_click": lambda: self._show_float_selector("SteerDelay", 0.0, 0.5, 0.01, "s"), "icon": "toggle_icons/icon_advanced_lateral_tune.png", "color": "#1BA1E2"},
      {"title": tr_noop("Friction"), "type": "value", "get_value": lambda: f"{self._params.get_float('SteerFriction'):.3f}", "on_click": lambda: self._show_float_selector("SteerFriction", 0.0, 0.5, 0.005), "icon": "toggle_icons/icon_advanced_lateral_tune.png", "color": "#1BA1E2"},
      {"title": tr_noop("Kp Factor"), "type": "value", "get_value": lambda: f"{self._params.get_float('SteerKP'):.2f}", "on_click": lambda: self._show_float_selector("SteerKP", 0.5, 2.5, 0.01), "icon": "toggle_icons/icon_advanced_lateral_tune.png", "color": "#1BA1E2"},
      {"title": tr_noop("Lateral Accel"), "type": "value", "get_value": lambda: f"{self._params.get_float('SteerLatAccel'):.2f}", "on_click": lambda: self._show_float_selector("SteerLatAccel", 0.5, 5.0, 0.01), "icon": "toggle_icons/icon_advanced_lateral_tune.png", "color": "#1BA1E2"},
      {"title": tr_noop("Steer Ratio"), "type": "value", "get_value": lambda: f"{self._params.get_float('SteerRatio'):.2f}", "on_click": lambda: self._show_float_selector("SteerRatio", 5.0, 25.0, 0.01), "icon": "toggle_icons/icon_advanced_lateral_tune.png", "color": "#1BA1E2"},
      {"title": tr_noop("Force Auto-Tune On"), "type": "toggle", "get_state": lambda: self._params.get_bool("ForceAutoTune"), "set_state": lambda x: self._params.put_bool("ForceAutoTune", x), "icon": "toggle_icons/icon_tuning.png", "color": "#1BA1E2"},
      {"title": tr_noop("Force Auto-Tune Off"), "type": "toggle", "get_state": lambda: self._params.get_bool("ForceAutoTuneOff"), "set_state": lambda x: self._params.put_bool("ForceAutoTuneOff", x), "icon": "toggle_icons/icon_tuning.png", "color": "#1BA1E2"},
      {"title": tr_noop("Force Torque Controller"), "type": "toggle", "get_state": lambda: self._params.get_bool("ForceTorqueController"), "set_state": lambda x: self._on_reboot_toggle("ForceTorqueController", x), "icon": "toggle_icons/icon_advanced_lateral_tune.png", "color": "#1BA1E2"},
    ]
    self._rebuild_grid()

  def _show_float_selector(self, key, min_v, max_v, step, unit=""):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_float(key, float(val))
        self._rebuild_grid()
    gui_app.set_modal_overlay(SliderDialog(tr(key), min_v, max_v, step, self._params.get_float(key), on_close, unit=unit, color="#1BA1E2"))

  def _on_reboot_toggle(self, key, state):
    self._params.put_bool(key, state)
    from openpilot.selfdrive.ui.ui_state import ui_state
    if ui_state.started:
      dialog = ConfirmDialog(tr("Reboot required. Reboot now?"), tr("Reboot"), tr("Cancel"), on_close=lambda res: HARDWARE.reboot() if res == DialogResult.CONFIRM else None)
      gui_app.set_modal_overlay(dialog)

class StarPilotAlwaysOnLateralLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {"title": tr_noop("Always On Lateral"), "type": "toggle", "get_state": lambda: self._params.get_bool("AlwaysOnLateral"), "set_state": lambda x: self._on_reboot_toggle("AlwaysOnLateral", x), "icon": "toggle_icons/icon_always_on_lateral.png", "color": "#1BA1E2"},
      {"title": tr_noop("Enable With LKAS"), "type": "toggle", "get_state": lambda: self._params.get_bool("AlwaysOnLateralLKAS"), "set_state": lambda x: self._params.put_bool("AlwaysOnLateralLKAS", x), "icon": "toggle_icons/icon_always_on_lateral.png", "color": "#1BA1E2"},
      {"title": tr_noop("Pause Below"), "type": "value", "get_value": lambda: f"{self._params.get_int('PauseAOLOnBrake')} mph", "on_click": lambda: self._show_speed_selector("PauseAOLOnBrake"), "icon": "toggle_icons/icon_always_on_lateral.png", "color": "#1BA1E2"},
    ]
    self._rebuild_grid()

  def _show_speed_selector(self, key):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_int(key, int(val))
        self._rebuild_grid()
    gui_app.set_modal_overlay(SliderDialog(tr(key), 0, 100, 1, self._params.get_int(key), on_close, unit=" mph", color="#1BA1E2"))

  def _on_reboot_toggle(self, key, state):
    self._params.put_bool(key, state)
    from openpilot.selfdrive.ui.ui_state import ui_state
    if ui_state.started:
      gui_app.set_modal_overlay(ConfirmDialog(tr("Reboot required. Reboot now?"), tr("Reboot"), tr("Cancel"), on_close=lambda res: HARDWARE.reboot() if res == DialogResult.CONFIRM else None))

class StarPilotLaneChangesLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {"title": tr_noop("Lane Changes"), "type": "toggle", "get_state": lambda: self._params.get_bool("LaneChanges"), "set_state": lambda s: self._params.put_bool("LaneChanges", s), "icon": "toggle_icons/icon_lane.png", "color": "#1BA1E2"},
      {"title": tr_noop("Automatic Lane Changes"), "type": "toggle", "get_state": lambda: self._params.get_bool("NudgelessLaneChange"), "set_state": lambda s: self._params.put_bool("NudgelessLaneChange", s), "icon": "toggle_icons/icon_lane.png", "color": "#1BA1E2"},
      {"title": tr_noop("Lane Change Delay"), "type": "value", "get_value": lambda: f"{self._params.get_float('LaneChangeTime'):.1f}s", "on_click": lambda: self._show_float_selector("LaneChangeTime", 0.0, 5.0, 0.1, "s"), "icon": "toggle_icons/icon_lane.png", "color": "#1BA1E2"},
      {"title": tr_noop("Min Lane Change Speed"), "type": "value", "get_value": lambda: f"{self._params.get_int('MinimumLaneChangeSpeed')} mph", "on_click": lambda: self._show_speed_selector("MinimumLaneChangeSpeed"), "icon": "toggle_icons/icon_lane.png", "color": "#1BA1E2"},
      {"title": tr_noop("Minimum Lane Width"), "type": "value", "get_value": lambda: f"{self._params.get_float('LaneDetectionWidth'):.1f} ft", "on_click": lambda: self._show_float_selector("LaneDetectionWidth", 0.0, 15.0, 0.1, " ft"), "icon": "toggle_icons/icon_lane.png", "color": "#1BA1E2"},
      {"title": tr_noop("One Lane Change Per Signal"), "type": "toggle", "get_state": lambda: self._params.get_bool("OneLaneChange"), "set_state": lambda s: self._params.put_bool("OneLaneChange", s), "icon": "toggle_icons/icon_lane.png", "color": "#1BA1E2"},
    ]
    self._rebuild_grid()

  def _show_speed_selector(self, key):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_int(key, int(val))
        self._rebuild_grid()
    gui_app.set_modal_overlay(SliderDialog(tr(key), 0, 100, 1, self._params.get_int(key), on_close, unit=" mph", color="#1BA1E2"))

  def _show_float_selector(self, key, min_v, max_v, step, unit=""):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_float(key, float(val))
        self._rebuild_grid()
    gui_app.set_modal_overlay(SliderDialog(tr(key), min_v, max_v, step, self._params.get_float(key), on_close, unit=unit, color="#1BA1E2"))

class StarPilotLateralTuneLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {"title": tr_noop("Force Turn Desires"), "type": "toggle", "get_state": lambda: self._params.get_bool("TurnDesires"), "set_state": lambda x: self._params.put_bool("TurnDesires", x), "icon": "toggle_icons/icon_lateral_tune.png", "color": "#1BA1E2"},
      {"title": tr_noop("NNFF"), "type": "toggle", "get_state": lambda: self._params.get_bool("NNFF"), "set_state": lambda x: self._on_reboot_toggle("NNFF", x), "icon": "toggle_icons/icon_lateral_tune.png", "color": "#1BA1E2"},
      {"title": tr_noop("NNFF Lite"), "type": "toggle", "get_state": lambda: self._params.get_bool("NNFFLite"), "set_state": lambda x: self._on_reboot_toggle("NNFFLite", x), "icon": "toggle_icons/icon_lateral_tune.png", "color": "#1BA1E2"},
    ]
    self._rebuild_grid()

  def _on_reboot_toggle(self, key, state):
    self._params.put_bool(key, state)
    from openpilot.selfdrive.ui.ui_state import ui_state
    if ui_state.started:
      gui_app.set_modal_overlay(ConfirmDialog(tr("Reboot required. Reboot now?"), tr("Reboot"), tr("Cancel"), on_close=lambda res: HARDWARE.reboot() if res == DialogResult.CONFIRM else None))

class StarPilotLateralQOLLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {"title": tr_noop("Pause Steering Below"), "type": "value", "get_value": lambda: f"{self._params.get_int('PauseLateralSpeed')} mph", "on_click": lambda: self._show_speed_selector("PauseLateralSpeed"), "icon": "toggle_icons/icon_quality_of_life.png", "color": "#1BA1E2"}
    ]
    self._rebuild_grid()

  def _show_speed_selector(self, key):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_int(key, int(val))
        self._rebuild_grid()
    gui_app.set_modal_overlay(SliderDialog(tr(key), 0, 100, 1, self._params.get_int(key), on_close, unit=" mph", color="#1BA1E2"))

class StarPilotLateralLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self._sub_panels = {
      "advanced_lateral": StarPilotAdvancedLateralLayout(),
      "always_on_lateral": StarPilotAlwaysOnLateralLayout(),
      "lane_changes": StarPilotLaneChangesLayout(),
      "lateral_tune": StarPilotLateralTuneLayout(),
      "qol": StarPilotLateralQOLLayout(),
    }
    self.CATEGORIES = [
      {"title": tr_noop("Advanced Lateral Tuning"), "panel": "advanced_lateral", "icon": "toggle_icons/icon_advanced_lateral_tune.png", "color": "#1BA1E2"},
      {"title": tr_noop("Always On Lateral"), "panel": "always_on_lateral", "icon": "toggle_icons/icon_always_on_lateral.png", "color": "#1BA1E2"},
      {"title": tr_noop("Lane Changes"), "panel": "lane_changes", "icon": "toggle_icons/icon_lane.png", "color": "#1BA1E2"},
      {"title": tr_noop("Lateral Tuning"), "panel": "lateral_tune", "icon": "toggle_icons/icon_lateral_tune.png", "color": "#1BA1E2"},
      {"title": tr_noop("Quality of Life"), "panel": "qol", "icon": "toggle_icons/icon_quality_of_life.png", "color": "#1BA1E2"},
    ]
    for name, panel in self._sub_panels.items():
      if hasattr(panel, 'set_navigate_callback'): panel.set_navigate_callback(self._navigate_to)
      if hasattr(panel, 'set_back_callback'): panel.set_back_callback(self._go_back)
    self._rebuild_grid()
