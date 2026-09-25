import json
from unittest.mock import patch

import pytest

from openpilot.starpilot.navigation.owner import NavigationOwner, ValidationError, ConflictError, response_json

PLACE = {'name': 'Home', 'latitude': 40., 'longitude': -90.}


@pytest.fixture
def owner(tmp_path):
  return NavigationOwner(tmp_path, runtime_source=lambda: None)


def test_settings_private_atomic_and_revision_scoped(owner):
  assert owner.snapshot()['enabled'] is False
  saved = owner.configure({'enabled': True, 'token': 'pk.test'}, '0', True)
  assert saved['hasKey'] and 'token' not in saved and saved['status'] == 'noDestination'
  assert owner.path.stat().st_mode & 0o777 == 0o600
  with pytest.raises(ConflictError):
    owner.select(PLACE, '0', True)
  selected = owner.select(PLACE, saved['revision'], True)
  assert selected['destination']['name'] == 'Home'
  assert owner.favorite(PLACE, selected['revision'], True)['favorites'][0]['name'] == 'Home'
  assert 'pk.test' not in json.dumps(owner.snapshot())


def test_authority_rechecked_after_flush(owner):
  calls = iter((True, False))
  with pytest.raises(PermissionError):
    owner.configure({'enabled': True}, '0', lambda: next(calls))
  assert not owner.path.exists()
  assert list(owner.root.glob('.settings-*')) == []


def test_corrupt_existing_settings_not_overwritten(owner):
  owner.path.write_text('{invalid')
  with pytest.raises(ValidationError):
    owner.configure({'enabled': True}, '0', True)
  assert owner.path.read_text() == '{invalid'


@pytest.mark.parametrize('value', [dict(PLACE, latitude=float('nan')), dict(PLACE, latitude=True), dict(PLACE, longitude=181),
                                   dict(PLACE, name=''), None])
def test_invalid_destination(owner, value):
  with pytest.raises(ValidationError):
    owner.select(value, '0', True)


def test_current_units_and_stale_revision_not_presented(owner):
  saved = owner.configure({'enabled': True, 'token': 'pk.test'}, '0', True)
  selected = owner.select(PLACE, saved['revision'], True)
  owner.runtime_source = lambda: {'revision': saved['revision'], 'status': 'guiding', 'instruction': {'text': 'old'}, 'route': []}
  with patch('openpilot.common.params.Params') as params:
    params.return_value.get_bool.return_value = True
    status = owner.snapshot()
  assert status['isMetric'] and status['instruction'] is None
  assert selected['revision'] != saved['revision']


def test_response_limits_and_private_failures():
  from unittest.mock import Mock
  response = Mock(status_code=200)
  response.__enter__ = Mock(return_value=response)
  response.__exit__ = Mock(return_value=False)
  response.iter_content.return_value = [b'{"ok":true}']
  session = Mock()
  session.get.return_value = response
  assert response_json(session, 'https://api.mapbox.com', {'access_token': 'private'}) == {'ok': True}
  with patch('openpilot.starpilot.navigation.owner.time.monotonic', side_effect=[0, 11]):
    with pytest.raises(ValidationError, match='too long'):
      response_json(session, 'https://api.mapbox.com', {})
