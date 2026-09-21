import json
from types import SimpleNamespace

import pytest

from openpilot.starpilot.navigation.location_state import gps_position_from_service, parse_location_state


class GPSMessages(dict):
  def __init__(self):
    super().__init__(gps=SimpleNamespace(latitude=1.0, longitude=1.0, bearingDeg=90.0, hasFix=True, unixTimestampMillis=100000))
    self.alive = {"gps": True}
    self.valid = {"gps": True}
    self.logMonoTime = {"gps": 100_000_000_000}


def test_cached_gps_message_cannot_renew_its_timestamp(monkeypatch):
  now = [100.0]
  monkeypatch.setattr("time.monotonic", lambda: now[0])
  messages = GPSMessages()
  first = gps_position_from_service(messages, "gps", 5.0)
  assert first["updatedAtMonotonic"] == 100.0
  now[0] = 102.5
  assert gps_position_from_service(messages, "gps", 5.0)["updatedAtMonotonic"] == 100.0
  now[0] = 102.501
  assert gps_position_from_service(messages, "gps", 5.0) is None
  messages.logMonoTime["gps"] = 102_501_000_000
  assert gps_position_from_service(messages, "gps", 5.0) is not None


@pytest.mark.parametrize("field", ["alive", "valid"])
def test_invalid_gps_service_is_not_published(monkeypatch, field):
  monkeypatch.setattr("time.monotonic", lambda: 100.0)
  messages = GPSMessages()
  getattr(messages, field)["gps"] = False
  assert gps_position_from_service(messages, "gps", 5.0) is None


@pytest.mark.parametrize("raw", [None, [], b"\xff", "null", "{", "[]", {"hasFix": False}])
def test_location_decoder_handles_invalid_storage(raw):
  assert parse_location_state(raw, now=100.0) is None


@pytest.mark.parametrize("encode", [lambda x: x, json.dumps, lambda x: json.dumps(x).encode()])
def test_valid_location_round_trip(monkeypatch, encode):
  monkeypatch.setattr("time.monotonic", lambda: 100.0)
  state = gps_position_from_service(GPSMessages(), "gps", 0.0)
  assert parse_location_state(encode(state), now=100.0) == state
