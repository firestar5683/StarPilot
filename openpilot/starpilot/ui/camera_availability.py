"""Publish already-observed native camera frames without UI-thread file I/O."""

import threading

from openpilot.starpilot.galaxy.camera_request import boot_ns, mark_frame


class CameraAvailability:
  def __init__(self, *, clock=boot_ns, write=mark_frame):
    self.clock, self.write = clock, write
    self.last_frame_ns = None
    self.last_queued_ns = None
    self.pending = None
    self.lock = threading.Lock()
    self.changed = threading.Event()
    self.stopped = False
    self.worker = threading.Thread(target=self._run, name="camera-availability", daemon=True)
    self.worker.start()

  def observe(self):
    now = self.clock()
    self.last_frame_ns = now
    if self.last_queued_ns is not None and 0 <= now - self.last_queued_ns < 1_000_000_000:
      return
    self.last_queued_ns = now
    with self.lock:
      if not self.stopped:
        self.pending = now
        self.changed.set()

  def available(self):
    return self.last_frame_ns is not None and 0 <= self.clock() - self.last_frame_ns <= 500_000_000

  def _run(self):
    while True:
      self.changed.wait()
      with self.lock:
        if self.stopped:
          return
        stamp, self.pending = self.pending, None
        self.changed.clear()
      if stamp is not None:
        try:
          self.write(clock=lambda stamp=stamp: stamp)
        except (OSError, ValueError):
          pass

  def close(self):
    with self.lock:
      self.stopped = True
      self.pending = None
      self.changed.set()
    self.worker.join(timeout=.1)
