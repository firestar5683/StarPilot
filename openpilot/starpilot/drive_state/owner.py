"""One session-bound request owner shared by local and authenticated controls."""

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import re
import stat
import threading
import uuid

from openpilot.common.params import UnknownKeyName

from .resolver import Mode


SESSION_KEY = 'DriveStateSession'
REQUEST_KEY = 'DriveStateRequest'
_HEX = re.compile(r'[0-9a-f]{32}\Z')


class Rejected(ValueError):
  pass


@dataclass(frozen=True)
class State:
  mode: Mode = Mode.AUTO
  revision: str | None = None
  available: bool = False


def valid_session(value) -> bool:
  return (type(value) is dict and set(value) == {'version', 'id', 'pid', 'birth', 'boot'} and
          type(value['version']) is int and value['version'] == 1 and
          isinstance(value['id'], str) and _HEX.fullmatch(value['id']) is not None and
          isinstance(value['boot'], str) and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value['boot']) is not None and
          all(type(value[key]) is int and value[key] > 0 for key in ('pid', 'birth')))


def request_state(value, session) -> State:
  if (type(value) is not dict or set(value) != {'version', 'session', 'revision', 'mode'} or
      type(value['version']) is not int or value['version'] != 1 or value['session'] != session['id'] or
      not isinstance(value['revision'], str) or _HEX.fullmatch(value['revision']) is None):
    return State()
  try:
    return State(Mode(value['mode']), value['revision'], True)
  except (TypeError, ValueError):
    return State()


def process_identity(pid: int):
  try:
    raw = Path(f"/proc/{pid}/stat").read_bytes()
    fields = raw[raw.rfind(b')') + 2:].split()
    return int(fields[19]), fields[0]
  except (OSError, IndexError, ValueError):
    return None, None


def manager_alive(session) -> bool:
  try:
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != session['boot']:
      return False
  except OSError:
    return False
  birth, state = process_identity(session['pid'])
  return birth == session['birth'] and state not in (None, b'Z', b'X')


class DriveStateOwner:
  def __init__(self, params, root: Path, *, alive: Callable[[dict], bool] = manager_alive):
    self.params, self.root, self.alive = params, Path(root), alive
    self._lock = threading.RLock()

  @contextmanager
  def _exclusive(self):
    with self._lock:
      self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
      info = self.root.lstat()
      if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise Rejected('Drive state storage is unavailable')
      fd = os.open(self.root / '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
      try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
          raise Rejected('Drive state storage is unavailable')
        try:
          fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
          raise Rejected("Drive state changed; refresh and try again") from None
        yield
      finally:
        os.close(fd)

  def _read(self):
    try:
      session = self.params.get(SESSION_KEY)
      if not valid_session(session) or not self.alive(session):
        return None, State()
      return session, request_state(self.params.get(REQUEST_KEY), session)
    except (OSError, KeyError, TypeError, ValueError, UnknownKeyName):
      return None, State()

  def snapshot(self) -> State:
    return self._read()[1]

  def initialize(self, *, pid: int, birth: int, boot: str) -> State:
    session = {'version': 1, 'id': uuid.uuid4().hex, 'pid': pid, 'birth': birth, 'boot': boot}
    if not valid_session(session) or not self.alive(session):
      raise Rejected('Manager session is unavailable')
    with self._exclusive():
      request = self._record(session, Mode.AUTO)
      # Mismatched generations resolve Auto during either write or a crash.
      self.params.put(REQUEST_KEY, request, block=True)
      self.params.put(SESSION_KEY, session, block=True)
      return request_state(request, session)

  def initialize_manager(self) -> State:
    pid = os.getpid()
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    return self.initialize(pid=pid, birth=process_identity(pid)[0], boot=boot)

  @staticmethod
  def _record(session, mode):
    return {'version': 1, 'session': session['id'], 'revision': uuid.uuid4().hex, 'mode': mode.value}

  def request(self, mode: str, *, expected_revision: str, authorized: Callable[[], bool],
              override_allowed: Callable[[], bool]) -> State:
    try:
      desired = Mode(mode)
    except (TypeError, ValueError):
      raise Rejected('Choose Auto, Offroad or Onroad') from None
    with self._exclusive():
      session, current = self._read()
      if not current.available or current.revision != expected_revision:
        raise Rejected('Drive state changed; refresh and try again')
      if not authorized():
        raise Rejected('Drive state changes are unavailable')
      if desired == current.mode:
        return current
      if desired == Mode.ONROAD and not override_allowed():
        raise Rejected('Park and disengage before changing drive state')
      # These callbacks recheck the authenticated caller and physical source,
      # rather than relying on the state that produced the button.
      if not authorized() or (desired == Mode.ONROAD and not override_allowed()) or not self.alive(session):
        raise Rejected('Drive state changes are unavailable')
      observed_session, observed = self._read()
      if observed_session != session or observed != current:
        raise Rejected('Drive state changed; refresh and try again')
      record = self._record(session, desired)
      if not authorized() or (desired == Mode.ONROAD and not override_allowed()):
        raise Rejected('Drive state changes are unavailable')
      self.params.put(REQUEST_KEY, record, block=True)
      return request_state(record, session)
