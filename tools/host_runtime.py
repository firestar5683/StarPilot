#!/usr/bin/env python3
"""StarPilot desktop commands with an independent build tree, index and Params."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
HELP = """Usage: ./dev <command> [args...]
       ./tool <command> [args...]       ./tools/host <command> [args...]

  c3 / c4       Build and launch the large / compact StarPilot Raylib UI.
  onroad        Build replay and launch route UI(s); see ./onroad --help.
  replay        Build and run upstream replay.
  cabana        Build and run Cabana in its own concurrent cache.
  plotjuggler   Run PlotJuggler (alias: juggle).
  galaxy        Run authenticated Galaxy on loopback (optional --port).
  python        Run Python with current source and native extensions.
  pytest        Run pytest with current source and native extensions.
  shell         Open a shell in the isolated host worktree.
  sync [bucket] Refresh all caches, or shared/cabana, without launching tools.
  help          Show this help without installing or building anything.

Build/launch commands accept an optional leading jobs count, e.g. ./c3 8.
The host cache is .host_runtime/<system>-<architecture>/<bucket>/.
Native build artifacts, editable installs and Params stay in that cache.
Shared commands wait while another shared command is running; Cabana is separate.
./build remains the Linux ARM64 device build, including ./build --panda.
"""
COMMANDS = {'c3', 'c4', 'onroad', 'replay', 'cabana', 'plotjuggler', 'galaxy', 'python', 'pytest', 'shell', 'sync'}
BUCKET_ALIASES = dict.fromkeys(('shared', 'default', 'ui', 'c3', 'c4', 'onroad', 'replay', 'shell', 'plotjuggler', 'juggle'), 'shared')
BUCKET_ALIASES['cabana'] = 'cabana'
VENDORS = ('msgq_repo', 'opendbc_repo', 'rednose_repo', 'teleoprtc_repo', 'tinygrad_repo')
# Never inherit a device/cross compiler or another project's editable imports.
REMOVE_ENV = ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV', 'CC', 'CXX', 'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS',
              'LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH', 'PKG_CONFIG_PATH', 'CPATH', 'LIBRARY_PATH',
              'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR')
EXCLUDE_DIRS = {'.git', '.venv', '.venv-linux-arm64', '.host_runtime', '.comma_sysroot', '.cache', '__pycache__'}


def run(arguments, *, cwd, env=None, capture=False):
  return subprocess.run([str(arg) for arg in arguments], cwd=cwd, env=env, check=True,
                        stdout=subprocess.PIPE if capture else None, text=capture)


def git(root, *arguments):
  env = {key: value for key, value in os.environ.items() if key not in REMOVE_ENV}
  return run(['git', *arguments], cwd=root, env=env, capture=True).stdout


def parse(arguments):
  command = arguments[0] if arguments else 'help'
  if command in ('help', '-h', '--help'):
    return 'help', 0, []
  if command == 'juggle':
    command = 'plotjuggler'
  if command not in COMMANDS:
    raise ValueError(f'Unknown developer command: {command}. Run ./dev help.')
  args = list(arguments[1:])
  jobs = max(1, os.cpu_count() or 8)
  if command not in ('python', 'pytest', 'shell', 'sync') and args and args[0].isdigit():
    jobs = int(args.pop(0))
    if jobs < 1:
      raise ValueError('The jobs count must be positive.')
  if command == 'sync' and (len(args) > 1 or (args and args[0] not in BUCKET_ALIASES)):
    raise ValueError('Usage: ./dev sync [shared|cabana]')
  return command, jobs, args


def inside(path, root):
  """Reject cache symlinks escaping the disposable tree before any mutation."""
  if not path.resolve().is_relative_to(root.resolve()):
    raise RuntimeError(f'Cache path escapes its root: {path}')
  return path


def same_contents(source, destination):
  if not destination.is_file() or source.stat().st_size != destination.stat().st_size:
    return False
  with source.open('rb') as left, destination.open('rb') as right:
    while block := left.read(1024 * 1024):
      if block != right.read(len(block)):
        return False
  return True


class HostRuntime:
  def __init__(self, root, bucket, *, system=None, machine=None):
    self.root = Path(root).resolve()
    self.system = system or platform.system()
    machine = machine or platform.machine()
    if self.system not in ('Darwin', 'Linux'):
      raise RuntimeError('Desktop tools support macOS and Linux.')
    self.cache = self.root / '.host_runtime' / f'{self.system.lower()}-{machine}' / bucket
    if (self.root / '.host_runtime').is_symlink():
      raise RuntimeError('.host_runtime must be a local directory, not a symlink.')
    inside(self.cache, self.root / '.host_runtime')
    self.work = self.cache / 'worktree'
    self.venv = self.cache / 'venv'
    self.prefix = 'starpilot-dev-' + hashlib.sha256(str(self.cache).encode()).hexdigest()[:12]
    self.lock_fd = None

  @contextmanager
  def locked(self):
    self.cache.mkdir(parents=True, exist_ok=True)
    lock_path = inside(self.cache / 'lock', self.cache)
    with lock_path.open('a+') as lock:
      try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
      except BlockingIOError:
        print(f'Waiting for the {self.cache.name} host session to exit…', flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)
      lock.seek(0)
      lock.truncate()
      lock.write(str(os.getpid()))
      lock.flush()
      self.lock_fd = lock.fileno()
      try:
        yield
      finally:
        self.lock_fd = None
        fcntl.flock(lock, fcntl.LOCK_UN)

  def sync(self):
    inside(self.work, self.cache).mkdir(parents=True, exist_ok=True)
    # Include uncommitted development, exclude ignored native/device outputs.
    listed = git(self.root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0')
    paths = {name for name in listed if name and not (set(Path(name).parts) & EXCLUDE_DIRS)
             and not (set(Path(name).suffixes) & {'.a', '.so', '.dylib', '.o', '.os'})
             and (self.root / name).is_file()}
    manifest = inside(self.cache / 'source-files.json', self.cache)
    previous = set(json.loads(manifest.read_text())) if manifest.exists() else set()
    for name in sorted(previous - paths):
      path = inside(self.work / name, self.work)
      if path.is_file() or path.is_symlink():
        path.unlink()
    for name in sorted(paths):
      source = self.root / name
      destination = inside(self.work / name, self.work)
      destination.parent.mkdir(parents=True, exist_ok=True)
      if source.is_symlink():
        # Keep repository-relative links; never point the host cache at device builds.
        inside(source, self.root)
        target = os.readlink(source)
        if os.path.isabs(target):
          raise RuntimeError(f'Absolute source symlink is not portable: {name}')
        if destination.is_symlink() and os.readlink(destination) == target:
          continue
        if destination.exists() or destination.is_symlink():
          destination.unlink()
        destination.symlink_to(target)
      elif destination.is_symlink() or not same_contents(source, destination):
        old_mtime = destination.stat().st_mtime_ns if destination.exists() else None
        if destination.is_symlink():
          destination.unlink()
        elif destination.is_dir():
          shutil.rmtree(destination)
        shutil.copy2(source, destination)
        # SCons' MD5-timestamp decider must notice edits even if an editor kept mtime.
        if destination.stat().st_mtime_ns == old_mtime:
          os.utime(destination, None)
      elif source.stat().st_mode != destination.stat().st_mode:
        destination.chmod(source.stat().st_mode)
    self.sync_git()
    manifest.write_text(json.dumps(sorted(paths)) + '\n')

  def sync_git(self):
    # Same read-only object sharing as `git clone --shared`, independent index/refs.
    metadata = self.work / '.git'
    if metadata.is_symlink() or (metadata.exists() and not metadata.is_dir()):
      raise RuntimeError('Host worktree has shared Git metadata; remove this host cache and retry.')
    if not metadata.exists():
      git(self.work, 'init', '-q')
    common = Path(git(self.root, 'rev-parse', '--git-common-dir').strip())
    if not common.is_absolute():
      common = self.root / common
    (metadata / 'objects/info/alternates').write_text(str(common.resolve() / 'objects') + '\n')
    head = git(self.root, 'rev-parse', 'HEAD').strip()
    branch = git(self.root, 'rev-parse', '--abbrev-ref', 'HEAD').strip()
    branch = 'host-detached' if branch == 'HEAD' else branch
    git(self.work, 'symbolic-ref', 'HEAD', f'refs/heads/{branch}')
    git(self.work, 'update-ref', 'HEAD', head)
    git(self.work, 'read-tree', head)
    config = git(self.root, 'config', '--list')
    origin = next((line.split('=', 1)[1] for line in config.splitlines() if line.startswith('remote.origin.url=')), '')
    if origin:
      git(self.work, 'config', 'remote.origin.url', origin)
    # A host helper must never accidentally push through this diagnostic clone.
    git(self.work, 'config', 'remote.origin.pushurl', 'disabled://host-runtime')
    git(self.work, 'config', 'core.hooksPath', '/dev/null')

  def environment(self):
    env = {key: value for key, value in os.environ.items() if key not in REMOVE_ENV}
    paths = [self.work, *(self.work / name for name in VENDORS)]
    env.update(PYTHONPATH=os.pathsep.join(map(str, paths)), PYTHONNOUSERSITE='1',
               PATH=f'{self.venv}/bin' + os.pathsep + env.get('PATH', ''), VIRTUAL_ENV=str(self.venv),
               BASEDIR=str(self.work), PWD=str(self.work), PARAMS_ROOT=str(inside(self.cache / 'params', self.cache)),
               OPENPILOT_PREFIX=self.prefix, SP_HOST_PREFIX=self.prefix,
               SP_HOST_PARAMS_ROOT=str(self.cache / 'params'), SP_HOST_RUNTIME='1',
               SP_SCONS_CACHE_DIR=str(self.cache / 'scons-cache'),
               SCONS_CACHE=str(self.cache / 'scons-cache'),
               NOBOARD='1', SIMULATION='1', SKIP_FW_QUERY='1', STARPILOT_UI_DEV='1',
               COMMA_CACHE=str(self.cache.parent / 'downloads'))
    if self.system == 'Darwin':
      env.update(CC='/usr/bin/clang', CXX='/usr/bin/clang++', ZMQ='1')
    return env

  def prepare(self):
    uv = shutil.which('uv')
    if uv is None:
      candidate = Path.home() / '.local/bin/uv'
      if candidate.is_file() and os.access(candidate, os.X_OK):
        uv = str(candidate)
    if uv is None:
      raise RuntimeError('uv is required. Run tools/setup_dependencies.sh, then retry ./dev.')
    inside(self.venv, self.cache)
    env = self.environment()
    env.update(UV_PROJECT_ENVIRONMENT=str(self.venv), UV_PYTHON='3.12')
    run([uv, 'sync', '--frozen', '--extra', 'tools', '--extra', 'testing', '--extra', 'dev'], cwd=self.work, env=env)
    link = self.work / '.venv'
    if link.is_symlink():
      if link.resolve() != self.venv.resolve():
        raise RuntimeError('Host worktree .venv points outside its environment.')
    elif link.exists():
      raise RuntimeError('Host worktree .venv is not the managed environment; remove this host cache and retry.')
    else:
      link.symlink_to(self.venv, target_is_directory=True)

  def build(self, command, jobs):
    params = 'openpilot/common/libparams_c' + ('.dylib' if self.system == 'Darwin' else '.so')
    targets = [params, 'msgq_repo/msgq/ipc_pyx.so', 'msgq_repo/msgq/visionipc/visionipc_pyx.so']
    if command in ('c3', 'c4', 'onroad', 'python', 'pytest', 'shell'):
      targets += ['rednose_repo/rednose/helpers/ekf_sym_pyx.so', 'openpilot/selfdrive/locationd',
                  'openpilot/selfdrive/controls/lib/longitudinal_mpc_lib/c_generated_code/acados_ocp_solver_pyx.so']
    if command in ('onroad', 'replay', 'cabana'):
      targets += ['openpilot/tools/' + ('cabana/cabana' if command == 'cabana' else 'replay/replay')]
    run([self.venv / 'bin/python', '-m', 'SCons', f'-j{jobs}', *targets], cwd=self.work, env=self.environment())

  def launch(self, command, jobs, arguments):
    env = self.environment()
    python = self.venv / 'bin/python'
    if command in ('c3', 'c4', 'onroad'):
      script = 'launch_onroad_desktop.sh' if command == 'onroad' else f'launch_ui_{command}_desktop.sh'
      argv = [self.work / 'scripts' / script, str(jobs), *arguments]
    elif command in ('replay', 'cabana'):
      argv = [self.work / 'openpilot/tools' / command / command, *arguments]
    elif command == 'plotjuggler':
      argv = [python, '-m', 'openpilot.tools.plotjuggler.juggle', *arguments]
    elif command == 'galaxy':
      argv = [python, '-m', 'openpilot.starpilot.galaxy.server', *arguments]
    elif command == 'pytest':
      argv = [python, '-m', 'pytest', *arguments]
      env.setdefault('SCALE', '1')  # UI imports must not probe a monitor in test workers.
      if self.system == 'Darwin':
        env['PYTEST_ADDOPTS'] = env.get('PYTEST_ADDOPTS', '') + ' -n0'
    elif command == 'shell':
      argv = [env.get('SHELL', '/bin/bash'), *arguments]
    else:
      argv = [python, *arguments]
    ipc = Path('/tmp' if self.system == 'Darwin' else '/dev/shm') / f'msgq_{self.prefix}'
    if ipc.is_symlink() or (ipc.exists() and (not ipc.is_dir() or ipc.stat().st_uid != os.getuid())):
      raise RuntimeError(f'Private messaging path is not owned by this user: {ipc}')
    ipc.mkdir(mode=0o700, exist_ok=True)
    # Keep the bucket locked if this wrapper is killed while its child is alive.
    inherited = () if self.lock_fd is None else (self.lock_fd,)
    with subprocess.Popen([str(arg) for arg in argv], cwd=self.work, env=env, pass_fds=inherited) as child:
      def forward(signum, _frame):
        if child.poll() is None:
          child.send_signal(signum)
      previous = {sig: signal.signal(sig, forward) for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
      try:
        result = child.wait()
        return result if result >= 0 else 128 - result
      finally:
        for sig, handler in previous.items():
          signal.signal(sig, handler)


def main(arguments=None):
  command, jobs, args = parse(sys.argv[1:] if arguments is None else arguments)
  if command == 'help':
    print(HELP)
    return 0
  if command in ('c3', 'c4', 'onroad') and args in (['--help'], ['-h']):
    helper = ROOT / ('openpilot/tools/replay/onroad.py' if command == 'onroad' else 'openpilot/starpilot/ui/host_launch.py')
    profile = [] if command == 'onroad' else ['large' if command == 'c3' else 'compact']
    return subprocess.call([sys.executable, str(helper), *profile, '--help'], cwd=ROOT)
  if command == 'sync':
    buckets = [BUCKET_ALIASES[args[0]]] if args else ['shared', 'cabana']
  else:
    buckets = ['cabana' if command == 'cabana' else 'shared']
  for bucket in buckets:
    runtime = HostRuntime(ROOT, bucket)
    with runtime.locked():
      runtime.sync()
      runtime.prepare()
      if command != 'sync':
        runtime.build(command, jobs)
        return runtime.launch(command, jobs, args)
  return 0


if __name__ == '__main__':
  try:
    raise SystemExit(main())
  except (ValueError, RuntimeError, OSError) as error:
    print(f'Host tools: {error}', file=sys.stderr)
    raise SystemExit(1) from None
  except subprocess.CalledProcessError as error:
    raise SystemExit(error.returncode if error.returncode > 0 else 128 - error.returncode) from None
  except KeyboardInterrupt:
    raise SystemExit(130) from None
