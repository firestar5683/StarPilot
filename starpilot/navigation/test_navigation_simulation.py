"""Deterministic host simulation of navigation publication and control hints.

These tests exercise route/GPS/Params boundaries, not vehicle dynamics or model
inference. All coordinates are synthetic.
"""
import itertools
import json
from types import SimpleNamespace

import pytest
from cereal import log

from openpilot.selfdrive.controls.lib.desire_helper import DesireHelper
from openpilot.selfdrive.controls.tests.test_navigation_desires import make_car_state, make_plan, make_toggles
from openpilot.selfdrive.controls.tests.test_starpilot_vcruise import make_sm, make_vcruise
from openpilot.starpilot.navigation import navigationd as nav_module
from openpilot.starpilot.navigation.location_state import gps_position_from_service
from openpilot.starpilot.navigation.route_engine import Coordinate, MapboxRouteEngine, NavigationRoute, parse_banner_instructions
from openpilot.starpilot.navigation.test_location_state import GPSMessages


class Params:
  def __init__(self):
    self.values = {}

  def get(self, key, **kwargs):
    value = self.values.get(key)
    return json.dumps(value) if "encoding" in kwargs and isinstance(value, dict) else value

  def put_nonblocking(self, key, value):
    self.values[key] = value

  def remove(self, key):
    self.values.pop(key, None)

  def get_bool(self, key):
    return bool(self.values.get(key))


def turn_route(direction="right"):
  geometry = [Coordinate(1, 1), Coordinate(1, 1.002), Coordinate(0.999 if direction == "right" else 1.001, 1.002)]
  steps = []
  for i, point in enumerate(geometry):
    steps.append({"location": vars(point), "maneuver": ["depart", "turn", "arrive"][i],
                  "instruction": ["Depart", f"Turn {direction}", "Arrive"][i], "modifier": direction,
                  "distance": point.distance_to(geometry[i + 1]) if i < 2 else 0.0, "duration": 20.0 if i < 2 else 0.0})
  return NavigationRoute.from_mapbox_route({"geometry": [vars(p) for p in geometry], "steps": steps,
                                           "totalDistance": sum(s["distance"] for s in steps), "totalDuration": 40.0})


class EndTick(Exception):
  pass


@pytest.fixture
def simulator(monkeypatch):
  clock = [100.0]
  monkeypatch.setattr("time.monotonic", lambda: clock[0])
  monkeypatch.setattr(nav_module, "monotonic", lambda: clock[0])
  monkeypatch.setattr(nav_module, "Params", lambda *a, **kw: Params())
  sent = {}
  monkeypatch.setattr(nav_module.messaging, "PubMaster", lambda *a: SimpleNamespace(send=lambda key, msg: sent.update({key: msg.to_dict()})))
  nav = nav_module.Navigationd()

  def stop():
    raise EndTick

  nav.rk = SimpleNamespace(keep_time=stop)
  nav._route = turn_route()
  dest = {"place_name": "Synthetic destination", "latitude": 0.999, "longitude": 1.002}
  nav._active_destination = dest
  nav.params.values["NavDestination"] = dest
  messages = GPSMessages()
  messages["gps"].longitude = 1.0019
  nav.params_memory.values["LastGPSPosition"] = gps_position_from_service(messages, "gps", 5.0)

  def tick():
    with pytest.raises(EndTick):
      nav.run()

  return SimpleNamespace(clock=clock, nav=nav, messages=messages, sent=sent, tick=tick)


def test_gps_loss_disables_both_navigation_consumers_and_recovers(simulator):
  sim = simulator
  helper = DesireHelper()
  helper.params_memory = sim.nav.params_memory
  planner, cruise = make_vcruise()
  planner.params_memory = sim.nav.params_memory
  toggles = make_toggles(lane_changes=False, nav_longitudinal_allowed=True, nav_lane_positioning_allowed=False)
  car = make_car_state(vEgo=5.0, rightBlinker=True)
  observed = []
  for i in range(101):
    sim.clock[0] = 100.0 + i / 20.0
    if i == 80:
      sim.messages.logMonoTime["gps"] = int(sim.clock[0] * 1e9)
    if i % 20 == 0:
      position = gps_position_from_service(sim.messages, "gps", 5.0)
      if position is not None:
        sim.nav.params_memory.values["LastGPSPosition"] = position
      sim.tick()
    helper.update(car, True, 0.0, make_plan(), toggles)
    target = cruise._get_nav_turn_control_target(20.0, make_sm(), toggles)
    observed.append((helper.desire, target))
  assert observed[0][0] == log.Desire.turnRight and 0 < observed[0][1] < 20
  assert all(desire == log.Desire.none and target == 0 for desire, target in observed[60:80])
  assert observed[80][0] == log.Desire.turnRight and 0 < observed[80][1] < 20


@pytest.mark.parametrize("fault", ["offroute", "heading", "cancel", "invalid_fix", "future_clock"])
def test_live_navigation_withholds_hints_on_fault(simulator, fault):
  sim = simulator
  sim.tick()
  assert sim.sent["navInstruction"]["valid"]
  gps = sim.nav.params_memory.values["LastGPSPosition"]
  if fault == "offroute":
    gps["latitude"] += 0.01
  elif fault == "heading":
    gps["bearing"] = 270.0
  elif fault == "cancel":
    sim.nav.params.remove("NavDestination")
  elif fault == "invalid_fix":
    gps["hasFix"] = False
  else:
    gps["updatedAtMonotonic"] += 10
  sim.tick()
  assert not sim.sent["navInstruction"]["valid"]
  assert sim.nav.params_memory.get("NavInstructionState") is None


def test_driver_turn_gates_for_both_directions():
  combinations = itertools.product(("left", "right"), (0.0, 5.0, 10.5, 12.0), ("matching", "opposite", "both", "none"), (False, True), (False, True))
  for direction, speed, signal, active, blindspot in combinations:
    route = turn_route(direction)
    progress = route.get_progress(Coordinate(1, 1.0019))
    payload = route.build_instruction_payload(progress)
    assert payload["maneuverModifier"] == direction
    helper = DesireHelper()
    helper._update_nav_params = lambda: None
    helper._nav_instruction_state = {"valid": True, **payload}
    left = signal == "both" or (signal == "matching" and direction == "left") or (signal == "opposite" and direction == "right")
    right = signal == "both" or (signal == "matching" and direction == "right") or (signal == "opposite" and direction == "left")
    car = make_car_state(vEgo=speed, leftBlinker=left, rightBlinker=right, standstill=speed == 0,
                         leftBlindspot=blindspot, rightBlindspot=blindspot)
    helper.update(car, active, 0.0, make_plan(), make_toggles(lane_changes=False, minimum_lane_change_speed=11.1))
    expected = log.Desire.none
    if active and signal == "matching" and 0 < speed < 11.1 and not blindspot:
      expected = log.Desire.turnLeft if direction == "left" else log.Desire.turnRight
    assert helper.desire == expected, (direction, speed, signal, active, blindspot)


@pytest.mark.parametrize("bad", [None, {}, "bad", [None], [{"primary": None}], [{"distanceAlongGeometry": "bad", "primary": {}}]])
def test_malformed_banners_do_not_crash_navigation(bad):
  assert parse_banner_instructions(bad, 10.0) is None


def test_unknown_speed_annotations_keep_geometry_alignment():
  route = turn_route()
  route.maxspeeds = [0.0, 10.0]
  assert route.get_progress(Coordinate(1, 1.0019)).current_speed_limit_ms == 0.0
  assert route.get_progress(Coordinate(0.9995, 1.002)).current_speed_limit_ms == 10.0


def test_mapbox_annotations_survive_response_conversion():
  route = turn_route()
  api_steps = [{"maneuver": {"type": step.maneuver, "instruction": step.instruction,
                             "location": [step.location.longitude, step.location.latitude], "modifier": step.modifier},
                "distance": step.distance, "duration": step.duration} for step in route.steps]
  api_route = {"distance": route.total_distance, "duration": route.total_duration,
               "geometry": {"coordinates": [[p.longitude, p.latitude] for p in route.geometry]},
               "legs": [{"steps": api_steps, "annotation": {"maxspeed": [{"unknown": True}, {"speed": 36, "unit": "km/h"}]}}]}
  requests = []

  def get(url, **kwargs):
    requests.append((url, kwargs))
    return SimpleNamespace(status_code=200, json=lambda: {"code": "Ok", "routes": [api_route]})

  result = MapboxRouteEngine(SimpleNamespace(get=get)).fetch_route("test-token", route.geometry[0],
                                                               vars(route.geometry[-1]), 90.0)
  assert result is not None
  assert result.get_progress(Coordinate(1, 1.0019)).current_speed_limit_ms == 0.0
  assert result.get_progress(Coordinate(0.9995, 1.002)).current_speed_limit_ms == 10.0
  assert requests[0][1]["params"]["bearings"] == "90,90;"
  assert requests[0][1]["timeout"] == 5


@pytest.mark.parametrize("status,body", [(403, {}), (429, {}), (200, {"code": "NoRoute"}), (200, {"code": "Ok", "routes": []})])
def test_failed_mapbox_response_does_not_produce_a_route(status, body):
  session = SimpleNamespace(get=lambda *a, **kw: SimpleNamespace(status_code=status, json=lambda: body))
  assert MapboxRouteEngine(session).fetch_route("test-token", Coordinate(1, 1), {"latitude": 2, "longitude": 2}) is None


def test_desktop_demo_instructions_refresh_and_expire(monkeypatch):
  from openpilot.starpilot.navigation.instruction_state import parse_instruction_state
  from openpilot.tools.replay.fake_nav_demo import SCENARIOS, build_nav_state
  now = [100.0]
  monkeypatch.setattr("time.monotonic", lambda: now[0])
  params = Params()
  for scenario in SCENARIOS:
    build_nav_state(params, scenario)
    assert parse_instruction_state(params.get("NavInstructionState"))
    now[0] += 3.0
    assert not parse_instruction_state(params.get("NavInstructionState"))


def test_arrival_clears_the_route_and_published_hints(simulator):
  sim = simulator
  for elapsed in range(7):
    sim.clock[0] = 100.0 + elapsed
    sim.nav.params_memory.values["LastGPSPosition"] = {
      "latitude": 0.999, "longitude": 1.002, "bearing": 180.0, "speed": 0.0,
      "hasFix": True, "updatedAtMonotonic": sim.clock[0],
    }
    sim.tick()
  assert sim.nav.params.get("NavDestination") is None
  assert sim.nav.params_memory.get("NavInstructionState") is None
  assert not sim.sent["navRoute"]["valid"]
  assert not sim.sent["navInstruction"]["valid"]


def test_ambiguous_position_resets_arrival_timer(simulator):
  from openpilot.starpilot.navigation.test_route_faults import loop_route
  sim = simulator
  sim.nav._route = loop_route()
  sim.nav._arrival_started_at = 90.0
  sim.nav.params_memory.values["LastGPSPosition"]["longitude"] = 1.0
  sim.tick()
  assert sim.nav._arrival_started_at is None
  assert sim.nav.params.get("NavDestination") is not None
  assert sim.nav.params_memory.get("NavInstructionState") is None


def test_published_lane_metadata_suppresses_ambiguous_edge_hint(simulator):
  sim = simulator
  payload = {"maneuverType": "fork", "maneuverModifier": "left", "maneuverDistance": 10.0, "lanes": [
    {"active": True, "directions": ["left"], "activeDirection": "left"},
    {"active": False, "directions": ["left", "straight"]},
    {"active": False, "directions": ["straight"]},
  ]}
  sim.nav._publish_nav_state(sim.nav._route, object(), True, payload)
  state = sim.nav.params_memory.get("NavInstructionState")
  assert state["sameSideLaneCount"] == 2 and state["activeLaneAtRoadEdge"] and state["hasSharedSameSideLane"]
  helper = DesireHelper()
  helper.params_memory = sim.nav.params_memory
  car = make_car_state(vEgo=10.0, steeringPressed=True, steeringTorque=1.0)
  assert helper._navigation_desire(car, True, make_plan(), make_toggles()) == log.Desire.none


def test_network_timeout_does_not_produce_a_route():
  import requests

  def timeout(*args, **kwargs):
    raise requests.Timeout

  engine = MapboxRouteEngine(SimpleNamespace(get=timeout))
  assert engine.fetch_route("test-token", Coordinate(1, 1), {"latitude": 2, "longitude": 2}) is None
