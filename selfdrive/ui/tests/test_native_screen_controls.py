"""Native UI behavior tests without loading device-only raylib/msgq libraries."""

import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest
from openpilot.selfdrive.ui.lib.screen_settings import try_screen_setting

ROOT = Path(__file__).resolve().parents[3]


def method(path, cls, name, **namespace):
  assert (ROOT / path).exists(), f'Missing native screen implementation {path}'
  tree = ast.parse((ROOT / path).read_text())
  class_node = next((node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == cls), None)
  assert class_node is not None, f'Missing native screen control {cls}'
  node = next((node for node in class_node.body if isinstance(node, ast.FunctionDef) and node.name == name), None)
  assert node is not None, f'Missing native screen behavior {cls}.{name}'
  module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), node], type_ignores=[])
  namespace.setdefault('try_screen_setting', try_screen_setting)
  namespace.setdefault('show_screen_save_error', lambda: pytest.fail('Unexpected native save error'))
  exec(compile(ast.fix_missing_locations(module), str(ROOT / path), 'exec'), namespace)
  return namespace[name]


SYSTEM = 'selfdrive/ui/layouts/settings/starpilot/system_settings.py'
MICi = 'selfdrive/ui/mici/layouts/settings/screen.py'


def real_params(directory):
  spec = importlib.util.spec_from_file_location('native_test_params', ROOT / 'common/params.py')
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module.Params(directory)


class TestNativeScreenControls:
  @pytest.fixture(autouse=True)
  def params_directory(self, tmp_path):
    self._params_directory = tmp_path

  def _real_params(self):
    return real_params(str(self._params_directory))

  def test_mici_toggle_refresh_uses_real_boolean_getter_signature(self):
    refresh = method(MICi, 'ScreenToggleMici', 'refresh')
    params = self._real_params()
    values = []
    control = SimpleNamespace(_params=params, _key='StandbyWakeBrake', _default=False, set_checked=values.append)
    refresh(control)
    params.put_bool('StandbyWakeBrake', True)
    refresh(control)
    assert values == [False, True]

  def test_mici_screen_controls_enabled_uses_real_boolean_getter(self):
    tree = ast.parse((ROOT / MICi).read_text())
    screen_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'ScreenSettingsLayoutMici')
    enabled_call = next(
      node for node in ast.walk(screen_class) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and (node.func.attr == 'set_enabled')
    )
    params = self._real_params()
    enabled = eval(compile(ast.Expression(enabled_call.args[0]), 'native-enable-callback', 'eval'), {'self': SimpleNamespace(_params=params)})
    assert enabled()
    params.put_bool('ScreenManagement', False)
    assert not enabled()

  def test_big_ui_wake_callbacks_use_real_boolean_getter_and_keep_choices_independent(self):
    tree = ast.parse((ROOT / SYSTEM).read_text())
    system_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'SystemSettingsManagerView')
    assignment = next(
      node
      for node in ast.walk(system_class)
      if isinstance(node, ast.Assign) and any(isinstance(target, ast.Attribute) and target.attr == '_wake_toggle_defs' for target in node.targets)
    )
    params = self._real_params()
    view = SimpleNamespace(_controller=SimpleNamespace(_params=params))
    namespace = {
      'self': view,
      'tr': lambda text: text,
      'SCREEN_WAKE_DESCRIPTIONS': {'StandbyWakeEngage': 'Wake when engaged.', 'StandbyWakeBrake': 'Wake when braking.'},
      'SCREEN_WAKE_OPTIONS': [('StandbyWakeEngage', 'Engagement', True), ('StandbyWakeBrake', 'Brake', False)],
    }
    exec(compile(ast.Module(body=[assignment], type_ignores=[]), 'native-wake-callbacks', 'exec'), namespace)
    assert [option['get_state']() for option in view._wake_toggle_defs] == [True, False]
    assert [option['subtitle'] for option in view._wake_toggle_defs] == ['Wake when engaged.', 'Wake when braking.']
    params.put_bool('StandbyWakeBrake', True)
    params.put_bool('StandbyWakeEngage', False)
    assert [option['get_state']() for option in view._wake_toggle_defs] == [False, True]

  def test_mici_screen_toggles_save_existing_and_new_settings(self):
    helper_spec = importlib.util.spec_from_file_location('screen_settings', ROOT / 'starpilot/common/screen_settings.py')
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    save = method(MICi, 'ScreenToggleMici', '_save', SCREEN_WAKE_KEYS=helper.SCREEN_WAKE_KEYS, write_screen_setting=helper.write_screen_setting)
    params = self._real_params()
    for key in ('ScreenManagement', 'StandbyMode', 'StandbyWakeBrake'):
      save(SimpleNamespace(_params=params, _key=key, refresh=lambda: None), True)
    assert [params.get_bool(key) for key in ('ScreenManagement', 'StandbyMode', 'StandbyWakeBrake')] == [True, True, True]

  def test_mici_value_save_remembers_brightness_and_accepts_existing_timeout(self):
    helper_spec = importlib.util.spec_from_file_location('screen_settings', ROOT / 'starpilot/common/screen_settings.py')
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    save = method(MICi, 'ScreenValueButton', '_save', SCREEN_INT_KEYS=helper.SCREEN_INT_KEYS, write_screen_setting=helper.write_screen_setting)
    params = self._real_params()
    params.put_int('ScreenBrightness', 101)
    view = SimpleNamespace(_params=params, refresh=lambda: None)
    save(view, 'ScreenBrightness', 38)
    save(view, 'ScreenTimeout', 25)
    assert [params.get_int(key) for key in ('ScreenBrightness', 'ScreenBrightnessManual', 'ScreenTimeout')] == [38, 38, 25]

  def test_big_ui_offroad_timeout_remains_visible_when_standby_is_off(self):
    get_keys = method(SYSTEM, 'SystemSettingsManagerView', '_display_keys')
    params = SimpleNamespace(get_bool=lambda key: False)
    view = SimpleNamespace(
      _controller=SimpleNamespace(_params=params), _display_slider_keys=['ScreenBrightness', 'ScreenBrightnessOnroad', 'ScreenTimeout', 'ScreenTimeoutOnroad']
    )
    assert get_keys(view) == ['ScreenBrightness', 'ScreenBrightnessOnroad', 'ScreenTimeout']
    params.get_bool = lambda key: True
    assert get_keys(view) == view._display_slider_keys

  def test_big_ui_standby_reveals_wake_choices_without_losing_other_toggles(self):
    get_defs = method(SYSTEM, 'SystemSettingsManagerView', '_visible_toggle_defs')
    params = SimpleNamespace(get_bool=lambda key: False)
    view = SimpleNamespace(
      _controller=SimpleNamespace(_params=params),
      _toggle_defs=[{'title': 'Standby'}, {'title': 'Uploads'}],
      _wake_toggle_defs=[{'title': 'Engagement'}, {'title': 'Brake'}],
    )
    assert get_defs(view) == [{'title': 'Standby'}, {'title': 'Uploads'}]
    params.get_bool = lambda key: True
    assert get_defs(view) == [{'title': 'Standby'}, {'title': 'Engagement'}, {'title': 'Brake'}, {'title': 'Uploads'}]

  def test_mici_brightness_slider_selects_offset_or_manual_with_correct_bounds(self):
    for mode, want in [('auto', ('ScreenBrightnessOnroadOffset', -30, 30, -25, '%')), ('manual', ('ScreenBrightnessOnroad', 0, 100, 73, '%'))]:
      get_spec = method(
        MICi, 'BrightnessLayoutMici', '_slider_spec', brightness_preferences=lambda params, key, mode=mode: {'mode': mode, 'manual': 73, 'offset': -25}
      )
      view = SimpleNamespace(_params=object(), _key='ScreenBrightnessOnroad')
      spec = get_spec(view)
      assert (spec['key'], spec['min'], spec['max'], spec['value'], spec['unit']) == want

  def test_big_ui_auto_summary_uses_signed_percent_without_affecting_manual(self):
    for mode, offset, want in [('auto', 25, 'Auto +25%'), ('auto', -25, 'Auto -25%'), ('manual', 0, 'Manual 73%')]:
      formatted_value = method(
        'selfdrive/ui/layouts/settings/starpilot/screen_controls.py',
        'BrightnessAdjustorRow',
        'formatted_value',
        brightness_preferences=lambda params, key, mode=mode, offset=offset: {'mode': mode, 'manual': 73, 'offset': offset},
        tr=lambda text: text,
      )
      assert formatted_value(SimpleNamespace(_params=object(), _brightness_key='ScreenBrightness')) == want

  def test_mici_value_card_signs_offset_only_when_both_modes_use_percent(self):
    refresh = method(MICi, 'ScreenValueButton', 'refresh')
    for minimum, value, want in [(-30, 25, '+25%'), (-30, -25, '-25%'), (-30, 0, '+0%'), (0, 73, '73%')]:
      values = []
      spec = {'min': minimum, 'value': value, 'unit': '%'}
      button = SimpleNamespace(_get_spec=lambda spec=spec: spec, text='brightness', set_text=lambda text: None, set_value=values.append)
      refresh(button)
      assert values == [want]

  def test_big_ui_manual_selection_uses_new_default_and_preserves_remembered_value(self):
    helper_spec = importlib.util.spec_from_file_location('screen_settings', ROOT / 'starpilot/common/screen_settings.py')
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    choose_mode = method(
      'selfdrive/ui/layouts/settings/starpilot/screen_controls.py', 'AetherBrightnessDialog', '_set_mode', set_brightness_mode=helper.set_brightness_mode
    )
    params = self._real_params()
    view = SimpleNamespace(_params=params, _key='ScreenBrightnessOnroad')
    choose_mode(view, 1)
    assert params.get_int('ScreenBrightnessOnroad') == 100
    params.put_int('ScreenBrightnessOnroad', 41)
    choose_mode(view, 0)
    choose_mode(view, 1)
    assert params.get_int('ScreenBrightnessOnroad') == 41

  def test_mici_standby_controls_visibility_without_changing_saved_values(self):
    refresh = method(MICi, 'ScreenSettingsLayoutMici', '_refresh')

    class Control:
      visible = None

      def refresh(self):
        pass

      def set_visible(self, value):
        self.visible = value

    params = SimpleNamespace(get_bool=lambda key: False)
    timeout = Control()
    triggers = [Control(), Control()]
    view = SimpleNamespace(_params=params, _refresh_controls=[], _onroad_timeout=timeout, _wake_controls=triggers)
    refresh(view)
    assert not timeout.visible
    assert all(control.visible is False for control in triggers)
    params.get_bool = lambda key: True
    refresh(view)
    assert timeout.visible
    assert all(control.visible is True for control in triggers)

  def test_mici_numeric_slider_clamps_and_snaps_to_allowed_steps(self):
    value_from_x = method(MICi, 'ScreenSliderMici', '_value_from_x')
    slider = SimpleNamespace(_track=SimpleNamespace(x=50, width=400), _minimum=-30, _maximum=30, _step=1)
    assert [value_from_x(slider, x) for x in (0, 50, 150, 250, 449, 500)] == [-30, -30, -15, 0, 30, 30]
    slider._minimum, slider._maximum, slider._step = (5, 60, 5)
    assert [value_from_x(slider, x) for x in (0, 122, 250, 500)] == [5, 15, 35, 60]
