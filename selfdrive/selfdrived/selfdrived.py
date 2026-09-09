#!/usr/bin/env python3
import json
import os
import time
import threading

import cereal.messaging as messaging

from cereal import car, custom, log
from msgq.visionipc import VisionIpcClient, VisionStreamType


from opendbc.car.chrysler.values import pacifica_hybrid_aol_stock_acc_mode
from opendbc.car.gm.values import GMFlags
from opendbc.car.hyundai.values import CAR as HYUNDAI_CAR
from opendbc.car.nissan.values import CAR as NISSAN_CAR

from openpilot.common.params import Params
from openpilot.common.realtime import config_realtime_process, Priority, Ratekeeper, DT_CTRL
from openpilot.common.swaglog import cloudlog
from openpilot.common.gps import get_gps_location_service

from openpilot.selfdrive.car.car_specific import CarSpecificEvents
from openpilot.selfdrive.car.cruise_state import should_flag_cruise_mismatch
from openpilot.selfdrive.locationd.helpers import PoseCalibrator, Pose
from openpilot.selfdrive.selfdrived.events import Events, ET
from openpilot.selfdrive.selfdrived.helpers import ExcessiveActuationCheck
from openpilot.selfdrive.selfdrived.state import StateMachine
from openpilot.selfdrive.selfdrived.alertmanager import AlertManager, set_offroad_alert
from openpilot.selfdrive.selfdrived.alert_sound import filter_forcing_stop_alert_sound

from openpilot.system.version import get_build_metadata
from openpilot.system.hardware import HARDWARE

from openpilot.starpilot.common.starpilot_utilities import contains_event_type
from openpilot.starpilot.common.starpilot_variables import get_starpilot_toggles
from openpilot.starpilot.common.lateral_only_experimental import experimental_mode_available
from openpilot.starpilot.common.longitudinal_mode import request_mode_refresh
from openpilot.starpilot.common.vision_bsm import get_fresh_vasm_state
from openpilot.starpilot.system.wheel_controls import (
  CONTROLLER_ACTION_COUNTERS,
  CONTROLLER_ACTION_DISENGAGE,
  CONTROLLER_ACTION_ENGAGE,
)

REPLAY = "REPLAY" in os.environ
SIMULATION = "SIMULATION" in os.environ
TESTING_CLOSET = "TESTING_CLOSET" in os.environ

LONGITUDINAL_PERSONALITY_MAP = {v: k for k, v in log.LongitudinalPersonality.schema.enumerants.items()}

ThermalStatus = log.DeviceState.ThermalStatus
State = log.SelfdriveState.OpenpilotState
PandaType = log.PandaState.PandaType
LaneChangeState = log.LaneChangeState
LaneChangeDirection = log.LaneChangeDirection
EventName = log.OnroadEvent.EventName
ButtonType = car.CarState.ButtonEvent.Type
SafetyModel = car.CarParams.SafetyModel
AlertLevel = log.DriverMonitoringState.AlertLevel
MonitoringPolicy = log.DriverMonitoringState.MonitoringPolicy

StarPilotEventName = custom.StarPilotOnroadEvent.EventName

IGNORED_SAFETY_MODES = (SafetyModel.silent, SafetyModel.noOutput)
VALID_ONLY_COMM_ISSUE_GRACE_FRAMES = max(1, round(0.5 / DT_CTRL))


def evaluate_comm_issue(all_checks: bool, all_alive: bool, all_freq_ok: bool,
                        valid_only_frames: int) -> tuple[bool, int]:
  if all_checks:
    return False, 0
  if not all_alive or not all_freq_ok:
    return True, 0

  valid_only_frames += 1
  return valid_only_frames >= VALID_ONLY_COMM_ISSUE_GRACE_FRAMES, valid_only_frames


def commanded_torque_at_max_for_saturation(CP, output: float) -> bool:
  torque_controller = (CP.steerControlType == car.CarParams.SteerControlType.torque and
                       CP.lateralTuning.which() == "torque")
  has_controller_grace = CP.carFingerprint == HYUNDAI_CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN
  return torque_controller and not has_controller_grace and abs(output) > 0.99


def controller_openpilot_event(CP, CS, enabled: bool, engage_requested: bool, disengage_requested: bool):
  if disengage_requested and enabled:
    return EventName.buttonCancel
  if engage_requested and not enabled and CS.canValid and (not CP.pcmCruise or CS.cruiseState.enabled):
    return EventName.buttonEnable
  return None


def should_loud_blindspot_alert_without_lateral(CS, sm, starpilot_toggles, combined_left_bsm=None, combined_right_bsm=None) -> bool:
  if not getattr(starpilot_toggles, "loud_blindspot_alert_when_disengaged", False):
    return False

  combined_left_bsm = CS.leftBlindspot if combined_left_bsm is None else combined_left_bsm
  combined_right_bsm = CS.rightBlindspot if combined_right_bsm is None else combined_right_bsm
  left_signal_blocked = bool(CS.leftBlinker and combined_left_bsm)
  right_signal_blocked = bool(CS.rightBlinker and combined_right_bsm)
  one_blinker = bool(CS.leftBlinker) != bool(CS.rightBlinker)
  if not (one_blinker and (left_signal_blocked or right_signal_blocked)):
    return False

  if sm['modelV2'].meta.laneChangeState == LaneChangeState.preLaneChange:
    direction = sm['modelV2'].meta.laneChangeDirection
    normal_lane_change_alert = (
      (left_signal_blocked and direction == LaneChangeDirection.left) or
      (right_signal_blocked and direction == LaneChangeDirection.right)
    )
    if normal_lane_change_alert:
      return False

  return (
    not sm['carControl'].latActive or
    not sm['starpilotPlan'].lateralCheck or
    sm['starpilotCarState'].pauseLateral
  )


def get_starpilot_alert_filters(current_alert_types: list[str], clear_event_types: set[str], starpilot_events: Events) -> tuple[list[str], set[str]]:
  starpilot_alert_types = list(current_alert_types)
  starpilot_clear_event_types = set(clear_event_types)

  if int(StarPilotEventName.lkasEnable) in starpilot_events.names:
    if ET.WARNING not in starpilot_alert_types:
      starpilot_alert_types.append(ET.WARNING)
    starpilot_clear_event_types.discard(ET.WARNING)

  # This alert is explicitly allowed while lateral is paused/off. The state
  # machine only exposes WARNING while active/AOL, so let this warning through.
  if StarPilotEventName.laneChangeBlockedLoud in starpilot_events.names:
    if ET.WARNING not in starpilot_alert_types:
      starpilot_alert_types.append(ET.WARNING)
    starpilot_clear_event_types.discard(ET.WARNING)

  return starpilot_alert_types, starpilot_clear_event_types


def add_tesla_preap_starpilot_events(CP, CS, FPCS, starpilot_events: Events, prev_pedal_long_active: bool) -> bool:
  if CP.brand != "tesla" or CP.carFingerprint != "TESLA_MODEL_S_PREAP":
    return False

  if CP.pcmCruise:
    if getattr(FPCS, 'teslaCCEngaged', False):
      starpilot_events.add(StarPilotEventName.teslaCCEngaged)
    if getattr(FPCS, 'teslaCCDisengaged', False):
      starpilot_events.add(StarPilotEventName.teslaCCDisengaged)
    if getattr(FPCS, 'teslaCCNotArmed', False):
      starpilot_events.add(StarPilotEventName.teslaCCNotArmed)
    return False

  from opendbc.car.tesla.preap.nap_conf import nap_conf
  if not nap_conf.pedal_calibrated:
    starpilot_events.add(StarPilotEventName.pedalNotCalibrated)

  if not CP.openpilotLongitudinalControl:
    return False

  pedal_long_active = bool(CS.cruiseState.enabled and getattr(FPCS, 'pedalLongActive', False))
  if pedal_long_active and not prev_pedal_long_active:
    starpilot_events.add(StarPilotEventName.pedalCruiseEnabled)
  elif prev_pedal_long_active and not pedal_long_active:
    starpilot_events.add(StarPilotEventName.pedalCruiseDisabled)

  if getattr(FPCS, 'pedalMaxRegen', False):
    starpilot_events.add(StarPilotEventName.pedalMaxRegen)

  return pedal_long_active


class SelfdriveD:
  def __init__(self, CP=None):
    self.params = Params()
    self.params_memory = Params(memory=True)

    # Ensure the current branch is cached, otherwise the first cycle lags
    build_metadata = get_build_metadata()

    if CP is None:
      cloudlog.info("selfdrived is waiting for CarParams")
      self.CP = messaging.log_from_bytes(self.params.get("CarParams", block=True), car.CarParams)
      cloudlog.info("selfdrived got CarParams")
    else:
      self.CP = CP

    self.car_events = CarSpecificEvents(self.CP)

    self.pose_calibrator = PoseCalibrator()
    self.calibrated_pose: Pose | None = None
    self.excessive_actuation_check = ExcessiveActuationCheck()
    self.allow_impossible_acceleration = self.params.get_bool("AllowImpossibleAcceleration")
    if self.allow_impossible_acceleration:
      self.clear_longitudinal_excessive_actuation_alert()
    self.excessive_actuation = self.params.get("Offroad_ExcessiveActuation") is not None

    # Setup sockets
    self.pm = messaging.PubMaster(['selfdriveState', 'onroadEvents'])

    self.gps_location_service = get_gps_location_service(self.params)
    self.gps_packets = [self.gps_location_service]
    self.sensor_packets = ["accelerometer", "gyroscope"]
    self.camera_packets = ["roadCameraState", "driverCameraState", "wideRoadCameraState"]

    # TODO: de-couple selfdrived with card/conflate on carState without introducing controls mismatches
    self.car_state_sock = messaging.sub_sock('carState', timeout=20)

    ignore = self.sensor_packets + self.gps_packets + ['alertDebug', 'lateralManeuverPlan']
    if SIMULATION:
      ignore += ['driverCameraState', 'managerState']
    if REPLAY:
      # no vipc in replay will make them ignored anyways
      ignore += ['roadCameraState', 'wideRoadCameraState']
    self.sm = messaging.SubMaster(['deviceState', 'pandaStates', 'peripheralState', 'modelV2', 'liveCalibration',
                                   'carOutput', 'driverMonitoringState', 'longitudinalPlan', 'livePose', 'liveDelay',
                                   'managerState', 'liveParameters', 'radarState', 'liveTorqueParameters',
                                   'controlsState', 'carControl', 'driverAssistance', 'alertDebug', 'userBookmark', 'audioFeedback',
                                   'lateralManeuverPlan'] + \
                                   self.camera_packets + self.sensor_packets + self.gps_packets,
                                  ignore_alive=ignore, ignore_avg_freq=ignore,
                                  ignore_valid=ignore, frequency=int(1/DT_CTRL))

    # read params
    self.is_metric = self.params.get_bool("IsMetric")
    self.is_ldw_enabled = self.params.get_bool("IsLdwEnabled")
    self.disengage_on_accelerator = self.params.get_bool("DisengageOnAccelerator")

    car_recognized = self.CP.brand != 'mock'

    # cleanup old params
    if not self.CP.alphaLongitudinalAvailable:
      self.params.remove("AlphaLongitudinalEnabled")
    if not experimental_mode_available(self.CP):
      self.params.remove("ExperimentalMode")

    self.CS_prev = car.CarState.new_message()
    self.AM = AlertManager()
    self.events = Events()

    self.initialized = False
    self.enabled = False
    self.active = False
    self.mismatch_counter = 0
    self.cruise_mismatch_counter = 0
    self.last_steering_pressed_frame = 0
    self.distance_traveled = 0
    self.last_functional_fan_frame = 0
    self.events_prev = []
    self.logged_comm_issue = None
    self.valid_only_comm_issue_frames = 0
    self.not_running_prev = None
    self.big_model_loading = False
    self.big_model_attempted = False
    self.big_model_active = False
    self.big_model_failed = False
    self.big_model_ready_t = 0.
    self.experimental_mode = False
    self.ecu_disable_failed = False
    self.ecu_disable_failed_checked = not (
      self.CP.openpilotLongitudinalControl and self.CP.carFingerprint == NISSAN_CAR.NISSAN_LEAF
    )
    self.safe_mode = self.params.get_bool("SafeMode")
    self.personality = log.LongitudinalPersonality.relaxed if self.safe_mode else self.params.get("LongitudinalPersonality", return_default=True)
    self.recalibrating_seen = False
    self.dm_lockout_set = False
    self.dm_uncertain_alerted = False
    self.state_machine = StateMachine()
    self.rk = Ratekeeper(100, print_delay_threshold=None)
    self.prev_pedal_long_active = False
    self._controller_openpilot_counters = {
      action: self.params_memory.get_int(CONTROLLER_ACTION_COUNTERS[action])
      for action in (CONTROLLER_ACTION_ENGAGE, CONTROLLER_ACTION_DISENGAGE)
    }

    # Determine startup event
    self.startup_event = StarPilotEventName.customStartupAlert
    if HARDWARE.get_device_type() == 'mici':
      self.startup_event = None
    if not car_recognized:
      self.startup_event = EventName.startupNoCar
    elif self.CP.secOcRequired and not self.CP.secOcKeyAvailable:
      self.startup_event = EventName.startupNoSecOcKey
    elif car_recognized and self.CP.passive:
      self.startup_event = EventName.startupNoControl

    if not car_recognized:
      self.events.add(EventName.carUnrecognized, static=True)
      set_offroad_alert("Offroad_CarUnrecognized", True)
    elif self.CP.passive:
      self.events.add(EventName.dashcamMode, static=True)

    self.sm = self.sm.extend(['starpilotCarState', 'starpilotPlan'])
    self.pm = self.pm.extend(['starpilotOnroadEvents', 'starpilotSelfdriveState'])

    self.starpilot_toggles = get_starpilot_toggles()

    self.starpilot_AM = AlertManager()
    self.starpilot_events = Events(starpilot=True)

    self.cancel_pressed_previously = False
    self.distance_pressed_previously = False
    self.display_timer = 0
    self.last_below_steer_speed_alert_time = -float("inf")
    self.last_steer_saturated_alert_time = -float("inf")
    self.forcing_stop_chime_played = False

    # Once-per-drive latch for belowSteerSpeed — shows the bottom alert once per
    # onroad session for the first below-min crossing, suppresses subsequent ones.
    self.below_steer_shown_this_drive = False
    self.below_steer_has_been_above_min = False
    self.below_steer_showing = False

    self.starpilot_events_prev = []

    self.has_menu = self.CP.brand == "gm" and not (self.CP.flags & GMFlags.NO_CAMERA.value)

    self.FPCP = messaging.log_from_bytes(self.params.get("StarPilotCarParams", block=True), custom.StarPilotCarParams)

  def update_ecu_disable_failed(self):
    if self.ecu_disable_failed_checked:
      return
    if self.CP.carFingerprint != NISSAN_CAR.NISSAN_LEAF:
      self.ecu_disable_failed_checked = True
      return

    if self.params.get_bool("ControlsReady"):
      self.ecu_disable_failed = self.params.get_bool("EcuDisableFailed")
      self.ecu_disable_failed_checked = True
      if self.ecu_disable_failed:
        self.CP = messaging.log_from_bytes(self.params.get("CarParams"), car.CarParams)
        self.FPCP = messaging.log_from_bytes(self.params.get("StarPilotCarParams"), custom.StarPilotCarParams)
        self.car_events = CarSpecificEvents(self.CP)

  def clear_longitudinal_excessive_actuation_alert(self):
    alert = self.params.get("Offroad_ExcessiveActuation")
    if not alert:
      return

    if isinstance(alert, bytes):
      try:
        alert = json.loads(alert.decode("utf-8", errors="replace"))
      except json.JSONDecodeError:
        return
    elif isinstance(alert, str):
      try:
        alert = json.loads(alert)
      except json.JSONDecodeError:
        return

    if not isinstance(alert, dict):
      return

    extra = alert.get("extra", "")
    if isinstance(extra, bytes):
      extra = extra.decode("utf-8", errors="replace")

    if str(extra).strip().lower() == "longitudinal":
      self.params.remove("Offroad_ExcessiveActuation")

  def _consume_controller_openpilot_action(self, action: str) -> bool:
    counter = self.params_memory.get_int(CONTROLLER_ACTION_COUNTERS[action])
    previous = self._controller_openpilot_counters[action]
    self._controller_openpilot_counters[action] = counter
    return counter > previous

  def update_events(self, CS):
    """Compute onroadEvents from carState"""

    self.update_ecu_disable_failed()
    self.events.clear()
    self.starpilot_events.clear()

    controller_engage_requested = self._consume_controller_openpilot_action(CONTROLLER_ACTION_ENGAGE)
    controller_disengage_requested = self._consume_controller_openpilot_action(CONTROLLER_ACTION_DISENGAGE)

    switchback_mode_enabled = self.params_memory.get_bool("SwitchbackModeEnabled")
    switchback_mode_cooldown = max(0.0, float(getattr(self.starpilot_toggles, "switchback_mode_cooldown", 0.0)))

    if not self.sm['deviceState'].started:
      self.below_steer_shown_this_drive = False
      self.below_steer_has_been_above_min = False
      self.below_steer_showing = False

    if not self.sm['deviceState'].started or not switchback_mode_enabled:
      self.last_below_steer_speed_alert_time = -float("inf")
      self.last_steer_saturated_alert_time = -float("inf")

    if self.sm['controlsState'].lateralControlState.which() == 'debugState':
      self.events.add(EventName.joystickDebug)
      self.startup_event = None

    loading = self.params.get_bool("UsbGpuLoading")
    if loading:
      self.big_model_attempted = True
    if self.big_model_loading and not loading:
      self.big_model_ready_t = time.monotonic()
    self.big_model_loading = loading
    if loading:
      self.events.add(EventName.bigModelLoading)

    big_active = self.params.get("UsbGpuActive")
    model_unavailable = self.big_model_active and self.sm.seen['modelV2'] and not self.sm.alive['modelV2']
    big_failed = self.big_model_attempted and not loading and (big_active is False or model_unavailable)
    if big_failed and not self.big_model_failed:
      self.events.add(EventName.bigModelFailed)
    self.big_model_failed = big_failed

    if big_active:
      self.big_model_active = True
    if not self.enabled and not model_unavailable:
      self.big_model_active = False

    if self.sm.recv_frame['lateralManeuverPlan'] > 0:
      self.starpilot_events.add(StarPilotEventName.lateralManeuver)
      self.startup_event = None
    elif self.sm.recv_frame['alertDebug'] > 0:
      self.events.add(EventName.longitudinalManeuver)
      self.startup_event = None

    # Add startup event
    if self.startup_event is not None:
      if self.startup_event in (StarPilotEventName.blockUser, StarPilotEventName.customStartupAlert):
        self.starpilot_events.add(self.startup_event)
      else:
        self.events.add(self.startup_event)
      self.startup_event = None

    # Don't add any more events if not initialized
    if not self.initialized:
      self.events.add(EventName.selfdriveInitializing)
      return

    # Check for user bookmark press (bookmark button or end of LKAS button feedback)
    if self.sm.updated['userBookmark']:
      self.events.add(EventName.userBookmark)

    if self.sm.updated['audioFeedback']:
      self.events.add(EventName.audioFeedback)

    # Don't add any more events while in dashcam mode
    if self.CP.passive:
      return

    controller_event = controller_openpilot_event(
      self.CP, CS, self.enabled, controller_engage_requested, controller_disengage_requested,
    )
    if controller_event is not None:
      self.events.add(controller_event)

    # Block resume if cruise never previously enabled
    resume_pressed = any(be.type in (ButtonType.accelCruise, ButtonType.resumeCruise) for be in CS.buttonEvents)
    if not self.CP.pcmCruise and CS.vCruise > 250 and resume_pressed:
      self.events.add(EventName.resumeBlocked)

    if not self.CP.notCar:
      # Block engaging until lockout times out or ignition reset
      if self.sm['driverMonitoringState'].lockout and not self.dm_lockout_set:
        self.params.put_bool("DriverTooDistracted", True)
        self.dm_lockout_set = True
      elif not self.sm['driverMonitoringState'].lockout and self.dm_lockout_set:
        self.params.remove("DriverTooDistracted")
        self.dm_lockout_set = False
      # No entry conditions
      if self.sm['driverMonitoringState'].lockout or self.sm['driverMonitoringState'].alwaysOnLockout:
        self.events.add(EventName.tooDistracted)
      # Alerts
      vision_dm = self.sm['driverMonitoringState'].activePolicy == MonitoringPolicy.vision
      if self.sm['driverMonitoringState'].alertLevel == AlertLevel.one:
        self.events.add(EventName.driverDistracted1 if vision_dm else EventName.driverUnresponsive1)
      elif self.sm['driverMonitoringState'].alertLevel == AlertLevel.two:
        self.events.add(EventName.driverDistracted2 if vision_dm else EventName.driverUnresponsive2)
      elif self.sm['driverMonitoringState'].alertLevel == AlertLevel.three:
        self.events.add(EventName.driverDistracted3 if vision_dm else EventName.driverUnresponsive3)
      # Warn consistent DM uncertainty
      if self.sm['driverMonitoringState'].visionPolicyState.uncertainOffroadAlertPercent >= 100 and not self.dm_uncertain_alerted:
        set_offroad_alert("Offroad_DriverMonitoringUncertain", True)
        self.dm_uncertain_alerted = True

    # Add car events, ignore if CAN isn't valid
    if CS.canValid:
      car_events = self.car_events.update(CS, self.CS_prev, self.sm['carControl']).to_msg()

      # Once-per-drive latch for belowSteerSpeed — match old MinSteerSpeedBanner 1:1.
      min_steer_speed = float(self.CP.minSteerSpeed)
      under_min = min_steer_speed > 0.0 and float(CS.vEgo) < min_steer_speed

      if not under_min:
        self.below_steer_has_been_above_min = True

      was_under_min_prev = min_steer_speed > 0.0 and float(self.CS_prev.vEgo) < min_steer_speed
      crossed_below = under_min and not was_under_min_prev
      if (not self.below_steer_shown_this_drive) and crossed_below and self.below_steer_has_been_above_min:
        self.below_steer_shown_this_drive = True
        self.below_steer_showing = True

      if self.below_steer_showing and not under_min:
        self.below_steer_showing = False

      # Fully own the event — strip brand emissions, inject our own while active.
      car_events = [e for e in car_events if e.name.raw != EventName.belowSteerSpeed]
      show_alert = self.below_steer_showing and under_min

      # Switchback cooldown: rate-limits the alert when car sits below min.
      if show_alert and switchback_mode_enabled and switchback_mode_cooldown > 0.0:
        now = time.monotonic()
        if (now - self.last_below_steer_speed_alert_time) < switchback_mode_cooldown:
          show_alert = False
        else:
          self.last_below_steer_speed_alert_time = now

      if show_alert:
        self.events.add(EventName.belowSteerSpeed)

      self.events.add_from_msg(car_events)

      self.prev_pedal_long_active = add_tesla_preap_starpilot_events(
        self.CP, CS, self.sm['starpilotCarState'], self.starpilot_events, self.prev_pedal_long_active
      )

      if (getattr(self.starpilot_toggles, "nostalgia_mode", False) and
          self.CP.openpilotLongitudinalControl and
          self.enabled and
          any(be.type == ButtonType.altButton2 for be in CS.buttonEvents)):
        self.events.add(EventName.buttonCancel)

      if self.CP.notCar:
        # wait for everything to init first
        if self.sm.frame > int(5. / DT_CTRL) and self.initialized:
          # body always wants to enable
          self.events.add(EventName.pcmEnable)

      gas_disable = CS.gasPressed and not self.CS_prev.gasPressed and self.disengage_on_accelerator
      brake_or_regen_disable = (
        (CS.brakePressed and (not self.CS_prev.brakePressed or not CS.standstill)) or
        (CS.regenBraking and (not self.CS_prev.regenBraking or not CS.standstill))
      )
      preap_steering_only_brake = (
        self.CP.brand == "tesla" and self.CP.carFingerprint == "TESLA_MODEL_S_PREAP" and
        self.CP.openpilotLongitudinalControl and not self.CP.pcmCruise
      )
      if gas_disable:
        self.events.add(EventName.pedalPressed)
      elif brake_or_regen_disable:
        if preap_steering_only_brake:
          self.events.add(EventName.gasPressedOverride)
        else:
          self.events.add(EventName.pedalPressed)

    # Create events for temperature, disk space, and memory
    if self.sm['deviceState'].thermalStatus >= ThermalStatus.overheated:
      self.events.add(EventName.overheat)
    if self.sm['deviceState'].freeSpacePercent < 7 and not SIMULATION:
      self.events.add(EventName.outOfSpace)
    if self.sm['deviceState'].memoryUsagePercent > 90 and not SIMULATION:
      self.events.add(EventName.lowMemory)

    # Alert if fan isn't spinning for 5 seconds
    if self.sm['peripheralState'].pandaType != log.PandaState.PandaType.unknown:
      if self.sm['peripheralState'].fanSpeedRpm < 500 and self.sm['deviceState'].fanSpeedPercentDesired > 50:
        # allow enough time for the fan controller in the panda to recover from stalls
        if (self.sm.frame - self.last_functional_fan_frame) * DT_CTRL > 15.0:
          self.events.add(EventName.fanMalfunction)
      else:
        self.last_functional_fan_frame = self.sm.frame

    # Handle calibration status
    cal_status = self.sm['liveCalibration'].calStatus
    if cal_status != log.LiveCalibrationData.Status.calibrated:
      if cal_status == log.LiveCalibrationData.Status.uncalibrated:
        self.events.add(EventName.calibrationIncomplete)
      elif cal_status == log.LiveCalibrationData.Status.recalibrating:
        if not self.recalibrating_seen:
          set_offroad_alert("Offroad_Recalibration", True)
        self.recalibrating_seen = True
        self.events.add(EventName.calibrationRecalibrating)
      else:
        self.events.add(EventName.calibrationInvalid)

    # Lane departure warning
    if self.is_ldw_enabled and self.sm.valid['driverAssistance']:
      if self.sm['driverAssistance'].leftLaneDeparture or self.sm['driverAssistance'].rightLaneDeparture:
        self.events.add(EventName.ldw)

    # ******************************************************************************************
    #  NOTE: To fork maintainers.
    #  Disabling or nerfing safety features will get you and your users banned from our servers.
    #  We recommend that you do not change these numbers from the defaults.
    if self.sm.updated['liveCalibration']:
      self.pose_calibrator.feed_live_calib(self.sm['liveCalibration'])
    if self.sm.updated['livePose']:
      device_pose = Pose.from_live_pose(self.sm['livePose'])
      self.calibrated_pose = self.pose_calibrator.build_calibrated_pose(device_pose)

    if self.calibrated_pose is not None:
      excessive_actuation = self.excessive_actuation_check.update(
        self.sm, CS, self.calibrated_pose, self.allow_impossible_acceleration
      )
      if not self.excessive_actuation and excessive_actuation is not None:
        set_offroad_alert("Offroad_ExcessiveActuation", True, extra_text=str(excessive_actuation))
        self.excessive_actuation = True

    if self.excessive_actuation:
      self.events.add(EventName.excessiveActuation)
    # ******************************************************************************************

    # Handle lane change - combine OEM BSM with fresh V-ASM state.
    blindspot_alert_added = False
    vasm_left, vasm_right = (False, False)
    if getattr(self.starpilot_toggles, "v_asm_enabled", False):
      vasm_left, vasm_right = get_fresh_vasm_state(self.params_memory)
    combined_left_bsm = CS.leftBlindspot or vasm_left
    combined_right_bsm = CS.rightBlindspot or vasm_right
    if self.sm['modelV2'].meta.laneChangeState == LaneChangeState.preLaneChange:
      direction = self.sm['modelV2'].meta.laneChangeDirection
      if (combined_left_bsm and direction == LaneChangeDirection.left) or \
         (combined_right_bsm and direction == LaneChangeDirection.right):
        blindspot_alert_added = True
        if self.starpilot_toggles.loud_blindspot_alert:
          self.starpilot_events.add(StarPilotEventName.laneChangeBlockedLoud)
        else:
          self.events.add(EventName.laneChangeBlocked)
      else:
        # Keep pre-lane-change prompts visible even when lane-width gate blocks the maneuver.
        # This preserves the onroad "Changing lanes" guidance while still surfacing
        # "No Lane Available" when the configured width threshold is not met.
        if direction == LaneChangeDirection.left:
          self.events.add(EventName.preLaneChangeLeft)
          if self.sm['starpilotPlan'].laneWidthLeft < self.starpilot_toggles.lane_detection_width:
            self.starpilot_events.add(StarPilotEventName.noLaneAvailable)
        elif direction == LaneChangeDirection.right:
          self.events.add(EventName.preLaneChangeRight)
          if self.sm['starpilotPlan'].laneWidthRight < self.starpilot_toggles.lane_detection_width:
            self.starpilot_events.add(StarPilotEventName.noLaneAvailable)
    elif self.sm['modelV2'].meta.laneChangeState in (LaneChangeState.laneChangeStarting,
                                                    LaneChangeState.laneChangeFinishing):
      self.events.add(EventName.laneChange)

    if not blindspot_alert_added and should_loud_blindspot_alert_without_lateral(CS, self.sm, self.starpilot_toggles, combined_left_bsm, combined_right_bsm):
      self.starpilot_events.add(StarPilotEventName.laneChangeBlockedLoud)

    for i, pandaState in enumerate(self.sm['pandaStates']):
      # All pandas must match the list of safetyConfigs, and if outside this list, must be silent or noOutput
      if i < len(self.CP.safetyConfigs):
        safety_mismatch = pandaState.safetyModel != self.CP.safetyConfigs[i].safetyModel or \
                          pandaState.safetyParam != self.FPCP.safetyConfigs[i].safetyParam or \
                          pandaState.alternativeExperience != self.FPCP.alternativeExperience
      else:
        safety_mismatch = pandaState.safetyModel not in IGNORED_SAFETY_MODES

      # safety mismatch allows some time for pandad to set the safety mode and publish it back from panda
      if (safety_mismatch and self.sm.frame*DT_CTRL > 10.) or pandaState.safetyRxChecksInvalid or self.mismatch_counter >= 200:
        self.events.add(EventName.controlsMismatch)

      if log.PandaState.FaultType.relayMalfunction in pandaState.faults:
        self.events.add(EventName.relayMalfunction)

    # Handle HW and system malfunctions
    # Order is very intentional here. Be careful when modifying this.
    # All events here should at least have NO_ENTRY and SOFT_DISABLE.
    num_events = len(self.events)

    if self.big_model_active and big_failed:
      self.events.add(EventName.bigModelFailed)

    not_running = {p.name for p in self.sm['managerState'].processes if not p.running and p.shouldBeRunning}
    if self.sm.recv_frame['managerState'] and len(not_running):
      if not_running != self.not_running_prev:
        cloudlog.event("process_not_running", not_running=not_running, error=True)
      self.not_running_prev = not_running
    if self.sm.recv_frame['managerState'] and not_running:
      self.events.add(EventName.processNotRunning)
    else:
      if not SIMULATION and not self.rk.lagging:
        if not self.sm.all_alive(self.camera_packets):
          self.events.add(EventName.cameraMalfunction)
        elif not self.sm.all_freq_ok(self.camera_packets):
          self.events.add(EventName.cameraFrameRate)
    if not REPLAY and self.rk.lagging:
      self.events.add(EventName.selfdrivedLagging)
    if self.sm['radarState'].radarErrors.canError:
      self.events.add(EventName.canError)
    elif self.sm['radarState'].radarErrors.radarUnavailableTemporary:
      self.events.add(EventName.radarTempUnavailable)
    elif any(self.sm['radarState'].radarErrors.to_dict().values()):
      self.events.add(EventName.radarFault)
    if not self.sm.valid['pandaStates']:
      self.events.add(EventName.usbError)
    if CS.canTimeout:
      self.events.add(EventName.canBusMissing)
    elif not CS.canValid and not self.starpilot_toggles.force_onroad:
      self.events.add(EventName.canError)

    # generic catch-all. ideally, a more specific event should be added above instead
    has_disable_events = contains_event_type(self.events, self.starpilot_events, ET.NO_ENTRY) and \
                         (contains_event_type(self.events, self.starpilot_events, ET.SOFT_DISABLE) or
                          contains_event_type(self.events, self.starpilot_events, ET.IMMEDIATE_DISABLE))
    no_system_errors = (not has_disable_events) or (len(self.events) == num_events)
    big_model_settling = self.big_model_loading or time.monotonic() < self.big_model_ready_t + 5.
    all_checks = self.sm.all_checks()
    all_alive = self.sm.all_alive() if not all_checks else True
    all_freq_ok = self.sm.all_freq_ok() if not all_checks else True
    report_comm_issue, self.valid_only_comm_issue_frames = evaluate_comm_issue(
      all_checks, all_alive, all_freq_ok, self.valid_only_comm_issue_frames,
    )
    if not all_checks and report_comm_issue and no_system_errors and not big_model_settling:
      if not all_alive:
        self.events.add(EventName.commIssue)
      elif not all_freq_ok:
        self.events.add(EventName.commIssueAvgFreq)
      else:
        self.events.add(EventName.commIssue)

      logs = {
        'invalid': [s for s, valid in self.sm.valid.items() if not valid],
        'not_alive': [s for s, alive in self.sm.alive.items() if not alive],
        'not_freq_ok': [s for s, freq_ok in self.sm.freq_ok.items() if not freq_ok],
      }
      if logs != self.logged_comm_issue:
        cloudlog.event("commIssue", error=True, **logs)
        self.logged_comm_issue = logs
    else:
      self.logged_comm_issue = None

    if not self.CP.notCar and not big_model_settling:
      if not self.sm['livePose'].posenetOK:
        self.events.add(EventName.posenetInvalid)
      if not self.sm['livePose'].inputsOK:
        self.events.add(EventName.locationdTemporaryError)
      if not self.sm['liveParameters'].valid and cal_status == log.LiveCalibrationData.Status.calibrated and not TESTING_CLOSET and (not SIMULATION or REPLAY):
        self.events.add(EventName.paramsdTemporaryError)

    # conservative HW alert. if the data or frequency are off, locationd will throw an error
    if any((self.sm.frame - self.sm.recv_frame[s])*DT_CTRL > 10. for s in self.sensor_packets):
      self.events.add(EventName.sensorDataInvalid)

    if not REPLAY:
      # Check for mismatch between openpilot and car's PCM
      pacifica_hybrid_aol = pacifica_hybrid_aol_stock_acc_mode(
        self.CP.carFingerprint,
        self.CP.pcmCruise,
        self.enabled,
        self.sm['starpilotCarState'].alwaysOnLateralEnabled,
      )
      preap_software_cruise = (
        self.CP.brand == "tesla" and self.CP.carFingerprint == "TESLA_MODEL_S_PREAP" and
        self.CP.openpilotLongitudinalControl and not self.CP.pcmCruise
      )
      effective_pcm_cruise = self.CP.pcmCruise or preap_software_cruise
      jeep_brake_hold = self.CP.brand == "chrysler" and getattr(CS, "brakeHoldActive", False)
      cruise_mismatch = should_flag_cruise_mismatch(self.CP, CS.cruiseState.enabled, self.enabled,
                                                    effective_pcm_cruise) and not pacifica_hybrid_aol and not jeep_brake_hold
      self.cruise_mismatch_counter = self.cruise_mismatch_counter + 1 if cruise_mismatch else 0
      if self.cruise_mismatch_counter > int(6. / DT_CTRL):
        self.events.add(EventName.cruiseMismatch)

    # Send a "steering required alert" if saturation count has reached the limit
    if CS.steeringPressed:
      self.last_steering_pressed_frame = self.sm.frame
    recent_steer_pressed = (self.sm.frame - self.last_steering_pressed_frame)*DT_CTRL < 2.0
    controlstate = self.sm['controlsState']
    lac = getattr(controlstate.lateralControlState, controlstate.lateralControlState.which())
    if lac.active and not recent_steer_pressed and not self.CP.notCar:
      clipped_speed = max(CS.vEgo, 0.3)
      actual_lateral_accel = controlstate.curvature * (clipped_speed**2)
      desired_lateral_accel = self.sm['modelV2'].action.desiredCurvature * (clipped_speed**2)
      undershooting = abs(desired_lateral_accel) / abs(1e-3 + actual_lateral_accel) > 1.2
      turning = abs(desired_lateral_accel) > 1.0
      commanded_torque_at_max = commanded_torque_at_max_for_saturation(self.CP, lac.output)
      # TODO: lac.saturated includes speed and other checks, should be pulled out
      if undershooting and turning and (lac.saturated or commanded_torque_at_max):
        now = time.monotonic()
        cooldown_active = switchback_mode_enabled and switchback_mode_cooldown > 0.0
        if not cooldown_active or (now - self.last_steer_saturated_alert_time) >= switchback_mode_cooldown:
          if switchback_mode_enabled:
            self.last_steer_saturated_alert_time = now

          if self.starpilot_toggles.goat_scream_alert:
            self.starpilot_events.add(StarPilotEventName.goatSteerSaturated)
          else:
            self.events.add(EventName.steerSaturated)

    # Check for FCW
    stock_long_is_braking = self.enabled and not self.CP.openpilotLongitudinalControl and CS.aEgo < -1.25
    model_fcw = self.sm['modelV2'].meta.hardBrakePredicted and not CS.brakePressed and not stock_long_is_braking
    planner_fcw = self.sm['longitudinalPlan'].fcw and self.enabled
    if (planner_fcw or model_fcw) and not self.CP.notCar:
      self.events.add(EventName.fcw)

    # GPS checks
    gps_ok = self.sm.recv_frame[self.gps_location_service] > 0 and (self.sm.frame - self.sm.recv_frame[self.gps_location_service]) * DT_CTRL < 2.0
    if not gps_ok and self.sm['livePose'].inputsOK and (self.distance_traveled > 1500):
      self.events.add(EventName.noGps)
    if gps_ok:
      self.distance_traveled = 0
    self.distance_traveled += abs(CS.vEgo) * DT_CTRL

    # TODO: fix simulator
    if not SIMULATION or REPLAY:
      if self.sm['modelV2'].frameDropPerc > 20:
        self.events.add(EventName.modeldLagging)

    # Decrement personality on configured steering-wheel button presses
    if self.CP.openpilotLongitudinalControl:
      cancel_pressed = False
      distance_pressed = False

      if self.starpilot_toggles.personality_profile_via_cancel:
        cancel_pressed |= bool(getattr(self.sm['starpilotCarState'], "cancelPressed", False))
        cancel_pressed &= not (
          self.sm['starpilotCarState'].cancelLongPressed or
          self.sm['starpilotCarState'].cancelVeryLongPressed
        )
      if self.starpilot_toggles.personality_profile_via_cancel_long:
        cancel_pressed |= self.sm['starpilotCarState'].cancelLongPressed
      if self.starpilot_toggles.personality_profile_via_cancel_very_long:
        cancel_pressed |= self.sm['starpilotCarState'].cancelVeryLongPressed

      if self.starpilot_toggles.personality_profile_via_distance:
        distance_pressed |= any(not be.pressed and be.type == ButtonType.gapAdjustCruise for be in CS.buttonEvents)
        distance_pressed &= not (self.sm['starpilotCarState'].distanceLongPressed or self.sm['starpilotCarState'].distanceVeryLongPressed)
      if self.starpilot_toggles.personality_profile_via_distance_long:
        distance_pressed |= self.sm['starpilotCarState'].distanceLongPressed
      if self.starpilot_toggles.personality_profile_via_distance_very_long:
        distance_pressed |= self.sm['starpilotCarState'].distanceVeryLongPressed
      if self.starpilot_toggles.personality_profile_via_lkas:
        distance_pressed |= any(not be.pressed and be.type == ButtonType.lkas for be in CS.buttonEvents)

      if not cancel_pressed and self.cancel_pressed_previously and not self.safe_mode:
        self.personality = (self.personality - 1) % 3
        self.params.put_nonblocking('LongitudinalPersonality', self.personality)
        self.events.add(EventName.personalityChanged)

      if not distance_pressed and self.distance_pressed_previously and not self.safe_mode:
        if self.display_timer > 0 or not self.has_menu:
          self.personality = (self.personality - 1) % 3
          self.params.put_nonblocking('LongitudinalPersonality', self.personality)
          self.events.add(EventName.personalityChanged)
        self.display_timer = 350

      self.cancel_pressed_previously = cancel_pressed
      self.distance_pressed_previously = distance_pressed

      self.display_timer -= 1

    self.starpilot_events.add_from_msg(self.sm['starpilotPlan'].starpilotEvents)

    # One plan owns both the selection and conditional result. A delayed/missed
    # toggle broadcast must not mix an old mode with the current plan result.
    self.experimental_mode = (not self.safe_mode and experimental_mode_available(self.CP) and (
      self.sm['starpilotPlan'].experimentalMode if not REPLAY or self.starpilot_toggles.conditional_experimental_mode
      or getattr(self.starpilot_toggles, "conditional_chill_mode", False)
      else self.experimental_mode or self.sm['starpilotPlan'].experimentalMode))

  def data_sample(self):
    _car_state = messaging.recv_one(self.car_state_sock)
    CS = _car_state.carState if _car_state else self.CS_prev

    self.sm.update(0)

    if not self.initialized:
      all_valid = CS.canValid and self.sm.all_checks()
      timed_out = self.sm.frame * DT_CTRL > 6.
      if all_valid or timed_out or (SIMULATION and not REPLAY):
        available_streams = VisionIpcClient.available_streams("camerad", block=False)
        if VisionStreamType.VISION_STREAM_ROAD not in available_streams:
          self.sm.ignore_alive.append('roadCameraState')
          self.sm.ignore_valid.append('roadCameraState')
        if VisionStreamType.VISION_STREAM_WIDE_ROAD not in available_streams:
          self.sm.ignore_alive.append('wideRoadCameraState')
          self.sm.ignore_valid.append('wideRoadCameraState')

        if REPLAY and any(ps.controlsAllowed for ps in self.sm['pandaStates']):
          self.state_machine.state = State.enabled

        self.initialized = True
        cloudlog.event(
          "selfdrived.initialized",
          dt=self.sm.frame*DT_CTRL,
          timeout=timed_out,
          canValid=CS.canValid,
          invalid=[s for s, valid in self.sm.valid.items() if not valid],
          not_alive=[s for s, alive in self.sm.alive.items() if not alive],
          not_freq_ok=[s for s, freq_ok in self.sm.freq_ok.items() if not freq_ok],
          error=True,
        )

    # When the panda and selfdrived do not agree on controls_allowed
    # we want to disengage openpilot. However the status from the panda goes through
    # another socket other than the CAN messages and one can arrive earlier than the other.
    # Therefore we allow a mismatch for two samples, then we trigger the disengagement.
    if not self.enabled:
      self.mismatch_counter = 0

    # All pandas not in silent mode must have controlsAllowed when openpilot is enabled
    if self.enabled and any(not ps.controlsAllowed for ps in self.sm['pandaStates']
           if ps.safetyModel not in IGNORED_SAFETY_MODES):
      self.mismatch_counter += 1

    return CS

  def update_alerts(self, CS):
    clear_event_types = set()
    if ET.WARNING not in self.state_machine.current_alert_types:
      clear_event_types.add(ET.WARNING)
    if self.enabled:
      clear_event_types.add(ET.NO_ENTRY)

    pers = LONGITUDINAL_PERSONALITY_MAP[self.personality]
    alerts = self.events.create_alerts(self.state_machine.current_alert_types, [self.CP, CS, self.sm, self.is_metric,
                                                                                self.state_machine.soft_disable_timer, pers,
                                                                                self.starpilot_toggles])
    self.AM.add_many(self.sm.frame, alerts)
    self.AM.process_alerts(self.sm.frame, clear_event_types)

    starpilot_alert_types, starpilot_clear_event_types = get_starpilot_alert_filters(
      self.state_machine.current_alert_types, clear_event_types, self.starpilot_events
    )
    starpilot_alerts = self.starpilot_events.create_alerts(starpilot_alert_types, [self.CP, CS, self.sm, self.is_metric,
                                                                                                    self.state_machine.soft_disable_timer, pers,
                                                                                                    self.starpilot_toggles])
    self.starpilot_AM.add_many(self.sm.frame, starpilot_alerts)
    self.starpilot_AM.process_alerts(self.sm.frame, starpilot_clear_event_types)

  def publish_selfdriveState(self, CS):
    # selfdriveState
    ss_msg = messaging.new_message('selfdriveState')
    ss_msg.valid = True
    ss = ss_msg.selfdriveState
    ss.enabled = self.enabled
    ss.active = self.active
    ss.state = self.state_machine.state
    ss.engageable = not contains_event_type(self.events, self.starpilot_events, ET.NO_ENTRY)
    ss.experimentalMode = self.experimental_mode
    ss.personality = self.personality

    ss.alertText1 = self.AM.current_alert.alert_text_1
    ss.alertText2 = self.AM.current_alert.alert_text_2
    ss.alertSize = self.AM.current_alert.alert_size
    ss.alertStatus = self.AM.current_alert.alert_status
    ss.alertType = self.AM.current_alert.alert_type
    ss.alertSound = self.AM.current_alert.audible_alert
    ss.alertHudVisual = self.AM.current_alert.visual_alert

    self.pm.send('selfdriveState', ss_msg)

    # onroadEvents - logged every second or on change
    if (self.sm.frame % int(1. / DT_CTRL) == 0) or (self.events.names != self.events_prev):
      ce_send = messaging.new_message('onroadEvents', len(self.events))
      ce_send.valid = True
      ce_send.onroadEvents = self.events.to_msg()
      self.pm.send('onroadEvents', ce_send)
    self.events_prev = self.events.names.copy()

    fpss_msg = messaging.new_message('starpilotSelfdriveState')
    fpss_msg.valid = True
    fpss = fpss_msg.starpilotSelfdriveState

    fpss.alertText1 = self.starpilot_AM.current_alert.alert_text_1
    fpss.alertText2 = self.starpilot_AM.current_alert.alert_text_2
    fpss.alertSize = self.starpilot_AM.current_alert.alert_size
    fpss.alertStatus = self.starpilot_AM.current_alert.alert_status
    fpss.alertType = self.starpilot_AM.current_alert.alert_type
    fpss.vEgo = CS.vEgo
    fpss.alertSound, self.forcing_stop_chime_played = filter_forcing_stop_alert_sound(
      fpss.alertType,
      self.starpilot_AM.current_alert.audible_alert,
      bool(self.sm["starpilotPlan"].forcingStop),
      self.forcing_stop_chime_played,
    )

    self.pm.send('starpilotSelfdriveState', fpss_msg)

    if (self.sm.frame % int(1. / DT_CTRL) == 0) or (self.starpilot_events.names != self.starpilot_events_prev):
      fpce_send = messaging.new_message('starpilotOnroadEvents')
      fpce_send.valid = True
      fpce_send.starpilotOnroadEvents.events = self.starpilot_events.to_msg()
      self.pm.send('starpilotOnroadEvents', fpce_send)
    self.starpilot_events_prev = self.starpilot_events.names.copy()

  def step(self):
    CS = self.data_sample()
    self.update_events(CS)
    if not self.CP.passive and self.initialized:
      self.enabled, self.active = self.state_machine.update(self.events, self.starpilot_events, self.sm['starpilotCarState'].alwaysOnLateralEnabled)
    self.update_alerts(CS)

    self.publish_selfdriveState(CS)

    self.CS_prev = CS

    self.starpilot_toggles = get_starpilot_toggles(self.sm)

  def params_thread(self, evt):
    while not evt.is_set():
      self.safe_mode = self.params.get_bool("SafeMode")
      self.is_metric = self.params.get_bool("IsMetric")
      self.is_ldw_enabled = self.params.get_bool("IsLdwEnabled")
      self.disengage_on_accelerator = self.params.get_bool("DisengageOnAccelerator")
      if REPLAY:
        # Older replay input sets omit starpilotPlan and its ordinary EXP bit.
        # Preserve Dom's historical Params path only for offline replay.
        if self.safe_mode:
          self.experimental_mode = False
        elif not self.starpilot_toggles.conditional_experimental_mode:
          self.experimental_mode = self.params.get_bool("ExperimentalMode") and experimental_mode_available(self.CP)
      else:
        # Off the driving loop: honor unnotified legacy mode writes, repeating
        # until a complete selection snapshot is actually published.
        request_mode_refresh(self.params, self.params_memory, self.starpilot_toggles)
      self.personality = log.LongitudinalPersonality.relaxed if self.safe_mode else self.params.get("LongitudinalPersonality", return_default=True)
      time.sleep(0.1)

  def run(self):
    e = threading.Event()
    t = threading.Thread(target=self.params_thread, args=(e, ))
    try:
      t.start()
      while True:
        self.step()
        self.rk.monitor_time()
    finally:
      e.set()
      t.join()


def main():
  # Run on core 5 (plannerd/radard, ~50% peak, FIFO prio 51) instead of sharing
  # the saturated core 4 with card+controlsd. Core 4 at 100% was starving
  # selfdrived's 100 Hz loop and firing selfdrivedLagging. selfdrived's higher
  # FIFO prio (53 > 51) lets it preempt the 20 Hz planner/radar when needed.
  # (Core 6 = camerad, core 7 = modeld are both timing-critical — avoid.)
  config_realtime_process(5, Priority.CTRL_HIGH)
  s = SelfdriveD()
  s.run()

if __name__ == "__main__":
  main()
