"""Pure source-policy vectors; accepted receipts are synthetic, not hardware evidence."""
from dataclasses import FrozenInstanceError
import math
import unittest

from opendbc.car.hyundai.canfd_lead import CANFDLeadObservation as Observation, select_lead

NOW = 1_000_000_000
FLOOR = 100_000_000


def selected(radar=None, camera=None, hud=False, now=NOW, floor=FLOOR):
  return select_lead(radar, camera, hud_visible=hud, observed_ns=now, epoch_floor_ns=floor)


class TestCANFDLead(unittest.TestCase):
  def test_precedence_minimum_distance_camera_and_hud_fallback(self):
    radar = Observation(True, 15., -2., NOW)
    camera = Observation(True, 10., 1., NOW)
    self.assertEqual(selected(radar, camera).distance, 15.)
    self.assertEqual(selected(Observation(True, .1, 2., NOW), camera).distance, 10.)
    self.assertEqual(selected(Observation(True, .1, 2., NOW)).distance, 20.)
    self.assertEqual(selected(hud=True).distance, 20.)
    self.assertFalse(selected().visible)
    self.assertFalse(selected(camera=Observation(True, .1, 0., NOW)).visible)
    self.assertGreater(selected(Observation(True, math.nextafter(.1, math.inf), 0., NOW)).distance, .1)

  def test_camera_age_future_epoch_and_nonfinite_boundaries(self):
    for age, visible in ((300_000_000, True), (300_000_001, False), (-1, False)):
      self.assertEqual(selected(camera=Observation(True, 10., 0., NOW-age)).visible, visible)
    for stamp in (0, FLOOR, FLOOR-1, NOW+1):
      self.assertFalse(selected(Observation(True, 10., 0., stamp)).visible)
      self.assertFalse(selected(camera=Observation(True, 10., 0., stamp)).visible)
    for value in (math.nan, math.inf, -math.inf):
      for observation in (Observation(True, value, 0., NOW), Observation(True, 10., value, NOW)):
        self.assertFalse(selected(observation).visible)
        self.assertFalse(selected(camera=observation).visible)
    self.assertFalse(selected(hud=True, floor=NOW).visible)
    self.assertFalse(selected(hud=True, floor=-1).visible)

  def test_clipping_stateless_recovery_and_immutable_values(self):
    observation = Observation(True, 300., -100., NOW)
    result = selected(observation)
    self.assertEqual((result.distance, result.relative_speed), (204.7, -16.4))
    self.assertEqual(selected(Observation(True, 10., 100., NOW)).relative_speed, 34.7)
    self.assertFalse(selected(camera=Observation(True, 10., 0., NOW-300_000_001)).visible)
    self.assertTrue(selected(camera=Observation(True, 10., 0., NOW)).visible)
    for instance in (observation, result):
      with self.assertRaises(FrozenInstanceError):
        instance.extra = 1
