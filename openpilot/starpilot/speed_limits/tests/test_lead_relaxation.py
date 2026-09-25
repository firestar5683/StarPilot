"""Lead-drop easing uses qualified source and lead evidence in planner coordinates."""

import unittest
from dataclasses import replace

from openpilot.starpilot.speed_limits import lead_relaxation as lr
from openpilot.starpilot.speed_limits.acceptance import Authority, LongitudinalOwner, Mode, ObservationKind

SESSION = "drive"
GENERATION = "system-long-1"
MPH_TO_MS = 0.44704
POLICY = lr.Policy(
  minimum_ego_mps=20.0 * MPH_TO_MS,
  minimum_distance_m=30.0,
  minimum_headway_s=1.2,
  maximum_lead_deficit_mps=0.35,
  maximum_lead_brake_mps2=0.25,
  drop_guard_mps=0.001,
  overspeed_guard_mps=0.05,
  overspeed_breakpoints_mps=tuple(v * MPH_TO_MS for v in (0.0, 5.0, 10.0, 15.0)),
  deceleration_mps2=(0.7, 0.9, 1.15, 1.35),
)
SOURCE = lr.SourceEvidence(ObservationKind.VALID, True)
LEAD = lr.LeadEvidence(lr.LeadKind.VALID, True, True, 80.0, 21.0, 0.0)
PRIOR = lr.PriorApplied(SESSION, GENERATION, 25.0)
ACTIVE = Authority(Mode.LONGITUDINAL_ONLY, LongitudinalOwner.SYSTEM, False, True, False, False)


def relax(raw_cap=20.0, *, source=SOURCE, lead=LEAD, prior=PRIOR, ego=27.0,
          override=False, active=True, elapsed=0.05, generation=GENERATION):
  return lr.step(raw_cap, source=source, lead=lead, prior=prior, session_id=SESSION,
                 continuity_id=generation, ego_mps=ego, override_active=override,
                 active_path=active, elapsed_s=elapsed, policy=POLICY)


class LeadRelaxationTests(unittest.TestCase):
  def test_frozen_dt_trace_and_elapsed_semigroup(self):
    first = relax()
    self.assertEqual(first.status, "eased")
    self.assertEqual(first.cap_mps, 24.9325)
    second = relax(prior=first.next_prior)
    self.assertAlmostEqual(second.cap_mps, 24.865)
    one_long_step = relax(elapsed=0.1)
    self.assertAlmostEqual(one_long_step.cap_mps, second.cap_mps)
    self.assertGreaterEqual(second.cap_mps, 20.0)

  def test_missing_stale_or_braking_lead_returns_qualified_raw_cap(self):
    for lead in (
      lr.LeadEvidence(lr.LeadKind.ABSENT),
      lr.LeadEvidence(lr.LeadKind.UNKNOWN),
      lr.LeadEvidence(lr.LeadKind.STALE),
      replace(LEAD, present=False),
      replace(LEAD, tracking=False),
      replace(LEAD, distance_m=20.0),
      replace(LEAD, speed_mps=19.0),
      replace(LEAD, accel_mps2=-0.3),
    ):
      with self.subTest(lead=lead):
        result = relax(lead=lead)
        self.assertEqual(result.cap_mps, 20.0)
        self.assertEqual(result.next_prior.cap_mps, 20.0)

  def test_frozen_distance_speed_and_braking_boundary_order(self):
    for lead in (replace(LEAD, distance_m=32.4), replace(LEAD, speed_mps=19.65),
                 replace(LEAD, accel_mps2=-0.25)):
      self.assertEqual(relax(lead=lead).cap_mps, 24.9325)
    for lead in (replace(LEAD, distance_m=32.399), replace(LEAD, speed_mps=19.649),
                 replace(LEAD, accel_mps2=-0.251)):
      self.assertEqual(relax(lead=lead).cap_mps, 20.0)

  def test_source_unknown_stale_and_unqualified_fallback_suppress_cap(self):
    for source in (
      lr.SourceEvidence(ObservationKind.UNKNOWN, True),
      lr.SourceEvidence(ObservationKind.STALE, True),
      lr.SourceEvidence(ObservationKind.ABSENT, False),
      lr.SourceEvidence(ObservationKind.VALID, False),
    ):
      with self.subTest(source=source):
        result = relax(source=source)
        self.assertIsNone(result.cap_mps)
        self.assertIsNone(result.next_prior)
    fallback = relax(source=lr.SourceEvidence(ObservationKind.ABSENT, True))
    self.assertEqual(fallback.cap_mps, 20.0)
    self.assertEqual(fallback.status, "fallback_source")

  def test_no_cap_inactive_force_stop_and_override_reset_prior(self):
    for kwargs in ({"raw_cap": None}, {"active": False}, {"override": True}):
      with self.subTest(kwargs=kwargs):
        result = relax(**kwargs)
        self.assertIsNone(result.next_prior)
        self.assertEqual(result.cap_mps, 20.0 if kwargs.get("override") else None)
    resumed = relax(prior=None)
    self.assertEqual(resumed.cap_mps, 20.0)

  def test_prior_drive_or_control_generation_cannot_carry_over(self):
    for prior in (replace(PRIOR, session_id="other"), replace(PRIOR, continuity_id="previous-mode")):
      result = relax(prior=prior)
      self.assertEqual(result.status, "invalid_prior")
      self.assertEqual(result.cap_mps, 20.0)
      self.assertIsNone(result.next_prior)
    self.assertEqual(relax(prior=None, generation="new-mode").cap_mps, 20.0)

  def test_invalid_policy_lead_and_elapsed_do_not_ease(self):
    for lead, elapsed, policy in (
      (replace(LEAD, distance_m=float("nan")), 0.05, POLICY),
      (LEAD, -0.1, POLICY),
      (LEAD, float("nan"), POLICY),
      (LEAD, 0.05, replace(POLICY, deceleration_mps2=(0.7, -0.9, 1.15, 1.35))),
    ):
      result = lr.step(20.0, source=SOURCE, lead=lead, prior=PRIOR, session_id=SESSION,
                       continuity_id=GENERATION, ego_mps=27.0, override_active=False,
                       active_path=True, elapsed_s=elapsed, policy=policy)
      self.assertTrue(result.errors)
      self.assertEqual(result.cap_mps, 20.0)
      self.assertIsNone(result.next_prior)
    self.assertEqual(relax(elapsed=0.0).cap_mps, 25.0)
    self.assertEqual(relax(elapsed=100.0).cap_mps, 20.0)

  def test_native_planner_still_arbitrates_lead_e2e_and_force_decel(self):
    from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
    from openpilot.starpilot.longitudinal.cruise_ceiling import CruiseCeiling
    from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import V_EGO, messages, snapshot
    from opendbc.car.honda.interface import CarInterface
    from opendbc.car.honda.values import CAR

    cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    eased = relax(raw_cap=16.0, prior=lr.PriorApplied(SESSION, GENERATION, 17.0),
                  ego=20.0, lead=replace(LEAD, distance_m=80.0, speed_mps=17.0))
    self.assertIsNotNone(eased.cap_mps)
    statuses = {}
    for case in ("ordinary", "lead", "e2e", "force"):
      planner = LongitudinalPlanner(cp, init_v=V_EGO)
      for _ in range(40):
        sm, _ = messages(lead=case == "lead", e2e=case == "e2e", force=case == "force")
        planner.update(sm, cruise_ceiling=CruiseCeiling(eased.cap_mps, ACTIVE))
      statuses[case] = (planner.last_cruise_ceiling_status, snapshot(planner))
    self.assertEqual(statuses["ordinary"][0], "applied")
    self.assertEqual(statuses["lead"][0], "applied")
    self.assertEqual(statuses["e2e"][0], "applied")
    self.assertEqual(statuses["force"][0], "force_decel")
    self.assertLess(statuses["lead"][1][0], statuses["ordinary"][1][0])
    self.assertLess(statuses["e2e"][1][0], statuses["ordinary"][1][0])
    self.assertEqual(statuses["lead"][1][2], "1")
    self.assertEqual(statuses["e2e"][1][2], "4")


if __name__ == "__main__":
  unittest.main()
