"""Exercise the real cross-socket wakeup between card and selfdrived."""

import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from opendbc.car.structs import car
from opendbc.car import gen_empty_fingerprint
from opendbc.car.honda.interface import CarInterface as HondaInterface
from opendbc.car.honda.values import CAR as HONDA
from openpilot.cereal import messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car.card import Car
from openpilot.selfdrive.car.tests.publication_fixture import initialize_publication_sources
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
from openpilot.starpilot.aol.runtime import current_intent, current_native, decide_axes
from openpilot.starpilot.aol.wire import IntentState, SafetyState, encode_intent, encode_safety


@pytest.mark.parametrize('pause_lateral,qualified,expected', [(False, True, 'combined'), (True, True, 'longitudinalOnly'),
                                                            (False, False, 'off')])
def test_card_companion_is_available_when_car_state_wakes_selfdrive(pause_lateral, qualified, expected):
  with OpenpilotPrefix():
    messaging.reset_context()
    pm = messaging.PubMaster(['carState', 'carOutput', 'aolIntentWire', 'aolSafetyWire'])
    sd = SelfdriveD.__new__(SelfdriveD)
    sd.sm = messaging.SubMaster(['aolIntentWire', 'aolSafetyWire'])
    sd.car_state_sock = messaging.sub_sock('carState', timeout=100)
    sd.initialized, sd.enabled = True, False
    sd.aol_car_state_log_ns, sd.conditional_car_state_valid = 0, False
    sd.CS_prev = car.CarState.new_message(canValid=True, gearShifter=car.CarState.GearShifter.drive, vEgo=20.)
    stamp = time.monotonic_ns()
    prior = stamp - 29_350_000  # Route: 29 ms CAN gap plus 2.7 ms consumer latency.
    old = messaging.new_message('aolIntentWire', 0, valid=True)
    old.logMonoTime = prior
    old.aolIntentWire = encode_intent(IntentState('card', 1, prior, prior, prior + 200_000_000,
                                                 True, False, False, True, True))
    pm.send('aolIntentWire', old)
    sd.sm.update(100)
    assert sd.sm.seen['aolIntentWire']
    # Native permission is current and unchanged throughout the race.
    cp = HondaInterface.get_params(HONDA.HONDA_CIVIC_BOSCH, gen_empty_fingerprint(), [], True, False, False)
    cp.safetyConfigs[-1].safetyParam |= 32
    cp.alternativeExperience = 1
    native = messaging.new_message('aolSafetyWire', 0, valid=True)
    native.logMonoTime = stamp
    native.aolSafetyWire = encode_safety(SafetyState(1, True, stamp, stamp + 200_000_000,
      int(car.CarParams.SafetyModel.hondaBosch), 34, True, True, True, True, 'panda', 'drive'))
    pm.send('aolSafetyWire', native)
    sd.sm.update(100)
    assert sd.sm.seen['aolSafetyWire']
    decisions = []

    def send(service, message):
      pm.send(service, message)
      if service == 'carState':
        # Force the consumer to run at the earliest possible publication
        # boundary, before card can execute its next line. Both receive paths
        # are real sockets and data_sample retains its nonblocking SM update.
        state = sd.data_sample()
        now = stamp + 2_800_000
        intent = current_intent(sd.sm, car_state_ns=sd.aol_car_state_log_ns, now_ns=now)
        ack = current_native(sd.sm, cp, now_ns=now, axis_session_id='drive')
        assert ack is not None
        if qualified:
          assert intent is not None
          assert intent.carStateLogMonoTime == sd.aol_car_state_log_ns == stamp
        else:
          assert intent is None
        decisions.append(decide_axes(standard_lateral=True, standard_longitudinal=True,
          intent=intent, native=ack, car_state=state, initialized=True, model_ready=True,
          no_entry=False, immediate_disable=False, dm_lockout=False, pause_brake_mps=0))
        # The original 30 ms contract remains exact; no arrival-side renewal.
        assert current_intent(sd.sm, car_state_ns=stamp, now_ns=stamp + 30_000_001) is None

    card = Car.__new__(Car)
    card.__dict__.update(sm=SimpleNamespace(frame=1, all_checks=lambda _: True), pm=SimpleNamespace(send=send),
      CP=cp, car_params_published=True, slc_replay=False, curve_replay=False, conditional_replay=False,
      last_actuators_output=car.CarControl.Actuators.new_message(), can_rcv_cum_timeout_counter=0,
      rk=SimpleNamespace(remaining=0), aol_replay=True, aol_qualified=qualified, aol_sequence=1,
      slc_producer_session='card', aol_card_intent=SimpleNamespace(allowed_latch=True, output=lambda _: (True, pause_lateral, False)),
      v_cruise_helper=SimpleNamespace(slc_cruise_change=None))
    initialize_publication_sources(card)
    create = messaging.new_message

    def stamped(service, *args, **kwargs):
      message = create(service, *args, **kwargs)
      if service == 'carState':
        message.logMonoTime = stamp
      return message

    with patch('openpilot.selfdrive.car.card.messaging.new_message', side_effect=stamped):
      card.state_publish(sd.CS_prev, None)
    assert len(decisions) == 1
    assert decisions[0].mode == expected


def test_future_companion_only_reuses_same_car_state_original_lease():
  with OpenpilotPrefix():
    messaging.reset_context()
    pm = messaging.PubMaster(['carState', 'aolIntentWire'])
    sd = SelfdriveD.__new__(SelfdriveD)
    sd.sm = messaging.SubMaster(['aolIntentWire'])
    sd.car_state_sock = messaging.sub_sock('carState', timeout=1)
    sd.initialized, sd.enabled = True, False
    sd.aol_car_state_log_ns, sd.conditional_car_state_valid = 0, False
    sd.CS_prev = car.CarState.new_message(canValid=True, gearShifter=car.CarState.GearShifter.drive, vEgo=20.)
    stamp = time.monotonic_ns()

    def publish_intent(at, *, valid=True, qualified=True, session='card'):
      message = messaging.new_message('aolIntentWire', 0, valid=valid)
      message.logMonoTime = at
      message.aolIntentWire = encode_intent(IntentState(session, 1, at, at, at + 200_000_000,
                                                       True, True, False, qualified, True))
      pm.send('aolIntentWire', message)

    publish_intent(stamp)
    state = messaging.new_message('carState', valid=True)
    state.logMonoTime, state.carState = stamp, sd.CS_prev
    pm.send('carState', state)
    sd.CS_prev = sd.data_sample()
    previous = current_intent(sd.sm, car_state_ns=stamp, now_ns=stamp + 1_000_000)
    assert previous is not None
    # Card has sent the next intent, but not its carState. Exercise the real
    # carState socket timeout and the real nonblocking SubMaster receive.
    publish_intent(stamp + 20_000_000)
    with patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', return_value=stamp + 23_000_000):
      assert sd.data_sample() is sd.CS_prev
    assert sd.aol_car_state_log_ns == stamp
    assert current_intent(sd.sm, car_state_ns=stamp, now_ns=stamp + 23_000_000) is None
    assert current_intent(sd.sm, car_state_ns=stamp, now_ns=stamp + 23_000_000, previous=previous) == previous
    assert current_intent(sd.sm, car_state_ns=stamp, now_ns=stamp + 30_000_001, previous=previous) is None
    assert current_intent(sd.sm, car_state_ns=stamp - 1, now_ns=stamp + 23_000_000, previous=previous) is None
    for changes in ({'valid': False}, {'qualified': False}, {'session': 'new-card'}):
      publish_intent(stamp + 20_000_000, **changes)
      sd.sm.update(100)
      assert current_intent(sd.sm, car_state_ns=stamp, now_ns=stamp + 23_000_000, previous=previous) is None


def _queued_publication():
  from openpilot.starpilot.aol.intent_companion import IntentCompanion

  pm = messaging.PubMaster(['carState', 'carOutput', 'aolIntentWire'])
  sd = SelfdriveD.__new__(SelfdriveD)
  sd.sm = messaging.SubMaster(['aolIntentWire'])
  sd.car_state_sock = messaging.sub_sock('carState', timeout=1)
  sd.aol_intent_companion = IntentCompanion(messaging.sub_sock('aolIntentWire', conflate=False))
  sd.initialized, sd.enabled = True, False
  sd.aol_car_state_log_ns, sd.conditional_car_state_valid = 0, False
  sd.CS_prev = car.CarState.new_message(canValid=True, gearShifter=car.CarState.GearShifter.drive, vEgo=20.)
  cp = HondaInterface.get_params(HONDA.HONDA_CIVIC_BOSCH, gen_empty_fingerprint(), [], True, False, False)
  card = Car.__new__(Car)
  card.__dict__.update(sm=SimpleNamespace(frame=1, all_checks=lambda _: True), pm=pm, CP=cp,
    car_params_published=True, slc_replay=False, curve_replay=False, conditional_replay=False,
    last_actuators_output=car.CarControl.Actuators.new_message(), can_rcv_cum_timeout_counter=0,
    rk=SimpleNamespace(remaining=0), aol_replay=True, aol_qualified=True, aol_sequence=0,
    slc_producer_session='card', aol_card_intent=SimpleNamespace(allowed_latch=True, output=lambda _: (True, False, False)),
    v_cruise_helper=SimpleNamespace(slc_cruise_change=None))
  initialize_publication_sources(card)
  return card, sd, time.monotonic_ns()


def _publish_card(card, state, stamp):
  create = messaging.new_message

  def stamped(service, *args, **kwargs):
    message = create(service, *args, **kwargs)
    if service == 'carState':
      message.logMonoTime = stamp
    return message

  with patch('openpilot.selfdrive.car.card.messaging.new_message', side_effect=stamped):
    card.state_publish(state, None)


def _paired(sd, source, now):
  return current_intent(sd.sm, car_state_ns=source, now_ns=now, companion=sd.aol_intent_companion)


def test_first_seen_queued_car_state_keeps_its_original_card_intent():
  with OpenpilotPrefix():
    messaging.reset_context()
    card, sd, stamp = _queued_publication()
    # A has never been admitted before the conflated consumer advances to B.
    _publish_card(card, sd.CS_prev, stamp)
    _publish_card(card, sd.CS_prev, stamp + 10_000_000)
    sd.sm.update(100)
    assert sd.sm.logMonoTime['aolIntentWire'] == stamp + 10_000_000
    sd.CS_prev = sd.data_sample()
    assert sd.aol_car_state_log_ns == stamp
    assert current_intent(sd.sm, car_state_ns=stamp, now_ns=stamp + 20_000_000) is None
    original = _paired(sd, stamp, stamp + 20_000_000)
    assert original is not None
    assert original.carStateLogMonoTime == original.observedMonoTime == stamp
    assert original.validUntilMonoTime == stamp + 200_000_000
    assert original.sequence == 1
    assert _paired(sd, stamp - 1, stamp + 20_000_000) is None
    assert _paired(sd, stamp + 1, stamp + 20_000_000) is None
    assert _paired(sd, stamp, stamp + 30_000_000) == original
    assert _paired(sd, stamp, stamp + 30_000_001) is None


def test_queued_next_car_state_is_not_limited_to_previously_admitted_pair():
  with OpenpilotPrefix():
    messaging.reset_context()
    card, sd, stamp = _queued_publication()
    _publish_card(card, sd.CS_prev, stamp)
    sd.CS_prev = sd.data_sample()
    prior = _paired(sd, stamp, stamp + 1_000_000)
    assert prior is not None
    for offset in (6_555_568, 17_161_461, 23_116_265):
      _publish_card(card, sd.CS_prev, stamp + offset)
    sd.sm.update(100)
    sd.CS_prev = sd.data_sample()
    source = stamp + 6_555_568
    now = stamp + 23_336_153
    assert sd.aol_car_state_log_ns == source
    assert current_intent(sd.sm, car_state_ns=source, now_ns=now, previous=prior) is None
    matched = _paired(sd, source, now)
    assert matched is not None
    assert matched.carStateLogMonoTime == matched.observedMonoTime == source
    assert matched.sequence == 2
    assert matched.allowedLatch
    # Retaining this exact CAN pair preserves its original lease, then expires.
    assert _paired(sd, source, source + 30_000_000) == matched
    assert _paired(sd, source, source + 30_000_001) is None


@pytest.mark.parametrize('changes', [{'allowedLatch': False}, {'pauseLateral': True}, {'pauseLongitudinal': True},
                                   {'settingsQualified': False}, {'producerSessionId': 'new-card'},
                                   {'valid': False}, {'malformed': True}],
                         ids=['allowed-off', 'lateral-pause', 'longitudinal-pause', 'settings-off',
                              'new-session', 'invalid', 'malformed'])
def test_newer_intent_denials_cannot_be_hidden_by_cached_pair(changes):
  from dataclasses import replace

  with OpenpilotPrefix():
    messaging.reset_context()
    card, sd, stamp = _queued_publication()
    _publish_card(card, sd.CS_prev, stamp)
    sd.CS_prev = sd.data_sample()
    original = _paired(sd, stamp, stamp + 1_000_000)
    assert original is not None
    fields = {key: value for key, value in changes.items() if key not in ('valid', 'malformed')}
    at = stamp + 10_000_000
    later = replace(original, sequence=2, carStateLogMonoTime=at, observedMonoTime=at,
                    validUntilMonoTime=at + 200_000_000, **fields)
    message = messaging.new_message('aolIntentWire', 0, valid=changes.get('valid', True))
    message.logMonoTime = at
    message.aolIntentWire = b'invalid' if changes.get('malformed') else encode_intent(later)
    card.pm.send('aolIntentWire', message)
    sd.sm.update(100)
    result = _paired(sd, stamp, stamp + 20_000_000)
    if set(changes) & {'settingsQualified', 'producerSessionId', 'valid', 'malformed'}:
      assert result is None
    else:
      assert result is not None
      assert result.carStateLogMonoTime == result.observedMonoTime == stamp
      assert result.validUntilMonoTime == original.validUntilMonoTime
      assert result.allowedLatch == (original.allowedLatch and later.allowedLatch)
      assert result.pauseLateral == (original.pauseLateral or later.pauseLateral)
      assert result.pauseLongitudinal == (original.pauseLongitudinal or later.pauseLongitudinal)


@pytest.mark.parametrize('malformed_between', [False, True], ids=['contiguous', 'malformed-gap'])
def test_session_restart_cannot_reuse_original_pair(malformed_between):
  from dataclasses import replace

  with OpenpilotPrefix():
    messaging.reset_context()
    card, sd, stamp = _queued_publication()
    _publish_card(card, sd.CS_prev, stamp)
    sd.CS_prev = sd.data_sample()
    original = _paired(sd, stamp, stamp + 1_000_000)
    assert original is not None
    for offset, session in ((10_000_000, 'new-card'), (20_000_000, 'card')):
      if malformed_between:
        malformed = messaging.new_message('aolIntentWire', 0, valid=True)
        malformed.logMonoTime = stamp + offset - 1_000_000
        malformed.aolIntentWire = b'invalid'
        card.pm.send('aolIntentWire', malformed)
        sd.sm.update(100)
        assert _paired(sd, stamp, stamp + offset) is None
      at = stamp + offset
      message = messaging.new_message('aolIntentWire', 0, valid=True)
      message.logMonoTime = at
      message.aolIntentWire = encode_intent(replace(original, producerSessionId=session, sequence=1,
        carStateLogMonoTime=at, observedMonoTime=at, validUntilMonoTime=at + 200_000_000))
      card.pm.send('aolIntentWire', message)
      sd.sm.update(100)
      assert _paired(sd, stamp, at + 1_000_000) is None


@pytest.mark.parametrize('conflict', ['sequence', 'duplicate', 'invalid_duplicate'],
                         ids=['sequence', 'duplicate', 'invalid-duplicate'])
def test_sequence_and_duplicate_conflicts_withdraw_cached_intent(conflict):
  from dataclasses import replace

  with OpenpilotPrefix():
    messaging.reset_context()
    card, sd, stamp = _queued_publication()
    _publish_card(card, sd.CS_prev, stamp)
    sd.CS_prev = sd.data_sample()
    original = _paired(sd, stamp, stamp + 1_000_000)
    assert original is not None
    at = stamp + 10_000_000 if conflict == 'sequence' else stamp
    message = messaging.new_message('aolIntentWire', 0, valid=conflict != 'invalid_duplicate')
    message.logMonoTime = at
    message.aolIntentWire = encode_intent(replace(original, pauseLateral=conflict == 'duplicate',
      carStateLogMonoTime=at, observedMonoTime=at, validUntilMonoTime=at + 200_000_000))
    card.pm.send('aolIntentWire', message)
    sd.sm.update(100)
    assert _paired(sd, stamp, stamp + 20_000_000) is None


def test_queue_overflow_is_bounded_and_cannot_grant_authority():
  from openpilot.starpilot.aol.intent_companion import MAX_COMPANIONS, MAX_DRAIN

  with OpenpilotPrefix():
    messaging.reset_context()
    card, sd, stamp = _queued_publication()
    for tick in range(MAX_DRAIN + 1):
      _publish_card(card, sd.CS_prev, stamp + tick * 100_000)
    sd.sm.update(100)
    assert _paired(sd, stamp, stamp + 10_000_000) is None
    assert len(sd.aol_intent_companion.samples) <= MAX_COMPANIONS
    assert _paired(sd, stamp, stamp + 10_000_000) is None
    assert len(sd.aol_intent_companion.samples) <= MAX_COMPANIONS
    # Evicted older authority cannot be reconstructed by a later backfill.
    old = messaging.new_message('aolIntentWire', 0, valid=True)
    old.logMonoTime = stamp
    old.aolIntentWire = encode_intent(IntentState('card', 1, stamp, stamp, stamp + 200_000_000,
                                                 True, False, False, True, True))
    card.pm.send('aolIntentWire', old)
    sd.sm.update(100)
    assert _paired(sd, stamp, stamp + 10_000_000) is None
    _publish_card(card, sd.CS_prev, stamp + 4_000_000)
    sd.sm.update(100)
    assert _paired(sd, stamp + 4_000_000, stamp + 10_000_000) is not None
    assert _paired(sd, stamp, stamp + 10_000_000) is None
    # Exhausting the drain budget cannot reset the producer's accepted sequence.
    at = stamp + 5_000_000
    message = messaging.new_message('aolIntentWire', 0, valid=True)
    message.logMonoTime = at
    message.aolIntentWire = encode_intent(IntentState('card', 1, at, at, at + 200_000_000,
                                                     True, False, False, True, True))
    card.pm.send('aolIntentWire', message)
    sd.sm.update(100)
    assert _paired(sd, at, stamp + 10_000_000) is None


def test_true_card_publication_gap_keeps_original_thirty_ms_withdrawal():
  with OpenpilotPrefix():
    messaging.reset_context()
    card, sd, stamp = _queued_publication()
    _publish_card(card, sd.CS_prev, stamp)
    sd.CS_prev = sd.data_sample()
    assert _paired(sd, stamp, stamp + 28_885_658) is not None
    now = stamp + 53_402_671
    with patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', return_value=now):
      assert sd.data_sample() is sd.CS_prev
    assert sd.aol_car_state_log_ns == 0
    assert not sd.conditional_car_state_valid
    assert _paired(sd, sd.aol_car_state_log_ns, now) is None
    _publish_card(card, sd.CS_prev, stamp + 80_877_165)
    sd.CS_prev = sd.data_sample()
    assert _paired(sd, stamp, stamp + 80_877_165) is None


def test_expired_sample_does_not_reset_producer_sequence():
  from dataclasses import replace

  with OpenpilotPrefix():
    messaging.reset_context()
    card, sd, stamp = _queued_publication()
    _publish_card(card, sd.CS_prev, stamp)
    sd.CS_prev = sd.data_sample()
    original = _paired(sd, stamp, stamp + 1_000_000)
    assert original is not None
    assert _paired(sd, stamp, stamp + 30_000_001) is None
    at = stamp + 40_000_000
    message = messaging.new_message('aolIntentWire', 0, valid=True)
    message.logMonoTime = at
    message.aolIntentWire = encode_intent(replace(original, sequence=0, carStateLogMonoTime=at,
      observedMonoTime=at, validUntilMonoTime=at + 200_000_000))
    card.pm.send('aolIntentWire', message)
    sd.sm.update(100)
    assert _paired(sd, at, at + 1_000_000) is None


def _known_older_sm_pair(*, latest_changes=None):
  from dataclasses import replace
  from openpilot.starpilot.aol.intent_companion import IntentCompanion

  prior, source, later, now = 1_081_445_990_726, 1_081_451_053_291, 1_081_455_731_297, 1_081_457_492_005
  companion = IntentCompanion(object())
  original = IntentState('card', 1, prior, prior, prior + 200_000_000, True, False, False, True, True, True)
  pair = replace(original, sequence=2, carStateLogMonoTime=source, observedMonoTime=source,
                 validUntilMonoTime=source + 200_000_000)
  latest = replace(original, sequence=3, carStateLogMonoTime=later, observedMonoTime=later,
                   validUntilMonoTime=later + 200_000_000, **(latest_changes or {}))
  for intent in (original, pair, latest):
    companion._observe(intent.carStateLogMonoTime, True, encode_intent(intent))
  class SM(dict):
    pass
  sm = SM(aolIntentWire=encode_intent(original))
  sm.seen = sm.valid = sm.alive = {'aolIntentWire': True}
  sm.logMonoTime = {'aolIntentWire': prior}
  return companion, sm, pair, latest, now


@pytest.mark.parametrize('changes', [{}, {'allowedLatch': False}, {'pauseLateral': True},
                                   {'pauseLongitudinal': True}, {'lateralArmed': False}, {'optionalSetRelease': False}])
def test_known_older_sm_pair_folds_all_restrictions_without_renewing_source(changes):
  companion, sm, pair, latest, now = _known_older_sm_pair(latest_changes=changes)
  with patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none', return_value=None):
    result = current_intent(sm, car_state_ns=pair.carStateLogMonoTime, now_ns=now, companion=companion)
    assert result is not None
    assert result.carStateLogMonoTime == result.observedMonoTime == pair.carStateLogMonoTime
    assert result.validUntilMonoTime == pair.validUntilMonoTime
    assert result.allowedLatch == (pair.allowedLatch and latest.allowedLatch)
    assert result.lateralArmed == (pair.lateralArmed and latest.lateralArmed)
    assert result.pauseLateral == (pair.pauseLateral or latest.pauseLateral)
    assert result.pauseLongitudinal == (pair.pauseLongitudinal or latest.pauseLongitudinal)
    assert result.optionalSetRelease == (pair.optionalSetRelease and latest.optionalSetRelease)
    assert current_intent(sm, car_state_ns=pair.carStateLogMonoTime,
      now_ns=pair.carStateLogMonoTime + 30_000_001, companion=companion) is None


@pytest.mark.parametrize('fault', ['invalid', 'malformed', 'conflicting-duplicate', 'session', 'stale', 'unseen-backwards', 'future'])
def test_older_sm_pair_still_rejects_unknown_corrupt_restart_and_expired_samples(fault):
  from dataclasses import replace

  companion, sm, pair, latest, now = _known_older_sm_pair()
  prior = companion.samples[sm.logMonoTime['aolIntentWire']][2]
  if fault == 'invalid':
    sm.valid = {'aolIntentWire': False}
  elif fault == 'malformed':
    sm['aolIntentWire'] = b'invalid'
  elif fault in ('conflicting-duplicate', 'session'):
    sm['aolIntentWire'] = encode_intent(replace(prior, pauseLateral=True) if fault == 'conflicting-duplicate'
      else replace(prior, producerSessionId='new-card'))
  elif fault == 'stale':
    now = prior.carStateLogMonoTime + 30_000_001
  else:
    at = prior.carStateLogMonoTime - 1 if fault == 'unseen-backwards' else now + 1
    sm.logMonoTime = {'aolIntentWire': at}
    sm['aolIntentWire'] = encode_intent(replace(prior, sequence=0 if fault == 'unseen-backwards' else 4,
      carStateLogMonoTime=at, observedMonoTime=at, validUntilMonoTime=at + 200_000_000))
  with patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none', return_value=None):
    assert current_intent(sm, car_state_ns=pair.carStateLogMonoTime, now_ns=now, companion=companion) is None
