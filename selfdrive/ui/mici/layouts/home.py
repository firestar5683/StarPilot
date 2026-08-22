import datetime
import re
import time

from cereal import log
import pyray as rl
from collections.abc import Callable
from importlib.resources import as_file
from openpilot.system.ui.widgets import Widget
from openpilot.system.ui.widgets.layouts import HBoxLayout
from openpilot.system.ui.widgets.icon_widget import IconWidget
from openpilot.system.ui.widgets.label import UnifiedLabel
from openpilot.system.ui.lib.application import ASSETS_DIR, gui_app, FontWeight, MousePos
from openpilot.selfdrive.ui.lib.mode_banner import ModeBannerVariant, get_mode_banner_variant, mode_atom_color
from openpilot.selfdrive.ui.lib.starpilot_version import DEFAULT_HOME_SCREEN_NAME, STARPILOT_DISPLAY_VERSION, home_screen_name
from openpilot.selfdrive.ui.ui_state import ui_state

HEAD_BUTTON_FONT_SIZE = 40
HOME_PADDING = 8

NetworkType = log.DeviceState.NetworkType

NETWORK_TYPES = {
  NetworkType.none: "Offline",
  NetworkType.wifi: "WiFi",
  NetworkType.cell2G: "2G",
  NetworkType.cell3G: "3G",
  NetworkType.cell4G: "LTE",
  NetworkType.cell5G: "5G",
  NetworkType.ethernet: "Ethernet",
}


class NetworkIcon(Widget):
  def __init__(self):
    super().__init__()
    self.set_rect(rl.Rectangle(0, 0, 54, 44))  # max size of all icons
    self._net_type = NetworkType.none
    self._net_strength = 0

    self._wifi_slash_txt = gui_app.texture("icons_mici/settings/network/wifi_strength_slash.png", 50, 44)
    self._wifi_none_txt = gui_app.texture("icons_mici/settings/network/wifi_strength_none.png", 50, 37)
    self._wifi_low_txt = gui_app.texture("icons_mici/settings/network/wifi_strength_low.png", 50, 37)
    self._wifi_medium_txt = gui_app.texture("icons_mici/settings/network/wifi_strength_medium.png", 50, 37)
    self._wifi_full_txt = gui_app.texture("icons_mici/settings/network/wifi_strength_full.png", 50, 37)

    self._cell_none_txt = gui_app.texture("icons_mici/settings/network/cell_strength_none.png", 54, 36)
    self._cell_low_txt = gui_app.texture("icons_mici/settings/network/cell_strength_low.png", 54, 36)
    self._cell_medium_txt = gui_app.texture("icons_mici/settings/network/cell_strength_medium.png", 54, 36)
    self._cell_high_txt = gui_app.texture("icons_mici/settings/network/cell_strength_high.png", 54, 36)
    self._cell_full_txt = gui_app.texture("icons_mici/settings/network/cell_strength_full.png", 54, 36)

  def _update_state(self):
    device_state = ui_state.sm['deviceState']
    self._net_type = device_state.networkType
    strength = device_state.networkStrength
    self._net_strength = max(0, min(5, strength.raw + 1)) if strength.raw > 0 else 0

  def _render(self, _):
    if self._net_type == NetworkType.wifi:
      # There is no 1
      draw_net_txt = {0: self._wifi_none_txt,
                      2: self._wifi_low_txt,
                      3: self._wifi_medium_txt,
                      4: self._wifi_full_txt,
                      5: self._wifi_full_txt}.get(self._net_strength, self._wifi_low_txt)
    elif self._net_type in (NetworkType.cell2G, NetworkType.cell3G, NetworkType.cell4G, NetworkType.cell5G):
      draw_net_txt = {0: self._cell_none_txt,
                      2: self._cell_low_txt,
                      3: self._cell_medium_txt,
                      4: self._cell_high_txt,
                      5: self._cell_full_txt}.get(self._net_strength, self._cell_none_txt)
    else:
      draw_net_txt = self._wifi_slash_txt

    draw_x = self._rect.x + (self._rect.width - draw_net_txt.width) / 2
    draw_y = self._rect.y + (self._rect.height - draw_net_txt.height) / 2

    if draw_net_txt == self._wifi_slash_txt:
      # Offset by difference in height between slashless and slash icons to make center align match
      draw_y -= (self._wifi_slash_txt.height - self._wifi_none_txt.height) / 2

    rl.draw_texture_ex(draw_net_txt, rl.Vector2(draw_x, draw_y), 0.0, 1.0, rl.Color(255, 255, 255, int(255 * 0.9)))


class ModeStatusAtom(Widget):
  def __init__(self):
    super().__init__()
    self._variant = ModeBannerVariant.CHILL
    self._textures = self._make_textures()
    self.set_rect(rl.Rectangle(0, 0, 48, 48))
    self.set_enabled(False)
    self.refresh()

  @staticmethod
  def _make_textures() -> dict[ModeBannerVariant, rl.Texture]:
    textures = {}
    with as_file(ASSETS_DIR.joinpath("icons_mici/experimental_mode.png")) as asset_path:
      source = rl.load_image(asset_path.as_posix())

    pixel_count = source.width * source.height
    source_pixels = bytearray(rl.ffi.buffer(source.data, pixel_count * 4))
    try:
      for variant in ModeBannerVariant:
        tinted = rl.image_copy(source)
        tinted_pixels = bytearray(source_pixels)
        gradient = [mode_atom_color(variant, x / max(source.width - 1, 1)) for x in range(source.width)]
        for y in range(source.height):
          for x in range(source.width):
            offset = (y * source.width + x) * 4
            opacity = source_pixels[offset + 3]
            if opacity == 0:
              continue

            color = gradient[x]
            source_shade = max(source_pixels[offset:offset + 3]) / 255.0
            shade = 0.65 + 0.35 * source_shade
            tinted_pixels[offset] = round(color.r * shade)
            tinted_pixels[offset + 1] = round(color.g * shade)
            tinted_pixels[offset + 2] = round(color.b * shade)
            tinted_pixels[offset + 3] = opacity

        rl.ffi.buffer(tinted.data, len(tinted_pixels))[:] = bytes(tinted_pixels)
        texture = rl.load_texture_from_image(tinted)
        rl.set_texture_filter(texture, rl.TextureFilter.TEXTURE_FILTER_BILINEAR)
        rl.set_texture_wrap(texture, rl.TextureWrap.TEXTURE_WRAP_CLAMP)
        rl.unload_image(tinted)
        textures[variant] = texture
    finally:
      rl.unload_image(source)
    return textures

  def refresh(self) -> None:
    self._variant = get_mode_banner_variant(ui_state.params, ui_state.params_memory)

  def _render(self, rect: rl.Rectangle) -> None:
    texture = self._textures[self._variant]
    source = rl.Rectangle(0, 0, texture.width, texture.height)
    rl.draw_texture_pro(texture, source, rect, rl.Vector2(0, 0), 0, rl.WHITE)

  def __del__(self):
    if rl.is_window_ready():
      for texture in getattr(self, "_textures", {}).values():
        if texture.id != 0:
          rl.unload_texture(texture)


class MiciHomeLayout(Widget):
  def __init__(self):
    super().__init__()
    self._on_settings_click: Callable | None = None

    self._last_refresh = 0
    self._mouse_down_t: None | float = None
    self._did_long_press = False
    self._is_pressed_prev = False

    self._version_text = None
    self._experimental_mode = False
    self._current_model_name = "default"
    self._home_screen_name = DEFAULT_HOME_SCREEN_NAME

    self._mode_status_atom = ModeStatusAtom()
    self._egpu_icon = IconWidget("icons_mici/egpu.png", (50, 37))
    self._egpu_icon_gray = IconWidget("icons_mici/egpu_gray.png", (50, 37))
    self._mic_icon = IconWidget("icons_mici/microphone.png", (32, 46))

    self._status_bar_layout = HBoxLayout([
      IconWidget("icons_mici/settings.png", (48, 48), opacity=0.9),
      NetworkIcon(),
      self._mode_status_atom,
      self._egpu_icon,
      self._egpu_icon_gray,
      self._mic_icon,
    ], spacing=18)

    self._openpilot_label = UnifiedLabel(self._home_screen_name, font_size=96, font_weight=FontWeight.BRAND, max_width=480, wrap_text=False)
    self._version_label = UnifiedLabel("", font_size=36, font_weight=FontWeight.ROMAN, max_width=480, wrap_text=False)
    self._large_version_label = UnifiedLabel("", font_size=64, text_color=rl.GRAY, font_weight=FontWeight.ROMAN, max_width=480, wrap_text=False)
    self._date_label = UnifiedLabel("", font_size=36, text_color=rl.GRAY, font_weight=FontWeight.ROMAN, max_width=480, wrap_text=False)
    self._branch_label = UnifiedLabel("", font_size=36, text_color=rl.GRAY, font_weight=FontWeight.ROMAN, scroll=True)
    self._version_commit_label = UnifiedLabel("", font_size=36, text_color=rl.GRAY, font_weight=FontWeight.ROMAN, max_width=480, wrap_text=False)

  def show_event(self):
    super().show_event()
    self._version_text = self._get_version_text()
    self._update_params()

  def _update_params(self):
    self._experimental_mode = ui_state.params.get_bool("ExperimentalMode")
    self._mode_status_atom.refresh()
    self._home_screen_name = home_screen_name(ui_state.params)
    self._openpilot_label.set_text(self._home_screen_name)
    self._openpilot_label.set_font_weight(FontWeight.BRAND if self._home_screen_name.isascii() else FontWeight.MEDIUM)

    def _clean_model_name(value: str) -> str:
      return re.sub(r"[🗺️👀📡]", "", value).replace("(Default)", "").strip()

    current_name = _clean_model_name(ui_state.params.get("DrivingModelName", encoding="utf-8") or "")
    if not current_name:
      default_name = ui_state.params.get_default_value("DrivingModelName")
      if isinstance(default_name, bytes):
        default_name = default_name.decode("utf-8", errors="ignore")
      current_name = _clean_model_name(str(default_name or ""))

    current_key = (ui_state.params.get("Model", encoding="utf-8") or
                   ui_state.params.get("DrivingModel", encoding="utf-8") or "").strip()
    self._current_model_name = current_name or current_key or "default"

  def _update_state(self):
    if self.is_pressed and not self._is_pressed_prev:
      self._mouse_down_t = time.monotonic()
    elif not self.is_pressed and self._is_pressed_prev:
      self._mouse_down_t = None
      self._did_long_press = False
    self._is_pressed_prev = self.is_pressed

    if self._mouse_down_t is not None:
      if time.monotonic() - self._mouse_down_t > 0.5:
        # long gating for experimental mode - only allow toggle if longitudinal control is available
        if ui_state.has_longitudinal_control:
          self._experimental_mode = not self._experimental_mode
          ui_state.params.put("ExperimentalMode", self._experimental_mode)
          self._mode_status_atom.refresh()
        self._mouse_down_t = None
        self._did_long_press = True

    if rl.get_time() - self._last_refresh > 5.0:
      # Update version text
      self._version_text = self._get_version_text()
      self._last_refresh = rl.get_time()
      self._update_params()

  def set_callbacks(self, on_settings: Callable | None = None):
    self._on_settings_click = on_settings

  def _handle_mouse_release(self, mouse_pos: MousePos):
    if not self._did_long_press:
      if self._on_settings_click:
        self._on_settings_click()
    self._did_long_press = False

  def _get_version_text(self) -> tuple[str, str, str, str] | None:
    branch = ui_state.params.get("GitBranch")
    commit = ui_state.params.get("GitCommit")

    if not all((branch, commit)):
      return None

    commit_date_raw = ui_state.params.get("GitCommitDate")
    try:
      # GitCommitDate format from get_commit_date(): '%ct %ci' e.g. "'1708012345 2024-02-15 ...'"
      unix_ts = int(commit_date_raw.strip("'").split()[0])
      date_str = datetime.datetime.fromtimestamp(unix_ts).strftime("%b %d")
    except (ValueError, IndexError, TypeError, AttributeError):
      date_str = ""

    return STARPILOT_DISPLAY_VERSION, branch, commit[:7], date_str

  def _render(self, _):
    # TODO: why is there extra space here to get it to be flush?
    text_pos = rl.Vector2(self.rect.x - 2 + HOME_PADDING, self.rect.y - 16)
    self._openpilot_label.set_position(text_pos.x, text_pos.y)
    self._openpilot_label.render()

    if self._version_text is not None:
      version_pos = rl.Rectangle(text_pos.x, text_pos.y + self._openpilot_label.font_size + 16, 100, 44)
      self._version_label.set_text(self._version_text[0])
      self._version_label.set_position(version_pos.x, version_pos.y)
      self._version_label.render()

      self._date_label.set_text(" " + self._version_text[3])
      self._date_label.set_position(version_pos.x + self._version_label.text_width + 10, version_pos.y)
      self._date_label.render()

      self._branch_label.set_max_width(gui_app.width - self._version_label.text_width - self._date_label.text_width - 32)
      self._branch_label.set_text(" " + self._current_model_name)
      self._branch_label.set_position(version_pos.x + self._version_label.text_width + self._date_label.text_width + 20, version_pos.y)
      self._branch_label.render()

      # 2nd line
      self._version_commit_label.set_text(self._version_text[2])
      self._version_commit_label.set_position(version_pos.x, version_pos.y + self._date_label.font_size + 7)
      self._version_commit_label.render()

    # ***** Center-aligned bottom section icons *****
    self._egpu_icon.set_visible(ui_state.usbgpu and ui_state.usbgpu_active)
    self._egpu_icon_gray.set_visible(ui_state.usbgpu and not ui_state.usbgpu_active)
    self._mic_icon.set_visible(ui_state.recording_audio)

    footer_rect = rl.Rectangle(self.rect.x + HOME_PADDING, self.rect.y + self.rect.height - 48, self.rect.width - HOME_PADDING, 48)
    self._status_bar_layout.render(footer_rect)
