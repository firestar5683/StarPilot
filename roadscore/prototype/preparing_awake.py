"""Keep the owned native preparation screen interactive until playback or failure."""
import json
from pathlib import Path
import time


class PreparationWake:
    def __init__(self, status_path, native):
        self.path = Path(status_path) if status_path else None
        self.native = native
        self.next_check = 0.

    def update(self, ui_state, device, now=None):
        if not self.native or self.path is None or ui_state.started:
            return False
        now = time.monotonic() if now is None else now
        if now < self.next_check:
            return False
        self.next_check = now + 1.
        try:
            status = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return False
        if not isinstance(status, dict) or str(status.get('readiness', '')).upper() != 'PREPARING':
            return False
        if status.get('worker_failed') or status.get('failure_kind'):
            return False
        device.reset_interactive_timeout()
        return True
