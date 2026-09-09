"""Isolated real AST seams + real OS advisory locks, never native/device Params."""
import ast
import copy
import multiprocessing
from itertools import product
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from test_longitudinal_mode import Params, mode
from openpilot.starpilot.common.longitudinal_mode import mode_lock, read_mode_values, request_mode_refresh

ROOT = Path(__file__).resolve().parents[4]


def nodes_in(path):
  return ast.parse((ROOT / path).read_text())


def execute(nodes, env):
  exec(compile(ast.Module(body=nodes, type_ignores=[]), '<runtime AST>', 'exec'), env)


def load_toggles(params, *, capable=True, safe=False):
  tree = nodes_in('starpilot/common/starpilot_variables.py')
  assignments = sorted((node for node in ast.walk(tree) if isinstance(node, ast.Assign)), key=lambda node: node.lineno)
  start = next(node.lineno for node in assignments if isinstance(node.targets[0], ast.Attribute) and node.targets[0].attr == 'longitudinal_mode_values')
  end = next(node.lineno for node in assignments if isinstance(node.targets[0], ast.Attribute) and node.targets[0].attr == 'conditional_chill_launch_assist')
  toggle = NS(openpilot_longitudinal=capable, experimental_mode_available=capable, safe_mode=safe)
  get_value = lambda key, condition=True, **kwargs: params.get(key) if condition else False
  execute([node for node in assignments if start <= node.lineno <= end],
          dict(toggle=toggle, self=NS(params=params, get_value=get_value), mode_values=read_mode_values(params), speed_conversion=1))
  return toggle


def plan_result(toggles, cem=True, ccm=True, slc=False):
  tree = nodes_in('starpilot/controls/starpilot_planner.py')
  method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == 'publish')
  start = next(i for i, node in enumerate(method.body) if isinstance(node, ast.Assign)
               and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'conditional_experimental_mode')
  plan = NS()
  execute(method.body[start:start + 3], dict(starpilot_toggles=toggles, starpilotPlan=plan,
          self=NS(starpilot_cem=NS(experimental_mode=cem), starpilot_ccm=NS(experimental_mode=ccm),
                  starpilot_vcruise=NS(slc=NS(experimental_mode=slc)))))
  return plan.experimentalMode


def selfdrive_result(plan, *, previous=False, cached=None, safe=False, capable=True, replay=False):
  tree = nodes_in('selfdrive/selfdrived/selfdrived.py')
  method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == 'update_events')
  nodes = [node for node in method.body if isinstance(node, ast.Assign)
           and isinstance(node.targets[0], ast.Attribute) and node.targets[0].attr == 'experimental_mode']
  assert len(nodes) == 1
  state = NS(experimental_mode=previous, starpilot_toggles=cached or NS(conditional_experimental_mode=False, conditional_chill_mode=False), safe_mode=safe, CP=object(),
             sm={'starpilotPlan': NS(experimentalMode=plan)})
  execute(nodes, dict(self=state, experimental_mode_available=lambda cp: capable, REPLAY=replay))
  return state.experimental_mode


@pytest.mark.parametrize('bits', list(product([False, True], repeat=3)))
@pytest.mark.parametrize('target', mode.MODES)
def test_onroad_transitions_never_publish_clear_all_intermediates(bits, target):
  params = Params(dict(zip(mode.MODE_KEYS, bits)) | {'IsOffroad': False, 'IsOnroad': True, 'CECurves': True, 'CCMLaunchAssist': True})
  published = load_toggles(params)
  old_values = published.longitudinal_mode_values.copy()
  observed = []
  put = params.put_bool

  def interleaved_write(key, value):
    nonlocal published
    put(key, value)
    # This is the real loader selection seam attempted at each write boundary.
    with pytest.raises(BlockingIOError):
      load_toggles(params)
    assert published.longitudinal_mode_values == old_values
    observed.append(selfdrive_result(plan_result(published)))

  params.put_bool = interleaved_write
  result = mode.set_mode(params, target, old_values, lambda: True)
  assert observed == [selfdrive_result(plan_result(published))] * len(params.writes)
  published = load_toggles(params)
  assert published.longitudinal_mode_values == result['values']
  assert published.conditional_curves is published.conditional_experimental_mode
  assert published.conditional_chill_launch_assist is published.conditional_chill_mode
  assert selfdrive_result(plan_result(published)) is (target != 'chill')


def child_read(path, pipe):
  params = NS(get_param_path=lambda: path, get_bool=lambda key: True)
  try:
    read_mode_values(params)
    pipe.send('read')
  except BlockingIOError:
    pipe.send('busy')
  finally:
    pipe.close()


def test_lock_is_cross_process_not_only_a_python_mutex():
  params = Params()
  ctx = multiprocessing.get_context('fork')
  receive, send = ctx.Pipe(duplex=False)
  with mode_lock(params, exclusive=True):
    child = ctx.Process(target=child_read, args=(params.get_param_path(), send))
    child.start()
    assert receive.poll(3), 'nonblocking read hung'
    assert receive.recv() == 'busy'
    child.join(3)
    assert child.exitcode == 0
  assert read_mode_values(params)['ConditionalExperimental'] is True
  send.close()
  receive.close()


def test_reader_excludes_participating_writer_between_key_reads():
  params = Params()
  before = {key: params.get_bool(key) for key in mode.MODE_KEYS}
  get = params.get_bool
  attempts = []
  def read(key):
    if key in mode.MODE_KEYS:
      with pytest.raises(mode.ModeError) as error:
        mode.set_mode(params, 'chill', before, lambda: True)
      assert error.value.status == 503
      attempts.append(key)
    return get(key)
  params.get_bool = read
  assert read_mode_values(params) == before
  assert attempts == list(mode.MODE_KEYS)
  assert not params.writes


@pytest.mark.parametrize('safe,capable', [(True, True), (False, False)])
def test_effective_plan_cannot_bypass_safety_or_vehicle_capability(safe, capable):
  assert selfdrive_result(True, safe=safe, capable=capable) is False
  params = Params({'ConditionalExperimental': False, 'ExperimentalMode': True})
  assert load_toggles(params, safe=safe, capable=capable).experimental_mode is False
  params.values.update(ConditionalExperimental=True, ConditionalChill=True)
  loaded = load_toggles(params, safe=safe, capable=capable)
  assert not loaded.conditional_experimental_mode and not loaded.conditional_chill_mode


@pytest.mark.parametrize('previous,plan,cached_cem,cached_ccm', list(product([False, True], repeat=4)))
def test_current_plan_wins_over_all_stale_cached_flags(previous, plan, cached_cem, cached_ccm):
  cached = NS(conditional_experimental_mode=cached_cem, conditional_chill_mode=cached_ccm)
  assert selfdrive_result(plan, previous=previous, cached=cached) is plan


def test_conditional_defaults_and_slc_override_preserved():
  params = Params({'ExperimentalMode': True})
  assert plan_result(load_toggles(params), cem=False) is False  # CEM masks dormant EXP
  assert plan_result(load_toggles(params), cem=False, slc=True) is True
  params.values.update(ConditionalExperimental=False, ConditionalChill=True)
  assert plan_result(load_toggles(params), ccm=False) is False
  assert plan_result(load_toggles(params), ccm=True) is True
  params.values.update(ConditionalChill=False)
  assert plan_result(load_toggles(params), cem=False, ccm=False) is True


def test_poll_retries_until_published_and_honors_unnotified_external_writes():
  params, memory = Params(), Params()
  published = load_toggles(params)
  request_mode_refresh(params, memory, published)
  assert not memory.writes
  # Dom/nonparticipating writer, without calling the Galaxy notification helper.
  params.values.update(ConditionalExperimental=False, ExperimentalMode=True)
  request_mode_refresh(params, memory, published)
  assert memory.writes[-1] == ('StarPilotTogglesUpdated', True)
  in_flight = load_toggles(params)
  params.values.update(ExperimentalMode=False, ConditionalChill=True)
  memory.values['StarPilotTogglesUpdated'] = False  # Worker consumes first signal.
  request_mode_refresh(params, memory, published)
  assert memory.get_bool('StarPilotTogglesUpdated')
  # Even publication of the older in-flight update must not suppress retry.
  memory.values['StarPilotTogglesUpdated'] = False
  request_mode_refresh(params, memory, in_flight)
  assert memory.get_bool('StarPilotTogglesUpdated')
  published = load_toggles(params)
  memory.writes.clear()
  request_mode_refresh(params, memory, published)
  assert not memory.writes
  with mode_lock(params, exclusive=True):
    request_mode_refresh(params, memory, published)
  assert not memory.writes


def test_background_failure_preserves_entire_old_object_and_requeues():
  params, memory = Params({'ExperimentalMode': True}), Params()
  published = load_toggles(params)
  variables = NS(starpilot_toggles=published, params_memory=memory)
  node = next(node for node in nodes_in('starpilot/starpilot_process.py').body
              if isinstance(node, ast.FunctionDef) and node.name == 'update_toggles_in_background')
  def reload(updated, *args, **kwargs):
    updated.starpilot_toggles.experimental_mode = False
    load_toggles(params)
  env = dict(copy=copy, update_toggles=reload)
  execute([node], env)
  result = {}
  with mode_lock(params, exclusive=True), pytest.raises(BlockingIOError):
    env['update_toggles_in_background'](result, variables, True, None, None, True, params, published)
  assert result == {'failed': True}
  assert variables.starpilot_toggles is published
  assert published.experimental_mode is True
  assert published.conditional_experimental_mode
  assert memory.get_bool('StarPilotTogglesUpdated')


@pytest.mark.parametrize('fail_at', [1, 2, 3])
def test_failed_write_releases_lock_without_enabling_or_rolling_back(fail_at):
  params = Params({'IsOffroad': False, 'IsOnroad': True}, fail_at=fail_at)
  before = read_mode_values(params)
  with pytest.raises(mode.ModeError):
    mode.set_mode(params, 'experimental', before, lambda: True)
  assert len(params.writes) == fail_at
  assert mode.selected_mode(params.values) in {mode.selected_mode(before), 'experimental'}
  assert read_mode_values(params) == {key: params.values[key] for key in mode.MODE_KEYS}


def test_lock_unavailable_fails_closed_without_writes(tmp_path):
  params = Params({'IsOffroad': False, 'IsOnroad': True})
  params.get_param_path = lambda: str(tmp_path / 'missing' / 'd')
  with pytest.raises(mode.ModeError) as error:
    mode.set_mode(params, 'experimental', params.values, lambda: True)
  assert error.value.status == 503
  assert not params.writes


def test_params_thread_no_longer_overwrites_experimental_from_live_params():
  method = next(node for node in ast.walk(nodes_in('selfdrive/selfdrived/selfdrived.py'))
                if isinstance(node, ast.FunctionDef) and node.name == 'params_thread')
  replay = next(node for node in ast.walk(method) if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == 'REPLAY')
  assert not any(isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store)
                 and node.attr == 'experimental_mode' for branch in replay.orelse for node in ast.walk(branch))
  assert any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == 'request_mode_refresh' for node in ast.walk(method))


@pytest.mark.parametrize('guard,capable', [({'SafeMode': True}, True), ({'SafeMode': None}, True),
  ({'IsOffroad': None}, True), ({'IsOnroad': None}, True), ({'IsOffroad': True}, True), ({}, False)])
def test_onroad_safety_state_and_capability_fail_closed(guard, capable):
  params = Params({'IsOffroad': False, 'IsOnroad': True, **guard})
  with pytest.raises(mode.ModeError) as error:
    mode.set_mode(params, 'experimental', params.values, lambda: capable)
  assert error.value.status == 403
  assert not params.writes


def test_onroad_api_accepts_exact_snapshot_but_rejects_stale_and_busy():
  from test_longitudinal_mode_api import client_for
  params = Params({'IsOffroad': False, 'IsOnroad': True})
  client, signals = client_for(params)
  before = client.get('/api/longitudinal_mode').json
  assert before['locked'] is False
  response = client.put('/api/longitudinal_mode', json={'mode': 'conditional_chill', 'expected': before['values']})
  assert response.status_code == 200
  assert response.json['mode'] == 'conditional_chill'
  writes = params.writes.copy()
  response = client.put('/api/longitudinal_mode', json={'mode': 'experimental', 'expected': before['values']})
  assert response.status_code == 409
  assert params.writes == writes
  with mode_lock(params, exclusive=True):
    assert client.get('/api/longitudinal_mode').status_code == 503
  assert client.get('/api/longitudinal_mode').json['mode'] == 'conditional_chill'
