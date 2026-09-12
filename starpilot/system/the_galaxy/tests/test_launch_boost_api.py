import json
from copy import deepcopy
import pytest
from test_personality_profiles_api import _client, the_galaxy
from openpilot.starpilot.common.longitudinal_personality_profiles import (
  PERSONALITY_IDS, LAUNCH_BOOST_LEVELS, PERSONALITY_PROFILES_PARAM,
  default_personality_profiles, profile_document, strict_profile_document,
)
URL="/api/personality_profiles/launch_boost"

@pytest.mark.parametrize("profile", PERSONALITY_IDS)
@pytest.mark.parametrize("level", LAUNCH_BOOST_LEVELS)
def test_save_readback_and_reload_each_personality_level(monkeypatch,profile,level):
  client,params=_client(monkeypatch,{"CustomPersonalities":True})
  before=client.get("/api/personality_profiles").get_json()
  assert before["launch_boost"]==dict.fromkeys(PERSONALITY_IDS,"high")
  response=client.put(URL,json={"profile":profile,"level":level,"expected":"high"})
  assert response.status_code==200,response.get_json()
  saved=client.get("/api/personality_profiles").get_json()
  assert saved["launch_boost"][profile]==level
  profiles=deepcopy(saved["profiles"]);assert profiles[profile].pop("launchBoost")==level
  assert profiles==before["profiles"]
  assert strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])["profiles"]==saved["profiles"]

def test_stale_launch_edit_rejected_but_unrelated_curve_edit_is_preserved(monkeypatch):
  client,params=_client(monkeypatch,{"CustomPersonalities":True})
  assert client.put(URL,json={"profile":"standard","level":"low","expected":"high"}).status_code==200
  assert client.put(URL,json={"profile":"standard","level":"off","expected":"high"}).status_code==409
  current=client.get("/api/personality_profiles").get_json()
  assert client.put("/api/personality_profiles",json={"profile":"standard","category":"braking","preset":"eco","curve":[],"expected":current["profiles"]["standard"]["braking"]}).status_code==200
  assert client.put(URL,json={"profile":"standard","level":"medium","expected":"low"}).status_code==200
  saved=client.get("/api/personality_profiles").get_json()
  assert saved["profiles"]["standard"]["braking"]["preset"]=="eco"
  assert saved["launch_boost"]["standard"]=="medium"
  assert client.put("/api/personality_profiles",json={"profile":"standard","category":"launchBoost","preset":"off","curve":[]}).status_code==400

@pytest.mark.parametrize("state",[{"IsOffroad":None},{"IsOnroad":True,"IsOffroad":True},{"IsOnroad":False,"IsOffroad":False}])
def test_unknown_or_onroad_state_rejects_without_writes(monkeypatch,state):
  client,params=_client(monkeypatch,state)
  assert client.put(URL,json={"profile":"standard","level":"off","expected":"high"}).status_code==403
  assert params.writes==[]

@pytest.mark.parametrize("payload",[{},None,{"profile":[],"level":"off","expected":"high"},{"profile":"standard","level":False,"expected":"high"},{"profile":"standard","level":"off","expected":True},{"profile":"standard","level":"off","expected":"high","extra":1}])
def test_malformed_payload_rejected(monkeypatch,payload):
  client,params=_client(monkeypatch)
  assert client.put(URL,json=payload).status_code==400
  assert params.writes==[]

def test_onroad_edit_uses_existing_personality_authoring_policy(monkeypatch):
  client,params=_client(monkeypatch,{"IsOnroad":True})
  assert client.put(URL,json={"profile":"traffic","level":"low","expected":"high"}).status_code==403
  assert params.writes == []

def test_failed_persistence_is_not_reported_as_saved(monkeypatch):
  client,params=_client(monkeypatch)
  monkeypatch.setattr(params,"put",lambda *args:None)
  assert client.put(URL,json={"profile":"standard","level":"off","expected":"high"}).status_code==500

def test_corrupt_document_not_overwritten(monkeypatch):
  client,params=_client(monkeypatch,{PERSONALITY_PROFILES_PARAM:'{"schemaVersion":99}'})
  assert client.put(URL,json={"profile":"standard","level":"off","expected":"high"}).status_code==409
  assert params.writes==[]

def test_road_state_rechecked_after_writer_lock(monkeypatch):
  client,params=_client(monkeypatch)
  class ChangeState:
    def __enter__(self):params.values["IsOnroad"]=True
    def __exit__(self,*args):pass
  monkeypatch.setattr(the_galaxy,"_PERSONALITY_PROFILES_WRITE_LOCK",ChangeState())
  assert client.put(URL,json={"profile":"standard","level":"off","expected":"high"}).status_code==403
  assert params.writes==[]


@pytest.mark.parametrize("extra", [{"preset": "custom"}, {"preset": "off", "expected": "low"}])
def test_launch_field_cannot_be_edited_as_a_curve_category(monkeypatch, extra):
  client, params = _client(monkeypatch)
  assert client.put(URL, json={"profile": "standard", "level": "low", "expected": "high"}).status_code == 200
  before = deepcopy(params.values)
  response = client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "launchBoost", "curve": [], **extra,
  })
  assert response.status_code == 400
  assert params.values == before
