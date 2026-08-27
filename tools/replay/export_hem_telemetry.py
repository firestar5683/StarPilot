#!/usr/bin/env python3
"""HEM Telemetry Exporter.

Extracts real telemetry from target segments and saves them to a portable JSON file,
capturing the raw model action intents, radar lead states, and planner controls.
"""
import os
import sys
import json
from pathlib import Path

# Add openpilot paths
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from openpilot.tools.lib.logreader import LogReader, ReadMode

ROUTES_TO_EXPORT = [
  ("afb7ef2ed593d651/000000b3--9c3d58d585", 10, "Pure Exp Stop Baseline"),
  ("afb7ef2ed593d651/000000b3--9c3d58d585", 11, "Pure Exp Stop Baseline 2"),
  ("afb7ef2ed593d651/000000b3--9c3d58d585", 3, "Stop Sign"),
  ("afb7ef2ed593d651/000000b5--8ee86fef97", 0, "Stop Sign"),
  ("afb7ef2ed593d651/000000b7--9bfbaf247a", 1, "Stop Sign"),
  ("afb7ef2ed593d651/000000b9--976a3b50cb", 6, "Red Light"),
]


def serialize_lead(lead_msg):
  if lead_msg is None:
    return {"status": False, "dRel": 150.0, "vLead": 0.0, "aLeadK": 0.0, "yRel": 0.0, "radar": False}
  return {
    "status": bool(getattr(lead_msg, "status", False)),
    "dRel": float(getattr(lead_msg, "dRel", 150.0)),
    "vLead": float(getattr(lead_msg, "vLead", 0.0)),
    "aLeadK": float(getattr(lead_msg, "aLeadK", 0.0)),
    "yRel": float(getattr(lead_msg, "yRel", 0.0)),
    "radar": bool(getattr(lead_msg, "radar", False)),
    "modelProb": float(getattr(lead_msg, "modelProb", 0.0)),
  }


def serialize_model(model_msg):
  """Extracts velocity, position, acceleration lists and raw action intents from modelV2."""
  v_list = list(getattr(getattr(model_msg, "velocity", None), "x", []))
  x_list = list(getattr(getattr(model_msg, "position", None), "x", []))
  a_list = list(getattr(getattr(model_msg, "acceleration", None), "x", []))

  action = getattr(model_msg, "action", None)
  a_exp_raw = float(getattr(action, "desiredAcceleration", 0.0)) if action is not None else 0.0
  should_stop_exp_raw = bool(getattr(action, "shouldStop", False)) if action is not None else False

  return {
    "velocity": v_list,
    "position": x_list,
    "acceleration": a_list,
    "desiredAcceleration": a_exp_raw,
    "shouldStop": should_stop_exp_raw,
  }


def export_routes():
  exported_data = {}

  for route, seg, label in ROUTES_TO_EXPORT:
    route_clean = route.replace("|", "/")
    print(f"\nProcessing {route_clean} segment {seg} ({label})...")

    local_paths = [
      Path(f"/data/media/0/realdata/{route_clean}--{seg}"),
      Path(os.path.expanduser(f"~/.comma/media/0/realdata/{route_clean}--{seg}")),
      Path(f"./{route_clean}--{seg}"),
    ]

    lr = None
    for path in local_paths:
      rlog_file = path / "rlog"
      if rlog_file.exists():
        lr = LogReader(str(rlog_file))
        break

    if lr is None:
      dongle_id, log_id = route_clean.split("/", 1)
      comma_id = f"{dongle_id}|{log_id}/{seg}"
      try:
        lr = LogReader(comma_id, default_mode=ReadMode.RLOG)
      except Exception as e:
        print(f"Failed to fetch {comma_id}: {e}")
        continue

    car_state_msgs = []
    radar_state_msgs = []
    model_msgs = []
    splan_msgs = []
    lplan_msgs = []
    selfdrive_msgs = []
    controls_state_msgs = []
    car_control_msgs = []

    try:
      for msg in lr:
        which = msg.which()
        t = msg.logMonoTime * 1e-9
        if which == "carState":
          car_state_msgs.append((t, msg.carState))
        elif which == "radarState":
          radar_state_msgs.append((t, msg.radarState))
        elif which == "modelV2":
          model_msgs.append((t, msg.modelV2))
        elif which == "starpilotPlan":
          splan_msgs.append((t, msg.starpilotPlan))
        elif which == "longitudinalPlan":
          lplan_msgs.append((t, msg.longitudinalPlan))
        elif which == "selfdriveState":
          selfdrive_msgs.append((t, msg.selfdriveState))
        elif which == "controlsState":
          controls_state_msgs.append((t, msg.controlsState))
        elif which == "carControl":
          car_control_msgs.append((t, msg.carControl))
    except Exception as e:
      print(f"Error reading log: {e}")
      continue

    car_state_msgs.sort(key=lambda x: x[0])
    radar_state_msgs.sort(key=lambda x: x[0])
    model_msgs.sort(key=lambda x: x[0])
    splan_msgs.sort(key=lambda x: x[0])
    lplan_msgs.sort(key=lambda x: x[0])
    selfdrive_msgs.sort(key=lambda x: x[0])
    controls_state_msgs.sort(key=lambda x: x[0])
    car_control_msgs.sort(key=lambda x: x[0])

    frames = []
    for t_model, model_msg in model_msgs:
      cs = next((m for t, m in reversed(car_state_msgs) if t <= t_model), None)
      rs = next((m for t, m in reversed(radar_state_msgs) if t <= t_model), None)
      splan = next((m for t, m in reversed(splan_msgs) if t <= t_model), None)
      lplan = next((m for t, m in reversed(lplan_msgs) if t <= t_model), None)
      sd = next((m for t, m in reversed(selfdrive_msgs) if t <= t_model), None)
      ctrl = next((m for t, m in reversed(controls_state_msgs) if t <= t_model), None)
      cc = next((m for t, m in reversed(car_control_msgs) if t <= t_model), None)

      if cs is None:
        continue

      enabled = False
      state = 0
      active = False
      exp_mode = False
      alert = ""

      if sd is not None:
        enabled = bool(sd.enabled)
        state = int(sd.state.raw)
        active = bool(sd.active)
        exp_mode = bool(getattr(sd, "experimentalMode", False))
        alert = str(getattr(sd, "alertText1", ""))
      elif ctrl is not None:
        enabled = bool(ctrl.enabled)
        state = 2 if enabled else 0
        active = enabled

      if splan is not None and hasattr(splan, "experimentalMode"):
        exp_mode = exp_mode or bool(splan.experimentalMode)

      cc_enabled = bool(getattr(cc, "enabled", False))
      cc_brake = 0.0
      cc_accel = None
      if cc is not None:
        act = getattr(cc, "actuators", None)
        if act is not None:
          cc_brake = float(getattr(act, "brake", 0.0) or 0.0)
          cc_accel = getattr(act, "accel", None)

      op_braking = bool(cc_enabled and cc_brake > 0.05)
      manual_brake = bool(cs.brakePressed) and not op_braking

      # Lead tracks
      lead_one_data = serialize_lead(getattr(rs, "leadOne", None))
      lead_two_data = serialize_lead(getattr(rs, "leadTwo", None))
      mpc_source = str(getattr(lplan, "longitudinalPlanSource", "lead0"))

      # Raw model outputs
      action = getattr(model_msg, "action", None)
      a_exp_raw = float(getattr(action, "desiredAcceleration", 0.0)) if action is not None else 0.0
      should_stop_exp_raw = bool(getattr(action, "shouldStop", False)) if action is not None else False

      frames.append({
        "t": t_model,
        "v_ego": float(cs.vEgo),
        "a_ego": float(getattr(cs, "aEgo", 0.0)),
        "standstill": bool(getattr(cs, "standstill", False)),
        "v_cruise": float(getattr(splan, "vCruise", getattr(cs, "vCruise", 0.0))),
        # a_chill is the real planner-side output target from longitudinalPlan
        "a_chill": float(getattr(lplan, "aTarget", 0.0)),
        "should_stop_chill": bool(getattr(lplan, "shouldStop", False)),
        # Raw E2E vision neural net output (not modified by MPC)
        "a_exp_raw": a_exp_raw,
        "should_stop_exp_raw": should_stop_exp_raw,
        "accel_jerk": float(getattr(splan, "accelerationJerk", 1.0)),
        "min_accel": float(getattr(splan, "minAcceleration", -3.5)),
        "max_accel": float(getattr(splan, "maxAcceleration", 1.5)),
        "mpc_source": mpc_source,
        "lead_one": lead_one_data,
        "lead_two": lead_two_data,
        "model_trajectory": serialize_model(model_msg),
        "enabled": enabled,
        "state": state,
        "active": active,
        "exp_mode": exp_mode,
        "alert": alert,
        "brake_pressed": manual_brake,
        "brake_raw": bool(cs.brakePressed),
        "gas_pressed": bool(cs.gasPressed),
      })

    if frames:
      t0 = frames[0]["t"]
      for f in frames:
        f["t"] = f["t"] - t0

      key_name = f"{route_clean.split('/')[-1][:8]}_s{seg}"
      exported_data[key_name] = {
        "label": label,
        "frames": frames,
      }
      print(f"Successfully processed {len(frames)} frames for {key_name}.")

  output_file = "hem_routes_telemetry.json"
  with open(output_file, "w") as f:
    json.dump(exported_data, f, indent=2)
  print(f"\nSaved export payload to {output_file}")


if __name__ == "__main__":
  export_routes()