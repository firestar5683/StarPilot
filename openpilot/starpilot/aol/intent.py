from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from opendbc.car.structs import car
from openpilot.cereal import log
from openpilot.selfdrive.car.cruise import CRUISE_LONG_PRESS
from openpilot.starpilot.conditional_mode.manual import Button, ButtonTracker, Press

ButtonType = car.CarState.ButtonEvent.Type
GearShifter = car.CarState.GearShifter

AOL_TOGGLE = 9
PAUSE_LATERAL = 3
PAUSE_LONGITUDINAL = 4

@dataclass(frozen=True)
class AolSettings:
  enabled: bool
  pause_brake_mps: float
  lkas_action: int
  main_action: int
  distance_actions: tuple[int, int, int]
  cancel_actions: tuple[int, int, int]
  mode_actions: tuple[int, int, int] = (0, 0, 0)
  custom_actions: tuple[int, int, int] = (0, 0, 0)


def _button_action(params, key: str) -> int:
  try:
    value = int(params.get(key, return_default=True) or '0')
  except (TypeError, ValueError):
    return 0
  return value if value in (0, PAUSE_LATERAL, PAUSE_LONGITUDINAL, AOL_TOGGLE) else 0


def read_settings(params) -> AolSettings:
  # Legacy thresholds are effectively SI despite the mph label; preserve them until replaced.
  # Read raw bytes so malformed overrides cannot silently restore AOL.
  pause_mps = 0.0
  for key in ('AolBrakePauseSpeedMps', 'PauseAOLOnBrake'):
    try:
      pause_mps = float(Path(params.get_param_path(key)).read_bytes())
    except FileNotFoundError:
      continue
    except (OSError, ValueError):
      pause_mps = float('nan')
    break
  valid_pause = 0.0 <= pause_mps <= 100.0
  return AolSettings(
    enabled=params.get_bool('AlwaysOnLateral') and valid_pause, pause_brake_mps=pause_mps if valid_pause else 0.0,
    lkas_action=_button_action(params, 'LKASButtonControl'),
    main_action=_button_action(params, 'MainCruiseButtonControl'),
    distance_actions=(_button_action(params, 'DistanceButtonControl'),
                      _button_action(params, 'LongDistanceButtonControl'),
                      _button_action(params, 'VeryLongDistanceButtonControl')),
    mode_actions=(_button_action(params, 'ModeButtonControl'), _button_action(params, 'LongModeButtonControl'),
                         _button_action(params, 'VeryLongModeButtonControl')),
    custom_actions=(_button_action(params, 'StarButtonControl'), _button_action(params, 'LongStarButtonControl'),
                         _button_action(params, 'VeryLongStarButtonControl')),
    cancel_actions=(_button_action(params, 'CancelButtonControl'),
                    _button_action(params, 'LongCancelButtonControl'),
                    _button_action(params, 'VeryLongCancelButtonControl')),
  )


def independent_axis_requested(settings: AolSettings, *, include_auxiliary: bool = False) -> bool:
  pause = (PAUSE_LATERAL, PAUSE_LONGITUDINAL)
  actions = (settings.lkas_action, settings.main_action, *settings.distance_actions)
  if include_auxiliary:
    actions += (*settings.cancel_actions, *settings.mode_actions, *settings.custom_actions)
  return settings.enabled or any(action in pause for action in actions)


def disarming_fault(events, CS) -> bool:
  """Temporary steering/known non-driving gears pause output, not driver intent."""
  if CS.steerFaultPermanent:
    return True
  for event in events:
    if event.immediateDisable:
      return True
    if event.softDisable:
      if event.name == log.OnroadEvent.EventName.steerTempUnavailable:
        continue
      if event.name == log.OnroadEvent.EventName.wrongGear and CS.gearShifter != GearShifter.unknown:
        continue
      return True
  return False


class AolCardIntent:
  def __init__(self, settings: AolSettings, *, explicit_latch: bool = False):
    self.settings = settings
    self.explicit_latch = explicit_latch
    self.allowed_latch = False
    self.pause_lateral = False
    self.pause_longitudinal = False
    self._gesture_neutral_seen = False
    self._distance_neutral_seen = False
    self._main_held = False
    self._lkas_held = False
    self._fault_inhibit = False
    self._last_latch_edge_ns = 0
    self._native_rejection_ns = 0
    self._calibration_inhibit = False
    self._calibration_fault = False
    self._calibration_rearm_required = False
    self._calibration_main = False
    self._calibration_engaged = False
    self._timers = {int(ButtonType.gapAdjustCruise): 0}
    self._held = {int(ButtonType.gapAdjustCruise): False}
    self._aux_cancel_tracker = ButtonTracker()
    self._aux_media_tracker = ButtonTracker()

  def _perform(self, action: int) -> None:
    if action == AOL_TOGGLE and self.settings.enabled and not self.explicit_latch:
      self.allowed_latch = not self.allowed_latch
      if self.allowed_latch:
        self.pause_lateral = False
    elif action == PAUSE_LATERAL:
      self.pause_lateral = not self.pause_lateral
    elif action == PAUSE_LONGITUDINAL:
      self.pause_longitudinal = not self.pause_longitudinal

  def update(self, CS, *, consumed_buttons: frozenset[int] = frozenset(), fault_active: bool | None = None,
             now_ns: int = 0, native_rejection_ns: int = 0, standard_enabled: bool = False) -> None:
    if self.explicit_latch and self._native_rejection_ns < native_rejection_ns <= now_ns:
      self._native_rejection_ns = native_rejection_ns
      if self._last_latch_edge_ns < native_rejection_ns <= now_ns:
        # Native authorization was revoked. Keep neutral/held-button history so
        # the next fresh physical press arms once, without replaying a held one.
        self.allowed_latch = False
    if self.explicit_latch and (fault_active is not None or CS.steerFaultPermanent):
      self._fault_inhibit = bool(fault_active or CS.steerFaultPermanent)
      if self._fault_inhibit:
        self.allowed_latch = False
        self._gesture_neutral_seen = False
    if not CS.canValid or CS.canTimeout:
      self.allowed_latch = False
      self._gesture_neutral_seen = False
      self._distance_neutral_seen = False
      self._main_held = False
      self._lkas_held = False
      for button in self._held:
        self._held[button] = False
        self._timers[button] = 0
      return

    if not self.settings.enabled:
      self.allowed_latch = False
      if self.explicit_latch:
        self._gesture_neutral_seen = False
      if not independent_axis_requested(self.settings, include_auxiliary=self.auxiliary_supported()):
        self.pause_lateral = False
        self.pause_longitudinal = False

    lkas_managed = self.settings.lkas_action == AOL_TOGGLE
    main_managed = self.settings.main_action == AOL_TOGGLE
    if self.explicit_latch and CS.accFaulted:
      self.allowed_latch = False
      self._gesture_neutral_seen = False
    elif self.settings.enabled and not self.explicit_latch and not lkas_managed and not main_managed:
      self.allowed_latch = bool(CS.cruiseState.available)
    elif not self.explicit_latch and not CS.cruiseState.available:
      self.allowed_latch = False

    for button in consumed_buttons:
      if button in self._held:
        self._held[button] = False
        self._timers[button] = 0

    distance_events = [event for event in CS.buttonEvents if event.type in (ButtonType.gapAdjustCruise, ButtonType.lkas)]
    if not self._distance_neutral_seen:
      self._distance_neutral_seen = not any(event.pressed for event in distance_events)

    if self.explicit_latch:
      previously_held = self._main_held or self._lkas_held
      cancel_pressed = False
      for event in CS.buttonEvents:
        button = int(event.type.raw)
        if button == int(ButtonType.mainCruise):
          self._main_held = bool(event.pressed)
        elif button == int(ButtonType.lkas):
          self._lkas_held = bool(event.pressed)
        elif button == int(ButtonType.cancel) and event.pressed:
          cancel_pressed = True
      gesture_held = self._main_held or self._lkas_held
      if not previously_held and gesture_held:
        self._last_latch_edge_ns = now_ns
      if cancel_pressed:
        self.allowed_latch = False
      elif not self._gesture_neutral_seen:
        self._gesture_neutral_seen = not gesture_held
      elif not previously_held and gesture_held and self.settings.enabled and not CS.accFaulted and not self._fault_inhibit:
        # The physical gesture owns lateral intent even while ordinary cruise
        # is engaged. Dropping only the AOL latch leaves standard steering on.
        lateral_engaged = not self.pause_lateral and (self.allowed_latch or standard_enabled)
        self.allowed_latch = not lateral_engaged
        self.pause_lateral = lateral_engaged

    for event in CS.buttonEvents:
      button = int(event.type.raw)
      if button in consumed_buttons:
        continue
      if self.explicit_latch and button in (int(ButtonType.cancel), int(ButtonType.lkas), int(ButtonType.mainCruise)):
        continue
      if button == int(ButtonType.gapAdjustCruise) and not self._distance_neutral_seen:
        continue
      if button == int(ButtonType.lkas) and event.pressed:
        self._perform(self.settings.lkas_action)
      elif button == int(ButtonType.mainCruise) and event.pressed:
        self._perform(self.settings.main_action)
      elif button in self._held:
        if event.pressed:
          self._held[button] = True
          self._timers[button] = 0
        else:
          ticks = self._timers[button]
          actions = self.settings.distance_actions if button == int(ButtonType.gapAdjustCruise) else self.settings.cancel_actions
          if 0 < ticks < CRUISE_LONG_PRESS:
            self._perform(actions[0])
          self._held[button] = False
          self._timers[button] = 0
    for button, held in self._held.items():
      if held:
        self._timers[button] += 1
        actions = self.settings.distance_actions if button == int(ButtonType.gapAdjustCruise) else self.settings.cancel_actions
        if self._timers[button] == CRUISE_LONG_PRESS:
          self._perform(actions[1])
        elif self._timers[button] == CRUISE_LONG_PRESS * 5:
          self._perform(actions[2])

  def observe_calibration(self, CS, *, events=None, standard_enabled: bool = False) -> None:
    if self.explicit_latch:
      return
    if events is not None:
      self._calibration_fault = disarming_fault(events, CS)
      self._calibration_inhibit = any(event.name in (
        log.OnroadEvent.EventName.calibrationInvalid,
        log.OnroadEvent.EventName.calibrationIncomplete,
        log.OnroadEvent.EventName.calibrationRecalibrating) for event in events)
    main = bool(CS.cruiseState.available)
    engaged = bool(CS.cruiseState.enabled or standard_enabled)
    main_derived = not self.explicit_latch and self.settings.lkas_action != AOL_TOGGLE and self.settings.main_action != AOL_TOGGLE
    if not main_derived:
      self._calibration_rearm_required = False
    fresh_edge = ((main and not self._calibration_main) or (engaged and not self._calibration_engaged))
    rearm_safe = (CS.canValid and not CS.canTimeout and not self._calibration_fault and
                  not CS.steerFaultPermanent and not CS.steerFaultTemporary and
                  CS.gearShifter not in (GearShifter.park, GearShifter.neutral, GearShifter.reverse, GearShifter.unknown))
    if self._calibration_inhibit and main_derived:
      self._calibration_rearm_required = True
    elif self._calibration_rearm_required and fresh_edge and rearm_safe and self.settings.enabled:
      self._calibration_rearm_required = False
    if self._calibration_inhibit or self._calibration_rearm_required:
      self.allowed_latch = False
    self._calibration_main = main
    self._calibration_engaged = engaged

  def auxiliary_supported(self) -> bool:
    return not self.explicit_latch

  def update_auxiliary(self, CS, *, media=None, media_eligible: bool = False, fault_active: bool | None = None) -> None:
    if (not self.auxiliary_supported() or not CS.canValid or CS.canTimeout or CS.steerFaultPermanent or
        fault_active is True or getattr(self, "_main_cycle_required", False)):
      self._aux_cancel_tracker = ButtonTracker()
      self._aux_media_tracker = ButtonTracker()
      return
    cancel = car.CarState(**CS.to_dict())
    cancel.buttonEvents = [car.CarState.ButtonEvent(type=ButtonType.gapAdjustCruise, pressed=event.pressed)
                          for event in CS.buttonEvents if event.type == ButtonType.cancel]
    for gesture in self._aux_cancel_tracker.observe(cancel.as_reader()):
      slot = (Press.SHORT, Press.LONG, Press.VERY_LONG).index(gesture.press)
      self._perform(self.settings.cancel_actions[slot])
    if not media_eligible:
      self._aux_media_tracker.invalidate_media()
      return
    for gesture in self._aux_media_tracker.observe(CS, media):
      if gesture.button not in (Button.MODE, Button.CUSTOM):
        continue
      slot = (Press.SHORT, Press.LONG, Press.VERY_LONG).index(gesture.press)
      actions = self.settings.mode_actions if gesture.button is Button.MODE else self.settings.custom_actions
      self._perform(actions[slot])

  def output(self, CS) -> tuple[bool, bool, bool]:
    driving = CS.gearShifter not in (GearShifter.neutral, GearShifter.park, GearShifter.reverse, GearShifter.unknown)
    return (self.allowed_latch and self.settings.enabled and CS.canValid and driving,
            self.pause_lateral, self.pause_longitudinal)
