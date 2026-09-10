"""Real catalogue/HID dispatcher with isolated Params and serialized CarParams.

Card/reader seams are source-extracted to avoid requiring native messaging builds.
"""
import ast
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from cereal import car, log

from openpilot.starpilot.common import favorite_slots as favorites
from openpilot.starpilot.common.longitudinal_personality_profiles import active_personality_id
from openpilot.starpilot.common.tests.test_favorite_slots import FakeParams
from openpilot.starpilot.system.wheel_controls import wheel_controlsd as wheel

ROOT = Path(__file__).resolve().parents[4]
ACTION = wheel.CONTROLLER_ACTION_CYCLE_PERSONALITY


class DiskSelectionParams(FakeParams):
  def __init__(self, root):
    super().__init__()
    self.root = root
    self.writes = []
    self.store.update(IsOnroad=True, IsOffroad=False)
    self.set_cp()
    self.set_selection(b"0")

  def set_cp(self, longitudinal=True, alpha=False):
    cp = car.CarParams.new_message(openpilotLongitudinalControl=longitudinal, alphaLongitudinalAvailable=alpha)
    cp_bytes = cp.to_bytes()
    self.store.update(CarParams=cp_bytes, CarParamsPersistent=cp_bytes)

  def get_param_path(self, key):
    return str(self.root / key)

  def set_selection(self, token):
    (self.root / "LongitudinalPersonality").write_bytes(token)

  def get(self, key, **kwargs):
    if key == "LongitudinalPersonality":
      return int((self.root / key).read_bytes())
    return self.store.get(key, kwargs.get("default"))

  def put_int(self, key, value):
    self.writes.append((key, value))
    if key == "LongitudinalPersonality":
      self.set_selection(str(value).encode())
    else:
      super().put_int(key, value)


@pytest.fixture
def params(tmp_path):
  params = DiskSelectionParams(tmp_path)
  wheel.set_controller_action_slot(0, ACTION, "Cycle Driving Personality", params, eligible_keys={ACTION})
  return params


def extracted(filename, name, namespace, class_name=None):
  tree = ast.parse((ROOT / filename).read_text())
  nodes = tree.body
  if class_name:
    nodes = next(n for n in nodes if isinstance(n, ast.ClassDef) and n.name == class_name).body
  node = next(n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == name)
  exec(compile(ast.Module(body=[node], type_ignores=[]), filename, "exec"), namespace)
  return namespace[name]


def test_unique_shared_catalogue_and_both_theme_status_consumers():
  options = favorites.build_favorite_slot_options(lambda _: True, alpha_longitudinal_available=True)
  assert ACTION in {o['key'] for o in options}
  assert favorites.is_favorite_action_key(ACTION)
  selected = [o for o in wheel.CONTROLLER_ACTION_OPTIONS if o['key'] == ACTION]
  assert len(selected) == 1
  assert selected[0]['label'] == 'Cycle Driving Personality'
  namespace = {'_get_available_favorite_slot_options': lambda: options, 'CONTROLLER_ACTION_OPTIONS': wheel.CONTROLLER_ACTION_OPTIONS}
  get_options = extracted('starpilot/system/the_galaxy/the_galaxy.py', '_get_available_controller_action_options', namespace)
  assert len([o for o in get_options() if o['key'] == ACTION]) == 1
  # Neither theme maintains a second action list: both use this status catalogue.
  for filename in ('assets/components/tools/wheel_controls.js', 'assets/mobile/js/components/WheelControls.js'):
    source = (ROOT / 'starpilot/system/the_galaxy' / filename).read_text()
    assert 'controller_options' in source
  assert 'LongitudinalPersonality' not in {o['key'] for o in options}


def test_existing_registry_and_persistence(params):
  registry = (ROOT / 'common/params_keys.h').read_text()
  assert registry.count('{"LongitudinalPersonality",') == 1
  assert ACTION not in registry
  controller = wheel.set_controller_action_slot(0, ACTION, 'Cycle Driving Personality', params, eligible_keys={ACTION})
  assert wheel.load_controller_action_slots(params, {ACTION}) == controller
  assert wheel.execute_controller_action(0, params, FakeParams())
  assert params.writes == [('LongitudinalPersonality', 1)]


def test_exact_enum_cycle_and_no_cruise_side_effect(params):
  assert log.LongitudinalPersonality.schema.enumerants == {'aggressive': 0, 'standard': 1, 'relaxed': 2}
  memory = FakeParams()
  wheel.set_controller_action_slot(0, ACTION, 'Cycle Driving Personality', params, eligible_keys={ACTION})
  for expected in (1, 2, 0, 1):
    assert wheel.execute_mapping_slot(favorites.FAVORITE_SLOT_COUNT, params, memory)
    assert params.get('LongitudinalPersonality') == expected
  assert params.writes == [('LongitudinalPersonality', n) for n in (1, 2, 0, 1)]
  assert memory.store == {}  # no speed, distance-gesture, Traffic or toggle counters


@pytest.mark.parametrize('token', [b'', b'bad', b'-1', b'3', b'1.0', b'1.5', b'NaN', b'Infinity', b'true', b' 1', b'01', b'\xff'])
def test_malformed_selection_is_not_coerced(params, token):
  params.set_selection(token)
  assert not wheel.execute_controller_action(0, params, FakeParams())
  assert params.writes == []
  assert Path(params.get_param_path('LongitudinalPersonality')).read_bytes() == token


def test_missing_selection_is_noop(params):
  Path(params.get_param_path('LongitudinalPersonality')).unlink()
  assert not wheel.execute_controller_action(0, params, FakeParams())
  assert params.writes == []


@pytest.mark.parametrize('onroad', [False, True])
@pytest.mark.parametrize('safe,longitudinal,alpha,enabled,allowed', [
  (False, True, False, False, True),
  (True, True, False, False, False),
  (False, False, False, True, False),
  (False, True, True, False, False),
  (False, False, True, True, True),
])
def test_native_capability_safe_mode_and_onroad_selection(params, onroad, safe, longitudinal, alpha, enabled, allowed):
  params.set_cp(longitudinal, alpha)
  params.store.update(SafeMode=safe, IsOnroad=onroad, IsOffroad=not onroad, AlphaLongitudinalEnabled=enabled)
  assert wheel.execute_controller_action(0, params, FakeParams()) is allowed
  assert params.writes == ([('LongitudinalPersonality', 1)] if allowed else [])


@pytest.mark.parametrize('cp', [None, b'bad'])
def test_no_stale_parked_capability_fallback_onroad(params, cp):
  params.store['CarParams'] = cp
  assert not wheel.execute_controller_action(0, params, FakeParams())
  assert params.writes == []


def test_disabled_assignment(params):
  wheel.set_controller_action_slot(0, ACTION, 'Cycle Driving Personality', params, eligible_keys={ACTION})
  # Controller slots disable by unassigning; enabled is derived from the key.
  wheel.set_controller_action_slot(0, None, '', params, eligible_keys={ACTION})
  assert not wheel.execute_controller_action(0, params, FakeParams())
  assert params.writes == []


def test_one_hid_press_one_change_release_and_autorepeat_ignored(params, monkeypatch):
  memory = FakeParams()
  wheel.set_controller_action_slot(0, ACTION, 'Cycle Driving Personality', params, eligible_keys={ACTION})
  source = wheel.InputSource('/dev/input/test', 'test-controller', 'Test', 3, 1, 2)
  wheel.upsert_mapping(source, 30, favorites.FAVORITE_SLOT_COUNT, params)
  daemon = wheel.WheelControlsDaemon(params, memory)
  daemon.sources[123] = source
  daemon.buffers[123] = bytearray()
  stream = b''.join(wheel.INPUT_EVENT.pack(0, 0, wheel.EV_KEY, 30, value) for value in (1, 2, 2, 0))
  monkeypatch.setattr(os, 'read', lambda *_: stream)
  daemon._read_events(123)
  assert params.writes == [('LongitudinalPersonality', 1)]
  assert memory.store == {}


def test_traffic_override_unchanged_and_native_reader_observes_selection(params):
  memory = FakeParams()
  counter = favorites.FAVORITE_ACTION_TRAFFIC_MODE_COUNTER
  memory.put_int(counter, 0)
  card = SimpleNamespace(params_memory=memory, _favorite_traffic_mode_counter=0, traffic_mode_enabled=True)
  consume = extracted('starpilot/controls/starpilot_card.py', '_handle_favorite_traffic_mode_action',
                      {'FAVORITE_ACTION_TRAFFIC_MODE_COUNTER': counter}, 'StarPilotCard')
  assert wheel.execute_controller_action(0, params, FakeParams())
  consume(card, {'carControl': SimpleNamespace(longActive=True)})
  assert card.traffic_mode_enabled is True
  assert active_personality_id(True, params.get('LongitudinalPersonality')) == 'traffic'
  assert active_personality_id(False, params.get('LongitudinalPersonality')) == 'standard'
  # Execute one iteration of the existing selfdrived reader, not an invented consumer.
  reader = extracted('selfdrive/selfdrived/selfdrived.py', 'params_thread', {
    'REPLAY': False, 'request_mode_refresh': lambda *_: None,
    'log': log, 'time': SimpleNamespace(sleep=lambda _: None),
  }, 'SelfdriveD')
  state = SimpleNamespace(params=params, params_memory=memory, starpilot_toggles=SimpleNamespace())
  checks = iter((False, True))
  reader(state, SimpleNamespace(is_set=lambda: next(checks)))
  assert state.personality == log.LongitudinalPersonality.standard
