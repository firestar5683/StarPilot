"""Niro comfort uses actual native lead/stop ownership and bypasses urgency."""
from unittest.mock import patch
import pytest

from opendbc.car import gen_empty_fingerprint
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.starpilot.longitudinal.niro_follow import NiroFarFollow, close_fast
from openpilot.starpilot.longitudinal.vehicle_policy import far_follow_owner
from openpilot.starpilot.longitudinal.tests.test_lead_approach_planner import Frame, DRIVE_NS


def params(candidate=CAR.KIA_NIRO_EV, *, active=True):
  return CarInterface.get_params(candidate, gen_empty_fingerprint(), [], active, False, False)


def frame(index=0, *, speed=9.3, distance=32., lead_speed=8.5):
  sm = Frame(index)
  sm['carState'].vEgo = speed
  for lead in (sm['radarState'].leadOne, sm['radarState'].leadTwo):
    lead.present = True
    lead.dRel, lead.vLead, lead.vLeadK, lead.yRel = distance, lead_speed, lead_speed, 0.
  sm['modelV2'].action.shouldStop = False
  return sm


def sample(owner, sm, target, previous=0., **overrides):
  return owner.sample(sm, now_ns=sm.now_ns, drive_id=DRIVE_NS, active=True, target=target,
                      previous_target=previous, follow_seconds=1.45, **overrides)


def test_original_scalar_first_frame_and_exact_brake_release_rates():
  owner = NiroFarFollow(.05)
  first = sample(owner, frame(0), -.3)
  assert first == -.3
  braking = sample(owner, frame(1), -.8, first)
  assert braking == pytest.approx(first - 2. * .05)
  release = sample(owner, frame(2), 1., braking)
  assert release == pytest.approx(braking + 1.25 * .05)
  for index, target in enumerate((-.9, -.1, -.8, .6), 3):
    expected = min(release + .0625, max(release - .1, target))
    assert sample(owner, frame(index), target, release) == pytest.approx(expected)
    release = expected


@pytest.mark.parametrize('candidate', [CAR.KIA_NIRO_EV_2ND_GEN, CAR.HYUNDAI_IONIQ_6, CAR.KIA_EV9, CAR.HYUNDAI_IONIQ_5])
def test_factory_sibling_and_ioniq_owners_unchanged(candidate):
  assert far_follow_owner(params(candidate), .05) is None


def test_exact_active_owner_and_no_stock_passive_or_foreign_brand():
  assert isinstance(far_follow_owner(params(), .05), NiroFarFollow)
  assert far_follow_owner(params(active=False), .05) is None
  for field, value in (('passive', True), ('dashcamOnly', True), ('notCar', True), ('brand', 'gm')):
    cp = params()
    setattr(cp, field, value)
    assert far_follow_owner(cp, .05) is None


@pytest.mark.parametrize('speed,distance,lead_speed,safe', [
  (4.99, 32., 4.99, False), (5., 32., 5., True),
  (9.3, 24.99, 9.3, False), (9.3, 25., 9.3, True),
  (30., 40.49, 30., False), (30., 40.5, 30., True),
  (20., 160., 0., True), (20., 159.99, 0., False),
])
def test_original_speed_distance_and_ttc_boundaries(speed, distance, lead_speed, safe):
  owner = NiroFarFollow(.05)
  sample(owner, frame(0, speed=speed, distance=distance, lead_speed=lead_speed), 0.)
  result = sample(owner, frame(1, speed=speed, distance=distance, lead_speed=lead_speed), -.8)
  assert owner.safe is safe
  assert result == pytest.approx(-.1 if safe else -.8)


@pytest.mark.parametrize('speed,lead_speed,distance,window', [(9.3, 6.3, 32., 36.845), (30., 27., 45., 94.2)])
def test_panic_overlap_bypasses_despite_safe_ttc_and_headway(speed, lead_speed, distance, window):
  sm = frame(1, speed=speed, lead_speed=lead_speed, distance=distance)
  lead = sm['radarState'].leadTwo
  assert distance / (speed - lead_speed) >= 8 and distance / speed >= 1.35
  assert (speed ** 2 - lead_speed ** 2) / 5 + 1.45 * speed + 6 + max(8, .35 * speed) == pytest.approx(window)
  assert close_fast(lead, speed, 1.45)
  owner = NiroFarFollow(.05)
  sample(owner, frame(0), 0.)
  sm['radarState'].leadOne.vLead = speed
  assert sample(owner, sm, -3.5) == -3.5
  assert not owner.safe


@pytest.mark.parametrize('defect', ['stale', 'future', 'gas', 'brake', 'stop', 'force', 'experimental', 'invalid', 'blocked'])
def test_withdrawal_bypasses_immediately_and_resets_first_eligible_frame(defect):
  owner = NiroFarFollow(.05)
  sample(owner, frame(0), 0.)
  sm = frame(1)
  if defect == 'stale':
    sm.logMonoTime['radarState'] = sm.now_ns - 250_000_001
  elif defect == 'future':
    sm.logMonoTime['modelV2'] = sm.now_ns + 1
  elif defect in ('gas', 'brake'):
    setattr(sm['carState'], defect + 'Pressed', True)
  elif defect == 'stop':
    sm['modelV2'].action.shouldStop = True
  elif defect == 'force':
    sm['controlsState'].forceDecel = True
  elif defect == 'experimental':
    sm['selfdriveState'].experimentalMode = True
  elif defect == 'invalid':
    sm.valid['carState'] = False
  assert sample(owner, sm, -3.5, blocked=defect == 'blocked') == -3.5
  assert not owner.safe
  assert sample(owner, frame(2), -.8) == -.8
  assert sample(owner, frame(3), 1.) == pytest.approx(.0625)


def test_new_drive_and_repeated_model_do_not_inherit_slew_state():
  owner = NiroFarFollow(.05)
  sm = frame(0)
  sample(owner, sm, 0.)
  assert sample(owner, sm, -.8) == -.8
  sample(owner, frame(1), 0.)
  assert sample(owner, frame(2), -.8) == pytest.approx(-.1)
  sm = frame(3)
  assert owner.sample(sm, now_ns=sm.now_ns, drive_id=DRIVE_NS + 1, active=True,
                      target=-.8, previous_target=0., follow_seconds=1.45) == -.8


def test_actual_planner_final_target_and_both_present_mpc_obstacles():
  cp = params()
  planner = LongitudinalPlanner(cp, init_v=9.3)
  owner = planner.vehicle_far_follow
  assert isinstance(owner, NiroFarFollow)
  captured = []
  actual = owner.sample

  def record(sm, **kwargs):
    result = actual(sm, **kwargs)
    captured.append((kwargs, result))
    return result

  with patch.object(owner, 'sample', side_effect=record), patch.object(planner.mpc, 'process_lead', wraps=planner.mpc.process_lead) as leads:
    for index in range(6):
      sm = frame(index)
      sm['radarState'].leadOne.aLeadK = -.3 if index % 2 else -.6
      sm['radarState'].leadTwo.aLeadK = -.1
      planner.update(sm, now_ns=sm.now_ns, drive_id=DRIVE_NS)
      assert planner.mpc.solution_status == 0
      assert planner.output_a_target == pytest.approx(captured[-1][1])
      assert leads.call_count == 2 * (index + 1)
      assert leads.call_args_list[-2].args[0].present and leads.call_args_list[-1].args[0].present
  assert len(captured) == 6 and owner.safe
  first, result = captured[0]
  assert result == first['target']
  for kwargs, result in captured[1:]:
    assert result == pytest.approx(min(kwargs['previous_target'] + .0625, max(kwargs['previous_target'] - .1, kwargs['target'])))
