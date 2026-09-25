"""Check recorded control-axis evidence; this does not control or qualify a car."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

AXES = ("lateral", "longitudinal")
MODES = {"off": (False, False), "lateral_only": (True, False), "longitudinal_only": (False, True), "combined": (True, True)}
SCENARIOS = tuple(f"mode_{mode}" for mode in MODES) + (
  "brake", "gas", "standstill", "gear_change", "steering_override", "lateral_fault", "longitudinal_fault",
  "input_stale", "permission_revoked", "cancel", "policy_recovery", "restart", "stock_acc_handoff",
)
AXIS_SIGNALS = ("request", "permission", "effective", "command_active", "blocking_fault", "input_fresh", "displayed_active")
EXPECTED_SIGNALS = ("effective", "command_active", "displayed_active")
CONFIG_TEXT = ("platform", "device", "harness", "policy_id")
CONFIG_HASHES = ("car_params_sha256", "schema_sha256", "settings_sha256", "safety_binary_sha256",
                 "firmware_manifest_sha256", "policy_sha256", "adapter_sha256")


def configuration_id(configuration):
  return hashlib.sha256(json.dumps(configuration, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_trace(document):
  """Return pass/failed/uncovered/error for this trace's contract, never fleet clearance.

  Null and absent observations are unknown. Expected recovery behavior comes from
  a named, hashed vehicle policy and explicit frame expectations, not this module.
  """
  errors, failures, gaps = [], [], []

  def unknown(path):
    gaps.append(f"{path}: unknown")

  def mapping(value, path):
    if value is None:
      unknown(path)
      return {}
    if not isinstance(value, dict):
      errors.append(f"{path}: expected object")
      return {}
    return value

  def boolean(value, path):
    if value is None:
      unknown(path)
      return None
    if type(value) is not bool:
      errors.append(f"{path}: expected boolean or null")
      return None
    return value

  def text(value, path, pattern=None):
    if value is None or value == "":
      unknown(path)
    elif not isinstance(value, str) or (pattern and not re.fullmatch(pattern, value)):
      errors.append(f"{path}: invalid string")

  document = mapping(document, "trace")
  if document.get("schema_version") != 1 or type(document.get("schema_version")) is not int:
    errors.append("schema_version: expected 1")
  text(document.get("case_id"), "case_id")
  scenario = document.get("scenario")
  if scenario not in SCENARIOS:
    errors.append("scenario: unknown scenario")
  kind = document.get("evidence_kind")
  if kind not in ("synthetic", "replay", "bench", "vehicle_recording"):
    errors.append("evidence_kind: unknown evidence kind")
  text(document.get("recording_sha256"), "recording_sha256", r"[0-9a-f]{64}")
  config = mapping(document.get("configuration"), "configuration")
  for key in CONFIG_TEXT:
    text(config.get(key), f"configuration.{key}")
  for key in CONFIG_HASHES:
    text(config.get(key), f"configuration.{key}", r"[0-9a-f]{64}")
  text(config.get("source_commit"), "configuration.source_commit", r"[0-9a-f]{40}")
  owner = config.get("longitudinal_owner")
  if owner is None:
    unknown("configuration.longitudinal_owner")
  elif owner not in ("system", "stock", "none"):
    errors.append("configuration.longitudinal_owner: invalid owner")
  supported = config.get("supported_modes")
  if supported is None:
    unknown("configuration.supported_modes")
    supported = []
  elif not isinstance(supported, list) or any(not isinstance(m, str) or m not in MODES for m in supported):
    errors.append("configuration.supported_modes: invalid modes")
    supported = []
  elif len(supported) != len(set(supported)) or "off" not in supported:
    errors.append("configuration.supported_modes: unique entries including off required")

  requirements = mapping(document.get("requirements"), "requirements")
  minimum = requirements.get("minimum_frames")
  max_gap = requirements.get("max_frame_gap_ns")
  if type(minimum) is not int or minimum < 2:
    errors.append("requirements.minimum_frames: integer >= 2 required")
    minimum = 2
  if type(max_gap) is not int or max_gap <= 0:
    errors.append("requirements.max_frame_gap_ns: positive integer required")
    max_gap = None
  required_events = requirements.get("required_events")
  if not isinstance(required_events, list) or any(not isinstance(e, str) or not e for e in required_events):
    errors.append("requirements.required_events: string list required")
    required_events = []
  # Transition cases must identify the transition they claim to exercise.
  if scenario in SCENARIOS and not scenario.startswith("mode_") and scenario not in required_events:
    gaps.append(f"{scenario}: required event absent from scenario contract")
  frames = document.get("frames")
  if not isinstance(frames, list):
    errors.append("frames: expected list")
    frames = []
  if len(frames) < minimum:
    gaps.append("insufficient frames")
  events, modes = set(), Counter()
  active = {mode: Counter() for mode in MODES}
  stock_active = Counter()
  previous_time = None
  for index, raw in enumerate(frames):
    prefix = f"frames[{index}]"
    frame = mapping(raw, prefix)
    time_ns = frame.get("time_ns")
    if type(time_ns) is not int or time_ns < 0:
      errors.append(f"{prefix}.time_ns: nonnegative integer required")
    else:
      if previous_time is not None:
        if time_ns <= previous_time:
          errors.append(f"{prefix}.time_ns: timestamps must strictly increase")
        elif max_gap is not None and time_ns - previous_time > max_gap:
          gaps.append(f"{prefix}: unobserved interval exceeds contract")
      previous_time = time_ns
    mode = frame.get("mode")
    valid_mode = isinstance(mode, str) and mode in MODES
    if not valid_mode:
      errors.append(f"{prefix}.mode: invalid mode")
      allowed_axes = (False, False)
    else:
      modes[mode] += 1
      allowed_axes = MODES[mode]
    event = frame.get("event")
    if event is not None:
      if not isinstance(event, str) or not event:
        errors.append(f"{prefix}.event: string or null required")
      else:
        events.add(event)
    observed = mapping(frame.get("observed"), f"{prefix}.observed")
    expected = mapping(frame.get("expected"), f"{prefix}.expected")
    signals = {}
    for name in AXIS_SIGNALS:
      pair = mapping(observed.get(name), f"{prefix}.observed.{name}")
      signals[name] = {axis: boolean(pair.get(axis), f"{prefix}.observed.{name}.{axis}") for axis in AXES}
    can_observed = boolean(observed.get("control_can_observed"), f"{prefix}.observed.control_can_observed")
    feedback_fresh = boolean(observed.get("safety_feedback_fresh"), f"{prefix}.observed.safety_feedback_fresh")
    stock = boolean(observed.get("stock_acc_active"), f"{prefix}.observed.stock_acc_active")
    if can_observed is False:
      gaps.append(f"{prefix}: control CAN not observed; no-command cannot be inferred")
    if feedback_fresh is False:
      gaps.append(f"{prefix}: safety feedback stale")
    for signal in EXPECTED_SIGNALS:
      pair = mapping(expected.get(signal), f"{prefix}.expected.{signal}")
      for axis in AXES:
        desired = boolean(pair.get(axis), f"{prefix}.expected.{signal}.{axis}")
        actual = signals[signal][axis]
        if desired is not None and actual is not None and desired != actual:
          failures.append(f"{prefix}: {signal}.{axis} differs from explicit policy expectation")
    desired_stock = boolean(expected.get("stock_acc_active"), f"{prefix}.expected.stock_acc_active")
    if stock is not None and desired_stock is not None and stock != desired_stock:
      failures.append(f"{prefix}: stock ACC differs from explicit policy expectation")
    for axis, selected in zip(AXES, allowed_axes, strict=True):
      request, permission, effective, command, fault, fresh = (signals[s][axis] for s in AXIS_SIGNALS[:6])
      if any(signals[s][axis] is True for s in ("request", "effective", "command_active")) and not selected:
        failures.append(f"{prefix}: {axis} activity outside selected mode")
      if (effective is True or command is True) and mode not in supported:
        failures.append(f"{prefix}: activity in unsupported mode")
      if axis == "longitudinal" and owner in ("stock", "none") and (effective is True or command is True):
        failures.append(f"{prefix}: host longitudinal actuation without system ownership")
      if effective is True and any(value is False for value in (request, permission, fresh)):
        failures.append(f"{prefix}: effective {axis} without request/permission/fresh input")
      if command is True and any(value is False for value in (request, permission, effective, fresh)):
        failures.append(f"{prefix}: active {axis} command without effective authorization")
      if fault is True and (effective is True or command is True):
        failures.append(f"{prefix}: {axis} active during a blocking axis fault")
      if valid_mode and command is True and can_observed is True and feedback_fresh is True:
        active[mode][axis] += 1
    if valid_mode and stock is True and can_observed is True and feedback_fresh is True:
      stock_active[mode] += 1
  gaps.extend(f"required event not observed: {event}" for event in required_events if event not in events)
  if isinstance(scenario, str) and scenario.startswith("mode_"):
    target = scenario.removeprefix("mode_")
    if target in MODES:
      if modes[target] < minimum:
        gaps.append(f"{target}: insufficient target-mode samples")
      if target in supported:
        for axis, selected in zip(AXES, MODES[target], strict=True):
          if selected and (axis == "lateral" or owner == "system") and active[target][axis] < minimum:
            gaps.append(f"{target}: insufficient observed active {axis} commands")
        if MODES[target][1] and owner == "stock" and stock_active[target] < minimum:
          gaps.append(f"{target}: insufficient observed stock ACC activity")
        if MODES[target][1] and owner == "none":
          gaps.append(f"{target}: requested longitudinal capability has no owner")
  status = "error" if errors else "failed" if failures else "uncovered" if gaps else "pass"
  return {"schema_version": 1, "scope": "recorded_control_trace_contract", "vehicle_qualification": "not_established",
          "case_id": document.get("case_id"), "scenario": scenario, "evidence_kind": kind,
          "configuration_id": configuration_id(config), "status": status, "errors": errors, "failures": failures,
          "uncovered": gaps, "frames": len(frames), "mode_frames": dict(modes),
          "observed_active_command_frames": {m: dict(v) for m, v in active.items()}}


def validate_matrix(documents, configurations):
  """Require every named scenario for each exact caller-supplied configuration.

  Synthetic evidence cannot satisfy this coverage gate. Even complete recorded
  coverage does not establish physical vehicle or release qualification.
  """
  results = [validate_trace(document) for document in documents]
  missing = []
  required_ids = [configuration_id(config) for config in configurations]
  if not required_ids:
    missing.append({"reason": "no required configurations"})
  for config_id in dict.fromkeys(required_ids):
    for scenario in SCENARIOS:
      rows = [r for r in results if r["configuration_id"] == config_id and r["scenario"] == scenario]
      if not any(r["status"] == "pass" and r["evidence_kind"] != "synthetic" for r in rows):
        missing.append({"configuration_id": config_id, "scenario": scenario, "reason": "no passing recorded evidence"})
  statuses = {r["status"] for r in results}
  status = "error" if "error" in statuses else "failed" if "failed" in statuses else "uncovered" if missing or "uncovered" in statuses else "pass"
  return {"schema_version": 1, "scope": "declared_configuration_coverage", "vehicle_qualification": "not_established",
          "status": status, "required_configurations": len(set(required_ids)), "required_scenarios": list(SCENARIOS),
          "results": results, "uncovered": missing}


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("trace", type=Path)
  parser.add_argument("--output", type=Path)
  args = parser.parse_args()
  try:
    report = validate_trace(json.loads(args.trace.read_text()))
  except (OSError, ValueError) as error:
    report = {"status": "error", "scope": "recorded_control_trace_contract", "vehicle_qualification": "not_established", "errors": [str(error)]}
  data = json.dumps(report, indent=2) + "\n"
  if args.output:
    args.output.write_text(data)
  else:
    print(data, end="")
  return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
  raise SystemExit(main())
