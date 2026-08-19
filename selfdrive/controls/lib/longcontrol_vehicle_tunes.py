import numpy as np

from opendbc.car.gm.values import CAR, GMFlags
from opendbc.car.subaru.values import CAR as SUBARU_CAR
from opendbc.car.toyota.values import CAR as TOYOTA_CAR
from openpilot.common.realtime import DT_CTRL
from openpilot.starpilot.common.testing_grounds import testing_ground


clip = np.clip
interp = np.interp

BOLT_ACC_PEDAL_REGEN_LIMIT_BP = [0.0, 1.5, 4.0, 8.0, 15.0, 30.0]
BOLT_ACC_PEDAL_REGEN_LIMIT_V = [-0.93, -1.28, -1.98, -2.58, -2.86, -2.95]
BOLT_ACC_PEDAL_START_HANDOFF_TIME = 0.75
BOLT_ACC_PEDAL_START_HANDOFF_MAX_SPEED = 1.25
BOLT_ACC_PEDAL_START_HANDOFF_MIN_TARGET = 0.15
BOLT_ACC_PEDAL_START_HANDOFF_FLOOR_BP = [0.0, 0.5, BOLT_ACC_PEDAL_START_HANDOFF_MAX_SPEED]
BOLT_ACC_PEDAL_START_HANDOFF_FLOOR_V = [0.22, 0.18, 0.10]
NEGATIVE_TARGET_CREEP_GUARD_SPEED = 0.35
NEGATIVE_TARGET_CREEP_GUARD_DECEL = 0.40
GM_TRUCK_TARGET_FILTER_MIN_SPEED = 12.0
GM_TRUCK_TARGET_FILTER_UP_TAU = 0.20
GM_TRUCK_TARGET_FILTER_DOWN_TAU = 0.14
GM_TRUCK_TARGET_FILTER_BRAKE_BYPASS = -0.65
GM_TRUCK_TARGET_FILTER_DROP_BYPASS = 0.45
TOYOTA_SIENNA_TARGET_FILTER_MIN_SPEED = 12.0
TOYOTA_SIENNA_TARGET_FILTER_UP_TAU = 0.32
TOYOTA_SIENNA_TARGET_FILTER_DOWN_TAU = 0.24
TOYOTA_SIENNA_LOW_SPEED_ACCEL_UP_TAU = 0.50
TOYOTA_SIENNA_TARGET_FILTER_BRAKE_BYPASS = -0.75
TOYOTA_SIENNA_TARGET_FILTER_DROP_BYPASS = 0.65
TOYOTA_SIENNA_COMFORT_FILTER_MIN_SPEED = 1.0
TOYOTA_SIENNA_COMFORT_FILTER_MIN_DISTANCE = 7.0
TOYOTA_SIENNA_COMFORT_FILTER_MIN_TTC = 4.5
TOYOTA_SIENNA_COMFORT_FILTER_MAX_CLOSING_SPEED = 4.0
TOYOTA_SIENNA_COMFORT_FILTER_MAX_LEAD_BRAKE = 2.5
TOYOTA_SIENNA_COMFORT_FILTER_BRAKE_BYPASS = -2.5
TOYOTA_COROLLA_TARGET_FILTER_MAX_SPEED = 3.0
TOYOTA_COROLLA_TARGET_FILTER_UP_TAU = 0.30
TOYOTA_COROLLA_TARGET_FILTER_DOWN_TAU = 0.18
TOYOTA_COROLLA_TARGET_FILTER_BRAKE_BYPASS = -0.75
TOYOTA_COROLLA_TARGET_FILTER_DROP_BYPASS = 0.45
VOLT_CRUISE_INTEGRATOR_MIN_SPEED = 8.0
VOLT_CRUISE_INTEGRATOR_TARGET_MAX = 0.12
VOLT_CRUISE_INTEGRATOR_ERROR_MAX = 0.12
VOLT_CRUISE_INTEGRATOR_LEAK = 0.995
SUBARU_IMPREZA_STOP_RELEASE_TIME = 0.75
SUBARU_IMPREZA_STOP_RELEASE_MAX_ACCEL = 0.8
HYUNDAI_ELANTRA_STOPPING_HOLD_TARGET_GAP = 0.25
HYUNDAI_ELANTRA_STOPPED_LEAD_MAX_EGO_SPEED = 2.0
HYUNDAI_ELANTRA_STOPPED_LEAD_MAX_SPEED = 0.5
HYUNDAI_ELANTRA_STOPPED_LEAD_MIN_CLOSING_SPEED = 0.25
HYUNDAI_ELANTRA_STOPPED_LEAD_MAX_CREEP_ACCEL = 0.05
HYUNDAI_SANTA_FE_FINAL_STOP_MAX_SPEED = 1.0
HYUNDAI_SANTA_FE_FINAL_STOP_CAP_BP = [0.0, 0.2, 0.5, HYUNDAI_SANTA_FE_FINAL_STOP_MAX_SPEED]
HYUNDAI_SANTA_FE_FINAL_STOP_CAP_V = [-0.25, -0.30, -0.50, -0.90]


def get_bolt_acc_pedal_friction_bias(output_accel, a_target, v_ego):
  if output_accel >= -0.05 or a_target >= -0.80 or v_ego <= 5.0:
    return 0.0

  authority_gap = max(0.0, abs(a_target) - abs(output_accel))
  if authority_gap <= 0.25:
    return 0.0

  speed_factor = interp(v_ego, [5.0, 10.0, 15.0, 25.0], [0.0, 0.55, 0.85, 1.0])
  max_bias = interp(abs(a_target), [0.8, 1.4, 2.2, 3.5], [0.0, 0.14, 0.42, 0.70])
  return float(min(authority_gap * 0.30, max_bias) * speed_factor)


def get_bolt_acc_pedal_friction_floor(a_target, v_ego, pedal_regen_limit):
  if v_ego <= 5.0 or a_target >= (pedal_regen_limit - 0.05):
    return None

  friction_request = max(0.0, pedal_regen_limit - a_target)
  if friction_request <= 0.10:
    return None

  speed_factor = interp(v_ego, [5.0, 8.0, 12.0, 18.0, 25.0], [0.0, 0.45, 0.75, 0.90, 1.0])
  demand_factor = interp(friction_request, [0.10, 0.25, 0.50, 0.90, 1.30], [0.0, 0.22, 0.50, 0.78, 1.0])
  floor_fraction = float(clip(speed_factor * demand_factor, 0.0, 1.0))

  return float(pedal_regen_limit - (friction_request * floor_fraction))


def get_bolt_acc_pedal_feedforward_gain(feedforward_gain, a_target, v_ego, pedal_regen_limit, last_output_accel):
  effective_gain = feedforward_gain
  if a_target >= 0.0:
    return effective_gain

  restore = 0.0

  if a_target < pedal_regen_limit:
    friction_gap = pedal_regen_limit - a_target
    restore = float(interp(friction_gap, [0.0, 0.25, 0.75], [0.0, 0.6, 1.0]))

  if v_ego > 5.0 and a_target < -1.10:
    authority_gap = max(0.0, abs(a_target) - abs(min(last_output_accel, 0.0)))
    target_restore = float(interp(abs(a_target), [1.1, 1.6, 2.2, 3.0], [0.0, 0.25, 0.55, 1.0]))
    gap_restore = float(interp(authority_gap, [0.2, 0.6, 1.0, 1.6], [0.0, 0.25, 0.60, 1.0]))
    speed_factor = float(interp(v_ego, [5.0, 8.0, 12.0, 18.0], [0.0, 0.35, 0.75, 1.0]))
    restore = max(restore, max(target_restore, gap_restore) * speed_factor)

  return float(feedforward_gain + ((1.0 - feedforward_gain) * clip(restore, 0.0, 1.0)))


class LongControlVehicleTuning:
  def __init__(self, CP):
    self.is_gm_pedal_long = bool(
      CP.brand == "gm" and CP.enableGasInterceptorDEPRECATED and (CP.flags & GMFlags.PEDAL_LONG.value)
    )
    self.is_volt = bool(
      CP.brand == "gm" and str(CP.carFingerprint).startswith("CHEVROLET_VOLT")
    )
    self.is_gm_stock_truck = bool(
      CP.brand == "gm" and
      getattr(CP, "carFingerprint", None) in (CAR.CHEVROLET_SILVERADO, CAR.CHEVROLET_SILVERADO_CC) and
      not CP.enableGasInterceptorDEPRECATED
    )
    self.is_toyota_sienna_4g = bool(
      CP.brand == "toyota" and
      str(getattr(CP, "carFingerprint", "")) == str(TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
    )
    self.is_toyota_corolla_tss2 = bool(
      CP.brand == "toyota" and
      getattr(CP, "carFingerprint", None) == TOYOTA_CAR.TOYOTA_COROLLA_TSS2
    )
    self.is_subaru_impreza_2020 = bool(
      CP.brand == "subaru" and
      getattr(CP, "carFingerprint", None) == SUBARU_CAR.SUBARU_IMPREZA_2020
    )
    self.is_hyundai_elantra_2021 = bool(
      CP.brand == "hyundai" and str(getattr(CP, "carFingerprint", "")) == "HYUNDAI_ELANTRA_2021"
    )
    self.is_hyundai_santa_fe_2022 = bool(
      CP.brand == "hyundai" and str(getattr(CP, "carFingerprint", "")) == "HYUNDAI_SANTA_FE_2022"
    )
    self.is_bolt_acc_pedal_friction_car = bool(
      CP.brand == "gm" and
      CP.enableGasInterceptorDEPRECATED and
      getattr(CP, "carFingerprint", None) == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL and
      (CP.flags & GMFlags.PEDAL_LONG.value)
    )
    self.reset()

  def reset(self):
    self.last_a_target = 0.0
    self.integrator_hold_frames = 0
    self.gm_truck_filtered_a_target = 0.0
    self.gm_truck_target_filter_initialized = False
    self.toyota_sienna_filtered_a_target = 0.0
    self.toyota_sienna_target_filter_initialized = False
    self.toyota_corolla_filtered_a_target = 0.0
    self.toyota_corolla_target_filter_initialized = False
    self.bolt_start_handoff_frames = 0
    self.subaru_stop_release_frames = 0

  def shape_stopping_accel(self, output_accel, a_target, should_stop, v_ego, has_lead, stop_accel):
    """Release a stale hard lead brake once the stop target has eased."""
    if (
      self.is_hyundai_santa_fe_2022 and
      v_ego <= HYUNDAI_SANTA_FE_FINAL_STOP_MAX_SPEED and
      a_target <= 0.1
    ):
      final_stop_cap = float(interp(v_ego, HYUNDAI_SANTA_FE_FINAL_STOP_CAP_BP, HYUNDAI_SANTA_FE_FINAL_STOP_CAP_V))
      return max(float(output_accel), final_stop_cap)

    if (
      not self.is_hyundai_elantra_2021 or
      not has_lead or not should_stop or v_ego > 2.0 or
      a_target <= stop_accel - HYUNDAI_ELANTRA_STOPPING_HOLD_TARGET_GAP
    ):
      return output_accel
    return max(float(output_accel), float(stop_accel))

  def is_hyundai_elantra_closing_on_stopped_lead(self, v_ego, should_stop, leads):
    if not self.is_hyundai_elantra_2021 or should_stop or v_ego > HYUNDAI_ELANTRA_STOPPED_LEAD_MAX_EGO_SPEED:
      return False

    lead = leads[0] if leads else None
    if lead is None or not bool(getattr(lead, "status", False)):
      return False

    lead_speed = max(0.0, float(getattr(lead, "vLead", 0.0)))
    closing_speed = float(v_ego) - lead_speed
    return (
      lead_speed <= HYUNDAI_ELANTRA_STOPPED_LEAD_MAX_SPEED and
      closing_speed >= HYUNDAI_ELANTRA_STOPPED_LEAD_MIN_CLOSING_SPEED
    )

  def shape_hyundai_elantra_lead_target(self, a_target, v_ego, should_stop, leads):
    if self.is_hyundai_elantra_closing_on_stopped_lead(v_ego, should_stop, leads):
      return min(float(a_target), HYUNDAI_ELANTRA_STOPPED_LEAD_MAX_CREEP_ACCEL)
    return a_target

  def cap_hyundai_elantra_lead_output(self, output_accel, v_ego, should_stop, leads):
    if self.is_hyundai_elantra_closing_on_stopped_lead(v_ego, should_stop, leads):
      return min(float(output_accel), HYUNDAI_ELANTRA_STOPPED_LEAD_MAX_CREEP_ACCEL)
    return output_accel

  def cap_subaru_stop_release_accel(self, output_accel, stopping_handoff, should_stop):
    """Prevent an Impreza stop-sign handoff from stepping straight into full throttle."""
    if not self.is_subaru_impreza_2020:
      return output_accel

    if should_stop:
      self.subaru_stop_release_frames = 0
    elif stopping_handoff:
      self.subaru_stop_release_frames = int(round(SUBARU_IMPREZA_STOP_RELEASE_TIME / DT_CTRL))

    if self.subaru_stop_release_frames <= 0:
      return output_accel

    self.subaru_stop_release_frames -= 1
    return min(float(output_accel), SUBARU_IMPREZA_STOP_RELEASE_MAX_ACCEL)

  def apply_bolt_start_handoff_floor(self, output_accel, last_output_accel, a_target, v_ego,
                                     starting_handoff, should_stop, has_lead):
    if not self.is_bolt_acc_pedal_friction_car:
      return output_accel

    if starting_handoff:
      self.bolt_start_handoff_frames = int(round(BOLT_ACC_PEDAL_START_HANDOFF_TIME / DT_CTRL))

    safe_to_hold = (
      self.bolt_start_handoff_frames > 0 and
      has_lead and
      not should_stop and
      a_target > BOLT_ACC_PEDAL_START_HANDOFF_MIN_TARGET and
      v_ego < BOLT_ACC_PEDAL_START_HANDOFF_MAX_SPEED
    )
    if not safe_to_hold:
      self.bolt_start_handoff_frames = 0
      return output_accel

    self.bolt_start_handoff_frames -= 1
    speed_floor = float(interp(v_ego, BOLT_ACC_PEDAL_START_HANDOFF_FLOOR_BP,
                               BOLT_ACC_PEDAL_START_HANDOFF_FLOOR_V))
    target_floor = min(speed_floor, max(0.0, 0.4 * float(a_target)))
    return max(float(output_accel), min(float(last_output_accel), target_floor))

  def shape_gm_truck_accel_target(self, a_target, v_ego, should_stop):
    if not self.is_gm_stock_truck:
      return a_target

    bypass_filter = (
      v_ego < GM_TRUCK_TARGET_FILTER_MIN_SPEED or
      should_stop or
      a_target <= GM_TRUCK_TARGET_FILTER_BRAKE_BYPASS or
      (self.gm_truck_target_filter_initialized and
       a_target < self.gm_truck_filtered_a_target - GM_TRUCK_TARGET_FILTER_DROP_BYPASS)
    )
    if not self.gm_truck_target_filter_initialized or bypass_filter:
      self.gm_truck_filtered_a_target = float(a_target)
      self.gm_truck_target_filter_initialized = True
      return float(a_target)

    tau = GM_TRUCK_TARGET_FILTER_DOWN_TAU if a_target < self.gm_truck_filtered_a_target else GM_TRUCK_TARGET_FILTER_UP_TAU
    alpha = DT_CTRL / (tau + DT_CTRL)
    self.gm_truck_filtered_a_target += alpha * (float(a_target) - self.gm_truck_filtered_a_target)
    return self.gm_truck_filtered_a_target

  def shape_toyota_sienna_accel_target(self, a_target, v_ego, should_stop, leads=None):
    """Smooth Sienna lead braking only while there is still comfortable stopping room."""
    if not self.is_toyota_sienna_4g or should_stop:
      self.toyota_sienna_target_filter_initialized = False
      return a_target

    comfort_lead = None
    if leads:
      active_leads = [
        lead for lead in leads
        if bool(getattr(lead, "status", False)) and
        abs(float(getattr(lead, "yRel", 0.0))) <= 1.75 and
        float(getattr(lead, "dRel", 0.0)) > 0.0
      ]
      if active_leads:
        comfort_lead = min(active_leads, key=lambda lead: float(getattr(lead, "dRel", 0.0)))

    comfort_filter_active = False
    if comfort_lead is not None and v_ego >= TOYOTA_SIENNA_COMFORT_FILTER_MIN_SPEED:
      lead_distance = float(getattr(comfort_lead, "dRel", 0.0))
      lead_speed = max(float(getattr(comfort_lead, "vLead", 0.0)), 0.0)
      closing_speed = max(0.0, float(v_ego) - lead_speed)
      ttc = lead_distance / max(closing_speed, 0.1) if closing_speed > 0.1 else float("inf")
      lead_brake = max(0.0, -float(getattr(comfort_lead, "aLeadK", 0.0)))
      comfort_filter_active = (
        lead_distance >= TOYOTA_SIENNA_COMFORT_FILTER_MIN_DISTANCE and
        ttc >= TOYOTA_SIENNA_COMFORT_FILTER_MIN_TTC and
        closing_speed <= TOYOTA_SIENNA_COMFORT_FILTER_MAX_CLOSING_SPEED and
        lead_brake <= TOYOTA_SIENNA_COMFORT_FILTER_MAX_LEAD_BRAKE
      )

    if v_ego < TOYOTA_SIENNA_TARGET_FILTER_MIN_SPEED and not comfort_filter_active:
      if a_target > 0.0:
        if not self.toyota_sienna_target_filter_initialized or (
          self.toyota_sienna_filtered_a_target < 0.0 and comfort_lead is None
        ):
          self.toyota_sienna_filtered_a_target = 0.0
          self.toyota_sienna_target_filter_initialized = True
        alpha = DT_CTRL / (TOYOTA_SIENNA_LOW_SPEED_ACCEL_UP_TAU + DT_CTRL)
        self.toyota_sienna_filtered_a_target += alpha * (
          float(a_target) - self.toyota_sienna_filtered_a_target
        )
        return self.toyota_sienna_filtered_a_target

      if comfort_lead is not None:
        self.toyota_sienna_filtered_a_target = float(a_target)
        self.toyota_sienna_target_filter_initialized = True
        return float(a_target)

      self.toyota_sienna_target_filter_initialized = False
      return a_target

    # Keep the legacy high-speed filter unchanged. The lower-speed entry is only
    # for a centered lead with enough room to soften a comfort response.
    if comfort_filter_active:
      bypass_filter = a_target <= TOYOTA_SIENNA_COMFORT_FILTER_BRAKE_BYPASS
    else:
      bypass_filter = (
        a_target <= TOYOTA_SIENNA_TARGET_FILTER_BRAKE_BYPASS or
        (self.toyota_sienna_target_filter_initialized and
         a_target < self.toyota_sienna_filtered_a_target - TOYOTA_SIENNA_TARGET_FILTER_DROP_BYPASS)
      )
    if not self.toyota_sienna_target_filter_initialized or bypass_filter:
      self.toyota_sienna_filtered_a_target = float(a_target)
      self.toyota_sienna_target_filter_initialized = True
      return float(a_target)

    tau = (TOYOTA_SIENNA_TARGET_FILTER_DOWN_TAU
           if a_target < self.toyota_sienna_filtered_a_target
           else TOYOTA_SIENNA_TARGET_FILTER_UP_TAU)
    alpha = DT_CTRL / (tau + DT_CTRL)
    self.toyota_sienna_filtered_a_target += alpha * (float(a_target) - self.toyota_sienna_filtered_a_target)
    return self.toyota_sienna_filtered_a_target

  def shape_toyota_corolla_accel_target(self, a_target, v_ego, should_stop, last_output_accel):
    """Smooth low-speed Corolla TSS2 stop releases without delaying hard braking."""
    if not self.is_toyota_corolla_tss2 or should_stop or v_ego >= TOYOTA_COROLLA_TARGET_FILTER_MAX_SPEED:
      self.toyota_corolla_target_filter_initialized = False
      return a_target

    if not self.toyota_corolla_target_filter_initialized:
      self.toyota_corolla_filtered_a_target = float(last_output_accel)
      self.toyota_corolla_target_filter_initialized = True

    bypass_filter = (
      a_target <= TOYOTA_COROLLA_TARGET_FILTER_BRAKE_BYPASS or
      a_target < self.toyota_corolla_filtered_a_target - TOYOTA_COROLLA_TARGET_FILTER_DROP_BYPASS
    )
    if bypass_filter:
      self.toyota_corolla_filtered_a_target = float(a_target)
      return float(a_target)

    tau = (TOYOTA_COROLLA_TARGET_FILTER_DOWN_TAU
           if a_target < self.toyota_corolla_filtered_a_target
           else TOYOTA_COROLLA_TARGET_FILTER_UP_TAU)
    alpha = DT_CTRL / (tau + DT_CTRL)
    self.toyota_corolla_filtered_a_target += alpha * (float(a_target) - self.toyota_corolla_filtered_a_target)
    return self.toyota_corolla_filtered_a_target

  def get_integrator_freeze(self, last_output_accel, a_target, error, v_ego, accel_limits):
    volt_test_tune_handoff = self.is_volt and testing_ground.use_2

    if not self.is_gm_pedal_long and not volt_test_tune_handoff:
      self.last_a_target = a_target
      self.integrator_hold_frames = 0
      return False

    if self.is_gm_pedal_long:
      handoff_threshold = interp(v_ego, [0.0, 4.0, 12.0, 25.0], [0.35, 0.45, 0.55, 0.70])
      hold_frames = int(round(interp(v_ego, [0.0, 4.0, 12.0, 25.0], [25.0, 20.0, 14.0, 10.0])))
    else:
      handoff_threshold = interp(v_ego, [0.0, 4.0, 12.0, 25.0], [0.24, 0.30, 0.38, 0.48])
      hold_frames = int(round(interp(v_ego, [0.0, 4.0, 12.0, 25.0], [12.0, 10.0, 8.0, 6.0])))

    if abs(a_target - self.last_a_target) > handoff_threshold:
      self.integrator_hold_frames = max(self.integrator_hold_frames, hold_frames)
    self.last_a_target = a_target

    if self.integrator_hold_frames > 0:
      self.integrator_hold_frames -= 1

    sat_buffer = 0.03
    at_neg_sat = last_output_accel <= (accel_limits[0] + sat_buffer)
    at_pos_sat = last_output_accel >= (accel_limits[1] - sat_buffer)
    sat_pushing_lower = at_neg_sat and error < -0.05
    sat_pushing_upper = at_pos_sat and error > 0.05

    return self.integrator_hold_frames > 0 or sat_pushing_lower or sat_pushing_upper

  def shape_volt_test_tune_integrator(self, pid, error, v_ego):
    if not (self.is_volt and testing_ground.use_2):
      return

    if pid.i * error < 0.0 and abs(error) > 0.05:
      bleed = interp(v_ego, [0.0, 4.0, 12.0, 25.0], [0.82, 0.86, 0.90, 0.94])
      pid.i *= bleed

  def trim_volt_cruise_integrator(self, pid, a_target, error, v_ego, should_stop, has_lead):
    """Release stale negative I during settled open-road speed holding."""
    if not self.is_volt or should_stop or has_lead:
      return
    if v_ego < VOLT_CRUISE_INTEGRATOR_MIN_SPEED:
      return
    if abs(a_target) > VOLT_CRUISE_INTEGRATOR_TARGET_MAX or abs(error) > VOLT_CRUISE_INTEGRATOR_ERROR_MAX:
      return
    if pid.i < 0.0:
      pid.i *= VOLT_CRUISE_INTEGRATOR_LEAK

  def trim_gm_truck_positive_hold_integrator(self, pid, last_output_accel, a_target, error, CS):
    if not self.is_gm_stock_truck or pid.i <= 0.0:
      return
    if last_output_accel <= 0.10:
      return
    light_accel_threshold = float(interp(CS.vEgo, [8.0, 15.0, 25.0], [0.03, 0.06, 0.10]))
    if a_target > light_accel_threshold:
      return
    if CS.vEgo <= NEGATIVE_TARGET_CREEP_GUARD_SPEED and a_target > -NEGATIVE_TARGET_CREEP_GUARD_DECEL:
      return

    authority_mismatch = last_output_accel - max(a_target, 0.0)
    if authority_mismatch <= 0.08 and error > -0.08:
      return

    target_factor = float(interp(a_target, [-0.30, -0.10, -0.02, light_accel_threshold], [0.20, 0.35, 0.60, 0.98]))
    if error < -0.20:
      target_factor *= 0.75
    pid.i *= target_factor

  def trim_gm_truck_negative_hold_integrator(self, pid, last_output_accel, a_target, error, CS):
    if not self.is_gm_stock_truck or pid.i >= -0.02:
      return
    if CS.vEgo < 12.0 or a_target <= -0.85:
      return
    if error <= 0.04:
      return

    authority_mismatch = float(a_target) - float(last_output_accel)
    if authority_mismatch <= 0.10:
      return

    release = float(interp(
      max(authority_mismatch, error),
      [0.10, 0.25, 0.50],
      [0.0008, 0.0020, 0.0040],
    ))
    pid.i = min(0.0, pid.i + release)

  def apply_pedal_long_brake_bias(self, output_accel, a_target, CS):
    if not self.is_gm_pedal_long:
      return output_accel
    if output_accel >= -0.05 or a_target >= -0.80:
      return output_accel
    if CS.vEgo <= 5.0:
      return output_accel

    authority_gap = max(0.0, abs(a_target) - abs(output_accel))
    if self.is_bolt_acc_pedal_friction_car:
      pedal_regen_limit = float(interp(CS.vEgo, BOLT_ACC_PEDAL_REGEN_LIMIT_BP, BOLT_ACC_PEDAL_REGEN_LIMIT_V))
      bias = get_bolt_acc_pedal_friction_bias(output_accel, a_target, CS.vEgo)
      floor = get_bolt_acc_pedal_friction_floor(a_target, CS.vEgo, pedal_regen_limit)
      if floor is not None:
        bias = max(bias, output_accel - floor)
      return output_accel - float(max(bias, 0.0))

    if authority_gap <= 0.40:
      return output_accel

    speed_factor = interp(CS.vEgo, [5.0, 12.0, 25.0], [0.0, 0.7, 1.0])
    max_bias = interp(abs(a_target), [0.8, 2.0, 3.5], [0.0, 0.10, 0.20])
    bias = min(authority_gap * 0.12, max_bias) * speed_factor
    return output_accel - float(bias)

  def get_longitudinal_feedforward(self, feedforward_gain, last_output_accel, a_target, v_ego):
    feedforward = a_target * feedforward_gain
    if not self.is_bolt_acc_pedal_friction_car or a_target >= 0.0:
      return feedforward

    pedal_regen_limit = float(interp(v_ego, BOLT_ACC_PEDAL_REGEN_LIMIT_BP, BOLT_ACC_PEDAL_REGEN_LIMIT_V))
    effective_gain = get_bolt_acc_pedal_feedforward_gain(
      feedforward_gain, a_target, v_ego, pedal_regen_limit, last_output_accel,
    )
    return a_target * effective_gain
