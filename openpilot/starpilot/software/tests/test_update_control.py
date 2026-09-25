import os
import socket
import sys
import threading
import unittest
from unittest import mock

from openpilot.starpilot.software import update_control


class UpdaterControlTests(unittest.TestCase):
  def test_invalid_identity_and_action_fail_closed(self):
    self.assertFalse(update_control.available(0, 0))
    with self.assertRaises(update_control.UpdaterControlError):
      update_control.send(0, 0, 'install')

  @unittest.skipUnless(sys.platform.startswith('linux') and hasattr(socket, 'SO_PEERCRED'), 'Linux peer credentials required')
  def test_same_process_control_and_stale_identity(self):
    actions = []
    accepted = threading.Event()
    def request(action):
      actions.append(action)
      accepted.set()
    server = update_control.UpdaterControlServer(request)
    server.start()
    self.addCleanup(server.close)
    pid = os.getpid()
    start = update_control.process_start(pid)
    self.assertTrue(update_control.available(pid, start))
    self.assertEqual(actions, [])
    update_control.send(pid, start, 'check')
    self.assertTrue(accepted.wait(1))
    accepted.clear()
    update_control.send(pid, start, 'download')
    self.assertTrue(accepted.wait(1))
    self.assertEqual(actions, ['check', 'download'])
    self.assertFalse(update_control.available(pid, start + 1))
    with self.assertRaises(update_control.UpdaterControlError):
      update_control.send(pid, start + 1, 'check')

    real_peer = update_control._peer
    def wrong_server_pid(connection):
      if threading.current_thread() is threading.main_thread():
        return pid + 1, os.geteuid()
      return real_peer(connection)
    with mock.patch.object(update_control, '_peer', side_effect=wrong_server_pid):
      with self.assertRaises(update_control.UpdaterControlError):
        update_control.send(pid, start, 'check')
    self.assertEqual(actions, ['check', 'download'])

    with mock.patch.object(update_control, '_peer', return_value=(pid + 1, os.geteuid() + 1)):
      with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(1)
        connection.connect(update_control._address(pid, start, os.geteuid()))
        connection.sendall(b'check\n')
        self.assertEqual(connection.recv(16), b'error\n')
    self.assertEqual(actions, ['check', 'download'])
    server.close()
    self.assertFalse(update_control.available(pid, start))

  def test_wait_helper_maps_control_requests_without_signal_handlers(self):
    from openpilot.system.updated import updated

    with mock.patch.object(updated.signal, 'signal') as register_signal, \
         mock.patch.object(updated, 'UpdaterControlServer') as server_type, \
         mock.patch.object(updated.atexit, 'register'):
      helper = updated.WaitTimeHelper()
    self.assertEqual(register_signal.call_count, 2)
    server_type.assert_called_once()
    server_type.return_value.start.assert_called_once()
    self.assertEqual(helper.user_request, updated.UserRequest.NONE)
    self.assertFalse(helper.ready_event.is_set())
    helper._control_request('check')
    self.assertEqual(helper.user_request, updated.UserRequest.CHECK)
    self.assertTrue(helper.ready_event.is_set())
    helper.ready_event.clear()
    helper._control_request('download')
    self.assertEqual(helper.user_request, updated.UserRequest.FETCH)
    self.assertTrue(helper.ready_event.is_set())
    helper.ready_event.clear()
    helper._control_request('status')
    self.assertEqual(helper.user_request, updated.UserRequest.FETCH)
    self.assertFalse(helper.ready_event.is_set())


if __name__ == '__main__':
  unittest.main()
