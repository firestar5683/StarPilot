"""WAN NAT for the Wi-Fi tethering hotspot.

AGNOS kernels (4.9, CONFIG_NF_TABLES not set — verified in upstream AGNOS)
can't run NetworkManager's shared-mode firewall rules, so tethered clients
get DHCP but no WAN access. `ensure_tethering_nat()` idempotently applies
masquerade/forward rules via iptables-legacy and enables IPv4 forwarding.

`tethering_nat_thread()` re-ensures the rules whenever the kernel assigns or
removes an IPv4 address on the hotspot interface (rtnetlink subscription —
no polling). It must run in an always-on process: the WifiManager-based
trigger only exists while a settings page has constructed it.
"""

import os
import shutil
import socket
import struct
import subprocess
import threading
from collections.abc import Callable, Iterator

from openpilot.common.swaglog import cloudlog

IPTABLES = "iptables-legacy"
IPTABLES_ABSOLUTE = "/usr/sbin/iptables-legacy"  # process PATH may lack /usr/sbin
IPV4_FORWARD_SYSCTL = "net.ipv4.ip_forward=1"

# NetworkManager's default shared range (profile without pinned address-data)
NM_SHARED_SUBNET = "10.42.0.0/24"
# WifiManager's pinned tethering address (TETHERING_IP_ADDRESS/24)
WIFI_MANAGER_SUBNET = "192.168.43.0/24"
HOTSPOT_SUBNETS = (NM_SHARED_SUBNET, WIFI_MANAGER_SUBNET)

NETLINK_ROUTE = 0
SOL_NETLINK = 270
NETLINK_ADD_MEMBERSHIP = 1
RTNLGRP_IPV4_IFADDR = 5
RTM_NEWADDR = 20
RTM_DELADDR = 21
AF_INET = 2


def iptables_binary() -> str | None:
  """Resolve iptables-legacy by PATH or its distro install location.

  openpilot daemons run with a minimal PATH that excludes /usr/sbin, where
  iptables-legacy lives on AGNOS; shutil.which() alone silently fails there.
  """
  resolved = shutil.which(IPTABLES)
  if resolved is not None:
    return resolved
  if os.access(IPTABLES_ABSOLUTE, os.X_OK):
    return IPTABLES_ABSOLUTE
  return None


def _interface_subnet(interface: str) -> str | None:
  """Return the interface's current IPv4 subnet as a CIDR, or None."""
  try:
    result = subprocess.run(
      ["ip", "-4", "-o", "addr", "show", "dev", interface],
      capture_output=True, text=True, timeout=5, check=True,
    )
  except (OSError, subprocess.SubprocessError) as exc:
    cloudlog.warning(f"Failed to read {interface} addresses for tethering NAT: {exc}")
    return None

  for line in result.stdout.splitlines():
    # Example: "11: wlan0    inet 10.42.0.1/24 brd ..."
    parts = line.split()
    inet_index = parts.index("inet") if "inet" in parts else -1
    if inet_index >= 0 and len(parts) > inet_index + 1 and "/" in parts[inet_index + 1]:
      addr, prefix = parts[inet_index + 1].split("/", 1)
      try:
        prefix = int(prefix)
      except ValueError:
        continue
      if prefix > 0 and not addr.startswith("127."):
        return _subnet_cidr(addr, prefix)
  return None


def _subnet_cidr(addr: str, prefix: int) -> str | None:
  if not isinstance(prefix, int) or isinstance(prefix, bool) or prefix < 8 or prefix > 32:
    return None
  try:
    octets = [int(o) for o in addr.split(".")]
  except (AttributeError, TypeError, ValueError):
    return None
  if len(octets) != 4 or any(o < 0 or o > 255 for o in octets):
    return None
  mask = ((0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF)
  network = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
  network &= mask
  return f"{(network >> 24) & 0xFF}.{(network >> 16) & 0xFF}.{(network >> 8) & 0xFF}.{network & 0xFF}/{prefix}"


def hotspot_subnets(interface: str = "wlan0") -> tuple[str, ...]:
  """Candidate hotspot subnets to NAT, live subnet first when present."""
  subnets = []
  live = _interface_subnet(interface)
  if live is not None:
    subnets.append(live)
  for candidate in HOTSPOT_SUBNETS:
    if candidate not in subnets:
      subnets.append(candidate)
  return tuple(subnets)


def hotspot_address_active(interface: str = "wlan0") -> bool:
  """True when the interface currently holds a known hotspot subnet address."""
  return _interface_subnet(interface) in HOTSPOT_SUBNETS


def _ensure_rule(binary: str, check_args: tuple[str, ...], add_args: tuple[str, ...]) -> bool:
  """Add a rule if missing. Both the check and the add require root."""
  try:
    result = subprocess.run(["sudo", "-n", binary, *check_args],
                            capture_output=True, timeout=5)
    if result.returncode == 0:
      return True
    result = subprocess.run(["sudo", "-n", binary, *add_args],
                            capture_output=True, text=True, timeout=5)
    if result.returncode != 0:
      cloudlog.warning(f"Failed to apply tethering NAT rule ({' '.join(add_args)}): {result.stderr.strip()}")
      return False
    return True
  except (OSError, subprocess.SubprocessError) as exc:
    cloudlog.warning(f"Error applying tethering NAT rule ({' '.join(add_args)}): {exc}")
    return False


def ensure_tethering_nat(interface: str = "wlan0", include_live_subnet: bool = True) -> bool:
  """Idempotently ensure WAN NAT for the hotspot subnet(s). Never raises.

  `include_live_subnet` also NATs the interface's current subnet; only pass
  True while the hotspot is active so a client connection's LAN subnet never
  gets masqueraded. Rules for subnets that aren't routed are inert.

  Returns False (without raising) where unsupported, e.g. PCs without
  iptables-legacy.
  """
  binary = iptables_binary()
  if binary is None:
    cloudlog.warning(f"{IPTABLES} not found in PATH or at {IPTABLES_ABSOLUTE}; skipping tethering NAT")
    return False

  ok = True
  try:
    result = subprocess.run(["sudo", "-n", "sysctl", "-w", IPV4_FORWARD_SYSCTL],
                            capture_output=True, text=True, timeout=5)
    if result.returncode != 0:
      cloudlog.warning(f"Failed to enable IPv4 forwarding for tethering: {result.stderr.strip()}")
      ok = False

    subnets: list[str] = []
    if include_live_subnet:
      live = _interface_subnet(interface)
      if live is not None:
        subnets.append(live)
    for candidate in HOTSPOT_SUBNETS:
      if candidate not in subnets:
        subnets.append(candidate)

    for subnet in subnets:
      ok &= _ensure_rule(
        binary,
        ("-t", "nat", "-C", "POSTROUTING", "-s", subnet, "!", "-d", subnet, "-j", "MASQUERADE"),
        ("-t", "nat", "-A", "POSTROUTING", "-s", subnet, "!", "-d", subnet, "-j", "MASQUERADE"),
      )
      ok &= _ensure_rule(
        binary,
        ("-C", "FORWARD", "-s", subnet, "-j", "ACCEPT"),
        ("-A", "FORWARD", "-s", subnet, "-j", "ACCEPT"),
      )
      ok &= _ensure_rule(
        binary,
        ("-C", "FORWARD", "-d", subnet, "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"),
        ("-A", "FORWARD", "-d", subnet, "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"),
      )
  except (OSError, subprocess.SubprocessError) as exc:
    cloudlog.warning(f"Error applying tethering NAT: {exc}")
    return False

  return ok


def _iter_addr_events(data: bytes, ifindex: int) -> Iterator[int]:
  """Yield RTM_NEWADDR/RTM_DELADDR types for AF_INET events on ifindex."""
  offset = 0
  while offset + 16 <= len(data):
    msg_len, msg_type, _flags, _seq, _pid = struct.unpack_from("<IHHII", data, offset)
    if msg_len < 16 or offset + msg_len > len(data):
      return
    if msg_type in (RTM_NEWADDR, RTM_DELADDR) and msg_len >= 16 + 8:
      family, _prefixlen, _flags, _scope, index = struct.unpack_from("<BBBBI", data, offset + 16)
      if family == AF_INET and index == ifindex:
        yield msg_type
    offset += msg_len


def tethering_nat_thread(interface: str = "wlan0") -> Callable[[], None]:
  """Build the blocking rtnetlink monitor runner for the hotspot interface.

  Subscribes to IPv4 address-change events and re-ensures the rules when one
  lands on the hotspot interface. Wakes only on kernel address events — no
  polling. Run as a daemon thread in an always-on process.
  """
  def runner():
    try:
      ifindex = socket.if_nametoindex(interface)
    except OSError:
      cloudlog.warning(f"Interface {interface} not found; tethering NAT monitor disabled")
      return

    # Cover a hotspot that is already up when the monitor starts
    if hotspot_address_active(interface):
      ensure_tethering_nat(interface)

    try:
      sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_ROUTE)
    except OSError as exc:
      cloudlog.warning(f"Failed to open rtnetlink socket for tethering NAT: {exc}")
      return

    with sock:
      try:
        sock.bind((0, 0))
        sock.setsockopt(SOL_NETLINK, NETLINK_ADD_MEMBERSHIP, RTNLGRP_IPV4_IFADDR)
      except OSError as exc:
        cloudlog.warning(f"Failed to subscribe to address events for tethering NAT: {exc}")
        return

      while True:
        data = sock.recv(65536)  # blocks; thread is daemonized
        if any(True for _ in _iter_addr_events(data, ifindex)):
          if hotspot_address_active(interface):
            cloudlog.debug("hotspot address event; ensuring tethering NAT")
            ensure_tethering_nat(interface)

  return runner


def start_tethering_nat_monitor(interface: str = "wlan0") -> None:
  threading.Thread(target=tethering_nat_thread(interface), name="tethering_nat", daemon=True).start()
