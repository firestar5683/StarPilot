from typing import Any
import ast
from dataclasses import replace
from enum import StrEnum
from pathlib import Path
import sys
from types import ModuleType
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_source(name, dependencies=None, classes=None):
  path = ROOT / name
  tree = ast.parse(path.read_text())
  if classes:
    tree.body = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in classes]
  else:
    tree.body = [node for node in tree.body if not isinstance(node, ast.ImportFrom) or
                 not node.module.startswith('openpilot.')]
  module = ModuleType('isolated_' + path.stem)
  sys.modules[module.__name__] = module
  module.__dict__.update(dependencies or {})
  exec(compile(ast.fix_missing_locations(tree), str(path), 'exec'), module.__dict__)
  return module


profile = load_source('presentation.py', {'StrEnum': StrEnum}, {'Profile'})
access = load_source('../galaxy/access.py', {'StrEnum': StrEnum}, {'AccessStatus'})
device = load_source('device_state.py', vars(access))
software = load_source('software_state.py')
toggles = load_source('toggles_state.py')
features = load_source('feature_settings_state.py')
home = load_source('home_state.py', {'Profile': profile.Profile})
settings = load_source('settings_state.py', {**vars(device), **vars(software), **vars(toggles), **vars(home),
                                           'Profile': profile.Profile})


def snapshot_selection():
  tree = ast.parse((ROOT / 'runtime_snapshot.py').read_text())
  adapter = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'RuntimeSnapshotAdapter')
  build = next(node for node in adapter.body if isinstance(node, ast.FunctionDef) and node.name == 'build')
  selected_nodes = [node for node in build.body if
                    isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'settings_pages'
                                                        for target in node.targets) or
                    isinstance(node, ast.If) and any(isinstance(target, ast.Name) and target.id == 'selected'
                                                   for child in node.body if isinstance(child, ast.Assign)
                                                   for target in child.targets)]
  function = ast.parse('def normalize(mode, selected):\n return selected, settings_pages').body[0]
  function.body = selected_nodes + function.body
  namespace: dict[str, Any] = {'Destination': settings.Destination, 'ShellMode': SimpleNamespace(SETTINGS='settings')}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), 'snapshot_selection', 'exec'), namespace)
  return namespace['normalize']


normalize = snapshot_selection()


class TestLargeTouchDrift(unittest.TestCase):
  def test_registered_snapshot_selection_survives_three_transitions_then_close(self):
    selected = settings.Destination.STAR
    for point, destination in (((260, 477), settings.Destination.DEVICE),
                               ((256, 573), settings.Destination.NETWORK),
                               ((241, 683), settings.Destination.BLUETOOTH)):
      actions = []
      handler = settings.SettingsInput(profile.Profile.LARGE, actions.append, lambda selected=selected: selected)
      normalized, _ = normalize('settings', selected)
      self.assertEqual(normalized, selected)
      handler.press(*point, settings.SettingsState())
      handler.release(*point, settings.SettingsState())
      selected = actions[0].destination.destination
      self.assertEqual(selected, destination)
    self.assertEqual(normalize('settings', selected)[0], settings.Destination.BLUETOOTH)
    for expected in (settings.Destination.STAR, 'home'):
      actions = []
      handler = settings.SettingsInput(profile.Profile.LARGE, actions.append, lambda selected=selected: selected)
      self.assertEqual(normalize('settings', selected)[0], selected)
      handler.press(196, 188, settings.SettingsState())
      handler.release(216, 211, settings.SettingsState())
      self.assertEqual(actions[0].kind, settings.SettingsActionKind.CLOSE)
      selected = settings.Destination.STAR if selected != settings.Destination.STAR else 'home'
      self.assertEqual(selected, expected)

  def test_all_registered_snapshot_destinations_and_invalid_fallback(self):
    _, registered = normalize('settings', settings.Destination.STAR)
    for destination in (*registered, settings.Destination.NETWORK):
      self.assertEqual(normalize('settings', destination)[0], destination)
    self.assertEqual(normalize('settings', 'unknown')[0], settings.Destination.STAR)
    self.assertEqual(normalize('home', settings.Destination.BLUETOOTH)[0], settings.Destination.STAR)

  def test_observed_close_taps_accept_finger_drift(self):
    for start, end in (((196, 188), (216, 211)), ((310, 133), (329, 150))):
      actions = []
      handler = settings.SettingsInput(profile.Profile.LARGE, actions.append)
      state = settings.SettingsState()
      handler.press(*start, state)
      handler.move(*end, state)
      handler.release(*end, state)
      self.assertEqual([item.kind for item in actions], [settings.SettingsActionKind.CLOSE])

  def test_menu_target_drift_and_cross_target_refusal(self):
    state = settings.SettingsState()
    actions = []
    handler = settings.SettingsInput(profile.Profile.LARGE, actions.append)
    handler.press(196, 450, state)
    handler.move(216, 473, state)
    handler.release(216, 473, state)
    self.assertEqual(actions[0].destination.destination, settings.Destination.DEVICE)
    actions.clear()
    handler.press(196, 450, state)
    handler.move(216, 560, state)
    handler.release(196, 450, state)
    self.assertEqual(actions, [])

  def test_compact_scroll_gesture_still_cancels(self):
    actions = []
    handler = settings.SettingsInput(profile.Profile.COMPACT, actions.append)
    state = settings.SettingsState()
    handler.press(200, 100, state)
    handler.move(220, 123, state)
    handler.release(220, 123, state)
    self.assertEqual(actions, [])

  def test_large_device_software_and_toggle_static_controls_allow_drift(self):
    cases = ((device.DeviceInput, device.DeviceState(), (1980, 650)),
             (software.SoftwareInput, software.SoftwareState(), (1980, 475)),
             (toggles.TogglesInput, toggles.TogglesState(), (1950, 130)))
    for factory, state, start in cases:
      actions = []
      handler = factory(actions.append)
      end = start[0] + 20, start[1] + 23
      handler.press(*start, state)
      handler.move(*end, state)
      handler.release(*end, state)
      self.assertEqual(len(actions), 1)
      handler.release(*end, state)
      self.assertEqual(len(actions), 1)
      actions.clear()
      handler.press(*start, state)
      handler.move(100, 500, state)
      handler.release(*start, state)
      self.assertEqual(actions, [])

  def test_toggle_scrolling_cancels_even_if_same_target_is_under_finger(self):
    actions = []
    handler = toggles.TogglesInput(actions.append)
    state = toggles.TogglesState()
    handler.press(1950, 130, state)
    handler.release(1970, 153, replace(state, scroll_y=1))
    self.assertEqual(actions, [])

  def test_stale_toggle_value_and_device_authority_still_cancel(self):
    actions = []
    handler = toggles.TogglesInput(actions.append)
    state = toggles.TogglesState()
    handler.press(1950, 130, state)
    handler.release(1970, 153, replace(state, enabled=False))
    handler = device.DeviceInput(actions.append)
    state = device.DeviceState()
    handler.press(1980, 650, state)
    handler.release(2000, 673, replace(state, offroad=False))
    self.assertEqual(actions, [])

  def test_feature_static_control_drift_and_cross_target_refusal(self):
    actions = []
    handler = features.FeatureInput(actions.append)
    row = features.FeatureRow('sample', 'Sample', 'Off', b'0', available=True)
    state = features.FeatureSettingsState(rows=(row, row), parked=True)
    handler.press(1770, 310, state)
    handler.move(1790, 333, state)
    handler.release(1790, 333, state)
    self.assertEqual(len(actions), 1)
    actions.clear()
    handler.press(1910, 310, state)
    handler.move(1940, 333, state)
    handler.release(1910, 310, state)
    self.assertEqual(actions, [])

  def test_feature_scroll_page_and_source_changes_cancel(self):
    row = features.FeatureRow('sample', 'Sample', 'Off', b'0', available=True)
    state = features.FeatureSettingsState(rows=(row, row), parked=True)
    for changed in (replace(state, scroll=1), replace(state, page='new_page'),
                    replace(state, rows=(replace(row, source=b'1'), row))):
      actions = []
      handler = features.FeatureInput(actions.append)
      handler.press(1770, 310, state)
      handler.release(1790, 333, changed)
      self.assertEqual(actions, [])


if __name__ == '__main__':
  unittest.main()
