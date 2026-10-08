"""Bounded Galaxy HTTP connections and shared-source shutdown."""

from contextlib import ExitStack
from http.server import ThreadingHTTPServer
import threading
import time


class _LocalHTTPServer(ThreadingHTTPServer):
  """Bound idle browser connections without blocking other local requests."""

  MAX_CONNECTIONS = 8
  REQUEST_TIMEOUT = 4.0

  def __init__(self, *args, **kwargs):
    self._slots = threading.BoundedSemaphore(self.MAX_CONNECTIONS)
    super().__init__(*args, **kwargs)

  def get_request(self):
    request, address = super().get_request()
    request.settimeout(self.REQUEST_TIMEOUT)
    return request, address

  def process_request(self, request, client_address):
    if not self._slots.acquire(timeout=self.REQUEST_TIMEOUT):
      self.shutdown_request(request)
      return
    try:
      super().process_request(request, client_address)
    except Exception:
      self._slots.release()
      raise

  def process_request_thread(self, request, client_address):
    try:
      super().process_request_thread(request, client_address)
    finally:
      self._slots.release()

  def drain_requests(self, timeout: float) -> bool:
    """Wait for accepted requests before closing their shared data sources."""
    deadline = time.monotonic() + timeout
    acquired = 0
    try:
      for _ in range(self.MAX_CONNECTIONS):
        if not self._slots.acquire(timeout=max(0.0, deadline - time.monotonic())):
          return False
        acquired += 1
      return True
    finally:
      for _ in range(acquired):
        self._slots.release()

  def server_close(self, *, close_sources: bool = True):
    if not close_sources:
      # Managed shutdown can abandon a stuck daemon request. Its readers must
      # remain alive until that process exits; only retire the listening socket.
      media = getattr(self, 'recording_media_source', None)
      if media is not None:
        media.stop_child()
      super().server_close()
      return
    # Always close every owned source, even if another cleanup raises. The
    # analysis child must stop before its parked-state reader is retired.
    with ExitStack() as cleanup:
      cleanup.callback(super().server_close)
      media = getattr(self, 'recording_media_source', None)
      if media is not None:
        cleanup.callback(media.close)
      for name in ('map_source', 'settings_source', 'vehicle_selection_source', 'model_source', 'plots_source',
                   'flm_source', 'bluetooth_authority', 'bluetooth_source', 'model_manager_source', 'model_authority', 'layout_authority', 'favorites_source',
                   'sound_authority', 'sound_source', 'software_operations_source', 'drive_stats_authority', 'drive_stats_source',
                   'pairing_authority', 'evidence_source', 'device_state_source', 'navigation_source', 'drive_physical_source', 'notification_source'):
        close = getattr(getattr(self, name, None), 'close', None)
        if callable(close):
          cleanup.callback(close)
