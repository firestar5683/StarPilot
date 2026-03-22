from __future__ import annotations
import subprocess
from pathlib import Path

from openpilot.common.basedir import BASEDIR
from openpilot.frogpilot.common.frogpilot_variables import ACTIVE_THEME_PATH
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.selection_dialog import SelectionDialog
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import StarPilotPanel
from openpilot.selfdrive.ui.layouts.settings.starpilot.metro import TileGrid, ToggleTile, SliderDialog

class StarPilotSoundsLayout(StarPilotPanel):
  VOLUME_KEYS = [
    "DisengageVolume",
    "EngageVolume",
    "PromptVolume",
    "PromptDistractedVolume",
    "RefuseVolume",
    "WarningSoftVolume",
    "WarningImmediateVolume",
  ]
  CUSTOM_ALERTS_KEYS = [
    "GoatScream",
    "GreenLightAlert",
    "LeadDepartingAlert",
    "LoudBlindspotAlert",
    "SpeedLimitChangedAlert",
  ]

  def __init__(self):
    super().__init__()

    self._sub_panels = {
      "volume_control": StarPilotVolumeControlLayout(),
      "custom_alerts": StarPilotCustomAlertsLayout(),
    }

    self.CATEGORIES = [
      {
        "title": tr_noop("Alert Volume Controller"),
        "panel": "volume_control",
        "desc": tr_noop("Adjust volume levels for different alert types."),
        "icon": "toggle_icons/icon_mute.png",
        "color": "#FF0097"
      },
      {
        "title": tr_noop("StarPilot Alerts"),
        "panel": "custom_alerts",
        "desc": tr_noop("Enable or disable specific StarPilot-only alerts."),
        "icon": "toggle_icons/icon_green_light.png",
        "color": "#FF0097"
      },
    ]

    for name, panel in self._sub_panels.items():
      if hasattr(panel, 'set_navigate_callback'):
        panel.set_navigate_callback(self._navigate_to)
      if hasattr(panel, 'set_back_callback'):
        panel.set_back_callback(self._go_back)

    self._rebuild_grid()

  def refresh_visibility(self):
    for panel in self._sub_panels.values():
      if hasattr(panel, 'refresh_visibility'):
        panel.refresh_visibility()

class StarPilotVolumeControlLayout(StarPilotPanel):
  VOLUME_INFO = {
    "DisengageVolume": {"title": tr_noop("Disengage Volume"), "icon": "toggle_icons/icon_mute.png", "min": 0},
    "EngageVolume": {"title": tr_noop("Engage Volume"), "icon": "toggle_icons/icon_green_light.png", "min": 0},
    "PromptVolume": {"title": tr_noop("Prompt Volume"), "icon": "toggle_icons/icon_message.png", "min": 0},
    "PromptDistractedVolume": {"title": tr_noop("Distracted Volume"), "icon": "toggle_icons/icon_display.png", "min": 0},
    "RefuseVolume": {"title": tr_noop("Refuse Volume"), "icon": "toggle_icons/icon_mute.png", "min": 0},
    "WarningSoftVolume": {"title": tr_noop("Warning Soft"), "icon": "toggle_icons/icon_conditional.png", "min": 25},
    "WarningImmediateVolume": {"title": tr_noop("Warning Immediate"), "icon": "toggle_icons/icon_conditional.png", "min": 25},
  }

  _sound_player_process = None

  def __init__(self):
    super().__init__()
    self._init_sound_player()
    
    self.CATEGORIES = []
    for key in StarPilotSoundsLayout.VOLUME_KEYS:
      info = self.VOLUME_INFO[key]
      
      def get_val(k=key):
        v = self._params.get_int(k, return_default=True, default=100)
        if v == 0: return tr("Muted")
        if v == 101: return tr("Auto")
        return f"{v}%"

      def on_click(k=key, i=info):
        self._show_volume_selector(k, i)

      self.CATEGORIES.append({
        "title": info["title"],
        "type": "value",
        "get_value": get_val,
        "on_click": on_click,
        "icon": info["icon"],
        "color": "#FF0097"
      })

    self._rebuild_grid()

  def _show_volume_selector(self, key: str, info: dict):
    current_v = self._params.get_int(key, return_default=True, default=100)
    
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        new_v = int(val)
        if new_v != 101 and new_v < info["min"]:
          new_v = info["min"]
        self._params.put_int(key, new_v)
        self._test_sound(key)
        self._rebuild_grid()

    gui_app.set_modal_overlay(SliderDialog(
      tr(info["title"]), 0, 101, 1, current_v, on_close,
      unit="%", labels={0: tr("Muted"), 101: tr("Auto")}, color="#FF0097"
    ))

  @classmethod
  def _init_sound_player(cls):
    if cls._sound_player_process is not None: return
    program = """
import numpy as np
import sounddevice as sd
import sys
import wave
while True:
  try:
    line = sys.stdin.readline()
    if not line: break
    path, volume = line.strip().split('|')
    sound_file = wave.open(path, 'rb')
    audio = np.frombuffer(sound_file.readframes(sound_file.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    sd.play(audio * float(volume), sound_file.getframerate())
    sd.wait()
  except: pass
"""
    cls._sound_player_process = subprocess.Popen(["python3", "-u", "-c", program], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

  def _test_sound(self, key: str):
    base_name = key.replace("Volume", "")
    if ui_state.started:
      self._params_memory.put("TestAlert", base_name[0].lower() + base_name[1:])
    else:
      self._play_sound_offroad(key)

  def _play_sound_offroad(self, key: str):
    base_name = key.replace("Volume", "")
    snake_case = "".join(["_" + c.lower() if c.isupper() else c for c in base_name]).lstrip("_")
    stock_path = Path(BASEDIR) / "selfdrive" / "assets" / "sounds" / f"{snake_case}.wav"
    theme_path = ACTIVE_THEME_PATH / "sounds" / f"{snake_case}.wav"
    sound_path = theme_path if theme_path.exists() else stock_path
    if not sound_path.exists(): return
    volume = self._params.get_int(key, return_default=True, default=100) / 100.0
    try:
      self._sound_player_process.stdin.write(f"{sound_path}|{volume}\n".encode())
      self._sound_player_process.stdin.flush()
    except: pass

class StarPilotCustomAlertsLayout(StarPilotPanel):
  ALERT_INFO = {
    "GoatScream": {"title": tr_noop("Goat Scream"), "icon": "toggle_icons/icon_sound.png"},
    "GreenLightAlert": {"title": tr_noop("Green Light"), "icon": "toggle_icons/icon_green_light.png"},
    "LeadDepartingAlert": {"title": tr_noop("Lead Departure"), "icon": "toggle_icons/icon_steering.png"},
    "LoudBlindspotAlert": {"title": tr_noop("Loud Blindspot"), "icon": "toggle_icons/icon_display.png"},
    "SpeedLimitChangedAlert": {"title": tr_noop("Speed Limit"), "icon": "toggle_icons/icon_speed_limit.png"},
  }

  def __init__(self):
    super().__init__()
    self.CATEGORIES = []
    for key in StarPilotSoundsLayout.CUSTOM_ALERTS_KEYS:
      info = self.ALERT_INFO[key]
      self.CATEGORIES.append({
        "title": info["title"],
        "type": "toggle",
        "get_state": lambda k=key: self._params.get_bool(k),
        "set_state": lambda s, k=key: self._params.put_bool(k, s),
        "icon": info["icon"],
        "color": "#FF0097",
        "key": key # Store for visibility check
      })
    self._rebuild_grid()

  def refresh_visibility(self):
    self._rebuild_grid()

  def _rebuild_grid(self):
    # Override to add custom BSM/SLC visibility logic
    if not self.CATEGORIES: return
    if self._tile_grid is None: self._tile_grid = TileGrid(columns=None, padding=20)
    self._tile_grid.clear()

    for cat in self.CATEGORIES:
      key = cat.get("key")
      visible = True

      if key == "LoudBlindspotAlert":
        visible &= starpilot_state.car_state.hasBSM
      elif key == "SpeedLimitChangedAlert":
        visible &= self._params.get_bool("ShowSpeedLimits") or (
          starpilot_state.car_state.hasOpenpilotLongitudinal and self._params.get_bool("SpeedLimitController")
        )

      if not visible: continue

      tile = ToggleTile(        title=tr(cat["title"]),
        get_state=cat["get_state"],
        set_state=cat["set_state"],
        icon_path=cat.get("icon"),
        bg_color=cat.get("color")
      )
      self._tile_grid.add_tile(tile)
