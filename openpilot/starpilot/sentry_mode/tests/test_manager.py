import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openpilot.common.params import Params
from openpilot.starpilot.sentry_mode.preferences import KEY, Preferences, encode
from openpilot.system.manager import process_config


class TestSentryManagerPredicate(unittest.TestCase):
  def test_device_and_pc_matrix_requires_enabled_and_valid_saved_document(self):
    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, PARAMS_ROOT=directory, OPENPILOT_PREFIX="sentrymanager",
                                                                  STARPILOT_SENTRY_DEVELOPMENT="0"):
      params = Params()
      process = process_config.managed_processes["sentry_motion"]
      sensor = process_config.managed_processes["sensord"]
      self.assertEqual(process.enabled, not process_config.PC)
      self.assertEqual(sensor.enabled, not process_config.PC)
      with patch.dict(os.environ, STARPILOT_SENTRY_DEVELOPMENT="1"):
        self.assertFalse(process_config.sentry_motion(False, params, object()))
        self.assertFalse(process_config.sensord_run(False, params, object()))
        self.assertTrue(process_config.sensord_run(True, params, object()))
        source = Path(params.get_param_path(KEY))
        source.write_bytes(b"invalid")
        self.assertFalse(process_config.sentry_motion(False, params, object()))
        source.write_bytes(encode(Preferences(True)))
        self.assertTrue(process_config.sentry_motion(False, params, object()))
        self.assertTrue(process_config.sensord_run(False, params, object()))
        self.assertFalse(process_config.sentry_motion(True, params, object()))
      self.assertTrue(process_config.sentry_motion(False, params, object()))
      self.assertTrue(process_config.sensord_run(False, params, object()))


if __name__ == "__main__":
  unittest.main()
