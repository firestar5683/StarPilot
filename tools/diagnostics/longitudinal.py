"""Offline longitudinal command and estimated-motion trace summary."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from tools.diagnostics.performance import Distribution


SERVICES = {"longitudinalPlan", "carControl", "carState", "selfdriveState"}
SIGNALS = {"longitudinalPlan": "plannerATarget", "carControl": "commandAccel",
           "carState": "aEgoEstimate"}
FIELDS = {"source": "longitudinalPlan", "experimental": "selfdriveState",
          "longActive": "carControl", "gasPressed": "carState", "brakePressed": "carState"}


def _field(body, name):
  try:
    return getattr(body, name)
  except (AttributeError, RuntimeError):
    return None


def _finite(value):
  return type(value) in (int, float) and math.isfinite(value)


def _value(service, body):
  if service == "longitudinalPlan":
    return _field(body, "aTarget")
  if service == "carControl":
    return _field(_field(body, "actuators"), "accel")
  return _field(body, "aEgo")


def _sha(path):
  digest = hashlib.sha256()
  with path.open("rb") as source:
    while chunk := source.read(1024 * 1024):
      digest.update(chunk)
  return digest.hexdigest()


def analyze(messages, *, max_gap_s=0.25, context_age_s=0.5):
  if not 0 < max_gap_s <= context_age_s:
    raise ValueError("Expected 0 < max_gap_s <= context_age_s")
  contexts = {}
  previous = {}
  transitions = Counter()
  rejected = Counter()
  counts = Counter()
  samples = {name: Distribution() for name in SIGNALS.values()}
  intervals = {name: Distribution() for name in SIGNALS.values()}
  delta_rates = {name: Distribution() for name in SIGNALS.values()}
  pedal_context = Counter()

  for message in messages:
    try:
      service = message.which()
    except (AttributeError, RuntimeError):
      continue
    if service not in SERVICES:
      continue
    counts[service] += 1
    timestamp = _field(message, "logMonoTime")
    if not _finite(timestamp) or timestamp < 0 or _field(message, "valid") is not True:
      rejected[f"{service}:invalid_envelope"] += 1
      previous.clear()
      for name, owner in FIELDS.items():
        if owner == service:
          contexts.pop(name, None)
      continue
    timestamp = timestamp / 1e9
    body = _field(message, service)
    if body is None:
      rejected[f"{service}:missing_body"] += 1
      previous.clear()
      for name, owner in FIELDS.items():
        if owner == service:
          contexts.pop(name, None)
      continue
    updates = {}
    if service == "longitudinalPlan":
      updates["source"] = str(_field(body, "longitudinalPlanSource"))
    elif service == "selfdriveState":
      updates["experimental"] = _field(body, "experimentalMode")
    elif service == "carControl":
      updates["longActive"] = _field(body, "longActive")
    else:
      updates["gasPressed"] = _field(body, "gasPressed")
      updates["brakePressed"] = _field(body, "brakePressed")
    if any(name in contexts and timestamp < contexts[name][0] for name in updates):
      rejected[f"{service}:timestamp_regression"] += 1
      previous.clear()
      continue
    for name, value in updates.items():
      prior = contexts.get(name)
      if prior is not None and prior[1] != value:
        transitions[name] += 1
        previous.clear()
      contexts[name] = (timestamp, value)
    if service not in SIGNALS:
      continue
    signal = SIGNALS[service]
    value = _value(service, body)
    if not _finite(value):
      samples[signal].add(None, "missing_or_nonfinite")
      previous.pop(service, None)
      continue
    samples[signal].add(value)
    if any(name not in contexts or not 0 <= timestamp - contexts[name][0] <= context_age_s for name in FIELDS):
      rejected[f"{service}:missing_or_stale_mode"] += 1
      previous.pop(service, None)
      continue
    mode = tuple(contexts[name][1] for name in FIELDS)
    if mode[0] not in ("cruise", "lead0", "lead1", "lead2", "e2e") or any(type(mode[index]) is not bool for index in (1, 2, 3, 4)):
      rejected[f"{service}:invalid_mode"] += 1
      previous.pop(service, None)
      continue
    pedal_context[f"gas={mode[3]},brake={mode[4]}"] += 1
    prior = previous.get(service)
    if prior is not None:
      elapsed = timestamp - prior[0]
      if elapsed <= 0:
        rejected[f"{service}:timestamp_regression"] += 1
      elif elapsed > max_gap_s:
        rejected[f"{service}:gap"] += 1
      elif mode != prior[2]:
        rejected[f"{service}:mode_changed"] += 1
      else:
        intervals[signal].add(elapsed)
        delta_rates[signal].add((value - prior[1]) / elapsed)
    previous[service] = (timestamp, value, mode)

  return {"limits": {"maxContinuousGapSeconds": max_gap_s, "maxContextAgeSeconds": context_age_s},
          "messageCounts": dict(counts), "transitions": dict(transitions), "pedalContextSamples": dict(pedal_context),
          "rejectedPairsOrSamples": dict(rejected),
          "signals": {name: {"valuesMps2": samples[name].summary(),
                             "continuousFrameDeltaSeconds": intervals[name].summary(),
                             "continuousDeltaRateMps3": delta_rates[name].summary()}
                      for name in SIGNALS.values()}}


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("rlog", type=Path, help="Existing local rlog or qlog segment")
  parser.add_argument("--max-gap-s", type=float, default=0.25)
  parser.add_argument("--context-age-s", type=float, default=0.5)
  args = parser.parse_args()
  path = args.rlog.resolve(strict=True)
  if not path.is_file() or path.suffix not in (".zst", ".bz2", ".rlog", ".qlog"):
    parser.error("Expected a local log file")
  from openpilot.tools.lib.logreader import LogReader
  report = analyze(LogReader(str(path)), max_gap_s=args.max_gap_s, context_age_s=args.context_age_s)
  report["input"] = {"path": str(path), "sha256": _sha(path), "sizeBytes": path.stat().st_size,
                     "kind": "qlog_decimated" if "qlog" in path.name else "rlog_segment"}
  root = Path(__file__).resolve().parents[2]
  report["sourceHashes"] = {name: _sha(root / name) for name in (
    "tools/diagnostics/longitudinal.py", "openpilot/cereal/log.capnp", "opendbc_repo/opendbc/car/car.capnp")}
  report["provenance"] = {"plannerATarget": "longitudinalPlan.aTarget planner target, m/s²",
                          "commandAccel": "carControl.actuators.accel command, m/s²",
                          "aEgoEstimate": "carState.aEgo speed-derived vehicle estimate, m/s²",
                          "deltaRate": "sample-to-sample signal derivative, not physical jerk or publisher rate"}
  print(json.dumps(report, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
  main()
