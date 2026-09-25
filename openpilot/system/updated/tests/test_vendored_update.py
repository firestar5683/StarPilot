"""Updater Git integration against temporary local repositories.

Native Params, logging, hardware, and consistency syncing are explicit test doubles.
Git fetch/checkout/reset/clean and finalization copies run against real temporary
repositories. No device paths, mounts, firmware calls, or network remotes are used.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch


from openpilot.common.vendor_manifest import DEPENDENCIES

BRANCH = "test-vendored"


class MemoryParams:
  def __init__(self):
    self.values = {"UpdaterTargetBranch": BRANCH}

  def get(self, key):
    return self.values.get(key)

  def put(self, key, value, **kwargs):
    self.values[key] = value

  put_bool = put


def load_updater():
  """Load unchanged updater code with explicit service boundaries substituted."""
  services = {
    "openpilot.common.params": {"Params": MemoryParams},
    "openpilot.common.time_helpers": {"system_time_valid": Mock()},
    "openpilot.common.markdown": {"parse_markdown": Mock()},
    "openpilot.common.swaglog": {"cloudlog": Mock()},
    "openpilot.selfdrive.selfdrived.alertmanager": {"set_offroad_alert": Mock()},
    "openpilot.common.hardware": {"AGNOS": False, "HARDWARE": Mock()},
    "openpilot.starpilot.drive_state.evidence": {"PhysicalSource": Mock()},
    "openpilot.common.version": {"get_build_metadata": Mock()},
  }
  modules = {}
  for name, attributes in services.items():
    module = ModuleType(name)
    module.__dict__.update(attributes)
    modules[name] = module
  path = Path(__file__).resolve().parents[1] / "updated.py"
  spec = importlib.util.spec_from_file_location("updater_git_test", path)
  assert spec is not None and spec.loader is not None
  updated = importlib.util.module_from_spec(spec)
  with patch.dict(sys.modules, modules):
    spec.loader.exec_module(updated)
  return updated


class TestVendoredUpdate(unittest.TestCase):
  def setUp(self):
    self.temporary = tempfile.TemporaryDirectory()
    self.addCleanup(self.temporary.cleanup)
    self.root = Path(self.temporary.name)
    self.source = self.root / "source"
    self.merged = self.root / "merged"
    self.finalized = self.root / "finalized"
    self.source.mkdir()
    self.env_patch = patch.dict(os.environ, {
      "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
      "GIT_AUTHOR_NAME": "Updater test", "GIT_COMMITTER_NAME": "Updater test",
      "GIT_AUTHOR_EMAIL": "updater@example.invalid", "GIT_COMMITTER_EMAIL": "updater@example.invalid",
    })
    self.env_patch.start()
    self.addCleanup(self.env_patch.stop)
    self.git(self.source, "init", "-b", BRANCH)
    for name in DEPENDENCIES:
      folder = self.source / name
      folder.mkdir()
      (folder / "README.md").write_text(f"{name} tracked source\n")
    self.manifest = {
      "schema_version": 1,
      "upstream": {"url": "https://github.com/commaai/openpilot.git", "commit": "1" * 40},
      "dependencies": [
        {"path": name, "url": f"https://github.com/commaai/{name}.git", "commit": "2" * 40, "tree": "3" * 40, "exclude": []}
        for name in DEPENDENCIES
      ],
    }
    self.write_manifest()
    self.initial_commit = self.commit_source("Initial vendored tree")
    self.git(self.root, "clone", "--no-local", "--no-hardlinks", str(self.source), str(self.merged))
    # Simulate inherited Git settings that would otherwise recurse on fetch/reset.
    self.git(self.merged, "config", "submodule.recurse", "true")
    self.git(self.merged, "config", "fetch.recurseSubmodules", "true")

    self.updated = load_updater()
    self.updated.OVERLAY_MERGED = str(self.merged)
    self.updated.FINALIZED = str(self.finalized)
    self.updated.BASEDIR = str(self.merged)
    self.updated.set_consistent_flag = self.set_consistent_flag
    self.updated.handle_agnos_update = Mock()
    self.commands = []
    real_run = self.updated.run

    def bounded_run(command, cwd=None):
      if cwd is None:
        raise AssertionError("Every updater command must name its isolated working directory")
      self.assertTrue(Path(cwd).resolve().is_relative_to(self.root.resolve()))
      self.assertNotEqual(command[:2], ["git", "submodule"])
      self.commands.append(command)
      if command in (["git", "gc"], ["git", "lfs", "prune"]):
        return ""
      return real_run(command, cwd)

    self.updated.run = bounded_run
    self.updater = self.updated.Updater()

  @staticmethod
  def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.STDOUT, text=True).strip()

  def write_manifest(self):
    (self.source / "upstream-sync.json").write_text(json.dumps(self.manifest))

  def commit_source(self, message):
    self.git(self.source, "add", "--all")
    self.git(self.source, "commit", "-m", message)
    return self.git(self.source, "rev-parse", "HEAD")

  def set_consistent_flag(self, consistent):
    marker = self.finalized / ".overlay_consistent"
    if consistent:
      marker.touch()
    else:
      marker.unlink(missing_ok=True)

  def assert_rejected_before_checkout(self):
    self.updated.AGNOS = True
    with self.assertRaises(ValueError):
      self.updater.fetch_update()
    self.assertEqual(self.git(self.merged, "rev-parse", "HEAD"), self.initial_commit)
    self.assertFalse(any(command[:2] == ["git", "checkout"] for command in self.commands))
    self.assertFalse((self.finalized / ".overlay_consistent").exists())
    self.updated.handle_agnos_update.assert_not_called()
    self.assertFalse(self.updater.params.values["UpdateAvailable"])

  def test_automatic_update_uses_fast_path_and_only_falls_back_on_incompatibility(self):
    fast_update = importlib.import_module("openpilot.starpilot.software.fast_update")
    for error in (None, self.updated.FastUpdateIncompatible("AGNOS changed"), self.updated.FastUpdateError("Tracked edits")):
      with self.subTest(error=error), patch.object(fast_update, "fast_update", side_effect=error, return_value="reboot-requested"), \
           patch.object(self.updater, "normal_update", return_value="reboot-requested") as normal:
        if error is not None and not isinstance(error, self.updated.FastUpdateIncompatible):
          with self.assertRaises(self.updated.FastUpdateError):
            self.updater.fast_update(BRANCH, self.initial_commit, automatic=True)
        else:
          self.assertEqual(self.updater.fast_update(BRANCH, self.initial_commit, automatic=True), "reboot-requested")
        self.assertEqual(normal.call_count, int(isinstance(error, self.updated.FastUpdateIncompatible)))
    with patch.object(fast_update, "fast_update", side_effect=self.updated.FastUpdateIncompatible("AGNOS changed")), \
         patch.object(self.updater, "normal_update") as normal:
      with self.assertRaises(self.updated.FastUpdateIncompatible):
        self.updater.fast_update(BRANCH, self.initial_commit)
      normal.assert_not_called()  # Explicit fast/rollback/version operations keep their contract.

  def test_normal_fallback_stages_flashes_and_requests_reboot_with_fresh_parked_state(self):
    installed = self.root / "installed"
    self.git(self.root, "clone", "--no-local", str(self.merged), str(installed))
    self.updated.BASEDIR = str(installed)
    (self.source / "panda/README.md").write_text("New native revision")
    target = self.commit_source("Full update")
    self.updated.AGNOS = True
    progress = Mock()
    with patch.object(self.updated, "init_overlay"):
      self.assertEqual(self.updater.normal_update(BRANCH, self.initial_commit, lambda: True, progress), "reboot-requested")
    self.updated.handle_agnos_update.assert_called_once()
    self.assertEqual(self.git(installed, "rev-parse", "HEAD"), self.initial_commit)
    self.assertEqual(self.git(self.finalized, "rev-parse", "HEAD"), target)
    self.assertTrue(self.updater.params.values["DoReboot"])
    self.assertTrue(self.updater.params.values["UpdateAvailable"])
    progress.assert_called_with("rebooting", "Update installed. Restarting device.")

  def test_normal_fallback_never_reboots_after_parked_authority_is_lost(self):
    installed = self.root / "installed"
    self.git(self.root, "clone", "--no-local", str(self.merged), str(installed))
    self.updated.BASEDIR = str(installed)
    (self.source / "panda/README.md").write_text("New native revision")
    self.commit_source("Full update")
    parked = iter((True, False))
    with patch.object(self.updated, "init_overlay"), self.assertRaises(self.updated.FastUpdateError):
      self.updater.normal_update(BRANCH, self.initial_commit, lambda: next(parked), Mock())
    self.assertNotIn("DoReboot", self.updater.params.values)

  def test_check_reports_confirmed_os_requirement_without_changing_installed_files(self):
    self.updated.AGNOS = True
    self.updated.HARDWARE.get_os_version.return_value = "12"
    for launch, required in (("export AGNOS_VERSION='12'\n", False), ("export AGNOS_VERSION='13'\n", True),
                             ("# Unknown OS version\n", None)):
      with self.subTest(launch=launch):
        (self.source / "launch_env.sh").write_text(launch)
        self.commit_source("Change target OS version")
        self.updater.check_for_update()
        expected = {} if required is None else {"branch": BRANCH, "required": required}
        self.assertEqual(self.updater.params.values["UpdaterOSUpdate"], expected)
        self.assertEqual(self.git(self.merged, "rev-parse", "HEAD"), self.initial_commit)
        self.updated.handle_agnos_update.assert_not_called()

  def test_vendored_fetch_and_finalize(self):
    (self.source / "panda" / "README.md").write_text("Updated ordinary tracked source\n")
    target = self.commit_source("Update dependency source atomically")
    self.updater.fetch_update()
    self.assertEqual(self.git(self.merged, "rev-parse", "HEAD"), target)
    self.assertEqual(self.git(self.finalized, "rev-parse", "HEAD"), target)
    self.assertEqual((self.finalized / "panda" / "README.md").read_text(), "Updated ordinary tracked source\n")
    self.assertTrue((self.finalized / ".overlay_consistent").is_file())
    for name in DEPENDENCIES:
      self.assertFalse((self.finalized / name / ".git").exists())
    self.assertFalse(any(line.startswith("160000 ") for line in self.git(self.finalized, "ls-tree", "-r", "HEAD").splitlines()))
    self.assertEqual(self.git(self.merged, "config", "submodule.recurse"), "false")
    self.assertEqual(self.git(self.merged, "config", "fetch.recurseSubmodules"), "false")
    self.updated.handle_agnos_update.assert_not_called()

  def test_invalid_manifest_rejected_before_checkout(self):
    self.manifest["schema_version"] = 999
    self.write_manifest()
    self.commit_source("Unsupported manifest")
    self.assert_rejected_before_checkout()

  def test_missing_manifest_rejected_before_checkout(self):
    (self.source / "upstream-sync.json").unlink()
    self.commit_source("Missing manifest")
    self.assert_rejected_before_checkout()

  def test_malformed_manifest_rejected_before_checkout(self):
    (self.source / "upstream-sync.json").write_text("{invalid JSON")
    self.commit_source("Malformed manifest")
    self.assert_rejected_before_checkout()

  def test_missing_dependency_rejected_before_checkout(self):
    shutil.rmtree(self.source / "panda")
    self.commit_source("Missing ordinary dependency folder")
    self.assert_rejected_before_checkout()

  def test_gitlink_rejected_before_checkout(self):
    self.git(self.source, "rm", "-r", "panda")
    self.git(self.source, "update-index", "--add", "--cacheinfo", f"160000,{self.initial_commit},panda")
    self.git(self.source, "commit", "-m", "Invalid gitlink dependency")
    self.assert_rejected_before_checkout()

  def test_gitmodules_rejected_before_checkout(self):
    (self.source / ".gitmodules").write_text('[submodule "panda"]\npath = panda\nurl = https://example.invalid/panda\n')
    self.commit_source("Invalid submodule configuration")
    self.assert_rejected_before_checkout()

  def test_finalize_invalid_tree_clears_existing_readiness(self):
    self.finalized.mkdir()
    (self.finalized / ".overlay_consistent").touch()
    self.manifest["dependencies"] = []
    self.write_manifest()
    self.commit_source("Invalid empty dependency manifest")
    shutil.rmtree(self.merged)
    self.git(self.root, "clone", "--no-local", "--no-hardlinks", str(self.source), str(self.merged))
    with self.assertRaises(ValueError):
      self.updated.finalize_update()
    self.assertFalse((self.finalized / ".overlay_consistent").exists())


if __name__ == "__main__":
  unittest.main()
