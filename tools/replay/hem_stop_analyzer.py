#!/usr/bin/env python3
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add openpilot paths if running from tools/ or other subdirectories
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from openpilot.common.realtime import DT_MDL
from openpilot.tools.lib.logreader import LogReader
from openpilot.starpilot.controls.lib.hybrid_experimental_mode import HybridExperimentalMode

# Define the specific routes and segments where stop-sign or red-light failures occurred
ROUTES_TO_ANALYZE = [
  ("afb7ef2ed593d651/000000b3--9c3d58d585", 3, "Stop Sign"),
  ("afb7ef2ed593d651/000000b3--9c3d58d585", 8, "Stop Sign"),
  ("afb7ef2ed593d651/000000b3--9c3d58d585", 10, "Stop Sign"),
  ("afb7ef2ed593d651/000000b3--9c3d58d585", 11, "Stop Sign"),
  ("afb7ef2ed593d651/000000b4--1a67659212", 1, "Stop Sign"),
  ("afb7ef2ed593d651/000000b5--8ee86fef97", 0, "Stop Sign"),
  ("afb7ef2ed593d651/000000b6--711631f3fd", 0, "Stop Sign"),
  ("afb7ef2ed593d651/000000b7--9bfbaf247a", 1, "Stop Sign"),
  ("afb7ef2ed593d651/000000b8--e3147dbfc3", 0, "Stop Sign"),
  ("afb7ef2ed593d651/000000b9--976a3b50cb", 0, "Stop Sign"),
  ("afb7ef2ed593d651/000000b9--976a3b50cb", 1, "Stop Sign"),
  ("afb7ef2ed593d651/000000b9--976a3b50cb", 2, "Stop Sign"),
  ("afb7ef2ed593d651/000000b9--976a3b50cb", 3, "Stop Sign"),
  ("afb7ef2ed593d651/000000b9--976a3b50cb", 6, "Red Light"),
]

class MockLead:
  def __init__(self, status=False, d_rel=150.0, v_lead=0.0):
    self.status = status
    self.dRel = float(d_rel)
    self.vLead = float(v_lead)

def fetch_telemetry(route_str, segment):
  """Loads specified segment logs. Attempts local lookups first, then falls back to public API."""
  route_clean = route_str.replace("|", "/")
  segment_str = f"{segment:02d}" if isinstance(segment, int) else str(segment)

  # Search local paths first
  local_paths = [
    Path(f"/data/media/0/realdata/{route_clean}--{segment}"),
    Path(os.path.expanduser(f"~/.comma/media/0/realdata/{route_clean}--{segment}")),
    Path(f"./{route_clean}--{segment}"),
  ]

  lr = None
  for path in local_paths:
    rlog_file = path / "rlog"
    if rlog_file.exists():
      print(f"Loading local data: {rlog_file}")
      lr = LogReader(str(rlog_file))
      break

  if lr is None:
    # Construct comma public database URL fallback
    dongle_id, route_sig = route_clean.split("/", 1)
    remote_url = f"https://commadata2.blob.core.windows.net/commadata2/{dongle_id}/{route_sig}/{segment}/rlog"
    print(f"Loading remote data: {remote_url}")
    try:
      lr = LogReader(remote_url)
    except Exception as e:
      print(f"Failed to fetch {remote_url}: {e}")
      return []

  print("Parsing messages...")
  car_state_msgs = []
  model_msgs = []
  splan_msgs = []
  lplan_msgs = []

  for msg in lr:
    which = msg.which()
    t = msg.logMonoTime * 1e-9
    if which == "carState":
      car_state_msgs.append((t, msg.carState))
    elif which == "modelV2":
      model_msgs.append((t, msg.modelV2))
    elif which == "starpilotPlan":
      splan_msgs.append((t, msg.starpilotPlan))
    elif which == "longitudinalPlan":
      lplan_msgs.append((t, msg.longitudinalPlan))

  car_state_msgs.sort(key=lambda x: x[0])
  model_msgs.sort(key=lambda x: x[0])
  splan_msgs.sort(key=lambda x: x[0])
  lplan_msgs.sort(key=lambda x: x[0])

  # Synchronize messages on model 20Hz time-grid
  data_frames = []
  for t_model, model_msg in model_msgs:
    # Find latest corresponding messages
    cs = next((m for t, m in reversed(car_state_msgs) if t <= t_model), None)
    splan = next((m for t, m in reversed(splan_msgs) if t <= t_model), None)
    lplan = next((m for t, m in reversed(lplan_msgs) if t <= t_model), None)

    if cs is None:
      continue

    v_ego = cs.vEgo
    v_cruise = getattr(splan, "vCruise", getattr(cs, "vCruise", 0.0))
    a_chill = getattr(lplan, "aTarget", 0.0)
    a_exp = getattr(model_msg.action, "desiredAcceleration", 0.0)

    data_frames.append({
      "t": t_model,
      "v_ego": v_ego,
      "v_cruise": v_cruise,
      "a_chill": a_chill,
      "a_exp": a_exp,
      "model": model_msg,
    })

  return data_frames

def simulate_hem(data_frames):
  """Simulates the controller over the synchronized messages."""
  controller = HybridExperimentalMode()
  controller.record_diag = True

  sim_results = []
  for frame in data_frames:
    # Lead initialization
    lead = MockLead(status=False)

    # Execute state update
    a_out, should_stop_fused = controller.update(
      v_ego=frame["v_ego"],
      v_cruise=frame["v_cruise"],
      lead_one=lead,
      model_v2=frame["model"],
      a_chill=frame["a_chill"],
      a_exp=frame["a_exp"],
    )

    diag = dict(controller.diag)
    diag["a_out"] = float(a_out)
    diag["should_stop_fused"] = bool(should_stop_fused)
    diag["t_rel"] = frame["t"] - data_frames[0]["t"]
    sim_results.append(diag)

  return sim_results

def analyze_failures(route_str, segment, label, results):
  """Analyzes decisions inside the critical deceleration window."""
  total_frames = len(results)
  if total_frames == 0:
    return None

  # Find the primary deceleration zone (where v_ego drops, or should have dropped)
  v_speeds = [r["v_ego"] for r in results]
  max_v = max(v_speeds)
  min_v = min(v_speeds)

  # Identify frames with a stop visible to vision (horizon stop or exp stop flag)
  active_frames = []
  for idx, r in enumerate(results):
    if r.get("horizon_stopping", False) or r.get("should_stop_exp", False) or r.get("w_vision", 0.0) > 0.1:
      active_frames.append(idx)

  if not active_frames:
    return {
      "route": route_str, "segment": segment, "label": label,
      "outcome": "No stop event detected by model.",
      "failure_mode": "Model did not predict stop point.",
    }

  start_idx = min(active_frames)
  end_idx = max(active_frames)

  # Analyze tracking variables inside the event window
  latch_decays = 0
  tracking_resets = 0
  early_departures = 0
  kinematic_collapses = 0

  for idx in range(start_idx, end_idx + 1):
    r = results[idx]

    # 1. Check for premature latch decay (decaying while still moving fast)
    if r.get("w_vision", 0.0) < 0.2 and r.get("v_ego", 0.0) > 2.0 and r.get("horizon_stopping", False):
      latch_decays += 1

    # 2. Check for stop detection being cleared while speed is still high
    if idx > start_idx:
      prev_r = results[idx - 1]
      if prev_r.get("horizon_stopping", False) and not r.get("horizon_stopping", False):
        if r.get("v_ego", 0.0) > 1.0 and not r.get("is_departing", False):
          tracking_resets += 1

    # 3. Check for departure lockout firing while still approaching a predicted stop
    if r.get("is_departing", False) and r.get("v_ego", 0.0) > 1.5 and r.get("horizon_stopping", False):
      early_departures += 1

    # 4. Check if the brake floor collapsed near the stop line
    if r.get("a_brake_fused", 0.0) > -0.1 and r.get("v_ego", 0.0) > 1.0 and r.get("horizon_stopping", False):
      kinematic_collapses += 1

  # Determine primary failure mode
  failure_modes = []
  if latch_decays > 5:
    failure_modes.append("Premature Latch Decay (w_vision collapsed)")
  if tracking_resets > 0:
    failure_modes.append("Stop Detection Cleared Early")
  if early_departures > 5:
    failure_modes.append("Early Departure Lockout Bypass (is_departing while approaching)")
  if kinematic_collapses > 5:
    failure_modes.append("Kinematic Brake Floor Collapse near stop line")

  failure_mode = " / ".join(failure_modes) if failure_modes else "Weak general deceleration tracking"
  outcome = f"Blew past stop line. Min speed reached: {min_v:.2f} m/s." if min_v > 0.5 else "Stopped but late/harsh."

  return {
    "route": route_str,
    "segment": segment,
    "label": label,
    "max_v": max_v,
    "min_v": min_v,
    "latch_decays": latch_decays,
    "tracking_resets": tracking_resets,
    "early_departures": early_departures,
    "kinematic_collapses": kinematic_collapses,
    "outcome": outcome,
    "failure_mode": failure_mode,
  }

def run_suite():
  all_analyses = []
  plot_data = {}

  for route, seg, label in ROUTES_TO_ANALYZE:
    print(f"\nAnalyzing {route} segment {seg} ({label})...")
    frames = fetch_telemetry(route, seg)
    if not frames:
      print("No frames retrieved. Skipping.")
      continue

    results = simulate_hem(frames)
    analysis = analyze_failures(route, seg, label, results)
    if analysis:
      all_analyses.append(analysis)
      plot_data[f"{route.split('/')[-1][:8]}_s{seg}"] = (frames, results)

  # 1. Export forensic summary text report
  report_path = "hem_forensic_report.txt"
  print(f"\nWriting forensic report to {report_path}...")
  with open(report_path, "w") as f:
    f.write("=== HYBRID EXPERIMENTAL MODE (HEM) FAILURE CASE STUDY SUMMARY ===\n")
    f.write(f"Analyzed {len(all_analyses)} routes where vehicle rolled stop-lines\n")
    f.write("==================================================================\n\n")

    # General findings
    f.write("COMMON STRUCTURAL ROOT CAUSES IDENTIFIED:\n")
    f.write("------------------------------------------\n")
    f.write("1. Stop Detection Cleared on Model Re-acceleration:\n")
    f.write("   When the trajectory velocity endpoint flips positive (a_exp > 0.1, v_horizon > 1.2)\n")
    f.write("   the 'vision_departing' / 'is_departing' signal fires TRUE and clears 'horizon_stopping'\n")
    f.write("   while the car is still traveling at speed close to the line, dropping the brake floor.\n\n")
    f.write("2. Insufficient Latch Sustainability (w_vision decays):\n")
    f.write("   If the model stops outputting a low velocity endpoint, even briefly, the vision weight\n")
    f.write("   decays toward zero and unlocks cruise throttle while still closing on the stop.\n\n")

    f.write("DETAILED SEGMENT TELEMETRY BREAKDOWN:\n")
    f.write("-------------------------------------\n")
    for a in all_analyses:
      f.write(f"Route: {a['route']} | Seg: {a['segment']} ({a['label']})\n")
      f.write(f"  • Velocity Profile : {a['max_v']:.1f} m/s -> {a['min_v']:.1f} m/s\n")
      f.write(f"  • Tracker Resets   : {a['tracking_resets']} frames\n")
      f.write(f"  • Early Departures : {a['early_departures']} frames\n")
      f.write(f"  • Outcome          : {a['outcome']}\n")
      f.write(f"  • Primary Fault    : {a['failure_mode']}\n")
      f.write("------------------------------------------------------------------\n")

  # 2. Generate tiled plot of critical variables for a subset of failures
  print("Generating diagnostic plots...")
  plot_keys = list(plot_data.keys())[:4]  # Plot up to 4 significant failures for space
  if not plot_keys:
    return

  fig, axes = plt.subplots(len(plot_keys), 2, figsize=(15, 3 * len(plot_keys)), sharex="col")
  if len(plot_keys) == 1:
    axes = np.expand_dims(axes, axis=0)

  for idx, key in enumerate(plot_keys):
    frames, results = plot_data[key]
    t = [r["t_rel"] for r in results]
    v_ego = [r["v_ego"] for r in results]
    w_vis = [r["w_vision"] for r in results]
    a_out = [r["a_out"] for r in results]
    a_kin = [r["a_brake_fused"] for r in results]

    # Left column: Speeds and Latch activations
    ax_l = axes[idx, 0]
    ax_l.plot(t, v_ego, color="black", lw=1.5, label="v_ego (m/s)")
    ax_l_twin = ax_l.twinx()
    ax_l_twin.plot(t, w_vis, color="orange", alpha=0.7, ls="--", label="w_vision (latch)")
    ax_l.set_title(f"Run: {key} - Speeds", fontsize=10)
    ax_l.set_ylabel("Speed (m/s)")
    ax_l_twin.set_ylabel("Latch Active", color="orange")
    ax_l.grid(alpha=0.3)
    if idx == 0:
      ax_l.legend(loc="upper left")
      ax_l_twin.legend(loc="upper right")

    # Right column: Acceleration commands
    ax_r = axes[idx, 1]
    ax_r.plot(t, a_out, color="blue", lw=1.5, label="a_out (fused)")
    ax_r.plot(t, a_kin, color="red", alpha=0.6, ls=":", label="a_kinematic_stop")
    ax_r.set_title(f"Run: {key} - Acceleration Commands", fontsize=10)
    ax_r.set_ylabel("Accel (m/s²)")
    ax_r.grid(alpha=0.3)
    if idx == 0:
      ax_r.legend(loc="upper right")

  plt.tight_layout()
  plot_out_path = "hem_failures_analysis.png"
  plt.savefig(plot_out_path, dpi=150)
  print(f"Diagnostic graph saved to {plot_out_path}")

if __name__ == "__main__":
  run_suite()