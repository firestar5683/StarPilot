from types import SimpleNamespace

from openpilot.selfdrive.car.ev9_software_bsm import Ev9SoftwareBsmDetector, select_ev9_software_bsm_outputs


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
