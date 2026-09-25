"""Native UI state/cache integration in an isolated process; no drawing or devices."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from openpilot.common.basedir import BASEDIR


class TestUICacheState(unittest.TestCase):
  def test_lost_or_unqualified_cache_clears_displayed_vehicle_capability(self):
    ipc_root = '/tmp' if sys.platform == 'darwin' else '/dev/shm'
    with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory(prefix='msgq_cache-test-', dir=ipc_root) as ipc:
      environment = dict(os.environ, PARAMS_ROOT=str(Path(temporary) / 'params'),
                         OPENPILOT_PREFIX=Path(ipc).name.removeprefix('msgq_'))
      if sys.platform == 'darwin':
        # The macOS wheel has no headless extension. Import its native backend
        # without opening a window; this test never initializes drawing.
        environment.pop('RAYLIB_BACKEND', None)
      script = '''
from unittest.mock import patch
from opendbc.car.structs import car
from openpilot.common.params import Params
from openpilot.starpilot.schema_cache import put_cache
from openpilot.selfdrive.ui.ui_state import ui_state

params = Params()
cp = car.CarParams.new_message(openpilotLongitudinalControl=True, alphaLongitudinalAvailable=False)
with patch.object(ui_state, 'chestnut_compiled', True):
  put_cache(params, 'CarParamsPersistent', cp, block=True)
  ui_state.update_params()
  assert ui_state.CP is not None and ui_state.has_longitudinal_control
  params.remove('CarParamsPersistent')
  ui_state.update_params()
  assert ui_state.CP is None and not ui_state.has_longitudinal_control
  params.put('CarParamsPersistent', cp.to_bytes(), block=True)
  ui_state.update_params()
  assert ui_state.CP is None and not ui_state.has_longitudinal_control
  put_cache(params, 'CarParamsPersistent', cp, block=True)
  ui_state.update_params()
  assert ui_state.has_longitudinal_control
  params.put('CarParamsPersistent', b'damaged-cache', block=True)
  ui_state.update_params()
  assert ui_state.CP is None and not ui_state.has_longitudinal_control
  assert params.get('CarParamsPersistent') == b'damaged-cache'
assert ui_state._params_thread is None and not ui_state.prime_state._running
'''
      result = subprocess.run([sys.executable, '-c', script], cwd=BASEDIR, env=environment, capture_output=True, text=True, timeout=30)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
  unittest.main()
