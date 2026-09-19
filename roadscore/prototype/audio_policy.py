"""Output policy shared by CLI and audio endpoints; never selects Bluetooth devices."""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def session_muted():
  return os.environ.get('ROADSCORE_FORCE_MUTE') == '1' or (ROOT / '.session-muted').exists()
def allow_output(requested):
  return bool(requested) and not session_muted()
