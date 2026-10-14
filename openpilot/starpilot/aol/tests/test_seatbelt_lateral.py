from contextlib import ExitStack
from dataclasses import replace

import pytest

from openpilot.cereal import log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.selfdrived.events import ET, EventName
from openpilot.starpilot.aol.runtime import current_intent, current_native
from openpilot.starpilot.aol.seatbelt import seatbelt_lateral_soft_event_allowed
from openpilot.starpilot.aol.tests.test_ioniq_availability import IoniqAvailabilityTests, car_state
from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import callers


@pytest.mark.parametrize('full_op', [False, True])
def test_actual_ioniq_belt_long_lock_preserves_armed_lateral(full_op):
  case = IoniqAvailabilityTests(methodName='runTest')
  with OpenpilotPrefix(), ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    sd, controls, drive, card, receive = case._ioniq_availability_callers(full_op)
    for tick, unlatched in ((2, True), (3, True), (4, False)):
      state = car_state()
      state.seatbeltUnlatched = unlatched
      axis, _, command = drive(tick, observed_state=state, native_request_long=False, long_allowed=False)
      assert axis.faultReason == 'none'
      assert axis.lateralActive and command.latActive
      assert not axis.longitudinalActive and not command.longActive
      if unlatched:
        assert sd.events.contains(ET.NO_ENTRY) and sd.events.contains(ET.SOFT_DISABLE)
        assert EventName.seatbeltNotLatched in sd.events.names
      # Deliver the exact published current command, rather than the prior SM command.
      published = controls.pm.messages['carControl']
      sd.sm.update_msgs((10_000_000_000 + tick * 10_000_000) / 1e9, [published])
      assert receive(10_000_000_000 + tick * 10_000_000, state=state,
                     axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      assert card.aol_card_intent.allowed_latch
      assert not card.sm['carControl'].longActive
    # Buckling is not an ordinary LONG enable gesture.
    assert not command.longActive


@pytest.mark.parametrize('fault', [None, 'native_denied', 'wrong_session', 'stale_source', 'unarmed',
                                   'belt_mismatch', 'mixed_user', 'no_entry_missing', 'door', 'permanent'])
def test_shared_belt_classification_keeps_actual_native_and_source_guards(fault):
  case = IoniqAvailabilityTests(methodName='runTest')
  with OpenpilotPrefix(), ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    sd, _, drive, _, _ = case._ioniq_availability_callers(False)
    state = car_state()
    state.seatbeltUnlatched = True
    state.cruiseState.available = True
    drive(2, observed_state=state, native_request_long=False)
    now = source = 10_020_000_000
    intent = current_intent(sd.sm, car_state_ns=source, now_ns=now, companion=sd.aol_intent_companion)
    native = current_native(sd.sm, now_ns=now, CP=sd.CP, axis_session_id=sd.aol_session_id)
    assert intent is not None and native is not None
    event = next(event for event in sd.events.to_msg() if event.name == EventName.seatbeltNotLatched)
    if fault == 'native_denied':
      native = replace(native, lateralAllowed=False)
    elif fault == 'wrong_session':
      native = replace(native, axisSessionId='other')
    elif fault == 'stale_source':
      now += 30_000_001
    elif fault == 'unarmed':
      intent = replace(intent, allowedLatch=False)
    elif fault == 'belt_mismatch':
      state.seatbeltUnlatched = False
    elif fault == 'mixed_user':
      event.userDisable = True
    elif fault == 'no_entry_missing':
      event.noEntry = False
    elif fault == 'door':
      state.doorOpen = True
    elif fault == 'permanent':
      state.steerFaultPermanent = True
    assert seatbelt_lateral_soft_event_allowed(sd.CP, state, intent, native, event,
      source_ns=source, now_ns=now, axis_session_id=sd.aol_session_id) == (fault is None)


@pytest.mark.parametrize('family', ['gm', 'toyota'])
@pytest.mark.parametrize('full_op', [False, True])
def test_actual_family_belt_removal_preserves_lateral_and_ordinary_long_timer(family, full_op):
  with ExitStack() as cleanup:
    sd, controls, drive, card, receive = callers(cleanup, family, not full_op)
    baseline = controls.pm.messages['carControl'].carControl
    assert baseline.latActive and baseline.longActive == full_op
    state = car_state()
    state.seatbeltUnlatched = True
    # Preserve the prior native combined grant for the first withdrawal decision.
    axis, _, command = drive(2, observed_state=state, native_request_long=full_op)
    assert axis.lateralActive and command.latActive
    assert not axis.desiredLongitudinal and not axis.longitudinalActive and not command.longActive
    assert axis.faultReason == 'none'
    assert receive(10_020_000_000, state)
    assert card.aol_card_intent.allowed_latch
    assert EventName.seatbeltNotLatched in sd.events.names
    assert sd.events.contains(ET.NO_ENTRY) and sd.events.contains(ET.SOFT_DISABLE)
    if full_op:
      assert sd.enabled and sd.state_machine.state == log.SelfdriveState.OpenpilotState.softDisabling
      assert sd.state_machine.soft_disable_timer == 300
      # Exercise the unchanged ordinary owner with its actual current event set.
      for _ in range(300):
        sd.state_machine.update(sd.events)
      assert sd.state_machine.state == log.SelfdriveState.OpenpilotState.disabled
    state.seatbeltUnlatched = False
    axis, _, command = drive(3, observed_state=state, native_request_long=False, long_allowed=False)
    assert axis.lateralActive and command.latActive
    assert not command.longActive
    assert not sd.enabled and not axis.desiredLongitudinal
    assert EventName.seatbeltNotLatched not in sd.events.names


def test_actual_ioniq_first_unbuckled_admission_needs_no_buckled_baseline():
  from opendbc.car.hyundai.interface import CarInterface
  from opendbc.car.hyundai.radar_interface import RadarInterface
  from openpilot.selfdrive.car.card import Car
  from openpilot.selfdrive.car.tests.test_hyundai_aol import candidate
  from opendbc.car.structs import car

  case = IoniqAvailabilityTests(methodName='runTest')
  with OpenpilotPrefix(), ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    _, cp = candidate(True)
    # Match Card pre_create_hook finalization before the supplied CI constructor.
    cp.safetyConfigs[-1].safetyParam |= 0x0800
    sd, _, drive = case._authority_callers(False, cp=cp, genuine_events=True)
    card_cp = cp.as_reader().as_builder()
    card = Car(CI=CarInterface(card_cp), RI=RadarInterface(card_cp))
    state = car_state()
    state.cruiseState.available = True
    state.seatbeltUnlatched = True
    assert not card.aol_card_intent.allowed_latch
    card.aol_card_intent.update(state, now_ns=9_990_000_000)
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
    card.aol_card_intent.update(state, now_ns=10_000_000_000)
    assert card.aol_card_intent.allowed_latch
    state.buttonEvents = []
    axis, _, command = drive(0, observed_state=state, latched=card.aol_card_intent.allowed_latch,
                             native_request_long=False)
    assert axis.faultReason == 'none' and axis.lateralActive and command.latActive
    assert not sd.enabled and not axis.desiredLongitudinal and not command.longActive
    assert EventName.seatbeltNotLatched in sd.events.names


@pytest.mark.parametrize('fault', ['wrong_inventory', 'unsupported', 'mixed_hard'])
def test_actual_family_belt_does_not_mask_foreign_or_hard_authority(fault):
  with ExitStack() as cleanup:
    sd, _, drive, _, _ = callers(cleanup, 'toyota', True)
    state = car_state()
    state.cruiseState.available = True
    state.seatbeltUnlatched = True
    if fault == 'mixed_hard':
      state.steerFaultPermanent = True
    axis, _, command = drive(2, observed_state=state, native_request_long=False)
    if fault == 'mixed_hard':
      assert not axis.lateralActive and not command.latActive and not command.longActive
      assert axis.faultReason == 'critical'
      return
    now = 10_020_000_000
    intent = current_intent(sd.sm, car_state_ns=now, now_ns=now, companion=sd.aol_intent_companion)
    native = current_native(sd.sm, sd.CP, now_ns=now, axis_session_id=sd.aol_session_id)
    assert intent is not None and native is not None and native.pandaInventory
    event = next(e for e in sd.events.to_msg() if e.name == EventName.seatbeltNotLatched)
    cp = sd.CP
    if fault == 'wrong_inventory':
      native = replace(native, pandaInventory=(replace(native.pandaInventory[0], safetyParam=0),))
    else:
      cp = cp.as_builder()
      cp.brand = 'unsupported'
    assert not seatbelt_lateral_soft_event_allowed(cp, state, intent, native, event,
      source_ns=now, now_ns=now, axis_session_id=sd.aol_session_id)
