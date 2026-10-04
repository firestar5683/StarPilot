"""Drive-scoped process recovery after an established Big publisher stops.

This owner never touches GPU buffers or retained model selection. Small may start
only after the exact failed modeld process has exited.
"""
from dataclasses import dataclass

ARM_SPAN_NS = 1_000_000_000
ARM_MAX_GAP_NS = 1_000_000_000
STALL_NS = 2_000_000_000
CAMERA_MAX_AGE_NS = 200_000_000
INT_GRACE_NS = 500_000_000
KILL_GRACE_NS = 1_000_000_000


@dataclass(frozen=True)
class RecoveryEvidence:
  now_ns: int
  drive_id: int
  identity: tuple[int, int] | None
  alive: bool
  big_receipt: bool
  loaded_ns: int
  model_ns: int
  driving_ns: int
  output_valid: bool
  output_big: bool
  cameras: tuple[tuple[int, int], ...]  # producer timestamp, frameId


class ModelRecoveryOwner:
  def __init__(self):
    self.drive_id = 0
    self.small_only = False
    self.phase = 'monitor'
    self.identity = None
    self.first_output_ns = 0
    self.last_output = (0, 0)
    self.last_progress_ns = 0
    self.last_cameras = ()
    self.camera_progress_since = 0
    self.deadline_ns = 0
    self.armed = False

  def _withdraw(self):
    self.identity = None
    self.first_output_ns = 0
    self.last_output = (0, 0)
    self.last_progress_ns = 0
    self.last_cameras = ()
    self.camera_progress_since = 0
    self.armed = False

  def step(self, e: RecoveryEvidence) -> str | None:
    if self.phase in ('sigint', 'sigkill', 'failed'):
      if not e.alive:
        if self.phase == 'failed' and e.drive_id == self.drive_id:
          return None
        if e.drive_id == self.drive_id and e.drive_id > 0:
          self.phase = 'small'
          return 'small'
        self.__init__()
        self.drive_id = e.drive_id
        return 'exit'
      if e.identity != self.identity:
        self.phase = 'failed'
        return None
      if self.phase != 'failed' and e.now_ns >= self.deadline_ns:
        if self.phase == 'sigint':
          self.phase = 'sigkill'
          self.deadline_ns = e.now_ns + KILL_GRACE_NS
          return 'kill'
        self.phase = 'failed'
        return 'failed'
      return None
    if e.drive_id <= 0:
      self.__init__()
      return None
    if e.drive_id != self.drive_id:
      self.__init__()
      self.drive_id = e.drive_id
    if self.phase != 'monitor' or self.small_only:
      return None
    if (not e.alive or e.identity is None or min(e.identity) <= 0 or not e.big_receipt or
        not self.drive_id <= e.loaded_ns <= e.now_ns):
      self._withdraw()
      return None
    if e.identity != self.identity:
      self._withdraw()
      self.identity = e.identity
    cameras_fresh = (len(e.cameras) == 2 and all(self.drive_id <= t <= e.now_ns and
                     e.now_ns - t <= CAMERA_MAX_AGE_NS and f >= 0 for t, f in e.cameras))
    if not cameras_fresh:
      self.camera_progress_since = 0
      self.last_cameras = ()
      return None
    cameras_advance = bool(self.last_cameras and all(t > pt and f > pf for (t, f), (pt, pf) in zip(e.cameras, self.last_cameras, strict=True)))
    if cameras_advance:
      if not self.camera_progress_since:
        self.camera_progress_since = e.now_ns
    else:
      self.camera_progress_since = 0
    self.last_cameras = e.cameras
    output = (e.model_ns, e.driving_ns)
    valid_output = (e.output_valid and e.output_big and all(e.loaded_ns <= t <= e.now_ns for t in output) and
                    e.now_ns - min(output) <= CAMERA_MAX_AGE_NS)
    if valid_output and all(t > old for t, old in zip(output, self.last_output, strict=True)):
      if not self.armed and self.last_progress_ns and e.now_ns - self.last_progress_ns > ARM_MAX_GAP_NS:
        self.first_output_ns = 0
      if not self.first_output_ns:
        self.first_output_ns = min(output)
      self.last_output = output
      self.last_progress_ns = e.now_ns
      self.armed = min(output) - self.first_output_ns >= ARM_SPAN_NS
      return None
    if (self.armed and self.last_progress_ns and e.now_ns - self.last_progress_ns >= STALL_NS and
        self.camera_progress_since and e.now_ns - self.camera_progress_since >= STALL_NS):
      self.small_only = True
      self.phase = 'sigint'
      self.deadline_ns = e.now_ns + INT_GRACE_NS
      return 'interrupt'
    return None
