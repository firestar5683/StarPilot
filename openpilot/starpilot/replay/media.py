"""Bounded epoch-owned fMP4 fragments from the existing hardware H.264 encoder."""
from collections import deque
import ctypes as C
import json
import math
import os
from pathlib import Path
import re
from typing import TypedDict

MAX_FRAGMENT_BYTES = 1024 * 1024
MAX_MEDIA_BYTES = 8 * 1024 * 1024
MAX_FRAGMENTS = 40
START_CODE = re.compile(b'\x00\x00(?:\x00)?\x01')


def codec_string(access_unit: bytes) -> str:
  for match in START_CODE.finditer(access_unit):
    if match.end() + 4 <= len(access_unit) and access_unit[match.end()] & 31 == 7:
      return 'avc1.' + access_unit[match.end() + 1:match.end() + 4].hex()
  raise ValueError('Replay keyframe has no SPS codec identity')


def atomic_json(path: Path, value):
  temporary = path.with_suffix('.tmp')
  fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
  with os.fdopen(fd, 'w') as stream:
    stream.write(json.dumps(value, allow_nan=False, separators=(',', ':')))
  temporary.replace(path)


class FrameTimeline:
  """Capture-time PTS; flush breaks continuity across pauses and long stalls."""
  def __init__(self):
    self.epoch, self.count = 0, 0
    self.captured_ns = None
    self.pts_ns = self.end_ns = 0

  def next(self, epoch: int, captured_ns: int):
    if (type(epoch) is not int or epoch <= 0 or epoch < self.epoch or
        type(captured_ns) is not int or captured_ns <= 0):
      raise ValueError('Invalid replay media clock')
    if epoch != self.epoch:
      self.epoch, self.count = epoch, 0
      self.captured_ns, self.end_ns = None, 0
    if self.captured_ns is None:
      self.pts_ns = self.end_ns
    else:
      elapsed = captured_ns - self.captured_ns
      if elapsed <= 0:
        raise ValueError('Replay capture clock must advance')
      self.pts_ns += max(1000, elapsed) if elapsed <= 1_000_000_000 else 50_000_000
    self.captured_ns = captured_ns
    self.end_ns = self.pts_ns + 50_000_000
    keyframe = self.count % 10 == 0
    self.count += 1
    return self.pts_ns // 1000, keyframe

  def flush(self):
    self.captured_ns = None


class MediaMux:
  def __init__(self, width: int, height: int, first: bytes, *, library: Path | None = None):
    from openpilot.common.basedir import BASEDIR
    library = library or Path(BASEDIR) / 'openpilot/tools/replay/libmedia_mux.so'
    self.codec = codec_string(first)
    self.lib = C.CDLL(str(library))
    pointer, size = C.c_void_p, C.c_size_t
    self.lib.replay_mux_create.argtypes = [C.c_int, C.c_int, pointer, size, pointer, size]
    self.lib.replay_mux_create.restype = pointer
    self.lib.replay_mux_init.argtypes = [pointer, pointer, size, pointer, size]
    self.lib.replay_mux_init.restype = C.c_int
    self.lib.replay_mux_frame.argtypes = [pointer, pointer, size, C.c_int64, C.c_int64, C.c_int, pointer, size, pointer, size]
    self.lib.replay_mux_frame.restype = C.c_int
    self.lib.replay_mux_close.argtypes = [pointer]
    self.lib.replay_mux_close.restype = None
    self.output = C.create_string_buffer(MAX_FRAGMENT_BYTES)
    self.error = C.create_string_buffer(512)
    self.handle = self.lib.replay_mux_create(width, height, first, len(first), self.error, len(self.error))
    if not self.handle:
      raise RuntimeError(self.error.value.decode('utf8', 'replace'))
    try:
      self.init = self._result(self.lib.replay_mux_init(self.handle, self.output, len(self.output), self.error, len(self.error)))
    except BaseException:
      self.close()
      raise

  def _result(self, count: int) -> bytes:
    if count <= 0 or count > MAX_FRAGMENT_BYTES:
      raise RuntimeError(self.error.value.decode('utf8', 'replace') or 'Empty replay MP4 fragment')
    return C.string_at(self.output, count)

  def frame(self, packet: bytes, *, pts_us: int, duration_us: int = 50000, keyframe: bool):
    return self._result(self.lib.replay_mux_frame(self.handle, packet, len(packet), pts_us, duration_us, int(keyframe),
                                                self.output, len(self.output), self.error, len(self.error)))

  def close(self):
    handle, self.handle = self.handle, None
    if handle:
      self.lib.replay_mux_close(handle)


class MediaFragment(TypedDict):
  sequence: int
  mediaPath: str
  length: int
  firstPosition: float | None
  lastPosition: float | None
  keyframe: bool


class MediaStore:
  def __init__(self, session_dir: Path, session_id: str, width: int, height: int):
    self.root = Path(session_dir) / 'media'
    self.root.mkdir(mode=0o700, exist_ok=True)
    self.manifest = Path(session_dir) / 'media.json'
    self.session_id, self.width, self.height = session_id, width, height
    self.epoch = 0
    self.codec = ''
    self.init: MediaFragment | None = None
    self.fragments: deque[MediaFragment] = deque()
    self.sequence = 0

  def _write(self, name: str, data: bytes):
    if not 0 < len(data) <= MAX_FRAGMENT_BYTES:
      raise ValueError('Replay MP4 fragment exceeds its bounded size')
    path = self.directory / name
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, 'wb') as stream:
      stream.write(data)
    return str(path)

  def begin(self, epoch: int, codec: str, init: bytes):
    if epoch <= self.epoch:
      raise ValueError('Replay media epoch must advance')
    old = self.init, tuple(self.fragments)
    self.epoch, self.codec, self.sequence = epoch, codec, 0
    self.directory = self.root / str(epoch)
    self.directory.mkdir(mode=0o700)
    path = self._write('init.mp4', init)
    self.init = {'sequence': 0, 'mediaPath': path, 'length': len(init), 'firstPosition': None, 'lastPosition': None, 'keyframe': True}
    self.fragments.clear()
    self._save()
    previous, fragments = old
    if previous is not None:
      for item in (previous, *fragments):
        Path(item['mediaPath']).unlink(missing_ok=True)
      Path(previous['mediaPath']).parent.rmdir()

  def publish(self, data: bytes, *, position: float, keyframe: bool):
    init = self.init
    if init is None:
      raise ValueError('Replay media has not been initialized')
    if not self.fragments and not keyframe:
      raise ValueError('Replay media must begin with a keyframe')
    self.sequence += 1
    item: MediaFragment = {'sequence': self.sequence, 'mediaPath': self._write(f'{self.sequence}.m4s', data), 'length': len(data),
                           'firstPosition': position, 'lastPosition': position, 'keyframe': bool(keyframe)}
    self.fragments.append(item)
    while (len(self.fragments) > MAX_FRAGMENTS or
           sum(row['length'] for row in self.fragments) + init['length'] > MAX_MEDIA_BYTES):
      following = next((i for i, row in enumerate(self.fragments) if i and row['keyframe']), None)
      if following is None:
        raise RuntimeError('Replay GOP exceeds the media memory budget')
      for _ in range(following):
        Path(self.fragments.popleft()['mediaPath']).unlink(missing_ok=True)
    self._save()
    return item

  def summary(self):
    return {'epoch': self.epoch, 'codec': self.codec, 'width': self.width, 'height': self.height,
            'firstSequence': self.fragments[0]['sequence'] if self.fragments else 1,
            'lastSequence': self.fragments[-1]['sequence'] if self.fragments else 0}

  def _save(self):
    atomic_json(self.manifest, {'version': 1, 'sessionId': self.session_id, **self.summary(),
                                'init': self.init, 'fragments': list(self.fragments)})


def media_descriptor(session_dir: Path, epoch: int, sequence: int, count: int = 1):
  """Read renderer metadata; never accept a client-supplied path or create resources."""
  import stat
  if (type(epoch) is not int or epoch <= 0 or type(sequence) is not int or sequence < 0 or
      type(count) is not int or not 1 <= count <= 8):
    raise ValueError('Invalid replay media identity')
  session_dir = Path(session_dir)
  path = session_dir / 'media.json'
  try:
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
  except FileNotFoundError:
    return {'available': False, 'epoch': epoch, 'sequence': sequence}
  with os.fdopen(fd, 'rb') as stream:
    info = os.fstat(stream.fileno())
    # Atomic replacement can unlink this already-open manifest; hard links remain forbidden.
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600 or
        info.st_nlink not in (0, 1) or not 0 < info.st_size <= 65536):
      raise ValueError('Unsafe replay media metadata')
    value = json.loads(stream.read(65537))
  if (not isinstance(value, dict) or value.get('version') != 1 or value.get('sessionId') != session_dir.name or
      type(value.get('epoch')) is not int or value['epoch'] <= 0 or
      not isinstance(value.get('fragments'), list) or len(value['fragments']) > MAX_FRAGMENTS or
      not all(isinstance(row, dict) for row in value['fragments']) or
      type(value.get('firstSequence')) is not int or value['firstSequence'] < 1 or
      type(value.get('lastSequence')) is not int or value['lastSequence'] < 0 or
      not isinstance(value.get('codec'), str) or re.fullmatch(r'avc1\.[a-f0-9]{6}', value['codec']) is None):
    raise ValueError('Invalid replay media metadata')
  if value.get('epoch') != epoch:
    return {'available': False, 'epoch': value.get('epoch'), 'sequence': sequence, 'code': 'media_epoch_changed'}
  def descriptor(sequence):
    row = value.get('init') if sequence == 0 else next((row for row in value['fragments'] if row.get('sequence') == sequence), None)
    if row is None:
      code = 'media_evicted' if sequence and sequence < value.get('firstSequence', 1) else 'media_pending'
      return {'available': False, 'epoch': epoch, 'sequence': sequence, 'code': code}
    filename = 'init.mp4' if sequence == 0 else f'{sequence}.m4s'
    expected = session_dir / 'media' / str(epoch) / filename
    if (not isinstance(row, dict) or row.get('mediaPath') != str(expected) or type(row.get('length')) is not int or
        not 0 < row['length'] <= MAX_FRAGMENT_BYTES or type(row.get('keyframe')) is not bool):
      raise ValueError('Invalid replay fragment path')
    for key in ('firstPosition', 'lastPosition'):
      position = row.get(key)
      if (sequence == 0 and position is not None or sequence != 0 and
          (type(position) not in (int, float) or not math.isfinite(position) or not 0 <= position <= 604800)):
        raise ValueError('Invalid replay fragment position')
    return {'available': True, 'epoch': epoch, 'sequence': sequence, 'mediaPath': str(expected), 'length': row['length'],
            'firstPosition': row.get('firstPosition'), 'lastPosition': row.get('lastPosition'), 'keyframe': row.get('keyframe'),
            'codec': value.get('codec')}

  if count == 1 or sequence == 0:
    return descriptor(sequence)
  fragments, total = [], 0
  for selected in range(sequence, sequence + count):
    row = descriptor(selected)
    if not row['available']:
      if not fragments or row.get('code') != 'media_pending':
        return row
      break
    if total + row['length'] > MAX_FRAGMENT_BYTES:
      break
    fragments.append(row)
    total += row['length']
  return {'available': True, 'epoch': epoch, 'sequence': sequence, 'fragments': fragments}
