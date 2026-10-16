"""Phone-app pairing beside the existing SecretGood Bluetooth controls."""
import time

from openpilot.starpilot.galaxy_bluetooth.bootstrap import retry_setup, setup_status
from openpilot.starpilot.galaxy_bluetooth.bridge.pairing import ensure_key, load_key, rotate_key, qr_payload


def permitted(allowed):
  try:
    return bool(allowed())
  except Exception:
    return False


def open_pairing(allowed):
  if not permitted(allowed):
    return
  from openpilot.system.ui.lib.application import gui_app
  try:
    gui_app.push_widget(PhoneCode(ensure_key(), allowed))
  except (OSError, ValueError):
    from openpilot.system.ui.widgets.confirm_dialog import alert_dialog
    gui_app.push_widget(alert_dialog('Phone pairing unavailable. Check Bluetooth setup and try again.'))


def forget_phones(allowed):
  if permitted(allowed):
    rotate_key()


class PhoneCode:
  def __new__(cls, key, allowed):
    import pyray as rl
    from openpilot.common.qrcode import make_texture
    from openpilot.system.ui.lib.application import gui_app, FontWeight
    from openpilot.system.ui.widgets import Widget
    from openpilot.system.ui.widgets.button import Button

    class Code(Widget):
      def __init__(self):
        super().__init__()
        self.key = key
        self.expires = time.monotonic() + 120
        self.texture = make_texture(qr_payload(key))
        rl.set_texture_filter(self.texture, rl.TextureFilter.TEXTURE_FILTER_POINT)
        self.close_button = self._child(Button('Close', gui_app.pop_widget, font_size=42))

      def _clear(self):
        if self.texture is not None:
          rl.unload_texture(self.texture)
          self.texture = None
        self.key = None

      def hide_event(self):
        self._clear()
        super().hide_event()

      def _update_state(self):
        try:
          valid = permitted(allowed) and time.monotonic() < self.expires and load_key() == self.key
        except (OSError, ValueError, KeyError):
          valid = False
        if not valid:
          self._clear()
          if gui_app.get_active_widget() is self:
            gui_app.pop_widget()

      def _render(self, rect):
        rl.draw_rectangle_rec(rect, rl.BLACK)
        font = gui_app.font(FontWeight.MEDIUM)
        compact = rect.height < 600
        size = min(rect.height * .64, rect.width * .48)
        x = rect.x + (rect.width - size) / 2
        y = rect.y + rect.height * .15
        rl.draw_text_ex(font, 'Scan in the StarPilot iPhone app', rl.Vector2(rect.x + 28, rect.y + 16), 26 if compact else 48, 0, rl.WHITE)
        if self.texture is not None:
          rl.draw_texture_pro(self.texture, rl.Rectangle(0, 0, self.texture.width, self.texture.height),
                              rl.Rectangle(x, y, size, size), rl.Vector2(0, 0), 0, rl.WHITE)
        rl.draw_text_ex(font, 'Keep this code private', rl.Vector2(rect.x + 28, rect.y + rect.height - (62 if compact else 100)),
                        22 if compact else 34, 0, rl.LIGHTGRAY)
        self.close_button.render(rl.Rectangle(rect.x + rect.width - (150 if compact else 300),
                                             rect.y + rect.height - (66 if compact else 120),
                                             130 if compact else 260, 54 if compact else 90))

    return Code()


def compact_phone_button(allowed):
  from openpilot.selfdrive.ui.mici.widgets.button import BigButton, GreyBigButton
  from openpilot.selfdrive.ui.mici.widgets.dialog import BigConfirmationDialog
  from openpilot.system.ui.lib.application import gui_app
  from openpilot.system.ui.widgets.scroller import NavScroller

  def options():
    page = NavScroller()
    pair = BigButton('pair iPhone app', 'scan a private code')
    pair.set_enabled(lambda: permitted(allowed))
    pair.set_click_callback(lambda: open_pairing(allowed))
    forget = BigButton('forget all app links', 'phones must scan again')
    forget.set_enabled(lambda: permitted(allowed))
    forget.set_click_callback(lambda: gui_app.push_widget(BigConfirmationDialog(
      'forget all app links?', gui_app.texture('icons_mici/settings/bluetooth.png', 64, 64),
      lambda: forget_phones(allowed), red=True)))
    retry = BigButton('retry phone setup', 'internet needed for first setup')
    retry.set_enabled(lambda: permitted(allowed))
    retry.set_click_callback(lambda: retry_setup() if permitted(allowed) else None)
    page._scroller.add_widgets([pair, forget, retry, GreyBigButton('phone bridge', setup_status())])
    gui_app.push_widget(page)

  class PhoneButton(BigButton):
    def _update_state(self):
      super()._update_state()
      self.set_value(setup_status())

  button = PhoneButton('StarPilot iPhone app', 'pair or forget app links', scroll=True)
  button.set_enabled(lambda: permitted(allowed))
  button.set_click_callback(options)
  return button


def large_phone_rows(allowed):
  from openpilot.system.ui.lib.application import gui_app
  from openpilot.system.ui.widgets import DialogResult
  from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
  from openpilot.system.ui.widgets.list_view import button_item, text_item

  def forget():
    gui_app.push_widget(ConfirmDialog('Forget all StarPilot app links? Phones must scan a new code.', 'Forget',
      callback=lambda result: forget_phones(allowed) if result == DialogResult.CONFIRM else None))

  return [button_item('StarPilot iPhone app', 'Pair', callback=lambda: open_pairing(allowed), enabled=lambda: permitted(allowed)),
          button_item('Forget all app links', 'Forget', callback=forget, enabled=lambda: permitted(allowed)),
          button_item('Phone bridge setup', 'Retry', callback=lambda: retry_setup() if permitted(allowed) else None,
                      enabled=lambda: permitted(allowed), description=setup_status())]
