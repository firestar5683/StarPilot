import pyray as rl
from openpilot.common.params import Params
from openpilot.system.ui.lib.application import gui_app, FontWeight, FONT_SCALE
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import Widget
from openpilot.selfdrive.ui.lib.mode_banner import ModeBannerVariant, draw_mode_banner_gradient, get_mode_banner_variant
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.starpilot.common.experimental_state import requested_experimental_mode


class ExperimentalModeButton(Widget):
  def __init__(self):
    super().__init__()

    self.img_width = 80
    self.horizontal_padding = 25
    self.button_height = 125

    self.params = Params()
    self.experimental_mode = requested_experimental_mode(self.params, ui_state.params_memory)
    self.mode_variant = get_mode_banner_variant(self.params, ui_state.params_memory)

    self.chill_pixmap = gui_app.texture("icons/couch.png", self.img_width, self.img_width)
    self.experimental_pixmap = gui_app.texture("icons/experimental_grey.png", self.img_width, self.img_width)

  def show_event(self):
    self.experimental_mode = requested_experimental_mode(self.params, ui_state.params_memory)
    self.mode_variant = get_mode_banner_variant(self.params, ui_state.params_memory)

  def _render(self, rect):
    rl.begin_scissor_mode(int(rect.x), int(rect.y), int(rect.width), int(rect.height))
    draw_mode_banner_gradient(rect, self.mode_variant, 0xCC if self.is_pressed else 0xFF)
    rl.draw_rectangle_rounded_lines_ex(self._rect, 0.19, 10, 5, rl.BLACK)
    rl.end_scissor_mode()

    # Draw vertical separator line
    line_x = rect.x + rect.width - self.img_width - (2 * self.horizontal_padding)
    separator_color = rl.Color(0, 0, 0, 77)  # 0x4d = 77
    rl.draw_line_ex(rl.Vector2(line_x, rect.y), rl.Vector2(line_x, rect.y + rect.height), 3, separator_color)

    # Draw text label (left aligned)
    text = tr("MODEL FIRST") if self.experimental_mode else tr("SET-SPEED FIRST")

    text_x = rect.x + self.horizontal_padding
    font = gui_app.font(FontWeight.NORMAL)
    font_size = 45
    available_width = line_x - text_x - self.horizontal_padding
    measured_width = measure_text_cached(font, text, font_size).x
    if measured_width > available_width:
      font_size = max(32, int(font_size * available_width / measured_width))
    text_y = rect.y + rect.height / 2 - font_size * FONT_SCALE // 2  # Center vertically

    rl.draw_text_ex(font, text, rl.Vector2(int(text_x), int(text_y)), font_size, 0, rl.BLACK)

    # Draw icon (right aligned)
    icon_x = rect.x + rect.width - self.horizontal_padding - self.img_width
    icon_y = rect.y + (rect.height - self.img_width) / 2
    icon_rect = rl.Rectangle(icon_x, icon_y, self.img_width, self.img_width)

    # Draw current mode icon
    current_icon = self.experimental_pixmap if self.experimental_mode else self.chill_pixmap
    source_rect = rl.Rectangle(0, 0, current_icon.width, current_icon.height)
    rl.draw_texture_pro(current_icon, source_rect, icon_rect, rl.Vector2(0, 0), 0, rl.WHITE)
