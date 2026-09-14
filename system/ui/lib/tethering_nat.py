"""WAN NAT for the Wi-Fi tethering hotspot.

AGNOS kernels (4.9, CONFIG_NF_TABLES not set — verified in upstream AGNOS)
can't run NetworkManager's shared-mode firewall rules, so tethered clients
get DHCP but no WAN access. `ensure_tethering_nat()` idempotently applies
masquerade/forward rules via iptables-legacy and enables IPv4 forwarding.
Safe to call repeatedly, from any hotspot activation path.
"""

import shutil
import subprocess

from openpilot.common.swaglog import cloudlog

IPTABLES = "iptables-legacy"
IPV4_FORWARD_SYSCTL = "net.ipv4.ip_forward=1"

# NetworkManager's default shared range (profile without pinned address-data)
NM_SHARED_SUBNET = "10.42.0.0/24"
# WifiManager's pinned tethering address (TETHERING_IP_ADDRESS/24)
WIFI_MANAGER_SUBNET = "192.168.43.0/24"


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
    if "inet" in parts and "/" in parts[parts.index("inet") + 1]:
      addr, prefix = parts[parts.index("inet") + 1].split("/", 1)
      try:
        prefix = int(prefix)
      except ValueError:
        continue
      if prefix > 0 and not addr.startswith("127."):
        return _subnet_cidr(addr, prefix)
  return None


def _subnet_cidr(addr: str, prefix: int) -> str | None:
  if prefix < 8 or prefix > 32 or len(addr.split(".")) != 4:
    return None
  octets = [int(o) for o in addr.split(".")]
  if any(o > 255 for o in octets):
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
  for candidate in (NM_SHARED_SUBNET, WIFI_MANAGER_SUBNET):
    if candidate not in subnets:
      subnets.append(candidate)
  return tuple(subnets)


def _ensure_rule(check_args: tuple[str, ...], add_args: tuple[str, ...]) -> bool:
  """Add a rule if missing. Both the check and the add require root."""
  try:
    result = subprocess.run(["sudo", "-n", IPTABLES, *check_args],
                            capture_output=True, timeout=5)
    if result.returncode == 0:
      return True
    result = subprocess.run(["sudo", "-n", IPTABLES, *add_args],
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
  if shutil.which(IPTABLES) is None:
    cloudlog.debug(f"{IPTABLES} not available; skipping tethering NAT")
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
    for candidate in (NM_SHARED_SUBNET, WIFI_MANAGER_SUBNET):
      if candidate not in subnets:
        subnets.append(candidate)

    for subnet in subnets:
      ok &= _ensure_rule(
        ("-t", "nat", "-C", "POSTROUTING", "-s", subnet, "!", "-d", subnet, "-j", "MASQUERADE"),
        ("-t", "nat", "-A", "POSTROUTING", "-s", subnet, "!", "-d", subnet, "-j", "MASQUERADE"),
      )
      ok &= _ensure_rule(
        ("-C", "FORWARD", "-s", subnet, "-j", "ACCEPT"),
        ("-A", "FORWARD", "-s", subnet, "-j", "ACCEPT"),
      )
      ok &= _ensure_rule(
        ("-C", "FORWARD", "-d", subnet, "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"),
        ("-A", "FORWARD", "-d", subnet, "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"),
      )
  except (OSError, subprocess.SubprocessError) as exc:
    cloudlog.warning(f"Error applying tethering NAT: {exc}")
    return False

  return ok
