import unittest
from types import SimpleNamespace

from cereal import car
from openpilot.common.constants import CV
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.car.redneck_cruise import (
  DECREASE_INACTIVE_TIMER,
  INCREASE_INACTIVE_TIMER,
  LEAD_INCREASE_INACTIVE_TIMER,
  RedneckCruise,
  SEND_BUTTON_DECREASE,
  SEND_BUTTON_INCREASE,
  SEND_BUTTON_NONE,
  select_redneck_target_speed,
)


ButtonType = car.CarState.ButtonEvent.Type


class TestRedneckCruise(unittest.TestCase):
  def setUp(self):
    self.CP = SimpleNamespace()
    self.FPCP = SimpleNamespace(pcmCruiseSpeed=False, redneckCruiseAvailable=True)
    self.redneck = RedneckCruise(self.CP, self.FPCP)

  def _new_state(self, speed_cluster_mph=20.0, button_events=None):
    return SimpleNamespace(
      cruiseState=SimpleNamespace(speedCluster=speed_cluster_mph * CV.MPH_TO_MS),
      buttonEvents=button_events or [],
    )

  @staticmethod
  def _new_control(override=False, cancel=False, resume=False):
    return SimpleNamespace(
      enabled=True,
      cruiseControl=SimpleNamespace(override=override, cancel=cancel, resume=resume),
    )

  @staticmethod
  def _button_event(button_type, pressed):
    return SimpleNamespace(type=button_type, pressed=pressed)

  def _run_until_active(self, target_mph, speed_cluster_mph=20.0, button_events=None,
                        override=False, cancel=False, resume=False, lead_present=False):
    frames = int(max(INCREASE_INACTIVE_TIMER, DECREASE_INACTIVE_TIMER) / DT_CTRL) + 2
    send_button = SEND_BUTTON_NONE
    v_target = 0
    for _ in range(frames):
      send_button, v_target = self.redneck.run(
        self._new_state(speed_cluster_mph=speed_cluster_mph, button_events=button_events),
        self._new_control(override=override, cancel=cancel, resume=resume),
        target_mph * CV.MPH_TO_MS,
        is_metric=False,
        lead_present=lead_present,
      )
      button_events = None
    return send_button, v_target

  def _frames_until_button(self, target_mph, speed_cluster_mph, lead_present=False):
    frames = int(INCREASE_INACTIVE_TIMER / DT_CTRL) + 4
    for frame in range(frames):
      send_button, _ = self.redneck.run(
        self._new_state(speed_cluster_mph=speed_cluster_mph),
        self._new_control(),
        target_mph * CV.MPH_TO_MS,
        is_metric=False,
        lead_present=lead_present,
      )
      if send_button != SEND_BUTTON_NONE:
        return frame
    return None

  def test_increases_cluster_speed_toward_target(self):
    send_button, v_target = self._run_until_active(target_mph=25.0, speed_cluster_mph=20.0)
    self.assertEqual(SEND_BUTTON_INCREASE, send_button)
    self.assertEqual(25, v_target)

  def test_decreases_cluster_speed_toward_target(self):
    send_button, v_target = self._run_until_active(target_mph=20.0, speed_cluster_mph=25.0)
    self.assertEqual(SEND_BUTTON_DECREASE, send_button)
    self.assertEqual(20, v_target)

  def test_decrease_activates_faster_than_increase(self):
    decrease_frame = self._frames_until_button(target_mph=20.0, speed_cluster_mph=25.0)
    self.redneck = RedneckCruise(self.CP, self.FPCP)
    increase_frame = self._frames_until_button(target_mph=25.0, speed_cluster_mph=20.0)

    self.assertIsNotNone(decrease_frame)
    self.assertIsNotNone(increase_frame)
    self.assertLess(decrease_frame, increase_frame)

  def test_lead_increase_activates_faster_than_free_cruise_increase(self):
    free_cruise_frame = self._frames_until_button(target_mph=25.0, speed_cluster_mph=20.0, lead_present=False)
    self.redneck = RedneckCruise(self.CP, self.FPCP)
    lead_frame = self._frames_until_button(target_mph=25.0, speed_cluster_mph=20.0, lead_present=True)

    self.assertIsNotNone(free_cruise_frame)
    self.assertIsNotNone(lead_frame)
    self.assertLess(lead_frame, free_cruise_frame)
    self.assertLessEqual(lead_frame, int(LEAD_INCREASE_INACTIVE_TIMER / DT_CTRL))

  def test_suppresses_output_during_manual_cruise_button_use(self):
    button_event = self._button_event(ButtonType.accelCruise, True)
    send_button, _ = self._run_until_active(target_mph=25.0, speed_cluster_mph=20.0, button_events=[button_event])
    self.assertEqual(SEND_BUTTON_NONE, send_button)

  def test_suppresses_output_for_capnp_style_button_events(self):
    button_event = SimpleNamespace(type=SimpleNamespace(raw=int(ButtonType.accelCruise)), pressed=True)
    send_button, _ = self._run_until_active(target_mph=25.0, speed_cluster_mph=20.0, button_events=[button_event])
    self.assertEqual(SEND_BUTTON_NONE, send_button)

  def test_suppresses_output_for_override_cancel_and_resume(self):
    for kwargs in ({"override": True}, {"cancel": True}, {"resume": True}):
      with self.subTest(**kwargs):
        send_button, _ = self._run_until_active(target_mph=25.0, speed_cluster_mph=20.0, **kwargs)
        self.assertEqual(SEND_BUTTON_NONE, send_button)

  def test_resets_when_pcm_cruise_speed_is_enabled(self):
    self.FPCP.pcmCruiseSpeed = True
    send_button, v_target = self._run_until_active(target_mph=25.0, speed_cluster_mph=20.0)
    self.assertEqual(SEND_BUTTON_NONE, send_button)
    self.assertEqual(0, v_target)

  def test_target_speed_returns_internal_max_when_plan_only_wants_to_speed_back_up(self):
    target_speed = select_redneck_target_speed(
      120.0,
      77.0 * CV.MPH_TO_MS,
      0.0,
      [78.3 * CV.MPH_TO_MS, 78.2 * CV.MPH_TO_MS, 78.1 * CV.MPH_TO_MS],
      10,
    )
    self.assertAlmostEqual(120.0 * CV.KPH_TO_MS, target_speed)

  def test_target_speed_ignores_plan_drift_during_free_cruise(self):
    target_speed = select_redneck_target_speed(
      104.4,
      63.0 * CV.MPH_TO_MS,
      0.0,
      [62.55 * CV.MPH_TO_MS, 62.44 * CV.MPH_TO_MS, 62.36 * CV.MPH_TO_MS],
      10,
      allow_plan_decrease=False,
    )
    self.assertAlmostEqual(104.4 * CV.KPH_TO_MS, target_speed)

  def test_target_speed_returns_plan_minimum_when_slowing_down(self):
    target_speed = select_redneck_target_speed(
      120.0,
      75.0 * CV.MPH_TO_MS,
      0.0,
      [74.0 * CV.MPH_TO_MS, 72.0 * CV.MPH_TO_MS, 71.0 * CV.MPH_TO_MS],
      10,
      allow_plan_decrease=True,
    )
    self.assertAlmostEqual(71.0 * CV.MPH_TO_MS, target_speed)

  def test_target_speed_uses_longer_horizon_and_buffer_for_lead_slowdown(self):
    target_speed = select_redneck_target_speed(
      120.0,
      75.0 * CV.MPH_TO_MS,
      0.0,
      [74.9 * CV.MPH_TO_MS, 74.6 * CV.MPH_TO_MS, 74.2 * CV.MPH_TO_MS, 73.8 * CV.MPH_TO_MS,
       73.4 * CV.MPH_TO_MS, 73.0 * CV.MPH_TO_MS, 72.6 * CV.MPH_TO_MS, 72.2 * CV.MPH_TO_MS,
       71.8 * CV.MPH_TO_MS, 71.4 * CV.MPH_TO_MS, 71.0 * CV.MPH_TO_MS],
      11,
      allow_plan_decrease=True,
      lead_present=True,
    )
    self.assertLess(target_speed, 71.4 * CV.MPH_TO_MS)

  def test_target_speed_uses_near_term_recovery_for_lead_speedup(self):
    target_speed = select_redneck_target_speed(
      120.0,
      55.0 * CV.MPH_TO_MS,
      0.0,
      [57.15 * CV.MPH_TO_MS, 56.9 * CV.MPH_TO_MS, 56.4 * CV.MPH_TO_MS, 55.8 * CV.MPH_TO_MS,
       54.88 * CV.MPH_TO_MS, 52.0 * CV.MPH_TO_MS, 50.15 * CV.MPH_TO_MS],
      10,
      allow_plan_decrease=True,
      lead_present=True,
    )
    self.assertAlmostEqual(55.8 * CV.MPH_TO_MS, target_speed)

  def test_target_speed_stays_on_lead_target_when_cluster_drops_below_it(self):
    target_speed = select_redneck_target_speed(
      76.9,
      32.9 * CV.MPH_TO_MS,
      47.8 * CV.MPH_TO_MS,
      [37.3 * CV.MPH_TO_MS, 37.2 * CV.MPH_TO_MS, 37.1 * CV.MPH_TO_MS],
      10,
      allow_plan_decrease=True,
      lead_present=True,
    )
    self.assertAlmostEqual(37.1 * CV.MPH_TO_MS, target_speed)


if __name__ == "__main__":
  unittest.main()
