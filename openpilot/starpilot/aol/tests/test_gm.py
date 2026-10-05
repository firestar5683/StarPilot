"""Finalized GM startup ownership and independent-axis caller lifecycle."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.gm.aol import GM_AOL_WORDS, GM_BASE_GATEWAY_IDS, qualified_gm
from opendbc.car.gm.lateral import lane_centering_supported
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.tests.test_bolt_cc import params as bolt_params, feed as feed_car, control, native
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.car.gm.tests.test_bolt_factory_acc import factory_params
from opendbc.car.gm.tests.test_bolt_volt_configurations import ordinary_params
from opendbc.car.gm.tests.test_volt_camera_control import camera_params
from opendbc.car.gm.tests.test_volt_camera_removed import removed_params
from opendbc.car.gm.tests.test_volt_sdgm_control import sdgm_params
from opendbc.car.gm.values import CAR, DBC, ORDINARY_ASCM_CAR, ORDINARY_SDGM_CAR, ORDINARY_CAMERA_CAR, ORDINARY_CC_CAR
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car.card import Car
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.starpilot.aol.runtime import decide_axes
from openpilot.starpilot.aol.vehicle import policy_for
from openpilot.starpilot.aol.wire import IntentState, SafetyState, encode_safety
from openpilot.starpilot.lateral.tests.test_lane_runtime import feed
from openpilot.starpilot.tests.test_volt_disable_longitudinal import configured
from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences


BOLT_IDS = (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_CC_2018_2021,
            CAR.CHEVROLET_BOLT_CC_2022_2023, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL)


def _configurations():
  for identity in GM_BASE_GATEWAY_IDS:
    cp = ordinary_params(identity, radar=True)
    yield cp
    if identity == CAR.BUICK_LACROSSE:
      disabled = cp.as_reader().as_builder()
      VehicleStartupPreferences(disable_bolt_long=True).prepare(disabled)
      yield disabled
      held = cp.as_reader().as_builder()
      VehicleStartupPreferences(gm_auto_hold=True).prepare(held)
      yield held
  for identity in BOLT_IDS:
    for pedal in (False, True):
      for removed in (False, True):
        if identity == BOLT_IDS[-1] and pedal and removed:
          continue
        cp = bolt_params(identity, present=pedal, pedal=pedal, removed=removed)
        yield cp
        if pedal:
          disabled = cp.as_reader().as_builder()
          VehicleStartupPreferences(disable_bolt_long=True).prepare(disabled, fingerprints={2: {0x180: 4}})
          yield disabled
  for alpha in (False, True):
    yield factory_params(alpha=alpha)
    yield camera_params(alpha=alpha)
    yield removed_params(alpha=alpha)
    yield removed_params(alpha=alpha, alternate=True)
    for c9 in (False, True):
      yield sdgm_params(alpha=alpha, brake_c9=c9)
    for c9 in (False, True):
      for radar in (False, True):
        yield ordinary_params(CAR.CHEVROLET_VOLT_ASCM, alpha=alpha, sascm=True,
                              accelerator=not c9, radar=radar)
  for variant in ('be', 'f1', 'cc'):
    cp = configured(variant)
    yield cp
    disabled = cp.as_reader().as_builder()
    VehicleStartupPreferences(disable_bolt_long=True).prepare(disabled)
    yield disabled

  from opendbc.car.gm.tests.test_ascm_intercept import params as intercept_params
  from opendbc.car.gm.tests.test_ordinary_camera import params as ordinary_camera
  from opendbc.car.gm.tests.test_ordinary_camera_removed import params as ordinary_removed
  from opendbc.car.gm.tests.test_conventional_pedal import params as conventional_pedal
  from opendbc.car.gm.tests.test_silverado_cc_pedal import params as silverado_pedal
  for identity in ORDINARY_ASCM_CAR | ORDINARY_SDGM_CAR:
    for alpha in (False, True):
      for c9 in (False, True):
        for radar in (False, True):
          yield intercept_params(identity, sascm=True, accelerator=not c9, radar=radar, alpha=alpha)
  for identity in ORDINARY_CAMERA_CAR:
    for alpha in (False, True):
      for analog in (False, True):
        yield ordinary_camera(identity, alpha=alpha, be=analog)
        yield ordinary_removed(identity, alpha=alpha, analog=analog)
  for identity in ORDINARY_CC_CAR:
    yield intercept_params(identity)
    for removed in (False, True):
      for disabled in (False, True):
        yield conventional_pedal(identity, removed=removed, disabled=disabled)
  for removed in (False, True):
    for disabled in (False, True):
      yield silverado_pedal(removed=removed, disabled=disabled)


def configurations():
  for cp in _configurations():
    yield cp
    selected = cp.as_reader().as_builder()
    VehicleStartupPreferences(gm_auto_hold=True).prepare(selected)
    if selected.safetyConfigs[0].safetyParam != cp.safetyConfigs[0].safetyParam:
      yield selected


class TestGmAol(unittest.TestCase):
  def test_actual_final_cp_registry_and_isolation(self):
    words = set()
    for cp in configurations():
      with self.subTest(identity=cp.carFingerprint, word=hex(cp.safetyConfigs[0].safetyParam)):
        self.assertTrue(qualified_gm(cp))
        words.add(cp.safetyConfigs[0].safetyParam)
        self.assertTrue(policy_for(cp).normal_runtime_supported)
        for field in ('passive', 'dashcamOnly', 'notCar'):
          denied = cp.as_reader().as_builder()
          setattr(denied, field, True)
          self.assertFalse(qualified_gm(denied))
        denied = cp.as_reader().as_builder()
        denied.safetyConfigs[0].safetyModel = 'noOutput'
        self.assertFalse(qualified_gm(denied))
        denied = cp.as_reader().as_builder()
        denied.alternativeExperience = 33
        self.assertFalse(qualified_gm(denied))
    self.assertEqual(words, GM_AOL_WORDS, {"missing": GM_AOL_WORDS - words, "unexpected": words - GM_AOL_WORDS})

  def test_base_gateway_aol_preserves_tuning_and_lane_capability(self):
    for identity in GM_BASE_GATEWAY_IDS:
      cp = ordinary_params(identity, radar=True)
      with self.subTest(identity=identity):
        self.assertTrue(qualified_gm(cp))
        self.assertFalse(lane_centering_supported(cp))
        selected = cp.as_reader().as_builder()
        selected.alternativeExperience = 32
        self.assertTrue(qualified_gm(selected))
        self.assertFalse(lane_centering_supported(selected))
        for field, value in (('pcmCruise', True), ('radarUnavailable', True), ('alphaLongitudinalAvailable', True),
                             ('networkLocation', 'fwdCamera'), ('transmissionType', 'direct'), ('flags', 1)):
          denied = cp.as_reader().as_builder()
          setattr(denied, field, value)
          self.assertFalse(qualified_gm(denied))
        denied = cp.as_reader().as_builder()
        denied.safetyConfigs[0].safetyParam = 0x80
        self.assertEqual(qualified_gm(denied), identity == CAR.BUICK_LACROSSE)
        denied = cp.as_reader().as_builder()
        denied.openpilotLongitudinalControl = False
        self.assertEqual(qualified_gm(denied), identity == CAR.BUICK_LACROSSE)

  @staticmethod
  def card(cp, settings):
    settings.put_bool('OpenpilotEnabledToggle', True, block=True)
    def get_car(*args, pre_create_hook, **kwargs):
      selected = pre_create_hook(cp.as_reader().as_builder(), cp.carFingerprint, {}, [])
      return CarInterface(selected)
    with patch('openpilot.selfdrive.car.card.messaging.recv_one_retry', return_value=SimpleNamespace(can=[1])), \
         patch('openpilot.selfdrive.car.card.get_car', side_effect=get_car):
      return Car()

  def test_actual_card_startup_default_off_and_main_cycle_fault_recovery(self):
    with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1', 'AOL_REPLAY_RUNTIME': '0'}):
      settings = Params()
      cp = factory_params(alpha=False)
      ordinary = self.card(cp, settings)
      self.assertIsNone(ordinary.aol_card_intent)
      self.assertEqual(ordinary.CP.alternativeExperience, 0)
      settings.put_bool('AlwaysOnLateral', True, block=True)
      selected = self.card(cp, settings)
      self.assertEqual(selected.CP.safetyConfigs[0].safetyParam, cp.safetyConfigs[0].safetyParam)
      self.assertEqual(selected.CP.alternativeExperience, 32)
      self.assertFalse(selected.aol_card_intent.explicit_latch)
      cs = structs.CarState(canValid=True, gearShifter='drive', vEgo=20.)
      cs.cruiseState.available = True
      selected.aol_card_intent.update(cs)
      self.assertTrue(selected.aol_card_intent.allowed_latch)
      cs.steerFaultTemporary = True
      selected.aol_card_intent.update(cs, fault_active=False)
      self.assertTrue(selected.aol_card_intent.allowed_latch)
      cs.steerFaultTemporary = False
      cs.gearShifter = 'reverse'
      selected.aol_card_intent.update(cs, fault_active=False)
      self.assertTrue(selected.aol_card_intent.allowed_latch)
      self.assertFalse(selected.aol_card_intent.output(cs)[0])
      cs.gearShifter = 'drive'
      cs.steerFaultPermanent = True
      selected.aol_card_intent.update(cs, fault_active=True)
      self.assertFalse(selected.aol_card_intent.allowed_latch)
      cs.steerFaultPermanent = False
      selected.aol_card_intent.update(cs, fault_active=False)
      self.assertFalse(selected.aol_card_intent.allowed_latch)
      cs.cruiseState.available = False
      cs.canValid = False
      selected.aol_card_intent.update(cs, fault_active=False)
      cs.cruiseState.available = True
      cs.canValid = True
      selected.aol_card_intent.update(cs, fault_active=False)
      self.assertFalse(selected.aol_card_intent.allowed_latch)
      cs.cruiseState.available = False
      selected.aol_card_intent.update(cs, fault_active=False)
      cs.cruiseState.available = True
      selected.aol_card_intent.update(cs, fault_active=False)
      self.assertTrue(selected.aol_card_intent.allowed_latch)

  def test_actual_controls_axis_receipt_and_fault_gates(self):
    with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1', 'REPLAY': '1', 'AOL_REPLAY_RUNTIME': '0'}):
      settings = Params()
      settings.put_bool('AlwaysOnLateral', True, block=True)
      selected = self.card(factory_params(alpha=False), settings)
      controls = Controls()
      cases = ((None, True), ('temporary', False), (None, True), ('reverse', False),
               ('brake_allowed', True), ('brake_paused', False), ('regen', True),
               ('permanent', False), (None, False), ('off', False), ('on', True))
      for tick, (fault, expected) in enumerate(cases):
        now = 1_000_000_000 + tick * 10_000_000
        feed(controls, now, tick, active=False, enabled=False)
        cs = structs.CarState(canValid=True, vEgo=20., gearShifter='drive')
        cs.cruiseState.available = fault != 'off'
        cs.steerFaultTemporary = fault == 'temporary'
        cs.steerFaultPermanent = fault == 'permanent'
        cs.gearShifter = 'reverse' if fault == 'reverse' else 'drive'
        cs.brakePressed = fault in ('brake_allowed', 'brake_paused')
        cs.regenBraking = fault == 'regen'
        selected.aol_card_intent.update(cs, fault_active=cs.steerFaultPermanent)
        intent = IntentState('card', tick + 1, now, now, now + 30_000_000,
                             selected.aol_card_intent.allowed_latch, False, False, True, True)
        native = SafetyState(1, True, now, now + 200_000_000, int(structs.CarParams.SafetyModel.gm),
                             selected.CP.safetyConfigs[0].safetyParam, True, False, True, False, 'panda', 'gm-test')
        decision = decide_axes(standard_lateral=False, standard_longitudinal=False, intent=intent, native=native,
                               car_state=cs, initialized=True, model_ready=True, no_entry=False,
                               immediate_disable=False, dm_lockout=False,
                               pause_brake_mps=25. if fault == 'brake_paused' else 0.)
        axis = messaging.new_message('aolAxisState', valid=True, logMonoTime=now)
        axis.aolAxisState.qualified = True
        axis.aolAxisState.nativeAcknowledged = decision.native_acknowledged
        axis.aolAxisState.desiredLateral = decision.desired_lateral
        axis.aolAxisState.lateralActive = decision.lateral_active
        axis.aolAxisState.sessionId = 'gm-test'
        axis.aolAxisState.observedMonoTime = now
        axis.aolAxisState.validUntilMonoTime = now + 30_000_000
        receipt = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=now)
        receipt.aolSafetyWire = encode_safety(native)
        state = messaging.new_message('carState', valid=True, logMonoTime=now)
        state.carState = cs
        controls.sm.update_msgs((now + 1_000) / 1e9, [axis.as_reader(), receipt.as_reader(), state.as_reader()])
        command, _ = controls.state_control()
        self.assertEqual(command.latActive, expected)
        self.assertFalse(command.longActive)


  def test_base_gateway_actual_card_controls_parser_and_native_axes(self):
    cases = [(identity, False, False) for identity in GM_BASE_GATEWAY_IDS]
    cases += [(CAR.BUICK_LACROSSE, True, False), (CAR.BUICK_LACROSSE, False, True)]
    safety = libsafety_py.libsafety
    for identity, held, disabled in cases:
      with self.subTest(identity=identity, held=held, disabled=disabled), OpenpilotPrefix(), \
           patch.dict(os.environ, {'SIMULATION': '1', 'REPLAY': '1', 'AOL_REPLAY_RUNTIME': '0'}):
        settings = Params()
        settings.put_bool('GMAutoHold', held, block=True)
        settings.put_bool('DisableOpenpilotLongitudinal', disabled, block=True)
        factory = ordinary_params(identity, radar=True)
        default = self.card(factory, settings)
        self.assertIsNone(default.aol_card_intent)
        self.assertEqual(default.CP.alternativeExperience, 0)
        settings.put_bool('AlwaysOnLateral', True, block=True)
        selected = self.card(factory, settings)
        self.assertEqual(selected.CP.safetyConfigs[0].safetyParam, default.CP.safetyConfigs[0].safetyParam)
        self.assertEqual(selected.CP.lateralTuning.to_dict(), default.CP.lateralTuning.to_dict())
        self.assertEqual(selected.CP.alternativeExperience, 32)
        self.assertEqual(selected.CP.openpilotLongitudinalControl, not disabled)
        self.assertFalse(selected.CP.pcmCruise)
        self.assertEqual(selected.CP.safetyConfigs[0].safetyParam, 0x80 if held else 0)
        self.assertEqual(selected.CP.lateralTuning.to_dict(), factory.lateralTuning.to_dict())
        self.assertFalse(lane_centering_supported(selected.CP))
        controls = Controls()
        self.assertEqual(controls.CP.lateralTuning.to_dict(), factory.lateralTuning.to_dict())
        self.assertEqual(controls.CP.lateralTuning.which(), factory.lateralTuning.which())
        ci = selected.CI
        packer = CANPacker(DBC[identity][Bus.pt])
        safety.set_alternative_experience(32)
        self.assertEqual(safety.set_safety_hooks(structs.CarParams.SafetyModel.gm, selected.CP.safetyConfigs[0].safetyParam), 0)
        safety.init_tests()
        seen_lateral = seen_longitudinal = False
        for tick in range(150):
          now = 1_000_000_000 + tick * 10_000_000
          ordinary = 41 <= tick < 60 and not disabled
          main = not 20 <= tick < 30
          gas, brake, reverse = 70 <= tick < 80, 80 <= tick < 90, 90 <= tick < 100
          _, packets = feed_car(SimpleNamespace(update=lambda _: None), packer, now, counter=tick % 4,
                                active=ordinary, speed=20., camera=False)
          packets = [packet for packet in packets if packet[0] not in (0xC9, 0x1C4, 0xBE, 0x1E1, 0x1F5, 0xBD)]
          packets += [packer.make_can_msg('AcceleratorPedal2', 0, {'CruiseState': 2 if ordinary else 0,
                                                                  'AcceleratorPedal2': 30 if gas else 0}),
                      packer.make_can_msg('ECMAcceleratorPos', 0, {'BrakePedalPos': 20 if brake else 0}),
                      packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 2 if reverse else 4}),
                      packer.make_can_msg('ASCMSteeringButton', 0, {'ACCButtons': 3 if tick == 40 else 6 if tick == 60 else 1,
                                                                  'RollingCounter': tick % 4})]
          if not 100 <= tick < 140:
            packets.append(packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': int(main)}))
          ci.update([(now - 1_000_000, packets)])
          cs = ci.update([(now, packets)])
          for packet in packets:
            native('rx', packet, now // 1000)
          safety.safety_tick()
          safety.set_aol_test_heartbeat(True)
          selected.aol_card_intent.update(cs, now_ns=now, standard_enabled=ordinary)
          intent = IntentState('card', tick + 1, now, now, now + 30_000_000,
                               selected.aol_card_intent.allowed_latch, False, False, True, True)
          wanted = decide_axes(standard_lateral=ordinary, standard_longitudinal=ordinary, intent=intent, native=None,
                               car_state=cs, initialized=True, model_ready=True, no_entry=False,
                               immediate_disable=False, dm_lockout=False, pause_brake_mps=25.)
          safety.aol_set_host_request(int(wanted.desired_lateral) | (int(wanted.desired_longitudinal) << 1))
          safety.set_timer(now // 1000 + 1)
          mask = safety.aol_get_permission_mask()
          receipt_state = SafetyState(1, True, now, now + 200_000_000, int(structs.CarParams.SafetyModel.gm),
                                      selected.CP.safetyConfigs[0].safetyParam,
                                      bool(mask & 1), bool(mask & 2),
                                      wanted.desired_lateral, wanted.desired_longitudinal, 'panda', 'gm-gateway-test')
          decision = decide_axes(standard_lateral=ordinary, standard_longitudinal=ordinary, intent=intent, native=receipt_state,
                                 car_state=cs, initialized=True, model_ready=True, no_entry=False,
                                 immediate_disable=False, dm_lockout=False, pause_brake_mps=25.)
          feed(controls, now, tick, active=ordinary, enabled=ordinary)
          axis = messaging.new_message('aolAxisState', valid=True, logMonoTime=now)
          axis.aolAxisState.qualified = True
          axis.aolAxisState.nativeAcknowledged = True
          axis.aolAxisState.desiredLateral = decision.desired_lateral
          axis.aolAxisState.desiredLongitudinal = decision.desired_longitudinal
          axis.aolAxisState.lateralActive = decision.lateral_active
          axis.aolAxisState.longitudinalActive = decision.longitudinal_active
          axis.aolAxisState.sessionId = 'gm-gateway-test'
          axis.aolAxisState.observedMonoTime = now
          axis.aolAxisState.validUntilMonoTime = now + 30_000_000
          receipt = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=now)
          from dataclasses import replace
          transport_receipt = receipt_state
          if tick == 11:
            transport_receipt = replace(receipt_state, safetyParam=5)
          elif tick == 12:
            transport_receipt = replace(receipt_state, axisSessionId='wrong-session')
          elif tick == 13:
            transport_receipt = replace(receipt_state, observedMonoTime=now + 1)
          elif tick == 14:
            transport_receipt = replace(receipt_state, validUntilMonoTime=now - 1)
          receipt.aolSafetyWire = encode_safety(transport_receipt)
          state = messaging.new_message('carState', valid=True, logMonoTime=now)
          state.carState = cs
          controls.sm.update_msgs((now + 1_000) / 1e9, [axis.as_reader(), receipt.as_reader(), state.as_reader()])
          command, _ = controls.state_control()
          self.assertEqual(command.latActive, decision.lateral_active and tick not in (11, 12, 13, 14))
          self.assertEqual(command.longActive, ordinary)
          self.assertEqual(bool(safety.get_controls_allowed()), 41 <= tick < 60)
          if not main or brake or reverse or 131 <= tick < 140:
            self.assertFalse(command.latActive)
          if tick == 10:
            self.assertTrue(command.latActive)
          command.actuators.torque = .02 if command.latActive else 0.
          _, messages = ci.apply(command.as_reader(), now + 2)
          for message in messages:
            self.assertTrue(native('tx', message, now // 1000 + 1), (tick, message))
          seen_lateral |= command.latActive and not command.longActive
          seen_longitudinal |= command.longActive
        self.assertTrue(seen_lateral)
        self.assertEqual(seen_longitudinal, not disabled)
        safety.set_alternative_experience(0)

  def test_actual_card_forwards_shared_disarming_events(self):
    class IntentUpdated(Exception):
      pass
    with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1', 'AOL_REPLAY_RUNTIME': '0'}):
      settings = Params()
      settings.put_bool('AlwaysOnLateral', True, block=True)
      selected = self.card(factory_params(alpha=False), settings)
      cs = structs.CarState(canValid=True, vEgo=20., gearShifter='drive')
      cs.cruiseState.available = True
      selected.aol_card_intent.update(cs)
      self.assertTrue(selected.aol_card_intent.allowed_latch)
      now = 1_000_000_000
      events = messaging.new_message('onroadEvents', 1, valid=True, logMonoTime=now)
      events.onroadEvents[0].name = 'controlsMismatch'
      events.onroadEvents[0].immediateDisable = True
      control = messaging.new_message('carControl', valid=True, logMonoTime=now)
      selected.sm.update_msgs(now / 1e9, [events.as_reader(), control.as_reader()])
      with patch('openpilot.selfdrive.car.card.messaging.drain_sock_raw', return_value=[b'fixture']), \
           patch('openpilot.selfdrive.car.card.can_capnp_to_list', return_value=[]), \
           patch('openpilot.selfdrive.car.card.time.monotonic_ns', return_value=now), \
           patch('openpilot.selfdrive.car.card.REPLAY', False), \
           patch.object(selected.CI, 'update', return_value=cs), \
           patch.object(selected.RI, 'update', return_value=None), \
           patch.object(selected.sm, 'update'), \
           patch.object(selected, 'observe_distance_personality', side_effect=IntentUpdated):
        with self.assertRaises(IntentUpdated):
          selected.state_update()
      self.assertFalse(selected.aol_card_intent.allowed_latch)
      selected.aol_card_intent.update(cs, fault_active=False)
      self.assertFalse(selected.aol_card_intent.allowed_latch)


  def test_actual_controller_inactive_cruise_brake_and_regen_lateral_only(self):
    safety = libsafety_py.libsafety
    release = safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0
    cases = [bolt_params(BOLT_IDS[0]), configured('cc'), camera_params(alpha=False),
             camera_params(alpha=True), removed_params(alpha=False), removed_params(alpha=True),
             sdgm_params(alpha=False), sdgm_params(alpha=True)]
    for variant in ('be', 'f1'):
      cp = configured(variant)
      VehicleStartupPreferences(disable_bolt_long=True).prepare(cp)
      cases.append(cp)
    for cp in cases:
      with self.subTest(identity=cp.carFingerprint, word=hex(cp.safetyConfigs[0].safetyParam)):
        cp.alternativeExperience = 32
        ci = CarInterface(cp)
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        safety.init_tests()
        safety.set_alternative_experience(32)
        safety.set_safety_hooks(structs.CarParams.SafetyModel.gm, cp.safetyConfigs[0].safetyParam)
        safety.set_aol_test_heartbeat(True)
        supported = not release or cp.safetyConfigs[0].safetyParam not in (20, 0x4007, 0x5007, 0xC151)
        requested = []
        for tick in range(18):
          now = 1_000_000_000 + tick * 10_000_000
          out, sources = feed_car(ci, packer, now, counter=tick % 4, active=False, brake=True, regen=True)
          sources = [source for source in sources if source[0] not in (0x1C4, 0xBE, 0xF1)]
          sources.extend([packer.make_can_msg('AcceleratorPedal2', 0, {'CruiseState': 0}),
                          packer.make_can_msg('ECMAcceleratorPos', 0, {'BrakePedalPos': 12}),
                          packer.make_can_msg('EBCMBrakePedalPosition', 0, {'BrakePedalPosition': 6}),
                          packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCruiseState': 0})])
          out = ci.update([(now + 1, sources)])
          for source in sources:
            native('rx', source, now // 1000)
          safety.safety_tick()
          safety.aol_set_host_request(1)
          permission = safety.aol_get_permission_mask()
          cc = control(enabled=False, long_active=False)
          cc.latActive = bool(permission & 1)
          ci.CC.frame = tick
          _, messages = ci.apply(cc.as_reader(), now + 2)
          self.assertFalse(cc.longActive)
          for message in messages:
            if message[0] == 0x180:
              requested.append(bool(message[1][0] & 8))
              self.assertEqual(native('tx', message, now // 1000 + 1), supported)
        self.assertTrue(out.canValid)
        self.assertFalse(out.cruiseState.enabled)
        self.assertTrue(out.brakePressed)
        self.assertEqual(any(requested), supported)


  def test_actual_selfdrived_gas_override_keeps_longitudinal_request(self):
    from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
    from openpilot.selfdrive.selfdrived.state import StateMachine
    from openpilot.selfdrive.selfdrived.events import Events, EventName
    from openpilot.starpilot.aol.runtime import AxisDecision
    from openpilot.starpilot.aol.wire import encode_intent
    from openpilot.starpilot.aol.intent import AolSettings
    from openpilot.cereal import log
    with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1', 'REPLAY': '1'}):
      cp = configured('be')
      cp.alternativeExperience = 32
      now = 1_000_000_000
      cs = structs.CarState(canValid=True, vEgo=20., gearShifter='drive', gasPressed=True)
      cs.cruiseState.available = cs.cruiseState.enabled = True
      sd = SelfdriveD.__new__(SelfdriveD)
      sd.CP, sd.initialized, sd.aol_replay = cp, True, True
      sd.aol_car_state_log_ns = now
      sd.aol_session_id = 'gm-test'
      sd.aol_axis_decision = AxisDecision()
      sd.aol_dm_lateral_inhibit = False
      sd.aol_settings = AolSettings(True, 0., 0, 0, (0, 0, 0), (0, 0, 0))
      sd.nostalgia_paddle_cancel = False
      sd.state_machine = StateMachine()
      sd.state_machine.state = log.SelfdriveState.OpenpilotState.enabled
      sd.events = Events()
      sd.events.add(EventName.gasPressedOverride)
      sd.sm = messaging.SubMaster(['aolIntentWire', 'aolSafetyWire', 'modelV2',
                                   'extrinsicsCalibration', 'driverMonitoringState'])
      intent = messaging.new_message('aolIntentWire', 0, valid=True, logMonoTime=now)
      intent.aolIntentWire = encode_intent(IntentState('card', 1, now, now, now + 30_000_000,
                                                      True, False, False, True, True))
      receipt = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=now)
      receipt.aolSafetyWire = encode_safety(SafetyState(1, True, now, now + 200_000_000,
        int(structs.CarParams.SafetyModel.gm), cp.safetyConfigs[0].safetyParam,
        True, True, True, True, 'panda', 'gm-test'))
      model = messaging.new_message('modelV2', valid=True, logMonoTime=now)
      calibration = messaging.new_message('extrinsicsCalibration', valid=True, logMonoTime=now)
      calibration.extrinsicsCalibration.calStatus = 'calibrated'
      monitoring = messaging.new_message('driverMonitoringState', valid=True, logMonoTime=now)
      sd.sm.update_msgs(now / 1e9, [intent.as_reader(), receipt.as_reader(), model.as_reader(),
                                   calibration.as_reader(), monitoring.as_reader()])
      with patch('openpilot.selfdrive.selfdrived.selfdrived.REPLAY', True), \
           patch.object(sd, 'data_sample', return_value=cs), patch.object(sd, 'update_events'), \
           patch.object(sd, 'update_alerts'), patch.object(sd, 'update_conditional_mode'), \
           patch.object(sd, 'publish_selfdriveState'):
        sd.step()
      self.assertTrue(sd.enabled)
      self.assertTrue(sd.aol_axis_decision.desired_longitudinal)
      self.assertTrue(sd.aol_axis_decision.longitudinal_active)
      self.assertEqual(sd.state_machine.state, log.SelfdriveState.OpenpilotState.overriding)


  def test_existing_vehicle_factories_preserve_intent_lifecycle(self):
    from opendbc.car import gen_empty_fingerprint
    from opendbc.car.honda.interface import CarInterface as HondaInterface
    from opendbc.car.honda.values import CAR as HondaCars
    from openpilot.starpilot.lateral.tests.test_lane_runtime import ioniq_candidate
    from openpilot.starpilot.aol.intent import AolSettings, AolCardIntent
    from openpilot.starpilot.aol.vehicle import create_intent
    honda = HondaInterface.get_params(HondaCars.HONDA_ACCORD, gen_empty_fingerprint(), [], True, False, False)
    _, hyundai = ioniq_candidate()
    # Existing Card startup adds AOL bit 11 inside the qualified Ioniq namespace.
    hyundai.safetyConfigs[-1].safetyParam |= 0x0800
    settings = AolSettings(True, 0., 0, 0, (0, 0, 0), (0, 0, 0))
    for cp in (honda, hyundai):
      policy = policy_for(cp)
      self.assertTrue(policy.intent_supported, (cp.carFingerprint, cp.safetyConfigs[-1].safetyParam))
      selected = create_intent(cp, settings, policy)
      reference = AolCardIntent(settings, explicit_latch=policy.explicit_latch)
      self.assertIs(type(selected), AolCardIntent)
      for main, permanent, temporary, gear in ((True, False, False, 'drive'),
                                             (True, False, True, 'drive'),
                                             (True, False, False, 'reverse'),
                                             (True, True, False, 'drive'),
                                             (True, False, False, 'drive'),
                                             (False, False, False, 'drive'),
                                             (True, False, False, 'drive')):
        cs = structs.CarState(canValid=True, gearShifter=gear, steerFaultPermanent=permanent,
                              steerFaultTemporary=temporary)
        cs.cruiseState.available = main
        selected.update(cs, fault_active=permanent)
        reference.update(cs, fault_active=permanent)
        self.assertEqual(selected.__dict__.keys(), reference.__dict__.keys())
        for key, value in vars(selected).items():
          expected = vars(reference)[key]
          self.assertEqual(vars(value) if hasattr(value, '__dict__') else value,
                           vars(expected) if hasattr(expected, '__dict__') else expected, key)
        self.assertEqual(selected.output(cs), reference.output(cs))
