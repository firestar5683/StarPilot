from __future__ import annotations
import os
import re
from pathlib import Path

from openpilot.system.hardware import HARDWARE
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
from openpilot.system.ui.widgets.selection_dialog import SelectionDialog
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import StarPilotPanel
from openpilot.selfdrive.ui.layouts.settings.starpilot.metro import SliderDialog, TileGrid, HubTile, ToggleTile, ValueTile
from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state

MAKE_TO_FOLDER = {
  "acura": "honda",
  "audi": "volkswagen",
  "buick": "gm",
  "cadillac": "gm",
  "chevrolet": "gm",
  "chrysler": "chrysler",
  "cupra": "volkswagen",
  "dodge": "chrysler",
  "ford": "ford",
  "genesis": "hyundai",
  "gmc": "gm",
  "holden": "gm",
  "honda": "honda",
  "hyundai": "hyundai",
  "jeep": "chrysler",
  "kia": "hyundai",
  "lexus": "toyota",
  "lincoln": "ford",
  "man": "volkswagen",
  "mazda": "mazda",
  "nissan": "nissan",
  "peugeot": "psa",
  "ram": "chrysler",
  "rivian": "rivian",
  "seat": "volkswagen",
  "škoda": "volkswagen",
  "subaru": "subaru",
  "tesla": "tesla",
  "toyota": "toyota",
  "volkswagen": "volkswagen",
}


def get_car_names(car_make: str):
  folder = MAKE_TO_FOLDER.get(car_make.lower())
  if not folder:
    return [], {}

  # Path to values.py in opendbc
  values_path = Path(__file__).parents[4] / "opendbc" / "car" / folder / "values.py"
  if not values_path.exists():
    return [], {}

  with open(values_path, "r") as f:
    content = f.read()

  # Clean comments
  content = re.sub(r'#.*', '', content)

  # Find platforms and car names
  platforms = re.findall(r'(\w+)\s*=\s*\w+\s*\(', content)
  car_models = {}
  car_names = []

  # This is a simplified version of the C++ regex logic
  # In values.py, CarDocs often appears as CarDocs("Name", ...)
  matches = re.finditer(r'CarDocs\w*\s*\(\s*"([^"]+)"', content)
  for match in matches:
    name = match.group(1)
    if name.lower().startswith(car_make.lower()):
      # Find the platform name by looking backwards for the nearest platform assignment
      # For now, we'll just store the name
      car_names.append(name)

  return sorted(list(set(car_names))), car_models


def _lock_doors_timer_labels():
  labels: dict[float, str] = {0.0: tr("Never")}
  for i in range(5, 305, 5):
    labels[float(i)] = f"{i}s"
  return labels


class StarPilotVehicleSettingsLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self._sub_panels = {
      "gm": StarPilotGMVehicleLayout(),
      "hkg": StarPilotHKGVehicleLayout(),
      "subaru": StarPilotSubaruVehicleLayout(),
      "toyota": StarPilotToyotaVehicleLayout(),
      "info": StarPilotVehicleInfoLayout(),
    }

    self.CATEGORIES = [
      {
        "title": tr_noop("Car Make"),
        "type": "value",
        "get_value": lambda: self._params.get("CarMake", encoding='utf-8') or tr("None"),
        "on_click": self._on_select_make,
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Car Model"),
        "type": "value",
        "get_value": lambda: self._params.get("CarModelName", encoding='utf-8') or tr("None"),
        "on_click": self._on_select_model,
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Disable Fingerprinting"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("ForceFingerprint"),
        "set_state": lambda s: self._params.put_bool("ForceFingerprint", s),
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Disable openpilot Long"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("DisableOpenpilotLongitudinal"),
        "set_state": self._on_disable_long,
        "color": "#FFC40D",
      },
      {"title": tr_noop("GM Settings"), "panel": "gm", "icon": "toggle_icons/icon_vehicle.png", "color": "#FFC40D", "key": "gm"},
      {"title": tr_noop("HKG Settings"), "panel": "hkg", "icon": "toggle_icons/icon_vehicle.png", "color": "#FFC40D", "key": "hkg"},
      {"title": tr_noop("Subaru Settings"), "panel": "subaru", "icon": "toggle_icons/icon_vehicle.png", "color": "#FFC40D", "key": "subaru"},
      {"title": tr_noop("Toyota Settings"), "panel": "toyota", "icon": "toggle_icons/icon_vehicle.png", "color": "#FFC40D", "key": "toyota"},
      {"title": tr_noop("Vehicle Info"), "panel": "info", "icon": "toggle_icons/icon_vehicle.png", "color": "#FFC40D"},
    ]

    for name, panel in self._sub_panels.items():
      if hasattr(panel, 'set_navigate_callback'):
        panel.set_navigate_callback(self._navigate_to)
      if hasattr(panel, 'set_back_callback'):
        panel.set_back_callback(self._go_back)

    self._rebuild_grid()

  def _rebuild_grid(self):
    if not self.CATEGORIES:
      return
    if self._tile_grid is None:
      self._tile_grid = TileGrid(columns=None, padding=20)
    self._tile_grid.clear()

    cs = starpilot_state.car_state
    for cat in self.CATEGORIES:
      key = cat.get("key")
      visible = True

      if key == "gm":
        visible = cs.isGM
      elif key == "hkg":
        visible = cs.isHKG
      elif key == "subaru":
        visible = cs.isSubaru
      elif key == "toyota":
        visible = cs.isToyota

      if not visible:
        continue

      tile_type = cat.get("type", "hub")
      if tile_type == "hub":
        on_click = cat.get("on_click")
        if on_click is None:
          on_click = lambda c=cat: self._navigate_to(c["panel"])
        tile = HubTile(
          title=tr(cat["title"]),
          desc=tr(cat.get("desc", "")),
          icon_path=cat.get("icon"),
          on_click=on_click,
          starpilot_icon=cat.get("starpilot_icon", True),
          bg_color=cat.get("color"),
        )
      elif tile_type == "toggle":
        tile = ToggleTile(title=tr(cat["title"]), get_state=cat["get_state"], set_state=cat["set_state"], icon_path=cat.get("icon"), bg_color=cat.get("color"))
      elif tile_type == "value":
        tile = ValueTile(title=tr(cat["title"]), get_value=cat["get_value"], on_click=cat["on_click"], icon_path=cat.get("icon"), bg_color=cat.get("color"))
      else:
        continue

      self._tile_grid.add_tile(tile)

  def _on_select_make(self):
    makes = sorted(list(MAKE_TO_FOLDER.keys()))
    makes = [m.capitalize() for m in makes]

    def on_select(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put("CarMake", val)
        self._params.remove("CarModel")
        self._params.remove("CarModelName")
        self._rebuild_grid()

    gui_app.set_modal_overlay(SelectionDialog(tr("Select Make"), makes, self._params.get("CarMake", encoding='utf-8') or "", on_close=on_select))

  def _on_select_model(self):
    make = self._params.get("CarMake", encoding='utf-8')
    if not make:
      gui_app.set_modal_overlay(ConfirmDialog(tr("Please select a Car Make first!"), tr("OK"), on_close=lambda r: None))
      return

    models, _ = get_car_names(make)
    if not models:
      gui_app.set_modal_overlay(ConfirmDialog(tr("No models found for this make."), tr("OK"), on_close=lambda r: None))
      return

    def on_select(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put("CarModelName", val)
        # In a real build we'd map name to platform code here
        self._rebuild_grid()

    gui_app.set_modal_overlay(SelectionDialog(tr("Select Model"), models, self._params.get("CarModelName", encoding='utf-8') or "", on_close=on_select))

  def _on_disable_long(self, state):
    if state:

      def on_confirm(res):
        if res == DialogResult.CONFIRM:
          self._params.put_bool("DisableOpenpilotLongitudinal", True)
          from openpilot.selfdrive.ui.ui_state import ui_state

          if ui_state.started:
            HARDWARE.reboot()
        self._rebuild_grid()

      gui_app.set_modal_overlay(ConfirmDialog(tr("Disable openpilot longitudinal control?"), tr("Disable"), on_close=on_confirm))
    else:
      self._params.put_bool("DisableOpenpilotLongitudinal", False)
      self._rebuild_grid()


class StarPilotGMVehicleLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {
        "title": tr_noop("Pedal for Long"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("GMPedalLongitudinal"),
        "set_state": lambda s: self._params.put_bool("GMPedalLongitudinal", s),
        "color": "#FFC40D",
        "key": "GMPedalLongitudinal",
      },
      {
        "title": tr_noop("Remote Start Panda"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("RemoteStartBootsComma"),
        "set_state": lambda s: self._params.put_bool("RemoteStartBootsComma", s),
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Volt SNG Hack"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("VoltSNG"),
        "set_state": lambda s: self._params.put_bool("VoltSNG", s),
        "color": "#FFC40D",
        "key": "VoltSNG",
      },
    ]
    self._rebuild_grid()

  def _rebuild_grid(self):
    if not self.CATEGORIES:
      return
    if self._tile_grid is None:
      self._tile_grid = TileGrid(columns=None, padding=20)
    self._tile_grid.clear()

    cs = starpilot_state.car_state
    for cat in self.CATEGORIES:
      key = cat.get("key")
      visible = True

      if key == "GMPedalLongitudinal":
        visible = cs.hasPedal or cs.canUsePedal
      elif key == "VoltSNG":
        visible = cs.isVolt and not cs.hasSNG

      if not visible:
        continue

      tile = ToggleTile(title=tr(cat["title"]), get_state=cat["get_state"], set_state=cat["set_state"], icon_path=cat.get("icon"), bg_color=cat.get("color"))
      self._tile_grid.add_tile(tile)


class StarPilotHKGVehicleLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {
        "title": tr_noop("Taco Bell Torque Hack"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("TacoTuneHacks"),
        "set_state": lambda s: self._params.put_bool("TacoTuneHacks", s),
        "color": "#FFC40D",
        "key": "TacoTuneHacks",
      },
    ]
    self._rebuild_grid()

  def _rebuild_grid(self):
    if not self.CATEGORIES:
      return
    if self._tile_grid is None:
      self._tile_grid = TileGrid(columns=None, padding=20)
    self._tile_grid.clear()

    cs = starpilot_state.car_state
    for cat in self.CATEGORIES:
      key = cat.get("key")
      visible = True

      if key == "TacoTuneHacks":
        visible = cs.isHKGCanFd

      if not visible:
        continue

      tile = ToggleTile(title=tr(cat["title"]), get_state=cat["get_state"], set_state=cat["set_state"], icon_path=cat.get("icon"), bg_color=cat.get("color"))
      self._tile_grid.add_tile(tile)


class StarPilotSubaruVehicleLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {
        "title": tr_noop("Stop and Go"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("SubaruSNG"),
        "set_state": lambda s: self._params.put_bool("SubaruSNG", s),
        "color": "#FFC40D",
      },
    ]
    self._rebuild_grid()


class StarPilotToyotaVehicleLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {
        "title": tr_noop("Auto Lock Doors"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("LockDoors"),
        "set_state": lambda s: self._params.put_bool("LockDoors", s),
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Auto Unlock Doors"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("UnlockDoors"),
        "set_state": lambda s: self._params.put_bool("UnlockDoors", s),
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Lock Doors Timer"),
        "type": "value",
        "get_value": lambda: _lock_doors_timer_labels().get(self._params.get_int('LockDoorsTimer'), f"{self._params.get_int('LockDoorsTimer')}s"),
        "on_click": self._show_lock_timer_selector,
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Dashboard Speed Offset"),
        "type": "value",
        "get_value": lambda: f"{self._params.get_float('ClusterOffset'):.3f}x",
        "on_click": self._show_offset_selector,
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Stop-and-Go Hack"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("SNGHack"),
        "set_state": lambda s: self._params.put_bool("SNGHack", s),
        "color": "#FFC40D",
        "key": "SNGHack",
      },
      {
        "title": tr_noop("FrogsGoMoo Tweak"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("FrogsGoMoosTweak"),
        "set_state": lambda s: self._params.put_bool("FrogsGoMoosTweak", s),
        "color": "#FFC40D",
        "key": "FrogsGoMoosTweak",
      },
    ]
    self._rebuild_grid()

  def _rebuild_grid(self):
    if not self.CATEGORIES:
      return
    if self._tile_grid is None:
      self._tile_grid = TileGrid(columns=None, padding=20)
    self._tile_grid.clear()

    cs = starpilot_state.car_state
    for cat in self.CATEGORIES:
      key = cat.get("key")
      visible = True

      if key == "SNGHack":
        visible = not cs.hasSNG
      elif key == "FrogsGoMoosTweak":
        visible = cs.hasOpenpilotLongitudinal

      if not visible:
        continue

      tile_type = cat.get("type", "hub")
      if tile_type == "toggle":
        tile = ToggleTile(title=tr(cat["title"]), get_state=cat["get_state"], set_state=cat["set_state"], icon_path=cat.get("icon"), bg_color=cat.get("color"))
      elif tile_type == "value":
        tile = ValueTile(title=tr(cat["title"]), get_value=cat["get_value"], on_click=cat["on_click"], icon_path=cat.get("icon"), bg_color=cat.get("color"))
      else:
        continue

      self._tile_grid.add_tile(tile)

  def _show_lock_timer_selector(self):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_int("LockDoorsTimer", int(val))
        self._rebuild_grid()

    gui_app.set_modal_overlay(
      SliderDialog(tr("Lock Doors Timer"), 0, 300, 5, self._params.get_int("LockDoorsTimer"), on_close, labels=_lock_doors_timer_labels(), color="#FFC40D")
    )

  def _show_offset_selector(self):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_float("ClusterOffset", float(val))
        self._rebuild_grid()

    gui_app.set_modal_overlay(
      SliderDialog(tr("Dashboard Speed Offset"), 1.000, 1.050, 0.001, self._params.get_float("ClusterOffset"), on_close, unit="x", color="#FFC40D")
    )


class StarPilotVehicleInfoLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {
        "title": tr_noop("Radar Support"),
        "type": "value",
        "get_value": lambda: tr("Yes") if starpilot_state.car_state.hasRadar else tr("No"),
        "on_click": lambda: None,
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Longitudinal Support"),
        "type": "value",
        "get_value": lambda: tr("Yes") if starpilot_state.car_state.hasOpenpilotLongitudinal else tr("No"),
        "on_click": lambda: None,
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Blind Spot Support"),
        "type": "value",
        "get_value": lambda: tr("Yes") if starpilot_state.car_state.hasBSM else tr("No"),
        "on_click": lambda: None,
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Hardware Detected"),
        "type": "value",
        "get_value": lambda: (
          ", ".join(
            filter(
              None,
              [
                tr("Pedal") if starpilot_state.car_state.canUsePedal else "",
                tr("SDSU") if starpilot_state.car_state.canUseSDSU else "",
                tr("ZSS") if starpilot_state.car_state.hasZSS else "",
              ],
            )
          )
          or tr("None")
        ),
        "on_click": lambda: None,
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Pedal Support"),
        "type": "value",
        "get_value": lambda: tr("Yes") if starpilot_state.car_state.canUsePedal else tr("No"),
        "on_click": lambda: None,
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("SDSU Support"),
        "type": "value",
        "get_value": lambda: tr("Yes") if starpilot_state.car_state.canUseSDSU else tr("No"),
        "on_click": lambda: None,
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("SNG Support"),
        "type": "value",
        "get_value": lambda: tr("Yes") if starpilot_state.car_state.hasSNG else tr("No"),
        "on_click": lambda: None,
        "color": "#FFC40D",
      },
    ]
    self._rebuild_grid()
