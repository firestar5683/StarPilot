import json
from types import SimpleNamespace

import pytest

from openpilot.starpilot.navigation.navigationd import Navigationd
from openpilot.starpilot.navigation.route_engine import Coordinate, NavigationRoute
from openpilot.starpilot.navigation.test_route_engine import make_route


@pytest.mark.parametrize("change", [
  {"updatedAtMonotonic": None}, {"updatedAtMonotonic": 0}, {"updatedAtMonotonic": 101},
  {"updatedAtMonotonic": float("nan")}, {"updatedAtMonotonic": "bad"},
  {"latitude": 91}, {"longitude": 181}, {"latitude": "bad"},
  {"latitude": True}, {"hasFix": "false"}, {"speed": float("inf")}, {"speed": "bad"},
])
def test_invalid_location_fails_closed(monkeypatch, change):
  monkeypatch.setattr("openpilot.starpilot.navigation.navigationd.monotonic", lambda: 100.0)
  state = {"latitude": 1.0, "longitude": 1.0, "bearing": 90.0, "speed": 10.0,
           "hasFix": True, "updatedAtMonotonic": 100.0, **change}
  nav = Navigationd.__new__(Navigationd)
  nav._last_position = Coordinate(1.0, 1.0)
  nav.params_memory = SimpleNamespace(get=lambda *a, **kw: json.dumps(state))
  assert nav._update_location() == (False, 0.0)
  assert nav._last_position is None


def test_final_step_clears_destination_after_arrival():
  route = make_route()
  progress = route.get_progress(route.geometry[-1])
  nav = Navigationd.__new__(Navigationd)
  nav._arrival_started_at = 10.0
  nav._off_route_started_at = None
  nav._bearing_misaligned_started_at = None
  cleared = []
  nav._clear_route = lambda **kw: cleared.append(kw)
  nav._maybe_recompute(route, {"place_name": "end"}, progress, {"now": 16.0})
  assert cleared == [{"remove_destination": True}]


def test_projection_at_destination_is_not_arrival_when_far_away():
  route = make_route()
  progress = route.get_progress(Coordinate(0.01, 0.002))
  assert progress is not None
  assert not route.arrived(progress, 0.0)


def test_empty_banner_does_not_repeat_completed_turn():
  route = make_route()
  progress = route.get_progress(Coordinate(0.0005, 0.002))
  assert progress is not None
  payload = route.build_instruction_payload(progress)
  assert payload["maneuverType"] == "arrive"
  assert payload["maneuverPrimaryText"] == "Your destination is on the right"


def loop_route():
  geometry = [Coordinate(1, 1), Coordinate(1, 1.001), Coordinate(1.001, 1.001),
              Coordinate(1, 1), Coordinate(1, 0.999)]
  steps = []
  for index, point in enumerate(geometry):
    steps.append({"location": vars(point), "maneuver": "arrive" if index == 4 else "turn",
                  "distance": point.distance_to(geometry[index + 1]) if index < 4 else 0,
                  "duration": 10 if index < 4 else 0, "modifier": "left"})
  return NavigationRoute.from_mapbox_route({"geometry": [vars(p) for p in geometry], "steps": steps,
                                           "totalDistance": sum(s["distance"] for s in steps), "totalDuration": 40})


def test_repeated_step_location_keeps_route_order():
  route = loop_route()
  assert route.steps[3].cumulative_distance > route.steps[2].cumulative_distance


def test_ambiguous_loop_position_does_not_publish_a_guessed_turn():
  route = loop_route()
  # No temporal or heading evidence distinguishes these two visits.
  assert route.get_progress(route.geometry[0]) is None
