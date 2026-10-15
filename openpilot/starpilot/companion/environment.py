"""Automatically provision the isolated companion environment while parked."""
import logging
import os
from pathlib import Path
import signal
import subprocess
import time

PYTHON = Path('/data/galaxy-ble/stardust-venv/bin/python')
COMPANION = Path(__file__).resolve().parent
REQUIREMENTS = COMPANION / 'upstream/tools/galaxy_bluetooth/bridge/requirements.txt'


class Environment:
  def __init__(self, python=PYTHON, requirements=REQUIREMENTS, installer=COMPANION / 'install_bluetooth.sh',
               run=subprocess.run, popen=subprocess.Popen, clock=time.monotonic, killpg=os.killpg):
    self.python, self.installer = python, installer
    self.run, self.popen, self.clock, self.killpg = run, popen, clock, killpg
    self.versions = dict(line.split('==', 1) for line in requirements.read_text().splitlines() if line and not line.startswith('#'))
    self.verified = False
    self.child = None
    self.log = None
    self.started = 0
    self.next_attempt = 0

  def verify(self):
    if not self.python.is_file():
      return False
    # Check actual imports and pinned versions, including after an interrupted install.
    code = ('import dbus_next, zeroconf; from Crypto.Cipher import AES; from importlib.metadata import version; ' +
            f'assert all(version(name) == expected for name, expected in {self.versions!r}.items())')
    try:
      self.run([str(self.python), '-c', code], check=True, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
      return True
    except (OSError, subprocess.SubprocessError):
      return False

  def step(self, install_allowed):
    if self.verified and self.python.is_file():
      return True
    self.verified = False
    now = self.clock()
    if self.child is not None:
      if not install_allowed or now - self.started >= 180:
        logging.info('Pausing companion setup; it will retry automatically while parked with internet')
        self.close()
        self.next_attempt = now + 60
        return False
      result = self.child.poll()
      if result is None:
        return False
      self.child = None
      self.log.close()
      self.log = None
      if result == 0 and self.verify():
        self.verified = True
        logging.info('Companion environment ready; starting LAN discovery')
        return True
      logging.warning('Companion setup incomplete; retrying automatically in 60 seconds (see stardust-setup.log)')
      self.next_attempt = now + 60
      return False
    if now < self.next_attempt:
      return False
    if self.verify():
      self.verified = True
      return True
    if not install_allowed:
      self.next_attempt = now + 60
      return False
    try:
      data = self.python.parents[2]
      data.mkdir(parents=True, exist_ok=True)
      log_path = data / 'stardust-setup.log'
      if log_path.exists() and log_path.stat().st_size > 256 * 1024:
        log_path.replace(data / 'stardust-setup.previous.log')
      self.log = os.fdopen(os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600), 'a')
      os.chmod(log_path, 0o600)
      self.child = self.popen(['bash', str(self.installer)], start_new_session=True,
                              env={**os.environ, 'COMPANION_VENV': str(self.python.parents[1])},
                              stdout=self.log, stderr=subprocess.STDOUT)
      self.started = now
      logging.info('Preparing companion LAN discovery automatically; comma needs internet for the first setup')
    except OSError:
      self.close()
      self.next_attempt = now + 60
      logging.exception('Could not start companion setup; will retry automatically')
    return False

  def close(self):
    if self.child is not None:
      # Stop venv/pip descendants as well when driving starts or the supervisor exits.
      try:
        self.killpg(self.child.pid, signal.SIGTERM)
      except ProcessLookupError:
        pass
      try:
        self.child.wait(timeout=2)
      except subprocess.TimeoutExpired:
        try:
          self.killpg(self.child.pid, signal.SIGKILL)
        except ProcessLookupError:
          pass
        self.child.wait(timeout=2)
      self.child = None
    if self.log is not None:
      self.log.close()
      self.log = None
