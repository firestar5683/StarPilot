"""Temporary offroad benchmark CPU settings; restore on exit. No manager changes."""
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

root = Path('/data/sa3-feasibility')

def is_offroad():
  check = subprocess.run(
    ['/usr/local/venv/bin/python', '-c',
     'from openpilot.common.params import Params; raise SystemExit(int(Params().get_bool("IsOnroad")))'],
    cwd='/data/openpilot', check=False,
  )
  return check.returncode == 0

if not is_offroad():
  raise SystemExit('This isolated benchmark requires a verified offroad device.')

paths = [Path(f'/sys/devices/system/cpu/cpu{i}/online') for i in range(4, 8)]
paths += [Path('/sys/devices/system/cpu/cpufreq/policy4') / n for n in ['scaling_max_freq', 'scaling_governor']]
saved = {str(p): p.read_text().strip() for p in paths}
(root / 'verify_trained_power_before.json').write_text(json.dumps(saved, indent=2))

def write(path, value):
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
  child = subprocess.Popen(['taskset', '-c', '4-7', 'bash', str(root / 'run_verify_trained.sh'), *sys.argv[1:]], start_new_session=True)
  rc = child.wait()
finally:
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
      for path in reversed(paths):
        write(path, saved[str(path)])
      (root / 'verify_trained_power_after.json').write_text(json.dumps({str(p): p.read_text().strip() for p in paths}, indent=2))
      print('POWER_RESTORED', flush=True)
    else:
      print('Device no longer verified offroad; leaving active CPU settings to hardwared.', flush=True)
sys.exit(rc)
