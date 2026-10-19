from types import SimpleNamespace

import pytest

from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR
from openpilot.selfdrive.controls.lib import longitudinal_planner as planner_module
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.selfdrive.controls.lib.longitudinal_vehicle_tunes import (
  get_far_follow_output_slew_min_speed,
  is_kia_niro_ev_follow_lead,
)
from openpilot.selfdrive.controls.tests.test_longitudinal_planner import make_lead, make_sm, make_toggles


@pytest.mark.parametrize("brand,fingerprint", [
  ("hyundai", "KIA_NIRO_EV_2ND_GEN"),
  ("hyundai", "HYUNDAI_IONIQ_6"),
  ("hyundai", "KIA_EV9"),
  ("toyota", "TOYOTA_COROLLA_TSS2"),
  ("gm", "CHEVROLET_BOLT_EUV"),
  ("gm", "KIA_NIRO_EV"),
])
def test_follow_tune_does_not_apply_to_other_cars(brand, fingerprint):
  cp = SimpleNamespace(brand=brand, carFingerprint=fingerprint)
  lead = make_lead(status=True, d_rel=32.0, v_lead=8.5, model_prob=0.99)
  assert not is_kia_niro_ev_follow_lead(cp, lead, 9.3)
  assert get_far_follow_output_slew_min_speed(cp, 10.0) == 10.0


@pytest.mark.parametrize("speed,fields", [
  (9.3, {"status": False}),
  (9.3, {"radar": True}),
  (9.3, {"model_prob": 0.94}),
  (9.3, {"y_rel": 1.51}),
  (9.3, {"d_rel": 40.1}),
  (25.0, {"d_rel": 62.6}),
  (9.3, {"d_rel": 9.9}),
  (4.9, {}),
])
def test_follow_tune_excludes_uncertain_far_and_launch_leads(speed, fields):
  cp = SimpleNamespace(brand="hyundai", carFingerprint="KIA_NIRO_EV")
  values = dict(status=True, d_rel=32.0, v_lead=8.5, model_prob=0.99)
  values.update(fields)
  assert not is_kia_niro_ev_follow_lead(cp, make_lead(**values), speed)


@pytest.mark.parametrize("experimental,scene,expected", [
  (False, None, True),
  (True, None, False),
  (False, "forcingStop", False),
  (False, "redLight", False),
  (False, "stopSignConfirmed", False),
])
@pytest.mark.parametrize("lead_slot", ["lead_one", "lead_two"])
def test_follow_admission_keeps_scene_and_mode_selection_unchanged(monkeypatch, experimental, scene, expected, lead_slot):
  cp = CarInterface.get_non_essential_params(CAR.KIA_NIRO_EV)
  planner = LongitudinalPlanner(cp, init_v=9.3)
  lead = make_lead(status=True, d_rel=32.0, v_lead=8.5, a_lead=-0.3, model_prob=0.99)
  sm = make_sm(9.3, -0.3, -3.5, experimental_mode=experimental,
               tracking_lead=False, **{lead_slot: lead})
  if scene:
    setattr(sm["starpilotPlan"], scene, True)
  captured = []
  update = planner.mpc.update

  def capture(*args, **kwargs):
    captured.append(kwargs["tracking_lead"])
    return update(*args, **kwargs)

  monkeypatch.setattr(planner.mpc, "update", capture)
  planner.update(sm, make_toggles())

  assert captured == [expected]
  assert planner.mode == ("blended" if experimental else "acc")
  assert sm["selfdriveState"].experimentalMode is experimental
  assert not sm["starpilotPlan"].trackingLead
  if scene:
    assert getattr(sm["starpilotPlan"], scene)


def test_city_follow_slew_damps_pulses_but_preserves_urgent_targets():
  cp = CarInterface.get_non_essential_params(CAR.KIA_NIRO_EV)
  planner = LongitudinalPlanner(cp, init_v=9.3)
  planner.lead_one = make_lead(status=True, d_rel=32.0, v_lead=8.5, model_prob=0.99)
  planner.lead_two = make_lead(status=False)

  assert planner.far_follow_slew_min_speed == 5.0
  first = planner.get_vehicle_far_follow_slew_target(9.3, 0.0, -0.3, False, False)
  braking = planner.get_vehicle_far_follow_slew_target(9.3, first, -0.8, False, False)
  release = planner.get_vehicle_far_follow_slew_target(9.3, braking, 1.0, False, False)
  assert braking == pytest.approx(first - 2.0 * planner.dt)
  assert release == pytest.approx(braking + 1.25 * planner.dt)
  assert planner.get_vehicle_far_follow_slew_target(9.3, release, -3.5, False, True) == -3.5
  assert planner.get_vehicle_far_follow_slew_target(9.3, release, -3.5, True, False) == -3.5
  planner.lead_one.dRel = 12.0
  assert planner.get_vehicle_far_follow_slew_target(9.3, release, -3.5, False, False) == -3.5
  planner.lead_one.dRel = 32.0
  planner.lead_one.vLead = 4.0
  assert planner.get_vehicle_far_follow_slew_target(9.3, release, -3.5, False, False) == -3.5


def test_acc_follow_stays_active_across_raw_close_lead_threshold(monkeypatch):
  cp = CarInterface.get_non_essential_params(CAR.KIA_NIRO_EV)
  baseline = LongitudinalPlanner(cp, init_v=9.3)
  candidate = LongitudinalPlanner(cp, init_v=9.3)
  old_tracking, new_tracking = [], []

  def capture(mpc, values):
    update = mpc.update

    def record(*args, **kwargs):
      values.append(kwargs["tracking_lead"])
      return update(*args, **kwargs)

    monkeypatch.setattr(mpc, "update", record)

  capture(baseline.mpc, old_tracking)
  capture(candidate.mpc, new_tracking)
  for frame in range(20):
    monkeypatch.setattr(planner_module.time, "monotonic", lambda: 100.0 + frame * 0.05)
    lead = make_lead(status=True, d_rel=32.0,
                     v_lead=8.5, a_lead=-0.3 if frame % 2 else -0.6, model_prob=0.99)
    lead.aLeadTau = 0.3
    sm = make_sm(9.3, -0.3, -1.0, experimental_mode=False, tracking_lead=False, lead_one=lead)
    with monkeypatch.context() as old_gate:
      old_gate.setattr(planner_module, "is_kia_niro_ev_follow_lead", lambda *args: False)
      baseline.update(sm, make_toggles())
    candidate.update(sm, make_toggles())

  assert old_tracking == [True, False] * 10
  assert new_tracking == [True] * 20
