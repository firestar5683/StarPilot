"""Jetlink's child teardown grace without blocking normal manager ticks."""
import signal
import time

from openpilot.common.swaglog import cloudlog
from openpilot.system.manager.process import PythonProcess, join_process


class JetlinkProcess(PythonProcess):
  STOP_GRACE = 15.0

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.stop_requested_at = None

  def stop(self, retry=True, block=True, sig=None):
    if self.proc is None:
      return None
    if self.proc.exitcode is None:
      if not self.shutting_down:
        self.signal(sig or signal.SIGINT)
        self.shutting_down = True
        self.stop_requested_at = time.monotonic()
      requested = self.stop_requested_at
      assert requested is not None
      remaining = max(0.0, self.STOP_GRACE - (time.monotonic() - requested))
      if block:
        join_process(self.proc, remaining)
      if self.proc.exitcode is None and retry and (block or remaining == 0):
        cloudlog.warning(f'Jetlink owner did not stop within {self.STOP_GRACE}s; killing')
        self.signal(signal.SIGKILL)
        if block:
          join_process(self.proc, 2.0)
    result = self.proc.exitcode
    if result is not None:
      self.proc = None
      self.shutting_down = False
      self.stop_requested_at = None
      self.restart_failures = 0
      self.restart_at = 0.0
    return result

  def start(self):
    if self.shutting_down:
      self.stop(block=False)
      if self.proc is not None:
        return
    super().start()
