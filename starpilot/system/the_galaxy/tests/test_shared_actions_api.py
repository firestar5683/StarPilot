import pytest
from test_navigation_params import _params_client, the_galaxy
from openpilot.starpilot.common.controller_actions import CONTROLLER_ACTION_SET_SPEED, CONTROLLER_ACTION_CYCLE_PERSONALITY
from openpilot.starpilot.common.favorite_slots import FAVORITE_SLOTS_PARAM, normalize_favorite_slots


@pytest.mark.parametrize('metric,value,status', [(False,30,200),(True,100,200),(False,4,400),(False,91,400),(True,146,400),(False,True,400),(False,None,400),(False,'30',400)])
def test_shared_speed_slot_validates_value_and_preserves_flags(monkeypatch,metric,value,status):
  client,params=_params_client(monkeypatch,{'IsMetric':metric},'tici')
  options=[{'key':CONTROLLER_ACTION_SET_SPEED,'label':'Set Speed To','action':'controller'}]
  monkeypatch.setattr(the_galaxy,'FAVORITE_SLOTS_PARAM',FAVORITE_SLOTS_PARAM)
  monkeypatch.setattr(the_galaxy,'normalize_favorite_slots',normalize_favorite_slots)
  monkeypatch.setattr(the_galaxy,'_favorite_slot_values',lambda _: {})
  monkeypatch.setattr(the_galaxy,'_get_available_favorite_slot_options',lambda:options)
  monkeypatch.setattr(the_galaxy,'update_starpilot_toggles',lambda:None)
  slot={'key':CONTROLLER_ACTION_SET_SPEED,'label':'Set Speed To','value':value,'enabled':True,'show_onroad':True}
  response=client.put('/api/favorites/slots',json={'slots':[slot]})
  assert response.status_code==status,response.json
  if status==200:
    assert response.json['slots'][0]==slot
    assert response.json['is_metric']==metric
    assert params.values[FAVORITE_SLOTS_PARAM][0]==slot
  else:assert not params.writes


def test_personality_action_can_be_assigned_to_favourites(monkeypatch):
  client,params=_params_client(monkeypatch,{},'tici')
  options=[{'key':CONTROLLER_ACTION_CYCLE_PERSONALITY,'label':'Cycle Driving Personality','action':'controller'}]
  monkeypatch.setattr(the_galaxy,'FAVORITE_SLOTS_PARAM',FAVORITE_SLOTS_PARAM)
  monkeypatch.setattr(the_galaxy,'normalize_favorite_slots',normalize_favorite_slots)
  monkeypatch.setattr(the_galaxy,'_favorite_slot_values',lambda _: {})
  monkeypatch.setattr(the_galaxy,'_get_available_favorite_slot_options',lambda:options)
  monkeypatch.setattr(the_galaxy,'update_starpilot_toggles',lambda:None)
  slot={'key':CONTROLLER_ACTION_CYCLE_PERSONALITY,'enabled':True,'show_onroad':False,'label':'Cycle Driving Personality'}
  response=client.put('/api/favorites/slots',json={'slots':[slot]})
  assert response.status_code==200,response.json
  assert response.json['slots'][0]==slot
