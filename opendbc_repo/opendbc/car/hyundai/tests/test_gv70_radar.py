import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.radar_interface import RadarInterface, get_radar_can_parser
from opendbc.car.hyundai.values import CAR, DBC, HYUNDAI_GV70_RADAR_DBC, HYUNDAI_MRR35_RADAR_DBC

CAR_ID = CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN


def params(bank=None):
  fp = gen_empty_fingerprint()
  fp[0][0x1CF] = 8
  if bank is not None:
    fp[0].update(bank)
  return CarInterface.get_params(CAR_ID, fp, [], False, False, False)


class TestGv70Radar(unittest.TestCase):
  def test_complete_exact_bank_required_without_changing_controls(self):
    complete = dict.fromkeys(range(0x210, 0x220), 32)
    absent = params()
    active = params(complete)
    self.assertTrue(absent.radarUnavailable)
    self.assertFalse(active.radarUnavailable)
    self.assertEqual(absent.flags, active.flags)
    self.assertEqual([(cfg.safetyModel, cfg.safetyParam) for cfg in absent.safetyConfigs],
                     [(cfg.safetyModel, cfg.safetyParam) for cfg in active.safetyConfigs])
    self.assertEqual(absent.openpilotLongitudinalControl, active.openpilotLongitudinalControl)
    for address in complete:
      bank = complete.copy()
      del bank[address]
      self.assertTrue(params(bank).radarUnavailable)
      bank[address] = 24
      self.assertTrue(params(bank).radarUnavailable)
    self.assertEqual(DBC[CAR_ID][Bus.radar], HYUNDAI_GV70_RADAR_DBC)
    self.assertEqual(DBC[CAR.GENESIS_GV70_ELECTRIFIED_2ND_GEN][Bus.radar], HYUNDAI_MRR35_RADAR_DBC)

  def test_existing_non_gv70_radar_parser_bus_and_bank_unchanged(self):
    expected = {
      'hyundai_kia_mando_front_radar_generated': (1, 0x500, 32),
      'hyundai_mrrevo14f_radar_generated': (1, 0x602, 16),
      'hyundai_mrr30_radar_generated': (0, 0x210, 16),
      'hyundai_mrr35_radar_generated': (0, 0x3A5, 32),
    }
    checked = set()
    for car in CAR:
      dbc = DBC[car].get(Bus.radar)
      if dbc not in expected or dbc in checked:
        continue
      cp = CarInterface.get_params(car, gen_empty_fingerprint(), [], False, False, False)
      radar = RadarInterface(cp)
      parser = get_radar_can_parser(cp)
      bus, start, count = expected[dbc]
      if car == CAR.HYUNDAI_IONIQ_6:
        continue
      self.assertEqual((parser.bus, radar.start_addr, radar.msg_count), (bus, start, count))
      checked.add(dbc)
    self.assertEqual(checked, set(expected))

  def test_all_32_original_target_slots_remain_distinct(self):
    radar = RadarInterface(params(dict.fromkeys(range(0x210, 0x220), 32)))
    packer = CANPacker(HYUNDAI_GV70_RADAR_DBC)
    frames = []
    for ordinal, addr in enumerate(range(0x210, 0x220)):
      values = {}
      for slot in (1, 2):
        target = ordinal * 2 + slot
        values.update({f'{slot}_STATE': 3 if slot == 1 else 4,
                       f'{slot}_LONG_DIST': target, f'{slot}_LAT_DIST': -.05 * target,
                       f'{slot}_REL_SPEED': -.01 * target})
      frames.append(packer.make_can_msg(f'RADAR_TRACK_{addr:x}', 0, values))
    result = radar.update((1_000_000_000, frames))
    self.assertFalse(result.errors.canError)
    self.assertEqual(len(result.points), 32)
    self.assertEqual(len({point.trackId for point in result.points}), 32)
    for ordinal, point in enumerate(result.points, 1):
      self.assertAlmostEqual(point.dRel, ordinal)
      self.assertAlmostEqual(point.yRel, -.05 * ordinal, places=6)
      self.assertAlmostEqual(point.vRel, -.01 * ordinal, places=6)

  def test_original_layout_to_current_typed_points_and_freshness(self):
    radar = RadarInterface(params(dict.fromkeys(range(0x210, 0x220), 32)))
    self.assertEqual((radar.rcp.bus, radar.start_addr, radar.msg_count), (0, 0x210, 16))
    packer = CANPacker(HYUNDAI_GV70_RADAR_DBC)
    frames = [packer.make_can_msg(f'RADAR_TRACK_{addr:x}', 0, {}) for addr in range(0x210, 0x220)]
    frames[0] = packer.make_can_msg('RADAR_TRACK_210', 0, {
      '1_STATE': 3, '1_LONG_DIST': 42.5, '1_LAT_DIST': -1.25, '1_REL_SPEED': -2.5,
      '2_STATE': 4, '2_LONG_DIST': 18.0, '2_LAT_DIST': 1.5, '2_REL_SPEED': 3.25,
    })
    data = frames[0][1]
    self.assertEqual(len(data), 32)
    # Independent raw extraction of original bit54/182 Motorola state and
    # little-endian bit64/192 distance, bit76/204 signed lateral, bit88/216 speed.
    expected = []
    for offset in (0, 16):
      self.assertEqual((data[offset + 6] >> 4) & 7, 3 if offset == 0 else 4)
      raw = int.from_bytes(data[offset + 8:offset + 13], 'little')
      distance = (raw & 0xFFF) * .05
      lateral = (raw >> 12) & 0xFFF
      speed = (raw >> 24) & 0x3FFF
      expected.append((distance, (lateral - 4096 if lateral & 2048 else lateral) * .05,
                       (speed - 16384 if speed & 8192 else speed) * .01))
    self.assertIsNone(radar.update((1_000_000_000, [(addr, dat, 1) for addr, dat, _ in frames])))
    self.assertIsNone(radar.update((1_010_000_000, [(addr, dat[:24], bus) for addr, dat, bus in frames])))
    result = radar.update((1_020_000_000, frames))
    self.assertEqual(len(result.points), 2)
    ids = [point.trackId for point in result.points]
    for point, values in zip(result.points, expected, strict=True):
      self.assertAlmostEqual(point.dRel, values[0])
      self.assertAlmostEqual(point.yRel, values[1])
      self.assertAlmostEqual(point.vRel, values[2])
    result = radar.update((1_040_000_000, frames))
    self.assertEqual([point.trackId for point in result.points], ids)
    self.assertEqual(len(radar.update((1_090_000_000, [frames[-1]])).points), 0)
    self.assertIsNone(radar.update((1_100_000_000, [frames[0]])))
    self.assertEqual(len(radar.update((1_160_000_000, [frames[-1]])).points), 0)
    # Valid→invalid must remove tracks, never retain an earlier target.
    radar.update((1_200_000_000, frames))
    frames[0] = packer.make_can_msg('RADAR_TRACK_210', 0, {'1_STATE': 2, '2_STATE': 7})
    self.assertEqual(len(radar.update((1_220_000_000, frames)).points), 0)


if __name__ == '__main__':
  unittest.main()
