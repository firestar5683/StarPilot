import unittest

from opendbc.car import structs
from opendbc.car.subaru.carcontroller import CarController
from opendbc.car.subaru.carstate import CarState
from opendbc.car.subaru.interface import CarInterface
from opendbc.car.subaru.values import CAR, DBC, SubaruFlags, SubaruSafetyFlags
from opendbc.car.subaru import subarucan
from opendbc.safety.tests.test_subaru_gen2_angle_pair import TestSubaruGen2AnglePair


class TestAscentLkasAlert(unittest.TestCase):
  def params(self, car=CAR.SUBARU_ASCENT_2023, bus=2, length=8):
    fingerprint = {0: {}, 1: {}, 2: {}}
    fingerprint[bus][0x3C4] = length
    return CarInterface.get_params(car, fingerprint, [], False, False, False)

  def test_platform_bus_length_gate_preserves_native_identity(self):
    for car in CAR:
      cp = self.params(car)
      self.assertEqual(bool(cp.flags & SubaruFlags.ASCENT_LKAS_ALERT), car == CAR.SUBARU_ASCENT_2023)
      self.assertEqual(bool(cp.safetyConfigs[0].safetyParam & SubaruSafetyFlags.ASCENT_LKAS_ALERT), car == CAR.SUBARU_ASCENT_2023)
    for bus, length in ((0, 8), (1, 8), (2, 4), (2, 16)):
      cp = self.params(bus=bus, length=length)
      self.assertFalse(cp.flags & SubaruFlags.ASCENT_LKAS_ALERT)
      self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xB1)
    self.assertEqual(self.params().safetyConfigs[0].safetyParam, 0x8B1)

  def test_production_parser_state_controller_and_actual_request(self):
    cp = self.params()
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    state.update(parsers)
    _, frames = TestSubaruGen2AnglePair.sources(CAR.SUBARU_ASCENT_2023)
    raw = bytes.fromhex("ce02000104000000")
    frames.append((0x3C4, raw, 2))
    for parser in parsers.values():
      parser.update([(1_000_000_000, frames)])
    state.out = state.update(parsers)
    self.assertEqual(state.es_lkas_alert_dat, raw)
    controller = CarController(DBC[cp.carFingerprint], cp)
    cc = structs.CarControl()
    cc.enabled = cc.latActive = True
    _, sends = controller.update(cc.as_reader(), state, 1_000_000_000)
    self.assertEqual(next(msg for msg in sends if msg[0] == 0x3C4)[1], raw)
    self.assertIsNone(controller._ascent_lkas_alert(cc, state))
    controller.angle_was_active = True
    for counter in (3, 15, 0):
      dat = bytearray(raw)
      dat[1] = counter | 0xA0
      dat[0] = (0xC4 + 3 + sum(dat[1:])) & 0xFF
      state.es_lkas_alert_dat = bytes(dat)
      msg = controller._ascent_lkas_alert(cc, state)
      self.assertEqual(msg[1][1], dat[1])
      self.assertEqual(msg[1][2:], bytes(6))
      self.assertIsNone(controller._ascent_lkas_alert(cc, state))

  def test_only_known_hands_on_pattern_masked(self):
    raw = bytes.fromhex("ce02000104000000")
    for active, alert, masked in ((True, 0, True), (False, 0, False), (True, structs.CarControl.HUDControl.VisualAlert.steerRequired, False)):
      msg = subarucan.create_ascent_lkas_alert(raw, active, alert)
      self.assertEqual(msg[1][2:], bytes(6) if masked else raw[2:])
    for payload in ("000000110000", "1e0030000000", "000704000000", "190000010000", "010104000000"):
      dat = bytearray(bytes.fromhex("0002" + payload))
      dat[0] = (0xC4 + 3 + sum(dat[1:])) & 0xFF
      self.assertEqual(subarucan.create_ascent_lkas_alert(bytes(dat), True, 0)[1], dat)
    for dat in (b"", bytes(7), bytes(9), bytes.fromhex("0002000104000000")):
      self.assertIsNone(subarucan.create_ascent_lkas_alert(dat, True, 0))
