"""Durable map context from validated GPS, independent of route authority."""
import fcntl
import json
import math
import os
from pathlib import Path
import tempfile
import time

CHECKPOINT_SECONDS = 5.


def coordinates(value):
  return (isinstance(value, dict) and
          all(type(value.get(key)) in (int, float) and math.isfinite(value[key])
              for key in ('longitude', 'latitude')) and
          -180 <= value['longitude'] <= 180 and -90 <= value['latitude'] <= 90)


class LastPositionStore:
  def __init__(self, root, *, clock=time.monotonic):
    self.root = Path(root)
    self.path = self.root / 'last-position.json'
    self.clock = clock
    self.cached = None
    self.dirty = False
    self.last_attempt = None

  def _read_disk(self):
    try:
      with self.path.open('rb') as source:
        raw = source.read(4097)
      value = json.loads(raw)
      if (len(raw) > 4096 or not coordinates(value) or value.get('version') != 1 or
          type(value.get('recordedAt')) not in (int, float) or not math.isfinite(value['recordedAt']) or
          value['recordedAt'] <= 0):
        return None
      point = {key: float(value[key]) for key in ('longitude', 'latitude', 'recordedAt')}
      if type(value.get('bearing')) in (int, float) and math.isfinite(value['bearing']):
        point['bearing'] = float(value['bearing']) % 360
      return dict(point, validForMs=0, lastKnown=True)
    except (OSError, ValueError, TypeError, KeyError):
      return None

  def read(self):
    saved = self._read_disk()
    if saved and not self.dirty:
      self.cached = saved
      self.dirty = False
    return dict(self.cached) if self.cached else None

  def record(self, point):
    if not coordinates(point):
      return
    previous = self.read() or {}
    value = {key: float(point[key]) for key in ('longitude', 'latitude')}
    bearing = point.get('bearing', previous.get('bearing'))
    if not isinstance(bearing, (int, float)) or isinstance(bearing, bool) or not math.isfinite(bearing):
      bearing = previous.get('bearing')
    if isinstance(bearing, (int, float)) and not isinstance(bearing, bool) and math.isfinite(bearing):
      value['bearing'] = float(bearing) % 360
    if all(previous.get(key) == value.get(key) for key in ('longitude', 'latitude', 'bearing')):
      self.flush()
      return
    # A display timestamp must survive reboot; it never grants a live GPS lease.
    self.cached = dict(value, recordedAt=time.time(), validForMs=0, lastKnown=True)  # noqa: TID251
    self.dirty = True
    self.flush()

  def flush(self, *, force=False):
    now = self.clock()
    if (not self.dirty or self.cached is None or
        not force and self.last_attempt is not None and 0 <= now - self.last_attempt < CHECKPOINT_SECONDS):
      return
    self.last_attempt = now
    value = {key: item for key, item in self.cached.items() if key not in ('validForMs', 'lastKnown')}
    temporary = None
    try:
      self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
      with (self.root / '.position-lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        fd, temporary = tempfile.mkstemp(dir=self.root, prefix='.position-')
        with os.fdopen(fd, 'w') as out:
          json.dump(dict(value, version=1), out, allow_nan=False, separators=(',', ':'))
          out.flush()
          os.fsync(out.fileno())
        os.replace(temporary, self.path)
        directory = os.open(self.root, os.O_RDONLY)
        try:
          os.fsync(directory)
        finally:
          os.close(directory)
      self.dirty = False
    except OSError:
      # Live GPS and the in-memory last fix remain usable if storage is unavailable.
      pass
    finally:
      if temporary is not None:
        try:
          Path(temporary).unlink(missing_ok=True)
        except OSError:
          pass
