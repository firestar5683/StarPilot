#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "scripts") not in sys.path:
  sys.path.insert(0, str(REPO_ROOT / "scripts"))

from model_compiler import REPOSITORY_FILE_LIMIT, split_oversized_artifact

DEFAULT_OPENPILOT = Path.home() / "openpilot"
DEFAULT_WORKSPACE = Path("/Volumes/T5/StarPilot-Model-Rebuild-2026-06-22")
DEFAULT_SOURCE_MAP = REPO_ROOT / "scripts/model_source_map_v22.json"
DEFAULT_MANIFEST = DEFAULT_WORKSPACE / "manifests/model_names_v22.json"
REMOTE = os.environ.get("STAR_PILOT_MODEL_REMOTE", "comma@192.168.3.109")
REMOTE_ROOT = Path("/data/openpilot")
SSH_OPTIONS = ("-o", "ConnectTimeout=10", "-o", "ConnectionAttempts=1")

MODEL_FILENAMES = (
  "driving_supercombo.onnx",
  "driving_vision.onnx",
  "driving_policy.onnx",
  "driving_on_policy.onnx",
  "driving_off_policy.onnx",
)
MODEL_PATH_PREFIXES = (
  "openpilot/selfdrive/modeld/models",
  "selfdrive/modeld/models",
  "frogpilot/tinygrad_modeld/models",
)


def run(command: list[str], *, cwd: Path | None = None, stdout=None, check: bool = True):
  return subprocess.run(command, cwd=cwd, stdout=stdout, check=check)


def sha256_file(path: Path) -> str:
  digest = hashlib.sha256()
  with open(path, "rb") as source:
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
      digest.update(chunk)
  return digest.hexdigest()


def load_json(path: Path):
  return json.loads(path.read_text())


def ensure_workspace(workspace: Path) -> None:
  for relative in (
    "onnx",
    "compiled",
    "driver-monitoring",
    "ready-for-resources",
    "manifests",
    "logs",
    "results",
    "source-maps",
    "scripts",
    "external-upload",
  ):
    (workspace / relative).mkdir(parents=True, exist_ok=True)


def git_object_path(repo: Path, oid: str) -> Path:
  git_dir = subprocess.check_output(
    ["git", "-C", str(repo), "rev-parse", "--git-dir"], text=True,
  ).strip()
  git_dir_path = Path(git_dir)
  if not git_dir_path.is_absolute():
    git_dir_path = repo / git_dir_path
  return git_dir_path / "lfs/objects" / oid[:2] / oid[2:4] / oid


def parse_lfs_pointer(path: Path) -> tuple[str, int] | None:
  with open(path, "rb") as source:
    head = source.read(512)
  if not head.startswith(b"version https://git-lfs.github.com/spec/v1"):
    return None
  fields = {}
  for line in head.decode("ascii").splitlines():
    if " " in line:
      key, value = line.split(" ", 1)
      fields[key] = value
  oid = fields.get("oid", "").removeprefix("sha256:")
  return (oid, int(fields["size"])) if oid and "size" in fields else None


def resolve_lfs(repo: Path, pointer_path: Path, ref: str, git_path: str) -> None:
  pointer = parse_lfs_pointer(pointer_path)
  if pointer is None:
    return
  oid, expected_size = pointer
  object_path = git_object_path(repo, oid)
  if not object_path.is_file():
    fetch_refs = [ref]
    if not ref.startswith("refs/"):
      fetch_refs.extend((f"refs/remotes/origin/{ref}", f"refs/heads/{ref}"))
    for fetch_ref in fetch_refs:
      result = subprocess.run(
        ["git", "-C", str(repo), "lfs", "fetch", "origin", fetch_ref, "--include", git_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
      )
      if result.returncode == 0 and object_path.is_file():
        break
  if not object_path.is_file():
    raise FileNotFoundError(f"Missing LFS object {oid} for {ref}:{git_path}")
  if object_path.stat().st_size != expected_size or sha256_file(object_path) != oid:
    raise ValueError(f"Invalid LFS object {oid} for {ref}:{git_path}")
  temporary = pointer_path.with_suffix(pointer_path.suffix + ".resolved")
  shutil.copyfile(object_path, temporary)
  temporary.replace(pointer_path)


def git_path_exists(repo: Path, ref: str, git_path: str) -> bool:
  result = subprocess.run(
    ["git", "-C", str(repo), "cat-file", "-e", f"{ref}:{git_path}"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
  )
  return result.returncode == 0


def ensure_git_ref(repo: Path, ref: str) -> None:
  if subprocess.run(
    ["git", "-C", str(repo), "cat-file", "-e", f"{ref}^{{commit}}"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
  ).returncode == 0:
    return
  run(["git", "-C", str(repo), "fetch", "--no-tags", "https://github.com/commaai/openpilot.git", ref])


def extract_git_file(repo: Path, ref: str, git_path: str, destination: Path) -> None:
  destination.parent.mkdir(parents=True, exist_ok=True)
  temporary = destination.with_suffix(destination.suffix + ".tmp")
  with open(temporary, "wb") as output:
    run(["git", "-C", str(repo), "show", f"{ref}:{git_path}"], stdout=output)
  resolve_lfs(repo, temporary, ref, git_path)
  temporary.replace(destination)


def find_model_paths(repo: Path, ref: str, input_format: str, uses_external_gpu: bool = False) -> dict[str, str]:
  """
  Returns a dictionary mapping the remote Git path to the standard local filename.
  This allows pulling a `big_` prefixed LFS file but saving it without the prefix locally.
  """
  prefix = "big_" if uses_external_gpu else ""
  requested_standard_names = (
    ("driving_supercombo.onnx",)
    if input_format == "supercombo"
    else (
      "driving_vision.onnx",
      "driving_policy.onnx",
      "driving_on_policy.onnx",
      "driving_off_policy.onnx",
    )
  )

  found: dict[str, str] = {}
  for standard_name in requested_standard_names:
    git_filename = f"{prefix}{standard_name}"
    for path_prefix in MODEL_PATH_PREFIXES:
      git_path = f"{path_prefix}/{git_filename}"
      if git_path_exists(repo, ref, git_path):
        found[git_path] = standard_name
        break

  if input_format == "supercombo" and len(found) != 1:
    raise FileNotFoundError(f"No supercombo ONNX found at {ref} (looked for {prefix}driving_supercombo.onnx)")

  if input_format == "split":
    standard_names_found = set(found.values())
    if "driving_vision.onnx" not in standard_names_found:
      raise FileNotFoundError(f"No {prefix}driving_vision.onnx found at {ref}")
    if not standard_names_found.intersection({"driving_policy.onnx", "driving_on_policy.onnx"}):
      raise FileNotFoundError(f"No policy ONNX found at {ref}")
  return found


def extract_model(model_id: str, source: dict, repo: Path, workspace: Path) -> dict:
  ref = source["ref"]
  input_format = source["input_format"]
  uses_external_gpu = source.get("uses_external_gpu", False)
  ensure_git_ref(repo, ref)
  output_dir = workspace / "onnx" / model_id
  output_dir.mkdir(parents=True, exist_ok=True)
  extracted = []

  paths_to_extract = find_model_paths(repo, ref, input_format, uses_external_gpu)
  for git_path, standard_name in paths_to_extract.items():
    destination = output_dir / f"{model_id}_{standard_name}"
    extract_git_file(repo, ref, git_path, destination)
    extracted.append({
      "component": standard_name,
      "git_path": git_path,
      "path": str(destination),
      "size": destination.stat().st_size,
      "sha256": sha256_file(destination),
    })
  result = {
    "id": model_id,
    "ref": ref,
    "input_format": input_format,
    "uses_external_gpu": uses_external_gpu,
    "files": extracted,
  }
  (workspace / "results" / f"{model_id}_source.json").write_text(json.dumps(result, indent=2) + "\n")
  return result


def remote(command: str, *, capture: bool = False):
  result = subprocess.run(
    ["ssh", *SSH_OPTIONS, REMOTE, command],
    check=False,
    text=capture,
    capture_output=capture,
  )
  if result.returncode != 0:
    detail = result.stderr.strip() if capture and result.stderr else f"exit {result.returncode}"
    raise RuntimeError(f"Remote command failed: {detail}")
  return result


def stage_ready_artifact(artifact: Path, workspace: Path) -> None:
  ready_path = workspace / "ready-for-resources" / artifact.name
  multipart_outputs = split_oversized_artifact(artifact, ready_path.parent)
  if multipart_outputs:
    ready_path.unlink(missing_ok=True)
    for multipart_output in multipart_outputs:
      multipart_output.chmod(0o644)
  else:
    shutil.copyfile(artifact, ready_path)
    ready_path.chmod(0o644)


def pull_remote_artifact(remote_output: str, local_output: Path) -> None:
  """Pull either a single artifact or the compiler's repository-safe parts."""
  local_output.unlink(missing_ok=True)
  for stale in local_output.parent.glob(f"{local_output.name}.p[0-9][0-9]"):
    stale.unlink()
  local_output.parent.joinpath(f"{local_output.name}.sha256").unlink(missing_ok=True)
  local_output.parent.mkdir(parents=True, exist_ok=True)
  run(["rsync", "-az", "-e", "ssh -o ConnectTimeout=10 -o ConnectionAttempts=1", f"{REMOTE}:{remote_output}*", f"{local_output.parent}/"])

  parts = sorted(local_output.parent.glob(f"{local_output.name}.p[0-9][0-9]"))
  if local_output.is_file():
    for part in parts:
      part.unlink()
    local_output.parent.joinpath(f"{local_output.name}.sha256").unlink(missing_ok=True)
    return
  checksum_path = local_output.parent / f"{local_output.name}.sha256"
  if not parts or not checksum_path.is_file():
    raise FileNotFoundError(f"Remote compiler returned neither {local_output.name} nor verified parts")
  with open(local_output, "wb") as destination:
    for part in parts:
      with open(part, "rb") as source:
        shutil.copyfileobj(source, destination, length=1024 * 1024)
  expected = checksum_path.read_text().split()[0]
  actual = sha256_file(local_output)
  if actual != expected:
    local_output.unlink(missing_ok=True)
    raise ValueError(f"Reassembled {local_output.name} checksum mismatch: {actual} != {expected}")
  for part in parts:
    part.unlink()
  checksum_path.unlink()


def compile_model(model_id: str, source: dict, version: str, workspace: Path, force: bool) -> dict:
  local_output = workspace / "compiled" / f"{model_id}_driving_tinygrad.pkl"
  if local_output.is_file() and not force:
    stage_ready_artifact(local_output, workspace)
    return artifact_result(model_id, local_output, "skipped")

  source_dir = workspace / "onnx" / model_id
  if not source_dir.is_dir():
    raise FileNotFoundError(f"Extract sources first: {source_dir}")
  remote_input = f"{REMOTE_ROOT}/uncompiledmodels/{model_id}"
  remote_output = f"{REMOTE_ROOT}/compiledmodels/{model_id}_driving_tinygrad.pkl"
  remote(f"rm -rf {remote_input} && mkdir -p {remote_input} {REMOTE_ROOT}/compiledmodels")
  run(["rsync", "-az", "-e", "ssh -o ConnectTimeout=10 -o ConnectionAttempts=1", "--exclude=._*", f"{source_dir}/", f"{REMOTE}:{remote_input}/"])

  log_path = workspace / "logs" / f"{model_id}.log"
  command_parts = [
    f"cd {REMOTE_ROOT} && ./models --model {model_id}",
    f"--input-dir {remote_input} --output-dir {REMOTE_ROOT}/compiledmodels",
    f"--input-format {source['input_format']} --version {version}",
  ]
  if source.get("uses_external_gpu"):
    command_parts.append("--external-gpu")
  command = " ".join(command_parts)
  with open(log_path, "wb") as log_file:
    process = subprocess.run(["ssh", *SSH_OPTIONS, REMOTE, command], stdout=log_file, stderr=subprocess.STDOUT)
  if process.returncode != 0:
    raise RuntimeError(f"Compilation failed for {model_id}; see {log_path}")

  pull_remote_artifact(remote_output, local_output)
  local_output.chmod(0o644)
  stage_ready_artifact(local_output, workspace)
  result = artifact_result(model_id, local_output, "compiled")
  (workspace / "results" / f"{model_id}_artifact.json").write_text(json.dumps(result, indent=2) + "\n")
  return result


def artifact_result(model_id: str, path: Path, status: str) -> dict:
  return {
    "id": model_id,
    "status": status,
    "path": str(path),
    "size": path.stat().st_size,
    "sha256": sha256_file(path),
    "multipart": path.stat().st_size > REPOSITORY_FILE_LIMIT,
  }


def validate_model(model_id: str, version: str, workspace: Path) -> dict:
  artifact = workspace / "compiled" / f"{model_id}_driving_tinygrad.pkl"
  if not artifact.is_file():
    raise FileNotFoundError(artifact)
  run(["rsync", "-az", "-e", "ssh -o ConnectTimeout=10 -o ConnectionAttempts=1", str(artifact), f"{REMOTE}:/data/models/{artifact.name}"])
  run([
    "rsync",
    "-az",
    "-e", "ssh -o ConnectTimeout=10 -o ConnectionAttempts=1",
    str(REPO_ROOT / "scripts/validate_model_artifact.py"),
    f"{REMOTE}:{REMOTE_ROOT}/scripts/validate_model_artifact.py",
  ])
  result = remote(
    f"cd {REMOTE_ROOT} && /usr/local/venv/bin/python3 scripts/validate_model_artifact.py "
    f"--model {model_id} --version {version}",
    capture=True,
  )
  payload = json.loads(result.stdout.strip().splitlines()[-1])
  (workspace / "results" / f"{model_id}_validation.json").write_text(
    json.dumps(payload, indent=2) + "\n",
  )
  return payload


def update_manifest(base_manifest: Path, workspace: Path, source_map: dict) -> dict:
  payload = load_json(base_manifest)
  models = payload["models"] if isinstance(payload, dict) else payload
  if not any(model.get("id") == "deeprl3v2" for model in models):
    models.append({
      "id": "deeprl3v2",
      "name": "Deep RL 3 V2 👀📡",
      "version": "v15",
      "series": "OP Series",
      "released": "2026-06-17",
      "community_favorite": False,
    })
  multipart_handoff = []
  for model in models:
    source = source_map.get(model["id"], {})
    if "uses_external_gpu" in source:
      model["uses_external_gpu"] = bool(source["uses_external_gpu"])
    artifact = workspace / "compiled" / f"{model['id']}_driving_tinygrad.pkl"
    model.pop("artifact_format", None)
    model.pop("artifact_size", None)
    model.pop("artifact_sha256", None)
    model.pop("artifact_urls", None)
    if not artifact.is_file() or artifact.stat().st_size <= REPOSITORY_FILE_LIMIT:
      model.pop("artifact_url", None)
    else:
      multipart_handoff.append({
        "id": model["id"],
        "filename": artifact.name,
        "size": artifact.stat().st_size,
        "sha256": sha256_file(artifact),
        "parts": [
          path.name
          for path in sorted((workspace / "ready-for-resources").glob(f"{artifact.name}.p[0-9][0-9]"))
        ],
      })
  output = {"models": models}
  output_path = workspace / "manifests/model_names_v22.json"
  output_path.parent.mkdir(parents=True, exist_ok=True)
  output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
  (workspace / "ready-for-resources" / "multipart.json").write_text(
    json.dumps(multipart_handoff, indent=2) + "\n",
  )
  return output


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("command", choices=("init", "extract", "compile", "validate", "manifest"))
  parser.add_argument("--model")
  parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
  parser.add_argument("--openpilot", type=Path, default=DEFAULT_OPENPILOT)
  parser.add_argument("--source-map", type=Path, default=DEFAULT_SOURCE_MAP)
  parser.add_argument("--base-manifest", type=Path)
  parser.add_argument("--force", action="store_true")
  args = parser.parse_args()

  ensure_workspace(args.workspace)
  source_map = load_json(args.source_map)
  if args.command == "init":
    shutil.copyfile(args.source_map, args.workspace / "source-maps" / args.source_map.name)
    shutil.copyfile(Path(__file__), args.workspace / "scripts" / Path(__file__).name)
    return 0
  if args.command == "manifest":
    if args.base_manifest is None:
      parser.error("--base-manifest is required")
    update_manifest(args.base_manifest, args.workspace, source_map)
    return 0

  model_ids = [args.model] if args.model else list(source_map)
  versions = {}
  if args.base_manifest:
    base = load_json(args.base_manifest)
    versions = {model["id"]: model["version"] for model in base.get("models", base)}
  versions.setdefault("deeprl3v2", "v15")

  for model_id in model_ids:
    if model_id not in source_map:
      raise KeyError(f"Unknown model ID: {model_id}")
    try:
      if args.command == "extract":
        result = extract_model(model_id, source_map[model_id], args.openpilot, args.workspace)
      elif args.command == "compile":
        result = compile_model(model_id, source_map[model_id], versions.get(model_id, ""), args.workspace, args.force)
      else:
        result = validate_model(model_id, versions.get(model_id, ""), args.workspace)
      (args.workspace / "results" / f"{model_id}_failure.json").unlink(missing_ok=True)
      print(json.dumps(result), flush=True)
    except Exception as error:
      failure = {"id": model_id, "status": "failed", "error": str(error)}
      (args.workspace / "results" / f"{model_id}_failure.json").write_text(json.dumps(failure, indent=2) + "\n")
      print(json.dumps(failure), file=sys.stderr, flush=True)
      if args.model:
        raise
  failures = [
    args.workspace / "results" / f"{model_id}_failure.json"
    for model_id in model_ids
    if (args.workspace / "results" / f"{model_id}_failure.json").is_file()
  ]
  return 1 if failures else 0


if __name__ == "__main__":
  raise SystemExit(main())
