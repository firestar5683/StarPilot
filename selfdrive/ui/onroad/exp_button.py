import time
import pyray as rl
from openpilot.common.params import Params
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets import Widget
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.starpilot.common.experimental_state import (
  requested_experimental_mode,
  toggle_longitudinal_model_preference,
)


class ExpButton(Widget):
  def __init__(self, button_size: int, icon_size: int):
    super().__init__()
    self._params = Params()
    self._experimental_mode: bool = False
    self._engageable: bool = False

    # State hold mechanism
    self._hold_duration = 2.0  # seconds
    self._held_mode: bool | None = None
    self._hold_end_time: float | None = None

    self._white_color: rl.Color = rl.Color(255, 255, 255, 255)
    self._black_bg: rl.Color = rl.Color(0, 0, 0, 166)
    self._txt_wheel: rl.Texture = gui_app.texture('icons/chffr_wheel.png', icon_size, icon_size)
    self._txt_exp: rl.Texture = gui_app.texture('icons/experimental.png', icon_size, icon_size)
    self._rect = rl.Rectangle(0, 0, button_size, button_size)

    self._steer_angle_filter = FirstOrderFilter(0.0, 0.1, 1 / gui_app.target_fps)
    self._bg_colors = {
      "disengaged": rl.Color(0, 0, 0, 166),
      "switchback": rl.Color(0x8b, 0x6c, 0xc5, 255),
      "aol": rl.Color(0x0a, 0xba, 0xb5, 255),
      "experimental": rl.Color(0xda, 0x6f, 0x25, 255),
      "traffic": rl.Color(0xc9, 0x22, 0x31, 255),
    }
    self._bg_color = self._black_bg

    # Visibility controlled by HideSteeringWheel toggle
    self.set_visible(lambda: not (ui_state.starpilot_toggles.get("hide_steering_wheel", False) or
                                  self._params.get_bool("HideSteeringWheel")))

  def set_rect(self, rect: rl.Rectangle) -> None:
    self._rect.x, self._rect.y = rect.x, rect.y

  def _update_state(self) -> None:
    selfdrive_state = ui_state.sm["selfdriveState"]
    self._experimental_mode = requested_experimental_mode(self._params, ui_state.params_memory)
    self._engageable = selfdrive_state.engageable or selfdrive_state.enabled or ui_state.always_on_lateral_active

    # Smooth steering angle for rotating wheel
    car_state = ui_state.sm["carState"]
    self._steer_angle_filter.update(car_state.steeringAngleDeg)

    # Determine background color based on engagement state
    simple_mode = ui_state.starpilot_toggles.get("simple_mode", False)
    if simple_mode or self.is_pressed or not self._engageable:
      self._bg_color = self._bg_colors["disengaged"]
    elif ui_state.switchback_mode_enabled:
      self._bg_color = self._bg_colors["switchback"]
    elif ui_state.always_on_lateral_active:
      self._bg_color = self._bg_colors["aol"]
    elif self._held_or_actual_mode():
      self._bg_color = self._bg_colors["experimental"]
    elif ui_state.traffic_mode_enabled:
      self._bg_color = self._bg_colors["traffic"]
    else:
      self._bg_color = self._bg_colors["disengaged"]

  def _handle_mouse_release(self, _):
    super()._handle_mouse_release(_)
    if self._is_toggle_allowed():
      new_mode = toggle_longitudinal_model_preference(self._params, ui_state.params_memory)
      self._held_mode = new_mode
      self._hold_end_time = time.monotonic() + self._hold_duration

  def _render(self, rect: rl.Rectangle) -> None:
    center_x = int(self._rect.x + self._rect.width // 2)
    center_y = int(self._rect.y + self._rect.height // 2)

    self._white_color.a = 180 if self.is_pressed or not self._engageable else 255

    texture = self._txt_exp if self._held_or_actual_mode() else self._txt_wheel
    rl.draw_circle(center_x, center_y, self._rect.width / 2, self._bg_color)

    rotating_wheel = ui_state.starpilot_toggles.get("rotating_wheel", False) or self._params.get_bool("RotatingWheel")
    if texture == self._txt_wheel and rotating_wheel:
      source_rect = rl.Rectangle(0, 0, texture.width, texture.height)
      dest_rect = rl.Rectangle(center_x, center_y, texture.width, texture.height)
      origin = rl.Vector2(texture.width / 2, texture.height / 2)
      rl.draw_texture_pro(texture, source_rect, dest_rect, origin, -self._steer_angle_filter.x, self._white_color)
    else:
      rl.draw_texture_ex(texture, rl.Vector2(center_x - texture.width / 2, center_y - texture.height / 2), 0.0, 1.0, self._white_color)

  def _held_or_actual_mode(self):
    now = time.monotonic()
    if self._hold_end_time and now < self._hold_end_time:
      return self._held_mode

    if self._hold_end_time and now >= self._hold_end_time:
      self._hold_end_time = self._held_mode = None

    return self._experimental_mode

  def _is_toggle_allowed(self):
    if self._params.get_bool("SafeMode"):
      return False

    if not self._params.get_bool("ExperimentalModeConfirmed"):
      return False

    # Mirror exp mode toggle using persistent car params
    return ui_state.has_longitudinal_control
