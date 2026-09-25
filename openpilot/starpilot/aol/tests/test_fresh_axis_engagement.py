"""Fresh proofs preserve accepted engagement, while real revocation remains sticky.

These tests use actual SelfdriveD event/state owners and Controls; fixture transport
and clocks are synthetic. Card checks cover its existing intent-feedback owner.
"""

from contextlib import ExitStack

from unittest import mock

from dataclasses import replace

from collections import deque


import pytest

from openpilot.cereal import log, messaging

from openpilot.common.prefix import OpenpilotPrefix

from openpilot.selfdrive.selfdrived import selfdrived as owner

from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture

from openpilot.starpilot.aol.tests.test_carstate_queue import message

from openpilot.starpilot.aol.wire import IntentState, encode_intent, decode_safety, encode_safety

BASE = 10_000_000_000

OLD_SOURCE = BASE + 15_677_616

RENEWAL_TIME = BASE + 51_614_499

FRESH_SOURCE = BASE + 48_648_729


def wire(ns, seq, **kw):
  m = messaging.new_message('aolIntentWire', 0, valid=True, logMonoTime=ns)
  v = IntentState('authority-card', seq, ns, ns, ns + 200_000_000, False, False, False, True, False)
  m.aolIntentWire = encode_intent(replace(v, **kw))
  return m


def authority_callers(stack, full=True):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  stack.callback(case.doCleanups)
  sd, controls, step, card, receive = case._ioniq_availability_callers(full_op=full)
  axis, _, cmd = step(2, state_stamp=OLD_SOURCE, intent_message=wire(OLD_SOURCE, 3, allowedLatch=not full, lateralArmed=not full), latched=not full)
  assert axis.lateralActive and cmd.latActive
  assert axis.validUntilMonoTime == BASE + 50_000_000
  return sd, controls, step, card, receive, axis


@pytest.mark.parametrize(
  'case',
  [
    'healthy',
    'cancel',
    'brake',
    'regen',
    'gas_cancel',
    'native_long_deny',
    'native_lat_deny',
    'native_invalid',
    'panda_fault',
    'relay_fault',
    'permanent_eps',
    'can_invalid',
    'can_timeout',
    'disabled',
    'inhibited',
    'source_zero',
    'producer',
    'sequence',
    'intent_pause',
    'future_intent',
    'settings',
    'model',
    'critical',
  ],
)
def test_gap_owner_boundaries(case):
  with ExitStack() as stack, OpenpilotPrefix():
    sd, controls, step, card, receive, old = authority_callers(stack)
    state = fixture.car_state()
    kwargs = {}
    w = wire(FRESH_SOURCE, 4)
    if case == 'cancel':
      state.buttonEvents = [fixture.car.CarState.ButtonEvent(type=fixture.car.CarState.ButtonEvent.Type.cancel, pressed=True)]
    elif case == 'brake':
      state.brakePressed = True
    elif case == 'regen':
      state.regenBraking = True
    elif case == 'gas_cancel':
      kwargs['gas'] = True
      sd.disengage_on_accelerator = True
    elif case == 'native_long_deny':
      kwargs['long_allowed'] = False
    elif case == 'native_lat_deny':
      kwargs['allowed'] = False
    elif case == 'native_invalid':
      kwargs['native_valid'] = False
    elif case == 'panda_fault':
      kwargs['panda_fault'] = True
    elif case == 'relay_fault':
      kwargs['relay_fault'] = True
    elif case == 'permanent_eps':
      state.steerFaultPermanent = True
    elif case == 'can_invalid':
      state.canValid = False
    elif case == 'can_timeout':
      state.canTimeout = True
    elif case == 'disabled':
      sd.state_machine.state = log.SelfdriveState.OpenpilotState.disabled
      sd.enabled = sd.active = False
    elif case == 'inhibited':
      sd.aol_availability_long_inhibit = True
    elif case == 'source_zero':
      with mock.patch.object(owner.time, 'monotonic_ns', return_value=BASE + 49_000_000):
        sd._expire_axis_source(state, BASE + 49_000_000)
      fixture.assert_ordinary_source_pause(sd, publication_only=True)
      assert old.validUntilMonoTime == BASE + 50_000_000
      with mock.patch.object(owner.time, 'monotonic_ns', return_value=old.validUntilMonoTime + 1):
        expired, _ = controls.state_control()
      assert not expired.latActive and not expired.longActive
    elif case == 'producer':
      w = wire(FRESH_SOURCE, 4, producerSessionId='new-card')
    elif case == 'sequence':
      w = wire(FRESH_SOURCE, 3)
    elif case == 'intent_pause':
      w = wire(FRESH_SOURCE, 4, pauseLongitudinal=True, pauseLateral=True)
    elif case == 'future_intent':
      w = wire(FRESH_SOURCE, 4, observedMonoTime=RENEWAL_TIME + 1)
    elif case == 'settings':
      w = wire(FRESH_SOURCE, 4, settingsQualified=False)
    elif case == 'model':
      cal = messaging.new_message('extrinsicsCalibration', valid=True, logMonoTime=RENEWAL_TIME)
      cal.extrinsicsCalibration.calStatus = 'uncalibrated'
      sd.sm.update_msgs(RENEWAL_TIME / 1e9, [cal.as_reader()])
    elif case == 'critical':
      kwargs['critical_event'] = log.OnroadEvent.EventName.controlsMismatch
    axis, pub, cmd = step(5, state_stamp=FRESH_SOURCE, intent_message=w, offset_ns=1_614_499, latched=False, observed_state=state, **kwargs)
    healthy = case in ('healthy', 'source_zero')
    assert cmd.longActive == healthy, (case, pub.to_dict(), axis.to_dict())
    assert axis.longitudinalActive == healthy
    if case in (
      'cancel',
      'brake',
      'regen',
      'gas_cancel',
      'native_long_deny',
      'native_lat_deny',
      'native_invalid',
      'panda_fault',
      'relay_fault',
      'permanent_eps',
      'can_invalid',
      'can_timeout',
      'disabled',
      'inhibited',
      'producer',
      'sequence',
      'future_intent',
      'settings',
      'model',
      'critical',
    ):
      again, _, cmd2 = step(6, intent_message=wire(BASE + 60_000_000, 5), latched=False)
      assert not again.longitudinalActive and not cmd2.longActive, (case, again.to_dict())
    if healthy:
      fixture.assert_fresh_ordinary_recovery(sd, axis, cmd, FRESH_SOURCE)
      assert not sd.aol_authority_lost and not getattr(sd, 'aol_availability_long_inhibit', False)
      assert axis.sourceCarStateMonoTime == FRESH_SOURCE and axis.validUntilMonoTime == RENEWAL_TIME + 30_000_000
      assert old.validUntilMonoTime == BASE + 50_000_000


@pytest.mark.parametrize('pulse', ['cancel', 'brake', 'regen', 'gas', 'invalid_envelope', 'permanent_eps'])
def test_queued_revoke_then_release_enable_cannot_renew(pulse):
  with ExitStack() as stack, OpenpilotPrefix():
    sd, controls, step, card, receive, old = authority_callers(stack)
    first = fixture.car_state()
    final = fixture.car_state()
    final.buttonEnable = True
    if pulse == 'cancel':
      first.buttonEvents = [fixture.car.CarState.ButtonEvent(type=fixture.car.CarState.ButtonEvent.Type.cancel, pressed=True)]
    elif pulse == 'brake':
      first.brakePressed = True
    elif pulse == 'regen':
      first.regenBraking = True
    elif pulse == 'gas':
      first.gasPressed = True
      sd.disengage_on_accelerator = True
    elif pulse == 'permanent_eps':
      first.steerFaultPermanent = True
    pending = deque([message(FRESH_SOURCE, final)])
    receive0 = messaging.recv_one_or_none
    # Hook data_sample's blocking read, after the fixture prepares its envelope.
    original = sd.data_sample

    def data():
      with (
        mock.patch.object(owner.messaging, 'recv_one', return_value=message(FRESH_SOURCE - 1_000_000, first, valid=pulse != 'invalid_envelope')),
        mock.patch.object(
          owner.messaging,
          'recv_one_or_none',
          side_effect=lambda sock: (pending.popleft() if pending else None) if sock is sd.car_state_sock else receive0(sock),
        ),
      ):
        return original()

    with mock.patch.object(sd, 'data_sample', side_effect=data):
      axis, pub, cmd = step(5, state_stamp=FRESH_SOURCE, intent_message=wire(FRESH_SOURCE, 4), offset_ns=1_614_499, latched=False)
    assert not axis.longitudinalActive and not cmd.longActive
    assert not sd.events.contains(fixture.ET.ENABLE)
    again, _, cmd2 = step(6, intent_message=wire(BASE + 60_000_000, 5), latched=False)
    assert not again.longitudinalActive and not cmd2.longActive


@pytest.mark.parametrize('card_latched', [False, True])
def test_controls_expire_before_fresh_renewal(card_latched):
  with ExitStack() as stack, OpenpilotPrefix():
    sd, controls, step, card, receive, old = authority_callers(stack)
    card.aol_card_intent.allowed_latch = card_latched
    before = sd.state_machine.state
    with mock.patch.object(owner.time, 'monotonic_ns', return_value=BASE + 50_000_001):
      expired, _ = controls.state_control()
      assert not expired.latActive and not expired.longActive
    receive(BASE + 50_000_001, state=fixture.car_state())
    assert sd.state_machine.state == before
    axis, pub, cmd = step(5, state_stamp=FRESH_SOURCE, intent_message=wire(FRESH_SOURCE, 4), offset_ns=1_614_499, latched=False)
    assert pub.enabled and axis.longitudinalActive and cmd.longActive


@pytest.mark.parametrize('change', ['axis_session', 'native_axis_session', 'native_long_deny', 'native_serial'])
def test_native_identity_at_renewal(change):
  with ExitStack() as stack, OpenpilotPrefix():
    sd, controls, step, card, receive, old = authority_callers(stack)
    original = sd.data_sample

    def data():
      result = original()
      if change == 'axis_session':
        sd.aol_session_id = 'replacement-session'
      else:
        value = decode_safety(sd.sm['aolSafetyWire'])
        kw = (
          {'axisSessionId': 'replacement-native-session'}
          if change == 'native_axis_session'
          else {'longitudinalAllowed': False}
          if change == 'native_long_deny'
          else {
            'pandaSerial': 'replacement-panda',
            'pandaInventory': tuple(
              replace(slot, hardwareSerial='replacement-panda') if slot.hardwareSerial == 'authority-panda' else slot for slot in value.pandaInventory
            ),
          }
        )
        sample = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=RENEWAL_TIME)
        sample.aolSafetyWire = encode_safety(replace(value, **kw))
        sd.sm.update_msgs(RENEWAL_TIME / 1e9, [sample.as_reader()])
      return result

    with mock.patch.object(sd, 'data_sample', side_effect=data):
      axis, pub, cmd = step(5, state_stamp=FRESH_SOURCE, intent_message=wire(FRESH_SOURCE, 4), offset_ns=1_614_499, latched=False)
    assert not axis.longitudinalActive and not cmd.longActive


def test_cancel_then_real_accepted_enable():
  with ExitStack() as stack, OpenpilotPrefix():
    sd, controls, step, card, receive, old = authority_callers(stack)
    cs = fixture.car_state()
    cs.buttonEvents = [fixture.car.CarState.ButtonEvent(type=fixture.car.CarState.ButtonEvent.Type.cancel, pressed=True)]
    axis, pub, cmd = step(5, state_stamp=FRESH_SOURCE, intent_message=wire(FRESH_SOURCE, 4), offset_ns=1_614_499, latched=False, observed_state=cs)
    assert not pub.enabled and not cmd.longActive
    axis, pub, cmd = step(6, intent_message=wire(BASE + 60_000_000, 5), latched=False)
    assert not pub.enabled and not cmd.longActive
    enabled = fixture.car_state()
    enabled.buttonEnable = True
    axis, pub, cmd = step(7, intent_message=wire(BASE + 70_000_000, 6), latched=False, observed_state=enabled)
    assert sd.events.contains(fixture.ET.ENABLE)
    assert pub.enabled and cmd.longActive and axis.longitudinalActive


@pytest.mark.parametrize('delivery', ['burst', 'split', 'healthy_fresh'])
def test_prior_intent_drains_cannot_hide_restrictions_during_early_hold(delivery):
  with ExitStack() as stack, OpenpilotPrefix():
    sd, _, step, _, _, old = authority_callers(stack)
    sd.car_state_poller = mock.Mock()
    sd.car_state_poller.poll.return_value = []
    now = [OLD_SOURCE + 29_900_000]
    original_health = sd.update_process_health
    original_receive = messaging.recv_one_or_none
    denied = wire(BASE + 46_000_000, 4, pauseLateral=True, pauseLongitudinal=True).as_reader()
    permitted = wire(BASE + 46_000_001, 5).as_reader()
    queue = deque([denied, permitted] if delivery == 'burst' else [denied, None, permitted, None])
    if delivery == 'healthy_fresh':
      queue = deque([wire(FRESH_SOURCE - 2, 4).as_reader(), wire(FRESH_SOURCE - 1, 5).as_reader()])
      now[0] = RENEWAL_TIME

    def health():
      result = original_health()
      if delivery != 'healthy_fresh':
        now[0] = BASE + 46_300_000
      return result

    def receive(sock):
      if sock is sd.aol_intent_companion.sock:
        return queue.popleft() if queue else None
      return original_receive(sock)

    with (
      mock.patch.object(owner.time, 'monotonic_ns', side_effect=lambda: now[0]),
      mock.patch.object(sd, 'update_process_health', side_effect=health),
      mock.patch.object(owner.messaging, 'recv_one_or_none', side_effect=receive),
    ):
      if delivery == 'healthy_fresh':
        axis, state, command = step(5, state_stamp=FRESH_SOURCE, intent_message=wire(FRESH_SOURCE, 6), offset_ns=1_614_499, latched=False)
      else:
        # Retain the already-consumed source while it is still fresh. Ordinary
        # event work crosses its source cutoff, and refresh drains intent first.
        axis, state, command = step(4, timeout=True, state_stamp=OLD_SOURCE, intent_message=wire(OLD_SOURCE, 3), offset_ns=6_300_000, latched=False)
    assert not queue
    assert not sd.aol_axis_publication_deferred
    if delivery == 'healthy_fresh':
      # Recording the count must not reject ordinary complete fresh decisions.
      assert axis.longitudinalActive and command.longActive and state.enabled
      assert axis.sourceCarStateMonoTime == FRESH_SOURCE
      assert sd.aol_step_intent_drain_count == 2
      following, _, command = step(6, intent_message=wire(BASE + 60_000_000, 7), latched=False)
      assert following.longitudinalActive and command.longActive
      assert sd.aol_step_intent_drain_count == 0
    else:
      assert not axis.longitudinalActive and not command.longActive
      assert old.validUntilMonoTime == BASE + 50_000_000
      assert sd.aol_step_intent_drain_count == 2
