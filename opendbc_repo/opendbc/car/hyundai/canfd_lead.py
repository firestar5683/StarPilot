"""Stateless CANFD lead selection; observations carry owner-qualified BOOTTIME receipts."""
from dataclasses import dataclass
import math

CAMERA_MAX_AGE_NS = 300_000_000
MIN_DISTANCE = 0.1


@dataclass(frozen=True)
class CANFDLeadObservation:
  visible: bool
  distance: float
  relative_speed: float
  producer_ns: int


@dataclass(frozen=True)
class CANFDLeadSelection:
  visible: bool
  distance: float
  relative_speed: float


ABSENT = CANFDLeadSelection(False, 0., 0.)


def _current(observation: CANFDLeadObservation | None, observed_ns: int,
             epoch_floor_ns: int) -> bool:
  return (observation is not None and type(observation.producer_ns) is int and
          epoch_floor_ns < observation.producer_ns <= observed_ns and
          math.isfinite(observation.distance) and math.isfinite(observation.relative_speed))


def _selection(observation: CANFDLeadObservation) -> CANFDLeadSelection:
  return CANFDLeadSelection(True, min(max(observation.distance, 0.), 204.7),
                           min(max(observation.relative_speed, -16.4), 34.7))


def select_lead(radar: CANFDLeadObservation | None, camera: CANFDLeadObservation | None, *,
                hud_visible: bool, observed_ns: int, epoch_floor_ns: int) -> CANFDLeadSelection:
  """Radar freshness is qualified by transport; camera integrity by its parser owner.

  Owner supplies one BOOTTIME domain and epoch floor. Camera age is bounded here;
  no G90 hysteresis or additional radar freshness policy is introduced.
  """
  if (type(observed_ns) is not int or type(epoch_floor_ns) is not int or
      epoch_floor_ns < 0 or observed_ns <= epoch_floor_ns):
    return ABSENT
  radar_current = _current(radar, observed_ns, epoch_floor_ns)
  radar_visible = radar_current and radar.visible
  if radar_visible and radar.distance > MIN_DISTANCE:
    return _selection(radar)
  if (_current(camera, observed_ns, epoch_floor_ns) and camera.visible and
      camera.distance > MIN_DISTANCE and observed_ns-camera.producer_ns <= CAMERA_MAX_AGE_NS):
    return _selection(camera)
  if radar_visible or hud_visible:
    return CANFDLeadSelection(True, 20., 0.)
  return ABSENT
