import unittest

from opendbc.car import structs
from openpilot.starpilot.aol.intent import AolSettings, AOL_TOGGLE
from openpilot.starpilot.car.ford.aol import FordCardIntent


class TestFordAolIntent(unittest.TestCase):
  def intent(self, lkas=0):
    return FordCardIntent(None, AolSettings(True, 0.0, lkas, 0, (0, 0, 0), (0, 0, 0)))

  def frame(self, intent, *, main, button=None, valid=True, gear=None, temporary=False, now=1):
    cs = structs.CarState(canValid=valid, steerFaultTemporary=temporary,
                          gearShifter=gear or structs.CarState.GearShifter.drive)
    cs.cruiseState.available = main
    if button is not None:
      cs.buttonEvents = [structs.CarState.ButtonEvent(type=structs.CarState.ButtonEvent.Type.lkas, pressed=button)]
    intent.update(cs.as_reader(), now_ns=now)
    return cs

  def test_main_pulse_releases_before_tja_toggle(self):
    intent = self.intent()
    self.frame(intent, main=False)
    self.frame(intent, main=True, now=2)
    self.assertTrue(intent.allowed_latch)
    self.frame(intent, main=True, now=3)
    self.assertFalse(intent._main_held)
    self.frame(intent, main=True, button=True, now=4)
    self.assertFalse(intent.allowed_latch)
    self.frame(intent, main=True, button=False, now=5)
    self.frame(intent, main=True, button=True, now=6)
    self.assertTrue(intent.allowed_latch)

  def test_lkas_managed_with_main_already_on(self):
    intent = self.intent(AOL_TOGGLE)
    self.frame(intent, main=True)
    self.assertFalse(intent.allowed_latch)
    self.frame(intent, main=True, button=True, now=2)
    self.assertTrue(intent.allowed_latch)

  def test_temporary_state_retains_intent_but_rx_loss_does_not(self):
    intent = self.intent()
    self.frame(intent, main=False)
    self.frame(intent, main=True, now=2)
    self.frame(intent, main=True, now=3)
    reverse = self.frame(intent, main=True, gear=structs.CarState.GearShifter.reverse, now=4)
    self.assertTrue(intent.allowed_latch)
    self.assertFalse(intent.output(reverse.as_reader())[0])
    self.frame(intent, main=True, temporary=True, now=5)
    self.assertTrue(intent.allowed_latch)
    self.frame(intent, main=True, valid=False, now=6)
    self.assertFalse(intent.allowed_latch)
    self.frame(intent, main=True, now=7)
    self.assertFalse(intent.allowed_latch)
