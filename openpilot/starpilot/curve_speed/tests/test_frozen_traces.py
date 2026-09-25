import json
from pathlib import Path
import unittest

from openpilot.starpilot.curve_speed.learning import LearnedCurve
from openpilot.starpilot.curve_speed.target import CurveProfile, TargetFilter, evaluate


class TestFrozenTraces(unittest.TestCase):
  def test_saved_learning_weather_and_curve_exit(self):
    fixture = json.loads(Path(__file__).with_name('frozen_traces.json').read_text())
    for case in fixture['cases']:
      with self.subTest(case=case['name']):
        loaded = LearnedCurve.load(case['data'])
        self.assertTrue(loaded.valid)
        curve, target = loaded.curve, TargetFilter()
        for curvature, expected in zip((0.001, 0.005, 0.02), case['comfort'], strict=True):
          self.assertAlmostEqual(curve.comfort(curvature), expected, places=12)
        checkpoints = {item['frame']: item for item in case['steps']}
        for frame in range(case['frames']):
          curvatures = case['curvatures'] if frame < case['release_frame'] else [0.0] * len(case['curvatures'])
          profile = CurveProfile(tuple(curvatures), tuple(case['distances']), (frame + 1) * 50_000_000)
          envelope = evaluate(profile, curve, case['cruise_mps'], weather_reduction=case['weather_reduction'])
          actual = target.step(envelope, ego_mps=case['ego_mps'], cruise_mps=case['cruise_mps'], dt=0.05)
          if frame in checkpoints:
            self.assertAlmostEqual(actual, checkpoints[frame]['target'], places=12)
            self.assertAlmostEqual(envelope.binding_distance_m, checkpoints[frame]['distance'], places=12)
