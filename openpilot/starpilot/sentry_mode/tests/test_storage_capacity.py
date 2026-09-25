from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openpilot.starpilot.sentry_mode import storage


class TestStorageCapacity(unittest.TestCase):
  def test_camera_events_fill_advertised_capacity_and_survive_restart(self):
    with tempfile.TemporaryDirectory() as folder, patch.object(storage, "MAX_EVENTS", 4):
      owner = storage.EventStore(Path(folder).resolve() / "events")
      image = b"\xff\xd8frame\xff\xd9"
      for stamp in range(4):
        self.assertTrue(owner.record("warning", stamp, permitted=lambda: True, images={"wide": image, "cabin": image}).durable)
      restarted = storage.EventStore(owner.root)
      self.assertEqual(len(restarted.snapshot()["events"]), 4)
      self.assertEqual(restarted.snapshot()["capacity"], 4)
      with self.assertRaises(storage.StorageUnavailable):
        restarted.record("alarm", 5, permitted=lambda: True, images={"cabin": image})

  def test_unpublished_image_directory_still_consumes_capacity(self):
    with tempfile.TemporaryDirectory() as folder, patch.object(storage, "MAX_EVENTS", 2):
      owner = storage.EventStore(Path(folder).resolve() / "events")
      owner.root.mkdir(mode=0o700)
      (owner.root / ("a" * 32)).mkdir(mode=0o700)
      owner.record("warning", 1, permitted=lambda: True)
      with self.assertRaises(storage.StorageUnavailable):
        owner.record("warning", 2, permitted=lambda: True)
