"""Bonjour advertisement for the on-device Galaxy HTTP service."""

from __future__ import annotations

import ipaddress
import socket
import threading
from collections.abc import Callable

from openpilot.common.swaglog import cloudlog


GALAXY_SERVICE_TYPE = "_galaxy._tcp.local."
GALAXY_SERVICE_PORT = 8082
ADDRESS_POLL_INTERVAL_SECONDS = 5.0


def _service_label(identifier: str | None = None) -> str:
  raw = (identifier or socket.gethostname().split(".", 1)[0] or "comma").strip()
  safe = "".join(character if character.isalnum() or character == "-" else "-" for character in raw)
  safe = safe.strip("-")[:40] or "comma"
  return f"StarPilot {safe}"


def _valid_ipv4(value: str | None) -> str | None:
  try:
    address = ipaddress.ip_address(str(value or "").strip())
  except ValueError:
    return None
  return str(address) if address.version == 4 and not address.is_loopback else None


class GalaxyBonjourAdvertiser:
  """Keep Galaxy discoverable while the comma's LAN address changes."""

  def __init__(
    self,
    address_provider: Callable[[], str | None],
    *,
    port: int = GALAXY_SERVICE_PORT,
    identifier: str | None = None,
    poll_interval: float = ADDRESS_POLL_INTERVAL_SECONDS,
  ) -> None:
    self._address_provider = address_provider
    self._port = port
    self._label = _service_label(identifier)
    self._poll_interval = poll_interval
    self._stop_event = threading.Event()
    self._thread: threading.Thread | None = None
    self._zeroconf = None
    self._service_info = None

  def start(self) -> None:
    if self._thread is not None:
      return
    self._thread = threading.Thread(target=self._run, name="galaxy-bonjour", daemon=True)
    self._thread.start()

  def close(self) -> None:
    self._stop_event.set()
    if self._thread is not None and self._thread is not threading.current_thread():
      self._thread.join(timeout=max(self._poll_interval + 1.0, 2.0))
    self._thread = None
    self._unregister()

  def _run(self) -> None:
    current_address = None
    while not self._stop_event.is_set():
      address = None
      try:
        address = _valid_ipv4(self._address_provider())
        if address != current_address or (address is not None and self._zeroconf is None):
          self._unregister()
          if address is not None:
            self._register(address)
          current_address = address
      except ModuleNotFoundError:
        current_address = address
        cloudlog.error("Galaxy Bonjour is unavailable because the zeroconf dependency is not installed")
      except Exception:
        cloudlog.exception("Galaxy Bonjour advertisement failed")
      self._stop_event.wait(self._poll_interval)

  def _register(self, address: str) -> None:
    # Import lazily so a stale device environment can still run Galaxy and use
    # the app's legacy LAN scan until its managed dependencies are refreshed.
    from zeroconf import IPVersion, InterfaceChoice, ServiceInfo, Zeroconf

    hostname = f"{self._label.lower().replace(' ', '-')}.local."
    service_info = ServiceInfo(
      GALAXY_SERVICE_TYPE,
      f"{self._label}.{GALAXY_SERVICE_TYPE}",
      addresses=[socket.inet_aton(address)],
      port=self._port,
      properties={
        "address": address,
        "api": "1",
        "path": "/",
        "port": str(self._port),
      },
      server=hostname,
    )
    # Galaxy only needs the interface that owns the selected LAN address. This
    # also avoids binding unrelated tunnel/AWDL interfaces on multihomed hosts.
    zeroconf = Zeroconf(interfaces=InterfaceChoice.Default, ip_version=IPVersion.V4Only)
    try:
      zeroconf.register_service(service_info)
    except Exception:
      zeroconf.close()
      raise
    self._zeroconf = zeroconf
    self._service_info = service_info
    cloudlog.info(f"Galaxy Bonjour advertised {service_info.name} at {address}:{self._port}")

  def _unregister(self) -> None:
    zeroconf = self._zeroconf
    service_info = self._service_info
    self._zeroconf = None
    self._service_info = None
    if zeroconf is None:
      return
    try:
      if service_info is not None:
        zeroconf.unregister_service(service_info)
    except Exception:
      cloudlog.exception("Unable to unregister Galaxy Bonjour service")
    finally:
      zeroconf.close()
