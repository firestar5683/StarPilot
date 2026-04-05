from __future__ import annotations
from pathlib import Path

from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.hardware import HARDWARE
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
from openpilot.system.ui.widgets.selection_dialog import SelectionDialog
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import StarPilotPanel
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import AetherSliderDialog


class StarPilotDeviceLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {"title": tr_noop("Screen Settings"), "panel": "screen", "icon": "toggle_icons/icon_light.png", "color": "#D43D8A"},
      {"title": tr_noop("Device Settings"), "panel": "device_settings", "icon": "toggle_icons/icon_device.png", "color": "#D43D8A"},
      {
        "title": tr_noop("Device Shutdown"),
        "type": "value",
        "get_value": self._get_shutdown_timer,
        "on_click": self._show_shutdown_selector,
        "color": "#D43D8A",
      },
      {
        "title": tr_noop("Disable Logging"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("NoLogging"),
        "set_state": lambda s: self._params.put_bool("NoLogging", s),
        "color": "#D43D8A",
      },
      {
        "title": tr_noop("Disable Uploads"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("NoUploads"),
        "set_state": lambda s: self._params.put_bool("NoUploads", s),
        "color": "#D43D8A",
      },
      {
        "title": tr_noop("Disable Onroad Uploads"),
        "type": "toggle",
        "param": "DisableOnroadUploads",
        "get_state": lambda: self._params.get_bool("DisableOnroadUploads"),
        "set_state": lambda s: self._params.put_bool("DisableOnroadUploads", s),
        "color": "#D43D8A",
      },
      {
        "title": tr_noop("High-Quality Recording"),
        "type": "toggle",
        "param": "HigherBitrate",
        "get_state": lambda: self._params.get_bool("HigherBitrate"),
        "set_state": lambda s: self._on_higher_bitrate_toggle(s),
        "color": "#D43D8A",
      },
    ]

    self._sub_panels = {
      "screen": StarPilotScreenLayout(),
      "device_settings": StarPilotDeviceManagementLayout(),
    }

    for name, panel in self._sub_panels.items():
      if hasattr(panel, 'set_navigate_callback'):
        panel.set_navigate_callback(self._navigate_to)
      if hasattr(panel, 'set_back_callback'):
        panel.set_back_callback(self._go_back)

    self._rebuild_grid()

  def _rebuild_grid(self):
    no_uploads = self._params.get_bool("NoUploads")
    disable_onroad = self._params.get_bool("DisableOnroadUploads")
    filtered = []
    for cat in self.CATEGORIES:
      param = cat.get("param")
      if param == "DisableOnroadUploads" and not no_uploads:
        continue
      if param == "HigherBitrate" and (not no_uploads or disable_onroad):
        continue
      filtered.append(cat)
    original = self.CATEGORIES
    self.CATEGORIES = filtered
    super()._rebuild_grid()
    self.CATEGORIES = original

  def _on_higher_bitrate_toggle(self, state):
    self._params.put_bool("HigherBitrate", state)
    cache_path = Path("/cache/use_HD")
    if state:
      cache_path.parent.mkdir(parents=True, exist_ok=True)
      cache_path.touch()
    else:
      if cache_path.exists():
        cache_path.unlink()
    if ui_state.started:
      gui_app.set_modal_overlay(
        ConfirmDialog(
          tr("Reboot required. Reboot now?"), tr("Reboot"), tr("Cancel"), on_close=lambda res: HARDWARE.reboot() if res == DialogResult.CONFIRM else None
        )
      )

  def _get_shutdown_timer(self):
    v = self._params.get_int("DeviceShutdown")
    if v == 0:
      return tr("5 mins")
    if v <= 3:
      return f"{v * 15} mins"
    return f"{v - 3} " + (tr("hour") if v == 4 else tr("hours"))

  def _show_shutdown_selector(self):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_int("DeviceShutdown", int(val))
        self._rebuild_grid()

    labels = {0: tr("5 mins")}
    for i in range(1, 4):
      labels[i] = f"{i * 15} mins"
    for i in range(4, 34):
      labels[i] = f"{i - 3} " + (tr("hour") if i == 4 else tr("hours"))

    gui_app.set_modal_overlay(AetherSliderDialog(tr("Device Shutdown"), 0, 33, 1, self._params.get_int("DeviceShutdown"), on_close, labels=labels, color="#D43D8A"))


class StarPilotScreenLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {
        "title": tr_noop("Brightness (Offroad)"),
        "type": "value",
        "get_value": lambda: self._get_brightness("ScreenBrightness"),
        "on_click": lambda: self._show_brightness_selector("ScreenBrightness"),
        "color": "#D43D8A",
      },
      {
        "title": tr_noop("Brightness (Onroad)"),
        "type": "value",
        "get_value": lambda: self._get_brightness("ScreenBrightnessOnroad"),
        "on_click": lambda: self._show_brightness_selector("ScreenBrightnessOnroad"),
        "color": "#D43D8A",
      },
      {
        "title": tr_noop("Timeout (Offroad)"),
        "type": "value",
        "get_value": lambda: f"{self._params.get_int('ScreenTimeout')}s",
        "on_click": lambda: self._show_timeout_selector("ScreenTimeout"),
        "color": "#D43D8A",
      },
      {
        "title": tr_noop("Timeout (Onroad)"),
        "type": "value",
        "get_value": lambda: f"{self._params.get_int('ScreenTimeoutOnroad')}s",
        "on_click": lambda: self._show_timeout_selector("ScreenTimeoutOnroad"),
        "color": "#D43D8A",
      },
      {
        "title": tr_noop("Standby Mode"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("StandbyMode"),
        "set_state": lambda s: self._params.put_bool("StandbyMode", s),
        "color": "#D43D8A",
      },
    ]
    self._rebuild_grid()

  def _get_brightness(self, key):
    v = self._params.get_int(key)
    if key == "ScreenBrightnessOnroad" and v == 0:
      v = 1
    if v == 0:
      return tr("Off")
    if v == 101:
      return tr("Auto")
    return f"{v}%"

  def _show_brightness_selector(self, key):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        new_v = int(val)
        if key == "ScreenBrightnessOnroad":
          new_v = max(new_v, 1)
        self._params.put_int(key, new_v)
        HARDWARE.set_brightness(new_v)
        self._rebuild_grid()

    min_value = 1 if key == "ScreenBrightnessOnroad" else 0
    current_value = max(self._params.get_int(key), min_value)
    labels = {101: tr("Auto")}
    if min_value == 0:
      labels[0] = tr("Off")

    gui_app.set_modal_overlay(
      AetherSliderDialog(tr(key), min_value, 101, 1, current_value, on_close, unit="%", labels=labels, color="#D43D8A")
    )

  def _show_timeout_selector(self, key):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_int(key, int(val))
        self._rebuild_grid()

    gui_app.set_modal_overlay(AetherSliderDialog(tr(key), 5, 60, 5, self._params.get_int(key), on_close, unit="s", color="#D43D8A"))


class StarPilotDeviceManagementLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {
        "title": tr_noop("Low-Voltage Cutoff"),
        "type": "value",
        "get_value": lambda: f"{self._params.get_float('LowVoltageShutdown'):.1f}V",
        "on_click": self._show_voltage_selector,
        "color": "#D43D8A",
      },
      {
        "title": tr_noop("Raise Temp Limits"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("IncreaseThermalLimits"),
        "set_state": lambda s: self._params.put_bool("IncreaseThermalLimits", s),
        "color": "#D43D8A",
      },
      {
        "title": tr_noop("Use Konik Server"),
        "type": "toggle",
        "get_state": lambda: self._get_konik_state(),
        "set_state": lambda s: self._on_konik_toggle(s),
        "color": "#D43D8A",
      },
    ]
    self._rebuild_grid()

  def _get_konik_state(self):
    if Path("/data/not_vetted").exists():
      return True
    return self._params.get_bool("UseKonikServer")

  def _on_konik_toggle(self, state):
    self._params.put_bool("UseKonikServer", state)
    cache_path = Path("/cache/use_konik")
    if state:
      cache_path.parent.mkdir(parents=True, exist_ok=True)
      cache_path.touch()
    else:
      if cache_path.exists():
        cache_path.unlink()
    if ui_state.started:
      gui_app.set_modal_overlay(
        ConfirmDialog(
          tr("Reboot required. Reboot now?"), tr("Reboot"), tr("Cancel"), on_close=lambda res: HARDWARE.reboot() if res == DialogResult.CONFIRM else None
        )
      )

  def _show_voltage_selector(self):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_float("LowVoltageShutdown", float(val))
        self._rebuild_grid()

    gui_app.set_modal_overlay(
      AetherSliderDialog(tr("Low-Voltage Cutoff"), 11.8, 12.5, 0.1, self._params.get_float("LowVoltageShutdown"), on_close, unit="V", color="#D43D8A")
    )
