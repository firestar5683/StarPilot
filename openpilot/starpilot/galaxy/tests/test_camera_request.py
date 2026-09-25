from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openpilot.starpilot.galaxy import camera_request


class TestCameraRequest(unittest.TestCase):
  def test_concurrent_latest_expiry_and_finite_lease(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'lease'
      with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda n: camera_request.request(clock=lambda: 100 + n, path=path), range(128)))
      self.assertEqual(int(path.read_text()), 227 + camera_request.TTL_NS)
      self.assertTrue(camera_request.requested(clock=lambda: 228, path=path))
      self.assertFalse(camera_request.requested(clock=lambda: 227 + camera_request.TTL_NS, path=path))
      self.assertFalse(camera_request.requested(clock=lambda: 1, path=path))

  def test_prefix_isolation_and_frame_receipt_aging(self):
    with patch.dict(os.environ, OPENPILOT_PREFIX='camera-a'):
      first = camera_request._path('lease')
    with patch.dict(os.environ, OPENPILOT_PREFIX='camera-b'):
      self.assertNotEqual(first, camera_request._path('lease'))
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'frame'
      camera_request.mark_frame(clock=lambda: 100, path=path)
      self.assertTrue(camera_request.frame_available(clock=lambda: 101, path=path))
      self.assertFalse(camera_request.frame_available(clock=lambda: 101 + camera_request.FRAME_TTL_NS, path=path))
      self.assertFalse(camera_request.frame_available(clock=lambda: 99, path=path))
