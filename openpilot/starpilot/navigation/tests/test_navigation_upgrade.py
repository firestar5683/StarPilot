from concurrent.futures import Future
from types import SimpleNamespace
import pytest
from openpilot.starpilot.navigation.owner import NavigationOwner, ConflictError, ValidationError
from openpilot.starpilot.navigation.route_engine import NavigationRoute
from openpilot.starpilot.navigation.runtime import RouteRuntime


def make_route(longitude, duration):
  return NavigationRoute({'distance': 1112., 'duration': duration, 'geometry': {'coordinates': [[0.,0.],[longitude,0.]]},
    'legs': [{'steps': [{'distance':1112., 'duration':duration, 'maneuver':{'type':'depart','instruction':'Go east'}}]}]})


def test_alternative_selection_keeps_favorites_and_gps_loss_is_visual_only(tmp_path):
  owner = NavigationOwner(tmp_path, runtime_source=lambda:None, transient_root=tmp_path/'boot')
  state = owner.configure({'enabled':True,'token':'pk.test'}, '0', True)
  place = {'name':'Home', 'longitude':.01, 'latitude':0.}
  state = owner.favorite(place, state['revision'], True)
  state = owner.select(place, state['revision'], True)
  future = Future()
  runtime = RouteRuntime(owner, engine=SimpleNamespace(fetch=None), executor=SimpleNamespace(submit=lambda *args:future))
  runtime.update(10, (9,(0.,0.),5.,90.), 1)
  first, second = make_route(.01,100), make_route(.02,150)
  first.alternatives = [first,second]
  future.set_result(first)
  runtime.update(20, (19,(0.,0.),5.,90.), 1)
  state = owner.snapshot()
  assert len(state['alternatives']) == 2
  assert not (tmp_path/'route-options.json').exists()
  assert (tmp_path/'boot'/'routes.cache').exists()
  selected = owner.select_route(1, state['revision'], True)
  assert selected['selectedRoute'] == 1 and selected['favorites'][0]['name'] == 'Home'
  runtime.update(30, (29,(0.,0.),5.,90.), 1)
  assert runtime.route is second
  lost = runtime.update(40, None, 1)
  assert lost['route'] == second.preview() and not lost['controlValid']
  with pytest.raises(ConflictError):
    owner.select_route(0, state['revision'], True)
  with pytest.raises(ValidationError):
    owner.select_route(99, selected['revision'], True)
  assert NavigationOwner(tmp_path, runtime_source=lambda:None, transient_root=tmp_path/'boot').read()['favorites'][0]['name'] == 'Home'
