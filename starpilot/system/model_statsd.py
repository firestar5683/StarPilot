#!/usr/bin/env python3
"""Optional passive observer. No publishers, Params writes, control hooks or replay.

Non-conflated sockets preserve short pedal/steering edges. A bounded 100ms
reorder buffer aligns service timestamps. Gaps are excluded, not interpolated.
SQLite runs only here, never in modeld/controlsd. Shutdown is not a disengagement.
"""
import heapq
import logging
import os
import signal
import sys
import time
import uuid
from pathlib import Path
from collections import Counter
from types import SimpleNamespace

from openpilot.starpilot.common.model_stats import Reducer, Sample, parse_identity
from openpilot.starpilot.common.model_stats_store import Store

SERVICES = ('carState', 'carControl', 'selfdriveState', 'starpilotCarState', 'deviceState', 'modelV2', 'starpilotModelV2')
FRESHNESS = {'carControl': .25, 'selfdriveState': .25, 'starpilotCarState': .25, 'deviceState': 2.5}


# Observer-local budgets, not control/transport configuration. Native receive
# allocates ONE raw message before its size is knowable; never bulk-drain.
MAX_TICK_MESSAGES = 256
MAX_EVENT_BYTES = 64 * 1024
MAX_TICK_BYTES = 1024 * 1024
MAX_TICK_SECONDS = .005
MAX_PENDING_EVENTS = 2048
MAX_PENDING_BYTES = 4 * 1024 * 1024
MAX_CHECKPOINTS = 16
MAX_CHECKPOINT_BYTES = 4 * 1024 * 1024
MAX_METRIC_ROWS = 128
MAX_MODEL_CACHE = 256


def decode_event(raw):
  # Do not use messaging.log_from_bytes: that disables traversal limits. Copy
  # only scalar observation fields, then release the native reader/raw buffer.
  from cereal import log
  fields = {
    'carState': ('vEgo', 'canValid', 'gearShifter', 'steeringPressed', 'brakePressed', 'gasPressed'),
    'carControl': ('latActive', 'longActive'), 'selfdriveState': ('enabled',),
    'starpilotCarState': ('alwaysOnLateralEnabled',), 'deviceState': ('started',),
    'modelV2': (), 'starpilotModelV2': ('modelMonoTime', 'runtimeIdentity'),
  }
  with log.Event.from_bytes(raw, traversal_limit_in_words=MAX_EVENT_BYTES // 8, nesting_limit=16) as event:
    name = event.which()
    data = getattr(event, name)
    values = {key: str(getattr(data, key)) if key == 'gearShifter' else getattr(data, key) for key in fields[name]}
    return SimpleNamespace(logMonoTime=event.logMonoTime, valid=event.valid, **{name: SimpleNamespace(**values)})


class BoundedEvents:
  def __init__(self):
    self.pending = []
    self.bytes = 0
    self.serial = 0
    self.cursor = 0
    self.loss_reason = self.yield_reason = None
    self.high_water_events = self.high_water_bytes = 0

  def clear(self):
    self.pending.clear()
    self.bytes = 0

  def receive(self, sockets, decode, clock=time.monotonic):
    """Yield without losing events on cooperative budgets; True is actual loss.

    Reserve one maximum-size event before receiving: no raw message is consumed
    merely to discover that the remaining per-pass byte budget is too small.
    Native calls are nonblocking; a single decode cannot be preempted.
    """
    self.loss_reason = None
    self.yield_reason = None
    active = list(sockets)
    if not active:
      return False
    indexes = {sock: index for index, sock in enumerate(active)}
    first = self.cursor % len(active)
    active = active[first:] + active[:first]
    deadline = clock() + MAX_TICK_SECONDS
    count = used = 0
    while active:
      if count >= MAX_TICK_MESSAGES:
        self.yield_reason = 'message_budget'
        return False
      if used + MAX_EVENT_BYTES > MAX_TICK_BYTES:
        self.yield_reason = 'byte_budget'
        return False
      if clock() >= deadline:
        self.yield_reason = 'time_budget'
        return False
      if len(self.pending) >= MAX_PENDING_EVENTS or self.bytes >= MAX_PENDING_BYTES:
        return self.lose('pending_capacity')
      sock = active.pop(0)
      self.cursor = (indexes[sock] + 1) % len(sockets)
      raw = sock.receive(non_blocking=True)
      if raw is None:
        continue
      count += 1
      size = len(raw)
      if size > MAX_EVENT_BYTES:
        return self.lose('oversize_raw')
      try:
        event = decode(raw)
        stamp = event.logMonoTime
        size = max(size, snapshot_size((stamp, self.serial + 1, sockets[sock], event, 0)) + 8)
      except Exception:
        return self.lose('decode_error')
      if size > MAX_EVENT_BYTES:
        return self.lose('oversize_decoded')
      if size > MAX_PENDING_BYTES - self.bytes:
        return self.lose('pending_capacity')
      # Keep the event even when decode/preemption crossed the cooperative
      # deadline. The next iteration yields before receiving anything else.
      self.serial += 1
      heapq.heappush(self.pending, (stamp, self.serial, sockets[sock], event, size))
      self.bytes += size
      used += size
      self.high_water_events = max(self.high_water_events, len(self.pending))
      self.high_water_bytes = max(self.high_water_bytes, self.bytes)
      active.append(sock)
    return False

  def lose(self, reason):
    self.loss_reason = reason
    self.clear()
    return True

  def pop(self):
    stamp, serial, name, event, size = heapq.heappop(self.pending)
    self.bytes -= size
    return stamp, serial, name, event


def snapshot_size(value):
  """Conservative Python retention estimate (shared objects counted repeatedly)."""
  size = sys.getsizeof(value)
  if isinstance(value, SimpleNamespace):
    return size + snapshot_size(vars(value))
  if isinstance(value, dict):
    for key, item in value.items():
      size += snapshot_size(key) + snapshot_size(item)
      if size > MAX_CHECKPOINT_BYTES:
        break
  elif isinstance(value, (list, tuple)):
    for item in value:
      size += snapshot_size(item)
      if size > MAX_CHECKPOINT_BYTES:
        break
  return size


class Telemetry:
  def __init__(self):
    self.latest = {}
    self.models = {}
    self.identities = {}
    self.runtime = None

  def feed(self, service, timestamp, valid, data):
    t = timestamp / 1e9
    # Reorder buffering cannot recover messages arriving after its deadline.
    # Never let those messages rewrite already-observed edges or road state.
    if service in self.latest and t <= self.latest[service][0]:
      return None
    if service == 'modelV2':
      self.models[timestamp] = valid
    elif service == 'starpilotModelV2':
      self.identities[getattr(data, 'modelMonoTime', 0)] = parse_identity(getattr(data, 'runtimeIdentity', '')) if valid else None
    else:
      self.latest[service] = (t, valid, data)
    for stamp in sorted(self.models.keys() & self.identities.keys()):
      if self.runtime is None or stamp > self.runtime[0]:
        self.runtime = (stamp, self.identities[stamp] if self.models[stamp] else None)
    for cache in (self.models, self.identities):
      for stamp in list(cache):
        if timestamp - stamp > 1e9:
          del cache[stamp]
      while len(cache) > MAX_MODEL_CACHE:
        del cache[next(iter(cache))]  # unmatched provenance is unavailable, never guessed
    if service != 'carState':
      return None
    fresh = valid and all(name in self.latest and self.latest[name][1]
                          and 0 <= t - self.latest[name][0] <= age for name, age in FRESHNESS.items())
    runtime_fresh = self.runtime and 0 <= timestamp - self.runtime[0] <= 250_000_000
    if not fresh or not runtime_fresh or self.runtime is None:
      return Sample(t, None, 0, valid=False)
    cc, sd, sp, device = (self.latest[name][2] for name in FRESHNESS)
    return Sample(t, self.runtime[1], data.vEgo, enabled=sd.enabled,
                  aol=sp.alwaysOnLateralEnabled, lat=cc.latActive, long=cc.longActive,
                  steering=data.steeringPressed, brake=data.brakePressed, gas=data.gasPressed,
                  reverse=str(data.gearShifter) == 'reverse', onroad=device.started,
                  valid=bool(data.canValid))


class Checkpoints:
  """Bounded failed cumulative snapshots; never evict counters silently.

  Saturation latches collection off for this process. A constant-size loss marker
  is retried alongside retained counters, including after storage recovers. It
  deliberately remains visible in history across restart (excluded coverage is
  not repaired by restarting). Power loss before any write can still lose RAM.
  """
  def __init__(self, factory=Store):
    self.factory = factory
    self.store = None
    self.pending = {}
    self.sizes = {}
    self.pending_bytes = 0
    self.retry_at = 0
    self.suspended = False
    self.loss_marker = None
    self.blocked_drive = None

  def suspend(self):
    if not self.suspended:
      self.suspended = True
      marker = Reducer()
      marker.break_stream()
      self.loss_marker = (uuid.uuid4().hex, time.time(), marker.snapshot() | {'coverageLoss': True})
      logging.error('Model statistics resource limit: collection suspended; coverage lost; retained counters retrying')

  def submit(self, drive, started, snapshot, complete=False):
    size = snapshot_size((drive, started, snapshot, complete))
    total = self.pending_bytes - self.sizes.get(drive, 0) + size
    if ((drive not in self.pending and ((self.suspended and drive != self.blocked_drive) or len(self.pending) >= MAX_CHECKPOINTS))
        or total > MAX_CHECKPOINT_BYTES):
      if not self.suspended:
        self.blocked_drive = drive
      self.suspend()
      return False
    self.pending[drive] = (started, snapshot, complete)
    self.sizes[drive] = size
    self.pending_bytes = total
    return True

  def flush(self, now):
    if not self.pending and self.loss_marker is None:
      return True
    if now < self.retry_at:
      return False
    try:
      if self.store is None:
        self.store = self.factory()
      if self.loss_marker is not None:
        drive, started, snapshot = self.loss_marker
        self.store.checkpoint(drive, started, snapshot, complete=False)
        self.loss_marker = None
      # Count is hard bounded; one flush cannot grow with outage duration.
      for drive, (started, snapshot, complete) in list(self.pending.items()):
        self.store.checkpoint(drive, started, snapshot, complete=complete)
        del self.pending[drive]
        self.pending_bytes -= self.sizes.pop(drive)
      return True
    except Exception:
      logging.exception('Model statistics checkpoint failed; retained for retry; driving is unaffected')
      if self.store is not None:
        try:
          self.store.close()
        except Exception:
          logging.exception('Model statistics store close failed')
      self.store = None
      self.retry_at = now + 30
      return False


class Diagnostics:
  """Constant-size counters/maxima, no per-message log or retained samples."""
  def __init__(self):
    self.counts = Counter()
    self.maxima = {}

  def timing(self, name, wall, cpu):
    for key, value in ((name + 'WallMs', wall * 1000), (name + 'CpuMs', cpu * 1000),
                       (name + 'WaitingMs', max(0, wall - cpu) * 1000)):
      self.maxima[key] = max(self.maxima.get(key, 0), round(value, 3))

  def snapshot(self, events):
    return {'counts': dict(self.counts), **self.maxima,
            'pendingHighWaterEvents': events.high_water_events,
            'pendingHighWaterBytes': events.high_water_bytes}


def current_route(path=Path('/data/params/d/CurrentRoute')):
  # Logger clears this on each onroad transition, then publishes its new ID.
  # Read only at start/checkpoint, never from a control process or per sample.
  import re
  try:
    with path.open('rb') as handle:
      value = handle.read(129).decode('ascii').strip()
    return value if re.fullmatch(r'(?:[0-9a-f]{8}--[0-9a-f]{10}|\d{4}-\d{2}-\d{2}--\d{2}-\d{2}-\d{2})', value) else None
  except (OSError, UnicodeError):
    return None


def main():
  import fcntl
  from openpilot.starpilot.common.model_stats_store import DEFAULT_PATH
  logging.basicConfig(level=logging.INFO)
  os.nice(19)
  DEFAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
  lock = (DEFAULT_PATH.parent / 'model_statsd.lock').open('a')
  try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
  except BlockingIOError:
    lock.close()
    return
  parent_pid = os.getppid()
  import cereal.messaging as messaging
  # Imported only by the process, so reducer/adapter tests need no native cereal.
  poller = messaging.Poller()
  sockets = {messaging.sub_sock(name, poller=poller, conflate=False): name for name in SERVICES}
  telemetry = Telemetry()
  reducer = None
  writer = Checkpoints()
  drive = None
  started = 0
  last_write = 0
  events = BoundedEvents()
  diagnostics = Diagnostics()
  route = None
  last_diagnostic_log = 0
  discard_before = 0
  unassigned_gap = False
  stopping = False

  def stop(*_):
    nonlocal stopping
    stopping = True

  signal.signal(signal.SIGTERM, stop)
  signal.signal(signal.SIGINT, stop)

  def checkpoint(complete=False):
    nonlocal last_write, route
    if reducer is not None:
      route = route or current_route()
      writer.submit(drive, started, reducer.snapshot() | {
        'routeName': route, 'diagnostics': diagnostics.snapshot(events)}, complete)
    last_write = time.monotonic()
    cpu = time.process_time()
    result = writer.flush(last_write)
    diagnostics.timing('storage', time.monotonic() - last_write, time.process_time() - cpu)
    if not result:
      diagnostics.counts['storage_retry'] += 1
    return result

  try:
    while not stopping and os.getppid() == parent_pid:
      if writer.suspended:
        # No more drive/reducer/socket growth. Preserve this bounded reducer for
        # retry if its final cumulative snapshot could not enter the queue.
        if reducer is not None:
          reducer.break_stream()
        if time.monotonic() - last_write >= 10:
          checkpoint()
        time.sleep(.02)
        continue
      poller.poll(20)
      receive_wall, receive_cpu = time.monotonic(), time.process_time()
      lost = events.receive(sockets, decode_event)
      diagnostics.timing('receive', time.monotonic() - receive_wall, time.process_time() - receive_cpu)
      if events.yield_reason:
        diagnostics.counts[events.yield_reason] += 1
      if lost:
        diagnostics.counts[events.loss_reason or 'input_loss'] += 1
        discard_before = int(time.monotonic() * 1e9)
        telemetry = Telemetry()
        if reducer:
          reducer.break_stream()
        else:
          unassigned_gap = True
      cutoff = int((time.monotonic() - .1) * 1e9)
      processing_wall, processing_cpu = time.monotonic(), time.process_time()
      processing_deadline = processing_wall + MAX_TICK_SECONDS
      processed = 0
      while events.pending and events.pending[0][0] <= cutoff:
        if processed >= MAX_TICK_MESSAGES or time.monotonic() >= processing_deadline:
          break
        stamp, _, name, event = events.pop()
        processed += 1
        if stamp < discard_before or stamp < cutoff - 250_000_000:
          diagnostics.counts['pre_break_backlog' if stamp < discard_before else 'stale_event'] += 1
          telemetry = Telemetry()
          if reducer:
            reducer.break_stream()
          else:
            unassigned_gap = True
          continue
        data = getattr(event, name)
        if name in telemetry.latest and stamp / 1e9 <= telemetry.latest[name][0]:
          continue
        if name == 'deviceState' and event.valid:
          if data.started and reducer is None:
            reducer, drive = Reducer(), uuid.uuid4().hex
            started = time.time() - (time.monotonic() - stamp / 1e9)
            route = current_route()
            if unassigned_gap:
              reducer.break_stream()
              unassigned_gap = False
          elif not data.started and reducer is not None:
            checkpoint(complete=True)
            if writer.suspended:
              reducer.break_stream()
              events.clear()
              break
            reducer, drive = None, None
        sample = telemetry.feed(name, stamp, event.valid, data)
        if reducer is not None and sample is not None:
          # An update can introduce at most two owner/mode rows. Stop rather
          # than evict attribution/counters through pathological identity churn.
          if len(reducer.metrics) >= MAX_METRIC_ROWS - 2:
            reducer.break_stream()
            writer.blocked_drive = drive
            writer.suspend()
            events.clear()
            break
          if not sample.usable:
            diagnostics.counts['unusable_sample'] += 1
            if not sample.owner:
              diagnostics.counts['identity_or_service_unavailable'] += 1
            elif sample.reverse:
              diagnostics.counts['reverse_sample'] += 1
            elif not 0 <= sample.speed <= 100:
              diagnostics.counts['invalid_speed'] += 1
            elif not sample.valid:
              diagnostics.counts['invalid_can'] += 1
          reducer.update(sample)
      diagnostics.timing('reduction', time.monotonic() - processing_wall, time.process_time() - processing_cpu)
      if processed >= MAX_TICK_MESSAGES or time.monotonic() >= processing_deadline:
        diagnostics.counts['reduction_budget'] += 1
      if reducer is not None and reducer.last_t is not None and cutoff / 1e9 - reducer.last_t > .25:
        reducer.break_stream()
      if time.monotonic() - last_write >= 10:
        checkpoint()
      if time.monotonic() - last_diagnostic_log >= 60:
        logging.info('Model statistics diagnostics: %s', diagnostics.snapshot(events))
        last_diagnostic_log = time.monotonic()
      if events.yield_reason or processed >= MAX_TICK_MESSAGES:
        time.sleep(.001)  # explicitly yield CPU while catching up; no busy drain loop
  finally:
    # A process stop mid-drive leaves an incomplete fragment, not a false event.
    checkpoint()
    if writer.store is not None:
      writer.store.close()
    lock.close()


def start_observer():
  """Galaxy-owned optional subprocess, deliberately absent from managerState.

  Started at server startup, not by a page/HTTP request. Failure cannot trigger
  processNotRunning. Parent death is observed by the child; retries are bounded.
  """
  import subprocess
  import sys
  import threading

  def supervise():
    while True:
      try:
        child = subprocess.Popen([sys.executable, '-m', 'openpilot.starpilot.system.model_statsd'],
                                 stdin=subprocess.DEVNULL)
        child.wait()
      except Exception:
        logging.exception('Optional model statistics observer failed')
      time.sleep(30)

  threading.Thread(target=supervise, name='model-statistics-supervisor', daemon=True).start()


if __name__ == '__main__':
  main()
