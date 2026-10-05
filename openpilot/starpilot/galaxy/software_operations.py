"""Parked requests to the existing updater and manager."""

from __future__ import annotations

import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import threading
import time
from collections.abc import Callable

from openpilot.common.basedir import BASEDIR
from openpilot.common.params import Params
from openpilot.common.vendor_manifest import validate_revision
from openpilot.starpilot.galaxy.software_status import SoftwareStatus, SoftwareUnavailable
from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.software.update_control import UpdaterControlError
from openpilot.starpilot.software.preferences import AUTOMATIC_DOWNLOADS, automatic_downloads
from openpilot.starpilot.software.history import commit_history, release_notes, recent_versions


FINALIZED = Path(os.environ.get("UPDATER_STAGING_ROOT", "/data/safe_staging")) / "finalized"
BRANCH_PATTERN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._/+@-]{0,127}\Z")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
MAX_BRANCH_LIST = 32768
MAX_BRANCHES = 256
PROCESS_TITLE = b"openpilot.system.updated.updated"


class SoftwareOperationError(Exception):
  def __init__(self, message: str, status: int = 409):
    super().__init__(message)
    self.status = status


class UpdaterProcess:
  """Resolve the exact manager child before using its updater-owned control."""

  def __init__(self, messages=None, *, control=None, proc_root: Path = Path("/proc"),
               mono_ns: Callable[[], int] = time.monotonic_ns):
    if control is None:
      from openpilot.starpilot.software import update_control
      control = update_control
    self.messages = messages
    self.control = control
    self.proc_root = proc_root
    self.mono_ns = mono_ns
    self.created_ns = mono_ns()
    self.lock = threading.Lock()

  def _manager_pid(self) -> int:
    if self.messages is None:
      from openpilot.cereal import messaging
      self.messages = messaging.SubMaster(["managerState"])
    sm = self.messages
    sm.update(0)
    now = self.mono_ns()
    received = int(sm.recv_time["managerState"] * 1e9)
    published = int(sm.logMonoTime["managerState"])
    age = now - received
    if (not sm.seen["managerState"] or not sm.alive["managerState"] or not sm.valid["managerState"] or
        not 0 <= age <= 3_000_000_000 or received <= self.created_ns or
        not 0 <= now - published <= 3_000_000_000 or published <= self.created_ns):
      raise SoftwareOperationError("Updater manager status is unavailable", 503)
    matches = [p for p in sm["managerState"].processes if p.name == "updated"]
    if len(matches) != 1 or not matches[0].running or not matches[0].shouldBeRunning or int(matches[0].pid) <= 1:
      raise SoftwareOperationError("Updater is not running", 503)
    return int(matches[0].pid)

  def _proc_identity(self, pid: int) -> int:
    base = self.proc_root / str(pid)
    try:
      raw = (base / "stat").read_text()
      right = raw.rfind(")")
      if right < 0:
        raise ValueError
      fields = raw[right + 2:].split()
      start = int(fields[19])
      cmdline = (base / "cmdline").read_bytes().split(b"\0", 1)[0]
      if start <= 0 or cmdline != PROCESS_TITLE:
        raise ValueError
      return start
    except (OSError, ValueError, IndexError):
      raise SoftwareOperationError("Updater process identity is unavailable", 503) from None

  def available(self) -> bool:
    with self.lock:
      try:
        pid = self._manager_pid()
        start = self._proc_identity(pid)
        return bool(self._manager_pid() == pid and self._proc_identity(pid) == start and
                    self.control.available(pid, start))
      except (SoftwareOperationError, UpdaterControlError, OSError, RuntimeError, ValueError):
        return False

  def send(self, action: str, *, branch=None, commit=None, selected_commit=None) -> None:
    if action not in ("check", "download", "fast", "rollback", "versions", "version"):
      raise SoftwareOperationError("Invalid updater command", 400)
    with self.lock:
      pid = self._manager_pid()
      start = self._proc_identity(pid)
      if self._manager_pid() != pid or self._proc_identity(pid) != start:
        raise SoftwareOperationError("Updater process changed", 503)
      try:
        if action == 'version':
          self.control.send(pid, start, action, branch=branch, commit=commit, selected_commit=selected_commit)
        elif action in ("fast", "rollback", "versions"):
          self.control.send(pid, start, action, branch=branch, commit=commit)
        else:
          self.control.send(pid, start, action)
      except (UpdaterControlError, OSError, RuntimeError, ValueError):
        raise SoftwareOperationError("Updater control is unavailable", 503) from None

  def close(self) -> None:
    with self.lock:
      if self.messages is not None:
        for sock in getattr(self.messages, "sock", {}).values():
          close = getattr(sock, "close", None)
          if close:
            close()
        self.messages = None


def _git_identity(path: Path) -> tuple[str, str] | None:
  try:
    branch = subprocess.run(["git", "-C", str(path), "symbolic-ref", "--quiet", "--short", "HEAD"],
                            check=True, capture_output=True, text=True, timeout=2).stdout.strip()
    commit = subprocess.run(["git", "-C", str(path), "rev-parse", "--verify", "HEAD^{commit}"],
                            check=True, capture_output=True, text=True, timeout=2).stdout.strip()
    if not BRANCH_PATTERN.fullmatch(branch) or not COMMIT_PATTERN.fullmatch(commit):
      return None
    return branch, commit
  except (OSError, subprocess.SubprocessError):
    return None


class SoftwareOperations:
  def __init__(self, params=None, status=None, parked=None, process=None, *, finalized=FINALIZED,
               installed=BASEDIR, git_identity=_git_identity, clock=time.monotonic, history_reader=commit_history):
    self.params = params if params is not None else Params()
    self.status = status if status is not None else SoftwareStatus(self.params)
    if parked is None:
      from openpilot.starpilot.galaxy.settings import LiveContextSource
      self.context = LiveContextSource(self.params)
      self.parked = self.context.parked
    else:
      self.context = None
      self.parked = parked
    self.process = process if process is not None else UpdaterProcess()
    self.finalized = Path(finalized)
    self.installed = Path(installed)
    self.git_identity = git_identity
    self.clock = clock
    self.history_reader = history_reader
    self._history_key = None
    self._history_at = float('-inf')
    self._history = None
    self.lock = threading.RLock()
    self.selected_target: str | None = None
    self.request: dict | None = None
    self._baseline: tuple | None = None
    self._started = 0.0
    self._fast_commit = None

  def _param(self, key: str, limit: int = 256) -> str | None:
    try:
      value = self.params.get(key)
      if isinstance(value, bytes):
        value = value.decode("utf-8")
      if value is not None and (type(value) is not str or len(value.encode()) > limit or not value.isprintable()):
        raise ValueError
      return value
    except (OSError, ValueError, UnicodeError, TypeError):
      raise SoftwareOperationError("Updater status is unavailable", 503) from None

  def _branches(self) -> list[str]:
    raw = self._param("UpdaterAvailableBranches", MAX_BRANCH_LIST)
    if raw is None or not raw:
      return []
    entries = raw.split(",")
    if len(entries) > MAX_BRANCHES:
      return []
    return list(dict.fromkeys(branch for branch in entries if BRANCH_PATTERN.fullmatch(branch)))

  def _flag(self, key: str) -> bool | None:
    try:
      raw, readable = read_saved(self.params, key, 8)
      if not readable:
        return None
      if raw is None:
        return False
      return raw == b"1" if raw in (b"0", b"1") else None
    except (OSError, ValueError, TypeError):
      return None

  @staticmethod
  def _valid_branch(branch: object) -> bool:
    if type(branch) is not str or not BRANCH_PATTERN.fullmatch(branch):
      return False
    try:
      return subprocess.run(["git", "check-ref-format", "--branch", branch], capture_output=True,
                            timeout=2).returncode == 0
    except (OSError, subprocess.SubprocessError):
      return False

  def _parked(self) -> bool:
    try:
      return self._flag("IsOffroad") is True and bool(self.parked())
    except (OSError, RuntimeError, ValueError, TypeError):
      return False

  def _ready(self, status: dict, target: str | None) -> bool:
    try:
      marker = self.finalized.joinpath(".overlay_consistent").lstat()
      regular_marker = stat.S_ISREG(marker.st_mode)
    except OSError:
      regular_marker = False
    if (target is None or status["updater"]["targetBranch"] != target or
        status["updater"]["finalizedUpdateReady"] is not True or
        status["updater"]["state"] != "idle" or
        not regular_marker):
      return False
    final = self.git_identity(self.finalized)
    current = self.git_identity(self.installed)
    if final is None or current is None or final[0] != target or final == current:
      return False
    description = self._param("UpdaterNewDescription")
    parts = description.split(" / ") if description else []
    if len(parts) != 4 or parts[1] != target or not final[1].startswith(parts[2]) or len(parts[2]) != 7:
      return False
    try:
      validate_revision(self.finalized, final[1])
    except (OSError, ValueError, subprocess.SubprocessError):
      return False
    return True

  def _refresh_request(self, status: dict) -> None:
    request = self.request
    if self._baseline is None or request is None or request["state"] != "pending" or request["action"] == "install":
      return
    state = status["updater"]["state"]
    if (request["action"] not in ("fast", "rollback", "versions", "version") and request["target"] is not None and
        status["updater"]["targetBranch"] != request["target"]):
      request.update(state="failed", error="Updater target changed")
    elif state == "idle" and status["updater"]["failedCount"] is not None and self._baseline[2] is not None and \
         status["updater"]["failedCount"] > self._baseline[2]:
      error = "Updater reported a failure"
      if request["action"] in ("fast", "rollback", "versions", "version"):
        try:
          error = self._param("LastUpdateException", 4096) or error
        except SoftwareOperationError:
          pass
      request.update(state="failed", error=error)
    elif request['action'] == 'versions' and state == 'idle' and status['updater']['failedCount'] == 0 and \
         status['updater']['lastFetchAt'] is not None and status['updater']['lastFetchAt'] != self._baseline[1]:
      request.update(state='complete', error=None)
    elif state == "idle" and status["updater"]["failedCount"] == 0 and \
         status["updater"]["lastSuccessAt"] is not None and \
         status["updater"]["lastSuccessAt"] != self._baseline[0]:
      if request["action"] in ("fast", "rollback", "versions", "version"):
        if status["updater"]["lastFetchAt"] != self._baseline[1]:
          restarting = self._flag("DoReboot") is True or status["installed"]["commit"] != self._fast_commit
          if request['action'] == 'versions':
            request.update(state='complete', error=None)
          else:
            request.update(state="complete", error=None, outcome="restarting" if restarting else "up_to_date")
      elif request["action"] == "check" or status["updater"]["lastFetchAt"] != self._baseline[1]:
        request.update(state="complete", error=None)
      elif self._ready(status, request["target"]):
        request.update(state="complete", error=None)
      else:
        request.update(state="failed", error="No new download was reported for this branch")
    elif self.clock() - self._started > 900:
      request.update(state="failed", error="Updater did not report completion")

  def _rollback_available(self):
    try:
      result = subprocess.run(["git", "-C", str(self.installed), "rev-parse", "--verify", "refs/starpilot/previous^{commit}"],
                              check=True, capture_output=True, text=True, timeout=2)
      branch = subprocess.run(["git", "-C", str(self.installed), "config", "--local", "--get", "starpilot.previousVersion"],
                              check=True, capture_output=True, text=True, timeout=2).stdout.strip()
      saved = branch.split(' ', 1)
      return bool(len(saved) == 2 and saved[0] == result.stdout.strip() and COMMIT_PATTERN.fullmatch(saved[0]) and self._valid_branch(saved[1]))
    except (OSError, subprocess.SubprocessError):
      return False

  def snapshot(self) -> dict:
    with self.lock:
      try:
        status = self.status.snapshot()
      except SoftwareUnavailable:
        raise SoftwareOperationError("Updater status is unavailable", 503) from None
      self._refresh_request(status)
      parked = self._parked()
      branches = self._branches()
      updater_idle = status["updater"]["state"] == "idle"
      pending = self.request is not None and self.request["state"] == "pending"
      disabled_state = self._flag("DisableUpdates")
      disabled = disabled_state is not False
      reboot = self._flag("DoReboot") is not False
      process = self.process.available() if parked and updater_idle and not disabled and not pending and not reboot else False
      usable = parked and updater_idle and not disabled and not pending and not reboot and process
      target = self.selected_target or status["updater"]["targetBranch"] or status["installed"]["branch"]
      selected = target is not None and target in branches and status["updater"]["targetBranch"] == target
      reason = None
      if not parked:
        reason = "Park the vehicle to manage updates"
      elif disabled:
        reason = "Updates are disabled"
      elif reboot:
        reason = "Reboot is pending"
      elif pending or not updater_idle:
        reason = "Updater is busy"
      elif not process:
        reason = "Updater is not running"
      return {
        "parked": parked, "availableBranches": branches, "selectedTarget": target,
        "canCheck": usable, "canFastUpdate": usable and self._valid_branch(status["installed"]["branch"]), "canSelect": usable and bool(branches),
        "canRollback": usable and self._rollback_available(),
        "canDownload": usable and selected, "canInstall": usable and selected and self._ready(status, target),
        "reason": reason, "request": dict(self.request) if self.request is not None else None,
        "automaticDownloads": automatic_downloads(self.params), "canConfigure": parked and not reboot,
        "history": self._history_snapshot(status),
      }

  def _history_snapshot(self, status: dict) -> dict:
    branch = self.selected_target or status['updater']['targetBranch'] or status['installed']['branch']
    key = (status['installed']['commit'], self._param('UpdaterNewDescription'), branch, status['updater']['lastFetchAt'])
    now = self.clock()
    if self._history is not None and self._history_key == key and 0 <= now - self._history_at < 30.:
      return self._history
    recent = recent_versions(self.installed, branch)
    installed = self.git_identity(self.installed)
    downloaded = self.git_identity(self.finalized)
    current_rows = self.history_reader(self.installed, installed[1]) if installed else []
    downloaded_rows = (self.history_reader(self.finalized, downloaded[1])
                       if downloaded and downloaded != installed else [])
    # Readiness and installation still require _ready(); a history entry never
    # grants permission to boot or execute a revision.
    self._history = {
      'installed': current_rows, 'downloaded': downloaded_rows, 'recent': recent,
      'currentReleaseNotes': release_notes(self.params, 'UpdaterCurrentReleaseNotes'),
      'downloadedReleaseNotes': release_notes(self.params, 'UpdaterNewReleaseNotes') if downloaded_rows else None,
    }
    self._history_at, self._history_key = now, key
    return self._history

  def _preferences(self, payload: dict, authorized: Callable[[], bool]) -> dict:
    expected = payload.get('expectedAutomaticDownloads')
    enabled = payload.get('automaticDownloads')
    if (set(payload) != {'action', 'automaticDownloads', 'expectedAutomaticDownloads'} or
        type(enabled) is not bool or expected is not None and type(expected) is not bool):
      raise SoftwareOperationError('Invalid software preferences', 400)
    with self.lock:
      if not authorized():
        raise SoftwareOperationError('Session expired', 403)
      if not self._parked() or self._flag('DoReboot') is not False:
        raise SoftwareOperationError('Park the vehicle to change update preferences', 409)
      if automatic_downloads(self.params) is not expected:
        raise SoftwareOperationError('Update preference changed; refresh before saving', 409)
      if not authorized() or not self._parked() or self._flag('DoReboot') is not False:
        raise SoftwareOperationError('Session or parked state changed', 403)
      if automatic_downloads(self.params) is not expected:
        raise SoftwareOperationError('Update preference changed; refresh before saving', 409)
      self.params.put_bool(AUTOMATIC_DOWNLOADS, enabled, block=True)
      if automatic_downloads(self.params) is not enabled:
        raise SoftwareOperationError('Update preference could not be verified', 503)
      return self.snapshot()

  def action(self, action: str, payload: object, *, authorized: Callable[[], bool]) -> dict:
    if (type(payload) is not dict or type(action) is not str or
        action not in ("check", "download", "select", "install", "preferences", "fast", "rollback", "versions", "version")):
      raise SoftwareOperationError("Invalid software action", 400)
    assert isinstance(payload, dict)
    payload = dict(payload)
    if payload.get("action") != action or any(type(key) is not str for key in payload):
      raise SoftwareOperationError("Invalid software action", 400)
    if action == 'preferences':
      return self._preferences(payload, authorized)
    fields = set(payload) - {"action"}
    if action == "check":
      if fields:
        raise SoftwareOperationError("Invalid software action", 400)
      branch = None
    else:
      required_fields = {"branch", "expectedCommit", "selectedCommit"} if action == "version" else {"branch"}
      if fields != required_fields or not self._valid_branch(payload.get("branch")):
        raise SoftwareOperationError("Invalid branch", 400)
      branch = payload["branch"]
      assert isinstance(branch, str)
    with self.lock:
      if not authorized():
        raise SoftwareOperationError("Session expired", 403)
      view = self.snapshot()
      if not view["parked"]:
        raise SoftwareOperationError("Vehicle is not safely parked", 409)
      if view["reason"] is not None:
        raise SoftwareOperationError(view["reason"], 503 if view["reason"] == "Updater is not running" else 409)
      if action not in ("fast", "rollback", "versions", "version") and branch is not None and branch not in view["availableBranches"]:
        raise SoftwareOperationError("Branch is not in the current updater list", 409)
      if action not in ("check", "select", "fast", "rollback", "versions", "version") and (branch != view["selectedTarget"] or not view["canDownload"]):
        raise SoftwareOperationError("Selected updater target changed", 409)
      if action in ("fast", "rollback", "versions", "version"):
        installed = self.status.snapshot()["installed"]
        identity = self.git_identity(self.installed)
        if (not view["canFastUpdate"] or identity is None or identity != (installed["branch"], installed["commit"]) or
            (action in ("fast", "versions", "version") and branch != installed["branch"] and branch not in view["availableBranches"]) or
            (action == "rollback" and (branch != installed["branch"] or not view["canRollback"]))):
          raise SoftwareOperationError("Installed branch changed; refresh before updating", 409)
      if action == 'version':
        target = payload['selectedCommit']
        recent = view['history']['recent']
        if (payload['expectedCommit'] != identity[1] or type(target) is not str or not COMMIT_PATTERN.fullmatch(target) or
            recent['branch'] != branch or not any(row['hash'] == target for row in recent['entries'])):
          raise SoftwareOperationError('Selected version or installed revision changed; refresh and try again', 409)
      if action == "install" and not view["canInstall"]:
        raise SoftwareOperationError("Finalized update does not match selected branch", 409)
      if not authorized() or not self._parked():
        raise SoftwareOperationError("Session or parked state changed", 403)
      current = self.status.snapshot()
      if (current["updater"]["state"] != "idle" or self._flag("DisableUpdates") is not False or
          self._flag("DoReboot") is not False or not self.process.available() or
          (action not in ("fast", "rollback", "versions", "version") and branch is not None and branch not in self._branches()) or
          (action == "rollback" and current["installed"]["branch"] != branch)):
        raise SoftwareOperationError("Updater state changed", 409)
      if action == "select":
        self.params.put("UpdaterTargetBranch", branch, block=True)
        self.selected_target = branch
        return self.snapshot()
      if action == "install":
        status = self.status.snapshot()
        if not self._ready(status, branch) or self._flag("DoReboot") is not False:
          raise SoftwareOperationError("Update is no longer ready", 409)
        if not authorized() or not self._parked():
          raise SoftwareOperationError("Session or parked state changed", 403)
        self.params.put_bool("DoReboot", True, block=True)
      else:
        status = self.status.snapshot()
        baseline = (status["updater"]["lastSuccessAt"], status["updater"]["lastFetchAt"],
                    status["updater"]["failedCount"])
        if not authorized() or not self._parked():
          raise SoftwareOperationError("Session or parked state changed", 403)
        if action in ("fast", "rollback", "versions", "version"):
          identity = self.git_identity(self.installed)
          if identity is None or identity != (status["installed"]["branch"], status["installed"]["commit"]):
            raise SoftwareOperationError("Installed branch changed; refresh before updating", 409)
          if action == 'version' and identity[1] != payload['expectedCommit']:
            raise SoftwareOperationError('Installed revision changed before version request; refresh and try again', 409)
          self._fast_commit = status["installed"]["commit"]
        if action in ("fast", "rollback", "versions", "version"):
          if action == 'version':
            self.process.send(action, branch=branch, commit=identity[1], selected_commit=payload['selectedCommit'])
          else:
            self.process.send(action, branch=branch, commit=identity[1])
        else:
          self.process.send(action)
      self.request = {"id": secrets.token_hex(8), "action": action,
                      "target": branch if branch is not None else status["updater"]["targetBranch"],
                      "state": "pending", "error": None}
      if action == 'version':
        self.request['selectedCommit'] = payload['selectedCommit']
      self._baseline = baseline if action != "install" else None
      self._started = self.clock()
      return self.snapshot()

  def close(self) -> None:
    if self.context is not None:
      self.context.close()
    self.process.close()
