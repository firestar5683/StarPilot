#!/usr/bin/env python3
import numpy as np
import random
import unittest
import itertools

from opendbc.car.toyota.values import ToyotaSafetyFlags
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py
import opendbc.safety.tests.common as common

TOYOTA_COMMON_TX_MSGS = [[0x2E4, 0], [0x191, 0], [0x412, 0], [0x343, 0], [0x1D2, 0]]  # LKAS + LTA + ACC & PCM cancel cmds
TOYOTA_SECOC_TX_MSGS = [[0x131, 0], [0x183, 0]] + TOYOTA_COMMON_TX_MSGS
TOYOTA_COMMON_LONG_TX_MSGS = [[0x283, 0], [0x2E6, 0], [0x2E7, 0], [0x33E, 0], [0x344, 0], [0x365, 0], [0x366, 0], [0x4CB, 0],  # DSU bus 0
                              [0x128, 1], [0x141, 1], [0x160, 1], [0x161, 1], [0x470, 1],  # DSU bus 1
                              [0x411, 0],  # PCS_HUD
                              [0x750, 0]]  # radar diagnostic address


class TestToyotaSafetyBase(common.CarSafetyTest, common.LongitudinalAccelSafetyTest):

  DBC = "toyota_nodsu_pt_generated"
  SAFETY_MODEL = CarParams.SafetyModel.toyota

  TX_MSGS = TOYOTA_COMMON_TX_MSGS + TOYOTA_COMMON_LONG_TX_MSGS
  RELAY_MALFUNCTION_ADDRS = {0: (0x2E4, 0x191, 0x412, 0x343)}
  FWD_BLACKLISTED_ADDRS = {2: [0x2E4, 0x412, 0x191, 0x343]}
  EPS_SCALE = 73

  def _torque_meas_msg(self, torque: int, driver_torque: int | None = None):
    values = {"STEER_TORQUE_EPS": (torque / self.EPS_SCALE) * 100.}
    if driver_torque is not None:
      values["STEER_TORQUE_DRIVER"] = driver_torque
    return self.packer.make_can_msg_safety("STEER_TORQUE_SENSOR", 0, values)

  # Both torque and angle safety modes test with each other's steering commands
  def _torque_cmd_msg(self, torque, steer_req=1):
    values = {"STEER_TORQUE_CMD": torque, "STEER_REQUEST": steer_req}
    return self.packer.make_can_msg_safety("STEERING_LKA", 0, values)

  def _angle_meas_msg(self, angle: float, steer_angle_initializing: bool = False):
    # This creates a steering torque angle message. Not set on all platforms,
    # relative to init angle on some older TSS2 platforms. Only to be used with LTA
    values = {"STEER_ANGLE": angle, "STEER_ANGLE_INITIALIZING": int(steer_angle_initializing)}
    return self.packer.make_can_msg_safety("STEER_TORQUE_SENSOR", 0, values)

  def _angle_cmd_msg(self, angle: float, enabled: bool):
    return self._lta_msg(int(enabled), int(enabled), angle, torque_wind_down=100 if enabled else 0)

  def _lta_msg(self, req, req2, angle_cmd, torque_wind_down=100):
    values = {"STEER_REQUEST": req, "STEER_REQUEST_2": req2, "STEER_ANGLE_CMD": angle_cmd, "TORQUE_WIND_DOWN": torque_wind_down}
    return self.packer.make_can_msg_safety("STEERING_LTA", 0, values)

  def _accel_msg_343(self, accel, cancel_req=0):
    values = {"ACCEL_CMD": accel, "CANCEL_REQ": cancel_req}
    return self.packer.make_can_msg_safety("ACC_CONTROL", 0, values)

  def _accel_msg(self, accel, cancel_req=0):
    return self._accel_msg_343(accel, cancel_req)

  def _speed_msg(self, speed, quality_flag=True):
    values = {("WHEEL_SPEED_%s" % n): speed * 3.6 for n in ["FR", "FL", "RR", "RL"]}
    if not quality_flag:
      values |= {"WHEEL_SPEED_%s_FAULT" % n: 1.0 for n in ["FR", "FL", "RR", "RL"]}
    return self.packer.make_can_msg_safety("WHEEL_SPEEDS", 0, values)

  def _user_brake_msg(self, brake):
    values = {"BRAKE_PRESSED": brake}
    return self.packer.make_can_msg_safety("BRAKE_MODULE", 0, values)

  def _user_gas_msg(self, gas):
    cruise_active = self.safety.get_controls_allowed()
    values = {"GAS_RELEASED": not gas, "CRUISE_ACTIVE": cruise_active}
    return self.packer.make_can_msg_safety("PCM_CRUISE", 0, values)

  def _pcm_status_msg(self, enable):
    values = {"CRUISE_ACTIVE": enable}
    return self.packer.make_can_msg_safety("PCM_CRUISE", 0, values)

  def test_diagnostics(self, stock_longitudinal: bool = False, ecu_disabled: bool = True):
    for should_tx, msg in ((False, b"\x6D\x02\x3E\x00\x00\x00\x00\x00"),  # fwdCamera tester present
                           (False, b"\x0F\x03\xAA\xAA\x00\x00\x00\x00"),  # non-tester present
                           (True, b"\x0F\x02\x3E\x00\x00\x00\x00\x00")):
      tester_present = libsafety_py.make_CANPacket(0x750, 0, msg)
      self.assertEqual(should_tx and ecu_disabled and not stock_longitudinal, self._tx(tester_present))

  def test_block_aeb(self, stock_longitudinal: bool = False):
    for controls_allowed in (True, False):
      for bad in (True, False):
        for _ in range(10):
          self.safety.set_controls_allowed(controls_allowed)
          dat = [random.randint(1, 255) for _ in range(7)]
          if not bad:
            dat = [0]*6 + dat[-1:]
          msg = libsafety_py.make_CANPacket(0x283, 0, bytes(dat))
          self.assertEqual(not bad and not stock_longitudinal, self._tx(msg))

  # Only allow LTA msgs with no actuation
  def test_lta_steer_cmd(self):
    for engaged, req, req2, torque_wind_down, angle in itertools.product([True, False],
                                                                  [0, 1], [0, 1],
                                                                  [0, 50, 100],
                                                                  np.linspace(-20, 20, 5)):
      self.safety.set_controls_allowed(engaged)

      should_tx = not req and not req2 and angle == 0 and torque_wind_down == 0
      self.assertEqual(should_tx, self._tx(self._lta_msg(req, req2, angle, torque_wind_down)),
                       f"{req=} {req2=} {angle=} {torque_wind_down=}")

  def test_rx_hook(self):
    # checksum checks
    for msg in ["trq", "pcm"]:
      self.safety.set_controls_allowed(1)
      if msg == "trq":
        msg = self._torque_meas_msg(0)
      if msg == "pcm":
        msg = self._pcm_status_msg(True)
      self.assertTrue(self._rx(msg))
      msg[0].data[4] = 0
      msg[0].data[5] = 0
      msg[0].data[6] = 0
      msg[0].data[7] = 0
      self.assertFalse(self._rx(msg))
      self.assertFalse(self.safety.get_controls_allowed())

    # quality flag tests
    msg = self._speed_msg(0)
    self.assertTrue(self._rx(msg))

    msg = self._speed_msg(0, quality_flag=False)
    self.assertFalse(self._rx(msg))

  def test_vehicle_speed_measurements(self):
    # OVERRIDDEN: 72.22_ is the max speed in m/s
    self._common_measurement_test(self._speed_msg, 0, 259 / 3.6, 1,
                                  self.safety.get_vehicle_speed_min, self.safety.get_vehicle_speed_max)


class TestToyotaSafetyTorque(TestToyotaSafetyBase, common.MotorTorqueSteeringSafetyTest, common.SteerRequestCutSafetyTest):

  MAX_RATE_UP = 15
  MAX_RATE_DOWN = 25
  MAX_TORQUE_LOOKUP = [0], [1500]
  MAX_RT_DELTA = 450
  MAX_TORQUE_ERROR = 350
  TORQUE_MEAS_TOLERANCE = 1  # toyota safety adds one to be conservative for rounding

  # Safety around steering req bit
  MIN_VALID_STEERING_FRAMES = 17
  MAX_INVALID_STEERING_FRAMES = 1

  @property
  def SAFETY_PARAM(self):
    return self.EPS_SCALE


class TestToyotaSafetyAngle(TestToyotaSafetyBase, common.AngleSteeringSafetyTest):

  # Angle control limits
  STEER_ANGLE_MAX = 94.9461  # deg
  DEG_TO_CAN = 17.452007  # 1 / 0.0573 deg to can

  ANGLE_RATE_BP = [5., 25., 25.]
  ANGLE_RATE_UP = [0.3, 0.15, 0.15]  # windup limit
  ANGLE_RATE_DOWN = [0.36, 0.26, 0.26]  # unwind limit

  MAX_LTA_ANGLE = 94.9461  # PCS faults if commanding above this, deg
  MAX_MEAS_TORQUE = 1500  # max allowed measured EPS torque before wind down
  MAX_LTA_DRIVER_TORQUE = 150  # max allowed driver torque before wind down

  @property
  def SAFETY_PARAM(self):
    return self.EPS_SCALE | ToyotaSafetyFlags.LTA

  def _prepare_lta_near_zero_rate(self, previous_raw):
    # At 5 m/s, the LTA windup and unwind limits round to 6 and 7 raw CAN
    # units. Check the two sign transitions where choosing the wrong limit
    # changes whether a packed, active steering command is accepted.
    self.assertEqual(int(self.ANGLE_RATE_UP[0] * self.DEG_TO_CAN + 1), 6)
    self.assertEqual(int(self.ANGLE_RATE_DOWN[0] * self.DEG_TO_CAN + 1), 7)
    self._reset_speed_measurement(5.)
    self._reset_angle_measurement(0.)
    self.safety.set_controls_allowed(True)
    self.assertTrue(self._tx(self._angle_cmd_msg(previous_raw / self.DEG_TO_CAN, True)))
    self.assertEqual(self.safety.get_desired_angle_last(), previous_raw)

  def test_lta_zero_angle_uses_unwind_rate(self):
    self._prepare_lta_near_zero_rate(0)
    self.assertTrue(self._tx(self._angle_cmd_msg(-7 / self.DEG_TO_CAN, True)))

  def test_lta_positive_angle_uses_windup_rate(self):
    self._prepare_lta_near_zero_rate(1)
    self.assertFalse(self._tx(self._angle_cmd_msg(8 / self.DEG_TO_CAN, True)))

  # Only allow LKA msgs with no actuation
  def test_lka_steer_cmd(self):
    for engaged, steer_req, torque in itertools.product([True, False],
                                                        [0, 1],
                                                        np.linspace(-1500, 1500, 7)):
      self.safety.set_controls_allowed(engaged)
      torque = int(torque)
      self.safety.set_rt_torque_last(torque)
      self.safety.set_torque_meas(torque, torque)
      self.safety.set_desired_torque_last(torque)

      should_tx = not steer_req and torque == 0
      self.assertEqual(should_tx, self._tx(self._torque_cmd_msg(torque, steer_req)))

  def test_lta_steer_cmd(self):
    """
    Tests the LTA steering command message
    controls_allowed:
    * STEER_REQUEST and STEER_REQUEST_2 do not mismatch
    * TORQUE_WIND_DOWN is only set to 0 or 100 when STEER_REQUEST and STEER_REQUEST_2 are both 1
    * Full torque messages are blocked if either EPS torque or driver torque is above the threshold

    not controls_allowed:
    * STEER_REQUEST, STEER_REQUEST_2, and TORQUE_WIND_DOWN are all 0
    """
    for controls_allowed in (True, False):
      for angle in np.arange(-90, 90, 1):
        self.safety.set_controls_allowed(controls_allowed)
        self._reset_angle_measurement(angle)
        self._set_prev_desired_angle(angle)

        self.assertTrue(self._tx(self._lta_msg(0, 0, angle, 0)))
        if controls_allowed:
          # Test the two steer request bits and TORQUE_WIND_DOWN torque wind down signal
          for req, req2, torque_wind_down in itertools.product([0, 1], [0, 1], [0, 50, 100]):
            mismatch = not (req or req2) and torque_wind_down != 0
            should_tx = req == req2 and (torque_wind_down in (0, 100)) and not mismatch
            self.assertEqual(should_tx, self._tx(self._lta_msg(req, req2, angle, torque_wind_down)))

        else:
          # Controls not allowed
          for req, req2, torque_wind_down in itertools.product([0, 1], [0, 1], [0, 50, 100]):
            should_tx = not (req or req2) and torque_wind_down == 0
            self.assertEqual(should_tx, self._tx(self._lta_msg(req, req2, angle, torque_wind_down)))

    # Test max EPS torque and driver override thresholds (independent of angle, test a few representative angles)
    for angle in (-89, 0, 89):
      self.safety.set_controls_allowed(True)
      self._reset_angle_measurement(angle)
      self._set_prev_desired_angle(angle)

      cases = itertools.product(
        (0, self.MAX_MEAS_TORQUE - 1, self.MAX_MEAS_TORQUE, self.MAX_MEAS_TORQUE + 1, self.MAX_MEAS_TORQUE * 2),
        (0, self.MAX_LTA_DRIVER_TORQUE - 1, self.MAX_LTA_DRIVER_TORQUE, self.MAX_LTA_DRIVER_TORQUE + 1, self.MAX_LTA_DRIVER_TORQUE * 2)
      )

      for eps_torque, driver_torque in cases:
        for sign in (-1, 1):
          for _ in range(6):
            self._rx(self._torque_meas_msg(sign * eps_torque, sign * driver_torque))

          # Toyota adds 1 to EPS torque since it is rounded after EPS factor
          should_tx = (eps_torque - 1) <= self.MAX_MEAS_TORQUE and driver_torque <= self.MAX_LTA_DRIVER_TORQUE
          self.assertEqual(should_tx, self._tx(self._lta_msg(1, 1, angle, 100)))
          self.assertTrue(self._tx(self._lta_msg(1, 1, angle, 0)))  # should tx if we wind down torque

  def test_angle_measurements(self):
    """
    * Tests angle meas quality flag dictates whether angle measurement is parsed, and if rx is valid
    * Tests rx hook correctly clips the angle measurement, since it is to be compared to LTA cmd when inactive
    """
    for steer_angle_initializing in (True, False):
      for angle in np.arange(0, self.STEER_ANGLE_MAX * 2, 1):
        # If init flag is set, do not rx or parse any angle measurements
        for a in (angle, -angle, 0, 0, 0, 0):
          self.assertEqual(not steer_angle_initializing,
                           self._rx(self._angle_meas_msg(a, steer_angle_initializing)))

        final_angle = 0 if steer_angle_initializing else round(angle * self.DEG_TO_CAN)
        self.assertEqual(self.safety.get_angle_meas_min(), -final_angle)
        self.assertEqual(self.safety.get_angle_meas_max(), final_angle)

        self._rx(self._angle_meas_msg(0))
        self.assertEqual(self.safety.get_angle_meas_min(), -final_angle)
        self.assertEqual(self.safety.get_angle_meas_max(), 0)

        self._rx(self._angle_meas_msg(0))
        self.assertEqual(self.safety.get_angle_meas_min(), 0)
        self.assertEqual(self.safety.get_angle_meas_max(), 0)


class TestToyotaAltBrakeSafety(TestToyotaSafetyTorque):

  DBC = "toyota_new_mc_pt_generated"

  @property
  def SAFETY_PARAM(self):
    return self.EPS_SCALE | ToyotaSafetyFlags.ALT_BRAKE

  def _user_brake_msg(self, brake):
    values = {"BRAKE_PRESSED": brake}
    return self.packer.make_can_msg_safety("BRAKE_MODULE", 0, values)

  # No LTA message in the DBC
  def test_lta_steer_cmd(self):
    pass


class TestToyotaStockLongitudinalBase(TestToyotaSafetyBase):

  TX_MSGS = TOYOTA_COMMON_TX_MSGS
  # Base addresses minus ACC_CONTROL (0x343)
  RELAY_MALFUNCTION_ADDRS = {0: (0x2E4, 0x191, 0x412)}
  FWD_BLACKLISTED_ADDRS = {2: [0x2E4, 0x412, 0x191]}

  LONGITUDINAL = False

  def test_diagnostics(self, stock_longitudinal: bool = True, ecu_disabled: bool = True):
    super().test_diagnostics(stock_longitudinal=stock_longitudinal, ecu_disabled=ecu_disabled)

  def test_block_aeb(self, stock_longitudinal: bool = True):
    super().test_block_aeb(stock_longitudinal=stock_longitudinal)

  def test_acc_cancel(self):
    """
      Regardless of controls allowed, never allow ACC_CONTROL if cancel bit isn't set
    """
    for controls_allowed in [True, False]:
      self.safety.set_controls_allowed(controls_allowed)
      for accel in np.arange(self.MIN_ACCEL - 1, self.MAX_ACCEL + 1, 0.1):
        self.assertFalse(self._tx(self._accel_msg_343(accel)))
        should_tx = np.isclose(accel, self.INACTIVE_ACCEL, atol=0.0001)
        self.assertEqual(should_tx, self._tx(self._accel_msg_343(accel, cancel_req=1)))


class TestToyotaStockLongitudinalTorque(TestToyotaStockLongitudinalBase, TestToyotaSafetyTorque):

  @property
  def SAFETY_PARAM(self):
    return self.EPS_SCALE | ToyotaSafetyFlags.STOCK_LONGITUDINAL


class TestToyotaStockLongitudinalAngle(TestToyotaStockLongitudinalBase, TestToyotaSafetyAngle):

  @property
  def SAFETY_PARAM(self):
    return self.EPS_SCALE | ToyotaSafetyFlags.STOCK_LONGITUDINAL | ToyotaSafetyFlags.LTA


class TestToyotaSecOcSafetyBase(TestToyotaSafetyBase):

  DBC = "toyota_secoc_pt_generated"

  TX_MSGS = TOYOTA_SECOC_TX_MSGS
  RELAY_MALFUNCTION_ADDRS = {0: (0x2E4, 0x191, 0x412, 0x131)}
  FWD_BLACKLISTED_ADDRS = {2: [0x2E4, 0x191, 0x412, 0x131]}

  @property
  def SAFETY_PARAM(self):
    return self.EPS_SCALE | ToyotaSafetyFlags.SECOC

  def test_diagnostics(self, ecu_disabled: bool = False):
    super().test_diagnostics(ecu_disabled=ecu_disabled)

  # This platform also has alternate brake and PCM messages, but same naming in the DBC, so same packers work

  def _user_gas_msg(self, gas):
    values = {"GAS_PEDAL_USER": gas}
    return self.packer.make_can_msg_safety("GAS_PEDAL", 0, values)

  # This platform sends both STEERING_LTA (same as other Toyota) and STEERING_LTA_2 (SecOC signed)
  # STEERING_LTA is checked for no-actuation by the base class, STEERING_LTA_2 is checked for no-actuation below

  def _lta_2_msg(self, req, req2, angle_cmd, torque_wind_down=100):
    values = {"STEER_REQUEST": req, "STEER_REQUEST_2": req2, "STEER_ANGLE_CMD": angle_cmd}
    return self.packer.make_can_msg_safety("STEERING_LTA_2", 0, values)

  def test_lta_2_steer_cmd(self):
    for engaged, req, req2, angle in itertools.product([True, False], [0, 1], [0, 1], np.linspace(-20, 20, 5)):
      self.safety.set_controls_allowed(engaged)

      should_tx = not req and not req2 and angle == 0
      self.assertEqual(should_tx, self._tx(self._lta_2_msg(req, req2, angle)), f"{req=} {req2=} {angle=}")

  def _accel_msg_183(self, accel):
    values = {"ACCEL_CMD": accel}
    return self.packer.make_can_msg_safety("ACC_CONTROL_2", 0, values)

  def _accel_msg(self, accel, cancel_req=0):
    return self._accel_msg_183(accel)


class TestToyotaSecOcSafetyStockLongitudinal(TestToyotaSecOcSafetyBase, TestToyotaStockLongitudinalBase):

  @property
  def SAFETY_PARAM(self):
    return self.EPS_SCALE | ToyotaSafetyFlags.STOCK_LONGITUDINAL | ToyotaSafetyFlags.SECOC


class TestToyotaSecOcSafety(TestToyotaSecOcSafetyBase):

  RELAY_MALFUNCTION_ADDRS = {0: (0x2E4, 0x191, 0x412, 0x131, 0x343, 0x183)}
  FWD_BLACKLISTED_ADDRS = {2: [0x2E4, 0x191, 0x412, 0x131, 0x343, 0x183]}

  @unittest.skip("test not applicable for cars without a DSU")
  def test_block_aeb(self, stock_longitudinal: bool = False):
    pass

  def test_343_actuation_blocked(self):
    """
    For SecOC cars, longitudinal acceleration must be sent in ACC_CONTROL_2, but all other ACC
    data remains in ACC_CONTROL. Verify no actuation is sent via ACC_CONTROL.
    """
    for controls_allowed in [True, False]:
      self.safety.set_controls_allowed(controls_allowed)
      for accel in np.arange(self.MIN_ACCEL - 1, self.MAX_ACCEL + 1, 0.1):
        should_tx = np.isclose(accel, self.INACTIVE_ACCEL, atol=0.0001)
        self.assertEqual(should_tx, self._tx(self._accel_msg_343(accel)))
        self.assertEqual(should_tx, self._tx(self._accel_msg_343(accel, cancel_req=1)))


class TestToyotaPriusLongFilter(TestToyotaSafetyTorque):
  SAFETY_PARAM = 0x1049
  TX_MSGS = TOYOTA_COMMON_TX_MSGS + [msg for msg in TOYOTA_COMMON_LONG_TX_MSGS if msg != [0x750, 0]]
  RELAY_MALFUNCTION_ADDRS = {0: (0x2E4, 0x191, 0x412)}
  FWD_BLACKLISTED_ADDRS = {2: [0x2E4, 0x412, 0x191]}

  def test_diagnostics(self):
    super().test_diagnostics(ecu_disabled=False)

  def test_filter_relay_exception_is_exact(self):
    for word, relay in ((73, True), (585, False), (0x1049, False), (0x1249, False),
                        (0x1048, True), (0x104A, True), (0x1149, True)):
      with self.subTest(word=word):
        self.safety.set_safety_hooks(self.SAFETY_MODEL, word)
        self.safety.init_tests()
        self.assertTrue(self._rx(self._accel_msg_343(0)))
        self.assertEqual(self.safety.get_relay_malfunction(), relay)
        self.assertEqual(self.safety.safety_fwd_hook(2, 0x343), -1 if relay else 0)

  def test_filter_does_not_admit_camera_bus_commands(self):
    self.safety.set_controls_allowed(True)
    for address, length in ((0x283, 7), (0x343, 8), (0x411, 8)):
      with self.subTest(address=address):
        self.assertFalse(self._tx(libsafety_py.make_CANPacket(address, 2, bytes(length))))
    for length in (7, 6):
      self.assertFalse(self._tx(libsafety_py.make_CANPacket(0x343, 0, bytes(length))))


class TestToyotaPriusLongFilterStock(TestToyotaStockLongitudinalTorque):
  SAFETY_PARAM = 0x1249

  def test_filter_stock_does_not_admit_dsu_commands(self):
    self.safety.set_controls_allowed(True)
    for address, length in ((0x283, 7), (0x411, 8), (0x750, 8)):
      self.assertFalse(self._tx(libsafety_py.make_CANPacket(address, 0, bytes(length))))

if __name__ == "__main__":
  unittest.main()


class TestToyotaHighlanderAol(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = common.CANPackerSafety("toyota_nodsu_pt_generated")

  def tearDown(self):
    self.safety.set_alternative_experience(0)
    self.safety.set_safety_hooks(CarParams.SafetyModel.noOutput, 0)

  def init(self, word=73, ae=32):
    self.safety.init_tests()
    self.safety.set_alternative_experience(ae)
    self.safety.set_safety_hooks(CarParams.SafetyModel.toyota, word)
    self.safety.set_timer(1_000_000)
    self.safety.set_aol_test_heartbeat(True)

  def rx(self, address, data, checksum=False):
    data = bytearray(data)
    if checksum:
      data[-1] = ((address & 255) + (address >> 8) + len(data) + sum(data[:-1])) & 255
    self.assertTrue(self.safety.safety_rx_hook(libsafety_py.make_CANPacket(address, 0, bytes(data))))

  def physical(self, *, cruise=False, belt=True, main=True, gear=0, door=False, eps=1, brake=False, gas=False):
    self.rx(0xAA, bytes([0x1A, 0x6F] * 4))
    self.rx(0x260, bytes(8), True)
    self.rx(0x1D2, bytes([(0 if gas else 16) | (32 if cruise else 0)]) + bytes(7), True)
    self.rx(0x226, bytes(4) + bytes([32 if brake else 0]) + bytes(3))
    self.rx(0x1D3, bytes([0, 128 if main else 0]) + bytes(6), True)
    self.rx(0x3BC, bytes([0, gear]) + bytes(6))
    self.rx(0x620, bytes(5) + bytes([4 if door else 0, 0, 0 if belt else 64]))
    self.assertTrue(self.safety.safety_rx_hook(self.packer.make_can_msg_safety("EPS_STATUS", 0, {"LKA_STATE": eps})))
    self.safety.aol_set_host_request(3)

  def test_radar_stock_lateral_never_grants_longitudinal(self):
    self.init(word=585)
    self.physical(cruise=True)
    self.assertEqual(self.safety.aol_get_request_mask(), 1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    for accel, cancel, allowed in ((0, 1, True), (0, 0, False), (0.1, 1, False), (-0.1, 1, False)):
      message = self.packer.make_can_msg_safety("ACC_CONTROL", 0, {"ACCEL_CMD": accel, "CANCEL_REQ": cancel})
      self.assertEqual(bool(self.safety.safety_tx_hook(message)), allowed)
    self.physical(main=False)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    for changes in ({'gear': 16}, {'eps': 9}, {'eps': 17}):
      self.init(word=585)
      self.physical(cruise=True)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)
      self.physical(cruise=True, **changes)
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.init(word=585)
    self.physical(cruise=True)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x343), 0)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x283), 0)
    self.safety.set_timer(1_400_001)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_main_lateral_independent_of_cruise_and_belt(self):
    for ae in (32, 160, 288):
      self.init(ae=ae)
      self.physical(belt=False)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)
      self.physical(cruise=True, belt=False)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)
      self.physical(cruise=True, belt=True)
      self.assertEqual(self.safety.aol_get_permission_mask(), 3)

  def test_brake_and_gas_preserve_lateral_only(self):
    for changes in ({"brake": True}, {"gas": True}):
      self.init()
      self.physical(cruise=True)
      self.assertEqual(self.safety.aol_get_permission_mask(), 3)
      self.physical(cruise=True, **changes)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)

  def test_physical_withdrawal_and_freshness(self):
    for changes in ({'main': False}, {'gear': 32}, {'door': True}, {'eps': 17}, {'eps': 3}, {'eps': 9}):
      with self.subTest(changes=changes):
        self.init()
        self.physical()
        self.assertEqual(self.safety.aol_get_permission_mask(), 1)
        self.physical(**changes)
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.init()
    self.physical()
    self.safety.set_timer(1_400_001)
    self.safety.aol_set_host_request(3)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_supplemental_checksum_faults(self):
    for address in (0x1D3, 0x262):
      self.init()
      self.physical()
      self.safety.safety_rx_hook(libsafety_py.make_CANPacket(address, 0, bytes(8)))
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)
      self.physical()
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)

  def test_observed_slow_source_cadence_and_expiry(self):
    self.init()
    for tick in range(1201):
      self.safety.set_timer(1_000_000 + tick * 10000)
      self.safety.set_aol_test_heartbeat(True)
      self.rx(0xAA, bytes([0x1A, 0x6F] * 4))
      self.rx(0x260, bytes(8), True)
      self.rx(0x1D2, bytes([16]) + bytes(7), True)
      self.rx(0x226, bytes(8))
      if tick % 3 == 0:
        self.rx(0x1D3, bytes([0, 128]) + bytes(6), True)
      if tick % 102 == 0:
        self.rx(0x3BC, bytes(8))
      if tick % 30 == 0:
        self.rx(0x620, bytes(8))
      if tick % 4 == 0:
        self.rx(0x262, bytes(3) + bytes([2]) + bytes(4), True)
      self.safety.aol_set_host_request(1)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    for address, expiry in ((0x1D3, 303031), (0x3BC, 10000000), (0x620, 3333334), (0x262, 400000)):
      self.init()
      self.physical()
      for delta in (expiry, expiry + 1):
        self.safety.set_timer(1_000_000 + delta)
        self.safety.set_aol_test_heartbeat(True)
        # Refresh every source except the source under test.
        for other, data, crc in ((0xAA, bytes([0x1A, 0x6F] * 4), False), (0x260, bytes(8), True),
                                 (0x1D2, bytes([16]) + bytes(7), True), (0x226, bytes(8), False),
                                 (0x1D3, bytes([0, 128]) + bytes(6), True), (0x3BC, bytes(8), False),
                                 (0x620, bytes(8), False), (0x262, bytes(3) + bytes([2]) + bytes(4), True)):
          if other != address:
            self.rx(other, data, crc)
        self.safety.aol_set_host_request(1)
        self.assertEqual(self.safety.aol_get_permission_mask(), int(delta == expiry))
      self.physical()
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)

  def test_selected_bus_and_malformed_source(self):
    for address in (0x1D3, 0x3BC, 0x620, 0x262):
      self.init()
      self.physical()
      self.safety.safety_rx_hook(libsafety_py.make_CANPacket(address, 1, bytes(7)))
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)
      self.safety.safety_rx_hook(libsafety_py.make_CANPacket(address, 0, bytes(7)))
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_exact_profile_admission_and_reset(self):
    for word, ae in ((585, 160), (585, 288), (72, 32), (329, 32), (1097, 32), (73, 33), (73, 289), (73, 416)):
      self.init(word, ae)
      self.physical()
      self.assertEqual(self.safety.aol_get_request_mask(), 0)
    self.init()
    self.physical()
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.init()
    self.safety.aol_set_host_request(3)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)


  def test_prius_filter_axis_permissions_and_tx_laws(self):
    for word, stock in ((4169, False), (4681, True)):
      with self.subTest(word=word):
        self.init(word=word)
        self.physical(cruise=True)
        self.assertEqual(self.safety.aol_get_request_mask(), 1 if stock else 3)
        self.assertEqual(self.safety.aol_get_permission_mask(), 1 if stock else 3)
        for accel, cancel, allowed in ((0, 1, True), (0, 0, not stock), (0.1, 0, not stock),
                                       (-0.1, 0, not stock), (2.1, 0, False), (-3.6, 0, False)):
          message = self.packer.make_can_msg_safety("ACC_CONTROL", 0, {"ACCEL_CMD": accel, "CANCEL_REQ": cancel})
          self.assertEqual(bool(self.safety.safety_tx_hook(message)), allowed)
        for address, bus, length in ((0x750, 0, 8), (0x343, 2, 8), (0x283, 2, 7), (0x411, 2, 8)):
          self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, bytes(length))))
        self.assertTrue(self.safety.safety_rx_hook(self.packer.make_can_msg_safety("ACC_CONTROL", 0, {})))
        self.assertFalse(self.safety.get_relay_malfunction())
        self.assertEqual(self.safety.safety_fwd_hook(2, 0x343), 0)
        self.physical(cruise=True, belt=False)
        self.assertEqual(self.safety.aol_get_permission_mask(), 1)
        for changes in ({"eps": 3}, {"main": False}, {"gear": 32}):
          self.physical(cruise=True, **changes)
          self.assertEqual(self.safety.aol_get_permission_mask(), 0)
          self.physical(cruise=True)
        self.safety.set_timer(1_400_001)
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_prius_filter_exact_experience_and_word_admission(self):
    for word, ae in ((4169, 0), (4169, 160), (4169, 288), (4681, 0), (4681, 160), (4681, 288),
                     (4168, 32), (4170, 32), (4680, 32), (4682, 32)):
      with self.subTest(word=word, ae=ae):
        self.init(word=word, ae=ae)
        self.physical(cruise=True)
        self.assertEqual(self.safety.aol_get_request_mask(), 0)
