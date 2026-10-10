"""Downloads the pinned Google Play resolver in the background after Galaxy setup, while parked."""
import fcntl
import hashlib
import os
from pathlib import Path
import platform
import shutil
import tempfile
import threading
import time
import urllib.request
from urllib.parse import urlsplit

from openpilot.starpilot.system.android_auto.play_package import PACKAGE, RUNTIME


class Paused(RuntimeError):
  pass


def checked_url(url):
  parsed = urlsplit(url)
  if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443)
      or parsed.hostname not in ('github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com')):
    raise ValueError('Untrusted package URL')
  return url


class ReleaseRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self, req, fp, code, msg, headers, newurl):
    return super().redirect_request(req, fp, code, msg, headers, checked_url(newurl))


def download(asset, destination, check, progress):
  digest = hashlib.sha256()
  received = 0
  opener = urllib.request.build_opener(ReleaseRedirect())
  request = urllib.request.Request(checked_url(asset['url']), headers={'User-Agent': 'StarPilot-Galaxy-Setup'})
  with opener.open(request, timeout=10) as response, destination.open('wb') as output:
    if response.status != 200:
      raise ValueError('Incomplete package response')
    while True:
      check()
      block = response.read(64 * 1024)
      if not block:
        break
      received += len(block)
      if received > asset['bytes']:
        raise ValueError('Package exceeds expected size')
      output.write(block)
      digest.update(block)
      progress(received)
  if received != asset['bytes'] or digest.hexdigest() != asset['sha256']:
    raise ValueError('Package integrity check failed')


class PlayInstall:
  def __init__(self, *, ready, parked, destination=RUNTIME, package=PACKAGE, enabled=None, fetch=download):
    self.ready, self.parked, self.destination, self.package = ready, parked, destination, package
    self.enabled = (Path('/AGNOS').is_file() and platform.machine() == 'aarch64') if enabled is None else enabled
    self.fetch = fetch
    self.lock = threading.Lock()
    self.stop = threading.Event()
    self.thread = None
    self.retry_at = 0.0
    self.failures = 0
    self.state, self.percent = 'pending', 0
    self.setup_seen = destination.parent / '.galaxy-setup-complete'

  def mark_setup_complete(self):
    if self.enabled and not self.setup_seen.exists():
      self.setup_seen.parent.mkdir(parents=True, exist_ok=True)
      self.setup_seen.touch(mode=0o600)

  def installed(self):
    try:
      return ((self.destination / 'package-id').read_text().strip() == self.package['id'] and
              (self.destination / 'playlink').is_file())
    except OSError:
      return False

  def status(self):
    with self.lock:
      return {'state': self.state, 'percent': self.percent}

  def maintain(self):
    if not self.enabled or self.stop.is_set():
      return
    with self.lock:
      if self.state == 'ready' or self.thread is not None and self.thread.is_alive():
        return
      if self.installed():
        self.state, self.percent = 'ready', 100
        return
      if time.monotonic() < self.retry_at:
        return
      try:
        setup_ready = self.setup_seen.exists() or self.ready()
        parked = self.parked()
      except Exception:
        self._retry_later()
        return
      if not setup_ready:
        return
      if not parked:
        self.state = 'paused'
        return
      self.state, self.percent = 'downloading', 0
      self.thread = threading.Thread(target=self._run, name='galaxy-play-install', daemon=True)
      self.thread.start()

  def _retry_later(self):
    # Early failures are usually the network still coming up after boot: 30 s, 1, 2, 4 min, then every 5 min.
    self.state, self.retry_at = 'retrying', time.monotonic() + min(300, 30 * 2 ** self.failures)
    self.failures += 1

  def _run(self):
    if platform.system() == 'Linux':
      try:
        os.setpriority(os.PRIO_PROCESS, threading.get_native_id(), 10)
      except OSError:
        pass
    deadline = time.monotonic() + 1800
    def check():
      if self.stop.is_set() or not self.parked():
        raise Paused()
      if time.monotonic() > deadline:
        raise TimeoutError()
    resolver = self.package['resolver']
    def progress(received):
      with self.lock:
        self.percent = min(99, received * 100 // resolver['bytes'])
    try:
      self.destination.parent.mkdir(parents=True, exist_ok=True)
      with (self.destination.parent / '.install.lock').open('a') as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not self.installed():
          check()
          # A power loss cannot run TemporaryDirectory cleanup. The exclusive
          # lock proves no other installer still owns these staging directories.
          for leftover in self.destination.parent.glob('.download-*'):
            if leftover.is_dir() and not leftover.is_symlink():
              shutil.rmtree(leftover)
          # Room for the resolver and a margin.
          if shutil.disk_usage(self.destination.parent).free < 64 * 1024**2:
            raise OSError('Insufficient storage')
          with tempfile.TemporaryDirectory(prefix='.download-', dir=self.destination.parent) as directory:
            runtime = Path(directory) / 'runtime'
            runtime.mkdir()
            helper = runtime / 'playlink'
            self.fetch(resolver, helper, check, progress)
            check()
            with self.lock:
              self.state = 'installing'
            with helper.open('rb') as executable:
              header = executable.read(20)
            if header[:5] != b'\x7fELF\x02' or int.from_bytes(header[18:20], 'little') != 183:
              raise ValueError('Resolver is not ARM64')
            helper.chmod(0o755)
            (runtime / 'package-id').write_text(self.package['id'] + '\n')
            check()
            # Each package id installs to its own directory, so a running older version is never replaced.
            runtime.rename(self.destination)
      with self.lock:
        self.state, self.percent, self.failures = 'ready', 100, 0
    except Paused:
      with self.lock:
        self.state, self.retry_at = 'paused', time.monotonic() + 10
    except Exception:
      with self.lock:
        self._retry_later()

  def close(self):
    self.stop.set()
    if self.thread is not None:
      self.thread.join(timeout=12)
