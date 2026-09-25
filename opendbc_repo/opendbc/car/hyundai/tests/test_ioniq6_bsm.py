import json
import unittest
from pathlib import Path

from opendbc.can import CANPacker
from opendbc.car import Bus, CanData, gen_empty_fingerprint, structs
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.hyundaicanfd import create_ioniq6_blindspot_status, hkg_can_fd_checksum
from opendbc.car.hyundai.ioniq6_bsm import BlindspotStatus, Ioniq6BlindspotSources
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.ioniq6_handoff import build_ioniq6_hda2_long_candidate
from opendbc.car.hyundai.values import CAR, DBC


CASES = json.loads((Path(__file__).parent / "testdata" / "ioniq6_bsm_frozen.json").read_text())["cases"]


def long_params():
  fingerprint = gen_empty_fingerprint()
  fingerprint[2].update({0x50: 16, 0x2A4: 24})
  fingerprint[1].update({0x1CF: 8, 0x35: 32, 0x175: 24, 0xA0: 24, 0xEA: 24,
                         0x1BA: 24, 0x1E5: 16, 0x36A: 16})
  fingerprint[0][0x3A5] = 24
  stock = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, fingerprint, [], False, False, False)
  candidate = build_ioniq6_hda2_long_candidate(stock, fingerprint)
  assert candidate is not None
  return candidate


class TestIoniq6BlindspotStatus(unittest.TestCase):
  def test_all_sixteen_frozen_executable_outputs_and_integrity(self):
    for case in CASES:
      with self.subTest(case=case):
        left = 1 + int(case["leftBlinker"]) if case["left"] else 0
        right = 1 + int(case["rightBlinker"]) if case["right"] else 0
        frames = create_ioniq6_blindspot_status(case["counter"], BlindspotStatus(left, right))
        self.assertEqual([(addr, bus) for addr, _, bus in frames], [(0x1BA, 1), (0x1E5, 1)])
        self.assertEqual([payload.hex() for _, payload, _ in frames], [case["rear"], case["front"]])
        for addr, payload, _ in frames:
          self.assertEqual(int.from_bytes(payload[:2], "little"), hkg_can_fd_checksum(addr, None, bytearray(payload)))

  def test_fresh_corner_and_lamp_holding_boundary(self):
    sources = Ioniq6BlindspotSources()
    t = 1_000_000_000
    self.assertIsNone(sources.status(t))
    sources.observe(corner_source_ns=t, corner_state=0x18, lamp_source_ns=t, left_lamp=True, right_lamp=False)
    self.assertEqual(sources.status(t), BlindspotStatus(2, 1))
    sources.observe(corner_source_ns=t + 100_000_000, corner_state=0x18,
                    lamp_source_ns=t + 100_000_000, left_lamp=False, right_lamp=False)
    self.assertEqual(sources.status(t + 100_000_000), BlindspotStatus(2, 1))
    # Repeated false lamp frames must not restart the hold.
    sources.observe(corner_source_ns=t + 590_000_000, corner_state=0x18,
                    lamp_source_ns=t + 590_000_000, left_lamp=False, right_lamp=False)
    self.assertEqual(sources.status(t + 600_000_000), BlindspotStatus(2, 1))
    self.assertEqual(sources.status(t + 600_000_001), BlindspotStatus(1, 1))
    self.assertIsNone(sources.status(t + 690_000_001))  # corner expiry
    sources.observe(corner_source_ns=t + 700_000_000, corner_state=0x18,
                    lamp_source_ns=t + 700_000_000, left_lamp=False, right_lamp=False)
    sources.observe(corner_source_ns=t + 2_200_000_001, corner_state=0x18,
                    lamp_source_ns=t + 700_000_000, left_lamp=False, right_lamp=False)
    self.assertIsNone(sources.status(t + 2_200_000_001))  # lamp expiry

  def test_live_lamp_does_not_expire_before_its_off_transition(self):
    sources = Ioniq6BlindspotSources()
    t = 1_000_000_000
    sources.observe(corner_source_ns=t, corner_state=0x10, lamp_source_ns=t, left_lamp=True, right_lamp=False)
    sources.observe(corner_source_ns=t + 600_000_000, corner_state=0x10,
                    lamp_source_ns=t + 600_000_000, left_lamp=True, right_lamp=False)
    self.assertEqual(sources.status(t + 600_000_000), BlindspotStatus(2, 0))
    sources.observe(corner_source_ns=t + 700_000_000, corner_state=0x10,
                    lamp_source_ns=t + 700_000_000, left_lamp=False, right_lamp=False)
    self.assertEqual(sources.status(t + 700_000_000), BlindspotStatus(2, 0))
    sources.observe(corner_source_ns=t + 1_200_000_001, corner_state=0x10,
                    lamp_source_ns=t + 1_200_000_001, left_lamp=False, right_lamp=False)
    self.assertEqual(sources.status(t + 1_200_000_001), BlindspotStatus(1, 0))

  def test_stale_lamp_gap_cannot_create_a_new_hold(self):
    sources = Ioniq6BlindspotSources()
    t = 1_000_000_000
    sources.observe(corner_source_ns=t, corner_state=0x10, lamp_source_ns=t, left_lamp=True, right_lamp=False)
    self.assertEqual(sources.status(t), BlindspotStatus(2, 0))
    self.assertIsNone(sources.status(t + 1_500_000_001))
    sources.observe(corner_source_ns=t + 2_000_000_000, corner_state=0x10,
                    lamp_source_ns=t + 2_000_000_000, left_lamp=False, right_lamp=False)
    self.assertEqual(sources.status(t + 2_000_000_000), BlindspotStatus(1, 0))

  def test_actual_parser_dynamic_alt_lamp_and_checksum_freshness(self):
    cp = long_params()
    ci = CarInterface(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    t = 1_000_000_000
    corner = packer.make_can_msg("BLINDSPOTS_FRONT_CORNER_2", 1, {"SIDE_DETECT_STATE": 0x10})
    alt_lamp = packer.make_can_msg("BLINKERS", 1, {"USE_ALT_LAMP": 1, "LEFT_LAMP_ALT": 1})
    ci.update([(t, [corner, alt_lamp])])
    self.assertTrue(ci.CS.out.leftBlinker)
    self.assertEqual(ci.CS.ioniq6_bsm_sources.status(t), BlindspotStatus(2, 0))
    corrupted = bytearray(corner[1])
    corrupted[0] ^= 1
    ci.update([(t + 101_000_000, [CanData(corner[0], bytes(corrupted), corner[2])])])
    self.assertIsNone(ci.CS.ioniq6_bsm_sources.status(t + 101_000_000))

  def test_controller_emits_only_fresh_paired_status_in_exact_long_profile(self):
    cp = long_params()
    ci = CarInterface(cp)
    controller = CarController(DBC[cp.carFingerprint], cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    t = 10_000_000_000  # CAN BOOTTIME; controller below sees MONOTONIC.
    ci.update([(t, [packer.make_can_msg("BLINDSPOTS_FRONT_CORNER_2", 1, {"SIDE_DETECT_STATE": 0x10}),
                    packer.make_can_msg("BLINKERS", 1, {})])])
    control = structs.CarControl()
    _, frames = controller.update(control.as_reader(), ci.CS, t - 9_000_000_000)
    rear_front = [(addr, payload, bus) for addr, payload, bus in frames if addr in (0x1BA, 0x1E5)]
    self.assertEqual(rear_front, create_ioniq6_blindspot_status(0, BlindspotStatus(1, 0)))
    for i in range(1, 5):
      controller.update(control.as_reader(), ci.CS, t - 9_000_000_000 + i * 10_000_000)
    ci.update([(t + 50_000_000, [packer.make_can_msg("BLINDSPOTS_FRONT_CORNER_2", 1, {"SIDE_DETECT_STATE": 0x10}),
                               packer.make_can_msg("BLINKERS", 1, {})])])
    _, next_frames = controller.update(control.as_reader(), ci.CS, t - 9_000_000_000 + 50_000_000)
    self.assertEqual([(addr, payload, bus) for addr, payload, bus in next_frames if addr in (0x1BA, 0x1E5)],
                     create_ioniq6_blindspot_status(1, BlindspotStatus(1, 0)))
    for i in range(6, 10):
      controller.update(control.as_reader(), ci.CS, t - 9_000_000_000 + i * 10_000_000)
    # An unrelated physical CAN update advances BOOTTIME without refreshing the
    # corner source. Host must withhold both frames; no zero-status substitute.
    ci.update([(t + 160_000_000, [packer.make_can_msg("WHEEL_SPEEDS", 1, {})])])
    _, stale = controller.update(control.as_reader(), ci.CS, t - 9_000_000_000 + 160_000_000)
    self.assertFalse(any(addr in (0x1BA, 0x1E5) for addr, _, _ in stale))
