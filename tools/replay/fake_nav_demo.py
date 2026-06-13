#!/usr/bin/env python3

import argparse
import json
import time
from itertools import cycle

from cereal import log, messaging
from openpilot.common.params import Params, UnknownKeyName


ROUTE_COORDS = [
  {"latitude": 0.0, "longitude": 0.0},
  {"latitude": 0.0, "longitude": 0.01},
  {"latitude": 0.01, "longitude": 0.02},
]


SCENARIOS = [
  {
    "primary": "Turn right onto Main St",
    "secondary": "Then keep left",
    "distance": 120.0,
    "type": "turn",
    "modifier": "right",
    "next_type": "fork",
    "next_modifier": "slightLeft",
  },
  {
    "primary": "Turn left onto Pine Ave",
    "secondary": "Then merge right",
    "distance": 180.0,
    "type": "turn",
    "modifier": "left",
    "next_type": "merge",
    "next_modifier": "right",
  },
  {
    "primary": "Keep right to stay on I-90",
    "secondary": "Then continue straight",
    "distance": 260.0,
    "type": "fork",
    "modifier": "slightRight",
    "next_type": "continue",
    "next_modifier": "straight",
  },
  {
    "primary": "Keep left to stay on I-90",
    "secondary": "Then take exit 14A",
    "distance": 210.0,
    "type": "fork",
    "modifier": "slightLeft",
    "next_type": "off ramp",
    "next_modifier": "right",
  },
  {
    "primary": "Take exit 14A",
    "secondary": "Then turn sharp right",
    "distance": 340.0,
    "type": "off ramp",
    "modifier": "right",
    "next_type": "turn",
    "next_modifier": "sharpRight",
  },
  {
    "primary": "Continue straight for 1 mile",
    "secondary": "Then enter the roundabout",
    "distance": 1600.0,
    "type": "continue",
    "modifier": "straight",
    "next_type": "roundabout",
    "next_modifier": "right",
  },
  {
    "primary": "Enter the roundabout",
    "secondary": "Take the second exit",
    "distance": 90.0,
    "type": "roundabout",
    "modifier": "right",
    "next_type": "turn",
    "next_modifier": "left",
  },
  {
    "primary": "Turn sharp left onto Oak St",
    "secondary": "Then make a U-turn",
    "distance": 75.0,
    "type": "turn",
    "modifier": "sharpLeft",
    "next_type": "continue",
    "next_modifier": "uturn",
  },
  {
    "primary": "Make a U-turn",
    "secondary": "Then arrive at destination",
    "distance": 60.0,
    "type": "continue",
    "modifier": "uturn",
    "next_type": "arrive",
    "next_modifier": "right",
  },
  {
    "primary": "Arrive at destination",
    "secondary": "Destination is on the right",
    "distance": 25.0,
    "type": "arrive",
    "modifier": "right",
    "next_type": "turn",
    "next_modifier": "straight",
  },
]


def build_nav_state(params_memory: Params, scenario: dict) -> None:
  params_memory.put_nonblocking("NavInstructionState", {
    "valid": True,
    "maneuverModifier": str(scenario["modifier"]),
    "maneuverType": str(scenario["type"]),
    "maneuverPrimaryText": str(scenario["primary"]),
    "maneuverSecondaryText": str(scenario["secondary"]),
    "maneuverDistance": float(scenario["distance"]),
    "nextManeuverType": str(scenario["next_type"]),
    "nextManeuverModifier": str(scenario["next_modifier"]),
    "nextManeuverDistance": float(scenario["distance"] + 220.0),
  })


def build_instruction(pm: messaging.PubMaster, scenario: dict) -> None:
  msg = messaging.new_message("navInstruction")
  msg.valid = True

  nav = msg.navInstruction
  nav.maneuverPrimaryText = scenario["primary"]
  nav.maneuverSecondaryText = scenario["secondary"]
  nav.maneuverDistance = scenario["distance"]
  nav.maneuverType = scenario["type"]
  nav.maneuverModifier = scenario["modifier"]
  nav.distanceRemaining = max(scenario["distance"] * 8, 400.0)
  nav.timeRemaining = max(scenario["distance"] / 10.0, 20.0)
  nav.timeRemainingTypical = nav.timeRemaining
  nav.showFull = True
  nav.speedLimit = 31.2928
  nav.speedLimitSign = log.NavInstruction.SpeedLimitSign.mutcd
  nav.allManeuvers = [
    {"distance": scenario["distance"], "type": scenario["type"], "modifier": scenario["modifier"]},
    {"distance": scenario["distance"] + 220.0, "type": scenario["next_type"], "modifier": scenario["next_modifier"]},
  ]

  pm.send("navInstruction", msg)


def build_route(pm: messaging.PubMaster) -> None:
  msg = messaging.new_message("navRoute")
  msg.valid = True
  msg.navRoute.coordinates = ROUTE_COORDS
  pm.send("navRoute", msg)


def build_destination(scenario: dict) -> dict:
  return {
    "place_name": str(scenario["primary"]),
    "latitude": float(ROUTE_COORDS[-1]["latitude"]),
    "longitude": float(ROUTE_COORDS[-1]["longitude"]),
    "routeId": "fake-nav-demo",
  }


def main() -> None:
  parser = argparse.ArgumentParser(description="Publish fake navigation instructions for desktop onroad replay.")
  parser.add_argument("--hold-seconds", type=float, default=3.0, help="How long each maneuver stays active.")
  parser.add_argument("--publish-interval", type=float, default=0.25, help="Seconds between navInstruction publishes.")
  args = parser.parse_args()

  pm = messaging.PubMaster(["navInstruction", "navRoute"])
  params = Params()
  params_memory = Params(memory=True)
  try:
    params_memory.put_bool("NavInstructionCollapsed", False)
  except UnknownKeyName:
    pass

  scenario_cycle = cycle(SCENARIOS)
  current = next(scenario_cycle)
  params.put("NavDestination", json.dumps(build_destination(current)))
  next_switch = time.monotonic() + args.hold_seconds
  print(f"showing: {current['type']} / {current['modifier']} -> {current['next_type']} / {current['next_modifier']}", flush=True)

  try:
    while True:
      now = time.monotonic()
      if now >= next_switch:
        current = next(scenario_cycle)
        params.put("NavDestination", json.dumps(build_destination(current)))
        next_switch = now + args.hold_seconds
        print(f"showing: {current['type']} / {current['modifier']} -> {current['next_type']} / {current['next_modifier']}", flush=True)

      build_nav_state(params_memory, current)
      build_instruction(pm, current)
      build_route(pm)
      time.sleep(args.publish_interval)
  finally:
    params.remove("NavDestination")
    params_memory.remove("NavInstructionState")
    try:
      params_memory.remove("NavInstructionCollapsed")
    except UnknownKeyName:
      pass


if __name__ == "__main__":
  main()
