"""Real storage cleanup keeps collection and unrelated files intact."""
import json
import os

import pytest

from openpilot.starpilot.galaxy.crash_reports import CrashChanged, CrashMissing, CrashReports, CrashUnavailable
from openpilot.starpilot.galaxy.sentry_events import SentryEvents
from openpilot.starpilot.sentry_mode.notifications import NotificationOwner
from openpilot.starpilot.sentry_mode.storage import EventStore, StorageUnavailable


def test_event_metadata_images_temporary_and_idempotence(tmp_path):
  store = EventStore(tmp_path / 'events')
  receipt = store.record('alarm', 1, permitted=lambda: True, images={'wide': b'\xff\xd8abc\xff\xd9', 'cabin': b'\xff\xd8xyz\xff\xd9'})
  other = store.record('warning', 2, permitted=lambda: True)
  (store.root / ('.' + receipt.event_id + '.tmp')).write_text('interrupted')
  os.chmod(store.root / ('.' + receipt.event_id + '.tmp'), 0o600)
  before = SentryEvents(store).snapshot()['storageBytes']
  result = SentryEvents(store).delete(receipt.event_id)
  assert not (store.root / receipt.event_id).exists()
  assert not (store.root / (receipt.event_id + '.json')).exists()
  assert not (store.root / ('.' + receipt.event_id + '.tmp')).exists()
  assert [event['eventId'] for event in result['events']] == [other.event_id]
  assert 0 < result['storageBytes'] < before
  assert SentryEvents(store).delete(receipt.event_id)['events'] == result['events']
  assert (store.root / '.lock').exists()
  fresh = store.record('selfie', 3, permitted=lambda: True)
  assert fresh.event_id in {event['eventId'] for event in EventStore(store.root).snapshot()['events']}


def test_event_corrupt_orphans_and_external_symlinks(tmp_path):
  store = EventStore(tmp_path / 'events')
  receipt = store.record('warning', 1, permitted=lambda: True)
  (store.root / (receipt.event_id + '.json')).write_bytes(b'{broken')
  outside = tmp_path / 'outside'
  outside.write_text('keep')
  (store.root / receipt.event_id).symlink_to(outside)
  orphan = store.root / ('b' * 32)
  orphan.mkdir(mode=0o700)
  (orphan / 'wide.jpg').write_bytes(b'corrupt')
  result = SentryEvents(store).delete()
  assert result['events'] == [] and result['storageBytes'] == 0 and not result['more']
  assert outside.read_text() == 'keep'
  assert list(store.root.iterdir()) == [store.root / '.lock']
  assert SentryEvents(EventStore(store.root)).snapshot()['events'] == []
  for invalid in ('../outside', 'a' * 31, 'A' * 32, 'a' * 32 + '/x'):
    with pytest.raises(ValueError):
      store.delete(invalid)
  assert outside.exists()
  redirect = tmp_path / 'redirect'
  redirect.symlink_to(tmp_path, target_is_directory=True)
  with pytest.raises(StorageUnavailable):
    EventStore(redirect).delete()


def test_bounded_delete_all_continues_and_missing_root(tmp_path):
  store = EventStore(tmp_path / 'events')
  assert SentryEvents(store).delete()['events'] == []
  store.record('alarm', 1, permitted=lambda: True)
  for index in range(4100):
    (store.root / f'corrupt-{index}').touch(mode=0o600)
  assert store.delete()['more']
  assert not store.delete()['more']
  assert store.snapshot()['storageBytes'] == 0
  assert store.record('warning', 2, permitted=lambda: True).durable
  with pytest.raises(PermissionError):
    store.delete(permitted=lambda: False)


def test_crash_real_flat_reports_corrupt_logs_and_collection_after_delete(tmp_path):
  directory = tmp_path / 'crash'
  directory.mkdir()
  report = directory / '2026-10-14.log'
  report.write_bytes(b'corrupt\xfftrace')
  (directory / 'error.txt').write_text('latest summary')
  reader = CrashReports(directory)
  original = reader.list()
  token = next(item['id'] for item in original['reports'] if item['name'] == report.name)
  result = reader.delete(token)
  assert not report.exists()
  assert result['reportCount'] == 1 and result['storageBytes'] == len('latest summary')
  assert reader.delete(token)['reportCount'] == 1
  assert not reader.delete()['reports']
  assert reader.list()['storageBytes'] == 0
  (directory / 'new-native-crash').write_text('new collection')
  assert CrashReports(directory).list()['reportCount'] == 1


def test_crash_changed_tokens_and_no_symlink_escape(tmp_path):
  directory = tmp_path / 'crash'
  directory.mkdir()
  report = directory / 'report'
  report.write_text('old')
  reader = CrashReports(directory)
  token = reader.list()['reports'][0]['id']
  report.write_text('new-longer')
  with pytest.raises(CrashChanged):
    reader.delete(token)
  assert report.read_text() == 'new-longer'
  outside = tmp_path / 'external'
  outside.write_text('keep')
  (directory / 'link').symlink_to(outside)
  assert reader.delete()['reports'] == []
  assert outside.read_text() == 'keep'
  for token in ('../external', 'bad', 'x' * 5000):
    with pytest.raises(CrashMissing):
      reader.delete(token)
  absent = CrashReports(tmp_path / 'missing')
  assert absent.delete()['reports'] == []
  linked = tmp_path / 'linked-root'
  linked.symlink_to(tmp_path, target_is_directory=True)
  with pytest.raises(CrashUnavailable):
    CrashReports(linked).delete()


def test_notification_jobs_removed_durably_without_preferences_loss(tmp_path):
  now = [9]
  store = EventStore(tmp_path / 'events')
  receipt = store.record('alarm', 1, permitted=lambda: True)
  owner = NotificationOwner(tmp_path / 'notifications', store=store, clock=lambda: now[0])
  try:
    owner.action({'action': 'configure', 'channel': 'ntfy', 'enabled': True, 'url': 'https://ntfy.sh/test-topic', 'token': ''})
    now[0] = 10
    owner._enqueue({'eventId': receipt.event_id, 'kind': 'alarm', 'wallTimeNs': 10_000_000_000})
    owner._save()
    original_channels = json.loads(json.dumps(owner.state['channels']))
    assert owner.state['jobs']
    owner.delete_events(lambda: store.delete(receipt.event_id), receipt.event_id)
    assert owner.state['jobs'] == {} and owner.state['channels'] == original_channels
  finally:
    owner.close()
  reopened = NotificationOwner(tmp_path / 'notifications', store=store, clock=lambda: now[0])
  try:
    assert reopened.state['jobs'] == {} and reopened.state['channels'] == original_channels
    fresh = store.record('warning', 2, permitted=lambda: True)
    reopened._enqueue({'eventId': fresh.event_id, 'kind': 'warning', 'wallTimeNs': 10_000_000_000})
    assert {job['eventId'] for job in reopened.state['jobs'].values()} == {fresh.event_id}
  finally:
    reopened.close()


def test_notification_inflight_delete_does_not_resurrect_jobs(tmp_path):
  now = [9]
  store = EventStore(tmp_path / 'events')
  receipt = store.record('alarm', 1, permitted=lambda: True)
  sent = []
  owner: NotificationOwner

  def transport(_channel, _config, _subscription, job, _key, _pem):
    sent.append(job['eventId'])
    owner.delete_events(lambda: store.delete())
    return 200

  owner = NotificationOwner(tmp_path / 'notifications', store=store, clock=lambda: now[0], transport=transport)
  try:
    owner.action({'action': 'configure', 'channel': 'ntfy', 'enabled': True, 'url': 'https://ntfy.sh/test-topic', 'token': ''})
    now[0] = 10
    owner._enqueue({'eventId': receipt.event_id, 'kind': 'alarm', 'wallTimeNs': 10_000_000_000})
    owner.tick()
    assert sent == [receipt.event_id]
    assert owner.state['jobs'] == {} and owner.available
    assert json.loads((owner.root / 'state.json').read_text())['jobs'] == {}
  finally:
    owner.close()


def test_actual_python_crash_collection_summary_and_future_collection(tmp_path, monkeypatch):
  from openpilot.common.hardware.hw import Paths
  from openpilot.system.sentry import save_exception
  monkeypatch.setattr(Paths, 'log_root', lambda: str(tmp_path))
  save_exception('old trace\nold end')
  reader = CrashReports(tmp_path / 'crash')
  old = next(item for item in reader.list()['reports'] if item['name'].endswith('.log'))
  save_exception('new trace\nnew end')
  current = next(item for item in reader.list()['reports'] if item['name'].endswith('.log') and item['id'] != old['id'])
  reader.delete(old['id'])
  assert (reader.directory / 'error.txt').read_text() == 'new trace\nnew end'
  assert reader.delete(current['id'])['reports'] == []
  assert reader.list()['storageBytes'] == 0
  save_exception('future trace')
  assert reader.list()['reportCount'] == 2
  assert (reader.directory / 'error.txt').read_text() == 'future trace'


def test_notification_failed_prune_keeps_event_and_persisted_jobs(tmp_path, monkeypatch):
  now = [9]
  store = EventStore(tmp_path / 'events')
  receipt = store.record('alarm', 1, permitted=lambda: True)
  sent = []
  owner = NotificationOwner(tmp_path / 'notifications', store=store, clock=lambda: now[0], transport=lambda *args: sent.append(args))
  try:
    owner.action({'action': 'configure', 'channel': 'ntfy', 'enabled': True, 'url': 'https://ntfy.sh/test-topic', 'token': ''})
    now[0] = 10
    owner._enqueue({'eventId': receipt.event_id, 'kind': 'alarm', 'wallTimeNs': 10_000_000_000})
    owner._save()
    jobs = json.loads(json.dumps(owner.state['jobs']))
    assert jobs
    def fail_save():
      raise OSError('injected persistence failure')
    monkeypatch.setattr(owner, '_save', fail_save)
    removed = []
    with pytest.raises(OSError):
      owner.delete_events(lambda: removed.append(store.delete(receipt.event_id)), receipt.event_id)
    assert removed == [] and sent == []
    assert owner.state['jobs'] == jobs
    assert (store.root / (receipt.event_id + '.json')).exists()
  finally:
    owner.close()
  reopened = NotificationOwner(tmp_path / 'notifications', store=store, clock=lambda: now[0])
  try:
    assert reopened.state['jobs'] == jobs
    def remove():
      assert json.loads((reopened.root / 'state.json').read_text())['jobs'] == {}
      return store.delete(receipt.event_id)
    reopened.delete_events(remove, receipt.event_id)
    assert reopened.state['jobs'] == {}
  finally:
    reopened.close()
