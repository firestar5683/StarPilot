#!/usr/bin/env python3
from enum import IntEnum
import math

import numpy as np
import cereal.messaging as messaging
from opendbc.car.interfaces import ACCEL_MIN, ACCEL_MAX

from openpilot.common.constants import CV
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.realtime import DT_MDL
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.car.cruise import V_CRUISE_UNSET
from openpilot.selfdrive.controls.lib.drive_helpers import CONTROL_N
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import (
  STOP_DISTANCE,
  T_IDXS as T_IDXS_MPC,
  LongitudinalMpc,
  should_trigger_planner_fcw,
)
from openpilot.selfdrive.controls.lib.longitudinal_vehicle_tunes import get_longitudinal_planner_tune
from openpilot.selfdrive.modeld.constants import ModelConstants


CONTROL_N_T_IDX = ModelConstants.T_IDXS[:CONTROL_N]
MIN_PLAN_HORIZON = 0.30
A_CRUISE_MAX_BP = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 40.0]
A_CRUISE_MAX_VALS = [1.125, 1.125, 1.125, 1.125, 1.25, 1.25, 1.5]
A_CRUISE_MIN = -1.0

ALLOW_THROTTLE_THRESHOLD = 0.40
ALLOW_THROTTLE_HYSTERESIS = 0.05
ALLOW_THROTTLE_CONFIRM_TIME = 0.25
MIN_ALLOW_THROTTLE_SPEED = 1.5
COAST_TARGET_SPEED = 5.0
COAST_TARGET_GAIN = 0.35

MODEL_STOP_BEGIN_TIME = 9.0
MODEL_STOP_FULL_TIME = 4.0
MODEL_STOP_MIN_END_SPEED = 2.0
MODEL_FIRST_AUTHORITY = 0.75
MODEL_FIRST_OPEN_ROAD_AUTHORITY = 0.35
MODEL_FIRST_CRUISE_ERROR = 1.5
MODEL_SLOWDOWN_MIN_ACCEL = 0.15
MODEL_SLOWDOWN_MIN_SPEED_DROP = 0.75
MODEL_SLOWDOWN_FULL_SPEED_DROP = 3.0
MODEL_SLOWDOWN_MAX_AUTHORITY = 0.65

STOP_ENTER_AUTHORITY = 0.72
STOP_RELEASE_TIME = 0.50
STOPPED_SPEED = 0.15
STOP_CONTROL_SPEED = 1.5
DEPART_COMPLETE_SPEED = 2.5
DEPART_LEAD_MIN_SPEED = 0.10
DEPART_LEAD_FAST_SPEED = 0.75
DEPART_CONFIRM_TIME = 0.20
DEPART_LEAD_MIN_GAP = 0.0
DEPART_MODEL_MIN_ACCEL = 0.08
DEPART_LEAD_MAX_BRAKE = 0.30

RAW_SAFETY_REACTION_BUFFER = 0.20
RAW_SAFETY_MIN_CLOSING_SPEED = 0.25
RAW_SAFETY_MIN_DECEL = 0.20
RAW_SAFETY_URGENT_DECEL = 0.80
RAW_SAFETY_URGENT_TTC = 4.0
RAW_SAFETY_EXTRA_STOP_BUFFER = 1.0

FORCE_STOP_HANDOFF_MAX_VCRUISE = 0.5

_A_TOTAL_MAX_V = [3.5, 3.5, 3.2]
_A_TOTAL_MAX_BP = [0.0, 20.0, 40.0]


class PlanState(IntEnum):
  moving = 0
  stopping = 1
  stopped = 2
  departing = 3


def get_coast_accel(pitch):
  return np.sin(pitch) * -5.65 - 0.3


def get_max_accel(v_ego):
  return float(np.interp(v_ego, A_CRUISE_MAX_BP, A_CRUISE_MAX_VALS))


def limit_accel_in_turns(v_ego, angle_steers, accel_limits, CP):
  a_total_max = np.interp(v_ego, _A_TOTAL_MAX_BP, _A_TOTAL_MAX_V)
  a_y = v_ego ** 2 * angle_steers * CV.DEG_TO_RAD / (CP.steerRatio * CP.wheelbase)
  a_x_allowed = math.sqrt(max(a_total_max ** 2 - a_y ** 2, 0.0))
  return [accel_limits[0], min(accel_limits[1], a_x_allowed)]


def get_vehicle_min_accel(CP, v_ego):
  is_gm = getattr(CP, "carName", "") == "gm" or getattr(CP, "brand", "") == "gm"
  if is_gm and getattr(CP, "enableGasInterceptorDEPRECATED", False):
    try:
      from opendbc.car.gm.values import CAR, GMFlags
      if bool(CP.flags & GMFlags.PEDAL_LONG.value):
        bolt_pedal_long = {
          CAR.CHEVROLET_BOLT_CC_2017,
          CAR.CHEVROLET_BOLT_CC_2018_2021,
          CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
          CAR.CHEVROLET_BOLT_CC_2022_2023,
          CAR.CHEVROLET_MALIBU_HYBRID_CC,
        }
        values = [-0.93, -1.28, -1.98, -2.58, -2.86, -2.95] if CP.carFingerprint in bolt_pedal_long else \
                 [-0.95, -1.30, -1.85, -2.30, -2.60, -2.80]
        return float(np.interp(v_ego, [0.0, 1.5, 4.0, 8.0, 15.0, 30.0], values))
    except Exception:
      pass
  return float(ACCEL_MIN)


def get_planner_v_ego(CP, car_state):
  is_gm = getattr(CP, "carName", "") == "gm" or getattr(CP, "brand", "") == "gm"
  if is_gm and getattr(CP, "enableGasInterceptorDEPRECATED", False):
    try:
      from opendbc.car.gm.values import GMFlags
      if bool(CP.flags & GMFlags.PEDAL_LONG.value):
        return float(car_state.vEgo)
    except Exception:
      pass
  return float(max(car_state.vEgo, car_state.vEgoCluster))


def get_accel_from_plan(speeds, accels, action_t=DT_MDL, v_ego_stopping=0.05):
  if len(speeds) != CONTROL_N:
    return 0.0, False

  v_now = float(speeds[0])
  a_now = float(accels[0])
  action_t = max(float(action_t), DT_MDL)
  v_target = float(np.interp(action_t, CONTROL_N_T_IDX, speeds))
  a_target = 2.0 * (v_target - v_now) / action_t - a_now
  v_target_1sec = float(np.interp(action_t + 1.0, CONTROL_N_T_IDX, speeds))
  should_stop = v_target < v_ego_stopping and v_target_1sec < v_ego_stopping
  return a_target, should_stop


def _smoothstep(value, low, high):
  if high <= low:
    return float(value >= high)
  x = float(np.clip((value - low) / (high - low), 0.0, 1.0))
  return x * x * (3.0 - 2.0 * x)


class LongitudinalPlanner:
  def __init__(self, CP, init_v=0.0, init_a=0.0, dt=DT_MDL):
    self.CP = CP
    self.dt = dt
    self.mpc = LongitudinalMpc(dt=dt)
    self.tune = get_longitudinal_planner_tune(CP)
    self.mpc.lead_filter_tau = self.tune.lead_filter_tau

    self.v_desired_filter = FirstOrderFilter(init_v, 2.0, dt)
    self.a_desired = init_a
    self.output_a_target = init_a
    self.output_should_stop = False
    self.allow_throttle = True
    self._throttle_transition_time = 0.0

    self.state = PlanState.moving
    self.stop_release_time = 0.0
    self.departure_confirm_time = 0.0
    self.model_authority = 0.0
    self.plan_source = "cruise"
    self.fcw = False

    self.v_desired_trajectory = np.zeros(CONTROL_N)
    self.a_desired_trajectory = np.zeros(CONTROL_N)
    self.j_desired_trajectory = np.zeros(CONTROL_N)

  @staticmethod
  def _model_stop_authority(model, v_ego):
    if bool(getattr(model.action, "shouldStop", False)):
      return 1.0
    if not len(model.position.x):
      return 0.0

    model_length = max(float(model.position.x[-1]), 0.0)
    horizon = model_length / max(float(v_ego), 1.0)
    end_speed = float(model.velocity.x[-1]) if len(model.velocity.x) else float(v_ego)
    time_score = 1.0 - _smoothstep(horizon, MODEL_STOP_FULL_TIME, MODEL_STOP_BEGIN_TIME)
    speed_score = 1.0 - _smoothstep(end_speed, 0.5, MODEL_STOP_MIN_END_SPEED)
    return float(time_score * speed_score)

  @staticmethod
  def _model_slowdown_authority(model, v_ego):
    """Preview sustained model braking before it becomes a full stop request."""
    if not len(model.position.x) or not len(model.velocity.x):
      return 0.0

    desired_accel = float(getattr(model.action, "desiredAcceleration", 0.0))
    if not np.isfinite(desired_accel) or desired_accel >= -MODEL_SLOWDOWN_MIN_ACCEL:
      return 0.0

    end_speed = float(model.velocity.x[-1])
    speed_drop = float(v_ego) - end_speed
    if not np.isfinite(end_speed) or speed_drop < MODEL_SLOWDOWN_MIN_SPEED_DROP:
      return 0.0

    accel_score = _smoothstep(-desired_accel, MODEL_SLOWDOWN_MIN_ACCEL, 0.8)
    speed_score = _smoothstep(speed_drop, MODEL_SLOWDOWN_MIN_SPEED_DROP, MODEL_SLOWDOWN_FULL_SPEED_DROP)
    return MODEL_SLOWDOWN_MAX_AUTHORITY * max(accel_score, speed_score)

  @staticmethod
  def _curve_authority(sm, v_ego):
    curvature = abs(float(getattr(sm["starpilotPlan"], "roadCurvature", 0.0)))
    lateral_accel = curvature * float(v_ego) ** 2
    curve_score = _smoothstep(lateral_accel, 0.7, 2.0)
    turning = bool(sm["carState"].leftBlinker or sm["carState"].rightBlinker)
    turn_score = 0.55 if turning and v_ego < 15.0 else 0.0
    return max(curve_score, turn_score)

  def _get_model_authority(self, sm, v_ego, v_cruise, has_lead, model_first, stop_authority):
    curve_authority = self._curve_authority(sm, v_ego)
    hard_stop = bool(
      getattr(sm["starpilotPlan"], "redLight", False) or
      getattr(sm["starpilotPlan"], "forcingStop", False) or
      getattr(sm["starpilotPlan"], "stopSignConfirmed", False)
    )
    scene_authority = 1.0 if hard_stop else max(stop_authority, curve_authority)

    if not model_first:
      return scene_authority

    cruise_error = max(0.0, float(v_cruise) - float(v_ego))
    open_road = not has_lead and scene_authority < 0.1
    open_road_blend = _smoothstep(cruise_error, 0.0, MODEL_FIRST_CRUISE_ERROR)
    base_authority = (
      MODEL_FIRST_AUTHORITY +
      (MODEL_FIRST_OPEN_ROAD_AUTHORITY - MODEL_FIRST_AUTHORITY) * open_road_blend
      if open_road else MODEL_FIRST_AUTHORITY
    )
    return max(scene_authority, base_authority)

  @staticmethod
  def _lead_safety_cap(lead, v_ego, reaction_time, stop_buffer):
    if lead is None or not bool(getattr(lead, "status", False)):
      return None, False

    d_rel = max(float(getattr(lead, "dRel", 0.0)), 0.0)
    v_lead = max(float(getattr(lead, "vLead", 0.0)), 0.0)
    closing_speed = max(0.0, float(v_ego) - v_lead)
    if closing_speed < RAW_SAFETY_MIN_CLOSING_SPEED:
      return None, False

    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    projected_closing = closing_speed + lead_brake * reaction_time
    available_distance = d_rel - stop_buffer - closing_speed * reaction_time
    ttc = max(d_rel - stop_buffer, 0.0) / max(closing_speed, 1e-3)

    if available_distance <= 0.0:
      return float(ACCEL_MIN), True

    required_decel = projected_closing ** 2 / (2.0 * available_distance)
    required_decel += 0.35 * lead_brake
    urgent = required_decel >= RAW_SAFETY_URGENT_DECEL or ttc <= RAW_SAFETY_URGENT_TTC
    if required_decel < RAW_SAFETY_MIN_DECEL and not urgent:
      return None, False
    return -float(required_decel), urgent

  def _get_raw_safety_cap(self, sm, v_ego, reaction_time):
    stop_buffer = (
      RAW_SAFETY_EXTRA_STOP_BUFFER +
      float(getattr(sm["starpilotPlan"], "increasedStoppedDistance", 0.0))
    )
    caps = [
      self._lead_safety_cap(lead, v_ego, reaction_time, stop_buffer)
      for lead in (sm["radarState"].leadOne, sm["radarState"].leadTwo)
    ]
    valid_caps = [cap for cap, _ in caps if cap is not None]
    return (min(valid_caps) if valid_caps else None), any(urgent for _, urgent in caps)

  @staticmethod
  def _safe_departure(sm, model_accel, stop_buffer):
    force_stop = bool(getattr(sm["starpilotPlan"], "forcingStop", False))
    stop_sign = bool(getattr(sm["starpilotPlan"], "stopSignConfirmed", False))
    if force_stop or stop_sign or bool(sm["carState"].brakePressed):
      return False, False

    leads = [lead for lead in (sm["radarState"].leadOne, sm["radarState"].leadTwo)
             if bool(getattr(lead, "status", False))]
    if not leads:
      return model_accel >= DEPART_MODEL_MIN_ACCEL, False

    lead = min(leads, key=lambda item: float(item.dRel))
    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    candidate = bool(
      float(lead.vLead) >= DEPART_LEAD_MIN_SPEED and
      float(lead.dRel) >= stop_buffer + DEPART_LEAD_MIN_GAP and
      lead_brake <= DEPART_LEAD_MAX_BRAKE
    )
    return candidate, candidate and float(lead.vLead) >= DEPART_LEAD_FAST_SPEED

  def _update_state(self, sm, v_ego, stop_request, safe_departure):
    if stop_request:
      self.stop_release_time = 0.0
      self.state = PlanState.stopped if v_ego <= STOPPED_SPEED else PlanState.stopping
      return

    if self.state in (PlanState.stopping, PlanState.stopped):
      if safe_departure:
        self.state = PlanState.departing
        self.stop_release_time = 0.0
      else:
        self.stop_release_time += self.dt
        if self.stop_release_time >= STOP_RELEASE_TIME and v_ego > STOPPED_SPEED:
          self.state = PlanState.moving
      return

    if self.state == PlanState.departing and v_ego >= DEPART_COMPLETE_SPEED:
      self.state = PlanState.moving
    elif self.state == PlanState.departing and not safe_departure:
      self.state = PlanState.stopped if v_ego <= STOPPED_SPEED else PlanState.stopping

  def _update_allow_throttle(self, throttle_prob, v_ego):
    if v_ego <= MIN_ALLOW_THROTTLE_SPEED:
      self.allow_throttle = True
      self._throttle_transition_time = 0.0
    else:
      lower = ALLOW_THROTTLE_THRESHOLD - ALLOW_THROTTLE_HYSTERESIS
      upper = ALLOW_THROTTLE_THRESHOLD + ALLOW_THROTTLE_HYSTERESIS
      requested = throttle_prob <= lower if self.allow_throttle else throttle_prob > upper
      self._throttle_transition_time = self._throttle_transition_time + self.dt if requested else 0.0
      if self._throttle_transition_time >= ALLOW_THROTTLE_CONFIRM_TIME:
        self.allow_throttle = not self.allow_throttle
        self._throttle_transition_time = 0.0

  def _smooth_output(self, target, urgent):
    if urgent or target <= self.output_a_target - RAW_SAFETY_URGENT_DECEL:
      return float(target)
    lower = self.output_a_target - self.tune.brake_slew_rate * self.dt
    upper = self.output_a_target + self.tune.accel_slew_rate * self.dt
    return float(np.clip(target, lower, upper))

  def update(self, sm, starpilot_toggles):
    car_state = sm["carState"]
    v_ego = get_planner_v_ego(self.CP, car_state)
    scene_v_ego = float(car_state.vEgo)
    v_cruise = float(sm["starpilotPlan"].vCruise)
    if not np.isfinite(v_cruise):
      cloudlog.error(f"Longitudinal planner received non-finite vCruise={v_cruise}")
      v_cruise = max(v_ego, 0.0)

    reset_state = (
      (sm["controlsState"].longControlState == LongCtrlState.off
       if self.CP.openpilotLongitudinalControl else not sm["selfdriveState"].enabled) or
      car_state.vCruise == V_CRUISE_UNSET
    )

    accel_limits = [
      float(sm["starpilotPlan"].minAcceleration),
      float(sm["starpilotPlan"].maxAcceleration),
    ]
    steer_angle = car_state.steeringAngleDeg - sm["liveParameters"].angleOffsetDeg
    accel_limits = limit_accel_in_turns(v_ego, steer_angle, accel_limits, self.CP)
    accel_limits[0] = max(get_vehicle_min_accel(self.CP, v_ego), accel_limits[0])

    if reset_state:
      self.v_desired_filter.x = v_ego
      self.a_desired = float(np.clip(car_state.aEgo, *accel_limits))
      self.output_a_target = self.a_desired
      self.state = PlanState.moving
      self.stop_release_time = 0.0
      self.departure_confirm_time = 0.0

    self.v_desired_filter.x = max(0.0, self.v_desired_filter.update(v_ego))

    gas_probs = sm["modelV2"].meta.disengagePredictions.gasPressProbs
    throttle_prob = float(gas_probs[1]) if len(gas_probs) > 1 else 1.0
    self._update_allow_throttle(throttle_prob, v_ego)
    if not self.allow_throttle:
      pitch = sm["carControl"].orientationNED[1] if len(sm["carControl"].orientationNED) == 3 else 0.0
      coast_accel = get_coast_accel(pitch)
      speed_guard = -COAST_TARGET_GAIN * (v_ego - COAST_TARGET_SPEED)
      accel_limits[1] = min(accel_limits[1], max(coast_accel, speed_guard, accel_limits[0]))

    if sm["controlsState"].forceDecel:
      v_cruise = 0.0

    accel_limits[0] = min(accel_limits[0], self.a_desired + 0.05)
    accel_limits[1] = max(accel_limits[1], self.a_desired - 0.05)
    self.mpc.set_accel_limits(*accel_limits)
    self.mpc.set_weights(
      acceleration_jerk=float(sm["starpilotPlan"].accelerationJerk) / 200.0,
      danger_jerk=float(sm["starpilotPlan"].dangerJerk) / 100.0,
      speed_jerk=float(sm["starpilotPlan"].speedJerk) / 5.0,
      prev_accel_constraint=not (reset_state or car_state.standstill),
    )
    self.mpc.set_cur_state(self.v_desired_filter.x, self.a_desired)
    self.mpc.update(
      sm["radarState"],
      v_cruise,
      danger_factor=float(sm["starpilotPlan"].dangerFactor),
      t_follow=float(sm["starpilotPlan"].tFollow),
      personality=sm["selfdriveState"].personality,
    )

    self.v_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC, self.mpc.v_solution)
    self.a_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC, self.mpc.a_solution)
    self.j_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC[:-1], self.mpc.j_solution)

    previous_a = self.a_desired
    self.a_desired = float(np.interp(self.dt, CONTROL_N_T_IDX, self.a_desired_trajectory))
    self.v_desired_filter.x += self.dt * (self.a_desired + previous_a) / 2.0

    actuator_delay = float(getattr(starpilot_toggles, "longitudinalActuatorDelay", self.CP.longitudinalActuatorDelay))
    action_t = max(actuator_delay + self.dt, MIN_PLAN_HORIZON)
    mpc_target, mpc_should_stop = get_accel_from_plan(
      self.v_desired_trajectory,
      self.a_desired_trajectory,
      action_t,
      float(getattr(starpilot_toggles, "vEgoStopping", 0.05)),
    )

    model_target = float(getattr(sm["modelV2"].action, "desiredAcceleration", mpc_target))
    if not np.isfinite(model_target):
      model_target = mpc_target

    leads = (sm["radarState"].leadOne, sm["radarState"].leadTwo)
    has_lead = any(bool(getattr(lead, "status", False)) for lead in leads)
    model_first = bool(getattr(starpilot_toggles, "longitudinal_model_preference", False))
    stop_authority = self._model_stop_authority(sm["modelV2"], scene_v_ego)
    slowdown_authority = self._model_slowdown_authority(sm["modelV2"], scene_v_ego)
    self.model_authority = self._get_model_authority(
      sm, scene_v_ego, v_cruise, has_lead, model_first, stop_authority,
    )
    self.model_authority = max(self.model_authority, slowdown_authority)
    model_limited_target = min(mpc_target, model_target)
    target = mpc_target + self.model_authority * (model_limited_target - mpc_target)
    self.plan_source = "e2e" if model_limited_target < mpc_target - 1e-3 and self.model_authority > 0.05 else self.mpc.source

    pinned_stop = bool(
      getattr(sm["starpilotPlan"], "forcingStop", False) or
      getattr(sm["starpilotPlan"], "stopSignConfirmed", False) or
      car_state.brakePressed
    )
    scene_stop = bool(
      getattr(sm["starpilotPlan"], "redLight", False) or
      pinned_stop or
      getattr(sm["modelV2"].action, "shouldStop", False)
    )
    model_stop_request = stop_authority >= STOP_ENTER_AUTHORITY
    stop_request = bool(scene_stop or mpc_should_stop or model_stop_request)
    increased_stop_distance = float(getattr(sm["starpilotPlan"], "increasedStoppedDistance", 0.0))
    departure_buffer = STOP_DISTANCE + increased_stop_distance
    departure_candidate, fast_departure = self._safe_departure(sm, model_target, departure_buffer)
    self.departure_confirm_time = self.departure_confirm_time + self.dt if departure_candidate else 0.0
    safe_departure = departure_candidate and (
      fast_departure or self.departure_confirm_time >= DEPART_CONFIRM_TIME
    )
    if safe_departure and not pinned_stop:
      stop_request = False
    was_departing = self.state == PlanState.departing
    was_stopped = self.state == PlanState.stopped
    self._update_state(sm, scene_v_ego, stop_request, safe_departure)
    departure_aborted = was_departing and self.state in (PlanState.stopping, PlanState.stopped)
    departure_started = was_stopped and self.state == PlanState.departing

    if self.state == PlanState.stopped:
      target = min(target, float(getattr(starpilot_toggles, "stopAccel", -0.5)))
    elif self.state == PlanState.stopping and scene_v_ego <= DEPART_COMPLETE_SPEED:
      target = min(target, float(getattr(starpilot_toggles, "stopAccel", -0.5)))
    elif self.state == PlanState.departing and safe_departure:
      target = max(target, self.tune.launch_accel)

    safety_cap, urgent = self._get_raw_safety_cap(
      sm,
      scene_v_ego,
      actuator_delay + RAW_SAFETY_REACTION_BUFFER,
    )
    urgent |= departure_aborted or departure_started
    if safety_cap is not None:
      target = min(target, safety_cap)
    if safety_cap is not None and safety_cap < -RAW_SAFETY_MIN_DECEL:
      if self.state == PlanState.departing:
        self.state = PlanState.stopping
      stop_request |= scene_v_ego <= STOP_CONTROL_SPEED

    target = float(np.clip(target, accel_limits[0], accel_limits[1]))
    self.output_a_target = self._smooth_output(target, urgent)
    self.output_should_stop = bool(
      self.state in (PlanState.stopping, PlanState.stopped) and
      (scene_v_ego <= STOP_CONTROL_SPEED or mpc_should_stop)
    )

    self.fcw = self.mpc.crash_cnt > 2 and not car_state.standstill and any(
      should_trigger_planner_fcw(lead, scene_v_ego) for lead in leads
    )
    if self.fcw:
      cloudlog.info("FCW triggered")

  def publish(self, sm, pm):
    plan_send = messaging.new_message("longitudinalPlan")
    plan_send.valid = sm.all_checks(service_list=["carState", "controlsState", "selfdriveState", "radarState"])

    plan = plan_send.longitudinalPlan
    plan.modelMonoTime = sm.logMonoTime["modelV2"]
    plan.processingDelay = (plan_send.logMonoTime / 1e9) - sm.logMonoTime["modelV2"]
    plan.solverExecutionTime = self.mpc.solve_time
    plan.speeds = self.v_desired_trajectory.tolist()
    plan.accels = self.a_desired_trajectory.tolist()
    plan.jerks = self.j_desired_trajectory.tolist()
    plan.hasLead = any(lead.status for lead in (sm["radarState"].leadOne, sm["radarState"].leadTwo))
    plan.longitudinalPlanSource = self.plan_source
    plan.fcw = self.fcw
    plan.aTarget = float(self.output_a_target)

    force_stop_handoff = bool(
      sm["starpilotPlan"].forcingStop and (
        sm["starpilotPlan"].forcingStopLength < 1.0 or
        sm["starpilotPlan"].vCruise <= FORCE_STOP_HANDOFF_MAX_VCRUISE
      )
    )
    plan.shouldStop = bool(self.output_should_stop or force_stop_handoff)
    plan.allowBrake = True
    plan.allowThrottle = bool(self.allow_throttle)
    pm.send("longitudinalPlan", plan_send)
