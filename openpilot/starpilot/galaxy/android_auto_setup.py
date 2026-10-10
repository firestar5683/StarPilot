"""Galaxy setup owner for a user's own Android Auto package.

The HTTP server must authenticate the caller before invoking this owner. This
module has no routes, device side effects, or credential material on import.
"""
from __future__ import annotations

import os
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Callable
from typing import BinaryIO

from openpilot.starpilot.system.android_auto import apk_identity, play_resolver


class SetupRejected(RuntimeError):
  pass


class AndroidAutoSetup:
  """Bounded upload and status owner for authenticated Galaxy routes.

  The legacy ``parked`` callback and status field report the shared connectivity
  authority for pairing and configuration, including effective offroad with ignition on.
  Package uploads, imports, and removal require only a valid session, in either road state.
  """

  def __init__(self, *, parked: Callable[[], bool], enabled: Callable[[], bool],
               session_valid: Callable[[tuple], bool], import_job: apk_identity.ImportJob | None = None,
               identity_status: Callable[[], dict] = apk_identity.identity_status,
               bluetooth_enabled: Callable[[], bool] = lambda: False,
               install_ready: Callable[[], bool] = lambda: False,
               service_ready: Callable[[], bool] = lambda: False,
               set_enabled: Callable[[bool], None] | None = None,
               enable_bluetooth: Callable[[tuple], None] | None = None, play_install=None):
    self.parked, self.enabled, self.session_valid = parked, enabled, session_valid
    self.bluetooth_enabled = bluetooth_enabled
    self.install_ready, self.service_ready, self.set_enabled_value = install_ready, service_ready, set_enabled
    self.enable_bluetooth_value = enable_bluetooth
    self.play_install = play_install
    self.job = import_job or apk_identity.ImportJob()
    self.identity_status = identity_status
    self.token_store = self.job.token_store if isinstance(self.job, apk_identity.ImportJob) else play_resolver.TokenStore()
    self._upload_lock = threading.Lock()
    self._refresh_after = 0.0

  def _require_session(self, session: tuple) -> None:
    if not session or not self.session_valid(session):
      raise SetupRejected('Galaxy session expired; sign in again')

  def status(self, session: tuple) -> dict:
    self._require_session(session)
    ident = self.identity_status()
    return {
      'enabled': self.enabled(), 'bluetoothEnabled': self.bluetooth_enabled(), 'parked': self.parked(),
      'installReady': self.install_ready(), 'serviceReady': self.service_ready(),
      'identity': {key: ident[key] for key in ('installed', 'expires', 'days_left', 'warning', 'message', 'expired', 'error') if key in ident},
      'import': self.job.status(),
      'googlePlay': {'available': play_resolver.BINARY.is_file(), 'remembered': self.token_store.exists(),
                     **({'package': self.play_install.status()} if self.play_install is not None else {})},
      'maxUploadBytes': apk_identity.MAX_FILE_BYTES,
      'wiredAvailable': False,
      'steps': [
        'The comma acts as the Android Auto phone; the car is the receiver.',
        'Enable Android Auto and upload your own Android Auto APK, XAPK, or APKM on-road or off-road.',
        'Wait for on-device certificate/key verification; replace it before expiry.',
        'In offroad mode or Park, pair the car over Bluetooth. The car then gives the comma its Wi-Fi access point.',
        'Start wireless projection after the car is selected; wired USB remains unavailable.',
      ],
    }

  def enable(self, session: tuple, value: bool, *, enable_bluetooth: bool = False) -> dict:
    if type(value) is not bool or type(enable_bluetooth) is not bool or not session or not self.session_valid(session):
      raise SetupRejected('Galaxy session expired; sign in again')
    if self.set_enabled_value is None:
      raise SetupRejected('Android Auto controls are unavailable in this build')
    if value and not self.install_ready():
      raise SetupRejected('Install the Android Auto display and encoder before enabling')
    if not self.session_valid(session):
      raise SetupRejected('Galaxy session or setup state changed')
    if value and not self.bluetooth_enabled():
      if not enable_bluetooth:
        raise SetupRejected('Android Auto requires Bluetooth. Enable Bluetooth and turn on Android Auto, or cancel.')
      if self.enable_bluetooth_value is None:
        raise SetupRejected('Bluetooth controls are unavailable in this build')
      self.enable_bluetooth_value(session)
      self._require_session(session)
      if not self.bluetooth_enabled():
        raise SetupRejected('Bluetooth could not be enabled; Android Auto was not turned on')
    self._require_session(session)
    self.set_enabled_value(value)
    if not self.session_valid(session):
      raise SetupRejected('Galaxy session expired; sign in again')
    return self.status(session)

  def upload(self, session: tuple, source: BinaryIO, length: int) -> dict:
    self._require_session(session)
    if type(length) is not int or not 0 < length <= apk_identity.MAX_FILE_BYTES:
      raise SetupRejected('Invalid Android Auto package size')
    if not self._upload_lock.acquire(blocking=False):
      raise SetupRejected('Another Android Auto upload is running')
    path: Path | None = None
    started = False
    try:
      if self.job.busy():
        raise SetupRejected('An Android Auto import is running')
      work_dir = self.job.work_dir
      work_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
      fd, name = tempfile.mkstemp(prefix='galaxy-upload-', suffix='.bin', dir=work_dir)
      path = Path(name)
      with os.fdopen(fd, 'wb') as out:
        remaining = length
        while remaining:
          self._require_session(session)
          chunk = source.read(min(1024 * 1024, remaining))
          if not chunk:
            raise SetupRejected('Android Auto package upload ended early')
          if len(chunk) > remaining:
            raise SetupRejected('Android Auto package exceeds declared size')
          out.write(chunk)
          remaining -= len(chunk)
        out.flush()
        os.fsync(out.fileno())
      self._require_session(session)
      self.job.start(path=path, enabled=lambda: self.session_valid(session))
      started = True
      return self.status(session)
    finally:
      if path is not None and not started:
        path.unlink(missing_ok=True)
      self._upload_lock.release()

  def start_google_import(self, session: tuple, *, email: str, token: str, remember: bool = False) -> dict:
    self._require_session(session)
    if type(remember) is not bool:
      raise SetupRejected('Remember must be a boolean')
    play_resolver.validate_credentials(email, token)
    if not self._upload_lock.acquire(blocking=False):
      raise SetupRejected('Another Android Auto upload is running')
    try:
      self._require_session(session)
      if self.job.busy():
        raise SetupRejected('An Android Auto import is running')
      self.job.start_google_import(email=email, save_token=remember,
                                   **({'oauth_token': token} if token.startswith('oauth2_4/') else {'aas_token': token}),
                                   enabled=lambda: self.session_valid(session))
      self._refresh_after = time.monotonic() + 86400
    finally:
      self._upload_lock.release()
    return self.status(session)

  def forget_google(self, session: tuple) -> dict:
    self._require_session(session)
    with self._upload_lock:
      self._require_session(session)
      if self.job.busy():
        raise SetupRejected('Wait for the current import before forgetting Google sign-in')
      self.token_store.forget()
    return self.status(session)

  def maintain(self, now: float | None = None) -> None:
    """Called by Galaxy housekeeping; at most one refresh per day, only offroad.

    Uses the same job and admission lock as manual imports. Explicitly saved
    credentials authorize renewal without the user signing in again. No account secrets
    or signed links enter the HTTP status or logs.
    """
    now = time.monotonic() if now is None else now
    if now < self._refresh_after or not self._upload_lock.acquire(blocking=False):
      return
    try:
      self._refresh_after = now + 60
      if self.job.busy() or not self.token_store.exists() or not self.enabled() or not self.parked():
        return
      ident = self.identity_status()
      expires = ident.get('expires')
      if not expires or (datetime.fromisoformat(expires) - datetime.now(UTC)).total_seconds() > 14 * 86400:
        return
      self._refresh_after = now + 86400
      credentials = self.token_store.load()
      try:
        self.job.start_google_import(email=credentials['email'], aas_token=credentials['token'], save_token=True,
                                     enabled=lambda: self.enabled() and self.parked() and self.token_store.exists())
      finally:
        credentials.clear()
    except (OSError, ValueError, TypeError, RuntimeError):
      # Malformed/revoked credentials must not crash Galaxy or cause retry storms.
      self._refresh_after = now + 86400
    finally:
      self._upload_lock.release()

  def remove(self, session: tuple, *, disconnect: Callable[[], None] | None = None) -> dict:
    self._require_session(session)
    with self._upload_lock:
      self._require_session(session)
      if self.job.busy():
        raise SetupRejected('An Android Auto import is running')
      if disconnect is not None:
        disconnect()
      self._require_session(session)
      self.token_store.forget()
      apk_identity.remove_identity()
    return self.status(session)
