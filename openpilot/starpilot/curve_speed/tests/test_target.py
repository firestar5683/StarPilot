import math
from types import SimpleNamespace
import unittest
from openpilot.starpilot.curve_speed.learning import LearnedCurve
from openpilot.starpilot.curve_speed.target import CurveProfile, Envelope, TargetFilter, evaluate


class TestTarget(unittest.TestCase):
  def test_full_profile_selects_binding_apex_and_distance(self):
    result = evaluate(CurveProfile((0.0, 0.02, 0.01), (0.0, 150.0, 200.0), 100), LearnedCurve(), 30.0)
    assert result.binding_distance_m == 150
    self.assertAlmostEqual(result.speed_mps, math.sqrt((25 * 0.44704) ** 2 + 0.6 * 150))
    assert evaluate(CurveProfile((0.02,), (2000.0,), 100), LearnedCurve(), 30.0) == Envelope(30.0, 0.0)

  def test_farfield_correction_and_weather_only_lower_envelope(self):
    curve = LearnedCurve()
    profile = CurveProfile((0.004,), (30.0,), 100)
    corrected = evaluate(profile, curve, 35.0)
    expected = math.sqrt(curve.comfort(0.004 * 1.23) / (0.004 * 1.23) + 0.6 * 30)
    self.assertAlmostEqual(corrected.speed_mps, expected)
    assert evaluate(profile, curve, 35.0, weather_reduction=0.3).speed_mps < corrected.speed_mps
    assert evaluate(CurveProfile((-0.004,), (30.0,), 100), curve, 35.0) == corrected

  def test_invalid_profile_rejected_before_arithmetic(self):
    for curvatures, distances in [
      ((), ()),
      ((0.1,), ()),
      ((math.nan,), (0.0,)),
      ((0.1,), (-1.0,)),
      ((0.1,), (math.inf,)),
      ((0.1, 0.2), (1.0, 0.0)),
      ((0.1,) * 130, (0.0,) * 130),
    ]:
      with self.subTest(curvatures=curvatures, distances=distances):
        with self.assertRaises(ValueError):
          CurveProfile(curvatures, distances, 100)

  def test_model_extraction_checks_whole_profile_and_low_speed(self):
    model = SimpleNamespace(
      orientationRate=SimpleNamespace(z=[0.3, -0.3, 0.3]), velocity=SimpleNamespace(x=[0.0, 10.0, 2.99]), position=SimpleNamespace(x=[0.0, 10.0, 20.0])
    )
    profile = CurveProfile.from_model(model, 100)
    assert profile == CurveProfile((0.0, 0.03, 0.0), (0.0, 10.0, 20.0), 100)
    model.velocity.x[1] = math.inf
    assert CurveProfile.from_model(model, 100) is None

  def test_seed_rate_limits_and_exit_recovery(self):
    target = TargetFilter()
    previous = 32.0
    for _ in range(150):
      current = target.step(Envelope(15.0, 20.0), ego_mps=30.0, cruise_mps=35.0, dt=0.05)
      assert 0 <= previous - current <= 2.5 * 0.05 + 1e-12
      previous = current
    assert current < 15.1
    released = target.step(Envelope(35.0, 0.0), ego_mps=15.0, cruise_mps=35.0, dt=0.05)
    self.assertAlmostEqual(released - current, 3.0 * 0.05)

  def test_model_origin_roundoff_is_normalized_without_relaxing_future_geometry(self):
    model = SimpleNamespace(orientationRate=SimpleNamespace(z=[0.1, 0.2, 0.3]),
                            velocity=SimpleNamespace(x=[10.0, 10.0, 10.0]),
                            position=SimpleNamespace(x=[-6.64888977208733e-11, 10.0, 20.0]))
    profile = CurveProfile.from_model(model, 100)
    self.assertEqual(profile.distances, (0.0, 10.0, 20.0))
    self.assertLess(model.position.x[0], 0.0)
    for distances in ([-1.0001e-6, 10.0, 20.0], [0.0, -1e-11, 20.0], [-1e-11, 10.0, 9.0]):
      with self.subTest(distances=distances):
        model.position.x = distances
        self.assertIsNone(CurveProfile.from_model(model, 100))

  def test_driver_reduction_is_immediate_ceiling_and_clock_gap_resets(self):
    target = TargetFilter()
    target.step(Envelope(35.0, 0.0), ego_mps=30.0, cruise_mps=35.0, dt=0.05)
    assert target.step(Envelope(15.0, 0.0), ego_mps=30.0, cruise_mps=15.0, dt=0.05) == 15.0
    with self.assertRaises(ValueError):
      target.step(Envelope(15.0, 0.0), ego_mps=30.0, cruise_mps=35.0, dt=1.0)
    assert target.target is None

  def test_unknown_weather_cannot_enter_envelope(self):
    for weather in [-0.1, 1.1, math.nan, True]:
      with self.subTest(weather=weather):
        with self.assertRaises(ValueError):
          evaluate(CurveProfile((0.01,), (0.0,), 100), LearnedCurve(), 30.0, weather_reduction=weather)
