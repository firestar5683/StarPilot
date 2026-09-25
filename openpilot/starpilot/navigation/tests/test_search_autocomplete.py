import uuid
from unittest.mock import patch

import pytest

from openpilot.starpilot.navigation.mapbox_budget import FREE, STOP_FRACTION, BudgetExhausted, MonthlyBudget, read_usage
from openpilot.starpilot.navigation.owner import NavigationOwner, ValidationError

POI = {'mapbox_id': 'poi/coffee', 'name': 'Coffee Shop', 'feature_type': 'poi', 'full_address': '123 Main St'}
STREET = {'mapbox_id': 'address/elm', 'name': '12 Elm St', 'feature_type': 'address', 'place_formatted': 'Springfield'}
COUNTRY = {'mapbox_id': 'country/us', 'name': 'United States', 'feature_type': 'country'}


@pytest.fixture
def owner(tmp_path):
  result = NavigationOwner(tmp_path / 'saved', runtime_source=lambda: None, transient_root=tmp_path / 'boot')
  result.configure({'enabled': True, 'token': 'pk.synthetic'}, '0', True)
  return result


def suggest(owner, query, search_id, client, suggestions, autocomplete=True):
  with patch('openpilot.starpilot.navigation.owner.response_json', return_value={'suggestions': suggestions}) as provider:
    results = owner.search_places(query, 'caller', search_id, client, autocomplete=autocomplete)
  return results, provider


def test_autocomplete_keystrokes_share_one_session_and_include_addresses(owner):
  search_id, client = str(uuid.uuid4()), str(uuid.uuid4())
  first, provider = suggest(owner, 'cof', search_id, client, [POI])
  second, later = suggest(owner, '12 elm', search_id, client, [STREET, COUNTRY])
  request, again = provider.call_args.args[2], later.call_args.args[2]
  assert request['session_token'] == again['session_token'], "typing is one Mapbox search session"
  assert set(request['types'].split(',')) >= {'poi', 'address', 'street', 'place'}
  assert [row['name'] for row in first] == ['Coffee Shop']
  assert [row['name'] for row in second] == ['12 Elm St'], "countries are not destinations"
  feature = {'features': [{'properties': {**POI}, 'geometry': {'coordinates': [-90., 40.]}}]}
  with patch('openpilot.starpilot.navigation.owner.response_json', return_value=feature):
    status = owner.select_place('poi/coffee', search_id, 'caller', owner.read()['revision'], True)
  assert status['destination']['name'] == 'Coffee Shop', "an earlier keystroke's suggestion is still choosable"
  _, fresh = suggest(owner, 'more', search_id, client, [POI])
  assert fresh.call_args.args[2]['session_token'] != request['session_token'], "choosing ends the session"


def test_search_button_keeps_upstream_places_then_address_search(owner):
  results, provider = suggest(owner, 'coffee', str(uuid.uuid4()), str(uuid.uuid4()), [POI, STREET], autocomplete=False)
  assert provider.call_args.args[2]['types'] == 'poi', "the Search button is unchanged: places first"
  assert [row['name'] for row in results] == ['Coffee Shop']
  with patch.object(owner, 'search', return_value=[]) as fallback:
    suggest(owner, 'nowhere', str(uuid.uuid4()), str(uuid.uuid4()), [], autocomplete=False)
  fallback.assert_called_once_with('nowhere')


def test_autocomplete_never_falls_back_to_permanent_geocoding(owner):
  with patch.object(owner, 'search') as fallback:
    assert suggest(owner, 'nowhere', str(uuid.uuid4()), str(uuid.uuid4()), [])[0] == []
    with patch('openpilot.starpilot.navigation.owner.response_json', side_effect=ValidationError('down')):
      assert owner.search_places('coffee', 'caller', str(uuid.uuid4()), str(uuid.uuid4()), autocomplete=True) == []
  fallback.assert_not_called()


def test_autocomplete_failure_is_quiet(owner):
  search_id, client = str(uuid.uuid4()), str(uuid.uuid4())
  with patch('openpilot.starpilot.navigation.owner.response_json', side_effect=ValidationError('down')) as provider:
    assert owner.search_places('coffee', 'caller', search_id, client, autocomplete=True) == []
  assert provider.call_count == 1


def test_search_sessions_stop_at_the_free_allowance(owner):
  limit = int(FREE['searchSessions'] * STOP_FRACTION)
  owner.search_budget.used = limit - 1
  suggest(owner, 'cof', str(uuid.uuid4()), str(uuid.uuid4()), [POI], autocomplete=True)
  with pytest.raises(ValidationError, match='free Mapbox searches'):
    suggest(owner, 'tea', str(uuid.uuid4()), str(uuid.uuid4()), [POI], autocomplete=True)
  results, _ = suggest(owner, 'tea', str(uuid.uuid4()), str(uuid.uuid4()), [POI], autocomplete=False)
  assert results, "the Search button keeps upstream's behavior past the cap"
  assert read_usage(owner.root / 'mapbox-usage')['searchSessions']['used'] == limit + 1, "and is still counted"


def test_budget_counts_persist_and_reset_monthly(tmp_path):
  now = [1_790_000_000.0]
  budget = MonthlyBudget('directions', tmp_path, clock=lambda: now[0])
  assert budget.limit == 99_000
  budget.spend(98_999)
  budget.spend()
  with pytest.raises(BudgetExhausted):
    budget.spend()
  assert MonthlyBudget('directions', tmp_path, clock=lambda: now[0]).remaining() == 0, "survives restarts"
  now[0] += 40 * 86400
  assert budget.remaining() == 99_000
  with pytest.raises(ValueError):
    MonthlyBudget('mapMatching', tmp_path)
