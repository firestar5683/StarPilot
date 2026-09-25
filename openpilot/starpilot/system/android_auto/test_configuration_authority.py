from contextlib import ExitStack
from types import SimpleNamespace
from unittest import mock

import pytest

from openpilot.starpilot.system.android_auto import daemon
from openpilot.starpilot.galaxy.settings import LiveContextSource
from openpilot.starpilot.drive_state.tests.test_evidence import Messages


def test_configuration_park_authority_is_fresh_and_releases_physical_observer(tmp_path):
  messages = Messages()
  messages.values['pandaStates'][0].ignitionLine = True
  messages.values['pandaStates'][0].controlsAllowed = True
  messages.values['pandaStates'][0].safetyModel = 'gm'
  source = SimpleNamespace(after_mono_ns=1_000_000_000, snapshot=lambda: messages, sock={})
  from openpilot.common.params import Params
  params = Params(str(tmp_path))
  params.put_bool('IsOffroad', False)
  authority = LiveContextSource(params, messages=source, mono_clock=lambda: 2_100_000_000,
                                boot_clock=lambda: 12_100_000_000, evidence_wait_ms=0)
  assert not authority.parked()
  assert authority.configuration_allowed()
  for field, value in [('enabled', True), ('active', True)]:
    setattr(messages.values['selfdriveState'], field, value)
    assert not authority.configuration_allowed()
    setattr(messages.values['selfdriveState'], field, False)
  messages.values['carState'].gearShifter = 'drive'
  assert not authority.configuration_allowed()
  messages.values['carState'].gearShifter = 'park'
  messages.valid['carState'] = False
  assert not authority.configuration_allowed()
  messages.valid['carState'] = True
  assert authority.configuration_allowed()
  physical = authority.physical
  authority.close()
  assert physical.closed and physical.messages is None
  assert authority.physical is None
  assert not authority.configuration_allowed()


@pytest.mark.parametrize('bind_failure', [False, True])
def test_daemon_uses_configuration_authority_and_cleans_up_after_bind_failure(bind_failure):
  with ExitStack() as patches:
    evidence = mock.Mock()
    evidence.start.return_value = evidence
    authority = mock.Mock()
    bluetooth, supervisor, server = mock.Mock(), mock.Mock(), mock.Mock()
    factories = [
      ('openpilot.starpilot.galaxy.evidence.EvidenceSource', evidence),
      ('openpilot.starpilot.galaxy.settings.LiveContextSource', authority),
      ('openpilot.starpilot.system.android_auto.bluetooth_bridge.SharedBluetoothOwner', bluetooth),
      ('openpilot.common.params.Params', mock.Mock()),
      ('openpilot.starpilot.system.android_auto.daemon.Supervisor', supervisor),
    ]
    calls = {name: patches.enter_context(mock.patch(name, return_value=value)) for name, value in factories}
    patches.enter_context(mock.patch.object(daemon.argparse.ArgumentParser, 'parse_args', return_value=SimpleNamespace(once=False)))
    for name in ('unlink', 'chmod'):
      patches.enter_context(mock.patch.object(daemon.os, name))
    patches.enter_context(mock.patch.object(daemon.signal, 'signal'))
    patches.enter_context(mock.patch.object(daemon.threading, 'Thread'))
    factory = patches.enter_context(mock.patch.object(daemon, 'Server', return_value=server,
                                                      side_effect=OSError('bind failed') if bind_failure else None))
    if bind_failure:
      with pytest.raises(OSError, match='bind failed'):
        daemon.main()
    else:
      assert daemon.main() == 0
      server.serve_forever.assert_called_once()
      server.server_close.assert_called_once()
    assert calls['openpilot.starpilot.system.android_auto.bluetooth_bridge.SharedBluetoothOwner'].call_args.args[0] == authority.configuration_allowed
    assert factory.call_args.args[-1] == authority.configuration_allowed
    for resource in (supervisor, bluetooth, authority, evidence):
      resource.close.assert_called_once()


def test_force_offroad_uses_live_park_authority_and_rejects_movement(tmp_path):
  from openpilot.starpilot.drive_state.evidence import PhysicalSource
  from openpilot.starpilot.drive_state.owner import DriveStateOwner, Mode, Rejected
  from openpilot.starpilot.drive_state.tests.test_owner import Params, BOOT
  messages = Messages()
  messages.after_mono_ns = 1_000_000_000
  messages.values['pandaStates'][0].ignitionLine = True
  messages.values['pandaStates'][0].controlsAllowed = True
  messages.values['pandaStates'][0].safetyModel = 'gm'
  messages.values['deviceState'] = SimpleNamespace(started=True)
  physical = PhysicalSource(messages, mono=lambda: 2_100_000_000, boot=lambda: 12_100_000_000)
  owner = DriveStateOwner(Params(), tmp_path / 'owner', alive=lambda _: True)
  owner.initialize(pid=1, birth=2, boot=BOOT)
  state = owner.request('offroad', expected_revision=owner.snapshot().revision,
                        authorized=lambda: True, override_allowed=physical.allowed)
  assert state.mode == Mode.OFFROAD
  owner.request('auto', expected_revision=state.revision, authorized=lambda: True, override_allowed=physical.allowed)
  messages.values['carState'].standstill = False
  with pytest.raises(Rejected):
    owner.request('offroad', expected_revision=owner.snapshot().revision,
                  authorized=lambda: True, override_allowed=physical.allowed)
  physical.close()
