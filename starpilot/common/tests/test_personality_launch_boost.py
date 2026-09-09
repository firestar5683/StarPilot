import json
from copy import deepcopy
from types import SimpleNamespace
import pytest
from openpilot.starpilot.common.longitudinal_personality_profiles import (
  LAUNCH_BOOST_LEVELS, PERSONALITY_IDS, default_personality_profiles, profile_document,
  migrate_profile_document, strict_profile_document, update_personality_launch_boost,
  update_personality_profile, resolve_personality_launch_boost, synchronise_profile_document_enabled,
)

def document():
  return profile_document(default_personality_profiles(False), enabled=True)

@pytest.mark.parametrize("personality", PERSONALITY_IDS)
@pytest.mark.parametrize("level", LAUNCH_BOOST_LEVELS)
def test_launch_round_trip_preserves_other_profiles_and_legacy_curves(personality, level):
  original=document()
  original["profiles"]["aggressive"]["acceleration"]={"preset":"custom","curve":[4.0]*10,"legacyCurve":[4.1]*7}
  snapshot=deepcopy(original)
  saved=deepcopy(original)
  saved["profiles"]=update_personality_launch_boost(original["profiles"],personality,level)
  assert original==snapshot
  assert "launchBoost" not in original["profiles"][personality]
  loaded=strict_profile_document(json.dumps(saved))
  assert loaded["profiles"][personality].pop("launchBoost")==level
  assert loaded==original

def test_legacy_document_and_disabled_profile_keep_original_high():
  doc=document()
  assert migrate_profile_document(doc)==doc
  toggles=SimpleNamespace(custom_personalities=True,longitudinal_personality_profiles=doc)
  assert resolve_personality_launch_boost(toggles,False,1)=="high"
  doc["profiles"]=update_personality_launch_boost(doc["profiles"],"standard","off")
  assert resolve_personality_launch_boost(toggles,False,1)=="off"
  toggles.standard_personality_profile=False
  assert resolve_personality_launch_boost(toggles,False,1)=="high"
  toggles.standard_personality_profile=True; toggles.custom_personalities=False
  assert resolve_personality_launch_boost(toggles,False,1)=="high"
  toggles.custom_personalities=True;doc["enabled"]=False
  assert resolve_personality_launch_boost(toggles,False,1)=="high"

def test_runtime_selects_each_personality_and_traffic_override():
  doc=document()
  for personality,level in zip(PERSONALITY_IDS,LAUNCH_BOOST_LEVELS):
    doc["profiles"]=update_personality_launch_boost(doc["profiles"],personality,level)
  toggles=SimpleNamespace(custom_personalities=True,longitudinal_personality_profiles=doc)
  assert [resolve_personality_launch_boost(toggles,False,p) for p in range(3)]==["low","medium","high"]
  assert resolve_personality_launch_boost(toggles,True,1)=="off"
  assert resolve_personality_launch_boost(toggles,False,True)=="high"

@pytest.mark.parametrize("level", [None,True,1,{},[],"LOW","sport"])
def test_invalid_level_is_rejected_without_overwriting_profiles(level):
  doc=document()
  with pytest.raises(ValueError):update_personality_launch_boost(doc["profiles"],"standard",level)
  doc["profiles"]["standard"]["launchBoost"]=level
  assert strict_profile_document(doc) is None

def test_curve_edit_and_master_switch_preserve_launch_selection():
  doc=document()
  doc["profiles"]=update_personality_launch_boost(doc["profiles"],"standard","low")
  doc["profiles"]=update_personality_profile(doc["profiles"],"standard","braking","eco",[],False)
  assert synchronise_profile_document_enabled(doc,False,False)["profiles"]["standard"]["launchBoost"]=="low"
