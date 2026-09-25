"""GM cold MAIN replay through actual factory/parser/Card/Controls/native code.

No vehicle I/O. Native masks are calculated by libsafety; CAN validity is
calculated by real parsers. Clock patching supplies a recorded test timeline.
"""
import os
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.gm.aol import qualified_gm
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.tests.test_bolt_cc import feed as packets_for_bolt, native, params as bolt_params
from opendbc.car.gm.tests.test_bolt_factory_acc import factory_params
from opendbc.car.gm.tests.test_volt_camera_control import camera_params, feed_camera
from opendbc.car.gm.tests.test_volt_sdgm_control import sdgm_params
from opendbc.car.gm.tests.test_cc_gateway_stock import silverado_stock_params, pt_frames
from opendbc.car.gm.values import CAR, DBC
from opendbc.safety.tests.libsafety import libsafety_py
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.selfdrive.selfdrived.events import Events, EventName, ET
from openpilot.starpilot.aol.intent import AolProcessFaultContext, read_settings
from openpilot.starpilot.aol.runtime import decide_axes, ordinary_lateral_requested
from openpilot.starpilot.aol.tests import test_gm as gm_fixtures
from openpilot.starpilot.aol.tests.test_gm import configurations
from openpilot.starpilot.aol.vehicle import create_intent, policy_for
from openpilot.starpilot.aol.wire import IntentState, SafetyState, encode_safety
from openpilot.starpilot.lateral.tests.test_lane_runtime import feed as feed_controls


def event_message(events, now):
  value = messaging.new_message('onroadEvents', 0, valid=True, logMonoTime=now)
  value.onroadEvents = events.to_msg()
  return value


def parsed_packets(cp, packer, now, tick, speed, main):
  # Packet-only fixture, followed by ONE actual parser update. Every engine
  # MAIN value in the resulting batch belongs to the declared physical level.
  empty = SimpleNamespace(update=lambda _: None)
  if cp.carFingerprint == CAR.CHEVROLET_SILVERADO_CC:
    packets = pt_frames(packer, cruise=False, main=main, counter=tick % 4)
  elif cp.carFingerprint in (CAR.CHEVROLET_VOLT_CAMERA, CAR.CHEVROLET_VOLT_2019):
    _, packets = feed_camera(empty, packer, now, counter=tick % 4, speed=speed, active=False)
  else:
    _, packets = packets_for_bolt(empty, packer, now, counter=tick % 4, speed=speed, active=False)
    packets += [packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCruiseState': 0})]
  if cp.carFingerprint != CAR.CHEVROLET_SILVERADO_CC:
    address = packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {})[0]
    packets = [row for row in packets if not (row[0] == address and row[2] == 2)]
    packets.append(packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCruiseState': 0}))
  replaced = ('ECMEngineStatus', 'EBCMWheelSpdFront', 'EBCMWheelSpdRear')
  addresses = {packer.make_can_msg(name, 0, {})[0] for name in replaced}
  packets = [row for row in packets if not (row[2] == 0 and row[0] in addresses)]
  packets += [packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': int(main)}),
    packer.make_can_msg('EBCMWheelSpdFront', 0, {'FLWheelSpd': speed * 3.6, 'FRWheelSpd': speed * 3.6}),
    packer.make_can_msg('EBCMWheelSpdRear', 0, {'RLWheelSpd': speed * 3.6, 'RRWheelSpd': speed * 3.6,
                                           'RLWheelDir': 1, 'RRWheelDir': 1})]
  return packets


def cases():
  yield factory_params(alpha=False)
  yield factory_params(alpha=True)
  yield bolt_params(CAR.CHEVROLET_BOLT_CC_2018_2021)
  yield silverado_stock_params()
  yield camera_params(alpha=False)
  yield camera_params(alpha=True)
  yield sdgm_params(alpha=False)
  yield sdgm_params(alpha=True)


@pytest.mark.parametrize('index', range(8))
@pytest.mark.parametrize('availability', [None, 'commIssue', 'commIssueAvgFreq'])
def test_cold_parser_main_readiness_then_actual_commands_without_main_edge(index, availability):
  cp = list(cases())[index]
  with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1', 'REPLAY': '1', 'AOL_REPLAY_RUNTIME': '0'}):
    params = Params()
    params.put_bool('AlwaysOnLateral', True, block=True)
    selected = gm_fixtures.TestGmAol.card(cp, params)
    selected.aol_process_fault_context = AolProcessFaultContext()
    selected.ci_initialized = True  # Skip ECU I/O; no native permission is fabricated.
    sent = []
    selected.publish_sendcan = lambda rows, **kwargs: sent.append(list(rows))
    controls = Controls()
    ci = selected.CI
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    safety = libsafety_py.libsafety
    safety.init_tests()
    safety.set_alternative_experience(32)
    assert safety.set_safety_hooks(int(structs.CarParams.SafetyModel.gm), selected.CP.safetyConfigs[0].safetyParam) == 0
    minimum = max(selected.CP.minSteerSpeed, .3)
    above = max(4., minimum + 2.)
    emitted_active = False
    try:
      for tick in range(48):
        now = 10_000_000_000 + tick * 10_000_000
        initializing = tick < 3
        incomplete = 3 <= tick < 8
        main = tick != 47
        speed = 0. if tick < 10 else minimum / 2. if tick < 20 else above
        packets = parsed_packets(cp, packer, now, tick, speed, main)
        # Actual parser lazy subscriptions may need a preceding genuine frame.
        if tick == 0:
          ci.update([(now - 1_000_000, packets)])
        cs = ci.update([(now, packets)])
        assert cs.canValid and not cs.canTimeout
        assert cs.cruiseState.available == main
        assert not cs.cruiseState.enabled  # MAIN is not engaged stock ACC.
        for packet in packets:
          assert native('rx', packet, now // 1000)
        safety.safety_tick()
        safety.set_aol_test_heartbeat(True)
        events = Events()
        if initializing:
          events.add(EventName.selfdriveInitializing)
        if incomplete:
          events.add(EventName.calibrationIncomplete)
          if availability:
            events.add(getattr(EventName, availability))
        event = event_message(events, now)
        selected.sm.update_msgs(now / 1e9, [event.as_reader()])
        disarm = selected.aol_disarming_fault(cs, now, now)
        assert not disarm
        selected.aol_card_intent.update(cs, fault_active=disarm, now_ns=now)
        selected.observe_aol_calibration(cs, now, False)
        allowed, pause_lat, pause_long = selected.aol_card_intent.output(cs)
        assert allowed == (main and not incomplete)
        assert not selected.aol_card_intent._main_cycle_required
        intent = IntentState(selected.slc_producer_session, tick + 1, now, now, now + 30_000_000,
                             allowed, pause_lat, pause_long, True, allowed)
        desired = decide_axes(standard_lateral=False, standard_longitudinal=False, intent=intent,
          native=None, car_state=cs, initialized=not initializing, model_ready=not incomplete,
          no_entry=events.contains(ET.NO_ENTRY), immediate_disable=events.contains(ET.IMMEDIATE_DISABLE),
          dm_lockout=False, pause_brake_mps=0.)
        safety.aol_set_host_request(int(desired.desired_lateral))
        mask = safety.aol_get_permission_mask()
        receipt_state = SafetyState(1, True, now, now + 200_000_000,
          int(structs.CarParams.SafetyModel.gm), selected.CP.safetyConfigs[0].safetyParam,
          bool(mask & 1), bool(mask & 2), desired.desired_lateral, False, 'panda', 'gm-startup')
        decision = decide_axes(standard_lateral=False, standard_longitudinal=False, intent=intent,
          native=receipt_state, car_state=cs, initialized=not initializing, model_ready=not incomplete,
          no_entry=events.contains(ET.NO_ENTRY), immediate_disable=events.contains(ET.IMMEDIATE_DISABLE),
          dm_lockout=False, pause_brake_mps=0.)
        if tick == 43:
          receipt_state = replace(receipt_state, observedMonoTime=now - 200_000_001, validUntilMonoTime=now - 1)
        elif tick == 44:
          receipt_state = replace(receipt_state, axisSessionId='replaced-session')
        elif tick == 46:
          receipt_state = replace(receipt_state, lateralAllowed=False)
        receipt = messaging.new_message('aolSafetyWire', 0, valid=tick != 45, logMonoTime=receipt_state.observedMonoTime)
        receipt.aolSafetyWire = encode_safety(receipt_state)
        axis = messaging.new_message('aolAxisState', valid=True, logMonoTime=now)
        axis.aolAxisState.qualified = True
        axis.aolAxisState.nativeAcknowledged = decision.native_acknowledged
        axis.aolAxisState.desiredLateral = decision.desired_lateral
        axis.aolAxisState.lateralActive = decision.lateral_active
        axis.aolAxisState.sessionId = 'gm-startup'
        axis.aolAxisState.observedMonoTime, axis.aolAxisState.validUntilMonoTime = now, now + 30_000_000
        state = messaging.new_message('carState', valid=True, logMonoTime=now)
        state.carState = cs
        # Build the existing full input fixture, then substitute the actual
        # physical/state/axis events BEFORE one genuine SubMaster receive.
        # Two receives of carState/onroadEvents at the same clock tick would
        # give the real frequency tracker a zero inter-arrival duration.
        batches = []
        with patch.object(controls.sm, 'update_msgs', side_effect=lambda stamp, rows, batches=batches: batches.append((stamp, rows))):
          feed_controls(controls, now, tick, active=False, enabled=False)
        assert len(batches) == 1 and batches[0][0] == now / 1e9
        samples = [sample for sample in batches[0][1] if sample.which() not in
                   ('carState', 'onroadEvents', 'aolAxisState', 'aolSafetyWire')]
        samples += [axis.as_reader(), receipt.as_reader(), state.as_reader(), event.as_reader()]
        assert len({sample.which() for sample in samples}) == len(samples)
        controls.sm.update_msgs(now / 1e9, samples)
        command, _ = controls.state_control()
        expected = bool(main and not incomplete and cs.vEgo > minimum and tick < 43)
        assert command.latActive == expected
        assert not command.longActive
        assert ordinary_lateral_requested(command.latActive, cs, selected.CP) == expected
        emitted_active |= expected
        command.actuators.torque = .02 if command.latActive else 0.
        current = messaging.new_message('carControl', valid=True, logMonoTime=now)
        current.carControl = command
        selected.sm.update_msgs(now / 1e9, [current.as_reader()])
        selected.can_log_mono_time = now + 2
        with patch('openpilot.selfdrive.car.card.time.monotonic_ns', return_value=now + 2), \
             patch('openpilot.selfdrive.car.card.time.monotonic', return_value=(now + 2) / 1e9):
          selected.controls_update(cs, current.carControl.as_reader())
        for message in sent.pop():
          assert native('tx', message, (now + 2) // 1000), (tick, message)
      assert emitted_active
      assert params.get_bool('AlwaysOnLateral')
    finally:
      safety.aol_set_host_request(0)
      selected.vehicle_startup.close()


def test_all_actual_gm_configuration_policies_cold_main_then_critical_recovery():
  with OpenpilotPrefix():
    params = Params()
    params.put_bool('AlwaysOnLateral', True, block=True)
    settings = read_settings(params)
    for cp in configurations():
      assert qualified_gm(cp)
      policy = policy_for(cp)
      assert policy.intent_supported
      owner = create_intent(cp, settings, policy)
      cs = structs.CarState(canValid=True, gearShifter='drive', vEgo=20.)
      cs.cruiseState.available = True
      initial = Events()
      initial.add(EventName.selfdriveInitializing)
      owner.update(cs, fault_active=False)
      owner.observe_calibration(cs, events=initial.to_msg())
      assert owner.startup_calibration_pending
      events = Events()
      events.add(EventName.calibrationIncomplete)
      owner.update(cs, fault_active=False)
      owner.observe_calibration(cs, events=events.to_msg())
      assert not owner.output(cs)[0] and not owner._calibration_rearm_required
      for _ in range(10):
        owner.update(cs, fault_active=None)
        owner.observe_calibration(cs, events=None)  # onroadEvents publishes sparsely.
        assert not owner.output(cs)[0] and not owner._calibration_rearm_required
      owner.update(cs, fault_active=False)
      owner.observe_calibration(cs, events=[])
      assert owner.output(cs)[0] and not owner.startup_calibration_pending
      # Same event after actual ready observation retains existing rearm law.
      owner.update(cs, fault_active=True)
      owner.observe_calibration(cs, events=events.to_msg())
      owner.update(cs, fault_active=False)
      owner.observe_calibration(cs, events=[])
      assert not owner.output(cs)[0] and owner._main_cycle_required
      cs.cruiseState.available = False
      owner.update(cs, fault_active=False)
      owner.observe_calibration(cs, events=[])
      cs.cruiseState.available = True
      owner.update(cs, fault_active=False)
      owner.observe_calibration(cs, events=[])
      assert owner.output(cs)[0]
      before = cp.to_dict()
      denied = cp.as_reader().as_builder()
      denied.passive = True
      assert create_intent(denied, settings, policy_for(denied)) is None
      assert cp.to_dict() == before


@pytest.mark.parametrize('fault', ['calibrationInvalid', 'calibrationRecalibrating', 'controlsMismatch', 'processNotRunning'])
def test_cold_mixed_or_critical_fault_never_uses_readiness_exception(fault):
  from openpilot.starpilot.car.gm.aol import intent_disarming_fault
  cp = factory_params(alpha=False)
  cs = structs.CarState(canValid=True, gearShifter='drive')
  cs.cruiseState.available = True
  events = Events()
  events.add(EventName.calibrationIncomplete)
  events.add(getattr(EventName, fault))
  assert intent_disarming_fault(cp, events.to_msg(), cs, startup_calibration_pending=True)


def test_explicit_off_and_managed_toggle_do_not_gain_startup_authority():
  with OpenpilotPrefix():
    params = Params()
    params.put_bool('AlwaysOnLateral', False, block=True)
    cp = factory_params(alpha=False)
    policy = policy_for(cp)
    owner = create_intent(cp, read_settings(params), policy)
    cs = structs.CarState(canValid=True, gearShifter='drive')
    cs.cruiseState.available = True
    owner.update(cs, fault_active=False)
    owner.observe_calibration(cs, events=[])
    assert not owner.output(cs)[0] and not params.get_bool('AlwaysOnLateral')
    params.put_bool('AlwaysOnLateral', True, block=True)
    params.put('MainCruiseButtonControl', 9, block=True)
    owner = create_intent(cp, read_settings(params), policy)
    owner.update(cs, fault_active=False)
    owner.observe_calibration(cs, events=[])
    assert not owner.output(cs)[0]
    cs.cruiseState.available = False
    cs.buttonEvents = [structs.CarState.ButtonEvent(type='mainCruise', pressed=True)]
    owner.update(cs, fault_active=False)
    assert not owner.output(cs)[0]  # Even a configured toggle cannot bypass MAIN OFF.


@pytest.mark.parametrize('index', range(8))
def test_cached_main_without_current_required_can_cannot_arm(index):
  cp = list(cases())[index]
  with OpenpilotPrefix():
    params = Params()
    params.put_bool('AlwaysOnLateral', True, block=True)
    owner = create_intent(cp, read_settings(params), policy_for(cp))
    ci = CarInterface(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    original_main_stamp = 0
    # A lazy source keeps its canonical initial timeout until rate is learned.
    # Derive actual held ticks from that real parser policy, never shorten it.
    stop_tick = 5
    tick = 0
    while tick < stop_tick:
      now = 10_000_000_000 + tick * 10_000_000
      packets = parsed_packets(cp, packer, now, tick, 20., True)
      if tick == 0:
        ci.update([(now - 1_000_000, packets)])
      if tick >= 5:
        main_address = packer.make_can_msg('ECMEngineStatus', 0, {})[0]
        packets = [packet for packet in packets if not (packet[0] == main_address and packet[2] == 0)]
      cs = ci.update([(now, packets)])
      main_stamp = ci.can_parsers[Bus.pt].ts_nanos['ECMEngineStatus']['CruiseMainOn']
      if tick == 4:
        original_main_stamp = main_stamp
        engine_address = packer.make_can_msg('ECMEngineStatus', 0, {})[0]
        timeout = ci.can_parsers[Bus.pt].message_states[engine_address].timeout_threshold
        from opendbc.can.parser import CAN_INVALID_CNT
        stop_tick = 5 + int(timeout // 10_000_000) + CAN_INVALID_CNT + 2
      elif tick >= 5:
        assert main_stamp == original_main_stamp
      owner.update(cs, fault_active=False, now_ns=now)
      if tick < 5:
        assert owner.output(cs)[0]
      tick += 1
    assert now - original_main_stamp > timeout
    assert cs.cruiseState.available  # Cached physical bit alone is insufficient.
    assert not cs.canValid and not owner.output(cs)[0]


def test_cold_native_transport_reset_is_not_a_readiness_recovery():
  with OpenpilotPrefix():
    params = Params()
    params.put_bool('AlwaysOnLateral', True, block=True)
    cp = factory_params(alpha=False)
    owner = create_intent(cp, read_settings(params), policy_for(cp))
    cs = structs.CarState(canValid=True, gearShifter='drive')
    cs.cruiseState.available = True
    events = Events()
    events.add(EventName.calibrationIncomplete)
    owner.update(cs, fault_active=False)
    owner.observe_calibration(cs, events=events.to_msg())
    assert not owner.output(cs)[0]
    owner.update(cs, fault_active=True)  # Existing Card transport-reset result.
    owner.observe_calibration(cs, events=events.to_msg())
    owner.update(cs, fault_active=False)
    owner.observe_calibration(cs, events=[])
    assert not owner.output(cs)[0] and owner._main_cycle_required
    assert not owner.startup_calibration_pending
