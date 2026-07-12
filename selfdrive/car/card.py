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
from opendbc.car.hyundai.ev9_longitudinal import EV9LongitudinalTestStage, get_ev9_longitudinal_test_config
from opendbc.car.hyundai.interface import attempt_ev9_pre_fingerprint_suppression
from opendbc.car.interfaces import CarInterfaceBase, RadarInterfaceBase
from opendbc.safety import ALTERNATIVE_EXPERIENCE
from openpilot.selfdrive.pandad import can_capnp_to_list, can_list_to_can_capnp
from openpilot.common.constants import CV
from openpilot.selfdrive.car.cruise import VCruiseHelper, IMPERIAL_INCREMENT, V_CRUISE_MAX, V_CRUISE_MIN
from openpilot.selfdrive.car.redneck_cruise import RedneckCruise, select_redneck_target_speed
from openpilot.selfdrive.car.car_specific import MockCarState
from openpilot.selfdrive.car.ev9_cluster_objects import filtered_radar_slots

from openpilot.starpilot.common.starpilot_variables import get_starpilot_toggles, update_starpilot_toggles
from openpilot.starpilot.controls.starpilot_card import StarPilotCard

REPLAY = "REPLAY" in os.environ
OPENPILOT_LEAD_MIN_DISTANCE = 0.1
REDNECK_DECREASE_LOOKAHEAD_POINTS = 10

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
    if self.ev9_cluster_objects_enabled and str(self.CP.carFingerprint) == "KIA_EV9":
      enable_ev9_live_radar_tracks = getattr(self.RI, "enable_ev9_live_radar_tracks", None)
      if enable_ev9_live_radar_tracks is not None:
        cloudlog.warning(f"EV9 cluster live radar tracks enabled={enable_ev9_live_radar_tracks()}")

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

    self.sm.update(0)

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

    self.CI.CS.openpilot_lead_visible = lead_visible
    self.CI.CS.openpilot_lead_distance = lead_distance
    self.CI.CS.openpilot_lead_rel_speed = lead_rel_speed

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
    if ev9_filtered_objects and radar_valid:
      lead_left = self.sm['starpilotRadarState'].leadLeft if adjacent_valid else None
      lead_right = self.sm['starpilotRadarState'].leadRight if adjacent_valid else None
      filtered_slots = filtered_radar_slots(self.sm['radarState'].leadOne, self.sm['radarState'].leadTwo,
                                            lead_left, lead_right, self.ev9_cluster_alternate_enabled)
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

    for side in ('left', 'right'):
      visible = False
      distance = 0.0
      lateral = 0.0
      filtered_object = getattr(filtered_slots, side) if filtered_slots is not None else None
      if filtered_object is not None:
        visible = True
        distance = filtered_object.distance
        lateral = filtered_object.lateral
      elif adjacent_valid and not ev9_filtered_objects:
        lead = getattr(self.sm['starpilotRadarState'], f'lead{side.title()}')
        if lead.status and float(lead.dRel) > OPENPILOT_LEAD_MIN_DISTANCE:
          visible = True
          distance = max(float(lead.dRel), 0.0)
          lateral = float(lead.yRel)
      setattr(self.CI.CS, f'openpilot_lead_{side}_visible', visible)
      setattr(self.CI.CS, f'openpilot_lead_{side}_distance', distance)
      setattr(self.CI.CS, f'openpilot_lead_{side}_lateral', lateral)

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
