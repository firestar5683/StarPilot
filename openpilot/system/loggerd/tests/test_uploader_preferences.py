"""Run the uploader's actual main loop with inert transport and live preferences."""
import ast
from enum import IntEnum
from pathlib import Path
from types import SimpleNamespace as NS
import unittest


class Network(IntEnum):
  none = 0
  wifi = 1
  cell = 2

  @property
  def raw(self):
    return int(self)


class TestUploadPreferences(unittest.TestCase):
  def run_loop(self, observations, *, force_wifi=False):
    main = next(node for node in ast.parse(Path(__file__).parents[1].joinpath('uploader.py').read_text()).body
                if isinstance(node, ast.FunctionDef) and node.name == 'main')
    state = NS(index=-1, calls=[], reads=[], cleared=False)

    class Saved:
      def get(self, key):
        return 'test-local-id' if key == 'DongleId' else None

      def get_bool(self, key):
        state.reads.append(key)
        current = observations[max(0, state.index)]
        return current.get('allow', False) if key == 'AlwaysAllowUploads' else current.get('offroad', False)

    class Master:
      def update(self, _):
        state.index += 1

      def __getitem__(self, _):
        row = observations[state.index]
        return NS(networkType=row.get('network', Network.cell), networkMetered=row.get('metered', True))

    class InertUploader:
      def __init__(self, *_):
        pass

      def step(self, network, metered):
        state.calls.append((network, metered))
        return None

    namespace: dict = {'threading': NS(Event=object), 'Params': Saved, 'Uploader': InertUploader,
                 'Paths': NS(log_root=lambda: '/unused'), 'clear_locks': lambda _: None,
                 'set_core_affinity': lambda _: None, 'messaging': NS(SubMaster=lambda _: Master()),
                 'NetworkType': Network, 'force_wifi': force_wifi, 'allow_sleep': False,
                 'cloudlog': NS(info=lambda *_: None, exception=lambda *_: None),
                 'active_provider': lambda: NS(name='comma')}
    exec(compile(ast.Module(body=[main], type_ignores=[]), 'uploader.py', 'exec'), namespace)
    namespace['main'](NS(is_set=lambda: state.index + 1 >= len(observations)))
    return state

  def test_metered_default_off_and_live_on_off_refresh(self):
    state = self.run_loop([{}, {'allow': True}, {'allow': False}, {'allow': True, 'metered': False},
                           {'allow': False, 'metered': False}])
    self.assertEqual(state.calls, [(2, True), (2, False), (2, True), (2, False), (2, False)])
    self.assertEqual(state.reads.count('AlwaysAllowUploads'), 5)

  def test_no_network_and_offroad_policy_are_preserved(self):
    state = self.run_loop([{'allow': True, 'network': Network.none}, {'offroad': True},
                           {'offroad': True, 'allow': True}])
    self.assertEqual(state.calls, [(2, True), (2, False)])
    self.assertEqual(state.reads.count('IsOffroad'), 3)

  def test_force_wifi_preserves_actual_network_metadata_and_metering(self):
    state = self.run_loop([{'network': Network.none}, {'network': Network.cell, 'allow': True}], force_wifi=True)
    self.assertEqual(state.calls, [(0, True), (2, False)])

  def test_typed_persistent_default_is_off(self):
    keys = Path(__file__).parents[3].joinpath('common/params_keys.h').read_text()
    self.assertIn('{"AlwaysAllowUploads", {PERSISTENT, BOOL, "0"}}', keys)


if __name__ == '__main__':
  unittest.main()
