from types import SimpleNamespace

from openpilot.selfdrive.car.ev9_cluster_objects import filtered_radar_slots, radar_backed_object


def lead(*, track_id=1, distance=30.0, lateral=0.0, relative_speed=-1.0, status=True, radar=True):
  return SimpleNamespace(status=status, radar=radar, radarTrackId=track_id,
                         dRel=distance, yRel=lateral, vRel=relative_speed)


def test_rejects_vision_only_lead():
  assert radar_backed_object(lead(track_id=-1, radar=False)) is None


def test_alternate_is_default_suppressible():
  slots = filtered_radar_slots(lead(track_id=1), lead(track_id=2), lead(status=False), lead(status=False), False)
  assert slots.primary is not None
  assert slots.alternate is None


def test_duplicate_track_only_occupies_one_slot():
  slots = filtered_radar_slots(lead(track_id=7), lead(track_id=7), lead(track_id=7), lead(status=False), True)
  assert slots.primary is not None
  assert slots.alternate is None
  assert slots.left is None


def test_distinct_radar_alternate_can_be_enabled():
  slots = filtered_radar_slots(lead(track_id=1), lead(track_id=2, distance=42.0),
                               lead(status=False), lead(status=False), True)
  assert slots.alternate is not None
  assert slots.alternate.track_id == 2
