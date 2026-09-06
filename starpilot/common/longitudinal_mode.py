"""Coherent mode Params reads for participating Python writers/readers.

The sidecar lock is outside the Params key directory (no registry addition).
Never unlink/replace it while processes are running. All locks are nonblocking:
background refreshers retry and keep the last complete toggle object on failure.
Legacy Dom writers are deliberately not excluded; their settled values remain
visible, but advisory locking cannot make their multi-key writes atomic.
"""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path

MODE_KEYS = ("ExperimentalMode", "ConditionalChill", "ConditionalExperimental")


@contextmanager
def mode_lock(params, *, exclusive=False):
  directory = Path(params.get_param_path()).parent
  fd = os.open(directory / ".longitudinal_mode.lock", os.O_CREAT | os.O_RDWR | os.O_CLOEXEC, 0o660)
  try:
    fcntl.flock(fd, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
    yield
  finally:
    os.close(fd)


def read_mode_values(params):
  with mode_lock(params):
    return {key: params.get_bool(key) for key in MODE_KEYS}


def request_mode_refresh(params, params_memory, toggles):
  """Background poll: also honor external writers which don't send a notification.

  Compare against the *published* snapshot, not a last-polled value. A refresh
  already in flight may contain an older selection; keep requesting until that
  selection is actually published. Busy/error is not a new all-false snapshot.
  """
  try:
    values = read_mode_values(params)
  except OSError:
    return
  if values != getattr(toggles, "longitudinal_mode_values", None):
    params_memory.put_bool("StarPilotTogglesUpdated", True)
