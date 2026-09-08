import json
import os
import socketserver
import threading
import time

from typing import Any

from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.starpilot.system.bluetooth.bluez import BlueZClient
from openpilot.starpilot.system.bluetooth.protocol import BLUETOOTH_SOCKET_PATH
from openpilot.starpilot.system.bluetooth.radio import BluetoothRadio


OFFROAD_COMMANDS = {"set_power", "start_scan", "stop_scan", "pair", "forget", "test_audio", "pairing_response"}
SCAN_DURATION = 20.0
AUDIO_TEST_START_DELAY = 3.0
AUDIO_TEST_HOLD_TIME = 3.0
RECONNECT_INTERVAL_SECONDS = 15.0
CONTROLLER_RECONNECT_INTERVAL_SECONDS = 5.0
RECONNECT_MAX_BACKOFF_SECONDS = 300.0
MANUAL_DISCONNECT_SUPPRESSION_SECONDS = 300.0
CONTROLLER_OFFROAD_DISCONNECT_DELAY_SECONDS = 120.0


class BluetoothController:
  def __init__(self, params: Params | None = None, bluez_factory=BlueZClient, radio: BluetoothRadio | None = None,
               params_memory: Params | None = None, sleep=time.sleep):
    self.params = params or Params()
    self.params_memory = params_memory or Params(memory=True)
    self._bluez_factory = bluez_factory
    self._radio = radio or BluetoothRadio()
    self._lock = threading.RLock()
    self._bluez: BlueZClient | None = None
    self._pairing_address = ""
    self._pairing_error = ""
    self._last_reconnect = 0.0
    self._reconnect_backoff: dict[str, tuple[int, float]] = {}
    self._manual_disconnect_until: dict[str, float] = {}
    self._offroad_since: float | None = None
    self._policy_disconnected: set[str] = set()
    self._policy_disconnect_retry_after: dict[str, float] = {}
    self._scan_deadline = 0.0
    self._audio_test_deadline = 0.0
    self._sleep = sleep
    self.params.remove("BluetoothAudioTestActive")
    self.params_memory.remove("TestAlert")

  def close(self) -> None:
    self.params.remove("BluetoothAudioTestActive")
    self.params_memory.remove("TestAlert")
    with self._lock:
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
      if self._bluez is not None:
        try:
          self._bluez.close()
        except Exception:
          pass
        self._bluez = None

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
      self._policy_disconnected.discard(normalized_address)
      self._policy_disconnect_retry_after.pop(normalized_address, None)
      try:
        with self._lock:
          self._client().disconnect(normalized_address)
      except RuntimeError as error:
        if "notconnected" not in str(error).replace(" ", "").lower():
          self._manual_disconnect_until.pop(normalized_address, None)
          raise
    elif command == "forget":
      self._client().remove(address)
      self._reconnect_backoff.pop(address.upper(), None)
      self._manual_disconnect_until.pop(address.upper(), None)
      self._policy_disconnected.discard(address.upper())
      self._policy_disconnect_retry_after.pop(address.upper(), None)
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

  def _maintain_controller_offroad_policy(self, status: dict[str, Any], now: float) -> bool:
    if not status["offroad"]:
      self._offroad_since = None
      if self._policy_disconnected:
        for address in self._policy_disconnected:
          self._reconnect_backoff.pop(address, None)
        self._policy_disconnect_retry_after.clear()
        self._last_reconnect = 0.0
      return False

    if self._offroad_since is None:
      self._offroad_since = now

    if not self.params.get_bool("BluetoothDisconnectControllersOffroad"):
      if self._policy_disconnected:
        self._policy_disconnect_retry_after.clear()
        self._last_reconnect = 0.0
      return False

    if now - self._offroad_since < CONTROLLER_OFFROAD_DISCONNECT_DELAY_SECONDS:
      return False

    for device in status["devices"]:
      if not device.get("paired") or not device.get("controller") or not device.get("connected"):
        continue
      address = str(device["address"]).upper()
      if now < self._policy_disconnect_retry_after.get(address, 0.0):
        continue
      self._policy_disconnected.add(address)
      self._policy_disconnect_retry_after[address] = now + RECONNECT_INTERVAL_SECONDS
      try:
        with self._lock:
          self._client().disconnect(address)
      except RuntimeError as error:
        if "notconnected" not in str(error).replace(" ", "").lower():
          self._policy_disconnected.discard(address)
          self._policy_disconnect_retry_after.pop(address, None)
          cloudlog.warning(f"Bluetooth offroad controller disconnect failed for {address}: {error}")
      except Exception as error:
        self._policy_disconnected.discard(address)
        self._policy_disconnect_retry_after.pop(address, None)
        cloudlog.warning(f"Bluetooth offroad controller disconnect failed for {address}: {error}")
    return True

  def _maintain_reconnects(self, status: dict[str, Any], now: float, suspend_controller_reconnect: bool) -> None:
    devices = status["devices"]
    devices_by_address = {device["address"].upper(): device for device in devices}
    for address in list(self._policy_disconnected):
      device = devices_by_address.get(address)
      if device is None or not device["paired"] or not device["trusted"]:
        self._policy_disconnected.discard(address)
        self._reconnect_backoff.pop(address, None)
      elif device["connected"]:
        self._policy_disconnected.discard(address)
        self._reconnect_backoff.pop(address, None)

    if self._pairing_address:
      return

    selected = str(status["selected_audio"])
    candidates = [device for device in devices if device["paired"] and device["trusted"] and not device["connected"]]
    candidates.sort(key=lambda device: device["address"].upper() != selected.upper())
    controller_candidates = {
      device["address"].upper() for device in candidates
      if device["controller"] or device["address"].upper() in self._policy_disconnected
    }
    reconnect_interval = CONTROLLER_RECONNECT_INTERVAL_SECONDS if controller_candidates else RECONNECT_INTERVAL_SECONDS
    if now - self._last_reconnect < reconnect_interval:
      return
    self._last_reconnect = now

    candidate_addresses = {device["address"].upper() for device in candidates}
    for address in list(self._manual_disconnect_until):
      if address not in candidate_addresses or now >= self._manual_disconnect_until[address]:
        self._manual_disconnect_until.pop(address, None)
    for address in list(self._reconnect_backoff):
      if address not in candidate_addresses:
        self._reconnect_backoff.pop(address, None)

    for device in candidates:
      address = device["address"].upper()
      controller = device["controller"] or address in self._policy_disconnected
      if not device["audio"] and not controller:
        continue
      if suspend_controller_reconnect and controller:
        continue
      if now < self._manual_disconnect_until.get(address, 0.0):
        continue
      attempts, retry_after = self._reconnect_backoff.get(address, (0, 0.0))
      if now < retry_after:
        continue
      try:
        with self._lock:
          self._client().connect(address, timeout=CONTROLLER_RECONNECT_INTERVAL_SECONDS if controller else 30.0)
        self._reconnect_backoff.pop(address, None)
      except Exception:
        attempts += 1
        delay = (CONTROLLER_RECONNECT_INTERVAL_SECONDS if controller else
                 min(RECONNECT_INTERVAL_SECONDS * (2 ** (attempts - 1)), RECONNECT_MAX_BACKOFF_SECONDS))
        self._reconnect_backoff[address] = (attempts, now + delay)
        cloudlog.warning(f"Bluetooth reconnect failed for {address}; retrying in {delay:.0f}s")

  def maintain_connections(self) -> None:
    while True:
      time.sleep(2)
      now = time.monotonic()
      if not self.params.get_bool("BluetoothEnabled"):
        self._maintain_controller_offroad_policy({"offroad": self._offroad(), "devices": []}, now)
        continue
      try:
        status = self.status()
        if not status["available"] or not status["powered"]:
          continue
        self._maintain_scan(status, now)
        suspend_controller_reconnect = self._maintain_controller_offroad_policy(status, now)
        self._maintain_reconnects(status, now, suspend_controller_reconnect)
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
