"""Read the owned replay publisher's clock without modifying recorded messages."""

from dataclasses import dataclass
import math
import mmap
import os
from pathlib import Path
import re
import stat
import struct
import sys
import time


MAGIC = 0x53505250434C4B31
VALID, PAUSED, SEEKING, BOOT_KNOWN = 1, 2, 4, 8
RECORD = struct.Struct("=QQIIQQQdqQQ")
HEARTBEAT_MAX_AGE_NS = 250_000_000
_PREFIX = re.compile(r"replay-[A-Za-z0-9_-]{1,48}\Z")


@dataclass(frozen=True)
class ClockSample:
  now_ns: int | None
  boot_ns: int | None
  host_ns: int
  epoch: int | None = None
  paused: bool = False
  valid: bool = False


class DisplayClockReader:
  @staticmethod
  def enabled(env=None) -> bool:
    env = os.environ if env is None else env
    prefix = env.get("OPENPILOT_PREFIX", "")
    root = Path("/tmp" if sys.platform == "darwin" else "/dev/shm")
    path = root / ("msgq_" + prefix) / "display-clock"
    return (env.get("SP_HOST_RUNTIME") == "1" and bool(_PREFIX.fullmatch(prefix)) and
            env.get("SP_REPLAY_CLOCK_PATH") == str(path))

  def __init__(self, env=None):
    env = os.environ if env is None else env
    self._mapping = None
    prefix = env.get("OPENPILOT_PREFIX", "")
    root = Path("/tmp" if sys.platform == "darwin" else "/dev/shm")
    parent = root / ("msgq_" + prefix)
    if not self.enabled(env):
      return
    directory = file = None
    try:
      directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
      metadata = os.fstat(directory)
      if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        return
      file = os.open("display-clock", os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
      metadata = os.fstat(file)
      if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or
          stat.S_IMODE(metadata.st_mode) != 0o600 or metadata.st_nlink != 1 or metadata.st_size != RECORD.size):
        return
      self._mapping = mmap.mmap(file, RECORD.size, access=mmap.ACCESS_READ)
    except (OSError, ValueError):
      return
    finally:
      if file is not None:
        os.close(file)
      if directory is not None:
        os.close(directory)

  def close(self):
    if self._mapping is not None:
      self._mapping.close()
      self._mapping = None

  def sample(self, host_ns: int | None = None) -> ClockSample:
    host_ns = time.monotonic_ns() if host_ns is None else host_ns
    missing = ClockSample(None, None, host_ns)
    if self._mapping is None or type(host_ns) is not int or host_ns <= 0:
      return missing
    for _ in range(4):
      before = struct.unpack_from("=Q", self._mapping)[0]
      if not before or before % 2:
        continue
      values = RECORD.unpack(self._mapping[:RECORD.size])
      after = struct.unpack_from("=Q", self._mapping)[0]
      if before == values[0] == after and not after % 2:
        break
    else:
      return missing
    _, magic, version, flags, epoch, route_anchor, host_anchor, speed, boot_offset, heartbeat, reserved = values
    if (magic != MAGIC or version != 1 or flags & ~15 or reserved or not epoch or
        not 0 < host_anchor <= heartbeat <= host_ns or host_ns - heartbeat > HEARTBEAT_MAX_AGE_NS or
        not math.isfinite(speed) or speed <= 0 or flags & BOOT_KNOWN and boot_offset < 0):
      return missing
    paused = bool(flags & PAUSED)
    if not flags & VALID or flags & SEEKING or not route_anchor:
      return ClockSample(None, None, host_ns, epoch, paused)
    now_ns = route_anchor if paused else route_anchor + int((host_ns - host_anchor) * speed)
    boot_ns = now_ns + boot_offset if flags & BOOT_KNOWN else None
    if not 0 < now_ns < 2**64 or boot_ns is not None and not 0 < boot_ns < 2**64:
      return missing
    return ClockSample(now_ns, boot_ns, host_ns, epoch, paused, True)
