"""Fixed-size nonblocking planner observations; a separate process formats logs."""
import os
from pathlib import Path
import signal
import struct
import sys
import time

PHASES = ('model_received', 'before_clock', 'clock_complete', 'profile_preferences_complete',
          'planner_update_return', 'curve_status_complete', 'conditional_sample_return',
          'conditional_attach_return', 'sibling_status_complete', 'slc_send_return', 'longplan_publish_return')
RECORD = struct.Struct('<6QdI' + 'IQQ' * len(PHASES))
SLOW_NS = 30_000_000
REPORT_NS = 1_000_000_000


class PlannerPhaseTiming:
  def __init__(self, *, spawn=True, clock=None):
    self.clock = clock or (lambda: (time.monotonic_ns(), time.thread_time_ns()))
    self.fd = self.pid = None
    self.points = []
    self.context = ()
    self.last_report_ns = self.sequence = self.dropped = 0
    if spawn:
      read_fd = write_fd = None
      try:
        read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
        os.set_blocking(write_fd, False)
        assert RECORD.size <= os.fpathconf(write_fd, 'PC_PIPE_BUF')
        actions = [(os.POSIX_SPAWN_DUP2, read_fd, 0), (os.POSIX_SPAWN_CLOSE, write_fd)]
        self.pid = os.posix_spawn(sys.executable, [sys.executable, '-B', str(Path(__file__).resolve()), '--worker'],
                                 os.environ.copy(), file_actions=actions,
                                 scheduler=(os.SCHED_OTHER, os.sched_param(0)))
        self.fd, write_fd = write_fd, None
      except (AttributeError, OSError, AssertionError, ValueError, TypeError, NotImplementedError):
        self.fd = None
      finally:
        for fd in (read_fd, write_fd):
          if fd is not None:
            try:
              os.close(fd)
            except OSError:
              pass

  def begin(self, context):
    try:
      self.context = tuple(int(value) for value in context)
      if len(self.context) != 4:
        raise ValueError("Invalid diagnostic context")
      self.points = [(0, *self.clock())] if self.fd is not None else []
    except Exception:
      self.points = []

  def mark(self, name):
    try:
      if self.points and len(self.points) < len(PHASES):
        self.points.append((PHASES.index(name), *self.clock()))
    except Exception:
      self.points = []

  def finish(self, *, relevant, solver_s):
    try:
      if not self.points or not relevant:
        return
      now = self.points[-1][1]
      if now - self.points[0][1] <= SLOW_NS or now - self.last_report_ns < REPORT_NS:
        return
      self.last_report_ns = now
      self.sequence += 1
      count = len(self.points)
      points = self.points + [(0, 0, 0)] * (len(PHASES) - count)
      data = RECORD.pack(self.sequence, *self.context, self.dropped, float(solver_s), count,
                         *(value for point in points for value in point))
      try:
        fd = self.fd
        if fd is None:
          return
        written = os.write(fd, data)
        if written != len(data):
          self.disable()
      except BlockingIOError:
        self.dropped += 1
      except OSError:
        self.disable()
    except Exception:
      self.dropped += 1
    finally:
      self.points = []

  def disable(self):
    fd, self.fd = self.fd, None
    if fd is not None:
      try:
        os.close(fd)
      except OSError:
        pass

  def close(self):
    self.disable()
    pid = self.pid
    if pid is None:
      return
    deadline = time.monotonic() + .1
    killed = False
    while time.monotonic() < deadline:
      try:
        reaped, _ = os.waitpid(pid, os.WNOHANG)
        if reaped:
          self.pid = None
          return
      except ChildProcessError:
        self.pid = None
        return
      except InterruptedError:
        continue
      except OSError:
        pass
      if not killed:
        try:
          os.kill(pid, signal.SIGKILL)
          killed = True
        except ProcessLookupError:
          pass
        except OSError:
          pass
      time.sleep(.005)
    # Keep ownership if an uninterruptible child could not be reaped in time.


def worker():
  # posix_spawn installs SCHED_OTHER atomically; this is a separate Python GIL.
  os.sched_setaffinity(0, {0, 1, 2, 3})
  sys.path.insert(0, str(Path.cwd()))
  from openpilot.common.swaglog import cloudlog
  pending = b''
  while True:
    chunk = os.read(0, RECORD.size - len(pending))
    if not chunk:
      return
    pending += chunk
    if len(pending) != RECORD.size:
      continue
    row = RECORD.unpack(pending)
    pending = b''
    sequence, model, car, sd, cc, dropped, solver, count = row[:8]
    if count > len(PHASES) or any(row[8 + 3 * i] >= len(PHASES) for i in range(count)):
      continue
    points = [(PHASES[row[8 + 3 * i]], *row[9 + 3 * i:11 + 3 * i]) for i in range(count)]
    try:
      cloudlog.event('plannerd.phase_timing', sequence=sequence, context=(model, car, sd, cc),
                     points=points, solver_seconds=solver, dropped=dropped,
                     context_columns=('model_ns', 'car_state_ns', 'selfdrive_ns', 'car_control_ns'),
                     point_columns=('phase', 'monotonic_ns', 'thread_cpu_ns'))
    except Exception:
      pass


if __name__ == '__main__' and sys.argv[1:] == ['--worker']:
  try:
    worker()
  except Exception:
    pass
