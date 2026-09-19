"""Offline, private export adapter. Never changes integration manifests or attempts."""
import argparse
import json
import math
from pathlib import Path

from prepare import ASSETS, LETTERS, copy_with_reserve, digest, normalize, write_json


def export_handoff(manifest, output, materialize=False, reserve_gib=8):
  manifest, output = Path(manifest), Path(output)
  batch = json.loads(manifest.read_text())
  rows = batch['routes']
  if sorted(r['label'] for r in rows) != LETTERS or len({r['route'] for r in rows}) != len(rows):
    raise ValueError('Require eleven unique routes with preserved A-K labels')
  if not isinstance(batch.get('configuration'), dict) or not batch['configuration']:
    raise ValueError('Inherited configuration is required')
  if output.exists():
    raise ValueError('Export must use a fresh directory; existing evidence is immutable')
  # Validate all identities/ranges before creating any output. No inferred range edits.
  for row in rows:
    if normalize(row['route'])['route'] != row['route']:
      raise ValueError('Noncanonical route')
    selection = row['selection']
    if selection['segments'] is not None or not selection.get('end_exclusive'):
      raise ValueError('Resolve selection to an end-exclusive time interval before export')
    start, end = selection['start_s'], selection['end_s']
    if not math.isfinite(start) or start < 0 or (end is not None and (not math.isfinite(end) or end <= start)):
      raise ValueError('Invalid time interval')
    if not isinstance(row['seed'], int) or isinstance(row['seed'], bool) or not 0 <= row['seed'] < 2**32:
      raise ValueError('Invalid preserved seed')
    if 'pending' in row.get('range_resolution', '').lower():
      raise ValueError('Range resolution is still pending')
  output.mkdir(parents=True, mode=0o700)
  submissions, ranges, plans = [], {}, []
  for row in rows:
    label, route, selection = row['label'], row['route'], row['selection']
    cache = row.get('cache', {})
    selected = cache.get('selected_segments', [])
    needed = set(selected) | {0}
    blockers = []
    if not selected or not cache.get('extent_verified_against_remote_listing'):
      blockers.append('Selected extent unverified')
    if row.get('analysis_status') != 'characterized':
      blockers.append('Offline analysis incomplete or blocked')
    route_root = output / 'routes' / route
    native_files, assets = [], set()
    for item in cache.get('files', []):
      segment = item['segment']
      if segment not in needed:
        continue
      source = (manifest.parent / item['path']).resolve()
      if not source.is_relative_to(manifest.parent.resolve()) or source.name not in ASSETS:
        raise ValueError('Cache path is outside this batch or has an unsupported asset')
      if not source.is_file() or source.stat().st_size != item['bytes'] or digest(source) != item['sha256']:
        blockers.append('Missing or corrupt cached asset')
        continue
      relative = Path(route.split('/')[1] + '--' + str(segment)) / source.name
      plans.append({'label': label, 'source': str(source), 'destination': str(Path('routes') / route / relative),
                    'bytes': item['bytes'], 'sha256': item['sha256']})
      if materialize:
        copy_with_reserve(source, route_root / relative, reserve_gib)
      native_files.append({'path': str(relative), 'bytes': item['bytes'], 'sha256': item['sha256']})
      assets.add((segment, source.name))
    if any(not any((s, a) in assets for a in ASSETS[:3]) for s in needed):
      blockers.append('Full logs missing, including route clock reference')
    if any((s, 'fcamera.hevc') not in assets for s in selected):
      blockers.append('Full front camera missing')
    if not materialize:
      blockers.append('Cache transfer plan only; assets not materialized')
    ready = not blockers
    if materialize:
      route_root.mkdir(parents=True, exist_ok=True)
      if ready:
        write_json(route_root / 'cache_manifest.json', {'route': route, 'native_layout': True,
                   'files': native_files, 'complete_available_files': False, 'complete_selected_files': True,
                   'selection': selection, 'source': 'Verified private preparation export'})
      else:
        (route_root / '.acquiring').write_text('Preparation incomplete. See private export manifest.\n')
    interval = {'start_seconds': selection['start_s'],
                'duration_seconds': 86400 if selection['end_s'] is None else selection['end_s'] - selection['start_s'],
                'range_resolution': 'resolved explicit preparation selection'}
    submissions.append({'label': label, 'route': route, 'seed': row['seed'], **interval,
                        'preparation_ready': ready, 'preparation_blockers': sorted(set(blockers))})
    ranges[label] = interval
  result = {'schema': 'roadscore-judging-handoff-v1', 'generation_authorized': False,
            'configuration': batch['configuration'], 'source_manifest_sha256': digest(manifest),
            'submissions': submissions}
  write_json(output / 'manifest.private.json', result)
  write_json(output / 'judging_ranges.private.json', ranges)
  write_json(output / 'cache_transfer.private.json', {'materialized': materialize, 'files': plans})
  return result


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--manifest', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  parser.add_argument('--materialize', action='store_true', help='Copy verified assets into a NEW native-layout export')
  parser.add_argument('--reserve-gib', type=float, default=8)
  args = parser.parse_args()
  result = export_handoff(args.manifest, args.output, args.materialize, args.reserve_gib)
  print('Private export created;', sum(r['preparation_ready'] for r in result['submissions']), 'ready; no generation authorized.')
