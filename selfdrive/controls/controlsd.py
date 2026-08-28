#!/usr/bin/env python3
import math
from numbers import Number

from cereal import car, custom, log
import cereal.messaging as messaging
from openpilot.common.constants import CV
from openpilot.common.params import Params
from openpilot.common.realtime import config_realtime_process, DT_CTRL, Priority, Ratekeeper
from openpilot.common.swaglog import cloudlog

from opendbc.car.car_helpers import interfaces
from opendbc.car.chrysler.values import pacifica_hybrid_aol_stock_acc_mode
from opendbc.car.gm.values import CAR as GM_CAR
from opendbc.car.honda.values import CAR as HONDA_CAR
from opendbc.car.hyundai.values import CAR as HYUNDAI_CAR
from opendbc.car.nissan.values import CAR as NISSAN_CAR
from opendbc.car.vehicle_model import VehicleModel
from openpilot.selfdrive.controls.lib.drive_helpers import (
  MAX_LATERAL_JERK,
  clip_curvature,
  get_kona_non_scc_lateral_active,
  get_lateral_active,
  update_lateral_fault_latch,
)
from openpilot.selfdrive.controls.lib.lane_centering import LaneCenteringController
from openpilot.selfdrive.controls.lib.latcontrol import LatControl
from openpilot.selfdrive.controls.lib.latcontrol_pid import LatControlPID
from openpilot.selfdrive.controls.lib.latcontrol_angle import LatControlAngle, STEER_ANGLE_SATURATION_THRESHOLD
from openpilot.selfdrive.controls.lib.latcontrol_curvature import LatControlCurvature
from openpilot.selfdrive.controls.lib.latcontrol_torque import (
  BOLT_2018_2021_STEER_RATIO_TEST_SCALE,
  LatControlTorque,
  get_bolt_2017_steer_ratio_scale,
  get_honda_accord_steer_ratio_scale,
)
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.selfdrive.car.cruise_state import should_cancel_stock_cruise
from openpilot.selfdrive.modeld.modeld import LAT_SMOOTH_SECONDS, get_car_lateral_smooth_seconds
from openpilot.selfdrive.locationd.helpers import PoseCalibrator, Pose

from openpilot.starpilot.common.starpilot_variables import get_starpilot_toggles
from openpilot.starpilot.controls.lib.neural_network_feedforward import LatControlNNFF

State = log.SelfdriveState.OpenpilotState
LaneChangeState = log.LaneChangeState
LaneChangeDirection = log.LaneChangeDirection
LateralControlMode = car.CarControl.Actuators.LateralControlMode

ACTUATOR_FIELDS = tuple(car.CarControl.Actuators.schema.fields.keys())

# After a smoothed lane change ends, ramp the curvature limits back to stock over this
# time so the final recenter correction is shaped instead of stepping through unclamped.
LANE_CHANGE_SMOOTH_RELEASE_T = 2.0

# Cap on the extra jerk factor granted while the model is unwinding lane-change curvature
# (the arrest and any correction back toward center). Entry gentleness is comfort, but arrest
# speed is a correctness constraint: a slow symmetric cap lets the car glide past the new lane
# center. 0.6 (≈ pace-5 rate) fully tracks the arrest demand seen in logs, 40% below stock.
LANE_CHANGE_ARREST_JERK_FLOOR = 0.6
# The extra unwind authority is proportional to how far the command lags the model
# (rate = lag/tau, a P-pursuit), NOT a fixed fast rate: a boolean-gated floor engages as a
# bang-bang switch right at the maneuver crest — where the slow entry command meets a model
# that already peaked and is diving — snapping the wheel ~2 deg in 0.2 s (lanechange1/2
# rlogs 2026-07-17). With pursuit, lag ~0 at the crest so the rate crosses zero smoothly,
# and noise-scale lag inside the deadband gets no boost (kills the fast-down/slow-up sawtooth).
LANE_CHANGE_ARREST_PURSUIT_TAU = 0.2   # s
LANE_CHANGE_ARREST_GAP_DEADBAND = 5e-5  # 1/m
LANE_CHANGE_ARREST_RISE_TAU = 0.2

# Low-speed turn-intent curvature hold. Approaching a turn with the blinker on, the
# model's time-based plan collapses as the car slows to a stop: desiredCurvature decays
# to zero, the controller actively unwinds the wheel at the intersection, and on
# pull-away it re-winds too late — the car goes wide (pauseturn rlog 2026-07-13).
# The hold ratchets up on the blinker-matching model command below the release speed
# and floors the command magnitude afterwards. Below the hard speed the floor is firm;
# between hard and release speed it decays toward the model's sustained demand, so a
# transient model dip barely sags it while a genuine end-of-turn unwind or an aborted
# turn still drains it in a few seconds. Retention deliberately does NOT depend on the
# blinker (the stalk auto-cancels during the stop in the log), on latActive (lateral
# goes inactive at standstill on torque cars; the wheel parks on rack friction), or on
# steeringPressed (the driver's instinctive grip during the unwind is what let the
# collapse through, and the driver physically overpowers a torque command regardless).
CURVATURE_HOLD_HARD_SPEED = 4.5 * CV.MPH_TO_MS
# Release must sit ABOVE the speed where the model's action wakes up mid-turn. Left
# turns cross the intersection before arcing, so the car reaches ~3.5-4 m/s while the
# action still reads ~0 (left1/left2 rlogs 2026-07-15: a 6 mph release dropped the
# floor mid-turn and visibly unwound the wheel 50 deg before the action woke; rights
# wake at ~2.2 m/s and never showed it). Hold authority above creep speed is bounded
# by the opposite-command release and the decay band, not by this ceiling.
CURVATURE_HOLD_RELEASE_SPEED = 10.0 * CV.MPH_TO_MS
# Pre-wind is a NEAR-STANDSTILL device: winding the wheel is only free when the car
# isn't moving. On rolling slow turns a plan-sourced floor applies the turn's final
# curvature at the entry, starting the arc 4-7 m early — the "turning too much"
# corrections in the stickyright1/2 and left-crossing rlogs (2026-07-16) all trace to
# plan capture while moving. Above this speed only the model's own action can raise
# the hold, rate-limited so a single-frame action spike (left1 rlog 21.9s: -0.157 for
# one model frame) can't get captured and floored for seconds.
CURVATURE_HOLD_PLAN_SOURCE_SPEED = 2.0 * CV.MPH_TO_MS
CURVATURE_HOLD_RATCHET_RATE = 0.04  # 1/m per s, hold growth limit above the plan-source speed
# Once the model's action has sustainably taken over the turn, hand off COMPLETELY:
# clear the hold and don't re-engage until the blinker cycle ends. A floor that chases
# the awake action only distorts the model's entry spiral, mid-turn shape, and exit
# unwind — the sticky right-turn exits were the floor trailing the model's unwind by
# 0.03-0.05 even at the fast decay (stickyright1 41.15s: floor 0.064 vs action 0.014,
# driver correcting +394). The bridge job is done the moment the action is awake.
CURVATURE_HOLD_HANDOFF_FRAC = 0.75
CURVATURE_HOLD_HANDOFF_TIME = 0.3  # s of sustained action >= frac*hold before handoff
CURVATURE_HOLD_DECAY_TAU = 2.0     # s; hold tracks a sustained lower model demand with this time constant
# At a turn exit the model unwinds through small SAME-sign commands (curvature only
# flips negative for the final counter-steer), so the opposite-release fires late and
# the tau-2 decay melts the floor slower than the model's exit ramp — the car keeps
# arcing while the driver hauls the wheel back (tightright3/4 rlogs 2026-07-15, drv
# +500). Turn progress is the discriminator between a mid-turn dip (protect the floor;
# left-turn sags happened at ~20 deg of swept heading) and an exit (drop it; the
# sticks happened past ~80 deg): once the swept heading passes the threshold, the
# decay switches to the fast tau and runs at ANY speed, including below the hard-hold
# speed. Swept resets whenever the hold disengages.
CURVATURE_HOLD_SWEPT_EXIT = 0.9    # rad of heading actually turned (~52 deg)
CURVATURE_HOLD_EXIT_DECAY_TAU = 0.5  # s
CURVATURE_HOLD_STANDSTILL_TIMEOUT = 30.0  # s stopped before the held turn intent is dropped

# The model's time-domain action.desiredCurvature is blind below ~2.5 m/s (0.3 s ahead
# at creep speed is centimeters of road), but the plan's spatial geometry already shows
# the turn at standstill: turn3/turn4 rlogs 2026-07-14 read plan curvature 0.13-0.16
# while the action output sat at 0.005, and the plan value matched the demand the
# action produced once rolling. Feeding it into the turn-hold ratchet lets the wheel
# pre-wind toward the real turn before the car moves. Scaled and capped conservatively:
# a too-high floor turns in tighter than the path (mild at creep lat accel), while a
# too-low one just reduces the head start. The plan flickers straight for ~1-2 s right
# at the standstill->motion transition; the ratchet holds through it by design.
CURVATURE_HOLD_PLAN_LOOKAHEAD_NEAR = 4.0  # m; reads whether the turn starts NOW
CURVATURE_HOLD_PLAN_LOOKAHEAD_FAR = 7.0   # m; reads the turn's curvature
CURVATURE_HOLD_PLAN_SCALE = 0.85
CURVATURE_HOLD_PLAN_CAP = 0.12       # 1/m
# Proximity gate on the pre-wind: the 4/7 m probe reads the corner's full curvature the
# instant the plan bends toward it, which at a stop-line turn is several meters before
# the car reaches the line — so it wound the wheel hard while still rolling and cut the
# inside curb (both directions), and on an early blinker it turned in before the corner
# (RL2 seg1 t=42: corner 2 m ahead, car at 1.2 m/s, pre-wind already at 0.13). The plan
# itself carries the distance: get_plan_turn_onset_dist is where the path bends. Scale
# the pre-wind from full at ONSET_NEAR to zero at ONSET_FAR_GATE so it winds only as the
# corner closes. At a real stop the onset collapses to ~0 m once stopped (model: "turn
# is here"), so the stop-line pre-wind still reaches full strength — just later, at the
# line instead of 3 m short of it.
CURVATURE_HOLD_ONSET_HEADING = 10.0    # deg of plan heading change that marks the corner
CURVATURE_HOLD_ONSET_NEAR = 1.5        # m; corner this close -> full pre-wind
CURVATURE_HOLD_ONSET_FAR_GATE = 5.0    # m; corner past this -> no pre-wind yet
CURVATURE_HOLD_ONSET_FAR = 100.0       # m; sentinel "no corner found"
CURVATURE_HOLD_REACH_MIN = 7.0
CURVATURE_HOLD_REACH_FULL = 12.0
# The model counter-steers at every turn exit; an opposite-direction command is the
# "turn is over" signal at any speed. Without this the floor converted the exit unwind
# (-0.076) into a stuck +0.012 for 1.4 s and the driver had to unwind by hand
# (rightturnfail rlog 33.2-34.4s). Deadband rejects the ~0.002 pull-away flickers.
CURVATURE_HOLD_OPPOSITE_RELEASE = 0.01  # 1/m
# Nudge-to-commit: creeping toward a rolling left below the release speed, the model
# often does not commit until the geometry is entered — the driver hauled the wheel
# 144-260 deg alone with the action at zero (0000087c segs 7/8, +377..+411 driver
# torque) before the model took over. Forcing the plan probe here instead is what
# caused the 2026-07-19 fights, and the driver's own torque separates those cases
# perfectly: they RESISTED the premature machine wind (-117, bracing) but PUSH when
# the gap is theirs. So the driver's matching push is the "go" signal: capture the
# curvature they have physically wound into the hold, un-rate-limited (the wheel is
# already there; holding adds no motion), so the car grabs the turn at a nudge instead
# of making them wind it all by hand. Allowed anywhere the hold exists (< release
# speed): a 3 m/s ceiling left the 0000087f seg 1 gap-taken-at-3.5-4.2 m/s haul
# (40->220 deg at +418) unassisted; the decay/handoff/opposite-release machinery
# already bounds the captured floor in that band.
CURVATURE_HOLD_CONFIRM_MIN = 0.003  # 1/m (~7 deg) of wound curvature before capture
CURVATURE_HOLD_CONFIRM_SWEPT = 0.6  # rad of heading swept this blinker cycle; past this the push is exit-shaping, not initiation

# Suppress low-speed action spikes while the model's spatial path remains straight.
TWITCH_GUARD_MAX_SPEED = 4.0
TWITCH_GUARD_FADE_SPEED = 3.0
TWITCH_GUARD_DURATION = 1.5
TWITCH_GUARD_PLAN_RATIO = 4.0
TWITCH_GUARD_FLOOR = 0.002
TWITCH_GUARD_STRAIGHT_LO = 0.005
TWITCH_GUARD_STRAIGHT_HI = 0.014
TWITCH_GUARD_MIN_REACH = 12.0


def _plan_circle_curvature(xs, ys, lookahead: float) -> float:
  # Fit curvature through the plan point at the requested lookahead.
  px, py = 0.0, 0.0
  for x, y in zip(xs, ys, strict=False):
    try:
      x, y = float(x), float(y)
    except (TypeError, ValueError, OverflowError):
      return 0.0
    if not (math.isfinite(x) and math.isfinite(y)):
      return 0.0
    px, py = x, y
    if math.hypot(x, y) >= lookahead:
      break
  d2 = px * px + py * py
  if d2 < 1.0:
    return 0.0
  return 2.0 * py / d2


def _plan_dual_probe(model_v2, d_near: float, d_far: float) -> float:
  # Use the smaller magnitude of near and far probes to avoid early turn bias.
  xs, ys = model_v2.position.x, model_v2.position.y
  near = _plan_circle_curvature(xs, ys, d_near)
  far = _plan_circle_curvature(xs, ys, d_far)
  if near * far <= 0.0:
    return 0.0
  return near if abs(near) < abs(far) else far


def get_plan_spatial_curvature(model_v2) -> float:
  return _plan_dual_probe(model_v2, CURVATURE_HOLD_PLAN_LOOKAHEAD_NEAR, CURVATURE_HOLD_PLAN_LOOKAHEAD_FAR)


def get_plan_turn_onset_dist(model_v2) -> float:
  # Distance along the plan at which the path first bends past ONSET_HEADING from the
  # car's current heading — i.e. how far ahead the corner actually starts. The pre-wind
  # magnitude scales on this so a stop-line turn winds only once the corner is close,
  # not the instant the plan first shows a turn several meters out (which cut the inside
  # curb at a stop and turned in early on an over-eager blinker). Returns a large
  # sentinel when no bend is found, so distant/straight plans read "far" and don't wind.
  xs, ys = model_v2.position.x, model_v2.position.y
  n = min(len(xs), len(ys))
  for i in range(2, n):
    dx = xs[i] - xs[i - 1]
    dy = ys[i] - ys[i - 1]
    if abs(dx) < 1e-3 and abs(dy) < 1e-3:
      continue
    if abs(math.degrees(math.atan2(dy, dx))) > CURVATURE_HOLD_ONSET_HEADING:
      return math.hypot(xs[i], ys[i])
  return CURVATURE_HOLD_ONSET_FAR


def get_plan_reach(model_v2) -> float:
  try:
    xs = model_v2.position.x
    return float(xs[-1]) if len(xs) else 0.0
  except (AttributeError, IndexError, TypeError, ValueError, OverflowError):
    return 0.0


def _plan_positions_are_finite(model_v2) -> bool:
  try:
    xs, ys = model_v2.position.x, model_v2.position.y
    return len(xs) == len(ys) and all(
      math.isfinite(float(x)) and math.isfinite(float(y)) for x, y in zip(xs, ys, strict=True)
    )
  except (AttributeError, TypeError, ValueError, OverflowError):
    return False


def limit_curvature_to_plan(model_v2, curvature: float, v_ego: float) -> float:
  if not (math.isfinite(curvature) and math.isfinite(v_ego)):
    return curvature
  if v_ego >= TWITCH_GUARD_MAX_SPEED or curvature == 0.0:
    return curvature
  if not _plan_positions_are_finite(model_v2):
    return curvature
  reach = get_plan_reach(model_v2)
  if not math.isfinite(reach) or reach < TWITCH_GUARD_MIN_REACH:
    return curvature
  plan = abs(_plan_circle_curvature(model_v2.position.x, model_v2.position.y,
                                    CURVATURE_HOLD_PLAN_LOOKAHEAD_FAR))
  if not math.isfinite(plan):
    return curvature
  straightness = (plan - TWITCH_GUARD_STRAIGHT_LO) / (TWITCH_GUARD_STRAIGHT_HI - TWITCH_GUARD_STRAIGHT_LO)
  limit = max(TWITCH_GUARD_PLAN_RATIO * plan * min(max(straightness, 0.0), 1.0), TWITCH_GUARD_FLOOR)
  if abs(curvature) <= limit:
    return curvature
  fade = (TWITCH_GUARD_MAX_SPEED - v_ego) / (TWITCH_GUARD_MAX_SPEED - TWITCH_GUARD_FADE_SPEED)
  fade = min(max(fade, 0.0), 1.0)
  return curvature + (math.copysign(limit, curvature) - curvature) * fade


def update_twitch_guard(remaining: float, v_ego: float, standstill: bool) -> float:
  if not (math.isfinite(remaining) and math.isfinite(v_ego)):
    return 0.0
  if standstill or abs(v_ego) <= 0.3:
    return TWITCH_GUARD_DURATION
  return max(remaining - DT_CTRL, 0.0)


def twitch_guard_allowed(honda_accord_11g: bool, blinker_active: bool,
                         turn_hold_active: bool, lane_change_active: bool) -> bool:
  if honda_accord_11g:
    return not (blinker_active or turn_hold_active or lane_change_active)
  return not (blinker_active or turn_hold_active)


def get_control_lateral_smooth_seconds(brand: str, v_ego: float, vehicle_smooth_seconds: float) -> float:
  if brand == "rivian" or (brand == "subaru" and vehicle_smooth_seconds > 0.0):
    return get_car_lateral_smooth_seconds(brand, v_ego, vehicle_smooth_seconds)
  return LAT_SMOOTH_SECONDS


def turn_lead_allowed(brand: str, lateral_control_mode: car.CarControl.Actuators.LateralControlMode) -> bool:
  # Torque steering mechanically damps the turn-lead fade. A direct angle
  # controller follows the resulting lead/catch-up cycle literally, which can
  # reverse the wheel command several times during one turn initiation.
  return brand != "rivian" or lateral_control_mode != LateralControlMode.angle


# Turn-initiation lead. The model's action and the fixed 4/7 m probes are anchored in
# METERS, so the seconds of warning they give shrinks with speed — at 12 mph a corner
# enters the 7 m window only ~1.3 s out, too late to wind the wheel, which is why every
# turn in the Desktop/new drive initiated only below ~5.5 m/s regardless of approach
# speed. This lead probes the plan at a constant-TIME distance instead and max-mag
# blends into the command, so initiation can start while still rolling at 9-12 mph.
# The engagement fade (authority ramps to zero as measured curvature approaches the
# lead) limits it to the initiation phase: once the car is tracking the arc, the model
# owns the turn shape — without it, the blend re-creates the 2026-07-16 rolling-turn
# front-load (stickyright2 entry: 0.084 commanded vs the model's own 0.041 spiral). A
# binary gate here limit-cycles: cutting drops demand to a still-small action, the
# wheel unwinds below the threshold, the lead re-fires — a 5 Hz demand sawtooth felt
# as wiggle (2026-07-19 drive seg 7 t=49-50). The fade instead settles at a stable
# ~2/3-of-lead equilibrium until the action takes over via the max-mag blend.
# Stop-sign approaches stay quiet because the stopping plan compresses to the stop
# line and reads ~straight until the car is nearly there (probes ~0 for 7 s of
# blinker-on coasting at 9-12 m/s). Below TURN_LEAD_MIN_SPEED the lead must stay OFF,
# not just for standstill plan flicker: at creep speed the probe's 4 m distance floor
# chord-fits a left turn's straight-then-arc entry as "arc now", demanding 3-5x the
# model's intent. The model fights back — its plan flips to correct the premature yaw,
# the wheel swings back through center, and the swing trips the stalk auto-cancel,
# killing the turn (2026-07-19 segs 6/7/8/10, all at 1.5-2.4 m/s; the same drive's
# completed turns show the model committing on its own below 3 m/s). The model's
# meter-anchored horizon gives it 2+ s of warning at creep speed — the lead's whole
# reason to exist (time-warning shrinking with speed) does not apply there.
TURN_LEAD_T = 1.3          # s of travel the probe looks ahead (~wind-up time + lat delay)
TURN_LEAD_MIN_M = 4.0
TURN_LEAD_MAX_M = 14.0
TURN_LEAD_MIN_SPEED = 3.0   # m/s: authority 0 here, ramps to full at FULL_SPEED
TURN_LEAD_FULL_SPEED = 4.0  # m/s
TURN_LEAD_MAX_SPEED = 7.0   # m/s (~15.7 mph)
TURN_LEAD_SCALE = 0.85
TURN_LEAD_CAP = 0.12       # 1/m
TURN_LEAD_ENGAGED_FRAC = 0.5   # engagement fade starts here, zero authority at 1.0
TURN_LEAD_MODEL_OPPOSE = 0.003  # 1/m: model steering this hard against the blinker vetoes the lead
# Braking-to-a-stop veto: if sustaining the current decel parks the car within this
# factor of the probe distance, the driver intends to stop short of the arc — demanding
# that arc's curvature NOW winds the wheel at a stop approach the model didn't plan
# (0000087c seg 1: lead wound 30 deg at 6 m/s while braking for a 13 s stop; driver
# yanked it back with -509 torque). Turn-approach braking releases before this trips;
# a held brake to standstill keeps it tripped, deferring the turn to the pre-wind.
TURN_LEAD_STOP_MARGIN = 1.5
TURN_LEAD_DECEL_GATE = -0.5  # m/s^2: only project a stop when genuinely braking


def get_gm_hud_set_speed(set_speed_ms: float, starpilot_toggles) -> float:
  spoofed_speed = set_speed_ms

  set_speed_offset = float(getattr(starpilot_toggles, "set_speed_offset", 0.0) or 0.0)
  if spoofed_speed > 0 and set_speed_offset > 0:
    spoofed_speed += set_speed_offset * CV.KPH_TO_MS

  return spoofed_speed


def get_torque_control_params(CP, torque_params, starpilot_toggles, use_live_params: bool) -> tuple[float, float, float]:
  torque_tune = CP.lateralTuning.torque
  lat_accel_factor = torque_tune.latAccelFactor
  lat_accel_offset = torque_tune.latAccelOffset
  friction = torque_tune.friction

  use_custom_lat_accel = getattr(starpilot_toggles, "use_custom_latAccelFactor", False)
  use_custom_friction = getattr(starpilot_toggles, "use_custom_friction", False)

  if use_live_params:
    if not use_custom_lat_accel:
      lat_accel_factor = torque_params.latAccelFactorFiltered
      lat_accel_offset = torque_params.latAccelOffsetFiltered
    if not use_custom_friction:
      friction = torque_params.frictionCoefficientFiltered

  if use_custom_lat_accel:
    lat_accel_factor = starpilot_toggles.latAccelFactor
  if use_custom_friction:
    friction = starpilot_toggles.friction

  return lat_accel_factor, lat_accel_offset, friction


class Controls:
  def __init__(self) -> None:
    self.params = Params()
    cloudlog.info("controlsd is waiting for CarParams")
    self.CP = messaging.log_from_bytes(self.params.get("CarParams", block=True), car.CarParams)
    self.FPCP = messaging.log_from_bytes(self.params.get("StarPilotCarParams", block=True), custom.StarPilotCarParams)
    cloudlog.info("controlsd got CarParams")

    self.CI = interfaces[self.CP.carFingerprint](self.CP, self.FPCP)

    self.sm = messaging.SubMaster(['liveDelay', 'liveParameters', 'liveTorqueParameters', 'modelV2', 'selfdriveState',
                                   'liveCalibration', 'livePose', 'longitudinalPlan', 'lateralManeuverPlan', 'carState', 'carOutput',
                                   'driverMonitoringState', 'onroadEvents', 'driverAssistance', 'radarState'], poll='selfdriveState')
    self.pm = messaging.PubMaster(['carControl', 'controlsState', 'starpilotLateralState'])

    self.steer_limited_by_safety = False
    self.curvature = 0.0
    self.desired_curvature = 0.0
    self.lc_smooth_release = 0.0
    self.lane_centering = LaneCenteringController()
    self.lc_entry_sign = 0.0
    self.lc_arrest_jerk_factor = 1.0
    self.turn_hold_curvature = 0.0
    self.turn_hold_standstill_t = 0.0
    self.turn_hold_swept = 0.0
    self.turn_hold_handoff_t = 0.0
    self.turn_hold_done = False
    self.turn_blinker_swept = 0.0
    self.twitch_guard_remaining = 0.0
    self.honda_accord_11g_lateral = self.CP.brand == "honda" and self.CP.carFingerprint == HONDA_CAR.HONDA_ACCORD_11G
    self.kona_non_scc_lateral_active = False
    self.kona_non_scc_lateral_faulted = False
    self.elantra_hev_2024_lateral_faulted = False
    self.elantra_hev_2024_previous_cruise_enabled = False

    self.pose_calibrator = PoseCalibrator()
    self.calibrated_pose: Pose | None = None

    self.LoC = LongControl(self.CP)
    self.VM = VehicleModel(self.CP)
    self.LaC: LatControl
    if self.CP.steerControlType == car.CarParams.SteerControlType.angle:
      self.LaC = LatControlAngle(self.CP, self.CI, DT_CTRL)
    elif self.CP.steerControlType == car.CarParams.SteerControlType.curvatureDEPRECATED:
      self.LaC = LatControlCurvature(self.CP, self.CI, DT_CTRL)
    elif self.CP.lateralTuning.which() == 'pid':
      self.LaC = LatControlPID(self.CP, self.CI, DT_CTRL)
    elif self.CP.lateralTuning.which() == 'torque':
      self.LaC = LatControlTorque(self.CP, self.CI, DT_CTRL)

    self.sm = self.sm.extend(['liveDelay', 'starpilotCarState', 'starpilotPlan'])

    self.starpilot_toggles = get_starpilot_toggles()
    self.ecu_disable_failed = False
    self.ecu_disable_failed_checked = not self.CP.openpilotLongitudinalControl

    if self.CP.lateralTuning.which() == "torque" and (self.starpilot_toggles.nnff or self.starpilot_toggles.nnff_lite):
      self.LaC = LatControlNNFF(self.CP, self.CI, DT_CTRL)

  def update(self):
    self.sm.update(15)
    if self.sm.updated["liveCalibration"]:
      self.pose_calibrator.feed_live_calib(self.sm['liveCalibration'])
    if self.sm.updated["livePose"]:
      device_pose = Pose.from_live_pose(self.sm['livePose'])
      self.calibrated_pose = self.pose_calibrator.build_calibrated_pose(device_pose)

    if hasattr(self.LaC, "pid") and self.CP.lateralTuning.which() != "pid":
      self.LaC.pid._k_p = self.starpilot_toggles.steerKp

    if self.sm.updated['liveDelay'] and hasattr(self.LaC, "update_live_delay"):
      self.LaC.update_live_delay(self.sm['liveDelay'].lateralDelay)

    self.starpilot_toggles = get_starpilot_toggles(self.sm)

  def update_ecu_disable_failed(self):
    if self.ecu_disable_failed_checked:
      return

    if self.params.get_bool("ControlsReady"):
      self.ecu_disable_failed = self.params.get_bool("EcuDisableFailed")
      self.ecu_disable_failed_checked = True
      if self.ecu_disable_failed and self.CP.carFingerprint == NISSAN_CAR.NISSAN_LEAF:
        self.CP = messaging.log_from_bytes(self.params.get("CarParams"), car.CarParams)
        self.FPCP = messaging.log_from_bytes(self.params.get("StarPilotCarParams"), custom.StarPilotCarParams)

  def state_control(self):
    CS = self.sm['carState']
    self.twitch_guard_remaining = update_twitch_guard(self.twitch_guard_remaining, CS.vEgo, CS.standstill)

    # Update VehicleModel
    lp = self.sm['liveParameters']
    x = max(lp.stiffnessFactor, 0.1)
    sr = max(lp.steerRatio, 0.1)
    custom_accord_ratio = getattr(self.starpilot_toggles, "steerRatio", self.CP.steerRatio)
    accord_ratio_is_explicit = getattr(self.starpilot_toggles, "use_custom_steerRatio", False) and \
      abs(custom_accord_ratio - self.CP.steerRatio) > 0.01
    if self.CP.carFingerprint == GM_CAR.CHEVROLET_BOLT_CC_2017:
      sr *= get_bolt_2017_steer_ratio_scale(CS.vEgo)
    elif self.CP.carFingerprint == GM_CAR.CHEVROLET_BOLT_CC_2018_2021:
      sr *= BOLT_2018_2021_STEER_RATIO_TEST_SCALE
    elif self.CP.carFingerprint == HONDA_CAR.HONDA_ACCORD and not accord_ratio_is_explicit:
      sr *= get_honda_accord_steer_ratio_scale(CS.vEgo)
    self.VM.update_params(x, sr)

    steer_angle_without_offset = math.radians(CS.steeringAngleDeg - lp.angleOffsetDeg)
    self.curvature = -self.VM.calc_curvature(steer_angle_without_offset, CS.vEgo, lp.roll)

    # Update Torque Params
    if self.CP.lateralTuning.which() == 'torque':
      torque_params = self.sm['liveTorqueParameters']
      force_auto_tune = getattr(self.starpilot_toggles, "force_auto_tune", False)
      use_live_params = self.sm.all_checks(['liveTorqueParameters']) and (torque_params.useParams or force_auto_tune)
      use_custom_torque_params = (
        getattr(self.starpilot_toggles, "use_custom_latAccelFactor", False) or
        getattr(self.starpilot_toggles, "use_custom_friction", False)
      )
      if use_live_params or use_custom_torque_params:
        lat_accel_factor, lat_accel_offset, friction = get_torque_control_params(self.CP, torque_params, self.starpilot_toggles, use_live_params)
        self.LaC.update_live_torque_params(lat_accel_factor, lat_accel_offset, friction)

    long_plan = self.sm['longitudinalPlan']
    model_v2 = self.sm['modelV2']

    CC = car.CarControl.new_message()
    CC.enabled = self.sm['selfdriveState'].enabled

    # Check which actuators can be enabled
    standstill = abs(CS.vEgo) <= max(self.CP.minSteerSpeed, 0.3) or CS.standstill
    if self.CP.carFingerprint == HYUNDAI_CAR.HYUNDAI_KONA_NON_SCC:
      always_on_lateral_enabled = self.sm['starpilotCarState'].alwaysOnLateralEnabled
      lateral_requested = (CC.enabled and self.sm['selfdriveState'].active) or always_on_lateral_enabled
      if not lateral_requested:
        self.kona_non_scc_lateral_faulted = False
      elif CS.steerFaultTemporary:
        self.kona_non_scc_lateral_faulted = True
      CC.latActive = get_kona_non_scc_lateral_active(
        CC.enabled, self.sm['selfdriveState'].active,
        always_on_lateral_enabled,
        CS.steerFaultTemporary, CS.steerFaultPermanent,
        standstill, self.CP.steerAtStandstill,
        self.sm['starpilotPlan'].lateralCheck,
        CS.steeringPressed, self.kona_non_scc_lateral_active,
        self.kona_non_scc_lateral_faulted,
      )
      self.kona_non_scc_lateral_active = CC.latActive
    elif self.CP.carFingerprint == HYUNDAI_CAR.HYUNDAI_ELANTRA_HEV_2024:
      always_on_lateral_enabled = self.sm['starpilotCarState'].alwaysOnLateralEnabled
      lateral_requested = (CC.enabled and self.sm['selfdriveState'].active) or always_on_lateral_enabled
      cruise_reenabled = CS.cruiseState.enabled and not self.elantra_hev_2024_previous_cruise_enabled
      self.elantra_hev_2024_lateral_faulted = update_lateral_fault_latch(
        self.elantra_hev_2024_lateral_faulted,
        lateral_requested,
        CS.steerFaultTemporary,
        reset=cruise_reenabled,
      )
      CC.latActive = get_lateral_active(
        CC.enabled, self.sm['selfdriveState'].active,
        always_on_lateral_enabled,
        CS.steerFaultTemporary, CS.steerFaultPermanent,
        standstill, self.CP.steerAtStandstill,
        self.sm['starpilotPlan'].lateralCheck,
        self.elantra_hev_2024_lateral_faulted,
      )
      self.elantra_hev_2024_previous_cruise_enabled = CS.cruiseState.enabled
    else:
      CC.latActive = get_lateral_active(CC.enabled, self.sm['selfdriveState'].active,
                                        self.sm['starpilotCarState'].alwaysOnLateralEnabled,
                                        CS.steerFaultTemporary, CS.steerFaultPermanent,
                                        standstill, self.CP.steerAtStandstill,
                                        self.sm['starpilotPlan'].lateralCheck)
    # EcuDisableFailed is set when car started in READY mode (ECU disable was rejected)
    # Disable longitudinal so stock ACC works instead
    self.update_ecu_disable_failed()
    CC.longActive = (
      CC.enabled and not any(e.overrideLongitudinal for e in self.sm['onroadEvents']) and
      not self.sm['starpilotCarState'].pauseLongitudinal and self.CP.openpilotLongitudinalControl and
      not self.ecu_disable_failed
    )

    actuators = CC.actuators
    actuators.longControlState = self.LoC.long_control_state

    # Enable blinkers while lane changing
    if model_v2.meta.laneChangeState != LaneChangeState.off:
      CC.leftBlinker = model_v2.meta.laneChangeDirection == LaneChangeDirection.left
      CC.rightBlinker = model_v2.meta.laneChangeDirection == LaneChangeDirection.right

    if not CC.latActive:
      self.LaC.reset()
      self.lane_centering.reset()
    tesla_pedal_override = self.CP.brand == "tesla" and bool(CS.gasPressed)
    if not CC.longActive and not tesla_pedal_override:
      self.LoC.reset()

    # accel PID loop
    pid_accel_limits = self.CI.get_pid_accel_limits(self.CP, CS.vEgo, CS.vCruise * CV.KPH_TO_MS)
    self.LoC.experimental_mode = bool(self.sm['selfdriveState'].experimentalMode)
    actuators.accel = float(min(self.LoC.update(CC.longActive, CS, long_plan.aTarget, long_plan.shouldStop, pid_accel_limits,
                                                self.starpilot_toggles, has_lead=long_plan.hasLead,
                                                traffic_mode_enabled=self.sm['starpilotCarState'].trafficModeEnabled,
                                                profile_max_accel=self.sm['starpilotPlan'].maxAcceleration,
                                                pedal_override=tesla_pedal_override,
                                                leads=(self.sm['radarState'].leadOne, self.sm['radarState'].leadTwo)),
                                self.starpilot_toggles.max_desired_acceleration))

    # Steering PID loop and lateral MPC
    # Reset desired curvature to current to avoid violating the limits on engage
    if self.sm.valid['lateralManeuverPlan']:
      new_desired_curvature = self.sm['lateralManeuverPlan'].desiredCurvature if CC.latActive else self.curvature
    else:
      new_desired_curvature = model_v2.action.desiredCurvature if CC.latActive else self.curvature

    # Low-speed turn-intent hold (see CURVATURE_HOLD_* above). Curvature sign convention
    # here is positive for RIGHT turns (pauseturn log: left turn at +148 deg steering
    # angle logs desiredCurvature -0.07), so the blinker maps right=+1, left=-1.
    blinker_dir = float(CS.rightBlinker) - float(CS.leftBlinker)
    lane_change_active = model_v2.meta.laneChangeState != LaneChangeState.off
    if (CC.latActive and self.twitch_guard_remaining > 0.0 and
        twitch_guard_allowed(self.honda_accord_11g_lateral, blinker_dir != 0.0,
                             self.turn_hold_curvature != 0.0, lane_change_active)):
      new_desired_curvature = limit_curvature_to_plan(model_v2, new_desired_curvature, CS.vEgo)
    # The validated Accord path keeps the native model/action curvature and does not
    # inherit generic turn-hold or turn-lead shaping. Lane centering remains downstream.
    accord11g_raw_curvature = new_desired_curvature
    # heading swept in the blinker's direction over the whole blinker cycle (any speed):
    # discriminates a turn not yet made from one being exited (see the re-arm below)
    if blinker_dir == 0.0:
      self.turn_blinker_swept = 0.0
    else:
      self.turn_blinker_swept += max(CS.vEgo * self.curvature * blinker_dir, 0.0) * DT_CTRL
    if CS.vEgo >= CURVATURE_HOLD_RELEASE_SPEED:
      self.turn_hold_curvature = 0.0
      self.turn_hold_standstill_t = 0.0
      self.turn_hold_swept = 0.0
      self.turn_hold_handoff_t = 0.0
      self.turn_hold_done = False
    else:
      if self.turn_hold_curvature == 0.0:
        self.turn_hold_swept = 0.0
      else:
        # heading actually swept in the hold's direction: the measure of turn progress
        self.turn_hold_swept += max(CS.vEgo * self.curvature * math.copysign(1.0, self.turn_hold_curvature), 0.0) * DT_CTRL
      turn_exiting = self.turn_hold_swept > CURVATURE_HOLD_SWEPT_EXIT
      if (CS.vEgo > CURVATURE_HOLD_HARD_SPEED or turn_exiting) and CC.latActive and self.turn_hold_curvature != 0.0:
        # Decay toward the model's sustained same-direction demand instead of leaking on
        # wall-clock time: a wall-clock leak drained the floor mid-turn while the model
        # dipped transiently (turnn rlog 40.0-40.5s), while sustained low demand (end of
        # turn, abort) still drains the hold within a couple of time constants.
        hold_dir = math.copysign(1.0, self.turn_hold_curvature)
        model_mag = max(new_desired_curvature * hold_dir, 0.0)
        if model_mag < abs(self.turn_hold_curvature):
          decay_tau = CURVATURE_HOLD_EXIT_DECAY_TAU if turn_exiting else CURVATURE_HOLD_DECAY_TAU
          decayed = abs(self.turn_hold_curvature) + (model_mag - abs(self.turn_hold_curvature)) * (DT_CTRL / decay_tau)
          self.turn_hold_curvature = math.copysign(decayed, self.turn_hold_curvature)
      if CS.vEgo < 0.5:
        self.turn_hold_standstill_t += DT_CTRL
        if self.turn_hold_standstill_t > CURVATURE_HOLD_STANDSTILL_TIMEOUT:
          self.turn_hold_curvature = 0.0
        # a stop resets the turn cycle: the model goes blind again, so a prior handoff
        # must not block the standstill pre-wind (turn4 regression in v9 replay)
        self.turn_hold_done = False
      else:
        self.turn_hold_standstill_t = 0.0
      if CC.latActive and self.turn_hold_curvature != 0.0 and \
         new_desired_curvature * math.copysign(1.0, self.turn_hold_curvature) < -CURVATURE_HOLD_OPPOSITE_RELEASE:
        # model is actively counter-steering: the turn is over, release at any speed
        self.turn_hold_curvature = 0.0
        self.turn_hold_done = True
      if CC.latActive and self.turn_hold_curvature != 0.0 and \
         new_desired_curvature * math.copysign(1.0, self.turn_hold_curvature) >= CURVATURE_HOLD_HANDOFF_FRAC * abs(self.turn_hold_curvature):
        self.turn_hold_handoff_t += DT_CTRL
        if self.turn_hold_handoff_t > CURVATURE_HOLD_HANDOFF_TIME:
          # action has sustainably taken over: hand off completely (see HANDOFF consts)
          self.turn_hold_curvature = 0.0
          self.turn_hold_done = True
      else:
        self.turn_hold_handoff_t = 0.0
      if blinker_dir == 0.0:
        # blinker cycle over: a fresh turn may engage a fresh hold
        self.turn_hold_done = False
      elif CC.latActive and CS.steeringPressed and CS.steeringTorque * blinker_dir < 0.0 and \
           self.curvature * blinker_dir > CURVATURE_HOLD_CONFIRM_MIN and \
           self.turn_blinker_swept < CURVATURE_HOLD_CONFIRM_SWEPT:
        # an active driver push into the signaled turn BEFORE the turn is made is fresh
        # turn intent: re-arm the cycle even after a prior handoff. A long blinker-on
        # approach can latch done on a trivial micro-handoff and lock out
        # nudge-to-commit ten seconds later at the real turn (0000087f seg 1: +418 haul
        # unassisted). The swept gate keeps a light same-direction touch during the
        # EXIT unwind from re-latching a large hold against the model's recentering
        # (0000087f seg 4 t=14.5 in replay: floor trailed the exit by 0.07 for 1.5 s).
        self.turn_hold_done = False
      if blinker_dir != 0.0 and not self.turn_hold_done:
        # Ratchet up on the raw model command, never on the floored/measured value, so
        # the hold can't feed itself and defeat the decay. Below the release speed the
        # plan's spatial curvature (see get_plan_spatial_curvature) is the second,
        # earlier-seeing source: it shows the turn at standstill while the action is
        # still blind, letting the pre-wind start before the car moves.
        turn_candidate = new_desired_curvature if CC.latActive else 0.0
        if CC.latActive and CS.vEgo < CURVATURE_HOLD_PLAN_SOURCE_SPEED:
          plan_curvature = get_plan_spatial_curvature(model_v2) * CURVATURE_HOLD_PLAN_SCALE
          plan_curvature = max(min(plan_curvature, CURVATURE_HOLD_PLAN_CAP), -CURVATURE_HOLD_PLAN_CAP)
          # Proximity gate (see CURVATURE_HOLD_ONSET_*): wind only as the corner closes,
          # so a stop-line turn winds at the line and an early blinker doesn't turn in
          # early. Full at ONSET_NEAR, zero at ONSET_FAR_GATE.
          onset = get_plan_turn_onset_dist(model_v2)
          onset_w = min(max((CURVATURE_HOLD_ONSET_FAR_GATE - onset) /
                            (CURVATURE_HOLD_ONSET_FAR_GATE - CURVATURE_HOLD_ONSET_NEAR), 0.0), 1.0)
          reach = get_plan_reach(model_v2)
          reach_w = min(max((reach - CURVATURE_HOLD_REACH_MIN) /
                            (CURVATURE_HOLD_REACH_FULL - CURVATURE_HOLD_REACH_MIN), 0.0), 1.0)
          plan_curvature *= onset_w * reach_w
          if plan_curvature * blinker_dir > turn_candidate * blinker_dir:
            turn_candidate = plan_curvature
        # Nudge-to-commit (see CURVATURE_HOLD_CONFIRM_*): the driver actively pushing in
        # the blinker direction at creep speed captures what they have wound. Positive
        # steeringTorque is a LEFT push (negative curvature), so agreement is a negative
        # product with blinker_dir. Exempt from the ratchet rate limit: latching the
        # wheel's current position commands no motion, only keeps the driver's progress.
        driver_confirmed = False
        if CC.latActive and CS.steeringPressed and \
           CS.steeringTorque * blinker_dir < 0.0 and self.curvature * blinker_dir > CURVATURE_HOLD_CONFIRM_MIN:
          wound_curvature = max(min(self.curvature, CURVATURE_HOLD_PLAN_CAP), -CURVATURE_HOLD_PLAN_CAP)
          if wound_curvature * blinker_dir > turn_candidate * blinker_dir:
            turn_candidate = wound_curvature
            driver_confirmed = True
        if turn_candidate * blinker_dir > abs(self.turn_hold_curvature):
          new_mag = turn_candidate * blinker_dir
          if CS.vEgo > CURVATURE_HOLD_PLAN_SOURCE_SPEED and not driver_confirmed:
            new_mag = min(new_mag, abs(self.turn_hold_curvature) + CURVATURE_HOLD_RATCHET_RATE * DT_CTRL)
          self.turn_hold_curvature = math.copysign(new_mag, turn_candidate)
        elif self.turn_hold_curvature * blinker_dir < 0.0:
          # blinker flipped to the other side: turn intent changed
          self.turn_hold_curvature = 0.0
      if CC.latActive and self.turn_hold_curvature != 0.0:
        hold_dir = math.copysign(1.0, self.turn_hold_curvature)
        if new_desired_curvature * hold_dir < abs(self.turn_hold_curvature):
          new_desired_curvature = self.turn_hold_curvature

    # Turn-initiation lead (see TURN_LEAD_*). Applied AFTER the hold block so the
    # ratchet/handoff only ever see the raw model action; pure max-magnitude, so it can
    # never reduce or oppose the model. Lane changes are excluded: that blinker's plan
    # bend is not a turn. The model-oppose veto is defense-in-depth for the fade-in
    # edge: a model actively steering against the blinker is correcting something the
    # lead must not fight (see the constants comment for the 2026-07-19 failures).
    lateral_control_mode = self.sm['carOutput'].actuatorsOutput.lateralControlMode
    if (turn_lead_allowed(self.CP.brand, lateral_control_mode) and
        CC.latActive and blinker_dir != 0.0 and
        model_v2.meta.laneChangeState == LaneChangeState.off and
        TURN_LEAD_MIN_SPEED <= CS.vEgo < TURN_LEAD_MAX_SPEED and
        new_desired_curvature * blinker_dir > -TURN_LEAD_MODEL_OPPOSE):
      d_near = max(min(TURN_LEAD_T * CS.vEgo, TURN_LEAD_MAX_M), TURN_LEAD_MIN_M)
      stopping_short = CS.aEgo < TURN_LEAD_DECEL_GATE and \
          CS.vEgo ** 2 / (2.0 * -CS.aEgo) < TURN_LEAD_STOP_MARGIN * d_near
      lead_curvature = 0.0 if stopping_short else _plan_dual_probe(model_v2, d_near, d_near + 3.0) * TURN_LEAD_SCALE
      lead_curvature = max(min(lead_curvature, TURN_LEAD_CAP), -TURN_LEAD_CAP)
      if lead_curvature * blinker_dir > 0.0:
        speed_w = min(max((CS.vEgo - TURN_LEAD_MIN_SPEED) / (TURN_LEAD_FULL_SPEED - TURN_LEAD_MIN_SPEED), 0.0), 1.0)
        engaged_ratio = abs(self.curvature) / abs(lead_curvature)
        engage_w = min(max((1.0 - engaged_ratio) / (1.0 - TURN_LEAD_ENGAGED_FRAC), 0.0), 1.0)
        lead_curvature *= speed_w * engage_w
        if lead_curvature * blinker_dir > max(new_desired_curvature * blinker_dir, 0.0):
          new_desired_curvature = lead_curvature
          # Capture the applied lead into the hold (rate-limited like any moving-speed
          # ratchet) so decelerating through the fade floor keeps the initiation
          # progress: without this, braking mid-wind dumped the lead's demand back to
          # the still-small action and visibly unwound the wheel 50->15 deg before the
          # standstill pre-wind had to redo the work (0000087c seg 6 first left).
          if CS.vEgo < CURVATURE_HOLD_RELEASE_SPEED and not self.turn_hold_done and \
             lead_curvature * blinker_dir > abs(self.turn_hold_curvature):
            held_mag = min(lead_curvature * blinker_dir, abs(self.turn_hold_curvature) + CURVATURE_HOLD_RATCHET_RATE * DT_CTRL)
            self.turn_hold_curvature = math.copysign(held_mag, lead_curvature)

    if self.honda_accord_11g_lateral:
      new_desired_curvature = accord11g_raw_curvature
      self.turn_hold_curvature = 0.0
      self.turn_hold_done = False

    new_desired_curvature = self.lane_centering.update(
      new_desired_curvature, model_v2, CS.vEgo,
      self.starpilot_toggles.lane_centering,
      self.starpilot_toggles.lane_center_offset,
      self.starpilot_toggles.lane_centering_e2e_authority,
      CC.latActive,
      bool(self.sm.all_checks(['modelV2'])),
      self.starpilot_toggles.lane_centering_pause_on_signal,
      bool(CS.leftBlinker or CS.rightBlinker))

    jerk_factor = 1.0
    if self.starpilot_toggles.lane_change_pace < 10:
      set_jerk = self.starpilot_toggles.lane_change_jerk_factor
      in_lane_change = model_v2.meta.laneChangeState in (LaneChangeState.laneChangeStarting, LaneChangeState.laneChangeFinishing) \
          and CS.vEgo >= self.starpilot_toggles.minimum_lane_change_speed
      # Hold the tight jerk limit for the whole maneuver, then taper back to stock so the
      # model's recenter step and mid-change corrections stay shaped instead of passing
      # through a mostly-relaxed clamp. Only the jerk (curvature rate) is tightened: capping
      # lat accel strangles the end-of-maneuver arrest and lets the car glide past the new
      # lane center before it can build enough counter-curvature.
      if in_lane_change:
        self.lc_smooth_release = LANE_CHANGE_SMOOTH_RELEASE_T
        if self.lc_entry_sign == 0.0 and abs(new_desired_curvature - self.desired_curvature) > 2e-4:
          self.lc_entry_sign = math.copysign(1.0, new_desired_curvature - self.desired_curvature)
      else:
        self.lc_smooth_release = max(self.lc_smooth_release - DT_CTRL, 0.0)
        if self.lc_smooth_release <= 0.0:
          self.lc_entry_sign = 0.0
      if self.lc_smooth_release > 0.0:
        release = 1.0 - self.lc_smooth_release / LANE_CHANGE_SMOOTH_RELEASE_T  # 0 in maneuver → 1 after
        jerk_factor = set_jerk + (1.0 - set_jerk) * release
        step = new_desired_curvature - self.desired_curvature
        model_unwinding = self.lc_entry_sign != 0.0 and abs(step) > LANE_CHANGE_ARREST_GAP_DEADBAND and \
            math.copysign(1.0, step) == -self.lc_entry_sign
        if model_unwinding:
          v_lim = max(CS.vEgo, 1.0)
          gap = max(abs(step) - LANE_CHANGE_ARREST_GAP_DEADBAND, 0.0)
          jf_gap = (gap / LANE_CHANGE_ARREST_PURSUIT_TAU) * v_lim ** 2 / MAX_LATERAL_JERK
          arrest_cap = LANE_CHANGE_ARREST_JERK_FLOOR + (1.0 - LANE_CHANGE_ARREST_JERK_FLOOR) * release
          jerk_factor = max(jerk_factor, min(arrest_cap, jerk_factor + jf_gap))
        if jerk_factor > self.lc_arrest_jerk_factor:
          rise_alpha = 1.0 - math.exp(-DT_CTRL / LANE_CHANGE_ARREST_RISE_TAU)
          jerk_factor = self.lc_arrest_jerk_factor + rise_alpha * (jerk_factor - self.lc_arrest_jerk_factor)
      self.lc_arrest_jerk_factor = jerk_factor

    if self.honda_accord_11g_lateral:
      jerk_factor = 1.0

    self.desired_curvature, curvature_limited = clip_curvature(CS.vEgo, self.desired_curvature, new_desired_curvature, lp.roll,
                                                               jerk_factor)
    lat_smooth_seconds = 0.0 if self.honda_accord_11g_lateral else get_control_lateral_smooth_seconds(
      self.CP.brand, CS.vEgo, self.CP.lateralSmoothSeconds,
    )
    lat_delay = self.sm["liveDelay"].lateralDelay + lat_smooth_seconds

    actuators.curvature = self.desired_curvature
    steer, lateral_output, lac_log = self.LaC.update(CC.latActive, CS, self.VM, lp,
                                                     self.steer_limited_by_safety, self.desired_curvature,
                                                     curvature_limited, lat_delay,
                                                     self.calibrated_pose,
                                                     self.sm['modelV2'],
                                                     self.starpilot_toggles)
    actuators.torque = float(steer)
    if self.CP.steerControlType == car.CarParams.SteerControlType.curvatureDEPRECATED:
      actuators.curvature = float(lateral_output)
    else:
      actuators.steeringAngleDeg = float(lateral_output)

    if len(long_plan.speeds):
      actuators.speed = long_plan.speeds[-1]

    # Ensure no NaNs/Infs
    for p in ACTUATOR_FIELDS:
      attr = getattr(actuators, p)
      if not isinstance(attr, Number):
        continue

      if not math.isfinite(attr):
        cloudlog.error(f"actuators.{p} not finite {actuators.to_dict()}")
        setattr(actuators, p, 0.0)

    return CC, lac_log

  def publish(self, CC, lac_log):
    CS = self.sm['carState']
    long_plan = self.sm['longitudinalPlan']

    # Orientation and angle rates can be useful for carcontroller
    # Only calibrated (car) frame is relevant for the carcontroller
    CC.currentCurvature = self.curvature
    if self.calibrated_pose is not None:
      CC.orientationNED = self.calibrated_pose.orientation.xyz.tolist()
      CC.angularVelocity = self.calibrated_pose.angular_velocity.xyz.tolist()

    CC.cruiseControl.override = CC.enabled and not CC.longActive and self.CP.openpilotLongitudinalControl
    pacifica_hybrid_aol = pacifica_hybrid_aol_stock_acc_mode(
      self.CP.carFingerprint,
      self.CP.pcmCruise,
      CC.enabled,
      self.sm['starpilotCarState'].alwaysOnLateralEnabled,
    )
    cancel_requested = should_cancel_stock_cruise(self.CP, CS.cruiseState.enabled, CC.enabled)
    CC.cruiseControl.cancel = cancel_requested and not pacifica_hybrid_aol

    legacy_resume_hack = False
    if len(long_plan.speeds):
      planned_resume = long_plan.speeds[-1] > 0.1
      # Some stock-ACC SNG hacks still rely on the legacy "planner wants speed"
      # signal rather than longitudinalPlan.shouldStop going false first.
      legacy_resume_hack = planned_resume and (
        (self.CP.brand == "toyota" and self.CP.openpilotLongitudinalControl and not self.CP.autoResumeSng) or
        (self.CP.brand == "gm" and getattr(self.starpilot_toggles, "volt_sng", False))
      )

    CC.cruiseControl.resume = CC.enabled and CS.cruiseState.standstill and (
      not self.sm['longitudinalPlan'].shouldStop or legacy_resume_hack
    )

    hudControl = CC.hudControl
    hud_set_speed = float(CS.vCruiseCluster * CV.KPH_TO_MS)
    gm_dash_spoof_offsets_enabled = (
      self.CP.brand == "gm" and
      self.CP.openpilotLongitudinalControl and
      self.CP.enableGasInterceptorDEPRECATED and
      getattr(self.starpilot_toggles, "gm_pedal_longitudinal", True) and
      not getattr(self.starpilot_toggles, "disable_openpilot_long", False) and
      getattr(self.starpilot_toggles, "gm_dash_spoof_offsets", False)
    )
    if gm_dash_spoof_offsets_enabled:
      hud_set_speed = get_gm_hud_set_speed(hud_set_speed, self.starpilot_toggles)
    hudControl.setSpeed = hud_set_speed
    hudControl.speedVisible = CC.enabled
    hudControl.lanesVisible = CC.enabled
    hudControl.leadVisible = self.sm['longitudinalPlan'].hasLead
    hudControl.leadDistanceBars = self.sm['selfdriveState'].personality.raw + 1
    hudControl.visualAlert = self.sm['selfdriveState'].alertHudVisual

    hudControl.rightLaneVisible = True
    hudControl.leftLaneVisible = True
    if self.sm.valid['driverAssistance']:
      hudControl.leftLaneDepart = self.sm['driverAssistance'].leftLaneDeparture
      hudControl.rightLaneDepart = self.sm['driverAssistance'].rightLaneDeparture

    if self.sm['selfdriveState'].active:
      CO = self.sm['carOutput']
      if self.CP.steerControlType == car.CarParams.SteerControlType.angle:
        self.steer_limited_by_safety = abs(CC.actuators.steeringAngleDeg - CO.actuatorsOutput.steeringAngleDeg) > \
                                              STEER_ANGLE_SATURATION_THRESHOLD
      else:
        self.steer_limited_by_safety = abs(CC.actuators.torque - CO.actuatorsOutput.torque) > 1e-2

    # TODO: both controlsState and carControl valids should be set by
    #       sm.all_checks(), but this creates a circular dependency

    # controlsState
    dat = messaging.new_message('controlsState')
    dat.valid = CS.canValid
    cs = dat.controlsState

    cs.curvature = self.curvature
    cs.longitudinalPlanMonoTime = self.sm.logMonoTime['longitudinalPlan']
    cs.lateralPlanMonoTime = self.sm.logMonoTime['modelV2']
    cs.desiredCurvature = self.desired_curvature
    cs.longControlState = self.LoC.long_control_state
    cs.upAccelCmd = float(self.LoC.pid.p)
    cs.uiAccelCmd = float(self.LoC.pid.i)
    cs.ufAccelCmd = float(self.LoC.pid.f)
    cs.forceDecel = bool(self.sm['driverMonitoringState'].noResponseForceDecel or
                         (self.sm['selfdriveState'].state == State.softDisabling) or self.sm["starpilotCarState"].forceCoast)

    lat_tuning = self.CP.lateralTuning.which()
    if self.CP.steerControlType == car.CarParams.SteerControlType.angle:
      cs.lateralControlState.angleState = lac_log
    elif self.CP.steerControlType == car.CarParams.SteerControlType.curvatureDEPRECATED:
      cs.lateralControlState.curvatureStateDEPRECATED = lac_log
    elif lat_tuning == 'pid':
      cs.lateralControlState.pidState = lac_log
    elif lat_tuning == 'torque':
      cs.lateralControlState.torqueState = lac_log

    self.pm.send('controlsState', dat)

    if hasattr(self.LaC, 'starpilot_lateral_state'):
      debug_dat = messaging.new_message('starpilotLateralState')
      debug_dat.starpilotLateralState = self.LaC.starpilot_lateral_state
      self.pm.send('starpilotLateralState', debug_dat)

    # carControl
    cc_send = messaging.new_message('carControl')
    cc_send.valid = CS.canValid
    cc_send.carControl = CC
    self.pm.send('carControl', cc_send)

  def run(self):
    rk = Ratekeeper(100, print_delay_threshold=None)
    while True:
      self.update()
      CC, lac_log = self.state_control()
      self.publish(CC, lac_log)
      rk.monitor_time()


def main():
  config_realtime_process(4, Priority.CTRL_HIGH)
  controls = Controls()
  controls.run()


if __name__ == "__main__":
  main()
