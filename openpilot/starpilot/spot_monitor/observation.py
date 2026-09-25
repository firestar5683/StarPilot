"""Fail-closed, display-only reader for the versioned V-ASM camera observation."""

from dataclasses import dataclass
import math
import re

from openpilot.starpilot.spot_monitor.inference import MODEL_SHA256


CAMERA_ADMISSION_NS = 500_000_000
WARNING_HOLD_NS = 3_000_000_000
CLOCK_OFFSET_TOLERANCE_NS = 5_000_000
SESSION = re.compile(r"[0-9a-f]{32}\Z")
FINGERPRINT = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class CameraSide:
  status: str = "unknown"
  confidence: float = 0.0
  warning: bool = False
  frame_id: int = 0
  eof_boot_ns: int = 0
  observed_mono_ns: int = 0
  valid_until_boot_ns: int = 0


@dataclass(frozen=True)
class VisualWarning:
  display_left: CameraSide = CameraSide()
  display_right: CameraSide = CameraSide()
  session_id: str = ""
  sequence: int = 0
  observed_mono_ns: int = 0


def _uint(value: object) -> bool:
  return type(value) is int and 0 <= value <= 0xffffffffffffffff


def _side(value, *, event_frame_id: int, event_eof_boot_ns: int,
          event_observed_mono_ns: int, event_clock_offset_ns: int,
          now_boot_ns: int) -> CameraSide:
  status = str(value.status)
  if status == "unknown":
    if value.warning or value.confidence != 0:
      raise ValueError("Unknown camera side carries warning")
    return CameraSide()
  if status not in ("clear", "warning") or bool(value.warning) != (status == "warning"):
    raise ValueError("Contradictory camera side status")
  confidence = float(value.confidence)
  frame_id = int(value.sourceFrameId)
  eof = int(value.sourceFrameEofBootTime)
  observed = int(value.sourceObservedMonoTime)
  expires = int(value.validUntilBootTime)
  if not math.isfinite(confidence) or not 0 <= confidence <= 1 or \
     not (0 < eof <= event_eof_boot_ns and 0 < observed <= event_observed_mono_ns) or \
     frame_id > event_frame_id or expires != eof + WARNING_HOLD_NS:
    raise ValueError("Invalid camera side source or expiry")
  # The side stamp is the original camera EOF converted to MONOTONIC at
  # admission. Later opposite-side publications cannot mint a new side age.
  if abs((eof - observed) - event_clock_offset_ns) > CLOCK_OFFSET_TOLERANCE_NS:
    raise ValueError("Camera side clock pair changed")
  if now_boot_ns > expires:
    return CameraSide()
  return CameraSide(status, confidence, bool(value.warning), frame_id, eof, observed, expires)


class ObservationReader:
  """One high-water per process session; old camera samples never renew a hold."""

  def __init__(self) -> None:
    self._session = ""
    self._sequence = 0
    self._observed_mono_ns = 0
    self._frame_id = -1
    self._frame_eof_boot_ns = 0
    self._sides = (CameraSide(), CameraSide())
    self._retired: list[str] = []
    self._clock_offset_ns: int | None = None
    self._post_resume_floor_ns = 0
    self._last_now_mono_ns = 0
    self._last_now_boot_ns = 0
    self._settings_fingerprint = ""
    self.current = VisualWarning()

  def _clear(self) -> None:
    self.current = VisualWarning()
    self._sides = (CameraSide(), CameraSide())

  def current_at(self, *, now_mono_ns: int, now_boot_ns: int,
                 settings_fingerprint: str) -> VisualWarning:
    """Recheck an already read warning without requiring another IPC packet."""
    if not _uint(now_mono_ns) or not _uint(now_boot_ns) or not \
       isinstance(settings_fingerprint, str) or FINGERPRINT.fullmatch(settings_fingerprint) is None:
      self._clear()
      return self.current
    if now_mono_ns < self._last_now_mono_ns or now_boot_ns < self._last_now_boot_ns:
      self._post_resume_floor_ns = max(self._post_resume_floor_ns, self._last_now_mono_ns)
      self._clear()
      return self.current
    self._last_now_mono_ns, self._last_now_boot_ns = now_mono_ns, now_boot_ns
    offset = now_boot_ns - now_mono_ns
    if self._clock_offset_ns is not None and abs(offset - self._clock_offset_ns) > CLOCK_OFFSET_TOLERANCE_NS:
      self._clock_offset_ns = offset
      self._post_resume_floor_ns = max(self._post_resume_floor_ns, now_mono_ns)
      self._clear()
      return self.current
    self._clock_offset_ns = offset
    if self.current.session_id and self._settings_fingerprint != settings_fingerprint:
      self._clear()
      return self.current
    if self.current.session_id:
      left, right = (side if now_boot_ns <= side.valid_until_boot_ns else CameraSide() for side in self._sides)
      self.current = VisualWarning(left, right, self._session, self._sequence, self._observed_mono_ns)
    return self.current

  def read(self, event, *, now_mono_ns: int, now_boot_ns: int,
           settings_fingerprint: str) -> VisualWarning:
    self.current_at(now_mono_ns=now_mono_ns, now_boot_ns=now_boot_ns,
                    settings_fingerprint=settings_fingerprint)
    if not _uint(now_mono_ns) or not _uint(now_boot_ns) or \
       type(settings_fingerprint) is not str or FINGERPRINT.fullmatch(settings_fingerprint) is None:
      return self.current
    offset = now_boot_ns - now_mono_ns
    try:
      if event.which() != "spotMonitorState":
        return self.current
      wire = event.spotMonitorState.observation
      if int(wire.version) != 1:  # Old @136 curvature-only logs have version 0.
        return self.current
      session = str(wire.producerSessionId)
      sequence = int(wire.sequence)
      observed_mono = int(wire.observedMonoTime)
      if SESSION.fullmatch(session) is None or observed_mono <= self._post_resume_floor_ns:
        self._clear()
        return self.current
      # Producer reset envelopes use a fresh UUID, sequence zero and invalid
      # Event. Accept only a current, source-stamped reset, retiring the old
      # session so delayed old valid packets cannot re-arm a visual warning.
      if sequence == 0 and not event.valid:
        if event.logMonoTime != observed_mono or observed_mono > now_mono_ns or \
           now_mono_ns - observed_mono > CAMERA_ADMISSION_NS:
          self._clear()
          return self.current
        if session != self._session and session not in self._retired and observed_mono > self._observed_mono_ns:
          if self._session:
            self._retired.append(self._session)
            self._retired = self._retired[-16:]
          self._session, self._sequence, self._observed_mono_ns = session, 0, observed_mono
          self._frame_id, self._frame_eof_boot_ns = -1, 0
        self._clear()
        return self.current
      if sequence < 1:
        self._clear()
        return self.current
      if session in self._retired or \
         (session == self._session and sequence <= self._sequence) or \
         (session != self._session and observed_mono <= self._observed_mono_ns):
        return self.current  # Older packets cannot clear or renew a newer state.
      if event.logMonoTime != observed_mono or not event.valid:
        self._clear()
        return self.current
      observed_boot = int(wire.observedBootTime)
      eof = int(wire.sourceFrameEofBootTime)
      frame_id = int(wire.sourceFrameId)
      expires = int(wire.validUntilBootTime)
      if str(wire.modelSha256) != MODEL_SHA256 or str(wire.settingsFingerprint) != settings_fingerprint or \
         not (0 < observed_mono <= now_mono_ns and now_mono_ns - observed_mono <= CAMERA_ADMISSION_NS) or \
         not (0 < eof <= observed_boot <= now_boot_ns and now_boot_ns - eof <= CAMERA_ADMISSION_NS) or \
         expires != eof + CAMERA_ADMISSION_NS or now_boot_ns > expires or \
         abs((observed_boot - observed_mono) - offset) > CLOCK_OFFSET_TOLERANCE_NS:
        self._clear()
        return self.current
      if session == self._session and (frame_id <= self._frame_id or eof <= self._frame_eof_boot_ns):
        return self.current
      left = _side(wire.left, event_frame_id=frame_id, event_eof_boot_ns=eof,
                   event_observed_mono_ns=observed_mono,
                   event_clock_offset_ns=observed_boot - observed_mono, now_boot_ns=now_boot_ns)
      right = _side(wire.right, event_frame_id=frame_id, event_eof_boot_ns=eof,
                    event_observed_mono_ns=observed_mono,
                    event_clock_offset_ns=observed_boot - observed_mono, now_boot_ns=now_boot_ns)
      if session == self._session:
        for before, after in zip(self._sides, (left, right), strict=True):
          if before.status != "unknown" and after.status != "unknown" and \
             (after.frame_id < before.frame_id or
              (after.frame_id == before.frame_id and after != before) or
              after.eof_boot_ns < before.eof_boot_ns):
            raise ValueError("Replayed or rewritten camera side")
      elif self._session:
        self._retired.append(self._session)
        self._retired = self._retired[-16:]
      self._session, self._sequence, self._observed_mono_ns = session, sequence, observed_mono
      self._frame_id, self._frame_eof_boot_ns = frame_id, eof
      self._sides = (left, right)
      self._settings_fingerprint = settings_fingerprint
      self.current = VisualWarning(left, right, session, sequence, observed_mono)
    except (AttributeError, OverflowError, TypeError, ValueError):
      self._clear()
    return self.current
