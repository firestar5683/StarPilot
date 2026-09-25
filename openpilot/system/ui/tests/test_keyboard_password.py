from unittest.mock import Mock, patch

from openpilot.system.ui.widgets.keyboard import Keyboard


def test_password_keyboard_masks_input_even_without_visibility_toggle():
  with patch("openpilot.system.ui.widgets.keyboard.gui_app.texture", return_value=Mock()), \
       patch("openpilot.system.ui.widgets.keyboard.gui_app.font", return_value=Mock()):
    keyboard = Keyboard(password_mode=True, show_password_toggle=False)
  keyboard.set_text("fixture123")
  assert keyboard.text == "fixture123"
  assert keyboard._input_box._get_display_text() == "•" * len(keyboard.text)


def test_plain_keyboard_keeps_visible_input():
  with patch("openpilot.system.ui.widgets.keyboard.gui_app.texture", return_value=Mock()), \
       patch("openpilot.system.ui.widgets.keyboard.gui_app.font", return_value=Mock()):
    keyboard = Keyboard(password_mode=False, show_password_toggle=False)
  keyboard.set_text("fixture123")
  assert keyboard._input_box._get_display_text() == "fixture123"
