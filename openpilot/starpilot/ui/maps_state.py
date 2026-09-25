"""Read-only native view of the single parked offline-map operation owner."""

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
import time

from openpilot.starpilot.ui.feature_settings_state import FeatureRow, FeatureSettingsState


def map_page(status: dict | None) -> FeatureSettingsState:
  if not isinstance(status, dict) or status.get("schemaVersion") != 1:
    rows = (FeatureRow("", "Map manager", "Unavailable", reason="Open Galaxy when the parked map manager is available"),)
  else:
    state = status.get("state")
    if state not in ("idle", "transferring", "validating", "selecting", "completed", "canceled", "failed", "interrupted", "unavailable"):
      return map_page(None)
    generation = status.get("selectedGeneration")
    if not isinstance(generation, str) or generation and (len(generation) != 64 or any(c not in "0123456789abcdef" for c in generation)):
      return map_page(None)
    rows = (FeatureRow("", "Operation", state.replace("_", " ").title()),
            FeatureRow("", "Selected map", generation[:12] + "…" if generation else "None",
                       reason="Selection applies on the next map service start; it does not prove an active map"),)
    if state in ("transferring", "validating", "selecting"):
      completed, total = status.get("completedGroups"), status.get("totalGroups")
      if type(completed) is int and type(total) is int and 0 <= completed <= total:
        rows += (FeatureRow("", "Progress", f"{completed} / {total} groups"),)
    if state in ("failed", "interrupted", "unavailable"):
      rows += (FeatureRow("", "Recovery", "Open Galaxy", reason="Review the parked map operation"),)
  rows += (FeatureRow("", "Manage regions", "Open Galaxy", reason="Parked downloads and cancellation are managed there"),)
  return FeatureSettingsState(title="Offline Maps", subtitle="Selected region and parked operation status.", rows=rows)


def _request_status() -> dict:
  from openpilot.starpilot.maps.operation_owner import request_operation
  response = request_operation({"version": 1, "op": "status"}, timeout_s=0.75)
  if (type(response) is not dict or response.get("version") != 1 or response.get("ok") is not True or
      type(response.get("result")) is not dict):
    raise ValueError("Map owner unavailable")
  return response["result"]


class MapStatusSource:
  """Bounded background socket read: no render-frame I/O or download authority."""

  REFRESH_NS = 3_000_000_000

  def __init__(self, request: Callable[[], dict] = _request_status, clock: Callable[[], int] = time.monotonic_ns):
    self.request = request
    self.clock = clock
    self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="map-status")
    self.pending: Future | None = None
    self.next_read_ns = 0
    self.status: dict | None = None
    self.closed = False

  def snapshot(self) -> FeatureSettingsState:
    if self.closed:
      return map_page(None)
    now = self.clock()
    if self.pending is not None and self.pending.done():
      try:
        self.status = self.pending.result()
      except (OSError, RuntimeError, ValueError):
        self.status = None
      self.pending = None
    if self.pending is None and now >= self.next_read_ns:
      self.pending = self.executor.submit(self.request)
      self.next_read_ns = now + self.REFRESH_NS
    return map_page(self.status)

  def close(self) -> None:
    self.closed = True
    self.executor.shutdown(wait=False, cancel_futures=True)
