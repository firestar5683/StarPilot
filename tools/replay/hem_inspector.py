#!/usr/bin/env python3
"""HEM Live Inspector & Diagnostic Studio.

An interactive, live-scrubbing telemetry debugger for Hybrid Experimental Mode (HEM)
and Pure Experimental Mode comparisons.
"""
from __future__ import annotations

import argparse
import bisect
import http.server
import json
import os
import socketserver
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

# Ensure openpilot root is in sys.path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
  sys.path.insert(0, str(ROOT_DIR))

from openpilot.common.constants import CV
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.car.cruise import V_CRUISE_MAX, V_CRUISE_UNSET
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.starpilot.controls.lib.hybrid_experimental_mode import HybridExperimentalMode
from openpilot.tools.lib.logreader import LogReader, ReadMode, parse_direct, parse_indirect
from openpilot.tools.lib.route import SegmentRange

SERVICES = {
  "carState", "radarState", "starpilotRadarState", "modelV2",
  "longitudinalPlan", "selfdriveState", "starpilotPlan", "starpilotCarState",
  "controlsState", "carParams", "liveParameters", "carControl",
}


def as_lead(raw):
  if raw is None:
    return SimpleNamespace(status=False, dRel=150.0, yRel=0.0, vRel=0.0, aRel=0.0,
                           vLead=0.0, vLeadK=0.0, dPath=0.0, vLat=0.0, aLeadK=0.0,
                           aLeadTau=1.5, fcw=False, modelProb=0.0, radar=False)
  return SimpleNamespace(
    status=bool(getattr(raw, "status", False)),
    dRel=float(getattr(raw, "dRel", 150.0)),
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


def load_route_data(route_str: str, segment: int, data_dir: str | None = None):
  print(f"[HEM Inspector] Resolving route: {route_str} (segment {segment})...")
  direct = parse_direct(route_str)
  if direct is not None:
    identifiers = [str(direct)]
  else:
    parsed = parse_indirect(route_str)
    sr = SegmentRange(parsed)
    route_name = sr.route_name.replace("/", "|")
    identifiers = [f"{route_name}--{segment}"]

  bufs = {s: [] for s in SERVICES}
  for identifier in identifiers:
    try:
      lr = LogReader(identifier, default_mode=ReadMode.RLOG)
    except Exception as exc:
      print(f"[HEM Inspector] Error reading {identifier}: {exc}", file=sys.stderr)
      return None

    for evt in lr:
      which = evt.which()
      if which in SERVICES:
        t = evt.logMonoTime * 1e-9
        bufs[which].append((t, getattr(evt, which)))

  for s in SERVICES:
    bufs[s].sort(key=lambda x: x[0])

  if not any(bufs[s] for s in SERVICES):
    print("[HEM Inspector] No telemetry messages found in segment.", file=sys.stderr)
    return None

  return bufs


def run_hem_replay(bufs, start_sec: float | None, end_sec: float | None, toggles: Any):
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

  req_services = [s for s in ("modelV2", "carState") if len(bufs.get(s, []))]
  all_min = max(bufs[s][0][0] for s in req_services) if req_services else min(t for s in SERVICES for t, _ in bufs[s] if len(bufs[s]))
  all_max = max(t for s in SERVICES for t, _ in bufs[s] if len(bufs[s]))
  start = all_min if start_sec is None else all_min + start_sec
  end = all_max if end_sec is None else min(all_max, all_min + end_sec)
  grid = np.arange(start, end, DT_MDL)

  planner = LongitudinalPlanner(cp_candidate, dt=DT_MDL)
  hybrid = HybridExperimentalMode()
  hybrid.record_diag = True
  hybrid.set_tuning(getattr(toggles, "hybrid_exp_bias", 0.0), getattr(toggles, "hybrid_vision_brake_sensitivity", 1.0))

  frames = []
  stop_events = []

  real_monotonic = time.monotonic
  fake_clock = [0.0]
  time.monotonic = lambda: fake_clock[0]

  try:
    for i, t in enumerate(grid):
      fake_clock[0] = float(i) * DT_MDL
      t_rel = round(t - all_min, 3)

      car_raw = latest("carState", t)
      model_v2 = latest("modelV2", t)
      if model_v2 is None or car_raw is None:
        continue
      v_ego = max(float(getattr(car_raw, "vEgo", 0.0)), 0.0)
      car = SimpleNamespace(
        vEgo=v_ego,
        vEgoCluster=max(float(getattr(car_raw, "vEgoCluster", v_ego)), 0.0),
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

      radar = latest("radarState", t)
      lead1 = as_lead(getattr(radar, "leadOne", None) if radar else None)
      lead2 = as_lead(getattr(radar, "leadTwo", None) if radar else None)

      lplan = latest("longitudinalPlan", t)
      sds = latest("selfdriveState", t)
      splan = latest("starpilotPlan", t)
      scs = latest("starpilotCarState", t)
      live_params = latest("liveParameters", t)
      car_control = latest("carControl", t)
      controls_state = latest("controlsState", t)

      # Logged in-drive states
      logged_exp_mode = bool(getattr(sds, "experimentalMode", False))
      logged_a_target = float(getattr(lplan, "aTarget", 0.0)) if lplan else 0.0
      logged_should_stop = bool(getattr(lplan, "shouldStop", False)) if lplan else False

      v_cruise = float(getattr(splan, "vCruise", 0.0) or 0.0)
      if not (v_cruise > 0):
        v_cruise_kph = float(getattr(car_raw, "vCruise", 0.0) or 0.0)
        v_cruise = min(v_cruise_kph, V_CRUISE_MAX) * CV.KPH_TO_MS if 0 < v_cruise_kph < V_CRUISE_UNSET else v_ego

      tracking_lead = bool(getattr(splan, "trackingLead", False) or getattr(lplan, "hasLead", False))
      t_follow = float(getattr(splan, "tFollow", 1.45))
      forcing_stop = bool(getattr(splan, "forcingStop", False))

      sm_dict = {
        "carState": car,
        "radarState": SimpleNamespace(leadOne=lead1, leadTwo=lead2),
        "starpilotRadarState": SimpleNamespace(leadLeft=as_lead(None), leadRight=as_lead(None)),
        "starpilotCarState": SimpleNamespace(
          trafficModeEnabled=bool(getattr(scs, "trafficModeEnabled", False)),
          alwaysOnLateralEnabled=bool(getattr(scs, "alwaysOnLateralEnabled", False)),
          accelPressed=bool(getattr(scs, "accelPressed", False)),
        ),
        "selfdriveState": SimpleNamespace(
          enabled=bool(getattr(sds, "enabled", False)),
          experimentalMode=False,
          personality=int(getattr(getattr(sds, "personality", None), "raw", 0)),
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
          longControlState=getattr(controls_state, "longControlState", LongCtrlState.pid),
          forceDecel=bool(getattr(controls_state, "forceDecel", False)),
          curvature=float(getattr(controls_state, "curvature", 0.0)),
        ),
        "liveParameters": SimpleNamespace(
          angleOffsetDeg=float(getattr(live_params, "angleOffsetDeg", 0.0)) if live_params else 0.0,
        ),
        "carControl": SimpleNamespace(
          orientationNED=getattr(car_control, "orientationNED", [0.0, 0.0, 0.0]) if car_control else [0.0, 0.0, 0.0],
        ),
        "modelV2": model_v2,
        "carParams": cp_candidate,
      }

      # 1. Update Chill Planner (ACC MPC Baseline)
      planner.update(sm_dict, toggles)
      a_chill = float(planner.output_a_target)
      should_stop_chill = bool(planner.output_should_stop)

      # 2. Extract Vision NN Action Intent & Horizon Metrics
      a_exp = 0.0
      should_stop_exp = False
      stop_line_prob = 0.0
      stop_line_dist = 0.0
      if model_v2 is not None:
        act = getattr(model_v2, "action", None)
        if act is not None:
          a_exp = float(getattr(act, "desiredAcceleration", 0.0))
          should_stop_exp = bool(getattr(act, "shouldStop", False))

        stop_line = getattr(model_v2, "stopLine", None)
        if stop_line is not None:
          stop_line_prob = float(getattr(stop_line, "prob", 0.0))
          stop_line_dist = float(getattr(stop_line, "distance", 0.0))

      # 3. Step HEM Fusion Machine
      active_lead = lead2 if planner.mpc.source == "lead1" else lead1
      a_fused, should_stop_fused = hybrid.update(
        v_ego=v_ego, v_cruise=v_cruise, lead_one=active_lead,
        model_v2=model_v2, a_chill=a_chill, a_exp=a_exp,
        should_stop_exp=should_stop_exp, should_stop_chill=should_stop_chill,
        gas_pressed=car.gasPressed,
      )

      diag_dump = dict(hybrid.diag) if hasattr(hybrid, "diag") else {}
      exp_dominant = bool(getattr(hybrid, "last_exp_dominant", False) or hybrid.w_vision > 0.65)

      if should_stop_exp or (exp_dominant and a_exp < -1.0) or (logged_should_stop and logged_exp_mode):
        if not stop_events or (t_rel - stop_events[-1]["time"]) > 3.0:
          stop_events.append({"time": t_rel, "reason": "Stop Detected" if (should_stop_exp or logged_should_stop) else "Vision Decel"})

      frame_payload = {
        "idx": i,
        "t": t_rel,
        "v_ego": round(v_ego, 2),
        "v_ego_mph": round(v_ego * CV.MS_TO_MPH, 1),
        "v_cruise_mph": round(v_cruise * CV.MS_TO_MPH, 1),
        "a_ego": round(car.aEgo, 2),
        "gas_pressed": car.gasPressed,
        "brake_pressed": car.brakePressed,
        "standstill": car.standstill,
        "logged_drive": {
          "experimental_mode": logged_exp_mode,
          "a_target": round(logged_a_target, 2),
          "should_stop": logged_should_stop,
        },
        "lead": {
          "status": active_lead.status,
          "dRel": round(active_lead.dRel, 1),
          "vLead": round(active_lead.vLead, 1),
          "aLeadK": round(active_lead.aLeadK, 2),
          "radar": active_lead.radar,
        },
        "model": {
          "should_stop_exp": should_stop_exp,
          "a_exp": round(a_exp, 2),
          "stop_line_prob": round(stop_line_prob, 3),
          "stop_line_dist": round(stop_line_dist, 1),
        },
        "planner": {
          "a_chill": round(a_chill, 2),
          "should_stop_chill": should_stop_chill,
          "mpc_source": planner.mpc.source,
          "v_desired_now": round(float(planner.v_desired_trajectory[0]), 2) if len(planner.v_desired_trajectory) else 0.0,
        },
        "hem": {
          "a_fused": round(a_fused, 2),
          "should_stop_fused": should_stop_fused,
          "w_vision": round(float(hybrid.w_vision), 3),
          "exp_dominant": exp_dominant,
          "diag": diag_dump,
        },
      }
      frames.append(frame_payload)
  finally:
    time.monotonic = real_monotonic

  return frames, stop_events


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>HEM & Pure EXP Live Inspector</title>
<style>
  :root {
    --bg: #0f1117; --panel: #181b23; --border: #282c37; --text: #e1e4ea;
    --accent: #3b82f6; --exp-orange: #ff9800; --chill-blue: #0ea5e9; --danger: #ef4444; --green: #22c55e; --logged-purple: #c084fc;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  body { background: var(--bg); color: var(--text); display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
  header { background: var(--panel); border-bottom: 1px solid var(--border); padding: 8px 16px; display: flex; justify-content: space-between; align-items: center; }
  .title { font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
  .badge { background: #334155; padding: 2px 7px; border-radius: 4px; font-size: 11px; text-transform: uppercase; }
  .badge.orange { background: #7c2d12; color: #ffedd5; border: 1px solid var(--exp-orange); }
  .badge.purple { background: #581c87; color: #f3e8ff; border: 1px solid var(--logged-purple); }

  .export-bar { display: flex; align-items: center; gap: 6px; background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 4px 10px; }
  .export-bar label { font-size: 11px; color: #94a3b8; font-weight: 600; }
  .export-bar input { width: 55px; background: #0f1117; color: #38bdf8; border: 1px solid #475569; border-radius: 4px; padding: 3px 6px; font-size: 12px; font-weight: bold; text-align: center; }

  .main-layout { display: grid; grid-template-columns: 1fr 380px; flex: 1; overflow: hidden; }
  .left-pane { display: flex; flex-direction: column; padding: 12px; gap: 12px; overflow-y: auto; }
  .right-pane { background: var(--panel); border-left: 1px solid var(--border); padding: 12px; display: flex; flex-direction: column; gap: 12px; overflow-y: auto; }

  .card { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 12px; position: relative; }
  .card.hem-border-active { border: 2px solid var(--exp-orange); box-shadow: 0 0 15px rgba(255, 152, 0, 0.25); }
  .card-title { font-size: 11px; font-weight: 600; text-transform: uppercase; color: #94a3b8; margin-bottom: 8px; display: flex; justify-content: space-between; }

  .controls-bar { display: flex; align-items: center; gap: 8px; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; }
  button { background: #334155; color: white; border: none; border-radius: 5px; padding: 5px 10px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
  button:hover { background: #475569; }
  button.primary { background: var(--accent); }
  button.primary:hover { background: #2563eb; }
  button.copy-btn { background: #059669; }
  button.copy-btn:hover { background: #047857; }

  .slider-container { flex: 1; display: flex; flex-direction: column; gap: 3px; }
  input[type=range] { width: 100%; accent-color: var(--accent); cursor: pointer; }

  .canvas-container { position: relative; height: 165px; width: 100%; }
  canvas { width: 100%; height: 100%; display: block; }

  .metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .metric-box { background: #0f1117; border: 1px solid var(--border); border-radius: 6px; padding: 6px; text-align: center; }
  .metric-val { font-size: 15px; font-weight: 700; margin-top: 2px; }
  .metric-lbl { font-size: 10px; color: #64748b; text-transform: uppercase; }

  .meter { height: 8px; background: #334155; border-radius: 4px; overflow: hidden; margin-top: 5px; }
  .meter-fill { height: 100%; width: 0%; background: linear-gradient(90deg, var(--chill-blue), var(--exp-orange)); transition: width 0.05s; }

  table.diag-table { width: 100%; border-collapse: collapse; font-size: 11px; font-family: monospace; }
  table.diag-table td { padding: 3px 5px; border-bottom: 1px solid #232733; }
  table.diag-table td.key { color: #94a3b8; }
  table.diag-table td.val { text-align: right; color: #38bdf8; font-weight: 600; }

  .events-list { display: flex; flex-wrap: wrap; gap: 6px; max-height: 70px; overflow-y: auto; }
  .event-chip { background: #1e293b; border: 1px solid #334155; border-radius: 4px; padding: 3px 8px; font-size: 11px; cursor: pointer; }
  .event-chip:hover { border-color: var(--exp-orange); color: var(--exp-orange); }
</style>
</head>
<body>

<header>
  <div class="title">
    <span>🚘 HEM & Pure EXP Inspector</span>
    <span id="driveModeBadge" class="badge">DRIVE: CHILL</span>
    <span id="expBadge" class="badge">CHILL DOMINANT</span>
    <span id="stopSignBadge" class="badge orange" style="display:none;">🛑 STOP DETECTED</span>
  </div>
  <div style="display: flex; gap: 8px; align-items: center;">
    <div class="export-bar">
      <label>Window:</label>
      <input type="number" id="exportStart" value="12" step="0.5">
      <span style="color:#64748b;">to</span>
      <input type="number" id="exportEnd" value="19" step="0.5">
      <label>sec</label>
      <button onclick="setExportWindowToCurrent()" style="padding:3px 6px; font-size:10px;">📍 Here ±3s</button>
    </div>
    <button class="copy-btn" onclick="copyDiagnosticRange()">📋 Copy Range Log (for AI)</button>
    <button onclick="copySingleSnapshot()" style="background:#334155;">📷 1-Frame</button>
  </div>
</header>

<div class="main-layout">
  <div class="left-pane">
    <div class="controls-bar">
      <button onclick="togglePlay()" id="playBtn">▶ Play</button>
      <button onclick="step(-1)">❮ 50ms</button>
      <button onclick="step(1)">50ms ❯</button>
      <button onclick="step(-20)">❮ 1s</button>
      <button onclick="step(20)">1s ❯</button>
      <div class="slider-container">
        <input type="range" id="timeSlider" min="0" max="100" step="1" value="0" oninput="onSlider(this.value)">
        <div style="display:flex; justify-content:space-between; font-size:11px; color:#64748b;">
          <span id="curTimeLbl">0.00s</span>
          <span id="totalTimeLbl">0.00s</span>
        </div>
      </div>
      <select id="speedSel" onchange="playbackSpeed = parseFloat(this.value)" style="background:#334155; color:white; border:none; padding:4px 6px; border-radius:4px; font-size:11px;">
        <option value="0.1">0.1x (Slow)</option>
        <option value="0.25">0.25x</option>
        <option value="0.5">0.5x</option>
        <option value="1.0" selected>1.0x</option>
        <option value="2.0">2.0x</option>
      </select>
    </div>

    <div class="card" style="padding:8px 12px;">
      <div class="card-title">Jump to Events / Stop Candidates</div>
      <div class="events-list" id="eventsList"></div>
    </div>

    <div class="card" id="mainCard">
      <div class="card-title">
        <span>Acceleration Trajectory Comparison (m/s²)</span>
        <span style="display:flex; gap:10px; font-size:10px;">
          <span style="color:#c084fc; font-weight:bold;">━ a_logged (Car)</span>
          <span style="color:#ff9800;">■ a_exp (Model)</span>
          <span style="color:#0ea5e9;">■ a_chill (MPC)</span>
          <span style="color:#38bdf8; font-weight:bold;">━ a_fused (HEM)</span>
        </span>
      </div>
      <div class="canvas-container">
        <canvas id="accelCanvas"></canvas>
      </div>
    </div>

    <div class="metric-grid">
      <div class="metric-box">
        <div class="metric-lbl">Speed (Ego / Set)</div>
        <div class="metric-val" id="mSpeed">0 / 0 <span style="font-size:10px; font-weight:normal;">mph</span></div>
      </div>
      <div class="metric-box">
        <div class="metric-lbl">Logged Drive Accel</div>
        <div class="metric-val" id="mLogged" style="color:#c084fc;">0.00 <span style="font-size:10px; font-weight:normal;">m/s²</span></div>
      </div>
      <div class="metric-box">
        <div class="metric-lbl">Simulated HEM Accel</div>
        <div class="metric-val" id="mFused" style="color:#38bdf8;">0.00 <span style="font-size:10px; font-weight:normal;">m/s²</span></div>
      </div>
      <div class="metric-box">
        <div class="metric-lbl">Lead Distance</div>
        <div class="metric-val" id="mLead">None</div>
      </div>
    </div>
  </div>

  <div class="right-pane">
    <div class="card">
      <div class="card-title">HEM Authority (Vision Weight)</div>
      <div style="display:flex; justify-content:space-between; font-size:16px; font-weight:bold;">
        <span id="authVal">0.00</span>
        <span id="authDesc" style="font-size:11px; color:#94a3b8;">Chill Cruise Mode</span>
      </div>
      <div class="meter"><div class="meter-fill" id="authMeter"></div></div>
    </div>

    <div class="card">
      <div class="card-title">Stop Intent Matrix</div>
      <table class="diag-table">
        <tr><td class="key">Logged In-Car Mode</td><td class="val" id="dLoggedMode">CHILL</td></tr>
        <tr><td class="key">Logged In-Car Stop</td><td class="val" id="dLoggedStop">False</td></tr>
        <tr><td class="key">model.shouldStop (Exp)</td><td class="val" id="dModelStop">False</td></tr>
        <tr><td class="key">planner.shouldStop (Chill)</td><td class="val" id="dChillStop">False</td></tr>
        <tr><td class="key">HEM Fused shouldStop</td><td class="val" id="dFusedStop">False</td></tr>
        <tr><td class="key">Stop Line Prob / Dist</td><td class="val" id="dStopLine">0.00 / 0.0m</td></tr>
      </table>
    </div>

    <div class="card" style="flex:1;">
      <div class="card-title">HEM Internal Diag State Dump</div>
      <table class="diag-table" id="diagTableBody"></table>
    </div>
  </div>
</div>

<script>
let frames = [];
let curIdx = 0;
let isPlaying = false;
let playbackSpeed = 1.0;
let playTimer = null;

fetch('/api/data').then(r => r.json()).then(data => {
  frames = data.frames;
  document.getElementById('timeSlider').max = frames.length - 1;
  const maxT = frames[frames.length - 1].t;
  document.getElementById('totalTimeLbl').innerText = maxT.toFixed(2) + 's';

  const el = document.getElementById('eventsList');
  if (data.events.length === 0) el.innerHTML = '<span style="font-size:11px; color:#64748b;">No high-decel stop events found.</span>';
  data.events.forEach(ev => {
    const chip = document.createElement('div');
    chip.className = 'event-chip';
    chip.innerText = `⏱ ${ev.time.toFixed(1)}s - ${ev.reason}`;
    chip.onclick = () => {
      seekTime(ev.time);
      document.getElementById('exportStart').value = Math.max(0, ev.time - 3).toFixed(1);
      document.getElementById('exportEnd').value = Math.min(maxT, ev.time + 3).toFixed(1);
    };
    el.appendChild(chip);
  });

  render();
});

function setExportWindowToCurrent() {
  if (!frames.length) return;
  const t = frames[curIdx].t;
  const maxT = frames[frames.length - 1].t;
  document.getElementById('exportStart').value = Math.max(0, t - 3.0).toFixed(1);
  document.getElementById('exportEnd').value = Math.min(maxT, t + 3.0).toFixed(1);
}

function onSlider(v) {
  curIdx = parseInt(v);
  render();
}

function step(delta) {
  curIdx = Math.max(0, Math.min(frames.length - 1, curIdx + delta));
  document.getElementById('timeSlider').value = curIdx;
  render();
}

function seekTime(targetT) {
  let best = 0;
  for (let i = 0; i < frames.length; i++) {
    if (frames[i].t >= targetT) { best = i; break; }
  }
  curIdx = best;
  document.getElementById('timeSlider').value = curIdx;
  render();
}

function togglePlay() {
  isPlaying = !isPlaying;
  document.getElementById('playBtn').innerText = isPlaying ? '⏸ Pause' : '▶ Play';
  if (isPlaying) scheduleNextFrame();
  else clearTimeout(playTimer);
}

function scheduleNextFrame() {
  if (!isPlaying) return;
  step(1);
  if (curIdx >= frames.length - 1) { togglePlay(); return; }
  playTimer = setTimeout(scheduleNextFrame, (50 / playbackSpeed));
}

function render() {
  if (!frames.length) return;
  const f = frames[curIdx];
  document.getElementById('curTimeLbl').innerText = f.t.toFixed(2) + 's';

  // Drive Mode
  const dmb = document.getElementById('driveModeBadge');
  if (f.logged_drive.experimental_mode) {
    dmb.innerText = 'LOGGED DRIVE: PURE EXP';
    dmb.className = 'badge purple';
  } else {
    dmb.innerText = 'LOGGED DRIVE: CHILL/HEM';
    dmb.className = 'badge';
  }

  // Badges & border
  const expBadge = document.getElementById('expBadge');
  const mainCard = document.getElementById('mainCard');
  if (f.hem.exp_dominant) {
    expBadge.innerText = 'HEM EXP DOMINANT';
    expBadge.className = 'badge orange';
    mainCard.className = 'card hem-border-active';
  } else {
    expBadge.innerText = 'HEM CHILL DOMINANT';
    expBadge.className = 'badge';
    mainCard.className = 'card';
  }
  document.getElementById('stopSignBadge').style.display = (f.model.should_stop_exp || f.logged_drive.should_stop) ? 'inline-block' : 'none';

  // Metrics
  document.getElementById('mSpeed').innerText = `${f.v_ego_mph} / ${f.v_cruise_mph}`;
  document.getElementById('mLogged').innerText = f.logged_drive.a_target.toFixed(2);
  document.getElementById('mFused').innerText = f.hem.a_fused.toFixed(2);
  document.getElementById('mLead').innerText = f.lead.status ? `${f.lead.dRel}m (${f.lead.vLead} m/s)` : 'None';

  // Authority
  document.getElementById('authVal').innerText = f.hem.w_vision.toFixed(2);
  document.getElementById('authMeter').style.width = (f.hem.w_vision * 100) + '%';
  document.getElementById('authDesc').innerText = f.hem.w_vision > 0.65 ? 'Vision Dominant' : (f.hem.w_vision < 0.35 ? 'ACC Chill Dominant' : 'Blended Authority');

  // Intent
  document.getElementById('dLoggedMode').innerText = f.logged_drive.experimental_mode ? 'PURE EXPERIMENTAL' : 'CHILL / MPC';
  document.getElementById('dLoggedMode').style.color = f.logged_drive.experimental_mode ? '#c084fc' : '#38bdf8';
  document.getElementById('dLoggedStop').innerText = f.logged_drive.should_stop ? '🛑 TRUE' : 'False';
  document.getElementById('dLoggedStop').style.color = f.logged_drive.should_stop ? '#ef4444' : '#94a3b8';
  document.getElementById('dModelStop').innerText = f.model.should_stop_exp ? '🛑 TRUE' : 'False';
  document.getElementById('dModelStop').style.color = f.model.should_stop_exp ? '#ef4444' : '#94a3b8';
  document.getElementById('dChillStop').innerText = f.planner.should_stop_chill ? 'TRUE' : 'False';
  document.getElementById('dFusedStop').innerText = f.hem.should_stop_fused ? '🛑 TRUE' : 'False';
  document.getElementById('dFusedStop').style.color = f.hem.should_stop_fused ? '#ef4444' : '#94a3b8';
  document.getElementById('dStopLine').innerText = `${f.model.stop_line_prob} / ${f.model.stop_line_dist}m`;

  // Diag Table
  const tbody = document.getElementById('diagTableBody');
  tbody.innerHTML = '';
  for (const [k, v] of Object.entries(f.hem.diag)) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td class="key">${k}</td><td class="val">${typeof v === 'number' ? v.toFixed(3) : v}</td>`;
    tbody.appendChild(tr);
  }

  drawGraph();
}

function drawGraph() {
  const canvas = document.getElementById('accelCanvas');
  const ctx = canvas.getContext('2d');
  canvas.width = canvas.parentElement.clientWidth;
  canvas.height = canvas.parentElement.clientHeight;
  const w = canvas.width, h = canvas.height;

  ctx.clearRect(0, 0, w, h);

  const zeroY = h * 0.45;
  ctx.strokeStyle = '#334155';
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(0, zeroY); ctx.lineTo(w, zeroY); ctx.stroke();

  const span = 60;
  const start = Math.max(0, curIdx - span/2);
  const end = Math.min(frames.length - 1, start + span);
  const scaleY = h / 7.0;

  function plotLine(keyFn, color, width, dash = []) {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.setLineDash(dash);
    ctx.beginPath();
    for (let i = start; i <= end; i++) {
      const x = ((i - start) / span) * w;
      const val = keyFn(frames[i]);
      const y = zeroY - val * scaleY;
      if (i === start) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }

  plotLine(f => f.logged_drive.a_target, '#c084fc', 2.0, [3, 2]); // Actual logged drive
  plotLine(f => f.planner.a_chill, '#0ea5e9', 1.2, [4, 4]);       // Chill MPC
  plotLine(f => f.model.a_exp, '#ff9800', 1.2, [2, 2]);           // Vision Model
  plotLine(f => f.hem.a_fused, '#38bdf8', 2.2);                   // Simulated HEM

  // Cursor
  const curX = ((curIdx - start) / span) * w;
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(curX, 0); ctx.lineTo(curX, h); ctx.stroke();
}

function copySingleSnapshot() {
  const f = frames[curIdx];
  const payload = {
    diagnostic_type: "HEM_SINGLE_FRAME_SNAPSHOT",
    timestamp_sec: f.t,
    logged_actual_drive: f.logged_drive,
    vehicle_state: {
      v_ego_mph: f.v_ego_mph,
      a_ego: f.a_ego,
      gas_pressed: f.gas_pressed,
      brake_pressed: f.brake_pressed,
      standstill: f.standstill,
    },
    lead: f.lead,
    model_vision: f.model,
    planner_acc_mpc: f.planner,
    hem_fusion_engine: f.hem,
  };

  const md = "```json\\n" + JSON.stringify(payload, null, 2) + "\\n```";
  navigator.clipboard.writeText(md).then(() => {
    alert("Copied 1-frame snapshot to clipboard!");
  });
}

function copyDiagnosticRange() {
  const startT = parseFloat(document.getElementById('exportStart').value) || 0.0;
  const endT = parseFloat(document.getElementById('exportEnd').value) || 0.0;

  if (startT >= endT) {
    alert("Start time must be strictly less than End time.");
    return;
  }

  const subset = frames.filter(f => f.t >= startT && f.t <= endT);
  if (!subset.length) {
    alert("No telemetry frames found in specified time range.");
    return;
  }

  let shouldStopFlicks = 0;
  let expDominantFlicks = 0;
  let leadStatusFlicks = 0;
  let minALogged = 999.0;
  let minAExp = 999.0;
  let minAChill = 999.0;
  let minAFused = 999.0;
  let maxWVision = 0.0;
  let minWVision = 1.0;
  let isPureExpRun = subset.some(f => f.logged_drive.experimental_mode);

  for (let i = 0; i < subset.length; i++) {
    const cur = subset[i];
    minALogged = Math.min(minALogged, cur.logged_drive.a_target);
    minAExp = Math.min(minAExp, cur.model.a_exp);
    minAChill = Math.min(minAChill, cur.planner.a_chill);
    minAFused = Math.min(minAFused, cur.hem.a_fused);
    maxWVision = Math.max(maxWVision, cur.hem.w_vision);
    minWVision = Math.min(minWVision, cur.hem.w_vision);

    if (i > 0) {
      const prev = subset[i - 1];
      if (cur.model.should_stop_exp !== prev.model.should_stop_exp) shouldStopFlicks++;
      if (cur.hem.exp_dominant !== prev.hem.exp_dominant) expDominantFlicks++;
      if (cur.lead.status !== prev.lead.status) leadStatusFlicks++;
    }
  }

  let tableMd = "| Time(s) | vEgo(mph) | a_logged | a_exp | a_chill | a_fused | w_vis | ExpStop | LoggedStop | FusedStop | Lead(dRel,vRel) | Gas/Brk |\\n";
  tableMd    += "|---------|-----------|----------|-------|---------|---------|-------|---------|------------|-----------|-----------------|---------|\\n";

  subset.forEach(f => {
    const leadStr = f.lead.status ? `${f.lead.dRel}m@${f.lead.vLead}m/s` : "None";
    const gasBrk = f.gas_pressed ? "GAS" : (f.brake_pressed ? "BRK" : "-");

    tableMd += `| ${f.t.toFixed(2).padStart(5)} | ` +
               `${f.v_ego_mph.toFixed(1).padStart(5)} | ` +
               `${f.logged_drive.a_target.toFixed(2).padStart(8)} | ` +
               `${f.model.a_exp.toFixed(2).padStart(5)} | ` +
               `${f.planner.a_chill.toFixed(2).padStart(7)} | ` +
               `${f.hem.a_fused.toFixed(2).padStart(7)} | ` +
               `${f.hem.w_vision.toFixed(2).padStart(5)} | ` +
               `${(f.model.should_stop_exp ? "🛑TRUE" : "false").padEnd(7)} | ` +
               `${(f.logged_drive.should_stop ? "🛑TRUE" : "false").padEnd(10)} | ` +
               `${(f.hem.should_stop_fused ? "🛑TRUE" : "false").padEnd(9)} | ` +
               `${leadStr.padEnd(15)} | ` +
               `${gasBrk.padEnd(7)} |\\n`;
  });

  const fullReport = `# Telemetry Investigation Report (Pure EXP vs HEM Diagnostic)
**Range:** ${startT.toFixed(2)}s to ${endT.toFixed(2)}s (${subset.length} frames @ 20Hz, ${(subset.length * 0.05).toFixed(1)}s duration)
**Logged Drive Mode on Car:** \`${isPureExpRun ? "PURE EXPERIMENTAL MODE" : "CHILL / HEM MODE"}\`

## 1. Executive Summary & Accel Comparisons
- **Actual Commanded In-Drive Accel (a_logged):** min \`${minALogged.toFixed(2)} m/s²\`
- **Vision Model Action Accel (a_exp):** min \`${minAExp.toFixed(2)} m/s²\`
- **Simulated ACC MPC Accel (a_chill):** min \`${minAChill.toFixed(2)} m/s²\`
- **Simulated HEM Fused Accel (a_fused):** min \`${minAFused.toFixed(2)} m/s²\`
- **HEM Vision Authority Range (w_vision):** \`[${minWVision.toFixed(2)}, ${maxWVision.toFixed(2)}]\`
- **Vision Stop Intent Flickers (should_stop_exp toggles):** \`${shouldStopFlicks}\`
- **Lead Target Status Flips:** \`${leadStatusFlicks}\`

## 2. High-Density Replay Telemetry
${tableMd}

## 3. Key Frame Dumps (Start, Peak Braking, End)
\`\`\`json
${JSON.stringify({
  frame_start: subset[0],
  frame_min_a_logged: subset.reduce((prev, curr) => (curr.logged_drive.a_target < prev.logged_drive.a_target ? curr : prev), subset[0]),
  frame_min_a_exp: subset.reduce((prev, curr) => (curr.model.a_exp < prev.model.a_exp ? curr : prev), subset[0]),
  frame_end: subset[subset.length - 1]
}, null, 2)}
\`\`\`
`;

  navigator.clipboard.writeText(fullReport).then(() => {
    alert(`Copied ${subset.length} frames (${startT}s - ${endT}s) of complete diagnostic telemetry to clipboard! You can paste it directly into your chat with AI.`);
  });
}
</script>
</body>
</html>
"""


class HEMServerHandler(http.server.SimpleHTTPRequestHandler):
  frames_data: dict[str, Any] = {}

  def do_GET(self):
    parsed = urllib.parse.urlparse(self.path)
    if parsed.path == "/" or parsed.path == "/index.html":
      self.send_response(200)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      self.wfile.write(INDEX_HTML.encode("utf-8"))
    elif parsed.path == "/api/data":
      self.send_response(200)
      self.send_header("Content-type", "application/json")
      self.end_headers()
      self.wfile.write(json.dumps(self.frames_data).encode("utf-8"))
    else:
      self.send_response(404)
      self.end_headers()


def start_server(port: int, data_payload: dict[str, Any]):
  HEMServerHandler.frames_data = data_payload
  socketserver.TCPServer.allow_reuse_address = True
  with socketserver.TCPServer(("127.0.0.1", port), HEMServerHandler) as httpd:
    url = f"http://127.0.0.1:{port}"
    print(f"\n[HEM Inspector] UI running live at: {url}")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
      httpd.serve_forever()
    except KeyboardInterrupt:
      print("\n[HEM Inspector] Server stopped.")


def main(argv=None):
  parser = argparse.ArgumentParser(description="HEM Live Inspector & Diagnostics")
  parser.add_argument("route", help="Route identifier (e.g. dongle|2023-07-27--13-01-19 or dongle/log_id/segment)")
  parser.add_argument("--segment", type=int, default=0, help="Segment index")
  parser.add_argument("--start", type=float, default=None, help="Start time in seconds (segment-relative)")
  parser.add_argument("--end", type=float, default=None, help="End time in seconds (segment-relative)")
  parser.add_argument("--port", type=int, default=8090, help="Web server port (default 8090)")
  parser.add_argument("--data_dir", default=None, help="Local directory containing routes")
  parser.add_argument("--bias", type=float, default=0.0, help="Override hybrid_exp_bias")
  parser.add_argument("--sensitivity", type=float, default=1.0, help="Override hybrid_vision_brake_sensitivity")

  args = parser.parse_args(argv)

  toggles = SimpleNamespace(
    hybrid_exp_bias=args.bias,
    hybrid_vision_brake_sensitivity=args.sensitivity,
    taco_tune=False,
    classic_model=False,
    tinygrad_model=False,
    vEgoStopping=0.05,
    radar_takeoffs=False,
    lane_change_close_gap=False,
    minimum_lane_change_speed=0.0,
    model_version=None,
  )

  bufs = load_route_data(args.route, args.segment, args.data_dir)
  if bufs is None:
    return 1

  print("[HEM Inspector] Replaying route segment through HEM & Longitudinal Planner...")
  frames, stop_events = run_hem_replay(bufs, args.start, args.end, toggles)
  print(f"[HEM Inspector] Processed {len(frames)} frames. Identified {len(stop_events)} stop/decel event candidates.")

  start_server(args.port, {"frames": frames, "events": stop_events})
  return 0


if __name__ == "__main__":
  raise SystemExit(main())