"""Sequential private batch; never resets hardware or repeats an existing attempt."""
import argparse
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PYTHON = '/usr/local/venv/bin/python'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    out = ROOT / 'results/community_judging'
    failures = 0
    for label in 'ABCDEFGHIJK':
        ledger = out / f'official_{label}.json'
        if ledger.exists():
            # The original A preparation/replay is already owned by its runner.
            deadline = time.monotonic() + 7200
            while json.loads(ledger.read_text()).get('phase') in ('preparing', 'replaying'):
                if time.monotonic() > deadline:
                    raise RuntimeError('Existing attempt did not finish; refusing to take it over')
                time.sleep(5)
        else:
            with (out / f'orchestrator_{label}.log').open('wb') as log:
                subprocess.run([PYTHON, str(ROOT / 'tools/judging_run.py'), str(args.manifest), '--label', label], stdout=log, stderr=subprocess.STDOUT)
        record = json.loads(ledger.read_text()) if ledger.exists() else {'phase': 'failed'}
        print(label, record['phase'], flush=True)
        # Preserve failed route evidence and continue, but never grind through a known link fault.
        link = ROOT / 'generated/ace_link.jsonl'
        if link.exists():
            last = json.loads(link.read_text().splitlines()[-1])
            if last.get('healthy') is False:
                raise RuntimeError('Chestnut link fault; batch paused without reset')
        failures = failures+1 if record['phase'] == 'failed' else 0
        if failures >= 3:
            raise RuntimeError('Three consecutive attempt failures; inspect pipeline before continuing')
        subprocess.run(['/data/sa3-feasibility/venv/bin/python', str(ROOT / 'tools/judging_review.py'), str(out)], check=True)
    subprocess.run([PYTHON, str(ROOT / 'prototype/worker_service.py'), 'stop', '--composer', 'ace'], check=True)
    print('Batch finished; worker stopped. All runs requested muted output.', flush=True)


if __name__ == '__main__':
    main()
