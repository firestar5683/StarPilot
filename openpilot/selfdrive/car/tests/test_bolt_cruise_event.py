import unittest

from opendbc.car import structs
from opendbc.car.gm.tests.test_bolt_cc import fixture, feed, control
from opendbc.car.gm.values import CAR
from openpilot.selfdrive.car.car_events import CarEvents, EventName
from openpilot.selfdrive.selfdrived.events import EVENTS, ET


SUPPORTED_NON_ACC = (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_CC_2018_2021, CAR.CHEVROLET_BOLT_CC_2022_2023)


class TestBoltCruiseModeEvent(unittest.TestCase):
  def test_actual_bolt_ci_state_does_not_block_engagement_for_wrong_cruise_mode(self):
    for identity in SUPPORTED_NON_ACC:
      for removed in (False, True):
        cp, ci, packer = fixture(identity, removed=removed)
        state, _ = feed(ci, packer, 1_000_000_000, active=True, speed=20)
        self.assertTrue(state.canValid)
        self.assertFalse(cp.pcmCruise)
        self.assertTrue(state.cruiseState.enabled)
        events = CarEvents(cp).update(state.as_reader(), structs.CarState.new_message().as_reader(), control().as_reader())
        self.assertNotIn(EventName.wrongCruiseMode, events.names, (identity, removed))
        self.assertFalse(state.cruiseState.nonAdaptive)

  def test_wrong_mode_still_produces_stock_owner_no_entry_and_user_disable(self):
    cp, _, _ = fixture(CAR.CHEVROLET_BOLT_EUV)
    self.assertTrue(cp.pcmCruise)
    state = structs.CarState.new_message()
    state.cruiseState.nonAdaptive = True
    events = CarEvents(cp).update(state.as_reader(), structs.CarState.new_message().as_reader(), control().as_reader())
    self.assertIn(EventName.wrongCruiseMode, events.names)
    self.assertIn(ET.NO_ENTRY, EVENTS[EventName.wrongCruiseMode])
    self.assertIn(ET.USER_DISABLE, EVENTS[EventName.wrongCruiseMode])
