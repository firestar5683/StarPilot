import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class TiciPairingTests(unittest.TestCase):
  def setUp(self):
    self.gui = SimpleNamespace(push_widget=Mock(), pop_widget=Mock())
    self.ui = SimpleNamespace(started=False, is_offroad=lambda: not self.ui.started)
    self.keys = SimpleNamespace(ensure_key=Mock(return_value=b'key'), load_key=Mock(return_value=b'key'),
                                rotate_key=Mock(), qr_payload=Mock())
    class Widget:
      def _update_state(self): pass
      def hide_event(self): pass
    def dialog(*args, **kwargs):
      return SimpleNamespace(args=args, **kwargs)
    attrs = {
      'openpilot.tools.galaxy_bluetooth.bootstrap': {'setup_status': lambda: 'Ready to pair', 'retry_setup': Mock()},
      'numpy': {}, 'pyray': {'unload_texture': Mock()}, 'qrcode': {},
      'openpilot.selfdrive.ui.ui_state': {'ui_state': self.ui},
      'openpilot.system.ui.lib.application': {'gui_app': self.gui, 'FontWeight': SimpleNamespace(MEDIUM=1)},
      'openpilot.system.ui.lib.text_measure': {'measure_text_cached': Mock()},
      'openpilot.system.ui.widgets': {'Widget': Widget, 'DialogResult': SimpleNamespace(CONFIRM=1, CANCEL=0)},
      'openpilot.system.ui.widgets.confirm_dialog': {'ConfirmDialog': dialog, 'alert_dialog': dialog},
      'openpilot.system.ui.widgets.list_view': {'button_item': dialog},
      'openpilot.system.ui.widgets.option_dialog': {'MultiOptionDialog': dialog},
      'openpilot.tools.galaxy_bluetooth.bridge.pairing': vars(self.keys),
    }
    modules = {}
    for name, values in attrs.items():
      modules[name] = ModuleType(name)
      modules[name].__dict__.update(values)
    spec = importlib.util.spec_from_file_location('tici_pairing_test', Path(__file__).resolve().parents[1] / 'comma_pairing_tici.py')
    self.module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
      spec.loader.exec_module(self.module)
    self.dialog_class = self.module.PhoneQRDialog
    self.module.PhoneQRDialog = Mock(return_value='qr')

  def options(self):
    item = self.module.pair_phone_item()
    self.assertTrue(item.enabled())
    item.callback()
    return self.gui.push_widget.call_args.args[0]

  def test_pair_uses_this_devices_key(self):
    options = self.options()
    options.selection = 'Pair phone'
    options.callback(1)
    self.keys.ensure_key.assert_called_once_with()
    self.module.PhoneQRDialog.assert_called_once_with(b'key')

  def test_forget_requires_confirmation_and_offroad(self):
    options = self.options()
    options.selection = 'Forget paired phones'
    options.callback(1)
    confirm = self.gui.push_widget.call_args.args[0]
    confirm.callback(0)
    self.keys.rotate_key.assert_not_called()
    self.ui.started = True
    confirm.callback(1)
    self.keys.rotate_key.assert_not_called()
    self.ui.started = False
    confirm.callback(1)
    self.keys.rotate_key.assert_called_once_with()

  def test_starting_drive_during_selection_blocks_pair(self):
    options = self.options()
    options.selection = 'Pair phone'
    self.ui.started = True
    options.callback(1)
    self.keys.ensure_key.assert_not_called()
    self.module.pair_phone_item().callback()
    self.keys.rotate_key.assert_not_called()

  def test_cancel_does_not_read_key(self):
    options = self.options()
    options.callback(0)
    self.keys.ensure_key.assert_not_called()

  def test_qr_closes_on_expiry_rotation_or_drive_and_releases_texture(self):
    for reason in ('expiry', 'rotation', 'drive'):
      with self.subTest(reason=reason):
        view = self.dialog_class.__new__(self.dialog_class)
        view._key = b'key'
        view._expires = float('inf') if reason != 'expiry' else 0
        view._texture = SimpleNamespace(id=1)
        self.ui.started = reason == 'drive'
        self.keys.load_key.return_value = b'new' if reason == 'rotation' else b'key'
        self.gui.pop_widget.reset_mock()
        view._update_state()
        self.gui.pop_widget.assert_called_once_with()
        view.hide_event()
        self.assertIsNone(view._texture)
        self.assertIsNone(view._key)
