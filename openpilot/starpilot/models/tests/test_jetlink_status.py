"""Jetlink's home icon and Android Auto card read one status, off the drawing thread, never keeping stale latency."""
import json
import threading
import time
from types import SimpleNamespace as NS
from unittest.mock import patch

import pytest
from jetlink.openpilot import Status

from openpilot.starpilot.models import jetlink_adapter as adapter, jetlink_status
from openpilot.starpilot.models.jetlink_status import JetlinkStatus, JetlinkStatusFeed, read_status


def status(**kw):
  return Status(enabled=True, mode='usb', transport='USB', present=True, port='host', ready=False,
                reason=None, progress=None, model='remote', default_model='remote')._replace(**kw)


def read(value, latency=24.6, failed=False):
  with patch.object(adapter, 'link_on', return_value=True), \
       patch.object(adapter, 'hooks', return_value=NS(status=lambda: value)), \
       patch.object(jetlink_status, 'read_latency', return_value=latency), \
       patch.object(jetlink_status, 'join_failed', return_value=failed):
    return read_status()


def test_off_reads_nothing_of_jetlink():
  with patch.object(adapter, 'link_on', return_value=False), patch.object(adapter, 'hooks') as hooks:
    assert read_status() == JetlinkStatus()
    hooks.assert_not_called()


@pytest.mark.parametrize('kw,expected', [
  ({'active': True, 'running': 'running'}, JetlinkStatus('USB host', 'active', 24.6, 'connected')),
  ({'running': 'ready'}, JetlinkStatus('USB host', 'waiting', port='connected')),
  ({'running': 'joining'}, JetlinkStatus('USB host', 'connecting', port='connected')),
  ({'running': 'retrying'}, JetlinkStatus('USB host', 'reconnecting', port='connected')),
  ({'running': None}, JetlinkStatus('USB host', 'preparing', port='connected')),
  ({'ready': True}, JetlinkStatus('USB host', 'prepared', port='connected')),
  ({'reason': 'service stopped'}, JetlinkStatus('USB host', 'unavailable', port='connected')),
  ({'present': False}, JetlinkStatus('USB host', 'detected', port='device')),
  ({'present': False, 'port': 'empty'}, JetlinkStatus('USB host', 'disconnected')),
  ({'present': True, 'port': 'empty', 'active': True}, JetlinkStatus('USB host', 'disconnected')),
  ({'present': False, 'port': None}, JetlinkStatus('USB host', 'disconnected')),
  ({'mode': 'ios', 'active': True}, JetlinkStatus('Mobile device (iOS)', 'active', 24.6, 'connected')),
  ({'enabled': False, 'active': True}, JetlinkStatus('USB host', 'unavailable')),
])
def test_states(kw, expected):
  assert read(status(**kw)) == expected


def test_failed_join_reads_failed_not_prepared():
  assert read(status(ready=True), failed=True) == JetlinkStatus('USB host', 'failed', port='connected')
  # a live join's record decides over a stale failure
  assert read(status(ready=True, running='joining'), failed=True) == JetlinkStatus('USB host', 'connecting', port='connected')


def test_join_record_round_trip(tmp_path):
  path = str(tmp_path / 'jetlink' / 'join.json')
  assert not jetlink_status.join_failed(path)
  jetlink_status.write_join(False, path)
  assert jetlink_status.join_failed(path)
  jetlink_status.write_join(True, path)
  assert not jetlink_status.join_failed(path)
  with open(path, 'w') as f:
    json.dump({'pid': 2 ** 22 + 12345, 'joined': False}, f)  # a modeld that is gone
  assert not jetlink_status.join_failed(path)


def test_no_usable_jetlink_is_unavailable():
  assert read(None) == JetlinkStatus(state='unavailable')


def test_latency_record_round_trip_and_staleness(tmp_path):
  path = str(tmp_path / 'jetlink' / 'latency.json')
  jetlink_status._write_latency(NS(client=NS(last_timings=(1, 2, 24600))), path)
  assert jetlink_status.read_latency(path) == pytest.approx(24.6)
  jetlink_status._write_latency(NS(client=None), path)  # the small model drives
  assert jetlink_status.read_latency(path) is None
  with open(path, 'w') as f:
    json.dump({'at': time.monotonic() - jetlink_status.LATENCY_FRESH_S - 1, 'server_ms': 24.6}, f)
  assert jetlink_status.read_latency(path) is None
  assert jetlink_status.read_latency(str(tmp_path / 'missing.json')) is None


def test_feed_polls_off_thread_expires_and_disables():
  arrived = threading.Event()
  threads = []
  def fake():
    threads.append(threading.get_ident())
    arrived.set()
    return JetlinkStatus('iPhone', 'active', 24.6, 'connected')
  feed = JetlinkStatusFeed(read=fake, period=0.01)
  try:
    assert feed.snapshot() == JetlinkStatus()
    feed.set_enabled(True)
    assert arrived.wait(2)
    assert threading.get_ident() not in threads
    assert feed.snapshot().latency_ms == 24.6
    feed.set_enabled(False)
    assert feed.snapshot() == JetlinkStatus()
  finally:
    feed.close()


def test_feed_stale_and_failed_reads_drop_latency_and_port():
  feed = JetlinkStatusFeed(read=lambda: JetlinkStatus('iPhone', 'active', 24.6, 'connected'))
  feed._enabled = True
  feed.poll()
  assert feed.snapshot().port == 'connected'
  feed._read_at = 0
  assert feed.snapshot() == JetlinkStatus('iPhone', 'unavailable')
  feed.read = lambda: 1 / 0
  feed.poll()
  assert feed.snapshot() == JetlinkStatus(state='unavailable')


@pytest.mark.parametrize('stage', ['download', 'upload', 'compile', 'load', 'warm'])
def test_preparation_progress_survives_snapshot(stage):
  result = read(status(running='joining', progress={'stage': stage, 'frac': 0.42}))
  assert result.stage == stage
  assert result.percent == (42 if stage in ('download', 'upload') else None)


@pytest.mark.parametrize('why, drops, stage', [
  ('lost', 0, 'reconnect_lost'), ('lost', 2, 'reconnect_cable'), ('behind', 0, 'reconnect_behind'),
  ('load_failed', 0, 'reconnect_load_failed'), ('bad_output', 0, 'reconnect_bad_output'), ('other', 0, ''), (None, 0, ''),
])
def test_reconnect_reason_is_read_from_the_progress_record(why, drops, stage):
  progress = {'stage': 'connect', 'frac': 0.0, 'drops': drops, 'code': 'reconnecting', 'args': {'why': why}}
  assert read(status(running='retrying', progress=progress)).stage == stage


@pytest.mark.parametrize('kw', [
  {'active': True, 'running': 'running'}, {'running': 'ready'}, {'running': 'retrying'},
  {'present': False}, {'port': 'empty'}, {'reason': 'service stopped'},
])
def test_live_state_overrides_old_progress(kw):
  result = read(status(progress={'stage': 'warm', 'frac': 0.9}, **kw))
  assert result.stage == ''
  assert result.percent is None


@pytest.mark.parametrize('frac', [None, True, '0.5', float('nan'), float('inf'), -1, 2])
def test_invalid_transfer_fraction_is_not_displayed(frac):
  result = read(status(progress={'stage': 'upload', 'frac': frac}))
  assert result.stage == 'upload'
  assert result.percent is None


def test_progress_code_and_unknown_stage():
  result = read(status(progress={'stage': 'connect', 'code': 'model_missing'}))
  assert result.stage == 'model_missing'
  assert read(status(progress={'stage': 'future_stage'})).stage == ''
