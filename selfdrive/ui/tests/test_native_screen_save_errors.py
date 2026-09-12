"""Exercise registered native save callbacks when the shared writer rejects a save."""

import os
from contextlib import nullcontext
from types import SimpleNamespace
import pytest
from unittest.mock import patch  # noqa: TID251 - standard-library mocking inside pytest tests

os.environ.setdefault('SP_HEADLESS_TEST', '1')
from openpilot.common.params import Params, UnknownKeyName
from openpilot.selfdrive.ui.layouts.settings.starpilot import screen_controls as big
from openpilot.selfdrive.ui.mici.layouts.settings import screen as mici


class Range:
  def __init__(self, *args, **kwargs):
    self.current_val = args[3] if len(args) > 3 else 0
    self.commit = kwargs.get('on_commit')
    self.is_interacting = False

  def set_visible(self, value):
    pass

  def set_value(self, value):
    self.current_val = value

  def reset_interaction(self):
    self.is_interacting = False


class TestNativeScreenSaveErrors:
  @pytest.fixture(autouse=True)
  def setup(self, tmp_path):
    self.params = Params(str(tmp_path))
    self.params.put_int('ScreenBrightness', 101)
    self.params.put_int('ScreenBrightnessManual', 37)
    self.params.put_int('ScreenBrightnessOffset', -12)
    self.params.put_bool('StandbyWakeBrake', False)
    self.errors = []
    with (
      patch.object(big, 'show_screen_save_error', lambda: self.errors.append('save failed')),
      patch.object(mici, 'show_screen_save_error', lambda: self.errors.append('save failed')),
    ):
      yield

  def assert_recoverable(self, action):
    try:
      result = action()
    except (OSError, ValueError) as error:
      pytest.fail(f'Save error escaped the native callback: {error}')
    assert self.errors == ['save failed']
    return result

  def big_dialog(self):
    with patch.object(big, 'AetherInlineRangeControl', Range), patch.object(big, 'AetherSegmentedControl', Range):
      return big.AetherBrightnessDialog(self.params, 'ScreenBrightness', 'Offroad brightness')

  def test_c3_failed_mode_save_preserves_auto_and_manual_memory(self):
    dialog = self.big_dialog()
    with patch.object(big, 'set_brightness_mode', side_effect=OSError('Screen settings busy')):
      self.assert_recoverable(lambda: dialog._set_mode(1))
    assert dialog._mode_index() == 0
    assert self.params.get_int('ScreenBrightnessManual') == 37

  def test_c3_failed_auto_selection_preserves_manual_brightness(self):
    self.params.put_int('ScreenBrightness', 37)
    dialog = self.big_dialog()
    with patch.object(big, 'set_brightness_mode', side_effect=ValueError('Invalid setting')):
      self.assert_recoverable(lambda: dialog._set_mode(0))
    assert dialog._mode_index() == 1
    assert self.params.get_int('ScreenBrightness') == 37

  def test_c3_registered_slider_callbacks_restore_saved_values(self):
    for control_name, saved in (('_offset', -12), ('_manual', 37)):
      self.errors.clear()
      self.params.put_int('ScreenBrightness', 37 if control_name == '_manual' else 101)
      dialog = self.big_dialog()
      control = getattr(dialog, control_name)
      control.current_val = 25
      with patch.object(big, 'write_screen_setting', side_effect=OSError('disk full')):
        self.assert_recoverable(lambda control=control: control.commit(25))
      assert control.current_val == saved
      assert self.params.get_int('ScreenBrightnessManual') == 37
      assert self.params.get_int('ScreenBrightnessOffset') == -12

  def test_c3_registered_wake_toggle_recovers_from_failed_save(self):
    import ast
    from types import MethodType, SimpleNamespace
    from openpilot.selfdrive.ui.tests.test_native_screen_controls import ROOT, SYSTEM, method
    from openpilot.starpilot.common.screen_settings import SCREEN_WAKE_DESCRIPTIONS, SCREEN_WAKE_OPTIONS

    def fail_write(params, key, value):
      raise OSError("Screen settings busy")

    namespace = {"write_screen_setting": fail_write, "show_screen_save_error": lambda: self.errors.append("save failed")}
    save = method(SYSTEM, "SystemSettingsManagerView", "_save_wake_setting", **namespace)
    view = SimpleNamespace(_controller=SimpleNamespace(_params=self.params))
    view._save_wake_setting = MethodType(save, view)
    tree = ast.parse((ROOT / SYSTEM).read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "SystemSettingsManagerView")
    definition = next(
      node.value
      for node in ast.walk(cls)
      if isinstance(node, ast.Assign) and any(isinstance(target, ast.Attribute) and target.attr == "_wake_toggle_defs" for target in node.targets)
    )
    definitions = eval(
      compile(ast.Expression(definition), "wake-controls", "eval"),
      dict(namespace, self=view, tr=lambda value: value, SCREEN_WAKE_OPTIONS=SCREEN_WAKE_OPTIONS, SCREEN_WAKE_DESCRIPTIONS=SCREEN_WAKE_DESCRIPTIONS),
    )
    brake = next(control for control in definitions if "Brake pedal" in control["title"])
    self.assert_recoverable(lambda: brake["set_state"](True))
    assert brake["get_state"]() is False
    assert self.params.get_bool("StandbyWakeBrake") is False

  @pytest.mark.parametrize("error_type", [OSError, ValueError, UnknownKeyName])
  def test_c4_failed_wake_toggle_restores_checked_state(self, error_type):
    control = mici.ScreenToggleMici.__new__(mici.ScreenToggleMici)
    control._params, control._key, control._default = (self.params, 'StandbyWakeBrake', False)
    control._checked = True
    with patch.object(mici, 'write_screen_setting', side_effect=error_type('Screen settings busy')):
      self.assert_recoverable(lambda: control._save(True))
    assert not control._checked
    assert not self.params.get_bool('StandbyWakeBrake')

  @pytest.mark.parametrize('key,minimum,saved', [('ScreenBrightnessOffset', -30, -12), ('ScreenBrightness', 0, 37)])
  def test_c4_slider_failure_restores_visible_value_and_keeps_slider_open(self, key, minimum, saved):
    self.params.put_int('ScreenBrightness', 37 if key == 'ScreenBrightness' else 101)
    button = mici.ScreenValueButton.__new__(mici.ScreenValueButton)
    button._params = self.params
    button.refresh = lambda: None
    slider = mici.ScreenSliderMici("brightness", minimum, 30 if minimum < 0 else 100, 1, saved, "%", lambda value: button._save(key, value))
    slider._value, slider._dragging = 25, True
    with patch.object(mici, 'write_screen_setting', side_effect=OSError('Screen settings busy')):
      self.assert_recoverable(lambda: slider._handle_mouse_release(None))
    assert slider._value == saved
    assert not slider.is_dismissing
    assert self.params.get_int(key) == saved

  @pytest.mark.parametrize('initial,selected,saved_mode', [(101, 'Manual', 'Auto'), (37, 'Auto', 'Manual')])
  @pytest.mark.parametrize('fail_save', [True, False])
  def test_c4_mode_confirmation_dismisses_only_after_successful_save(self, initial, selected, saved_mode, fail_save):
    self.params.put_int('ScreenBrightness', initial)
    layout = mici.BrightnessLayoutMici.__new__(mici.BrightnessLayoutMici)
    layout._params, layout._key = (self.params, 'ScreenBrightness')
    shown_modes = []
    layout._mode = SimpleNamespace(set_value=shown_modes.append)
    layout._value = SimpleNamespace(refresh=lambda: None)
    layout._explanation = SimpleNamespace(set_value=lambda value: None)
    dialogs = []
    base = getattr(mici, 'ScreenModeDialogMici', mici.BigMultiOptionDialog)

    class Dialog:
      def __init__(self, options, default, right_btn_callback, **kwargs):
        self._right_btn_callback = right_btn_callback
        self._selected_option = selected
        self._default_option = default
        self._current_option = kwargs.get('current_option', lambda: default)
        self.dismissed = False

      def get_selected_option(self):
        return self._selected_option

      def dismiss(self, callback=None):
        self.dismissed = True
        if callback:
          callback()

      def _on_option_selected(self, option):
        self._selected_option = option

    with (
      patch.object(mici, 'BigMultiOptionDialog', Dialog),
      patch.object(mici, 'ScreenModeDialogMici', Dialog, create=True),
      patch.object(mici.gui_app, 'push_widget', dialogs.append),
    ):
      layout._show_mode_selector()
    dialog = dialogs[0]
    with patch.object(mici, 'set_brightness_mode', side_effect=OSError('Screen settings busy')) if fail_save else nullcontext():
      if fail_save:
        self.assert_recoverable(lambda: base._confirm_selection(dialog))
      else:
        base._confirm_selection(dialog)
        assert self.errors == []
    assert dialog.dismissed is not fail_save
    assert dialog.get_selected_option() == (saved_mode if fail_save else selected)
    assert shown_modes[-1] == (saved_mode if fail_save else selected)
    assert self.params.get_int('ScreenBrightness') == (initial if fail_save else 37 if selected == 'Manual' else 101)
    assert self.params.get_int('ScreenBrightnessManual') == 37

  @pytest.mark.parametrize("interface", ["c3", "c4"])
  def test_native_controls_recover_when_another_save_holds_the_lock(self, interface):
    from openpilot.starpilot.common.screen_settings import _screen_write_transaction

    if interface == "c3":
      control = self.big_dialog()

      def action():
        return control._set_mode(1)
    else:
      control = mici.ScreenToggleMici.__new__(mici.ScreenToggleMici)
      control._params, control._key, control._default = self.params, "StandbyWakeBrake", False
      control._checked = True

      def action():
        return control._save(True)

    with _screen_write_transaction(self.params):
      self.assert_recoverable(action)
    assert self.params.get_int("ScreenBrightness") == 101
    assert self.params.get_int("ScreenBrightnessManual") == 37
    assert self.params.get_bool("StandbyWakeBrake") is False
    if interface == "c3":
      assert control._mode_index() == 0
    else:
      assert control._checked is False

  @pytest.mark.parametrize("key,initial,external", [("ScreenBrightnessOffset", -12, 19), ("ScreenBrightness", 37, 73)])
  def test_c4_rejected_save_reads_latest_persisted_slider_value_before_retry(self, key, initial, external):
    if key == "ScreenBrightness":
      mici.write_screen_setting(self.params, key, initial)
    button = mici.ScreenValueButton.__new__(mici.ScreenValueButton)
    button._params = self.params
    button.refresh = lambda: None
    button._get_spec = lambda: {
      "key": key,
      "title": "brightness",
      "value": initial,
      "min": -30 if key.endswith("Offset") else 0,
      "max": 30 if key.endswith("Offset") else 100,
      "unit": "%",
    }
    dialogs = []
    with patch.object(mici.gui_app, "push_widget", dialogs.append):
      button._show_slider()
    slider = dialogs[0]
    # A second client changes this value while the native slider is open.
    mici.write_screen_setting(self.params, key, external)
    if key == "ScreenBrightness":
      mici.set_brightness_mode(self.params, key, "auto")
    slider._value, slider._dragging = 25, True
    with patch.object(mici, "write_screen_setting", side_effect=OSError("Screen settings busy")):
      self.assert_recoverable(lambda: slider._handle_mouse_release(None))
    assert slider._value == external
    assert slider._committed_value == external
    assert not slider.is_dismissing
    slider._value, slider._dragging = external + 1, True
    slider._handle_mouse_release(None)
    assert self.params.get_int(key) == external + 1
    assert slider._committed_value == external + 1
