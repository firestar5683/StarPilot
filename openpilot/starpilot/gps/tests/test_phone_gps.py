import math
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from openpilot.cereal import log, messaging
from openpilot.starpilot.gps.phone import PhoneGpsPublisher, phone_gps
from openpilot.starpilot.gps import source
from openpilot.starpilot.gps.source import GPS_SOURCES, gps_mode, select_location
from openpilot.starpilot.navigation.status import NavigationStatusSource

NOW = 101_000_000_000
FIX = {"latitude": 40., "longitude": -110., "horizontalAccuracy": 5., "ageMs": 300, "speed": 20., "bearing": 90.,
       "bearingAccuracy": 10., "timestamp": 1_790_000_000_000}


class Messages:
  def __init__(self):
    self.data = {}
    self.valid = dict.fromkeys(GPS_SOURCES, False)
    self.logMonoTime = dict.fromkeys(GPS_SOURCES, 0)
    self.alive = dict.fromkeys(GPS_SOURCES, True)
    self.seen = dict.fromkeys(GPS_SOURCES, True)
    self.recv_time = dict.fromkeys(GPS_SOURCES, 0.)

  def __getitem__(self, key):
    return self.data[key]

  def update(self, _timeout):
    pass

  def send(self, service, message):
    with log.Event.from_bytes(message.to_bytes()) as event:
      value = getattr(event, service).to_dict()
      if service in ("starpilotCarState", "phoneGps"):
        value["gps"] = SimpleNamespace(**getattr(event, service).gps.to_dict())
      self.data[service] = SimpleNamespace(**value)
      self.valid[service] = event.valid
      self.logMonoTime[service] = event.logMonoTime
      self.recv_time[service] = event.logMonoTime / 1e9


def publish(sm, payload=FIX, now=NOW):
  return PhoneGpsPublisher(pm_factory=lambda: sm, mono_clock=lambda: now).publish(dict(payload))


def test_phone_is_used_only_without_another_fix():
  sm = Messages()
  assert publish(sm) == {"ok": True}
  stamp, gps = select_location(sm, NOW)
  assert stamp == NOW - 300_000_000 and gps.longitude == -110. and gps.bearingDeg == 90.

  car = messaging.new_message("starpilotCarState", valid=True, logMonoTime=NOW)
  car.starpilotCarState.gps = {"sourceMonoTime": NOW - 1, "latitude": 41., "longitude": -111., "horizontalAccuracy": 5., "hasFix": True}
  sm.send("starpilotCarState", car)
  assert select_location(sm, NOW)[1].longitude == -111.

  native = messaging.new_message("gpsLocation", valid=True, logMonoTime=NOW - 10_000_000)
  native.gpsLocation = {"source": "qcomdiag", "hasFix": True, "horizontalAccuracy": 5., "longitude": -90., "latitude": 30.}
  sm.send("gpsLocation", native)
  assert select_location(sm, NOW)[1].longitude == -90.


def test_phone_fix_expires_on_comma_clock():
  sm = Messages()
  publish(sm)
  assert select_location(sm, NOW + 2_100_000_000) is not None
  assert select_location(sm, NOW + 2_300_000_000) is None


def test_unknown_values_are_not_used():
  gps = phone_gps({**FIX, "speed": -1, "bearing": 45., "bearingAccuracy": -1, "verticalAccuracy": -1, "altitude": None}, NOW)
  assert all(math.isnan(gps[key]) for key in ("speed", "bearingDeg", "bearingAccuracyDeg", "verticalAccuracy", "altitude"))


@pytest.mark.parametrize("change", [{"ageMs": 2500}, {"ageMs": -1}, {"latitude": 91.}, {"latitude": 0., "longitude": 0.},
                                    {"horizontalAccuracy": 0}, {"latitude": True}, {"extra": 1}, {"timestamp": 1.5}])
def test_invalid_fixes_are_rejected(change):
  with pytest.raises(ValueError):
    phone_gps({**FIX, **change}, NOW)


def test_inaccurate_phone_fix_is_published_but_not_selected():
  sm = Messages()
  publish(sm, {**FIX, "horizontalAccuracy": 60.})
  assert sm.valid["phoneGps"] and select_location(sm, NOW) is None


def test_navigation_status_ranks_phone_below_native():
  sm = Messages()
  with patch('openpilot.cereal.messaging.SubMaster', return_value=sm):
    status = NavigationStatusSource(mono_clock=lambda: NOW - 1_000_000_000, boot_clock=lambda: NOW)
  status.mono_clock = lambda: NOW
  publish(sm)
  assert status.map_position()['longitude'] == -110.
  native = messaging.new_message("gpsLocation", valid=True, logMonoTime=NOW - 500_000_000)
  native.gpsLocation = {"source": "qcomdiag", "hasFix": True, "horizontalAccuracy": 5., "longitude": -90., "latitude": 30.}
  sm.send("gpsLocation", native)
  assert status.map_position()['longitude'] == -90.


def native(sm):
  message = messaging.new_message("gpsLocation", valid=True, logMonoTime=NOW - 10_000_000)
  message.gpsLocation = {"source": "qcomdiag", "hasFix": True, "horizontalAccuracy": 5., "longitude": -90., "latitude": 30.}
  sm.send("gpsLocation", message)


def test_gps_modes_choose_phone_first_or_never():
  sm = Messages()
  publish(sm)
  assert select_location(sm, NOW, "comma") is None
  native(sm)
  assert select_location(sm, NOW, "backup")[1].longitude == -90.
  assert select_location(sm, NOW, "comma")[1].longitude == -90.
  assert select_location(sm, NOW, "phone")[1].longitude == -110.
  assert select_location(sm, NOW + 2_300_000_000, "phone")[1].longitude == -90.


def test_gps_mode_follows_navigation_settings(tmp_path, monkeypatch):
  monkeypatch.setattr("openpilot.starpilot.storage.starpilot_storage_root", lambda: tmp_path)
  monkeypatch.setattr(source, "_mode", [-math.inf, "backup"])
  assert gps_mode(10.) == "backup"
  (tmp_path / "navigation").mkdir()
  (tmp_path / "navigation" / "settings.json").write_text('{"gpsSource": "phone"}')
  assert gps_mode(10.5) == "backup"
  assert gps_mode(11.) == "phone"
  (tmp_path / "navigation" / "settings.json").write_text('{"gpsSource": "tunnel"}')
  assert gps_mode(12.) == "backup"


@pytest.mark.parametrize("mode,longitude,name", [("backup", -90., "comma"), ("phone", -110., "phone"), ("comma", -90., "comma")])
def test_navigation_status_reports_the_source_it_follows(mode, longitude, name):
  sm = Messages()
  with patch('openpilot.cereal.messaging.SubMaster', return_value=sm):
    status = NavigationStatusSource(mono_clock=lambda: NOW - 1_000_000_000, boot_clock=lambda: NOW)
  status.mono_clock = lambda: NOW
  publish(sm)
  native(sm)
  with patch('openpilot.starpilot.navigation.status.gps_mode', return_value=mode):
    position = status.map_position()
  assert position['longitude'] == longitude and position['source'] == name


def test_car_gps_ranks_against_the_phone_in_every_mode():
  sm = Messages()
  publish(sm)
  car = messaging.new_message("starpilotCarState", valid=True, logMonoTime=NOW)
  car.starpilotCarState.gps = {"sourceMonoTime": NOW - 1, "latitude": 41., "longitude": -111., "horizontalAccuracy": 5., "hasFix": True}
  sm.send("starpilotCarState", car)
  assert select_location(sm, NOW, "backup")[1].longitude == -111.
  assert select_location(sm, NOW, "comma")[1].longitude == -111.
  assert select_location(sm, NOW, "phone")[1].longitude == -110.
  with patch('openpilot.cereal.messaging.SubMaster', return_value=sm):
    status = NavigationStatusSource(mono_clock=lambda: NOW - 1_000_000_000, boot_clock=lambda: NOW)
  status.mono_clock = lambda: NOW
  for mode, name in (("backup", "car"), ("comma", "car"), ("phone", "phone")):
    with patch('openpilot.starpilot.navigation.status.gps_mode', return_value=mode):
      assert status.map_position()['source'] == name
