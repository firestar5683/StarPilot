import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.carstate import CarState, decode_ioniq_6_corner_bsm
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.radar_interface import MRR35_RADAR_START_ADDR, RadarInterface, get_radar_can_parser, radar_bus
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags


def params(topology: str, *, radar_bus_number: int | None = None, radar_length: int = 24, bsm: bool = False):
  fingerprint = gen_empty_fingerprint()
  if topology == "lka":
    fingerprint[2][0x50] = 16
  elif topology == "lka_alt":
    fingerprint[2][0x110] = 32
  else:
    assert topology == "camera"
  ecan = 1 if topology != "camera" else 0
  fingerprint[ecan][0x1cf] = 8
  if radar_bus_number is not None:
    fingerprint[radar_bus_number][MRR35_RADAR_START_ADDR] = radar_length
  if bsm:
    fingerprint[ecan][0x1ba] = 24
  return CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, fingerprint, [], False, False, False)


class TestIoniq6ReceiveOnly(unittest.TestCase):
  def test_radar_bus_length_and_stock_cruise_are_topology_bound(self):
    for topology, expected_bus in (("camera", 1), ("lka", 0), ("lka_alt", 0)):
      for observed_bus, length in ((None, 24), (expected_bus, 24), (1 - expected_bus, 24), (expected_bus, 8)):
        with self.subTest(topology=topology, bus=observed_bus, length=length):
          cp = params(topology, radar_bus_number=observed_bus, radar_length=length)
          self.assertEqual(radar_bus(cp), expected_bus)
          self.assertEqual(get_radar_can_parser(cp).bus, expected_bus)
          self.assertEqual(cp.radarUnavailable, observed_bus != expected_bus or length != 24)
          self.assertFalse(cp.openpilotLongitudinalControl)
          self.assertTrue(cp.pcmCruise)
          self.assertFalse(cp.alphaLongitudinalAvailable)
          self.assertEqual(bool(cp.flags & HyundaiFlags.CANFD_CAMERA_SCC), topology == "camera")

  def test_mrr35_real_packed_cycle_with_missing_and_delayed_tracks(self):
    for topology, expected_bus in (("camera", 1), ("lka", 0), ("lka_alt", 0)):
      with self.subTest(topology=topology):
        cp = params(topology, radar_bus_number=expected_bus)
        radar = RadarInterface(cp)
        packer = CANPacker(DBC[cp.carFingerprint][Bus.radar])
        track = packer.make_can_msg("RADAR_TRACK_3a5", expected_bus, {
          "STATE": 3, "LONG_DIST": 28.5, "LAT_DIST": -1.25, "REL_SPEED": -2.5,
        })
        trigger = packer.make_can_msg("RADAR_TRACK_3c4", expected_bus, {})
        wrong_bus_track = (track[0], track[1], 1 - expected_bus)
        self.assertIsNone(radar.update((1_000_000_000, [wrong_bus_track])))
        self.assertEqual(len(radar.update((1_010_000_000, [(track[0], track[1][:8], expected_bus), trigger])).points), 0)
        out = radar.update((1_050_000_000, [track, trigger]))
        self.assertEqual(len(out.points), 1)
        self.assertAlmostEqual(out.points[0].dRel, 28.5, delta=0.05)
        self.assertAlmostEqual(out.points[0].yRel, -1.25, delta=0.05)
        self.assertAlmostEqual(out.points[0].vRel, -2.5, delta=0.02)
        out = radar.update((1_100_000_000, [trigger]))
        self.assertEqual(len(out.points), 0)
        self.assertIsNone(radar.update((1_125_000_000, [track, (trigger[0], trigger[1][:8], expected_bus)])))
        self.assertIsNone(radar.update((1_150_000_000, [track])))
        out = radar.update((1_250_000_000, [trigger]))
        self.assertEqual(len(out.points), 0)

  def test_corner_bits_are_received_without_status_transmission(self):
    self.assertEqual(decode_ioniq_6_corner_bsm(0x02), (False, False))
    self.assertEqual(decode_ioniq_6_corner_bsm(0x0a), (False, True))
    self.assertEqual(decode_ioniq_6_corner_bsm(0x12), (True, False))
    self.assertEqual(decode_ioniq_6_corner_bsm(0x1a), (True, True))
    for topology in ("camera", "lka", "lka_alt"):
      with self.subTest(topology=topology):
        cp = params(topology, bsm=True)
        self.assertTrue(cp.deprecated.enableBsm)
        can_bus = CanBus(cp)
        state = CarState(cp)
        parsers = state.get_can_parsers(cp)
        parser = parsers[Bus.pt]
        self.assertEqual(parser.message_states[0x1ba].frequency, 0)
        self.assertEqual(parser.message_states[0x36a].frequency, 0)
        state.out = state.update(parsers)
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        rear = packer.make_can_msg("ADAS_CMD_50_50ms", can_bus.ECAN, {"BCW_LtIndSta": 1})
        front = packer.make_can_msg("BLINDSPOTS_FRONT_CORNER_2", can_bus.ECAN, {"SIDE_DETECT_STATE": 0x08})
        parser.update((1_000_000_000, [rear, front]))
        state.out = state.update(parsers)
        self.assertTrue(state.out.leftBlindspot)
        self.assertTrue(state.out.rightBlindspot)
        control = structs.CarControl()
        control.enabled = control.latActive = True
        _, sent = CarController(DBC[cp.carFingerprint], cp).update(control.as_reader(), state, 1_000_000_000)
        self.assertFalse({0x1ba, 0x1e5, 0x36a} & {address for address, _, _ in sent})
        wrong_bus_front = (front[0], front[1], 1 - can_bus.ECAN)
        parser.update((1_100_000_000, [wrong_bus_front]))
        state.out = state.update(parsers)
        self.assertTrue(state.out.rightBlindspot)
        # Rear and front sources expire independently as normal fuel traffic
        # advances the parser clock; neither can advertise indefinitely.
        fuel = packer.make_can_msg("ACCELERATOR", can_bus.ECAN, {})
        fresh_front = packer.make_can_msg("BLINDSPOTS_FRONT_CORNER_2", can_bus.ECAN, {"SIDE_DETECT_STATE": 0x10})
        parser.update((1_250_000_000, [fuel, fresh_front]))
        state.out = state.update(parsers)
        self.assertTrue(state.out.leftBlindspot)
        self.assertFalse(state.out.rightBlindspot)
        parser.update((1_500_000_000, [fuel]))
        state.out = state.update(parsers)
        self.assertFalse(state.out.leftBlindspot)
        self.assertFalse(state.out.rightBlindspot)

  def test_front_source_without_rear_detection_does_not_enable_bsm(self):
    cp = params("lka")
    self.assertFalse(cp.deprecated.enableBsm)
    state = CarState(cp)
    parser = state.get_can_parsers(cp)[Bus.pt]
    self.assertNotIn(0x36a, parser.message_states)
    fingerprint = gen_empty_fingerprint()
    fingerprint[2][0x50] = 16
    fingerprint[1][0x1ba] = 16
    cp = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, fingerprint, [], False, False, False)
    self.assertFalse(cp.deprecated.enableBsm)


if __name__ == "__main__":
  unittest.main()
