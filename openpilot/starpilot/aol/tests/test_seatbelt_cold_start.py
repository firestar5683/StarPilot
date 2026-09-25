"""Cold factory admission through real native RX, Card, SelfdriveD and Controls."""
from contextlib import ExitStack
from dataclasses import replace
from unittest import mock

import pytest

from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.radar_interface import RadarInterface
from opendbc.car.structs import car
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car.card import Car
from openpilot.selfdrive.car.tests.test_hyundai_aol import candidate
from openpilot.selfdrive.selfdrived.events import ET, EventName
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.wire import decode_intent, decode_safety, encode_intent, encode_safety


def factory_callers(cleanup, full_op, *, pause_brake_mps=0., arm=True):
  params = Params()
  cleanup.callback(params._finalizer)
  for key, enabled in (('OpenpilotEnabledToggle', True), ('SafeMode', False), ('AlwaysOnLateral', True)):
    params.put_bool(key, enabled, block=True)
  params.put('AolBrakePauseSpeedMps', pause_brake_mps, block=True)
  if full_op:
    from opendbc.car.hyundai.tests import test_ioniq6_handoff as startup
    earned = startup.TestIoniq6PrepublicationHandoff(methodName='runTest')
    cleanup.callback(earned.doCleanups)
    captured = []
    real_interface = startup.CarInterface
    class Capture:
      get_params = staticmethod(real_interface.get_params)
      def __new__(cls, prepared):
        actual = real_interface(prepared)
        captured.append(actual.CP.as_reader().as_builder())
        return actual
    with mock.patch.object(startup, 'CarInterface', Capture):
      earned.assert_card_prepublication_fallback({})
    assert len(captured) == 1
    cp = captured[0]
    assert cp.openpilotLongitudinalControl and not cp.pcmCruise
    assert int(cp.safetyConfigs[-1].safetyParam) == 0x8815
  else:
    cp, _ = candidate(True)
    assert not cp.openpilotLongitudinalControl and cp.pcmCruise
  # The actual Card factory installs its marker; the test never inserts one.
  card = Car(CI=CarInterface(cp), RI=RadarInterface(cp))
  cleanup.callback(card.params._finalizer)
  assert not card.CP.passive and card.CI.CC is not None
  assert int(card.CP.safetyConfigs[-1].safetyParam) == (0x8815 if full_op else 0x0891)
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  cleanup.callback(case.doCleanups)
  real_selfdrived, constructor_settings = fixture.SelfdriveD, []
  def construct(*args, **kwargs):
    actual = real_selfdrived(*args, **kwargs)
    constructor_settings.append(actual.aol_settings)
    return actual
  with mock.patch.object(fixture, 'SelfdriveD', side_effect=construct):
    sd, controls, drive = case._authority_callers(False, cp=card.CP.as_reader().as_builder(), genuine_events=True)
  # The generic fixture clears settings; retain this actual constructor's snapshot.
  assert len(constructor_settings) == 1 and constructor_settings[0] is not None
  sd.aol_settings = constructor_settings[0]
  assert sd.aol_settings.enabled and sd.aol_settings.pause_brake_mps == pause_brake_mps
  cleanup.callback(sd.params._finalizer)
  cleanup.callback(controls.params._finalizer)
  assert sd.CP.as_builder().to_bytes() == card.CP.as_reader().as_builder().to_bytes()
  state = fixture.car_state()
  state.cruiseState.available, state.seatbeltUnlatched = True, True
  assert not card.aol_card_intent.allowed_latch
  if arm:
    card.aol_card_intent.update(state, now_ns=9_980_000_000)
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
    card.aol_card_intent.update(state, now_ns=9_990_000_000)
    assert card.aol_card_intent.allowed_latch
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=False)]
    card.aol_card_intent.update(state, now_ns=9_999_000_000)
    state.buttonEvents = []
  class Publisher:
    def __init__(self):
      self.messages = {}
    def send(self, service, message):
      self.messages[service] = messaging.log_from_bytes(message.to_bytes())
  cleanup.enter_context(mock.patch.object(card, 'pm', Publisher()))
  original_message = messaging.new_message
  def published_drive(tick, **kwargs):
    observed = kwargs['observed_state']
    now = 10_000_000_000 + tick * 10_000_000
    if 'latched' in kwargs:
      assert kwargs['latched'] == card.aol_card_intent.allowed_latch
    def stamped_message(*args, **options):
      options.setdefault('logMonoTime', now)
      return original_message(*args, **options)
    with mock.patch('openpilot.selfdrive.car.card.REPLAY', False), \
         mock.patch('openpilot.selfdrive.car.card.messaging.new_message', side_effect=stamped_message):
      card.state_publish(observed, None)
    actual = card.pm.messages['aolIntentWire'].as_builder()
    intent = decode_intent(actual.aolIntentWire)
    assert actual.valid and intent.producerSessionId == card.slc_producer_session
    assert intent.carStateLogMonoTime == card.pm.messages['carState'].logMonoTime == now
    assert intent.settingsQualified and intent.lateralArmed == card.aol_card_intent.allowed_latch
    kwargs['intent_message'] = actual
    return drive(tick, **kwargs)
  return card, sd, controls, published_drive, state


def deliver_card(card, sd, controls, state, tick):
  now = 10_000_000_000 + tick * 10_000_000
  rows = [sd.pm.messages['aolAxisState'], sd.pm.messages['onroadEvents'], controls.pm.messages['carControl']]
  for service in ('pandaStates', 'aolSafetyWire', 'deviceState'):
    event = messaging.new_message(service, len(sd.sm[service]) if service in ('pandaStates', 'aolSafetyWire') else None,
                                  valid=sd.sm.valid[service], logMonoTime=sd.sm.logMonoTime[service])
    setattr(event, service, sd.sm[service])
    rows.append(messaging.log_from_bytes(event.to_bytes()))
  # Retain the prior observation between publications; do not replay it as new RX.
  delivered = getattr(card, '_cold_test_delivered', {})
  fresh = []
  for row in rows:
    signature = row.as_builder().to_bytes()
    if delivered.get(row.which()) != signature:
      delivered[row.which()] = signature
      fresh.append(row)
  card._cold_test_delivered = delivered
  card.sm.update_msgs(now / 1e9, fresh)
  card.CC_prev = card.sm['carControl']
  with mock.patch('openpilot.selfdrive.car.card.messaging.drain_sock_raw', return_value=[b'fixture']), \
       mock.patch('openpilot.selfdrive.car.card.can_capnp_to_list', return_value=[]), \
       mock.patch('openpilot.selfdrive.car.card.time.monotonic_ns', return_value=now), \
       mock.patch('openpilot.selfdrive.car.card.REPLAY', False), \
       mock.patch.object(card.CI, 'update', return_value=state), \
       mock.patch.object(card.RI, 'update', return_value=None), mock.patch.object(card.sm, 'update'):
    actual, _ = card.state_update()
  assert actual is state


@pytest.mark.parametrize('full_op', [False, True])
@pytest.mark.parametrize('fault', ['none', 'denied', 'missing', 'expired_native', 'wrong_session', 'wrong_inventory',
                                 'expired_intent', 'door', 'permanent_eps', 'temporary_eps', 'hard'])
def test_cold_unbelted_request_preserves_all_authority_guards(full_op, fault):
  with OpenpilotPrefix(), ExitStack() as cleanup:
    card, sd, _, drive, state = factory_callers(cleanup, full_op)
    actual_update = sd.sm.update_msgs
    def frames(t, rows):
      changed = []
      for row in rows:
        if row.which() == 'aolSafetyWire' and fault in ('missing', 'expired_native', 'wrong_session', 'wrong_inventory'):
          if fault == 'missing':
            continue
          builder = row.as_builder()
          native = decode_safety(builder.aolSafetyWire)
          if fault == 'expired_native':
            native = replace(native, observedMonoTime=9_700_000_000, validUntilMonoTime=9_900_000_000)
          elif fault == 'wrong_session':
            native = replace(native, axisSessionId='different-session')
          else:
            native = replace(native, pandaInventory=tuple(replace(slot, safetyParam=slot.safetyParam ^ 1)
                                                          for slot in native.pandaInventory))
          builder.aolSafetyWire = encode_safety(native)
          row = builder.as_reader()
        if row.which() == 'aolIntentWire' and fault == 'expired_intent':
          builder = row.as_builder()
          intent = decode_intent(builder.aolIntentWire)
          builder.aolIntentWire = encode_intent(replace(intent, observedMonoTime=9_700_000_000,
                                                       validUntilMonoTime=9_900_000_000))
          row = builder.as_reader()
        changed.append(row)
      return actual_update(t, changed)
    state.doorOpen = fault == 'door'
    state.steerFaultPermanent, state.steerFaultTemporary = fault == 'permanent_eps', fault == 'temporary_eps'
    options = {'native_request_long': False, 'native_request_lat': fault == 'denied', 'allowed': False}
    if fault == 'hard':
      options['critical_event'] = EventName.controlsMismatch
    with mock.patch.object(sd.sm, 'update_msgs', side_effect=frames):
      axis, _, command = drive(0, observed_state=state, latched=card.aol_card_intent.allowed_latch, **options)
    assert not axis.longitudinalActive and not command.longActive
    assert not axis.lateralActive and not command.latActive
    if fault != 'none':
      assert axis.faultReason != 'none' or not axis.desiredLateral
      return
    assert axis.desiredLateral and axis.faultReason == 'none'
    axis, _, command = drive(1, observed_state=state, latched=card.aol_card_intent.allowed_latch,
                             native_request_long=False, native_request_lat=True, allowed=True)
    assert axis.faultReason == 'none' and axis.lateralActive and command.latActive
    assert not sd.enabled and not axis.desiredLongitudinal and not command.longActive
    assert EventName.seatbeltNotLatched in sd.events.names and sd.events.contains(ET.NO_ENTRY)


@pytest.mark.parametrize('full_op', [False, True])
def test_cold_unbelted_native_grant_card_feedback_brake_and_lkas(full_op):
  from opendbc.safety.tests.test_hyundai_ioniq6_stock_aol import TestHyundaiIoniq6StockAol
  with OpenpilotPrefix(), ExitStack() as cleanup:
    card, sd, controls, drive, state = factory_callers(cleanup, full_op, pause_brake_mps=10.)
    native = TestHyundaiIoniq6StockAol(methodName='runTest')
    native.mode(int(card.CP.safetyConfigs[-1].safetyParam))
    native.safety.set_alternative_experience(int(card.CP.alternativeExperience))
    if full_op:
      # Full-OP preflight has disabled stock SCC. Receiving SCC_CONTROL here
      # is a real relay fault, so supply only the native required RX inventory.
      for name, values in (('ACCELERATOR', {'GEAR': 5}), ('TCS', {}), ('WHEEL_SPEEDS', {}),
                           ('MDPS', {}), ('CRUISE_BUTTONS', {})):
        native.rx(name, values)
    else:
      native.healthy()
    assert native.safety.aol_rx_healthy() and not native.safety.get_relay_malfunction()
    native.safety.set_aol_test_heartbeat(True)
    native.safety.aol_set_host_request(0)
    assert native.safety.aol_get_permission_mask() == 0
    native.rx('CRUISE_BUTTONS', {'LDA_BTN': 1})
    native.rx('CRUISE_BUTTONS', {})

    def receive(tick):
      deliver_card(card, sd, controls, state, tick)

    axis, _, command = drive(0, observed_state=state, latched=True, allowed=False,
                             native_request_lat=False, native_request_long=False)
    assert axis.desiredLateral and not axis.lateralActive and not command.latActive and not command.longActive
    assert axis.faultReason == 'none'
    receive(0)
    assert card.aol_card_intent.allowed_latch
    native.safety.aol_set_host_request(int(axis.desiredLateral))
    mask = native.safety.aol_get_permission_mask()
    assert mask == 1
    axis, _, command = drive(1, observed_state=state, latched=card.aol_card_intent.allowed_latch,
                             allowed=bool(mask & 1), native_request_lat=True, native_request_long=False)
    assert axis.lateralActive and command.latActive and not axis.longitudinalActive and not command.longActive
    receive(1)
    assert card.aol_card_intent.allowed_latch
    state.brakePressed = True
    native.rx('TCS', {'DriverBraking': 1})
    assert native.safety.aol_get_permission_mask() == 1
    axis, _, command = drive(2, observed_state=state, latched=True, native_request_long=False)
    assert axis.lateralActive and command.latActive and not command.longActive
    receive(2)
    assert card.aol_card_intent.allowed_latch
    state.vEgo = 2.
    axis, _, command = drive(3, observed_state=state, latched=True, native_request_long=False)
    assert not axis.lateralActive and not command.latActive and not command.longActive
    receive(3)
    assert card.aol_card_intent.allowed_latch
    state.vEgo = 20.
    state.brakePressed, state.seatbeltUnlatched = False, False
    axis, _, command = drive(4, observed_state=state, latched=True, native_request_long=False)
    assert axis.lateralActive and not sd.enabled and not axis.desiredLongitudinal and not command.longActive
    receive(4)
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
    card.aol_card_intent.update(state, now_ns=10_050_000_000)
    native.rx('CRUISE_BUTTONS', {'LDA_BTN': 1})
    native.rx('CRUISE_BUTTONS', {})
    assert not card.aol_card_intent.allowed_latch
    state.buttonEvents = []
    axis, _, command = drive(5, observed_state=state, latched=False, native_request_long=False)
    assert not axis.desiredLateral and not axis.lateralActive and not command.latActive and not command.longActive
    native.safety.aol_set_host_request(int(axis.desiredLateral))
    assert native.safety.aol_get_permission_mask() == 0
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=False)]
    card.aol_card_intent.update(state, now_ns=10_060_000_000)
    state.seatbeltUnlatched = True
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
    card.aol_card_intent.update(state, now_ns=10_070_000_000)
    assert card.aol_card_intent.allowed_latch
    native.rx('CRUISE_BUTTONS', {'LDA_BTN': 1})
    native.rx('CRUISE_BUTTONS', {})
    state.buttonEvents = []
    pending, _, command = drive(7, observed_state=state, latched=True, allowed=False,
                                native_request_lat=False, native_request_long=False)
    assert pending.desiredLateral and not pending.lateralActive and not command.latActive and not command.longActive
    native.safety.aol_set_host_request(int(pending.desiredLateral))
    assert native.safety.aol_get_permission_mask() == 1
    axis, _, command = drive(8, observed_state=state, latched=True, native_request_long=False)
    assert axis.lateralActive and command.latActive and not sd.enabled and not command.longActive
    receive(8)
    assert card.aol_card_intent.allowed_latch


@pytest.mark.parametrize('full_op', [False, True])
@pytest.mark.parametrize('missing_bootstrap', [False, True])
def test_cold_unbelted_off_feedback_allows_the_first_actual_card_lkas_press(full_op, missing_bootstrap):
  from opendbc.safety.tests.test_hyundai_ioniq6_stock_aol import TestHyundaiIoniq6StockAol
  with OpenpilotPrefix(), ExitStack() as cleanup:
    card, sd, controls, drive, state = factory_callers(cleanup, full_op, arm=False)
    native = TestHyundaiIoniq6StockAol(methodName='runTest')
    native.mode(int(card.CP.safetyConfigs[-1].safetyParam))
    native.safety.set_alternative_experience(int(card.CP.alternativeExperience))
    if full_op:
      for name, values in (('ACCELERATOR', {'GEAR': 5}), ('TCS', {}), ('WHEEL_SPEEDS', {}),
                           ('MDPS', {}), ('CRUISE_BUTTONS', {})):
        native.rx(name, values)
    else:
      native.healthy()
    assert native.safety.aol_rx_healthy() and not native.safety.get_relay_malfunction()
    native.safety.set_aol_test_heartbeat(True)
    native.safety.aol_set_host_request(0)
    assert native.safety.aol_get_permission_mask() == 0
    if missing_bootstrap:
      denied, _, command = drive(-1, observed_state=state, latched=False, allowed=False, native_valid=False,
                                 native_request_lat=False, native_request_long=False)
      assert denied.faultReason == 'critical' and not denied.desiredLateral
      assert not command.latActive and not command.longActive
      deliver_card(card, sd, controls, state, -1)
      assert not card.aol_card_intent.allowed_latch and card.aol_card_intent._fault_inhibit
    # Deliver the actual inactive, unbelted publication before any arming gesture.
    axis, _, command = drive(0, observed_state=state, latched=False, allowed=False,
                             native_request_lat=False, native_request_long=False)
    assert not axis.desiredLateral and not axis.lateralActive and not command.latActive and not command.longActive
    assert axis.faultReason == 'none'
    deliver_card(card, sd, controls, state, 0)
    assert not card.aol_card_intent.allowed_latch and not card.aol_card_intent._fault_inhibit
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
    native.rx('CRUISE_BUTTONS', {'LDA_BTN': 1})
    native.rx('CRUISE_BUTTONS', {})
    deliver_card(card, sd, controls, state, 1)
    assert card.aol_card_intent.allowed_latch
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=False)]
    deliver_card(card, sd, controls, state, 2)
    pending, _, command = drive(2, observed_state=state, latched=True, allowed=False,
                                native_request_lat=False, native_request_long=False)
    assert pending.desiredLateral and not pending.lateralActive and not command.latActive and not command.longActive
    assert pending.faultReason == 'none'
    deliver_card(card, sd, controls, state, 2)
    assert card.aol_card_intent.allowed_latch
    native.safety.aol_set_host_request(int(pending.desiredLateral))
    assert native.safety.aol_get_permission_mask() == 1
    axis, _, command = drive(3, observed_state=state, latched=True, native_request_long=False)
    assert axis.lateralActive and command.latActive and not sd.enabled and not command.longActive
    assert state.seatbeltUnlatched
    deliver_card(card, sd, controls, state, 3)
    assert card.aol_card_intent.allowed_latch


def test_cold_unbelted_lateral_requires_belt_new_enable_and_native_ack_for_longitudinal():
  from opendbc.car.hyundai.values import Buttons
  from opendbc.safety.tests.test_hyundai_ioniq6_stock_aol import TestHyundaiIoniq6StockAol
  from openpilot.cereal import log
  with OpenpilotPrefix(), ExitStack() as cleanup:
    card, sd, _, drive, state = factory_callers(cleanup, True)
    native = TestHyundaiIoniq6StockAol(methodName='runTest')
    native.mode(int(card.CP.safetyConfigs[-1].safetyParam))
    native.safety.set_alternative_experience(int(card.CP.alternativeExperience))
    for name, values in (('ACCELERATOR', {'GEAR': 5}), ('TCS', {}), ('WHEEL_SPEEDS', {}),
                         ('MDPS', {}), ('CRUISE_BUTTONS', {})):
      native.rx(name, values)
    assert native.safety.aol_rx_healthy() and not native.safety.get_relay_malfunction()
    native.safety.set_aol_test_heartbeat(True)
    native.safety.aol_set_host_request(0)
    assert native.safety.aol_get_permission_mask() == 0
    native.rx('CRUISE_BUTTONS', {'LDA_BTN': 1})
    native.rx('CRUISE_BUTTONS', {})
    original_encode = fixture.encode_safety
    def actual_native(value):
      mask = native.safety.aol_get_permission_mask()
      request = native.safety.aol_get_request_mask()
      return original_encode(replace(value, requestedLateral=bool(request & 1), requestedLongitudinal=bool(request & 2),
        lateralAllowed=bool(mask & 1), longitudinalAllowed=bool(mask & 2), pandaInventory=tuple(
          replace(slot, controlsAllowed=native.safety.get_controls_allowed()) for slot in value.pandaInventory)))
    with mock.patch.object(fixture, 'encode_safety', side_effect=actual_native):
      pending, _, command = drive(0, observed_state=state, native_request_lat=False, native_request_long=False)
      assert pending.desiredLateral and not pending.lateralActive and not command.longActive
      native.safety.aol_set_host_request(int(pending.desiredLateral))
      assert native.safety.aol_get_permission_mask() == 1
      axis, _, command = drive(1, observed_state=state, native_request_long=False)
      assert axis.lateralActive and command.latActive and not command.longActive

      def button(tick, pressed):
        previous, current = (Buttons.NONE, Buttons.SET_DECEL) if pressed else (Buttons.SET_DECEL, Buttons.NONE)
        state.buttonEvents = card.CI.CS.create_cruise_button_events(current, previous)
        state.buttonEnable = card.CI.CS.update_button_enable(state.buttonEvents)
        native.rx('CRUISE_BUTTONS', {'CRUISE_BUTTONS': current})
        return drive(tick, observed_state=state, native_request_long=False)
      button(2, True)
      axis, _, command = button(3, False)
      assert sd.events.contains(ET.ENABLE) and sd.events.contains(ET.NO_ENTRY)
      assert not sd.enabled and not axis.desiredLongitudinal and not command.longActive
      state.buttonEvents, state.buttonEnable, state.seatbeltUnlatched = [], False, False
      axis, _, command = drive(4, observed_state=state, native_request_long=False)
      assert not sd.enabled and not axis.desiredLongitudinal and not command.longActive
      button(5, True)
      axis, _, command = button(6, False)
      assert sd.events.contains(ET.ENABLE) and not sd.events.contains(ET.NO_ENTRY)
      assert sd.enabled and axis.desiredLongitudinal and not axis.longitudinalActive and not command.longActive
      native.safety.aol_set_host_request(int(axis.desiredLateral) | (int(axis.desiredLongitudinal) << 1))
      assert native.safety.aol_get_permission_mask() == 3
      state.buttonEvents, state.buttonEnable = [], False
      axis, _, command = drive(7, observed_state=state, native_request_long=True)
      assert axis.lateralActive and axis.longitudinalActive and command.latActive and command.longActive
      state.seatbeltUnlatched = True
      axis, _, command = drive(8, observed_state=state, native_request_long=True)
      assert axis.lateralActive and command.latActive and not axis.longitudinalActive and not command.longActive
      assert sd.state_machine.state == log.SelfdriveState.OpenpilotState.softDisabling
      assert sd.state_machine.soft_disable_timer == 300
      for _ in range(300):
        sd.state_machine.update(sd.events)
      assert sd.state_machine.state == log.SelfdriveState.OpenpilotState.disabled
      native.safety.aol_set_host_request(1)
      state.seatbeltUnlatched = False
      axis, _, command = drive(9, observed_state=state, native_request_long=False)
      assert axis.lateralActive and command.latActive and not sd.enabled and not axis.desiredLongitudinal and not command.longActive
