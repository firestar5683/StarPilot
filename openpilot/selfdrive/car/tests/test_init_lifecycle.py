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


if __name__ == '__main__':
  unittest.main()
