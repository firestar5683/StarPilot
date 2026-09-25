"""One bounded, local Quick road recording remux for authenticated Galaxy playback."""

from __future__ import annotations

import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import tempfile
import threading

from openpilot.common.hardware.hw import Paths
from openpilot.starpilot.galaxy.drive_history import DIR_FLAGS, MAX_SEGMENT_ENTRIES, SEGMENT_NAME


SOURCE_NAME = 'qcamera.ts'
MAX_SOURCE_BYTES = 128 * 1024 * 1024
MAX_MP4_BYTES = 256 * 1024 * 1024
REMUX_TIMEOUT_S = 30
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_RANGE = re.compile(r'bytes=(\d*)-(\d*)\Z')


class RecordingMediaUnavailable(Exception):
  pass


class RecordingMediaChanged(RecordingMediaUnavailable):
  pass


class RecordingMediaBusy(RecordingMediaUnavailable):
  pass


class RecordingMediaMissing(RecordingMediaUnavailable):
  pass


class RecordingMediaNotPrepared(RecordingMediaUnavailable):
  pass


class RecordingMediaUnsupported(RecordingMediaUnavailable):
  pass


def _identity(fd: int) -> tuple[int, int, int, int, int]:
  info = os.fstat(fd)
  return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _same(fd: int, name: str | Path, parent: int | None = None) -> bool:
  try:
    opened = os.fstat(fd)
    current = os.stat(name, dir_fd=parent, follow_symlinks=False)
  except OSError:
    return False
  return (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) == \
         (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns, current.st_ctime_ns)


class VerifiedRecording:
  def __init__(self, root: Path, name: str):
    if SEGMENT_NAME.fullmatch(name) is None:
      raise ValueError('Invalid segment identity')
    self.root, self.name = root, name
    self.root_fd = self.segment_fd = self.source_fd = -1
    try:
      self.root_fd = os.open(root, DIR_FLAGS)
      self.segment_fd = os.open(name, DIR_FLAGS, dir_fd=self.root_fd)
      self.source_fd = os.open(SOURCE_NAME, FILE_FLAGS, dir_fd=self.segment_fd)
      info = os.fstat(self.source_fd)
      self.identity = _identity(self.source_fd)
      if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_SOURCE_BYTES or not self.current():
        raise RecordingMediaChanged
    except FileNotFoundError as error:
      self.close()
      raise RecordingMediaMissing from error
    except (OSError, RecordingMediaChanged):
      self.close()
      raise RecordingMediaChanged from None

  def current(self) -> bool:
    if self.root_fd < 0 or self.segment_fd < 0 or self.source_fd < 0:
      return False
    if not (_same(self.root_fd, self.root) and _same(self.segment_fd, self.name, self.root_fd) and
            _identity(self.source_fd) == self.identity and
            _same(self.source_fd, SOURCE_NAME, self.segment_fd)):
      return False
    try:
      with os.scandir(self.segment_fd) as entries:
        for count, entry in enumerate(entries, 1):
          if count > MAX_SEGMENT_ENTRIES or entry.name.endswith('.lock'):
            return False
      return stat.S_ISREG(os.fstat(self.source_fd).st_mode)
    except OSError:
      return False

  def close(self) -> None:
    for name in ('source_fd', 'segment_fd', 'root_fd'):
      fd = getattr(self, name)
      if fd >= 0:
        os.close(fd)
        setattr(self, name, -1)


class MediaLease:
  def __init__(self, source: VerifiedRecording, video_fd: int):
    self.source, self.video_fd = source, video_fd
    self.size = os.fstat(video_fd).st_size

  def close(self) -> None:
    if self.video_fd >= 0:
      os.close(self.video_fd)
      self.video_fd = -1
    self.source.close()


def byte_range(value: str | None, size: int) -> tuple[int, int] | None:
  if value is None:
    return 0, size - 1
  if len(value) > 80:
    return None
  matched = _RANGE.fullmatch(value)
  if matched is None or size <= 0:
    return None
  first, last = matched.groups()
  if not first and not last:
    return None
  if not first:
    length = int(last)
    return (max(0, size - length), size - 1) if length > 0 else None
  start = int(first)
  end = min(int(last), size - 1) if last else size - 1
  return (start, end) if start < size and end >= start else None


def _ffmpeg_binary() -> Path:
  import ffmpeg
  return Path(ffmpeg.__file__).resolve().parent / 'install/bin/ffmpeg'


class RecordingMedia:
  def __init__(self, root: Path | None = None, *, ffmpeg_binary: Path | None = None):
    self.root = root if root is not None else Path(Paths.log_root())
    self.ffmpeg_binary = ffmpeg_binary if ffmpeg_binary is not None else _ffmpeg_binary()
    self._cache = tempfile.TemporaryDirectory(prefix='starpilot-galaxy-media-')
    self._cache_path = Path(self._cache.name) / 'quick-road.mp4'
    self._cache_key: tuple | None = None
    self._lock = threading.Lock()
    self._state_lock = threading.Lock()
    self._process: subprocess.Popen | None = None
    self._closed = False

  def _stop_child(self) -> None:
    with self._state_lock:
      process = self._process
    if process is not None and process.poll() is None:
      try:
        os.killpg(process.pid, signal.SIGTERM)
      except ProcessLookupError:
        return
      try:
        process.wait(timeout=1)
      except subprocess.TimeoutExpired:
        try:
          os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
          pass
        process.wait(timeout=1)

  def stop_child(self) -> None:
    """Managed forced shutdown may stop work without closing an active handler's files."""
    with self._state_lock:
      self._closed = True
    self._stop_child()

  def close(self) -> None:
    self.stop_child()
    with self._lock:
      self._cache.cleanup()

  def open(self, name: str, *, prepare: bool = True) -> MediaLease:
    source = VerifiedRecording(self.root, name)
    try:
      key = (name, source.identity)
      if not self._lock.acquire(blocking=False):
        raise RecordingMediaBusy
      try:
        if self._closed:
          raise RecordingMediaUnavailable
        if self._cache_key != key or not self._cache_path.exists():
          if not prepare:
            raise RecordingMediaNotPrepared
          self._remux(source)
          self._cache_key = key
        video_fd = os.open(self._cache_path, FILE_FLAGS)
        video_info = os.fstat(video_fd)
        if not stat.S_ISREG(video_info.st_mode) or not 0 < video_info.st_size <= MAX_MP4_BYTES or not source.current():
          os.close(video_fd)
          raise RecordingMediaChanged
        return MediaLease(source, video_fd)
      finally:
        self._lock.release()
    except Exception:
      source.close()
      raise

  def _remux(self, source: VerifiedRecording) -> None:
    pending = Path(self._cache.name) / 'pending.mp4'
    pending.unlink(missing_ok=True)
    descriptor_root = '/proc/self/fd' if Path('/proc/self/fd').is_dir() else '/dev/fd'
    command = [str(self.ffmpeg_binary), '-nostdin', '-hide_banner', '-loglevel', 'error',
               '-protocol_whitelist', 'file,pipe', '-f', 'mpegts', '-i', f'{descriptor_root}/{source.source_fd}',
               '-map', '0:v:0', '-an', '-c:v', 'copy', '-bsf:v', 'h264_mp4toannexb', '-movflags', 'faststart',
               '-fs', str(MAX_MP4_BYTES), '-f', 'mp4', '-y', str(pending)]
    try:
      process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, pass_fds=(source.source_fd,), start_new_session=True)
      with self._state_lock:
        self._process = process
        closed = self._closed
      if closed:
        self._stop_child()
        raise RecordingMediaUnavailable
      try:
        result = process.wait(timeout=REMUX_TIMEOUT_S)
      except subprocess.TimeoutExpired:
        self._stop_child()
        raise RecordingMediaUnavailable from None
      if not source.current():
        raise RecordingMediaChanged
      if result != 0:
        raise RecordingMediaUnsupported('Quick road source is not a supported H.264 MPEG-TS recording')
      info = pending.stat()
      if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_MP4_BYTES:
        raise RecordingMediaUnavailable
      pending.replace(self._cache_path)
    except OSError as error:
      raise RecordingMediaUnavailable from error
    finally:
      with self._state_lock:
        self._process = None
      pending.unlink(missing_ok=True)
