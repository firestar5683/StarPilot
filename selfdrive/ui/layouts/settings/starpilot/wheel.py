from __future__ import annotations
from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.selection_dialog import SelectionDialog
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import StarPilotPanel

ACTION_NAMES = ["No Action", "Change Personality", "Force Coast", "Pause Steering", "Pause Accel/Brake", "Toggle Experimental", "Toggle Traffic"]
ACTION_IDS = {name: i for i, name in enumerate(ACTION_NAMES)}


class StarPilotWheelLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {
        "title": tr_noop("Remap Cancel Button"),
        "type": "toggle",
        "get_state": lambda: self._params.get_bool("RemapCancelToDistance"),
        "set_state": lambda s: self._params.put_bool("RemapCancelToDistance", s),
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Distance Button"),
        "type": "value",
        "get_value": lambda: self._get_action_name("DistanceButtonControl"),
        "on_click": lambda: self._show_action_picker("DistanceButtonControl"),
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Distance (Long Press)"),
        "type": "value",
        "get_value": lambda: self._get_action_name("LongDistanceButtonControl"),
        "on_click": lambda: self._show_action_picker("LongDistanceButtonControl"),
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("Distance (Very Long)"),
        "type": "value",
        "get_value": lambda: self._get_action_name("VeryLongDistanceButtonControl"),
        "on_click": lambda: self._show_action_picker("VeryLongDistanceButtonControl"),
        "color": "#FFC40D",
      },
      {
        "title": tr_noop("LKAS Button"),
        "type": "value",
        "get_value": lambda: self._get_action_name("LKASButtonControl"),
        "on_click": lambda: self._show_action_picker("LKASButtonControl"),
        "key": "LKASButtonControl",
        "color": "#FFC40D",
      },
    ]
    self._rebuild_grid()

  def _get_action_name(self, key):
    idx = self._params.get_int(key)
    if 0 <= idx < len(ACTION_NAMES):
      return ACTION_NAMES[idx]
    return ACTION_NAMES[0]

  def _get_available_actions(self):
    actions = list(ACTION_NAMES[:1])  # No Action
    cs = starpilot_state.car_state
    if cs.hasOpenpilotLongitudinal:
      actions.extend(ACTION_NAMES[1:])
    return actions

  def _show_action_picker(self, key):
    actions = self._get_available_actions()
    current = self._get_action_name(key)
    if current not in actions:
      current = actions[0]

    def on_select(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_int(key, ACTION_IDS.get(val, 0))
        self._rebuild_grid()

    gui_app.set_modal_overlay(SelectionDialog(tr(key), actions, current, on_close=on_select))

  def _rebuild_grid(self):
    if not self.CATEGORIES:
      return
    if self._tile_grid is None:
      self._tile_grid = __import__('openpilot.selfdrive.ui.layouts.settings.starpilot.metro', fromlist=['TileGrid']).TileGrid(columns=None, padding=20)
    self._tile_grid.clear()
    cs = starpilot_state.car_state
    for cat in self.CATEGORIES:
      key = cat.get("key")
      visible = True
      if key == "LKASButtonControl":
        visible &= not cs.isSubaru
      if not visible:
        continue
      tile_type = cat.get("type", "hub")
      if tile_type == "toggle":
        from openpilot.selfdrive.ui.layouts.settings.starpilot.metro import ToggleTile

        tile = ToggleTile(title=tr(cat["title"]), get_state=cat["get_state"], set_state=cat["set_state"], bg_color=cat.get("color"))
      elif tile_type == "value":
        from openpilot.selfdrive.ui.layouts.settings.starpilot.metro import ValueTile

        tile = ValueTile(title=tr(cat["title"]), get_value=cat["get_value"], on_click=cat["on_click"], bg_color=cat.get("color"))
      else:
        continue
      self._tile_grid.add_tile(tile)
