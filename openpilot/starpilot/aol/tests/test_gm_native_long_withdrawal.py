"""GM native driver withdrawal can precede the separately sampled host state."""
from contextlib import ExitStack

import pytest
from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm.tests.test_bolt_cc import native
from opendbc.car.gm.tests.test_bolt_pedal import params
from opendbc.car.gm.gmcan import create_pedal_command
from opendbc.car.gm.values import CAR, DBC
from opendbc.safety.tests.libsafety import libsafety_py
from openpilot.cereal import log
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_gm_held_native import NOW, parse


@pytest.mark.parametrize('candidate', [CAR.CHEVROLET_BOLT_CC_2018_2021, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL])
@pytest.mark.parametrize('gesture', ['paddle', 'cancel'])
def test_native_withdrawal_before_host_input_keeps_independent_lateral(candidate, gesture):
  from openpilot.starpilot.aol.tests.test_gm import TestGmAol
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    cp = params(candidate, pedal=True, camera=True)
    sd, _, step = case._authority_callers(True, cp=cp, genuine_events=True)
    card = TestGmAol.card(cp, Params())
    cleanup.callback(card.vehicle_startup.close)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])

    def packets_at(now, tick, gesture=None):
      packets = parse(card, now, gesture=gesture, counter=tick % 4, packets_only=True)
      packets.append(packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCruiseState': 0}))
      return packets

    safety = libsafety_py.libsafety
    safety.init_tests()
    safety.set_alternative_experience(32)
    assert safety.set_safety_hooks(4, cp.safetyConfigs[0].safetyParam) == 0
    for tick in range(10):
      now = NOW + tick * 10_000_000
      packets = packets_at(now, tick)
      if tick == 0:
        card.CI.update([(now - 1_000_000, packets)])
      cs = card.CI.update([(now, packets)])
      assert cs.canValid and not cs.canTimeout
      for packet in packets:
        assert native('rx', packet, now // 1000)
      safety.set_aol_test_heartbeat(True)
      safety.aol_set_host_request(3)
      if tick == 0:
        # The recorded starting condition is established full engagement.
        safety.set_controls_allowed(True)
      axis, state, command = step(tick)
      assert safety.aol_get_permission_mask() == 3
      assert state.enabled and axis.lateralActive and axis.longitudinalActive
      assert command.latActive and command.longActive
    health_before_input = safety.get_controls_allowed()
    # Exact recorded physical bytes: route173 segment5 paddle / segment7 Cancel.
    packet = (0xBD, bytes.fromhex('20000000000000'), 0) if gesture == 'paddle' else (
      0x1E1, bytes.fromhex('00000000016490'), 0)
    assert native('rx', packet, (NOW + 95_000_000) // 1000)
    mask = safety.aol_get_permission_mask()
    assert health_before_input and not safety.get_controls_allowed() and mask == 1
    assert not native('tx', create_pedal_command(packer, .1, 0), (NOW + 96_000_000) // 1000)
    assert native('tx', create_pedal_command(packer, 0., 1), (NOW + 96_000_000) // 1000)
    # Pandad samples health BEFORE its final native permission read. Card has
    # not published the physical edge yet, exactly as in the two route failures.
    axis, state, command = step(10, allowed=bool(mask & 1), long_allowed=bool(mask & 2),
      native_request_lat=True, native_request_long=True, panda_controls_allowed=health_before_input)
    assert state.enabled and axis.lateralActive and command.latActive
    assert not axis.longitudinalActive and not command.longActive
    assert not sd.aol_authority_lost
    assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
    # The real host parser then observes the input. LONG remains withdrawn;
    # the existing driver-disable event owns ordinary disengagement.
    observed = card.CI.update([(NOW + 110_000_000, packets_at(NOW + 110_000_000, 11, gesture))])
    assert observed.canValid and not observed.canTimeout
    assert observed.regenBraking == (gesture == 'paddle')
    axis, state, command = step(11, observed_state=observed, native_request_lat=True,
      native_request_long=True, long_allowed=False, panda_controls_allowed=False)
    assert not state.enabled and not command.longActive and not axis.longitudinalActive
    assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
    # The ordinary Cancel NO_ENTRY policy may pause LAT on its input tick.
    # Releasing the input must preserve independent LAT without resuming LONG.
    axis, state, command = step(12, native_request_lat=True, native_request_long=False,
      long_allowed=False, panda_controls_allowed=False)
    assert not state.enabled and not command.longActive
    assert axis.lateralActive and command.latActive


@pytest.mark.parametrize('candidate', [CAR.CHEVROLET_BOLT_CC_2018_2021, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL])
@pytest.mark.parametrize('fault', ['lat_denied', 'native_invalid', 'rx_fault', 'relay_fault', 'missing_prior'])
def test_gm_long_withdrawal_does_not_bypass_faults(candidate, fault):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, step = case._authority_callers(True, cp=params(candidate, pedal=True, camera=True), genuine_events=True)
    for tick in range(10):
      axis, state, command = step(tick)
      assert state.enabled and axis.lateralActive and command.longActive
    options = {'native_request_lat': True, 'native_request_long': True, 'long_allowed': False,
               'panda_controls_allowed': True}
    if fault == 'lat_denied':
      options['allowed'] = False
    elif fault == 'native_invalid':
      options['native_valid'] = False
    elif fault == 'rx_fault':
      options['panda_fault'] = True
    elif fault == 'relay_fault':
      options['relay_fault'] = True
    else:
      sd.aol_published_input_proof = None
    axis, state, command = step(10, **options)
    assert log.OnroadEvent.EventName.controlsMismatch in sd.events.names
    assert not state.enabled and not axis.lateralActive and not command.latActive and not command.longActive


@pytest.mark.parametrize('candidate', [CAR.CHEVROLET_BOLT_CC_2018_2021, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL])
def test_persistent_gm_native_denial_still_reaches_ordinary_mismatch(candidate):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, step = case._authority_callers(True, cp=params(candidate, pedal=True, camera=True), genuine_events=True)
    for tick in range(10):
      axis, state, command = step(tick)
      assert state.enabled and axis.lateralActive and command.longActive
    for tick in range(10, 230):
      axis, state, command = step(tick, native_request_lat=True, native_request_long=True,
        long_allowed=False, panda_controls_allowed=tick < 20)
      assert not axis.longitudinalActive and not command.longActive
      if log.OnroadEvent.EventName.controlsMismatch in sd.events.names:
        break
      assert state.enabled and axis.lateralActive and command.latActive
    assert sd.mismatch_counter >= 200
    assert log.OnroadEvent.EventName.controlsMismatch in sd.events.names
    assert not state.enabled and not axis.lateralActive and not command.latActive
