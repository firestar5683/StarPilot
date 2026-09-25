import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.hyundai.values import DBC
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests.test_hyundai_ioniq6_long import params


class TestHyundaiIoniq6StockAol(unittest.TestCase):
  def mode(self, raw):
    self.safety = libsafety_py.libsafety
    self.assertEqual(self.safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundaiCanfd, raw), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)
    self.packer = CANPacker(DBC[params("lkas_alt" if raw & 0x80 else "lkas")[0].carFingerprint][Bus.pt])
    self.steer = "LKAS_ALT" if raw & 0x80 else "LKAS"
    self.counters = {}

  def packet(self, name, bus, values):
    frame = self.packer.make_can_msg(name, bus, values)
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def rx(self, name, values=None):
    self.counters[name] = self.counters.get(name, 0) + 1
    self.assertTrue(self.safety.safety_rx_hook(self.packet(name, 1, {
      "COUNTER": self.counters[name] % (16 if name == "CRUISE_BUTTONS" else 256), **(values or {})})), name)

  def healthy(self, acc=False):
    for name, values in (("ACCELERATOR", {"GEAR": 5}), ("TCS", {}), ("WHEEL_SPEEDS", {}),
                         ("MDPS", {}), ("CRUISE_BUTTONS", {}), ("SCC_CONTROL", {"ACCMode": int(acc)})):
      self.rx(name, values)

  def tx(self, torque, request):
    frame = self.packer.make_can_msg(self.steer, 0, {"StrTqReqVal": torque, "ActToiSta": request})
    data = frame[1]
    self.assertEqual((((data[6] & 0xF) << 7) | (data[5] >> 1)) - 1024, torque)
    self.assertEqual((data[6] >> 4) & 1, request)
    return self.safety.safety_tx_hook(libsafety_py.make_CANPacket(frame[0], frame[2], data))

  def arm(self):
    self.rx("CRUISE_BUTTONS", {"LDA_BTN": 1})
    self.rx("CRUISE_BUTTONS", {})
    self.safety.set_aol_test_heartbeat(True)
    self.safety.aol_set_host_request(3)

  def test_stock_scc_and_physical_gesture_share_request_gate(self):
    for raw in (0x811, 0x891):
      with self.subTest(raw=raw):
        self.mode(raw)
        self.healthy()
        self.safety.set_aol_test_heartbeat(True)
        self.safety.aol_set_host_request(3)
        self.assertFalse(self.safety.get_controls_allowed())
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)
        self.assertFalse(self.tx(1, 1))
        self.arm()
        self.assertEqual(self.safety.aol_get_permission_mask(), 1)
        self.assertTrue(self.tx(1, 1))
        self.safety.aol_set_host_request(0)
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)
        self.assertFalse(self.tx(1, 1))
        self.assertTrue(self.tx(0, 0))
        self.safety.aol_set_host_request(3)
        # LDA authorizes lateral AOL, but is deliberately not a stock ACC
        # enable-button interaction in hyundai_common_cruise_buttons_check.
        self.rx("SCC_CONTROL", {"ACCMode": 1})
        self.assertFalse(self.safety.get_controls_allowed())
        self.rx("SCC_CONTROL", {"ACCMode": 0})
        self.rx("CRUISE_BUTTONS", {"CRUISE_BUTTONS": 2})  # physical SET
        self.rx("SCC_CONTROL", {"ACCMode": 1})
        self.assertTrue(self.safety.get_controls_allowed())
        self.assertEqual(self.safety.aol_get_permission_mask(), 1)
        self.rx("SCC_CONTROL", {"ACCMode": 0})
        self.assertFalse(self.safety.get_controls_allowed())
        self.assertEqual(self.safety.aol_get_permission_mask(), 1)
        for name, bus, values in (("SCC_CONTROL", 1, {"ACCMode": 1, "aReqRaw": 1, "aReqValue": 1}),
                                  ("LFA", 1, {"StrTqReqVal": 1, "ActToiSta": 1})):
          self.assertFalse(self.safety.safety_tx_hook(self.packet(name, bus, values)))
        self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x730, 1, b"\x02\x3e\x80\0\0\0\0\0")))

  def test_cancel_heartbeat_expiry_and_reset_revoke_latch(self):
    for raw in (0x811, 0x891):
      for cause in ("cancel", "heartbeat", "expiry", "reset", "relay"):
        with self.subTest(raw=raw, cause=cause):
          self.mode(raw)
          self.healthy()
          self.arm()
          self.assertEqual(self.safety.aol_get_permission_mask(), 1)
          if cause == "cancel":
            self.rx("CRUISE_BUTTONS", {"CRUISE_BUTTONS": 4})
          elif cause == "heartbeat":
            self.safety.set_aol_test_heartbeat(False)
          elif cause == "expiry":
            self.safety.set_timer(1_600_001)
          elif cause == "relay":
            self.safety.set_relay_malfunction(True)
          else:
            self.mode(raw)
          self.assertEqual(self.safety.aol_get_permission_mask(), 0)
          self.assertFalse(self.tx(1, 1))


if __name__ == "__main__":
  unittest.main()
