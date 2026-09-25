"""Actual radio writer survives manager admission in a separate process."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from openpilot.common.params import Params, ParamKeyFlag
from openpilot.starpilot.bluetooth.radio_preference import RadioPreference
from openpilot.starpilot.state_migration import MigrationRequired, prepare_manager_start


SECOND_START = '''
import sys
from pathlib import Path
from openpilot.common.params import Params
from openpilot.starpilot.state_migration import prepare_manager_start
params = Params()
prepare_manager_start(params, Path(sys.argv[1]), dry_run=True)
prepare_manager_start(params, Path(sys.argv[1]))
'''


def test_actual_radio_writer_is_registered_and_second_start_preserves_value(tmp_path):
  params_root = tmp_path / 'params'
  params = Params(str(params_root))
  storage = tmp_path / 'recovery'
  preference = RadioPreference(Path(params.get_param_path('BluetoothEnabled')))
  assert 'BluetoothEnabled' in {key.decode() if isinstance(key, bytes) else key for key in params.all_keys()}
  assert params.get_default_value('BluetoothEnabled') is None
  prepare_manager_start(params, storage)
  assert not preference.path.exists()
  for enabled in (True, False):
    change = preference.begin(enabled)
    change.apply()
    expected = b'1' if enabled else b'0'
    assert params.get('BluetoothEnabled') is enabled
    assert preference.path.read_bytes() == expected
    for flag in (ParamKeyFlag.CLEAR_ON_MANAGER_START, ParamKeyFlag.CLEAR_ON_ONROAD_TRANSITION,
                 ParamKeyFlag.CLEAR_ON_OFFROAD_TRANSITION, ParamKeyFlag.CLEAR_ON_IGNITION_ON,
                 ParamKeyFlag.DEVELOPMENT_ONLY):
      params.clear_all(flag)
      assert preference.path.read_bytes() == expected
    subprocess.run([sys.executable, '-c', SECOND_START, str(storage)],
                   env=dict(os.environ, PARAMS_ROOT=str(params_root)), check=True)
    assert preference.path.read_bytes() == expected
    assert preference.enabled() is enabled


def test_legacy_newline_radio_semantics_and_unrelated_unknown_guard(tmp_path):
  params = Params(str(tmp_path / 'params'))
  storage = tmp_path / 'recovery'
  prepare_manager_start(params, storage)
  preference = RadioPreference(Path(params.get_param_path('BluetoothEnabled')))
  preference.path.write_bytes(b'1\n\n')
  assert preference.enabled()
  subprocess.run([sys.executable, '-c', SECOND_START, str(storage)],
                 env=dict(os.environ, PARAMS_ROOT=str(tmp_path / 'params')), check=True)
  assert preference.path.read_bytes() == b'1\n\n'
  change = preference.begin(False)
  change.apply()
  assert change.rollback()
  assert preference.path.read_bytes() == b'1\n\n'
  unknown = Path(params.get_param_path()) / 'UnregisteredRadioRegression'
  unknown.write_bytes(b'preserve')
  with pytest.raises(MigrationRequired, match='unknown saved keys'):
    prepare_manager_start(params, storage, dry_run=True)
  assert unknown.read_bytes() == b'preserve'
  assert preference.path.read_bytes() == b'1\n\n'
