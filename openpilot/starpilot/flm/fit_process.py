"""One optional fitter process, nonblocking bounded IPC; no Python workerthread."""

import json
import os
import signal
import subprocess
import sys

MAX_INPUT = 8 * 1024 * 1024
MAX_OUTPUT = 65536
CHUNK = 65536
WALL_NS = 30_000_000_000
INTERVAL_NS = 60_000_000_000


class FitProcess:
  def __init__(self):
    self.child = None
    self.pending = b''
    self.position = 0
    self.output = bytearray()
    self.token = None
    self.started_ns = self.last_start_ns = 0
    self.reaping = False
    self.reason = 'idle'

  def submit(self, snapshot, *, token, now_ns):
    if self.child is not None or self.last_start_ns and now_ns - self.last_start_ns < INTERVAL_NS:
      return False
    try:
      payload = json.dumps(snapshot, separators=(',', ':'), allow_nan=False).encode()
    except (TypeError, ValueError, MemoryError):
      self.reason = 'fit_snapshot_invalid'
      self.last_start_ns = now_ns
      return False
    if len(payload) > MAX_INPUT:
      self.reason = 'fit_snapshot_bound'
      self.last_start_ns = now_ns
      return False
    environment = dict(os.environ)
    # Bound numerical backend thread creation only in this child.
    for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
      environment[key] = '1'
    environment['STARPILOT_FLM_PARENT_PID'] = str(os.getpid())
    try:
      self.child = subprocess.Popen(
        [sys.executable, '-B', '-m', 'openpilot.starpilot.flm.fit_worker'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=environment,
      )
    except OSError:
      self.reason = 'fit_child_unavailable'
      self.last_start_ns = now_ns
      return False
    try:
      os.set_blocking(self.child.stdin.fileno(), False)
      os.set_blocking(self.child.stdout.fileno(), False)
    except OSError:
      self.close('fit_pipe_setup_failed')
      self.last_start_ns = now_ns
      return False
    self.pending, self.position, self.output = payload, 0, bytearray()
    self.token, self.started_ns, self.last_start_ns = token, now_ns, now_ns
    self.reaping = False
    self.reason = 'fitting'
    return True

  def cancel(self, reason):
    if self.child is not None and not self.reaping:
      try:
        os.killpg(self.child.pid, signal.SIGKILL)
      except ProcessLookupError:
        pass
      self.reaping = True
    self.pending = b''
    self.output.clear()
    self.reason = reason

  def close(self, reason='fitter_closed'):
    # Only parent shutdown/setup failure; the live20Hz loop uses cancel/poll.
    self.cancel(reason)
    if self.child is not None:
      try:
        self.child.wait(timeout=1.0)
      except subprocess.TimeoutExpired:
        return False
      self._close()
    return True

  def poll(self, *, token, now_ns):
    child = self.child
    if child is None:
      return None
    if token != self.token or now_ns - self.started_ns > WALL_NS:
      self.cancel('fit_context_changed' if token != self.token else 'fit_wall_limit')
    if self.reaping:
      if child.poll() is not None:
        self._close()
      return None
    if self.position < len(self.pending):
      try:
        self.position += os.write(child.stdin.fileno(), self.pending[self.position : self.position + CHUNK])
      except BlockingIOError:
        pass
      except BrokenPipeError:
        self.cancel('fit_input_closed')
        return None
    if self.position == len(self.pending) and child.stdin is not None:
      child.stdin.close()
      child.stdin = None
      self.pending = b''
    try:
      part = os.read(child.stdout.fileno(), CHUNK)
    except BlockingIOError:
      part = None
    if part:
      self.output.extend(part)
      if len(self.output) > MAX_OUTPUT:
        self.cancel('fit_output_bound')
        return None
    code = child.poll()
    if code is None:
      return None
    # Drain one final bounded chunk after exit; producer cannot consume a
    # partially read report merely because the child exited successfully.
    try:
      tail = os.read(child.stdout.fileno(), CHUNK)
    except BlockingIOError:
      tail = b''
    self.output.extend(tail)
    result = None
    if code == 0 and len(self.output) <= MAX_OUTPUT:
      try:
        result = json.loads(self.output)
      except (ValueError, UnicodeError):
        self.reason = 'fit_report_invalid'
    else:
      self.reason = 'fit_failed'
    self._close()
    return result

  def _close(self):
    child = self.child
    if child is not None:
      for stream in (child.stdin, child.stdout):
        if stream is not None:
          stream.close()
      # poll() already reaped the direct child. This actor contract forbids any
      # spawned descendants; actual lifecycle qualification is root-owned.
    self.child = None
    self.pending = b''
    self.position = 0
    self.output = bytearray()
    self.token = None
    self.reaping = False
