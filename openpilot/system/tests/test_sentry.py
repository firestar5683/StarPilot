"""Exercise real SDK envelopes and callers without contacting any backend."""
import datetime
import importlib
import hashlib
import json
import multiprocessing
import socket
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from openpilot.system import sentry

FAKE_DSN = "https://test-key@errors.invalid/1"


@pytest.fixture
def reporting(monkeypatch, tmp_path):
  def deny_network(*args, **kwargs):
    raise AssertionError("Crash tests must not contact servers")

  monkeypatch.setattr(socket.socket, 'connect', deny_network)
  monkeypatch.setattr(socket.socket, 'connect_ex', deny_network)
  monkeypatch.setattr(sentry, 'PC', False)
  monkeypatch.setattr(sentry.Paths, 'log_root', lambda: str(tmp_path))
  metadata = SimpleNamespace(canonical='0.0-test-' + 'a' * 40 + '-test', channel='testing', openpilot=SimpleNamespace(version='0.0-test',
                             git_origin='github.com/test/project', git_commit='a' * 40, is_dirty=False))
  monkeypatch.setattr(sentry, 'get_build_metadata', lambda: metadata)
  installed = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
  monkeypatch.setattr(sentry, 'Params', lambda: SimpleNamespace(get=lambda key: {'DongleId': 'test-device',
                            'InstallDate': installed, 'LastUpdateTime': installed}.get(key)))
  monkeypatch.setattr(sentry.HARDWARE, 'get_device_type', lambda: 'test-hardware')
  sdk = sentry._load_sdk()
  transport_module = importlib.import_module('sentry_sdk.transport')
  events, inits = [], []

  class RecordingTransport(transport_module.Transport):
    def capture_envelope(self, envelope):
      events.append(envelope)

  real_init = sdk.init

  def initialize(**kwargs):
    inits.append(kwargs.copy())
    kwargs.update(dsn=FAKE_DSN, transport=RecordingTransport)
    return real_init(**kwargs)

  monkeypatch.setattr(sdk, 'init', initialize)
  monkeypatch.setattr(sentry, 'sdk', None)
  monkeypatch.setattr(sentry, '_initialized_pid', None)
  assert sentry.init()
  events.clear()
  yield SimpleNamespace(sdk=sdk, events=events, inits=inits, real_init=real_init, tmp_path=tmp_path)
  real_init(dsn=None, default_integrations=False, auto_enabling_integrations=False)


def event_list(reporting):
  return [envelope.get_event() for envelope in reporting.events if envelope.get_event() is not None]


def test_manager_init_failure_before_logmessaged_has_structured_stack(reporting, monkeypatch):
  from openpilot.system.manager import manager
  monkeypatch.setattr(manager, 'manager_cleanup', Mock())
  monkeypatch.setattr(manager, 'manager_thread', Mock())
  monkeypatch.setattr(sentry, 'flush', Mock())

  def fail_init():
    raise RuntimeError('manager failure before processes start')

  monkeypatch.setattr(manager, 'manager_init', fail_init)
  with pytest.raises(RuntimeError, match='before processes start'):
    manager.main()
  event, = event_list(reporting)
  value = event['exception']['values'][0]
  assert value['type'] == 'RuntimeError'
  assert any(frame['function'] == 'fail_init' for frame in value['stacktrace']['frames'])
  assert event['tags']['daemon'] == 'manager' and event['tags']['device'] == 'test-hardware'
  assert event['user']['id'] == 'test-device'
  assert event['release'] == '0.0-test-' + 'a' * 40 + '-test' and event['environment'] == 'Testing'
  manager.manager_thread.assert_not_called()
  manager.manager_cleanup.assert_not_called()
  sentry.flush.assert_called_once_with()


@pytest.mark.parametrize('during_import', [True, False])
def test_child_import_and_main_failure_after_real_fork(reporting, monkeypatch, during_import):
  from openpilot.system.manager import process
  parent_pid = sentry._initialized_pid
  ctx = multiprocessing.get_context('fork')
  reader, writer = ctx.Pipe(duplex=False)
  original_capture = reporting.sdk.capture_exception

  def capture(*args, **kwargs):
    original_capture(*args, **kwargs)
    writer.send((sentry._initialized_pid, event_list(reporting)))

  monkeypatch.setattr(reporting.sdk, 'capture_exception', capture)
  monkeypatch.setattr(process.messaging, 'reset_context', Mock())
  monkeypatch.setattr(process, 'setproctitle', Mock())
  monkeypatch.setattr(sentry, 'flush', Mock())

  def fail_main():
    raise RuntimeError('child main failed')

  def import_child(name):
    assert sentry._initialized_pid != parent_pid
    if during_import:
      raise ImportError('child module import failed')
    return SimpleNamespace(main=fail_main)

  real_import = process.importlib.import_module
  monkeypatch.setattr(process.importlib, 'import_module', lambda name: import_child(name) if name == 'test.child' else real_import(name))
  child = ctx.Process(target=process.launcher, args=('test.child', 'test-child'))
  child.start()
  try:
    assert reader.poll(5), 'child did not capture failure'
    pid, events = reader.recv()
    child.join(5)
    assert not child.is_alive() and child.exitcode != 0
    assert pid == child.pid and pid != parent_pid
    event, = events
    assert event['exception']['values'][0]['type'] == ('ImportError' if during_import else 'RuntimeError')
    assert event['tags']['daemon'] == 'test-child'
    assert event['exception']['values'][0]['stacktrace']['frames']
  finally:
    if child.is_alive():
      child.terminate()
      child.join(2)
    reader.close()
    writer.close()


def test_uncaught_background_thread_captured_once(reporting, monkeypatch):
  monkeypatch.setattr(threading, 'excepthook', lambda args: None)

  def fail_thread():
    raise ValueError('uncaught thread')

  thread = threading.Thread(target=fail_thread)
  thread.start()
  thread.join(2)
  assert not thread.is_alive()
  event, = event_list(reporting)
  value = event['exception']['values'][0]
  assert value['type'] == 'ValueError' and value['mechanism']['type'] == 'threading'
  assert any(frame['function'] == 'fail_thread' for frame in value['stacktrace']['frames'])


def test_explicit_exception_and_cloudlog_exactly_once_without_flush(reporting, monkeypatch):
  monkeypatch.setattr(reporting.sdk, 'flush', Mock())
  try:
    raise LookupError('ordinary explicit crash')
  except LookupError:
    sentry.cloudlog.exception('crash')
    sentry.capture_exception()
  event, = event_list(reporting)
  assert event['exception']['values'][0]['type'] == 'LookupError'
  assert (reporting.tmp_path / 'crash/error.txt').read_text().endswith('LookupError: ordinary explicit crash')
  assert 'logging' not in reporting.sdk.get_client().integrations
  reporting.sdk.flush.assert_not_called()


@pytest.mark.parametrize('qlog_name', ['qlog.zst', 'qlog.bz2', 'qlog'])
@pytest.mark.parametrize('report_available', [True, False])
def test_native_apport_keeps_local_copy_and_queues_header_stack_qlog(reporting, monkeypatch, qlog_name, report_available):
  from openpilot.system import tombstoned
  source = reporting.tmp_path / 'native.crash'
  payload = 'ExecutablePath: /data/openpilot/native/daemon\nSignal: 11\nCoreDump: PRIVATE-CORE-PAYLOAD\n'
  source.write_text(payload)
  qlog = reporting.tmp_path / 'route' / qlog_name
  qlog.parent.mkdir()
  qlog.write_bytes(b'test-qlog')
  monkeypatch.setattr(tombstoned, 'get_apport_stacktrace', lambda fn: '#0\n#1 native_func() at openpilot/selfdrive/native.cc:1\n')
  monkeypatch.setattr(tombstoned, 'get_build_metadata', sentry.get_build_metadata)
  if not report_available:
    monkeypatch.setattr(sentry, 'sdk', None)
  tombstoned.report_tombstone_apport(str(source))
  assert not source.exists()
  copies = list((reporting.tmp_path / 'crash').iterdir())
  assert len(copies) == 1 and copies[0].read_text() == payload
  if not report_available:
    assert event_list(reporting) == []
    return
  envelope, = [envelope for envelope in reporting.events if envelope.get_event() is not None]
  event = envelope.get_event()
  assert 'native_func' in event['message'] and 'Signal: 11' in event['extra']['tombstone']
  assert 'native_func' in event['extra']['tombstone'] and 'PRIVATE-CORE-PAYLOAD' not in event['extra']['tombstone']
  assert [item.payload.get_bytes() for item in envelope.items if item.headers['type'] == 'attachment'] == [b'test-qlog']


def test_offline_http_does_not_wait_on_capture_and_flush_is_bounded(reporting):
  entered, release, completed = threading.Event(), threading.Event(), threading.Event()
  production_transport = reporting.inits[0]['transport']

  class OfflineTransport(production_transport):
    def _send_request(self, *args, **kwargs):
      entered.set()
      assert release.wait(5)
      raise TimeoutError('simulated offline HTTP')

  reporting.real_init(dsn=FAKE_DSN, default_integrations=False, auto_enabling_integrations=False,
                      transport=OfflineTransport, transport_queue_size=sentry.TRANSPORT_QUEUE_SIZE,
                      enable_backpressure_handling=False, shutdown_timeout=sentry.EXIT_FLUSH_TIMEOUT)
  transport = reporting.sdk.get_client().transport
  assert transport.TIMEOUT == 2 and transport._worker._queue.maxsize == 32
  try:
    sentry.report_tombstone('test', 'first offline event', 'stack')
    assert entered.wait(2)

    def producer():
      for index in range(64):
        sentry.report_tombstone('test', f'offline event {index}', 'stack')
      completed.set()

    thread = threading.Thread(target=producer)
    thread.start()
    assert completed.wait(1), 'producer waited for blocked HTTP'
    thread.join(1)
    assert not release.is_set()
    start = time.monotonic()
    sentry.flush()
    assert time.monotonic() - start < 1, 'exit flush exceeded bound'
  finally:
    release.set()
    transport.flush(2)
    transport.kill()


def test_missing_sdk_isolated_local_exception_preserved(reporting, monkeypatch):
  monkeypatch.setattr(sentry, '_initialized_pid', None)
  monkeypatch.setattr(sentry, '_load_sdk', Mock(side_effect=ImportError('dependency absent')))
  assert sentry.init() is False and sentry.sdk is None
  try:
    raise RuntimeError('original failure')
  except RuntimeError:
    sentry.capture_exception()
  assert 'original failure' in (reporting.tmp_path / 'crash/error.txt').read_text()
  sentry.flush()


def test_disk_failure_still_captures_same_pid_refresh_reuses_client(reporting, monkeypatch):
  monkeypatch.setattr(sentry, 'save_exception', Mock(side_effect=OSError('read-only disk')))
  client = reporting.sdk.get_client()
  assert sentry.init() and reporting.sdk.get_client() is client and len(reporting.inits) == 1
  sentry.capture_exception(RuntimeError('survives disk failure'))
  event, = event_list(reporting)
  assert event['exception']['values'][0]['value'] == 'survives disk failure'


def test_pc_does_not_initialize_sdk(reporting, monkeypatch):
  monkeypatch.setattr(sentry, 'PC', True)
  loader = Mock()
  monkeypatch.setattr(sentry, '_load_sdk', loader)
  assert sentry.init() is False
  loader.assert_not_called()


def test_packaged_sdk_is_complete_and_matches_provenance(reporting):
  root = Path(sentry.BASEDIR) / 'sentry_sdk_repo'
  manifest = json.loads((root / 'source-manifest.json').read_text())
  assert manifest['version'] == '2.38.0' and manifest['license'] == 'MIT'
  assert Path(reporting.sdk.__file__).resolve().is_relative_to(root)
  actual = {path.relative_to(root).as_posix() for path in (root / 'sentry_sdk').rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'}
  assert actual == set(manifest['files'])
  for name, record in manifest['files'].items():
    payload = (root / name).read_bytes()
    assert len(payload) == record['bytes'] and hashlib.sha256(payload).hexdigest() == record['sha256']
  assert 'MIT License' in (root / 'LICENSE').read_text()


def test_metadata_or_attachment_error_does_not_disable_capture(reporting, monkeypatch):
  monkeypatch.setattr(sentry, 'get_build_metadata', Mock(side_effect=OSError('metadata absent')))
  assert sentry.init()
  monkeypatch.setattr(sentry.glob, 'glob', Mock(side_effect=OSError('qlog unavailable')))
  sentry.capture_exception(ValueError('metadata and attachment unavailable'))
  event, = event_list(reporting)
  assert event['exception']['values'][0]['type'] == 'ValueError'
