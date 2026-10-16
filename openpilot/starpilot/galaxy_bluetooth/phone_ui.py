"""Phone-app pairing beside the existing SecretGood Bluetooth controls."""
import time

from openpilot.starpilot.galaxy_bluetooth.bootstrap import retry_setup, setup_status
from openpilot.starpilot.galaxy_bluetooth.bridge.pairing import (add_phone, describe, forget_all, load_keys, load_phones,
                                                                 qr_payload, remove_phone)


_status_read_at = -1e9
_status_text = ''


def cached_setup_status(ttl=2.):
  # Widgets poll every frame; the status file changes at most every few seconds.
  global _status_read_at, _status_text
  now = time.monotonic()
  if now - _status_read_at >= ttl:
    _status_read_at, _status_text = now, setup_status()
  return _status_text


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
    # Every scanned code is a new phone with its own key, so it can be forgotten on its own.
    phone_id, key = add_phone('Phone')  # the app sends its own name when it first connects
    code = PhoneCode(key, allowed, phone_id)
    gui_app.push_widget(code)
  except (OSError, ValueError):
    from openpilot.system.ui.widgets.confirm_dialog import alert_dialog
    gui_app.push_widget(alert_dialog('Phone pairing unavailable. Check Bluetooth setup and try again.'))


def forget_phones(allowed):
  if permitted(allowed):
    forget_all()


def forget_phone(allowed, phone_id):
  if permitted(allowed):
    remove_phone(phone_id)


def paired_phones():
  """[(unique label, phone id, detail)] for the forget menus."""
  try:
    phones = load_phones()
  except (OSError, ValueError):
    return []
  rows, seen = [], set()
  for phone in phones:
    label = describe(phone)
    if label in seen:
      label = f"{label} ({phone['id']})"
    seen.add(label)
    detail = f"last used {phone['last_used']}" if phone['last_used'] else 'not used yet'
    rows.append((label, phone['id'], detail))
  return rows


class PhoneCode:
  def __new__(cls, key, allowed, phone_id=None):
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
        self.next_check = 0.
        self.texture = make_texture(qr_payload(key, phone_id))
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
        now = time.monotonic()
        if self.key is not None and now < self.next_check:
          return
        self.next_check = now + 1.
        try:
          valid = permitted(allowed) and now < self.expires and self.key in load_keys().values()
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
    forgotten = set()
    phones = []
    for label, phone_id, detail in paired_phones():
      phone = BigButton(f'forget {label}', detail)
      phone.set_enabled(lambda phone_id=phone_id: permitted(allowed) and phone_id not in forgotten)

      def confirm(label=label, phone_id=phone_id):
        def forget_one():
          forget_phone(allowed, phone_id)
          forgotten.add(phone_id)
        gui_app.push_widget(BigConfirmationDialog(f'forget {label}?', gui_app.texture('icons_mici/settings/bluetooth.png', 64, 64),
                                                  forget_one, red=True))
      phone.set_click_callback(confirm)
      phones.append(phone)
    forget = BigButton('forget all phones', 'iPhone and Android pair again')
    forget.set_enabled(lambda: permitted(allowed))
    forget.set_click_callback(lambda: gui_app.push_widget(BigConfirmationDialog(
      'forget all phones?', gui_app.texture('icons_mici/settings/bluetooth.png', 64, 64),
      lambda: forget_phones(allowed), red=True)))
    retry = BigButton('retry phone setup', 'restart the phone bridge')
    retry.set_enabled(lambda: permitted(allowed))
    retry.set_click_callback(lambda: retry_setup() if permitted(allowed) else None)
    page._scroller.add_widgets([pair, *phones, forget, retry, GreyBigButton('phone bridge', cached_setup_status())])
    gui_app.push_widget(page)

  class PhoneButton(BigButton):
    def _update_state(self):
      super()._update_state()
      status = cached_setup_status()
      if status != self.value:
        self.set_value(status)

  button = PhoneButton('StarPilot phone app', 'iPhone and Android', scroll=True)
  button.set_enabled(lambda: permitted(allowed))
  button.set_click_callback(options)
  return button


def large_phone_rows(allowed):
  from openpilot.system.ui.lib.application import gui_app
  from openpilot.system.ui.widgets import DialogResult
  from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
  from openpilot.system.ui.widgets.list_view import button_item

  def forget():
    gui_app.push_widget(ConfirmDialog('Forget all StarPilot phones? iPhone and Android must pair again.', 'Forget',
      callback=lambda result: forget_phones(allowed) if result == DialogResult.CONFIRM else None))

  def forget_one():
    from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
    rows = {label: phone_id for label, phone_id, _ in paired_phones()}
    if not rows:
      from openpilot.system.ui.widgets.confirm_dialog import alert_dialog
      gui_app.push_widget(alert_dialog('No phones are paired.'))
      return

    def chosen(result):
      label = picker.selection
      if result != DialogResult.CONFIRM or label not in rows:
        return
      gui_app.push_widget(ConfirmDialog(f'Forget {label}? Only this phone must pair again.', 'Forget',
        callback=lambda confirmed: forget_phone(allowed, rows[label]) if confirmed == DialogResult.CONFIRM else None))
    picker = MultiOptionDialog('Forget which phone?', list(rows), callback=chosen)
    gui_app.push_widget(picker)

  return [button_item('Pair StarPilot iPhone app', 'Pair', callback=lambda: open_pairing(allowed), enabled=lambda: permitted(allowed)),
          button_item('Forget a StarPilot phone', 'Choose', callback=forget_one, enabled=lambda: permitted(allowed)),
          button_item('Forget all StarPilot phones', 'Forget', callback=forget, enabled=lambda: permitted(allowed)),
          button_item('StarPilot phone bridge', 'Retry', callback=lambda: retry_setup() if permitted(allowed) else None,
                      enabled=lambda: permitted(allowed), description=cached_setup_status())]
