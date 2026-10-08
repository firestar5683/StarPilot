"""Run replay and the selected native desktop UI(s) in one private host session."""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import os
from pathlib import Path
import re
import secrets
import signal
import shutil
import subprocess
import sys
import tempfile
import time

USAGE = """Usage: ./onroad [jobs] [--c3|--c4|--all|--replay-only] [--params /saved/params] [--alert] [--cem] [--csc] [--prefix replay-NAME] <replay args>
Replay arguments include a route or --demo, --start, --cache, --playback, --data_dir and --no-loop.
The native replay terminal provides playback controls. Route playback may read/download the route you request.
--alert previews a synthetic visual critical alert; it does not publish car control.
--cem and --csc preview synthetic onroad visuals in the selected native UI only.
Old --nav, --offroad and --galaxy demos are not available in this port.
--params supplements recorded settings with a read-only snapshot, including unlogged layout preferences.
"""
UNAVAILABLE = frozenset(("--nav", "-nav", "--offroad", "--galaxy"))
PREFIX_RE = re.compile(r"replay-[A-Za-z0-9_-]{1,48}\Z")


@dataclass(frozen=True)
class OnroadPlan:
  targets: tuple[str, ...]
  explicit: bool
  replay_only: bool
  prefix: str | None
  replay_args: tuple[str, ...]
  alert: bool = False
  visual_preview: frozenset[str] = frozenset()
  params_snapshot: str | None = None


def _block_alert_service(args: tuple[str, ...]) -> list[str]:
  """Merge the one owned publisher exclusion with a user's existing replay block list."""
  result: list[str] = []
  blocked: list[str] = []
  index = 0
  while index < len(args):
    arg = args[index]
    if arg in ("-b", "--block"):
      blocked.extend(args[index + 1].split(","))
      index += 2
      continue
    if arg.startswith("--block="):
      blocked.extend(arg.partition("=")[2].split(","))
    else:
      result.append(arg)
    index += 1
  services = [service for service in (*blocked, "selfdriveState") if service]
  return ["-b", ",".join(dict.fromkeys(services)), *result]


def parse_onroad_args(args: list[str]) -> OnroadPlan:
  from openpilot.tools.replay.onroad_config import parse_replay_args
  targets: list[str] = []
  explicit = False
  replay_only = False
  alert = False
  visual_preview: set[str] = set()
  prefix = None
  params_snapshot = None
  replay_args: list[str] = []
  index = 0
  while index < len(args):
    arg = args[index]
    if arg == "--":
      replay_args.extend(args[index + 1:])
      break
    if arg in UNAVAILABLE:
      raise ValueError(f"{arg} has no current producer; this developer preview does not start a substitute")
    if arg in ("-alert", "--alert", "--alert-demo"):
      alert = True
      index += 1
      continue
    if arg in ("--cem", "--mici-widget-demo", "--widget-demo"):
      visual_preview.add("cem")
      index += 1
      continue
    if arg in ("--csc", "--csc-demo"):
      visual_preview.add("csc")
      index += 1
      continue
    if arg in ("--c3", "--c4", "--all", "--replay-only"):
      if arg == "--all":
        targets.extend(("c3", "c4"))
        explicit = True
      elif arg == "--replay-only":
        replay_only = True
      else:
        targets.append(arg.removeprefix("--"))
        explicit = True
    elif arg == "--params" or arg.startswith("--params="):
      if arg == "--params":
        if index + 1 >= len(args):
          raise ValueError("missing --params directory")
        params_snapshot = args[index + 1]
        index += 1
      else:
        params_snapshot = arg.partition("=")[2]
      if not params_snapshot or not Path(params_snapshot).is_absolute():
        raise ValueError("--params must name an absolute directory")
    elif arg in ("--prefix", "-p"):
      if index + 1 >= len(args):
        raise ValueError("missing --prefix value")
      prefix = args[index + 1]
      index += 1
    elif arg.startswith("--prefix="):
      prefix = arg.partition("=")[2]
    elif arg.startswith("--ui=") or arg == "--ui":
      if arg == "--ui":
        if index + 1 >= len(args):
          raise ValueError("missing --ui value")
        selection = args[index + 1]
        index += 1
      else:
        selection = arg.partition("=")[2]
      raw = selection.replace(" ", "").lower()
      if raw == "all":
        targets.extend(("c3", "c4"))
      elif raw != "none":
        choices = raw.split(",")
        if not choices or any(value not in ("c3", "c4") for value in choices):
          raise ValueError("--ui accepts c3, c4, all, or none")
        targets.extend(choices)
      explicit = True
    else:
      replay_args.append(arg)
    index += 1
  if prefix is not None and PREFIX_RE.fullmatch(prefix) is None:
    raise ValueError("--prefix must be replay-NAME with letters, digits, _ or -")
  if any(arg in ("-p", "--prefix") or arg.startswith("--prefix=") for arg in replay_args):
    raise ValueError("Replay prefix must be set before --, so the UI and replay share one isolated namespace")
  if not replay_args:
    raise ValueError("a route or --demo is required")
  parsed = parse_replay_args(replay_args)
  if parsed.route is None:
    raise ValueError("a route or --demo is required")
  if replay_only:
    targets = []
  if (alert or visual_preview) and (replay_only or (explicit and not targets)):
    raise ValueError("Visual previews require a native UI")
  return OnroadPlan(tuple(name for name in ("c3", "c4") if name in targets), explicit, replay_only,
                    prefix, tuple(replay_args), alert, frozenset(visual_preview), params_snapshot)


def _private_prefix(requested: str | None) -> str:
  return requested if requested is not None else "replay-" + secrets.token_hex(8)


def _session_marker(private_root: Path, prefix: str) -> Path:
  return private_root / f"replay-session-{prefix}"


def _ipc_root(prefix: str) -> Path:
  return Path("/tmp" if sys.platform == "darwin" else "/dev/shm") / f"msgq_{prefix}"


@contextmanager
def owned_ipc_namespace(prefix: str):
  """Create only this session's native msgq parent, then remove it after children exit."""
  root = _ipc_root(prefix)
  try:
    root.mkdir(mode=0o700)
  except FileExistsError as error:
    raise RuntimeError(f"Replay prefix already has an IPC namespace: {prefix}") from error
  try:
    yield root
  finally:
    shutil.rmtree(root)


@contextmanager
def _parent_prefix(prefix: str):
  previous = os.environ.get("OPENPILOT_PREFIX")
  os.environ["OPENPILOT_PREFIX"] = prefix
  try:
    yield
  finally:
    if previous is None:
      os.environ.pop("OPENPILOT_PREFIX", None)
    else:
      os.environ["OPENPILOT_PREFIX"] = previous


def seed_replay_params(init_data, params_root: str, prefix: str, snapshot: str | None = None) -> int:
  from openpilot.common.params import Params
  from openpilot.tools.replay.onroad_config import seed_preview
  with _parent_prefix(prefix):
    return seed_preview(init_data, Params(params_root), snapshot)


def _stop(children: list[subprocess.Popen]) -> None:
  for child in reversed(children):
    if child.poll() is None:
      child.terminate()
  deadline = time.monotonic() + 3.0
  for child in reversed(children):
    if child.poll() is None:
      try:
        child.wait(timeout=max(0.01, deadline - time.monotonic()))
      except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=1.0)


def _exit_status(code: int) -> int:
  return code if code >= 0 else 128 - code


def supervise(replay_command: list[str], ui_commands: list[list[str]], env: dict[str, str], *,
              demo_commands: list[list[str]] | None = None,
              spawn=subprocess.Popen) -> int:
  children: list[subprocess.Popen] = []
  shutdown_signal: int | None = None
  def interrupted(signum: int, _frame) -> None:
    nonlocal shutdown_signal
    shutdown_signal = signum
  old_handlers = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
  try:
    children.append(spawn(replay_command, env=env))
    if shutdown_signal is not None:
      return 128 + shutdown_signal
    first_status = children[0].poll()
    if first_status is not None:
      return _exit_status(first_status)
    for command in [*ui_commands, *(demo_commands or ())]:
      children.append(spawn(command, env=env))
      if shutdown_signal is not None:
        return 128 + shutdown_signal
    while True:
      if shutdown_signal is not None:
        return 128 + shutdown_signal
      for index, child in enumerate(children):
        status = child.poll()
        if status is not None:
          if index >= 1 + len(ui_commands) and status == 0:
            return 1  # A clean exit from a demo publisher still leaves the preview unsupported.
          return _exit_status(status)
      time.sleep(0.1)
  finally:
    _stop(children)
    for sig, handler in old_handlers.items():
      signal.signal(sig, handler)


def run(plan: OnroadPlan) -> int:
  from openpilot.tools.replay.onroad_config import parse_replay_args, route_init_data, select_ui_target, replay_device_type
  from openpilot.starpilot.ui.host_launch import launch_environment
  from openpilot.starpilot.ui.developer_preview import encode_flags
  from openpilot.starpilot.ui.presentation import Profile
  source = dict(os.environ)
  if source.get("SP_HOST_RUNTIME") != "1":
    raise RuntimeError("Start replay through ./onroad in the isolated host runtime")
  raw_host_params = source.get("SP_HOST_PARAMS_ROOT", "")
  if not raw_host_params or not Path(raw_host_params).is_absolute():
    raise RuntimeError("Host replay requires an isolated absolute SP_HOST_PARAMS_ROOT")
  host_params = Path(raw_host_params).resolve()
  if host_params != Path(source.get("PARAMS_ROOT", "")).resolve():
    raise RuntimeError("Host replay Params root differs from the isolated runner root")
  prefix = _private_prefix(plan.prefix)
  marker = _session_marker(host_params.parent, prefix)
  if marker.exists():
    raise RuntimeError(f"Replay prefix already has a host session: {prefix}")
  if _ipc_root(prefix).exists() or _ipc_root(prefix).is_symlink():
    raise RuntimeError(f"Replay prefix already has an IPC namespace: {prefix}")
  repo = Path(__file__).resolve().parents[3]
  replay_binary = repo / "openpilot/tools/replay/replay"
  if not replay_binary.is_file() or not os.access(replay_binary, os.X_OK):
    raise RuntimeError("Host replay binary is missing; rebuild the isolated host runtime")
  no_ui = plan.replay_only or (plan.explicit and not plan.targets)
  replay_args = parse_replay_args(plan.replay_args)
  init_data = None if no_ui else route_init_data(replay_args)
  if not no_ui and not plan.explicit and replay_args.data_dir and init_data is None:
    raise RuntimeError("Local replay has no readable initData; choose --c3 or --c4 explicitly")
  targets = plan.targets if plan.explicit or plan.replay_only else (select_ui_target(init_data),)
  preview = encode_flags(plan.visual_preview)
  if targets:
    for profile in (Profile.LARGE if name == "c3" else Profile.COMPACT for name in targets):
      launch_environment(profile, {**source, "OPENPILOT_PREFIX": prefix,
                                   "PARAMS_ROOT": str(host_params),
                                   "SP_ONROAD_VISUAL_PREVIEW": preview})  # font/asset contract before children
  host_params.parent.mkdir(parents=True, exist_ok=True)
  with tempfile.TemporaryDirectory(prefix="replay-params-", dir=host_params.parent) as params_root:
    env = {**source, "OPENPILOT_PREFIX": prefix, "PARAMS_ROOT": params_root,
           "SP_ONROAD_VISUAL_PREVIEW": preview, "SP_REPLAY_DEVICE_TYPE": replay_device_type(init_data)}
    env["COMMA_CACHE"] = str(host_params.parent / "download-cache")
    restored = seed_replay_params(init_data, params_root, prefix, plan.params_snapshot)
    marker.mkdir(mode=0o700)
    try:
      ui_commands = [[sys.executable, "-m", "openpilot.starpilot.ui.host_launch",
                      "large" if target == "c3" else "compact"] for target in targets]
      print(f"Replay prefix {prefix}; native UI: {', '.join(targets) if targets else 'none'}", flush=True)
      if targets:
        print(f"Recorded device: {env['SP_REPLAY_DEVICE_TYPE']}; restored {restored} saved settings", flush=True)
        if plan.params_snapshot is None:
          print("Unlogged settings use defaults; --params /saved/params supplies an exact saved layout and preferences.", flush=True)
      with owned_ipc_namespace(prefix) as ipc_root:
        from openpilot.tools.replay.display_clock import RECORD
        clock_path = ipc_root / "display-clock"
        fd = os.open(clock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
          os.ftruncate(fd, RECORD.size)
        finally:
          os.close(fd)
        env["SP_REPLAY_CLOCK_PATH"] = str(clock_path)
        replay_command = [str(replay_binary), *(_block_alert_service(plan.replay_args) if plan.alert else plan.replay_args)]
        demos = [[sys.executable, "-m", "openpilot.tools.replay.alert_demo"]] if plan.alert else []
        return supervise(replay_command, ui_commands, env, demo_commands=demos)
    finally:
      marker.rmdir()


def main(argv: list[str] | None = None) -> int:
  args = list(sys.argv[1:] if argv is None else argv)
  if any(arg in ("--help", "-h") for arg in args):
    print(USAGE)
    return 0
  try:
    return run(parse_onroad_args(args))
  except (KeyError, OSError, RuntimeError, ValueError) as error:
    print(f"onroad: {error}", file=sys.stderr)
    return 2


if __name__ == "__main__":
  raise SystemExit(main())
