#!/usr/bin/env python3
"""Rebuild a model generation on an explicitly selected compiler device."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.error import HTTPError

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from openpilot.starpilot.models.catalog import ARTIFACT_ABI, CATALOG_PATH, COMPILER_REVISION, GENERATION
from openpilot.starpilot.models.manager import atomic_json, validate_manifest

BUCKET = "StarPilot-Driving/StarPilot-Resources"
REMOTE_WORK = "/data/starpilot-v26-rebuild"
CHUNK_BYTES = 45 * 1024 * 1024


def digest(path: Path) -> str:
  with path.open("rb") as stream:
    return hashlib.file_digest(stream, "sha256").hexdigest()


def run(args: list[str], *, output=None) -> None:
  subprocess.run(args, check=True, stdout=output, stderr=subprocess.STDOUT if output is not None else None)


def remote(device: str, command: list[str], *, output=None) -> None:
  run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=30",
       device, shlex.join(command)], output=output)


def inventory() -> list[dict]:
  result = []
  url = f"https://huggingface.co/api/buckets/{BUCKET}/tree?recursive=true&limit=1000"
  while url:
    with urlopen(url, timeout=40) as response:
      result.extend(json.load(response))
      links = response.headers.get("Link", "")
    url = next((p.split(">")[0].strip("< ") for p in links.split(",") if 'rel="next"' in p), "")
  return result


def source_plan(model_id: str, source_map: dict, objects: list[dict]) -> list[dict]:
  source_id = source_map[model_id]["source_id"]
  files = [obj for obj in objects if obj["type"] == "file" and obj["path"].startswith(f"onnx/{source_id}/") and
           obj["path"].endswith(".onnx")]
  if not files:
    raise ValueError(f"No archived ONNX source for {model_id} ({source_id})")
  return files


def prepare_sources(model_id: str, files: list[dict], workspace: Path, hf: str) -> Path:
  directory = workspace / "onnx" / model_id
  directory.mkdir(parents=True, exist_ok=True)
  for obj in files:
    name = Path(obj["path"]).name
    if "driving_" not in name:
      raise ValueError(f"Unrecognized model source filename: {name}")
    name = model_id + "_" + name[name.index("driving_"):]
    destination = directory / name
    if not destination.is_file() or destination.stat().st_size != obj["size"]:
      run([hf, "buckets", "cp", f"hf://buckets/{BUCKET}/{obj['path']}", str(destination), "--format", "quiet"])
    if destination.stat().st_size != obj["size"]:
      raise ValueError("Source download size mismatch")
  return directory


def split_artifact(artifact: Path, directory: Path) -> tuple[list[Path], int]:
  directory.mkdir(parents=True, exist_ok=True)
  count = (artifact.stat().st_size + CHUNK_BYTES - 1) // CHUNK_BYTES
  if count == 1:
    return [artifact], 0
  parts = []
  with artifact.open("rb") as stream:
    for index in range(1, count + 1):
      part = directory / f"{artifact.name}.chunk{index:02d}of{count:02d}"
      part.write_bytes(stream.read(CHUNK_BYTES))
      parts.append(part)
  return parts, count


def publish_artifact(model_id: str, artifact: Path, receipt: dict, workspace: Path, hf: str) -> dict:
  if receipt["compiler_revision"] != COMPILER_REVISION or receipt["artifact_abi"] != ARTIFACT_ABI or digest(artifact) != receipt["artifact_sha256"]:
    raise ValueError("Compiled artifact identity changed")
  parts, count = split_artifact(artifact, workspace / "release" / model_id)
  for part in parts:
    run([hf, "buckets", "cp", str(part), f"hf://buckets/{BUCKET}/models/{GENERATION}/{model_id}/{part.name}", "--format", "quiet"])
  if count:
    marker = workspace / "release" / model_id / f"{artifact.name}.chunkmanifest"
    marker.write_text(str(count))
    run([hf, "buckets", "cp", str(marker), f"hf://buckets/{BUCKET}/models/{GENERATION}/{model_id}/{marker.name}", "--format", "quiet"])
  return {"artifact_format": ARTIFACT_ABI, "artifact_size": artifact.stat().st_size,
          "artifact_sha256": receipt["artifact_sha256"], "artifact_chunk_count": count,
          "source_sha256": receipt["source_sha256"]}


def compile_one(model: dict, args, source_map: dict, objects: list[dict]) -> dict:
  mid = model["id"]
  work = args.workspace
  result_path = work / "results" / f"{mid}.json"
  output_dir = work / "compiled" / mid
  artifact = output_dir / f"{mid}_driving_tinygrad.pkl"
  if result_path.is_file():
    previous = json.loads(result_path.read_text())
    if (previous.get("status") == "passed" and previous.get("compiler_revision") == COMPILER_REVISION and artifact.is_file() and
        digest(artifact) == previous["artifact_sha256"] and (not args.publish or previous.get("published"))):
      return previous
  sources = prepare_sources(mid, source_plan(mid, source_map, objects), work, args.hf)
  remote_dir = f"{REMOTE_WORK}/work/{mid}"
  remote(args.device, ["mkdir", "-p", f"{remote_dir}/onnx", f"{remote_dir}/compiled"])
  run(["rsync", "-az", str(sources) + "/", f"{args.device}:{remote_dir}/onnx/"])
  command = ["/usr/local/venv/bin/python", "/data/openpilot/scripts/model_compiler.py", "--model", mid,
             "--version", model["version"], "--input-format", source_map[mid]["input_format"],
             "--input-dir", f"{remote_dir}/onnx", "--output-dir", f"{remote_dir}/compiled"]
  if model.get("uses_external_gpu"):
    command.append("--gpu")
  with (work / "logs" / f"{mid}.log").open("ab") as log:
    remote(args.device, ["env", "PYTHONUNBUFFERED=1", *command], output=log)
    validate = ["/usr/local/venv/bin/python", "/data/openpilot/scripts/validate_driving_model.py",
                f"{remote_dir}/compiled/{artifact.name}", "--version", model["version"],
                "--source-dir", f"{remote_dir}/onnx", "--report", f"{remote_dir}/compiled/validation.json", "--max-p95-ms", "50"]
    if model.get("uses_external_gpu"):
      validate.append("--gpu")
    remote(args.device, validate, output=log)
  output_dir.mkdir(parents=True, exist_ok=True)
  run(["rsync", "-az", f"{args.device}:{remote_dir}/compiled/", str(output_dir) + "/"])
  receipt = json.loads(artifact.with_suffix(".build.json").read_text())
  validation = json.loads((output_dir / "validation.json").read_text())
  if (digest(artifact) != receipt["artifact_sha256"] or not validation.get("passed") or
      validation.get("artifact_sha256") != receipt["artifact_sha256"]):
    raise ValueError("Compiled model failed runtime validation")
  result = {**receipt, "status": "passed", "published": False, "validation": validation}
  if args.publish:
    result["release"] = publish_artifact(mid, artifact, receipt, work, args.hf)
    result["published"] = True
  atomic_json(result_path, result)
  # Only this invocation's sources and output are removed after the verified host copy exists.
  remote(args.device, ["/usr/local/venv/bin/python", "-c", "import shutil,sys; shutil.rmtree(sys.argv[1])", remote_dir])
  return result


def publish_manifest(workspace: Path, hf: str) -> None:
  manifest = json.loads(CATALOG_PATH.read_text())
  try:
    with urlopen(f"https://huggingface.co/buckets/{BUCKET}/resolve/manifests/model_names_{GENERATION}.json", timeout=30) as response:
      live = json.load(response)
    existing = validate_manifest(live)
    for row in manifest["models"]:
      if row["id"] in existing:
        row.update(existing[row["id"]])
  except HTTPError as error:
    if error.code != 404:
      raise
  for model in manifest["models"]:
    path = workspace / "results" / f"{model['id']}.json"
    if path.is_file():
      result = json.loads(path.read_text())
      if result.get("status") == "passed" and result.get("published") and result.get("compiler_revision") == COMPILER_REVISION:
        model.update(result["release"])
  path = workspace / "manifests" / f"model_names_{GENERATION}.json"
  atomic_json(path, manifest)
  run([hf, "buckets", "cp", str(path), f"hf://buckets/{BUCKET}/manifests/{path.name}", "--format", "quiet"])


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--device", required=True, help="Explicit SSH target, for example comma@comma-device.local")
  parser.add_argument("--workspace", required=True, type=Path)
  parser.add_argument("--models", nargs="+", help="Stable model IDs; defaults to the full catalog, favorites first")
  parser.add_argument("--hf", default=str(Path.home()/".local/bin/hf"))
  parser.add_argument("--publish", action="store_true", help="Upload validated v26 artifacts and manifest to Hugging Face")
  args = parser.parse_args()
  args.workspace = args.workspace.resolve()
  for directory in ("results", "logs", "manifests"):
    (args.workspace / directory).mkdir(parents=True, exist_ok=True)
  rows = json.loads(CATALOG_PATH.read_text())["models"]
  source_map = json.loads((REPO / "scripts/model_source_map_v26.json").read_text())
  if args.models:
    by_id = {row["id"]: row for row in rows}
    rows = [by_id[mid] for mid in args.models]
  else:
    rows.sort(key=lambda row: (not row.get("community_favorite", False), row["id"] != "cinquev3"))
  objects = inventory()
  atomic_json(args.workspace / "source-inventory.json", {"objects": objects})
  failures = []
  for model in rows:
    mid = model["id"]
    print(f"START {mid}", flush=True)
    started = time.monotonic()
    try:
      compile_one(model, args, source_map, objects)
      if args.publish:
        publish_manifest(args.workspace, args.hf)
      print(f"PASS {mid} {time.monotonic()-started:.0f}s", flush=True)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
      failures.append(mid)
      atomic_json(args.workspace / "results" / f"{mid}.failure.json", {"model_id": mid, "error": str(error)})
      print(f"FAIL {mid}: {error}", flush=True)
  return int(bool(failures))


if __name__ == "__main__":
  raise SystemExit(main())
