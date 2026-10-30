"""Regression: Mazda wheel-action availability must import a module that exists."""

import unittest

from opendbc.car import structs
from opendbc.car.mazda.values import CAR, MazdaFlags


class MazdaWheelActionsTest(unittest.TestCase):
  def _mazda(self, fingerprint=CAR.MAZDA_CX5_2022):
    return structs.CarParams(carFingerprint=fingerprint, brand="mazda", flags=int(MazdaFlags.GEN1))

  def test_cancel_keys_resolve_without_import_error(self):
    # Before the fix these raised ModuleNotFoundError: opendbc.car.mazda.aol,
    # which killed the Galaxy settings handler and surfaced as HTTP 502 to the app.
    from openpilot.starpilot.controllers import wheel_actions

    for key in ("CancelButtonControl", "LongCancelButtonControl", "VeryLongCancelButtonControl"):
      self.assertFalse(wheel_actions.button_reported(self._mazda(), key))

  def test_main_cruise_key_does_not_consult_mazda_aol(self):
    from openpilot.starpilot.controllers import wheel_actions

    self.assertFalse(wheel_actions.button_reported(self._mazda(), "MainCruiseButtonControl"))


if __name__ == "__main__":
  unittest.main()
