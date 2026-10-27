"""Shared Jetlink presentation state and background polling for native and projected screens."""
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
# Whether this modeld's attach() joined the link. Without it a join that raised leaves no runtime record,
# which jetlink reports as 'prepared' for the whole drive
JOIN_RECORD = "/dev/shm/jetlink/starpilot_join.json"


def connection_state(status) -> str:
  """Project Jetlink's current API for every StarPilot surface, without changing its reconnect policy."""
  if status is None or not status.enabled:
    return 'unavailable'
  # Presence intentionally survives brief enumeration gaps. An empty physical
  # port is stronger evidence for the UI than that hold or a prior runtime record.
  if status.port == 'empty':
    return 'disconnected'
  if status.reason:
    return 'unavailable'
  if not status.present:
    return 'disconnected'
  return status.phase


@dataclass(frozen=True)
class JetlinkStatus:
  device: str = ''
  state: str = 'off'  # Jetlink phase, or off/disconnected/unavailable
  latency_ms: float | None = None
  port: str | None = None  # jetlink's port_state: 'connected' (host on the link), 'device' (plugged in), else None
  stage: str = ''
  percent: int | None = None


RECONNECT_WHY = ('lost', 'behind', 'load_failed', 'bad_output')


def reconnect_reason(progress) -> str:
  """Why jetlink handed the drive back and is rejoining, as 'reconnect_<why>'; a link that has dropped repeatedly
  is 'reconnect_cable'. '' when jetlink did not say."""
  if not isinstance(progress, dict) or progress.get('code') != 'reconnecting':
    return ''
  args = progress.get('args')
  why = args.get('why') if isinstance(args, dict) else None
  if why not in RECONNECT_WHY:
    return ''
  drops = progress.get('drops')
  return 'reconnect_cable' if why == 'lost' and type(drops) is int and drops > 0 else f'reconnect_{why}'


def preparation_progress(status, state):
  """Only attach progress to pending states; live readiness wins over old progress.

  Build estimates are Jetson-specific and server warm-up fractions may be paced,
  so only byte transfers get a percentage. Never present those estimates as a
  countdown on a phone.
  """
  progress = status.progress
  if state == 'reconnecting':
    return reconnect_reason(progress), None
  if state not in ('preparing', 'connecting'):
    return '', None
  if not isinstance(progress, dict):
    return '', None
  stage = progress.get('code') or progress.get('stage')
  if stage not in ('download', 'downloading', 'upload', 'patch', 'parse', 'convert', 'compile', 'build', 'load', 'warm',
                   'finding_model', 'model_missing', 'download_stalled', 'downloaded_waiting_host'):
    return '', None
  frac = progress.get('frac')
  percent = (int(frac * 100) if stage in ('download', 'downloading', 'upload') and
             type(frac) in (int, float) and math.isfinite(frac) and 0 <= frac <= 1 else None)
  return stage, percent


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


def write_join(joined: bool, path=JOIN_RECORD) -> None:
  """modeld, once attach() has answered. Never raises: the drive goes on either way."""
  try:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
      json.dump({"pid": os.getpid(), "joined": joined}, f)
    os.replace(tmp, path)
  except OSError:
    pass


def join_failed(path=JOIN_RECORD) -> bool:
  """A live modeld's attach() did not join the link."""
  try:
    with open(path) as f:
      record = json.load(f)
    pid = record.get("pid")
    if type(pid) is not int or record.get("joined") is not False:
      return False
    os.kill(pid, 0)
    return True
  except PermissionError:
    return record.get("joined") is False
  except (OSError, ValueError, AttributeError):
    return False


def read_status() -> JetlinkStatus:
  from openpilot.starpilot.models.jetlink_adapter import hooks, link_on
  if not link_on():
    return JetlinkStatus()  # one file read: nothing of jetlink's loads
  status = hooks().status()
  if status is None:
    return JetlinkStatus(state='unavailable')
  device = 'Mobile device (iOS)' if status.mode == 'ios' else 'USB host'
  state = connection_state(status)
  if state == 'disconnected' and status.port == 'host':
    state = 'detected'
  if state == 'prepared' and join_failed():
    state = 'failed'
  port = status.port_state if status.enabled and status.port != 'empty' and status.port_state in ('connected', 'device') else None
  stage, percent = preparation_progress(status, state)
  return JetlinkStatus(device, state, read_latency() if state == 'active' else None, port, stage, percent)


class JetlinkStatusFeed:
  """Polls off the render thread; snapshot() never does file IO."""
  def __init__(self, read=read_status, period=0.25):
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
