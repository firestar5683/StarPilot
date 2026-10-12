"""Opt-in onroad diagnostics for performance work.

Turn on or off from Settings > Developer > intense logging, or over SSH with
`python3 -m openpilot.starpilot.intense_logging on|off|status`. Takes effect at the next drive.

Control threads only append to bounded deques. A non-realtime worker thread on cores 0-3
formats and logs: late loop phases, long GC pauses and (in one host) run-queue waits.
"""
from collections import deque
import gc
import os
import threading
import time

from openpilot.common.realtime import drop_realtime, set_core_affinity
from openpilot.common.swaglog import cloudlog
from openpilot.starpilot.card_loop_timing import CardLoopTiming

FLAG_PATH = '/data/intense_logging'
LOOP_LIMIT_NS = 15_000_000
GC_PAUSE_NS = 5_000_000
SCHED_WAIT_SPIKE_NS = 10_000_000
SCHED_SUMMARY_INTERVAL_S = 10.0
PID_REFRESH_INTERVAL_S = 10.0


def enabled() -> bool:
  return os.path.exists(FLAG_PATH)


def set_enabled(on: bool) -> None:
  if on:
    with open(FLAG_PATH, 'a'):
      pass
  else:
    try:
      os.remove(FLAG_PATH)
    except FileNotFoundError:
      pass


def loop_timing(limit_ns=LOOP_LIMIT_NS):
  """Detailed phase timing for a control loop, or None when intense logging is off."""
  if not enabled():
    return None
  timing = CardLoopTiming()
  timing.LIMIT_NS = limit_ns
  return timing


class GcPauses:
  def __init__(self):
    self.pending = deque(maxlen=32)
    self.dropped = 0
    self._start = {}

  def __call__(self, phase, info):
    tid = threading.get_native_id()
    now = time.monotonic_ns()
    if phase == 'start':
      self._start[tid] = now
      return
    start = self._start.pop(tid, None)
    if start is not None and now - start >= GC_PAUSE_NS:
      if len(self.pending) == self.pending.maxlen:
        self.dropped += 1
      self.pending.append((now, now - start, info.get('generation'), info.get('collected'), tid))


def _read_schedstat(path):
  with open(path) as f:
    cpu, wait, _ = f.read().split()
  return int(cpu), int(wait)


class SchedWaits:
  """Per-thread run-queue wait (time runnable but not running) for openpilot processes."""

  def __init__(self):
    self.prev = {}
    self.window = {}
    self.tasks = []
    self.next_refresh = 0.0
    self.next_summary = time.monotonic() + SCHED_SUMMARY_INTERVAL_S

  @staticmethod
  def _openpilot_pids():
    pids = []
    for pid in os.listdir('/proc'):
      if not pid.isdigit():
        continue
      try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
          cmdline = f.read()
        exe = os.readlink(f'/proc/{pid}/exe')
      except OSError:
        continue
      if b'openpilot' in cmdline or b'starpilot' in cmdline or exe.startswith('/data/openpilot'):
        pids.append(pid)
    return pids

  def _refresh(self):
    tasks = []
    for pid in self._openpilot_pids():
      try:
        with open(f'/proc/{pid}/comm') as f:
          process = f.read().strip()
        for tid in os.listdir(f'/proc/{pid}/task'):
          with open(f'/proc/{pid}/task/{tid}/comm') as f:
            tasks.append((f'/proc/{pid}/task/{tid}/schedstat', f'{process}/{f.read().strip()}', int(tid)))
      except OSError:
        continue
    self.tasks = tasks

  def sample(self):
    now = time.monotonic()
    if now >= self.next_refresh:
      self._refresh()
      self.next_refresh = now + PID_REFRESH_INTERVAL_S
    spikes = []
    current = {}
    for path, name, tid in self.tasks:
      try:
        cpu, wait = _read_schedstat(path)
      except (OSError, ValueError):
        continue
      current[tid] = (cpu, wait)
      if tid in self.prev:
        d_cpu, d_wait = cpu - self.prev[tid][0], wait - self.prev[tid][1]
        total = self.window.setdefault(tid, [name, 0, 0, 0])
        total[1] += d_wait
        total[2] += d_cpu
        total[3] = max(total[3], d_wait)
        if d_wait >= SCHED_WAIT_SPIKE_NS:
          spikes.append((name, tid, round(d_wait / 1e6, 1), round(d_cpu / 1e6, 1)))
    self.prev = current
    if spikes:
      spikes.sort(key=lambda s: -s[2])
      cloudlog.event('intense.sched_wait_spike', error=True,
                     threads=[{'name': n, 'tid': t, 'wait_ms': w, 'cpu_ms': c} for n, t, w, c in spikes[:10]])
    if now >= self.next_summary:
      top = sorted(self.window.items(), key=lambda kv: -kv[1][1])[:15]
      cloudlog.event('intense.sched_wait_summary', window_s=SCHED_SUMMARY_INTERVAL_S,
                     threads=[{'name': v[0], 'tid': tid, 'wait_ms': round(v[1] / 1e6, 1), 'cpu_ms': round(v[2] / 1e6, 1),
                               'max_wait_ms_per_s': round(v[3] / 1e6, 1)} for tid, v in top])
      self.window = {}
      self.next_summary = now + SCHED_SUMMARY_INTERVAL_S


class IntenseLogger:
  """Drains a process's loop timing and GC pauses; optionally hosts the system-wide run-queue sampler."""

  def __init__(self, name, timing=None, *, sched_waits=False):
    self.name = name
    self.timing = timing
    self.gc_pauses = GcPauses()
    self.sched_waits = SchedWaits() if sched_waits else None
    self.stop_event = threading.Event()
    self.thread = None

  def start(self):
    gc.callbacks.append(self.gc_pauses)
    self.thread = threading.Thread(target=self._run, name=f'{self.name}_intense_log', daemon=True)
    self.thread.start()
    cloudlog.event('intense.enabled', process=self.name, loop_timing=self.timing is not None,
                   loop_limit_ms=self.timing.LIMIT_NS / 1e6 if self.timing is not None else None,
                   sched_waits=self.sched_waits is not None)
    return self

  def stop(self):
    self.stop_event.set()
    if self.gc_pauses in gc.callbacks:
      gc.callbacks.remove(self.gc_pauses)

  def drain(self):
    if self.timing is not None:
      report = self.timing.take_report()
      while report is not None:
        cloudlog.event(f'{self.name}.loop_late', error=True, **report)
        report = self.timing.take_report()
    while self.gc_pauses.pending:
      end_ns, pause_ns, generation, collected, tid = self.gc_pauses.pending.popleft()
      cloudlog.event('intense.gc_pause', error=True, process=self.name, end_ns=end_ns, pause_ms=round(pause_ns / 1e6, 2),
                     generation=generation, collected=collected, thread_id=tid, dropped=self.gc_pauses.dropped)

  def _run(self):
    # Spawned from a realtime thread: leave the control cores and FIFO policy.
    drop_realtime()
    set_core_affinity([0, 1, 2, 3])
    next_sched = time.monotonic()
    while not self.stop_event.wait(0.1):
      try:
        self.drain()
        if self.sched_waits is not None and time.monotonic() >= next_sched:
          self.sched_waits.sample()
          next_sched += 1.0
      except Exception:
        cloudlog.exception('intense logging worker failed')


def start(name, timing=None, *, sched_waits=False):
  """Start the worker when intense logging is on; returns the logger or None."""
  return IntenseLogger(name, timing, sched_waits=sched_waits).start() if enabled() else None


if __name__ == '__main__':
  import sys
  command = sys.argv[1] if len(sys.argv) > 1 else 'status'
  if command in ('on', 'off'):
    set_enabled(command == 'on')
  elif command != 'status':
    sys.exit('usage: intense_logging.py on|off|status')
  print(f"intense logging {'on' if enabled() else 'off'} (applies at the next drive)")
