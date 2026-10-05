#!/usr/bin/env python3
"""Preview or stage a three-way dependency update from an explicit upstream commit."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from openpilot.common.vendor_manifest import MANIFEST, SHA, dependency_entries, git, validate_worktree


def run(repo: Path, *args: str, data: bytes | None = None) -> bytes:
  return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null", "-C", str(repo), *args], input=data)


def commit_tree(repo: Path, tree: str, parent: str | None = None) -> str:
  args = ["-c", "user.name=Source sync", "-c", "user.email=source-sync@localhost", "-c", "commit.gpgsign=false", "commit-tree", tree]
  if parent is not None:
    args += ["-p", parent]
  return run(repo, *args, data=b"Temporary source merge\n").decode().strip()


def filtered_tree(repo: Path, revision: str, excluded: list[str]) -> str:
  run(repo, "read-tree", revision)
  records = run(repo, "ls-files", "--stage", "-z").split(b"\0")
  remove = []
  for record in records:
    if not record:
      continue
    meta, path = record.split(b"\t", 1)
    name = path.decode()
    if any(name == omit or name.startswith(omit + "/") for omit in excluded):
      remove.append(path)
    elif meta.startswith(b"160000") or Path(name).name.lower() in (".gitmodules", "agents.md"):
      raise ValueError(f"Upstream snapshot contains unsupported metadata: {name}")
  if remove:
    run(repo, "update-index", "--force-remove", "-z", "--stdin", data=b"\0".join(remove) + b"\0")
  return run(repo, "write-tree").decode().strip()


def upstream_cache(entry: dict, target: str) -> Path:
  cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "starpilot-source" / entry["path"]
  cache.mkdir(parents=True, exist_ok=True)
  if not (cache / "HEAD").exists():
    run(cache, "init", "--bare", "--quiet")
  run(cache, "fetch", "--no-tags", "--no-recurse-submodules", "--depth=1", entry["url"], entry["commit"], target)
  return cache


def sync(repo: Path, dependency: str, target: str, source_repo: Path | None = None, apply: bool = False) -> dict:
  repo = repo.resolve()
  if not SHA.fullmatch(target):
    raise ValueError("Select an explicit full upstream commit hash")
  manifest = validate_worktree(repo)
  if git(repo, "status", "--porcelain=v1", "--untracked-files=all").strip():
    raise ValueError("Commit or preserve all working tree changes before syncing")
  entry = next((item for item in dependency_entries(manifest) if item["path"] == dependency), None)
  if entry is None:
    raise ValueError(f"Unknown dependency: {dependency}")
  source = source_repo.resolve() if source_repo is not None else upstream_cache(entry, target)
  if source == repo or repo in source.parents:
    raise ValueError("Upstream object cache must live outside the source checkout")
  for revision in (entry["commit"], target):
    if run(source, "rev-parse", "--verify", f"{revision}^{{commit}}").decode().strip() != revision:
      raise ValueError("Selected source object is not a commit")
  original_tree = run(source, "rev-parse", f"{entry['commit']}^{{tree}}").decode().strip()
  if original_tree != entry["tree"]:
    raise ValueError("Recorded upstream base tree does not match its commit")
  target_tree = run(source, "rev-parse", f"{target}^{{tree}}").decode().strip()
  current_tree = run(repo, "rev-parse", f"HEAD:{dependency}").decode().strip()
  current_head = run(repo, "rev-parse", "HEAD").decode().strip()
  with tempfile.TemporaryDirectory(prefix="source-merge-") as directory:
    scratch = Path(directory)
    run(scratch, "init", "--quiet")
    object_dirs = []
    for source_path in (source, repo):
      objects = Path(run(source_path, "rev-parse", "--git-path", "objects").decode().strip())
      object_dirs.append(str(objects if objects.is_absolute() else (source_path / objects).resolve()))
    (scratch / ".git/objects/info/alternates").write_text("\n".join(object_dirs) + "\n")
    base_tree = filtered_tree(scratch, entry["commit"], entry["exclude"])
    incoming_tree = filtered_tree(scratch, target, entry["exclude"])
    base = commit_tree(scratch, base_tree)
    ours = commit_tree(scratch, current_tree, base)
    theirs = commit_tree(scratch, incoming_tree, base)
    result = subprocess.run(["git", "-C", str(scratch), "merge-tree", "--write-tree", ours, theirs], capture_output=True)
    if result.returncode == 1:
      raise ValueError("Upstream update conflicts with local changes; checkout and manifest unchanged:\n" + result.stdout.decode())
    if result.returncode != 0:
      raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    merged_tree = result.stdout.splitlines()[0].decode()
    # Validate merged metadata too: local edits must not undo import exclusions.
    filtered_tree(scratch, merged_tree, [])
    patch = run(scratch, "diff", "--binary", "--no-ext-diff", "--no-textconv", "--no-renames",
                f"--src-prefix=a/{dependency}/", f"--dst-prefix=b/{dependency}/", current_tree, merged_tree)
    changed = [os.fsdecode(name) for name in run(scratch, "diff", "--name-only", "-z", current_tree, merged_tree).split(b"\0") if name]
    if apply:
      if run(repo, "rev-parse", "HEAD").decode().strip() != current_head or git(repo, "status", "--porcelain=v1", "--untracked-files=all").strip():
        raise ValueError("Source checkout changed while preparing the update")
      if patch:
        run(repo, "apply", "--check", "--index", "--binary", data=patch)
        run(repo, "apply", "--index", "--binary", "--whitespace=nowarn", data=patch)
      entry.update(commit=target, tree=target_tree)
      (repo / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
      run(repo, "add", "--", MANIFEST)
  return {"dependency": dependency, "upstream_commit": target, "changed_files": changed, "applied": apply}


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("dependency")
  parser.add_argument("commit", help="Full upstream commit hash")
  parser.add_argument("--source-repo", type=Path, help="Existing external upstream Git cache (offline operation)")
  parser.add_argument("--apply", action="store_true", help="Stage a conflict-free update; never commit or push")
  args = parser.parse_args()
  try:
    print(json.dumps(sync(ROOT, args.dependency, args.commit, args.source_repo, args.apply), indent=2))
  except (ValueError, OSError, subprocess.CalledProcessError) as e:
    print(f"Source sync failed: {e}", file=sys.stderr)
    return 1
  return 0


if __name__ == "__main__":
  sys.exit(main())
