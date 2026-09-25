"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

Root on the comma: scripts/comma/jetlink-root.sh under sudo -n, and nothing
else. The script leaves its own record of the gadget and its network in
/dev/shm (jetlink-gadget, jetlink-net), so a False here only says the call
failed; the reason is in the log line and, for the gadget, in those files.

    root.run('gadget', '--ios')
    root.run('port', 'hold', timeout=root.PORT_TIMEOUT)
    root.run('vm', 'apply')

Only AGNOS has the gadget stack, the port's lever and the sysctls, so
everywhere else run() is a quiet False and nothing is spawned.
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

log = logging.getLogger('jetlink.comma')

AGNOS = os.path.isfile('/AGNOS')

# Resolved, so that <openpilot>/jetlink, a symlink into jetlink_repo, still
# leads to the checkout's scripts.
SCRIPT = Path(__file__).resolve().parents[2] / 'scripts' / 'comma' / 'jetlink-root.sh'

# sudo, configfs, and for iOS nmcli and dnsmasq
TIMEOUT = 30.0
# sudo and two echos take tens of ms. Short, because the owner lets the port go
# before it closes FunctionFS, inside manager's 5 s
PORT_TIMEOUT = 2.0
# port source: the kernel waits up to 2 s for the far end's PR_Swap
SWAP_TIMEOUT = 4.0


def run(*args: str, timeout: float = TIMEOUT) -> bool:
  """sudo -n bash SCRIPT *args, on AGNOS. True when it exits 0; otherwise one
  log line, with the last thing the script wrote to stderr, and False. Off
  AGNOS a False with no log line. Never raises."""
  if not AGNOS:
    return False
  what = ' '.join((SCRIPT.name, *args))
  try:
    result = subprocess.run(['sudo', '-n', 'bash', str(SCRIPT), *args], stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE, timeout=timeout, text=True, errors='replace')
  except subprocess.TimeoutExpired:
    log.error("jetlink: %s timed out after %.0f s", what, timeout)
    return False
  except Exception as e:
    log.error("jetlink: %s did not run: %s", what, e)
    return False
  if result.returncode == 0:
    return True
  lines = (result.stderr or '').strip().splitlines()
  log.error("jetlink: %s failed (exit %d): %s", what, result.returncode, lines[-1] if lines else 'no output')
  return False
