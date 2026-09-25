import time
import uuid
from unittest.mock import patch

import pytest

from openpilot.starpilot.navigation.owner import NavigationOwner, ValidationError, ConflictError
from openpilot.starpilot.navigation.runtime import RouteRuntime
from openpilot.starpilot.navigation.tests.test_route_runtime import Executor

POI = {'mapbox_id':'poi/id', 'name':'Coffee Shop', 'feature_type':'poi', 'full_address':'123 Main St, Springfield'}
FEATURE = {'features':[{'properties':POI, 'geometry':{'coordinates':[-90.,40.]}}]}
ADDRESS = {'name':'Old address', 'latitude':39., 'longitude':-91.}


@pytest.fixture
def owner(tmp_path):
  result = NavigationOwner(tmp_path/'saved', runtime_source=lambda:None, transient_root=tmp_path/'boot')
  saved = result.configure({'enabled':True, 'token':'pk.synthetic'}, '0', True)
  result.select(ADDRESS, saved['revision'], True)
  return result


def suggest(owner, caller='caller', client=None):
  search_id, client = str(uuid.uuid4()), client or str(uuid.uuid4())
  with patch('openpilot.starpilot.navigation.owner.response_json', return_value={'suggestions':[POI]}) as provider:
    result = owner.search_places('coffee', caller, search_id, client)
  return result[0], provider.call_args.args[2]['session_token'], client


def choose(owner, result, caller='caller', authorized=True):
  with patch('openpilot.starpilot.navigation.owner.response_json', return_value=FEATURE) as provider:
    value = owner.select_place(result['id'], result['searchId'], caller, owner.read()['revision'], authorized)
  return value, provider


def test_selected_poi_routes_without_persistent_coordinates_or_token(owner):
  result, session, _ = suggest(owner)
  assert 'latitude' not in result
  assert result['description'] == '123 Main St, Springfield'
  status, provider = choose(owner, result)
  assert provider.call_args.args[2]['session_token'] == session
  assert status['destination']['name'] == 'Coffee Shop'
  assert status['destination']['temporary'] is True
  assert owner.read()['destination'] is None
  assert 'Coffee Shop' not in owner.path.read_text()
  temporary = list(owner.transient_root.glob('*.json'))
  assert len(temporary) == 1 and temporary[0].stat().st_mode & 0o777 == 0o600
  assert 'pk.synthetic' not in temporary[0].read_text()
  second = NavigationOwner(owner.root, runtime_source=lambda:None, transient_root=owner.transient_root)
  executor = Executor()
  runtime = RouteRuntime(second, engine=type('Engine',(),{'fetch':None})(), executor=executor)
  assert runtime.update(10, (9,(-90.,40.),0.,0.),1)['destinationName'] == 'Coffee Shop'
  assert len(executor.jobs) == 1
  with pytest.raises(ValidationError):
    choose(owner, result)
  with pytest.raises(ValidationError, match='cannot be saved'):
    owner.favorite(status['destination'], status['revision'], True)


def test_expiry_clear_keychange_and_permanent_select_never_restore_old_route(owner):
  result, _, _ = suggest(owner)
  choose(owner, result)
  with patch('openpilot.starpilot.navigation.owner.time.monotonic', return_value=time.monotonic()+50000):
    assert owner.read_routing()['destination'] is None
  revision = owner.read()['revision']
  changed = owner.configure({'token':'pk.new'}, revision, True)
  assert changed['destination'] is None
  result, _, _ = suggest(owner)
  choose(owner,result)
  cleared = owner.clear(owner.read()['revision'], True)
  assert cleared['destination'] is None
  result, _, _ = suggest(owner)
  choose(owner,result)
  selected = owner.select(ADDRESS, owner.read()['revision'], True)
  assert selected['destination']['name'] == 'Old address'
  assert not list(owner.transient_root.glob('*.json'))


def test_favorite_only_revision_keeps_temporary_route_and_existing_favorites(owner):
  result, _, _ = suggest(owner)
  status, _ = choose(owner,result)
  saved = owner.favorite(ADDRESS,status['revision'],True)
  assert saved['destination']['name'] == 'Coffee Shop'
  assert saved['favorites'][0]['name'] == 'Old address'
  removed = owner.remove_favorite(saved['favorites'][0]['id'],saved['revision'],True)
  assert removed['destination']['name'] == 'Coffee Shop'


def test_rejected_authority_and_interrupted_commit_keep_previous_route(owner):
  result, _, _ = suggest(owner)
  choose(owner,result)
  prior = owner.snapshot()
  result, _, _ = suggest(owner)
  checks = iter((True,True,False))
  with pytest.raises(PermissionError):
    choose(owner,result,authorized=lambda:next(checks))
  assert owner.snapshot()['destination'] == prior['destination']
  assert owner.snapshot()['revision'] == prior['revision']
  result, _, _ = suggest(owner)
  with patch('openpilot.starpilot.navigation.owner.os.replace', side_effect=lambda source,dest,**kw:
             (_ for _ in ()).throw(OSError('synthetic crash')) if dest == owner.path else
             __import__('os').rename(source,dest,**kw)):
    with pytest.raises(OSError):
      choose(owner,result)
  assert owner.snapshot()['destination'] == prior['destination']


def test_sessions_are_caller_and_tab_scoped_cancelled_expired_and_single_use(owner):
  first, session1, client = suggest(owner)
  other, session2, _ = suggest(owner)
  assert session1 != session2
  newest, _, _ = suggest(owner, client=client)
  with pytest.raises(ValidationError):
    choose(owner,first)
  with pytest.raises(ValidationError):
    choose(owner,newest,caller='other-caller')
  owner.cancel_search('caller', newest['searchId'])
  with pytest.raises(ValidationError):
    choose(owner,newest)
  with patch('openpilot.starpilot.navigation.owner.time.monotonic',return_value=time.monotonic()+181):
    with pytest.raises(ValidationError):
      choose(owner,other)
  for _ in range(8):
    suggest(owner,caller='bounded')
  with pytest.raises(ValidationError,match='Too many'):
    suggest(owner,caller='bounded')


def test_invalid_retrieve_and_stale_revision_do_not_change_saved_destination(owner):
  result, _, _ = suggest(owner)
  before = owner.path.read_bytes()
  with patch('openpilot.starpilot.navigation.owner.response_json',return_value={'features':[]}):
    with pytest.raises(ValidationError):
      owner.select_place(result['id'],result['searchId'],'caller',owner.read()['revision'],True)
  assert owner.path.read_bytes() == before
  result, _, _ = suggest(owner)
  owner.favorite(ADDRESS,owner.read()['revision'],True)
  with pytest.raises(ValidationError):
    choose(owner,result)


def test_address_fallback_and_symlink_safe_ephemeral_state(owner,tmp_path):
  with patch('openpilot.starpilot.navigation.owner.response_json',return_value={'suggestions':[]}), \
       patch.object(owner,'search',return_value=[ADDRESS]) as fallback:
    assert owner.search_places('100 Main','caller',str(uuid.uuid4()),str(uuid.uuid4())) == [ADDRESS]
  fallback.assert_called_once_with('100 Main')
  owner.transient_root.rmdir()
  owner.transient_root.symlink_to(tmp_path)
  with pytest.raises(OSError):
    owner.read_routing()


def test_cancel_during_provider_does_not_start_address_fallback(owner):
  search_id, client_id = str(uuid.uuid4()), str(uuid.uuid4())
  def cancelled(*args):
    owner.cancel_search('caller',search_id)
    return {'suggestions':[]}
  with patch('openpilot.starpilot.navigation.owner.response_json',side_effect=cancelled), \
       patch.object(owner,'search') as fallback:
    with pytest.raises(ValidationError):
      owner.search_places('coffee','caller',search_id,client_id)
    fallback.assert_not_called()


def test_expired_and_crash_orphan_coordinates_are_deleted(owner):
  result, _, _ = suggest(owner)
  choose(owner,result)
  orphan = owner.transient_root/'orphan.json'
  orphan.write_text('synthetic orphan')
  with patch('openpilot.starpilot.navigation.owner.time.monotonic',return_value=time.monotonic()+50000):
    assert owner.read_routing()['destination'] is None
  assert not list(owner.transient_root.glob('*.json'))


def test_slow_retrieve_allows_keychange_and_rejects_stale_result(owner):
  import threading
  result, _, _ = suggest(owner)
  entered, release = threading.Event(), threading.Event()
  errors = []
  def slow(*args):
    entered.set()
    assert release.wait(2)
    return FEATURE
  def worker():
    try:
      owner.select_place(result['id'],result['searchId'],'caller',owner.read()['revision'],True)
    except Exception as error:
      errors.append(error)
  with patch('openpilot.starpilot.navigation.owner.response_json',side_effect=slow):
    thread = threading.Thread(target=worker)
    thread.start()
    assert entered.wait(2)
    try:
      changed = owner.configure({'token':'pk.changed'},owner.read()['revision'],True)
      assert changed['destination']['name'] == 'Old address'
    finally:
      release.set()
      thread.join(2)
  assert not thread.is_alive() and len(errors) == 1 and isinstance(errors[0], ConflictError)
  assert owner.snapshot()['destination']['name'] == 'Old address'
