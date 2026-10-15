"""Live metered-upload preferences in the actual Athena worker and callback."""

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import queue
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from openpilot.common.params import Params
from openpilot.system.athena import athenad


class UploadPreferencesTest(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name)
    self.params = Params(str(self.root / 'params'))
    self.file = self.root / 'rlog.zst'
    self.file.write_bytes(b'log')

  def master(self, metered):
    data = SimpleNamespace(networkMetered=metered, networkType=SimpleNamespace(raw=4))
    master = Mock()
    master.__getitem__ = Mock(return_value=data)
    master.recv_time = {'deviceState': 0.}
    return master

  def item(self, allow_cellular=False):
    return athenad.UploadItem(path=str(self.file), url='https://unused.example/upload', headers={},
                              created_at=int(datetime.now().timestamp() * 1000), id='test', allow_cellular=allow_cellular)

  def test_actual_worker_admits_global_override_and_retains_default_policy(self):
    for metered, item_allowed, override, expected in ((True, False, False, False), (True, False, True, True),
                                                    (True, True, False, True), (False, False, False, True)):
      with self.subTest(metered=metered, item_allowed=item_allowed, override=override):
        self.params.put_bool('AlwaysAllowUploads', override, block=True)
        end = threading.Event()
        pending = queue.Queue()
        pending.put(self.item(item_allowed))
        transfer = Mock()

        @contextmanager
        def upload(item, callback, transfer=transfer, end=end):
          transfer(item)
          callback(3, 1)
          yield SimpleNamespace(status_code=201)
          end.set()

        with patch.object(athenad, 'Params', return_value=self.params), \
             patch.object(athenad.messaging, 'SubMaster', return_value=self.master(metered)), \
             patch.object(athenad, 'upload_queue', pending), patch.object(athenad, 'cur_upload_items', {}), \
             patch.object(athenad, 'cancelled_uploads', set()), patch.object(athenad, '_do_upload', side_effect=upload), \
             patch.object(athenad.UploadQueueCache, 'cache'), \
             patch.object(athenad, 'retry_upload', side_effect=lambda *args, stop=end: stop.set()) as retry:
          athenad.upload_handler(end)
          self.assertEqual(transfer.call_count, int(expected))
          self.assertEqual(retry.call_count, int(not expected))

  def test_callback_rechecks_live_override_and_still_aborts_shutdown(self):
    master = self.master(True)
    item, end = self.item(), threading.Event()
    with patch.object(athenad, 'Params', return_value=self.params), patch.object(athenad, 'cur_upload_items', {}):
      self.params.put_bool('AlwaysAllowUploads', True, block=True)
      athenad.cb(master, item, 1, end, 10, 1)
      self.assertEqual(athenad.cur_upload_items[1].progress, .1)
      self.params.put_bool('AlwaysAllowUploads', False, block=True)
      with self.assertRaises(athenad.AbortTransferException):
        athenad.cb(master, item, 1, end, 10, 2)
      self.params.put_bool('AlwaysAllowUploads', True, block=True)
      end.set()
      with self.assertRaises(athenad.AbortTransferException):
        athenad.cb(master, item, 1, end, 10, 2)
