#!/usr/bin/env python3
"""Test and build the pinned map provider, with optional isolated shadow IPC tests."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "mapd_repo"


def source_identity():
  files = {path.relative_to(SOURCE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
           for path in SOURCE.rglob("*") if path.is_file() and
           path.relative_to(SOURCE).parts[0] not in (".git", "build", "media", "offline")}
  return {"revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
          "manifest_sha256": hashlib.sha256((ROOT / "upstream-sync.json").read_bytes()).hexdigest(),
          "files": files}


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--go", default="go", help="Go executable; go.mod selects the supported version")
  parser.add_argument("--output", type=Path, required=True, help="New directory outside mapd_repo")
  args = parser.parse_args()
  output = args.output.resolve()
  if output == SOURCE or SOURCE in output.parents:
    parser.error("Test output must be outside provider source")
  if output.exists():
    parser.error("Use a fresh evidence directory")
  go = shutil.which(args.go)
  if go is None:
    parser.error("Go is not installed; install the version recorded in mapd_repo/go.mod")
  output.mkdir(parents=True)
  env = dict(os.environ, GOTOOLCHAIN="local")
  before = source_identity()
  manifest = json.loads((ROOT / "upstream-sync.json").read_text())
  pin = next(entry for entry in manifest["dependencies"] if entry["path"] == "mapd_repo")
  report = {"provider": pin, "source_before": before, "commands": [], "tests": []}
  report["required_ipc_targets"] = {
    "go_to_host": env.get("STARPILOT_SHADOW_IPC_REQUIRED") == "1",
    "host_gps_to_shadow_executable": env.get("STARPILOT_SHADOW_EXEC_REQUIRED") == "1",
  }
  digest = hashlib.sha256(json.dumps(before["files"], sort_keys=True).encode()).hexdigest()
  report["source_digest"] = digest

  def run(label, arguments):
    command = [go, *arguments]
    start = time.monotonic()
    with (output / f"{label}.stdout").open("w") as stdout, (output / f"{label}.stderr").open("w") as stderr:
      result = subprocess.run(command, cwd=SOURCE, env=env, stdout=stdout, stderr=stderr)
    report["commands"].append({"label": label, "command": command, "exit_code": result.returncode,
                               "duration_seconds": time.monotonic() - start})
    return result.returncode

  run("version", ["version"])
  run("test", ["test", "-mod=readonly", "-json", "./..."])
  for line in (output / "test.stdout").read_text().splitlines():
    record = json.loads(line)
    if record.get("Action") in ("pass", "fail", "skip"):
      report["tests"].append({key: record[key] for key in ("Action", "Package", "Test", "Elapsed") if key in record})
  run("vet", ["vet", "-mod=readonly", "./..."])
  binary = output / "mapd"
  stamp = f'-X main.sourceRevision={before["revision"]} -X main.upstreamRevision={pin["commit"]} -X main.sourceDigest={digest}'
  built = run("build", ["build", "-mod=readonly", "-trimpath", "-buildvcs=true", "-ldflags", stamp, "-o", str(binary), "."])
  if built == 0:
    built_bytes = binary.read_bytes()
    report["binary_sha256"] = hashlib.sha256(built_bytes).hexdigest()
    report["embedded_source_stamps"] = all(value.encode() in built_bytes for value in (before["revision"], pin["commit"], digest))
    run("build-info", ["version", "-m", str(binary)])
  report["source_after"] = source_identity()
  report["source_unchanged"] = before == report["source_after"]
  report["counts"] = dict(Counter(item["Action"] for item in report["tests"] if "Test" in item))
  report["passed"] = report["source_unchanged"] and report.get("embedded_source_stamps", False) and bool(report["counts"].get("pass")) and all(
    command["exit_code"] == 0 for command in report["commands"])
  report["scope"] = (
    "Provider tests and build; the selected executable IPC fixture runs only temporary --shadow with private IPC/Params and synthetic tiles. "
    if report["required_ipc_targets"]["host_gps_to_shadow_executable"] else
    "Provider tests and build; provider executable not started. "
  ) + "No installed provider, real maps, route or device qualification."
  (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
  print(json.dumps({key: report[key] for key in ("passed", "counts", "source_unchanged", "scope")}))
  return int(not report["passed"])


if __name__ == "__main__":
  raise SystemExit(main())
