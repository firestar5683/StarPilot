"""Host-only companion tests: stub native Params/IPC/solver imports, never devices.

Run from the repository root with uv --extra testing --noconftest via this script.
The Params stub is in-memory and does not establish native storage/ABI coverage.
"""

import sys
import types
from unittest.mock import MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
msgq = types.ModuleType('msgq')
for name in (
  'fake_event_handle',
  'drain_sock_raw',
  'MultiplePublishersError',
  'IpcError',
  'Context',
  'Poller',
  'SubSocket',
  'PubSocket',
  'SocketEventHandle',
  'toggle_fake_events',
  'set_fake_prefix',
  'get_fake_prefix',
  'delete_fake_prefix',
  'wait_for_one_event',
):
  setattr(msgq, name, MagicMock())
sys.modules['msgq'] = msgq
params = types.ModuleType('openpilot.common.params')


class Params:
  values = {}

  def __init__(self, path='default'):
    self.data = self.values.setdefault(str(path), {})

  def get(self, key, *args, **kwargs):
    return self.data.get(key)

  def get_bool(self, key):
    return bool(self.get(key))

  def put(self, key, value, **kwargs):
    self.data[key] = value

  def put_bool(self, key, value, **kwargs):
    self.put(key, value)

  def remove(self, key):
    self.data.pop(key, None)


params.Params = Params
params.ParamKeyType = MagicMock()
params.ParamKeyFlag = MagicMock()
params.UnknownKeyName = KeyError
sys.modules['openpilot.common.params'] = params
native = types.ModuleType('openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.c_generated_code.acados_ocp_solver_pyx')
native.AcadosOcpSolverCython = MagicMock()
sys.modules[native.__name__] = native
import pytest

defaults = [
  'openpilot/starpilot/companion/android/tests/test_android_manifest.py',
  'openpilot/starpilot/companion/android/tests/test_ble_wire_vectors.py',
  'openpilot/starpilot/companion/android/tests/test_lan_discovery.py',
  'openpilot/starpilot/galaxy/tests/test_companion.py',
  'openpilot/starpilot/galaxy/tests/test_companion_http.py',
  'openpilot/starpilot/galaxy/tests/test_companion_data_guards.py',
]
sys.exit(pytest.main(['--noconftest', '-n0', '-q', *(sys.argv[1:] or defaults)]))
