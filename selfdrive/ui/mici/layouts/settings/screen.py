from __future__ import annotations

from collections.abc import Callable
import pyray as rl

from openpilot.common.params import Params
from openpilot.selfdrive.ui.mici.widgets.button import BigButton, BigToggle, GreyBigButton
from openpilot.selfdrive.ui.mici.widgets.dialog import BigDialog, BigMultiOptionDialog
from openpilot.starpilot.common.screen_settings import (
  BRIGHTNESS_KEYS,
  SCREEN_INT_KEYS,
  SCREEN_WAKE_DESCRIPTIONS,
  SCREEN_WAKE_KEYS,
  SCREEN_WAKE_OPTIONS,
  brightness_preferences,
  set_brightness_mode,
  write_screen_setting,
)
from openpilot.system.ui.lib.application import FontWeight, gui_app
from openpilot.system.ui.widgets.label import gui_label
from openpilot.system.ui.widgets.nav_widget import NavWidget
from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.system.ui.lib.multilang import tr
from openpilot.selfdrive.ui.lib.screen_settings import try_screen_setting


def show_screen_save_error():
  gui_app.push_widget(BigDialog("", tr("Unable to save screen settings. Please try again.")))


class ScreenModeDialogMici(BigMultiOptionDialog):
  def __init__(self, *args, current_option: Callable[[], str], **kwargs):
    super().__init__(*args, **kwargs)
    self._current_option = current_option

  def _confirm_selection(self):
    if self._right_btn_callback is None or self._right_btn_callback():
      self.dismiss()
    else:
      self._selected_option = self._default_option = self._current_option()
      self._on_option_selected(self._selected_option)


class ScreenSliderMici(NavWidget):
  """A numeric slider sized for the comma4 display, with swipe-down back navigation."""

  BACK_TOUCH_AREA_PERCENTAGE = 0.30

  def __init__(
    self,
    title: str,
    minimum: int,
    maximum: int,
    step: int,
    value: int,
    unit: str,
    on_change: Callable[[int], bool | None],
    read_value: Callable[[], int] | None = None,
  ):
    super().__init__()
    self._title, self._minimum, self._maximum, self._step = title, minimum, maximum, step
    self._value, self._unit, self._on_change = value, unit, on_change
    self._committed_value = value
    self._read_value = read_value
    self._track = rl.Rectangle(0, 0, 1, 1)
    self._minus = rl.Rectangle(0, 0, 0, 0)
    self._plus = rl.Rectangle(0, 0, 0, 0)
    self._pressed = None
    self._dragging = False

  def _value_from_x(self, x: float) -> int:
    fraction = max(0.0, min(1.0, (x - self._track.x) / max(1.0, self._track.width)))
    value = self._minimum + round(fraction * (self._maximum - self._minimum) / self._step) * self._step
    return max(self._minimum, min(self._maximum, int(value)))

  def _handle_mouse_press(self, mouse_pos):
    if self.is_dismissing:
      return
    self._pressed = None
    if rl.check_collision_point_rec(mouse_pos, self._minus):
      self._pressed = "minus"
    elif rl.check_collision_point_rec(mouse_pos, self._plus):
      self._pressed = "plus"
    elif rl.check_collision_point_rec(mouse_pos, rl.Rectangle(self._track.x, self._track.y - 35, self._track.width, 80)):
      self._dragging = True
      self._value = self._value_from_x(mouse_pos.x)

  def _handle_mouse_event(self, mouse_event):
    super()._handle_mouse_event(mouse_event)
    if self._dragging and mouse_event.left_down:
      self._value = self._value_from_x(mouse_event.pos.x)

  def _handle_mouse_release(self, mouse_pos):
    changed = self._dragging
    if self._pressed == "minus" and rl.check_collision_point_rec(mouse_pos, self._minus):
      self._value = max(self._minimum, self._value - self._step)
      changed = True
    elif self._pressed == "plus" and rl.check_collision_point_rec(mouse_pos, self._plus):
      self._value = min(self._maximum, self._value + self._step)
      changed = True
    self._dragging, self._pressed = False, None
    if changed and not self.is_dismissing:
      if self._on_change(self._value) is False:
        self._value = self._read_value() if self._read_value is not None else self._committed_value
        self._committed_value = self._value
      else:
        self._committed_value = self._value

  def _render(self, rect: rl.Rectangle):
    color = rl.Color(175, 150, 255, 255)
    gui_label(rl.Rectangle(rect.x + 25, rect.y + 22, rect.width - 50, 45), self._title, 34, rl.WHITE, FontWeight.BOLD)
    value = f"{self._value:+d}{self._unit}" if self._minimum < 0 else f"{self._value}{self._unit}"
    gui_label(rl.Rectangle(rect.x + 25, rect.y + 72, rect.width - 50, 48), value, 42, color, FontWeight.BOLD, alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER)
    y = rect.y + rect.height - 75
    self._minus = rl.Rectangle(rect.x + 20, y - 20, 60, 65)
    self._plus = rl.Rectangle(rect.x + rect.width - 80, y - 20, 60, 65)
    self._track = rl.Rectangle(rect.x + 105, y + 10, max(1, rect.width - 210), 8)
    for button, label in ((self._minus, "-"), (self._plus, "+")):
      rl.draw_rectangle_rounded(button, 0.3, 6, rl.Color(50, 50, 55, 255))
      gui_label(button, label, 42, rl.WHITE, FontWeight.BOLD, alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER)
    rl.draw_rectangle_rounded(self._track, 1.0, 8, rl.Color(65, 65, 70, 255))
    fraction = (self._value - self._minimum) / max(1, self._maximum - self._minimum)
    fill = rl.Rectangle(self._track.x, self._track.y, self._track.width * fraction, self._track.height)
    if fill.width > 0:
      rl.draw_rectangle_rounded(fill, 1.0, 8, color)
    rl.draw_circle_v(rl.Vector2(self._track.x + fill.width, self._track.y + 4), 18, color)
    for x, endpoint, alignment in (
      (self._track.x, self._minimum, rl.GuiTextAlignment.TEXT_ALIGN_LEFT),
      (self._track.x + self._track.width - 140, self._maximum, rl.GuiTextAlignment.TEXT_ALIGN_RIGHT),
    ):
      endpoint_text = f"{endpoint:+d}{self._unit}" if self._minimum < 0 else f"{endpoint}{self._unit}"
      gui_label(rl.Rectangle(x, y + 38, 140, 26), endpoint_text, 20, rl.Color(160, 160, 170, 255), FontWeight.NORMAL, alignment=alignment)


class ScreenValueButton(BigButton):
  def __init__(self, title: str, params, get_spec: Callable[[], dict]):
    super().__init__(title)
    self._params, self._get_spec = params, get_spec
    self.set_click_callback(self._show_slider)
    self.refresh()

  def refresh(self):
    spec = self._get_spec()
    value = int(spec["value"])
    self.set_text(spec.get("label", self.text))
    self.set_value(f"{value:+d}{spec['unit']}" if spec["min"] < 0 else f"{value}{spec['unit']}")

  def _show_slider(self):
    spec = self._get_spec()
    gui_app.push_widget(
      ScreenSliderMici(
        spec["title"],
        spec["min"],
        spec["max"],
        spec.get("step", 1),
        spec["value"],
        spec["unit"],
        lambda value: self._save(spec["key"], value),
        read_value=lambda: self._read_saved_value(spec["key"]),
      )
    )

  def _read_saved_value(self, key: str) -> int:
    if key in BRIGHTNESS_KEYS:
      return brightness_preferences(self._params, key)["manual"]
    if key.endswith("Offset"):
      return brightness_preferences(self._params, key.removesuffix("Offset"))["offset"]
    return self._params.get_int(key, return_default=True)

  def _save(self, key: str, value: int):
    def write():
      if key in SCREEN_INT_KEYS:
        write_screen_setting(self._params, key, value)
      else:
        self._params.put_int(key, value)

    saved = try_screen_setting(write, show_screen_save_error)
    self.refresh()
    return saved


class BrightnessLayoutMici(NavScroller):
  def __init__(self, key: str, title: str):
    super().__init__()
    self._params, self._key, self._title = Params(), key, title
    self._mode = BigButton(title, "")
    self._mode.set_click_callback(self._show_mode_selector)
    self._value = ScreenValueButton("", self._params, self._slider_spec)
    self._explanation = GreyBigButton("", "")
    self._scroller.add_widgets([self._mode, self._value, self._explanation])
    self._refresh()

  def _slider_spec(self) -> dict:
    prefs = brightness_preferences(self._params, self._key)
    if prefs["mode"] == "auto":
      return {
        "key": self._key + "Offset",
        "title": "auto brightness offset",
        "label": "auto offset",
        "min": -30,
        "max": 30,
        "value": prefs["offset"],
        "unit": "%",
      }
    return {"key": self._key, "title": "manual brightness", "label": "manual brightness", "min": 0, "max": 100, "value": prefs["manual"], "unit": "%"}

  def _show_mode_selector(self):
    prefs = brightness_preferences(self._params, self._key)
    holder = {}

    def confirm():
      saved = try_screen_setting(lambda: set_brightness_mode(self._params, self._key, holder["dialog"].get_selected_option().lower()), show_screen_save_error)
      self._refresh()
      return saved

    dialog = ScreenModeDialogMici(
      options=["Auto", "Manual"],
      default=prefs["mode"].title(),
      right_btn_callback=confirm,
      current_option=lambda: brightness_preferences(self._params, self._key)["mode"].title(),
    )
    holder["dialog"] = dialog
    gui_app.push_widget(dialog)

  def _refresh(self):
    prefs = brightness_preferences(self._params, self._key)
    self._mode.set_value(prefs["mode"].title())
    self._value.refresh()
    self._explanation.set_value(
      "Auto offset: -30% to +30%. 0% keeps normal brightness." if prefs["mode"] == "auto" else "Manual sets a fixed brightness from 0 to 100%."
    )

  def show_event(self):
    super().show_event()
    self._refresh()

  def _update_state(self):
    super()._update_state()
    self._refresh()


class ScreenToggleMici(BigToggle):
  def __init__(self, title: str, params, key: str, default: bool = False):
    self._params, self._key, self._default = params, key, default
    super().__init__(title, toggle_callback=self._save)
    self.refresh()

  def _save(self, value: bool):
    def write():
      if self._key in SCREEN_WAKE_KEYS:
        write_screen_setting(self._params, self._key, value)
      else:
        self._params.put_bool(self._key, value)

    saved = try_screen_setting(write, show_screen_save_error)
    self.refresh()
    return saved

  def refresh(self):
    self.set_checked(self._params.get_bool(self._key, default=self._default))


class ScreenWakeToggleMici(ScreenToggleMici):
  """Keep each wake condition and its full explanation on one small-screen card."""

  LABEL_HORIZONTAL_PADDING = 22
  LABEL_VERTICAL_PADDING = 14

  def __init__(self, title: str, params, key: str, default: bool):
    super().__init__(title, params, key, default)
    self.set_value(SCREEN_WAKE_DESCRIPTIONS[key])
    self._sub_label.set_line_height(1.0)

  def _get_label_font_size(self):
    return 26

  def _width_hint(self) -> int:
    return int(self._rect.width - self.LABEL_HORIZONTAL_PADDING * 2 - self._txt_enabled_toggle.width)

  def _draw_content(self, btn_y: float):
    width = self._width_hint()
    available = self._rect.height - self.LABEL_VERTICAL_PADDING * 2 - self._label.get_content_height(width)
    for size in range(22, 17, -1):
      self._sub_label.set_font_size(size)
      if self._sub_label.get_content_height(width) <= available:
        break
    super()._draw_content(btn_y)


class ScreenSettingsLayoutMici(NavScroller):
  def __init__(self):
    super().__init__()
    self._params = Params()
    management = ScreenToggleMici("screen controls", self._params, "ScreenManagement", True)
    offroad = BigButton("offroad brightness")
    offroad.set_click_callback(lambda: gui_app.push_widget(BrightnessLayoutMici("ScreenBrightness", "offroad brightness")))
    onroad = BigButton("onroad brightness")
    onroad.set_click_callback(lambda: gui_app.push_widget(BrightnessLayoutMici("ScreenBrightnessOnroad", "onroad brightness")))
    offroad_timeout = self._timeout_button("ScreenTimeout", "offroad timeout")
    self._onroad_timeout = self._timeout_button("ScreenTimeoutOnroad", "onroad timeout")
    standby = ScreenToggleMici("standby mode", self._params, "StandbyMode")
    self._wake_controls = [ScreenWakeToggleMici("wake: " + label.lower(), self._params, key, default) for key, label, default in SCREEN_WAKE_OPTIONS]
    explanation = GreyBigButton("", "Standby sleeps the screen onroad. Only selected wake events wake it.")
    self._refresh_controls = [management, offroad_timeout, self._onroad_timeout, standby, *self._wake_controls]
    for control in [offroad, onroad, offroad_timeout, self._onroad_timeout, standby, *self._wake_controls]:
      control.set_enabled(lambda: self._params.get_bool("ScreenManagement", default=True))
    self._scroller.add_widgets([management, offroad, onroad, offroad_timeout, standby, self._onroad_timeout, *self._wake_controls, explanation])
    self._refresh()

  def _timeout_button(self, key: str, title: str) -> ScreenValueButton:
    return ScreenValueButton(
      title,
      self._params,
      lambda: {
        "key": key,
        "title": title,
        "label": title,
        "min": 5,
        "max": 60,
        "step": 5,
        "value": self._params.get_int(key, return_default=True),
        "unit": " seconds",
      },
    )

  def _refresh(self):
    for control in self._refresh_controls:
      control.refresh()
    standby = self._params.get_bool("StandbyMode")
    self._onroad_timeout.set_visible(standby)
    for control in self._wake_controls:
      control.set_visible(standby)

  def show_event(self):
    super().show_event()
    self._refresh()

  def _update_state(self):
    super()._update_state()
    self._refresh()
