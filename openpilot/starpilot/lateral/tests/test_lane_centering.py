"""Native model-message fixtures for the standalone curvature contribution."""
from dataclasses import replace
import math
from types import SimpleNamespace
from typing import Any, cast
import unittest
from unittest.mock import patch

from openpilot.cereal import messaging
from openpilot.selfdrive.controls.lib.drive_helpers import clip_curvature
from openpilot.starpilot.lateral.lane_centering import (ControlMode, LaneCenteringController, LaneCenteringInput,
                                                       LaneCenteringSettings, MAX_CORRECTION, raw_correction)


XS = [float(i) for i in range(51)]


def model(*, left=-1.5, right=2.1, path=0.0, path_std=0.1, prob=0.9, std=0.1):
  message = messaging.new_message("modelV2")
  m = message.modelV2
  m.init("laneLines", 4)
  for line, y in zip(m.laneLines, (0.0, left, right, 0.0), strict=True):
    line.x = XS
    line.y = [y] * len(XS)
  m.laneLineProbs = [0.0, prob, prob, 0.0]
  m.laneLineStds = [0.0, std, std, 0.0]
  m.position.x = XS
  m.position.y = [path] * len(XS)
  m.position.yStd = [path_std] * len(XS)
  return m


def observation(m=None, **updates):
  source = LaneCenteringInput(m if m is not None else model(), 1, True, 0.0002, 20.0,
                              ControlMode.LATERAL_ONLY, True, LaneCenteringSettings(True, 0.0, 0.0, True), 0.01)
  return replace(source, **updates)


def settled(controller, source, ticks=300):
  result = None
  for _ in range(ticks):
    result = controller.update(source)
  assert result is not None
  return result


class TestLaneCentering(unittest.TestCase):
  def test_reader_cache_detects_mutation_samples_and_reset(self):
    from openpilot.starpilot.lateral import lane_centering as module
    builder = model()
    reader = builder.as_reader()
    source = observation(reader)
    controller = LaneCenteringController()
    with patch.object(module, '_path_xy', wraps=module._path_xy) as evaluate:
      first = controller.update(source)
      second = controller.update(source)
      self.assertGreater(second.correction, first.correction)
      self.assertEqual(evaluate.call_count, 4)
      builder.laneLines[2].y = [2.5] * len(XS)
      controller.update(source)
      self.assertEqual(evaluate.call_count, 8)
      builder.laneLineProbs = [0., .1, .1, 0.]
      self.assertEqual(controller.update(source).reason, 'unqualified_model')
      self.assertEqual(evaluate.call_count, 12)
      controller.update(replace(source, model_sample_id=0))
      self.assertEqual(evaluate.call_count, 16)
      controller.update(replace(source, model=reader.as_builder().as_reader()))
      self.assertEqual(evaluate.call_count, 20)
      controller.reset()
      controller.update(source)
      self.assertEqual(evaluate.call_count, 24)
      controller.update(replace(source, time_discontinuity=True))
      controller.update(source)
      self.assertEqual(evaluate.call_count, 28)

  def test_explicit_axis_authority(self):
    for mode, allowed in ((ControlMode.OFF, False), (ControlMode.LATERAL_ONLY, True),
                          (ControlMode.LONGITUDINAL_ONLY, False), (ControlMode.COMBINED, True)):
      with self.subTest(mode=mode):
        result = LaneCenteringController().update(observation(mode=mode))
        self.assertEqual(result.correction > 0.0, allowed)
        assert result.candidate_curvature is not None
        self.assertAlmostEqual(result.candidate_curvature, 0.0002 + result.correction)

  def test_held_model_sample_advances_filter_as_in_frozen_controller(self):
    controller = LaneCenteringController()
    source = observation()
    first = controller.update(source).correction
    second = controller.update(source).correction
    raw = raw_correction(source.model, 20.0, 0.0, 0.0)
    assert raw is not None
    expected_target = raw * 0.30 * 1.5
    self.assertAlmostEqual(first, expected_target * (1.0 - math.exp(-0.01 / 0.4)))
    self.assertAlmostEqual(second, expected_target * (1.0 - math.exp(-0.02 / 0.4)))
    self.assertGreater(second, first)

  def test_strength_increases_sublimit_correction_without_changing_default(self):
    source = observation()
    standard, explicit, stronger = LaneCenteringController(), LaneCenteringController(), LaneCenteringController()
    for _ in range(100):
      before = standard.update(source)
      same = explicit.update(replace(source, settings=replace(source.settings, strength=1.5)))
      boosted = stronger.update(replace(source, settings=replace(source.settings, strength=3.0)))
      self.assertEqual(before, same)
      self.assertAlmostEqual(boosted.correction, before.correction * 2, delta=1e-15)
      self.assertLess(abs(boosted.correction), MAX_CORRECTION)

  def test_strength_preserves_absolute_filter_and_axis_bounds(self):
    for strength in (0.5, 1.5, 3.0):
      controller = LaneCenteringController()
      source = observation(model(left=-0.3, right=3.3), settings=LaneCenteringSettings(True, strength=strength))
      previous = 0.0
      for index in range(200):
        source = replace(source, model=model(left=-0.3, right=3.3) if index < 100 else model(left=-3.3, right=0.3))
        correction = controller.update(source).correction
        self.assertLessEqual(abs(correction), MAX_CORRECTION)
        self.assertLessEqual(abs(correction - previous), 2 * MAX_CORRECTION * (1 - math.exp(-0.01 / 0.4)) + 1e-15)
        previous = correction
      self.assertEqual(controller.update(replace(source, lateral_active=False)).correction, 0)
      self.assertEqual(controller.update(replace(source, time_discontinuity=True)).correction, 0)
    for invalid in (True, float("nan"), 0.49, 3.001):
      self.assertEqual(LaneCenteringController().update(replace(observation(), settings=LaneCenteringSettings(True, strength=invalid))).reason,
                       "invalid_input")

  def test_stronger_centering_remains_bounded_with_lane_uncertainty_and_sign_changes(self):
    for speed in (5., 35.):
      controller = LaneCenteringController()
      previous = 0.
      for index in range(120):
        dt = (.01, .02, .05)[index % 3]
        displacement = (.079, .081, .159, .161)[index % 4] * (1 if index < 60 else -1)
        source = observation(model(left=-1.8 + displacement, right=1.8 + displacement, std=.29999998211860657),
                             speed_mps=speed, elapsed_seconds=dt,
                             settings=LaneCenteringSettings(True, e2e_authority=0., strength=3.0))
        result = controller.update(source)
        self.assertEqual(result.reason, "qualified")
        self.assertLessEqual(abs(result.correction), MAX_CORRECTION)
        self.assertLessEqual(abs(result.correction - previous),
                             2 * MAX_CORRECTION * (1 - math.exp(-dt / .4)) + 1e-15)
        previous = result.correction
      self.assertEqual(controller.update(replace(source, driver_override=True)).correction, 0.)

  def test_strength_does_not_replace_model_path_authority(self):
    shifted = model(path=0.5)
    for authority in (0.0, 0.5, 1.0):
      source = observation(shifted, settings=LaneCenteringSettings(True, e2e_authority=authority))
      normal = settled(LaneCenteringController(), source).correction
      stronger = settled(LaneCenteringController(), replace(source, settings=replace(source.settings, strength=3.0))).correction
      self.assertAlmostEqual(stronger, normal * 2, delta=1e-15)

  def test_native_builder_trace_matches_frozen_source(self):
    # Frozen controller at 678af783; native modelV2, ten held 0.01 s ticks.
    expected = (8.147727264677505e-06, 1.6094286426420937e-05, 2.3844644343388891e-05,
                3.1403645241574984e-05, 3.8776013742606983e-05, 4.5966357816788907e-05,
                5.2979171663232737e-05, 5.9818838518878981e-05, 6.6489633398162377e-05,
                7.2995725765035352e-05)
    controller = LaneCenteringController()
    source = observation()
    source = replace(source, settings=replace(source.settings, strength=1.0))
    for reference in expected:
      self.assertAlmostEqual(controller.update(source).correction, reference, delta=1e-15)

  def test_filter_elapsed_time_matches_repeated_frozen_10ms_ticks(self):
    source = observation()
    ten_ms, twenty_ms = LaneCenteringController(), LaneCenteringController()
    for _ in range(10):
      result_ten = ten_ms.update(source)
    for _ in range(5):
      result_twenty = twenty_ms.update(replace(source, elapsed_seconds=0.02))
    self.assertAlmostEqual(result_ten.correction, result_twenty.correction, delta=1e-15)

  def test_candidate_passes_through_existing_curvature_limiter(self):
    result = settled(LaneCenteringController(), observation())
    self.assertIsNotNone(result.candidate_curvature)
    clipped, _ = clip_curvature(20.0, 0.0, result.candidate_curvature, 0.0)
    self.assertGreater(clipped, 0.0)
    self.assertLessEqual(clipped, result.candidate_curvature)

  def test_both_directions_offset_deadband_and_bounds(self):
    right = settled(LaneCenteringController(), observation(model())).correction
    left = settled(LaneCenteringController(), observation(model(left=-2.1, right=1.5))).correction
    self.assertGreater(right, 0.0)
    self.assertLess(left, 0.0)
    self.assertEqual(settled(LaneCenteringController(), observation(model(left=-1.75, right=1.85))).correction, 0.0)
    settings = LaneCenteringSettings(True, 0.3, 0.0)
    narrow = observation(model(left=-1.3, right=1.3), settings=settings)
    safe_limit = replace(narrow, settings=replace(settings, offset_m=0.2))
    self.assertAlmostEqual(settled(LaneCenteringController(), narrow).correction,
                           settled(LaneCenteringController(), safe_limit).correction)
    extreme = settled(LaneCenteringController(), observation(model(left=0.0, right=3.0)))
    self.assertAlmostEqual(extreme.correction, MAX_CORRECTION, delta=1e-6)

  def test_e2e_break_in_requires_confident_path(self):
    shifted = model(left=-1.0, right=2.6)
    no_e2e = settled(LaneCenteringController(), observation(shifted)).correction
    full_e2e = settled(LaneCenteringController(), observation(
      shifted, settings=LaneCenteringSettings(True, 0.0, 1.0))).correction
    uncertain = settled(LaneCenteringController(), observation(
      model(left=-1.0, right=2.6, path_std=0.6), settings=LaneCenteringSettings(True, 0.0, 1.0))).correction
    self.assertGreater(no_e2e, 0.0)
    self.assertAlmostEqual(full_e2e, 0.0)
    self.assertAlmostEqual(uncertain, no_e2e)

  def test_hard_gates_reset_and_reenable(self):
    for change in ("disabled", "override", "lane_change", "low_speed", "invalid_model", "long_only"):
      with self.subTest(change=change):
        controller = LaneCenteringController()
        source = observation()
        before = settled(controller, source).correction
        if change == "disabled":
          blocked = replace(source, settings=replace(source.settings, enabled=False))
        elif change == "override":
          blocked = replace(source, driver_override=True)
        elif change == "low_speed":
          blocked = replace(source, speed_mps=4.9)
        elif change == "invalid_model":
          blocked = replace(source, model_valid=False)
        elif change == "long_only":
          blocked = replace(source, mode=ControlMode.LONGITUDINAL_ONLY)
        else:
          changed_model = model()
          changed_model.meta.laneChangeState = "laneChangeStarting"
          blocked = replace(source, model=changed_model)
        self.assertGreater(before, 0.0)
        self.assertEqual(controller.update(blocked).correction, 0.0)
        reacquired = controller.update(source).correction
        self.assertGreater(reacquired, 0.0)
        self.assertLess(reacquired, before)

  def test_signal_and_confidence_release_then_reacquire(self):
    controller = LaneCenteringController()
    source = observation()
    before = settled(controller, source).correction
    signal = controller.update(replace(source, turn_signal_active=True))
    self.assertGreater(signal.correction, 0.0)
    self.assertLess(signal.correction, before)
    self.assertEqual(signal.reason, "signal_release")
    no_pause = replace(source, settings=replace(source.settings, pause_on_signal=False), turn_signal_active=True)
    self.assertGreater(controller.update(no_pause).correction, signal.correction)
    fading = controller.update(replace(source, model=model(prob=0.2)))
    self.assertGreater(fading.correction, 0.0)
    self.assertLess(fading.correction, before)
    self.assertEqual(fading.reason, "unqualified_model")
    self.assertGreater(controller.update(source).correction, fading.correction)

  def test_signal_pause_precedes_lane_change_as_in_frozen_source(self):
    controller = LaneCenteringController()
    source = observation()
    before = settled(controller, source).correction
    changed_model = model()
    changed_model.meta.laneChangeState = "laneChangeStarting"
    signaled = controller.update(replace(source, model=changed_model, turn_signal_active=True))
    self.assertEqual(signaled.reason, "signal_release")
    self.assertGreater(signaled.correction, 0.0)
    self.assertLess(signaled.correction, before)
    unsignaled = controller.update(replace(source, model=changed_model))
    self.assertEqual(unsignaled.reason, "lane_change")
    self.assertEqual(unsignaled.correction, 0.0)

  def test_unqualified_native_models_have_no_new_correction(self):
    for bad_model in (model(prob=0.2), model(std=0.4), model(left=-0.5, right=0.5),
                      model(path=float("nan"))):
      with self.subTest(model=bad_model):
        self.assertEqual(LaneCenteringController().update(observation(bad_model)).correction, 0.0)

  def test_missing_lookahead_and_nonmonotonic_path_rejected(self):
    short = model()
    short.laneLines[1].x = XS[:10]
    short.laneLines[1].y = [-1.5] * 10
    self.assertIsNone(raw_correction(short, 20.0, 0.0, 0.0))
    reversed_path = model()
    reversed_path.position.x = list(reversed(XS))
    self.assertIsNone(raw_correction(reversed_path, 20.0, 0.0, 0.0))

  def test_malformed_inputs_rejected_without_unsafe_candidate(self):
    for updates in ({"base_curvature": float("nan")}, {"speed_mps": float("inf")},
                    {"elapsed_seconds": float("nan")}, {"elapsed_seconds": -0.01},
                    {"base_curvature": True}, {"base_curvature": "0.0002"},
                    {"speed_mps": False}, {"speed_mps": "20"},
                    {"elapsed_seconds": True}, {"elapsed_seconds": "0.01"},
                    {"settings": LaneCenteringSettings(True, float("nan"))},
                    {"settings": LaneCenteringSettings(True, True)},
                    {"settings": LaneCenteringSettings(True, cast(Any, "0.2"))},
                    {"settings": LaneCenteringSettings(True, 0.0, cast(Any, "1.0"))},
                    {"time_discontinuity": "false"}):
      with self.subTest(updates=updates):
        controller = LaneCenteringController()
        settled(controller, observation())
        result = controller.update(observation(**updates))
        self.assertEqual(result.correction, 0.0)
        self.assertEqual(result.reason, "invalid_input")
        if "base_curvature" in updates:
          self.assertIsNone(result.candidate_curvature)

  def test_invalid_observation_type_is_inert(self):
    controller = LaneCenteringController()
    settled(controller, observation())
    result = controller.update(cast(Any, object()))
    self.assertEqual(result.reason, "invalid_input")
    self.assertIsNone(result.candidate_curvature)
    self.assertEqual(result.correction, 0.0)

  def test_numeric_strings_in_model_path_rejected(self):
    native_model = model()
    wrong_path = SimpleNamespace(x=[str(x) for x in XS], y=native_model.position.y,
                                 yStd=native_model.position.yStd)
    changed_model = SimpleNamespace(laneLines=native_model.laneLines, laneLineProbs=native_model.laneLineProbs,
                                    laneLineStds=native_model.laneLineStds, position=wrong_path)
    self.assertIsNone(raw_correction(changed_model, 20.0, 0.0, 0.0))

  def test_time_discontinuity_explicitly_resets(self):
    controller = LaneCenteringController()
    settled(controller, observation())
    result = controller.update(observation(elapsed_seconds=0.2, time_discontinuity=True))
    self.assertEqual(result.reason, "time_discontinuity")
    self.assertEqual(result.correction, 0.0)

  def test_elapsed_time_does_not_infer_a_discontinuity(self):
    controller = LaneCenteringController()
    result = controller.update(observation(elapsed_seconds=0.2))
    self.assertEqual(result.reason, "qualified")
    self.assertGreater(result.correction, 0.0)
