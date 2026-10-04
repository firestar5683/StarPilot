import unittest

from opendbc.car import structs
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests.test_honda import TestHondaBoschLongSafety, Btn


class TestHondaAolSourceBinding(unittest.TestCase):
  def test_wrong_bus_or_short_main_cannot_refresh_permission(self):
    for param in (34, 35):
      for kind in ("wrong_bus", "short"):
        with self.subTest(param=param, kind=kind):
          fixture = TestHondaBoschLongSafety("test_diagnostics")
          fixture.setUp()
          safety = fixture.safety
          if safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0:
            self.skipTest("DEBUG classic Bosch owner")
          safety.set_safety_hooks(structs.CarParams.SafetyModel.hondaBosch, param)
          safety.init_tests()
          safety.set_timer(1_000_000)
          safety.set_aol_test_heartbeat(True)
          fixture._rx(fixture._acc_state_msg(True))
          fixture._rx(fixture._button_msg(Btn.NONE))
          fixture._rx(fixture._speed_msg(20))
          fixture._rx(fixture._powertrain_data_msg())
          if param == 35:
            fixture._rx(fixture._alt_brake_msg(0))
          safety.aol_set_host_request(1)
          self.assertEqual(safety.aol_get_permission_mask(), 1)
          safety.set_timer(1_250_000)
          message = fixture._acc_state_msg(True)
          if kind == "wrong_bus":
            message[0].bus = 0
          else:
            message = libsafety_py.make_CANPacket(0x326, 1, bytes(message[0].data[0:7]))
          safety.safety_rx_hook(message)
          safety.set_timer(1_300_001)
          fixture._rx(fixture._button_msg(Btn.NONE))
          fixture._rx(fixture._speed_msg(20))
          fixture._rx(fixture._powertrain_data_msg())
          if param == 35:
            fixture._rx(fixture._alt_brake_msg(0))
          safety.aol_set_host_request(1)
          self.assertEqual(safety.aol_get_permission_mask(), 0)

  def test_unselected_main_source_cannot_clear_actual_main(self):
    fixture = TestHondaBoschLongSafety("test_diagnostics")
    fixture.setUp()
    safety = fixture.safety
    if safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0:
      self.skipTest("DEBUG classic Bosch owner")
    safety.set_safety_hooks(structs.CarParams.SafetyModel.hondaBosch, 34)
    safety.init_tests()
    safety.set_timer(1_000_000)
    safety.set_aol_test_heartbeat(True)
    fixture._rx(fixture._acc_state_msg(True))
    fixture._rx(fixture._button_msg(Btn.NONE))
    fixture._rx(fixture._speed_msg(20))
    fixture._rx(fixture._powertrain_data_msg())
    safety.aol_set_host_request(1)
    self.assertEqual(safety.aol_get_permission_mask(), 1)
    message = libsafety_py.make_CANPacket(0x1A6, 1, bytes(8))
    safety.safety_rx_hook(message)
    self.assertEqual(safety.aol_get_permission_mask(), 1)
