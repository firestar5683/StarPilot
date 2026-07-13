from types import SimpleNamespace

from openpilot.selfdrive.car.ev9_cluster_objects import Ev9ClusterObjectTracker, default_enabled_param, filtered_radar_slots, \
                                                         radar_backed_object


def lead(*, track_id=1, distance=30.0, lateral=0.0, relative_speed=-1.0, status=True, radar=True):
  return SimpleNamespace(status=status, radar=radar, radarTrackId=track_id,
                         dRel=distance, yRel=lateral, vRel=relative_speed)


def point(track_id=1, distance=30.0, lateral=0.0, relative_speed=-1.0, measured=True):
  return SimpleNamespace(trackId=track_id, dRel=distance, yRel=lateral,
                         vRel=relative_speed, measured=measured)


def acquire(tracker, points, samples=3, **kwargs):
  slots = None
  for _ in range(samples):
    slots = tracker.update(points, **kwargs)
  return slots


class FakeParams:
  def __init__(self, value):
    self.value = value

  def get(self, key):
    return self.value


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


def test_tracker_requires_acquisition_confirmation():
  tracker = Ev9ClusterObjectTracker()
  assert tracker.update([point()]).primary is None
  assert tracker.update([point()]).primary is None
  assert tracker.update([point()]).primary is not None


def test_tracker_holds_short_dropout_without_flicker():
  tracker = Ev9ClusterObjectTracker()
  acquire(tracker, [point(track_id=4)])
  for _ in range(tracker.DROPOUT_HOLD_SAMPLES):
    assert tracker.update([]).primary is not None
  assert tracker.update([]).primary is None


def test_tracker_smooths_distance():
  tracker = Ev9ClusterObjectTracker()
  acquire(tracker, [point(distance=20.0)])
  slots = tracker.update([point(distance=40.0)])
  assert slots.primary is not None
  assert 20.0 < slots.primary.distance < 40.0


def test_tracker_assigns_each_track_to_only_one_slot():
  tracker = Ev9ClusterObjectTracker()
  slots = acquire(tracker, [point(track_id=9, lateral=2.5)])
  assert slots.left is not None
  assert slots.primary is None

  for _ in range(6):
    slots = tracker.update([point(track_id=9, lateral=0.0)])
    assert not (slots.primary is not None and slots.left is not None)
  assert slots.primary is not None
  assert slots.left is None


def test_tracker_alternate_is_distinct_and_opt_in():
  tracker = Ev9ClusterObjectTracker()
  objects = [point(track_id=1, distance=20.0), point(track_id=2, distance=35.0)]
  slots = acquire(tracker, objects)
  assert slots.primary is not None
  assert slots.alternate is None
  slots = tracker.update(objects, alternate_enabled=True)
  assert slots.alternate is not None
  assert slots.primary.track_id != slots.alternate.track_id


def test_tracker_keeps_slot_identity_when_another_track_appears():
  tracker = Ev9ClusterObjectTracker()
  slots = acquire(tracker, [point(track_id=1, distance=30.0)])
  assert slots.primary.track_id == 1
  slots = acquire(tracker, [point(track_id=1, distance=30.0), point(track_id=2, distance=20.0)])
  assert slots.primary.track_id == 1


def test_quality_allowlist_rejects_garage_track_and_accepts_qualified_track():
  tracker = Ev9ClusterObjectTracker()
  garage_track = point(track_id=7, distance=7.1, lateral=1.9, relative_speed=0.0)
  assert acquire(tracker, [garage_track], qualified_track_ids=set()).primary is None
  assert acquire(tracker, [garage_track], qualified_track_ids={7}).left is not None


def test_quality_allowlist_removes_deleted_or_stale_track_immediately():
  tracker = Ev9ClusterObjectTracker()
  obj = point(track_id=9)
  assert acquire(tracker, [obj], qualified_track_ids={9}).primary is not None
  assert tracker.update([obj], qualified_track_ids=set()).primary is None
  assert 9 not in tracker.tracks
  # Re-qualification starts a fresh acquisition instead of reviving stale UI state.
  assert tracker.update([obj], qualified_track_ids={9}).primary is None


def test_quality_filter_disabled_preserves_legacy_tracker_behavior():
  tracker = Ev9ClusterObjectTracker()
  garage_track = point(track_id=11, distance=4.5, lateral=-2.0, relative_speed=0.0)
  assert acquire(tracker, [garage_track], qualified_track_ids=None).right is not None


def test_fused_slot_quality_allowlist_is_display_only():
  primary = lead(track_id=1)
  left = lead(track_id=2, lateral=2.5)
  slots = filtered_radar_slots(primary, lead(status=False), left, lead(status=False), False, {1})
  assert slots.primary is not None
  assert slots.left is None


def test_quality_filter_param_defaults_on_when_missing_and_honors_explicit_off():
  assert default_enabled_param(FakeParams(None), "KiaEv9RadarQualityFilterEnabled")
  assert default_enabled_param(FakeParams(b"1"), "KiaEv9RadarQualityFilterEnabled")
  assert not default_enabled_param(FakeParams(b"0"), "KiaEv9RadarQualityFilterEnabled")
