#!/usr/bin/env python3
import math
import os
import time
import threading

import cereal.messaging as messaging

from cereal import car, custom, log

from openpilot.common.params import Params
from openpilot.common.realtime import config_realtime_process, Priority, Ratekeeper
from openpilot.common.swaglog import cloudlog, ForwardingHandler
from openpilot.system.hardware.hw import Paths

from opendbc.car import DT_CTRL, ButtonType, structs
from opendbc.car.can_definitions import CanData, CanRecvCallable, CanSendCallable
from opendbc.car.carlog import carlog
from opendbc.car.fw_versions import ObdCallback
from opendbc.car.car_helpers import get_car, interfaces
from opendbc.car.hyundai.ev9_longitudinal import EV9_SOFTWARE_BSM_COMMA_OUTPUT_PARAM, EV9_SOFTWARE_BSM_PARAM, \
                                                   EV9_SOFTWARE_BSM_VEHICLE_OUTPUT_PARAM, EV9LongitudinalTestStage, \
                                                   ev9_cluster_display_speed_limit_raw, \
                                                   get_ev9_longitudinal_test_config
from opendbc.car.hyundai.interface import attempt_ev9_pre_fingerprint_suppression
from opendbc.car.interfaces import CarInterfaceBase, RadarInterfaceBase
from opendbc.safety import ALTERNATIVE_EXPERIENCE
from openpilot.selfdrive.pandad import can_capnp_to_list, can_list_to_can_capnp
from openpilot.common.constants import CV
from openpilot.selfdrive.car.cruise import VCruiseHelper, IMPERIAL_INCREMENT, V_CRUISE_MAX, V_CRUISE_MIN
from openpilot.selfdrive.car.redneck_cruise import RedneckCruise, select_redneck_target_speed
from openpilot.selfdrive.car.car_specific import MockCarState
from openpilot.selfdrive.car.ev9_cluster_objects import ClusterObjectSlots, Ev9ClusterObjectTracker, bsm_gated_side_slots, default_enabled_param, \
                                                         ev9_cluster_display_context_valid, filtered_radar_slots
from openpilot.selfdrive.car.ev9_software_bsm import RAW_BASE_MASK, RAW_LEFT_MASK, RAW_RIGHT_MASK, Ev9SoftwareBsmDetector, \
                                                       select_ev9_software_bsm_outputs

from openpilot.starpilot.common.starpilot_variables import get_starpilot_toggles, update_starpilot_toggles
from openpilot.starpilot.controls.starpilot_card import StarPilotCard

REPLAY = "REPLAY" in os.environ
OPENPILOT_LEAD_MIN_DISTANCE = 0.1
REDNECK_DECREASE_LOOKAHEAD_POINTS = 10
EV9_SOFTWARE_BSM_RADAR_STALE_S = 0.15

EventName = log.OnroadEvent.EventName

# forward
carlog.addHandler(ForwardingHandler(cloudlog))


def obd_callback(params: Params) -> ObdCallback:
  def set_obd_multiplexing(obd_multiplexing: bool):
    if params.get_bool("ObdMultiplexingEnabled") != obd_multiplexing:
      cloudlog.warning(f"Setting OBD multiplexing to {obd_multiplexing}")
      params.remove("ObdMultiplexingChanged")
      params.put_bool("ObdMultiplexingEnabled", obd_multiplexing)
      params.get_bool("ObdMultiplexingChanged", block=True)
      cloudlog.warning("OBD multiplexing set successfully")
  return set_obd_multiplexing


def can_comm_callbacks(logcan: messaging.SubSocket, sendcan: messaging.PubSocket) -> tuple[CanRecvCallable, CanSendCallable]:
  def can_recv(wait_for_one: bool = False) -> list[list[CanData]]:
    """
    wait_for_one: wait the normal logcan socket timeout for a CAN packet, may return empty list if nothing comes

    Returns: CAN packets comprised of CanData objects for easy access
    """
    ret = []
    for can in messaging.drain_sock(logcan, wait_for_one=wait_for_one):
      ret.append([CanData(msg.address, msg.dat, msg.src) for msg in can.can])
    return ret

  def can_send(msgs: list[CanData]) -> None:
    sendcan.send(can_list_to_can_capnp(msgs, msgtype='sendcan'))

  return can_recv, can_send


class Car:
  CI: CarInterfaceBase
  RI: RadarInterfaceBase
  CP: car.CarParams

  FPCP: custom.StarPilotCarParams

  def __init__(self, CI=None, RI=None) -> None:
    self.can_sock = messaging.sub_sock('can', timeout=20)
    self.sm = messaging.SubMaster(['pandaStates', 'carControl', 'onroadEvents', 'radarState', 'starpilotRadarState',
                                   'longitudinalPlan'])
    self.pm = messaging.PubMaster(['sendcan', 'carState', 'carParams', 'carOutput', 'liveTracks'])

    self.can_rcv_cum_timeout_counter = 0

    self.CC_prev = car.CarControl.new_message()
    self.CS_prev = car.CarState.new_message()
    self.initialized_prev = False
    self.interface_initialized = False
    self.ev9_early_control_active = False
    # CarController expects a reader (normal carControl messages come from a
    # SubMaster). Passing a builder makes its nested actuators lack as_builder.
    self.ev9_early_car_control = car.CarControl.new_message().as_reader()

    self.last_actuators_output = structs.CarControl.Actuators()

    self.params = Params()
    self.params_memory = Params(memory=True)
    self.ev9_cluster_objects_enabled = self.params.get_bool("KiaEv9ClusterObjectsEnabled")
    self.ev9_cluster_alternate_enabled = self.params.get_bool("KiaEv9ClusterAlternateLeadEnabled")
    self.ev9_cluster_smoothing_enabled = self.params.get_bool("KiaEv9ClusterObjectSmoothingEnabled")
    self.ev9_cluster_map_speed_limit_fallback_enabled = self.params.get_bool("KiaEv9ClusterMapSpeedLimitFallbackEnabled")
    self.ev9_radar_quality_filter_enabled = default_enabled_param(self.params, "KiaEv9RadarQualityFilterEnabled")
    self.ev9_cluster_fused_primary_required = default_enabled_param(self.params, "KiaEv9ClusterFusedPrimaryRequired")
    self.ev9_cluster_side_objects_require_bsm = self.params.get_bool("KiaEv9ClusterSideObjectsRequireBsmEnabled")
    self.ev9_cluster_strict_side_filter_enabled = default_enabled_param(
      self.params, "KiaEv9ClusterStrictSideObjectFilterEnabled",
    )
    self.ev9_cluster_right_objects_enabled = self.params.get_bool("KiaEv9ClusterRightObjectsEnabled")
    self.ev9_cluster_tracker = Ev9ClusterObjectTracker()
    self.ev9_cluster_slots = ClusterObjectSlots()
    self.ev9_software_bsm_enabled = self.params.get_bool(EV9_SOFTWARE_BSM_PARAM)
    self.ev9_software_bsm_comma_output_enabled = self.params.get_bool(EV9_SOFTWARE_BSM_COMMA_OUTPUT_PARAM)
    self.ev9_software_bsm_vehicle_output_enabled = self.params.get_bool(EV9_SOFTWARE_BSM_VEHICLE_OUTPUT_PARAM)
    self.ev9_software_bsm_detector = Ev9SoftwareBsmDetector()
    self.ev9_software_bsm_last_state = (False, False, False, False)
    self.ev9_software_bsm_last_log_time = 0.0
    self.ev9_software_bsm_last_radar_time = 0.0

    self.can_callbacks = can_comm_callbacks(self.can_sock, self.pm.sock['sendcan'])

    is_release = False

    if CI is None:
      # wait for one pandaState and one CAN packet
      print("Waiting for CAN messages...")
      while True:
        can = messaging.recv_one_retry(self.can_sock)
        if len(can.can) > 0:
          break

      initial_can_messages = [CanData(msg.address, msg.dat, msg.src) for msg in can.can]
      # Preserve any additional frames already queued in the same wake-up
      # burst. This does not wait or widen the UDS timing window.
      for initial_event in messaging.drain_sock(self.can_sock, wait_for_one=False):
        initial_can_messages.extend(CanData(msg.address, msg.dat, msg.src) for msg in initial_event.can)

      alpha_long_allowed = self.params.get_bool("AlphaLongitudinalEnabled")
      num_pandas = len(messaging.recv_one_retry(self.sm.sock['pandaStates']).pandaStates)

      cached_params = None
      # CarParamsCache is intentionally cleared when manager starts. The
      # persistent copy lets the strictly gated EV9 pre-fingerprint request run
      # on the first OFF -> READY transition after a comma reboot as well.
      cached_params_raw = self.params.get("CarParamsCache") or self.params.get("CarParamsPersistent")
      if cached_params_raw is not None:
        with car.CarParams.from_bytes(cached_params_raw) as _cached_params:
          cached_params = _cached_params.as_builder()

      cached_fpcp = None
      cached_fpcp_raw = self.params.get("StarPilotCarParamsPersistent")
      if cached_fpcp_raw is not None:
        with custom.StarPilotCarParams.from_bytes(cached_fpcp_raw) as _cached_fpcp:
          cached_fpcp = _cached_fpcp.as_builder()

      # If the strictly gated pre-fingerprint request succeeds, use the exact
      # persisted interface configuration instead of spending another second
      # collecting a live fingerprint while the ADAS output is already muted.
      # Both parameter blobs were produced by a verified EV9 route and the UDS
      # helper independently checks identity, firmware, and developer gates.
      pre_fingerprint_suppressed = False
      if cached_fpcp is not None:
        pre_fingerprint_suppressed = attempt_ev9_pre_fingerprint_suppression(cached_params, self.params, *self.can_callbacks,
                                                                              initial_can_messages)

      if pre_fingerprint_suppressed:
        cloudlog.warning("EV9 using verified persistent interface after pre-fingerprint suppression")
        self.CI = interfaces[cached_params.carFingerprint](cached_params, cached_fpcp)
      else:
        self.CI = get_car(*self.can_callbacks, obd_callback(self.params), alpha_long_allowed, is_release, self.params, num_pandas, cached_params,
                          get_starpilot_toggles())
      self.RI = interfaces[self.CI.CP.carFingerprint].RadarInterface(self.CI.CP)
      self.CP = self.CI.CP

      # continue onto next fingerprinting step in pandad
      self.params.put_bool("FirmwareQueryDone", True)

      self.FPCP = self.CI.FPCP
    else:
      self.CI, self.CP, self.FPCP = CI, CI.CP, CI.FPCP
      self.RI = RI

    # CP and RI do not exist until fingerprinting/interface construction above.
    # Enabling EV9 live tracks earlier crashes card before controls can start.
    if self.ev9_cluster_objects_enabled and str(self.CP.carFingerprint) == "KIA_EV9":
      enable_ev9_live_radar_tracks = getattr(self.RI, "enable_ev9_live_radar_tracks", None)
      if enable_ev9_live_radar_tracks is not None:
        cloudlog.warning(f"EV9 cluster live radar tracks enabled={enable_ev9_live_radar_tracks()}")

    interface_alternative_experience = self.CP.alternativeExperience
    self.CP.alternativeExperience = interface_alternative_experience
    openpilot_enabled_toggle = self.params.get_bool("OpenpilotEnabledToggle")
    controller_available = self.CI.CC is not None and openpilot_enabled_toggle
    self.CP.passive = not controller_available
    if self.CP.passive:
      safety_config = structs.CarParams.SafetyConfig()
      safety_config.safetyModel = structs.CarParams.SafetyModel.noOutput
      self.CP.safetyConfigs = [safety_config]

    if self.CP.secOcRequired and not is_release:
      # Copy user key if available
      try:
        user_key = Params(Paths.params_cache_root()).get("SecOCKey")
        if user_key is not None:
          user_key = user_key.strip()
          if len(user_key) == 32:
            self.params.put("SecOCKey", user_key)
      except Exception:
        pass

      secoc_key = self.params.get("SecOCKey")
      if secoc_key is not None:
        saved_secoc_key = bytes.fromhex(secoc_key.strip())
        if len(saved_secoc_key) == 16:
          self.CP.secOcKeyAvailable = True
          self.CI.CS.secoc_key = saved_secoc_key
          if controller_available:
            self.CI.CC.secoc_key = saved_secoc_key
        else:
          cloudlog.warning("Saved SecOC key is invalid")

    # Write previous route's CarParams
    prev_cp = self.params.get("CarParamsPersistent")
    if prev_cp is not None:
      self.params.put("CarParamsPrevRoute", prev_cp)

    # Write CarParams for controls and radard
    cp_bytes = self.CP.to_bytes()
    self.params.put("CarParams", cp_bytes)
    self.params.put_nonblocking("CarParamsCache", cp_bytes)
    self.params.put_nonblocking("CarParamsPersistent", cp_bytes)

    self.mock_carstate = MockCarState()
    self.v_cruise_helper = VCruiseHelper(self.CP, self.FPCP)
    self.redneck_cruise = RedneckCruise(self.CP, self.FPCP) if self.CP.brand == "hyundai" and self.FPCP.redneckCruiseAvailable and not self.FPCP.pcmCruiseSpeed else None

    self.is_metric = self.params.get_bool("IsMetric")
    self.safe_mode = self.params.get_bool("SafeMode")
    self.experimental_mode = self.params.get_bool("ExperimentalMode") and not self.safe_mode

    # card is driven by can recv, expected at 100Hz
    self.rk = Ratekeeper(100, print_delay_threshold=None)

    self.resume_prev_button = False

    self.starpilot_toggles = get_starpilot_toggles()

    self.FPCP.alternativeExperience |= interface_alternative_experience

    if self.starpilot_toggles.always_on_lateral:
      self.CP.alternativeExperience |= ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL
      self.FPCP.alternativeExperience |= ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL
    if getattr(self.starpilot_toggles, "remap_cancel_to_distance", False):
      self.CP.alternativeExperience |= ALTERNATIVE_EXPERIENCE.GM_REMAP_CANCEL_TO_DISTANCE
      self.FPCP.alternativeExperience |= ALTERNATIVE_EXPERIENCE.GM_REMAP_CANCEL_TO_DISTANCE

    fpcp_bytes = self.FPCP.to_bytes()
    self.params.put("StarPilotCarParams", fpcp_bytes)
    self.params.put_nonblocking("StarPilotCarParamsPersistent", fpcp_bytes)

    # OFF -> READY can put the EV9 ADAS ECU into a state that rejects
    # CommunicationControl long before the rest of selfdrive is initialized.
    # For the explicitly armed, fully reconstructed, non-actuating stage only,
    # suppress the ECU immediately after fingerprinting and begin emitting the
    # inactive replacement set while selfdrive finishes starting. This also
    # avoids a second knockout at the normal controls-ready handoff.
    ev9_test = get_ev9_longitudinal_test_config(self.params) if str(self.CP.carFingerprint) == "KIA_EV9" else None
    ev9_early_requested = bool(not self.CP.passive and ev9_test is not None and
                               ev9_test.stage == EV9LongitudinalTestStage.STEERING_KEEPALIVE and
                               ev9_test.persistent_suppression_allowed)
    if ev9_early_requested:
      cloudlog.warning("EV9 early stage-15 interface initialization requested")
      self._initialize_car_interface()
      self.ev9_early_control_active = self.CP.openpilotLongitudinalControl and not self.params.get_bool("EcuDisableFailed")
      cloudlog.warning(f"EV9 early inactive reconstruction active={self.ev9_early_control_active}")

    update_starpilot_toggles()

    self.starpilot_card = StarPilotCard(self.CP, self.FPCP)

    self.sm = self.sm.extend(['starpilotOnroadEvents', 'starpilotPlan', 'starpilotSelfdriveState', 'liveCalibration', 'selfdriveState'])
    self.pm = self.pm.extend(['starpilotCarState'])

  def _initialize_car_interface(self) -> None:
    if self.interface_initialized:
      return

    was_openpilot_long = self.CP.openpilotLongitudinalControl
    self.CI.init(self.CP, *self.can_callbacks)
    # If ECU disable was skipped/failed, strip LONG safety from both parameter
    # sets before ControlsReady lets pandad select the vehicle safety model.
    if was_openpilot_long and self.params.get_bool("EcuDisableFailed"):
      long_flag = 4  # HyundaiSafetyFlags.LONG
      for cfg in self.CP.safetyConfigs:
        cfg.safetyParam &= ~long_flag
      for cfg in self.FPCP.safetyConfigs:
        cfg.safetyParam &= ~long_flag
      self.CP.pcmCruise = True
      self.CP.openpilotLongitudinalControl = False
      self.params.put("CarParams", self.CP.to_bytes())
      self.params.put("StarPilotCarParams", self.FPCP.to_bytes())

    self.interface_initialized = True
    self.params.put_bool_nonblocking("ControlsReady", True)

  def _send_ev9_early_inactive_reconstruction(self, CS: car.CarState) -> None:
    """Maintain the complete non-actuating EV9 replacement set during startup."""
    now_nanos = self.can_log_mono_time if REPLAY else int(time.monotonic() * 1e9)
    self.last_actuators_output, can_sends = self.CI.apply(self.ev9_early_car_control, now_nanos, self.starpilot_toggles)
    self.pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan', valid=CS.canValid))

  def state_update(self) -> tuple[car.CarState, structs.RadarDataT | None]:
    """carState update loop, driven by can"""

    can_strs = messaging.drain_sock_raw(self.can_sock, wait_for_one=True)
    can_list = can_capnp_to_list(can_strs)

    # Update carState from CAN
    CS, FPCS = self.CI.update(can_list, self.starpilot_toggles)
    if self.CP.brand == 'mock':
      CS, FPCS = self.mock_carstate.update(CS, FPCS)

    # Update radar tracks from CAN
    RD: structs.RadarDataT | None = self.RI.update(can_list)

    # Consume the current fused radar state before selecting a preferred EV9
    # display track. The tracker is display-only and must fail closed whenever
    # its vehicle/radar context is not valid.
    self.sm.update(0)

    if str(self.CP.carFingerprint) == "KIA_EV9" and self.ev9_cluster_objects_enabled and \
       self.ev9_cluster_smoothing_enabled:
      radar_valid = self.sm.seen['radarState'] and self.sm.alive['radarState'] and self.sm.valid['radarState']
      main_enabled = bool(getattr(self.CI.CS, "ev9_cruise_main_on", CS.cruiseState.available))
      display_context_valid = ev9_cluster_display_context_valid(
        radar_valid, main_enabled, CS.gearShifter == structs.CarState.GearShifter.drive, CS.standstill, CS.vEgo,
      )
      if not display_context_valid:
        self.ev9_cluster_slots = self.ev9_cluster_tracker.clear()
      elif RD is not None:
        preferred_primary_track_id = -1
        fused_lead = self.sm['radarState'].leadOne
        if fused_lead.status and getattr(fused_lead, "radar", False):
          preferred_primary_track_id = int(getattr(fused_lead, "radarTrackId", -1))
        qualified_track_ids = set(getattr(self.RI, "ev9_cluster_quality_track_ids", set())) \
          if self.ev9_radar_quality_filter_enabled else None
        side_qualified_track_ids = set(getattr(self.RI, "ev9_cluster_strict_side_track_ids", set())) \
          if self.ev9_cluster_strict_side_filter_enabled else None
        side_retention_track_ids = set(getattr(self.RI, "ev9_cluster_side_retention_track_ids", set())) \
          if self.ev9_cluster_strict_side_filter_enabled else None
        self.ev9_cluster_slots = self.ev9_cluster_tracker.update(
          list(RD.points), preferred_primary_track_id, False,
          qualified_track_ids=qualified_track_ids,
          require_preferred_primary=self.ev9_cluster_fused_primary_required,
          side_qualified_track_ids=side_qualified_track_ids,
          side_retention_track_ids=side_retention_track_ids,
          right_enabled=self.ev9_cluster_right_objects_enabled,
          v_ego=float(CS.vEgo),
        )
    elif str(self.CP.carFingerprint) == "KIA_EV9":
      self.ev9_cluster_slots = self.ev9_cluster_tracker.clear()

    if str(self.CP.carFingerprint) == "KIA_EV9":
      if RD is not None:
        self.ev9_software_bsm_last_radar_time = time.monotonic()
        qualified_track_ids = set(getattr(self.RI, "ev9_cluster_quality_track_ids", set()))
        qualified_tracks = [point for point in RD.points if int(getattr(point, "trackId", -1)) in qualified_track_ids]
        raw_state = int(getattr(self.CI.CS, "ev9_raw_blindspot_state", 0))
        raw_base_valid = bool(raw_state & RAW_BASE_MASK)
        if self.ev9_software_bsm_enabled:
          software_bsm = self.ev9_software_bsm_detector.update(
            raw_left=raw_base_valid and bool(raw_state & RAW_LEFT_MASK),
            raw_right=raw_base_valid and bool(raw_state & RAW_RIGHT_MASK),
            fresh=bool(getattr(self.CI.CS, "ev9_raw_blindspot_fresh", False)),
            drive=CS.gearShifter == structs.CarState.GearShifter.drive,
            reverse=CS.gearShifter == structs.CarState.GearShifter.reverse,
            v_ego=float(CS.vEgo),
            steering_angle_deg=float(CS.steeringAngleDeg),
            left_blinker=bool(CS.leftBlinker),
            right_blinker=bool(CS.rightBlinker),
            hazard=bool(CS.leftBlinker and CS.rightBlinker),
            radar_tracks=qualified_tracks,
          )
        else:
          self.ev9_software_bsm_detector.reset()
          software_bsm = self.ev9_software_bsm_detector.update(
            raw_left=False, raw_right=False, fresh=False, drive=False,
            v_ego=0.0, steering_angle_deg=0.0,
          )

        self.CI.CS.ev9_software_bsm_left = software_bsm.left.detected
        self.CI.CS.ev9_software_bsm_right = software_bsm.right.detected
        self.CI.CS.ev9_software_bsm_left_escalated = software_bsm.left.escalated
        self.CI.CS.ev9_software_bsm_right_escalated = software_bsm.right.escalated
        self.CI.CS.ev9_software_bsm_left_source = software_bsm.left.source
        self.CI.CS.ev9_software_bsm_right_source = software_bsm.right.source
        self.CI.CS.ev9_software_bsm_left_confidence = software_bsm.left.confidence
        self.CI.CS.ev9_software_bsm_right_confidence = software_bsm.right.confidence

        native_fresh = bool(getattr(self.CI.CS, "ev9_stock_blindspot_fresh", False) and
                            getattr(self.CI.CS, "ev9_blindspot_source", "neutral") == "stock")
        native_left = bool(getattr(self.CI.CS, "left_blindspot_from_radar", False))
        native_right = bool(getattr(self.CI.CS, "right_blindspot_from_radar", False))
        bsm_outputs = select_ev9_software_bsm_outputs(
          software_bsm,
          detector_enabled=self.ev9_software_bsm_enabled,
          comma_output_enabled=self.ev9_software_bsm_comma_output_enabled,
          vehicle_output_enabled=self.ev9_software_bsm_vehicle_output_enabled,
          native_fresh=native_fresh,
          native_left=native_left,
          native_right=native_right,
        )
        if bsm_outputs.comma_override:
          CS.leftBlindspot = bsm_outputs.comma_left
          CS.rightBlindspot = bsm_outputs.comma_right

        self.CI.CS.ev9_vehicle_bsm_left = bsm_outputs.vehicle_left
        self.CI.CS.ev9_vehicle_bsm_right = bsm_outputs.vehicle_right
        self.CI.CS.ev9_vehicle_bsm_left_escalated = bsm_outputs.vehicle_left_escalated
        self.CI.CS.ev9_vehicle_bsm_right_escalated = bsm_outputs.vehicle_right_escalated

        detector_state = (software_bsm.left.detected, software_bsm.right.detected,
                          software_bsm.left.escalated, software_bsm.right.escalated)
        if detector_state != self.ev9_software_bsm_last_state:
          now = time.monotonic()
          if now - self.ev9_software_bsm_last_log_time >= 1.0:
            cloudlog.info(
              f"EV9 software BSM shadow left={software_bsm.left.detected}/{software_bsm.left.escalated} "
              f"({software_bsm.left.source},{software_bsm.left.confidence:.2f}) "
              f"right={software_bsm.right.detected}/{software_bsm.right.escalated} "
              f"({software_bsm.right.source},{software_bsm.right.confidence:.2f})",
            )
            self.ev9_software_bsm_last_log_time = now
          self.ev9_software_bsm_last_state = detector_state

      elif not self.ev9_software_bsm_enabled or (self.ev9_software_bsm_last_radar_time > 0.0 and
                                                  time.monotonic() - self.ev9_software_bsm_last_radar_time >
                                                  EV9_SOFTWARE_BSM_RADAR_STALE_S):
        # RD=None is normal between the 20 Hz radar trigger frames. Clear only
        # once the complete radar update is actually stale; clearing every CAN
        # tick would make the detector's two-sample acquisition impossible.
        self.ev9_software_bsm_detector.reset()
        self.CI.CS.ev9_software_bsm_left = False
        self.CI.CS.ev9_software_bsm_right = False
        self.CI.CS.ev9_software_bsm_left_escalated = False
        self.CI.CS.ev9_software_bsm_right_escalated = False
        self.CI.CS.ev9_software_bsm_left_source = "neutral"
        self.CI.CS.ev9_software_bsm_right_source = "neutral"
        self.CI.CS.ev9_software_bsm_left_confidence = 0.0
        self.CI.CS.ev9_software_bsm_right_confidence = 0.0
        self.CI.CS.ev9_vehicle_bsm_left = False
        self.CI.CS.ev9_vehicle_bsm_right = False
        self.CI.CS.ev9_vehicle_bsm_left_escalated = False
        self.CI.CS.ev9_vehicle_bsm_right_escalated = False

      plan_valid = self.sm.seen['starpilotPlan'] and self.sm.alive['starpilotPlan'] and self.sm.valid['starpilotPlan']
      plan = self.sm['starpilotPlan']
      self.CI.CS.ev9_cluster_speed_limit_raw = ev9_cluster_display_speed_limit_raw(
        getattr(self.CI.CS, "ev9_cluster_speed_limit_raw", 0),
        self.ev9_cluster_map_speed_limit_fallback_enabled,
        plan_valid,
        str(plan.slcSpeedLimitSource) if plan_valid else "None",
        float(plan.slcSpeedLimit) if plan_valid else 0.0,
        bool(getattr(self.CI.CS, "is_metric", self.is_metric)),
      )

    can_rcv_valid = len(can_strs) > 0

    # Check for CAN timeout
    if not can_rcv_valid:
      self.can_rcv_cum_timeout_counter += 1

    if can_rcv_valid and REPLAY:
      self.can_log_mono_time = messaging.log_from_bytes(can_strs[0]).logMonoTime

    preap_software_cruise = (
      self.CP.brand == "tesla" and self.CP.carFingerprint == "TESLA_MODEL_S_PREAP" and
      self.CP.openpilotLongitudinalControl and not self.CP.pcmCruise
    )
    if not preap_software_cruise:
      self.v_cruise_helper.update_v_cruise(
        CS,
        self.sm['carControl'].enabled,
        self.is_metric,
        self.sm['starpilotPlan'].speedLimitChanged,
        self.starpilot_toggles,
        FPCS,
      )
    else:
      preap_v_cruise_kph = float(CS.cruiseState.speed * CV.MS_TO_KPH)
      self.v_cruise_helper.v_cruise_kph_last = self.v_cruise_helper.v_cruise_kph
      self.v_cruise_helper.v_cruise_kph = preap_v_cruise_kph
      self.v_cruise_helper.v_cruise_cluster_kph = preap_v_cruise_kph
    slc_force_speed = self.params_memory.get_float("SLCForceCruiseSpeed")
    if slc_force_speed > 0:
      if self.is_metric:
        new_cruise_kph = round(slc_force_speed * CV.MS_TO_KPH)
      else:
        new_cruise_kph = round(slc_force_speed * CV.MS_TO_MPH) * IMPERIAL_INCREMENT
      self.v_cruise_helper.v_cruise_kph = max(min(new_cruise_kph, V_CRUISE_MAX), V_CRUISE_MIN)
      self.v_cruise_helper.v_cruise_cluster_kph = self.v_cruise_helper.v_cruise_kph
      self.params_memory.remove("SLCForceCruiseSpeed")

    if self.sm['carControl'].enabled and not self.CC_prev.enabled and not preap_software_cruise:
      # Use CarState w/ buttons from the step selfdrived enables on
      desired_speed_limit = self.sm['starpilotPlan'].slcSpeedLimit + self.sm['starpilotPlan'].slcSpeedLimitOffset
      self.v_cruise_helper.initialize_v_cruise(
        self.CS_prev,
        self.experimental_mode,
        self.resume_prev_button,
        self.starpilot_toggles,
        desired_speed_limit=desired_speed_limit,
      )

    # TODO: mirror the carState.cruiseState struct?
    CS.vCruise = float(self.v_cruise_helper.v_cruise_kph)
    CS.vCruiseCluster = float(self.v_cruise_helper.v_cruise_cluster_kph)

    if any(be.type in (ButtonType.accelCruise, ButtonType.resumeCruise) for be in CS.buttonEvents):
      self.resume_prev_button = True
    elif any(be.type in (ButtonType.decelCruise, ButtonType.setCruise) for be in CS.buttonEvents):
      self.resume_prev_button = False

    FPCS = self.starpilot_card.update(CS, FPCS, self.sm, self.starpilot_toggles)

    return CS, RD, FPCS

  def state_publish(self, CS: car.CarState, RD: structs.RadarDataT | None, FPCS: custom.StarPilotCarState):
    """carState and carParams publish loop"""

    # carParams - logged every 50 seconds (> 1 per segment)
    if self.sm.frame % int(50. / DT_CTRL) == 0:
      cp_send = messaging.new_message('carParams')
      cp_send.valid = True
      cp_send.carParams = self.CP
      self.pm.send('carParams', cp_send)

    # publish new carOutput
    co_send = messaging.new_message('carOutput')
    co_send.valid = self.sm.all_checks(['carControl'])
    co_send.carOutput.actuatorsOutput = self.last_actuators_output
    self.pm.send('carOutput', co_send)

    # kick off controlsd step while we actuate the latest carControl packet
    cs_send = messaging.new_message('carState')
    cs_send.valid = CS.canValid
    cs_send.carState = CS
    cs_send.carState.canErrorCounter = self.can_rcv_cum_timeout_counter
    cs_send.carState.cumLagMs = -self.rk.remaining * 1000.
    self.pm.send('carState', cs_send)

    if RD is not None:
      tracks_msg = messaging.new_message('liveTracks')
      tracks_msg.valid = not any(RD.errors.to_dict().values())
      tracks_msg.liveTracks = RD
      self.pm.send('liveTracks', tracks_msg)

    fpcs_send = messaging.new_message('starpilotCarState')
    fpcs_send.valid = CS.canValid
    fpcs_send.starpilotCarState = FPCS
    self.pm.send('starpilotCarState', fpcs_send)

  def controls_update(self, CS: car.CarState, CC: car.CarControl):
    """control update loop, driven by carControl"""

    if not self.interface_initialized:
      # Initialize CarInterface, once controls are ready
      # TODO: this can make us miss at least a few cycles when doing an ECU knockout
      self._initialize_car_interface()

    if self.sm.all_alive(['carControl']):
      # send car controls over can
      now_nanos = self.can_log_mono_time if REPLAY else int(time.monotonic() * 1e9)
      self._update_redneck_cruise(CS, CC)
      self._update_openpilot_lead_state(CC)
      self.last_actuators_output, can_sends = self.CI.apply(CC, now_nanos, self.starpilot_toggles)
      self.pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan', valid=CS.canValid))

      self.CC_prev = CC

  def _update_openpilot_lead_state(self, CC: car.CarControl) -> None:
    ev9_filtered_objects = str(self.CP.carFingerprint) == "KIA_EV9" and self.ev9_cluster_objects_enabled
    lead_visible = bool(CC.hudControl.leadVisible)
    lead_distance = 0.0
    lead_rel_speed = 0.0

    radar_valid = self.sm.seen['radarState'] and self.sm.alive['radarState'] and self.sm.valid['radarState']
    if radar_valid and not ev9_filtered_objects:
      lead = self.sm['radarState'].leadOne
      if lead.status:
        lead_visible = True
        lead_distance = max(float(lead.dRel), 0.0)
        lead_rel_speed = float(lead.vRel)

    if lead_distance <= OPENPILOT_LEAD_MIN_DISTANCE:
      lead_distance = 0.0
      lead_rel_speed = 0.0

    lead_two_visible = False
    lead_two_distance = 0.0
    lead_two_lateral = 0.0
    if radar_valid and not ev9_filtered_objects:
      lead_two = self.sm['radarState'].leadTwo
      if lead_two.status and float(lead_two.dRel) > OPENPILOT_LEAD_MIN_DISTANCE:
        lead_two_visible = True
        lead_two_distance = max(float(lead_two.dRel), 0.0)
        lead_two_lateral = float(lead_two.yRel)

    adjacent_valid = self.sm.seen['starpilotRadarState'] and self.sm.alive['starpilotRadarState'] and \
      self.sm.valid['starpilotRadarState']

    filtered_slots = None
    qualified_track_ids = set(getattr(self.RI, "ev9_cluster_quality_track_ids", set())) \
      if self.ev9_radar_quality_filter_enabled else None
    if ev9_filtered_objects and self.ev9_cluster_smoothing_enabled:
      # The tracker holds brief raw-track dropouts itself. Once the complete
      # radar service is invalid, fail closed instead of retaining stale cars.
      filtered_slots = self.ev9_cluster_slots if radar_valid else ClusterObjectSlots()
      if filtered_slots.primary is not None:
        lead_visible = True
        lead_distance = filtered_slots.primary.distance
        lead_rel_speed = filtered_slots.primary.relative_speed
      else:
        lead_visible = False

      if filtered_slots.alternate is not None:
        lead_two_visible = True
        lead_two_distance = filtered_slots.alternate.distance
        lead_two_lateral = filtered_slots.alternate.lateral
    elif ev9_filtered_objects and radar_valid:
      lead_left = self.sm['starpilotRadarState'].leadLeft if adjacent_valid else None
      lead_right = self.sm['starpilotRadarState'].leadRight if adjacent_valid else None
      filtered_slots = filtered_radar_slots(self.sm['radarState'].leadOne, self.sm['radarState'].leadTwo,
                                            lead_left, lead_right, self.ev9_cluster_alternate_enabled,
                                            qualified_track_ids)
      if filtered_slots.primary is not None:
        lead_visible = True
        lead_distance = filtered_slots.primary.distance
        lead_rel_speed = filtered_slots.primary.relative_speed
      else:
        # Do not turn a model-only HUD lead into a physical cluster object.
        lead_visible = False

      if filtered_slots.alternate is not None:
        lead_two_visible = True
        lead_two_distance = filtered_slots.alternate.distance
        lead_two_lateral = filtered_slots.alternate.lateral

    if ev9_filtered_objects and filtered_slots is not None:
      filtered_slots = bsm_gated_side_slots(
        filtered_slots,
        bool(getattr(self.CI.CS, 'ev9_vehicle_bsm_left', False)),
        bool(getattr(self.CI.CS, 'ev9_vehicle_bsm_right', False)),
        self.ev9_cluster_side_objects_require_bsm,
      )

    for side in ('left', 'right'):
      visible = False
      distance = 0.0
      lateral = 0.0
      selected = False
      filtered_object = getattr(filtered_slots, side) if filtered_slots is not None else None
      if filtered_object is not None:
        visible = True
        distance = filtered_object.distance
        lateral = filtered_object.lateral
        selected = filtered_object.selected
      elif adjacent_valid and not ev9_filtered_objects:
        lead = getattr(self.sm['starpilotRadarState'], f'lead{side.title()}')
        if lead.status and float(lead.dRel) > OPENPILOT_LEAD_MIN_DISTANCE:
          visible = True
          distance = max(float(lead.dRel), 0.0)
          lateral = float(lead.yRel)
      setattr(self.CI.CS, f'openpilot_lead_{side}_visible', visible)
      setattr(self.CI.CS, f'openpilot_lead_{side}_distance', distance)
      setattr(self.CI.CS, f'openpilot_lead_{side}_lateral', lateral)
      setattr(self.CI.CS, f'openpilot_lead_{side}_selected', selected)

    # Publish the final filtered result. Assigning these before the EV9 tracker
    # ran left hudControl's model-visible bit paired with a zero distance, which
    # produced a persistent zero-metre front object throughout route 00000108.
    self.CI.CS.openpilot_lead_visible = lead_visible
    self.CI.CS.openpilot_lead_distance = lead_distance
    self.CI.CS.openpilot_lead_rel_speed = lead_rel_speed
    self.CI.CS.openpilot_lead_two_visible = lead_two_visible
    self.CI.CS.openpilot_lead_two_distance = lead_two_distance
    self.CI.CS.openpilot_lead_two_lateral = lead_two_lateral
    self.CI.CS.openpilot_radar_valid = radar_valid
    self.CI.CS.panda_faulted = not self.sm.seen['pandaStates'] or any(len(p.faults) > 0 for p in self.sm['pandaStates'])

  def _update_redneck_cruise(self, CS: car.CarState, CC: car.CarControl) -> None:
    if self.redneck_cruise is None:
      return

    v_target_ms, lead_present = self._get_redneck_target_speed(CS)
    send_button, v_target = self.redneck_cruise.run(CS, CC, v_target_ms, self.is_metric, lead_present=lead_present)
    self.CI.CS.redneck_send_button = send_button
    self.CI.CS.redneck_v_target = v_target

  def _get_redneck_target_speed(self, CS: car.CarState) -> tuple[float, bool]:
    starpilot_target_speed = 0.0
    allow_plan_decrease = False
    lead_present = False
    lead_distance_m = 0.0
    lead_rel_speed_ms = 0.0
    lookahead_points = REDNECK_DECREASE_LOOKAHEAD_POINTS
    if self.sm.seen['starpilotPlan'] and self.sm.valid['starpilotPlan']:
      starpilot_target_speed = float(self.sm['starpilotPlan'].vCruise)

    plan_speeds = []
    if self.sm.seen['longitudinalPlan'] and self.sm.valid['longitudinalPlan']:
      longitudinal_plan = self.sm['longitudinalPlan']
      plan_speeds = [float(speed) for speed in longitudinal_plan.speeds if math.isfinite(float(speed))]
      lead_present = bool(longitudinal_plan.hasLead)
      allow_plan_decrease = bool(lead_present or longitudinal_plan.shouldStop or
                                 str(longitudinal_plan.longitudinalPlanSource) != "cruise")
      if lead_present and len(plan_speeds) > 0:
        lookahead_points = len(plan_speeds)
        if self.sm.seen['radarState'] and self.sm.valid['radarState']:
          lead = self.sm['radarState'].leadOne
          if lead.status:
            lead_distance_m = max(float(lead.dRel), 0.0)
            lead_rel_speed_ms = float(lead.vRel)

    return select_redneck_target_speed(
      float(getattr(CS, "vCruise", 0.0)),
      float(CS.cruiseState.speedCluster),
      starpilot_target_speed,
      plan_speeds,
      lookahead_points,
      allow_plan_decrease=allow_plan_decrease,
      lead_present=lead_present,
      lead_distance_m=lead_distance_m,
      lead_rel_speed_ms=lead_rel_speed_ms,
    ), lead_present

  def step(self):
    CS, RD, FPCS = self.state_update()

    self.state_publish(CS, RD, FPCS)

    initialized = (not any(e.name == EventName.selfdriveInitializing for e in self.sm['onroadEvents']) and
                   self.sm.seen['onroadEvents'])
    if not self.CP.passive and initialized:
      self.controls_update(CS, self.sm['carControl'])
    elif self.ev9_early_control_active:
      self._send_ev9_early_inactive_reconstruction(CS)

    self.initialized_prev = initialized
    self.CS_prev = CS

    self.CI.CS.CC = self.sm['carControl']

    self.starpilot_toggles = get_starpilot_toggles(self.sm)

  def params_thread(self, evt):
    while not evt.is_set():
      self.safe_mode = self.params.get_bool("SafeMode")
      self.is_metric = self.params.get_bool("IsMetric")
      self.experimental_mode = self.params.get_bool("ExperimentalMode") and self.CP.openpilotLongitudinalControl and not self.safe_mode
      self.ev9_cluster_objects_enabled = self.params.get_bool("KiaEv9ClusterObjectsEnabled")
      self.ev9_cluster_alternate_enabled = self.params.get_bool("KiaEv9ClusterAlternateLeadEnabled")
      self.ev9_cluster_smoothing_enabled = self.params.get_bool("KiaEv9ClusterObjectSmoothingEnabled")
      self.ev9_cluster_map_speed_limit_fallback_enabled = self.params.get_bool("KiaEv9ClusterMapSpeedLimitFallbackEnabled")
      self.ev9_radar_quality_filter_enabled = default_enabled_param(self.params, "KiaEv9RadarQualityFilterEnabled")
      self.ev9_cluster_fused_primary_required = default_enabled_param(self.params, "KiaEv9ClusterFusedPrimaryRequired")
      self.ev9_cluster_side_objects_require_bsm = self.params.get_bool("KiaEv9ClusterSideObjectsRequireBsmEnabled")
      self.ev9_cluster_strict_side_filter_enabled = default_enabled_param(
        self.params, "KiaEv9ClusterStrictSideObjectFilterEnabled",
      )
      self.ev9_cluster_right_objects_enabled = self.params.get_bool("KiaEv9ClusterRightObjectsEnabled")
      self.ev9_software_bsm_enabled = self.params.get_bool(EV9_SOFTWARE_BSM_PARAM)
      self.ev9_software_bsm_comma_output_enabled = self.params.get_bool(EV9_SOFTWARE_BSM_COMMA_OUTPUT_PARAM)
      self.ev9_software_bsm_vehicle_output_enabled = self.params.get_bool(EV9_SOFTWARE_BSM_VEHICLE_OUTPUT_PARAM)
      time.sleep(0.1)

  def card_thread(self):
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
  config_realtime_process(4, Priority.CTRL_HIGH)
  car = Car()
  car.card_thread()


if __name__ == "__main__":
  main()
