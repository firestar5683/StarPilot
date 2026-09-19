"""Reuse complete local preparation caches without importing their judging policy."""
import json
import subprocess
from pathlib import Path


def preparation_roots(root):
  roots = [Path(root)]
  try:
    result = subprocess.run(['git', 'worktree', 'list', '--porcelain'], cwd=root,
                            capture_output=True, text=True, timeout=2, check=True)
    roots.extend(Path(line[9:]) / 'roadscore' for line in result.stdout.splitlines()
                 if line.startswith('worktree '))
  except (OSError, subprocess.SubprocessError):
    pass
  return list(dict.fromkeys(roots))


def manifest_source(manifest, route):
  try:
    document = json.loads(manifest.read_text())
    for entry in document.get('routes', []):
      if entry.get('route') != route:
        continue
      selection = entry.get('selection', {})
      cache = entry.get('cache', {})
      remote = cache.get('remote_segments', [])
      if (selection.get('start_s') != 0 or selection.get('end_s') is not None
          or selection.get('segments') is not None or not remote
          or not cache.get('extent_verified_against_remote_listing')
          or sorted(cache.get('selected_segments', [])) != sorted(remote)):
        continue
      files = cache.get('files', [])
      parents = set()
      assets = {segment: set() for segment in remote}
      for item in files:
        if item.get('clock_reference_only'):
          continue
        path = manifest.parent / item['path']
        if not path.is_file() or path.stat().st_size != item['bytes']:
          break
        segment = item['segment']
        if segment not in assets or path.parent.name != route.split('/')[1] + '--' + str(segment):
          break
        parents.add(path.parent.parent)
        assets[segment].add(path.name)
      else:
        logs = {'rlog', 'rlog.zst', 'rlog.bz2', 'qlog', 'qlog.zst', 'qlog.bz2'}
        cameras = {'fcamera.hevc', 'qcamera.ts'}
        if len(parents) == 1 and all(names & logs and names & cameras for names in assets.values()):
          parent = parents.pop()
          if not (parent / '.acquiring').exists():
            return parent
  except (OSError, ValueError, KeyError, TypeError, AttributeError):
    pass
  return None


def prepared_source(route, root):
  for source in preparation_roots(root):
    for manifest in sorted((source / 'results').glob('**/manifest.private.json')):
      candidate = manifest_source(manifest, route)
      if candidate is not None:
        return candidate
  return None
