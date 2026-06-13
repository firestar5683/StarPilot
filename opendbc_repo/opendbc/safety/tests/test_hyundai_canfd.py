#!/usr/bin/env python3
from parameterized import parameterized_class
import unittest
import numpy as np

from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, CarControllerParams
from opendbc.car.hyundai.values import HyundaiSafetyFlags, HyundaiStarPilotSafetyFlags
from opendbc.car.lateral import get_max_angle_delta_vm, get_max_angle_vm
from opendbc.car.structs import CarParams
from opendbc.car.vehicle_model import VehicleModel
from opendbc.safety.tests.libsafety import libsafety_py
import opendbc.safety.tests.common as common
from opendbc.safety.tests.common import CANPackerSafety, away_round, round_speed
from opendbc.safety.tests.hyundai_common import HyundaiAolLkasOnEngageBase, HyundaiAolLkasOnEngageStockBase, HyundaiButtonBase, HyundaiLongitudinalBase

# All combinations of radar/camera-SCC and gas/hybrid/EV cars
ALL_GAS_EV_HYBRID_COMBOS = [
  # Radar SCC
  {"GAS_MSG": ("ACCELERATOR_BRAKE_ALT", "ACCELERATOR_PEDAL_PRESSED"), "SCC_BUS": 0, "SAFETY_PARAM": 0},
  {"GAS_MSG": ("ACCELERATOR", "ACCELERATOR_PEDAL"), "SCC_BUS": 0, "SAFETY_PARAM": HyundaiSafetyFlags.EV_GAS},
  {"GAS_MSG": ("ACCELERATOR_ALT", "ACCELERATOR_PEDAL"), "SCC_BUS": 0, "SAFETY_PARAM": HyundaiSafetyFlags.HYBRID_GAS},
  # Camera SCC
  {"GAS_MSG": ("ACCELERATOR_BRAKE_ALT", "ACCELERATOR_PEDAL_PRESSED"), "SCC_BUS": 2, "SAFETY_PARAM": HyundaiSafetyFlags.CAMERA_SCC},
  {"GAS_MSG": ("ACCELERATOR", "ACCELERATOR_PEDAL"), "SCC_BUS": 2, "SAFETY_PARAM": HyundaiSafetyFlags.EV_GAS | HyundaiSafetyFlags.CAMERA_SCC},
  {"GAS_MSG": ("ACCELERATOR_ALT", "ACCELERATOR_PEDAL"), "SCC_BUS": 2, "SAFETY_PARAM": HyundaiSafetyFlags.HYBRID_GAS | HyundaiSafetyFlags.CAMERA_SCC},
]

MRR35_RADAR_TRACK_ADDRS = list(range(0x3A5, 0x3C5))


def _set_value(msg: bytearray, sig, ival: int) -> None:
  i = sig.lsb // 8
  bits = sig.size
  if sig.size < 64:
    ival &= (1 << sig.size) - 1
  while 0 <= i < len(msg) and bits > 0:
    shift = sig.lsb % 8 if (sig.lsb // 8) == i else 0
    size = min(bits, 8 - shift)
    mask = ((1 << size) - 1) << shift
    msg[i] &= ~mask
    msg[i] |= (ival & ((1 << size) - 1)) << shift
    bits -= size
    ival >>= size
    i = i + 1 if sig.is_little_endian else i - 1


class TestHyundaiCanfdBase(HyundaiButtonBase, common.CarSafetyTest, common.DriverTorqueSteeringSafetyTest, common.SteerRequestCutSafetyTest):

  TX_MSGS = [[0x50, 0], [0x1CF, 1], [0x2A4, 0]]
  STANDSTILL_THRESHOLD = 12  # 0.375 kph
  FWD_BLACKLISTED_ADDRS = {2: [0x50, 0x2a4]}

  MAX_RATE_UP = 10
  MAX_RATE_DOWN = 10
  MAX_TORQUE_LOOKUP = [0], [409]

  MAX_RT_DELTA = 375

  DRIVER_TORQUE_ALLOWANCE = 250
  DRIVER_TORQUE_FACTOR = 2

  # Safety around steering req bit
  MIN_VALID_STEERING_FRAMES = 89
  MAX_INVALID_STEERING_FRAMES = 2

  PT_BUS = 0
  SCC_BUS = 2
  STEER_BUS = 0
  STEER_MSG = ""
  GAS_MSG = ("", "")
  BUTTONS_TX_BUS = 1

  def _torque_driver_msg(self, torque):
    values = {"STEERING_COL_TORQUE": torque}
    return self.packer.make_can_msg_safety("MDPS", self.PT_BUS, values)

  def _torque_cmd_msg(self, torque, steer_req=1):
    values = {"TORQUE_REQUEST": torque, "STEER_REQ": steer_req}
    return self.packer.make_can_msg_safety(self.STEER_MSG, self.STEER_BUS, values)

  def _speed_msg(self, speed):
    values = {f"WHL_Spd{pos}Val": speed * 0.03125 for pos in ["FL", "FR", "RL", "RR"]}
    return self.packer.make_can_msg_safety("WHEEL_SPEEDS", self.PT_BUS, values)

  def _user_brake_msg(self, brake):
    values = {"DriverBraking": brake}
    return self.packer.make_can_msg_safety("TCS", self.PT_BUS, values)

  def _user_gas_msg(self, gas):
    values = {self.GAS_MSG[1]: gas}
    return self.packer.make_can_msg_safety(self.GAS_MSG[0], self.PT_BUS, values)

  def _pcm_status_msg(self, enable):
    values = {"ACCMode": 1 if enable else 0}
    return self.packer.make_can_msg_safety("SCC_CONTROL", self.SCC_BUS, values)

  def _acc_state_msg(self, main_on):
    values = {"MainMode_ACC": int(main_on), "ACCMode": 0}
    return self.packer.make_can_msg_safety("SCC_CONTROL", self.SCC_BUS, values)

  def _button_msg(self, buttons, main_button=0, bus=None):
    if bus is None:
      bus = self.PT_BUS
    values = {
      "CRUISE_BUTTONS": buttons,
      "ADAPTIVE_CRUISE_MAIN_BTN": main_button,
    }
    return self.packer.make_can_msg_safety("CRUISE_BUTTONS", bus, values)

  def _toggle_aol(self, toggle_on):
    if not hasattr(self, "_aol_state"):
      self._aol_state = False

    # Already in the requested state
    if toggle_on == self._aol_state:
      return None

    # Simulate button press + release
    values = {
      "CRUISE_BUTTONS": 0,
      "ADAPTIVE_CRUISE_MAIN_BTN": 0,
      "LFA_BTN": 1,
      "COUNTER": 0,
    }
    self._rx(self.packer.make_can_msg_panda("CRUISE_BUTTONS", self.PT_BUS, values))
    self._rx(self.packer.make_can_msg_panda("CRUISE_BUTTONS", self.PT_BUS, {**values, "LFA_BTN": 0}))

    self._aol_state = toggle_on
    return None  # avoid duplicate message in harness

  def test_pcm_main_cruise_state_availability(self):
    if self.safety.get_current_safety_param() & HyundaiSafetyFlags.LONG:
      raise unittest.SkipTest("Longitudinal mode does not learn ACC main state from SCC_CONTROL RX")

    for should_turn_acc_main_on in (True, False):
      self._rx(self._acc_state_msg(should_turn_acc_main_on))
      self.assertEqual(should_turn_acc_main_on, self.safety.get_acc_main_on())


class TestHyundaiCanfdLFASteeringBase(TestHyundaiCanfdBase):

  TX_MSGS = [[0x12A, 0], [0x1A0, 1], [0x1CF, 0], [0x1E0, 0]]
  RELAY_MALFUNCTION_ADDRS = {0: (0x12A, 0xCB, 0x1E0)}  # LFA, ADAS_CMD_35_10ms, LFAHDA_CLUSTER
  FWD_BLACKLISTED_ADDRS = {2: [0x12A, 0xCB, 0x1E0]}

  STEER_MSG = "LFA"
  BUTTONS_TX_BUS = 2
  SAFETY_PARAM: int

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    if cls.__name__ in ("TestHyundaiCanfdLFASteering", "TestHyundaiCanfdLFASteeringAltButtons"):
      cls.packer = None
      cls.safety = None
      raise unittest.SkipTest

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_canfd_generated")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd, self.SAFETY_PARAM)
    self.safety.init_tests()


class TestHyundaiCanfdAngleSteering(HyundaiButtonBase, common.CarSafetyTest):

  TX_MSGS = [[0x12A, 0], [0xCB, 0], [0x160, 0], [0x1A0, 0], [0x1CF, 2], [0x1E0, 0]]
  RELAY_MALFUNCTION_ADDRS = {0: (0x12A, 0xCB, 0x1E0)}
  FWD_BLACKLISTED_ADDRS = {2: [0x12A, 0xCB, 0x1E0]}

  PT_BUS = 0
  SCC_BUS = 2
  BUTTONS_TX_BUS = 2
  LATERAL_FREQUENCY = 100
  STANDSTILL_THRESHOLD = 12
  STEER_ANGLE_MAX = 360
  DEG_TO_CAN = 10
  GAS_MSG = ("ACCELERATOR_ALT", "ACCELERATOR_PEDAL")
  SAFETY_PARAM = HyundaiSafetyFlags.CANFD_ANGLE_STEERING | HyundaiSafetyFlags.CAMERA_SCC | HyundaiSafetyFlags.HYBRID_GAS
  BASELINE_CAR = CAR.KIA_SPORTAGE_HEV_2026

  @classmethod
  def setUpClass(cls):
    if cls.__name__ == "TestHyundaiCanfdAngleSteering":
      super().setUpClass()

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_canfd_generated")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd, self.SAFETY_PARAM)
    self.safety.init_tests()
    self.angle_cmd_cnt = 0

  def _speed_msg(self, speed):
    values = {f"WHL_Spd{pos}Val": speed * 0.03125 for pos in ["FL", "FR", "RL", "RR"]}
    return self.packer.make_can_msg_safety("WHEEL_SPEEDS", self.PT_BUS, values)

  def _pcm_status_msg(self, enable):
    values = {"ACCMode": 1 if enable else 0}
    return self.packer.make_can_msg_safety("SCC_CONTROL", self.SCC_BUS, values)

  def _user_brake_msg(self, brake):
    values = {"DriverBraking": brake}
    return self.packer.make_can_msg_safety("TCS", self.PT_BUS, values)

  def _user_gas_msg(self, gas):
    values = {self.GAS_MSG[1]: gas}
    return self.packer.make_can_msg_safety(self.GAS_MSG[0], self.PT_BUS, values)

  def _button_msg(self, buttons, main_button=0, bus=None):
    if bus is None:
      bus = self.PT_BUS
    values = {
      "CRUISE_BUTTONS": buttons,
      "ADAPTIVE_CRUISE_MAIN_BTN": main_button,
    }
    return self.packer.make_can_msg_safety("CRUISE_BUTTONS", bus, values)

  def _angle_meas_msg(self, angle):
    values = {"STEERING_ANGLE": angle}
    return self.packer.make_can_msg_safety("MDPS", self.PT_BUS, values)

  def _reset_angle_measurement(self, angle):
    for _ in range(common.MAX_SAMPLE_VALS):
      self._rx(self._angle_meas_msg(angle))

  def _reset_speed_measurement(self, speed):
    for _ in range(common.MAX_SAMPLE_VALS):
      self._rx(self._speed_msg(speed))

  def _set_prev_desired_angle(self, angle):
    self.safety.set_desired_angle_last(round(angle * self.DEG_TO_CAN))

  def _get_vm(self, car_name):
    return VehicleModel(CarInterface.get_non_essential_params(str(car_name)))

  def _baseline_limits(self):
    return CarControllerParams(CarInterface.get_non_essential_params(str(self.BASELINE_CAR)))

  def _get_steer_cmd_angle_max(self, speed):
    limits = self._baseline_limits()
    return get_max_angle_vm(max(speed, 1), self._get_vm(self.BASELINE_CAR), limits)

  def _update_checksum(self, addr, dat):
    msg = self.packer.dbc.addr_to_msg[addr]
    sig_checksum = next((s for s in msg.sigs.values() if s.calc_checksum is not None), None)
    checksum = sig_checksum.calc_checksum(addr, sig_checksum, dat)
    _set_value(dat, sig_checksum, checksum)

  def _angle_cmd_msg(self, angle, enabled, increment_timer=True, gain_raw=250):
    if increment_timer:
      self.safety.set_timer(self.angle_cmd_cnt * int(1e6 / self.LATERAL_FREQUENCY))
      self.angle_cmd_cnt += 1

    addr = self.packer.dbc.name_to_msg["LFA"].address
    dat = self.packer.pack(addr, {
      "LKA_MODE": 2,
      "LKA_ICON": 2 if enabled else 1,
      "TORQUE_REQUEST": 0,
      "LKA_ASSIST": 0,
      "STEER_REQ": 0,
      "STEER_MODE": 0,
      "NEW_SIGNAL_1": 0,
      "NEW_SIGNAL_2": 0,
    })

    desired_angle = int(round(np.clip(angle, -819.1, 819.1) * self.DEG_TO_CAN))
    if desired_angle < 0:
      desired_angle += 1 << 14

    dat[9] = (dat[9] & ~0x30) | (((2 if enabled else 1) & 0x3) << 4)
    dat[10] = (dat[10] & 0x03) | ((desired_angle & 0x3F) << 2)
    dat[11] = (desired_angle >> 6) & 0xFF
    dat[12] = gain_raw if enabled or gain_raw != 250 else 0
    self._update_checksum(addr, dat)
    return libsafety_py.make_CANPacket(addr, 0, bytes(dat))

  def test_steering_angle_measurements(self):
    self._common_measurement_test(self._angle_meas_msg, -self.STEER_ANGLE_MAX, self.STEER_ANGLE_MAX, self.DEG_TO_CAN,
                                  self.safety.get_angle_meas_min, self.safety.get_angle_meas_max)

  def test_angle_cmd_when_disabled(self):
    for controls_allowed in (True, False):
      self.safety.set_controls_allowed(controls_allowed)
      for angle_meas in np.arange(-90, 91, 10):
        self._reset_angle_measurement(angle_meas)
        for angle_cmd in np.arange(-90, 91, 10):
          self._set_prev_desired_angle(angle_cmd)
          self.assertEqual(controls_allowed, self._tx(self._angle_cmd_msg(angle_cmd, True)))
          self.assertEqual(angle_cmd == angle_meas, self._tx(self._angle_cmd_msg(angle_cmd, False)))

  def test_lateral_accel_limit(self):
    limits = self._baseline_limits()
    vm = self._get_vm(self.BASELINE_CAR)

    for speed in np.linspace(0, 40, 40):
      speed = round_speed(away_round(speed / 0.03125 * 3.6) * 0.03125 / 3.6)
      speed = max(speed, 1)
      self.safety.set_controls_allowed(True)
      self._reset_speed_measurement(speed + 1)

      max_angle = round(get_max_angle_vm(speed, vm, limits), 1)
      max_angle = float(np.clip(max_angle, -self.STEER_ANGLE_MAX, self.STEER_ANGLE_MAX))
      self.safety.set_desired_angle_last(round(max_angle * self.DEG_TO_CAN))
      self.assertTrue(self._tx(self._angle_cmd_msg(max_angle, True)))

  def test_lateral_jerk_limit(self):
    limits = self._baseline_limits()
    vm = self._get_vm(self.BASELINE_CAR)

    for speed in np.linspace(0, 40, 40):
      speed = round_speed(away_round(speed / 0.03125 * 3.6) * 0.03125 / 3.6)
      speed = max(speed, 1)
      self.safety.set_controls_allowed(True)
      self._reset_speed_measurement(speed + 1)
      self.assertTrue(self._tx(self._angle_cmd_msg(0, True)))

      max_delta = round(get_max_angle_delta_vm(speed, vm, limits), 1)
      self.assertTrue(self._tx(self._angle_cmd_msg(max_delta, True)))
      self.safety.set_desired_angle_last(round(max_delta * self.DEG_TO_CAN))
      self.assertTrue(self._tx(self._angle_cmd_msg(max_delta, True)))
      self.assertTrue(self._tx(self._angle_cmd_msg(0, True)))

  def test_rt_limits(self):
    self.safety.set_timer(0)
    self.safety.set_controls_allowed(True)
    max_rt_msgs = int(self.LATERAL_FREQUENCY * common.RT_INTERVAL / 1e6 * 1.2 + 1)

    for i in range(max_rt_msgs * 2):
      should_tx = i <= max_rt_msgs
      self.assertEqual(should_tx, self._tx(self._angle_cmd_msg(0, True, increment_timer=False)))

    self.safety.set_timer(common.RT_INTERVAL)
    self.assertFalse(self._tx(self._angle_cmd_msg(0, True, increment_timer=False)))
    self.assertTrue(self._tx(self._angle_cmd_msg(0, True, increment_timer=False)))

  def test_angle_torque_reduction_gain_limits(self):
    if self.__class__.__name__ != "TestHyundaiCanfdAngleSteering":
      return

    self.safety.set_controls_allowed(True)
    self._reset_speed_measurement(1)
    self._set_prev_desired_angle(0)
    self.assertTrue(self._tx(self._angle_cmd_msg(0, True, gain_raw=250)))
    self._set_prev_desired_angle(0)
    self.assertFalse(self._tx(self._angle_cmd_msg(0, True, gain_raw=251)))
    self._set_prev_desired_angle(0)
    self.assertFalse(self._tx(self._angle_cmd_msg(0, False, gain_raw=1)))


class TestHyundaiCanfdAngleSteeringLfaAlt(TestHyundaiCanfdAngleSteering):

  def _angle_cmd_msg(self, angle, enabled, increment_timer=True):
    if increment_timer:
      self.safety.set_timer(self.angle_cmd_cnt * int(1e6 / self.LATERAL_FREQUENCY))
      self.angle_cmd_cnt += 1

    values = {
      "ADAS_ActvACISta": 0,
      "ADAS_ActvACILvl2Sta": 2 if enabled else 1,
      "ADAS_StrAnglReqVal": angle,
      "ADAS_ACIAnglTqRedcGainVal": 1.0 if enabled else 0.0,
      "FCA_ESA_ActvSta": 0,
      "FCA_ESA_TqBstGainVal": 0.0,
    }
    return self.packer.make_can_msg_safety("ADAS_CMD_35_10ms", 0, values)


@parameterized_class(ALL_GAS_EV_HYBRID_COMBOS)
class TestHyundaiCanfdLFASteering(TestHyundaiCanfdLFASteeringBase):
  pass


class TestHyundaiCanfdLFASteeringAltButtonsBase(TestHyundaiCanfdLFASteeringBase):

  SAFETY_PARAM: int

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_canfd_generated")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd, HyundaiSafetyFlags.CANFD_ALT_BUTTONS | self.SAFETY_PARAM)
    self.safety.init_tests()

  def _button_msg(self, buttons, main_button=0, bus=1):
    values = {
      "CRUISE_BUTTONS": buttons,
      "ADAPTIVE_CRUISE_MAIN_BTN": main_button,
    }
    return self.packer.make_can_msg_safety("CRUISE_BUTTONS_ALT", self.PT_BUS, values)

  def _acc_cancel_msg(self, cancel, accel=0):
    values = {"ACCMode": 4 if cancel else 0, "aReqRaw": accel, "aReqValue": accel}
    return self.packer.make_can_msg_safety("SCC_CONTROL", self.PT_BUS, values)

  def test_button_sends(self):
    """
      No button send allowed with alt buttons.
    """
    for enabled in (True, False):
      for btn in range(8):
        self.safety.set_controls_allowed(enabled)
        self.assertFalse(self._tx(self._button_msg(btn)))

  def test_acc_cancel(self):
    # FIXME: the CANFD_ALT_BUTTONS cars are the only ones that use SCC_CONTROL to cancel, why can't we use buttons?
    for enabled in (True, False):
      self.safety.set_controls_allowed(enabled)
      self.assertTrue(self._tx(self._acc_cancel_msg(True)))
      self.assertFalse(self._tx(self._acc_cancel_msg(True, accel=1)))
      self.assertFalse(self._tx(self._acc_cancel_msg(False)))

  def _toggle_aol(self, toggle_on):
    if not hasattr(self, "_aol_state"):
      self._aol_state = False

    # Already in the requested state
    if toggle_on == self._aol_state:
      return None

    # Simulate button press + release
    values = {
      "CRUISE_BUTTONS_ALT": 0,
      "ADAPTIVE_CRUISE_MAIN_BTN": 0,
      "LFA_BTN": 1,
      "COUNTER": 0,
    }
    self._rx(self.packer.make_can_msg_panda("CRUISE_BUTTONS_ALT", self.PT_BUS, values))
    self._rx(self.packer.make_can_msg_panda("CRUISE_BUTTONS_ALT", self.PT_BUS, {**values, "LFA_BTN": 0}))

    self._aol_state = toggle_on
    return None  # avoid duplicate message in harness


@parameterized_class(ALL_GAS_EV_HYBRID_COMBOS)
class TestHyundaiCanfdLFASteeringAltButtons(TestHyundaiCanfdLFASteeringAltButtonsBase):
  pass


class TestHyundaiCanfdCCNCSupportFrames(common.SafetyTestBase):
  TX_MSGS = [[0x161, 0], [0x162, 0], [0x7C4, 2], [0xEA, 2]]

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_canfd_generated")
    self.safety = libsafety_py.libsafety

  def _set_hooks(self, param):
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd, param)
    self.safety.init_tests()

  def test_ccnc_support_frames_require_ccnc_flag(self):
    support_msgs = (
      self.packer.make_can_msg_safety("CCNC_0x161", 0, {}),
      self.packer.make_can_msg_safety("CCNC_0x162", 0, {}),
      common.make_msg(2, 0x7C4, 8),
      common.make_msg(2, 0xEA, 24),
    )

    for longitudinal in (False, True):
      base_param = HyundaiSafetyFlags.CAMERA_SCC | (HyundaiSafetyFlags.LONG if longitudinal else 0)

      self._set_hooks(base_param)
      for msg in support_msgs:
        self.assertFalse(self._tx(msg))

      self._set_hooks(base_param | HyundaiSafetyFlags.CCNC)
      for msg in support_msgs:
        self.assertTrue(self._tx(msg))


class TestHyundaiCanfdLKASteeringEV(TestHyundaiCanfdBase):

  TX_MSGS = [[0x50, 0], [0x1CF, 1], [0x2A4, 0]]
  RELAY_MALFUNCTION_ADDRS = {0: (0x50, 0x2a4)}  # LKAS, CAM_0x2A4
  FWD_BLACKLISTED_ADDRS = {2: [0x50, 0x2a4]}

  PT_BUS = 1
  SCC_BUS = 1
  STEER_MSG = "LKAS"
  GAS_MSG = ("ACCELERATOR", "ACCELERATOR_PEDAL")

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_canfd_generated")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd, HyundaiSafetyFlags.CANFD_LKA_STEERING | HyundaiSafetyFlags.EV_GAS)
    self.safety.init_tests()

  def _paddle_msg(self, left_paddle=0, right_paddle=0, buttons=0, main_button=0, lka_button=0, bus=None):
    if bus is None:
      bus = self.BUTTONS_TX_BUS
    values = {
      "CRUISE_BUTTONS": buttons,
      "ADAPTIVE_CRUISE_MAIN_BTN": main_button,
      "LDA_BTN": lka_button,
      "RIGHT_PADDLE": right_paddle,
      "LEFT_PADDLE": left_paddle,
      "SET_ME_1": 1,
    }
    return self.packer.make_can_msg_safety("CRUISE_BUTTONS", bus, values)

  def test_left_paddle_send(self):
    for controls_allowed in (True, False):
      self.safety.set_controls_allowed(controls_allowed)
      self.assertFalse(self._tx(self._paddle_msg(left_paddle=1)))


# TODO: Handle ICE and HEV configurations once we see cars that use the new messages
class TestHyundaiCanfdLKASteeringAltEV(TestHyundaiCanfdBase):

  TX_MSGS = [[0x110, 0], [0x1CF, 1], [0x362, 0]]
  RELAY_MALFUNCTION_ADDRS = {0: (0x110, 0x362)}  # LKAS_ALT, CAM_0x362
  FWD_BLACKLISTED_ADDRS = {2: [0x110, 0x362]}

  PT_BUS = 1
  SCC_BUS = 1
  STEER_MSG = "LKAS_ALT"
  GAS_MSG = ("ACCELERATOR", "ACCELERATOR_PEDAL")

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_canfd_generated")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd, HyundaiSafetyFlags.CANFD_LKA_STEERING | HyundaiSafetyFlags.EV_GAS |
                                 HyundaiSafetyFlags.CANFD_LKA_STEERING_ALT)
    self.safety.init_tests()


class TestHyundaiCanfdLKASteeringLongEV(HyundaiLongitudinalBase, TestHyundaiCanfdLKASteeringEV):

  TX_MSGS = [[0x50, 0], [0x1CF, 1], [0x2A4, 0], [0x51, 0], [0x730, 1], [0x12a, 1], [0x160, 1],
             [0x1ba, 1], [0x1e0, 1], [0x1e5, 1], [0x31a, 1], [0x3b5, 1], [0x3c1, 1],
             [0x1a0, 1], [0x1ea, 1], [0x200, 1], [0x345, 1], [0x1da, 1]]

  RELAY_MALFUNCTION_ADDRS = {0: (0x50, 0x2a4), 1: (0x1a0,)}  # LKAS, CAM_0x2A4, SCC_CONTROL
  FWD_BLACKLISTED_ADDRS = {0: MRR35_RADAR_TRACK_ADDRS, 2: [0x50, 0x2a4]}

  DISABLED_ECU_UDS_MSG = (0x730, 1)
  DISABLED_ECU_ACTUATION_MSG = (0x1a0, 1)

  STEER_MSG = "LFA"
  GAS_MSG = ("ACCELERATOR", "ACCELERATOR_PEDAL")
  STEER_BUS = 1

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_canfd_generated")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd, HyundaiSafetyFlags.CANFD_LKA_STEERING |
                                 HyundaiSafetyFlags.LONG | HyundaiSafetyFlags.EV_GAS)
    self.safety.init_tests()

  def _accel_msg(self, accel, aeb_req=False, aeb_decel=0):
    values = {
      "aReqRaw": accel,
      "aReqValue": accel,
    }
    return self.packer.make_can_msg_safety("SCC_CONTROL", 1, values)

  def _tx_acc_state_msg(self, main_on):
    values = {"MainMode_ACC": int(main_on), "ACCMode": 0}
    return self.packer.make_can_msg_safety("SCC_CONTROL", 1, values)


# Tests longitudinal for ICE, hybrid, EV cars with LFA steering
class TestHyundaiCanfdLFASteeringLongBase(HyundaiLongitudinalBase, TestHyundaiCanfdLFASteeringBase):

  TX_MSGS = [[0x12A, 0], [0x1A0, 1], [0x1CF, 0], [0x1E0, 0], [0x1BA, 0], [0x1E5, 0], [0x31A, 0], [0x3B5, 0], [0x3C1, 0]]
  FWD_BLACKLISTED_ADDRS = {2: [0x12a, 0xcb, 0x1e0, 0x1a0, 0x160]}

  RELAY_MALFUNCTION_ADDRS = {0: (0x12A, 0xCB, 0x1E0, 0x1a0, 0x160)}  # LFA, ADAS_CMD_35_10ms, LFAHDA_CLUSTER, SCC_CONTROL, ADRV_0x160

  DISABLED_ECU_UDS_MSG = (0x7D0, 0)
  DISABLED_ECU_ACTUATION_MSG = (0x1a0, 0)

  @classmethod
  def setUpClass(cls):
    if cls.__name__ == "TestHyundaiCanfdLFASteeringLongBase":
      cls.safety = None
      raise unittest.SkipTest

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_canfd_generated")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd, HyundaiSafetyFlags.LONG | self.SAFETY_PARAM)
    self.safety.init_tests()

  def _accel_msg(self, accel, aeb_req=False, aeb_decel=0):
    values = {
      "aReqRaw": accel,
      "aReqValue": accel,
    }
    return self.packer.make_can_msg_safety("SCC_CONTROL", 0, values)

  def _tx_acc_state_msg(self, main_on):
    values = {"MainMode_ACC": int(main_on), "ACCMode": 0}
    return self.packer.make_can_msg_safety("SCC_CONTROL", 0, values)

  def test_tester_present_allowed(self, ecu_disable: bool = True):
    super().test_tester_present_allowed(ecu_disable=not self.SAFETY_PARAM & HyundaiSafetyFlags.CAMERA_SCC)


@parameterized_class(ALL_GAS_EV_HYBRID_COMBOS)
class TestHyundaiCanfdLFASteeringLong(TestHyundaiCanfdLFASteeringLongBase):
  @classmethod
  def setUpClass(cls):
    if cls.__name__ == "TestHyundaiCanfdLFASteeringLong":
      cls.safety = None
      raise unittest.SkipTest


@parameterized_class(ALL_GAS_EV_HYBRID_COMBOS)
class TestHyundaiCanfdLFASteeringLongAltButtons(TestHyundaiCanfdLFASteeringLongBase, TestHyundaiCanfdLFASteeringAltButtonsBase):
  @classmethod
  def setUpClass(cls):
    if cls.__name__ == "TestHyundaiCanfdLFASteeringLongAltButtons":
      cls.safety = None
      raise unittest.SkipTest

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_canfd_generated")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd, HyundaiSafetyFlags.LONG | HyundaiSafetyFlags.CANFD_ALT_BUTTONS | self.SAFETY_PARAM)
    self.safety.init_tests()

  def test_acc_cancel(self):
    # Alt buttons does not use SCC_CONTROL to cancel if longitudinal
    pass


class TestHyundaiCanfdLKASteeringLongAolLkasOnEngageEV(HyundaiAolLkasOnEngageBase, TestHyundaiCanfdLKASteeringLongEV):
  def setUp(self):
    self.packer = CANPackerSafety("hyundai_canfd_generated")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd,
                                 HyundaiSafetyFlags.CANFD_LKA_STEERING |
                                 HyundaiSafetyFlags.LONG |
                                 HyundaiSafetyFlags.EV_GAS |
                                 HyundaiStarPilotSafetyFlags.AOL_LKAS_ON_ENGAGE)
    self.safety.init_tests()


class TestHyundaiCanfdLKASteeringAolLkasOnEngageEV(HyundaiAolLkasOnEngageStockBase, TestHyundaiCanfdLKASteeringEV):
  def setUp(self):
    self.packer = CANPackerSafety("hyundai_canfd_generated")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd,
                                 HyundaiSafetyFlags.CANFD_LKA_STEERING |
                                 HyundaiSafetyFlags.EV_GAS |
                                 HyundaiStarPilotSafetyFlags.AOL_LKAS_ON_ENGAGE)
    self.safety.init_tests()



if __name__ == "__main__":
  unittest.main()
