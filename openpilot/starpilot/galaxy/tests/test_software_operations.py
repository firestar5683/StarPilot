from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from openpilot.common.params import Params
from openpilot.starpilot.galaxy.software_operations import (
  SoftwareOperations, SoftwareOperationError, UpdaterProcess, PROCESS_TITLE,
)
from openpilot.starpilot.software.update_control import UpdaterControlError


class FakeProcess:
  def __init__(self):
    self.running = True
    self.sent = []

  def available(self):
    return self.running

  def send(self, sig):
    if not self.running:
      raise SoftwareOperationError("Updater stopped", 503)
    self.sent.append(sig)

  def close(self):
    pass


class SoftwareOperationsTest(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    root = Path(self.temp.name)
    self.params = Params(str(root / "params"))
    self.params.put("Version", "test", block=True)
    self.params.put("GitBranch", "main", block=True)
    self.params.put("GitCommit", "a" * 40, block=True)
    self.params.put("UpdaterState", "idle", block=True)
    self.params.put("UpdaterTargetBranch", "main", block=True)
    self.params.put("UpdaterAvailableBranches", "main,release", block=True)
    self.params.put_bool("IsOffroad", True, block=True)
    self.params.put_bool("UpdateAvailable", False, block=True)
    self.params.put_bool("DisableUpdates", False, block=True)
    self.params.put("UpdateFailedCount", 0, block=True)
    self.process = FakeProcess()
    self.parked = True
    self.authorized = True
    self.finalized = root / "finalized"
    self.finalized.mkdir()
    self.installed = root / "installed"
    self.installed.mkdir()
    self.git = {self.installed: ("main", "a" * 40), self.finalized: ("release", "b" * 40)}
    self.owner = SoftwareOperations(self.params, parked=lambda: self.parked, process=self.process,
                                    finalized=self.finalized, installed=self.installed,
                                    git_identity=lambda path: self.git.get(path))
    self.addCleanup(self.owner.close)

  def act(self, action, branch=None):
    body = {"action": action}
    if branch is not None:
      body["branch"] = branch
    return self.owner.action(action, body, authorized=lambda: self.authorized)

  def denied(self, action, status, branch=None):
    with self.assertRaises(SoftwareOperationError) as caught:
      self.act(action, branch)
    self.assertEqual(caught.exception.status, status)

  def test_select_then_check_then_download_signals_exact_updater(self):
    self.assertTrue(self.owner.snapshot()["canSelect"])
    self.assertEqual(self.owner.snapshot()["selectedTarget"], "main")
    selected = self.act("select", "release")
    self.assertEqual(selected["selectedTarget"], "release")
    self.assertEqual(self.params.get("UpdaterTargetBranch"), "release")
    self.assertEqual(self.process.sent, [])
    checked = self.act("check")
    self.assertEqual(checked["request"]["state"], "pending")
    self.assertEqual(self.process.sent, ["check"])
    self.denied("download", 409, "release")
    self.params.put("UpdaterState", "checking...", block=True)
    self.owner.snapshot()
    self.params.put("UpdaterState", "idle", block=True)
    self.params.put("LastUpdateTime", datetime(2026, 9, 27, 12, 0), block=True)
    self.assertEqual(self.owner.snapshot()["request"]["state"], "complete")
    downloaded = self.act("download", "release")
    self.assertEqual(downloaded["request"]["target"], "release")
    self.assertEqual(self.process.sent, ["check", "download"])
    self.denied("download", 409, "release")

  def test_fresh_manager_without_target_allows_check_and_select(self):
    self.params.remove("UpdaterTargetBranch")
    initial = self.owner.snapshot()
    self.assertEqual(initial["selectedTarget"], "main")
    self.assertTrue(initial["canCheck"])
    self.assertTrue(initial["canSelect"])
    check = self.act("check")
    self.assertIsNone(check["request"]["target"])
    self.assertEqual(check["request"]["state"], "pending")
    self.params.put("UpdaterTargetBranch", "main", block=True)
    self.assertEqual(self.owner.snapshot()["request"]["state"], "pending")
    self.params.put("LastUpdateTime", datetime(2026, 9, 27, 12, 4), block=True)
    self.assertEqual(self.owner.snapshot()["request"]["state"], "complete")
    self.act("select", "release")
    self.assertEqual(self.params.get("UpdaterTargetBranch"), "release")

  def test_bad_or_stale_branch_and_missing_updater_never_mutate(self):
    self.denied("select", 400, "--help")
    self.denied("select", 409, "unknown")
    self.assertEqual(self.params.get("UpdaterTargetBranch"), "main")
    self.process.running = False
    self.denied("check", 503)
    self.assertEqual(self.process.sent, [])

  def test_parked_authority_and_session_rechecked_before_effect(self):
    for offroad, parked, authorized in ((False, True, True), (True, False, True), (True, True, False)):
      with self.subTest(offroad=offroad, parked=parked, authorized=authorized):
        self.params.put_bool("IsOffroad", offroad, block=True)
        self.parked = parked
        self.authorized = authorized
        self.denied("check", 403 if not authorized else 409)
    self.assertEqual(self.process.sent, [])
    Path(self.params.get_param_path("IsOnroad")).write_bytes(b"1")
    self.params.put_bool("IsOffroad", True, block=True)
    self.parked = self.authorized = True
    self.denied("check", 409)
    Path(self.params.get_param_path("IsOnroad")).unlink()
    self.params.put_bool("IsOffroad", True, block=True)
    self.parked = self.authorized = True
    checks = iter((True, False))
    with self.assertRaises(SoftwareOperationError):
      self.owner.action("check", {"action": "check"}, authorized=lambda: next(checks))
    self.assertEqual(self.process.sent, [])

  def test_install_requires_exact_finalized_target_and_reboot_once(self):
    self.act("select", "release")
    self.params.put_bool("UpdateAvailable", True, block=True)
    self.params.put("UpdaterNewDescription", "test / release / bbbbbbb / Sep 27", block=True)
    with mock.patch("openpilot.starpilot.galaxy.software_operations.validate_revision", return_value={}):
      self.assertFalse(self.owner.snapshot()["canInstall"])
      (self.finalized / ".overlay_consistent").touch()
      self.assertTrue(self.owner.snapshot()["canInstall"])
      self.denied("install", 409, "main")
      self.git[self.finalized] = ("release", "c" * 40)
      self.assertFalse(self.owner.snapshot()["canInstall"])
      self.denied("install", 409, "release")
      self.git[self.finalized] = ("release", "b" * 40)
      result = self.act("install", "release")
      self.assertEqual(result["request"]["state"], "pending")
      self.assertEqual(result["request"]["action"], "install")
      self.assertTrue(self.params.get_bool("DoReboot"))
      self.denied("install", 409, "release")
      self.assertEqual(self.process.sent, [])

  def test_target_change_or_failure_is_reported(self):
    self.act("select", "release")
    self.act("download", "release")
    self.params.put("UpdaterTargetBranch", "main", block=True)
    self.assertEqual(self.owner.snapshot()["request"]["state"], "failed")
    self.act("select", "release")
    self.act("check")
    self.params.put("UpdateFailedCount", 1, block=True)
    self.assertEqual(self.owner.snapshot()["request"]["state"], "failed")

  def test_counter_reset_does_not_claim_a_completed_check(self):
    self.params.put("UpdateFailedCount", 2, block=True)
    self.act("check")
    self.params.put("UpdateFailedCount", 0, block=True)
    self.assertEqual(self.owner.snapshot()["request"]["state"], "pending")
    self.params.put("LastUpdateTime", datetime(2026, 9, 27, 12, 1), block=True)
    self.assertEqual(self.owner.snapshot()["request"]["state"], "complete")

  def test_download_without_fetch_cannot_claim_unpublished_target(self):
    self.act("select", "release")
    self.act("download", "release")
    self.params.put_bool("UpdaterFetchAvailable", False, block=True)
    self.params.put("LastUpdateTime", datetime(2026, 9, 27, 12, 2), block=True)
    request = self.owner.snapshot()["request"]
    self.assertEqual(request["state"], "failed")
    self.assertIn("No new download", request["error"])

  def test_download_does_not_call_missing_remote_branch_up_to_date(self):
    self.act("download", "main")
    self.params.put_bool("UpdaterFetchAvailable", False, block=True)
    self.params.put("LastUpdateTime", datetime(2026, 9, 27, 12, 3), block=True)
    self.assertEqual(self.owner.snapshot()["request"]["state"], "failed")

  def test_catalog_keeps_other_branches_when_one_entry_is_invalid(self):
    self.params.put("UpdaterAvailableBranches", "main,feature+lab,bad branch,feature@lab", block=True)
    branches = self.owner.snapshot()["availableBranches"]
    self.assertEqual(branches, ["main", "feature+lab", "feature@lab"])
    self.act("select", "feature+lab")
    self.assertEqual(self.params.get("UpdaterTargetBranch"), "feature+lab")

  def test_published_catalog_with_more_than_64_branches_remains_usable(self):
    branches = [f"release/{number:03d}" for number in range(76)]
    self.params.put("UpdaterAvailableBranches", ",".join(branches), block=True)
    snapshot = self.owner.snapshot()
    self.assertEqual(snapshot["availableBranches"], branches)
    self.assertTrue(snapshot["canSelect"])
    self.act("select", branches[-1])
    self.assertEqual(self.params.get("UpdaterTargetBranch"), branches[-1])

  def test_slash_branch_description_can_match_finalized_commit(self):
    self.params.put("UpdaterAvailableBranches", "main,release/2026", block=True)
    self.act("select", "release/2026")
    self.git[self.finalized] = ("release/2026", "b" * 40)
    self.params.put_bool("UpdateAvailable", True, block=True)
    self.params.put("UpdaterNewDescription", "test / release/2026 / bbbbbbb / Sep 27", block=True)
    (self.finalized / ".overlay_consistent").touch()
    with mock.patch("openpilot.starpilot.galaxy.software_operations.validate_revision", return_value={}):
      self.assertTrue(self.owner.snapshot()["canInstall"])

  def save_downloads(self, enabled, expected):
    return self.owner.action('preferences', {'action': 'preferences', 'automaticDownloads': enabled,
                                             'expectedAutomaticDownloads': expected}, authorized=lambda: self.authorized)

  def test_download_preference_is_independent_of_manual_updater_commands(self):
    self.assertIs(self.owner.snapshot()['automaticDownloads'], True)
    result = self.save_downloads(False, True)
    self.assertIs(result['automaticDownloads'], False)
    self.assertIsNone(result['request'])
    self.assertEqual(self.process.sent, [])
    self.assertTrue(result['canDownload'])
    self.act('download', 'main')
    self.assertEqual(self.process.sent, ['download'])

  def test_preference_can_be_saved_without_running_updater_but_not_after_authority_changes(self):
    self.process.running = False
    self.assertTrue(self.owner.snapshot()['canConfigure'])
    self.assertFalse(self.save_downloads(False, True)['automaticDownloads'])
    for case in ('stale', 'onroad', 'unauthorized', 'reboot'):
      self.parked = case != 'onroad'
      self.authorized = case != 'unauthorized'
      self.params.put_bool('DoReboot', case == 'reboot', block=True)
      with self.assertRaises(SoftwareOperationError):
        self.save_downloads(True, True if case == 'stale' else False)
      self.assertFalse(self.params.get_bool('UpdaterAutomaticDownloads'))
    self.assertEqual(self.process.sent, [])

  def test_invalid_preference_can_be_repaired_without_implicit_enabling(self):
    Path(self.params.get_param_path('UpdaterAutomaticDownloads')).write_bytes(b'bad')
    self.assertIsNone(self.owner.snapshot()['automaticDownloads'])
    self.assertFalse(self.save_downloads(False, None)['automaticDownloads'])
    with self.assertRaises(SoftwareOperationError):
      self.save_downloads(1, False)

  def test_history_caches_local_reads_and_refreshes_when_download_identity_changes(self):
    reader = mock.Mock(side_effect=lambda path, sha: [{'hash': sha, 'date': '2026-09-29T12:00:00+00:00', 'subject': path.name}])
    self.owner.history_reader = reader
    self.params.put('UpdaterCurrentReleaseNotes', b'<h1>Current</h1>', block=True)
    self.params.put('UpdaterNewReleaseNotes', b'<h1>Next</h1>', block=True)
    first = self.owner.snapshot()['history']
    self.assertEqual(first['installed'][0]['hash'], 'a' * 40)
    self.assertEqual(first['downloaded'][0]['hash'], 'b' * 40)
    self.assertEqual(first['currentReleaseNotes'], 'Current')
    self.assertEqual(first['downloadedReleaseNotes'], 'Next')
    self.assertEqual(reader.call_count, 2)
    self.assertEqual(self.owner.snapshot()['history'], first)
    self.assertEqual(reader.call_count, 2)
    self.params.put('UpdaterNewDescription', 'new description', block=True)
    self.owner.snapshot()
    self.assertEqual(reader.call_count, 4)


class UpdaterIdentityTest(unittest.TestCase):
  def test_fresh_manager_pid_and_same_proc_start_before_signal(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      proc = root / "123"
      proc.mkdir()
      (proc / "stat").write_text("123 (updater) " + " ".join(["S", *(["0"] * 18), "3456"]))
      (proc / "cmdline").write_bytes(PROCESS_TITLE + b"\0")
      state = SimpleNamespace(name="updated", running=True, shouldBeRunning=True, pid=123)
      class ManagerMessages:
        seen = {"managerState": True}
        alive = {"managerState": True}
        valid = {"managerState": True}
        recv_time = {"managerState": 1.25}
        logMonoTime = {"managerState": 1_250_000_000}

        def update(self, timeout):
          pass

        def __getitem__(self, key):
          return SimpleNamespace(processes=[state])

      sm = ManagerMessages()
      clock = [1_000_000_000]
      class FakeControl:
        def __init__(self):
          self.available_calls = []
          self.sent = []

        def available(self, pid, start):
          self.available_calls.append((pid, start))
          return True

        def send(self, pid, start, action):
          self.sent.append((pid, start, action))

      control = FakeControl()
      process = UpdaterProcess(sm, control=control, proc_root=root, mono_ns=lambda: clock[0])
      clock[0] = 1_500_000_000
      with mock.patch("os.kill") as kill:
        self.assertTrue(process.available())
        process.send("check")
        self.assertEqual(control.available_calls, [(123, 3456)])
        self.assertEqual(control.sent, [(123, 3456, "check")])
        with mock.patch.object(control, "send", side_effect=UpdaterControlError("declined")):
          with self.assertRaises(SoftwareOperationError) as denied:
            process.send("download")
          self.assertEqual(denied.exception.status, 503)
        with mock.patch.object(process, "_manager_pid", side_effect=[123, 124]):
          with self.assertRaises(SoftwareOperationError):
            process.send("download")
        self.assertEqual(control.sent, [(123, 3456, "check")])
        kill.assert_not_called()
      sm.recv_time["managerState"] = 0.9
      self.assertFalse(process.available())
      sm.recv_time["managerState"] = 1.25
      (proc / "cmdline").write_bytes(b"other\0")
      self.assertFalse(process.available())
      with self.assertRaises(SoftwareOperationError):
        process.send("download")


if __name__ == "__main__":
  unittest.main()
