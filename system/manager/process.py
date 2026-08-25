import importlib
import os
import signal
import stat as statmod
import struct
import threading
import time
import subprocess
from pathlib import Path
from collections.abc import Callable, ValuesView
from abc import ABC, abstractmethod
from multiprocessing import Process
from types import SimpleNamespace

from setproctitle import setproctitle

from cereal import car, log
import cereal.messaging as messaging
import openpilot.system.sentry as sentry
from openpilot.common.basedir import BASEDIR
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.common.watchdog import WATCHDOG_FN

ENABLE_WATCHDOG = os.getenv("NO_WATCHDOG") is None

DEBUG_ENV_KEYS = (
  "XDG_RUNTIME_DIR",
  "WAYLAND_DISPLAY",
  "WAYLAND_SOCKET",
  "QT_QPA_PLATFORM",
  "QT_WAYLAND_SHELL_INTEGRATION",
  "QT_WAYLAND_DISABLE_WINDOWDECORATION",
)


def _debug_dump_dir() -> Path:
  for candidate in (Path("/data/log"), Path("/tmp")):
    if candidate.is_dir() and os.access(candidate, os.W_OK):
      return candidate
  return Path.cwd()


def _truncate_text(text: str, max_chars: int = 32768) -> str:
  if len(text) <= max_chars:
    return text
  return text[:max_chars] + "\n<truncated>\n"


def _read_text_file(path: Path, max_bytes: int = 16384) -> str:
  try:
    data = path.read_bytes()
  except OSError as e:
    return f"<read failed: {e}>"

  if len(data) > max_bytes:
    data = data[:max_bytes] + b"\n<truncated>\n"

  return data.decode("utf-8", errors="replace")


def _read_proc_cmdline(proc_dir: Path, max_bytes: int = 4096) -> str:
  try:
    data = (proc_dir / "cmdline").read_bytes()
  except OSError as e:
    return f"<read failed: {e}>"

  cmdline = data.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()
  return _truncate_text(cmdline or "<empty>", max_bytes)


def _read_proc_environ(proc_dir: Path) -> dict[str, str]:
  try:
    data = (proc_dir / "environ").read_bytes()
  except OSError:
    return {}

  env = {}
  for item in data.split(b"\0"):
    if not item or b"=" not in item:
      continue
    key, value = item.split(b"=", 1)
    env[key.decode("utf-8", errors="replace")] = value.decode("utf-8", errors="replace")
  return env


def _format_env_subset(env: dict[str, str]) -> str:
  if not env:
    return "<empty>"

  lines = [f"{key}={env[key]}" for key in DEBUG_ENV_KEYS if key in env]
  return "\n".join(lines) if lines else "<no relevant keys>"


def _coerce_subprocess_output(data) -> str:
  if data is None:
    return ""
  if isinstance(data, bytes):
    return data.decode("utf-8", errors="replace")
  return data


def _run_debug_command(cmd: str, timeout: float = 1.5, max_chars: int = 32768) -> str:
  try:
    result = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True, timeout=timeout)
    parts = [f"$ {cmd}", f"<exit {result.returncode}>"]
    if result.stdout:
      parts.append(result.stdout.rstrip())
    if result.stderr:
      parts.extend(["[stderr]", result.stderr.rstrip()])
    if len(parts) == 2:
      parts.append("<no output>")
    return _truncate_text("\n".join(parts), max_chars)
  except subprocess.TimeoutExpired as e:
    stdout = _coerce_subprocess_output(e.stdout).rstrip()
    stderr = _coerce_subprocess_output(e.stderr).rstrip()
    parts = [f"$ {cmd}", f"<timed out after {timeout:.1f}s>"]
    if stdout:
      parts.append(stdout)
    if stderr:
      parts.extend(["[stderr]", stderr])
    if len(parts) == 2:
      parts.append("<no output>")
    return _truncate_text("\n".join(parts), max_chars)


def _read_proc_start_wall_time(proc_dir: Path) -> str:
  try:
    stat_text = (proc_dir / "stat").read_text()
    rparen = stat_text.rfind(")")
    fields = stat_text[rparen + 2:].split()
    start_ticks = int(fields[19])
    uptime_s = float(Path("/proc/uptime").read_text().split()[0])
    hz = os.sysconf("SC_CLK_TCK")
    start_time_s = time.time() - uptime_s + (start_ticks / hz)
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(start_time_s))
  except Exception as e:
    return f"<parse failed: {e}>"


def _find_process_dirs(match_terms: tuple[str, ...]) -> list[Path]:
  proc_root = Path("/proc")
  try:
    proc_dirs = sorted((p for p in proc_root.iterdir() if p.name.isdigit()), key=lambda p: int(p.name))
  except OSError:
    return []

  matches = []
  for proc_dir in proc_dirs:
    comm = _read_text_file(proc_dir / "comm", 256).strip()
    cmdline = _read_proc_cmdline(proc_dir, 2048)
    haystacks = (comm, cmdline)
    if any(term in haystack for term in match_terms for haystack in haystacks):
      matches.append(proc_dir)
  return matches


def _read_symlink(path: Path) -> str:
  try:
    return os.readlink(path)
  except OSError as e:
    return f"<read failed: {e}>"


def _describe_path(path: Path) -> str:
  try:
    st = path.stat()
  except OSError as e:
    return f"path={path}\n<stat failed: {e}>"

  mode = statmod.filemode(st.st_mode)
  if statmod.S_ISSOCK(st.st_mode):
    path_type = "socket"
  elif statmod.S_ISDIR(st.st_mode):
    path_type = "dir"
  elif statmod.S_ISREG(st.st_mode):
    path_type = "file"
  else:
    path_type = "other"

  return "\n".join([
    f"path={path}",
    f"type={path_type}",
    f"mode={mode}",
    f"inode={st.st_ino}",
    f"size={st.st_size}",
    f"mtime={time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(st.st_mtime))}",
    f"mtime_ns={st.st_mtime_ns}",
    f"ctime_ns={st.st_ctime_ns}",
  ])


def _proc_net_unix_matches(path: Path) -> str:
  path_str = str(path)
  try:
    rows = [line for line in Path("/proc/net/unix").read_text().splitlines() if path_str in line]
  except OSError as e:
    return f"<read failed: {e}>"

  return "\n".join(rows) if rows else "<no matches>"


def _resolve_wayland_socket(runtime_dir: Path | None, display: str | None) -> Path | None:
  if not display:
    return runtime_dir / "wayland-0" if runtime_dir is not None else None

  socket_path = Path(display)
  if socket_path.is_absolute():
    return socket_path
  if runtime_dir is None:
    return None
  return runtime_dir / socket_path


def _append_ui_watchdog_context(lines: list[str], ui_proc_dir: Path) -> None:
  ui_env = _read_proc_environ(ui_proc_dir)
  weston_procs = _find_process_dirs(("weston",))
  weston_envs = [_read_proc_environ(proc_dir) for proc_dir in weston_procs]

  lines.extend([
    "== ui proc cmdline ==",
    _read_proc_cmdline(ui_proc_dir),
    "",
    "== ui proc exe ==",
    _read_symlink(ui_proc_dir / "exe"),
    "",
    "== ui proc env ==",
    _format_env_subset(ui_env),
    "",
  ])

  for proc_dir, env in zip(weston_procs, weston_envs):
    lines.extend([
      f"== weston process {proc_dir.name} ==",
      "-- cmdline --",
      _read_proc_cmdline(proc_dir),
      "",
      "-- exe --",
      _read_symlink(proc_dir / "exe"),
      "",
      "-- start wall time --",
      _read_proc_start_wall_time(proc_dir),
      "",
      "-- status --",
      _read_text_file(proc_dir / "status"),
      "",
      "-- wchan --",
      _read_text_file(proc_dir / "wchan", 1024),
      "",
      "-- syscall --",
      _read_text_file(proc_dir / "syscall", 2048),
      "",
      "-- env --",
      _format_env_subset(env),
      "",
    ])

  runtime_dirs: set[Path] = set()
  socket_paths: set[Path] = set()

  for env in (ui_env, *weston_envs):
    runtime_dir = Path(env["XDG_RUNTIME_DIR"]) if env.get("XDG_RUNTIME_DIR") else None
    if runtime_dir is not None:
      runtime_dirs.add(runtime_dir)
    socket_path = _resolve_wayland_socket(runtime_dir, env.get("WAYLAND_DISPLAY"))
    if socket_path is not None:
      socket_paths.add(socket_path)

  if not runtime_dirs:
    for candidate in (Path("/run/user/1000"), Path("/tmp")):
      if candidate.exists():
        runtime_dirs.add(candidate)

  for runtime_dir in sorted(runtime_dirs):
    lines.extend([
      f"== runtime dir {runtime_dir} ==",
      _describe_path(runtime_dir),
      "",
    ])

    candidates = {path for path in socket_paths if path.parent == runtime_dir}
    if runtime_dir.exists():
      candidates.update(runtime_dir.glob("wayland-*"))
      candidates.update(runtime_dir.glob("weston*"))

    for candidate in sorted(candidates):
      lines.extend([
        f"-- wayland path {candidate.name} --",
        _describe_path(candidate),
        "-- /proc/net/unix --",
        _proc_net_unix_matches(candidate),
        "",
      ])

  for socket_path in sorted(socket_paths):
    if socket_path.parent not in runtime_dirs:
      lines.extend([
        f"== wayland path {socket_path} ==",
        _describe_path(socket_path),
        "-- /proc/net/unix --",
        _proc_net_unix_matches(socket_path),
        "",
      ])

  commands = [
    (
      "== systemctl weston ==",
      "systemctl show weston.service weston-ready.service "
      "--property=Id,ActiveState,SubState,MainPID,ExecMainStartTimestamp,ExecMainStartTimestampMonotonic,ExecMainStatus "
      "--no-pager 2>/dev/null || true",
      1.5,
    ),
    (
      "== journalctl weston ==",
      "journalctl -u weston.service -u weston-ready.service -n 120 --no-pager 2>&1 || true",
      1.5,
    ),
    (
      "== recent swaglog weston/ui ==",
      "grep -RinE 'Watchdog timeout for ui|weston|Wayland|EGL|gbm|drm|GPU|segfault|SIGSEGV|OOM|fatal' "
      "/data/log/swaglog* 2>/dev/null | tail -n 160 || true",
      1.5,
    ),
    (
      "== dmesg weston/gpu ==",
      "dmesg 2>/dev/null | grep -Ei 'drm|gpu|msm|kgsl|weston|wayland|segfault|oom|hang' | tail -n 160 || true",
      1.5,
    ),
  ]

  for title, cmd, timeout in commands:
    lines.extend([
      title,
      _run_debug_command(cmd, timeout=timeout),
      "",
    ])


def _capture_watchdog_debug_dump(name: str, pid: int, reason: str, dt: float) -> None:
  try:
    proc_dir = Path(f"/proc/{pid}")
    if not proc_dir.exists():
      cloudlog.error(f"watchdog debug dump skipped for {name}: /proc/{pid} no longer exists")
      return

    dump_path = _debug_dump_dir() / f"{name}_watchdog_dump_{pid}_{time.monotonic_ns()}.log"
    lines = [
      f"name={name}",
      f"pid={pid}",
      f"dt={dt:.3f}",
      f"reason={reason}",
      f"wall_time={time.strftime('%Y-%m-%dT%H:%M:%S%z')}",
      f"watchdog_file={WATCHDOG_FN}{pid}",
      "",
      "== /proc/status ==",
      _read_text_file(proc_dir / "status"),
      "",
      "== /proc/wchan ==",
      _read_text_file(proc_dir / "wchan", 1024),
      "",
      "== /proc/syscall ==",
      _read_text_file(proc_dir / "syscall", 2048),
      "",
    ]

    watchdog_file = Path(f"{WATCHDOG_FN}{pid}")
    lines.extend([
      "== watchdog file ==",
      _describe_path(watchdog_file),
      "",
    ])

    if name == "ui":
      _append_ui_watchdog_context(lines, proc_dir)

    task_dir = proc_dir / "task"
    try:
      task_entries = sorted(task_dir.iterdir(), key=lambda p: int(p.name))
    except OSError as e:
      task_entries = []
      lines.extend([
        "== /proc/task ==",
        f"<read failed: {e}>",
        "",
      ])

    for entry in task_entries:
      lines.extend([
        f"== thread {entry.name} ==",
        "-- comm --",
        _read_text_file(entry / "comm", 1024),
        "",
        "-- wchan --",
        _read_text_file(entry / "wchan", 1024),
        "",
        "-- syscall --",
        _read_text_file(entry / "syscall", 2048),
        "",
        "-- status --",
        _read_text_file(entry / "status"),
        "",
        "-- stack --",
        _read_text_file(entry / "stack"),
        "",
      ])

    try:
      dump_path.write_text("\n".join(lines))
      cloudlog.error(f"Wrote watchdog debug dump for {name} to {dump_path}")
    except OSError as e:
      cloudlog.error(f"failed to write watchdog debug dump for {name} to {dump_path}: {e}")
  except Exception:
    cloudlog.exception(f"failed to capture watchdog debug dump for {name} pid={pid}")


def launcher(proc: str, name: str, nice: int | None = None) -> None:
  try:
    if nice is not None:
      os.nice(nice)

    # import the process
    mod = importlib.import_module(proc)

    # rename the process
    setproctitle(proc)

    # create new context since we forked
    messaging.reset_context()

    # add daemon name tag to logs
    cloudlog.bind(daemon=name)
    sentry.set_tag("daemon", name)

    # exec the process
    mod.main()
  except KeyboardInterrupt:
    cloudlog.warning(f"child {proc} got SIGINT")
  except Exception:
    # can't install the crash handler because sys.excepthook doesn't play nice
    # with threads, so catch it here.
    sentry.capture_exception()
    raise


def nativelauncher(pargs: list[str], cwd: str, name: str, nice: int | None = None) -> None:
  if nice is not None:
    os.nice(nice)

  os.environ['MANAGER_DAEMON'] = name

  # exec the process
  os.chdir(cwd)
  os.execvp(pargs[0], pargs)


def join_process(process: Process, timeout: float) -> None:
  # Process().join(timeout) will hang due to a python 3 bug: https://bugs.python.org/issue28382
  # We have to poll the exitcode instead
  t = time.monotonic()
  while time.monotonic() - t < timeout and process.exitcode is None:
    time.sleep(0.001)


class ManagerProcess(ABC):
  daemon = False
  sigkill = False
  should_run: Callable[[bool, Params, car.CarParams, SimpleNamespace], bool]
  proc: Process | None = None
  enabled = True
  name = ""

  last_watchdog_time = 0
  watchdog_max_dt: int | None = None
  watchdog_seen = False
  shutting_down = False

  @abstractmethod
  def prepare(self) -> None:
    pass

  @abstractmethod
  def start(self) -> None:
    pass

  def restart(self) -> None:
    self.stop(sig=signal.SIGKILL)
    self.start()

  def capture_watchdog_debug_dump(self, reason: str, dt: float) -> None:
    if self.proc is None or self.proc.pid is None:
      return

    _capture_watchdog_debug_dump(self.name, self.proc.pid, reason, dt)

  def capture_watchdog_debug_dump_async(self, reason: str, dt: float) -> None:
    if self.proc is None or self.proc.pid is None:
      return

    # Capture watchdog evidence in the background so managerState stays responsive.
    thread = threading.Thread(
      name=f"{self.name}_watchdog_dump",
      target=_capture_watchdog_debug_dump,
      args=(self.name, self.proc.pid, reason, dt),
      daemon=True,
    )
    thread.start()

  def check_watchdog(self, started: bool) -> None:
    if self.watchdog_max_dt is None or self.proc is None:
      return

    try:
      fn = WATCHDOG_FN + str(self.proc.pid)
      with open(fn, "rb") as f:
        self.last_watchdog_time = struct.unpack('Q', f.read())[0]
      self.watchdog_seen = True
    except Exception:
      if not self.watchdog_seen:
        return

    dt = time.monotonic() - self.last_watchdog_time / 1e9
    if dt > self.watchdog_max_dt and ENABLE_WATCHDOG:
      self.capture_watchdog_debug_dump_async(f"watchdog_timeout started={started}", dt)
      cloudlog.error(f"Watchdog timeout for {self.name} (exitcode {self.proc.exitcode}) restarting ({started=})")
      if isinstance(self, NativeProcess):
        sentry.capture_message(
          f"Native process watchdog timeout: {self.name}",
          level="fatal",
          tags={"process": self.name, "process_kind": "native", "failure": "watchdog"},
          extras={"pid": self.proc.pid, "watchdog_dt": dt, "started": started},
          flush_timeout=0.5,
        )
      self.restart()

  def stop(self, retry: bool = True, block: bool = True, sig: signal.Signals = None) -> int | None:
    if self.proc is None:
      return None

    if self.proc.exitcode is None:
      if not self.shutting_down:
        cloudlog.info(f"killing {self.name}")
        if sig is None:
          sig = signal.SIGKILL if self.sigkill else signal.SIGINT
        self.signal(sig)
        self.shutting_down = True

        if not block:
          return None

      join_process(self.proc, 5)

      # If process failed to die send SIGKILL
      if self.proc.exitcode is None and retry:
        cloudlog.info(f"killing {self.name} with SIGKILL")
        self.signal(signal.SIGKILL)
        self.proc.join()

    ret = self.proc.exitcode
    cloudlog.info(f"{self.name} is dead with {ret}")

    if self.proc.exitcode is not None:
      self.shutting_down = False
      self.proc = None

    return ret

  def signal(self, sig: int) -> None:
    if self.proc is None:
      return

    # Don't signal if already exited
    if self.proc.exitcode is not None and self.proc.pid is not None:
      return

    # Can't signal if we don't have a pid
    if self.proc.pid is None:
      return

    cloudlog.info(f"sending signal {sig} to {self.name}")
    os.kill(self.proc.pid, sig)

  def get_process_state_msg(self):
    state = log.ManagerState.ProcessState.new_message()
    state.name = self.name
    if self.proc:
      state.running = self.proc.is_alive()
      state.shouldBeRunning = self.proc is not None and not self.shutting_down
      state.pid = self.proc.pid or 0
      state.exitCode = self.proc.exitcode or 0
    return state


class NativeProcess(ManagerProcess):
  def __init__(self, name, cwd, cmdline, should_run, enabled=True, sigkill=False, watchdog_max_dt=None, nice=None):
    self.name = name
    self.cwd = cwd
    self.cmdline = cmdline
    self.should_run = should_run
    self.enabled = enabled
    self.sigkill = sigkill
    self.watchdog_max_dt = watchdog_max_dt
    self.nice = nice
    self.launcher = nativelauncher

  def prepare(self) -> None:
    pass

  def start(self) -> None:
    # In case we only tried a non blocking stop we need to stop it before restarting
    if self.shutting_down:
      self.stop()

    if self.proc is not None:
      return

    cwd = os.path.join(BASEDIR, self.cwd)
    cloudlog.info(f"starting process {self.name}")
    self.proc = Process(name=self.name, target=self.launcher, args=(self.cmdline, cwd, self.name, self.nice))
    self.proc.start()
    self.last_watchdog_time = 0
    self.watchdog_seen = False
    self.shutting_down = False


class PythonProcess(ManagerProcess):
  def __init__(self, name, module, should_run, enabled=True, sigkill=False, watchdog_max_dt=None, nice=None):
    self.name = name
    self.module = module
    self.should_run = should_run
    self.enabled = enabled
    self.sigkill = sigkill
    self.watchdog_max_dt = watchdog_max_dt
    self.nice = nice
    self.launcher = launcher

  def prepare(self) -> None:
    if self.enabled:
      cloudlog.info(f"preimporting {self.module}")
      start = time.monotonic()
      try:
        importlib.import_module(self.module)
      finally:
        line = f"SP_BOOT_TIMING preimport {self.name} module={self.module} +{time.monotonic() - start:.3f}s"
        try:
          with open(os.environ.get("SP_BOOT_TIMING_LOG", "/tmp/starpilot_boot_timing.log"), "a") as f:
            f.write(line + "\n")
        except OSError:
          pass
        cloudlog.warning(line)

  def start(self) -> None:
    # In case we only tried a non blocking stop we need to stop it before restarting
    if self.shutting_down:
      self.stop()

    if self.proc is not None:
      return

    # TODO: this is just a workaround for this tinygrad check:
    # https://github.com/tinygrad/tinygrad/blob/ac9c96dae1656dc220ee4acc39cef4dd449aa850/tinygrad/device.py#L26
    name = self.name if "modeld" not in self.name else "MainProcess"

    cloudlog.info(f"starting python {self.module}")
    self.proc = Process(name=name, target=self.launcher, args=(self.module, self.name, self.nice))
    self.proc.start()
    self.last_watchdog_time = 0
    self.watchdog_seen = False
    self.shutting_down = False


class DaemonProcess(ManagerProcess):
  """Python process that has to stay running across manager restart.
  This is used for athena so you don't lose SSH access when restarting manager."""
  def __init__(self, name, module, param_name, enabled=True):
    self.name = name
    self.module = module
    self.param_name = param_name
    self.enabled = enabled
    self.params = None

  @staticmethod
  def should_run(started, params, CP, starpilot_toggles):
    return True

  def prepare(self) -> None:
    pass

  def start(self) -> None:
    if self.params is None:
      self.params = Params()

    pid = self.params.get(self.param_name)
    if pid is not None:
      try:
        os.kill(int(pid), 0)
        with open(f'/proc/{pid}/cmdline') as f:
          if self.module in f.read():
            # daemon is running
            return
      except (OSError, FileNotFoundError):
        # process is dead
        pass

    cloudlog.info(f"starting daemon {self.name}")
    proc = subprocess.Popen(['python', '-m', self.module],
                               stdin=open('/dev/null'),
                               stdout=open('/dev/null', 'w'),
                               stderr=open('/dev/null', 'w'),
                               preexec_fn=os.setpgrp)

    self.params.put(self.param_name, proc.pid)

  def stop(self, retry=True, block=True, sig=None) -> None:
    pass


def ensure_running(procs: ValuesView[ManagerProcess], started: bool, params=None, CP: car.CarParams=None,
                   not_run: list[str] | None=None, starpilot_toggles: SimpleNamespace=None) -> list[ManagerProcess]:
  if not_run is None:
    not_run = []

  running = []
  for p in procs:
    # Reap crashed processes so they can be cleanly restarted below.
    if p.proc is not None and p.proc.exitcode is not None and not p.shutting_down:
      exitcode = p.proc.exitcode
      cloudlog.error(f"Process {p.name} crashed with exitcode {exitcode}, restarting")
      if isinstance(p, NativeProcess):
        sentry.capture_message(
          f"Native process crashed: {p.name}",
          level="fatal",
          tags={"process": p.name, "process_kind": "native"},
          extras={"exitcode": exitcode, "started": started},
          flush_timeout=0.5,
        )
      p.stop(retry=False)

    if p.enabled and p.name not in not_run and p.should_run(started, params, CP, starpilot_toggles):
      running.append(p)
    else:
      p.stop(block=False)

    p.check_watchdog(started)

  for p in running:
    p.start()

  return running
