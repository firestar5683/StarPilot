"""Dom-compatible numbered model parts, with verified atomic disk materialization.

The count-only .chunkmanifest format remains readable. New packages include an
integrity sidecar; model compilers and tinygrad's disk-backed loader stay unchanged.
"""
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

CHUNK_SIZE = 45 * 1024 * 1024


def get_chunk_name(name, idx, num_chunks):
  return f'{name}.chunk{idx + 1:02d}of{num_chunks:02d}'


def get_manifest_path(name):
  return f'{name}.chunkmanifest'


def get_existing_chunks(path):
  path = Path(path)
  manifest = Path(get_manifest_path(path))
  if not manifest.exists() and path.is_file():
    return [path]
  text = manifest.read_text().strip()
  if not text.isdecimal() or not 1 <= int(text) <= 1024:
    raise ValueError('invalid model part count')
  count = int(text)
  parts = [path.with_name(get_chunk_name(path.name, i, count)) for i in range(count)]
  for i, part in enumerate(parts):
    size = part.stat().st_size
    if not 0 < size <= CHUNK_SIZE or (i < count - 1 and size != CHUNK_SIZE):
      raise ValueError('invalid model part size')
  return [manifest, *parts]


def file_chunked_exists(path):
  try:
    get_existing_chunks(path)
    return True
  except (OSError, ValueError):
    return False


def _digest_file(path):
  digest = hashlib.sha256()
  with Path(path).open('rb') as inp:
    while block := inp.read(1024 * 1024):
      digest.update(block)
  return digest.hexdigest()


def materialize_file_chunked(path, expected_sha256=None):
  """Return a regular file for tinygrad OOB reads; refuse invalid packages.

  Cache publication uses os.replace so concurrent readers never see partial data.
  Legacy count-only packages can supply an externally pinned expected_sha256.
  """
  path = Path(path)
  entries = get_existing_chunks(path)
  if entries == [path]:
    if expected_sha256 is not None and _digest_file(path) != expected_sha256:
      raise ValueError('model digest mismatch')
    return path
  sidecar = Path(f'{path}.chunksha256')
  metadata = json.loads(sidecar.read_text()) if sidecar.exists() else None
  if metadata is not None:
    if set(metadata) != {'sha256', 'bytes', 'parts'} or len(metadata['parts']) != len(entries) - 1:
      raise ValueError('invalid model integrity manifest')
    if expected_sha256 is not None and metadata['sha256'] != expected_sha256:
      raise ValueError('model digest mismatch')
    expected_sha256 = metadata['sha256']
  cache = Path(f'{path}.unchunked')
  digest, total = hashlib.sha256(), 0
  for i, part in enumerate(entries[1:]):
    part_hash, part_size = hashlib.sha256(), 0
    with part.open('rb') as inp:
      while block := inp.read(1024 * 1024):
        digest.update(block)
        part_hash.update(block)
        part_size += len(block)
    total += part_size
    if metadata is not None and metadata['parts'][i] != {'bytes': part_size, 'sha256': part_hash.hexdigest()}:
      raise ValueError('model part digest mismatch')
  if expected_sha256 is not None and digest.hexdigest() != expected_sha256:
    raise ValueError('model digest mismatch')
  if metadata is not None and total != metadata['bytes']:
    raise ValueError('model size mismatch')
  if cache.is_file() and cache.stat().st_size == total and _digest_file(cache) == digest.hexdigest():
    return cache
  fd, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
  copied_digest, copied_size = hashlib.sha256(), 0
  try:
    with os.fdopen(fd, 'wb') as out:
      for part in entries[1:]:
        with part.open('rb') as inp:
          while block := inp.read(1024 * 1024):
            out.write(block)
            copied_digest.update(block)
            copied_size += len(block)
    if copied_size != total or copied_digest.hexdigest() != digest.hexdigest():
      raise ValueError('model parts changed during materialization')
    os.replace(temporary, cache)
    return cache
  finally:
    if os.path.exists(temporary):
      os.unlink(temporary)


def read_file_chunked(path, expected_sha256=None):
  return materialize_file_chunked(path, expected_sha256).read_bytes()


def open_file_chunked(path, expected_sha256=None):
  return materialize_file_chunked(path, expected_sha256).open('rb')


def package_file(path, destination):
  """Package a compiled artifact without deleting the compiler's original output."""
  path, destination = Path(path), Path(destination)
  source_stat = path.stat()
  size = source_stat.st_size
  if size <= 0:
    raise ValueError('empty model artifact')
  count = (size + CHUNK_SIZE - 1) // CHUNK_SIZE
  if count > 1024:
    raise ValueError('model exceeds part count limit')
  destination.parent.mkdir(parents=True, exist_ok=True)
  digest, parts = hashlib.sha256(), []
  with path.open('rb') as inp:
    for i in range(count):
      block = inp.read(CHUNK_SIZE)
      digest.update(block)
      destination.with_name(get_chunk_name(destination.name, i, count)).write_bytes(block)
      parts.append({'bytes': len(block), 'sha256': hashlib.sha256(block).hexdigest()})
  final_stat = path.stat()
  unchanged = (source_stat.st_size, source_stat.st_mtime_ns, source_stat.st_ino) == (final_stat.st_size, final_stat.st_mtime_ns, final_stat.st_ino)
  if not unchanged or sum(part['bytes'] for part in parts) != size:
    raise ValueError('compiled model changed while packaging')
  Path(f'{destination}.chunksha256').write_text(json.dumps({'bytes': size, 'sha256': digest.hexdigest(), 'parts': parts}, indent=2) + '\n')
  Path(get_manifest_path(destination)).write_text(str(count))
  active = {get_chunk_name(destination.name, i, count) for i in range(count)}
  for old in destination.parent.glob(destination.name + '.chunk*of*'):
    if old.name not in active and re.fullmatch(re.escape(destination.name) + r'\.chunk[0-9]{2,}of[0-9]{2,}', old.name):
      old.unlink()
  return digest.hexdigest()
