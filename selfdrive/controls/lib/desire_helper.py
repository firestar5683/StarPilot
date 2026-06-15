import json

import numpy as np

from cereal import log
from openpilot.common.constants import CV
from openpilot.common.params import Params
from openpilot.common.realtime import DT_MDL

LaneChangeState = log.LaneChangeState
LaneChangeDirection = log.LaneChangeDirection

LANE_CHANGE_SPEED_MIN = 20 * CV.MPH_TO_MS
LANE_CHANGE_TIME_MAX = 10.
NAV_TURN_DISTANCE_SPEED_BREAKPOINTS = [0.0, 5.0, 10.0]
NAV_TURN_DISTANCE_BREAKPOINTS = [20.0, 25.0, 30.0]
NAV_KEEP_DISTANCE_SPEED_BREAKPOINTS = [0.0, 15.0, 30.0]
NAV_KEEP_DISTANCE_BREAKPOINTS = [25.0, 90.0, 160.0]
NAV_KEEP_AMBIGUOUS_SPLIT_DISTANCE_SCALE = 0.6

DESIRES = {
  LaneChangeDirection.none: {
    LaneChangeState.off: log.Desire.none,
    LaneChangeState.preLaneChange: log.Desire.none,
    LaneChangeState.laneChangeStarting: log.Desire.none,
    LaneChangeState.laneChangeFinishing: log.Desire.none,
  },
  LaneChangeDirection.left: {
    LaneChangeState.off: log.Desire.none,
    LaneChangeState.preLaneChange: log.Desire.none,
    LaneChangeState.laneChangeStarting: log.Desire.laneChangeLeft,
    LaneChangeState.laneChangeFinishing: log.Desire.laneChangeLeft,
  },
  LaneChangeDirection.right: {
    LaneChangeState.off: log.Desire.none,
    LaneChangeState.preLaneChange: log.Desire.none,
    LaneChangeState.laneChangeStarting: log.Desire.laneChangeRight,
    LaneChangeState.laneChangeFinishing: log.Desire.laneChangeRight,
  },
}

TurnDirection = log.Desire

TURN_DESIRES = {
  TurnDirection.none: log.Desire.none,
  TurnDirection.turnLeft: log.Desire.turnLeft,
  TurnDirection.turnRight: log.Desire.turnRight,
}


class DesireHelper:
  def __init__(self):
    self.params = Params()
    self.params_memory = Params(memory=True)
    self.lane_change_state = LaneChangeState.off
    self.lane_change_direction = LaneChangeDirection.none
    self.lane_change_timer = 0.0
    self.lane_change_ll_prob = 1.0
    self.keep_pulse_timer = 0.0
    self.prev_one_blinker = False
    self.desire = log.Desire.none

    self.lane_change_completed = False

    self.lane_change_wait_timer = 0.0
    self.nav_desires_allowed = False
    self._nav_param_counter = -1
    self._nav_instruction_state_raw: object = None
    self._nav_instruction_state: dict[str, object] = {}

  def _update_nav_params(self):
    self._nav_param_counter += 1
    if self._nav_param_counter % 60 == 0:
      self.nav_desires_allowed = self.params.get_bool("NavDesiresAllowed")

    raw = self.params_memory.get("NavInstructionState") or {}
    if raw == self._nav_instruction_state_raw:
      return

    self._nav_instruction_state_raw = raw
    if not raw:
      self._nav_instruction_state = {}
      return

    if isinstance(raw, dict):
      self._nav_instruction_state = raw
      return

    if isinstance(raw, str):
      try:
        parsed = json.loads(raw)
        self._nav_instruction_state = parsed if isinstance(parsed, dict) else {}
        return
      except Exception:
        pass

    self._nav_instruction_state = {}

  @staticmethod
  def _nav_keep_direction_is_clear(carstate, lane_change_direction):
    return not (
      (lane_change_direction == LaneChangeDirection.left and carstate.leftBlindspot) or
      (lane_change_direction == LaneChangeDirection.right and carstate.rightBlindspot)
    )

  @staticmethod
  def _nav_torque_applied(carstate, lane_change_direction):
    return carstate.steeringPressed and (
      (lane_change_direction == LaneChangeDirection.left and carstate.steeringTorque > 0) or
      (lane_change_direction == LaneChangeDirection.right and carstate.steeringTorque < 0)
    )

  @staticmethod
  def _nav_turn_is_imminent(carstate, maneuver_distance):
    try:
      distance = float(maneuver_distance)
    except (TypeError, ValueError):
      return False

    return distance <= float(np.interp(carstate.vEgo, NAV_TURN_DISTANCE_SPEED_BREAKPOINTS, NAV_TURN_DISTANCE_BREAKPOINTS))

  @staticmethod
  def _nav_keep_is_imminent(carstate, maneuver_distance, maneuver_type="", same_side_lane_count=0):
    try:
      distance = float(maneuver_distance)
    except (TypeError, ValueError):
      return False

    threshold = float(np.interp(carstate.vEgo, NAV_KEEP_DISTANCE_SPEED_BREAKPOINTS, NAV_KEEP_DISTANCE_BREAKPOINTS))
    if maneuver_type in ("off ramp", "fork") and int(same_side_lane_count or 0) > 1:
      threshold *= NAV_KEEP_AMBIGUOUS_SPLIT_DISTANCE_SCALE
    return distance <= threshold

  @staticmethod
  def _nav_should_suppress_edge_lane_keep(nav_instruction_state):
    maneuver_type = str(nav_instruction_state.get("maneuverType", ""))
    if maneuver_type not in ("off ramp", "fork"):
      return False

    active_lane_direction = str(nav_instruction_state.get("activeLaneDirection", ""))
    if active_lane_direction not in ("slightLeft", "left", "sharpLeft", "slightRight", "right", "sharpRight"):
      return False

    return (
      int(nav_instruction_state.get("sameSideLaneCount", 0) or 0) > 1 and
      bool(nav_instruction_state.get("activeLaneAtRoadEdge", False)) and
      bool(nav_instruction_state.get("hasSharedSameSideLane", False))
    )

  @staticmethod
  def _nav_effective_modifier(nav_instruction_state, carstate, maneuver_distance):
    modifier = str(nav_instruction_state.get("maneuverModifier", ""))
    maneuver_type = str(nav_instruction_state.get("maneuverType", ""))
    active_lane_direction = str(nav_instruction_state.get("activeLaneDirection", ""))
    same_side_lane_count = int(nav_instruction_state.get("sameSideLaneCount", 0) or 0)

    if maneuver_type in ("off ramp", "fork") and modifier in ("slightLeft", "left", "sharpLeft", "slightRight", "right", "sharpRight"):
      if not DesireHelper._nav_keep_is_imminent(carstate, maneuver_distance, maneuver_type, same_side_lane_count):
        return ""

      if DesireHelper._nav_should_suppress_edge_lane_keep(nav_instruction_state):
        return ""

      if active_lane_direction in ("slightLeft", "left"):
        return "slightLeft"
      if active_lane_direction in ("slightRight", "right"):
        return "slightRight"

      # If lane guidance says the active lane stays straight, don't reinterpret the
      # broader fork/off-ramp maneuver as a late turn into another branch.
      return ""

    return modifier

  def _navigation_desire(self, carstate, lateral_active, starpilotPlan, starpilot_toggles):
    self._update_nav_params()
    if not self.nav_desires_allowed or not lateral_active or not bool(self._nav_instruction_state.get("valid", False)):
      return log.Desire.none

    maneuver_distance = self._nav_instruction_state.get("maneuverDistance", 0.0)
    modifier = self._nav_effective_modifier(self._nav_instruction_state, carstate, maneuver_distance)
    if modifier == "":
      return log.Desire.none

    if modifier == "slightLeft":
      lane_change_direction = LaneChangeDirection.left
      desired_lane_width = starpilotPlan.laneWidthLeft
      nudgeless_allowed = starpilot_toggles.nudgeless and desired_lane_width >= starpilot_toggles.lane_detection_width
      if not carstate.rightBlinker and self._nav_keep_direction_is_clear(carstate, lane_change_direction):
        if self._nav_torque_applied(carstate, lane_change_direction) or nudgeless_allowed:
          return log.Desire.keepLeft
    elif modifier == "slightRight":
      lane_change_direction = LaneChangeDirection.right
      desired_lane_width = starpilotPlan.laneWidthRight
      nudgeless_allowed = starpilot_toggles.nudgeless and desired_lane_width >= starpilot_toggles.lane_detection_width
      if not carstate.leftBlinker and self._nav_keep_direction_is_clear(carstate, lane_change_direction):
        if self._nav_torque_applied(carstate, lane_change_direction) or nudgeless_allowed:
          return log.Desire.keepRight
    elif modifier in ("left", "sharpLeft"):
      if not carstate.rightBlinker and not carstate.leftBlindspot and carstate.vEgo < starpilot_toggles.minimum_lane_change_speed and not carstate.standstill and self._nav_turn_is_imminent(carstate, maneuver_distance):
        return log.Desire.turnLeft
    elif modifier in ("right", "sharpRight"):
      if not carstate.leftBlinker and not carstate.rightBlindspot and carstate.vEgo < starpilot_toggles.minimum_lane_change_speed and not carstate.standstill and self._nav_turn_is_imminent(carstate, maneuver_distance):
        return log.Desire.turnRight

    return log.Desire.none

  @staticmethod
  def get_lane_change_direction(CS):
    return LaneChangeDirection.left if CS.leftBlinker else LaneChangeDirection.right

  def update(self, carstate, lateral_active, lane_change_prob, starpilotPlan, starpilot_toggles):
    v_ego = carstate.vEgo
    one_blinker = carstate.leftBlinker != carstate.rightBlinker
    below_lane_change_speed = v_ego < starpilot_toggles.minimum_lane_change_speed
    cruise_state = getattr(carstate, "cruiseState", None)
    lane_changes_allowed = starpilot_toggles.lane_changes
    lane_changes_allowed &= not getattr(starpilot_toggles, "lane_changes_require_cruise", False) or bool(getattr(cruise_state, "enabled", False))

    lane_change_time_max = getattr(starpilot_toggles, 'lane_change_time_max', LANE_CHANGE_TIME_MAX)
    if not lateral_active or self.lane_change_timer > lane_change_time_max or not lane_changes_allowed:
      self.lane_change_state = LaneChangeState.off
      self.lane_change_direction = LaneChangeDirection.none
    else:
      # LaneChangeState.off
      if self.lane_change_state == LaneChangeState.off and one_blinker and not self.prev_one_blinker and not below_lane_change_speed:
        self.lane_change_state = LaneChangeState.preLaneChange
        self.lane_change_ll_prob = 1.0
        # Initialize lane change direction to prevent UI alert flicker
        self.lane_change_direction = self.get_lane_change_direction(carstate)

      # LaneChangeState.preLaneChange
      elif self.lane_change_state == LaneChangeState.preLaneChange:
        # Update lane change direction
        self.lane_change_direction = self.get_lane_change_direction(carstate)

        torque_applied = carstate.steeringPressed and \
                         ((carstate.steeringTorque > 0 and self.lane_change_direction == LaneChangeDirection.left) or
                          (carstate.steeringTorque < 0 and self.lane_change_direction == LaneChangeDirection.right))

        blindspot_detected = ((carstate.leftBlindspot and self.lane_change_direction == LaneChangeDirection.left) or
                              (carstate.rightBlindspot and self.lane_change_direction == LaneChangeDirection.right))

        if torque_applied:
          self.lane_change_wait_timer = starpilot_toggles.lane_change_delay
        else:
          torque_applied |= starpilot_toggles.nudgeless
          torque_applied &= self.lane_change_wait_timer >= starpilot_toggles.lane_change_delay

          desired_lane_width = starpilotPlan.laneWidthLeft if self.lane_change_direction == LaneChangeDirection.left else starpilotPlan.laneWidthRight
          torque_applied &= desired_lane_width >= starpilot_toggles.lane_detection_width

        if not one_blinker or below_lane_change_speed or self.lane_change_completed:
          self.lane_change_state = LaneChangeState.off
          self.lane_change_direction = LaneChangeDirection.none
        elif torque_applied and not blindspot_detected:
          self.lane_change_state = LaneChangeState.laneChangeStarting

          self.lane_change_completed = starpilot_toggles.one_lane_change

          self.lane_change_wait_timer = 0.0

        self.lane_change_wait_timer += DT_MDL

      # LaneChangeState.laneChangeStarting
      elif self.lane_change_state == LaneChangeState.laneChangeStarting:
        # fade out over .5s
        self.lane_change_ll_prob = max(self.lane_change_ll_prob - 2 * DT_MDL, 0.0)

        # 98% certainty
        if lane_change_prob < 0.02 and self.lane_change_ll_prob < 0.01:
          self.lane_change_state = LaneChangeState.laneChangeFinishing

      # LaneChangeState.laneChangeFinishing
      elif self.lane_change_state == LaneChangeState.laneChangeFinishing:
        # fade in laneline over 1s
        self.lane_change_ll_prob = min(self.lane_change_ll_prob + DT_MDL, 1.0)

        if self.lane_change_ll_prob > 0.99:
          self.lane_change_direction = LaneChangeDirection.none
          if one_blinker:
            self.lane_change_state = LaneChangeState.preLaneChange
          else:
            self.lane_change_state = LaneChangeState.off

    if self.lane_change_state in (LaneChangeState.off, LaneChangeState.preLaneChange):
      self.lane_change_timer = 0.0
    else:
      self.lane_change_timer += DT_MDL

    self.prev_one_blinker = one_blinker

    if lateral_active and one_blinker and below_lane_change_speed and not carstate.standstill and starpilot_toggles.use_turn_desires:
      self.turn_direction = TurnDirection.turnLeft if carstate.leftBlinker else TurnDirection.turnRight
      self.desire = TURN_DESIRES[self.turn_direction]
    else:
      self.turn_direction = TurnDirection.none
      self.desire = DESIRES[self.lane_change_direction][self.lane_change_state]

    # Send keep pulse once per second during LaneChangeStart.preLaneChange
    if self.lane_change_state in (LaneChangeState.off, LaneChangeState.laneChangeStarting):
      self.keep_pulse_timer = 0.0
    elif self.lane_change_state == LaneChangeState.preLaneChange:
      self.keep_pulse_timer += DT_MDL
      if self.keep_pulse_timer > 1.0:
        self.keep_pulse_timer = 0.0
      elif self.desire in (log.Desire.keepLeft, log.Desire.keepRight):
        self.desire = log.Desire.none

    if not one_blinker:
      self.lane_change_completed = False

      self.lane_change_wait_timer = 0.0

    nav_desire = self._navigation_desire(carstate, lateral_active, starpilotPlan, starpilot_toggles)
    if nav_desire != log.Desire.none and self.lane_change_state == LaneChangeState.off:
      self.desire = nav_desire
