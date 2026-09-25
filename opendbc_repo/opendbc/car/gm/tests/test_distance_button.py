import unittest

from opendbc.can import CANPacker
from opendbc.car.gm.distance_button import GMDistanceButtons, SOURCE_MAX_GAP_NS


class TestDistanceSource(unittest.TestCase):
  def setUp(self):
    self.packer = CANPacker('gm_global_a_powertrain_generated')

  def packet(self, stamp, held, bus=0):
    return stamp, [self.packer.make_can_msg('ASCMSteeringButton', bus, {'DistanceButton': int(held)})]

  def test_dbc_distance_oracle_and_order(self):
    source = GMDistanceButtons()
    observed = source.update([self.packet(1_000_000_000, False), self.packet(1_030_000_000, True),
                              self.packet(1_060_000_000, False)])
    self.assertTrue(observed.valid)
    self.assertEqual([(s.held, s.source_boot_ns) for s in observed.samples],
                     [(False, 1_000_000_000), (True, 1_030_000_000), (False, 1_060_000_000)])
    cached = source.update([(1_070_000_000, [])])
    self.assertTrue(cached.valid)
    self.assertEqual(cached.samples, ())
    self.assertFalse(source.update([(1_060_000_000 + SOURCE_MAX_GAP_NS + 1, [])]).valid)

  def test_wrong_bus_size_duplicate_and_epoch(self):
    for bad in (self.packet(1_030_000_000, True, 2),
                (1_030_000_000, [(0x1E1, bytes(8), 0)]),
                self.packet(1_000_000_000, True),
                self.packet(999_999_999, True)):
      source = GMDistanceButtons()
      source.update([self.packet(1_000_000_000, False)])
      observed = source.update([bad])
      self.assertEqual(observed.samples, ())
      if bad[1][0][2] == 2:
        self.assertTrue(observed.valid)  # Wrong bus supplies no new heartbeat.
      else:
        self.assertFalse(observed.valid)
        self.assertGreater(observed.source_epoch, 0)
      self.assertFalse(source.update([]).valid)
