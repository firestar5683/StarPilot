import pytest

from openpilot.common import gps


class FakeParams:
  def __init__(self, value=None):
    self.value = value

  def get(self, key):
    assert key == gps.GPS_SOURCE_PARAM
    return self.value


@pytest.fixture
def car_gps(monkeypatch):
  """Patch the opendbc lookups: car_gps(available, provides_time)."""
  import opendbc.car.gps as car_gps_module

  def setup(available: bool, provides_time: bool):
    monkeypatch.setattr(car_gps_module, "car_gps_available", lambda CP: available)
    monkeypatch.setattr(car_gps_module, "car_gps_provides_time", lambda CP: available and provides_time)
  return setup


# (car GPS available, car GPS has time, device u-blox, GpsSource, expected use_car_gps)
CASES = [
  (False, False, True,  "auto",   False),  # no car GPS: always the device
  (False, False, False, "car",    False),  # no car GPS: override can't create one
  (True,  False, False, "auto",   True),   # no u-blox: car GPS is the only source
  (True,  False, False, "device", True),   # no u-blox: "device" can't be honored
  (True,  False, True,  "auto",   False),  # Bolt-style (no time) + u-blox: prefer u-blox
  (True,  True,  True,  "auto",   True),   # Ford-style (real time) + u-blox: keep car GPS
  (True,  True,  True,  "device", False),  # override: force u-blox
  (True,  False, True,  "car",    True),   # override: force car GPS
  (True,  False, True,  None,     False),  # unset param behaves like auto
  (True,  False, True,  "bogus",  False),  # invalid value behaves like auto
  (True,  False, True,  b"car",   True),   # bytes values are accepted
]


@pytest.mark.parametrize("available,provides_time,ublox,pref,expected", CASES)
def test_use_car_gps(monkeypatch, car_gps, available, provides_time, ublox, pref, expected):
  car_gps(available, provides_time)
  monkeypatch.setattr(gps, "ublox_present", lambda: ublox)
  assert gps.use_car_gps(FakeParams(pref), CP=None) is expected


def test_unregistered_param_defaults_to_auto():
  class RaisingParams:
    def get(self, key):
      raise KeyError(key)
  assert gps.gps_source_preference(RaisingParams()) == "auto"
