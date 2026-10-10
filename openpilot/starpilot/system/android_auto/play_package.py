"""Pinned Google Play resolver release asset and the directory it installs to."""
import json
from pathlib import Path

PACKAGE = json.loads(Path(__file__).with_suffix('.json').read_text())
RUNTIME = Path('/data/starpilot/google-play') / PACKAGE['id']
