import os
from pathlib import Path
import re


STORAGE_ANCHOR = Path('/data/media/0')


def offline_root(anchor: Path = STORAGE_ANCHOR) -> Path:
  prefix = os.environ.get('OPENPILOT_PREFIX', '')
  if prefix and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', prefix) is None:
    raise ValueError('Invalid map storage namespace')
  name = f'starpilot-{prefix}' if prefix else 'starpilot'
  return anchor / name / 'maps/offline'
