#!/usr/bin/env python3
import time
import numpy as np

from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.realtime import DT_MDL
from openpilot.common.constants import CV

from openpilot.starpilot.common.experimental_state import (
  CEStatus,
  is_manual_ce_status,
  restore_persisted_ce_state,
)
from openpilot.starpilot.common.starpilot_variables import CRUISING_SPEED, THRESHOLD

def interp(x, xp, fp):
  return float(np.interp(x, xp, fp))


def scale_threshold(v_ego):
  # Speed-based lead threshold behavior (v_ego in m/s)
  return interp(v_ego, [0.0, 17.9, 26.8, 35.8, 44.7], [0.58, 0.60, 0.62, 0.75, 0.90])


class ConditionalExperimentalMode:
  # ===== CONDITIONAL EXPERIMENTAL MODE SPEED-BASED TUNING =====
  # Speed ranges: [0-35, 35-55, 55-70, 70+ mph]

  # FILTER TIME CONSTANTS (Lower = More responsive, Higher = Smoother)
  # [City, Urban Hwy, Rural Hwy, High Speed]
  FILTER_TIME_CURVES = [0.9, 0.8, 0.6, 0.5]    # Faster detection at highway speeds
  FILTER_TIME_LEADS = [0.9, 0.8, 0.7, 0.5]     # Less sensitive at 70+ mph for slow leads
  FILTER_TIME_LIGHTS = [0.9, 0.8, 0.75, 0.55]  # Less sensitive at 60+ mph for stoplights

  # HIGHWAY LIGHT DETECTION MULTIPLIERS
  # How much to increase model stop time at highway speeds
  LIGHT_BOOSTS = [1.0, 1.2, 1.1, 1.0]         # Keep conservative boost for highest speeds
  LIGHT_SPEED_LOW = 50 * CV.MPH_TO_MS     # 50 mph threshold
  LIGHT_SPEED_HIGH = 60 * CV.MPH_TO_MS    # 60 mph threshold
  LIGHT_MAX_TIME = 9       # Balanced max time preserving city performance
  LOW_SPEED_LIGHT_FILTER_TIME = 0.35
  LEAD_CLEAR_FILTER_TIME_LOW = 0.6
  LEAD_CLEAR_FILTER_TIME_HIGH = 0.35
  STOP_LIGHT_ON_MARGIN = 2.5
  STOP_LIGHT_OFF_MARGIN = 4.0
  STOP_LIGHT_MODEL_HOLD_STRONG_MARGIN = 10.0
  STOP_LIGHT_LEAD_BLOCK_MARGIN = 15.0
  STOP_LIGHT_HANDOFF_MAX_LEAD_SPEED = 2.0
  STOP_LIGHT_DETECTED_HOLD_TIME = 1.75
  STOP_APPROACH_LATCH_TIME = 1.0
  STOP_APPROACH_MAX_LEAD_SPEED = 4.5
  STOP_APPROACH_MIN_MODEL_PROB = 0.9
  SLOW_LEAD_CONTINUITY_MIN_MODEL_PROB = 0.85
  SLOW_LEAD_CONTINUITY_MAX_DISTANCE_TIME = 4.0
  SLOW_LEAD_CONTINUITY_MIN_EGO = 2.5
  SLOW_LEAD_CONTINUITY_HOLD_TIME = 1.25
  SLOW_LEAD_FORCE_CLEAR_TIME = 0.75
  SLOW_LEAD_MIN_CLOSING_SPEED = 0.75
  SLOW_LEAD_CLEAR_FASTER_FACTOR = 0.5

  # ===== END TUNING PARAMETERS =====

  # Current active values
  FILTER_TIME_CURVE = 0.8
  FILTER_TIME_LEAD = 0.8
  FILTER_TIME_LIGHT = 0.8
  LIGHT_BOOST_LOW = 1.15
  LIGHT_BOOST_HIGH = 1.2

  # Small latch to avoid frame-to-frame mode chatter.
  CEM_TRANSITION_GUARD_TIME = 0.50
  CEM_TRANSITION_BUFFER_TIME = 0.25

  @staticmethod
  def get_speed_based_param(speed_mph, param_array):
    """Get parameter value based on current speed using smooth interpolation between breakpoints [0, 35, 55, 70]"""
    return interp(speed_mph, [0, 35, 55, 70], param_array)

  def __init__(self, StarPilotPlanner):
    self.starpilot_planner = StarPilotPlanner
    self.params = self.starpilot_planner.params
    self.params_memory = self.starpilot_planner.params_memory

    # Faster filters with hysteresis for better responsiveness
    self.curvature_filter = FirstOrderFilter(0, self.FILTER_TIME_CURVE, DT_MDL)
    self.slow_lead_filter = FirstOrderFilter(0, self.FILTER_TIME_LEAD, DT_MDL)
    self.stop_light_filter = FirstOrderFilter(0, self.FILTER_TIME_LIGHT, DT_MDL)
    self.lead_clear_filter = FirstOrderFilter(0, self.LEAD_CLEAR_FILTER_TIME_LOW, DT_MDL)

    self.curve_detected = False
    self.slow_lead_detected = False
    self.prev_tracking_lead = bool(getattr(self.starpilot_planner, "tracking_lead", False))
    self.slow_lead_clear_since = 0.0
    self.slow_lead_continuity_until = 0.0
    self.experimental_mode = False
    self.stop_light_detected = False
    self.stop_light_model_detected = False
    self.stop_light_detected_hold_until = 0.0
    self.stop_approach_hold_until = 0.0
    self.standstill_stop_reason = None
    self.prev_experimental_mode = False  # For hysteresis
    self.mode_hold_until = 0.0
    self.mode_false_since = 0.0
    self._prev_ce_status = None
    self.close_stopped_lead_since = 0.0

  def update(self, v_ego, sm, starpilot_toggles):
    now = time.monotonic()
    standstill = bool(sm["carState"].standstill)

    if not standstill:
      self.standstill_stop_reason = None

    self.status_value = CEStatus["OFF"] if self.params.get_bool("SafeMode") else restore_persisted_ce_state(self.params, self.params_memory)

    if not is_manual_ce_status(self.status_value) and not standstill:
      self.update_conditions(v_ego, sm, starpilot_toggles)

      triggered = self.check_conditions(v_ego, sm, starpilot_toggles)
      if triggered:
        self.mode_hold_until = now + self.CEM_TRANSITION_GUARD_TIME
        self.mode_false_since = 0.0
      elif self.mode_false_since == 0.0:
        self.mode_false_since = now

      hold_active = now < self.mode_hold_until
      transition_buffer_active = self.mode_false_since != 0.0 and (now - self.mode_false_since) < self.CEM_TRANSITION_BUFFER_TIME

      self.experimental_mode = triggered or hold_active or transition_buffer_active
      self.prev_experimental_mode = self.experimental_mode
      ce_write_value = self.status_value if self.experimental_mode else CEStatus["OFF"]
      if ce_write_value != self._prev_ce_status:
        self.params_memory.put_int("CEStatus", ce_write_value)
        self._prev_ce_status = ce_write_value
    elif not is_manual_ce_status(self.status_value):
      self.mode_hold_until = 0.0
      self.mode_false_since = 0.0

      # Keep the stop-light path live at standstill so EXP stays pinned for a red
      # light / stop sign. Stop signs latch until pedal, while stop lights can
      # immediately release to CHILL when the model clears the stop.
      self.stop_sign_and_light(v_ego, sm, starpilot_toggles.conditional_model_stop_time)
      standstill_stop_hold = self.get_standstill_stop_hold(sm)

      self.experimental_mode = standstill_stop_hold
      self.prev_experimental_mode = self.experimental_mode
      self.status_value = CEStatus["STOP_LIGHT"] if self.experimental_mode else CEStatus["OFF"]
      ce_write_value = self.status_value
      if ce_write_value != self._prev_ce_status:
        self.params_memory.put_int("CEStatus", ce_write_value)
        self._prev_ce_status = ce_write_value
    else:
      self.mode_hold_until = 0.0
      self.mode_false_since = 0.0
      self._prev_ce_status = None
      self.experimental_mode = self.status_value == CEStatus["USER_OVERRIDDEN"]
      self.prev_experimental_mode = self.experimental_mode
      self.stop_light_detected &= not is_manual_ce_status(self.status_value)
      self.stop_light_filter.x = 0

  # At standstill behind a close, stopped lead, prefer Chill over CEM.
  # Why: CEM is slow to release when the lead pulls away (waits on stop-light
  # filter + STOP_LIGHT_DETECTED_HOLD_TIME). Chill reacts to lead departure faster.
  STANDSTILL_LEAD_OVERRIDE_MAX_DISTANCE = 15.0  # meters
  STANDSTILL_LEAD_OVERRIDE_MAX_SPEED = 1.0      # m/s
  # Persistence required before handing off CEM->Chill. Cross-traffic (cars passing
  # perpendicular in front) briefly registers as a close, stopped lead and would
  # otherwise flap CEM out of EXP. Real queue-mates persist much longer than this.
  STANDSTILL_LEAD_OVERRIDE_PERSIST_TIME = 0.5  # seconds

  def get_standstill_stop_hold(self, sm):
    now = time.monotonic()
    dash_stop_sign = (
      bool(getattr(self.starpilot_planner.starpilot_vcruise, "stop_sign_confirmed", False)) or
      bool(getattr(sm["starpilotCarState"], "dashboardStopSign", 0) > 0)
    )
    force_stop_active = bool(getattr(self.starpilot_planner.starpilot_vcruise, "forcing_stop", False))
    model_stopped = bool(getattr(self.starpilot_planner, "model_stopped", False))
    pedal_override = bool(getattr(sm["carState"], "gasPressed", False) or getattr(sm["starpilotCarState"], "accelPressed", False))

    if pedal_override or not bool(sm["carState"].standstill):
      self.standstill_stop_reason = None
      self.close_stopped_lead_since = 0.0
      return False

    if dash_stop_sign:
      self.standstill_stop_reason = "sign"
    elif self.stop_light_detected or force_stop_active or model_stopped:
      if self.standstill_stop_reason is None:
        self.standstill_stop_reason = "light"
    elif self.standstill_stop_reason == "light":
      self.standstill_stop_reason = None

    if self.standstill_stop_reason == "sign":
      self.close_stopped_lead_since = 0.0
      return True

    lead = getattr(self.starpilot_planner, "lead_one", None)
    close_stopped_lead = bool(
      lead is not None and
      getattr(lead, "status", False) and
      float(getattr(lead, "dRel", float("inf"))) < self.STANDSTILL_LEAD_OVERRIDE_MAX_DISTANCE and
      float(getattr(lead, "vLead", float("inf"))) < self.STANDSTILL_LEAD_OVERRIDE_MAX_SPEED
    )
    if close_stopped_lead:
      if self.close_stopped_lead_since == 0.0:
        self.close_stopped_lead_since = now
      if (now - self.close_stopped_lead_since) >= self.STANDSTILL_LEAD_OVERRIDE_PERSIST_TIME:
        return False
    else:
      self.close_stopped_lead_since = 0.0

    return bool(self.stop_light_detected or force_stop_active or model_stopped)

  def check_conditions(self, v_ego, sm, starpilot_toggles):
    below_speed = starpilot_toggles.conditional_limit > v_ego >= 1 and not self.starpilot_planner.starpilot_following.following_lead
    below_speed_with_lead = starpilot_toggles.conditional_limit_lead > v_ego >= 1 and self.starpilot_planner.starpilot_following.following_lead
    if below_speed or below_speed_with_lead:
      self.status_value = CEStatus["SPEED"]
      return True

    desired_lane = self.starpilot_planner.lane_width_left if sm["carState"].leftBlinker else self.starpilot_planner.lane_width_right
    lane_available = desired_lane >= starpilot_toggles.lane_detection_width or not starpilot_toggles.conditional_signal_lane_detection
    if v_ego < starpilot_toggles.conditional_signal and (sm["carState"].leftBlinker or sm["carState"].rightBlinker) and not lane_available:
      self.status_value = CEStatus["SIGNAL"]
      return True

    if starpilot_toggles.conditional_curves and self.curve_detected and (starpilot_toggles.conditional_curves_lead or not self.starpilot_planner.starpilot_following.following_lead):
      self.status_value = CEStatus["CURVATURE"]
      return True

    if starpilot_toggles.conditional_lead and self.slow_lead_detected and v_ego <= 35.31:
      self.status_value = CEStatus["LEAD"]
      return True

    if starpilot_toggles.conditional_model_stop_time != 0 and self.stop_light_detected:
      self.status_value = CEStatus["STOP_LIGHT"]
      return True

    if self.starpilot_planner.starpilot_vcruise.slc.experimental_mode:
      self.status_value = CEStatus["SPEED_LIMIT"]
      return True

    return False

  def update_conditions(self, v_ego, sm, starpilot_toggles):
    self.curve_detection(v_ego, starpilot_toggles)
    self.slow_lead(starpilot_toggles, v_ego)
    self.stop_sign_and_light(v_ego, sm, starpilot_toggles.conditional_model_stop_time)

  def curve_detection(self, v_ego, starpilot_toggles):
    self.curvature_filter.update(self.starpilot_planner.road_curvature_detected or self.starpilot_planner.driving_in_curve)
    self.curve_detected = bool(self.curvature_filter.x >= THRESHOLD and v_ego > CRUISING_SPEED)

  def slow_lead(self, starpilot_toggles, v_ego):
    now = time.monotonic()
    lead = self.starpilot_planner.lead_one
    tracking_lead = bool(getattr(self.starpilot_planner, "tracking_lead", False))
    lead_status = bool(getattr(lead, "status", False))
    lead_distance = float(getattr(lead, "dRel", float("inf")))
    lead_speed = float(getattr(lead, "vLead", float("inf")))
    lead_prob = float(getattr(lead, "modelProb", 1.0))
    closing_speed = max(0.0, v_ego - lead_speed)
    min_closing_speed = max(self.SLOW_LEAD_MIN_CLOSING_SPEED, 0.04 * v_ego)

    if not starpilot_toggles.conditional_stopped_lead and v_ego < self.SLOW_LEAD_CONTINUITY_MIN_EGO:
      self.clear_slow_lead_state(tracking_lead)
      return

    slower_lead = starpilot_toggles.conditional_slower_lead and self.starpilot_planner.starpilot_following.slower_lead
    stopped_lead = bool(
      starpilot_toggles.conditional_stopped_lead and
      lead_status and
      lead_speed < 1 and
      lead_distance < max(40.0, v_ego * self.SLOW_LEAD_CONTINUITY_MAX_DISTANCE_TIME)
    )
    vision_slow_lead_candidate = bool(
      lead_status and
      lead_prob >= self.SLOW_LEAD_CONTINUITY_MIN_MODEL_PROB and
      lead_distance < max(40.0, v_ego * self.SLOW_LEAD_CONTINUITY_MAX_DISTANCE_TIME) and
      closing_speed >= min_closing_speed and
      lead_speed < max(v_ego - 0.5, 2.0)
    )

    lead_threshold = scale_threshold(v_ego)
    adjusted_threshold = lead_threshold * (1.0 + 0.2 * (1.0 - lead_prob))  # Higher threshold for lower confidence

    if lead_status and not slower_lead and not stopped_lead and closing_speed < (min_closing_speed * self.SLOW_LEAD_CLEAR_FASTER_FACTOR):
      self.clear_slow_lead_state(tracking_lead)
      return

    if tracking_lead and (slower_lead or stopped_lead or vision_slow_lead_candidate):
      self.slow_lead_continuity_until = now + self.SLOW_LEAD_CONTINUITY_HOLD_TIME
    elif self.prev_tracking_lead and not tracking_lead and self.slow_lead_detected and vision_slow_lead_candidate:
      self.slow_lead_continuity_until = now + self.SLOW_LEAD_CONTINUITY_HOLD_TIME

    raw_vision_slow_lead = bool(
      starpilot_toggles.conditional_slower_lead and
      not tracking_lead and
      now < self.slow_lead_continuity_until and
      vision_slow_lead_candidate
    )

    slow_lead_active = bool(slower_lead or raw_vision_slow_lead or stopped_lead)
    if slow_lead_active:
      self.slow_lead_clear_since = 0.0
      self.slow_lead_filter.update(True)
      self.slow_lead_detected = bool(self.slow_lead_filter.x >= adjusted_threshold)
    elif tracking_lead:
      if self.slow_lead_clear_since == 0.0:
        self.slow_lead_clear_since = now

      if (now - self.slow_lead_clear_since) >= self.SLOW_LEAD_FORCE_CLEAR_TIME:
        self.clear_slow_lead_state(tracking_lead)
      else:
        self.slow_lead_filter.update(False)
        self.slow_lead_detected = bool(self.slow_lead_filter.x >= adjusted_threshold)
    else:
      self.clear_slow_lead_state(tracking_lead)

    self.prev_tracking_lead = tracking_lead

  def clear_slow_lead_state(self, tracking_lead):
    self.slow_lead_filter.update(False)
    self.slow_lead_detected = False
    self.slow_lead_clear_since = 0.0
    self.slow_lead_continuity_until = 0.0
    self.prev_tracking_lead = tracking_lead

  def stop_sign_and_light(self, v_ego, sm, model_time):
    now = time.monotonic()

    # While the dashboard has confirmed a stop sign on this approach, pin CEM in EXP.
    # Approaches routinely exceed the mode_hold_until/mode_false_since hysteresis (0.5s/0.25s),
    # so without this the model briefly losing the sign drops CEM to CHILL and stalls the
    # force-stop activation path. Latch is owned by starpilot_vcruise.
    if getattr(self.starpilot_planner.starpilot_vcruise, 'stop_sign_confirmed', False):
      self.stop_light_filter.x = 1.0
      self.stop_light_detected = True
      return

    if not sm["starpilotCarState"].trafficModeEnabled:
      speed_mph = v_ego * CV.MS_TO_MPH  # Convert m/s to mph

      # Interp for smooth scaling in 35-45 mph
      bp = [0, 35, 45]
      low_filter_time = 0.0  # No filtering under 35 mph
      tuned_filter_time_curves = self.FILTER_TIME_CURVES[1]  # At 35-55 mph
      tuned_filter_time_leads = self.FILTER_TIME_LEADS[1]
      tuned_filter_time_lights = self.FILTER_TIME_LIGHTS[1]
      low_boost = 1.0
      tuned_boost = self.LIGHT_BOOSTS[1]
      low_cap_factor = 0.0  # No cap under 35 mph
      tuned_cap_factor = 1.0

      filter_time_curves = interp(speed_mph, bp, [low_filter_time, low_filter_time, tuned_filter_time_curves])
      filter_time_leads = interp(speed_mph, bp, [low_filter_time, low_filter_time, tuned_filter_time_leads])
      filter_time_lights = interp(speed_mph, bp, [self.LOW_SPEED_LIGHT_FILTER_TIME, self.LOW_SPEED_LIGHT_FILTER_TIME, tuned_filter_time_lights])
      lead_clear_filter_time = interp(speed_mph, bp, [self.LEAD_CLEAR_FILTER_TIME_LOW, self.LEAD_CLEAR_FILTER_TIME_LOW, self.LEAD_CLEAR_FILTER_TIME_HIGH])
      light_boost = interp(speed_mph, bp, [low_boost, low_boost, tuned_boost])
      cap_factor = interp(speed_mph, bp, [low_cap_factor, low_cap_factor, tuned_cap_factor])

      # Update filter times with interp
      self.curvature_filter.update_alpha(filter_time_curves)
      self.slow_lead_filter.update_alpha(filter_time_leads)
      self.stop_light_filter.update_alpha(filter_time_lights)
      self.lead_clear_filter.update_alpha(lead_clear_filter_time)

      # Disable stoplight detection at very high speeds to prevent false positives
      if speed_mph > 75:  # Disable above 75 mph
        self.stop_light_filter.x = 0
        self.stop_light_detected = False
        self.stop_light_model_detected = False
        self.stop_light_detected_hold_until = 0.0
        self.lead_clear_filter.x = 0
        return

      # Adjust model time with interp boost and gradual cap
      adjusted_model_time = model_time * light_boost
      if cap_factor > 0:
        adjusted_model_time = min(adjusted_model_time, self.LIGHT_MAX_TIME * cap_factor + model_time * (1 - cap_factor))  # Gradual cap

      stop_threshold = max(v_ego * adjusted_model_time, 0.0)
      if self.stop_light_model_detected:
        model_stopping = self.starpilot_planner.model_length < stop_threshold + self.STOP_LIGHT_OFF_MARGIN
      else:
        model_stopping = self.starpilot_planner.model_length < max(stop_threshold - self.STOP_LIGHT_ON_MARGIN, 0.0)
      self.stop_light_model_detected = model_stopping

      # `model_stopped` is a coarse horizon-length check (< 50 m with current constants)
      # used elsewhere for force-stop/green-light behavior. Reusing it here causes
      # ordinary low-speed cruising to look like a stop prediction and can latch the
      # STOP_LIGHT CEM trigger. For the CEM detector, key strictly off the configured
      # "predicted stop within N seconds" threshold.
      # Key off relevant raw lead presence, not trackingLead. Vision-only GM can
      # flap trackingLead around the model-length threshold while leadOne remains
      # present; far/stale leads should not suppress true stop-light detection.
      lead = getattr(self.starpilot_planner, "lead_one", None)
      lead_distance = float(getattr(lead, "dRel", float("inf")))
      lead_speed = float(getattr(lead, "vLead", float("inf")))
      lead_radar = bool(getattr(lead, "radar", False))
      lead_prob = float(getattr(lead, "modelProb", 1.0 if lead_radar else 0.0))
      tracking_lead = bool(self.starpilot_planner.tracking_lead)
      lead_relevant = bool(getattr(lead, "status", False)) and lead_distance < stop_threshold + self.STOP_LIGHT_LEAD_BLOCK_MARGIN
      vision_stop_approach = (
        lead_relevant and
        not lead_radar and
        lead_prob >= self.STOP_APPROACH_MIN_MODEL_PROB and
        lead_speed < self.STOP_APPROACH_MAX_LEAD_SPEED
      )
      stop_approach_hold_active = now < self.stop_approach_hold_until
      trackable_stop_approach = vision_stop_approach and not tracking_lead
      if (self.stop_light_detected or self.stop_light_model_detected or stop_approach_hold_active) and trackable_stop_approach:
        self.stop_approach_hold_until = now + self.STOP_APPROACH_LATCH_TIME
      stop_approach_latched = now < self.stop_approach_hold_until and trackable_stop_approach
      handoff_to_stopped_lead = (
        lead_relevant and
        not tracking_lead and
        (
          (self.stop_light_detected and lead_speed < self.STOP_LIGHT_HANDOFF_MAX_LEAD_SPEED) or
          stop_approach_latched
        )
      )
      if handoff_to_stopped_lead:
        lead_cleared = True
      else:
        self.lead_clear_filter.update(not lead_relevant)
        lead_cleared = self.lead_clear_filter.x >= THRESHOLD
      self.stop_light_filter.update(model_stopping and lead_cleared)
      model_detector_active = bool(self.stop_light_filter.x >= THRESHOLD**2 and lead_cleared)
      detector_active = bool(model_detector_active or handoff_to_stopped_lead or stop_approach_latched)
      model_hold_qualifies = bool(
        self.starpilot_planner.model_stopped or
        self.starpilot_planner.model_length < max(stop_threshold - self.STOP_LIGHT_MODEL_HOLD_STRONG_MARGIN, 0.0)
      )
      if model_detector_active and model_hold_qualifies:
        self.stop_light_detected_hold_until = now + self.STOP_LIGHT_DETECTED_HOLD_TIME

      hold_context_ok = bool((not lead_relevant) or trackable_stop_approach)
      self.stop_light_detected = bool(
        detector_active or
        (hold_context_ok and now < self.stop_light_detected_hold_until)
      )
    else:
      self.stop_light_filter.x = 0
      self.stop_light_detected = False
      self.stop_light_model_detected = False
      self.stop_light_detected_hold_until = 0.0
      self.lead_clear_filter.x = 0
      self.stop_approach_hold_until = 0.0
