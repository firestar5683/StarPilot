import numpy as np

from cereal import car
from types import SimpleNamespace
from opendbc.car.hyundai.values import CAR as HYUNDAI_CAR
from openpilot.selfdrive.locationd.torqued import (TorqueEstimator, LAT_ACC_THRESHOLD, FACTOR_SANITY,
                                                   IONIQ_6_LAT_ACC_THRESHOLD, IONIQ_6_FACTOR_SANITY)


def _torque_cp(fingerprint, lat_accel_factor=3.0, friction=0.09):
  CP = car.CarParams.new_message()
  CP.carFingerprint = fingerprint
  CP.brand = "hyundai"
  CP.lateralTuning.init("torque")
  CP.lateralTuning.torque.latAccelFactor = lat_accel_factor
  CP.lateralTuning.torque.friction = friction
  return CP


def _fill_line(est, slope, seed=0):
  """Fill every bucket to its minimum (and the total) with points on lat = slope * torque."""
  rng = np.random.default_rng(seed)
  for (low, high), min_pts in zip(est.filtered_points.buckets.keys(),
                                  est.filtered_points.buckets_min_points.values(), strict=True):
    for _ in range(int(min_pts)):
      x = rng.uniform(low, high)
      est.filtered_points.add_point(x, slope * x + rng.normal(0.0, 0.02))
  # top up the total round-robin: a single bucket caps at POINTS_PER_BUCKET, below min_points_total
  keys = list(est.filtered_points.buckets)
  i = 0
  while len(est.filtered_points) < est.min_points_total:
    x = rng.uniform(*keys[i % len(keys)])
    est.filtered_points.add_point(x, slope * x + rng.normal(0.0, 0.02))
    i += 1


def _clipped_factor(fingerprint, slope):
  est = TorqueEstimator(_torque_cp(fingerprint))
  est.starpilot_toggles = SimpleNamespace(use_custom_latAccelFactor=False, use_custom_friction=False)
  _fill_line(est, slope)
  captured = {}
  est.update_params = lambda params: captured.update(params)
  msg = est.get_msg()
  assert msg.liveTorqueParameters.liveValid
  return msg.liveTorqueParameters.latAccelFactorRaw, captured["latAccelFactor"]


def test_ioniq_6_learner_limits():
  est = TorqueEstimator(_torque_cp(HYUNDAI_CAR.HYUNDAI_IONIQ_6))
  assert est.lat_acc_threshold == IONIQ_6_LAT_ACC_THRESHOLD
  assert np.isclose(est.min_lataccel_factor, 3.0 * (1 - IONIQ_6_FACTOR_SANITY))
  assert np.isclose(est.max_lataccel_factor, 3.0 * (1 + IONIQ_6_FACTOR_SANITY))

  other = TorqueEstimator(_torque_cp(HYUNDAI_CAR.HYUNDAI_IONIQ_5))
  assert other.lat_acc_threshold == LAT_ACC_THRESHOLD
  assert np.isclose(other.max_lataccel_factor, 3.0 * (1 + FACTOR_SANITY))


def test_ioniq_6_post_tire_slope_is_not_clamped():
  raw, used = _clipped_factor(HYUNDAI_CAR.HYUNDAI_IONIQ_6, 4.4)
  assert abs(raw - 4.4) < 0.1
  assert abs(used - 4.4) < 0.1

  # the old +/-30% window (still used by every other car) pins the same data at 3.9
  _, used_other = _clipped_factor(HYUNDAI_CAR.HYUNDAI_IONIQ_5, 4.4)
  assert np.isclose(used_other, 3.0 * (1 + FACTOR_SANITY))


def test_cal_percent():
  est = TorqueEstimator(car.CarParams())
  est.starpilot_toggles = SimpleNamespace(use_custom_latAccelFactor=False, use_custom_friction=False)
  msg = est.get_msg()
  assert msg.liveTorqueParameters.calPerc == 0

  for (low, high), min_pts in zip(est.filtered_points.buckets.keys(),
                                  est.filtered_points.buckets_min_points.values(), strict=True):
    for _ in range(int(min_pts)):
      est.filtered_points.add_point((low + high) / 2.0, 0.0)

  # enough bucket points, but not enough total points
  msg = est.get_msg()
  assert msg.liveTorqueParameters.calPerc == (len(est.filtered_points) / est.min_points_total * 100 + 100) / 2

  # add enough points to bucket with most capacity
  key = list(est.filtered_points.buckets)[0]
  for _ in range(est.min_points_total - len(est.filtered_points)):
    est.filtered_points.add_point((key[0] + key[1]) / 2.0, 0.0)

  msg = est.get_msg()
  assert msg.liveTorqueParameters.calPerc == 100
