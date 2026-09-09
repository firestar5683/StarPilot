import math
from types import SimpleNamespace
import pytest
from openpilot.selfdrive.controls.lib.launch_boost import lead_allows_launch_boost

def lead(**changes):
  data=dict(status=True,dRel=7.,vLead=1.5,aLeadK=.8,yRel=0.,modelProb=1.,radar=False)
  data.update(changes)
  return SimpleNamespace(**data)

@pytest.mark.parametrize('changes', [dict(dRel=6.49),dict(vLead=.49),dict(aLeadK=.29),dict(aLeadK=-.01),
 dict(modelProb=.84),dict(yRel=1.76),dict(dRel=float('nan')),dict(aLeadK=float('inf')),dict(vLead=None)])
def test_weak_close_braking_or_uncertain_lead_blocks_extra(changes):
  assert not lead_allows_launch_boost([lead(**changes)],0,6)

def test_clear_pulling_away_lead_and_boundaries():
  assert lead_allows_launch_boost([lead(dRel=6.5,vLead=.5,aLeadK=.3)],.25,6)
  assert not lead_allows_launch_boost([lead(vLead=.5)],.26,6)
  assert lead_allows_launch_boost([lead(radar=True,modelProb=0)],0,6)

def test_nearer_weak_lead_cannot_be_overruled_by_farther_strong_lead():
  assert not lead_allows_launch_boost([lead(dRel=15),lead(dRel=7,aLeadK=.1)],0,6)
  assert not lead_allows_launch_boost([lead(dRel=7,aLeadK=.1),lead(dRel=15)],0,6)
  assert not lead_allows_launch_boost([],0,6)
  assert not lead_allows_launch_boost([lead(status=False)],0,6)
