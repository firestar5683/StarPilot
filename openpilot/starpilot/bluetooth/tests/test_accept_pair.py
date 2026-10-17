import json
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from queue import Queue
from unittest.mock import patch

from jeepney import DBusAddress, new_method_call
from jeepney.low_level import HeaderFields, MessageType

from openpilot.starpilot.bluetooth.owner import (
  AGENT, AGENT_PATH, BlueZ, BluetoothOwner, BluetoothRejected, OpenPairingSession,
)
from openpilot.starpilot.bluetooth.radio_preference import RadioPreference

PHONE = '/org/bluez/hci0/dev_11_22_33_44_55_66'
SPEAKER = '/org/bluez/hci0/dev_AA_BB_CC_DD_EE_01'
A2DP_SOURCE = '0000110a-0000-1000-8000-00805f9b34fb'
SENDER = ':1.7'


def device(address, device_class, *, paired=False, uuids=()):
  return {'Address': address, 'Alias': 'Pixel' if device_class >> 8 & 0x1f == 2 else 'Speaker', 'Class': device_class,
          'Paired': paired, 'Blocked': False, 'UUIDs': list(uuids)}


class WindowHarness:
  def __init__(self, test, *, pairable=False, discoverable=False, seconds=120.0):
    self.responses, self.calls, self.visibility, self.journal, self.restored, self.classes = [], [], [], [], [], []
    self.incoming = Queue()
    self.now = time.monotonic
    harness = self

    class Router:
      @contextmanager
      def filter(self, *_args, **_kwargs):
        yield harness.incoming

      def send(self, message):
        harness.responses.append(message)

    self.objects = {
      '/org/bluez/hci0': {'org.bluez.Adapter1': {'Powered': True, 'Discovering': False, 'Pairable': pairable,
                                                  'Discoverable': discoverable, 'Address': 'AA:AA:AA:AA:AA:AA',
                                                  'Class': 0x4c0000}},
      PHONE: {'org.bluez.Device1': device('11:22:33:44:55:66', 0x5a020c)},
      SPEAKER: {'org.bluez.Device1': device('AA:BB:CC:DD:EE:01', 0x240414)},
    }
    self.bluez = BlueZ.__new__(BlueZ)
    test.enterContext(patch.object(self.bluez, 'router', Router(), create=True))
    test.enterContext(patch.object(self.bluez, '_bluez_sender', lambda: SENDER))
    test.enterContext(patch.object(self.bluez, '_objects', lambda: self.objects))
    test.enterContext(patch.object(self.bluez, 'set_pairing_visibility',
                                   lambda path, *, pairable, discoverable: self.visibility.append((pairable, discoverable))))
    test.enterContext(patch.object(self.bluez, '_call', self.call))
    test.enterContext(patch.object(self.bluez, 'set_class', lambda major, minor: self.classes.append((major, minor)) or True))
    self.session = OpenPairingSession(('session', b'generation'), lambda: True, self.now)
    self.session.deadline = self.now() + seconds

  def call(self, _path, _interface, member, *_args, **_kwargs):
    self.calls.append(member)
    return ()

  def agent(self, path, sender=SENDER):
    message = new_method_call(DBusAddress(AGENT_PATH, bus_name=':1.9', interface=AGENT),
                              'RequestConfirmation', 'ou', (path, 123456))
    message.header.fields[HeaderFields.sender] = sender
    self.incoming.put(message)

  def run(self):
    return self.bluez.accept_pair(self.session, lambda *args: self.journal.append(args), lambda: self.restored.append(True))


class AcceptPairWindowTest(unittest.TestCase):
  def answer_when_prompted(self, harness, accepted=True):
    def worker():
      for _ in range(400):
        prompt = harness.session.prompt
        if prompt is not None:
          harness.session.respond(harness.session.identity, prompt['id'], accepted, '')
          return
        time.sleep(0.01)
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread

  def test_first_phone_claims_window_and_visibility_returns_to_prior_values(self):
    harness = WindowHarness(self, pairable=True, discoverable=False)
    harness.agent(SPEAKER)
    harness.agent(PHONE)
    answerer = self.answer_when_prompted(harness)

    def finish_bond():
      for _ in range(400):
        if harness.session.path == PHONE and harness.session.prompt is None and harness.responses:
          time.sleep(0.05)
          harness.objects[PHONE]['org.bluez.Device1'].update(Paired=True, UUIDs=[A2DP_SOURCE])
          return
        time.sleep(0.01)
    threading.Thread(target=finish_bond, daemon=True).start()
    self.assertTrue(harness.run())
    answerer.join(2)
    self.assertEqual(harness.session.address, '11:22:33:44:55:66')
    self.assertIn(A2DP_SOURCE, harness.session.uuids)
    self.assertEqual(harness.visibility, [(True, True), (True, False)])
    self.assertEqual(harness.journal, [('/org/bluez/hci0', SENDER, True, False)])
    self.assertEqual(harness.restored, [True])
    self.assertEqual(harness.calls.count('RequestDefaultAgent'), 1)
    self.assertEqual(harness.calls[-1], 'UnregisterAgent')
    self.assertIn('Set', harness.calls)
    self.assertEqual(harness.responses[0].header.message_type, MessageType.error)
    self.assertEqual(harness.classes, [(4, 5), (0, 0)], 'shown as a speaker, then the original class returns')

  def test_devices_that_are_not_phones_cannot_claim_the_window(self):
    harness = WindowHarness(self, seconds=0.8)
    harness.agent(SPEAKER)
    self.assertFalse(harness.run())
    self.assertEqual(harness.session.path, '')
    self.assertEqual([item.header.message_type for item in harness.responses], [MessageType.error])
    self.assertEqual(harness.visibility[-1], (False, False))
    self.assertEqual(harness.restored, [True])

  def test_second_phone_is_rejected_after_the_first_claims(self):
    harness = WindowHarness(self, seconds=1.5)
    other = '/org/bluez/hci0/dev_66_55_44_33_22_11'
    harness.objects[other] = {'org.bluez.Device1': device('66:55:44:33:22:11', 0x5a020c)}
    harness.agent(PHONE)
    harness.agent(other)
    self.answer_when_prompted(harness, accepted=False)
    self.assertFalse(harness.run())
    self.assertEqual(harness.session.path, PHONE)
    self.assertEqual(len(harness.responses), 2)
    self.assertTrue(all(item.header.message_type == MessageType.error for item in harness.responses))

  def test_unpark_closes_the_window_and_restores_visibility(self):
    harness = WindowHarness(self, discoverable=True)
    parked = [True]
    harness.session.parked = lambda: parked[0]
    threading.Timer(0.4, lambda: parked.__setitem__(0, False)).start()
    self.assertFalse(harness.run())
    self.assertEqual(harness.visibility, [(True, True), (False, True)])
    self.assertEqual(harness.calls[-1], 'UnregisterAgent')

  def test_failed_restore_keeps_the_journal_for_the_next_owner(self):
    harness = WindowHarness(self, seconds=0.5)
    attempts = []

    def visibility(_path, *, pairable, discoverable):
      attempts.append((pairable, discoverable))
      if len(attempts) == 2:
        raise BluetoothRejected('Bluetooth Pairable change failed')
    self.enterContext(patch.object(harness.bluez, 'set_pairing_visibility', visibility))
    with self.assertRaises(BluetoothRejected):
      harness.run()
    self.assertEqual(harness.restored, [])
    self.assertEqual(len(harness.journal), 1)


class FakeWindowBlueZ:
  instances = []
  adapter = ('/org/bluez/hci0', {}, SENDER)

  def __init__(self):
    self.visibility = []
    type(self).instances.append(self)

  def adapter_identity(self):
    return type(self).adapter

  def set_pairing_visibility(self, path, *, pairable, discoverable):
    self.visibility.append((path, pairable, discoverable))

  def accept_pair(self, session, journal, restored):
    journal(*type(self).adapter[:1], SENDER, False, False)
    session.claim(PHONE, '11:22:33:44:55:66', 'Pixel')
    session.uuids = (A2DP_SOURCE,)
    accepted, _ = session.ask('confirmation', PHONE, '123456')
    restored()
    return accepted

  def snapshot(self):
    return {'adapter': True, 'powered': True, 'discovering': False, 'devices': []}

  def cancel_pair(self, _path):
    pass

  def _objects(self):
    return None

  def _devices(self, _objects):
    return []

  def operation(self, *_args):
    pass

  def close(self):
    pass


class AcceptPairOwnerTest(unittest.TestCase):
  identity = ('session-a', b'generation')

  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    root = Path(self.temp.name)
    (root / 'bluetooth-radio').write_bytes(b'helper')
    FakeWindowBlueZ.instances = []
    FakeWindowBlueZ.adapter = ('/org/bluez/hci0', {}, SENDER)
    self.paired = []
    self.owner = BluetoothOwner(lambda: True, bluez_factory=FakeWindowBlueZ, radio_helper=root / 'bluetooth-radio',
                                systemctl=lambda command, **_kwargs: type('Result', (), {'stdout': 'active\n'})(),
                                radio_preference=RadioPreference(root / 'BluetoothEnabled'),
                                admission_lock=root / 'owner.lock', on_paired=lambda *args: self.paired.append(args))

  def wait_for_prompt(self):
    for _ in range(300):
      prompt = self.owner.snapshot(session=self.identity)['pairing']
      if prompt and prompt['prompt']:
        return prompt
      time.sleep(0.01)
    self.fail('pairing prompt never appeared')

  def test_window_requires_a_session_and_no_address(self):
    with self.assertRaises(ValueError):
      self.owner.request('accept_pair')
    with self.assertRaises(ValueError):
      self.owner.request('accept_pair', address='11:22:33:44:55:66', session=self.identity)

  def test_open_window_blocks_other_pairing_and_reports_the_claimed_phone(self):
    started = self.owner.request('accept_pair', session=self.identity)
    self.assertTrue(started['pairing']['incoming'])
    prompt = self.wait_for_prompt()
    self.assertEqual(prompt['address'], '11:22:33:44:55:66')
    self.assertEqual(prompt['name'], 'Pixel')
    for operation in ('scan', 'accept_pair'):
      with self.assertRaises(BluetoothRejected) as raised:
        self.owner.request(operation, session=self.identity)
      self.assertEqual(raised.exception.code, 'busy')
    self.owner.request('pairing_response', session=self.identity, prompt_id=prompt['prompt']['id'], accepted=True)
    self.assertTrue(self.owner.pairing.done.wait(2))
    self.assertEqual(self.paired, [('11:22:33:44:55:66', 'Pixel', (A2DP_SOURCE,))])
    self.assertEqual(self.owner.snapshot(session=self.identity)['pairing']['state'], 'paired')

  def request_when_free(self, *args, **kwargs):
    # The closed window's watcher briefly holds the owner lock while it lets go of the adapter.
    for _ in range(100):
      try:
        return self.owner.request(*args, **kwargs)
      except BluetoothRejected as error:
        if str(error) != 'Bluetooth is busy':
          raise
        time.sleep(0.02)
    self.fail('owner stayed busy')

  def test_unclaimed_window_gives_way_to_forget_and_pair(self):
    for operation in ('forget', 'connect', 'disconnect', 'scan'):
      self.request_when_free('accept_pair', session=self.identity)
      self.wait_for_prompt()
      window = self.owner.pairing
      window.path = ''
      address = None if operation == 'scan' else '11:22:33:44:55:66'
      self.request_when_free(operation, address=address, session=self.identity)
      self.assertTrue(window.done.is_set(), operation)
      self.assertEqual(self.paired, [])
      self.request_when_free('stop_scan', session=self.identity)

  def test_declined_or_canceled_window_does_not_report_a_phone(self):
    self.owner.request('accept_pair', session=self.identity)
    self.wait_for_prompt()
    self.owner.request('cancel_pair', session=self.identity)
    self.assertTrue(self.owner.pairing.done.wait(2))
    self.assertEqual(self.paired, [])

  def test_crash_journal_restores_visibility_only_on_the_same_bluez(self):
    journal = self.owner.window_journal_path
    journal.write_text(json.dumps({'path': '/org/bluez/hci0', 'sender': SENDER, 'pairable': True, 'discoverable': False}))
    self.owner.request('accept_pair', session=self.identity)
    self.wait_for_prompt()
    self.assertEqual(FakeWindowBlueZ.instances[0].visibility, [('/org/bluez/hci0', True, False)])
    self.assertTrue(isinstance(self.owner.pairing, OpenPairingSession))
    self.owner.request('cancel_pair', session=self.identity)
    self.assertTrue(self.owner.pairing.done.wait(2))
    self.assertFalse(journal.exists())

  def test_stale_journal_from_another_bluez_instance_is_dropped_unapplied(self):
    journal = self.owner.window_journal_path
    journal.write_text(json.dumps({'path': '/org/bluez/hci0', 'sender': ':1.99', 'pairable': True, 'discoverable': True}))
    self.owner.request('accept_pair', session=self.identity)
    self.wait_for_prompt()
    self.assertEqual(FakeWindowBlueZ.instances[0].visibility, [])
    self.owner.request('cancel_pair', session=self.identity)
    self.assertTrue(self.owner.pairing.done.wait(2))
    self.assertFalse(journal.exists())


if __name__ == '__main__':
  unittest.main()
