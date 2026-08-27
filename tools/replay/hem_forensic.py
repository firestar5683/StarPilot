#!/usr/bin/env python3
"""HEM forensic analyzer: figure out exactly what HybridExperimentalMode decided
and why, on a logged route, down to the per-frame input params and every internal
gate. Designed to answer "why did HEM roll through that stop sign / red light?"

It replays a route segment(s) through the *real* LongitudinalPlanner (Chill / ACC)
and the *real* HybridExperimentalMode (using the logged modelV2 action for Exp),
and records HybridExperimentalMode's full internal decision state each frame
(vision weight, stop detection, throttle/brake fusion, standstill anchor, safety
barrier, slew filter). It then:

  * auto-detects "stop roll-through" incidents (vehicle creeping/coasting through
    a detected stop with no braking authority),
  * prints a per-frame forensic log of the decision chain around the incident,
  * prints a root-cause narrative naming the exact gate that failed, and
  * writes a graph of the Exp input, Chill input, fused output, authority, vision
    weight and regime.

Usage:
  ./dev python tools/replay/hem_forensic.py <dongleId>/<routeId> [--segments 0,1]
      [--start 30] [--end 120] [--data_dir /path/to/routes] [--out hem_forensic.png]
      [--show] [--csv out.csv] [--window 12]
      [--set hybrid_exp_bias=0.2 --set hybrid_vision_brake_sensitivity=1.2]

Examples:
  ./dev python tools/replay/hem_forensic.py afb7ef2ed593d651/000000af--414a758637 --segments 0,1
  ./dev python tools/replay/hem_forensic.py afb7ef2ed593d651/000000af--414a758637 --segments 0,1 --window 20 --set hybrid_exp_bias=0.2
"""
from __future__ import annotations

import argparse
import bisect
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
  sys.path.insert(0, str(ROOT_DIR))

from openpilot.common.constants import CV
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.car.cruise import V_CRUISE_MAX, V_CRUISE_UNSET
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.starpilot.controls.lib.hybrid_experimental_mode import HybridExperimentalMode
from openpilot.tools.replay.mode_sim import (
  FakeParams,
  TOGGLE_DEFAULTS,
  as_lead,
  load_buffers,
  parse_toggle_overrides,
  resolve_segment_identifier,
)

# Services we need to reconstruct the Chill (ACC) planner + Exp input + HEM.
SERVICES = {
  "carState", "radarState", "starpilotRadarState", "modelV2",
  "longitudinalPlan", "selfdriveState", "starpilotPlan", "starpilotCarState",
  "controlsState", "carParams", "liveParameters", "carControl",
}

# Fields in HybridExperimentalMode.diag that are part of the decision chain.
DIAG_KEYS = [
  # inputs
  "v_ego", "v_cruise", "a_chill", "a_exp",
  "should_stop_chill", "should_stop_exp",
  "lead_status", "lead_d_rel", "lead_v_lead",
  # vision intent
  "has_full_trajectory", "v_horizon", "v_short", "v_min",
  "speed_drop_ratio", "model_decel_strength",
  "raw_vision_metric", "w_target", "w_vision",
  # departure / override
  "lead_departing", "vision_departing", "driver_override", "is_departing",
  "horizon_stopping",
  # fusion
  "a_brake_fused", "a_throttle_fused", "is_stopping_event", "exp_dominant",
  # standstill handshake
  "standstill_intent", "should_stop_fused", "a_out",
]
REGIME_KEYS = ["regime", "standstill"]


def merge_buffers(buffers_list):
  """Merge per-segment {service: [(t, msg), ...]} into one dict sorted by time."""
  merged = {s: [] for s in SERVICES}
  for bufs in buffers_list:
    for s in SERVICES:
      merged[s].extend(bufs.get(s, []))
  for s in SERVICES:
    merged[s].sort(key=lambda x: x[0])
  return merged


def run_forensic(grid, bufs, toggles):
  """Replay through the real planner + HEM, recording every HEM internal gate."""
  ts = {s: [t for t, _ in m] for s, m in bufs.items()}
  ms = {s: [m for _, m in bufs[s]] for s in bufs}

  def latest(service, t):
    times = ts.get(service)
    if not times:
      return None
    idx = bisect.bisect_right(times, t) - 1
    return ms[service][idx] if idx >= 0 else None

  cp_candidate = None
  for _, cp in bufs.get("carParams", []):
    if cp is not None:
      cp_candidate = cp
      break
  if cp_candidate is None:
    cp_candidate = SimpleNamespace(
      brand="toyota", carFingerprint="TOYOTA_RAV4", openpilotLongitudinalControl=True,
      pcmCruise=False, steerRatio=15.0, wheelbase=2.7, longitudinalActuatorDelay=0.2, flags=0,
    )

  planner_state = SimpleNamespace(
    params=FakeParams(),
    params_memory=FakeParams(),
    starpilot_following=SimpleNamespace(following_lead=False, slower_lead=False),
    starpilot_vcruise=SimpleNamespace(
      slc=SimpleNamespace(experimental_mode=False),
      stop_sign_confirmed=False,
      forcing_stop=False,
    ),
  )

  hybrid = HybridExperimentalMode()
  hybrid.record_diag = True  # capture full per-frame decision state for the trace
  hybrid.set_tuning(toggles.hybrid_exp_bias, toggles.hybrid_vision_brake_sensitivity)
  chill_long_planner = LongitudinalPlanner(cp_candidate, dt=DT_MDL)

  n = len(grid)
  out = {k: np.zeros(n) for k in [
    "v_ego", "v_cruise", "model_v0", "a_chill", "a_exp", "hem_a", "hem_authority",
    "lead_d_rel", "lead_v_lead", "logged_aTarget", "a_ego",
  ]}
  out["lead_status"] = np.zeros(n, dtype=bool)
  out["brake_pressed"] = np.zeros(n, dtype=bool)
  out["gas_pressed"] = np.zeros(n, dtype=bool)
  for k in DIAG_KEYS:
    if k in ("should_stop_chill", "should_stop_exp", "lead_status", "has_full_trajectory",
             "lead_departing", "vision_departing", "driver_override", "is_departing",
             "horizon_stopping", "is_stopping_event", "exp_dominant", "standstill_intent",
             "should_stop_fused"):
      out["hem_" + k] = np.zeros(n, dtype=bool)
    else:
      out["hem_" + k] = np.zeros(n)
  out["hem_regime"] = np.zeros(n, dtype=bool)
  out["hem_standstill"] = np.zeros(n, dtype=bool)
  # Gates dropped in the new HEM design map onto the surviving output signal.
  out["hem_a_anchored"] = np.full(n, np.nan)
  out["hem_a_safe"] = np.zeros(n)

  real_monotonic = time.monotonic
  fake_clock = [0.0]
  time.monotonic = lambda: fake_clock[0]

  last_model_v2 = None
  for _, m in bufs.get("modelV2", []):
    if m is not None:
      last_model_v2 = m
      break

  try:
    for i, t in enumerate(grid):
      fake_clock[0] = float(i) * DT_MDL

      car_raw = latest("carState", t)
      v_ego_raw = max(float(getattr(car_raw, "vEgo", 0.0)), 0.0)
      car = SimpleNamespace(
        vEgo=v_ego_raw,
        vEgoCluster=max(float(getattr(car_raw, "vEgoCluster", v_ego_raw)), 0.0),
        vCruise=float(getattr(car_raw, "vCruise", 0.0)),
        standstill=bool(getattr(car_raw, "standstill", False)),
        leftBlinker=bool(getattr(car_raw, "leftBlinker", False)),
        rightBlinker=bool(getattr(car_raw, "rightBlinker", False)),
        gasPressed=bool(getattr(car_raw, "gasPressed", False)),
        brakePressed=bool(getattr(car_raw, "brakePressed", False)),
        steeringAngleDeg=float(getattr(car_raw, "steeringAngleDeg", 0.0)),
        aEgo=float(getattr(car_raw, "aEgo", 0.0)),
        leftBlindspot=bool(getattr(car_raw, "leftBlindspot", False)),
        rightBlindspot=bool(getattr(car_raw, "rightBlindspot", False)),
      )
      v_ego = car.vEgo

      radar = latest("radarState", t)
      lead = as_lead(getattr(radar, "leadOne", None) if radar is not None else None)
      lead2 = as_lead(getattr(radar, "leadTwo", None) if radar is not None else None)
      sradar = latest("starpilotRadarState", t)
      lead_left = as_lead(getattr(sradar, "leadLeft", None) if sradar is not None else None)
      lead_right = as_lead(getattr(sradar, "leadRight", None) if sradar is not None else None)

      lplan = latest("longitudinalPlan", t)
      sds = latest("selfdriveState", t)
      splan = latest("starpilotPlan", t)
      scs = latest("starpilotCarState", t)
      model_v2 = latest("modelV2", t)
      if model_v2 is not None:
        last_model_v2 = model_v2
      else:
        model_v2 = last_model_v2  # carry last vision frame across a replay gap
      live_params = latest("liveParameters", t)
      car_control = latest("carControl", t)
      controls_state = latest("controlsState", t)
      car_params = latest("carParams", t) or cp_candidate

      v_cruise = float(getattr(splan, "vCruise", 0.0) or 0.0)
      if not (v_cruise > 0):
        v_cruise_kph = float(getattr(car_raw, "vCruise", 0.0) or 0.0)
        if 0 < v_cruise_kph < V_CRUISE_UNSET:
          v_cruise = min(v_cruise_kph, V_CRUISE_MAX) * CV.KPH_TO_MS
        else:
          v_cruise = v_ego

      tracking_lead = bool(getattr(splan, "trackingLead", False))
      if not tracking_lead:
        tracking_lead = bool(getattr(lplan, "hasLead", False))

      t_follow = float(getattr(splan, "tFollow", 1.45))
      following_lead = tracking_lead and lead.dRel < (t_follow * 2) * v_ego
      planner_state.lead_one = lead
      planner_state.tracking_lead = tracking_lead

      sm_dict = {
        "carState": car,
        "radarState": SimpleNamespace(leadOne=lead, leadTwo=lead2),
        "starpilotRadarState": SimpleNamespace(leadLeft=lead_left, leadRight=lead_right),
        "starpilotCarState": SimpleNamespace(
          trafficModeEnabled=bool(getattr(scs, "trafficModeEnabled", False)),
          alwaysOnLateralEnabled=bool(getattr(scs, "alwaysOnLateralEnabled", False)),
          dashboardStopSign=int(getattr(scs, "dashboardStopSign", 0)),
          accelPressed=bool(getattr(scs, "accelPressed", False)),
        ),
        "selfdriveState": SimpleNamespace(
          enabled=bool(getattr(sds, "enabled", False)),
          experimentalMode=False,  # force ACC/Chill evaluation in MPC
          personality=0,
        ),
        "longitudinalPlan": SimpleNamespace(
          hasLead=bool(getattr(lplan, "hasLead", False)),
          allowThrottle=bool(getattr(lplan, "allowThrottle", True)),
          shouldStop=bool(getattr(lplan, "shouldStop", False)),
          aTarget=float(getattr(lplan, "aTarget", 0.0)),
        ),
        "starpilotPlan": SimpleNamespace(
          vCruise=v_cruise,
          tFollow=t_follow,
          trackingLead=tracking_lead,
          redLight=bool(getattr(splan, "redLight", False)),
          forcingStop=bool(getattr(splan, "forcingStop", False)),
          forcingStopLength=float(getattr(splan, "forcingStopLength", 100.0)),
          minAcceleration=float(getattr(splan, "minAcceleration", -3.5)),
          maxAcceleration=float(getattr(splan, "maxAcceleration", 1.5)),
          accelerationJerk=float(getattr(splan, "accelerationJerk", 1.0)),
          dangerJerk=float(getattr(splan, "dangerJerk", 1.0)),
          speedJerk=float(getattr(splan, "speedJerk", 1.0)),
          dangerFactor=float(getattr(splan, "dangerFactor", 1.0)),
          disableThrottle=bool(getattr(splan, "disableThrottle", False)),
        ),
        "controlsState": SimpleNamespace(
          longControlState=LongCtrlState.pid,
          forceDecel=bool(getattr(controls_state, "forceDecel", False)),
          curvature=0.0,
        ),
        "liveParameters": SimpleNamespace(
          angleOffsetDeg=float(getattr(live_params, "angleOffsetDeg", 0.0)) if live_params else 0.0,
        ),
        "carControl": SimpleNamespace(
          orientationNED=getattr(car_control, "orientationNED", [0.0, 0.0, 0.0]) if car_control else [0.0, 0.0, 0.0],
        ),
        "modelV2": model_v2,
        "carParams": car_params,
      }

      # Chill (ACC) acceleration target via the real planner.
      chill_long_planner.update(sm_dict, toggles)
      a_chill = float(chill_long_planner.output_a_target)

      # Exp (vision) acceleration target from the logged model action.
      a_exp = 0.0
      if model_v2 is not None:
        try:
          action_obj = getattr(model_v2, "action", None)
          if action_obj is not None and hasattr(action_obj, "desiredAcceleration"):
            a_exp = float(action_obj.desiredAcceleration)
          else:
            accel_x = getattr(model_v2, "acceleration", None)
            if accel_x is not None and len(accel_x.x):
              a_exp = float(accel_x.x[0])
        except Exception:
          a_exp = 0.0

      should_stop_exp = False
      if model_v2 is not None:
        try:
          should_stop_exp = bool(getattr(getattr(model_v2, "action", None), "shouldStop", False))
        except Exception:
          should_stop_exp = False
      a_hem, should_stop_fused = hybrid.update(
        v_ego=v_ego, v_cruise=v_cruise, lead_one=lead, model_v2=model_v2,
        a_chill=a_chill, a_exp=a_exp,
        should_stop_exp=should_stop_exp,
        should_stop_chill=bool(getattr(lplan, "shouldStop", False)),
      )

      model_v0 = v_ego
      if model_v2 is not None:
        try:
          vel_x = getattr(model_v2, "velocity", None)
          if vel_x is not None and len(vel_x.x):
            model_v0 = float(vel_x.x[0])
        except Exception:
          model_v0 = v_ego

      out["v_ego"][i] = v_ego
      out["v_cruise"][i] = v_cruise
      out["model_v0"][i] = model_v0
      out["a_chill"][i] = a_chill
      out["a_exp"][i] = a_exp
      out["hem_a"][i] = a_hem
      out["hem_authority"][i] = hybrid.w_vision
      out["lead_status"][i] = lead.status
      out["lead_d_rel"][i] = lead.dRel
      out["lead_v_lead"][i] = lead.vLead
      out["logged_aTarget"][i] = float(getattr(lplan, "aTarget", 0.0))
      out["brake_pressed"][i] = car.brakePressed
      out["gas_pressed"][i] = car.gasPressed
      out["a_ego"][i] = car.aEgo

      for k in DIAG_KEYS:
        val = hybrid.diag.get(k)
        if isinstance(val, bool):
          out["hem_" + k][i] = bool(val)
        else:
          try:
            out["hem_" + k][i] = float(val)
          except Exception:
            out["hem_" + k][i] = 0.0
      out["hem_regime"][i] = hybrid.diag.get("regime") == "brake"
      out["hem_standstill"][i] = bool(hybrid.diag.get("standstill", False))
      out["hem_a_anchored"][i] = out["hem_a"][i] if out["hem_standstill"][i] else np.nan
      out["hem_a_safe"][i] = out["hem_a"][i]
  finally:
    time.monotonic = real_monotonic

  return out


def detect_incidents(out, t):
  """Find frames where a detected stop was rolled/crept through for lack of braking.

  A roll-through frame: the car is actually moving (v_ego > 0.5 m/s), the vision
  side has flagged a stop (w_vision > 0.3), yet the fused output is essentially
  coasting because BOTH chill and exp inputs failed to request a stop:
      a_chill (ACC) is not braking          -> a_chill > -0.3
      exp effective accel is non-negative   -> a_exp_effective >= 0
  Under those conditions a_brake_fused = min(a_chill, a_exp) lands at ~0 and HEM
  coasts through the stop it claims to see.
  """
  idxs = []
  for i in range(len(t)):
    v = out["v_ego"][i]
    w = out["hem_w_vision"][i]
    ac = out["hem_a_chill"][i]
    ae_eff = out["hem_a_exp"][i]
    aout = out["hem_a"][i]
    if v > 0.5 and w > 0.3 and ac > -0.3 and ae_eff >= 0.0 and abs(aout) < 0.25:
      idxs.append(i)
  return idxs


def hard_brake_clusters(out, gap_sec=1.5):
  """Clusters of frames where the DRIVER slammed the brakes (a_ego < -2.0).

  The driver's own hard brake is the ground-truth marker that HEM failed to stop
  the car. Each cluster is a discrete human-intervention event."""
  hb = hard_brake_idxs(out)
  return cluster_indices(hb, gap_sec=gap_sec)


def classify_failure(out, sl, i_brake):
  """Classify WHY the driver had to brake, from the frames just before the brake."""
  lead = int(3.0 / DT_MDL)
  pre = slice(max(sl.start, i_brake - lead), i_brake)
  if pre.stop <= pre.start:
    return "UNKNOWN", {}
  v = out["v_ego"][pre]
  exp_eff = out["hem_a_exp"][pre]
  wv = out["hem_w_vision"][pre]
  hem = out["hem_a"][pre]
  chill = out["hem_a_chill"][pre]
  # out["hem_regime"] is True for the BRAKE regime.
  brake_share = float(np.mean(out["hem_regime"][pre]))
  throttle_share = 1.0 - brake_share

  stats = {
    "v_before": float(v[-1]), "v_max": float(v.max()),
    "exp_eff_mean": float(exp_eff.mean()), "exp_eff_min": float(exp_eff.min()),
    "w_vis_max": float(wv.max()), "w_vis_mean": float(wv.mean()),
    "hem_min": float(hem.min()), "hem_mean": float(hem.mean()),
    "chill_min": float(chill.min()),
    "throttle_share": throttle_share,
  }

  if stats["hem_min"] > -0.35 and stats["w_vis_max"] < 0.5 and stats["exp_eff_mean"] >= 0.0:
    mode = "NO_STOP_REQUEST"   # HEM never braked; neither input requested a stop
  elif stats["throttle_share"] > 0.6 and stats["exp_eff_mean"] < -0.2:
    mode = "THROTTLE_OVERRIDE"  # vision wanted to brake but HEM output positive throttle
  elif stats["w_vis_max"] > 0.4 and stats["exp_eff_mean"] < -0.2 and stats["hem_min"] > -1.2:
    mode = "WEAK_BRAKE"         # vision saw the stop but braking authority was too weak
  elif stats["w_vis_max"] > 0.3 and stats["exp_eff_mean"] < -0.1:
    mode = "LATE_BRAKE"         # HEM braked but too late / not enough distance
  else:
    mode = "UNKNOWN"
  return mode, stats


def cluster_indices(idxs, gap_sec=2.0):
  """Split incident indices into clusters separated by > gap_sec of quiet time."""
  if not idxs:
    return []
  gap = int(gap_sec / DT_MDL)
  clusters = [[idxs[0]]]
  for idx in idxs[1:]:
    if idx - clusters[-1][-1] > gap:
      clusters.append([idx])
    else:
      clusters[-1].append(idx)
  return clusters


def hard_brake_idxs(out):
  """Frames where the DRIVER slammed the brakes (a_ego strongly negative) — a
  human-intervention marker proving HEM was about to run the stop."""
  return [i for i in range(len(out["a_ego"])) if out["a_ego"][i] < -2.0]


def select_main_cluster(clusters, hb):
  """Pick the incident cluster the driver actually intervened on (nearest hard
  brake); fall back to the densest cluster when no driver braking occurred."""
  if not clusters:
    return []
  if not hb:
    return max(clusters, key=len)
  best, best_gap = None, float("inf")
  for cl in clusters:
    gap = min(min(abs(i - j) for j in hb) for i in cl)
    if gap < best_gap:
      best_gap, best = gap, cl
  return best


def window_around(idxs, t, out, span_sec=6.0, max_frames=400):
  """Select the incident cluster the driver braked on, return (slice, cluster)."""
  if not idxs:
    return None, []
  clusters = cluster_indices(idxs)
  main = select_main_cluster(clusters, hard_brake_idxs(out))
  start = max(0, main[0] - int(span_sec / DT_MDL))
  end = min(len(t) - 1, main[-1] + int(span_sec / DT_MDL))
  if end - start > max_frames:
    mid = (start + end) // 2
    start = max(0, mid - max_frames // 2)
    end = min(len(t) - 1, start + max_frames)
    main = [i for i in main if start <= i <= end]
  return slice(start, end + 1), main


def print_forensic_log(out, sl, t0):
  print("\n" + "-" * 122)
  print(" PER-FRAME HEM DECISION CHAIN")
  print("-" * 122)
  hdr = (f"  {'t':>5} {'vEgo':>5} {'aEgo':>6} {'dvrBrk':>6} {'chill':>6} {'exp':>6} {'expEff':>6} "
         f"{'wVis':>5} {'auth':>5} {'regime':>8} {'stand':>5} {'brakeF':>6} {'throtF':>6} {'hem_a':>6}")
  print(hdr)
  print("  " + "-" * 122)
  for i in range(sl.start, sl.stop):
    dt = t0[i]
    row = [
      f"{dt:5.1f}",
      f"{out['v_ego'][i]:5.2f}",
      f"{out['a_ego'][i]:6.2f}",
      f"{'<<<<' if out['a_ego'][i] < -2.0 else ('Y' if out['brake_pressed'][i] else '-'):>6}",
      f"{out['hem_a_chill'][i]:6.2f}",
      f"{out['hem_a_exp'][i]:6.2f}",
      f"{out['hem_a_exp'][i]:6.2f}",
      f"{out['hem_w_vision'][i]:5.2f}",
      f"{out['hem_authority'][i]:5.2f}",
      f"{'brake' if out['hem_regime'][i] else 'throttle':>8}",
      f"{'Y' if out['hem_standstill'][i] else '-':>5}",
      f"{out['hem_a_brake_fused'][i]:6.2f}",
      f"{out['hem_a_throttle_fused'][i]:6.2f}",
      f"{out['hem_a'][i]:6.2f}",
    ]
    print("  " + " ".join(row))


def print_root_cause(out, t0, brake_cluster, sl, mode, stats):
  print("\n" + "=" * 78)
  print(" ROOT-CAUSE DIAGNOSIS (driver-brake anchored)")
  print("=" * 78)
  if not brake_cluster:
    print("  No hard driver brake (a_ego < -2.0) found; no human intervention to explain.")
    print("  If a stop was still rolled through, pass --start/--end around it.")
    return

  i = brake_cluster[0]
  dt = t0[i]
  v = out["v_ego"][i]
  print(f"  Driver slammed the brakes at t = {dt:.1f}s (segment-relative), v_ego = {v:.1f} m/s "
        f"({v * CV.MS_TO_MPH:.1f} mph), a_ego = {out['a_ego'][i]:.2f} m/s².")
  print(f"  HEM fused output at that instant: {out['hem_a'][i]:+.2f} m/s².")

  labels = {
    "NO_STOP_REQUEST": "HEM NEVER REQUESTED A STOP",
    "THROTTLE_OVERRIDE": "HEM ACCELERATED DESPITE VISION STOP",
    "WEAK_BRAKE": "HEM BRAKED BUT TOO WEAKLY",
    "LATE_BRAKE": "HEM BRAKED BUT TOO LATE",
    "UNKNOWN": "NO CLEAR FAILURE MODE (see trace)",
  }
  print(f"\n  FAILURE MODE: {labels.get(mode, mode)}")

  print("\n  [HEM STATE IN THE ~3s BEFORE THE DRIVER BRAKE]")
  print(f"    Speed just before brake : {stats.get('v_before', 0):.1f} m/s (max {stats.get('v_max', 0):.1f})")
  print(f"    Vision weight w_vision  : mean {stats.get('w_vis_mean', 0):.2f} | max {stats.get('w_vis_max', 0):.2f}  (0.3+ = stop detected)")
  print(f"    Exp effective a         : mean {stats.get('exp_eff_mean', 0):+.2f} | min {stats.get('exp_eff_min', 0):+.2f} m/s²")
  print(f"    Chill (ACC) a_chill     : min {stats.get('chill_min', 0):+.2f} m/s²")
  print(f"    HEM output a_hem        : mean {stats.get('hem_mean', 0):+.2f} | min {stats.get('hem_min', 0):+.2f} m/s²")
  print(f"    Throttle regime share   : {100 * stats.get('throttle_share', 0):.0f}%")

  print("\n  [INTERPRETATION]")
  if mode == "NO_STOP_REQUEST":
    print("    • Vision never flagged a stop (w_vision stayed < 0.5) and Exp requested no brake")
    print("      (a_exp_eff >= 0). Chill/ACC also requested no brake. HEM coasted, so the driver")
    print("      had to brake. The stop/light was missed at the perception level (model predicted go).")
  elif mode == "THROTTLE_OVERRIDE":
    print("    • Vision DID see the stop (exp_eff < -0.2) but HEM spent >60% of the approach in the")
    print("      THROTTLE regime and output positive accel. The throttle path (smooth_max of chill/exp)")
    print("      or a departing flag won over the brake path, so HEM drove toward the light.")
  elif mode == "WEAK_BRAKE":
    print("    • Vision saw the stop (w_vision > 0.4) and Exp requested a brake, but HEM's output")
    print(f"      never went harder than {stats.get('hem_min', 0):.2f} m/s². That decel was not enough to")
    print("      stop in time at the approach speed, so the driver had to brake hard.")
  elif mode == "LATE_BRAKE":
    print("    • HEM did brake but only started hard late in the approach (or the needed stop distance")
    print("      exceeded what its braking could cover), forcing the driver to intervene.")
  else:
    print("    • Review the per-frame trace above; the inputs/state were mixed.")

  print("\n  [FIX DIRECTIONS]")
  if mode in ("NO_STOP_REQUEST", "THROTTLE_OVERRIDE"):
    print("    • When w_vision or exp_eff indicates a stop but neither input produces a brake, HEM")
    print("      should synthesize its own kinematic brake (a_kinematic_stop) instead of blending 0's.")
    print("    • Lock the braking regime (w_accel=0) harder when a stop is detected, so the throttle")
    print("      path cannot override a vision brake.")
  elif mode in ("WEAK_BRAKE", "LATE_BRAKE"):
    print("    • HEM currently mirrors the model's Exp brake (a_exp_eff) and the ACC brake; when those")
    print("      are too gentle for the required stop distance, HEM should apply a stronger floor based")
    print("      on the kinematic stop calculation (-v²/2d) and vision brake sensitivity.")
    print("    • Raise VISION_BRAKE_SENSITIVITY or lower the kinematic-stop distance threshold so the")
    print("      vision stop requests decel earlier and harder.")


def plot_results(out, t0, args, incident_idxs):
  import matplotlib
  if not args.show:
    matplotlib.use("Agg")
  import matplotlib.pyplot as plt

  n = len(t0)
  fig, axs = plt.subplots(5, 1, figsize=(15, 17), sharex=True,
                          gridspec_kw={"height_ratios": [2, 2, 2, 2, 1.4]})
  fig.suptitle(f"HEM forensic  {args.route}  segs {args.segments}  "
               f"(bias={args_set(args.set, 'hybrid_exp_bias', 0.0):+.2f}, "
               f"vis_brake={args_set(args.set, 'hybrid_vision_brake_sensitivity', 1.0):.2f})",
               fontsize=11)

  # shade incident region
  if incident_idxs:
    for ax in axs:
      x0 = t0[max(0, incident_idxs[0] - int(2 / DT_MDL))]
      x1 = t0[min(n - 1, incident_idxs[-1] + int(2 / DT_MDL))]
      ax.axvspan(x0, x1, color="red", alpha=0.08)

  # speed
  axs[0].plot(t0, out["v_ego"] * CV.MS_TO_MPH, color="black", lw=1.5, label="v_ego")
  axs[0].plot(t0, out["v_cruise"] * CV.MS_TO_MPH, color="tab:blue", lw=1.0, ls="--", label="v_cruise")
  axs[0].plot(t0, out["model_v0"] * CV.MS_TO_MPH, color="tab:green", lw=1.0, alpha=0.7, label="model v[0]")
  axs[0].set_ylabel("mph")
  axs[0].set_title("1) Speed")
  axs[0].legend(loc="upper right", fontsize=8)
  axs[0].grid(alpha=0.3)

  # accel inputs vs output
  axs[1].axhline(0, color="gray", lw=0.6)
  hard_brake = out["a_ego"] < -2.0
  if np.any(hard_brake):
    axs[1].fill_between(t0, -3.5, 2.0, where=hard_brake, step="post",
                        color="crimson", alpha=0.15, label="driver hard brake")
  axs[1].plot(t0, out["a_chill"], color="tab:blue", lw=1.1, ls="--", label="Chill (ACC) input")
  axs[1].plot(t0, out["a_exp"], color="tab:orange", lw=1.1, ls=":", label="Exp (vision) input")
  axs[1].plot(t0, out["hem_a"], color="tab:cyan", lw=1.6, label="HEM fused output")
  axs[1].plot(t0, out["a_ego"], color="crimson", lw=1.0, alpha=0.8, label="a_ego (actual)")
  axs[1].plot(t0, out["logged_aTarget"], color="gray", lw=0.9, alpha=0.6, label="logged aTarget")
  axs[1].set_ylim(-3.5, 2.0)
  axs[1].set_ylabel("accel (m/s²)")
  axs[1].set_title("2) HEM inputs vs output vs actual (crimson = driver brake)")
  axs[1].legend(loc="upper right", fontsize=7, ncol=2)
  axs[1].legend(loc="upper right", fontsize=8, ncol=2)
  axs[1].grid(alpha=0.3)

  # vision weight, authority, exp_effective
  axs[2].plot(t0, out["hem_w_vision"], color="tab:red", lw=1.3, label="w_vision")
  axs[2].plot(t0, out["hem_authority"], color="tab:purple", lw=1.3, label="exp authority")
  axs[2].plot(t0, out["hem_a_exp"], color="tab:olive", lw=1.0, ls="--", label="exp a")
  axs[2].axhline(0.3, color="tab:red", lw=0.6, ls=":")
  axs[2].set_ylim(-1, 1.5)
  axs[2].set_ylabel("weight")
  axs[2].set_title("3) Vision stop detection vs Exp effective accel")
  axs[2].legend(loc="upper right", fontsize=8)
  axs[2].grid(alpha=0.3)

  # decision gates
  axs[3].plot(t0, out["hem_a_brake_fused"], color="tab:blue", lw=1.2, label="brake-fused")
  axs[3].plot(t0, out["hem_a_throttle_fused"], color="tab:orange", lw=1.2, label="throttle-fused")
  axs[3].plot(t0, out["hem_a_anchored"], color="tab:green", lw=1.2, ls="--", label="after standstill")
  axs[3].plot(t0, out["hem_a_safe"], color="tab:red", lw=1.2, ls="--", label="after safety")
  axs[3].plot(t0, out["hem_a"], color="black", lw=1.6, label="final output")
  axs[3].axhline(0, color="gray", lw=0.6)
  axs[3].set_ylabel("accel (m/s²)")
  axs[3].set_title("4) Fusion pipeline: which gate produced the output")
  axs[3].legend(loc="upper right", fontsize=8, ncol=2)
  axs[3].grid(alpha=0.3)

  # regime + standstill
  axs[4].fill_between(t0, 0.0, 1.0, where=out["hem_regime"], step="post",
                      color="tab:red", alpha=0.5, label="brake regime")
  axs[4].fill_between(t0, 1.0, 2.0, where=out["hem_standstill"], step="post",
                      color="tab:green", alpha=0.5, label="standstill anchor")
  axs[4].set_yticks([0.5, 1.5])
  axs[4].set_yticklabels(["brake", "standstill"])
  axs[4].set_ylim(-0.3, 2.3)
  axs[4].set_xlabel("time (s, segment-relative)")
  axs[4].set_title("5) Regime")
  axs[4].legend(loc="upper right", fontsize=8)
  axs[4].grid(axis="y", alpha=0.3)

  fig.tight_layout()
  if args.out:
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=150)
    print(f"Saved graph to {p}")
  if args.show:
    plt.show()
  plt.close(fig)


def args_set(overrides, key, default):
  for item in overrides:
    k, sep, raw = item.partition("=")
    if sep and k.strip() == key:
      try:
        return float(raw.strip())
      except ValueError:
        return default
  return default


def main(argv=None):
  parser = argparse.ArgumentParser(
    description="Forensic analysis of what HybridExperimentalMode decided, and why, on a route.")
  parser.add_argument("route", help="route: <dongleId>/<logId> (the part after connect.comma.ai/), "
                                    "e.g. afb7ef2ed593d651/000000af--414a758637")
  parser.add_argument("--segments", default="0", help="comma-separated segment indices, e.g. 0,1")
  parser.add_argument("--data_dir", help="local directory containing route files")
  parser.add_argument("--start", type=float, default=None, help="start seconds (segment-relative)")
  parser.add_argument("--end", type=float, default=None, help="end seconds (segment-relative)")
  parser.add_argument("--window", type=float, default=8.0,
                      help="seconds of context to print around each detected incident (default 8)")
  parser.add_argument("--out", default="hem_forensic.png", help="output PNG path")
  parser.add_argument("--show", action="store_true", help="show plot window")
  parser.add_argument("--csv", default=None, help="optional CSV output of the time series")
  parser.add_argument("--set", action="append", default=[], metavar="KEY=value",
                      help="override a toggle, e.g. --set hybrid_exp_bias=0.2 --set hybrid_vision_brake_sensitivity=1.2")
  args = parser.parse_args(argv)

  overrides = parse_toggle_overrides(args.set)
  defaults = dict(TOGGLE_DEFAULTS)
  defaults.update(overrides)
  toggles = SimpleNamespace(**defaults)
  for key, value in overrides.items():
    print(f"toggle override: {key} = {value}")

  segments = [int(s) for s in args.segments.split(",") if s.strip() != ""]
  buffers_list = []
  for seg in segments:
    identifiers = resolve_segment_identifier(args.route, seg, args.data_dir)
    if not identifiers:
      print(f"No data found for {args.route} seg {seg}", file=sys.stderr)
      return 1
    print(f"Loading seg {seg}: {identifiers}")
    bufs = load_buffers(identifiers, SERVICES)
    if not any(bufs[s] for s in SERVICES):
      print(f"No messages loaded for seg {seg}.", file=sys.stderr)
      return 1
    buffers_list.append(bufs)

  bufs = merge_buffers(buffers_list)
  all_min = min(t for s in SERVICES for t, _ in bufs[s])
  all_max = max(t for s in SERVICES for t, _ in bufs[s])
  start = all_min if args.start is None else all_min + args.start
  end = all_max if args.end is None else min(all_max, all_min + args.end)
  if end - start < DT_MDL:
    print(f"Empty time window [{start:.1f}, {end:.1f}].", file=sys.stderr)
    return 1
  grid = np.arange(start, end, DT_MDL)
  print(f"Window: {start - all_min:.1f}s -> {end - all_min:.1f}s ({len(grid)} frames at {1 / DT_MDL:.0f} Hz)")
  t0 = grid - start

  out = run_forensic(grid, bufs, toggles)

  if args.csv:
    import csv
    csv_path = Path(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    top_cols = ["v_ego", "v_cruise", "a_chill", "a_exp", "hem_a", "hem_authority",
                "lead_status", "lead_d_rel", "lead_v_lead", "a_ego",
                "brake_pressed", "gas_pressed", "logged_aTarget"]
    diag_cols = ["hem_" + k for k in DIAG_KEYS] + ["hem_regime", "hem_standstill"]
    seen = set()
    unique_cols = []
    for c in ["t"] + top_cols + diag_cols:
      if c not in seen:
        seen.add(c)
        unique_cols.append(c)
    with open(csv_path, "w", newline="") as f:
      writer = csv.writer(f)
      writer.writerow(unique_cols)
      for i in range(len(t0)):
        row = [f"{t0[i]:.3f}"]
        for c in unique_cols[1:]:
          row.append(f"{out[c][i]:.4f}")
        writer.writerow(row)
    print(f"Saved CSV to {csv_path}")

  brake_clusters = hard_brake_clusters(out)
  if brake_clusters:
    main_brake = max(brake_clusters, key=len)
    lead_sec = int(args.window / DT_MDL)
    sl = slice(max(0, main_brake[0] - lead_sec),
               min(len(t0), main_brake[-1] + int(3 / DT_MDL)))
    if sl.stop - sl.start > 600:
      mid = (sl.start + sl.stop) // 2
      sl = slice(max(0, mid - 300), min(len(t0), mid + 300))
    print(f"\nDetected {len(brake_clusters)} driver hard-brake interventions.")
    print(f"Focusing on the main one at t={t0[main_brake[0]]:.1f}s..{t0[main_brake[-1]]:.1f}s; "
          "use --start/--end to zoom elsewhere.")
    mode, stats = classify_failure(out, sl, main_brake[0])
    focus_incidents = main_brake
  else:
    print("\nNo hard driver brake (a_ego < -2.0) found in the window.")
    print("Falling back to coast-through detection (vision saw a stop but HEM coasted).")
    incident_idxs = detect_incidents(out, t0)
    sl, focus_incidents = window_around(incident_idxs, t0, out, span_sec=args.window)
    if sl is None:
      sl = slice(0, len(t0))
    mode, stats = None, {}

  print_forensic_log(out, sl, t0)
  print_root_cause(out, t0, focus_incidents, sl, mode, stats)
  plot_results(out, t0, args, focus_incidents if focus_incidents else [])
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
