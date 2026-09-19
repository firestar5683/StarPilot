"""Private single-attempt native judging orchestration. No musical selection or uploads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PYTHON = '/usr/local/venv/bin/python'


def save(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2))
    os.chmod(temp, 0o600)
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--label', required=True, choices=list('ABCDEFGHIJK'))
    parser.add_argument('--resume-preparation', action='store_true')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    row = next(r for r in manifest['submissions'] if r['label'] == args.label)
    ranges = args.manifest.with_name('judging_ranges.private.json')
    if ranges.exists():
        row.update(json.loads(ranges.read_text()).get(args.label, {}))
    if row.get('range_resolution') == 'pending metadata':
        raise SystemExit('Resolve submitted range before launching this entry')
    frozen = ROOT / 'generated/judging_configuration.private.json'
    if frozen.exists():
        for name, digest in json.loads(frozen.read_text()).items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
                raise SystemExit('Frozen judging configuration changed: '+name)
    out = ROOT / 'results/community_judging'
    out.mkdir(exist_ok=True, mode=0o700)
    ledger = out / f'official_{args.label}.json'
    if ledger.exists():
        record = json.loads(ledger.read_text())
        if not args.resume_preparation or record['phase'] != 'preparing' or record['seed'] != row['seed']:
            raise SystemExit('Existing attempt preserved; refusing an automatic rerun')
    else:
        record = {'label': args.label, 'seed': row['seed'], 'attempt': 1, 'phase': 'preparing',
                  'started_wall': time.time(), 'configuration': manifest['configuration'], 'manual_reruns': 0}
        with ledger.open('x') as stream:
            json.dump(record, stream, indent=2)
        os.chmod(ledger, 0o600)
    env = os.environ.copy()
    env.update(ROADSCORE_GENERATION_SEED=str(row['seed']), AM_POWER_LIMIT='45')
    service = ROOT / 'prototype/worker_service.py'
    try:
        if not args.resume_preparation:
            subprocess.run([PYTHON, str(service), 'stop', '--composer', 'ace'], check=True)
            subprocess.run([PYTHON, str(service), 'start', '--composer', 'ace', '--profile', 'prism'], env=env, check=True)
        deadline = time.monotonic() + 1560
        while True:
            state = json.loads((ROOT / 'generated/ace_worker_state.json').read_text())
            if state.get('generation_seed') == row['seed'] and state.get('phase') == 'READY':
                break
            if (state.get('generation_seed') == row['seed'] and state.get('phase') == 'Stopped') or time.monotonic() > deadline:
                raise RuntimeError('Preparation stopped or timed out; original attempt retained')
            time.sleep(5)
        initial = json.loads((ROOT / 'generated/ace_initial.json').read_text())
        if initial.get('generation_seed') != row['seed']:
            raise RuntimeError('Prepared seed mismatch')
        save(out / f'preparation_{args.label}.json', initial)
        # Require the ordinary complete cache, without inspecting musical/road events.
        import sys
        sys.path.insert(0, str(ROOT / 'prototype'))
        from route_library import cache_complete
        deadline = time.monotonic() + 3600
        while not cache_complete(ROOT / 'routes' / row['route']):
            if time.monotonic() > deadline:
                raise RuntimeError('Cache not ready within one hour; no replay launched')
            time.sleep(10)
        before = set((ROOT / 'results').glob('normal_*'))
        record.update(phase='replaying', replay_started_wall=time.time())
        save(ledger, record)
        command = [str(ROOT.parent / 'onroad'), '--routeid', row['route'], '--roadscore',
                   '--composer', 'ace', '--profile', 'prism', '--muted',
                   '--start', str(row.get('start_seconds', 0)), '--duration', str(row.get('duration_seconds', 86400))]
        with (out / f'console_{args.label}.log').open('wb') as log:
            result = subprocess.run(command, env=env, cwd=ROOT.parent, stdout=log, stderr=subprocess.STDOUT)
        runs = sorted(set((ROOT / 'results').glob('normal_*')) - before)
        record.update(phase='finished' if result.returncode == 0 else 'failed', exit_code=result.returncode,
                      run_paths=[str(r) for r in runs], ended_wall=time.time())
        for run in runs:
            audit_args = [PYTHON, str(ROOT / 'tools/event_replay_audit.py'), str(run)]
            if row.get('duration_seconds', 86400) < 86400:
                audit_args += ['--expected-duration', str(row['duration_seconds'])]
            subprocess.run(audit_args, stdout=subprocess.DEVNULL, check=True)
    except Exception as error:
        record.update(phase='failed', error_type=type(error).__name__, error=str(error), ended_wall=time.time())
        raise
    finally:
        save(ledger, record)
    print(args.label, record['phase'], flush=True)


if __name__ == '__main__':
    main()
