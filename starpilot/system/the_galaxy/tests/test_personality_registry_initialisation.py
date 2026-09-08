"""Registry JSON {} is unconfigured, not a malformed saved profile."""
import pytest
from test_personality_profiles_api import _client, _slot_client
from openpilot.starpilot.common.longitudinal_personality_profiles import PERSONALITY_PROFILES_PARAM, strict_profile_document

@pytest.mark.parametrize('raw', [{}, '{}', b'{}'])
def test_registry_empty_object_get_and_enable(monkeypatch, raw):
  client, params = _client(monkeypatch, {PERSONALITY_PROFILES_PARAM: raw, 'CustomPersonalities':False})
  before = dict(params.values)
  response = client.get('/api/personality_profiles')
  assert response.status_code == 200
  assert not response.get_json()['configured']
  assert params.values == before
  response = client.put('/api/params', json={'key':'CustomPersonalities','value':True})
  assert response.status_code == 200
  saved = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert saved is not None and saved['enabled']
  assert all(profile == {
    'acceleration': {'preset':'standard','curve':[]},
    'braking': {'preset':'standard','curve':[]},
    'following': {'preset':'medium','curve':[]},
  } for profile in saved['profiles'].values())

@pytest.mark.parametrize('raw', [{}, '{}', b'{}'])
@pytest.mark.parametrize('enabled', [False, True])
def test_first_run_slot_master_restore_recognises_registry_sentinel(monkeypatch, tmp_path, raw, enabled):
  client, params = _slot_client(monkeypatch, tmp_path, {'CustomPersonalities':enabled}, {
    PERSONALITY_PROFILES_PARAM:raw, 'CustomPersonalities':False,
  })
  assert client.post('/api/toggles/profiles/a/load').status_code == 200
  assert params.values['CustomPersonalities'] is enabled
  if enabled:
    saved = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
    assert saved is not None and saved['enabled']
  else:
    assert params.values[PERSONALITY_PROFILES_PARAM] == raw


@pytest.mark.parametrize('raw', ['null', '[]', '', '{broken', {'schemaVersion':99}, {'unexpected':1}])
def test_nonempty_or_nonobject_malformed_document_stays_blocked(monkeypatch, raw):
  client, params = _client(monkeypatch, {PERSONALITY_PROFILES_PARAM:raw, 'CustomPersonalities':False})
  before = dict(params.values)
  assert client.get('/api/personality_profiles').status_code == 409
  assert client.put('/api/params', json={'key':'CustomPersonalities','value':True}).status_code == 409
  assert params.values == before
