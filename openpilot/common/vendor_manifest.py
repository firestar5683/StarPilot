"""Validate the source layout without loading native modules or device state."""

import json
import re
import subprocess
import os
import stat
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

MANIFEST = "upstream-sync.json"
BASE_DEPENDENCIES = frozenset({"msgq_repo", "opendbc_repo", "panda", "rednose_repo", "teleoprtc_repo", "tinygrad_repo", "mapd_repo"})
EXTENSIONS = frozenset({"jetlink_repo"})
DEPENDENCIES = BASE_DEPENDENCIES | EXTENSIONS
SHA = re.compile(r"[0-9a-f]{40}\Z")


def git(repo: Path | str, *args: str) -> bytes:
  return subprocess.check_output(["git", "-C", str(repo), *args])


def dependency_entries(manifest: dict) -> list[dict]:
  return [*manifest["dependencies"], *manifest.get("vendored_extensions", [])]


def parse_manifest(data: bytes | str) -> dict:
  try:
    value = json.loads(data)
  except (ValueError, UnicodeError) as e:
    raise ValueError("Invalid source manifest JSON") from e
  if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
    raise ValueError("Unsupported source manifest schema")
  upstream = value.get("upstream")
  dependencies = value.get("dependencies")
  extensions = value.get("vendored_extensions", [])
  if not isinstance(upstream, dict) or not isinstance(dependencies, list) or not isinstance(extensions, list):
    raise ValueError("Source manifest must define upstream and dependencies")
  entries = dependency_entries(value)
  paths = []
  for entry in [upstream, *entries]:
    if not isinstance(entry, dict):
      raise ValueError("Invalid source manifest entry")
    if not isinstance(entry.get("commit"), str) or not SHA.fullmatch(entry["commit"]):
      raise ValueError("Source revisions must be full commit hashes")
    url = entry.get("url")
    if not isinstance(url, str) or not url.startswith("https://") or not urlsplit(url).hostname or urlsplit(url).username:
      raise ValueError("Source URLs must use HTTPS")
  for entry in extensions:
    if not isinstance(entry.get("path"), str) or entry["path"] not in EXTENSIONS:
      raise ValueError("Unexpected vendored extension path")
  for entry in entries:
    path = entry.get("path")
    if not isinstance(path, str) or path not in DEPENDENCIES:
      raise ValueError(f"Unexpected dependency path: {path!r}")
    paths.append(path)
    if not isinstance(entry.get("tree"), str) or not SHA.fullmatch(entry["tree"]):
      raise ValueError(f"Missing pristine upstream tree for {path}")
    excluded = entry.get("exclude")
    if not isinstance(excluded, list) or not all(isinstance(name, str) for name in excluded) or len(set(excluded)) != len(excluded):
      raise ValueError(f"Invalid exclusions for {path}")
    for name in excluded:
      invalid_name = not name or name == "." or "\0" in name or name != PurePosixPath(name).as_posix()
      if invalid_name or any(p in ("..", ".git") for p in PurePosixPath(name).parts) or name.startswith("/"):
        raise ValueError(f"Unsafe exclusion for {path}")
  if len(paths) != len(set(paths)) or not BASE_DEPENDENCIES <= set(paths):
    raise ValueError("Source manifest must list each dependency exactly once")
  return value


def tree_entries(repo: Path | str, revision: str) -> dict[str, str]:
  revision = git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}").decode().strip()
  entries = {}
  for record in git(repo, "ls-tree", "-rz", "--full-tree", revision).split(b"\0"):
    if record:
      meta, name = record.split(b"\t", 1)
      entries[name.decode()] = meta.split()[0].decode()
  return entries


def validate_layout(manifest: dict, entries: dict[str, str]) -> None:
  for path, mode in entries.items():
    if mode == "160000":
      raise ValueError(f"Source tree contains a gitlink: {path}")
    if PurePosixPath(path).name.lower() in (".gitmodules", "agents.md"):
      raise ValueError(f"Source tree contains excluded metadata: {path}")
  if entries.get(MANIFEST) != "100644":
    raise ValueError("Source manifest must be a tracked regular file")
  dependencies = dependency_entries(manifest)
  declared = {entry["path"] for entry in dependencies}
  for extension in EXTENSIONS - declared:
    if extension in entries or any(name.startswith(extension + "/") for name in entries):
      raise ValueError(f"Missing source provenance for {extension}")
  for dependency in dependencies:
    path = dependency["path"]
    members = [name for name in entries if name.startswith(path + "/")]
    if path in entries or not members:
      raise ValueError(f"Missing tracked dependency folder: {path}")
    for excluded in dependency["exclude"]:
      prefix = f"{path}/{excluded}"
      if any(name == prefix or name.startswith(prefix + "/") for name in members):
        raise ValueError(f"Excluded dependency content is tracked: {prefix}")


def validate_revision(repo: Path | str, revision: str) -> dict:
  revision = git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}").decode().strip()
  entries = tree_entries(repo, revision)
  if entries.get(MANIFEST) != "100644":
    raise ValueError("Source manifest must be a tracked regular file")
  manifest = parse_manifest(git(repo, "show", f"{revision}:{MANIFEST}"))
  validate_layout(manifest, entries)
  return manifest


def validate_worktree(repo: Path | str) -> dict:
  repo = Path(repo)
  if (repo / MANIFEST).is_symlink() or not (repo / MANIFEST).is_file():
    raise ValueError("Source manifest must be a regular file")
  manifest = parse_manifest((repo / MANIFEST).read_bytes())
  entries = {}
  for record in git(repo, "ls-files", "--stage", "-z").split(b"\0"):
    if not record:
      continue
    meta, name = record.split(b"\t", 1)
    mode, _, stage = meta.split()
    if stage != b"0":
      raise ValueError(f"Unresolved source conflict: {name.decode()}")
    entries[name.decode()] = mode.decode()
  validate_layout(manifest, entries)
  for dependency in dependency_entries(manifest):
    folder = repo / dependency["path"]
    if not folder.is_dir() or folder.is_symlink():
      raise ValueError(f"Dependency must be an ordinary folder: {folder.name}")
    for current, directories, files in os.walk(folder, followlinks=False):
      if ".git" in directories or ".git" in files:
        raise ValueError(f"Nested Git metadata in dependency: {current}")
    for name, mode in entries.items():
      if name.startswith(folder.name + "/"):
        file = repo / name
        if not file.exists() and not file.is_symlink():
          raise ValueError(f"Missing dependency source: {name}")
        if file.is_symlink() != (mode == "120000"):
          raise ValueError(f"Dependency file type changed: {name}")
        if mode != "120000" and not stat.S_ISREG(file.lstat().st_mode):
          raise ValueError(f"Dependency source is not a regular file: {name}")
        if any(parent.is_symlink() for parent in file.parents if parent != repo and repo in parent.parents):
          raise ValueError(f"Dependency source has a symlink parent: {name}")
  return manifest
