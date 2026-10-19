"""The Pair phone window and its permission checks."""
import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from openpilot.starpilot.galaxy_bluetooth import phone_ui
from openpilot.starpilot.galaxy_bluetooth.bridge import claim, pairing


class Galaxy:
  """A fake Galaxy: records calls and answers from a script."""
  def __init__(self, opened=200, status=None):
    self.calls = []
    self.opened = opened
    self.status = status if status is not None else {'adapterName': 'comma', 'pairing': None}

  def __call__(self, method, path, payload=None):
    self.calls.append((method, path, payload))
    if method == 'POST' and payload == {'operation': 'accept_pair'}:
      return self.opened, {'adapterName': 'comma'}
    if method == 'GET':
      return 200, self.status
    return 200, {}


class Clock:
  now = 100.
  def __call__(self):
    return self.now


class PhoneWindowTest(unittest.TestCase):
  def window(self, galaxy, claimed=''):
    self.clock = Clock()
    return phone_ui.PhoneWindow(galaxy, claim_status=lambda: {'claimed': claimed} if claimed else {}, clock=self.clock)

  def test_it_opens_the_window_through_galaxy(self):
    galaxy = Galaxy()
    window = self.window(galaxy)
    self.assertEqual(window.open(), 'waiting')
    self.assertEqual(galaxy.calls, [('POST', phone_ui.ACTION, {'operation': 'accept_pair'})])
    self.assertEqual(window.view()['adapter'], 'comma')

  def test_busy_and_unavailable_are_reported_not_hidden(self):
    self.assertEqual(self.window(Galaxy(opened=409)).open(), 'busy')
    self.assertEqual(self.window(Galaxy(opened=503)).open(), 'unavailable')

    def broken(*args):
      raise OSError
    self.assertEqual(self.window(broken).open(), 'unavailable')

  def test_app_and_music_both_finish_the_window(self):
    galaxy = Galaxy()
    window = self.window(galaxy, claimed='Pixel 8')
    window.open()
    self.assertEqual(window.poll(), 'waiting')
    self.assertEqual((window.view()['app'], window.view()['music']), ('Pixel 8', ''))
    galaxy.status = {'adapterName': 'comma', 'pairing': {'incoming': True, 'state': 'paired', 'name': 'Pixel 8'}}
    self.assertEqual(window.poll(), 'done')
    self.assertEqual(window.view()['music'], 'Pixel 8')

  def test_a_pairing_that_is_not_ours_does_not_count_as_music(self):
    galaxy = Galaxy(status={'pairing': {'incoming': False, 'state': 'paired', 'name': 'Speaker'}})
    window = self.window(galaxy)
    window.open()
    window.poll()
    self.assertEqual(window.view()['music'], '')

  def test_the_code_is_shown_only_when_the_phone_must_tap(self):
    galaxy = Galaxy(status={'pairing': {'incoming': True, 'state': 'pairing', 'prompt': {'kind': 'confirmation', 'value': '123456', 'displayOnly': True}}})
    window = self.window(galaxy)
    window.open()
    window.poll()
    self.assertEqual(window.view()['code'], '123456')
    galaxy.status = {'pairing': {'incoming': True, 'state': 'pairing', 'prompt': {'kind': 'confirmation', 'value': '123456', 'displayOnly': False}}}
    window.poll()
    self.assertEqual(window.view()['code'], '')

  def test_the_window_closes_when_time_runs_out_or_cancelled(self):
    galaxy = Galaxy()
    window = self.window(galaxy)
    window.open()
    self.clock.now += claim.WINDOW_SECONDS + 1
    self.assertEqual(window.poll(), 'closed')
    other = self.window(galaxy)
    other.open()
    other.cancel()
    self.assertEqual(other.state, 'closed')
    self.assertEqual(galaxy.calls[-1], ('POST', phone_ui.ACTION, {'operation': 'cancel_pair'}))
    count = len(galaxy.calls)
    other.cancel()
    self.assertEqual(len(galaxy.calls), count)

  def test_every_state_has_text_and_names_the_comma(self):
    for state in ('opening', 'waiting', 'done', 'closed', 'busy', 'unavailable'):
      lines = phone_ui.message_lines({'state': state, 'adapter': 'my comma', 'app': 'Pixel', 'music': '', 'code': '', 'left': 75})
      self.assertTrue(lines)
    waiting = phone_ui.message_lines({'state': 'waiting', 'adapter': 'my comma', 'app': '', 'music': '', 'code': '', 'left': 75})
    self.assertIn('No app? Tap my comma in your phone’s Bluetooth settings.', waiting)
    self.assertIn('1:15 left', waiting)
    self.assertTrue(any('Phone app link: Waiting' in line for line in
                        phone_ui.message_lines({'state': 'waiting', 'adapter': '', 'app': '', 'music': '', 'code': '', 'left': 5}, 'Waiting for Bluetooth')))


class GalaxyCallTest(unittest.TestCase):
  def test_the_call_wraps_json_the_way_the_bridge_does(self):
    seen = []

    class Proxy:
      def handle(self, request):
        seen.append(request)
        return {'status': 200, 'body': base64.b64encode(b'{"ok":true}').decode()}
    with patch('openpilot.starpilot.galaxy_bluetooth.bridge.proxy.GalaxyProxy', Proxy):
      call = phone_ui.galaxy_call()
    self.assertEqual(call('POST', '/x', {'a': 1}), (200, {'ok': True}))
    self.assertEqual(json.loads(base64.b64decode(seen[0]['body'])), {'a': 1})
    self.assertEqual(call('GET', '/x')[0], 200)
    self.assertNotIn('body', seen[1])

  def test_the_ui_imports_the_bridge_without_its_folder_on_the_path(self):
    # Other bridge tests put the bridge folder on sys.path; the comma UI does not, so check in a clean process.
    root = str(Path(__file__).resolve().parents[4])
    code = 'from openpilot.starpilot.galaxy_bluetooth.phone_ui import galaxy_call; galaxy_call()'
    result = subprocess.run([sys.executable, '-c', code], cwd=root, env={**os.environ, 'PYTHONPATH': root},
                            capture_output=True, text=True, timeout=60)
    self.assertEqual(result.returncode, 0, result.stderr)


class PermissionTest(unittest.TestCase):
  def test_permission_failure_is_closed(self):
    self.assertFalse(phone_ui.permitted(lambda: (_ for _ in ()).throw(OSError())))

  def test_denied_pairing_opens_nothing(self):
    with patch.object(phone_ui, 'PairPhone') as screen:
      phone_ui.open_pairing(lambda: False)
    screen.assert_not_called()

  def test_forgetting_checks_permission_at_confirmation_time(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'pairing.json'
      phone_id, _ = pairing.add_phone('Pixel', path)
      pairing.link_address(phone_id, '11:22:33:44:55:66', path)
      with patch.object(phone_ui, 'remove_by_address', side_effect=lambda address: pairing.remove_by_address(address, path)):
        phone_ui.forget_phone_keys(lambda: False, '11:22:33:44:55:66')
        self.assertEqual(len(pairing.load_keys(path)), 1)
        phone_ui.forget_phone_keys(lambda: True, '11:22:33:44:55:66')
        self.assertEqual(pairing.load_keys(path), {})

  def test_app_only_phones_are_forgotten_without_touching_linked_ones(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'pairing.json'
      linked, _ = pairing.add_phone('Pixel', path)
      pairing.link_address(linked, '11:22:33:44:55:66', path)
      pairing.add_phone('Old iPhone', path)
      with patch.object(phone_ui, 'app_only', side_effect=lambda: pairing.app_only(path)), \
           patch.object(phone_ui, 'remove_phone', side_effect=lambda phone_id: pairing.remove_phone(phone_id, path)):
        self.assertEqual(phone_ui.app_only_count(), 1)
        phone_ui.forget_app_only(lambda: False)
        self.assertEqual(len(pairing.load_keys(path)), 2)
        phone_ui.forget_app_only(lambda: True)
      self.assertEqual(list(pairing.load_keys(path)), [linked])


if __name__ == '__main__':
  unittest.main()
