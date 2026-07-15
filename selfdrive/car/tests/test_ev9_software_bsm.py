from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest

from openpilot.selfdrive.car.ev9_software_bsm import EV9_SOFTWARE_BSM_PROFILE_V1, Ev9SoftwareBsmDetector, \
                                                       select_ev9_software_bsm_outputs


DRIVING_SPEED = 12.0


def track(*, distance=20.0, lateral=3.0, relative_speed=-5.0, measured=True):
  return SimpleNamespace(dRel=distance, yRel=lateral, vRel=relative_speed, measured=measured)


def update(detector, **kwargs):
  values = dict(raw_left=False, raw_right=False, fresh=True, drive=True,
                v_ego=DRIVING_SPEED, steering_angle_deg=0.0)
  values.update(kwargs)
  return detector.update(**values)


def acquire_right(detector, **kwargs):
  result = None
  for _ in range(detector.ACQUIRE_SAMPLES):
    result = update(detector, raw_right=True, **kwargs)
  return result


def test_no_stationary_or_garage_wall_warning():
  detector = Ev9SoftwareBsmDetector()
  wall_tracks = [track(distance=4.0, lateral=3.0, relative_speed=0.0),
                 track(distance=4.0, lateral=-3.0, relative_speed=0.0)]
  for _ in range(10):
    result = update(detector, raw_left=True, raw_right=True, v_ego=0.0, radar_tracks=wall_tracks)
    assert not result.left.detected
    assert not result.right.detected
    assert result.shadow_only


def test_stale_or_reverse_resets_immediately_without_hold():
  detector = Ev9SoftwareBsmDetector()
  assert acquire_right(detector).right.detected
  assert not update(detector, raw_right=True, fresh=False).right.detected

  assert acquire_right(detector).right.detected
  assert not update(detector, raw_right=True, reverse=True).right.detected


def test_acquire_and_short_dropout_hold():
  detector = Ev9SoftwareBsmDetector()
  assert not update(detector, raw_right=True).right.detected
  result = update(detector, raw_right=True)
  assert result.right.detected
  assert result.right.source == "raw36a_right"
  assert 0.0 < result.right.confidence < 1.0

  for _ in range(detector.HOLD_SAMPLES):
    assert update(detector).right.detected
  assert not update(detector).right.detected


def test_scored_diagnostics_explain_candidates_without_changing_detection():
  detector = Ev9SoftwareBsmDetector()

  right = update(detector, raw_right=True)
  assert not right.right.detected
  assert right.right.diagnostics.raw_candidate
  assert not right.right.diagnostics.track_candidate
  assert right.right.diagnostics.candidate
  assert right.right.diagnostics.score == pytest.approx(0.54)
  assert right.right.diagnostics.reject_reason == "acquiring"

  left = update(detector, raw_left=True)
  assert not left.left.detected
  assert left.left.diagnostics.raw_candidate
  assert not left.left.diagnostics.candidate
  assert left.left.diagnostics.score == pytest.approx(0.34)
  assert left.left.diagnostics.reject_reason == "track_required"

  left_with_track = update(detector, raw_left=True, radar_tracks=[track(relative_speed=-9.0)])
  assert not left_with_track.left.detected
  assert left_with_track.left.diagnostics.track_candidate
  assert left_with_track.left.diagnostics.candidate
  assert left_with_track.left.diagnostics.score == pytest.approx(0.68)
  assert left_with_track.left.diagnostics.reject_reason == "acquiring"


@pytest.mark.parametrize(("kwargs", "reason"), [
  ({"fresh": False}, "stale_raw"),
  ({"drive": False}, "not_drive"),
  ({"reverse": True}, "reverse"),
  ({"v_ego": 0.0}, "below_reset_speed"),
  ({"v_ego": float("nan")}, "invalid_speed"),
  ({"steering_angle_deg": 10.0}, "steering_angle"),
  ({"steering_angle_deg": float("nan")}, "invalid_steering_angle"),
])
def test_context_reject_reasons_fail_closed(kwargs, reason):
  result = update(Ev9SoftwareBsmDetector(), raw_right=True, **kwargs)
  assert not result.right.detected
  assert not result.right.diagnostics.candidate
  assert result.right.diagnostics.reject_reason == reason


def test_profile_is_immutable_and_overrides_are_explicit():
  with pytest.raises(FrozenInstanceError):
    EV9_SOFTWARE_BSM_PROFILE_V1.acquire_samples = 1

  profile = replace(
    EV9_SOFTWARE_BSM_PROFILE_V1,
    version="test-no-left-track-v2",
    acquire_samples=1,
    left_track_required=False,
    left_candidate_score=EV9_SOFTWARE_BSM_PROFILE_V1.left_raw_score,
  )
  result = update(Ev9SoftwareBsmDetector(profile), raw_left=True)
  assert result.left.detected
  assert result.left.diagnostics.profile_version == "test-no-left-track-v2"
  assert result.left.diagnostics.score == pytest.approx(profile.left_raw_score)


def test_profile_controls_acquisition_and_hold_counts():
  profile = replace(EV9_SOFTWARE_BSM_PROFILE_V1, version="test-timing-v2",
                    acquire_samples=3, hold_samples=2)
  detector = Ev9SoftwareBsmDetector(profile)
  assert not update(detector, raw_right=True).right.detected
  assert not update(detector, raw_right=True).right.detected
  active = update(detector, raw_right=True).right
  assert active.detected
  assert active.diagnostics.acquire_samples == 3
  assert active.diagnostics.hold_samples == 2

  first_hold = update(detector).right
  assert first_hold.detected
  assert first_hold.diagnostics.reject_reason == "holding"
  assert first_hold.diagnostics.hold_samples == 1
  second_hold = update(detector).right
  assert second_hold.detected
  assert second_hold.diagnostics.hold_samples == 0
  assert not update(detector).right.detected


def test_left_requires_qualified_measured_moving_track():
  detector = Ev9SoftwareBsmDetector()
  for _ in range(4):
    assert not update(detector, raw_left=True).left.detected

  # Absolute target speed is only 2 m/s, below the 10 km/h threshold.
  slow_target = track(relative_speed=-10.0)
  for _ in range(4):
    assert not update(detector, raw_left=True, radar_tracks=[slow_target]).left.detected

  qualified = track(relative_speed=-9.0)
  assert not update(detector, raw_left=True, radar_tracks=[qualified]).left.detected
  result = update(detector, raw_left=True, radar_tracks=[qualified])
  assert result.left.detected
  assert result.left.source == "raw36a_left+measured_track"


def test_speed_hysteresis_and_large_steering_fail_closed():
  detector = Ev9SoftwareBsmDetector()
  below_acquire = detector.EGO_ACQUIRE_SPEED - 0.1
  for _ in range(4):
    assert not update(detector, raw_right=True, v_ego=below_acquire).right.detected

  assert acquire_right(detector).right.detected
  assert update(detector, raw_right=True, v_ego=detector.EGO_RESET_SPEED + 0.1).right.detected
  assert not update(detector, raw_right=True, v_ego=detector.EGO_RESET_SPEED - 0.1).right.detected

  assert acquire_right(detector).right.detected
  assert not update(detector, raw_right=True, steering_angle_deg=detector.MAX_STEERING_ANGLE_DEG).right.detected


def test_same_side_blinker_escalates_but_hazards_do_not():
  detector = Ev9SoftwareBsmDetector()
  assert acquire_right(detector).right.detected
  assert update(detector, raw_right=True, right_blinker=True).right.escalated
  assert not update(detector, raw_right=True, right_blinker=True, hazard=True).right.escalated
  assert not update(detector, raw_right=True, left_blinker=True, right_blinker=True).right.escalated


def test_output_gates_are_independent_and_default_closed():
  detector = Ev9SoftwareBsmDetector()
  result = acquire_right(detector, right_blinker=True)

  outputs = select_ev9_software_bsm_outputs(
    result, detector_enabled=True, comma_output_enabled=False, vehicle_output_enabled=False,
    native_fresh=False, native_left=False, native_right=False,
  )
  assert not outputs.comma_override
  assert not outputs.vehicle_right

  comma = select_ev9_software_bsm_outputs(
    result, detector_enabled=True, comma_output_enabled=True, vehicle_output_enabled=False,
    native_fresh=False, native_left=False, native_right=False,
  )
  assert comma.comma_override and comma.comma_right
  assert not comma.vehicle_right

  vehicle = select_ev9_software_bsm_outputs(
    result, detector_enabled=True, comma_output_enabled=False, vehicle_output_enabled=True,
    native_fresh=False, native_left=False, native_right=False,
  )
  assert not vehicle.comma_override
  assert vehicle.vehicle_right and vehicle.vehicle_right_escalated


def test_fresh_native_state_is_authoritative_over_shadow_result():
  detector = Ev9SoftwareBsmDetector()
  result = acquire_right(detector, right_blinker=True)
  outputs = select_ev9_software_bsm_outputs(
    result, detector_enabled=True, comma_output_enabled=True, vehicle_output_enabled=True,
    native_fresh=True, native_left=True, native_right=False,
  )
  assert not outputs.comma_override
  assert outputs.vehicle_left
  assert not outputs.vehicle_right
  assert not outputs.vehicle_left_escalated
  assert not outputs.vehicle_right_escalated
