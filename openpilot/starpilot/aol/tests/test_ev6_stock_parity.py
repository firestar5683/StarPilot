"""EV6 stock cruise retains separate steering intent and truthful dash status."""
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from opendbc.car import Bus, structs
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, DBC
from opendbc.can import CANPacker, CANParser
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car import card as card_module
from openpilot.starpilot.aol.intent import AOL_TOGGLE
from openpilot.starpilot.aol.tests import test_canfd_stock_profiles as stock
from openpilot.starpilot.tests import test_ev6_startup as startup


def packets(ci, tick, *, main=0, lkas=0):
  result = []
  for parser in ci.can_parsers.values():
    packer = CANPacker(parser.dbc.name)
    for address in sorted(parser.addresses):
      name = parser.dbc.addr_to_msg[address].name
      values = {} if name in ('FR_CMR_02_100ms', 'DOORS_SEATBELTS', 'BLINKERS') else {'COUNTER': tick % 16}
      if name == ci.CS.cruise_btns_msg_canfd:
        values.update(ADAPTIVE_CRUISE_MAIN_BTN=main, LDA_BTN=lkas)
      elif name == 'SCC_CONTROL':
        values.update(MainMode_ACC=1, ACCMode=0)
      elif name == ci.CS.gear_msg_canfd:
        values['GEAR'] = 5
      elif name == 'DOORS_SEATBELTS':
        values['DRIVER_SEATBELT'] = 1
      result.append(packer.make_can_msg(name, parser.bus, values))
  return result


@pytest.mark.parametrize('main_action', [0, AOL_TOGGLE])
def test_actual_card_stock_lkas_then_main_respects_saved_binding(main_action):
  with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1', 'AOL_REPLAY_RUNTIME': '0'}):
    saved = Params()
    for key in ('AlwaysOnLateral', 'OpenpilotEnabledToggle'):
      saved.put_bool(key, True, block=True)
    saved.put('MainCruiseButtonControl', main_action, block=True)
    saved.put('LKASButtonControl', AOL_TOGGLE, block=True)
    cp = stock.params(CAR.KIA_EV6)

    def factory(*args, pre_create_hook, **kwargs):
      selected = pre_create_hook(cp.as_reader().as_builder(), cp.carFingerprint, {}, [])
      return CarInterface(selected)

    with patch.object(card_module.messaging, 'recv_one_retry', return_value=SimpleNamespace(can=[1])), \
         patch.object(card_module, 'get_car', side_effect=factory):
      card = card_module.Car()
    card.ci_initialized = True
    card.publish_sendcan = lambda *args, **kwargs: None
    card.CI.update([])  # Register lazy subscriptions before supplying the warmup batch.
    try:
      for tick, (main, lkas) in enumerate([(0, 0)] * 20 + [(0, 1), (0, 0), (1, 0), (0, 0)]):
        now = 10_000_000_000 + tick * 10_000_000
        batch = messaging.log_from_bytes(card_module.can_list_to_can_capnp(packets(card.CI, tick, main=main, lkas=lkas))).as_builder()
        batch.logMonoTime = now
        with patch.object(card_module, 'REPLAY', False), \
             patch.object(card_module.messaging, 'drain_sock_raw', return_value=[batch.to_bytes()]), \
             patch.object(card_module.time, 'monotonic_ns', return_value=now), \
             patch.object(card_module.time, 'monotonic', return_value=now / 1e9), patch.object(card.sm, 'update'):
          card.step()
        assert card.CS_prev.canValid and not card.CS_prev.canTimeout
        assert card.CS_prev.cruiseState.available
        if tick == 21:
          assert card.aol_card_intent.allowed_latch
      assert card.aol_card_intent.allowed_latch == (main_action == 0)
      assert not card.last_actuators_output.torqueOutputCan  # No native permission was provided.
    finally:
      card.vehicle_startup.close()


@pytest.mark.parametrize('alpha', [False, True])
def test_actual_controller_dash_follows_aol_without_changing_actuation(alpha):
  if alpha:
    ci, _, _ = startup.TestEV6Startup().exercise(mode='sent_restore')
    ci.CP.alternativeExperience = 32
  else:
    ci = CarInterface(stock.params(CAR.KIA_EV6))
  ci.CP.safetyConfigs[-1].safetyParam |= 0x800
  parser = CANParser(DBC[CAR.KIA_EV6][Bus.pt], [('LKAS', 0)], ci.CC.CAN.ACAN)
  for tick in range(120):
    now = 10_000_000_000 + tick * 10_000_000
    ci.update([(now, packets(ci, tick))])
    command = structs.CarControl(enabled=40 <= tick < 80, latActive=20 <= tick < 60)
    _, frames = ci.apply(command.as_reader(), now)
    steering = [frame for frame in frames if frame[0] == 0x50 and frame[2] == ci.CC.CAN.ACAN]
    assert len(steering) == 1
    parser.update([(now, steering)])
    values = parser.vl['LKAS']
    assert values['LKA_SysIndReq'] == (2 if command.enabled or command.latActive else 1)
    assert values['ActToiSta'] == command.latActive
    assert values['StrTqReqVal'] == 0
    cluster = [frame for frame in frames if frame[0] == 0x1E0]
    assert len(cluster) == int(alpha and tick % 5 == 0)


@pytest.mark.parametrize('variation', ['normal', 'aol_off', 'active', 'stale', 'native_mismatch', 'native_fault', 'invalid_can', 'changed_cp'])
def test_actual_card_replaces_disabled_adrv_during_selfdrive_initialization(variation):
  from opendbc.car.hyundai.radar_interface import RadarInterface
  from openpilot.starpilot.vehicle_startup import VehicleStartupOwner

  with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1', 'AOL_REPLAY_RUNTIME': '0'}):
    saved = Params()
    saved.put_bool('OpenpilotEnabledToggle', True, block=True)
    saved.put_bool('AlwaysOnLateral', variation != 'aol_off', block=True)
    # The fixture normally seals for its own assertions; Card owns the real seal here.
    with patch.object(VehicleStartupOwner, 'seal_publication'):
      ci, holder, _ = startup.TestEV6Startup().exercise(mode='sent_restore')
    card = card_module.Car(CI=ci, RI=RadarInterface(ci.CP), startup_owner=holder.owner)
    assert card.ev6_startup_keepalive()
    holder.owner.published = False
    assert not card.ev6_startup_keepalive()
    holder.owner.published = True
    holder.owner.ci = None
    assert not card.ev6_startup_keepalive()
    holder.owner.ci = ci
    card.CI.update([])
    emitted = []
    card.publish_sendcan = lambda frames, valid=True: emitted.extend((card.sm.frame, frame, valid) for frame in frames)
    try:
      for tick in range(620):
        now = 10_000_000_000 + tick * 10_000_000
        batch = messaging.log_from_bytes(card_module.can_list_to_can_capnp(packets(card.CI, tick))).as_builder()
        batch.logMonoTime = now
        control = messaging.new_message('carControl', valid=True, logMonoTime=now - (200_000_000 if variation == 'stale' else 0))
        if variation == 'active':
          control.carControl.enabled = control.carControl.latActive = True
          control.carControl.actuators.torque = .1
        events = messaging.new_message('onroadEvents', 1, valid=True, logMonoTime=now)
        events.onroadEvents[0].name = 'selfdriveInitializing'
        events.onroadEvents[0].noEntry = True
        pandas = messaging.new_message('pandaStates', 1, valid=True, logMonoTime=now)
        panda = pandas.pandaStates[0]
        config = card.CP.safetyConfigs[0]
        panda.safetyModel = config.safetyModel if tick >= 5 else 'elm327'
        panda.safetyParam = (config.safetyParam ^ int(variation == 'native_mismatch')) if tick >= 5 else 1
        panda.alternativeExperience = card.CP.alternativeExperience if tick >= 5 else 0
        panda.ignitionLine = True
        if variation == 'changed_cp':
          card.CP.mass += 1
        if variation == 'native_fault':
          panda.faults = ['relayMalfunction']
        card.sm.update_msgs(now / 1e9, [control.as_reader(), events.as_reader(), pandas.as_reader()])
        with patch.object(card_module, 'REPLAY', False), \
             patch.object(card_module.messaging, 'drain_sock_raw', return_value=[batch.to_bytes()]), \
             patch.object(card_module.time, 'monotonic_ns', return_value=now), \
             patch.object(card_module.time, 'monotonic', return_value=now / 1e9), \
             patch.object(card_module.time, 'clock_gettime_ns', return_value=now), patch.object(card.sm, 'update'):
          if variation == 'invalid_can':
            with patch.object(card.CI, 'update', wraps=card.CI.update) as parse:
              def invalid(*args, **kwargs):
                state = parse._mock_wraps(*args, **kwargs)
                state.canValid = False
                return state
              parse.side_effect = invalid
              card.step()
          else:
            card.step()
        assert card.CS_prev.canValid == (variation != 'invalid_can') and not card.CS_prev.canTimeout
      if variation not in ('normal', 'aol_off'):
        assert not emitted
        return
      assert card.ci_initialized and saved.get_bool('ControlsReady')
      assert emitted and all(valid for _, _, valid in emitted)
      assert min(frame for frame, _, _ in emitted) <= 6
      scc = [(frame, msg) for frame, msg, _ in emitted if msg[0] == 0x1A0]
      testers = [frame for frame, msg, _ in emitted if msg[0] == 0x730]
      assert len(scc) >= 300 and len(testers) >= 6
      assert max(b - a for a, b in zip(testers, testers[1:], strict=False)) <= 100
      parser = CANParser(DBC[CAR.KIA_EV6][Bus.pt], [('SCC_CONTROL', 0)], card.CI.CC.CAN.ECAN)
      for frame, msg in scc:
        parser.update([(10_000_000_000 + frame * 10_000_000, [msg])])
        values = parser.vl['SCC_CONTROL']
        assert (values['ACCMode'], values['aReqRaw'], values['aReqValue'], values['StopReq']) == (0, 0., 0., 0)
      assert card.last_actuators_output.torqueOutputCan == 0
    finally:
      card.vehicle_startup.close()


def test_stock_held_main_rebinding_and_cancel_keep_physical_edges():
  from dataclasses import replace
  from openpilot.starpilot.aol.intent import AolSettings
  from openpilot.starpilot.car.hyundai.aol import create_intent

  owner = create_intent(stock.params(CAR.KIA_EV6), AolSettings(True, 0., AOL_TOGGLE, 0, (0, 0, 0), (0, 0, 0)))
  cs = structs.CarState(canValid=True, gearShifter='drive')
  cs.cruiseState.available = True
  def update(events, now):
    cs.buttonEvents = [structs.CarState.ButtonEvent(type=kind, pressed=pressed) for kind, pressed in events]
    owner.update(cs, fault_active=False, now_ns=now)
  update([], 1)
  update([('lkas', True)], 2)
  update([('lkas', False)], 3)
  update([('mainCruise', True)], 4)
  assert owner.allowed_latch
  owner.settings = replace(owner.settings, main_action=AOL_TOGGLE)
  update([('mainCruise', True)], 5)
  assert owner.allowed_latch  # A new mapping cannot turn an already held level into another press.
  update([('mainCruise', False)], 6)
  update([('mainCruise', True)], 7)
  assert not owner.allowed_latch
  owner.settings = replace(owner.settings, main_action=0)
  update([('mainCruise', False)], 8)
  update([('lkas', True)], 9)
  assert owner.allowed_latch
  update([('cancel', True)], 10)
  assert not owner.allowed_latch
