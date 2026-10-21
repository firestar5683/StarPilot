"""Inventory of the Galaxy web files, so companion apps can download and verify them from comma."""
import hashlib
from pathlib import Path

# Served dynamically or preview-only; never part of the files an app caches.
EXCLUDED = ('data/runtime.json',)

_cache: dict[str, tuple[tuple, dict]] = {}


def _commit() -> str | None:
  try:
    from openpilot.common.params import Params
    value = Params().get('GitCommit')
  except Exception:
    return None
  text = value.decode() if isinstance(value, bytes) else value
  return text.strip() or None if isinstance(text, str) else None


def _wanted(relative: str) -> bool:
  return relative not in EXCLUDED and not relative.endswith('.sample.json')


def web_manifest(web: Path) -> dict:
  files = []
  for path in sorted(p for p in web.rglob('*') if p.is_file()):
    relative = path.relative_to(web).as_posix()
    if not _wanted(relative):
      continue
    stat = path.stat()
    identity = (stat.st_ino, stat.st_mtime_ns, stat.st_size)
    cached = _cache.get(str(path))
    if cached is None or cached[0] != identity:
      body = path.read_bytes()
      cached = (identity, {'path': relative, 'size': len(body), 'sha256': hashlib.sha256(body).hexdigest()})
      _cache[str(path)] = cached
    files.append(cached[1])
  return {'schema': 1, 'commit': _commit(), 'files': files}
