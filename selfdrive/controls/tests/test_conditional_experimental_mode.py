from pathlib import Path
from types import SimpleNamespace

import numpy as np

from openpilot.common.constants import CV
from openpilot.starpilot.controls.starpilot_planner import StarPilotPlanner
import openpilot.starpilot.controls.starpilot_planner as starpilot_planner_module
import openpilot.starpilot.controls.lib.conditional_experimental_mode as conditional_experimental_mode_module
from openpilot.starpilot.controls.lib.conditional_experimental_mode import ConditionalExperimentalMode


class FakeParams:
  def __init__(self, initial=None):
    self._store = dict(initial or {})

  def get_bool(self, key):
    return bool(self._store.get(key, False))

  def put_bool(self, key, value):
    self._store[key] = bool(value)

  def get_int(self, key, default=0):
    return int(self._store.get(key, default))

  def put_int(self, key, value):
    self._store[key] = int(value)


def make_cem(*, model_length: float, model_stopped: bool = False, tracking_lead: bool = False,
             lead_status: bool = False, lead_d_rel: float = float("inf"),
             lead_v_lead: float = 0.0, lead_model_prob: float = 0.0, lead_radar: bool = False,
             stop_sign_confirmed: bool = False, forcing_stop: bool = False):
  planner = SimpleNamespace(
    params=FakeParams(),
    params_memory=FakeParams(),
    model_length=model_length,
    model_stopped=model_stopped,
    tracking_lead=tracking_lead,
    starpilot_vcruise=SimpleNamespace(
      stop_sign_confirmed=stop_sign_confirmed,
      forcing_stop=forcing_stop,
      slc=SimpleNamespace(experimental_mode=False),
    ),
    starpilot_following=SimpleNamespace(slower_lead=False, following_lead=False),
    lead_one=SimpleNamespace(status=lead_status, dRel=lead_d_rel, vLead=lead_v_lead,
                             modelProb=lead_model_prob, radar=lead_radar),
    road_curvature_detected=False,
    driving_in_curve=False,
    lane_width_left=0.0,
    lane_width_right=0.0,
  )
  return ConditionalExperimentalMode(planner)


def make_sm(traffic_mode_enabled: bool = False, car_fingerprint: str = ""):
  return {
    "carState": SimpleNamespace(standstill=False, leftBlinker=False, rightBlinker=False, steeringAngleDeg=0.0),
    "starpilotCarState": SimpleNamespace(trafficModeEnabled=traffic_mode_enabled),
    "carParams": SimpleNamespace(carFingerprint=car_fingerprint),
  }


def run_stop_light_detector(cem, v_ego, *, steps: int, tracking_lead: bool = False):
  for _ in range(steps):
    cem.starpilot_planner.tracking_lead = tracking_lead
    cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)


def make_update_sm(*, standstill: bool):
  return {
    "carState": SimpleNamespace(standstill=standstill, leftBlinker=False, rightBlinker=False, gasPressed=False, steeringAngleDeg=0.0),
    "starpilotCarState": SimpleNamespace(trafficModeEnabled=False, dashboardStopSign=0, accelPressed=False),
  }


def make_update_toggles():
  return SimpleNamespace(
    conditional_limit=0.0,
    conditional_limit_lead=0.0,
    conditional_signal=0.0,
    conditional_signal_lane_detection=False,
    lane_detection_width=0.0,
    conditional_curves=False,
    conditional_curves_lead=False,
    conditional_lead=False,
    conditional_open_road=False,
    conditional_model_stop_time=7.0,
    conditional_slower_lead=False,
    conditional_stopped_lead=False,
  )


def test_open_road_triggers_at_set_speed_without_a_lead():
  cem = make_cem(model_length=80.0)
  toggles = make_update_toggles()
  toggles.conditional_open_road = True

  triggered = cem.check_conditions(
    57 * CV.MPH_TO_MS,
    make_sm(),
    toggles,
    v_cruise=57 * CV.MPH_TO_MS,
  )

  assert triggered
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["SPEED"]


def test_open_road_does_not_trigger_below_or_far_above_set_speed():
  toggles = make_update_toggles()
  toggles.conditional_open_road = True

  too_far_below = make_cem(model_length=80.0)
  above_set_speed = make_cem(model_length=80.0)

  assert not too_far_below.check_conditions(
    56 * CV.MPH_TO_MS, make_sm(), toggles, v_cruise=57 * CV.MPH_TO_MS,
  )
  assert not above_set_speed.check_conditions(
    59 * CV.MPH_TO_MS, make_sm(), toggles, v_cruise=57 * CV.MPH_TO_MS,
  )


def test_open_road_requires_a_set_speed():
  cem = make_cem(model_length=80.0)
  toggles = make_update_toggles()
  toggles.conditional_open_road = True

  assert not cem.check_conditions(55 * CV.MPH_TO_MS, make_sm(), toggles)


def test_open_road_requires_no_lead_vehicle():
  cem = make_cem(model_length=80.0, lead_status=True, lead_d_rel=60.0, lead_v_lead=55 * CV.MPH_TO_MS)
  toggles = make_update_toggles()
  toggles.conditional_open_road = True

  assert not cem.check_conditions(
    55 * CV.MPH_TO_MS, make_sm(), toggles, v_cruise=57 * CV.MPH_TO_MS,
  )


def test_open_road_holds_exp_briefly_for_safe_lead_handoff(monkeypatch):
  cem = make_cem(model_length=80.0)
  toggles = make_update_toggles()
  toggles.conditional_open_road = True
  sm = make_update_sm(standstill=False)
  monkeypatch.setattr(cem, "update_conditions", lambda *args: None)

  now = [100.0]
  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: now[0])

  cem.update(57 * CV.MPH_TO_MS, sm, toggles, v_cruise=57 * CV.MPH_TO_MS)
  assert cem.experimental_mode

  cem.starpilot_planner.lead_one.status = True
  cem.starpilot_planner.lead_one.dRel = 60.0
  cem.starpilot_planner.lead_one.vLead = 55 * CV.MPH_TO_MS
  now[0] = 100.6
  cem.update(55 * CV.MPH_TO_MS, sm, toggles, v_cruise=57 * CV.MPH_TO_MS)
  assert cem.experimental_mode
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["SPEED"]

  now[0] = 101.4
  cem.update(55 * CV.MPH_TO_MS, sm, toggles, v_cruise=57 * CV.MPH_TO_MS)
  assert not cem.experimental_mode


def test_open_road_does_not_delay_urgent_lead_handoff(monkeypatch):
  cem = make_cem(model_length=80.0)
  toggles = make_update_toggles()
  toggles.conditional_open_road = True
  sm = make_update_sm(standstill=False)
  monkeypatch.setattr(cem, "update_conditions", lambda *args: None)

  now = [100.0]
  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: now[0])

  cem.update(57 * CV.MPH_TO_MS, sm, toggles, v_cruise=57 * CV.MPH_TO_MS)
  cem.starpilot_planner.lead_one.status = True
  cem.starpilot_planner.lead_one.dRel = 20.0
  cem.starpilot_planner.lead_one.vLead = 0.0
  now[0] = 101.6
  cem.update(55 * CV.MPH_TO_MS, sm, toggles, v_cruise=57 * CV.MPH_TO_MS)
  now[0] = 101.9
  cem.update(55 * CV.MPH_TO_MS, sm, toggles, v_cruise=57 * CV.MPH_TO_MS)

  assert not cem.experimental_mode


def test_low_speed_cruise_does_not_trigger_stop_light_from_model_stopped():
  v_ego = 10 * CV.MPH_TO_MS
  model_length = v_ego * 10.0

  cem = make_cem(model_length=model_length, model_stopped=True)
  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)

  assert not cem.stop_light_detected


def test_predicted_stop_within_threshold_triggers_stop_light():
  v_ego = 30 * CV.MPH_TO_MS
  model_length = v_ego * 4.0

  cem = make_cem(model_length=model_length)
  run_stop_light_detector(cem, v_ego, steps=20)

  assert cem.stop_light_detected


def test_elantra_stop_light_filter_uses_earlier_approach_timing():
  v_ego = 36 * CV.MPH_TO_MS
  model_length = v_ego * 4.0

  default_cem = make_cem(model_length=model_length)
  elantra_cem = make_cem(model_length=model_length)
  default_sm = make_sm()
  elantra_sm = make_sm(car_fingerprint="HYUNDAI_ELANTRA_2021")

  default_steps = None
  elantra_steps = None
  for step in range(1, 30):
    default_cem.stop_sign_and_light(v_ego, default_sm, model_time=7.0)
    elantra_cem.stop_sign_and_light(v_ego, elantra_sm, model_time=7.0)
    if default_steps is None and default_cem.stop_light_detected:
      default_steps = step
    if elantra_steps is None and elantra_cem.stop_light_detected:
      elantra_steps = step

  assert elantra_steps is not None
  assert default_steps is not None
  assert elantra_steps < default_steps


def test_chattering_lead_does_not_trigger_stop_light():
  v_ego = 22 * CV.MPH_TO_MS
  model_length = v_ego * 4.0

  cem = make_cem(model_length=model_length)
  for i in range(30):
    cem.starpilot_planner.tracking_lead = (i % 2 == 0)
    cem.starpilot_planner.lead_one.status = (i % 2 == 0)
    cem.starpilot_planner.lead_one.dRel = model_length + 5.0
    cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)

  assert not cem.stop_light_detected


def test_close_visible_but_untracked_lead_blocks_stop_light():
  v_ego = 22 * CV.MPH_TO_MS
  model_length = v_ego * 4.0

  cem = make_cem(model_length=model_length, lead_status=True, lead_d_rel=model_length + 5.0)
  run_stop_light_detector(cem, v_ego, steps=30)

  assert not cem.stop_light_detected


def test_far_visible_lead_does_not_block_stop_light():
  v_ego = 22 * CV.MPH_TO_MS
  model_length = v_ego * 4.0

  cem = make_cem(model_length=model_length, lead_status=True, lead_d_rel=v_ego * 7.0 + 30.0)
  run_stop_light_detector(cem, v_ego, steps=30)

  assert cem.stop_light_detected


def test_stop_light_stays_latched_until_untracked_stopped_lead_handoff():
  v_ego = 45 * CV.MPH_TO_MS
  model_length = v_ego * 4.0

  cem = make_cem(model_length=model_length)
  run_stop_light_detector(cem, v_ego, steps=30)
  assert cem.stop_light_detected

  cem.starpilot_planner.lead_one.status = True
  cem.starpilot_planner.lead_one.dRel = model_length - 5.0
  cem.starpilot_planner.lead_one.vLead = 0.5
  run_stop_light_detector(cem, v_ego, steps=10, tracking_lead=False)

  assert cem.stop_light_detected


def test_stop_light_latch_holds_slow_high_confidence_vision_lead_during_model_flicker(monkeypatch):
  v_ego = 40 * CV.MPH_TO_MS
  model_length = v_ego * 3.8
  cem = make_cem(
    model_length=model_length,
    lead_status=True,
    lead_d_rel=model_length - 5.0,
    lead_v_lead=3.0,
    lead_model_prob=0.98,
  )

  run_stop_light_detector(cem, v_ego, steps=20)
  assert cem.stop_light_detected

  monotonic_values = iter([10.0, 10.2])
  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: next(monotonic_values))

  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)
  cem.stop_light_detected = False
  cem.stop_light_model_detected = False
  cem.stop_light_filter.x = 0.0
  cem.starpilot_planner.model_length = v_ego * 9.0
  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)

  assert cem.stop_light_detected


def test_stop_light_hold_bridges_short_no_lead_model_flicker(monkeypatch):
  v_ego = 40 * CV.MPH_TO_MS
  cem = make_cem(model_length=v_ego * 3.8)

  run_stop_light_detector(cem, v_ego, steps=20)
  assert cem.stop_light_detected
  cem.stop_light_detected_hold_until = 11.75

  monotonic_values = iter([10.0, 11.0, 14.5, 16.5, 18.5])
  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: next(monotonic_values))

  cem.starpilot_planner.model_length = v_ego * 9.0
  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)
  assert cem.stop_light_detected

  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)
  assert cem.stop_light_detected

  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)
  assert cem.stop_light_detected

  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)
  assert cem.stop_light_detected

  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)
  assert not cem.stop_light_detected


def test_stop_light_hold_refreshes_through_stopped_approach_lead(monkeypatch):
  v_ego = 20 * CV.MPH_TO_MS
  model_length = v_ego * 4.0
  cem = make_cem(
    model_length=model_length,
    lead_status=True,
    lead_d_rel=model_length - 5.0,
    lead_v_lead=0.5,
    lead_model_prob=0.98,
  )

  run_stop_light_detector(cem, v_ego, steps=20)
  assert cem.stop_light_detected

  monotonic_values = iter([20.0, 21.2, 22.4])
  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: next(monotonic_values))

  cem.starpilot_planner.model_length = v_ego * 9.0
  cem.stop_light_detected = False
  cem.stop_light_model_detected = False
  cem.stop_light_filter.x = 0.0

  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)
  assert cem.stop_light_detected

  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)
  assert cem.stop_light_detected

  cem.starpilot_planner.lead_one.vLead = 6.0
  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)
  assert not cem.stop_light_detected


def test_stop_light_approach_latch_clears_once_tracked_lead_takes_over(monkeypatch):
  v_ego = 20 * CV.MPH_TO_MS
  model_length = v_ego * 4.0
  cem = make_cem(
    model_length=model_length,
    lead_status=True,
    lead_d_rel=model_length - 5.0,
    lead_v_lead=0.5,
    lead_model_prob=0.98,
  )

  run_stop_light_detector(cem, v_ego, steps=20)
  assert cem.stop_light_detected

  monotonic_values = iter([20.0, 20.2])
  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: next(monotonic_values))

  cem.starpilot_planner.model_length = v_ego * 9.0
  cem.stop_light_detected = False
  cem.stop_light_model_detected = False
  cem.stop_light_filter.x = 0.0

  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)
  assert cem.stop_light_detected

  cem.starpilot_planner.tracking_lead = True
  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)
  assert not cem.stop_light_detected


def test_stopped_lead_handoff_does_not_hold_cem_on_empty_road(monkeypatch):
  v_ego = 40 * CV.MPH_TO_MS
  cem = make_cem(
    model_length=v_ego * 9.0,
    tracking_lead=False,
    lead_status=False,
  )
  cem.stop_light_detected = True
  cem.stop_light_model_detected = False
  cem.stop_light_filter.x = 0.0
  cem.stop_approach_hold_until = 11.0
  cem.stop_light_detected_hold_until = 0.0

  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: 10.2)

  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)

  assert not cem.stop_light_detected


def test_stopped_lead_toggle_does_not_self_trigger_without_a_real_lead():
  v_ego = 25 * CV.MPH_TO_MS
  cem = make_cem(
    model_length=v_ego * 6.0,
    tracking_lead=False,
    lead_status=False,
    lead_v_lead=0.0,
  )
  toggles = SimpleNamespace(conditional_slower_lead=False, conditional_stopped_lead=True)

  for _ in range(24):
    cem.slow_lead(toggles, v_ego)

  assert not cem.slow_lead_detected


def test_stopped_lead_toggle_still_triggers_for_real_close_stopped_lead():
  v_ego = 25 * CV.MPH_TO_MS
  cem = make_cem(
    model_length=v_ego * 4.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=18.0,
    lead_v_lead=0.4,
    lead_model_prob=0.99,
  )
  toggles = SimpleNamespace(conditional_slower_lead=False, conditional_stopped_lead=True)

  for _ in range(24):
    cem.slow_lead(toggles, v_ego)

  assert cem.slow_lead_detected


def test_borderline_empty_road_model_dip_does_not_refresh_long_hold(monkeypatch):
  v_ego = 20 * CV.MPH_TO_MS
  stop_threshold = v_ego * 7.0
  cem = make_cem(model_length=stop_threshold - 4.0)
  cem.stop_light_filter.x = conditional_experimental_mode_module.THRESHOLD ** 2

  monotonic_values = iter([10.0, 10.2])
  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: next(monotonic_values))

  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)
  assert cem.stop_light_detected_hold_until == 0.0

  cem.starpilot_planner.model_length = stop_threshold + 20.0
  cem.stop_sign_and_light(v_ego, make_sm(), model_time=7.0)
  assert not cem.stop_light_detected


def test_standstill_red_light_keeps_exp_on_even_when_model_stopped_clears(monkeypatch):
  cem = make_cem(model_length=80.0, model_stopped=False)
  toggles = make_update_toggles()
  sm = make_update_sm(standstill=True)

  cem.stop_light_detected = True
  cem.experimental_mode = False
  monkeypatch.setattr(cem, "stop_sign_and_light", lambda *args, **kwargs: None)

  cem.update(0.0, sm, toggles)

  assert cem.experimental_mode
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["STOP_LIGHT"]


def test_standstill_close_stopped_lead_does_not_drop_red_light_exp(monkeypatch):
  cem = make_cem(
    model_length=80.0,
    model_stopped=False,
    lead_status=True,
    lead_d_rel=8.0,
    lead_v_lead=0.0,
  )
  toggles = make_update_toggles()
  sm = make_update_sm(standstill=True)

  cem.stop_light_detected = True
  monkeypatch.setattr(cem, "stop_sign_and_light", lambda *args, **kwargs: None)

  cem.update(0.0, sm, toggles)

  assert cem.experimental_mode
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["STOP_LIGHT"]


def test_standstill_update_can_activate_exp_from_red_light_detection(monkeypatch):
  cem = make_cem(model_length=80.0, model_stopped=False)
  toggles = make_update_toggles()
  sm = make_update_sm(standstill=True)

  def detect_red_light(*args, **kwargs):
    cem.stop_light_detected = True

  monkeypatch.setattr(cem, "stop_sign_and_light", detect_red_light)

  cem.update(0.0, sm, toggles)

  assert cem.experimental_mode
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["STOP_LIGHT"]


def test_first_post_standstill_pullaway_frame_does_not_blip_into_exp(monkeypatch):
  cem = make_cem(
    model_length=70.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=8.4,
    lead_v_lead=2.7,
    lead_model_prob=0.999,
  )
  toggles = make_update_toggles()
  toggles.conditional_lead = True
  toggles.conditional_slower_lead = True
  toggles.conditional_stopped_lead = True
  standstill_sm = make_update_sm(standstill=True)
  moving_sm = make_update_sm(standstill=False)

  now = [100.0]
  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: now[0])

  cem.update(0.0, standstill_sm, toggles)
  assert not cem.experimental_mode

  now[0] = 100.1
  cem.update(0.12, moving_sm, toggles)

  assert not cem.experimental_mode
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["OFF"]


def test_post_stop_speed_trigger_is_suppressed_after_red_light_release(monkeypatch):
  cem = make_cem(model_length=80.0, model_stopped=False)
  toggles = make_update_toggles()
  toggles.conditional_limit = 5.0 * CV.MPH_TO_MS
  standstill_sm = make_update_sm(standstill=True)
  moving_sm = make_update_sm(standstill=False)

  now = [100.0]
  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: now[0])

  def hold_red_light(*args, **kwargs):
    cem.stop_light_detected = True

  monkeypatch.setattr(cem, "stop_sign_and_light", hold_red_light)
  cem.update(0.0, standstill_sm, toggles)
  assert cem.experimental_mode

  def clear_red_light(*args, **kwargs):
    cem.stop_light_detected = False
    cem.stop_light_model_detected = False

  monkeypatch.setattr(cem, "stop_sign_and_light", clear_red_light)

  low_speed_trigger_v_ego = 4.0 * CV.MPH_TO_MS

  now[0] = 100.1
  cem.update(low_speed_trigger_v_ego, moving_sm, toggles)
  assert not cem.experimental_mode
  assert cem.params_memory.get_int("CEStatus") == conditional_experimental_mode_module.CEStatus["OFF"]

  now[0] = 102.5
  cem.update(low_speed_trigger_v_ego, moving_sm, toggles)
  assert cem.experimental_mode
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["SPEED"]


def test_post_stop_suppression_survives_hold_release_before_motion(monkeypatch):
  cem = make_cem(model_length=80.0, model_stopped=False)
  toggles = make_update_toggles()
  toggles.conditional_limit = 5.0 * CV.MPH_TO_MS
  standstill_sm = make_update_sm(standstill=True)
  moving_sm = make_update_sm(standstill=False)

  now = [100.0]
  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: now[0])

  def hold_red_light(*args, **kwargs):
    cem.stop_light_detected = True

  monkeypatch.setattr(cem, "stop_sign_and_light", hold_red_light)
  cem.update(0.0, standstill_sm, toggles)
  assert cem.experimental_mode

  def clear_red_light(*args, **kwargs):
    cem.stop_light_detected = False
    cem.stop_light_model_detected = False

  monkeypatch.setattr(cem, "stop_sign_and_light", clear_red_light)

  now[0] = 100.1
  cem.update(0.0, standstill_sm, toggles)
  assert not cem.experimental_mode
  assert cem.standstill_stop_release_pending

  low_speed_trigger_v_ego = 4.0 * CV.MPH_TO_MS

  now[0] = 100.2
  cem.update(low_speed_trigger_v_ego, moving_sm, toggles)
  assert not cem.experimental_mode
  assert not cem.standstill_stop_release_pending

  now[0] = 102.5
  cem.update(low_speed_trigger_v_ego, moving_sm, toggles)
  assert cem.experimental_mode
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["SPEED"]


def test_post_stop_slow_lead_trigger_is_suppressed_after_red_light_release(monkeypatch):
  cem = make_cem(model_length=80.0, model_stopped=False)
  toggles = make_update_toggles()
  toggles.conditional_lead = True
  toggles.conditional_slower_lead = True
  toggles.conditional_stopped_lead = True
  standstill_sm = make_update_sm(standstill=True)
  moving_sm = make_update_sm(standstill=False)

  now = [100.0]
  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: now[0])

  def hold_red_light(*args, **kwargs):
    cem.stop_light_detected = True

  def clear_red_light(*args, **kwargs):
    cem.stop_light_detected = False
    cem.stop_light_model_detected = False

  def detect_slow_lead(*args, **kwargs):
    cem.slow_lead_detected = True

  monkeypatch.setattr(cem, "stop_sign_and_light", hold_red_light)
  cem.update(0.0, standstill_sm, toggles)
  assert cem.experimental_mode

  monkeypatch.setattr(cem, "stop_sign_and_light", clear_red_light)
  monkeypatch.setattr(cem, "slow_lead", detect_slow_lead)

  launch_v_ego = 8.0 * CV.MPH_TO_MS

  now[0] = 100.1
  cem.update(launch_v_ego, moving_sm, toggles)
  assert not cem.experimental_mode
  assert cem.params_memory.get_int("CEStatus") == conditional_experimental_mode_module.CEStatus["OFF"]

  now[0] = 102.5
  cem.update(launch_v_ego, moving_sm, toggles)
  assert cem.experimental_mode
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["LEAD"]


def test_slow_lead_mode_release_waits_for_stable_credible_lead(monkeypatch):
  v_ego = 20.0
  cem = make_cem(
    model_length=100.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=34.0,
    lead_v_lead=18.5,
    lead_model_prob=0.99,
  )
  toggles = make_update_toggles()
  toggles.conditional_lead = True
  toggles.conditional_slower_lead = True
  sm = make_update_sm(standstill=False)
  slow_lead_active = [True]
  now = [100.0]

  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: now[0])

  def update_conditions(*args, **kwargs):
    cem.slow_lead_detected = slow_lead_active[0]

  monkeypatch.setattr(cem, "update_conditions", update_conditions)

  cem.update(v_ego, sm, toggles)
  assert cem.experimental_mode
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["LEAD"]

  slow_lead_active[0] = False
  now[0] = 100.9
  cem.update(v_ego, sm, toggles)
  assert cem.experimental_mode
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["LEAD"]

  now[0] = 101.6
  cem.update(v_ego, sm, toggles)
  assert not cem.experimental_mode
  assert cem.params_memory.get_int("CEStatus") == conditional_experimental_mode_module.CEStatus["OFF"]


def test_slow_lead_mode_release_does_not_hold_missing_lead(monkeypatch):
  v_ego = 20.0
  cem = make_cem(
    model_length=100.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=34.0,
    lead_v_lead=18.5,
    lead_model_prob=0.99,
  )
  toggles = make_update_toggles()
  toggles.conditional_lead = True
  toggles.conditional_slower_lead = True
  sm = make_update_sm(standstill=False)
  slow_lead_active = [True]
  now = [200.0]

  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: now[0])

  def update_conditions(*args, **kwargs):
    cem.slow_lead_detected = slow_lead_active[0]

  monkeypatch.setattr(cem, "update_conditions", update_conditions)

  cem.update(v_ego, sm, toggles)
  assert cem.experimental_mode

  slow_lead_active[0] = False
  cem.starpilot_planner.lead_one.status = False
  cem.starpilot_planner.tracking_lead = False
  now[0] = 200.6
  cem.update(v_ego, sm, toggles)
  assert cem.experimental_mode

  now[0] = 200.9
  cem.update(v_ego, sm, toggles)

  assert not cem.experimental_mode
  assert cem.params_memory.get_int("CEStatus") == conditional_experimental_mode_module.CEStatus["OFF"]


def test_standstill_update_can_activate_exp_from_dashboard_stop_sign(monkeypatch):
  cem = make_cem(model_length=80.0, model_stopped=False)
  toggles = make_update_toggles()
  sm = make_update_sm(standstill=True)
  sm["starpilotCarState"].dashboardStopSign = 1

  monkeypatch.setattr(cem, "stop_sign_and_light", lambda *args, **kwargs: None)

  cem.update(0.0, sm, toggles)

  assert cem.experimental_mode
  assert cem.standstill_stop_reason == "sign"
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["STOP_LIGHT"]


def test_standstill_green_light_clears_exp_immediately(monkeypatch):
  cem = make_cem(model_length=80.0, model_stopped=False)
  toggles = make_update_toggles()
  sm = make_update_sm(standstill=True)

  cem.stop_light_detected = True
  cem.experimental_mode = True

  def clear_red_light(*args, **kwargs):
    cem.stop_light_detected = False
    cem.stop_light_model_detected = False

  monkeypatch.setattr(cem, "stop_sign_and_light", clear_red_light)

  cem.update(0.0, sm, toggles)

  assert not cem.experimental_mode
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["OFF"]


def test_standstill_dashboard_stop_sign_keeps_exp_on(monkeypatch):
  cem = make_cem(model_length=80.0, model_stopped=False, stop_sign_confirmed=True)
  toggles = make_update_toggles()
  sm = make_update_sm(standstill=True)

  monkeypatch.setattr(cem, "stop_sign_and_light", lambda *args, **kwargs: None)

  cem.update(0.0, sm, toggles)

  assert cem.experimental_mode
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["STOP_LIGHT"]


def test_standstill_force_stop_keeps_exp_on_even_if_red_light_latch_clears(monkeypatch):
  cem = make_cem(model_length=80.0, model_stopped=False, forcing_stop=True)
  toggles = make_update_toggles()
  sm = make_update_sm(standstill=True)

  cem.stop_light_detected = True
  cem.experimental_mode = True

  def clear_red_light(*args, **kwargs):
    cem.stop_light_detected = False
    cem.stop_light_model_detected = False

  monkeypatch.setattr(cem, "stop_sign_and_light", clear_red_light)

  cem.update(0.0, sm, toggles)

  assert cem.experimental_mode
  assert cem.status_value == conditional_experimental_mode_module.CEStatus["STOP_LIGHT"]


def test_committed_turn_veto_blocks_stop_light_detection():
  v_ego = 10 * CV.MPH_TO_MS
  model_length = v_ego * 4.0

  cem = make_cem(model_length=model_length)
  sm = make_sm()
  sm["carState"].rightBlinker = True
  sm["carState"].steeringAngleDeg = 70.0

  run_stop_light_detector(cem, v_ego, steps=20)
  assert cem.stop_light_detected

  cem.stop_light_detected = False
  cem.stop_light_model_detected = False
  cem.stop_light_filter.x = 0.0

  for _ in range(20):
    cem.stop_sign_and_light(v_ego, sm, model_time=7.0)

  assert not cem.stop_light_detected


def test_standstill_stop_sign_latches_until_pedal_even_after_force_stop_ends(monkeypatch):
  cem = make_cem(model_length=80.0, model_stopped=False)
  toggles = make_update_toggles()
  sm = make_update_sm(standstill=True)
  sm["starpilotCarState"].dashboardStopSign = 1

  monkeypatch.setattr(cem, "stop_sign_and_light", lambda *args, **kwargs: None)
  cem.update(0.0, sm, toggles)

  assert cem.experimental_mode
  assert cem.standstill_stop_reason == "sign"

  sm["starpilotCarState"].dashboardStopSign = 0
  cem.update(0.0, sm, toggles)

  assert cem.experimental_mode
  assert cem.standstill_stop_reason == "sign"


def test_standstill_stop_sign_releases_on_pedal(monkeypatch):
  cem = make_cem(model_length=80.0, model_stopped=False)
  toggles = make_update_toggles()
  sm = make_update_sm(standstill=True)
  sm["starpilotCarState"].dashboardStopSign = 1

  monkeypatch.setattr(cem, "stop_sign_and_light", lambda *args, **kwargs: None)
  cem.update(0.0, sm, toggles)
  assert cem.experimental_mode

  sm["starpilotCarState"].dashboardStopSign = 0
  sm["carState"].gasPressed = True
  cem.update(0.0, sm, toggles)

  assert not cem.experimental_mode
  assert cem.standstill_stop_reason is None


def test_slow_lead_holds_through_tracking_flap_for_high_confidence_vision_lead():
  v_ego = 35 * CV.MPH_TO_MS
  cem = make_cem(
    model_length=v_ego * 5.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=v_ego * 3.5,
    lead_v_lead=8.0 * CV.MPH_TO_MS,
    lead_model_prob=0.95,
  )
  toggles = SimpleNamespace(conditional_slower_lead=True, conditional_stopped_lead=False)

  cem.slow_lead_filter.x = 1.0
  cem.slow_lead_detected = True

  cem.starpilot_planner.tracking_lead = False
  cem.starpilot_planner.starpilot_following.slower_lead = False
  cem.slow_lead(toggles, v_ego)
  assert cem.slow_lead_detected


def test_untracked_raw_slow_lead_does_not_self_trigger_without_recent_tracking(monkeypatch):
  v_ego = 35 * CV.MPH_TO_MS
  cem = make_cem(
    model_length=v_ego * 5.0,
    tracking_lead=False,
    lead_status=True,
    lead_d_rel=v_ego * 3.0,
    lead_v_lead=8.0 * CV.MPH_TO_MS,
    lead_model_prob=0.95,
  )
  toggles = SimpleNamespace(conditional_slower_lead=True, conditional_stopped_lead=False)

  monotonic_values = iter([20.0 + 0.1 * i for i in range(24)])
  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: next(monotonic_values))

  for _ in range(12):
    cem.slow_lead(toggles, v_ego)

  assert not cem.slow_lead_detected


def test_untracked_raw_slow_lead_continuity_expires_after_tracking_flap(monkeypatch):
  v_ego = 35 * CV.MPH_TO_MS
  cem = make_cem(
    model_length=v_ego * 5.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=v_ego * 3.0,
    lead_v_lead=8.0 * CV.MPH_TO_MS,
    lead_model_prob=0.95,
  )
  toggles = SimpleNamespace(conditional_slower_lead=True, conditional_stopped_lead=False)

  cem.slow_lead_filter.x = 1.0
  cem.slow_lead_detected = True
  monotonic_values = iter([30.0, 30.1, 31.6])
  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: next(monotonic_values))

  cem.slow_lead(toggles, v_ego)
  assert cem.slow_lead_detected

  cem.starpilot_planner.tracking_lead = False
  cem.starpilot_planner.starpilot_following.slower_lead = False
  cem.slow_lead(toggles, v_ego)
  assert cem.slow_lead_detected

  cem.slow_lead(toggles, v_ego)
  assert not cem.slow_lead_detected


def test_tracked_highway_mild_closing_lead_does_not_trigger_raw_slow_lead():
  v_ego = 65 * CV.MPH_TO_MS
  cem = make_cem(
    model_length=v_ego * 5.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=46.0,
    lead_v_lead=v_ego - 1.4,
    lead_model_prob=1.0,
  )
  toggles = SimpleNamespace(conditional_slower_lead=True, conditional_stopped_lead=False)

  cem.slow_lead_filter.x = 0.0
  cem.slow_lead_detected = False
  cem.starpilot_planner.starpilot_following.slower_lead = False
  for _ in range(12):
    cem.slow_lead(toggles, v_ego)

  assert not cem.slow_lead_detected


def test_tracked_following_slower_lead_still_triggers_slow_lead():
  v_ego = 65 * CV.MPH_TO_MS
  cem = make_cem(
    model_length=v_ego * 5.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=36.0,
    lead_v_lead=v_ego - 3.0,
    lead_model_prob=1.0,
  )
  toggles = SimpleNamespace(conditional_slower_lead=True, conditional_stopped_lead=False)

  cem.slow_lead_filter.x = 0.0
  cem.slow_lead_detected = False
  cem.starpilot_planner.starpilot_following.slower_lead = True
  for _ in range(24):
    cem.slow_lead(toggles, v_ego)

  assert cem.slow_lead_detected


def test_far_radar_slower_lead_waits_for_comfort_range_before_triggering():
  v_ego = 75 * CV.MPH_TO_MS
  cem = make_cem(
    model_length=v_ego * 5.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=136.0,
    lead_v_lead=v_ego - 5.0,
    lead_model_prob=1.0,
    lead_radar=True,
  )
  toggles = SimpleNamespace(conditional_slower_lead=True, conditional_stopped_lead=False)
  cem.starpilot_planner.starpilot_following.slower_lead = True

  for _ in range(24):
    cem.slow_lead(toggles, v_ego)
  assert not cem.slow_lead_detected

  cem.starpilot_planner.lead_one.dRel = 80.0
  for _ in range(24):
    cem.slow_lead(toggles, v_ego)
  assert cem.slow_lead_detected


def test_far_vision_slower_lead_keeps_existing_trigger_range():
  v_ego = 75 * CV.MPH_TO_MS
  cem = make_cem(
    model_length=v_ego * 5.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=110.0,
    lead_v_lead=v_ego - 5.0,
    lead_model_prob=1.0,
    lead_radar=False,
  )
  toggles = SimpleNamespace(conditional_slower_lead=True, conditional_stopped_lead=False)
  cem.starpilot_planner.starpilot_following.slower_lead = True

  for _ in range(24):
    cem.slow_lead(toggles, v_ego)
  assert cem.slow_lead_detected


def test_tracked_vision_slow_lead_continues_existing_experimental_mode():
  v_ego = 8.0
  cem = make_cem(
    model_length=80.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=22.0,
    lead_v_lead=6.4,
    lead_model_prob=0.99,
  )
  toggles = SimpleNamespace(conditional_slower_lead=True, conditional_stopped_lead=False)

  cem.prev_experimental_mode = True
  for _ in range(24):
    cem.slow_lead(toggles, v_ego)

  assert cem.slow_lead_detected


def test_tracked_vision_slow_lead_does_not_start_experimental_mode():
  v_ego = 8.0
  cem = make_cem(
    model_length=80.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=22.0,
    lead_v_lead=6.4,
    lead_model_prob=0.99,
  )
  toggles = SimpleNamespace(conditional_slower_lead=True, conditional_stopped_lead=False)

  for _ in range(24):
    cem.slow_lead(toggles, v_ego)

  assert not cem.slow_lead_detected


def test_slow_lead_does_not_linger_at_crawl_when_stopped_lead_disabled():
  v_ego = 1.5
  cem = make_cem(
    model_length=20.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=8.0,
    lead_v_lead=1.2,
    lead_model_prob=0.99,
  )
  toggles = SimpleNamespace(conditional_slower_lead=True, conditional_stopped_lead=False)

  cem.slow_lead_filter.x = 1.0
  cem.slow_lead_detected = True
  cem.starpilot_planner.starpilot_following.slower_lead = False
  cem.slow_lead(toggles, v_ego)

  assert not cem.slow_lead_detected


def test_far_untracked_slow_lead_does_not_trigger_slow_lead():
  v_ego = 50 * CV.MPH_TO_MS
  cem = make_cem(
    model_length=v_ego * 5.0,
    tracking_lead=False,
    lead_status=True,
    lead_d_rel=v_ego * 4.8,
    lead_v_lead=v_ego - 2.0,
    lead_model_prob=0.97,
  )
  toggles = SimpleNamespace(conditional_slower_lead=True, conditional_stopped_lead=False)

  cem.slow_lead_filter.x = 1.0
  cem.slow_lead_detected = True
  cem.starpilot_planner.starpilot_following.slower_lead = False
  cem.slow_lead(toggles, v_ego)

  assert not cem.slow_lead_detected


def test_pace_matched_lead_clears_slow_lead_quickly():
  v_ego = 30 * CV.MPH_TO_MS
  cem = make_cem(
    model_length=v_ego * 4.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=24.0,
    lead_v_lead=v_ego + 0.2,
    lead_model_prob=0.99,
  )
  toggles = SimpleNamespace(conditional_slower_lead=True, conditional_stopped_lead=False)

  cem.slow_lead_filter.x = 1.0
  cem.slow_lead_detected = True
  cem.starpilot_planner.starpilot_following.slower_lead = False
  cem.slow_lead(toggles, v_ego)

  assert not cem.slow_lead_detected


def test_tracked_stale_slow_lead_clears_after_short_timeout(monkeypatch):
  v_ego = 65 * CV.MPH_TO_MS
  cem = make_cem(
    model_length=v_ego * 5.0,
    tracking_lead=True,
    lead_status=True,
    lead_d_rel=55.0,
    lead_v_lead=v_ego - 0.8,
    lead_model_prob=0.98,
  )
  toggles = SimpleNamespace(conditional_slower_lead=True, conditional_stopped_lead=False)

  cem.slow_lead_filter.x = 1.0
  cem.slow_lead_detected = True
  cem.starpilot_planner.starpilot_following.slower_lead = False

  monotonic_values = iter([50.0, 50.3, 50.9])
  monkeypatch.setattr(conditional_experimental_mode_module.time, "monotonic", lambda: next(monotonic_values))

  cem.slow_lead(toggles, v_ego)
  assert cem.slow_lead_detected

  cem.slow_lead(toggles, v_ego)
  assert cem.slow_lead_detected

  cem.slow_lead(toggles, v_ego)
  assert not cem.slow_lead_detected


class DummyThemeManager:
  def update_wheel_image(self, *args, **kwargs):
    pass


def test_starpilot_planner_updates_cem_with_current_frame_state(monkeypatch):
  planner = StarPilotPlanner(Path("/tmp/nonexistent"), DummyThemeManager())

  try:
    monkeypatch.setattr(starpilot_planner_module, "calculate_road_curvature", lambda model, v_ego: (0.01, 1.0))
    monkeypatch.setattr(starpilot_planner_module, "extract_curve_profile", lambda model: (np.zeros(33), np.zeros(33)))
    monkeypatch.setattr(planner.starpilot_acceleration, "update", lambda *args, **kwargs: None)
    monkeypatch.setattr(planner.starpilot_events, "update", lambda *args, **kwargs: None)
    monkeypatch.setattr(planner.starpilot_vcruise, "update", lambda *args, **kwargs: 0.0)
    monkeypatch.setattr(planner.starpilot_weather, "update_weather", lambda *args, **kwargs: None)

    def following_update(*args, **kwargs):
      planner.starpilot_following.following_lead = planner.tracking_lead
      planner.starpilot_following.slower_lead = planner.tracking_lead

    monkeypatch.setattr(planner.starpilot_following, "update", following_update)

    seen = {}

    def cem_update(v_ego, sm, starpilot_toggles, v_cruise):
      seen.update({
        "v_cruise": v_cruise,
        "tracking_lead": planner.tracking_lead,
        "following_lead": planner.starpilot_following.following_lead,
        "slower_lead": planner.starpilot_following.slower_lead,
        "model_length": planner.model_length,
        "driving_in_curve": planner.driving_in_curve,
        "road_curvature_detected": planner.road_curvature_detected,
      })

    monkeypatch.setattr(planner.starpilot_cem, "update", cem_update)

    planner.model_length = 0.0
    planner.tracking_lead = False
    planner.driving_in_curve = False
    planner.lateral_acceleration = 0.0
    planner.road_curvature_detected = False
    planner.starpilot_following.following_lead = False
    planner.starpilot_following.slower_lead = False

    starpilot_toggles = SimpleNamespace(
      set_speed_offset=0,
      conditional_experimental_mode=True,
      minimum_lane_change_speed=100.0,
      pause_lateral_below_speed=0.0,
      pause_lateral_below_signal=False,
      weather_presets=False,
    )

    for controls_enabled, aol_enabled in ((True, False), (False, True)):
      seen.clear()

      sm = {
        "radarState": SimpleNamespace(leadOne=SimpleNamespace(status=True, dRel=25.0, vLead=0.5)),
        "selfdriveState": SimpleNamespace(enabled=controls_enabled),
        "carState": SimpleNamespace(vCruise=50.0, vEgo=20.0, standstill=False, leftBlinker=False, rightBlinker=False),
        "controlsState": SimpleNamespace(curvature=0.02),
        "modelV2": SimpleNamespace(position=SimpleNamespace(x=[0.0, 30.0]), laneLines=[None] * 4, roadEdges=[None] * 2),
        "starpilotCarState": SimpleNamespace(pauseLateral=False, alwaysOnLateralEnabled=aol_enabled),
        planner.gps_location_service: SimpleNamespace(latitude=1.0, longitude=1.0, bearingDeg=90.0),
      }

      planner.tracking_lead_filter.x = 1.0
      planner.update(0.0, False, sm, starpilot_toggles)

      assert seen == {
        "v_cruise": 50.0 * CV.KPH_TO_MS,
        "tracking_lead": True,
        "following_lead": True,
        "slower_lead": True,
        "model_length": 30.0,
        "driving_in_curve": True,
        "road_curvature_detected": True,
      }
  finally:
    planner.shutdown()
