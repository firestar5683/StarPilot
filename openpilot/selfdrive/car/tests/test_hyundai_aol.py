"""Ioniq 6 host requests remain gated by a separate exact native AOL profile."""

import unittest
import time
from types import SimpleNamespace
from unittest import mock

from opendbc.can import CANParser
from opendbc.car import Bus, gen_empty_fingerprint
from opendbc.car.hyundai.tests.test_ioniq6_longitudinal import controller_fixture
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.ioniq6_handoff import build_ioniq6_hda2_long_candidate
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags
from opendbc.car.structs import car
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.starpilot.aol.intent import AolCardIntent, AolSettings
from openpilot.starpilot.aol.runtime import current_native, decide_axes, monitoring_lateral_engaged
from openpilot.starpilot.aol.vehicle import native_latch_rejected, policy_for
from openpilot.starpilot.aol.wire import SafetyState, encode_safety
from openpilot.starpilot.car.hyundai.aol import ioniq6_settings_capable, qualified_ioniq6


def candidate(alt: bool):
  fp = gen_empty_fingerprint()
  steering, support = ((0x110, 0x362) if alt else (0x50, 0x2A4))
  fp[2][steering] = 32 if alt else 16
  fp[2][support] = 32 if alt else 24
  fp[0][0x3A5] = 24
  fp[1].update({0x1CF: 8, 0x1AA: 16, 0x35: 32, 0x175: 24, 0xA0: 24, 0xEA: 24,
                0x1BA: 24, 0x1E5: 16, 0x36A: 16})
  stock = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, fp, [], False, False, False)
  long_cp = build_ioniq6_hda2_long_candidate(stock, fp)
  assert long_cp is not None
  return stock, long_cp


def state():
  return car.CarState(canValid=True, gearShifter=car.CarState.GearShifter.drive, vEgo=20.0)


class Ioniq6HostTests(unittest.TestCase):
  def test_native_token_loss_resynchronizes_card_without_changing_native_safety(self):
    from opendbc.safety.tests.test_hyundai_ioniq6_long import TestHyundaiIoniq6Long

    native_test = TestHyundaiIoniq6Long()
    native_test.setUp()
    if native_test.release:
      self.skipTest("RELEASE denies the Ioniq 6 AOL profiles")
    from opendbc.can import CANPacker
    for alt, raw in ((False, 0x8815), (True, 0x8895)):
      with self.subTest(alt=alt), OpenpilotPrefix():
        _, cp = candidate(alt)
        cp.safetyConfigs[0].safetyParam = raw
        native_test.mode(raw)
        safety = native_test.safety
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        native_test.refresh_required_rx(packer, 1, 1_000_000)
        safety.set_aol_test_heartbeat(True)
        owner = AolCardIntent(AolSettings(True, 0, 0, 0, (0, 0, 0), (0, 0, 0)), explicit_latch=True)
        cs = state()
        owner.update(cs, now_ns=1_000_000_000)
        sm = messaging.SubMaster(['aolSafetyWire'])

        def buttons(counter, pressed, safety=safety, packer=packer, cs=cs, owner=owner):
          self.assertTrue(safety.safety_rx_hook(native_test.packet(packer.make_can_msg(
            'CRUISE_BUTTONS', 1, {'COUNTER': counter, 'LDA_BTN': int(pressed)}))))
          cs.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=pressed)]
          owner.update(cs, now_ns=1_000_000_000 + counter * 10_000_000)

        def receipt(stamp, safety=safety, cp=cp, raw=raw, sm=sm):
          requested, allowed = safety.aol_get_request_mask(), safety.aol_get_permission_mask()
          message = messaging.new_message('aolSafetyWire', 0, valid=True)
          message.logMonoTime = stamp
          message.aolSafetyWire = encode_safety(SafetyState(
            1, True, stamp, stamp + 200_000_000, int(cp.safetyConfigs[0].safetyModel.raw), raw,
            bool(allowed & 1), bool(allowed & 2), bool(requested & 1), bool(requested & 2), 'panda', 'selfdrived'))
          sm.update_msgs(stamp / 1e9, [message.as_reader()])
          return current_native(sm, cp, now_ns=stamp)

        buttons(2, True)
        safety.aol_set_host_request(1)
        self.assertEqual(safety.aol_get_permission_mask(), 1)
        buttons(3, False)
        self.assertTrue(owner.allowed_latch)
        # Brake/gas override affect neither the physical AOL token nor its host latch.
        for name, values in (('TCS', {'DriverBraking': 1}), ('ACCELERATOR', {'ACCELERATOR_PEDAL': 100})):
          self.assertTrue(safety.safety_rx_hook(native_test.packet(packer.make_can_msg(name, 1, values))))
          self.assertEqual(safety.aol_get_permission_mask(), 1)
        native = receipt(1_040_000_000)
        self.assertFalse(native_latch_rejected(cp, native))
        cs.buttonEvents = []
        cs.gasPressed, cs.brakePressed = True, True
        owner.update(cs, now_ns=1_040_000_000)
        self.assertTrue(owner.allowed_latch)
        safety.set_aol_test_heartbeat(False)
        self.assertEqual(safety.aol_get_permission_mask(), 0)
        safety.set_aol_test_heartbeat(True)
        safety.aol_set_host_request(1)
        native = receipt(1_050_000_000)
        self.assertTrue(native_latch_rejected(cp, native))
        owner.update(cs, now_ns=1_050_000_000, native_rejection_ns=native.observedMonoTime)
        self.assertFalse(owner.allowed_latch)
        self.assertEqual(safety.aol_get_permission_mask(), 0)
        # Native neutral after its reset, then one real LKAS edge restores both.
        buttons(6, False)
        buttons(7, True)
        safety.aol_set_host_request(1)
        self.assertTrue(owner.allowed_latch)
        self.assertEqual(safety.aol_get_permission_mask(), 1)

  def test_latch_feedback_requires_fresh_exact_native_receipt(self):
    _, cp = candidate(False)
    cp.safetyConfigs[0].safetyParam = 0x8815
    now = 2_000_000_000
    with OpenpilotPrefix():
      sm = messaging.SubMaster(['aolSafetyWire'])
      for requested, allowed in ((False, False), (False, True), (True, True), (True, False)):
        now += 100_000_000
        msg = messaging.new_message('aolSafetyWire', 0, valid=True)
        msg.logMonoTime = now
        msg.aolSafetyWire = encode_safety(SafetyState(1, True, now, now + 200_000_000,
          int(cp.safetyConfigs[0].safetyModel.raw), 0x8815, allowed, False, requested, False, 'panda', 'session'))
        sm.update_msgs(now / 1e9, [msg.as_reader()])
        self.assertEqual(native_latch_rejected(cp, current_native(sm, cp, now_ns=now)), requested and not allowed)
        self.assertFalse(native_latch_rejected(cp, current_native(sm, cp, now_ns=now + 201_000_000)))
        self.assertFalse(native_latch_rejected(cp, current_native(sm, cp, now_ns=now - 1)))
        wrong = cp.as_reader().as_builder()
        wrong.safetyConfigs[0].safetyParam = 0x8895
        self.assertFalse(native_latch_rejected(wrong, current_native(sm, wrong, now_ns=now)))

  def test_only_exact_tagged_hda2_long_cp_qualifies(self):
    for alt, raw in ((False, 0x8815), (True, 0x8895)):
      with self.subTest(alt=alt):
        stock, long_cp = candidate(alt)
        self.assertFalse(qualified_ioniq6(stock))
        self.assertFalse(qualified_ioniq6(long_cp))
        self.assertFalse(policy_for(long_cp).runtime_supported)
        cp = long_cp.as_reader().as_builder()
        cp.safetyConfigs[0].safetyParam = raw
        self.assertTrue(qualified_ioniq6(cp))
        self.assertTrue(policy_for(cp).runtime_supported)
        for wrong in (raw ^ 0x80, raw | 0x20, raw | 0x100, raw & ~0x8000, raw & ~0x800):
          cp.safetyConfigs[0].safetyParam = wrong
          self.assertFalse(qualified_ioniq6(cp), hex(wrong))
        cp.safetyConfigs[0].safetyParam = raw
        for field, value in (('pcmCruise', True), ('openpilotLongitudinalControl', False),
                             ('radarUnavailable', True), ('notCar', True), ('passive', True), ('dashcamOnly', True)):
          altered = cp.as_reader().as_builder()
          setattr(altered, field, value)
          self.assertFalse(qualified_ioniq6(altered), field)
        altered = cp.as_reader().as_builder()
        altered.flags |= int(HyundaiFlags.CANFD_ALT_BUTTONS)
        self.assertFalse(qualified_ioniq6(altered))
        altered = cp.as_reader().as_builder()
        altered.safetyConfigs[0].safetyModel = car.CarParams.SafetyModel.noOutput
        self.assertFalse(qualified_ioniq6(altered))

  def test_stock_settings_capability_is_separate_from_runtime(self):
    for alt in (False, True):
      stock, long_cp = candidate(alt)
      self.assertTrue(ioniq6_settings_capable(stock))
      self.assertTrue(policy_for(stock).runtime_supported)
      self.assertTrue(policy_for(stock).explicit_latch)
      self.assertTrue(ioniq6_settings_capable(long_cp))  # LONG saved choices do not require AOL's separate bit.
      tagged = long_cp.as_reader().as_builder()
      tagged.safetyConfigs[0].safetyParam |= 0x800
      self.assertTrue(ioniq6_settings_capable(tagged))
      self.assertTrue(policy_for(tagged).runtime_supported)
      changed = stock.as_reader().as_builder()
      changed.safetyConfigs[0].safetyParam |= 0x20
      self.assertFalse(ioniq6_settings_capable(changed))
      changed = stock.as_reader().as_builder()
      changed.flags |= int(HyundaiFlags.CANFD_ALT_BUTTONS)
      self.assertFalse(ioniq6_settings_capable(changed))
      with mock.patch('openpilot.starpilot.car.hyundai.aol.IONIQ6_LONG_PREARM_ENABLED', False):
        self.assertTrue(ioniq6_settings_capable(stock))

  def test_tcs_availability_never_arms_explicit_lateral_latch(self):
    settings = AolSettings(True, 0.0, 0, 0, (0, 0, 0), (0, 0, 0))
    owner = AolCardIntent(settings, explicit_latch=True)
    cs = state()
    cs.cruiseState.available = True
    owner.update(cs)
    self.assertFalse(owner.output(cs)[0])
    cs.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
    owner.update(cs)
    self.assertTrue(owner.output(cs)[0])
    cs.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=False)]
    owner.update(cs)
    cs.buttonEvents = []
    cs.brakePressed = True
    cs.gasPressed = True
    owner.update(cs)
    self.assertTrue(owner.output(cs)[0])
    cs.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
    owner.update(cs)
    self.assertFalse(owner.output(cs)[0])
    cs.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.mainCruise, pressed=True)]
    owner.update(cs)
    self.assertTrue(owner.output(cs)[0])
    cs.buttonEvents = []
    cs.accFaulted = True
    owner.update(cs)
    self.assertFalse(owner.output(cs)[0])
    cs.accFaulted = False
    cs.canValid = False
    owner.update(cs)
    self.assertFalse(owner.output(cs)[0])

  def test_startup_held_and_simultaneous_buttons_have_one_combined_edge(self):
    settings = AolSettings(True, 0.0, 0, 0, (0, 0, 0), (0, 0, 0))
    main = car.CarState.ButtonEvent.Type.mainCruise
    lkas = car.CarState.ButtonEvent.Type.lkas
    cs = state()
    owner = AolCardIntent(settings, explicit_latch=True)
    cs.buttonEvents = [car.CarState.ButtonEvent(type=main, pressed=True)]
    owner.update(cs)
    self.assertFalse(owner.output(cs)[0])  # held at initialization is ignored
    cs.buttonEvents = []
    owner.update(cs)
    self.assertFalse(owner.output(cs)[0])
    cs.buttonEvents = [car.CarState.ButtonEvent(type=main, pressed=False)]
    owner.update(cs)
    self.assertFalse(owner.output(cs)[0])
    cs.buttonEvents = [car.CarState.ButtonEvent(type=main, pressed=True),
                       car.CarState.ButtonEvent(type=lkas, pressed=True)]
    owner.update(cs)
    self.assertTrue(owner.output(cs)[0])  # one combined gesture, not two toggles
    cs.buttonEvents = [car.CarState.ButtonEvent(type=main, pressed=False)]
    owner.update(cs)
    self.assertTrue(owner.output(cs)[0])
    cs.buttonEvents = [car.CarState.ButtonEvent(type=lkas, pressed=False)]
    owner.update(cs)
    self.assertTrue(owner.output(cs)[0])
    cs.buttonEvents = [car.CarState.ButtonEvent(type=lkas, pressed=True)]
    owner.update(cs)
    self.assertFalse(owner.output(cs)[0])

  def test_native_reset_token_never_grants_without_matching_host_request(self):
    settings = AolSettings(True, 0.0, 0, 0, (0, 0, 0), (0, 0, 0))
    owner = AolCardIntent(settings, explicit_latch=True)
    cs = state()
    owner.update(cs)  # neutral baseline
    button = car.CarState.ButtonEvent.Type.lkas
    cs.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=True)]
    owner.update(cs)
    self.assertTrue(owner.output(cs)[0])
    cs.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=False)]
    owner.update(cs)
    # Native can revoke its idempotent token independently after heartbeat/RX
    # loss; host's next deliberate toggle requests off, so a new native token
    # cannot grant actuation until another explicit host-on gesture.
    cs.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=True)]
    owner.update(cs)
    self.assertFalse(owner.output(cs)[0])

  def test_four_axes_require_exact_native_readback(self):
    for alt, raw in ((False, 0x8815), (True, 0x8895)):
      _, cp = candidate(alt)
      cp.safetyConfigs[0].safetyParam = raw
      stamp = 1_000_000_000
      for standard_long, lateral_latch, expected in ((False, False, 'off'), (False, True, 'lateralOnly'),
                                                      (True, False, 'longitudinalOnly'), (True, True, 'combined')):
        cp.safetyConfigs[0].safetyParam = raw
        desired_lat, desired_long = lateral_latch, standard_long
        wire = encode_safety(SafetyState(1, True, stamp, stamp + 200_000_000,
                                        int(car.CarParams.SafetyModel.hyundaiCanfd), raw,
                                        desired_lat, desired_long, desired_lat, desired_long,
                                        'panda', 'drive-session'))
        class SafetySM:
          valid = {'aolSafetyWire': True}
          alive = {'aolSafetyWire': True}
          seen = {'aolSafetyWire': True}
          logMonoTime = {'aolSafetyWire': stamp}

          def __init__(self, payload):
            self.payload = payload

          def __getitem__(self, key):
            return self.payload

        sm = SafetySM(wire)
        native = current_native(sm, cp, now_ns=stamp + 1_000_000, axis_session_id='drive-session')
        self.assertIsNotNone(native)
        intent = SimpleNamespace(allowedLatch=lateral_latch, pauseLateral=False, pauseLongitudinal=False)
        decision = decide_axes(standard_lateral=False, standard_longitudinal=standard_long,
                               intent=intent, native=native, car_state=state(), initialized=True,
                               model_ready=True, no_entry=False, immediate_disable=False, dm_lockout=False,
                               pause_brake_mps=0.0)
        self.assertEqual(decision.mode, expected)
        self.assertEqual((decision.desired_lateral, decision.desired_longitudinal), (desired_lat, desired_long))
        cp.safetyConfigs[0].safetyParam = raw ^ 0x800
        self.assertIsNone(current_native(sm, cp, now_ns=stamp + 1_000_000, axis_session_id='drive-session'))

  def test_monitoring_requires_fresh_matching_native_lateral_permission(self):
    stamp = 1_000_000_000
    class MonitorSM:
      valid = {'aolAxisState': True, 'aolSafetyWire': True}
      alive = {'aolAxisState': True, 'aolSafetyWire': True}
      seen = {'aolAxisState': True, 'aolSafetyWire': True}
      logMonoTime = {'aolAxisState': stamp, 'aolSafetyWire': stamp}

      def __init__(self):
        self.axis = SimpleNamespace(qualified=True, sessionId='drive-session', lateralActive=True,
                                    nativeAcknowledged=True, observedMonoTime=stamp, validUntilMonoTime=stamp + 30_000_000)
        self.payload = b''

      def __getitem__(self, key):
        return self.axis if key == 'aolAxisState' else self.payload

    sm = MonitorSM()
    for raw in (0x8815, 0x8895):
      sm.payload = encode_safety(SafetyState(1, True, stamp, stamp + 200_000_000,
                                             int(car.CarParams.SafetyModel.hyundaiCanfd), raw,
                                             True, False, True, False, 'panda', 'drive-session'))
      self.assertTrue(monitoring_lateral_engaged(sm, now_ns=stamp + 1_000_000))
      sm.payload = encode_safety(SafetyState(1, True, stamp, stamp + 200_000_000,
                                             int(car.CarParams.SafetyModel.hyundaiCanfd), raw,
                                             False, False, True, False, 'panda', 'drive-session'))
      self.assertFalse(monitoring_lateral_engaged(sm, now_ns=stamp + 1_000_000))
    self.assertFalse(monitoring_lateral_engaged(sm, now_ns=stamp + 31_000_000))
    sm.payload = encode_safety(SafetyState(1, True, stamp, stamp + 200_000_000,
                                           int(car.CarParams.SafetyModel.hyundaiCanfd), 0x8015,
                                           True, False, True, False, 'panda', 'drive-session'))
    self.assertFalse(monitoring_lateral_engaged(sm, now_ns=stamp + 1_000_000))

  def test_actual_controls_lateral_only_command_has_active_steering_status(self):
    for alt, raw in ((False, 0x8815), (True, 0x8895)):
      with self.subTest(alt=alt), OpenpilotPrefix(), mock.patch.dict('os.environ', {'AOL_REPLAY_RUNTIME': '1', 'SIMULATION': '1'}):
        cp, controller_cs, controller = controller_fixture(alt, aol=True)
        self.assertEqual(cp.safetyConfigs[0].safetyParam, raw)
        Params().put('CarParams', cp.to_bytes(), block=True)
        controls = Controls()
        self.assertTrue(controls.aol_replay)
        cs = state()
        cs.cruiseState.available = True
        controls.sm.data['carState'] = cs.as_reader()
        axis = SimpleNamespace(sessionId='drive-session', nativeAcknowledged=True, lateralActive=True,
                               longitudinalActive=False, desiredLateral=True, desiredLongitudinal=False)
        native = SimpleNamespace(requestedLateral=True, requestedLongitudinal=False,
                                 lateralAllowed=True, longitudinalAllowed=False)
        with mock.patch('openpilot.selfdrive.controls.controlsd.current_axis', return_value=axis), \
             mock.patch('openpilot.selfdrive.controls.controlsd.current_native', return_value=native):
          command, _ = controls.state_control()
        self.assertFalse(command.enabled)
        self.assertTrue(command.latActive)
        self.assertFalse(command.longActive)
        _, frames = controller.update(command.as_reader(), controller_cs, 1_000_000_000)
        lfa = next(frame for frame in frames if frame[0] == 0x12A)
        parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [('LFA', 0)], 1)
        parser.update((1_000_000_000, [lfa]))
        self.assertEqual(parser.vl['LFA']['LKA_SysIndReq'], 2)
        self.assertEqual(parser.vl['LFA']['ActToiSta'], 1)
        scc = next(frame for frame in frames if frame[0] == 0x1A0)
        parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [('SCC_CONTROL', 0)], 1)
        parser.update((1_000_000_000, [scc]))
        self.assertEqual(parser.vl['SCC_CONTROL']['ACCMode'], 0)
        self.assertEqual(parser.vl['SCC_CONTROL']['aReqValue'], 0.)
        self.assertEqual(parser.vl['SCC_CONTROL']['aReqRaw'], 0.)

  def test_serialized_ioniq_axis_and_native_receipts_drive_both_controls_and_expire(self):
    with OpenpilotPrefix(), mock.patch.dict('os.environ', {'AOL_REPLAY_RUNTIME': '0', 'SIMULATION': '1'}):
      cp, _, _ = controller_fixture(True, aol=True)
      params = Params()
      params.put('CarParams', cp.to_bytes(), block=True)
      params.put_bool('AlwaysOnLateral', True, block=True)
      controls = Controls()
      self.assertTrue(controls.aol_replay)
      base = time.monotonic_ns()

      def command(stamp: int, *, longitudinal: bool, native_receipt: bool = True):
        car_msg = messaging.new_message('carState', valid=True)
        car_msg.logMonoTime = stamp
        car_msg.carState = state()
        drive_msg = messaging.new_message('selfdriveState', valid=True)
        drive_msg.logMonoTime = stamp
        drive_msg.selfdriveState.enabled = longitudinal
        axis_msg = messaging.new_message('aolAxisState', valid=True)
        axis_msg.logMonoTime = stamp
        axis = axis_msg.aolAxisState
        axis.qualified = axis.nativeAcknowledged = axis.lateralActive = axis.desiredLateral = True
        axis.longitudinalActive = axis.desiredLongitudinal = longitudinal
        axis.sessionId = 'ioniq-drive'
        axis.sourceCarStateMonoTime = stamp
        axis.observedMonoTime = stamp
        axis.validUntilMonoTime = stamp + 30_000_000
        events = [car_msg, drive_msg, axis_msg]
        if native_receipt:
          safety_msg = messaging.new_message('aolSafetyWire', 0, valid=True)
          safety_msg.logMonoTime = stamp
          safety_msg.aolSafetyWire = encode_safety(SafetyState(
            1, True, stamp, stamp + 200_000_000,
            int(car.CarParams.SafetyModel.hyundaiCanfd), 0x8895,
            True, longitudinal, True, longitudinal, 'panda', 'ioniq-drive'))
          events.append(safety_msg)
        controls.sm.update_msgs(stamp / 1e9, [messaging.log_from_bytes(event.to_bytes()) for event in events])
        with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=stamp + 1_000_000):
          return controls.state_control()[0]

      combined = command(base, longitudinal=True)
      self.assertTrue(combined.latActive and combined.longActive)
      lateral_only = command(base + 10_000_000, longitudinal=False)
      self.assertTrue(lateral_only.latActive)
      self.assertFalse(lateral_only.longActive)
      restored = command(base + 20_000_000, longitudinal=True)
      self.assertTrue(restored.latActive and restored.longActive)
      lost = command(base + 250_000_000, longitudinal=True, native_receipt=False)
      self.assertFalse(lost.latActive or lost.longActive)
