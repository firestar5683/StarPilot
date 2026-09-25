import math
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.radar_interface import RadarInterface
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags, HYUNDAI_G90_RADAR_DBC
from opendbc.dbc.generator.hyundai.hyundai_kia_mando_front_radar import generate


def params(bank=None):
  fp = gen_empty_fingerprint()
  if bank is not None:
    fp[1].update(bank)
  return CarInterface.get_params(CAR.GENESIS_G90, fp, [], False, False, False)


def raw_motorola(data, start, size, signed=False):
  raw = 0
  bit = start
  for _ in range(size):
    raw = (raw << 1) | ((data[bit // 8] >> (bit % 8)) & 1)
    bit = bit - 1 if bit % 8 else bit + 15
  return raw - (1 << size) if signed and raw & (1 << (size - 1)) else raw


class TestG90Radar(unittest.TestCase):
  def setUp(self):
    self.packer = CANPacker(HYUNDAI_G90_RADAR_DBC)
    self.bank = dict.fromkeys(range(0x500, 0x540), 8)

  def test_readiness_lower_bank_exact_length_and_stable_authority(self):
    absent = params()
    present = params(self.bank)
    self.assertTrue(absent.radarUnavailable)
    self.assertFalse(present.radarUnavailable)
    self.assertTrue(present.flags & HyundaiFlags.MANDO_RADAR)
    self.assertFalse(present.openpilotLongitudinalControl)
    self.assertEqual([(cfg.safetyModel, cfg.safetyParam) for cfg in absent.safetyConfigs],
                     [(cfg.safetyModel, cfg.safetyParam) for cfg in present.safetyConfigs])
    lower_bank = dict.fromkeys(range(0x500, 0x520), 8)
    self.assertFalse(params(lower_bank).radarUnavailable)
    radar = RadarInterface(params(lower_bank))
    lower_frames = [self.packer.make_can_msg(f'RADAR_TRACK_{addr:x}', 1, {'STATE': 3, 'LONG_DIST': 10})
                    for addr in lower_bank]
    result = radar.update((1_000_000_000, lower_frames))
    self.assertEqual(len(result.points), 32)
    self.assertTrue(all(addr < 0x520 for addr in radar.pts))
    for address in lower_bank:
      bank = lower_bank.copy()
      del bank[address]
      self.assertTrue(params(bank).radarUnavailable)
      bank[address] = 16
      self.assertTrue(params(bank).radarUnavailable)

  def test_both_halves_all_current_typed_outputs_match_original_bits(self):
    radar = RadarInterface(params(self.bank))
    self.assertEqual((radar.rcp.bus, radar.start_addr, radar.msg_count, radar.trigger_msg), (1, 0x500, 64, 0x51F))
    frames = []
    for index, address in enumerate(self.bank):
      frames.append(self.packer.make_can_msg(f'RADAR_TRACK_{address:x}', 1, {
        'STATE': 3 if index % 2 == 0 else 4, 'LONG_DIST': index + 1,
        'AZIMUTH': 10.0 if index % 2 == 0 else -10.0, 'REL_SPEED': -.01 * index,
      }))
    result = radar.update((1_000_000_000, frames))
    self.assertFalse(result.errors.canError)
    self.assertEqual(len(result.points), 64)
    self.assertEqual(len({point.trackId for point in result.points}), 64)
    for point, (_, data, _) in zip(result.points, frames, strict=True):
      azimuth = math.radians(raw_motorola(data, 12, 10, True) * .2)
      distance = raw_motorola(data, 18, 11) * .1
      speed = raw_motorola(data, 53, 14, True) * .01
      self.assertAlmostEqual(point.dRel, math.cos(azimuth) * distance, places=5)
      self.assertAlmostEqual(point.yRel, -.5 * math.sin(azimuth) * distance, places=5)
      self.assertAlmostEqual(point.vRel, speed, places=6)

  def test_original_lower_trigger_and_upper_cycle_freshness(self):
    radar = RadarInterface(params(self.bank))
    lower = [self.packer.make_can_msg(f'RADAR_TRACK_{addr:x}', 1, {}) for addr in range(0x500, 0x520)]
    upper = self.packer.make_can_msg('RADAR_TRACK_520', 1, {'STATE': 3, 'LONG_DIST': 20, 'REL_SPEED': -1})
    self.assertIsNone(radar.update((1_000_000_000, [(upper[0], upper[1], 0)])))
    self.assertIsNone(radar.update((1_010_000_000, [(upper[0], upper[1] * 2, 1)])))
    self.assertIsNone(radar.update((1_020_000_000, [(upper[0], upper[1][:4], 1)])))
    self.assertEqual(len(radar.update((1_030_000_000, lower)).points), 0)
    self.assertIsNone(radar.update((1_040_000_000, [upper])))
    result = radar.update((1_050_000_000, lower))
    self.assertEqual(len(result.points), 1)
    first_id = result.points[0].trackId
    # Fresh upper-bank packet never drives cadence by itself.
    self.assertIsNone(radar.update((1_060_000_000, [upper])))
    self.assertEqual(len(radar.update((1_090_000_000, lower)).points), 0)
    self.assertIsNone(radar.update((1_100_000_000, [upper])))
    self.assertEqual(len(radar.update((1_110_000_000, lower)).points), 1)
    self.assertGreater(radar.pts[0x520].trackId, first_id)
    invalid = self.packer.make_can_msg('RADAR_TRACK_520', 1, {'STATE': 2})
    radar.update((1_120_000_000, [invalid]))
    self.assertEqual(len(radar.update((1_130_000_000, lower)).points), 0)

  def test_ordinary_mando_generator_and_parser_unchanged(self):
    outputs = generate()
    ordinary = outputs['hyundai_kia_mando_front_radar.dbc']
    extended = outputs['hyundai_genesis_g90_radar.dbc']
    self.assertTrue(extended.startswith(ordinary))
    self.assertEqual(ordinary.count('\nBO_ '), 32)
    self.assertEqual(extended.count('\nBO_ '), 64)
    cars = [car for car in CAR if car != CAR.GENESIS_G90 and
            DBC[car].get(Bus.radar) == 'hyundai_kia_mando_front_radar_generated']
    self.assertTrue(cars)
    for car in cars:
      cp = CarInterface.get_params(car, gen_empty_fingerprint(), [], False, False, False)
      radar = RadarInterface(cp)
      self.assertEqual((radar.rcp.bus, radar.start_addr, radar.msg_count, radar.trigger_msg), (1, 0x500, 32, 0x51F))


if __name__ == '__main__':
  unittest.main()
