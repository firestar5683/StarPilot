import signal
import subprocess
import sys
import types
from unittest.mock import Mock

import pytest

from openpilot.starpilot.companion.environment import Environment


@pytest.fixture
def setup(tmp_path):
  requirements = tmp_path / 'requirements.txt'
  requirements.write_text('dbus-next==0.2.3\npycryptodome==3.23.0\nzeroconf==0.151.3\n')
  python = tmp_path / 'data/stardust-venv/bin/python'
  now = [0]
  child = Mock(pid=123, poll=Mock(return_value=None))
  run = Mock()
  popen = Mock(return_value=child)
  killpg = Mock()
  environment = Environment(python, requirements, tmp_path / 'install.sh', run, popen, lambda: now[0], killpg)
  yield environment, child, now
  environment.close()


def installed(environment):
  environment.python.parent.mkdir(parents=True, exist_ok=True)
  environment.python.touch()


def test_missing_environment_installs_automatically_and_only_runs_once(setup):
  environment, child, _ = setup
  assert not environment.step(install_allowed=True)
  args, kwargs = environment.popen.call_args
  assert args[0] == ['bash', str(environment.installer)]
  assert kwargs['start_new_session'] is True
  assert kwargs['env']['COMPANION_VENV'] == str(environment.python.parents[1])
  assert not environment.step(install_allowed=True)
  environment.popen.assert_called_once()
  installed(environment)
  child.poll.return_value = 0
  assert environment.step(install_allowed=True)
  assert environment.step(install_allowed=False)
  assert environment.log is None
  assert environment.python.parents[2].joinpath('stardust-setup.log').stat().st_mode & 0o777 == 0o600
  environment.popen.assert_called_once()


def test_existing_valid_environment_starts_offline_even_onroad(setup):
  environment, _, _ = setup
  installed(environment)
  assert environment.step(install_allowed=False)
  assert environment.step(install_allowed=False)
  environment.run.assert_called_once()
  environment.popen.assert_not_called()


def test_missing_environment_waits_until_installation_allowed(setup):
  environment, _, now = setup
  assert not environment.step(install_allowed=False)
  environment.popen.assert_not_called()
  now[0] = 60
  assert not environment.step(install_allowed=True)
  environment.popen.assert_called_once()


def test_broken_environment_verification_is_backed_off_while_onroad(setup):
  environment, _, now = setup
  installed(environment)
  environment.run.side_effect = subprocess.CalledProcessError(1, 'verification')
  for timestamp in range(0, 60, 2):
    now[0] = timestamp
    assert not environment.step(install_allowed=False)
  environment.run.assert_called_once()
  environment.popen.assert_not_called()
  now[0] = 60
  assert not environment.step(install_allowed=False)
  assert environment.run.call_count == 2
  now[0] = 120
  assert not environment.step(install_allowed=True)
  environment.popen.assert_called_once()


@pytest.mark.parametrize('result', [1, 0])
def test_failed_or_partial_install_is_retried_without_deleting_data(setup, result):
  environment, child, now = setup
  data = environment.python.parents[2]
  data.mkdir(parents=True)
  pairing = data / 'pairing.json'
  pairing.write_text('existing pairing key')
  assert not environment.step(True)
  child.poll.return_value = result
  # Even a successful exit is insufficient without a verified Python environment.
  assert not environment.step(True)
  assert not environment.step(True)
  environment.popen.assert_called_once()
  now[0] = 60
  assert not environment.step(True)
  assert environment.popen.call_count == 2
  assert pairing.read_text() == 'existing pairing key'


def test_wrong_versions_or_broken_imports_trigger_repair(setup):
  environment, child, _ = setup
  installed(environment)
  environment.run.side_effect = subprocess.CalledProcessError(1, 'verification')
  assert not environment.step(True)
  code = environment.run.call_args.args[0][2]
  assert "'zeroconf': '0.151.3'" in code
  assert 'from Crypto.Cipher import AES' in code
  child.poll.return_value = 0
  assert not environment.step(True)
  assert not environment.verified


def test_installer_is_canceled_when_driving_or_phone_sharing_starts(setup):
  environment, child, now = setup
  assert not environment.step(True)
  assert not environment.step(False)
  environment.killpg.assert_called_once_with(child.pid, signal.SIGTERM)
  assert environment.child is None
  assert environment.log is None
  assert not environment.step(True)
  environment.popen.assert_called_once()
  now[0] = 60
  assert not environment.step(True)
  assert environment.popen.call_count == 2


def test_timeout_stops_the_whole_installation_process_group(setup):
  environment, child, now = setup
  environment.step(True)
  now[0] = 180
  child.wait.side_effect = [subprocess.TimeoutExpired('installer', 2), 0]
  assert not environment.step(True)
  assert environment.killpg.call_args_list[0].args == (child.pid, signal.SIGTERM)
  assert environment.killpg.call_args_list[1].args == (child.pid, signal.SIGKILL)
  assert environment.child is None


def test_shutdown_cancels_an_in_progress_install(setup):
  environment, child, _ = setup
  environment.step(True)
  environment.close()
  environment.killpg.assert_called_once_with(child.pid, signal.SIGTERM)
  assert environment.child is None
  assert environment.log is None


def test_installer_start_failure_retries_and_closes_log(setup):
  environment, _, now = setup
  environment.popen.side_effect = OSError('temporary failure')
  assert not environment.step(True)
  assert environment.log is None
  assert not environment.step(True)
  environment.popen.assert_called_once()
  now[0] = 60
  assert not environment.step(True)
  assert environment.popen.call_count == 2


@pytest.mark.parametrize('offroad,sharing,allowed', [(False, False, False), (True, True, False), (True, False, True)])
def test_supervisor_automatically_prepares_then_starts_discovery(monkeypatch, tmp_path, offroad, sharing, allowed):
  from openpilot.starpilot.companion import bluetooth_daemon as daemon
  params = Mock()
  # The active manager publishes IsOffroad; the imported fork's IsOnroad key does not exist here.
  params.get_bool.side_effect = lambda key: {'IsOffroad': offroad}[key]
  module = types.ModuleType('openpilot.common.params')
  module.Params = lambda: params
  monkeypatch.setitem(sys.modules, 'openpilot.common.params', module)
  stopped = Mock(is_set=Mock(side_effect=[False, False, True]))
  monkeypatch.setattr(daemon.threading, 'Event', lambda: stopped)
  monkeypatch.setattr(daemon.signal, 'signal', Mock())
  monkeypatch.setattr(daemon, 'phone_uplink_active', lambda: sharing)
  monkeypatch.setattr(daemon, 'KEY_PATH', tmp_path / 'missing-pairing')
  environment = Mock(step=Mock(return_value=allowed))
  monkeypatch.setattr(daemon, 'Environment', lambda: environment)
  child = Mock(poll=Mock(return_value=None))
  popen = Mock(return_value=child)
  monkeypatch.setattr(daemon.subprocess, 'Popen', popen)
  daemon.main()
  assert environment.step.call_count == 2
  environment.step.assert_called_with(install_allowed=allowed)
  environment.close.assert_called_once()
  if allowed:
    popen.assert_called_once()
    assert popen.call_args.args[0] == [str(daemon.PYTHON), '-m', 'openpilot.starpilot.companion.lan_discovery']
    child.terminate.assert_called_once()
  else:
    popen.assert_not_called()
