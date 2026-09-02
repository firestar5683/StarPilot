from __future__ import annotations

from dataclasses import dataclass
from functools import partial
import threading

import pyray as rl

from openpilot.starpilot.system.bluetooth.protocol import BluetoothDevice, BluetoothStatus
from openpilot.system.ui.lib.application import FontWeight, MousePos, gui_app
from openpilot.system.ui.lib.bluetooth_manager import BluetoothManager
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.scroll_panel import GuiScrollPanel
from openpilot.system.ui.widgets import DialogResult, Widget
from openpilot.system.ui.widgets.button import Button, ButtonStyle
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog, alert_dialog
from openpilot.system.ui.widgets.keyboard import Keyboard
from openpilot.system.ui.widgets.label import gui_label, gui_text_box
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
from openpilot.system.ui.widgets.toggle import Toggle


HEADER_HEIGHT = 180
ITEM_HEIGHT = 160
HEADER_PADDING = 40
SCAN_BUTTON_WIDTH = 260
FORGET_BUTTON_WIDTH = 180
ACTION_GAP = 35

# Match the Network panel: the Settings surface stays pure black and list rows are transparent over it.
PANEL_BACKGROUND = rl.BLACK
DIALOG_BACKGROUND = rl.Color(27, 27, 27, 255)
ROW_BORDER = rl.LIGHTGRAY
TEXT_SECONDARY = rl.Color(170, 170, 170, 255)
TEXT_DISABLED = rl.Color(150, 150, 150, 255)
TEXT_CONNECTED = rl.Color(113, 209, 135, 255)


def device_status_text(device: BluetoothDevice, operation: str, selected_audio: str) -> str:
  """Return the concise, state-first label shown below a Bluetooth device name."""
  if operation:
    return operation.capitalize() + "..."

  capabilities = []
  if device.audio:
    capabilities.append(tr("audio output") if selected_audio.upper() == device.address.upper() else tr("audio"))
  if device.controller:
    capabilities.append(tr("controller"))
  if device.serial:
    capabilities.append(tr("serial"))
  capability_text = " / ".join(capabilities)

  if device.connected:
    return tr("Connected") + (f" / {capability_text}" if capability_text else "")
  if device.paired:
    if device.serial:
      return tr("Paired - tap to use ELM327") + (f" / {capability_text}" if capability_text else "")
    return tr("Paired - tap to connect")
  return tr("Tap to pair") + (f" / {capability_text}" if capability_text else "")


def device_action_allowed(device: BluetoothDevice, operation: str, offroad: bool) -> bool:
  """Mirror the daemon's operation policy before a row can receive a tap."""
  if operation:
    return False
  if device.serial and not offroad:
    return False
  if not offroad and not device.paired:
    return False
  return True


@dataclass(frozen=True)
class _DeviceViewState:
  device: BluetoothDevice
  operation: str
  selected_audio: str
  offroad: bool


class BluetoothDeviceRow(Widget):
  """A Wi-Fi-style, scroll-safe row with a primary device action and optional forget button."""
  def __init__(self, address: str, on_select, on_forget):
    super().__init__()
    self.address = address
    self._on_select = on_select
    self._on_forget = on_forget
    self._state: _DeviceViewState | None = None
    self._forget_button = Button(tr("Forget"), on_forget, button_style=ButtonStyle.FORGET_WIFI, font_size=42)
    self._forget_rect = rl.Rectangle(0, 0, 0, 0)

  def update(self, state: _DeviceViewState) -> None:
    self._state = state
    self.set_enabled(device_action_allowed(state.device, state.operation, state.offroad))

  def set_touch_valid_callback(self, touch_callback):
    super().set_touch_valid_callback(touch_callback)
    self._forget_button.set_touch_valid_callback(touch_callback)

  def _show_forget(self) -> bool:
    state = self._state
    return bool(state and state.device.paired and state.offroad and not state.operation)

  def _update_layout_rects(self) -> None:
    if self._show_forget():
      self._forget_rect = rl.Rectangle(
        self._rect.x + self._rect.width - FORGET_BUTTON_WIDTH,
        self._rect.y + (self._rect.height - 80) / 2,
        FORGET_BUTTON_WIDTH,
        80,
      )
    else:
      self._forget_rect = rl.Rectangle(0, 0, 0, 0)

  def _handle_mouse_release(self, mouse_pos: MousePos) -> None:
    if self._show_forget() and rl.check_collision_point_rec(mouse_pos, self._forget_rect):
      return
    self._on_select()

  def _render(self, rect: rl.Rectangle):
    state = self._state
    if state is None:
      return

    self._update_layout_rects()
    enabled = self.enabled
    rl.draw_rectangle_rec(rect, PANEL_BACKGROUND)

    right_padding = FORGET_BUTTON_WIDTH + ACTION_GAP if self._show_forget() else HEADER_PADDING
    text_rect = rl.Rectangle(rect.x + HEADER_PADDING, rect.y + 18, rect.width - HEADER_PADDING - right_padding, 62)
    text_color = rl.WHITE if enabled else TEXT_DISABLED
    gui_label(text_rect, state.device.name, font_size=54, color=text_color, font_weight=FontWeight.MEDIUM)

    status_rect = rl.Rectangle(text_rect.x, rect.y + 82, text_rect.width, 52)
    status = device_status_text(state.device, state.operation, state.selected_audio)
    status_color = TEXT_CONNECTED if state.device.connected and not state.operation else TEXT_SECONDARY
    if not enabled:
      status_color = TEXT_DISABLED
    gui_label(status_rect, status, font_size=39, color=status_color)

    if self._show_forget():
      self._forget_button.set_enabled(enabled)
      self._forget_button.set_parent_rect(self._parent_rect or rect)
      self._forget_button.render(self._forget_rect)


class BluetoothAudioTestDialog(Widget):
  """Shows the existing delayed Bluetooth audio test without introducing another backend state."""
  def __init__(self, manager: BluetoothManager):
    super().__init__()
    self._manager = manager
    self._error = ""
    self._done_button = Button(tr("Done"), gui_app.pop_widget, button_style=ButtonStyle.PRIMARY)

  def _update_state(self):
    if not self._error:
      self._error = self._manager.consume_error()

  def _render(self, rect: rl.Rectangle):
    dialog_rect = rl.Rectangle(rect.x + rect.width * 0.25, rect.y + rect.height * 0.3, rect.width * 0.5, rect.height * 0.4)
    rl.draw_rectangle_rounded(dialog_rect, 0.04, 20, DIALOG_BACKGROUND)

    if self._error:
      title = tr("Bluetooth audio test failed")
      detail = self._error
    else:
      phase = self._manager.audio_test_phase()
      title = tr("Bluetooth audio test")
      if phase == "NOW":
        detail = tr("Playing now")
      elif phase == "complete":
        detail = tr("Complete")
      else:
        detail = tr("Playing in {}...").format(phase)

    gui_label(rl.Rectangle(dialog_rect.x + 50, dialog_rect.y + 55, dialog_rect.width - 100, 80), title,
              font_size=62, font_weight=FontWeight.BOLD, alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER)
    gui_label(rl.Rectangle(dialog_rect.x + 50, dialog_rect.y + 155, dialog_rect.width - 100, 80), detail,
              font_size=50, color=TEXT_SECONDARY, alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER)

    button_rect = rl.Rectangle(dialog_rect.x + 50, dialog_rect.y + dialog_rect.height - 150, dialog_rect.width - 100, 100)
    self._done_button.render(button_rect)


class ELM327Dialog(Widget):
  """Ephemeral, offroad-only ELM327 controls opened from the Bluetooth panel."""
  def __init__(self, manager: BluetoothManager, device: BluetoothDevice):
    super().__init__()
    self._manager = manager
    self._address = device.address
    self._name = device.name
    self._state_lock = threading.Lock()
    self._closed = False
    self._connecting = True
    self._adapter = ""
    self._response = ""
    self._codes: list[str] | None = None
    self._error = ""
    self._keyboard = Keyboard(max_text_size=256, min_text_size=1, password_mode=False)
    self._read_button = Button(tr("Read Codes"), self._read_codes, button_style=ButtonStyle.PRIMARY, font_size=42)
    self._command_button = Button(tr("Send Command"), self._send_command, button_style=ButtonStyle.NORMAL, font_size=42)
    self._done_button = Button(tr("Done"), gui_app.pop_widget, button_style=ButtonStyle.NORMAL, font_size=42)

  def show_event(self):
    super().show_event()
    self._manager.elm_open(self._address, callback=self._on_open_result)

  def hide_event(self):
    with self._state_lock:
      self._closed = True
    self._manager.elm_close(self._address)
    super().hide_event()

  def _on_open_result(self, result, error):
    should_close = False
    with self._state_lock:
      self._connecting = False
      if error:
        self._error = error
      else:
        self._adapter = str((result or {}).get("adapter", ""))
        self._response = ""
        self._codes = None
        should_close = self._closed
    if should_close:
      self._manager.elm_close(self._address)

  def _on_command_result(self, command: str, result, error):
    with self._state_lock:
      if error:
        self._error = error
      else:
        response = str((result or {}).get("response", ""))
        self._response = f"{command}\n{response}".strip()

  def _on_read_result(self, result, error):
    with self._state_lock:
      if error:
        self._error = error
      else:
        self._codes = [str(code) for code in (result or {}).get("codes", [])]
        self._response = str((result or {}).get("raw", ""))

  def _send_command(self):
    with self._state_lock:
      if self._connecting or self._error or self._closed:
        return
    self._keyboard.reset(min_text_size=1)
    self._keyboard.set_title(tr("Send ELM327 command"), tr("Raw commands are available offroad only."))
    self._keyboard.set_callback(self._on_command_entered)
    gui_app.push_widget(self._keyboard)

  def _on_command_entered(self, result: DialogResult):
    command = self._keyboard.text.strip()
    self._keyboard.clear()
    if result != DialogResult.CONFIRM or not command:
      return
    with self._state_lock:
      self._response = f"{command}\nSending..."
      self._error = ""
    self._manager.elm_command(self._address, command, callback=partial(self._on_command_result, command))

  def _read_codes(self):
    with self._state_lock:
      self._codes = None
      self._error = ""
    self._manager.elm_read_dtcs(self._address, callback=self._on_read_result)

  def _update_state(self):
    with self._state_lock:
      ready = bool(self._adapter) and not self._connecting and not self._error and not self._closed
    status = self._manager.status
    operation = self._manager.operation_for(self._address)
    enabled = ready and status.offroad and not operation
    self._read_button.set_enabled(enabled)
    self._command_button.set_enabled(enabled)
    self._done_button.set_enabled(True)

  def _render(self, rect: rl.Rectangle):
    dialog_rect = rl.Rectangle(rect.x + 90, rect.y + 60, rect.width - 180, rect.height - 120)
    rl.draw_rectangle_rounded(dialog_rect, 0.03, 20, DIALOG_BACKGROUND)

    with self._state_lock:
      connecting = self._connecting
      adapter = self._adapter
      response = self._response
      codes = self._codes
      error = self._error
    gui_label(rl.Rectangle(dialog_rect.x + 45, dialog_rect.y + 35, dialog_rect.width - 90, 70), tr("ELM327"),
              font_size=62, font_weight=FontWeight.BOLD)
    gui_label(rl.Rectangle(dialog_rect.x + 45, dialog_rect.y + 105, dialog_rect.width - 90, 52), self._name,
              font_size=42, color=TEXT_SECONDARY)
    identity = tr("Connecting...") if connecting else adapter
    gui_label(rl.Rectangle(dialog_rect.x + 45, dialog_rect.y + 157, dialog_rect.width - 90, 52), identity,
              font_size=42, color=TEXT_CONNECTED if adapter else TEXT_SECONDARY)

    button_y = dialog_rect.y + 225
    button_width = (dialog_rect.width - 135) / 3
    self._read_button.render(rl.Rectangle(dialog_rect.x + 45, button_y, button_width, 90))
    self._command_button.render(rl.Rectangle(dialog_rect.x + 60 + button_width, button_y, button_width, 90))
    self._done_button.render(rl.Rectangle(dialog_rect.x + 75 + button_width * 2, button_y, button_width, 90))

    if error:
      gui_text_box(rl.Rectangle(dialog_rect.x + 45, dialog_rect.y + 330, dialog_rect.width - 90, 80), error,
                   font_size=38, color=rl.Color(255, 150, 150, 255))
    if codes is not None:
      gui_label(rl.Rectangle(dialog_rect.x + 45, dialog_rect.y + 410, 300, 45), tr("Stored Codes"),
                font_size=38, font_weight=FontWeight.BOLD)
      code_text = "\n".join(codes) if codes else tr("No stored codes reported.")
      gui_text_box(rl.Rectangle(dialog_rect.x + 45, dialog_rect.y + 455, dialog_rect.width - 90, 95), code_text,
                   font_size=38, color=TEXT_SECONDARY)
    gui_label(rl.Rectangle(dialog_rect.x + 45, dialog_rect.y + 560, 300, 45), tr("Response"),
              font_size=38, font_weight=FontWeight.BOLD)
    gui_text_box(rl.Rectangle(dialog_rect.x + 45, dialog_rect.y + 605, dialog_rect.width - 90, dialog_rect.height - 650),
                 response or "—", font_size=36, color=TEXT_SECONDARY)


class BluetoothManagerUI(Widget):
  """Big UI Bluetooth settings panel backed by the existing Bluetooth manager daemon."""
  def __init__(self, manager: BluetoothManager):
    super().__init__()
    self._manager = manager
    self._scroll_panel = GuiScrollPanel()
    self._power_toggle = Toggle(initial_state=False, callback=self._toggle_power)
    self._scan_button = Button(tr("Scan"), self._scan, button_style=ButtonStyle.NORMAL, font_size=42)
    self._device_rows: dict[str, BluetoothDeviceRow] = {}
    self._pending_power: bool | None = None
    self._scan_pending = False
    self._scan_on_ready = False
    self._last_prompt_id = ""
    self._last_status_error = ""
    self._last_operation_error = ""
    self._keyboard = Keyboard(max_text_size=32, min_text_size=1, password_mode=False)

  def show_event(self):
    super().show_event()
    self._manager.set_active(True)
    self._scan_on_ready = True

  def hide_event(self):
    status = self._manager.status
    if status.discovering and status.offroad:
      self._manager.set_scanning(False)
    self._scan_pending = False
    self._manager.set_active(False)
    super().hide_event()

  def _toggle_power(self, enabled: bool):
    status = self._manager.status
    if not status.available or not status.offroad:
      self._power_toggle.set_state(status.enabled)
      return
    self._pending_power = enabled
    self._scan_on_ready = enabled
    self._manager.set_power(enabled)

  def _scan(self):
    status = self._manager.status
    if status.enabled and status.offroad and not status.discovering and not self._scan_pending:
      self._scan_pending = True
      self._manager.set_scanning(True)

  def _operation_for(self, device: BluetoothDevice, status: BluetoothStatus) -> str:
    operation = self._manager.operation_for(device.address)
    if not operation and status.pairing_address.upper() == device.address.upper():
      operation = tr("pairing")
    return operation

  def _sync_power(self, status: BluetoothStatus) -> None:
    if self._pending_power is not None and status.enabled == self._pending_power:
      self._pending_power = None
    if status.discovering or not status.enabled:
      self._scan_pending = False
    if self._pending_power is None:
      self._power_toggle.set_state(status.enabled)
    self._power_toggle.set_enabled(status.available and status.offroad and self._pending_power is None)
    self._scan_button.set_enabled(status.enabled and status.offroad and not status.discovering and not self._scan_pending)
    self._scan_button.set_text(tr("Scanning") if status.discovering or self._scan_pending else tr("Scan"))

  def _sync_rows(self, status: BluetoothStatus) -> list[BluetoothDeviceRow]:
    visible_rows = []
    known_addresses = set()
    for device in status.devices:
      address = device.address.upper()
      known_addresses.add(address)
      row = self._device_rows.get(address)
      if row is None:
        row = BluetoothDeviceRow(
          address,
          on_select=partial(self._select_device, address),
          on_forget=partial(self._confirm_forget, address),
        )
        row.set_touch_valid_callback(self._scroll_panel.is_touch_valid)
        self._device_rows[address] = row
      row.update(_DeviceViewState(device, self._operation_for(device, status), status.selected_audio, status.offroad))
      visible_rows.append(row)
    self._device_rows = {address: row for address, row in self._device_rows.items() if address in known_addresses}
    return visible_rows

  def _select_device(self, address: str):
    device = self._find_device(address)
    status = self._manager.status
    if device is None or not device_action_allowed(device, self._operation_for(device, status), status.offroad):
      return
    if not device.paired:
      self._manager.pair(device.address)
    elif device.serial:
      gui_app.push_widget(ELM327Dialog(self._manager, device))
    elif not device.connected:
      self._manager.connect(device.address)
    else:
      self._show_device_actions(device)

  def _find_device(self, address: str) -> BluetoothDevice | None:
    return next((device for device in self._manager.status.devices if device.address.upper() == address.upper()), None)

  def _show_device_actions(self, device: BluetoothDevice):
    status = self._manager.status
    options = [tr("Disconnect")]
    if device.audio and status.offroad:
      selected = status.selected_audio.upper() == device.address.upper()
      options.append(tr("Stop using for audio") if selected else tr("Use for audio"))
      options.append(tr("Test audio"))

    def apply(result: DialogResult):
      if result != DialogResult.CONFIRM:
        return
      if dialog.selection == tr("Disconnect"):
        self._manager.disconnect(device.address)
      elif dialog.selection == tr("Use for audio"):
        self._manager.select_audio(device.address)
      elif dialog.selection == tr("Stop using for audio"):
        self._manager.select_audio("")
      elif dialog.selection == tr("Test audio"):
        self._manager.test_audio(device.address)
        gui_app.push_widget(BluetoothAudioTestDialog(self._manager))

    dialog = MultiOptionDialog(device.name, options, options[0], callback=apply)
    gui_app.push_widget(dialog)

  def _confirm_forget(self, address: str):
    device = self._find_device(address)
    status = self._manager.status
    if device is None or not device.paired or not status.offroad:
      return

    def apply(result: DialogResult):
      if result == DialogResult.CONFIRM:
        self._manager.forget(device.address)

    gui_app.push_widget(ConfirmDialog(tr("Forget Bluetooth device \"{}\"?").format(device.name), tr("Forget"), callback=apply))

  def _handle_prompt(self, status: BluetoothStatus):
    prompt = status.prompt
    if prompt is None:
      self._last_prompt_id = ""
      return
    prompt_id = str(prompt.get("id", ""))
    if not prompt_id or prompt_id == self._last_prompt_id:
      return
    self._last_prompt_id = prompt_id

    name = str(prompt.get("name") or tr("Bluetooth device"))
    kind = str(prompt.get("kind") or "")
    value = str(prompt.get("value") or "")
    if prompt.get("display_only"):
      message = value if value else tr("Pairing with {}.").format(name)
      gui_app.push_widget(alert_dialog(message))
    elif kind in ("pin", "passkey"):
      self._keyboard.reset(min_text_size=1)
      self._keyboard.set_title(tr("Enter {} for {}").format(kind, name), "")
      self._keyboard.set_callback(partial(self._on_pairing_value, prompt_id))
      gui_app.push_widget(self._keyboard)
    else:
      message = tr("Pair with {}?").format(name)
      if value:
        message += f"\n{value}"
      gui_app.push_widget(ConfirmDialog(message, tr("Pair"), callback=partial(self._on_pairing_confirmation, prompt_id)))

  def _on_pairing_value(self, prompt_id: str, result: DialogResult):
    value = self._keyboard.text
    self._keyboard.clear()
    self._manager.respond(prompt_id, result == DialogResult.CONFIRM, value if result == DialogResult.CONFIRM else "")

  def _on_pairing_confirmation(self, prompt_id: str, result: DialogResult):
    self._manager.respond(prompt_id, result == DialogResult.CONFIRM)

  def _show_errors(self, status: BluetoothStatus) -> bool:
    operation_error = self._manager.consume_error()
    if operation_error:
      self._pending_power = None
      self._scan_pending = False
      if operation_error != self._last_operation_error:
        self._last_operation_error = operation_error
        gui_app.push_widget(alert_dialog(operation_error))
        return True
      return False
    self._last_operation_error = ""
    if not status.error:
      self._last_status_error = ""
      return False
    if status.error != self._last_status_error:
      self._last_status_error = status.error
      gui_app.push_widget(alert_dialog(status.error))
      return True
    return False

  def _update_state(self):
    status = self._manager.status
    self._sync_power(status)
    if self._scan_on_ready and status.available and status.enabled:
      self._scan_on_ready = False
      if status.offroad and not status.discovering:
        self._scan()
    if not self._show_errors(status):
      self._handle_prompt(status)

  def _render(self, rect: rl.Rectangle):
    status = self._manager.status
    header_rect = rl.Rectangle(rect.x, rect.y, rect.width, HEADER_HEIGHT)
    self._render_header(header_rect, status)

    content_rect = rl.Rectangle(rect.x, rect.y + HEADER_HEIGHT, rect.width, rect.height - HEADER_HEIGHT)
    if not status.available:
      gui_label(content_rect, tr("Bluetooth is not available on this device."), font_size=62,
                color=TEXT_SECONDARY, alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER)
      return
    if not status.enabled:
      gui_label(content_rect, tr("Bluetooth is off."), font_size=62, color=TEXT_SECONDARY,
                alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER)
      return

    rows = self._sync_rows(status)
    if not rows:
      message = tr("Scanning for Bluetooth devices...") if status.discovering else tr("No Bluetooth devices found.")
      gui_label(content_rect, message, font_size=62, color=TEXT_SECONDARY, alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER)
      return
    self._render_device_list(content_rect, rows)

  def _render_header(self, rect: rl.Rectangle, status: BluetoothStatus):
    rl.draw_rectangle_rec(rect, PANEL_BACKGROUND)
    line_y = int(rect.y + rect.height - 1)
    rl.draw_line(int(rect.x), line_y, int(rect.x + rect.width), line_y, ROW_BORDER)

    gui_label(rl.Rectangle(rect.x + HEADER_PADDING, rect.y + 26, 500, 68), tr("Bluetooth"), font_size=64, font_weight=FontWeight.BOLD)
    subtitle = tr("On") if status.enabled else tr("Off")
    if status.enabled and not status.offroad:
      subtitle += " - " + tr("Limited while driving")
    gui_label(rl.Rectangle(rect.x + HEADER_PADDING, rect.y + 104, 650, 44), subtitle, font_size=40, color=TEXT_SECONDARY)

    toggle_rect = rl.Rectangle(rect.x + rect.width - HEADER_PADDING - 160, rect.y + (rect.height - 80) / 2, 160, 80)
    self._power_toggle.render(toggle_rect)
    scan_rect = rl.Rectangle(toggle_rect.x - ACTION_GAP - SCAN_BUTTON_WIDTH, rect.y + (rect.height - 100) / 2, SCAN_BUTTON_WIDTH, 100)
    self._scan_button.render(scan_rect)

  def _render_device_list(self, rect: rl.Rectangle, rows: list[BluetoothDeviceRow]):
    content_rect = rl.Rectangle(rect.x, rect.y, rect.width, len(rows) * ITEM_HEIGHT)
    offset = self._scroll_panel.update(rect, content_rect)

    rl.begin_scissor_mode(int(rect.x), int(rect.y), int(rect.width), int(rect.height))
    for index, row in enumerate(rows):
      item_rect = rl.Rectangle(rect.x, rect.y + index * ITEM_HEIGHT + offset, rect.width, ITEM_HEIGHT)
      if not rl.check_collision_recs(item_rect, rect):
        continue
      row.set_parent_rect(rect)
      row.render(item_rect)
      if index < len(rows) - 1:
        line_y = int(item_rect.y + item_rect.height - 1)
        rl.draw_line(int(item_rect.x), line_y, int(item_rect.x + item_rect.width), line_y, ROW_BORDER)
    rl.end_scissor_mode()
