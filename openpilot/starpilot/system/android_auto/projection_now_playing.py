"""Read-only now-playing snapshot for the car screen, polled away from Android Auto's drawing thread."""
import threading

from openpilot.starpilot.soloist import now_playing
from openpilot.starpilot.soloist.paths import Layout


class ProjectionNowPlayingFeed:
  """Only poll while placed. The renderer takes immutable snapshots without file IO."""
  def __init__(self, read=None):
    self.read = read or (lambda: now_playing.read(Layout.default().status))
    self._lock = threading.Lock()
    self._stop = threading.Event()
    self._thread = None
    self._enabled = False
    self._value = None

  def set_enabled(self, enabled):
    with self._lock:
      self._enabled = enabled
      if not enabled:
        self._value = None
    if enabled and self._thread is None:
      self._thread = threading.Thread(target=self._run, name='aa-now-playing', daemon=True)
      self._thread.start()

  def poll(self):
    with self._lock:
      if not self._enabled:
        return
    try:
      value = self.read()
    except Exception:
      value = None
    with self._lock:
      if self._enabled:
        self._value = value

  def snapshot(self):
    with self._lock:
      return self._value

  def _run(self):
    while not self._stop.is_set():
      self.poll()
      self._stop.wait(1.0)

  def close(self):
    self._stop.set()
    if self._thread is not None:
      self._thread.join(timeout=2)
