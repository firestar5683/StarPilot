"""Supervise BLE and LAN discovery in an isolated, explicitly provisioned environment."""
import os
from pathlib import Path
import signal
import subprocess
import threading

from openpilot.starpilot.companion.bluetooth import KEY_PATH, UPSTREAM

PYTHON = Path('/data/galaxy-ble/stardust-venv/bin/python')
ROOT = Path(__file__).resolve().parents[3]


def main():
  stopped = threading.Event()
  for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, lambda *_: stopped.set())
  children = {}
  try:
    while not stopped.is_set():
      if PYTHON.is_file():
        commands = {'lan': [str(PYTHON), str(UPSTREAM / 'lan_discovery.py')]}
        if KEY_PATH.is_file():
          commands['ble'] = [str(PYTHON), '-m', 'openpilot.starpilot.companion.bluetooth']
        for name, command in commands.items():
          if name not in children or children[name].poll() is not None:
            # Neither child changes Bluetooth power, bonds, NetworkManager settings or the other fork's units.
            children[name] = subprocess.Popen(command, cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT)})
      stopped.wait(10)
  finally:
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
