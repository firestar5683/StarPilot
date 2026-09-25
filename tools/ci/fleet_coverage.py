#!/usr/bin/env python3
"""Report exact source-platform obligations without qualifying any vehicle."""

import argparse
from collections import Counter
import hashlib
import importlib.machinery
import json
from pathlib import Path
import re
import subprocess

from openpilot.starpilot.validation.control_modes import SCENARIOS, configuration_id, validate_matrix

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "openpilot/starpilot/validation/required-platforms.json"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
REVISION = re.compile(r"[0-9a-f]{40}\Z")
NATIVE_CAN_SOURCES = {"opendbc_repo/opendbc/can/packer.py", "opendbc_repo/opendbc/can/parser.py"}
RELEVANT_SOURCE_PATHS = ("opendbc_repo", "openpilot/common", "openpilot/cereal", "msgq_repo",
                         "tools/ci/run_vehicle_tests.py", "tools/test_runner.py", "upstream-sync.json")


def sha256(path):
  return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(value):
  """Hash compact, key-sorted UTF-8 JSON without a trailing newline."""
  return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def relevant_dirty_paths():
  output = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all", "--", *RELEVANT_SOURCE_PATHS],
                                   cwd=ROOT, text=True)
  return output.splitlines()


def _relevant_status_lines(status):
  if not isinstance(status, str):
    return []
  return [line for line in status.splitlines() if len(line) >= 4 and any(
    line[3:] == path or line[3:].startswith(path + "/") for path in RELEVANT_SOURCE_PATHS)]


def _ids(values, label, errors):
  if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
    errors.append(f"{label}: expected nonempty string IDs")
    return []
  duplicates = sorted(k for k, count in Counter(values).items() if count > 1)
  if duplicates:
    errors.append(f"{label}: duplicate exact IDs {duplicates}")
  return values


def evaluate(manifest, coverage, results, mode_evidence=None, *, expected_revision=None, hashes=None, dirty_relevant=None):
  """Check independent registration, test execution and per-config mode evidence.

  All input documents are caller supplied; their physical origin is not asserted.
  """
  errors, failures, uncovered = [], [], []
  if not isinstance(manifest, dict):
    errors.append("required-platform manifest: expected object")
    manifest = {}
  if not isinstance(coverage, dict):
    errors.append("interface coverage: expected object")
    coverage = {}
  if not isinstance(results, dict):
    errors.append("interface results: expected object")
    results = {}
  if mode_evidence is not None and not isinstance(mode_evidence, dict):
    errors.append("mode evidence: expected object")
    mode_evidence = {}
  if dirty_relevant is None:
    dirty_relevant = relevant_dirty_paths()
  if dirty_relevant:
    uncovered.append("relevant vehicle/runner source differs from committed checkout")
  platforms = manifest.get("platforms")
  if manifest.get("schema_version") != 1 or not isinstance(platforms, list):
    errors.append("required-platform manifest: expected schema v1 and platforms list")
    platforms = []
  required = _ids([r.get("id") if isinstance(r, dict) else None for r in platforms], "required platforms", errors)
  required_set = set(required)
  if not required_set:
    errors.append("required-platform manifest: at least one exact source ID required")
  additions = _ids(manifest.get("upstream_additions"), "upstream additions", errors)
  addition_set = set(additions)
  if required_set & addition_set:
    errors.append("required source platforms and upstream additions overlap")
  all_obligations = required_set | addition_set
  for row in platforms:
    if isinstance(row, dict) and (not row.get("family") or row.get("source_declaration") not in ("source_only", "same_declaration", "declaration_changed")):
      errors.append(f"required platform metadata invalid: {row.get('id')}")
  if not REVISION.fullmatch(str(manifest.get("source_revision", ""))) or not SHA256.fullmatch(str(manifest.get("source_inventory_sha256", ""))):
    errors.append("required-platform manifest source provenance missing")

  registered = _ids(coverage.get("platform_ids"), "reported registry", errors)
  registered_set = set(registered)
  mapped = coverage.get("interface_test_ids")
  if not isinstance(mapped, dict):
    errors.append("interface_test_ids: expected exact ID to test ID mapping")
    mapped = {}
  elif any(not isinstance(k, str) or not k for k in mapped):
    errors.append("interface_test_ids: mapping keys must be exact string IDs")
    mapped = {k: v for k, v in mapped.items() if isinstance(k, str) and k}
  selected = _ids(coverage.get("selected_test_ids"), "selected tests", errors)
  raw_records = results.get("results")
  if not isinstance(raw_records, list):
    errors.append("results: expected per-test records")
    raw_records = []
  record_ids = [r.get("id") if isinstance(r, dict) else None for r in raw_records]
  if any(not isinstance(v, str) for v in record_ids) or len(record_ids) != len({v for v in record_ids if isinstance(v, str)}):
    errors.append("results: invalid or duplicate test IDs")
  by_test = {r["id"]: r for r in raw_records if isinstance(r, dict) and isinstance(r.get("id"), str)}
  nonpassing_records = [r for r in raw_records if isinstance(r, dict) and r.get("status") != "passed"]
  for record in nonpassing_records:
    issue = f"execution record {record.get('id')}: {record.get('status', 'missing status')}"
    if record.get("status") == "skipped":
      uncovered.append(issue)
    else:
      failures.append(issue)
  if coverage.get("suite") != "interfaces" or coverage.get("schema_version") != 1:
    errors.append("coverage: expected interface suite schema v1")
  if results.get("schema_version") != 1:
    errors.append("results: expected schema v1")
  result_selected = results.get("selected_test_ids")
  if not isinstance(result_selected, list) or any(not isinstance(v, str) for v in result_selected):
    errors.append("results selected_test_ids: expected test IDs")
    result_selected = []
  if set(selected) != set(by_test) or set(selected) != set(result_selected):
    errors.append("selected tests and execution records differ")
  mapped_values = list(mapped.values())
  unique_mapped = {v for v in mapped_values if isinstance(v, str)}
  if set(mapped) != registered_set or len(unique_mapped) != len(mapped):
    errors.append("registered platforms and unique interface test mapping differ")
  if coverage.get("platform_count") != len(registered) or coverage.get("result_sha256") != (hashes or {}).get("results"):
    errors.append("interface coverage count or companion results hash invalid")
  if coverage.get("interface_results") != {p: by_test.get(t) if isinstance(t, str) else None for p, t in mapped.items()}:
    errors.append("embedded interface results differ from execution records")
  for p, test_id in mapped.items():
    if not isinstance(test_id, str) or not test_id.endswith(".test_car_interfaces_" + p) or test_id not in selected:
      errors.append(f"{p}: concrete interface test mapping invalid")
  if coverage.get("status") != "completed" or results.get("status") != "completed" or coverage.get("exit_code") != 0 or results.get("exit_code") != 0:
    failures.append("interface suite did not complete successfully")
  if coverage.get("collection_errors") or coverage.get("gate_errors") or results.get("collection_errors") or results.get("gate_errors"):
    failures.append("interface suite reported collection or gate failures")
  source = coverage.get("source")
  source = source if isinstance(source, dict) else {}
  if not isinstance(source.get("status"), str):
    uncovered.append("interface report working-tree status missing or malformed")
  reported_dirty = _relevant_status_lines(source.get("status"))
  if reported_dirty:
    uncovered.append("interface report recorded relevant dirty vehicle/runner source")
  revision = source.get("revision")
  dependencies = source.get("dependencies")
  opendbc = [d for d in dependencies if isinstance(d, dict) and d.get("path") == "opendbc_repo"] if isinstance(dependencies, list) else []
  if not REVISION.fullmatch(str(revision or "")) or len(opendbc) != 1 or not REVISION.fullmatch(str(opendbc[0].get("commit", ""))):
    errors.append("interface source/dependency provenance missing")
  if expected_revision is not None and revision != expected_revision:
    uncovered.append("interface report source revision differs from requested checkout")
  current_manifest = ROOT / "upstream-sync.json"
  current_runner = ROOT / "tools/ci/run_vehicle_tests.py"
  current_test_runner = ROOT / "tools/test_runner.py"
  for field, path in (("manifest_sha256", current_manifest), ("suite_runner_sha256", current_runner), ("runner_sha256", current_test_runner)):
    if source.get(field) != sha256(path):
      uncovered.append(f"interface report {field} differs from current source")
  pinned = json.loads(current_manifest.read_text()).get("dependencies", [])
  pinned_opendbc = [d for d in pinned if d.get("path") == "opendbc_repo"]
  if len(pinned_opendbc) != 1 or len(opendbc) != 1 or opendbc[0].get("commit") != pinned_opendbc[0].get("commit"):
    uncovered.append("interface report opendbc revision differs from current pin")
  native = coverage.get("native")
  if not isinstance(native, dict) or not isinstance(native.get("can_sources"), dict) or not isinstance(native.get("pycapnp"), dict):
    uncovered.append("interface report native parser/packer provenance missing")
  else:
    if set(native["can_sources"]) != NATIVE_CAN_SOURCES:
      uncovered.append("interface report native CAN source set incomplete or unexpected")
    for source_path, digest in native["can_sources"].items():
      if not isinstance(source_path, str) or not (ROOT / source_path).is_file() or digest != sha256(ROOT / source_path):
        uncovered.append(f"interface report native CAN source mismatch: {source_path}")
    pycapnp = native["pycapnp"]
    binary_name = pycapnp.get("path")
    binary_path = Path(binary_name) if isinstance(binary_name, str) else None
    if (binary_path is None or not any(str(binary_path).endswith(s) for s in importlib.machinery.EXTENSION_SUFFIXES)
        or not binary_path.is_file() or pycapnp.get("sha256") != sha256(binary_path)):
      uncovered.append("interface report pycapnp binary unavailable or changed")
  if results.get("selected_test_ids") != selected:
    errors.append("selected test order differs between coverage and results")
  current_execution_compatible = not errors and not failures and not dirty_relevant and not reported_dirty
  current_execution_compatible &= not any(issue.startswith("interface report ") for issue in uncovered)

  platform_rows = []
  for p in sorted(required_set):
    if p not in registered_set:
      interface = "missing_port"
    elif p not in mapped:
      interface = "missing_test"
    else:
      test_id = mapped[p]
      status = by_test.get(test_id, {}).get("status") if isinstance(test_id, str) else None
      interface = "passed" if status == "passed" else "missing_test" if status is None else status
    current_interface = interface if interface != "passed" else "passed" if current_execution_compatible else "historical_pass_only"
    platform_rows.append({"id": p, "obligation": "source", "interface": interface,
                          "current_interface": current_interface, "mode": "uncovered"})
    if interface != "passed":
      uncovered.append(f"{p}: interface {interface}")
      if interface not in ("missing_port", "missing_test", "skipped"):
        failures.append(f"{p}: concrete interface test {interface}")
  upstream_only = sorted(registered_set - required_set)
  if set(upstream_only) != addition_set:
    uncovered.append("upstream additions differ from frozen manifest")
  # Additions remain independent obligations even if a future registry drops one.
  for p in sorted(addition_set):
    status = by_test.get(mapped.get(p), {}).get("status") if isinstance(mapped.get(p), str) else None
    reported_interface = "passed" if status == "passed" else "missing_port" if p not in registered_set else status or "missing_test"
    current_interface = "historical_pass_only" if reported_interface == "passed" and not current_execution_compatible else reported_interface
    platform_rows.append({"id": p, "obligation": "upstream_addition",
                          "interface": reported_interface, "current_interface": current_interface,
                          "mode": "uncovered"})
    if status != "passed":
      uncovered.append(f"upstream addition {p}: concrete interface test {status or 'missing'}")
      if status not in (None, "skipped"):
        failures.append(f"upstream addition {p}: concrete interface test {status}")

  mode_summary = {"input": "absent", "required_scenarios": list(SCENARIOS), "configuration_count": 0, "recorded_trace_count": 0}
  if mode_evidence is None:
    uncovered.append("independent per-configuration mode evidence absent")
  else:
    mode_summary["input"] = "supplied"
    if mode_evidence.get("schema_version") != 1:
      errors.append("mode evidence: expected schema v1")
    provenance = mode_evidence.get("provenance")
    provenance_keys = ("configuration_inventory_sha256", "trace_catalog_sha256")
    if not isinstance(provenance, dict) or any(not SHA256.fullmatch(str(provenance.get(k, ""))) for k in provenance_keys):
      uncovered.append("mode evidence: configuration inventory or trace catalog provenance missing")
    configurations = mode_evidence.get("configurations")
    traces = mode_evidence.get("traces")
    if not isinstance(configurations, list) or not isinstance(traces, list):
      errors.append("mode evidence: configurations and traces must be lists")
      configurations, traces = [], []
    if isinstance(provenance, dict):
      if provenance.get("configuration_inventory_sha256") != canonical_sha256(configurations):
        errors.append("mode evidence: configuration inventory digest mismatch")
      if provenance.get("trace_catalog_sha256") != canonical_sha256(traces):
        errors.append("mode evidence: trace catalog digest mismatch")
    mode_summary["configuration_count"] = len(configurations)
    mode_summary["recorded_trace_count"] = len(traces)
    config_ids = [configuration_id(c) for c in configurations if isinstance(c, dict)]
    if len(config_ids) != len(configurations) or len(config_ids) != len(set(config_ids)):
      errors.append("mode evidence: invalid or duplicate exact configurations")
    if any(not isinstance(c, dict) or not isinstance(c.get("platform"), str) or c["platform"] not in all_obligations for c in configurations):
      errors.append("mode evidence: configuration platform is not an exact obligated ID")
    if any(not isinstance(t, dict) or not isinstance(t.get("configuration"), dict) or configuration_id(t["configuration"]) not in config_ids for t in traces):
      errors.append("mode evidence: trace has no exact declared configuration")
    complete = mode_evidence.get("enumeration_complete")
    if complete is not True:
      uncovered.append("mode evidence: exact configuration enumeration not asserted complete")
    for platform in sorted(all_obligations):
      row = next((r for r in platform_rows if r["id"] == platform), None)
      configs = [c for c in configurations if isinstance(c, dict) and c.get("platform") == platform]
      if not configs:
        uncovered.append(f"{platform}: no exact configurations enumerated")
        continue
      platform_traces = [t for t in traces if isinstance(t, dict) and isinstance(t.get("configuration"), dict)
                         and t["configuration"].get("platform") == platform]
      try:
        matrix = validate_matrix(platform_traces, configs)
      except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"{platform}: malformed mode matrix: {type(exc).__name__}")
        continue
      if row is not None:
        row["mode"] = matrix["status"]
      if matrix["status"] == "error":
        errors.append(f"{platform}: malformed mode trace")
      elif matrix["status"] == "failed":
        failures.append(f"{platform}: mode invariant or expectation failed")
      elif matrix["status"] == "uncovered":
        uncovered.append(f"{platform}: {len(matrix['uncovered'])} mode scenario/configuration gaps")

  status = "error" if errors else "failed" if failures else "uncovered" if uncovered else "pass"
  if errors or failures:
    current_execution_compatible = False
    for row in platform_rows:
      if row["current_interface"] == "passed":
        row["current_interface"] = "historical_pass_only"
  return {"schema_version": 1, "scope": "exact_source_platform_and_recorded_configuration_coverage",
          "vehicle_qualification": "not_established", "status": status,
          "source_revision": manifest.get("source_revision"), "interface_report_revision": revision,
          "hashes": hashes or {}, "required_platform_count": len(required_set),
          "upstream_addition_count": len(addition_set), "registered_platform_count": len(registered_set),
          "upstream_only": upstream_only, "required_upstream_additions": sorted(addition_set),
          "evidence_limit": "Supplied recording labels and hashes do not authenticate trace adapters or physical origin.",
          "relevant_dirty_paths": dirty_relevant,
          "reported_relevant_dirty_paths": reported_dirty,
          "interface_execution_context": "current_compatible" if current_execution_compatible else "historical_or_incompatible",
          "reported_interface_counts": dict(Counter(r["interface"] for r in platform_rows)),
          "current_interface_counts": dict(Counter(r["current_interface"] for r in platform_rows)),
          "platforms": platform_rows,
          "mode_evidence": mode_summary, "errors": errors, "failures": failures, "uncovered": uncovered}


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
  parser.add_argument("--interface-coverage", type=Path, required=True)
  parser.add_argument("--interface-results", type=Path, required=True)
  parser.add_argument("--mode-evidence", type=Path)
  parser.add_argument("--expected-revision", help="40-character checkout revision; defaults to current HEAD")
  parser.add_argument("--output", type=Path, required=True)
  args = parser.parse_args()
  if args.output.exists():
    parser.error(f"output already exists; refusing to replace evidence: {args.output}")
  paths = {"manifest": args.manifest, "coverage": args.interface_coverage, "results": args.interface_results}
  if args.mode_evidence:
    paths["mode_evidence"] = args.mode_evidence
  hashes = {k: sha256(v) for k, v in paths.items()}
  checkout_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
  if args.expected_revision is not None and args.expected_revision != checkout_revision:
    parser.error("expected revision differs from current checkout HEAD")
  expected = checkout_revision
  report = evaluate(json.loads(args.manifest.read_text()), json.loads(args.interface_coverage.read_text()),
                    json.loads(args.interface_results.read_text()),
                    json.loads(args.mode_evidence.read_text()) if args.mode_evidence else None,
                    expected_revision=expected, hashes=hashes, dirty_relevant=relevant_dirty_paths())
  args.output.parent.mkdir(parents=True, exist_ok=True)
  with args.output.open("x") as stream:
    stream.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
  summary = (f"fleet coverage: {report['status']}; required={report['required_platform_count']}; " +
             f"registered={report['registered_platform_count']}; missing={report['reported_interface_counts'].get('missing_port', 0)}; " +
             f"current passes={report['current_interface_counts'].get('passed', 0)}; " +
             f"mode configurations={report['mode_evidence']['configuration_count']}; report={args.output}")
  print(summary)
  return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
  raise SystemExit(main())
