from __future__ import annotations
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.selection_dialog import SelectionDialog
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog, alert_dialog
from openpilot.system.ui.widgets.input_dialog import InputDialog
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import StarPilotPanel


class StarPilotNavigationLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self._sub_panels = {
      "mapbox": StarPilotMapboxLayout(),
    }
    self.CATEGORIES = [
      {"title": tr_noop("Mapbox Credentials"), "panel": "mapbox", "icon": "toggle_icons/icon_navigate.png", "color": "#8CBF26"},
      {"title": tr_noop("Setup Instructions"), "type": "hub", "on_click": self._on_setup, "icon": "toggle_icons/icon_navigate.png", "color": "#8CBF26"},
      {
        "title": tr_noop("Speed Limit Filler"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("SpeedLimitFiller"),
        "set_state": lambda s: self._params.put_bool("SpeedLimitFiller", s),
        "icon": "toggle_icons/icon_speed_limit.png",
        "color": "#8CBF26",
      },
      {"title": tr_noop("Search Destination"), "type": "hub", "on_click": self._on_search, "icon": "toggle_icons/icon_navigate.png", "color": "#8CBF26"},
      {
        "title": tr_noop("Home Address"),
        "type": "value",
        "get_value": lambda: self._params.get("HomeAddress", encoding='utf-8') or tr("Not set"),
        "on_click": self._on_home,
        "icon": "toggle_icons/icon_navigate.png",
        "color": "#8CBF26",
      },
      {
        "title": tr_noop("Work Address"),
        "type": "value",
        "get_value": lambda: self._params.get("WorkAddress", encoding='utf-8') or tr("Not set"),
        "on_click": self._on_work,
        "icon": "toggle_icons/icon_navigate.png",
        "color": "#8CBF26",
      },
    ]
    for name, panel in self._sub_panels.items():
      if hasattr(panel, 'set_navigate_callback'):
        panel.set_navigate_callback(self._navigate_to)
      if hasattr(panel, 'set_back_callback'):
        panel.set_back_callback(self._go_back)
    self._rebuild_grid()

  def _on_setup(self):
    gui_app.set_modal_overlay(
      alert_dialog(tr("Mapbox Setup:\n1. Create account at mapbox.com\n2. Generate Public/Secret keys\n3. Add keys in 'Mapbox Credentials'"))
    )

  def _on_search(self):
    def on_close(res, text):
      if res == DialogResult.CONFIRM and text:
        self._params.put("SearchAddress", text)

    gui_app.set_modal_overlay(InputDialog(tr("Search Destination"), "", on_close=on_close))

  def _on_home(self):
    current = self._params.get("HomeAddress", encoding='utf-8') or ""

    def on_close(res, text):
      if res == DialogResult.CONFIRM:
        self._params.put("HomeAddress", text)
        self._rebuild_grid()

    gui_app.set_modal_overlay(InputDialog(tr("Home Address"), current, on_close=on_close))

  def _on_work(self):
    current = self._params.get("WorkAddress", encoding='utf-8') or ""

    def on_close(res, text):
      if res == DialogResult.CONFIRM:
        self._params.put("WorkAddress", text)
        self._rebuild_grid()

    gui_app.set_modal_overlay(InputDialog(tr("Work Address"), current, on_close=on_close))


class StarPilotMapboxLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {
        "title": tr_noop("Public Mapbox Key"),
        "type": "value",
        "get_value": self._get_key_display,
        "on_click": lambda: self._on_key("MapboxPublicKey", "pk."),
        "color": "#8CBF26",
      },
      {
        "title": tr_noop("Secret Mapbox Key"),
        "type": "value",
        "get_value": self._get_secret_display,
        "on_click": lambda: self._on_key("MapboxSecretKey", "sk."),
        "color": "#8CBF26",
      },
    ]
    self._rebuild_grid()

  def _get_key_display(self):
    v = self._params.get("MapboxPublicKey", encoding='utf-8') or ""
    return f"{v[:8]}..." if v else tr("Not set")

  def _get_secret_display(self):
    v = self._params.get("MapboxSecretKey", encoding='utf-8') or ""
    return "********" if v else tr("Not set")

  def _on_key(self, key, prefix):
    current = self._params.get(key, encoding='utf-8') or ""
    if current:

      def on_remove(res):
        if res == DialogResult.CONFIRM:
          self._params.remove(key)
          self._rebuild_grid()

      gui_app.set_modal_overlay(ConfirmDialog(tr(f"Remove your {key.replace('Mapbox', '')} key?"), tr("Remove"), on_close=on_remove))
    else:

      def on_close(res, text):
        if res == DialogResult.CONFIRM and text:
          if not text.startswith(prefix):
            text = prefix + text
          self._params.put(key, text)
          self._rebuild_grid()

      gui_app.set_modal_overlay(InputDialog(tr(f"Enter {key.replace('Mapbox', 'Mapbox ')}"), "", on_close=on_close))
