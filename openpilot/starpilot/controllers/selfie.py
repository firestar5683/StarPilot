import threading
import time

from openpilot.starpilot.conditional_mode.ui_action import fresh_service
from openpilot.starpilot.controllers.wheel_actions import cp_fingerprint, eligible
from openpilot.starpilot.galaxy.camera_snapshot import CameraSnapshot, SnapshotUnavailable
from openpilot.starpilot.sentry_mode.storage import EventStore, StorageUnavailable


def authority(sm, cp, *, drive_id, fingerprint, now_ns):
  try:
    return bool(eligible(cp) and cp_fingerprint(cp) == fingerprint and
                fresh_service(sm, 'deviceState', drive_id, now_ns, 1_000_000_000) and
                sm['deviceState'].started and int(sm['deviceState'].startedMonoTime) == drive_id and
                fresh_service(sm, 'carState', drive_id, now_ns) and
                sm['carState'].canValid and not sm['carState'].canTimeout)
  except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
    return False


class SelfieCapture:
  def __init__(self, *, camera=None, store=None, clock=time.monotonic_ns):
    self.camera = camera if camera is not None else CameraSnapshot()
    self.store = store if store is not None else EventStore()
    self.clock = clock
    self.lock = threading.Lock()
    self.last_result = None
    self.worker = None

  @property
  def busy(self):
    return self.lock.locked()

  def submit(self, permitted):
    if not permitted() or not self.lock.acquire(blocking=False):
      return False
    self.last_result = None
    try:
      self.worker = threading.Thread(target=self._capture, args=(permitted,), daemon=True)
      self.worker.start()
    except RuntimeError:
      self.lock.release()
      return False
    return True

  def _capture(self, permitted):
    try:
      image = self.camera.capture('cabin', permitted=permitted)
      if not permitted():
        return
      receipt = self.store.record('selfie', self.clock(), permitted=permitted, images={'cabin': image})
      self.last_result = receipt
    except (SnapshotUnavailable, StorageUnavailable, OSError, ValueError):
      self.last_result = None
    finally:
      self.lock.release()
