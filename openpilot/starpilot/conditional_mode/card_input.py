"""Card input qualification for physical conditional-mode gestures."""

from opendbc.car.structs import car
from opendbc.car.gm.distance_button import DistanceObservation
from opendbc.car.gm.profiles import profiles_supported as gm_profiles_supported
from opendbc.car.hyundai.ioniq6_media import MediaObservation
from openpilot.common.params import Params
from openpilot.starpilot.speed_limits import physical_actions as slc_physical
from openpilot.starpilot.conditional_mode.manual import Button, ButtonMap, ButtonTracker, TRAFFIC_MODE_ACTION, ioniq6_media_eligible, read_button_map
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner
from openpilot.starpilot.conditional_mode.status import settings_fingerprint


def conditional_manual_candidate(CS: car.CarState, tracker: ButtonTracker, params: Params,
                                 settings_owner: ConditionalSettingsOwner, CP: car.CarParams, sm, *,
                                 now_ns: int, explicit_aol_latch: bool = False,
                                 media: MediaObservation | None = None,
                                 media_buttons: ButtonMap | None = None, media_map_captured: bool = False):
  """Qualify one physical press after the Card's existing button arbitration."""
  ioniq_media = ioniq6_media_eligible(CP)
  gestures = tracker.observe(CS)
  if not ioniq_media or media is None:
    tracker.invalidate_media()
  if type(now_ns) is not int or now_ns <= 0:
    tracker.invalidate_media()
    return None
  if (not CP.openpilotLongitudinalControl or CP.passive or CP.dashcamOnly or CP.notCar or
      not CS.canValid or CS.canTimeout):
    tracker.invalidate_media()
    return None
  controls_ns = int(sm.logMonoTime.get('carControl', 0))
  device_ns = int(sm.logMonoTime.get('deviceState', 0))
  if (not sm.valid.get('carControl', False) or not sm.alive.get('carControl', False) or
      not sm.valid.get('deviceState', False) or not sm.alive.get('deviceState', False) or
      not 0 < controls_ns <= now_ns or now_ns - controls_ns > slc_physical.STATE_MAX_AGE_NS or
      not 0 < device_ns <= now_ns or now_ns - device_ns > 1_000_000_000 or
      not sm['carControl'].enabled or not sm['carControl'].longActive):
    tracker.invalidate_media()
    return None
  drive_id = int(sm['deviceState'].startedMonoTime)
  if not 0 < drive_id <= now_ns:
    tracker.invalidate_media()
    return None
  snapshot = settings_owner.refresh(now_ns)
  verdict = settings_owner.verdict(snapshot, now_mono_ns=now_ns, drive_id=drive_id)
  if verdict.status != 'ready' or verdict.selection is None or verdict.safe_mode is not False:
    tracker.invalidate_media()
    return None
  choice = verdict.selection.choice
  if choice not in (ModeChoice.CEM, ModeChoice.CCM) or snapshot.preferences is None:
    tracker.invalidate_media()
    return None
  fingerprint = settings_fingerprint(snapshot)
  if fingerprint is None:
    tracker.invalidate_media()
    return None
  buttons = None
  if ioniq_media and media is not None:
    if not media.valid:
      tracker.observe_media(media)
    elif media.samples:
      buttons = media_buttons if media_map_captured else read_button_map(params, include_ioniq_media=True)
      if buttons is None:
        tracker.invalidate_media()
        return None
      tracker.bind_media((drive_id, fingerprint, buttons))
      gestures = (*gestures, *tracker.observe_media(media))
  if len(gestures) != 1:
    return None
  gesture = gestures[0]
  if explicit_aol_latch and gesture.button is Button.LKAS:
    return None
  if gesture.button in (Button.LKAS, Button.DISTANCE):
    # Read the saved mapping on each physical gesture so live remaps apply without 0x448.
    buttons = read_button_map(params, include_ioniq_media=ioniq_media)
  elif buttons is None:
    buttons = media_buttons if media_map_captured and ioniq_media else read_button_map(params, include_ioniq_media=ioniq_media)
  if buttons is None or not buttons.assigned(gesture):
    return None
  return gesture, drive_id, fingerprint, choice, now_ns


def conditional_traffic_candidate(CS: car.CarState, tracker: ButtonTracker, params: Params,
                                  settings_owner: ConditionalSettingsOwner, CP: car.CarParams, sm, *,
                                  now_ns: int, media: MediaObservation | DistanceObservation | None = None,
                                  media_buttons: ButtonMap | None = None, media_map_captured: bool = False,
                                  distance: DistanceObservation | None = None, action: int = TRAFFIC_MODE_ACTION):
  """Source-backed wheel heartbeat and optional action-six proposal.

  A heartbeat is emitted only for a new physical packet. An empty cached
  observation cannot extend the planner's source lifetime.
  """
  gm_distance = gm_profiles_supported(CP) and distance is not None
  if gm_distance:
    media = distance
  if not (ioniq6_media_eligible(CP) or gm_distance) or media is None or not media.valid:
    tracker.invalidate_media()
    return None
  if (type(now_ns) is not int or now_ns <= 0 or action not in (TRAFFIC_MODE_ACTION, 7) or
      (action == TRAFFIC_MODE_ACTION and not CP.openpilotLongitudinalControl) or
      CP.passive or CP.dashcamOnly or CP.notCar or not CS.canValid or CS.canTimeout):
    tracker.invalidate_media()
    return None
  device_ns = int(sm.logMonoTime.get('deviceState', 0))
  if (not sm.valid.get('deviceState', False) or not sm.alive.get('deviceState', False) or
      not 0 < device_ns <= now_ns or now_ns - device_ns > 1_000_000_000):
    tracker.invalidate_media()
    return None
  drive_id = int(sm['deviceState'].startedMonoTime)
  if not getattr(sm['deviceState'], 'started', False) or not 0 < drive_id <= now_ns:
    tracker.invalidate_media()
    return None
  snapshot = settings_owner.refresh(now_ns)
  verdict = settings_owner.verdict(snapshot, now_mono_ns=now_ns, drive_id=drive_id)
  fingerprint = settings_fingerprint(snapshot) if verdict.status == 'ready' and verdict.safe_mode is False else None
  if fingerprint is None:
    tracker.invalidate_media()
    return None
  controls_ns = int(sm.logMonoTime.get('carControl', 0))
  authority = (sm.valid.get('carControl', False) and sm.alive.get('carControl', False) and
               0 < controls_ns <= now_ns and now_ns - controls_ns <= slc_physical.STATE_MAX_AGE_NS and
               (sm['carControl'].latActive if action == 7 else
                sm['carControl'].enabled and sm['carControl'].longActive))
  if not authority:
    tracker.invalidate_media()  # No held press can finish after authority returns.
  if not media.samples:
    # Hold the 5 Hz gesture history across 100 Hz polls only within the same authority;
    # cached samples must not become heartbeats.
    if tracker.media_context is not None and tracker.media_context[:2] != (drive_id, fingerprint):
      tracker.invalidate_media()
    return None
  buttons = media_buttons if media_map_captured else read_button_map(params, include_ioniq_media=not gm_distance)
  if buttons is None:
    tracker.invalidate_media()
    return None
  tracker.bind_media((drive_id, fingerprint, buttons))
  gestures = (tracker.observe_distance_source(distance) if gm_distance else tracker.observe(CS, media)) if authority else ()
  allowed = (Button.DISTANCE,) if gm_distance else (Button.MODE, Button.CUSTOM)
  toggles = tuple(gesture for gesture in gestures if gesture.button in allowed and
                  buttons.action(gesture) == action)
  if len(gestures) > 1 or len(toggles) > 1:
    tracker.invalidate_media()
    return None
  return (bool(toggles), toggles[0] if toggles else None, drive_id, fingerprint,
          buttons.fingerprint(), media.source_epoch, media.samples[-1].source_boot_ns, now_ns)
