import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags


class TestCanfdBlinkers(unittest.TestCase):
  def read_lamps(self, model, values, invalid_selector=None):
    cp = CarInterface.get_params(model, gen_empty_fingerprint(), [], False, False, False)
    self.assertTrue(cp.flags & HyundaiFlags.CANFD)
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    state.update(parsers)
    bus = CanBus(cp).ECAN
    packer = CANPacker(DBC[model][Bus.pt])
    parsers[Bus.pt].update((1_000_000_000, [packer.make_can_msg("BLINKERS", bus, values)]))
    if invalid_selector is not None:
      parsers[Bus.pt].vl["BLINKERS"]["USE_ALT_LAMP"] = invalid_selector
    out = state.update(parsers)
    return out.leftBlinker, out.rightBlinker

  def test_selector_selects_packed_lamps_on_existing_canfd_cars(self):
    for model in (CAR.KIA_EV6, CAR.HYUNDAI_IONIQ_6):
      for selector in (0, 1):
        for left, right in ((0, 0), (1, 0), (0, 1), (1, 1)):
          with self.subTest(model=model, selector=selector, left=left, right=right):
            values = {"USE_ALT_LAMP": selector, "LEFT_LAMP": left, "RIGHT_LAMP": right,
                      "LEFT_LAMP_ALT": 1 - left, "RIGHT_LAMP_ALT": 1 - right}
            expected = (bool(left), bool(right)) if selector == 0 else (not left, not right)
            self.assertEqual(self.read_lamps(model, values), expected)

  def test_ccnc_and_kona_keep_alternate_lamps_without_selector(self):
    for model in (CAR.HYUNDAI_KONA_EV_2ND_GEN, CAR.KIA_SPORTAGE_2026):
      for selector in (0, 1):
        with self.subTest(model=model, selector=selector):
          self.assertEqual(self.read_lamps(model, {"USE_ALT_LAMP": selector,
                           "LEFT_LAMP": 0, "RIGHT_LAMP": 1,
                           "LEFT_LAMP_ALT": 1, "RIGHT_LAMP_ALT": 0}), (True, False))

  def test_selector_change_retains_existing_lamp_hold_and_release(self):
    cp = CarInterface.get_params(CAR.KIA_EV6, gen_empty_fingerprint(), [], False, False, False)
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    state.update(parsers)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    bus = CanBus(cp).ECAN
    for frame in range(52):
      values = {"USE_ALT_LAMP": 1 if frame == 0 else 0, "LEFT_LAMP_ALT": int(frame == 0)}
      parsers[Bus.pt].update(((frame + 1) * 10_000_000, [packer.make_can_msg("BLINKERS", bus, values)]))
      out = state.update(parsers)
      self.assertEqual(out.leftBlinker, frame < 50, frame)
      self.assertFalse(out.rightBlinker)

  def test_default_lamps_and_invalid_selector_keep_standard_defaults(self):
    for model in (CAR.KIA_EV6, CAR.HYUNDAI_IONIQ_6):
      with self.subTest(model=model):
        self.assertEqual(self.read_lamps(model, {}), (False, False))
        self.assertEqual(self.read_lamps(model, {"LEFT_LAMP": 1, "RIGHT_LAMP_ALT": 1},
                                        invalid_selector=2), (True, False))


if __name__ == "__main__":
  unittest.main()
