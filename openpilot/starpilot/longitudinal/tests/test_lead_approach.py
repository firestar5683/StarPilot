from dataclasses import replace
from types import SimpleNamespace as NS

import pytest

from openpilot.starpilot.longitudinal.lead_approach import (ApproachFrame, ApproachLead, LeadApproach,
                                                           LeadApproachKey, project)


DRIVE = 900_000_000
NOW = 1_000_000_000
KEY = LeadApproachKey('saved-setting-and-car', DRIVE)
NEAR = ApproachLead(True, False, 0.984, 38.9, 18.04, -0.026)


def frame(index=0, lead=NEAR):
  stamp = NOW + index * 50_000_000
  return ApproachFrame(stamp + 2_000_000, stamp, 21.535, lead)


def sample():
  stamps = dict.fromkeys(('modelV2', 'carState', 'radarState', 'carControl', 'controlsState', 'selfdriveState'), NOW - 2000000)
  messages = {
    'modelV2': NS(action=NS(shouldStop=False)),
    'carState': NS(vEgo=21.535, canValid=True, canTimeout=False, gasPressed=False, brakePressed=False, standstill=False),
    'radarState': NS(leadOne=NS(present=True, radar=False, modelProb=0.984, dRel=38.9,
                                vLead=18.04, aLeadK=-0.026), leadTwo=NS(present=True, radar=True, modelProb=1.0,
                                                                            dRel=10.0, vLead=0.0, aLeadK=-2.0)),
    'carControl': NS(longActive=True),
    'controlsState': NS(longControlState=1, forceDecel=False),
    'selfdriveState': NS(enabled=True),
  }
  sm = NS(logMonoTime=stamps, valid=dict.fromkeys(stamps, True), alive=dict.fromkeys(stamps, True))
  class SubMaster:
    logMonoTime, valid, alive = sm.logMonoTime, sm.valid, sm.alive
    def __getitem__(self, name):
      return messages[name]
  cp = NS(openpilotLongitudinalControl=True, passive=False, dashcamOnly=False, notCar=False)
  return SubMaster(), cp, messages


def test_original_vision_target_and_rise_release_rates():
  policy = LeadApproach(actuator_delay=0.2)
  outputs = [policy.step(KEY, frame(index), 1.45) for index in range(8)]
  assert outputs[0] == pytest.approx(1.50)
  assert outputs[1] == pytest.approx(1.55)
  assert outputs[-1] == pytest.approx(1.73104381, abs=1e-7)
  assert policy.step(KEY, frame(8, None), 1.45) == pytest.approx(outputs[-1] - 0.03)
  assert policy.step(KEY, frame(9, None), 1.45) == pytest.approx(outputs[-1] - 0.06)


def test_far_radar_is_noop_and_braking_near_radar_rises():
  policy = LeadApproach()
  assert policy.step(KEY, frame(0, ApproachLead(True, True, 0.0, 200.0, 20.0, 0.0)), 1.45) is None
  assert policy.step(KEY, frame(1, ApproachLead(True, True, 0.0, 45.0, 20.0, -1.0)), 1.45) == pytest.approx(1.50)


def test_project_only_fresh_active_lead_one_after_drive():
  sm, cp, messages = sample()
  projected = project(sm, cp, NOW, KEY)
  assert projected is not None and projected.lead == NEAR
  assert projected.model_ns == NOW - 2_000_000
  messages['radarState'].leadOne.present = False
  assert project(sm, cp, NOW, KEY).lead is None
  messages['radarState'].leadOne.present = True
  sm.logMonoTime['radarState'] = DRIVE
  assert project(sm, cp, NOW, KEY) is None
  sm.logMonoTime['radarState'] = NOW - 2_000_000
  sm.valid['modelV2'] = False
  assert project(sm, cp, NOW, KEY) is None


@pytest.mark.parametrize('change', [
  lambda sm, cp, msg: setattr(msg['carState'], 'canValid', False),
  lambda sm, cp, msg: setattr(msg['carState'], 'gasPressed', True),
  lambda sm, cp, msg: setattr(msg['controlsState'], 'forceDecel', True),
  lambda sm, cp, msg: setattr(msg['carControl'], 'longActive', False),
  lambda sm, cp, msg: setattr(msg['selfdriveState'], 'enabled', False),
  lambda sm, cp, msg: setattr(msg['modelV2'].action, 'shouldStop', True),
  lambda sm, cp, msg: setattr(cp, 'passive', True),
  lambda sm, cp, msg: setattr(msg['radarState'].leadOne, 'dRel', float('nan')),
])
def test_projection_rejects_unsafe_or_invalid_source(change):
  sm, cp, messages = sample()
  change(sm, cp, messages)
  assert project(sm, cp, NOW, KEY) is None


def test_invalid_frame_key_change_and_discontinuous_stamp_reset_state():
  policy = LeadApproach()
  assert policy.step(KEY, frame(), 1.45) == pytest.approx(1.50)
  assert policy.step(KEY, frame(1), 1.45) == pytest.approx(1.55)
  assert policy.step(KEY, replace(frame(2), lead=replace(NEAR, distance=float('nan'))), 1.45) is None
  assert policy.step(KEY, frame(3), 1.45) == pytest.approx(1.50)
  assert policy.step(KEY, frame(3), 1.45) is None
  assert policy.step(KEY, frame(4), 1.45) == pytest.approx(1.50)
  other = LeadApproachKey('changed-setting', DRIVE)
  assert policy.step(other, frame(5), 1.45) == pytest.approx(1.50)
  assert policy.step(other, frame(9), 1.45) is None
  assert policy.step(other, frame(10), 1.45) == pytest.approx(1.50)
  assert policy.step(other, frame(11), 1.45, blocked=True) is None
  assert policy.step(other, frame(12), 1.45) == pytest.approx(1.50)


def test_base_limit_and_low_probability_are_numerical_noops():
  policy = LeadApproach()
  assert policy.step(KEY, frame(0), 3.0) is None
  policy.reset()
  assert policy.step(KEY, frame(1, replace(NEAR, model_prob=0.84)), 1.45) is None
