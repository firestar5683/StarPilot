from types import SimpleNamespace

from openpilot.selfdrive.controls.lib.longitudinal_vehicle_tunes import get_far_lead_coast_headway_floor
from openpilot.selfdrive.controls.lib.lead_behavior import (
  get_tracked_lead_catchup_bias,
  is_radarless_matched_follow_window,
  should_hold_tracked_vision_lead,
  should_track_lead,
  should_disable_far_lead_throttle,
)


def test_tracked_lead_catchup_bias_for_hanging_gap():
  bias = get_tracked_lead_catchup_bias(31.4, 78.7, 38.0, 0.1)
  assert bias > 10.0


def test_tracked_lead_catchup_bias_ignores_near_desired_gap():
  bias = get_tracked_lead_catchup_bias(31.4, 50.0, 38.0, 0.1)
  assert bias == 0.0


def test_tracked_lead_catchup_bias_corrects_lightning_aggressive_follow_bookmark():
  default_bias = get_tracked_lead_catchup_bias(
    31.75,
    46.2,
    34.0,
    0.0,
    v_cruise=37.55,
    y_rel=0.1,
  )
  bias = get_tracked_lead_catchup_bias(
    31.75,
    46.2,
    34.0,
    0.0,
    v_cruise=37.55,
    y_rel=0.1,
    min_headway_margin=0.20,
    full_headway_margin=0.45,
  )

  assert default_bias == 0.0
  assert bias > 2.0


def test_tracked_lead_catchup_bias_handles_crv_hanging_gap():
  tuned_bias = get_tracked_lead_catchup_bias(
    19.8,
    85.0,
    43.636,
    1.7,
    v_cruise=20.44,
    y_rel=-0.54,
    min_headway_margin=0.10,
    full_headway_margin=0.35,
    bias_gain=1.25,
    bias_cap=65.0,
    speed_range=(10.0, 18.0),
    fade_margins=(0.75, 6.5),
    cruise_error_full=0.75,
  )

  assert tuned_bias > 40.0


def test_tracked_lead_catchup_bias_ignores_very_far_gap():
  bias = get_tracked_lead_catchup_bias(31.4, 110.0, 38.0, 0.1)
  assert bias == 0.0


def test_tracked_lead_catchup_bias_applies_to_two_second_highway_gap():
  bias = get_tracked_lead_catchup_bias(30.4, 63.0, 40.0, 0.4)
  assert bias > 9.0


def test_tracked_lead_catchup_bias_reduces_for_laterally_offset_lead():
  centered = get_tracked_lead_catchup_bias(34.0, 103.0, 73.0, 1.9, y_rel=0.2)
  offset = get_tracked_lead_catchup_bias(34.0, 103.0, 73.0, 1.9, y_rel=1.95)
  assert centered > 0.0
  assert offset == 0.0


def test_tracked_lead_catchup_bias_fades_before_very_far_gap_cutoff():
  near_upper = get_tracked_lead_catchup_bias(34.0, 103.0, 73.0, 1.9)
  smaller_gap = get_tracked_lead_catchup_bias(34.0, 96.0, 73.0, 1.9)
  assert near_upper > 0.0
  assert near_upper < smaller_gap


def test_tracked_lead_catchup_bias_stays_off_once_at_set_speed():
  bias = get_tracked_lead_catchup_bias(31.4, 78.7, 38.0, 0.1, v_cruise=31.4)
  assert bias == 0.0


def test_tracked_lead_catchup_bias_fades_smoothly_near_set_speed():
  below_set = get_tracked_lead_catchup_bias(27.70, 81.0, 46.0, 0.0, v_cruise=27.78, y_rel=0.8)
  at_set = get_tracked_lead_catchup_bias(27.78, 81.0, 46.0, 0.0, v_cruise=27.78, y_rel=0.8)
  assert 0.0 < below_set < 0.25
  assert at_set == 0.0


def test_tracked_lead_catchup_bias_dials_back_camry_bookmark_case():
  bias = get_tracked_lead_catchup_bias(27.40, 81.0, 46.0, 0.0, v_cruise=27.78, y_rel=0.8)
  assert 0.0 < bias < 2.0


def test_tracked_lead_catchup_bias_fades_smoothly_at_closing_limit():
  below_limit = get_tracked_lead_catchup_bias(31.4, 78.7, 38.0, 3.75)
  above_limit = get_tracked_lead_catchup_bias(31.4, 78.7, 38.0, 3.77)
  assert abs(below_limit - above_limit) < 0.1


def test_disable_far_lead_throttle_rejects_two_second_plus_gap():
  should_disable = should_disable_far_lead_throttle(31.4, 78.7, 38.0, 0.1, False)
  assert not should_disable


def test_disable_far_lead_throttle_keeps_mild_coast_near_target_gap():
  should_disable = should_disable_far_lead_throttle(31.4, 52.0, 38.0, 0.5, False)
  assert should_disable


def test_disable_far_lead_throttle_waits_until_reduced_gap():
  should_disable = should_disable_far_lead_throttle(31.4, 43.5, 38.0, 0.5, False)
  assert should_disable


def test_disable_far_lead_throttle_rejects_fast_closing():
  should_disable = should_disable_far_lead_throttle(31.4, 52.0, 38.0, 3.5, False)
  assert not should_disable


def test_disable_far_lead_throttle_rejects_route_like_highway_stab_case():
  should_disable = should_disable_far_lead_throttle(34.69, 68.5, 63.0, 2.31, False)
  assert not should_disable


def test_disable_far_lead_throttle_rejects_large_gap_near_pace_matched_case():
  should_disable = should_disable_far_lead_throttle(32.43, 72.4, 56.0, 1.30, False)
  assert not should_disable


def test_silverado_far_lead_coast_does_not_cut_throttle_at_hanging_highway_gap():
  truck = SimpleNamespace(brand="gm", carFingerprint="CHEVROLET_SILVERADO", enableGasInterceptorDEPRECATED=False)
  # Route 15c: the old coast gate repeatedly closed at roughly 60 m, not 0.75 s.
  scene = (34.0, 57.0, 43.0, 1.0, False)
  assert should_disable_far_lead_throttle(*scene)
  assert not should_disable_far_lead_throttle(*scene, get_far_lead_coast_headway_floor(truck))


def test_silverado_far_lead_coast_still_works_near_requested_gap():
  truck = SimpleNamespace(brand="gm", carFingerprint="CHEVROLET_SILVERADO", enableGasInterceptorDEPRECATED=False)
  floor = get_far_lead_coast_headway_floor(truck)
  assert should_disable_far_lead_throttle(34.0, 40.0, 33.0, 0.6, False, floor)
  assert not should_disable_far_lead_throttle(34.0, 40.0, 33.0, 4.0, False, floor)
  assert not should_disable_far_lead_throttle(15.0, 24.0, 16.0, 0.6, False, floor)
  assert not should_disable_far_lead_throttle(34.0, 40.0, 33.0, 0.6, True, floor)


def test_far_lead_coast_tune_is_only_for_non_pedal_gm_trucks():
  for fingerprint in ("CHEVROLET_SILVERADO", "CHEVROLET_SILVERADO_CC"):
    truck = SimpleNamespace(brand="gm", carFingerprint=fingerprint, enableGasInterceptorDEPRECATED=False)
    assert get_far_lead_coast_headway_floor(truck) == 1.25
    truck.enableGasInterceptorDEPRECATED = True
    assert get_far_lead_coast_headway_floor(truck) == 1.75
  for brand, fingerprint in (("gm", "CHEVROLET_BOLT_EUV"), ("ford", "FORD_F_150_LIGHTNING_MK1"), ("hyundai", "HYUNDAI_IONIQ_6")):
    assert get_far_lead_coast_headway_floor(SimpleNamespace(brand=brand, carFingerprint=fingerprint)) == 1.75
  assert get_far_lead_coast_headway_floor(None) == 1.75


def test_should_track_lead_keeps_radar_leads_on_model_horizon():
  assert should_track_lead(True, 95.0, 100.0, 6.0, 30.0, v_lead=25.0, radar=True)


def test_should_track_lead_rejects_far_vision_only_highway_lead():
  assert not should_track_lead(True, 82.0, 140.0, 6.0, 29.0, v_lead=25.0, radar=False)


def test_should_track_lead_accepts_closer_vision_only_highway_lead():
  assert should_track_lead(True, 56.0, 140.0, 6.0, 29.0, v_lead=25.0, radar=False)


def test_should_track_lead_accepts_fast_closing_vision_lead_early():
  assert should_track_lead(True, 90.0, 140.0, 6.0, 20.0, v_lead=0.0, radar=False)


def test_should_hold_tracked_vision_lead_keeps_honda_bookmark_case():
  assert should_hold_tracked_vision_lead(
    True, 44.5, 174.0, 6.0, 16.8,
    model_prob=0.99, y_rel=-0.69, radar=False,
  )


def test_should_hold_tracked_vision_lead_does_not_expand_initial_tracking_gate():
  assert not should_track_lead(True, 44.5, 174.0, 6.0, 16.8, v_lead=16.7, radar=False)


def test_should_hold_tracked_vision_lead_releases_offcenter_lead():
  assert not should_hold_tracked_vision_lead(
    True, 44.5, 174.0, 6.0, 16.8,
    model_prob=0.99, y_rel=-1.7, radar=False,
  )


def test_should_hold_tracked_vision_lead_uses_path_relative_offset_on_curve():
  assert should_hold_tracked_vision_lead(
    True, 27.8, 174.0, 6.0, 16.0,
    model_prob=1.0, y_rel=-2.11, path_y=1.32, radar=False,
  )


def test_should_hold_tracked_vision_lead_releases_low_confidence_lead():
  assert not should_hold_tracked_vision_lead(
    True, 44.5, 174.0, 6.0, 16.8,
    model_prob=0.69, y_rel=0.0, radar=False,
  )


def test_should_hold_tracked_vision_lead_does_not_change_radar_tracking():
  assert not should_hold_tracked_vision_lead(
    True, 44.5, 174.0, 6.0, 16.8,
    model_prob=0.99, y_rel=0.0, radar=True,
  )


def test_should_hold_tracked_vision_lead_keeps_braking_lead():
  assert should_hold_tracked_vision_lead(
    True, 44.5, 174.0, 6.0, 16.8,
    model_prob=0.99, y_rel=0.0, radar=False,
  )


def test_should_hold_tracked_vision_lead_releases_beyond_exit_gap():
  assert not should_hold_tracked_vision_lead(
    True, 57.0, 174.0, 6.0, 16.8,
    model_prob=0.99, y_rel=0.0, radar=False,
  )


def test_should_hold_tracked_vision_lead_ignores_shortened_model_horizon_in_bolt_stutter_case():
  assert should_hold_tracked_vision_lead(
    True, 54.6, 40.0, 6.0, 19.4,
    model_prob=1.0, y_rel=0.05, radar=False,
  )


def test_should_hold_tracked_vision_lead_does_not_extend_low_confidence_short_horizon_case():
  assert not should_hold_tracked_vision_lead(
    True, 54.6, 40.0, 6.0, 19.4,
    model_prob=0.90, y_rel=0.05, radar=False,
  )


def test_radarless_matched_follow_window_accepts_pace_matched_highway_follow():
  assert is_radarless_matched_follow_window(31.0, 48.0, 30.4, 1.45, radar=False, lead_brake=0.05, lead_prob=0.95)


def test_radarless_matched_follow_window_rejects_large_relative_speed():
  assert not is_radarless_matched_follow_window(31.0, 48.0, 27.5, 1.45, radar=False, lead_brake=0.05, lead_prob=0.95)


def test_radarless_matched_follow_window_rejects_far_headway():
  assert not is_radarless_matched_follow_window(31.0, 82.0, 30.4, 1.45, radar=False, lead_brake=0.05, lead_prob=0.95)


def test_radarless_matched_follow_window_rejects_low_confidence_lead():
  assert not is_radarless_matched_follow_window(31.0, 48.0, 30.4, 1.45, radar=False, lead_brake=0.05, lead_prob=0.55)


def test_radarless_matched_follow_window_keeps_default_low_speed_guard():
  assert not is_radarless_matched_follow_window(14.4, 25.4, 16.2, 1.25, radar=False, lead_brake=0.0, lead_prob=1.0)


def test_radarless_matched_follow_window_accepts_lower_speed_when_requested():
  assert is_radarless_matched_follow_window(14.4, 25.4, 16.2, 1.25, radar=False, lead_brake=0.0, lead_prob=1.0, min_speed=12.0)
