from cereal import log

from openpilot.starpilot.navigation.route_engine import Coordinate, NavigationRoute


def make_route() -> NavigationRoute:
  route_data = {
    "geometry": [
      {"latitude": 0.0, "longitude": 0.0},
      {"latitude": 0.0, "longitude": 0.001},
      {"latitude": 0.0, "longitude": 0.002},
      {"latitude": 0.001, "longitude": 0.002},
    ],
    "steps": [
      {
        "maneuver": "depart",
        "instruction": "Head east",
        "distance": 220.0,
        "duration": 20.0,
        "location": {"latitude": 0.0, "longitude": 0.0},
        "modifier": "straight",
        "bannerInstructions": [
          {
            "distanceAlongGeometry": 80.0,
            "primary": {
              "text": "Turn right",
              "type": "turn",
              "modifier": "right",
            },
            "secondary": {"text": "onto Market St"},
          },
        ],
      },
      {
        "maneuver": "turn",
        "instruction": "Turn right onto Market St",
        "distance": 111.0,
        "duration": 10.0,
        "location": {"latitude": 0.0, "longitude": 0.002},
        "modifier": "right",
        "bannerInstructions": [],
      },
      {
        "maneuver": "arrive",
        "instruction": "Your destination is on the right",
        "distance": 0.0,
        "duration": 0.0,
        "location": {"latitude": 0.001, "longitude": 0.002},
        "modifier": "right",
        "bannerInstructions": [],
      },
    ],
    "totalDistance": 331.0,
    "totalDuration": 30.0,
    "maxspeed": [
      {"speed": 35.0, "unit": "mph"},
      {"speed": 35.0, "unit": "mph"},
      {"speed": 25.0, "unit": "mph"},
      {"speed": 25.0, "unit": "mph"},
    ],
  }
  route = NavigationRoute.from_mapbox_route(route_data)
  assert route is not None
  return route


def test_route_progress_and_instruction_payload():
  route = make_route()
  progress = route.get_progress(Coordinate(0.0, 0.0015))

  assert progress is not None
  assert progress.current_step_index == 0
  assert progress.distance_remaining > 0
  assert route.upcoming_turn_modifier(progress, Coordinate(0.0, 0.0015), 20.0) == "right"

  payload = route.build_instruction_payload(progress)
  assert payload["maneuverPrimaryText"] == "Turn right"
  assert payload["maneuverSecondaryText"] == "onto Market St"
  assert payload["maneuverType"] == "turn"
  assert payload["maneuverModifier"] == "right"


def test_route_off_route_and_arrival_detection():
  route = make_route()
  off_route_progress = route.get_progress(Coordinate(0.0020, 0.0010))
  misaligned_progress = route.get_progress(Coordinate(0.0, 0.0015))
  arrive_progress = route.get_progress(Coordinate(0.0010, 0.0020))

  assert off_route_progress is not None
  assert misaligned_progress is not None
  assert arrive_progress is not None
  assert route.off_route_distance_exceeded(off_route_progress, 10.0)
  assert route.route_bearing_misaligned(misaligned_progress.closest_segment_index, 270.0, 10.0)
  assert route.arrived(arrive_progress, 0.5)


def test_route_progress_projects_onto_segments_for_destination_step():
  route = make_route()
  progress = route.get_progress(Coordinate(0.00098, 0.0020))

  assert progress is not None
  assert progress.next_step is not None
  assert progress.next_step.maneuver == "arrive"
  assert progress.distance_remaining <= 5.0
  assert route.arrived(progress, 0.5)


def test_route_bearing_misaligned_catches_ninety_degree_wrong_turn():
  route = make_route()
  progress = route.get_progress(Coordinate(0.0, 0.0015))

  assert progress is not None
  assert route.route_bearing_misaligned(progress.closest_segment_index, 0.0, 6.0)


def test_lane_payload_uses_capnp_enum_names():
  route_data = {
    "geometry": [
      {"latitude": 0.0, "longitude": 0.0},
      {"latitude": 0.0, "longitude": 0.001},
      {"latitude": 0.0, "longitude": 0.002},
    ],
    "steps": [
      {
        "maneuver": "turn",
        "instruction": "Keep left",
        "distance": 120.0,
        "duration": 12.0,
        "location": {"latitude": 0.0, "longitude": 0.001},
        "modifier": "slight left",
        "bannerInstructions": [
          {
            "distanceAlongGeometry": 80.0,
            "primary": {
              "text": "Keep left",
              "type": "turn",
              "modifier": "slight left",
            },
            "sub": {
              "components": [
                {
                  "type": "lane",
                  "active": True,
                  "directions": ["straight", "slight left"],
                  "active_direction": "slight left",
                },
              ],
            },
          },
        ],
      },
    ],
    "totalDistance": 120.0,
    "totalDuration": 12.0,
  }

  route = NavigationRoute.from_mapbox_route(route_data)
  assert route is not None
  progress = route.get_progress(Coordinate(0.0, 0.0005))
  assert progress is not None

  payload = route.build_instruction_payload(progress)
  msg = log.Event.new_message()
  msg.init("navInstruction")
  msg.navInstruction.lanes = payload["lanes"]

  assert len(msg.navInstruction.lanes) == 1
  assert list(msg.navInstruction.lanes[0].directions) == [
    log.NavInstruction.Direction.straight,
    log.NavInstruction.Direction.slightLeft,
  ]
  assert msg.navInstruction.lanes[0].activeDirection == log.NavInstruction.Direction.slightLeft
