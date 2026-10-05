#!/usr/bin/env python3
import os
import time
import threading
import uuid
from collections import deque

import openpilot.cereal.messaging as messaging

from openpilot.cereal import log
from opendbc.car.structs import car

from openpilot.common.params import Params
from openpilot.common.realtime import config_realtime_process, Priority, Ratekeeper
from openpilot.common.swaglog import cloudlog, ForwardingHandler

from opendbc.car import DT_CTRL, structs
from opendbc.car.can_definitions import CanData, CanRecvCallable, CanSendCallable
from opendbc.car.carlog import carlog
from opendbc.car.fw_versions import ObdCallback
from opendbc.car.car_helpers import get_car, interfaces
from opendbc.car.gm.distance_button import GMDistanceButtons
from opendbc.car.gm.profiles import profiles_supported as gm_profiles_supported
from opendbc.car.hyundai.ioniq6_handoff import (IONIQ6_LONG_PREARM_ENABLED, HandoffOutcome,
                                                IONIQ6_ECAN_BUS, TimestampedCanPacket, build_ioniq6_hda2_long_candidate,
                                                prepare_ioniq6_long_candidate, confirm_ioniq6_prepared_takeover, restore_ioniq6_adas,
                                                inspect_ioniq6_long_sources)
from opendbc.car.hyundai.ioniq6_media import Ioniq6MediaButtons
from opendbc.car.hyundai.values import CAR as HYUNDAI_CAR
from opendbc.car.interfaces import CarInterfaceBase, RadarInterfaceBase
from openpilot.selfdrive.pandad import can_capnp_to_list, can_list_to_can_capnp
from openpilot.selfdrive.car.cruise import VCruiseHelper, SlcPendingConfirmation
from openpilot.starpilot.speed_limits import physical_actions as slc_physical
from openpilot.starpilot.aol.intent import disarming_fault, independent_axis_requested, read_settings
from opendbc.car.honda.stock_aol import (
  qualified as qualified_honda_stock_aol, native_observation as honda_native_observation,
  temporary_restriction as honda_temporary_restriction,
)
from opendbc.car.mazda.stock_aol import (qualified as qualified_mazda_aol,
                                        native_observation as mazda_native_observation,
                                        temporary_restriction as mazda_temporary_restriction)
from opendbc.car.tesla.preap.aol import (
  qualified as qualified_tesla_preap, native_observation as preap_native_observation,
  temporary_restriction as preap_temporary_restriction,
)
from opendbc.car.ford.aol import (
  qualified as qualified_ford_aol, native_observation as ford_native_observation,
  temporary_restriction as ford_temporary_restriction,
)
from opendbc.car.hyundai.canfd_angle_aol import native_observation, temporary_restriction, qualified as qualified_angle_aol
from openpilot.starpilot.aol.runtime import current_native
from openpilot.starpilot.aol.vehicle import create_intent as create_aol_intent, native_latch_rejected, policy_for as aol_policy_for
from openpilot.starpilot.aol.wire import IntentState, encode_intent
from openpilot.starpilot.conditional_mode.manual import Button, ButtonTracker, IoniqMediaMapCache, WheelMapCache, Press, ioniq6_media_eligible
from openpilot.starpilot.longitudinal.ioniq6_start import eligible as ioniq6_long_eligible
from opendbc.car.gm.ordinary_cc import control_transport_required as gm_cc_transport_required
from openpilot.starpilot.longitudinal.toyota_output_policy import CLOCK_PAIR_MAX_SKEW_NS, clock_pair_ns
from openpilot.starpilot.longitudinal.cruise_intervals import read_cruise_intervals
from openpilot.starpilot.conditional_mode.card_input import conditional_manual_candidate, conditional_traffic_candidate
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner
from openpilot.starpilot.conditional_mode.status import settings_fingerprint
from openpilot.starpilot.feature_runtime import requested as feature_requested
from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.vehicle_selection import startup_candidate
from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences
from openpilot.starpilot.controller_extensions import configure_controller
from openpilot.starpilot.vehicle_startup import VehicleStartupOwner
from openpilot.starpilot.controllers.wheel_actions import WheelPublisher, key_for
from openpilot.starpilot.controllers.cruise_action import CruiseActionConsumer, eligible as cruise_action_eligible
from openpilot.starpilot.schema_cache import get_cache, prewarm_cache_contracts, put_cache

REPLAY = "REPLAY" in os.environ

EventName = log.OnroadEvent.EventName
DISTANCE_GESTURE_KEYS = {Press.SHORT: ('DistanceButtonControl', 0),
                         Press.LONG: ('LongDistanceButtonControl', 1),
                         Press.VERY_LONG: ('VeryLongDistanceButtonControl', 2)}

# forward
carlog.addHandler(ForwardingHandler(cloudlog))


def obd_callback(params: Params) -> ObdCallback:
  def set_obd_multiplexing(obd_multiplexing: bool):
    if params.get_bool("ObdMultiplexingEnabled") != obd_multiplexing:
      cloudlog.warning(f"Setting OBD multiplexing to {obd_multiplexing}")
      params.remove("ObdMultiplexingChanged")
      params.put_bool("ObdMultiplexingEnabled", obd_multiplexing, block=True)
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
      ret.append(TimestampedCanPacket([CanData(msg.address, msg.dat, msg.src) for msg in can.can], int(can.logMonoTime)))
    return ret

  def can_send(msgs: list[CanData]) -> None:
    sendcan.send(can_list_to_can_capnp(msgs, msgtype='sendcan'))

  return can_recv, can_send


def curve_press_receipt(CS: car.CarState, helper: VCruiseHelper, sm, *, curve_replay: bool,
                        slc_replay: bool, host_long_active: bool, observed_ns: int):
  """Reserve SLC presentation presses even when their command is stale or rejected."""
  accelerate = frozenset((car.CarState.ButtonEvent.Type.accelCruise,
                          car.CarState.ButtonEvent.Type.resumeCruise))
  pressed = {b.type.raw for b in CS.buttonEvents if b.pressed and b.type.raw in accelerate}
  if (not curve_replay or not host_long_active or not CS.canValid or CS.canTimeout or not CS.cruiseState.available or
      not pressed):
    return None
  if slc_replay and (helper.slc_consumed_button is not None or bool(pressed & helper.slc_suppressed_buttons) or
                     bool(sm['slcState'].hasPending)):
    return None
  return ('curveAccelPress', None, float(helper.v_cruise_kph_last / 3.6),
          float(helper.v_cruise_kph / 3.6), observed_ns)


def alpha_long_requested(params, *, is_release: bool) -> bool:
  """Retain saved intent on release branches without granting Alpha authority."""
  return not is_release and params.get_bool("AlphaLongitudinalEnabled")


class Car:
  CI: CarInterfaceBase
  RI: RadarInterfaceBase
  CP: car.CarParams
  controller_cruise_sock = None
  curve_replay = False
  car_params_published = False

  def __init__(self, CI=None, RI: RadarInterfaceBase | None = None, startup_owner=None) -> None:
    prewarm_cache_contracts(("CarParamsCache", "CarParamsPersistent", "CarParamsPrevRoute"))
    self.can_sock = messaging.sub_sock('can', timeout=20)
    self.params = Params()
    self.slc_replay = os.getenv('SLC_REPLAY_RUNTIME') == '1' or feature_requested(self.params, 'slc')
    self.curve_replay = os.getenv('CURVE_REPLAY_RUNTIME') == '1' or feature_requested(self.params, 'curve')
    self.aol_replay = os.getenv('AOL_REPLAY_RUNTIME') == '1' or feature_requested(self.params, 'aol')
    self.conditional_replay = os.getenv('CONDITIONAL_MODE_REPLAY_RUNTIME') == '1' or feature_requested(self.params, 'conditional')
    subscribed_services = ['pandaStates', 'carControl', 'onroadEvents', 'deviceState']
    if self.aol_replay:
      subscribed_services.append('aolSafetyWire')
    if self.slc_replay:
      subscribed_services.append('slcState')
    self.sm = messaging.SubMaster(subscribed_services)
    self.slc_cruise_event_id = 0
    self.slc_producer_session = uuid.uuid4().hex
    self.slc_command_sock = messaging.sub_sock('slcCruiseCommand', conflate=False) if self.slc_replay else None
    self.slc_commands = deque(maxlen=8)
    self.slc_last_command_id = 0
    self.slc_command_session = ''
    self.slc_receipts: list[tuple[str, object, float, float, int]] = []
    self.manual_receipt = None
    self.manual_event_sequence = 0
    self.traffic_receipt = None
    self.traffic_event_sequence = 0
    self.switchback_receipt = None
    self.switchback_event_sequence = 0
    publish_services = ['sendcan', 'carState', 'carParams', 'carOutput', 'radarTracks']
    # One existing event channel also carries source-qualified Switchback gestures.
    publish_services.append('slcCruiseEvent')
    self.wheel_publisher = WheelPublisher(self.params)
    self.wheel_commands = ()
    if self.slc_replay:
      publish_services.append('slcDashboardObservation')
    if self.aol_replay:
      publish_services.append('aolIntentWire')
    self.pm = messaging.PubMaster(publish_services)

    self.can_rcv_cum_timeout_counter = 0

    self.CC_prev = car.CarControl.new_message()
    self.CS_prev = car.CarState.new_message()
    self.initialized_prev = False
    self.ci_initialized = False

    self.last_actuators_output = structs.CarControl.Actuators()

    self.manual_button_tracker = ButtonTracker() if self.conditional_replay else None
    self.traffic_button_tracker = ButtonTracker() if self.conditional_replay else None
    self.ioniq_media_map = IoniqMediaMapCache() if self.conditional_replay else None
    self.manual_settings_owner = ConditionalSettingsOwner(self.params) if self.conditional_replay else None
    self.ioniq6_long_prearmed = False
    self.ioniq6_long_pending = False
    self.ioniq6_long_selected = False
    self.ioniq6_last_preflight_at = 0.0
    self.ioniq6_panda_armed = False
    self.ioniq6_host_warmed = False
    self.ioniq6_long_lost = False
    self.ioniq6_keepalive = None
    self.ioniq6_restore_callbacks = None
    self.ioniq6_restore_attempted = False
    self.ioniq6_init_complete = False

    self.vehicle_startup = VehicleStartupOwner(startup_owner)
    self.can_callbacks = can_comm_callbacks(self.can_sock, self.pm.sock['sendcan'])

    is_release = self.params.get_bool("IsReleaseBranch")
    openpilot_enabled_toggle = self.params.get_bool("OpenpilotEnabledToggle")
    startup_preferences = VehicleStartupPreferences.read(self.params, enabled=openpilot_enabled_toggle)

    if CI is None:
      # wait for one pandaState and one CAN packet
      print("Waiting for CAN messages...")
      while True:
        can = messaging.recv_one_retry(self.can_sock)
        if len(can.can) > 0:
          break

      alpha_long_allowed = alpha_long_requested(self.params, is_release=is_release)

      cached_params = None
      cached_params_raw = get_cache(self.params, "CarParamsCache")
      if cached_params_raw is not None:
        with car.CarParams.from_bytes(cached_params_raw) as _cached_params:
          cached_params = _cached_params

      def pre_create_hook(cp, candidate, fingerprints, car_fw):
        if candidate == HYUNDAI_CAR.HYUNDAI_IONIQ_6:
          # This decision must precede CarInterface parser/controller construction
          # and the first CarParams publication below. The exact opt-in is
          # still subject to current source and restore verification.
          eligible = alpha_long_allowed and IONIQ6_LONG_PREARM_ENABLED and not is_release and openpilot_enabled_toggle and not self.params.get_bool("IsOffroad")
          if eligible:
            self.sm.update(0)
            eligible = bool(self.sm.valid['pandaStates'] and self.sm.alive['pandaStates'] and
                            any(ps.ignitionLine or ps.ignitionCan for ps in self.sm['pandaStates']))
          long_cp = build_ioniq6_hda2_long_candidate(cp, fingerprints) if eligible else None
          if long_cp is not None:
            preflight = inspect_ioniq6_long_sources(self.can_callbacks[0])
            cloudlog.event('ioniq6_long_preflight', reason=preflight.reason)
            if preflight.source_period is None:
              long_cp = None
          if long_cp is not None and self.aol_replay and independent_axis_requested(read_settings(self.params)):
            # Bit 11 is AOL only inside the exact Ioniq 6 bit-15 namespace.
            # This immutable choice precedes the ECU transaction and CP publish.
            long_cp.safetyConfigs[-1].safetyParam |= 0x0800
          cp, self.ioniq6_long_pending = prepare_ioniq6_long_candidate(
            cp, long_cp, enabled=eligible, is_release=is_release)
          self.ioniq6_long_selected = self.ioniq6_long_pending
        cp = startup_preferences.prepare(cp, fingerprints=fingerprints)
        return self.vehicle_startup.prepare(cp, interfaces[candidate], self.can_callbacks,
                                            requested=alpha_long_allowed and not is_release and openpilot_enabled_toggle,
                                            admission=self.startup_diagnostic_admission)

      self.CI = get_car(*self.can_callbacks, obd_callback(self.params), alpha_long_allowed, is_release, cached_params,
                        pre_create_hook=pre_create_hook,
                        forced_candidate=startup_candidate(self.params, developer_fingerprint=bool(os.getenv('FINGERPRINT'))))
      self.RI = interfaces[self.CI.CP.carFingerprint].RadarInterface(self.CI.CP)
      self.CP = self.CI.CP

      # continue onto next fingerprinting step in pandad
      self.params.put_bool("FirmwareQueryDone", True, block=True)
    else:
      self.CI, self.CP = CI, CI.CP
      if RI is None:
        raise ValueError('explicit car interface requires a radar interface')
      self.RI = RI

    self.volt_cc_selected = gm_cc_transport_required(self.CP)
    self.volt_cc_boot_offset_ns = None
    self.volt_cc_source_floor_ns = 0
    if self.volt_cc_selected and 'deviceState' not in subscribed_services:
      subscribed_services.append('deviceState')
      self.sm = messaging.SubMaster(subscribed_services, ignore_alive=['deviceState'], ignore_valid=['deviceState'],
                                    ignore_avg_freq=['deviceState'])

    self.CP.alternativeExperience = 0
    self.switchback_capable = ioniq6_media_eligible(self.CP)
    self.ioniq6_media = Ioniq6MediaButtons(IONIQ6_ECAN_BUS) if self.switchback_capable else None
    self.switchback_button_tracker = ButtonTracker() if self.switchback_capable else None
    self.switchback_settings_owner = ConditionalSettingsOwner(self.params) if self.switchback_capable else None
    self.gm_distance = GMDistanceButtons() if self.conditional_replay and gm_profiles_supported(self.CP) else None
    self.gm_distance_map = WheelMapCache(include_ioniq_media=False) if self.gm_distance is not None else None
    self.gm_distance_claim_tracker = ButtonTracker() if self.gm_distance is not None else None
    controller_available = self.CI.CC is not None and openpilot_enabled_toggle and not self.CP.dashcamOnly
    self.CP.passive = not controller_available or self.CP.dashcamOnly
    if self.CP.passive:
      safety_config = structs.CarParams.SafetyConfig()
      safety_config.safetyModel = structs.CarParams.SafetyModel.noOutput
      self.CP.safetyConfigs = [safety_config]

    startup_preferences.finalize(self.CP)
    startup_preferences.configure_controller(self.CI)
    configure_controller(self.CI, self.params)
    self.vehicle_startup.configure(self.CI)

    if self.CP.secOcRequired:
      # Copy user key if available
      try:
        with open("/cache/params/SecOCKey") as f:
          user_key = f.readline().strip()
          if len(user_key) == 32:
            self.params.put("SecOCKey", user_key, block=True)
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

    self.is_metric = self.params.get_bool("IsMetric")
    aol_policy = aol_policy_for(self.CP)
    if aol_policy.full_axis_runtime_required and not self.aol_replay:
      self.aol_replay = True
      subscribed_services.append('aolSafetyWire')
      self.sm = messaging.SubMaster(subscribed_services)
      self.pm.sock['aolIntentWire'] = messaging.pub_sock('aolIntentWire')
    self.aol_settings = read_settings(self.params) if self.aol_replay else None
    self.aol_qualified = bool(self.aol_settings is not None and
                              (aol_policy.full_axis_runtime_required or aol_policy.physical_stalk_owner or independent_axis_requested(self.aol_settings,
                                include_auxiliary=aol_policy.intent_supported and not aol_policy.explicit_latch)) and
                              aol_policy.intent_supported and not self.CP.passive)
    self.aol_card_intent = (create_aol_intent(self.CP, self.aol_settings, aol_policy)
                            if self.aol_qualified and self.aol_settings is not None else None)
    self.distance_personality_tracker = ButtonTracker() if aol_policy.distance_personality else None
    self.aol_sequence = 0
    if self.aol_qualified:
      self.CP.safetyConfigs[0].safetyParam |= aol_policy.safety_param_addition
      self.CP.alternativeExperience |= aol_policy.alternative_experience_addition
    self.vehicle_startup.finalize_aol_configuration(self.CI)

    # Write previous route's CarParams
    prev_cp = get_cache(self.params, "CarParamsPersistent")
    if prev_cp is not None:
      with car.CarParams.from_bytes(prev_cp) as previous:
        put_cache(self.params, "CarParamsPrevRoute", previous, block=True)

    # Write CarParams for controls and radard
    self.vehicle_startup.seal_publication()
    cp_bytes = self.CP.to_bytes()
    self.params.put("CarParams", cp_bytes, block=True)
    put_cache(self.params, "CarParamsCache", self.CP)
    put_cache(self.params, "CarParamsPersistent", self.CP)

    self.controller_cruise_consumer = CruiseActionConsumer()
    self.controller_cruise_sock = messaging.sub_sock('slcAction', conflate=False) if cruise_action_eligible(self.CP) else None
    self.v_cruise_helper = VCruiseHelper(self.CP)
    self.v_cruise_helper.intervals = read_cruise_intervals(self.params, pcm_cruise=self.CP.pcmCruise)

    self.experimental_mode = self.params.get_bool("ExperimentalMode")

    # card is driven by can recv, expected at 100Hz
    self.rk = Ratekeeper(100, print_delay_threshold=None)
    self.ioniq6_init_complete = True

  def observe_distance_personality(self, CS: car.CarState, now_ns: int) -> None:
    tracker = getattr(self, 'distance_personality_tracker', None)
    if tracker is None:
      return
    for gesture in tracker.observe(CS):
      if gesture.button is not Button.DISTANCE:
        continue
      key, slot = DISTANCE_GESTURE_KEYS[gesture.press]
      try:
        raw, readable = read_saved(self.params, key, 8)
      except (OSError, TypeError, ValueError):
        raw, readable = None, False
      sampled = self.aol_card_intent.settings.distance_actions[slot] if self.aol_card_intent is not None else 0
      handled = sampled in (3, 4) or sampled == 9 and self.aol_card_intent is not None and \
        self.aol_card_intent.settings.enabled and not self.aol_card_intent.explicit_latch
      configured = readable and (raw in (b'3', b'4') or ioniq6_long_eligible(self.CP) and raw == b'5')
      if handled or configured:
        tracker.claim(gesture, now_ns, key)

  def state_update(self) -> tuple[car.CarState, structs.RadarDataT | None]:
    """carState update loop, driven by can"""

    can_strs = messaging.drain_sock_raw(self.can_sock, wait_for_one=True)
    can_list = can_capnp_to_list(can_strs)

    # Update carState from CAN
    CS = self.CI.update(can_list)
    self.observe_ioniq6_long_authority(can_list, CS)
    media_owner = getattr(self, 'ioniq6_media', None)
    media_observation = media_owner.update(can_list) if media_owner is not None else None
    distance_owner = getattr(self, 'gm_distance', None)
    distance_observation = distance_owner.update(can_list) if distance_owner is not None else None

    # Update radar tracks from CAN
    RD: structs.RadarDataT | None = self.RI.update(can_list)

    self.sm.update(0)

    self.update_vehicle_state_context(CS)

    can_rcv_valid = len(can_strs) > 0

    # Check for CAN timeout
    if not can_rcv_valid:
      self.can_rcv_cum_timeout_counter += 1

    if can_rcv_valid and REPLAY:
      self.can_log_mono_time = messaging.log_from_bytes(can_strs[0]).logMonoTime

    self.slc_receipts = []
    now_ns = int(self.can_log_mono_time) if REPLAY and hasattr(self, 'can_log_mono_time') else time.monotonic_ns()
    evidence = getattr(self.CI.CS, 'dashboard_limit', None) if self.slc_replay else None
    observation = evidence.observation if evidence is not None else None
    control_log_ns = int(self.sm.logMonoTime['carControl'])
    host_enabled = bool(
      CS.canValid and not CS.canTimeout and
      self.CC_prev.enabled and
      self.sm.valid['carControl'] and self.sm.alive['carControl'] and
      0 < control_log_ns <= now_ns and now_ns - control_log_ns <= slc_physical.STATE_MAX_AGE_NS and
      self.sm['carControl'].enabled)
    host_control_enabled = bool(self.CP.openpilotLongitudinalControl and not self.CP.pcmCruise and host_enabled)
    host_long_active = host_control_enabled and self.sm['carControl'].longActive
    slc_long_active = self.slc_replay and host_long_active
    pending = None
    if observation is not None and self.slc_replay:
      pending = slc_physical.pending_confirmation(
        self.sm, observation, self.slc_producer_session, now_ns,
        long_active=slc_long_active, pcm_cruise=bool(self.CP.pcmCruise))
    self.v_cruise_helper.update_v_cruise(CS, self.sm['carControl'].enabled, self.is_metric, pending)
    if self.sm['carControl'].enabled and not self.CC_prev.enabled:
      # Initialization owns this edge; evaluate commands against its final speed.
      self.v_cruise_helper.initialize_v_cruise(self.CS_prev, self.experimental_mode,
                                            resume=self.vehicle_startup.consume_cruise_resume())
    if self.controller_cruise_sock is not None:
      for _ in range(8):
        request = messaging.recv_one_or_none(self.controller_cruise_sock)
        if request is None:
          break
        self.controller_cruise_consumer.apply(request, self.CP, CS, self.sm, self.v_cruise_helper,
                                             now_ns=now_ns, is_metric=self.is_metric,
                                             enabled=bool(host_control_enabled and can_rcv_valid and not self.params.get_bool("SafeMode")))
    consumed = self.v_cruise_helper.slc_consumed_button
    if self.aol_card_intent is not None:
      fault_active = None
      event_ns = int(self.sm.logMonoTime['onroadEvents'])
      if (getattr(self.aol_card_intent, 'requires_fault_observation', self.aol_card_intent.explicit_latch) and
          self.sm.updated['onroadEvents'] and
          self.sm.valid['onroadEvents'] and 0 < event_ns <= now_ns and now_ns - event_ns <= 1_500_000_000):
        fault_active = disarming_fault(self.sm['onroadEvents'], CS)
      angle_aol = qualified_angle_aol(self.CP, marked_only=True)
      ford_aol = qualified_ford_aol(self.CP, marked_only=True)
      honda_aol = qualified_honda_stock_aol(self.CP, marked_only=True)
      mazda_aol = qualified_mazda_aol(self.CP, marked_only=True)
      preap_aol = qualified_tesla_preap(self.CP, marked_only=True)
      permission_owner = angle_aol or ford_aol or honda_aol or mazda_aol or preap_aol
      angle_panda_ready = not permission_owner or self.startup_panda_configured()
      native = (
        current_native(self.sm, self.CP, now_ns=now_ns, axis_session_id=self.slc_producer_session if permission_owner else None)
        if self.aol_card_intent.explicit_latch and (permission_owner or self.sm.updated['aolSafetyWire'])
        else None
      )
      native_reset = False
      if permission_owner:
        observe = (preap_native_observation if preap_aol else mazda_native_observation if mazda_aol else honda_native_observation if honda_aol else
                   ford_native_observation if ford_aol else native_observation)
        restrict = (preap_temporary_restriction if preap_aol else mazda_temporary_restriction if mazda_aol else honda_temporary_restriction if honda_aol else
                    ford_temporary_restriction if ford_aol else temporary_restriction)
        preap_observation = {}
        if preap_aol:
          cancel_stamp = int(self.CI.CS.preap.cancel_echo_stamp_ns)
          if cancel_stamp > getattr(self, '_preap_cancel_echo_stamp_ns', 0):
            self._preap_cancel_echo_stamp_ns = cancel_stamp
            self._preap_cancel_echo_pending_ns = now_ns
          preap_observation['pending_cancel_ns'] = getattr(self, '_preap_cancel_echo_pending_ns', 0)
        pending_since, lost, native_reset = observe(
          native,
          latched=self.aol_card_intent.allowed_latch,
          panda_ready=angle_panda_ready,
          restricted=restrict(self.CP, CS) or ((mazda_aol or preap_aol) and self.aol_card_intent.pause_lateral),
          now_ns=now_ns,
          pending_since_ns=getattr(self, '_angle_aol_pending_since_ns', 0),
          **preap_observation,
        )
        if (preap_aol and native is not None and preap_observation['pending_cancel_ns'] and
            native.observedMonoTime >= preap_observation['pending_cancel_ns']):
          self._preap_cancel_echo_pending_ns = 0
        self._angle_aol_pending_since_ns = pending_since
        if lost:
          fault_active = True
      rejected = native_reset or native_latch_rejected(self.CP, native, state=CS if angle_panda_ready else None)
      rejection_ns = now_ns if native_reset else int(native.observedMonoTime) if rejected else 0
      self.aol_card_intent.update(CS, fault_active=fault_active, now_ns=now_ns, native_rejection_ns=rejection_ns,
                                  standard_enabled=(host_enabled if getattr(self.aol_card_intent, 'observe_stock_engagement', False)
                                                    else host_control_enabled))
    if self.aol_card_intent is not None and preap_aol:
      self.CI.CS.preap_lateral_authorized = bool(
        native is not None and native.lateralAllowed and self.aol_card_intent.allowed_latch and
        not self.aol_card_intent.pause_lateral and CS.canValid and not CS.canTimeout and
        CS.gearShifter == structs.CarState.GearShifter.drive and not CS.doorOpen and
        not CS.seatbeltUnlatched and not CS.steerFaultPermanent and not CS.steeringDisengage)
    if self.aol_card_intent is not None:
      self.aol_card_intent.update_auxiliary(CS, media=media_observation,
        media_eligible=ioniq6_media_eligible(self.CP), fault_active=fault_active)
      self.observe_aol_calibration(CS, now_ns,
        host_enabled if getattr(self.aol_card_intent, 'observe_stock_engagement', False) else host_control_enabled)
    self.observe_distance_personality(CS, now_ns)
    gm_claim = getattr(self, 'gm_distance_claim_tracker', None)
    if gm_claim is not None:
      gm_claim.observe(CS)
    self.manual_receipt = None
    self.traffic_receipt = None
    if (self.conditional_replay and (not REPLAY or hasattr(self, 'can_log_mono_time')) and
        self.manual_button_tracker is not None and self.manual_settings_owner is not None):
      # Refresh is internally rate-limited to one Params read per second. A
      # held gesture loses its claim if the drive or saved mode changes.
      manual_snapshot = self.manual_settings_owner.refresh(now_ns)
      manual_drive_id = int(self.sm['deviceState'].startedMonoTime)
      manual_verdict = self.manual_settings_owner.verdict(manual_snapshot, now_mono_ns=now_ns, drive_id=manual_drive_id)
      manual_fingerprint = (settings_fingerprint(manual_snapshot) if manual_verdict.status == 'ready' and manual_verdict.safe_mode is False and
                            manual_verdict.selection is not None and manual_verdict.selection.choice in (ModeChoice.CEM, ModeChoice.CCM)
                            else None)
      self.manual_button_tracker.keep_claim(manual_drive_id, manual_fingerprint)
      shared_media_map = (self.ioniq_media_map.sample(self.params, media_observation, now_ns)
                          if self.ioniq_media_map is not None and ioniq6_media_eligible(self.CP) else None)
      shared_media_captured = self.ioniq_media_map is not None and ioniq6_media_eligible(self.CP)
      self.manual_receipt = conditional_manual_candidate(
        CS, self.manual_button_tracker, self.params, self.manual_settings_owner, self.CP, self.sm,
        now_ns=now_ns, explicit_aol_latch=bool(self.aol_card_intent is not None and self.aol_card_intent.explicit_latch),
        media=media_observation, media_buttons=shared_media_map, media_map_captured=shared_media_captured)
      if self.manual_receipt is not None:
        gesture, drive_id, fingerprint, _, _ = self.manual_receipt
        self.manual_button_tracker.claim(gesture, drive_id, fingerprint)
      gm_buttons = (self.gm_distance_map.sample(self.params, distance_observation, now_ns)
                    if distance_owner is not None else None)
      if self.traffic_button_tracker is not None:
        self.traffic_receipt = conditional_traffic_candidate(
          CS, self.traffic_button_tracker, self.params, self.manual_settings_owner,
          self.CP, self.sm, now_ns=now_ns, media=media_observation,
          media_buttons=gm_buttons if distance_owner is not None else shared_media_map,
          media_map_captured=distance_owner is not None or shared_media_captured, distance=distance_observation)
        if self.traffic_receipt is not None and self.traffic_receipt[0] and distance_owner is not None and gm_claim is not None:
          gm_claim.claim(self.traffic_receipt[1], self.traffic_receipt[2], self.traffic_receipt[3])
    self.switchback_receipt = None
    if self.switchback_button_tracker is not None and self.switchback_settings_owner is not None:
      self.switchback_receipt = conditional_traffic_candidate(
        CS, self.switchback_button_tracker, self.params, self.switchback_settings_owner,
        self.CP, self.sm, now_ns=now_ns, media=media_observation, action=7)
    if consumed is not None:
      self.slc_receipts.append(('confirmationAccept' if consumed.button == 'accel' else 'confirmationReject',
                                consumed, 0.0, 0.0, now_ns))
    curve_receipt = curve_press_receipt(CS, self.v_cruise_helper, self.sm, curve_replay=self.curve_replay,
                                        slc_replay=self.slc_replay, host_long_active=host_long_active, observed_ns=now_ns)
    if curve_receipt is not None:
      self.slc_receipts.append(curve_receipt)
    if self.slc_replay and self.slc_command_sock is not None:
      for _ in range(8):
        command_message = messaging.recv_one_or_none(self.slc_command_sock)
        if command_message is None:
          break
        if command_message.valid:
          self.slc_commands.append(command_message)
      for _ in range(len(self.slc_commands)):
        command_message = self.slc_commands.popleft()
        command = command_message.slcCruiseCommand
        if now_ns < int(command.issuedMonoTime):
          if now_ns <= int(command.expiresMonoTime):
            self.slc_commands.append(command_message)
          continue
        state = (slc_physical.state_current(self.sm, observation, self.slc_producer_session, now_ns)
                 if observation is not None else None)
        if (state is None or int(self.sm.logMonoTime['slcState']) < int(command.issuedMonoTime)) and now_ns < int(command.expiresMonoTime):
          self.slc_commands.append(command_message)
          continue
        if state is not None and str(state.sessionId) != self.slc_command_session:
          self.slc_command_session = str(state.sessionId)
          self.slc_last_command_id = 0
        if not self.slc_command_session:
          self.slc_command_session = str(command.sessionId)
        if str(command.sessionId) != self.slc_command_session or int(command.commandId) <= self.slc_last_command_id:
          continue
        self.slc_last_command_id = int(command.commandId)
        previous_mps = float(self.v_cruise_helper.v_cruise_kph / 3.6)
        origin = SlcPendingConfirmation(str(command.sessionId), int(command.decisionId), int(command.presentationId))
        owners = {**self.v_cruise_helper.slc_suppression_owner, **self.v_cruise_helper.slc_released_owner}
        allowed_buttons = {button for button, owner in owners.items() if owner == origin} if int(command.decisionId) > 0 else set()
        intervening_button = (bool(self.v_cruise_helper.slc_cruise_change) or
                              any(b.type.raw not in allowed_buttons for b in CS.buttonEvents) or
                              any(timer > 0 and button not in allowed_buttons
                                  for button, timer in self.v_cruise_helper.button_timers.items()))
        applicable = slc_physical.command_applicable(
          command, state, observation, self.slc_producer_session, now_ns, previous_mps,
          long_active=slc_long_active, pcm_cruise=bool(self.CP.pcmCruise),
          button_event=intervening_button)
        if applicable:
          self.v_cruise_helper.apply_slc_target(float(command.targetMps), self.is_metric)
        self.slc_receipts.append(('commandApplied' if applicable else 'commandRejected', command,
                                  previous_mps, float(self.v_cruise_helper.v_cruise_kph / 3.6), now_ns))
    blocked_keys = set()
    if self.manual_receipt is not None:
      blocked_keys.add(key_for(self.manual_receipt[0]))
    for receipt in (self.traffic_receipt, self.switchback_receipt):
      if receipt is not None and receipt[0] and receipt[1] is not None:
        blocked_keys.add(key_for(receipt[1]))
    self.wheel_commands = self.wheel_publisher.observe(
      self.params, self.CP, CS, now_ns=now_ns, drive_id=int(self.sm['deviceState'].startedMonoTime),
      media=media_observation, blocked_keys=blocked_keys)
    # TODO: mirror the carState.cruiseState struct?
    CS.vCruise = float(self.v_cruise_helper.v_cruise_kph)
    CS.vCruiseCluster = float(self.v_cruise_helper.v_cruise_cluster_kph)

    return CS, RD

  def observe_aol_calibration(self, CS, now_ns: int, standard_enabled: bool) -> None:
    calibration_events = None
    event_ns = int(self.sm.logMonoTime['onroadEvents'])
    if (self.sm.updated['onroadEvents'] and self.sm.valid['onroadEvents'] and
        0 < event_ns <= now_ns and now_ns - event_ns <= 1_500_000_000):
      calibration_events = self.sm['onroadEvents']
    self.aol_card_intent.observe_calibration(CS, events=calibration_events, standard_enabled=standard_enabled)

  def state_publish(self, CS: car.CarState, RD: structs.RadarDataT | None):
    """carState and carParams publish loop"""

    # Publish the finalized CP immediately, then retain the segment cadence.
    if not self.car_params_published or self.sm.frame % int(50. / DT_CTRL) == 0:
      cp_send = messaging.new_message('carParams')
      cp_send.valid = True
      cp_send.carParams = self.CP
      self.pm.send('carParams', cp_send)
      self.car_params_published = True

    # publish new carOutput
    co_send = messaging.new_message('carOutput')
    co_send.valid = self.sm.all_checks(['carControl'])
    co_send.carOutput.actuatorsOutput = self.last_actuators_output
    self.pm.send('carOutput', co_send)

    # kick off controlsd step while we actuate the latest carControl packet
    cs_send = messaging.new_message('carState')
    if (self.slc_replay or self.curve_replay or getattr(self, 'conditional_replay', False)) and REPLAY and hasattr(self, 'can_log_mono_time'):
      cs_send.logMonoTime = int(self.can_log_mono_time)
    cs_send.valid = CS.canValid
    cs_send.carState = CS
    manual_tracker = getattr(self, 'manual_button_tracker', None)
    personality_tracker = getattr(self, 'distance_personality_tracker', None)
    gm_claim = getattr(self, 'gm_distance_claim_tracker', None)
    if ((getattr(self, 'conditional_replay', False) and manual_tracker is not None and manual_tracker.suppress_distance_release) or
        (personality_tracker is not None and personality_tracker.suppress_distance_release) or
        (gm_claim is not None and gm_claim.suppress_distance_release) or
        (getattr(self, 'wheel_publisher', None) is not None and self.wheel_publisher.suppress_distance_release)):
      # This is the serialized carState copy. Keep the original parsed state
      # and raw CAN intact for the controller and diagnostics.
      cs_send.carState.buttonEvents = [event for event in CS.buttonEvents if not
                                       (event.type == car.CarState.ButtonEvent.Type.gapAdjustCruise and not event.pressed)]
    cs_send.carState.canErrorCounter = self.can_rcv_cum_timeout_counter
    cs_send.carState.cumLagMs = -self.rk.remaining * 1000.
    if self.aol_replay:
      self.aol_sequence += 1
      intent_msg = messaging.new_message('aolIntentWire', 0)
      intent_msg.logMonoTime = int(cs_send.logMonoTime)
      intent_msg.valid = bool(cs_send.valid and self.aol_qualified)
      allowed_latch = pause_lateral = pause_longitudinal = False
      lateral_armed = False
      if self.aol_card_intent is not None:
        allowed_latch, pause_lateral, pause_longitudinal = self.aol_card_intent.output(CS)
        lateral_armed = self.aol_card_intent.allowed_latch
      intent_msg.aolIntentWire = encode_intent(IntentState(
        self.slc_producer_session, self.aol_sequence, int(cs_send.logMonoTime), int(cs_send.logMonoTime),
        int(cs_send.logMonoTime) + 200_000_000, allowed_latch, pause_lateral, pause_longitudinal, self.aol_qualified, lateral_armed))
      self.pm.send('aolIntentWire', intent_msg)

    # carState wakes selfdrived. Commit its companion intent first, so a
    # consumer scheduled at the wakeup cannot sample the preceding intent.
    if self.CP.brand == 'tesla':
      from openpilot.starpilot.car.tesla.stock_events import publish_stock_status
      internal = getattr(self.CI.CS, 'preap', None)
      if internal is not None:
        self.slc_cruise_event_id += 1
        publish_stock_status(self.pm, self.CP, internal, session=self.slc_producer_session,
                             sequence=self.slc_cruise_event_id, car_state_stamp=int(cs_send.logMonoTime),
                             valid=bool(cs_send.valid and not CS.canTimeout))
    self.pm.send('carState', cs_send)

    wheel = getattr(self, 'wheel_publisher', None)
    if wheel is not None:
      wheel.publish(self.wheel_commands, self.CP, self.pm, now_ns=int(cs_send.logMonoTime),
                    drive_id=int(self.sm['deviceState'].startedMonoTime), source_car_ns=int(cs_send.logMonoTime),
                    source_control_ns=int(self.sm.logMonoTime['carControl']))

    if self.slc_replay:
      source = messaging.new_message('slcDashboardObservation')
      source.logMonoTime = int(cs_send.logMonoTime)
      source.valid = bool(cs_send.valid)
      evidence = getattr(self.CI.CS, 'dashboard_limit', None)
      source.slcDashboardObservation.producerSessionId = self.slc_producer_session
      source.slcDashboardObservation.carStateLogMonoTime = int(cs_send.logMonoTime)
      if evidence is not None:
        observation = evidence.observation
        source.slcDashboardObservation.status = observation.status.value
        source.slcDashboardObservation.speedMps = observation.speed_mps
        source.slcDashboardObservation.observedMonoTime = observation.observed_ns
        source.slcDashboardObservation.validUntilMonoTime = observation.valid_until_ns
        source.slcDashboardObservation.episode = observation.episode
      self.pm.send('slcDashboardObservation', source)

    change = self.v_cruise_helper.slc_cruise_change
    if (self.slc_replay or self.curve_replay) and not self.CP.pcmCruise:
      if change is not None:
        self.slc_receipts.append(('driverChange', change, change[0], change[1], int(cs_send.logMonoTime)))
      for kind, detail, previous_mps, selected_mps, observed_ns in self.slc_receipts:
        self.slc_cruise_event_id += 1
        event = messaging.new_message('slcCruiseEvent')
        event.logMonoTime = int(cs_send.logMonoTime)
        event.valid = bool(cs_send.valid)
        record = event.slcCruiseEvent
        record.eventId = self.slc_cruise_event_id
        record.producerSessionId = self.slc_producer_session
        record.observedMonoTime = observed_ns
        record.kind = kind
        record.previousMps = previous_mps
        record.selectedMps = selected_mps
        if kind == 'driverChange':
          assert isinstance(detail, tuple) and len(detail) == 4
          record.button, record.longPress = detail[2], detail[3]
        elif kind in ('confirmationAccept', 'confirmationReject'):
          record.button = detail.button
          record.sessionId = detail.pending.session_id
          record.decisionId = detail.pending.decision_id
          record.presentationId = detail.pending.presentation_id
        elif kind == 'curveAccelPress':
          record.button = 'accel'
        else:
          record.sessionId = str(detail.sessionId)
          record.commandId = int(detail.commandId)
          record.decisionId = int(detail.decisionId)
          record.presentationId = int(detail.presentationId)
        self.pm.send('slcCruiseEvent', event)

    if getattr(self, 'conditional_replay', False) and self.manual_receipt is not None:
      gesture, drive_id, fingerprint, choice, observed_ns = self.manual_receipt
      self.slc_cruise_event_id += 1
      self.manual_event_sequence += 1
      event = messaging.new_message('slcCruiseEvent')
      event.logMonoTime = int(cs_send.logMonoTime)
      event.valid = bool(cs_send.valid)
      record = event.slcCruiseEvent
      record.eventId = self.slc_cruise_event_id
      record.producerSessionId = self.slc_producer_session
      record.observedMonoTime = observed_ns
      record.kind = 'conditionalMode'
      record.manualMode = {
        'version': 1, 'sessionId': self.slc_producer_session, 'sequence': self.manual_event_sequence,
        'observedMonoTime': observed_ns, 'driveStartMonoTime': drive_id,
        'settingsFingerprint': fingerprint,
        'choice': 'conditionalExperimental' if choice is ModeChoice.CEM else 'conditionalChill',
        'button': gesture.button.value, 'press': gesture.press.value,
        'sourceCarStateMonoTime': int(cs_send.logMonoTime),
        'validUntilMonoTime': int(cs_send.logMonoTime) + 100_000_000,
      }
      self.pm.send('slcCruiseEvent', event)

    self.publish_traffic_receipt(cs_send)

    if RD is not None:
      tracks_msg = messaging.new_message('radarTracks')
      tracks_msg.valid = not any(RD.errors.to_dict().values())
      tracks_msg.radarTracks = RD
      self.pm.send('radarTracks', tracks_msg)

  def publish_traffic_receipt(self, cs_send):
    traffic_receipt = getattr(self, 'traffic_receipt', None)
    if getattr(self, 'conditional_replay', False) and traffic_receipt is not None:
      toggle, gesture, drive_id, fingerprint, map_fingerprint, source_epoch, source_boot_ns, observed_ns = traffic_receipt
      self.slc_cruise_event_id += 1
      self.traffic_event_sequence += 1
      event = messaging.new_message('slcCruiseEvent')
      event.logMonoTime = int(cs_send.logMonoTime)
      event.valid = bool(cs_send.valid)
      record = event.slcCruiseEvent
      record.eventId = self.slc_cruise_event_id
      record.producerSessionId = self.slc_producer_session
      record.observedMonoTime = observed_ns
      record.kind = 'trafficMode'
      record.trafficMode = {
        'version': 1, 'sessionId': self.slc_producer_session, 'sequence': self.traffic_event_sequence,
        'observedMonoTime': observed_ns, 'driveStartMonoTime': drive_id,
        'settingsFingerprint': fingerprint, 'buttonMapFingerprint': map_fingerprint,
        'sourceEpoch': source_epoch, 'sourceBootTime': source_boot_ns,
        'sourceCarStateMonoTime': int(cs_send.logMonoTime),
        'validUntilMonoTime': int(cs_send.logMonoTime) + 100_000_000,
        'toggle': toggle, 'button': gesture.button.value if gesture is not None else 'unknown',
        'press': gesture.press.value if gesture is not None else 'unknown',
      }
      self.pm.send('slcCruiseEvent', event)

    switchback_receipt = getattr(self, 'switchback_receipt', None)
    if getattr(self, 'switchback_capable', False) and switchback_receipt is not None:
      toggle, gesture, drive_id, fingerprint, map_fingerprint, source_epoch, source_boot_ns, observed_ns = switchback_receipt
      self.slc_cruise_event_id += 1
      self.switchback_event_sequence += 1
      event = messaging.new_message('slcCruiseEvent')
      event.logMonoTime = int(cs_send.logMonoTime)
      event.valid = bool(cs_send.valid)
      record = event.slcCruiseEvent
      record.eventId = self.slc_cruise_event_id
      record.producerSessionId = self.slc_producer_session
      record.observedMonoTime = observed_ns
      record.kind = 'switchbackMode'
      record.trafficMode = {
        'version': 1, 'sessionId': self.slc_producer_session, 'sequence': self.switchback_event_sequence,
        'observedMonoTime': observed_ns, 'driveStartMonoTime': drive_id,
        'settingsFingerprint': fingerprint, 'buttonMapFingerprint': map_fingerprint,
        'sourceEpoch': source_epoch, 'sourceBootTime': source_boot_ns,
        'sourceCarStateMonoTime': int(cs_send.logMonoTime),
        'validUntilMonoTime': int(cs_send.logMonoTime) + 100_000_000,
        'toggle': toggle, 'button': gesture.button.value if gesture is not None else 'unknown',
        'press': gesture.press.value if gesture is not None else 'unknown',
      }
      self.pm.send('slcCruiseEvent', event)

  def observe_ioniq6_long_authority(self, can_list, CS):
    if getattr(self, 'ioniq6_long_selected', False) and self.ioniq6_long_lost:
      CS.canValid = False
      return
    if not self.ioniq6_long_prearmed:
      return
    if any((src == 1 and address in (0x1A0, 0x1BA, 0x1E5)) or (src == 0 and address == 0x100)
           for _, packet in can_list for address, _, src in packet):
      self.ioniq6_long_lost = True
    if CS.canValid:
      self.ioniq6_host_warmed = True
    elif self.ioniq6_host_warmed:
      self.ioniq6_long_lost = True
    if self.ioniq6_long_lost:
      CS.canValid = False
      if self.ioniq6_keepalive is not None:
        self.ioniq6_keepalive.stop()

  def ioniq6_panda_matches(self):
    panda_states = self.sm['pandaStates']
    return bool(
      self.sm.valid['pandaStates'] and self.sm.alive['pandaStates'] and
      len(panda_states) >= len(self.CP.safetyConfigs) and
      all(ps.safetyModel == config.safetyModel and ps.safetyParam == config.safetyParam and
          ps.alternativeExperience == self.CP.alternativeExperience and not ps.safetyRxChecksInvalid
          for ps, config in zip(panda_states, self.CP.safetyConfigs, strict=False))
    )

  def ioniq6_panda_diagnostic_ready(self):
    if not self.sm.valid['pandaStates'] or not self.sm.alive['pandaStates']:
      return False
    panda_states = self.sm['pandaStates']
    return bool(
      len(panda_states) == len(self.CP.safetyConfigs) and
      all(ps.safetyModel == structs.CarParams.SafetyModel.elm327 and
          ps.safetyParam in (0, 1) and not ps.controlsAllowed
          for ps in panda_states)
    )

  def update_vehicle_state_context(self, state):
    holder = getattr(self, 'vehicle_startup', None)
    if holder is None or holder.owner is None:
      return
    # Python controls and receive times use MONOTONIC. Panda/CAN producers
    # use BOOTTIME, which can diverge after suspend.
    clocks = clock_pair_ns()
    mono_ns, boot_ns = clocks if clocks is not None else (0, 0)
    sm = self.sm
    control_stamp = int(sm.logMonoTime['carControl'])
    control_receipt = int(sm.recv_time['carControl'] * 1e9)
    panda_stamp = int(sm.logMonoTime['pandaStates'])
    panda_receipt = int(sm.recv_time['pandaStates'] * 1e9)
    control_current = bool(clocks is not None and
                           sm.seen['carControl'] and sm.valid['carControl'] and sm.alive['carControl'] and
                           0 < control_stamp <= mono_ns and mono_ns - control_stamp <= 150_000_000 and
                           0 < control_receipt <= mono_ns and mono_ns - control_receipt <= 150_000_000)
    panda_current = bool(clocks is not None and
                         sm.seen['pandaStates'] and sm.valid['pandaStates'] and sm.alive['pandaStates'] and
                         0 < panda_stamp <= boot_ns and boot_ns - panda_stamp <= 300_000_000 and
                         0 < panda_receipt <= mono_ns and mono_ns - panda_receipt <= 300_000_000)
    holder.after_state(ci=self.CI, state=state, now_ns=boot_ns,
                       control_enabled=bool(sm['carControl'].enabled), control_current=control_current,
                       pandas=sm['pandaStates'], panda_log_ns=panda_stamp,
                       panda_recv_ns=panda_receipt + boot_ns - mono_ns if panda_current else 0,
                       panda_current=panda_current)

  def startup_diagnostic_admission(self):
    self.sm.update(0)
    now, boot = time.monotonic_ns(), time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    sm = self.sm
    stamp, receipt = int(sm.logMonoTime['pandaStates']), int(sm.recv_time['pandaStates'] * 1e9)
    pandas = sm['pandaStates']
    return bool(not self.params.get_bool('IsOffroad') and not self.params.get_bool('ControlsReady') and
                sm.seen['pandaStates'] and sm.valid['pandaStates'] and sm.alive['pandaStates'] and
                0 < stamp <= boot and boot - stamp <= 300_000_000 and
                0 < receipt <= now and now - receipt <= 300_000_000 and len(pandas) == 1 and
                all(ps.safetyModel == structs.CarParams.SafetyModel.elm327 and ps.safetyParam == 1 and
                    not ps.controlsAllowed and not ps.safetyRxChecksInvalid and
                    (ps.ignitionLine or ps.ignitionCan) for ps in pandas))

  def startup_panda_configured(self):
    now, boot = time.monotonic_ns(), time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    sm = self.sm
    stamp, receipt = int(sm.logMonoTime['pandaStates']), int(sm.recv_time['pandaStates'] * 1e9)
    pandas = sm['pandaStates']
    return bool(sm.seen['pandaStates'] and sm.valid['pandaStates'] and sm.alive['pandaStates'] and
                0 < stamp <= boot and boot - stamp <= 300_000_000 and
                0 < receipt <= now and now - receipt <= 300_000_000 and
                len(pandas) == len(self.CP.safetyConfigs) and
                all(ps.safetyModel == cfg.safetyModel and ps.safetyParam == cfg.safetyParam and
                    ps.alternativeExperience == self.CP.alternativeExperience and not ps.safetyRxChecksInvalid
                    for ps, cfg in zip(pandas, self.CP.safetyConfigs, strict=True)))

  def publish_sendcan(self, frames, valid=True):
    packet = can_list_to_can_capnp(frames, msgtype='sendcan', valid=valid)
    if getattr(self, 'volt_cc_selected', False):
      # CAN producer/parser and pandad send age use BOOTTIME; Python controls/device envelopes use MONOTONIC.
      builder = messaging.log_from_bytes(packet).as_builder()
      builder.logMonoTime = int(getattr(self, 'volt_cc_now_boot_ns', 0))
      packet = builder.to_bytes()
    if self.vehicle_startup.owner is not None:
      with self.vehicle_startup.send_lock:
        self.pm.send('sendcan', packet)
      # Successful send acknowledgment is outside the sender lock, before any join.
      self.vehicle_startup.sent(frames, valid=valid)
    elif self.ioniq6_long_prearmed and self.ioniq6_keepalive is not None:
      # The diagnostic sender and the normal controller share one PubSocket.
      with self.ioniq6_keepalive.lock:
        self.pm.send('sendcan', packet)
    else:
      self.pm.send('sendcan', packet)

  def volt_cc_control_current(self):
    pair = clock_pair_ns()
    if pair is None or REPLAY:
      self.volt_cc_boot_offset_ns = None
      return False
    now_ns, boot_ns = pair
    offset = boot_ns - now_ns
    if self.volt_cc_boot_offset_ns is None or abs(offset - self.volt_cc_boot_offset_ns) > CLOCK_PAIR_MAX_SKEW_NS:
      self.volt_cc_boot_offset_ns = offset
      self.volt_cc_source_floor_ns = now_ns
      return False
    sm = self.sm
    if not all(sm.seen[name] and sm.alive[name] and sm.valid[name] for name in ('carControl', 'deviceState')):
      return False
    drive_id = int(sm['deviceState'].startedMonoTime)
    if not sm['deviceState'].started or drive_id <= 0:
      return False
    for name, limit in (('carControl', 150_000_000), ('deviceState', 2_000_000_000)):
      source_ns, receipt_ns = int(sm.logMonoTime[name]), int(sm.recv_time[name] * 1e9)
      if (not max(drive_id, self.volt_cc_source_floor_ns) < source_ns <= receipt_ns <= now_ns or
          now_ns - source_ns > limit or now_ns - receipt_ns > limit):
        return False
    self.volt_cc_drive_id = drive_id
    self.volt_cc_now_boot_ns = boot_ns
    self.volt_cc_now_mono_ns = now_ns
    return True

  def controls_update(self, CS: car.CarState, CC: car.CarControl):
    """control update loop, driven by carControl"""

    if getattr(self, 'volt_cc_selected', False):
      if not self.volt_cc_control_current():
        self.publish_sendcan([], valid=False)
        return
      physical = getattr(self.CI.CS, 'volt_cc_physical', None)
      if physical is None or any(source - self.volt_cc_boot_offset_ns <= max(self.volt_cc_drive_id, self.volt_cc_source_floor_ns)
                                 for source in (physical.observed_ns, *physical.source_ns)):
        self.publish_sendcan([], valid=False)
        return
      if physical.button_credit_ns - self.volt_cc_boot_offset_ns <= max(self.volt_cc_drive_id, self.volt_cc_source_floor_ns):
        self.CI.CC.volt_cc_consumed_source_ns = physical.button_credit_ns
      self.CI.CC.volt_cc_metric = self.is_metric

    if getattr(self.CI.CC, "bolt_cc_profile", False):
      self.CI.CC.bolt_cc_metric = self.is_metric

    if not self.ci_initialized:
      # Keep stock ECU output intact until CAN and controls are ready.
      if (not CS.canValid or CS.canTimeout or not self.sm.valid['carControl'] or
          not self.sm.all_alive(['carControl'])):
        self.publish_sendcan([], valid=False)
        return
      if getattr(self, 'ioniq6_long_pending', False):
        # Panda is still in its diagnostic safety mode here. Take over only
        # after the control producer is ready, then request Hyundai safety.
        if not self.ioniq6_panda_diagnostic_ready():
          self.publish_sendcan([], valid=False)
          return
        handoff_started = time.monotonic()
        if handoff_started - self.ioniq6_last_preflight_at < 0.5:
          self.publish_sendcan([], valid=False)
          return
        self.ioniq6_last_preflight_at = handoff_started
        try:
          self.ioniq6_handoff_result = confirm_ioniq6_prepared_takeover(*self.can_callbacks)
        except Exception:
          cloudlog.exception("Ioniq 6 takeover transaction failed")
          self.ioniq6_handoff_result = None
        result = self.ioniq6_handoff_result
        cloudlog.event('ioniq6_long_handoff',
                       outcome=result.outcome.name if result is not None else 'EXCEPTION',
                       reason=result.reason if result is not None else 'transaction_exception',
                       elapsed_s=round(time.monotonic() - handoff_started, 3))
        if result is not None and result.outcome is HandoffOutcome.NOT_READY:
          self.publish_sendcan([], valid=False)
          return
        self.ioniq6_long_pending = False
        if result is None or result.outcome is not HandoffOutcome.CONFIRMED:
          self.ioniq6_long_lost = True
          self.ci_initialized = True
          CS.canValid = False
          self.publish_sendcan([], valid=False)
          return
        self.ioniq6_long_prearmed = True
        # The transaction consumed Card's CAN cursor. Rewarm the host parser
        # from post-handoff independent inputs before its first controller TX.
        self.ioniq6_host_warmed = False
        self.ioniq6_restore_callbacks = self.can_callbacks
      elif self.vehicle_startup.owner is None:
        self.CI.init(self.CP, *self.can_callbacks)
      # signal pandad to switch to car safety mode
      self.params.put_bool("ControlsReady", True)
      self.ci_initialized = True

    self.vehicle_startup.check()
    now_ns = time.monotonic_ns()
    control_current = bool(self.sm.seen['carControl'] and self.sm.alive['carControl'] and self.sm.valid['carControl'] and
                           0 < int(self.sm.logMonoTime['carControl']) <= now_ns and
                           now_ns - int(self.sm.logMonoTime['carControl']) <= 150_000_000 and
                           0 < int(self.sm.recv_time['carControl'] * 1e9) <= now_ns and
                           now_ns - int(self.sm.recv_time['carControl'] * 1e9) <= 150_000_000)
    if self.vehicle_startup.owner is not None and not self.vehicle_startup.before_control(
        configured=self.startup_panda_configured(), ci=self.CI,
        now_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME), control_current=control_current):
      self.publish_sendcan([], valid=False)
      return

    if getattr(self, 'ioniq6_long_selected', False) and not self.ioniq6_long_prearmed:
      CS.canValid = False
      self.publish_sendcan([], valid=False)
      return

    if self.ioniq6_long_prearmed:
      panda_matches = self.ioniq6_panda_matches()
      if not panda_matches and self.ioniq6_panda_armed:
        self.ioniq6_long_lost = True
      self.ioniq6_panda_armed |= panda_matches
      if not panda_matches or not self.ioniq6_host_warmed or self.ioniq6_long_lost or not CS.canValid:
        self.publish_sendcan([], valid=False)
        return

    if self.sm.valid['carControl'] and self.sm.all_alive(['carControl']):
      if self.ioniq6_long_prearmed and self.ioniq6_keepalive is not None:
        self.ioniq6_keepalive.stop()
        if self.ioniq6_long_lost:
          self.publish_sendcan([], valid=False)
          return
      # send car controls over can
      now_nanos = (self.volt_cc_now_boot_ns if getattr(self, 'volt_cc_selected', False) else
                   self.can_log_mono_time if REPLAY else int(time.monotonic() * 1e9))
      self.last_actuators_output, can_sends = self.CI.apply(CC, now_nanos)
      self.publish_sendcan(can_sends, valid=CS.canValid)

      self.CC_prev = CC

  def step(self):
    CS, RD = self.state_update()

    if self.vehicle_startup.owner is not None:
      self.vehicle_startup.maintain(configured=self.startup_panda_configured())
    self.state_publish(CS, RD)

    initialized = (not any(e.name == EventName.selfdriveInitializing for e in self.sm['onroadEvents']) and
                   self.sm.seen['onroadEvents'])
    if not self.CP.passive and initialized:
      self.controls_update(CS, self.sm['carControl'])

    self.initialized_prev = initialized
    self.CS_prev = CS

  def params_thread(self, evt):
    next_cruise_read = 0.0
    while not evt.is_set():
      self.is_metric = self.params.get_bool("IsMetric")
      self.experimental_mode = self.params.get_bool("ExperimentalMode") and self.CP.openpilotLongitudinalControl
      if self.aol_card_intent is not None:
        self.aol_card_intent.settings = read_settings(self.params)
      now = time.monotonic()
      if now >= next_cruise_read:
        self.v_cruise_helper.intervals = read_cruise_intervals(self.params, pcm_cruise=self.CP.pcmCruise)
        next_cruise_read = now + 1.0
      time.sleep(0.1)

  def card_thread(self):
    e = threading.Event()
    t = threading.Thread(target=self.params_thread, args=(e, ))
    try:
      t.start()
      while True:
        self.vehicle_startup.check()
        self.step()
        self.rk.monitor_time()
    finally:
      e.set()
      t.join()
      if self.ioniq6_keepalive is not None:
        self.ioniq6_long_lost = True
        self.ioniq6_keepalive.stop()


def main():
  config_realtime_process(4, Priority.CTRL_HIGH)
  # Retain the partially initialized object so its diagnostic worker can be
  # stopped even if construction fails after a confirmed ECU handoff.
  car = Car.__new__(Car)
  try:
    Car.__init__(car)
    car.card_thread()
  finally:
    if getattr(car, 'vehicle_startup', None) is not None:
      car.vehicle_startup.close()
    if getattr(car, 'ioniq6_keepalive', None) is not None:
      car.ioniq6_long_lost = True
      car.ioniq6_keepalive.stop()
    if getattr(car, 'ioniq6_long_prearmed', False) and not getattr(car, 'ioniq6_restore_attempted', False):
      # This Card is no longer an output owner, even if it had published a
      # qualified CP. Restore stock ECU traffic before a later Card starts.
      # Do not mutate the already published CP or claim stock on failure.
      callbacks = getattr(car, 'ioniq6_restore_callbacks', None)
      if callbacks is not None:
        car.ioniq6_restore_attempted = True
        try:
          restored = restore_ioniq6_adas(*callbacks)
        except Exception:
          restored = False
        if not restored:
          cloudlog.error("Ioniq 6 Card exited; stock SCC restoration unverified")


if __name__ == "__main__":
  main()
