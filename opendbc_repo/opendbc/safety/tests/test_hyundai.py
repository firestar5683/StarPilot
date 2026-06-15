#!/usr/bin/env python3
import random
import unittest

from opendbc.car.hyundai.values import HyundaiSafetyFlags, HyundaiStarPilotSafetyFlags
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py
import opendbc.safety.tests.common as common
from opendbc.safety.tests.common import CANPackerSafety
from opendbc.safety.tests.hyundai_common import Buttons, HyundaiAolLkasOnEngageBase, HyundaiAolLkasOnEngageStockBase, HyundaiButtonBase, HyundaiLongitudinalBase


# 4 bit checkusm used in some hyundai messages
# lives outside the can packer because we never send this msg
def checksum(msg):
  addr, dat, bus = msg

  chksum = 0
  if addr == 0x386:
    for i, b in enumerate(dat):
      for j in range(8):
        # exclude checksum and counter bits
        if (i != 1 or j < 6) and (i != 3 or j < 6) and (i != 5 or j < 6) and (i != 7 or j < 6):
          bit = (b >> j) & 1
        else:
          bit = 0
        chksum += bit
    chksum = (chksum ^ 9) & 0xF
    ret = bytearray(dat)
    ret[5] |= (chksum & 0x3) << 6
    ret[7] |= (chksum & 0xc) << 4
  else:
    for i, b in enumerate(dat):
      if addr in [0x260, 0x421] and i == 7:
        b &= 0x0F if addr == 0x421 else 0xF0
      elif addr == 0x394 and i == 6:
        b &= 0xF0
      elif addr == 0x394 and i == 7:
        continue
      chksum += sum(divmod(b, 16))
    chksum = (16 - chksum) % 16
    ret = bytearray(dat)
    ret[6 if addr == 0x394 else 7] |= chksum << (4 if addr == 0x421 else 0)

  return addr, ret, bus


class TestHyundaiSafety(HyundaiButtonBase, common.CarSafetyTest, common.DriverTorqueSteeringSafetyTest, common.SteerRequestCutSafetyTest):
  TX_MSGS = [[0x340, 0], [0x4F1, 0], [0x485, 0]]
  STANDSTILL_THRESHOLD = 12  # 0.375 kph
  RELAY_MALFUNCTION_ADDRS = {0: (0x340, 0x485)}  # LKAS11
  FWD_BLACKLISTED_ADDRS = {2: [0x340, 0x485]}

  MAX_RATE_UP = 3
  MAX_RATE_DOWN = 7
  MAX_TORQUE_LOOKUP = [0], [384]
  MAX_RT_DELTA = 112
  DRIVER_TORQUE_ALLOWANCE = 50
  DRIVER_TORQUE_FACTOR = 2

  # Safety around steering req bit
  MIN_VALID_STEERING_FRAMES = 89
  MAX_INVALID_STEERING_FRAMES = 2

  cnt_gas = 0
  cnt_speed = 0
  cnt_brake = 0
  cnt_cruise = 0
  cnt_button = 0

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai, 0)
    self.safety.init_tests()

  def _button_msg(self, buttons, main_button=0, bus=0):
    values = {"CF_Clu_CruiseSwState": buttons, "CF_Clu_CruiseSwMain": main_button, "CF_Clu_AliveCnt1": self.cnt_button}
    self.__class__.cnt_button += 1
    return self.packer.make_can_msg_safety("CLU11", bus, values)

  def _user_gas_msg(self, gas):
    values = {"CF_Ems_AclAct": gas, "AliveCounter": self.cnt_gas % 4}
    self.__class__.cnt_gas += 1
    return self.packer.make_can_msg_safety("EMS16", 0, values, fix_checksum=checksum)

  def _user_brake_msg(self, brake):
    values = {"DriverOverride": 2 if brake else random.choice((0, 1, 3)),
              "AliveCounterTCS": self.cnt_brake % 8}
    self.__class__.cnt_brake += 1
    return self.packer.make_can_msg_safety("TCS13", 0, values, fix_checksum=checksum)

  def _speed_msg(self, speed):
    # safety doesn't scale, so undo the scaling
    values = {"WHL_SPD_%s" % s: speed * 0.03125 for s in ["FL", "FR", "RL", "RR"]}
    values["WHL_SPD_AliveCounter_LSB"] = (self.cnt_speed % 16) & 0x3
    values["WHL_SPD_AliveCounter_MSB"] = (self.cnt_speed % 16) >> 2
    self.__class__.cnt_speed += 1
    return self.packer.make_can_msg_safety("WHL_SPD11", 0, values, fix_checksum=checksum)

  def _pcm_status_msg(self, enable):
    values = {"ACCMode": enable, "CR_VSM_Alive": self.cnt_cruise % 16}
    self.__class__.cnt_cruise += 1
    return self.packer.make_can_msg_safety("SCC12", self.SCC_BUS, values, fix_checksum=checksum)

  def _acc_state_msg(self, main_on):
    dat = bytearray(8)
    dat[0] = int(main_on)
    return libsafety_py.make_CANPacket(0x420, self.SCC_BUS, bytes(dat))

  def _torque_driver_msg(self, torque):
    values = {"CR_Mdps_StrColTq": torque}
    return self.packer.make_can_msg_safety("MDPS12", 0, values)

  def _torque_cmd_msg(self, torque, steer_req=1):
    values = {"CR_Lkas_StrToqReq": torque, "CF_Lkas_ActToi": steer_req}
    return self.packer.make_can_msg_safety("LKAS11", 0, values)

  def test_pcm_main_cruise_state_availability(self):
    if self.safety.get_current_safety_param() & HyundaiSafetyFlags.LONG:
      raise unittest.SkipTest("Longitudinal mode does not learn ACC main state from SCC11 RX")
    if self.safety.get_current_safety_mode() == CarParams.SafetyModel.hyundaiLegacy:
      raise unittest.SkipTest("Legacy Hyundai safety does not track ACC main state from SCC11 RX")

    for should_turn_acc_main_on in (True, False):
      self._rx(self._acc_state_msg(should_turn_acc_main_on))
      self.assertEqual(should_turn_acc_main_on, self.safety.get_acc_main_on())


class TestHyundaiSafetyAltLimits(TestHyundaiSafety):
  MAX_RATE_UP = 2
  MAX_RATE_DOWN = 3
  MAX_TORQUE_LOOKUP = [0], [270]

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai, HyundaiSafetyFlags.ALT_LIMITS)
    self.safety.init_tests()


class TestHyundaiSafetyAltLimits2(TestHyundaiSafety):
  MAX_RATE_UP = 2
  MAX_RATE_DOWN = 3
  MAX_TORQUE_LOOKUP = [0], [170]

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai, HyundaiSafetyFlags.ALT_LIMITS_2)
    self.safety.init_tests()


class TestHyundaiSafetyCameraSCC(TestHyundaiSafety):
  BUTTONS_TX_BUS = 2  # tx on 2, rx on 0
  SCC_BUS = 2  # rx on 2

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai, HyundaiSafetyFlags.CAMERA_SCC)
    self.safety.init_tests()


class TestHyundaiSafetyNonScc(TestHyundaiSafety):
  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai, HyundaiSafetyFlags.NON_SCC)
    self.safety.init_tests()

  def _user_gas_msg(self, gas):
    dat = bytearray(8)
    cruise_active = self.safety.get_controls_allowed() or self.safety.get_cruise_engaged_prev()
    acc_main_on = self.safety.get_acc_main_on() or cruise_active
    dat[3] |= int(acc_main_on) << 1
    dat[3] |= int(cruise_active) << 2
    dat[7] = ((self.cnt_gas % 4) << 4) | (0x40 if gas else 0x00)
    self.__class__.cnt_gas += 1
    _, dat, bus = checksum((0x260, dat, 0))
    return libsafety_py.make_CANPacket(0x260, bus, bytes(dat))

  def _acc_state_msg(self, main_on):
    dat = bytearray(8)
    dat[3] |= int(main_on) << 1
    dat[7] |= (self.cnt_cruise % 4) << 4
    self.__class__.cnt_cruise += 1
    _, dat, bus = checksum((0x260, dat, 0))
    return libsafety_py.make_CANPacket(0x260, bus, bytes(dat))

  def _pcm_status_msg(self, enable):
    dat = bytearray(8)
    dat[3] |= int(enable) << 1
    dat[3] |= int(enable) << 2
    dat[7] |= (self.cnt_cruise % 4) << 4
    self.__class__.cnt_cruise += 1
    _, dat, bus = checksum((0x260, dat, 0))
    return libsafety_py.make_CANPacket(0x260, bus, bytes(dat))

  def test_non_scc_uses_live_acc_state_rx_checks(self):
    self._rx(self._user_gas_msg(False))
    self._rx(self._torque_driver_msg(0))
    self._rx(self._speed_msg(0))
    self._rx(self._user_brake_msg(False))
    self._rx(self._button_msg(Buttons.NONE))
    self._rx(self._pcm_status_msg(False))
    self.assertTrue(self.safety.safety_config_valid())


class TestHyundaiCanCanfdBlendedSafety(TestHyundaiSafety):
  TX_MSGS = [[0x340, 0], [0x4F1, 0], [0x485, 0], [0x364, 0]]
  RELAY_MALFUNCTION_ADDRS = {0: (0x340, 0x485, 0x364)}
  FWD_BLACKLISTED_ADDRS = {2: [0x340, 0x485, 0x364]}
  MAX_RATE_UP = 2
  MAX_RATE_DOWN = 3
  MAX_TORQUE_LOOKUP = [0], [404]

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_palisade_2023_generated")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai, HyundaiSafetyFlags.CAN_CANFD_BLENDED)
    self.safety.init_tests()

  def _pcm_status_msg(self, enable):
    values = {"ACCMode": enable, "COUNTER": self.cnt_cruise % 16}
    self.__class__.cnt_cruise += 1
    return self.packer.make_can_msg_panda("SCC12", 0, values)

  def _acc_state_msg(self, main_on):
    dat = bytearray(8)
    dat[3] = int(main_on) << 3
    return libsafety_py.make_CANPacket(0x420, 0, bytes(dat))


class TestHyundaiSafetyFCEV(TestHyundaiSafety):
  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai, HyundaiSafetyFlags.FCEV_GAS)
    self.safety.init_tests()

  def _user_gas_msg(self, gas):
    values = {"ACCELERATOR_PEDAL": gas}
    return self.packer.make_can_msg_safety("FCEV_ACCELERATOR", 0, values)


class TestHyundaiLegacySafety(TestHyundaiSafety):
  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiLegacy, 0)
    self.safety.init_tests()


class TestHyundaiLegacySafetyEV(TestHyundaiSafety):
  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiLegacy, HyundaiSafetyFlags.EV_GAS)
    self.safety.init_tests()

  def _user_gas_msg(self, gas):
    values = {"Accel_Pedal_Pos": gas}
    return self.packer.make_can_msg_safety("E_EMS11", 0, values, fix_checksum=checksum)


class TestHyundaiLegacySafetyHEV(TestHyundaiSafety):
  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiLegacy, HyundaiSafetyFlags.HYBRID_GAS)
    self.safety.init_tests()

  def _user_gas_msg(self, gas):
    values = {"CR_Vcu_AccPedDep_Pos": gas}
    return self.packer.make_can_msg_safety("E_EMS11", 0, values, fix_checksum=checksum)


class TestHyundaiLongitudinalSafety(HyundaiLongitudinalBase, TestHyundaiSafety):
  TX_MSGS = [[0x340, 0], [0x4F1, 0], [0x485, 0], [0x420, 0], [0x421, 0], [0x50A, 0], [0x389, 0], [0x4A2, 0], [0x38D, 0], [0x483, 0], [0x7D0, 0]]

  FWD_BLACKLISTED_ADDRS = {2: [0x340, 0x485, 0x421, 0x420, 0x50A, 0x389]}

  RELAY_MALFUNCTION_ADDRS = {0: (0x340, 0x485, 0x421, 0x420, 0x50A, 0x389)}  # LKAS11, LFAHDA_MFC, SCC12, SCC11, SCC13, SCC14

  DISABLED_ECU_UDS_MSG = (0x7D0, 0)
  DISABLED_ECU_ACTUATION_MSG = (0x421, 0)

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai, HyundaiSafetyFlags.LONG)
    self.safety.init_tests()

  def _accel_msg(self, accel, aeb_req=False, aeb_decel=0):
    values = {
      "aReqRaw": accel,
      "aReqValue": accel,
      "AEB_CmdAct": int(aeb_req),
      "CR_VSM_DecCmd": aeb_decel,
    }
    return self.packer.make_can_msg_safety("SCC12", self.SCC_BUS, values)

  def _tx_acc_state_msg(self, main_on):
    dat = bytearray(8)
    dat[0] = int(main_on)
    return libsafety_py.make_CANPacket(0x420, 0, bytes(dat))

  def _fca11_msg(self, idx=0, vsm_aeb_req=False, fca_aeb_req=False, aeb_decel=0):
    values = {
      "CR_FCA_Alive": idx % 0xF,
      "FCA_Status": 2,
      "CR_VSM_DecCmd": aeb_decel,
      "CF_VSM_DecCmdAct": int(vsm_aeb_req),
      "FCA_CmdAct": int(fca_aeb_req),
    }
    return self.packer.make_can_msg_safety("FCA11", 0, values)

  def test_no_aeb_fca11(self):
    self.assertTrue(self._tx(self._fca11_msg()))
    self.assertFalse(self._tx(self._fca11_msg(vsm_aeb_req=True)))
    self.assertFalse(self._tx(self._fca11_msg(fca_aeb_req=True)))
    self.assertFalse(self._tx(self._fca11_msg(aeb_decel=1.0)))

  def test_no_aeb_scc12(self):
    self.assertTrue(self._tx(self._accel_msg(0)))
    self.assertFalse(self._tx(self._accel_msg(0, aeb_req=True)))
    self.assertFalse(self._tx(self._accel_msg(0, aeb_decel=1.0)))


class TestHyundaiCanCanfdBlendedLongitudinalSafety(HyundaiLongitudinalBase, TestHyundaiCanCanfdBlendedSafety):
  TX_MSGS = [[0x340, 0], [0x4F1, 0], [0x485, 0], [0x364, 0], [0x420, 0], [0x421, 0], [0x389, 0], [0x38D, 0], [0x4A2, 0], [0x363, 0], [0x398, 0], [0x7D0, 0]]
  FWD_BLACKLISTED_ADDRS = {2: [0x340, 0x485, 0x364, 0x420, 0x421, 0x389]}
  RELAY_MALFUNCTION_ADDRS = {0: (0x340, 0x485, 0x364, 0x420, 0x421, 0x389)}
  MAX_ACCEL = 3.5

  DISABLED_ECU_UDS_MSG = (0x7D0, 0)
  DISABLED_ECU_ACTUATION_MSG = (0x420, 0)
  CANCEL_BUTTON_ENABLE = True

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_palisade_2023_generated")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai,
                                 HyundaiSafetyFlags.CAN_CANFD_BLENDED | HyundaiSafetyFlags.LONG | HyundaiSafetyFlags.CANCEL_BTN_ENABLE)
    self.safety.init_tests()

  def _accel_msg(self, accel, aeb_req=False, aeb_decel=0):
    values = {
      "aReqRaw": accel,
      "aReqValue": accel,
    }
    return self.packer.make_can_msg_panda("SCC11", 0, values)

  def _tx_acc_state_msg(self, main_on):
    dat = bytearray(8)
    dat[3] = int(main_on) << 3
    return libsafety_py.make_CANPacket(0x420, 0, bytes(dat))

  def test_no_aeb_fca11(self):
    pass

  def test_cancel_button_enables_controls_from_standby(self):
    self.assertFalse(self.safety.get_controls_allowed())

    self._rx(self._button_msg(Buttons.CANCEL))
    self.assertFalse(self.safety.get_controls_allowed())

    self._rx(self._button_msg(Buttons.NONE))
    self.assertTrue(self.safety.get_controls_allowed())


class TestHyundaiLongitudinalSafetyCameraSCC(HyundaiLongitudinalBase, TestHyundaiSafety):
  TX_MSGS = [[0x340, 0], [0x4F1, 2], [0x485, 0], [0x420, 0], [0x421, 0], [0x50A, 0], [0x389, 0], [0x4A2, 0]]

  FWD_BLACKLISTED_ADDRS = {2: [0x340, 0x485, 0x420, 0x421, 0x50A, 0x389]}
  RELAY_MALFUNCTION_ADDRS = {0: (0x340, 0x485, 0x421, 0x420, 0x50A, 0x389)}  # LKAS11, LFAHDA_MFC, SCC12, SCC11, SCC13, SCC14

  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai, HyundaiSafetyFlags.LONG | HyundaiSafetyFlags.CAMERA_SCC)
    self.safety.init_tests()

  def _accel_msg(self, accel, aeb_req=False, aeb_decel=0):
    values = {
      "aReqRaw": accel,
      "aReqValue": accel,
      "AEB_CmdAct": int(aeb_req),
      "CR_VSM_DecCmd": aeb_decel,
    }
    return self.packer.make_can_msg_safety("SCC12", self.SCC_BUS, values)

  def _tx_acc_state_msg(self, main_on):
    dat = bytearray(8)
    dat[0] = int(main_on)
    return libsafety_py.make_CANPacket(0x420, self.SCC_BUS, bytes(dat))

  def test_no_aeb_scc12(self):
    self.assertTrue(self._tx(self._accel_msg(0)))
    self.assertFalse(self._tx(self._accel_msg(0, aeb_req=True)))
    self.assertFalse(self._tx(self._accel_msg(0, aeb_decel=1.0)))

  def test_tester_present_allowed(self):
    pass

  def test_disabled_ecu_alive(self):
    pass


class TestHyundaiSafetyFCEVLong(TestHyundaiLongitudinalSafety, TestHyundaiSafetyFCEV):
  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai, HyundaiSafetyFlags.FCEV_GAS | HyundaiSafetyFlags.LONG)
    self.safety.init_tests()


class TestHyundaiLegacyLongitudinalSafetyHEV(TestHyundaiLongitudinalSafety, TestHyundaiLegacySafetyHEV):
  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiLegacy, HyundaiSafetyFlags.HYBRID_GAS | HyundaiSafetyFlags.LONG)
    self.safety.init_tests()


class TestHyundaiLongitudinalAolLkasOnEngageSafety(HyundaiAolLkasOnEngageBase, TestHyundaiLongitudinalSafety):
  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai,
                                 HyundaiSafetyFlags.LONG | HyundaiStarPilotSafetyFlags.AOL_LKAS_ON_ENGAGE)
    self.safety.init_tests()


class TestHyundaiAolLkasOnEngageStockSafety(HyundaiAolLkasOnEngageStockBase, TestHyundaiSafety):
  def setUp(self):
    self.packer = CANPackerSafety("hyundai_kia_generic")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai, HyundaiStarPilotSafetyFlags.AOL_LKAS_ON_ENGAGE)
    self.safety.init_tests()


if __name__ == "__main__":
  unittest.main()
