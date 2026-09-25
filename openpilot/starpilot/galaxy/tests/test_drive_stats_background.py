"""Device lifecycle analysis continues with no HTTP clients."""
import tempfile
import threading
import time
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from openpilot.starpilot.galaxy.drive_stats import DriveStatsOwner

class BackgroundHistoryTest(TestCase):
  def test_no_browser_pause_resume_and_restart_reuses_completion(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      allowed = threading.Event()
      entered = threading.Event()
      cancelled = threading.Event()
      complete = threading.Event()
      calls = []
      record = dict(routeId='example', startTime=1700000000., endTime=1700000060.,
                    distanceMeters=100., durationSeconds=60., engagedSeconds=20., engagedPercent=100/3,
                    model='test', distractedMoments=0, unresponsiveMoments=0,
                    complete=True, reason=None, segmentCount=1)
      class History:
        def __init__(self): self.root = root
        def snapshot(self): return {'routes': [{'routeId': 'example', 'segments': []}]}
      def analyze(_root, route, *, permitted):
        calls.append(route['routeId'])
        entered.set()
        if len(calls) == 1:
          deadline = time.monotonic() + 2
          while permitted() and time.monotonic() < deadline: time.sleep(.005)
          cancelled.set()
          return dict(record, complete=False, reason='Analysis cancelled')
        complete.set()
        return record
      owner = DriveStatsOwner(root=root, store=root/'cache.json', history=History(),
                              analyzer=analyze, permitted=allowed.is_set)
      try:
        owner.snapshot()
        self.assertIsNone(owner._worker, 'dashboard must only read cached status')
        owner.start()
        owner.start()
        self.assertFalse(entered.wait(.15))
        allowed.set()
        self.assertTrue(entered.wait(2), 'offroad must start without requests')
        allowed.clear()
        self.assertTrue(cancelled.wait(.4), 'onroad must revoke analysis promptly')
        time.sleep(.15)
        self.assertFalse(owner._failures, 'interruption is not a corrupt log')
        self.assertFalse((root/'cache.json').exists() and owner._records)
        allowed.set()
        self.assertTrue(complete.wait(2), 'offroad must resume without requests')
        deadline = time.monotonic() + 2
        while owner._worker.is_alive() and time.monotonic() < deadline: time.sleep(.01)
        self.assertEqual(owner.snapshot()['totals']['drives'], 1)
      finally:
        owner.close()
      restored = DriveStatsOwner(root=root, store=root/'cache.json', history=History(),
                                 analyzer=analyze, permitted=allowed.is_set)
      try:
        restored.start()
        deadline = time.monotonic() + 2
        while restored._worker is None and time.monotonic() < deadline: time.sleep(.01)
        restored._worker.join(2)
        self.assertEqual(calls, ['example', 'example'])
        self.assertEqual(restored.snapshot()['totals']['drives'], 1)
      finally:
        restored.close()
      self.assertFalse(owner._scheduler.is_alive())
      self.assertFalse(restored._scheduler.is_alive())
