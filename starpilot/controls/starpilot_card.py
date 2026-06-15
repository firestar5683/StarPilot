#!/usr/bin/env python3
from opendbc.car.chrysler.values import pacifica_hybrid_aol_requires_set_press
from opendbc.car.hyundai.values import CAR as HYUNDAI_CAR, HyundaiFlags
from opendbc.safety import ALTERNATIVE_EXPERIENCE
from openpilot.common.params import Params
from openpilot.selfdrive.car.cruise import CRUISE_LONG_PRESS, ButtonType
from openpilot.selfdrive.selfdrived.events import ET

from openpilot.starpilot.common.experimental_state import (
  CCStatus,
  CEStatus,
  next_manual_cc_status,
  next_manual_ce_status,
  sync_manual_cc_state,
  sync_manual_ce_state,
)
from openpilot.starpilot.common.favorite_slots import toggle_favorite_slot
from openpilot.starpilot.common.starpilot_utilities import is_FrogsGoMoo
from openpilot.starpilot.common.starpilot_variables import ERROR_LOGS_PATH, GearShifter, NON_DRIVING_GEARS

class StarPilotCard:
  @staticmethod
  def _button_type_raw(button_event) -> int:
    button_type = getattr(button_event, "type", button_event)
    return int(getattr(button_type, "raw", button_type))

  def __init__(self, CP, FPCP):
    self.CP = CP

    self.params = Params(return_defaults=True)
    self.params_memory = Params(memory=True)

    self.accel_pressed = False
    self.always_on_lateral_allowed = False
    hyundai_flags = getattr(self.CP, "flags", 0)
    kia_forte_non_scc = (
      getattr(self.CP, "carFingerprint", None) in (HYUNDAI_CAR.KIA_FORTE_2019_NON_SCC, HYUNDAI_CAR.KIA_FORTE_2021_NON_SCC) and
      bool(hyundai_flags & HyundaiFlags.NON_SCC)
    )
    self.hyundai_aol_needs_engagement = self.CP.brand == "hyundai" and not (hyundai_flags & HyundaiFlags.CANFD) and not kia_forte_non_scc
    self.hyundai_aol_ready = False
    self.prev_active = False
    self.prev_cruise_enabled = False
    self.decel_pressed = False
    self.cancelPressed_previously = False
    self.distancePressed_previously = False
    self.force_coast = False
    self.modePressed_previously = False
    self.mode_counter = 0
    self.customPressed_previously = False
    self.custom_counter = 0
    self.pause_lateral = False
    self.pause_longitudinal = False
    self.switchback_mode_enabled = self.params_memory.get_bool("SwitchbackModeEnabled")
    self.traffic_mode_enabled = False

    self.gap_counter = 0
    self.cancel_counter = 0
    self._distance_poll_counter = 0
    self._onroad_distance_pressed = False

    self.always_on_lateral_set = bool(FPCP.alternativeExperience & ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL)
    self.frogs_go_moo = is_FrogsGoMoo()

    self.long_press_threshold = CRUISE_LONG_PRESS
    self.very_long_press_threshold = CRUISE_LONG_PRESS * 5

    self.error_log = ERROR_LOGS_PATH / "error.txt"

  def handle_button_event(self, key, sm, starpilot_toggles):
    if sm["carControl"].longActive and getattr(starpilot_toggles, f"experimental_mode_via_{key}"):
      self.handle_experimental_mode(sm, starpilot_toggles)
    elif getattr(starpilot_toggles, f"bookmark_via_{key}"):
      self.handle_bookmark()
    elif getattr(starpilot_toggles, f"force_coast_via_{key}"):
      self.force_coast = not self.force_coast
    elif getattr(starpilot_toggles, f"pause_lateral_via_{key}"):
      self.pause_lateral = not self.pause_lateral
    elif getattr(starpilot_toggles, f"pause_longitudinal_via_{key}"):
      self.pause_longitudinal = not self.pause_longitudinal
    elif getattr(starpilot_toggles, f"switchback_mode_via_{key}"):
      self.switchback_mode_enabled = not self.switchback_mode_enabled
      self.params_memory.put_bool("SwitchbackModeEnabled", self.switchback_mode_enabled)
    elif sm["carControl"].longActive and getattr(starpilot_toggles, f"traffic_mode_via_{key}"):
      self.traffic_mode_enabled = not self.traffic_mode_enabled
    else:
      for slot_index in range(3):
        if getattr(starpilot_toggles, f"favorite_{slot_index + 1}_via_{key}", False):
          toggle_favorite_slot(slot_index, self.params, self.params_memory)
          break

  def handle_bookmark(self):
    counter = self.params_memory.get_int("WheelButtonBookmarkCounter")
    self.params_memory.put_int("WheelButtonBookmarkCounter", counter + 1)

  def handle_experimental_mode(self, sm, starpilot_toggles):
    if getattr(starpilot_toggles, "safe_mode", False):
      return

    if starpilot_toggles.conditional_experimental_mode:
      current_status = self.params_memory.get_int("CEStatus", default=CEStatus["OFF"])
      override_value = next_manual_ce_status(current_status, sm["selfdriveState"].experimentalMode)
      self.params_memory.put_int("CEStatus", override_value)
      sync_manual_ce_state(self.params, override_value)
    elif getattr(starpilot_toggles, "conditional_chill_mode", False):
      current_status = self.params_memory.get_int("CCStatus", default=CCStatus["OFF"])
      override_value = next_manual_cc_status(current_status, sm["selfdriveState"].experimentalMode)
      self.params_memory.put_int("CCStatus", override_value)
      sync_manual_cc_state(self.params, override_value)
    else:
      self.params.put_bool_nonblocking("ExperimentalMode", not sm["selfdriveState"].experimentalMode)

  def update(self, carState, starpilotCarState, sm, starpilot_toggles):
    self.switchback_mode_enabled = self.params_memory.get_bool("SwitchbackModeEnabled")
    button_event_types = [self._button_type_raw(be) for be in carState.buttonEvents]

    if self.hyundai_aol_needs_engagement:
      if carState.gearShifter in NON_DRIVING_GEARS:
        self.hyundai_aol_ready = False
        self.always_on_lateral_allowed = False
      elif sm["selfdriveState"].active or carState.cruiseState.enabled:
        self.hyundai_aol_ready = True

    if self.CP.brand == "hyundai" or starpilot_toggles.lkas_allowed_for_aol:
      for be, be_type in zip(carState.buttonEvents, button_event_types, strict=False):
        if be_type == ButtonType.lkas and be.pressed and starpilot_toggles.always_on_lateral_lkas:
          if self.hyundai_aol_needs_engagement:
            self.hyundai_aol_ready = True
          self.always_on_lateral_allowed = not self.always_on_lateral_allowed
          if carState.cruiseState.enabled or self.pause_lateral:
            self.pause_lateral = not self.always_on_lateral_allowed
        elif be_type == ButtonType.mainCruise and be.pressed:
          if starpilot_toggles.main_cruise_aol_toggle:
            if self.hyundai_aol_needs_engagement:
              self.hyundai_aol_ready = True
            self.always_on_lateral_allowed = not self.always_on_lateral_allowed
          elif starpilot_toggles.main_cruise_slc_adopt and starpilot_toggles.speed_limit_controller:
            self.params_memory.put_bool("SLCAdoptSpeedLimit", True)
    elif starpilot_toggles.always_on_lateral_main:
      if pacifica_hybrid_aol_requires_set_press(self.CP.carFingerprint, self.CP.pcmCruise):
        # Chrysler Pacifica Hybrid stock ACC can fall back to plain cruise if AOL
        # starts steering before the driver presses SET.
        if not carState.cruiseState.available:
          self.always_on_lateral_allowed = False
        elif carState.cruiseState.enabled and not self.prev_cruise_enabled:
          self.always_on_lateral_allowed = True
      else:
        self.always_on_lateral_allowed = carState.cruiseState.available

    # On rising edge of engagement (SET press enabling lat+long), auto-enable AOL
    # so that lateral persists when braking disengages longitudinal
    if sm["selfdriveState"].active and not self.prev_active and self.always_on_lateral_set and starpilot_toggles.always_on_lateral_lkas:
      if self.hyundai_aol_needs_engagement:
        self.hyundai_aol_ready = True
      self.always_on_lateral_allowed = True

    self.prev_active = sm["selfdriveState"].active
    self.prev_cruise_enabled = carState.cruiseState.enabled

    self.always_on_lateral_enabled = self.always_on_lateral_allowed and self.always_on_lateral_set
    self.always_on_lateral_enabled &= carState.gearShifter not in NON_DRIVING_GEARS
    self.always_on_lateral_enabled &= not self.hyundai_aol_needs_engagement or self.hyundai_aol_ready
    self.always_on_lateral_enabled &= sm["starpilotPlan"].lateralCheck
    self.always_on_lateral_enabled &= sm["liveCalibration"].calPerc >= 1
    self.always_on_lateral_enabled &= (ET.IMMEDIATE_DISABLE not in sm["selfdriveState"].alertType + sm["starpilotSelfdriveState"].alertType) or self.frogs_go_moo
    self.always_on_lateral_enabled &= not (carState.brakePressed and carState.vEgo < starpilot_toggles.always_on_lateral_pause_speed) or carState.standstill
    self.always_on_lateral_enabled &= not self.error_log.is_file() or self.frogs_go_moo

    if sm.updated["starpilotPlan"] or any(be_type in (ButtonType.accelCruise, ButtonType.resumeCruise) for be_type in button_event_types):
      self.accel_pressed = any(be_type in (ButtonType.accelCruise, ButtonType.resumeCruise) for be_type in button_event_types)

    if sm.updated["starpilotPlan"] or any(be_type == ButtonType.decelCruise for be_type in button_event_types):
      self.decel_pressed = any(be_type == ButtonType.decelCruise for be_type in button_event_types)

    self._distance_poll_counter += 1
    if self._distance_poll_counter >= 10:
      self._distance_poll_counter = 0
      self._onroad_distance_pressed = self.params_memory.get_bool("OnroadDistanceButtonPressed")
    starpilotCarState.distancePressed |= self._onroad_distance_pressed

    if starpilotCarState.distancePressed:
      self.gap_counter += 1
    elif not self.distancePressed_previously:
      self.gap_counter = 0

    self.distancePressed_previously = starpilotCarState.distancePressed

    if not starpilotCarState.distancePressed and 1 <= self.gap_counter < self.long_press_threshold:
      self.handle_button_event("distance", sm, starpilot_toggles)
    elif self.gap_counter == self.long_press_threshold:
      self.handle_button_event("distance_long", sm, starpilot_toggles)
    elif self.gap_counter == self.very_long_press_threshold:
      self.handle_button_event("distance_long", sm, starpilot_toggles)
      self.handle_button_event("distance_very_long", sm, starpilot_toggles)

    cancel_pressed = bool(getattr(starpilotCarState, "cancelPressed", False))
    if cancel_pressed:
      self.cancel_counter += 1
    elif not self.cancelPressed_previously:
      self.cancel_counter = 0

    self.cancelPressed_previously = cancel_pressed

    if not cancel_pressed and 1 <= self.cancel_counter < self.long_press_threshold:
      self.handle_button_event("cancel", sm, starpilot_toggles)
    elif self.cancel_counter == self.long_press_threshold:
      self.handle_button_event("cancel_long", sm, starpilot_toggles)
    elif self.cancel_counter == self.very_long_press_threshold:
      self.handle_button_event("cancel_long", sm, starpilot_toggles)
      self.handle_button_event("cancel_very_long", sm, starpilot_toggles)

    if any(be.pressed and be_type == ButtonType.lkas for be, be_type in zip(carState.buttonEvents, button_event_types, strict=False)):
      self.handle_button_event("lkas", sm, starpilot_toggles)

    if getattr(starpilot_toggles, "has_canfd_media_buttons", False):
      if starpilotCarState.modePressed:
        self.mode_counter += 1
      elif not self.modePressed_previously:
        self.mode_counter = 0
      self.modePressed_previously = starpilotCarState.modePressed

      if not starpilotCarState.modePressed and 1 <= self.mode_counter < self.long_press_threshold:
        self.handle_button_event("mode", sm, starpilot_toggles)
      elif self.mode_counter == self.long_press_threshold:
        self.handle_button_event("mode_long", sm, starpilot_toggles)
      elif self.mode_counter == self.very_long_press_threshold:
        self.handle_button_event("mode_long", sm, starpilot_toggles)
        self.handle_button_event("mode_very_long", sm, starpilot_toggles)

      if starpilotCarState.customPressed:
        self.custom_counter += 1
      elif not self.customPressed_previously:
        self.custom_counter = 0
      self.customPressed_previously = starpilotCarState.customPressed

      if not starpilotCarState.customPressed and 1 <= self.custom_counter < self.long_press_threshold:
        self.handle_button_event("star", sm, starpilot_toggles)
      elif self.custom_counter == self.long_press_threshold:
        self.handle_button_event("star_long", sm, starpilot_toggles)
      elif self.custom_counter == self.very_long_press_threshold:
        self.handle_button_event("star_long", sm, starpilot_toggles)
        self.handle_button_event("star_very_long", sm, starpilot_toggles)

    self.force_coast &= not (carState.brakePressed or carState.gasPressed)

    starpilotCarState.accelPressed = self.accel_pressed
    starpilotCarState.alwaysOnLateralAllowed = self.always_on_lateral_allowed
    starpilotCarState.alwaysOnLateralEnabled = self.always_on_lateral_enabled
    starpilotCarState.cancelLongPressed = self.very_long_press_threshold > self.cancel_counter >= self.long_press_threshold
    starpilotCarState.cancelVeryLongPressed = self.cancel_counter >= self.very_long_press_threshold
    starpilotCarState.decelPressed = self.decel_pressed
    starpilotCarState.distanceLongPressed = self.very_long_press_threshold > self.gap_counter >= self.long_press_threshold
    starpilotCarState.distanceVeryLongPressed = self.gap_counter >= self.very_long_press_threshold
    starpilotCarState.forceCoast = self.force_coast
    starpilotCarState.isParked = carState.gearShifter == GearShifter.park
    starpilotCarState.pauseLateral = self.pause_lateral
    starpilotCarState.pauseLongitudinal = self.pause_longitudinal
    starpilotCarState.trafficModeEnabled = self.traffic_mode_enabled

    return starpilotCarState
