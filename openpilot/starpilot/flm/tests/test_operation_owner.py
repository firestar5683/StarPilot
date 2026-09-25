"""One isolated FLM operation never publishes a partial or unparked report."""

from pathlib import Path
import json
import subprocess
import sys
import threading
import time
from unittest import mock

import pytest
import zstandard as zstd

from openpilot.cereal import messaging
from openpilot.starpilot.flm.operation_owner import FlmAnalysisOwner, FlmOperationError


SEGMENT = '1234abcd--0123456789--0'


def recording(tmp_path: Path, *, valid: bool = True) -> Path:
  root = tmp_path.resolve()
  folder = root / SEGMENT
  folder.mkdir()
  event = messaging.new_message('deviceState', valid=True)
  event.logMonoTime = 1234
  (folder / 'rlog.zst').write_bytes(zstd.ZstdCompressor().compress(event.to_bytes()) if valid else b'bad zstd')
  return root


def terminal(owner: FlmAnalysisOwner) -> dict:
  deadline = time.monotonic() + 5
  while time.monotonic() < deadline:
    state = owner.snapshot()
    if state['state'] != 'running':
      return state
    time.sleep(0.01)
  raise AssertionError('operation did not terminate')


def test_real_local_worker_report_source_identity_and_stale_id(tmp_path):
  owner = FlmAnalysisOwner(root=recording(tmp_path), parked=lambda: True)
  try:
    started = owner.start((SEGMENT,))
    assert started['operationId'].count(':') == 1 and started['selected'] == 1
    assert terminal(owner)['state'] == 'completed'
    report = owner.report(started['operationId'])
    assert report['schemaVersion'] == 1 and report['vehicleQualification'] is False
    assert report['segments'][0]['source']['segmentName'] == SEGMENT
    assert report['segments'][0]['analysis']['status'] == 'missing_car_params'
    report['segments'].clear()
    assert len(owner.report(started['operationId'])['segments']) == 1
    next_run = owner.start((SEGMENT,))
    with pytest.raises(FlmOperationError, match='operation_changed'):
      owner.report(started['operationId'])
    assert terminal(owner)['state'] == 'completed'
    assert owner.report(next_run['operationId'])['operationId'] == next_run['operationId']
  finally:
    owner.close()


def test_request_thread_can_exit_while_monitor_owned_child_completes(tmp_path):
  owner = FlmAnalysisOwner(root=recording(tmp_path), parked=lambda: True)
  replies = []
  request_thread = threading.Thread(target=lambda: replies.append(owner.start((SEGMENT,))))
  try:
    request_thread.start()
    request_thread.join(timeout=2)
    assert not request_thread.is_alive() and len(replies) == 1
    assert terminal(owner)['state'] == 'completed'
    assert owner.report(replies[0]['operationId'])['segments'][0]['analysis']['status'] == 'missing_car_params'
  finally:
    owner.close()


def test_failed_monitor_start_is_unavailable_and_does_not_wedge_future_analysis(tmp_path):
  owner = FlmAnalysisOwner(root=recording(tmp_path), parked=lambda: True)
  try:
    with mock.patch.object(threading.Thread, 'start', side_effect=RuntimeError('thread unavailable')):
      with pytest.raises(FlmOperationError, match='unavailable'):
        owner.start((SEGMENT,))
    assert owner.snapshot()['state'] == 'failed'
    token = owner.start((SEGMENT,))['operationId']
    assert terminal(owner)['state'] == 'completed'
    assert owner.report(token)['operationId'] == token
  finally:
    owner.close()


def test_corrupt_and_symlinked_local_sources_publish_no_report(tmp_path):
  root = recording(tmp_path, valid=False)
  owner = FlmAnalysisOwner(root=root, parked=lambda: True)
  try:
    token = owner.start((SEGMENT,))['operationId']
    assert terminal(owner)['state'] == 'unavailable'
    with pytest.raises(FlmOperationError):
      owner.report(token)
    path = root / SEGMENT / 'rlog.zst'
    path.unlink()
    path.symlink_to(root / 'outside')
    token = owner.start((SEGMENT,))['operationId']
    assert terminal(owner)['state'] == 'unavailable'
    with pytest.raises(FlmOperationError):
      owner.report(token)
  finally:
    owner.close()


def test_cancel_busy_and_onroad_kill_isolated_slow_child(tmp_path):
  root = recording(tmp_path)
  parked = [True]
  slow_worker = (sys.executable, '-c', 'import sys,time;sys.stdin.buffer.read();time.sleep(30)')
  owner = FlmAnalysisOwner(root=root, parked=lambda: parked[0], worker_argv=slow_worker)
  try:
    token = owner.start((SEGMENT,))['operationId']
    with pytest.raises(FlmOperationError, match='busy'):
      owner.start((SEGMENT,))
    assert owner.cancel(token)['state'] == 'canceled'
    token = owner.start((SEGMENT,))['operationId']
    with owner._lock:
      parked[0] = False
      assert owner.snapshot()['state'] == 'unavailable'
      parked[0] = True
      with pytest.raises(FlmOperationError, match='busy'):
        owner.start((SEGMENT,))
    parked[0] = False
    assert terminal(owner)['state'] == 'unavailable'
    with pytest.raises(FlmOperationError):
      owner.report(token)
  finally:
    owner.close()


def test_worker_pipe_eof_while_alive_and_selector_failure_reap(tmp_path):
  root = recording(tmp_path)
  eof_worker = (sys.executable, '-c', 'import os,sys,time;sys.stdin.buffer.read();os.close(1);time.sleep(30)')
  owner = FlmAnalysisOwner(root=root, parked=lambda: True, worker_argv=eof_worker)
  try:
    owner.start((SEGMENT,))
    assert terminal(owner)['state'] == 'failed'
    assert owner._child is None
  finally:
    owner.close()

  class BrokenSelector:
    def __enter__(self):
      return self
    def __exit__(self, *args):
      return False
    def register(self, *_args):
      raise OSError('injected selector failure')

  with mock.patch('openpilot.starpilot.flm.operation_owner.selectors.DefaultSelector', BrokenSelector):
    owner = FlmAnalysisOwner(root=root, parked=lambda: True, worker_argv=eof_worker)
    try:
      owner.start((SEGMENT,))
      assert terminal(owner)['state'] == 'failed'
      assert owner._child is None
    finally:
      owner.close()


def test_close_stops_child_and_revokes_report(tmp_path):
  owner = FlmAnalysisOwner(root=recording(tmp_path), parked=lambda: True)
  token = owner.start((SEGMENT,))['operationId']
  assert terminal(owner)['state'] == 'completed'
  owner.close()
  with pytest.raises(FlmOperationError, match='unavailable'):
    owner.report(token)


def test_worker_rejects_stale_parent_identity_before_any_log_read(tmp_path):
  root = recording(tmp_path)
  child = subprocess.run((sys.executable, '-m', 'openpilot.starpilot.flm.operation_worker'),
                         input=json.dumps({'root': str(root), 'segments': [SEGMENT], 'parentPid': 1}).encode(),
                         capture_output=True, timeout=5, check=False)
  assert child.returncode != 0
  assert b'"kind":"result"' not in child.stdout
  assert b'"code":"process_failed"' in child.stdout


def test_wall_deadline_stops_and_reaps_child(tmp_path):
  worker = (sys.executable, '-c', 'import sys,time;sys.stdin.buffer.read();time.sleep(30)')
  with mock.patch('openpilot.starpilot.flm.operation_owner.WALL_DEADLINE_SECONDS', 0.05):
    owner = FlmAnalysisOwner(root=recording(tmp_path), parked=lambda: True, worker_argv=worker)
    try:
      owner.start((SEGMENT,))
      status = terminal(owner)
      assert status['state'] == 'failed' and status['errorCode'] == 'deadline'
      assert owner._child is None
    finally:
      owner.close()


def test_invalid_selection_and_unparked_start_do_not_spawn(tmp_path):
  owner = FlmAnalysisOwner(root=tmp_path.resolve(), parked=lambda: False)
  try:
    for names in ((), (SEGMENT, SEGMENT), ('../outside',)):
      with pytest.raises(FlmOperationError, match='invalid_request'):
        owner.start(names)
    with pytest.raises(FlmOperationError, match='not_parked'):
      owner.start((SEGMENT,))
    assert owner.snapshot()['state'] == 'idle'
  finally:
    owner.close()
