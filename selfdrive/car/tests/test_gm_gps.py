from types import SimpleNamespace

import pytest

from cereal import messaging
from openpilot.selfdrive.car.card import Car, GM_GPS_SOURCES


def sample():
  gps = messaging.new_message("gpsLocation", valid=True).gpsLocation
  gps.hasFix = True
  gps.latitude = 38.3
  gps.longitude = -85.7
  gps.source = "ublox"
  return dict(gps.to_dict(), timestamp_nanos=1)


@pytest.fixture
def selector():
  card = Car.__new__(Car)
  card._gm_gps = dict.fromkeys(source for source, _ in GM_GPS_SOURCES)
  card._gm_gps_had_fix = False
  card._last_car_gps_publish_monotonic = 0.0
  card.gps_pm = SimpleNamespace(sent=[])
  card.gps_pm.send = lambda service, message: card.gps_pm.sent.append((service, message))
  card.sm = SimpleNamespace(updated={"gpsLocation": False})
  card.CI = SimpleNamespace(CS=SimpleNamespace(get_car_gps_sources=dict))
  return card


@pytest.mark.parametrize("states,winner", [
  (("good", None, None), "device"),
  (("bad", "good", None), "pps"),
  (("stale", "good", None), "pps"),
  (("bad", "bad", "good"), "onstar"),
  (("good", "good", "good"), "device"),
  (("bad", "stale", None), None),
  (("stale", "stale", "good"), "onstar"),
  (("bad", "bad", "bad"), None),
  (("stale", "stale", "stale"), None),
])
def test_priority(selector, states, winner):
  for index, ((source, timeout), state) in enumerate(zip(GM_GPS_SOURCES, states, strict=True)):
    if state is not None:
      fix = sample() | {"latitude": 38.0 + index, "hasFix": state != "bad"}
      selector._gm_gps[source] = (fix, 10.0 - timeout - 0.01 if state == "stale" else 10.0)
  selector._publish_gm_gps(10.0)
  if winner is None:
    assert not selector.gps_pm.sent
  else:
    assert selector.gps_pm.sent[-1][1].gpsLocationExternal.latitude == selector._gm_gps[winner][0]["latitude"]


@pytest.mark.parametrize("source,timeout", [("device", 2.0), ("pps", 1.0), ("onstar", 2.5)])
def test_freshness_and_recovery(selector, source, timeout):
  selector._gm_gps[source] = (sample(), 10.0)
  selector._publish_gm_gps(10.0 + timeout)
  assert selector.gps_pm.sent[-1][1].valid
  selector._publish_gm_gps(10.01 + timeout)
  assert not selector.gps_pm.sent[-1][1].valid
  selector._gm_gps[source] = (sample(), 20.0)
  selector._publish_gm_gps(20.0)
  assert selector.gps_pm.sent[-1][1].valid


@pytest.mark.parametrize("source", ["device", "pps"])
def test_upward_recovery(selector, source):
  selector._gm_gps["onstar"] = (sample() | {"latitude": 40.0}, 10.0)
  selector._publish_gm_gps(10.0)
  assert selector.gps_pm.sent[-1][1].gpsLocationExternal.latitude == 40.0
  selector._gm_gps[source] = (sample(), 10.21)
  selector._publish_gm_gps(10.21)
  assert selector.gps_pm.sent[-1][1].gpsLocationExternal.latitude == 38.3


@pytest.mark.parametrize("changes,expected", [
  ({"latitude": float("nan")}, False), ({"longitude": float("inf")}, False),
  ({"latitude": 91}, False), ({"longitude": -181}, False), ({"longitude": 181}, False),
  ({"latitude": 0, "longitude": 0}, False), ({"speed": float("nan")}, False),
  ({"latitude": 0, "longitude": 10}, True), ({"latitude": 10, "longitude": 0}, True),
  ({"horizontalAccuracy": 500.0}, True),
])
def test_health(selector, changes, expected):
  selector._gm_gps = {source: (sample() | {"latitude": 40.0}, 10.0) for source, _ in GM_GPS_SOURCES}
  selector._gm_gps["device"] = (sample() | changes, 10.0)
  selector._publish_gm_gps(10.0)
  gps = selector.gps_pm.sent[-1][1].gpsLocationExternal
  assert gps.latitude == (selector._gm_gps["device"][0]["latitude"] if expected else 40.0)
  assert gps.source == ("ublox" if expected else "car")


@pytest.mark.parametrize("source", [source for source, _ in GM_GPS_SOURCES])
def test_selected_fix_fields_are_preserved(selector, source):
  fix = sample() | {"altitude": 123.0, "speed": 10.0, "vNED": [0.0, 10.0, 0.0], "bearingDeg": 90.0,
                    "horizontalAccuracy": 3.0, "verticalAccuracy": 5.0, "bearingAccuracyDeg": 2.0}
  if source == "device":
    selector._gm_gps[source] = (fix, 10.0)
  else:
    selector.CI.CS.get_car_gps_sources = lambda: {source: fix}
  selector._publish_gm_gps(10.0)
  service, message = selector.gps_pm.sent[-1]
  assert service == "gpsLocationExternal"
  assert message.valid
  expected = {key: value for key, value in fix.items() if key != "timestamp_nanos"}
  expected["source"] = "ublox" if source == "device" else "car"
  assert message.gpsLocationExternal.to_dict() == expected


@pytest.mark.parametrize("source", ["pps", "onstar"])
def test_can_cache_freshness_and_explicit_invalidation(selector, source):
  sources = {"pps": sample(), "onstar": sample() | {"latitude": 40.0}}
  selector.CI.CS.get_car_gps_sources = lambda: sources
  selector._publish_gm_gps(10.0)
  for timestamp in (1, 0):
    sources[source] = sources[source] | {"timestamp_nanos": timestamp}
    selector._publish_gm_gps(10.5)
    assert selector._gm_gps[source][1] == 10.0
  sources[source] = sources[source] | {"timestamp_nanos": 2}
  selector._publish_gm_gps(10.6)
  assert selector._gm_gps[source][1] == 10.6
  sources[source] = None
  selector._publish_gm_gps(10.9)
  assert selector._gm_gps[source] is None
  assert selector.gps_pm.sent[-1][1].gpsLocationExternal.latitude == (40.0 if source == "pps" else 38.3)


def test_no_source_publication_transition(selector):
  selector._publish_gm_gps(10.0)
  assert not selector.gps_pm.sent
  selector._gm_gps["device"] = (sample(), 10.0)
  selector._publish_gm_gps(10.0)
  valid = selector.gps_pm.sent[-1][1]
  assert valid.valid and valid.gpsLocationExternal.hasFix
  assert valid.gpsLocationExternal.latitude == 38.3
  selector._publish_gm_gps(10.1)
  assert len(selector.gps_pm.sent) == 1
  selector._publish_gm_gps(12.1)
  invalid = selector.gps_pm.sent[-1][1]
  assert not invalid.valid and not invalid.gpsLocationExternal.hasFix
  for now in (12.12, 12.13, 12.14):
    selector._publish_gm_gps(now)
  assert len(selector.gps_pm.sent) == 2
  selector._gm_gps["device"] = (sample(), 12.15)
  selector._publish_gm_gps(12.15)  # Recovery bypasses the 200 ms healthy cadence.
  assert len(selector.gps_pm.sent) == 3
  assert selector.gps_pm.sent[-1][1].gpsLocationExternal.hasFix
  for now in (15.0, 20.0, 30.0):
    selector._publish_gm_gps(now)
  assert len(selector.gps_pm.sent) == 4  # One more loss marker, then sustained silence.


def test_device_updates_honor_event_validity(selector):
  message = messaging.new_message("gpsLocation", valid=True)
  message.gpsLocation = {key: value for key, value in sample().items() if key != "timestamp_nanos"}
  class DeviceMessages(dict):
    updated = {"gpsLocation": True}
    valid = {"gpsLocation": True}
  selector.sm = DeviceMessages(gpsLocation=message.gpsLocation)
  selector._publish_gm_gps(10.0)
  assert selector.gps_pm.sent[-1][1].valid
  selector.sm.updated["gpsLocation"] = False
  selector._publish_gm_gps(10.05)
  assert selector._gm_gps["device"][1] == 10.0
  selector.sm.updated["gpsLocation"] = True
  selector.sm.valid["gpsLocation"] = False
  selector._publish_gm_gps(10.1)
  assert selector._gm_gps["device"] is None
  assert len(selector.gps_pm.sent) == 2  # Loss bypasses the healthy cadence too.
  assert not selector.gps_pm.sent[-1][1].gpsLocationExternal.hasFix
