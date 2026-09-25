#!/usr/bin/env python3
"""Replay pinned public upstream vehicle fixtures with explicit native variants."""
from collections import Counter
from contextlib import contextmanager
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import socket
import stat
import sys
import tempfile
import time
import traceback
import unittest
from urllib.request import build_opener, HTTPRedirectHandler, Request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools import test_runner

MANIFEST = ROOT / 'tools/ci/recorded-vehicle-fixtures.json'
ORIGIN = 'https://commadataci.blob.core.windows.net/openpilotci/'
MAX_FIXTURE_BYTES = 16 * 1024 * 1024


def load_fixtures(path=MANIFEST):
  document = json.loads(Path(path).read_text())
  fixtures = document['fixtures']
  if document['schema_version'] != 1 or not fixtures or len(fixtures) > 64:
    raise ValueError('Invalid recorded fixture manifest')
  ids = set()
  for f in fixtures:
    if (not re.fullmatch(r'[a-z][a-z0-9_]*', f['id']) or f['id'] in ids or
        not re.fullmatch(r'[A-Z][A-Z0-9_]+', f['platform']) or
        not re.fullmatch(r'[0-9a-f]{16}/[0-9a-f]{8}--[0-9a-f]{10}', f['route']) or
        type(f['segment']) is not int or not 0 <= f['segment'] <= 10000 or
        type(f['bytes']) is not int or not 0 < f['bytes'] <= MAX_FIXTURE_BYTES or
        not re.fullmatch(r'[0-9a-f]{64}', f['sha256']) or
        type(f['longitudinal']) is not bool or type(f['pcm_cruise']) is not bool or
        f['safety_model'] != 'tesla' or type(f['safety_param']) is not int or
        not f['variants'] or len(set(f['variants'])) != len(f['variants']) or
        not set(f['variants']) <= {'debug', 'release'}):
      raise ValueError('Invalid recorded fixture entry')
    ids.add(f['id'])
  return fixtures


class NoRedirect(HTTPRedirectHandler):
  def redirect_request(self, *args, **kwargs):
    raise OSError('Recorded fixture redirects are forbidden')


def verify_fixture(path, fixture):
  fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0))
  try:
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_size != fixture['bytes']:
      raise ValueError('Recorded fixture size or file type changed')
    with os.fdopen(fd, 'rb', closefd=False) as stream:
      data = stream.read(fixture['bytes'] + 1)
    if len(data) != fixture['bytes'] or hashlib.sha256(data).hexdigest() != fixture['sha256']:
      raise ValueError('Recorded fixture content changed')
  finally:
    os.close(fd)
  return path


def get_fixture(fixture, cache, download=False):
  cache = Path(cache)
  cache.mkdir(parents=True, exist_ok=True)
  path = cache / (fixture['sha256'] + '.zst')
  try:
    return verify_fixture(path, fixture)
  except FileNotFoundError:
    if not download:
      raise FileNotFoundError(f"Pinned fixture {fixture['id']} missing; use --download to fetch its public CI blob") from None
  url = f"{ORIGIN}{fixture['route']}/{fixture['segment']}/rlog.zst"
  opener = build_opener(NoRedirect())
  # No account API, alternate routes, auth headers, redirects, or unpinned data.
  started = time.monotonic()
  fd, temporary = tempfile.mkstemp(prefix='.fixture-', dir=cache)
  try:
    with os.fdopen(fd, 'wb') as output, opener.open(Request(url, headers={'Accept-Encoding': 'identity'}), timeout=15) as response:
      if response.status != 200 or response.geturl() != url:
        raise OSError('Unexpected recorded fixture response')
      declared = response.headers.get('Content-Length')
      if declared is not None and int(declared) != fixture['bytes']:
        raise ValueError('Recorded fixture declared size changed')
      total = 0
      while True:
        if time.monotonic() - started > 60:
          raise TimeoutError('Recorded fixture download deadline exceeded')
        chunk = response.read(min(65536, fixture['bytes'] - total + 1))
        if not chunk:
          break
        total += len(chunk)
        if total > fixture['bytes']:
          raise ValueError('Recorded fixture exceeded pinned size')
        output.write(chunk)
      output.flush()
      os.fsync(output.fileno())
    verify_fixture(temporary, fixture)
    os.replace(temporary, path)
  finally:
    Path(temporary).unlink(missing_ok=True)
  return path


def deny_network(*args, **kwargs):
  raise AssertionError('Network access is forbidden during recorded replay')


@contextmanager
def offline_replay():
  with patch('urllib.request.urlopen', deny_network), patch.object(socket.socket, 'connect', deny_network), \
       patch.object(socket.socket, 'connect_ex', deny_network):
    yield


def make_cases(fixtures, paths, observed):
  from opendbc.car.tests import test_models
  from opendbc.car.tests.routes import CarTestRoute
  from opendbc.car.logreader import LogReader
  from opendbc.car.values import PLATFORMS

  # The inherited tests receive only validated local paths; original download
  # helpers are disabled as well so future changes cannot silently fall back.
  test_models.get_cached_segment = deny_network
  test_models.get_cached_url = deny_network
  test_models.urlopen = deny_network

  class RecordedBase(test_models.TestCarModelBase):
    fixture = None
    local_path = None

    @classmethod
    def get_testing_data(cls):
      verify_fixture(cls.local_path, cls.fixture)
      return cls.get_testing_data_from_logreader(LogReader(str(cls.local_path), only_union_types=True, sort_by_time=True))

    @classmethod
    def setUpClass(cls):
      super().setUpClass()
      cp = cls.CP
      if (cp.dashcamOnly or cp.passive or cp.notCar or
          str(cp.carFingerprint) != cls.fixture['platform'] or
          cp.openpilotLongitudinalControl != cls.fixture['longitudinal'] or
          cp.pcmCruise != cls.fixture['pcm_cruise'] or
          len(cp.safetyConfigs) != 1 or
          str(cp.safetyConfigs[0].safetyModel) != cls.fixture['safety_model'] or
          cp.safetyConfigs[0].safetyParam != cls.fixture['safety_param']):
        raise AssertionError('Recorded fixture no longer has its reviewed controller configuration')
      observed.append({'fixture': cls.fixture['id'], 'platform': str(cp.carFingerprint),
                       'can_batches': len(cls.can_msgs), 'duration_seconds': (cls.can_msgs[-1][0] - cls.can_msgs[0][0]) / 1e9,
                       'longitudinal': cp.openpilotLongitudinalControl, 'pcm_cruise': cp.pcmCruise,
                       'safety_model': str(cp.safetyConfigs[0].safetyModel), 'safety_param': cp.safetyConfigs[0].safetyParam})

  tests = []
  for fixture in fixtures:
    name = 'TestRecorded_' + fixture['id']
    cls = type(name, (RecordedBase,), {'__module__': __name__, 'platform': PLATFORMS[fixture['platform']],
      'test_route': CarTestRoute(fixture['route'], PLATFORMS[fixture['platform']], segment=fixture['segment']),
      'fixture': fixture, 'local_path': paths[fixture['id']]})
    globals()[name] = cls
    tests.extend(test_runner.flatten(unittest.TestLoader().loadTestsFromTestCase(cls)))
  if not tests:
    raise ValueError('No recorded tests selected')
  return tests


def execution_errors(ids, records):
  by_id = {r['id']: r for r in records}
  return [f"Recorded case must pass: {test_id}: {by_id.get(test_id, {}).get('status', 'missing')}"
          for test_id in ids if by_id.get(test_id, {}).get('status') != 'passed']


def run(variant, cache, output, download=False):
  from tools.ci import run_vehicle_tests as vehicle
  output = Path(output).resolve()
  output.mkdir(parents=True, exist_ok=True)
  started = time.monotonic()
  tests, records, errors, observed = [], [], [], []
  plan = {'schema_version': 1, 'suite': 'recorded-vehicles', 'variant': variant,
          'scope': 'Recorded CAN parser/native RX agreement; synthetic TX and fuzzy checks use the recorded fingerprint.',
          'uncovered': ['user weekend drive', 'physical CAN/harness/device behavior', 'road and whole-fleet qualification',
                        'recordings with incompatible historical schemas'],
          'runner_sha256': vehicle.sha256(__file__), 'manifest_sha256': vehicle.sha256(MANIFEST),
          'fuzz_seed': os.environ.get('FUZZ_SEED'), 'max_examples_override': os.environ.get('MAX_EXAMPLES')}
  (output / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
  try:
    if variant not in ('debug', 'release'):
      raise ValueError('Unknown native variant')
    fixtures = load_fixtures()
    selected = [f for f in fixtures if variant in f['variants']]
    plan['fixtures'] = selected
    plan['excluded_fixtures'] = [{'id': f['id'], 'reason': 'Recorded controller configuration is outside this native variant'}
                                 for f in fixtures if variant not in f['variants']]
    plan['source'] = vehicle.source_provenance()
    paths = {f['id']: get_fixture(f, cache, download) for f in selected}
    with offline_replay():
      plan['native'] = vehicle.native_provenance()
      plan['native']['safety'] = vehicle.build_safety_library(variant == 'release', output)
      tests = make_cases(selected, paths, observed)
      ids = [t.id() for t in tests]
      plan.update(selected_test_ids=ids, status='ready')
      (output / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
      records = test_runner.run_batch(ids, capture_output=True)
    plan['source_after'] = vehicle.source_provenance()
    if plan['source']['inputs'] != plan['source_after']['inputs']:
      errors.append('Vehicle/control source inputs changed during recorded replay')
  except Exception:
    errors.append(traceback.format_exc())
  ids = [t.id() for t in tests]
  records = test_runner.account_for_tests(ids, records, tests)
  errors.extend(execution_errors(ids, records))
  if not ids:
    errors.append('Recorded replay collected no tests')
  elapsed = time.monotonic() - started
  exit_code = test_runner.report(records, errors, 5, elapsed)
  test_runner.write_json_report(output / 'results.json', ids, records, errors, elapsed, exit_code)
  plan.update(status='failed' if exit_code else 'completed', exit_code=exit_code, errors=errors,
              observations=observed, selected_test_ids=ids, result_counts=dict(Counter(r['status'] for r in records)),
              duration_seconds=elapsed, result_sha256=vehicle.sha256(output / 'results.json'))
  (output / 'coverage.json').write_text(json.dumps(plan, indent=2) + '\n')
  return exit_code


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--variant', choices=('debug', 'release'), required=True)
  parser.add_argument('--cache', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  parser.add_argument('--download', action='store_true', help='Allow pinned public CI blob downloads before offline execution')
  args = parser.parse_args()
  os.chdir(ROOT)
  os.environ.setdefault('FUZZ_SEED', '0')
  shared_memory = '/tmp' if platform.system() == 'Darwin' else '/dev/shm'
  with tempfile.TemporaryDirectory(prefix='starpilot-recorded-params-') as params, \
       tempfile.TemporaryDirectory(prefix='msgq_starpilot-recorded-', dir=shared_memory) as messaging:
    os.environ.update(PARAMS_ROOT=params, OPENPILOT_PREFIX=Path(messaging).name.removeprefix('msgq_'))
    return run(args.variant, args.cache, args.output, args.download)


if __name__ == '__main__':
  raise SystemExit(main())
