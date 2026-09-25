import itertools
import math
import unittest
from dataclasses import FrozenInstanceError, replace
from typing import Any, cast

from openpilot.starpilot.speed_limits.acceptance import (
  CONFIRMATION_NS, MAX_REJECTIONS, AcceptedLimit, ActionKind, AdoptRequest, Authority, Candidate, DriverAction,
  IdentityKind, LongitudinalOwner, Mode, Observation, ObservationIdentity, ObservationKind, Policy, State, new_session, step,
)

NS = 1_000_000_000


def geographic(value: str) -> ObservationIdentity:
  return ObservationIdentity(IdentityKind.GEOGRAPHIC, value=value)


HIGH = Candidate("dashboard", geographic("road-1"), 29.0576)
LOW = Candidate("dashboard", geographic("road-2"), 20.1168)
ACTIVE = Authority(Mode.LONGITUDINAL_ONLY, LongitudinalOwner.SYSTEM, False, True, False, False)
PAUSED = replace(ACTIVE, longitudinal_active=False)
DISENGAGED = replace(PAUSED, fully_disengaged=True)
ABSENT = Observation(ObservationKind.ABSENT)
DEFAULT_POLICY = Policy()


def valid(candidate: Candidate) -> Observation:
  return Observation(ObservationKind.VALID, candidate)


def saved(candidate: Candidate = HIGH) -> State:
  return new_session("drive", AcceptedLimit(candidate, "previous-drive", 0))


class TestAcceptance(unittest.TestCase):
  def test_vision_requires_current_driver_confirmation_across_disengage_and_source_loss(self):
    policy = Policy(confirm_lower=False, confirm_higher=False, fallback_previous=True,
                    vision_driver_confirm=True)
    first_sign = Candidate('vision', ObservationIdentity(IdentityKind.PRODUCER_EPISODE,
                                                         value='drive:ioniq:camera:1'), 22.0)
    next_sign = replace(first_sign, observation_identity=ObservationIdentity(
      IdentityKind.PRODUCER_EPISODE, value='drive:ioniq:camera:2'), speed_mps=17.0)
    stopped = step(new_session('drive'), valid(first_sign), DISENGAGED, policy, now_ns=0)
    self.assertIsNone(stopped.history_write)
    self.assertIsNone(stopped.state.accepted)
    engaged = step(stopped.state, valid(first_sign), ACTIVE, policy, now_ns=NS)
    self.assertEqual(engaged.basis, 'pending')
    self.assertIsNone(engaged.control_target_mps)
    action = DriverAction('drive', 1, engaged.state.pending.decision_id, ActionKind.ACCEPT)
    confirmed = step(engaged.state, valid(first_sign), ACTIVE, policy, now_ns=2 * NS, action=action)
    self.assertEqual(confirmed.basis, 'driver_accept')
    self.assertEqual(confirmed.control_target_mps, 22.0)
    continued = step(confirmed.state, valid(first_sign), ACTIVE, policy, now_ns=3 * NS)
    self.assertEqual(continued.control_target_mps, 22.0)
    changed = step(continued.state, valid(next_sign), ACTIVE, policy, now_ns=4 * NS)
    self.assertIsNone(changed.control_target_mps)
    self.assertIsNone(changed.state.accepted)
    lost = step(changed.state, Observation(ObservationKind.STALE), ACTIVE, policy, now_ns=5 * NS)
    returned = step(lost.state, valid(first_sign), ACTIVE, policy, now_ns=6 * NS)
    self.assertEqual(returned.basis, 'pending')
    self.assertIsNone(returned.control_target_mps)

  def pending(self, candidate=LOW, authority=ACTIVE, policy=DEFAULT_POLICY, state=None, now_ns=0):
    decision = step(saved() if state is None else state, valid(candidate), authority, policy, now_ns=now_ns)
    self.assertEqual(decision.errors, ())
    self.assertIsNotNone(decision.state.pending)
    return decision

  def act(self, state, kind, *, now_ns=NS, sequence=0, authority=ACTIVE, policy=DEFAULT_POLICY):
    self.assertIsNotNone(state.pending)
    action = DriverAction(state.session_id, sequence, state.pending.decision_id, kind)
    return step(state, state.observation, authority, policy, now_ns=now_ns, action=action)

  def adopt_request(self, state, sequence=0):
    self.assertIsNotNone(state.presentation)
    return AdoptRequest(state.session_id, sequence, state.presentation.presentation_id, state.presentation.candidate)

  def test_reject_then_source_loss_never_activates_rejected_limit(self):
    policy = Policy(fallback_previous=True)
    initial = step(new_session("drive"), valid(HIGH), DISENGAGED, policy, now_ns=0)
    self.assertEqual(initial.history_write.candidate, HIGH)
    proposed = self.pending(state=initial.state, policy=policy, now_ns=NS)
    self.assertEqual(proposed.control_target_mps, HIGH.speed_mps)
    rejected = self.act(proposed.state, ActionKind.REJECT, policy=policy, now_ns=2 * NS)
    lost = step(rejected.state, ABSENT, ACTIVE, policy, now_ns=3 * NS)
    returned = step(lost.state, valid(LOW), ACTIVE, policy, now_ns=4 * NS)
    for decision in (rejected, lost, returned):
      self.assertEqual(decision.control_target_mps, HIGH.speed_mps)
      self.assertEqual(decision.state.accepted, initial.history_write)
      self.assertIsNone(decision.state.pending)
      self.assertIsNone(decision.history_write)
      self.assertIn(LOW, decision.state.rejected)
    self.assertTrue(rejected.action_receipt.consumed)
    self.assertEqual(returned.basis, "rejected")

  def test_absence_fallback_is_explicit_unknown_and_stale_suppress_it(self):
    for kind, fallback in itertools.product((ObservationKind.ABSENT, ObservationKind.UNKNOWN, ObservationKind.STALE), (False, True)):
      with self.subTest(kind=kind, fallback=fallback):
        result = step(saved(), Observation(kind), ACTIVE, Policy(fallback_previous=fallback), now_ns=0)
        self.assertEqual(result.control_target_mps, HIGH.speed_mps if kind is ObservationKind.ABSENT and fallback else None)
        self.assertIsNone(result.display_candidate)
        self.assertIsNone(result.history_write)
    result = step(new_session("drive"), ABSENT, ACTIVE, Policy(fallback_previous=True), now_ns=0)
    self.assertIsNone(result.control_target_mps)

  def test_unknown_stale_and_absence_clear_pending_and_restart_decision_identity(self):
    for kind in (ObservationKind.UNKNOWN, ObservationKind.STALE, ObservationKind.ABSENT):
      with self.subTest(kind=kind):
        before = self.pending()
        missing = step(before.state, Observation(kind), ACTIVE, Policy(), now_ns=NS)
        after = self.pending(state=missing.state, now_ns=2 * NS)
        self.assertIsNone(missing.state.pending)
        self.assertNotEqual(before.state.pending.decision_id, after.state.pending.decision_id)
        self.assertEqual(after.state.pending.active_elapsed_ns, 0)
        late = DriverAction("drive", 1, before.state.pending.decision_id, ActionKind.ACCEPT)
        result = step(after.state, valid(LOW), ACTIVE, Policy(), now_ns=3 * NS, action=late)
        self.assertFalse(result.action_receipt.consumed)
        self.assertEqual(result.action_receipt.status, "different_decision")
        self.assertEqual(result.state.accepted.candidate, HIGH)

  def test_rejection_survives_other_sources_and_fully_disengaged_return(self):
    rejected = self.act(self.pending().state, ActionKind.REJECT)
    other = Candidate("map", geographic("another-road"), 25.0)
    accepted_other = step(rejected.state, valid(other), DISENGAGED, Policy(), now_ns=2 * NS)
    returned = step(accepted_other.state, valid(LOW), DISENGAGED, Policy(), now_ns=3 * NS)
    self.assertIn(LOW, returned.state.rejected)
    self.assertEqual(returned.state.accepted.candidate, other)
    self.assertEqual(returned.basis, "rejected")
    self.assertIsNone(returned.history_write)
    self.assertIsNone(returned.control_target_mps)

  def test_same_speed_new_zone_does_not_reuse_rejection(self):
    rejected = self.act(self.pending().state, ActionKind.REJECT)
    next_zone = replace(LOW, observation_identity=geographic("road-3"))
    result = self.pending(candidate=next_zone, state=rejected.state, now_ns=2 * NS)
    self.assertEqual(result.state.pending.candidate, next_zone)
    self.assertIn(LOW, result.state.rejected)

  def test_rejected_limit_from_another_source_still_requires_confirmation(self):
    for identity in (LOW.observation_identity, geographic("map-road")):
      with self.subTest(identity=identity):
        rejected = self.act(self.pending().state, ActionKind.REJECT)
        mapped = replace(LOW, source="map", observation_identity=identity)
        proposed = self.pending(candidate=mapped, state=rejected.state, now_ns=2 * NS)
        self.assertEqual(proposed.control_target_mps, HIGH.speed_mps)
        self.assertEqual(proposed.state.accepted.candidate, HIGH)
        self.assertIsNone(proposed.history_write)
        returned = step(proposed.state, valid(LOW), ACTIVE, Policy(), now_ns=3 * NS)
        self.assertEqual(returned.basis, "rejected")
        self.assertIsNone(returned.state.pending)
        self.assertEqual(returned.control_target_mps, HIGH.speed_mps)
        self.assertEqual(returned.state.accepted.candidate, HIGH)

  def test_changed_pending_candidate_starts_new_clock_and_id(self):
    first = self.pending()
    progressed = step(first.state, valid(LOW), ACTIVE, Policy(), now_ns=29 * NS)
    changed = self.pending(candidate=replace(LOW, speed_mps=19.0), state=progressed.state, now_ns=40 * NS)
    self.assertNotEqual(changed.state.pending.decision_id, first.state.pending.decision_id)
    self.assertEqual(changed.state.pending.active_elapsed_ns, 0)

  def test_confirmation_expires_at_thirty_active_seconds(self):
    pending = self.pending()
    before = step(pending.state, valid(LOW), ACTIVE, Policy(), now_ns=CONFIRMATION_NS - 1)
    self.assertIsNotNone(before.state.pending)
    expired = step(before.state, valid(LOW), ACTIVE, Policy(), now_ns=CONFIRMATION_NS)
    self.assertEqual(expired.basis, "timeout_reject")
    self.assertIn(LOW, expired.state.rejected)
    self.assertIsNone(expired.state.pending)
    self.assertIsNone(expired.history_write)
    self.assertEqual(expired.control_target_mps, HIGH.speed_mps)

  def test_paused_confirmation_does_not_accumulate_inactive_time(self):
    start = self.pending()
    active = step(start.state, valid(LOW), ACTIVE, Policy(), now_ns=10 * NS)
    pause = step(active.state, valid(LOW), PAUSED, Policy(), now_ns=20 * NS)
    held = step(pause.state, valid(LOW), PAUSED, Policy(), now_ns=1000 * NS)
    resume = step(held.state, valid(LOW), ACTIVE, Policy(), now_ns=2000 * NS)
    for result in (active, pause, held, resume):
      self.assertEqual(result.state.pending.active_elapsed_ns, 10 * NS)
    self.assertIsNone(pause.control_target_mps)
    self.assertIsNone(held.control_target_mps)
    expired = step(resume.state, valid(LOW), ACTIVE, Policy(), now_ns=2020 * NS)
    self.assertEqual(expired.basis, "timeout_reject")

  def test_no_implicit_ttl_or_maximum_active_gap(self):
    # Freshness belongs to the adapter: an explicitly valid active interval counts.
    start = self.pending()
    result = step(start.state, valid(LOW), ACTIVE, Policy(), now_ns=1000 * NS)
    self.assertEqual(result.basis, "timeout_reject")

  def test_action_at_deadline_precedes_automatic_timeout(self):
    for kind in ActionKind:
      with self.subTest(kind=kind):
        result = self.act(self.pending().state, kind, now_ns=CONFIRMATION_NS)
        self.assertEqual(result.basis, "driver_accept" if kind is ActionKind.ACCEPT else "driver_reject")
        self.assertTrue(result.action_receipt.consumed)

  def test_directional_confirmation_and_first_limit_policy(self):
    for lower, higher, candidate in itertools.product((False, True), (False, True), (LOW, HIGH, replace(HIGH, speed_mps=31.0))):
      with self.subTest(lower=lower, higher=higher, candidate=candidate):
        result = step(saved(), valid(candidate), ACTIVE, Policy(lower, higher), now_ns=0)
        expected_pending = lower if candidate.speed_mps < HIGH.speed_mps else higher if candidate.speed_mps > HIGH.speed_mps else False
        self.assertEqual(result.state.pending is not None, expected_pending)
        self.assertEqual(result.control_target_mps, HIGH.speed_mps if expected_pending else candidate.speed_mps)
    for higher in (False, True):
      result = step(new_session("drive"), valid(LOW), ACTIVE, Policy(confirm_higher=higher), now_ns=0)
      self.assertEqual(result.state.pending is not None, higher)
      self.assertEqual(result.control_target_mps, None if higher else LOW.speed_mps)
      self.assertEqual(result.history_write is None, higher)

  def test_near_equal_values_are_exact_and_source_identity_updates_history(self):
    for toward in (0.0, math.inf):
      near = replace(HIGH, speed_mps=math.nextafter(HIGH.speed_mps, toward))
      result = self.pending(candidate=near)
      self.assertNotEqual(result.state.pending.candidate.speed_mps, HIGH.speed_mps)
    same_speed = replace(HIGH, source="map", observation_identity=geographic("mapped-road"))
    result = step(saved(), valid(same_speed), ACTIVE, Policy(), now_ns=0)
    self.assertIsNone(result.state.pending)
    self.assertEqual(result.history_write.candidate, same_speed)
    unchanged = step(result.state, valid(same_speed), ACTIVE, Policy(), now_ns=NS)
    self.assertIsNone(unchanged.history_write)

  def test_disengaged_acceptance_has_no_control_and_needs_no_button(self):
    for mode, owner in itertools.product(Mode, LongitudinalOwner):
      with self.subTest(mode=mode, owner=owner):
        authority = Authority(mode, owner, False, False, False, True)
        result = step(saved(), valid(LOW), authority, Policy(), now_ns=0)
        self.assertEqual(result.state.accepted.candidate, LOW)
        self.assertIsNotNone(result.history_write)
        self.assertIsNone(result.state.pending)
        self.assertIsNone(result.control_target_mps)

  def test_zero_active_axes_does_not_imply_fully_disengaged(self):
    result = self.pending(authority=PAUSED)
    self.assertEqual(result.state.accepted.candidate, HIGH)
    self.assertIsNone(result.history_write)
    self.assertIsNone(result.control_target_mps)

  def test_modes_stock_owner_and_inactive_long_never_gain_control_or_consume_action(self):
    contexts = [
      Authority(Mode.OFF, LongitudinalOwner.NONE, False, False, False, False),
      Authority(Mode.LATERAL_ONLY, LongitudinalOwner.SYSTEM, True, False, False, False),
      Authority(Mode.LATERAL_ONLY, LongitudinalOwner.STOCK, True, False, True, False),
      Authority(Mode.COMBINED, LongitudinalOwner.STOCK, True, False, True, False),
      Authority(Mode.LONGITUDINAL_ONLY, LongitudinalOwner.STOCK, False, False, True, False),
      PAUSED,
    ]
    for authority in contexts:
      with self.subTest(authority=authority):
        pending = self.pending(authority=authority)
        acted = self.act(pending.state, ActionKind.ACCEPT, authority=authority)
        lost = step(acted.state, ABSENT, authority, Policy(fallback_previous=True), now_ns=2 * NS)
        for decision in (pending, acted, lost):
          self.assertIsNone(decision.control_target_mps)
          self.assertIsNone(decision.history_write)
        self.assertTrue(acted.action_receipt.acknowledged)
        self.assertFalse(acted.action_receipt.consumed)
        self.assertEqual(acted.state.last_action_sequence, 0)

  def test_combined_and_long_only_have_equal_longitudinal_decisions(self):
    for authority in (ACTIVE, replace(ACTIVE, mode=Mode.COMBINED, lateral_active=True)):
      pending = self.pending(authority=authority)
      accepted = self.act(pending.state, ActionKind.ACCEPT, authority=authority)
      self.assertEqual(accepted.control_target_mps, LOW.speed_mps)
      self.assertEqual(accepted.history_write.candidate, LOW)

  def test_all_authority_combinations_reject_contradictions(self):
    combinations = itertools.product(Mode, LongitudinalOwner, (False, True), (False, True), (False, True), (False, True))
    for mode, owner, lateral, longitudinal, stock, disengaged in combinations:
      authority = Authority(mode, owner, lateral, longitudinal, stock, disengaged)
      invalid = ((lateral and mode not in (Mode.LATERAL_ONLY, Mode.COMBINED)) or
                 (longitudinal and (mode not in (Mode.LONGITUDINAL_ONLY, Mode.COMBINED) or owner is not LongitudinalOwner.SYSTEM)) or
                 (stock and owner is not LongitudinalOwner.STOCK) or (disengaged and (lateral or longitudinal or stock)))
      with self.subTest(authority=authority):
        result = step(saved(), valid(LOW), authority, Policy(False, False, True), now_ns=0)
        self.assertEqual(bool(result.errors), bool(invalid))
        if invalid:
          self.assertIsNone(result.control_target_mps)
          self.assertIsNone(result.history_write)
        elif not longitudinal:
          self.assertIsNone(result.control_target_mps)

  def test_display_only_clears_pending_and_never_accepts_or_falls_back(self):
    pending = self.pending()
    action = DriverAction("drive", 1, pending.state.pending.decision_id, ActionKind.ACCEPT)
    for authority, observation in itertools.product((ACTIVE, DISENGAGED), (valid(LOW), ABSENT)):
      with self.subTest(authority=authority, observation=observation):
        result = step(pending.state, observation, authority, Policy(fallback_previous=True, display_only=True), now_ns=NS, action=action)
        self.assertIsNone(result.state.pending)
        self.assertEqual(result.state.accepted, pending.state.accepted)
        self.assertIsNone(result.history_write)
        self.assertIsNone(result.control_target_mps)
        self.assertEqual(result.display_candidate, observation.candidate)
        self.assertFalse(result.action_receipt.consumed)
        self.assertEqual(result.state.last_action_sequence, 1)

  def test_repeated_and_out_of_order_actions_are_seen_but_not_consumed(self):
    pending = self.pending()
    ineligible = self.act(pending.state, ActionKind.ACCEPT, sequence=10, authority=PAUSED)
    for sequence in (10, 9):
      result = self.act(ineligible.state, ActionKind.ACCEPT, sequence=sequence, now_ns=2 * NS)
      self.assertFalse(result.action_receipt.consumed)
      self.assertEqual(result.action_receipt.status, "already_seen")
      self.assertEqual(result.state.last_action_sequence, 10)
      self.assertEqual(result.state.accepted.candidate, HIGH)
    accepted = self.act(ineligible.state, ActionKind.ACCEPT, sequence=11, now_ns=2 * NS)
    self.assertTrue(accepted.action_receipt.consumed)
    self.assertEqual(accepted.state.accepted.candidate, LOW)

  def test_wrong_session_does_not_poison_sequence_watermark(self):
    pending = self.pending()
    foreign = DriverAction("other-drive", 10_000, pending.state.pending.decision_id, ActionKind.ACCEPT)
    result = step(pending.state, valid(LOW), ACTIVE, Policy(), now_ns=NS, action=foreign)
    self.assertEqual(result.action_receipt.status, "foreign_session")
    self.assertFalse(result.action_receipt.consumed)
    self.assertEqual(result.state.last_action_sequence, -1)
    accepted = self.act(result.state, ActionKind.ACCEPT, sequence=0, now_ns=2 * NS)
    self.assertTrue(accepted.action_receipt.consumed)

  def test_unrelated_action_is_acknowledged_and_watermarked_without_consuming_it(self):
    pending = self.pending()
    unrelated = DriverAction("drive", 3, 987, ActionKind.REJECT)
    result = step(pending.state, valid(LOW), ACTIVE, Policy(), now_ns=NS, action=unrelated)
    self.assertTrue(result.action_receipt.acknowledged)
    self.assertFalse(result.action_receipt.consumed)
    self.assertEqual(result.action_receipt.status, "different_decision")
    self.assertEqual(result.state.last_action_sequence, 3)
    self.assertEqual(result.state.rejected, frozenset())

  def test_event_cannot_accept_a_decision_not_previously_presented(self):
    action = DriverAction("drive", 0, 1, ActionKind.ACCEPT)
    result = step(saved(), valid(LOW), ACTIVE, Policy(), now_ns=0, action=action)
    self.assertEqual(result.state.pending.decision_id, 1)
    self.assertEqual(result.action_receipt.status, "not_presented")
    self.assertFalse(result.action_receipt.consumed)
    self.assertEqual(result.state.last_action_sequence, 0)
    self.assertEqual(result.state.accepted.candidate, HIGH)

  def test_invalid_input_fails_closed_and_valid_action_is_still_seen(self):
    pending = self.pending(now_ns=10 * NS)
    action = DriverAction("drive", 2, pending.state.pending.decision_id, ActionKind.ACCEPT)
    result = step(pending.state, valid(LOW), ACTIVE, Policy(), now_ns=9 * NS, action=action)
    self.assertTrue(result.errors)
    self.assertIsNone(result.control_target_mps)
    self.assertIsNone(result.state.pending)
    self.assertFalse(result.state.timer_running)
    self.assertEqual(result.state.last_timestamp_ns, 10 * NS)
    self.assertIsNone(result.history_write)
    self.assertFalse(result.action_receipt.consumed)
    self.assertEqual(result.action_receipt.status, "invalid_input")
    self.assertEqual(result.state.last_action_sequence, 2)
    recovered = self.pending(state=result.state, now_ns=20 * NS)
    self.assertEqual(recovered.state.pending.active_elapsed_ns, 0)

  def test_clock_requires_nonnegative_monotonic_integer_nanoseconds(self):
    invalid_times: tuple[Any, ...] = (-1, 0.0, True, math.nan, math.inf, "10", None)
    for now_ns in invalid_times:
      with self.subTest(now_ns=now_ns):
        result = step(saved(), valid(LOW), ACTIVE, Policy(), now_ns=now_ns)
        self.assertTrue(result.errors)
        self.assertIsNone(result.control_target_mps)
    pending = self.pending(now_ns=NS)
    same = step(pending.state, valid(LOW), ACTIVE, Policy(), now_ns=NS)
    self.assertEqual(same.state.pending.active_elapsed_ns, 0)

  def test_candidate_requires_finite_positive_speed_and_explicit_bounded_identity(self):
    malformed = [replace(LOW, speed_mps=value) for value in (0, -1, True, math.nan, math.inf, "20", None, 10 ** 1000)]
    malformed += [replace(LOW, source=""), replace(LOW, observation_identity=geographic("")), replace(LOW, source=" "),
                  replace(LOW, observation_identity=geographic("x" * 257)),
                  replace(LOW, source="a\nb")]
    for candidate in malformed:
      with self.subTest(candidate=candidate):
        result = step(saved(), valid(candidate), ACTIVE, Policy(False, False), now_ns=0)
        self.assertTrue(result.errors)
        self.assertIsNone(result.control_target_mps)
        self.assertIsNone(result.history_write)

  def test_observation_classification_is_explicit_and_consistent(self):
    malformed: list[Any] = [Observation(ObservationKind.VALID), Observation(cast(Any, "valid"), LOW), None]
    malformed += [Observation(kind, LOW) for kind in (ObservationKind.ABSENT, ObservationKind.UNKNOWN, ObservationKind.STALE)]
    for observation in malformed:
      with self.subTest(observation=observation):
        result = step(saved(), observation, ACTIVE, Policy(fallback_previous=True), now_ns=0)
        self.assertTrue(result.errors)
        self.assertIsNone(result.control_target_mps)

  def test_policy_authority_and_actions_reject_coerced_types(self):
    for field in ("confirm_lower", "confirm_higher", "fallback_previous", "display_only"):
      result = step(saved(), valid(LOW), ACTIVE, replace(Policy(), **{field: 1}), now_ns=0)
      self.assertTrue(result.errors)
    for authority in (replace(ACTIVE, mode="longitudinal_only"), replace(ACTIVE, owner="system"), replace(ACTIVE, fully_disengaged=0)):
      result = step(saved(), valid(LOW), authority, Policy(), now_ns=0)
      self.assertTrue(result.errors)
    pending = self.pending()
    action = DriverAction("drive", 1, pending.state.pending.decision_id, ActionKind.ACCEPT)
    for invalid in (replace(action, sequence_id=True), replace(action, sequence_id=-1), replace(action, decision_id=0),
                    replace(action, session_id=""), replace(action, kind="accept")):
      result = step(pending.state, valid(LOW), ACTIVE, Policy(), now_ns=NS, action=invalid)
      self.assertTrue(result.errors)
      self.assertIsNone(result.control_target_mps)
      self.assertIsNone(result.action_receipt)
      self.assertEqual(result.state.last_action_sequence, -1)

  def test_invalid_state_never_returns_a_control_target(self):
    malformed = [replace(saved(), session_id=""), replace(saved(), rejected=set()), replace(saved(), last_timestamp_ns=-1),
                 replace(saved(), next_decision_id=0), replace(saved(), timer_running=True), replace(saved(), accepted=LOW)]
    for state in malformed:
      with self.subTest(state=state):
        result = step(state, valid(LOW), ACTIVE, Policy(False, False, True), now_ns=0)
        self.assertTrue(result.errors)
        self.assertIsNone(result.control_target_mps)
        self.assertIsNone(result.history_write)

  def test_accepted_or_pending_candidate_cannot_also_be_rejected(self):
    accepted_conflict = replace(saved(), rejected=frozenset({HIGH}))
    pending_conflict = replace(self.pending().state, rejected=frozenset({LOW}))
    for state in (accepted_conflict, pending_conflict):
      with self.subTest(state=state):
        result = step(state, valid(HIGH), ACTIVE, Policy(False, False, True), now_ns=NS)
        self.assertTrue(result.errors)
        self.assertIsNone(result.control_target_mps)
        self.assertIsNone(result.history_write)
        self.assertIs(result.state, state)
        self.assertEqual(result.state.accepted.candidate, HIGH)

  def test_rejection_capacity_latches_closed_instead_of_evicting(self):
    state = saved()
    for index in range(MAX_REJECTIONS + 1):
      candidate = replace(LOW, observation_identity=geographic(f"zone-{index}"))
      pending = self.pending(candidate=candidate, state=state, now_ns=2 * index)
      result = self.act(pending.state, ActionKind.REJECT, sequence=index, now_ns=2 * index + 1)
      state = result.state
    self.assertEqual(len(state.rejected), MAX_REJECTIONS)
    self.assertTrue(state.rejection_capacity_exhausted)
    self.assertIsNone(result.control_target_mps)
    self.assertIn(replace(LOW, observation_identity=geographic("zone-0")), state.rejected)
    after = step(state, ABSENT, ACTIVE, Policy(fallback_previous=True), now_ns=2 * MAX_REJECTIONS + 2)
    self.assertEqual(after.basis, "session_reset_required")
    self.assertIsNone(after.control_target_mps)
    shown = step(after.state, valid(replace(LOW, observation_identity=geographic("zone-0"))), ACTIVE, Policy(),
                 now_ns=2 * MAX_REJECTIONS + 3)
    blocked_adopt = step(shown.state, shown.state.observation, ACTIVE, Policy(), now_ns=2 * MAX_REJECTIONS + 4,
                         adopt=self.adopt_request(shown.state, MAX_REJECTIONS + 1))
    self.assertFalse(blocked_adopt.adoption_receipt.consumed)
    self.assertEqual(blocked_adopt.adoption_receipt.status, "session_reset_required")
    self.assertIsNone(blocked_adopt.adoption)
    self.assertIsNone(blocked_adopt.history_write)
    self.assertIsNone(blocked_adopt.control_target_mps)
    self.assertTrue(blocked_adopt.state.rejection_capacity_exhausted)
    self.assertEqual(blocked_adopt.state.rejected, state.rejected)
    reset = new_session("next-drive", state.accepted)
    self.assertFalse(reset.rejection_capacity_exhausted)
    self.assertEqual(reset.rejected, frozenset())
    self.assertEqual(reset.accepted, state.accepted)
    self.assertEqual(reset.last_action_sequence, -1)

  def test_state_and_inputs_are_immutable_and_new_session_validates_history(self):
    original = saved()
    step(original, valid(LOW), ACTIVE, Policy(), now_ns=0)
    self.assertIsNone(original.pending)
    self.assertIsNone(original.last_timestamp_ns)
    with self.assertRaises(FrozenInstanceError):
      cast(Any, original).session_id = "changed"
    for session, history in (("", None), ("drive", LOW), ("drive", AcceptedLimit(replace(HIGH, speed_mps=0), "old", 0))):
      with self.assertRaises(ValueError):
        new_session(session, cast(Any, history))

  def test_identity_kinds_are_explicit_and_not_interchangeable(self):
    identities = (geographic("road"), ObservationIdentity(IdentityKind.PRODUCER_EPISODE, value="episode"),
                  ObservationIdentity(IdentityKind.SESSION_VALUE, session_id="drive"))
    for identity in identities:
      candidate = replace(HIGH, observation_identity=identity)
      result = step(saved(), valid(candidate), ACTIVE, Policy(), now_ns=0)
      self.assertEqual(result.errors, ())
      self.assertEqual(result.state.accepted.candidate, candidate)
    self.assertEqual(len({replace(HIGH, observation_identity=identity) for identity in identities}), 3)

  def test_session_value_retains_rejection_across_dropout_and_source_switching(self):
    identity = ObservationIdentity(IdentityKind.SESSION_VALUE, session_id="drive")
    candidate = replace(LOW, observation_identity=identity)
    pending = self.pending(candidate=candidate)
    rejected = self.act(pending.state, ActionKind.REJECT)
    absent = step(rejected.state, ABSENT, ACTIVE, Policy(), now_ns=2 * NS)
    alternate = step(absent.state, valid(replace(candidate, source="map")), ACTIVE, Policy(), now_ns=3 * NS)
    returned = step(alternate.state, valid(Candidate("dashboard", ObservationIdentity(IdentityKind.SESSION_VALUE, session_id="drive"),
                                                    LOW.speed_mps)), ACTIVE, Policy(), now_ns=4 * NS)
    self.assertIn(candidate, returned.state.rejected)
    self.assertEqual(returned.basis, "rejected")
    self.assertEqual(returned.state.accepted.candidate, HIGH)
    self.assertIsNotNone(alternate.state.pending)
    self.assertIsNone(returned.state.pending)

  def test_session_value_has_no_alternate_token_and_cannot_cross_sessions(self):
    malformed = [ObservationIdentity(IdentityKind.SESSION_VALUE, value="invented", session_id="drive"),
                 ObservationIdentity(IdentityKind.SESSION_VALUE), ObservationIdentity(IdentityKind.SESSION_VALUE, session_id="other"),
                 ObservationIdentity(IdentityKind.GEOGRAPHIC, value="road", session_id="drive"),
                 ObservationIdentity(IdentityKind.PRODUCER_EPISODE, value=""),
                 ObservationIdentity(cast(Any, "session_value"), session_id="drive"), cast(Any, "road")]
    for identity in malformed:
      with self.subTest(identity=identity):
        result = step(saved(), valid(replace(LOW, observation_identity=identity)), ACTIVE, Policy(), now_ns=0)
        self.assertTrue(result.errors)
        self.assertIsNone(result.control_target_mps)
        self.assertIsNone(result.history_write)
    candidate = replace(HIGH, observation_identity=ObservationIdentity(IdentityKind.SESSION_VALUE, session_id="old"))
    history = AcceptedLimit(candidate, "old", 0)
    with self.assertRaises(ValueError):
      new_session("drive", history)
    with self.assertRaises(ValueError):
      new_session("drive", replace(history, session_id="drive"))
    # No implicit rekeying: independently qualified geographic history retains its original accepted session.
    qualified = AcceptedLimit(HIGH, "old", 0)
    self.assertIs(new_session("drive", qualified).accepted, qualified)

  def test_explicit_adopt_clears_only_matching_rejection(self):
    first_reject = self.act(self.pending().state, ActionKind.REJECT)
    other = replace(LOW, source="map", speed_mps=19.0)
    second_pending = self.pending(candidate=other, state=first_reject.state, now_ns=2 * NS)
    second_reject = self.act(second_pending.state, ActionKind.REJECT, sequence=1, now_ns=3 * NS)
    shown = step(second_reject.state, valid(LOW), ACTIVE, Policy(), now_ns=4 * NS)
    request = self.adopt_request(shown.state, sequence=2)
    adopted = step(shown.state, valid(LOW), ACTIVE, Policy(), now_ns=5 * NS, adopt=request)
    self.assertEqual(adopted.basis, "driver_adopt")
    self.assertTrue(adopted.adoption_receipt.consumed)
    self.assertIsNone(adopted.action_receipt)
    self.assertEqual(adopted.state.rejected, frozenset({other}))
    self.assertEqual(adopted.history_write.candidate, LOW)
    self.assertEqual(adopted.control_target_mps, LOW.speed_mps)
    self.assertIsNone(adopted.state.pending)
    self.assertTrue(adopted.adoption.clear_override)
    self.assertEqual(adopted.adoption.session_id, "drive")
    self.assertEqual(adopted.adoption.action_sequence_id, 2)
    self.assertEqual(adopted.adoption.presentation_id, request.presentation_id)
    self.assertEqual(adopted.adoption.accepted, adopted.state.accepted)
    self.assertEqual(adopted.adoption.reconciliation_speed_mps, LOW.speed_mps)
    still_rejected = step(adopted.state, valid(other), ACTIVE, Policy(), now_ns=6 * NS)
    self.assertEqual(still_rejected.basis, "rejected")
    self.assertEqual(still_rejected.control_target_mps, LOW.speed_mps)

  def test_adopt_already_accepted_candidate_still_emits_reconciliation(self):
    shown = step(saved(), valid(HIGH), ACTIVE, Policy(), now_ns=0)
    for authority in (ACTIVE, replace(ACTIVE, mode=Mode.COMBINED, lateral_active=True)):
      result = step(shown.state, valid(HIGH), authority, Policy(), now_ns=NS, adopt=self.adopt_request(shown.state))
      self.assertTrue(result.adoption_receipt.consumed)
      self.assertIsNone(result.history_write)
      self.assertEqual(result.state.accepted, shown.state.accepted)
      self.assertTrue(result.adoption.clear_override)
      self.assertEqual(result.adoption.reconciliation_speed_mps, HIGH.speed_mps)

  def test_adopt_precedes_confirmation_timeout(self):
    pending = self.pending()
    result = step(pending.state, valid(LOW), ACTIVE, Policy(), now_ns=CONFIRMATION_NS, adopt=self.adopt_request(pending.state))
    self.assertEqual(result.basis, "driver_adopt")
    self.assertEqual(result.state.accepted.candidate, LOW)
    self.assertNotIn(LOW, result.state.rejected)

  def test_adopt_requires_prior_presentation_even_when_new_id_is_guessed(self):
    guessed = AdoptRequest("drive", 0, 1, LOW)
    unseen = step(saved(), valid(LOW), ACTIVE, Policy(), now_ns=0, adopt=guessed)
    self.assertEqual(unseen.state.presentation.presentation_id, guessed.presentation_id)
    self.assertFalse(unseen.adoption_receipt.consumed)
    self.assertEqual(unseen.adoption_receipt.status, "different_presentation")
    self.assertIsNone(unseen.adoption)
    self.assertIsNone(unseen.history_write)
    replay = step(unseen.state, valid(LOW), ACTIVE, Policy(), now_ns=NS, adopt=guessed)
    self.assertEqual(replay.adoption_receipt.status, "already_seen")
    self.assertIsNone(replay.adoption)
    fresh = step(replay.state, valid(LOW), ACTIVE, Policy(), now_ns=2 * NS, adopt=replace(guessed, sequence_id=1))
    self.assertTrue(fresh.adoption_receipt.consumed)

  def test_adopt_context_expires_on_source_change_or_loss(self):
    shown = self.pending()
    request = self.adopt_request(shown.state)
    for observation in (valid(replace(LOW, source="map")), ABSENT, Observation(ObservationKind.UNKNOWN), Observation(ObservationKind.STALE)):
      with self.subTest(observation=observation):
        changed = step(shown.state, observation, ACTIVE, Policy(fallback_previous=True), now_ns=NS, adopt=request)
        self.assertFalse(changed.adoption_receipt.consumed)
        self.assertIsNone(changed.adoption)
        self.assertIsNone(changed.history_write)
        returned = step(changed.state, valid(LOW), ACTIVE, Policy(), now_ns=2 * NS, adopt=replace(request, sequence_id=1))
        self.assertFalse(returned.adoption_receipt.consumed)
        self.assertIsNone(returned.adoption)
        self.assertNotEqual(returned.state.presentation.presentation_id, request.presentation_id)

  def test_adopt_exact_candidate_cannot_be_swapped_under_existing_context(self):
    shown = self.pending()
    for other in (replace(LOW, source="map"), replace(LOW, speed_mps=19.0),
                  replace(LOW, observation_identity=geographic("other-road"))):
      request = replace(self.adopt_request(shown.state), candidate=other)
      result = step(shown.state, valid(LOW), ACTIVE, Policy(), now_ns=NS, adopt=request)
      self.assertFalse(result.adoption_receipt.consumed)
      self.assertEqual(result.adoption_receipt.status, "different_presentation")
      self.assertIsNone(result.adoption)

  def test_adopt_requires_active_system_long_authority_and_control_policy(self):
    rejected = self.act(self.pending().state, ActionKind.REJECT)
    request = self.adopt_request(rejected.state, sequence=1)
    contexts = [PAUSED, DISENGAGED, Authority(Mode.OFF, LongitudinalOwner.NONE, False, False, False, False),
                Authority(Mode.LATERAL_ONLY, LongitudinalOwner.NONE, True, False, False, False),
                Authority(Mode.LATERAL_ONLY, LongitudinalOwner.STOCK, True, False, True, False),
                Authority(Mode.COMBINED, LongitudinalOwner.STOCK, True, False, True, False)]
    for authority in contexts:
      with self.subTest(authority=authority):
        result = step(rejected.state, valid(LOW), authority, Policy(), now_ns=2 * NS, adopt=request)
        self.assertFalse(result.adoption_receipt.consumed)
        self.assertEqual(result.adoption_receipt.status, "no_longitudinal_authority")
        self.assertIn(LOW, result.state.rejected)
        self.assertIsNone(result.adoption)
        self.assertIsNone(result.history_write)
        self.assertIsNone(result.control_target_mps)
        self.assertEqual(result.state.last_action_sequence, 1)
    display = step(rejected.state, valid(LOW), ACTIVE, Policy(display_only=True), now_ns=2 * NS, adopt=request)
    self.assertFalse(display.adoption_receipt.consumed)
    self.assertEqual(display.adoption_receipt.status, "display_only")
    self.assertIn(LOW, display.state.rejected)
    self.assertIsNone(display.adoption)
    self.assertIsNone(display.history_write)

  def test_adopt_foreign_session_does_not_advance_watermark(self):
    shown = self.pending()
    foreign = replace(self.adopt_request(shown.state, sequence=999), session_id="other")
    result = step(shown.state, valid(LOW), ACTIVE, Policy(), now_ns=NS, adopt=foreign)
    self.assertEqual(result.adoption_receipt.status, "foreign_session")
    self.assertEqual(result.state.last_action_sequence, -1)
    self.assertIsNone(result.adoption)
    accepted = step(result.state, valid(LOW), ACTIVE, Policy(), now_ns=2 * NS, adopt=self.adopt_request(result.state))
    self.assertTrue(accepted.adoption_receipt.consumed)

  def test_adoption_and_confirmation_share_seen_sequence_watermark(self):
    shown = self.pending()
    request = self.adopt_request(shown.state, sequence=5)
    paused = step(shown.state, valid(LOW), PAUSED, Policy(), now_ns=NS, adopt=request)
    repeated_action = DriverAction("drive", 5, paused.state.pending.decision_id, ActionKind.ACCEPT)
    repeated = step(paused.state, valid(LOW), ACTIVE, Policy(), now_ns=2 * NS, action=repeated_action)
    self.assertEqual(repeated.action_receipt.status, "already_seen")
    self.assertFalse(repeated.action_receipt.consumed)
    fresh = step(repeated.state, valid(LOW), ACTIVE, Policy(), now_ns=3 * NS, action=replace(repeated_action, sequence_id=6))
    self.assertTrue(fresh.action_receipt.consumed)
    old_adopt = step(fresh.state, valid(LOW), ACTIVE, Policy(), now_ns=4 * NS, adopt=request)
    self.assertFalse(old_adopt.adoption_receipt.consumed)
    self.assertIsNone(old_adopt.adoption)

  def test_ambiguous_action_and_adopt_fail_closed_and_watermark_both(self):
    shown = self.pending()
    for ordinary_sequence, adopt_sequence in ((3, 7), (7, 3), (7, 7)):
      with self.subTest(ordinary=ordinary_sequence, adopt=adopt_sequence):
        action = DriverAction("drive", ordinary_sequence, shown.state.pending.decision_id, ActionKind.ACCEPT)
        adopt = self.adopt_request(shown.state, sequence=adopt_sequence)
        result = step(shown.state, valid(LOW), ACTIVE, Policy(), now_ns=NS, action=action, adopt=adopt)
        self.assertIn("ambiguous action and adopt request", result.errors)
        self.assertFalse(result.action_receipt.consumed)
        self.assertFalse(result.adoption_receipt.consumed)
        self.assertEqual(result.state.last_action_sequence, 7)
        self.assertIsNone(result.control_target_mps)
        self.assertIsNone(result.adoption)
        self.assertIsNone(result.history_write)
        self.assertEqual(result.state.accepted.candidate, HIGH)
        self.assertIsNone(result.state.presentation)

  def test_invalid_adopt_or_clock_never_produces_an_effect(self):
    shown = self.pending(now_ns=10 * NS)
    request = self.adopt_request(shown.state, sequence=1)
    for malformed in (replace(request, sequence_id=True), replace(request, presentation_id=0),
                      replace(request, session_id=""), replace(request, candidate=replace(LOW, speed_mps=0))):
      result = step(shown.state, valid(LOW), ACTIVE, Policy(), now_ns=11 * NS, adopt=malformed)
      self.assertTrue(result.errors)
      self.assertIsNone(result.adoption_receipt)
      self.assertIsNone(result.adoption)
      self.assertIsNone(result.control_target_mps)
      self.assertEqual(result.state.last_action_sequence, -1)
    reversed_clock = step(shown.state, valid(LOW), ACTIVE, Policy(), now_ns=9 * NS, adopt=request)
    self.assertTrue(reversed_clock.errors)
    self.assertFalse(reversed_clock.adoption_receipt.consumed)
    self.assertEqual(reversed_clock.state.last_action_sequence, 1)
    self.assertIsNone(reversed_clock.adoption)

  def test_invalid_presentation_state_is_inert(self):
    shown = self.pending()
    for state in (replace(shown.state, presentation=None), replace(shown.state, next_presentation_id=1),
                  replace(shown.state, presentation=replace(shown.state.presentation, candidate=HIGH))):
      result = step(state, valid(LOW), ACTIVE, Policy(), now_ns=NS, adopt=self.adopt_request(shown.state))
      self.assertTrue(result.errors)
      self.assertIsNone(result.control_target_mps)
      self.assertIsNone(result.adoption)
      self.assertIsNone(result.history_write)


if __name__ == "__main__":
  unittest.main()
