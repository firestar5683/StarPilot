#!/usr/bin/env python3
import unittest

from opendbc.car.gm.values import GMSafetyFlags
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py
import opendbc.safety.tests.common as common
from opendbc.safety.tests.common import CANPackerSafety, CANPackerPanda


class Buttons:
  UNPRESS = 1
  RES_ACCEL = 2
  DECEL_SET = 3
  CANCEL = 6


def test_gm_starpilot_safety_flag_combinations():
  safety = libsafety_py.libsafety
  combinations = (
    GMSafetyFlags.HW_SDGM | GMSafetyFlags.FLAG_GM_NO_CAMERA | GMSafetyFlags.FLAG_GM_PANDA_PADDLE_SCHED,
    GMSafetyFlags.HW_CAM | GMSafetyFlags.FLAG_GM_NO_CAMERA | GMSafetyFlags.FLAG_GM_PANDA_PADDLE_SCHED,
    GMSafetyFlags.HW_CAM | GMSafetyFlags.FLAG_GM_NO_CAMERA | GMSafetyFlags.FLAG_GM_NO_ACC |
      GMSafetyFlags.FLAG_GM_PEDAL_LONG | GMSafetyFlags.FLAG_GM_GAS_INTERCEPTOR |
      GMSafetyFlags.FLAG_GM_BOLT_2022_PEDAL | GMSafetyFlags.FLAG_GM_PANDA_PADDLE_SCHED,
    GMSafetyFlags.HW_CAM | GMSafetyFlags.FLAG_GM_GAS_INTERCEPTOR,
  )
  for flags in combinations:
    assert safety.set_safety_hooks(CarParams.SafetyModel.gm, flags) == 0
    safety.init_tests()


def test_gm_panda_scheduler_paths():
  safety = libsafety_py.libsafety
  flags = (GMSafetyFlags.HW_CAM | GMSafetyFlags.FLAG_GM_NO_ACC | GMSafetyFlags.FLAG_GM_CC_LONG |
           GMSafetyFlags.FLAG_GM_PEDAL_LONG | GMSafetyFlags.FLAG_GM_GAS_INTERCEPTOR |
           GMSafetyFlags.FLAG_GM_PANDA_3D1_SCHED | GMSafetyFlags.FLAG_GM_PANDA_PADDLE_SCHED)
  assert safety.set_safety_hooks(CarParams.SafetyModel.gm, flags) == 0
  safety.init_tests()
  safety.set_controls_allowed(True)

  paddle = common.make_msg(0, 0xBD, 7, bytes([0x20, 0, 0, 0, 0, 0, 0]))
  prndl = common.make_msg(0, 0x1F5, 8, bytes([0, 0, 0, 7, 0, 0, 0, 0]))
  cruise = common.make_msg(0, 0x3D1, 8)

  safety.set_timer(100000)
  safety.safety_tx_hook(paddle)
  safety.safety_tx_hook(prndl)
  safety.safety_tx_hook(cruise)
  safety.safety_rx_hook(paddle)
  safety.safety_rx_hook(prndl)
  safety.safety_rx_hook(cruise)

  safety.set_timer(125000)
  safety.safety_rx_hook(paddle)
  safety.safety_rx_hook(prndl)
  safety.set_timer(300000)
  safety.safety_rx_hook(paddle)
  safety.safety_rx_hook(prndl)


def test_gm_bolt_acc_pedal_clears_stock_cruise():
  safety = libsafety_py.libsafety
  flags = GMSafetyFlags.HW_CAM | GMSafetyFlags.FLAG_GM_GAS_INTERCEPTOR | GMSafetyFlags.FLAG_GM_BOLT_2022_PEDAL
  assert safety.set_safety_hooks(CarParams.SafetyModel.gm, flags) == 0
  safety.init_tests()
  safety.set_cruise_engaged_prev(True)
  assert safety.safety_rx_hook(libsafety_py.make_CANPacket(0x1C4, 0, bytes(8)))
  assert not safety.get_cruise_engaged_prev()


class GmLongitudinalBase(common.CarSafetyTest, common.LongitudinalGasBrakeSafetyTest):

  RELAY_MALFUNCTION_ADDRS = {0: (0x180, 0x2CB), 2: (0x184,)}  # ASCMLKASteeringCmd, ASCMGasRegenCmd, PSCMStatus

  MAX_POSSIBLE_BRAKE = 2 ** 12
  MAX_BRAKE = 400

  MAX_POSSIBLE_GAS = 4000  # reasonably excessive limits, not signal max
  MIN_POSSIBLE_GAS = -4000

  PCM_CRUISE = False  # openpilot can control the PCM state if longitudinal

  def _send_brake_msg(self, brake):
    values = {"FrictionBrakeCmd": -brake}
    return self.packer_chassis.make_can_msg_safety("EBCMFrictionBrakeCmd", self.BRAKE_BUS, values)

  def _send_gas_msg(self, gas):
    values = {"GasRegenCmd": gas}
    return self.packer.make_can_msg_safety("ASCMGasRegenCmd", 0, values)

  # override these tests from CarSafetyTest, GM longitudinal uses button enable
  def _pcm_status_msg(self, enable):
    raise NotImplementedError

  def test_disable_control_allowed_from_cruise(self):
    pass

  def test_enable_control_allowed_from_cruise(self):
    pass

  def test_cruise_engaged_prev(self):
    pass

  def test_set_resume_buttons(self):
    """
      SET and RESUME enter controls allowed on their falling and rising edges, respectively.
    """
    for btn_prev in range(8):
      for btn_cur in range(8):
        with self.subTest(btn_prev=btn_prev, btn_cur=btn_cur):
          self._rx(self._button_msg(btn_prev))
          self.safety.set_controls_allowed(0)
          for _ in range(10):
            self._rx(self._button_msg(btn_cur))

          should_enable = btn_cur != Buttons.DECEL_SET and btn_prev == Buttons.DECEL_SET
          should_enable = should_enable or (btn_cur == Buttons.RES_ACCEL and btn_prev != Buttons.RES_ACCEL)
          should_enable = should_enable and btn_cur != Buttons.CANCEL
          self.assertEqual(should_enable, self.safety.get_controls_allowed())

  def test_cancel_button(self):
    self.safety.set_controls_allowed(1)
    self._rx(self._button_msg(Buttons.CANCEL))
    self.assertFalse(self.safety.get_controls_allowed())


class TestGmSafetyBase(common.CarSafetyTest, common.DriverTorqueSteeringSafetyTest):
  STANDSTILL_THRESHOLD = 10 * 0.0311
  # Ensures ASCM is off on ASCM cars, and relay is not malfunctioning for camera-ACC cars
  RELAY_MALFUNCTION_ADDRS = {0: (0x180,), 2: (0x184,)}  # ASCMLKASteeringCmd, PSCMStatus
  BUTTONS_BUS = 0  # rx or tx
  BRAKE_BUS = 0  # tx only

  MAX_RATE_UP = 10
  MAX_RATE_DOWN = 15
  MAX_TORQUE_LOOKUP = [0], [300]
  MAX_RT_DELTA = 128
  DRIVER_TORQUE_ALLOWANCE = 65
  DRIVER_TORQUE_FACTOR = 4

  PCM_CRUISE = True  # openpilot is tied to the PCM state if not longitudinal

  EXTRA_SAFETY_PARAM = 0

  def setUp(self):
    self.packer = CANPackerSafety("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerSafety("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.gm, 0)
    self.safety.init_tests()

  def _pcm_status_msg(self, enable):
    if self.PCM_CRUISE:
      values = {"CruiseState": enable}
      return self.packer.make_can_msg_safety("AcceleratorPedal2", 0, values)
    else:
      raise NotImplementedError

  def _speed_msg(self, speed):
    values = {"%sWheelSpd" % s: speed for s in ["RL", "RR"]}
    return self.packer.make_can_msg_safety("EBCMWheelSpdRear", 0, values)

  def _user_brake_msg(self, brake):
    # GM safety has a brake threshold of 8
    values = {"BrakePedalPos": 8 if brake else 0}
    return self.packer.make_can_msg_safety("ECMAcceleratorPos", 0, values)

  def _user_gas_msg(self, gas):
    values = {"AcceleratorPedal2": 1 if gas else 0}
    if self.PCM_CRUISE:
      # Fill CruiseState with expected value if the safety mode reads cruise state from gas msg
      values["CruiseState"] = self.safety.get_controls_allowed()
    return self.packer.make_can_msg_safety("AcceleratorPedal2", 0, values)

  def _torque_driver_msg(self, torque):
    # Safety tests assume driver torque is an int, use DBC factor
    values = {"LKADriverAppldTrq": torque * 0.01}
    return self.packer.make_can_msg_safety("PSCMStatus", 0, values)

  def _torque_cmd_msg(self, torque, steer_req=1):
    values = {"LKASteeringCmd": torque, "LKASteeringCmdActive": steer_req}
    return self.packer.make_can_msg_safety("ASCMLKASteeringCmd", 0, values)

  def _button_msg(self, buttons):
    values = {"ACCButtons": buttons}
    return self.packer.make_can_msg_safety("ASCMSteeringButton", self.BUTTONS_BUS, values)

  def _toggle_aol(self, toggle_on):
    # ECMEngineStatus, bit 29 is CruiseMainOn
    values = {"CruiseMainOn": 1 if toggle_on else 0}
    return self.packer.make_can_msg_panda("ECMEngineStatus", 0, values)


class TestGmEVSafetyBase(TestGmSafetyBase):
  EXTRA_SAFETY_PARAM = 0

  # existence of _user_regen_msg adds regen tests
  def _user_regen_msg(self, regen):
    values = {"RegenPaddle": 2 if regen else 0}
    return self.packer.make_can_msg_safety("EBCMRegenPaddle", 0, values)


class GmCameraAccEVRegenMixin:
  # Camera-ACC EV modes currently track regen paddle state and treat regen
  # input as a user-override path that drops controls.
  def test_prev_user_regen(self):
    self.assertFalse(self.safety.get_regen_braking_prev())
    for pressed in (False, True, False):
      self._rx(self._user_regen_msg(pressed))
      self.assertEqual(pressed, self.safety.get_regen_braking_prev())

  def test_allow_user_regen_at_zero_speed(self):
    self._rx(self._vehicle_moving_msg(0))
    self.safety.set_controls_allowed(True)
    self._rx(self._user_regen_msg(True))
    self.assertFalse(self.safety.get_controls_allowed())
    self.assertFalse(self.safety.get_longitudinal_allowed())
    self.assertTrue(self.safety.get_regen_braking_prev())

  def test_not_allow_user_regen_when_moving(self):
    self._rx(self._vehicle_moving_msg(self.STANDSTILL_THRESHOLD + 1))
    self.safety.set_controls_allowed(True)
    self._rx(self._user_regen_msg(True))
    self.assertFalse(self.safety.get_controls_allowed())
    self.assertFalse(self.safety.get_longitudinal_allowed())
    self.assertTrue(self.safety.get_regen_braking_prev())
    self._rx(self._vehicle_moving_msg(0))


class TestGmAscmSafety(GmLongitudinalBase, TestGmSafetyBase):
  TX_MSGS = [[0x180, 0], [0x409, 0], [0x40A, 0], [0x2CB, 0], [0x370, 0], [0x200, 0], [0x1E1, 0], [0xBD, 0], [0x1F5, 0],  # pt bus
             [0xA1, 1], [0x306, 1], [0x308, 1], [0x310, 1],  # obs bus
             [0x315, 2]]  # ch bus
  FWD_BLACKLISTED_ADDRS: dict[int, list[int]] = {}
  RELAY_MALFUNCTION_ADDRS = {0: (0x180, 0x2CB)}  # ASCMLKASteeringCmd, ASCMGasRegenCmd
  FWD_BUS_LOOKUP: dict[int, int] = {}
  BRAKE_BUS = 2

  MAX_GAS = 2041
  MIN_GAS = -650  # maximum regen
  INACTIVE_GAS = -650

  def setUp(self):
    self.packer = CANPackerSafety("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerSafety("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.gm, self.EXTRA_SAFETY_PARAM)
    self.safety.init_tests()


class TestGmAscmEVSafety(TestGmAscmSafety, TestGmEVSafetyBase):
  EXTRA_SAFETY_PARAM = GMSafetyFlags.FLAG_GM_NO_CAMERA
  TX_MSGS = [[0x180, 0], [0x409, 0], [0x40A, 0], [0x2CB, 0], [0x370, 0], [0x200, 0], [0x1E1, 0], [0xBD, 0], [0x1F5, 0], [0x315, 0],
             [0xA1, 1], [0x306, 1], [0x308, 1], [0x310, 1]]
  RELAY_MALFUNCTION_ADDRS = {0: (0x180, 0x2CB, 0x315)}
  BRAKE_BUS = 0

  def _user_brake_msg(self, brake):
    values = {"BrakePedalPosition": 6 if brake else 0}
    return self.packer.make_can_msg_panda("EBCMBrakePedalPosition", 0, values)


class TestGmCameraSafetyBase(TestGmSafetyBase):
  def _user_brake_msg(self, brake):
    values = {"BrakePressed": brake}
    return self.packer.make_can_msg_safety("ECMEngineStatus", 0, values)


class TestGmCameraSafety(TestGmCameraSafetyBase):
  TX_MSGS = [[0x180, 0], [0x370, 0], [0x200, 0], [0x1E1, 0], [0x3D1, 0], [0xBD, 0], [0x1F5, 0],  # pt bus
             [0x1E1, 2], [0x184, 2]]  # camera bus
  FWD_BLACKLISTED_ADDRS = {2: [0x180], 0: [0x184]}  # block LKAS message and PSCMStatus
  BUTTONS_BUS = 2  # tx only

  def setUp(self):
    self.packer = CANPackerSafety("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerSafety("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.gm, GMSafetyFlags.HW_CAM | self.EXTRA_SAFETY_PARAM)
    self.safety.init_tests()

  def test_buttons(self):
    # Only CANCEL button is allowed while cruise is enabled
    self.safety.set_controls_allowed(0)
    for btn in range(8):
      self.assertFalse(self._tx(self._button_msg(btn)))

    self.safety.set_controls_allowed(1)
    for btn in range(8):
      self.assertFalse(self._tx(self._button_msg(btn)))

    for enabled in (True, False):
      self._rx(self._pcm_status_msg(enabled))
      self.assertEqual(enabled, self._tx(self._button_msg(Buttons.CANCEL)))


class TestGmSdgmSafety(TestGmSafetyBase):
  TX_MSGS = [[0x180, 0], [0x370, 0], [0x200, 0], [0x1E1, 0], [0x3D1, 0], [0xBD, 0], [0x1F5, 0],  # pt bus
             [0x1E1, 2], [0x184, 2]]  # camera bus
  FWD_BLACKLISTED_ADDRS = {2: [0x180], 0: [0x184]}  # block LKAS message and PSCMStatus
  RELAY_MALFUNCTION_ADDRS = {0: (0x180,), 2: ()}
  BUTTONS_BUS = 2  # tx only

  def setUp(self):
    self.packer = CANPackerSafety("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerSafety("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.gm, GMSafetyFlags.HW_SDGM | self.EXTRA_SAFETY_PARAM)
    self.safety.init_tests()


def _prime_gm_base_rx_checks(safety, f1_bus: int) -> None:
  for bus, addr, length in (
    (0, 0x184, 8),
    (0, 0x34A, 5),
    (0, 0x1E1, 7),
    (f1_bus, 0xF1, 6),
    (0, 0x1C4, 8),
    (0, 0xC9, 8),
  ):
    safety.safety_rx_hook(common.make_msg(bus, addr, length))


def test_gm_camera_stock_acc_uses_base_rx_checks():
  safety = libsafety_py.libsafety
  safety.set_safety_hooks(CarParams.SafetyModel.gm, GMSafetyFlags.HW_CAM)
  safety.init_tests()

  _prime_gm_base_rx_checks(safety, 0)
  assert safety.safety_config_valid()


def _prime_gm_ascm_int_stock_cam_rx_checks(safety, f1_bus: int) -> None:
  # This path should only accept the Volt/Malibu ASCM_INT stock-camera status on bus 0.
  _prime_gm_base_rx_checks(safety, f1_bus)


def test_gm_ascm_int_stock_cam_f1_rx_pinning():
  safety = libsafety_py.libsafety
  safety.set_safety_hooks(CarParams.SafetyModel.gm, GMSafetyFlags.HW_CAM | GMSafetyFlags.HW_ASCM_INT)
  safety.init_tests()

  _prime_gm_ascm_int_stock_cam_rx_checks(safety, 0)
  assert safety.safety_config_valid()

  safety.set_safety_hooks(CarParams.SafetyModel.gm, GMSafetyFlags.HW_CAM | GMSafetyFlags.HW_ASCM_INT)
  safety.init_tests()

  _prime_gm_ascm_int_stock_cam_rx_checks(safety, 2)
  assert not safety.safety_config_valid()


def test_gm_ascm_int_long_no_accel_pos_uses_stock_cam_rx_checks():
  safety = libsafety_py.libsafety
  safety.set_safety_hooks(CarParams.SafetyModel.gm, GMSafetyFlags.HW_CAM | GMSafetyFlags.HW_CAM_LONG |
                          GMSafetyFlags.HW_ASCM_INT | GMSafetyFlags.FLAG_GM_FORCE_BRAKE_C9)
  safety.init_tests()

  _prime_gm_ascm_int_stock_cam_rx_checks(safety, 0)
  assert safety.safety_config_valid()


def test_ascm_int_camera_long_blocks_radar_status_tx():
  safety = libsafety_py.libsafety
  radar_status_msgs = (
    (0xA1, 7),
    (0x306, 8),
    (0x308, 7),
    (0x310, 2),
  )
  ascm_int_long = GMSafetyFlags.HW_CAM | GMSafetyFlags.HW_CAM_LONG | GMSafetyFlags.HW_ASCM_INT

  safety.set_safety_hooks(CarParams.SafetyModel.gm, ascm_int_long)
  safety.init_tests()
  for addr, length in radar_status_msgs:
    assert not safety.safety_tx_hook(common.make_msg(1, addr, length))

  volt_sdgm_long = GMSafetyFlags.HW_CAM | GMSafetyFlags.HW_CAM_LONG | GMSafetyFlags.HW_SDGM
  safety.set_safety_hooks(CarParams.SafetyModel.gm, volt_sdgm_long)
  safety.init_tests()
  for addr, length in radar_status_msgs:
    assert not safety.safety_tx_hook(common.make_msg(1, addr, length))


class TestGmCameraEVSafety(GmCameraAccEVRegenMixin, TestGmCameraSafety, TestGmEVSafetyBase):
  pass


class TestGmCameraNoCameraSafety(TestGmCameraSafety):
  TX_MSGS = TestGmCameraSafety.TX_MSGS + [[0x409, 0], [0x40A, 0]]
  RELAY_MALFUNCTION_ADDRS = {0: (), 2: ()}

  def setUp(self):
    self.packer = CANPackerSafety("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerSafety("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.gm, GMSafetyFlags.HW_CAM | GMSafetyFlags.FLAG_GM_NO_CAMERA)
    self.safety.init_tests()


class TestGmCameraLongitudinalSafety(GmLongitudinalBase, TestGmCameraSafetyBase):
  TX_MSGS = [[0x180, 0], [0x315, 0], [0x2CB, 0], [0x2CD, 0], [0x370, 0], [0x200, 0], [0x1E1, 0], [0x3D1, 0], [0xBD, 0], [0x1F5, 0],  # pt bus
             [0x184, 2]]  # camera bus
  FWD_BLACKLISTED_ADDRS = {2: [0x180, 0x2CB, 0x2CD, 0x370, 0x315], 0: [0x184]}  # block LKAS, ACC messages and PSCMStatus
  RELAY_MALFUNCTION_ADDRS = {0: (0x180, 0x2CB, 0x2CD, 0x370, 0x315), 2: (0x184,)}
  BUTTONS_BUS = 0  # rx only

  MAX_GAS = 2698
  MIN_GAS = -540  # maximum regen
  INACTIVE_GAS = -500

  def setUp(self):
    self.packer = CANPackerSafety("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerSafety("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.gm, GMSafetyFlags.HW_CAM | GMSafetyFlags.HW_CAM_LONG | self.EXTRA_SAFETY_PARAM)
    self.safety.init_tests()


class TestGmCameraLongitudinalEVSafety(GmCameraAccEVRegenMixin, TestGmCameraLongitudinalSafety, TestGmEVSafetyBase):
  pass


class TestGmCameraLongitudinalNoCameraSafety(TestGmCameraLongitudinalSafety):
  TX_MSGS = TestGmCameraLongitudinalSafety.TX_MSGS + [[0x409, 0], [0x40A, 0]]
  RELAY_MALFUNCTION_ADDRS = {0: (), 2: ()}

  def setUp(self):
    self.packer = CANPackerSafety("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerSafety("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.gm, GMSafetyFlags.HW_CAM | GMSafetyFlags.HW_CAM_LONG | GMSafetyFlags.FLAG_GM_NO_CAMERA)
    self.safety.init_tests()


def interceptor_msg(gas, addr):
  to_send = common.make_msg(0, addr, 6)
  to_send[0].data[0] = (gas & 0xFF00) >> 8
  to_send[0].data[1] = gas & 0xFF
  to_send[0].data[2] = (gas & 0xFF00) >> 8
  to_send[0].data[3] = gas & 0xFF
  return to_send


class TestGmInterceptorSafety(common.GasInterceptorSafetyTest, TestGmCameraSafety, TestGmEVSafetyBase):
  INTERCEPTOR_THRESHOLD = 550
  FWD_BLACKLISTED_ADDRS = {2: [0x180, 0x370], 0: [0x184, 0x3D1]}

  def setUp(self):
    self.packer = CANPackerPanda("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerPanda("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(
      CarParams.SafetyModel.gm,
      GMSafetyFlags.HW_CAM | GMSafetyFlags.FLAG_GM_NO_ACC | GMSafetyFlags.FLAG_GM_PEDAL_LONG | GMSafetyFlags.FLAG_GM_GAS_INTERCEPTOR | self.EXTRA_SAFETY_PARAM)
    self.safety.init_tests()

  def test_pcm_sets_cruise_engaged(self):
    for enabled in [True, False]:
      self._rx(self._pcm_status_msg(enabled))
      self.assertEqual(enabled, self.safety.get_cruise_engaged_prev())

  def test_no_pcm_enable(self):
    self.safety.set_controls_allowed(False)
    self.assertFalse(self.safety.get_controls_allowed())
    self._rx(self._pcm_status_msg(True))
    self.assertFalse(self.safety.get_controls_allowed())
    self.assertTrue(self.safety.get_cruise_engaged_prev())

  def test_no_response_to_acc_pcm_message(self):
    for enable in [True, False]:
      self.safety.set_controls_allowed(enable)
      self._rx(self.packer.make_can_msg_panda("AcceleratorPedal2", 0, {"CruiseState": True}))
      self.assertEqual(enable, self.safety.get_controls_allowed())
      self._rx(self.packer.make_can_msg_panda("AcceleratorPedal2", 0, {"CruiseState": False}))
      self.assertEqual(enable, self.safety.get_controls_allowed())

  def test_buttons(self):
    # Pedal-long non-ACC only allows CANCEL when the CC-only cruise state is engaged.
    self.safety.set_controls_allowed(False)
    for btn in range(8):
      self.assertFalse(self._tx(self._button_msg(btn)))

    self.safety.set_controls_allowed(True)
    for btn in range(8):
      self.assertFalse(self._tx(self._button_msg(btn)))

    for enabled in (True, False):
      self._rx(self._pcm_status_msg(enabled))
      self.assertEqual(enabled, self._tx(self._button_msg(Buttons.CANCEL)))

  def test_cancel_remap_passthrough_does_not_disable_controls(self):
    for extra_safety_param in (0, GMSafetyFlags.FLAG_GM_BOLT_2022_PEDAL):
      self.safety.set_safety_hooks(
        CarParams.SafetyModel.gm,
        GMSafetyFlags.HW_CAM | GMSafetyFlags.FLAG_GM_NO_ACC | GMSafetyFlags.FLAG_GM_PEDAL_LONG |
        GMSafetyFlags.FLAG_GM_GAS_INTERCEPTOR | extra_safety_param,
      )
      self.safety.init_tests()
      self.safety.set_alternative_experience(0x40)
      self._rx(self._pcm_status_msg(True))
      self.safety.set_controls_allowed(True)
      self._rx(self._button_msg(Buttons.CANCEL))
      self.assertTrue(self.safety.get_controls_allowed())

  def test_disable_control_allowed_from_cruise(self):
    pass

  def test_enable_control_allowed_from_cruise(self):
    pass

  def _interceptor_gas_cmd(self, gas):
    return interceptor_msg(gas, 0x200)

  def _interceptor_user_gas(self, gas):
    return interceptor_msg(gas, 0x201)

  def _pcm_status_msg(self, enable):
    to_send = common.make_msg(0, 0x3D1, 8)
    if enable:
      to_send[0].data[4] |= 0x80
    return to_send


class TestGmBolt2022PedalFrictionSafety(TestGmInterceptorSafety):
  TX_MSGS = TestGmInterceptorSafety.TX_MSGS + [[0x315, 0]]
  FWD_BLACKLISTED_ADDRS = {2: [0x180, 0x370, 0x315], 0: [0x184, 0x3D1]}
  RELAY_MALFUNCTION_ADDRS = {0: (0x180, 0x315), 2: (0x184,)}
  EXTRA_SAFETY_PARAM = GMSafetyFlags.FLAG_GM_BOLT_2022_PEDAL

  def setUp(self):
    self.packer = CANPackerPanda("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerPanda("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(
      CarParams.SafetyModel.gm,
      GMSafetyFlags.HW_CAM |
      GMSafetyFlags.FLAG_GM_NO_ACC |
      GMSafetyFlags.FLAG_GM_PEDAL_LONG |
      GMSafetyFlags.FLAG_GM_GAS_INTERCEPTOR |
      GMSafetyFlags.FLAG_GM_PANDA_PADDLE_SCHED |
      self.EXTRA_SAFETY_PARAM)
    self.safety.init_tests()

  def _send_brake_msg(self, brake):
    values = {"FrictionBrakeCmd": -brake}
    return self.packer_chassis.make_can_msg_safety("EBCMFrictionBrakeCmd", 0, values)

  def _engage_longitudinal(self):
    self._rx(self.packer.make_can_msg_panda("ASCMSteeringButton", 0, {"ACCButtons": Buttons.DECEL_SET}))
    self._rx(self.packer.make_can_msg_panda("ASCMSteeringButton", 0, {"ACCButtons": Buttons.UNPRESS}))
    self.assertTrue(self.safety.get_controls_allowed())
    self.assertTrue(self.safety.get_longitudinal_allowed())

  def test_tx_hook_on_wrong_safety_mode(self):
    self.skipTest("Gen2 Bolt pedal friction experiment intentionally shares the interceptor TX set plus 0x315")

  def test_buttons(self):
    for controls_allowed in (False, True):
      self.safety.set_controls_allowed(controls_allowed)
      for btn in range(8):
        self.assertEqual(btn == Buttons.CANCEL, self._tx(self._button_msg(btn)))

  def test_brake_allowed_when_controls_allowed(self):
    self._engage_longitudinal()
    self.assertTrue(self._tx(self._send_brake_msg(100)))

  def test_brake_blocked_without_controls(self):
    self.safety.set_controls_allowed(False)
    self.assertFalse(self._tx(self._send_brake_msg(100)))

  def test_brake_limit_enforced(self):
    self._engage_longitudinal()
    self.assertTrue(self._tx(self._send_brake_msg(400)))
    self.assertFalse(self._tx(self._send_brake_msg(401)))

  def test_brake_whitelist_requires_paddle_scheduler_selector(self):
    self.safety.set_safety_hooks(
      CarParams.SafetyModel.gm,
      GMSafetyFlags.HW_CAM |
      GMSafetyFlags.FLAG_GM_NO_ACC |
      GMSafetyFlags.FLAG_GM_PEDAL_LONG |
      GMSafetyFlags.FLAG_GM_GAS_INTERCEPTOR |
      self.EXTRA_SAFETY_PARAM)
    self.safety.init_tests()
    self._engage_longitudinal()
    self.assertFalse(self._tx(self._send_brake_msg(100)))


class TestGmCcLongitudinalSafety(TestGmCameraSafety):
  TX_MSGS = [[0x180, 0], [0x370, 0], [0x1E1, 0], [0x3D1, 0], [0xBD, 0], [0x1F5, 0], [0x184, 2], [0x1E1, 2]]
  FWD_BLACKLISTED_ADDRS = {2: [0x180], 0: [0x184, 0x3D1]}  # block LKAS, PSCMStatus, and stock cruise status
  BUTTONS_BUS = 0  # tx only

  def setUp(self):
    self.packer = CANPackerPanda("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerPanda("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.gm, GMSafetyFlags.HW_CAM | GMSafetyFlags.FLAG_GM_NO_ACC | GMSafetyFlags.FLAG_GM_CC_LONG)
    self.safety.init_tests()

  def _pcm_status_msg(self, enable):
    values = {"CruiseActive": enable}
    return self.packer.make_can_msg_panda("ECMCruiseControl", 0, values)

  def test_buttons(self):
    self.safety.set_controls_allowed(0)
    for btn in range(8):
      self.assertFalse(self._tx(self._button_msg(btn)))

    self.safety.set_controls_allowed(1)
    for btn in range(8):
      self.assertFalse(self._tx(self._button_msg(btn)))

    for enabled in (True, False):
      for btn in (Buttons.RES_ACCEL, Buttons.DECEL_SET, Buttons.CANCEL):
        self._rx(self._pcm_status_msg(enabled))
        self.assertEqual(enabled, self._tx(self._button_msg(btn)))


class TestGmCcLongitudinalNoCameraSafety(TestGmCcLongitudinalSafety):
  TX_MSGS = TestGmCcLongitudinalSafety.TX_MSGS + [[0x409, 0], [0x40A, 0]]
  RELAY_MALFUNCTION_ADDRS = {0: (), 2: ()}

  def setUp(self):
    self.packer = CANPackerPanda("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerPanda("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.gm, GMSafetyFlags.HW_CAM | GMSafetyFlags.FLAG_GM_NO_ACC |
                                 GMSafetyFlags.FLAG_GM_CC_LONG | GMSafetyFlags.FLAG_GM_NO_CAMERA)
    self.safety.init_tests()


class TestGmCcLongitudinalPandaSchedSafety(TestGmCcLongitudinalSafety):
  FWD_BLACKLISTED_ADDRS = {2: [0x180, 0x370], 0: [0x184, 0x3D1]}
  INTERCEPTOR_GAS_PRESSED = 596

  def setUp(self):
    self.packer = CANPackerPanda("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerPanda("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(
      CarParams.SafetyModel.gm,
      GMSafetyFlags.HW_CAM |
      GMSafetyFlags.FLAG_GM_NO_ACC |
      GMSafetyFlags.FLAG_GM_CC_LONG |
      GMSafetyFlags.FLAG_GM_PEDAL_LONG |
      GMSafetyFlags.FLAG_GM_GAS_INTERCEPTOR |
      GMSafetyFlags.FLAG_GM_PANDA_3D1_SCHED |
      GMSafetyFlags.FLAG_GM_PANDA_PADDLE_SCHED,
    )
    self.safety.init_tests()

  def _interceptor_user_gas(self, gas):
    return interceptor_msg(gas, 0x201)

  def test_prev_gas(self):
    self.assertFalse(self.safety.get_gas_pressed_prev())
    self._rx(self._user_gas_msg(self.GAS_PRESSED_THRESHOLD + 1))
    self.assertFalse(self.safety.get_gas_pressed_prev())
    self._rx(self._interceptor_user_gas(self.INTERCEPTOR_GAS_PRESSED))
    self.assertTrue(self.safety.get_gas_pressed_prev())
    self._rx(self._interceptor_user_gas(0))
    self.assertFalse(self.safety.get_gas_pressed_prev())

  def test_no_disengage_on_gas(self):
    self._rx(self._interceptor_user_gas(0))
    self.safety.set_controls_allowed(True)
    self._rx(self._interceptor_user_gas(self.INTERCEPTOR_GAS_PRESSED))
    self.assertTrue(self.safety.get_controls_allowed())
    self.assertFalse(self.safety.get_longitudinal_allowed())
    self._rx(self._interceptor_user_gas(0))
    self.assertTrue(self.safety.get_longitudinal_allowed())
class TestGmVoltAutoHoldCameraSafety(TestGmCameraSafetyBase):
  TX_MSGS = TestGmCameraSafety.TX_MSGS + [[0x315, 0]]
  FWD_BLACKLISTED_ADDRS = {2: [0x180], 0: [0x184]}
  RELAY_MALFUNCTION_ADDRS = {0: (0x180, 0x315), 2: (0x184,)}
  EXTRA_SAFETY_PARAM = GMSafetyFlags.FLAG_GM_PANDA_PADDLE_SCHED

  def setUp(self):
    self.packer = CANPackerSafety("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerSafety("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.gm, GMSafetyFlags.HW_CAM | self.EXTRA_SAFETY_PARAM)
    self.safety.init_tests()

  def _send_brake_msg(self, brake):
    values = {"FrictionBrakeCmd": -brake}
    return self.packer_chassis.make_can_msg_safety("EBCMFrictionBrakeCmd", 0, values)

  def test_standstill_brake_allowed_without_controls_when_main_on(self):
    self._rx(self._speed_msg(0))
    self._rx(self._toggle_aol(True))
    self.safety.set_controls_allowed(False)
    self.assertTrue(self._tx(self._send_brake_msg(100)))
    self.assertEqual(-1, self.safety.safety_fwd_hook(2, 0x315))

  def test_standstill_brake_blocked_without_main_on(self):
    self._rx(self._speed_msg(0))
    self._rx(self._toggle_aol(False))
    self.safety.set_controls_allowed(False)
    self.assertFalse(self._tx(self._send_brake_msg(100)))
    self.assertEqual(0, self.safety.safety_fwd_hook(2, 0x315))

  def test_moving_brake_blocked_without_controls(self):
    self._rx(self._speed_msg(self.STANDSTILL_THRESHOLD + 1))
    self._rx(self._toggle_aol(True))
    self.safety.set_controls_allowed(False)
    self.assertFalse(self._tx(self._send_brake_msg(100)))

  def test_gas_blocks_standstill_brake_without_controls(self):
    self._rx(self._speed_msg(0))
    self._rx(self._toggle_aol(True))
    self._rx(self._user_gas_msg(True))
    self.safety.set_controls_allowed(False)
    self.assertFalse(self._tx(self._send_brake_msg(100)))


class TestGmVoltOnePedalCameraSafety(TestGmCameraSafetyBase):
  TX_MSGS = TestGmCameraSafety.TX_MSGS + [[0x315, 0]]
  FWD_BLACKLISTED_ADDRS = {2: [0x180], 0: [0x184]}
  RELAY_MALFUNCTION_ADDRS = {0: (0x180, 0x315), 2: (0x184,)}
  EXTRA_SAFETY_PARAM = GMSafetyFlags.FLAG_GM_PANDA_PADDLE_SCHED | GMSafetyFlags.FLAG_GM_PANDA_3D1_SCHED

  def setUp(self):
    self.packer = CANPackerSafety("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerSafety("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.gm, GMSafetyFlags.HW_CAM | self.EXTRA_SAFETY_PARAM)
    self.safety.init_tests()

  def _send_brake_msg(self, brake):
    values = {"FrictionBrakeCmd": -brake}
    return self.packer_chassis.make_can_msg_safety("EBCMFrictionBrakeCmd", 0, values)

  def test_moving_brake_allowed_without_controls_when_main_on(self):
    self._rx(self._speed_msg(self.STANDSTILL_THRESHOLD + 1))
    self._rx(self._toggle_aol(True))
    self.safety.set_controls_allowed(False)
    self.assertTrue(self._tx(self._send_brake_msg(100)))
    self.assertEqual(-1, self.safety.safety_fwd_hook(2, 0x315))

  def test_moving_brake_blocked_without_main_on(self):
    self._rx(self._speed_msg(self.STANDSTILL_THRESHOLD + 1))
    self._rx(self._toggle_aol(False))
    self.safety.set_controls_allowed(False)
    self.assertFalse(self._tx(self._send_brake_msg(100)))
    self.assertEqual(0, self.safety.safety_fwd_hook(2, 0x315))

  def test_gas_blocks_moving_brake_without_controls(self):
    self._rx(self._speed_msg(self.STANDSTILL_THRESHOLD + 1))
    self._rx(self._toggle_aol(True))
    self._rx(self._user_gas_msg(True))
    self.safety.set_controls_allowed(False)
    self.assertFalse(self._tx(self._send_brake_msg(100)))


class TestGmVoltAutoHoldSdgmSafety(TestGmSafetyBase):
  TX_MSGS = TestGmSdgmSafety.TX_MSGS + [[0x315, 2]]
  FWD_BLACKLISTED_ADDRS = {2: [0x180], 0: [0x184]}
  RELAY_MALFUNCTION_ADDRS = {0: (0x180,), 2: ()}
  EXTRA_SAFETY_PARAM = GMSafetyFlags.FLAG_GM_PANDA_PADDLE_SCHED

  def setUp(self):
    self.packer = CANPackerSafety("gm_global_a_powertrain_generated")
    self.packer_chassis = CANPackerSafety("gm_global_a_chassis")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.gm, GMSafetyFlags.HW_SDGM | self.EXTRA_SAFETY_PARAM)
    self.safety.init_tests()

  def _send_brake_msg(self, brake):
    values = {"FrictionBrakeCmd": -brake}
    return self.packer_chassis.make_can_msg_safety("EBCMFrictionBrakeCmd", 2, values)

  def test_standstill_brake_allowed_without_controls_when_main_on(self):
    self._rx(self._speed_msg(0))
    self._rx(self._toggle_aol(True))
    self.safety.set_controls_allowed(False)
    self.assertTrue(self._tx(self._send_brake_msg(100)))
    self.assertEqual(-1, self.safety.safety_fwd_hook(0, 0x315))

  def test_standstill_brake_blocked_without_main_on(self):
    self._rx(self._speed_msg(0))
    self._rx(self._toggle_aol(False))
    self.safety.set_controls_allowed(False)
    self.assertFalse(self._tx(self._send_brake_msg(100)))
    self.assertEqual(2, self.safety.safety_fwd_hook(0, 0x315))

  def test_moving_brake_blocked_without_controls(self):
    self._rx(self._speed_msg(self.STANDSTILL_THRESHOLD + 1))
    self._rx(self._toggle_aol(True))
    self.safety.set_controls_allowed(False)
    self.assertFalse(self._tx(self._send_brake_msg(100)))

  def test_3d1_spoof_blocked_on_acc(self):
    self.assertFalse(self._tx(common.make_msg(0, 0x3D1, 8)))

  def test_paddle_feed_apply_frames_buffered_before_stock_sync(self):
    paddle_apply = common.make_msg(0, 0xBD, 7, bytes([0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
    prndl_apply = common.make_msg(0, 0x1F5, 8, bytes([0x00, 0x00, 0x00, 0x07, 0x00, 0x00, 0x00, 0x00]))

    self.safety.set_controls_allowed(True)
    self.assertTrue(self._tx(paddle_apply))
    self.assertTrue(self._tx(prndl_apply))

  def test_paddle_feed_apply_frames_blocked_after_stock_sync(self):
    paddle_apply = common.make_msg(0, 0xBD, 7, bytes([0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
    prndl_apply = common.make_msg(0, 0x1F5, 8, bytes([0x00, 0x00, 0x00, 0x07, 0x00, 0x00, 0x00, 0x00]))

    self.safety.set_controls_allowed(True)
    self.assertTrue(self._tx(paddle_apply))
    self.assertTrue(self._tx(prndl_apply))

    self._rx(paddle_apply)
    self._rx(prndl_apply)
    self.assertFalse(self._tx(paddle_apply))
    self.assertFalse(self._tx(prndl_apply))


if __name__ == "__main__":
  unittest.main()
