"""Production EV9 longitudinal shaping and integrity gates.

The historical staged knockout/probe controls deliberately do not live in this
module. An EV9 with openpilot longitudinal enabled always uses the complete,
route-validated reconstruction profile; otherwise it uses the stock path.
"""

from dataclasses import dataclass
from enum import IntEnum

import numpy as np

from opendbc.car import CanData, rate_limit
from opendbc.car.hyundai.values import CarControllerParams


EV9_ACTUATION_JERK_LOWER = 0.7
EV9_ACTUATION_JERK_UPPER = 0.7
EV9_HOLD_JERK_UPPER = 1.5
EV9_STARTING_JERK_UPPER = 0.5
EV9_STOPPING_JERK_UPPER = 1.0
EV9_SCC_CONTROL_FREQUENCY = 50.0
EV9_STOP_REQUEST_SPEED = 0.47
EV9_STANDSTILL_DELAY_FRAMES = 178
EV9_STOP_RELEASE_DELAY_FRAMES = 6
EV9_START_ACCEL = 0.20
EV9_STARTING_SPEED = 0.5

# StopReq owns the final handoff near 0.47 m/s; the lower points provide a
# continuous fail-soft extrapolation if the state transition arrives late.
EV9_STOP_BRAKE_CAP_SPEED_BP = [0.0, 0.46, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
EV9_STOP_BRAKE_CAP_ACCEL_V = [0.0, -0.69, -0.70, -0.87, -1.05, -1.35, -1.65, -2.10, -2.20]

# Full route-backed ADAS_DRV continuation set produced by create_adrv_messages.
# 0x51 was absent from the stock reference route and 0x57A remains physical,
# so neither is synthesized here.
EV9_PRODUCTION_REPLAY_ADDRS = frozenset((0x160, 0x1DA, 0x1EA, 0x200, 0x345))


class EV9ActuationAbortReason(IntEnum):
  NONE = 0
  CAN_INVALID = 1
  RADAR_INVALID = 2
  PANDA_FAULT = 3
  STOCK_SCC_BASELINE_MISSING = 4


@dataclass(frozen=True)
class EV9LongitudinalStopState:
  stop_request: bool = False
  cruise_standstill: bool = False
  stop_request_frames: int = 0
  release_frames: int = 0


def update_ev9_longitudinal_stop_state(state: EV9LongitudinalStopState, enabled: bool,
                                        stopping: bool, v_ego: float) -> EV9LongitudinalStopState:
  """Reproduce the stock EV9 stop/hold/release timing captured in route b4."""
  if not enabled:
    return EV9LongitudinalStopState()

  if stopping:
    if not state.stop_request and v_ego > EV9_STOP_REQUEST_SPEED:
      return EV9LongitudinalStopState()
    frames = state.stop_request_frames + 1 if state.stop_request else 0
    return EV9LongitudinalStopState(
      stop_request=True,
      cruise_standstill=frames >= EV9_STANDSTILL_DELAY_FRAMES,
      stop_request_frames=frames,
    )

  if state.stop_request:
    release_frames = state.release_frames + 1
    if release_frames <= EV9_STOP_RELEASE_DELAY_FRAMES:
      return EV9LongitudinalStopState(
        stop_request=True,
        cruise_standstill=False,
        stop_request_frames=state.stop_request_frames,
        release_frames=release_frames,
      )

  return EV9LongitudinalStopState()


def should_send_ev9_direct_angle_command(drive_gear: bool, lat_active: bool) -> bool:
  """Only make 0xCB active while lateral control is requested in Drive."""
  return drive_gear and lat_active


def filter_ev9_adrv_replay_messages(messages: list[CanData]) -> list[CanData]:
  """Select the fixed production continuation set from generic ADAS messages."""
  return [msg for msg in messages if msg[0] in EV9_PRODUCTION_REPLAY_ADDRS]


def ev9_longitudinal_scc_command(enabled: bool, accel: float, stopping: bool, gas_override: bool,
                                 actuation_permitted: bool = True) -> tuple[bool, float, bool, bool]:
  """Return a bounded EV9 SCC request or an inactive fail-closed request."""
  if actuation_permitted:
    limited_accel = max(CarControllerParams.ACCEL_MIN, min(accel, CarControllerParams.ACCEL_MAX))
    return enabled, limited_accel, stopping, gas_override
  return False, 0.0, False, False


def ev9_limit_stopping_accel(accel_raw: float, v_ego: float) -> float:
  """Cap low-speed braking with the taper measured in the stock EV9 route."""
  brake_cap = float(np.interp(max(v_ego, 0.0), EV9_STOP_BRAKE_CAP_SPEED_BP, EV9_STOP_BRAKE_CAP_ACCEL_V))
  return min(0.0, max(accel_raw, brake_cap))


def shape_ev9_longitudinal_accel(accel_last: float, accel_raw: float, v_ego: float, starting: bool,
                                 stopping: bool, stop_state: EV9LongitudinalStopState) -> tuple[float, float, float]:
  """Return EV9 raw/applied acceleration and upper jerk for the current phase."""
  if stop_state.stop_request:
    first_stop_request = stop_state.stop_request_frames == 0 and stop_state.release_frames == 0 and \
      not stop_state.cruise_standstill
    jerk_upper = EV9_STOPPING_JERK_UPPER if first_stop_request else EV9_HOLD_JERK_UPPER
    return 0.0, 0.0, jerk_upper

  if stopping:
    accel_raw = ev9_limit_stopping_accel(accel_raw, v_ego)

  if starting:
    jerk_upper = EV9_STARTING_JERK_UPPER
  elif stopping:
    jerk_upper = EV9_STOPPING_JERK_UPPER
  else:
    jerk_upper = EV9_ACTUATION_JERK_UPPER

  accel_value = rate_limit(
    accel_raw, accel_last,
    -EV9_ACTUATION_JERK_LOWER / EV9_SCC_CONTROL_FREQUENCY,
    jerk_upper / EV9_SCC_CONTROL_FREQUENCY,
  )
  return accel_raw, accel_value, jerk_upper


def ev9_actuation_abort_reason(control_requested: bool, can_valid: bool, radar_valid: bool,
                               panda_faulted: bool, scc_baseline_valid: bool = True) -> EV9ActuationAbortReason:
  """Inhibit EV9 actuation while any required integrity input is invalid."""
  if not control_requested:
    return EV9ActuationAbortReason.NONE
  if not can_valid:
    return EV9ActuationAbortReason.CAN_INVALID
  if not radar_valid:
    return EV9ActuationAbortReason.RADAR_INVALID
  if panda_faulted:
    return EV9ActuationAbortReason.PANDA_FAULT
  if not scc_baseline_valid:
    return EV9ActuationAbortReason.STOCK_SCC_BASELINE_MISSING
  return EV9ActuationAbortReason.NONE
