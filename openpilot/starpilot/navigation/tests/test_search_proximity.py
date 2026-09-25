import json
import threading
import uuid
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import pytest

from openpilot.cereal import log, messaging
from openpilot.starpilot.navigation.owner import NavigationOwner, ValidationError
from openpilot.starpilot.navigation.status import GPS_SOURCES, NavigationStatusSource

POI = {'mapbox_id': 'poi/id', 'name': 'Coffee', 'feature_type': 'poi'}


class Clock:
  mono = 100_000_000_000
  offset = 50_000_000_000

  def boot(self):
    return self.mono + self.offset


class Messages:
  def __init__(self, clock):
    self.clock = clock
    names = ['starpilotNavigation', *GPS_SOURCES]
    self.seen = dict.fromkeys(names, True)
    self.alive = dict.fromkeys(names, True)
    self.valid = dict.fromkeys(names, True)
    self.recv_time = dict.fromkeys(names, 0.)
    self.logMonoTime = dict.fromkeys(names, 0)
    self.sock = {'test': Mock()}
    self.data = {}
    self.update_hook = lambda: None

  def __getitem__(self, service):
    return self.data[service]

  def update(self, _timeout):
    self.update_hook()

  def fix(self, service, *, stamp=None, longitude=-87.63, latitude=41.88, accuracy=5.):
    self.logMonoTime[service] = stamp if stamp is not None else self.clock.mono - 20_000_000
    self.recv_time[service] = (self.clock.mono - 10_000_000) / 1e9
    self.data[service] = NS(source=GPS_SOURCES[service], longitude=longitude, latitude=latitude,
                            hasFix=True, horizontalAccuracy=accuracy)


@pytest.fixture
def source():
  clock = Clock()
  messages = Messages(clock)
  with patch('openpilot.cereal.messaging.SubMaster', return_value=messages) as factory:
    result = NavigationStatusSource(mono_clock=lambda: clock.mono, boot_clock=clock.boot)
  assert factory.call_args.args[0] == ['starpilotNavigation', 'gpsLocationExternal', 'gpsLocation']
  clock.mono += 100_000_000
  messages.fix('gpsLocationExternal')
  messages.fix('gpsLocation', stamp=clock.mono - 30_000_000, longitude=-90., latitude=40.)
  yield result, messages, clock
  result.close()


def test_current_python_gps_monotonic_envelope_and_newest_valid_fix(source):
  reader, sm, clock = source
  event = messaging.new_message('gpsLocationExternal', valid=True, logMonoTime=clock.mono - 20_000_000)
  event.gpsLocationExternal = {'source': 'ublox', 'hasFix': True, 'horizontalAccuracy': 4.,
                              'longitude': -87.63, 'latitude': 41.88}
  with log.Event.from_bytes(event.to_bytes()) as parsed:
    sm.data['gpsLocationExternal'] = parsed.gpsLocationExternal
    assert reader.search_position() == (-87.63, 41.88)
  # A BOOTTIME stamp is invalid for these proved Python publishers.
  sm.logMonoTime['gpsLocationExternal'] = clock.boot() - 20_000_000
  assert reader.search_position() == (-90., 40.)


@pytest.mark.parametrize('fault', ['unseen', 'invalid', 'dead', 'no_fix', 'unknown_source', 'old_envelope',
                                  'old_receipt', 'future_receipt', 'future_envelope', 'poor_quality',
                                  'unknown_quality', 'nan', 'bad_longitude', 'bad_latitude'])
def test_missing_or_unqualified_fix_omits_optional_bias(source, fault):
  reader, sm, clock = source
  sm.valid['gpsLocation'] = False
  gps = sm.data['gpsLocationExternal']
  if fault in ('unseen', 'invalid', 'dead'):
    getattr(sm, {'unseen': 'seen', 'invalid': 'valid', 'dead': 'alive'}[fault])['gpsLocationExternal'] = False
  elif fault == 'no_fix':
    gps.hasFix = False
  elif fault == 'unknown_source':
    gps.source = 'android'
  elif fault == 'old_envelope':
    sm.logMonoTime['gpsLocationExternal'] = clock.mono - 3_000_000_000
  elif fault == 'old_receipt':
    sm.recv_time['gpsLocationExternal'] = (clock.mono - 3_000_000_000) / 1e9
  elif fault == 'future_receipt':
    sm.recv_time['gpsLocationExternal'] = (clock.mono + 1_000_000) / 1e9
  elif fault == 'future_envelope':
    sm.logMonoTime['gpsLocationExternal'] = clock.mono + 1_000_000
  elif fault == 'poor_quality':
    gps.horizontalAccuracy = 26.
  elif fault == 'unknown_quality':
    gps.horizontalAccuracy = 0.
  elif fault == 'nan':
    gps.longitude = float('nan')
  elif fault == 'bad_longitude':
    gps.longitude = 181.
  elif fault == 'bad_latitude':
    gps.latitude = -91.
  assert reader.search_position() is None


def test_startup_resume_and_receipt_during_update_require_current_source(source):
  reader, sm, clock = source
  assert reader.search_position() is not None
  clock.offset += 100_000_000
  assert reader.search_position() is None
  assert reader.search_position() is None  # Queued pre-resume fix cannot recover it.
  clock.mono += 100_000_000
  sm.fix('gpsLocationExternal')
  assert reader.search_position() == (-87.63, 41.88)
  sm.logMonoTime['gpsLocationExternal'] = reader.gps_after_mono_ns - 1
  sm.valid['gpsLocation'] = False
  assert reader.search_position() is None
  def receive():
    clock.mono += 1_000_000
    sm.fix('gpsLocationExternal', stamp=clock.mono)
    sm.recv_time['gpsLocationExternal'] = clock.mono / 1e9
  sm.update_hook = receive
  assert reader.search_position() == (-87.63, 41.88)


def test_resume_during_receive_denies_then_new_fix_recovers(source):
  reader, sm, clock = source
  assert reader.search_position() is not None
  def resume():
    clock.offset += 100_000_000
    clock.mono += 1_000_000
  sm.update_hook = resume
  assert reader.search_position() is None
  sm.update_hook = lambda: None
  assert reader.search_position() is None
  clock.mono += 100_000_000
  sm.fix('gpsLocationExternal')
  assert reader.search_position() == (-87.63, 41.88)


def test_qcom_without_horizontal_accuracy_is_not_fabricated_from_other_quality(source):
  reader, sm, _clock = source
  sm.valid['gpsLocationExternal'] = False
  sm.data['gpsLocation'].horizontalAccuracy = 0.
  sm.data['gpsLocation'].verticalAccuracy = 1.
  assert reader.search_position() is None


def test_close_releases_existing_source_sockets_and_cannot_reuse_position(source):
  reader, sm, _clock = source
  reader.close()
  sm.sock['test'].close.assert_called_once()
  assert reader.search_position() is None
  assert reader.snapshot() is None


def owner(tmp_path, reader):
  result = NavigationOwner(tmp_path / 'saved', runtime_source=reader, transient_root=tmp_path / 'boot')
  result.configure({'enabled': True, 'token': 'pk.synthetic'}, '0', True)
  return result


def test_provider_uses_optional_vehicle_bias_without_persisting_or_exposing_coordinates(tmp_path, source):
  reader, _sm, _clock = source
  nav = owner(tmp_path, reader)
  before = nav.path.read_bytes()
  search = str(uuid.uuid4())
  with patch('openpilot.starpilot.navigation.owner.response_json', return_value={'suggestions': [POI]}) as provider:
    result = nav.search_places('coffee', 'caller', search, str(uuid.uuid4()))
  params = provider.call_args.args[2]
  assert params['proximity'] == '-87.630000,41.880000'
  assert params['types'] == 'poi' and params['q'] == 'coffee'
  assert str(uuid.UUID(params['session_token'], version=4)) == params['session_token']
  assert nav.path.read_bytes() == before
  assert '-87.63' not in json.dumps(list(nav._searches.values()), default=lambda _value: None)
  assert 'proximity' not in json.dumps(result) and 'latitude' not in json.dumps(result)
  assert 'proximity' not in nav.snapshot()


def test_optional_source_failure_preserves_provider_ip_bias_and_address_fallback(tmp_path):
  reader = NS(search_position=Mock(side_effect=OSError('GPS unavailable')))
  nav = owner(tmp_path, reader)
  with patch('openpilot.starpilot.navigation.owner.response_json', side_effect=[
      {'suggestions': []}, {'features': [{'properties': {'full_address': '123 Main'},
                                       'geometry': {'coordinates': [-90., 40.]}}]}]) as provider:
    result = nav.search_places('123 Main', 'caller', str(uuid.uuid4()), str(uuid.uuid4()))
  assert 'proximity' not in provider.call_args_list[0].args[2]
  assert 'proximity' not in provider.call_args_list[1].args[2]
  assert result[0]['name'] == '123 Main' and not result[0].get('temporary')


def test_slow_network_holds_neither_owner_lock_nor_prevents_cancel(tmp_path, source):
  reader, _sm, _clock = source
  nav = owner(tmp_path, reader)
  search = str(uuid.uuid4())
  entered, release, canceled = threading.Event(), threading.Event(), threading.Event()
  errors = []
  cancel = None
  def provider(*_args):
    entered.set()
    assert release.wait(2)
    return {'suggestions': [POI]}
  def run():
    try:
      nav.search_places('coffee', 'caller', search, str(uuid.uuid4()))
    except ValidationError as error:
      errors.append(str(error))
  with patch('openpilot.starpilot.navigation.owner.response_json', side_effect=provider) as requests:
    thread = threading.Thread(target=run)
    thread.start()
    try:
      assert entered.wait(1)
      cancel = threading.Thread(target=lambda: (nav.cancel_search('caller', search), canceled.set()))
      cancel.start()
      assert canceled.wait(1)
    finally:
      release.set()
      thread.join(2)
      if cancel is not None:
        cancel.join(2)
  assert errors == ['Start a new destination search']
  assert requests.call_count == 1  # Canceled work must not start address fallback.


def test_cancel_during_optional_context_never_sends_provider_or_fallback(tmp_path):
  nav = owner(tmp_path, NS())
  search = str(uuid.uuid4())
  def context():
    nav.cancel_search('caller', search)
    return (-87.63, 41.88)
  nav.runtime_source.search_position = context
  with patch('openpilot.starpilot.navigation.owner.response_json') as provider:
    with pytest.raises(ValidationError, match='Start a new destination search'):
      nav.search_places('coffee', 'caller', search, str(uuid.uuid4()))
  provider.assert_not_called()


def test_map_position_lease_uses_oldest_envelope_or_receipt_and_expires(source):
  reader, sm, clock = source
  sm.valid['gpsLocation'] = False
  assert reader.map_position() == {'longitude': -87.63, 'latitude': 41.88, 'validForMs': 2480.}
  sm.recv_time['gpsLocationExternal'] = (clock.mono - 500_000_000) / 1e9
  assert reader.map_position()['validForMs'] == 2000.
  clock.mono += 2_000_000_001
  assert reader.map_position() is None
