from unittest import TestCase
from unittest.mock import Mock, patch

from openpilot.starpilot.controllers.input import Press
from openpilot.starpilot.controllers.runtime import ControllerRuntime


class TestControllerRuntime(TestCase):
  def runtime(self):
    authority, reader, owner, service = Mock(), Mock(), Mock(), Mock()
    reader.poll.return_value = []
    reader.devices.return_value = []
    with patch('openpilot.starpilot.controllers.runtime.ControllerOwner', return_value=owner), \
         patch('openpilot.starpilot.controllers.runtime.ControllerService', return_value=service):
      runtime = ControllerRuntime(None, actions=Mock(), favorites=Mock(), invoke_favorite=Mock(),
                                  authority=authority, reader=reader)
    self.addCleanup(runtime.close)
    return runtime, authority, reader, owner, service

  def test_input_inventory_and_existing_presses_precede_new_bindings(self):
    runtime, _authority, reader, owner, service = self.runtime()
    reader.poll.return_value = [Press('device', 304, 10)]
    reader.devices.return_value = [{'id': 'device', 'name': 'Gamepad', 'bus': 5}]
    events = []
    owner.set_devices.side_effect = lambda devices: events.append(('devices', devices))
    owner.tick.side_effect = lambda: events.append(('tick',))
    owner.feed.side_effect = lambda press: events.append(('press', press))
    service.poll.side_effect = lambda: events.append(('settings',))
    runtime.poll()
    self.assertEqual([item[0] for item in events], ['devices', 'tick', 'press', 'settings'])
    self.assertEqual(events[0][1], reader.devices.return_value)

  def test_input_failure_stops_actions_and_releases_all_resources(self):
    runtime, authority, reader, owner, service = self.runtime()
    reader.poll.side_effect = OSError('input disconnected')
    with self.assertLogs('openpilot.starpilot.controllers.runtime', level='ERROR'):
      runtime.poll()
    runtime.poll()
    owner.feed.assert_not_called()
    service.poll.assert_not_called()
    reader.close.assert_called_once()
    authority.close.assert_called_once()
    service.close.assert_called_once()

  def test_idle_poll_expires_learning_even_without_input(self):
    runtime, _authority, _reader, owner, service = self.runtime()
    runtime.poll()
    owner.tick.assert_called_once()
    service.poll.assert_called_once()
    owner.feed.assert_not_called()

  def test_close_is_idempotent(self):
    runtime, authority, reader, _owner, service = self.runtime()
    runtime.close()
    runtime.close()
    reader.close.assert_called_once()
    authority.close.assert_called_once()
    service.close.assert_called_once()
