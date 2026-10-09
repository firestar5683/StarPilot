"""On-device, offroad-only native app pairing for comma 4."""
import time

import numpy as np
import pyray as rl
import qrcode

from openpilot.selfdrive.ui.mici.layouts.settings.galaxy import GalaxyQRDialog
from openpilot.selfdrive.ui.mici.widgets.button import BigButton
from openpilot.selfdrive.ui.mici.widgets.dialog import BigDialog, BigConfirmationDialog, BigMultiOptionDialog
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.widgets.label import UnifiedLabel
from openpilot.tools.galaxy_bluetooth.bootstrap import setup_status, retry_setup
from openpilot.tools.galaxy_bluetooth.bridge.pairing import ensure_key, load_key, rotate_key, qr_payload


class PhoneQRDialog(GalaxyQRDialog):
  def __init__(self, key):
    self._key = key
    self._expires = time.monotonic() + 120
    super().__init__(qr_payload(key))
    self._title = UnifiedLabel("scan in Galaxy app\nBluetooth pairing\nkeep this code private",
                               font_size=36, font_weight=FontWeight.BOLD)

  def _generate_qr_code(self):
    # Standard dark modules with a four-module quiet zone for phone cameras.
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
    qr.add_data(self._url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    pixels = np.array(image, dtype=np.uint8)
    raw = rl.Image()
    raw.data = rl.ffi.cast("void *", pixels.ctypes.data)
    raw.width, raw.height = image.size
    raw.mipmaps = 1
    raw.format = rl.PixelFormat.PIXELFORMAT_UNCOMPRESSED_R8G8B8A8
    self._qr_texture = rl.load_texture_from_image(raw)
    rl.set_texture_filter(self._qr_texture, rl.TextureFilter.TEXTURE_FILTER_POINT)

  def _update_state(self):
    super()._update_state()
    try:
      current = load_key()
    except Exception:
      current = None
    if ui_state.started or current != self._key or time.monotonic() >= self._expires:
      self.dismiss()

  def hide_event(self):
    # A popped dialog must not retain a visible pairing code in a GPU texture.
    if self._qr_texture and self._qr_texture.id:
      rl.unload_texture(self._qr_texture)
    self._qr_texture = None
    self._key = None
    self._url = ""
    super().hide_event()


class PairPhoneButton(BigButton):
  def __init__(self):
    super().__init__("pair phone", "Galaxy app", gui_app.texture("icons_mici/settings/bluetooth.png", 64, 64))
    self.set_click_callback(self._show_options)

  def _get_label_font_size(self):
    return 64

  def _update_state(self):
    super()._update_state()
    self.set_enabled(not ui_state.started)
    self.set_value(setup_status())

  def _show_qr(self):
    if ui_state.started:
      return
    try:
      gui_app.push_widget(PhoneQRDialog(ensure_key()))
    except Exception:
      # Do not log credential contents or put a code on a web endpoint.
      gui_app.push_widget(BigDialog("pair phone", "Could not open pairing. Check the Galaxy bridge installation."))

  def _forget(self):
    if ui_state.started:
      return
    try:
      rotate_key()
      gui_app.push_widget(BigDialog("phones forgotten", "All phones must scan a new code to use Galaxy Bluetooth."))
    except Exception:
      gui_app.push_widget(BigDialog("pair phone", "Could not forget phones. Try again."))

  def _show_options(self):
    if ui_state.started:
      return
    holder = {}

    def apply():
      if ui_state.started:
        return
      if holder["dialog"].get_selected_option() == "pair phone":
        self._show_qr()
      elif holder["dialog"].get_selected_option() == "retry setup":
        try:
          retry_setup()
          gui_app.push_widget(BigDialog("Bluetooth setup", "Setup queued. Connect comma to internet for first setup."))
        except OSError:
          gui_app.push_widget(BigDialog("Bluetooth setup", "Could not queue setup. Restart comma and try again."))
      elif holder["dialog"].get_selected_option() == "forget paired phones":
        gui_app.push_widget(BigConfirmationDialog(
          "forget all phones?\nscan again to reconnect",
          gui_app.texture("icons_mici/settings/bluetooth.png", 64, 64), self._forget, red=True))

    dialog = BigMultiOptionDialog(options=["pair phone", "forget paired phones", "retry setup"],
                                 default="pair phone", right_btn_callback=apply)
    holder["dialog"] = dialog
    gui_app.push_widget(dialog)
