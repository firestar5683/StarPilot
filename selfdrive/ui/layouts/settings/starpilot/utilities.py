from __future__ import annotations
import json
from openpilot.system.hardware import HARDWARE
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog, alert_dialog
from openpilot.system.ui.widgets.selection_dialog import SelectionDialog
from openpilot.system.ui.widgets.input_dialog import InputDialog
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import StarPilotPanel

EXCLUDED_KEYS = {
  "AvailableModels",
  "AvailableModelNames",
  "FrogPilotStats",
  "GithubSshKeys",
  "GithubUsername",
  "MapBoxRequests",
  "ModelDrivesAndScores",
  "OverpassRequests",
  "SpeedLimits",
  "SpeedLimitsFiltered",
  "UpdaterAvailableBranches",
}

REPORT_CATEGORIES = [
  "Acceleration feels harsh or jerky",
  "An alert was unclear and I'm not sure what it meant",
  "Braking is too sudden or uncomfortable",
  "I'm not sure if this is normal or a bug:",
  "My steering wheel buttons aren't working",
  "openpilot disengages when I don't expect it",
  "openpilot feels sluggish or slow to respond",
  "Something else (please describe)",
]


class StarPilotUtilitiesLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {
        "title": tr_noop("Debug Mode"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("DebugMode"),
        "set_state": lambda s: self._params.put_bool("DebugMode", s),
        "color": "#FA6800",
      },
      {"title": tr_noop("Flash Panda"), "type": "hub", "on_click": self._on_flash_panda, "color": "#FA6800"},
      {
        "title": tr_noop("Force Drive State"),
        "type": "value",
        "get_value": self._get_force_drive_state,
        "on_click": self._on_force_drive_state,
        "color": "#FA6800",
      },
      {
        "title": tr_noop("The Pond"),
        "type": "value",
        "get_value": lambda: tr("Paired") if self._params.get_bool("PondPaired") else tr("Not paired"),
        "on_click": self._on_pond_clicked,
        "color": "#FA6800",
      },
      {"title": tr_noop("Report Issue"), "type": "hub", "on_click": self._on_report_issue, "color": "#FA6800"},
      {"title": tr_noop("Reset to Defaults"), "type": "hub", "on_click": self._on_reset_defaults, "color": "#FA6800"},
      {"title": tr_noop("Reset to Stock"), "type": "hub", "on_click": self._on_reset_stock, "color": "#FA6800"},
    ]
    self._rebuild_grid()

  def _get_force_drive_state(self):
    if self._params.get_bool("ForceOnroad"):
      return tr("Onroad")
    if self._params.get_bool("ForceOffroad"):
      return tr("Offroad")
    return tr("Default")

  def _on_flash_panda(self):
    def _do_flash(res):
      if res == DialogResult.CONFIRM:
        self._params_memory.put_bool("FlashPanda", True)
        gui_app.set_modal_overlay(alert_dialog(tr("Panda flashing started. Device will reboot when finished.")))

    gui_app.set_modal_overlay(ConfirmDialog(tr("Flash Panda firmware?"), tr("Flash"), on_close=_do_flash))

  def _on_force_drive_state(self):
    options = [tr("Offroad"), tr("Onroad"), tr("Default")]

    def on_select(res, val):
      if res == DialogResult.CONFIRM:
        if val == tr("Offroad"):
          self._params.put_bool("ForceOffroad", True)
          self._params.put_bool("ForceOnroad", False)
        elif val == tr("Onroad"):
          self._params.put_bool("ForceOnroad", True)
          self._params.put_bool("ForceOffroad", False)
        else:
          self._params.put_bool("ForceOffroad", False)
          self._params.put_bool("ForceOnroad", False)
        self._rebuild_grid()

    current = self._get_force_drive_state()
    gui_app.set_modal_overlay(SelectionDialog(tr("Force Drive State"), options, current, on_close=on_select))

  def _on_pond_clicked(self):
    paired = self._params.get_bool("PondPaired")
    if paired:

      def on_unpair(res):
        if res == DialogResult.CONFIRM:
          self._params.put_bool("PondPaired", False)
          gui_app.set_modal_overlay(alert_dialog(tr("Unpaired from The Pond.")))
          self._rebuild_grid()

      gui_app.set_modal_overlay(ConfirmDialog(tr("Unpair from The Pond?"), tr("Unpair"), on_close=on_unpair))
    else:
      gui_app.set_modal_overlay(alert_dialog(tr("Visit frogpilot.com/the_pond to pair your device.")))

  def _on_report_issue(self):
    def on_category(res, val):
      if res != DialogResult.CONFIRM:
        return
      discord_user = self._params.get("DiscordUsername", encoding='utf-8') or ""

      def on_discord(res2, username):
        if res2 == DialogResult.CONFIRM and username:
          self._params.put("DiscordUsername", username)
          report = json.dumps({"DiscordUser": username, "Issue": val})
          self._params_memory.put("IssueReported", report)
          gui_app.set_modal_overlay(alert_dialog(tr("Issue reported. Thank you!")))

      gui_app.set_modal_overlay(InputDialog(tr("Discord Username"), discord_user or "", on_close=on_discord))

    gui_app.set_modal_overlay(SelectionDialog(tr("Select Issue"), REPORT_CATEGORIES, on_close=on_category))

  def _on_reset_defaults(self):
    def _do_reset(res):
      if res == DialogResult.CONFIRM:
        all_keys = self._params.all_keys()
        for k in all_keys:
          if k in EXCLUDED_KEYS:
            continue
          default = self._params.get_default_value(k)
          if default is not None:
            self._params.put(k, default)
        gui_app.set_modal_overlay(alert_dialog(tr("Toggles reset to defaults.")))
        self._rebuild_grid()

    gui_app.set_modal_overlay(ConfirmDialog(tr("Reset all toggles to defaults?"), tr("Reset"), on_close=_do_reset))

  def _on_reset_stock(self):
    def _do_reset(res):
      if res == DialogResult.CONFIRM:
        all_keys = self._params.all_keys()
        for k in all_keys:
          if k in EXCLUDED_KEYS:
            continue
          stock = self._params.get_stock_value(k)
          if stock is not None:
            self._params.put(k, stock)
        gui_app.set_modal_overlay(alert_dialog(tr("Toggles reset to stock openpilot.")))
        self._rebuild_grid()

    gui_app.set_modal_overlay(ConfirmDialog(tr("Reset all toggles to stock openpilot?"), tr("Reset"), on_close=_do_reset))
