"""NetworkManager lease for the head unit's projection Wi-Fi.

The lease creates one volatile, never-default connection profile named
``starpilot-android-auto``, activates it on the Wi-Fi device, and on release
deactivates and deletes only that profile and reactivates whatever Wi-Fi
connection was active before -- unless the user switched networks meanwhile.
Credentials travel over D-Bus only; they never appear in argv or logs. The
cellular default route and DNS are left alone (``never-default``,
``ignore-auto-dns``) so the car's local network cannot take over Internet traffic.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import replace

from jeepney import DBusAddress, new_method_call
from jeepney.io.threading import DBusRouter, open_dbus_connection
from jeepney.low_level import MessageType
from jeepney.wrappers import Properties

from openpilot.starpilot.system.android_auto.bootstrap import WifiCredentials

NM = "org.freedesktop.NetworkManager"
NM_PATH = "/org/freedesktop/NetworkManager"
NM_IFACE = "org.freedesktop.NetworkManager"
NM_DEVICE_IFACE = "org.freedesktop.NetworkManager.Device"
NM_ACTIVE_IFACE = "org.freedesktop.NetworkManager.Connection.Active"
NM_SETTINGS_CONNECTION_IFACE = "org.freedesktop.NetworkManager.Settings.Connection"
NM_IP4_CONFIG_IFACE = "org.freedesktop.NetworkManager.IP4Config"
DEVICE_TYPE_WIFI = 2
ACTIVE_STATE_ACTIVATED = 2
ACTIVE_STATE_DEACTIVATED = 4
CONNECTION_ID = "starpilot-android-auto"
SECURITY_WPA3 = (32,)


class NetworkError(RuntimeError):
  pass


def connection_settings(credentials: WifiCredentials, interface: str) -> dict:
  wireless = {
    "ssid": ("ay", credentials.ssid.encode("utf-8")),
    "mode": ("s", "infrastructure"),
    "hidden": ("b", True),  # projection networks are often hidden; harmless when broadcast
  }
  if credentials.bssid:
    wireless["bssid"] = ("ay", bytes.fromhex(credentials.bssid.replace(":", "")))
  settings = {
    "connection": {
      "type": ("s", "802-11-wireless"),
      "uuid": ("s", str(uuid.uuid4())),
      "id": ("s", CONNECTION_ID),
      "interface-name": ("s", interface),
      "autoconnect": ("b", False),
      "autoconnect-retries": ("i", 1),
    },
    "802-11-wireless": wireless,
    "ipv4": {
      "method": ("s", "auto"),
      "never-default": ("b", True),
      "ignore-auto-dns": ("b", True),
      "route-metric": ("x", 3000),
    },
    "ipv6": {"method": ("s", "ignore")},
  }
  if not credentials.open:
    settings["802-11-wireless-security"] = {
      "key-mgmt": ("s", "sae" if credentials.security in SECURITY_WPA3 else "wpa-psk"),
      "psk": ("s", credentials.key),
    }
  return settings


class NetworkLease:
  def __init__(self, log: Callable[..., None], interface: str = "wlan0"):
    self.log = log
    self.interface = interface
    self.router: DBusRouter | None = None
    self.device_path = ""
    self.connection_path = ""
    self.active_path = ""
    self.previous_connection = ""
    self.local_ip = ""
    self._lock = threading.Lock()

  def _open(self) -> DBusRouter:
    if self.router is None:
      self.router = DBusRouter(open_dbus_connection(bus="SYSTEM"))
    return self.router

  def _call(self, path: str, interface: str, member: str, signature: str | None = None, body: tuple = (), timeout: float = 10.0):
    address = DBusAddress(path, bus_name=NM, interface=interface)
    message = new_method_call(address, member, signature, body) if signature else new_method_call(address, member)
    reply = self._open().send_and_get_reply(message, timeout=timeout)
    if reply.header.message_type == MessageType.error:
      raise NetworkError(f"{member} failed: {reply.body[0] if reply.body else reply.header}")
    return reply.body

  def _get(self, path: str, interface: str, name: str):
    address = DBusAddress(path, bus_name=NM, interface=interface)
    reply = self._open().send_and_get_reply(Properties(address).get(name), timeout=5.0)
    if reply.header.message_type == MessageType.error:
      raise NetworkError(f"Cannot read {name}: {reply.body[0] if reply.body else ''}")
    return reply.body[0][1]

  def _wifi_device(self) -> str:
    fallback = ""
    for path in self._call(NM_PATH, NM_IFACE, "GetDevices")[0]:
      if self._get(path, NM_DEVICE_IFACE, "DeviceType") != DEVICE_TYPE_WIFI:
        continue
      if self._get(path, NM_DEVICE_IFACE, "Interface") == self.interface:
        return path
      fallback = fallback or path
    if not fallback:
      raise NetworkError("No Wi-Fi device found")
    self.interface = self._get(fallback, NM_DEVICE_IFACE, "Interface")
    return fallback

  def acquire(self, credentials: WifiCredentials, timeout: float = 40.0, cancelled: Callable[[], bool] = lambda: False) -> str:
    """Join the projection network and return the comma's IPv4 address on it.

    The BSSID the car reports is tried first (fast, unambiguous); if that
    attempt fails, one retry matches the SSID alone in case the reported BSSID
    belongs to a different radio of the head unit.
    """
    attempts = [credentials]
    if credentials.bssid:
      attempts.append(replace(credentials, bssid=""))
    last_error: NetworkError | None = None
    for index, attempt in enumerate(attempts):
      try:
        return self._acquire_once(attempt, timeout / len(attempts), cancelled)
      except NetworkError as error:
        last_error = error
        if cancelled() or index == len(attempts) - 1:
          raise
        self.log("wifi_retry_without_bssid", error=str(error))
        self._drop_attempt()
    raise last_error or NetworkError("Could not join the projection network")

  def _drop_attempt(self) -> None:
    for path, interface, member in ((self.active_path, NM_IFACE, "DeactivateConnection"),
                                    (self.connection_path, NM_SETTINGS_CONNECTION_IFACE, "Delete")):
      if not path:
        continue
      try:
        if member == "DeactivateConnection":
          self._call(NM_PATH, NM_IFACE, member, "o", (path,))
        else:
          self._call(path, interface, member)
      except NetworkError:
        pass
    self.active_path = self.connection_path = ""

  def _acquire_once(self, credentials: WifiCredentials, timeout: float, cancelled: Callable[[], bool]) -> str:
    with self._lock:
      if not self._get(NM_PATH, NM_IFACE, "WirelessEnabled"):
        raise NetworkError("Wi-Fi is turned off on the comma")
      self.device_path = self._wifi_device()
      active = self._get(self.device_path, NM_DEVICE_IFACE, "ActiveConnection")
      if active and active != "/" and not self.previous_connection:
        try:
          previous = self._get(active, NM_ACTIVE_IFACE, "Connection")
          if self._connection_id(previous) != CONNECTION_ID:
            self.previous_connection = previous
        except NetworkError:
          pass
      self._delete_stale_profiles()
      self.log("wifi_joining", interface=self.interface, **{k: v for k, v in credentials.describe().items() if k != "key_length"},
               had_previous=bool(self.previous_connection))
      body = self._call(NM_PATH, NM_IFACE, "AddAndActivateConnection2", "a{sa{sv}}ooa{sv}",
                        (connection_settings(credentials, self.interface), self.device_path, "/",
                         {"persist": ("s", "volatile")}), timeout=15.0)
      self.connection_path, self.active_path = body[0], body[1]

    deadline = time.monotonic() + timeout
    while True:
      if cancelled():
        raise NetworkError("cancelled")
      try:
        state = self._get(self.active_path, NM_ACTIVE_IFACE, "State")
      except NetworkError as error:
        raise NetworkError("The projection network connection was removed (wrong key or out of range?)") from error
      if state == ACTIVE_STATE_ACTIVATED:
        break
      if state == ACTIVE_STATE_DEACTIVATED:
        raise NetworkError("NetworkManager could not join the projection network")
      if time.monotonic() >= deadline:
        raise NetworkError(f"Timed out joining the projection network after {timeout:.0f} s")
      time.sleep(0.25)
    self.local_ip = self._ipv4()
    self.log("wifi_joined", interface=self.interface, local_ip=self.local_ip)
    return self.local_ip

  def _connection_id(self, path: str) -> str:
    try:
      return self._call(path, NM_SETTINGS_CONNECTION_IFACE, "GetSettings")[0].get("connection", {}).get("id", ("s", ""))[1]
    except NetworkError:
      return ""

  def _ipv4(self) -> str:
    config = self._get(self.active_path, NM_ACTIVE_IFACE, "Ip4Config")
    if config and config != "/":
      for entry in self._get(config, NM_IP4_CONFIG_IFACE, "AddressData"):
        address = entry.get("address", ("s", ""))[1]
        if address:
          return address
    raise NetworkError("Joined the projection network but received no IPv4 address")

  def _delete_stale_profiles(self) -> None:
    """Remove profiles left by a crashed earlier session (volatile ones vanish on their own)."""
    settings = DBusAddress("/org/freedesktop/NetworkManager/Settings", bus_name=NM, interface="org.freedesktop.NetworkManager.Settings")
    reply = self._open().send_and_get_reply(new_method_call(settings, "ListConnections"), timeout=5.0)
    if reply.header.message_type == MessageType.error:
      return
    for path in reply.body[0]:
      try:
        body = self._call(path, NM_SETTINGS_CONNECTION_IFACE, "GetSettings")
        if body[0].get("connection", {}).get("id", ("s", ""))[1] == CONNECTION_ID:
          self._call(path, NM_SETTINGS_CONNECTION_IFACE, "Delete")
          self.log("wifi_stale_profile_removed")
      except NetworkError:
        continue

  def still_connected(self) -> bool:
    if not self.active_path:
      return False
    try:
      return self._get(self.active_path, NM_ACTIVE_IFACE, "State") == ACTIVE_STATE_ACTIVATED
    except NetworkError:
      return False

  def release(self, restore: bool = True) -> None:
    """Undo only what this lease owns. Safe to call repeatedly.

    ``restore=False`` is for a retry: the earlier network is remembered and
    reactivated only when the session finally stops, avoiding churn between attempts.
    """
    with self._lock:
      if self.router is None:
        return
      ours_active = False
      try:
        if self.device_path:
          current = self._get(self.device_path, NM_DEVICE_IFACE, "ActiveConnection")
          ours_active = current == self.active_path or current in ("", "/")
      except NetworkError:
        ours_active = True
      if self.active_path:
        try:
          self._call(NM_PATH, NM_IFACE, "DeactivateConnection", "o", (self.active_path,))
        except NetworkError:
          pass
      if self.connection_path:
        try:
          self._call(self.connection_path, NM_SETTINGS_CONNECTION_IFACE, "Delete")
        except NetworkError:
          pass  # volatile profiles delete themselves on deactivation
      if restore and ours_active and self.previous_connection and self.device_path:
        try:
          self._call(NM_PATH, NM_IFACE, "ActivateConnection", "ooo", (self.previous_connection, self.device_path, "/"))
          self.log("wifi_restored_previous")
        except NetworkError as error:
          self.log("wifi_restore_failed", error=str(error))
      self.connection_path = self.active_path = self.local_ip = ""
      if restore:
        self.previous_connection = ""
      try:
        self.router.close()
      finally:
        self.router = None
