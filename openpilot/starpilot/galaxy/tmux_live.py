"""Read-only, bounded view of the normal launcher console over either HTTP transport."""

import re
import subprocess
import tempfile
import threading
import time


MAX_BYTES = 65536
MAX_LINES = 300


class TmuxLive:
  def __init__(self, *, run=subprocess.run, clock=time.monotonic):
    self.run, self.clock = run, clock
    self.lock = threading.Lock()
    self.cached, self.expiry = None, 0.0

  def snapshot(self):
    with self.lock:
      if self.cached is not None and self.clock() < self.expiry:
        return self.cached
      result = {'available': False, 'reason': '', 'text': '', 'truncated': False, 'pane': ''}
      try:
        panes = self.run(['tmux', 'list-panes', '-t', '=comma:0', '-F', '#{pane_id}\t#{pane_index}\t#{pane_dead}'],
                         capture_output=True, timeout=1, check=True).stdout.decode()
        pane = next((fields[0] for line in panes[:16384].splitlines()
                     if len(fields := line.split('\t')) == 3 and fields[1:] == ['0', '0'] and
                     re.fullmatch(r'%\d+', fields[0])), None)
        if pane is None:
          raise ValueError('No live launcher pane')
        # A terminal can contain very long lines; bound memory as well as scrollback.
        with tempfile.TemporaryFile() as output:
          self.run(['tmux', 'capture-pane', '-p', '-t', pane, '-S', f'-{MAX_LINES}', '-E', '-'],
                   stdout=output, stderr=subprocess.DEVNULL, timeout=1, check=True)
          size = output.tell()
          output.seek(max(0, size - MAX_BYTES))
          text = output.read(MAX_BYTES).decode('utf-8', errors='replace')
        # Replacement decoding can expand malformed/cut UTF-8 beyond the raw
        # byte limit. Bound the actual JSON text encoding as well.
        encoded = text.encode('utf-8')
        expanded = len(encoded) > MAX_BYTES
        if expanded:
          text = encoded[-MAX_BYTES:].decode('utf-8', errors='ignore')
        lines = text.splitlines()
        result.update(available=True, text='\n'.join(lines[-MAX_LINES:]), truncated=size > MAX_BYTES or expanded or len(lines) >= MAX_LINES,
                      pane='comma:0.0')
      except FileNotFoundError:
        result['reason'] = 'tmux is not installed in this build. Install a complete StarPilot build to use the live console.'
      except (OSError, subprocess.SubprocessError, ValueError, UnicodeError):
        result['reason'] = 'The StarPilot launcher console is not running in its normal tmux session. Crash Reports and System Monitor are still available.'
      self.cached, self.expiry = result, self.clock() + 1.0
      return result
