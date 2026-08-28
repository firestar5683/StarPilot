import sys
import types
from types import SimpleNamespace

from cereal import car, log, messaging
import numpy as np
import pytest

from opendbc.car.honda.values import CAR as HONDA_CAR
from openpilot.selfdrive.controls.controlsd import (
  TWITCH_GUARD_DURATION,
  limit_curvature_to_plan,
  twitch_guard_allowed,
  update_twitch_guard,
)
from openpilot.selfdrive.locationd import lagd
from openpilot.selfdrive.locationd.lagd import (
  ACCORD_11G_MIN_LAG,
  ACCORD_11G_MIN_VEGO,
  BLOCK_NUM_NEEDED,
  LateralLagEstimator,
  MAX_LAG,
  retrieve_initial_lag,
)


def _model(curvature: float = 0.0, reach: float = 20.0, lane_change: int = 0):
  xs = np.linspace(0.0, reach, 41)
  ys = 0.5 * curvature * xs ** 2
  return SimpleNamespace(
    position=SimpleNamespace(x=xs, y=ys),
    meta=SimpleNamespace(laneChangeState=lane_change),
  )


def _cp(fingerprint=HONDA_CAR.HONDA_ACCORD_11G, delay=0.3):
  return car.CarParams(brand="honda", carFingerprint=fingerprint, steerActuatorDelay=delay)


def _estimator(fingerprint=HONDA_CAR.HONDA_ACCORD_11G):
  estimator = LateralLagEstimator(_cp(fingerprint), 0.05)
  estimator.starpilot_toggles = SimpleNamespace(use_custom_steerActuatorDelay=False, steerActuatorDelay=0.0)
  return estimator


def test_native_takeoff_guard_rejects_only_straight_launch_spike():
  assert limit_curvature_to_plan(_model(0.0), 0.05, 1.0) == pytest.approx(0.002)
  assert limit_curvature_to_plan(_model(0.01), 0.015, 1.0) == pytest.approx(0.015)
  assert limit_curvature_to_plan(_model(0.08), 0.08, 1.0) == pytest.approx(0.08)


def test_native_takeoff_guard_fades_and_rearms_at_stop():
  assert limit_curvature_to_plan(_model(0.0), 0.05, 3.5) == pytest.approx(0.026)
  assert limit_curvature_to_plan(_model(0.0), 0.05, 4.0) == pytest.approx(0.05)
  remaining = update_twitch_guard(0.0, 0.0, True)
  assert remaining == pytest.approx(TWITCH_GUARD_DURATION)
  for _ in range(150):
    remaining = update_twitch_guard(remaining, 1.0, False)
  assert remaining == pytest.approx(0.0)


@pytest.mark.parametrize(
  ("blinker", "turn_hold", "lane_change", "expected"),
  [(False, False, False, True), (True, False, False, False),
   (False, True, False, False), (False, False, True, False)],
)
def test_accord_takeoff_guard_respects_maneuver_bypasses(blinker, turn_hold, lane_change, expected):
  assert twitch_guard_allowed(True, blinker, turn_hold, lane_change) is expected


def test_non_accord_guard_preserves_native_lane_change_behavior():
  assert twitch_guard_allowed(False, False, False, True)


def test_native_model_route_ignores_planplus_without_changing_default(monkeypatch):
  fake_commonmodel = types.ModuleType("openpilot.selfdrive.modeld.models.commonmodel_pyx")
  fake_commonmodel.DrivingModelFrame = object
  fake_commonmodel.CLContext = object
  monkeypatch.setitem(sys.modules, fake_commonmodel.__name__, fake_commonmodel)
  from openpilot.selfdrive.modeld import modeld
  from openpilot.selfdrive.modeld.constants import ModelConstants, Plan

  plan = np.zeros((1, ModelConstants.IDX_N, ModelConstants.PLAN_WIDTH), dtype=np.float32)
  planplus = np.ones_like(plan)
  captured = []
  monkeypatch.setattr(modeld, "get_accel_from_plan_tomb_raider", lambda *args, **kwargs: (0.0, False))

  def capture_curvature(_output, selected_plan, *_args, **_kwargs):
    captured.append(selected_plan.copy())
    return 0.0

  monkeypatch.setattr(modeld, "get_curvature_from_output", capture_curvature)
  previous = log.ModelDataV2.Action.new_message()
  toggles = SimpleNamespace(vEgoStopping=0.3, recovery_power=1.0)
  kwargs = dict(lat_action_t=0.2, long_action_t=0.5, v_ego=5.0, mlsim=True,
                is_v9=False, is_v14=False, is_v15=False, starpilot_toggles=toggles,
                lat_smooth_seconds=0.0, long_smooth_seconds=0.0)
  output = {"plan": plan, "planplus": planplus}
  modeld.get_action_from_model(output, previous, honda_accord_11g_lateral=True, **kwargs)
  modeld.get_action_from_model(output, previous, honda_accord_11g_lateral=False, **kwargs)
  np.testing.assert_allclose(captured[0], 0.0)
  np.testing.assert_allclose(captured[1][:, Plan.VELOCITY], 1.0)


def test_accord_delay_initialization_and_learning_scope():
  estimator = _estimator()
  assert estimator.honda_accord_11g_lateral
  assert estimator.initial_lag == pytest.approx(0.5)
  assert estimator.min_vego == pytest.approx(ACCORD_11G_MIN_VEGO)
  assert estimator.get_msg(True).liveDelay.lateralDelay == pytest.approx(0.5)


@pytest.mark.parametrize(("learned", "expected"), [(0.10, 0.15), (0.30, 0.30), (0.80, 0.65)])
def test_accord_published_delay_is_bounded(learned, expected):
  estimator = _estimator()
  estimator.block_avg.values[:] = learned
  estimator.block_avg.valid_blocks = BLOCK_NUM_NEEDED
  assert estimator.get_msg(True).liveDelay.lateralDelay == pytest.approx(expected)


def test_accord_ignores_custom_delay_while_generic_honda_is_unchanged():
  accord = _estimator()
  accord.starpilot_toggles = SimpleNamespace(use_custom_steerActuatorDelay=True, steerActuatorDelay=0.01)
  assert accord.get_msg(True).liveDelay.lateralDelay == pytest.approx(0.5)
  generic = _estimator(HONDA_CAR.HONDA_CRV_6G)
  generic.starpilot_toggles = SimpleNamespace(use_custom_steerActuatorDelay=True, steerActuatorDelay=0.27)
  assert not generic.honda_accord_11g_lateral
  assert generic.min_vego == pytest.approx(lagd.MIN_VEGO)
  assert generic.get_msg(True).liveDelay.lateralDelay == pytest.approx(0.27)


class FakeParams:
  def __init__(self, data):
    self.data = data
    self.removed = []

  def get(self, key):
    return self.data.get(key)

  def remove(self, key):
    self.removed.append(key)
    self.data.pop(key, None)


@pytest.mark.parametrize(("cached", "accepted"), [(0.15, True), (0.65, True), (0.149, False), (0.651, False)])
def test_accord_delay_cache_range_guard(cached, accepted):
  cp = _cp()
  event = messaging.new_message("liveDelay")
  event.liveDelay.status = "estimated"
  event.liveDelay.lateralDelayEstimate = cached
  event.liveDelay.validBlocks = 3
  params = FakeParams({"LiveDelay": event.to_bytes(), "CarParamsPrevRoute": cp.to_bytes()})
  result = retrieve_initial_lag(params, cp)
  if accepted:
    assert result == pytest.approx((cached, 3))
    assert not params.removed
  else:
    assert result is None
    assert params.removed == ["LiveDelay"]


def test_accord_delay_search_excludes_below_minimum_peak():
  dt = 0.05
  signal = np.sin(np.arange(400) * 0.17) + 0.3 * np.sin(np.arange(400) * 0.037)
  actual = np.roll(signal, 1)
  delay, _, _ = LateralLagEstimator.actuator_delay(signal, actual, np.ones(signal.size, dtype=bool), dt, MAX_LAG, ACCORD_11G_MIN_LAG)
  assert ACCORD_11G_MIN_LAG <= delay <= MAX_LAG
