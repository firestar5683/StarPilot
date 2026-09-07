import threading
import time
import uuid

from collections.abc import Callable
from typing import Any

from jeepney import DBusAddress, MatchRule, new_error, new_method_call, new_method_return
from jeepney.io.threading import DBusRouter, open_dbus_connection
from jeepney.low_level import HeaderFields, MessageType
from jeepney.wrappers import Properties

from openpilot.starpilot.system.bluetooth.protocol import device_capabilities, show_pairing_device


BLUEZ = "org.bluez"
OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"
ADAPTER_IFACE = "org.bluez.Adapter1"
DEVICE_IFACE = "org.bluez.Device1"
AGENT_MANAGER_IFACE = "org.bluez.AgentManager1"
AGENT_IFACE = "org.bluez.Agent1"
AGENT_PATH = "/link/firestar/starpilot/agent"
DEVICE_STATE_TIMEOUT = 5.0
# Requests that never contain a user-entered secret.
AUTO_ACCEPTABLE_AGENT_METHODS = frozenset(
  {"DisplayPinCode", "DisplayPasskey", "RequestConfirmation", "RequestAuthorization", "AuthorizeService"}
)


class BlueZError(RuntimeError):
  def __init__(self, name: str, detail: str):
    super().__init__(detail)
    self.name = name


def unwrap_variant(value: Any) -> Any:
  if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str):
    return unwrap_variant(value[1])
  if isinstance(value, dict):
    return {key: unwrap_variant(item) for key, item in value.items()}
  if isinstance(value, list):
    return [unwrap_variant(item) for item in value]
  return value


class PairingAgent:
  def __init__(self):
    self._condition = threading.Condition()
    self._prompt: dict[str, Any] | None = None
    self._response: tuple[bool, str] | None = None
    self._generation = 0
    self._auto_accept_paths: set[str] = set()
    self._auto_accept_incoming = False
    # Authorizes silent pairing only during an explicit companion window.
    self.auto_accept_handler: Callable[[str], bool] | None = None

  def should_auto_accept(self, device_path: str) -> bool:
    handler = self.auto_accept_handler
    if handler is None:
      return False
    try:
      return bool(handler(device_path))
    except Exception:
      return False

  @property
  def prompt(self) -> dict[str, Any] | None:
    with self._condition:
      return dict(self._prompt) if self._prompt is not None else None

  def clear(self) -> None:
    with self._condition:
      self._generation += 1
      self._prompt = None
      self._response = None
      self._condition.notify_all()

  def display(self, kind: str, device_path: str, value: str) -> None:
    with self._condition:
      self._generation += 1
      self._prompt = {"id": uuid.uuid4().hex, "kind": kind, "device_path": device_path, "value": value, "display_only": True}

  def request(self, kind: str, device_path: str, value: str = "", timeout: float = 60.0) -> tuple[bool, str]:
    if self.auto_accept(kind, device_path):
      return True, ""
    prompt_id = uuid.uuid4().hex
    with self._condition:
      self._generation += 1
      generation = self._generation
      self._response = None
      self._prompt = {"id": prompt_id, "kind": kind, "device_path": device_path, "value": value, "display_only": False}
      deadline = time.monotonic() + timeout
      while self._response is None and self._generation == generation:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
          self._prompt = None
          return False, ""
        self._condition.wait(remaining)
      if self._generation != generation:
        return False, ""
      response = self._response
      self._response = None
      self._prompt = None
      return response

  def respond(self, prompt_id: str, accepted: bool, value: str = "") -> bool:
    with self._condition:
      if self._prompt is None or self._prompt.get("id") != prompt_id or self._prompt.get("display_only"):
        return False
      self._response = accepted, value
      self._condition.notify_all()
      return True

  def set_auto_accept(self, device_path: str, enabled: bool) -> None:
    with self._condition:
      if enabled:
        self._auto_accept_paths.add(device_path)
      else:
        self._auto_accept_paths.discard(device_path)

  def set_auto_accept_incoming(self, enabled: bool) -> None:
    with self._condition:
      self._auto_accept_incoming = enabled

  def auto_accept(self, kind: str, device_path: str) -> bool:
    with self._condition:
      configured = self._auto_accept_incoming or device_path in self._auto_accept_paths
    return kind in {"confirmation", "authorization"} and (configured or self.should_auto_accept(device_path))

class BlueZClient:
  def __init__(self):
    self.router = DBusRouter(open_dbus_connection(bus="SYSTEM"))
    self._request_lock = threading.RLock()
    self._closed = threading.Event()
    self.agent = PairingAgent()
    self._agent_filter = self.router.filter(MatchRule(type="method_call", interface=AGENT_IFACE, path=AGENT_PATH), bufsize=20)
    self._agent_queue = self._agent_filter.__enter__()
    self._agent_thread = threading.Thread(target=self._agent_loop, daemon=True)
    self._agent_thread.start()
    self._register_agent()

  def close(self) -> None:
    if self._closed.is_set():
      return
    self._closed.set()
    self.agent.clear()
    try:
      self._agent_queue.put_nowait(None)
    except Exception:
      pass
    with self._request_lock:
      try:
        self._call("/org/bluez", AGENT_MANAGER_IFACE, "UnregisterAgent", "o", (AGENT_PATH,))
      except Exception:
        pass
    self._agent_filter.__exit__(None, None, None)
    self.router.close()
    self._agent_thread.join(timeout=1.0)

  def _call(self, path: str, interface: str, member: str, signature: str | None = None, body: tuple = (), timeout: float = 15.0):
    address = DBusAddress(path, bus_name=BLUEZ, interface=interface)
    message = new_method_call(address, member, signature, body) if signature is not None else new_method_call(address, member)
    with self._request_lock:
      reply = self.router.send_and_get_reply(message, timeout=timeout)
    if reply.header.message_type == MessageType.error:
      error_name = reply.header.fields.get(HeaderFields.error_name, "org.bluez.Error.Failed")
      detail = reply.body[0] if reply.body else error_name
      raise BlueZError(str(error_name), str(detail))
    return reply.body

  def _register_agent(self) -> None:
    try:
      self._call("/org/bluez", AGENT_MANAGER_IFACE, "RegisterAgent", "os", (AGENT_PATH, "KeyboardDisplay"))
    except RuntimeError as error:
      if "alreadyexists" not in str(error).replace(" ", "").lower():
        raise
    self._call("/org/bluez", AGENT_MANAGER_IFACE, "RequestDefaultAgent", "o", (AGENT_PATH,))

  def _agent_loop(self) -> None:
    while not self._closed.is_set():
      message = self._agent_queue.get()
      if message is None:
        break
      member = message.header.fields.get(HeaderFields.member, "")
      device_path = str(message.body[0]) if message.body else ""
      if member in {"RequestPinCode", "RequestPasskey", "RequestConfirmation", "RequestAuthorization", "AuthorizeService"}:
        threading.Thread(target=self._handle_agent_request, args=(message, member, device_path), daemon=True).start()
        continue
      try:
        response_signature = None
        response_body: tuple = ()
        auto = member in AUTO_ACCEPTABLE_AGENT_METHODS and self.agent.should_auto_accept(device_path)
        if member == "Release":
          self.agent.clear()
        elif member == "DisplayPinCode":
          if not auto:
            self.agent.display("display_pin", device_path, str(message.body[1]))
        elif member == "DisplayPasskey":
          if not auto:
            self.agent.display("display_passkey", device_path, f"{int(message.body[1]):06d}")
        elif member == "Cancel":
          self.agent.clear()
        else:
          raise RuntimeError(f"Unsupported pairing request: {member}")
        self._send_agent_reply(new_method_return(message, response_signature, response_body))
      except PermissionError:
        self._send_agent_reply(new_error(message, "org.bluez.Error.Rejected", "s", ("Pairing rejected",)))
      except Exception as error:
        self._send_agent_reply(new_error(message, "org.bluez.Error.Canceled", "s", (str(error),)))

  def _send_agent_reply(self, message: Any) -> None:
    try:
      self.router.send(message)
    except Exception:
      self._closed.set()

  def _handle_agent_request(self, message: Any, member: str, device_path: str) -> None:
    try:
      response_signature = None
      response_body: tuple = ()
      if member == "RequestPinCode":
        accepted, value = self.agent.request("pin", device_path)
        if not accepted:
          raise PermissionError
        response_signature, response_body = "s", (value,)
      elif member == "RequestPasskey":
        accepted, value = self.agent.request("passkey", device_path)
        if not accepted:
          raise PermissionError
        response_signature, response_body = "u", (int(value),)
      elif member == "RequestConfirmation":
        accepted, _ = self.agent.request("confirmation", device_path, f"{int(message.body[1]):06d}")
        if not accepted:
          raise PermissionError
      else:
        accepted, _ = self.agent.request("authorization", device_path)
        if not accepted:
          raise PermissionError
      self._send_agent_reply(new_method_return(message, response_signature, response_body))
    except PermissionError:
      self._send_agent_reply(new_error(message, "org.bluez.Error.Rejected", "s", ("Pairing rejected",)))
    except Exception as error:
      self._send_agent_reply(new_error(message, "org.bluez.Error.Canceled", "s", (str(error),)))

  def managed_objects(self) -> dict[str, dict[str, dict[str, Any]]]:
    body = self._call("/", OBJECT_MANAGER, "GetManagedObjects")
    return unwrap_variant(body[0]) if body else {}

  def adapter(self, objects: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    objects = self.managed_objects() if objects is None else objects
    for path, interfaces in objects.items():
      if ADAPTER_IFACE in interfaces:
        return path, interfaces[ADAPTER_IFACE]
    raise RuntimeError("Bluetooth adapter is not available")

  def devices(self, objects: dict[str, Any] | None = None, include_hidden: bool = False,
              include_discovering: bool = False) -> list[dict[str, Any]]:
    objects = self.managed_objects() if objects is None else objects
    devices = []
    for path, interfaces in objects.items():
      if DEVICE_IFACE not in interfaces:
        continue
      props = interfaces[DEVICE_IFACE]
      uuids = [str(value).lower() for value in props.get("UUIDs", [])]
      audio, controller = device_capabilities(uuids, int(props.get("Class", 0)), str(props.get("Icon", "")))
      device = {
        "path": path,
        "address": str(props.get("Address", "")),
        "name": str(props.get("Alias") or props.get("Name") or props.get("Address") or "Unknown device"),
        "paired": bool(props.get("Paired", False)),
        "trusted": bool(props.get("Trusted", False)),
        "connected": bool(props.get("Connected", False)),
        "blocked": bool(props.get("Blocked", False)),
        "rssi": int(props["RSSI"]) if "RSSI" in props else None,
        "uuids": uuids,
        "audio": audio,
        "controller": controller,
      }
      if include_hidden or show_pairing_device(device["address"], device["name"], device["paired"], device["trusted"], device["connected"],
                                               device["blocked"], audio, controller, include_discovering):
        devices.append(device)
    return sorted(devices, key=lambda device: (not device["connected"], not device["paired"], -(device["rssi"] or -127), device["name"].lower()))

  def status(self) -> dict[str, Any]:
    objects = self.managed_objects()
    _, adapter = self.adapter(objects)
    prompt = self.agent.prompt
    if prompt is not None:
      prompt = dict(prompt)
      device = objects.get(prompt.get("device_path", ""), {}).get(DEVICE_IFACE, {})
      prompt["address"] = str(device.get("Address", ""))
      prompt["name"] = str(device.get("Alias") or device.get("Name") or prompt["address"] or "Bluetooth device")
    return {
      "powered": bool(adapter.get("Powered", False)),
      "discovering": bool(adapter.get("Discovering", False)),
      "devices": self.devices(objects, include_discovering=bool(adapter.get("Discovering", False))),
      "prompt": prompt,
    }

  def set_adapter_property(self, name: str, signature: str, value: Any) -> None:
    path, _ = self.adapter()
    address = DBusAddress(path, bus_name=BLUEZ, interface=ADAPTER_IFACE)
    with self._request_lock:
      reply = self.router.send_and_get_reply(Properties(address).set(name, signature, value), timeout=10.0)
    if reply.header.message_type == MessageType.error:
      raise RuntimeError(str(reply.body[0] if reply.body else f"Unable to set adapter {name}"))

  def set_powered(self, powered: bool) -> None:
    self.set_adapter_property("Powered", "b", powered)

  def set_pairing_mode(self, enabled: bool) -> None:
    if enabled:
      self.set_adapter_property("PairableTimeout", "u", 0)
      self.set_adapter_property("DiscoverableTimeout", "u", 0)
      self.set_adapter_property("Pairable", "b", True)
      try:
        self.set_adapter_property("Discoverable", "b", True)
      except Exception:
        self.set_adapter_property("Pairable", "b", False)
        raise
    else:
      error: Exception | None = None
      for name in ("Discoverable", "Pairable"):
        try:
          self.set_adapter_property(name, "b", False)
        except Exception as current_error:
          error = error or current_error
      if error is not None:
        raise error

  def set_discoverable(self, discoverable: bool) -> None:
    path, _ = self.adapter()
    address = DBusAddress(path, bus_name=BLUEZ, interface=ADAPTER_IFACE)
    with self._request_lock:
      reply = self.router.send_and_get_reply(Properties(address).set("Pairable", "b", True), timeout=10.0)
    if reply.header.message_type == MessageType.error:
      raise RuntimeError(str(reply.body[0] if reply.body else "Unable to enable Bluetooth pairing"))
    with self._request_lock:
      reply = self.router.send_and_get_reply(Properties(address).set("DiscoverableTimeout", "u", 0), timeout=10.0)
    if reply.header.message_type == MessageType.error:
      raise RuntimeError(str(reply.body[0] if reply.body else "Unable to configure Bluetooth discoverability"))
    with self._request_lock:
      reply = self.router.send_and_get_reply(Properties(address).set("Discoverable", "b", discoverable), timeout=10.0)
    if reply.header.message_type == MessageType.error:
      raise RuntimeError(str(reply.body[0] if reply.body else "Unable to change Bluetooth discoverability"))

  def start_discovery(self) -> None:
    path, props = self.adapter()
    if props.get("Discovering", False):
      return
    try:
      self._call(path, ADAPTER_IFACE, "StartDiscovery")
    except BlueZError as error:
      # A concurrent scan already reached the desired state.
      if error.name != "org.bluez.Error.InProgress":
        raise

  def stop_discovery(self) -> None:
    path, props = self.adapter()
    if props.get("Discovering", False):
      self._call(path, ADAPTER_IFACE, "StopDiscovery")

  def device_for_address(self, address: str) -> dict[str, Any]:
    normalized = address.upper()
    for device in self.devices(self.managed_objects(), include_hidden=True):
      if device["address"].upper() == normalized:
        return device
    raise RuntimeError(f"Bluetooth device {address} was not found")

  def paired_device_for_path(self, path: str) -> dict[str, Any] | None:
    interfaces = self.managed_objects().get(path, {})
    props = interfaces.get(DEVICE_IFACE)
    # Bonded confirms persisted keys; fall back for older BlueZ releases.
    bonded = bool(props.get("Bonded", props.get("Paired", False))) if props is not None else False
    if props is None or not bonded:
      return None
    return {
      "path": path,
      "address": str(props.get("Address", "")),
      "name": str(props.get("Alias") or props.get("Name") or props.get("Address") or "Bluetooth device"),
      "paired": True,
      "bonded": True,
      "trusted": bool(props.get("Trusted", False)),
      "connected": bool(props.get("Connected", False)),
    }

  def set_device_property(self, address: str, name: str, signature: str, value: Any) -> None:
    device = self.device_for_address(address)
    dbus_address = DBusAddress(device["path"], bus_name=BLUEZ, interface=DEVICE_IFACE)
    with self._request_lock:
      reply = self.router.send_and_get_reply(Properties(dbus_address).set(name, signature, value), timeout=10.0)
    if reply.header.message_type == MessageType.error:
      raise RuntimeError(str(reply.body[0] if reply.body else f"Unable to set {name}"))

  def pair(self, address: str, device_path: str | None = None) -> None:
    self._register_agent()
    device = {"path": device_path} if device_path else self.device_for_address(address)
    self.agent.set_auto_accept(device["path"], True)
    try:
      self._call(device["path"], DEVICE_IFACE, "Pair", timeout=90.0)
    finally:
      self.agent.set_auto_accept(device["path"], False)
    self.set_device_property(address, "Trusted", "b", True)
    self.agent.clear()

  def connect(self, address: str) -> None:
    device = self.device_for_address(address)
    self._call(device["path"], DEVICE_IFACE, "Connect", timeout=30.0)
    self._wait_for_connection_state(address, True)

  def disconnect(self, address: str) -> None:
    device = self.device_for_address(address)
    self._call(device["path"], DEVICE_IFACE, "Disconnect", timeout=15.0)
    self._wait_for_connection_state(address, False)

  def _wait_for_connection_state(self, address: str, connected: bool) -> None:
    deadline = time.monotonic() + DEVICE_STATE_TIMEOUT
    while True:
      try:
        if self.device_for_address(address).get("connected", False) == connected:
          return
      except RuntimeError as error:
        if not connected and "was not found" in str(error):
          return
        raise
      if time.monotonic() >= deadline:
        state = "connect" if connected else "disconnect"
        raise RuntimeError(f"Bluetooth device did not {state}")
      time.sleep(0.1)

  def remove(self, address: str) -> None:
    adapter_path, _ = self.adapter()
    device = self.device_for_address(address)
    self._call(adapter_path, ADAPTER_IFACE, "RemoveDevice", "o", (device["path"],))
