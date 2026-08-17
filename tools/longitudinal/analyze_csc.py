#!/usr/bin/env python3
"""Curve Speed Controller field report: does it cut the lateral-accel tail, how
often does it engage, and how often do drivers reject it.

Usage:
  ./analyze_csc.py <route-or-segment>            # e.g. a1b2c3d4e5f6g7h8|2026-08-14--10-30-00
  ./analyze_csc.py <rlog-path> [<rlog-path> ...]
  ./analyze_csc.py <route> --json report.json
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

DT = 0.05                      # modelV2/starpilotPlan cadence
MS_TO_MPH = 2.23694
M_TO_MILES = 1.0 / 1609.34
HIGHWAY_SPEED = 60.0 / MS_TO_MPH   # above this, engagement is the over-slowing regression risk
CURVE_LAT_ACCEL = 1.3              # MINIMUM_LATERAL_ACCELERATION
EPISODE_GAP_S = 1.0
V_CRUISE_UNSET = 255


@dataclass
class Frame:
  t: float = 0.0
  v_ego: float = 0.0
  a_ego: float = 0.0
  curvature: float = 0.0
  gas: bool = False
  brake: bool = False
  accel_pressed: bool = False
  long_active: bool = False
  blinker: bool = False     # CSC gating input: a blinker suspends it entirely
  csc_active: bool = False
  csc_overridden: bool = False
  csc_training: bool = False
  csc_speed: float = 0.0
  v_cruise: float = 0.0     # applied cruise speed, already reduced by CSC
  set_speed: float = 0.0    # what the driver dialled in, so cuts are measurable
  learned_lat_accel: float = 0.0
  binding_distance: float = 0.0

  @property
  def lat_accel(self) -> float:
    return self.v_ego ** 2 * abs(self.curvature)


@dataclass
class Episode:
  start: float
  end: float
  peak_cut: float = 0.0
  peak_lat_accel: float = 0.0
  min_a_ego: float = 0.0
  entry_speed: float = 0.0
  binding_distance: float = 0.0
  cancelled: bool = False
  gas: bool = False
  brake: bool = False

  @property
  def duration(self) -> float:
    return self.end - self.start


def read_events(identifier: str):
  """A downloaded rlog reads directly; anything else goes through LogReader."""
  path = Path(identifier)
  if path.is_file():
    from cereal import log as capnp_log

    data = path.read_bytes()
    if data[:4] == b"\x28\xb5\x2f\xfd":
      import zstandard
      data = zstandard.ZstdDecompressor().decompress(data, max_output_size=2 << 30)
    return capnp_log.Event.read_multiple_bytes(data)

  from openpilot.tools.lib.logreader import LogReader, ReadMode  # needs the device stack

  return LogReader(identifier, default_mode=ReadMode.AUTO, sort_by_time=True)


def read_frames(identifier: str) -> list[Frame]:
  """Join carState/controlsState/starpilotPlan onto the plan's cadence."""
  frames: list[Frame] = []
  latest = Frame()
  t0 = None
  have_plan = False

  for msg in read_events(identifier):
    which = msg.which()
    if which == "carState":
      cs = msg.carState
      latest.v_ego = float(cs.vEgo)
      latest.a_ego = float(cs.aEgo)
      latest.gas = bool(cs.gasPressed)
      latest.brake = bool(cs.brakePressed)
      latest.blinker = bool(cs.leftBlinker or cs.rightBlinker)
      set_kph = float(cs.vCruise)
      latest.set_speed = set_kph / 3.6 if 0 < set_kph < V_CRUISE_UNSET else 0.0
    elif which == "carControl":
      latest.long_active = bool(msg.carControl.longActive)
    elif which == "controlsState":
      latest.curvature = float(msg.controlsState.curvature)
    elif which == "starpilotCarState":
      latest.accel_pressed = bool(getattr(msg.starpilotCarState, "accelPressed", False))
    elif which == "starpilotPlan":
      plan = msg.starpilotPlan
      have_plan = True
      if t0 is None:
        t0 = msg.logMonoTime / 1e9
      latest.t = msg.logMonoTime / 1e9 - t0
      latest.csc_active = bool(plan.cscControllingSpeed)
      latest.csc_training = bool(plan.cscTraining)
      latest.csc_speed = float(plan.cscSpeed)
      latest.v_cruise = float(plan.vCruise)
      # absent in older logs
      latest.csc_overridden = bool(getattr(plan, "cscOverridden", False))
      latest.learned_lat_accel = float(getattr(plan, "cscLearnedLatAccel", 0.0))
      latest.binding_distance = float(getattr(plan, "cscBindingDistance", 0.0))
      frames.append(Frame(**vars(latest)))

  if not have_plan:
    raise SystemExit(f"no starpilotPlan messages in {identifier} — is this a StarPilot route?")
  return frames


def build_episodes(frames: list[Frame]) -> list[Episode]:
  episodes: list[Episode] = []
  current: Episode | None = None
  last_active_t = -math.inf

  for f in frames:
    if f.csc_active:
      if current is None or (f.t - last_active_t) > EPISODE_GAP_S:
        current = Episode(start=f.t, end=f.t, entry_speed=f.v_ego,
                          binding_distance=f.binding_distance, min_a_ego=f.a_ego)
        episodes.append(current)
      current.end = f.t
      if f.set_speed > 0:
        current.peak_cut = max(current.peak_cut, f.set_speed - f.csc_speed)
      current.peak_lat_accel = max(current.peak_lat_accel, f.lat_accel)
      current.min_a_ego = min(current.min_a_ego, f.a_ego)
      current.gas |= f.gas
      current.brake |= f.brake
      last_active_t = f.t
    elif current is not None and (f.t - last_active_t) <= EPISODE_GAP_S:
      # an override releases CSC on the same frame it registers, so the rejection
      # always lands just past the end of the episode it rejected
      current.cancelled |= f.csc_overridden or f.accel_pressed
      current.gas |= f.gas
      current.brake |= f.brake

  return episodes


def curve_lat_accel_peaks(frames: list[Frame]) -> list[float]:
  """Peak lateral acceleration of each distinct curve, engaged driving only."""
  peaks: list[float] = []
  peak = 0.0
  in_curve = False
  for f in frames:
    if not f.long_active:
      continue
    if f.lat_accel >= CURVE_LAT_ACCEL:
      in_curve = True
      peak = max(peak, f.lat_accel)
    elif in_curve:
      peaks.append(peak)
      peak = 0.0
      in_curve = False
  if in_curve:
    peaks.append(peak)
  return peaks


def summarize(frames: list[Frame], episodes: list[Episode]) -> dict:
  driving = [f for f in frames if f.v_ego > 5.0]
  engaged = [f for f in driving if f.long_active]
  active = [f for f in engaged if f.csc_active]
  distance_mi = sum(f.v_ego * DT for f in driving) * M_TO_MILES
  peaks = curve_lat_accel_peaks(frames)
  highway = [e for e in episodes if e.entry_speed >= HIGHWAY_SPEED]

  def pct(n, d):
    return 100.0 * n / d if d else 0.0

  return {
    "route": {
      "duration_min": len(frames) * DT / 60.0,
      "distance_mi": distance_mi,
      "engaged_pct": pct(len(engaged), len(driving)),
      "mean_speed_mph": float(np.mean([f.v_ego for f in driving]) * MS_TO_MPH) if driving else 0.0,
    },
    "engagement": {
      "active_pct_of_engaged": pct(len(active), len(engaged)),
      "episodes": len(episodes),
      "episodes_per_mile": len(episodes) / distance_mi if distance_mi > 0.1 else 0.0,
      "median_duration_s": float(np.median([e.duration for e in episodes])) if episodes else 0.0,
      "max_duration_s": max((e.duration for e in episodes), default=0.0),
      "median_cut_mph": float(np.median([e.peak_cut for e in episodes]) * MS_TO_MPH) if episodes else 0.0,
      "max_cut_mph": max((e.peak_cut for e in episodes), default=0.0) * MS_TO_MPH,
      "median_anticipation_m": float(np.median([e.binding_distance for e in episodes])) if episodes else 0.0,
    },
    "outcome_lat_accel": {
      "curves_seen": len(peaks),
      "median": float(np.median(peaks)) if peaks else 0.0,
      "p90": float(np.percentile(peaks, 90)) if peaks else 0.0,
      "p99": float(np.percentile(peaks, 99)) if peaks else 0.0,
      "max": max(peaks, default=0.0),
      "over_3_0_pct": pct(sum(1 for p in peaks if p > 3.0), len(peaks)),
    },
    "acceptance": {
      "cancelled_episodes": sum(1 for e in episodes if e.cancelled),
      "cancel_rate_pct": pct(sum(1 for e in episodes if e.cancelled), len(episodes)),
      "gas_during_episode_pct": pct(sum(1 for e in episodes if e.gas), len(episodes)),
      "brake_during_episode_pct": pct(sum(1 for e in episodes if e.brake), len(episodes)),
    },
    "comfort": {
      "median_min_a_ego": float(np.median([e.min_a_ego for e in episodes])) if episodes else 0.0,
      "hardest_decel": min((e.min_a_ego for e in episodes), default=0.0),
    },
    "highway_watch": {
      "episodes_above_60mph": len(highway),
      "max_cut_mph": max((e.peak_cut for e in highway), default=0.0) * MS_TO_MPH,
    },
    "learning": {
      "training_pct_of_driving": pct(sum(1 for f in driving if f.csc_training), len(driving)),
      "learned_lat_accel_min": min((f.learned_lat_accel for f in active), default=0.0),
      "learned_lat_accel_max": max((f.learned_lat_accel for f in active), default=0.0),
    },
  }


def print_report(name: str, s: dict) -> None:
  r, e, o, a, c, h, l = (s["route"], s["engagement"], s["outcome_lat_accel"],
                         s["acceptance"], s["comfort"], s["highway_watch"], s["learning"])
  print(f"\n=== {name}")
  print(f"  {r['duration_min']:.1f} min, {r['distance_mi']:.1f} mi, "
        f"{r['mean_speed_mph']:.0f} mph avg, engaged {r['engaged_pct']:.0f}% of driving")

  print("\n  DOES IT WORK -- peak lateral accel per curve (engaged)")
  print(f"    {o['curves_seen']} curves   median {o['median']:.2f}   p90 {o['p90']:.2f}   "
        f"p99 {o['p99']:.2f}   max {o['max']:.2f} m/s^2")
  print(f"    curves over 3.0 m/s^2: {o['over_3_0_pct']:.1f}%   <-- this tail should shrink vs a CSC-off route")

  print("\n  DO USERS ACCEPT IT")
  print(f"    cancel rate (RES+) {a['cancel_rate_pct']:.0f}%   gas {a['gas_during_episode_pct']:.0f}%   "
        f"brake {a['brake_during_episode_pct']:.0f}%   of {e['episodes']} episodes")
  print("    cancels/gas high => too slow;  brake high => too fast")

  print("\n  ENGAGEMENT")
  print(f"    {e['active_pct_of_engaged']:.1f}% of engaged time, {e['episodes_per_mile']:.2f} episodes/mi, "
        f"median {e['median_duration_s']:.1f}s (max {e['max_duration_s']:.1f}s)")
  print(f"    speed cut median {e['median_cut_mph']:.1f} mph, max {e['max_cut_mph']:.1f} mph")
  print(f"    braking begins {e['median_anticipation_m']:.0f} m ahead (median)")

  print("\n  COMFORT / REGRESSION WATCH")
  print(f"    decel median {c['median_min_a_ego']:.2f}, hardest {c['hardest_decel']:.2f} m/s^2")
  print(f"    highway (>60 mph) episodes: {h['episodes_above_60mph']}, max cut {h['max_cut_mph']:.1f} mph"
        f"   <-- over-slowing complaints start here")

  print("\n  LEARNING")
  print(f"    training {l['training_pct_of_driving']:.1f}% of driving; "
        f"learned comfort in use {l['learned_lat_accel_min']:.2f}-{l['learned_lat_accel_max']:.2f} m/s^2")


def main() -> None:
  parser = argparse.ArgumentParser(description="Curve Speed Controller field report.")
  parser.add_argument("routes", nargs="+", help="route/segment identifier(s) or rlog path(s)")
  parser.add_argument("--json", type=Path, help="also write the raw numbers here")
  args = parser.parse_args()

  reports = {}
  for identifier in args.routes:
    name = Path(identifier).name if Path(identifier).exists() else identifier
    frames = read_frames(identifier)
    episodes = build_episodes(frames)
    summary = summarize(frames, episodes)
    reports[name] = summary
    print_report(name, summary)

  if args.json:
    args.json.write_text(json.dumps(reports, indent=2))
    print(f"\nwrote {args.json}")


if __name__ == "__main__":
  main()
