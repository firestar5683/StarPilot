"""Read-only BlueZ adapter power for the compact Home indicator.

This does not enable Bluetooth, manage devices, or report a connection. The
system-bus query runs off the render thread and expires after a short gap.
"""

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
import subprocess
import time


def _clock_ns() -> int:
  boot = getattr(time, "CLOCK_BOOTTIME", None)
  return time.clock_gettime_ns(boot) if boot is not None else time.monotonic_ns()


def read_adapter_powered() -> bool:
  try:
    result = subprocess.run(("busctl", "--system", "--timeout=1", "get-property", "org.bluez", "/org/bluez/hci0",
                             "org.bluez.Adapter1", "Powered"),
                            capture_output=True, text=True, timeout=1.5, check=False)
  except (OSError, subprocess.TimeoutExpired):
    return False
  return result.returncode == 0 and result.stdout.strip() == "b true"


class BluetoothStatusSource:
  """One bounded background read; stale, failed, or absent status is false."""

  REFRESH_NS = 2_000_000_000
  MAX_AGE_NS = 4_000_000_000

  def __init__(self, request: Callable[[], bool] = read_adapter_powered,
               clock: Callable[[], int] = _clock_ns):
    self.request = request
    self.clock = clock
    self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="bluetooth-status")
    self.pending: Future[tuple[bool, int]] | None = None
    self.next_read_ns = 0
    self.powered = False
    self.observed_ns: int | None = None
    self.closed = False

  def _poll(self) -> tuple[bool, int]:
    try:
      powered = self.request() is True
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
      powered = False
    return powered, self.clock()

  def snapshot(self) -> bool:
    if self.closed:
      return False
    now = self.clock()
    if self.pending is not None and self.pending.done():
      try:
        self.powered, self.observed_ns = self.pending.result()
      except (OSError, RuntimeError, ValueError):
        self.powered, self.observed_ns = False, None
      self.pending = None
    if now < self.next_read_ns - self.REFRESH_NS:
      self.next_read_ns = 0
      self.powered, self.observed_ns = False, None
    if self.pending is None and now >= self.next_read_ns:
      self.pending = self.executor.submit(self._poll)
      self.next_read_ns = now + self.REFRESH_NS
    return bool(self.powered and self.observed_ns is not None and
                0 <= now - self.observed_ns <= self.MAX_AGE_NS)

  def close(self) -> None:
    self.closed = True
    self.executor.shutdown(wait=False, cancel_futures=True)
