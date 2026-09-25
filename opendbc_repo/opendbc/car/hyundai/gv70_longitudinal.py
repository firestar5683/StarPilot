"""First-generation Electrified GV70 SCC demand and stock-cancel policy."""
from dataclasses import dataclass
import numpy as np

from opendbc.car.hyundai.values import CAR

JERK_UPPER = 1.5
JERK_LOWER = 2.0
URGENT_JERK_LOWER = 5.0
URGENT_ACCEL = -1.0
SCC_FREQUENCY = 50.0


def is_gv70(cp):
  return cp.carFingerprint == CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN


@dataclass(frozen=True)
class SCCRequest:
  raw_accel: float
  accel: float
  jerk_upper: float
  jerk_lower: float


def scc_request(enabled, gas_override, stopping, accel, accel_last):
  lower = URGENT_JERK_LOWER if stopping or accel <= URGENT_ACCEL else JERK_LOWER
  shaped = float(np.clip(accel, accel_last - lower / SCC_FREQUENCY, accel_last + JERK_UPPER / SCC_FREQUENCY)) \
    if enabled and not gas_override else 0.0
  return SCCRequest(accel, shaped, JERK_UPPER, lower)


def suppress_stock_cancel(cp, brake_pressed, lat_active, *, stock_fallback=False):
  return bool(is_gv70(cp) and not cp.openpilotLongitudinalControl and
              (stock_fallback or (brake_pressed and lat_active)))


def tracked_lead_scale(cp):
  eligible = (cp.carFingerprint == CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN and cp.openpilotLongitudinalControl and
              not cp.passive and not cp.dashcamOnly and not cp.notCar)
  return 1.75 if eligible else 1.0
