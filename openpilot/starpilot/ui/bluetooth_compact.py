"""C4 Bluetooth controls backed by the shared BlueZ owner."""

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
import re
import time
import uuid

from openpilot.selfdrive.ui.mici.widgets.button import BigButton, GreyBigButton
from openpilot.selfdrive.ui.mici.widgets.dialog import BigConfirmationDialog, BigDialog, BigInputDialog
from openpilot.starpilot.bluetooth.owner import BluetoothOwner, BluetoothRejected, BluetoothUnavailable
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets.scroller import NavScroller


def device_label(device: dict) -> str:
  name = "".join(char for char in str(device.get("name") or "") if char.isprintable()).strip()
  return (name or str(device.get("address") or "device"))[:80]


class BluetoothCompact(NavScroller):
  REFRESH_SECONDS = 2.0

  def __init__(self, connectivity_allowed: Callable[[], bool]):
    super().__init__()
    self.session: tuple | None = None
    self.active = False
    self.owner = BluetoothOwner(connectivity_allowed,
                                session_valid=lambda identity: self.active and identity == self.session)
    self.executor: ThreadPoolExecutor | None = None
    self.pending: Future | None = None
    self.operation = ""
    self.return_to_root = False
    self.queued: tuple | None = None
    self.pending_session: tuple | None = None
    self.status: dict | None = None
    self.next_refresh = 0.0
    self.pair_dialog = None
    self.pair_dialog_id: str | None = None
    self.icon = gui_app.texture("icons_mici/settings/bluetooth.png", 64, 64)
    self._rebuild()

  def show_event(self):
    super().show_event()
    self.session = ('compact', uuid.uuid4().hex)
    self.active = True
    gui_app.add_nav_stack_tick(self._tick)
    self.next_refresh = 0.0
    if self.status is None:
      self._rebuild()
    self._tick()

  def hide_event(self):
    gui_app.remove_nav_stack_tick(self._tick)
    self.active = False
    self.session = None
    executor = self.executor
    if executor is not None:
      self.pending = executor.submit(self.owner.close)
      self.operation = "close"
      self.pending_session = None
      executor.shutdown(wait=False, cancel_futures=False)
      self.executor = None
    self.return_to_root = False
    self.queued = None
    self.status = None
    self.pair_dialog = None
    self.pair_dialog_id = None
    super().hide_event()

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
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="c4-bluetooth")
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
          gui_app.push_widget(BigDialog("bluetooth", "Operation unavailable. Refresh and try again."))
      except Exception:
        self.return_to_root = False
        self.queued = None
        if not stale:
          gui_app.push_widget(BigDialog("bluetooth", "Adapter is unavailable. Try again later."))
      else:
        if operation != "close" and not stale:
          self.status = result
          self._retire_prompt()
          self._rebuild()
          if self.return_to_root:
            gui_app.pop_widgets_to(self)
        self.return_to_root = False
      self.next_refresh = 0.0 if operation == "close" or stale else time.monotonic() + \
                          (0.25 if self._pairing_active() else self.REFRESH_SECONDS)
      if operation == "snapshot" and self.queued is not None and not stale:
        queued = self.queued
        self.queued = None
        self._submit_request(*queued)
        return
    if self.pending is None and time.monotonic() >= self.next_refresh:
      self._snapshot()
      self.next_refresh = time.monotonic() + (0.25 if self._pairing_active() else self.REFRESH_SECONDS)

  def _retire_prompt(self) -> None:
    prompt = ((self.status or {}).get("pairing") or {}).get("prompt")
    if getattr(self, "pair_dialog", None) is not None and (prompt is None or prompt.get("id") != self.pair_dialog_id):
      if gui_app.get_active_widget() is self.pair_dialog:
        gui_app.pop_widgets_to(self)
      self.pair_dialog = None
      self.pair_dialog_id = None

  def _show_pair_dialog(self, prompt: dict, dialog) -> None:
    if not self._pairing_ready() or ((self.status or {}).get("pairing") or {}).get("prompt") != prompt:
      return
    self.pair_dialog, self.pair_dialog_id = dialog, prompt["id"]
    gui_app.push_widget(dialog)

  def _pairing_cards(self) -> list:
    pairing = (self.status or {}).get("pairing")
    if pairing is None:
      return []
    state = pairing.get("state")
    if state != "pairing":
      return [GreyBigButton("pairing", "paired" if state == "paired" else "ended")]
    address = pairing.get("address")
    device = next((item for item in (self.status or {}).get("devices", ()) if item.get("address") == address), None)
    cards = [GreyBigButton("pairing", device_label(device or {"address": address}))]
    prompt = pairing.get("prompt")
    if prompt is None:
      cards.append(GreyBigButton("waiting", "check your device"))
    elif prompt.get("displayOnly"):
      cards.append(GreyBigButton("code shown on this device", str(prompt.get("value") or "")))
    elif prompt.get("kind") in ("confirmation", "authorization"):
      code = str(prompt.get("value") or "")
      cards.append(GreyBigButton("match this code" if code else "pairing request", code or "Confirm on both devices"))
      accept = BigButton("confirm match" if code else "allow pairing", "review and confirm")
      accept.set_click_callback(lambda p=prompt: self._show_pair_dialog(p, BigConfirmationDialog(
        f"Match Bluetooth code {code}?" if code else "Allow Bluetooth pairing?", self.icon,
        lambda: self._request("pairing_response", prompt_id=p["id"], accepted=True))))
      accept.set_enabled(self._pairing_ready)
      cards.append(accept)
    elif prompt.get("kind") in ("pin", "passkey"):
      kind = prompt["kind"]
      entry = BigButton("enter PIN" if kind == "pin" else "enter passkey", "enter code from your device")
      validator = (lambda text: bool(re.fullmatch(r"[0-9]{1,6}", text))) if kind == "passkey" else \
                  (lambda text: 1 <= len(text) <= 16 and text.isascii() and text.isprintable())
      entry.set_click_callback(lambda p=prompt, k=kind, valid=validator: self._show_pair_dialog(p, BigInputDialog(
        "PIN" if k == "pin" else "passkey", minimum_length=1, text_validator=valid, password_mode=True,
        confirm_callback=lambda text: self._request("pairing_response", prompt_id=p["id"], accepted=True, value=text))))
      entry.set_enabled(self._pairing_ready)
      cards.append(entry)
    if prompt is not None and not prompt.get("displayOnly"):
      reject = BigButton("reject pairing", "do not pair")
      reject.set_click_callback(lambda p=prompt: self._request("pairing_response", prompt_id=p["id"], accepted=False))
      reject.set_enabled(self._pairing_ready)
      cards.append(reject)
    cancel = BigButton("cancel pairing", "stop this request")
    cancel.set_click_callback(lambda: self._request("cancel_pair"))
    cancel.set_enabled(self._pairing_ready)
    cards.append(cancel)
    return cards

  def _rebuild(self):
    status = self.status
    if status is None:
      cards = [GreyBigButton("bluetooth", "checking adapter")]
    else:
      value = "on" if status.get("powered") else "off"
      if status.get("errorCode") == "radio_unavailable":
        value = "radio unavailable"
      power = BigButton("bluetooth", value, self.icon)
      power.set_click_callback(lambda: self._request("power", enabled=not bool(self.status and self.status.get("powered"))))
      power.set_enabled(lambda: self._ready() and bool(self.status and self.status.get("parked")))
      cards = [power]
      if status.get("errorCode") in ("adapter_unavailable", "service_unavailable", "radio_preference_unavailable"):
        label = {"adapter_unavailable": "adapter", "service_unavailable": "service", "radio_preference_unavailable": "power setting"}
        cards.append(GreyBigButton(label[status["errorCode"]], "not responding"))
      if status.get("powered"):
        cards.extend(self._pairing_cards())
        for device in status.get("devices", ()):
          name = device_label(device)
          if not device.get("paired"):
            button = BigButton(name, "tap to pair", scroll=True)
            address = device["address"]
            button.set_click_callback(lambda addr=address: self._open_device(addr))
            button.set_enabled(self._ready)
            cards.append(button)
            continue
          value = "connected" if device.get("connected") else "saved device"
          button = BigButton(name, value, scroll=True)
          address = device["address"]
          button.set_click_callback(lambda addr=address: self._open_device(addr))
          button.set_enabled(self._ready)
          cards.append(button)
        if not status.get("devices"):
          cards.append(GreyBigButton("devices", "none found"))
        scanning = bool(status.get("discovering"))
        scan = BigButton("stop scan" if scanning else "scan for devices", "searching" if scanning else "scan")
        scan.set_click_callback(lambda: self._request("stop_scan" if scanning else "scan"))
        scan.set_enabled(lambda: self._ready() and bool(self.status and self.status.get("adapter")))
        cards.append(scan)
    self._scroller.items.clear()
    self._scroller.add_widgets(cards)

  def _open_device(self, address: str):
    device = next((item for item in (self.status or {}).get("devices", ()) if item.get("address") == address), None)
    if device is None:
      return
    if not device.get("paired"):
      self._request("pair", address=address)
      return
    page = NavScroller()
    cards = [GreyBigButton(device_label(device), address.lower())]
    connected = bool(device.get("connected"))
    action = BigButton("disconnect" if connected else "connect", "saved device")
    action.set_click_callback(lambda: self._request("disconnect" if connected else "connect", address=address,
                                                    return_to_root=True))
    action.set_enabled(self._ready)
    cards.append(action)
    forget = BigButton("forget device", "remove saved device")
    forget.set_click_callback(lambda: gui_app.push_widget(BigConfirmationDialog(
      "forget device", self.icon, lambda: self._request("forget", address=address, return_to_root=True), red=True)))
    forget.set_enabled(self._ready)
    cards.append(forget)
    page._scroller.add_widgets(cards)
    gui_app.push_widget(page)
