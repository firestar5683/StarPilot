"""Mac-only judging preparation. No replay, generation, device or audio control."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import string
import sys
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
LETTERS = list(string.ascii_uppercase[:11])
ROUTE = re.compile(r'([0-9a-fA-F]{16})[|/]([a-zA-Z0-9_-]{20})(.*)')
ASSETS = ('rlog.zst', 'rlog.bz2', 'rlog', 'qlog.zst', 'qlog.bz2', 'qlog', 'fcamera.hevc', 'qcamera.ts')


def digest(path):
  h = hashlib.sha256()
  with Path(path).open('rb') as f:
    for block in iter(lambda: f.read(1024 * 1024), b''):
      h.update(block)
  return h.hexdigest()


def write_json(path, data):
  path = Path(path)
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + '.tmp')
  tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
  os.chmod(tmp, 0o600)
  tmp.replace(path)


def normalize(row):
  if isinstance(row, str):
    row = {'route': row}
  if not isinstance(row, dict) or set(row) - {'route', 'segments', 'start_s', 'end_s', 'submitter', 'note'}:
    raise ValueError('Unknown submission fields; use the documented schema')
  if not isinstance(row.get('route'), str):
    raise ValueError('route must be a string')
  raw = row['route'].strip()
  value = unquote(raw)
  is_connect = '://' in value
  if is_connect:
    url = urlparse(value)
    if url.scheme != 'https' or url.netloc not in ('connect.comma.ai', 'connect.konik.ai'):
      raise ValueError('Only HTTPS Connect route links are supported')
    if url.query or url.fragment:
      raise ValueError('URL query/fragment needs an explicit range decision; remove it and provide start_s/end_s or segments')
    value = url.path.strip('/')
  match = ROUTE.fullmatch(value)
  if not match:
    raise ValueError('Expected DONGLE/ROUTE, DONGLE|ROUTE or a Connect route link')
  dongle, route, suffix = match.groups()
  segments = None
  resolution = 'resolved syntax; metadata pending'
  if is_connect and suffix:
    times = re.fullmatch(r'/(\d+)(?:/(\d+))?', suffix)
    if not times:
      raise ValueError('Connect suffixes are seconds: /START or /START/END')
    row = dict(row)
    if 'segments' in row or 'start_s' in row or 'end_s' in row:
      raise ValueError('Conflicting URL and explicit selections')
    row['start_s'] = int(times[1])
    row['end_s'] = int(times[2]) if times[2] is not None else None
    if times[2] is None and int(times[1]) > 0:
      resolution = 'pending single-timestamp intent: current Connect displays full route without end'
    suffix = ''
  if suffix:
    single = re.fullmatch(r'(?:--|/)(\d+)', suffix)
    span = re.fullmatch(r'/(\d+):(\d+)', suffix)
    if single:
      segments = [int(single[1])]
    elif span and int(span[2]) > int(span[1]):
      segments = list(range(int(span[1]), int(span[2])))
    else:
      raise ValueError('Ambiguous segment suffix; use /N, --N, /START:STOP (exclusive) or explicit segments')
  if 'segments' in row:
    explicit = row['segments']
    if not isinstance(explicit, list) or not explicit or any(type(x) is not int or x < 0 for x in explicit):
      raise ValueError('segments must be a nonempty list of nonnegative integers')
    explicit = sorted(set(explicit))
    if segments is not None and explicit != segments:
      raise ValueError('Conflicting segment selections')
    segments = explicit
  start, end = row.get('start_s', 0), row.get('end_s')
  for v in (start, end):
    if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0):
      raise ValueError('Time ranges must contain finite nonnegative seconds')
  if start is None or (end is not None and end <= start):
    raise ValueError('end_s must be greater than start_s')
  if segments is not None and ('start_s' in row or 'end_s' in row):
    raise ValueError('Combining segment and time ranges requires a single explicit selection decision')
  selection = {'segments': segments, 'start_s': float(start), 'end_s': None if end is None else float(end),
               'time_basis': 'route_start', 'end_exclusive': True}
  return {'route': dongle.lower() + '/' + route, 'selection': selection, 'range_resolution': resolution,
          'submission': {'raw': raw, 'submitter': row.get('submitter'), 'note': row.get('note')}}


def normalize_all(rows):
  unique, duplicates, errors = [], [], []
  keys = {}
  for n, row in enumerate(rows, 1):
    try:
      item = normalize(row)
      key = json.dumps([item['route'], item['selection']], sort_keys=True)
      if key in keys:
        duplicates.append({'submission': n, 'duplicate_of': keys[key], 'provenance': item['submission']})
      else:
        item['submission_number'] = n
        unique.append(item)
        keys[key] = n
    except (ValueError, KeyError, TypeError) as e:
      errors.append({'submission': n, 'reason': str(e)})
  overlaps = []
  for i, left in enumerate(unique):
    for right in unique[i + 1:]:
      if left['route'] == right['route']:
        overlaps.append([left['submission_number'], right['submission_number']])
  return {'routes': unique, 'duplicates': duplicates, 'errors': errors, 'same_route_different_selection': overlaps}


def prepare(source, output, acknowledge=False, existing=None):
  rows = json.loads(source.read_text())
  if not isinstance(rows, list):
    raise ValueError('Input must be a JSON array')
  if output.exists():
    raise ValueError('Output already exists; mapping is immutable. Use a new batch directory')
  report = normalize_all(rows)
  output.mkdir(parents=True, mode=0o700)
  write_json(output / 'normalization.private.json', report)
  if report['errors'] or len(report['routes']) != 11 or (report['same_route_different_selection'] and not acknowledge):
    raise ValueError('Batch blocked: inspect normalization.private.json; require 11 unique selections, no errors, and acknowledge same-route selections')
  shuffled = report['routes'][:]
  random.SystemRandom().shuffle(shuffled)
  if existing:
    inherited = json.loads(existing.read_text())
    prior = inherited.get('submissions', inherited.get('routes', []))
    if {r['route'] for r in prior} != {r['route'] for r in shuffled} or sorted(r['label'] for r in prior) != LETTERS:
      raise ValueError('Existing mapping does not match this candidate set')
    lookup = {r['route']: r for r in prior}
    shuffled.sort(key=lambda r: lookup[r['route']]['label'])
  for label, row in zip(LETTERS, shuffled):
    row.update({'seed': int.from_bytes(hashlib.sha256(('roadscore-judging-v1:' + row['route']).encode()).digest()[:4], 'big'), 'label': label, 'cache_status': 'not_checked', 'analysis_status': 'not_run', 'score_status': 'not_generated'})
  if existing:
    for row in shuffled:
      if row['seed'] != lookup[row['route']]['seed']:
        raise ValueError('Existing seed violates the deterministic route-derived policy')
  batch = {'schema_version': 1, 'input_sha256': digest(source), 'generation_authorized': False,
           'mapping_policy': 'preserved existing mapping' if existing else 'SystemRandom shuffle, frozen at creation; no seed/music optimization', 'routes': shuffled}
  if existing:
    batch['inherited_manifest_sha256'] = digest(existing)
    batch['configuration'] = inherited.get('configuration')
  write_json(output / 'manifest.private.json', batch)
  write_json(output / 'blind_mapping.private.json', {r['label']: {'route': r['route'], 'selection': r['selection'], 'submission': r['submission']} for r in shuffled})
  blind = output / 'blind'
  blind.mkdir(mode=0o700)
  shutil.copyfile(Path(__file__).with_name('index.html'), blind / 'index.html')
  write_json(blind / 'batch.json', {'batch_id': digest(output / 'blind_mapping.private.json'), 'labels': LETTERS})
  return batch


def selected_segments(row, available):
  selection = row['selection']
  if selection['segments'] is not None:
    wanted = selection['segments']
  elif selection['end_s'] is not None:
    wanted = list(range(int(selection['start_s'] // 60), math.ceil(selection['end_s'] / 60)))
  else:
    # Full/open-ended routes must begin at the selected nominal minute with no holes.
    first = int(selection['start_s'] // 60)
    wanted = list(range(first, max(available, default=first - 1) + 1))
  return wanted


def cache_local(manifest, roots):
  """Copy only selected original logs/front video, never prior generated scores."""
  batch = json.loads(manifest.read_text())
  for row in batch['routes']:
    dongle, name = row['route'].split('/')
    sources = {}
    for root in roots:
      for parent in (root / dongle / name, root / dongle, root):
        if (parent / '.acquiring').exists():
          continue
        for folder in sorted(parent.glob(name + '--*')):
          suffix = folder.name[len(name) + 2:]
          if folder.is_dir() and suffix.isdigit():
            sources.setdefault(int(suffix), []).append(folder)
    wanted = selected_segments(row, sources)
    files, missing = [], []
    for segment in wanted:
      segment_assets = []
      for asset in ASSETS:
        src = next((p / asset for p in sources.get(segment, []) if (p / asset).is_file() and (p / asset).stat().st_size), None)
        if src is None:
          continue
        dest = manifest.parent / 'cache' / row['label'] / (name + '--' + str(segment)) / asset
        dest.parent.mkdir(parents=True, exist_ok=True)
        checksum = digest(src)
        if not dest.exists() or digest(dest) != checksum:
          tmp = dest.with_suffix(dest.suffix + '.partial')
          shutil.copyfile(src, tmp)
          if digest(tmp) != checksum:
            raise ValueError('Cache copy checksum mismatch')
          tmp.replace(dest)
        files.append({'segment': segment, 'path': str(dest.relative_to(manifest.parent)), 'bytes': dest.stat().st_size, 'sha256': checksum})
        segment_assets.append(asset)
      if not any(a.startswith('rlog') for a in segment_assets):
        missing.append({'segment': segment, 'asset': 'rlog'})
      if 'fcamera.hevc' not in segment_assets:
        missing.append({'segment': segment, 'asset': 'fcamera.hevc'})
    row['cache'] = {'files': files, 'selected_segments': wanted, 'missing': missing,
                    'extent_verified_against_remote_listing': False,
                    'note': 'Nominal 60s segment selection; actual timestamps must be checked in analysis. Local presence does not prove remote EOF.'}
    row['cache_status'] = 'local_assets_present_extent_unverified' if wanted and not missing else 'incomplete'
  write_json(manifest, batch)
  return batch


def fetch_remote(manifest, logs_only=False, reserve_gib=8, preview_video=False):
  """Explicit Mac HTTPS download. Native auth/host fallback, no device transport."""
  from openpilot.tools.lib.api import APIError, CommaApi, route_api_hosts
  from openpilot.tools.lib.auth_config import get_token
  import requests
  batch = json.loads(manifest.read_text())
  for row in batch['routes']:
    row['fetch_status'] = 'failed'
    try:
      listing = None
      for host in route_api_hosts():
        try:
          listing = CommaApi(get_token(host), host=host).get('v1/route/' + row['route'].replace('/', '|') + '/files', timeout=30)
          break
        except APIError as e:
          if e.status_code != 404:
            raise
      if listing is None:
        raise ValueError('No remote listing')
      assets = {}
      for urls in listing.values():
        if not isinstance(urls, list):
          continue
        for url in urls:
          parsed = urlparse(url)
          parts = unquote(parsed.path).split('/')
          if parsed.scheme != 'https' or len(parts) < 2 or not parts[-2].isdigit() or parts[-1] not in ASSETS:
            continue
          assets[(int(parts[-2]), parts[-1])] = url
      wanted = selected_segments(row, [s for s, _ in assets])
      download_segments = sorted(set(wanted + ([0] if row['selection']['segments'] is None else [])))
      name = row['route'].split('/')[1]
      files, missing = [], []
      previous_files = {f['path']: f for f in row.get('cache', {}).get('files', [])}
      row['cache'] = {'files': files, 'selected_segments': wanted, 'missing': missing,
                      'extent_verified_against_remote_listing': True, 'remote_segments': sorted({s for s, _ in assets})}
      row['cache_status'] = 'acquiring'
      for segment in download_segments:
        # Prefer full logs and road camera; qlog/qcamera are diagnostic fallbacks.
        chosen = []
        groups = (ASSETS[:6],) if logs_only or segment not in wanted else (ASSETS[:6], ASSETS[7:] if preview_video else ASSETS[6:7])
        for alternatives in groups:
          chosen += [next((a for a in alternatives if (segment, a) in assets), None)]
        for asset in filter(None, chosen):
          dest = manifest.parent / 'cache' / row['label'] / (name + '--' + str(segment)) / asset
          dest.parent.mkdir(parents=True, exist_ok=True)
          previous = previous_files.get(str(dest.relative_to(manifest.parent)))
          if not previous or not dest.is_file() or digest(dest) != previous['sha256']:
            if shutil.disk_usage(manifest.parent).free < reserve_gib * 1024**3:
              raise OSError('Disk reserve reached')
            tmp = dest.with_suffix(dest.suffix + '.partial')
            with requests.get(assets[(segment, asset)], stream=True, timeout=(20, 90)) as response:
              response.raise_for_status()
              with tmp.open('wb') as out:
                for chunk in response.iter_content(1024 * 1024):
                  if shutil.disk_usage(manifest.parent).free - len(chunk) < reserve_gib * 1024**3:
                    raise OSError('Disk reserve reached')
                  out.write(chunk)
            if not tmp.stat().st_size:
              raise ValueError('Empty remote asset')
            tmp.replace(dest)
          files.append({'segment': segment, 'path': str(dest.relative_to(manifest.parent)), 'bytes': dest.stat().st_size, 'sha256': digest(dest), 'clock_reference_only': segment not in wanted})
          write_json(manifest, batch)
        if not any(a in chosen for a in ASSETS[:3]):
          missing.append({'segment': segment, 'asset': 'rlog'})
        if segment in wanted and 'fcamera.hevc' not in chosen:
          missing.append({'segment': segment, 'asset': 'fcamera.hevc'})
      row['cache'] = {'files': files, 'selected_segments': wanted, 'missing': missing,
                      'extent_verified_against_remote_listing': True, 'remote_segments': sorted({s for s, _ in assets})}
      row['cache_status'] = 'available_listing_cached' if wanted and not missing else 'incomplete'
      row['fetch_status'] = 'completed'
      print(row['label'], 'cached', len(files), 'files', flush=True)
    except Exception as e:
      print(row['label'], 'fetch failed', type(e).__name__, flush=True)
      # Exception text can contain signed URLs or authentication material.
      row['fetch_status'] = 'failed:' + type(e).__name__
      row['cache_status'] = 'fetch_failed_needs_review'
    write_json(manifest, batch)
  return batch


def metadata(manifest):
  """Read route extent metadata without coordinates, tokens or signed URL persistence."""
  from openpilot.tools.lib.api import APIError, CommaApi, route_api_hosts
  from openpilot.tools.lib.auth_config import get_token
  batch = json.loads(manifest.read_text())
  out = {}
  for row in batch['routes']:
    for host in route_api_hosts():
      try:
        meta = CommaApi(get_token(host), host=host).get('v1/route/' + row['route'].replace('/', '|'), timeout=30)
        fields = ('duration', 'start_time', 'end_time', 'maxqlog', 'maxlog', 'maxcamera', 'maxqcamera',
                  'start_time_utc_millis', 'end_time_utc_millis', 'size')
        out[row['label']] = {'status': 'available', 'metadata': {k: meta[k] for k in fields if k in meta}}
        break
      except APIError as e:
        out[row['label']] = {'status': 'failed', 'status_code': e.status_code}
        if e.status_code != 404:
          break
      except Exception as e:
        out[row['label']] = {'status': 'failed', 'type': type(e).__name__}
        break
    write_json(manifest.parent / 'route_metadata.private.json', out)
  return out


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  sub = parser.add_subparsers(dest='action', required=True)
  p = sub.add_parser('prepare')
  p.add_argument('--submissions', required=True, type=Path)
  p.add_argument('--output', required=True, type=Path)
  p.add_argument('--acknowledge-same-route-selections', action='store_true')
  p.add_argument('--existing-manifest', type=Path)
  p = sub.add_parser('cache')
  p.add_argument('--manifest', required=True, type=Path)
  p.add_argument('--source', action='append', default=[], type=Path)
  p = sub.add_parser('fetch')
  p.add_argument('--manifest', required=True, type=Path)
  modes = p.add_mutually_exclusive_group()
  modes.add_argument('--logs-only', action='store_true')
  modes.add_argument('--preview-video', action='store_true', help='Cache smaller qcamera previews; full-camera readiness remains false')
  p.add_argument('--reserve-gib', type=float, default=8)
  p = sub.add_parser('metadata')
  p.add_argument('--manifest', required=True, type=Path)
  args = parser.parse_args()
  if args.action == 'prepare':
    prepare(args.submissions, args.output, args.acknowledge_same_route_selections, args.existing_manifest)
  elif args.action == 'cache':
    cache_local(args.manifest, args.source)
  elif args.action == 'fetch':
    fetch_remote(args.manifest, args.logs_only, args.reserve_gib, args.preview_video)
  else:
    metadata(args.manifest)
  print('Preparation operation complete. No RoadScore generation was run.')


if __name__ == '__main__':
  main()
