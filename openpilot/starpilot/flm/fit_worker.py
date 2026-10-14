"""Fresh bounded numerical/replay actor. Invoked only by optional learner owner."""

import json
import os
import resource
import sys

MAX_INPUT = 8 * 1024 * 1024
MAX_OUTPUT = 65536
MAX_AS = 2 * 1024 * 1024 * 1024
MAX_CPU = 20


def main():
  try:
    if sys.platform.startswith('linux'):
      import ctypes
      import signal

      parent = int(os.environ['STARPILOT_FLM_PARENT_PID'])
      if ctypes.CDLL(None).prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() != parent:
        raise ValueError('fitter parent disappeared')
    if hasattr(os, 'sched_setscheduler'):
      os.sched_setscheduler(0, os.SCHED_OTHER, os.sched_param(0))
    os.nice(10)
    for kind, ceiling in ((resource.RLIMIT_AS, MAX_AS), (resource.RLIMIT_CPU, MAX_CPU)):
      soft, hard = resource.getrlimit(kind)
      limit = min((ceiling, *[v for v in (soft, hard) if v >= 0]))
      resource.setrlimit(kind, (limit, hard))
    raw = sys.stdin.buffer.read(MAX_INPUT + 1)
    if len(raw) > MAX_INPUT:
      raise ValueError('fit input bound')
    snapshot = json.loads(raw)
    from openpilot.starpilot.flm.learner_factory import fit_snapshot

    result = fit_snapshot(snapshot)
    encoded = json.dumps(result, separators=(',', ':'), allow_nan=False).encode()
    if len(encoded) > MAX_OUTPUT:
      raise ValueError('fit result bound')
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()
    return 0
  except (Exception, MemoryError):
    # Optional process failure never modifies command owners or their state.
    return 1


if __name__ == '__main__':
  raise SystemExit(main())
