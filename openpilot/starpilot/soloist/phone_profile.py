"""Temporary AGNOS BlueALSA receiving profile. Invoked as root with a fixed action.

Only a feature-owned /run drop-in is changed; Bluetooth power, bonds, bluetoothd,
HFP and the on-disk service definition are untouched. Unknown service commands
are rejected rather than replaced. The override disappears on reboot.
"""
from __future__ import annotations

import fcntl
from pathlib import Path
import subprocess
import sys

DROP_IN = Path('/run/systemd/system/bluealsa.service.d/90-starpilot-phone.conf')
CONTENTS = '[Service]\nExecStart=\nExecStart=/usr/bin/bluealsa -p a2dp-source -p a2dp-sink\n'


def systemctl(*args):
  return subprocess.run(['/usr/bin/systemctl', *args], check=True, capture_output=True, text=True, timeout=15).stdout.strip()


def configure(action: str, path: Path = DROP_IN, run=systemctl) -> None:
  if action not in ('acquire', 'release'):
    raise ValueError('Unknown profile action')
  if path.exists() and path.read_text() != CONTENTS:
    raise RuntimeError('Phone audio profile override was changed externally')
  if action == 'release':
    if path.exists():
      path.unlink()
      run('daemon-reload')
      run('try-restart', 'bluealsa.service')
    return
  command = run('show', '--property=ExecStart', '--value', 'bluealsa.service')
  if 'argv[]=/usr/bin/bluealsa -p a2dp-source -p a2dp-sink ;' in command:
    run('start', 'bluealsa.service')
    return
  if 'argv[]=/usr/bin/bluealsa -p a2dp-source ;' not in command:
    raise RuntimeError('Unsupported BlueALSA service configuration; phone audio was not enabled')
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(CONTENTS)
  try:
    run('daemon-reload')
    run('restart', 'bluealsa.service')
  except Exception:
    path.unlink(missing_ok=True)
    run('daemon-reload')
    run('try-restart', 'bluealsa.service')
    raise


if __name__ == '__main__':
  # Serializes recovery and normal shutdown; never takes the adapter's pairing lease.
  with open('/run/starpilot-phone-profile.lock', 'w') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    configure(sys.argv[1])
