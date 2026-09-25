import numpy as np

from opendbc.car import DT_CTRL
from opendbc.car.ford.values import CarControllerParams

STEER_DT = CarControllerParams.STEER_STEP * DT_CTRL
MANUAL_TURN_ENTRY_ANGLE_DEG = 12.0
MANUAL_TURN_RELEASE_ANGLE_DEG = 12.0
MANUAL_TURN_RECOVERY_SECONDS = 0.25


class HumanTurnDetector:
  ANGLE_DEG = 45.0
  HOLD_SECONDS = 1.5
  PRETURNED_HOLD_SECONDS = 3.0

  def __init__(self):
    self.timer = 0.0
    self.active = False
    self._pressed_last = False
    self._press_started_preturned = False

  def update(self, enabled: bool, steering_pressed: bool, steering_angle_deg: float) -> bool:
    if steering_pressed and not self._pressed_last:
      self._press_started_preturned = abs(steering_angle_deg) > self.ANGLE_DEG
    self._pressed_last = steering_pressed

    if enabled and steering_pressed and abs(steering_angle_deg) > self.ANGLE_DEG:
      self.timer += STEER_DT
    else:
      self.timer = 0.0

    hold_time = self.PRETURNED_HOLD_SECONDS if self._press_started_preturned else self.HOLD_SECONDS
    self.active = self.timer + 1e-9 >= hold_time
    return self.active

  def reset(self):
    self.timer = 0.0
    self.active = False
    self._pressed_last = False
    self._press_started_preturned = False


class ManualTurnLatch:
  def __init__(self):
    self.human_turn = HumanTurnDetector()
    self.manual_turn_latched = False
    self.manual_turn_recovery_timer = 0.0
    self.manual_turn_direction = 0.0
    self.human_turn_enabled = True

  def update(self, CC, CS, desired: float, enabled: bool, lane_change: bool, entry_allowed: bool = True) -> bool:
    if not CC.latActive:
      self.human_turn.reset()
      self.manual_turn_latched = False
      self.manual_turn_recovery_timer = 0.0
      self.manual_turn_direction = 0.0
      return False
    self.human_turn_enabled = enabled
    detected = self.human_turn.update(
      self.human_turn_enabled, CS.out.steeringPressed, CS.out.steeringAngleDeg)
    if not self.human_turn_enabled:
      self.manual_turn_latched = False
      self.manual_turn_recovery_timer = 0.0
      self.manual_turn_direction = 0.0
      return False

    blinker_direction = float(CS.out.rightBlinker) - float(CS.out.leftBlinker)
    driver_turning_with_signal = (
      CS.out.steeringPressed and abs(CS.out.steeringAngleDeg) >= MANUAL_TURN_ENTRY_ANGLE_DEG and
      blinker_direction != 0.0 and not lane_change and
      CS.out.steeringTorque * blinker_direction < 0.0
    )
    if entry_allowed and (detected or driver_turning_with_signal):
      self.manual_turn_latched = True
      if blinker_direction != 0.0:
        self.manual_turn_direction = blinker_direction
      elif self.manual_turn_direction == 0.0:
        self.manual_turn_direction = -float(np.sign(CS.out.steeringAngleDeg))

    if not self.manual_turn_latched:
      self.manual_turn_recovery_timer = 0.0
      self.manual_turn_direction = 0.0
      return False

    if (CS.out.steeringPressed or blinker_direction != 0.0 or
        abs(CS.out.steeringAngleDeg) > MANUAL_TURN_RELEASE_ANGLE_DEG):
      self.manual_turn_recovery_timer = 0.0
    else:
      self.manual_turn_recovery_timer += STEER_DT
      if self.manual_turn_recovery_timer + 1e-9 >= MANUAL_TURN_RECOVERY_SECONDS:
        current = -CS.out.yawRate / max(CS.out.vEgoRaw, 0.1)
        if (self.manual_turn_direction * desired > 0.0 and
            self.manual_turn_direction * (desired - current) > CarControllerParams.CURVATURE_ERROR):
          self.manual_turn_recovery_timer = MANUAL_TURN_RECOVERY_SECONDS
        else:
          self.manual_turn_latched = False
          self.manual_turn_recovery_timer = 0.0
          self.manual_turn_direction = 0.0

    return self.manual_turn_latched
