import math
from time import monotonic_ns
from dataclasses import dataclass
import numpy as np

from opendbc.car.structs import car
from openpilot.common.constants import CV
from openpilot.starpilot.longitudinal.cruise_intervals import CruiseIntervals


# WARNING: this value was determined based on the model's training distribution,
#          model predictions above this speed can be unpredictable
# V_CRUISE's are in kph
V_CRUISE_MIN = 8
V_CRUISE_MAX = 145
V_CRUISE_UNSET = 255
V_CRUISE_INITIAL = 40
V_CRUISE_INITIAL_EXPERIMENTAL_MODE = 105
IMPERIAL_INCREMENT = round(CV.MPH_TO_KPH, 1)  # round here to avoid rounding errors incrementing set speed

ButtonEvent = car.CarState.ButtonEvent
ButtonType = car.CarState.ButtonEvent.Type
CRUISE_LONG_PRESS = 50
CRUISE_NEAREST_FUNC = {
  ButtonType.accelCruise: math.ceil,
  ButtonType.decelCruise: math.floor,
}
CRUISE_INTERVAL_SIGN = {
  ButtonType.accelCruise: +1,
  ButtonType.decelCruise: -1,
}


@dataclass(frozen=True)
class SlcPendingConfirmation:
  session_id: str
  decision_id: int
  presentation_id: int


@dataclass(frozen=True)
class SlcConsumedButton:
  pending: SlcPendingConfirmation
  button: str


class VCruiseHelper:
  def __init__(self, CP):
    self.CP = CP
    self.intervals = CruiseIntervals()
    self.v_cruise_kph = V_CRUISE_UNSET
    self.v_cruise_cluster_kph = V_CRUISE_UNSET
    self.v_cruise_kph_last = 0
    self.pending_resume_ns = 0
    self.button_timers = {ButtonType.decelCruise: 0, ButtonType.accelCruise: 0}
    self.button_change_states = {btn: {"standstill": False, "enabled": False} for btn in self.button_timers}
    # Set only by the non-PCM button path that actually changes vCruise.
    self.slc_cruise_change: tuple[float, float, str, bool] | None = None
    self.slc_consumed_button: SlcConsumedButton | None = None
    self.slc_suppressed_buttons: set[ButtonType] = set()
    self.slc_suppression_owner: dict[ButtonType, SlcPendingConfirmation] = {}
    self.slc_released_owner: dict[ButtonType, SlcPendingConfirmation] = {}
    self.slc_released_suppressed = False

  @property
  def v_cruise_initialized(self):
    return self.v_cruise_kph != V_CRUISE_UNSET

  def update_v_cruise(self, CS, enabled, is_metric, slc_pending: SlcPendingConfirmation | None = None):
    self.slc_cruise_change = None
    self.slc_consumed_button = None
    self.slc_released_suppressed = False
    self.slc_released_owner = {}
    self.v_cruise_kph_last = self.v_cruise_kph
    now_ns = monotonic_ns()
    if not CS.cruiseState.available or now_ns - self.pending_resume_ns > 500_000_000:
      self.pending_resume_ns = 0
    if not self.CP.pcmCruise:
      for button in CS.buttonEvents:
        self.pending_resume_ns = 0
        if (not enabled and CS.cruiseState.available and not button.pressed and
            button.type in (ButtonType.accelCruise, ButtonType.resumeCruise) and self.v_cruise_initialized):
          self.pending_resume_ns = now_ns

    if not self.CP.pcmCruise:
      self._update_slc_button_latches(CS, enabled, slc_pending)

    if CS.cruiseState.available:
      if not self.CP.pcmCruise:
        # if stock cruise is completely disabled, then we can use our own set speed logic
        self._update_v_cruise_non_pcm(CS, enabled, is_metric)
        self.v_cruise_cluster_kph = self.v_cruise_kph
        self.update_button_timers(CS, enabled)
      else:
        self.v_cruise_kph = CS.cruiseState.speed * CV.MS_TO_KPH
        self.v_cruise_cluster_kph = CS.cruiseState.speedCluster * CV.MS_TO_KPH
        if CS.cruiseState.speed == 0:
          self.v_cruise_kph = V_CRUISE_UNSET
          self.v_cruise_cluster_kph = V_CRUISE_UNSET
        elif CS.cruiseState.speed == -1:
          self.v_cruise_kph = -1
          self.v_cruise_cluster_kph = -1
    else:
      self.v_cruise_kph = V_CRUISE_UNSET
      self.v_cruise_cluster_kph = V_CRUISE_UNSET
      if not self.CP.pcmCruise:
        self.update_button_timers(CS, enabled)

  def _update_slc_button_latches(self, CS, enabled, slc_pending: SlcPendingConfirmation | None) -> None:
    for b in CS.buttonEvents:
      button = b.type.raw
      if button not in self.button_timers:
        continue
      if not b.pressed and button in self.slc_suppressed_buttons:
        self.slc_suppressed_buttons.remove(button)
        prior_owner = self.slc_suppression_owner.pop(button, None)
        if prior_owner is not None:
          self.slc_released_owner[button] = prior_owner
        self.slc_released_suppressed = True
      elif (b.pressed and enabled and CS.cruiseState.available and slc_pending is not None and
            button not in self.slc_suppressed_buttons):
        self.slc_suppressed_buttons.add(button)
        self.slc_suppression_owner[button] = slc_pending
        self.slc_consumed_button = SlcConsumedButton(slc_pending, 'accel' if button == ButtonType.accelCruise else 'decel')

  def _update_v_cruise_non_pcm(self, CS, enabled, is_metric):
    # handle button presses. TODO: this should be in state_control, but a decelCruise press
    # would have the effect of both enabling and changing speed is checked after the state transition
    if not enabled:
      return
    if self.slc_released_suppressed:
      return

    long_press = False
    button_type = None

    for b in CS.buttonEvents:
      if b.type.raw in self.button_timers and not b.pressed:
        if self.button_timers[b.type.raw] > CRUISE_LONG_PRESS:
          return  # end long press
        button_type = b.type.raw
        break
    else:
      for k, timer in self.button_timers.items():
        if timer and timer % CRUISE_LONG_PRESS == 0:
          button_type = k
          long_press = True
          break

    if button_type is None:
      return

    if button_type in self.slc_suppressed_buttons:
      return

    # Don't adjust speed when pressing resume to exit standstill
    cruise_standstill = self.button_change_states[button_type]["standstill"] or CS.cruiseState.standstill
    if button_type == ButtonType.accelCruise and cruise_standstill:
      return

    # Don't adjust speed if we've enabled since the button was depressed (some ports enable on rising edge)
    if not self.button_change_states[button_type]["enabled"]:
      return

    self.adjust_v_cruise(button_type, CS, is_metric, long_press=long_press)

  def adjust_v_cruise(self, button_type, CS, is_metric: bool, *, long_press: bool = False) -> bool:
    """Apply the normal software cruise step without synthesizing button events."""
    if (self.CP.pcmCruise or button_type not in (ButtonType.accelCruise, ButtonType.decelCruise) or
        not 0 < self.v_cruise_kph < V_CRUISE_UNSET or
        (button_type == ButtonType.accelCruise and CS.cruiseState.standstill)):
      return False
    v_cruise_delta = 1. if is_metric else IMPERIAL_INCREMENT
    previous_kph = self.v_cruise_kph
    interval = self.intervals.held if long_press else self.intervals.short
    v_cruise_delta = v_cruise_delta * interval
    if interval % 5 == 0 and self.v_cruise_kph % v_cruise_delta != 0:
      # partial interval
      self.v_cruise_kph = CRUISE_NEAREST_FUNC[button_type](self.v_cruise_kph / v_cruise_delta) * v_cruise_delta
    else:
      self.v_cruise_kph += v_cruise_delta * CRUISE_INTERVAL_SIGN[button_type]

    # If set is pressed while overriding, clip cruise speed to minimum of vEgo
    if CS.gasPressed and button_type in (ButtonType.decelCruise, ButtonType.setCruise):
      self.v_cruise_kph = max(self.v_cruise_kph, CS.vEgo * CV.MS_TO_KPH)

    self.v_cruise_kph = np.clip(round(self.v_cruise_kph, 1), V_CRUISE_MIN, V_CRUISE_MAX)
    if 0 < previous_kph < V_CRUISE_UNSET and self.v_cruise_kph != previous_kph:
      button = "accel" if button_type == ButtonType.accelCruise else "decel"
      self.slc_cruise_change = (float(previous_kph / 3.6), float(self.v_cruise_kph / 3.6), button, long_press)

    self.v_cruise_cluster_kph = self.v_cruise_kph
    return self.v_cruise_kph != previous_kph

  def update_button_timers(self, CS, enabled):
    # increment timer for buttons still pressed
    for k in self.button_timers:
      if self.button_timers[k] > 0:
        self.button_timers[k] += 1

    for b in CS.buttonEvents:
      if b.type.raw in self.button_timers:
        # Start/end timer and store current state on change of button pressed
        self.button_timers[b.type.raw] = 1 if b.pressed else 0
        self.button_change_states[b.type.raw] = {"standstill": CS.cruiseState.standstill, "enabled": enabled}

  def apply_slc_target(self, target_mps: float, is_metric: bool) -> None:
    """Apply a qualified planner command to the card-owned software set speed."""
    if is_metric:
      target_kph = round(target_mps * CV.MS_TO_KPH)
    else:
      target_kph = round(target_mps * CV.MS_TO_MPH) * IMPERIAL_INCREMENT
    self.v_cruise_kph = float(np.clip(target_kph, V_CRUISE_MIN, V_CRUISE_MAX))
    self.v_cruise_cluster_kph = self.v_cruise_kph

  def initialize_v_cruise(self, CS, experimental_mode: bool, *, resume: bool | None = None) -> None:
    # initializing is handled by the PCM
    if self.CP.pcmCruise:
      return

    initial = V_CRUISE_INITIAL_EXPERIMENTAL_MODE if experimental_mode else V_CRUISE_INITIAL

    # A car-owned acknowledgment can outlive the physical button event.
    if resume is None:
      age = monotonic_ns() - self.pending_resume_ns
      resume = (0 < self.pending_resume_ns and 0 <= age <= 500_000_000) or any(
        b.type in (ButtonType.accelCruise, ButtonType.resumeCruise) for b in CS.buttonEvents)
    self.pending_resume_ns = 0
    if resume and self.v_cruise_initialized:
      self.v_cruise_kph = self.v_cruise_kph_last
    else:
      self.v_cruise_kph = int(round(np.clip(CS.vEgo * CV.MS_TO_KPH, initial, V_CRUISE_MAX)))

    self.v_cruise_cluster_kph = self.v_cruise_kph
