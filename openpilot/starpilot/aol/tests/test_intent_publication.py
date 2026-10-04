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
