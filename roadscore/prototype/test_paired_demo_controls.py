"""Local injected transport only; no sockets, hardware, audio, or server changes."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from paired_demo_controls import GalaxyPeer, PairedDemoControls, _NoRedirect, _http_json


BASE = 'https://galaxy.firestar.link/ABCDEFGHIJKLMNOP'
COOKIE = 'ABCDEFGHIJKLMNOP%3A' + 'a' * 64
READY = {'available': True, 'offroad': True, 'state': 'READY', 'live': {'enabled': False},
         'demo': {'available': True, 'session_id': 'independent-peer-session',
                  'mode': 'recorded', 'signal_mode': 'recorded'}}


def target(result):
  return result['targets'].get('comma', result['targets'].get('peer'))


class MockGalaxy:
  def __init__(self):
    self.status = copy.deepcopy(READY)
    self.calls = []
    self.adopt = True

  def __call__(self, method, url, payload, headers, timeout):
    self.calls.append((method, url, payload, headers, timeout))
    if method == 'GET':
      return copy.deepcopy(self.status)
    field = 'mode' if url.endswith('/demo_engagement') else 'signal_mode'
    if self.adopt:
      self.status['demo'][field] = payload[field]
    return {'requested_' + field: payload[field], 'demo': copy.deepcopy(self.status['demo'])}


class PairedTests(unittest.TestCase):
  def setUp(self):
    self.transport = MockGalaxy()
    self.peer = GalaxyPeer(BASE, COOKIE)

  def forwarder(self, **options):
    result = PairedDemoControls(self.peer, enabled=True, transport=self.transport, **options)
    self.addCleanup(result.close)
    return result

  def test_default_disabled_even_with_explicit_peer(self):
    for peer in (None, self.peer):
      controls = PairedDemoControls(peer, transport=self.transport)
      result = controls.submit('demo_signal', 'left').result(0)
      self.assertEqual(target(result)['status'], 'disabled')
      self.assertFalse(result['music_video_synchronized'])
    self.assertEqual(self.transport.calls, [])

  def test_explicit_enable_and_authenticated_https_required(self):
    with self.assertRaises(ValueError):
      PairedDemoControls(enabled=True)
    for url in ('http://192.0.2.1:8082', 'https://host/', BASE + '?token=secret',
                BASE.replace('https://', 'https://user:secret@'), BASE + '/other', BASE + '\n'):
      with self.subTest(url=url), self.assertRaises(ValueError):
        GalaxyPeer(url, COOKIE)
    for cookie in ('', 'wrong', 'wrongslug%3A' + 'a' * 64, COOKIE + '\r\nInjected: value'):
      with self.assertRaises(ValueError):
        GalaxyPeer(BASE, cookie)
    self.assertNotIn(COOKIE, repr(self.peer))
    self.assertNotIn(BASE, repr(self.peer))

  def test_no_import_or_constructor_network(self):
    with patch('paired_demo_controls.build_opener', side_effect=AssertionError('No network')):
      controls = PairedDemoControls(self.peer, enabled=True)
      controls.close()
    self.assertEqual(self.transport.calls, [])

  def test_lan_requires_separate_opt_in_private_literal_and_exact_port(self):
    for url in ('http://192.168.8.156:8082', 'http://10.1.2.3:8082', 'http://172.16.0.1:8082'):
      with self.assertRaises(ValueError):
        GalaxyPeer(url)
      peer = GalaxyPeer(url, allow_lan_http=True)
      controls = PairedDemoControls(peer, enabled=True, transport=self.transport)
      self.addCleanup(controls.close)
      self.assertTrue(target(controls.submit('demo_signal', 'left').result(1))['applied'])
      self.assertNotIn('Cookie', self.transport.calls[-1][3])
      self.assertTrue(self.transport.calls[-1][1].startswith(url + '/api/roadscore/'))
    for url in ('http://8.8.8.8:8082', 'http://127.0.0.1:8082', 'http://169.254.1.1:8082',
                'http://192.0.2.1:8082', 'http://192.168.8.156', 'http://192.168.8.156:80',
                'http://device.local:8082', 'http://192.168.8.156:8082/mobile/',
                'http://192.168.8.156:8082/#/roadscore', 'http://[::1]:8082'):
      with self.subTest(url=url), self.assertRaises(ValueError):
        GalaxyPeer(url, allow_lan_http=True)
    with self.assertRaises(ValueError):
      GalaxyPeer('http://192.168.8.156:8082', COOKIE, allow_lan_http=True)

  def test_only_replay_actions_and_values(self):
    controls = self.forwarder()
    for action, value in (('power', 'off'), ('play', 'on'), ('start', 'on'), ('live', True),
                          ('demo_signal', 'hazards'), ('demo_engagement', 'controlsAllowed'),
                          ('demo_signal', {'signal_mode': 'left'}), ({}, 'left')):
      result = controls.submit(action, value).result(0)
      self.assertEqual(target(result)['status'], 'rejected')
    self.assertEqual(self.transport.calls, [])

  def test_independent_session_exact_post_and_per_target_ack(self):
    result = self.forwarder().submit('demo_signal', 'right').result(1)
    outcome = target(result)
    self.assertEqual(outcome['status'], 'applied')
    self.assertTrue(outcome['acknowledged'])
    self.assertTrue(outcome['applied'])
    self.assertFalse(outcome['delivery_unknown'])
    self.assertFalse(result['music_video_synchronized'])
    self.assertIn('not synchronized', result['disclosure'])
    self.assertEqual([call[0] for call in self.transport.calls], ['GET', 'POST', 'GET'])
    post = self.transport.calls[1]
    self.assertEqual(post[1], BASE + '/api/roadscore/demo_signal')
    self.assertEqual(post[2], {'session_id': 'independent-peer-session', 'signal_mode': 'right'})
    self.assertEqual(post[3]['Cookie'], 'galaxy_session=' + COOKIE)
    self.assertTrue(all(0 < call[4] <= .75 for call in self.transport.calls))

  def test_engagement_uses_its_distinct_payload(self):
    result = self.forwarder().submit('demo_engagement', 'disengaged').result(1)
    self.assertTrue(target(result)['applied'])
    self.assertEqual(self.transport.calls[1][2], {'session_id': 'independent-peer-session', 'mode': 'disengaged'})

  def test_current_galaxy_operator_wire_contract_without_network(self):
    source = Path(__file__).resolve().parents[2] / 'starpilot/system/the_galaxy/roadscore.py'
    spec = importlib.util.spec_from_file_location('paired_test_galaxy', source)
    galaxy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(galaxy)
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      run = root / 'results/current'
      run.mkdir(parents=True)
      state = {'route': 'fixture-route', 'input_mode': 'replay', 'command_wall': time.monotonic(),
               'presentation_session_id': 'galaxy-independent-session',
               'engagement_presentation': {'enabled': True}}
      (run / 'status.json').write_text(json.dumps(state))
      operator = galaxy.Operator(root=root, device=True, offroad=lambda: True)
      def local_transport(method, url, payload, headers, timeout):
        if method == 'GET':
          return {**READY, 'demo': operator.demo_status()}
        result = operator.operate(url.rsplit('/', 1)[1], payload, True)
        # Mock the replay app consuming the command after Galaxy acknowledged it.
        command = json.loads((run / 'demo_engagement.json').read_text())
        state.update(demo_engagement_mode=command['mode'], demo_signal_mode=command['signal_mode'])
        (run / 'status.json').write_text(json.dumps(state))
        return result
      self.transport = local_transport
      outcome = target(self.forwarder().submit('demo_signal', 'right').result(1))
      self.assertEqual(outcome['session_id'], 'galaxy-independent-session')
      self.assertTrue(outcome['applied'])
      self.assertEqual({p.name for p in run.iterdir()}, {'status.json', 'demo_engagement.json'})

  def test_unready_stale_live_stored_and_unknown_rejected_before_post(self):
    patches = [{'available': False}, {'offroad': False}, {'state': 'PREPARING'}, {'state': 'DEGRADED'},
               {'demo': {'available': False}}, {'demo': {}}, {'input_mode': 'live'},
               {'mode': 'stored-score'}, {'live': {'enabled': True}}, {'judging_locked': True}]
    for changes in patches:
      with self.subTest(changes=changes):
        self.transport = MockGalaxy()
        self.transport.status.update(changes)
        outcome = target(self.forwarder().submit('demo_signal', 'left').result(1))
        self.assertEqual(outcome['status'], 'failed')
        self.assertFalse(outcome['acknowledged'])
        self.assertEqual([c[0] for c in self.transport.calls], ['GET'])

  def test_missing_invalid_peer_session_cannot_use_local_session(self):
    for session in (None, '', 123, '\nbad', 'x' * 257):
      self.transport = MockGalaxy()
      self.transport.status['demo']['session_id'] = session
      outcome = target(self.forwarder().submit('demo_signal', 'left').result(1))
      self.assertEqual(outcome['error'], 'invalid_peer_session')
      self.assertEqual(len(self.transport.calls), 1)

  def test_http_auth_error_is_sanitized_and_never_retried(self):
    self.transport = lambda *args: (_ for _ in ()).throw(HTTPError(BASE, 401, COOKIE, {}, None))
    result = self.forwarder().submit('demo_signal', 'left').result(1)
    self.assertEqual(target(result)['error'], 'peer_http_401')
    self.assertNotIn(COOKIE, json.dumps(result))
    self.assertNotIn(BASE, json.dumps(result))

  def test_application_not_claimed_from_post_receipt_alone(self):
    self.transport.adopt = False
    outcome = target(self.forwarder(timeout=.1).submit('demo_signal', 'left').result(1))
    self.assertEqual(outcome['status'], 'acknowledged')
    self.assertTrue(outcome['acknowledged'])
    self.assertFalse(outcome['applied'])
    self.assertEqual(outcome['error'], 'peer_application_unconfirmed')
    self.assertEqual(sum(c[0] == 'POST' for c in self.transport.calls), 1)

  def test_session_change_after_post_does_not_retry_into_new_session(self):
    original = self.transport
    def changed(method, *args):
      value = original(method, *args)
      if method == 'POST':
        original.status['demo']['session_id'] = 'new-session'
      return value
    self.transport = changed
    outcome = target(self.forwarder().submit('demo_signal', 'left').result(1))
    self.assertEqual(outcome['error'], 'peer_session_changed')
    self.assertTrue(outcome['acknowledged'])
    self.assertFalse(outcome['applied'])
    self.assertEqual(sum(c[0] == 'POST' for c in original.calls), 1)

  def test_slow_status_has_bounded_future_no_queue_and_no_late_post(self):
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    calls = []
    def blocked(method, *args):
      calls.append(method)
      entered.set()
      release.wait(2)
      finished.set()
      return copy.deepcopy(READY)
    self.transport = blocked
    controls = self.forwarder(timeout=.1)
    started = time.monotonic()
    future = controls.submit('demo_signal', 'left')
    self.assertLess(time.monotonic() - started, .1)
    self.assertTrue(entered.wait(1))
    self.assertEqual(target(controls.submit('demo_signal', 'right').result(0))['status'], 'busy')
    try:
      outcome = target(future.result(1))
      self.assertEqual(outcome['status'], 'timed_out')
      self.assertFalse(outcome['delivery_unknown'])
      self.assertEqual(target(controls.submit('demo_signal', 'off').result(0))['status'], 'busy')
    finally:
      release.set()
    self.assertTrue(finished.wait(1))
    self.assertEqual(calls, ['GET'])

  def test_timeout_during_write_reports_unknown_without_rollback(self):
    entered, release = threading.Event(), threading.Event()
    original = self.transport
    def blocked(method, *args):
      value = original(method, *args)
      if method == 'POST':
        entered.set()
        release.wait(2)
      return value
    self.transport = blocked
    controls = self.forwarder(timeout=.1)
    future = controls.submit('demo_signal', 'left')
    self.assertTrue(entered.wait(1))
    try:
      outcome = target(future.result(1))
      self.assertTrue(outcome['delivery_unknown'])
      self.assertFalse(outcome['applied'])
      self.assertFalse(outcome['acknowledged'])
      self.assertEqual(original.status['demo']['signal_mode'], 'left')
      self.assertEqual(sum(c[0] == 'POST' for c in original.calls), 1)
    finally:
      release.set()

  def test_future_callback_can_close_without_deadlock(self):
    entered, release = threading.Event(), threading.Event()
    original = self.transport
    def blocked(method, *args):
      if method == 'POST':
        entered.set()
        release.wait(1)
      return original(method, *args)
    self.transport = blocked
    controls = self.forwarder()
    future = controls.submit('demo_signal', 'left')
    self.assertTrue(entered.wait(1))
    callback_done = threading.Event()
    future.add_done_callback(lambda _: (controls.close(), callback_done.set()))
    release.set()
    future.result(1)
    self.assertTrue(callback_done.wait(1))
    self.assertEqual(target(controls.submit('demo_signal', 'off').result(0))['status'], 'disabled')

  def test_redirects_are_rejected_instead_of_forwarding_cookie(self):
    with self.assertRaises(ValueError):
      _NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.example/')

  def test_response_reader_is_bounded_and_does_not_honor_proxies(self):
    class Response:
      status = 200
      class headers:
        @staticmethod
        def get_content_type(): return 'application/json'
      def __enter__(self): return self
      def __exit__(self, *args): pass
      def read(self, count):
        self.count = count
        return b'x' * count
    response = Response()
    with patch('paired_demo_controls.build_opener') as build:
      build.return_value.open.return_value = response
      with self.assertRaises(ValueError):
        _http_json('GET', BASE, None, {}, .2)
      self.assertEqual(build.call_args.args[0].proxies, {})
      self.assertEqual(response.count, 65537)


if __name__ == '__main__':
  unittest.main()
