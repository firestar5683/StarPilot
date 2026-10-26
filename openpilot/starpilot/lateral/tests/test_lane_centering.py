"""Native model-message fixtures for the standalone curvature contribution."""
from dataclasses import replace
import math
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
import unittest
from unittest.mock import patch

from openpilot.cereal import messaging
from openpilot.selfdrive.controls.lib.drive_helpers import clip_curvature
from openpilot.starpilot.lateral.lane_centering import (ControlMode, LaneCenteringController, LaneCenteringInput,
                                                       LaneCenteringSettings, MAX_CORRECTION, STOCK_CORRECTION, raw_correction)


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
                              ControlMode.LATERAL_ONLY, True, LaneCenteringSettings(True, 0.0, 0.0, True, strength=1.5, max_correction=STOCK_CORRECTION, min_speed_mps=4.4704), 0.01)
  return replace(source, **updates)


def settled(controller, source, ticks=300):
  result = None
  for _ in range(ticks):
    result = controller.update(source)
  assert result is not None
  return result


class TestLaneCentering(unittest.TestCase):
  def test_boundary_geometry_updates_once_per_model_frame_and_reset(self):
    from openpilot.starpilot.lateral import lane_centering as module
    source = observation(model().as_reader(), settings=LaneCenteringSettings(True, e2e_authority=0., curve_adaptation=False))
    controller = LaneCenteringController()
    with patch.object(module, '_path_xy', wraps=module._path_xy) as evaluate:
      first = controller.update(source)
      second = controller.update(source)
      self.assertGreater(second.correction, first.correction)
      self.assertEqual(evaluate.call_count, 4)
      controller.update(replace(source, model_sample_id=2))
      self.assertEqual(evaluate.call_count, 8)
      controller.reset()
      controller.update(source)
      self.assertEqual(evaluate.call_count, 12)
      controller.update(replace(source, time_discontinuity=True))
      controller.update(source)
      self.assertEqual(evaluate.call_count, 16)

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
    # Isolate the filter from v4 versus legacy-helper deadband differences.
    source = replace(source, settings=replace(source.settings, response_tau=.4, single_deadband=.08))
    first = controller.update(source).correction
    second = controller.update(source).correction
    raw = raw_correction(source.model, 20.0, 0.0, 0.0)
    assert raw is not None
    expected_target = raw * 0.30 * 1.5
    self.assertAlmostEqual(first, expected_target * (1.0 - math.exp(-0.01 / 0.4)))
    self.assertAlmostEqual(second, expected_target * (1.0 - math.exp(-0.02 / 0.4)))
    self.assertGreater(second, first)

  def test_strength_increases_sublimit_correction_without_changing_default(self):
    source = observation(model(left=-1.6, right=2.0))  # Remains below cap with 2cm deadband and strength3.0.
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
      source = observation(shifted, settings=LaneCenteringSettings(True, e2e_authority=authority, strength=1.5))
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
    source = replace(source, settings=replace(source.settings, strength=1.0, response_tau=.4, single_deadband=.08))
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
    self.assertEqual(settled(LaneCenteringController(), observation(model(left=-1.79, right=1.81))).correction, 0.0)
    settings = LaneCenteringSettings(True, 0.3, 0.0)
    narrow = observation(model(left=-1.3, right=1.3), settings=settings)
    safe_limit = replace(narrow, settings=replace(settings, offset_m=0.2))
    self.assertAlmostEqual(settled(LaneCenteringController(), narrow).correction,
                           settled(LaneCenteringController(), safe_limit).correction)
    extreme = settled(LaneCenteringController(), observation(model(left=0.0, right=3.0)), ticks=400)
    self.assertAlmostEqual(extreme.correction, STOCK_CORRECTION, delta=1e-6)

  def test_doubled_cap_is_reachable_and_bounded_in_both_directions(self):
    self.assertAlmostEqual(MAX_CORRECTION, 0.0024)
    for sign in (-1, 1):
      for strength in (1.0, 1.5, 3.0):
        source = observation(model(left=-1.8 + sign * 1.5, right=1.8 + sign * 1.5),
                             speed_mps=5., settings=LaneCenteringSettings(True, strength=strength, e2e_authority=0., response_tau=0., response_min=0., max_correction=MAX_CORRECTION))
        result = LaneCenteringController().update(source)
        self.assertAlmostEqual(result.correction, sign * 0.0024)
        self.assertAlmostEqual(result.candidate_curvature, source.base_curvature + result.correction)

  def test_e2e_break_in_requires_confident_path(self):
    shifted = model(left=-1.0, right=2.6)
    no_e2e = settled(LaneCenteringController(), observation(shifted)).correction
    full_e2e = settled(LaneCenteringController(), observation(
      shifted, settings=replace(observation().settings, e2e_authority=1.0))).correction
    uncertain = settled(LaneCenteringController(), observation(
      model(left=-1.0, right=2.6, path_std=0.6), settings=replace(observation().settings, e2e_authority=1.0))).correction
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
          blocked = replace(source, speed_mps=source.settings.min_speed_mps - .1)
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
    fading = controller.update(replace(source, model=model(prob=0.09), model_sample_id=2))
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
    for bad_model in (model(prob=0.09), model(std=1.0), model(left=-0.5, right=0.5),
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


def single(*, missing_right=True, line=-0.9, edge=3.0, path=0.0):
  m = model(left=line if missing_right else -3.0, right=2.0 if missing_right else -line, path=path)
  m.laneLineProbs = [0., .95 if missing_right else .05, .05 if missing_right else .95, 0.]
  m.init('roadEdges', 2)
  for item, y in zip(m.roadEdges, (-3.0 if missing_right else -edge, edge if missing_right else 3.0), strict=True):
    item.x = XS
    item.y = [y] * len(XS)
  m.roadEdgeStds = [.1, .1]
  return m


class TestSingleBoundary(unittest.TestCase):
  def test_recorded_bd_missing_right_line_recovers_bounded_clearance(self):
    fixture = json.loads((Path(__file__).parent / 'fixtures/route_bd_single_boundary.json').read_text())
    m = messaging.new_message('modelV2').modelV2
    m.from_dict(fixture['model'])
    self.assertTrue(fixture['recordedCarControl']['latActive'])
    self.assertEqual(fixture['recordedFeedback']['requestedCorrection'], 0.)
    self.assertEqual(fixture['recordedFeedback']['reason'], 'unqualified_model')
    self.assertLess(m.laneLineProbs[2], .6)
    raw = raw_correction(m, fixture['speedMps'], 0., 0.)
    assert raw is not None
    self.assertGreater(raw, 0.)
    self.assertAlmostEqual(raw, fixture['expectedRaw'], places=12)
    result = settled(LaneCenteringController(), observation(m, speed_mps=fixture['speedMps']))
    self.assertLessEqual(abs(result.correction), MAX_CORRECTION)
    # At the exact earlier bookmark BOTH line probabilities are low and the
    # left-line std is .919 m. Preserve that refusal rather than invent a lane.
    refused = messaging.new_message('modelV2').modelV2
    refused.from_dict(fixture['firstBookmarkRefusal']['model'])
    self.assertIsNone(raw_correction(refused, 15.75, 0., 0.))

  def test_missing_either_line_recovers_clearance_without_centering_on_edge(self):
    for missing_right, sign in ((True, 1), (False, -1)):
      for edge in (2.5, 3.0):
        with self.subTest(missing_right=missing_right, edge=edge):
          m = single(missing_right=missing_right, edge=edge)
          raw = raw_correction(m, 20., 0., 0.)
          assert raw is not None
          self.assertAlmostEqual(raw, sign * 2. * (.2 - .08) / 400., places=8)
          result = settled(LaneCenteringController(), observation(m))
          self.assertEqual(result.reason, 'qualified')
          self.assertGreater(sign * result.correction, 0.)
          self.assertLessEqual(abs(result.correction), MAX_CORRECTION)

  def test_safe_model_path_is_retained_and_missing_line_geometry_is_unused(self):
    m = single(line=-1.5)
    self.assertEqual(raw_correction(m, 20., 0., 0.), 0.)
    m.laneLines[2].x = []
    m.laneLines[2].y = []
    self.assertEqual(raw_correction(m, 20., 0., 0.), 0.)

  def test_refuses_both_missing_and_unqualified_path_edge_or_corridor(self):
    for defect in ('both', 'path_std', 'edge_std', 'nan_edge', 'no_edge', 'crossed', 'wide', 'narrow',
                   'path_outside', 'near_crossing', 'missing_std', 'short_edge', 'bad_x', 'nan_prob'):
      with self.subTest(defect=defect):
        m = single()
        if defect == 'both':
          m.laneLineProbs = [0., .05, .05, 0.]
        elif defect == 'path_std':
          m.position.yStd = [.36] * len(XS)
        elif defect == 'edge_std':
          m.roadEdgeStds = [.1, .31]
        elif defect == 'nan_edge':
          m.roadEdges[1].y = [float('nan')] * len(XS)
        elif defect == 'no_edge':
          m.roadEdges = []
        elif defect == 'crossed':
          m.roadEdges[1].y = [-2.] * len(XS)
        elif defect == 'wide':
          m.roadEdges[1].y = [4.] * len(XS)
        elif defect == 'narrow':
          m.roadEdges[1].y = [1.] * len(XS)
        elif defect == 'path_outside':
          m.position.y = [-1.] * len(XS)
        elif defect == 'near_crossing':
          m.roadEdges[1].y = [-2. if x <= 10 else 3. for x in XS]
        elif defect == 'missing_std':
          m.position.yStd = []
        elif defect == 'short_edge':
          m.roadEdges[1].x = XS[:10]
          m.roadEdges[1].y = [3.] * 10
        elif defect == 'bad_x':
          m.roadEdges[1].x = list(reversed(XS))
        else:
          m.laneLineProbs = [0., .95, float('nan'), 0.]
        self.assertIsNone(raw_correction(m, 20., 0., 0.))

  def test_edge_acceptance_changes_only_on_new_model_frame(self):
    m = single()
    source = observation(m.as_reader())
    controller = LaneCenteringController()
    controller.update(source)
    self.assertEqual(controller.selected_mode, 2)
    m.roadEdgeStds = [1.01, 1.01]
    controller.update(source)
    self.assertEqual(controller.selected_mode, 2)
    controller.update(replace(source, model_sample_id=source.model_sample_id + 1))
    self.assertEqual(controller.selected_mode, 3)
    m.roadEdgeStds = [.1, .1]
    controller.update(replace(source, model_sample_id=source.model_sample_id + 2))
    self.assertEqual(controller.selected_mode, 2)

  def test_single_boundary_still_obeys_override_freshness_signal_and_axis(self):
    source = observation(single())
    for updates in ({'driver_override':True}, {'model_valid':False}, {'lateral_active':False},
                    {'time_discontinuity':True}):
      controller = LaneCenteringController()
      self.assertGreater(settled(controller, source).correction, 0.)
      self.assertEqual(controller.update(replace(source, **updates)).correction, 0.)
    controller = LaneCenteringController()
    prior = settled(controller, source).correction
    faded = controller.update(replace(source, turn_signal_active=True))
    self.assertEqual(faded.reason, 'signal_release')
    self.assertLess(faded.correction, prior)

