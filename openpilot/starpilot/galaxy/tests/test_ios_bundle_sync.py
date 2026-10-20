import importlib.util
from pathlib import Path
import unittest

TOOL = Path(__file__).resolve().parents[2] / 'companion/ios/tools/sync_web_bundle.py'


class IosBundleSyncTest(unittest.TestCase):
  def test_bundled_web_ui_matches_galaxy_web(self):
    spec = importlib.util.spec_from_file_location('sync_web_bundle', TOOL)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    self.assertEqual(tool.drift(), [], 'Run openpilot/starpilot/companion/ios/tools/sync_web_bundle.py')

  def test_preview_only_files_are_never_bundled(self):
    spec = importlib.util.spec_from_file_location('sync_web_bundle', TOOL)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    self.assertFalse(any(path.startswith('assets/mobile/') or path in ('data/runtime.json', 'data/system-monitor.sample.json')
                         for path in tool.source_files()))


if __name__ == '__main__':
  unittest.main()
