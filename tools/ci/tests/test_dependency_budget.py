import importlib.util
import unittest
import tempfile
from pathlib import Path


CHECKER_PATH = Path(__file__).resolve().parents[3] / 'scripts/lint/check_dependencies.py'
SPEC = importlib.util.spec_from_file_location('starpilot_dependency_budget_check', CHECKER_PATH)
if SPEC is None or SPEC.loader is None:
  raise RuntimeError(f'Cannot load dependency checker: {CHECKER_PATH}')
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)

TOOLING_PACKAGES = CHECKER.TOOLING_PACKAGES
direct_dependency_counts = CHECKER.direct_dependency_counts
direct_dependencies_within_limits = CHECKER.direct_dependencies_within_limits
installed_dependency_counts = CHECKER.installed_dependency_counts
installed_dependencies_within_limits = CHECKER.installed_dependencies_within_limits


class DirectDependencyBudgetTest(unittest.TestCase):
  def setUp(self):
    self.project = {
      'dependencies': ['core'] * 23,
      'optional-dependencies': {
        'testing': ['test'] * 4,
        'tools': ['tool'] * 5,
        'vendored': ['vendor'] * 7,
        'dev': ['dev'] * 3,
        'safety': ['safety'] * 5,
      },
    }

  def test_existing_separate_budgets_are_admitted(self):
    self.assertEqual(direct_dependency_counts(self.project), {'baseline': 39, 'dev': 3, 'safety': 5})
    self.assertTrue(direct_dependencies_within_limits(self.project))

  def test_new_extra_and_each_over_budget_category_fail(self):
    for name in ('new_extra', 'dev', 'safety'):
      with self.subTest(name=name):
        project = {
          'dependencies': self.project['dependencies'],
          'optional-dependencies': {key: list(values) for key, values in self.project['optional-dependencies'].items()},
        }
        project['optional-dependencies'].setdefault(name, []).append('new-package')
        self.assertFalse(direct_dependencies_within_limits(project))


class InstalledDependencyBudgetTest(unittest.TestCase):
  def test_locked_tooling_allowance_and_baseline_boundary(self):
    self.assertEqual(len(TOOLING_PACKAGES), 15)
    baseline = {f'baseline-{index}' for index in range(64)}
    self.assertEqual(installed_dependency_counts(baseline | TOOLING_PACKAGES), (64, 15))
    self.assertTrue(installed_dependencies_within_limits(baseline | TOOLING_PACKAGES))
    self.assertTrue(installed_dependencies_within_limits(baseline | {'baseline-64'} | TOOLING_PACKAGES))
    self.assertFalse(installed_dependencies_within_limits(baseline | {'baseline-64', 'baseline-65'} | TOOLING_PACKAGES))

  def test_sixteenth_tool_and_unknown_package_fail_separately(self):
    baseline = {f'baseline-{index}' for index in range(65)}
    expanded_tooling = TOOLING_PACKAGES | {'new-ci-tool'}
    self.assertEqual(installed_dependency_counts(baseline | expanded_tooling, expanded_tooling), (65, 16))
    self.assertFalse(installed_dependencies_within_limits(baseline | expanded_tooling, expanded_tooling))
    self.assertEqual(installed_dependency_counts(baseline | TOOLING_PACKAGES | {'unknown-package'}), (66, 15))
    self.assertFalse(installed_dependencies_within_limits(baseline | TOOLING_PACKAGES | {'unknown-package'}))


class InstalledPayloadTest(unittest.TestCase):
  def test_import_caches_do_not_change_payload_and_other_files_still_count(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      (root / "package.py").write_bytes(b"source")
      (root / "native.so").write_bytes(b"binary")
      (root / "interpreter").symlink_to(root / "native.so")
      self.assertEqual(CHECKER.installed_payload_bytes(root), 12)
      cache = root / "__pycache__"
      cache.mkdir()
      (cache / "package.cpython-312.pyc").write_bytes(b"cache" * 100)
      self.assertEqual(CHECKER.installed_payload_bytes(root), 12)
      (cache / "payload.bin").write_bytes(b"data")
      (root / "standalone.pyc").write_bytes(b"bytecode")
      self.assertEqual(CHECKER.installed_payload_bytes(root), 24)


if __name__ == '__main__':
  unittest.main()
