#!/usr/bin/env python3
"""Explicit Linux ARM64 Mapd shadow package build; never starts the provider."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from openpilot.starpilot.maps.artifact import elf_arm64_static, source_digest


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'mapd_repo'
DEFAULT_OUTPUT = ROOT / 'openpilot/starpilot/maps/provider'


def package(*, go: str, output: Path) -> dict:
  go_path = shutil.which(go)
  if go_path is None:
    raise ValueError('pinned Go toolchain is unavailable')
  version = subprocess.check_output([go_path, 'version'], text=True).split()
  if len(version) < 3 or version[2] != 'go1.25.1':
    raise ValueError('Mapd shadow package requires Go 1.25.1')
  pin = json.loads((ROOT / 'upstream-sync.json').read_text())
  revision = next(item['commit'] for item in pin['dependencies'] if item['path'] == 'mapd_repo')
  digest = source_digest(SOURCE)
  commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
  output.mkdir(parents=True, exist_ok=True)
  with tempfile.TemporaryDirectory(prefix='mapd-shadow-build-') as temporary:
    binary = Path(temporary) / 'mapd'
    stamps = f'-extldflags=-static -s -w -X main.sourceRevision={commit} -X main.upstreamRevision={revision} -X main.sourceDigest={digest}'
    env = dict(os.environ, GOTOOLCHAIN='local', GOPROXY='off', GOSUMDB='off')
    subprocess.run([go_path, 'build', '-mod=readonly', '-trimpath', '-tags', 'netgo,osusergo', '-buildvcs=true',
                    '-ldflags', stamps, '-o', str(binary), '.'], cwd=SOURCE, env=env, check=True)
    if source_digest(SOURCE) != digest or not elf_arm64_static(binary):
      raise ValueError('source changed during build or binary is not static Linux ARM64')
    data = binary.read_bytes()
    if any(stamp.encode() not in data for stamp in (commit, revision, digest)):
      raise ValueError('binary is missing exact source stamps')
    manifest = {'schemaVersion': 1, 'sourceRevision': commit, 'sourceDigest': digest,
                'upstreamRevision': revision, 'goVersion': version[2], 'target': 'linux-arm64-static',
                'binarySha256': hashlib.sha256(data).hexdigest()}
    staged = output / '.mapd-new'
    staged.write_bytes(data)
    staged.chmod(0o755)
    os.replace(staged, output / 'mapd')
    staged_manifest = output / '.manifest-new'
    staged_manifest.write_text(json.dumps(manifest, sort_keys=True, separators=(',', ':')) + '\n')
    os.replace(staged_manifest, output / 'manifest.json')
  return manifest


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--go', default='go', help='Go 1.25.1 executable')
  parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT, help='generated package directory')
  args = parser.parse_args()
  print(json.dumps(package(go=args.go, output=args.output.resolve()), sort_keys=True))
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
