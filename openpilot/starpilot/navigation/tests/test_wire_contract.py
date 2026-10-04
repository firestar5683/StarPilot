from types import SimpleNamespace

import pytest

from openpilot.cereal import log, messaging
from openpilot.starpilot.navigation.wire import VERSION, LEGACY_SOURCE_FORMAT, navigation_state, navigation_envelope, decode_legacy_navigation


def value():
  return {'sessionId': 'navigation', 'frameMonoTime': 100, 'startedMonoTime': 10, 'revision': 'revision',
          'enabled': True, 'controlValid': True, 'status': 'guiding', 'locationMonoTime': 100,
          'route': [{'latitude': 1., 'longitude': 2.}]}


def test_nested_navigation_roundtrip_preserves_historical_prefix():
  message = messaging.new_message('starpilotNavigation')
  message.starpilotNavigation = navigation_envelope(value())
  message.starpilotNavigation.hudControl.audibleAlert = 'engage'
  message.starpilotNavigation.steeringLimitInfo.valid = True
  with log.Event.from_bytes(message.to_bytes()) as decoded:
    assert decoded.starpilotNavigation.hudControl.audibleAlert == 'engage'
    assert decoded.starpilotNavigation.steeringLimitInfo.valid
    assert navigation_state(decoded.starpilotNavigation).version == VERSION
    assert navigation_state(decoded.starpilotNavigation).route[0].latitude == 1.


@pytest.mark.parametrize('envelope', (None, SimpleNamespace(sessionId='old-flat', enabled=True),
                                   SimpleNamespace(navigation=SimpleNamespace(version=0)),
                                   SimpleNamespace(navigation=SimpleNamespace(version=1))))
def test_old_flat_or_unknown_live_version_never_admits(envelope):
  assert navigation_state(envelope) is None


def test_explicit_offline_legacy_schema_preserves_published_data_only():
  import capnp
  from pathlib import Path
  from openpilot.starpilot.navigation import wire
  schema = capnp.load(str(Path(wire.__file__).with_name('legacy_navigation.capnp')))
  raw = schema.LegacyNavigation.new_message(**value()).to_bytes()
  assert decode_legacy_navigation(raw, source_format='unknown', event_stamp_ns=100) is None
  decoded = decode_legacy_navigation(raw, source_format=LEGACY_SOURCE_FORMAT, event_stamp_ns=100)
  assert decoded['sessionId'] == 'navigation' and decoded['route'][0]['latitude'] == 1.
  assert decode_legacy_navigation(b'bad', source_format=LEGACY_SOURCE_FORMAT, event_stamp_ns=100) is None
  from openpilot.cereal import custom
  historical = custom.StarPilotCarControl.new_message()
  historical.hudControl.audibleAlert = 'engage'
  assert decode_legacy_navigation(historical.to_bytes(), source_format=LEGACY_SOURCE_FORMAT, event_stamp_ns=100) is None
