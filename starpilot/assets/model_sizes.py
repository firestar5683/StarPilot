"""Local logical payload sizes. No HEAD requests, hashing, or model mutation."""
from pathlib import Path
import re
import threading
import time

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


class ModelSizes:
  """Bounded cache for local catalogue size reads, independent of statistics."""
  def __init__(self):
    self.lock = threading.Lock()
    self.sizes = {}

  def size(self, path, declared):
    # Short TTL avoids repeated directory scans on status polls, not stale sizes
    # across completed downloads. Bad metadata is treated as unknown by helper.
    key = (str(path), repr(declared))
    with self.lock:
      cached = self.sizes.get(key)
      if cached is None or time.monotonic() >= cached[0]:
        cached = (time.monotonic() + 2, artifact_size(path, declared))
        if len(self.sizes) > 1000:
          self.sizes.clear()
        self.sizes[key] = cached
      return dict(cached[1])

  def annotate(self, models, models_path, builtin_path, metadata, accelerator_filename):
    for model in models:
      key = model['value']
      entry = metadata.get(key, {})
      entry = entry if isinstance(entry, dict) else {}
      path = builtin_path if model['builtin'] else Path(models_path) / f'{key}_driving_tinygrad.pkl'
      model.update(self.size(path, entry.get('artifact_size')))
      variants = entry.get('accelerator_artifacts', {})
      variant = variants.get('chestnut') if isinstance(variants, dict) else None
      if isinstance(variant, dict):
        model['modelLabFileSize'] = self.size(Path(models_path) / accelerator_filename(key), variant.get('artifact_size'))
    return models
