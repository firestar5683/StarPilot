"""Android Auto session supervisor: owns every stage, deadline, retry and cleanup.

One session, started by the user or by auto-connect (see auto_connect.py), runs
in one worker thread:

  idle -> connecting_bluetooth -> discovering -> rfcomm -> wifi_start -> wifi_info
       -> joining_wifi -> connecting_tcp -> authenticating -> negotiating -> streaming
  streaming <-> suspended (head unit showing its own screen)
  failure -> cleanup -> backoff -> retry          stop -> cleanup -> idle

Each attempt has a generation number; Stop cancels immediately (sockets are
closed from the caller's thread to unblock I/O). Between retries the projection
network is released without restoring the previous Wi-Fi, which happens once,
on Stop. Nothing here runs as root or touches vehicle control.
"""

from __future__ import annotations

import json
import os
import re
import socket
import threading
import time
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openpilot.common.hardware import COMMA_HARDWARE
from openpilot.starpilot.system.android_auto import identity as identity_store
from openpilot.starpilot.system.android_auto.auto_connect import AutoConnectPolicy
from openpilot.starpilot.system.android_auto.bootstrap import NAMES, BootstrapError, WirelessBootstrap
from openpilot.starpilot.system.android_auto.frame_source import (DEFAULT_PATH as DEFAULT_FRAME_PATH, FLAG_ASYNC_READBACK, FLAG_NV12,
                                                                  FORMAT_NV12, FrameRequest)
from openpilot.starpilot.system.android_auto.touch import DEFAULT_TOUCH_SOCKET
from openpilot.starpilot.system.android_auto.view import CAR_FRAME_PATH, ViewSource, renderer_available
from openpilot.starpilot.system.android_auto.session import AuthenticationRejected, PeerRequestedStop, ProjectionSession

BACKOFF_SECONDS = (2.0, 4.0, 8.0, 15.0, 30.0)
STABLE_SESSION_SECONDS = 30.0
PEER_STOP_RETRY_SECONDS = 10.0
FRAME_MAX_AGE = 0.5          # never send a UI frame older than this
SOFTWARE_FPS = 15            # libx264 cadence; the hardware encoder runs at 30
UNAVAILABLE_AFTER = 1.0      # focused but no fresh UI frame for this long -> "unavailable" card; the Honda gives the screen back after 3 s without video
SDP_SETTLE = (1.5, 2.2, 3.0)
TCP_ATTEMPTS = 6
MAX_LOG_FILES = 20
ENCODER_RECOVERIES = 3       # hardware encoder reopens allowed per window before the session is torn down
ENCODER_RECOVERY_WINDOW = 10.0
CAR_LINK_HOLD = 10.0         # a hands-free connection from the car counts as "car present" this long
WIRED_USB_VERIFIED = False   # configfs gadget/vehicle CAN USB isolation has not been proven on target


def encoder_preference(configured: str) -> str:
  return 'hardware' if COMMA_HARDWARE else configured

STATE_LABELS = {
  "idle": "off", "connecting_bluetooth": "connecting to car", "discovering": "finding android auto",
  "rfcomm": "starting wireless setup", "wifi_start": "waiting for car", "wifi_info": "getting car wi-fi",
  "joining_wifi": "joining car wi-fi", "connecting_tcp": "connecting", "authenticating": "authenticating",
  "negotiating": "negotiating video", "streaming": "projecting", "suspended": "car showing its own screen",
  "backoff": "retrying", "stopping": "stopping", "error": "error",
  "waiting_for_usb": "plug into the car's usb", "usb_accessory": "starting usb",
}


def _is_onroad() -> bool:
  try:
    from openpilot.common.params import Params
    from openpilot.starpilot.saved_source import read_saved
    raw, readable = read_saved(Params(), "IsOffroad", 1)
    return readable and raw == b"0"
  except Exception:
    return False


class Cancelled(Exception):
  pass


class NoLease:
  """Wired sessions use no car Wi-Fi network."""
  local_ip = None

  def release(self, restore: bool = False) -> None:
    pass


class UsbLease:
  """The link of a wired session: the USB cable, via the accessory bridge."""
  local_ip = None
  lost = "The car's USB connection ended"

  def __init__(self, bridge):
    self.bridge = bridge

  def still_connected(self) -> bool:
    return not self.bridge.closed.is_set()


class EventLog:
  """Sanitized JSONL session log under /data/android_auto/logs, plus the recent tail in memory."""

  def __init__(self, directory: Path | None = None):
    self.directory = directory or identity_store.LOG_DIR
    self.handle = None
    self.recent: deque[dict] = deque(maxlen=40)
    self.lock = threading.Lock()

  @staticmethod
  def _order(path: Path) -> tuple[int, str]:
    # Files are numbered, because the clock can read a date from months ago until it syncs;
    # pruning by the timestamp in the name deleted the newest session first.
    # Unnumbered files are from before numbering, so they are the oldest.
    match = re.fullmatch(r"session-(\d{6})-.*\.jsonl", path.name)
    return (int(match[1]), path.name) if match else (-1, path.name)

  def open(self) -> None:
    try:
      self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
      logs = sorted(self.directory.glob("session-*.jsonl"), key=self._order)
      for old in logs[:max(0, len(logs) - MAX_LOG_FILES + 1)]:
        old.unlink(missing_ok=True)
      number = max([0, *(self._order(log)[0] for log in logs)]) + 1
      path = self.directory / f"session-{number:06d}-{identity_store.timestamp()}.jsonl"
      fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
      self.handle = os.fdopen(fd, "a")
    except OSError:
      self.handle = None

  def close(self) -> None:
    with self.lock:
      if self.handle is not None:
        self.handle.close()
        self.handle = None

  def __call__(self, name: str, **values) -> None:
    record = {"t": datetime.now(UTC).isoformat(timespec="milliseconds"), "event": name, **values}
    with self.lock:
      self.recent.append(record)
      if self.handle is not None:
        try:
          self.handle.write(json.dumps(record, default=str) + "\n")
          self.handle.flush()
        except OSError:
          pass


class Supervisor:
  def __init__(self, bluez_factory=None, lease_factory=None, bluetooth_client=None, frame_path: str | None = None,
               synthetic: bool = False, car_frame_path: str = CAR_FRAME_PATH, touch_path: str = DEFAULT_TOUCH_SOCKET,
               renderer_command: list[str] | None = None, onroad=_is_onroad,
               shared_bluetooth_owner=None, source_session: tuple | None = None,
               projection_enabled: Callable[[], bool] = lambda: True):
    self._synthetic = synthetic
    self._onroad = onroad
    self._car_frame_path, self._touch_path, self._renderer_command = car_frame_path, touch_path, renderer_command
    self._bluez_factory = bluez_factory
    self._shared_bluetooth_owner = shared_bluetooth_owner
    self._source_session = source_session
    self._projection_enabled = projection_enabled
    self._lease_factory = lease_factory
    self._bt_client = bluetooth_client
    self._frame_path = frame_path
    self._lock = threading.RLock()
    self._stop = threading.Event()
    self._thread: threading.Thread | None = None
    self._generation = 0
    self._sockets: set[socket.socket] = set()
    self._bluez: Any = None
    self._pairing_until = 0.0
    self._pairing_known: set[str] | None = None  # Android Auto cars already paired when the pairing window opened
    self._car_seen_at = -CAR_LINK_HOLD
    self.auto = AutoConnectPolicy()
    self._companion_retry_at = 0.0
    self.log = EventLog()
    self.config = identity_store.load_config()
    self._status: dict = {"state": "idle", "detail": "", "error": "", "last_stage": "", "attempt": 0,
                          "retry_in": 0.0, "mode": None, "stats": {}, "head_unit": {}, "identity": "", "running": False,
                          "view": "", "encoder": "", "target_fps": 0}

  # ------------------------------------------------------------------ status

  def _set(self, **values) -> None:
    with self._lock:
      self._status.update(values)

  def _stage(self, state: str, detail: str = "") -> None:
    self._check_cancel()
    self._set(state=state, detail=detail, last_stage=state)
    self.log("stage", state=state, detail=detail)

  def _check_cancel(self) -> None:
    if self._stop.is_set():
      raise Cancelled()

  def status(self) -> dict:
    with self._lock:
      status = dict(self._status)
    status["label"] = STATE_LABELS.get(status["state"], status["state"])
    status["receiver_address"] = self.config["receiver_address"]
    status["receiver_name"] = self.config["receiver_name"]
    status["companion_address"] = self.config.get("companion_address", "")
    status["companion_name"] = self.config.get("companion_name", "")
    status["configured_view"] = self.config["view"]
    status["connection"] = self.config["connection"]
    status["pairing_ready"] = self._pairing_active()
    status["auto_connect"] = bool(self.config["auto_connect"])
    status["auto_paused"] = self.auto.suppressed
    status["recent"] = list(self.log.recent)[-8:]
    return status

  # ---------------------------------------------------------------- commands

  def user_start(self) -> None:
    self.auto.manual_start()
    self.start()

  def user_stop(self) -> None:
    """Stop pressed: also holds auto-connect off until the next drive."""
    self.auto.manual_stop(self._session_alive())
    self.stop()

  def set_auto_connect(self, enabled: bool) -> None:
    with self._lock:
      self.config["auto_connect"] = bool(enabled)
      identity_store.save_config(self.config)
    self.log("auto_connect_selected", enabled=bool(enabled))

  def start(self, trigger: str = "manual") -> None:
    with self._lock:
      if not self._projection_enabled():
        raise RuntimeError("Android Auto is disabled")
      if self.config["connection"] == "wired" and not WIRED_USB_VERIFIED:
        raise RuntimeError("Wired Android Auto is unavailable until USB controller isolation is verified")
      if self._thread is not None and self._thread.is_alive():
        if self._stop.is_set():
          raise RuntimeError("Android Auto is still stopping; try again in a moment")
        return
      if self.config["connection"] != "wired" and not self.config["receiver_address"]:
        raise RuntimeError("Choose your car first")
      identity = identity_store.load_identity()  # fail fast with a clear message
      self._stop.clear()
      self._generation += 1
      self._set(state="connecting_bluetooth", detail="", error="", attempt=0, retry_in=0.0, running=True,
                identity=identity_store.expiry_warning(identity))
      self._thread = threading.Thread(target=self._run, args=(self._generation, trigger), name="android_auto_session", daemon=True)
      self._thread.start()

  def stop(self, timeout: float = 8.0, graceful: float = 3.0) -> None:
    """Cancel the session: let a streaming session say goodbye to the car, then force it."""
    thread = self._thread
    self._stop.set()
    if thread is not None:
      thread.join(timeout=graceful)
    self._close_sockets()  # unblocks any stage still waiting on Bluetooth or the network
    if thread is not None:
      thread.join(timeout=max(0.0, timeout - graceful))
    with self._lock:
      if thread is not None and thread.is_alive():
        return  # still cleaning up; start() refuses until it finishes
      self._thread = None
      if self._status["state"] != "error":
        self._set(state="idle", detail="")
      self._set(running=False, retry_in=0.0)

  def select_receiver(self, address: str, name: str = "") -> None:
    from openpilot.starpilot.system.android_auto.bt_sockets import normalize_address
    address = normalize_address(address)
    device = self._phone().device(address)
    if device is None or not device['paired'] or not device.get('android_auto'):
      raise RuntimeError('Choose a paired Android Auto receiver')
    with self._lock:
      if self._thread is not None and self._thread.is_alive():
        raise RuntimeError("Stop Android Auto before changing the car")
      if self._bluez is not None and self.config['receiver_address'] and self.config['receiver_address'] != address:
        self._bluez.release()
      if self.config["receiver_address"] != address:
        self.config.update(companion_address="", companion_name="")
      self.config.update(receiver_address=address, receiver_name=name or address)
      identity_store.save_config(self.config)
    self._unselect_car_audio(address)
    try:
      self._phone().acquire()
      self._phone().set_trusted(address)  # the car's own connections are accepted onroad, like a phone's
    except Exception as error:
      self.log("trust_failed", error=str(error))

  def set_view(self, view: str) -> None:
    """Choose what the car shows; applies from the next projection session."""
    if view not in ("car", "mirror"):
      raise RuntimeError(f"Unknown view {view!r}")
    with self._lock:
      self.config["view"] = view
      identity_store.save_config(self.config)
    self.log("view_selected", view=view)

  def set_connection(self, connection: str) -> None:
    """Choose wireless (Bluetooth + car Wi-Fi) or wired (USB) projection."""
    if connection not in ("wireless", "wired"):
      raise RuntimeError(f"Unknown connection {connection!r}")
    if connection == "wired" and not WIRED_USB_VERIFIED:
      raise RuntimeError("Wired Android Auto is unavailable until USB controller isolation is verified")
    with self._lock:
      if self._thread is not None and self._thread.is_alive():
        raise RuntimeError("Stop Android Auto before changing the connection")
      self.config["connection"] = connection
      identity_store.save_config(self.config)
    self.log("connection_selected", connection=connection)

  def prepare_pairing(self, seconds: float = 180.0) -> None:
    """Present as a phone (HFP gateway, smartphone class) while the car pairs."""
    if self._bluez_factory is None and (self._source_session is None or self._shared_bluetooth_owner is None or
                                        not self._shared_bluetooth_owner.session_valid(self._source_session)):
      raise RuntimeError('Current Galaxy pairing authorization required')
    if self._session_alive():
      raise RuntimeError('Stop projection before pairing another receiver')
    bluez = self._phone()
    known = {device["address"] for device in bluez.devices() if device["paired"] and device.get("android_auto")}
    if self._bluez_factory is None:
      bluez.release()
      bluez.acquire_pairing()
    elif self.config.get('phone_class', True):
      bluez.acquire()
    with self._lock:
      self._pairing_known = known
      self._pairing_until = time.monotonic() + seconds
    self.log("pairing_window", seconds=seconds)

  def pair_device(self, address: str) -> None:
    if self._source_session is None or self._shared_bluetooth_owner is None or not self._pairing_active():
      raise RuntimeError('Current Galaxy pairing authorization required')
    self._shared_bluetooth_owner.pair_device(self._source_session, address)

  def pairing_status(self) -> dict:
    if self._source_session is None or self._shared_bluetooth_owner is None:
      return {'active': False, 'receiver': None, 'prompt': None, 'approved': False}
    return self._shared_bluetooth_owner.incoming_status(self._source_session)

  def pairing_response(self, prompt_id: str, accepted: bool, value: str = '') -> None:
    if not isinstance(prompt_id, str) or len(prompt_id) != 32 or type(accepted) is not bool or not isinstance(value, str):
      raise ValueError('Invalid pairing response')
    if self._source_session is None or self._shared_bluetooth_owner is None or not self._pairing_active() or \
       not self._shared_bluetooth_owner.incoming_response(self._source_session, prompt_id, accepted, value):
      raise RuntimeError('Pairing prompt expired or changed')

  def cancel_pairing(self) -> None:
    with self._lock:
      self._pairing_until, self._pairing_known = 0.0, None
      phone = self._bluez if not self._session_alive() else None
      if phone is not None:
        self._bluez = None
    if phone is not None:
      phone.close()

  def bind_source_session(self, session: tuple) -> None:
    """Bind a Galaxy-minted, externally revalidated pairing source."""
    if self._shared_bluetooth_owner is None or not self._shared_bluetooth_owner.session_valid(session):
      raise RuntimeError('Galaxy Android Auto pairing source is unavailable')
    with self._lock:
      if self._source_session == session:
        return
      old_phone = self._bluez if not self._session_alive() else None
      if old_phone is not None:
        self._bluez = None
      elif self._bluez is not None and hasattr(self._bluez, 'session'):
        self._bluez.session = session
      self._source_session = session
      if old_phone is not None:
        self._pairing_until, self._pairing_known = 0.0, None
    if old_phone is not None:
      old_phone.close()

  def devices(self) -> list[dict]:
    try:
      devices = self._phone().devices()
    except Exception as error:
      raise RuntimeError(f"Bluetooth unavailable: {error}") from error
    return [{key: device[key] for key in ("address", "name", "paired", "connected", "android_auto")}
            for device in devices if device["paired"]]

  def maintain(self, now: float | None = None) -> None:
    """Periodic housekeeping from the daemon thread: pairing window, auto-connect."""
    now = time.monotonic() if now is None else now
    owner = self._shared_bluetooth_owner
    if not self._projection_enabled():
      self._set(error='Android Auto was disabled')
      self.stop(timeout=0.0, graceful=0.0)
      if self._bluez is not None:
        self._bluez.close()
        self._bluez = None
      return
    if owner is not None:
      try:
        owner.maintain_phone_role()
      except Exception:
        self._set(error='Bluetooth receiver identity is unavailable')
        self.stop(timeout=0.0, graceful=0.0)
        if self._bluez is not None:
          self._bluez.close()
          self._bluez = None
        return
      lease = getattr(self._bluez, 'lease', None)
      if lease is not None and lease.released:
        if lease.session is None:
          self._set(error='Selected Bluetooth receiver changed or was unpaired')
          self.stop(timeout=0.0, graceful=0.0)
        else:
          self._pairing_until, self._pairing_known = 0.0, None
        self._bluez.close()
        self._bluez = None
        return
      if self._source_session is not None and not owner.session_valid(self._source_session):
        with self._lock:
          old_phone = self._bluez if self._bluez is not None and \
                      getattr(getattr(self._bluez, 'lease', None), 'session', None) is not None else None
          if old_phone is not None:
            self._bluez = None
          self._source_session = None
          self._pairing_until, self._pairing_known = 0.0, None
        if old_phone is not None:
          old_phone.close()
    if self._pairing_until:
      if self._pairing_active():
        self._select_new_car()
      else:
        with self._lock:
          self._pairing_until, self._pairing_known = 0.0, None
        if not self._session_alive():
          self._release_phone()
    self._auto_connect(now)

  def _auto_connect(self, now: float) -> None:
    config = self.config
    if self._pairing_active():
      return
    address = config["receiver_address"]
    if not (self._projection_enabled() and config["auto_connect"] and config["connection"] == "wireless" and address):
      if self._bluez is not None and not self._session_alive() and not self._pairing_active():
        self._release_phone()  # drop a standby gateway left from before auto-connect was turned off
      return
    running = self._session_alive()
    try:
      bluez = self._phone()
      adapter_ready, device = bluez.snapshot(address)
      if adapter_ready and device and device['paired']:
        if self._bluez_factory is None:
          bluez.acquire()
        elif config.get('phone_class', True):
          bluez.register_hfp()
    except Exception:
      adapter_ready, device = False, None  # Bluetooth still starting (or restarting)
    car_device = device
    companion = config.get('companion_address', '')
    if companion and adapter_ready and device and device['paired'] and self._shared_bluetooth_owner is not None:
      try:
        car_device = self._shared_bluetooth_owner.prepare_companion(companion, lambda: self.config.get('companion_address', ''))
        if not running and not car_device['connected'] and now >= self._companion_retry_at:
          self._companion_retry_at = now + 15.0
          car_device = self._shared_bluetooth_owner.prepare_companion(
            companion, lambda: self.config.get('companion_address', ''), connect=True)
      except Exception as error:
        car_device = None
        self._set(error=f'Waiting for selected car: {error}'[:300])
    car_link = bool(car_device and car_device["connected"]) or now - self._car_seen_at < CAR_LINK_HOLD
    onroad = self._onroad()
    action = self.auto.decide(now, enabled=True, onroad=onroad, car_link=car_link,
                              ready=adapter_ready and bool(device and device["paired"]) and (not companion or car_link), running=running)
    if action == "start":
      trigger = "onroad" if onroad else "car_connected"
      try:
        self.start(trigger=trigger)
      except Exception as error:
        self.auto.start_refused(now)
        self._set(error=f"auto-connect: {error}"[:300])
        self.log("auto_connect_refused", error=str(error))
    elif action == "stop":
      self.log("auto_connect_stop", reason="car gone")
      self.stop()

  def _select_new_car(self) -> None:
    """A car that paired during the pairing window and offers Android Auto becomes the chosen car."""
    if self._session_alive():
      return
    try:
      devices = self._phone().devices()
    except Exception:
      return
    approved = self.pairing_status()
    receiver = approved['receiver'] if approved['active'] and approved['approved'] else None
    with self._lock:
      known = self._pairing_known
      if known is None:
        return
      new = [device for device in devices if receiver is not None and device['address'] == receiver['address'] and
             device["paired"] and device.get("android_auto") and (device["address"] not in known or self._shared_bluetooth_owner is not None and
              self._shared_bluetooth_owner.phone_lease is not None and
              self._shared_bluetooth_owner.phone_lease.receiver == device["address"])]
      if not new:
        return
    try:
      self.cancel_pairing()
      self.select_receiver(new[0]["address"], new[0]["name"])
      self.log("car_selected_after_pairing", car=new[0]["name"])
    except (RuntimeError, ValueError) as error:
      self.log("car_select_failed", error=str(error))

  def close(self) -> None:
    self.stop()
    if self._bluez is not None:
      try:
        self._bluez.close()
      except Exception:
        pass
      self._bluez = None

  # ----------------------------------------------------------------- helpers

  def _phone(self):
    with self._lock:
      if self._bluez is None:
        if self._bluez_factory is not None:
          bluez = self._bluez_factory(self.log)  # test injection only
        elif self._shared_bluetooth_owner is not None:
          from openpilot.starpilot.system.android_auto.bluetooth_bridge import LeaseAwarePhone
          bluez = LeaseAwarePhone(self._shared_bluetooth_owner, self._source_session, self.log,
                                 enabled=self._projection_enabled,
                                 selected_receiver=lambda: self.config['receiver_address'])
        else:
          raise RuntimeError('Shared StarPilot Bluetooth owner is required for wireless Android Auto')
        bluez.accepts = self._hfp_accepts
        bluez.on_connection = self._hfp_connected
        self._bluez = bluez
      return self._bluez

  def _pairing_active(self) -> bool:
    return time.monotonic() < self._pairing_until

  def _session_alive(self) -> bool:
    thread = self._thread
    return thread is not None and thread.is_alive()

  def _hfp_accepts(self, address: str) -> bool:
    receiver = self.config["receiver_address"]
    if self._pairing_active() and self._source_session is not None and self._shared_bluetooth_owner is not None:
      lease = self._shared_bluetooth_owner.phone_lease
      return bool(lease is not None and not lease.released and
                  (lease.receiver == address.upper() or lease.incoming is not None and
                   lease.incoming.approved_address == address.upper()))
    return bool(receiver) and (address.upper() == receiver.upper() or
      self._shared_bluetooth_owner is not None and self._shared_bluetooth_owner.companion_accepts(address))

  def companion_bluetooth_action(self, operation: str, address: str, session: tuple):
    owner = self._shared_bluetooth_owner
    if owner is None:
      return None
    # select_receiver takes the supervisor lock before releasing an owner lease.
    # Keep that same order through connection, save and admission pruning so an
    # old adapter's successful action cannot save its car under a new adapter.
    with self._lock, owner.lock:
      lease = owner.phone_lease
      receiver = self.config['receiver_address']
      result = owner.companion_action(operation, address, session)
      if result is None:
        return None
      if (lease is None or owner.phone_lease is not lease or lease.released or lease.session is not None or
          lease.receiver != receiver.upper() or self.config['receiver_address'] != receiver or
          not owner.session_valid(session) or lease.enabled is None or not lease.enabled() or
          lease.selected_receiver is None or lease.selected_receiver().upper() != lease.receiver):
        raise RuntimeError('Android Auto receiver or pairing authorization changed')
      if operation == 'connect':
        device = self._phone().device(address)
        if (device is None or not device['paired'] or not device['connected'] or
            owner.phone_lease is not lease or lease.released or
            not owner.session_valid(session) or not lease.enabled()):
          raise RuntimeError('Selected car connection was not confirmed')
        self.config.update(companion_address=device['address'], companion_name=device['name'])
        identity_store.save_config(self.config)
        for previous in list(owner.companion_devices):
          if previous != device['address']:
            owner.companion_devices.pop(previous, None)
      elif self.config.get('companion_address', '').upper() == address.upper():
        self.config.update(companion_address='', companion_name='')
        identity_store.save_config(self.config)
      return result

  def _hfp_connected(self, address: str) -> None:
    if address.upper() in (self.config["receiver_address"].upper(), self.config.get("companion_address", "").upper()):
      self._car_seen_at = time.monotonic()

  def _release_phone(self) -> None:
    """Stop looking like a phone; keep only the standby gateway auto-connect needs."""
    bluez = self._bluez
    if bluez is None:
      return
    config = self.config
    standby = config["auto_connect"] and config["connection"] == "wireless" and bool(config["receiver_address"]) \
              and self._projection_enabled()
    if self._pairing_active():
      return
    if self._bluez_factory is not None:
      if standby:
        bluez.restore_class()
      else:
        bluez.release()
      return
    if not standby:
      bluez.release()
    elif getattr(bluez, 'lease', None) is None or bluez.lease.released:
      bluez.acquire()
    else:
      bluez.restore_class()

  def _remember_channel(self, address: str, channel: int | None) -> None:
    with self._lock:
      cache = dict(self.config["rfcomm_cache"])
      if channel is None:
        if cache.pop(address, None) is None:
          return
      elif cache.get(address) == channel:
        return
      else:
        cache[address] = channel
      self.config["rfcomm_cache"] = cache
      identity_store.save_config(self.config)

  def _lease(self):
    if self._lease_factory is None:
      from openpilot.starpilot.system.android_auto.network import NetworkLease
      return NetworkLease(self.log, self.config["wifi_interface"])
    return self._lease_factory(self.log, self.config["wifi_interface"])

  def _unselect_car_audio(self, address: str) -> None:
    if self._bt_client is None:
      return
    try:
      if self._bt_client.status().selected_audio.upper() == address.upper():
        self._bt_client.select_audio("")
        self.log("car_audio_unselected")
    except Exception:
      pass

  def _track(self, sock: socket.socket) -> socket.socket:
    with self._lock:
      self._sockets.add(sock)
    if self._stop.is_set():
      self._close_sockets()
      raise Cancelled()
    return sock

  def _close_sockets(self) -> None:
    with self._lock:
      sockets, self._sockets = self._sockets, set()
    for sock in sockets:
      try:
        sock.shutdown(socket.SHUT_RDWR)
      except OSError:
        pass
      try:
        sock.close()
      except OSError:
        pass

  def _wait(self, seconds: float) -> None:
    if self._stop.wait(seconds):
      raise Cancelled()

  # ---------------------------------------------------------------- session

  def _run(self, generation: int, trigger: str = "manual") -> None:
    self.log.open()
    wired = self.config["connection"] == "wired"
    self.log("session_start", receiver="usb" if wired else self.config["receiver_name"], generation=generation, trigger=trigger)
    lease = NoLease() if wired else self._lease()
    attempt = 0
    try:
      while not self._stop.is_set():
        started = time.monotonic()
        peer_stopped = False
        try:
          self._attempt(lease)
          self.log("session_ended")
        except Cancelled:
          break
        except PeerRequestedStop as error:
          self._set(error="", detail=str(error))
          self.log("session_ended", reason=str(error))
          peer_stopped = True
        except Exception as error:
          if self._stop.is_set():
            break  # I/O torn down by Stop; not a failure to report
          stage = error.stage if isinstance(error, BootstrapError) else self._status["last_stage"]
          message = self._describe_error(stage, error)
          self._set(error=message)
          self.log("attempt_failed", stage=stage, error=message, kind=type(error).__name__)
        finally:
          self._close_sockets()
          try:
            lease.release(restore=False)
          except Exception as error:
            self.log("wifi_release_failed", error=str(error))
        if self._stop.is_set():
          break
        attempt = 0 if time.monotonic() - started > STABLE_SESSION_SECONDS else attempt + 1
        delay = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
        if peer_stopped:
          delay = max(delay, PEER_STOP_RETRY_SECONDS)  # the car ended projection itself; do not bounce straight back
        self._set(state="backoff", attempt=attempt, retry_in=delay, mode=None)
        try:
          self._wait(delay)
        except Cancelled:
          break
    finally:
      self._set(state="stopping", detail="")
      try:
        lease.release(restore=True)
      except Exception as error:
        self.log("wifi_release_failed", error=str(error))
      try:
        self._release_phone()
      except Exception as error:
        self.log("bluetooth_release_failed", error=str(error))
      self.log("session_stop")
      self.log.close()
      self._set(state="idle", detail="", running=False, retry_in=0.0, mode=None)

  @staticmethod
  def _describe_error(stage: str, error: Exception) -> str:
    if isinstance(error, AuthenticationRejected):
      return "The car rejected the Android Auto identity; it may have expired"
    text = str(error) or type(error).__name__
    if stage == "authenticating" and "certificate" in text.lower():
      text += " (set verify_head_unit false in config.json to test without verifying the car)"
    return f"{STATE_LABELS.get(stage, stage)}: {text}"[:300]

  def _attempt(self, lease) -> None:
    if self.config["connection"] == "wired":
      self._attempt_usb()
      return
    config = self.config
    address = config["receiver_address"]
    ident = identity_store.load_identity()

    self._stage("connecting_bluetooth", config["receiver_name"])
    bluez = self._phone()
    bluez.acquire()
    device = bluez.device(address)
    if device is None or not device["paired"]:
      raise RuntimeError("The car is not paired with this comma; pair it in Bluetooth settings")
    companion = config.get('companion_address', '')
    if companion:
      if self._shared_bluetooth_owner is None:
        raise RuntimeError('Shared Bluetooth owner required for the selected car')
      self._shared_bluetooth_owner.prepare_companion(companion, lambda: self.config.get('companion_address', ''), connect=True)
      self._check_cancel()
      self.log('companion_car_connected', address=companion)
    elif device.get('android_auto') and '0000111e-0000-1000-8000-00805f9b34fb' not in device.get('uuids', []):
      raise RuntimeError('Connect your paired car in Galaxy Bluetooth first to select it for this Android Auto adapter')
    bluez.connect_device(address)
    self._wait(1.0)

    from openpilot.starpilot.system.android_auto import bt_sockets
    channel = int(config.get("rfcomm_channel") or 0)
    source = "config"
    if not channel:
      channel, source = config["rfcomm_cache"].get(address, 0), "cache"
    self._stage("discovering")
    if not channel:
      channel, source = self._discover_channel(address), "sdp"
    self.log("rfcomm_channel", channel=channel, source=source)

    try:
      self._stage("rfcomm", f"channel {channel}")
      rfcomm = self._track(bt_sockets.connect_rfcomm(address, channel))
      boot = WirelessBootstrap(rfcomm, self._bootstrap_log, device_serial=config["device_name"],
                               version_status=int(config.get("version_status", 0)))
      self._set(state="wifi_start")
      result = boot.run(lambda credentials: lease.acquire(credentials, cancelled=self._stop.is_set), cancelled=self._stop.is_set)
    except Exception:
      if source == "cache" and not self._stop.is_set() and self._status["last_stage"] in ("rfcomm", "wifi_start"):
        self._remember_channel(address, None)  # the car never answered there; ask it over SDP next time
        self.log("rfcomm_cache_dropped", channel=channel)
      raise
    if source == "sdp":
      self._remember_channel(address, channel)
    self._set(head_unit=result.head_unit)
    bluez.restore_class()  # the car has accepted the comma; stop looking like a phone to everything else
    keepalive_stop = threading.Event()
    threading.Thread(target=boot.keepalive, args=(keepalive_stop,), name="aa_rfcomm_keepalive", daemon=True).start()
    try:
      self._project(result, lease, ident)
    finally:
      keepalive_stop.set()

  def _discover_channel(self, address: str) -> int:
    from openpilot.starpilot.system.android_auto import bt_sockets, sdp
    last_error: Exception | None = None
    for settle in SDP_SETTLE:
      self._check_cancel()
      try:
        with self._track(bt_sockets.connect_l2cap(address, sdp.SDP_PSM)) as sdp_sock:
          self._wait(settle)
          return sdp.query_channel(sdp_sock)
      except (OSError, sdp.SdpError) as error:
        last_error = error
        self.log("sdp_retry", error=str(error), settle=settle)
        self._wait(0.35)
    raise RuntimeError(f"Could not find the car's Android Auto service: {last_error}")

  def _attempt_usb(self) -> None:
    """Wired: wait for the car's accessory handshake on USB, then project over the cable."""
    if not WIRED_USB_VERIFIED:
      raise RuntimeError("Wired Android Auto is unavailable until USB controller isolation is verified")
    from openpilot.starpilot.system.android_auto import usb_accessory as usb
    ident = identity_store.load_identity()
    gadget = usb.AccessoryGadget(self.log)
    listener = usb.UeventListener()
    bridge = None
    try:
      gadget.prepare()
      self._stage("waiting_for_usb")
      while True:
        self._check_cancel()
        event = listener.next(0.5)
        if event is None:
          continue
        if "USB_STATE" in event:
          self.log("usb_state", state=event["USB_STATE"])
        if event.get("ACCESSORY") == "START":
          break
      self._stage("usb_accessory")
      gadget.switch_to_accessory()
      bridge = usb.AccessoryBridge(log=self.log)
      self._project(None, UsbLease(bridge), ident, connect=lambda: self._track(bridge.socket))
    finally:
      if bridge is not None:
        bridge.close()
      listener.close()
      gadget.restore()

  def _bootstrap_log(self, name: str, **values) -> None:
    self.log(name, **values)
    if name == "bootstrap_tx" and values.get("message") == NAMES[2]:
      self._set(state="wifi_info", last_stage="wifi_info")
    elif name == "wifi_joining":
      self._set(state="joining_wifi", last_stage="joining_wifi", detail=str(values.get("ssid", "")))

  def _connect_tcp(self, result, lease) -> socket.socket:
    self._stage("connecting_tcp", f"{result.endpoint.ip}:{result.endpoint.port}")
    last_error: Exception | None = None
    for attempt in range(TCP_ATTEMPTS):
      self._check_cancel()
      try:
        sock = socket.create_connection((result.endpoint.ip, result.endpoint.port), timeout=5.0,
                                        source_address=(lease.local_ip, 0) if lease.local_ip else None)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return self._track(sock)
      except OSError as error:
        last_error = error
        self.log("tcp_retry", attempt=attempt + 1, error=str(error))
        self._wait(1.0 + attempt * 0.5)
    raise RuntimeError(f"Car did not accept the projection connection: {last_error}")

  def _project(self, result, lease, ident, connect=None) -> None:
    config = self.config
    sock = connect() if connect is not None else self._connect_tcp(result, lease)
    ca = ident.root if config.get("verify_head_unit", True) else None
    session = ProjectionSession(sock, ident.cert, ident.key, self.log, ca)
    self._stage("authenticating")
    session.authenticate()
    self._stage("negotiating")
    mode = session.start(config["device_name"], "comma.ai")
    self._set(mode=mode.as_dict(), error="")
    self.log("projection_ready", mode=mode.as_dict(), head_unit_subject=session.head_unit_subject)
    try:
      from openpilot.starpilot.system.android_auto.display_profile import record_screen
      record_screen(mode.as_dict())
    except (OSError, ValueError, TypeError, KeyError) as error:
      self.log("screen_profile_error", error=str(error))

    from openpilot.starpilot.system.android_auto.hw_encoder import create_encoder
    software_fps = min(SOFTWARE_FPS, config["fps"]) if config["fps"] else SOFTWARE_FPS
    encoder, fps = create_encoder(mode.width, mode.height, preference=encoder_preference(config["encoder"]),
                                  bitrate_kbps=config["bitrate_kbps"],
                                  margin_height=mode.margin_height, software_fps=software_fps, log=self.log,
                                  rate_control=config["rate_control"])
    fps = min(fps, mode.fps, config["fps"] or fps)
    interval = 1.0 / fps
    flags = (FLAG_NV12 if config["gpu_nv12"] and getattr(encoder, "supports_nv12", False) else 0) | \
            (FLAG_ASYNC_READBACK if config["async_readback"] else 0)
    request = FrameRequest(mode.width, mode.height, mode.margin_width, mode.margin_height, int(interval * 1e6), flags)
    self.log("frame_pipeline", nv12=bool(flags & FLAG_NV12), async_readback=bool(flags & FLAG_ASYNC_READBACK))
    view = config["view"]
    if view == "car" and not self._synthetic and self._renderer_command is None and not renderer_available():
      view = "unavailable"
    source = ViewSource(view, request, self.log, synthetic=self._synthetic,
                        mirror_path=self._frame_path or DEFAULT_FRAME_PATH, car_path=self._car_frame_path,
                        touch_path=self._touch_path, renderer_command=self._renderer_command,
                        renderer_log=identity_store.LOG_DIR / "car_ui.log")
    self._set(view=source.label, encoder=getattr(encoder, "backend", "libx264"), target_fps=fps)
    try:
      self._stream(session, encoder, source, lease, interval)
    finally:
      source.close()
      encoder.close()
      if self._stop.is_set():
        try:
          session.shutdown()
        except Exception:
          pass

  def _stream(self, session: ProjectionSession, encoder, source: ViewSource, lease, interval: float) -> None:
    started = time.monotonic()
    last_fresh = time.monotonic()
    last_unavailable = 0.0
    next_check = 0.0
    ages: deque[float] = deque(maxlen=120)
    sent_times: deque[float] = deque(maxlen=200)
    unavailable: dict[str, bytes] = {}
    recoveries: list[float] = []  # when the hardware encoder was reopened, this session
    encode_peak = 0.0
    wait_for_frame = False
    self._stage("streaming")
    while not self._stop.is_set():
      # Wait only when there was no frame or the receiver's window is full.
      # select wakes immediately for touches/ACKs; sleeping after every encode
      # used to add dead time even when the next frame was already available.
      timeout = min(interval / 4, 0.01) if wait_for_frame else 0.0
      handled = session.pump(timeout if session.can_send() else 0.05)
      # Bound the drain so a burst of input cannot starve video, but do not
      # make each queued touch or ACK wait for another encode/poll cycle.
      for _ in range(15):
        if not handled:
          break
        handled = session.pump(0.0)
      session.check_progress()
      now = time.monotonic()
      wait_for_frame = True
      if session.focused:
        source.demand(1.0)
      else:
        source.release_demand()
      if session.touch_events:
        source.send_touches(list(session.touch_events))
        session.touch_events.clear()
      state = "streaming" if session.focused else "suspended"
      if self._status["state"] != state:
        self._set(state=state)
      if session.can_send():
        frame = source.latest()
        if frame is not None:
          age = now - frame.captured_ns / 1e9
          encode = encoder.encode_nv12 if frame.pixel_format == FORMAT_NV12 else encoder.encode_rgba
          encoded = self._encode(encoder, encode, frame.data, session.needs_keyframe, recoveries) if age <= FRAME_MAX_AGE else None
          if encoded is not None:
            data, keyframe = encoded
            encode_peak = max(encode_peak, encoder.last_encode_ms)
            session.send_frame(data, frame.captured_ns // 1000, keyframe=keyframe)
            if source.view == "car":
              source.source.mark_sent(frame.captured_ns)
            sent_at = time.monotonic()
            ages.append(sent_at - frame.captured_ns / 1e9)
            sent_times.append(sent_at)
            last_fresh = sent_at
            wait_for_frame = False
        elif now - last_fresh > UNAVAILABLE_AFTER and now - last_unavailable > 1.0:
          # The UI stopped producing frames (e.g. the offroad render budget ran
          # out). Say so on the car instead of freezing on an old image.
          text = "Starting StarPilot" if source.waiting_for_first_frame else "StarPilot display unavailable"
          if text not in unavailable:
            unavailable[text] = self._unavailable_frame(source.request, text)
          encoded = self._encode(encoder, encoder.encode_rgba, unavailable[text], True, recoveries)
          if encoded is not None:
            session.send_frame(encoded[0], time.monotonic_ns() // 1000, keyframe=encoded[1])
          last_unavailable = now
      now = time.monotonic()
      if now >= next_check:
        next_check = now + 1.0
        if not lease.still_connected():
          raise RuntimeError(getattr(lease, "lost", "Lost the car's Wi-Fi network"))
        label = source.label
        source.check(now, focused=session.focused)
        if source.label != label:
          self._set(view=source.label)
        window = [t for t in sent_times if now - t <= 5.0]
        ordered = sorted(ages)
        stats = {**session.stats(), "fps": round(len(window) / 5.0, 1), "encode_ms": round(encoder.last_encode_ms, 1),
                 "encode_peak_ms": round(encode_peak, 1), "encoder_recoveries": len(recoveries),
                 "frame_age_p95_ms": round(ordered[int(len(ordered) * 0.95) - 1] * 1000) if ordered else None,
                 "uptime_s": round(now - started), "frames_from_view": source.frames}
        self._set(stats=stats)
        if int(now - started) % 30 == 0:
          self.log("stats", **stats)
          encode_peak = 0.0  # the peak covers each logged 30 s window

  def _encode(self, encoder, encode, data: bytes, keyframe: bool, recoveries: list[float]) -> tuple[bytes, bool] | None:
    """Encode one frame. When the hardware encoder fails (the shared VPU stalled past the
    deadline), reopen it and drop this frame instead of tearing down the whole session:
    the next frame is an IDR, and the car waits 3 s for video before taking its screen back.
    Repeated failures still end the attempt, which reconnects from scratch."""
    started = time.monotonic()
    try:
      return encode(data, keyframe=keyframe)
    except Exception as error:
      failed = time.monotonic()
      recent = sum(1 for at in recoveries if failed - at <= ENCODER_RECOVERY_WINDOW)
      reopen = getattr(encoder, "reopen", None)  # libx264 has nothing to reopen
      if reopen is None or recent >= ENCODER_RECOVERIES:
        self.log("encoder_failed", error=str(error), encode_ms=round((failed - started) * 1000), recent_recoveries=recent)
        raise
      try:
        reopen()
      except Exception as reopen_error:
        self.log("encoder_reopen_failed", error=str(error), reopen_error=str(reopen_error))
        raise error from reopen_error
      recoveries.append(failed)
      self.log("encoder_recovered", error=str(error), encode_ms=round((failed - started) * 1000),
               reopen_ms=round((time.monotonic() - failed) * 1000), recent_recoveries=recent + 1, total=len(recoveries))
      return None

  @staticmethod
  def _unavailable_frame(request: FrameRequest | None, text: str) -> bytes:
    assert request is not None
    try:
      from PIL import Image, ImageDraw, ImageFont
      from openpilot.common.basedir import BASEDIR

      base = Path(BASEDIR)
      logo_path = base / "starpilot" / "system" / "the_galaxy" / "assets" / "images" / "main_logo.png"
      font_path = base / "selfdrive" / "assets" / "fonts" / "como-heavy.otf"

      bg_color = (10, 10, 22, 255)  # Cosmic void #0a0a16
      canvas = Image.new("RGBA", (request.width, request.height), bg_color)

      font_size = max(18, min(64, int(request.height * 0.06)))
      try:
        font = ImageFont.truetype(str(font_path), font_size) if font_path.exists() else ImageFont.load_default()
      except Exception:
        font = ImageFont.load_default()

      draw = ImageDraw.Draw(canvas)
      bbox = draw.textbbox((0, 0), text, font=font)
      text_w = bbox[2] - bbox[0]
      text_h = bbox[3] - bbox[1]

      gap = max(12, int(request.height * 0.04))
      target_logo_h = int(min(request.height * 0.42, request.width * 0.35))

      if logo_path.exists() and target_logo_h > 20:
        logo = Image.open(logo_path).convert("RGBA")
        logo_w = int(logo.width * (target_logo_h / logo.height))
        logo_resized = logo.resize((logo_w, target_logo_h), Image.Resampling.LANCZOS)
        total_h = target_logo_h + gap + text_h
        start_y = max(8, (request.height - total_h) // 2)
        logo_x = (request.width - logo_w) // 2
        canvas.paste(logo_resized, (logo_x, int(start_y)), logo_resized)
        text_y = start_y + target_logo_h + gap
      else:
        text_y = (request.height - text_h) // 2

      text_x = (request.width - text_w) // 2
      draw.text((text_x + 1, text_y + 1), text, font=font, fill=(30, 20, 50, 180))
      draw.text((text_x, text_y), text, font=font, fill=(250, 248, 255, 255))
      return canvas.tobytes()
    except Exception:
      try:
        import cv2
        import numpy as np
        image = np.zeros((request.height, request.width, 4), np.uint8)
        image[..., 3] = 255
        scale = request.height / 480
        size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, max(1, int(2 * scale)))[0]
        cv2.putText(image, text, ((request.width - size[0]) // 2, (request.height + size[1]) // 2), cv2.FONT_HERSHEY_SIMPLEX,
                    scale, (255, 255, 255, 255), max(1, int(2 * scale)), cv2.LINE_AA)
        return image.tobytes()
      except Exception:
        return bytes(request.width * request.height * 4)
