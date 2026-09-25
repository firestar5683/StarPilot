"""Timestamped synthetic CAN/UDS through the actual prepublication caller."""
import time
import unittest
from unittest.mock import patch

from opendbc.can.packer import CANPacker
from opendbc.car import Bus, CanData, gen_empty_fingerprint, structs
from opendbc.car import car_helpers, disable_ecu as disable_module
from opendbc.car.hyundai import ecu_startup
from opendbc.car.hyundai.ecu_startup import Outcome, stock_copy
from opendbc.car.hyundai.ev6_startup import EV6Startup, eligible
from opendbc.car.hyundai.hyundaicanfd import hkg_can_fd_checksum
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.ioniq6_handoff import TimestampedCanPacket
from opendbc.car.hyundai.values import CAR, DBC
from openpilot.starpilot.vehicle_startup import VehicleStartupOwner


def params(alpha=True, radar=False, car=CAR.KIA_EV6):
  fp = gen_empty_fingerprint()
  fp[2][0x50] = 16
  fp[1][0x1cf] = 8
  if radar:
    if car == CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN:
      fp[0].update(dict.fromkeys(range(0x210, 0x220), 32))
    else:
      fp[1][0x500] = 8
  fw = [structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.adas)]
  return CarInterface.get_params(car, fp, fw, alpha, False, False)


class TestEV6Startup(unittest.TestCase):
  @patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
  def exercise(self, mode='sent', *, capture=True, admission=lambda: True, requested=True, wrong_bus=False,
               missing_source=None, fail_ctor=False, warm_fault=None, car=CAR.KIA_EV6):
    original = params(car=car)
    holder = VehicleStartupOwner()
    ci_ref = []
    requests = []
    self.last_requests = requests
    packer = CANPacker(DBC[car][Bus.pt])
    counter = 0
    def recv(wait_for_one=False):
      nonlocal counter
      counter += 1
      if not ci_ref:
        if not capture:
          return []
        data = bytearray(32)
        data[2], data[4] = counter % 256, 7
        data[:2] = hkg_can_fd_checksum(0x51, None, data).to_bytes(2, 'little')
        frames = [CanData(0x51, bytes(data), 1 if wrong_bus else 0)]
      else:
        frames = []
        for parser in ci_ref[0].can_parsers.values():
          for address in parser.addresses:
            name = parser.dbc.addr_to_msg[address].name
            if name != missing_source and name != 'CRUISE_BUTTONS_ALT':
              frame = CanData(*packer.make_can_msg(name, 0 if warm_fault == 'wrongbus' and name == 'SCC_CONTROL' else parser.bus, {}))
              frames.extend([frame] * (7 if warm_fault == 'counter' and name == 'SCC_CONTROL' else 1))
      stamp = 1 if ci_ref and warm_fault == 'stale' else time.clock_gettime_ns(time.CLOCK_BOOTTIME)
      return [TimestampedCanPacket(frames, stamp)]
    def query(send, can_recv, bus, addresses, commands, responses, **kwargs):
      command = commands[0]
      self.assertEqual(bus, 1)
      self.assertEqual(addresses, [(0x730, None)])
      self.assertEqual(responses, [{b'\x10\x03': b'\x50\x03', b'\x28\x83\x01': b'', b'\x28\x00\x01': b'\x68\x00'}[command]])
      requests.append(command)
      class Query:
        def get_data(self, timeout):
          send([CanData(0x730, bytes((len(command),))+command+bytes(7-len(command)), 1)])
          if command == b'\x28\x83\x01' and mode not in ('sent', 'sent_restore'):
            raise OSError('simulated partial send')
          if command == b'\x28\x00\x01' and mode not in ('restored', 'sent_restore'):
            return {}
          return {(0x730, None): b''}
      return Query()
    def hook(cp, candidate, fingerprints, firmware):
      return holder.prepare(cp, CarInterface, (recv, lambda frames: None), requested=requested, admission=admission)
    fp = gen_empty_fingerprint()
    fp[2][0x50], fp[1][0x1cf] = 16, 8
    fw = [structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.adas)]
    fingerprint = (car, fp, '0'*17, fw, original.fingerprintSource, True)
    with patch.object(car_helpers, 'fingerprint', return_value=fingerprint), \
         patch.object(disable_module, 'IsoTpParallelQuery', side_effect=query), \
         patch.object(ecu_startup, 'IsoTpParallelQuery', side_effect=query):
      if fail_ctor:
        try:
          with patch.object(CarInterface, 'CarController', side_effect=RuntimeError('constructor failed')):
            car_helpers.get_car(recv, lambda frames: None, lambda *args: None, True, False, pre_create_hook=hook)
        finally:
          holder.close()
      ci = car_helpers.get_car(recv, lambda frames: None, lambda *args: None, True, False, pre_create_hook=hook)
      ci_ref.append(ci)
      holder.configure(ci)
      holder.seal_publication()
    return ci, holder, requests

  def test_sent_prepublication_binds_immutable_template_and_suppressed_protocol(self):
    ci, holder, requests = self.exercise()
    self.assertIs(holder.owner.outcome, Outcome.SENT_UNCONFIRMED)
    self.assertIs(ci.CC.adrv_template, holder.owner.template)
    self.assertTrue(ci.CP.openpilotLongitudinalControl)
    self.assertIn(b'\x28\x83\x01', requests)
    self.assertNotIn(b'\x28\x03\x01', requests)
    ci.CP.safetyConfigs[-1].safetyParam ^= 4
    with self.assertRaisesRegex(RuntimeError, 'prepared'):
      holder.seal_publication()

  def test_missing_capture_never_requests_uds_and_partial_restore_warms_actual_stock(self):
    ci, holder, requests = self.exercise(capture=False)
    self.assertEqual(requests, [])
    self.assertIs(holder.owner.outcome, Outcome.STOCK_UNTOUCHED)
    self.assertFalse(ci.CP.openpilotLongitudinalControl)
    ci, holder, requests = self.exercise('restored')
    self.assertIs(holder.owner.outcome, Outcome.STOCK_RESTORED)
    self.assertIn(b'\x28\x00\x01', requests)
    self.assertTrue(holder.owner.ready)
    self.assertIsNone(ci.CC.adrv_template)

  def test_partial_failure_without_restore_admission_cannot_publish(self):
    admitted = iter((True, False))
    with self.assertRaisesRegex(RuntimeError, 'restoration unverified'):
      self.exercise('restored', admission=lambda: next(admitted))
    with self.assertRaisesRegex(RuntimeError, 'restoration unverified'):
      self.exercise('uncertain')

  def test_stock_copy_exact_and_button_pause_policy_and_explicit_owner_guard(self):
    for radar in (False, True):
      self.assertEqual(stock_copy(params(radar=radar)).to_dict(), params(False, radar).to_dict())
    ci = CarInterface(params())
    buttons = ci.can_parsers[Bus.pt].message_states[0x1cf]
    self.assertGreaterEqual(buttons.timeout_threshold, 500_000_000)
    self.assertNotIn(0x1a0, ci.can_parsers[Bus.pt].addresses)
    stock = CarInterface(params(False))
    self.assertIn(0x1a0, stock.can_parsers[Bus.pt].addresses)
    with self.assertRaisesRegex(RuntimeError, 'matching prepared'):
      VehicleStartupOwner().configure(ci)
    self.assertIsNone(CarInterface.startup_owner(params(), (list, lambda frames: None), requested=False))
    sibling = params()
    sibling.carFingerprint = CAR.HYUNDAI_IONIQ_6
    self.assertFalse(eligible(sibling))

  def test_missing_stock_source_cannot_publish_and_buttons_can_pause(self):
    with self.assertRaisesRegex(RuntimeError, 'stock CANFD'):
      self.exercise('restored', missing_source='SCC_CONTROL')
    ci, holder, _ = self.exercise('restored')
    parser = ci.can_parsers[Bus.pt]
    # Freeze the real last button receipt while refreshing all other sources.
    packer = CANPacker(DBC[CAR.KIA_EV6][Bus.pt])
    stamp = max(source.timestamps[-1] for source in parser.message_states.values() if source.timestamps)
    for i in range(1, 51):
      frames = []
      for source_parser in ci.can_parsers.values():
        for address in source_parser.addresses:
          name = source_parser.dbc.addr_to_msg[address].name
          if name not in ('CRUISE_BUTTONS', 'CRUISE_BUTTONS_ALT'):
            frames.append(CanData(*packer.make_can_msg(name, source_parser.bus, {})))
      ci.update([(stamp+i*10_000_000, frames)])
    self.assertTrue(ci.CS.out.canValid)
    self.assertTrue(holder.owner._sources(ci, stamp+500_000_000, floor=holder.owner.floor_ns))

  def test_capture_rejects_wrong_bus_crc_repeats_and_old_producers(self):
    for bad in ('bus', 'crc', 'repeat', 'stale'):
      with self.subTest(bad=bad):
        tick = [1_000_000_000]
        counter = [0]
        def recv(tick=tick, counter=counter, bad=bad):
          tick[0] += 100_000_000
          counter[0] += 1
          data = bytearray(32)
          data[2] = 7 if bad == 'repeat' else counter[0]
          data[4] = 1
          data[:2] = hkg_can_fd_checksum(0x51, None, data).to_bytes(2, 'little')
          if bad == 'crc':
            data[0] ^= 1
          return [TimestampedCanPacket([CanData(0x51, bytes(data), 1 if bad == 'bus' else 0)],
                                       1 if bad == 'stale' else tick[0])]
        owner = EV6Startup(params(), (recv, lambda frames: self.fail('capture must not transmit')))
        with patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True), \
             patch.object(time, 'clock_gettime_ns', side_effect=lambda clock, tick=tick: tick[0]), \
             patch.object(time, 'monotonic', side_effect=lambda tick=tick: tick[0]/1e9), patch.object(time, 'sleep'):
          self.assertIsNone(owner._capture())

  def test_unpublished_actual_constructor_failure_restores_transaction(self):
    with self.assertRaisesRegex(RuntimeError, 'constructor failed'):
      self.exercise('sent_restore', fail_ctor=True)
    self.assertIn(b'\x28\x83\x01', self.last_requests)
    self.assertIn(b'\x28\x00\x01', self.last_requests)

  def test_wrong_bus_stale_and_counter_loss_stock_sources_cannot_publish(self):
    for fault in ('wrongbus', 'stale', 'counter'):
      with self.subTest(fault=fault), self.assertRaisesRegex(RuntimeError, 'stock CANFD'):
        self.exercise('restored', warm_fault=fault)
