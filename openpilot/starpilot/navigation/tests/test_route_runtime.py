from concurrent.futures import Future
import time
from types import SimpleNamespace

import pytest

from openpilot.starpilot.navigation.owner import NavigationOwner
from openpilot.starpilot.navigation.route_engine import NavigationRoute, project, distance
from openpilot.starpilot.navigation.runtime import RouteRuntime, location, publish_status


@pytest.fixture
def route():
  return NavigationRoute({'distance': 1112., 'duration': 100., 'geometry': {'coordinates': [[0., 0.], [.01, 0.]]}, 'legs': [{'steps': [
    {'distance': 1112., 'duration': 100., 'maneuver': {'type': 'depart', 'instruction': 'Head east'}, 'bannerInstructions': [
      {'primary': {'type': 'turn', 'modifier': 'right', 'text': 'Turn right on First Street'}}]},
    {'distance': 0., 'duration': 0., 'maneuver': {'type': 'arrive', 'instruction': 'You have arrived'}}]}]})


def test_route_interpolation_preserves_distance_and_advice(route):
  progress = route.progress((.005, 0.), 5., 90.)
  assert abs(progress.instruction['distanceMeters'] - 556.) < .01
  assert progress.instruction['text'] == 'Turn right on First Street'
  assert not progress.off_route and not progress.arrived
  assert route.progress((.005, 0.), 5., 270.).off_route
  assert route.progress((.01, 0.), 0.).arrived
  assert project((0, 0), (0, 0), (0, .001))[0] == 0
  assert distance((0, 0), (0, .001)) == pytest.approx(111.195, abs=.01)


class Executor:
  def __init__(self):
    self.jobs = []
  def submit(self, *args):
    future = Future()
    self.jobs.append(future)
    return future


def configured(tmp_path):
  owner = NavigationOwner(tmp_path, runtime_source=lambda: None)
  settings = owner.configure({'enabled': True, 'token': 'pk.test'}, '0', True)
  owner.select({'name': 'Destination', 'longitude': .01, 'latitude': 0.}, settings['revision'], True)
  return owner


def test_generation_discard_and_current_drive_control(tmp_path, route):
  owner, executor = configured(tmp_path), Executor()
  runtime = RouteRuntime(owner, engine=SimpleNamespace(fetch=None), executor=executor)
  assert runtime.update(10_000_000_000, (9_999_000_000, (0., 0.), 5., 90.), 9_000_000_000)['status'] == 'routing'
  owner.clear(owner.read()['revision'], True)
  executor.jobs[0].set_result(route)
  assert runtime.update(11_000_000_000, (10_999_000_000, (0., 0.), 5., 90.), 9_000_000_000)['status'] == 'noDestination'
  assert runtime.route is None
  owner.select({'name': 'Destination', 'longitude': .01, 'latitude': 0.}, owner.read()['revision'], True)
  runtime.update(12_000_000_000, (11_999_000_000, (0., 0.), 5., 90.), 9_000_000_000)
  executor.jobs[1].set_result(route)
  result = runtime.update(13_000_000_000, (12_999_000_000, (0., 0.), 5., 90.), 9_000_000_000)
  assert result['status'] == 'guiding' and result['controlValid']
  result = runtime.update(14_000_000_000, None, 9_000_000_000)
  assert result['status'] == 'waitingForLocation' and not result['controlValid']
  result = runtime.update(15_000_000_000, (14_999_000_000, (0., 0.), 5., 90.), 14_000_000_000)
  assert result['status'] == 'routing' and not result['controlValid']


def test_route_failure_backoff_and_no_parallel_requests(tmp_path):
  executor = Executor()
  runtime = RouteRuntime(configured(tmp_path), engine=SimpleNamespace(fetch=None), executor=executor)
  runtime.update(10, (9, (0., 0.), 5., 90.), 1)
  for now in range(11, 20):
    runtime.update(now, (now, (0., 0.), 5., 90.), 1)
  assert len(executor.jobs) == 1
  executor.jobs[0].set_exception(ValueError('invalid route'))
  assert runtime.update(20, (19, (0., 0.), 5., 90.), 1)['status'] == 'routeUnavailable'
  assert len(executor.jobs) == 1


def test_location_requires_fix_accuracy_and_freshness():
  gps = SimpleNamespace(source='qcomdiag', latitude=0., longitude=0., speed=1., bearingDeg=0., horizontalAccuracy=5., hasFix=True)
  class SM(dict):
    valid = {'gpsLocation': True, 'gpsLocationExternal': True}
    logMonoTime = {'gpsLocation': 10_000_000_000, 'gpsLocationExternal': 9_000_000_000}
  sm = SM(gpsLocation=gps, gpsLocationExternal=SimpleNamespace(**{**vars(gps), 'source': 'ublox'}))
  sm.valid['gpsLocationExternal'] = False
  assert location(sm, 11_000_000_000)[0] == 10_000_000_000
  assert location(sm, 13_000_000_000) is None
  gps.horizontalAccuracy = 30.
  assert location(sm, 11_000_000_000) is None


def test_steps_without_banner_describe_next_maneuver_not_previous_turn():
  route = NavigationRoute({'distance': 1112., 'duration': 100.,
                           'geometry': {'coordinates': [[0., 0.], [.005, 0.], [.01, 0.]]},
                           'legs': [{'steps': [
                             {'distance': 556., 'duration': 50., 'maneuver': {'type': 'depart', 'instruction': 'Head east'}},
                             {'distance': 556., 'duration': 50., 'maneuver': {'type': 'turn', 'modifier': 'right', 'instruction': 'Turn right'}},
                             {'distance': 0., 'duration': 0., 'maneuver': {'type': 'arrive', 'instruction': 'Destination'}}]}]})
  first = route.progress((.004, 0.), 5.)
  after_turn = route.progress((.006, 0.), 5.)
  assert first.instruction['maneuverType'] == 'turn'
  assert after_turn.instruction['maneuverType'] == 'arrive'


def test_favorite_edits_preserve_inflight_and_guiding_route(tmp_path, route):
  owner, executor = configured(tmp_path), Executor()
  runtime = RouteRuntime(owner, engine=SimpleNamespace(fetch=None), executor=executor)
  position = (9, (.001, 0.), 5., 90.)
  runtime.update(10, position, 1)
  favorite = {'name': 'Home', 'longitude': .02, 'latitude': .01}
  owner.favorite(favorite, owner.read()['revision'], True)
  executor.jobs[0].set_result(route)
  result = runtime.update(11, position, 1)
  assert result['status'] == 'guiding' and len(executor.jobs) == 1
  assert result['revision'] == owner.read()['revision']
  identity = owner.read()['favorites'][0]['id']
  owner.remove_favorite(identity, owner.read()['revision'], True)
  result = runtime.update(12, position, 1)
  assert result['status'] == 'guiding' and len(executor.jobs) == 1
  assert runtime.route is route and result['revision'] == owner.read()['revision']
  owner.configure({'token': 'pk.replaced'}, owner.read()['revision'], True)
  assert runtime.update(13, position, 1)['status'] == 'routing'
  assert len(executor.jobs) == 2


def test_published_navigation_reaches_status_and_control_consumers(tmp_path, route):
  from openpilot.cereal import messaging
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.starpilot.navigation.intent import current_instruction
  from openpilot.starpilot.navigation.status import NavigationStatusSource

  with OpenpilotPrefix():
    services = ['starpilotNavigation', 'deviceState', 'carState', 'carControl']
    sm = messaging.SubMaster(services)
    publisher = messaging.PubMaster(['starpilotNavigation'])
    receiver = messaging.sub_sock('starpilotNavigation', timeout=1000)
    status = NavigationStatusSource()
    status.sm = sm
    now = time.monotonic_ns()
    drive = now - 1_000_000_000
    executor = Executor()
    runtime = RouteRuntime(configured(tmp_path), engine=SimpleNamespace(fetch=None), executor=executor)
    position = (now, (.001, 0.), 5., 90.)
    runtime.update(now, position, drive)
    executor.jobs[0].set_result(route)

    for active_drive in (drive, 0):
      if not active_drive:
        runtime.update(now, position, 0)
        executor.jobs[-1].set_result(route)
      value = runtime.update(now, position, active_drive)
      publish_status(publisher, value)
      received = messaging.recv_one(receiver)
      assert received is not None and received.valid
      assert received.starpilotNavigation.navigation.controlValid is bool(active_drive)

      device = messaging.new_message('deviceState', valid=True)
      device.deviceState.started, device.deviceState.startedMonoTime = bool(active_drive), active_drive
      cs = messaging.new_message('carState', valid=True)
      cs.carState.canValid, cs.carState.gearShifter = True, 'drive'
      cc = messaging.new_message('carControl', valid=True)
      sm.update_msgs(time.monotonic(), [received, device, cs, cc])
      snapshot = status.snapshot()
      assert snapshot is not None and snapshot['status'] == 'guiding'
      instruction = current_instruction(sm, time.monotonic_ns())
      assert (instruction is not None) is bool(active_drive)


def saved_origin_runtime(tmp_path, monkeypatch):
  # These routing tests do not need the native Params library or boot-specific IPC paths.
  monkeypatch.setattr(NavigationOwner, '_is_metric', lambda self: True)
  owner = NavigationOwner(tmp_path, runtime_source=lambda: None, transient_root=tmp_path / 'runtime')
  settings = owner.configure({'enabled': True, 'token': 'pk.test'}, '0', True)
  owner.select({'name': 'Destination', 'longitude': .01, 'latitude': 0.}, settings['revision'], True)
  executor = Executor()
  executor.calls = []
  submit = executor.submit
  def record_submit(*args):
    executor.calls.append(args)
    return submit(*args)
  executor.submit = record_submit
  return owner, executor, RouteRuntime(owner, engine=SimpleNamespace(fetch=None), executor=executor)


def test_saved_origin_preview_without_live_guidance(tmp_path, monkeypatch, route):
  owner, executor, runtime = saved_origin_runtime(tmp_path, monkeypatch)
  assert runtime.update(10, None, 1)['status'] == 'waitingForLocation'
  assert not executor.jobs
  owner.position_store.record({'longitude': 0., 'latitude': 0., 'bearing': 90.})
  assert runtime.update(11, None, 1)['status'] == 'routing'
  assert executor.calls[0][2] == (0., 0.)
  executor.jobs[0].set_result(route)
  preview = runtime.update(12, None, 1)
  assert preview['route'] == route.preview()
  assert preview['status'] == 'waitingForLocation'
  assert preview['locationMonoTime'] == 0 and not preview['controlValid']
  assert preview['instruction'] == {} and preview['nextManeuver'] == {}
  assert owner.route_options(owner.read()['revision'])[0]['distanceMeters'] == route.total_distance
  owner.runtime_source = lambda: {**preview, 'instruction': None}
  snapshot = owner.snapshot()
  assert snapshot['route'] and snapshot['location']['lastKnown']
  assert snapshot['location']['validForMs'] == 0 and snapshot['instruction'] is None
  for now in range(13, 20):
    assert runtime.update(now, None, 1)['route'] == route.preview()
  assert len(executor.jobs) == 1


@pytest.mark.parametrize('completed', [False, True])
def test_live_fix_replaces_saved_origin_request(tmp_path, monkeypatch, route, completed):
  owner, executor, runtime = saved_origin_runtime(tmp_path, monkeypatch)
  owner.position_store.record({'longitude': 0., 'latitude': 0.})
  runtime.update(10, None, 1)
  if completed:
    executor.jobs[0].set_result(route)
    runtime.update(11, None, 1)
  live = (12, (.001, 0.), 5., 90.)
  result = runtime.update(12, live, 1)
  assert not result['controlValid'] and result['route'] == []
  if not completed:
    assert len(executor.jobs) == 1
    executor.jobs[0].set_result(route)
    result = runtime.update(13, live, 1)
    assert not result['controlValid'] and result['route'] == []
  assert len(executor.jobs) == 2 and executor.calls[1][2] == (.001, 0.)
  executor.jobs[1].set_result(route)
  result = runtime.update(14, live, 1)
  assert result['status'] == 'guiding' and result['controlValid']


def test_saved_origin_failure_backoff_and_destination_change(tmp_path, monkeypatch, route):
  owner, executor, runtime = saved_origin_runtime(tmp_path, monkeypatch)
  owner.position_store.record({'longitude': 0., 'latitude': 0.})
  runtime.update(10, None, 0)
  executor.jobs[0].set_exception(ValueError('route unavailable'))
  assert runtime.update(11, None, 0)['status'] == 'routeUnavailable'
  runtime.update(12, None, 0)
  assert len(executor.jobs) == 1
  runtime.update(30_000_000_012, None, 0)
  assert len(executor.jobs) == 2
  owner.clear(owner.read()['revision'], True)
  executor.jobs[1].set_result(route)
  result = runtime.update(30_000_000_013, None, 0)
  assert result['status'] == 'noDestination' and result['route'] == []
