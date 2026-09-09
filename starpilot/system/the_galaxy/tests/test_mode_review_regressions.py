"""Concrete regressions from the on-road handoff review; fake Params only."""
import ast
import copy
from itertools import product
from types import SimpleNamespace as NS

import pytest

from test_longitudinal_mode import Params, mode
from test_coherent_mode_handoff import nodes_in, execute, selfdrive_result, mode_lock, read_mode_values
from test_native_mode_presentation import big_layout


@pytest.mark.parametrize('bits', list(product([False, True], repeat=3)))
@pytest.mark.parametrize('target', list(mode.MODES))
def test_failed_write_at_every_boundary_keeps_old_or_requested_mode(bits, target):
  before = dict(zip(mode.MODE_KEYS, bits))
  old = mode.selected_mode(before)
  if old == target:
    return  # No-op normalisation is covered separately.
  for fail_at, after_write in product([1, 2, 3], [False, True]):
    params = Params(before | {'IsOffroad': False, 'IsOnroad': True})
    put = params.put_bool
    stored = []
    def failing(key, value):
      if len(params.writes) + 1 == fail_at and not after_write:
        params.writes.append((key, value))
        raise OSError('before write')
      put(key, value)
      stored.append(mode.selected_mode(params.values))
      if len(params.writes) == fail_at:
        raise OSError('after write')
    params.put_bool = failing
    with pytest.raises(mode.ModeError):
      mode.set_mode(params, target, before, lambda: True)
    assert len(params.writes) == fail_at
    assert set(stored) <= {old, target}
    assert mode.selected_mode(read_mode_values(params)) in {old, target}


def update_prefix():
  method = copy.deepcopy(next(node for node in ast.walk(nodes_in('starpilot/common/starpilot_variables.py'))
                              if isinstance(node, ast.FunctionDef) and node.name == 'update'))
  # Execute the real pre-mutation branch, including its early return.
  assert isinstance(method.body[0], ast.Assign) and isinstance(method.body[1], ast.Try)
  method.body = method.body[:2] + ast.parse('return mode_values, clear_update_flag').body
  ast.fix_missing_locations(method)
  env = {'read_mode_values': read_mode_values}
  execute([method], env)
  return env['update']


@pytest.mark.parametrize('existing', [False, True])
@pytest.mark.parametrize('failure', ['busy', 'unavailable'])
def test_startup_and_sync_refresh_dont_crash_or_mutate_old_snapshot(existing, failure, tmp_path):
  params, memory = Params(), Params()
  old = NS(longitudinal_mode_values={key: True for key in mode.MODE_KEYS}, sentinel={'untouched': True}) if existing else NS()
  before = copy.deepcopy(vars(old))
  variables = NS(params=params, params_memory=memory, starpilot_toggles=old)
  run = update_prefix()
  if failure == 'busy':
    with mode_lock(params, exclusive=True):
      result = run(variables)
  else:
    params.get_param_path = lambda: str(tmp_path/'missing'/'d')
    result = run(variables)
  assert vars(old) == before
  assert memory.get_bool('StarPilotTogglesUpdated')
  if existing:
    assert result is None  # Return before the first shared-object mutation.
  else:
    values, clear_update_flag = result
    assert values == {key: False for key in mode.MODE_KEYS}
    assert clear_update_flag is False  # Complete startup in Chill, retry later.


def test_comma3_retains_legacy_lateral_only_experimental_control():
  layout, state, _, params, _, _, _ = big_layout()
  state.CP.openpilotLongitudinalControl = False
  layout._sync_mode_selection()
  assert layout._toggles['ExperimentalMode'].visible
  assert not layout._mode_setting.visible
  assert not layout._mode_enabled()
  assert not params.writes
  state.CP.openpilotLongitudinalControl = True
  layout._sync_mode_selection()
  assert not layout._toggles['ExperimentalMode'].visible
  assert layout._mode_setting.visible


@pytest.mark.parametrize('previous,plan,conditional', list(product([False, True], repeat=3)))
def test_old_replay_without_complete_plan_retains_dom_behaviour(previous, plan, conditional):
  cached = NS(conditional_experimental_mode=conditional, conditional_chill_mode=False)
  assert selfdrive_result(plan, previous=previous, cached=cached, replay=True) is (plan if conditional else previous or plan)
  assert selfdrive_result(plan, previous=previous, cached=cached, replay=True, safe=True) is False


def test_live_params_thread_never_uses_replay_fallback():
  method = next(node for node in ast.walk(nodes_in('selfdrive/selfdrived/selfdrived.py'))
                if isinstance(node, ast.FunctionDef) and node.name == 'params_thread')
  branch = next(node for node in ast.walk(method) if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == 'REPLAY')
  calls = []
  state = NS(params=Params({'ExperimentalMode': True}), params_memory=Params(), safe_mode=False,
             experimental_mode=False, starpilot_toggles=NS(conditional_experimental_mode=False), CP=object())
  env = dict(self=state, REPLAY=False, request_mode_refresh=lambda *args: calls.append('refresh'), experimental_mode_available=lambda cp: True)
  execute([branch], env)
  assert state.experimental_mode is False and calls == ['refresh']
  env['REPLAY'] = True
  execute([branch], env)
  assert state.experimental_mode is True and calls == ['refresh']
