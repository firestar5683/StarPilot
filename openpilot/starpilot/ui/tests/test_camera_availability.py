import threading
import unittest

from openpilot.starpilot.ui.camera_availability import CameraAvailability


class TestCameraAvailability(unittest.TestCase):
  def test_native_frames_freshness_throttle_and_background_publication(self):
    now = [1_000_000_000]
    written = []
    published = threading.Event()
    def write(*, clock):
      written.append((clock(), threading.get_ident()))
      published.set()
    owner = CameraAvailability(clock=lambda: now[0], write=write)
    self.addCleanup(owner.close)
    self.assertFalse(owner.available())
    owner.observe()
    self.assertTrue(published.wait(1))
    self.assertTrue(owner.available())
    self.assertNotEqual(written[0][1], threading.get_ident())
    for tick in range(1,100):
      now[0] = 1_000_000_000 + tick * 10_000_000
      owner.observe()
    self.assertEqual(len(written), 1)
    published.clear()
    now[0] = 2_000_000_000
    owner.observe()
    self.assertTrue(published.wait(1))
    self.assertEqual(len(written), 2)
    now[0] += 500_000_001
    self.assertFalse(owner.available())
    now[0] = 1
    self.assertFalse(owner.available())

  def test_slow_writer_keeps_latest_bounded_frame_and_never_blocks_observer(self):
    now = [1_000_000_000]
    entered, release, done = threading.Event(), threading.Event(), threading.Event()
    written = []
    def write(*, clock):
      stamp = clock()
      if not written:
        entered.set()
        release.wait(1)
      written.append(stamp)
      if len(written) == 2:
        done.set()
    owner = CameraAvailability(clock=lambda: now[0], write=write)
    self.addCleanup(owner.close)
    owner.observe()
    self.assertTrue(entered.wait(1))
    now[0] = 2_000_000_000
    owner.observe()
    now[0] = 3_000_000_000
    owner.observe()
    self.assertEqual(owner.pending, 3_000_000_000)
    release.set()
    self.assertTrue(done.wait(1))
    self.assertEqual(written, [1_000_000_000, 3_000_000_000])
