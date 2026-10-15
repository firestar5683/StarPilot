"""Automatically prepare and supervise companion BLE and LAN discovery."""
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

from openpilot.starpilot.companion.bluetooth import KEY_PATH
from openpilot.starpilot.companion.environment import Environment, PYTHON
from openpilot.starpilot.galaxy.companion import phone_uplink_active

ROOT = Path(__file__).resolve().parents[3]


def main():
  from openpilot.common.params import Params
  params = Params()
  stopped = threading.Event()
  for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, lambda *_: stopped.set())
  children = {}
  next_start = {}
  environment = Environment()
  try:
    while not stopped.is_set():
      if environment.step(install_allowed=params.get_bool('IsOffroad') and not phone_uplink_active()):
        commands = {'lan': [str(PYTHON), '-m', 'openpilot.starpilot.companion.lan_discovery']}
        if KEY_PATH.is_file():
          commands['ble'] = [str(PYTHON), '-m', 'openpilot.starpilot.companion.bluetooth']
        for name, command in commands.items():
          if (name not in children or children[name].poll() is not None) and time.monotonic() >= next_start.get(name, 0):
            # Neither child changes Bluetooth power, bonds, NetworkManager settings or the other fork's units.
            children[name] = subprocess.Popen(command, cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT)})
            next_start[name] = time.monotonic() + 10
      stopped.wait(2)
  finally:
    environment.close()
    for child in children.values():
      if child.poll() is None:
        child.terminate()
    for child in children.values():
      try:
        child.wait(timeout=5)
      except subprocess.TimeoutExpired:
        child.kill()
        child.wait()


if __name__ == '__main__':
  main()
