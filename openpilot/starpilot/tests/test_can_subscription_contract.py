"""CAN subscription migration contracts using the actual upstream Python parser.

These synthetic messages test required/optional freshness semantics only. They
do not qualify a vehicle, checksum algorithm, native safety mode or CAN hardware.
"""

import math
import unittest

from opendbc.can import CANPacker, CANParser


class TestCanSubscriptionContract(unittest.TestCase):
  REQUIRED = "ESP_B"
  OPTIONAL = "DI_torque1"
  START_NS = 1_000_000_000
  PERIOD_NS = 20_000_000

  def parser(self, optional_frequency):
    return CANParser("tesla_can", [(self.REQUIRED, 50), (self.OPTIONAL, optional_frequency)], 0)

  def schedule(self, parser, first_frame, count, names):
    packer = CANPacker("tesla_can")
    validity = []
    for frame in range(first_frame, first_frame + count):
      now_ns = self.START_NS + frame * self.PERIOD_NS
      parser.update([(now_ns, [packer.make_can_msg(name, 0, {}) for name in names])])
      # The parser currently debounces on property reads, so read once per frame.
      validity.append(parser.can_valid)
    return validity

  def timestamps(self, parser, name):
    self.assertTrue(parser.ts_nanos[name], "fixture message must have actual signals")
    return set(parser.ts_nanos[name].values())

  def test_missing_optional_message_does_not_invalidate_required_traffic(self):
    parser = self.parser(math.nan)
    self.assertTrue(all(self.schedule(parser, 0, 60, [self.REQUIRED])))
    self.assertEqual(self.timestamps(parser, self.REQUIRED), {self.START_NS + 59 * self.PERIOD_NS})
    # Aggregate CAN validity must never be interpreted as optional signal freshness.
    self.assertEqual(self.timestamps(parser, self.OPTIONAL), {0})

  def test_optional_signal_retains_old_timestamp_after_it_stops(self):
    parser = self.parser(math.nan)
    self.assertTrue(all(self.schedule(parser, 0, 60, [self.REQUIRED, self.OPTIONAL])))
    optional_last_seen = self.START_NS + 59 * self.PERIOD_NS
    self.assertEqual(self.timestamps(parser, self.OPTIONAL), {optional_last_seen})
    self.assertTrue(all(self.schedule(parser, 60, 60, [self.REQUIRED])))
    self.assertEqual(self.timestamps(parser, self.OPTIONAL), {optional_last_seen})
    self.assertEqual(self.timestamps(parser, self.REQUIRED), {self.START_NS + 119 * self.PERIOD_NS})

  def test_optional_traffic_does_not_hide_loss_of_required_message(self):
    parser = self.parser(math.nan)
    self.assertTrue(all(self.schedule(parser, 0, 60, [self.REQUIRED, self.OPTIONAL])))
    after_loss = self.schedule(parser, 60, 60, [self.OPTIONAL])
    self.assertFalse(any(after_loss[-10:]))
    self.assertEqual(self.timestamps(parser, self.REQUIRED), {self.START_NS + 59 * self.PERIOD_NS})
    self.assertEqual(self.timestamps(parser, self.OPTIONAL), {self.START_NS + 119 * self.PERIOD_NS})

  def test_zero_frequency_is_required_and_learns_received_frequency(self):
    parser = self.parser(0)
    self.assertFalse(any(self.schedule(parser, 0, 60, [self.REQUIRED])))
    self.assertEqual(self.timestamps(parser, self.OPTIONAL), {0})
    # Real packets restore validity; zero is not an optional-message declaration.
    self.assertTrue(all(self.schedule(parser, 60, 60, [self.REQUIRED, self.OPTIONAL])))
    after_loss = self.schedule(parser, 120, 60, [self.REQUIRED])
    self.assertFalse(any(after_loss[-10:]))
    self.assertEqual(self.timestamps(parser, self.OPTIONAL), {self.START_NS + 119 * self.PERIOD_NS})


if __name__ == "__main__":
  unittest.main()
