#!/usr/bin/env python3
import unittest

from opendbc.car.tesla.preap.interface import SAFETY_TESLA_PREAP
from opendbc.safety.tests.libsafety import libsafety_py
import opendbc.safety.tests.common as common


class TestTeslaPreAPSafety(common.SafetyTestBase):
  TX_MSGS = [[0x488, 0], [0x2B9, 0], [0x214, 0], [0x551, 0], [0x551, 2], [0x45, 0]]

  def setUp(self):
    self.safety = libsafety_py.libsafety
    self._set_mode(0)

  def _set_mode(self, param: int) -> None:
    self.safety.set_safety_hooks(SAFETY_TESLA_PREAP, param)
    self.safety.init_tests()

  @staticmethod
  def _gear_msg(gear: int = 4):
    dat = bytearray(6)
    dat[1] = (gear & 0x7) << 4
    return common.make_msg(0, 0x118, 6, dat)

  @staticmethod
  def _doors_msg(opened: bool):
    dat = bytearray(8)
    if opened:
      dat[1] = 0x10
    return common.make_msg(0, 0x318, 8, dat)

  @staticmethod
  def _stalk_msg(lever: int):
    dat = bytearray(8)
    dat[0] = lever & 0x3F
    return common.make_msg(0, 0x45, 8, dat)

  @staticmethod
  def _steering_status_msg(hands_on_level: int = 0, eac_status: int = 1, eac_error_code: int = 0, angle_tenths: int = 0):
    raw_angle = angle_tenths + 8192
    dat = bytearray(8)
    dat[2] = (eac_error_code & 0xF) << 4
    dat[4] = ((hands_on_level & 0x3) << 6) | ((raw_angle >> 8) & 0x3F)
    dat[5] = raw_angle & 0xFF
    dat[6] = (eac_status & 0x7) << 5
    return common.make_msg(0, 0x370, 8, dat)

  @staticmethod
  def _steer_cmd_msg(angle_tenths: int, steer_control_type: int = 1):
    raw_angle = angle_tenths + 16384
    dat = bytearray(4)
    dat[0] = (raw_angle >> 8) & 0x7F
    dat[1] = raw_angle & 0xFF
    dat[2] = (steer_control_type & 0x3) << 6
    return common.make_msg(0, 0x488, 4, dat)

  @staticmethod
  def _epas_control_msg(epas_control_type: int):
    dat = bytearray(3)
    dat[0] = epas_control_type & 0x7
    return common.make_msg(0, 0x214, 3, dat)

  @staticmethod
  def _long_msg(aeb_event: int = 0):
    dat = bytearray(8)
    dat[2] = aeb_event & 0x3
    return common.make_msg(0, 0x2B9, 8, dat)

  @staticmethod
  def _msg(addr: int, dat: bytes | bytearray = bytes(8), bus: int = 0):
    return common.make_msg(bus, addr, len(dat), bytearray(dat))

  @staticmethod
  def _pedal_cmd_msg(raw_cmd: int = 700, enable: bool = True, bus: int = 0):
    dat = bytearray(6)
    dat[0] = (raw_cmd >> 8) & 0xFF
    dat[1] = raw_cmd & 0xFF
    dat[4] = 0x80 if enable else 0x00
    return common.make_msg(bus, 0x551, 6, dat)

  def _prime_can_engage(self):
    self.assertTrue(self._rx(self._gear_msg(4)))
    self.assertTrue(self._rx(self._doors_msg(False)))

  def test_mode_param_round_trip(self):
    self._set_mode(1 | 2 | 4)
    self.assertEqual(self.safety.get_current_safety_mode(), 35)
    self.assertEqual(self.safety.get_current_safety_param(), 1 | 2 | 4)

  def test_stalk_engage_and_cancel(self):
    self._prime_can_engage()

    self.assertFalse(self.safety.get_controls_allowed())
    self.assertTrue(self._rx(self._stalk_msg(2)))
    self.assertTrue(self.safety.get_controls_allowed())

    self.safety.set_timer(700000)
    self.assertTrue(self._rx(self._stalk_msg(1)))
    self.assertFalse(self.safety.get_controls_allowed())

  def test_door_open_blocks_engagement(self):
    self.assertTrue(self._rx(self._gear_msg(4)))
    self.assertTrue(self._rx(self._doors_msg(True)))
    self.assertTrue(self._rx(self._stalk_msg(2)))
    self.assertFalse(self.safety.get_controls_allowed())

  def test_steering_disengage_drops_controls(self):
    self._prime_can_engage()
    self.assertTrue(self._rx(self._stalk_msg(2)))
    self.assertTrue(self.safety.get_controls_allowed())

    self.assertTrue(self._rx(self._steering_status_msg(hands_on_level=3)))
    self.assertFalse(self.safety.get_controls_allowed())
    self.assertTrue(self.safety.get_steering_disengage_prev())

  def test_steering_tx_limits(self):
    self.safety.set_controls_allowed(True)

    self.assertTrue(self._tx(self._steer_cmd_msg(0, 1)))
    self.assertFalse(self._tx(self._steer_cmd_msg(0, 2)))
    self.assertFalse(self._tx(self._steer_cmd_msg(4000, 1)))
    self.assertTrue(self._tx(self._epas_control_msg(1)))
    self.assertFalse(self._tx(self._epas_control_msg(2)))

  def test_aeb_is_blocked(self):
    self.safety.set_controls_allowed(True)
    self.assertTrue(self._tx(self._long_msg(0)))
    self.assertFalse(self._tx(self._long_msg(1)))

  def test_pedal_tx_requires_pedal_flag_and_longitudinal_allowed(self):
    self.safety.set_controls_allowed(True)
    self.assertFalse(self._tx(self._pedal_cmd_msg()))

    self._set_mode(1)
    self.safety.set_controls_allowed(False)
    self.assertFalse(self._tx(self._pedal_cmd_msg()))

    self.safety.set_controls_allowed(True)
    self.assertTrue(self._tx(self._pedal_cmd_msg()))
    self.assertTrue(self._tx(self._pedal_cmd_msg(raw_cmd=0, enable=False)))
    self.assertFalse(self._tx(self._pedal_cmd_msg(raw_cmd=501, enable=False)))

  def test_rx_state_paths(self):
    self.safety.set_controls_allowed(True)
    self.assertTrue(self._rx(self._msg(0x155, b"\x00\x00\x00\x00\x00\x00\x64\x00")))
    self.assertTrue(self.safety.get_vehicle_moving())
    self.assertTrue(self._rx(self._msg(0x368, b"\x00\x30\x00\x00\x00\x00\x00\x00")))
    self.assertFalse(self.safety.get_vehicle_moving())

    self.assertTrue(self._rx(self._msg(0x108, b"\x00\x00\x00\x00\x00\x00\x01\x00")))
    self.assertTrue(self.safety.get_gas_pressed_prev())
    self.assertTrue(self._rx(self._msg(0x20A)))
    self.assertFalse(self.safety.get_brake_pressed_prev())

    self.assertTrue(self._rx(self._steering_status_msg(eac_status=0, eac_error_code=6)))
    self.assertTrue(self.safety.get_steering_disengage_prev())

    self.safety.set_controls_allowed(True)
    self.assertTrue(self._rx(self._gear_msg(3)))
    self.assertFalse(self.safety.get_controls_allowed())

  def test_all_door_sources_disengage(self):
    for index, mask in ((1, 0x10), (1, 0x40), (2, 0x40), (3, 0x20), (6, 0x04), (5, 0x40)):
      self._set_mode(0)
      self.safety.set_controls_allowed(True)
      dat = bytearray(8)
      dat[index] = mask
      self.assertTrue(self._rx(self._msg(0x318, dat)))
      self.assertFalse(self.safety.get_controls_allowed())

  def test_stalk_cancel_echo_window(self):
    self._prime_can_engage()
    self.safety.set_timer(100000)
    self.assertTrue(self._rx(self._stalk_msg(2)))
    self.safety.set_timer(200000)
    self.assertTrue(self._rx(self._stalk_msg(1)))
    self.assertTrue(self.safety.get_controls_allowed())

  def test_pedal_rx_sources(self):
    self._set_mode(1)
    self.assertTrue(self._rx(self._msg(0x552, b"\x02\x8b\x00\x00\x00\x00")))
    self.assertTrue(self.safety.get_gas_pressed_prev())
    self._set_mode(1)
    self.assertTrue(self._rx(self._msg(0x552, b"\x00\x00\x00\x00\x00\x00", bus=2)))
    self.assertFalse(self.safety.get_gas_pressed_prev())

  def test_radar_emulation_input_paths(self):
    self._set_mode(2 | 4)
    for addr in (0x45, 0x108, 0x145, 0x20A, 0x308, 0x30A, 0x405):
      self.assertTrue(self._rx(self._msg(addr)))

    self.assertTrue(self._rx(self._msg(0x398, b"\x00\x00\x00\x00\x00\x00\x00\x00")))
    self.assertTrue(self._rx(self._msg(0x0E, b"\x00\x00\x3f\xff\x00\x00\x00\x00")))
    self.assertTrue(self._rx(self._msg(0x0E)))
    self.assertTrue(self._rx(self._msg(0x115, b"\x00\x00\x00\x00\xa0\x00\x00\x00")))
    self.assertTrue(self._rx(self._msg(0x118, b"\x00\x00\xff\x0f\x01\x00")))
    self.assertTrue(self._rx(self._msg(0x118, b"\x00\x00\x01\x00\x01\x00")))
    self.assertTrue(self._rx(self._msg(0x118, b"\x00\x00\x20\x03\x02\x00")))

  def test_forwarding_passthrough(self):
    self.assertEqual(self.safety.safety_fwd_hook(0, 0x123), 2)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x123), 0)


if __name__ == "__main__":
  unittest.main()
