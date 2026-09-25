"""Actual get_car/owner/CI publication path with explicit diagnostic transport replies."""
import ast
import inspect
import textwrap
import time
import unittest
from unittest.mock import patch

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car import car_helpers, disable_ecu as disable_module
from opendbc.car.can_definitions import CanData
from opendbc.car.hyundai import g90_startup
from opendbc.car.hyundai.g90_startup import Outcome
from opendbc.car.hyundai.ioniq6_handoff import TimestampedCanPacket
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.tests.test_g90_longitudinal import params
from opendbc.car.hyundai.values import CAR, DBC, HyundaiSafetyFlags
from openpilot.selfdrive.car.card import Car
from openpilot.starpilot.vehicle_startup import VehicleStartupOwner


class Replies:
  def __init__(self, mode):
    self.mode = mode
    self.requests = []

  def query(self, send, recv, bus, addresses, requests, responses, **kwargs):
    request = requests[0]
    expected = {b'\x10\x03': b'\x50\x03', b'\x28\x83\x01': b'', b'\x28\x00\x01': b'\x68\x00'}
    assert responses == [expected[request]], (request, responses)
    self.requests.append(request)
    owner = self
    class Query:
      def get_data(self, timeout):
        send([CanData(addresses[0][0], bytes((len(request),)) + request + bytes(7-len(request)), bus)])
        if request == b'\x10\x03':
          return {} if owner.mode == 'untouched' else {(0x7d0, None): b''}
        if request == b'\x28\x83\x01':
          if owner.mode != 'sent':
            raise OSError('Explicit simulated failure after communication request send')
          return {}
        if request == b'\x28\x00\x01':
          return {(0x7d0, None): b''} if owner.mode == 'restored' else {}
        raise AssertionError(request)
    return Query()


class TestG90Startup(unittest.TestCase):
  # Mac has no BOOTTIME constant. This fixture-only shim uses its monotonic
  # clock for both producer and consumer; Linux exercises native BOOTTIME.
  @patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
  def run_prepublication(self, mode, *, warm_mode=None, admission=lambda: True, requested=True):
    replies = Replies(mode)
    holder = VehicleStartupOwner()
    holder_ci = []
    original = params()
    sent = []
    packer = CANPacker(DBC[CAR.GENESIS_G90][Bus.pt])
    def recv(wait_for_one=False):
      if not holder_ci:
        return []
      ci = holder_ci[0]
      frames = []
      for parser in ci.can_parsers.values():
        for address in parser.addresses:
          message = parser.dbc.addr_to_msg[address]
          packet = CanData(*packer.make_can_msg(message.name, parser.bus, {}))
          if warm_mode == 'wrongbus' and message.name in ('SCC11', 'SCC12'):
            packet = CanData(packet.address, packet.dat, 1)
          frames.extend([packet] * (7 if warm_mode == 'counter' else 1))
      stamp = 1 if warm_mode == 'stale' else time.clock_gettime_ns(time.CLOCK_BOOTTIME)
      return [TimestampedCanPacket(frames, stamp)]
    def hook(cp, candidate, fingerprints, firmware):
      return holder.prepare(cp, CarInterface, (recv, sent.extend), requested=requested, admission=admission)
    fingerprint = (CAR.GENESIS_G90, gen_empty_fingerprint(), '0'*17, [], original.fingerprintSource, True)
    with patch.object(car_helpers, 'fingerprint', return_value=fingerprint), \
         patch.object(disable_module, 'IsoTpParallelQuery', side_effect=replies.query), \
         patch.object(g90_startup, 'IsoTpParallelQuery', side_effect=replies.query):
      ci = car_helpers.get_car(recv, sent.extend, lambda *args: None, True, False, pre_create_hook=hook)
      holder_ci.append(ci)
      if not requested:
        # Actual Card finalizes passive before holder.configure; no native output.
        ci.CP.passive = True
        ci.CP.safetyConfigs[0].safetyModel = structs.CarParams.SafetyModel.noOutput
        ci.CP.safetyConfigs[0].safetyParam = 0
      if warm_mode:
        with patch.object(g90_startup.time, 'monotonic', side_effect=[0., 0., 4.]):
          holder.configure(ci)
      else:
        holder.configure(ci)
      holder.seal_publication()
    return ci, holder, replies, original

  def test_actual_prepublication_sent_success_preserves_cp_and_protocol(self):
    ci, holder, replies, original = self.run_prepublication('sent')
    self.assertIs(holder.owner.outcome, Outcome.SENT_UNCONFIRMED)
    self.assertTrue(ci.CP.openpilotLongitudinalControl)
    self.assertFalse(ci.CP.pcmCruise)
    self.assertIn(b'\x28\x83\x01', replies.requests)
    self.assertNotIn(b'\x28\x03\x01', replies.requests)
    self.assertEqual(ci.CP.safetyConfigs[0].safetyParam, original.safetyConfigs[0].safetyParam)

  def test_actual_failed_prepublication_restores_then_publishes_stock(self):
    for mode, outcome in (('untouched', Outcome.STOCK_UNTOUCHED), ('restored', Outcome.STOCK_RESTORED)):
      ci, holder, replies, original = self.run_prepublication(mode)
      self.assertIs(holder.owner.outcome, outcome)
      self.assertFalse(ci.CP.openpilotLongitudinalControl)
      self.assertTrue(ci.CP.pcmCruise)
      self.assertFalse(ci.CP.safetyConfigs[0].safetyParam & HyundaiSafetyFlags.LONG.value)
      self.assertTrue(original.openpilotLongitudinalControl)  # Caller clone not mutated.
      self.assertTrue(holder.owner.ready)
      self.assertEqual(b'\x28\x00\x01' in replies.requests, mode == 'restored')

  def test_ambiguous_failure_aborts_before_constructor_and_explicit_ci_requires_owner(self):
    with self.assertRaisesRegex(RuntimeError, 'restoration unverified'):
      self.run_prepublication('uncertain')
    ci = CarInterface(params())
    with self.assertRaisesRegex(RuntimeError, 'matching prepared'):
      VehicleStartupOwner().configure(ci)
    holder = VehicleStartupOwner()
    stock = params(alpha=False)
    holder.configure(CarInterface(stock))  # Ordinary stock and all siblings need no owner.

  def test_stale_wrongbus_and_counter_loss_cannot_publish_stock(self):
    for warm_mode in ('stale', 'wrongbus', 'counter'):
      with self.subTest(warm_mode=warm_mode), self.assertRaisesRegex(RuntimeError, 'stock SCC'):
        self.run_prepublication('restored', warm_mode=warm_mode)

  def test_revoked_diagnostic_admission_cannot_restore_partial_failure(self):
    admitted = iter((True, False))
    with self.assertRaisesRegex(RuntimeError, 'restoration unverified'):
      self.run_prepublication('restored', admission=lambda: next(admitted))

  def test_explicit_prepared_owner_matches_exact_cp(self):
    ci, holder, replies, original = self.run_prepublication('sent')
    VehicleStartupOwner(holder.owner).configure(ci)
    other = params()
    other.safetyConfigs[0].safetyParam ^= 1
    with self.assertRaisesRegex(RuntimeError, 'matching prepared'):
      VehicleStartupOwner(holder.owner).configure(CarInterface(other))

  def test_same_object_mutation_cannot_rebind_prepared_decision(self):
    for mutation in ('safety', 'ownership'):
      ci, holder, replies, original = self.run_prepublication('sent')
      self.assertIs(ci.CP, holder.owner.cp)
      if mutation == 'safety':
        ci.CP.safetyConfigs[0].safetyParam ^= 1
      else:
        ci.CP.openpilotLongitudinalControl = False
        ci.CP.pcmCruise = True
      self.assertFalse(holder.owner.prepared_for(ci.CP))
      with self.assertRaisesRegex(RuntimeError, 'prepared'):
        holder.seal_publication()
      with self.assertRaisesRegex(RuntimeError, 'prepared'):
        holder.configure(ci)

  def test_distinct_equal_cp_mutation_cannot_pass_publication(self):
    for mutation in ('safety', 'ownership'):
      ci, holder, replies, original = self.run_prepublication('sent')
      with structs.CarParams.from_bytes(ci.CP.to_bytes()) as reader:
        equal_cp = reader.as_builder()
      distinct_ci = CarInterface(equal_cp)
      self.assertIsNot(distinct_ci.CP, holder.owner.cp)
      self.assertTrue(holder.owner.prepared_for(distinct_ci.CP))
      holder.configure(distinct_ci)
      if mutation == 'safety':
        distinct_ci.CP.safetyConfigs[0].safetyParam ^= 1
      else:
        distinct_ci.CP.openpilotLongitudinalControl = False
        distinct_ci.CP.pcmCruise = True
      self.assertTrue(holder.owner.prepared_for(holder.owner.cp))
      with self.assertRaisesRegex(RuntimeError, 'prepared'):
        holder.seal_publication()

  def test_disabled_request_passive_finalization_never_sends_diagnostics(self):
    ci, holder, replies, original = self.run_prepublication('sent', requested=False)
    self.assertIsNone(holder.owner)
    self.assertEqual(replies.requests, [])
    self.assertTrue(ci.CP.passive)
    self.assertEqual(ci.CP.safetyConfigs[0].safetyModel, structs.CarParams.SafetyModel.noOutput)
    self.assertEqual(ci.CP.safetyConfigs[0].safetyParam, 0)

  def test_actual_card_publication_order_and_generic_explicit_owner_api(self):
    source = inspect.getsource(Car.__init__)
    self.assertIn('startup_owner=None', source)
    self.assertLess(source.index('self.vehicle_startup.configure(self.CI)'), source.index('self.CP.to_bytes()'))
    self.assertLess(source.index('self.vehicle_startup.seal_publication()'), source.index('self.CP.to_bytes()'))
    tree = ast.parse(textwrap.dedent(source))
    self.assertFalse(any(isinstance(node, ast.Constant) and node.value == 'GENESIS_G90' for node in ast.walk(tree)))
