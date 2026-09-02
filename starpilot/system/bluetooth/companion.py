import json
import math
import queue
import threading

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jeepney import DBusAddress, MatchRule, new_error, new_method_return, new_signal
from jeepney.low_level import HeaderFields

from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.ui.lib.starpilot_version import STARPILOT_DISPLAY_VERSION
from openpilot.starpilot.system.bluetooth.live import (
  LIVE_FRAME_RATE_HZ,
  LIVE_FRAME_SIZE,
  LIVE_NOTIFICATION_FRAGMENT_COUNT,
  LIVE_NOTIFICATION_SIZE,
  LIVE_PROTOCOL_VERSION,
  LiveSnapshot,
  LiveTelemetryPublisher,
  live_metadata,
  live_notification_fragments,
)


BLUEZ = "org.bluez"
OBJECT_MANAGER_IFACE = "org.freedesktop.DBus.ObjectManager"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
GATT_MANAGER_IFACE = "org.bluez.GattManager1"
GATT_SERVICE_IFACE = "org.bluez.GattService1"
GATT_CHARACTERISTIC_IFACE = "org.bluez.GattCharacteristic1"
ADVERTISEMENT_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"
ADVERTISEMENT_IFACE = "org.bluez.LEAdvertisement1"

COMPANION_APP_PATH = "/link/firestar/starpilot/companion"
COMPANION_SERVICE_PATH = f"{COMPANION_APP_PATH}/service0"
COMPANION_STATUS_PATH = f"{COMPANION_SERVICE_PATH}/char0"
COMPANION_COMMAND_PATH = f"{COMPANION_SERVICE_PATH}/char1"
COMPANION_RESPONSE_PATH = f"{COMPANION_SERVICE_PATH}/char2"
COMPANION_LIVE_PATH = f"{COMPANION_SERVICE_PATH}/char3"
COMPANION_ADVERTISEMENT_PATH = f"{COMPANION_APP_PATH}/advertisement0"

COMPANION_SERVICE_UUID = "9b6d1000-6f7a-4a5b-8c3d-2e1f0a9b8c7d"
COMPANION_STATUS_UUID = "9b6d1001-6f7a-4a5b-8c3d-2e1f0a9b8c7d"
COMPANION_COMMAND_UUID = "9b6d1002-6f7a-4a5b-8c3d-2e1f0a9b8c7d"
COMPANION_RESPONSE_UUID = "9b6d1003-6f7a-4a5b-8c3d-2e1f0a9b8c7d"
COMPANION_LIVE_UUID = "9b6d1004-6f7a-4a5b-8c3d-2e1f0a9b8c7d"

COMPANION_PROTOCOL_VERSION = 2
MAX_COMPANION_COMMAND_BYTES = 512
MAX_COMPANION_RESPONSE_BYTES = 512


def _wall_time() -> float:
  return datetime.now(UTC).timestamp()


def _param_text(params: Params, key: str) -> str:
  value = params.get(key, encoding="utf-8") or ""
  if isinstance(value, bytes):
    value = value.decode("utf-8", errors="ignore")
  return str(value)[:64]


# Share the Galaxy settings allow-list without importing its server.
_SETTINGS_CATALOG_PATH = Path(__file__).resolve().parents[2] / "common" / "assets" / "device_settings_layout.json"
_EDITABLE_UI_TYPES = {"toggle", "numeric", "dropdown", "color"}
_cached_editable_params: dict[str, dict[str, Any]] | None = None


def load_editable_params(path: Path | None = None) -> dict[str, dict[str, Any]]:
  """Return catalog entries a bonded phone may read or write."""
  global _cached_editable_params
  if path is None and _cached_editable_params is not None:
    return _cached_editable_params

  editable: dict[str, dict[str, Any]] = {}

  def walk(params: Any) -> None:
    for param in params or []:
      if not isinstance(param, dict):
        continue
      key = param.get("key")
      ui_type = param.get("ui_type")
      data_type = param.get("data_type")
      if key and ui_type in _EDITABLE_UI_TYPES and data_type:
        editable[str(key)] = {
          "data_type": str(data_type),
          "requires_offroad": bool(param.get("requires_offroad", False)),
        }
      walk(param.get("params"))

  try:
    with (path or _SETTINGS_CATALOG_PATH).open(encoding="utf-8") as catalog_file:
      catalog = json.load(catalog_file)
    for section in catalog:
      if isinstance(section, dict):
        walk(section.get("params"))
  except (OSError, ValueError):
    cloudlog.exception("Unable to load the companion settings catalog")

  if path is None:
    _cached_editable_params = editable
  return editable


def _coerce_param_value(data_type: str, value: Any) -> Any:
  """Coerce an incoming JSON value into stored form, mirroring /api/params."""
  if data_type == "bool":
    if isinstance(value, bool):
      return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
  if data_type == "int":
    return str(int(round(float(value))))
  if data_type == "float":
    number = float(value)
    if not math.isfinite(number):
      raise ValueError("Value must be a finite number")
    return repr(number)
  if data_type == "json":
    return json.dumps(value, separators=(",", ":"))
  return str(value)


class CompanionProtocol:
  """Versioned, allow-listed protocol for a bonded phone."""

  def __init__(self, params: Params | None = None, clock=_wall_time, params_memory: Params | None = None,
               publisher_factory=LiveTelemetryPublisher):
    self.params = params or Params()
    self.params_memory = params_memory or Params(memory=True)
    self._clock = clock
    self._publisher_factory = publisher_factory
    self._publisher = None
    self._live_lock = threading.Lock()
    self._live_listeners: set[Callable[[bytes], None]] = set()
    self._live_frame = LiveSnapshot().pack(0, 0)

  def status(self) -> dict[str, Any]:
    return {
      "protocol_version": COMPANION_PROTOCOL_VERSION,
      "device": "StarPilot",
      "version": STARPILOT_DISPLAY_VERSION,
      "branch": _param_text(self.params, "GitBranch"),
      "onroad": not self.params.get_bool("IsOffroad"),
      "live": {
        "uuid": COMPANION_LIVE_UUID,
        "protocol_version": LIVE_PROTOCOL_VERSION,
        "frame_size": LIVE_FRAME_SIZE,
        "rate_hz": LIVE_FRAME_RATE_HZ,
        "notification_size": LIVE_NOTIFICATION_SIZE,
        "notification_fragments": LIVE_NOTIFICATION_FRAGMENT_COUNT,
      },
    }

  def status_bytes(self) -> bytes:
    return json.dumps(self.status(), separators=(",", ":"), sort_keys=True).encode("utf-8")

  def live_bytes(self) -> bytes:
    with self._live_lock:
      return self._live_frame

  def add_live_listener(self, listener: Callable[[bytes], None]) -> None:
    with self._live_lock:
      self._live_listeners.add(listener)

  def remove_live_listener(self, listener: Callable[[bytes], None]) -> None:
    with self._live_lock:
      self._live_listeners.discard(listener)

  def _publish_live(self, frame: bytes) -> None:
    with self._live_lock:
      self._live_frame = frame
      listeners = tuple(self._live_listeners)
    for listener in listeners:
      try:
        listener(frame)
      except Exception:
        cloudlog.exception("Bluetooth live telemetry notification failed")

  def start(self) -> None:
    if self._publisher is not None:
      return
    self._publisher = self._publisher_factory(self._publish_live, self.params, self.params_memory)
    self._publisher.start()

  def close(self) -> None:
    publisher = self._publisher
    self._publisher = None
    if publisher is not None:
      publisher.close()

  def handle(self, payload: bytes) -> bytes:
    request_id = ""
    operation = ""
    try:
      if not payload or len(payload) > MAX_COMPANION_COMMAND_BYTES:
        raise ValueError(f"Command must be between 1 and {MAX_COMPANION_COMMAND_BYTES} bytes")
      request = json.loads(payload.decode("utf-8"))
      if not isinstance(request, dict):
        raise ValueError("Command must be a JSON object")
      request_id = str(request.get("id", ""))[:64]
      operation = str(request.get("op", ""))
      if operation == "ping":
        data = {"time": int(self._clock())}
      elif operation == "get_status":
        data = self.status()
      elif operation == "get_live_metadata":
        current = self._publisher.details() if self._publisher is not None and hasattr(self._publisher, "details") else None
        data = live_metadata(self.params, current)
      elif operation == "get_params":
        data = self._handle_get_params(request)
      elif operation == "set_params":
        data = self._handle_set_params(request)
      elif operation == "set_navigation":
        data = self._handle_set_navigation(request)
      else:
        raise ValueError(f"Unsupported companion operation: {operation or '<empty>'}")
      response = {"id": request_id, "ok": True, "op": operation, "data": data}
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
      response = {"id": request_id, "ok": False, "op": operation, "error": str(error)}
    encoded = json.dumps(response, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if len(encoded) > MAX_COMPANION_RESPONSE_BYTES and response.get("ok") and operation == "get_live_metadata":
      data = response["data"]
      for container, key in (
        (data["alert"], "text2"),
        (data["alert"], "text1"),
        (data["alert"], "type"),
        (data["model"], "name"),
        (data["model"], "key"),
        (data, "speed_limit_source"),
      ):
        container[key] = ""
        encoded = json.dumps(response, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        if len(encoded) <= MAX_COMPANION_RESPONSE_BYTES:
          break
    if len(encoded) > MAX_COMPANION_RESPONSE_BYTES:
      encoded = json.dumps({
        "id": request_id,
        "ok": False,
        "op": operation,
        "error": "Companion response exceeds the 512-byte GATT limit",
      }, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return encoded

  # Keep responses within the GATT payload limit.
  MAX_GET_PARAM_KEYS = 16

  def _read_param(self, key: str, data_type: str) -> Any:
    raw = self.params.get(key, encoding="utf-8")
    if raw is None:
      return None
    if isinstance(raw, bytes):
      raw = raw.decode("utf-8", errors="ignore")
    raw = str(raw)
    if data_type == "bool":
      return raw.strip().lower() in {"1", "true", "yes", "on"}
    if data_type == "int":
      try:
        return int(float(raw))
      except ValueError:
        return raw
    if data_type == "float":
      try:
        return float(raw)
      except ValueError:
        return raw
    return raw

  def _handle_get_params(self, request: dict[str, Any]) -> dict[str, Any]:
    keys = request.get("keys")
    if not isinstance(keys, list) or not keys:
      raise ValueError("get_params requires a non-empty 'keys' list")
    if len(keys) > self.MAX_GET_PARAM_KEYS:
      raise ValueError(f"get_params accepts at most {self.MAX_GET_PARAM_KEYS} keys per call")
    editable = load_editable_params()
    values: dict[str, Any] = {}
    for key in keys:
      meta = editable.get(str(key))
      if meta is None:
        continue
      value = self._read_param(str(key), meta["data_type"])
      if value is not None:
        values[str(key)] = value
    return values

  def _handle_set_params(self, request: dict[str, Any]) -> dict[str, Any]:
    key = str(request.get("key", ""))
    if not key:
      raise ValueError("set_params requires a 'key'")
    if "value" not in request:
      raise ValueError("set_params requires a 'value'")
    meta = load_editable_params().get(key)
    if meta is None:
      raise ValueError(f"Parameter '{key}' is not editable")
    if meta["requires_offroad"] and not self.params.get_bool("IsOffroad"):
      raise ValueError(f"'{key}' can only be changed while the car is off")
    try:
      stored = _coerce_param_value(meta["data_type"], request["value"])
    except (TypeError, ValueError) as error:
      raise ValueError(f"Invalid value for '{key}'") from error
    if isinstance(stored, bool):
      self.params.put_bool(key, stored)
    else:
      self.params.put(key, stored)
    self._refresh_toggles()
    return {"key": key, "applied": True}

  def _handle_set_navigation(self, request: dict[str, Any]) -> dict[str, Any]:
    from openpilot.starpilot.navigation.destination_store import (
      normalize_destination_payload,
      update_recent_destinations,
    )
    destination = normalize_destination_payload(request.get("destination", request))
    if destination is None:
      raise ValueError("Invalid destination payload")
    recent = update_recent_destinations(self.params.get("ApiCache_NavDestinations", encoding="utf-8") or "", destination)
    self.params.put("NavDestination", json.dumps(destination))
    self.params.put("ApiCache_NavDestinations", recent)
    return {"name": destination.get("name", "")}

  @staticmethod
  def _refresh_toggles() -> None:
    try:
      from openpilot.starpilot.common.starpilot_variables import update_starpilot_toggles
      update_starpilot_toggles()
    except Exception:
      cloudlog.exception("Unable to refresh StarPilot toggles after a companion write")


class CompanionGattApplication:
  """Exports the StarPilot companion GATT service on an existing BlueZ D-Bus connection."""

  def __init__(self, router, bluez_call: Callable[..., Any], authorize: Callable[[str], bool],
               protocol: CompanionProtocol | None = None):
    self.router = router
    self._bluez_call = bluez_call
    self._authorize = authorize
    self.protocol = protocol or CompanionProtocol()
    self._adapter_path = ""
    self._registered = False
    self._responses: dict[str, bytes] = {}
    self._notifying = False
    self._notify_lock = threading.Lock()
    self._running = True
    self._closed = False
    self._close_lock = threading.Lock()
    self._filter = self.router.filter(MatchRule(type="method_call", path_namespace=COMPANION_APP_PATH), bufsize=20)
    self._queue = self._filter.__enter__()
    self._thread = threading.Thread(target=self._serve, daemon=True)
    self._thread.start()
    self.protocol.add_live_listener(self._on_live_frame)

  @property
  def registered(self) -> bool:
    return self._registered

  def managed_objects(self) -> dict[str, dict[str, dict[str, tuple[str, Any]]]]:
    return {
      COMPANION_SERVICE_PATH: {
        GATT_SERVICE_IFACE: {
          "UUID": ("s", COMPANION_SERVICE_UUID),
          "Primary": ("b", True),
        },
      },
      COMPANION_STATUS_PATH: {
        GATT_CHARACTERISTIC_IFACE: {
          "UUID": ("s", COMPANION_STATUS_UUID),
          "Service": ("o", COMPANION_SERVICE_PATH),
          # Require a durable authenticated bond.
          "Flags": ("as", ["encrypt-authenticated-read"]),
        },
      },
      COMPANION_COMMAND_PATH: {
        GATT_CHARACTERISTIC_IFACE: {
          "UUID": ("s", COMPANION_COMMAND_UUID),
          "Service": ("o", COMPANION_SERVICE_PATH),
          "Flags": ("as", ["encrypt-authenticated-write"]),
        },
      },
      COMPANION_RESPONSE_PATH: {
        GATT_CHARACTERISTIC_IFACE: {
          "UUID": ("s", COMPANION_RESPONSE_UUID),
          "Service": ("o", COMPANION_SERVICE_PATH),
          "Flags": ("as", ["encrypt-authenticated-read"]),
        },
      },
      COMPANION_LIVE_PATH: {
        GATT_CHARACTERISTIC_IFACE: {
          "UUID": ("s", COMPANION_LIVE_UUID),
          "Service": ("o", COMPANION_SERVICE_PATH),
          "Flags": ("as", ["encrypt-authenticated-read", "encrypt-authenticated-notify", "notify"]),
          "Notifying": ("b", bool(getattr(self, "_notifying", False))),
        },
      },
    }

  def advertisement_properties(self) -> dict[str, tuple[str, Any]]:
    return {
      "Type": ("s", "peripheral"),
      "ServiceUUIDs": ("as", [COMPANION_SERVICE_UUID]),
      "LocalName": ("s", "StarPilot"),
    }

  def start(self, adapter_path: str) -> None:
    if self._registered:
      return
    self._adapter_path = adapter_path
    self._bluez_call(adapter_path, GATT_MANAGER_IFACE, "RegisterApplication", "oa{sv}", (COMPANION_APP_PATH, {}))
    try:
      self._bluez_call(adapter_path, ADVERTISEMENT_MANAGER_IFACE, "RegisterAdvertisement", "oa{sv}",
                       (COMPANION_ADVERTISEMENT_PATH, {}))
    except Exception:
      try:
        self._bluez_call(adapter_path, GATT_MANAGER_IFACE, "UnregisterApplication", "o", (COMPANION_APP_PATH,))
      except Exception:
        pass
      raise
    self._registered = True
    self.protocol.start()

  def rearm_advertisement(self) -> None:
    # BlueZ does not resume this advertisement after the central disconnects.
    with self._close_lock:
      if self._closed or not self._registered:
        return
      adapter_path = self._adapter_path
    if not adapter_path:
      return
    try:
      self._bluez_call(adapter_path, ADVERTISEMENT_MANAGER_IFACE, "UnregisterAdvertisement", "o",
                       (COMPANION_ADVERTISEMENT_PATH,))
    except Exception:
      pass
    self._bluez_call(adapter_path, ADVERTISEMENT_MANAGER_IFACE, "RegisterAdvertisement", "oa{sv}",
                     (COMPANION_ADVERTISEMENT_PATH, {}))

  def close(self) -> None:
    with self._close_lock:
      if self._closed:
        return
      self._closed = True
      with self._notify_lock:
        self._notifying = False
      self.protocol.remove_live_listener(self._on_live_frame)
      self.protocol.close()
      if self._registered:
        try:
          self._bluez_call(self._adapter_path, ADVERTISEMENT_MANAGER_IFACE, "UnregisterAdvertisement", "o",
                           (COMPANION_ADVERTISEMENT_PATH,))
        except Exception:
          pass
        try:
          self._bluez_call(self._adapter_path, GATT_MANAGER_IFACE, "UnregisterApplication", "o", (COMPANION_APP_PATH,))
        except Exception:
          pass
      self._registered = False
      self._running = False
      self._filter.__exit__(None, None, None)
      try:
        self._queue.put_nowait(None)
      except queue.Full:
        pass
      if self._thread.is_alive():
        self._thread.join(timeout=1.0)

  @staticmethod
  def _options(message) -> dict[str, Any]:
    raw = message.body[-1] if message.body and isinstance(message.body[-1], dict) else {}
    return {key: value[1] if isinstance(value, tuple) and len(value) == 2 else value for key, value in raw.items()}

  def _require_bonded_phone(self, message) -> str:
    options = self._options(message)
    # Reject classic-only bonds; CoreBluetooth reconnects require an LE LTK.
    if str(options.get("link", "")).upper() != "LE":
      raise PermissionError("An LE bonded phone is required")
    device_path = str(options.get("device", ""))
    if not device_path or not self._authorize(device_path):
      raise PermissionError("An LE bonded phone is required")
    return device_path

  @staticmethod
  def _slice_value(value: bytes, message) -> bytes:
    offset = int(CompanionGattApplication._options(message).get("offset", 0))
    if offset < 0 or offset > len(value):
      raise ValueError("Invalid characteristic offset")
    return value[offset:]

  def _properties_for(self, path: str, interface: str) -> dict[str, tuple[str, Any]]:
    if path == COMPANION_ADVERTISEMENT_PATH and interface == ADVERTISEMENT_IFACE:
      return self.advertisement_properties()
    return self.managed_objects().get(path, {}).get(interface, {})

  def _properties(self, message, path: str, member: str):
    interface = str(message.body[0]) if message.body else ""
    properties = self._properties_for(path, interface)
    if not properties:
      raise KeyError(f"Unknown interface {interface}")
    if member == "GetAll":
      return new_method_return(message, "a{sv}", (properties,))
    if member == "Get" and len(message.body) > 1:
      name = str(message.body[1])
      if name not in properties:
        raise KeyError(f"Unknown property {name}")
      return new_method_return(message, "v", (properties[name],))
    raise KeyError("Unsupported properties request")

  def _emit_live_properties(self, changed: dict[str, tuple[str, Any]]) -> None:
    emitter = DBusAddress(COMPANION_LIVE_PATH, interface=PROPERTIES_IFACE)
    self.router.send(new_signal(
      emitter,
      "PropertiesChanged",
      "sa{sv}as",
      (GATT_CHARACTERISTIC_IFACE, changed, []),
    ))

  def _on_live_frame(self, frame: bytes) -> None:
    with self._notify_lock:
      notifying = self._notifying and self._registered and not self._closed
    if notifying:
      self._emit_live_frame(frame)

  def _emit_live_frame(self, frame: bytes) -> None:
    for fragment in live_notification_fragments(frame):
      self._emit_live_properties({"Value": ("ay", fragment)})

  def _set_notifying(self, notifying: bool) -> None:
    with self._notify_lock:
      if self._notifying == notifying:
        if notifying:
          raise RuntimeError("Notifications are already enabled")
        return
      self._notifying = notifying
    self._emit_live_properties({"Notifying": ("b", notifying)})
    if notifying:
      self._emit_live_frame(self.protocol.live_bytes())

  def _dispatch(self, message):
    path = str(message.header.fields.get(HeaderFields.path, ""))
    interface = str(message.header.fields.get(HeaderFields.interface, ""))
    member = str(message.header.fields.get(HeaderFields.member, ""))
    if path == COMPANION_APP_PATH and interface == OBJECT_MANAGER_IFACE and member == "GetManagedObjects":
      return new_method_return(message, "a{oa{sa{sv}}}", (self.managed_objects(),))
    if interface == PROPERTIES_IFACE:
      return self._properties(message, path, member)
    if path == COMPANION_ADVERTISEMENT_PATH and interface == ADVERTISEMENT_IFACE and member == "Release":
      return new_method_return(message)
    if interface != GATT_CHARACTERISTIC_IFACE:
      raise KeyError("Unsupported companion interface")

    if member == "ReadValue" and path in (COMPANION_STATUS_PATH, COMPANION_RESPONSE_PATH, COMPANION_LIVE_PATH):
      device_path = self._require_bonded_phone(message)
      if path == COMPANION_STATUS_PATH:
        value = self.protocol.status_bytes()
      elif path == COMPANION_LIVE_PATH:
        value = self.protocol.live_bytes()
      else:
        value = self._responses.get(device_path, b"{}")
      return new_method_return(message, "ay", (self._slice_value(value, message),))
    if member == "WriteValue" and path == COMPANION_COMMAND_PATH:
      device_path = self._require_bonded_phone(message)
      value = bytes(message.body[0]) if message.body else b""
      self._responses[device_path] = self.protocol.handle(value)
      return new_method_return(message)
    if path == COMPANION_LIVE_PATH and member == "StartNotify":
      self._set_notifying(True)
      return new_method_return(message)
    if path == COMPANION_LIVE_PATH and member == "StopNotify":
      self._set_notifying(False)
      return new_method_return(message)
    raise KeyError("Unsupported companion characteristic operation")

  def _serve(self) -> None:
    while self._running:
      message = self._queue.get()
      if message is None:
        return
      try:
        response = self._dispatch(message)
      except PermissionError as error:
        response = new_error(message, "org.bluez.Error.NotAuthorized", "s", (str(error),))
      except ValueError as error:
        response = new_error(message, "org.bluez.Error.InvalidValueLength", "s", (str(error),))
      except Exception as error:
        response = new_error(message, "org.bluez.Error.NotSupported", "s", (str(error),))
      self.router.send(response)
