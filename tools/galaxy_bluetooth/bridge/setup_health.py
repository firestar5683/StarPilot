import json
import os
from pathlib import Path
import tempfile


def clear_ready(data):
  (Path(data) / 'bridge-ready.json').unlink(missing_ok=True)


def write_ready(data):
  fd, temporary = tempfile.mkstemp(dir=data, prefix='.ready-')
  try:
    with os.fdopen(fd, 'w') as stream:
      json.dump({'pid': os.getpid()}, stream)
    os.replace(temporary, Path(data) / 'bridge-ready.json')
  finally:
    if os.path.exists(temporary):
      os.unlink(temporary)
