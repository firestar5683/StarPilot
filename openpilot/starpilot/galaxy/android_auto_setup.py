"""Galaxy setup owner for a user's own Android Auto package.

The HTTP server must authenticate the caller before invoking this owner. This
module has no routes, device side effects, or credential material on import.
"""
from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from collections.abc import Callable
from typing import BinaryIO

from openpilot.starpilot.system.android_auto import apk_identity


class SetupRejected(RuntimeError):
  pass


class AndroidAutoSetup:
  """Bounded upload and status owner for authenticated Galaxy routes.

  The legacy ``parked`` callback and status field mean setup is admitted by the
  shared connectivity authority, including effective offroad with ignition on.
  """

  def __init__(self, *, parked: Callable[[], bool], enabled: Callable[[], bool],
               session_valid: Callable[[tuple], bool], import_job: apk_identity.ImportJob | None = None,
               identity_status: Callable[[], dict] = apk_identity.identity_status,
               bluetooth_enabled: Callable[[], bool] = lambda: False,
               install_ready: Callable[[], bool] = lambda: False,
               service_ready: Callable[[], bool] = lambda: False,
               set_enabled: Callable[[bool], None] | None = None):
    self.parked, self.enabled, self.session_valid = parked, enabled, session_valid
    self.bluetooth_enabled = bluetooth_enabled
    self.install_ready, self.service_ready, self.set_enabled_value = install_ready, service_ready, set_enabled
    self.job = import_job or apk_identity.ImportJob()
    self.identity_status = identity_status
    self._upload_lock = threading.Lock()

  def _admit(self, session: tuple) -> None:
    if not session or not self.session_valid(session):
      raise SetupRejected('Galaxy session expired; sign in again')
    if not self.parked():
      raise SetupRejected('Use offroad mode or Park before Android Auto setup')
    if not self.enabled():
      raise SetupRejected('Enable experimental Android Auto first')

  def status(self, session: tuple) -> dict:
    if not session or not self.session_valid(session):
      raise SetupRejected('Galaxy session expired; sign in again')
    ident = self.identity_status()
    return {
      'enabled': self.enabled(), 'bluetoothEnabled': self.bluetooth_enabled(), 'parked': self.parked(),
      'installReady': self.install_ready(), 'serviceReady': self.service_ready(),
      'identity': {key: ident[key] for key in ('installed', 'expires', 'days_left', 'warning', 'message', 'expired', 'error') if key in ident},
      'import': self.job.status(),
      'maxUploadBytes': apk_identity.MAX_FILE_BYTES,
      'wiredAvailable': False,
      'steps': [
        'The comma acts as the Android Auto phone; the car is the receiver.',
        'Enable experimental Android Auto and upload your own Android Auto APK, XAPK, or APKM.',
        'Wait for on-device certificate/key verification; replace it before expiry.',
        'In offroad mode or Park, pair the car over Bluetooth. The car then gives the comma its Wi-Fi access point.',
        'Start wireless projection after the car is selected; wired USB remains unavailable.',
      ],
    }

  def enable(self, session: tuple, value: bool) -> dict:
    if type(value) is not bool or not session or not self.session_valid(session):
      raise SetupRejected('Galaxy session expired; sign in again')
    if self.set_enabled_value is None:
      raise SetupRejected('Android Auto controls are unavailable in this build')
    if value and (not self.parked() or not self.install_ready()):
      raise SetupRejected('Use offroad mode or Park and install the Android Auto display and encoder before enabling')
    if not self.session_valid(session) or value and not self.parked():
      raise SetupRejected('Galaxy session or setup state changed')
    self.set_enabled_value(value)
    if not self.session_valid(session):
      raise SetupRejected('Galaxy session expired; sign in again')
    return self.status(session)

  def upload(self, session: tuple, source: BinaryIO, length: int) -> dict:
    self._admit(session)
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
          self._admit(session)
          chunk = source.read(min(1024 * 1024, remaining))
          if not chunk:
            raise SetupRejected('Android Auto package upload ended early')
          if len(chunk) > remaining:
            raise SetupRejected('Android Auto package exceeds declared size')
          out.write(chunk)
          remaining -= len(chunk)
        out.flush()
        os.fsync(out.fileno())
      self._admit(session)
      self.job.start(path=path, enabled=lambda: self.enabled() and self.parked() and self.session_valid(session))
      started = True
      return self.status(session)
    finally:
      if path is not None and not started:
        path.unlink(missing_ok=True)
      self._upload_lock.release()

  def remove(self, session: tuple) -> dict:
    self._admit(session)
    with self._upload_lock:
      self._admit(session)
      if self.job.busy():
        raise SetupRejected('An Android Auto import is running')
      apk_identity.remove_identity()
    return self.status(session)
