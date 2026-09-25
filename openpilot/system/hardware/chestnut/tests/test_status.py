"""Chestnut alerts reflect the current model runtime rather than a branch label."""

import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from openpilot.common.hardware.usb import CHESTNUT_USB_PRODUCT
from openpilot.system.hardware.chestnut.status import ChestnutStatus


DEVICE = {"vendorId": 0xADD1, "productId": 0x0001, "product": CHESTNUT_USB_PRODUCT, "speedMbps": 10000}


class TestChestnutStatus(unittest.TestCase):
  def check(self, *, compiled: bool, devices: list[dict], branch: str = "domathon", offroad: bool = True,
            firmware_failed: bool = False, state=None) -> dict[str, bool]:
    alerts = {}
    with nullcontext(), \
         patch("openpilot.system.hardware.chestnut.status.time.monotonic", side_effect=(0.0, 11.0)):
      owner = ChestnutStatus()
      owner.update(offroad, branch, devices, firmware_failed, False, None, state,
                   lambda key, enabled, *extra: alerts.__setitem__(key, enabled))
    return alerts

  def test_present_device_has_no_removed_uncompiled_alert(self):
    alerts = self.check(compiled=True, devices=[DEVICE])
    self.assertFalse(alerts["Offroad_ChestnutBranch"])
    self.assertFalse(alerts["Offroad_ChestnutNotDetected"])
    self.assertNotIn("Offroad_ChestnutUncompiled", alerts)

  def test_removed_uncompiled_key_and_missing_hardware_warning(self):
    uncompiled = self.check(compiled=False, devices=[DEVICE])
    self.assertFalse(uncompiled["Offroad_ChestnutBranch"])
    self.assertNotIn("Offroad_ChestnutUncompiled", uncompiled)
    self.assertFalse(self.check(compiled=True, devices=[])["Offroad_ChestnutNotDetected"])
    self.assertTrue(self.check(compiled=False, devices=[], branch="release-chestnut")["Offroad_ChestnutNotDetected"])

  def test_observed_onroad_usb_loss_still_reports_missing(self):
    alerts = {}
    with nullcontext(), \
         patch("openpilot.system.hardware.chestnut.status.time.monotonic", return_value=0.0):
      owner = ChestnutStatus()
      def send(key, enabled, *extra):
        alerts[key] = enabled
      owner.update(False, "domathon", [DEVICE], False, False, None, None, send)
      self.assertFalse(alerts["Offroad_ChestnutNotDetected"])
      owner.update(False, "domathon", [], False, False, None, None, send)
    self.assertTrue(alerts["Offroad_ChestnutNotDetected"])

  def test_slow_usb_overheat_and_firmware_failure_are_independent(self):
    slow = {**DEVICE, "speedMbps": 480}
    hot = SimpleNamespace(tempC=102.0, memoryTempC=90.0)
    alerts = self.check(compiled=True, devices=[slow], firmware_failed=True, state=hot)
    self.assertFalse(alerts["Offroad_ChestnutBranch"])
    self.assertTrue(alerts["Offroad_ChestnutOverheated"])
    self.assertTrue(alerts["Offroad_ChestnutUsbSlow"])
    self.assertTrue(alerts["Offroad_ChestnutUpdateFailed"])

  def test_model_error_requires_completed_attempt_and_survives_offroad(self):
    alerts = {}
    with nullcontext():
      owner = ChestnutStatus()
      def update(offroad=False, loading=False, active=None):
        owner.update(offroad, "domathon", [DEVICE], False, loading, active, None,
                     lambda key, enabled, *extra: alerts.__setitem__(key, enabled))
        return alerts["Offroad_ChestnutModelError"]

      self.assertFalse(update(active=False))
      self.assertFalse(update(loading=True))
      self.assertFalse(update())
      self.assertFalse(update(active=True))
      self.assertTrue(update(active=False))
      self.assertTrue(update(offroad=True))
      self.assertFalse(update(loading=True))
      self.assertFalse(update(active=True))

  def test_initial_model_load_failure_is_reported(self):
    alerts = {}
    with nullcontext():
      owner = ChestnutStatus()
      for loading, active in ((True, None), (False, False)):
        owner.update(False, "domathon", [DEVICE], False, loading, active, None,
                     lambda key, enabled, *extra: alerts.__setitem__(key, enabled))
      self.assertTrue(alerts["Offroad_ChestnutModelError"])
    self.assertFalse(self.check(compiled=True, devices=[])["Offroad_ChestnutModelError"])

  def test_physical_fault_alert_takes_precedence_over_model_failure(self):
    for failure in ("usb", "power", "link"):
      with self.subTest(failure=failure), \
           nullcontext():
        alerts = {}
        state = SimpleNamespace(supplyVoltage=12000, supplyFault=False, pcieLtssm=0x78, tempC=40., memoryTempC=40.)
        owner = ChestnutStatus()
        def update(devices, loading, active, *, owner=owner, state=state, alerts=alerts):
          owner.update(False, "domathon", devices, False, loading, active, state,
                       lambda key, enabled, *extra: alerts.__setitem__(key, enabled))
        update([DEVICE], True, None)
        update([DEVICE], False, False)
        self.assertTrue(alerts["Offroad_ChestnutModelError"])
        if failure == "power":
          state.supplyFault = True
        elif failure == "link":
          state.pcieLtssm = 0
        for _ in range(2):
          update([] if failure == "usb" else [DEVICE], False, False)
        self.assertFalse(alerts["Offroad_ChestnutModelError"])
        self.assertTrue(alerts["Offroad_ChestnutNotDetected"] if failure == "usb" else alerts["Offroad_ChestnutPcieUnavailable"])


if __name__ == "__main__":
  unittest.main()
