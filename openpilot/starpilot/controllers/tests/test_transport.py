from pathlib import Path
import socket
import struct
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from openpilot.starpilot.controllers.transport import (
  ControllerDenied, ControllerInvalid, ControllerService, ControllerUnavailable, request_action, request_status,
)


class TestControllerTransport(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.path = Path(temporary.name) / 'ui.sock'
    self.owner = Mock()
    self.threads = []
    self.owner.snapshot.side_effect = lambda: (self.threads.append(threading.get_ident()) or {'version': 1})
    self.owner.action.side_effect = lambda payload: (self.threads.append(threading.get_ident()) or {'accepted': payload})
    self.service = ControllerService(self.owner, self.path)
    self.service.start()
    self.addCleanup(self.service.close)

  def pump(self, callback):
    result = {}
    def call():
      try:
        result['value'] = callback()
      except Exception as error:
        result['error'] = error
    client = threading.Thread(target=call)
    client.start()
    deadline = time.monotonic() + 2
    while client.is_alive() and time.monotonic() < deadline:
      self.service.poll()
      client.join(0.01)
    self.assertFalse(client.is_alive())
    return result

  def test_status_and_configuration_run_on_poll_thread(self):
    self.assertEqual(self.pump(lambda: request_status(self.path))['value'], {'version': 1})
    payload = {'operation': 'test', 'enabled': True}
    self.assertEqual(self.pump(lambda: request_action(payload, self.path))['value']['accepted'], payload)
    self.assertEqual(self.threads, [threading.get_ident()] * 2)
    self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
    self.owner.feed.assert_not_called()

  def test_owner_permission_and_validation_return_typed_errors(self):
    self.owner.action.side_effect = PermissionError('Park to configure buttons')
    self.assertIsInstance(self.pump(lambda: request_action({'operation': 'cancel'}, self.path))['error'], ControllerDenied)
    self.owner.action.side_effect = ValueError('Unknown button')
    self.assertIsInstance(self.pump(lambda: request_action({'operation': 'cancel'}, self.path))['error'], ControllerInvalid)

  def test_expired_request_cannot_execute_later(self):
    with patch('openpilot.starpilot.controllers.transport.REQUEST_DEADLINE', 0.05):
      with self.assertRaises(ControllerUnavailable):
        request_action({'operation': 'learn', 'slot': 1}, self.path, timeout=0.5)
    self.service.poll()
    self.owner.action.assert_not_called()

  def test_claimed_slow_write_reports_indeterminate_result(self):
    result = {}
    def slow_action(payload):
      time.sleep(0.1)
      return {'saved': True}
    self.owner.action.side_effect = slow_action
    with patch('openpilot.starpilot.controllers.transport.REQUEST_DEADLINE', 0.04):
      result = self.pump(lambda: request_action({'operation': 'cancel'}, self.path))
    self.assertIsInstance(result['error'], ControllerUnavailable)
    self.assertIn('may have changed', str(result['error']))
    self.owner.action.assert_called_once()

  def test_remote_cannot_inject_physical_input(self):
    with self.assertRaises(ControllerInvalid):
      request_action({'operation': 'press', 'code': 304}, self.path)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
      peer.settimeout(1)
      peer.connect(str(self.path))
      data = b'{"operation":"feed","code":304}'
      peer.sendall(struct.pack('!I', len(data)) + data)
      response = peer.recv(1024)
      self.assertIn(b'invalid', response)
    self.owner.feed.assert_not_called()
    self.owner.action.assert_not_called()

  def test_duplicate_fields_and_oversize_fail_without_dispatch(self):
    for data, size in ((b'{"operation":"status","operation":"cancel"}', None), (b'', 65537)):
      with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
        peer.settimeout(1)
        peer.connect(str(self.path))
        peer.sendall(struct.pack('!I', len(data) if size is None else size) + data)
        self.assertIn(b'invalid', peer.recv(1024))
    self.service.poll()
    self.owner.action.assert_not_called()
    self.owner.snapshot.assert_not_called()

  def test_contender_does_not_unlink_running_service(self):
    contender = ControllerService(self.owner, self.path)
    with self.assertRaises(ControllerUnavailable):
      contender.start()
    contender.close()
    self.assertTrue(self.path.exists())
    self.assertIn('value', self.pump(lambda: request_status(self.path)))

  def test_unexpected_owner_error_is_logged_and_not_returned(self):
    self.owner.snapshot.side_effect = KeyError('private details')
    with self.assertLogs('openpilot.starpilot.controllers.transport', level='ERROR') as logged:
      first = self.pump(lambda: request_status(self.path))
      self.pump(lambda: request_status(self.path))
    self.assertEqual(len(logged.output), 1)
    self.assertNotIn('private details', str(first['error']))
    self.assertIsInstance(first['error'], ControllerUnavailable)

  def test_close_and_missing_ui_are_bounded(self):
    self.service.close()
    self.assertFalse(self.path.exists())
    with self.assertRaises(ControllerUnavailable):
      request_status(self.path, timeout=0.05)
