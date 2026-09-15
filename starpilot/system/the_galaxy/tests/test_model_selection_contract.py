"""Actual Flask Active Big contract with in-memory Params, no native/device I/O."""
import pytest
from test_personality_profiles_api import _client, the_galaxy

@pytest.mark.parametrize('profile,onroad,expected', [('big',False,200),('small',False,400),('big',True,403),('invalid',False,400)])
def test_active_big_empty_contract(monkeypatch, profile, onroad, expected):
  client, params = _client(monkeypatch, {'IsOnroad':onroad})
  calls=[]
  monkeypatch.setattr(the_galaxy,'disable_big_model_profile',lambda p:calls.append(p))
  monkeypatch.setattr(the_galaxy,'normalize_model_lab_config',lambda raw:{'enabled':False})
  response=client.put('/api/models/active',json={'profile':profile,'model':''})
  assert response.status_code == expected, response.get_json()
  assert len(calls) == (expected == 200)
  if expected == 200:
    assert response.get_json()['model'] == ''
    assert response.get_json()['profile'] == 'big'
