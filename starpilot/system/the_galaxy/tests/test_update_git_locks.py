"""Timed-out git commands must be stopped so git can remove its lock files."""
import ast
import contextlib
import os
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1].joinpath("the_galaxy.py").read_text()

# Stands in for git: holds a lock and removes it on SIGTERM, as git's lockfile cleanup does.
FAKE_GIT = '''
import os, signal, sys, time
lock, mode = sys.argv[1:3]
open(lock, "w").close()
def cleanup(signum, frame):
  os.unlink(lock)
  sys.exit(128 + signum)
signal.signal(signal.SIGTERM, signal.SIG_IGN if mode == "stubborn" else cleanup)
if mode == "helper":
  # Like a hook or filter git starts: inherits git's stdout/stderr and outlives it.
  import subprocess
  helper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
  open(lock + ".helper", "w").write(str(helper.pid))
open(lock + ".ready", "w").close()
while True:
  time.sleep(0.05)
'''


def load(*names, **scope):
  functions = [node for node in ast.parse(SOURCE).body if isinstance(node, ast.FunctionDef) and node.name in names]
  assert {node.name for node in functions} == set(names)
  exec(compile(ast.Module(body=functions, type_ignores=[]), "the_galaxy.py", "exec"), scope)
  return scope


def git_runner(tmp_path, mode, grace=5.0):
  script = tmp_path / "fake_git.py"
  script.write_text(FAKE_GIT)
  lock = tmp_path / "shallow.lock"
  scope = load("_stop_git_process", "_run_git_with_progress", "_run_git",
               subprocess=subprocess, os=os, selectors=selectors, time=time,
               _GIT_TERMINATE_GRACE_S=grace, _FAST_UPDATE_PROGRESS_UPDATE_INTERVAL_S=5.0,
               _git_base_cmd=lambda: [sys.executable, str(script), str(lock), mode],
               _git_command_env=lambda: dict(os.environ),
               _parse_git_progress_line=lambda text: (None, text, ""),
               _normalize_git_phase_percent=lambda phase, percent: percent,
               _set_fast_update_progress=lambda *args: None)
  return scope, lock


def test_stalled_fetch_is_terminated_so_git_removes_its_lock(tmp_path):
  scope, lock = git_runner(tmp_path, "clean")
  with pytest.raises(TimeoutError, match="stalled"):
    scope["_run_git_with_progress"](str(tmp_path), ["fetch"], timeout=1.5, step=2, label="Fetching")
  assert Path(f"{lock}.ready").exists(), "the stand-in must have installed its handler"
  assert not lock.exists()


def test_git_ignoring_sigterm_is_killed_after_the_grace_period(tmp_path):
  scope, lock = git_runner(tmp_path, "stubborn", grace=0.3)
  started = time.monotonic()
  with pytest.raises(TimeoutError):
    scope["_run_git_with_progress"](str(tmp_path), ["fetch"], timeout=1.5, step=2, label="Fetching")
  assert time.monotonic() - started < 10
  assert lock.exists(), "only SIGKILL, the fallback, leaves the lock behind"


def test_timed_out_short_git_command_is_terminated_and_still_raises(tmp_path):
  scope, lock = git_runner(tmp_path, "clean")
  with pytest.raises(subprocess.TimeoutExpired):
    scope["_run_git"](str(tmp_path), ["reset", "--hard", "FETCH_HEAD"], timeout=1.5)
  assert not lock.exists()


def test_timed_out_git_returns_even_if_its_child_still_holds_the_output_pipes(tmp_path):
  scope, lock = git_runner(tmp_path, "helper")
  started = time.monotonic()
  try:
    with pytest.raises(subprocess.TimeoutExpired):
      scope["_run_git"](str(tmp_path), ["reset", "--hard", "FETCH_HEAD"], timeout=1.5)
    assert time.monotonic() - started < 10
    assert not lock.exists()
  finally:
    with contextlib.suppress(FileNotFoundError, ProcessLookupError):
      os.kill(int(Path(f"{lock}.helper").read_text()), signal.SIGKILL)


def test_run_git_keeps_its_completed_process_result(tmp_path):
  scope = load("_stop_git_process", "_run_git", subprocess=subprocess, _GIT_TERMINATE_GRACE_S=5.0,
               _git_base_cmd=lambda: [sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)"],
               _git_command_env=lambda: dict(os.environ))
  result = scope["_run_git"](str(tmp_path), [])
  assert (result.returncode, result.stdout.strip(), result.stderr.strip()) == (3, "out", "err")


@pytest.mark.parametrize("error,hinted", [
  ("fatal: Unable to create '/data/openpilot/.git/shallow.lock': File exists.\nAnother git process seems to be running", True),
  ("fatal: Unable to create '/data/openpilot/.git/index.lock': File exists.", False),
  ("fatal: unable to access 'https://github.com/': Could not resolve host", False),
])
def test_stale_shallow_lock_error_points_to_recover(error, hinted):
  states = []
  scope = load("_set_fast_update_error_state", SHALLOW_LOCK_NAME="shallow.lock", _FAST_UPDATE_TOTAL_STEPS=5, time=time,
               _set_fast_update_state=lambda **state: states.append(state))
  scope["_set_fast_update_error_state"]("Fast update failed.", RuntimeError(error))
  [state] = states
  assert state["lastError"] == error
  assert ("Tap Recover" in state["message"]) is hinted
  assert state["message"].startswith("Fast update failed.")
