"""Read-only Jetlink status for the home icon and the Android Auto card, polled off the drawing thread."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
import threading
import time

STALE_NS = 2_500_000_000
# The host's processing time for the last big-model frame (excludes USB); jetlink's runtime record does not carry it
LATENCY_RECORD = "/dev/shm/jetlink/starpilot_latency.json"
LATENCY_FRESH_S = 3.
RUNNING = {'ready': 'ready', 'joining': 'connecting', 'retrying': 'connecting'}


@dataclass(frozen=True)
class JetlinkStatus:
  device: str = ''
  state: str = 'off'  # off, disconnected, connected, connecting, ready, active, unavailable
  latency_ms: float | None = None
  port: str | None = None  # jetlink's port_state: 'connected' (host on the link), 'device' (plugged in), else None


def _write_latency(model, path) -> None:
  timings = getattr(getattr(model, "client", None), "last_timings", None)  # the big model's client while it drives
  total_us = timings[2] if isinstance(timings, (tuple, list)) and len(timings) == 3 else 0
  record = {"at": time.monotonic(), "server_ms": total_us / 1000 if type(total_us) in (int, float) and total_us > 0 else None}
  os.makedirs(os.path.dirname(path), exist_ok=True)
  tmp = f"{path}.tmp"
  with open(tmp, "w") as f:
    json.dump(record, f)
  os.replace(tmp, path)


def start_latency_writer(model, path=LATENCY_RECORD, period=1.):
  """modeld, before it goes realtime, so the thread keeps normal priority and the frame loop does no file IO."""
  def run():
    while True:
      try:
        _write_latency(model, path)
      except Exception:
        pass
      time.sleep(period)
  thread = threading.Thread(target=run, name="jetlink-latency", daemon=True)
  thread.start()
  return thread


def read_latency(path=LATENCY_RECORD) -> float | None:
  try:
    with open(path) as f:
      record = json.load(f)
    ms, at = record.get("server_ms"), record.get("at")
    fresh = type(at) in (int, float) and 0 <= time.monotonic() - at < LATENCY_FRESH_S
    return float(ms) if fresh and type(ms) in (int, float) and math.isfinite(ms) and ms > 0 else None
  except (OSError, ValueError, AttributeError):
    return None


def read_status() -> JetlinkStatus:
  from openpilot.starpilot.models.jetlink_adapter import hooks, link_on
  if not link_on():
    return JetlinkStatus()  # one file read: nothing of jetlink's loads
  status = hooks().status()
  if status is None:
    return JetlinkStatus(state='unavailable')
  if not status.enabled:
    return JetlinkStatus()  # a Chestnut is fitted
  device = 'iPhone' if status.mode == 'ios' else 'Computer'
  port = status.port_state if status.port_state in ('connected', 'device') else None
  if not status.present:
    return JetlinkStatus(device, 'disconnected', port=port)
  if status.active:
    return JetlinkStatus(device, 'active', read_latency(), port)
  if status.reason:
    return JetlinkStatus(device, 'unavailable', port=port)
  return JetlinkStatus(device, RUNNING.get(status.running, 'connected'), port=port)


class JetlinkStatusFeed:
  """Polls once a second only while enabled; snapshot() never does file IO."""
  def __init__(self, read=read_status, period=1.0):
    self.read, self.period = read, period
    self._lock = threading.Lock()
    self._stop = threading.Event()
    self._thread = None
    self._enabled = False
    self._status = JetlinkStatus()
    self._read_at = 0

  def set_enabled(self, enabled):
    with self._lock:
      self._enabled = enabled
      if not enabled:
        self._status = JetlinkStatus()
    if enabled and self._thread is None:
      self._thread = threading.Thread(target=self._run, name='jetlink-status', daemon=True)
      self._thread.start()

  def poll(self):
    with self._lock:
      if not self._enabled:
        return
    try:
      status = self.read()
    except Exception:
      status = JetlinkStatus(state='unavailable')
    with self._lock:
      if self._enabled:
        self._status = status
        self._read_at = time.monotonic_ns()

  def snapshot(self):
    with self._lock:
      status, read_at = self._status, self._read_at
    if status.state != 'off' and time.monotonic_ns() - read_at > STALE_NS:
      return JetlinkStatus(status.device, 'unavailable')
    return status

  def _run(self):
    while not self._stop.is_set():
      self.poll()
      self._stop.wait(self.period)

  def close(self):
    self._stop.set()
    if self._thread is not None:
      self._thread.join(timeout=2)
