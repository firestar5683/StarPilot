"""Local logical payload sizes. No HEAD requests, hashing, or model mutation."""
from pathlib import Path
import re

MAX_DECLARED_BYTES = 1 << 50


def positive_size(value):
  return value if type(value) is int and 0 < value <= MAX_DECLARED_BYTES else None


def artifact_size(path, declared=None):
  path = Path(path)
  declared = positive_size(declared)
  result = {'fileSizeBytes': None, 'declaredSizeBytes': declared, 'downloadedBytes': None,
            'sizeSource': 'metadata' if declared else 'unknown',
            'sizeStatus': 'declared' if declared else 'unknown'}
  try:
    if path.is_file():
      size = path.stat().st_size
      result.update(fileSizeBytes=size if size > 0 else None, downloadedBytes=size,
                    sizeSource='installed', sizeStatus='complete' if size > 0 else 'partial')
    else:
      manifest = Path(str(path) + '.chunkmanifest')
      chunks = [p for p in path.parent.glob(path.name + '.chunk*')
                if re.fullmatch(re.escape(path.name) + r'\.chunk\d+of\d+', p.name) and p.is_file()]
      if not manifest.is_file() and not chunks:
        return result
      count = None
      if manifest.is_file():
        try:
          text = manifest.read_text().strip()
          count = int(text) if text.isdecimal() and len(text) <= 5 else None
        except (ValueError, UnicodeError):
          pass
      expected = [Path(f'{path}.chunk{i + 1:02d}of{count:02d}') for i in range(count)] if count and count <= 10000 else []
      complete = bool(expected) and set(chunks) == set(expected)
      downloaded = sum(p.stat().st_size for p in chunks)
      result.update(downloadedBytes=downloaded, fileSizeBytes=downloaded if complete and downloaded > 0 else None,
                    sizeSource='installed' if complete else 'partial',
                    sizeStatus='complete' if complete and downloaded > 0 else 'partial')
    if result['fileSizeBytes'] is not None and declared and declared != result['fileSizeBytes']:
      result['sizeStatus'] = 'mismatch'
  except OSError:
    result.update(fileSizeBytes=None, downloadedBytes=None, sizeSource='unknown', sizeStatus='unknown')
  return result
