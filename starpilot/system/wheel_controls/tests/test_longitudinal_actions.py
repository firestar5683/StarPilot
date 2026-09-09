"""Shared catalogues, legacy assignments, and actual HID dispatch; fake Params."""
import ast
from pathlib import Path

import pytest

from openpilot.starpilot.common import favorite_slots as favorites
from openpilot.starpilot.common import longitudinal_mode_actions as actions
from openpilot.starpilot.common.tests.test_favorite_slots import FakeParams
from openpilot.starpilot.system.wheel_controls import wheel_controlsd as wheel

ROOT = Path(__file__).resolve().parents[4]


def test_both_catalogues_have_five_modes_and_preserve_legacy_toggles():
  options = favorites.build_favorite_slot_options(lambda _: True, alpha_longitudinal_available=True)
  tree = ast.parse((ROOT/'starpilot/system/the_galaxy/the_galaxy.py').read_text())
  fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_get_available_controller_action_options')
  env = {'_get_available_favorite_slot_options': lambda: options, 'CONTROLLER_ACTION_OPTIONS': wheel.CONTROLLER_ACTION_OPTIONS}
  exec(compile(ast.Module(body=[fn], type_ignores=[]), '<catalogue>', 'exec'), env)
  section = favorites.get_catalog_param_map()['ConditionalExperimental']['section']
  for catalogue in (options, env[fn.name]()):
    keys = [o['key'] for o in catalogue]
    assert all(keys.count(k) == 1 for k in actions.ACTION_TARGETS)
    assert set(actions.LEGACY_MODE_ACTIONS) & set(favorites.get_catalog_param_map()) <= set(keys)
    assert all(o['section'] == section for o in catalogue if o['key'] in actions.ACTION_TARGETS)


@pytest.mark.parametrize('key', actions.ACTION_TARGETS)
def test_favourite_native_and_bluetooth_dispatch_once_without_param_writes(key, monkeypatch):
  params, memory, calls = FakeParams(), FakeParams(), []
  monkeypatch.setattr(favorites, 'request_mode_action', lambda k: calls.append(k) or True)
  slots = favorites.default_favorite_slots()
  slots[0] = {'key':key,'label':'test','enabled':True,'show_onroad':True}
  favorites.save_favorite_slots(slots, params)
  wheel.set_controller_action_slot(0, key, 'test', params, eligible_keys=set(actions.ACTION_TARGETS))
  before = params.store.copy()
  assert favorites.toggle_favorite_slot(0, params, memory)
  assert wheel.execute_mapping_slot(3, params, memory)
  assert calls == [key, key]
  assert params.store == before and memory.store == {}
  params.store[favorites.FAVORITE_SLOTS_PARAM][0]['enabled'] = False
  assert not favorites.toggle_favorite_slot(0, params, memory)
  assert calls == [key, key]


@pytest.mark.parametrize('legacy,target', actions.LEGACY_MODE_ACTIONS.items())
def test_old_assignments_keep_toggle_keys_and_storage(legacy, target, monkeypatch):
  params, memory, calls = FakeParams(), FakeParams(), []
  params.types[legacy] = favorites.ParamKeyType.BOOL
  raw = [{'key':legacy,'label':'old name','enabled':True,'show_onroad':False}]
  params.store[favorites.FAVORITE_SLOTS_PARAM] = raw
  params.store[wheel.CONTROLLER_ACTIONS_PARAM] = raw
  monkeypatch.setattr(favorites, 'request_mode_action', lambda k: calls.append(k) or True)
  assert favorites.load_favorite_slots(params, set(actions.ACTION_TARGETS) | set(actions.LEGACY_MODE_ACTIONS))[0]['key'] == legacy
  assert wheel.load_controller_action_slots(params, set(actions.ACTION_TARGETS) | set(actions.LEGACY_MODE_ACTIONS))[0]['key'] == legacy
  assert favorites.toggle_favorite_slot(0, params, memory)
  assert wheel.execute_mapping_slot(3, params, memory)
  assert favorites.execute_favorite_key(legacy, params, memory)
  assert calls == [legacy]*3
  assert params.store[favorites.FAVORITE_SLOTS_PARAM] == raw
  assert params.store[wheel.CONTROLLER_ACTIONS_PARAM] == raw
  assert memory.store == {}


def test_unrelated_disabled_and_unassigned_slots_preserved():
  params = FakeParams()
  slots = [{'enabled':False,'show_onroad':False,'key':'ForceOffroad','label':'Mine'},
           {'enabled':False,'show_onroad':False,'key':None,'label':''}]
  assert favorites.normalize_favorite_slots(slots, params)[:2] == slots


def test_press_not_release_or_autorepeat(monkeypatch):
  params, memory, calls = FakeParams(), FakeParams(), []
  key = actions.PREFIX+'cycle'
  wheel.set_controller_action_slot(0, key, 'cycle', params, eligible_keys={key})
  source = wheel.InputSource('/dev/input/event-test', 'test-id', 'test', 5, 1, 1)
  params.put_bool(wheel.ENABLED_PARAM, True)
  wheel.upsert_mapping(source, 304, 3, params)
  monkeypatch.setattr(favorites, 'request_mode_action', lambda k, **kw: calls.append(k) or True)
  daemon = wheel.WheelControlsDaemon(params, memory)
  daemon.sources[123] = source
  daemon.buffers[123] = bytearray()
  data = b''.join(wheel.INPUT_EVENT.pack(0, 0, wheel.EV_KEY, 304, value) for value in (1, 2, 0))
  monkeypatch.setattr(wheel.os, 'read', lambda *_: data)
  try:
    daemon._read_events(123)
  finally:
    daemon.selector.close()
  assert calls == [key]
