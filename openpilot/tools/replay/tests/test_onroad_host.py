"""Host replay parsing, private Params seeding and child ownership."""

from pathlib import Path
from types import SimpleNamespace
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from openpilot.common.params import Params
from openpilot.tools.replay.onroad import _block_alert_service, _ipc_root, owned_ipc_namespace, parse_onroad_args, run, seed_replay_params, supervise
from openpilot.tools.replay.onroad_config import first_log_identifier, parse_replay_args, seed_preview, select_ui_target


class TestOnroadHost(unittest.TestCase):
  def test_supervisor_preserves_fast_clean_exit_and_maps_child_signal(self):
    class FakeProcess:
      def __init__(self, statuses):
        self.statuses = iter(statuses)
        self.returncode = None

      def poll(self):
        self.returncode = next(self.statuses, self.returncode)
        return self.returncode

      def terminate(self):
        self.returncode = 0

    clean = FakeProcess([0])
    self.assertEqual(supervise(["replay"], [], {}, spawn=lambda *_args, **_kwargs: clean), 0)
    replay = FakeProcess([None, None])
    aborted_ui = FakeProcess([-6])
    queue = iter((replay, aborted_ui))
    self.assertEqual(supervise(["replay"], [["ui"]], {}, spawn=lambda *_args, **_kwargs: next(queue)), 134)

  def test_native_pubmaster_uses_owned_ipc_parent_and_cleanup(self):
    prefix = f"replay-test-{os.getpid()}-{time.time_ns()}"
    root = _ipc_root(prefix)
    self.assertFalse(root.exists())
    with owned_ipc_namespace(prefix):
      self.assertTrue(root.is_dir())
      env = dict(os.environ, OPENPILOT_PREFIX=prefix)
      env.pop("CEREAL_FAKE", None)
      result = subprocess.run([sys.executable, "-c", "from openpilot.cereal.messaging import PubMaster; PubMaster(['accelerometer'])"],
                              env=env, capture_output=True, text=True, check=False, timeout=5)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      self.assertTrue((root / "accelerometer").exists())
    self.assertFalse(root.exists())

  def test_existing_ipc_namespace_is_never_removed(self):
    prefix = f"replay-test-{os.getpid()}-{time.time_ns()}"
    root = _ipc_root(prefix)
    root.mkdir()
    try:
      sentinel = root / "external"
      sentinel.write_text("keep")
      with self.assertRaisesRegex(RuntimeError, "already has an IPC namespace"):
        with owned_ipc_namespace(prefix):
          pass
      self.assertEqual(sentinel.read_text(), "keep")
    finally:
      sentinel.unlink()
      root.rmdir()

  def test_help_requires_no_runtime_or_route(self):
    result = subprocess.run([sys.executable, "-m", "openpilot.tools.replay.onroad", "--help"],
                            capture_output=True, text=True, check=False)
    self.assertEqual(result.returncode, 0)
    self.assertIn("--replay-only", result.stdout)

  def test_route_ui_and_option_preservation(self):
    plan = parse_onroad_args(["--c4", "--prefix", "replay-fixture", "--start", "30", "--data_dir=/private/routes",
                              "route/abc", "--no-loop"])
    self.assertEqual(plan.targets, ("c4",))
    self.assertEqual(plan.prefix, "replay-fixture")
    self.assertEqual(plan.replay_args, ("--start", "30", "--data_dir=/private/routes", "route/abc", "--no-loop"))
    self.assertEqual(select_ui_target(SimpleNamespace(deviceType="mici")), "c4")
    self.assertEqual(select_ui_target(None), "c3")
    self.assertEqual(parse_onroad_args(["--all", "--demo"]).targets, ("c3", "c4"))
    self.assertEqual(parse_onroad_args(["--replay-only", "--demo"]).targets, ())

  def test_unsupported_or_unsafe_options_fail_before_spawn(self):
    for args in (["--nav", "--demo"], ["--replay-only", "--alert", "--demo"],
                 ["--ui=none", "-alert", "--demo"],
                 ["--prefix", "d", "--demo"], ["--demo", "--", "--prefix", "replay-other"],
                 ["--headless", "--demo"], ["--auto"], ["--ui=bogus", "--demo"]):
      with self.subTest(args=args), self.assertRaises(ValueError):
        parse_onroad_args(args)

  def test_alert_preview_preserves_route_and_combines_native_blocklist(self):
    plan = parse_onroad_args(["--c4", "-alert", "-b", "carControl,selfdriveState", "--start", "30", "--demo"])
    self.assertTrue(plan.alert)
    self.assertEqual(plan.targets, ("c4",))
    self.assertEqual(_block_alert_service(plan.replay_args),
                     ["-b", "carControl,selfdriveState", "--start", "30", "--demo"])
    self.assertEqual(_block_alert_service(("--block=carState", "--demo")),
                     ["-b", "carState,selfdriveState", "--demo"])
    self.assertEqual(_block_alert_service(("-b", "carState", "--block=carControl,selfdriveState", "--demo")),
                     ["-b", "carState,carControl,selfdriveState", "--demo"])
    self.assertFalse(parse_onroad_args(["--c3", "--demo"]).alert)
    self.assertFalse(parse_onroad_args(["--demo"]).visual_preview)

  def test_cem_csc_aliases_are_ui_only_and_combine_with_alert(self):
    plan = parse_onroad_args(["--c4", "--mici-widget-demo", "--csc-demo", "-alert", "--demo"])
    self.assertEqual(plan.visual_preview, frozenset(("cem", "csc")))
    self.assertTrue(plan.alert)
    self.assertEqual(plan.replay_args, ("--demo",))
    self.assertEqual(parse_onroad_args(["--c3", "--widget-demo", "--demo"]).visual_preview,
                     frozenset(("cem",)))
    self.assertEqual(parse_onroad_args(["--c3", "--csc", "--demo"]).visual_preview,
                     frozenset(("csc",)))
    for args in (["--replay-only", "--cem", "--demo"], ["--ui=none", "--csc", "--demo"]):
      with self.subTest(args=args), self.assertRaisesRegex(ValueError, "require a native UI"):
        parse_onroad_args(args)

  def test_alert_publisher_failure_reaps_replay_and_ui(self):
    class FakeProcess:
      def __init__(self, statuses):
        self.statuses = iter(statuses)
        self.returncode = None
        self.terminated = False

      def poll(self):
        self.returncode = next(self.statuses, self.returncode)
        return self.returncode

      def terminate(self):
        self.terminated = True
        self.returncode = 0

    replay = FakeProcess([None, None])
    ui = FakeProcess([None])
    alert = FakeProcess([2])
    queue = iter((replay, ui, alert))
    self.assertEqual(supervise(["replay"], [["ui"]], {}, demo_commands=[["alert"]],
                               spawn=lambda *_args, **_kwargs: next(queue)), 2)
    self.assertTrue(replay.terminated)
    self.assertTrue(ui.terminated)
    replay = FakeProcess([None, None])
    ui = FakeProcess([None])
    alert = FakeProcess([0])
    queue = iter((replay, ui, alert))
    self.assertEqual(supervise(["replay"], [["ui"]], {}, demo_commands=[["alert"]],
                               spawn=lambda *_args, **_kwargs: next(queue)), 1)

  def test_alert_run_passes_one_owned_publisher_and_replay_exclusion(self):
    with tempfile.TemporaryDirectory() as directory:
      private = Path(directory) / "params"
      env = {"SP_HOST_RUNTIME": "1", "SP_HOST_PARAMS_ROOT": str(private), "PARAMS_ROOT": str(private),
             "SP_HOST_PREFIX": "starpilot-dev-host", "OPENPILOT_PREFIX": "starpilot-dev-host"}
      with patch.dict(os.environ, env), patch.object(Path, "is_file", return_value=True), \
           patch("openpilot.tools.replay.onroad.os.access", return_value=True), \
           patch("openpilot.tools.replay.onroad_config.route_init_data", return_value=None), \
           patch("openpilot.starpilot.ui.host_launch.launch_environment", return_value={}), \
           patch("openpilot.tools.replay.onroad.supervise", return_value=0) as owned:
        self.assertEqual(run(parse_onroad_args(["--c4", "--cem", "--csc", "-alert", "--prefix", "replay-alertfixture",
                                               "-b", "carControl", "--demo"])), 0)
      replay, ui, child_env, kwargs = owned.call_args.args[0], owned.call_args.args[1], owned.call_args.args[2], owned.call_args.kwargs
      self.assertEqual(replay[1:3], ["-b", "carControl,selfdriveState"])
      self.assertEqual(len(ui), 1)
      self.assertEqual(child_env["SP_ONROAD_VISUAL_PREVIEW"], "cem,csc")
      self.assertEqual(kwargs["demo_commands"], [[sys.executable, "-m", "openpilot.tools.replay.alert_demo"]])

  def test_actual_private_alert_pubsub_shows_then_clears(self):
    prefix = f"replay-alert-{os.getpid()}-{time.time_ns()}"
    env = dict(os.environ, OPENPILOT_PREFIX=prefix, USE_MSGQ_PREFIX="true", SP_HOST_RUNTIME="1")
    env.pop("CEREAL_FAKE", None)
    receiver = """import time
from openpilot.cereal import messaging
from openpilot.starpilot.ui.runtime_snapshot import current_message, _alert
sm = messaging.SubMaster(['selfdriveState'], ignore_alive=['selfdriveState'])
seen = []
deadline = time.monotonic() + 5
while time.monotonic() < deadline:
  sm.update(100)
  if not sm.updated['selfdriveState']:
    continue
  msg = current_message(sm, 'selfdriveState', time.monotonic_ns())
  if msg is None:
    continue
  visual = _alert(msg)
  if visual.size.value == 'full':
    assert visual.critical and visual.text1 == 'TAKE CONTROL IMMEDIATELY'
    seen.append('full')
  elif visual.size.value == 'none' and 'full' in seen:
    seen.append('clear')
    break
assert seen[-2:] == ['full', 'clear'], seen
"""
    with owned_ipc_namespace(prefix):
      subscriber = subprocess.Popen([sys.executable, "-c", receiver], env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True)
      publisher = subprocess.Popen([sys.executable, "-m", "openpilot.tools.replay.alert_demo",
                                    "--delay", ".2", "--hold", ".5"], env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
      try:
        stdout, stderr = subscriber.communicate(timeout=7)
        self.assertEqual(subscriber.returncode, 0, stdout + stderr)
        self.assertIsNone(publisher.poll(), "Preview publisher must remain owned after clearing")
      finally:
        if subscriber.poll() is None:
          subscriber.kill()
          subscriber.wait(timeout=2)
        if publisher.poll() is None:
          publisher.terminate()
        publisher.communicate(timeout=3)

  def test_alert_module_refuses_unowned_namespace_before_publishing(self):
    env = dict(os.environ, SP_HOST_RUNTIME="1", OPENPILOT_PREFIX="replay-missing-namespace")
    result = subprocess.run([sys.executable, "-m", "openpilot.tools.replay.alert_demo", "--delay", "0"],
                            env=env, capture_output=True, text=True, check=False, timeout=5)
    self.assertEqual(result.returncode, 2)
    self.assertIn("isolated host replay session", result.stderr)

  def test_local_first_log_choice_does_not_fetch(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "private.rlog.zst"
      path.write_bytes(b"fixture")
      self.assertEqual(first_log_identifier(parse_replay_args([str(path)])), str(path))
      self.assertIsNotNone(first_log_identifier(parse_replay_args(["--demo"])))

  def test_data_dir_uses_native_timestamp_segment_layout_without_remote_fallback(self):
    route = "0123456789abcdef/2024-01-02--03-04-05/0"
    with tempfile.TemporaryDirectory() as directory:
      segment = Path(directory) / "2024-01-02--03-04-05--0"
      segment.mkdir()
      local = segment / "rlog.zst"
      local.write_bytes(b"fixture")
      args = parse_replay_args(["--data_dir", directory, route])
      self.assertEqual(first_log_identifier(args), str(local))
      local.unlink()
      self.assertIsNone(first_log_identifier(args))

  def test_seed_only_registered_display_booleans_in_disposable_params(self):
    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, OPENPILOT_PREFIX="replay-test-seed"):
      params = Params(directory)
      entries = [SimpleNamespace(key="IsMetric", value=b"1"), SimpleNamespace(key="HideSpeed", value=b"0"),
                 SimpleNamespace(key="HideMaxSpeed", value=b"not-a-bool"),
                 SimpleNamespace(key="AccessToken", value=b"secret")]
      init = SimpleNamespace(params=SimpleNamespace(entries=entries))
      self.assertEqual(seed_preview(init, params), 2)
      self.assertIs(params.get("IsMetric"), True)
      self.assertIs(params.get("HideSpeed"), False)
      self.assertIsNone(params.get("HideMaxSpeed"))
      self.assertIsNone(params.get("AccessToken"))
      self.assertIs(params.get("OpenpilotEnabledToggle"), True)

  def test_seed_uses_replay_namespace_not_runner_namespace(self):
    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, OPENPILOT_PREFIX="starpilot-dev-original"):
      init = SimpleNamespace(params=SimpleNamespace(entries=[SimpleNamespace(key="IsMetric", value=b"1")]))
      self.assertEqual(seed_replay_params(init, directory, "replay-target"), 1)
      self.assertEqual(os.environ["OPENPILOT_PREFIX"], "starpilot-dev-original")
      self.assertEqual((Path(directory) / "replay-target" / "IsMetric").read_bytes(), b"1")
      self.assertFalse((Path(directory) / "starpilot-dev-original").exists())

  def test_replay_only_does_not_fetch_route_metadata(self):
    for ui_args in (["--replay-only"], ["--ui=none"]):
      with self.subTest(ui_args=ui_args), tempfile.TemporaryDirectory() as directory:
        private = Path(directory) / "params"
        env = {"SP_HOST_RUNTIME": "1", "SP_HOST_PARAMS_ROOT": str(private), "PARAMS_ROOT": str(private),
               "SP_HOST_PREFIX": "starpilot-dev-host", "OPENPILOT_PREFIX": "starpilot-dev-host"}
        with patch.dict(os.environ, env), \
             patch.object(Path, "is_file", return_value=True), \
             patch("openpilot.tools.replay.onroad.os.access", return_value=True), \
             patch("openpilot.tools.replay.onroad_config.route_init_data", side_effect=AssertionError("fetched")), \
             patch("openpilot.tools.replay.onroad.supervise", return_value=0) as owned:
          self.assertEqual(run(parse_onroad_args([*ui_args, "--prefix", "replay-onlyfixture", "--demo"])), 0)
        self.assertEqual(owned.call_count, 1)
        self.assertFalse((Path(directory) / "replay-session-replay-onlyfixture").exists())

  def test_replay_exit_reaps_other_child(self):
    with tempfile.TemporaryDirectory() as directory:
      marker = Path(directory) / "terminated"
      waiting = "; ".join(("import signal,time,sys",
                            "signal.signal(signal.SIGTERM, lambda *_: (open(sys.argv[1], 'w').write('yes'), sys.exit(0)))",
                            "time.sleep(10)"))
      exiting = "import time; time.sleep(.2)"
      result = supervise([sys.executable, "-c", exiting], [[sys.executable, "-c", waiting, str(marker)]], dict(os.environ))
      self.assertEqual(result, 0)
      self.assertEqual(marker.read_text(), "yes")

  def test_termination_reaps_replay_and_ui(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      ready = root / "ready"
      replay_stopped = root / "replay-stopped"
      ui_stopped = root / "ui-stopped"
      worker = "; ".join(("import signal,time,sys", "from pathlib import Path",
                          "Path(sys.argv[1]).write_text('ready')",
                          "signal.signal(signal.SIGTERM, lambda *_: (Path(sys.argv[2]).write_text('stopped'), sys.exit(0)))",
                          "time.sleep(20)"))
      call = "raise SystemExit(supervise([sys.executable,'-c',worker,paths[0],paths[1]]," + \
             "[[sys.executable,'-c',worker,paths[2],paths[3]]],dict(os.environ)))"
      supervisor = "; ".join(("import os,sys", "from openpilot.tools.replay.onroad import supervise",
                              "worker=sys.argv[1]", "paths=sys.argv[2:]", call))
      proc = subprocess.Popen([sys.executable, "-c", supervisor, worker, str(ready), str(replay_stopped),
                               str(root / "ui-ready"), str(ui_stopped)], env=dict(os.environ))
      try:
        deadline = time.monotonic() + 5
        while not (ready.exists() and (root / "ui-ready").exists()) and time.monotonic() < deadline:
          time.sleep(.02)
        self.assertTrue(ready.exists() and (root / "ui-ready").exists())
        proc.send_signal(signal.SIGTERM)
        self.assertEqual(proc.wait(timeout=5), 143)
        self.assertEqual(replay_stopped.read_text(), "stopped")
        self.assertEqual(ui_stopped.read_text(), "stopped")
      finally:
        if proc.poll() is None:
          proc.kill()
          proc.wait(timeout=2)
