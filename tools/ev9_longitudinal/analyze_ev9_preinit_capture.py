#!/usr/bin/env python3
"""Summarize EV9 preinit ownership, handoff, events, and reconstructed CAN."""

import argparse
from collections import Counter
import json
from pathlib import Path

from openpilot.tools.lib.logreader import LogReader


MANAGED = {0x100, 0x12A, 0xCB, 0x160, 0x161, 0x162, 0x1A0, 0x1BA,
           0x1DA, 0x1E0, 0x1E5, 0x1EA, 0x200, 0x345, 0x38C, 0x730}


def enum_name(value) -> str:
  return str(value)


def analyze_capture(path: Path) -> dict:
  first_mono = None
  last_mono = None
  service_counts = Counter()
  can_counts = Counter()
  icon_states_161 = Counter()
  first_icon_state_161 = {}
  panda_transitions = []
  car_transitions = []
  alert_transitions = []
  event_transitions = []
  car_params = []
  previous_panda = None
  previous_car = None
  previous_alert = None
  previous_events = None

  for msg in LogReader(str(path)):
    service = msg.which()
    service_counts[service] += 1
    mono = int(msg.logMonoTime)
    first_mono = mono if first_mono is None else min(first_mono, mono)
    last_mono = mono if last_mono is None else max(last_mono, mono)

    if service == "pandaStates" and len(msg.pandaStates):
      panda = msg.pandaStates[0]
      status = panda.ev9LongPreinitStatus
      key = (
        bool(panda.ignitionLine or panda.ignitionCan),
        enum_name(panda.safetyModel),
        int(panda.safetyParam),
        bool(panda.powerSaveEnabled),
        int(status.state),
        int(status.flags),
        int(status.fingerprint),
        int(status.attempts),
        int(status.lastHostTxUs),
        int(status.handoffUs),
        int(status.abortUs),
      )
      if key != previous_panda:
        panda_transitions.append({
          "mono_ns": mono,
          "ignition": key[0],
          "safety_model": key[1],
          "safety_param": key[2],
          "power_save": key[3],
          "state": key[4],
          "flags": key[5],
          "fingerprint": key[6],
          "attempts": key[7],
          "last_host_tx_us": key[8],
          "handoff_us": key[9],
          "abort_us": key[10],
          "cycle_started_us": int(status.cycleStartedUs),
          "trigger_us": int(status.triggerUs),
          "session_response_us": int(status.sessionResponseUs),
          "comm_control_response_us": int(status.commControlResponseUs),
          "suppression_confirmed_us": int(status.suppressionConfirmedUs),
          "first_replacement_us": int(status.firstReplacementUs),
          "ready_us": int(status.readyUs),
        })
        previous_panda = key

    elif service == "can":
      for frame in msg.can:
        address = int(frame.address)
        source = int(frame.src)
        if address in MANAGED:
          can_counts[(source, address)] += 1
        if address == 0x161:
          data = bytes(frame.dat)
          key = (source, data[3], data[4])
          icon_states_161[key] += 1
          first_icon_state_161.setdefault(key, (mono, data.hex()))

    elif service == "carState":
      state = msg.carState
      key = (
        bool(msg.valid), bool(state.canValid), bool(state.canTimeout),
        bool(state.adasUnavailable), enum_name(state.gearShifter),
        bool(state.cruiseState.available),
      )
      if key != previous_car:
        car_transitions.append({
          "mono_ns": mono, "valid": key[0], "can_valid": key[1],
          "can_timeout": key[2], "adas_unavailable": key[3],
          "gear": key[4], "cruise_available": key[5],
        })
        previous_car = key

    elif service == "selfdriveState":
      state = msg.selfdriveState
      key = (str(state.alertType), str(state.alertText1), str(state.alertText2),
             bool(state.engageable))
      if key != previous_alert:
        alert_transitions.append({
          "mono_ns": mono, "alert_type": key[0], "text1": key[1],
          "text2": key[2], "engageable": key[3],
        })
        previous_alert = key

    elif service == "onroadEvents":
      key = tuple(sorted(str(event.name) for event in msg.onroadEvents))
      if key != previous_events:
        event_transitions.append({"mono_ns": mono, "events": key})
        previous_events = key

    elif service == "carParams":
      params = msg.carParams
      car_params.append({
        "mono_ns": mono,
        "fingerprint": str(params.carFingerprint),
        "openpilot_long": bool(params.openpilotLongitudinalControl),
        "passive": bool(params.passive),
        "safety": [(str(config.safetyModel), int(config.safetyParam))
                   for config in params.safetyConfigs],
      })

  def relative(entries):
    for entry in entries:
      entry["t_s"] = (entry["mono_ns"] - first_mono) / 1e9
    return entries

  bodies = []
  for (source, byte3, byte4), count in icon_states_161.most_common():
    first_seen, example = first_icon_state_161[(source, byte3, byte4)]
    bodies.append({
      "source": source,
      "count": count,
      "first_t_s": (first_seen - first_mono) / 1e9,
      "byte3": byte3,
      "byte4": byte4,
      "example": example,
    })

  return {
    "path": str(path),
    "first_mono_ns": first_mono,
    "last_mono_ns": last_mono,
    "duration_s": (last_mono - first_mono) / 1e9,
    "service_counts": dict(service_counts),
    "panda_transitions": relative(panda_transitions),
    "car_transitions": relative(car_transitions),
    "alert_transitions": relative(alert_transitions),
    "event_transitions": relative(event_transitions),
    "car_params": relative(car_params),
    "managed_can_counts": {
      f"src={source}:0x{address:X}": count
      for (source, address), count in sorted(can_counts.items())
    },
    "icon_states_161": bodies,
  }


def extract_route_logs(paths: list[Path]) -> list[dict]:
  matches = []
  needles = ("EV9", "preinit", "handoff", "takeover", "EcuDisable",
             "fingerprint", "card", "commIssue", "controlsMismatch",
             "safety model", "Finished FW query", "CarParams", "ControlsReady")
  for path in paths:
    for msg in LogReader(str(path)):
      if msg.which() != "logMessage":
        continue
      raw = str(msg.logMessage)
      try:
        parsed = json.loads(raw)
        text = str(parsed.get("msg", raw))
      except json.JSONDecodeError:
        parsed = {}
        text = raw
      if any(needle.lower() in text.lower() for needle in needles):
        matches.append({
          "path": str(path),
          "mono_ns": int(msg.logMonoTime),
          "level": parsed.get("levelnum"),
          "filename": parsed.get("filename"),
          "text": text,
        })
  return matches


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("capture", type=Path)
  parser.add_argument("--route", type=Path, action="append", default=[])
  args = parser.parse_args()
  print(json.dumps({
    "capture": analyze_capture(args.capture),
    "route_logs": extract_route_logs(args.route),
  }, indent=2))


if __name__ == "__main__":
  main()
