"""Current-road Maps projection; source ordering/freshness stays in MapTracker."""
import hashlib
import json

from openpilot.starpilot.speed_limits import acceptance as acc
from openpilot.starpilot.speed_limits import map_source as ms


def copy_frame(road, *, event_valid: bool, event_boot_ns: int) -> ms.MapFrame:
  """Copy a current mapdOut reader without retaining a mutable cereal view."""
  try:
    return ms.MapFrame(event_valid, event_boot_ns, int(road.sampleVersion), str(road.roadStatus),
      str(road.gpsSource), int(road.gpsMonoTime), int(road.computedMonoTime),
      int(road.sourceGeneration), int(road.producerSession), float(road.speedLimit),
      bool(road.tileLoaded), int(road.wayId), str(road.waySelectionType))
  except Exception as error:  # pycapnp lazy reads may raise KjException, not ValueError
    raise ValueError('invalid mapdOut reader') from error


class MapSource:
  """Plannerd's map observation owner; never grants longitudinal authority."""

  def __init__(self):
    self.tracker = ms.MapTracker()

  def reset(self):
    self.tracker.reset()

  def step(self, frame: ms.MapFrame | None, *, received: bool, now_boot_ns: int,
           transport_alive: bool, drive_session: str, car_fingerprint: str) -> acc.Observation:
    evidence = self.tracker.step(frame, received=received, now_boot_ns=now_boot_ns,
                                 transport_alive=transport_alive)
    if evidence.observation.kind is acc.ObservationKind.STALE:
      return evidence.observation
    accepted = self.tracker.diagnostic(now_boot_ns=now_boot_ns).frame
    if (evidence.kind != 'matched_limit_unqualified' or accepted is None or
        accepted.way_selection != 'current' or
        any(type(value) is not str or not 0 < len(value) <= 256 or not value.strip() or
            any(ord(c) < 32 for c in value) for value in (drive_session, car_fingerprint))):
      # Missing speed metadata, coverage/GPS loss and ambiguous/lookahead ways
      # are incomplete evidence, not a new limit or regulatory absence.
      return acc.Observation(acc.ObservationKind.UNKNOWN)
    identity = hashlib.sha256(json.dumps((drive_session, car_fingerprint, accepted.producer_session,
      accepted.generation, accepted.source, accepted.way_id), separators=(',', ':')).encode()).hexdigest()
    return acc.Observation(acc.ObservationKind.VALID, acc.Candidate('map',
      acc.ObservationIdentity(acc.IdentityKind.GEOGRAPHIC, value=identity), accepted.speed_mps))
