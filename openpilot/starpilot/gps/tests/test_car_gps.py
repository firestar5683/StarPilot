from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from opendbc.can import CANPacker
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR
from openpilot.cereal import log, messaging
from openpilot.starpilot.gps.publisher import CarGpsPublisher
from openpilot.starpilot.gps.source import GPS_SOURCES, observation, select_location
from openpilot.starpilot.navigation.runtime import location
from openpilot.starpilot.navigation.status import NavigationStatusSource


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
    # Decode the actual wire rather than reading the producer's builder.
    with log.Event.from_bytes(message.to_bytes()) as event:
      value = getattr(event, service).to_dict()
      if service == 'starpilotCarState':
        value['gps'] = SimpleNamespace(**getattr(event, service).gps.to_dict())
      self.data[service] = SimpleNamespace(**value)
      self.valid[service] = event.valid
      self.logMonoTime[service] = event.logMonoTime
      self.recv_time[service] = event.logMonoTime / 1e9


def live_can_fix():
  cp = CarInterface.get_non_essential_params(CAR.CHEVROLET_BOLT_CC_2018_2021)
  ci = CarInterface(cp)
  packer = CANPacker('gm_global_a_powertrain_generated')
  frame = packer.make_can_msg('TCICOnStarGPSPosition', 0, {'GPSLatitude': 40. * 3_600_000, 'GPSLongitude': -110. * 3_600_000})
  ci.update([(151_000_000_000, [frame])])
  return ci.CS


def test_real_interface_wire_navigation_and_search_fallback():
  state, sm = live_can_fix(), Messages()
  clock = [100_000_000_000]
  with patch('openpilot.cereal.messaging.SubMaster', return_value=sm):
    status = NavigationStatusSource(mono_clock=lambda: clock[0], boot_clock=lambda: clock[0] + 50_000_000_000)
  clock[0] = 101_000_000_000
  owner = CarGpsPublisher(mono_clock=lambda: clock[0], boot_clock=lambda: clock[0] + 50_000_000_000)
  owner.update(state, sm)
  assert sm['starpilotCarState'].gps.sourceMonoTime == clock[0]
  assert sm['starpilotCarState'].gps.unixTimestampMillis == 0  # OnStar position has no GNSS clock.
  assert location(sm, clock[0]) == (clock[0], (-110., 40.), 0., None)
  assert status.search_position() == (-110., 40.)
  position = status.map_position()
  assert position is not None and 'bearing' not in position  # No invented north heading.
  original = sm.logMonoTime['starpilotCarState']
  clock[0] += 1_000_000_000
  owner.update(state, sm)
  assert sm.logMonoTime['starpilotCarState'] == original
  clock[0] += 2_000_000_000
  assert location(sm, clock[0]) is None
  assert status.map_position() is None


def test_native_gps_keeps_priority_and_recovers_after_can():
  sm, state = Messages(), live_can_fix()
  now = 101_000_000_000
  CarGpsPublisher(mono_clock=lambda: now, boot_clock=lambda: now + 50_000_000_000).update(state, sm)
  native = messaging.new_message('gpsLocationExternal', valid=True, logMonoTime=now - 10_000_000)
  native.gpsLocationExternal = {'source': 'ublox', 'hasFix': True, 'horizontalAccuracy': 5., 'longitude': -90., 'latitude': 30.}
  sm.send('gpsLocationExternal', native)
  assert select_location(sm, now)[1].longitude == -90.
  sm.valid['gpsLocationExternal'] = False
  assert select_location(sm, now)[1].longitude == -110.
  sm.valid['gpsLocationExternal'] = True
  assert select_location(sm, now)[1].longitude == -90.


@pytest.mark.parametrize('fault', ['expired_source', 'future_source', 'no_fix', 'bad_position', 'bad_accuracy', 'future_envelope'])
def test_can_observation_never_uses_invalid_or_restamped_old_position(fault):
  sm, state = Messages(), live_can_fix()
  now = 101_000_000_000
  CarGpsPublisher(mono_clock=lambda: now, boot_clock=lambda: now + 50_000_000_000).update(state, sm)
  gps = sm['starpilotCarState'].gps
  if fault == 'expired_source':
    gps.sourceMonoTime = now - 3_000_000_000
  elif fault == 'future_source':
    gps.sourceMonoTime = now + 1
  elif fault == 'no_fix':
    gps.hasFix = False
  elif fault == 'bad_position':
    gps.latitude = 91.
  elif fault == 'bad_accuracy':
    gps.horizontalAccuracy = float('nan')
  else:
    sm.logMonoTime['starpilotCarState'] = now + 1
  assert observation(sm, 'starpilotCarState', now) is None


@pytest.mark.parametrize('age', [-1, 2_500_000_001])
def test_publisher_rejects_future_or_expired_can(age):
  state, output = live_can_fix(), Mock()
  owner = CarGpsPublisher(mono_clock=lambda: 101_000_000_000, boot_clock=lambda: 151_000_000_000 + age)
  owner.update(state, output)
  output.send.assert_not_called()


def test_absent_gps_and_clock_pair_interruption_do_not_publish():
  output = Mock()
  clock = iter([101_000_000_000, 101_002_000_000])
  owner = CarGpsPublisher(mono_clock=lambda: next(clock), boot_clock=lambda: 151_000_000_000)
  owner.update(SimpleNamespace(), output)
  owner.update(live_can_fix(), output)
  output.send.assert_not_called()


def test_old_car_state_wire_has_no_gps_fix():
  event = messaging.new_message('starpilotCarState', valid=True, logMonoTime=101_000_000_000)
  event.starpilotCarState.dashboardSpeedLimit = 25.
  sm = Messages()
  sm.send('starpilotCarState', event)
  assert select_location(sm, 101_000_000_000) is None
