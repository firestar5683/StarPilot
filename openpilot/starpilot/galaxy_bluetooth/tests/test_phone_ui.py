"""Native phone pairing checks permission again at the action boundary."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from openpilot.starpilot.galaxy_bluetooth import phone_ui
from openpilot.starpilot.galaxy_bluetooth.bridge.pairing import ensure_key, load_key


class PhoneUITest(unittest.TestCase):
  def test_denied_pairing_does_not_create_or_display_a_key(self):
    with patch.object(phone_ui, 'ensure_key') as key:
      phone_ui.open_pairing(lambda: False)
    key.assert_not_called()

  def test_permission_failure_is_closed(self):
    self.assertFalse(phone_ui.permitted(lambda: (_ for _ in ()).throw(OSError())))

  def test_forget_checks_permission_at_confirmation_time(self):
    with tempfile.TemporaryDirectory() as directory:
      key_path = Path(directory) / 'pairing.json'
      original = ensure_key(key_path)
      from openpilot.starpilot.galaxy_bluetooth.bridge.pairing import rotate_key
      with patch.object(phone_ui, 'rotate_key', side_effect=lambda: rotate_key(key_path)) as rotate:
        phone_ui.forget_phones(lambda: False)
        rotate.assert_not_called()
        self.assertEqual(load_key(key_path), original)
        phone_ui.forget_phones(lambda: True)
        self.assertNotEqual(load_key(key_path), original)


if __name__ == '__main__': unittest.main()
