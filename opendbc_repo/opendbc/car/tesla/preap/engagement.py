from opendbc.car import structs
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.tesla.preap.buttons import CruiseButtons

ButtonType = structs.CarState.ButtonEvent.Type


class PreAPEngagement:
  def __init__(self, double_pull_enabled: bool, double_pull_window_ms: int):
    self.enableDoublePull = double_pull_enabled
    self.double_pull_window_ms = double_pull_window_ms
    self.cruiseEnabled = False
    self.lateralEnabled = False
    self.lateralRearmRequired = False
    self.enableLongControl = False
    self.enableJustCC = False
    self.pending_enable = False
    self.stalk_pull_time_ms = 0
    self.prev_stalk_pull_time_ms = -1000
    self.pedal_speed_kph = 0.0
    self.preap_cc_cancel_needed = False
    self.preap_cc_engage_needed = False
    self.preap_last_cc_spoof_ms = 0
    self.preap_brake_pressed_prev = False
    self.last_stalk_non_cancel_ms = -10000
    self.prev_steering_disengage = False

  def handle_steering_disengage(self, steering_disengage: bool) -> None:
    if steering_disengage and not self.prev_steering_disengage:
      self.lateralEnabled = False
      self.lateralRearmRequired = True
      self.cruiseEnabled = False
      self.enableLongControl = False
      self.enableJustCC = False
      self.pending_enable = False
      self.pedal_speed_kph = 0.0
      self.stalk_pull_time_ms = 0
      self.prev_stalk_pull_time_ms = -1000
    self.prev_steering_disengage = steering_disengage

  def process_buttons(self, cruise_buttons: int, prev_cruise_buttons: int, curr_time_ms: int, v_ego: float, speed_units: str,
                      use_pedal: bool, pedal_long_allowed: bool, long_control_allowed: bool, real_brake_pressed: bool,
                      di_cruise_state: str = "OFF") -> list[structs.CarState.ButtonEvent]:
    self.preap_cc_cancel_needed = False
    self.preap_cc_engage_needed = False
    button_events: list[structs.CarState.ButtonEvent] = []

    if cruise_buttons == CruiseButtons.MAIN and prev_cruise_buttons != CruiseButtons.MAIN:
      self.lateralEnabled = True
      self.lateralRearmRequired = False
      if self.enableDoublePull:
        self._handle_double_pull(curr_time_ms, v_ego, speed_units, use_pedal, pedal_long_allowed, long_control_allowed, di_cruise_state)
      else:
        self.cruiseEnabled = True
        self.enableLongControl = long_control_allowed
        self.enableJustCC = not long_control_allowed
        self.pedal_speed_kph = self._capture_target_speed(v_ego, speed_units) if pedal_long_allowed else 0.0
        if not use_pedal and di_cruise_state == "STANDBY":
          self.preap_cc_engage_needed = True
          self.preap_last_cc_spoof_ms = curr_time_ms

    if cruise_buttons != prev_cruise_buttons:
      button_events.append(self._make_button_event(cruise_buttons, prev_cruise_buttons, curr_time_ms, v_ego, speed_units, use_pedal))

    if self.pending_enable and (curr_time_ms - self.stalk_pull_time_ms > self.double_pull_window_ms):
      self.pending_enable = False

    brake_rising_edge = real_brake_pressed and not self.preap_brake_pressed_prev
    if use_pedal and brake_rising_edge and self.cruiseEnabled and self.enableLongControl:
      self.enableLongControl = False
      self.enableJustCC = True
      self.pending_enable = False
      self.pedal_speed_kph = 0.0
    self.preap_brake_pressed_prev = real_brake_pressed

    return button_events

  def check_can_engage(self, door_open: bool, gear_shifter, seatbelt_unlatched: bool) -> bool:
    can_engage = not door_open and gear_shifter == structs.CarState.GearShifter.drive and not seatbelt_unlatched
    if not can_engage:
      self.lateralEnabled = False
      self.lateralRearmRequired = True
      self.cruiseEnabled = False
      self.enableLongControl = False
      self.enableJustCC = False
      self.pending_enable = False
    return can_engage

  def _handle_double_pull(self, curr_time_ms: int, v_ego: float, speed_units: str, use_pedal: bool,
                          pedal_long_allowed: bool, long_control_allowed: bool, di_cruise_state: str) -> None:
    self.prev_stalk_pull_time_ms = self.stalk_pull_time_ms
    self.stalk_pull_time_ms = curr_time_ms
    double_pull = (self.stalk_pull_time_ms - self.prev_stalk_pull_time_ms) < self.double_pull_window_ms

    self.cruiseEnabled = True
    self.pending_enable = False
    self.enableLongControl = long_control_allowed if double_pull else False
    self.enableJustCC = not self.enableLongControl
    self.pedal_speed_kph = self._capture_target_speed(v_ego, speed_units) if pedal_long_allowed and double_pull else 0.0

    if double_pull:
      if not use_pedal:
        self.preap_cc_engage_needed = True
        self.preap_last_cc_spoof_ms = curr_time_ms
    else:
      self.pending_enable = True
      if not use_pedal:
        self.preap_cc_cancel_needed = True
        self.preap_last_cc_spoof_ms = curr_time_ms

  def _make_button_event(self, cruise_buttons: int, prev_cruise_buttons: int, curr_time_ms: int,
                         v_ego: float, speed_units: str, use_pedal: bool) -> structs.CarState.ButtonEvent:
    be = structs.CarState.ButtonEvent()
    be.pressed = cruise_buttons != CruiseButtons.IDLE
    state = cruise_buttons if be.pressed else prev_cruise_buttons

    if state == CruiseButtons.MAIN:
      be.type = ButtonType.setCruise
      if be.pressed:
        self.last_stalk_non_cancel_ms = curr_time_ms
    elif state == CruiseButtons.CANCEL:
      be.type = ButtonType.cancel
      self.lateralEnabled = False
      self.lateralRearmRequired = True
      self.cruiseEnabled = False
      self.enableLongControl = False
      self.enableJustCC = False
      self.pending_enable = False
      self.pedal_speed_kph = 0.0
      self.stalk_pull_time_ms = 0
      self.prev_stalk_pull_time_ms = -1000
    elif CruiseButtons.is_accel(state):
      be.type = ButtonType.accelCruise
      if be.pressed and use_pedal and self.enableLongControl:
        speed_uom_kph = CV.MPH_TO_KPH if speed_units == "MPH" else 1.0
        actual_kph = int(v_ego * CV.MS_TO_KPH / speed_uom_kph + 0.5) * speed_uom_kph
        self.pedal_speed_kph = min(max(self.pedal_speed_kph, actual_kph) +
                                   (5 * speed_uom_kph if state == CruiseButtons.RES_ACCEL_2ND else speed_uom_kph), 270.0)
    elif CruiseButtons.is_decel(state):
      be.type = ButtonType.decelCruise
      if be.pressed and use_pedal and self.enableLongControl:
        speed_uom_kph = CV.MPH_TO_KPH if speed_units == "MPH" else 1.0
        self.pedal_speed_kph = max(self.pedal_speed_kph - (5 * speed_uom_kph if state == CruiseButtons.DECEL_2ND else speed_uom_kph), 0.0)
    else:
      be.type = ButtonType.unknown

    return be

  @staticmethod
  def _capture_target_speed(v_ego: float, speed_units: str) -> float:
    speed_uom_kph = CV.MPH_TO_KPH if speed_units == "MPH" else 1.0
    return max(int(v_ego * CV.MS_TO_KPH / speed_uom_kph + 0.5) * speed_uom_kph, 0.0)
