"""Readback-only mode indicator using the personality control's pill artwork."""
from openpilot.selfdrive.ui.mici.widgets.button import BigButton, BigMultiToggle
from openpilot.selfdrive.ui.mici.layouts.settings.longitudinal_mode import MODE_LABELS


class LongitudinalModeButton(BigMultiToggle):
  def __init__(self):
    super().__init__("speed control", list(MODE_LABELS.values()))
    self._sub_label.set_font_size(20)
    self.set_value("Unavailable")

  def _get_label_font_size(self):
    return 36

  def _handle_mouse_release(self, mouse_pos):
    # Dispatch only: BigMultiToggle would advance the display before readback.
    # Never use BigMultiParamToggle with a made-up persisted selector key.
    BigButton._handle_mouse_release(self, mouse_pos)

  def _draw_content(self, btn_y):
    if self.value in self._options:
      super()._draw_content(btn_y)
    else:
      BigButton._draw_content(self, btn_y)
      x = self._rect.x + self._rect.width - self._txt_enabled_toggle.width
      for i in range(len(self._options)):
        self._draw_pill(x, btn_y + i * 35, False)
