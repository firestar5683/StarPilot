import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from openpilot.system.loggerd import uploader
from openpilot.system.athena import athenad
from openpilot.starpilot.software import fast_update


def test_uploader_ignores_unmetered_override():
  instance = uploader.Uploader.__new__(uploader.Uploader)
  instance.params = Mock()
  instance.params.get_bool.return_value = True  # AlwaysAllowUploads
  instance.next_file_to_upload = Mock(side_effect=AssertionError('must not select upload'))
  with patch.object(uploader, 'phone_uplink_active', return_value=True):
    assert instance.step(uploader.NetworkType.wifi, False) is None
    with pytest.raises(uploader.requests.ConnectionError, match='Phone uplink'):
      instance.do_upload('qlog', '/not-read')
  instance.next_file_to_upload.assert_not_called()


def test_athena_allow_cellular_is_still_deferred():
  stop = threading.Event()
  item = athenad.UploadItem(path='/unused', url='https://upload.test', headers={}, created_at=int(athenad.datetime.now().timestamp() * 1000),
                           id='phone-test', allow_cellular=True)
  queue = Mock()
  queue.get.return_value = item
  sm = Mock()
  sm.__getitem__ = Mock(return_value=SimpleNamespace(networkMetered=False, networkType=SimpleNamespace(raw=1)))
  with patch.object(athenad, 'upload_queue', queue), patch.object(athenad.messaging, 'SubMaster', return_value=sm), \
       patch.object(athenad, 'phone_uplink_active', return_value=True), \
       patch.object(athenad, 'retry_upload', side_effect=lambda *_: stop.set()) as retry, \
       patch.object(athenad, '_do_upload') as upload:
    athenad.upload_handler(stop)
    retry.assert_called_once_with(threading.get_ident(), stop, False)
    upload.assert_not_called()
    with pytest.raises(athenad.AbortTransferException):
      athenad.cb(sm, item, 0, stop, 100, 1)


def test_update_fetch_rejected_and_inflight_process_stopped(tmp_path):
  with patch.object(fast_update, 'phone_uplink_active', return_value=True), patch.object(fast_update.subprocess, 'Popen') as spawn:
    with pytest.raises(fast_update.FastUpdateError, match='disabled'):
      fast_update.run(['git', 'fetch'], tmp_path)
    spawn.assert_not_called()
  # Exercise cancellation of a real process when a link changes mid-fetch.
  # Mac disallows killpg(pid, 0) after exit; use a portable child reaper here.
  def reap(process):
    process.terminate()
    process.wait(timeout=2)
  with patch.object(fast_update, 'phone_uplink_active', side_effect=[False, False, True]), \
       patch.object(fast_update, '_stop_process', side_effect=reap) as stop:
    with pytest.raises(fast_update.FastUpdateError, match='stopped'):
      fast_update.run(['python3', '-c', 'import time; time.sleep(20)', 'fetch'], tmp_path, timeout=5)
    stop.assert_called_once()


def test_agnos_stream_never_starts_or_continues_over_phone():
  from openpilot.common.hardware.comma import agnos
  with patch.object(agnos, 'phone_uplink_active', return_value=True), patch.object(agnos.requests, 'get') as request:
    with pytest.raises(agnos.requests.ConnectionError, match='disabled'):
      agnos.StreamingDecompressor('https://example.test/image')
    request.assert_not_called()
    stream = agnos.StreamingDecompressor.__new__(agnos.StreamingDecompressor)
    stream.req = Mock()
    with pytest.raises(agnos.requests.ConnectionError, match='stopped'):
      stream.read(1024)
    stream.req.close.assert_called_once()
