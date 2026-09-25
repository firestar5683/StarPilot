"""Offset and coordinate composition through actual acceptance and override decisions."""

import unittest
from dataclasses import replace
from typing import Any, cast

from openpilot.starpilot.speed_limits import acceptance as acc
from openpilot.starpilot.speed_limits import action_arbitration as arb
from openpilot.starpilot.speed_limits import overrides as ov
from openpilot.starpilot.speed_limits import speed_domain as sd

SESSION = "coordinates"
ACTIVE = acc.Authority(acc.Mode.LONGITUDINAL_ONLY, acc.LongitudinalOwner.SYSTEM, False, True, False, False)
POLICY = acc.Policy(confirm_lower=False, confirm_higher=False, fallback_previous=True)
SCHEDULE = sd.OffsetSchedule((sd.OffsetBand(0.0, None, 2.0),))
PEDAL_OFF = ov.PedalEvidence(ov.EvidenceKind.VALID, False)


def candidate(speed: float) -> acc.Candidate:
  return acc.Candidate("map", acc.ObservationIdentity(acc.IdentityKind.GEOGRAPHIC, value=f"road-{speed}"), speed)


class SpeedDomainTests(unittest.TestCase):
  def setUp(self):
    self.accepted = acc.step(acc.new_session(SESSION), acc.Observation(acc.ObservationKind.VALID, candidate(20.0)),
                             ACTIVE, POLICY, now_ns=0)
    self.state = ov.new_session(SESSION)

  def decision(self, now: int, *, speed: float = 20.0, source: acc.ObservationKind = acc.ObservationKind.VALID):
    observed = acc.Observation(source, candidate(speed) if source is acc.ObservationKind.VALID else None)
    self.accepted = acc.step(self.accepted.state, observed, ACTIVE, POLICY, now_ns=now)

  def frame(self, now: int, *, selected_raw: float = 20.0, selected_cluster: float | None = None,
            ego_raw: float = 20.0, ego_cluster: float | None = None,
            pedal: bool = False, change: arb.ClassifiedChange | None = None,
            schedule: sd.OffsetSchedule = SCHEDULE):
    selected_cluster = selected_raw if selected_cluster is None else selected_cluster
    ego_cluster = ego_raw if ego_cluster is None else ego_cluster
    domain = sd.resolve(self.accepted, schedule,
                        sd.SpeedPair(sd.DomainStatus.VALID, selected_raw, selected_cluster, SESSION, now),
                        sd.SpeedPair(sd.DomainStatus.VALID, ego_raw, ego_cluster, SESSION, now))
    self.assertEqual(domain.status, sd.DomainStatus.VALID)
    assert domain.context is not None
    override = ov.step(self.state, self.accepted, ACTIVE, POLICY, ov.SelectedEvidence(ov.EvidenceKind.VALID, selected_raw),
                       ov.PedalEvidence(ov.EvidenceKind.VALID, pedal, ego_raw), now_ns=now, change=change, domain=domain)
    self.state = override.state
    self.assertFalse(override.errors)
    coordinate = sd.to_planner_coordinate(domain.context, override.contribution_mps, override.basis)
    return override, coordinate

  def intent(self, now: int, old: float, new: float, context: ov.Context, effect: int = 1):
    return arb.ClassifiedChange(SESSION, effect, effect, context.context_id, context.issued_at_ns,
                                old, new, arb.Disposition.DRIVER_INTENT)

  def test_offset_and_deltas_apply_once(self):
    _, base = self.frame(0, selected_raw=30.0, selected_cluster=31.0, ego_raw=25.0, ego_cluster=26.0)
    self.assertEqual(base.cap_mps, 21.0)
    self.decision(1)
    _, pedal = self.frame(1, selected_raw=30.0, selected_cluster=31.0, ego_raw=25.0, ego_cluster=26.0, pedal=True)
    self.assertEqual(pedal.cap_mps, 25.0)
    self.assertEqual(pedal.cluster_target_mps, 26.0)

  def test_effective_threshold_blocks_early_intent_and_cluster_only_pedal_can_cross(self):
    offset_three = sd.OffsetSchedule((sd.OffsetBand(0.0, None, 3.0),))
    first, _ = self.frame(0, selected_raw=20.0, ego_raw=20.0, schedule=offset_three)
    self.decision(1)
    effect = self.intent(1, 20.0, 22.0, first.context)
    armed, _ = self.frame(1, selected_raw=22.0, ego_raw=22.0, change=effect, schedule=offset_three)
    self.assertTrue(armed.event_receipt.consumed)
    self.assertIsNone(armed.state.persistent_selected_mps)  # 22 is below the effective 23 target.
    self.decision(2)
    raw_below, _ = self.frame(2, selected_raw=22.0, ego_raw=21.0, ego_cluster=21.5, pedal=True, schedule=offset_three)
    self.assertIsNone(raw_below.contribution_mps)
    self.decision(3)
    cluster_above, result = self.frame(3, selected_raw=22.0, ego_raw=21.0, ego_cluster=24.0,
                                       pedal=True, schedule=offset_three)
    self.assertEqual(cluster_above.contribution_mps, 21.0)
    self.assertEqual(result.cap_mps, 21.0)

  def test_selected_kph_conversion_and_offset_change_rotates_without_rearming(self):
    pair = sd.selected_pair_from_kph(20.0, 75.6, session_id=SESSION, timestamp_ns=0)
    self.assertEqual(pair.status, sd.DomainStatus.VALID)
    assert pair.cluster_mps is not None
    self.assertAlmostEqual(pair.cluster_mps, 21.0)
    first, _ = self.frame(0)
    self.decision(1)
    larger = sd.OffsetSchedule((sd.OffsetBand(0.0, None, 3.0),))
    changed, coordinate = self.frame(1, schedule=larger)
    self.assertNotEqual(changed.context.context_id, first.context.context_id)
    self.assertIsNone(changed.state.persistent_selected_mps)
    self.assertEqual(coordinate.cap_mps, 23.0)

  def test_negative_offset_can_retain_raw_intent_below_raw_accepted_limit(self):
    lower = sd.OffsetSchedule((sd.OffsetBand(0.0, None, -5.0),))
    first, _ = self.frame(0, schedule=lower)
    self.decision(1)
    effect = self.intent(1, 20.0, 18.0, first.context)
    armed, _ = self.frame(1, selected_raw=18.0, schedule=lower, change=effect)
    self.assertEqual(armed.state.persistent_selected_mps, 18.0)
    self.decision(2)
    retained, _ = self.frame(2, selected_raw=18.0, schedule=lower)
    self.assertEqual(retained.contribution_mps, 18.0)

  def test_cluster_delta_jitter_does_not_rotate_causal_context(self):
    first, _ = self.frame(0, selected_raw=20.0, selected_cluster=20.5)
    self.decision(1)
    changed, _ = self.frame(1, selected_raw=20.0, selected_cluster=20.6)
    self.assertEqual(changed.context.context_id, first.context.context_id)

  def test_mismatched_domain_resets_and_clears_intent(self):
    first, _ = self.frame(0)
    self.decision(1)
    effect = self.intent(1, 20.0, 25.0, first.context)
    self.frame(1, selected_raw=25.0, change=effect)
    self.decision(2)
    mismatched = sd.resolve(self.accepted, SCHEDULE, sd.SpeedPair(sd.DomainStatus.VALID, 24.0, 24.0, SESSION, 2),
                            sd.SpeedPair(sd.DomainStatus.VALID, 20.0, 20.0, SESSION, 2))
    bad = ov.step(self.state, self.accepted, ACTIVE, POLICY, ov.SelectedEvidence(ov.EvidenceKind.VALID, 25.0),
                  PEDAL_OFF, now_ns=2, domain=mismatched)
    self.assertTrue(bad.errors)
    self.assertTrue(bad.state.reset_required)
    self.assertIsNone(bad.state.persistent_selected_mps)

  def test_pair_from_another_frame_cannot_bind_to_acceptance(self):
    stale_frame = sd.resolve(self.accepted, SCHEDULE,
                             sd.SpeedPair(sd.DomainStatus.VALID, 20.0, 20.0, SESSION, 1),
                             sd.SpeedPair(sd.DomainStatus.VALID, 20.0, 20.0, SESSION, 0))
    self.assertEqual(stale_frame.status, sd.DomainStatus.INVALID)
    foreign = sd.resolve(self.accepted, SCHEDULE,
                         sd.SpeedPair(sd.DomainStatus.VALID, 20.0, 20.0, "other", 0),
                         sd.SpeedPair(sd.DomainStatus.VALID, 20.0, 20.0, SESSION, 0))
    self.assertEqual(foreign.status, sd.DomainStatus.INVALID)

  def test_nonvalid_domain_status_cannot_smuggle_a_valid_context(self):
    valid = sd.resolve(self.accepted, SCHEDULE,
                       sd.SpeedPair(sd.DomainStatus.VALID, 20.0, 20.0, SESSION, 0),
                       sd.SpeedPair(sd.DomainStatus.VALID, 20.0, 20.0, SESSION, 0))
    assert valid.context is not None
    for status in (sd.DomainStatus.STALE, sd.DomainStatus.UNKNOWN):
      with self.subTest(status=status):
        forged = sd.DomainResolution(status, valid.context)
        result = ov.step(ov.new_session(SESSION), self.accepted, ACTIVE, POLICY,
                         ov.SelectedEvidence(ov.EvidenceKind.VALID, 20.0), PEDAL_OFF, now_ns=0, domain=forged)
        self.assertTrue(result.errors)
        self.assertTrue(result.state.reset_required)
        self.assertIsNone(result.contribution_mps)

  def test_malformed_nested_acceptance_and_policy_return_invalid(self):
    pair = sd.SpeedPair(sd.DomainStatus.VALID, 20.0, 20.0, SESSION, 0)
    cases = (
      replace(self.accepted, state=replace(self.accepted.state, accepted="bad")),
      replace(self.accepted, state=replace(self.accepted.state,
                                           accepted=acc.AcceptedLimit(cast(Any, "bad"), SESSION, 0))),
      replace(self.accepted, state=replace(self.accepted.state, observation="bad")),
      replace(self.accepted, policy=replace(POLICY, display_only=True)),
      replace(self.accepted, policy=replace(POLICY, fallback_previous="bad")),
      replace(self.accepted, state=replace(self.accepted.state, observation=acc.Observation(acc.ObservationKind.STALE))),
    )
    for decision in cases:
      with self.subTest(decision=decision):
        result = sd.resolve(decision, SCHEDULE, pair, pair)
        self.assertEqual(result.status, sd.DomainStatus.INVALID)
        self.assertIsNone(result.context)

  def test_cluster_measurements_below_raw_clamp_both_deltas_to_zero(self):
    _, coordinate = self.frame(0, selected_raw=20.0, selected_cluster=19.0,
                               ego_raw=20.0, ego_cluster=19.0)
    self.assertEqual(coordinate.cap_mps, 22.0)
    self.assertEqual(coordinate.ego_delta_mps, 0.0)

  def test_adoption_clears_retained_intent_before_domain_conversion(self):
    first, _ = self.frame(0)
    self.decision(1)
    effect = self.intent(1, 20.0, 25.0, first.context)
    self.frame(1, selected_raw=25.0, change=effect)
    shown = self.accepted.state.presentation
    assert shown is not None
    request = acc.AdoptRequest(SESSION, 2, shown.presentation_id, shown.candidate)
    self.accepted = acc.step(self.accepted.state, acc.Observation(acc.ObservationKind.VALID, candidate(20.0)),
                             ACTIVE, POLICY, now_ns=2, adopt=request)
    adopted, coordinate = self.frame(2, selected_raw=25.0)
    self.assertIsNone(adopted.state.persistent_selected_mps)
    self.assertIsNone(adopted.contribution_mps)
    self.assertEqual(coordinate.cap_mps, 22.0)

  def test_retained_raw_intent_uses_current_delta_not_current_selected_value(self):
    first, _ = self.frame(0, selected_raw=20.0, ego_raw=20.0)
    self.decision(1)
    effect = self.intent(1, 20.0, 30.0, first.context)
    armed, _ = self.frame(1, selected_raw=30.0, selected_cluster=31.0, ego_raw=20.0, change=effect)
    self.assertEqual(armed.state.persistent_selected_mps, 30.0)
    self.decision(2)
    retained, coordinate = self.frame(2, selected_raw=28.0, selected_cluster=29.0, ego_raw=25.0, ego_cluster=26.0)
    self.assertEqual(retained.contribution_mps, 30.0)
    self.assertEqual(coordinate.cluster_target_mps, 31.0)
    self.assertEqual(coordinate.cap_mps, 30.0)

  def test_effective_target_catches_intent_and_rotates_origin(self):
    first, _ = self.frame(0)
    self.decision(1)
    effect = self.intent(1, 20.0, 24.0, first.context)
    armed, _ = self.frame(1, selected_raw=24.0, change=effect)
    self.assertEqual(armed.state.persistent_selected_mps, 24.0)
    self.decision(2, speed=23.0)
    caught, coordinate = self.frame(2, selected_raw=24.0)
    self.assertIsNone(caught.state.persistent_selected_mps)
    self.assertNotEqual(caught.context.context_id, first.context.context_id)
    self.assertEqual(coordinate.cap_mps, 25.0)

  def test_offset_catches_intent_and_reduction_does_not_restore_it(self):
    first, _ = self.frame(0)
    self.decision(1)
    self.frame(1, selected_raw=24.0, change=self.intent(1, 20.0, 24.0, first.context))
    self.decision(2)
    caught, _ = self.frame(2, selected_raw=24.0, schedule=sd.OffsetSchedule((sd.OffsetBand(0.0, None, 5.0),)))
    self.assertIsNone(caught.state.persistent_selected_mps)
    self.decision(3)
    reduced, coordinate = self.frame(3, selected_raw=24.0, schedule=sd.OffsetSchedule((sd.OffsetBand(0.0, None, 1.0),)))
    self.assertIsNone(reduced.contribution_mps)
    self.assertIsNone(reduced.state.persistent_selected_mps)
    self.assertEqual(coordinate.cap_mps, 21.0)

  def test_absent_fallback_and_unavailable_pair(self):
    self.frame(0)
    self.decision(1, source=acc.ObservationKind.ABSENT)
    fallback, coordinate = self.frame(1)
    self.assertEqual(fallback.state.accepted_mps, 20.0)
    self.assertEqual(coordinate.cap_mps, 22.0)
    self.decision(2)
    unavailable = sd.resolve(self.accepted, SCHEDULE, sd.SpeedPair(sd.DomainStatus.STALE),
                             sd.SpeedPair(sd.DomainStatus.VALID, 20.0, 20.0, SESSION, 2))
    self.assertEqual(unavailable.status, sd.DomainStatus.UNAVAILABLE)
    suppressed = ov.step(self.state, self.accepted, ACTIVE, POLICY, ov.SelectedEvidence(ov.EvidenceKind.VALID, 20.0),
                         PEDAL_OFF, now_ns=2, domain=unavailable)
    self.assertIsNone(suppressed.contribution_mps)
    self.assertIsNone(suppressed.context)

  def test_system_cap_is_denied_outside_active_system_longitudinal_mode(self):
    authorities = (
      acc.Authority(acc.Mode.OFF, acc.LongitudinalOwner.NONE, False, False, False, True),
      acc.Authority(acc.Mode.LATERAL_ONLY, acc.LongitudinalOwner.NONE, True, False, False, False),
      acc.Authority(acc.Mode.LONGITUDINAL_ONLY, acc.LongitudinalOwner.STOCK, False, False, True, False),
    )
    for authority in authorities:
      with self.subTest(authority=authority):
        accepted = acc.step(acc.new_session(SESSION), acc.Observation(acc.ObservationKind.VALID, candidate(20.0)),
                            authority, POLICY, now_ns=0)
        domain = sd.resolve(accepted, SCHEDULE, sd.SpeedPair(sd.DomainStatus.VALID, 25.0, 26.0, SESSION, 0),
                            sd.SpeedPair(sd.DomainStatus.VALID, 20.0, 21.0, SESSION, 0))
        self.assertEqual(domain.status, sd.DomainStatus.UNAVAILABLE)
        result = ov.step(ov.new_session(SESSION), accepted, authority, POLICY,
                         ov.SelectedEvidence(ov.EvidenceKind.VALID, 25.0), PEDAL_OFF, now_ns=0, domain=domain)
        self.assertIsNone(result.contribution_mps)
        self.assertIsNone(result.context)

  def test_composed_cap_reaches_native_planner_once(self):
    from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
    from openpilot.starpilot.longitudinal.cruise_ceiling import CruiseCeiling
    from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import V_EGO, message_bytes, messages, snapshot
    from opendbc.car.honda.interface import CarInterface
    from opendbc.car.honda.values import CAR

    self.accepted = acc.step(acc.new_session(SESSION), acc.Observation(acc.ObservationKind.VALID, candidate(15.0)),
                             ACTIVE, POLICY, now_ns=0)
    _, coordinate = self.frame(0, selected_raw=25.0, selected_cluster=26.0, ego_raw=20.0, ego_cluster=21.0)
    self.assertEqual(coordinate.cap_mps, 16.0)  # accepted 15 + offset 2 - ego delta 1
    cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    ordinary = LongitudinalPlanner(cp, init_v=V_EGO)
    composed = LongitudinalPlanner(cp, init_v=V_EGO)
    for _ in range(40):
      left, left_envelopes = messages()
      right, right_envelopes = messages()
      for sm in (left, right):
        sm['carState'].vCruise = 25.0 * 3.6
        sm['carState'].vCruiseCluster = 26.0 * 3.6
        sm['carState'].vEgoCluster = 21.0
      before = message_bytes((*left_envelopes, *right_envelopes))
      ordinary.update(left)
      composed.update(right, cruise_ceiling=CruiseCeiling(coordinate.cap_mps, ACTIVE))
      self.assertEqual(before, message_bytes((*left_envelopes, *right_envelopes)))
      self.assertEqual(ordinary.mpc.solution_status, 0)
      self.assertEqual(composed.mpc.solution_status, 0)
    self.assertEqual(ordinary.last_cruise_ceiling_status, "absent")
    self.assertEqual(composed.last_cruise_ceiling_status, "applied")
    self.assertNotEqual(snapshot(ordinary), snapshot(composed))


if __name__ == "__main__":
  unittest.main()
