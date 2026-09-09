"""Exact class and planner branch, fake clocks/scene/Params; no native runtime."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import pytest

ROOT = Path(__file__).resolve().parents[3]

def make_modes():
  now = [100.0]
  statuses = {'OFF': 0, 'LEAD': 1, 'SPEED': 2, 'USER_EXPERIMENTAL': 99, 'USER_OVERRIDDEN': 99}
  memory = {}
  params = NS(get_bool=lambda _: False)
  planner = NS(params=params, params_memory=NS(put_int=lambda k,v: memory.update({k:v})))
  ns = {'time': NS(monotonic=lambda: now[0]), 'CV': NS(MPH_TO_MS=0.44704), 'CCStatus': statuses, 'CEStatus': statuses,
        'restore_persisted_cc_state': lambda *_: memory.get('manual', 0), 'restore_persisted_ce_state': lambda *_: memory.get('manual', 0),
        'is_manual_cc_status': lambda s: s == 99, 'is_manual_ce_status': lambda s: s == 99,
        'FirstOrderFilter': lambda *args: NS(x=0), 'DT_MDL': .05}
  for file, name in [('conditional_chill_mode.py','ConditionalChillMode'), ('conditional_experimental_mode.py','ConditionalExperimentalMode')]:
    path = ROOT/'starpilot/controls/lib'/file
    cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == name)
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(path), 'exec'), ns)
  cem = ns['ConditionalExperimentalMode'](planner)
  ccm = ns['ConditionalChillMode'](planner, cem)
  planner.starpilot_cem, planner.starpilot_ccm = cem, ccm
  ccm._refresh_detector = lambda *_: None
  ccm._get_chill_status = lambda *_: (1, False)
  ccm._has_hard_veto = lambda *a, **k: False
  cem.update_conditions = lambda *_: None
  cem.check_conditions = lambda *_: False
  cem.stop_sign_and_light = lambda *_: None
  return planner, now, memory

def branch(planner, mode):
  path = ROOT/'starpilot/controls/starpilot_planner.py'
  node = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.If) and ast.unparse(n.test).startswith('conditional_tracking_active and'))
  exec(compile(ast.Module(body=[node],type_ignores=[]), str(path), 'exec'),
       {'self': planner, 'conditional_tracking_active': True, 'starpilot_toggles': NS(conditional_experimental_mode=mode=='cem', conditional_chill_mode=mode=='ccm'), 'v_ego':20, 'v_cruise':30, 'sm':{}, 'PLANNER_TIME':10})

@pytest.mark.parametrize('absence', [.1, 100])
@pytest.mark.parametrize('other', ['fixed', 'cem'])
def test_ccm_reentry_requires_new_confirmation(absence, other):
  p, now, _ = make_modes()
  p.starpilot_ccm.update(20,30,{},NS())
  original_update = p.starpilot_cem.update
  p.starpilot_cem.update = lambda *_: None
  branch(p, other)
  p.starpilot_cem.update = original_update
  now[0] += absence
  p.starpilot_ccm.update(20,30,{},NS())
  assert p.starpilot_ccm.experimental_mode
  assert p.starpilot_ccm._candidate_since == now[0]
  now[0] += 1.01
  p.starpilot_ccm.update(20,30,{},NS())
  assert not p.starpilot_ccm.experimental_mode

@pytest.mark.parametrize('other', ['fixed', 'ccm'])
def test_cem_reentry_does_not_inherit_mode_hold(other):
  p, now, _ = make_modes()
  cem = p.starpilot_cem
  cem.prev_experimental_mode = True
  cem.mode_hold_until = now[0] + .5
  cem.slow_lead_mode_hold_until = now[0] + 1.5
  original_update = p.starpilot_ccm.update
  p.starpilot_ccm.update = lambda *_: None
  branch(p, other)
  p.starpilot_ccm.update = original_update
  now[0] += .1
  cem.update(20, {'carState': NS(standstill=False)}, NS(conditional_lead=False,conditional_open_road=False))
  assert not cem.experimental_mode

@pytest.mark.parametrize('other', ['fixed', 'cem'])
def test_ccm_manual_override_survives_deactivation(other):
  p, _, memory = make_modes()
  memory['manual'] = 99
  p.starpilot_cem.update = lambda *_: None
  branch(p, other)
  p.starpilot_ccm.update(20,30,{},NS())
  assert p.starpilot_ccm.experimental_mode
  assert memory['manual'] == 99

def test_cem_deactivation_retains_shared_hazard_detector_state():
  p, _, _ = make_modes()
  cem = p.starpilot_cem
  cem.stop_light_detected = True
  cem.stop_light_filter.x = .9
  cem.standstill_stop_reason = 'sign'
  branch(p, 'fixed')
  assert cem.stop_light_detected and cem.stop_light_filter.x == .9
  assert cem.standstill_stop_reason == 'sign'


@pytest.mark.parametrize('condition', ['none', 'veto', 'safe'])
def test_ccm_reentry_still_honors_current_scene_and_safety(condition):
  p, now, _ = make_modes()
  ccm = p.starpilot_ccm
  ccm.update(20,30,{},NS())
  branch(p, 'fixed')
  now[0] += 100
  if condition == 'none':
    ccm._get_chill_status = lambda *_: (0, False)
  elif condition == 'veto':
    ccm._has_hard_veto = lambda *a, **k: True
  else:
    p.params.get_bool = lambda key: key == 'SafeMode'
  ccm.update(20,30,{},NS())
  assert ccm.experimental_mode == (condition != 'safe')
  assert ccm._candidate_since == 0


def test_cem_manual_override_survives_inactive_interval():
  p, _, memory = make_modes()
  memory['manual'] = 99
  branch(p, 'fixed')
  p.starpilot_cem.update(20, {'carState': NS(standstill=False)}, NS())
  assert p.starpilot_cem.experimental_mode
  assert memory['manual'] == 99
