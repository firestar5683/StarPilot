"""Managed Galaxy ignition continuity and real loopback process lifecycle."""

import http.client
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from opendbc.car.structs import car
from openpilot.common.params import Params
from openpilot.starpilot.galaxy import managed
from openpilot.starpilot.galaxy.server import make_server
from openpilot.system.manager.process import PythonProcess, ensure_running
from openpilot.system.manager.process_config import managed_processes


CHILD = r'''
import hashlib
import sys
from pathlib import Path
from openpilot.starpilot.galaxy import managed
from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.galaxy.server import make_remote_server
from openpilot.starpilot.galaxy.remote import RemotePairing, make_gateway_auth_server

root = Path(sys.argv[1])
owner = GalaxyAccessOwner(root / 'access')
pairing = RemotePairing(root / 'pairing')
if len(sys.argv) <= 2 or sys.argv[2] != 'unconfigured':
  assert owner.configure('disposable-password', lambda: True)
if len(sys.argv) > 2 and sys.argv[2].startswith('remote-'):
  assert pairing.pair(hashlib.sha256(b'disposable-password').hexdigest())

class Monitor:
  def sample(self):
    return {'schemaVersion': 1, 'mode': 'disposable-managed-test'}

class Maps:
  def snapshot(self):
    if len(sys.argv) > 2 and sys.argv[2] in ('blocked', 'remote-blocked'):
      import threading
      (root / 'active').write_text('active')
      threading.Event().wait(30)
    return {'schemaVersion': 1, 'mode': 'disposable-map-test'}

  def close(self):
    (root / 'closed').write_text('closed')

def factory(port, host):
  assert host == '0.0.0.0'
  server = make_server(port=0, owner=owner, remote_pairing=pairing, monitor=Monitor(), maps=Maps())
  (root / 'port').write_text(str(server.server_port))
  return server

managed.make_server = factory
def remote_factory(local):
  remote = make_remote_server(local, port=0)
  (root / 'remote-port').write_text(str(remote.server_port))
  return remote
managed.make_remote_server = remote_factory
managed.default_remote_pairing = lambda: pairing
managed.make_gateway_auth_server = lambda pairing, dongle_id: make_gateway_auth_server(pairing, dongle_id, port=0)
managed.main()
'''


class ManagedGalaxyTest(unittest.TestCase):
  def test_manager_runs_offroad_and_onroad_until_explicitly_disabled(self):
    proc = managed_processes['galaxy']
    self.assertIsInstance(proc, PythonProcess)
    self.assertEqual(proc.module, 'openpilot.starpilot.galaxy.managed')
    with tempfile.TemporaryDirectory() as directory, \
         mock.patch.object(proc, 'start') as start, mock.patch.object(proc, 'stop') as stop:
      params = Params(directory)
      CP = car.CarParams.new_message()
      selected = {'galaxy': proc}.values()
      with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop('STARPILOT_GALAXY_DEV', None)
        os.environ.pop('STARPILOT_GALAXY_DISABLE', None)
        self.assertEqual(ensure_running(selected, False, params, CP), [proc])
        self.assertEqual(ensure_running(selected, True, params, CP), [proc])
        self.assertEqual(ensure_running(selected, False, params, CP), [proc])
      self.assertEqual(start.call_count, 3)
      stop.assert_not_called()
      with mock.patch.dict(os.environ, {'STARPILOT_GALAXY_DISABLE': '1', 'STARPILOT_GALAXY_DEV': '1'}):
        self.assertEqual(ensure_running(selected, False, params, CP), [])
        self.assertEqual(ensure_running(selected, True, params, CP), [])
      with mock.patch.dict(os.environ, {'STARPILOT_GALAXY_DEV': '1', 'STARPILOT_GALAXY_DISABLE': '0'}):
        self.assertEqual(ensure_running(selected, True, params, CP), [proc])
      self.assertEqual(start.call_count, 4)
      self.assertEqual(stop.call_count, 2)

  def test_entrypoint_default_and_recovery_disable_before_binding(self):
    with mock.patch.dict(os.environ, {}, clear=False), mock.patch.object(managed, 'make_server') as make:
      os.environ.pop('STARPILOT_GALAXY_DEV', None)
      os.environ.pop('STARPILOT_GALAXY_DISABLE', None)
      with mock.patch.object(managed, 'serve_managed'), mock.patch.object(managed, 'make_remote_server'), \
           mock.patch.object(managed, 'make_gateway_auth_server'):
        managed.main()
      make.assert_called_once_with(port=8082, host='0.0.0.0')
      make.reset_mock()
      os.environ['STARPILOT_GALAXY_DISABLE'] = '1'
      with self.assertRaisesRegex(RuntimeError, 'STARPILOT_GALAXY_DISABLE=1'):
        managed.main()
      make.assert_not_called()

  def test_port_collision_does_not_fall_back_to_another_interface(self):
    with socket.socket() as held:
      held.bind(('127.0.0.1', 0))
      held.listen()
      port = held.getsockname()[1]
      with mock.patch.dict(os.environ, {'STARPILOT_GALAXY_DISABLE': '0'}), \
           mock.patch.object(managed, 'make_server', side_effect=lambda **kwargs: make_server(port=port)) as factory:
        with self.assertRaises(OSError):
          managed.main()
        factory.assert_called_once_with(port=8082, host='0.0.0.0')

  def test_real_local_process_auth_and_signal_cleanup(self):
    for termination, mode in ((signal.SIGINT, 'normal'), (signal.SIGTERM, 'normal'),
                              (signal.SIGTERM, 'blocked'), (signal.SIGTERM, 'unconfigured')):
      with self.subTest(termination=termination, mode=mode), tempfile.TemporaryDirectory() as directory:
        env = os.environ.copy()
        env.pop('STARPILOT_GALAXY_DISABLE', None)
        env.pop('STARPILOT_GALAXY_DEV', None)
        child = subprocess.Popen([sys.executable, '-c', CHILD, directory, mode], env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        held = None
        try:
          port_file = Path(directory, 'port')
          deadline = time.monotonic() + 10
          while not port_file.exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
          self.assertTrue(port_file.exists(), 'Managed child did not bind within ten seconds')
          port = int(port_file.read_text())

          def request(path, *, method='GET', payload=None, cookie=None, port=port, local=False):
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
            try:
              headers = {} if local else {'Forwarded': 'for=203.0.113.10'}
              if method == 'POST':
                headers.update({'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{port}'})
              if cookie is not None:
                headers['Cookie'] = cookie
              connection.request(method, path, body=json.dumps(payload) if payload is not None else None, headers=headers)
              response = connection.getresponse()
              return response.status, json.loads(response.read()), dict(response.getheaders())
            finally:
              connection.close()

          deadline = time.monotonic() + 2
          while True:
            try:
              status, body, _ = request('/api/auth/session')
              break
            except OSError:
              if time.monotonic() >= deadline:
                raise
              time.sleep(0.01)
          local_status, local_body, local_headers = request('/api/auth/session', local=True)
          self.assertEqual(local_status, 200)
          self.assertTrue(local_body['authenticated'])
          self.assertTrue(local_body['localAccess'])
          self.assertIn('Set-Cookie', local_headers)
          self.assertEqual((status, body['state']), (200, 'setup_required' if mode == 'unconfigured' else 'configured'))
          if mode == 'unconfigured':
            status, body, _ = request('/api/system/monitor')
            self.assertEqual((status, body['code']), (503, 'setup_required'))
            cookie = None
          else:
            self.assertEqual(request('/api/system/monitor')[0], 401)
            status, _, headers = request('/api/auth/login', method='POST', payload={'password': 'disposable-password'})
            self.assertEqual(status, 200)
            cookie = headers['Set-Cookie'].split(';', 1)[0]
            self.assertEqual(request('/api/system/monitor', cookie=cookie)[1]['mode'], 'disposable-managed-test')
          held = socket.create_connection(('127.0.0.1', port), timeout=2)
          if mode == 'blocked':
            request_line = f'GET /api/maps/status HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n'
            request_line += f'Cookie: {cookie}\r\nConnection: close\r\n\r\n'
            held.sendall(request_line.encode())
            active_file = Path(directory, 'active')
            deadline = time.monotonic() + 2
            while not active_file.exists() and time.monotonic() < deadline:
              time.sleep(0.01)
            self.assertTrue(active_file.exists(), 'Map reader was not active')
          else:
            # Exercise an accepted idle socket, then release it before the
            # normal-drain assertion. Its four-second timeout and the drain
            # deadline otherwise have a legitimate tie.
            held.close()
            held = None
          stopped_at = time.monotonic()
          child.send_signal(termination)
          stdout, stderr = child.communicate(timeout=6)
          self.assertEqual(child.returncode, 0, stderr)
          self.assertLess(time.monotonic() - stopped_at, 5)
          self.assertRegex(stdout, r'Galaxy local/LAN service listening on port \d+')
          if mode == 'blocked':
            self.assertFalse(Path(directory, 'closed').exists(), 'Live map reader was closed during a request')
          else:
            self.assertEqual(Path(directory, 'closed').read_text(), 'closed')
          with self.assertRaises(OSError):
            socket.create_connection(('127.0.0.1', port), timeout=1)
        finally:
          if held is not None:
            held.close()
          if child.poll() is None:
            child.kill()
            child.communicate(timeout=2)

  def test_remote_requests_drain_before_shared_sources_close(self):
    for mode in ('remote-normal', 'remote-blocked'):
      with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        child = subprocess.Popen([sys.executable, '-c', CHILD, directory, mode],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        held = None
        try:
          deadline = time.monotonic() + 10
          while not (root / 'remote-port').exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
          self.assertTrue((root / 'remote-port').exists(), 'Remote listener did not bind')
          port = int((root / 'remote-port').read_text())
          record = json.loads((root / 'pairing/remote-v1.json').read_text())
          slug = record['slug']
          cookie = f"galaxy_session={slug}%3A{record['session']}"
          held = socket.create_connection(('127.0.0.1', port), timeout=2)
          held.sendall((f'GET /api/maps/status HTTP/1.1\r\nHost: {slug}.devices.local\r\n' +
                        f'Cookie: {cookie}\r\nConnection: close\r\n\r\n').encode())
          if mode == 'remote-normal':
            self.assertIn(b'200 OK', held.recv(4096))
            held.close()
            held = None
          else:
            deadline = time.monotonic() + 2
            while not (root / 'active').exists() and time.monotonic() < deadline:
              time.sleep(0.01)
            self.assertTrue((root / 'active').exists(), 'Remote map reader was not active')
          stopped_at = time.monotonic()
          child.send_signal(signal.SIGTERM)
          _, stderr = child.communicate(timeout=6)
          self.assertEqual(child.returncode, 0, stderr)
          self.assertLess(time.monotonic() - stopped_at, 5)
          self.assertEqual((root / 'closed').exists(), mode == 'remote-normal')
          with self.assertRaises(OSError):
            socket.create_connection(('127.0.0.1', port), timeout=1)
        finally:
          if held is not None:
            held.close()
          if child.poll() is None:
            child.kill()
            child.communicate(timeout=2)


if __name__ == '__main__':
  unittest.main()
