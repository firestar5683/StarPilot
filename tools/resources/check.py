"""Reject placeholder pointers, active checkout filters and oversized Git blobs."""
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POINTER = b'version https://git-lfs.github.com/spec/v1'
MAX_BLOB_BYTES = 100 * 1024 * 1024


def validate_blob(path, size, data=None):
  if size > MAX_BLOB_BYTES:
    raise ValueError(f'ordinary Git blob exceeds 100 MiB: {path}')
  if data is not None and data.startswith(POINTER):
    raise ValueError(f'placeholder pointer payload: {path}')
  if Path(path).name == '.gitattributes' and data is not None:
    for line in data.decode().splitlines():
      if line.strip() and not line.lstrip().startswith('#') and 'filter=lfs' in line.split():
        raise ValueError(f'active checkout filter: {path}')
  if path == '.lfsconfig':
    raise ValueError('obsolete checkout configuration')


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--revision')
  args = parser.parse_args()
  if args.revision:
    entries = subprocess.check_output(['git', 'ls-tree', '-rl', args.revision], cwd=ROOT, text=True).splitlines()
    for entry in entries:
      fields, path = entry.split('\t', 1)
      mode, kind, oid, size = fields.split()
      if kind != 'blob':
        continue
      size = int(size)
      data = subprocess.check_output(['git', 'cat-file', 'blob', oid], cwd=ROOT) if size <= 1024 or Path(path).name == '.gitattributes' else None
      validate_blob(path, size, data)
  else:
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).split(b'\0')
    for raw in paths:
      if not raw:
        continue
      path = raw.decode()
      file = ROOT / path
      if not file.is_file():
        continue  # tracked symlinks/deletions are handled by source/release gates
      with file.open('rb') as f:
        data = f.read() if file.name == '.gitattributes' else f.read(1024)
      validate_blob(path, file.stat().st_size, data)
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
