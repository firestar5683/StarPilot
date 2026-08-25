import numpy as np
import pytest

from types import SimpleNamespace

from openpilot.common.realtime import DT_MDL
from openpilot.starpilot.common.starpilot_variables import DEFAULT_LATERAL_ACCELERATION
from openpilot.starpilot.controls.lib.curve_speed_controller import (
  CSC_APPROACH_DECEL,
  CSC_COMFORT_MARGIN,
  CSC_COUNT_CAP,
  CSC_EGO_HEADROOM,
  CSC_FARFIELD_GAIN,
  CSC_LAT_ACCEL_MAX,
  CSC_MIN_SPEED,
  MAX_CURVATURE,
  PRIOR_CURVATURE_BP,
  PRIOR_LAT_ACCEL_V,
  CSC_NUDGE,
  CSC_NUDGE_WEIGHT,
  CSC_OVERRIDE_WATCH_TIME,
  CSC_TARGET_UP_RATE,
  CSC_TRAINING_SETTLE_TIME,
  CurveSpeedController,
  weighted_isotonic,
)


class FakeParams:
  def __init__(self, values=None):
    self.values = dict(values or {})

  def get(self, *args, **kwargs):
    key = args[0] if args else None
    return self.values.get(key)

  def put_nonblocking(self, key, value):
    self.values[key] = value


def make_controller(curve_profile=None, curvature_data=None, weather_id=0, reduce_lat=0.0, road_curvature=0.02, driving_in_curve=False):
  if curve_profile is None:
    curve_profile = (np.zeros(33), np.linspace(0.0, 300.0, 33))

  planner = SimpleNamespace(
    params=FakeParams({"CurvatureData": curvature_data} if curvature_data is not None else None),
    curve_profile=curve_profile,
    starpilot_weather=SimpleNamespace(weather_id=weather_id, reduce_lateral_acceleration=reduce_lat),
    road_curvature=road_curvature,
    driving_in_curve=driving_in_curve,
    tracking_lead=False,
    lateral_acceleration=0.0,
  )
  controller = CurveSpeedController(SimpleNamespace(starpilot_planner=planner))
  return planner, controller


def make_sm(*, gas=False, brake=False, long_active=True, blinker=False, accel_pressed=False):
  return {
    "carControl": SimpleNamespace(longActive=long_active),
    "carState": SimpleNamespace(gasPressed=gas, brakePressed=brake, leftBlinker=blinker, rightBlinker=False),
    "starpilotCarState": SimpleNamespace(accelPressed=accel_pressed),
    "onroadEvents": [],
  }


def single_apex_profile(curvature, distance):
  distances = np.linspace(0.0, max(distance * 1.5, 1.0), 33)
  curvatures = np.zeros(33)
  index = int(np.argmin(np.abs(distances - distance)))
  distances[index] = distance
  curvatures[index] = curvature
  return curvatures, distances


def converge(controller, v_ego, v_cruise, frames=600):
  for _ in range(frames):
    controller.update_target(v_ego, v_cruise)
  return controller.target


def envelope_speed(controller, curvature, distance):
  curve_speed = max(float(np.sqrt(controller.lat_accel_for_curvature(curvature) / curvature)), CSC_MIN_SPEED)
  return float(np.sqrt(curve_speed**2 + 2.0 * CSC_APPROACH_DECEL * distance))


def test_straight_road_target_is_cruise_speed():
  _, controller = make_controller()

  controller.update_target(30.0, 30.0)

  assert controller.target == pytest.approx(30.0)


def test_distant_apex_does_not_constrain_until_braking_is_due():
  # derived from the shipped decel so retuning it doesn't silently invalidate the case
  _, probe = make_controller()
  curve_speed = max(float(np.sqrt(probe.lat_accel_for_curvature(0.02) / 0.02)), CSC_MIN_SPEED)
  beyond_braking = 1.3 * (30.0**2 - curve_speed**2) / (2 * CSC_APPROACH_DECEL)

  _, controller = make_controller(curve_profile=single_apex_profile(0.02, beyond_braking))

  target = converge(controller, 30.0, 30.0)

  assert target == pytest.approx(30.0)


def test_apex_in_braking_range_constrains_to_kinematic_envelope():
  _, controller = make_controller(curve_profile=single_apex_profile(0.02, 150.0))

  target = converge(controller, 30.0, 30.0)

  assert target == pytest.approx(envelope_speed(controller, 0.02, 150.0), abs=0.1)
  assert target < 30.0


def test_exit_recovery_rises_immediately_without_freeze():
  planner, controller = make_controller(curve_profile=single_apex_profile(0.03, 20.0))
  low_target = converge(controller, 15.0, 30.0)
  assert low_target < 20.0

  planner.curve_profile = (np.zeros(33), np.linspace(0.0, 300.0, 33))
  controller.update_target(15.0, 30.0)
  assert controller.target > low_target          # rises on the very next frame, no freeze
  assert controller.target - low_target == pytest.approx(CSC_TARGET_UP_RATE * DT_MDL)

  # and it clears the car by the headroom within the time the up-rate needs
  frames = int((15.0 + CSC_EGO_HEADROOM - controller.target) / (CSC_TARGET_UP_RATE * DT_MDL)) + 1
  for _ in range(frames):
    controller.update_target(15.0, 30.0)
  assert controller.target >= 15.0 + CSC_EGO_HEADROOM

  recovered = converge(controller, 15.0, 30.0)
  assert recovered == pytest.approx(30.0)


def test_upward_jitter_in_the_envelope_is_rate_limited():
  # a sweeper the envelope only grazes: raw_target flicks between a mild cap and the
  # set speed. The target must not chase the jumps, or the glow strobes.
  planner, controller = make_controller(curve_profile=single_apex_profile(0.002, 40.0))
  steady = converge(controller, 30.0, 32.0)
  assert steady < 32.0

  flat = (np.zeros(33), np.linspace(0.0, 300.0, 33))
  grazing = planner.curve_profile
  peak = steady
  for i in range(40):
    planner.curve_profile = flat if i % 2 else grazing
    controller.update_target(30.0, 32.0)
    assert controller.target - peak <= CSC_TARGET_UP_RATE * DT_MDL + 1e-6
    peak = controller.target


def test_firm_distant_curvature_is_corrected_for_the_model_under_read():
  # the model reads ~0.81x actual at range, so a firm distant bend binds later than it should
  distance = 90.0
  _, plain = make_controller(curve_profile=single_apex_profile(0.0045, distance))
  _, probe = make_controller()
  corrected = probe._correct_far_field(*single_apex_profile(0.0045, distance))

  assert corrected.max() == pytest.approx(0.0045 * CSC_FARFIELD_GAIN)
  assert converge(plain, 30.0, 30.0) < envelope_speed(plain, 0.0045, distance) + 1e-6


def test_weak_or_near_readings_are_left_alone():
  _, probe = make_controller()

  # too weak to carry usable magnitude at range
  weak = probe._correct_far_field(*single_apex_profile(0.002, 90.0))
  assert weak.max() == pytest.approx(0.002)

  # firm, but close enough that the model is already accurate
  near = probe._correct_far_field(*single_apex_profile(0.0045, 10.0))
  assert near.max() == pytest.approx(0.0045)


def test_far_field_correction_brings_the_slowdown_forward():
  profile = single_apex_profile(0.0045, 120.0)
  _, controller = make_controller(curve_profile=profile)

  corrected = converge(controller, 30.0, 30.0)
  raw_curvatures, distances = profile
  uncorrected = float(np.sqrt(
    max(np.sqrt(controller.lat_accel_for_curvature(0.0045) / 0.0045), CSC_MIN_SPEED) ** 2
    + 2.0 * CSC_APPROACH_DECEL * 120.0))

  assert corrected < uncorrected      # binds sooner than the model's own reading would


def test_fresh_activation_seeds_at_envelope_not_cruise():
  _, controller = make_controller(curve_profile=(np.full(33, 0.05), np.linspace(0.0, 60.0, 33)))

  controller.update_target(6.0, 30.0)

  assert controller.target < 15.0


def test_target_never_trails_accelerating_car_when_unconstrained():
  planner, controller = make_controller(curve_profile=single_apex_profile(0.03, 20.0))
  converge(controller, 15.0, 30.0)

  planner.curve_profile = (np.zeros(33), np.linspace(0.0, 300.0, 33))
  v_ego = 15.0
  caught_up = None
  for frame in range(200):
    v_ego = min(v_ego + 2.0 * DT_MDL, 30.0)
    controller.update_target(v_ego, 30.0)
    # the target climbs faster than the car can, so once it is ahead it stays ahead
    if controller.target >= v_ego:
      caught_up = caught_up if caught_up is not None else frame
    assert caught_up is None or controller.target >= min(30.0, v_ego) - 1e-6

  assert caught_up is not None and caught_up * DT_MDL < 2.0
  assert controller.target == pytest.approx(30.0)


def test_target_does_not_ratchet_down_with_ego_speed():
  _, controller = make_controller(curve_profile=single_apex_profile(0.02, 150.0))
  target = converge(controller, 30.0, 30.0)
  assert target > 15.0

  controller.update_target(14.0, 30.0)

  assert controller.target == pytest.approx(target, abs=0.2)


def test_sharp_curve_target_floors_at_min_speed():
  _, controller = make_controller(curve_profile=(np.full(33, 0.1), np.linspace(0.0, 100.0, 33)))

  target = converge(controller, 15.0, 30.0)

  assert target == pytest.approx(CSC_MIN_SPEED, abs=0.05)


def test_weather_reduces_curve_speed():
  _, dry = make_controller(curve_profile=single_apex_profile(0.01, 0.0))
  _, wet = make_controller(curve_profile=single_apex_profile(0.01, 0.0), weather_id=1, reduce_lat=0.2)

  dry_target = converge(dry, 20.0, 30.0)
  wet_target = converge(wet, 20.0, 30.0)

  assert wet_target < dry_target
  assert wet_target == pytest.approx(dry_target * np.sqrt(0.8), abs=0.1)


def test_prior_gives_higher_lat_accel_for_sharper_curves():
  _, controller = make_controller()

  assert controller.learned_lat_accel(0.001) == pytest.approx(1.5, abs=0.05)
  assert controller.learned_lat_accel(MAX_CURVATURE) > controller.learned_lat_accel(0.001)
  assert controller.learned_lat_accel(MAX_CURVATURE) == pytest.approx(
    float(np.interp(MAX_CURVATURE, PRIOR_CURVATURE_BP, PRIOR_LAT_ACCEL_V)), abs=0.05)
  assert controller.lateral_acceleration == pytest.approx(DEFAULT_LATERAL_ACCELERATION)


def test_comfort_margin_aims_below_the_learned_habit():
  _, controller = make_controller()

  assert controller.lat_accel_for_curvature(0.01) == pytest.approx(
    controller.learned_lat_accel(0.01) * CSC_COMFORT_MARGIN)
  assert controller.lat_accel_for_curvature(0.01) < controller.learned_lat_accel(0.01)


def test_margin_slider_overrides_the_default():
  _, controller = make_controller()
  controller.starpilot_toggles = SimpleNamespace(csc_margin=0.7)

  assert controller.comfort_margin == pytest.approx(0.7)
  assert controller.lat_accel_for_curvature(0.01) == pytest.approx(
    controller.learned_lat_accel(0.01) * 0.7)


def test_margin_falls_back_to_default_without_toggles():
  _, controller = make_controller()

  # toggles are only attached once vcruise runs
  assert controller.comfort_margin == pytest.approx(CSC_COMFORT_MARGIN)
  controller.starpilot_toggles = SimpleNamespace(csc_margin=0.0)
  assert controller.comfort_margin == pytest.approx(CSC_COMFORT_MARGIN)


def test_lower_margin_engages_on_gentler_curves():
  planner, controller = make_controller(curve_profile=single_apex_profile(0.004, 0.0))
  controller.starpilot_toggles = SimpleNamespace(csc_margin=1.0)
  relaxed = converge(controller, 30.0, 30.0)

  planner2, aggressive_controller = make_controller(curve_profile=single_apex_profile(0.004, 0.0))
  aggressive_controller.starpilot_toggles = SimpleNamespace(csc_margin=0.7)
  aggressive = converge(aggressive_controller, 30.0, 30.0)

  assert aggressive < relaxed


def test_approach_decel_slider_moves_where_braking_starts():
  # the same curve must bind further out when the approach is planned gentler
  def bind_distance(decel):
    planner, controller = make_controller(curve_profile=single_apex_profile(0.01, 200.0))
    controller.starpilot_toggles = SimpleNamespace(csc_approach_decel=decel)
    converge(controller, 30.0, 30.0)
    return controller.target

  assert bind_distance(0.3) < bind_distance(1.5)


def test_approach_decel_falls_back_to_default():
  _, controller = make_controller()

  assert controller.approach_decel == pytest.approx(CSC_APPROACH_DECEL)
  controller.starpilot_toggles = SimpleNamespace(csc_approach_decel=0.0)
  assert controller.approach_decel == pytest.approx(CSC_APPROACH_DECEL)


def test_binding_distance_reports_the_constraining_point():
  _, controller = make_controller(curve_profile=single_apex_profile(0.02, 150.0))
  converge(controller, 30.0, 30.0)

  assert controller.binding_distance == pytest.approx(150.0, abs=1.0)


def test_binding_distance_is_zero_when_unconstrained():
  _, controller = make_controller()
  converge(controller, 30.0, 30.0)

  assert controller.binding_distance == 0.0


def test_heavily_sampled_bucket_dominates_prior():
  _, controller = make_controller(curvature_data={"0.05": {"average": 3.0, "count": 100000}})

  assert controller.learned_lat_accel(0.05) == pytest.approx(3.0, abs=0.05)
  assert controller.learned_lat_accel(0.08) >= controller.learned_lat_accel(0.05)


def test_learned_curve_stays_monotonic_despite_low_outlier_bucket():
  _, controller = make_controller(curvature_data={"0.05": {"average": 0.5, "count": 100000}})

  assert controller.learned_lat_accel(0.05) >= controller.learned_lat_accel(0.03)


def test_dense_bucket_is_not_overridden_by_sparse_neighbour():
  # real device data: a running maximum ratcheted the 80-sample bucket up to the 20-sample neighbour
  _, dense_low = make_controller(curvature_data={
    "0.003": {"average": 1.95, "count": 20},
    "0.005": {"average": 1.38, "count": 80},
  })
  _, dense_high = make_controller(curvature_data={
    "0.003": {"average": 1.95, "count": 80},
    "0.005": {"average": 1.38, "count": 20},
  })

  assert dense_low.learned_lat_accel(0.005) < 1.95      # not ratcheted to the sparse neighbour
  assert dense_low.learned_lat_accel(0.005) >= dense_low.learned_lat_accel(0.003)
  # whichever side is better sampled should pull the fit: swapping the counts must raise it
  assert dense_high.learned_lat_accel(0.005) > dense_low.learned_lat_accel(0.005)


def test_weighted_isotonic_pools_violators_by_weight():
  fitted = weighted_isotonic(np.array([1.0, 3.0, 1.2]), np.array([1.0, 1.0, 1000.0]))

  assert np.all(np.diff(fitted) >= -1e-9)
  assert fitted[-1] == pytest.approx(1.2, abs=0.02)


def test_weighted_isotonic_leaves_sorted_input_untouched():
  values = np.array([1.0, 1.5, 2.0, 2.5])
  fitted = weighted_isotonic(values, np.ones(4))

  assert fitted == pytest.approx(values)


def test_legacy_off_grid_curvature_data_merges_into_buckets():
  _, controller = make_controller(curvature_data={
    "0.0203": {"average": 2.5, "count": 10},
    "0.02": {"average": 2.0, "count": 10},
  })

  assert controller.curvature_data["0.02"]["count"] == 20
  assert controller.curvature_data["0.02"]["average"] == pytest.approx(2.25)


def test_training_update_step_is_capped_by_ema_count():
  planner, controller = make_controller(curvature_data={"0.02": {"average": 2.0, "count": 10000}}, driving_in_curve=True)
  planner.lateral_acceleration = 3.0
  controller.training_timer = CSC_TRAINING_SETTLE_TIME

  controller.log_data(10.0, make_sm(long_active=False))

  data = controller.curvature_data["0.02"]
  assert data["count"] == 10001
  assert data["average"] == pytest.approx((2.0 * CSC_COUNT_CAP + 3.0) / (CSC_COUNT_CAP + 1))


def test_no_passive_training_right_after_csc_limited_speed():
  planner, controller = make_controller(curve_profile=single_apex_profile(0.03, 20.0), driving_in_curve=True)
  planner.lateral_acceleration = 3.0
  converge(controller, 15.0, 30.0)
  assert controller.training_quiet_timer > 0.0

  controller.training_timer = CSC_TRAINING_SETTLE_TIME
  controller.log_data(10.0, make_sm(long_active=False))
  assert "0.02" not in controller.curvature_data
  assert not controller.enable_training

  controller.training_quiet_timer = 0.0
  controller.training_timer = CSC_TRAINING_SETTLE_TIME
  controller.log_data(10.0, make_sm(long_active=False))
  assert controller.curvature_data["0.02"]["count"] == 1


def test_training_settles_within_a_couple_of_seconds():
  # a real drive rarely holds every eligibility condition for a whole model horizon,
  # so the settle time has to be short enough that ordinary curves still teach it
  planner, controller = make_controller(driving_in_curve=True)
  planner.lateral_acceleration = 2.4
  sm = make_sm(long_active=False)

  for _ in range(int(CSC_TRAINING_SETTLE_TIME / DT_MDL) - 2):
    controller.log_data(10.0, sm)
  assert "0.02" not in controller.curvature_data

  for _ in range(3):
    controller.log_data(10.0, sm)
  assert controller.curvature_data["0.02"]["count"] >= 1


def test_brief_ineligibility_does_not_restart_the_settle_timer():
  planner, controller = make_controller(driving_in_curve=True)
  planner.lateral_acceleration = 2.4
  sm = make_sm(long_active=False)
  for _ in range(int(CSC_TRAINING_SETTLE_TIME / DT_MDL) + 1):
    controller.log_data(10.0, sm)
  trained = controller.curvature_data["0.02"]["count"]

  # a lead flickers into the tracker for two frames, then leaves
  planner.tracking_lead = True
  controller.log_data(10.0, sm)
  controller.log_data(10.0, sm)
  planner.tracking_lead = False

  controller.log_data(10.0, sm)
  assert controller.curvature_data["0.02"]["count"] == trained + 1


def test_sustained_ineligibility_still_drains_the_settle_timer():
  planner, controller = make_controller(driving_in_curve=True)
  planner.lateral_acceleration = 2.4
  engaged = make_sm(long_active=True)
  manual = make_sm(long_active=False)
  for _ in range(int(CSC_TRAINING_SETTLE_TIME / DT_MDL) + 1):
    controller.log_data(10.0, manual)

  for _ in range(int(2 * CSC_TRAINING_SETTLE_TIME / DT_MDL)):
    controller.log_data(10.0, engaged)
  assert controller.training_timer == pytest.approx(0.0)

  controller.log_data(10.0, manual)
  assert not controller.enable_training


def settle_override(controller, sm=None, frames=None):
  """Run the post-override watch out so the pseudo-sample is committed."""
  sm = sm if sm is not None else make_sm()
  for _ in range(frames if frames is not None else int(CSC_OVERRIDE_WATCH_TIME / DT_MDL) + 1):
    controller.handle_override(20.0, False, sm)


def test_gas_override_nudges_bucket_up_once_per_episode():
  _, controller = make_controller()
  prior = controller.learned_lat_accel(0.02)
  controller.target = 10.0

  controller.handle_override(20.0, True, make_sm(gas=True))
  controller.handle_override(20.0, True, make_sm(gas=True))
  assert "0.02" not in controller.curvature_data  # still watching what the driver holds

  settle_override(controller)
  assert controller.curvature_data["0.02"]["count"] == CSC_NUDGE_WEIGHT
  assert controller.curvature_data["0.02"]["average"] > prior

  controller.handle_override(20.0, False, make_sm())
  controller.target = 10.0
  controller.handle_override(20.0, True, make_sm(gas=True))
  settle_override(controller)
  assert controller.curvature_data["0.02"]["count"] == 2 * CSC_NUDGE_WEIGHT


def test_override_learns_the_cornering_the_driver_actually_held():
  # the whole point: a fixed step needs several rejections to close a real disagreement,
  # so record what they demonstrated instead
  planner, observed = make_controller(driving_in_curve=True)
  observed.target = 10.0
  observed.handle_override(20.0, True, make_sm(gas=True))
  planner.lateral_acceleration = 2.9          # they hold the curve much harder than CSC wanted
  settle_override(observed, make_sm(gas=True))

  _, stepped = make_controller(driving_in_curve=True)
  stepped._apply_nudge(CSC_NUDGE)             # what the old fixed-step path would have recorded

  assert observed.curvature_data["0.02"]["average"] == pytest.approx(2.9)
  assert observed.curvature_data["0.02"]["average"] > stepped.curvature_data["0.02"]["average"]
  assert observed.learned_lat_accel(0.02) > stepped.learned_lat_accel(0.02)


def test_override_on_a_straight_still_registers_the_fixed_step():
  planner, controller = make_controller()
  prior = controller.learned_lat_accel(0.02)
  controller.target = 10.0

  controller.handle_override(20.0, True, make_sm(gas=True))
  planner.lateral_acceleration = 0.0          # never reached a corner
  settle_override(controller)

  assert controller.curvature_data["0.02"]["average"] == pytest.approx(prior + CSC_NUDGE)


def test_res_button_nudges_bucket_up_even_at_target_speed():
  _, controller = make_controller()
  prior = controller.learned_lat_accel(0.02)
  controller.target = 20.0  # car tracking the target, so the gas-press condition would not fire

  controller.handle_override(20.0, True, make_sm(), accel_button=True)
  settle_override(controller)

  assert controller.curvature_data["0.02"]["count"] == CSC_NUDGE_WEIGHT
  assert controller.curvature_data["0.02"]["average"] > prior


def test_brake_override_nudges_bucket_down():
  _, controller = make_controller(driving_in_curve=True)
  prior = controller.learned_lat_accel(0.02)

  controller.handle_override(20.0, True, make_sm(brake=True))

  assert controller.curvature_data["0.02"]["count"] == CSC_NUDGE_WEIGHT
  assert controller.curvature_data["0.02"]["average"] < prior


def test_calibrated_lateral_acceleration_param_is_written_on_flush():
  planner, controller = make_controller(curvature_data={"0.02": {"average": 2.8, "count": 5000}})

  assert "CalibratedLateralAcceleration" not in planner.params.values
  controller.flush_data()

  assert planner.params.values["CalibratedLateralAcceleration"] > DEFAULT_LATERAL_ACCELERATION
  assert controller.lateral_acceleration == planner.params.values["CalibratedLateralAcceleration"]


def test_stale_param_from_a_previous_build_is_republished_without_training():
  # a stale value must not survive a restart just because this drive never trained
  planner, controller = make_controller(curvature_data={"0.02": {"average": 2.8, "count": 5000}})
  planner.params.values["CalibratedLateralAcceleration"] = 3.71

  controller.log_data(0.0, make_sm())  # standstill: ineligible -> flush path

  assert planner.params.values["CalibratedLateralAcceleration"] <= CSC_LAT_ACCEL_MAX
