#!/usr/bin/env python3
"""
Safety tests for Volvo C1/CMA/SPA.

The safety mode lives at ``opendbc/safety/modes/volvo.h`` and is parameterized
by ``safetyParam``:

  - ``safetyParam == 0``       → CMA platform (Volvo XC40 Recharge)
  - ``safetyParam == VOLVO_FLAG_SPA`` → SPA platform (Volvo S60 Recharge,
    Polestar 2)
  - ``safetyParam == VOLVO_FLAG_C1``  → C1 platform (Volvo V40)

CMA and SPA share LCA/PSCM/etc. addresses on the main and party buses but use
different PT-bus addresses and signal scales. C1 uses the V40's legacy CAN
layout and its own safety allowlist. The tests exercise all three through the
generic ``CarSafetyTest`` harness so divergence between ``carstate.py`` and
``volvo.h`` is caught before running in a car.

Companion to: ``opendbc/car/volvo/carstate.py`` (must agree on thresholds).
"""

import pathlib
import re
import unittest

from opendbc.car.volvo.interface import SAFETY_VOLVO
from opendbc.car.volvo.values import VolvoSafetyFlags
from opendbc.car.volvo.volvocan import create_c1_checksum, create_c1_steering_control
from opendbc.safety.tests.libsafety import libsafety_py
import opendbc.safety.tests.common as common
from opendbc.safety.tests.common import CANPackerSafety


# Must match the flags in opendbc/safety/modes/volvo.h
VOLVO_FLAG_SPA = VolvoSafetyFlags.SPA.value
VOLVO_FLAG_C1 = VolvoSafetyFlags.C1.value

# Must match VOLVO_SPEED_TO_MS in volvo.h and SPEED_TO_MS in carstate.py
VOLVO_SPEED_TO_MS = 0.003977

# Bus layout (must match volvo.h)
VOLVO_MAIN_BUS = 0
VOLVO_PT_BUS = 1
VOLVO_PARTY_BUS = 2

# Shared platform-independent addresses
VOLVO_SPEED         = 0x60
VOLVO_LCA_STEER     = 0x58
VOLVO_LCA_2         = 0x69
VOLVO_LCA_3         = 0x57
VOLVO_LCA_4         = 0x90
VOLVO_LCA_5         = 0x67
VOLVO_LCA_6         = 0x97
VOLVO_LCA_7         = 0x92
VOLVO_PSCM          = 0x16
VOLVO_PSCM_RELATED  = 0x17
VOLVO_SAS           = 0x55
VOLVO_DRIVER_INPUT  = 0x15

# Addresses panda TX'd with .check_relay = true, grouped by bus
_TX_PARTY_BUS_ADDRS = (
  VOLVO_LCA_STEER, VOLVO_LCA_2, VOLVO_LCA_3, VOLVO_LCA_4,
  VOLVO_LCA_5, VOLVO_LCA_6, VOLVO_LCA_7,
)
_TX_MAIN_BUS_ADDRS = (VOLVO_PSCM, VOLVO_PSCM_RELATED)


class TestVolvoSafetyBase(common.CarSafetyTest):
  """Shared RX/TX/relay tests for both CMA and SPA.

  Subclasses pin down the PT-bus DBC and per-platform gas/cruise encoding.
  """

  TX_MSGS = (
    [[a, VOLVO_PARTY_BUS] for a in _TX_PARTY_BUS_ADDRS]
    + [[a, VOLVO_MAIN_BUS] for a in _TX_MAIN_BUS_ADDRS]
  )
  RELAY_MALFUNCTION_ADDRS = {
    VOLVO_PARTY_BUS: _TX_PARTY_BUS_ADDRS,
    VOLVO_MAIN_BUS: _TX_MAIN_BUS_ADDRS,
  }
  # volvo.h installs no custom fwd hook, so the panda uses the default main<->party
  # forwarding (bus 0 <-> bus 2). For each TX addr with .check_relay=true, the panda
  # automatically refuses to forward from the bus where stock traffic lives TO the
  # bus where openpilot is TX'ing — that's what keeps the stock ECU from fighting us.
  FWD_BLACKLISTED_ADDRS = {
    VOLVO_MAIN_BUS: list(_TX_PARTY_BUS_ADDRS),   # stock on 0 must not forward to 2
    VOLVO_PARTY_BUS: list(_TX_MAIN_BUS_ADDRS),   # stock on 2 must not forward to 0
  }
  STANDSTILL_THRESHOLD = 0.1  # m/s, matches volvo.h

  # Subclasses set these
  SAFETY_PARAM: int = 0
  PT_DBC: str = ""

  MID_DBC = "volvo_mid_1"

  @classmethod
  def setUpClass(cls):
    if cls.__name__ == "TestVolvoSafetyBase":
      cls.safety = None
      raise unittest.SkipTest
    super().setUpClass()

  def setUp(self):
    self.pt_packer = CANPackerSafety(self.PT_DBC)
    self.mid_packer = CANPackerSafety(self.MID_DBC)
    # CarSafetyTest.packer is referenced by a few generic tests; point it at
    # the mid-bus DBC since most shared messages live there.
    self.packer = self.mid_packer
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(SAFETY_VOLVO, self.SAFETY_PARAM)
    self.safety.init_tests()

  def test_tx_hook_on_wrong_safety_mode(self):
    # CMA and SPA intentionally share the party-bus TX allowlist. safetyParam
    # selects the PT-bus RX encodings, not a different set of steering frames.
    self.skipTest("CMA and SPA intentionally share Volvo TX IDs")

  # ---- Abstract methods from CarSafetyTest ----

  def _user_brake_msg(self, brake):
    # volvo.h reads BRAKE_PEDAL_PRESSED_B (bit 46, factor 1, active high)
    values = {"BRAKE_PEDAL_PRESSED_B": 1 if brake else 0}
    return self.mid_packer.make_can_msg_safety("LCA_2", VOLVO_MAIN_BUS, values)

  def _speed_msg(self, speed):
    # Main-bus SPEED, the same message on both platforms. The DBC carries it as
    # raw counts (factor 1) and volvo.h applies VOLVO_SPEED_TO_MS, so convert here.
    values = {"SPEED": round(speed / VOLVO_SPEED_TO_MS)}
    return self.mid_packer.make_can_msg_safety("SPEED", VOLVO_MAIN_BUS, values)

  def _speed_msg_2(self, speed):
    # Volvo's safety mode only consumes a single vehicle-speed source, so the
    # generic rx_hook_speed_mismatch test doesn't apply. Returning None asks
    # the harness to skip it (see common.CarSafetyTest.test_rx_hook_speed_mismatch).
    return None

  def _angle_meas_msg(self, angle):
    return self.mid_packer.make_can_msg_safety(
      "PSCM", VOLVO_PARTY_BUS, {"PSCM_ANGLE_SENSOR": angle})

  def _angle_cmd_msg(self, angle):
    return self.mid_packer.make_can_msg_safety(
      "LCA_5", VOLVO_PARTY_BUS, {"LCA_5_STEER": angle})

  def _reset_angle_measurement(self, angle):
    for _ in range(common.MAX_SAMPLE_VALS):
      self._rx(self._angle_meas_msg(angle))

  def _reset_speed_measurement(self, speed):
    for _ in range(common.MAX_SAMPLE_VALS):
      self._rx(self._speed_msg(speed))

  def test_angle_tx_is_bounded(self):
    """The LCA_5 angle command must obey the measured-angle safety envelope."""
    self._reset_angle_measurement(0)
    self._reset_speed_measurement(10)

    self.safety.set_controls_allowed(True)
    self.safety.set_desired_angle_last(0)
    self.assertTrue(self._tx(self._angle_cmd_msg(0)))

    # The software controller's ±540 degree envelope is also enforced by the
    # panda. Set the previous command explicitly so this test isolates the
    # absolute bound from the rate limiter.
    angle_can = round(540 / 0.05596)
    self.safety.set_desired_angle_last(angle_can)
    self.assertTrue(self._tx(self._angle_cmd_msg(540)))
    self.safety.set_desired_angle_last(0)
    self.assertFalse(self._tx(self._angle_cmd_msg(541)))

  def test_angle_tx_follows_measurement_when_controls_disabled(self):
    self._reset_angle_measurement(10)
    self.safety.set_controls_allowed(False)

    self.assertTrue(self._tx(self._angle_cmd_msg(10)))
    self.assertFalse(self._tx(self._angle_cmd_msg(20)))

  def test_angle_tx_rate_matches_controller_cadence(self):
    """LCA_5 is 50 Hz, so each frame may contain two 100 Hz controller steps."""
    self._reset_speed_measurement(50)
    self.safety.set_controls_allowed(True)

    self.safety.set_desired_angle_last(0)
    self.assertTrue(self._tx(self._angle_cmd_msg(0.4)))

    self.safety.set_desired_angle_last(round(0.4 / 0.05596))
    self.assertFalse(self._tx(self._angle_cmd_msg(0.9)))

  def test_lca_authority_is_bounded(self):
    self.safety.set_controls_allowed(True)
    valid = {
      "LCA_STEER_LOOSELY": 614,
      "LCA_STEER_LOOSELY_INV": -614,
      "LCA_STEER": 0,
    }
    self.assertTrue(self._tx(self.mid_packer.make_can_msg_safety(
      "LCA", VOLVO_PARTY_BUS, valid)))

    for key, value in (("LCA_STEER_LOOSELY", 615),
                       ("LCA_STEER_LOOSELY_INV", -615)):
      invalid = valid | {key: value}
      self.assertFalse(self._tx(self.mid_packer.make_can_msg_safety(
        "LCA", VOLVO_PARTY_BUS, invalid)))

  def test_pscm_relay_cannot_invent_angle(self):
    self._reset_angle_measurement(10)
    valid = self.mid_packer.make_can_msg_safety(
      "PSCM", VOLVO_MAIN_BUS, {"PSCM_ANGLE_SENSOR": 10})
    invalid = self.mid_packer.make_can_msg_safety(
      "PSCM", VOLVO_MAIN_BUS, {"PSCM_ANGLE_SENSOR": 20})
    self.assertTrue(self._tx(valid))
    self.assertFalse(self._tx(invalid))

  def test_driver_input_is_a_normal_override(self):
    def driver_input_msg(value):
      return self.mid_packer.make_can_msg_safety(
        "DRIVER_INPUT", VOLVO_PARTY_BUS, {"STEERING_DRIVER_INPUT": value})

    for value in (2, 3, 5, 6, 20, -20):
      self._rx(driver_input_msg(0))
      self.safety.set_controls_allowed(True)
      self._rx(driver_input_msg(value))
      self.assertTrue(self.safety.get_controls_allowed(), f"unexpected safety disengage at {value=}")
      self.assertFalse(self.safety.get_steering_disengage_prev())

  # ---- Volvo-specific consistency tests ----

  def test_tx_hook_wrong_bus_blocked(self):
    """
    Every TX address is pinned to exactly one bus by the VOLVO_TX_MSGS
    allowlist, which safety_tx_hook() enforces before volvo_tx_hook() runs.
    TX attempts anywhere off the allowlisted bus must be rejected, even with
    controls allowed. Also covers the relayed-RX addresses (SAS, DRIVER_INPUT)
    that volvo_tx_hook() used to re-check: they are not TX'able on any bus.
    """
    tx_msgs = {tuple(m) for m in self.TX_MSGS}
    addrs = {addr for addr, _ in tx_msgs} | {VOLVO_SAS, VOLVO_DRIVER_INPUT}
    self.safety.set_controls_allowed(True)
    for addr in sorted(addrs):
      for bus in range(4):
        if (addr, bus) in tx_msgs:
          self.assertTrue(self._tx(common.make_msg(bus, addr)),
                          f"blocked TX addr={hex(addr)} on allowlisted bus={bus}")
        else:
          self.assertFalse(self._tx(common.make_msg(bus, addr)),
                           f"allowed TX addr={hex(addr)} on wrong bus={bus}")

  def test_gas_threshold_self_consistent(self):
    """
    Sanity: the panda's gas_pressed edge is exactly where GAS_PRESSED_THRESHOLD
    is defined. Regression guard for the CMA-vs-SPA scale mismatch bug where
    carstate.py applied CMA thresholds (raw 0-255) to SPA's DBC-scaled percent.
    If you change the threshold in volvo.h, update carstate.py AND this test.
    """
    # Just below threshold → not pressed. Use a value strictly less than threshold.
    just_below = max(self.GAS_PRESSED_THRESHOLD - 1, 0)
    self._rx(self._user_gas_msg(just_below))
    self.assertFalse(self.safety.get_gas_pressed_prev(),
                     f"gas flagged at {just_below} (threshold={self.GAS_PRESSED_THRESHOLD})")

    # Just above threshold → pressed.
    self._rx(self._user_gas_msg(self.GAS_PRESSED_THRESHOLD + 1))
    self.assertTrue(self.safety.get_gas_pressed_prev(),
                    f"gas not flagged above {self.GAS_PRESSED_THRESHOLD}")

  def test_speed_scale_self_consistent(self):
    """
    The main-bus SPEED LSB is written out in three places: volvo.h, carstate.py
    and this file. They must agree, or the panda and openpilot disagree about
    vehicle speed. Parsed as text so this holds without importing either.
    """
    root = pathlib.Path(__file__).parents[3]
    sources = {
      "volvo.h": (root / "opendbc/safety/modes/volvo.h",
                  r"#define\s+VOLVO_SPEED_TO_MS\s+([0-9.]+)f?"),
      "carstate.py": (root / "opendbc/car/volvo/carstate.py",
                      r"^SPEED_TO_MS\s*=\s*([0-9.]+)"),
    }
    for name, (path, pattern) in sources.items():
      m = re.search(pattern, path.read_text(), re.MULTILINE)
      self.assertIsNotNone(m, f"could not find the speed LSB in {name}")
      self.assertEqual(float(m.group(1)), VOLVO_SPEED_TO_MS,
                       f"{name} speed LSB disagrees with test_volvo.py")


class TestVolvoCMA(TestVolvoSafetyBase):
  """
  Volvo CMA: XC40 Recharge.

  ECM_1.ACCELERATOR_PEDAL_POS is raw 0-255 (DBC factor 1). Idle is ~20; panda
  fires gas_pressed above 21. carstate.py uses the same raw threshold.
  """
  SAFETY_PARAM = 0
  PT_DBC = "volvo_front_1_cma"
  GAS_PRESSED_THRESHOLD = 21  # raw counts

  def _user_gas_msg(self, gas):
    values = {"ACCELERATOR_PEDAL_POS": gas}
    return self.pt_packer.make_can_msg_safety("ECM_1", VOLVO_PT_BUS, values)

  def _pcm_status_msg(self, enable):
    # CMA cruise is a pair of bools; either one being high enables cruise.
    values = {"CRUISE_CONTROL_ENABLED": 1 if enable else 0,
              "CRUISE_CONTROL_ENABLED_IDLE_TRAFFIC": 0}
    return self.pt_packer.make_can_msg_safety(
      "BUS1_CRUISE_CONTROL", VOLVO_PT_BUS, values)


class TestVolvoSPA(TestVolvoSafetyBase):
  """
  Volvo SPA: S60 Recharge, Polestar 2.

  ECM_1.ACCELERATOR_PEDAL_POS is DBC-scaled to percent (factor 0.00390625,
  range 0-100%). Idle is ~0; panda fires gas_pressed above 1.0%.
  carstate.py MUST use the same percent-based threshold — see
  opendbc/car/volvo/carstate.py. A mismatch here manifests in test_models.py
  as persistent ``panda safety doesn't agree with openpilot: {'gasPressed': N}``.
  """
  SAFETY_PARAM = VOLVO_FLAG_SPA
  PT_DBC = "volvo_front_1_spa"
  GAS_PRESSED_THRESHOLD = 1.0  # percent

  def _user_gas_msg(self, gas):
    values = {"ACCELERATOR_PEDAL_POS": gas}
    return self.pt_packer.make_can_msg_safety("ECM_1", VOLVO_PT_BUS, values)

  def _pcm_status_msg(self, enable):
    # SPA cruise signal has DBC factor -1 offset 1, so the "enabled" DBC value
    # is 1 (which encodes as raw bit 0 — panda inverts it).
    values = {"CRUISE_CONTROL_SPA_ENABLED": 1 if enable else 0}
    return self.pt_packer.make_can_msg_safety(
      "BUS1_CRUISE_CONTROL", VOLVO_PT_BUS, values)


class TestVolvoC1(common.CarSafetyTest, common.AngleSteeringSafetyTest):
  TX_MSGS = [[0xD0, VOLVO_MAIN_BUS], [0x125, VOLVO_PARTY_BUS], [0x10, VOLVO_MAIN_BUS]]
  RELAY_MALFUNCTION_ADDRS = {
    VOLVO_MAIN_BUS: (0xD0,),
    VOLVO_PARTY_BUS: (0x125,),
  }
  FWD_BLACKLISTED_ADDRS = {
    VOLVO_MAIN_BUS: [0x125],
    VOLVO_PARTY_BUS: [0xD0],
  }
  STANDSTILL_THRESHOLD = 0.1
  GAS_PRESSED_THRESHOLD = 5.0

  STEER_ANGLE_MAX = 359.9
  STEER_ANGLE_TEST_MAX = 350.0
  DEG_TO_CAN = 1 / 0.04395
  ANGLE_RATE_BP = [7.0, 17.0, 36.0]
  ANGLE_RATE_UP = [2.0, 0.25, 0.1]
  ANGLE_RATE_DOWN = [2.0, 0.25, 0.1]

  def setUp(self):
    self.packer = CANPackerSafety("volvo_v40_2017_pt")
    self.safety = libsafety_py.libsafety
    self.safety.set_safety_hooks(SAFETY_VOLVO, VOLVO_FLAG_C1)
    self.safety.init_tests()

  def _angle_cmd_msg(self, angle: float, enabled: bool, increment_timer: bool = True):
    values = {
      "SET_X_E3": 0xE3,
      "SET_X_B4": 0xB4,
      "SET_X_08": 0x08,
      "LKAAngleReq": angle,
      "LKASteerDirection": 3 if enabled else 0,
      "TrqLim": 0,
      "SET_X_25": 0x25,
      "SET_X_02": 0x02,
    }

    def fix_checksum(msg):
      address, data, bus = msg
      data = bytearray(data)
      data[6] = create_c1_checksum(data)
      return address, data, bus

    return self.packer.make_can_msg_safety("FSM1", VOLVO_MAIN_BUS, values, fix_checksum)

  def _angle_meas_msg(self, angle: float):
    return self.packer.make_can_msg_safety(
      "PSCM1", VOLVO_MAIN_BUS, {"SteeringAngleServo": angle})

  def _speed_msg(self, speed):
    return self.packer.make_can_msg_safety(
      "VehicleSpeed1", VOLVO_MAIN_BUS, {"VehicleSpeed": speed * 3.6})

  def _speed_msg_2(self, speed):
    return None

  def _user_brake_msg(self, brake):
    return self.packer.make_can_msg_safety(
      "PedalandBrake", VOLVO_MAIN_BUS, {"BrakePedalActive2": bool(brake)})

  def _user_gas_msg(self, gas):
    return self.packer.make_can_msg_safety(
      "PedalandBrake", VOLVO_MAIN_BUS, {"AccPedal": gas})

  def _pcm_status_msg(self, enable):
    return self.packer.make_can_msg_safety(
      "FSM0", VOLVO_PARTY_BUS, {"ACCStatusActive": bool(enable)})

  def test_cancel_button_only(self):
    allowed = self.packer.make_can_msg_safety(
      "CCButtons", VOLVO_MAIN_BUS, {"ACCStopBtn": 1})
    self.assertTrue(self._tx(allowed))

    for signal in ("ACCOnOffBtn", "ACCSetBtn", "ACCResumeBtn", "ACCMinusBtn",
                   "TimeGapIncreaseBtn", "TimeGapDecreaseBtn"):
      msg = self.packer.make_can_msg_safety("CCButtons", VOLVO_MAIN_BUS, {signal: 1})
      self.assertFalse(self._tx(msg), signal)

  def test_pscm_relay_cannot_invent_angle(self):
    for _ in range(common.MAX_SAMPLE_VALS):
      self._rx(self._angle_meas_msg(10))
    valid = self.packer.make_can_msg_safety(
      "PSCM1", VOLVO_PARTY_BUS, {"SteeringAngleServo": 10})
    invalid = self.packer.make_can_msg_safety(
      "PSCM1", VOLVO_PARTY_BUS, {"SteeringAngleServo": 20})
    self.assertTrue(self._tx(valid))
    self.assertFalse(self._tx(invalid))

  def test_pscm_relay_preserves_full_lock_angle(self):
    for angle in (-720, 500):
      for _ in range(common.MAX_SAMPLE_VALS):
        self._rx(self._angle_meas_msg(angle))
      relayed = self.packer.make_can_msg_safety(
        "PSCM1", VOLVO_PARTY_BUS, {"SteeringAngleServo": angle})
      self.assertTrue(self._tx(relayed), angle)

  def test_steering_static_fields_and_checksum(self):
    self.safety.set_controls_allowed(True)
    self._reset_angle_measurement(0)
    self._reset_speed_measurement(10)
    self._set_prev_desired_angle(0)
    valid = self._angle_cmd_msg(0, True)
    self.assertTrue(self._tx(valid))

    for byte_index in (0, 1, 2, 3, 4, 6, 7):
      invalid = self._angle_cmd_msg(0, True)
      invalid[0].data[byte_index] ^= 0x4 if byte_index in (4, 7) else 0x1
      self.assertFalse(self._tx(invalid), byte_index)

  def test_controller_steering_message_is_allowed(self):
    self.safety.set_controls_allowed(True)
    self._reset_angle_measurement(0)
    self._reset_speed_measurement(10)
    self._set_prev_desired_angle(0)
    address, data, bus = create_c1_steering_control(self.packer, 0, True)
    self.assertTrue(self._tx(libsafety_py.make_CANPacket(address, bus, data)))


if __name__ == "__main__":
  unittest.main()
