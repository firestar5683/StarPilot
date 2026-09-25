"""The first finalized CarParams must reach manager before periodic logging."""

import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.car import DT_CTRL
from opendbc.car.hyundai.ioniq6_handoff import prepare_ioniq6_long_candidate
from opendbc.car.structs import car
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.selfdrive.car.card import Car
from openpilot.selfdrive.car.cruise import VCruiseHelper
from openpilot.selfdrive.car.tests.test_hyundai_aol import candidate
from openpilot.system.manager.process_config import vision_slc_development


class Publisher:
  def __init__(self):
    self.messages: list[tuple[str, bytes]] = []

  def send(self, service, message):
    self.messages.append((service, message.to_bytes()))

  def car_params(self):
    return [messaging.log_from_bytes(payload).carParams for service, payload in self.messages
            if service == 'carParams']


def card_for(test: unittest.TestCase, cp, publisher, frame):
  card = Car.__new__(Car)
  card.CP = cp
  card.pm = publisher
  test.enterContext(patch.object(card, 'sm', SimpleNamespace(frame=frame, all_checks=lambda _: True), create=True))
  card.slc_replay = False
  card.curve_replay = False
  card.conditional_replay = False
  card.aol_replay = False
  card.last_actuators_output = car.CarControl.Actuators()
  card.can_rcv_cum_timeout_counter = 0
  test.enterContext(patch.object(card, 'rk', SimpleNamespace(remaining=0.0), create=True))
  card.v_cruise_helper = VCruiseHelper(cp)
  card.slc_receipts = []
  return card


class CarParamsFirstPublishTest(unittest.TestCase):
  def test_ioniq_prearm_sample_does_not_delay_final_long_cp_or_vision(self):
    stock, long_cp = candidate(False)
    publisher = Publisher()
    card = card_for(self, long_cp, publisher, 1)
    sm = messaging.SubMaster(['carControl'])
    sm.update_msgs(1.0, [])  # Pre-create ignition sample consumes frame 0.
    sm.update_msgs(1.01, [])  # First normal Card update advances to frame 1.
    self.assertEqual(sm.frame, 1)
    self.enterContext(patch.object(card, 'sm', sm))
    state = car.CarState(canValid=True)

    with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ',
                                                                  {'SLC_REPLAY_RUNTIME': '0', 'SLC_VISION_DEVELOPMENT': '0'}):
      params = Params(directory)
      params.put_bool('SpeedLimitController', True, block=True)
      params.put('SLCPriority1', 'Vision', block=True)
      self.assertFalse(vision_slc_development(True, params, car.CarParams.new_message()))
      self.assertFalse(vision_slc_development(True, params, stock))

      Car.state_publish(card, state, None)
      published = publisher.car_params()
      self.assertEqual(len(published), 1)
      self.assertEqual(int(published[0].safetyConfigs[0].safetyParam),
                       int(long_cp.safetyConfigs[0].safetyParam))
      self.assertTrue(vision_slc_development(True, params, published[0]))

      for frame in (2, int(50. / DT_CTRL) - 1):
        card.sm.frame = frame
        Car.state_publish(card, state, None)
      self.assertEqual(len(publisher.car_params()), 1)
      card.sm.frame = int(50. / DT_CTRL)
      Car.state_publish(card, state, None)
      self.assertEqual(len(publisher.car_params()), 2)

  def test_failed_prearm_publishes_only_final_stock_cp(self):
    stock, abandoned_long_cp = candidate(False)
    selected, pending = prepare_ioniq6_long_candidate(stock, abandoned_long_cp, enabled=False, is_release=False)
    self.assertFalse(pending)
    publisher = Publisher()
    card = card_for(self, selected, publisher, 1)
    Car.state_publish(card, car.CarState(canValid=True), None)
    published = publisher.car_params()
    self.assertEqual(len(published), 1)
    self.assertEqual(int(published[0].safetyConfigs[0].safetyParam),
                     int(stock.safetyConfigs[0].safetyParam))
    self.assertNotEqual(int(published[0].safetyConfigs[0].safetyParam),
                        int(abandoned_long_cp.safetyConfigs[0].safetyParam))

  def test_ordinary_first_frame_does_not_duplicate_publication(self):
    stock, _ = candidate(False)
    publisher = Publisher()
    card = card_for(self, stock, publisher, 0)
    Car.state_publish(card, car.CarState(canValid=True), None)
    card.sm.frame = 1
    Car.state_publish(card, car.CarState(canValid=True), None)
    self.assertEqual(len(publisher.car_params()), 1)


if __name__ == '__main__':
  unittest.main()
