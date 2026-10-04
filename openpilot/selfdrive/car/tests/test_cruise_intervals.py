"""Saved cruise intervals alter only Card's non-PCM button increments."""

import tempfile
import unittest
from pathlib import Path

from opendbc.car.structs import car
from openpilot.common.params import Params
from openpilot.selfdrive.car.cruise import CRUISE_LONG_PRESS, IMPERIAL_INCREMENT, SlcPendingConfirmation, VCruiseHelper
from openpilot.starpilot.longitudinal.cruise_intervals import CruiseIntervals, read_cruise_intervals


Button = car.CarState.ButtonEvent.Type


def state(button=None, pressed=False, *, standstill=False):
  events = [] if button is None else [car.CarState.ButtonEvent(type=button, pressed=pressed)]
  return car.CarState(cruiseState={"available": True, "standstill": standstill}, buttonEvents=events)


class TestCruiseIntervals(unittest.TestCase):
  def setUp(self):
    temp = tempfile.TemporaryDirectory()
    self.addCleanup(temp.cleanup)
    self.params = Params(temp.name)

  def test_saved_children_ignore_retired_parent_and_keep_pcm_gate(self):
    self.params.put("CustomCruise", 5.0, block=True)
    self.params.put("CustomCruiseLong", 1.0, block=True)
    self.assertEqual(read_cruise_intervals(self.params, pcm_cruise=False), CruiseIntervals(5, 1))
    self.params.put_bool("QOLLongitudinal", True, block=True)
    self.assertEqual(read_cruise_intervals(self.params, pcm_cruise=False), CruiseIntervals(5, 1))
    self.assertEqual(read_cruise_intervals(self.params, pcm_cruise=True), CruiseIntervals())
    self.params.put_bool("QOLLongitudinal", False, block=True)
    self.assertEqual(read_cruise_intervals(self.params, pcm_cruise=False), CruiseIntervals(5, 1))

  def test_invalid_children_fall_back_without_enabling_other_features(self):
    self.params.put_bool("QOLLongitudinal", True, block=True)
    Path(self.params.get_param_path("CustomCruise")).write_bytes(b"nan")
    Path(self.params.get_param_path("CustomCruiseLong")).write_bytes(b"200")
    self.assertEqual(read_cruise_intervals(self.params, pcm_cruise=False), CruiseIntervals())

  def helper(self, *, metric=True, custom=True, initial=67.0, pcm=False):
    helper = VCruiseHelper(car.CarParams(pcmCruise=pcm))
    helper.v_cruise_kph = initial
    if custom:
      helper.intervals = CruiseIntervals(5, 1)
    return helper

  @staticmethod
  def step(helper, button=None, pressed=False, *, metric=True, pending=None, standstill=False):
    helper.update_v_cruise(state(button, pressed, standstill=standstill), True, metric, pending)

  def test_metric_short_and_held_accel_and_decel(self):
    for button, short_target, held_target in ((Button.accelCruise, 70, 71), (Button.decelCruise, 65, 64)):
      with self.subTest(button=button):
        helper = self.helper()
        self.step(helper, button, True)
        self.step(helper, button, False)
        self.assertEqual(helper.v_cruise_kph, short_target)
        self.assertEqual(helper.slc_cruise_change[2:], ("accel" if button == Button.accelCruise else "decel", False))
        self.step(helper, button, True)
        for _ in range(CRUISE_LONG_PRESS - 1):
          self.step(helper)
        self.step(helper)
        self.assertEqual(helper.v_cruise_kph, held_target)
        self.step(helper, button, False)
        self.assertEqual(helper.v_cruise_kph, held_target)
        self.assertIsNone(helper.slc_cruise_change)

  def test_imperial_display_unit_increments(self):
    helper = self.helper(initial=50 * IMPERIAL_INCREMENT)
    self.step(helper, Button.accelCruise, True, metric=False)
    self.step(helper, Button.accelCruise, False, metric=False)
    self.assertAlmostEqual(helper.v_cruise_kph, 55 * IMPERIAL_INCREMENT)
    self.step(helper, Button.accelCruise, True, metric=False)
    for _ in range(CRUISE_LONG_PRESS):
      self.step(helper, metric=False)
    self.assertAlmostEqual(helper.v_cruise_kph, 56 * IMPERIAL_INCREMENT)

  def test_default_pcm_standstill_and_slc_ownership(self):
    default = self.helper(custom=False, initial=60)
    self.step(default, Button.accelCruise, True)
    self.step(default, Button.accelCruise, False)
    self.assertEqual(default.v_cruise_kph, 61)

    pcm = self.helper(pcm=True, initial=60)
    self.step(pcm, Button.accelCruise, True)
    self.step(pcm, Button.accelCruise, False)
    self.assertEqual(pcm.v_cruise_kph, 255)
    for pressed in (True, False):
      pcm_state = state(Button.accelCruise, pressed)
      pcm_state.cruiseState.speed = 20.0
      pcm_state.cruiseState.speedCluster = 21.0
      pcm.update_v_cruise(pcm_state, True, True)
      self.assertEqual(pcm.v_cruise_kph, 72.0)
      self.assertAlmostEqual(pcm.v_cruise_cluster_kph, 75.6)

    standstill = self.helper(initial=60)
    self.step(standstill, Button.accelCruise, True, standstill=True)
    self.step(standstill, Button.accelCruise, False)
    self.assertEqual(standstill.v_cruise_kph, 60)

    slc = self.helper(initial=60)
    pending = SlcPendingConfirmation("s", 1, 1)
    self.step(slc, Button.accelCruise, True, pending=pending)
    self.step(slc, Button.accelCruise, False)
    self.assertEqual(slc.v_cruise_kph, 60)
    self.assertTrue(slc.slc_released_suppressed)
