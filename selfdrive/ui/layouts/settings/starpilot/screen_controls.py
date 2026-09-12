from __future__ import annotations

import pyray as rl

from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  AetherAdjustorRow,
  AetherInlineRangeControl,
  AetherSegmentedControl,
  DEFAULT_PANEL_STYLE,
  RowToggleTile,
  draw_rounded_fill,
  draw_rounded_stroke,
  draw_text_fit_common,
  wrap_text,
)
from openpilot.starpilot.common.screen_settings import brightness_preferences, set_brightness_mode, write_screen_setting
from openpilot.system.ui.lib.application import FontWeight, gui_app
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.widgets import Widget
from openpilot.system.ui.widgets.label import gui_label
from openpilot.system.ui.widgets.confirm_dialog import alert_dialog
from openpilot.selfdrive.ui.lib.screen_settings import try_screen_setting


def show_screen_save_error():
  gui_app.push_widget(alert_dialog(tr("Unable to save screen settings. Please try again.")))


class BrightnessAdjustorRow(AetherAdjustorRow):
  def __init__(self, *args, params, brightness_key: str, **kwargs):
    self._params = params
    self._brightness_key = brightness_key
    super().__init__(*args, **kwargs)

  def formatted_value(self) -> str:
    prefs = brightness_preferences(self._params, self._brightness_key)
    if prefs["mode"] == "auto":
      return tr("Auto") + f" {prefs['offset']:+d}%"
    return tr("Manual") + f" {prefs['manual']}%"


class WakeToggleRow(RowToggleTile):
  """Show the wake description; the standard compact toggle row only shows its state."""

  def _render(self, rect: rl.Rectangle):
    active = self.get_state()
    self._animate_plate(rl.get_frame_time())
    face, accent = self._render_hud_background(rect, self._active_color, self._glow)
    x, width = face.x + 24, face.width - 48
    draw_text_fit_common(self._font, self.title, rl.Vector2(x, face.y + 14), width - 150, 32, color=rl.WHITE)
    state = tr("Enabled") if active else tr("Disabled")
    gui_label(
      rl.Rectangle(x + width - 135, face.y + 12, 135, 38),
      state,
      24,
      accent if active else rl.Color(170, 175, 185, 255),
      FontWeight.MEDIUM,
      alignment=rl.GuiTextAlignment.TEXT_ALIGN_RIGHT,
    )
    lines = wrap_text(self._font_desc, self.desc, width, 22, max_lines=3)
    for index, line in enumerate(lines):
      draw_text_fit_common(self._font_desc, line, rl.Vector2(x, face.y + 54 + index * 24), width, 22, color=rl.Color(190, 195, 205, 255))


class AetherBrightnessDialog(Widget):
  """Separate persisted mode and value controls; all brightness output stays in Device."""

  def __init__(self, params, key: str, title: str):
    super().__init__()
    self._params, self._key, self._title = params, key, title
    self._done_rect = rl.Rectangle(0, 0, 0, 0)
    self._done_pressed = False
    self._mode_control = self._child(AetherSegmentedControl([tr("Auto"), tr("Manual")], self._mode_index, self._set_mode, style=DEFAULT_PANEL_STYLE))
    prefs = brightness_preferences(params, key)
    self._offset = self._child(
      AetherInlineRangeControl(
        -30,
        30,
        1,
        prefs["offset"],
        lambda value: None,
        on_commit=lambda value: self._save_value(self._key + "Offset", int(value)),
        unit="%",
        labels={value: f"{value:+d}%" for value in range(-30, 31)},
      )
    )
    self._manual = self._child(
      AetherInlineRangeControl(0, 100, 1, prefs["manual"], lambda value: None, on_commit=lambda value: self._save_value(self._key, int(value)), unit="%")
    )
    self._offset.set_visible(lambda: self._mode_index() == 0)
    self._manual.set_visible(lambda: self._mode_index() == 1)

  def _mode_index(self) -> int:
    return 0 if brightness_preferences(self._params, self._key)["mode"] == "auto" else 1

  def _set_mode(self, index: int):
    saved = try_screen_setting(lambda: set_brightness_mode(self._params, self._key, "auto" if index == 0 else "manual"), show_screen_save_error)
    if not saved:
      self._refresh_controls()
    return saved

  def _save_value(self, key: str, value: int):
    saved = try_screen_setting(lambda: write_screen_setting(self._params, key, value), show_screen_save_error)
    if not saved:
      self._refresh_controls()
    return saved

  def _refresh_controls(self):
    prefs = brightness_preferences(self._params, self._key)
    for control, value in ((self._offset, prefs["offset"]), (self._manual, prefs["manual"])):
      control.reset_interaction()
      control.set_value(value)

  def _handle_mouse_press(self, mouse_pos):
    self._done_pressed = rl.check_collision_point_rec(mouse_pos, self._done_rect)

  def _handle_mouse_release(self, mouse_pos):
    if self._done_pressed and rl.check_collision_point_rec(mouse_pos, self._done_rect):
      gui_app.pop_widget()
    self._done_pressed = False

  def _render(self, rect: rl.Rectangle):
    rl.draw_rectangle(0, 0, gui_app.width, gui_app.height, rl.Color(0, 0, 0, 180))
    card = rl.Rectangle(rect.x + 60, rect.y + 60, rect.width - 120, rect.height - 120)
    draw_rounded_fill(card, rl.Color(10, 12, 16, 255), radius_px=35)
    draw_rounded_stroke(card, rl.Color(255, 255, 255, 35), radius_px=35)
    inset, width = card.x + 80, card.width - 160
    gui_label(rl.Rectangle(inset, card.y + 50, width - 250, 80), self._title, 60, rl.WHITE, FontWeight.BOLD)
    self._done_rect = rl.Rectangle(card.x + card.width - 290, card.y + 35, 230, 110)
    draw_rounded_fill(self._done_rect, DEFAULT_PANEL_STYLE.accent, radius_px=20)
    gui_label(self._done_rect, tr("Done"), 46, rl.WHITE, FontWeight.BOLD, alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER)
    self._mode_control.render(rl.Rectangle(inset, card.y + 175, width, 125))

    prefs = brightness_preferences(self._params, self._key)
    auto = prefs["mode"] == "auto"
    control = self._offset if auto else self._manual
    if not control.is_interacting:
      control.set_value(prefs["offset"] if auto else prefs["manual"])
    value = int(control.current_val)
    title = tr("Auto Brightness Offset") if auto else tr("Manual Brightness")
    description = (
      tr("Adjust automatic brightness from -30% to +30%. 0% keeps the normal automatic level.") if auto else tr("Set a fixed brightness from 0 to 100%.")
    )
    gui_label(rl.Rectangle(inset, card.y + 355, width, 70), title, 46, rl.WHITE, FontWeight.MEDIUM)
    gui_label(rl.Rectangle(inset, card.y + 435, width, 75), f"{value:+d}%" if auto else f"{value}%", 66, DEFAULT_PANEL_STYLE.accent, FontWeight.BOLD)
    control.render(rl.Rectangle(inset, card.y + card.height - 245, width, 100))
    endpoint_y = card.y + card.height - 153
    gui_label(rl.Rectangle(inset + 84, endpoint_y, 300, 30), "-30%" if auto else "0%", 26, rl.Color(160, 165, 175, 255), FontWeight.NORMAL)
    gui_label(
      rl.Rectangle(inset + width - 384, endpoint_y, 300, 30),
      "+30%" if auto else "100%",
      26,
      rl.Color(160, 165, 175, 255),
      FontWeight.NORMAL,
      alignment=rl.GuiTextAlignment.TEXT_ALIGN_RIGHT,
    )
    gui_label(rl.Rectangle(inset, card.y + card.height - 115, width, 70), description, 28, rl.Color(180, 185, 195, 255), FontWeight.NORMAL)
