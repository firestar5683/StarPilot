#!/usr/bin/env python3
"""Offline mode-scenario estimator for CEM / Chill (CCM) / HEM / Exp.

Replays a logged route segment through the real StarPilot mode state machines
(ConditionalExperimentalMode, ConditionalChillMode, HybridExperimentalMode)
and openpilot's LongitudinalPlanner, then plots and prints what each mode's
experimental intent and acceleration target would have been at every 20 Hz frame.

Usage:
  ./dev python tools/replay/mode_sim.py <route> [--segment 0] [--start 30] [--end 120]
      [--data_dir /path/to/routes] [--out graph.png] [--show]
      [--set CESpeed=20 --set CEModelStopTime=3.0 --set CCMLead=true] [--csv out.csv]

Examples:
  ./dev python tools/replay/mode_sim.py afb7ef2ed593d651/00000095--9dcb90357c --segment 9
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
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner, get_accel_from_plan
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import COMFORT_BRAKE
from openpilot.starpilot.common.experimental_state import CCStatus, CEStatus
from openpilot.starpilot.common.starpilot_utilities import calculate_lane_width, calculate_road_curvature
from openpilot.starpilot.common.starpilot_variables import CRUISING_SPEED, MINIMUM_LATERAL_ACCELERATION, PLANNER_TIME
from openpilot.starpilot.controls.lib.conditional_chill_mode import ConditionalChillMode
from openpilot.starpilot.controls.lib.conditional_experimental_mode import ConditionalExperimentalMode
from openpilot.starpilot.controls.lib.hybrid_experimental_mode import HybridExperimentalMode
from openpilot.tools.lib.logreader import LogReader, ReadMode, parse_direct, parse_indirect
from openpilot.tools.lib.route import SegmentRange

SERVICES = {
  "carState", "radarState", "starpilotRadarState", "modelV2",
  "longitudinalPlan", "selfdriveState", "starpilotPlan", "starpilotCarState",
  "controlsState", "carParams", "liveParameters", "carControl",
}

CE_LABELS = {
  CEStatus["CURVATURE"]: "CURVE",
  CEStatus["LEAD"]: "LEAD",
  CEStatus["SIGNAL"]: "SIGNAL",
  CEStatus["SPEED"]: "SPEED",
  CEStatus["SPEED_LIMIT"]: "SPEED_LIMIT",
  CEStatus["STOP_LIGHT"]: "STOP_LIGHT",
}
CC_LABELS = {
  CCStatus["LEAD"]: "LEAD",
  CCStatus["SPEED"]: "SPEED",
}
CC_AUTO_STATUSES = {CCStatus["SPEED"], CCStatus["LEAD"]}

# CEM/CCM toggle defaults (units in m/s where appropriate).
TOGGLE_DEFAULTS: dict[str, Any] = {
  # CEM
  "conditional_curves": True,
  "conditional_curves_lead": True,
  "conditional_lead": True,
  "conditional_slower_lead": True,
  "conditional_stopped_lead": True,
  "conditional_open_road": False,
  "conditional_limit": 0.0,                           # CESpeed, m/s (0 = disabled)
  "conditional_limit_lead": 0.0,                      # CESpeedLead, m/s (0 = disabled)
  "conditional_signal": 0.0,                          # CESignalSpeed, m/s (0 = disabled)
  "conditional_model_stop_time": 0.0,                 # CEModelStopTime, s (0 = disabled)
  "conditional_signal_lane_detection": False,
  "lane_detection_width": 0.0,
  # Chill (CCM)
  "conditional_chill_speed": 30 * CV.MPH_TO_MS,       # CCMSpeed
  "conditional_chill_speed_lead": 25 * CV.MPH_TO_MS,  # CCMSpeedLead
  "conditional_chill_speed_margin": 3 * CV.MPH_TO_MS, # CCMSetSpeedMargin
  "conditional_chill_lead": True,
  "conditional_chill_launch_assist": False,
  # HEM
  "hybrid_exp_bias": 0.0,
  "hybrid_vision_brake_sensitivity": 1.0,
  # StarPilot / Planner toggles
  "taco_tune": False,
  "classic_model": False,
  "tinygrad_model": False,
  "vEgoStopping": 0.05,
  "hybrid_experimental_mode": False,
  "radar_takeoffs": False,
  "lane_change_close_gap": False,
  "minimum_lane_change_speed": 0.0,
  "model_version": None,
}
BOOL_KEYS = {
  "conditional_curves", "conditional_curves_lead", "conditional_lead",
  "conditional_slower_lead", "conditional_stopped_lead", "conditional_open_road",
  "conditional_signal_lane_detection", "conditional_chill_lead",
  "conditional_chill_launch_assist", "taco_tune", "classic_model", "tinygrad_model",
  "hybrid_experimental_mode", "radar_takeoffs", "lane_change_close_gap",
}


class FakeParams:
  def __init__(self):
    self.bools = {}
    self.ints = {}

  def get_bool(self, key):
    return bool(self.bools.get(key, False))

  def put_bool(self, key, value):
    self.bools[key] = bool(value)

  def get_int(self, key, default=0):
    return int(self.ints.get(key, default))

  def put_int(self, key, value):
    self.ints[key] = int(value)


def default_lead(status=False):
  return SimpleNamespace(
    status=status,
    dRel=float("inf"),
    yRel=0.0,
    vRel=0.0,
    aRel=0.0,
    vLead=0.0,
    vLeadK=0.0,
    dPath=0.0,
    vLat=0.0,
    aLeadK=0.0,
    aLeadTau=1.5,
    fcw=False,
    modelProb=0.0,
    radar=False,
  )


def as_lead(raw):
  if raw is None:
    return default_lead()
  try:
    status = bool(getattr(raw, "status", False))
  except Exception:
    status = False
  return SimpleNamespace(
    status=status,
    dRel=float(getattr(raw, "dRel", float("inf"))),
    yRel=float(getattr(raw, "yRel", 0.0)),
    vRel=float(getattr(raw, "vRel", 0.0)),
    aRel=float(getattr(raw, "aRel", 0.0)),
    vLead=float(getattr(raw, "vLead", 0.0)),
    vLeadK=float(getattr(raw, "vLeadK", getattr(raw, "vLead", 0.0))),
    dPath=float(getattr(raw, "dPath", 0.0)),
    vLat=float(getattr(raw, "vLat", 0.0)),
    aLeadK=float(getattr(raw, "aLeadK", 0.0)),
    aLeadTau=float(getattr(raw, "aLeadTau", 1.5)),
    fcw=bool(getattr(raw, "fcw", False)),
    modelProb=float(getattr(raw, "modelProb", 0.0)),
    radar=bool(getattr(raw, "radar", False)),
  )


def local_segment_files(data_dir, route_name, segment):
  data_root = Path(data_dir)
  segment_names = (f"{route_name}--{segment}", f"{route_name.replace('|', '/')}/{segment}")
  filenames = ("rlog.zst", "rlog.bz2", "qlog.zst", "qlog.bz2")
  identifiers = []
  for segment_name in segment_names:
    for filename in filenames:
      candidate = data_root / segment_name / filename
      if candidate.exists():
        identifiers.append(str(candidate))
  for filename in filenames:
    explorer = data_root / f"{route_name}--{segment}--{filename}"
    if explorer.exists():
      identifiers.append(str(explorer))
  return identifiers


def resolve_segment_identifier(route, segment, data_dir):
  direct = parse_direct(route)
  if direct is not None:
    return [str(direct)]
  parsed = parse_indirect(route)
  sr = SegmentRange(parsed)
  route_name = sr.route_name.replace("/", "|")
  if data_dir:
    identifiers = local_segment_files(data_dir, route_name, segment)
    if identifiers:
      return identifiers
  return [f"{route_name}--{segment}"]


def load_buffers(identifiers, services):
  bufs = {s: [] for s in services}
  for identifier in identifiers:
    try:
      logreader = LogReader(identifier, default_mode=ReadMode.RLOG)
    except Exception as exc:
      print(f"Unable to open {identifier}: {exc}", file=sys.stderr)
      continue
    for evt in logreader:
      which = evt.which()
      if which not in services:
        continue
      try:
        t = evt.logMonoTime * 1e-9
      except Exception:
        continue
      bufs[which].append((t, getattr(evt, which)))
  for service in services:
    bufs[service].sort(key=lambda x: x[0])
  return bufs


def parse_toggle_overrides(args_set):
  overrides = {}
  for item in args_set or []:
    key, sep, raw = item.partition("=")
    key = key.strip()
    if not sep or key not in TOGGLE_DEFAULTS:
      print(f"warning: ignoring unknown toggle override '{item}'", file=sys.stderr)
      continue
    raw = raw.strip()
    if key in BOOL_KEYS:
      overrides[key] = raw.lower() in {"1", "true", "yes", "on"}
    else:
      try:
        overrides[key] = float(raw)
      except ValueError:
        print(f"warning: ignoring non-numeric toggle override '{item}'", file=sys.stderr)
  return overrides


def run_simulation(grid, bufs, toggles):
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
      brand="toyota",
      carFingerprint="TOYOTA_RAV4",
      openpilotLongitudinalControl=True,
      pcmCruise=False,
      steerRatio=15.0,
      wheelbase=2.7,
      longitudinalActuatorDelay=0.2,
      flags=0,
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

  cem = ConditionalExperimentalMode(planner_state)
  cem_ccm_detector = ConditionalExperimentalMode(planner_state)
  ccm = ConditionalChillMode(planner_state, cem_ccm_detector)
  hybrid = HybridExperimentalMode()
  hybrid.set_tuning(toggles.hybrid_exp_bias, toggles.hybrid_vision_brake_sensitivity)

  # Full openpilot Longitudinal Planner for true Chill (ACC) MPC execution
  chill_long_planner = LongitudinalPlanner(cp_candidate, dt=DT_MDL)

  n = len(grid)
  out = {
    "t": grid,
    "v_ego": np.zeros(n),
    "v_cruise": np.zeros(n),
    "model_v0": np.zeros(n),
    "lead_status": np.zeros(n, dtype=bool),
    "lead_dRel": np.zeros(n),
    "lead_vLead": np.zeros(n),
    "cem_exp": np.zeros(n, dtype=bool),
    "cem_status": np.zeros(n, dtype=int),
    "ccm_exp": np.zeros(n, dtype=bool),
    "ccm_status": np.zeros(n, dtype=int),
    "chill_active": np.zeros(n, dtype=bool),
    "logged_exp": np.zeros(n, dtype=bool),
    "logged_aTarget": np.zeros(n),
    "a_chill": np.zeros(n),
    "a_exp": np.zeros(n),
    "hem_a": np.zeros(n),
    "hem_authority": np.zeros(n),
  }

  real_monotonic = time.monotonic
  fake_clock = [0.0]
  time.monotonic = lambda: fake_clock[0]

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
      live_params = latest("liveParameters", t)
      car_control = latest("carControl", t)
      controls_state = latest("controlsState", t)
      car_params = latest("carParams", t) or cp_candidate

      controls_enabled = bool(getattr(sds, "enabled", False))
      conditional_tracking_active = controls_enabled or bool(getattr(scs, "alwaysOnLateralEnabled", False))

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

      model_length = 0.0
      if model_v2 is not None:
        try:
          pos_x = getattr(model_v2, "position", None)
          if pos_x is not None and len(pos_x.x):
            model_length = float(pos_x.x[-1])
        except Exception:
          model_length = 0.0

      forcing_stop = bool(getattr(splan, "forcingStop", False))
      raw_model_stopped = model_length < CRUISING_SPEED * PLANNER_TIME
      model_stopped = raw_model_stopped or forcing_stop

      road_curvature_detected = False
      if model_v2 is not None:
        try:
          road_curvature, _time_to_curve = calculate_road_curvature(model_v2, v_ego)
          road_curvature_detected = (
            (1 / abs(road_curvature)) ** 0.5 < v_ego > CRUISING_SPEED
            and not (car.leftBlinker or car.rightBlinker)
          )
        except Exception:
          road_curvature_detected = False

      try:
        curvature = float(getattr(controls_state, "curvature", 0.0))
      except Exception:
        curvature = 0.0
      lateral_accel = v_ego ** 2 * curvature
      driving_in_curve = abs(lateral_accel) >= MINIMUM_LATERAL_ACCELERATION

      lane_width_left = 0.0
      lane_width_right = 0.0
      if model_v2 is not None:
        try:
          lane_lines = getattr(model_v2, "laneLines", None)
          road_edges = getattr(model_v2, "roadEdges", None)
          if lane_lines is not None and len(lane_lines) >= 4:
            edge_left = road_edges[0] if road_edges is not None and len(road_edges) else None
            edge_right = road_edges[1] if road_edges is not None and len(road_edges) > 1 else None
            lane_width_left = calculate_lane_width(lane_lines[0], lane_lines[1], edge_left)
            lane_width_right = calculate_lane_width(lane_lines[3], lane_lines[2], edge_right)
        except Exception:
          pass

      t_follow = float(getattr(splan, "tFollow", 1.45))
      following_lead = tracking_lead and lead.dRel < (t_follow * 2) * v_ego
      slower_lead = False
      if (conditional_tracking_active and tracking_lead and toggles.conditional_slower_lead
          and lead.status and lead.vLead < v_ego):
        distance_factor = max(lead.dRel - (lead.vLead * t_follow), 1)
        braking_offset = float(np.clip(min(v_ego - lead.vLead, lead.vLead) - COMFORT_BRAKE, 1, distance_factor))
        slower_lead = braking_offset > 1

      planner_state.lead_one = lead
      planner_state.tracking_lead = tracking_lead
      planner_state.model_length = model_length
      planner_state.raw_model_stopped = raw_model_stopped
      planner_state.model_stopped = model_stopped
      planner_state.road_curvature_detected = road_curvature_detected
      planner_state.driving_in_curve = driving_in_curve
      planner_state.lane_width_left = lane_width_left
      planner_state.lane_width_right = lane_width_right
      planner_state.starpilot_following.following_lead = following_lead
      planner_state.starpilot_following.slower_lead = slower_lead
      planner_state.starpilot_vcruise.forcing_stop = forcing_stop

      raw_personality = getattr(sds, "personality", None)
      if hasattr(raw_personality, "raw"):
        personality_val = int(raw_personality.raw)
      elif isinstance(raw_personality, (int, float)):
        personality_val = int(raw_personality)
      else:
        personality_val = 0

      long_ctrl_state = getattr(controls_state, "longControlState", LongCtrlState.pid)

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
          enabled=controls_enabled,
          experimentalMode=False,  # Enforce ACC/Chill mode evaluation in MPC
          personality=personality_val,
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
          forcingStop=forcing_stop,
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
          longControlState=long_ctrl_state,
          forceDecel=bool(getattr(controls_state, "forceDecel", False)),
          curvature=curvature,
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

      # Run CEM / CCM State Machines
      if conditional_tracking_active:
        cem.update(v_ego, sm_dict, toggles, v_cruise)
        ccm.update(v_ego, v_cruise, sm_dict, toggles)
      else:
        cem.experimental_mode = False
        cem.status_value = CEStatus["OFF"]
        ccm.experimental_mode = True
        ccm.status_value = CCStatus["OFF"]

      chill_active = (not ccm.experimental_mode) and ccm.status_value in CC_AUTO_STATUSES

      # Compute accurate MPC Chill (ACC) Acceleration
      chill_long_planner.update(sm_dict, toggles)
      a_chill = float(chill_long_planner.output_a_target)

      # Determine realistic Exp acceleration target
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

      # Hybrid Experimental Mode continuous fusion
      a_hem, _should_stop_fused = hybrid.update(
        v_ego=v_ego, v_cruise=v_cruise, lead_one=lead, model_v2=model_v2,
        a_chill=a_chill, a_exp=a_exp,
      )
      authority = hybrid.w_vision

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
      out["lead_status"][i] = lead.status
      out["lead_dRel"][i] = lead.dRel
      out["lead_vLead"][i] = lead.vLead
      out["cem_exp"][i] = bool(cem.experimental_mode)
      out["cem_status"][i] = int(cem.status_value)
      out["ccm_exp"][i] = bool(ccm.experimental_mode)
      out["ccm_status"][i] = int(ccm.status_value)
      out["chill_active"][i] = chill_active
      out["logged_exp"][i] = bool(getattr(sds, "experimentalMode", False))
      out["logged_aTarget"][i] = float(getattr(lplan, "aTarget", 0.0))
      out["a_chill"][i] = a_chill
      out["a_exp"][i] = a_exp
      out["hem_a"][i] = a_hem
      out["hem_authority"][i] = authority
  finally:
    time.monotonic = real_monotonic

  return out


def intervals_for(t, keys):
  """Group consecutive identical non-zero status keys into [start, end, key] spans."""
  spans = []
  cur = 0
  for i, k in enumerate(keys):
    if k and k == cur:
      spans[-1][1] = t[i]
    elif k:
      spans.append([t[i], t[i], k])
      cur = k
    else:
      cur = 0
  return spans


def print_summary(out):
  t = out["t"]
  n = len(t)
  if n == 0:
    print("No simulation frames to summarize.")
    return

  v_ego_mph = out["v_ego"] * CV.MS_TO_MPH
  v_cruise_mph = out["v_cruise"] * CV.MS_TO_MPH
  standstill_mask = out["v_ego"] < 0.2
  standstill_pct = 100.0 * np.mean(standstill_mask)

  stops = 0
  for i in range(1, n):
    if standstill_mask[i] and not standstill_mask[i - 1]:
      stops += 1

  cem_switches = int(np.sum(np.diff(out["cem_exp"].astype(int)) != 0))
  ccm_switches = int(np.sum(np.diff(out["chill_active"].astype(int)) != 0))

  print("\n" + "=" * 78)
  print(f" MODE SIMULATION SUMMARY & TELEMETRY LOG  ({t[0]:.1f}s -> {t[-1]:.1f}s | {n} frames)")
  print("=" * 78)

  print("\n[1. DRIVE PROFILE]")
  print(f"  • Speed (v_ego)     : Min {v_ego_mph.min():.1f} mph | Avg {v_ego_mph.mean():.1f} mph | Max {v_ego_mph.max():.1f} mph")
  print(f"  • Cruise Set Speed  : Min {v_cruise_mph.min():.1f} mph | Avg {v_cruise_mph.mean():.1f} mph | Max {v_cruise_mph.max():.1f} mph")
  print(f"  • Standstill Time   : {standstill_pct:.1f}% ({stops} full stop events)")
  print(f"  • Lead Presence     : {100.0 * np.mean(out['lead_status']):.1f}% of route")

  print("\n[2. MODE INTENT & TRIGGER BREAKDOWN]")
  print(f"  • Logged (Actual)   : Exp {100.0 * out['logged_exp'].mean():.1f}%")
  print(f"  • CEM (Conditional) : Exp {100.0 * out['cem_exp'].mean():.1f}% | {cem_switches} mode toggles")
  cem_reasons = []
  for status_code, label in CE_LABELS.items():
    pct = 100.0 * np.mean((out["cem_status"] == status_code) & out["cem_exp"])
    if pct > 0.1:
      cem_reasons.append(f"{label}: {pct:.1f}%")
  if cem_reasons:
    print(f"    └─ CEM Active Triggers -> {', '.join(cem_reasons)}")

  print(f"  • Chill Mode (CCM)  : Chill {100.0 * out['chill_active'].mean():.1f}% | Exp {100.0 * out['ccm_exp'].mean():.1f}% | {ccm_switches} toggles")
  ccm_reasons = []
  for status_code, label in CC_LABELS.items():
    pct = 100.0 * np.mean((out["ccm_status"] == status_code) & out["chill_active"])
    if pct > 0.1:
      ccm_reasons.append(f"{label}: {pct:.1f}%")
  if ccm_reasons:
    print(f"    └─ Chill Active Reasons -> {', '.join(ccm_reasons)}")

  auth = out["hem_authority"]
  chill_dom = 100.0 * np.mean(auth < 0.35)
  blended = 100.0 * np.mean((auth >= 0.35) & (auth <= 0.65))
  exp_dom = 100.0 * np.mean(auth > 0.65)
  print(f"  • HEM (Hybrid)      : Mean Exp Authority {auth.mean():.2f}")
  print(f"    └─ Distribution   -> Chill-dominant (<0.35): {chill_dom:.1f}% | Blended (0.35-0.65): {blended:.1f}% | Exp-dominant (>0.65): {exp_dom:.1f}%")

  print("\n[3. ACCELERATION ENVELOPE (m/s²)]")
  print(f"  {'Signal':<16} | {'Min (Max Brake)':<15} | {'Mean':<10} | {'Max (Max Throttle)':<18}")
  print("  " + "-" * 66)
  print(f"  {'Logged aTarget':<16} | {out['logged_aTarget'].min():<15.2f} | {out['logged_aTarget'].mean():<10.2f} | {out['logged_aTarget'].max():<18.2f}")
  print(f"  {'Chill a':<16} | {out['a_chill'].min():<15.2f} | {out['a_chill'].mean():<10.2f} | {out['a_chill'].max():<18.2f}")
  print(f"  {'Exp a':<16} | {out['a_exp'].min():<15.2f} | {out['a_exp'].mean():<10.2f} | {out['a_exp'].max():<18.2f}")
  print(f"  {'HEM Fused a':<16} | {out['hem_a'].min():<15.2f} | {out['hem_a'].mean():<10.2f} | {out['hem_a'].max():<18.2f}")

  print("\n[4. KEY EVENT CHRONOLOGY (Sampled Significant Transitions)]")
  print(f"  {'Time (s)':<9} | {'vEgo':<8} | {'CEM Status':<12} | {'CCM':<7} | {'a_chill':<8} | {'a_exp':<8} | {'HEM a':<8} | {'Auth':<5} | Event Context")
  print("  " + "-" * 95)

  step = max(1, n // 18)
  sample_indices = set(range(0, n, step))

  hard_brakes = np.where(out["hem_a"] < -1.2)[0]
  if len(hard_brakes) > 0:
    sample_indices.update(hard_brakes[::max(1, len(hard_brakes)//4)])

  standstills = np.where(standstill_mask)[0]
  if len(standstills) > 0:
    sample_indices.update(standstills[::max(1, len(standstills)//3)])

  sorted_indices = sorted(list(sample_indices))[:22]

  for idx in sorted_indices:
    cur_t = t[idx] - t[0]
    ego_mph = v_ego_mph[idx]
    cem_st = CE_LABELS.get(out["cem_status"][idx], "OFF") if out["cem_exp"][idx] else "CHILL"
    ccm_st = "CHILL" if out["chill_active"][idx] else "EXP"
    ac = out["a_chill"][idx]
    ae = out["a_exp"][idx]
    ah = out["hem_a"][idx]
    au = out["hem_authority"][idx]

    ctx = []
    if out["lead_status"][idx]:
      ctx.append(f"Lead {out['lead_dRel'][idx]:.0f}m")
    if ego_mph < 1.0:
      ctx.append("Standstill")
    elif ah < -1.0:
      ctx.append("Braking")
    elif ah > 0.8:
      ctx.append("Accelerating")
    else:
      ctx.append("Cruising")

    if abs(ac - ae) > 1.0:
      ctx.append("Disagreement")

    context_str = ", ".join(ctx)
    print(f"  {cur_t:<9.1f} | {ego_mph:<5.1f}mph | {cem_st:<12} | {ccm_st:<7} | {ac:<8.2f} | {ae:<8.2f} | {ah:<8.2f} | {au:<5.2f} | {context_str}")

  print("=" * 78 + "\n")


def plot_results(out, toggles, args):
  import matplotlib
  if not args.show:
    matplotlib.use("Agg")
  import matplotlib.pyplot as plt

  t = out["t"]
  n = len(t)

  fig, (ax_speed, ax_mode, ax_accel) = plt.subplots(
    3, 1, figsize=(14, 10), sharex=True,
    gridspec_kw={"height_ratios": [2, 3, 2]},
  )
  fig.suptitle(f"Mode scenario estimate  {args.route}  seg {args.segment}", fontsize=11)

  ax_speed.plot(t, out["v_ego"] * CV.MS_TO_MPH, color="black", lw=1.4, label="v_ego")
  ax_speed.plot(t, out["v_cruise"] * CV.MS_TO_MPH, color="tab:blue", lw=1.0, ls="--", label="v_cruise")
  ax_speed.plot(t, out["model_v0"] * CV.MS_TO_MPH, color="tab:green", lw=1.0, alpha=0.7, label="model v[0]")
  ax_speed.set_ylabel("mph")
  ax_speed.legend(loc="upper right", fontsize=8, ncol=3)
  ax_speed.grid(alpha=0.3)

  rows = [
    ("Exp (always)", out["t"], np.ones(n, dtype=bool), "tab:blue", 3.0),
    ("CEM", out["t"], out["cem_exp"], "tab:orange", 2.0),
    ("Chill", out["t"], out["chill_active"], "tab:green", 1.0),
    ("Logged", out["t"], out["logged_exp"], "tab:gray", 0.0),
  ]
  for label, tt, active, color, ycenter in rows:
    ax_mode.fill_between(tt, ycenter - 0.28, ycenter + 0.28, where=active,
                         step="post", color=color, alpha=0.55, edgecolor="none")

  cem_spans = intervals_for(t, [out["cem_status"][i] if out["cem_exp"][i] else 0 for i in range(n)])
  for a, b, k in cem_spans:
    if b - a > 0.8 and k in CE_LABELS:
      ax_mode.text((a + b) / 2, 2.0 + 0.34, CE_LABELS[k], ha="center", fontsize=7, color="tab:orange")
  cc_spans = intervals_for(t, [out["ccm_status"][i] if out["chill_active"][i] else 0 for i in range(n)])
  for a, b, k in cc_spans:
    if b - a > 0.8 and k in CC_LABELS:
      ax_mode.text((a + b) / 2, 1.0 + 0.34, CC_LABELS[k], ha="center", fontsize=7, color="tab:green")

  ax_hem = ax_mode.twinx()
  ax_hem.plot(t, out["hem_authority"], color="tab:cyan", lw=1.2, label="HEM exp-authority")
  ax_hem.set_ylim(0, 1)
  ax_hem.set_ylabel("HEM exp authority", color="tab:cyan", fontsize=8)
  ax_hem.tick_params(axis="y", labelcolor="tab:cyan", labelsize=7)

  ax_mode.set_yticks([3.0, 2.0, 1.0, 0.0])
  ax_mode.set_yticklabels(["Exp", "CEM", "Chill", "Logged"])
  ax_mode.set_ylim(-0.6, 3.6)
  ax_mode.grid(axis="y", alpha=0.3)

  ax_accel.plot(t, out["logged_aTarget"], color="tab:gray", lw=1.2, label="logged aTarget")
  ax_accel.plot(t, out["a_chill"], color="tab:blue", lw=1.0, ls="--", label="chill (ACC) a")
  ax_accel.plot(t, out["a_exp"], color="tab:orange", lw=1.0, ls=":", label="exp (model) a")
  ax_accel.plot(t, out["hem_a"], color="tab:cyan", lw=1.4, label="HEM fused a")
  ax_accel.set_ylabel("accel (m/s²)")
  ax_accel.set_xlabel("time (s, segment-relative)")
  ax_accel.legend(loc="upper right", fontsize=8, ncol=2)
  ax_accel.grid(alpha=0.3)

  fig.tight_layout()
  if args.out:
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    print(f"Saved graph to {out_path}")
  if args.show:
    plt.show()
  plt.close(fig)


def main(argv=None):
  parser = argparse.ArgumentParser(
    description="Estimate CEM/Chill/HEM/Exp mode intent from a logged route and plot a comparison graph.")
  parser.add_argument("route", help="route (e.g. dongle|2023-07-27--13-01-19 or dongle/2023-07-27--13-01-19/0)")
  parser.add_argument("--segment", type=int, default=0, help="segment index (default 0)")
  parser.add_argument("--data_dir", help="local directory containing route files")
  parser.add_argument("--start", type=float, default=None, help="start seconds (segment-relative)")
  parser.add_argument("--end", type=float, default=None, help="end seconds (segment-relative)")
  parser.add_argument("--out", default="mode_sim.png", help="output PNG path")
  parser.add_argument("--show", action="store_true", help="show the plot window instead of saving only")
  parser.add_argument("--csv", default=None, help="optional CSV output of the time series")
  parser.add_argument("--set", action="append", default=[], metavar="KEY=value",
                      help="override a mode toggle, e.g. --set CESpeed=20 --set CEModelStopTime=3.0 --set CCMLead=false")
  args = parser.parse_args(argv)

  overrides = parse_toggle_overrides(args.set)
  defaults = dict(TOGGLE_DEFAULTS)
  defaults.update(overrides)
  toggles = SimpleNamespace(**defaults)
  for key, value in overrides.items():
    print(f"toggle override: {key} = {value}")

  identifiers = resolve_segment_identifier(args.route, args.segment, args.data_dir)
  if not identifiers:
    print(f"No segment data found for {args.route} seg {args.segment}", file=sys.stderr)
    return 1
  print(f"Loading: {identifiers}")
  bufs = load_buffers(identifiers, SERVICES)
  if not any(bufs[s] for s in SERVICES):
    print("No messages loaded.", file=sys.stderr)
    return 1

  all_min = min(t for s in SERVICES for t, _ in bufs[s])
  all_max = max(t for s in SERVICES for t, _ in bufs[s])
  start = all_min if args.start is None else all_min + args.start
  end = all_max if args.end is None else min(all_max, all_min + args.end)
  if end - start < DT_MDL:
    print(f"Empty time window [{start:.1f}, {end:.1f}]. Check --start/--end.", file=sys.stderr)
    return 1
  grid = np.arange(start, end, DT_MDL)
  print(f"Window: {start - all_min:.1f}s -> {end - all_min:.1f}s ({len(grid)} frames at {1 / DT_MDL:.0f} Hz)")

  out = run_simulation(grid, bufs, toggles)

  if args.csv:
    import csv
    csv_path = Path(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="") as f:
      writer = csv.writer(f)
      writer.writerow(["t", "v_ego", "v_cruise", "model_v0", "cem_exp", "cem_status",
                       "ccm_exp", "ccm_status", "chill_active", "logged_exp", "logged_aTarget",
                       "a_chill", "a_exp", "hem_a", "hem_authority"])
      for i in range(len(out["t"])):
        writer.writerow([out["t"][i], out["v_ego"][i], out["v_cruise"][i], out["model_v0"][i],
                         int(out["cem_exp"][i]), out["cem_status"][i],
                         int(out["ccm_exp"][i]), out["ccm_status"][i], int(out["chill_active"][i]),
                         int(out["logged_exp"][i]), out["logged_aTarget"][i],
                         out["a_chill"][i], out["a_exp"][i], out["hem_a"][i], out["hem_authority"][i]])
    print(f"Saved CSV to {csv_path}")

  print_summary(out)
  plot_results(out, toggles, args)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())