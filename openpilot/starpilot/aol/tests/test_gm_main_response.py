"""MAIN rearm with an idle response still in Card's receive snapshot."""
import os
from dataclasses import replace
from unittest.mock import patch

import pytest
from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm.tests.test_ascm_intercept import params as ascm_params
from opendbc.car.gm.values import CAR, DBC, CruiseButtons
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car import card as module
from openpilot.starpilot.aol.runtime import decide_axes
from openpilot.starpilot.aol.tests import test_gm as gm_fixtures
from openpilot.starpilot.aol.tests.test_gm_held_native import peers
from openpilot.starpilot.aol.tests.test_gm_startup_main import parsed_packets
from openpilot.starpilot.aol.wire import PandaSlot, SafetyState, IntentState

NOW = 10_000_000_000


@pytest.mark.parametrize('variation', [
  'delayed_idle', 'new_source', 'future_source', 'expired', 'producer', 'epoch', 'session',
  'invalid', 'native_denied', 'native_config', 'critical', 'cancel', 'settings_off',
])
def test_actual_card_main_rearm_waits_only_for_older_idle_response(variation):
  with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1', 'AOL_REPLAY_RUNTIME': '0'}):
    saved = Params()
    saved.put_bool('AlwaysOnLateral', True, block=True)
    cp = ascm_params(CAR.CHEVROLET_VOLT_ASCM, accelerator=False, radar=False, alpha=False)
    card = gm_fixtures.TestGmAol.card(cp, saved)
    assert card.CP.safetyConfigs[0].safetyParam == 0x605
    assert card.CP.alternativeExperience == 32
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    card.ci_initialized = True
    card.publish_sendcan = lambda *args, **kwargs: None  # No vehicle I/O.
    for tick in range(20):
      stamp = NOW - (20 - tick) * 10_000_000
      card.CI.update([(stamp, parsed_packets(cp, packer, stamp, tick, 8., True))])

    def cycle(tick, main=True, ack=True, source=None, fault=False, mutate=False):
      now = NOW + tick * 10_000_000
      if mutate and variation == 'expired':
        now += 31_000_000
      config = card.CP.safetyConfigs[0]
      slot = PandaSlot(0, 'gm-unit', config.safetyModel.raw, config.safetyParam, 32, False)
      native = SafetyState(1, True, now, now + 200_000_000, config.safetyModel.raw, config.safetyParam,
                           False, False, False, False, 'gm-unit', 'gm-session',
                           sourcePandaStatesMonoTime=now, pandaInventory=(slot,))
      if mutate and variation == 'native_denied':
        native = replace(native, requestedLateral=True)
      if mutate and variation == 'native_config':
        native = replace(native, safetyParam=0)
      incoming, _ = peers(card.CP, card.slc_producer_session, now, controls=False,
                           native=native, sequence=tick + 1, long_active=False)
      axis = incoming.messages['aolAxisState'].as_builder()
      a = axis.aolAxisState
      a.sourceCarStateMonoTime = now - 1 if source is None else source
      a.nativeAcknowledged = ack
      a.desiredLateral = a.lateralActive = a.desiredLongitudinal = a.longitudinalActive = False
      if fault:
        a.faultReason = 'critical'
      if mutate:
        if variation == 'new_source':
          a.sourceCarStateMonoTime = now - 1
        elif variation == 'future_source':
          axis.logMonoTime = a.observedMonoTime = a.faultEventMonoTime = now - 15_000_000
          a.validUntilMonoTime = a.observedMonoTime + 30_000_000
          a.sourceCarStateMonoTime = now - 12_000_000
        elif variation == 'producer':
          a.intentProducerSessionId = 'foreign'
        elif variation == 'epoch':
          a.intentIntegrityEpoch += 1
        elif variation == 'session':
          a.sessionId = a.faultSessionId = 'foreign'
        elif variation == 'invalid':
          axis.valid = False
        elif variation == 'settings_off':
          saved.put_bool('AlwaysOnLateral', False, block=True)
          card.aol_card_intent.settings = module.read_settings(saved)
      events = messaging.new_message('onroadEvents', int(fault or mutate and variation == 'critical'),
                                     valid=True, logMonoTime=now)
      if events.onroadEvents:
        events.onroadEvents[0].name = 'controlsMismatch'
        events.onroadEvents[0].immediateDisable = True
      control = messaging.new_message('carControl', valid=True, logMonoTime=now)
      card.sm.update_msgs(now / 1e9, [incoming.messages[k] for k in ('aolSafetyWire', 'pandaStates')] +
                          [axis.as_reader(), events.as_reader(), control.as_reader()])
      packets = parsed_packets(cp, packer, now, tick, 8., main)
      if mutate and variation == 'cancel':
        packets = [p for p in packets if p[0] != 0x1E1]
        packets.append(packer.make_can_msg('ASCMSteeringButton', 0, {'ACCButtons': CruiseButtons.CANCEL}))
      batch = messaging.log_from_bytes(module.can_list_to_can_capnp(packets)).as_builder()
      batch.logMonoTime = now
      with patch.object(module, 'REPLAY', False), \
           patch.object(module.messaging, 'drain_sock_raw', return_value=[batch.to_bytes()]), \
           patch.object(module.time, 'monotonic_ns', return_value=now), \
           patch.object(module.time, 'monotonic', return_value=now / 1e9), \
           patch.object(card.sm, 'update'):
        card.step()
      assert card.CS_prev.canValid and not card.CS_prev.canTimeout
      assert card.CS_prev.cruiseState.available == main
      assert not card.last_actuators_output.torqueOutputCan
      return now

    try:
      cycle(0)
      cycle(1, fault=True)
      assert card.aol_card_intent._main_cycle_required and not card.aol_card_intent.allowed_latch
      cycle(2)  # A healthy idle baseline clears transport failure, not the MAIN requirement.
      assert not card.aol_transport_feedback.failed and card.aol_card_intent._main_cycle_required
      off_source = cycle(3, main=False, ack=False)
      cycle(4, ack=False, source=off_source)
      assert card.aol_card_intent.allowed_latch
      edge = card.aol_card_intent.main_arm_ns
      healthy = card.aol_transport_feedback.healthy_feedback_ns
      cycle(5, ack=False, source=off_source, mutate=True)
      if variation != 'delayed_idle':
        assert not card.aol_card_intent.allowed_latch
        return
      assert card.aol_card_intent.allowed_latch
      assert card.aol_card_intent.main_arm_ns == edge
      assert card.aol_transport_feedback.healthy_feedback_ns == healthy
      # Intent retention cannot grant either axis against the unchanged idle native status.
      cs = card.CS_prev
      intent = IntentState(card.slc_producer_session, 1, NOW, NOW, NOW + 30_000_000,
                           True, False, False, True, True)
      decision = decide_axes(standard_lateral=False, standard_longitudinal=False, intent=intent,
                            native=None, car_state=cs, initialized=True, model_ready=True,
                            no_entry=False, immediate_disable=False, dm_lockout=False, pause_brake_mps=0.)
      assert not decision.lateral_active and not decision.longitudinal_active
      cycle(6)  # A subsequent matching response ends the join normally.
      assert card.aol_card_intent.allowed_latch and not card.aol_transport_feedback.failed
    finally:
      card.vehicle_startup.close()
