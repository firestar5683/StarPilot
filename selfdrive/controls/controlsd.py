#!/usr/bin/env python3
import math
from numbers import Number

from cereal import car, custom, log
import cereal.messaging as messaging
from openpilot.common.constants import CV
from openpilot.common.params import Params
from openpilot.common.realtime import config_realtime_process, DT_CTRL, Priority, Ratekeeper
from openpilot.common.swaglog import cloudlog

from opendbc.car.car_helpers import interfaces
from opendbc.car.chrysler.values import pacifica_hybrid_aol_stock_acc_mode
from opendbc.car.gm.values import CAR as GM_CAR
from opendbc.car.vehicle_model import VehicleModel
from openpilot.selfdrive.controls.lib.drive_helpers import clip_curvature, get_lateral_active
from openpilot.selfdrive.controls.lib.latcontrol import LatControl
from openpilot.selfdrive.controls.lib.latcontrol_pid import LatControlPID
from openpilot.selfdrive.controls.lib.latcontrol_angle import LatControlAngle, STEER_ANGLE_SATURATION_THRESHOLD
from openpilot.selfdrive.controls.lib.latcontrol_torque import (
  BOLT_2018_2021_STEER_RATIO_TEST_SCALE,
  LatControlTorque,
  get_bolt_2017_steer_ratio_scale,
)
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.selfdrive.car.cruise_state import should_cancel_stock_cruise
from openpilot.selfdrive.modeld.modeld import LAT_SMOOTH_SECONDS
from openpilot.selfdrive.locationd.helpers import PoseCalibrator, Pose

from openpilot.starpilot.common.starpilot_variables import get_starpilot_toggles
from openpilot.starpilot.controls.lib.neural_network_feedforward import LatControlNNFF

State = log.SelfdriveState.OpenpilotState
LaneChangeState = log.LaneChangeState
LaneChangeDirection = log.LaneChangeDirection

ACTUATOR_FIELDS = tuple(car.CarControl.Actuators.schema.fields.keys())


def get_gm_hud_set_speed(set_speed_ms: float, starpilot_toggles) -> float:
  spoofed_speed = set_speed_ms

  set_speed_offset = float(getattr(starpilot_toggles, "set_speed_offset", 0.0) or 0.0)
  if spoofed_speed > 0 and set_speed_offset > 0:
    spoofed_speed += set_speed_offset * CV.KPH_TO_MS

  return spoofed_speed


def get_torque_control_params(CP, torque_params, starpilot_toggles, use_live_params: bool) -> tuple[float, float, float]:
  torque_tune = CP.lateralTuning.torque
  lat_accel_factor = torque_tune.latAccelFactor
  lat_accel_offset = torque_tune.latAccelOffset
  friction = torque_tune.friction

  use_custom_lat_accel = getattr(starpilot_toggles, "use_custom_latAccelFactor", False)
  use_custom_friction = getattr(starpilot_toggles, "use_custom_friction", False)

  if use_live_params:
    if not use_custom_lat_accel:
      lat_accel_factor = torque_params.latAccelFactorFiltered
      lat_accel_offset = torque_params.latAccelOffsetFiltered
    if not use_custom_friction:
      friction = torque_params.frictionCoefficientFiltered

  if use_custom_lat_accel:
    lat_accel_factor = starpilot_toggles.latAccelFactor
  if use_custom_friction:
    friction = starpilot_toggles.friction

  return lat_accel_factor, lat_accel_offset, friction


class Controls:
  def __init__(self) -> None:
    self.params = Params()
    cloudlog.info("controlsd is waiting for CarParams")
    self.CP = messaging.log_from_bytes(self.params.get("CarParams", block=True), car.CarParams)
    self.FPCP = messaging.log_from_bytes(self.params.get("StarPilotCarParams", block=True), custom.StarPilotCarParams)
    cloudlog.info("controlsd got CarParams")

    self.CI = interfaces[self.CP.carFingerprint](self.CP, self.FPCP)

    self.sm = messaging.SubMaster(['liveDelay', 'liveParameters', 'liveTorqueParameters', 'modelV2', 'selfdriveState',
                                   'liveCalibration', 'livePose', 'longitudinalPlan', 'lateralManeuverPlan', 'carState', 'carOutput',
                                   'driverMonitoringState', 'onroadEvents', 'driverAssistance'], poll='selfdriveState')
    self.pm = messaging.PubMaster(['carControl', 'controlsState'])

    self.steer_limited_by_safety = False
    self.curvature = 0.0
    self.desired_curvature = 0.0
    self.lc_smooth_elapsed = 0.0

    self.pose_calibrator = PoseCalibrator()
    self.calibrated_pose: Pose | None = None

    self.LoC = LongControl(self.CP)
    self.VM = VehicleModel(self.CP)
    self.LaC: LatControl
    if self.CP.steerControlType == car.CarParams.SteerControlType.angle:
      self.LaC = LatControlAngle(self.CP, self.CI, DT_CTRL)
    elif self.CP.lateralTuning.which() == 'pid':
      self.LaC = LatControlPID(self.CP, self.CI, DT_CTRL)
    elif self.CP.lateralTuning.which() == 'torque':
      self.LaC = LatControlTorque(self.CP, self.CI, DT_CTRL)

    self.sm = self.sm.extend(['liveDelay', 'starpilotCarState', 'starpilotPlan'])

    self.starpilot_toggles = get_starpilot_toggles()
    self.ecu_disable_failed = False
    self.ecu_disable_failed_checked = not self.CP.openpilotLongitudinalControl

    if self.CP.lateralTuning.which() == "torque" and (self.starpilot_toggles.nnff or self.starpilot_toggles.nnff_lite):
      self.LaC = LatControlNNFF(self.CP, self.CI, DT_CTRL)

  def update(self):
    self.sm.update(15)
    if self.sm.updated["liveCalibration"]:
      self.pose_calibrator.feed_live_calib(self.sm['liveCalibration'])
    if self.sm.updated["livePose"]:
      device_pose = Pose.from_live_pose(self.sm['livePose'])
      self.calibrated_pose = self.pose_calibrator.build_calibrated_pose(device_pose)

    if hasattr(self.LaC, "pid") and self.CP.lateralTuning.which() != "pid":
      self.LaC.pid._k_p = self.starpilot_toggles.steerKp

    if self.sm.updated['liveDelay'] and hasattr(self.LaC, "update_live_delay"):
      self.LaC.update_live_delay(self.sm['liveDelay'].lateralDelay)

    self.starpilot_toggles = get_starpilot_toggles(self.sm)

  def update_ecu_disable_failed(self):
    if self.ecu_disable_failed_checked:
      return

    # ControlsReady is set after CarInterface.init(), where Hyundai ECU disable
    # writes EcuDisableFailed. Once init has completed, the value is stable.
    if self.params.get_bool("ControlsReady"):
      self.ecu_disable_failed = self.params.get_bool("EcuDisableFailed")
      self.ecu_disable_failed_checked = True

  def state_control(self):
    CS = self.sm['carState']

    # Update VehicleModel
    lp = self.sm['liveParameters']
    x = max(lp.stiffnessFactor, 0.1)
    sr = max(lp.steerRatio, 0.1)
    if self.CP.carFingerprint == GM_CAR.CHEVROLET_BOLT_CC_2017:
      sr *= get_bolt_2017_steer_ratio_scale(CS.vEgo)
    elif self.CP.carFingerprint == GM_CAR.CHEVROLET_BOLT_CC_2018_2021:
      sr *= BOLT_2018_2021_STEER_RATIO_TEST_SCALE
    self.VM.update_params(x, sr)

    steer_angle_without_offset = math.radians(CS.steeringAngleDeg - lp.angleOffsetDeg)
    self.curvature = -self.VM.calc_curvature(steer_angle_without_offset, CS.vEgo, lp.roll)

    # Update Torque Params
    if self.CP.lateralTuning.which() == 'torque':
      torque_params = self.sm['liveTorqueParameters']
      force_auto_tune = getattr(self.starpilot_toggles, "force_auto_tune", False)
      use_live_params = self.sm.all_checks(['liveTorqueParameters']) and (torque_params.useParams or force_auto_tune)
      use_custom_torque_params = (
        getattr(self.starpilot_toggles, "use_custom_latAccelFactor", False) or
        getattr(self.starpilot_toggles, "use_custom_friction", False)
      )
      if use_live_params or use_custom_torque_params:
        lat_accel_factor, lat_accel_offset, friction = get_torque_control_params(self.CP, torque_params, self.starpilot_toggles, use_live_params)
        self.LaC.update_live_torque_params(lat_accel_factor, lat_accel_offset, friction)

    long_plan = self.sm['longitudinalPlan']
    model_v2 = self.sm['modelV2']

    CC = car.CarControl.new_message()
    CC.enabled = self.sm['selfdriveState'].enabled

    # Check which actuators can be enabled
    standstill = abs(CS.vEgo) <= max(self.CP.minSteerSpeed, 0.3) or CS.standstill
    CC.latActive = get_lateral_active(CC.enabled, self.sm['selfdriveState'].active,
                                      self.sm['starpilotCarState'].alwaysOnLateralEnabled,
                                      CS.steerFaultTemporary, CS.steerFaultPermanent,
                                      standstill, self.CP.steerAtStandstill,
                                      self.sm['starpilotPlan'].lateralCheck)
    # EcuDisableFailed is set when car started in READY mode (ECU disable was rejected)
    # Disable longitudinal so stock ACC works instead
    self.update_ecu_disable_failed()
    CC.longActive = CC.enabled and not any(e.overrideLongitudinal for e in self.sm['onroadEvents']) and not self.sm['starpilotCarState'].pauseLongitudinal and self.CP.openpilotLongitudinalControl and not self.ecu_disable_failed

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
    self.LoC.experimental_mode = bool(self.sm['selfdriveState'].experimentalMode)
    actuators.accel = float(min(self.LoC.update(CC.longActive, CS, long_plan.aTarget, long_plan.shouldStop, pid_accel_limits, self.starpilot_toggles), self.starpilot_toggles.max_desired_acceleration))

    # Steering PID loop and lateral MPC
    # Reset desired curvature to current to avoid violating the limits on engage
    if self.sm.valid['lateralManeuverPlan']:
      new_desired_curvature = self.sm['lateralManeuverPlan'].desiredCurvature if CC.latActive else self.curvature
    else:
      new_desired_curvature = model_v2.action.desiredCurvature if CC.latActive else self.curvature

    jerk_factor = 1.0
    lat_accel_factor = 1.0
    if self.starpilot_toggles.lane_change_pace < 10:
      t_target = self.starpilot_toggles.lane_change_t_target
      set_jerk = self.starpilot_toggles.lane_change_jerk_factor
      set_accel = self.starpilot_toggles.lane_change_lat_accel_factor
      in_lane_change = model_v2.meta.laneChangeState in (LaneChangeState.laneChangeStarting, LaneChangeState.laneChangeFinishing) \
          and CS.vEgo >= self.starpilot_toggles.minimum_lane_change_speed
      if in_lane_change or 0.0 < self.lc_smooth_elapsed < t_target:
        self.lc_smooth_elapsed = min(self.lc_smooth_elapsed + DT_CTRL, t_target)
        progress = self.lc_smooth_elapsed / t_target  # 0 → 1 over T seconds
        jerk_factor = set_jerk + (1.0 - set_jerk) * progress
        lat_accel_factor = set_accel + (1.0 - set_accel) * progress
        if not in_lane_change and self.lc_smooth_elapsed >= t_target:
          self.lc_smooth_elapsed = 0.0
      elif not in_lane_change:
        self.lc_smooth_elapsed = 0.0

    self.desired_curvature, curvature_limited = clip_curvature(CS.vEgo, self.desired_curvature, new_desired_curvature, lp.roll,
                                                               jerk_factor, lat_accel_factor)
    lat_delay = self.sm["liveDelay"].lateralDelay + LAT_SMOOTH_SECONDS

    actuators.curvature = self.desired_curvature
    steer, steeringAngleDeg, lac_log = self.LaC.update(CC.latActive, CS, self.VM, lp,
                                                       self.steer_limited_by_safety, self.desired_curvature,
                                                       curvature_limited, lat_delay,
                                                       self.calibrated_pose,
                                                       self.sm['modelV2'],
                                                       self.starpilot_toggles)
    actuators.torque = float(steer)
    actuators.steeringAngleDeg = float(steeringAngleDeg)

    if len(long_plan.speeds):
      actuators.speed = long_plan.speeds[-1]

    # Ensure no NaNs/Infs
    for p in ACTUATOR_FIELDS:
      attr = getattr(actuators, p)
      if not isinstance(attr, Number):
        continue

      if not math.isfinite(attr):
        cloudlog.error(f"actuators.{p} not finite {actuators.to_dict()}")
        setattr(actuators, p, 0.0)

    return CC, lac_log

  def publish(self, CC, lac_log):
    CS = self.sm['carState']
    long_plan = self.sm['longitudinalPlan']

    # Orientation and angle rates can be useful for carcontroller
    # Only calibrated (car) frame is relevant for the carcontroller
    CC.currentCurvature = self.curvature
    if self.calibrated_pose is not None:
      CC.orientationNED = self.calibrated_pose.orientation.xyz.tolist()
      CC.angularVelocity = self.calibrated_pose.angular_velocity.xyz.tolist()

    CC.cruiseControl.override = CC.enabled and not CC.longActive and self.CP.openpilotLongitudinalControl
    pacifica_hybrid_aol = pacifica_hybrid_aol_stock_acc_mode(
      self.CP.carFingerprint,
      self.CP.pcmCruise,
      CC.enabled,
      self.sm['starpilotCarState'].alwaysOnLateralEnabled,
    )
    cancel_requested = should_cancel_stock_cruise(self.CP, CS.cruiseState.enabled, CC.enabled)
    CC.cruiseControl.cancel = cancel_requested and not pacifica_hybrid_aol

    legacy_resume_hack = False
    if len(long_plan.speeds):
      planned_resume = long_plan.speeds[-1] > 0.1
      # Some stock-ACC SNG hacks still rely on the legacy "planner wants speed"
      # signal rather than longitudinalPlan.shouldStop going false first.
      legacy_resume_hack = planned_resume and (
        (self.CP.brand == "toyota" and self.CP.openpilotLongitudinalControl and not self.CP.autoResumeSng) or
        (self.CP.brand == "gm" and getattr(self.starpilot_toggles, "volt_sng", False))
      )

    CC.cruiseControl.resume = CC.enabled and CS.cruiseState.standstill and (
      not self.sm['longitudinalPlan'].shouldStop or legacy_resume_hack
    )

    hudControl = CC.hudControl
    hud_set_speed = float(CS.vCruiseCluster * CV.KPH_TO_MS)
    gm_dash_spoof_offsets_enabled = (
      self.CP.brand == "gm" and
      self.CP.openpilotLongitudinalControl and
      self.CP.enableGasInterceptorDEPRECATED and
      getattr(self.starpilot_toggles, "gm_pedal_longitudinal", True) and
      not getattr(self.starpilot_toggles, "disable_openpilot_long", False) and
      getattr(self.starpilot_toggles, "gm_dash_spoof_offsets", False)
    )
    if gm_dash_spoof_offsets_enabled:
      hud_set_speed = get_gm_hud_set_speed(hud_set_speed, self.starpilot_toggles)
    hudControl.setSpeed = hud_set_speed
    hudControl.speedVisible = CC.enabled
    hudControl.lanesVisible = CC.enabled
    hudControl.leadVisible = self.sm['longitudinalPlan'].hasLead
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
    cs.forceDecel = bool((self.sm['driverMonitoringState'].awarenessStatus < 0.) or
                         (self.sm['selfdriveState'].state == State.softDisabling) or self.sm["starpilotCarState"].forceCoast)

    lat_tuning = self.CP.lateralTuning.which()
    if self.CP.steerControlType == car.CarParams.SteerControlType.angle:
      cs.lateralControlState.angleState = lac_log
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
