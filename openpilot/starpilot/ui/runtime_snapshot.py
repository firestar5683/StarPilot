"""Read-only bridge from current UIState messages to immutable StarPilot views.

No message default, missing drive history, or old onroad message is presented as
an observed value. This module has no transport construction or write path.
"""

from openpilot.starpilot.ui.onroad_customization import default_document, read_customization

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
import math
import time
from typing import Any
from openpilot.starpilot.galaxy.access import AccessStatus, GalaxyAccessOwner
from openpilot.starpilot.ui.appearance_preferences import CameraViewChoice, OnroadAppearance, onroad_appearance
from openpilot.starpilot.ui.brand import DISPLAY_VERSION, home_description
from openpilot.starpilot.curve_speed.status import observation as curve_observation
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.manual import TRAFFIC_MODE_ACTION, ioniq6_media_eligible, read_button_map
from openpilot.starpilot.conditional_mode.projection import paired_clocks_ns
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner
from openpilot.starpilot.conditional_mode.status import settings_fingerprint
from openpilot.starpilot.longitudinal.profile_runtime import read_traffic_settings
from openpilot.starpilot.parked_evidence import ParkedEvidence, RESUME_SKEW_NS, fresh_offroad
from openpilot.starpilot.ui.conditional_status import ConditionalDisplayProjector, ConditionalPerceptionProjector, configured_choice
from openpilot.starpilot.ui.traffic_status import TrafficDisplayProjector
from openpilot.starpilot.controllers.mode_actions import SwitchbackStatusOwner
from openpilot.starpilot.ui.wheel_feedback import observe_wheel_feedback
from openpilot.starpilot.ui.torque_feedback import observe_torque_feedback
from openpilot.starpilot.ui.live_developer_sidebar import DeveloperMetrics

from openpilot.cereal import log
from openpilot.cereal.services import SERVICE_LIST
from opendbc.car.structs import car as car_schema
from openpilot.starpilot.ui.device_state import DeviceRequest, DeviceState
from openpilot.starpilot.ui.home_state import HomeMode, HomeState
from openpilot.starpilot.ui.onroad_state import (AlertSize, BorderSignals, ObservationKind, OnroadAlert,
                                                OnroadState, SpeedLimitObservation, speed_limit_from_message)
from openpilot.starpilot.ui.onroad_stopped_timer import StoppedTimer
from openpilot.starpilot.ui.onroad_lane_alerts import lateral_lane_alert
from openpilot.starpilot.ui.onroad_camera import ReverseDriverCamera
from openpilot.starpilot.ui.navigation_state import navigation_display
from openpilot.starpilot.ui.settings_state import Destination, DestinationAvailability, SettingsState
from openpilot.starpilot.ui.shell import ShellMode, ShellSnapshot
from openpilot.starpilot.ui.software_state import DownloadLabel, SoftwareRequest, SoftwareState
from openpilot.starpilot.ui.toggles_state import Personality, ToggleKey, TogglesState


def _boot_time_ns() -> int:
  return time.clock_gettime_ns(getattr(time, "CLOCK_BOOTTIME", time.CLOCK_MONOTONIC))


def _clock_pair(mono_clock: Callable[[], int], boot_clock: Callable[[], int]) -> tuple[int, int, int] | None:
  try:
    before = mono_clock()
    boot = boot_clock()
    after = mono_clock()
  except (OSError, RuntimeError, TypeError, ValueError, OverflowError):
    return None
  if (type(before) is not int or type(boot) is not int or type(after) is not int or
      min(before, boot, after) <= 0 or after < before or after - before > RESUME_SKEW_NS):
    return None
  return after, boot, boot - ((before + after) // 2)


def _message_at_age(sm: Any, service: str, now_ns: int, after_frame: int, max_age_ns: int,
                    *, recv_now_ns: int | None = None) -> Any | None:
  try:
    stamp = int(sm.logMonoTime[service])
    if (not sm.valid[service] or not sm.alive[service] or stamp <= 0 or stamp > now_ns or
        now_ns - stamp > max_age_ns or int(sm.recv_frame[service]) <= after_frame):
      return None
    if recv_now_ns is not None:
      receipt_age = recv_now_ns - int(sm.recv_time[service] * 1e9)
      if not 0 <= receipt_age <= max_age_ns:
        return None
    return sm[service]
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError):
    return None


def current_message(sm: Any, service: str, now_ns: int, *, after_frame: int = 0,
                    boot_now_ns: int | None = None) -> Any | None:
  """Require native transport validity, age and a post-transition receive."""
  frequency = SERVICE_LIST[service].frequency
  max_age_ns = int(2e9 / frequency) if frequency else 1_000_000_000
  if service == "pandaStates":
    if boot_now_ns is None:
      pair = _clock_pair(time.monotonic_ns, _boot_time_ns)
      if pair is None:
        return None
      boot_now_ns = now_ns + pair[2]
    return _message_at_age(sm, service, boot_now_ns, after_frame, max_age_ns, recv_now_ns=now_ns)
  return _message_at_age(sm, service, now_ns, after_frame, max_age_ns)


def display_message(sm: Any, service: str, now_ns: int, *, after_frame: int = 0) -> Any | None:
  """Allow a bounded UI frame gap without extending control-action freshness."""
  return _message_at_age(sm, service, now_ns, after_frame, 200_000_000)


def current_curve_message(sm: Any, now_ns: int, *, after_frame: int = 0) -> Any | None:
  """Read the nested Curve payload without treating SLC's Event.valid as its validity."""
  try:
    stamp = int(sm.logMonoTime["slcState"])
    frequency = SERVICE_LIST["slcState"].frequency
    max_age_ns = int(2e9 / frequency) if frequency else 1_000_000_000
    if (not sm.alive["slcState"] or stamp <= 0 or stamp > now_ns or now_ns - stamp > max_age_ns or
        int(sm.recv_frame["slcState"]) <= after_frame):
      return None
    return sm["slcState"]
  except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
    return None


def _finite(value: Any, *, positive: bool = False) -> float | None:
  try:
    number = float(value)
  except (TypeError, ValueError, OverflowError):
    return None
  if not math.isfinite(number) or (positive and number <= 0) or (not positive and number < 0):
    return None
  return number


def _model_confidence(model: Any | None) -> float | None:
  try:
    predictions = model.meta.disengagePredictions
    brake = [float(value) for value in predictions.brakeDisengageProbs]
    steer = [float(value) for value in predictions.steerOverrideProbs]
    if not brake or not steer or any(not math.isfinite(value) or not 0 <= value <= 1 for value in (*brake, *steer)):
      return None
    return (1 - max(brake)) * (1 - max(steer))
  except (AttributeError, TypeError, ValueError, OverflowError):
    return None


def _text(params: Any, key: str, fallback: str = "") -> str:
  try:
    value = params.get(key)
  except (KeyError, OSError, ValueError):
    return fallback
  if isinstance(value, bytes):
    value = value.decode("utf-8", "replace")
  return str(value) if value is not None else fallback


def _flag(params: Any, key: str) -> bool:
  try:
    return bool(params.get_bool(key))
  except (KeyError, OSError, ValueError):
    return False


def _commit_date(raw: str) -> str:
  try:
    return datetime.fromtimestamp(int(raw.strip("'").split()[0]), UTC).strftime("%b %-d")
  except (ValueError, IndexError, OverflowError, OSError):
    return ""


def _alert(message: Any | None) -> OnroadAlert:
  if message is None:
    return OnroadAlert()
  try:
    size = (AlertSize.NONE, AlertSize.SMALL, AlertSize.MID, AlertSize.FULL)[int(message.alertSize.raw)]
    return OnroadAlert(size, str(message.alertText1), str(message.alertText2), int(message.alertStatus.raw) == 2,
                       str(getattr(message, 'alertType', '')), int(message.alertStatus.raw) == 1,
                       int(getattr(getattr(message, 'alertHudVisual', 0), 'raw', getattr(message, 'alertHudVisual', 0))))
  except (AttributeError, TypeError, ValueError, IndexError):
    return OnroadAlert()


_ALERT_TRANSPORT_TIMEOUT_NS = 5_000_000_000  # Upstream selfdriveState display timeout.
_ALERT_CRITICAL_TIMEOUT_NS = 10_000_000_000


def current_alert(sm: Any, now_ns: int, *, after_frame: int) -> OnroadAlert:
  """Keep an admitted alert until an explicit clear or upstream transport timeout."""
  try:
    service = 'selfdriveState'
    stamp = int(sm.logMonoTime[service])
    receipt = int(sm.recv_time[service] * 1e9)
    if (not sm.valid[service] or int(sm.recv_frame[service]) <= after_frame or
        stamp <= 0 or stamp > now_ns or receipt <= 0 or receipt > now_ns):
      return OnroadAlert()
    missing_ns = now_ns - receipt
    if missing_ns > _ALERT_TRANSPORT_TIMEOUT_NS:
      previous = sm[service]
      if bool(previous.enabled) and missing_ns < _ALERT_TRANSPORT_TIMEOUT_NS + _ALERT_CRITICAL_TIMEOUT_NS:
        return OnroadAlert(AlertSize.FULL, 'TAKE CONTROL IMMEDIATELY', 'System Unresponsive', True)
      return OnroadAlert(AlertSize.FULL, 'System Unresponsive', 'Reboot Device', True)
    return _alert(sm[service])
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return OnroadAlert()


def _personality(raw: Any) -> Personality:
  try:
    return (Personality.AGGRESSIVE, Personality.STANDARD, Personality.RELAXED)[int(raw)]
  except (TypeError, ValueError, IndexError):
    return Personality.STANDARD


class PersonalityNotice:
  """Show one short notice for an observed onroad personality transition."""

  def __init__(self) -> None:
    self._drive_frame: int | None = None
    self._last: int | None = None
    self._until_ns = 0
    self._label = ""

  def update(self, source: Any | None, *, drive_frame: int, event_ns: int, now_ns: int,
             native_alert: OnroadAlert) -> OnroadAlert:
    try:
      personality = int(getattr(source.personality, "raw", source.personality))
      if personality not in (0, 1, 2) or event_ns <= 0 or event_ns > now_ns:
        raise ValueError("Invalid personality observation")
    except (AttributeError, TypeError, ValueError):
      self._drive_frame = None
      self._last = None
      self._until_ns = 0
      return native_alert
    if self._drive_frame != drive_frame or self._last is None or now_ns < event_ns:
      self._drive_frame = drive_frame
      self._last = personality
      self._until_ns = 0
    elif personality != self._last:
      self._last = personality
      self._label = ("Aggressive", "Standard", "Relaxed")[personality]
      self._until_ns = event_ns + 1_500_000_000
    if native_alert.size != AlertSize.NONE:
      return native_alert
    if now_ns < self._until_ns:
      return OnroadAlert(AlertSize.MID, self._label, "Driving Personality")
    return native_alert


class RuntimeSnapshotAdapter:
  """Build one coherent display snapshot after each UIState.update()."""

  def __init__(self, ui_state: Any, galaxy_access: GalaxyAccessOwner | None = None,
               bluetooth_powered: Callable[[], bool] | None = None,
               *, mono_clock: Callable[[], int] = time.monotonic_ns,
               boot_clock: Callable[[], int] = _boot_time_ns):
    self.ui_state = ui_state
    self.galaxy_access = galaxy_access
    self.bluetooth_powered = bluetooth_powered
    self._customization_value = default_document()
    self._appearance_value = OnroadAppearance()
    self._appearance_read_ns: int | None = None
    self._last_mode: ShellMode | None = None
    self._onroad_ancillary: tuple[int, tuple[bool, int, bool], ShellSnapshot] | None = None
    self._conditional = ConditionalDisplayProjector()
    self._conditional_perception = ConditionalPerceptionProjector()
    self._conditional_choice: ModeChoice | None = None
    self._conditional_read_ns: int | None = None
    self._traffic = TrafficDisplayProjector()
    self._switchback = SwitchbackStatusOwner()
    self._traffic_settings = ConditionalSettingsOwner(ui_state.params)
    self._traffic_context_ns: int | None = None
    self._traffic_map_fingerprint: str | None = None
    self._traffic_map_assigned = False
    self._traffic_profile_valid = False
    self._personality_notice = PersonalityNotice()
    self._stopped_timer = StoppedTimer()
    self._developer_metrics = DeveloperMetrics()
    self._reverse_driver_camera = ReverseDriverCamera()
    self._slc_sign_cache: tuple[int, tuple[int, int], str, SpeedLimitObservation] | None = None
    self._mono_clock, self._boot_clock = mono_clock, boot_clock
    self._device_after_mono_ns = mono_clock()
    self._device_offset_ns: int | None = None
    self._last_pair_offset_ns: int | None = None
    self._pair_failed = False

  def _parked(self, ui: Any, pair: tuple[int, int, int] | None) -> bool:
    if pair is None:
      self._device_offset_ns = None
      self._pair_failed = True
      return False
    mono_now, boot_now, offset = pair
    if self._pair_failed:
      self._device_after_mono_ns = max(self._device_after_mono_ns, mono_now)
      self._device_offset_ns = None
      self._pair_failed = False
    if self._last_pair_offset_ns is not None and abs(offset - self._last_pair_offset_ns) > RESUME_SKEW_NS:
      self._device_after_mono_ns = max(self._device_after_mono_ns, mono_now)
      self._device_offset_ns = None
    self._last_pair_offset_ns = offset
    sm = ui.sm
    try:
      if sm.updated["deviceState"] and int(sm.logMonoTime["deviceState"]) > self._device_after_mono_ns:
        self._device_offset_ns = offset
      pandas = sm["pandaStates"]
      evidence = ParkedEvidence(
        not ui.started, bool(sm.seen["deviceState"]), bool(sm.alive["deviceState"]), bool(sm.valid["deviceState"]),
        bool(sm["deviceState"].started), int(sm.logMonoTime["deviceState"]),
        int(sm.recv_time["deviceState"] * 1e9), self._device_offset_ns, self._device_after_mono_ns,
        bool(sm.seen["pandaStates"]), bool(sm.alive["pandaStates"]), bool(sm.valid["pandaStates"]),
        int(sm.logMonoTime["pandaStates"]), int(sm.recv_time["pandaStates"] * 1e9),
        tuple(bool(p.ignitionLine or p.ignitionCan) for p in pandas),
      )
      return fresh_offroad(evidence, now_mono_ns=mono_now, now_boot_ns=boot_now)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError, OSError, RuntimeError):
      return False

  def invalidate_appearance(self) -> None:
    self._appearance_read_ns = None

  def confirmed_offroad(self) -> bool:
    """Recheck transport evidence without changing presentation state."""
    return self._parked(self.ui_state, _clock_pair(self._mono_clock, self._boot_clock))

  def connectivity_allowed(self) -> bool:
    """Fresh effective offroad admission for connectivity setup, regardless of ignition."""
    return self.confirmed_offroad()

  def build(self, mode: ShellMode, selected: Destination = Destination.STAR, *, compact_y: float = 0,
            compact_scroll_x: float = 0, sidebar_expanded: bool = True, now_ns: int | None = None,
            menu_only: bool = False) -> ShellSnapshot:
    now_ns = time.monotonic_ns() if now_ns is None else now_ns
    if mode != ShellMode.ONROAD or self._last_mode != ShellMode.ONROAD:
      self._onroad_ancillary = None
    if mode == ShellMode.ONROAD and self._last_mode == ShellMode.SETTINGS:
      self.invalidate_appearance()
      self._conditional_read_ns = None
    self._last_mode = mode
    if (self._appearance_read_ns is None or now_ns < self._appearance_read_ns or
        now_ns - self._appearance_read_ns >= 1_000_000_000):
      self._customization_value = read_customization(self.ui_state.params)
      self._appearance_value = onroad_appearance(self.ui_state.params)
      self._appearance_read_ns = now_ns
    ui, params = self.ui_state, self.ui_state.params
    if (self._conditional_read_ns is None or now_ns < self._conditional_read_ns or
        now_ns - self._conditional_read_ns >= 1_000_000_000):
      self._conditional_choice = configured_choice(params)
      self._conditional_read_ns = now_ns
    sm = ui.sm
    device = current_message(sm, "deviceState", now_ns)
    pair = _clock_pair(self._mono_clock, self._boot_clock)
    pandas = current_message(sm, "pandaStates", now_ns, boot_now_ns=now_ns + pair[2]) if pair is not None else None
    panda_connected = bool(pandas and any(p.pandaType != log.PandaState.PandaType.unknown for p in pandas))
    # UIState owns drive transitions. Health-message freshness governs actions,
    # not the lifetime of the camera, widget filters, and engagement animations.
    started = bool(ui.started)
    confirmed_offroad = self._parked(ui, pair)
    after = ui.started_frame if ui.started else 0
    drive_id = int(getattr(sm["deviceState"], "startedMonoTime", 0)) if started else 0
    car = current_message(sm, "carState", now_ns, after_frame=after) if started else None
    control = current_message(sm, "carControl", now_ns, after_frame=after) if started else None
    controls = current_message(sm, "controlsState", now_ns, after_frame=after) if started else None
    selfdrive = current_message(sm, "selfdriveState", now_ns, after_frame=after) if started else None
    display_car = display_message(sm, "carState", now_ns, after_frame=after) if started else None
    display_control = display_message(sm, "carControl", now_ns, after_frame=after) if started else None
    display_controls = display_message(sm, "controlsState", now_ns, after_frame=after) if started else None
    display_selfdrive = display_message(sm, "selfdriveState", now_ns, after_frame=after) if started else None
    display_model = display_message(sm, "modelV2", now_ns, after_frame=after) if started else None
    display_radar = display_message(sm, "radarState", now_ns, after_frame=after) if started else None
    native_alert = current_alert(sm, now_ns, after_frame=after) if started else OnroadAlert()
    native_alert = lateral_lane_alert(native_alert, car=display_car, control=display_control,
                                      model=display_model, selfdrive=display_selfdrive)
    alert = self._personality_notice.update(
      display_selfdrive, drive_frame=after, event_ns=int(sm.logMonoTime['selfdriveState']) if display_selfdrive is not None else 0,
      now_ns=now_ns, native_alert=native_alert)
    slc = display_message(sm, "slcState", now_ns, after_frame=after) if started else None
    curve_envelope = current_curve_message(sm, now_ns, after_frame=after) if started else None
    curve = curve_observation(curve_envelope, now_ns) if curve_envelope is not None else None
    conditional_envelope = display_message(sm, 'starpilotSelfdriveState', now_ns, after_frame=after) if started else None

    from openpilot.starpilot.navigation.wire import navigation_state
    navigation = navigation_state(_message_at_age(sm, "starpilotNavigation", now_ns, after, 3_000_000_000)) if started else None

    long_active = bool(control.longActive) if control is not None else False
    system_long = bool(long_active and controls is not None and str(controls.longControlState) != "off" and
                       selfdrive is not None and selfdrive.enabled and car is not None and
                       bool(getattr(car, "canValid", False)) and not getattr(car, "canTimeout", True) and ui.CP is not None and
                       ui.CP.openpilotLongitudinalControl)
    raw_speed = None if display_car is None else _finite(display_car.vEgoCluster)
    if raw_speed is None or raw_speed == 0:
      raw_speed = None if display_car is None else _finite(display_car.vEgo)
    display_car_valid = bool(display_car is not None and getattr(display_car, "canValid", False) and
                             not getattr(display_car, "canTimeout", True))
    timer_car_fresh = False
    timer_standstill = False
    timer_reverse = False
    reverse_source_fresh = False
    if display_car_valid:
      try:
        gear = display_car.gearShifter
        timer_reverse = gear == car_schema.CarState.GearShifter.reverse or str(gear).split(".")[-1].lower() == "reverse"
        reverse_source_fresh = True
      except (AttributeError, TypeError, ValueError):
        pass
      try:
        timer_standstill = display_car.standstill
        timer_car_fresh = type(timer_standstill) is bool and reverse_source_fresh
      except (AttributeError, TypeError, ValueError):
        pass
    drive_key = (int(after), drive_id) if started else None
    reverse_driver_camera = self._reverse_driver_camera.step(
      now_ns=now_ns, drive_key=drive_key,
      enabled=self._appearance_value.driver_camera_on_reverse and self._appearance_value.camera_view != CameraViewChoice.NONE,
      car_fresh=reverse_source_fresh, reverse=timer_reverse,
    )
    stopped_duration = self._stopped_timer.step(
      now_ns=now_ns,
      drive_key=drive_key,
      car_fresh=timer_car_fresh, standstill=timer_standstill, reverse=timer_reverse,
      enabled=self._appearance_value.show_stopped_timer,
    )
    border_signals = (BorderSignals(bool(getattr(display_car, 'leftBlinker', False)),
                                    bool(getattr(display_car, 'rightBlinker', False)),
                                    bool(getattr(display_car, 'leftBlindspot', False)),
                                    bool(getattr(display_car, 'rightBlindspot', False))) if display_car_valid else None)
    cp = ui.CP
    traffic = None
    traffic_envelope = current_curve_message(sm, now_ns, after_frame=after) if started else None
    traffic_wire = getattr(traffic_envelope, 'trafficMode', None)
    traffic_eligible = False
    if getattr(traffic_wire, 'version', 0) == 1 and cp is not None:
      try:
        traffic_eligible = bool(ioniq6_media_eligible(cp) and cp.openpilotLongitudinalControl and not cp.passive)
      except (AttributeError, TypeError, ValueError):
        pass  # A partial or unreadable CP never qualifies a display receipt.
    if traffic_eligible:
      if (self._traffic_context_ns is None or now_ns < self._traffic_context_ns or
          now_ns - self._traffic_context_ns >= 1_000_000_000):
        buttons = read_button_map(params, include_ioniq_media=True)
        self._traffic_map_fingerprint = buttons.fingerprint() if buttons is not None else None
        self._traffic_map_assigned = bool(buttons is not None and TRAFFIC_MODE_ACTION in
                                          (buttons.mode, buttons.mode_long, buttons.mode_very_long,
                                           buttons.custom, buttons.custom_long, buttons.custom_very_long))
        try:
          self._traffic_profile_valid = read_traffic_settings(params).valid
        except (AttributeError, OSError, TypeError, ValueError):
          self._traffic_profile_valid = False
        self._traffic_context_ns = now_ns
      pair = paired_clocks_ns()
      if pair is not None and abs(pair[0] - now_ns) <= 10_000_000:
        fingerprint = settings_fingerprint(self._traffic_settings.refresh(now_ns))
        traffic = self._traffic.project(
          traffic_envelope, now_mono_ns=now_ns, now_boot_ns=pair[1],
          drive_id=drive_id,
          settings_fingerprint=fingerprint, map_fingerprint=self._traffic_map_fingerprint,
          map_assigned=self._traffic_map_assigned,
          profile_valid=self._traffic_profile_valid, long_active=bool(display_control is not None and display_control.longActive),
          selfdrive_enabled=bool(display_selfdrive is not None and getattr(display_selfdrive, 'enabled', False)),
          car_valid=display_car_valid, system_long=bool(cp.openpilotLongitudinalControl and not cp.passive),
        )
    elif not started or traffic_wire is not None and getattr(traffic_wire, 'version', 0) == 1:
      self._traffic.reset()
    conditional = self._conditional.project(
      conditional_envelope, now_ns=now_ns,
      event_ns=int(sm.logMonoTime['starpilotSelfdriveState']) if conditional_envelope is not None else 0,
      selfdrive_ns=int(sm.logMonoTime['selfdriveState']) if display_selfdrive is not None else 0,
      drive_id=drive_id,
      selfdrive_experimental=bool(display_selfdrive.experimentalMode) if display_selfdrive is not None else False,
      selfdrive_enabled=bool(getattr(display_selfdrive, 'enabled', False)) if display_selfdrive is not None else False,
      long_active=bool(display_control is not None and display_control.longActive), car_valid=display_car_valid,
      system_long=bool(cp is not None and getattr(cp, 'openpilotLongitudinalControl', False) and
                       not getattr(cp, 'passive', False)),
    )
    perception = self._conditional_perception.project(
      curve_envelope, now_ns=now_ns, event_ns=int(sm.logMonoTime['slcState']) if curve_envelope is not None else 0,
      drive_id=drive_id, choice=self._conditional_choice,
      lateral_active=bool(display_control is not None and display_control.latActive),
      selfdrive_enabled=bool(display_selfdrive is not None and getattr(display_selfdrive, 'enabled', False)),
      car_valid=display_car_valid,
      system_long=bool(cp is not None and getattr(cp, "openpilotLongitudinalControl", False) and not getattr(cp, "passive", False)),
    )
    if not display_car_valid:
      curve = None
    cluster_cruise = _finite(display_car.vCruiseCluster) if display_car_valid else None
    cruise = cluster_cruise if cluster_cruise is not None and cluster_cruise > 0 else None
    if cluster_cruise == 0 and display_controls is not None:
      cruise = _finite(getattr(display_controls, "vCruiseDEPRECATED", None), positive=True)
    if cruise is not None and cruise >= 255:
      cruise = None
    stock_cruise = bool(display_car_valid and
                        bool(getattr(getattr(display_car, "cruiseState", None), "enabled", False)) and
                        cp is not None and (not cp.openpilotLongitudinalControl or cp.pcmCruise))
    observation = speed_limit_from_message(slc) if slc is not None and (slc.enabled or slc.displayOnly) else SpeedLimitObservation()
    if slc is None and started:
      observation = SpeedLimitObservation(kind=ObservationKind.STALE)
    if mode != ShellMode.ONROAD or drive_key is None:
      self._slc_sign_cache = None
    elif observation.kind == ObservationKind.VALID and slc is not None:
      if (observation.pending_speed_limit_mps is None and not observation.decision_id and
          not bool(getattr(slc, 'hasPending', False))):
        self._slc_sign_cache = (int(sm.logMonoTime['slcState']), drive_key,
                                observation.session_id or '', observation)
      else:
        self._slc_sign_cache = None
    elif observation.kind == ObservationKind.UNKNOWN and slc is not None and self._slc_sign_cache is not None:
      stamp, previous_drive, session, previous = self._slc_sign_cache
      if (previous_drive == drive_key and session and session == str(getattr(slc, 'sessionId', '')) and
          str(getattr(slc, 'observationKind', '')) == 'unknown' and str(getattr(slc, 'source', '')) == 'none' and
          0 <= now_ns - stamp <= 150_000_000 and not bool(getattr(slc, 'hasPending', False)) and
          not getattr(slc, 'decisionId', 0)):
        observation = SpeedLimitObservation(kind=ObservationKind.VALID, source=previous.source,
                                            speed_limit_mps=previous.speed_limit_mps,
                                            offset_mps=previous.offset_mps, status='display_hold')
      else:
        self._slc_sign_cache = None
    else:
      self._slc_sign_cache = None
    experimental = bool(display_selfdrive.experimentalMode) if display_selfdrive is not None else _flag(params, "ExperimentalMode")
    observed_experimental = bool(display_selfdrive.experimentalMode) if display_selfdrive is not None else False
    persona = _personality(_text(params, "LongitudinalPersonality", "1"))
    torque = observe_torque_feedback(
      display_car, display_control, display_controls,
      display_message(sm, "carOutput", now_ns, after_frame=after) if started else None,
      display_message(sm, "vehicleParameters", now_ns, after_frame=after) if started else None, cp,
    )
    display_lat_active = bool(display_control.latActive) if display_control is not None else False
    display_long_active = bool(display_control.longActive) if display_control is not None else False
    longitudinal_overridden = bool(
      display_car_valid and getattr(display_car, 'gasPressed', False) and
      display_selfdrive is not None and getattr(display_selfdrive, 'enabled', False) and
      str(getattr(display_selfdrive, 'state', '')) == 'overriding' and
      cp is not None and cp.openpilotLongitudinalControl)
    developer_metrics = self._developer_metrics.observe(
      drive=after if started else None, car=display_car if display_car_valid else None,
      delay=current_message(sm, 'lateralDelay', now_ns, after_frame=after) if started else None,
      torque=current_message(sm, 'lateralTorqueParameters', now_ns, after_frame=after) if started else None,
      parameters=display_message(sm, 'vehicleParameters', now_ns, after_frame=after) if started else None,
      metric=bool(ui.is_metric), cp=cp)
    onroad = OnroadState(developer_metrics=developer_metrics,
                         engaged=display_lat_active or display_long_active or longitudinal_overridden, camera_available=started,
                         speed_mps=raw_speed, cruise_kph=cruise, speed_limit=observation,
                         appearance=self._appearance_value, customization=self._customization_value,
                         alert=alert, metric=bool(ui.is_metric),
                         experimental_available=bool(ui.has_longitudinal_control),
                         experimental_enabled=observed_experimental,
                         personality=list(Personality).index(persona),
                         switchback_mode=bool(cp is not None and ioniq6_media_eligible(cp) and display_control is not None and display_control.latActive and
                           self._switchback.sample(slc, drive_id=drive_id, now_ns=now_ns,
                             event_ns=int(sm.logMonoTime['slcState']))),
                         traffic_mode=bool(traffic is not None and traffic.state == 'active'),
                         traffic_display=traffic,
                         torque_utilization=torque.utilization if torque.utilization is not None else 0.0,
                         torque_source_available=torque.utilization is not None,
                         torque_drive_frame=after if started else None, drive_frame=after if started else None, observed_ns=now_ns,
                         wheel_feedback=observe_wheel_feedback(display_car, display_control),
                         lateral_active=display_lat_active, longitudinal_active=display_long_active,
                         longitudinal_overridden=longitudinal_overridden,
                         stock_cruise_active=stock_cruise,
                         slc_system_long_available=system_long,
                         curve=curve, show_curve_status=_flag(params, "ShowCSCStatus"),
                         conditional_configured=self._conditional_choice, conditional_effective=conditional,
                         conditional_perception=perception,
                         navigation=navigation_display(navigation, now_ns=now_ns, drive_id=drive_id),
                         border_signals=border_signals, stopped_duration_s=stopped_duration,
                         reverse_driver_camera=reverse_driver_camera,
                         reversing=bool(reverse_source_fresh and timer_reverse),
                         stock_confidence_source_fresh=display_model is not None,
                         stock_confidence_source_stamp_ns=int(sm.logMonoTime["modelV2"]) if display_model is not None else None,
                         stock_confidence_drive_frame=after if started else None,
                         model_confidence=_model_confidence(display_model),
                         lead_indicator_source_fresh=display_model is not None and display_radar is not None)

    ancillary_key = (bool(ui.started), int(ui.started_frame), confirmed_offroad)
    if mode == ShellMode.ONROAD and self._onroad_ancillary is not None:
      stamp, key, previous = self._onroad_ancillary
      if key == ancillary_key and 0 <= now_ns - stamp < 1_000_000_000:
        return replace(previous, onroad=onroad)

    network = "none"
    strength = 0
    connection = "UNKNOWN"
    if device is not None:
      network = {1: "wifi", 2: "cell2G", 3: "cell3G", 4: "cell4G", 5: "cell5G", 6: "ethernet"}.get(
        int(device.networkType.raw), "none")
      raw_strength = int(device.networkStrength.raw)
      strength = max(0, min(5, raw_strength + 1)) if raw_strength > 0 else 0
      ping = int(device.lastAthenaPingTime)
      connection = "ONLINE" if 0 < ping <= now_ns and now_ns - ping < 80_000_000_000 else "OFFLINE"
    try:
      bluetooth = self.bluetooth_powered() is True if mode == ShellMode.HOME and self.bluetooth_powered is not None else False
    except (OSError, RuntimeError, ValueError):
      bluetooth = False
    gpu_present = bool(device is not None and getattr(device, "chestnutPresent", False) and
                       not getattr(ui, "usb_unknown", False))
    gpu_active = bool(gpu_present and getattr(getattr(ui, "chestnut_state", None), "value", None) == "active")
    home = HomeState(version=DISPLAY_VERSION, commit=_text(params, "GitCommit"),
                     commit_date=_commit_date(_text(params, "GitCommitDate")),
                     model_label="",
                     description=home_description(_text(params, "UpdaterCurrentDescription")),
                     mode=(HomeMode.CONDITIONAL_EXPERIMENTAL if self._conditional_choice is ModeChoice.CEM else
                           HomeMode.CONDITIONAL_CHILL if self._conditional_choice is ModeChoice.CCM else
                           HomeMode.EXPERIMENTAL if experimental else HomeMode.CHILL),
                     experimental_enabled=experimental, experimental_available=bool(ui.has_longitudinal_control),
                     stats=None, paired=bool(ui.prime_state.is_paired()), network=network, network_strength=strength,
                     vehicle_online=panda_connected, connection=connection,
                     recording_audio=bool(ui.recording_audio), bluetooth=bluetooth,
                     gpu_present=gpu_present, gpu_active=gpu_active, branch=_text(params, "GitBranch"),
                     gpu_state=getattr(getattr(ui, "chestnut_state", None), "value", "disconnected"))

    settings_pages = (Destination.STAR, Destination.DEVICE, Destination.NETWORK, Destination.SOFTWARE, Destination.TOGGLES,
                      Destination.DRIVING_CONTROLS, Destination.SOUNDS, Destination.APPEARANCE,
                      Destination.SYSTEM, Destination.DRIVING_MODEL, Destination.BLUETOOTH, Destination.DEVELOPER, Destination.VEHICLE)
    availability = tuple(DestinationAvailability(item, item in settings_pages,
                          "Manage network connections" if item == Destination.NETWORK else
                          "Manage Bluetooth devices" if item == Destination.BLUETOOTH else
                          ("Available With the Vehicle Off" if confirmed_offroad else "Offroad state is unavailable")) for item in Destination)
    settings = SettingsState(sidebar_expanded=sidebar_expanded, compact_y=compact_y,
                             compact_scroll_x=compact_scroll_x, paired=bool(ui.prime_state.is_paired()),
                             availability=availability)
    if mode != ShellMode.SETTINGS:
      selected = Destination.STAR
    if selected not in settings_pages:
      selected = Destination.STAR
    # Home and the compact menu consume no leaf-panel state. Keep temporal,
    # pairing and parked evidence current without reading unused preferences.
    if mode == ShellMode.HOME or menu_only and mode == ShellMode.SETTINGS:
      return ShellSnapshot(mode, home, settings, onroad, DeviceState(offroad=confirmed_offroad), selected=selected)

    device_actions = {DeviceRequest.PREVIEW_DRIVER_CAMERA, DeviceRequest.RESET_CALIBRATION} if confirmed_offroad else set()
    galaxy_status = self.galaxy_access.status().status if self.galaxy_access is not None else AccessStatus.UNAVAILABLE
    if self.galaxy_access is not None:
      device_actions.add(DeviceRequest.OPEN_GALAXY)
    device_state = DeviceState(dongle_id=_text(params, "DongleId", "N/A"),
                               serial=_text(params, "HardwareSerial", "N/A"),
                               galaxy_paired=None,
                               galaxy_configured=(galaxy_status == AccessStatus.CONFIGURED_LOCAL if galaxy_status != AccessStatus.UNAVAILABLE else None),
                               galaxy_status=galaxy_status, galaxy_local_only=self.galaxy_access is not None,
                               offroad=confirmed_offroad,
                               available_actions=frozenset(device_actions))
    updater_state = _text(params, "UpdaterState")
    available = _flag(params, "UpdaterFetchAvailable")
    status = "updater status unavailable" if not updater_state else updater_state if updater_state != "idle" else (
      "update available" if available else "up to date, last checked " + ("previously" if _text(params, "LastUpdateTime") else "never"))
    software_actions: set[SoftwareRequest] = set()
    if confirmed_offroad:
      software_actions.add(SoftwareRequest.OPEN_UNINSTALL_CONFIRMATION)
      if updater_state == "idle":
        software_actions.update((SoftwareRequest.FAST_UPDATE, SoftwareRequest.ROLLBACK))
        software_actions.add(SoftwareRequest.DOWNLOAD_UPDATE if available else SoftwareRequest.CHECK_FOR_UPDATES)
      if not _flag(params, "IsTestedBranch") and _text(params, "UpdaterAvailableBranches"):
        software_actions.add(SoftwareRequest.OPEN_BRANCH_CHOOSER)
    software = SoftwareState(current_version=_text(params, "UpdaterCurrentDescription"),
                             automatic_updates=(None if _text(params, "DisableUpdates") == "" else
                                                not _flag(params, "DisableUpdates")),
                             download_status=status,
                             download_label=DownloadLabel.DOWNLOAD if available and updater_state == "idle" else DownloadLabel.CHECK,
                             target_branch=_text(params, "UpdaterTargetBranch"),
                             available_actions=frozenset(software_actions))
    toggles = TogglesState(enabled=_flag(params, "OpenpilotEnabledToggle"),
                           experimental=experimental, disengage_accelerator=_flag(params, "DisengageOnAccelerator"),
                           lane_departure=_flag(params, "IsLdwEnabled"),
                           always_on_dm=_flag(params, "AlwaysOnDM"), record_front=_flag(params, "RecordFront"),
                           record_audio=_flag(params, "RecordAudio"), metric=bool(ui.is_metric), personality=persona,
                           unavailable=frozenset((ToggleKey.SAFE_MODE, ToggleKey.RIGHT_HAND_DRIVING)))
    snapshot = ShellSnapshot(mode, home, settings, onroad, device_state, software, toggles, selected)
    if mode == ShellMode.ONROAD:
      self._onroad_ancillary = (now_ns, ancillary_key, snapshot)
    return snapshot
