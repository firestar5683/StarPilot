"""One parked, read-only FLM operation with an isolated local-log worker."""

from collections.abc import Callable, Sequence
import json
import logging
import os
from pathlib import Path
import selectors
import subprocess
import sys
import threading
import time
import uuid

from openpilot.common.hardware.hw import Paths
from openpilot.starpilot.galaxy.drive_history import SEGMENT_NAME


MAX_REPORT_BYTES = 1024 * 1024
MAX_PIPE_BYTES = MAX_REPORT_BYTES + 4096
WALL_DEADLINE_SECONDS = 5 * 60
POLL_SECONDS = 0.05
ACTIVE_STATE = 'running'
ERROR_CODES = frozenset(('invalid_request', 'busy', 'not_parked', 'operation_changed', 'unavailable',
                         'canceled', 'process_failed', 'deadline', 'recording_unavailable', 'decode_failed', 'resource_limit'))


class FlmOperationError(RuntimeError):
  def __init__(self, code: str):
    self.code = code if code in ERROR_CODES else 'unavailable'
    super().__init__(self.code)


def _stop_child(child: subprocess.Popen) -> None:
  if child.poll() is not None:
    child.wait()
    return
  try:
    child.terminate()
  except ProcessLookupError:
    pass
  try:
    child.wait(timeout=0.5)
  except subprocess.TimeoutExpired:
    try:
      child.kill()
    except ProcessLookupError:
      pass
    try:
      child.wait(timeout=0.5)
    except subprocess.TimeoutExpired as error:
      raise FlmOperationError('unavailable') from error


class FlmAnalysisOwner:
  """Parent alone owns fresh parked authority, operation identity and report visibility."""

  def __init__(self, *, parked: Callable[[], bool], root: Path | None = None,
               worker_argv: Sequence[str] | None = None):
    self.root = Path(Paths.log_root()) if root is None else root
    self._parked = parked
    self._worker_argv = tuple(worker_argv) if worker_argv is not None else (
      sys.executable, '-m', 'openpilot.starpilot.flm.operation_worker')
    self._lock = threading.RLock()
    self._session = uuid.uuid4().hex
    self._sequence = 0
    self._closed = False
    self._cancel = threading.Event()
    self._child: subprocess.Popen | None = None
    self._monitor_thread: threading.Thread | None = None
    self._report: dict | None = None
    self._status = self._fresh_status('idle', None, 0)

  @staticmethod
  def _fresh_status(state: str, operation_id: str | None, selected: int, processed: int = 0,
                    error_code: str | None = None) -> dict:
    return {'version': 1, 'operationId': operation_id, 'state': state, 'selected': selected,
            'processed': processed, 'errorCode': error_code}

  def _allowed(self) -> bool:
    try:
      return self._parked() is True
    except Exception:
      return False

  def _revoke_if_unparked(self) -> None:
    if self._allowed():
      return
    with self._lock:
      if self._status['state'] != 'idle':
        self._status = self._fresh_status('unavailable', self._status['operationId'],
                                          self._status['selected'], self._status['processed'], 'not_parked')
        self._report = None
        self._cancel.set()

  def snapshot(self) -> dict:
    self._revoke_if_unparked()
    with self._lock:
      return dict(self._status)

  def start(self, segment_names: Sequence[str]) -> dict:
    if (type(segment_names) not in (tuple, list) or not 1 <= len(segment_names) <= 5 or
        any(type(name) is not str or len(name) > 180 or SEGMENT_NAME.fullmatch(name) is None
            for name in segment_names) or len(set(segment_names)) != len(segment_names)):
      raise FlmOperationError('invalid_request')
    if not self._allowed():
      raise FlmOperationError('not_parked')
    with self._lock:
      if self._closed:
        raise FlmOperationError('unavailable')
      if self._status['state'] == ACTIVE_STATE or self._child is not None or \
         (self._monitor_thread is not None and self._monitor_thread.is_alive()):
        raise FlmOperationError('busy')
      self._sequence += 1
      token = f'{self._session}:{self._sequence}'
      self._cancel = threading.Event()
      self._report = None
      self._status = self._fresh_status(ACTIVE_STATE, token, len(segment_names))
      request = json.dumps({'root': str(self.root), 'segments': list(segment_names), 'parentPid': os.getpid()},
                           sort_keys=True, separators=(',', ':')).encode()
      if len(request) > 2048:
        self._status = self._fresh_status('failed', token, len(segment_names), error_code='invalid_request')
        raise FlmOperationError('invalid_request')
      # The monitor must create the child: Linux PR_SET_PDEATHSIG follows the
      # creating thread, and an HTTP request thread ends after this response.
      self._monitor_thread = threading.Thread(target=self._monitor, args=(token, self._cancel,
                                                                           tuple(segment_names), request), daemon=True)
      try:
        self._monitor_thread.start()
      except RuntimeError as error:
        self._monitor_thread = None
        self._status = self._fresh_status('failed', token, len(segment_names), error_code='unavailable')
        raise FlmOperationError('unavailable') from error
    self._revoke_if_unparked()
    return self.snapshot()

  def _monitor(self, token: str, canceled: threading.Event, names: tuple[str, ...], request: bytes) -> None:
    result: dict | None = None
    error: str | None = 'process_failed'
    child: subprocess.Popen | None = None
    reaped = False
    try:
      if canceled.is_set():
        error = 'canceled'
        return
      if not self._allowed():
        error = 'not_parked'
        return
      child = subprocess.Popen(self._worker_argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, bufsize=0, close_fds=True)
      with self._lock:
        if self._status['operationId'] == token:
          self._child = child
      if child.stdin is None:
        raise OSError('worker input unavailable')
      child.stdin.write(request)
      child.stdin.close()
      result, error = self._read_worker(token, child, canceled, names)
      if error is None:
        if result is None:
          raise ValueError('missing report')
        sources = result['segments']
        if (result.get('schemaVersion') != 1 or result.get('purpose') != 'offline_tracking_diagnostics' or
            result.get('tuneRecommendation', 1) is not None or result.get('vehicleQualification') is not False or
            type(sources) is not list or [row['source']['segmentName'] for row in sources] != list(names)):
          raise ValueError('report shape')
        result = {**result, 'operationId': token}
        if len(json.dumps(result, allow_nan=False).encode()) > MAX_REPORT_BYTES:
          raise ValueError('report limit')
    except Exception:
      logging.exception('FLM operation failed')
      error = 'process_failed'
    finally:
      if child is not None:
        try:
          _stop_child(child)
          reaped = True
        except (OSError, FlmOperationError):
          error = 'unavailable'
        for pipe in (child.stdin, child.stdout):
          if pipe is None:
            continue
          try:
            pipe.close()
          except OSError:
            error = 'unavailable'
      else:
        reaped = True
      if not self._allowed():
        error = 'not_parked'
      with self._lock:
        if self._status['operationId'] == token:
          if self._closed or self._status['state'] == 'unavailable':
            error = 'not_parked' if not self._closed else 'unavailable'
          if error is None and not canceled.is_set() and reaped:
            self._report = result
            self._status = self._fresh_status('completed', token, len(names), len(names))
          else:
            code = 'unavailable' if self._closed else \
                   'canceled' if canceled.is_set() and error != 'not_parked' else error or 'canceled'
            unavailable = code in ('not_parked', 'unavailable', 'recording_unavailable', 'decode_failed', 'resource_limit')
            state = 'canceled' if code == 'canceled' else 'unavailable' if unavailable else 'failed'
            self._status = self._fresh_status(state, token, len(names), self._status['processed'], code)
            self._report = None
        if child is not None and self._child is child and reaped:
          self._child = None

  def _read_worker(self, token: str, child: subprocess.Popen, canceled: threading.Event,
                   names: tuple[str, ...]) -> tuple[dict | None, str | None]:
    if child.stdout is None:
      return None, 'process_failed'
    deadline = time.monotonic() + WALL_DEADLINE_SECONDS
    buffer = bytearray()
    consumed = 0
    result = None
    error = None
    with selectors.DefaultSelector() as selector:
      selector.register(child.stdout, selectors.EVENT_READ)
      while error is None:
        if canceled.is_set():
          return None, 'canceled'
        if not self._allowed():
          return None, 'not_parked'
        if time.monotonic() >= deadline:
          return None, 'deadline'
        if not selector.select(POLL_SECONDS):
          continue
        chunk = os.read(child.stdout.fileno(), 64 * 1024)
        if not chunk:
          break  # Pipe EOF; wait only a bounded time for the child to exit.
        consumed += len(chunk)
        if consumed > MAX_PIPE_BYTES:
          return None, 'process_failed'
        buffer.extend(chunk)
        while b'\n' in buffer:
          line, _, remainder = buffer.partition(b'\n')
          buffer = bytearray(remainder)
          message = json.loads(line)
          if type(message) is not dict:
            return None, 'process_failed'
          if message.get('kind') == 'progress' and type(message.get('processed')) is int and \
             0 < message['processed'] <= len(names):
            with self._lock:
              if self._status['operationId'] == token and self._status['state'] == ACTIVE_STATE:
                self._status['processed'] = max(self._status['processed'], message['processed'])
          elif message.get('kind') == 'result' and type(message.get('report')) is dict:
            result = message['report']
          elif message.get('kind') == 'error' and message.get('code') in (
            'unavailable', 'process_failed', 'recording_unavailable', 'decode_failed', 'resource_limit',
          ):
            error = message['code']
          else:
            return None, 'process_failed'
          if error is not None:
            break
    if error is not None:
      return None, error
    if buffer or child.wait(timeout=0.5) != 0 or result is None:
      return None, 'process_failed'
    return result, None

  def report(self, operation_id: str) -> dict:
    self._revoke_if_unparked()
    with self._lock:
      if self._closed:
        raise FlmOperationError('unavailable')
      if self._status['operationId'] != operation_id:
        raise FlmOperationError('operation_changed')
      if self._status['state'] != 'completed' or self._report is None:
        raise FlmOperationError(self._status['errorCode'] or 'unavailable')
      return json.loads(json.dumps(self._report, allow_nan=False))

  def cancel(self, operation_id: str) -> dict:
    self._revoke_if_unparked()
    with self._lock:
      if self._status['operationId'] != operation_id:
        raise FlmOperationError('operation_changed')
      if self._status['state'] != ACTIVE_STATE:
        return dict(self._status)
      self._cancel.set()
      thread = self._monitor_thread
    if thread is not None:
      thread.join(timeout=1.5)
      if thread.is_alive():
        with self._lock:
          child = self._child
        if child is not None:
          _stop_child(child)
        thread.join(timeout=0.5)
    return self.snapshot()

  def close(self) -> None:
    with self._lock:
      self._closed = True
      self._cancel.set()
      thread = self._monitor_thread
    if thread is not None:
      thread.join(timeout=1.5)
    with self._lock:
      child = self._child
    if child is not None:
      _stop_child(child)
    with self._lock:
      self._report = None
      if self._status['state'] != 'idle':
        self._status = self._fresh_status('unavailable', self._status['operationId'],
                                          self._status['selected'], self._status['processed'], 'unavailable')
