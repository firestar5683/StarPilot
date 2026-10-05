import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from openpilot.common.vendor_manifest import DEPENDENCIES, MANIFEST, validate_worktree
from tools.vendor.sync import sync


class TestSourceSync(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    self.source = self.root / "upstream"
    self.repo = self.root / "project"
    for folder in (self.source, self.repo):
      folder.mkdir()
      self.git(folder, "init", "--quiet")
      self.git(folder, "config", "user.name", "Test")
      self.git(folder, "config", "user.email", "test@example.invalid")
      self.git(folder, "config", "commit.gpgsign", "false")
      self.git(folder, "config", "core.hooksPath", "/dev/null")
    for name in ("local.txt", "upstream.txt", "remove.txt", "local_delete.txt"):
      (self.source / name).write_text("base\n")
    (self.source / "shared.txt").write_text("".join(f"line {i}\n" for i in range(20)))
    (self.source / "data.bin").write_bytes(b"\0\x01base\xff")
    (self.source / "run.sh").write_text("#!/bin/sh\nexit 0\n")
    (self.source / "link").symlink_to("local.txt")
    (self.source / "AGENTS.md").write_text("Excluded upstream metadata\n")
    self.base = self.commit(self.source)
    self.base_tree = self.git(self.source, "rev-parse", "HEAD^{tree}").strip().decode()

    shutil.copytree(self.source, self.repo / "panda", symlinks=True, ignore=shutil.ignore_patterns(".git", "AGENTS.md"))
    for dependency in DEPENDENCIES - {"panda"}:
      (self.repo / dependency).mkdir()
      (self.repo / dependency / "source.py").write_text("# fixture\n")
    self.manifest = {
      "schema_version": 1,
      "upstream": {"url": "https://example.invalid/main.git", "commit": self.base},
      "dependencies": [
        {"path": name, "url": f"https://example.invalid/{name}.git", "commit": self.base,
         "tree": self.base_tree, "exclude": ["AGENTS.md"] if name == "panda" else []}
        for name in sorted(DEPENDENCIES)
      ],
    }
    self.write_manifest()
    self.commit(self.repo)

  def git(self, repo: Path, *args: str, data: bytes | None = None) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args], input=data, stderr=subprocess.PIPE)

  def commit(self, repo: Path) -> str:
    self.git(repo, "add", "--all")
    self.git(repo, "commit", "--quiet", "-m", "fixture")
    return self.git(repo, "rev-parse", "HEAD").strip().decode()

  def write_manifest(self):
    (self.repo / MANIFEST).write_text(json.dumps(self.manifest, indent=2) + "\n")

  def snapshot(self) -> tuple:
    files = {}
    for file in self.repo.rglob("*"):
      relative = file.relative_to(self.repo)
      if relative.parts[0] == ".git":
        continue
      if file.is_symlink():
        files[str(relative)] = ("link", os.readlink(file))
      elif file.is_file():
        files[str(relative)] = (file.stat().st_mode & 0o777, file.read_bytes())
    return (self.git(self.repo, "rev-parse", "HEAD"),
            self.git(self.repo, "ls-files", "--stage", "-z"),
            self.git(self.repo, "status", "--porcelain=v1", "--untracked-files=all"), files)

  def update(self, *, apply: bool = True) -> dict:
    target = self.git(self.source, "rev-parse", "HEAD").strip().decode()
    return sync(self.repo, "panda", target, self.source, apply=apply)

  def test_preview_and_apply_preserve_local_edits(self):
    (self.repo / "panda/local.txt").write_text("local customization\n")
    shared = self.repo / "panda/shared.txt"
    shared.write_text(shared.read_text().replace("line 1\n", "local line\n"))
    old_head = self.commit(self.repo)
    (self.source / "upstream.txt").write_text("upstream improvement\n")
    shared = self.source / "shared.txt"
    shared.write_text(shared.read_text().replace("line 18\n", "upstream line\n"))
    target = self.commit(self.source)

    before = self.snapshot()
    preview = self.update(apply=False)
    self.assertEqual(self.snapshot(), before)
    self.assertFalse(preview["applied"])
    self.assertEqual(set(preview["changed_files"]), {"shared.txt", "upstream.txt"})
    applied = self.update()
    self.assertTrue(applied["applied"])
    self.assertEqual((self.repo / "panda/local.txt").read_text(), "local customization\n")
    self.assertEqual((self.repo / "panda/upstream.txt").read_text(), "upstream improvement\n")
    merged = (self.repo / "panda/shared.txt").read_text()
    self.assertIn("local line\n", merged)
    self.assertIn("upstream line\n", merged)
    self.assertEqual(self.git(self.repo, "rev-parse", "HEAD").strip().decode(), old_head)
    self.assertEqual(self.git(self.repo, "diff", "--name-only"), b"")
    entry = next(e for e in validate_worktree(self.repo)["dependencies"] if e["path"] == "panda")
    self.assertEqual(entry["commit"], target)
    self.assertEqual(entry["tree"], self.git(self.source, "rev-parse", "HEAD^{tree}").strip().decode())

  def test_extension_sync_preserves_manifest_groups_and_local_edits(self):
    entry = next(item for item in self.manifest['dependencies'] if item['path'] == 'jetlink_repo')
    self.manifest['dependencies'].remove(entry)
    self.manifest['vendored_extensions'] = [entry]
    entry['exclude'] = ['AGENTS.md']
    self.write_manifest()
    # Give the extension the same real pinned upstream base as the ordinary fixture.
    shutil.rmtree(self.repo / 'jetlink_repo')
    shutil.copytree(self.repo / 'panda', self.repo / 'jetlink_repo', symlinks=True)
    (self.repo / 'jetlink_repo/local.txt').write_text('local extension customization\n')
    self.commit(self.repo)
    original_dependencies = json.loads(json.dumps(self.manifest['dependencies']))
    (self.source / 'upstream.txt').write_text('extension upstream update\n')
    target = self.commit(self.source)
    before = self.snapshot()
    preview = sync(self.repo, 'jetlink_repo', target, self.source, apply=False)
    self.assertFalse(preview['applied'])
    self.assertEqual(self.snapshot(), before)
    sync(self.repo, 'jetlink_repo', target, self.source, apply=True)
    manifest = validate_worktree(self.repo)
    self.assertEqual(manifest['dependencies'], original_dependencies)
    self.assertEqual(len(manifest['vendored_extensions']), 1)
    self.assertEqual(manifest['vendored_extensions'][0]['commit'], target)
    self.assertEqual(manifest['vendored_extensions'][0]['tree'],
                     self.git(self.source, 'rev-parse', 'HEAD^{tree}').strip().decode())
    self.assertEqual((self.repo / 'jetlink_repo/local.txt').read_text(), 'local extension customization\n')
    self.assertEqual((self.repo / 'jetlink_repo/upstream.txt').read_text(), 'extension upstream update\n')
    self.assertEqual(self.git(self.repo, 'diff', '--name-only'), b'')

  def test_conflict_leaves_worktree_index_and_manifest_unchanged(self):
    (self.repo / "panda/local.txt").write_text("local side\n")
    self.commit(self.repo)
    (self.source / "local.txt").write_text("upstream side\n")
    self.commit(self.source)
    before = self.snapshot()
    with self.assertRaisesRegex(ValueError, "conflicts with local changes"):
      self.update()
    self.assertEqual(self.snapshot(), before)

  def test_binary_modes_symlink_and_deletions(self):
    (self.repo / "panda/local_delete.txt").unlink()
    self.commit(self.repo)
    blob = b"\0\xffincoming\x80\n"
    (self.source / "data.bin").write_bytes(blob)
    (self.source / "run.sh").chmod(0o755)
    (self.source / "link").unlink()
    (self.source / "link").symlink_to("upstream.txt")
    (self.source / "remove.txt").unlink()
    (self.source / "new name.txt").write_text("new file\n")
    self.commit(self.source)
    self.update()
    self.assertEqual((self.repo / "panda/data.bin").read_bytes(), blob)
    self.assertTrue(os.access(self.repo / "panda/run.sh", os.X_OK))
    self.assertTrue(self.git(self.repo, "ls-files", "--stage", "panda/run.sh").startswith(b"100755"))
    self.assertEqual(os.readlink(self.repo / "panda/link"), "upstream.txt")
    self.assertFalse((self.repo / "panda/remove.txt").exists())
    self.assertFalse((self.repo / "panda/local_delete.txt").exists())
    self.assertEqual((self.repo / "panda/new name.txt").read_text(), "new file\n")

  def test_declared_metadata_exclusion_applies_to_new_snapshot(self):
    (self.source / "AGENTS.md").write_text("Changed excluded metadata\n")
    target = self.commit(self.source)
    result = self.update()
    self.assertEqual(result["changed_files"], [])
    self.assertFalse((self.repo / "panda/AGENTS.md").exists())
    self.assertEqual(set(self.git(self.repo, "diff", "--cached", "--name-only").decode().splitlines()), {MANIFEST})
    entry = next(e for e in validate_worktree(self.repo)["dependencies"] if e["path"] == "panda")
    self.assertEqual(entry["commit"], target)
    self.assertEqual(entry["exclude"], ["AGENTS.md"])

  def test_worktree_sources_and_successive_updates(self):
    (self.repo / "panda/local.txt").write_text("persistent local change\n")
    self.commit(self.repo)
    (self.source / "upstream.txt").write_text("first upstream change\n")
    self.commit(self.source)
    for attr in ("repo", "source"):
      original = getattr(self, attr)
      worktree = self.root / f"{attr}-worktree"
      self.git(original, "worktree", "add", "--quiet", "--detach", str(worktree), "HEAD")
      setattr(self, attr, worktree)
    self.assertTrue((self.repo / ".git").is_file())
    self.assertTrue((self.source / ".git").is_file())
    self.update()
    self.commit(self.repo)
    (self.source / "upstream.txt").write_text("second upstream change\n")
    self.commit(self.source)
    self.update()
    self.assertEqual((self.repo / "panda/local.txt").read_text(), "persistent local change\n")
    self.assertEqual((self.repo / "panda/upstream.txt").read_text(), "second upstream change\n")

  def test_preview_reports_exact_filenames(self):
    names = {"name with spaces.txt", "name\twith\ttabs.txt", "name\nwith\nnewlines.txt", "caf\N{LATIN SMALL LETTER E WITH ACUTE}.txt"}
    for name in names:
      (self.source / name).write_text("new source\n")
    self.commit(self.source)
    before = self.snapshot()
    self.assertEqual(set(self.update(apply=False)["changed_files"]), names)
    self.assertEqual(self.snapshot(), before)

  def test_non_commit_target_and_abbreviated_hash_are_rejected(self):
    for target in (self.base[:12], self.base_tree):
      with self.subTest(target=target):
        before = self.snapshot()
        with self.assertRaises((ValueError, subprocess.CalledProcessError)):
          sync(self.repo, "panda", target, self.source, apply=True)
        self.assertEqual(self.snapshot(), before)

  def test_dirty_worktree_index_and_untracked_files_are_rejected(self):
    for dirty_kind in ("unstaged", "staged", "untracked"):
      with self.subTest(kind=dirty_kind):
        changed = self.repo / ("new.txt" if dirty_kind == "untracked" else "panda/local.txt")
        original = changed.read_bytes() if changed.exists() else None
        changed.write_text("uncommitted\n")
        if dirty_kind == "staged":
          self.git(self.repo, "add", "--", str(changed))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "working tree changes"):
          self.update()
        self.assertEqual(self.snapshot(), before)
        if original is None:
          changed.unlink()
        else:
          changed.write_bytes(original)
          self.git(self.repo, "add", "--", str(changed))

  def test_invalid_baseline_hash_is_rejected_without_mutation(self):
    entry = next(e for e in self.manifest["dependencies"] if e["path"] == "panda")
    entry["tree"] = "0" * 40
    self.write_manifest()
    self.commit(self.repo)
    before = self.snapshot()
    with self.assertRaisesRegex(ValueError, "base tree does not match"):
      self.update()
    self.assertEqual(self.snapshot(), before)

  def test_upstream_gitlinks_and_undeclared_metadata_are_rejected(self):
    for metadata in ("gitlink", "nested/AGENTS.md", ".gitmodules"):
      with self.subTest(metadata=metadata):
        self.git(self.source, "reset", "--hard", self.base)
        if metadata == "gitlink":
          self.git(self.source, "update-index", "--add", "--cacheinfo", f"160000,{self.base},nested")
          self.git(self.source, "commit", "--quiet", "-m", "gitlink fixture")
        else:
          file = self.source / metadata
          file.parent.mkdir(parents=True, exist_ok=True)
          file.write_text("metadata\n")
          self.commit(self.source)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "unsupported metadata"):
          self.update()
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
  unittest.main()
