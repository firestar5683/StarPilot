#!/usr/bin/env python3
"""Isolated native msgq build. Never modifies source checkout or build receipts."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import sysconfig
import tempfile

sys.dont_write_bytecode = True

from validate_elf import BASELINE_SHA256

HERE = Path(__file__).resolve().parent
PINNED = {'Cython': '3.3.0', 'SCons': '4.11.1', 'pytest': '8.4.2', 'iniconfig': '2.3.0',
          'packaging': '26.3', 'pluggy': '1.6.0', 'Pygments': '2.21.0'}


def check(condition, message):
  if not condition:
    raise RuntimeError(message)


def capture(*args, cwd=None):
  return subprocess.check_output(args, cwd=cwd, text=True).strip()


def sha(path):
  return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def manifest(root):
  return {str(p.relative_to(root)): {'size': p.stat().st_size, 'sha256': sha(p)}
          for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def bind_committed_sources(source, revision, build, source_manifest):
  tree = subprocess.check_output(['git', 'ls-tree', '-rz', revision, '--', 'msgq_repo'], cwd=source)
  committed = {}
  for row in tree.split(b'\0'):
    if row:
      metadata, path = row.split(b'\t', 1)
      mode, kind, blob = metadata.decode().split()
      committed[path.decode()] = (mode, kind, blob)
  for relative, info in source_manifest.items():
    original = 'msgq_repo/'+relative
    check(original in committed, f'Uncommitted build input: {original}')
    mode, kind, blob = committed[original]
    check(kind == 'blob' and mode in ('100644', '100755'), f'Unsupported build input type: {original}')
    copied = build/relative
    check(not copied.is_symlink(), f'Symlink build input is not permitted: {original}')
    check(('100755' if copied.stat().st_mode & 0o111 else '100644') == mode, f'Build input mode differs from commit: {original}')
    data = subprocess.check_output(['git', 'cat-file', 'blob', blob], cwd=source)
    check(copied.read_bytes() == data, f'Build input bytes differ from committed blob: {original}')
    info.update(git_path=original, git_mode=mode, git_blob=blob)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('source_root', type=Path)
  parser.add_argument('baseline_so', type=Path)
  parser.add_argument('output_dir', type=Path)
  args = parser.parse_args()
  source, baseline, output = (p.resolve() for p in (args.source_root, args.baseline_so, args.output_dir))
  check(platform.machine() == 'aarch64' and platform.system() == 'Linux', 'Actual native Linux AArch64 required')
  check(sys.implementation.name == 'cpython' and sys.version_info[:3] == (3, 12, 13), 'Actual CPython 3.12.13 required')
  check(os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get('CI') == 'true', 'This helper is scoped to the explicitly approved CI job')
  check(os.environ.get('RUNNER_ARCH') == 'ARM64' and sys.flags.optimize == 0, 'Native ARM64 runner and non-optimized Python required')
  check(not Path('/AGNOS').exists(), 'Do not run this helper on a device')
  check(not output.is_relative_to(source) and not source.is_relative_to(output), 'Output and source must be separate trees')
  check(not output.exists() or not any(output.iterdir()), 'Output directory must be new or empty')
  check(sha(baseline) == BASELINE_SHA256, 'Wrong reviewed baseline library')
  source_commit = capture('git', 'rev-parse', 'HEAD', cwd=source)
  check(source_commit == os.environ['EXPECTED_SOURCE_COMMIT'], 'Source commit differs from approved SHA')
  base_commit = os.environ['EXPECTED_BASE_COMMIT']
  check(base_commit == 'e8389b0b7529bad402f1f4e5fbd672ff13d9d382', 'Unreviewed baseline commit')
  check(len(base_commit) == 40 and capture('git', 'rev-parse', base_commit+'^{commit}', cwd=source) == base_commit, 'Full baseline commit must be available locally')
  subprocess.run(['git', 'merge-base', '--is-ancestor', base_commit, source_commit], cwd=source, check=True)
  check(not capture('git', 'status', '--porcelain', '--untracked-files=all', cwd=source), 'Source checkout must be clean, including untracked paths')
  versions = {name: importlib.metadata.version(name) for name in PINNED}
  check(versions == PINNED, f'Build/test packages differ from reviewed uv.lock pins: {versions}')
  compiler = {key: Path(os.environ.get(key, '/usr/bin/'+name+'-13')).resolve() for key, name in [('GCC', 'gcc'), ('GXX', 'g++')]}
  expected_gcc = os.environ['EXPECTED_GCC_VERSION']
  check(expected_gcc.split('.')[0] == '13', 'Only explicitly reviewed GCC 13 is allowed')
  for path in compiler.values():
    check(capture(str(path), '-dumpfullversion') == expected_gcc, f'Unapproved compiler version: {path}')
    check(capture(str(path), '-dumpmachine') == 'aarch64-linux-gnu', f'Compiler is not native generic AArch64: {path}')
  output.mkdir(parents=True, exist_ok=True)
  artifacts = output/'artifacts'
  artifacts.mkdir()
  toolchain = {
    'qualification': 'CI ARM host artifact; not deployed or device-qualified',
    'source_commit': source_commit, 'base_commit': base_commit, 'baseline_sha256': sha(baseline),
    'python': sys.version, 'python_executable': str(Path(sys.executable).resolve()), 'python_sha256': sha(Path(sys.executable).resolve()),
    'python_sysconfig': {key: sysconfig.get_config_var(key) for key in ('SOABI', 'MULTIARCH', 'CONFIG_ARGS', 'CC', 'CFLAGS', 'LDFLAGS')},
    'packages': versions, 'platform': platform.platform(), 'os_release': Path('/etc/os-release').read_text(),
    'compilers': {key: {'path': str(path), 'sha256': sha(path), 'version': capture(str(path), '--version')} for key, path in compiler.items()},
    'compiler_packages': capture('dpkg-query', '-W', '-f=${Package}\t${Version}\t${Architecture}\n', 'gcc-13', 'g++-13', 'libstdc++6', 'libc6', 'binutils'),
    'binutils': capture('readelf', '--version'), 'isa_flags': ['-march=armv8-a', '-mtune=generic'],
    'cxx_compatibility_flags': ['-fno-sized-deallocation'],
    'requirements_sha256': sha(HERE/'requirements.lock'), 'uv_lock_sha256': sha(source/'uv.lock'),
  }
  libstdcxx = Path(capture(str(compiler['GXX']), '-print-file-name=libstdc++.so')).resolve()
  toolchain['compiler_libstdcxx'] = {'path': str(libstdcxx), 'sha256': sha(libstdcxx)}
  (artifacts/'toolchain.json').write_text(json.dumps(toolchain, indent=2)+'\n')
  build = output/'build'
  shutil.copytree(source/'msgq_repo', build, ignore=shutil.ignore_patterns('.git', '*.so', '*.o', '*.a', '*.pyc', '__pycache__', '.sconsign*', '*_pyx.cpp'))
  source_manifest = manifest(build)
  bind_committed_sources(source, source_commit, build, source_manifest)
  (artifacts/'source_files.json').write_text(json.dumps(source_manifest, indent=2)+'\n')
  baseline_root = output/'baseline'
  (baseline_root/'msgq/visionipc').mkdir(parents=True)
  (baseline_root/'msgq/tests').mkdir()
  baseline_files = ['msgq/__init__.py', 'msgq/visionipc/__init__.py', 'msgq/visionipc/visionipc_pyx.so',
                    'msgq/tests/__init__.py', 'msgq/tests/test_fake.py', 'msgq/tests/test_messaging.py', 'msgq/tests/test_poller.py']
  for relative in baseline_files:
    data = subprocess.check_output(['git', 'show', base_commit+':msgq_repo/'+relative], cwd=source)
    (baseline_root/relative).write_bytes(data)
  tracked_baseline = subprocess.check_output(['git', 'show', base_commit+':msgq_repo/msgq/ipc_pyx.so'], cwd=source)
  check(hashlib.sha256(tracked_baseline).hexdigest() == BASELINE_SHA256, 'Baseline commit does not contain reviewed ipc_pyx bytes')
  shutil.copy2(baseline, baseline_root/'msgq/ipc_pyx.so')
  companion_relative = Path('msgq/visionipc/visionipc_pyx.so')
  companion_sha = sha(baseline_root/companion_relative)
  check(companion_sha == 'd9aee015a9ca9d6d8f4dc54c5bca6a8f3ab24ad9a42477561ea7cc32eebff5a4', 'Unreviewed companion baseline')
  check(sha(source/'msgq_repo'/companion_relative) == companion_sha, 'Source checkout changed shipped visionipc companion')
  shutil.copy2(baseline_root/companion_relative, build/companion_relative)
  (artifacts/'unchanged_companion.json').write_text(json.dumps({'git_blob': capture('git', 'rev-parse', base_commit+':msgq_repo/'+str(companion_relative), cwd=source), 'sha256': companion_sha}, indent=2)+'\n')
  wrappers = output/'compiler-bin'
  wrappers.mkdir()
  for name in ('cc', 'gcc', 'c++', 'g++'):
    (wrappers/name).symlink_to(HERE/'compiler_wrapper.py')
  env = dict(os.environ, PATH=str(wrappers)+os.pathsep+str(Path(sys.executable).parent)+os.pathsep+os.environ['PATH'],
             PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONPATH=str(build),
             ARM_CI_GCC=str(compiler['GCC']), ARM_CI_GXX=str(compiler['GXX']),
             ARM_CI_COMPILER_LOG=str(artifacts/'compiler_commands.jsonl'),
             ARM_CI_BASELINE_ROOT=str(baseline_root), ARM_CI_CANDIDATE_ROOT=str(build),
             ARM_CI_COMPANION_SHA256=companion_sha, ARM_CI_PAIR_REPORT=str(artifacts/'api_and_companion.json'))
  env.pop('CEREAL_FAKE', None)
  env.pop('SCONSFLAGS', None)
  env.pop('LD_PRELOAD', None)
  env.pop('PYTHONOPTIMIZE', None)

  def run_logged(name, command, cwd, command_env=env):
    with (artifacts/(name+'.log')).open('w') as log:
      log.write(json.dumps({'cwd': str(cwd), 'argv': command})+'\n')
      log.flush()
      subprocess.run(command, cwd=cwd, env=command_env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)

  run_logged('build', [sys.executable, '-m', 'SCons', '--minimal', '--cache-disable', '-j2', 'msgq/ipc_pyx.so'], build)
  candidate = build/'msgq/ipc_pyx.so'
  run_logged('static_abi', [sys.executable, str(HERE/'validate_elf.py'), '--baseline', str(baseline), '--candidate', str(candidate), '--report', str(artifacts/'elf_comparison.json')], output)
  for name, package in [('baseline', baseline_root), ('candidate', build)]:
    with tempfile.TemporaryDirectory(prefix='msgq_armci_', dir='/dev/shm') as namespace:
      test_env = dict(env, PYTHONPATH=str(package), OPENPILOT_PREFIX=Path(namespace).name.removeprefix('msgq_'))
      run_logged(name+'_tests', [sys.executable, '-m', 'pytest', '--noconftest', '--rootdir', str(output), '-p', 'no:cacheprovider', '-o', 'addopts=', '-q', '--junitxml', str(artifacts/(name+'_tests.xml')), str(package/'msgq/tests')], output, test_env)
  run_logged('mixed_version_tests', [sys.executable, '-m', 'pytest', '--noconftest', '--rootdir', str(output), '-p', 'no:cacheprovider', '-o', 'addopts=', '-q', '--junitxml', str(artifacts/'mixed_version_tests.xml'), str(HERE/'test_native_pair.py')], output)
  generated = {str(p.relative_to(build)): {'size': p.stat().st_size, 'sha256': sha(p)} for p in sorted(build.rglob('*'))
               if p.is_file() and (p.suffix in ('.o', '.a', '.so') or p.name == 'ipc_pyx.cpp')}
  (artifacts/'generated_files.json').write_text(json.dumps(generated, indent=2)+'\n')
  shutil.copy2(candidate, artifacts/'ipc_pyx.so')
  shutil.copy2(build/'msgq/ipc_pyx.cpp', artifacts/'ipc_pyx.cpp')
  check(all(sha(build/p) == info['sha256'] for p, info in source_manifest.items()), 'Build modified an input source file')
  check(not capture('git', 'status', '--porcelain', '--untracked-files=all', cwd=source), 'Build changed checkout, including untracked paths')
  (artifacts/'RESULT.json').write_text(json.dumps({'status': 'native_arm_ci_checks_passed', 'candidate_sha256': sha(candidate),
                                                 'device_qualification': 'NOT ESTABLISHED; explicit artifact/toolchain/runtime review required',
                                                 'receipts_modified': False, 'deployed': False}, indent=2)+'\n')
  print(artifacts)


if __name__ == '__main__':
  main()
