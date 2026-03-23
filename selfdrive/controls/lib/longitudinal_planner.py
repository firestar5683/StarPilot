#!/usr/bin/env python3
import math
import time
import numpy as np

import cereal.messaging as messaging
from opendbc.car.interfaces import ACCEL_MIN, ACCEL_MAX
from openpilot.common.constants import CV
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.modeld.constants import ModelConstants
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import LongitudinalMpc
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import T_IDXS as T_IDXS_MPC
from openpilot.selfdrive.controls.lib.drive_helpers import CONTROL_N, get_accel_from_plan
from openpilot.selfdrive.car.cruise import V_CRUISE_UNSET
from openpilot.common.swaglog import cloudlog

LON_MPC_STEP = 0.2  # first step is 0.2s
A_CRUISE_MIN = -1.0
A_CRUISE_MAX_BP = [0.0, 5., 10., 15., 20., 25., 40.]
A_CRUISE_MAX_VALS = [1.125, 1.125, 1.125, 1.125, 1.25, 1.25, 1.5]
CONTROL_N_T_IDX = ModelConstants.T_IDXS[:CONTROL_N]
ALLOW_THROTTLE_THRESHOLD = 0.4
MIN_ALLOW_THROTTLE_SPEED = 2.5

# Uncertainty-based filter disable thresholds
UNCERT_SLOPE_TRIG = 0.12  # per second
UNCERT_MAG_TRIG = 0.50

# Lookup table for turns
_A_TOTAL_MAX_V = [1.7, 3.2]
_A_TOTAL_MAX_BP = [20., 40.]


def get_max_accel(v_ego):
  return np.interp(v_ego, A_CRUISE_MAX_BP, A_CRUISE_MAX_VALS)

def get_coast_accel(pitch):
  return np.sin(pitch) * -5.65 - 0.3  # fitted from data using xx/projects/allow_throttle/compute_coast_accel.py


def limit_accel_in_turns(v_ego, angle_steers, a_target, CP):
  """
  This function returns a limited long acceleration allowed, depending on the existing lateral acceleration
  this should avoid accelerating when losing the target in turns
  """
  # FIXME: This function to calculate lateral accel is incorrect and should use the VehicleModel
  # The lookup table for turns should also be updated if we do this
  a_total_max = np.interp(v_ego, _A_TOTAL_MAX_BP, _A_TOTAL_MAX_V)
  a_y = v_ego ** 2 * angle_steers * CV.DEG_TO_RAD / (CP.steerRatio * CP.wheelbase)
  a_x_allowed = math.sqrt(max(a_total_max ** 2 - a_y ** 2, 0.))

  return [a_target[0], min(a_target[1], a_x_allowed)]


class LongitudinalPlanner:
  def __init__(self, CP, init_v=0.0, init_a=0.0, dt=DT_MDL):
    self.CP = CP
    self.mpc = LongitudinalMpc(dt=dt)
    self.fcw = False
    self.dt = dt
    self.allow_throttle = True
    self.mode = 'acc'
    self.generation = None

    self.a_desired = init_a
    self.v_desired_filter = FirstOrderFilter(init_v, 2.0, self.dt)
    self.v_model_error = 0.0
    self.output_a_target = 0.0
    self.output_should_stop = False

    self.v_desired_trajectory = np.zeros(CONTROL_N)
    self.a_desired_trajectory = np.zeros(CONTROL_N)
    self.j_desired_trajectory = np.zeros(CONTROL_N)
    self.solverExecutionTime = 0.0

    self.uncert_slow = FirstOrderFilter(0.0, 1.6, self.dt)
    self.uncert_fast = FirstOrderFilter(0.0, 0.9, self.dt)
    self.prev_lead_dist = None
    self.last_big_brake_t = 0.0
    self.stable_lead = False
    self.lead_dist_f = None
    self._uncert_last = 0.0
    self._uncert_last_t = None
    self.v_ego_stopping = 0.05
    self.longitudinal_actuator_delay = 0.2

  @property
  def mlsim(self):
    return self.generation in ("v8", "v10", "v11", "v12")

  @staticmethod
  def get_model_speed_error(model_msg, v_ego):
    temporal_pose = getattr(model_msg, "temporalPose", None)
    if temporal_pose is not None and len(temporal_pose.trans):
      return float(np.clip(temporal_pose.trans[0] - v_ego, -5.0, 5.0))
    if len(model_msg.velocity.x) == ModelConstants.IDX_N:
      return float(np.clip(model_msg.velocity.x[0] - v_ego, -5.0, 5.0))
    return 0.0

  @staticmethod
  def parse_model(model_msg, model_error, v_ego, taco_tune):
    if (len(model_msg.position.x) == ModelConstants.IDX_N and
      len(model_msg.velocity.x) == ModelConstants.IDX_N and
      len(model_msg.acceleration.x) == ModelConstants.IDX_N):
      x = np.interp(T_IDXS_MPC, ModelConstants.T_IDXS, model_msg.position.x) - model_error * T_IDXS_MPC
      v = np.interp(T_IDXS_MPC, ModelConstants.T_IDXS, model_msg.velocity.x) - model_error
      a = np.interp(T_IDXS_MPC, ModelConstants.T_IDXS, model_msg.acceleration.x)
      j = np.zeros(len(T_IDXS_MPC))
    else:
      x = np.zeros(len(T_IDXS_MPC))
      v = np.zeros(len(T_IDXS_MPC))
      a = np.zeros(len(T_IDXS_MPC))
      j = np.zeros(len(T_IDXS_MPC))
    if len(model_msg.meta.disengagePredictions.gasPressProbs) > 1:
      throttle_prob = model_msg.meta.disengagePredictions.gasPressProbs[1]
    else:
      throttle_prob = 1.0

    if taco_tune:
      max_lat_accel = np.interp(v_ego, [5, 10, 20], [1.5, 2.0, 3.0])
      curvatures = np.interp(T_IDXS_MPC, ModelConstants.T_IDXS, model_msg.orientationRate.z) / np.clip(v, 0.3, 100.0)
      max_v = np.sqrt(max_lat_accel / (np.abs(curvatures) + 1e-3)) - 2.0
      v = np.minimum(max_v, v)

    return x, v, a, j, throttle_prob

  def update(self, sm, frogpilot_toggles=None):
    self.generation = getattr(frogpilot_toggles, "model_version", None)
    self.mode = 'blended' if sm['selfdriveState'].experimentalMode else 'acc'
    self.mpc.mode = 'acc'
    if not self.mlsim:
      self.mpc.mode = self.mode
    self.v_ego_stopping = getattr(frogpilot_toggles, "vEgoStopping", self.v_ego_stopping)
    self.longitudinal_actuator_delay = getattr(frogpilot_toggles, "longitudinalActuatorDelay", self.longitudinal_actuator_delay)

    if len(sm['carControl'].orientationNED) == 3:
      accel_coast = get_coast_accel(sm['carControl'].orientationNED[1])
    else:
      accel_coast = ACCEL_MAX

    v_ego = max(sm['carState'].vEgo, sm['carState'].vEgoCluster)
    v_cruise = sm['frogpilotPlan'].vCruise
    v_cruise_initialized = sm['carState'].vCruise != V_CRUISE_UNSET

    long_control_off = sm['controlsState'].longControlState == LongCtrlState.off
    force_slow_decel = sm['controlsState'].forceDecel

    # Reset current state when not engaged, or user is controlling the speed
    reset_state = long_control_off if self.CP.openpilotLongitudinalControl else not sm['selfdriveState'].enabled
    # PCM cruise speed may be updated a few cycles later, check if initialized
    reset_state = reset_state or not v_cruise_initialized

    # No change cost when user is controlling the speed, or when standstill
    prev_accel_constraint = not (reset_state or sm['carState'].standstill)

    if self.mpc.mode == 'acc':
      accel_limits = [sm['frogpilotPlan'].minAcceleration, sm['frogpilotPlan'].maxAcceleration]
      steer_angle_without_offset = sm['carState'].steeringAngleDeg - sm['liveParameters'].angleOffsetDeg
      accel_limits_turns = limit_accel_in_turns(v_ego, steer_angle_without_offset, accel_limits, self.CP)
    else:
      accel_limits = [ACCEL_MIN, ACCEL_MAX]
      accel_limits_turns = [ACCEL_MIN, ACCEL_MAX]

    if reset_state:
      self.v_desired_filter.x = v_ego
      # Clip aEgo to cruise limits to prevent large accelerations when becoming active
      self.a_desired = np.clip(sm['carState'].aEgo, accel_limits[0], accel_limits[1])

    # Prevent divergence, smooth in current v_ego
    self.v_desired_filter.x = max(0.0, self.v_desired_filter.update(v_ego))
    self.v_model_error = self.get_model_speed_error(sm['modelV2'], v_ego)
    x, v, a, j, throttle_prob = self.parse_model(sm['modelV2'], self.v_model_error, v_ego, getattr(frogpilot_toggles, "taco_tune", False))
    # Don't clip at low speeds since throttle_prob doesn't account for creep
    self.allow_throttle = throttle_prob > ALLOW_THROTTLE_THRESHOLD or v_ego <= MIN_ALLOW_THROTTLE_SPEED
    self.allow_throttle &= not sm['frogpilotPlan'].disableThrottle

    if not self.allow_throttle:
      clipped_accel_coast = max(accel_coast, accel_limits_turns[0])
      clipped_accel_coast_interp = np.interp(v_ego, [MIN_ALLOW_THROTTLE_SPEED, MIN_ALLOW_THROTTLE_SPEED*2], [accel_limits_turns[1], clipped_accel_coast])
      accel_limits_turns[1] = min(accel_limits_turns[1], clipped_accel_coast_interp)

    if force_slow_decel:
      v_cruise = 0.0

    accel_limits_turns[0] = min(accel_limits_turns[0], self.a_desired + 0.05)
    accel_limits_turns[1] = max(accel_limits_turns[1], self.a_desired - 0.05)

    lead_one = sm['radarState'].leadOne
    lead_dist = lead_one.dRel if lead_one.status else 50.0

    alpha = max(0.02, min(0.15, 0.05 + 0.002 * v_ego))
    if self.lead_dist_f is None:
      self.lead_dist_f = float(lead_dist)
    else:
      self.lead_dist_f += alpha * (float(lead_dist) - self.lead_dist_f)

    now_t = time.monotonic()
    v_rel = (v_ego - lead_one.vLead) if lead_one.status else 0.0
    if self.prev_lead_dist is None:
      d_rel_dot = 0.0
    else:
      d_rel_dot = (lead_dist - self.prev_lead_dist) / max(self.dt, 1e-3)
    self.prev_lead_dist = lead_dist

    uncertainty = 0.0
    raw_brake_max = 0.0
    if hasattr(sm['modelV2'], 'meta'):
      desire_entropy = 0.0
      if hasattr(sm['modelV2'].meta, 'desirePrediction'):
        desire_probs = sm['modelV2'].meta.desirePrediction
        if len(desire_probs) > 1:
          probs = np.asarray(desire_probs, dtype=float)
          total = float(np.sum(probs))
          if total > 1e-6:
            p = probs / total
            entropy = -np.sum(p * np.log(p + 1e-10))
            max_entropy = np.log(len(p))
            desire_entropy = float(entropy / max(max_entropy, 1e-6))

      disengage_risk = 0.0
      if hasattr(sm['modelV2'].meta, 'disengagePredictions'):
        brake_probs = sm['modelV2'].meta.disengagePredictions.brakePressProbs
        if len(brake_probs) > 0:
          probs = np.asarray(brake_probs, dtype=float)
          if float(np.max(probs)) < 0.015:
            probs = probs * 0.5
          raw_brake_max = float(np.max(probs))
          t = np.arange(len(probs), dtype=float) * DT_MDL
          lam = 0.6
          weights = np.exp(-lam * t)
          disengage_risk = float(np.max(probs * weights))

      raw_uncertainty = desire_entropy + disengage_risk
      self.uncert_slow.update(raw_uncertainty)
      self.uncert_fast.update(raw_uncertainty)
      uncertainty = self.uncert_slow.x

    if raw_brake_max > 0.02:
      self.last_big_brake_t = now_t

    recently_braked = (now_t - self.last_big_brake_t) < 0.7
    self.stable_lead = (
      lead_one.status and
      abs(v_rel) < 0.5 and
      abs(d_rel_dot) < 0.5 and
      not recently_braked
    )

    if self._uncert_last_t is None:
      uncert_slope = 0.0
    else:
      dt_u = max(1e-3, now_t - self._uncert_last_t)
      uncert_slope = (uncertainty - self._uncert_last) / dt_u
    self._uncert_last = uncertainty
    self._uncert_last_t = now_t

    closing_fast = lead_one.status and (v_ego - lead_one.vLead) > 0.5
    panic_bypass = closing_fast and (uncert_slope > UNCERT_SLOPE_TRIG or uncertainty >= UNCERT_MAG_TRIG)
    if panic_bypass:
      cloudlog.error(f"LON_SLOPE slope={uncert_slope:.3f} uncertainty={uncertainty:.3f} v_ego={v_ego:.2f}")

    self.mpc.set_weights(sm['frogpilotPlan'].accelerationJerk,
                         sm['frogpilotPlan'].dangerJerk,
                         sm['frogpilotPlan'].speedJerk,
                         prev_accel_constraint,
                         personality=sm['selfdriveState'].personality,
                         v_ego=v_ego,
                         lead_dist=self.lead_dist_f if self.lead_dist_f is not None else lead_dist,
                         uncertainty=uncertainty,
                         panic_bypass=panic_bypass,
                         stop_distance=getattr(frogpilot_toggles, "stop_distance", 6.0))
    self.mpc.set_accel_limits(accel_limits_turns[0], accel_limits_turns[1])
    self.mpc.set_cur_state(self.v_desired_filter.x, self.a_desired)
    tracking_lead = sm['frogpilotPlan'].desiredFollowDistance > 0
    self.mpc.update(sm['radarState'], v_cruise, x, v, a, j,
                    sm['frogpilotPlan'].dangerFactor, sm['frogpilotPlan'].tFollow,
                    personality=sm['selfdriveState'].personality, tracking_lead=tracking_lead)

    self.v_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC, self.mpc.v_solution)
    self.a_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC, self.mpc.a_solution)
    self.j_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC[:-1], self.mpc.j_solution)

    # TODO counter is only needed because radar is glitchy, remove once radar is gone
    self.fcw = self.mpc.crash_cnt > 2 and not sm['carState'].standstill
    if self.fcw:
      cloudlog.info("FCW triggered")

    # Interpolate 0.05 seconds and save as starting point for next iteration
    a_prev = self.a_desired
    self.a_desired = float(np.interp(self.dt, CONTROL_N_T_IDX, self.a_desired_trajectory))
    self.v_desired_filter.x = self.v_desired_filter.x + self.dt * (self.a_desired + a_prev) / 2.0

    if lead_one.status:
      rel_v = max(0.0, v_ego - lead_one.vLead)
      base_th = 1.6
      th = base_th + 0.6 * max(0.0, uncertainty - 0.42)
      desired_gap = th * v_ego
      if self.lead_dist_f is not None and self.lead_dist_f < desired_gap and rel_v > 0.5:
        k_rel, k_unc = 0.04, 0.20
        pre_brake = k_rel * rel_v + k_unc * max(0.0, uncertainty - 0.42)
        self.a_desired = float(self.a_desired - min(pre_brake, 0.06))

    if -0.05 < self.a_desired < 0.05:
      self.a_desired = 0.0

  def publish(self, sm, pm):
    plan_send = messaging.new_message('longitudinalPlan')

    plan_send.valid = sm.all_checks(service_list=['carState', 'controlsState', 'selfdriveState', 'radarState'])

    longitudinalPlan = plan_send.longitudinalPlan
    longitudinalPlan.modelMonoTime = sm.logMonoTime['modelV2']
    longitudinalPlan.processingDelay = (plan_send.logMonoTime / 1e9) - sm.logMonoTime['modelV2']
    longitudinalPlan.solverExecutionTime = self.mpc.solve_time

    longitudinalPlan.speeds = self.v_desired_trajectory.tolist()
    longitudinalPlan.accels = self.a_desired_trajectory.tolist()
    longitudinalPlan.jerks = self.j_desired_trajectory.tolist()

    longitudinalPlan.hasLead = sm['radarState'].leadOne.status
    longitudinalPlan.longitudinalPlanSource = self.mpc.source
    longitudinalPlan.fcw = self.fcw

    action_t = self.longitudinal_actuator_delay + DT_MDL
    output_a_target_mpc, output_should_stop_mpc = get_accel_from_plan(
      longitudinalPlan.speeds, longitudinalPlan.accels, CONTROL_N_T_IDX,
      action_t=action_t, vEgoStopping=self.v_ego_stopping,
    )
    output_a_target_e2e = sm['modelV2'].action.desiredAcceleration
    output_should_stop_e2e = sm['modelV2'].action.shouldStop

    if self.mode == 'acc' or self.generation == 'v9':
      a_target = output_a_target_mpc
      should_stop = output_should_stop_mpc
    else:
      a_target = min(output_a_target_mpc, output_a_target_e2e)
      should_stop = output_should_stop_e2e or output_should_stop_mpc

    self.output_a_target = float(a_target)
    self.output_should_stop = bool(should_stop) or sm['frogpilotPlan'].forcingStopLength < 1
    longitudinalPlan.aTarget = self.output_a_target
    longitudinalPlan.shouldStop = self.output_should_stop
    longitudinalPlan.allowBrake = True
    longitudinalPlan.allowThrottle = bool(self.allow_throttle)

    pm.send('longitudinalPlan', plan_send)
