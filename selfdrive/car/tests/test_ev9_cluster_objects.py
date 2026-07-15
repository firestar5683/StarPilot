from types import SimpleNamespace

from openpilot.selfdrive.car.ev9_cluster_objects import ClusterObject, ClusterObjectSlots, Ev9ClusterObjectTracker, \
                                                         bsm_gated_side_slots, default_enabled_param, \
                                                         ev9_cluster_display_context_valid, filtered_radar_slots, radar_backed_object, \
                                                         validate_cluster_slots_for_output


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


def test_distinct_radar_alternate_remains_suppressed():
  slots = filtered_radar_slots(lead(track_id=1), lead(track_id=2, distance=42.0),
                               lead(status=False), lead(status=False), True)
  assert slots.alternate is None


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


def test_selected_primary_retains_style_when_promoted_to_side_slot():
  tracker = Ev9ClusterObjectTracker()
  slots = acquire(tracker, [point(track_id=9)], preferred_primary_track_id=9)
  assert slots.primary is not None and slots.primary.selected

  for _ in range(6):
    slots = tracker.update([point(track_id=9, lateral=2.5)], preferred_primary_track_id=9)
  assert slots.primary is None
  assert slots.left is not None and slots.left.selected


def test_tracker_alternate_remains_suppressed():
  tracker = Ev9ClusterObjectTracker()
  objects = [point(track_id=1, distance=20.0), point(track_id=2, distance=35.0)]
  slots = acquire(tracker, objects)
  assert slots.primary is not None
  assert slots.alternate is None
  slots = tracker.update(objects, alternate_enabled=True)
  assert slots.alternate is None


def test_tracker_keeps_slot_identity_when_another_track_appears():
  tracker = Ev9ClusterObjectTracker()
  slots = acquire(tracker, [point(track_id=1, distance=30.0)])
  assert slots.primary.track_id == 1


def test_tracker_hard_clear_discards_confirmed_and_pending_identity():
  tracker = Ev9ClusterObjectTracker()
  slots = acquire(tracker, [point(track_id=1), point(track_id=2, lateral=2.5)])
  assert slots.primary is not None
  assert slots.left is not None

  assert tracker.clear() == type(slots)()
  assert not tracker.tracks
  assert all(track_id == -1 for track_id in tracker.slot_track_ids.values())
  assert tracker.update([point(track_id=1)]).primary is None


def test_tracker_can_require_fused_primary_track():
  tracker = Ev9ClusterObjectTracker()
  objects = [point(track_id=1, distance=20.0), point(track_id=2, distance=35.0)]
  slots = acquire(tracker, objects, require_preferred_primary=True)
  assert slots.primary is None
  slots = tracker.update(objects, preferred_primary_track_id=2, require_preferred_primary=True)
  assert slots.primary is not None
  assert slots.primary.track_id == 2


def test_centered_fused_lead_cannot_duplicate_into_side_slot():
  tracker = Ev9ClusterObjectTracker()
  obj = point(track_id=8, distance=30.0, lateral=2.0)
  slots = acquire(tracker, [obj], preferred_primary_track_id=8, qualified_track_ids={8},
                  side_qualified_track_ids={8}, side_retention_track_ids={8}, v_ego=20.0)
  assert slots.primary is not None
  assert slots.left is None
  assert slots.right is None


def test_bsm_gate_removes_only_unconfirmed_side_slots():
  tracker = Ev9ClusterObjectTracker()
  slots = acquire(tracker, [point(track_id=1), point(track_id=2, lateral=2.5), point(track_id=3, lateral=-2.5)])
  gated = bsm_gated_side_slots(slots, left_blindspot=True, right_blindspot=False)
  assert gated.primary is not None
  assert gated.left is not None
  assert gated.right is None
  assert bsm_gated_side_slots(slots, False, False, gate_enabled=False) == slots
  slots = acquire(tracker, [point(track_id=1, distance=30.0), point(track_id=2, distance=20.0)])
  assert slots.primary.track_id == 1


def test_quality_allowlist_rejects_garage_track_and_accepts_qualified_track():
  tracker = Ev9ClusterObjectTracker()
  garage_track = point(track_id=7, distance=7.1, lateral=1.9, relative_speed=0.0)
  assert acquire(tracker, [garage_track], qualified_track_ids=set(), require_preferred_primary=True).primary is None
  assert acquire(tracker, [garage_track], qualified_track_ids={7}, require_preferred_primary=True).left is not None


def test_quality_allowlist_removes_deleted_or_stale_track_immediately():
  tracker = Ev9ClusterObjectTracker()
  obj = point(track_id=9)
  assert acquire(tracker, [obj], qualified_track_ids={9}).primary is not None
  assert tracker.update([obj], qualified_track_ids=set()).primary is None
  assert 9 not in tracker.tracks
  # Re-qualification starts a fresh acquisition instead of reviving stale UI state.
  assert tracker.update([obj], qualified_track_ids={9}).primary is None


def test_missing_qualified_track_gets_only_bounded_dropout_hold():
  tracker = Ev9ClusterObjectTracker()
  obj = point(track_id=12)
  assert acquire(tracker, [obj], qualified_track_ids={12}).primary is not None
  for _ in range(tracker.DROPOUT_HOLD_SAMPLES):
    assert tracker.update([], qualified_track_ids=set()).primary is not None
  assert tracker.update([], qualified_track_ids=set()).primary is None


def test_quality_filter_disabled_preserves_legacy_tracker_behavior():
  tracker = Ev9ClusterObjectTracker()
  garage_track = point(track_id=11, distance=4.5, lateral=-2.5, relative_speed=0.0)
  assert acquire(tracker, [garage_track], qualified_track_ids=None).right is not None


def test_strict_side_allowlist_does_not_remove_qualified_primary():
  tracker = Ev9ClusterObjectTracker()
  objects = [point(track_id=1, distance=25.0), point(track_id=2, distance=35.0, lateral=2.5)]
  slots = acquire(tracker, objects, qualified_track_ids={1, 2}, side_qualified_track_ids=set())
  assert slots.primary is not None and slots.primary.track_id == 1
  assert slots.left is None


def test_strict_side_allowlist_and_geometry_accept_left_candidate():
  tracker = Ev9ClusterObjectTracker()
  obj = point(track_id=2, distance=35.0, lateral=2.5)
  slots = acquire(tracker, [obj], qualified_track_ids={2}, side_qualified_track_ids={2}, v_ego=20.0)
  assert slots.left is not None and slots.left.track_id == 2


def test_right_side_can_fail_closed_independently():
  tracker = Ev9ClusterObjectTracker()
  obj = point(track_id=3, distance=20.0, lateral=-2.5)
  slots = acquire(tracker, [obj], qualified_track_ids={3}, side_qualified_track_ids={3}, right_enabled=False)
  assert slots.right is None


def test_right_side_requires_deep_entry_then_uses_wider_retention_envelope():
  tracker = Ev9ClusterObjectTracker()
  shallow = point(track_id=3, distance=30.0, lateral=-1.7, relative_speed=0.0)
  assert acquire(tracker, [shallow], qualified_track_ids={3}, side_qualified_track_ids={3},
                 side_retention_track_ids={3}, v_ego=20.0).right is None

  deep = point(track_id=3, distance=30.0, lateral=-3.0, relative_speed=0.0)
  slots = acquire(tracker, [deep], qualified_track_ids={3}, side_qualified_track_ids={3},
                  side_retention_track_ids={3}, v_ego=20.0)
  assert slots.right is not None

  deep_left = point(track_id=6, distance=30.0, lateral=3.0, relative_speed=0.0)
  left_tracker = Ev9ClusterObjectTracker()
  left_slots = acquire(left_tracker, [deep_left], qualified_track_ids={6}, side_qualified_track_ids={6},
                       side_retention_track_ids={6}, v_ego=20.0)
  assert left_slots.left is not None
  assert left_slots.right is None

  # Once selected, the same strong track remains visible closer to the lane
  # edge; a new shallow track cannot acquire this slot.
  slots = tracker.update([shallow], qualified_track_ids={3}, side_qualified_track_ids=set(),
                         side_retention_track_ids={3}, v_ego=20.0)
  assert slots.right is not None


def test_right_side_rejects_far_deep_track_and_low_absolute_speed():
  far_tracker = Ev9ClusterObjectTracker()
  far = point(track_id=4, distance=78.0, lateral=-3.2, relative_speed=0.0)
  assert acquire(far_tracker, [far], qualified_track_ids={4}, side_qualified_track_ids={4},
                 side_retention_track_ids={4}, v_ego=20.0).right is None

  slow_tracker = Ev9ClusterObjectTracker()
  slow = point(track_id=5, distance=30.0, lateral=-3.2, relative_speed=-19.0)
  assert acquire(slow_tracker, [slow], qualified_track_ids={5}, side_qualified_track_ids={5},
                 side_retention_track_ids={5}, v_ego=20.0).right is None


def test_left_side_rejects_stationary_world_return():
  tracker = Ev9ClusterObjectTracker()
  curb = point(track_id=8, distance=12.0, lateral=3.0, relative_speed=-20.0)
  slots = acquire(tracker, [curb], qualified_track_ids={8}, side_qualified_track_ids={8}, v_ego=20.0)
  assert slots.left is None


def test_confirmed_side_vehicle_survives_stop_without_new_standstill_acquisition():
  tracker = Ev9ClusterObjectTracker()
  vehicle = point(track_id=8, distance=12.0, lateral=3.0, relative_speed=0.0)
  slots = acquire(tracker, [vehicle], qualified_track_ids={8}, side_qualified_track_ids={8}, v_ego=20.0)
  assert slots.left is not None and slots.left.motion_confirmed

  slots = tracker.update([point(track_id=8, distance=12.0, lateral=3.0, relative_speed=0.0)],
                         qualified_track_ids={8}, side_qualified_track_ids={8}, v_ego=0.0, standstill=True)
  assert slots.left is not None

  stopped_tracker = Ev9ClusterObjectTracker()
  assert acquire(stopped_tracker, [vehicle], qualified_track_ids={8}, side_qualified_track_ids={8},
                 v_ego=0.0, standstill=True).left is None


def test_output_validation_requires_current_fused_primary():
  tracker = Ev9ClusterObjectTracker()
  slots = acquire(tracker, [point(track_id=4)], preferred_primary_track_id=4,
                  require_preferred_primary=True)
  assert validate_cluster_slots_for_output(slots, lead(track_id=4), 10.0, False).primary is not None
  assert validate_cluster_slots_for_output(slots, lead(status=False), 10.0, False).primary is None
  assert validate_cluster_slots_for_output(slots, lead(track_id=5), 10.0, False).primary is None


def test_output_validation_rejects_stationary_side_return():
  moving_side = ClusterObjectSlots(right=ClusterObject(
    track_id=7, distance=5.0, lateral=-3.0, relative_speed=-10.0,
    motion_confirmed=True, raw_relative_speed=-10.0,
  ))
  assert validate_cluster_slots_for_output(moving_side, lead(status=False), 10.0, False).right is None
  assert validate_cluster_slots_for_output(moving_side, lead(status=False), 0.0, True).right is not None


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


def test_display_context_requires_live_radar_main_and_drive_but_allows_stop():
  assert ev9_cluster_display_context_valid(True, True, True, False, 5.0)
  assert not ev9_cluster_display_context_valid(False, True, True, False, 5.0)
  assert not ev9_cluster_display_context_valid(True, False, True, False, 5.0)
  assert not ev9_cluster_display_context_valid(True, True, False, False, 5.0)
  assert ev9_cluster_display_context_valid(True, True, True, True, 0.0)
  assert ev9_cluster_display_context_valid(True, True, True, False, 0.1)
