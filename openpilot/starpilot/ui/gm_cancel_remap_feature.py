"""Saved next-drive secondary Cancel input on exact supported pedal-long Bolts."""
import hashlib
from dataclasses import replace
from opendbc.car.gm.cancel_remap import KEY, supported
from openpilot.starpilot.saved_document import commit_exact


class GmCancelRemapFeature:
  def __init__(self, owner):
    self.owner = owner

  def capability(self):
    cp = self.owner.vehicle_params()
    if not supported(cp):
      return None
    reader = cp.as_reader() if hasattr(cp, "as_reader") else cp
    return (str(cp.carFingerprint), hashlib.sha256(reader.as_builder().to_bytes()).hexdigest())

  def rows(self, parked):
    capability = self.capability()
    if capability is None:
      return []
    row = self.owner._bool_row(KEY, "Use Cancel as Secondary Button", parked and self.owner.authority("parked_preferences"),
      "Use the Cancel button assignments in Wheel Controls instead of canceling cruise. Applies next drive.")
    return [replace(row, capability=capability, available=row.available and self.owner._readable(KEY))]

  def apply(self, request):
    capability = self.capability()
    if capability is None or request.capability != capability or request.value not in ("Off", "On"):
      return False
    def authorized():
      return self.owner.authority("parked_preferences") and self.capability() == capability
    result = commit_exact(self.owner.params, key=KEY, max_bytes=8, expected=request.expected,
      raw=b"1" if request.value == "On" else b"0", authorized=authorized, temp_prefix=".gm-cancel-")
    return result.committed and result.verified
