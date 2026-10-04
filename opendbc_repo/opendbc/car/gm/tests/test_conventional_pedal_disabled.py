"""Stock-only conventional GM pedal startup and cancellation."""

import os
import unittest
from unittest.mock import patch

from opendbc.can import CANPacker
from opendbc.car import Bus, structs, gen_empty_fingerprint
from opendbc.car.gm.gmcan import create_buttons
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.radar_interface import RadarInterface
from opendbc.car.gm.values import CAR, DBC, ORDINARY_CC_CAR, is_conventional_cc_pedal_profile
from opendbc.car.gm.aol import qualified_gm
from opendbc.car.gm.lateral import lane_centering_supported
from opendbc.car.gm.feature_capabilities import longitudinal_supported, display_supported
from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
from opendbc.car.gm.tests.test_conventional_pedal import pedal_frames
from opendbc.safety.tests.libsafety import libsafety_py
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.common.params import Params
from openpilot.selfdrive.car.card import Car
from openpilot.starpilot.aol.vehicle import native_matches_cp, native_profile_supported
from openpilot.starpilot.car.gm.aol import native_accepts_cp
from openpilot.starpilot.feature_runtime import enabled as feature_enabled
from openpilot.starpilot.longitudinal.vehicle_policy import policy_for as longitudinal_policy_for


def make_card(identity, removed, store):
  store.put_bool('OpenpilotEnabledToggle', True, block=True)
  store.put_bool('GMPedalLongitudinal', True, block=True)
  store.put_bool('DisableOpenpilotLongitudinal', True, block=True)
  fp = gen_empty_fingerprint()
  fp[0].update({0x201: 6, 0xF1: 6, 0xBE: 6, 0xC9: 8, 0x1C4: 8,
                0x1E1: 7, 0x3D1: 8, 0x1F5: 8, 0x184: 8, 0x34A: 5})
  if not removed:
    fp[2][0x320] = 6
  cp = CarInterface.get_params(identity, fp, [], False, False, False)
  return Car(CI=CarInterface(cp), RI=RadarInterface(cp))


class TestConventionalPedalDisabled(unittest.TestCase):
  def test_actual_card_stock_only_profiles_and_aol_preference(self):
    for identity in ORDINARY_CC_CAR:
      for removed in (False, True):
        for aol in (False, True):
          with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1', 'AOL_REPLAY_RUNTIME': '0'}):
            store = Params()
            store.put_bool('AlwaysOnLateral', aol, block=True)
            card = make_card(identity, removed, store)
            cp = card.CP
            model, word = int(cp.safetyConfigs[0].safetyModel.raw), int(cp.safetyConfigs[0].safetyParam)
            self.assertEqual(word, 0xC186 + int(removed))
            self.assertFalse(cp.openpilotLongitudinalControl or cp.pcmCruise or cp.passive)
            self.assertTrue(is_conventional_cc_pedal_profile(cp))
            self.assertTrue(lane_centering_supported(cp))
            self.assertTrue(display_supported(cp))
            self.assertTrue(qualified_gm(cp))
            self.assertFalse(longitudinal_supported(cp))
            self.assertIsNone(longitudinal_policy_for(cp))
            self.assertFalse(feature_enabled(store, cp, 'conditional', {}))
            self.assertEqual(feature_enabled(store, cp, 'aol', {}), aol)
            self.assertEqual(cp.alternativeExperience, 32 if aol else 0)
            self.assertEqual(card.aol_card_intent is not None, aol)
            self.assertTrue(native_profile_supported(model, word))
            self.assertEqual(native_accepts_cp(cp, model, word), aol)
            self.assertEqual(native_matches_cp(cp, model, word), aol)
            wrong = cp.as_reader().as_builder()
            wrong.safetyConfigs[0].safetyParam = 0xC180 + int(removed)
            self.assertFalse(qualified_gm(wrong))
            wrong = cp.as_reader().as_builder()
            wrong.openpilotLongitudinalControl = True
            self.assertFalse(is_conventional_cc_pedal_profile(wrong))

  def run_caller(self, identity, removed, *, neutral_ticks, benign=False, button_batches=None, silent_ticks=(), authority_veto=None):
    with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1', 'AOL_REPLAY_RUNTIME': '0'}):
      card = make_card(identity, removed, Params())
      ci, cp = card.CI, card.CP
      safety = libsafety_py.libsafety
      safety.set_alternative_experience(0)
      self.assertEqual(safety.set_safety_hooks(int(cp.safetyConfigs[0].safetyModel.raw), cp.safetyConfigs[0].safetyParam), 0)
      safety.init_tests()
      packer = CANPacker(DBC[identity][Bus.pt])
      generation = -1
      seen, cancelled = set(), []
      for tick in range(100):
        now = 1_000_000_000 + tick * 10_000_000
        veto = 30 <= tick < 60
        frames = pt_frames(packer, cruise=not (veto and authority_veto == 'stock'),
                           main=not (veto and authority_veto == 'main'), counter=0)
        frames = [f for f in frames if f[0] != 0x1E1]
        if tick in neutral_ticks:
          generation += 1
          frames.append(create_buttons(packer, 0, generation % 4, 1))
        if tick % 2 == 0:
          frames += pedal_frames(packer, tick // 2, pressed=benign and tick >= 40, removed=removed,
                                 bad_crc=benign and tick >= 60)
        else:
          frames += [packer.make_can_msg('EBCMBrakePedalPosition', 0, {'BrakePedalPosition': 0})]
          if not removed:
            frames += [packer.make_can_msg('ASCMLKASteeringCmd', 2, {'RollingCounter': tick % 4}),
                       packer.make_can_msg('AEBCmd', 2, {})]
        if benign and tick >= 30:
          frames = [f for f in frames if f[0] != 0xC9]
          frames.append(packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': 1, 'BrakePressed': 1}))
        if benign and tick >= 50:
          frames = [f for f in frames if f[0] != 0x1F5]
          frames.append(packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 2}))
        missing = authority_veto in (0xC9, 0x3D1) and 30 <= tick < 80
        if missing:
          frames = [f for f in frames if f[0] != authority_veto]
        batches = [(now, frames)]
        if button_batches and tick in button_batches:
          frames[:] = [f for f in frames if f[0] != 0x1E1]
          batches += [(now + delta, packets) for delta, packets in button_batches[tick](packer)]
        out = ci.update(batches)
        if not missing:
          self.assertTrue(out.canValid)
        safety.set_timer(now // 1000)
        for stamp, packets in batches:
          safety.set_timer(stamp // 1000)
          for address, data, bus in packets:
            if bus != 128:
              safety.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, data))
        safety.set_timer(now // 1000)
        safety.safety_tick()
        if not missing:
          self.assertTrue(safety.safety_config_valid())
        cc = structs.CarControl(enabled=False, latActive=False, longActive=False)
        cc.cruiseControl.cancel = True
        _, messages = ci.apply(cc.as_reader(), now)
        self.assertFalse(any(m[0] in (0x200, 0x409, 0x40A) for m in messages))
        if tick in silent_ticks:
          self.assertFalse(any(m[0] == 0x1E1 for m in messages), (tick, messages))
        for message in messages:
          if message[0] != 0x1E1:
            continue
          self.assertGreater(tick + 1, 10)
          self.assertEqual(message, create_buttons(packer, 2, message[1][4], 6))
          self.assertNotIn(generation, seen)
          seen.add(generation)
          self.assertTrue(safety.safety_tx_hook(libsafety_py.make_CANPacket(message[0], message[2], message[1])))
          cancelled.append(tick)
      self.assertTrue(cancelled)
      if benign:
        self.assertTrue(any(tick >= 60 for tick in cancelled))
      return cancelled

  def test_actual_camera_cancel_native_join_at_neutral_source_cadence(self):
    schedules = (set(range(0, 100, 10)), {0, 9, 20, 32, 43, 60, 70, 81, 93})
    for identity in ORDINARY_CC_CAR:
      for removed in (False, True):
        for schedule in schedules:
          self.run_caller(identity, removed, neutral_ticks=schedule)

  def test_benign_brake_gas_reverse_and_sensor_fault_preserve_cancel(self):
    for identity in ORDINARY_CC_CAR:
      for removed in (False, True):
        self.run_caller(identity, removed, neutral_ticks=set(range(0, 100, 10)), benign=True)

  def test_full_button_template_and_dlc_cannot_grant_cancel_credit(self):
    def corrupt(bit):
      def frames(packer):
        address, data, bus = create_buttons(packer, 0, 1, 1)
        damaged = bytearray(data)
        damaged[bit // 8] ^= 1 << (bit % 8)
        return [(0, [(address, bytes(damaged), bus)])]
      return frames

    for bit in range(56):
      with self.subTest(bit=bit):
        self.run_caller(CAR.CADILLAC_CT6_CC, False, neutral_ticks=set(range(0, 100, 10)),
                        button_batches={10: corrupt(bit)}, silent_ticks=range(10, 20))
    for length in (6, 8):
      def wrong_length(packer, length=length):
        address, data, bus = create_buttons(packer, 0, 1, 1)
        return [(0, [(address, (data + b'\0')[:length], bus)])]
      with self.subTest(length=length):
        self.run_caller(CAR.CHEVROLET_MALIBU_CC, True, neutral_ticks=set(range(0, 100, 10)),
                        button_batches={10: wrong_length}, silent_ticks=range(10, 20))

  def test_ordered_same_timestamp_and_backward_button_packets_revoke_credit(self):
    def ordered(packer):
      return [(0, [create_buttons(packer, 0, 1, 1), create_buttons(packer, 0, 1, 2)])]

    def resync(packer):
      return [(-120_000_000, [create_buttons(packer, 0, 2, 1)]),
              (0, [create_buttons(packer, 0, 1, 1)])]

    for removed in (False, True):
      self.run_caller(CAR.CADILLAC_CT6_CC, removed, neutral_ticks=set(range(0, 100, 10)),
                      button_batches={10: ordered}, silent_ticks=range(10, 20))
      # Neutral0@1s -> neutral2@.9s -> neutral1@1.02s must not transmit.
      self.run_caller(CAR.CHEVROLET_MALIBU_CC, removed, neutral_ticks=set(range(0, 100, 10)),
                      button_batches={2: resync}, silent_ticks=range(2, 20))
      def changed_same_stamp(packer):
        return [(-10_000_000, [create_buttons(packer, 0, 1, 2)])]
      self.run_caller(CAR.CADILLAC_CT6_CC, removed, neutral_ticks=set(range(0, 100, 10)),
                      button_batches={11: changed_same_stamp}, silent_ticks=range(11, 20))

  def test_current_main_stock_active_and_source_freshness_are_required(self):
    for removed in (False, True):
      for veto in ('main', 'stock'):
        with self.subTest(removed=removed, veto=veto):
          self.run_caller(CAR.CADILLAC_CT6_CC, removed, neutral_ticks=set(range(0, 100, 10)),
                          authority_veto=veto, silent_ticks=range(30, 60))
      for source in (0xC9, 0x3D1):
        with self.subTest(removed=removed, stale_source=source):
          self.run_caller(CAR.CADILLAC_CT6_CC, removed, neutral_ticks=set(range(0, 100, 10)),
                          authority_veto=source, silent_ticks=range(60, 80))
