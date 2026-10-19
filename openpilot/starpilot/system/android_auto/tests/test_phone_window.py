"""A phone pairing window opened inside Android Auto's projection lease."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from openpilot.starpilot.bluetooth.owner import BluetoothRejected, OpenPairingSession
from openpilot.starpilot.bluetooth.radio_preference import RadioPreference
from openpilot.starpilot.bluetooth.tests.test_accept_pair import A2DP_SOURCE, SENDER, FakeWindowBlueZ
from openpilot.starpilot.system.android_auto.bluetooth_bridge import SharedBluetoothOwner

SESSION = ('galaxy', 'source-a')
CAR = '02:00:00:00:00:01'


class PhoneWindowTest(unittest.TestCase):
  def setUp(self):
    temp = tempfile.TemporaryDirectory()
    self.addCleanup(temp.cleanup)
    root = Path(temp.name)
    (root / 'bluetooth-radio').write_bytes(b'helper')
    FakeWindowBlueZ.instances = []
    FakeWindowBlueZ.adapter = ('/org/bluez/hci0', {}, SENDER)
    FakeWindowBlueZ.bonded = threading.Event()
    self.state = {'parked': True, 'valid': True}
    self.owner = SharedBluetoothOwner(lambda: self.state['parked'], session_valid=lambda s: s == SESSION and self.state['valid'],
                                      bluez_factory=FakeWindowBlueZ, lock_path=root / 'owner.lock', radio_helper=root / 'bluetooth-radio',
                                      systemctl=lambda *a, **k: SimpleNamespace(stdout='active\n'),
                                      radio_preference=RadioPreference(root / 'BluetoothEnabled'))
    self.owner.journal_path.write_text('{"lease": "original visibility"}')
    self.lease = SimpleNamespace(released=False, session=None, discovering=False, close_agent=None, phone=Mock(),
                                 adapter_path='/org/bluez/hci0', bluez_sender=SENDER, was_pairable=True, was_discoverable=False,
                                 process_lock=Mock(), receiver=CAR)
    self.owner.phone_lease = self.lease

  def claimed(self):
    for _ in range(300):
      result = self.owner.phone_window('status', SESSION)
      if result and result['pairing'] and result['pairing']['prompt']:
        return result['pairing']
      time.sleep(0.01)
    self.fail('phone never claimed the window')

  def test_window_pairs_a_phone_without_touching_the_lease_or_its_journal(self):
    started = self.owner.phone_window('accept_pair', SESSION)
    self.assertTrue(started['pairing']['incoming'])
    prompt = self.claimed()
    self.assertEqual(prompt['address'], '11:22:33:44:55:66')
    self.assertTrue(prompt['prompt']['displayOnly'], 'the code is shown, not waited on')
    FakeWindowBlueZ.bonded.set()
    self.assertTrue(self.owner.pairing.done.wait(2))
    final = self.owner.phone_window('status', SESSION)
    self.assertEqual(final['pairing']['state'], 'paired')
    self.assertEqual(final['windowPaired'], {'address': '11:22:33:44:55:66', 'name': 'Pixel', 'uuids': [A2DP_SOURCE]})
    self.assertIs(self.owner.phone_lease, self.lease)
    self.assertFalse(self.lease.released)
    self.assertEqual(self.owner.journal_path.read_text(), '{"lease": "original visibility"}')

  def test_no_projection_means_not_handled(self):
    self.owner.phone_lease = None
    for operation in ('accept_pair', 'status', 'cancel_pair'):
      self.assertIsNone(self.owner.phone_window(operation, SESSION))

  def test_refused_while_unparked_mid_pairing_or_with_an_expired_session(self):
    self.state['parked'] = False
    with self.assertRaises(BluetoothRejected) as error:
      self.owner.phone_window('accept_pair', SESSION)
    self.assertEqual(error.exception.code, 'park_required')
    self.state['parked'] = True
    self.lease.session = ('aa', 'car-pairing')
    with self.assertRaises(BluetoothRejected) as error:
      self.owner.phone_window('accept_pair', SESSION)
    self.assertEqual(error.exception.code, 'busy')
    self.lease.session = None
    self.state['valid'] = False
    with self.assertRaises(BluetoothRejected):
      self.owner.phone_window('accept_pair', SESSION)
    self.assertIsNone(self.owner.pairing)

  def test_other_sessions_cannot_answer_or_read_the_window(self):
    self.owner.phone_window('accept_pair', SESSION)
    prompt = self.claimed()
    other = ('galaxy', 'source-b')
    self.owner.session_valid = lambda s: s in (SESSION, other)
    self.assertIsNone(self.owner.phone_window('status', other))
    self.assertIsNone(self.owner.phone_window('pairing_response', other, prompt_id=prompt['prompt']['id'], accepted=True))
    self.owner.phone_window('cancel_pair', SESSION)
    self.assertTrue(self.owner.pairing.done.wait(2))
    self.assertNotEqual(self.owner.pairing.state, 'paired')

  def test_ending_projection_closes_the_window_before_the_lease_restores_visibility(self):
    self.owner.phone_window('accept_pair', SESSION)
    self.claimed()
    window = self.owner.pairing
    self.assertIsInstance(window, OpenPairingSession)
    self.owner.release_phone_role(self.lease)
    self.assertTrue(window.done.is_set())
    self.assertEqual(FakeWindowBlueZ.instances[-1].visibility[-1], ('/org/bluez/hci0', True, False))
    self.assertFalse(self.owner.journal_path.exists())


if __name__ == '__main__':
  unittest.main()
