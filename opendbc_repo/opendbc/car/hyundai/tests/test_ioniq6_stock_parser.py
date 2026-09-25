"""Synthetic stock CAN graph through actual CarState, CANParser and CI aggregation."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.interfaces import CarInterfaceBase
from opendbc.car.hyundai.ioniq6_handoff import (build_ioniq6_hda2_long_candidate, finalize_ioniq6_prepublication,
                                             HandoffOutcome, HandoffResult)
from opendbc.car.hyundai.values import CAR, DBC


def params(alternate):
  fingerprint = gen_empty_fingerprint()
  fingerprint[2].update({0x110 if alternate else 0x50: 32 if alternate else 16,
                         0x362 if alternate else 0x2A4: 32 if alternate else 24})
  fingerprint[1].update({0x1CF: 8, 0x35: 32, 0x175: 24, 0xA0: 24, 0xEA: 24,
                         0x1BA: 24, 0x1E5: 16, 0x36A: 16})
  fingerprint[0][0x3A5] = 24
  cp = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, fingerprint, [], False, False, False)
  return cp, fingerprint


class StockParserTests(unittest.TestCase):
  def host(self, cp):
    cs = CarState(cp)
    ci = SimpleNamespace(CS=cs, CP=cp, can_parsers=cs.get_can_parsers(cp), v_ego_cluster_seen=False)
    ci.update = lambda frames: CarInterfaceBase.update(ci, frames)
    ci.update([])  # register every lazy field the real CarState consumes
    return ci

  def feed(self, ci, *, omit=(), alt_units=None, count=200):
    packer = CANPacker(DBC[ci.CP.carFingerprint][Bus.pt])
    out = None
    for index in range(1, count + 1):
      frames = []
      ci.test_time_ns = getattr(ci, 'test_time_ns', 1_000_000_000) + 10_000_000
      for parser in ci.can_parsers.values():
        for state in list(parser.message_states.values()):
          if state.name in omit or (state.ignore_alive and not (state.name == 'CRUISE_BUTTONS_ALT' and alt_units is not None)):
            continue
          values = {'COUNTER': index % (16 if state.name == 'CRUISE_BUTTONS' else 256)} if any(signal.name == 'COUNTER' for signal in state.signals) else {}
          if state.name == 'ACCELERATOR': values.update(GEAR=5)
          elif state.name == 'DOORS_SEATBELTS': values.update(DRIVER_SEATBELT=1)
          elif state.name == 'SCC_CONTROL': values.update(ACCMode=1, VSetDis=60)
          elif state.name == 'CRUISE_BUTTONS_ALT': values.update(DISTANCE_UNIT=alt_units)
          frame = packer.make_can_msg(state.name, parser.bus, values)
          frames.append((frame[0], frame[1], frame[2]))
      out = ci.update([(ci.test_time_ns, frames)])
    return out

  def test_alpha_off_and_alpha_preflight_stock_fallback_without_optional_alt(self):
    for alternate in (False, True):
      for enabled in (False, True):
        with self.subTest(alternate=alternate, alpha_requested=enabled):
          stock, fingerprint = params(alternate)
          candidate = build_ioniq6_hda2_long_candidate(stock, fingerprint)
          exchanges = []
          with patch('opendbc.car.hyundai.ioniq6_handoff.run_ioniq6_handoff',
                     return_value=HandoffResult(HandoffOutcome.STOCK, 'preflight_scc_period')):
            cp, selected, _ = finalize_ioniq6_prepublication(stock, candidate, lambda **kw: [], exchanges.append,
                                                           enabled=enabled, is_release=False)
          self.assertIs(cp, stock)
          self.assertFalse(selected)
          self.assertEqual(exchanges, [])
          self.assertTrue(cp.pcmCruise)
          self.assertFalse(cp.openpilotLongitudinalControl)
          ci = self.host(cp)
          parser = ci.can_parsers[Bus.pt]
          self.assertTrue(parser.message_states[parser.dbc.name_to_msg['CRUISE_BUTTONS_ALT'].address].ignore_alive)
          out = self.feed(ci)
          self.assertTrue(out.canValid)
          self.assertFalse(out.canTimeout)
          self.assertTrue(out.cruiseState.enabled)
          self.assertTrue(ci.CS.is_metric)  # existing absent-units default, not current units proof

  def test_present_optional_alt_units_still_decode(self):
    for alternate in (False, True):
      cp, _ = params(alternate)
      ci = self.host(cp)
      out = self.feed(ci, alt_units=1)
      self.assertTrue(out.canValid)
      self.assertFalse(ci.CS.is_metric)

  def test_stock_required_inputs_remain_required(self):
    for alternate in (False, True):
      for missing in ('ACCELERATOR', 'TCS', 'WHEEL_SPEEDS', 'MDPS', 'CRUISE_BUTTONS', 'SCC_CONTROL'):
        with self.subTest(alternate=alternate, missing=missing):
          cp, _ = params(alternate)
          ci = self.host(cp)
          self.assertTrue(self.feed(ci).canValid)
          parser = ci.can_parsers[Bus.pt]
          state = parser.message_states[parser.dbc.name_to_msg[missing].address]
          self.assertFalse(state.ignore_alive)
          # Advance past the actual retained parser timeout, keep all siblings healthy.
          out = self.feed(ci, omit=(missing,), count=int(state.timeout_threshold / 10_000_000) + 20)
          self.assertFalse(out.canValid)

  def test_existing_long_parser_subscription_contract_is_unchanged(self):
    for alternate in (False, True):
      stock, fingerprint = params(alternate)
      cp = build_ioniq6_hda2_long_candidate(stock, fingerprint)
      self.assertIsNotNone(cp)
      ci = self.host(cp)
      pt = ci.can_parsers[Bus.pt]
      for name in ('ACCELERATOR', 'TCS', 'WHEEL_SPEEDS', 'MDPS', 'CRUISE_BUTTONS'):
        self.assertFalse(pt.message_states[pt.dbc.name_to_msg[name].address].ignore_alive)
      self.assertTrue(pt.message_states[pt.dbc.name_to_msg['CRUISE_BUTTONS_ALT'].address].ignore_alive)
      self.assertNotIn(pt.dbc.name_to_msg['SCC_CONTROL'].address, pt.message_states)
      camera_name = 'CAM_0x362' if alternate else 'CAM_0x2a4'
      cam = ci.can_parsers[Bus.cam]
      self.assertEqual(cam.message_states[cam.dbc.name_to_msg[camera_name].address].frequency, 20)


if __name__ == '__main__':
  unittest.main()
