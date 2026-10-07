"""The retired key retains saved bytes without affecting the fixed output ceiling."""

from pathlib import Path
import tempfile
import unittest

from openpilot.common.params import Params
from openpilot.starpilot.longitudinal.output_max import KEY, final_output
from openpilot.starpilot.state_migration import MigrationRequired, prepare_manager_start


class OutputMaximumNamespaceTests(unittest.TestCase):
  def test_native_key_initialized_retention_and_unqualified_legacy_rejection(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      params = Params(str(root / 'params'))
      recovery = root / 'recovery'
      keys = {key.decode() if isinstance(key, bytes) else key for key in params.all_keys()}
      self.assertIn(KEY, keys)
      prepare_manager_start(params, recovery)
      params.put(KEY, .6, block=True)
      raw = Path(params.get_param_path(KEY)).read_bytes()
      prepare_manager_start(params, recovery, dry_run=True)
      prepare_manager_start(params, recovery)
      self.assertEqual(Path(params.get_param_path(KEY)).read_bytes(), raw)
      self.assertEqual(final_output(5.0), 4.0)
      legacy = Params(str(root / 'legacy'))
      namespace = Path(legacy.get_param_path())
      (namespace / 'AdvancedLongitudinalTune').write_bytes(b'0')
      (namespace / 'MaxDesiredAcceleration').write_bytes(b'0.1')
      before = {path.name: path.read_bytes() for path in namespace.iterdir()}
      with self.assertRaises(MigrationRequired):
        prepare_manager_start(legacy, root / 'legacy-recovery', dry_run=True)
      self.assertEqual({path.name: path.read_bytes() for path in namespace.iterdir()}, before)
      self.assertFalse((namespace / KEY).exists())
