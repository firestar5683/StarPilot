#!/usr/bin/env python3
import os
import json
from collections import deque

from opendbc.car.structs import car
from opendbc.car.gm.profiles import profiles_supported as gm_profiles_supported
from openpilot.common.params import Params
from openpilot.common.realtime import Priority, config_realtime_process
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.controls.lib.ldw import LaneDepartureWarning
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner, NATIVE_PLAN_INPUTS
import openpilot.cereal.messaging as messaging
from openpilot.cereal.services import SERVICE_LIST
from openpilot.starpilot.speed_limits import history as slc_history
from openpilot.starpilot.speed_limits.runtime import Action as SlcAction, CruiseEvent as SlcCruiseEvent, Runtime as SlcRuntime
from openpilot.starpilot.longitudinal.profile_runtime import ProfileHost
from openpilot.starpilot.longitudinal.lane_change_gap import LaneGapPreferences
from openpilot.starpilot.longitudinal.experimental_release import ConditionalHandoff
from openpilot.starpilot.longitudinal.lead_approach import LeadApproachKey
from openpilot.starpilot.longitudinal.lead_takeoff_preferences import TakeoffPreferences
from openpilot.starpilot.longitudinal.force_stop_runtime import ForceStopRuntime
from openpilot.starpilot.longitudinal.stop_resume import collect_resume
from openpilot.starpilot.longitudinal.lead_approach_runtime import LeadApproachPreferences
from openpilot.starpilot.curve_speed.host import CurveHost
from openpilot.starpilot.curve_speed.runtime import DriverEvent as CurveDriverEvent
from openpilot.starpilot.curve_speed.preferences import PreferenceHost as CurvePreferenceHost
from openpilot.starpilot.curve_speed.status import StatusPublisher as CurveStatusPublisher
from openpilot.starpilot.model_geometry import road_curvature
from openpilot.starpilot.conditional_mode.planner_host import ConditionalPlannerHost
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.projection import ConditionalOwnerContext, ObservedBool
from openpilot.starpilot.conditional_mode.traffic import TrafficOwner, TrafficVerdict
from openpilot.starpilot.controllers.mode_actions import ModeActionOwner, KINDS as CONTROLLER_MODE_KINDS, publish_switchback, apply_switchback_gesture
import secrets
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner
from openpilot.starpilot.conditional_mode.manual import ioniq6_media_eligible
from openpilot.starpilot.conditional_mode.projection import paired_clocks_ns
from openpilot.starpilot.conditional_mode.ui_action import observation as ui_manual_observation
from openpilot.starpilot.longitudinal.cruise_ceiling import CurveCeiling
from openpilot.starpilot.feature_runtime import enabled as feature_enabled, requested as feature_requested, slc_runtime_settings, vision_control_enabled
import time


def profile_for_frame(host: ProfileHost | None, sm, CP, now_ns: int, *, traffic_mode: bool | None = False):
  if host is None or not sm['carState'].canValid or sm['carState'].canTimeout:
    return None
  required = ('carState', 'carControl', 'selfdriveState', 'controlsState')
  if not all(sm.valid[s] and sm.alive[s] and 0 <= now_ns - int(sm.logMonoTime[s]) <=
             int(2e9 / SERVICE_LIST[s].frequency) for s in required):
    return None
  return host.sample(now_ns, sm['selfdriveState'].personality, float(sm['carState'].vEgo), CP,
                     traffic_mode=traffic_mode)


def global_braking_for_frame(host: ProfileHost | None, sm, now_ns: int) -> str | None:
  if host is None or not sm['carState'].canValid or sm['carState'].canTimeout:
    return None
  required = ('carState', 'carControl', 'selfdriveState', 'controlsState')
  if not all(sm.valid[s] and sm.alive[s] and 0 <= now_ns - int(sm.logMonoTime[s]) <=
             int(2e9 / SERVICE_LIST[s].frequency) for s in required):
    return None
  return host.sample_global_braking(now_ns)


def _profile_frame_valid(sm, now_ns: int) -> bool:
  if not sm['carState'].canValid or sm['carState'].canTimeout:
    return False
  required = ('carState', 'carControl', 'selfdriveState', 'controlsState')
  if not all(sm.valid[s] and sm.alive[s] and 0 <= now_ns - int(sm.logMonoTime[s]) <=
             int(2e9 / SERVICE_LIST[s].frequency) for s in required):
    return False
  return True


def profile_host_needed(CP, *, profile_enabled: bool, conditional_enabled: bool) -> bool:
  """Traffic defaults need a resolver only on the reviewed media topology."""
  return profile_enabled or (conditional_enabled and ioniq6_media_eligible(CP))


def traffic_profile_status(mode: bool | None, target, applied, settings) -> tuple[bool, str]:
  """Report actual post-MPC application, not merely an available target."""
  if mode is not True:
    return False, 'inactive'
  if target is not None and applied is not None:
    return True, 'qualified'
  if target is not None:
    return False, 'target_unapplied'
  reason = getattr(settings, 'reason', 'unavailable')
  return False, 'source_unavailable' if reason == 'valid' else reason


def curve_for_frame(host: CurveHost | None, sm, CP, now_ns: int, *, drive_id: int = 0,
                    event: CurveDriverEvent | None = None, follow_time_s: float | None = None):
  """A diagnostic runtime result is not planner authority by itself."""
  if host is None:
    return None, None
  result = host.sample(sm, CP, now_ns, drive_id=drive_id, event=event, follow_time_s=follow_time_s)
  if result.ceiling_mps is None:
    return None, result
  model_ns = sm.logMonoTime.get('modelV2', 0)
  if type(model_ns) is not int or model_ns <= 0:
    return None, result
  return CurveCeiling(result.ceiling_mps, model_ns), result


def confirm_curve_frame(host: CurveHost | None, planner: LongitudinalPlanner, now_ns: int) -> None:
  if host is not None:
    host.runtime.confirm_applied(now_ns, applied=bool(planner.last_curve_ceiling_applied))


def conditional_handoff_for_frame(host: ConditionalPlannerHost | None, sm, CP, now_ns: int,
                                  drive_id: int) -> ConditionalHandoff | None:
  if host is None or not CP.openpilotLongitudinalControl or CP.passive or CP.dashcamOnly:
    return None
  try:
    stamp = sm.logMonoTime['deviceState']
    device = sm['deviceState']
    if (type(drive_id) is not int or not 0 < drive_id <= stamp <= now_ns or
        not sm.valid['deviceState'] or not sm.alive['deviceState'] or
        now_ns - stamp > int(2e9 / SERVICE_LIST['deviceState'].frequency) or
        not device.started or device.startedMonoTime != drive_id):
      return None
  except (AttributeError, KeyError, TypeError):
    return None
  snapshot = host.settings.refresh(now_ns)
  verdict = host.settings.verdict(snapshot, now_mono_ns=now_ns, drive_id=drive_id)
  if (verdict.status != 'ready' or verdict.safe_mode is not False or verdict.selection is None or
      verdict.selection.choice not in (ModeChoice.CEM, ModeChoice.CCM)):
    return None
  return snapshot.owner_token, snapshot.revision, drive_id, verdict.selection.choice.value


def lead_approach_for_frame(preferences: LeadApproachPreferences | None, sm, CP, now_ns: int) -> LeadApproachKey | None:
  if preferences is None:
    return None
  try:
    device = sm['deviceState']
    stamp = sm.logMonoTime['deviceState']
    if (sm.valid['deviceState'] is not True or sm.alive['deviceState'] is not True or device.started is not True or
        not 0 < device.startedMonoTime <= stamp <= now_ns or
        now_ns - stamp > int(2e9 / SERVICE_LIST['deviceState'].frequency)):
      return None
    return preferences.sample(CP, now_ns, int(device.startedMonoTime))
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return None


def update_curve_frame(planner: LongitudinalPlanner, sm, CP, now_ns: int, *, host: CurveHost | None = None,
                       cruise_ceiling=None, profile_tuning=None, traffic_mode: bool | None = False, drive_id: int = 0,
                       event: CurveDriverEvent | None = None, lane_change_policy=None,
                       global_braking_response: str | None = None, selected_profiles=None, conditional_handoff: ConditionalHandoff | None = None,
                       lead_approach_key: LeadApproachKey | None = None, force_stop_provider=None,
                       faster_lead_takeoff: bool = False):
  """One model cycle: MPC chooses follow time, then Curve samples and receives winner feedback."""
  if host is None:
    planner.update(sm, cruise_ceiling=cruise_ceiling, profile_tuning=profile_tuning, traffic_mode=traffic_mode,
                   lane_change_policy=lane_change_policy, global_braking_response=global_braking_response, selected_profiles=selected_profiles,
                   conditional_handoff=conditional_handoff, lead_approach_key=lead_approach_key, force_stop_provider=force_stop_provider, faster_lead_takeoff=faster_lead_takeoff,
                   takeoff_drive_id=drive_id, now_ns=now_ns, drive_id=drive_id)
    return None
  results = []
  def provider(follow_time_s: float | None):
    ceiling, result = curve_for_frame(host, sm, CP, now_ns, drive_id=drive_id,
                                      event=event, follow_time_s=follow_time_s)
    results.append(result)
    return ceiling
  planner.update(sm, cruise_ceiling=cruise_ceiling, profile_tuning=profile_tuning,
                 curve_provider=provider, traffic_mode=traffic_mode, lane_change_policy=lane_change_policy,
                 global_braking_response=global_braking_response, selected_profiles=selected_profiles, conditional_handoff=conditional_handoff,
                 lead_approach_key=lead_approach_key, force_stop_provider=force_stop_provider, faster_lead_takeoff=faster_lead_takeoff,
                   takeoff_drive_id=drive_id, now_ns=now_ns, drive_id=drive_id)
  confirm_curve_frame(host, planner, now_ns)
  return results[0] if results else None


def queue_cruise_event(event, slc_events, curve_events, conditional_events=None, traffic_events=None) -> None:
  """One nonconflated Card stream preserves both physical and cruise changes."""
  if not event.valid:
    return
  cruise = event.slcCruiseEvent
  kind = str(cruise.kind)
  if kind == 'conditionalMode':
    if conditional_events is not None:
      conditional_events.append(event)
  elif kind == 'trafficMode':
    if traffic_events is not None:
      traffic_events.append(event)
  elif kind == 'curveAccelPress':
    if (not cruise.longPress and str(cruise.button) == 'accel' and
        not (cruise.sessionId or cruise.decisionId or cruise.presentationId or cruise.commandId)):
      curve_events.append(CurveDriverEvent(str(cruise.producerSessionId), int(cruise.eventId),
                                          int(cruise.observedMonoTime), kind, str(cruise.button), int(event.logMonoTime)))
  else:
    slc_events.append(SlcCruiseEvent(int(cruise.eventId), int(cruise.observedMonoTime),
                                   float(cruise.previousMps), float(cruise.selectedMps), str(cruise.button),
                                   str(cruise.producerSessionId), int(event.logMonoTime), kind,
                                   str(cruise.sessionId), int(cruise.decisionId),
                                   int(cruise.presentationId), int(cruise.commandId)))


def current_cruise_event(events, now_ns: int):
  max_event_age_ns = int(2e9 / SERVICE_LIST['modelV2'].frequency)
  while events and now_ns - events[0].observed_ns > max_event_age_ns:
    events.popleft()
  return events.popleft() if events and events[0].observed_ns <= now_ns else None


def queue_ui_action(event, slc_actions, conditional_actions, mode_actions=None) -> None:
  if not event.valid:
    return
  request = event.slcAction
  kind = str(request.kind)
  if kind in CONTROLLER_MODE_KINDS and mode_actions is not None:
    mode_actions.append(event)
  elif kind == 'conditionalModeCycle':
    conditional_actions.append(event)
  elif kind in ('accept', 'reject', 'adopt'):
    slc_actions.append((int(event.logMonoTime), SlcAction(str(request.sessionId), int(request.sequenceId),
                                                       int(request.decisionId), int(request.presentationId), kind)))


def current_ui_manual_event(events, now_ns: int):
  while events:
    event = events.popleft()
    if ui_manual_observation(event, now_ns) is not None:
      return event
  return None


def current_manual_event(events, now_ns: int, car_state_ns: int):
  while events and (not events[0].valid or now_ns > int(events[0].slcCruiseEvent.manualMode.validUntilMonoTime)):
    events.popleft()
  return (events.popleft() if events and
          int(events[0].slcCruiseEvent.manualMode.observedMonoTime) <= now_ns and
          int(events[0].slcCruiseEvent.manualMode.sourceCarStateMonoTime) <= car_state_ns else None)


def current_traffic_event(events, now_ns: int, car_state_ns: int):
  while events and (not events[0].valid or now_ns > int(events[0].slcCruiseEvent.trafficMode.validUntilMonoTime)):
    events.popleft()
  return (events.popleft() if events and
          int(events[0].slcCruiseEvent.trafficMode.observedMonoTime) <= now_ns and
          int(events[0].slcCruiseEvent.trafficMode.sourceCarStateMonoTime) <= car_state_ns else None)


def starpilot_main():
  config_realtime_process(5, Priority.CTRL_LOW)

  cloudlog.info("plannerd is waiting for CarParams")
  params = Params()
  CP = messaging.log_from_bytes(params.get("CarParams", block=True), car.CarParams)
  cloudlog.info("plannerd got CarParams: %s", CP.brand)

  ldw = LaneDepartureWarning()
  longitudinal_planner = LongitudinalPlanner(CP)
  # Saved-on features start only for a finalized, supported driving owner. Their
  # current-source and longitudinal authority checks still run every frame.
  slc_replay = feature_enabled(params, CP, 'slc', os.environ)
  slc_vision_development = slc_replay and feature_enabled(params, CP, 'vision', os.environ)
  profile_replay = feature_enabled(params, CP, 'profile', os.environ)
  curve_replay = feature_enabled(params, CP, 'curve', os.environ)
  conditional_replay = feature_enabled(params, CP, 'conditional', os.environ)
  # A validated Traffic gesture uses its frozen default profile even when
  # CustomPersonalities is off; saved custom category values still require
  # that master switch in ProfileHost.
  traffic_capable = ((conditional_replay and ioniq6_media_eligible(CP)) or
                     (gm_profiles_supported(CP) and feature_requested(params, 'conditional')))
  traffic_settings = ConditionalSettingsOwner(params) if traffic_capable else None
  profile_request_ns = -1_000_000_000
  profile_host = ProfileHost(params) if profile_host_needed(CP, profile_enabled=profile_replay,
                                                            conditional_enabled=conditional_replay) or traffic_capable else None
  lane_gap_preferences = LaneGapPreferences(params) if CP.openpilotLongitudinalControl else None
  approach_preferences = LeadApproachPreferences(params) if CP.openpilotLongitudinalControl else None
  curve_preferences = CurvePreferenceHost(params) if curve_replay else None
  curve_host = curve_preferences.make_host(replay='REPLAY' in os.environ) if curve_preferences is not None else None
  curve_status = CurveStatusPublisher() if curve_host is not None else None
  force_stop_owner = ForceStopRuntime(params) if CP.openpilotLongitudinalControl else None
  takeoff_preferences = TakeoffPreferences(params) if CP.openpilotLongitudinalControl else None
  stop_resume_sock = messaging.sub_sock("carState", conflate=False) if force_stop_owner is not None else None
  conditional_host = (ConditionalPlannerHost(params, enabled_scene_owners=(frozenset({'traffic_mode'}) if traffic_capable else frozenset()) |
                                                                        frozenset({'forcing_stop', 'plan_forcing_stop'}),
                                             slc_runtime_enabled=slc_replay) if conditional_replay else None)
  traffic_owner = TrafficOwner() if traffic_capable else None
  mode_owner = ModeActionOwner() if ioniq6_media_eligible(CP) else None
  mode_session, mode_sequence = secrets.token_hex(16), 0
  pending_modes = deque(maxlen=8)
  pending_switchback = deque(maxlen=8)
  mode_settings = ConditionalSettingsOwner(params) if mode_owner is not None else None
  slc_runtime = (SlcRuntime(slc_runtime_settings(params, CP, os.environ), vision_enabled=slc_vision_development,
                            vision_control_qualified=vision_control_enabled(params, CP),
                            vision_display_qualified=feature_enabled(params, CP, 'vision', {}))
                 if slc_replay else None)
  slc_action_sock = messaging.sub_sock("slcAction", conflate=False) if slc_runtime is not None or conditional_host is not None or mode_owner is not None else None
  slc_cruise_sock = (messaging.sub_sock("slcCruiseEvent", conflate=False)
                     if slc_runtime is not None or curve_host is not None or conditional_host is not None or traffic_owner is not None or mode_owner is not None else None)
  pending_slc_actions = deque(maxlen=64)
  pending_slc_cruise = deque(maxlen=64)
  pending_curve_events = deque(maxlen=64)
  pending_conditional_events = deque(maxlen=64)
  pending_conditional_ui = deque(maxlen=64)
  pending_traffic_events = deque(maxlen=64)
  drive_start_ns = 0
  publish_services = ['longitudinalPlan', 'driverAssistance']
  if slc_runtime is not None or curve_host is not None or conditional_host is not None or traffic_owner is not None or mode_owner is not None:
    publish_services.append('slcState')
  if slc_runtime is not None:
    publish_services.append('slcCruiseCommand')
  pm = messaging.PubMaster(publish_services)
  native_plan_checks = list(NATIVE_PLAN_INPUTS)
  subscribed_services = list(NATIVE_PLAN_INPUTS)
  if slc_runtime is not None or curve_host is not None or conditional_host is not None or traffic_owner is not None or mode_owner is not None or approach_preferences is not None:
    subscribed_services.append('deviceState')
  if conditional_host is not None:
    subscribed_services.append('starpilotRadarState')
  if slc_runtime is not None:
    subscribed_services.append('slcDashboardObservation')
    if slc_vision_development:
      subscribed_services.append('slcVisionObservation')
  subscribed_services.append('starpilotNavigation')
  optional_conditional = ['starpilotNavigation'] + (['starpilotRadarState'] if conditional_host is not None else [])
  sm = messaging.SubMaster(subscribed_services, poll='modelV2',
                           ignore_alive=optional_conditional, ignore_valid=optional_conditional,
                           ignore_avg_freq=optional_conditional)

  try:
    while True:
      sm.update()
      if sm.updated['modelV2']:
        # Only explicit replay uses the recorded model timeline. In a live host,
        # modelV2 may lag newer inputs in the same SubMaster update.
        now_ns = int(sm.logMonoTime['modelV2']) if 'REPLAY' in os.environ else time.monotonic_ns()
        current_start_ns = (int(sm['deviceState'].startedMonoTime)
                            if 'deviceState' in subscribed_services and sm.valid['deviceState'] and
                            sm.alive['deviceState'] and 0 < sm.logMonoTime['deviceState'] <= now_ns else 0)
        if stop_resume_sock is not None:
          collect_resume(force_stop_owner.resume, stop_resume_sock, messaging.recv_one_or_none,
                         now_ns=now_ns, drive_id=current_start_ns,
                         receive_clock=time.monotonic_ns if 'REPLAY' not in os.environ else None)
        slc_ceiling = None
        planner_status = None
        slc_output = None
        drive_changed = current_start_ns > 0 and drive_start_ns > 0 and current_start_ns != drive_start_ns
        if slc_cruise_sock is not None:
          for _ in range(8):
            event = messaging.recv_one_or_none(slc_cruise_sock)
            if event is None:
              break
            if str(event.slcCruiseEvent.kind) == 'switchbackMode' and event.valid:
              pending_switchback.append(event)
              continue
            queue_cruise_event(event, pending_slc_cruise, pending_curve_events,
                               pending_conditional_events, pending_traffic_events)
        if drive_changed:
          pending_slc_cruise.clear()
          pending_curve_events.clear()
          pending_conditional_events.clear()
          pending_conditional_ui.clear()
          pending_traffic_events.clear()
          pending_modes.clear()
          pending_switchback.clear()
          if mode_owner is not None:
            mode_owner.reset(current_start_ns)
          if traffic_owner is not None:
            traffic_owner.reset()
        if slc_action_sock is not None:
          for _ in range(8):
            event = messaging.recv_one_or_none(slc_action_sock)
            if event is None:
              break
            queue_ui_action(event, pending_slc_actions, pending_conditional_ui, pending_modes)
        if slc_runtime is not None:
          if drive_changed or slc_runtime.state.reset_required or slc_runtime.ledger.reset_required:
            slc_runtime.reset()
            pending_slc_actions.clear()
            pending_slc_cruise.clear()
          max_event_age_ns = int(2e9 / SERVICE_LIST['modelV2'].frequency)
          while pending_slc_actions and now_ns - pending_slc_actions[0][0] > max_event_age_ns:
            pending_slc_actions.popleft()
          cruise_event = current_cruise_event(pending_slc_cruise, now_ns)
          request = (pending_slc_actions.popleft()[1] if cruise_event is None and pending_slc_actions and
                     pending_slc_actions[0][0] <= now_ns else None)
          output = slc_runtime.step(sm, CP, now_ns=now_ns, request=request, cruise_event=cruise_event)
          slc_output = output
          slc_ceiling = output.result.ceiling
          planner_status = output.message
          if output.command is not None:
            pm.send('slcCruiseCommand', output.command)
          history_write = output.result.acceptance.history_write if output.result.acceptance is not None else None
          # A camera episode has no road-location identity for a later drive.
          if history_write is not None and history_write.candidate.source != 'vision':
            params.put("SLCQualifiedHistory", json.loads(slc_history.encode(history_write, time.time_ns())))
        needs_clock = conditional_host is not None or traffic_owner is not None or force_stop_owner is not None or mode_owner is not None
        clock_pair = paired_clocks_ns() if needs_clock and 'REPLAY' not in os.environ else None
        controller_traffic_toggle = False
        if mode_owner is not None and clock_pair is not None:
          while pending_switchback:
            apply_switchback_gesture(mode_owner, pending_switchback.popleft(), params=params,
              settings=mode_settings, sm=sm, cp=CP, now_ns=clock_pair[0], now_boot_ns=clock_pair[1])
        if mode_owner is not None:
          while pending_modes:
            command = pending_modes.popleft()
            if mode_owner.update(command, sm, CP, now_ns=now_ns):
              if str(command.slcAction.kind) == 'trafficModeToggle':
                controller_traffic_toggle = not controller_traffic_toggle
        traffic_verdict = None
        traffic_mode: bool | None = False
        if traffic_owner is not None and clock_pair is not None:
          traffic_now_ns, traffic_boot_ns, _ = clock_pair
          traffic_event = current_traffic_event(pending_traffic_events, traffic_now_ns, int(sm.logMonoTime['carState']))
          if traffic_owner.controller_source and mode_owner is not None and traffic_event is not None:
            if apply_switchback_gesture(mode_owner, traffic_event, params=params, settings=mode_settings,
                sm=sm, cp=CP, now_ns=traffic_now_ns, now_boot_ns=traffic_boot_ns, mode='traffic'):
              controller_traffic_toggle = not controller_traffic_toggle
          traffic_verdict = traffic_owner.sample(
            traffic_event,
            params=params, settings=traffic_settings, sm=sm, cp=CP,
            drive_id=current_start_ns, now_mono_ns=traffic_now_ns, now_boot_ns=traffic_boot_ns,
            controller_toggle=controller_traffic_toggle)
          traffic_mode = traffic_verdict.profile_mode
        elif traffic_owner is not None:
          traffic_owner.reset()
          traffic_mode = None
        if now_ns - profile_request_ns >= 1_000_000_000 or now_ns < profile_request_ns:
          profile_request_ns = now_ns
          profile_replay = feature_enabled(params, CP, 'profile', os.environ)
          if profile_replay and profile_host is None:
            profile_host = ProfileHost(params)
        # A Traffic-only host may resolve the accepted Traffic defaults, but
        # cannot turn on ordinary saved profiles without their existing gate.
        profile_tuning = (profile_for_frame(profile_host, sm, CP, now_ns, traffic_mode=traffic_mode)
                          if profile_replay or traffic_mode is not False else None)
        # selected response supersedes the old global-only channel.
        global_braking_response = None
        selected_profiles = (profile_host.sample_selected(now_ns, sm['selfdriveState'].personality,
                              sm['carState'].vEgo, CP, traffic_mode=traffic_mode, legacy=profile_tuning)
                             if profile_replay and profile_host is not None and
                             _profile_frame_valid(sm, now_ns) else None)
        lane_change_policy = lane_gap_preferences.sample(now_ns) if lane_gap_preferences is not None else None
        lead_approach_key = lead_approach_for_frame(approach_preferences, sm, CP, now_ns)
        if curve_preferences is not None and curve_host is not None:
          curve_preferences.refresh(curve_host, now_ns)
        curve_event = current_cruise_event(pending_curve_events, now_ns)
        conditional_handoff = (conditional_handoff_for_frame(conditional_host, sm, CP, clock_pair[0], current_start_ns)
                               if clock_pair is not None else None)
        faster_lead_takeoff = takeoff_preferences.sample(now_ns) if takeoff_preferences is not None else False
        force_stop_provider = None
        if force_stop_owner is not None:
          if clock_pair is None:
            force_stop_owner.reset()
          else:
            def force_stop_provider(follow_seconds, clock_pair=clock_pair, current_start_ns=current_start_ns, traffic_mode=traffic_mode):
              return force_stop_owner.sample(sm, CP, now_ns=clock_pair[0], now_boot_ns=clock_pair[1],
                                              drive_id=current_start_ns, follow_seconds=follow_seconds,
                                              traffic_mode=traffic_mode, takeoff_enabled=faster_lead_takeoff)
        curve_result = update_curve_frame(longitudinal_planner, sm, CP, now_ns, host=curve_host,
                                          cruise_ceiling=slc_ceiling, profile_tuning=profile_tuning,
                                          traffic_mode=traffic_mode, lane_change_policy=lane_change_policy,
                                          global_braking_response=global_braking_response, selected_profiles=selected_profiles,
                                          conditional_handoff=conditional_handoff,
                                          lead_approach_key=lead_approach_key, force_stop_provider=force_stop_provider,
                                          drive_id=current_start_ns, event=curve_event, faster_lead_takeoff=faster_lead_takeoff)
        if curve_preferences is not None and curve_host is not None and curve_result is not None:
          curve_preferences.persist(curve_host, curve_result, now_ns)
          assert curve_status is not None
          curve_geometry = road_curvature(sm['modelV2'], sm['carState'].vEgo) if curve_result.candidate_mps is not None else None
          planner_status = curve_status.attach(planner_status, curve_host, curve_result, longitudinal_planner,
                                               now_ns=now_ns, model_ns=int(sm.logMonoTime['modelV2']),
                                               persistence_status=curve_preferences.status,
                                               road_curvature=curve_geometry[0] if curve_geometry is not None else None)
        if conditional_host is not None and 'REPLAY' not in os.environ:
          if drive_changed:
            conditional_host.reset()
          # A recorded BOOTTIME pair is not part of the current replay input.
          # Camera EOF cannot be used to invent one; replay remains unavailable.
          if clock_pair is not None:
            conditional_now_ns, conditional_boot_ns, conditional_skew_ns = clock_pair
            proposal, snapshot = conditional_host.sample(
              sm, CP, longitudinal_planner, now_mono_ns=conditional_now_ns, now_boot_ns=conditional_boot_ns,
              sample_skew_ns=conditional_skew_ns, drive_id=current_start_ns,
              owner_context=ConditionalOwnerContext(
                traffic_mode=ObservedBool(traffic_verdict.effective, traffic_verdict.source_mono_ns)
                if traffic_verdict is not None and traffic_verdict.effective is not None else None,
                forcing_stop=ObservedBool(longitudinal_planner.force_stop_plan.forcing, int(sm.logMonoTime['modelV2'])),
                plan_forcing_stop=ObservedBool(longitudinal_planner.force_stop_plan.forcing, int(sm.logMonoTime['modelV2']))),
              slc_runtime=slc_runtime, slc_output=slc_output,
              native_plan_valid=bool(sm.all_checks(native_plan_checks)),
              manual_event=current_manual_event(pending_conditional_events, conditional_now_ns,
                                                int(sm.logMonoTime['carState'])),
              ui_event=current_ui_manual_event(pending_conditional_ui, conditional_now_ns),
            )
            planner_status = conditional_host.status.attach(
              planner_status, proposal, snapshot, now_ns=conditional_now_ns,
              drive_id=current_start_ns, model_ns=int(sm.logMonoTime['modelV2']),
              car_state_ns=int(sm.logMonoTime['carState']),
            )
        if traffic_owner is not None:
          traffic_profile_ready, traffic_profile_reason = traffic_profile_status(
            traffic_mode, profile_tuning, longitudinal_planner.last_profile,
            getattr(profile_host, 'settings', None))
          planner_status = traffic_owner.attach(
            planner_status, traffic_verdict or TrafficVerdict(False, None, 'clock_unavailable', -1, 0, 0, '', ''),
            now_ns=now_ns, drive_id=current_start_ns,
            profile_target_ready=traffic_profile_ready,
            profile_reason=traffic_profile_reason)
        if mode_owner is not None:
          mode_sequence += 1
          planner_status = publish_switchback(planner_status,
            mode_owner.sample('switchback', sm, CP, now_ns=now_ns), session=mode_session,
            sequence=mode_sequence, now_ns=now_ns, source_car_control_ns=int(sm.logMonoTime['carControl']))
        if planner_status is not None:
          pm.send('slcState', planner_status)
        if current_start_ns > 0:
          drive_start_ns = current_start_ns
        longitudinal_planner.publish(sm, pm)

        ldw.update(sm.frame, sm['modelV2'], sm['carState'], sm['carControl'])
        msg = messaging.new_message('driverAssistance')
        msg.valid = sm.all_checks(native_plan_checks)
        msg.driverAssistance.leftLaneDeparture = ldw.left
        msg.driverAssistance.rightLaneDeparture = ldw.right
        pm.send('driverAssistance', msg)

  finally:
    if conditional_host is not None:
      conditional_host.close()
    if curve_preferences is not None:
      curve_preferences.close()

def main():
  # Manager stops plannerd offroad. Select once before constructing any planner
  # or StarPilot feature host; a saved change takes effect on the next drive.
  from openpilot.starpilot.longitudinal.planner_selection import run_selected
  return run_selected(Params(), starpilot_main)


if __name__ == "__main__":
  main()
