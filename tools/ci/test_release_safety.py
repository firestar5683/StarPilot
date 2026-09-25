"""Explicit release hook-registry contract; run through run_vehicle_tests.py."""
import unittest

from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py

RELEASE_MODES = frozenset({
  "silent", "hondaNidec", "toyota", "elm327", "gm", "hondaBosch", "hyundai", "chrysler", "subaru", "volkswagen",
  "volkswagenMeb", "nissan", "noOutput", "hyundaiLegacy", "mazda", "body", "ford", "rivian", "tesla", "hyundaiCanfd", "teslaPreap",
})


def registry_test(name, value):
  def test(self):
    self.assertEqual(libsafety_py.libsafety.set_safety_hooks(value, 0) == 0, name in RELEASE_MODES, name)
  return test


class TestReleaseRegistry(unittest.TestCase):
  pass


class TestReleaseAxisCapabilities(unittest.TestCase):
  def test_experimental_hyundai_longitudinal_payloads_remain_closed_in_release(self):
    safety = libsafety_py.libsafety
    # Exact whole-controller SCC11, ADRV and FCA samples; generic steering
    # and tester-present overlap are deliberately outside this assertion.
    packets = (
      (0x420, 0, "49005dedaa470600"),
      (0x420, 1, "620009ecaa470600"),
      (0x51, 0, "00" * 32),
      (0x38D, 1, "8d000000c03f7f00"),
      (0x7D0, 0, "0328030100000000"),
      (0x730, 1, "0328030100000000"),
    )
    for param in (0x2004, 0x2014):
      self.assertEqual(safety.set_safety_hooks(CarParams.SafetyModel.hyundai, param), 0)
      safety.init_tests()
      safety.set_controls_allowed(True)
      for address, bus, payload in packets:
        with self.subTest(safety_param=param, address=hex(address), bus=bus):
          packet = libsafety_py.make_CANPacket(address, bus, bytes.fromhex(payload))
          self.assertFalse(safety.safety_tx_hook(packet))

  def test_honda_debug_only_longitudinal_cannot_grant_aol_in_release(self):
    safety = libsafety_py.libsafety
    for param in (0, 2, 32, 34, 42, 50):
      with self.subTest(safety_param=param):
        self.assertEqual(safety.set_safety_hooks(CarParams.SafetyModel.hondaBosch, param), 0)
        safety.init_tests()
        safety.set_controls_allowed(True)
        safety.set_aol_test_heartbeat(True)
        safety.aol_set_host_request(3)
        self.assertEqual(safety.aol_get_request_mask(), 0)
        self.assertEqual(safety.aol_get_permission_mask(), 0)


for mode_name, mode_value in CarParams.SafetyModel.schema.enumerants.items():
  setattr(TestReleaseRegistry, f"test_release_registry_{mode_name}", registry_test(mode_name, mode_value))
