"""Actual EV9 candidate and startup owner at the publication boundary."""
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.can_definitions import CanData
from opendbc.car.hyundai.ecu_startup import Outcome
from opendbc.car.hyundai.ev9_longitudinal import candidate, qualified
from opendbc.car.hyundai.ev9_startup import EV9Startup
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.ioniq6_handoff import TimestampedCanPacket
from opendbc.car.hyundai.tests.test_ioniq5pe_stock import params
from opendbc.car.hyundai.values import CAR, DBC


class TestEV9Startup(unittest.TestCase):
  def setUp(self):
    sleeper = patch("opendbc.car.hyundai.ev9_startup.time.sleep")
    sleeper.start()
    self.addCleanup(sleeper.stop)

  def owner(self, mode='sent'):
    stock = params(candidate=CAR.KIA_EV9)
    long = candidate(stock, enabled=True, is_release=False)
    sent, requests = [], []
    class Keeper:
      abort_reason = None
      stopped = False
      def __init__(self, send, **kwargs):
        self.send = send
      def start(self):
        pass
      def stop(self):
        self.stopped = True
    owner = EV9Startup(long, (lambda **kwargs: [], sent.extend), stock_cp=stock, keeper_factory=Keeper)
    def query(send, recv, bus, addresses, requests_arg, responses):
      request = requests_arg[0]
      expected = {b'\x10\x03': b'\x50\x03', b'\x28\x01\x01': b'', b'\x28\x00\x01': b'\x68\x00'}
      self.assertEqual((bus, addresses, responses), (1, [(0x730, None)], [expected[request]]))
      requests.append(request)
      def data(timeout):
        send([CanData(0x730, bytes((len(request),)) + request + bytes(7 - len(request)), 1)])
        if request == b'\x10\x03':
          return {} if mode == 'untouched' else {(0x730, None): b''}
        if request == b'\x28\x01\x01':
          if mode in ('restored', 'uncertain'):
            raise OSError('after actual command emission')
          return {}  # Original helper treats absence as sent, not confirmed.
        return {(0x730, None): b''} if mode == 'restored' else {}
      return SimpleNamespace(get_data=data)
    return stock, owner, sent, requests, query

  @patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
  def test_source_selected_request_silence_is_sent_unconfirmed(self):
    stock, owner, sent, requests, query = self.owner()
    with patch.object(owner, '_ready', return_value=False), patch.object(owner, '_query', side_effect=query):
      cp = owner.prepare(admission=lambda: True)
    self.assertIs(owner.outcome, Outcome.SENT_UNCONFIRMED)
    self.assertTrue(qualified(cp))
    self.assertEqual(requests, [b'\x10\x03', b'\x28\x01\x01'])
    self.assertTrue(owner.disable_attempted)
    self.assertEqual(stock.safetyConfigs[0].safetyParam, 0x5c91)
    self.assertAlmostEqual(cp.longitudinalActuatorDelay, 0.3)

  @patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
  def test_session_failure_no_disable_emission_returns_exact_stock(self):
    stock, owner, sent, requests, query = self.owner('untouched')
    with patch.object(owner, '_ready', return_value=False), patch.object(owner, '_query', side_effect=query):
      cp = owner.prepare(admission=lambda: True)
    self.assertIs(owner.outcome, Outcome.STOCK_UNTOUCHED)
    self.assertFalse(owner.disable_attempted)
    self.assertEqual(cp.to_dict(), stock.to_dict())

  @patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
  def test_original_ready_bit_skips_diagnostic_mutation(self):
    stock, owner, sent, requests, query = self.owner()
    owner.callbacks = (lambda **kwargs: [[CanData(0x35, b'\0\0\0\x40' + bytes(28), 1)]], sent.extend)
    with patch.object(owner, '_query', side_effect=AssertionError('READY must not query')):
      cp = owner.prepare(admission=lambda: True)
    self.assertEqual(cp.to_dict(), stock.to_dict())
    self.assertIs(owner.outcome, Outcome.STOCK_UNTOUCHED)
    self.assertEqual(sent, [])

  @patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
  def test_attempted_failure_requires_verified_restore(self):
    for mode in ('restored', 'uncertain'):
      stock, owner, sent, requests, query = self.owner(mode)
      with patch.object(owner, '_ready', return_value=False), patch.object(owner, '_query', side_effect=query):
        if mode == 'uncertain':
          with self.assertRaises(RuntimeError):
            owner.prepare(admission=lambda: True)
          self.assertIs(owner.outcome, Outcome.ABORT_UNCERTAIN)
        else:
          cp = owner.prepare(admission=lambda: True)
          self.assertEqual(cp.to_dict(), stock.to_dict())
          self.assertIs(owner.outcome, Outcome.STOCK_RESTORED)
      self.assertTrue(owner.disable_attempted)
      self.assertIn(b'\x28\x00\x01', requests)

  @patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
  def test_publication_seal_rejects_changed_cp(self):
    stock, owner, sent, requests, query = self.owner()
    with patch.object(owner, '_ready', return_value=False), patch.object(owner, '_query', side_effect=query):
      cp = owner.prepare(admission=lambda: True)
    ci = CarInterface(cp)
    owner.configure(ci)
    ci.CP.safetyConfigs[0].safetyParam = 0x5c91
    with self.assertRaises(RuntimeError):
      owner.seal_publication()

  @patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
  def test_restored_stock_requires_real_parser_warmup(self):
    stock, owner, sent, requests, query = self.owner('restored')
    with patch.object(owner, '_ready', return_value=False), patch.object(owner, '_query', side_effect=query):
      cp = owner.prepare(admission=lambda: True)
    ci = CarInterface(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    def recv(**kwargs):
      frames = []
      for parser in ci.can_parsers.values():
        for address in parser.addresses:
          message = parser.dbc.addr_to_msg[address]
          frames.append(CanData(*packer.make_can_msg(message.name, parser.bus, {})))
      return [TimestampedCanPacket(frames, time.clock_gettime_ns(time.CLOCK_BOOTTIME))]
    owner.callbacks = (recv, sent.extend)
    owner.configure(ci)
    owner.seal_publication()
    self.assertTrue(owner.ready)
    self.assertTrue(owner.published)
    self.assertEqual(ci.CP.to_dict(), stock.to_dict())

  @patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
  def test_keeper_handoff_requires_configured_current_sources_and_control(self):
    stock, owner, sent, requests, query = self.owner()
    with patch.object(owner, '_ready', return_value=False), patch.object(owner, '_query', side_effect=query):
      owner.prepare(admission=lambda: True)
    for values in ((False, True, True), (True, False, True), (True, True, False)):
      self.assertFalse(owner.before_control(configured=values[0], sources_current=values[1], control_current=values[2]))
      self.assertFalse(owner.keeper.stopped)
    self.assertTrue(owner.before_control(configured=True, sources_current=True, control_current=True))
    self.assertTrue(owner.keeper.stopped)
    self.assertTrue(owner.handed_off)

  @patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
  def test_keeper_abort_restores_on_main_thread_and_blocks_control(self):
    stock, owner, sent, requests, query = self.owner()
    with patch.object(owner, '_ready', return_value=False), patch.object(owner, '_query', side_effect=query):
      owner.prepare(admission=lambda: True)
    owner.keeper.abort_reason = 'software deadline'
    with patch.object(owner, '_restore', return_value=True) as restore:
      with self.assertRaises(RuntimeError):
        owner.before_control(configured=True, sources_current=True, control_current=True)
    restore.assert_called_once()
    self.assertTrue(owner.keeper.stopped)
    self.assertIs(owner.outcome, Outcome.ABORT_UNCERTAIN)

  @patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
  def test_factory_and_required_constructor_boundary_use_prepared_cp(self):
    from openpilot.starpilot.vehicle_startup import VehicleStartupOwner
    stock, owner, sent, requests, query = self.owner()
    self.assertIsNone(CarInterface.startup_owner(stock, owner.callbacks, requested=False))
    self.assertTrue(CarInterface.startup_required(owner.cp))
    with self.assertRaises(RuntimeError):
      VehicleStartupOwner().configure(CarInterface(owner.cp))
    holder = VehicleStartupOwner()
    with patch.object(CarInterface, 'startup_owner', return_value=owner), \
         patch.object(owner, '_ready', return_value=False), patch.object(owner, '_query', side_effect=query):
      prepared = holder.prepare(stock, CarInterface, owner.callbacks, requested=True, admission=lambda: True)
    ci = CarInterface(prepared)
    holder.configure(ci)
    holder.seal_publication()
    self.assertEqual(ci.CP.to_dict(), prepared.to_dict())
    self.assertEqual(ci.CP.safetyConfigs[0].safetyParam, 0x5c95)

  @patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
  def test_actual_factory_promotes_only_exact_stock_cp(self):
    stock = params(candidate=CAR.KIA_EV9)
    actual = CarInterface.startup_owner(stock, (lambda **kwargs: [], lambda frames: None), requested=True)
    self.assertIsInstance(actual, EV9Startup)
    self.assertTrue(qualified(actual.cp))
    self.assertEqual(actual.stock_cp.to_dict(), stock.to_dict())
    self.assertFalse(candidate(stock, enabled=False, is_release=False).openpilotLongitudinalControl)
    self.assertFalse(candidate(stock, enabled=True, is_release=True).openpilotLongitudinalControl)
    sibling = params(candidate=CAR.HYUNDAI_IONIQ_5_PE)
    self.assertIsNone(CarInterface.startup_owner(sibling, actual.callbacks, requested=True))

  def test_ready_poll_is_nonblocking_and_exact_source_bound(self):
    stock, owner, sent, requests, query = self.owner()
    now, polls = [0.0], []
    owner.clock = lambda: now[0]
    def recv(wait_for_one=False):
      self.assertFalse(wait_for_one)
      polls.append(now[0])
      now[0] += .1
      return []
    owner.callbacks = (recv, sent.extend)
    with patch('opendbc.car.hyundai.ev9_startup.time.sleep'):
      self.assertFalse(owner._ready())
    self.assertEqual(len(polls), 5)

  def test_unsuppressed_reply_classification(self):
    for payload, expected in ((b'\x68\x01', True), (b'\x7f\x28\x22', False),
                              (b'', False), (b'\x68\x03', False), (b'garbage', False)):
      stock, owner, sent, requests, query = self.owner()
      calls = [0]
      def replies(*args, **kwargs):
        calls[0] += 1
        if calls[0] == 1:
          return SimpleNamespace(get_data=lambda timeout: {(0x730, None): b''})
        return SimpleNamespace(get_data=lambda timeout: {(0x730, None): payload})
      with patch.object(owner, '_query', side_effect=replies), patch('opendbc.car.hyundai.ev9_startup.time.sleep'):
        self.assertEqual(owner._disable(owner.callbacks[0], owner.callbacks[1]), expected)

  @patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
  def test_actual_get_car_finalizes_long_before_interface_construction(self):
    from opendbc.car import car_helpers, gen_empty_fingerprint
    from openpilot.starpilot.vehicle_startup import VehicleStartupOwner
    stock, owner, sent, requests, query = self.owner()
    fingerprint = gen_empty_fingerprint()
    fingerprint[1].update({0x35: 32, 0x175: 24, 0xA0: 24, 0xEA: 24, 0x1CF: 8, 0x1A0: 32, 0x130: 16})
    fingerprint[2].update({0x110: 32, 0x362: 32})
    found = (CAR.KIA_EV9, fingerprint, '0' * 17, [], stock.fingerprintSource, True)
    holder = VehicleStartupOwner()
    def hook(cp, candidate_id, fingerprints, firmware):
      return holder.prepare(cp, CarInterface, owner.callbacks, requested=True, admission=lambda: True)
    with patch.object(car_helpers, 'fingerprint', return_value=found), \
         patch.object(EV9Startup, '_ready', return_value=False), patch.object(EV9Startup, '_query', side_effect=query):
      # Inject a non-thread keeper at the actual factory boundary.
      original_factory = CarInterface.startup_owner
      def factory(cp, callbacks, *, requested):
        selected = original_factory(cp, callbacks, requested=requested)
        selected.keeper_factory = owner.keeper_factory
        return selected
      with patch.object(CarInterface, 'startup_owner', side_effect=factory):
        ci = car_helpers.get_car(owner.callbacks[0], owner.callbacks[1], lambda *args: None,
                                 True, False, pre_create_hook=hook)
    holder.configure(ci)
    holder.seal_publication()
    self.assertTrue(qualified(ci.CP))
    self.assertEqual(ci.CP.safetyConfigs[0].safetyParam, 0x5c95)
    self.assertIs(holder.owner.outcome, Outcome.SENT_UNCONFIRMED)

  def test_malformed_long_cp_cannot_bypass_required_startup_owner(self):
    from openpilot.starpilot.vehicle_startup import VehicleStartupOwner
    for field, value in (("brand", "other"), ("pcmCruise", True), ("alternativeExperience", 32)):
      stock, owner, sent, requests, query = self.owner()
      setattr(owner.cp, field, value)
      self.assertFalse(qualified(owner.cp))
      self.assertTrue(CarInterface.startup_required(owner.cp))
      with self.assertRaises(RuntimeError):
        VehicleStartupOwner().configure(CarInterface(owner.cp))
    for word in (0x5c91, 0x5495, 0x5c97):
      stock, owner, sent, requests, query = self.owner()
      owner.cp.safetyConfigs[0].safetyParam = word
      self.assertFalse(qualified(owner.cp))
      self.assertTrue(CarInterface.startup_required(owner.cp))
      with self.assertRaises(RuntimeError):
        VehicleStartupOwner().configure(CarInterface(owner.cp))
    stock, owner, sent, requests, query = self.owner()
    owner.cp.flags = 0
    self.assertFalse(qualified(owner.cp))
    self.assertTrue(CarInterface.startup_required(owner.cp))
    # Malformed topology already fails while building the actual parser.
    with self.assertRaises(KeyError) as constructor_error:
      CarInterface(owner.cp)
    self.assertEqual(constructor_error.exception.args, ("LVR12",))
    # Exercise the actual class's owner boundary separately from parser setup.
    ci = object.__new__(CarInterface)
    ci.CP = owner.cp
    with self.assertRaises(RuntimeError):
      VehicleStartupOwner().configure(ci)
