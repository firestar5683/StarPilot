import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from opendbc.car import gen_empty_fingerprint
from opendbc.car.can_definitions import CanData
from opendbc.car.gm.interface import CarInterface as GMInterface
from opendbc.car.gm.values import CAR as GMCar, GMFlags
from openpilot.cereal import messaging
from openpilot.selfdrive.car.card import Car, EventName
from openpilot.selfdrive.pandad import can_capnp_to_list
from openpilot.starpilot.vehicle_startup import VehicleStartupOwner


class CardInitLifecycleTest(unittest.TestCase):
  def test_bolt_pedal_waits_for_control_then_initializes_once_before_output(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x201] = 6
    cp = GMInterface.get_params(GMCar.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
                                fingerprint, [], False, False, False)
    self.assertTrue(cp.flags & GMFlags.PEDAL_LONG.value)

    order = []
    card = Car.__new__(Car)
    card.CP = cp
    card.vehicle_startup = VehicleStartupOwner()
    card.ci_initialized = False
    card.initialized_prev = False
    card.aol_replay = False
    card.ioniq6_long_prearmed = False
    card.ioniq6_long_selected = False
    card.can_callbacks = (lambda wait_for_one=False: [], lambda frames: None)

    def apply(*_):
      order.append('apply')
      return object(), [CanData(0x200, b'\x00' * 8, 0)]

    fake_ci = SimpleNamespace(
      CC=SimpleNamespace(),
      init=Mock(side_effect=lambda *_: order.append('init')),
      apply=Mock(side_effect=apply),
    )
    self.enterContext(patch.object(card, 'CI', fake_ci, create=True))
    self.enterContext(patch.object(card, 'params', SimpleNamespace(put_bool=lambda key, value: order.append((key, value))), create=True))
    sent = []

    def publish(service, packet):
      assert service == 'sendcan'
      sent.append(packet)
      order.append(('sendcan', tuple(can_capnp_to_list([packet], msgtype='sendcan')[0][1]),
                    bool(messaging.log_from_bytes(packet).valid)))

    self.enterContext(patch.object(card, 'pm', SimpleNamespace(send=publish), create=True))
    card.state_publish = Mock(side_effect=lambda *_: order.append('carState'))
    cs = SimpleNamespace(canValid=True, canTimeout=False)
    card.state_update = Mock(return_value=(cs, None))
    control = object()

    class SubMaster:
      valid = {'carControl': False}
      alive = {'carControl': False}
      seen = {'onroadEvents': False, 'carControl': True}
      logMonoTime = {}
      recv_time = {}
      events = []

      def __getitem__(self, key):
        return self.events if key == 'onroadEvents' else control

      def all_alive(self, services):
        return all(self.alive[name] for name in services)

    sm = SubMaster()
    self.enterContext(patch.object(card, 'sm', sm, create=True))
    for _ in range(30):
      card.step()
    self.assertNotIn('init', order)
    sm.seen['onroadEvents'] = True
    sm.events = [SimpleNamespace(name=EventName.selfdriveInitializing)]
    card.step()
    self.assertNotIn('init', order)

    sm.events = []
    card.step()  # Controls still have no live producer.
    self.assertNotIn('init', order)
    sm.valid['carControl'] = True
    sm.alive['carControl'] = True
    import time
    sm.logMonoTime['carControl'] = time.monotonic_ns()
    sm.recv_time['carControl'] = time.monotonic()
    cs.canValid = False
    card.step()  # A live controller cannot initialize against invalid CAN.
    self.assertNotIn('init', order)

    cs.canValid = True
    card.step()
    self.assertEqual(order[-5:-1], ['carState', 'init', ('ControlsReady', True), 'apply'])
    self.assertEqual(order[-1][0], 'sendcan')
    self.assertEqual([(frame[0], frame[2]) for frame in order[-1][1]], [(0x200, 0)])
    self.assertTrue(order[-1][2])
    self.assertTrue(all(not can_capnp_to_list([packet], msgtype='sendcan')[0][1] for packet in sent[:-1]))
    self.assertTrue(all(not messaging.log_from_bytes(packet).valid for packet in sent[:-1]))
    card.step()
    fake_ci.init.assert_called_once_with(cp, *card.can_callbacks)
    self.assertEqual(order.count(('ControlsReady', True)), 1)

    applied = fake_ci.apply.call_count
    sent_before = len(sent)
    sm.valid['carControl'] = False
    card.step()  # A live but invalid native command cannot renew CAN output.
    self.assertEqual(fake_ci.apply.call_count, applied)
    self.assertEqual(len(sent), sent_before)
    sm.valid['carControl'] = True
    card.step()
    self.assertEqual(fake_ci.apply.call_count, applied + 1)
    self.assertEqual(len(sent), sent_before + 1)
    self.assertTrue(messaging.log_from_bytes(sent[-1]).valid)
    fake_ci.init.assert_called_once_with(cp, *card.can_callbacks)

  def test_volt_sdgm_inactive_startup_continues_until_initialized(self):
    from opendbc.car import Bus, structs
    from opendbc.can import CANPacker
    from opendbc.car.gm.values import DBC
    from opendbc.car.gm.tests.test_volt_camera_control import feed_camera
    fingerprint = gen_empty_fingerprint()
    fingerprint[2][0x180] = 4
    fingerprint[0][0x2FF] = 8
    fingerprint[0][0xBE] = 6
    cp = GMInterface.get_params(GMCar.CHEVROLET_VOLT_2019, fingerprint, [], True, False, False)
    self.assertEqual(cp.safetyConfigs[0].safetyParam, 0x5007)
    cp.alternativeExperience = 32
    card = Car.__new__(Car)
    card.CP = cp
    card.CI = GMInterface(cp)
    card.vehicle_startup = VehicleStartupOwner()
    card.ci_initialized = False
    card.initialized_prev = False
    card.aol_replay = True
    card.ioniq6_long_prearmed = False
    card.ioniq6_long_selected = False
    card.can_callbacks = (lambda **_: [], lambda _: None)
    card.params = SimpleNamespace(put_bool=Mock())
    card.state_publish = Mock()
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    cs, _ = feed_camera(card.CI, packer, 22_000_000_000, active=False)
    self.assertTrue(cs.canValid)
    card.state_update = Mock(return_value=(cs, None))
    control = structs.CarControl.new_message().as_reader()
    panda = SimpleNamespace(safetyModel=cp.safetyConfigs[0].safetyModel, safetyParam=0x5007,
                            alternativeExperience=cp.alternativeExperience, safetyRxChecksInvalid=True)
    mono, boot = 20_000_000_000, 22_000_000_000

    class SubMaster:
      seen = dict.fromkeys(('carControl', 'pandaStates', 'onroadEvents'), True)
      valid = dict.fromkeys(('carControl', 'pandaStates'), True)
      alive = dict(valid)
      logMonoTime = {'carControl': mono, 'pandaStates': boot}
      recv_time = dict.fromkeys(('carControl', 'pandaStates'), mono / 1e9)
      events = [SimpleNamespace(name=EventName.selfdriveInitializing)]

      def __getitem__(self, key):
        return {'carControl': control, 'pandaStates': [panda], 'onroadEvents': self.events}[key]

      def all_alive(self, services):
        return all(self.alive[name] for name in services)

    card.sm = SubMaster()
    sent = []
    card.publish_sendcan = lambda frames, valid=True: sent.extend(frames)
    # These saved requests cannot acquire startup brake ownership.
    card.CI.CC.gm_auto_hold = True
    card.CI.CC.volt_one_pedal = True
    with patch('openpilot.selfdrive.car.card.time.monotonic_ns', return_value=mono), \
         patch('openpilot.selfdrive.car.card.time.clock_gettime_ns', return_value=boot), \
         patch.object(card.CI, 'apply', wraps=card.CI.apply) as apply, \
         patch.object(card.CI, 'init', wraps=card.CI.init) as init:
      self.assertFalse(card.startup_panda_configured())
      self.assertTrue(card.startup_panda_configured(inactive_keepalive=True))
      for _ in range(30):
        card.step()
      self.assertEqual(apply.call_count, 30)
      init.assert_called_once()
      card.params.put_bool.assert_called_once_with('ControlsReady', True)
      self.assertEqual(card.CI.CC.gm_auto_hold_state.drive_ns, 0)
      self.assertEqual(card.CI.CC.apply_brake, 0)
      for call in apply.call_args_list:
        cc, timestamp = call.args
        self.assertEqual(timestamp, boot)
        self.assertTrue(call.kwargs['startup_keepalive'])
        self.assertFalse(cc.enabled or cc.latActive or cc.longActive)
        self.assertEqual((cc.actuators.torque, cc.actuators.accel), (0., 0.))
      self.assertTrue(sent)
      for address, data, _ in sent:
        if address == 0x180:
          self.assertEqual(data[0] & 15, 0)
          self.assertEqual(data[1], 0)
        elif address == 0x315:
          self.assertEqual(((data[0] & 15) << 8) | data[1], 0)
        elif address == 0x2CB:
          self.assertEqual(data[0] & 1, 0)
      panda.safetyParam = 0x5087
      card.step()
      self.assertEqual(apply.call_count, 30)
      panda.safetyParam = 0x5007
      card.sm.logMonoTime['pandaStates'] = boot - 300_000_001
      card.step()
      self.assertEqual(apply.call_count, 30)
      card.sm.logMonoTime['pandaStates'] = boot
      active = structs.CarControl.new_message(latActive=True)
      control = active.as_reader()
      card.step()
      self.assertEqual(apply.call_count, 30)
      control = structs.CarControl.new_message().as_reader()
      card.sm.events = []
      card.step()
      self.assertEqual(apply.call_count, 31)
      self.assertEqual(apply.call_args.args[1], boot)
      self.assertFalse(apply.call_args.kwargs)


if __name__ == '__main__':
  unittest.main()
