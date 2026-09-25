from types import SimpleNamespace as NS
from unittest.mock import patch
import pytest

from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.starpilot.longitudinal.lead_behavior import adjust, departure_floor, inside_gap_cap
from openpilot.starpilot.longitudinal.tests.test_conditional_handoff import Frame, NOW, DRIVE


def lead(**values):
  return NS(present=True, radar=True, dRel=6., vLead=2., aLeadK=.3, modelProb=.99, yRel=0., **values)


def test_departure_formula_and_native_plan_ceiling():
  obj = lead()
  assert departure_floor(obj, 0., .2) == pytest.approx(.3)
  sm = Frame()
  sm['carState'].vEgo = 0.
  sm['carState'].standstill = True
  sm['selfdriveState'].experimentalMode = True
  sm['radarState'].leadOne = vars(obj)
  sm['radarState'].leadTwo.present = False
  sm['modelV2'].action.shouldStop = False
  cp = NS(openpilotLongitudinalControl=True, passive=False, dashcamOnly=False, notCar=False)
  args = {'target': .2, 'sm': sm, 'cp': cp, 'now_ns': NOW, 'key': ('settings', 1, DRIVE, 'conditional_experimental'),
          'follow_seconds': 1.45, 'mpc_target': .8, 'cruise_target': .9, 'model_target': .2,
          'stopping': False, 'force_stop': False, 'traffic_mode': False, 'accel_min': -3.5}
  assert adjust(**args) == pytest.approx(.3)
  assert adjust(**(args | {'mpc_target': .21})) == .21
  for changes in ({'stopping': True}, {'force_stop': True}, {'traffic_mode': True}, {'key': None}):
    assert adjust(**(args | changes)) == .2
  sm['carState'].brakePressed = True
  assert adjust(**args) == .2
  sm['carState'].brakePressed = False
  sm.logMonoTime['radarState'] = NOW - 250_000_001
  assert adjust(**args) == .2


def test_inside_gap_braking_keeps_stronger_original_braking():
  obj = lead()
  obj.vLead = 18.
  obj.dRel = 15.
  value = inside_gap_cap(obj, 20., 1.45, -3.5)
  assert value is not None and -.65 <= value < 0.
  obj.dRel = 80.
  assert inside_gap_cap(obj, 20., 1.45, -3.5) is None
  obj.dRel = 15.
  obj.yRel = 2.
  assert inside_gap_cap(obj, 20., 1.45, -3.5) is None
  obj.yRel = 0.
  obj.radar = False
  obj.modelProb = .94
  assert inside_gap_cap(obj, 20., 1.45, -3.5) is None


@pytest.mark.parametrize('case', ['none', 'depart', 'close', 'braking', 'stopping', 'stale', 'pedal', 'outside_lane'])
def test_native_planner_lead_response_and_unchanged_exclusions(case):
  cp = CarInterface.get_non_essential_params(CAR.HYUNDAI_IONIQ_6)
  cp.openpilotLongitudinalControl = True
  speed = 0. if case == 'depart' else 20.
  original, current = (LongitudinalPlanner(cp, init_v=speed) for _ in range(2))
  key = ('settings', 1, DRIVE, 'conditional_experimental')
  changed = 0
  for tick in range(40):
    sm = Frame()
    now = NOW + tick * 50_000_000
    sm.logMonoTime = dict.fromkeys(sm, now - 5_000_000)
    sm['carState'].vEgo = speed
    sm['carState'].brakePressed = case == 'pedal'
    sm['selfdriveState'].experimentalMode = case in ('depart', 'braking', 'stopping')
    sm['modelV2'].action.desiredAcceleration = -2. if case == 'braking' else .2
    sm['modelV2'].action.shouldStop = case == 'stopping'
    lead = sm['radarState'].leadOne
    lead.present = case != 'none'
    lead.vLead = lead.vLeadK = 2. if case == 'depart' else 18.
    lead.vRel = lead.vLead - speed
    lead.dRel = 6. if case == 'depart' else 15.
    lead.aLeadK = .3 if case == 'depart' else 0.
    lead.radar, lead.modelProb = True, .99
    lead.yRel = 2. if case == 'outside_lane' else 0.
    sm['radarState'].leadTwo.present = False
    if case == 'stale':
      sm.logMonoTime['radarState'] = now - 250_000_001
    with patch('openpilot.selfdrive.controls.lib.longitudinal_planner.adjust_lead_behavior', side_effect=lambda **kw: kw['target']):
      original.update(sm, now_ns=now, conditional_handoff=key)
    current.update(sm, now_ns=now, conditional_handoff=key)
    assert original.mpc.solution_status == current.mpc.solution_status == 0
    before, after = float(original.output_a_target), float(current.output_a_target)
    assert -3.5 <= after <= 2.
    changed += before != after
    if case not in ('depart', 'close'):
      assert before == after
    elif case == 'depart':
      assert after >= before
  assert bool(changed) == (case in ('depart', 'close'))
