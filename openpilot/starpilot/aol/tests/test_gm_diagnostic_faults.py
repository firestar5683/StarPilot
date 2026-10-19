"""Source-prepared exact GM admission regressions; root executes after candidate review."""
from dataclasses import replace
from types import SimpleNamespace

import pytest
from opendbc.car.gm.tests.test_volt_sdgm_control import sdgm_params
from opendbc.car.gm.tests.test_bolt_pedal import params
from opendbc.car.gm.values import CAR
from openpilot.starpilot.aol.runtime import current_native, native_inventory_matches_cp, decide_axes
from openpilot.starpilot.aol.wire import PandaSlot, SafetyState
from openpilot.starpilot.aol.tests.test_panda_inventory import sm_for
from openpilot.starpilot.aol.tests.test_runtime import car_state

NOW = 10_000_000_000


def owner(label):
  cp = sdgm_params(alpha=False, sascm=True, radar=False) if label == 'volt' else params(
    CAR.CHEVROLET_BOLT_CC_2018_2021, pedal=True, camera=True)
  cp.alternativeExperience = 32
  assert cp.safetyConfigs[0].safetyParam == (0x1005 if label == 'volt' else 0x9D)
  assert cp.openpilotLongitudinalControl == (label == 'bolt')
  assert cp.pcmCruise == (label == 'volt')
  config = cp.safetyConfigs[0]
  slot = PandaSlot(0, label, config.safetyModel.raw, config.safetyParam, 32, False)
  state = SafetyState(1, True, NOW, NOW + 200_000_000, config.safetyModel.raw, config.safetyParam,
                      False, False, False, False, label, 'session', NOW, (slot,))
  return cp, state


@pytest.mark.parametrize('label', ('volt', 'bolt'))
@pytest.mark.parametrize('mask', (0, 1 << 2, 1 << 3, 1 << 18, 12))
def test_diagnostic_receipt_does_not_invent_native_authority(label, mask):
  cp, state = owner(label)
  state = replace(state, pandaInventory=(replace(state.pandaInventory[0], faults=mask),))
  admitted = mask == 0 or (label == 'volt' and mask == 1 << 18) or (label == 'bolt' and mask in (1 << 2, 1 << 3, 12))
  assert native_inventory_matches_cp(state, cp) == admitted
  accepted = current_native(sm_for(cp, state), cp, now_ns=NOW, axis_session_id='session')
  if not admitted:
    assert accepted is None
    return
  assert accepted == state
  intent = SimpleNamespace(allowedLatch=True, pauseLateral=False, pauseLongitudinal=False)
  decision = decide_axes(standard_lateral=True, standard_longitudinal=cp.openpilotLongitudinalControl,
                         intent=intent, native=accepted, car_state=car_state(), initialized=True,
                         model_ready=True, no_entry=False, immediate_disable=False, dm_lockout=False, pause_brake_mps=0.)
  assert not decision.lateral_active and not decision.longitudinal_active


@pytest.mark.parametrize('label', ('volt', 'bolt'))
@pytest.mark.parametrize('bit', (0, 1, 4, 5, 7, 8, 15, 20, 21, 22, 23, 25, 26, 27, 31))
def test_authority_faults_and_unknown_bits_still_block(label, bit):
  cp, state = owner(label)
  baseline = replace(state, pandaInventory=(replace(state.pandaInventory[0], faults=(1 << 18 if label == 'volt' else 12)),))
  assert current_native(sm_for(cp, baseline), cp, now_ns=NOW, axis_session_id='session') == baseline
  state = replace(baseline, pandaInventory=(replace(baseline.pandaInventory[0], faults=baseline.pandaInventory[0].faults | (1 << bit)),))
  assert current_native(sm_for(cp, state), cp, now_ns=NOW, axis_session_id='session') is None


@pytest.mark.parametrize('label', ('volt', 'bolt'))
@pytest.mark.parametrize('bad', ('rx', 'heartbeat', 'word', 'ae', 'serial', 'session', 'expired'))
def test_diagnostic_bits_cannot_bypass_other_vetoes(label, bad):
  cp, state = owner(label)
  slot = replace(state.pandaInventory[0], faults=(1 << 18 if label == 'volt' else 12))
  baseline = replace(state, pandaInventory=(slot,))
  assert current_native(sm_for(cp, baseline), cp, now_ns=NOW, axis_session_id='session') == baseline
  mutations = {'rx': {'safetyRxChecksInvalid': True}, 'heartbeat': {'heartbeatLost': True},
               'word': {'safetyParam': slot.safetyParam ^ 1}, 'ae': {'alternativeExperience': 0},
               'serial': {'hardwareSerial': 'wrong'}}
  state = replace(state, pandaInventory=(replace(slot, **mutations.get(bad, {})),))
  assert current_native(sm_for(cp, state), cp, now_ns=NOW + (200_000_001 if bad == 'expired' else 0),
                        axis_session_id='wrong' if bad == 'session' else 'session') is None


def test_other_brands_keep_existing_all_fault_veto():
  from openpilot.starpilot.aol.panda_faults import blocking_fault_mask, blocking_fault_list
  from openpilot.cereal import log
  cp = SimpleNamespace(brand='hyundai')
  assert blocking_fault_mask(12, cp)
  assert blocking_fault_list([log.PandaState.FaultType.interruptRateCan1], cp)


@pytest.mark.parametrize('fault, blocks', [('interruptRateCan2', False), ('interruptRateUsb', False),
                                          ('relayMalfunction', True), ('registerDivergent', True),
                                          ('heartbeatLoopWatchdog', True)])
def test_honda_latched_interrupt_rate_faults_do_not_block(fault, blocks):
  from openpilot.starpilot.aol.panda_faults import blocking_fault_mask, blocking_fault_list
  from openpilot.cereal import log
  cp = SimpleNamespace(brand='honda')
  value = log.PandaState.FaultType.schema.enumerants[fault]
  assert blocking_fault_mask(1 << value, cp) == blocks
  assert blocking_fault_list([value], cp) == blocks
  assert blocking_fault_list([log.PandaState.FaultType.interruptRateCan2, value], cp) == blocks


@pytest.mark.parametrize('word', (0x1405, 0x5007, 0x5407, 0x5087, 0xD107, 0xE500, 0x205, 0x4007, 0x20))
def test_other_volt_configs_do_not_borrow_stock_register_policy(word):
  from openpilot.starpilot.aol.panda_faults import blocking_fault_mask
  cp, _ = owner('volt')
  cp.safetyConfigs[0].safetyParam = word
  assert blocking_fault_mask(1 << 18, cp)


@pytest.mark.parametrize('identity', (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_CC_2022_2023,
                                     CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL))
def test_other_bolt_generations_do_not_borrow_irq_policy(identity):
  from openpilot.starpilot.aol.panda_faults import blocking_fault_mask
  cp = params(identity, pedal=True, camera=True)
  cp.alternativeExperience = 32
  assert blocking_fault_mask(12, cp)


@pytest.mark.parametrize('label', ('volt', 'bolt'))
def test_latest_raw_faults_use_same_exact_policy_and_retain_native_veto(label):
  from openpilot.cereal import messaging
  from openpilot.starpilot.aol.transport_pause import healthy_transport
  cp, state = owner(label)
  allowed = 'registerDivergent' if label == 'volt' else 'interruptRateCan2'
  mask = 1 << 18 if label == 'volt' else 1 << 3
  state = replace(state, pandaInventory=(replace(state.pandaInventory[0], faults=mask),))
  sm = sm_for(cp, state)
  assert current_native(sm, cp, now_ns=NOW, axis_session_id='session') == state
  event = messaging.new_message('pandaStates', 1, valid=True, logMonoTime=NOW)
  event.pandaStates[0] = sm['pandaStates'][0]
  event.pandaStates[0].faults = [allowed]
  sm.update_msgs(NOW / 1e9, [event.as_reader()])
  assert healthy_transport(sm, cp, car_state(), 'session', NOW)
  event.pandaStates[0].faults = [allowed, 'relayMalfunction']
  sm.update_msgs(NOW / 1e9, [event.as_reader()])
  assert not healthy_transport(sm, cp, car_state(), 'session', NOW)
  event.pandaStates[0].faults = [allowed]
  event.pandaStates[0].heartbeatLost = True
  sm.update_msgs(NOW / 1e9, [event.as_reader()])
  assert not healthy_transport(sm, cp, car_state(), 'session', NOW)


@pytest.mark.parametrize('label', ('volt', 'bolt'))
def test_raw_enum_policy_does_not_borrow_other_config_diagnostics(label):
  from openpilot.cereal import log
  from openpilot.starpilot.aol.panda_faults import blocking_fault_list
  cp, _ = owner(label)
  allowed = [log.PandaState.FaultType.registerDivergent] if label == 'volt' else [
    log.PandaState.FaultType.interruptRateCan1, log.PandaState.FaultType.interruptRateCan2]
  assert not blocking_fault_list(allowed, cp)
  denied = (log.PandaState.FaultType.interruptRateCan1 if label == 'volt' else log.PandaState.FaultType.registerDivergent)
  assert blocking_fault_list([*allowed, denied], cp)
  assert blocking_fault_list([*allowed, log.PandaState.FaultType.interruptRateCan3], cp)
  assert blocking_fault_list([*allowed, log.PandaState.FaultType.relayMalfunction], cp)
  assert blocking_fault_list([*allowed, 31], cp)


@pytest.mark.parametrize('label', ('volt', 'bolt'))
def test_real_native_permission_and_brake_withdrawal_remain_authoritative(label):
  from opendbc.can import CANPacker
  from opendbc.car import Bus
  from opendbc.car.gm.interface import CarInterface
  from opendbc.car.gm.values import DBC, CruiseButtons
  from opendbc.car.gm.bolt_cc import button_bytes
  from opendbc.car.gm.gmcan import pedal_crc
  from opendbc.car.gm.tests.test_bolt_cc import feed
  from opendbc.safety.tests.libsafety import libsafety_py
  cp, state = owner(label)
  ci = CarInterface(cp)
  packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
  safety = libsafety_py.libsafety
  safety.init_tests()
  safety.set_alternative_experience(32)
  assert safety.set_safety_hooks(cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam) == 0
  for tick in range(32):
    now = NOW + tick * 10_000_000
    _, packets = feed(SimpleNamespace(update=lambda _: None), packer, now, counter=tick % 4,
                      active=label == 'volt', speed=20., camera=True, brake=tick == 31)
    packets = [packet for packet in packets if packet[0] != 0x1E1]
    button = CruiseButtons.DECEL_SET if tick == 20 else CruiseButtons.UNPRESS
    packets.append((0x1E1, button_bytes(button, tick % 4), 0))
    if label == 'volt':
      # Stock SDGM requires camera ACC status and its selected PT brake source.
      packets = [packet for packet in packets if packet[0] != 0xBE]
      packets.append(packer.make_can_msg('ECMAcceleratorPos', 0, {'BrakePedalPos': 12 if tick == 31 else 0}))
      packets.append(packer.make_can_msg('ASCMActiveCruiseControlStatus', 2,
                                        {'ACCCruiseState': 3, 'ACCSpeedSetpoint': 60}))
    if label == 'bolt':
      packets = [packet for packet in packets if packet[0] != 0x1F5]
      packets.append(packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 6}))
      sensor = bytearray(packer.make_can_msg('GAS_SENSOR', 0, {
        'INTERCEPTOR_GAS': 0., 'INTERCEPTOR_GAS2': 0., 'STATE': 0, 'COUNTER_PEDAL': tick % 16})[1])
      sensor[5] = pedal_crc(sensor)
      packets.append((0x201, bytes(sensor), 0))
    parsed = ci.update([(now, packets)])
    safety.set_timer(now // 1000)
    for address, data, bus in packets:
      assert safety.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, data))
    safety.safety_tick()
    # Transport instrumentation supplies heartbeat/request, never a permission or controlsAllowed setter.
    safety.set_aol_test_heartbeat(True)
    request = 1 if label == 'volt' else 3
    safety.aol_set_host_request(request)
    mask = safety.aol_get_permission_mask()
    if tick == 30:
      assert parsed.canValid
      assert mask == request
    if tick == 31:
      assert parsed.brakePressed
      assert not mask & 2
      slot = replace(state.pandaInventory[0], controlsAllowed=bool(safety.get_controls_allowed()),
                     faults=1 << 18 if label == 'volt' else 12)
      receipt = replace(state, observedMonoTime=now, validUntilMonoTime=now + 200_000_000,
                        lateralAllowed=bool(mask & 1), longitudinalAllowed=bool(mask & 2),
                        requestedLateral=bool(request & 1), requestedLongitudinal=bool(request & 2),
                        pandaInventory=(slot,))
      # Admission of a classified diagnostic does not overwrite native LONG withdrawal.
      assert native_inventory_matches_cp(receipt, cp)
      intent = SimpleNamespace(allowedLatch=True, pauseLateral=False, pauseLongitudinal=False)
      decision = decide_axes(standard_lateral=True, standard_longitudinal=cp.openpilotLongitudinalControl,
                             intent=intent, native=receipt, car_state=parsed, initialized=True, model_ready=True,
                             no_entry=False, immediate_disable=False, dm_lockout=False, pause_brake_mps=0.)
      assert not decision.longitudinal_active
  safety.set_alternative_experience(0)
