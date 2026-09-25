"""Source-timed Ioniq comfort hysteresis and native planner admission."""

import unittest

from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import messages
from openpilot.starpilot.longitudinal.tests.test_ioniq6_start import candidate
from openpilot.starpilot.longitudinal.throttle_gate import ModelThrottleGate


BASE_NS = 10_000_000_000
FRAME_NS = 50_000_000


class ModelThrottleGateTests(unittest.TestCase):
  def setUp(self):
    self.gate = ModelThrottleGate()

  def step(self, index, probability, *, speed=20.0, now_ns=None, stamp_ns=None, valid=True):
    stamp = BASE_NS + index * FRAME_NS if stamp_ns is None else stamp_ns
    return self.gate.step(probability, speed, low_speed_mps=2.5, model_ns=stamp,
                          now_ns=stamp + 10_000_000 if now_ns is None else now_ns, model_valid=valid)

  def test_confirmed_thresholds_and_low_speed_bypass(self):
    for frame in range(5):
      self.assertTrue(self.step(frame, 0.34))
    self.assertFalse(self.step(5, 0.34))
    self.assertFalse(self.step(6, 0.44))
    for frame in range(7, 12):
      self.assertFalse(self.step(frame, 0.46))
    self.assertTrue(self.step(12, 0.46))
    self.assertTrue(self.step(13, 0.34, speed=2.5))
    self.assertFalse(self.step(14, 0.34, speed=2.5, valid=False))
    self.assertTrue(self.step(15, 0.34, speed=2.5))

  def test_repeated_stale_future_and_gap_cannot_accumulate_hold(self):
    self.assertTrue(self.step(0, 0.34))
    self.assertFalse(self.step(0, 0.34))
    for _ in range(10):
      self.assertFalse(self.step(0, 0.9))
    self.assertFalse(self.step(1, 0.9, now_ns=BASE_NS + FRAME_NS - 1))
    self.assertFalse(self.step(2, 0.9, now_ns=BASE_NS + FRAME_NS * 2 + 251_000_000))
    self.assertFalse(self.step(8, 0.9))
    for frame in range(9, 14):
      self.assertFalse(self.step(frame, 0.9))
    self.assertTrue(self.step(14, 0.9))

  def test_unknown_probability_never_grants_and_reset_clears_epoch(self):
    self.assertFalse(self.step(0, float('nan')))
    self.assertFalse(self.step(0, 1.0))
    self.gate.reset()
    self.assertTrue(self.step(0, 1.0))

  def test_future_outlier_does_not_poison_valid_stream(self):
    self.assertTrue(self.step(0, 0.34))
    self.assertFalse(self.step(100, 0.34, now_ns=BASE_NS + 20_000_000))
    for frame in range(1, 6):
      self.assertFalse(self.step(frame, 0.9))
    self.assertTrue(self.step(6, 0.9))


class Frame(dict):
  def __init__(self, payloads):
    super().__init__(payloads)
    self.logMonoTime = {'modelV2': BASE_NS}
    self.valid = {'modelV2': True}
    self.alive = {'modelV2': True}


class NativePlannerThrottleTests(unittest.TestCase):
  def test_exact_ioniq_active_path_uses_source_hold_stock_keeps_one_frame(self):
    stock, tagged = candidate()
    now = [BASE_NS + 10_000_000]
    native = LongitudinalPlanner(stock, init_v=20.0, clock_ns=lambda: now[0])
    scoped = LongitudinalPlanner(tagged, init_v=20.0, clock_ns=lambda: now[0])
    native_sm = Frame(messages()[0])
    scoped_sm = Frame(messages()[0])
    for sm in (native_sm, scoped_sm):
      sm['carControl'].longActive = True
      sm['modelV2'].meta.disengagePredictions.gasPressProbs = [0.34] * 6
    for frame in range(6):
      stamp = BASE_NS + frame * FRAME_NS
      now[0] = stamp + 10_000_000
      for sm in (native_sm, scoped_sm):
        sm.logMonoTime['modelV2'] = stamp
      native.update(native_sm)
      scoped.update(scoped_sm)
      self.assertFalse(native.allow_throttle)
      self.assertEqual(scoped.allow_throttle, frame < 5)
      self.assertEqual(native.mpc.solution_status, 0)
      self.assertEqual(scoped.mpc.solution_status, 0)
    scoped.update(scoped_sm)
    self.assertFalse(scoped.allow_throttle)
    scoped_sm.logMonoTime['modelV2'] += FRAME_NS
    now[0] += FRAME_NS
    scoped_sm.valid['modelV2'] = False
    scoped.update(scoped_sm)
    self.assertFalse(scoped.allow_throttle)
    scoped_sm['carControl'].longActive = False
    scoped.update(scoped_sm)
    self.assertFalse(scoped.allow_throttle)
    scoped_sm['carState'].vEgo = 2.0
    scoped.update(scoped_sm)
    self.assertTrue(scoped.allow_throttle)

  def test_lead_candidate_keeps_native_mpc_priority(self):
    stock, tagged = candidate()
    now = [BASE_NS + 10_000_000]
    planners = (LongitudinalPlanner(stock, init_v=20.0, clock_ns=lambda: now[0]),
                LongitudinalPlanner(tagged, init_v=20.0, clock_ns=lambda: now[0]))
    streams = (Frame(messages(lead=True)[0]), Frame(messages(lead=True)[0]))
    for sm in streams:
      sm['carControl'].longActive = True
      sm['modelV2'].meta.disengagePredictions.gasPressProbs = [0.34] * 6
    for frame in range(6):
      stamp = BASE_NS + frame * FRAME_NS
      now[0] = stamp + 10_000_000
      for planner, sm in zip(planners, streams, strict=True):
        sm.logMonoTime['modelV2'] = stamp
        planner.update(sm)
        self.assertEqual(planner.mpc.solution_status, 0)
    self.assertEqual(planners[0].mpc.source, planners[1].mpc.source)
    self.assertNotEqual(str(planners[0].mpc.source), 'cruise')
    self.assertAlmostEqual(planners[0].output_a_target, planners[1].output_a_target)


if __name__ == '__main__':
  unittest.main()
