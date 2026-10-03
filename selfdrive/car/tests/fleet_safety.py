"""Offline current-controller -> current-safety checks using the registered fleet routes.

No Panda connection, vehicle processes, or actuation. Missing evidence is not a pass.
Run with: python -m selfdrive.car.tests.fleet_safety --help
"""
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import uuid

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = Path(__file__).parent / 'fleet_results'


def digest(path):
  return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory():
  from opendbc.car.values import PLATFORMS
  from opendbc.car.tests.routes import routes, non_tested_cars
  registered = defaultdict(list)
  for route in routes:
    registered[str(route.car_model)].append(dict(route=route.route, segment=route.segment))
  exempt = set(map(str, non_tested_cars))
  return [dict(platform=str(platform), routes=registered[str(platform)],
               declared_without_route=str(platform) in exempt,
               status='pending' if registered[str(platform)] else 'uncovered')
          for platform in sorted(PLATFORMS)]


def build_safety(out, release=False):
  source = ROOT / 'opendbc_repo/opendbc/safety/tests/libsafety/safety.c'
  target = out / ('safety_release' if release else 'safety_debug')
  target.mkdir(parents=True, exist_ok=True)
  command = [os.environ.get('CC', 'cc'), '-shared', '-fPIC', '-std=gnu11', '-Wall', '-Werror',
             '-I', str(ROOT/'opendbc_repo'), str(source), '-o', str(target/'libsafety.so')]
  if not release:
    command.insert(1, '-DALLOW_DEBUG')
  else:
    # Some hooks declare constants only consumed by ALLOW_DEBUG branches.
    # Keep the compiler diagnostic, without making a host-only warning prevent
    # checking which configurations the release registry actually supports.
    command.insert(1, '-Wno-error=unused-variable')
  result = subprocess.run(command, capture_output=True, text=True, timeout=120)
  (target/'build.log').write_text(result.stdout + result.stderr)
  result.check_returncode()
  shutil.copy2(source.with_name('libsafety_py.py'), target/'libsafety_py.py')
  headers = sorted((ROOT/'opendbc_repo/opendbc/safety').rglob('*.h'))
  provenance = dict(command=command, release=release, library_sha256=digest(target/'libsafety.so'),
                    source_sha256=digest(source), headers={str(p.relative_to(ROOT)): digest(p) for p in headers})
  (target/'build.json').write_text(json.dumps(provenance, indent=2))
  return target


def load_safety(directory, panda_index):
  # Each Panda gets independent C globals, never multiple handles to one library.
  target = directory.parent / f'{directory.name}_panda_{panda_index}'
  target.mkdir(exist_ok=True)
  for name in ('libsafety.so', 'libsafety_py.py'):
    shutil.copy2(directory/name, target/name)
  spec = importlib.util.spec_from_file_location(f'fleet_safety_panda_{panda_index}', target/'libsafety_py.py')
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


def test_toggles(scenario):
  # Explicit fixture; do not read the operator's installed settings.
  return SimpleNamespace(always_on_lateral=scenario != 'recorded', always_on_lateral_main=scenario == 'aol-main',
                         always_on_lateral_lkas=False, car_model='', cluster_offset=1.0,
                         disable_openpilot_long=False, force_fingerprint=False, lock_doors=False, lock_doors_speed=0.0,
                         sng_hack=False, subaru_sng=False, subaru_sng_manual_parking_brake=False,
                         tesla_cooperative_steering=False, unlock_doors=False, unlock_doors_trigger=0,
                         vEgoStopping=0.5, volt_sng=False)


def read_route(route, segment, local_log=None):
  from openpilot.tools.lib.logreader import LogReader, openpilotci_source
  errors = []
  for seg in ([segment] if segment is not None else [2, 1, 0]):
    identifier = local_log or f'{route}/{seg}'
    try:
      selected = [m for m in LogReader(identifier, sources=[openpilotci_source], sort_by_time=True)
                  if m.which() in ('can', 'carControl', 'carParams')]
      if not any(m.which() == 'carParams' for m in selected):
        raise ValueError('No recorded CarParams')
      if not any(m.which() == 'carControl' for m in selected):
        raise ValueError('No recorded control requests; active coverage unavailable')
      return selected, identifier
    except Exception as error:
      errors.append(f'{identifier}: {type(error).__name__}: {error}')
      if local_log:
        break
  raise RuntimeError('; '.join(errors))


def run_case(platform, route, segment, scenario, safety_dir, local_log=None):
  from opendbc.car import gen_empty_fingerprint
  from opendbc.car.can_definitions import CanData
  from opendbc.car.car_helpers import interfaces
  from opendbc.car.fingerprints import MIGRATION
  from opendbc.safety import ALTERNATIVE_EXPERIENCE
  from openpilot.selfdrive.car.tests.fleet_safety_core import effective_safety_configs, TxAudit

  messages, identifier = read_route(route, segment, local_log)
  recorded = next(m.carParams for m in messages if m.which() == 'carParams')
  detected = MIGRATION.get(recorded.carFingerprint, recorded.carFingerprint)
  if detected != platform:
    raise ValueError(f'Fixture identity mismatch: {detected} != {platform}')
  fingerprint = gen_empty_fingerprint()
  for msg in messages:
    if msg.which() == 'can':
      for frame in msg.can:
        if frame.src < 64:
          fingerprint.setdefault(frame.src, {})[frame.address] = len(frame.dat)
  toggles = test_toggles(scenario)
  interface = interfaces[platform]
  cp = interface.get_params(platform, fingerprint, list(recorded.carFw),
                            recorded.openpilotLongitudinalControl, False, docs=False, starpilot_toggles=toggles)
  fp = interface.get_starpilot_params(platform, fingerprint, list(recorded.carFw), cp, toggles)
  if cp.dashcamOnly or cp.notCar:
    return dict(status='uncovered', reason='Current interface is dashcamOnly/notCar', platform=platform, scenario=scenario)
  if scenario == 'aol-main':
    cp.alternativeExperience |= ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL
    fp.alternativeExperience |= ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL
  configs = effective_safety_configs(cp, fp)
  audits = {}
  modules = {}
  for cfg in configs:
    if cfg.safety_model in (0, 19):  # SILENT/noOutput; any attempted TX below is a failure.
      continue
    module = load_safety(safety_dir, cfg.panda_index)
    safety = module.libsafety
    if safety.set_safety_hooks(cfg.safety_model, cfg.safety_param) != 0:
      raise ValueError(f'Safety configuration unavailable in built library: {cfg}')
    safety.init_tests()
    safety.set_alternative_experience(cfg.alternative_experience)
    modules[cfg.panda_index] = module
    audits[cfg.panda_index] = TxAudit(safety, module.make_CANPacket, config=cfg)
  ci = interface(cp, fp)
  from inspect import getfile
  imported = {getfile(interface), getfile(type(ci.CC)), getfile(type(ci.CS))}
  for path in imported:
    if not Path(path).resolve().is_relative_to(ROOT/'opendbc_repo/opendbc/car'):
      raise RuntimeError('Controller imports outside the tested checkout: ' + path)
  source_hashes = {str(Path(p).resolve().relative_to(ROOT)): digest(p) for p in imported}
  first = messages[0].logMonoTime
  pending = []
  coverage = Counter()
  errors = []
  previous = None
  previous_command = None
  warmed = False
  for msg in messages:
    elapsed = (msg.logMonoTime-first)/1e9
    if elapsed > 2 and not warmed:
      # Keep safety/controller history established during startup, but report the
      # scored interval separately from the explicit two-second fixture warmup.
      audits = {cfg.panda_index: TxAudit(modules[cfg.panda_index].libsafety,
                modules[cfg.panda_index].make_CANPacket, config=cfg)
                for cfg in configs if cfg.panda_index in modules}
      warmed = True
    for module in modules.values():
      module.libsafety.set_timer((msg.logMonoTime//1000) & 0xffffffff)
    if msg.which() == 'can':
      rx = [CanData(f.address, bytes(f.dat), f.src) for f in msg.can if f.src < 64]
      pending.append((msg.logMonoTime, rx))
      for frame in rx:
        index = frame.src//4
        if index not in modules:
          continue
        module = modules[index]
        accepted = module.libsafety.safety_rx_hook(module.make_CANPacket(frame.address, frame.src-index*4, frame.dat))
        if not accepted and elapsed > 2:
          coverage['rx_rejections'] += 1
      continue
    if msg.which() != 'carControl':
      continue
    cs, _ = ci.update(pending, toggles)
    pending.clear()
    cc = msg.carControl.as_builder()
    if previous_command is not None and msg.logMonoTime-previous_command > 100_000_000:
      coverage['command_gaps_over_100ms'] += 1
    previous_command = msg.logMonoTime
    if scenario == 'aol-main':
      # This is a controller/safety MAIN-availability probe, not a substitute for
      # testing StarPilotCard's separate LKAS-button latch or full selfdrived loop.
      cc.enabled = False
      cc.longActive = False
      cc.cruiseControl.cancel = False
      cc.cruiseControl.resume = False
      cc.latActive = bool(cs.canValid and cs.cruiseState.available and
                          str(cs.gearShifter) in ('drive', 'sport', 'low', 'eco', 'manumatic') and
                          not (cs.steerFaultTemporary or cs.steerFaultPermanent or cs.steeringDisengage or cs.brakePressed) and
                          (cp.steerAtStandstill or not cs.standstill))
    state = (bool(cc.latActive), bool(cc.longActive), bool(cs.brakePressed), bool(cs.gasPressed), bool(cs.standstill))
    if elapsed > 2:
      coverage['control_frames'] += 1
      coverage['lat_active_frames'] += bool(cc.latActive)
      coverage['long_active_frames'] += bool(cc.longActive)
      coverage['lat_only_frames'] += bool(cc.latActive and not cc.longActive)
      coverage['brake_frames'] += bool(cs.brakePressed)
      coverage['gas_frames'] += bool(cs.gasPressed)
      coverage['standstill_frames'] += bool(cs.standstill)
      coverage['invalid_carstate_frames'] += not cs.canValid
      if previous is not None and previous[0] != state[0]:
        coverage['lateral_transitions'] += 1
      for module in modules.values():
        module.libsafety.safety_tick_current_safety_config()
        coverage['invalid_safety_rx_frames'] += not module.libsafety.safety_config_valid()
    previous = state
    _, frames = ci.apply(cc.as_reader(), msg.logMonoTime, toggles)
    for addr, data, bus in frames:
      if bus//4 not in audits:
        errors.append(f'Unconfigured outgoing bus {bus} at {msg.logMonoTime}')
        continue
      audit = audits[bus//4]
      audit.check(addr, bus, bytes(data), msg.logMonoTime, scenario,
                  requested_lat_active=bool(cc.latActive), requested_long_active=bool(cc.longActive))
  summaries = {str(index): audit.summary() for index, audit in audits.items()}
  missing = [name for name in ('lat_active_frames', 'lateral_transitions') if coverage[name] == 0]
  if coverage['lat_active_frames'] < 100:
    missing.append('at_least_100_active_control_frames')
  if coverage['command_gaps_over_100ms']:
    missing.append('continuous_recorded_control_timing')
  if not summaries or any(s['status'] == 'uncovered' for s in summaries.values()):
    missing.append('active_tx_authorization_and_request')
  if scenario == 'aol-main' and coverage['lat_only_frames'] == 0:
    missing.append('lat_only_frames')
  if scenario == 'aol-main' and not any(s['requested_aol_only_tx'] for s in summaries.values()):
    missing.append('requested_steering_with_aol_only_safety_permission')
  failed = bool(errors or any(s['status'] == 'failed' for s in summaries.values()) or
                any(coverage[k] for k in ('rx_rejections', 'invalid_carstate_frames', 'invalid_safety_rx_frames')))
  status = 'failed' if failed else 'uncovered' if missing else 'pass'
  return dict(platform=platform, route=identifier, scenario=scenario, status=status,
              missing_coverage=missing, coverage=dict(coverage), errors=errors[:30],
              safety_configs=[asdict(c) for c in configs], panda_results=summaries, source_hashes=source_hashes,
              warmup_seconds=2,
              configuration_policy='Recorded actuator requests under current default settings, or explicit AOL MAIN probe',
              recorded_alternative_experience=int(recorded.alternativeExperience),
              limitations=['Controller/safety only: no modeld, selfdrived/AOL latch, UI or physical ECU simulation',
                           'Uses recorded actuator requests; does not test new model outputs or every optional feature'])


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--inventory', action='store_true')
  parser.add_argument('--platform', action='append', default=[])
  parser.add_argument('--all', action='store_true')
  parser.add_argument('--shard-count', type=int, default=1)
  parser.add_argument('--shard-index', type=int, default=0)
  parser.add_argument('--scenario', action='append', choices=['recorded', 'aol-main'])
  parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
  parser.add_argument('--release', action='store_true', help='Build without ALLOW_DEBUG')
  parser.add_argument('--local-log', help='Explicit local rlog, requires one selected platform')
  parser.add_argument('--case-timeout', type=float, default=180)
  parser.add_argument('--worker', type=Path, help=argparse.SUPPRESS)
  args = parser.parse_args()
  if args.shard_count < 1 or not 0 <= args.shard_index < args.shard_count:
    parser.error('Require 0 <= shard-index < shard-count')
  args.out = args.out.resolve()
  args.out.mkdir(parents=True, exist_ok=True)
  if args.worker:
    case = json.loads(args.worker.read_text())
    # Isolate any Params access by interfaces from real operator settings.
    with tempfile.TemporaryDirectory(prefix='fleet-params-') as params:
      os.environ.update(PARAMS_ROOT=params, OPENPILOT_PREFIX='fleet-offline-'+str(os.getpid()))
      try:
        result = run_case(case['platform'], case['route'], case['segment'], case['scenario'],
                          Path(case['safety_dir']), case.get('local_log'))
      except Exception as error:
        import traceback
        result = dict(status='error', error=repr(error), traceback=traceback.format_exc())
      result['execution_id'] = case['execution_id']
      args.worker.with_suffix('.result.json').write_text(json.dumps(result, indent=2))
    return 0 if result['status'] == 'pass' else 1
  entries = inventory()
  report = dict(platforms=entries, total_platforms=len(entries),
                with_routes=sum(bool(e['routes']) for e in entries),
                registered_routes=sum(len(e['routes']) for e in entries),
                scope='offline controller/safety compatibility; not full vehicle validation')
  (args.out/'inventory.json').write_text(json.dumps(report, indent=2))
  if args.inventory:
    print(json.dumps({k:v for k,v in report.items() if k != 'platforms'}, indent=2))
    return 0
  if not args.all and not args.platform:
    parser.error('Choose --all or --platform; --inventory only lists coverage')
  unknown = set(args.platform)-{e['platform'] for e in entries}
  if unknown:
    parser.error('Unknown platforms: '+', '.join(sorted(unknown)))
  if args.local_log and (len(args.platform) != 1 or args.all):
    parser.error('--local-log requires exactly one --platform')
  (args.out/'results.json').write_text(json.dumps(dict(cases=[], counts={}, state='running')))
  try:
    safety_dir = build_safety(args.out, args.release)
  except (subprocess.SubprocessError, OSError) as error:
    failure = dict(status='error', reason='Safety build failed', error=repr(error))
    (args.out/'results.json').write_text(json.dumps(dict(cases=[failure], counts={'error': 1}), indent=2))
    print(failure['reason'] + ': ' + failure['error'], flush=True)
    return 1
  selected = [e for e in entries if args.all or e['platform'] in args.platform]
  selected = selected[args.shard_index::args.shard_count]
  results = []
  for entry in selected:
    registered = entry['routes']
    if args.local_log:
      registered = [dict(route='local', segment=0)]
    if not registered:
      results.append(dict(platform=entry['platform'], status='uncovered', reason='No registered route'))
      continue
    for route in registered:
      for scenario in args.scenario or ['recorded', 'aol-main']:
        case = dict(platform=entry['platform'], **route, scenario=scenario, safety_dir=str(safety_dir),
                    local_log=args.local_log, execution_id=uuid.uuid4().hex)
        path = args.out / f'case_{len(results):04d}.json'
        path.write_text(json.dumps(case))
        path.with_suffix('.result.json').unlink(missing_ok=True)
        print(f"Checking {entry['platform']} {scenario} {route['route']}", flush=True)
        with path.with_suffix('.log').open('w') as log:
          try:
            completed = subprocess.run([sys.executable, '-m', 'selfdrive.car.tests.fleet_safety', '--worker', str(path)],
                                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=args.case_timeout, check=False)
            result = json.loads(path.with_suffix('.result.json').read_text())
            if result.get('execution_id') != case['execution_id'] or completed.returncode != (0 if result.get('status') == 'pass' else 1):
              raise ValueError('Worker identity/exit status does not match its report')
          except (subprocess.TimeoutExpired, OSError, ValueError) as error:
            result = dict(status='error', error=repr(error))
        results.append({**case, **result})
        print('  '+result['status'], flush=True)
        (args.out/'results.json').write_text(json.dumps(dict(cases=results, counts=dict(Counter(r['status'] for r in results))), indent=2))
  counts = Counter(r['status'] for r in results)
  (args.out/'results.json').write_text(json.dumps(dict(cases=results, counts=dict(counts)), indent=2))
  print(json.dumps(dict(counts), indent=2))
  return 0 if results and all(r['status'] == 'pass' for r in results) else 1


if __name__ == '__main__':
  raise SystemExit(main())
