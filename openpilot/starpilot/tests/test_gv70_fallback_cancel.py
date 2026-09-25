"""Requested GV70 takeover fallback keeps stock Cancel and Resume distinct."""
import unittest

from opendbc.car import structs
from opendbc.car.hyundai.values import CAR
from openpilot.starpilot.tests import test_ev6_startup as fixture


class TestGV70FallbackCancel(unittest.TestCase):
  def test_actual_startup_fallback_suppresses_cancel_but_preserves_resume(self):
    for mode, capture in (("restored", True), ("sent", False)):
      ci, holder, _ = fixture.TestEV6Startup("runTest").exercise(
        mode, capture=capture, car=CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN)
      self.assertFalse(ci.CP.openpilotLongitudinalControl)
      self.assertTrue(ci.CC.gv70_stock_fallback)
      command = structs.CarControl()
      command.cruiseControl.cancel = True
      cancels = []
      for tick in range(60):
        _, frames = ci.apply(command.as_reader(), (tick+1)*10_000_000)
        cancels.extend(frame for frame in frames if frame[0] == 0x1cf)
      self.assertEqual(cancels, [])
      command.cruiseControl.cancel = False
      command.cruiseControl.resume = True
      resumes = []
      for tick in range(60, 120):
        _, frames = ci.apply(command.as_reader(), (tick+1)*10_000_000)
        resumes.extend(frame for frame in frames if frame[0] == 0x1cf)
      self.assertTrue(resumes)
      self.assertTrue(holder.owner.ready)
