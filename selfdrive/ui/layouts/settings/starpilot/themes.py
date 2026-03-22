from __future__ import annotations
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.selection_dialog import SelectionDialog
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import StarPilotPanel


class StarPilotThemesLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()

    self._sub_panels = {
      "personalize": StarPilotPersonalizeLayout(),
    }

    self.CATEGORIES = [
      {
        "title": tr_noop("Personalize openpilot"),
        "panel": "personalize",
        "icon": "toggle_icons/icon_frog.png",
        "color": "#A200FF",
        "desc": tr_noop("Customize the overall look and feel."),
      },
      {
        "title": tr_noop("Holiday Themes"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("HolidayThemes"),
        "set_state": lambda s: self._params.put_bool("HolidayThemes", s),
        "icon": "toggle_icons/icon_calendar.png",
        "color": "#A200FF",
      },
      {
        "title": tr_noop("Rainbow Path"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("RainbowPath"),
        "set_state": lambda s: self._params.put_bool("RainbowPath", s),
        "icon": "toggle_icons/icon_rainbow.png",
        "color": "#A200FF",
      },
      {
        "title": tr_noop("Random Events"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("RandomEvents"),
        "set_state": lambda s: self._params.put_bool("RandomEvents", s),
        "icon": "toggle_icons/icon_random.png",
        "color": "#A200FF",
      },
      {
        "title": tr_noop("Random Themes"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("RandomThemes"),
        "set_state": lambda s: self._params.put_bool("RandomThemes", s),
        "icon": "toggle_icons/icon_random_themes.png",
        "color": "#A200FF",
      },
      {"title": tr_noop("Startup Alert"), "type": "hub", "on_click": self._on_startup_alert, "color": "#A200FF"},
    ]

    for name, panel in self._sub_panels.items():
      if hasattr(panel, 'set_navigate_callback'):
        panel.set_navigate_callback(self._navigate_to)
      if hasattr(panel, 'set_back_callback'):
        panel.set_back_callback(self._go_back)

    self._rebuild_grid()

  def _on_startup_alert(self):
    options = ["Stock", "FrogPilot", "Clear"]
    current_top = self._params.get("StartupMessageTop", encoding='utf-8') or ""
    if current_top == "Be ready to take over at any time":
      current = "Stock"
    elif current_top == "Hop in and buckle up!":
      current = "FrogPilot"
    else:
      current = "Clear"

    def on_select(res, val):
      if res == DialogResult.CONFIRM:
        if val == "Stock":
          self._params.put("StartupMessageTop", "Be ready to take over at any time")
          self._params.put("StartupMessageBottom", "Always keep hands on wheel and eyes on road")
        elif val == "FrogPilot":
          self._params.put("StartupMessageTop", "Hop in and buckle up!")
          self._params.put("StartupMessageBottom", "Human-tested, frog-approved")
        else:
          self._params.remove("StartupMessageTop")
          self._params.remove("StartupMessageBottom")

    gui_app.set_modal_overlay(SelectionDialog(tr("Startup Alert"), options, current, on_close=on_select))


class StarPilotPersonalizeLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {
        "title": tr_noop("Boot Logo"),
        "type": "value",
        "get_value": lambda: self._params.get("BootLogo", encoding='utf-8') or "Stock",
        "on_click": lambda: self._show_theme_selector("BootLogo"),
        "color": "#A200FF",
      },
      {
        "title": tr_noop("Color Scheme"),
        "type": "value",
        "get_value": lambda: self._params.get("ColorScheme", encoding='utf-8') or "Stock",
        "on_click": lambda: self._show_theme_selector("ColorScheme"),
        "color": "#A200FF",
      },
      {
        "title": tr_noop("Distance Icons"),
        "type": "value",
        "get_value": lambda: self._params.get("DistanceIconPack", encoding='utf-8') or "Stock",
        "on_click": lambda: self._show_theme_selector("DistanceIconPack"),
        "color": "#A200FF",
      },
      {
        "title": tr_noop("Icon Pack"),
        "type": "value",
        "get_value": lambda: self._params.get("IconPack", encoding='utf-8') or "Stock",
        "on_click": lambda: self._show_theme_selector("IconPack"),
        "color": "#A200FF",
      },
      {
        "title": tr_noop("Turn Signals"),
        "type": "value",
        "get_value": lambda: self._params.get("SignalAnimation", encoding='utf-8') or "Stock",
        "on_click": lambda: self._show_theme_selector("SignalAnimation"),
        "color": "#A200FF",
      },
      {
        "title": tr_noop("Sound Pack"),
        "type": "value",
        "get_value": lambda: self._params.get("SoundPack", encoding='utf-8') or "Stock",
        "on_click": lambda: self._show_theme_selector("SoundPack"),
        "color": "#A200FF",
      },
      {
        "title": tr_noop("Steering Wheel"),
        "type": "value",
        "get_value": lambda: self._params.get("WheelIcon", encoding='utf-8') or "Stock",
        "on_click": lambda: self._show_theme_selector("WheelIcon"),
        "color": "#A200FF",
      },
    ]
    self._rebuild_grid()

  def _show_theme_selector(self, key):
    # Ported logic for theme selection. In a real environment we'd scan directories.
    # For now, we'll provide a simplified selection based on current param.
    themes = ["Stock", "Frog", "Cyberpunk", "Minimal"]
    current = self._params.get(key, encoding='utf-8') or "Stock"

    def on_select(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put(key, val)
        self._rebuild_grid()

    gui_app.set_modal_overlay(SelectionDialog(tr(key), themes, current, on_close=on_select))
