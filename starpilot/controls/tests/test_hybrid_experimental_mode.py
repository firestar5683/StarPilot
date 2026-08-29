#!/usr/bin/env python3
import numpy as np
import pytest

from openpilot.starpilot.controls.lib.hybrid_experimental_mode import (
  HybridExperimentalMode,
  lerp,
)


class FakeLead:
  def __init__(self, status=False, d_rel=150.0, v_lead=0.0):
    self.status = status
    self.dRel = float(d_rel)
    self.vLead = float(v_lead)


class FakeModel:
  def __init__(self, velocity=None, position=None):
    self.velocity = type("Velocity", (), {"x": list(velocity)})() if velocity is not None else None
    self.position = type("Position", (), {"x": list(position)})() if position is not None else None


def make_controller(prev=0.0):
  controller = HybridExperimentalMode()
  controller.reset(prev)
  return controller


def run(controller, *, v_ego=20.0, v_cruise=30.0, lead=None, model=None, a_chill=0.5, a_exp=0.8, frames=80):
  lead = lead if lead is not None else FakeLead()
  if model is None:
    model = FakeModel(velocity=[v_ego] * 33, position=list(np.linspace(0.0, 100.0, 33)))
  result = 0.0
  should_stop = False
  for _ in range(frames):
    result, should_stop = controller.update(v_ego, v_cruise, lead, model, a_chill, a_exp)
  return result, should_stop


def test_update_returns_accel_and_should_stop_tuple():
  controller = make_controller()
  result = controller.update(20.0, 30.0, FakeLead(), FakeModel(velocity=[20.0] * 33), 0.5, 0.5)
  assert isinstance(result, tuple) and len(result) == 2
  assert isinstance(result[0], float)
  assert isinstance(result[1], bool)


def test_open_road_throttle_follows_chill_without_bias():
  # On open road with default bias, HEM yields to pure Chill MPC cruise.
  controller = make_controller()
  a, _ = run(controller, a_chill=0.5, a_exp=0.8)
  assert a == pytest.approx(0.5, abs=1e-3)


def test_throttle_uses_exp_bias():
  controller = make_controller()
  controller.set_tuning(0.5, 1.0)
  a, _ = run(controller, a_chill=0.5, a_exp=0.8)
  expected = 0.5 + max(0.0, 0.8 - 0.5) * 0.5
  assert a == pytest.approx(expected, abs=1e-3)
  assert a > 0.5


def test_green_light_departure_from_standstill():
  controller = make_controller(prev=-0.5)
  controller.set_tuning(0.5, 1.0)
  traj_v = np.linspace(0.0, 12.0, 33)
  traj_x = np.linspace(0.0, 45.0, 33)
  model = FakeModel(velocity=traj_v, position=traj_x)

  a, should_stop = run(controller, v_ego=0.0, v_cruise=20.0, model=model, a_chill=1.0, a_exp=1.5, frames=40)
  assert a > 1.0, f"Vehicle should depart promptly on green light, got {a}"
  assert not should_stop


def test_standstill_hold_at_red_light_without_lead():
  controller = make_controller(prev=0.0)
  traj_v = np.zeros(33)
  traj_x = np.zeros(33)
  model = FakeModel(velocity=traj_v, position=traj_x)

  a, should_stop = run(controller, v_ego=0.0, v_cruise=25.0, lead=FakeLead(status=False),
          model=model, a_chill=0.2, a_exp=-1.0, frames=40)
  assert a <= -0.4, f"Standstill brake must hold even when Chill cruise wants to go, got {a}"
  assert should_stop, "Standstill at a predicted stop must assert should_stop"


def test_red_light_high_speed_approach_braking():
  controller = make_controller(prev=0.0)
  traj_v = np.linspace(25.0, 0.0, 33)
  traj_x = np.linspace(0.0, 60.0, 33)
  model = FakeModel(velocity=traj_v, position=traj_x)

  a, _ = run(controller, v_ego=25.0, v_cruise=25.0, model=model, a_chill=0.5, a_exp=-2.0, frames=60)
  assert a <= -2.0, f"Stopping deceleration should be fully honored without dilution, got {a}"


def test_red_light_low_speed_roll_prevent_dilution():
  controller = make_controller(prev=-0.5)
  traj_v = np.linspace(0.8, 0.0, 33)
  traj_x = np.linspace(0.0, 3.0, 33)
  model = FakeModel(velocity=traj_v, position=traj_x)

  a, _ = run(controller, v_ego=0.8, v_cruise=20.0, model=model, a_chill=0.8, a_exp=-0.6, frames=30)
  assert a <= -0.55, f"Vision stop clamp must enforce stopping bite at low speeds, got {a}"


def test_vision_stop_does_not_dilute_brake_with_cruise_throttle():
  controller = make_controller(prev=0.0)
  model = FakeModel(velocity=list(np.linspace(20.0, 0.0, 33)))
  a, _ = run(controller, v_ego=20.0, v_cruise=20.0, lead=FakeLead(status=False),
             model=model, a_chill=0.8, a_exp=-2.5, frames=20)
  assert a <= -2.5, f"Cruise throttle must be locked out during a vision stop, got {a}"


def test_missing_or_corrupt_model_v2_fallbacks():
  controller = make_controller()
  model_none = FakeModel(velocity=None, position=None)
  a, _ = run(controller, lead=FakeLead(status=False), model=model_none, a_chill=0.5, a_exp=0.2)
  assert a > 0.35, "Controller should gracefully fallback when trajectory is None"

  model_empty = FakeModel(velocity=[], position=[])
  a, _ = run(controller, lead=FakeLead(status=False), model=model_empty, a_chill=0.6, a_exp=0.7)
  assert a > 0.55, "Controller should gracefully handle empty trajectory lists"


def test_nan_a_exp_falls_back_to_chill_channel():
  controller = make_controller(prev=0.0)
  model = FakeModel(velocity=[20.0] * 33, position=list(np.linspace(0.0, 100.0, 33)))
  a, _ = run(controller, model=model, a_chill=0.5, a_exp=float("nan"), frames=10)
  assert np.isfinite(a), f"NaN a_exp must never propagate, got {a}"
  assert 0.4 <= a <= 0.6, f"NaN a_exp should degrade to the Chill channel, got {a}"


def test_inf_a_exp_does_not_propagate():
  controller = make_controller(prev=0.0)
  model = FakeModel(velocity=[20.0] * 33, position=list(np.linspace(0.0, 100.0, 33)))
  for a_exp in (float("inf"), float("-inf")):
    controller.reset(0.0)
    a, _ = run(controller, model=model, a_chill=0.5, a_exp=a_exp, frames=10)
    assert np.isfinite(a), f"Non-finite a_exp={a_exp} must not propagate, got {a}"


def test_nan_a_chill_falls_back_to_last_target():
  controller = make_controller(prev=0.0)
  model = FakeModel(velocity=[20.0] * 33, position=list(np.linspace(0.0, 100.0, 33)))
  a, _ = run(controller, model=model, a_chill=float("nan"), a_exp=0.8, frames=10)
  assert np.isfinite(a), f"NaN a_chill must never propagate, got {a}"


def test_nan_in_trajectory_does_not_propagate():
  controller = make_controller(prev=0.0)
  v = [20.0] * 20 + [float("nan")] + [20.0] * 12
  model = FakeModel(velocity=v, position=list(np.linspace(0.0, 100.0, 33)))
  a, _ = run(controller, model=model, a_chill=0.5, a_exp=0.8, frames=10)
  assert np.isfinite(a), f"NaN trajectory must not propagate, got {a}"


def test_reset_rejects_non_finite_seed():
  controller = make_controller(prev=-1.5)
  controller.reset(float("nan"))
  assert controller.prev_a_target == 0.0


def test_reset_seeds_active_acceleration():
  controller = make_controller(prev=0.0)
  controller.reset(a_ego=-1.8)
  assert controller.prev_a_target == -1.8


def test_tuning_clamping():
  controller = make_controller()
  controller.set_tuning(5.0, 9.0)
  assert controller.HYBRID_EXP_BIAS == 1.0
  assert controller.VISION_BRAKE_SENSITIVITY == 2.0
  controller.set_tuning(-5.0, -1.0)
  assert controller.HYBRID_EXP_BIAS == -1.0
  assert controller.VISION_BRAKE_SENSITIVITY == 0.0


def test_slower_lead_closing_blends_vision_decel():
  controller = make_controller(prev=0.0)
  lead = FakeLead(status=True, d_rel=25.0, v_lead=5.0)
  model = FakeModel(velocity=list(np.linspace(15.0, 8.0, 33)))
  a, _ = run(controller, v_ego=15.0, v_cruise=20.0, lead=lead, model=model, a_chill=-0.4, a_exp=-0.6)
  assert a < -0.3, f"Closing on a slower lead must brake, got {a}"


def test_cut_in_emergency_braking_preserves_chill_floor():
  controller = make_controller(prev=0.0)
  cut_in_lead = FakeLead(status=True, d_rel=6.0, v_lead=10.0)
  model = FakeModel(velocity=[20.0] * 33)

  for _ in range(8):
    a, _ = controller.update(20.0, 25.0, cut_in_lead, model, a_chill=-3.2, a_exp=0.0)
  assert a <= -2.5, f"Emergency cut-in should preserve the Chill brake floor, got {a}"


def test_no_hard_brake_on_gentle_high_horizon_slowdown():
  # A gentle slowdown that KEEPS a high horizon speed (curve / slower traffic,
  # ends at 15 m/s) must NOT trigger hard stop-to-zero braking.
  controller = make_controller(prev=0.0)
  traj_v = np.linspace(20.0, 15.0, 33)
  traj_x = np.linspace(0.0, 100.0, 33)
  model = FakeModel(velocity=traj_v, position=traj_x)
  a, _ = run(controller, v_ego=20.0, v_cruise=20.0, lead=FakeLead(status=False),
          model=model, a_chill=0.0, a_exp=-0.1, frames=5)
  assert a > -0.5, f"Gentle high-horizon slowdown must not hard-brake, got {a}"


def test_lead_departure_releases_vision_latch():
  controller = make_controller(prev=-1.0)
  stop_model = FakeModel(velocity=np.zeros(33))
  for _ in range(5):
    controller.update(5.0, 25.0, FakeLead(status=False), stop_model, 0.0, -2.0)
  assert controller.w_vision > 0.3

  depart_model = FakeModel(velocity=[10.0] * 33)
  lead = FakeLead(status=True, d_rel=30.0, v_lead=8.0)
  a, should_stop = controller.update(0.3, 25.0, lead, depart_model, 0.5, 0.5)
  assert controller.w_vision == 0.0, "Lead departure must release the vision latch instantly"
  assert a > 0.0
  assert not should_stop


def test_should_stop_chill_handshake():
  controller = make_controller(prev=0.0)
  model = FakeModel(velocity=[20.0] * 33)
  a, should_stop = controller.update(20.0, 25.0, FakeLead(), model, 0.0, 0.0, should_stop_chill=True)
  assert should_stop, "should_stop_chill must propagate into the fused stop flag"


def test_should_stop_chill_engages_braking_regime_without_vision():
  controller = make_controller(prev=0.0)
  model = FakeModel(velocity=[20.0] * 33)
  a, should_stop = controller.update(20.0, 25.0, FakeLead(), model, 0.0, -1.5, should_stop_chill=True)
  assert controller.last_exp_dominant, "should_stop_chill must engage the braking regime"
  assert a == pytest.approx(-1.5, abs=1e-3), f"Must command exp braking on planner stop, got {a}"
  assert should_stop


def test_should_stop_exp_handshake():
  controller = make_controller(prev=0.0)
  model = FakeModel(velocity=[5.0] * 33)
  a, should_stop = controller.update(5.0, 25.0, FakeLead(), model, 0.0, 0.0, should_stop_exp=True)
  assert should_stop, "should_stop_exp must propagate into the fused stop flag"


def test_standstill_intent_asserts_should_stop():
  controller = make_controller(prev=0.0)
  model = FakeModel(velocity=np.zeros(33))
  a, should_stop = controller.update(0.3, 20.0, FakeLead(), model, 0.0, 0.0)
  assert should_stop, "Standstill intent at low speed must assert should_stop"


def test_no_should_stop_on_open_road():
  controller = make_controller(prev=0.0)
  model = FakeModel(velocity=[20.0] * 33)
  a, should_stop = controller.update(20.0, 25.0, FakeLead(), model, 0.5, 0.5)
  assert not should_stop, "Open road cruising must not assert should_stop"


def test_output_bounded_between_chill_and_exp():
  # Defense-in-depth invariant: HEM output must never exceed the more aggressive of
  # the two inputs, and can only dip below both via the intentional -0.6 standstill
  # anchor (which keeps the car planted at a predicted stop). This guarantees HEM can
  # never command something more aggressive than both Chill and Exp intended.
  controller = make_controller(prev=0.0)
  scenarios = [
    (20.0, 0.5, 0.8),      # both throttle
    (20.0, 0.5, -2.0),     # exp brakes, chill cruise
    (20.0, -3.0, -0.5),    # chill emergency, exp mild
    (20.0, -1.0, -1.8),    # both brake
    (0.3, 0.8, -1.0),      # standstill (anchor may engage)
    (0.3, 0.5, 1.2),       # departure
  ]
  for v_ego, a_chill, a_exp in scenarios:
    for traj in ([v_ego] * 33, list(np.linspace(max(v_ego, 1.0), 0.0, 33))):
      controller.reset(0.0)
      model = FakeModel(velocity=traj)
      a, _ = controller.update(v_ego, 25.0, FakeLead(), model, a_chill, a_exp)
      lo = min(a_chill, a_exp, -0.6)
      hi = max(a_chill, a_exp)
      assert lo - 1e-9 <= a <= hi + 1e-9, \
        f"v_ego={v_ego} a_chill={a_chill} a_exp={a_exp} -> a_out={a} outside [{lo}, {hi}]"

  # A positive Exp bias blends toward Exp but never overshoots the max of the two.
  controller.set_tuning(0.5, 1.0)
  controller.reset(0.0)
  model = FakeModel(velocity=[20.0] * 33)
  a, _ = controller.update(20.0, 25.0, FakeLead(), model, 0.5, 1.2)
  assert 0.5 - 1e-9 <= a <= 1.2 + 1e-9


def test_dropped_trajectory_at_crawl_does_not_phantom_brake():
  # Regression for the indexing fallback bug: if modelV2 drops frames or returns a
  # too-short/corrupt trajectory at crawling speed (0.8 < v_ego < 1.5), the fallback
  # must not fake a stop (v_short must only be trusted from a full trajectory).
  for traj in ([], [1.2] * 5):
    controller = make_controller(prev=0.0)
    model = FakeModel(velocity=traj)
    a, should_stop = controller.update(1.2, 20.0, FakeLead(), model, 0.3, 0.0)
    assert a > 0.0, f"Short trajectory must not phantom-brake at crawl, got {a}"
    assert not should_stop


def test_lead_departure_from_standstill_clears_anchor():
  # Regression for the standstill deadlock: stopped behind a lead with v_horizon≈0,
  # when the lead pulls away, departure must clear the anchor/latch immediately even
  # before the vision horizon visually extends past the stop threshold.
  controller = make_controller(prev=-1.0)
  stop_model = FakeModel(velocity=np.zeros(33))
  for _ in range(5):
    controller.update(0.3, 25.0, FakeLead(), stop_model, 0.0, -1.0, should_stop_exp=True)
  assert controller.w_vision > 0.3

  lead = FakeLead(status=True, d_rel=6.0, v_lead=6.0)  # lead accelerates away
  depart_model = FakeModel(velocity=np.zeros(33))      # horizon still ~0 (not yet registered)
  a, should_stop = controller.update(0.3, 25.0, lead, depart_model, 0.5, 0.3)
  assert controller.w_vision == 0.0
  assert not should_stop, "Lead departure must clear shouldStop despite v_horizon~=0"
  assert a > 0.0, "Standstill anchor must not fight a departing lead"


def test_last_exp_dominant_true_when_vision_braking():
  controller = make_controller(prev=0.0)
  model = FakeModel(velocity=list(np.linspace(20.0, 0.2, 33)), position=list(np.linspace(0.0, 40.0, 33)))
  run(controller, v_ego=20.0, v_cruise=25.0, lead=FakeLead(status=False),
      model=model, a_chill=0.0, a_exp=-3.0, frames=60)
  assert controller.last_exp_dominant


def test_last_exp_dominant_false_when_chill_brakes_for_lead():
  controller = make_controller(prev=0.0)
  lead = FakeLead(status=True, d_rel=5.0, v_lead=0.0)
  model = FakeModel(velocity=[15.0] * 33, position=list(np.linspace(0.0, 100.0, 33)))
  run(controller, v_ego=15.0, v_cruise=20.0, lead=lead, model=model, a_chill=-2.5, a_exp=1.0, frames=40)
  assert not controller.last_exp_dominant


def test_last_exp_dominant_false_at_neutral_cruise():
  controller = make_controller(prev=0.0)
  run(controller, a_chill=0.0, a_exp=0.05, frames=10)
  assert not controller.last_exp_dominant
