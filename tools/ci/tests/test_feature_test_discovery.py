"""Keep custom pytest-function tests in the hosted unit-test selection."""

from pathlib import Path
import unittest

from tools.ci.run_host_tests import pytest_files


ROOT = Path(__file__).resolve().parents[3]


class TestFeatureTestDiscovery(unittest.TestCase):
  def test_hosted_pytest_selection_covers_all_custom_function_tests(self):
    workflow = (ROOT / '.github/workflows/tests.yaml').read_text()
    unit_job = workflow.split('\n  unit_tests:', 1)[1].split('\n  map_provider:', 1)[0]
    self.assertIn('run: python3 tools/ci/run_host_tests.py --pytest', unit_job)
    selected = pytest_files()
    self.assertTrue(selected)
    for package in ('flm', 'spot_monitor', 'sentry_mode', 'galaxy', 'ui'):
      self.assertTrue(any(path.startswith(f'openpilot/starpilot/{package}/') for path in selected), package)


if __name__ == '__main__':
  unittest.main()
