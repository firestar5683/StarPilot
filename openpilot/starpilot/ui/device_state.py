"""Supplied Device panel data and request-only input for the large UI."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from openpilot.starpilot.galaxy.access import AccessStatus


class DeviceRequest(StrEnum):
  # Open the pairing/management entry; this never pairs or unpairs a device.
  OPEN_GALAXY = "open_galaxy"
  PREVIEW_DRIVER_CAMERA = "preview_driver_camera"
  RESET_DRIVER_MONITORING = "reset_driver_monitoring"
  RESET_CALIBRATION = "reset_calibration"


@dataclass(frozen=True)
class DeviceAction:
  request: DeviceRequest


@dataclass(frozen=True)
class DeviceState:
  dongle_id: str = "N/A"
  serial: str = "N/A"
  galaxy_paired: bool | None = False
  galaxy_configured: bool | None = None
  galaxy_status: AccessStatus = AccessStatus.UNCONFIGURED
  galaxy_local_only: bool = False
  offroad: bool = True
  available_actions: frozenset[DeviceRequest] = frozenset(DeviceRequest)


BUTTON_ROWS = (
  (DeviceRequest.OPEN_GALAXY, 2),
  (DeviceRequest.PREVIEW_DRIVER_CAMERA, 3),
  (DeviceRequest.RESET_DRIVER_MONITORING, 4),
  (DeviceRequest.RESET_CALIBRATION, 5),
)


def button_rect(request: DeviceRequest) -> tuple[int, int, int, int]:
  index = dict(BUTTON_ROWS)[request]
  return 1860, 50 + index * 171 + 35, 250, 100


def request_enabled(request: DeviceRequest, state: DeviceState) -> bool:
  return request in state.available_actions and state.offroad


class DeviceInput:
  """Single pointer hit testing for the captured viewport; no device operation."""

  def __init__(self, emit: Callable[[DeviceAction], None]):
    self.emit = emit
    self._pressed: tuple[float, float, DeviceRequest, AccessStatus | None] | None = None

  @staticmethod
  def _target(x: float, y: float, state: DeviceState) -> DeviceRequest | None:
    if not (550 <= x < 2110 and 50 <= y < 1030):
      return None
    for request, _ in BUTTON_ROWS:
      rx, ry, width, height = button_rect(request)
      if rx <= x < rx + width and ry <= y < ry + height and request_enabled(request, state):
        return request
    return None

  def press(self, x: float, y: float, state: DeviceState) -> None:
    target = self._target(x, y, state)
    self._pressed = (x, y, target, state.galaxy_status if target == DeviceRequest.OPEN_GALAXY else None) if target is not None else None

  def move(self, x: float, y: float, state: DeviceState) -> None:
    if self._pressed is not None:
      _, _, target, status = self._pressed
      if (self._target(x, y, state) != target or
          (target == DeviceRequest.OPEN_GALAXY and state.galaxy_status != status)):
        self.cancel()

  def release(self, x: float, y: float, state: DeviceState) -> None:
    self.move(x, y, state)
    if self._pressed is not None:
      self.emit(DeviceAction(self._pressed[2]))
    self.cancel()

  def cancel(self) -> None:
    self._pressed = None
