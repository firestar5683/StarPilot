"""Private single-attempt native judging orchestration. No musical selection or uploads."""
import argparse
import hashlib
import json
import os
import math
import re
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



def validate_frozen_configuration(root, frozen=None):
    """Refuse official work unless a nonempty local freeze verifies completely."""
    frozen = frozen or root / 'generated/judging_configuration.private.json'
    try:
        entries = json.loads(frozen.read_text())
    except (OSError, ValueError) as error:
        raise SystemExit('Valid frozen judging configuration is required') from error
    if not isinstance(entries, dict) or not entries:
        raise SystemExit('Frozen judging configuration must be a nonempty file/hash mapping')
    for name, digest in entries.items():
        if (not isinstance(name, str) or not name or Path(name).is_absolute()
                or '..' in Path(name).parts or not isinstance(digest, str)
                or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)):
            raise SystemExit('Invalid frozen judging configuration entry')
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('Frozen judging configuration path escapes project')
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise SystemExit('Frozen judging configuration file unavailable: ' + name) from error
        if actual != digest:
            raise SystemExit('Frozen judging configuration changed: ' + name)


def validate_handoff_readiness(manifest, row):
    """Preparation exports are inert until explicitly authorized and complete."""
    if manifest.get('schema') == 'roadscore-judging-handoff-v1':
        if manifest.get('generation_authorized') is not True:
            raise SystemExit('Judging handoff has not been authorized for generation')
        if row.get('preparation_ready') is not True or row.get('preparation_blockers') != []:
            raise SystemExit('Judging handoff preparation is incomplete or blocked')


def attempt_configuration(manifest, manifest_path, root):
    """Keep future policy evidence separate from historical attempts and freezes."""
    config = manifest['configuration']
    if manifest.get('schema') != 'roadscore-judging-handoff-v1':
        raise SystemExit('Export a versioned judging handoff; historical attempts are preserved')
    version = config.get('policy_version', '')
    if not isinstance(version, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', version):
        raise SystemExit('A safe, explicit judging policy_version is required')
    mode, cap = config.get('hardware_mode'), config.get('power_limit_watts')
    env = os.environ.copy()
    env.pop('AM_POWER_LIMIT', None)
    if mode == 'full-speed' and cap is None:
        pass
    elif mode == 'capped' and isinstance(cap, (int, float)) and not isinstance(cap, bool) and math.isfinite(cap) and cap > 0:
        env['AM_POWER_LIMIT'] = str(cap)
    else:
        raise SystemExit('Declare full-speed with no cap, or an explicit capped policy')
    return (root / 'results/community_judging' / version,
            manifest_path.with_name('configuration.freeze.private.json'), env)


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
    validate_handoff_readiness(manifest, row)
    out, frozen, env = attempt_configuration(manifest, args.manifest, ROOT)
    validate_frozen_configuration(ROOT, frozen)
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
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
    env['ROADSCORE_GENERATION_SEED'] = str(row['seed'])
    env['ROADSCORE_SEED_ORIGIN'] = 'judging-route'
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
                   '--roadscore-seed', str(row['seed']),
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
