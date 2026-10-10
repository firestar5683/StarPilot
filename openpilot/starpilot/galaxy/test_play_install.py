import hashlib
import io
import time
from unittest.mock import Mock

import pytest

from openpilot.starpilot.galaxy.play_install import Paused, PlayInstall, checked_url, download


def wait(job):
  job.thread.join(timeout=3)
  assert not job.thread.is_alive()


@pytest.fixture
def provision(tmp_path):
  helper = b'\x7fELF\x02' + bytes(13) + (183).to_bytes(2, 'little')
  contents = {'resolver': helper}
  manifest = {'id': 'release-1', 'resolver': {'sha256': hashlib.sha256(helper).hexdigest(), 'bytes': len(helper), 'url': 'resolver'}}
  state = {'ready': False, 'parked': True}
  calls = []
  def fetch(asset, destination, check, progress):
    calls.append(asset['url'])
    check()
    destination.write_bytes(contents[asset['url']])
    progress(asset['bytes'])
  job = PlayInstall(ready=lambda: state['ready'], parked=lambda: state['parked'], destination=tmp_path / 'installed' / 'release-1',
                       package=manifest, enabled=True, fetch=fetch)
  yield job, state, calls
  job.close()


def test_waits_for_setup_then_installs_once(provision):
  job, state, calls = provision
  job.maintain()
  assert job.thread is None and not calls
  abandoned = job.destination.parent / '.download-interrupted'
  abandoned.mkdir(parents=True)
  (abandoned / 'partial').write_bytes(b'interrupted download')
  state['ready'] = True
  job.maintain()
  wait(job)
  assert job.status() == {'state': 'ready', 'percent': 100}
  assert job.installed()
  assert calls == ['resolver']
  assert not list(job.destination.parent.glob('.download-*'))
  job.maintain()
  assert calls == ['resolver']
  restarted = PlayInstall(ready=lambda: False, parked=lambda: False, destination=job.destination,
                             package=job.package, enabled=True, fetch=Mock(side_effect=AssertionError))
  restarted.maintain()
  assert restarted.status()['state'] == 'ready'


def test_local_setup_marker_survives_restart(provision):
  job, _, calls = provision
  job.mark_setup_complete()
  job.maintain()
  wait(job)
  assert job.installed() and calls


def test_park_admission_and_cancellation_leave_no_partial_install(provision):
  job, state, calls = provision
  state.update(ready=True, parked=False)
  job.maintain()
  assert job.status()['state'] == 'paused' and not calls
  state['parked'] = True
  original = job.fetch
  def move(asset, destination, check, progress):
    original(asset, destination, check, progress)
    state['parked'] = False
  job.fetch = move
  job.maintain()
  wait(job)
  assert job.status()['state'] == 'paused'
  assert not job.destination.exists()
  assert not list(job.destination.parent.glob('.download-*'))


def test_failed_download_backs_off_and_preserves_older_release(provision):
  job, state, calls = provision
  state['ready'] = True
  older = job.destination.parent / 'previous'
  older.mkdir(parents=True)
  (older / 'keep').write_text('old runtime')
  job.fetch = Mock(side_effect=OSError('signed-url-must-not-leak'))
  job.maintain()
  wait(job)
  assert job.status()['state'] == 'retrying'
  assert job.retry_at > time.monotonic()
  job.maintain()
  assert job.fetch.call_count == 1
  assert (older / 'keep').read_text() == 'old runtime'
  assert not job.destination.exists()


@pytest.mark.parametrize('url', ['http://github.com/file', 'https://github.com.evil.test/file',
                               'https://user:password@github.com/file', 'https://example.com/file'])
def test_rejects_untrusted_download_and_redirect_urls(url):
  with pytest.raises(ValueError):
    checked_url(url)


@pytest.mark.parametrize('body,size,digest', [(b'bad', 3, '0'*64), (b'oversize', 2, '0'*64), (b'short', 10, '0'*64)])
def test_download_integrity_failure(tmp_path, monkeypatch, body, size, digest):
  response = io.BytesIO(body)
  response.status = 200
  monkeypatch.setattr('urllib.request.build_opener', lambda *_: Mock(open=Mock(return_value=response)))
  with pytest.raises(ValueError):
    download({'url': 'https://github.com/release/file', 'bytes': size, 'sha256': digest}, tmp_path / 'download', lambda: None, lambda _: None)


def test_download_checks_permission_before_consuming_body(tmp_path, monkeypatch):
  response = io.BytesIO(b'content')
  response.status = 200
  monkeypatch.setattr('urllib.request.build_opener', lambda *_: Mock(open=Mock(return_value=response)))
  def paused():
    raise Paused()
  with pytest.raises(Paused):
    download({'url': 'https://github.com/release/file', 'bytes': 7, 'sha256': '0'*64}, tmp_path / 'download', paused, lambda _: None)


def test_retry_delay_starts_short_and_caps_at_five_minutes(provision):
  job, _, _ = provision
  delays = []
  for _ in range(6):
    before = time.monotonic()
    job._retry_later()
    delays.append(round(job.retry_at - before))
  assert delays == [30, 60, 120, 240, 300, 300]
  assert job.status()['state'] == 'retrying'



def test_rejects_resolver_that_is_not_arm64(provision):
  job, state, _ = provision
  state['ready'] = True
  def fetch(asset, destination, check, progress):
    destination.write_bytes(b'#!/bin/sh\n')
  job.fetch = fetch
  job.maintain()
  wait(job)
  assert job.status()['state'] == 'retrying'
  assert not job.destination.exists()
