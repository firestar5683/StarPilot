"""Phone pairing for the comma 3/3X settings layout."""
import time

import numpy as np
import pyray as rl
import qrcode

from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import Widget, DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog, alert_dialog
from openpilot.system.ui.widgets.list_view import button_item
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
from openpilot.tools.galaxy_bluetooth.bridge.pairing import ensure_key, load_key, rotate_key, qr_payload


class PhoneQRDialog(Widget):
  def __init__(self, key):
    super().__init__()
    self._key = key
    self._expires = time.monotonic() + 120
    self._texture = None
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
    qr.add_data(qr_payload(key))
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    pixels = np.array(image, dtype=np.uint8)
    raw = rl.Image()
    raw.data = rl.ffi.cast("void *", pixels.ctypes.data)
    raw.width, raw.height = image.size
    raw.mipmaps = 1
    raw.format = rl.PixelFormat.PIXELFORMAT_UNCOMPRESSED_R8G8B8A8
    self._texture = rl.load_texture_from_image(raw)
    rl.set_texture_filter(self._texture, rl.TextureFilter.TEXTURE_FILTER_POINT)

  def _update_state(self):
    super()._update_state()
    try:
      current = load_key()
    except Exception:
      current = None
    if ui_state.started or current != self._key or time.monotonic() >= self._expires:
      gui_app.pop_widget()

  def hide_event(self):
    if self._texture and self._texture.id:
      rl.unload_texture(self._texture)
    self._texture = None
    self._key = None
    super().hide_event()

  def _handle_mouse_release(self, _):
    gui_app.pop_widget()

  def _text(self, rect, text, y, size):
    font = gui_app.font(FontWeight.MEDIUM)
    width = measure_text_cached(font, text, size).x
    rl.draw_text_ex(font, text, rl.Vector2(rect.x + (rect.width - width) / 2, y), size, 0, rl.WHITE)

  def _render(self, rect):
    rl.clear_background(rl.Color(26, 26, 48, 255))
    self._text(rect, "Scan in the Galaxy app", rect.y + 40, 60)
    if self._texture:
      size = min(rect.height * 0.60, rect.width * 0.60)
      target = rl.Rectangle(rect.x + (rect.width - size) / 2, rect.y + 140, size, size)
      source = rl.Rectangle(0, 0, self._texture.width, self._texture.height)
      rl.draw_texture_pro(self._texture, source, target, rl.Vector2(0, 0), 0, rl.WHITE)
    self._text(rect, "Bluetooth pairing • Keep this code private", rect.y + rect.height - 140, 36)
    self._text(rect, "Tap anywhere to dismiss", rect.y + rect.height - 80, 34)


def pair_phone_item():
  def show_qr():
    if ui_state.started:
      return
    try:
      gui_app.push_widget(PhoneQRDialog(ensure_key()))
    except Exception:
      gui_app.push_widget(alert_dialog("Could not open pairing. Check the Galaxy bridge installation."))

  def forget(result):
    if result != DialogResult.CONFIRM or ui_state.started:
      return
    try:
      rotate_key()
      gui_app.push_widget(alert_dialog("Phones forgotten. Scan a new code to reconnect."))
    except Exception:
      gui_app.push_widget(alert_dialog("Could not forget phones. Try again."))

  def show_options():
    if ui_state.started:
      return

    def apply(result):
      if result != DialogResult.CONFIRM or ui_state.started:
        return
      if dialog.selection == "Pair phone":
        show_qr()
      else:
        gui_app.push_widget(ConfirmDialog("Forget all phones? Scan again to reconnect.", "Forget", callback=forget))

    dialog = MultiOptionDialog("Galaxy app", ["Pair phone", "Forget paired phones"], "Pair phone", callback=apply)
    gui_app.push_widget(dialog)

  return button_item("Pair phone", "MANAGE", "Pair the Galaxy iPhone app with this comma.",
                     callback=show_options, enabled=ui_state.is_offroad)
