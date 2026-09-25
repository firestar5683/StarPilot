"""Powered-offroad connectivity authority and existing Park boundaries."""

from pathlib import Path

import pytest

from openpilot.common.params import Params
from openpilot.starpilot.galaxy.settings import LiveContextSource
from openpilot.starpilot.galaxy.tests.test_borrowed_authority import Messages


@pytest.fixture
def powered(tmp_path):
  params, messages = Params(str(tmp_path / 'params')), Messages()
  params.put_bool('IsOffroad', True, block=True)
  messages.data['pandaStates'][0].ignitionLine = True
  for service in ('carState', 'selfdriveState'):
    messages.seen[service] = messages.alive[service] = messages.valid[service] = False
  clocks = {'mono': 1_000_000_000, 'offset': 10_000_000_000}
  authority = LiveContextSource(params, messages=messages, borrowed_messages=True, evidence_wait_ms=0,
                               mono_clock=lambda: clocks['mono'], boot_clock=lambda: clocks['mono'] + clocks['offset'])
  clocks['mono'] = 2_100_000_000
  assert authority.configuration_allowed()
  yield authority, params, messages, clocks
  authority.close()
  messages.update.assert_not_called()
  messages.sock['carState'].close.assert_not_called()


@pytest.mark.parametrize('service', ['deviceState', 'pandaStates'])
@pytest.mark.parametrize('field', ['seen', 'alive', 'valid'])
def test_powered_offroad_requires_healthy_publishers(powered, service, field):
  authority, _, messages, _ = powered
  getattr(messages, field)[service] = False
  assert not authority.configuration_allowed()


@pytest.mark.parametrize('offroad', [b'0', b'', b'corrupt'])
def test_powered_offroad_requires_effective_manager_mode(powered, offroad):
  authority, params, _, _ = powered
  Path(params.get_param_path('IsOffroad')).write_bytes(offroad)
  assert not authority.configuration_allowed()


def test_powered_offroad_rejects_started_and_missing_panda(powered):
  authority, _, messages, _ = powered
  messages.data['deviceState'].started = True
  assert not authority.configuration_allowed()
  messages.data['deviceState'].started = False
  messages.data['pandaStates'] = []
  assert not authority.configuration_allowed()


@pytest.mark.parametrize('service', ['deviceState', 'pandaStates'])
def test_powered_offroad_rejects_future_and_stale_publisher_stamps(powered, service):
  authority, _, messages, clocks = powered
  original = messages.logMonoTime[service]
  messages.logMonoTime[service] = original + 1_000_000_000
  assert not authority.configuration_allowed()
  messages.logMonoTime[service] = original
  clocks['mono'] += 2_000_000_000
  assert not authority.configuration_allowed()


def test_powered_offroad_resume_requires_new_evidence_and_preserves_strict_park(powered):
  authority, _, messages, clocks = powered
  assert not authority.parked()
  clocks['offset'] += 1_000_000_000
  assert not authority.configuration_allowed()
  clocks['mono'] += 100_000_000
  for service in ('deviceState', 'pandaStates'):
    messages.logMonoTime[service] = clocks['mono'] - 10_000_000 + (clocks['offset'] if service == 'pandaStates' else 0)
    messages.recv_time[service] = (clocks['mono'] - 10_000_000) / 1e9
  assert authority.configuration_allowed()
  assert not authority.parked()
  authority.close()
  assert not authority.configuration_allowed()
