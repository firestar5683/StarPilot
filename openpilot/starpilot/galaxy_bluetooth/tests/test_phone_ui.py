"""Native phone pairing checks permission again at the action boundary."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from openpilot.starpilot.galaxy_bluetooth import phone_ui
from openpilot.starpilot.galaxy_bluetooth.bridge import pairing


class PhoneUITest(unittest.TestCase):
  def test_denied_pairing_does_not_create_or_display_a_key(self):
    with patch.object(phone_ui, 'add_phone') as key:
      phone_ui.open_pairing(lambda: False)
    key.assert_not_called()

  def test_permission_failure_is_closed(self):
    self.assertFalse(phone_ui.permitted(lambda: (_ for _ in ()).throw(OSError())))

  def test_forget_checks_permission_at_confirmation_time(self):
    with tempfile.TemporaryDirectory() as directory:
      key_path = Path(directory) / 'pairing.json'
      pairing.add_phone('iPhone', key_path)
      with patch.object(phone_ui, 'forget_all', side_effect=lambda: pairing.forget_all(key_path)) as forget:
        phone_ui.forget_phones(lambda: False)
        forget.assert_not_called()
        self.assertEqual(len(pairing.load_keys(key_path)), 1)
        phone_ui.forget_phones(lambda: True)
        self.assertEqual(pairing.load_keys(key_path), {})

  def test_forget_one_phone_keeps_the_others(self):
    with tempfile.TemporaryDirectory() as directory:
      key_path = Path(directory) / 'pairing.json'
      _, iphone = pairing.add_phone('iPhone', key_path)
      _, android = pairing.add_phone('Android phone', key_path)
      with patch.object(phone_ui, 'load_phones', side_effect=lambda: pairing.load_phones(key_path)), \
           patch.object(phone_ui, 'remove_phone', side_effect=lambda phone_id: pairing.remove_phone(phone_id, key_path)):
        rows = phone_ui.paired_phones()
        self.assertEqual(len({label for label, _, _ in rows}), 2)
        target = next(phone_id for _, phone_id, _ in rows if pairing.load_keys(key_path)[phone_id] == iphone)
        phone_ui.forget_phone(lambda: False, target)
        self.assertEqual(len(pairing.load_keys(key_path)), 2)
        phone_ui.forget_phone(lambda: True, target)
      self.assertEqual(list(pairing.load_keys(key_path).values()), [android])


if __name__ == '__main__':
  unittest.main()
