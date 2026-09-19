"""Temporary offroad benchmark CPU settings; restore on exit. No manager changes."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

root = Path('/data/roadscore')

_params = None
def is_offroad():
  global _params
  if _params is None:
    # Always inspect the real device, never a replay's temporary Params root.
    for key in ['OPENPILOT_PREFIX', 'PARAMS_ROOT']:
      os.environ.pop(key, None)
    sys.path.insert(0, '/data/openpilot')
    from openpilot.common.params import Params
    _params = Params()
  return not _params.get_bool('IsOnroad')

if not is_offroad():
  raise SystemExit('This isolated benchmark requires a verified offroad device.')

paths = [Path(f'/sys/devices/system/cpu/cpu{i}/online') for i in range(4, 8)]
paths += [Path('/sys/devices/system/cpu/cpufreq/policy4') / n for n in ['scaling_max_freq', 'scaling_governor']]
saved = {str(p): p.read_text().strip() for p in paths}
(root / 'worker_power_before.json').write_text(json.dumps(saved, indent=2))

def write(path, value):
  # Offline clusters can reject redundant governor writes; verify before mutating.
  if Path(path).read_text().strip() == value:
    return
  subprocess.run(['sudo', '-n', 'tee', str(path)], input=value + '\n', text=True, stdout=subprocess.DEVNULL, check=True)

def stop(sig, frame):
  raise KeyboardInterrupt

signal.signal(signal.SIGTERM, stop)
child = None
rc = 1
try:
  for path in paths[:4]:
    write(path, '1')
  write(paths[4], '1689600')
  write(paths[5], 'performance')
  print('POWER', json.dumps({str(p): p.read_text().strip() for p in paths}), flush=True)
  child = subprocess.Popen(['taskset', '-c', '4-7', 'bash', str(root / 'prototype/run_worker.sh'), *sys.argv[1:]], start_new_session=True)
  try:
    from power_lease import maintain
    desired = {str(p): '1' for p in paths[:4]}
    # Reassert only online bits changed by screen-off power saving. Never
    # reassert clock limits over any thermal controller's later decision.
    corrections = []
    (root / 'worker_power_corrections.json').write_text('[]')
    while child.poll() is None:
      changed = maintain(desired, is_offroad, lambda p: Path(p).read_text().strip(), write)
      if changed is None:
        print('REAL_ONROAD_STOP: relinquishing worker CPU ownership', flush=True)
        break
      if changed:
        # CPU hotplug can broaden a task's affinity when its entire mask goes offline.
        if child.poll() is None:
          try:os.sched_setaffinity(child.pid, {4, 5, 6, 7})
          except ProcessLookupError:pass
        corrections.append({'wall': time.time(), 'paths': changed})
        (root / 'worker_power_corrections.json').write_text(json.dumps(corrections, indent=2))
        print('POWER_REASSERTED', json.dumps(changed), flush=True)
      time.sleep(1)
    rc = child.returncode if child.returncode is not None else 0
  except KeyboardInterrupt:
    rc = 0
finally:
  (root / 'generated/worker_ready').unlink(missing_ok=True)
  try:
    if child is not None and child.poll() is None:
      os.killpg(child.pid, signal.SIGTERM)
      try:
        child.wait(timeout=15)
      except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait()
  finally:
    if is_offroad():
      errors=[]
      for path in reversed(paths):
        try:write(path, saved[str(path)])
        except subprocess.CalledProcessError as e:errors.append(str(e))
      after={str(p): p.read_text().strip() for p in paths}
      (root / 'worker_power_after.json').write_text(json.dumps(after, indent=2))
      if after != saved:raise RuntimeError('CPU restoration mismatch: '+repr(errors))
      print('POWER_RESTORED', flush=True)
    else:
      print('Device no longer verified offroad; leaving active CPU settings to hardwared.', flush=True)
sys.exit(rc)
