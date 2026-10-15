"""Start-state admission for an exact tagged Ioniq 6 LONG session.

This does not qualify ECU ownership; the opt-in prearm still requires a verified
live handoff before longitudinal control is published.
Weak or unknown evidence keeps the ordinary longitudinal PID path. Admission is
immediate because the controller's launch jerk only applies in starting.
"""

import math
from dataclasses import dataclass

from opendbc.car.hyundai.ioniq6_handoff import IONIQ6_DEBUG_LONG_PARAMS
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from opendbc.car.structs import car


LongCtrlState = car.CarControl.Actuators.LongControlState
STRONG_TARGET_MPS2 = 0.75  # Existing Ioniq controller's standstill launch floor.
START_SPEED_MPS = 0.1


@dataclass(frozen=True)
class StartEvidence:
  car_fresh: bool
  plan_fresh: bool
  lead_clear: bool | None
  drive_id: int | None
  observed_ns: int | None


def eligible(cp) -> bool:
  """A stock Ioniq CP never receives the optional starting state."""
  try:
    flags = int(cp.flags)
    required = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_LKA_STEER_MSG)
    forbidden = int(HyundaiFlags.CANFD_ALT_BUTTONS | HyundaiFlags.CANFD_ANGLE_STEERING | HyundaiFlags.CANFD_CAMERA_SCC)
    expected_raw = (0x8095, 0x8895) if flags & int(HyundaiFlags.CANFD_LKA_STEER_MSG_ALT) else (0x8015, 0x8815)
    return (str(cp.carFingerprint) == str(CAR.HYUNDAI_IONIQ_6) and cp.brand == 'hyundai' and
            cp.openpilotLongitudinalControl is True and cp.alphaLongitudinalAvailable is True and
            not cp.pcmCruise and not cp.radarUnavailable and
            not cp.passive and not cp.dashcamOnly and not cp.notCar and
            flags & required == required and not flags & forbidden and
            len(cp.safetyConfigs) == 1 and cp.safetyConfigs[0].safetyModel == car.CarParams.SafetyModel.hyundaiCanfd and
            int(cp.safetyConfigs[0].safetyParam) in expected_raw and
            int(cp.safetyConfigs[0].safetyParam) in IONIQ6_DEBUG_LONG_PARAMS)
  except (AttributeError, IndexError, TypeError, ValueError):
    return False


class Ioniq6StartPolicy:
  def reset(self) -> None:
    pass

  def transition(self, native_state, previous_state, *, active: bool, should_stop: bool,
                 brake_pressed: bool, gas_pressed: bool, can_valid: bool, can_timeout: bool,
                 car_fresh: bool, plan_fresh: bool, lead_clear: bool | None,
                 drive_id: int | None, observed_ns: int | None,
                 speed_mps: float, target_mps2: float, accel_limits: tuple[float, float]):
    """Use native transition except for a fully evidenced strong start frame."""
    try:
      lower, upper = accel_limits
      physical = all(type(value) in (int, float) and math.isfinite(value)
                     for value in (speed_mps, target_mps2, lower, upper))
      strong = (physical and active is True and should_stop is False and brake_pressed is False and
                gas_pressed is False and can_valid is True and can_timeout is False and
                car_fresh is True and plan_fresh is True and type(lead_clear) is bool and
                type(drive_id) is int and drive_id > 0 and
                type(observed_ns) is int and observed_ns > drive_id and
                0.0 <= speed_mps <= START_SPEED_MPS and lower <= 0.0 <= upper and
                target_mps2 >= STRONG_TARGET_MPS2 and upper >= STRONG_TARGET_MPS2)
    except (TypeError, ValueError, OverflowError):
      strong = False

    if strong:
      return LongCtrlState.starting
    if previous_state == LongCtrlState.starting:
      return LongCtrlState.stopping if active and should_stop else (LongCtrlState.pid if active else LongCtrlState.off)
    return native_state

  @staticmethod
  def starting_output(target_mps2: float, accel_limits: tuple[float, float]) -> float:
    """Never add a launch kick above the fresh planner target or native bound."""
    return max(0.0, min(target_mps2, accel_limits[1]))
