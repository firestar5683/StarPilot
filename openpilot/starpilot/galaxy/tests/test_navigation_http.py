import base64
import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.remote import RemotePairing
from openpilot.starpilot.galaxy.server import make_remote_server, make_server
from openpilot.starpilot.navigation.owner import NavigationOwner


PLACE = {'name': 'Library', 'latitude': 41.1, 'longitude': -88.2}


class NavigationHttpTest(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    root = Path(temporary.name)
    self.access = GalaxyAccessOwner(root / 'access')
    self.pairing = RemotePairing(root / 'pairing')
    self.navigation = NavigationOwner(root / 'navigation', runtime_source=lambda: None, transient_root=root/'boot-navigation')
    self.parked = True
    self.local = make_server(port=0, owner=self.access, remote_pairing=self.pairing, navigation=self.navigation,
                             parked=lambda: self.parked)
    self.remote = make_remote_server(self.local, port=0)
    self.servers = []
    for server in (self.local, self.remote):
      thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
      thread.start()
      self.servers.append((server, thread))
    self.addCleanup(self.close)
    self.local_cookie = self.request()[2]['Set-Cookie'].split(';', 1)[0]
    self.access.configure('password123', lambda: True)
    self.slug = self.pairing.pair(hashlib.sha256(b'password123').hexdigest())
    record = self.pairing.read()
    self.remote_cookie = 'galaxy_session=' + base64.urlsafe_b64encode(json.dumps({self.slug: record['session']}).encode()).decode().rstrip('=')

  def close(self):
    for server, thread in reversed(self.servers):
      server.shutdown()
      thread.join(timeout=2)
      server.server_close()

  def request(self, path='/api/auth/session', *, payload=None, remote=False, cookie=None, origin=None):
    server = self.remote if remote else self.local
    host = f'{self.slug}.devices.local' if remote else f'127.0.0.1:{server.server_port}'
    headers = {'Host': host}
    if cookie is not None:
      headers['Cookie'] = cookie
    if payload is not None:
      headers.update({'Content-Type': 'application/json', 'Origin': origin or ('https://galaxy.firestar.link' if remote else f'http://{host}')})
    connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=2)
    try:
      connection.request('POST' if payload is not None else 'GET', path,
                         json.dumps(payload) if payload is not None else None, headers)
      response = connection.getresponse()
      return response.status, json.loads(response.read()), dict(response.getheaders())
    finally:
      connection.close()

  def test_map_tiles_recheck_authentication_after_provider(self):
    def tile(*args):
      self.pairing.unpair()
      return b'fixture tile'
    self.navigation.map_tile = tile
    connection = http.client.HTTPConnection('127.0.0.1', self.remote.server_port, timeout=2)
    try:
      connection.request('GET', '/api/navigation/map/tiles/0/0/0.png', headers={'Host': f'{self.slug}.devices.local', 'Cookie': self.remote_cookie})
      response = connection.getresponse()
      self.assertNotEqual(response.status, 200)
      self.assertNotIn(b'fixture tile', response.read())
    finally:
      connection.close()

  def action(self, action, *, remote=False, **values):
    return self.request('/api/navigation/action', payload=dict(action=action, revision=self.navigation.snapshot()['revision'], **values),
                         remote=remote, cookie=self.remote_cookie if remote else self.local_cookie)

  def test_local_and_remote_share_real_destination_and_saved_places_without_secrets(self):
    for remote in (False, True):
      with self.subTest(remote=remote):
        result = self.action('configure', remote=remote, patch={'enabled': True, 'token': 'pk.secret-test-token'})
        self.assertEqual(result[0], 200)
        self.assertTrue(result[1]['hasKey'])
        self.assertNotIn('pk.secret-test-token', json.dumps(result))
        result = self.action('select', remote=remote, destination=PLACE)
        self.assertEqual(result[0], 200)
        self.assertEqual(result[1]['destination']['name'], 'Library')
        self.assertEqual(result[1]['status'], 'waitingForLocation')
        self.assertEqual(self.action('favorite', remote=remote, destination=PLACE)[0], 200)
        result = self.action('clear', remote=remote)
        self.assertIsNone(result[1]['destination'])
        self.assertEqual(len(result[1]['favorites']), 1)
        self.assertEqual(self.action('removeFavorite', remote=remote, id=result[1]['favorites'][0]['id'])[1]['favorites'], [])

  def test_alternative_route_action_uses_authenticated_revision(self):
    from openpilot.starpilot.navigation.route_engine import NavigationRoute
    route = NavigationRoute({'distance':100., 'duration':20., 'geometry':{'coordinates':[[0.,0.],[.001,0.]]},
                             'legs':[{'steps':[{'distance':100.,'duration':20.,'maneuver':{'type':'depart','instruction':'Continue'}}]}]})
    self.action('configure', patch={'enabled':True,'token':'pk.test'})
    self.action('select', destination=PLACE)
    revision = self.navigation.read()['revision']
    self.navigation.record_routes(revision, [route,route])
    result = self.action('selectRoute', remote=True, index=1)
    self.assertEqual(result[0],200)
    self.assertEqual(result[1]['selectedRoute'],1)
    self.assertNotIn('pk.test',json.dumps(result))
    self.assertEqual(self.request('/api/navigation/action', payload={'action':'selectRoute','revision':revision,'index':0},
                                  remote=True,cookie=self.remote_cookie)[0],409)

  def test_gateway_auth_and_origin_are_required(self):
    self.assertEqual(self.request('/api/navigation/status', remote=True)[0], 401)
    self.assertEqual(self.request('/api/navigation/status', remote=True, cookie=self.local_cookie)[0], 401)
    payload = {'action': 'configure', 'revision': '0', 'patch': {'enabled': True}}
    self.assertEqual(self.request('/api/navigation/action', payload=payload, remote=True,
                                  cookie=self.remote_cookie, origin='https://wrong.example')[0], 403)
    self.assertFalse(self.navigation.snapshot()['enabled'])

  def test_keys_require_parked_but_destinations_do_not(self):
    self.parked = False
    self.assertEqual(self.action('configure', patch={'token': 'pk.new-key'})[0], 409)
    self.assertFalse(self.navigation.snapshot()['hasKey'])
    self.assertEqual(self.action('configure', patch={'enabled': True})[0], 200)
    self.assertEqual(self.action('select', destination=PLACE)[0], 200)

  def test_stale_or_invalid_actions_never_overwrite_configuration(self):
    self.action('configure', patch={'enabled': True})
    before = self.navigation.path.read_bytes()
    status = self.request('/api/navigation/action', payload={'action': 'clear', 'revision': '0'}, cookie=self.local_cookie)[0]
    self.assertEqual(status, 409)
    for payload in ({'action': 'configure', 'revision': '0', 'patch': {'OtherParam': True}},
                    {'action': 'clear', 'revision': '0', 'unwanted': True}, {'action': [], 'revision': '0'},
                    {'action': 'select', 'revision': '0', 'destination': {'name': 'bad', 'latitude': 95, 'longitude': 0}}):
      self.assertIn(self.request('/api/navigation/action', payload=payload, cookie=self.local_cookie)[0], (400, 409))
    self.assertEqual(self.navigation.path.read_bytes(), before)

  def test_poi_search_then_go_retrieves_only_selected_place(self):
    self.action('configure', patch={'token':'pk.synthetic','enabled':True})
    identity = 'poi/id'
    search = {'query':'coffee', 'searchId':str(uuid.uuid4()), 'clientId':str(uuid.uuid4())}
    suggestion = {'suggestions':[{'mapbox_id':identity,'name':'Coffee Shop','feature_type':'poi'}]}
    feature = {'features':[{'properties':{'mapbox_id':identity,'name':'Coffee Shop'},
                            'geometry':{'coordinates':[-90.,40.]}}]}
    with patch('openpilot.starpilot.navigation.owner.response_json',side_effect=[suggestion,feature]) as provider:
      status, result, _ = self.request('/api/navigation/search',payload=search,cookie=self.local_cookie)
      self.assertEqual(status,200)
      self.assertEqual(provider.call_count,1)
      self.assertNotIn('latitude',result['results'][0])
      status, result, _ = self.action('selectPlace',id=identity,searchId=search['searchId'])
      self.assertEqual(status,200)
      self.assertEqual(result['destination']['name'],'Coffee Shop')
      self.assertEqual(provider.call_count,2)
      self.assertEqual(provider.call_args_list[0].args[2]['session_token'],provider.call_args_list[1].args[2]['session_token'])
    unmarked = dict(result['destination'])
    unmarked.pop('temporary')
    self.assertEqual(self.action('favorite',destination=unmarked)[0],400)
    self.assertEqual(self.action('select',destination=unmarked)[0],400)
    self.assertIsNone(self.navigation.read()['destination'])
    self.assertNotIn('Coffee Shop',self.navigation.path.read_text())
    self.assertNotIn('pk.synthetic',json.dumps(result))
    self.assertEqual(self.action('selectPlace',id=identity,searchId=search['searchId'])[0],400)

  def test_slow_poi_retrieve_does_not_block_other_settings_actions(self):
    self.action('configure',patch={'token':'pk.synthetic','enabled':True})
    search = {'query':'coffee','searchId':str(uuid.uuid4()),'clientId':str(uuid.uuid4())}
    with patch('openpilot.starpilot.navigation.owner.response_json',return_value={
        'suggestions':[{'mapbox_id':'poi/id','name':'Coffee Shop','feature_type':'poi'}]}):
      self.request('/api/navigation/search',payload=search,cookie=self.local_cookie)
    entered, release, changed = threading.Event(), threading.Event(), threading.Event()
    results = {}
    def slow(*args):
      entered.set()
      release.wait(3)
      return {'features':[{'properties':{'mapbox_id':'poi/id','name':'Coffee Shop'},'geometry':{'coordinates':[-90.,40.]}}]}
    def retrieve():
      results['retrieve'] = self.action('selectPlace',id='poi/id',searchId=search['searchId'])[0]
    def configure():
      results['configure'] = self.action('configure',patch={'token':'pk.changed'})[0]
      changed.set()
    with patch('openpilot.starpilot.navigation.owner.response_json',side_effect=slow):
      worker = threading.Thread(target=retrieve)
      worker.start()
      self.assertTrue(entered.wait(2))
      other = threading.Thread(target=configure)
      other.start()
      try:
        self.assertTrue(changed.wait(1),'Provider retrieval blocked unrelated Galaxy actions')
      finally:
        release.set()
        worker.join(3)
        other.join(3)
    self.assertEqual(results,{'configure':200,'retrieve':409})
    self.assertIsNone(self.navigation.snapshot()['destination'])

  def test_browser_cancel_makes_suggestion_unselectable(self):
    self.action('configure',patch={'token':'pk.synthetic','enabled':True})
    search = {'query':'coffee','searchId':str(uuid.uuid4()),'clientId':str(uuid.uuid4())}
    with patch('openpilot.starpilot.navigation.owner.response_json',return_value={
        'suggestions':[{'mapbox_id':'poi/id','name':'Coffee Shop','feature_type':'poi'}]}) as provider:
      self.assertEqual(self.request('/api/navigation/search',payload=search,cookie=self.local_cookie)[0],200)
      self.assertEqual(self.action('cancelSearch',searchId=search['searchId'])[0],200)
      self.assertEqual(self.action('selectPlace',id='poi/id',searchId=search['searchId'])[0],400)
      self.assertEqual(provider.call_count,1)

  def test_poi_retrieve_rechecks_auth_before_temporary_selection(self):
    self.action('configure',patch={'token':'pk.synthetic','enabled':True})
    search = {'query':'coffee','searchId':str(uuid.uuid4()),'clientId':str(uuid.uuid4())}
    with patch('openpilot.starpilot.navigation.owner.response_json',return_value={
        'suggestions':[{'mapbox_id':'poi/id','name':'Coffee Shop','feature_type':'poi'}]}):
      self.assertEqual(self.request('/api/navigation/search',payload=search,remote=True,cookie=self.remote_cookie)[0],200)
    def revoked(*args):
      self.pairing.unpair()
      return {'features':[{'properties':{'mapbox_id':'poi/id','name':'Coffee Shop'},'geometry':{'coordinates':[-90.,40.]}}]}
    before = self.navigation.path.read_bytes()
    with patch('openpilot.starpilot.navigation.owner.response_json',side_effect=revoked):
      status, result, _ = self.action('selectPlace',id='poi/id',searchId=search['searchId'],remote=True)
    self.assertEqual(status,401)
    self.assertEqual(self.navigation.path.read_bytes(),before)
    self.assertNotIn('Coffee Shop',json.dumps(result))
    self.assertEqual(list(self.navigation.transient_root.glob('*.json')),[])

  def test_search_checks_session_again_after_provider_returns(self):
    self.navigation.search = lambda query: (self.pairing.unpair(), [PLACE])[1]
    result = self.request('/api/navigation/search', payload={'query': 'Library'}, remote=True, cookie=self.remote_cookie)
    self.assertEqual(result[0], 401)
    self.assertNotIn('Library', json.dumps(result[1]))
