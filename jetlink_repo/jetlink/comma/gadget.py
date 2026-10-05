"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

The comma's USB gadget, and how to look at it, using nothing but the
standard library and jetlink's own transport.

Kept apart from openpilot so the process that owns the gadget can be small.
Holding ep0 needs sysfs and a unix socket; `openpilot.common.swaglog` costs
28 MB because it drags numpy, capnp and zmq in to publish a log line, and
`openpilot.common.params` imports swaglog, so a module that touches either
prices the owner out of being minimal. Measured on the comma: python plus this
plus the FunctionFS transport is 10.4 MB against 47.5 MB for the daemon that
imported the world.

Nothing in jetlink.comma may import openpilot or knows a param: the settings
come from jetlink.openpilot.settings, over the directory and the keys the
fork's adapter names. tests/test_comma_gadget.py holds the line.

jetlink.openpilot's heavy processes import it too, and bind() points `log` at
the fork's cloudlog (set_logger), so their lines still reach the drive's log
while the owner's go to a file.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from jetlink.comma import root
from jetlink.transport import ffs
from jetlink.transport.base import UDC_SYSFS, udc_speed
from jetlink.transport.tcp import CABLE_ADDRESS, DEFAULT_PORT

# -- logging --------------------------------------------------------------
# a module-level indirection rather than an import: the owner has no swaglog
# and must not grow one, and every other process wants its lines in the drive.
log = logging.getLogger('jetlink.comma.gadget')


def set_logger(logger) -> None:
  """Send this module's lines somewhere else, and the root script's failures
  with them: jetlink.openpilot.bind points it at the fork's cloudlog."""
  global log
  log = logger
  root.log = logger


# -- what carries the link ------------------------------------------------
# The Jetlink setting names the host: USB (a Jetson or a Mac on the
# FunctionFS vendor interface) or iOS (an iPhone, which gives apps no USB
# access). For iOS the gadget is composite, with a CDC-NCM network interface
# whose comma end is 192.168.60.1 (jetlink-root.sh gadget --ios, and net, which
# also runs the DHCP server), and the phone dials CABLE_ADDR whenever it holds
# a lease on that network.
# Whoever holds the loan listens for the dial, the owner while nobody does;
# nothing writes to the endpoint files, which a phone never reads. The setting,
# not a guess, says which: a hello over FunctionFS to a phone blocks 15 s and
# bounces the gadget, and waiting to see whether a phone dials cost every
# Jetson reconnect 5 to 10 s.
LINK = Path("/dev/shm/jetlink-link")        # "cable <peer ip>" while a phone is dialed in
NET_STATUS = Path("/dev/shm/jetlink-net")   # jetlink-root.sh: "ok 192.168.60.1 <netdev>", "error: ...", "net: off" (USB)
CABLE_ADDR = (CABLE_ADDRESS, DEFAULT_PORT)


def read(path: Path) -> str:
  """A record's or a sysfs file's text, stripped; '' when it is missing or
  unreadable."""
  try:
    return path.read_text().strip()
  except OSError:
    return ''


def _write(path: Path, text: str | None, what: str) -> bool:
  """Write a record, or remove it with None. False, and logged, when that fails."""
  try:
    if text is None:
      path.unlink(missing_ok=True)
    else:
      path.write_text(text)
    return True
  except OSError:
    log.exception("jetlink: could not %s", what)
    return False


def link_state() -> tuple[str | None, str | None]:
  """The link record in one read: the gadget the owner built, 'cable' for
  iOS (the phone's network interface on the gadget) or 'usb', and on the
  cable the phone's address while a link is up. (None, None) before the
  owner has said."""
  record = read(LINK).split()
  if record[:1] not in (['cable'], ['usb']):
    return None, None
  return record[0], (record[1] if record[0] == 'cable' and len(record) > 1 else None)


def link_kind(mode: str | None = None) -> str:
  """link_state's kind, or a stand-in: `mode`, the Jetlink setting as
  the caller read it, stands in only until the owner has said: it may have
  moved and be waiting for the car to park. Without either, 'usb'."""
  kind, _ = link_state()
  return kind or ('cable' if mode == 'ios' else 'usb')


def link_peer() -> str | None:
  """The phone's address, while a cable link is up."""
  return link_state()[1]


def note_link(kind: str, peer: str | None = None) -> None:
  """The owner's record of the gadget it built, 'usb' or 'cable', and on the
  cable the phone that dialed in; see link_kind and link_peer."""
  _write(LINK, f"{kind} {peer}".strip() if peer else kind, "record the link")


def clear_link() -> None:
  _write(LINK, None, "clear the link record")


def net_status() -> str | None:
  """What jetlink-root.sh said about the gadget's network interface, if it ran."""
  return read(NET_STATUS) or None


def usb_speed() -> str | None:
  """The bus speed the host enumerated us at: 458 KB a frame is ~1 ms on
  super-speed and ~11 ms on high-speed, so this is the first thing to read
  when the link is slow. None while unbound or where the UDC does not say."""
  udc = bound_udc()
  return None if udc is None else udc_speed(udc, str(UDC_PATH))


# -- where the gadget lives -----------------------------------------------
# the comma is the USB gadget and the Jetson the host, decided by the kernels:
# AGNOS has CONFIG_USB_F_FS built in, L4T images are often stripped of the
# gadget modules. See docs/transport.md
GADGET_PATH = Path(ffs.GADGET)
FFS_MOUNT = Path(ffs.MOUNT)
UDC_PATH = Path(UDC_SYSFS)
# the network function jetlink-root.sh gadget --ios adds after ffs.jetlink. Its
# netdev is not usb0, which the modem holds, but whatever the kernel names it
NET_FUNCTION = 'ncm.usb0'
# written by scripts/comma/jetlink-root.sh gadget, which the owner runs when the
# link is on and there is no gadget: "ok", or "error: <reason>"
GADGET_STATUS = Path("/dev/shm/jetlink-gadget")
# the owner's own: "error: the lender could not listen: <reason>" while nothing
# can borrow the gadget from it, absent otherwise. Not GADGET_STATUS, which
# root owns and every build rewrites
LENDER_STATUS = Path("/dev/shm/jetlink-lender")
CC_ORIENTATION = Path('/sys/class/power_supply/usb/typec_cc_orientation')
# the owner's pid while it has released the gadget on purpose so the Jetson can
# sleep. Presence comes from this, not the UDC; a marker whose writer is dead is
# a leftover from a kill
DORMANT = Path("/dev/shm/jetlink-dormant")
# hardwared's request to power the Jetson off; see backend.shutdown
SHUTDOWN_REQUEST = Path("/dev/shm/jetlink-shutdown")
# the owner's status record: everything the readers used to take from the
# files above one by one, rewritten whole every step, which makes it the
# owner's heartbeat too. A clean stop removes it
STATUS = Path("/dev/shm/jetlink/status.json")
# how old that record may be before a reader takes its owner for gone: six of
# its 0.5 s steps. A wait inside a step renews it (Owner.beat)
HEARTBEAT_TIMEOUT = 3.0
# the owner's start times, for its crash-loop backoff (see the owner)
STARTS = Path("/dev/shm/jetlink/starts.json")
# held with flock by the owner for its whole life, so there is only ever one
OWNER_LOCK = Path("/dev/shm/jetlink/owner.lock")
# what the server's last hello said (lending.SERVER_FIELDS), kept apart from
# the status record so a clean stop leaves it for the next owner
SERVER = Path("/dev/shm/jetlink/server.json")
# how long a host that stopped reading configured still counts as there. The
# owner holds the gadget for as long as the link is enabled, so presence no
# longer blinks at every handover; what is left to bridge is a USB3 link
# recovery passing through "addressed", and a bounce made on purpose when a
# host will not enumerate (wait_for_host)
PRESENCE_HOLD = 5.0


def write_record(path: Path, record) -> None:
  """Replace a JSON record whole: a reader gets the old one or the new one,
  never half of either. Raises OSError, for the writer to say once; the
  temporary goes with a failure (a SIGKILL between the two leaves it for
  the next owner to clear, clear_leftovers)."""
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_name(f".{path.name}.{os.getpid()}")
  try:
    tmp.write_text(json.dumps(record))
    os.replace(tmp, path)
  except BaseException:
    tmp.unlink(missing_ok=True)
    raise


def clear_leftovers(directory: Path) -> None:
  """The temporaries a writer killed between its write and its rename left
  in `directory`. For the owner's start, when nothing else writes there."""
  try:
    for leftover in directory.glob('.*.json.*'):
      leftover.unlink(missing_ok=True)
  except OSError:
    pass


def owner_status() -> dict | None:
  """The owner's status record, or None without one: no owner has run since
  boot, the last one stopped cleanly, or it is one too old to write it."""
  try:
    record = json.loads(read(STATUS))
  except ValueError:
    return None
  return record if isinstance(record, dict) else None


def owner_alive(record: dict) -> bool:
  """Was this record written within HEARTBEAT_TIMEOUT? time.monotonic is the
  system's CLOCK_MONOTONIC, the same in every process on the device, and
  unlike the wall clock it does not jump when the comma sets its time."""
  at = record.get('at')
  return isinstance(at, (int, float)) and time.monotonic() - at < HEARTBEAT_TIMEOUT


def _status_error(path: Path) -> str | None:
  """The reason in an "ok" or "error: <reason>" file. A missing file is not an
  error: whatever writes it has not run."""
  reason = read(path)
  if not reason or reason == 'ok':
    return None
  return reason.removeprefix('error:').strip() or None


def build_error() -> str | None:
  """Why the gadget could not be built, if it could not."""
  return _status_error(GADGET_STATUS)


def gadget_error() -> str | None:
  """Why the link is unavailable, if it is: the gadget could not be built, or
  it was and nothing can borrow it from the owner.

  Both happen in the owner, nowhere a user would look, so this is how the
  reason reaches the panels.
  """
  return build_error() or _status_error(LENDER_STATUS)


def note_lender_error(reason: str | None) -> None:
  """The owner's record of a lender that cannot listen, or None once it can."""
  _write(LENDER_STATUS, None if reason is None else f"error: the lender could not listen: {reason}\n",
         "record the lender's state")


def bound_udc() -> str | None:
  """The device controller our gadget is attached to, if it is attached."""
  return read(GADGET_PATH / "UDC") or None


def other_gadget() -> str | None:
  """Another gadget bound to a device controller, by name: on a comma, AGNOS's
  ADB gadget (g1) while ADB is on. jetlink-root.sh refuses to take the
  controller from it."""
  for udc in GADGET_PATH.parent.glob("*/UDC"):
    if udc.parent != GADGET_PATH and read(udc):
      return udc.parent.name
  return None


def udc_state() -> str | None:
  """What the device controller says about the bus, or None if we are unbound.

  "configured" is a host that has us; "default" and "addressed" are one that
  reset the bus and stopped part way, which is what a Jetson that took the
  bind as a wake and did not finish waking looks like.
  """
  udc = bound_udc()
  return None if udc is None else read(UDC_PATH / udc / "state") or None


def host_attached() -> bool:
  """Has a host (the Jetson) enumerated and configured us?"""
  return udc_state() == "configured"


def cc_orientation() -> int | None:
  """What the USB-C port controller reads on the CC pin, so electrically true
  whether or not anything enumerated: 0 is a port with nothing on it, 1 or 2 a
  cable with a live host behind it (it cannot say what kind). A legacy A-to-C
  cable's pull-up rides on the host's VBUS and reads the same. None where the
  kernel does not say."""
  try:
    return int(read(CC_ORIENTATION))
  except ValueError:
    return None


def port_has_host() -> bool:
  """Does the USB-C port controller see a host on the cable?"""
  return bool(cc_orientation())


# how long the UDC may sit half enumerated with a host on the cable before the
# gadget is bounced. A real enumeration is milliseconds; this only fires for a
# host that answered the bind with a bus reset and then stopped, which is what
# an unarmed hub does to a box asleep. See FfsTransport.rebind
STALLED_ENUMERATION = 20.0
STALLED_STATES = ('default', 'addressed')
HOST_POLL = 0.5


def wait_for_host(timeout: float, bounce=None, should_stop=None, report=None, mode: str | None = None) -> bool:
  """Wait for the Jetson to enumerate us, bouncing a bus that stalled.

  The gadget stays bound throughout. An unbind is an unplug as the far end sees
  it, and while one boots it takes ~50 s a cycle: doing that on a timer landed
  an unplug on a box that was seconds from enumerating.

  The one case that needs an edge is a host that took the bind as a wake, reset
  the bus and stopped. The UDC then sits in default or addressed with the CC
  pin still showing a host, and only another connect moves it: that is what
  `bounce` is for, and it is spent once.

  On the cable there is nothing to wait for: the connect that made the client
  already reached the phone. The UDC is configured too, but by the phone, and
  it is the dial that proved it is there. `mode` is the link setting, for
  before the owner has recorded which gadget it built (link_kind).
  """
  if link_kind(mode) == 'cable':
    return True
  deadline = time.monotonic() + timeout
  stalled_since = None
  bounced = False
  reported = False
  while True:
    state = udc_state()
    if state == "configured":
      return True
    now = time.monotonic()
    if now >= deadline or (should_stop is not None and should_stop()):
      return False
    if report is not None and not reported:
      reported = True
      report()
    if state in STALLED_STATES and port_has_host():
      stalled_since = now if stalled_since is None else stalled_since
      if not bounced and bounce is not None and now - stalled_since > STALLED_ENUMERATION:
        bounced = True
        log.warning("jetlink: the bus has been half enumerated for %.0f s, bouncing the gadget",
                    STALLED_ENUMERATION)
        try:
          bounce()
        except Exception:
          log.exception("jetlink: could not bounce the gadget")
    else:
      stalled_since = None
    time.sleep(HOST_POLL)


def setup_gadget(ios: bool) -> bool:
  """Create the gadget, for USB or iOS: there is none yet, or the setting
  moved between the two. The script records "ok" or the reason itself, in
  GADGET_STATUS, so a failure here reaches the offroad alert. Off AGNOS
  there is nothing to create it with, and this is a False."""
  if not root.run('gadget', *(['--ios'] if ios else [])):
    return False
  log.warning("jetlink: gadget set up for %s", 'iOS' if ios else 'USB')
  return link_configured()


def built_for_ios() -> bool:
  """Does the gadget carry the network function, as jetlink-root.sh gadget --ios builds it?"""
  return os.path.lexists(GADGET_PATH / 'configs' / 'c.1' / NET_FUNCTION)


def net_up() -> bool:
  """Bring the gadget's network interface up, for a phone to dial over.

  The netdev does not exist until the first UDC bind (f_ncm registers it in
  its bind), and the gadget subcommand never binds, so the owner runs this
  after it binds. `net` is idempotent: nmcli unmanaged, 192.168.60.1/24, the
  DHCP server, and NET_STATUS written as "ok 192.168.60.1 <netdev>" or
  "error: <reason>".
  """
  if not root.run('net'):
    return False
  status = net_status() or ''
  log.warning("jetlink: gadget network: %s", status or 'no status written')
  return status.startswith('ok')


def link_configured() -> bool:
  """Can we even attempt a link? The gadget exists.

  Not host_attached(): the UDC only binds when something opens ep0, and nothing
  opens ep0 unless the link looks usable. Waiting for a host deadlocks.

  The cable too: a phone is on the gadget's own network interface, which
  exists only while ep0 is held.
  """
  if build_error() is not None:
    return False
  try:
    return (FFS_MOUNT / "ep0").exists()
  except OSError:
    # a root-only mount raises PermissionError from stat; unusable either way
    return False


def set_dormant(on: bool) -> None:
  _write(DORMANT, str(os.getpid()) if on else None, "update the dormant marker")


def dormant() -> bool:
  """Has a live owner released the gadget on purpose?"""
  try:
    pid = int(read(DORMANT))
  except ValueError:
    return False
  try:
    os.kill(pid, 0)
  except ProcessLookupError:
    return False
  except PermissionError:
    pass  # alive, just not ours to signal
  return True


def request_shutdown(reason: str) -> bool:
  return _write(SHUTDOWN_REQUEST, json.dumps({'reason': reason}), "write the shutdown request")


def pending_shutdown() -> str | None:
  """The reason in a shutdown request that has not been dealt with, if any.

  Read twice a second for the life of the process and almost never there, so
  the miss is a stat rather than an open that raises.
  """
  if not SHUTDOWN_REQUEST.exists():
    return None
  try:
    return str(json.loads(read(SHUTDOWN_REQUEST)).get('reason', ''))
  except ValueError:
    return None


def await_shutdown(timeout: float, poll: float = 0.25) -> bool:
  """Wait for the owner's run to take a shutdown request. False if nobody did
  within `timeout`, and then the request is withdrawn."""
  deadline = time.monotonic() + timeout
  while time.monotonic() < deadline:
    if not SHUTDOWN_REQUEST.exists():
      return True
    time.sleep(poll)
  finish_shutdown()
  return False


def finish_shutdown() -> None:
  _write(SHUTDOWN_REQUEST, None, "remove the shutdown request")
