"""Install and supervise the phone bridge without changing StarPilot settings."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

DATA = Path('/data/galaxy-ble')
BRIDGE = Path(__file__).resolve().parent / 'bridge'
UNIT = 'galaxy-ble-fork.service'
LAN_UNIT = 'galaxy-lan-discovery.service'


def write_json(path, value):
  path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
  fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.setup-')
  try:
    with os.fdopen(fd, 'w') as stream:
      json.dump(value, stream)
    os.replace(temporary, path)
  finally:
    if os.path.exists(temporary):
      os.unlink(temporary)


def setup_status(data=DATA):
  try:
    value = json.loads((data / 'setup-status.json').read_text())
    if time.time() - value['updated'] > 45:
      return 'Bridge startup pending'
    return value['message']
  except (OSError, ValueError, KeyError, TypeError):
    return 'Bridge startup pending'


def retry_setup(data=DATA):
  write_json(data / 'retry-setup.json', {'requested': time.time()})


class Bootstrap:
  def __init__(self, params, data=DATA, bridge=BRIDGE, run=subprocess.run):
    self.params, self.data, self.bridge, self.run = params, data, bridge, run
    self.verified = None
    self.next_attempt = 0
    self.registered = False
    self.discovery_registered = False

  def status(self, state, message):
    write_json(self.data / 'setup-status.json', {'state': state, 'message': message, 'updated': time.time()})

  def command(self, args, timeout=20, **kwargs):
    return self.run(args, timeout=timeout, check=True, **kwargs)

  def systemctl(self, *args, **kwargs):
    return self.command(['sudo', '-n', 'systemctl', *args], **kwargs)

  def step(self):
    requested = self.data / 'retry-setup.json'
    if requested.exists():
      requested.unlink(missing_ok=True)
      self.next_attempt = 0
      self.verified = None
      self.registered = False
    if time.monotonic() < self.next_attempt:
      self.status('error', 'Setup failed. Connect comma to internet, then Retry setup. See setup.log.')
      return
    try:
      digest = hashlib.sha256((self.bridge / 'requirements.txt').read_bytes()).hexdigest()
      python = self.data / 'venv/bin/python'
      receipt = self.data / 'installed-requirements'
      if self.verified != digest:
        valid = python.exists() and receipt.exists() and receipt.read_text() == digest
        if valid:
          try:
            self.command([str(python), '-c', 'import dbus_next; import zeroconf; from Crypto.Cipher import AES'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
          except (subprocess.SubprocessError, OSError):
            valid = False
        if not valid:
          if self.params.get_bool('IsOnroad'):
            self.status('waiting', 'Park to finish Bluetooth setup')
            return
          self.status('installing', 'Installing Bluetooth bridge. Comma needs internet.')
          self.run(['sudo', '-n', 'systemctl', 'stop', UNIT, LAN_UNIT], timeout=20, check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
          log_path = self.data / 'setup.log'
          if log_path.exists() and log_path.stat().st_size > 256 * 1024:
            os.replace(log_path, self.data / 'setup.previous.log')
          env = dict(os.environ, GALAXY_BLE_DATA_DIR=str(self.data), GALAXY_BLE_QUIET='1')
          with log_path.open('a') as log:
            os.chmod(log_path, 0o600)
            self.command(['sh', str(self.bridge / 'install.sh')], timeout=180,
                         stdout=log, stderr=subprocess.STDOUT, env=env)
          receipt.write_text(digest)
          os.chmod(receipt, 0o600)
          self.registered = False
        self.verified = digest
      if not self.registered:
        self.systemctl('link', '--runtime', str(self.bridge / UNIT), stdout=subprocess.DEVNULL)
        self.systemctl('daemon-reload', stdout=subprocess.DEVNULL)
        self.registered = True
      # Discovery remains available when Bluetooth is off or the BLE service retries.
      # An optional discovery failure must not prevent Bluetooth startup.
      try:
        if not self.discovery_registered:
          self.systemctl('link', '--runtime', str(self.bridge / LAN_UNIT), stdout=subprocess.DEVNULL)
          self.systemctl('daemon-reload', stdout=subprocess.DEVNULL)
          self.discovery_registered = True
        self.systemctl('start', LAN_UNIT, stdout=subprocess.DEVNULL)
      except (OSError, subprocess.SubprocessError):
        pass
      self.systemctl('start', UNIT, stdout=subprocess.DEVNULL)
      try:
        pid = json.loads((self.data / 'bridge-ready.json').read_text())['pid']
        result = self.systemctl('show', UNIT, '--property=MainPID', '--value', capture_output=True, text=True)
        running = pid == int(result.stdout.strip()) and pid > 0
      except (OSError, ValueError, KeyError, TypeError):
        running = False
      self.status('ready' if running else 'waiting', 'Ready to pair' if running else 'Waiting for Bluetooth. Enable Bluetooth on comma.')
    except (OSError, subprocess.SubprocessError, ValueError):
      self.next_attempt = time.monotonic() + 60
      self.status('error', 'Setup failed. Connect comma to internet, then Retry setup. See setup.log.')


def main():
  from openpilot.common.params import Params
  DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
  os.chmod(DATA, 0o700)
  with (DATA / 'bootstrap.lock').open('w') as lock:
    try:
      fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
      return
    worker = Bootstrap(Params())
    while True:
      worker.step()
      time.sleep(10)


if __name__ == '__main__':
  main()

