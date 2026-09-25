#!/usr/bin/env python3
"""Normalize valid current-schema v1 Event caches before an offline source update."""

import argparse
import json
import os
from pathlib import Path
import sys


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--params-path', required=True, help='Existing Params root containing the active namespace')
  parser.add_argument('--backup-dir', required=True, help='Private backup directory outside Params')
  parser.add_argument('--producers-stopped', action='store_true', required=True,
                      help='Assert the caller has stopped every cache producer before this operation')
  args = parser.parse_args()

  namespace = Path(args.params_path) / os.environ.get('OPENPILOT_PREFIX', 'd')
  if not Path(args.params_path).is_dir() or not namespace.is_dir():
    parser.error('--params-path must already contain the existing Params namespace')

  from openpilot.common.params import Params
  from openpilot.starpilot.schema_cache_normalize import normalize_current_event_caches

  try:
    params = Params(args.params_path)
    report = normalize_current_event_caches(params, args.backup_dir, producers_stopped=args.producers_stopped)
  except (OSError, RuntimeError, ValueError) as error:
    print(json.dumps({'status': 'failed', 'error': f'{type(error).__name__}: {error}'}), file=sys.stderr)
    return 1
  print(json.dumps(report, indent=2))
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
