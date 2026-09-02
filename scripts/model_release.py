#!/usr/bin/env python3
"""Release one upstream model through the device compiler and resource stores.

The command is intentionally fail-closed when the supplied upstream commits
touch tinygrad or modeld runtime code. A model source update is safe to build
only after that runtime change has been reviewed separately.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import ipaddress
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any
from pathlib import Path


OPENPILOT_REPO = "commaai/openpilot"
RESOURCES_REPO = os.environ.get("STARPILOT_RESOURCES_REPO", "firestar5683/StarPilot-Resources")
HF_BUCKET = os.environ.get("STARPILOT_HF_BUCKET", "StarPilot-Driving/StarPilot-Resources")
RESOURCE_BRANCH = "Models"
MANIFEST_VERSION = "v25"
DEFAULT_BEHAVIOR_VERSION = "v16"
DEVICE_ROOT = "/data/openpilot"
REPOSITORY_FILE_LIMIT = 100_000_000
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"
CHUNK_SUFFIX_RE = re.compile(r"\.p\d{2}$")
SHA_RE = re.compile(r"(?<![0-9a-f])([0-9a-f]{40})(?![0-9a-f])", re.IGNORECASE)
DATE_RE = re.compile(r"([A-Za-z]+\s+\d{1,2},\s+\d{4})")
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

RUNTIME_PATH_PREFIXES = (
  "tinygrad/",
  "tinygrad_repo/",
  "openpilot/tinygrad/",
  "openpilot/tinygrad_repo/",
  "selfdrive/modeld/",
  "openpilot/selfdrive/modeld/",
  "system/hardware/chestnut/",
  "openpilot/system/hardware/chestnut/",
)


class ReleaseError(RuntimeError):
  pass


@dataclass
class ReleaseInfo:
  model_id: str
  display_name: str
  release_date: str
  branch: str
  source_ref: str
  source_path: str
  input_format: str
  behavior_version: str
  uses_external_gpu: bool
  commits: list[str]
  model_iteration: str


def default_workspace() -> Path:
  t5 = Path("/Volumes/T5")
  if t5.is_dir():
    return t5 / "StarPilot-Model-Releases"
  return Path.home() / "Desktop" / "StarPilot-Model-Releases"


def run(command: list[str], *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess:
  print("$ " + " ".join(shlex.quote(part) for part in command))
  return subprocess.run(
    command,
    cwd=cwd,
    check=True,
    text=capture,
    capture_output=capture,
  )


def sha256_file(path: Path) -> str:
  digest = hashlib.sha256()
  with path.open("rb") as source:
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
      digest.update(chunk)
  return digest.hexdigest()


def http_request(url: str, *, method: str = "GET", payload: bytes | None = None, headers: dict[str, str] | None = None):
  request_headers = {"User-Agent": "StarPilot-model-release/1.0", **(headers or {})}
  token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
  if token and "api.github.com" in url:
    request_headers["Authorization"] = f"Bearer {token}"
  request = urllib.request.Request(url, data=payload, headers=request_headers, method=method)
  try:
    return urllib.request.urlopen(request, timeout=30)
  except urllib.error.HTTPError as error:
    detail = error.read(500).decode("utf-8", errors="replace")
    raise ReleaseError(f"HTTP {error.code} from {url}: {detail}") from error
  except urllib.error.URLError as error:
    raise ReleaseError(f"Unable to reach {url}: {error.reason}") from error


def get_json_value(url: str) -> Any:
  with http_request(url, headers={"Accept": "application/vnd.github+json"}) as response:
    try:
      return json.loads(response.read().decode("utf-8"))
    except json.JSONDecodeError as error:
      raise ReleaseError(f"Invalid JSON response from {url}") from error


def get_json(url: str) -> dict:
  payload = get_json_value(url)
  if not isinstance(payload, dict):
    raise ReleaseError(f"Unexpected JSON response from {url}")
  return payload


def parse_lfs_pointer(data: bytes) -> tuple[str, int] | None:
  if not data.startswith(LFS_POINTER_PREFIX):
    return None
  fields: dict[str, str] = {}
  for line in data.decode("ascii", errors="strict").splitlines():
    if " " in line:
      key, value = line.split(" ", 1)
      fields[key] = value
  oid = fields.get("oid", "").removeprefix("sha256:")
  size = fields.get("size", "")
  if not re.fullmatch(r"[0-9a-f]{64}", oid) or not size.isdigit():
    raise ReleaseError("Malformed Git LFS pointer")
  return oid, int(size)


def stream_response(response, destination: Path, prefix: bytes = b"") -> tuple[int, str]:
  digest = hashlib.sha256()
  size = 0
  with destination.open("wb") as output:
    if prefix:
      output.write(prefix)
      digest.update(prefix)
      size += len(prefix)
    for chunk in iter(lambda: response.read(1024 * 1024), b""):
      output.write(chunk)
      digest.update(chunk)
      size += len(chunk)
  return size, digest.hexdigest()


def download_lfs_object(oid: str, expected_size: int, ref: str, destination: Path) -> tuple[int, str]:
  batch_url = f"https://github.com/{OPENPILOT_REPO}.git/info/lfs/objects/batch"
  payload = json.dumps({
    "operation": "download",
    "transfers": ["basic"],
    "objects": [{"oid": oid, "size": expected_size}],
    "ref": {"name": ref},
  }).encode("utf-8")
  with http_request(
    batch_url,
    method="POST",
    payload=payload,
    headers={"Accept": "application/vnd.git-lfs+json", "Content-Type": "application/vnd.git-lfs+json"},
  ) as response:
    batch = json.loads(response.read().decode("utf-8"))

  objects = batch.get("objects", []) if isinstance(batch, dict) else []
  if not objects or "error" in objects[0]:
    raise ReleaseError(f"Git LFS download was not available for {oid}")
  action = objects[0].get("actions", {}).get("download")
  if not action or not action.get("href"):
    raise ReleaseError(f"Git LFS returned no download action for {oid}")
  headers = {str(key): str(value) for key, value in action.get("header", {}).items()}
  with http_request(action["href"], headers=headers) as response:
    size, digest = stream_response(response, destination)
  if size != expected_size or digest != oid:
    raise ReleaseError(f"LFS object verification failed: size {size}/{expected_size}, sha256 {digest}/{oid}")
  return size, digest


def download_source(ref: str, git_path: str, destination: Path, force: bool) -> dict:
  destination.parent.mkdir(parents=True, exist_ok=True)
  if destination.exists() and not force:
    raise ReleaseError(f"Source already exists: {destination}; use --force to fetch the requested commit")

  encoded_ref = urllib.parse.quote(ref, safe="/")
  encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in git_path.split("/"))
  raw_url = f"https://raw.githubusercontent.com/{OPENPILOT_REPO}/{encoded_ref}/{encoded_path}"
  temporary = destination.with_name(destination.name + ".part")
  temporary.unlink(missing_ok=True)

  with http_request(raw_url) as response:
    prefix = response.read(512)
    pointer = parse_lfs_pointer(prefix)
    if pointer is None:
      size, digest = stream_response(response, temporary, prefix)
    else:
      temporary.unlink(missing_ok=True)
      size, digest = download_lfs_object(pointer[0], pointer[1], ref, temporary)

  temporary.replace(destination)
  print(f"Downloaded source: {size} bytes, sha256 {digest}")
  return {"path": str(destination), "size": size, "sha256": digest, "url": raw_url, "ref": ref, "git_path": git_path}


def clean_markdown(value: str) -> str:
  value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", value)
  value = re.sub(r"[*_`]+", "", value)
  return " ".join(value.split()).strip()


def slug_model_id(name: str) -> str:
  tokens = re.findall(r"[a-z0-9]+", name.lower())
  return "".join(tokens)


def parse_release_date(text: str) -> str | None:
  match = DATE_RE.search(text)
  if not match:
    return None
  for fmt in ("%B %d, %Y", "%b %d, %Y"):
    try:
      return dt.datetime.strptime(match.group(1), fmt).date().isoformat()
    except ValueError:
      continue
  return None


def commit_local_date(payload: dict) -> str:
  commit_data = payload.get("commit", {})
  for author_key in ("committer", "author"):
    timestamp = commit_data.get(author_key, {}).get("date") if isinstance(commit_data, dict) else None
    if not timestamp:
      continue
    try:
      return dt.datetime.fromisoformat(str(timestamp).replace("Z", "+00:00")).astimezone().date().isoformat()
    except ValueError:
      continue
  return dt.date.today().isoformat()


def source_name_from_path(source_path: str) -> str:
  stem = Path(source_path).stem
  stem = re.sub(r"^(?:big_)?driving_supercombo$", "", stem, flags=re.IGNORECASE)
  stem = re.sub(r"_driving_(?:supercombo|vision|policy)$", "", stem, flags=re.IGNORECASE)
  stem = stem.strip("_-")
  return stem.replace("_", " ").replace("-", " ").title() or "Model"


def select_model_source(files: list[Any], commit: str) -> str:
  paths = [
    str(item.get("filename", ""))
    for item in files
    if isinstance(item, dict) and str(item.get("filename", "")).lower().endswith(".onnx")
  ]
  preferred = [path for path in paths if Path(path).name.lower().endswith("driving_supercombo.onnx")]
  candidates = preferred or paths
  if len(candidates) != 1:
    if not candidates:
      raise ReleaseError(f"Commit {commit} does not change a driving ONNX file")
    raise ReleaseError(f"Commit {commit} changes multiple ONNX files; provide the full bot message to disambiguate")
  return candidates[0]


def resolve_commit_release(commit: str, model_id_override: str | None, behavior_version: str) -> ReleaseInfo:
  commit_payload = get_json(f"https://api.github.com/repos/{OPENPILOT_REPO}/commits/{commit}")
  files = commit_payload.get("files", [])
  if not isinstance(files, list):
    raise ReleaseError(f"GitHub returned no file list for commit {commit}")
  source_path = select_model_source(files, commit)

  branch = ""
  display_name = ""
  pulls = get_json_value(f"https://api.github.com/repos/{OPENPILOT_REPO}/commits/{commit}/pulls")
  if isinstance(pulls, list):
    for pull in pulls:
      if not isinstance(pull, dict):
        continue
      head = pull.get("head", {})
      if isinstance(head, dict) and str(head.get("sha", "")).lower() == commit:
        branch = str(head.get("ref") or "")
        display_name = clean_markdown(str(pull.get("title") or ""))
        break

  if not branch:
    branches = get_json_value(
      f"https://api.github.com/repos/{OPENPILOT_REPO}/commits/{commit}/branches-where-head"
    )
    if isinstance(branches, list):
      names = [str(item.get("name")) for item in branches if isinstance(item, dict) and item.get("name")]
      branch = next((name for name in names if name.lower() != "master"), names[0] if names else "")
  branch = branch or commit

  if not display_name or display_name.lower() in {"big", "model", "update model"}:
    display_name = source_name_from_path(source_path)
  model_id = model_id_override or slug_model_id(display_name)
  if not MODEL_ID_RE.fullmatch(model_id):
    raise ReleaseError(f"Invalid model ID {model_id!r}; use lowercase letters, digits, '-' or '_'")
  uses_external_gpu = Path(source_path).name.lower().startswith("big_")
  model_iteration_match = re.search(r"\b(v\d+)\b", display_name, flags=re.IGNORECASE)
  return ReleaseInfo(
    model_id=model_id,
    display_name=display_name,
    release_date=commit_local_date(commit_payload),
    branch=branch,
    source_ref=commit,
    source_path=source_path,
    input_format="supercombo" if "supercombo" in Path(source_path).name else "split",
    behavior_version=behavior_version,
    uses_external_gpu=uses_external_gpu,
    commits=[commit],
    model_iteration=model_iteration_match.group(1).lower() if model_iteration_match else "",
  )


def parse_pasted_release(text: str, model_id_override: str | None, behavior_version: str) -> ReleaseInfo:
  cleaned_text = text.replace("\\u00a0", " ")
  commits = list(dict.fromkeys(match.lower() for match in SHA_RE.findall(cleaned_text)))
  if re.fullmatch(r"\s*[0-9a-f]{40}\s*", cleaned_text, flags=re.IGNORECASE):
    return resolve_commit_release(commits[0], model_id_override, behavior_version)

  source_match = re.search(
    r"https?://github\.com/commaai/openpilot/(?:blob|raw)/([^/\s]+)/([^\s)\]]+)",
    cleaned_text,
    flags=re.IGNORECASE,
  )
  if source_match:
    branch = urllib.parse.unquote(source_match.group(1))
    source_path = urllib.parse.unquote(source_match.group(2)).rstrip(".,")
  else:
    branch_match = re.search(r"\[([^]]+)\]\s*\(Branch\s+v?\d+\)", cleaned_text, flags=re.IGNORECASE)
    branch = clean_markdown(branch_match.group(1)) if branch_match else ""
    family_match = re.search(r"\[([a-z0-9_-]+)\]\s*\(Branch", cleaned_text, flags=re.IGNORECASE)
    family = family_match.group(1).lower() if family_match else ""
    source_path = f"openpilot/selfdrive/modeld/models/{family}_driving_supercombo.onnx" if family else ""

  if not branch:
    raise ReleaseError("Could not parse the openpilot branch from the pasted release block")
  if not source_path or not source_path.endswith(".onnx"):
    raise ReleaseError("Could not parse the upstream ONNX path from the pasted release block")

  name = ""
  release_date = None
  for line in cleaned_text.splitlines():
    plain = clean_markdown(line)
    date_match = DATE_RE.search(plain)
    if date_match:
      candidate = plain[:date_match.start()].strip(" :-(\t")
      candidate = re.sub(r"^(?:model name|name)\s*[:=-]?\s*", "", candidate, flags=re.IGNORECASE)
      if candidate and "next model version" not in candidate.lower():
        name = candidate
        release_date = parse_release_date(plain)
        break
  if not name:
    family_match = re.search(r"\[([a-z0-9_-]+)\]\s*\(Branch", cleaned_text, flags=re.IGNORECASE)
    name = family_match.group(1).replace("-", " ").title() if family_match else Path(source_path).stem
    release_date = dt.date.today().isoformat()
  release_date = release_date or dt.date.today().isoformat()

  iteration_match = re.search(r"\b(v\d+)\b", name, flags=re.IGNORECASE)
  model_iteration = iteration_match.group(1).lower() if iteration_match else ""
  model_id = model_id_override or slug_model_id(name)
  if not MODEL_ID_RE.fullmatch(model_id):
    raise ReleaseError(f"Invalid model ID {model_id!r}; use lowercase letters, digits, '-' or '_'")

  uses_external_gpu = bool(
    re.search(r"\[big\]|\bbig[_ -]model\b", cleaned_text, flags=re.IGNORECASE)
    or Path(source_path).name.startswith("big_")
  )
  source_ref = commits[0] if commits else branch
  input_format = "supercombo" if "supercombo" in Path(source_path).name else "split"
  return ReleaseInfo(
    model_id=model_id,
    display_name=name,
    release_date=release_date,
    branch=branch,
    source_ref=source_ref,
    source_path=source_path,
    input_format=input_format,
    behavior_version=behavior_version,
    uses_external_gpu=uses_external_gpu,
    commits=commits,
    model_iteration=model_iteration,
  )


def resolve_branch_commit(branch: str) -> str:
  url = f"https://api.github.com/repos/{OPENPILOT_REPO}/commits/{urllib.parse.quote(branch, safe='')}"
  payload = get_json(url)
  sha = str(payload.get("sha") or "")
  if not SHA_RE.fullmatch(sha):
    raise ReleaseError(f"Could not resolve branch head for {branch}")
  return sha


def runtime_file(path: str) -> bool:
  normalized = path.lstrip("./")
  if normalized.lower().endswith(".onnx"):
    return False
  return normalized.startswith(RUNTIME_PATH_PREFIXES)


def scan_runtime_changes(info: ReleaseInfo) -> list[dict]:
  commits = info.commits or [resolve_branch_commit(info.branch)]
  findings: list[dict] = []
  for commit in commits:
    url = f"https://api.github.com/repos/{OPENPILOT_REPO}/commits/{commit}"
    payload = get_json(url)
    files = payload.get("files", [])
    if not isinstance(files, list):
      raise ReleaseError(f"GitHub returned no file list for commit {commit}")
    changed = [str(item.get("filename", "")) for item in files if isinstance(item, dict)]
    runtime_paths = [path for path in changed if runtime_file(path)]
    if runtime_paths:
      findings.append({"commit": commit, "message": str(payload.get("commit", {}).get("message", "")).splitlines()[0], "paths": runtime_paths})
  return findings


def print_summary(info: ReleaseInfo) -> None:
  print("\nRelease summary")
  print(f"  model ID:       {info.model_id}")
  print(f"  display name:   {info.display_name}")
  print(f"  release date:   {info.release_date}")
  print(f"  behavior:       {info.behavior_version}")
  print(f"  source ref:     {info.source_ref}")
  print(f"  source path:    {info.source_path}")
  print(f"  input format:   {info.input_format}")
  print(f"  external GPU:   {info.uses_external_gpu}")


def print_runtime_warning(findings: list[dict]) -> None:
  print("\n" + "!" * 88)
  print("STOP: UPSTREAM TINYGRAD/MODELD RUNTIME CHANGES DETECTED")
  print("Ask Firestar to review these changes before compiling this model.")
  for finding in findings:
    print(f"  {finding['commit'][:12]} {finding['message']}")
    for path in finding["paths"]:
      print(f"    - {path}")
  print("The release tool will not compile until --allow-runtime-changes is supplied.")
  print("!" * 88 + "\n")


def choose_device_ip(args: argparse.Namespace) -> str:
  if args.ip:
    value = args.ip.strip()
  elif sys.stdin.isatty():
    value = input("Comma IP [192.168.3.110]: ").strip() or "192.168.3.110"
  else:
    raise ReleaseError("Pass --ip when the release text is piped on stdin")
  try:
    address = ipaddress.ip_address(value)
  except ValueError as error:
    raise ReleaseError(f"Invalid comma IP: {value}") from error
  if str(address).split(".")[-1] == "109":
    raise ReleaseError("Refusing to use .109. This workflow is restricted to the requested device, not 192.168.3.109.")
  return str(address)


def ssh_base(ip: str) -> list[str]:
  return ["ssh", "-o", "ConnectTimeout=10", "-o", "ConnectionAttempts=1", "-o", "ServerAliveInterval=30", f"comma@{ip}"]


def scp_base(ip: str) -> list[str]:
  return ["scp", "-p", "-o", "ConnectTimeout=10", "-o", "ConnectionAttempts=1"]


def remote_compile(info: ReleaseInfo, source: Path, ip: str, workspace: Path, keep_device_files: bool) -> dict:
  if info.input_format != "supercombo":
    raise ReleaseError("The release tool currently requires a single supercombo ONNX source")

  input_dir = f"{DEVICE_ROOT}/uncompiledmodels"
  output_dir = f"{DEVICE_ROOT}/compiledmodels"
  remote_source = f"{input_dir}/{info.model_id}_driving_supercombo.onnx"
  artifact_prefix = f"{info.model_id}_driving_tinygrad.pkl"
  safe_id = shlex.quote(info.model_id)
  cleanup_command = f"rm -f {shlex.quote(remote_source)} {shlex.quote(output_dir)}/{artifact_prefix}*"
  run(ssh_base(ip) + [f"mkdir -p {shlex.quote(input_dir)} {shlex.quote(output_dir)} && {cleanup_command}"])
  run(scp_base(ip) + [str(source), f"comma@{ip}:{remote_source}"])

  command = [
    f"cd {shlex.quote(DEVICE_ROOT)} && ./models",
    f"--model {safe_id}",
    f"--input-dir {shlex.quote(input_dir)}",
    f"--output-dir {shlex.quote(output_dir)}",
    f"--input-format supercombo",
    f"--version {shlex.quote(info.behavior_version)}",
  ]
  if info.uses_external_gpu:
    command.append("--gpu")
  remote_command = " ".join(command)
  log_path = workspace / "logs" / f"{info.model_id}.log"
  log_path.parent.mkdir(parents=True, exist_ok=True)
  print(f"\nCompiling on comma@{ip}. Output is also logged to {log_path}")
  with log_path.open("w", encoding="utf-8") as log:
    process = subprocess.Popen(
      ssh_base(ip) + [remote_command],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      text=True,
      bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
      print(f"[device] {line}", end="")
      log.write(line)
    return_code = process.wait()
  if return_code != 0:
    raise ReleaseError(f"Device compilation failed; see {log_path}")

  list_command = f"for f in {shlex.quote(output_dir)}/{artifact_prefix}*; do [ -f \"$f\" ] && basename \"$f\"; done"
  listed = run(ssh_base(ip) + [list_command], capture=True).stdout.splitlines()
  remote_files = sorted(name for name in listed if name.startswith(artifact_prefix))
  if not remote_files:
    raise ReleaseError(f"Device compiler produced no {artifact_prefix} output")

  artifact_dir = workspace / "compiled" / info.model_id
  artifact_dir.mkdir(parents=True, exist_ok=True)
  for stale in artifact_dir.iterdir():
    if stale.is_file():
      stale.unlink()
  for filename in remote_files:
    run(scp_base(ip) + [f"comma@{ip}:{output_dir}/{filename}", str(artifact_dir / filename)])

  parts = sorted(artifact_dir.glob(f"{artifact_prefix}.p[0-9][0-9]"))
  full_artifact = artifact_dir / artifact_prefix
  checksum_path = artifact_dir / f"{artifact_prefix}.sha256"
  if parts:
    if full_artifact.exists() or not checksum_path.is_file():
      raise ReleaseError("Device returned invalid multipart output")
    expected = checksum_path.read_text(encoding="utf-8").split()[0].lower()
    digest = hashlib.sha256()
    size = 0
    for part in parts:
      with part.open("rb") as source_part:
        for chunk in iter(lambda: source_part.read(1024 * 1024), b""):
          digest.update(chunk)
          size += len(chunk)
    actual = digest.hexdigest()
    if actual != expected:
      raise ReleaseError(f"Multipart checksum mismatch: {actual} != {expected}")
    artifact_files = [*parts, checksum_path]
  elif full_artifact.is_file():
    size = full_artifact.stat().st_size
    actual = sha256_file(full_artifact)
    artifact_files = [full_artifact]
    expected = actual
  else:
    raise ReleaseError("Device returned no usable artifact")

  if not keep_device_files:
    run(ssh_base(ip) + [cleanup_command])
  result = {
    "id": info.model_id,
    "status": "compiled",
    "size": size,
    "sha256": expected,
    "multipart": bool(parts),
    "files": [path.name for path in artifact_files],
    "path": str(artifact_dir),
  }
  (workspace / "results").mkdir(parents=True, exist_ok=True)
  (workspace / "results" / f"{info.model_id}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
  return result


def manifest_entry(info: ReleaseInfo, result: dict) -> dict:
  display_name = info.display_name
  if "👀" not in display_name and "📡" not in display_name:
    display_name += " 👀📡"
  return {
    "id": info.model_id,
    "name": display_name,
    "version": info.behavior_version,
    "series": "OP Series",
    "released": info.release_date,
    "community_favorite": False,
    "artifact_format": "tinygrad_single_v1",
    "artifact_size": result["size"],
    "artifact_sha256": result["sha256"],
    "uses_external_gpu": info.uses_external_gpu,
  }


def update_manifest(repo: Path, info: ReleaseInfo, result: dict, manifest_version: str) -> Path:
  path = repo / f"model_names_{manifest_version}.json"
  if not path.is_file():
    raise ReleaseError(f"Manifest not found: {path}")
  payload = json.loads(path.read_text(encoding="utf-8"))
  models = payload.get("models", payload) if isinstance(payload, dict) else payload
  if not isinstance(models, list):
    raise ReleaseError(f"Unsupported manifest shape: {path}")
  entry = manifest_entry(info, result)
  replaced = False
  updated = []
  for model in models:
    if isinstance(model, dict) and model.get("id") == info.model_id:
      updated.append(entry)
      replaced = True
    else:
      updated.append(model)
  if not replaced:
    updated.append(entry)
  output = {**payload, "models": updated} if isinstance(payload, dict) else {"models": updated}
  path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  return path


def find_hf() -> str:
  candidates = [shutil.which("hf"), str(Path.home() / ".local/bin/hf")]
  for candidate in candidates:
    if candidate and Path(candidate).is_file():
      return candidate
  raise ReleaseError("Hugging Face CLI not found; install/authenticate `hf` first")


def hf_copy(source: Path, bucket: str, remote_path: str) -> None:
  hf = find_hf()
  destination = f"hf://buckets/{bucket}/{remote_path}"
  run([hf, "buckets", "cp", str(source), destination, "--format", "quiet"])


def upload_huggingface(info: ReleaseInfo, result: dict, workspace: Path, bucket: str, manifest: Path, upload_onnx: bool, source: Path) -> None:
  artifact_dir = Path(result["path"])
  for filename in result["files"]:
    hf_copy(artifact_dir / filename, bucket, f"models/{info.model_id}/{filename}")
  if upload_onnx:
    hf_copy(source, bucket, f"onnx/{info.model_id}/{source.name}")
  hf_copy(manifest, bucket, f"manifests/{manifest.name}")
  print(f"Hugging Face upload complete: {bucket}/models/{info.model_id}/")


def git_output(repo: Path, args: list[str]) -> str:
  return run(["git", "-C", str(repo), *args], capture=True).stdout.strip()


def check_resources_repo(repo: Path, branch: str) -> None:
  if not (repo / ".git").exists():
    raise ReleaseError(f"GitHub resources checkout not found: {repo}")
  status = git_output(repo, ["status", "--porcelain"])
  if status:
    raise ReleaseError(f"Resources checkout is dirty; refusing to modify it:\n{status}")
  current_branch = git_output(repo, ["branch", "--show-current"])
  if current_branch != branch:
    raise ReleaseError(f"Resources checkout is on {current_branch!r}, expected {branch!r}")
  remote_head = git_output(repo, ["rev-parse", f"origin/{branch}"])
  local_head = git_output(repo, ["rev-parse", "HEAD"])
  if remote_head != local_head:
    raise ReleaseError("Resources checkout has unpushed or missing remote commits; sync it before releasing")


def push_github(info: ReleaseInfo, result: dict, resources_repo: Path, manifest: Path, branch: str, force: bool) -> None:
  artifact_dir = Path(result["path"])
  artifact_names = list(result["files"])
  destination_paths = []
  stale_relative: list[str] = []
  for filename in artifact_names:
    destination = resources_repo / filename
    if destination.exists() and not force:
      raise ReleaseError(f"Artifact already exists in GitHub checkout: {destination}; use --force to replace it")
    shutil.copy2(artifact_dir / filename, destination)
    destination_paths.append(destination)

  prefix = f"{info.model_id}_driving_tinygrad.pkl"
  if force:
    allowed = {path.name for path in destination_paths}
    for stale in resources_repo.glob(f"{prefix}*"):
      if stale.name not in allowed and stale.is_file():
        stale.unlink()
        stale_relative.append(str(stale.relative_to(resources_repo)))

  for index, destination in enumerate(destination_paths):
    relative = destination.relative_to(resources_repo)
    paths_to_stage = [str(relative)]
    if index == 0:
      paths_to_stage.extend(stale_relative)
    run(["git", "-C", str(resources_repo), "add", "-A", "--", *paths_to_stage])
    run(["git", "-C", str(resources_repo), "commit", "-m", f"Add {info.model_id} artifact {destination.name}", "--", *paths_to_stage])
    run(["git", "-C", str(resources_repo), "push", "origin", f"HEAD:{branch}"])

  run(["git", "-C", str(resources_repo), "add", "--", str(manifest.relative_to(resources_repo))])
  if git_output(resources_repo, ["diff", "--cached", "--name-only"]):
    run(["git", "-C", str(resources_repo), "commit", "-m", f"Add {info.display_name} to {manifest.name}", "--", str(manifest.relative_to(resources_repo))])
    run(["git", "-C", str(resources_repo), "push", "origin", f"HEAD:{branch}"])
  print(f"GitHub upload complete: {RESOURCES_REPO}/{branch}")


def read_release_text(args: argparse.Namespace) -> str:
  if args.commit:
    return args.commit
  if args.text_file:
    return args.text_file.read_text(encoding="utf-8")
  if args.text:
    return args.text
  if not sys.stdin.isatty():
    return sys.stdin.read()
  print("Paste the model bot message. Press Ctrl-D when finished.")
  return sys.stdin.read()


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Download, device-compile, verify, and publish one upstream model.")
  parser.add_argument("commit", nargs="?", help="A single openpilot commit SHA; metadata is resolved from GitHub.")
  parser.add_argument("--text", help="Release text, otherwise paste it into stdin.")
  parser.add_argument("--text-file", type=Path, help="Read the pasted release text from a file.")
  parser.add_argument("--model-id", help="Override the ID parsed from the model name.")
  parser.add_argument("--behavior-version", default=DEFAULT_BEHAVIOR_VERSION, help="Runtime behavior version (default: v16).")
  parser.add_argument("--ip", help="Comma IP; prompted interactively when omitted.")
  parser.add_argument("--workspace", type=Path, default=default_workspace())
  parser.add_argument("--resources-repo", type=Path, default=Path.home() / "StarPilot-Resources")
  parser.add_argument("--resources-branch", default=RESOURCE_BRANCH)
  parser.add_argument("--manifest-version", default=MANIFEST_VERSION)
  parser.add_argument("--hf-bucket", default=HF_BUCKET)
  gpu = parser.add_mutually_exclusive_group()
  gpu.add_argument("--gpu", dest="gpu", action="store_true", help="Force external-GPU compilation.")
  gpu.add_argument("--no-gpu", dest="gpu", action="store_false", help="Disable external-GPU compilation.")
  parser.set_defaults(gpu=None)
  parser.add_argument("--allow-runtime-changes", action="store_true", help="Continue only after reviewing the runtime-change warning.")
  parser.add_argument("--no-onnx-upload", action="store_true", help="Do not archive the source ONNX in Hugging Face.")
  parser.add_argument("--keep-device-files", action="store_true", help="Leave the staged source and compiled output on the comma.")
  parser.add_argument("--force", action="store_true", help="Replace an existing source/artifact/model ID.")
  parser.add_argument("--dry-run", action="store_true", help="Parse and scan only; do not download, compile, or publish.")
  return parser.parse_args()


def main() -> int:
  args = parse_args()
  try:
    if not re.fullmatch(r"v\d+", args.behavior_version.strip(), flags=re.IGNORECASE):
      raise ReleaseError("--behavior-version must look like v16")
    text = read_release_text(args)
    if not text.strip():
      raise ReleaseError("No release text was supplied")
    info = parse_pasted_release(text, args.model_id, args.behavior_version.strip().lower())
    if args.gpu is not None:
      info.uses_external_gpu = args.gpu
    print_summary(info)

    findings = scan_runtime_changes(info)
    if findings:
      print_runtime_warning(findings)
      if not args.allow_runtime_changes:
        return 2
    else:
      print("Runtime scan: no tinygrad/modeld runtime files changed in the supplied commits.")

    if args.dry_run:
      print("Dry run complete; no device or repository changes made.")
      return 0

    ip = choose_device_ip(args)
    workspace = args.workspace / info.model_id
    for relative in ("onnx", "compiled", "logs", "results"):
      (workspace / relative).mkdir(parents=True, exist_ok=True)
    source = workspace / "onnx" / f"{info.model_id}_driving_supercombo.onnx"
    source_result = download_source(info.source_ref, info.source_path, source, args.force)
    (workspace / "release.txt").write_text(text, encoding="utf-8")
    (workspace / "source.json").write_text(json.dumps({**source_result, "model": info.__dict__}, indent=2) + "\n", encoding="utf-8")

    result = remote_compile(info, source, ip, workspace, args.keep_device_files)
    resources_repo = args.resources_repo.expanduser().resolve()
    check_resources_repo(resources_repo, args.resources_branch)
    manifest = update_manifest(resources_repo, info, result, args.manifest_version)
    upload_huggingface(info, result, workspace, args.hf_bucket, manifest, not args.no_onnx_upload, source)
    push_github(info, result, resources_repo, manifest, args.resources_branch, args.force)
    print("\nRelease complete.")
    print(f"  local artifact: {result['path']}")
    print(f"  Hugging Face:  {args.hf_bucket}/models/{info.model_id}/")
    print(f"  GitHub:        {RESOURCES_REPO}/{args.resources_branch}")
    return 0
  except (ReleaseError, subprocess.CalledProcessError) as error:
    print(f"ERROR: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
  raise SystemExit(main())
