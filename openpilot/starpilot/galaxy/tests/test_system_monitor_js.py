"""Run the browser-native monitor contract through the repository unittest runner."""

import os
from pathlib import Path
import shutil
import subprocess
import unittest


TESTS = tuple(path.name for path in sorted(Path(__file__).parent.glob('test_*.mjs')))


class SystemMonitorJavaScriptTest(unittest.TestCase):
  def test_snapshot_and_process_contract(self):
    requested = os.environ.get("STARPILOT_NODE") or "node"
    node = shutil.which(requested)
    self.assertIsNotNone(node, f"Node.js runtime not found: {requested}. Set STARPILOT_NODE to a Node 24 executable.")
    assert node is not None

    for test in TESTS:
      with self.subTest(test=test):
        try:
          result = subprocess.run([node, str(Path(__file__).with_name(test))], capture_output=True, text=True, timeout=30, check=False)
        except subprocess.TimeoutExpired as exc:
          self.fail(f"System Monitor JavaScript contract timed out after 30 seconds: {exc}")
        detail = "\n".join((f"System Monitor JavaScript contract failed ({result.returncode}).",
                            f"stdout:\n{result.stdout}", f"stderr:\n{result.stderr}"))
        self.assertEqual(result.returncode, 0, detail)
