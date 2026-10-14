"""One renderer-owned RGBA slot; device viewers only read it."""
from dataclasses import dataclass
import fcntl
import math
import mmap
import os
from pathlib import Path
import re
import stat
import struct
import time

MAGIC = 0x5350525046524D31
VERSION = 1
HEADER_SIZE = 4096
MAX_WIDTH, MAX_HEIGHT = 1600, 800
HEADER = struct.Struct('=QQIIIIQQQd64s')
SEQ = struct.Struct('=Q')
SESSION = re.compile(r'[a-f0-9]{32}\Z')
PROFILES = {'large': 1, 'compact': 2}


@dataclass(frozen=True)
class ReplayFrame:
  data: bytes
  width: int
  height: int
  session_id: str
  epoch: int
  position: float
  frame_id: int
  captured_ns: int


class ReplayFramePublisher:
  def __init__(self, path: Path, session_id: str, profile: str, width: int, height: int):
    if SESSION.fullmatch(session_id) is None or profile not in PROFILES or not 0 < width <= MAX_WIDTH or not 0 < height <= MAX_HEIGHT:
      raise ValueError('Invalid replay frame geometry or identity')
    self.path, self.session_id, self.profile = Path(path), session_id, profile
    self.width, self.height = width, height
    self.size = HEADER_SIZE + width * height * 4
    self.frame_id = 0
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
      os.ftruncate(fd, self.size)
      self.mm = mmap.mmap(fd, self.size)
    except BaseException:
      os.close(fd)
      raise
    self.fd = fd

  def publish(self, pixels, *, epoch: int, position: float, captured_ns: int):
    if type(epoch) is not int or epoch <= 0 or not math.isfinite(position) or position < 0 or captured_ns <= 0:
      raise ValueError('Invalid replay frame clock')
    if len(pixels) != self.width * self.height * 4:
      raise ValueError('Invalid RGBA replay frame')
    # Kernel locks also establish ordering on ARM; a Python mmap seqlock alone
    # cannot provide acquire/release barriers while a reader copies the pixels.
    deadline = time.monotonic() + .1
    while True:
      try:
        fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        break
      except BlockingIOError:
        if time.monotonic() >= deadline:
          raise RuntimeError('Replay frame consumer stalled') from None
        time.sleep(.001)
    try:
      self._publish(pixels, epoch=epoch, position=position, captured_ns=captured_ns)
    finally:
      fcntl.flock(self.fd, fcntl.LOCK_UN)

  def _publish(self, pixels, *, epoch, position, captured_ns):
    seq = SEQ.unpack_from(self.mm, 8)[0]
    SEQ.pack_into(self.mm, 8, seq | 1)
    self.mm[HEADER_SIZE:] = pixels
    self.frame_id += 1
    HEADER.pack_into(self.mm, 0, MAGIC, seq | 1, VERSION, self.width, self.height, PROFILES[self.profile],
                     epoch, self.frame_id, captured_ns, position, self.session_id.encode())
    SEQ.pack_into(self.mm, 8, (seq | 1) + 1)

  def close(self):
    self.mm.close()
    os.close(self.fd)
    self.path.unlink(missing_ok=True)


class ReplayFrameReader:
  def __init__(self, path: Path, session_id: str, profile: str | None = None):
    if SESSION.fullmatch(session_id) is None or profile is not None and profile not in PROFILES:
      raise ValueError('Invalid replay frame identity')
    self.session_id, self.profile, self.last_key = session_id, profile, None
    self.mm = None
    self.fd = None
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
      info = os.fstat(fd)
      if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600 or
          info.st_nlink != 1 or not HEADER_SIZE < info.st_size <= HEADER_SIZE + MAX_WIDTH * MAX_HEIGHT * 4):
        raise ValueError('Unsafe replay frame file')
      self.mm = mmap.mmap(fd, info.st_size, access=mmap.ACCESS_READ)
    except BaseException:
      os.close(fd)
      raise
    self.fd = fd

  def latest(self) -> ReplayFrame | None:
    mm, fd = self.mm, self.fd
    if mm is None or fd is None:
      return None
    try:
      fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
    except BlockingIOError:
      return None
    try:
      return self._latest(mm)
    finally:
      fcntl.flock(fd, fcntl.LOCK_UN)

  def _latest(self, mm: mmap.mmap):
    for _ in range(3):
      seq = SEQ.unpack_from(mm, 8)[0]
      if not seq or seq & 1:
        continue
      magic, stamp, version, width, height, profile, epoch, frame_id, captured_ns, position, session = HEADER.unpack_from(mm)
      if (magic != MAGIC or stamp != seq or version != VERSION or profile not in PROFILES.values() or
          self.profile is not None and profile != PROFILES[self.profile] or
          not 0 < width <= MAX_WIDTH or not 0 < height <= MAX_HEIGHT or
          len(mm) != HEADER_SIZE + width * height * 4 or session.rstrip(b'\0') != self.session_id.encode() or
          epoch <= 0 or frame_id <= 0 or captured_ns <= 0 or not math.isfinite(position) or position < 0):
        return None
      key = epoch, frame_id
      if key == self.last_key:
        return None
      data = mm[HEADER_SIZE:]
      if SEQ.unpack_from(mm, 8)[0] != seq:
        continue
      self.last_key = key
      return ReplayFrame(data, width, height, self.session_id, epoch, position, frame_id, captured_ns)
    return None

  def close(self):
    if self.mm is not None:
      self.mm.close()
      self.mm = None
    if self.fd is not None:
      os.close(self.fd)
      self.fd = None
