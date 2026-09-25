"""Supplied Software viewport data and inert, typed input requests."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class DownloadLabel(StrEnum):
  CHECK = "CHECK"
  DOWNLOAD = "DOWNLOAD"


class SoftwareRequest(StrEnum):
  SET_AUTOMATIC_UPDATES = "set_automatic_updates"
  CHECK_FOR_UPDATES = "check_for_updates"
  DOWNLOAD_UPDATE = "download_update"
  OPEN_BRANCH_CHOOSER = "open_branch_chooser"
  OPEN_UNINSTALL_CONFIRMATION = "open_uninstall_confirmation"
  OPEN_ERROR_LOG = "open_error_log"


@dataclass(frozen=True)
class SoftwareAction:
  request: SoftwareRequest
  desired_enabled: bool | None = None


@dataclass(frozen=True)
class SoftwareState:
  current_version: str = ""
  automatic_updates: bool | None = True
  download_status: str = "up to date, last checked never"
  download_label: DownloadLabel = DownloadLabel.CHECK
  target_branch: str = ""
  available_actions: frozenset[SoftwareRequest] = frozenset(SoftwareRequest)


BUTTON_ROWS = (
  (SoftwareRequest.CHECK_FOR_UPDATES, 2),
  (SoftwareRequest.OPEN_BRANCH_CHOOSER, 3),
  (SoftwareRequest.OPEN_UNINSTALL_CONFIRMATION, 4),
  (SoftwareRequest.OPEN_ERROR_LOG, 5),
)


def button_rect(row: int) -> tuple[int, int, int, int]:
  return 1860, 50 + row * 171 + 35, 250, 100


TOGGLE_RECT = (1950, 266, 160, 80)


class SoftwareInput:
  """Single-pointer hit testing. The caller decides what any request means."""

  def __init__(self, emit: Callable[[SoftwareAction], None]):
    self.emit = emit
    self._pressed: tuple[float, float, SoftwareRequest, bool | None] | None = None

  @staticmethod
  def _target(x: float, y: float, state: SoftwareState) -> SoftwareRequest | None:
    if not (550 <= x < 2110 and 50 <= y < 1030):
      return None
    tx, ty, tw, th = TOGGLE_RECT
    if tx <= x < tx + tw and ty <= y < ty + th:
      return SoftwareRequest.SET_AUTOMATIC_UPDATES if SoftwareRequest.SET_AUTOMATIC_UPDATES in state.available_actions else None
    for request, row in BUTTON_ROWS:
      bx, by, bw, bh = button_rect(row)
      if bx <= x < bx + bw and by <= y < by + bh:
        if request == SoftwareRequest.CHECK_FOR_UPDATES and state.download_label == DownloadLabel.DOWNLOAD:
          request = SoftwareRequest.DOWNLOAD_UPDATE
        return request if request in state.available_actions else None
    return None

  def press(self, x: float, y: float, state: SoftwareState) -> None:
    target = self._target(x, y, state)
    displayed_toggle = state.automatic_updates if target == SoftwareRequest.SET_AUTOMATIC_UPDATES else None
    self._pressed = (x, y, target, displayed_toggle) if target is not None else None

  def move(self, x: float, y: float, state: SoftwareState) -> None:
    if self._pressed is not None:
      px, py, target, displayed_toggle = self._pressed
      if (abs(x - px) > 5 or abs(y - py) > 5 or self._target(x, y, state) != target or
          (target == SoftwareRequest.SET_AUTOMATIC_UPDATES and state.automatic_updates != displayed_toggle)):
        self.cancel()

  def release(self, x: float, y: float, state: SoftwareState) -> None:
    self.move(x, y, state)
    if self._pressed is not None:
      _, _, request, displayed_toggle = self._pressed
      desired = not displayed_toggle if displayed_toggle is not None else None
      self.emit(SoftwareAction(request, desired))
    self.cancel()

  def cancel(self) -> None:
    self._pressed = None
