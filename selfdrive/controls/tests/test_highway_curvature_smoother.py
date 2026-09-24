import math
from types import SimpleNamespace

import numpy as np

from opendbc.car.hyundai.values import CAR as HYUNDAI_CAR
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.highway_curvature_smoother import HighwayCurvatureSmoother


_IONIQ_6 = SimpleNamespace(carFingerprint=HYUNDAI_CAR.HYUNDAI_IONIQ_6)
_OTHER = SimpleNamespace(carFingerprint=HYUNDAI_CAR.HYUNDAI_IONIQ_5)
_V_HWY = 31.0  # ~70 mph


def _run(smoother, curvature, v_ego=_V_HWY, lat_active=True, bypass=False):
  return np.array([smoother.update(float(c), v_ego, lat_active, bypass) for c in curvature])


def _weave(seconds=20.0, freq=0.6, lat_accel_amp=0.08, v_ego=_V_HWY, bias=0.0):
  t = np.arange(0.0, seconds, DT_CTRL)
  return bias + (lat_accel_amp / v_ego ** 2) * np.sin(2 * math.pi * freq * t)


def test_other_cars_pass_through():
  raw = _weave()
  out = _run(HighwayCurvatureSmoother(_OTHER), raw)
  np.testing.assert_array_equal(out, raw)


def test_straight_weave_is_attenuated():
  raw = _weave()
  out = _run(HighwayCurvatureSmoother(_IONIQ_6), raw)
  tail = slice(len(raw) // 2, None)  # after the weight has faded in
  assert np.std(out[tail]) < 0.8 * np.std(raw[tail])


def test_below_speed_gate_passes_through():
  v = 15.0  # ~34 mph
  raw = _weave(v_ego=v)
  out = _run(HighwayCurvatureSmoother(_IONIQ_6), raw, v_ego=v)
  np.testing.assert_allclose(out, raw, atol=1e-12)


def test_real_curve_is_not_delayed():
  # straight, then a highway curve ramping to 1.5 m/s^2 over 2 s
  t = np.arange(0.0, 20.0, DT_CTRL)
  lat = np.clip((t - 10.0) / 2.0, 0.0, 1.0) * 1.5
  raw = lat / _V_HWY ** 2
  out = _run(HighwayCurvatureSmoother(_IONIQ_6), raw)
  in_curve = lat > 0.6
  assert np.max(np.abs(out[in_curve] - raw[in_curve])) * _V_HWY ** 2 < 1e-3
  # reaches 0.6 m/s^2 no later than the raw command
  assert np.argmax(out * _V_HWY ** 2 >= 0.6) == np.argmax(in_curve)


def test_weight_does_not_modulate_at_weave_frequency():
  # weave peaks crossing the ON threshold must not make the weight oscillate
  smoother = HighwayCurvatureSmoother(_IONIQ_6)
  weights = []
  for c in _weave(lat_accel_amp=0.3):
    smoother.update(float(c), _V_HWY, True, False)
    weights.append(smoother.weight)
  tail = np.array(weights[len(weights) // 2:])
  assert np.ptp(tail) < 0.02


def test_bypass_and_reengage_have_no_step():
  raw = _weave(seconds=30.0)
  smoother = HighwayCurvatureSmoother(_IONIQ_6)
  out = []
  for i, c in enumerate(raw):
    bypass = 1000 <= i < 1500  # e.g. blinker held for 5 s
    out.append(smoother.update(float(c), _V_HWY, True, bypass))
  out = np.array(out)
  max_raw_step = np.max(np.abs(np.diff(raw)))
  assert np.max(np.abs(np.diff(out))) <= 1.5 * max_raw_step


def test_lat_inactive_resets_to_input():
  smoother = HighwayCurvatureSmoother(_IONIQ_6)
  _run(smoother, _weave(seconds=5.0))
  assert smoother.update(0.002, _V_HWY, False, False) == 0.002
  assert smoother.weight == 0.0
  assert smoother.filtered == 0.002
