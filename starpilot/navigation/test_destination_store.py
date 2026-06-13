import json

from openpilot.starpilot.navigation.destination_store import (
  normalize_destination_payload,
  update_recent_destinations,
)


def test_normalize_destination_payload_requires_name_and_coordinates():
  payload = {
    "name": "123 Main St",
    "latitude": "41.881832",
    "longitude": "-87.623177",
  }

  assert normalize_destination_payload(payload) == {
    "name": "123 Main St",
    "place_name": "123 Main St",
    "latitude": 41.881832,
    "longitude": -87.623177,
  }
  assert normalize_destination_payload({"name": "Missing coords"}) is None


def test_recent_destinations_dedupe_and_cap():
  existing = json.dumps([
    {"place_name": "Old 1"},
    {"place_name": "Old 2"},
    {"place_name": "Home"},
    {"place_name": "Old 3"},
    {"place_name": "Old 4"},
    {"place_name": "Old 5"},
    {"place_name": "Old 6"},
    {"place_name": "Old 7"},
    {"place_name": "Old 8"},
    {"place_name": "Old 9"},
  ])

  updated = update_recent_destinations(existing, {
    "name": "Home",
    "latitude": 1.0,
    "longitude": 2.0,
  })

  assert updated[0]["place_name"] == "Home"
  assert len(updated) == 10
  assert [entry["place_name"] for entry in updated].count("Home") == 1
  assert updated[-1]["place_name"] == "Old 9"
