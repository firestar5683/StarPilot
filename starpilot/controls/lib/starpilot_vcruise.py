#!/usr/bin/env python3
import json
import math

from openpilot.common.constants import CV
from openpilot.common.realtime import DT_MDL

from openpilot.starpilot.common.starpilot_variables import CITY_SPEED_LIMIT, CRUISING_SPEED
from openpilot.starpilot.controls.lib.curve_speed_controller import CurveSpeedController, is_manual_speed_control
from openpilot.starpilot.controls.lib.speed_limit_controller import SpeedLimitController
from openpilot.starpilot.system.uniden_shm import get_shm_param
from openpilot.selfdrive.controls.lib.longitudinal_vehicle_tunes import (
  get_force_stop_distance_bias,
  get_force_stop_handoff_distance,
  get_force_stop_low_speed_hold,
  get_force_stop_reanchor_speed_tolerance,
)

CSC_MIN_SPEED = CITY_SPEED_LIMIT * CV.MPH_TO_MS
CSC_CURVE_RELEASE_HOLD_TIME = 0.75
OVERRIDE_FORCE_STOP_TIMER = 10
STANDSTILL_FORCE_STOP_CLEAR_TIME = 0.75
# Open-loop — green is undetectable at standstill, so this only needs to cover the
# handoff to CEM+model ownership. Extra seconds are pure departure lag.
STANDSTILL_FORCE_STOP_LIGHT_HOLD_TIME = 2.0
FORCE_STOP_LIGHT_CLEAR_TIME = 0.5
SLC_LEAD_DROP_RELAXATION_MIN_SPEED = 20.0 * CV.MPH_TO_MS
SLC_LEAD_DROP_RELAXATION_MIN_DISTANCE = 30.0
SLC_LEAD_DROP_RELAXATION_MIN_HEADWAY = 1.2
SLC_LEAD_DROP_RELAXATION_MAX_POST_DROP_CLOSING_SPEED = 0.35
SLC_LEAD_DROP_RELAXATION_MAX_LEAD_BRAKE = 0.25
SLC_LEAD_DROP_RELAXATION_OVERSPEED_BP = [0.0, 5.0 * CV.MPH_TO_MS, 10.0 * CV.MPH_TO_MS, 15.0 * CV.MPH_TO_MS]
SLC_LEAD_DROP_RELAXATION_DECEL_V = [0.7, 0.9, 1.15, 1.35]
NAV_TURN_COMFORT_DECEL = 1.25
NAV_TURN_DISTANCE_BUFFER = 8.0
NAV_TURN_MIN_TARGET_DELTA = 0.25
NAV_TURN_TARGET_SPEEDS = {
  "uturn": 5.0 * CV.MPH_TO_MS,
  "sharpLeft": 10.0 * CV.MPH_TO_MS,
  "sharpRight": 10.0 * CV.MPH_TO_MS,
  "left": 14.0 * CV.MPH_TO_MS,
  "right": 14.0 * CV.MPH_TO_MS,
}

# Force-stop kinematic profile. The user tunes one signed knob (ForceStopDistanceOffset,
# in feet); positive = stop later/longer, negative = stop sooner/shorter.
# Smaller values pull speed down earlier on approach.
FORCE_STOP_MODEL_APPROACH_DECEL = 0.65
FORCE_STOP_DASH_APPROACH_DECEL = 1.0
ACTIVATION_M = 100.0      # m — CEM/model path activates when model_length < this. Buys
                          # ~1.8 s more runway inside the position constraint, which is the
                          # only part of the approach that tracks without lag. A false arm
                          # off a brief red blip is driver-cancellable: gas suppresses force
                          # stop for OVERRIDE_FORCE_STOP_TIMER seconds.
ACTIVATION_HYSTERESIS_M = 8.0  # m — release margin; absorbs model_length jitter at the gate
LEAD_VETO_M = 75.0        # m — lead proximity that vetoes Force Stop (kept off ACTIVATION_M
                          # so raising activation can't silently widen the veto)
LEAD_VETO_M_OVERRIDES = {
  "HYUNDAI_ELANTRA_2021": 90.0,
}
FORCE_STOP_APPROACH_DECEL = 0.65  # m/s^2 — speed ceiling before commit. LOWER = more early
                          # braking; don't go under FORCE_STOP_MODEL_APPROACH_DECEL
# approachStopLength is published RAW: model_length converges from above, so rate-limiting
# it inward freezes it far out and the constraint never binds. Tried, measured, don't re-add.
ADAS_MAX_MS = 17.88       # 40 mph — cross-street ADAS guard
DASH_SEED_M = 27.0        # ~88 ft — typical ADAS detection distance, used to snap
                          # tracked length closer when dashboard confirms a sign
DASH_MODEL_AGREE_M = 50.0 # m — dash arm/snap needs model_length under this; a lone dash bit
                          # against a long model path is a phantom stop
FT_TO_M = 0.3048
ADJACENT_STOP_MIN_USE_M = 10.0  # m — inside this the MPC already owns the stop; a
                                # late-arriving hint could only jerk it
FORCE_STOP_TURN_VETO_MAX_SPEED = 18.0 * CV.MPH_TO_MS
# Real-turn steering angle. A stop-then-turn is still ~straight on approach, so a low
# threshold caused legit stops to be skipped when the blinker came on early. Only suppress
# Force Stop once the wheel is actually wound into the turn (turn instead of stop), and only
# for *new* activation — an in-progress stop is carried through (see force_stop_timer logic).
FORCE_STOP_TURN_VETO_STEERING_ANGLE = 25.0
FORCE_STOP_CURVE_VETO_MAX_ROAD_CURVATURE = 0.003
FORCE_STOP_TURN_VETO_STOP_SEEN_HOLD_TIME = 4.0
FORCE_STOP_DISTANCE_REANCHOR_MIN_GAP = 3.0  # m — ignore small model-horizon noise
FORCE_STOP_REANCHOR_MIN_M = 40.0  # m — inside this only ratchet down; shouldStop doesn't
                          # assert until ~10 m, so horizon jitter would release the stop
FORCE_STOP_CAP_SLACK_M = 15.0  # m — the line can't move away, so tracked can never exceed
                          # what it was at commit minus distance driven. Slack covers an
                          # under-read at commit; without it that would stop us short.
FORCE_STOP_CAP_TAPER_M = 60.0  # m — slack fades to 0 as the cap closes. The solver aims at
                          # tracked, so slack held near the line is braking for a stop bar
                          # that far past the real one.

# Knob bounds (mirror of UI slider; defense in depth)
OFFSET_FT_MIN = -20
OFFSET_FT_MAX = 20


def get_lead_veto_distance(car_params):
  fingerprint = str(getattr(car_params, "carFingerprint", ""))
  return LEAD_VETO_M_OVERRIDES.get(fingerprint, LEAD_VETO_M)


def get_active_slc_control_target(speed_limit_controller, set_speed_limit, slc_target, slc_offset, overridden_speed,
                                  v_ego_diff, allow_lower_override=False):
  # `SetSpeedLimit` only controls engage-time set-speed initialization. Ongoing
  # SLC speed matching must remain active whenever Speed Limit Controller is on.
  if not speed_limit_controller:
    return 0.0

  if allow_lower_override and overridden_speed > 0:
    base_target = float(overridden_speed)
  else:
    base_target = max(float(overridden_speed), float(slc_target) + float(slc_offset))
  if base_target <= 0.0:
    return 0.0

  return max(0.0, base_target - float(v_ego_diff))


def _interp_linear(x, xp, fp):
  if x <= xp[0]:
    return fp[0]
  if x >= xp[-1]:
    return fp[-1]

  for i in range(1, len(xp)):
    if x <= xp[i]:
      span = xp[i] - xp[i - 1]
      if span <= 0.0:
        return fp[i]
      ratio = (x - xp[i - 1]) / span
      return fp[i - 1] + ratio * (fp[i] - fp[i - 1])

  return fp[-1]


def get_slc_lead_drop_relaxed_target(raw_target, previous_target, v_ego, tracking_lead, lead, override_active, source):
  if (
    raw_target <= 0.0 or
    previous_target <= 0.0 or
    override_active or
    source == "None" or
    not tracking_lead or
    lead is None or
    not getattr(lead, "status", False)
  ):
    return raw_target

  if (
    raw_target >= previous_target - 1e-3 or
    v_ego < SLC_LEAD_DROP_RELAXATION_MIN_SPEED or
    raw_target >= v_ego - 0.05
  ):
    return raw_target

  d_rel = float(getattr(lead, "dRel", 0.0))
  if d_rel < max(SLC_LEAD_DROP_RELAXATION_MIN_DISTANCE, float(v_ego) * SLC_LEAD_DROP_RELAXATION_MIN_HEADWAY):
    return raw_target

  v_lead = float(getattr(lead, "vLead", 0.0))
  if v_lead < float(raw_target) - SLC_LEAD_DROP_RELAXATION_MAX_POST_DROP_CLOSING_SPEED:
    return raw_target

  lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
  if lead_brake > SLC_LEAD_DROP_RELAXATION_MAX_LEAD_BRAKE:
    return raw_target

  overspeed = max(0.0, float(v_ego) - float(raw_target))
  comfort_decel = _interp_linear(overspeed, SLC_LEAD_DROP_RELAXATION_OVERSPEED_BP, SLC_LEAD_DROP_RELAXATION_DECEL_V)
  return max(float(raw_target), float(previous_target) - comfort_decel * DT_MDL)


class StarPilotVCruise:
  def __init__(self, StarPilotPlanner):
    self.starpilot_planner = StarPilotPlanner

    self.csc = CurveSpeedController(self)
    self.slc = SpeedLimitController(self)

    self.forcing_stop = False
    self.override_force_stop = False
    self.override_force_standstill = False

    self.override_force_stop_timer = 0
    self.force_stop_timer = 0.0
    self.force_stop_entry_speed = None
    self.activation_gate_active = False
    self.standstill_force_stop_hold = False
    self.standstill_force_stop_clear_since = 0.0
    self.standstill_force_stop_started_at = None
    self.standstill_force_stop_reason = None
    self.force_stop_from_light = False
    self.force_stop_light_clear_since = None
    self.controls_enabled_previously = False
    self.approach_stop_length = 0.0  # published as starpilotPlan.approachStopLength
    # Kinematic distance estimator. Same attribute also published as
    # starpilotPlan.forcingStopLength, so the existing reader keeps working.
    self.tracked_model_length = 0.0
    self.force_stop_distance_cap = 0.0  # odometry ceiling, re-seeded until commit

    self.stop_sign_confirmed = False
    self.stop_seen_on_approach_at = None
    self.nav_turn_target = 0.0
    self._nav_instruction_state_raw = None
    self._nav_instruction_state = {}
    self._applied_slc_control_target = 0.0
    self.csc_controlling_speed = False
    self.csc_target = 0.0
    self.csc_curve_last_seen_at = None

  def _update_nav_instruction_state(self):
    raw = self.starpilot_planner.params_memory.get("NavInstructionState") or {}
    if raw == self._nav_instruction_state_raw:
      return

    self._nav_instruction_state_raw = raw
    if not raw:
      self._nav_instruction_state = {}
      return

    if isinstance(raw, dict):
      self._nav_instruction_state = raw
      return

    if isinstance(raw, str):
      try:
        parsed = json.loads(raw)
        self._nav_instruction_state = parsed if isinstance(parsed, dict) else {}
        return
      except Exception:
        pass

    self._nav_instruction_state = {}

  @staticmethod
  def _elapsed_seconds(now, since):
    delta = now - since
    return delta.total_seconds() if hasattr(delta, "total_seconds") else float(delta)

  def _clear_standstill_force_stop_hold(self):
    self.standstill_force_stop_hold = False
    self.standstill_force_stop_clear_since = 0.0
    self.standstill_force_stop_started_at = None
    self.standstill_force_stop_reason = None

  @staticmethod
  def _get_adjacent_stop_distance(sm):
    """dRel of a vehicle that decelerated to a stop in an adjacent lane, or None.

    The model's own distance runs long on a clear-lane approach; a car stopped alongside
    is physically at (or just behind) the stop bar. Radar-only, so it holds for any
    driving model.
    """
    try:
      radar_state = sm["starpilotRadarState"]
    except (KeyError, IndexError, TypeError, AttributeError):
      return None

    adjacent = getattr(radar_state, "adjacentStopped", None)
    if adjacent is None or not getattr(adjacent, "status", False):
      return None

    d_rel = float(getattr(adjacent, "dRel", 0.0))
    return d_rel if d_rel > ADJACENT_STOP_MIN_USE_M else None

  @staticmethod
  def _nav_maneuver_target_speed(maneuver_type, maneuver_modifier):
    maneuver_type = str(maneuver_type or "").strip().lower()
    maneuver_modifier = str(maneuver_modifier or "").strip()

    if not maneuver_modifier and not maneuver_type:
      return None

    if maneuver_modifier == "uturn" or "uturn" in maneuver_type or "u-turn" in maneuver_type:
      return NAV_TURN_TARGET_SPEEDS["uturn"]

    if "roundabout" in maneuver_type or "rotary" in maneuver_type:
      return 12.0 * CV.MPH_TO_MS

    if maneuver_type == "turn":
      return NAV_TURN_TARGET_SPEEDS.get(maneuver_modifier)

    return None

  @staticmethod
  def _nav_target_for_distance(target_speed, maneuver_distance):
    try:
      remaining_distance = max(float(maneuver_distance) - NAV_TURN_DISTANCE_BUFFER, 0.0)
    except (TypeError, ValueError):
      return 0.0

    return math.sqrt(max(target_speed * target_speed + (2.0 * NAV_TURN_COMFORT_DECEL * remaining_distance), 0.0))

  @staticmethod
  def _get_nav_long_min_target_speed(sm):
    car_params = None
    try:
      car_params = sm["carParams"]
    except Exception:
      if hasattr(sm, "get"):
        car_params = sm.get("carParams")
    return max(float(getattr(car_params, "minSteerSpeed", 0.0) or 0.0), 0.0)

  def _get_nav_turn_control_target(self, v_cruise, sm, starpilot_toggles):
    self._update_nav_instruction_state()
    if not getattr(starpilot_toggles, "nav_longitudinal_allowed", False):
      return 0.0
    if not bool(self._nav_instruction_state.get("valid", False)):
      return 0.0

    nav_long_min_target_speed = self._get_nav_long_min_target_speed(sm)

    candidates = [
      (
        self._nav_instruction_state.get("maneuverType"),
        self._nav_instruction_state.get("maneuverModifier"),
        self._nav_instruction_state.get("maneuverDistance"),
      ),
      (
        self._nav_instruction_state.get("nextManeuverType"),
        self._nav_instruction_state.get("nextManeuverModifier"),
        self._nav_instruction_state.get("nextManeuverDistance"),
      ),
    ]
    for maneuver_type, maneuver_modifier, maneuver_distance in candidates:
      target_speed = self._nav_maneuver_target_speed(maneuver_type, maneuver_modifier)
      if target_speed is None:
        continue
      target_speed = max(target_speed, nav_long_min_target_speed)

      target = max(target_speed, self._nav_target_for_distance(target_speed, maneuver_distance))
      if target + NAV_TURN_MIN_TARGET_DELTA < v_cruise:
        return target

    return 0.0

  # ===== Main update =====

  def update(self, controls_enabled, now, time_validated, v_cruise, v_ego, sm, starpilot_toggles):
    if not controls_enabled or not getattr(starpilot_toggles, "speed_limit_controller", False):
      self._applied_slc_control_target = 0.0

    long_control_active = sm["carControl"].longActive
    force_stop_handoff_m = get_force_stop_handoff_distance(
      getattr(starpilot_toggles, "car_model", "")
    )
    force_stop_distance_bias_m = get_force_stop_distance_bias(
      getattr(starpilot_toggles, "car_model", "")
    )

    raw_stop_seen = bool(
      self.starpilot_planner.starpilot_cem.stop_light_detected
      or getattr(self.starpilot_planner, "raw_model_stopped", False)
      or sm["starpilotCarState"].dashboardStopSign > 0
    )
    if raw_stop_seen and not sm["carState"].standstill:
      self.stop_seen_on_approach_at = now
    elif sm["carState"].standstill:
      self.stop_seen_on_approach_at = None
    stop_then_turn = (
      self.stop_seen_on_approach_at is not None
      and self._elapsed_seconds(now, self.stop_seen_on_approach_at) < FORCE_STOP_TURN_VETO_STOP_SEEN_HOLD_TIME
    )

    turn_scene_active = bool(
      v_ego <= FORCE_STOP_TURN_VETO_MAX_SPEED and
      (getattr(sm["carState"], "leftBlinker", False) or getattr(sm["carState"], "rightBlinker", False)) and
      abs(float(getattr(sm["carState"], "steeringAngleDeg", 0.0))) >= FORCE_STOP_TURN_VETO_STEERING_ANGLE and
      not stop_then_turn
    )

    # ----- Activation paths -----
    # Raw lead check: block Force Stop as soon as a relevant lead is present, without
    # waiting for the tracking_lead filter (~1s ramp). Without this, Force Stop can latch
    # during the filter's settling window and stay committed for the whole stop.
    lead = self.starpilot_planner.lead_one
    try:
      car_params = sm["carParams"]
    except (KeyError, IndexError, TypeError, AttributeError):
      car_params = None
    force_stop_reanchor_speed_tolerance = get_force_stop_reanchor_speed_tolerance(car_params)
    force_stop_low_speed_hold = get_force_stop_low_speed_hold(car_params)
    lead_veto_m = get_lead_veto_distance(car_params)
    lead_present = (bool(getattr(lead, "status", False))
                    and float(getattr(lead, "dRel", float("inf"))) < lead_veto_m
                    and float(getattr(lead, "vLead", float("inf"))) < v_ego + 2.0)
    curved_approach_scene = (
      abs(float(getattr(self.starpilot_planner, "road_curvature", 0.0))) >= FORCE_STOP_CURVE_VETO_MAX_ROAD_CURVATURE
      and not stop_then_turn
    )

    # CEM/model path: model predicted stop within ACTIVATION_M.
    # Exclude when a lead is present (raw or filtered) — the handoff_to_stopped_lead path
    # in CEM can set stop_light_detected even with a lead present, which would incorrectly
    # activate Force Stop and stop the car far behind the lead instead of letting ACC handle it.
    # Schmitt trigger: model_length jitters around ACTIVATION_M and keeps resetting
    # force_stop_timer's ramp. Scoped to a detected stop so the wider release threshold
    # can't leak into ordinary slow driving.
    stop_light_detected = self.starpilot_planner.starpilot_cem.stop_light_detected
    if self.activation_gate_active and stop_light_detected:
      model_length_active = self.starpilot_planner.model_length < ACTIVATION_M + ACTIVATION_HYSTERESIS_M
    else:
      model_length_active = self.starpilot_planner.model_length < ACTIVATION_M
    self.activation_gate_active = model_length_active and stop_light_detected

    cem_path = (stop_light_detected
                and controls_enabled and starpilot_toggles.force_stops
                and model_length_active
                and self.override_force_stop_timer <= 0
                and not self.starpilot_planner.driving_in_curve
                and not curved_approach_scene
                and not turn_scene_active
                and not self.starpilot_planner.tracking_lead
                and not lead_present)

    # Dashboard path: ADAS camera confirms a stop sign on our road. Field is 0 on
    # platforms that don't publish ADAS_0x380, so dash_path is naturally inert there.
    dash_value = sm["starpilotCarState"].dashboardStopSign
    dash_active = dash_value > 0
    dash_path = (dash_active and controls_enabled and starpilot_toggles.force_stops
                 and v_ego < ADAS_MAX_MS
                 and self.starpilot_planner.model_length < DASH_MODEL_AGREE_M
                 and self.override_force_stop_timer <= 0
                 and not self.starpilot_planner.driving_in_curve
                 and not turn_scene_active
                 and not self.starpilot_planner.tracking_lead
                 and not lead_present)

    force_stop_active = cem_path or dash_path

    if cem_path:
      self.force_stop_from_light = True
      self.force_stop_light_clear_since = None
    elif not self.forcing_stop:
      self.force_stop_from_light = False
      self.force_stop_light_clear_since = None

    # Latch on first dash frame so the CEM pin can fire and we don't release on
    # transient dashboard dropouts. Cleared in the no-force-stop branch below.
    if dash_path:
      self.stop_sign_confirmed = True

    raw_model_stopped = bool(getattr(self.starpilot_planner, "raw_model_stopped", False))
    standstill_force_stop_scene_active = bool(force_stop_active or raw_model_stopped)
    standstill = bool(sm["carState"].standstill)
    engaged_at_standstill = controls_enabled and not self.controls_enabled_previously and standstill

    # Stop signs remain latched until the driver resumes. A light hold is only
    # seeded on the engagement edge; otherwise the expired Force Stop would
    # immediately re-arm itself from the still-short model trajectory.
    stop_sign_hold_requested = controls_enabled and standstill and self.stop_sign_confirmed
    light_hold_requested = engaged_at_standstill and standstill_force_stop_scene_active and not self.stop_sign_confirmed
    if stop_sign_hold_requested and self.standstill_force_stop_reason != "sign":
      self.standstill_force_stop_hold = True
      self.standstill_force_stop_clear_since = 0.0
      self.standstill_force_stop_started_at = now
      self.standstill_force_stop_reason = "sign"
      self.tracked_model_length = 0.0
    elif light_hold_requested and not self.standstill_force_stop_hold:
      self.standstill_force_stop_hold = True
      self.standstill_force_stop_clear_since = 0.0
      self.standstill_force_stop_started_at = now
      self.standstill_force_stop_reason = "light"
      self.tracked_model_length = 0.0

    if self.standstill_force_stop_hold:
      pedal_override = bool(sm["carState"].gasPressed or sm["starpilotCarState"].accelPressed)
      light_hold_expired = (
        self.standstill_force_stop_reason == "light" and
        self.standstill_force_stop_started_at is not None and
        self._elapsed_seconds(now, self.standstill_force_stop_started_at) >= STANDSTILL_FORCE_STOP_LIGHT_HOLD_TIME
      )
      if pedal_override:
        self.override_force_stop_timer = OVERRIDE_FORCE_STOP_TIMER
      elif light_hold_expired:
        self.override_force_stop_timer = OVERRIDE_FORCE_STOP_TIMER
      if (not controls_enabled) or (not standstill) or lead_present or pedal_override or light_hold_expired:
        self._clear_standstill_force_stop_hold()
      elif standstill_force_stop_scene_active:
        self.standstill_force_stop_clear_since = 0.0
      elif self.standstill_force_stop_clear_since == 0.0:
        self.standstill_force_stop_clear_since = now
      elif self._elapsed_seconds(now, self.standstill_force_stop_clear_since) >= STANDSTILL_FORCE_STOP_CLEAR_TIME:
        self._clear_standstill_force_stop_hold()

    # Timer ramp. Faster commitment when the dashboard confirms.
    if force_stop_active and not sm["carState"].standstill:
      rate = DT_MDL * 2 if dash_active else DT_MDL
      self.force_stop_timer = min(self.force_stop_timer + rate, 2.0)
    elif turn_scene_active and not self.forcing_stop and not sm["carState"].standstill:
      # Suppress only a *new* stop while turning. If we're already forcing a stop
      # (stop-then-turn), carry it through to the stop line instead of releasing here.
      self.force_stop_timer = 0.0
    elif self.standstill_force_stop_hold:
      self.force_stop_timer = max(self.force_stop_timer, 0.5)
    elif (self.forcing_stop and sm["carState"].standstill and not dash_active and
          not self.starpilot_planner.starpilot_cem.stop_light_detected and not raw_model_stopped):
      self.force_stop_timer = 0.0
    else:
      self.force_stop_timer = max(self.force_stop_timer - DT_MDL * 0.25, 0.0)

    force_stop_enabled = self.force_stop_timer >= 0.5
    # Stay committed across model dropouts until standstill. Signaling a turn does not
    # abandon a stop already in progress — we bring the car to the stop line, then turn.
    force_stop_enabled |= self.forcing_stop and not sm["carState"].standstill
    force_stop_enabled |= self.standstill_force_stop_hold

    light_stop_cleared = (
      self.forcing_stop and
      self.force_stop_from_light and
      not sm["carState"].standstill and
      not stop_light_detected and
      not dash_active
    )
    low_speed_stop_commit = bool(
      light_stop_cleared and
      force_stop_low_speed_hold is not None and
      self.force_stop_entry_speed is not None and
      v_ego <= force_stop_low_speed_hold and
      v_ego < self.force_stop_entry_speed - 0.25
    )
    # The Santa Fe's model stop signal can blink off after the car has already
    # committed to the stop. Do not turn that late dropout into a throttle
    # release while the vehicle is still rolling through the sign.
    light_stop_cleared &= not low_speed_stop_commit
    if light_stop_cleared:
      if self.force_stop_light_clear_since is None:
        self.force_stop_light_clear_since = now
      elif self._elapsed_seconds(now, self.force_stop_light_clear_since) >= FORCE_STOP_LIGHT_CLEAR_TIME:
        self.forcing_stop = False
        self.force_stop_from_light = False
        self.force_stop_light_clear_since = None
        self.force_stop_timer = 0.0
        force_stop_enabled = False
    else:
      self.force_stop_light_clear_since = None

    if self.forcing_stop and standstill and not force_stop_enabled and self.standstill_force_stop_reason != "sign":
      self.override_force_stop_timer = OVERRIDE_FORCE_STOP_TIMER

    # Override: gas/accel pedal during an active force stop
    self.override_force_stop |= sm["carState"].gasPressed
    self.override_force_stop |= sm["starpilotCarState"].accelPressed
    self.override_force_stop &= force_stop_enabled

    if self.override_force_stop:
      self.override_force_stop_timer = OVERRIDE_FORCE_STOP_TIMER
    elif self.override_force_stop_timer > 0:
      self.override_force_stop_timer -= DT_MDL

    # ----- Force standstill (independent sibling toggle) -----
    force_standstill_enabled = controls_enabled and starpilot_toggles.force_standstill and sm["carState"].standstill
    if force_standstill_enabled:
      self.override_force_standstill |= sm["carState"].gasPressed
      self.override_force_standstill |= sm["starpilotCarState"].accelPressed
    else:
      self.override_force_standstill = False

    v_cruise_cluster = max(sm["carState"].vCruiseCluster * CV.KPH_TO_MS, v_cruise)
    v_cruise_diff = v_cruise_cluster - v_cruise

    v_ego_cluster = max(sm["carState"].vEgoCluster, v_ego)
    v_ego_diff = v_ego_cluster - v_ego

    # Curve Speed Controller
    following_lead = bool(getattr(self.starpilot_planner.starpilot_following, "following_lead", False))
    manual_speed_control = is_manual_speed_control(sm)
    csc_available = (
      not force_stop_active and
      not self.forcing_stop and
      long_control_active and
      not manual_speed_control and
      v_ego > CRUISING_SPEED and
      starpilot_toggles.curve_speed_controller and
      (not getattr(starpilot_toggles, "csc_no_lead", False) or not following_lead)
    )
    csc_curve_detected = csc_available and self.starpilot_planner.road_curvature_detected
    if csc_curve_detected:
      self.csc.update_target(v_ego)

      self.csc_controlling_speed = True
      self.csc_target = self.csc.target
      self.csc_curve_last_seen_at = now
    else:
      csc_release_hold = bool(
        csc_available and
        self.csc_controlling_speed and
        self.csc_curve_last_seen_at is not None and
        self._elapsed_seconds(now, self.csc_curve_last_seen_at) < CSC_CURVE_RELEASE_HOLD_TIME
      )
      if not csc_release_hold:
        self.csc.log_data(v_ego, sm)

        self.csc_controlling_speed = False
        self.csc.target_set = False
        self.csc_curve_last_seen_at = None

        self.csc_target = v_cruise

    # Pfeiferj's Speed Limit Controller
    self.slc.starpilot_toggles = starpilot_toggles

    if starpilot_toggles.speed_limit_controller:
      self.slc.update_limits(sm["starpilotCarState"].dashboardSpeedLimit, now, time_validated, v_cruise, v_ego, sm)
      self.slc.update_override(v_cruise, v_cruise_diff, v_ego, v_ego_diff, sm)

      self.slc_offset = self.slc.offset
      self.slc_target = self.slc.target
    elif starpilot_toggles.show_speed_limits:
      self.slc.update_limits(sm["starpilotCarState"].dashboardSpeedLimit, now, time_validated, v_cruise, v_ego, sm, display_only=True)

      self.slc_offset = 0
      self.slc_target = self.slc.target
    else:
      self.slc_offset = 0
      self.slc_target = 0

    self.nav_turn_target = self._get_nav_turn_control_target(v_cruise, sm, starpilot_toggles)

    # Single tuning knob (signed feet -> meters). Defense clamp on top of UI bounds.
    offset_ft_raw = int(getattr(starpilot_toggles, 'force_stop_distance_offset', 0) or 0)
    offset_ft = max(OFFSET_FT_MIN, min(OFFSET_FT_MAX, offset_ft_raw))
    offset_m = offset_ft * FT_TO_M

    # cleared on every path; only the far-approach envelope below republishes it
    self.approach_stop_length = 0.0

    if force_standstill_enabled and not self.override_force_standstill:
      self.forcing_stop = True
      self.tracked_model_length = 0.0
      v_cruise = 0.0

    elif force_stop_enabled and not self.override_force_stop:
      if self.force_stop_entry_speed is None and not sm["carState"].standstill:
        self.force_stop_entry_speed = v_ego
      self.forcing_stop |= not sm["carState"].standstill or self.standstill_force_stop_hold

      if self.standstill_force_stop_hold:
        self.tracked_model_length = 0.0
        v_cruise = 0.0
      else:
        # Kinematic distance estimator (also published as forcingStopLength).
        # Decay one-to-one with motion. A force-stop cycle may otherwise retain
        # an old short horizon forever, even after the model has reopened the
        # path. Recover only for the CEM/model path and only when the model's
        # explicit stop action is clear; a committed model stop remains sticky.
        self.tracked_model_length = max(self.tracked_model_length - (v_ego * DT_MDL), 0.0)
        model_length = float(self.starpilot_planner.model_length)
        try:
          model_wants_stop = bool(sm["modelV2"].action.shouldStop)
        except (KeyError, AttributeError, TypeError):
          model_wants_stop = False
        if (
          not dash_active and
          self.tracked_model_length > max(force_stop_handoff_m, FORCE_STOP_REANCHOR_MIN_M) and
          not model_wants_stop and
          model_length > self.tracked_model_length + FORCE_STOP_DISTANCE_REANCHOR_MIN_GAP and
          (
            force_stop_reanchor_speed_tolerance is None or
            self.force_stop_entry_speed is None or
            v_ego >= self.force_stop_entry_speed - force_stop_reanchor_speed_tolerance
          )
        ):
          self.tracked_model_length = model_length
        else:
          self.tracked_model_length = min(self.tracked_model_length, model_length)
        # Odometry ceiling: the line can't recede, so a re-anchor may never exceed what we
        # had at commit minus what we've driven. Bounds a ballooning horizon (seen +95 m)
        # that the REANCHOR_MIN floor can't catch, since that floor trusts the estimate.
        self.force_stop_distance_cap = max(self.force_stop_distance_cap - (v_ego * DT_MDL), 0.0)
        cap_slack = FORCE_STOP_CAP_SLACK_M * min(self.force_stop_distance_cap / FORCE_STOP_CAP_TAPER_M, 1.0)
        self.tracked_model_length = min(self.tracked_model_length, self.force_stop_distance_cap + cap_slack)
        if dash_active:
          if model_length < DASH_MODEL_AGREE_M:
            self.tracked_model_length = min(self.tracked_model_length, DASH_SEED_M)
          # inside the seed the model range is the better line estimate; letting it pull
          # tracked back up is what keeps an early snap from parking us short of the sign
          if model_length < DASH_SEED_M:
            self.tracked_model_length = model_length

        # A car stopped in the next lane marks the stop bar better than the model does.
        # Shortening clamp only — it can pull the stop in, never push it out.
        adjacent_stop_d = self._get_adjacent_stop_distance(sm)
        if adjacent_stop_d is not None:
          self.tracked_model_length = min(self.tracked_model_length, adjacent_stop_d)

        # Kinematic profile with user offset. Positive offset shifts the perceived
        # line further down the road -> car rolls further before commanding 0.
        effective_d = self.tracked_model_length + offset_m + force_stop_distance_bias_m
        if effective_d <= force_stop_handoff_m:
          v_target = 0.0
        else:
          approach_decel = FORCE_STOP_DASH_APPROACH_DECEL if dash_active else FORCE_STOP_MODEL_APPROACH_DECEL
          v_target = math.sqrt(2.0 * approach_decel * (effective_d - force_stop_handoff_m))

        v_cruise = min(v_target, v_cruise)

    else:
      self.forcing_stop = False
      self.force_stop_entry_speed = None
      self._clear_standstill_force_stop_hold()
      # Latch is only meaningful during an active force-stop cycle
      self.stop_sign_confirmed = False

      self.tracked_model_length = self.starpilot_planner.model_length
      self.force_stop_distance_cap = self.tracked_model_length

      targets = [v_cruise]
      if self.csc_target >= CSC_MIN_SPEED:
        targets.append(self.csc_target)
      slc_control_target = get_active_slc_control_target(
        starpilot_toggles.speed_limit_controller,
        getattr(starpilot_toggles, "set_speed_limit", False),
        self.slc_target,
        self.slc_offset,
        self.slc.overridden_speed,
        v_ego_diff,
        allow_lower_override=(getattr(starpilot_toggles, "redneck_cruise", False) and
                              getattr(starpilot_toggles, "speed_limit_controller_override_set_speed", False)),
      )
      slc_control_target = get_slc_lead_drop_relaxed_target(
        slc_control_target,
        self._applied_slc_control_target,
        v_ego,
        bool(getattr(self.starpilot_planner, "tracking_lead", False)),
        getattr(self.starpilot_planner, "lead_one", None),
        self.slc.overridden_speed > 0.0,
        getattr(self.slc, "source", "None"),
      )
      self._applied_slc_control_target = slc_control_target if slc_control_target > 0.0 else 0.0
      if slc_control_target >= CSC_MIN_SPEED:
        targets.append(slc_control_target)

      # Police Threat Auto-Slowdown (Uniden Radar Detector + Waze Crowd-Sourced Police Ahead):
      # If live radar is firing OR a verified Waze police report (hidden/visible, >= 3 confirmations) is ahead,
      # clamp max cruise speed directly down to the road speed limit (ignoring manual set speed overrides).
      radar_alert_active = get_shm_param("UnidenRadarAlertActive", False)
      waze_police_active = get_shm_param("WazePoliceSlowdownActive", False)
      if (radar_alert_active or waze_police_active) and self.slc_target >= CSC_MIN_SPEED:
        targets.append(float(self.slc_target))
      if self.nav_turn_target > 0.0:
        targets.append(self.nav_turn_target)

      # Far-approach envelope: bleed speed off before commit so the car isn't still at
      # cruise when the kinematic curve takes over. Same vetoes as the activation paths;
      # no latch, recomputed each frame, releases on green.
      if (stop_light_detected
          and controls_enabled and starpilot_toggles.force_stops
          and self.override_force_stop_timer <= 0
          and not self.starpilot_planner.driving_in_curve
          and not curved_approach_scene
          and not turn_scene_active
          and not self.starpilot_planner.tracking_lead
          and not lead_present):
        # adjacent-stopped hint caps the model distance; shorten-only, self-clearing
        approach_d = self.starpilot_planner.model_length
        adjacent_stop_d = self._get_adjacent_stop_distance(sm)
        if adjacent_stop_d is not None:
          approach_d = min(approach_d, adjacent_stop_d)
        # pre-offset, so it hands off to forcingStopLength at commit without a step
        self.approach_stop_length = max(approach_d, 0.0)
        approach_d += offset_m + force_stop_distance_bias_m
        if approach_d > force_stop_handoff_m:
          targets.append(math.sqrt(2.0 * FORCE_STOP_APPROACH_DECEL * (approach_d - force_stop_handoff_m)))

      v_cruise = min(targets)

    self.controls_enabled_previously = controls_enabled
    return v_cruise
