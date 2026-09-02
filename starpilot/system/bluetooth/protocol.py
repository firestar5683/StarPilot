import json
import os
import socket
import threading
import time

from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from openpilot.common.params import Params


BLUETOOTH_SOCKET_PATH = "/tmp/starpilot-bluetooth.sock"
BLUETOOTH_RADIO_HELPER = "/usr/comma/bluetooth-radio"
A2DP_SINK_UUID = "0000110b-0000-1000-8000-00805f9b34fb"
HID_UUID = "00001124-0000-1000-8000-00805f9b34fb"
HOG_UUID = "00001812-0000-1000-8000-00805f9b34fb"
SPP_UUID = "00001101-0000-1000-8000-00805f9b34fb"
COMMAND_TIMEOUTS = {
  "set_power": 90.0,
  "start_scan": 20.0,
  "stop_scan": 20.0,
  "connect": 35.0,
  "disconnect": 20.0,
  "forget": 20.0,
  "test_audio": 10.0,
  "elm_open": 15.0,
  "elm_close": 5.0,
  "elm_command": 20.0,
  "elm_read_dtcs": 30.0,
}
TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class BluetoothDevice:
  address: str
  name: str
  paired: bool = False
  trusted: bool = False
  connected: bool = False
  blocked: bool = False
  rssi: int | None = None
  uuids: tuple[str, ...] = ()
  audio: bool = False
  controller: bool = False
  serial: bool = False

  @classmethod
  def from_dict(cls, value: dict[str, Any]) -> "BluetoothDevice":
    return cls(
      address=str(value.get("address", "")),
      name=str(value.get("name", value.get("address", "Unknown device"))),
      paired=bool(value.get("paired", False)),
      trusted=bool(value.get("trusted", False)),
      connected=bool(value.get("connected", False)),
      blocked=bool(value.get("blocked", False)),
      rssi=int(value["rssi"]) if value.get("rssi") is not None else None,
      uuids=tuple(str(uuid).lower() for uuid in value.get("uuids", ())),
      audio=bool(value.get("audio", False)),
      controller=bool(value.get("controller", False)),
      serial=bool(value.get("serial", False)),
    )


@dataclass(frozen=True)
class BluetoothStatus:
  available: bool = False
  enabled: bool = False
  powered: bool = False
  discovering: bool = False
  offroad: bool = False
  selected_audio: str = ""
  pairing_address: str = ""
  devices: tuple[BluetoothDevice, ...] = ()
  prompt: dict[str, Any] | None = None
  error: str = ""

  @classmethod
  def from_dict(cls, value: dict[str, Any]) -> "BluetoothStatus":
    return cls(
      available=bool(value.get("available", False)),
      enabled=bool(value.get("enabled", False)),
      powered=bool(value.get("powered", False)),
      discovering=bool(value.get("discovering", False)),
      offroad=bool(value.get("offroad", False)),
      selected_audio=str(value.get("selected_audio", "")),
      pairing_address=str(value.get("pairing_address", "")),
      devices=tuple(BluetoothDevice.from_dict(device) for device in value.get("devices", ())),
      prompt=value.get("prompt"),
      error=str(value.get("error", "")),
    )


def device_capabilities(uuids: list[str] | tuple[str, ...], bluetooth_class: int = 0, icon: str = "") -> tuple[bool, bool, bool]:
  normalized = {str(uuid).lower() for uuid in uuids}
  major_class = (int(bluetooth_class) >> 8) & 0x1F
  audio = A2DP_SINK_UUID in normalized or major_class == 0x04 or icon in {"audio-card", "audio-headphones", "audio-headset"}
  controller = HID_UUID in normalized or HOG_UUID in normalized or major_class == 0x05 or icon in {"input-gaming", "input-mouse", "input-keyboard"}
  serial = SPP_UUID in normalized
  return audio, controller, serial


def show_pairing_device(address: str, name: str, paired: bool, trusted: bool, connected: bool, blocked: bool,
                        audio: bool, controller: bool, serial: bool = False, discovering: bool = False) -> bool:
  known = paired or trusted or connected
  normalized_address = "".join(character for character in address.upper() if character.isalnum())
  normalized_name = "".join(character for character in name.upper() if character.isalnum())
  named = bool(name) and name != "Unknown device" and normalized_name != normalized_address
  return known or (named and not blocked and (audio or controller or serial or discovering))


class _DesktopFakeBluetooth:
  """Small stateful fallback for desktop UI demos when bluetooth_managerd is absent."""
  def __init__(self):
    self._lock = threading.Lock()
    self._enabled = True
    self._discovering = False
    self._selected_audio = "00:11:22:33:44:55"
    self._devices = (
      BluetoothDevice("00:11:22:33:44:55", "Bluetooth Speaker", paired=True, trusted=True, connected=True, audio=True, rssi=-34),
      BluetoothDevice("AA:BB:CC:DD:EE:FF", "Game Controller", controller=True, rssi=-48),
      BluetoothDevice("10:20:30:40:50:60", "Wireless Headphones", audio=True, rssi=-63),
    )

  def status(self) -> BluetoothStatus:
    with self._lock:
      return BluetoothStatus(
        available=True,
        enabled=self._enabled,
        powered=self._enabled,
        discovering=self._discovering,
        # Desktop demos do not run bluetooth_managerd, so keep the mock usable from Settings.
        offroad=True,
        selected_audio=self._selected_audio,
        devices=self._devices,
      )

  def _device_index(self, address: str) -> int:
    normalized_address = address.upper()
    for index, device in enumerate(self._devices):
      if device.address.upper() == normalized_address:
        return index
    raise RuntimeError("Bluetooth device not found")

  def _replace_device(self, address: str, **changes: Any) -> BluetoothDevice:
    index = self._device_index(address)
    device = replace(self._devices[index], **changes)
    self._devices = (*self._devices[:index], device, *self._devices[index + 1:])
    return device

  def _require_enabled(self) -> None:
    if not self._enabled:
      raise RuntimeError("Enable Bluetooth before continuing")

  def call(self, command: str, **payload: Any) -> dict[str, Any]:
    with self._lock:
      address = str(payload.get("address", ""))
      if command == "set_power":
        self._enabled = bool(payload.get("enabled", False))
        self._discovering = False
        if not self._enabled:
          self._devices = tuple(replace(device, connected=False) for device in self._devices)
      elif command == "start_scan":
        self._require_enabled()
        self._discovering = True
      elif command == "stop_scan":
        self._discovering = False
      elif command == "pair":
        self._require_enabled()
        self._replace_device(address, paired=True, trusted=True)
      elif command == "connect":
        self._require_enabled()
        device = self._devices[self._device_index(address)]
        if not device.paired:
          raise RuntimeError("Pair the Bluetooth device before connecting")
        self._replace_device(address, connected=True)
      elif command == "disconnect":
        self._replace_device(address, connected=False)
      elif command == "forget":
        self._replace_device(address, paired=False, trusted=False, connected=False)
        if self._selected_audio.upper() == address.upper():
          self._selected_audio = ""
      elif command == "select_audio":
        if not address:
          self._selected_audio = ""
        else:
          device = self._devices[self._device_index(address)]
          if not device.audio:
            raise RuntimeError("Selected device does not support Bluetooth audio")
          self._selected_audio = device.address
      elif command == "test_audio":
        device = self._devices[self._device_index(address)]
        if not device.audio:
          raise RuntimeError("Selected device does not support Bluetooth audio")
        if not device.paired or not device.connected:
          raise RuntimeError("Connect the Bluetooth audio device before testing")
        self._selected_audio = device.address
        return {"audio_test_delay_ms": 3000}
      elif command != "pairing_response":
        raise RuntimeError(f"Unknown Bluetooth command: {command}")
      return {}


class BluetoothClient:
  def __init__(self, socket_path: str = BLUETOOTH_SOCKET_PATH, timeout: float = 5.0):
    self.socket_path = socket_path
    self.timeout = timeout
    self._desktop_fake: _DesktopFakeBluetooth | None = None

  def _get_desktop_fake(self) -> _DesktopFakeBluetooth | None:
    if not (os.getenv("SP_ALLOW_DESKTOP_FAKE_BLUETOOTH", "0").lower() in TRUE_VALUES and
            os.getenv("SIMULATION", "0").lower() in TRUE_VALUES and
            os.getenv("NOBOARD", "0").lower() in TRUE_VALUES and
            not os.path.exists(self.socket_path)):
      return None
    from openpilot.system.hardware import PC
    if not PC:
      return None
    if self._desktop_fake is None:
      self._desktop_fake = _DesktopFakeBluetooth()
    return self._desktop_fake

  def call(self, command: str, **payload: Any) -> dict[str, Any]:
    fake = self._get_desktop_fake()
    if fake is not None:
      return fake.call(command, **payload)

    request = json.dumps({"command": command, **payload}, separators=(",", ":")).encode() + b"\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
      sock.settimeout(max(self.timeout, COMMAND_TIMEOUTS.get(command, 0.0)))
      sock.connect(self.socket_path)
      sock.sendall(request)
      response = bytearray()
      while not response.endswith(b"\n"):
        chunk = sock.recv(65536)
        if not chunk:
          break
        response.extend(chunk)

    if not response:
      raise RuntimeError("Bluetooth service returned no response")
    result = json.loads(response)
    if not result.get("ok", False):
      raise RuntimeError(str(result.get("error", "Bluetooth operation failed")))
    return result

  def status(self) -> BluetoothStatus:
    fake = self._get_desktop_fake()
    if fake is not None:
      return fake.status()
    if not os.path.exists(self.socket_path):
      params = Params()
      return BluetoothStatus(
        available=Path(BLUETOOTH_RADIO_HELPER).is_file(),
        enabled=params.get_bool("BluetoothEnabled"),
        offroad=params.get_bool("IsOffroad"),
        selected_audio=params.get("BluetoothAudioAddress", encoding="utf-8") or "",
      )
    return BluetoothStatus.from_dict(self.call("status").get("status", {}))

  @staticmethod
  def serialize_status(status: BluetoothStatus) -> dict[str, Any]:
    return asdict(status)

  def set_power(self, enabled: bool) -> None:
    fake = self._get_desktop_fake()
    if fake is not None:
      fake.call("set_power", enabled=enabled)
      return

    params = Params()
    bootstrap = enabled and not os.path.exists(self.socket_path)
    if bootstrap:
      params.put_bool("BluetoothEnabled", True)
      deadline = time.monotonic() + max(self.timeout, 45.0)
      while not os.path.exists(self.socket_path):
        if time.monotonic() >= deadline:
          params.put_bool("BluetoothEnabled", False)
          raise RuntimeError("Bluetooth service did not start")
        time.sleep(0.05)
    try:
      self.call("set_power", enabled=enabled)
    except Exception:
      if bootstrap:
        params.put_bool("BluetoothEnabled", False)
      raise

  def start_scan(self) -> None:
    self.call("start_scan")

  def stop_scan(self) -> None:
    self.call("stop_scan")

  def pair(self, address: str) -> None:
    self.call("pair", address=address)

  def connect(self, address: str) -> None:
    self.call("connect", address=address)

  def disconnect(self, address: str) -> None:
    self.call("disconnect", address=address)

  def forget(self, address: str) -> None:
    self.call("forget", address=address)

  def select_audio(self, address: str) -> None:
    self.call("select_audio", address=address)

  def test_audio(self, address: str) -> float:
    result = self.call("test_audio", address=address)
    return max(0.0, float(result.get("audio_test_delay_ms", 0)) / 1000.0)

  def elm_open(self, address: str) -> dict[str, Any]:
    return self.call("elm_open", address=address)

  def elm_close(self, address: str) -> dict[str, Any]:
    return self.call("elm_close", address=address)

  def elm_command(self, address: str, value: str) -> dict[str, Any]:
    return self.call("elm_command", address=address, value=value)

  def elm_read_dtcs(self, address: str) -> dict[str, Any]:
    return self.call("elm_read_dtcs", address=address)

  def respond(self, prompt_id: str, accepted: bool, value: str = "") -> None:
    self.call("pairing_response", prompt_id=prompt_id, accepted=accepted, value=value)
