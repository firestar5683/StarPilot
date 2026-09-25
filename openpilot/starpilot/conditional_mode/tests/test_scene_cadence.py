"""Scene sampling retains bounded publisher freshness across one planner tick."""
import unittest

from openpilot.starpilot.conditional_mode.projection import SceneProjector, _fresh
from openpilot.starpilot.conditional_mode.tests.test_projection import BOOT, CP, MONO, FakeSubMaster, serialized_scene


class TestSceneCadence(unittest.TestCase):
  def test_fast_publisher_ages_retain_actual_scene_authority(self):
    for age_ns in (22_472_000, 27_290_000, 23_594_000, 27_557_000, 26_571_000, 26_638_000):
      with self.subTest(age_ns=age_ns):
        now = MONO + 200_000_000
        sm = FakeSubMaster(serialized_scene(stamp=BOOT + 200_000_000, lead_present=False), now - 1_000_000)
        projector = SceneProjector()
        projector.project(sm, CP, now_mono_ns=MONO, now_boot_ns=BOOT, sample_skew_ns=1000)
        sm.logMonoTime['carControl'] = now - age_ns
        sm.recv_time['carControl'] = (now - 2_000_000) / 1e9
        result = projector.project(sm, CP, now_mono_ns=now, now_boot_ns=BOOT + 200_000_000,
                                   sample_skew_ns=1000, safe_mode=False)
        self.assertIsNotNone(result.authority)
        self.assertTrue(result.authority.long_active)
        self.assertTrue(result.authority.driving_enabled)

  def test_fast_publisher_retains_both_clock_and_transport_bounds(self):
    now = MONO + 200_000_000
    sm = FakeSubMaster(serialized_scene(), now - 50_000_000)
    self.assertTrue(_fresh(sm, 'carControl', now, MONO))
    for field in ('logMonoTime', 'recv_time'):
      values = getattr(sm, field)
      good = values['carControl']
      values['carControl'] = now - 50_000_001 if field == 'logMonoTime' else (now - 50_000_001) / 1e9
      self.assertFalse(_fresh(sm, 'carControl', now, MONO))
      values['carControl'] = good
    for field in ('seen', 'alive', 'valid'):
      values = getattr(sm, field)
      values['carControl'] = False
      self.assertFalse(_fresh(sm, 'carControl', now, MONO))
      values['carControl'] = True
    self.assertFalse(_fresh(sm, 'carControl', now, now - 50_000_000))
    sm.logMonoTime['carControl'] = now + 1
    self.assertFalse(_fresh(sm, 'carControl', now, MONO))

  def test_model_publisher_keeps_existing_hundred_ms_bound(self):
    now = MONO + 200_000_000
    sm = FakeSubMaster(serialized_scene(), now - 100_000_000)
    self.assertTrue(_fresh(sm, 'modelV2', now, MONO))
    sm.logMonoTime['modelV2'] -= 1
    self.assertFalse(_fresh(sm, 'modelV2', now, MONO))
    sm.logMonoTime['modelV2'] += 1
    sm.recv_time['modelV2'] = (now - 100_000_001) / 1e9
    self.assertFalse(_fresh(sm, 'modelV2', now, MONO))
