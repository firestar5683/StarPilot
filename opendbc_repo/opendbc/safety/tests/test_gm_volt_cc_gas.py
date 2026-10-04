"""Volt CC driver gas SET exception retains the physical stock-cruise owner."""
import unittest

from opendbc.car.gm import gmcan
from opendbc.safety.tests import test_gm_volt_cc as baseline


class TestGmVoltCcGas(unittest.TestCase):
  setUp = baseline.TestGmVoltCc.setUp
  packet = staticmethod(baseline.TestGmVoltCc.packet)
  tx = baseline.TestGmVoltCc.tx

  def reset(self):
    baseline.TestGmVoltCc.reset(self)
    self.safety.set_timer(990_000)
    self.feed(counter=3, gas=False)
    self.safety.set_timer(1_000_000)

  def feed(self, counter=0, gas=True, stock_kph=54., speed=20., brake=False, regen=False, gear=4, manual=False, active=True, main=True):
    frames = baseline.TestGmVoltCc.frames(self, counter=counter, gas=gas, speed=speed, brake=brake)
    replacements = [self.packer.make_can_msg('ECMCruiseControl', 0, {'CruiseActive': active, 'CruiseSetSpeed': stock_kph}),
                    self.packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': main}),
                    self.packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': gear, 'ManualMode': manual}),
                    self.packer.make_can_msg('EBCMRegenPaddle', 0, {'RegenPaddle': 2 if regen else 0})]
    addresses = {frame[0] for frame in replacements}
    ordered = [frame for frame in frames if frame[0] not in addresses] + replacements
    for frame in sorted(ordered, key=lambda frame: frame[0] == 0x3D1):
      self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)))
    self.safety.safety_tick()

  def test_set_only_under_gas_retains_lateral_and_consumes_credit(self):
    self.reset()
    self.feed()
    self.assertEqual(self.safety.get_controls_allowed(), not self.release)
    self.assertFalse(self.tx(button=2))
    self.assertEqual(self.tx(button=3), not self.release)
    self.assertFalse(self.tx(button=3))
    steer = gmcan.create_steering_control(self.packer, 0, 1, 0, True)
    self.assertEqual(self.safety.safety_tx_hook(self.packet(steer)), not self.release)
    self.safety.set_timer(1_010_000)
    self.feed(counter=1, gas=False)
    self.assertEqual(self.safety.get_controls_allowed(), not self.release)
    for stamp, counter in ((1_100_000, 2), (1_190_000, 3), (1_220_000, 0)):
      self.safety.set_timer(stamp)
      self.feed(counter=counter, gas=False)
    self.assertEqual(self.tx(counter=1, button=2), not self.release)

  def test_gas_cadence_and_stock_speed_boundary(self):
    for elapsed, allowed in ((519999, False), (520000, True), (520001, True)):
      self.reset()
      self.feed()
      self.assertEqual(self.tx(button=3), not self.release)
      # Refresh sequential physical slots so cadence is the only missing condition.
      for step in range(1, 6):
        self.safety.set_timer(1_000_000 + step * 90000)
        self.feed(counter=step % 4)
      self.safety.set_timer(1_000_000 + elapsed)
      self.feed(counter=2)
      self.assertEqual(self.tx(counter=3, button=3), allowed and not self.release)
    for stock_kph, speed in ((72., 20.), (71.9375, 20.), (72.0625, 20.), (54., 10.)):
      self.reset()
      self.feed(stock_kph=stock_kph, speed=speed)
      wheels = self.packer.make_can_msg('EBCMWheelSpdRear', 0, {'RLWheelSpd': speed * 3.6, 'RRWheelSpd': speed * 3.6, 'RLWheelDir': 1, 'RRWheelDir': 1})[1]
      raw_sum = int.from_bytes(wheels[:2], 'big') + int.from_bytes(wheels[2:4], 'big')
      source_boundary = round(stock_kph * 16) * 1250 < raw_sum * 311 and speed >= 24 * .44704
      self.assertEqual(self.tx(button=3), source_boundary and not self.release)

  def test_inactive_override_stale_and_tuple_negatives(self):
    for condition in ({'brake': True}, {'regen': True}, {'gear': 0}, {'active': False}, {'main': False}):
      self.reset()
      self.feed(**condition)
      self.assertFalse(self.tx(button=3))
    self.reset()
    self.feed()
    self.safety.set_controls_allowed(False)
    self.assertFalse(self.tx(button=3))
    self.reset()
    self.feed()
    good = gmcan.create_buttons(self.packer, 0, 1, 3)
    for index in range(7):
      data = bytearray(good[1])
      data[index] ^= 1
      self.assertFalse(self.safety.safety_tx_hook(self.packet((good[0], bytes(data), 0))))
    self.assertFalse(self.safety.safety_tx_hook(self.packet((good[0], good[1], 2))))
    self.assertFalse(self.safety.safety_tx_hook(self.packet((good[0], good[1][:-1], 0))))
    self.safety.set_timer(1_101_000)
    self.assertFalse(self.tx(button=3))
    self.reset()
    self.feed()
    self.safety.set_timer(1_010_000)
    self.feed(counter=2)
    self.assertFalse(self.tx(counter=3, button=3))

  def test_brake_release_requires_existing_pcm_rearm(self):
    self.reset()
    self.feed()
    self.safety.set_timer(1_005_000)
    self.feed(brake=True, counter=1)
    self.safety.set_timer(1_010_000)
    self.feed(counter=2)
    self.assertFalse(self.safety.get_controls_allowed())
    self.assertFalse(self.tx(counter=3, button=3))
    self.safety.set_timer(1_020_000)
    self.feed(counter=3, active=False)
    self.safety.set_timer(1_030_000)
    self.feed(counter=0, active=True)
    self.assertEqual(self.safety.get_controls_allowed(), not self.release)
    self.assertFalse(self.tx(counter=1, button=3))
    self.safety.set_timer(1_040_000)
    self.feed(counter=1)
    self.assertEqual(self.tx(counter=2, button=3), not self.release)

  def test_exact_forward_gears_and_current_credit(self):
    for gear in (4, 6):
      self.reset()
      self.feed(gear=gear, gas=False)
      self.assertEqual(self.tx(button=2), not self.release)
      self.safety.set_timer(1_210_000)
      self.feed(counter=0, gear=6 if gear == 4 else 4, gas=False)
      self.assertEqual(self.safety.get_controls_allowed(), not self.release)
      self.assertFalse(self.tx(counter=1, button=2))
      self.safety.set_timer(1_220_000)
      self.feed(counter=1, gear=6 if gear == 4 else 4, gas=False)
      self.assertEqual(self.tx(counter=2, button=2), not self.release)
    for gear, manual in ((0, False), (1, False), (2, False), (3, False), (7, False), (4, True), (6, True)):
      self.reset()
      self.feed(gear=gear, manual=manual)
      self.assertFalse(self.tx(button=3))
      steer = gmcan.create_steering_control(self.packer, 0, 1, 0, True)
      self.assertFalse(self.safety.safety_tx_hook(self.packet(steer)))
