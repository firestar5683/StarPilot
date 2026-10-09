import unittest

from opendbc.car.structs import CarParams
from opendbc.car.tesla.values import TeslaSafetyFlags
from opendbc.safety import ALTERNATIVE_EXPERIENCE
from opendbc.safety.tests.common import CANPackerSafety, make_msg
from opendbc.safety.tests import test_tesla


class TestTeslaScreenButton(unittest.TestCase):
  TX_MSGS = None

  def setUp(self):
    self.helper = test_tesla.TestTeslaStockSafety()
    self.helper.setUp()
    self.safety = self.helper.safety
    self.vehicle_packer = CANPackerSafety("tesla_model3_vehicle")
    self.init_safety()

  def init_safety(self, flag=True, aol=True, long_control=False, disengage_on_brake=False):
    param = (TeslaSafetyFlags.AOL_SCREEN_BUTTON if flag else 0) | (TeslaSafetyFlags.LONG_CONTROL if long_control else 0)
    if disengage_on_brake:
      param |= TeslaSafetyFlags.AOL_SCREEN_DISENGAGE_ON_BRAKE
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.tesla, param), 0)
    self.safety.init_tests()
    self.safety.set_alternative_experience(ALTERNATIVE_EXPERIENCE.ALWAYS_ON_LATERAL if aol else 0)
    self.helper._rx(self.helper._pcm_status_msg(False))
    self.safety.set_angle_meas(0, 0)
    self.safety.set_desired_angle_last(0)

  def touch(self, fingers, bus=1):
    self.helper._rx(self.vehicle_packer.make_can_msg_safety("UI_status2", bus, {"UI_activeTouchPoints": fingers}))

  def gesture(self):
    self.touch(0)
    self.touch(3)

  def test_gesture_enables_only_lateral(self):
    self.assertFalse(self.helper._tx(self.helper._angle_cmd_msg(0)))
    self.gesture()
    self.assertTrue(self.safety.get_aol_allowed())
    self.assertTrue(self.safety.get_lkas_on())
    self.assertFalse(self.safety.get_controls_allowed())
    self.assertTrue(self.helper._tx(self.helper._angle_cmd_msg(0)))
    self.assertFalse(self.helper._tx(self.helper._long_control_msg(10, acc_state=2, accel_limits=(0, 1))))
    self.gesture()
    self.assertFalse(self.safety.get_aol_allowed())
    self.assertFalse(self.helper._tx(self.helper._angle_cmd_msg(0)))

  def test_does_not_enable_alpha_long_actuation(self):
    self.init_safety(long_control=True)
    self.gesture()
    self.assertTrue(self.safety.get_aol_allowed())
    self.assertFalse(self.safety.get_controls_allowed())
    self.assertFalse(self.helper._tx(self.helper._long_control_msg(10, acc_state=2, accel_limits=(0, 1))))

  def test_flag_and_aol_are_required(self):
    for flag, aol in ((False, False), (False, True), (True, False)):
      with self.subTest(flag=flag, aol=aol):
        self.init_safety(flag=flag, aol=aol)
        self.gesture()
        self.assertFalse(self.safety.get_aol_allowed())
        self.assertFalse(self.helper._tx(self.helper._angle_cmd_msg(0)))

  def test_wrong_bus_and_length_do_not_toggle(self):
    for bus in (0, 2, 3):
      self.gesture_on_wrong_bus(bus)
      self.assertFalse(self.safety.get_lkas_on())
    self.touch(0)
    for length in (0, 3, 4, 5, 6, 7):
      msg = make_msg(1, 0x3DF, length)
      if length > 3:
        msg[0].data[3] = 3
      self.helper._rx(msg)
      self.assertFalse(self.safety.get_lkas_on())

  def gesture_on_wrong_bus(self, bus):
    self.touch(0, bus)
    self.touch(3, bus)

  def test_held_touch_and_other_finger_counts(self):
    for fingers in (3, 3, 0, 1, 2, 4, 5, 255, 0):
      self.touch(fingers)
      self.assertFalse(self.safety.get_lkas_on())
    self.touch(3)
    for _ in range(20):
      self.touch(3)
      self.assertTrue(self.safety.get_lkas_on())
    self.touch(0)
    self.touch(3)
    self.assertFalse(self.safety.get_lkas_on())

  def test_brake_disables_long_but_not_gesture_lateral(self):
    self.gesture()
    self.helper._rx(self.helper._user_brake_msg(True))
    self.assertTrue(self.safety.get_aol_allowed())
    self.assertFalse(self.safety.get_controls_allowed())
    self.assertTrue(self.helper._tx(self.helper._angle_cmd_msg(0)))

  def test_opt_in_brake_disengage_needs_brake_release_and_new_gesture(self):
    self.init_safety(disengage_on_brake=True)
    self.gesture()
    self.helper._rx(self.helper._user_brake_msg(True))
    self.assertFalse(self.safety.get_aol_allowed())
    self.gesture()
    self.assertFalse(self.safety.get_aol_allowed())
    self.helper._rx(self.helper._user_brake_msg(False))
    self.assertFalse(self.safety.get_aol_allowed())
    self.gesture()
    self.assertTrue(self.safety.get_aol_allowed())

  def test_steering_override_requires_a_new_gesture(self):
    self.gesture()
    self.helper._rx(self.helper._angle_meas_msg(0, hands_on_level=3))
    self.assertFalse(self.safety.get_aol_allowed())
    self.gesture()
    self.assertFalse(self.safety.get_aol_allowed())
    self.helper._rx(self.helper._angle_meas_msg(0))
    self.assertFalse(self.safety.get_aol_allowed())
    self.gesture()
    self.assertTrue(self.safety.get_aol_allowed())

  def test_cancelled_cruise_clears_gesture_latch(self):
    self.gesture()
    self.helper._rx(self.helper._pcm_status_msg(True))
    self.helper._rx(self.helper._pcm_status_msg(False))
    self.assertFalse(self.safety.get_aol_allowed())
    self.assertFalse(self.safety.get_lkas_on())

  def test_safety_reinitialization_clears_touch_latch(self):
    self.gesture()
    self.init_safety()
    self.touch(3)
    self.assertFalse(self.safety.get_aol_allowed())

  def test_stock_lkas_does_not_block_authorized_gesture_steering(self):
    self.gesture()
    self.helper._rx(self.helper._angle_cmd_msg(0, state=2, bus=2))
    self.assertTrue(self.helper._tx(self.helper._angle_cmd_msg(0)))

  def test_stock_lkas_still_blocks_when_not_authorized(self):
    self.helper._rx(self.helper._angle_cmd_msg(0, state=2, bus=2))
    self.gesture()
    self.assertFalse(self.helper._tx(self.helper._angle_cmd_msg(0)))

  def test_autopark_still_blocks_steering(self):
    self.helper._rx(self.helper._pcm_status_msg(False, autopark_state=3))
    self.gesture()
    self.assertFalse(self.helper._tx(self.helper._angle_cmd_msg(0)))

  def test_aeb_still_blocks_longitudinal_and_is_forwarded(self):
    self.init_safety(long_control=True)
    self.gesture()
    self.helper._rx(self.helper._long_control_msg(0, aeb_event=1, bus=2))
    self.assertFalse(self.helper._tx(self.helper._long_control_msg(0, acc_state=13)))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x2B9), 0)


if __name__ == "__main__":
  unittest.main()
