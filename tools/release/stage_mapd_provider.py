#!/usr/bin/env python3
"""Verify a prebuilt Mapd provider, then copy it into a release tree."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

SOURCE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE_ROOT))
from openpilot.starpilot.maps.artifact import elf_arm64_static_file, source_digest


PROVIDER = Path('openpilot/starpilot/maps/provider')
MANIFEST_LIMIT = 4096
BINARY_LIMIT = 128 * 1024 * 1024
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')


def _regular(path: Path, *, max_bytes: int, executable: bool = False):
  info = path.lstat()
  if (not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= max_bytes or
      executable and not info.st_mode & 0o111):
    raise ValueError(f'invalid Mapd package file: {path}')
  descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
  file = os.fdopen(descriptor, 'rb')
  if not stat.S_ISREG(os.fstat(descriptor).st_mode):
    file.close()
    raise ValueError(f'invalid Mapd package file: {path}')
  return file


def _directories(root: Path, *, provider: bool = True) -> None:
  relatives = (Path('.'), Path('openpilot'), Path('openpilot/starpilot'), Path('openpilot/starpilot/maps'))
  for relative in relatives + ((PROVIDER,) if provider else ()):
    path = root / relative
    if not stat.S_ISDIR(path.lstat().st_mode):
      raise ValueError(f'unsafe Mapd package directory: {path}')


def _unique(pairs):
  result = {}
  for key, value in pairs:
    if key in result:
      raise ValueError('duplicate Mapd manifest field')
    result[key] = value
  return result


def validate_provider(source: Path) -> dict:
  source = Path(source)
  _directories(source)
  binary = source / PROVIDER / 'mapd'
  manifest_path = source / PROVIDER / 'manifest.json'
  with _regular(manifest_path, max_bytes=MANIFEST_LIMIT) as file:
    manifest = json.loads(file.read(MANIFEST_LIMIT + 1), object_pairs_hook=_unique)
  fields = {'schemaVersion', 'goVersion', 'target', 'sourceRevision', 'upstreamRevision',
            'sourceDigest', 'binarySha256'}
  if (type(manifest) is not dict or set(manifest) != fields or type(manifest['schemaVersion']) is not int or
      manifest['schemaVersion'] != 1 or manifest['goVersion'] != 'go1.25.1' or
      manifest['target'] != 'linux-arm64-static' or
      any(type(manifest[name]) is not str or pattern.fullmatch(manifest[name]) is None
          for name, pattern in (('sourceRevision', HEX40), ('upstreamRevision', HEX40),
                                ('sourceDigest', HEX64), ('binarySha256', HEX64)))):
    raise ValueError('invalid Mapd package manifest')
  pinned = json.loads((source / 'upstream-sync.json').read_text())
  upstream = next(item['commit'] for item in pinned['dependencies'] if item['path'] == 'mapd_repo')
  if manifest['upstreamRevision'] != upstream or manifest['sourceDigest'] != source_digest(source / 'mapd_repo'):
    raise ValueError('Mapd package source changed; run ./build --mapd')
  stamps = {manifest[name].encode() for name in ('sourceRevision', 'upstreamRevision', 'sourceDigest')}
  digest, seen, carry = hashlib.sha256(), set(), b''
  with _regular(binary, max_bytes=BINARY_LIMIT, executable=True) as file:
    if not elf_arm64_static_file(file):
      raise ValueError('Mapd package is not a static Linux ARM64 executable')
    file.seek(0)
    for chunk in iter(lambda: file.read(1024 * 1024), b''):
      digest.update(chunk)
      window = carry + chunk
      seen.update(stamp for stamp in stamps if stamp in window)
      carry = window[-128:]
  if digest.hexdigest() != manifest['binarySha256'] or seen != stamps:
    raise ValueError('Mapd package hash or embedded source stamps differ; run ./build --mapd')
  return manifest


def stage_provider(source: Path, destination: Path) -> dict:
  source, destination = Path(source), Path(destination)
  manifest = validate_provider(source)
  _directories(destination, provider=False)
  if (source_digest(destination / 'mapd_repo') != manifest['sourceDigest'] or
      (destination / 'upstream-sync.json').read_bytes() != (source / 'upstream-sync.json').read_bytes()):
    raise ValueError('release Mapd source differs from the validated package')
  provider = destination / PROVIDER
  if provider.exists() or provider.is_symlink():
    _directories(destination)
  else:
    provider.mkdir(mode=0o755)
  outputs = []
  try:
    for name, mode in (('mapd', 0o755), ('manifest.json', 0o644)):
      target = destination / PROVIDER / name
      with _regular(source / PROVIDER / name, max_bytes=BINARY_LIMIT if name == 'mapd' else MANIFEST_LIMIT,
                    executable=name == 'mapd') as input_file:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
        outputs.append(target)
        with os.fdopen(descriptor, 'wb') as output:
          for chunk in iter(lambda: input_file.read(1024 * 1024), b''):
            output.write(chunk)
    with (destination / PROVIDER / 'mapd').open('rb') as file:
      if hashlib.file_digest(file, 'sha256').hexdigest() != manifest['binarySha256']:
        raise ValueError('Mapd package changed while staging')
    if json.loads((destination / PROVIDER / 'manifest.json').read_text(), object_pairs_hook=_unique) != manifest:
      raise ValueError('Mapd manifest changed while staging')
  except Exception:
    for path in outputs:
      path.unlink(missing_ok=True)
    raise
  return manifest


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--source', type=Path, required=True)
  parser.add_argument('--destination', type=Path)
  args = parser.parse_args()
  try:
    manifest = stage_provider(args.source, args.destination) if args.destination else validate_provider(args.source)
  except (OSError, ValueError, KeyError, TypeError, StopIteration) as error:
    parser.exit(1, f'Mapd release package unavailable: {error}\nBuild it in the source checkout with ./build --mapd.\n')
  print(f"Verified Mapd release package {manifest['binarySha256']}")
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
