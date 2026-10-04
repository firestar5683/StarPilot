#!/usr/bin/env python3
import math
import time
from collections.abc import Callable
from dataclasses import replace
import numpy as np

import openpilot.cereal.messaging as messaging
from opendbc.car.interfaces import ACCEL_MIN, ACCEL_MAX
from openpilot.common.constants import CV
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.modeld.constants import ModelConstants
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import LongitudinalMpc, LongitudinalPlanSource, get_T_FOLLOW, get_jerk_factor
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import T_IDXS as T_IDXS_MPC
from openpilot.selfdrive.controls.lib.drive_helpers import CONTROL_N, get_accel_from_plan, should_stop
from openpilot.selfdrive.car.cruise import V_CRUISE_MAX, V_CRUISE_UNSET
from openpilot.common.swaglog import cloudlog
from openpilot.starpilot.navigation.intent import cruise_ceiling as navigation_ceiling
from openpilot.starpilot.longitudinal.vehicle_policy import forecast_should_stop, planner_cost_owner
from openpilot.starpilot.longitudinal.cruise_ceiling import CruiseCeiling, CurveCeiling, select_cruise_ceiling, select_curve_ceiling
from openpilot.starpilot.longitudinal.profile_runtime import (AppliedProfile, ProfileSmoother, ProfileTuning, SelectedProfileTuning,
                                                             TRAFFIC_CRUISE_BRAKE_MAGNITUDE)
from openpilot.starpilot.longitudinal.slc_coast import braking_lead_relevant, slc_coast_floor
from openpilot.starpilot.longitudinal.throttle_gate import ModelThrottleGate
from openpilot.starpilot.longitudinal.ioniq6_start import eligible as ioniq6_long_eligible
from openpilot.starpilot.longitudinal.lane_change_gap import LaneChangeGap, project as project_lane_gap
from openpilot.starpilot.longitudinal.experimental_release import ConditionalHandoff, ExperimentalRelease, project as project_release
from openpilot.starpilot.longitudinal.force_stop import StopPlan
from openpilot.starpilot.longitudinal.follow_jerk import FollowJerk
from openpilot.starpilot.longitudinal.lead_takeoff import LeadTakeoff, project as project_takeoff
from openpilot.starpilot.longitudinal.lead_behavior import adjust as adjust_lead_behavior
from openpilot.starpilot.longitudinal.lead_approach import LeadApproach, LeadApproachKey, project as project_approach
from openpilot.starpilot.lateral.lane_change_preferences import LaneChangePolicy

A_CRUISE_MAX_VALS = [1.6, 1.2, 0.8, 0.6]
A_CRUISE_MAX_BP = [0., 10.0, 25., 40.]
J_CRUISE_VALS = [1.6, 1.2, 0.8, 0.6]
A_CRUISE_MIN = -1.2
CONTROL_N_T_IDX = ModelConstants.T_IDXS[:CONTROL_N]
MIN_ALLOW_THROTTLE_SPEED = 2.5
NATIVE_ALLOW_THROTTLE_PROBABILITY = 0.4
NATIVE_PLAN_INPUTS = ('carControl', 'carState', 'controlsState', 'vehicleParameters',
                      'radarState', 'modelV2', 'selfdriveState')

# Lookup table for turns
_A_TOTAL_MAX_V = [1.7, 3.2]
_A_TOTAL_MAX_BP = [20., 40.]

def get_max_accel(v_ego):
  return np.interp(v_ego, A_CRUISE_MAX_BP, A_CRUISE_MAX_VALS)

def get_coast_accel(pitch):
  return np.sin(pitch) * -5.65 - 0.3  # fitted from data using xx/projects/allow_throttle/compute_coast_accel.py

def get_cruise_accel(e2e, v_cruise, v_ego, a_cruise_prev, angle_steers, CP, dt, accel_coast, allow_throttle,
                     profile: AppliedProfile | None = None, cruise_brake_floor: float | None = None,
                     base_brake_floor: float = A_CRUISE_MIN, selected_acceleration_max: float | None = None):
  max_accel = ACCEL_MAX if e2e else get_max_accel(v_ego)
  if profile is not None:
    max_accel = min(max_accel, profile.acceleration_max, ACCEL_MAX)

  if selected_acceleration_max is not None:
    max_accel = min(max_accel, selected_acceleration_max, ACCEL_MAX)

  if not e2e:
    a_total_max = np.interp(v_ego, _A_TOTAL_MAX_BP, _A_TOTAL_MAX_V)
    a_y = v_ego ** 2 * angle_steers * CV.DEG_TO_RAD / (CP.steerRatio * CP.wheelbase)
    a_x_allowed = math.sqrt(max(a_total_max ** 2 - a_y ** 2, 0.))
    max_accel = min(max_accel, a_x_allowed)
    if not allow_throttle:
      clipped_accel_coast = max(accel_coast, ACCEL_MIN)
      coast_limit = np.interp(v_ego, [MIN_ALLOW_THROTTLE_SPEED, MIN_ALLOW_THROTTLE_SPEED*2], [max_accel, clipped_accel_coast])
      max_accel = min(max_accel, coast_limit)

  cruise_min = max(ACCEL_MIN, -profile.cruise_brake_magnitude) if profile is not None else max(ACCEL_MIN, base_brake_floor)
  if cruise_brake_floor is not None:
    cruise_min = max(cruise_min, cruise_brake_floor)
  target_accel = np.clip(v_cruise - v_ego, cruise_min, max_accel)
  j_cruise = np.interp(v_ego, A_CRUISE_MAX_BP, J_CRUISE_VALS)
  target_accel = float(np.clip(target_accel, a_cruise_prev - j_cruise * dt, a_cruise_prev + j_cruise * dt))

  return target_accel


class LongitudinalPlanner:
  def __init__(self, CP, init_v=0.0, init_a=0.0, dt=DT_MDL, clock_ns: Callable[[], int] = time.monotonic_ns):
    self.CP = CP
    self.mpc = LongitudinalMpc(dt=dt)
    self.fcw = False
    self.dt = dt
    self.clock_ns = clock_ns
    self.allow_throttle = True
    self.throttle_gate = ModelThrottleGate()
    self.ioniq6_throttle_gate_enabled = ioniq6_long_eligible(CP)
    self.lane_change_gap = LaneChangeGap()
    self.experimental_release = ExperimentalRelease()
    self.lead_approach = LeadApproach(dt, CP.longitudinalActuatorDelay)

    self.v_desired_filter = FirstOrderFilter(init_v, 2.0, self.dt)
    self.a_cruise = init_a
    self.output_a_target = init_a
    self.output_should_stop = False

    self.v_desired_trajectory = np.zeros(CONTROL_N)
    self.a_desired_trajectory = np.zeros(CONTROL_N)
    self.j_desired_trajectory = np.zeros(CONTROL_N)
    self.last_cruise_ceiling_status = "absent"
    self.last_curve_ceiling_status = "absent"
    self.last_curve_ceiling_applied = False
    self.profile_smoother = ProfileSmoother()
    self.last_profile: AppliedProfile | None = None
    self.force_stop_plan = StopPlan()
    self.follow_jerk = FollowJerk(CP)
    self.vehicle_cost_owner = planner_cost_owner(CP)
    self.lead_takeoff = LeadTakeoff()

  def update(self, sm, *, cruise_ceiling: CruiseCeiling | None = None,
             profile_tuning: ProfileTuning | None = None, curve_ceiling: CurveCeiling | None = None,
             curve_provider: Callable[[float | None], CurveCeiling | None] | None = None,
             traffic_mode: bool | None = False, lane_change_policy: LaneChangePolicy | None = None,
             global_braking_response: str | None = None, selected_profiles: SelectedProfileTuning | None = None,
             conditional_handoff: ConditionalHandoff | None = None,
             lead_approach_key: LeadApproachKey | None = None,
             force_stop_provider: Callable[[float], StopPlan] | None = None,
             faster_lead_takeoff: bool = False, takeoff_drive_id: int = 0,
             now_ns: int | None = None, drive_id: int = 0, wheel_coast=None):
    if curve_ceiling is not None and curve_provider is not None:
      raise ValueError('choose explicit Curve ceiling or same-cycle provider')
    sample_now_ns = self.clock_ns() if now_ns is None else now_ns
    if len(sm['carControl'].orientationNED) == 3:
      accel_coast = get_coast_accel(sm['carControl'].orientationNED[1])
    else:
      accel_coast = ACCEL_MAX

    v_ego = sm['carState'].vEgo
    v_cruise_kph = min(sm['carState'].vCruise, V_CRUISE_MAX)
    v_cruise = v_cruise_kph * CV.KPH_TO_MS
    ceiling = select_cruise_ceiling(
      cruise_ceiling, driver_v_cruise_kph=sm['carState'].vCruise, driver_cruise_mps=v_cruise,
      system_long_available=self.CP.openpilotLongitudinalControl,
      long_control_active=sm['controlsState'].longControlState != LongCtrlState.off,
      selfdrive_enabled=sm['selfdriveState'].enabled, force_decel=sm['controlsState'].forceDecel,
    )
    self.last_cruise_ceiling_status = ceiling.status
    if ceiling.effective_mps is not None:
      v_cruise = ceiling.effective_mps
    long_control_off = sm['controlsState'].longControlState == LongCtrlState.off
    profile_eligible = (self.CP.openpilotLongitudinalControl and
                        sm['selfdriveState'].enabled and not long_control_off and sm['carControl'].longActive)
    if profile_eligible:
      self.last_profile = self.profile_smoother.sample(profile_tuning, sm['selfdriveState'].personality, self.dt,
                                                       traffic_mode=traffic_mode)
    else:
      self.profile_smoother.applied = None
      self.profile_smoother.slc_braking_style = 'standard'
      self.last_profile = None

    # Reset current state when not engaged, or user is controlling the speed
    reset_state = long_control_off if self.CP.openpilotLongitudinalControl else not sm['selfdriveState'].enabled
    # PCM cruise speed may be updated a few cycles later, check if initialized
    v_cruise_initialized = sm['carState'].vCruise != V_CRUISE_UNSET
    reset_state = reset_state or not v_cruise_initialized

    throttle_probs = sm['modelV2'].meta.disengagePredictions.gasPressProbs
    throttle_prob = throttle_probs[1] if len(throttle_probs) > 1 else 1.0
    if self.ioniq6_throttle_gate_enabled and sm['carControl'].longActive and not reset_state:
      model_ns = getattr(sm, 'logMonoTime', {}).get('modelV2', 0)
      self.allow_throttle = self.throttle_gate.step(throttle_prob if len(throttle_probs) > 1 else float('nan'),
                                                    v_ego, low_speed_mps=MIN_ALLOW_THROTTLE_SPEED, model_ns=model_ns,
                                                    now_ns=sample_now_ns,
                                                    model_valid=(getattr(sm, 'valid', {}).get('modelV2', False) is True and
                                                                 getattr(sm, 'alive', {}).get('modelV2', False) is True))
    else:
      self.throttle_gate.reset()
      self.allow_throttle = throttle_prob > NATIVE_ALLOW_THROTTLE_PROBABILITY or v_ego <= MIN_ALLOW_THROTTLE_SPEED

    steer_angle_without_offset = sm['carState'].steeringAngleDeg - sm['vehicleParameters'].angleOffsetDeg

    if reset_state:
      self.v_desired_filter.x = v_ego
      self.output_a_target = np.clip(sm['carState'].aEgo, ACCEL_MIN, ACCEL_MAX)
      self.a_cruise = self.output_a_target

    # Prevent divergence, smooth in current v_ego
    self.v_desired_filter.x = max(0.0, self.v_desired_filter.update(v_ego))

    # No change cost when user is controlling the speed, or when standstill
    prev_accel_constraint = not (reset_state or sm['carState'].standstill)

    self.mpc.set_cur_state(self.v_desired_filter.x, self.output_a_target)
    base_follow = self.last_profile.follow_seconds if self.last_profile is not None else get_T_FOLLOW(sm['selfdriveState'].personality)
    approach_follow = self.lead_approach.step(
      lead_approach_key, project_approach(sm, self.CP, sample_now_ns, lead_approach_key) if lead_approach_key is not None else None,
      base_follow, blocked=reset_state)
    gap_follow = self.lane_change_gap.step(
      lane_change_policy, project_lane_gap(sm, sample_now_ns) if lane_change_policy is not None else None,
      base_follow=base_follow, long_active=bool(self.CP.openpilotLongitudinalControl and sm['carControl'].longActive and
                                                not reset_state and sm['selfdriveState'].enabled and approach_follow is None))
    follow = approach_follow if approach_follow is not None else gap_follow
    selected_follow = follow if follow is not None else base_follow
    self.force_stop_plan = force_stop_provider(selected_follow) if force_stop_provider is not None else StopPlan()
    if (reset_state or not profile_eligible or self.force_stop_plan.model_ns != getattr(sm, 'logMonoTime', {}).get('modelV2') or
        sm['carState'].gasPressed or sm['carState'].brakePressed or sm['controlsState'].forceDecel):
      self.force_stop_plan = StopPlan()
    if self.force_stop_plan.speed_ceiling_mps is not None:
      v_cruise = min(v_cruise, self.force_stop_plan.speed_ceiling_mps)
    follow_scale = self.follow_jerk.sample(sm, self.CP, sample_now_ns, selected_follow, self.force_stop_plan,
                                           active=profile_eligible and not reset_state, drive_id=drive_id)
    accelerating = sm['carState'].aEgo >= 0
    weights = None
    if self.vehicle_cost_owner is not None:
      # Current mode arbitration is retained; do not recreate old one-cycle delay.
      weights = self.vehicle_cost_owner.sample(
        sm, sample_now_ns, active=profile_eligible and not reset_state, drive_id=drive_id,
        mode='blended' if sm['selfdriveState'].experimentalMode else 'acc',
        acceleration_factor=(self.last_profile.acceleration_jerk if accelerating else self.last_profile.deceleration_jerk)
        if self.last_profile is not None else get_jerk_factor(sm['selfdriveState'].personality),
        speed_factor=(self.last_profile.speed_jerk if accelerating else self.last_profile.speed_decrease_jerk)
        if self.last_profile is not None else get_jerk_factor(sm['selfdriveState'].personality),
        danger_factor=self.last_profile.danger_jerk if self.last_profile is not None else get_jerk_factor(sm['selfdriveState'].personality),
        stop_plan=self.force_stop_plan, follow_scale=follow_scale, prev_accel_constraint=prev_accel_constraint)
    if weights is not None:
      self.mpc.set_cost_weights(weights.stage, weights.constraints)
    else:
      self.mpc.set_weights(prev_accel_constraint, personality=sm['selfdriveState'].personality,
                           acceleration_jerk=(self.last_profile.acceleration_jerk if accelerating else self.last_profile.deceleration_jerk)
                           if self.last_profile is not None else None,
                           speed_jerk=(self.last_profile.speed_jerk if accelerating else self.last_profile.speed_decrease_jerk)
                           if self.last_profile is not None else None,
                           danger_jerk=self.last_profile.danger_jerk if self.last_profile is not None else None,
                           stop_jerk_scale=self.force_stop_plan.jerk_scale, acceleration_change_scale=follow_scale)
    selected_acceleration = selected_profiles.acceleration_max if profile_eligible and selected_profiles is not None else None
    acceleration_cap = self.last_profile.acceleration_max if self.last_profile is not None else None
    if selected_acceleration is not None:
      acceleration_cap = selected_acceleration
    self.mpc.update(sm['radarState'], personality=sm['selfdriveState'].personality,
                    follow_seconds=follow if follow is not None else
                    (self.last_profile.follow_seconds if self.last_profile is not None else None),
                    acceleration_max=acceleration_cap,
                    stop_line_m=self.force_stop_plan.obstacle_m)

    # MPC has selected the actual follow time for this model cycle. Its solve
    # does not use the Curve cruise cap, so a provider may now evaluate the
    # filtered lead condition without reading a stale saved preference.
    if curve_provider is not None:
      try:
        selected_follow = float(self.mpc.params[0, 4])
        if not math.isfinite(selected_follow) or not 0.5 <= selected_follow <= 3.0:
          selected_follow = None
      except (AttributeError, IndexError, TypeError, ValueError, OverflowError):
        selected_follow = None
      curve_ceiling = curve_provider(selected_follow)
    curve = select_curve_ceiling(
      curve_ceiling, model_ns=getattr(sm, 'logMonoTime', {}).get('modelV2', 0),
      driver_v_cruise_kph=sm['carState'].vCruise, effective_cruise_mps=v_cruise,
      system_long_available=self.CP.openpilotLongitudinalControl,
      long_control_active=sm['controlsState'].longControlState != LongCtrlState.off,
      car_long_active=sm['carControl'].longActive, selfdrive_enabled=sm['selfdriveState'].enabled,
      force_decel=sm['controlsState'].forceDecel, driver_override=sm['carState'].gasPressed or sm['carState'].brakePressed,
    )
    self.last_curve_ceiling_status = curve.status
    self.last_curve_ceiling_applied = False
    if curve.effective_mps is not None:
      v_cruise = curve.effective_mps
    navigation_target = navigation_ceiling(sm, self.CP, sample_now_ns, v_cruise) if profile_eligible else None
    if navigation_target is not None:
      v_cruise = min(v_cruise, navigation_target)
    coast_plan = None
    if wheel_coast is not None:
      owner, wheel_params = wheel_coast
      pulse_lead = any(lead.present and (v_ego - lead.vLead > 0.5 or lead.aLeadK < -0.4 or
                                        lead.dRel < max(18.0, 2.0 * v_ego))
                       for lead in (sm['radarState'].leadOne, sm['radarState'].leadTwo))
      coast_plan = owner.sample(wheel_params, self.CP, sm, now_ns=sample_now_ns, target_mps=v_cruise,
        lead_relevant=bool(pulse_lead), stop_context=bool(sm['carState'].standstill or sm['controlsState'].forceDecel or
        self.force_stop_plan.forcing or sm['modelV2'].action.shouldStop or not self.allow_throttle))
      if coast_plan.speed_ceiling_mps is not None:
        v_cruise = min(v_cruise, coast_plan.speed_ceiling_mps)
    if sm['controlsState'].forceDecel or coast_plan is not None and coast_plan.force_decel:
      v_cruise = 0.0

    self.v_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC, self.mpc.v_solution)
    self.a_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC, self.mpc.a_solution)
    self.j_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC[:-1], self.mpc.j_solution)

    # TODO counter is only needed because radar is glitchy, remove once radar is gone
    self.fcw = self.mpc.crash_cnt > 2 and not sm['carState'].standstill
    if self.fcw:
      cloudlog.info("FCW triggered")

    # Save starting point for next iteration
    a_prev = self.output_a_target

    action_t =  self.CP.longitudinalActuatorDelay + DT_MDL
    output_a_target_mpc = get_accel_from_plan(self.v_desired_trajectory, self.a_desired_trajectory, CONTROL_N_T_IDX,
                                              action_t=action_t)
    output_should_stop_mpc = forecast_should_stop(
      self.CP, self.v_desired_trajectory, CONTROL_N_T_IDX, action_t,
      fallback=should_stop(v_ego, output_a_target_mpc))
    output_a_target_e2e = sm['modelV2'].action.desiredAcceleration
    output_should_stop_e2e = sm['modelV2'].action.shouldStop

    relevant_lead = any(braking_lead_relevant(lead, v_ego) for lead in
                        (sm['radarState'].leadOne, sm['radarState'].leadTwo))
    global_magnitude = ({'standard': 1.2, 'eco': 0.6, 'sport': 2.4}.get(global_braking_response)
                        if type(global_braking_response) is str else None)
    selected_braking = (selected_profiles.cruise_brake_magnitude
                        if profile_eligible and selected_profiles is not None else None)
    if selected_braking is not None:
      global_magnitude = selected_braking  # One resolved response, never multiplied or stacked.
      global_braking_response = selected_profiles.braking_style
    global_selected = (global_magnitude is not None and profile_eligible and (traffic_mode is False or selected_braking is not None) and
                       not sm['controlsState'].forceDecel and not sm['carState'].standstill and
                       not sm['carState'].brakePressed and not sm['carState'].gasPressed and
                       not relevant_lead and not self.force_stop_plan.forcing and not sm['modelV2'].action.shouldStop and
                       not output_should_stop_mpc and
                       (selected_braking is not None or self.last_profile is None or profile_tuning is None or
                        profile_tuning.cruise_brake_magnitude is None))
    global_floor = -global_magnitude if global_selected else A_CRUISE_MIN
    cruise_profile = self.last_profile
    custom_traffic_braking = (traffic_mode is True and profile_eligible and cruise_profile is not None and
                              profile_tuning is not None and profile_tuning.traffic_braking_custom is True and
                              not sm['controlsState'].forceDecel)
    if custom_traffic_braking and (sm['carState'].standstill or sm['radarState'].leadOne.present or
                                   sm['radarState'].leadTwo.present):
      cruise_profile = replace(cruise_profile, cruise_brake_magnitude=TRAFFIC_CRUISE_BRAKE_MAGNITUDE)
      self.profile_smoother.applied = cruise_profile
      self.last_profile = cruise_profile
    if global_selected and cruise_profile is not None:
      cruise_profile = replace(cruise_profile, cruise_brake_magnitude=global_magnitude)
    if sm['controlsState'].forceDecel:
      cruise_profile = None
    elif (ceiling.effective_mps is not None or curve.effective_mps is not None) and cruise_profile is not None:
      # An eligible lower ceiling must retain at least native approach
      # braking even when the saved profile requests a softer cruise response.
      cruise_profile = replace(cruise_profile, cruise_brake_magnitude=max(cruise_profile.cruise_brake_magnitude,
                                                                          abs(A_CRUISE_MIN)))
    if ceiling.effective_mps is not None or curve.effective_mps is not None:
      global_floor = min(global_floor, A_CRUISE_MIN)
    slc_floor = slc_coast_floor(
      v_ego=v_ego, slc_target=ceiling.effective_mps if curve.effective_mps is None and not traffic_mode else None,
      driver_cruise=v_cruise_kph * CV.KPH_TO_MS,
      full_brake_floor=max(ACCEL_MIN, -cruise_profile.cruise_brake_magnitude) if cruise_profile is not None else global_floor,
      relevant_lead=relevant_lead,
      stop_context=bool(sm['carState'].standstill or sm['controlsState'].forceDecel or
                        self.force_stop_plan.forcing or sm['modelV2'].action.shouldStop or output_should_stop_mpc or
                        sm['selfdriveState'].experimentalMode or not sm['carControl'].longActive or not self.allow_throttle),
      braking_style=(global_braking_response if global_selected and global_braking_response is not None else
                     self.profile_smoother.slc_braking_style if self.last_profile is not None else 'standard'),
    )
    if selected_acceleration is not None and cruise_profile is not None:
      # The selected curve owns acceleration; following/jerks retain their owner.
      cruise_profile = replace(cruise_profile, acceleration_max=selected_acceleration)
    if coast_plan is not None and coast_plan.brake_floor is not None:
      global_floor = coast_plan.brake_floor
      cruise_profile = None
      slc_floor = None
    self.a_cruise = get_cruise_accel(sm['selfdriveState'].experimentalMode, v_cruise, v_ego,
                                     self.a_cruise, steer_angle_without_offset, self.CP, self.dt,
                                     accel_coast, self.allow_throttle, cruise_profile, slc_floor,
                                     base_brake_floor=global_floor, selected_acceleration_max=selected_acceleration)
    cruise_should_stop = should_stop(v_ego, self.a_cruise)

    candidates = [(output_a_target_mpc, self.mpc.source, output_should_stop_mpc),
                  (self.a_cruise, LongitudinalPlanSource.cruise, cruise_should_stop)]
    if sm['selfdriveState'].experimentalMode:
      candidates.append((output_a_target_e2e, LongitudinalPlanSource.e2e, output_should_stop_e2e))

    mpc_source = self.mpc.source
    output_a_target, self.mpc.source, _ = min(candidates, key=lambda c: c[0])
    # A curve candidate alone cannot own driver feedback. Lead/e2e braking and
    # an equal or lower SLC ceiling retain their own attribution.
    self.last_curve_ceiling_applied = (curve.effective_mps is not None and self.a_cruise < output_a_target_mpc and
                                      (not sm['selfdriveState'].experimentalMode or self.a_cruise < output_a_target_e2e))
    self.output_should_stop = self.force_stop_plan.should_stop or any(should_stop for _, _, should_stop in candidates)
    if conditional_handoff is None:
      self.experimental_release.reset()
    else:
      mpc_lead_index = {LongitudinalPlanSource.lead0: 0, LongitudinalPlanSource.lead1: 1}.get(mpc_source)
      release_cap = self.experimental_release.step(
        conditional_handoff, project_release(sm, self.CP, sample_now_ns, lead_index=mpc_lead_index,
                                             conditional_handoff=conditional_handoff),
        previous_target=a_prev, target=output_a_target, follow_seconds=float(self.mpc.params[0, 4]),
        blocked=bool(reset_state or self.output_should_stop or self.fcw))
      if release_cap is not None:
        output_a_target = min(output_a_target, release_cap)
    output_a_target = adjust_lead_behavior(
      target=output_a_target, sm=sm, cp=self.CP, now_ns=sample_now_ns, key=conditional_handoff,
      follow_seconds=float(self.mpc.params[0, 4]), mpc_target=output_a_target_mpc,
      cruise_target=self.a_cruise, model_target=output_a_target_e2e, stopping=self.output_should_stop,
      force_stop=self.force_stop_plan.forcing, traffic_mode=traffic_mode, accel_min=ACCEL_MIN)
    if faster_lead_takeoff:
      # Dom takeoff bypasses the standstill cruise slew, never its final bounds.
      takeoff_max = ACCEL_MAX if sm['selfdriveState'].experimentalMode else get_max_accel(v_ego)
      if cruise_profile is not None:
        takeoff_max = min(takeoff_max, cruise_profile.acceleration_max)
      if selected_acceleration is not None:
        takeoff_max = min(takeoff_max, selected_acceleration)
      a_total_max = np.interp(v_ego, _A_TOTAL_MAX_BP, _A_TOTAL_MAX_V)
      a_y = v_ego ** 2 * steer_angle_without_offset * CV.DEG_TO_RAD / (self.CP.steerRatio * self.CP.wheelbase)
      takeoff_max = min(takeoff_max, math.sqrt(max(a_total_max ** 2 - a_y ** 2, 0.)), max(0., v_cruise - v_ego))
      takeoff_frame = project_takeoff(
        sm, self.CP, now_ns=sample_now_ns, drive_id=takeoff_drive_id, stop_plan=self.force_stop_plan,
        acceleration_max=takeoff_max, mpc_accel=output_a_target_mpc, follow_seconds=float(self.mpc.params[0, 4]),
        blocked=bool(reset_state or self.fcw or not self.allow_throttle or traffic_mode is not False or
                     self.mpc.solution_status != 0))
      output_a_target, self.output_should_stop = self.lead_takeoff.step(
        True, takeoff_frame, output_a_target, self.output_should_stop)
    else:
      self.lead_takeoff.reset()
    self.output_a_target = np.clip(output_a_target, ACCEL_MIN, ACCEL_MAX)

    self.v_desired_filter.x = self.v_desired_filter.x + self.dt * (self.output_a_target + a_prev) / 2.0

  def publish(self, sm, pm):
    plan_send = messaging.new_message('longitudinalPlan')

    plan_send.valid = sm.all_checks(NATIVE_PLAN_INPUTS)

    longitudinalPlan = plan_send.longitudinalPlan
    longitudinalPlan.modelMonoTime = sm.logMonoTime['modelV2']
    longitudinalPlan.processingDelay = (plan_send.logMonoTime - sm.logMonoTime['modelV2']) / 1e9
    longitudinalPlan.solverExecutionTime = self.mpc.solve_time

    longitudinalPlan.speeds = self.v_desired_trajectory.tolist()
    longitudinalPlan.accels = self.a_desired_trajectory.tolist()
    longitudinalPlan.jerks = self.j_desired_trajectory.tolist()

    longitudinalPlan.hasLead = sm['radarState'].leadOne.present
    longitudinalPlan.longitudinalPlanSource = self.mpc.source
    longitudinalPlan.fcw = self.fcw

    longitudinalPlan.aTarget = float(self.output_a_target)
    longitudinalPlan.shouldStop = bool(self.output_should_stop)
    longitudinalPlan.forceStopHolding = bool(self.force_stop_plan.manual_hold)
    longitudinalPlan.allowBrake = True
    longitudinalPlan.allowThrottle = bool(self.allow_throttle)

    pm.send('longitudinalPlan', plan_send)
