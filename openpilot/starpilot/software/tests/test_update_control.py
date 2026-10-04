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

  def test_fast_wire_pins_branch_and_commit_without_changing_legacy_commands(self):
    commit = 'a' * 40
    with mock.patch.object(update_control, '_exchange') as exchange:
      update_control.send(123, 456, 'fast', branch='SecretGoodStarPilot', commit=commit)
      exchange.assert_called_once_with(123, 456, b'fast SecretGoodStarPilot ' + commit.encode())
    self.assertEqual(update_control._parse(b'fast SecretGoodStarPilot ' + commit.encode() + b'\n'),
                     ('fast', 'SecretGoodStarPilot', commit))
    for action in ('check', 'download'):
      self.assertEqual(update_control._command(action), action.encode())
      self.assertEqual(update_control._parse(action.encode() + b'\n'), (action, None, None))
    self.assertLessEqual(len(update_control._command('fast', 'x' * 128, commit)) + 1, update_control.MAX_COMMAND)
    for raw in (b'fast\n', b'fast Dom bad\n', b'fast Dom ' + commit.encode(),
                b'fast Dom ' + commit.encode() + b' extra\n', b'fast Dom\ncheck ' + commit.encode() + b'\n'):
      with self.subTest(raw=raw), self.assertRaises(update_control.UpdaterControlError):
        update_control._parse(raw)
    for branch, revision in ((None, commit), ('Dom', None), ('Dom\ncheck', commit), ('x' * 129, commit), ('Dom', 'A' * 40)):
      with self.subTest(branch=branch), self.assertRaises(update_control.UpdaterControlError):
        update_control.send(123, 456, 'fast', branch=branch, commit=revision)
    with self.assertRaises(update_control.UpdaterControlError):
      update_control.send(123, 456, 'check', branch='Dom', commit=commit)

  def test_server_delivers_fast_identity_and_legacy_callback_shape(self):
    for raw, expected in ((b'fast Dom ' + b'a' * 40 + b'\n', mock.call('fast', branch='Dom', commit='a' * 40)),
                          (b'check\n', mock.call('check')), (b'download\n', mock.call('download'))):
      with self.subTest(raw=raw):
        client, connection = socket.socketpair()
        try:
          client.settimeout(1)
          client.sendall(raw)
          callback = mock.Mock()
          listener = mock.Mock()
          listener.accept.side_effect = [(connection, None), OSError()]
          server = update_control.UpdaterControlServer(callback)
          with mock.patch.object(update_control, '_peer', return_value=(os.getpid(), os.geteuid())):
            server._run(listener)
          self.assertEqual(client.recv(16), b'ok\n')
          self.assertEqual(callback.call_args, expected)
        finally:
          client.close()
          connection.close()

  @unittest.skipUnless(sys.platform.startswith('linux') and hasattr(socket, 'SO_PEERCRED'), 'Linux peer credentials required')
  def test_rollback_wire_and_wait_helper_preserve_approved_identity(self):
    from openpilot.system.updated import updated
    command = update_control._command('rollback', branch='Dom', commit='a' * 40)
    self.assertEqual(update_control._parse(command + b'\n'), ('rollback', 'Dom', 'a' * 40))
    with mock.patch.object(updated.signal, 'signal'), mock.patch.object(updated, 'UpdaterControlServer'), mock.patch.object(updated.atexit, 'register'):
      helper = updated.WaitTimeHelper()
    helper._control_request('rollback', branch='Dom', commit='a' * 40)
    request, _, target = helper.current_request()
    self.assertEqual(request, updated.UserRequest.ROLLBACK)
    self.assertEqual(target, ('Dom', 'a' * 40))

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
