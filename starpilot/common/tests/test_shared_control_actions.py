import ast
from pathlib import Path

import pytest
from openpilot.starpilot.common import favorite_slots as favorites
from openpilot.starpilot.common.controller_actions import CONTROLLER_ACTION_KEYS, CONTROLLER_ACTION_SET_SPEED
from openpilot.starpilot.common.tests.test_favorite_slots import FakeParams
from openpilot.starpilot.system.wheel_controls import wheel_controlsd as wheel


def test_favourites_and_bluetooth_have_identical_unique_options():
  options = favorites.build_favorite_slot_options(lambda _: True, alpha_longitudinal_available=True)
  source = Path(__file__).parents[2] / 'system/the_galaxy/the_galaxy.py'
  fn = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == '_get_available_controller_action_options')
  env = {'_get_available_favorite_slot_options': lambda: options}
  exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), 'exec'), env)
  assert env[fn.name]() == options
  keys = [o['key'] for o in options]
  assert len(keys) == len(set(keys))
  assert CONTROLLER_ACTION_KEYS <= set(keys)


@pytest.mark.parametrize('key', sorted(CONTROLLER_ACTION_KEYS))
def test_every_controller_action_works_through_native_favourite_dispatch(key, monkeypatch):
  params, memory, calls = FakeParams(), FakeParams(), []
  slot = {'key': key, 'label': 'Assigned', 'enabled': True, 'show_onroad': True}
  if key == CONTROLLER_ACTION_SET_SPEED: slot['value'] = 42
  params.put(favorites.FAVORITE_SLOTS_PARAM, [slot])
  monkeypatch.setattr(wheel, 'execute_controller_key', lambda k, p, m, **kw: calls.append((k, p, m, kw['value'])) or True)
  assert favorites.toggle_favorite_slot(0, params, memory)
  assert calls == [(key, params, memory, slot.get('value'))]
  assert params.get(favorites.FAVORITE_SLOTS_PARAM) == [slot]
  slot['enabled'] = False
  assert not favorites.toggle_favorite_slot(0, params, memory)
  assert len(calls) == 1


@pytest.mark.parametrize('onroad,engaged,value,success', [(False,False,30,False),(True,False,30,False),(True,True,30,True),(True,True,500,False),(True,True,float('nan'),False)])
def test_favourite_set_speed_keeps_controller_bounds_and_engagement_guard(onroad,engaged,value,success):
  from openpilot.starpilot.system.wheel_controls.tests.test_wheel_controlsd import FakeParams as WheelParams
  params, memory = WheelParams({'IsOnroad':onroad,'IsEngaged':engaged,'IsMetric':False}), WheelParams()
  assert favorites.trigger_favorite_action(CONTROLLER_ACTION_SET_SPEED,memory,params=params,value=value) is success
  assert bool(memory.values) is success
