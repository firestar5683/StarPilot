"""Wired Android Auto: the comma as an Android Open Accessory (AOA) USB device.

The car's USB port is the host. ``AccessoryGadget`` binds a gadget of its own to
the comma's USB controller, with the accessory function as its only interface, so
the car finds it at interface 0 as on a phone; head units built on aasdk open only
that. ADB is not needed: configfs is mounted here when nothing has. If comma's ADB
gadget is bound it steps aside for the session and comes back afterwards,
following the ADB setting at that moment; ``recover`` does the same after a crash.

Two ways in, as head units differ:

* handshake: present as the comma. The car sends the AOA handshake
  (GET_PROTOCOL, the accessory strings, START), which the kernel's f_accessory
  answers and reports as an ``ACCESSORY=START`` uevent; the comma then
  re-enumerates as Google's accessory (18d1:2d00), as a phone does.
* direct: present as Google's accessory from the start, for head units that
  never send START to a device they do not recognise as a phone.

Either way the car then opens bulk endpoints carrying the same Android Auto
protocol as the Wi-Fi link. ``/dev/usb_accessory`` has no poll() and each
read() consumes one whole USB transfer, so ``AccessoryBridge`` copies between
it and a socket pair; the projection session uses the socket end unchanged.
Gadget changes need root and go through ``sudo -n``, like
``/usr/comma/set_adb.sh``.
"""

from __future__ import annotations

import errno
import fcntl
import os
import socket
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path
CONFIGFS_MOUNT = Path("/config")  # where /usr/comma/set_adb.sh mounts configfs when nothing has
CONFIGFS_FALLBACK_MOUNT = Path("/sys/kernel/config")  # the kernel's own mount point, always present with configfs
ADB_FUNCTION = "ffs.adb"
GADGET_NAME = "android_auto"
LEGACY_GADGET_NAMES = ("starpilot_aa",)  # a pre-rename session may still hold the one accessory function
CONFIG = "configs/c.1"
UDC_NAME = "a600000.dwc3"
ACCESSORY_FUNCTION = "accessory.gs2"
ACCESSORY_DEVICE = "/dev/usb_accessory"
COMMA_VID, COMMA_PID = 0x04D8, 0x1234  # the comma's own gadget identity, before the handshake
GOOGLE_VID = 0x18D1
ACCESSORY_PID = 0x2D00                 # accessory only: nothing else for the car to open instead
MAX_SPEED = "high-speed"               # head units are USB 2.0 hosts
READ_SIZE = 16384  # f_accessory's bulk buffer; a read must cover a whole transfer
MAX_EMPTY_READS = 64
NETLINK_KOBJECT_UEVENT = 15
UDC_SETTLE_SECONDS = 0.5  # allow the host to observe detach before descriptors/controller ownership change
OPEN_BUSY_WAIT = 5.0  # /dev/usb_accessory stays busy until the previous session's descriptor is released
# f_accessory's ACCESSORY_GET_STRING_* ioctls: _IOW('M', n, char[256]) for n = 1..6 in this order.
ACCESSORY_STRINGS = ("manufacturer", "model", "description", "version", "uri", "serial")
ACCESSORY_STRING_SIZE = 256


def _ioc_write(kind: str, number: int, size: int) -> int:
  return (1 << 30) | (size << 16) | (ord(kind) << 8) | number


ACCESSORY_GET_STRING = {name: _ioc_write("M", index + 1, ACCESSORY_STRING_SIZE) for index, name in enumerate(ACCESSORY_STRINGS)}


def read_accessory_strings(fd: int, ioctl: Callable = fcntl.ioctl) -> dict[str, str]:
  """What the car sent in the AOA handshake: its maker and model, for diagnostics. Empty when it sent none."""
  strings = {}
  for name, request in ACCESSORY_GET_STRING.items():
    buffer = bytearray(ACCESSORY_STRING_SIZE)
    try:
      ioctl(fd, request, buffer, True)
    except OSError:
      continue
    value = bytes(buffer).split(b"\0", 1)[0].decode("utf-8", "replace").strip()
    if value:
      strings[name] = "redacted" if name == "serial" else value  # a per-car identifier; logs are shared
  return strings


def configfs_mount(mounts: str = "/proc/mounts") -> Path | None:
  try:
    for line in Path(mounts).read_text().splitlines():
      parts = line.split()
      if len(parts) >= 3 and parts[2] == "configfs":
        return Path(parts[1])
  except OSError:
    pass
  return None


def adb_enabled() -> bool | None:
  """The user's ADB setting, or None when it cannot be read (then the gadget we released is rebound)."""
  try:
    from openpilot.common.params import Params
    return Params().get_bool("AdbEnabled")
  except Exception:
    return None


def parse_uevent(data: bytes) -> dict[str, str]:
  """Parse one kernel uevent datagram (``action@path`` then ``KEY=value`` lines)."""
  parts = data.split(b"\0")
  event: dict[str, str] = {}
  if parts and b"@" in parts[0] and b"=" not in parts[0]:
    action, path = parts[0].decode("utf-8", "replace").split("@", 1)
    event.update(ACTION=action, DEVPATH=path)
    parts = parts[1:]
  for part in parts:
    if b"=" in part:
      key, value = part.decode("utf-8", "replace").split("=", 1)
      event[key] = value
  return event


class UeventListener:
  """Kernel uevents for the USB gadget: connection state and the accessory start request."""

  def __init__(self):
    self.sock = socket.socket(socket.AF_NETLINK, socket.SOCK_DGRAM, NETLINK_KOBJECT_UEVENT)
    self.sock.bind((0, 1))

  def next(self, timeout: float) -> dict[str, str] | None:
    deadline = time.monotonic() + timeout
    while (remaining := deadline - time.monotonic()) > 0:
      self.sock.settimeout(remaining)
      try:
        data = self.sock.recv(8192)
      except TimeoutError:
        return None
      event = parse_uevent(data)
      # Connection state comes from android0; ACCESSORY=START from the usb_accessory misc device.
      if any(name in event.get("DEVPATH", "") for name in ("android_usb", "usb_accessory")):
        return event
    return None

  def close(self) -> None:
    self.sock.close()


class AccessoryGadget:
  """A gadget of our own on the comma's USB controller: the accessory function alone, at interface 0."""

  def __init__(self, log: Callable[..., None], configfs: Path | None = None, udc: str = UDC_NAME,
               run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
               adb_wanted: Callable[[], bool | None] = adb_enabled):
    self.log = log
    self.configfs = configfs
    self.udc = udc
    self.run = run
    self.adb_wanted = adb_wanted
    self.root: Path | None = None
    self.released: Path | None = None  # the gadget that had the controller, rebound by restore()

  def _sudo(self, *args: str, data: str | None = None) -> None:
    result = self.run(["sudo", "-n", *args], input=data, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
      raise RuntimeError(f"{' '.join(args)}: {(result.stderr or '').strip() or result.returncode}")

  def _write(self, path: Path, value: str) -> None:
    self._sudo("tee", str(path), data=value + "\n")

  @staticmethod
  def _read(path: Path) -> str:
    try:
      return path.read_text().strip()
    except OSError:
      return ""

  def _base(self) -> Path:
    """configfs's gadget directory, mounting configfs first when ADB has never been on to do it."""
    if self.configfs is None:
      self.configfs = configfs_mount()
    if self.configfs is None:
      self.configfs = self._mount_configfs()
    base = self.configfs / "usb_gadget"
    if not base.is_dir():
      raise RuntimeError("This comma's kernel has no USB gadget support, so it cannot use a USB connection")
    return base

  def _mount_configfs(self) -> Path:
    errors = []
    for mount in (CONFIGFS_MOUNT, CONFIGFS_FALLBACK_MOUNT):  # /config may not exist on a read-only root
      try:
        if not mount.is_dir():
          self._sudo("mkdir", "-p", str(mount))
        self._sudo("mount", "-t", "configfs", "none", str(mount))
      except RuntimeError as error:
        errors.append(f"{mount}: {error}")
        continue
      self.log("usb_configfs_mounted", path=str(mount))
      return mount
    raise RuntimeError(f"Could not set up USB (configfs mount failed: {'; '.join(errors)})")

  def _existing_base(self) -> Path | None:
    """The gadget directory if configfs is already mounted; never mounts."""
    configfs = self.configfs or configfs_mount()
    return configfs / "usb_gadget" if configfs is not None else None

  def _is_adb(self, gadget: Path) -> bool:
    return any(link.is_symlink() and link.resolve().name == ADB_FUNCTION for link in gadget.glob("configs/*/*"))

  def _controller_owner(self, base: Path) -> Path | None:
    return next((gadget for gadget in sorted(base.glob("*")) if self._read(gadget / "UDC") == self.udc), None)

  def _release_controller(self, base: Path) -> None:
    """Unbind whichever other gadget holds the controller (comma's ADB gadget), to rebind it later."""
    self.released = None
    for gadget in sorted(base.glob("*")):
      if gadget != self.root and self._read(gadget / "UDC") == self.udc:
        self._write(gadget / "UDC", "")
        self.released = gadget
        time.sleep(UDC_SETTLE_SECONDS)

  def _our_gadget(self, base: Path) -> Path:
    """Our gadget directory, reusing a pre-rename one still in configfs (f_accessory allows only one instance)."""
    return next((base / name for name in (GADGET_NAME, *LEGACY_GADGET_NAMES) if (base / name).is_dir()), base / GADGET_NAME)

  def _remove_stale_accessories(self, base: Path) -> None:
    """f_accessory allows one instance; earlier versions left an unlinked one in comma's ADB gadget."""
    for function in sorted(base.glob("*/functions/accessory.*")):
      gadget = function.parent.parent
      if gadget == self.root or any(link.is_symlink() and link.resolve() == function.resolve() for link in gadget.glob("configs/*/*")):
        continue
      self._sudo("rmdir", str(function))
      self.log("usb_stale_accessory_removed", gadget=gadget.name)

  def _bind(self, vid: int, pid: int) -> None:
    assert self.root is not None
    if self._read(self.root / "UDC"):
      self._write(self.root / "UDC", "")
      time.sleep(UDC_SETTLE_SECONDS)
    self._write(self.root / "idVendor", f"0x{vid:04x}")
    self._write(self.root / "idProduct", f"0x{pid:04x}")
    self._write(self.root / "UDC", self.udc)

  def prepare(self, direct: bool = False) -> None:
    """Take the controller with the accessory gadget; ``direct`` presents as Google's accessory at once."""
    base = self._base()
    self.root = self._our_gadget(base)
    config = self.root / CONFIG
    # A daemon crash can leave our gadget bound; configfs descriptors/functions
    # must only be edited while detached. The normal retry is already unbound.
    if self._read(self.root / "UDC"):
      self._write(self.root / "UDC", "")
      time.sleep(UDC_SETTLE_SECONDS)
    self._remove_stale_accessories(base)
    for path in (self.root / "strings/0x409", config / "strings/0x409"):
      if not path.is_dir():
        self._sudo("mkdir", "-p", str(path))
    function = self.root / "functions" / ACCESSORY_FUNCTION
    if not function.is_dir():
      try:
        self._sudo("mkdir", "-p", str(function))
      except RuntimeError as error:
        raise RuntimeError(f"This comma's kernel does not support USB accessory mode ({error})") from error
    for name, value in (("strings/0x409/manufacturer", "comma.ai"), ("strings/0x409/product", "StarPilot"),
                        ("strings/0x409/serialnumber", "StarPilot"), (f"{CONFIG}/strings/0x409/configuration", "Android Auto"),
                        (f"{CONFIG}/MaxPower", "250")):
      self._write(self.root / name, value)
    try:
      self._write(self.root / "max_speed", MAX_SPEED)
    except RuntimeError as error:
      self.log("usb_max_speed_unset", error=str(error))
    for link in config.iterdir():
      if link.is_symlink() and link.name != ACCESSORY_FUNCTION:
        self._sudo("rm", "-f", str(link))  # only the accessory: the car must find it at interface 0
    if not (config / ACCESSORY_FUNCTION).is_symlink():
      self._sudo("ln", "-s", str(self.root / "functions" / ACCESSORY_FUNCTION), str(config / ACCESSORY_FUNCTION))
    self._release_controller(base)
    self._bind(GOOGLE_VID if direct else COMMA_VID, ACCESSORY_PID if direct else COMMA_PID)
    self.log("usb_gadget_prepared", mode="direct" if direct else "handshake",
             released=self.released.name if self.released else "")
    if direct:
      self._await_device()

  def switch_to_accessory(self) -> None:
    """Re-enumerate as Google's accessory, as a phone does after the AOA START request."""
    self._bind(GOOGLE_VID, ACCESSORY_PID)
    self._await_device()
    self.log("usb_accessory_mode", vid=f"{GOOGLE_VID:04x}", pid=f"{ACCESSORY_PID:04x}")

  def _await_device(self) -> None:
    for _ in range(50):
      if os.path.exists(ACCESSORY_DEVICE):
        break
      time.sleep(0.1)
    self._sudo("chown", f"{os.getuid()}:{os.getgid()}", ACCESSORY_DEVICE)

  def connection_state(self) -> str:
    """Read the current controller state as a fallback for missing/coalesced uevents."""
    state = self._read(Path("/sys/class/udc") / self.udc / "state")
    if state == "configured":
      return "CONFIGURED"
    if state in ("attached", "powered", "default", "addressed", "suspended"):
      return "CONNECTED"
    return "DISCONNECTED" if state == "not attached" else ""

  def detach(self) -> None:
    """Cancel pending accessory I/O before closing the bridge or restoring ADB."""
    if self.root is not None and self._read(self.root / "UDC"):
      self._write(self.root / "UDC", "")
      time.sleep(UDC_SETTLE_SECONDS)

  def _give_back(self, base: Path) -> Path | None:
    """The gadget to rebind: the one we released, unless the ADB setting changed meanwhile.

    ADB turned on mid-session could not bind (we held the controller), so its gadget is bound
    now; ADB turned off mid-session stays off. None when the setting cannot be read.
    """
    target = self.released
    wanted = self.adb_wanted()
    if wanted is False and target is not None and self._is_adb(target):
      target = None
    elif wanted and target is None:
      target = next((gadget for gadget in sorted(base.glob("*")) if gadget != self._our_gadget(base) and self._is_adb(gadget)), None)
    if target is None or self._controller_owner(base) is not None:
      return None
    self._write(target / "UDC", self.udc)
    return target

  def restore(self) -> None:
    """Let go of the controller and give it back as the ADB setting wants; the car sees the cable drop."""
    if self.root is None:
      return
    try:
      self.detach()
      rebound = self._give_back(self.root.parent)
      self.log("usb_gadget_restored", rebound=rebound.name if rebound else "")
      self.root = self.released = None
    except Exception as error:
      self.log("usb_gadget_restore_failed", error=str(error))

  def recover(self) -> bool:
    """After a crash mid-session: drop our leftover gadget and hand the controller back. Never mounts configfs.

    Without it, the car keeps seeing a dead accessory and ADB stays off until a reboot.
    True when a leftover gadget was found.
    """
    base = self._existing_base()
    if base is None or not self._read(self._our_gadget(base) / "UDC"):
      return False
    self.root = self._our_gadget(base)
    self.log("usb_gadget_recovering")
    self.restore()
    return True


class AccessoryBridge:
  """Expose /dev/usb_accessory as a connected socket for the projection session."""

  def __init__(self, device: str = ACCESSORY_DEVICE, log: Callable[..., None] = lambda *a, **k: None):
    self.log = log
    self.fd = self._open(device)
    self.strings = read_accessory_strings(self.fd)
    self.session_sock, self.bridge_sock = socket.socketpair()
    self.closed = threading.Event()
    self._close_lock = threading.Lock()
    self._cleanup_thread: threading.Thread | None = None
    self.error = ""
    self.threads = [threading.Thread(target=self._usb_to_socket, name="android_auto_usb_rx", daemon=True),
                    threading.Thread(target=self._socket_to_usb, name="android_auto_usb_tx", daemon=True)]
    for thread in self.threads:
      thread.start()

  @staticmethod
  def _open(device: str) -> int:
    deadline = time.monotonic() + OPEN_BUSY_WAIT
    while True:
      try:
        return os.open(device, os.O_RDWR)
      except OSError as error:
        if error.errno != errno.EBUSY or time.monotonic() >= deadline:
          raise
        time.sleep(0.25)

  @property
  def socket(self) -> socket.socket:
    return self.session_sock

  def _finish(self, error: str) -> None:
    if not self.closed.is_set():
      self.error = error
      self.closed.set()
      self.log("usb_bridge_closed", error=error)
      try:
        self.bridge_sock.shutdown(socket.SHUT_RDWR)
      except OSError:
        pass

  def _usb_to_socket(self) -> None:
    empty = 0
    try:
      while not self.closed.is_set():
        data = os.read(self.fd, READ_SIZE)
        if not data:
          empty += 1  # a zero-length packet is normal; an endless run of them is a dead link
          if empty > MAX_EMPTY_READS:
            self._finish("car disconnected")
            return
          continue
        empty = 0
        self.bridge_sock.sendall(data)
    except OSError as error:
      self._finish("car disconnected" if error.errno in (errno.ENODEV, errno.EIO, errno.ESHUTDOWN) else str(error))

  def _socket_to_usb(self) -> None:
    try:
      while not self.closed.is_set():
        data = self.bridge_sock.recv(READ_SIZE)
        if not data:
          break
        view = memoryview(data)
        while view and not self.closed.is_set():
          written = os.write(self.fd, view)
          if written <= 0:
            raise OSError(errno.EIO, "USB write made no progress")
          view = view[written:]
    except OSError as error:
      self._finish(str(error))
    self._finish(self.error or "session closed")

  def close(self) -> None:
    """Call after detaching the gadget: Linux close alone cannot wake accessory I/O."""
    with self._close_lock:
      self._close()

  def _close(self) -> None:
    if self.fd < 0 or self._cleanup_thread is not None:
      return
    self._finish(self.error or "closed")
    for sock in (self.session_sock, self.bridge_sock):
      try:
        sock.close()
      except OSError:
        pass
    for thread in self.threads:
      thread.join(timeout=2.0)
    if any(thread.is_alive() for thread in self.threads):
      # Keep ownership of the fd; reusing its number while a worker still runs is unsafe.
      self._cleanup_thread = threading.Thread(target=self._finish_close, name="android_auto_usb_cleanup", daemon=True)
      self._cleanup_thread.start()
      raise RuntimeError("USB I/O did not stop after detach")
    os.close(self.fd)
    self.fd = -1

  def _finish_close(self) -> None:
    for thread in self.threads:
      thread.join()
    with self._close_lock:
      os.close(self.fd)
      self.fd = -1
