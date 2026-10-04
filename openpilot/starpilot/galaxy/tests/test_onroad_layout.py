import copy
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from openpilot.common.params import Params
from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.onroad_layout import LayoutChanged, OnroadLayoutOwner
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.ui.onroad_customization import MAX_BYTES, PARAM_KEY, default_document


class TestOnroadLayoutOwner(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.parked = True
    self.owner = OnroadLayoutOwner(self.params, lambda: self.parked)

  def changed(self, profile='large'):
    snapshot = self.owner.snapshot()
    document = copy.deepcopy(snapshot['document'])
    first = next(iter(document['layouts'][profile].values()))
    first['enabled'] = not first['enabled']
    return {'revision': snapshot['revision'], 'document': document}

  def test_defaults_and_profile_edits_survive_independent_saves(self):
    initial = self.owner.snapshot()
    self.assertTrue(initial['editable'])
    self.assertTrue(initial['valid'])
    self.assertEqual(initial['document'], default_document())
    self.assertIsNone(self.params.get(PARAM_KEY))
    large = self.changed()
    saved = self.owner.save(large, session_valid=lambda: True)
    self.assertEqual(saved['document']['layouts']['compact'], initial['document']['layouts']['compact'])
    compact = self.changed('compact')
    result = self.owner.save(compact, session_valid=lambda: True)
    self.assertEqual(result['document']['layouts']['large'], large['document']['layouts']['large'])
    self.assertEqual(self.params.get(PARAM_KEY), compact['document'])
    self.assertNotEqual(initial['revision'], result['revision'])

  def test_v1_read_is_non_mutating_and_widget_colors_save_with_source_revision(self):
    old = default_document()
    old['version'] = 1
    del old['widgetColors']
    del old['roadColors']
    for profile in old['layouts'].values():
      del profile['steering_wheel']['size']
    old['palette']['text'] = '#ABCDEF80'
    old['layouts']['compact']['driver_monitor'].update(x=80, y=40, enabled=False)
    raw = json.dumps(old).encode()
    path = Path(self.params.get_param_path(PARAM_KEY))
    path.write_bytes(raw)
    snapshot = self.owner.snapshot()
    self.assertTrue(snapshot['valid'])
    self.assertEqual(path.read_bytes(), raw)
    expected_layouts = copy.deepcopy(old['layouts'])
    for profile, placements in expected_layouts.items():
      placements['steering_wheel']['size'] = default_document()['layouts'][profile]['steering_wheel']['size']
    self.assertEqual(snapshot['document']['layouts'], expected_layouts)
    document = copy.deepcopy(snapshot['document'])
    document['widgetColors']['compact']['conditional_mode'] = {'cardFill': '#12345680'}
    saved = self.owner.save({'revision': snapshot['revision'], 'document': document}, session_valid=lambda: True)
    self.assertEqual(saved['document'], document)
    self.assertEqual(saved['document']['palette'], old['palette'])
    self.assertNotEqual(saved['revision'], snapshot['revision'])
    with self.assertRaises(LayoutChanged):
      self.owner.save({'revision': snapshot['revision'], 'document': document}, session_valid=lambda: True)

  def test_stale_browser_cannot_overwrite_another_profile_edit(self):
    stale = self.changed('compact')
    fresh = self.changed('large')
    self.owner.save(fresh, session_valid=lambda: True)
    with self.assertRaises(LayoutChanged):
      self.owner.save(stale, session_valid=lambda: True)
    self.assertEqual(self.params.get(PARAM_KEY), fresh['document'])

  def test_parked_and_session_authority_rechecked_during_commit(self):
    request = self.changed()
    self.parked = False
    self.assertFalse(self.owner.snapshot()['editable'])
    with self.assertRaises(LayoutChanged):
      self.owner.save(request, session_valid=lambda: True)
    self.parked = True
    calls = 0
    def session():
      nonlocal calls
      calls += 1
      return calls == 1
    with self.assertRaises(LayoutChanged):
      self.owner.save(request, session_valid=session)
    self.assertGreaterEqual(calls, 2)
    self.assertIsNone(self.params.get(PARAM_KEY))

  def test_corrupt_saved_document_can_be_repaired_without_silent_write(self):
    path = Path(self.params.get_param_path(PARAM_KEY))
    path.write_bytes(b'{"version":1,"version":2}')
    snapshot = self.owner.snapshot()
    self.assertFalse(snapshot['valid'])
    self.assertTrue(snapshot['editable'])
    self.assertEqual(snapshot['document'], default_document())
    self.assertEqual(path.read_bytes(), b'{"version":1,"version":2}')
    saved = self.owner.save({'revision': snapshot['revision'], 'document': default_document()}, session_valid=lambda: True)
    self.assertTrue(saved['valid'])
    path.write_bytes(b'x' * (MAX_BYTES + 1))
    self.assertFalse(self.owner.snapshot()['editable'])
    with self.assertRaises(OSError):
      self.owner.save({'revision': saved['revision'], 'document': default_document()}, session_valid=lambda: True)

  def test_unknown_and_invalid_requests_do_not_write(self):
    request = self.changed()
    for invalid in ({}, {**request, 'action': 'execute'}, {'revision': True, 'document': request['document']},
                    {'revision': request['revision'], 'document': {'version': 99}}):
      with self.subTest(request=invalid), self.assertRaises(ValueError):
        self.owner.save(invalid, session_valid=lambda: True)
    self.assertIsNone(self.params.get(PARAM_KEY))


class TestOnroadLayoutHttp(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(str(Path(temporary.name) / 'params'))
    self.parked = True
    self.owner = OnroadLayoutOwner(self.params, lambda: self.parked)
    access = GalaxyAccessOwner(Path(temporary.name) / 'access')
    self.server = make_server(port=0, owner=access, layouts=self.owner)
    self.worker = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    self.worker.start()
    self.addCleanup(self.stop)

  def stop(self):
    self.server.shutdown()
    self.worker.join(timeout=2)
    self.server.server_close()

  def request(self, path, payload=None, cookie='', *, origin=None, raw=None):
    connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
    headers = {'Cookie': cookie}
    if payload is not None or raw is not None:
      headers.update({'Content-Type': 'application/json', 'Origin': origin or f'http://127.0.0.1:{self.server.server_port}'})
    try:
      connection.request('POST' if payload is not None or raw is not None else 'GET', path,
                         body=raw if raw is not None else json.dumps(payload) if payload is not None else None, headers=headers)
      response = connection.getresponse()
      return response.status, json.loads(response.read()), dict(response.getheaders())
    finally:
      connection.close()

  def login(self):
    code, _, headers = self.request('/api/auth/session', None)
    self.assertEqual(code, 200)
    return headers['Set-Cookie'].split(';', 1)[0]

  def test_local_access_layout_save_and_stale_write(self):
    self.assertEqual(self.request('/api/ui/layout')[0], 401)
    cookie = self.login()
    code, snapshot, _ = self.request('/api/ui/layout', cookie=cookie)
    self.assertEqual(code, 200)
    self.assertEqual(set(snapshot['metadata']['profiles']), {'large', 'compact'})
    request = {'revision': snapshot['revision'], 'document': snapshot['document']}
    covered_actions = copy.deepcopy(request)
    covered_actions['document']['layouts']['compact']['speed_limit']['y'] = -1
    self.assertEqual(self.request('/api/ui/layout', covered_actions, cookie)[0], 400)
    self.assertIsNone(self.params.get(PARAM_KEY))
    code, saved, _ = self.request('/api/ui/layout', request, cookie)
    self.assertEqual(code, 200)
    self.assertEqual(saved['document'], default_document())
    self.assertEqual(self.request('/api/ui/layout', request, cookie)[0], 409)
    self.parked = False
    self.assertEqual(self.request('/api/ui/layout', {'revision': saved['revision'], 'document': saved['document']}, cookie)[0], 409)
    self.assertEqual(self.params.get(PARAM_KEY), default_document())

  def test_mutation_requires_origin_session_and_unique_fields(self):
    cookie = self.login()
    _, snapshot, _ = self.request('/api/ui/layout', cookie=cookie)
    request = {'revision': snapshot['revision'], 'document': snapshot['document']}
    self.assertEqual(self.request('/api/ui/layout', request)[0], 401)
    self.assertEqual(self.request('/api/ui/layout', request, cookie, origin='http://example.com')[0], 403)
    self.assertEqual(self.request('/api/ui/layout', cookie=cookie, raw='{"revision":"a","revision":"b"}')[0], 400)
    self.assertEqual(self.request('/api/ui/layout', cookie=cookie, raw=' ' * 17409)[0], 413)
    self.assertIsNone(self.params.get(PARAM_KEY))
