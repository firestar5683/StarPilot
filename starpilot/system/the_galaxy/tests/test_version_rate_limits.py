"""Offline quota and request-coalescing regressions."""
import importlib.util
import io
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError

import pytest


@pytest.fixture
def history():
  path = Path(__file__).resolve().parents[1] / 'version_history.py'
  spec = importlib.util.spec_from_file_location('version_rate_limits_under_test', path)
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


@pytest.mark.parametrize('transport', ['api', 'raw'])
@pytest.mark.parametrize('headers,deadline', [({'Retry-After': '180'}, 1180),
  ({'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '4600'}, 4600), ({}, 1060)])
def test_full_server_backoff_blocks_all_urls_until_deadline(history, monkeypatch, transport, headers, deadline):
  clock = [1000.0]
  monkeypatch.setattr(history.time, 'time', lambda: clock[0])
  monkeypatch.setattr(history.time, 'monotonic', lambda: clock[0])
  calls = []
  def limited(request, **kwargs):
    calls.append(request.full_url)
    if len(calls) == 1:
      raise HTTPError(request.full_url, 429, 'Limited', headers, io.BytesIO())
    return io.BytesIO(b'{}' if transport == 'api' else b'STARPILOT_DISPLAY_VERSION = "6.7.7"')
  monkeypatch.setattr(history, '_open_url' if transport == 'api' else '_open_raw_url', limited)
  fetch = history._get_json if transport == 'api' else history._get_display_version
  with pytest.raises(history.HistoryUnavailable):
    fetch('https://example.test/first')
  clock[0] = deadline - 1
  with pytest.raises(history.HistoryUnavailable):
    fetch('https://example.test/second')
  assert len(calls) == 1
  clock[0] = deadline
  fetch('https://example.test/second')
  assert len(calls) == 2


@pytest.mark.parametrize('transport', ['api', 'raw'])
def test_concurrent_identical_cache_misses_download_once(history, monkeypatch, transport):
  start = threading.Barrier(3)
  entered, duplicate, release = threading.Event(), threading.Event(), threading.Event()
  calls = []
  def response(*args, **kwargs):
    calls.append(1)
    entered.set()
    if len(calls) > 1:
      duplicate.set()
    assert release.wait(timeout=0.8)
    return {} if transport == 'api' else '6.7.7'
  monkeypatch.setattr(history, '_get_json' if transport == 'api' else '_get_display_version', response)
  def caller():
    start.wait(timeout=0.8)
    if transport == 'api':
      return history._json('https://api.github.com/repos/a/b/commits')
    return history._display_version('https://api.github.com/repos/a/b', 'a' * 40)
  with ThreadPoolExecutor(max_workers=2) as executor:
    futures = [executor.submit(caller) for _ in range(2)]
    start.wait(timeout=0.8)
    try:
      assert entered.wait(timeout=0.8)
      duplicate.wait(timeout=0.1)
    finally:
      release.set()
    assert futures[0].result(timeout=0.8) == futures[1].result(timeout=0.8)
  assert len(calls) == 1


def test_raw_quota_does_not_block_api_or_cached_raw(history, monkeypatch):
  base, sha = 'https://api.github.com/repos/a/b', 'a' * 40
  monkeypatch.setattr(history, '_open_raw_url', lambda *a, **kw: io.BytesIO(b'STARPILOT_DISPLAY_VERSION = "6.7.7"'))
  assert history._display_version(base, sha) == '6.7.7'
  def limited(request, **kwargs):
    raise HTTPError(request.full_url, 429, 'Limited', {'Retry-After': '180'}, io.BytesIO())
  monkeypatch.setattr(history, '_open_raw_url', limited)
  with pytest.raises(history.HistoryUnavailable):
    history._display_version(base, 'b' * 40)
  assert history._display_version(base, sha) == '6.7.7'
  monkeypatch.setattr(history, '_open_url', lambda *a, **kw: io.BytesIO(b'{}'))
  assert history._get_json(base) == {}


def test_fresh_api_calls_do_not_reuse_cached_head(history, monkeypatch):
  calls = []
  def response(url):
    calls.append(url)
    return {'call': len(calls)}
  monkeypatch.setattr(history, '_get_json', response)
  assert history._json('head') == {'call': 1}
  assert history._json('head', fresh=True) == {'call': 2}
  assert history._json('head', fresh=True) == {'call': 3}


def test_later_shorter_raw_response_cannot_shorten_active_backoff(history, monkeypatch):
  clock = [1000.0]
  monkeypatch.setattr(history.time, 'time', lambda: clock[0])
  monkeypatch.setattr(history.time, 'monotonic', lambda: clock[0])
  started, long_finished = threading.Barrier(2), threading.Event()
  calls = []
  def limited(request, **kwargs):
    calls.append(request.full_url)
    started.wait(timeout=0.8)
    if request.full_url.endswith('short'):
      assert long_finished.wait(timeout=0.8)
    wait = '180' if request.full_url.endswith('long') else '60'
    raise HTTPError(request.full_url, 429, 'Limited', {'Retry-After': wait}, io.BytesIO())
  monkeypatch.setattr(history, '_open_raw_url', limited)
  def caller(suffix):
    with pytest.raises(history.HistoryUnavailable):
      history._get_display_version('https://raw.githubusercontent.com/' + suffix)
    if suffix == 'long':
      long_finished.set()
  with ThreadPoolExecutor(max_workers=2) as executor:
    futures = [executor.submit(caller, suffix) for suffix in ['long', 'short']]
    for future in futures:
      future.result(timeout=0.8)
  clock[0] = 1179
  with pytest.raises(history.HistoryUnavailable):
    history._get_display_version('https://raw.githubusercontent.com/third')
  assert len(calls) == 2


def test_raw_worker_waiting_for_slot_observes_new_quota(history, monkeypatch):
  entered, queued, release = threading.Event(), threading.Event(), threading.Event()
  slots, gate_lock = threading.Semaphore(1), threading.Lock()
  counts = {'attempts': 0, 'http': 0}
  class Gate:
    def __enter__(self):
      with gate_lock:
        counts['attempts'] += 1
        if counts['attempts'] == 2:
          queued.set()
      assert slots.acquire(timeout=0.8)
    def __exit__(self, *args):
      slots.release()
  monkeypatch.setattr(history, '_version_slots', Gate())
  def limited(request, **kwargs):
    counts['http'] += 1
    entered.set()
    assert release.wait(timeout=0.8)
    raise HTTPError(request.full_url, 429, 'Limited', {'Retry-After': '180'}, io.BytesIO())
  monkeypatch.setattr(history, '_open_raw_url', limited)
  with ThreadPoolExecutor(max_workers=2) as executor:
    first = executor.submit(history._display_version, 'https://api.github.com/repos/a/b', 'a' * 40)
    assert entered.wait(timeout=0.8)
    second = executor.submit(history._display_version, 'https://api.github.com/repos/a/b', 'b' * 40)
    try:
      assert queued.wait(timeout=0.8)
    finally:
      release.set()
    for future in (first, second):
      with pytest.raises(history.HistoryUnavailable):
        future.result(timeout=0.8)
  assert counts['http'] == 1


def test_distinct_api_requests_serialize_and_observe_first_quota(history, monkeypatch):
  start = threading.Barrier(3)
  entered, duplicate, release = threading.Event(), threading.Event(), threading.Event()
  calls = []
  def limited(request, **kwargs):
    calls.append(request.full_url)
    entered.set()
    if len(calls) > 1:
      duplicate.set()
    assert release.wait(timeout=0.8)
    raise HTTPError(request.full_url, 429, 'Limited', {'Retry-After': '180'}, io.BytesIO())
  monkeypatch.setattr(history, '_open_url', limited)
  def caller(suffix):
    start.wait(timeout=0.8)
    return history._get_json('https://api.github.com/repos/a/b/' + suffix)
  with ThreadPoolExecutor(max_workers=2) as executor:
    futures = [executor.submit(caller, suffix) for suffix in ['branches/main', 'commits']]
    start.wait(timeout=0.8)
    try:
      assert entered.wait(timeout=0.8)
      duplicate.wait(timeout=0.1)
    finally:
      release.set()
    for future in futures:
      with pytest.raises(history.HistoryUnavailable):
        future.result(timeout=0.8)
  assert len(calls) == 1
