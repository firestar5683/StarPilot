"""Category CAS is opt-in; legacy clients retain the original PUT contract."""
import copy
import pytest
from test_personality_profiles_api import _client, default_personality_profiles, profile_document, PERSONALITY_PROFILES_PARAM, the_galaxy

@pytest.mark.parametrize('writer', ['classic', 'big_dipper', 'slot_restore'])
def test_stale_category_rejected_without_overwrite(monkeypatch, writer):
  profiles = default_personality_profiles(False)
  profiles['standard']['acceleration'] = {'preset': 'custom', 'curve': [1.0] * 10}
  client, params = _client(monkeypatch, {PERSONALITY_PROFILES_PARAM: profile_document(profiles, enabled=True)})
  original = client.get('/api/personality_profiles').get_json()['profiles']['standard']['acceleration']
  first = copy.deepcopy(original)
  first['curve'][0] = 2.0
  if writer == 'slot_restore':
    # Same persisted document seam used by a successful validated slot restore.
    profiles['standard']['acceleration'] = first
    params.put(PERSONALITY_PROFILES_PARAM, profile_document(profiles, enabled=True))
  else:
    assert client.put('/api/personality_profiles', json={'profile': 'standard', 'category': 'acceleration', **first, 'expected': original}).status_code == 200
  second = copy.deepcopy(original)
  second['curve'][1] = 3.0
  response = client.put('/api/personality_profiles', json={'profile': 'standard', 'category': 'acceleration', **second, 'expected': original})
  assert response.status_code == 409
  assert client.get('/api/personality_profiles').get_json()['profiles']['standard']['acceleration'] == first


def test_legacy_put_contract_unchanged(monkeypatch):
  client, _ = _client(monkeypatch, {})
  response = client.put('/api/personality_profiles', json={'profile': 'standard', 'category': 'acceleration', 'preset': 'custom', 'curve': []})
  assert response.status_code == 200

@pytest.mark.parametrize('expected', [None, True, [], {'preset': 'custom', 'curve': [True] * 10}])
def test_invalid_expected_rejected(monkeypatch, expected):
  client, _ = _client(monkeypatch, {})
  response = client.put('/api/personality_profiles', json={'profile': 'standard', 'category': 'acceleration', 'preset': 'custom', 'curve': [], 'expected': expected})
  assert response.status_code in (400, 409)


def test_precondition_reads_inside_lock(monkeypatch):
  profiles = default_personality_profiles(False)
  original = {'preset': 'custom', 'curve': [1.0] * 10}
  profiles['standard']['acceleration'] = original
  client, params = _client(monkeypatch, {PERSONALITY_PROFILES_PARAM: profile_document(profiles, enabled=True)})
  class ChangedWhileWaiting:
    def __enter__(self):
      profiles['standard']['acceleration'] = {'preset': 'custom', 'curve': [2.0] * 10}
      params.values[PERSONALITY_PROFILES_PARAM] = profile_document(profiles, enabled=True)
    def __exit__(self, *_):
      pass
  monkeypatch.setattr(the_galaxy, '_PERSONALITY_PROFILES_WRITE_LOCK', ChangedWhileWaiting())
  response = client.put('/api/personality_profiles', json={'profile':'standard', 'category':'acceleration', **original, 'expected':original})
  assert response.status_code == 409
  assert params.writes == []


@pytest.mark.parametrize('boolean_expected', [False, True])
def test_numeric_roundtrip_and_historical_point_preservation(monkeypatch, boolean_expected):
  profiles = default_personality_profiles(False)
  original = {'preset':'custom', 'curve':[6.0] + [1.0] * 9}
  profiles['standard']['acceleration'] = original
  client, _ = _client(monkeypatch, {PERSONALITY_PROFILES_PARAM: profile_document(profiles, enabled=True)})
  expected = {'preset':'custom', 'curve':[6] + [True if boolean_expected else 1] * 9}
  edited = [6] + [2] + [1] * 8
  response = client.put('/api/personality_profiles', json={'profile':'standard', 'category':'acceleration', 'preset':'custom', 'curve':edited, 'expected':expected})
  assert response.status_code == (409 if boolean_expected else 200)
  if not boolean_expected:
    assert response.get_json()['profiles']['standard']['acceleration']['curve'] == edited
