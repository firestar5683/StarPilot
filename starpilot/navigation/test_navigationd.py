import pytest

from openpilot.starpilot.navigation.navigationd import Navigationd


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


def test_run_builds_one_payload_for_both_navigation_publishers():
  navigationd = Navigationd.__new__(Navigationd)
  route = CountingRoute()
  params = CountingParams()
  navigationd.params = params
  navigationd.rk = Ratekeeper()
  navigationd._update_location = Recorder((True, 0.0))
  navigationd._maybe_update_route = Recorder((route, None, 0))
  navigationd._build_progress = Recorder(("progress", None))
  navigationd._maybe_recompute = Recorder()
  navigationd._snapshot_route = Recorder((route, None, 0))
  navigationd._publish_nav_instruction = Recorder()
  navigationd._publish_nav_state = Recorder()
  navigationd._publish_nav_route_if_needed = Recorder()

  with pytest.raises(StopLoop):
    navigationd.run()

  assert route.payload_builds == 1
  assert params.use_vienna_reads == 1
  instruction_payload = navigationd._publish_nav_instruction.calls[0][3]
  state_payload = navigationd._publish_nav_state.calls[0][3]
  assert instruction_payload is state_payload
