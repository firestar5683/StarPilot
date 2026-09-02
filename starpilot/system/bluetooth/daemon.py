import json
import os
import socketserver
import threading
import time

from typing import Any

from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.starpilot.system.bluetooth.bluez import BlueZClient
from openpilot.starpilot.system.bluetooth.elm327 import ELM327Session
from openpilot.starpilot.system.bluetooth.protocol import BLUETOOTH_SOCKET_PATH
from openpilot.starpilot.system.bluetooth.radio import BluetoothRadio


OFFROAD_COMMANDS = {"set_power", "start_scan", "stop_scan", "pair", "forget", "test_audio", "pairing_response",
                    "elm_open", "elm_command", "elm_read_dtcs"}
SCAN_DURATION = 20.0
AUDIO_TEST_START_DELAY = 3.0
AUDIO_TEST_HOLD_TIME = 3.0
RECONNECT_INTERVAL_SECONDS = 15.0
RECONNECT_MAX_BACKOFF_SECONDS = 300.0
MANUAL_DISCONNECT_SUPPRESSION_SECONDS = 300.0


class BluetoothController:
  def __init__(self, params: Params | None = None, bluez_factory=BlueZClient, radio: BluetoothRadio | None = None,
               params_memory: Params | None = None, sleep=time.sleep, elm_factory=ELM327Session):
    self.params = params or Params()
    self.params_memory = params_memory or Params(memory=True)
    self._bluez_factory = bluez_factory
    self._elm_factory = elm_factory
    self._radio = radio or BluetoothRadio()
    self._lock = threading.RLock()
    self._bluez: BlueZClient | None = None
    self._elm: ELM327Session | None = None
    self._pairing_address = ""
    self._pairing_error = ""
    self._last_reconnect = 0.0
    self._reconnect_backoff: dict[str, tuple[int, float]] = {}
    self._manual_disconnect_until: dict[str, float] = {}
    self._scan_deadline = 0.0
    self._audio_test_deadline = 0.0
    self._sleep = sleep
    self.params.remove("BluetoothAudioTestActive")
    self.params_memory.remove("TestAlert")

  def close(self) -> None:
    self.params.remove("BluetoothAudioTestActive")
    self.params_memory.remove("TestAlert")
    with self._lock:
      self._close_elm()
      if self._bluez is not None:
        self._bluez.close()
        self._bluez = None
    if not self.params.get_bool("BluetoothEnabled"):
      try:
        self._radio.stop()
      except Exception:
        pass

  def _client(self) -> BlueZClient:
    with self._lock:
      if self._bluez is None:
        if not self.params.get_bool("BluetoothEnabled"):
          raise RuntimeError("Bluetooth is disabled")
        self._radio.start()
        self._bluez = self._bluez_factory()
        self._bluez.set_powered(True)
        self._bluez.agent.set_auto_accept_incoming(self._offroad())
        try:
          self._bluez.set_discoverable(True)
        except Exception as error:
          cloudlog.warning(f"Bluetooth discoverability setup failed: {error}")
      return self._bluez

  def initialize(self) -> None:
    if not self.params.get_bool("BluetoothEnabled"):
      return
    try:
      self._client()
    except Exception:
      cloudlog.exception("Bluetooth initialization failed")

  def _reset_client(self) -> None:
    with self._lock:
      self._close_elm()
      if self._bluez is not None:
        try:
          self._bluez.close()
        except Exception:
          pass
        self._bluez = None

  def _close_elm(self) -> None:
    with self._lock:
      session = self._elm
      self._elm = None
      if session is None:
        return
      try:
        session.close()
      except Exception:
        cloudlog.warning("ELM327 session close failed")

  def _invalidate_elm(self, session: ELM327Session) -> None:
    with self._lock:
      if self._elm is not session:
        return
      self._close_elm()

  def _active_elm(self, address: str) -> ELM327Session:
    with self._lock:
      session = self._elm
      if session is None:
        raise RuntimeError("ELM327 session is not open")
      if str(session.address).upper() != address.upper():
        raise RuntimeError("ELM327 session is open for another device")
      return session

  def _offroad(self) -> bool:
    return self.params.get_bool("IsOffroad")

  def status(self) -> dict[str, Any]:
    # Status lazily initializes the radio, so serialize it with power changes.
    with self._lock:
      result = {
        "available": self._radio.available,
        "enabled": self.params.get_bool("BluetoothEnabled"),
        "powered": False,
        "discovering": False,
        "offroad": self._offroad(),
        "selected_audio": self.params.get("BluetoothAudioAddress", encoding="utf-8") or "",
        "devices": [],
        "prompt": None,
        "error": self._pairing_error,
        "pairing_address": self._pairing_address,
      }
      if not result["enabled"]:
        return result
      try:
        result.update(self._client().status())
        result["available"] = True
        self._bluez.agent.set_auto_accept_incoming(result["offroad"])
        prompt = result.get("prompt")
        if prompt is not None and self._pairing_address:
          prompt["address"] = self._pairing_address
          device = next((item for item in result["devices"] if item["address"].upper() == self._pairing_address.upper()), None)
          prompt["name"] = device["name"] if device else self._pairing_address
      except Exception as error:
        result["error"] = str(error)
        if not self._pairing_address:
          self._reset_client()
      return result

  def _require_offroad(self, command: str) -> None:
    if command in OFFROAD_COMMANDS and not self._offroad():
      raise RuntimeError("Bluetooth settings can only be changed offroad")

  def _pair_worker(self, address: str) -> None:
    try:
      self._client().pair(address)
      status = self._client().device_for_address(address)
      if status.get("audio") and not self.params.get("BluetoothAudioAddress", encoding="utf-8"):
        self.params.put("BluetoothAudioAddress", address)
      self._pairing_error = ""
    except Exception as error:
      self._pairing_error = str(error)
      cloudlog.exception("Bluetooth pairing failed")
    finally:
      try:
        self._client().stop_discovery()
      except Exception:
        pass
      self._pairing_address = ""

  def _test_audio_worker(self, address: str, deadline: float) -> None:
    try:
      self._sleep(max(0.0, deadline - time.monotonic()))
      if (not self._offroad() or not self.params.get_bool("BluetoothEnabled") or
          (self.params.get("BluetoothAudioAddress", encoding="utf-8") or "").upper() != address.upper()):
        return
      device = self._client().device_for_address(address)
      if not device.get("connected"):
        return
      self.params_memory.put("TestAlert", "engage")
      self._sleep(AUDIO_TEST_HOLD_TIME)
    except Exception:
      cloudlog.exception("Bluetooth audio test failed")
    finally:
      self._audio_test_deadline = 0.0
      self.params.remove("BluetoothAudioTestActive")

  def handle(self, request: dict[str, Any]) -> dict[str, Any]:
    command = str(request.get("command", ""))
    if command == "status":
      return {"status": self.status()}
    self._require_offroad(command)

    address = str(request.get("address", ""))
    if command == "set_power":
      enabled = bool(request.get("enabled", False))
      with self._lock:
        if enabled:
          try:
            self.params.put_bool("BluetoothEnabled", True)
            self._client()
          except Exception:
            self.params.put_bool("BluetoothEnabled", False)
            self._reset_client()
            try:
              self._radio.stop()
            except Exception:
              pass
            raise
        else:
          self._close_elm()
          try:
            client = self._bluez
            if client is not None:
              client.set_powered(False)
          finally:
            self._reset_client()
            self._radio.stop()
            self.params.put_bool("BluetoothEnabled", False)
            self._scan_deadline = 0.0
    elif command == "start_scan":
      if not self.params.get_bool("BluetoothEnabled"):
        raise RuntimeError("Enable Bluetooth before scanning")
      self._pairing_error = ""
      self._client().start_discovery()
      self._scan_deadline = time.monotonic() + SCAN_DURATION
    elif command == "stop_scan":
      self._client().stop_discovery()
      self._scan_deadline = 0.0
    elif command == "pair":
      if self._pairing_address:
        raise RuntimeError("Another Bluetooth device is already pairing")
      self._client().device_for_address(address)
      self._scan_deadline = 0.0
      self._reconnect_backoff.pop(address.upper(), None)
      self._manual_disconnect_until.pop(address.upper(), None)
      self._pairing_address = address
      self._pairing_error = ""
      threading.Thread(target=self._pair_worker, args=(address,), daemon=True).start()
    elif command == "connect":
      normalized_address = address.upper()
      self._reconnect_backoff.pop(normalized_address, None)
      self._manual_disconnect_until.pop(normalized_address, None)
      with self._lock:
        self._client().connect(normalized_address)
    elif command == "disconnect":
      normalized_address = address.upper()
      # Mark this before issuing the D-Bus call. A disconnected device can
      # report NotConnected, and it must not immediately be auto-reconnected.
      self._manual_disconnect_until[normalized_address] = time.monotonic() + MANUAL_DISCONNECT_SUPPRESSION_SECONDS
      self._reconnect_backoff.pop(normalized_address, None)
      try:
        with self._lock:
          self._client().disconnect(normalized_address)
      except RuntimeError as error:
        if "notconnected" not in str(error).replace(" ", "").lower():
          self._manual_disconnect_until.pop(normalized_address, None)
          raise
    elif command == "forget":
      with self._lock:
        if self._elm is not None and str(self._elm.address).upper() == address.upper():
          self._close_elm()
      self._client().remove(address)
      self._reconnect_backoff.pop(address.upper(), None)
      self._manual_disconnect_until.pop(address.upper(), None)
      if (self.params.get("BluetoothAudioAddress", encoding="utf-8") or "").upper() == address.upper():
        self.params.remove("BluetoothAudioAddress")
    elif command == "select_audio":
      if address:
        device = self._client().device_for_address(address)
        if not device.get("audio"):
          raise RuntimeError("Selected device does not support Bluetooth audio")
        self.params.put("BluetoothAudioAddress", address)
      else:
        self.params.remove("BluetoothAudioAddress")
    elif command == "test_audio":
      if self.params.get_bool("BluetoothAudioTestActive"):
        raise RuntimeError("Bluetooth audio test is already playing")
      device = self._client().device_for_address(address)
      if not device.get("audio"):
        raise RuntimeError("Selected device does not support Bluetooth audio")
      if not device.get("paired") or not device.get("connected"):
        raise RuntimeError("Connect the Bluetooth audio device before testing")
      self.params.put("BluetoothAudioAddress", address)
      self.params.put_bool("BluetoothAudioTestActive", True)
      deadline = time.monotonic() + AUDIO_TEST_START_DELAY
      self._audio_test_deadline = deadline
      threading.Thread(target=self._test_audio_worker, args=(address, deadline), daemon=True).start()
      return {"audio_test_delay_ms": max(0, round((deadline - time.monotonic()) * 1000))}
    elif command == "elm_open":
      if not address:
        raise RuntimeError("Bluetooth device address is required")
      if not self.params.get_bool("BluetoothEnabled"):
        raise RuntimeError("Bluetooth is disabled")
      with self._lock:
        if self._elm is not None and str(self._elm.address).upper() == address.upper():
          return {"adapter": self._elm.adapter_name}
        device = self._client().device_for_address(address)
        if not device.get("paired"):
          raise RuntimeError("Pair the Bluetooth device before opening ELM327")
        if not device.get("serial"):
          raise RuntimeError("Bluetooth device does not advertise Serial Port Profile")
        self._close_elm()
        session = self._elm_factory(address)
        try:
          adapter = str(session.open())
        except Exception:
          try:
            session.close()
          except Exception:
            pass
          raise
        session.adapter_name = adapter
        self._elm = session
        return {"adapter": adapter}
    elif command == "elm_close":
      with self._lock:
        if self._elm is not None and str(self._elm.address).upper() == address.upper():
          self._close_elm()
    elif command == "elm_command":
      session = self._active_elm(address)
      try:
        return {"response": session.command(str(request.get("value", "")))}
      except Exception:
        self._invalidate_elm(session)
        raise
    elif command == "elm_read_dtcs":
      session = self._active_elm(address)
      try:
        return session.read_dtcs()
      except Exception:
        self._invalidate_elm(session)
        raise
    elif command == "pairing_response":
      if not self._client().agent.respond(str(request.get("prompt_id", "")), bool(request.get("accepted", False)), str(request.get("value", ""))):
        raise RuntimeError("Pairing request is no longer active")
    else:
      raise RuntimeError(f"Unknown Bluetooth command: {command}")
    return {}

  def _maintain_scan(self, status: dict[str, Any], now: float) -> None:
    if not status["discovering"]:
      self._scan_deadline = 0.0
    elif not status["offroad"] or (self._scan_deadline and now >= self._scan_deadline):
      self._client().stop_discovery()
      self._scan_deadline = 0.0

  def maintain_connections(self) -> None:
    while True:
      time.sleep(2)
      if not self.params.get_bool("BluetoothEnabled"):
        self._close_elm()
        continue
      try:
        status = self.status()
        if self._elm is not None and not status["offroad"]:
          self._close_elm()
        if not status["available"] or not status["powered"]:
          self._close_elm()
          continue
        now = time.monotonic()
        self._maintain_scan(status, now)
        if self._pairing_address or now - self._last_reconnect < RECONNECT_INTERVAL_SECONDS:
          continue
        self._last_reconnect = now
        selected = str(status["selected_audio"])
        candidates = [device for device in status["devices"] if device["paired"] and device["trusted"] and not device["connected"]]
        candidates.sort(key=lambda device: device["address"].upper() != selected.upper())
        candidate_addresses = {device["address"].upper() for device in candidates}
        for address in list(self._manual_disconnect_until):
          if address not in candidate_addresses or now >= self._manual_disconnect_until[address]:
            self._manual_disconnect_until.pop(address, None)
        for address in list(self._reconnect_backoff):
          if address not in candidate_addresses:
            self._reconnect_backoff.pop(address, None)
        for device in candidates:
          if device["audio"] or device["controller"]:
            address = device["address"].upper()
            if now < self._manual_disconnect_until.get(address, 0.0):
              continue
            _attempts, retry_after = self._reconnect_backoff.get(address, (0, 0.0))
            if now < retry_after:
              continue
            try:
              with self._lock:
                self._client().connect(address)
              self._reconnect_backoff.pop(address, None)
            except Exception:
              attempts = _attempts + 1
              delay = min(RECONNECT_INTERVAL_SECONDS * (2 ** (attempts - 1)), RECONNECT_MAX_BACKOFF_SECONDS)
              self._reconnect_backoff[address] = (attempts, now + delay)
              cloudlog.warning(f"Bluetooth reconnect failed for {address}; retrying in {delay:.0f}s")
      except Exception:
        cloudlog.exception("Bluetooth connection maintenance failed")


class BluetoothRequestHandler(socketserver.StreamRequestHandler):
  def handle(self) -> None:
    try:
      raw = self.rfile.readline(1024 * 1024)
      request = json.loads(raw)
      payload = self.server.controller.handle(request)
      response = {"ok": True, **payload}
    except Exception as error:
      response = {"ok": False, "error": str(error)}
    self.wfile.write(json.dumps(response, separators=(",", ":")).encode() + b"\n")


class BluetoothServer(socketserver.ThreadingUnixStreamServer):
  daemon_threads = True

  def __init__(self, socket_path: str, controller: BluetoothController):
    self.controller = controller
    super().__init__(socket_path, BluetoothRequestHandler)


def main() -> None:
  try:
    os.unlink(BLUETOOTH_SOCKET_PATH)
  except FileNotFoundError:
    pass
  controller = BluetoothController()
  threading.Thread(target=controller.initialize, daemon=True).start()
  threading.Thread(target=controller.maintain_connections, daemon=True).start()
  try:
    with BluetoothServer(BLUETOOTH_SOCKET_PATH, controller) as server:
      os.chmod(BLUETOOTH_SOCKET_PATH, 0o660)
      server.serve_forever()
  finally:
    controller.close()
    try:
      os.unlink(BLUETOOTH_SOCKET_PATH)
    except FileNotFoundError:
      pass


if __name__ == "__main__":
  main()
