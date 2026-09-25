#!/usr/bin/env python3
import math
import os
import time
from numbers import Number

from openpilot.cereal import log
from opendbc.car.structs import car
import openpilot.cereal.messaging as messaging
from openpilot.common.constants import CV
from openpilot.common.params import Params
from openpilot.common.realtime import config_realtime_process, DT_CTRL, Priority, Ratekeeper
from openpilot.common.swaglog import cloudlog

from opendbc.car.car_helpers import interfaces
from opendbc.car.vehicle_model import VehicleModel
from openpilot.selfdrive.controls.lib.drive_helpers import clip_curvature
from openpilot.selfdrive.controls.lib.latcontrol import LatControl
from openpilot.selfdrive.controls.lib.latcontrol_pid import LatControlPID
from openpilot.selfdrive.controls.lib.latcontrol_angle import LatControlAngle, STEER_ANGLE_SATURATION_THRESHOLD
from openpilot.selfdrive.controls.lib.latcontrol_curvature import LatControlCurvature
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.selfdrive.modeld.modeld import LAT_SMOOTH_SECONDS
from openpilot.selfdrive.locationd.helpers import PoseCalibrator, Pose
from openpilot.starpilot.car.hyundai.lateral_fault import LateralFaultLatch
from openpilot.starpilot.feature_runtime import enabled as feature_enabled
from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences
from openpilot.starpilot.lateral.model_turn_assist import ModelTurnAssist, update_twitch_guard, bind_turn_assist
from openpilot.starpilot.aol.runtime import current_axis, current_native, ordinary_lateral_requested, ordinary_axis_acknowledged
from openpilot.starpilot.aol.vehicle import policy_for as axis_policy_for, ordinary_axis_request_allowed, allow_lateral_onset
from openpilot.starpilot.lateral.lane_centering import (
  LaneCenteringController, LaneCenteringInput, LaneCenteringRequest, LaneCenteringResult,
)
from openpilot.starpilot.lateral.lane_feedback import feedback_message
from openpilot.starpilot.lateral.lane_change_preferences import read_saved as read_lane_change, effective as lane_change_policy
from openpilot.starpilot.lateral.lane_change_smoothing import LaneChangeSmoother, limit_rate
from openpilot.starpilot.lateral.lane_runtime import LaneCenteringHost, runtime_supported as lane_runtime_supported
from openpilot.starpilot.lateral.torque_runtime import TorqueHost, runtime_enabled as torque_runtime_enabled
from openpilot.starpilot.lateral.controller_selection import learning_allowed, read_selection
from openpilot.starpilot.lateral.gain_runtime import create_gain_owner
from openpilot.starpilot.longitudinal.inputs import LongitudinalInputs
from openpilot.starpilot.longitudinal.output_max import OutputMaximum, final_output

State = log.SelfdriveState.OpenpilotState
LaneChangeState = log.LaneChangeState
LaneChangeDirection = log.LaneChangeDirection

ACTUATOR_FIELDS = tuple(car.CarControl.Actuators.schema.fields.keys())


class Controls:
  def __init__(self) -> None:
    self.params = Params()
    cloudlog.info("controlsd is waiting for CarParams")
    self.CP = messaging.log_from_bytes(self.params.get("CarParams", block=True), car.CarParams)
    cloudlog.info("controlsd got CarParams")

    self.CI = interfaces[self.CP.carFingerprint](self.CP)
    self.hyundai_lateral_fault = LateralFaultLatch(self.CP.carFingerprint)
    self.lateral_controller_selection = read_selection(self.params, self.CP)
    self.vehicle_startup_preferences = VehicleStartupPreferences.read(
      self.params, enabled=self.params.get_bool("OpenpilotEnabledToggle"))
    self.torque_learning_allowed = learning_allowed(self.params, self.CP, selection=self.lateral_controller_selection)
    self.aol_replay = feature_enabled(self.params, self.CP, 'aol', os.environ)
    self.ordinary_axis_ack_required = axis_policy_for(self.CP).ordinary_axis_ack_required
    self.longitudinal_inputs = LongitudinalInputs(self.CP, self.params, lambda: self.sm)
    self.longitudinal_output_maximum = OutputMaximum(self.params, self.CP)

    services = (['lateralDelay', 'vehicleParameters', 'lateralTorqueParameters', 'modelV2', 'selfdriveState',
                 'extrinsicsCalibration', 'deviceMotion', 'longitudinalPlan', 'lateralManeuverPlan', 'carState', 'carOutput',
                 'driverMonitoringState', 'onroadEvents', 'driverAssistance'] +
                (['aolAxisState', 'aolSafetyWire'] if self.aol_replay or self.ordinary_axis_ack_required else []))
    optional = self.longitudinal_inputs.optional_services
    if optional:
      self.sm = messaging.SubMaster(services + optional, poll='selfdriveState',
                                    ignore_alive=optional, ignore_valid=optional, ignore_avg_freq=optional)
    else:
      self.sm = messaging.SubMaster(services, poll='selfdriveState')
    self.pm = messaging.PubMaster(['carControl', 'controlsState', 'starpilotLateralState'])

    self.steer_limited_by_safety = False
    self.curvature = 0.0
    self.desired_curvature = 0.0
    self.model_turn_assist = ModelTurnAssist()
    self.lane_centering_controller = LaneCenteringController()
    self.lane_change_policy = lane_change_policy(read_lane_change(self.params))
    self.lane_change_smoother = LaneChangeSmoother()
    self.lane_centering_host = LaneCenteringHost(self.params) if lane_runtime_supported(self.CP) else None
    self.torque_host = (TorqueHost(self.params, self.CP, allow_learning=(self.torque_learning_allowed
                        if self.lateral_controller_selection.policy is not None else None))
                        if torque_runtime_enabled(self.CP, self.params) else None)
    self.last_lane_centering_result: LaneCenteringResult | None = None
    self.lane_centering_applied = 0.0

    self.pose_calibrator = PoseCalibrator()
    self.calibrated_pose: Pose | None = None

    self.lateral_gain_owner = None
    self.LoC = LongControl(self.CP)
    self.VM = VehicleModel(self.CP)
    self.LaC: LatControl
    if self.CP.steerControlType == car.CarParams.SteerControlType.angle:
      self.LaC = LatControlAngle(self.CP, self.CI, DT_CTRL)
    elif self.CP.steerControlType == car.CarParams.SteerControlType.curvature:
      self.LaC = LatControlCurvature(self.CP, self.CI, DT_CTRL)
    elif self.CP.lateralTuning.which() == 'pid':
      self.LaC = LatControlPID(self.CP, self.CI, DT_CTRL)
    elif self.CP.lateralTuning.which() == 'torque':
      self.LaC = LatControlTorque(self.CP, self.CI, DT_CTRL, controller_mode=self.lateral_controller_selection.mode,
                                 turn_assist=self.vehicle_startup_preferences.turn_assist)
      self.lateral_gain_owner = create_gain_owner(self.params, self.CP, self.LaC)
      cloudlog.info({"event": "torque controller selected", "controller": self.LaC.controller_mode.value,
                     "source": self.lateral_controller_selection.source,
                     "vehicle": self.CP.carFingerprint, "policy": self.LaC.controller_policy,
                     "automaticLearning": self.torque_learning_allowed, "startupParameterSource": "vehicle",
                     "startupTorque": {"factor": self.LaC.torque_params.latAccelFactor,
                                       "offset": self.LaC.torque_params.latAccelOffset,
                                       "friction": self.LaC.torque_params.friction},
                     "startupPidGain": [list(row) for row in self.LaC.pid._k_p],
                     "startupPidLimits": [self.LaC.pid.neg_limit, self.LaC.pid.pos_limit]})

    self.turn_assist_enabled = bind_turn_assist(self.LaC)

  def update(self):
    self.sm.update(15)
    if self.sm.updated["extrinsicsCalibration"]:
      self.pose_calibrator.feed_extrinsics_calibration(self.sm['extrinsicsCalibration'])
    if self.sm.updated["deviceMotion"]:
      device_motion = Pose.from_device_motion(self.sm['deviceMotion'])
      self.calibrated_pose = self.pose_calibrator.build_calibrated_pose(device_motion)

  def state_control(self, *, lane_centering: LaneCenteringRequest | None = None):
    CS = self.sm['carState']
    if self.lateral_gain_owner is not None:
      self.lateral_gain_owner.refresh()

    # Update VehicleModel
    lp = self.sm['vehicleParameters']
    x = max(lp.stiffnessFactor, 0.1)
    sr = max(lp.steerRatio, 0.1)
    torque_extension = getattr(self.LaC, 'starpilot_extension', None)
    if torque_extension is not None:
      sr = torque_extension.vehicle_model_ratio(sr, CS.vEgo)
    self.VM.update_params(x, sr)

    steer_angle_without_offset = math.radians(CS.steeringAngleDeg - lp.angleOffsetDeg)
    self.curvature = -self.VM.calc_curvature(steer_angle_without_offset, CS.vEgo, lp.roll)

    # Update Torque Params
    if self.CP.lateralTuning.which() == 'torque' and self.torque_host is None and self.torque_learning_allowed:
      torque_params = self.sm['lateralTorqueParameters']
      if self.sm.all_checks(['lateralTorqueParameters']) and torque_params.useParams:
        self.LaC.update_torque_parameters(torque_params.latAccelFactorFiltered, torque_params.latAccelOffsetFiltered,
                                           torque_params.frictionCoefficientFiltered)

    long_plan = self.sm['longitudinalPlan']
    model_v2 = self.sm['modelV2']

    CC = car.CarControl.new_message()
    CC.enabled = self.sm['selfdriveState'].enabled

    # Check which actuators can be enabled
    standstill = abs(CS.vEgo) <= max(self.CP.minSteerSpeed, 0.3) or CS.standstill
    lateral_requested = self.sm['selfdriveState'].enabled and self.sm['selfdriveState'].active
    CC.latActive = ordinary_lateral_requested(self.sm['selfdriveState'].active, CS, self.CP)
    CC.longActive = CC.enabled and not any(e.overrideLongitudinal for e in self.sm['onroadEvents']) and self.CP.openpilotLongitudinalControl
    CC.longActive = self.longitudinal_inputs.qualify_active(CC.longActive)
    if self.aol_replay:
      now_ns = int(self.sm.logMonoTime['carState']) if os.getenv('REPLAY') == '1' else time.monotonic_ns()
      axis = current_axis(self.sm, now_ns=now_ns)
      native = current_native(self.sm, self.CP, now_ns=now_ns,
                              axis_session_id=str(axis.sessionId) if axis is not None else None)
      acknowledged = axis is not None and native is not None and axis.nativeAcknowledged
      lateral_requested = bool(axis.desiredLateral) if axis is not None else None
      CC.latActive = bool(acknowledged and axis.lateralActive and
                          bool(axis.desiredLateral) == bool(native.requestedLateral) and native.lateralAllowed and
                          not CS.steerFaultTemporary and not CS.steerFaultPermanent and
                          (not standstill or self.CP.steerAtStandstill))
      CC.longActive = bool(acknowledged and axis.longitudinalActive and
                           bool(axis.desiredLongitudinal) == bool(native.requestedLongitudinal) and native.longitudinalAllowed and
                           self.CP.openpilotLongitudinalControl and
                           not any(e.overrideLongitudinal for e in self.sm['onroadEvents']))

    if getattr(self, 'ordinary_axis_ack_required', False):
      now_ns = int(self.sm.logMonoTime['carState']) if os.getenv('REPLAY') == '1' else time.monotonic_ns()
      CC.latActive = bool(CC.latActive and CS.canValid and not CS.canTimeout and
                          ordinary_axis_request_allowed(self.CP, CS) and
                          ordinary_axis_acknowledged(self.sm, self.CP, now_ns=now_ns))

    fault_latch = getattr(self, 'hyundai_lateral_fault', None)
    if fault_latch is not None:
      latched = fault_latch.update(requested=lateral_requested, temporary_fault=bool(CS.steerFaultTemporary),
                                   cruise_enabled=bool(CS.cruiseState.enabled))
      CC.latActive = bool(CC.latActive and not latched)

    CC.latActive = allow_lateral_onset(self.CP, requested=bool(CC.latActive), normal_enabled=bool(CC.enabled),
                                      steering_pressed=bool(CS.steeringPressed),
                                      previous_active=bool(getattr(self, 'aol_previous_lateral_active', False)))

    if self.torque_host is not None:
      # The optional source must not keep an active torque request through lost car state.
      CC.latActive = bool(CC.latActive and CS.canValid and not CS.canTimeout)
      now_ns = int(self.sm.logMonoTime['carState']) if os.getenv('REPLAY') == '1' else time.monotonic_ns()
      tune = self.torque_host.sample(self.sm, now_ns=now_ns, lat_active=bool(CC.latActive))
      self.torque_host.apply(self.LaC, tune)
      if not CC.latActive:
        self.LaC.pid.reset()

    actuators = CC.actuators
    actuators.longControlState = self.LoC.long_control_state

    # Enable blinkers while lane changing
    if model_v2.meta.laneChangeState != LaneChangeState.off:
      CC.leftBlinker = model_v2.meta.laneChangeDirection == LaneChangeDirection.left
      CC.rightBlinker = model_v2.meta.laneChangeDirection == LaneChangeDirection.right

    if not CC.latActive:
      self.LaC.reset()
    if not CC.longActive:
      self.LoC.reset()

    # accel PID loop
    pid_accel_limits = self.CI.get_pid_accel_limits(self.CP, CS.vEgo, CS.vCruise * CV.KPH_TO_MS)
    longitudinal_output = self.LoC.update(CC.longActive, CS, long_plan.aTarget, long_plan.shouldStop, pid_accel_limits,
                                          context=self.longitudinal_inputs.context(CC.longActive))
    actuators.accel = final_output(longitudinal_output, getattr(self, "longitudinal_output_maximum", None), time.monotonic_ns())
    if self.longitudinal_inputs.publish_state:
      # Publish the selected launch state to the vehicle controller in this same frame.
      actuators.longControlState = self.LoC.long_control_state

    # Steering PID loop and lateral MPC
    # Reset desired curvature to current to avoid violating the limits on engage
    if self.sm.valid['lateralManeuverPlan']:
      new_desired_curvature = self.sm['lateralManeuverPlan'].desiredCurvature if CC.latActive else self.curvature
    else:
      new_desired_curvature = model_v2.action.desiredCurvature if CC.latActive else self.curvature
    assist = self.turn_assist_enabled()
    rolling = math.isfinite(CS.vEgo) and CS.vEgo > max(.1 * CV.MPH_TO_MS, self.CP.minSteerSpeed)
    if (assist and rolling and self.sm.all_checks(['modelV2']) and CC.latActive and not CS.standstill and not CS.steerFaultTemporary and
        not CS.steerFaultPermanent and CS.gearShifter in (car.CarState.GearShifter.drive, car.CarState.GearShifter.low)):
      self.model_turn_assist.curvature = self.curvature
      self.model_turn_assist.twitch_guard_remaining = update_twitch_guard(self.model_turn_assist.twitch_guard_remaining, CS.vEgo, CS.standstill)
      new_desired_curvature = self.model_turn_assist.update(CS, model_v2, CC, new_desired_curvature)
    elif getattr(self, 'model_turn_assist', None) is not None:
      self.model_turn_assist.reset()
      self.model_turn_assist.twitch_guard_remaining = update_twitch_guard(0., CS.vEgo, CS.standstill)
    lane_base_curvature = new_desired_curvature
    self.lane_centering_applied = 0.0
    self.last_lane_centering_result = None
    if lane_centering is None and self.lane_centering_host is not None:
      now_ns = int(self.sm.logMonoTime['carState']) if os.getenv('REPLAY') == '1' else time.monotonic_ns()
      lane_centering = self.lane_centering_host.sample(self.sm, now_ns=now_ns,
                                                     lateral_active=CC.latActive, longitudinal_active=CC.longActive)
    if lane_centering is None:
      self.lane_centering_controller.reset()
    elif not isinstance(lane_centering, LaneCenteringRequest):
      self.lane_centering_controller.reset()
      self.last_lane_centering_result = LaneCenteringResult(None, 0.0, 0, "invalid_request")
    else:
      result = self.lane_centering_controller.update(LaneCenteringInput(
        model=model_v2, model_sample_id=self.sm.logMonoTime['modelV2'],
        model_valid=bool(self.sm.all_checks(['modelV2'])), base_curvature=new_desired_curvature,
        speed_mps=CS.vEgo, mode=lane_centering.mode, lateral_active=CC.latActive,
        settings=lane_centering.settings, elapsed_seconds=lane_centering.elapsed_seconds,
        turn_signal_active=bool(CS.leftBlinker or CS.rightBlinker), driver_override=bool(CS.steeringPressed),
        time_discontinuity=lane_centering.time_discontinuity,
      ))
      self.last_lane_centering_result = result
      if result.candidate_curvature is not None:
        new_desired_curvature = result.candidate_curvature
    previous_curvature = self.desired_curvature
    factor = self.lane_change_smoother.factor(
      active=bool(CC.latActive and CS.canValid and not CS.canTimeout and self.sm.all_checks(['modelV2']) and
                  self.lane_change_policy.enabled), lane_change_state=model_v2.meta.laneChangeState,
      speed=CS.vEgo, minimum_speed=self.lane_change_policy.minimum_speed_mps,
      duration=self.lane_change_policy.duration_s, previous=previous_curvature, desired=new_desired_curvature,
      turn_assist=assist)
    new_desired_curvature = limit_rate(CS.vEgo, previous_curvature, new_desired_curvature, factor)
    self.desired_curvature, curvature_limited = clip_curvature(CS.vEgo, previous_curvature, new_desired_curvature, lp.roll)
    if self.last_lane_centering_result is not None and self.last_lane_centering_result.correction != 0.0:
      baseline_curvature, _ = clip_curvature(CS.vEgo, previous_curvature, limit_rate(CS.vEgo, previous_curvature, lane_base_curvature, factor), lp.roll)
      self.lane_centering_applied = self.desired_curvature - baseline_curvature
    lat_delay = self.sm["lateralDelay"].lateralDelay + LAT_SMOOTH_SECONDS

    actuators.curvature = self.desired_curvature
    steer, lateral_output, lac_log = self.LaC.update(CC.latActive, CS, self.VM, lp,
                                                     self.steer_limited_by_safety, self.desired_curvature,
                                                     curvature_limited, lat_delay)
    actuators.torque = float(steer)
    if self.CP.steerControlType == car.CarParams.SteerControlType.curvature:
      actuators.curvature = float(lateral_output)
    else:
      actuators.steeringAngleDeg = float(lateral_output)
    # Ensure no NaNs/Infs
    for p in ACTUATOR_FIELDS:
      attr = getattr(actuators, p)
      if not isinstance(attr, Number):
        continue

      if not math.isfinite(attr):
        cloudlog.error(f"actuators.{p} not finite {actuators.to_dict()}")
        setattr(actuators, p, 0.0)

    self.aol_previous_lateral_active = bool(CC.latActive)
    return CC, lac_log

  def publish(self, CC, lac_log):
    CS = self.sm['carState']

    # Orientation and angle rates can be useful for carcontroller
    # Only calibrated (car) frame is relevant for the carcontroller
    CC.currentCurvature = self.curvature
    if self.calibrated_pose is not None:
      CC.orientationNED = self.calibrated_pose.orientation.xyz.tolist()
      CC.angularVelocity = self.calibrated_pose.angular_velocity.xyz.tolist()

    CC.cruiseControl.override = CC.enabled and not CC.longActive and self.CP.openpilotLongitudinalControl
    CC.cruiseControl.cancel = CS.cruiseState.enabled and (not CC.enabled or not self.CP.pcmCruise)
    CC.cruiseControl.resume = CC.enabled and CS.cruiseState.standstill and not self.sm['longitudinalPlan'].shouldStop

    hudControl = CC.hudControl
    hudControl.setSpeed = float(CS.vCruiseCluster * CV.KPH_TO_MS)
    hudControl.speedVisible = CC.enabled
    hudControl.lanesVisible = CC.enabled
    hudControl.leadVisible = self.sm['longitudinalPlan'].hasLead
    hudControl.leadVisible = self.longitudinal_inputs.lead_visible(hudControl.leadVisible)
    hudControl.leadDistanceBars = self.sm['selfdriveState'].personality.raw + 1
    hudControl.visualAlert = self.sm['selfdriveState'].alertHudVisual

    hudControl.rightLaneVisible = True
    hudControl.leftLaneVisible = True
    if self.sm.valid['driverAssistance']:
      hudControl.leftLaneDepart = self.sm['driverAssistance'].leftLaneDeparture
      hudControl.rightLaneDepart = self.sm['driverAssistance'].rightLaneDeparture

    if self.sm['selfdriveState'].active:
      CO = self.sm['carOutput']
      if self.CP.steerControlType == car.CarParams.SteerControlType.angle:
        self.steer_limited_by_safety = abs(CC.actuators.steeringAngleDeg - CO.actuatorsOutput.steeringAngleDeg) > \
                                              STEER_ANGLE_SATURATION_THRESHOLD
      else:
        self.steer_limited_by_safety = abs(CC.actuators.torque - CO.actuatorsOutput.torque) > 1e-2

    # TODO: both controlsState and carControl valids should be set by
    #       sm.all_checks(), but this creates a circular dependency

    # controlsState
    dat = messaging.new_message('controlsState')
    dat.valid = CS.canValid
    cs = dat.controlsState

    cs.curvature = self.curvature
    cs.longitudinalPlanMonoTime = self.sm.logMonoTime['longitudinalPlan']
    cs.lateralPlanMonoTime = self.sm.logMonoTime['modelV2']
    cs.desiredCurvature = self.desired_curvature
    cs.longControlState = self.LoC.long_control_state
    cs.upAccelCmd = float(self.LoC.pid.p)
    cs.uiAccelCmd = float(self.LoC.pid.i)
    cs.ufAccelCmd = float(self.LoC.pid.f)
    cs.forceDecel = bool(self.sm['driverMonitoringState'].noResponseForceDecel or
                         (self.sm['selfdriveState'].state == State.softDisabling))

    # trigger the car's stock driver monitoring escalation
    CC.driverMonitoringEscalation = cs.forceDecel

    lat_tuning = self.CP.lateralTuning.which()
    if self.CP.steerControlType == car.CarParams.SteerControlType.angle:
      cs.lateralControlState.angleState = lac_log
    elif self.CP.steerControlType == car.CarParams.SteerControlType.curvature:
      cs.lateralControlState.curvatureState = lac_log
    elif lat_tuning == 'pid':
      cs.lateralControlState.pidState = lac_log
    elif lat_tuning == 'torque':
      cs.lateralControlState.torqueState = lac_log

    self.pm.send('controlsState', dat)

    # carControl
    cc_send = messaging.new_message('carControl')
    cc_send.valid = CS.canValid
    cc_send.carControl = CC
    self.pm.send('carControl', cc_send)
    self.pm.send('starpilotLateralState', feedback_message(
      self.last_lane_centering_result, self.lane_centering_applied, CC.latActive,
      model_mono_time=self.sm.logMonoTime['modelV2'], car_control_mono_time=cc_send.logMonoTime,
      valid=bool(CS.canValid and self.sm.all_checks(['modelV2']))))

  def run(self):
    rk = Ratekeeper(100, print_delay_threshold=None)
    while True:
      self.update()
      CC, lac_log = self.state_control()
      self.publish(CC, lac_log)
      rk.monitor_time()


def main():
  config_realtime_process(4, Priority.CTRL_HIGH)
  controls = Controls()
  controls.run()


if __name__ == "__main__":
  main()
