"""Contracts, not comfort claims. These exercise real Python bodies, no solver."""
import ast
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from test_personality_longitudinal_profiles import StarPilotAcceleration, _document, _planner, _sm, _toggles
from openpilot.starpilot.common.longitudinal_personality_profiles import interpolate_category_curve

ROOT = Path(__file__).resolve().parents[3]


def _method(relative_path, class_name, name):
  tree = ast.parse((ROOT / relative_path).read_text())
  scope = {'np': np}
  # Only literal/numeric top-level constants, never imports/native initialisation.
  for node in tree.body:
    if isinstance(node, ast.Assign):
      try:
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<source-constant>', 'exec'), scope)
      except (NameError, AttributeError, TypeError):
        pass
  cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
  method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
  scope['DT_MDL'] = .05
  exec(compile(ast.Module(body=[method], type_ignores=[]), '<real-source-method>', 'exec'), scope)
  return scope[name]


@pytest.mark.parametrize('preset', ['eco', 'sport'])
def test_named_lead_presence_transition_matches_stock_floor(preset):
  doc = _document(); doc['profiles']['standard']['braking'] = {'preset': preset, 'curve': []}
  c = StarPilotAcceleration(_planner(v_cruise=5.0))
  outputs = []
  for lead in (False, True, False):
    c.update(10.0, _sm(lead=lead), _toggles(doc)); outputs.append(c.min_accel)
  assert outputs == ([-.5] * 3 if preset == 'eco' else [-2.] * 3)


def test_saved_custom_gate_is_preserved_not_silently_retuned():
  doc = _document(); doc['profiles']['standard']['braking'] = {'preset': 'custom', 'curve': [.5] * 10}
  c = StarPilotAcceleration(_planner())
  outputs = []
  for speed, lead in [(20.049999, False), (20.050001, False), (20.050001, True), (20.050001, False)]:
    c.update(speed, _sm(lead=lead), _toggles(doc)); outputs.append(c.min_accel)
  assert outputs == [-1., -.5, -1., -.5]


def test_curve_switch_and_reloaded_document_take_effect_next_update_without_hidden_filter():
  doc = _document(); c = StarPilotAcceleration(_planner()); t = _toggles(doc)
  c.update(0., _sm(), t); assert c.max_accel == 2.
  replacement = _document(); replacement['profiles']['standard']['acceleration'] = {'preset': 'sport_plus', 'curve': []}
  t.longitudinal_personality_profiles = replacement
  c.update(0., _sm(), t); assert c.max_accel == 3.5
  # Original saved document is not mutated by resolving another document.
  assert doc['profiles']['standard']['acceleration']['preset'] == 'standard'
  t.custom_personalities = False
  c.update(0., _sm(), t); assert c.max_accel == 2.


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -float('inf'), True])
def test_profile_curve_nonfinite_speed_is_explicitly_rejected(bad):
  with pytest.raises(ValueError):
    interpolate_category_curve('acceleration', bad, {'preset': 'eco', 'curve': []}, True)


@pytest.mark.parametrize('mode', [(False, False), (True, False), (False, True)])
@pytest.mark.parametrize('preset', ['eco', 'standard', 'sport', 'sport_plus'])
def test_named_acceleration_continuous_bounded_and_no_overshoot(mode, preset):
  ev, truck = mode
  config = {'preset': preset, 'curve': []}
  axis = [0., 5., 10., 15., 20., 25., 40.]
  for lo, hi in zip(axis[:-1], axis[1:]):
    ends = [interpolate_category_curve('acceleration', v, config, ev, truck) for v in (lo, hi)]
    samples = [interpolate_category_curve('acceleration', v, config, ev, truck) for v in np.linspace(lo, hi, 201)]
    assert all(np.isfinite(v) and min(ends) - 1e-12 <= v <= max(ends) + 1e-12 and v >= 0 for v in samples)
  for v in axis:
    left = interpolate_category_curve('acceleration', v - 1e-6, config, ev, truck)
    right = interpolate_category_curve('acceleration', v + 1e-6, config, ev, truck)
    assert abs(right - left) < 1e-10


def test_existing_headway_limiters_do_not_imply_symmetric_personality_slew():
  lane = _method('starpilot/controls/lib/starpilot_following.py', 'StarPilotFollowing', 'update_lane_change_gap')
  dynamic = _method('selfdrive/controls/lib/longitudinal_planner.py', 'LongitudinalPlanner', 'get_dynamic_t_follow')
  state = SimpleNamespace(t_follow=1.75, lane_change_t_follow=None)
  downstream = SimpleNamespace(effective_t_follow=None, dt=.05)
  result = []
  for base in [1.75, 1.25, 1.75]:
    state.t_follow = base
    lane(state, True, 20., {}, SimpleNamespace(lane_change_close_gap=False))
    effective = dynamic(downstream, state.t_follow, None, 20.)
    result.append((state.t_follow, effective))
  assert result[0] == (1.75, 1.75)
  # min(base, lane-ramp) allows a shorter base immediately; downstream dynamic
  # follow retains and slowly releases its previous larger value.
  assert result[1][0] == 1.25
  assert 1.25 < result[1][1] < 1.75
  # Do not add another filter without defining interaction with both existing ones.
  assert result[2][1] >= result[2][0]
