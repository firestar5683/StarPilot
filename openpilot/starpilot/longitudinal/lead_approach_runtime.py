"""Drive-scoped saved opt-in for the approaching-lead following buffer."""

import hashlib

from openpilot.starpilot.longitudinal.lead_approach import LeadApproachKey
from openpilot.starpilot.saved_source import read_saved


KEY = "LeadApproachBuffer"
SAFE_MODE_KEY = "SafeMode"


def eligible_cp(cp) -> tuple[str, str, str, int, bool] | None:
  try:
    fingerprint, brand, vin = cp.carFingerprint, cp.brand, cp.carVin
    if (type(fingerprint) is not str or not fingerprint or type(brand) is not str or not brand or type(vin) is not str or
        cp.openpilotLongitudinalControl is not True or cp.notCar is not False or
        cp.passive is not False or cp.dashcamOnly is not False):
      return None
    return fingerprint, brand, vin, int(cp.flags), bool(cp.pcmCruise)
  except (AttributeError, TypeError, ValueError, OverflowError):
    return None


class LeadApproachPreferences:
  REFRESH_NS = 1_000_000_000
  MAX_AGE_NS = 2_000_000_000

  def __init__(self, params):
    self.params = params
    self.key: LeadApproachKey | None = None
    self.identity: tuple[str, str, str, int, bool] | None = None
    self.drive_id = 0
    self.last_sample_ns = -1
    self.last_attempt_ns = -self.REFRESH_NS
    self.last_success_ns = -1

  def _clear(self):
    self.key = None
    self.last_success_ns = -1
    self.last_attempt_ns = -self.REFRESH_NS

  def sample(self, cp, now_ns: int, drive_id: int) -> LeadApproachKey | None:
    if type(now_ns) is not int or type(drive_id) is not int or not 0 < drive_id <= now_ns:
      self._clear()
      self.identity = None
      self.drive_id = 0
      self.last_sample_ns = -1
      return None
    identity = eligible_cp(cp)
    if identity is None:
      self._clear()
      self.identity = None
      self.drive_id = 0
      self.last_sample_ns = -1
      return None
    if identity != self.identity or drive_id != self.drive_id or now_ns < self.last_sample_ns:
      self._clear()
    self.identity, self.drive_id, self.last_sample_ns = identity, drive_id, now_ns
    if now_ns - self.last_attempt_ns >= self.REFRESH_NS:
      self.last_attempt_ns = now_ns
      try:
        saved, readable = read_saved(self.params, KEY, 8)
        safe, safe_readable = read_saved(self.params, SAFE_MODE_KEY, 8) if readable and saved == b"1" else (None, False)
      except (OSError, RuntimeError, TypeError, ValueError):
        saved, readable, safe, safe_readable = None, False, None, False
      if readable and saved == b"1" and safe_readable and safe in (None, b"0"):
        fingerprint = hashlib.sha256(b"\0".join((b"lead-approach-v1", KEY.encode(), saved,
                                                   *(str(part).encode() for part in identity), str(drive_id).encode()))).hexdigest()
        self.key = LeadApproachKey(fingerprint, drive_id)
        self.last_success_ns = now_ns
      else:
        self.key = None
        self.last_success_ns = -1
    return self.key if self.last_success_ns > 0 and now_ns - self.last_success_ns <= self.MAX_AGE_NS else None
