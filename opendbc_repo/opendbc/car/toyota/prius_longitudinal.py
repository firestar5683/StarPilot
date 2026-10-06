import numpy as np
from opendbc.car import structs
from opendbc.car.toyota.values import CAR, ToyotaFlags

PRIUS_POSITIVE_FEEDFORWARD_SCALE = .7
PRIUS_CRUISE_FEEDFORWARD_SCALE = 1.
PRIUS_NEGATIVE_FEEDFORWARD_SCALE = 1.125
TOYOTA_COAST_BRAKE_MIN_SPEED = 15.
TOYOTA_COAST_BRAKE_ENABLE_ACCEL = -.10
TOYOTA_COAST_BRAKE_DISABLE_ACCEL = -.06
TOYOTA_NO_LEAD_COAST_BRAKE_ACCEL = -.30
TOYOTA_NO_LEAD_CRUISE_SIGN_FLIP_MIN_SET_SPEED_ERROR = .35


def configured(cp):
  return (cp.brand == 'toyota' and cp.carFingerprint in (CAR.TOYOTA_PRIUS, CAR.TOYOTA_PRIUS_RETROFIT) and
          cp.pcmCruise and not cp.dashcamOnly and not cp.notCar and
          not cp.passive and cp.steerControlType == structs.CarParams.SteerControlType.torque and
          cp.flags == int(ToyotaFlags.HYBRID | ToyotaFlags.LONG_FILTER | ToyotaFlags.RAISED_ACCEL_LIMIT) and
          len(cp.safetyConfigs) == 1 and cp.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.toyota and
          cp.safetyConfigs[0].safetyParam in (4169, 4681) and
          cp.openpilotLongitudinalControl == (cp.safetyConfigs[0].safetyParam == 4169))


def enabled(cp):
  return configured(cp) and cp.openpilotLongitudinalControl


def stopping_decel_rate(cp):
  return .3 if enabled(cp) else None


def prepare_stock(cp):
  if not configured(cp):
    return False
  cp.openpilotLongitudinalControl = False
  cp.safetyConfigs[0].safetyParam = 4681
  cp.autoResumeSng = False
  return True


def get_prius_positive_feedforward_scale(v_ego: float) -> float:
  return float(np.interp(v_ego, [0.0, 8.0, 20.0],
                         [PRIUS_POSITIVE_FEEDFORWARD_SCALE, PRIUS_POSITIVE_FEEDFORWARD_SCALE, PRIUS_CRUISE_FEEDFORWARD_SCALE]))

def get_prius_feedforward(accel: float, v_ego: float) -> float:
  if accel > 0.0:
    return accel * get_prius_positive_feedforward_scale(v_ego)
  return accel * PRIUS_NEGATIVE_FEEDFORWARD_SCALE

def update_permit_braking(current: bool, net_acceleration_request_min: float, stopping: bool,
                          long_active: bool, v_ego: float, lead_visible: bool) -> bool:
  if stopping or not long_active:
    return True

  if not lead_visible and v_ego >= TOYOTA_COAST_BRAKE_MIN_SPEED:
    return net_acceleration_request_min <= TOYOTA_NO_LEAD_COAST_BRAKE_ACCEL

  # At cruising speeds, some Toyota platforms turn tiny negative accel corrections
  # into noticeable brake taps. Keep a small coast-only band so mild follow/cruise
  # trims stay off the brakes while still allowing real negative requests through.
  if v_ego >= TOYOTA_COAST_BRAKE_MIN_SPEED:
    if net_acceleration_request_min <= TOYOTA_COAST_BRAKE_ENABLE_ACCEL:
      return True
    if net_acceleration_request_min >= TOYOTA_COAST_BRAKE_DISABLE_ACCEL:
      return False
    return current

  if net_acceleration_request_min < 0.2:
    return True
  if net_acceleration_request_min > 0.3:
    return False
  return current

def limit_prius_stopping_accel(pcm_accel_cmd: float, target_accel: float, stopping: bool, v_ego: float, lead_visible: bool) -> float:
  if not stopping or pcm_accel_cmd >= 0.0 or v_ego >= 1.5:
    return pcm_accel_cmd

  # Prius can hold onto a stale full negative stop command at standstill even after the
  # planner has already softened. Keep enough brake to hold the stop, but let the command
  # unwind toward the live planner target so launches are not delayed and stop transitions
  # are less abrupt.
  if target_accel <= -1.8:
    return pcm_accel_cmd

  stop_floor = float(np.interp(v_ego,
                               [0.0, 0.2, 0.5, 0.9, 1.5],
                               [-0.96, -1.00, -1.08, -1.18, -1.35] if lead_visible else [-0.84, -0.88, -0.96, -1.08, -1.24]))
  target_buffer = float(np.interp(v_ego, [0.0, 0.5, 1.5], [0.06, 0.10, 0.16]))
  planner_floor = float(target_accel) - target_buffer
  return max(pcm_accel_cmd, max(stop_floor, planner_floor))

def limit_no_lead_cruise_sign_flip(pcm_accel_cmd: float, target_accel: float, stopping: bool, v_ego: float,
                                   set_speed: float, lead_visible: bool) -> float:
  if stopping or lead_visible or pcm_accel_cmd >= 0.0 or v_ego < TOYOTA_COAST_BRAKE_MIN_SPEED:
    return pcm_accel_cmd
  if target_accel < -0.02 or set_speed <= 0.0:
    return pcm_accel_cmd

  if float(set_speed) - float(v_ego) >= TOYOTA_NO_LEAD_CRUISE_SIGN_FLIP_MIN_SET_SPEED_ERROR:
    return max(pcm_accel_cmd, 0.0)

  return pcm_accel_cmd
