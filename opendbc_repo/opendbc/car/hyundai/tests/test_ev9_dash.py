from types import SimpleNamespace

import pytest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus
from opendbc.car.structs import CarParams
from opendbc.car.hyundai import ev9_dash, hyundaicanfd
from opendbc.car.hyundai.carstate import get_canfd_speed_limit_state
from opendbc.car.hyundai.ev9_dash import ClusterObject, ClusterObjectSlots, Ev9DashObjectTracker, Ev9DashScene, \
                                             Ev9LaneBoundary, Ev9LaneOutline, Ev9LaneOutlineTracker, \
                                             Ev9RawBlindspotGateState, Ev9TargetLineTracker, display_context_valid, filter_side_objects, \
                                             radar_backed_object, select_ev9_lane_boundaries, select_lane_change_direction, \
                                             select_target_line_distance, update_ev9_raw_blindspot_gate, \
                                             validate_slots_for_output
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.radar_interface import ev9_dash_display_candidate, ev9_dash_side_candidate, \
                                                    ev9_dash_side_retention_candidate
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags, HyundaiStarPilotFlags


def point(track_id=1, distance=30.0, lateral=0.0, relative_speed=-1.0, measured=True):
  return SimpleNamespace(trackId=track_id, dRel=distance, yRel=lateral,
                         vRel=relative_speed, measured=measured)


def lead(track_id=1, distance=30.0, lateral=0.0, relative_speed=-1.0,
         status=True, radar=True):
  return SimpleNamespace(status=status, radar=radar, radarTrackId=track_id,
                         dRel=distance, yRel=lateral, vRel=relative_speed)


def update(tracker, points, preferred=1, display=None, side=None, retention=None,
           v_ego=15.0, standstill=False, model_prob=1.0):
  display = {p.trackId for p in points} if display is None else display
  side = set() if side is None else side
  retention = set() if retention is None else retention
  return tracker.update(points, preferred, model_prob, display, side, retention, v_ego, standstill)


def acquire(tracker, points, samples=3, **kwargs):
  slots = ClusterObjectSlots()
  for _ in range(samples):
    slots = update(tracker, points, **kwargs)
  return slots


def target_line(**overrides):
  values = {
    "display_active": True,
    "starpilot_plan_valid": True,
    "longitudinal_plan_valid": True,
    "model_valid": True,
    "forcing_stop": False,
    "stop_sign_confirmed": False,
    "red_light": False,
    "should_stop": False,
    "model_should_stop": False,
    "experimental_mode": True,
    "has_lead": False,
    "tracking_lead": False,
    "vehicle_stopped": False,
    "lead_distance": 40.0,
    "desired_follow_distance": 0.0,
    "model_terminal_speed": 0.0,
    "model_distance": 42.0,
  }
  values.update(overrides)
  return select_target_line_distance(**values)


def test_display_context_requires_live_radar_main_and_drive():
  assert display_context_valid(True, True, True)
  assert not display_context_valid(False, True, True)
  assert not display_context_valid(True, False, True)
  assert not display_context_valid(True, True, False)


@pytest.mark.parametrize(("native", "native_fresh", "reconstructed", "enabled", "expected"), [
  ((True, False), True, (False, True), False, (True, False)),
  ((True, False), True, (False, True), True, (True, False)),
  ((False, False), False, (True, False), False, (False, False)),
  ((False, False), False, (True, False), True, (True, False)),
])
def test_blindspot_reconstruction_never_overrides_native(native, native_fresh, reconstructed, enabled, expected):
  assert ev9_dash.resolve_ev9_blindspot_state(
    *native,
    native_fresh,
    *reconstructed,
    enabled,
  ) == expected


def test_raw_blindspot_left_requires_strict_adjacent_moving_track():
  state = Ev9RawBlindspotGateState()
  adjacent = point(track_id=7, distance=30.0, lateral=3.0, relative_speed=0.0)
  assert update_ev9_raw_blindspot_gate(state, 0x12, True, True, [adjacent], {7}, {7}, 15.0) == (True, False)

  two_lanes_away = point(track_id=7, distance=30.0, lateral=6.5, relative_speed=0.0)
  assert update_ev9_raw_blindspot_gate(state, 0x12, True, True, [two_lanes_away], {7}, {7}, 15.0) == (False, False)
  assert update_ev9_raw_blindspot_gate(state, 0x12, True, True, [adjacent], {7}, set(), 15.0) == (False, False)

  stationary_wall = point(track_id=7, distance=30.0, lateral=3.0, relative_speed=-15.0)
  assert update_ev9_raw_blindspot_gate(state, 0x12, True, True, [stationary_wall], {7}, {7}, 15.0) == (False, False)


def test_raw_blindspot_right_requires_three_adjacent_display_scans_without_hold():
  state = Ev9RawBlindspotGateState()
  adjacent = point(track_id=8, distance=25.0, lateral=-3.0, relative_speed=0.0)
  for _ in range(2):
    assert update_ev9_raw_blindspot_gate(state, 0x0A, True, True, [adjacent], {8}, {8}, 15.0) == (False, False)
  assert update_ev9_raw_blindspot_gate(state, 0x0A, True, True, [adjacent], {8}, {8}, 15.0) == (False, True)
  assert update_ev9_raw_blindspot_gate(state, 0x0A, True, True, [], set(), set(), 15.0) == (False, False)


def test_raw_blindspot_right_accepts_firmware_variant_side_lifecycle():
  state = Ev9RawBlindspotGateState()
  adjacent = point(track_id=8, distance=25.0, lateral=-3.0, relative_speed=0.0)
  for _ in range(2):
    assert update_ev9_raw_blindspot_gate(state, 0x0A, True, True, [adjacent], set(), {8}, 15.0) == (False, False)
  assert update_ev9_raw_blindspot_gate(state, 0x0A, True, True, [adjacent], set(), {8}, 15.0) == (False, True)


@pytest.mark.parametrize(("raw_state", "raw_fresh", "drive_gear"), [
  (0x10, True, True),  # Missing the observed 0x02 base bit.
  (0x12, False, True),
  (0x12, True, False),
])
def test_raw_blindspot_gate_fails_closed_without_fresh_drive_context(raw_state, raw_fresh, drive_gear):
  state = Ev9RawBlindspotGateState(2, 2)
  adjacent = point(track_id=7, distance=30.0, lateral=3.0, relative_speed=0.0)
  assert update_ev9_raw_blindspot_gate(
    state, raw_state, raw_fresh, drive_gear, [adjacent], {7}, {7}, 15.0,
  ) == (False, False)
  assert state.left_hits == state.right_hits == 0


def test_tracker_requires_three_samples_and_smooths_distance():
  tracker = Ev9DashObjectTracker()
  assert update(tracker, [point(distance=30.0)]).primary is None
  assert update(tracker, [point(distance=32.0)]).primary is None
  primary = update(tracker, [point(distance=34.0)]).primary
  assert primary is not None
  assert primary.distance == pytest.approx(31.855)
  assert primary.distance < 34.0


def test_tracker_holds_four_dropouts_then_clears():
  tracker = Ev9DashObjectTracker()
  assert acquire(tracker, [point()]).primary is not None
  for _ in range(tracker.DROPOUT_HOLD_SAMPLES):
    assert update(tracker, [], display=set()).primary is not None
  assert update(tracker, [], display=set()).primary is None


def test_tracker_holds_qualified_side_slot_through_short_dropout():
  tracker = Ev9DashObjectTracker()
  left = point(track_id=2, distance=30.0, lateral=3.0, relative_speed=0.0)
  assert acquire(tracker, [left], preferred=-1, side={2}, retention={2}).left is not None
  for _ in range(tracker.DROPOUT_HOLD_SAMPLES):
    slots = update(tracker, [], preferred=-1, display=set(), side=set(), retention=set())
    assert slots.left is not None
  assert update(tracker, [], preferred=-1, display=set(), side=set(), retention=set()).left is None


def test_present_disqualified_track_clears_without_hold():
  tracker = Ev9DashObjectTracker()
  assert acquire(tracker, [point()]).primary is not None
  assert update(tracker, [point()], preferred=-1, display=set()).primary is None


def test_fused_primary_does_not_depend_on_route_variant_display_score():
  tracker = Ev9DashObjectTracker()
  slots = acquire(tracker, [point(track_id=7)], preferred=7, display=set())
  assert slots.primary is not None
  assert slots.primary.track_id == 7


def test_firmware_variant_side_track_does_not_require_display_candidate():
  tracker = Ev9DashObjectTracker()
  adjacent = point(track_id=7, lateral=3.0, relative_speed=0.0)
  slots = acquire(tracker, [adjacent], preferred=-1, display=set(), side={7}, retention={7})
  assert slots.left is not None
  assert slots.left.track_id == 7


def test_primary_requires_the_fused_radar_track():
  tracker = Ev9DashObjectTracker()
  points = [point(track_id=1, distance=20.0), point(track_id=2, distance=12.0)]
  slots = acquire(tracker, points, preferred=1)
  assert slots.primary is not None
  assert slots.primary.track_id == 1

  slots = update(tracker, points, preferred=-1)
  assert slots.primary is None


def test_primary_accepts_route_observed_lateral_without_old_2_2_cutoff():
  tracker = Ev9DashObjectTracker()
  slots = acquire(tracker, [point(lateral=2.4)], preferred=1, display=set())
  assert slots.primary is not None
  assert update(tracker, [point(lateral=2.6)], preferred=1, display=set()).primary is None


def test_primary_confidence_is_stricter_beyond_100_metres():
  near_tracker = Ev9DashObjectTracker()
  near = acquire(near_tracker, [point(distance=80.0)], preferred=1, display=set(), model_prob=0.8)
  assert near.primary is not None

  far_tracker = Ev9DashObjectTracker()
  far = acquire(far_tracker, [point(distance=120.0)], preferred=1, display=set(), model_prob=0.8, samples=10)
  assert far.primary is None
  far = acquire(far_tracker, [point(distance=120.0)], preferred=1, display=set(), model_prob=0.95)
  assert far.primary is not None


def test_primary_confidence_holds_four_low_probability_scans_then_clears():
  tracker = Ev9DashObjectTracker()
  assert acquire(tracker, [point()], preferred=1, display=set(), model_prob=1.0).primary is not None
  for _ in range(tracker.DROPOUT_HOLD_SAMPLES):
    assert update(tracker, [point()], preferred=1, display=set(), model_prob=0.5).primary is not None
  assert update(tracker, [point()], preferred=1, display=set(), model_prob=0.5).primary is None


def test_left_slot_is_stable_and_excludes_primary():
  tracker = Ev9DashObjectTracker()
  primary = point(track_id=1, distance=25.0, lateral=0.0, relative_speed=0.0)
  track_3 = point(track_id=3, distance=30.0, lateral=3.2, relative_speed=0.0)
  slots = acquire(tracker, [primary, track_3], side={3})
  assert slots.left is not None
  assert slots.left.track_id == 3

  moved = [primary, point(track_id=2, distance=29.0, lateral=3.0, relative_speed=0.0), track_3]
  slots = update(tracker, moved, side={2, 3})
  assert slots.left is not None
  assert slots.left.track_id == 3


def test_side_slot_does_not_acquire_from_ambiguous_candidates():
  tracker = Ev9DashObjectTracker()
  points = [
    point(track_id=2, distance=35.0, lateral=3.0, relative_speed=0.0),
    point(track_id=3, distance=30.0, lateral=3.2, relative_speed=0.0),
  ]
  assert acquire(tracker, points, preferred=-1, side={2, 3}).left is None


@pytest.mark.parametrize(("side", "adjacent_lateral"), [("left", 2.6), ("right", -2.8)])
def test_primary_moves_atomically_to_adjacent_slot(side, adjacent_lateral):
  tracker = Ev9DashObjectTracker()
  assert acquire(tracker, [point(track_id=7)], preferred=7, display=set()).primary is not None

  moved = point(track_id=7, lateral=adjacent_lateral, relative_speed=0.0)
  slots = update(tracker, [moved], preferred=-1, side={7}, retention={7})
  adjacent = getattr(slots, side)
  assert slots.primary is None
  assert adjacent is not None and adjacent.track_id == 7


def test_primary_handoff_wins_an_ambiguous_adjacent_scene_without_duplication():
  tracker = Ev9DashObjectTracker()
  primary = point(track_id=7, distance=30.0, relative_speed=0.0)
  adjacent = point(track_id=8, distance=40.0, lateral=3.2, relative_speed=0.0)
  slots = acquire(tracker, [primary, adjacent], preferred=7, side={8}, retention={8})
  assert slots.primary is not None and slots.primary.track_id == 7
  assert slots.left is not None and slots.left.track_id == 8

  crossing = point(track_id=7, distance=29.0, lateral=2.6, relative_speed=0.0)
  slots = update(tracker, [crossing, adjacent], preferred=-1, side={7, 8}, retention={7, 8})
  assert slots.primary is None
  assert slots.left is not None and slots.left.track_id == 7
  assert slots.left_rear is None


@pytest.mark.parametrize(("side", "side_lateral"), [("left", 3.0), ("right", -3.0)])
def test_adjacent_track_remains_visible_until_atomic_primary_promotion(side, side_lateral):
  tracker = Ev9DashObjectTracker()
  adjacent = point(track_id=7, lateral=side_lateral, relative_speed=0.0)
  slots = acquire(tracker, [adjacent], preferred=-1, side={7}, retention={7})
  assert getattr(slots, side) is not None

  entering = point(track_id=7, lateral=1.0 if side == "left" else -1.0, relative_speed=0.0)
  for _ in range(tracker.ACQUISITION_SAMPLES - 1):
    slots = update(tracker, [entering], preferred=7, side=set(), retention={7})
    assert slots.primary is None
    assert getattr(slots, side) is not None
  slots = update(tracker, [entering], preferred=7, side=set(), retention={7})
  assert slots.primary is not None and slots.primary.track_id == 7
  assert getattr(slots, side) is None


def test_right_slot_requires_deep_entry_then_retains_toward_lane_edge():
  tracker = Ev9DashObjectTracker()
  entering = point(track_id=4, distance=40.0, lateral=-3.2, relative_speed=0.0)
  slots = acquire(tracker, [entering], preferred=-1, side={4}, retention={4})
  assert slots.right is not None

  retained = point(track_id=4, distance=39.0, lateral=-1.7, relative_speed=0.0)
  slots = update(tracker, [retained], preferred=-1, side=set(), retention={4})
  assert slots.right is not None
  assert slots.right.track_id == 4


def test_right_slot_accepts_route_observed_inner_entry():
  tracker = Ev9DashObjectTracker()
  entering = point(track_id=4, distance=40.0, lateral=-2.4, relative_speed=0.0)
  slots = acquire(tracker, [entering], preferred=-1, side={4}, retention={4})
  assert slots.right is not None


def test_right_lane_edge_ghost_cannot_enter_without_deep_history():
  tracker = Ev9DashObjectTracker()
  ghost = point(track_id=4, distance=40.0, lateral=-1.7, relative_speed=0.0)
  slots = acquire(tracker, [ghost], preferred=-1, side={4}, retention={4}, samples=10)
  assert slots.right is None


def test_stationary_world_side_return_is_rejected():
  tracker = Ev9DashObjectTracker()
  wall = point(track_id=2, distance=20.0, lateral=3.0, relative_speed=-15.0)
  slots = acquire(tracker, [wall], preferred=-1, side={2}, retention={2}, v_ego=15.0)
  assert slots.left is None


def test_moving_side_target_is_retained_at_standstill():
  tracker = Ev9DashObjectTracker()
  moving = point(track_id=2, distance=20.0, lateral=3.0, relative_speed=-8.0)
  slots = acquire(tracker, [moving], preferred=-1, side={2}, retention={2}, v_ego=15.0)
  assert slots.left is not None

  stopped = point(track_id=2, distance=19.0, lateral=3.0, relative_speed=0.0)
  slots = update(tracker, [stopped], preferred=-1, side={2}, retention={2}, v_ego=0.0, standstill=True)
  assert slots.left is not None


def test_validate_output_rejects_stale_primary_and_stationary_side():
  slots = ClusterObjectSlots(
    primary=ClusterObject(1, 20.0, 0.0, 0.0),
    left=ClusterObject(2, 15.0, 3.0, -15.0, True, -15.0),
    left_rear=ClusterObject(4, 10.0, 3.0, -15.0, True, -15.0),
  )
  validated = validate_slots_for_output(slots, lead(track_id=3), 15.0, False)
  assert validated.primary is None
  assert validated.left is None
  assert validated.left_rear is None


def test_side_objects_fail_closed_unless_explicitly_enabled():
  slots = ClusterObjectSlots(
    primary=ClusterObject(1, 20.0, 0.0, 0.0),
    left=ClusterObject(2, 15.0, 3.0, 0.0),
    right=ClusterObject(3, 15.0, -3.0, 0.0),
    left_rear=ClusterObject(4, 10.0, 3.0, 0.0),
    right_rear=ClusterObject(5, 10.0, -3.0, 0.0),
  )
  assert filter_side_objects(slots, True) == slots
  filtered = filter_side_objects(slots, False)
  assert filtered.primary == slots.primary
  assert filtered.left is None
  assert filtered.right is None
  assert filtered.left_rear is None
  assert filtered.right_rear is None


def test_radar_backed_object_rejects_vision_only_and_invalid_values():
  assert radar_backed_object(lead(radar=False)) is None
  assert radar_backed_object(lead(track_id=-1)) is None
  assert radar_backed_object(lead(distance=float("nan"))) is None
  assert radar_backed_object(lead()).track_id == 1


@pytest.mark.parametrize("stop_input", [
  {"forcing_stop": True},
  {"stop_sign_confirmed": True},
  {"red_light": True, "model_terminal_speed": 0.5},
  {"should_stop": True},
  {"model_should_stop": True},
])
def test_target_line_uses_committed_model_stop(stop_input):
  assert target_line(**stop_input) == 42.0
  assert target_line(display_active=False, **stop_input) is None
  assert target_line(starpilot_plan_valid=False, **stop_input) is None
  assert target_line(longitudinal_plan_valid=False, **stop_input) is None


def test_target_line_uses_planner_follow_gap_and_rejects_uncommitted_stop():
  assert target_line(has_lead=True, tracking_lead=True, lead_distance=40.0, desired_follow_distance=28.0) == 12.0
  assert target_line(has_lead=True, tracking_lead=True, lead_distance=18.0, desired_follow_distance=28.0) == 0.1
  assert target_line(has_lead=True, tracking_lead=True, lead_distance=float("nan"), desired_follow_distance=28.0) is None
  assert target_line(should_stop=True, has_lead=True, tracking_lead=False) is None
  assert target_line(should_stop=True, has_lead=True, tracking_lead=False, vehicle_stopped=True) == 42.0
  assert target_line(should_stop=True, vehicle_stopped=True, experimental_mode=False) is None
  assert target_line(has_lead=True, tracking_lead=True, lead_distance=40.0,
                     desired_follow_distance=28.0, experimental_mode=False) == 12.0
  assert target_line(should_stop=True, has_lead=True, tracking_lead=True,
                     lead_distance=40.0, desired_follow_distance=28.0) == 12.0
  assert target_line(should_stop=True, has_lead=True, tracking_lead=True,
                     lead_distance=100.0, desired_follow_distance=28.0) == 72.0
  assert target_line(stop_sign_confirmed=True, has_lead=True, tracking_lead=True,
                     lead_distance=100.0, desired_follow_distance=28.0) == 42.0
  assert target_line(red_light=True, model_terminal_speed=5.0) is None
  assert target_line(forcing_stop=True, model_distance=float("nan")) is None
  assert target_line(forcing_stop=True, model_distance=-1.0) == pytest.approx(0.1)
  assert target_line(forcing_stop=True, model_distance=300.0) == pytest.approx(204.7)


def test_target_line_tracker_smooths_source_transitions_once_per_input_update():
  tracker = Ev9TargetLineTracker()
  assert tracker.update(True, True, None, 30.0, maximum_distance=10.0) == 10.0
  tracker.clear()
  assert tracker.update(True, True, 20.0, 30.0) == 20.0
  assert tracker.update(True, False, 50.0, 30.0) == 20.0
  assert tracker.update(True, True, 50.0, 30.0) == 20.5
  assert tracker.update(True, True, None, 10.0) == 20.0
  assert tracker.update(True, True, 8.0, 10.0, maximum_distance=8.0) == 8.0
  assert tracker.update(False, True, 50.0, 30.0) is None
  assert tracker.distance is None


def test_lane_change_direction_requires_active_committed_model_maneuver():
  assert select_lane_change_direction(True, True, True, "left") == "left"
  assert select_lane_change_direction(True, True, True, "right") == "right"
  assert select_lane_change_direction(False, True, True, "left") is None
  assert select_lane_change_direction(True, False, True, "left") is None
  assert select_lane_change_direction(True, True, False, "left") is None
  assert select_lane_change_direction(True, True, True, None) is None


def test_lane_outline_tracker_hysteresis_smoothing_and_fail_closed_behavior():
  tracker = Ev9LaneOutlineTracker()
  outline = tracker.update(True, True, True, Ev9LaneBoundary(0.6, 0.02), Ev9LaneBoundary(0.6, 0.02), 0.02)
  assert outline.left_visible and outline.right_visible
  assert outline.desired_curvature == pytest.approx(0.02)

  # The car loop is faster than modeld; repeated control ticks must not apply
  # the EMA again or update visibility from the same model frame.
  assert tracker.update(True, True, False, Ev9LaneBoundary(), Ev9LaneBoundary(), -0.05) == outline

  outline = tracker.update(True, True, True, Ev9LaneBoundary(0.44, -0.05), Ev9LaneBoundary(0.50, -0.05), -0.1)
  assert outline.left_visible
  assert outline.right_visible
  assert outline.desired_curvature == pytest.approx(-0.0045)

  for _ in range(tracker.VISIBILITY_DROPOUT_SAMPLES - 1):
    assert tracker.update(True, True, True, Ev9LaneBoundary(), Ev9LaneBoundary(0.5, -0.05), -0.1).left_visible
  assert not tracker.update(True, True, True, Ev9LaneBoundary(), Ev9LaneBoundary(0.5, -0.05), -0.1).left_visible

  assert tracker.update(False, True, True, Ev9LaneBoundary(1.0), Ev9LaneBoundary(1.0), 0.01) == Ev9LaneOutline()
  assert tracker.update(True, False, True, Ev9LaneBoundary(1.0), Ev9LaneBoundary(1.0), 0.01) == Ev9LaneOutline()


def test_lane_boundary_selection_prefers_lane_and_falls_back_to_road_edge():
  straight = SimpleNamespace(x=[5.0, 20.0, 35.0], y=[3.0, 3.0, 3.0])
  curved_edge = SimpleNamespace(x=[5.0, 20.0, 35.0], y=[-3.0, -3.3, -4.2])
  left, right = select_ev9_lane_boundaries(
    [0.0, 0.9, 0.2, 0.0], [straight, straight, straight, straight],
    [1.0, 0.2], [straight, curved_edge],
  )
  assert left.confidence == pytest.approx(0.9)
  assert left.curvature == pytest.approx(0.0)
  assert right.confidence == pytest.approx(0.8)
  assert right.curvature is not None and right.curvature < 0.0


def test_canfd_speed_limit_state_reuses_camera_decode_and_preserves_unlimited():
  CP = SimpleNamespace(flags=int(HyundaiFlags.CANFD_LKA_STEERING))
  FPCP = SimpleNamespace(flags=int(HyundaiStarPilotFlags.SPEED_LIMIT_AVAILABLE))
  camera_values = {"ISLW_SpdCluMainDis": 60, "ISLA_SpdWrn": 1}
  cp = SimpleNamespace(vl={"FR_CMR_02_100ms": camera_values})
  cp_cam = SimpleNamespace(vl={"FR_CMR_02_100ms": {"ISLW_SpdCluMainDis": 35, "ISLA_SpdWrn": 0}})

  assert get_canfd_speed_limit_state(CP, FPCP, cp, cp_cam) == (60, True)
  CP.flags = 0
  assert get_canfd_speed_limit_state(CP, FPCP, cp, cp_cam) == (35, False)
  CP.flags = int(HyundaiFlags.CANFD_LKA_STEERING)
  camera_values["ISLW_SpdCluMainDis"] = 253
  camera_values["ISLA_SpdWrn"] = 0
  assert get_canfd_speed_limit_state(CP, FPCP, cp, cp_cam) == (253, False)
  for invalid in (0, 254, 255):
    camera_values["ISLW_SpdCluMainDis"] = invalid
    assert get_canfd_speed_limit_state(CP, FPCP, cp, cp_cam) == (0, False)

  FPCP.flags = 0
  camera_values["ISLW_SpdCluMainDis"] = 60
  assert get_canfd_speed_limit_state(CP, FPCP, cp, cp_cam) == (0, False)


def test_route_derived_mrr35_display_qualifiers():
  base = {"NEW_SIGNAL_7": 201, "NEW_SIGNAL_3": 2, "NEW_SIGNAL_12": 10,
          "NEW_SIGNAL_15": 2, "NEW_SIGNAL_17": 1}
  assert ev9_dash_display_candidate(base)
  assert ev9_dash_side_candidate(base)
  assert ev9_dash_side_retention_candidate(base)

  strict = base | {"NEW_SIGNAL_7": 281}
  assert ev9_dash_display_candidate(strict)
  assert ev9_dash_side_candidate(strict)
  assert ev9_dash_side_retention_candidate(strict)

  firmware_variant = base | {"NEW_SIGNAL_7": 99}
  assert not ev9_dash_display_candidate(firmware_variant)
  assert ev9_dash_side_candidate(firmware_variant)
  assert ev9_dash_side_retention_candidate(firmware_variant)

  relaxed_retention = firmware_variant | {"NEW_SIGNAL_12": 7, "NEW_SIGNAL_15": 1}
  assert not ev9_dash_side_candidate(relaxed_retention)
  assert ev9_dash_side_retention_candidate(relaxed_retention)

  for signal in ("NEW_SIGNAL_3", "NEW_SIGNAL_12", "NEW_SIGNAL_15", "NEW_SIGNAL_17"):
    assert not ev9_dash_side_candidate(strict | {signal: 0})


def test_ccnc_status_encodes_stable_stock_object_slots():
  CP = CarParams.new_message()
  CP.carFingerprint = CAR.KIA_EV9
  CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CCNC | HyundaiFlags.CANFD_ANGLE_STEERING |
                 HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)
  packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
  can_bus = CanBus(CP)
  parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("CCNC_0x161", 0), ("CCNC_0x162", 0)], can_bus.ECAN)
  scene = Ev9DashScene(objects=ClusterObjectSlots(
    primary=ClusterObject(1, 30.0, 0.2, -1.0),
    left=ClusterObject(2, 40.0, 3.4, 0.0),
    right=ClusterObject(3, 35.0, -3.1, 0.0),
    left_rear=ClusterObject(4, 18.0, 3.0, 0.0),
    right_rear=ClusterObject(5, 22.0, -3.0, 0.0),
  ), speed_limit_raw=60, speed_limit_warning=True)
  out = SimpleNamespace(vCruiseCluster=100.0, vEgo=10.0)
  hud = SimpleNamespace(leadDistanceBars=3, leftLaneDepart=False, rightLaneDepart=False)

  parser.update([(1, hyundaicanfd.create_ccnc_angle_long_status_messages(
    packer, CP, can_bus, 1, enabled=True, main_cruise_enabled=True,
    hud=hud, out=out, dash_scene=scene,
  ))])
  status = parser.vl["CCNC_0x162"]
  assert parser.vl["CCNC_0x161"]["FCA_ICON"] == 1
  assert parser.vl["CCNC_0x161"]["LKA_ICON"] == 0
  assert parser.vl["CCNC_0x161"]["TARGET_DISTANCE"] == pytest.approx(16.3)
  assert parser.vl["CCNC_0x161"]["DISTANCE_LEAD"] == 2
  assert status["LEAD"] == 2
  assert status["LEAD_DISTANCE"] == pytest.approx(29.8)
  assert status["LEAD_LATERAL"] == 0.0
  assert status["LEAD_ALT"] == 0
  assert status["LEAD_LEFT"] == 1
  assert status["LEAD_LEFT_DISTANCE"] == pytest.approx(39.8)
  assert status["LEAD_LEFT_LATERAL"] == pytest.approx(3.0)
  assert status["LEAD_RIGHT"] == 1
  assert status["LEAD_RIGHT_DISTANCE"] == pytest.approx(34.8)
  assert status["LEAD_RIGHT_LATERAL"] == pytest.approx(3.0)
  assert status["LEAD_LEFT_REAR_STATUS"] == 1
  assert status["LEAD_LEFT_REAR_DISTANCE"] == pytest.approx(17.8)
  assert status["LEAD_RIGHT_REAR_STATUS"] == 1
  assert status["LEAD_RIGHT_REAR_DISTANCE"] == pytest.approx(21.8)
  assert status["COUNTRY"] == 7
  assert status["SPEEDLIMIT"] == 60
  assert status["SPEEDLIMIT_FLASH"] == 4
  assert status["SPEEDLIMIT_WEATHER"] == 0

  parser.update([(2, hyundaicanfd.create_ccnc_angle_long_status_messages(
    packer, CP, can_bus, 2, enabled=True, main_cruise_enabled=True,
    hud=hud, out=out, dash_scene=Ev9DashScene(target_line_distance=42.0, speed_limit_raw=253),
  ))])
  assert parser.vl["CCNC_0x161"]["TARGET_DISTANCE"] == pytest.approx(42.0)
  assert parser.vl["CCNC_0x162"]["SPEEDLIMIT"] == 253
  assert parser.vl["CCNC_0x162"]["SPEEDLIMIT_FLASH"] == 2


def test_disabled_optional_reconstruction_keeps_mandatory_handoff_status():
  CP = CarParams.new_message()
  CP.carFingerprint = CAR.KIA_EV9
  CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CCNC | HyundaiFlags.CANFD_ANGLE_STEERING |
                 HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)
  CP.wheelbase = 3.1
  CP.steerRatio = 16.0
  packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
  can_bus = CanBus(CP)
  parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("CCNC_0x161", 0), ("CCNC_0x162", 0)], can_bus.ECAN)
  scene = Ev9DashScene(
    objects=ClusterObjectSlots(
      primary=ClusterObject(1, 30.0, 0.0, 0.0),
      left=ClusterObject(2, 35.0, 3.0, 0.0),
      right=ClusterObject(3, 35.0, -3.0, 0.0),
    ),
    lane_outline=Ev9LaneOutline(True, True, 0.01),
    target_line_distance=40.0,
    lane_change_direction="left",
    objects_enabled=False,
    headway_enabled=False,
  )
  hud = SimpleNamespace(leadDistanceBars=3, leftLaneDepart=False, rightLaneDepart=False)
  out = SimpleNamespace(vCruiseCluster=100.0, vEgo=10.0)

  parser.update([(1, hyundaicanfd.create_ccnc_angle_long_status_messages(
    packer, CP, can_bus, 1, enabled=False, main_cruise_enabled=True,
    hud=hud, out=out, steering_available=True, steering_active=False,
    dash_scene=scene,
  ))])

  status_161 = parser.vl["CCNC_0x161"]
  status_162 = parser.vl["CCNC_0x162"]
  assert status_161["FCA_ICON"] == 1
  assert status_161["LKA_ICON"] == 0
  assert status_161["LFA_ICON"] == 1
  assert status_161["LCA_LEFT_ARROW"] == 2
  assert status_161["TARGET"] == 0
  assert status_161["DISTANCE_LEAD"] == 0
  assert status_162["LEAD"] == 0
  assert status_162["LEAD_LEFT"] == 0
  assert status_162["LEAD_RIGHT"] == 0

  standby_scene = Ev9DashScene(
    objects=scene.objects,
    lane_outline=Ev9LaneOutline(True, True, 0.01),
    target_line_distance=42.0,
  )
  parser.update([(3, hyundaicanfd.create_ccnc_angle_long_status_messages(
    packer, CP, can_bus, 3, enabled=False, main_cruise_enabled=True,
    hud=hud, out=out, dash_scene=standby_scene,
  ))])
  standby_161 = parser.vl["CCNC_0x161"]
  standby_162 = parser.vl["CCNC_0x162"]
  assert standby_161["TARGET"] == 3
  assert standby_161["TARGET_DISTANCE"] == pytest.approx(42.0)
  assert standby_161["LANELINE_LEFT"] == 2
  assert standby_161["LANELINE_RIGHT"] == 2
  assert standby_161["DISTANCE_LEAD"] == 1
  assert standby_162["LEAD"] == 1
  assert standby_162["LEAD_LEFT"] == 1
  assert standby_162["LEAD_RIGHT"] == 1

  parser.update([(4, hyundaicanfd.create_ccnc_angle_long_status_messages(
    packer, CP, can_bus, 4, enabled=False, main_cruise_enabled=False,
    hud=hud, out=out, dash_scene=standby_scene,
  ))])
  assert parser.vl["CCNC_0x161"]["TARGET"] == 0
  assert parser.vl["CCNC_0x161"]["LANELINE_LEFT"] == 0
  assert parser.vl["CCNC_0x161"]["DISTANCE_LEAD"] == 0
  assert parser.vl["CCNC_0x162"]["LEAD"] == 0
  assert parser.vl["CCNC_0x162"]["LEAD_LEFT"] == 0

  neutral_messages = hyundaicanfd.create_ccnc_angle_long_status_messages(
    packer, CP, can_bus, 5, enabled=True, main_cruise_enabled=True,
    hud=hud, out=out, dash_scene=Ev9DashScene(),
  )
  neutral_status = next(msg for msg in neutral_messages if msg.address == 0x162)
  parser.update([(5, neutral_messages)])
  assert neutral_status.dat[3] == 0x27
  assert parser.vl["CCNC_0x162"]["COUNTRY"] == 7
  assert parser.vl["CCNC_0x162"]["SPEEDLIMIT"] == 0
  assert parser.vl["CCNC_0x162"]["SPEEDLIMIT_FLASH"] == 2


@pytest.mark.parametrize(("side", "left_arrow", "right_arrow"), [
  ("left", 2, 0),
  ("right", 0, 2),
])
def test_ccnc_lane_change_uses_existing_lane_arrow_and_icon_states(side, left_arrow, right_arrow):
  CP = CarParams.new_message()
  CP.carFingerprint = CAR.KIA_EV9
  CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CCNC | HyundaiFlags.CANFD_ANGLE_STEERING |
                 HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)
  CP.wheelbase = 3.1
  CP.steerRatio = 16.0
  packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
  can_bus = CanBus(CP)
  parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("CCNC_0x161", 0)], can_bus.ECAN)
  scene = Ev9DashScene(
    lane_outline=Ev9LaneOutline(True, True, 0.01),
    lane_change_direction=side,
  )
  hud = SimpleNamespace(leadDistanceBars=3, leftLaneDepart=False, rightLaneDepart=False)
  out = SimpleNamespace(vCruiseCluster=100.0, vEgo=10.0)

  parser.update([(1, hyundaicanfd.create_ccnc_angle_long_status_messages(
    packer, CP, can_bus, 1, enabled=False, main_cruise_enabled=True,
    hud=hud, out=out, dash_scene=scene,
  ))])
  status = parser.vl["CCNC_0x161"]
  assert status["LCA_LEFT_ICON"] == 2
  assert status["LCA_RIGHT_ICON"] == 2
  assert status["LCA_LEFT_ARROW"] == left_arrow
  assert status["LCA_RIGHT_ARROW"] == right_arrow
  assert status["LANELINE_LEFT"] == 6
  assert status["LANELINE_RIGHT"] == 6


@pytest.mark.parametrize(("steering_angle", "expected"), [
  (-67.5, 13),
  (-9.0, 0),
  (-4.5, 31),
  (0.0, 15),
  (4.5, 16),
  (67.5, 30),
])
def test_ccnc_lane_curvature_mapping_preserves_existing_ccnc_encoding(steering_angle, expected):
  assert hyundaicanfd.ccnc_lane_curvature_from_steering_angle(steering_angle) == expected


@pytest.mark.parametrize(("desired_curvature", "expected_direction"), [
  (0.02, "below"),
  (-0.02, "above"),
])
def test_ccnc_status_encodes_model_lane_outline_with_stock_layout(desired_curvature, expected_direction):
  CP = CarParams.new_message()
  CP.carFingerprint = CAR.KIA_EV9
  CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CCNC | HyundaiFlags.CANFD_ANGLE_STEERING |
                 HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)
  CP.wheelbase = 3.1
  CP.steerRatio = 16.0
  packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
  can_bus = CanBus(CP)
  parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("CCNC_0x161", 0)], can_bus.ECAN)
  hud = SimpleNamespace(leadDistanceBars=3, leftLaneDepart=True, rightLaneDepart=False)
  out = SimpleNamespace(vCruiseCluster=100.0, vEgo=10.0)
  scene = Ev9DashScene(lane_outline=Ev9LaneOutline(True, True, desired_curvature))

  parser.update([(1, hyundaicanfd.create_ccnc_angle_long_status_messages(
    packer, CP, can_bus, 1, enabled=True, main_cruise_enabled=True,
    hud=hud, out=out, dash_scene=scene,
  ))])
  status = parser.vl["CCNC_0x161"]
  assert status["LANELINE_LEFT"] == 4
  assert status["LANELINE_RIGHT"] == 2
  assert status["LANELINE_LEFT_POSITION"] == 15
  assert status["LANELINE_RIGHT_POSITION"] == 15
  assert status["LANE_ZOOM"] == 1
  if expected_direction == "below":
    assert status["LANELINE_CURVATURE"] < 15
  else:
    assert 15 < status["LANELINE_CURVATURE"] < 31

  parser.update([(2, hyundaicanfd.create_ccnc_angle_long_status_messages(
    packer, CP, can_bus, 2, enabled=False, main_cruise_enabled=True,
    hud=hud, out=out, dash_scene=scene,
  ))])
  status = parser.vl["CCNC_0x161"]
  assert status["LANELINE_LEFT"] == 4
  assert status["LANELINE_RIGHT"] == 2
  if expected_direction == "below":
    assert status["LANELINE_CURVATURE"] < 15
  else:
    assert 15 < status["LANELINE_CURVATURE"] < 31
  assert status["LANELINE_LEFT_POSITION"] == 15
  assert status["LANELINE_RIGHT_POSITION"] == 15
  assert status["LANE_ZOOM"] == 1


def test_ccnc_side_kill_switch_suppresses_all_radar_side_slots():
  CP = CarParams.new_message()
  CP.carFingerprint = CAR.KIA_EV9
  CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CCNC | HyundaiFlags.CANFD_LKA_STEERING)
  packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
  can_bus = CanBus(CP)
  parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("CCNC_0x162", 0)], can_bus.ECAN)
  scene = Ev9DashScene(
    objects=ClusterObjectSlots(
      left=ClusterObject(2, 20.0, 3.0, 0.0),
      left_rear=ClusterObject(3, 10.0, 3.0, 0.0),
    ),
    side_objects_enabled=False,
  )
  parser.update([(1, hyundaicanfd.create_ccnc_angle_long_status_messages(
    packer, CP, can_bus, 1, enabled=True,
    hud=SimpleNamespace(leadDistanceBars=3), out=SimpleNamespace(vCruiseCluster=100.0, vEgo=10.0),
    dash_scene=scene,
  ))])
  status = parser.vl["CCNC_0x162"]
  assert status["LEAD_LEFT"] == 0
  assert status["LEAD_LEFT_REAR_STATUS"] == 0


def test_ccnc_status_uses_standby_objects_until_main_is_off():
  CP = CarParams.new_message()
  CP.carFingerprint = CAR.KIA_EV9
  CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CCNC | HyundaiFlags.CANFD_ANGLE_STEERING |
                 HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)
  packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
  can_bus = CanBus(CP)
  parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("CCNC_0x161", 0), ("CCNC_0x162", 0)], can_bus.ECAN)
  scene = Ev9DashScene(objects=ClusterObjectSlots(primary=ClusterObject(1, 30.0, 0.0, 0.0)))

  parser.update([(1, hyundaicanfd.create_ccnc_angle_long_status_messages(
    packer, CP, can_bus, 1, enabled=False, main_cruise_enabled=True,
    hud=SimpleNamespace(leadDistanceBars=3), out=SimpleNamespace(vCruiseCluster=100.0, vEgo=10.0),
    dash_scene=scene,
  ))])
  assert parser.vl["CCNC_0x161"]["DISTANCE_LEAD"] == 1
  assert parser.vl["CCNC_0x162"]["LEAD"] == 1

  parser.update([(2, hyundaicanfd.create_ccnc_angle_long_status_messages(
    packer, CP, can_bus, 2, enabled=False, main_cruise_enabled=False,
    hud=SimpleNamespace(leadDistanceBars=3), out=SimpleNamespace(vCruiseCluster=100.0, vEgo=10.0),
    dash_scene=scene,
  ))])
  assert parser.vl["CCNC_0x161"]["DISTANCE_LEAD"] == 0
  assert parser.vl["CCNC_0x162"]["LEAD"] == 0
