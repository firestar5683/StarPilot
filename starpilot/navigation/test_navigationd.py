import pytest
from types import SimpleNamespace

from openpilot.starpilot.navigation.navigationd import Navigationd
from openpilot.starpilot.navigation.route_engine import Coordinate


@pytest.fixture
def pending_navigation(monkeypatch):
  from openpilot.starpilot.navigation import navigationd as nav_module
  callbacks = []

  class Params:
    def __init__(self, *args, **kwargs):
      self.values = {"MapboxSecretKey": "test-token"}

    def get(self, key, **kwargs):
      return self.values.get(key)

    def remove(self, key):
      self.values.pop(key, None)

    def put_nonblocking(self, key, value):
      self.values[key] = value

  monkeypatch.setattr(nav_module, "Params", Params)
  monkeypatch.setattr(nav_module.messaging, "PubMaster", lambda *args: None)
  monkeypatch.setattr(nav_module.threading, "Thread", lambda *, target, daemon: SimpleNamespace(start=lambda: callbacks.append(target)))
  navigation = Navigationd(route_engine=SimpleNamespace(fetch_route=lambda *args: object()))
  navigation._last_position = Coordinate(1.0, 1.0)
  return navigation, callbacks


def destination(name):
  return {"place_name": name, "latitude": 1.0, "longitude": 2.0}


def test_cancel_rejects_pending_route(pending_navigation):
  navigation, callbacks = pending_navigation
  navigation._maybe_update_route(destination("A"))
  navigation._maybe_update_route(None)
  callbacks.pop(0)()
  assert navigation._snapshot_route()[0] is None


def test_destination_change_rejects_pending_route(pending_navigation):
  navigation, callbacks = pending_navigation
  navigation._maybe_update_route(destination("A"))
  navigation._maybe_update_route(destination("B"))
  callbacks.pop(0)()
  assert navigation._snapshot_route()[0] is None
  navigation._maybe_update_route(destination("B"))
  callbacks.pop(0)()
  assert navigation._snapshot_route()[1] == destination("B")


def test_destination_change_clears_old_route_while_waiting(pending_navigation):
  navigation, callbacks = pending_navigation
  navigation._maybe_update_route(destination("A"))
  callbacks.pop(0)()
  navigation.params_memory.values["NavInstructionState"] = {"valid": True}
  route, _, _ = navigation._maybe_update_route(destination("B"))
  assert route is None
  assert navigation.params_memory.get("NavInstructionState") is None


def test_fetch_exception_allows_retry(pending_navigation):
  navigation, callbacks = pending_navigation

  def fail(*args):
    raise ValueError("Invalid route response")

  navigation.route_engine.fetch_route = fail
  navigation._maybe_update_route(destination("A"))
  callbacks.pop(0)()
  assert not navigation._route_fetch_inflight
  navigation.route_engine.fetch_route = lambda *args: object()
  navigation._maybe_update_route(destination("A"))
  callbacks.pop(0)()
  assert navigation._snapshot_route()[0] is not None


def test_navigation_state_refreshes_even_when_instruction_is_unchanged(monkeypatch):
  now = [100.0]
  monkeypatch.setattr("openpilot.starpilot.navigation.navigationd.monotonic", lambda: now[0])
  writes = []
  navigationd = Navigationd.__new__(Navigationd)
  navigationd.params_memory = SimpleNamespace(put_nonblocking=lambda key, value: writes.append(value))
  payload = {"maneuverType": "turn", "maneuverModifier": "right", "maneuverDistance": 10.0}
  navigationd._publish_nav_state(object(), object(), True, payload)
  now[0] = 101.0
  navigationd._publish_nav_state(object(), object(), True, payload)
  assert len(writes) == 2
  assert [state["updatedAtMonotonic"] for state in writes] == [100.0, 101.0]


def test_navigation_restart_clears_previous_process_instruction():
  removed = []
  navigationd = Navigationd.__new__(Navigationd)
  navigationd.params_memory = SimpleNamespace(remove=removed.append)
  navigationd._publish_nav_state(None, None, False)
  assert removed == ["NavInstructionState"]


class CountingParams:
  def __init__(self):
    self.use_vienna_reads = 0

  def get(self, key: str, *, encoding: str):
    assert key == "NavDestination"
    return None

  def get_bool(self, key: str) -> bool:
    assert key == "UseVienna"
    self.use_vienna_reads += 1
    return True


class CountingRoute:
  def __init__(self):
    self.payload_builds = 0

  def build_instruction_payload(self, progress, *, use_vienna_sign: bool):
    assert progress == "progress"
    assert use_vienna_sign
    self.payload_builds += 1
    return {"payload": self.payload_builds}


class StopLoop(Exception):
  pass


class Recorder:
  def __init__(self, return_value=None):
    self.calls = []
    self.return_value = return_value

  def __call__(self, *args):
    self.calls.append(args)
    return self.return_value


class Ratekeeper:
  def keep_time(self):
    raise StopLoop


@pytest.mark.parametrize("off_route,misaligned", [(False, False), (True, False), (False, True)])
@pytest.mark.parametrize("route_replaced", [False, True])
def test_run_only_publishes_instruction_for_a_matching_route(off_route, misaligned, route_replaced):
  navigationd = Navigationd.__new__(Navigationd)
  route = CountingRoute()
  updated_route = CountingRoute() if route_replaced else route
  params = CountingParams()
  navigationd.params = params
  navigationd.rk = Ratekeeper()
  navigationd._update_location = Recorder((True, 0.0))
  navigationd._maybe_update_route = Recorder((route, None, 0))
  def build_progress(candidate, *args):
    matches = candidate is updated_route
    return "progress", {"offRoute": off_route if matches else False, "misaligned": misaligned if matches else False}

  navigationd._build_progress = build_progress
  navigationd._maybe_recompute = Recorder()
  navigationd._snapshot_route = Recorder((updated_route, None, 0))
  navigationd._publish_nav_instruction = Recorder()
  navigationd._publish_nav_state = Recorder()
  navigationd._publish_nav_route_if_needed = Recorder()

  with pytest.raises(StopLoop):
    navigationd.run()

  valid = not (off_route or misaligned)
  assert updated_route.payload_builds == int(valid)
  assert params.use_vienna_reads == int(valid)
  assert navigationd._publish_nav_instruction.calls[0][2] == valid
  assert navigationd._publish_nav_instruction.calls[0][0] is updated_route
  assert navigationd._publish_nav_state.calls[0][2] == valid
  instruction_payload = navigationd._publish_nav_instruction.calls[0][3]
  state_payload = navigationd._publish_nav_state.calls[0][3]
  assert instruction_payload is state_payload
