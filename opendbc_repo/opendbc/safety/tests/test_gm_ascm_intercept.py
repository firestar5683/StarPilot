import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.carstate import CarState
from opendbc.car.gm.tests.test_ascm_intercept import params
from opendbc.car.gm.values import ASCM_INTERCEPT_CAR, CAR, DBC, GMSafetyFlags
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py


class TestGmAscmIntercept(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.release = self.safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0

  @staticmethod
  def packet(msg):
    return libsafety_py.make_CANPacket(msg[0], msg[2], msg[1])

  def mode(self, cp):
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, cp.safetyConfigs[0].safetyParam), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)

  @staticmethod
  def stock_frames(packer, brake_c9, ev=False, cruise=0):
    frames = [
      packer.make_can_msg("PSCMStatus", 0, {}),
      packer.make_can_msg("EBCMWheelSpdRear", 0, {}),
      packer.make_can_msg("ASCMSteeringButton", 0, {"ACCButtons": 1}),
      packer.make_can_msg("AcceleratorPedal2", 0, {"CruiseState": cruise}),
      packer.make_can_msg("ECMEngineStatus" if brake_c9 else "ECMAcceleratorPos", 0, {}),
    ]
    if ev:
      frames.append(packer.make_can_msg("EBCMRegenPaddle", 0, {}))
    return frames

  def feed(self, frames):
    for frame in frames:
      self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)), hex(frame[0]))
    self.safety.safety_tick()
    self.assertTrue(self.safety.safety_config_valid())

  def controller_frames(self, cp, *, brake_c9=False, radar=False, alpha=False, cancel=False, enabled=True):
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    car_state = CarState(cp)
    parsers = car_state.get_can_parsers(cp)
    car_state.update(parsers)
    sources = self.stock_frames(packer, brake_c9, cp.carFingerprint == CAR.CHEVROLET_VOLT_ASCM, cruise=1 if not alpha else 0)
    parsers[Bus.pt].update([(1_000_000_000, sources)])
    out = car_state.update(parsers)
    self.feed(sources)
    controller = CarController(DBC[cp.carFingerprint], cp)
    controller.frame = 20
    controller.last_steer_frame = 0
    control = structs.CarControl()
    control.enabled = enabled
    control.latActive = enabled
    control.longActive = alpha and enabled
    control.actuators.torque = 0.03
    control.actuators.accel = 0.2
    control.cruiseControl.cancel = cancel
    if cancel:
      controller.cancel_counter = 11
    _, commands = controller.update(control.as_reader(), car_state, 1_100_000_000)
    return packer, sources, out, commands

  def test_stock_controller_and_native_all_eight_both_brake_sources(self):
    for car in ASCM_INTERCEPT_CAR:
      for brake_c9 in (False, True):
        with self.subTest(car=car, brake_c9=brake_c9):
          cp = params(car, accelerator=not brake_c9)
          self.mode(cp)
          _, sources, out, commands = self.controller_frames(cp, brake_c9=brake_c9, cancel=True)
          self.assertTrue(out.cruiseState.enabled)
          self.assertFalse(out.brakePressed)
          self.assertEqual({msg[0] for msg in commands}, {0x180, 0x1E1, 0x184})
          for msg in commands:
            self.assertTrue(self.safety.safety_tx_hook(self.packet(msg)), hex(msg[0]))
          self.assertFalse(self.safety.safety_tx_hook(self.packet((0x2CB, b"\x00" * 8, 0))))
          packer = CANPacker(DBC[car][Bus.pt])
          pressed = packer.make_can_msg("ECMEngineStatus" if brake_c9 else "ECMAcceleratorPos", 0,
                                        {"BrakePressed": 1} if brake_c9 else {"BrakePedalPos": 10})
          self.safety.safety_rx_hook(self.packet(pressed))
          self.assertFalse(self.safety.get_controls_allowed())
          steer = next(msg for msg in commands if msg[0] == 0x180)
          self.assertFalse(self.safety.safety_tx_hook(self.packet(steer)))
          self.mode(cp)
          self.feed(sources)
          self.safety.set_timer(2_100_000)
          self.safety.safety_tick()
          self.assertFalse(self.safety.safety_config_valid())
          self.assertFalse(self.safety.safety_tx_hook(self.packet(steer)))

  def test_alpha_real_controller_frames_and_radar_bus(self):
    for car in ASCM_INTERCEPT_CAR:
      for brake_c9, radar in ((False, False), (False, True), (True, False), (True, True)):
        with self.subTest(car=car, brake_c9=brake_c9, radar=radar):
          cp = params(car, sascm=True, accelerator=not brake_c9,
                      radar=radar, alpha=True)
          self.mode(cp)
          packer, _, _, commands = self.controller_frames(cp, brake_c9=brake_c9, radar=radar, alpha=True)
          self.assertIn(0x2CB, [msg[0] for msg in commands])
          self.assertIn(0x315, [msg[0] for msg in commands])
          self.assertIn(0x180, [msg[0] for msg in commands])
          self.assertFalse(any(msg[2] == 1 for msg in commands))
          # Native alpha arms on a real SET release, after healthy observed RX.
          self.assertTrue(self.safety.safety_rx_hook(self.packet(packer.make_can_msg("ASCMSteeringButton", 0, {"ACCButtons": 3}))))
          self.assertTrue(self.safety.safety_rx_hook(self.packet(packer.make_can_msg("ASCMSteeringButton", 0, {"ACCButtons": 1}))))
          self.assertEqual(self.safety.get_controls_allowed(), not self.release)
          for msg in commands:
            allowed = (msg[0] == 0x184 and car != CAR.CHEVROLET_VOLT_ASCM) or not self.release
            self.assertEqual(self.safety.safety_tx_hook(self.packet(msg)), allowed, hex(msg[0]))
            if msg[2] == 1:
              bad = bytearray(msg[1])
              bad[-1] ^= 1
              self.assertFalse(self.safety.safety_tx_hook(self.packet((msg[0], bytes(bad), 1))))
              self.assertFalse(self.safety.safety_tx_hook(self.packet((msg[0], msg[1], 0))))
              self.assertFalse(self.safety.safety_tx_hook(self.packet((msg[0], msg[1][:-1], 1))))
          active = next(msg for msg in commands if msg[0] == 0x2CB)
          self.assertFalse(self.safety.safety_tx_hook(self.packet((active[0], active[1], 2))))
          self.assertFalse(self.safety.safety_tx_hook(self.packet((active[0], active[1][:-1], active[2]))))
          self.assertTrue(self.safety.safety_rx_hook(self.packet(packer.make_can_msg("ASCMSteeringButton", 0, {"ACCButtons": 6}))))
          self.assertFalse(self.safety.get_controls_allowed())
          self.assertFalse(self.safety.safety_tx_hook(self.packet(active)))
          dashboard = next(msg for msg in commands if msg[0] == 0x370)
          self.assertFalse(self.safety.safety_tx_hook(self.packet(dashboard)))

  def test_source_health_and_brake_variant(self):
    for brake_c9, ev in ((False, False), (True, False), (False, True), (True, True)):
      with self.subTest(brake_c9=brake_c9, ev=ev):
        car = CAR.CHEVROLET_VOLT_ASCM if ev else CAR.GMC_ACADIA_ASCM
        cp = params(car, accelerator=not brake_c9)
        self.mode(cp)
        packer = CANPacker(DBC[car][Bus.pt])
        frames = self.stock_frames(packer, brake_c9, ev)
        for missing in (0xC9 if brake_c9 else 0xBE, 0xBD if ev else 0x1C4):
          self.mode(cp)
          for frame in frames:
            if frame[0] != missing:
              self.safety.safety_rx_hook(self.packet(frame))
          self.safety.safety_tick()
          self.assertFalse(self.safety.safety_config_valid(), hex(missing))
        self.mode(cp)
        self.feed(frames)
        other = packer.make_can_msg("ECMAcceleratorPos" if brake_c9 else "ECMEngineStatus", 0, {})
        self.safety.safety_rx_hook(self.packet(other))
        self.safety.safety_tick()
        self.assertTrue(self.safety.safety_config_valid())
        self.mode(cp)
        for frame in frames:
          self.safety.safety_rx_hook(self.packet((frame[0], frame[1], 1 if frame[0] == missing else 0)))
        self.safety.safety_tick()
        self.assertFalse(self.safety.safety_config_valid())

  def test_alpha_inactive_longitudinal_frames(self):
    cp = params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True, accelerator=False)
    self.mode(cp)
    _, _, _, commands = self.controller_frames(cp, brake_c9=True, alpha=True, enabled=False)
    self.assertFalse(self.safety.get_controls_allowed())
    for addr in (0x2CB, 0x315, 0x370):
      msg = next(frame for frame in commands if frame[0] == addr)
      self.assertEqual(self.safety.safety_tx_hook(self.packet(msg)), not self.release, hex(addr))

  def test_parser_and_native_agree_on_brake_source_and_timeout(self):
    for brake_c9 in (False, True):
      cp = params(CAR.GMC_ACADIA_ASCM, accelerator=not brake_c9)
      self.mode(cp)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      state = CarState(cp)
      parsers = state.get_can_parsers(cp)
      state.update(parsers)
      base = self.stock_frames(packer, brake_c9)
      self.feed(base)
      wrong = packer.make_can_msg("ECMAcceleratorPos" if brake_c9 else "ECMEngineStatus", 0,
                                  {"BrakePedalPos": 10} if brake_c9 else {"BrakePressed": 1})
      parsers[Bus.pt].update([(1_000_000_000, [wrong])])
      self.safety.safety_rx_hook(self.packet(wrong))
      self.assertFalse(state.update(parsers).brakePressed)
      self.assertFalse(self.safety.get_brake_pressed_prev())
      right = packer.make_can_msg("ECMEngineStatus" if brake_c9 else "ECMAcceleratorPos", 0,
                                  {"BrakePressed": 1} if brake_c9 else {"BrakePedalPos": 10})
      parsers[Bus.pt].update([(1_010_000_000, [right])])
      self.safety.safety_rx_hook(self.packet(right))
      self.assertTrue(state.update(parsers).brakePressed)
      self.assertTrue(self.safety.get_brake_pressed_prev())
      self.safety.set_timer(2_100_000)
      self.safety.safety_tick()
      self.assertFalse(self.safety.safety_config_valid())

  def test_frozen_be_lengths_six_seven_eight_only(self):
    cp = params(CAR.CADILLAC_ESCALADE_ASCM)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    base = self.stock_frames(packer, False)
    for length in (5, 6, 7, 8):
      with self.subTest(length=length):
        self.mode(cp)
        for frame in base:
          if frame[0] == 0xBE:
            frame = (frame[0], frame[1][:length].ljust(length, b"\x00"), frame[2])
          self.safety.safety_rx_hook(self.packet(frame))
        self.safety.safety_tick()
        self.assertEqual(self.safety.safety_config_valid(), length in (6, 7, 8))

  def test_release_native_denies_raw_alpha_flag(self):
    cp = params(CAR.GMC_ACADIA_ASCM, sascm=True, alpha=True)
    self.mode(cp)
    # The same test runs with the preloaded DEBUG and RELEASE suite libraries.
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    active = packer.make_can_msg("ASCMActiveCruiseControlStatus", 0, {"ACCAlwaysOne": 1, "ACCAlwaysOne2": 1})
    self.assertEqual(self.safety.safety_tx_hook(self.packet(active)), not self.release)

  def test_stock_alpha_forwarding_relay_and_conflicting_flags(self):
    for alpha in (False, True):
      cp = params(CAR.GMC_ACADIA_ASCM, sascm=True, radar=True, alpha=alpha)
      self.mode(cp)
      for bus, addr, expected in ((0, 0x123, 2), (0, 0x184, -1), (2, 0x123, 0),
                                  (2, 0x180, -1), (2, 0x315, -1 if alpha and not self.release else 0),
                                  (1, 0x123, -1)):
        self.assertEqual(self.safety.safety_fwd_hook(bus, addr), expected)
      self.assertFalse(self.safety.get_relay_malfunction())
      self.safety.safety_rx_hook(self.packet((0x184, b"\x00" * 8, 2)))
      self.assertTrue(self.safety.get_relay_malfunction())
      self.assertEqual(self.safety.safety_fwd_hook(0, 0x123), -1)
      self.assertFalse(self.safety.safety_tx_hook(self.packet((0x184, b"\x00" * 8, 2))))
      self.mode(cp)
      self.safety.safety_rx_hook(self.packet((0x315, b"\x00" * 5, 0)))
      self.assertEqual(self.safety.get_relay_malfunction(), alpha and not self.release)

    cp = params(CAR.GMC_ACADIA_ASCM, sascm=True, radar=True, alpha=True)
    for conflict in (GMSafetyFlags.PEDAL_LONG, GMSafetyFlags.NO_ACC):
      param = cp.safetyConfigs[0].safetyParam | int(conflict)
      self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, param), 0)
      self.safety.init_tests()
      dashboard = CANPacker(DBC[cp.carFingerprint][Bus.pt]).make_can_msg(
        "ASCMActiveCruiseControlStatus", 0, {"ACCAlwaysOne": 1, "ACCAlwaysOne2": 1})
      self.assertFalse(self.safety.safety_tx_hook(self.packet(dashboard)))
    # A radar bit without the intercepted ASCM flag cannot open the camera radar TX list.
    param = int(GMSafetyFlags.HW_CAM | GMSafetyFlags.HW_CAM_LONG | GMSafetyFlags.ASCM_RADAR)
    self.safety.set_safety_hooks(CarParams.SafetyModel.gm, param)
    self.safety.init_tests()
    self.assertFalse(self.safety.safety_tx_hook(self.packet((0x310, b"\x42\x04", 1))))


if __name__ == "__main__":
  unittest.main()
