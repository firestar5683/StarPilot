"""Disposable local Git rehearsal; no device, network, reboot or real signals.

Run with pytest -c /dev/null --confcutdir=<this directory>. Git operations,
resolution, compatibility checks, checkout, backups and restore are real. Public
metadata transport is answered from a local bare origin. The installed OS file
is synthetic; ELF headers exercise validation only, not ARM execution. Recovery
uses the copied module in a fresh interpreter with process discovery disabled.
"""
import ast
import importlib.util
import inspect
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import pytest


MODULE_DIR = Path(__file__).resolve().parents[1]


def load_module(name, path=None):
  spec = importlib.util.spec_from_file_location(name, path or MODULE_DIR / (name + '.py'))
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


def git(repo, *args):
  return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.STDOUT, text=True).strip()


def write(root, name, content):
  path = root / name
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_bytes(content if isinstance(content, bytes) else content.encode())
  return path


@pytest.fixture
def rehearsal(monkeypatch):
  # Constrain every Git subprocess, including the copied recovery helper, to
  # local file transport even if a future fixture accidentally adds a remote.
  monkeypatch.setenv('GIT_ALLOW_PROTOCOL', 'file')
  monkeypatch.setenv('GIT_CONFIG_NOSYSTEM', '1')
  monkeypatch.setenv('GIT_CONFIG_GLOBAL', '/dev/null')
  with tempfile.TemporaryDirectory(prefix='galaxy-version-rehearsal-') as directory:
    root = Path(directory)
    installer = load_module('rehearsal_installer', MODULE_DIR / 'version_install.py')
    history = load_module('rehearsal_history', MODULE_DIR / 'version_history.py')
    seed = root / 'seed'
    seed.mkdir()
    git(seed, 'init', '-b', 'Dom')
    git(seed, 'config', 'user.name', 'Local rehearsal')
    git(seed, 'config', 'user.email', 'rehearsal@example.invalid')
    files = {
      'launch_env.sh': 'export AGNOS_VERSION="19.6.20"\n',
      'launch_chffrplus.sh': '#!/bin/sh\n',
      'common/params_keys.h': 'AutomaticUpdates TeslaWakeOnCAN\n',
      'starpilot/common/starpilot_variables.py': 'automatic_updates = AutomaticUpdates\n',
      'system/updated/updated.py': 'automatic_updates_enabled\n',
      'system/hardware/tici/agnos.json': '[{"name":"system", "hash":"fixture"}]\n',
      'feature.txt': 'historical\n',
      'selfdrive/pandad/panda_firmware.py': inspect.getsource(installer._selected_firmware_name).replace(
        'def _selected_firmware_name(', 'def get_selected_firmware_name(', 1),
      'panda/board/obj/panda_tesla_wake.bin.signed': b'synthetic firmware fixture',
      'panda/board/obj/panda_h7_tesla_wake.bin.signed': b'synthetic firmware fixture',
    }
    # Deliberately minimal headers: test the native preflight predicate only.
    elf = bytearray(64)
    elf[:6], elf[18:20] = b'\x7fELF\x02\x01', b'\xb7\x00'
    for name in ('common/params_pyx.so', 'selfdrive/pandad/pandad', 'system/camerad/camerad'):
      files[name] = bytes(elf)
    for name, content in files.items():
      write(seed, name, content)
    git(seed, 'add', '.')
    git(seed, 'commit', '-m', 'Historical fixture without Galaxy module')
    old = git(seed, 'rev-parse', 'HEAD')
    write(seed, 'feature.txt', 'latest\n')
    write(seed, 'starpilot/system/the_galaxy/version_install.py', (MODULE_DIR / 'version_install.py').read_bytes())
    git(seed, 'add', '.')
    git(seed, 'commit', '-m', 'Latest fixture with Galaxy recovery')
    latest = git(seed, 'rev-parse', 'HEAD')
    origin, repo = root / 'origin.git', root / 'checkout'
    git(root, 'clone', '--bare', str(seed), str(origin))
    git(root, 'clone', '--depth=1', '--branch', 'Dom', origin.as_uri(), str(repo))
    assert git(repo, 'rev-parse', '--is-shallow-repository') == 'true'
    assert subprocess.run(['git', '-C', str(repo), 'cat-file', '-e', old], capture_output=True).returncode != 0
    write(repo, 'feature.txt', 'valuable local changes\n')
    write(repo, 'local-tool.txt', 'untracked local tool\n')
    data = root / 'fake-data'
    for name, value in {'IsOnroad': '0', 'IsOffroad': '1', 'AutomaticUpdates': '1',
                        'ExampleSetting': 'preserve me', 'TeslaWakeOnCAN': '1'}.items():
      write(data, 'params/d/' + name, value)
    write(data, 'safe_staging/finalized/.overlay_consistent', '')
    version_file = write(root, 'VERSION', '19.6.20\n')
    monkeypatch.setattr(installer, 'OS_VERSION_FILE', version_file)
    monkeypatch.setattr(installer, '_processes', lambda: {})
    def no_signal(*args):
      raise AssertionError('A local rehearsal must never signal a real process')
    monkeypatch.setattr(installer.os, 'kill', no_signal)

    # Preserve the actual resolver/branch validation/ancestry checks. Only the
    # external metadata endpoint is represented by our local origin transport.
    monkeypatch.setattr(history, '_repository', lambda path: 'local-rehearsal')
    requests = []
    def local_metadata(url):
      requests.append(url)
      if url == 'local-rehearsal/branches/Dom':
        return {'name': 'Dom', 'commit': {'sha': git(origin, 'rev-parse', 'refs/heads/Dom')}}
      prefix = 'local-rehearsal/compare/'
      assert url.startswith(prefix), url
      chosen, head = url.removeprefix(prefix).split('...')
      ancestor = git(origin, 'merge-base', chosen, head)
      return {'status': 'ahead', 'merge_base_commit': {'sha': ancestor}}
    monkeypatch.setattr(history, '_get_json', local_metadata)
    tree = ast.parse((MODULE_DIR / 'the_galaxy.py').read_text())
    fetch_node = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                      and node.name == '_build_shallow_fetch_commit_args')
    namespace = {}
    exec(compile(ast.Module(body=[fetch_node], type_ignores=[]), str(MODULE_DIR / 'the_galaxy.py'), 'exec'), namespace)
    (data / 'starpilot').mkdir()
    connection = sqlite3.connect(data / 'starpilot/model_stats.sqlite')
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('PRAGMA wal_autocheckpoint=0')
    connection.execute('CREATE TABLE events (id INTEGER PRIMARY KEY, note TEXT)')
    connection.execute('INSERT INTO events VALUES (1, "before install")')
    connection.commit()
    assert Path(str(data / 'starpilot/model_stats.sqlite') + '-wal').stat().st_size > 0
    state = SimpleNamespace(root=root, repo=repo, data=data, origin=origin, old=old, latest=latest,
                            installer=installer, history=history, connection=connection,
                            requests=requests, version_file=version_file,
                            fetch_args=namespace['_build_shallow_fetch_commit_args'])
    try:
      yield state
    finally:
      connection.close()
  assert not root.exists(), 'Disposable install environment was not removed'
  print('CLEANUP VERIFIED: ' + str(root))


def fetch_target(state, selection):
  target = state.history.resolve_version(state.repo, 'Dom', selection)
  git(state.repo, *state.fetch_args(target['commit']))
  assert git(state.repo, 'rev-parse', 'FETCH_HEAD^{commit}') == target['commit']
  return target


def install_target(state, target):
  progress = []
  with state.installer.suspend_updater() as control:
    result = state.installer.install(
      state.repo, target, data_root=state.data,
      check_parked=lambda: state.installer.require_parked(state.data),
      progress=lambda *args: progress.append(args), require_device_binaries=True)
    assert control.restart
  assert progress[-1][2] == 100
  return Path(result['backup'])


def test_real_shallow_install_external_recovery_and_return_latest(rehearsal):
  state = rehearsal
  backup = install_target(state, fetch_target(state, state.old))
  assert git(state.repo, 'rev-parse', 'HEAD') == state.old
  assert (state.repo / 'feature.txt').read_text() == 'historical\n'
  assert not (state.repo / 'starpilot/system/the_galaxy/version_install.py').exists()
  assert state.installer.read_pin(state.repo, state.data)['commit'] == state.old
  assert (state.data / 'params/d/AutomaticUpdates').read_bytes() == b'0'
  assert (state.data / 'params/d/ExampleSetting').read_bytes() == b'preserve me'
  assert (state.data / 'params/d/TeslaWakeOnCAN').read_bytes() == b'1'
  assert not (state.data / 'safe_staging/finalized/.overlay_consistent').exists()
  with sqlite3.connect(backup / 'model_stats.sqlite') as saved:
    assert saved.execute('PRAGMA integrity_check').fetchone() == ('ok',)
    assert saved.execute('SELECT * FROM events').fetchall() == [(1, 'before install')]
  assert (backup / 'params/AutomaticUpdates').read_bytes() == b'1'
  state.connection.execute('INSERT INTO events VALUES (2, "after install")')
  state.connection.commit()
  write(state.data, 'params/d/ExampleSetting', 'newer preference')

  # Load only the saved helper in an isolated interpreter. Its real standalone
  # restore needs no checkout imports; redirect its parked root and process
  # discovery because CLI defaults intentionally refer to an actual device.
  recovery_script = '''
import importlib.util, pathlib, sys
backup = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('saved_recovery', backup / 'recover.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
helper._processes = lambda: {}
def no_signal(*args):
  raise AssertionError('Recovery rehearsal must never signal a process')
helper.os.kill = no_signal
with helper.suspend_updater() as control:
  restored = helper.restore(backup, check_parked=lambda: helper.require_parked(pathlib.Path(sys.argv[2])))
  assert control.restart
print(restored['commit'])
'''
  result = subprocess.run([sys.executable, '-I', '-c', recovery_script, str(backup), str(state.data)],
                          cwd=state.root, text=True, capture_output=True, timeout=60, check=True)
  assert result.stdout.strip() == state.latest
  assert git(state.repo, 'rev-parse', 'HEAD') == state.latest
  assert (state.repo / 'feature.txt').read_text() == 'valuable local changes\n'
  assert (state.repo / 'local-tool.txt').read_text() == 'untracked local tool\n'
  assert state.installer.read_pin(state.repo, state.data) is None
  assert state.connection.execute('SELECT * FROM events').fetchall() == [(1, 'before install'), (2, 'after install')]
  assert (state.data / 'params/d/ExampleSetting').read_text() == 'newer preference'

  install_target(state, fetch_target(state, state.old))
  target = fetch_target(state, 'latest')
  assert target == {'branch': 'Dom', 'commit': state.latest, 'head': state.latest, 'pinned': False}
  assert state.requests.count('local-rehearsal/branches/Dom') == 3
  install_target(state, target)
  assert git(state.repo, 'rev-parse', 'HEAD') == state.latest
  assert (state.repo / 'feature.txt').read_text() == 'latest\n'
  assert state.installer.read_pin(state.repo, state.data) is None
  assert not (state.data / 'starpilot/version_selection.json').exists()
  assert (state.data / 'params/d/AutomaticUpdates').read_bytes() == b'0'
  assert (state.data / 'params/d/ExampleSetting').read_text() == 'newer preference'
  assert state.connection.execute('SELECT count(*) FROM events').fetchone() == (2,)


@pytest.mark.parametrize('guard', ['installed_os', 'firmware_variant', 'native_artifact'])
def test_native_preflight_guards_leave_local_source_and_data_untouched(rehearsal, guard):
  state = rehearsal
  target = fetch_target(state, state.old)
  if guard == 'installed_os':
    state.version_file.write_text('18.0\n')
    expected = 'running device has AGNOS'
  else:
    # Create a deliberately incompatible target in the LOCAL origin and fetch
    # it through the same exact-SHA path, retaining the previous local checkout.
    seed = state.root / 'seed'
    git(seed, 'checkout', '--detach', state.old)
    name = ('panda/board/obj/panda_h7_tesla_wake.bin.signed' if guard == 'firmware_variant'
            else 'system/camerad/camerad')
    write(seed, name, b'')
    git(seed, 'add', name)
    git(seed, 'commit', '-m', 'Deliberately incompatible local target')
    bad = git(seed, 'rev-parse', 'HEAD')
    git(seed, 'push', str(state.origin), 'HEAD:refs/heads/guard-fixture')
    git(state.repo, *state.fetch_args(bad))
    target = dict(target, commit=bad)
    expected = 'firmware settings' if guard == 'firmware_variant' else 'compatible ARM64 artifact'
  with pytest.raises(state.installer.InstallError, match=expected):
    install_target(state, target)
  assert git(state.repo, 'rev-parse', 'HEAD') == state.latest
  assert (state.repo / 'feature.txt').read_text() == 'valuable local changes\n'
  assert (state.repo / 'local-tool.txt').read_text() == 'untracked local tool\n'
  assert (state.data / 'params/d/AutomaticUpdates').read_bytes() == b'1'
  assert (state.data / 'params/d/TeslaWakeOnCAN').read_bytes() == b'1'
  assert (state.data / 'params/d/ExampleSetting').read_bytes() == b'preserve me'
  assert state.connection.execute('SELECT * FROM events').fetchall() == [(1, 'before install')]
  assert (state.data / 'safe_staging/finalized/.overlay_consistent').exists()
  assert not (state.data / 'starpilot/version-backups').exists()
