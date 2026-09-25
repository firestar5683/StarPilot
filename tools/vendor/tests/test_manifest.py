"""Source-manifest validation with standard-library and temporary Git fixtures."""

import copy
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpilot.common.vendor_manifest import DEPENDENCIES, parse_manifest, validate_revision, validate_worktree


def make_manifest():
  return {
    "schema_version": 1,
    "upstream": {"url": "https://github.com/commaai/openpilot.git", "commit": "1" * 40},
    "dependencies": [
      {"path": name, "url": f"https://github.com/commaai/{name}.git", "commit": "2" * 40, "tree": "3" * 40, "exclude": []}
      for name in sorted(DEPENDENCIES)
    ],
  }


def extension_manifest():
  manifest = make_manifest()
  entry = next(item for item in manifest['dependencies'] if item['path'] == 'jetlink_repo')
  manifest['dependencies'].remove(entry)
  manifest['vendored_extensions'] = [entry]
  return manifest


class TestManifestSchema(unittest.TestCase):
  def assert_invalid(self, manifest):
    with self.assertRaises(ValueError):
      parse_manifest(json.dumps(manifest))

  def test_valid_manifest(self):
    manifest = make_manifest()
    manifest["dependencies"][-1]["exclude"] = ["AGENTS.md", "docs/generated"]
    self.assertEqual(parse_manifest(json.dumps(manifest)), manifest)

  def test_extension_and_legacy_manifest_forms(self):
    for manifest in (make_manifest(), extension_manifest()):
      self.assertEqual(parse_manifest(json.dumps(manifest)), manifest)
    legacy = extension_manifest()
    del legacy['vendored_extensions']
    self.assertEqual(parse_manifest(json.dumps(legacy)), legacy)

  def test_extensions_are_known_unique_and_fully_validated(self):
    for field, value in (('path', 'unknown_repo'), ('path', 'panda'), ('commit', 'short'),
                         ('tree', 'short'), ('url', 'http://example.com'), ('exclude', ['../escape'])):
      with self.subTest(field=field, value=value):
        manifest = extension_manifest()
        manifest['vendored_extensions'][0][field] = value
        self.assert_invalid(manifest)
    for entries in (None, {}, 'jetlink_repo'):
      manifest = extension_manifest()
      manifest['vendored_extensions'] = entries
      self.assert_invalid(manifest)
    manifest = extension_manifest()
    manifest['vendored_extensions'] *= 2
    self.assert_invalid(manifest)
    manifest = extension_manifest()
    manifest['dependencies'].append(copy.deepcopy(manifest['vendored_extensions'][0]))
    self.assert_invalid(manifest)

  def test_malformed_json_and_non_objects(self):
    for raw in ("", "{", b"\xff", "null", "true", "[]", '"manifest"', "1"):
      with self.subTest(raw=raw), self.assertRaises(ValueError):
        parse_manifest(raw)

  def test_schema_is_integer_version_one(self):
    for version in (None, True, False, 1.0, 0, 2, "1", [], {}):
      with self.subTest(version=version):
        manifest = make_manifest()
        manifest["schema_version"] = version
        self.assert_invalid(manifest)

  def test_invalid_source_urls(self):
    for url in (None, [], "", "https://", "https:///repo", "http://example.com/repo", "file:///repo", "git@example.com:repo"):
      for field in ("upstream", "dependency"):
        with self.subTest(url=url, field=field):
          manifest = make_manifest()
          entry = manifest["upstream"] if field == "upstream" else manifest["dependencies"][0]
          entry["url"] = url
          self.assert_invalid(manifest)

  def test_invalid_revision_and_tree_identifiers(self):
    for sha in (None, [], "", "a" * 39, "a" * 41, "G" * 40, "A" * 40, "master"):
      for field in ("upstream", "dependency", "tree"):
        with self.subTest(sha=sha, field=field):
          manifest = make_manifest()
          entry = manifest["upstream"] if field == "upstream" else manifest["dependencies"][0]
          entry["tree" if field == "tree" else "commit"] = sha
          self.assert_invalid(manifest)

  def test_dependencies_are_complete_unique_and_known(self):
    manifest = make_manifest()
    variants = [None, {}, [], manifest["dependencies"][:-1], manifest["dependencies"] + [manifest["dependencies"][0]]]
    for entries in variants:
      with self.subTest(entries=entries):
        candidate = copy.deepcopy(manifest)
        candidate["dependencies"] = entries
        self.assert_invalid(candidate)
    for path in (None, [], {}, "../panda", "/panda", "panda/child", "unknown"):
      with self.subTest(path=path):
        candidate = make_manifest()
        candidate["dependencies"][0]["path"] = path
        self.assert_invalid(candidate)
    for entry in (None, [], "dependency"):
      with self.subTest(entry=entry):
        candidate = make_manifest()
        candidate["dependencies"][0] = entry
        self.assert_invalid(candidate)

  def test_exclusions_are_safe_relative_paths(self):
    for exclusion in ("", ".", "..", "../escape", "/absolute", "dir/../../escape", "./file", "dir//file", ".git", "dir/.git", "bad\0path"):
      with self.subTest(exclusion=exclusion):
        manifest = make_manifest()
        manifest["dependencies"][0]["exclude"] = [exclusion]
        self.assert_invalid(manifest)
    for excluded in (None, "AGENTS.md", [None], [[]], [{}], ["file", "file"]):
      with self.subTest(excluded=excluded):
        manifest = make_manifest()
        manifest["dependencies"][0]["exclude"] = excluded
        self.assert_invalid(manifest)


class TestManifestSourceTrees(unittest.TestCase):
  def setUp(self):
    self.temporary = tempfile.TemporaryDirectory()
    self.addCleanup(self.temporary.cleanup)
    self.root = Path(self.temporary.name)
    self.repo = self.root / "source"
    self.repo.mkdir()
    env_patch = patch.dict(os.environ, {
      "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
      "GIT_AUTHOR_NAME": "Source manifest test", "GIT_COMMITTER_NAME": "Source manifest test",
      "GIT_AUTHOR_EMAIL": "source@example.invalid", "GIT_COMMITTER_EMAIL": "source@example.invalid",
    })
    env_patch.start()
    self.addCleanup(env_patch.stop)
    self.git("init", "-b", "test-manifest")
    self.manifest = make_manifest()
    self.manifest_path = self.repo / "upstream-sync.json"
    self.write_manifest()
    for name in DEPENDENCIES:
      folder = self.repo / name
      folder.mkdir()
      (folder / "README.md").write_text("Ordinary dependency source\n")
    self.commit()

  def git(self, *args, input_text=None):
    return subprocess.run(
      ["git", "-C", str(self.repo), *args], input=input_text, check=True,
      text=True, capture_output=True,
    ).stdout.strip()

  def write_manifest(self):
    self.manifest_path.write_text(json.dumps(self.manifest))

  def commit(self):
    self.git("add", "--all")
    self.git("commit", "-m", "Source layout fixture")

  def assert_invalid_revision_and_worktree(self):
    with self.assertRaises(ValueError):
      validate_revision(self.repo, "HEAD")
    with self.assertRaises(ValueError):
      validate_worktree(self.repo)

  def use_extension(self):
    self.manifest = extension_manifest()
    self.write_manifest()
    self.commit()

  def test_extension_tree_and_missing_provenance(self):
    self.use_extension()
    self.assertEqual(validate_revision(self.repo, 'HEAD'), self.manifest)
    self.assertEqual(validate_worktree(self.repo), self.manifest)
    del self.manifest['vendored_extensions']
    self.write_manifest()
    self.commit()
    self.assert_invalid_revision_and_worktree()
    shutil.rmtree(self.repo / 'jetlink_repo')
    self.commit()
    self.assertEqual(validate_revision(self.repo, 'HEAD'), self.manifest)
    self.assertEqual(validate_worktree(self.repo), self.manifest)

  def test_extension_missing_folder_and_symlink_rejected(self):
    self.use_extension()
    folder = self.repo / 'jetlink_repo'
    external = self.root / 'external-jetlink'
    folder.rename(external)
    self.commit()
    self.assert_invalid_revision_and_worktree()
    folder.symlink_to(external, target_is_directory=True)
    self.commit()
    self.assert_invalid_revision_and_worktree()

  def test_extension_excluded_metadata_and_nested_git_rejected(self):
    self.use_extension()
    folder = self.repo / 'jetlink_repo'
    (folder / '.git').mkdir()
    with self.assertRaises(ValueError):
      validate_worktree(self.repo)
    (folder / '.git').rmdir()
    (folder / 'AGENTS.md').write_text('Excluded metadata')
    self.commit()
    self.assert_invalid_revision_and_worktree()

  def test_valid_tree_permits_local_source_edits(self):
    self.assertEqual(validate_revision(self.repo, "HEAD"), self.manifest)
    (self.repo / "panda" / "README.md").write_text("Intentional local customization\n")
    self.assertEqual(validate_worktree(self.repo), self.manifest)

  def test_missing_tracked_manifest(self):
    self.manifest_path.unlink()
    self.commit()
    with self.assertRaises(ValueError):
      validate_revision(self.repo, "HEAD")

  def test_manifest_worktree_symlink(self):
    target = self.root / "external-manifest.json"
    self.manifest_path.rename(target)
    self.manifest_path.symlink_to(target)
    with self.assertRaises(ValueError):
      validate_worktree(self.repo)

  def test_tracked_manifest_symlink(self):
    target = self.repo / "source-manifest.json"
    self.manifest_path.rename(target)
    self.manifest_path.symlink_to(target.name)
    self.commit()
    self.assert_invalid_revision_and_worktree()

  def test_missing_dependency_folder(self):
    shutil.rmtree(self.repo / "panda")
    with self.assertRaises(ValueError):
      validate_worktree(self.repo)
    self.commit()
    self.assert_invalid_revision_and_worktree()

  def test_dependency_root_symlink(self):
    folder = self.repo / "panda"
    target = self.root / "panda-outside"
    folder.rename(target)
    folder.symlink_to(target, target_is_directory=True)
    with self.assertRaises(ValueError):
      validate_worktree(self.repo)
    self.commit()
    self.assert_invalid_revision_and_worktree()

  def test_gitlink_anywhere_is_rejected(self):
    commit = self.git("rev-parse", "HEAD")
    self.git("update-index", "--add", "--cacheinfo", f"160000,{commit},panda/embedded")
    self.git("commit", "-m", "Nested gitlink fixture")
    self.assert_invalid_revision_and_worktree()

  def test_tracked_metadata_is_rejected(self):
    for name in (".gitmodules", "AGENTS.md", "nested/agents.md"):
      with self.subTest(name=name):
        path = self.repo / "panda" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Excluded metadata fixture\n")
        self.commit()
        self.assert_invalid_revision_and_worktree()
        path.unlink()
        self.commit()

  def test_nested_git_metadata_is_rejected(self):
    for relative in (".git", "nested/.git"):
      for kind in ("file", "directory", "broken_symlink"):
        with self.subTest(relative=relative, kind=kind):
          path = self.repo / "panda" / relative
          path.parent.mkdir(parents=True, exist_ok=True)
          if kind == "file":
            path.write_text("gitdir: /does-not-exist\n")
          elif kind == "directory":
            path.mkdir()
          else:
            path.symlink_to("does-not-exist")
          try:
            with self.assertRaises(ValueError):
              validate_worktree(self.repo)
          finally:
            if path.is_dir() and not path.is_symlink():
              path.rmdir()
            else:
              path.unlink()

  def test_missing_tracked_source(self):
    (self.repo / "panda" / "README.md").unlink()
    with self.assertRaises(ValueError):
      validate_worktree(self.repo)

  def test_regular_file_replaced_by_directory(self):
    file = self.repo / "panda" / "README.md"
    file.unlink()
    file.mkdir()
    with self.assertRaises(ValueError):
      validate_worktree(self.repo)

  def test_regular_file_replaced_by_symlink(self):
    file = self.repo / "panda" / "README.md"
    file.unlink()
    file.symlink_to("../msgq_repo/README.md")
    with self.assertRaises(ValueError):
      validate_worktree(self.repo)

  def test_intermediate_directory_symlink_is_rejected(self):
    folder = self.repo / "panda" / "nested"
    folder.mkdir()
    (folder / "source.py").write_text("SOURCE = 1\n")
    self.commit()
    target = self.root / "external-source"
    folder.rename(target)
    folder.symlink_to(target, target_is_directory=True)
    with self.assertRaises(ValueError):
      validate_worktree(self.repo)

  def test_tracked_leaf_symlink_is_preserved(self):
    link = self.repo / "panda" / "linked-readme"
    link.symlink_to("README.md")
    self.commit()
    self.assertEqual(validate_revision(self.repo, "HEAD"), self.manifest)
    self.assertEqual(validate_worktree(self.repo), self.manifest)
    link.unlink()
    link.write_text("Unexpected regular file\n")
    with self.assertRaises(ValueError):
      validate_worktree(self.repo)

  def test_unresolved_index_is_rejected(self):
    blob = self.git("rev-parse", "HEAD:panda/README.md")
    self.git("update-index", "--force-remove", "panda/README.md")
    self.git("update-index", "--index-info", input_text=f"100644 {blob} 2\tpanda/README.md\n100644 {blob} 3\tpanda/README.md\n")
    with self.assertRaises(ValueError):
      validate_worktree(self.repo)

  def test_excluded_file_and_directory_are_not_tracked(self):
    entry = next(entry for entry in self.manifest["dependencies"] if entry["path"] == "panda")
    entry["exclude"] = ["private.txt", "generated"]
    self.write_manifest()
    self.commit()
    self.assertEqual(validate_revision(self.repo, "HEAD"), self.manifest)
    for name in ("private.txt", "generated/source.py"):
      with self.subTest(name=name):
        file = self.repo / "panda" / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("Excluded content\n")
        self.commit()
        self.assert_invalid_revision_and_worktree()
        file.unlink()
        self.commit()


if __name__ == "__main__":
  unittest.main()
