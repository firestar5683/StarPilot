#!/usr/bin/env python3
"""Run pre-push regression checks in the existing isolated developer runtime."""

import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.ci.run_predeploy import commands, run
from tools.ci.run_host_tests import UI_PYTEST_FILES


QUICK_TARGETS = (
  'openpilot/common/tests/test_params.py',
  'openpilot/common/tests/test_params_registry_usage.py',
  'openpilot/selfdrive/selfdrived/tests/test_big_model_status.py',
  'openpilot/starpilot/tests',
  'openpilot/starpilot/aol/tests',
  'openpilot/starpilot/analytics/tests',
  'openpilot/starpilot/bluetooth/tests/test_owner.py',
  'openpilot/starpilot/flm/tests/test_controller_replay.py',
  'openpilot/starpilot/controllers/tests',
  'openpilot/starpilot/car/tesla/tests',
  'openpilot/starpilot/lateral/tests',
  'openpilot/starpilot/longitudinal/tests',
  'openpilot/starpilot/drive_state/tests',
  'openpilot/starpilot/models/tests',
  'openpilot/starpilot/software/tests/test_fast_update.py',
  'openpilot/starpilot/software/tests/test_update_process.py',
  'openpilot/starpilot/software/tests/test_history.py',
  'openpilot/starpilot/ui/tests',
  'openpilot/starpilot/galaxy/tests/test_access.py',
  'openpilot/starpilot/galaxy/tests/test_pairing_migration.py',
  'openpilot/starpilot/galaxy/tests/test_settings_defaults.py',
  'openpilot/starpilot/galaxy/tests/test_vehicle_configuration.py',
  'openpilot/starpilot/galaxy/tests/test_tesla_screen_settings.py',
  'opendbc_repo/opendbc/car/gm/tests/test_bolt_pedal.py',
  'opendbc_repo/opendbc/car/gm/tests/test_camera_acc_pedal.py',
  'opendbc_repo/opendbc/car/gm/tests/test_volt_transitions.py',
  'opendbc_repo/opendbc/car/gm/tests/test_ordinary_cc.py::TestMalibuHybridCc',
  'opendbc_repo/opendbc/safety/tests/test_gm_bolt_pedal.py',
  'opendbc_repo/opendbc/safety/tests/test_gm_camera_acc_pedal.py',
  'opendbc_repo/opendbc/safety/tests/test_gm_cc_pedal.py',
  'opendbc_repo/opendbc/safety/tests/test_gm_hybrid_cc.py',
  'opendbc_repo/opendbc/car/tesla/tests/test_screen_button.py',
  'opendbc_repo/opendbc/safety/tests/test_tesla_screen_button.py',
  'opendbc_repo/opendbc/safety/tests/test_toyota.py',
  'opendbc_repo/opendbc/car/toyota/tests/test_retrofit.py',
  'opendbc_repo/opendbc/car/honda/tests/test_stock_aol.py',
  'openpilot/selfdrive/car/tests/test_honda_aol.py::HondaFamilyQualificationTests',
  'opendbc_repo/opendbc/car/hyundai/tests/test_ioniq6_stock_parser.py',
  'opendbc_repo/opendbc/car/hyundai/tests/test_ioniq6_engagement_messages.py',
  'opendbc_repo/opendbc/safety/tests/test_hyundai_ioniq6_long.py',
) + UI_PYTEST_FILES


def main(arguments=None):
  parser = argparse.ArgumentParser(description=__doc__, epilog=(
    'Default: lint, packaging/CI/updater checks, startup/migration, Params, controls, models, UI, and Bolt/Ioniq regressions. '
    + 'First use prepares host dependencies; later runs reuse them. No device build, flash, push, or road qualification.'))
  parser.add_argument('--full', action='store_true', help='Run the existing full Linux pre-deployment suite, including recorded routes and replay')
  parser.add_argument('--download', action='store_true', help='Allow pinned recorded-route downloads with --full (replay may also fetch its logs)')
  parser.add_argument('--output', type=Path, help='New directory for per-check logs; defaults to a temporary report directory')
  args = parser.parse_args(arguments)
  if args.download and not args.full:
    parser.error('--download requires --full; the default checks do not fetch routes')
  if args.full and platform.system() != 'Linux':
    parser.error('--full requires Linux for native transport and map IPC; run ./test for local checks on macOS')
  output = args.output.expanduser().resolve() if args.output else Path(tempfile.mkdtemp(prefix='starpilot-tests-')) / 'results'
  if output.exists():
    parser.error('--output must be new so previous reports are preserved')
  if output.is_relative_to(ROOT):
    parser.error('--output must be outside the source checkout')
  if os.environ.get('SP_HOST_RUNTIME') != '1':
    options = ['--output', str(output), *(['--full'] if args.full else []), *(['--download'] if args.download else [])]
    print(f'Preparing isolated host tests. Reports: {output}', flush=True)
    started = time.monotonic()
    result = subprocess.run([str(ROOT / 'dev'), 'python', 'tools/ci/run_local_tests.py', *options], cwd=ROOT, check=False)
    print(f'Total including host preparation: {time.monotonic() - started:.1f}s', flush=True)
    return result.returncode if result.returncode >= 0 else 128 - result.returncode
  environment = dict(os.environ, SCALE='1', RAYLIB_BACKEND='desktop' if platform.system() == 'Darwin' else 'headless',
                     FUZZ_SEED='0', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
  for key in ('FAST', 'RUN', 'SKIP', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS'):
    environment.pop(key, None)
  if args.full:
    return subprocess.call([sys.executable, 'tools/ci/run_predeploy.py', '--output', str(output),
                            *(['--download'] if args.download else [])], cwd=ROOT, env=environment)

  if platform.system() == 'Darwin':
    for prefix in ('/opt/homebrew', '/usr/local'):
      directory = Path(prefix) / 'opt/coreutils/libexec/gnubin'
      if directory.is_dir():
        environment['PATH'] = str(directory) + os.pathsep + environment.get('PATH', '')
        break
  if shutil.which('timeout', path=environment.get('PATH')) is None:
    parser.error('GNU timeout is required for the updater checks; install coreutils (brew install coreutils on macOS)')
  shared_memory = '/tmp' if platform.system() == 'Darwin' else '/dev/shm'
  with tempfile.TemporaryDirectory(prefix='starpilot-test-params-') as params, \
       tempfile.TemporaryDirectory(prefix='msgq_starpilot-test-', dir=shared_memory) as messaging:
    environment.update(PARAMS_ROOT=params, OPENPILOT_PREFIX=Path(messaging).name.removeprefix('msgq_'))
    plan = commands(output, Path('/unused'))['source']
    aol_protocol = output / 'test_aol_protocol'
    plan.extend((('aol-protocol-build', ['c++', '-std=c++17', '-I.', '-Iopenpilot', '-Iopendbc_repo',
                                       'openpilot/selfdrive/pandad/tests/test_aol_protocol.cc', '-o', str(aol_protocol)]),
                 ('aol-protocol', [str(aol_protocol)])))
    plan.append(('regressions', [sys.executable, '-m', 'pytest', '-q', '--import-mode=importlib',
                                 '--junitxml', str(output / 'regressions.xml'), *QUICK_TARGETS]))
    result = run(plan, output, environment=environment)
  print(f'{"PASS" if result == 0 else "FAIL"}: local pre-push checks. Reports: {output}', flush=True)
  return result


if __name__ == '__main__':
  raise SystemExit(main())
