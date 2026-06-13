from cereal import car
from opendbc.car import apply_hysteresis
from openpilot.common.constants import CV
from openpilot.common.realtime import DT_CTRL

ButtonType = car.CarState.ButtonEvent.Type

SEND_BUTTON_NONE = 0
SEND_BUTTON_INCREASE = 1
SEND_BUTTON_DECREASE = 2

HYST_GAP = 0.0
INCREASE_INACTIVE_TIMER = 0.4
DECREASE_INACTIVE_TIMER = 0.1
LEAD_INCREASE_INACTIVE_TIMER = 0.1
LEAD_RECOVERY_LOOKAHEAD_POINTS = 4
LEAD_COAST_BUFFER_MS = 1.0 * CV.MPH_TO_MS

CRUISE_BUTTON_TIMERS = {
  int(ButtonType.decelCruise): 0,
  int(ButtonType.accelCruise): 0,
  int(ButtonType.setCruise): 0,
  int(ButtonType.resumeCruise): 0,
  int(ButtonType.cancel): 0,
  int(ButtonType.mainCruise): 0,
}


def select_redneck_target_speed(v_cruise_kph: float, speed_cluster_ms: float,
                                starpilot_target_speed_ms: float, plan_speeds_ms: list[float],
                                lookahead_points: int, allow_plan_decrease: bool = True,
                                lead_present: bool = False) -> float:
  target_speed_ms = float(speed_cluster_ms)
  if v_cruise_kph > 0:
    target_speed_ms = float(v_cruise_kph) * CV.KPH_TO_MS
  elif starpilot_target_speed_ms > 0:
    target_speed_ms = float(starpilot_target_speed_ms)

  if allow_plan_decrease and len(plan_speeds_ms) > 0:
    if lead_present and plan_speeds_ms[0] > speed_cluster_ms:
      recovery_lookahead_points = min(len(plan_speeds_ms), LEAD_RECOVERY_LOOKAHEAD_POINTS)
      recovery_target_speed_ms = max(speed_cluster_ms, min(plan_speeds_ms[:recovery_lookahead_points]))
      return min(target_speed_ms, recovery_target_speed_ms)

    decrease_target_speed_ms = min(plan_speeds_ms[:lookahead_points])
    if lead_present and decrease_target_speed_ms < speed_cluster_ms:
      decrease_target_speed_ms = max(0.0, decrease_target_speed_ms - LEAD_COAST_BUFFER_MS)

    if decrease_target_speed_ms < target_speed_ms:
      return decrease_target_speed_ms

  return target_speed_ms


def get_minimum_set_speed(is_metric: bool) -> int:
  return 30 if is_metric else 20


def update_manual_button_timers(CS: car.CarState, button_timers: dict[int, int]) -> None:
  for button_type in button_timers:
    if button_timers[button_type] > 0:
      button_timers[button_type] += 1

  for event in CS.buttonEvents:
    button_type = event.type.raw if hasattr(event.type, "raw") else int(event.type)
    if button_type in button_timers:
      button_timers[button_type] = 1 if event.pressed else 0


class RedneckCruise:
  def __init__(self, CP, FPCP):
    self.CP = CP
    self.FPCP = FPCP

    self.v_target = 0
    self.v_target_ms_last = 0.0
    self.v_cruise_cluster = 0
    self.v_cruise_min = 0
    self.state = "inactive"
    self.pre_active_timer = 0
    self.is_ready = False
    self.is_ready_prev = False
    self.cruise_button_timers = dict(CRUISE_BUTTON_TIMERS)

  @staticmethod
  def _send_button_for_state(state: str) -> int:
    if state == "increasing":
      return SEND_BUTTON_INCREASE
    if state == "decreasing":
      return SEND_BUTTON_DECREASE
    return SEND_BUTTON_NONE

  def _reset(self) -> None:
    self.state = "inactive"
    self.pre_active_timer = 0
    self.is_ready = False
    self.is_ready_prev = False

  def _update_calculations(self, CS: car.CarState, v_target_ms: float, is_metric: bool) -> None:
    speed_conv = CV.MS_TO_KPH if is_metric else CV.MS_TO_MPH
    ms_conv = CV.KPH_TO_MS if is_metric else CV.MPH_TO_MS

    self.v_target_ms_last = apply_hysteresis(v_target_ms, self.v_target_ms_last, HYST_GAP * ms_conv)
    self.v_target = round(self.v_target_ms_last * speed_conv)
    self.v_cruise_min = get_minimum_set_speed(is_metric)
    self.v_cruise_cluster = round(CS.cruiseState.speedCluster * speed_conv)

  def _update_readiness(self, CS: car.CarState, CC: car.CarControl) -> None:
    update_manual_button_timers(CS, self.cruise_button_timers)
    button_pressed = any(timer > 0 for timer in self.cruise_button_timers.values())
    self.is_ready = CC.enabled and not CC.cruiseControl.override and not CC.cruiseControl.cancel and not CC.cruiseControl.resume and not button_pressed

  def _desired_state(self) -> str:
    if self.v_target > self.v_cruise_cluster:
      return "increasing"
    if self.v_target < self.v_cruise_cluster and self.v_cruise_cluster > self.v_cruise_min:
      return "decreasing"
    return "holding"

  @staticmethod
  def _get_pre_active_frames(state: str, lead_present: bool) -> int:
    if state == "decreasing":
      timer = DECREASE_INACTIVE_TIMER
    elif lead_present:
      timer = LEAD_INCREASE_INACTIVE_TIMER
    else:
      timer = INCREASE_INACTIVE_TIMER
    return int(timer / DT_CTRL)

  def _arm_pre_active(self, desired_state: str, lead_present: bool) -> None:
    if desired_state == "holding":
      self.state = "holding"
      self.pre_active_timer = 0
      return

    self.state = "preActive"
    self.pre_active_timer = self._get_pre_active_frames(desired_state, lead_present)

  def _update_state_machine(self, lead_present: bool) -> int:
    desired_state = self._desired_state()

    if not self.is_ready:
      self.state = "inactive"
      self.pre_active_timer = 0
    elif self.state == "inactive":
      if not self.is_ready_prev:
        self._arm_pre_active(desired_state, lead_present)
    elif self.state == "preActive":
      if desired_state == "holding":
        self.state = "holding"
        self.pre_active_timer = 0
      else:
        desired_frames = self._get_pre_active_frames(desired_state, lead_present)
        self.pre_active_timer = max(0, min(self.pre_active_timer, desired_frames) - 1)
        if self.pre_active_timer <= 0:
          self.state = desired_state
    elif self.state == "holding":
      if desired_state != "holding":
        self._arm_pre_active(desired_state, lead_present)
    elif self.state != desired_state:
      if desired_state == "holding":
        self.state = "holding"
      else:
        self._arm_pre_active(desired_state, lead_present)

    return self._send_button_for_state(self.state)

  def run(self, CS: car.CarState, CC: car.CarControl, v_target_ms: float, is_metric: bool,
          lead_present: bool = False) -> tuple[int, int]:
    if self.FPCP.pcmCruiseSpeed or not self.FPCP.redneckCruiseAvailable:
      self._reset()
      return SEND_BUTTON_NONE, 0

    self._update_calculations(CS, v_target_ms, is_metric)
    self._update_readiness(CS, CC)
    send_button = self._update_state_machine(lead_present)

    self.is_ready_prev = self.is_ready
    return send_button, self.v_target
