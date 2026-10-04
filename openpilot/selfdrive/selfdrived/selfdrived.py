#!/usr/bin/env python3
import os
import math
import time
import threading
import uuid
from copy import copy

import openpilot.cereal.messaging as messaging

from openpilot.cereal import log
from opendbc.car.structs import car
from openpilot.cereal.visionipc import VisionStreamType
from msgq.visionipc import VisionIpcClient


from openpilot.common.params import Params
from openpilot.common.realtime import config_realtime_process, Priority, Ratekeeper, DT_CTRL
from openpilot.common.swaglog import cloudlog
from openpilot.common.gps import get_gps_location_service

from openpilot.selfdrive.car.car_events import CarEvents
from openpilot.selfdrive.locationd.helpers import PoseCalibrator, Pose
from openpilot.selfdrive.selfdrived.events import Events, ET, Alert, Priority as AlertPriority
from openpilot.starpilot.longitudinal.force_stop_alert import HoldAlertState, EVENT_TYPE as FORCE_STOP_HOLD
from openpilot.selfdrive.selfdrived.helpers import ExcessiveActuationCheck
from openpilot.selfdrive.selfdrived.state import StateMachine
from openpilot.starpilot.aol.intent import read_settings
from openpilot.starpilot.aol.runtime import (INTENT_MAX_AGE_NS, AxisDecision, current_intent, current_native, decide_axes,
                                            ordinary_lateral_requested, decide_ordinary_axis)
from openpilot.starpilot.aol.vehicle import policy_for as axis_policy_for, ordinary_axis_request_allowed
from openpilot.starpilot.conditional_mode.consumer import ConsumerResult, ModeConsumer
from openpilot.starpilot.conditional_mode.effective_status import publish_ack
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.manual import ioniq6_media_eligible
from openpilot.starpilot.controllers.mode_actions import SwitchbackStatusOwner, SwitchbackCooldown, ModeActionOwner
from openpilot.starpilot.conditional_mode.projection import paired_clocks_ns
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner
from openpilot.starpilot.conditional_mode.status import settings_fingerprint
from openpilot.starpilot.feature_runtime import enabled as feature_enabled
from openpilot.starpilot.nostalgia import aol_no_entry, paddle_cancel, physical_cancel, saved_enabled as nostalgia_saved_enabled
from openpilot.starpilot.lateral.lane_change_status_wire import alert_wording, decode as decode_lane_status, fresh_for_model
from openpilot.selfdrive.selfdrived.alertmanager import AlertManager, set_offroad_alert

from openpilot.common.version import get_build_metadata
from openpilot.common.hardware import HARDWARE

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

IGNORED_SAFETY_MODES = (SafetyModel.silent, SafetyModel.noOutput)


class SelfdriveD:
  def __init__(self, CP=None):
    self.params = Params()

    # Ensure the current branch is cached, otherwise the first cycle lags
    build_metadata = get_build_metadata()

    if CP is None:
      cloudlog.info("selfdrived is waiting for CarParams")
      self.CP = messaging.log_from_bytes(self.params.get("CarParams", block=True), car.CarParams)
      cloudlog.info("selfdrived got CarParams")
    else:
      self.CP = CP

    self.aol_replay = feature_enabled(self.params, self.CP, 'aol', os.environ)
    self.ordinary_axis_ack_required = axis_policy_for(self.CP).ordinary_axis_ack_required
    self.axis_transport_required = self.aol_replay or self.ordinary_axis_ack_required
    self.nostalgia_enabled = nostalgia_saved_enabled(self.params)
    self.nostalgia_paddle_cancel = False
    self.aol_session_id = uuid.uuid4().hex
    self.aol_sequence = 0
    self.aol_axis_decision = AxisDecision()
    self.aol_dm_lateral_inhibit = False
    self.force_stop_hold_alert = HoldAlertState()
    self.aol_car_state_log_ns = 0
    self.aol_last_intent = None
    self.lane_status_session = ""
    self.lane_status_sequence = -1
    self.conditional_replay = feature_enabled(self.params, self.CP, 'conditional', os.environ)
    self.conditional_settings = ConditionalSettingsOwner(self.params) if self.conditional_replay else None
    self.conditional_consumer = ModeConsumer() if self.conditional_replay else None
    self.conditional_status = 'disabled'
    self.controller_action_sock = messaging.sub_sock('slcAction', conflate=False)
    self.controller_action_owner = ModeActionOwner()
    self.switchback_capable = ioniq6_media_eligible(self.CP) and not self.CP.passive and not self.CP.dashcamOnly and not self.CP.notCar
    self.switchback_status = SwitchbackStatusOwner()
    self.switchback_cooldown = SwitchbackCooldown()
    self.switchback_setting_ns = 0
    self.switchback_cooldown_ns = 300_000_000_000
    self.conditional_car_state_valid = False
    self.conditional_ack_session = uuid.uuid4().hex
    self.conditional_ack_sequence = 0
    self.conditional_result = ConsumerResult(False, False, 'disabled')

    self.car_events = CarEvents(self.CP)
    from openpilot.starpilot.car.tesla.stock_events import StockCruiseConsumer
    self.tesla_stock_consumer = StockCruiseConsumer(self.CP)

    self.pose_calibrator = PoseCalibrator()
    self.calibrated_pose: Pose | None = None
    self.excessive_actuation_check = ExcessiveActuationCheck()
    self.excessive_actuation = self.params.get("Offroad_ExcessiveActuation") is not None
    self.big_model_loading = False
    self.big_model_active = False
    self.big_model_failed = False
    self.big_model_ready_t = 0.

    # Setup sockets
    self.pm = messaging.PubMaster(['selfdriveState', 'onroadEvents'] +
                                  (['aolAxisState'] if self.axis_transport_required else []) +
                                  (['starpilotSelfdriveState'] if self.conditional_replay else []))

    self.gps_location_service = get_gps_location_service(self.params)
    self.gps_packets = [self.gps_location_service]
    self.sensor_packets = ["accelerometer", "gyroscope"]
    self.camera_packets = ["narrowRoadCameraState", "cabinCameraState", "wideRoadCameraState"]

    # TODO: de-couple selfdrived with card/conflate on carState without introducing controls mismatches
    self.car_state_sock = messaging.sub_sock('carState', timeout=20)

    ignore = self.sensor_packets + self.gps_packets + ['alertDebug', 'lateralManeuverPlan', 'laneChangeAssistWire']
    if self.aol_replay:
      ignore += ['aolIntentWire']
    if self.axis_transport_required:
      ignore += ['aolSafetyWire']
    if self.conditional_replay or self.switchback_capable:
      # This optional proposal never controls the native process-health gate.
      ignore += ['slcState']
    if SIMULATION:
      ignore += ['cabinCameraState', 'managerState']
    if REPLAY:
      # no vipc in replay will make them ignored anyways
      ignore += ['narrowRoadCameraState', 'wideRoadCameraState']
    self.sm = messaging.SubMaster(['deviceState', 'pandaStates', 'peripheralState', 'modelV2', 'extrinsicsCalibration',
                                   'carOutput', 'driverMonitoringState', 'longitudinalPlan', 'deviceMotion', 'lateralDelay',
                                   'managerState', 'vehicleParameters', 'radarState', 'lateralTorqueParameters',
                                   'controlsState', 'carControl', 'driverAssistance', 'alertDebug', 'userBookmark',
                                   'lateralManeuverPlan', 'laneChangeAssistWire'] + (['aolIntentWire'] if self.aol_replay else []) +
                                   (['aolSafetyWire'] if self.axis_transport_required else []) +
                                   (['slcState'] if self.conditional_replay or self.switchback_capable else []) + \
                                   self.camera_packets + self.sensor_packets + self.gps_packets,
                                  ignore_alive=ignore, ignore_avg_freq=ignore,
                                  ignore_valid=ignore, frequency=int(1/DT_CTRL))

    # read params
    self.is_metric = self.params.get_bool("IsMetric")
    self.aol_settings = read_settings(self.params) if self.aol_replay else None
    self.is_ldw_enabled = self.params.get_bool("IsLdwEnabled")
    self.disengage_on_accelerator = self.params.get_bool("DisengageOnAccelerator")

    car_recognized = self.CP.brand != 'mock'

    # Capability changes affect runtime authority, never the saved Alpha Long choice.
    if not self.CP.openpilotLongitudinalControl:
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
    self.not_running_prev = None
    self.experimental_mode = False
    self.requested_experimental_mode = False
    self.personality = self.params.get("LongitudinalPersonality", return_default=True)
    self.recalibrating_seen = False
    self.dm_lockout_set = False
    self.dm_uncertain_alerted = False
    self.state_machine = StateMachine()
    self.rk = Ratekeeper(100, print_delay_threshold=None)

    # Determine startup event
    self.startup_event = EventName.startup if build_metadata.openpilot.comma_remote and build_metadata.tested_channel else EventName.startupMaster
    if HARDWARE.get_device_type() == 'mici':
      self.startup_event = None
    if not car_recognized:
      self.startup_event = EventName.startupNoCar
    elif car_recognized and self.CP.passive:
      self.startup_event = EventName.startupNoControl
    elif self.CP.secOcRequired and not self.CP.secOcKeyAvailable:
      self.startup_event = EventName.startupNoSecOcKey

    if not car_recognized:
      self.events.add(EventName.carUnrecognized, static=True)
      set_offroad_alert("Offroad_CarUnrecognized", True)
    elif self.CP.passive:
      self.events.add(EventName.dashcamMode, static=True)

  def update_events(self, CS):
    """Compute onroadEvents from carState"""

    self.events.clear()
    self.nostalgia_paddle_cancel = False
    action_owner = getattr(self, 'controller_action_owner', None)
    action_sock = getattr(self, 'controller_action_sock', None)
    if action_owner is not None and action_sock is not None:
      for _ in range(8):
        request = messaging.recv_one_or_none(action_sock)
        if request is None:
          break
        if (str(request.slcAction.kind) == 'disengageRequest' and self.enabled and
            action_owner.update(request, self.sm, self.CP, now_ns=time.monotonic_ns())):
          self.events.add(EventName.buttonCancel)

    if self.sm['controlsState'].lateralControlState.which() == 'debugState':
      self.events.add(EventName.joystickDebug)
      self.startup_event = None

    loading = self.params.get_bool("ChestnutLoading")
    if self.big_model_loading and not loading:
      self.big_model_ready_t = time.monotonic()
    self.big_model_loading = loading
    if self.big_model_loading:
      self.events.add(EventName.bigModelLoading)

    big_active = self.params.get("ChestnutActive")
    chestnut_present = self.sm['deviceState'].chestnutPresent
    model_unavailable = big_active is True and self.sm.seen['modelV2'] and not self.sm.alive['modelV2']
    big_failed = big_active is False or model_unavailable or (self.big_model_active and not chestnut_present)
    if big_failed and not self.big_model_failed:
      self.events.add(EventName.bigModelFailed)
    self.big_model_failed = big_failed

    # soft disable if the big model fails
    if big_active:
      self.big_model_active = True
    if not self.enabled and not model_unavailable:
      self.big_model_active = False

    if self.sm.recv_frame['lateralManeuverPlan'] > 0:
      self.events.add(EventName.lateralManeuver)
      self.startup_event = None
    elif self.sm.recv_frame['alertDebug'] > 0:
      self.events.add(EventName.longitudinalManeuver)
      self.startup_event = None

    # Add startup event
    if self.startup_event is not None:
      self.events.add(self.startup_event)
      self.startup_event = None

    # Don't add any more events if not initialized
    if not self.initialized:
      self.events.add(EventName.selfdriveInitializing)
      return

    # Check for user bookmark press
    if self.sm.updated['userBookmark']:
      prime_type = self.params.get("PrimeType")
      paired = prime_type is not None and int(prime_type) >= 0
      self.events.add(EventName.userBookmark if paired else EventName.userBookmarkNotPaired)

    # Don't add any more events while in dashcam mode
    if self.CP.passive:
      return

    # Block resume if cruise never previously enabled
    resume_pressed = any(be.type in (ButtonType.accelCruise, ButtonType.resumeCruise) for be in CS.buttonEvents)
    if not self.CP.pcmCruise and CS.vCruise > 250 and resume_pressed:
      self.events.add(EventName.resumeBlocked)

    # Handle DM
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
      self.events.add_from_msg(car_events)
      if self.tesla_stock_consumer.binding is not None:
        now_ns = self.aol_car_state_log_ns if REPLAY and self.aol_car_state_log_ns else time.monotonic_ns()
        companion = current_intent(self.sm, car_state_ns=int(self.sm.logMonoTime['carState']), now_ns=now_ns,
                                   previous=self.aol_last_intent)
        session = companion.producerSessionId if companion is not None else None
        self.tesla_stock_consumer.poll(self.events, self.sm, now_ns=now_ns, session=session)

      paddle_pressed = paddle_cancel(self.CP, CS, enabled=self.enabled, saved=self.nostalgia_enabled)
      self.nostalgia_paddle_cancel = bool(paddle_pressed and EventName.buttonCancel not in self.events.names and
                                         not physical_cancel(CS))
      if paddle_pressed:
        self.events.add(EventName.buttonCancel)

      if self.CP.notCar:
        # wait for everything to init first
        if self.sm.frame > int(2. / DT_CTRL) and self.initialized:
          # body always wants to enable
          self.events.add(EventName.pcmEnable)

      # Disable on rising edge of accelerator or brake. Also disable on brake when speed > 0
      if (CS.gasPressed and not self.CS_prev.gasPressed and self.disengage_on_accelerator) or \
        (CS.brakePressed and (not self.CS_prev.brakePressed or not CS.standstill)) or \
        (CS.regenBraking and (not self.CS_prev.regenBraking or not CS.standstill)):
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
    cal_status = self.sm['extrinsicsCalibration'].calStatus
    if cal_status != log.ExtrinsicsCalibration.Status.calibrated:
      if cal_status == log.ExtrinsicsCalibration.Status.uncalibrated:
        self.events.add(EventName.calibrationIncomplete)
      elif cal_status == log.ExtrinsicsCalibration.Status.recalibrating:
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
    if self.sm.updated['extrinsicsCalibration']:
      self.pose_calibrator.feed_extrinsics_calibration(self.sm['extrinsicsCalibration'])
    if self.sm.updated['deviceMotion']:
      device_motion = Pose.from_device_motion(self.sm['deviceMotion'])
      self.calibrated_pose = self.pose_calibrator.build_calibrated_pose(device_motion)

    if self.calibrated_pose is not None and not self.CP.notCar:
      excessive_actuation = self.excessive_actuation_check.update(self.sm, CS, self.calibrated_pose)
      if not self.excessive_actuation and excessive_actuation is not None:
        set_offroad_alert("Offroad_ExcessiveActuation", True, extra_text=str(excessive_actuation))
        self.excessive_actuation = True

    if self.excessive_actuation:
      self.events.add(EventName.excessiveActuation)
    # ******************************************************************************************

    # Handle lane change
    if self.sm['modelV2'].meta.laneChangeState == LaneChangeState.preLaneChange:
      direction = self.sm['modelV2'].meta.laneChangeDirection
      if (CS.leftBlindspot and direction == LaneChangeDirection.left) or \
         (CS.rightBlindspot and direction == LaneChangeDirection.right):
        self.events.add(EventName.laneChangeBlocked)
      else:
        if direction == LaneChangeDirection.left:
          self.events.add(EventName.preLaneChangeLeft)
        else:
          self.events.add(EventName.preLaneChangeRight)
    elif self.sm['modelV2'].meta.laneChangeState in (LaneChangeState.laneChangeStarting,
                                                    LaneChangeState.laneChangeFinishing):
      self.events.add(EventName.laneChange)

    for i, pandaState in enumerate(self.sm['pandaStates']):
      # All pandas must match the list of safetyConfigs, and if outside this list, must be silent or noOutput
      if i < len(self.CP.safetyConfigs):
        safety_mismatch = pandaState.safetyModel != self.CP.safetyConfigs[i].safetyModel or \
                          pandaState.safetyParam != self.CP.safetyConfigs[i].safetyParam or \
                          pandaState.alternativeExperience != self.CP.alternativeExperience
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
    if self.CP.openpilotLongitudinalControl:
      if self.sm['radarState'].radarErrors.canError:
        self.events.add(EventName.canError)
      elif self.sm['radarState'].radarErrors.radarUnavailableTemporary:
        self.events.add(EventName.radarTempUnavailable)
      elif any(self.sm['radarState'].radarErrors.to_dict().values()):
        self.events.add(EventName.radarFault)
    if CS.canTimeout:
      self.events.add(EventName.canBusMissing)
    elif not CS.canValid:
      self.events.add(EventName.canError)

    # generic catch-all. ideally, a more specific event should be added above instead
    has_disable_events = self.events.contains(ET.NO_ENTRY) and (self.events.contains(ET.SOFT_DISABLE) or self.events.contains(ET.IMMEDIATE_DISABLE))
    no_system_errors = (not has_disable_events) or (len(self.events) == num_events)
    warmup_sec = 5.
    big_model_settling = self.big_model_loading or time.monotonic() < self.big_model_ready_t + warmup_sec
    if not self.sm.all_checks() and no_system_errors and not big_model_settling:  # the load holds modelV2 and friends back on purpose
      if not self.sm.all_alive():
        self.events.add(EventName.commIssue)
      elif not self.sm.all_freq_ok():
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

    if not self.CP.notCar and not big_model_settling:  # localization has nothing to work with during the load
      # the defaults of a message that was never received are not a localizer failure
      if self.sm.seen['deviceMotion'] and not self.sm['deviceMotion'].posenetOK:
        self.events.add(EventName.posenetInvalid)
      if self.sm.seen['deviceMotion'] and not self.sm['deviceMotion'].inputsOK:
        self.events.add(EventName.locationdTemporaryError)
      if (self.sm.seen['vehicleParameters'] and not self.sm['vehicleParameters'].valid and cal_status == log.ExtrinsicsCalibration.Status.calibrated and
          not TESTING_CLOSET and (not SIMULATION or REPLAY)):
        self.events.add(EventName.paramsdTemporaryError)

    # conservative HW alert. if the data or frequency are off, locationd will throw an error
    if any((self.sm.frame - self.sm.recv_frame[s])*DT_CTRL > 10. for s in self.sensor_packets):
      self.events.add(EventName.sensorDataInvalid)

    if not REPLAY:
      # Check for mismatch between openpilot and car's PCM
      cruise_mismatch = CS.cruiseState.enabled and (not self.enabled or not self.CP.pcmCruise)
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
      # TODO: lac.saturated includes speed and other checks, should be pulled out
      if undershooting and turning and lac.saturated:
        self.events.add(EventName.steerSaturated)

    # Check for FCW
    stock_long_is_braking = self.enabled and not self.CP.openpilotLongitudinalControl and CS.aEgo < -1.25
    model_fcw = self.sm['modelV2'].meta.hardBrakePredicted and not CS.brakePressed and not stock_long_is_braking
    planner_fcw = self.sm['longitudinalPlan'].fcw and self.enabled
    if (planner_fcw or model_fcw) and not self.CP.notCar:
      self.events.add(EventName.fcw)

    # GPS checks
    gps_ok = self.sm.recv_frame[self.gps_location_service] > 0 and (self.sm.frame - self.sm.recv_frame[self.gps_location_service]) * DT_CTRL < 2.0
    if not gps_ok and self.sm['deviceMotion'].inputsOK and (self.distance_traveled > 1500):
      self.events.add(EventName.noGps)
    if gps_ok:
      self.distance_traveled = 0
    self.distance_traveled += abs(CS.vEgo) * DT_CTRL

    # TODO: fix simulator
    if not SIMULATION or REPLAY:
      if self.sm['modelV2'].frameDropPerc > 1:
        self.events.add(EventName.modeldLagging)

    # Decrement personality on distance button press
    if self.CP.openpilotLongitudinalControl:
      if any(not be.pressed and be.type == ButtonType.gapAdjustCruise for be in CS.buttonEvents):
        self.personality = (self.personality - 1) % 3
        self.params.put('LongitudinalPersonality', self.personality)
        self.events.add(EventName.personalityChanged)

  def data_sample(self):
    _car_state = messaging.recv_one(self.car_state_sock)
    CS = _car_state.carState if _car_state else self.CS_prev
    if _car_state is not None:
      self.aol_car_state_log_ns = int(_car_state.logMonoTime)
      self.conditional_car_state_valid = bool(_car_state.valid)
    else:
      # The 20 ms socket wait can expire between healthy CAN frames. Reusing
      # CS_prev must also keep its original timestamp, never create a new one.
      age_ns = time.monotonic_ns() - self.aol_car_state_log_ns
      retained = (self.conditional_car_state_valid and self.aol_car_state_log_ns > 0 and
                  0 <= age_ns <= INTENT_MAX_AGE_NS and CS.canValid and not CS.canTimeout)
      if not retained:
        self.aol_car_state_log_ns = 0
        self.conditional_car_state_valid = False

    self.sm.update(0)

    if not self.initialized:
      all_valid = CS.canValid and self.sm.all_checks()
      timed_out = self.sm.frame * DT_CTRL > 6.
      if all_valid or timed_out or (SIMULATION and not REPLAY):
        available_streams = VisionIpcClient.available_streams("camerad", block=False)
        if VisionStreamType.VISION_STREAM_NARROW_ROAD not in available_streams:
          self.sm.ignore_alive.append('narrowRoadCameraState')
          self.sm.ignore_valid.append('narrowRoadCameraState')
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
                                                                                self.state_machine.soft_disable_timer, pers])
    now_ns = time.monotonic_ns()
    drive = int(self.sm['deviceState'].startedMonoTime) if self.sm['deviceState'].started else 0
    switchback = bool(self.switchback_capable and self.sm.seen['slcState'] and self.sm.alive['slcState'] and
                      self.sm.valid['slcState'] and self.sm['carControl'].latActive and
                      self.switchback_status.sample(self.sm['slcState'], drive_id=drive, now_ns=now_ns,
                        event_ns=int(self.sm.logMonoTime['slcState'])))
    if now_ns - self.switchback_setting_ns >= 1_000_000_000:
      self.switchback_setting_ns = now_ns
      try:
        cooldown = float(self.params.get('SwitchbackModeCooldown') or 5)
        self.switchback_cooldown_ns = int(cooldown * 60e9) if math.isfinite(cooldown) and 0 <= cooldown <= 30 else 0
      except (TypeError, ValueError, OverflowError):
        self.switchback_cooldown_ns = 0
    # Reset the advisory clock even on frames without either advisory.
    self.switchback_cooldown.allow('', active=switchback, drive_id=drive, now_ns=now_ns,
                                  cooldown_ns=self.switchback_cooldown_ns)
    alerts = [alert for alert in alerts if alert.alert_type not in ('belowSteerSpeed/warning', 'steerSaturated/warning') or
              self.switchback_cooldown.allow(alert.alert_type.split('/')[0], active=switchback,
                drive_id=drive, now_ns=now_ns, cooldown_ns=self.switchback_cooldown_ns)]
    for index, alert in enumerate(alerts):
      if alert.alert_type not in ("preLaneChangeLeft/warning", "preLaneChangeRight/warning"):
        continue
      source_ok = (self.sm.seen['laneChangeAssistWire'] and self.sm.alive['laneChangeAssistWire'] and
                   self.sm.valid['laneChangeAssistWire'] and self.sm.valid['modelV2'])
      status = decode_lane_status(self.sm['laneChangeAssistWire']) if source_ok else None
      now_mono_ns = time.monotonic_ns()
      recv_ns = int(self.sm.recv_time['laneChangeAssistWire'] * 1e9)
      message_ns = int(self.sm.logMonoTime['laneChangeAssistWire'])
      valid_status = fresh_for_model(status, self.sm['modelV2'], now_mono_ns, recv_ns,
                                    self.lane_status_sequence, self.lane_status_session, message_ns)
      if valid_status:
        assert status is not None
        self.lane_status_session, self.lane_status_sequence = status.producer_session_id, status.sequence
      wording = alert_wording(status if valid_status else None, self.sm['modelV2'], now_mono_ns, recv_ns)
      if wording is None:
        continue
      replacement = copy(alert)
      replacement.alert_text_1, replacement.alert_text_2 = wording
      alerts[index] = replacement
    if not hasattr(self, 'force_stop_hold_alert'):
      self.force_stop_hold_alert = HoldAlertState()
    holding = self.force_stop_hold_alert.active(
      self.sm, self.CP, CS, enabled=self.enabled, car_ns=getattr(self, 'aol_car_state_log_ns', 0),
      car_valid=getattr(self, 'conditional_car_state_valid', False), now_ns=time.monotonic_ns()) and ET.WARNING in self.state_machine.current_alert_types
    if holding:
      alert = Alert("Force Stop Holding", "Press RES or accelerator to proceed", log.SelfdriveState.AlertStatus.normal,
                    log.SelfdriveState.AlertSize.mid, AlertPriority.LOW, car.CarControl.HUDControl.VisualAlert.none,
                    log.SelfdriveState.AudibleAlert.none, 0.)
      alert.alert_type, alert.event_type = "forceStopHold/warning", FORCE_STOP_HOLD
      alerts.append(alert)
    else:
      clear_event_types.add(FORCE_STOP_HOLD)
    self.AM.add_many(self.sm.frame, alerts)
    self.AM.process_alerts(self.sm.frame, clear_event_types)

  def publish_selfdriveState(self, CS):
    # selfdriveState
    ss_msg = messaging.new_message('selfdriveState')
    ss_msg.valid = True
    ss = ss_msg.selfdriveState
    ss.enabled = self.enabled
    ss.active = self.active
    ss.state = self.state_machine.state
    ss.engageable = not self.events.contains(ET.NO_ENTRY)
    ss.experimentalMode = self.experimental_mode
    ss.personality = self.personality

    ss.alertText1 = self.AM.current_alert.alert_text_1
    ss.alertText2 = self.AM.current_alert.alert_text_2
    ss.alertSize = self.AM.current_alert.alert_size
    ss.alertStatus = self.AM.current_alert.alert_status
    ss.alertType = self.AM.current_alert.alert_type
    ss.alertSound = self.AM.current_alert.audible_alert
    ss.alertHudVisual = self.AM.current_alert.visual_alert

    if self.aol_replay or getattr(self, 'ordinary_axis_ack_required', False):
      now_ns = self.aol_car_state_log_ns if REPLAY and self.aol_car_state_log_ns else time.monotonic_ns()
      self.aol_sequence += 1
      axis_msg = messaging.new_message('aolAxisState')
      axis_msg.logMonoTime = now_ns
      axis_msg.valid = self.aol_car_state_log_ns > 0
      axis = axis_msg.aolAxisState
      axis.sessionId = self.aol_session_id
      axis.sequence = self.aol_sequence
      axis.sourceCarStateMonoTime = self.aol_car_state_log_ns
      axis.observedMonoTime = now_ns
      axis.validUntilMonoTime = now_ns + 30_000_000
      axis.mode = self.aol_axis_decision.mode
      axis.lateralActive = self.aol_axis_decision.lateral_active
      axis.longitudinalActive = self.aol_axis_decision.longitudinal_active
      axis.desiredLateral = self.aol_axis_decision.desired_lateral
      axis.desiredLongitudinal = self.aol_axis_decision.desired_longitudinal
      axis.nativeAcknowledged = self.aol_axis_decision.native_acknowledged
      axis.qualified = self.aol_replay or getattr(self, 'ordinary_axis_ack_required', False)
      self.pm.send('aolAxisState', axis_msg)
    self.pm.send('selfdriveState', ss_msg)
    if self.conditional_replay:
      self.conditional_ack_sequence += 1
      result = self.conditional_result
      proposal = self.conditional_consumer.last if result.accepted and self.conditional_consumer is not None else None
      ack = publish_ack(session=self.conditional_ack_session, sequence=self.conditional_ack_sequence,
                        observed_ns=time.monotonic_ns(), selfdrive_state_ns=int(ss_msg.logMonoTime),
                        drive_id=int(self.sm['deviceState'].startedMonoTime), effective_experimental=bool(ss.experimentalMode),
                        result=result, accepted_proposal=proposal)
      historic = ack.starpilotSelfdriveState
      historic.alertText1 = ss.alertText1
      historic.alertText2 = ss.alertText2
      historic.alertStatus = str(ss.alertStatus)
      historic.alertSize = str(ss.alertSize)
      historic.alertType = ss.alertType
      sound = str(ss.alertSound)
      historic.alertSound = sound if sound in ('none', 'engage', 'disengage', 'refuse', 'warningSoft',
                                                'warningImmediate', 'prompt', 'promptRepeat', 'promptDistracted') else 'none'
      historic.vEgo = CS.vEgo
      self.pm.send('starpilotSelfdriveState', ack)

    # onroadEvents - logged every second or on change
    if (self.sm.frame % int(1. / DT_CTRL) == 0) or (self.events.names != self.events_prev):
      ce_send = messaging.new_message('onroadEvents', len(self.events))
      ce_send.valid = True
      ce_send.onroadEvents = self.events.to_msg()
      self.pm.send('onroadEvents', ce_send)
    self.events_prev = self.events.names.copy()

  def update_conditional_mode(self, CS):
    # The Params thread owns the stock request; only this thread publishes the
    # effective choice. Conditional proposals cannot race a Params assignment.
    self.experimental_mode = self.requested_experimental_mode
    self.conditional_result = ConsumerResult(self.experimental_mode, False, 'unavailable')
    if not self.conditional_replay:
      return
    assert self.conditional_settings is not None and self.conditional_consumer is not None
    clocks = paired_clocks_ns() if not REPLAY else None
    if clocks is None:
      self.conditional_consumer.invalidate(time.monotonic_ns())
      self.conditional_status = 'clock_unavailable'
      return
    now_ns, boot_ns, skew_ns = clocks
    snapshot = self.conditional_settings.current
    drive_id = int(self.sm['deviceState'].startedMonoTime)
    verdict = self.conditional_settings.verdict(snapshot, now_mono_ns=now_ns, drive_id=drive_id)
    configured = (verdict.status == 'ready' and verdict.selection is not None and
                  snapshot is not None and verdict.revision == snapshot.revision)
    required = ('deviceState', 'modelV2', 'carControl')
    fresh = all(self.sm.seen[service] and self.sm.valid[service] and self.sm.alive[service] and
                0 < self.sm.logMonoTime[service] <= now_ns and
                now_ns - self.sm.logMonoTime[service] <= (2_000_000_000 if service == 'deviceState' else 150_000_000)
                for service in required)
    axis_active = self.aol_axis_decision.longitudinal_active if self.aol_replay else self.enabled
    authority = bool(configured and fresh and self.initialized and axis_active and
                     self.CP.openpilotLongitudinalControl and not self.CP.passive and
                     self.conditional_car_state_valid and CS.canValid and not CS.canTimeout and self.sm['deviceState'].started and
                     self.sm['carControl'].longActive and self.sm.seen['slcState'] and self.sm.alive['slcState'])
    result = self.conditional_consumer.sample(
      self.sm['slcState'], now_ns=now_ns, now_boot_ns=boot_ns, sample_skew_ns=skew_ns,
      message_ns=int(self.sm.logMonoTime['slcState']), receipt_ns=int(self.sm.recv_time['slcState'] * 1e9),
      drive_id=drive_id, model_ns=int(self.sm.logMonoTime['modelV2']), car_state_ns=self.aol_car_state_log_ns,
      authority=authority, stock_experimental=self.requested_experimental_mode,
      choice=verdict.selection.choice if configured else ModeChoice.STOCK,
      settings_fingerprint=settings_fingerprint(snapshot) if configured else None)
    self.experimental_mode = result.experimental
    self.conditional_status = result.status
    self.conditional_result = result

  def step(self):
    CS = self.data_sample()
    self.update_events(CS)
    native = None
    lost_active_aol = False
    if self.aol_replay or getattr(self, 'ordinary_axis_ack_required', False):
      now_ns = self.aol_car_state_log_ns if REPLAY and self.aol_car_state_log_ns else time.monotonic_ns()
      native = current_native(self.sm, self.CP, now_ns=now_ns, axis_session_id=self.aol_session_id)
      if native is None:
        lost_active_aol = self.aol_axis_decision.lateral_active or self.aol_axis_decision.longitudinal_active
        self.events.add(EventName.controlsMismatch)
    if not self.CP.passive and self.initialized:
      self.enabled, self.active = self.state_machine.update(self.events)
    if lost_active_aol and ET.IMMEDIATE_DISABLE not in self.state_machine.current_alert_types:
      self.state_machine.current_alert_types.append(ET.IMMEDIATE_DISABLE)
    if self.aol_replay:
      intent = current_intent(self.sm, car_state_ns=self.aol_car_state_log_ns, now_ns=now_ns,
                              previous=getattr(self, 'aol_last_intent', None))
      self.aol_last_intent = intent
      if self.sm['driverMonitoringState'].alertLevel == AlertLevel.three or self.sm['driverMonitoringState'].lockout:
        self.aol_dm_lateral_inhibit = True
      elif intent is not None and not intent.allowedLatch:
        self.aol_dm_lateral_inhibit = False
      self.aol_axis_decision = decide_axes(
        standard_lateral=self.active, standard_longitudinal=self.enabled and self.CP.openpilotLongitudinalControl,
        intent=intent, native=native, car_state=CS, initialized=self.initialized,
        model_ready=bool(self.sm.all_checks(['modelV2', 'extrinsicsCalibration']) and
                         self.sm['extrinsicsCalibration'].calStatus == log.ExtrinsicsCalibration.Status.calibrated),
        no_entry=aol_no_entry(self.events.names, CS, paddle_only_cancel=self.nostalgia_paddle_cancel),
        immediate_disable=self.events.contains(ET.IMMEDIATE_DISABLE),
        dm_lockout=bool(not self.sm.all_checks(['driverMonitoringState']) or
                        self.sm['driverMonitoringState'].lockout or self.sm['driverMonitoringState'].alwaysOnLockout or
                        self.sm['driverMonitoringState'].alertLevel == AlertLevel.three),
        pause_brake_mps=self.aol_settings.pause_brake_mps if self.aol_settings is not None else 0.0,
        lateral_inhibit=self.aol_dm_lateral_inhibit)
    if getattr(self, 'ordinary_axis_ack_required', False):
      self.aol_axis_decision = decide_ordinary_axis(
        requested=bool(self.initialized and self.conditional_car_state_valid and
                       CS.canValid and not CS.canTimeout and
                       ordinary_lateral_requested(self.active, CS, self.CP) and
                       ordinary_axis_request_allowed(self.CP, CS)), native=native)
    if (self.aol_replay and intent is not None and intent.lateralArmed and
        CS.steerFaultTemporary and not CS.steerFaultPermanent):
      # An armed AOL session still needs the ordinary temporary-steering warning
      # while actual steering is suspended and the stock state machine is off.
      if EventName.steerTempUnavailableSilent not in self.events.names:
        self.events.add(EventName.steerTempUnavailableSilent)
      if ET.WARNING not in self.state_machine.current_alert_types:
        self.state_machine.current_alert_types.append(ET.WARNING)
    self.update_alerts(CS)
    self.update_conditional_mode(CS)

    self.publish_selfdriveState(CS)

    self.CS_prev = CS

  def params_thread(self, evt):
    while not evt.is_set():
      self.is_metric = self.params.get_bool("IsMetric")
      if self.aol_replay:
        self.aol_settings = read_settings(self.params)
      self.is_ldw_enabled = self.params.get_bool("IsLdwEnabled")
      self.disengage_on_accelerator = self.params.get_bool("DisengageOnAccelerator")
      self.nostalgia_enabled = nostalgia_saved_enabled(self.params)
      self.requested_experimental_mode = self.params.get_bool("ExperimentalMode") and self.CP.openpilotLongitudinalControl
      if self.conditional_settings is not None:
        self.conditional_settings.refresh(time.monotonic_ns())
      self.personality = self.params.get("LongitudinalPersonality", return_default=True)
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
  config_realtime_process(5, Priority.CTRL_HIGH)
  s = SelfdriveD()
  s.run()

if __name__ == "__main__":
  main()
