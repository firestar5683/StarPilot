"""Read-only, unqualified map observation for authenticated local Galaxy."""

import threading
import time

from openpilot.starpilot.speed_limits.map_source import MapTracker, decode_event


class MapUnavailable(Exception):
  pass


def boot_time_ns() -> int:
  clock = getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC)
  return time.clock_gettime_ns(clock)


class MapStatus:
  MAX_DRAIN = 32

  def __init__(self, receiver=None, *, clock=boot_time_ns):
    self._receiver = receiver
    self._clock = clock
    self._tracker = MapTracker()
    self._lock = threading.Lock()
    self._closed = False

  def close(self):
    with self._lock:
      self._closed = True
      if self._receiver is not None:
        close = getattr(self._receiver, 'close', None)
        if close is not None:
          close()
        self._receiver = None

  def snapshot(self):
    with self._lock:
      if self._closed:
        raise MapUnavailable('Map observation is closed')
      if self._receiver is None:
        from openpilot.cereal import messaging
        try:
          self._receiver = messaging.sub_sock('mapdOut', conflate=True)
        except Exception as error:
          raise MapUnavailable('Map transport is unavailable') from error
      try:
        now = self._clock()
        evidence = self._tracker.step(None, received=False, now_boot_ns=now)
        for _ in range(self.MAX_DRAIN):
          raw = self._receiver.receive(non_blocking=True)
          if raw is None:
            break
          now = self._clock()
          try:
            frame = decode_event(raw)
          except ValueError:
            evidence = self._tracker.step(None, received=True, now_boot_ns=now)
          else:
            evidence = self._tracker.step(frame, received=True, now_boot_ns=now)
        else:
          # A busy queue must not make one HTTP request unbounded or present
          # an earlier drained packet as the latest observation.
          self._tracker.step(None, received=True, now_boot_ns=self._clock())
          raise MapUnavailable('Map transport is busy')
      except MapUnavailable:
        raise
      except (OSError, RuntimeError, ValueError) as error:
        self._tracker.step(None, received=False, now_boot_ns=self._clock(), transport_alive=False)
        raise MapUnavailable('Map transport is unavailable') from error
      # Parsing and IPC draining may take longer than the source TTL. The
      # projection must use a fresh boot-clock sample, not the receive time.
      now = self._clock()
      final_evidence = self._tracker.step(None, received=False, now_boot_ns=now)
      # The tracker reports STALE once, then UNKNOWN after clearing its held
      # frame. Preserve that one transition if our second check was the only
      # reason it advanced; no candidate is preserved.
      if not (evidence.kind == 'stale' and final_evidence.kind == 'unknown'):
        evidence = final_evidence
      diagnostic = self._tracker.diagnostic(now_boot_ns=now)
      frame = diagnostic.frame
      return {'schemaVersion': 1, 'qualification': 'unqualified', 'state': evidence.kind,
              'candidateSpeedMps': evidence.speed_mps,
              'roadStatus': frame.status if frame is not None else None,
              'gpsSource': frame.source if frame is not None else None,
              'gpsAgeMs': (now - frame.gps_mono_ns) // 1_000_000 if frame is not None and frame.gps_mono_ns > 0 else None,
              'computedAgeMs': (now - frame.computed_mono_ns) // 1_000_000 if frame is not None else None,
              'eventAgeMs': (now - frame.event_mono_ns) // 1_000_000 if frame is not None else None,
              'tileLoaded': frame.tile_loaded if frame is not None else None,
              'producerRestarts': diagnostic.producer_restarts,
              'sourceSwitches': diagnostic.source_switches}
