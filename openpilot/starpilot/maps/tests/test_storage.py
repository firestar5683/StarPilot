import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openpilot.starpilot.maps.storage import offline_root
from openpilot.starpilot.maps import shadow_lifecycle as shadow


class TestMapStorage(unittest.TestCase):
  def test_default_and_namespaced_stores_are_separate(self):
    with tempfile.TemporaryDirectory() as directory:
      anchor = Path(directory)
      with patch.dict(os.environ, {'OPENPILOT_PREFIX': ''}):
        normal = offline_root(anchor)
        normal.mkdir(parents=True)
        self.assertTrue(shadow._owned_root(normal, anchor))
      with patch.dict(os.environ, {'OPENPILOT_PREFIX': 'desk_12'}):
        isolated = offline_root(anchor)
        isolated.mkdir(parents=True)
        self.assertNotEqual(normal, isolated)
        self.assertTrue(shadow._owned_root(isolated, anchor))
        self.assertFalse(shadow._owned_root(normal, anchor))
        isolated.rmdir()
        isolated.symlink_to(normal, target_is_directory=True)
        self.assertFalse(shadow._owned_root(isolated, anchor))

  def test_invalid_namespace_cannot_choose_a_directory(self):
    for value in ('../normal', '/', 'a/b', '.', 'x' * 65):
      with self.subTest(value=value), patch.dict(os.environ, {'OPENPILOT_PREFIX': value}):
        with self.assertRaises(ValueError):
          offline_root()
