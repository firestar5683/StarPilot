from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import re
import time
import uuid

from openpilot.starpilot.bluetooth.owner import BluetoothOwner, BluetoothRejected, BluetoothUnavailable
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets import DialogResult, Widget
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog, alert_dialog
from openpilot.system.ui.widgets.keyboard import Keyboard
from openpilot.system.ui.widgets.list_view import button_item, text_item
from openpilot.system.ui.widgets.scroller_tici import Scroller


def device_label(device: dict) -> str:
  name = "".join(char for char in str(device.get("name") or "") if char.isprintable()).strip()
  return (name or str(device.get("address") or "device"))[:80]


class BluetoothLarge(Widget):
  REFRESH_SECONDS = 2.0

  def __init__(self, connectivity_allowed: Callable[[], bool]):
    super().__init__()
    self.session = None
    self.active = False
    self.owner = BluetoothOwner(connectivity_allowed, session_valid=lambda identity: self.active and identity == self.session)
    self.executor = None
    self.pending = None
    self.operation = ""
    self.return_to_root = False
    self.queued = None
    self.pending_session = None
    self.status = None
    self.next_refresh = 0.0
    self.pair_dialog = None
    self.pair_dialog_id = None
    self.last_prompt_id = None
    self.scan_on_ready = False
    self._signature = None
    self._touch_held = False
    self._rebuild()

  def show_event(self):
    super().show_event()
    self.session = ('large', uuid.uuid4().hex)
    self.active = True
    self.scan_on_ready = True
    gui_app.add_nav_stack_tick(self._tick)
    self.next_refresh = 0.0
    self._scroller.show_event()
    self._tick()

  def hide_event(self):
    gui_app.remove_nav_stack_tick(self._tick)
    self.active = False
    self.session = None
    if self.executor is not None:
      self.pending = self.executor.submit(self.owner.close)
      self.operation = "close"
      self.pending_session = None
      self.executor.shutdown(wait=False, cancel_futures=False)
      self.executor = None
    self.return_to_root = False
    self.queued = None
    self.status = None
    self.scan_on_ready = False
    self.last_prompt_id = None
    self._retire_prompt()
    self._signature = None
    self._scroller.hide_event()
    super().hide_event()

  def _render(self, rect):
    for event in gui_app.mouse_events:
      if event.slot == 0:
        self._touch_held = event.left_down
    self._rebuild()
    self._scroller.render(rect)

  def _ready(self) -> bool:
    return bool(self.status and self.status.get("available") and self.queued is None and
                not self._pairing_active() and
                (self.pending is None or self.operation == "snapshot"))

  def _pairing_active(self) -> bool:
    return bool(((self.status or {}).get("pairing") or {}).get("state") == "pairing")

  def _pairing_ready(self) -> bool:
    return bool(self.active and self.session is not None and self._pairing_active() and
                self.status and self.status.get("available") and self.queued is None and
                (self.pending is None or self.operation == "snapshot"))

  def _snapshot(self):
    if self.pending is None:
      if self.executor is None:
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="big-bluetooth")
      self.pending = self.executor.submit(self.owner.snapshot, session=getattr(self, "session", None))
      self.operation = "snapshot"
      self.pending_session = getattr(self, "session", None)

  def _request(self, operation: str, *, address: str | None = None, enabled: bool | None = None,
               return_to_root: bool = False, prompt_id: str | None = None,
               accepted: bool | None = None, value: str = ""):
    pairing_action = operation in ("pairing_response", "cancel_pair")
    if not (self._pairing_ready() if pairing_action else self._ready()):
      return
    if operation == "power" and not self.status.get("parked"):
      return
    if pairing_action and operation == "pairing_response":
      prompt = ((self.status or {}).get("pairing") or {}).get("prompt")
      if prompt is None or prompt.get("id") != prompt_id:
        return
    session = getattr(self, "session", None) if operation in ("pair", "pairing_response", "cancel_pair") else None
    request = (operation, address, enabled, return_to_root, session, prompt_id, accepted, value)
    if self.pending is not None:
      self.queued = request
      self._rebuild()
      return
    self._submit_request(*request)

  def _submit_request(self, operation: str, address: str | None, enabled: bool | None, return_to_root: bool,
                      session: tuple | None, prompt_id: str | None, accepted: bool | None, value: str):
    if self.executor is None:
      return
    if operation in ("pair", "pairing_response", "cancel_pair"):
      self.pending = self.executor.submit(self.owner.request, operation, address=address, session=session,
                                          prompt_id=prompt_id, accepted=accepted, value=value)
    else:
      self.pending = self.executor.submit(self.owner.request, operation, address=address, enabled=enabled)
    self.operation = operation
    self.pending_session = getattr(self, "session", None)
    self.return_to_root = return_to_root
    self._rebuild()

  def _tick(self):
    if self.pending is not None and self.pending.done():
      future, operation = self.pending, self.operation
      self.pending = None
      self.operation = ""
      stale = getattr(self, "pending_session", None) != getattr(self, "session", None)
      self.pending_session = None
      try:
        result = future.result()
      except (BluetoothRejected, BluetoothUnavailable, ValueError):
        self.return_to_root = False
        self.queued = None
        if not stale:
          gui_app.push_widget(alert_dialog("Operation unavailable. Refresh and try again."))
      except Exception:
        self.return_to_root = False
        self.queued = None
        if not stale:
          gui_app.push_widget(alert_dialog("Adapter is unavailable. Try again later."))
      else:
        if operation != "close" and not stale:
          self.status = result
          if operation == "power":
            self.scan_on_ready = bool(result.get("powered"))
          self._retire_prompt()
          self._rebuild()
          if self.return_to_root:
            gui_app.pop_widget()
        self.return_to_root = False
      self.next_refresh = 0.0 if operation == "close" or stale else time.monotonic() + \
                          (0.25 if self._pairing_active() else self.REFRESH_SECONDS)
      if operation == "snapshot" and self.queued is not None and not stale:
        queued = self.queued
        self.queued = None
        self._submit_request(*queued)
        return
    prompt = ((self.status or {}).get("pairing") or {}).get("prompt")
    if prompt and self._pairing_ready() and prompt["id"] != self.last_prompt_id and not gui_app.mouse_events:
      self.last_prompt_id = prompt["id"]
      self._prompt(prompt)
    if (self.active and self.scan_on_ready and self._ready() and
        self.status.get("powered") and self.status.get("parked")):
      self.scan_on_ready = False
      if not self.status.get("discovering"):
        self._request("scan")
        return
    if self.pending is None and time.monotonic() >= self.next_refresh:
      self._snapshot()
      self.next_refresh = time.monotonic() + (0.25 if self._pairing_active() else self.REFRESH_SECONDS)

  def _retire_prompt(self) -> None:
    prompt = ((self.status or {}).get("pairing") or {}).get("prompt")
    if getattr(self, "pair_dialog", None) is not None and (prompt is None or prompt.get("id") != self.pair_dialog_id):
      if gui_app.get_active_widget() is self.pair_dialog:
        gui_app.pop_widget()
      self.pair_dialog = None
      self.pair_dialog_id = None

  def _show_pair_dialog(self, prompt: dict, dialog) -> None:
    if not self._pairing_ready() or ((self.status or {}).get("pairing") or {}).get("prompt") != prompt:
      return
    self.pair_dialog, self.pair_dialog_id = dialog, prompt["id"]
    gui_app.push_widget(dialog)

  def _confirm(self, question, callback):
    session = self.session
    gui_app.push_widget(ConfirmDialog(question, "Confirm", callback=lambda result:
      callback() if result == DialogResult.CONFIRM and self.active and self.session == session else None))

  def _prompt(self, prompt):
    if prompt.get("displayOnly"):
      self._show_pair_dialog(prompt, alert_dialog(f"Bluetooth code: {prompt.get('value') or ''}"))
    elif prompt.get("kind") in ("pin", "passkey"):
      session = self.session
      keyboard = Keyboard(max_text_size=6 if prompt["kind"] == "passkey" else 16, min_text_size=1, password_mode=True)
      keyboard.set_title("Bluetooth passkey" if prompt["kind"] == "passkey" else "Bluetooth PIN")
      def entered(result):
        value = keyboard.text
        valid = bool(re.fullmatch(r"[0-9]{1,6}", value)) if prompt["kind"] == "passkey" else value.isascii() and value.isprintable()
        accepted = result == DialogResult.CONFIRM and valid
        if self.active and self.session == session:
          self._request("pairing_response", prompt_id=prompt["id"], accepted=accepted, value=value if accepted else "")
        keyboard.clear()
      keyboard.set_callback(entered)
      self._show_pair_dialog(prompt, keyboard)
    else:
      question = f"Confirm Bluetooth code {prompt['value']}?" if prompt.get("value") else "Allow Bluetooth pairing?"
      dialog = ConfirmDialog(question, "Confirm", callback=lambda result:
        self._request("pairing_response", prompt_id=prompt["id"], accepted=result == DialogResult.CONFIRM))
      self._show_pair_dialog(prompt, dialog)

  def _rebuild(self):
    status = self.status or {}
    devices = tuple((item.get("address"), item.get("name"), item.get("paired"), item.get("connected"))
                    for item in status.get("devices", ()))
    signature = repr((self.status is None, status.get("available"), status.get("powered"), status.get("parked"),
                      status.get("discovering"), status.get("errorCode"), status.get("pairing"), devices))
    if hasattr(self, "_scroller") and (self._touch_held or gui_app.mouse_events):
      return
    if signature == self._signature:
      return
    self._signature = signature
    status = self.status or {}
    rows = [button_item("Bluetooth", "On" if status.get("powered") else "Off",
      description=status.get("errorCode") or ("Checking adapter" if self.status is None else None),
      callback=lambda: self._request("power", enabled=not bool((self.status or {}).get("powered"))),
      enabled=lambda: self.active and self._ready() and bool((self.status or {}).get("parked")))]
    error = {
      "radio_unavailable": "Bluetooth radio support is not installed on this device.",
      "adapter_unavailable": "No Bluetooth adapter detected. Turn Bluetooth on to start it.",
      "service_unavailable": "Bluetooth service is not responding. Try turning Bluetooth on again.",
      "radio_preference_unavailable": "The Bluetooth power setting could not be read.",
    }.get(status.get("errorCode"))
    if error:
      rows.append(text_item("Bluetooth status", error))
    elif self.status is not None and not status.get("parked"):
      rows.append(text_item("Bluetooth status", "Switch to Offroad to change Bluetooth power."))
    if status.get("powered"):
      rows.append(button_item("Nearby devices", "Stop scan" if status.get("discovering") else "Scan",
        callback=lambda: self._request("stop_scan" if (self.status or {}).get("discovering") else "scan"),
        enabled=lambda: self.active and self._ready()))
      pairing = status.get("pairing") or {}
      if pairing.get("state") == "pairing":
        prompt = pairing.get("prompt")
        rows.append(text_item("Pairing", str((prompt or {}).get("value") or "Check your device")))
        if prompt and not prompt.get("displayOnly"):
          rows.append(button_item("Pairing request", "Review", callback=lambda p=prompt: self._prompt(p), enabled=self._pairing_ready))
          rows.append(button_item("Reject pairing", "Reject", callback=lambda p=prompt:
            self._request("pairing_response", prompt_id=p["id"], accepted=False), enabled=self._pairing_ready))
        rows.append(button_item("Cancel pairing", "Cancel", callback=lambda: self._request("cancel_pair"), enabled=self._pairing_ready))
      for device in status.get("devices", ()):
        address = device.get("address")
        name = "".join(char for char in str(device.get("name") or "") if char.isprintable()).strip()
        address_name = bool(re.fullmatch(r"(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}", name))
        if not address or not device.get("paired") and (not name or address_name or name.startswith(("Audio Device ·", "Bluetooth Device ·"))):
          continue
        operation = "disconnect" if device.get("connected") else "connect" if device.get("paired") else "pair"
        rows.append(button_item(device_label(device), operation.title(), description=address,
          callback=lambda a=address, op=operation: self._request(op, address=a), enabled=lambda: self.active and self._ready()))
        if device.get("paired"):
          rows.append(button_item("Forget " + device_label(device), "Forget", callback=lambda a=address:
            self._confirm("Forget this Bluetooth device?", lambda: self._request("forget", address=a)),
            enabled=lambda: self.active and self._ready()))
    previous = getattr(self, "_scroller", None)
    self._scroller = Scroller(rows, spacing=0, line_separator=True)
    if previous is not None:
      self._scroller.scroll_panel = previous.scroll_panel
      for row in rows:
        row.set_touch_valid_callback(self._scroller.scroll_panel.is_touch_valid)
