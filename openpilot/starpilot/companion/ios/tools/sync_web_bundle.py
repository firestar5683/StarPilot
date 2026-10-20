#!/usr/bin/env python3
"""Keep the iOS app's bundled Galaxy web UI in step with the Galaxy web sources.

  python3 sync_web_bundle.py          copy the sources into the bundle and rewrite its manifest
  python3 sync_web_bundle.py --check  exit 1 if the bundle has drifted from the sources
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

IOS = Path(__file__).resolve().parents[1]
SOURCE = IOS.parents[1] / 'galaxy' / 'web'
BUNDLE = IOS / 'GalaxyBluetooth' / 'Resources' / 'Web'
MANIFEST = 'galaxy-native-manifest.json'

# Preview-only data must never ship inside the app (see tests/check_secretgood_bundle.py).
EXCLUDED = ('data/runtime.json', 'data/system-monitor.sample.json', 'assets/mobile/')
# Bundle-specific files kept as they are: the app has no Jetlink model controls. Each maps to the SHA-256 of the
# galaxy/web file it was trimmed from, so a change to that source is flagged and the copy can be re-trimmed.
PINNED = {'js/models.js': 'a66eafe5930c974c520946bfe216fcb61ebb045d153acd249213504682668d15'}


def wanted(path: str) -> bool:
  return not path.startswith(EXCLUDED[2]) and path not in EXCLUDED[:2]


def source_files() -> list[str]:
  return sorted(p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*') if p.is_file() and wanted(p.relative_to(SOURCE).as_posix()))


def expected(path: str) -> bytes:
  return (BUNDLE if path in PINNED else SOURCE).joinpath(path).read_bytes()


def manifest_for(paths: list[str]) -> dict:
  old = json.loads((BUNDLE / MANIFEST).read_text())
  files = [{'path': p, 'size': len(expected(p)), 'sha256': hashlib.sha256(expected(p)).hexdigest()} for p in paths]
  return {**old, 'files': files}


def render(manifest: dict) -> str:
  return json.dumps(manifest, separators=(',', ':')) + '\n'


def drift() -> list[str]:
  paths = source_files()
  problems = [f'{p}: differs from galaxy/web' for p in paths
              if p not in PINNED and (not (BUNDLE / p).is_file() or (BUNDLE / p).read_bytes() != (SOURCE / p).read_bytes())]
  problems += [f'{p}: pinned file missing from the bundle' for p in PINNED if not (BUNDLE / p).is_file()]
  problems += [f'{p}: galaxy/web changed since the pinned copy was trimmed; re-trim it and update its hash in PINNED'
               for p, digest in PINNED.items() if hashlib.sha256((SOURCE / p).read_bytes()).hexdigest() != digest]
  problems += [f'{p.relative_to(BUNDLE).as_posix()}: not in galaxy/web' for p in sorted(BUNDLE.rglob('*'))
               if p.is_file() and p.name != MANIFEST and p.relative_to(BUNDLE).as_posix() not in paths]
  if not problems and (BUNDLE / MANIFEST).read_text() != render(manifest_for(paths)):
    problems.append(f'{MANIFEST}: sizes or hashes are stale')
  return problems


def sync() -> None:
  paths = source_files()
  for stale in sorted(BUNDLE.rglob('*')):
    relative = stale.relative_to(BUNDLE).as_posix()
    if stale.is_file() and stale.name != MANIFEST and relative not in paths:
      stale.unlink()
  for path in paths:
    if path not in PINNED:
      target = BUNDLE / path
      target.parent.mkdir(parents=True, exist_ok=True)
      target.write_bytes((SOURCE / path).read_bytes())
  (BUNDLE / MANIFEST).write_text(render(manifest_for(paths)))


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('--check', action='store_true', help='fail instead of writing when the bundle has drifted')
  if not parser.parse_args().check:
    sync()
    print(f'Synced {len(source_files())} files into the iOS bundle')
    return 0
  problems = drift()
  for problem in problems:
    print(problem, file=sys.stderr)
  if problems:
    print('The iOS web bundle has drifted. Run: python3 openpilot/starpilot/companion/ios/tools/sync_web_bundle.py', file=sys.stderr)
    return 1
  print('iOS web bundle matches galaxy/web')
  return 0


if __name__ == '__main__':
  sys.exit(main())
