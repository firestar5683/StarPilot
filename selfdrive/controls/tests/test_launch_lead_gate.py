from types import SimpleNamespace
import pytest
from openpilot.selfdrive.controls.lib.launch_boost import LaunchLeadGate

def lead(gap=7, accel=0.8, **other):
  return SimpleNamespace(status=True,dRel=gap,aLeadK=accel,**other)

@pytest.mark.parametrize('gap,accel,allowed',[(7,.49,False),(7,0,False),(7,-.5,False),(7,.5,True),(12,.1,True),(20,-.5,True),(3,.8,True)])
def test_only_close_slow_or_braking_lead_blocks(gap,accel,allowed):
  assert LaunchLeadGate().allows([lead(gap,accel)]) is allowed

def test_release_hysteresis():
  gate=LaunchLeadGate()
  assert not gate.allows([lead(7,.4)])
  assert not gate.allows([lead(12.5,.55)])
  assert gate.allows([lead(13,.1)])
  assert gate.allows([lead(12.5,.1)])
  assert not gate.allows([lead(11.9,.49)])
  assert gate.allows([lead(7,.6)])
  assert gate.allows([lead(7,.55)])

def test_absent_lead_clears_block_and_nearest_lead_wins():
  gate=LaunchLeadGate()
  assert not gate.allows([lead(30,.8),lead(7,.1)])
  assert gate.allows([])
  assert gate.allows([SimpleNamespace(status=False)])
  assert not gate.allows([lead(7,-.1)])
  gate.reset()
  assert gate.allows([lead(12.5,.1)])

@pytest.mark.parametrize('reading',[lead(float('nan'),.8),lead(7,float('nan')),SimpleNamespace(status=True)])
def test_unusable_reported_lead_cannot_authorize_extra(reading):
  assert not LaunchLeadGate().allows([reading])
