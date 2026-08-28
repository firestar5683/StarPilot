import numpy as np


HONDA_HRV_3G_FAR_FOLLOW_BRAKE_SLEW_RATE = 3.0
HONDA_HRV_3G_FAR_FOLLOW_RELEASE_SLEW_RATE = 2.0
HONDA_CRV_5G_FAR_FOLLOW_BRAKE_SLEW_RATE = 1.5
HONDA_CRV_5G_FAR_FOLLOW_RELEASE_SLEW_RATE = 1.0
HONDA_ACCORD_FAR_FOLLOW_BRAKE_SLEW_RATE = 2.0
HONDA_ACCORD_FAR_FOLLOW_RELEASE_SLEW_RATE = 1.5
HONDA_HRV_3G_UNTRACKED_SLOW_LEAD_DECEL_SCALE = 1.35
HONDA_ACCORD_LEAD_DEPART_ACCEL_HOLD_MAX_ACCEL = 0.85
HONDA_ACCORD_LEAD_DEPART_ACCEL_ASSIST = 0.25
HONDA_ACCORD_STOP_GO_MAX_EGO_SPEED = 4.5
HONDA_ACCORD_STOP_GO_MIN_DISTANCE = 5.5
HONDA_ACCORD_STOP_GO_MAX_DISTANCE = 14.0
HONDA_ACCORD_STOP_GO_MAX_LEAD_SPEED = 4.5
HONDA_ACCORD_STOP_GO_MIN_LEAD_SPEED = 0.4
HONDA_ACCORD_STOP_GO_MAX_LEAD_BRAKE = 0.25
HONDA_ACCORD_STOP_GO_MAX_LATERAL_OFFSET = 1.25
HONDA_ACCORD_STOP_GO_MIN_MODEL_PROB = 0.95
HONDA_ACCORD_STOP_GO_ACCEL_RISE_RATE = 4.0
HONDA_ACCORD_11G_CRUISE_ACCEL_MAX_BP = (0.0, 10.0, 25.0, 40.0)
HONDA_ACCORD_11G_CRUISE_ACCEL_MAX_V = (1.6, 1.2, 0.8, 0.6)
HONDA_ACCORD_11G_TOTAL_ACCEL_MAX_BP = (20.0, 40.0)
HONDA_ACCORD_11G_TOTAL_ACCEL_MAX_V = (1.7, 3.2)
HONDA_ACCORD_11G_THROTTLE_PROB_THRESHOLD = 0.4
HONDA_ACCORD_11G_MIN_ALLOW_THROTTLE_SPEED = 2.5
HONDA_ACCORD_11G_MIN_ACTION_DELAY = 0.3
HONDA_ACCORD_11G_ACCEL_CLIP_SLEW_STEP = 0.05
HYUNDAI_ELANTRA_LEAD_FOLLOW_JERK_SCALE = 1.25
GENESIS_GV70_ELECTRIFIED_LEAD_FOLLOW_JERK_SCALE = 1.75
FORD_LIGHTNING_LEAD_FOLLOW_JERK_SCALE = 1.35
HONDA_CRV_5G_LEAD_FOLLOW_JERK_SCALE = 1.35
GM_SILVERADO_EARLY_FOLLOW_MIN_EGO_SPEED = 18.0
GM_SILVERADO_EARLY_FOLLOW_MAX_DISTANCE = 130.0
GM_SILVERADO_EARLY_FOLLOW_MIN_MODEL_PROB = 0.85
GM_SILVERADO_EARLY_FOLLOW_MAX_LATERAL_OFFSET = 1.2
DEFAULT_FOLLOW_PREBRAKE_MIN_HEADWAY = 1.25
GM_SILVERADO_FOLLOW_PREBRAKE_MIN_HEADWAY = 1.25
FORD_LIGHTNING_FOLLOW_PREBRAKE_MIN_HEADWAY = 0.75
FORD_LIGHTNING_TRACKED_LEAD_CATCHUP_MIN_HEADWAY_MARGIN = 0.10
FORD_LIGHTNING_TRACKED_LEAD_CATCHUP_FULL_HEADWAY_MARGIN = 0.25
FORD_LIGHTNING_TRACKED_LEAD_CATCHUP_BIAS_GAIN = 1.0
FORD_LIGHTNING_STOPPED_RADAR_FOLLOW_MAX_EGO_SPEED = 4.5
FORD_LIGHTNING_STOPPED_RADAR_FOLLOW_MAX_DISTANCE = 18.0
FORD_LIGHTNING_STOPPED_RADAR_FOLLOW_MAX_LEAD_SPEED = 2.0
FORD_LIGHTNING_STOPPED_RADAR_FOLLOW_MAX_LATERAL_OFFSET = 1.25
HONDA_CRV_5G_TRACKED_LEAD_CATCHUP_MIN_HEADWAY_MARGIN = 0.10
HONDA_CRV_5G_TRACKED_LEAD_CATCHUP_FULL_HEADWAY_MARGIN = 0.35
HONDA_CRV_5G_TRACKED_LEAD_CATCHUP_BIAS_GAIN = 1.25
HONDA_CRV_5G_TRACKED_LEAD_CATCHUP_BIAS_CAP = 65.0
HONDA_CRV_5G_TRACKED_LEAD_CATCHUP_SPEED_RANGE = (10.0, 18.0)
HONDA_CRV_5G_TRACKED_LEAD_CATCHUP_FADE_MARGINS = (0.75, 6.5)
HONDA_CRV_5G_TRACKED_LEAD_CATCHUP_CRUISE_ERROR_FULL = 0.75
FORD_LIGHTNING_FAR_FOLLOW_BRAKE_SLEW_RATE = 2.5
FORD_LIGHTNING_FAR_FOLLOW_RELEASE_SLEW_RATE = 1.75
FORD_LIGHTNING_STANDSTILL_GUARD_DISTANCE_MARGIN = 5.0
FORD_LIGHTNING_STANDSTILL_GUARD_MAX_LEAD_SPEED = 0.60
FORD_LIGHTNING_GAP_SETTLE_MAX_EXTRA_GAP = 3.0
TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MAX_EGO_SPEED = 2.0
TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MAX_LEAD_SPEED = 0.45
TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MAX_LEAD_DELTA = 0.35
TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MAX_LEAD_ACCEL = 0.35
TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MIN_MODEL_PROB = 0.95
TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MAX_LATERAL_OFFSET = 1.75
TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MIN_BRAKE = 0.18
TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MAX_BRAKE = 0.32
TOYOTA_RAV4_TSS2_EARLY_LEAD_MIN_EGO_SPEED = 12.0
TOYOTA_RAV4_TSS2_EARLY_LEAD_MIN_MODEL_PROB = 0.85
TOYOTA_RAV4_TSS2_EARLY_LEAD_MAX_LATERAL_OFFSET = 1.2
TOYOTA_RAV4_TSS2_EARLY_LEAD_MIN_DISTANCE = 45.0
TOYOTA_RAV4_TSS2_EARLY_LEAD_MAX_DISTANCE = 105.0
TOYOTA_RAV4_TSS2_EARLY_LEAD_MIN_CLOSING_SPEED = 4.0
TOYOTA_RAV4_TSS2_EARLY_LEAD_MIN_BRAKE = 0.8
TOYOTA_RAV4_TSS2_EARLY_LEAD_MAX_BRAKE = 2.0
TOYOTA_RAV4_TSS2_EARLY_LEAD_MAX_DECEL = 0.5
TOYOTA_RAV4_TSS2_RADAR_FOLLOW_MIN_SPEED = 5.0
TOYOTA_RAV4_TSS2_RADAR_FOLLOW_MIN_CLOSING_SPEED = 0.75
TOYOTA_RAV4_TSS2_RADAR_FOLLOW_MIN_DISTANCE = 70.0
TOYOTA_RAV4_TSS2_RADAR_FOLLOW_MAX_DISTANCE = 100.0
TOYOTA_RAV4_TSS2_RADAR_FOLLOW_DISTANCE_TIME = 4.5
TOYOTA_RAV4_TSS2_RADAR_FOLLOW_DISTANCE_OFFSET = 32.0
TOYOTA_RAV4_TSS2_RADAR_FOLLOW_MAX_LATERAL_OFFSET = 1.75
TOYOTA_RAV4_TSS2_FAR_FOLLOW_BRAKE_SLEW_RATE = 2.5
TOYOTA_RAV4_TSS2_FAR_FOLLOW_RELEASE_SLEW_RATE = 1.75
TOYOTA_RAV4_TSS2_LEAD_DEPART_ACCEL_HOLD_MAX_ACCEL = 0.70
TOYOTA_RAV4_TSS2_LEAD_DEPART_ACCEL_ASSIST = 0.20
TOYOTA_RAV4_TSS2_LEAD_CREEP_MIN_LEAD_SPEED = 0.15
TOYOTA_RAV4_TSS2_LEAD_CREEP_MIN_LEAD_ACCEL = -0.05
TOYOTA_PRIUS_STOPPED_LEAD_OBSTACLE_BIAS_M = 1.5
TOYOTA_PRIUS_STOPPED_LEAD_MAX_EGO_SPEED = 22.0
TOYOTA_PRIUS_STOPPED_LEAD_MAX_SPEED = 1.0
TOYOTA_PRIUS_STOPPED_LEAD_MIN_CLOSING_SPEED = 0.15
TOYOTA_PRIUS_STOPPED_LEAD_MAX_DISTANCE = 80.0
TOYOTA_PRIUS_STOPPED_LEAD_RAMP_DISTANCE = 10.0
TOYOTA_PRIUS_STOPPED_LEAD_MAX_LATERAL_OFFSET = 1.75
HONDA_CRV_5G_STOPPED_LEAD_OBSTACLE_BIAS_M = 1.0
HONDA_CRV_5G_STOPPED_LEAD_MAX_EGO_SPEED = 22.0
HONDA_CRV_5G_STOPPED_LEAD_MAX_SPEED = 1.0
HONDA_CRV_5G_STOPPED_LEAD_MIN_CLOSING_SPEED = 0.15
HONDA_CRV_5G_STOPPED_LEAD_MAX_DISTANCE = 80.0
HONDA_CRV_5G_STOPPED_LEAD_RAMP_DISTANCE = 10.0
HONDA_CRV_5G_STOPPED_LEAD_MAX_LATERAL_OFFSET = 1.75
HONDA_CRV_5G_LOW_SPEED_STOP_MAX_EGO_SPEED = 4.5
HONDA_CRV_5G_LOW_SPEED_STOP_MAX_LEAD_SPEED = 0.5
HONDA_CRV_5G_LOW_SPEED_STOP_MIN_MODEL_PROB = 0.99
HONDA_CRV_5G_LOW_SPEED_STOP_MAX_DISTANCE = 12.0
HONDA_CRV_5G_LOW_SPEED_STOP_MIN_DISTANCE = 6.5
HONDA_CRV_5G_LOW_SPEED_STOP_MIN_CLOSING_SPEED = 0.15
HONDA_CRV_5G_LOW_SPEED_STOP_MAX_LEAD_ACCEL = 0.25
HONDA_CRV_5G_LOW_SPEED_STOP_MAX_DECEL = 0.45
HONDA_CRV_5G_LOW_SPEED_STOP_MIN_DECEL = 0.12
HONDA_CRV_5G_GAP_SETTLE_MAX_EXTRA_GAP = 7.0
HONDA_CRV_5G_GUARD_DISTANCE_MARGIN = 1.5
HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MIN_EGO_SPEED = 8.0
HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MAX_EGO_SPEED = 22.0
HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MAX_LEAD_SPEED = 8.0
HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MIN_CLOSING_SPEED = 7.0
HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MAX_TTC = 8.0
HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MAX_DISTANCE_TIME = 5.0
HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MIN_MODEL_PROB = 0.80
HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MAX_LATERAL_OFFSET = 1.0
TOYOTA_CAMRY_TSS2_FORCE_STOP_HANDOFF_M = 4.5
# The Camry's force-stop path otherwise consumes the model endpoint before the
# normal MPC stop-distance margin can be applied. Keep it within the forward
# offset range exposed by the Force Stop setting.
TOYOTA_CAMRY_TSS2_FORCE_STOP_DISTANCE_BIAS_M = 6.0
DEFAULT_FORCE_STOP_HANDOFF_M = 6.0
HYUNDAI_SANTA_FE_2022_FORCE_STOP_REANCHOR_SPEED_TOLERANCE = 0.25
HYUNDAI_SANTA_FE_2022_FORCE_STOP_LOW_SPEED_HOLD = 2.5
KIA_CARNIVAL_2025_STOP_SIGN_LOW_SPEED_HOLD = 0.75


def is_honda_accord_11g(CP):
  return (
    getattr(CP, "brand", "") == "honda" and
    str(getattr(CP, "carFingerprint", "")) == "HONDA_ACCORD_11G"
  )


def get_honda_accord_11g_cruise_accel_max(CP, v_ego):
  """Return the validated Accord 11G cruise acceleration ceiling."""
  if not is_honda_accord_11g(CP):
    return None
  return float(np.interp(v_ego, HONDA_ACCORD_11G_CRUISE_ACCEL_MAX_BP, HONDA_ACCORD_11G_CRUISE_ACCEL_MAX_V))


def get_honda_accord_11g_total_accel_max(CP, v_ego):
  """Return the validated Accord 11G combined longitudinal/lateral envelope."""
  if not is_honda_accord_11g(CP):
    return None
  return float(np.interp(v_ego, HONDA_ACCORD_11G_TOTAL_ACCEL_MAX_BP, HONDA_ACCORD_11G_TOTAL_ACCEL_MAX_V))


def get_honda_accord_11g_throttle_policy(CP):
  if not is_honda_accord_11g(CP):
    return None
  return HONDA_ACCORD_11G_THROTTLE_PROB_THRESHOLD, HONDA_ACCORD_11G_MIN_ALLOW_THROTTLE_SPEED


def get_honda_accord_11g_min_action_delay(CP):
  return HONDA_ACCORD_11G_MIN_ACTION_DELAY if is_honda_accord_11g(CP) else None


def get_honda_accord_11g_accel_clip_slew_step(CP):
  return HONDA_ACCORD_11G_ACCEL_CLIP_SLEW_STEP if is_honda_accord_11g(CP) else None


def get_honda_accord_11g_reduction_only_v_cruise(CP, stock_v_cruise, starpilot_v_cruise):
  """Keep StarPilot as a reduction-only speed constraint for the Accord 11G."""
  if not is_honda_accord_11g(CP):
    return None
  if np.isfinite(starpilot_v_cruise) and starpilot_v_cruise >= 0.0:
    return float(min(stock_v_cruise, starpilot_v_cruise))
  return float(stock_v_cruise)


def get_toyota_prius_stopped_lead_obstacle_bias(CP, lead, v_ego):
  """Move the ordinary Prius stopped-lead target back without touching stop targets."""
  if (
    getattr(CP, "brand", "") != "toyota" or
    str(getattr(CP, "carFingerprint", "")) != "TOYOTA_PRIUS" or
    lead is None or not bool(getattr(lead, "status", False)) or
    float(v_ego) <= 0.0 or float(v_ego) > TOYOTA_PRIUS_STOPPED_LEAD_MAX_EGO_SPEED or
    float(getattr(lead, "vLead", 0.0)) > TOYOTA_PRIUS_STOPPED_LEAD_MAX_SPEED or
    abs(float(getattr(lead, "yRel", 0.0))) > TOYOTA_PRIUS_STOPPED_LEAD_MAX_LATERAL_OFFSET
  ):
    return 0.0

  distance = float(getattr(lead, "dRel", float("inf")))
  closing_speed = float(v_ego) - float(getattr(lead, "vLead", 0.0))
  if (
    distance <= 0.0 or distance > TOYOTA_PRIUS_STOPPED_LEAD_MAX_DISTANCE or
    closing_speed < TOYOTA_PRIUS_STOPPED_LEAD_MIN_CLOSING_SPEED
  ):
    return 0.0

  strength = np.clip(
    (TOYOTA_PRIUS_STOPPED_LEAD_MAX_DISTANCE - distance) /
    (TOYOTA_PRIUS_STOPPED_LEAD_MAX_DISTANCE - TOYOTA_PRIUS_STOPPED_LEAD_RAMP_DISTANCE),
    0.0, 1.0,
  )
  bias = TOYOTA_PRIUS_STOPPED_LEAD_OBSTACLE_BIAS_M * strength
  return float(min(bias, max(distance - 0.5, 0.0)))


def is_honda_crv_5g(CP):
  return (
    getattr(CP, "brand", "") == "honda" and
    str(getattr(CP, "carFingerprint", "")) == "HONDA_CRV_5G"
  )


def is_honda_crv_5g_early_radar_follow_lead(CP, lead, v_ego):
  """Admit a credible, rapidly closing CR-V radar lead before model tracking catches up."""
  if (
    not is_honda_crv_5g(CP) or
    lead is None or not bool(getattr(lead, "status", False)) or
    not bool(getattr(lead, "radar", False)) or
    not HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MIN_EGO_SPEED <= float(v_ego) <= \
      HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MAX_EGO_SPEED or
    float(getattr(lead, "modelProb", 0.0)) < HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MIN_MODEL_PROB or
    abs(float(getattr(lead, "yRel", 0.0))) > HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MAX_LATERAL_OFFSET
  ):
    return False

  lead_speed = max(float(getattr(lead, "vLead", 0.0)), 0.0)
  closing_speed = float(v_ego) - lead_speed
  distance = float(getattr(lead, "dRel", float("inf")))
  if (
    lead_speed > HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MAX_LEAD_SPEED or
    closing_speed < HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MIN_CLOSING_SPEED or
    distance <= 0.0 or
    distance > HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MAX_DISTANCE_TIME * float(v_ego)
  ):
    return False

  return distance / max(closing_speed, 0.1) <= HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MAX_TTC


def get_honda_crv_5g_early_radar_follow_cap(CP, lead, v_ego, accel_min):
  """Start a mild CR-V radar response before the normal lead handoff."""
  if not is_honda_crv_5g_early_radar_follow_lead(CP, lead, v_ego):
    return None

  lead_speed = max(float(getattr(lead, "vLead", 0.0)), 0.0)
  closing_speed = float(v_ego) - lead_speed
  distance = float(getattr(lead, "dRel", float("inf")))
  ttc = distance / max(closing_speed, 0.1)
  urgency = float(np.clip(
    (HONDA_CRV_5G_RADAR_EARLY_FOLLOW_MAX_TTC - ttc) / 4.0,
    0.0, 1.0,
  ))
  cap = 0.25 + 0.25 * urgency
  return max(float(accel_min), -cap)


def get_honda_crv_5g_stopped_lead_obstacle_bias(CP, lead, v_ego):
  """Bring the CR-V's vision stopped-lead target in without changing stops."""
  if (
    not is_honda_crv_5g(CP) or
    lead is None or not bool(getattr(lead, "status", False)) or
    float(v_ego) <= 0.0 or float(v_ego) > HONDA_CRV_5G_STOPPED_LEAD_MAX_EGO_SPEED or
    float(getattr(lead, "vLead", 0.0)) > HONDA_CRV_5G_STOPPED_LEAD_MAX_SPEED or
    bool(getattr(lead, "radar", False)) or
    float(getattr(lead, "modelProb", 0.0)) < 0.95 or
    abs(float(getattr(lead, "yRel", 0.0))) > HONDA_CRV_5G_STOPPED_LEAD_MAX_LATERAL_OFFSET
  ):
    return 0.0

  distance = float(getattr(lead, "dRel", float("inf")))
  closing_speed = float(v_ego) - float(getattr(lead, "vLead", 0.0))
  if (
    distance <= 0.0 or distance > HONDA_CRV_5G_STOPPED_LEAD_MAX_DISTANCE or
    closing_speed < HONDA_CRV_5G_STOPPED_LEAD_MIN_CLOSING_SPEED
  ):
    return 0.0

  strength = np.clip(
    (HONDA_CRV_5G_STOPPED_LEAD_MAX_DISTANCE - distance) /
    (HONDA_CRV_5G_STOPPED_LEAD_MAX_DISTANCE - HONDA_CRV_5G_STOPPED_LEAD_RAMP_DISTANCE),
    0.0, 1.0,
  )
  bias = HONDA_CRV_5G_STOPPED_LEAD_OBSTACLE_BIAS_M * strength
  return float(min(bias, max(distance - 0.5, 0.0)))


def get_honda_crv_5g_low_speed_stopped_lead_cap(CP, lead, v_ego, accel_min):
  """Bleed a CR-V crawl into the normal standstill gap without a hard jab."""
  if (
    not is_honda_crv_5g(CP) or
    lead is None or not bool(getattr(lead, "status", False)) or
    bool(getattr(lead, "radar", False)) or
    float(getattr(lead, "modelProb", 0.0)) < HONDA_CRV_5G_LOW_SPEED_STOP_MIN_MODEL_PROB or
    float(v_ego) <= 0.0 or float(v_ego) > HONDA_CRV_5G_LOW_SPEED_STOP_MAX_EGO_SPEED
  ):
    return None

  lead_speed = max(float(getattr(lead, "vLead", 0.0)), 0.0)
  distance = float(getattr(lead, "dRel", float("inf")))
  if (
    lead_speed > HONDA_CRV_5G_LOW_SPEED_STOP_MAX_LEAD_SPEED or
    float(getattr(lead, "aLeadK", 0.0)) > HONDA_CRV_5G_LOW_SPEED_STOP_MAX_LEAD_ACCEL or
    distance < HONDA_CRV_5G_LOW_SPEED_STOP_MIN_DISTANCE or
    distance > HONDA_CRV_5G_LOW_SPEED_STOP_MAX_DISTANCE or
    float(v_ego) - lead_speed < HONDA_CRV_5G_LOW_SPEED_STOP_MIN_CLOSING_SPEED or
    abs(float(getattr(lead, "yRel", 0.0))) > HONDA_CRV_5G_STOPPED_LEAD_MAX_LATERAL_OFFSET
  ):
    return None

  available_gap = max(distance - 6.0, 1.0)
  required_decel = float(v_ego) ** 2 / (2.0 * available_gap)
  decel = float(np.clip(
    required_decel * 0.85,
    HONDA_CRV_5G_LOW_SPEED_STOP_MIN_DECEL,
    HONDA_CRV_5G_LOW_SPEED_STOP_MAX_DECEL,
  ))
  return max(float(accel_min), -decel)


def allow_honda_crv_5g_vision_gap_settle(CP):
  return is_honda_crv_5g(CP)


def get_standstill_gap_settle_max_extra_gap(CP):
  if is_honda_crv_5g(CP):
    return HONDA_CRV_5G_GAP_SETTLE_MAX_EXTRA_GAP
  if is_ford_f150_lightning(CP):
    return FORD_LIGHTNING_GAP_SETTLE_MAX_EXTRA_GAP
  return 1.5


def get_standstill_stopped_lead_guard_distance_margin(CP):
  if is_honda_crv_5g(CP):
    return HONDA_CRV_5G_GUARD_DISTANCE_MARGIN
  if is_ford_f150_lightning(CP):
    return FORD_LIGHTNING_STANDSTILL_GUARD_DISTANCE_MARGIN
  return 3.0


def get_standstill_stopped_lead_guard_max_lead_speed(CP, default):
  if is_ford_f150_lightning(CP):
    return FORD_LIGHTNING_STANDSTILL_GUARD_MAX_LEAD_SPEED
  return float(default)


def get_tracked_lead_catchup_headway_margins(CP):
  if is_honda_crv_5g(CP):
    return (
      HONDA_CRV_5G_TRACKED_LEAD_CATCHUP_MIN_HEADWAY_MARGIN,
      HONDA_CRV_5G_TRACKED_LEAD_CATCHUP_FULL_HEADWAY_MARGIN,
    )
  if is_ford_f150_lightning(CP):
    return (
      FORD_LIGHTNING_TRACKED_LEAD_CATCHUP_MIN_HEADWAY_MARGIN,
      FORD_LIGHTNING_TRACKED_LEAD_CATCHUP_FULL_HEADWAY_MARGIN,
    )
  return None


def get_tracked_lead_catchup_bias_gain(CP):
  if is_honda_crv_5g(CP):
    return HONDA_CRV_5G_TRACKED_LEAD_CATCHUP_BIAS_GAIN
  if is_ford_f150_lightning(CP):
    return FORD_LIGHTNING_TRACKED_LEAD_CATCHUP_BIAS_GAIN
  return None


def get_tracked_lead_catchup_bias_cap(CP):
  if is_honda_crv_5g(CP):
    return HONDA_CRV_5G_TRACKED_LEAD_CATCHUP_BIAS_CAP
  return None


def get_tracked_lead_catchup_speed_range(CP):
  if is_honda_crv_5g(CP):
    return HONDA_CRV_5G_TRACKED_LEAD_CATCHUP_SPEED_RANGE
  return None


def get_tracked_lead_catchup_fade_margins(CP):
  if is_honda_crv_5g(CP):
    return HONDA_CRV_5G_TRACKED_LEAD_CATCHUP_FADE_MARGINS
  return None


def get_tracked_lead_catchup_cruise_error_full(CP):
  if is_honda_crv_5g(CP):
    return HONDA_CRV_5G_TRACKED_LEAD_CATCHUP_CRUISE_ERROR_FULL
  return None


def is_ford_f150_lightning(CP):
  return (
    getattr(CP, "brand", "") == "ford" and
    str(getattr(CP, "carFingerprint", "")) == "FORD_F_150_LIGHTNING_MK1"
  )


def is_ford_f150_lightning_stopped_radar_follow_lead(CP, lead, v_ego):
  """Keep a credible stopped radar lead active after the CEM model horizon collapses."""
  if (
    not is_ford_f150_lightning(CP) or
    lead is None or not bool(getattr(lead, "status", False)) or
    not bool(getattr(lead, "radar", False)) or
    float(v_ego) < 0.0 or
    float(v_ego) > FORD_LIGHTNING_STOPPED_RADAR_FOLLOW_MAX_EGO_SPEED or
    float(getattr(lead, "dRel", float("inf"))) > FORD_LIGHTNING_STOPPED_RADAR_FOLLOW_MAX_DISTANCE or
    max(float(getattr(lead, "vLead", 0.0)), 0.0) > FORD_LIGHTNING_STOPPED_RADAR_FOLLOW_MAX_LEAD_SPEED or
    abs(float(getattr(lead, "yRel", 0.0))) > FORD_LIGHTNING_STOPPED_RADAR_FOLLOW_MAX_LATERAL_OFFSET
  ):
    return False

  return float(getattr(lead, "dRel", 0.0)) > 0.0


def is_toyota_rav4_tss2_post_departure_tune(CP):
  """Identify RAV4 TSS2 variants that need normal catch-up caps after departure."""
  return (
    getattr(CP, "brand", "") == "toyota" and
    str(getattr(CP, "carFingerprint", "")) in ("TOYOTA_RAV4_TSS2", "TOYOTA_RAV4_TSS2_2023")
  )


def get_toyota_rav4_tss2_lead_departure_tune(CP):
  if is_toyota_rav4_tss2_post_departure_tune(CP):
    return (
      TOYOTA_RAV4_TSS2_LEAD_DEPART_ACCEL_HOLD_MAX_ACCEL,
      TOYOTA_RAV4_TSS2_LEAD_DEPART_ACCEL_ASSIST,
    )
  return None


def get_toyota_rav4_tss2_lead_creep_tune(CP):
  """Allow a credible RAV4 vision lead to release the standstill hold early."""
  if is_toyota_rav4_tss2_post_departure_tune(CP):
    return (
      TOYOTA_RAV4_TSS2_LEAD_CREEP_MIN_LEAD_SPEED,
      TOYOTA_RAV4_TSS2_LEAD_CREEP_MIN_LEAD_ACCEL,
    )
  return None


def get_toyota_rav4_tss2_early_lead_cap(CP, lead, v_ego, accel_min):
  """Start a mild RAV4 coast/brake response before a hard lead approach."""
  if (
    not is_toyota_rav4_tss2_post_departure_tune(CP) or
    lead is None or not bool(getattr(lead, "status", False)) or
    bool(getattr(lead, "radar", False)) or
    float(v_ego) < TOYOTA_RAV4_TSS2_EARLY_LEAD_MIN_EGO_SPEED or
    float(getattr(lead, "modelProb", 0.0)) < TOYOTA_RAV4_TSS2_EARLY_LEAD_MIN_MODEL_PROB or
    abs(float(getattr(lead, "yRel", 0.0))) > TOYOTA_RAV4_TSS2_EARLY_LEAD_MAX_LATERAL_OFFSET
  ):
    return None

  distance = float(getattr(lead, "dRel", float("inf")))
  lead_speed = max(float(getattr(lead, "vLead", 0.0)), 0.0)
  closing_speed = float(v_ego) - lead_speed
  lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
  if (
    not TOYOTA_RAV4_TSS2_EARLY_LEAD_MIN_DISTANCE <= distance <= TOYOTA_RAV4_TSS2_EARLY_LEAD_MAX_DISTANCE or
    closing_speed < TOYOTA_RAV4_TSS2_EARLY_LEAD_MIN_CLOSING_SPEED or
    lead_brake < TOYOTA_RAV4_TSS2_EARLY_LEAD_MIN_BRAKE
  ):
    return None

  distance_factor = np.clip(
    (TOYOTA_RAV4_TSS2_EARLY_LEAD_MAX_DISTANCE - distance) /
    (TOYOTA_RAV4_TSS2_EARLY_LEAD_MAX_DISTANCE - TOYOTA_RAV4_TSS2_EARLY_LEAD_MIN_DISTANCE),
    0.0, 1.0,
  )
  closing_factor = np.clip((closing_speed - 4.0) / 6.0, 0.0, 1.0)
  brake_factor = np.clip(
    (lead_brake - TOYOTA_RAV4_TSS2_EARLY_LEAD_MIN_BRAKE) /
    (TOYOTA_RAV4_TSS2_EARLY_LEAD_MAX_BRAKE - TOYOTA_RAV4_TSS2_EARLY_LEAD_MIN_BRAKE),
    0.0, 1.0,
  )
  confidence_factor = np.clip(
    (float(getattr(lead, "modelProb", 0.0)) - TOYOTA_RAV4_TSS2_EARLY_LEAD_MIN_MODEL_PROB) / 0.13,
    0.0, 1.0,
  )
  decel = 0.10 + 0.20 * distance_factor + 0.10 * closing_factor + 0.10 * brake_factor
  decel *= 0.75 + 0.25 * confidence_factor
  return max(float(accel_min), -min(TOYOTA_RAV4_TSS2_EARLY_LEAD_MAX_DECEL, decel))


def is_toyota_rav4_tss2_radar_follow_lead(CP, lead, v_ego):
  """Keep a credible RAV4 radar lead active through model-horizon dropouts."""
  if (
    not is_toyota_rav4_tss2_post_departure_tune(CP) or
    lead is None or not bool(getattr(lead, "status", False)) or
    not bool(getattr(lead, "radar", False)) or
    float(v_ego) < TOYOTA_RAV4_TSS2_RADAR_FOLLOW_MIN_SPEED or
    abs(float(getattr(lead, "yRel", 0.0))) > TOYOTA_RAV4_TSS2_RADAR_FOLLOW_MAX_LATERAL_OFFSET
  ):
    return False

  lead_speed = max(float(getattr(lead, "vLead", 0.0)), 0.0)
  closing_speed = float(v_ego) - lead_speed
  distance_limit = float(np.clip(
    TOYOTA_RAV4_TSS2_RADAR_FOLLOW_DISTANCE_OFFSET +
    TOYOTA_RAV4_TSS2_RADAR_FOLLOW_DISTANCE_TIME * float(v_ego),
    TOYOTA_RAV4_TSS2_RADAR_FOLLOW_MIN_DISTANCE,
    TOYOTA_RAV4_TSS2_RADAR_FOLLOW_MAX_DISTANCE,
  ))
  return (
    float(getattr(lead, "dRel", float("inf"))) <= distance_limit and
    closing_speed >= TOYOTA_RAV4_TSS2_RADAR_FOLLOW_MIN_CLOSING_SPEED
  )


def allow_radar_standstill_gap_settle(CP):
  """Keep the generic stopped-lead gap nudge out of the early RAV4 TSS2 path."""
  return not (
    getattr(CP, "brand", "") == "toyota" and
    str(getattr(CP, "carFingerprint", "")) == "TOYOTA_RAV4_TSS2"
  )


def get_far_follow_output_slew_rates(CP):
  if CP.brand == "honda" and str(CP.carFingerprint) == "HONDA_ACCORD":
    return (
      HONDA_ACCORD_FAR_FOLLOW_BRAKE_SLEW_RATE,
      HONDA_ACCORD_FAR_FOLLOW_RELEASE_SLEW_RATE,
    )
  if CP.brand == "honda" and str(CP.carFingerprint) == "HONDA_HRV_3G":
    return (
      HONDA_HRV_3G_FAR_FOLLOW_BRAKE_SLEW_RATE,
      HONDA_HRV_3G_FAR_FOLLOW_RELEASE_SLEW_RATE,
    )
  if is_honda_crv_5g(CP):
    return (
      HONDA_CRV_5G_FAR_FOLLOW_BRAKE_SLEW_RATE,
      HONDA_CRV_5G_FAR_FOLLOW_RELEASE_SLEW_RATE,
    )
  if is_toyota_rav4_tss2_post_departure_tune(CP):
    return (
      TOYOTA_RAV4_TSS2_FAR_FOLLOW_BRAKE_SLEW_RATE,
      TOYOTA_RAV4_TSS2_FAR_FOLLOW_RELEASE_SLEW_RATE,
    )
  if is_ford_f150_lightning(CP):
    return (
      FORD_LIGHTNING_FAR_FOLLOW_BRAKE_SLEW_RATE,
      FORD_LIGHTNING_FAR_FOLLOW_RELEASE_SLEW_RATE,
    )
  return 0.0, 0.0


def get_untracked_slow_lead_decel_scale(CP):
  if CP.brand == "honda" and str(CP.carFingerprint) == "HONDA_HRV_3G":
    return HONDA_HRV_3G_UNTRACKED_SLOW_LEAD_DECEL_SCALE
  return 1.0


def get_lead_follow_jerk_scale(CP):
  """Spread the lead-source transition for cars with a sharp vision-lead handoff."""
  if getattr(CP, "brand", "") == "hyundai" and str(getattr(CP, "carFingerprint", "")) == "HYUNDAI_ELANTRA_2021":
    return HYUNDAI_ELANTRA_LEAD_FOLLOW_JERK_SCALE
  if (
    getattr(CP, "brand", "") == "hyundai" and
    str(getattr(CP, "carFingerprint", "")) == "GENESIS_GV70_ELECTRIFIED_1ST_GEN"
  ):
    return GENESIS_GV70_ELECTRIFIED_LEAD_FOLLOW_JERK_SCALE
  if is_honda_crv_5g(CP):
    return HONDA_CRV_5G_LEAD_FOLLOW_JERK_SCALE
  if is_ford_f150_lightning(CP):
    return FORD_LIGHTNING_LEAD_FOLLOW_JERK_SCALE
  return 1.0


def get_honda_accord_lead_departure_tune(CP):
  if CP.brand == "honda" and str(CP.carFingerprint) == "HONDA_ACCORD":
    return (
      HONDA_ACCORD_LEAD_DEPART_ACCEL_HOLD_MAX_ACCEL,
      HONDA_ACCORD_LEAD_DEPART_ACCEL_ASSIST,
    )
  return None


def get_honda_accord_stop_go_accel_cap(CP, lead, v_ego):
  """Keep the Accord from launching at the full cruise acceleration into a close lead."""
  if (
    CP.brand != "honda" or str(CP.carFingerprint) != "HONDA_ACCORD" or
    lead is None or not bool(getattr(lead, "status", False)) or
    bool(getattr(lead, "radar", False)) or
    float(getattr(lead, "modelProb", 0.0)) < HONDA_ACCORD_STOP_GO_MIN_MODEL_PROB or
    float(v_ego) < 0.0 or float(v_ego) > HONDA_ACCORD_STOP_GO_MAX_EGO_SPEED or
    abs(float(getattr(lead, "yRel", 0.0))) > HONDA_ACCORD_STOP_GO_MAX_LATERAL_OFFSET
  ):
    return None

  distance = float(getattr(lead, "dRel", float("inf")))
  lead_speed = max(float(getattr(lead, "vLead", 0.0)), 0.0)
  lead_delta = lead_speed - float(v_ego)
  lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
  if (
    not HONDA_ACCORD_STOP_GO_MIN_DISTANCE <= distance <= HONDA_ACCORD_STOP_GO_MAX_DISTANCE or
    not HONDA_ACCORD_STOP_GO_MIN_LEAD_SPEED <= lead_speed <= HONDA_ACCORD_STOP_GO_MAX_LEAD_SPEED or
    lead_delta < -0.25 or
    lead_brake > HONDA_ACCORD_STOP_GO_MAX_LEAD_BRAKE
  ):
    return None

  speed_factor = float(np.clip(float(v_ego) / 2.5, 0.0, 1.0))
  gap_factor = float(np.clip(
    (distance - HONDA_ACCORD_STOP_GO_MIN_DISTANCE) /
    max(HONDA_ACCORD_STOP_GO_MAX_DISTANCE - HONDA_ACCORD_STOP_GO_MIN_DISTANCE, 0.1),
    0.0, 1.0,
  ))
  return float(0.90 + 0.12 * speed_factor + 0.10 * gap_factor)


def get_honda_accord_stop_go_accel_rise_rate(CP):
  if CP.brand == "honda" and str(CP.carFingerprint) == "HONDA_ACCORD":
    return HONDA_ACCORD_STOP_GO_ACCEL_RISE_RATE
  return 0.0


def is_gm_silverado_early_follow_lead(CP, lead, v_ego):
  """Admit a credible centered vision lead before it becomes a close lead."""
  if (
    CP.brand != "gm" or str(CP.carFingerprint) not in ("CHEVROLET_SILVERADO", "CHEVROLET_SILVERADO_CC") or
    lead is None or not bool(getattr(lead, "status", False)) or bool(getattr(lead, "radar", False)) or
    float(v_ego) < GM_SILVERADO_EARLY_FOLLOW_MIN_EGO_SPEED or
    float(getattr(lead, "dRel", float("inf"))) > GM_SILVERADO_EARLY_FOLLOW_MAX_DISTANCE or
    float(getattr(lead, "modelProb", 0.0)) < GM_SILVERADO_EARLY_FOLLOW_MIN_MODEL_PROB or
    abs(float(getattr(lead, "yRel", 0.0))) > GM_SILVERADO_EARLY_FOLLOW_MAX_LATERAL_OFFSET
  ):
    return False
  return True


def get_follow_prebrake_min_headway(CP, t_follow):
  """Return the comfort pre-brake floor without changing lead safety distance."""
  if CP.brand == "gm" and str(CP.carFingerprint) in ("CHEVROLET_SILVERADO", "CHEVROLET_SILVERADO_CC"):
    return max(float(t_follow), GM_SILVERADO_FOLLOW_PREBRAKE_MIN_HEADWAY)
  if CP.brand == "ford" and str(CP.carFingerprint) == "FORD_F_150_LIGHTNING_MK1":
    return max(float(t_follow), FORD_LIGHTNING_FOLLOW_PREBRAKE_MIN_HEADWAY)
  return max(float(t_follow), DEFAULT_FOLLOW_PREBRAKE_MIN_HEADWAY)


def get_toyota_sienna_post_departure_restop_cap(CP, lead, v_ego, accel_min,
                                                stop_distance, now_t, departure_latch_until):
  """Re-arm a stop if a Sienna's lead twitches forward and stops again."""
  if (
    CP.brand != "toyota" or str(CP.carFingerprint) != "TOYOTA_SIENNA_4TH_GEN" or
    now_t >= departure_latch_until or lead is None or not lead.status or
    float(v_ego) > TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MAX_EGO_SPEED
  ):
    return None

  lead_radar = bool(getattr(lead, "radar", False))
  lead_prob = float(getattr(lead, "modelProb", 1.0 if lead_radar else 0.0))
  if not lead_radar and lead_prob < TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MIN_MODEL_PROB:
    return None
  if abs(float(getattr(lead, "yRel", 0.0))) > TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MAX_LATERAL_OFFSET:
    return None

  lead_speed = max(float(getattr(lead, "vLead", 0.0)), 0.0)
  lead_delta = lead_speed - float(v_ego)
  lead_accel = float(getattr(lead, "aLeadK", 0.0))
  max_distance = max(float(stop_distance) + 3.0, 4.5)
  if (
    float(getattr(lead, "dRel", float("inf"))) > max_distance or
    lead_speed > TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MAX_LEAD_SPEED or
    lead_delta > TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MAX_LEAD_DELTA or
    lead_accel > TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MAX_LEAD_ACCEL
  ):
    return None

  speed_factor = float(np.clip(float(v_ego) / TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MAX_EGO_SPEED, 0.0, 1.0))
  closing_factor = float(np.clip((float(v_ego) - lead_speed) / 1.5, 0.0, 1.0))
  hold_brake = TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MIN_BRAKE + 0.08 * speed_factor + 0.06 * closing_factor
  brake_floor = -float(np.clip(
    hold_brake,
    TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MIN_BRAKE,
    TOYOTA_SIENNA_POST_DEPARTURE_RESTOP_MAX_BRAKE,
  ))
  return brake_floor if accel_min >= 0.0 else max(float(accel_min), brake_floor)


def get_force_stop_handoff_distance(car_fingerprint):
  """Return the distance at which force-stop control hands off to MPC."""
  if str(car_fingerprint) == "TOYOTA_CAMRY_TSS2":
    return TOYOTA_CAMRY_TSS2_FORCE_STOP_HANDOFF_M
  return DEFAULT_FORCE_STOP_HANDOFF_M


def get_force_stop_distance_bias(car_fingerprint):
  if str(car_fingerprint) == "TOYOTA_CAMRY_TSS2":
    return TOYOTA_CAMRY_TSS2_FORCE_STOP_DISTANCE_BIAS_M
  return 0.0


def get_force_stop_reanchor_speed_tolerance(car_params):
  """Keep the Santa Fe stop distance from reopening after braking begins."""
  if str(getattr(car_params, "carFingerprint", car_params)) == "HYUNDAI_SANTA_FE_2022":
    return HYUNDAI_SANTA_FE_2022_FORCE_STOP_REANCHOR_SPEED_TOLERANCE
  return None


def get_force_stop_low_speed_hold(car_params):
  """Keep a committed Santa Fe stop from releasing while it is still rolling."""
  if str(getattr(car_params, "carFingerprint", car_params)) == "HYUNDAI_SANTA_FE_2022":
    return HYUNDAI_SANTA_FE_2022_FORCE_STOP_LOW_SPEED_HOLD
  return None


def get_stop_sign_low_speed_hold(car_params):
  """Keep a confirmed Carnival stop latched through the final low-speed handoff."""
  if str(getattr(car_params, "carFingerprint", car_params)) == "KIA_CARNIVAL_2025":
    return KIA_CARNIVAL_2025_STOP_SIGN_LOW_SPEED_HOLD
  return None
