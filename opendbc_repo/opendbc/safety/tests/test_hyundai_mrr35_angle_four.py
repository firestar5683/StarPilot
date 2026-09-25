import math
import unittest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.fw_versions import match_fw_to_car
from opendbc.car.fingerprints import all_legacy_fingerprint_cars
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.hyundaicanfd import CanBus, hkg_can_fd_checksum, create_angle_steering_messages
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.radar_interface import RadarInterface, MRR35_RADAR_START_ADDR
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags, HyundaiSafetyFlags, CANFD_ANGLE_MODEL_BITS, CANFD_ANGLE_OBSERVED_ADAS_BIT
from opendbc.car.hyundai.fingerprints import FW_VERSIONS
from opendbc.car.lateral import get_max_angle_vm
from opendbc.safety.tests.libsafety import libsafety_py


ANGLE_CARS = (CAR.GENESIS_GV70_2026, CAR.GENESIS_GV70_ELECTRIFIED_2ND_GEN,
              CAR.GENESIS_GV80_2025, CAR.HYUNDAI_IONIQ_9)
TOPOLOGIES = ("lka", "lka_alt", "lfa", "lfa_alt")


def params(car, topology="lka_alt", *, alpha=False, release=False, adas_cmd=False, radar=False, hybrid=False):
  fp = gen_empty_fingerprint()
  if topology == "lka":
    fp[2][0x50] = 16
  elif topology == "lka_alt":
    fp[2][0x110] = 32
  if topology.startswith("lka"):
    fp[1][0x1CF] = 8
  elif topology == "lfa":
    fp[0][0x1CF] = 8
  else:
    fp[0][0x1AA] = 16
  if adas_cmd:
    fp[2][0xCB] = 24
  if radar:
    fp[0][MRR35_RADAR_START_ADDR] = 24
  if hybrid:
    fp[1 if topology.startswith("lka") else 0][0xFA] = 8
  return CarInterface.get_params(car, fp, [], alpha, release, False)


class TestHyundaiMRR35AngleFour(unittest.TestCase):
  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def mode(self, cp, extra=0):
    safety = libsafety_py.libsafety
    self.assertEqual(safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundaiCanfd,
                                              cp.safetyConfigs[-1].safetyParam | extra), 0)
    safety.init_tests()
    safety.set_timer(1_000_000)
    return safety

  @staticmethod
  def source_frames(cp, topology, *, brake=False, speed=30.0, cruise=True, measured_angle=0.0, gear_value=5):
    can = CanBus(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    ev = bool(cp.flags & HyundaiFlags.EV)
    fuel = "ACCELERATOR" if ev else "ACCELERATOR_BRAKE_ALT"
    gear = "ACCELERATOR" if ev else "GEAR_ALT_2"
    button = "CRUISE_BUTTONS_ALT" if topology == "lfa_alt" else "CRUISE_BUTTONS"
    scc_bus = can.CAM if topology.startswith("lfa") else can.ECAN
    inputs = [(fuel, can.ECAN, {"GEAR": gear_value} if ev else {}),
              ("TCS", can.ECAN, {"DriverBraking": int(brake)}),
              ("WHEEL_SPEEDS", can.ECAN, {key: speed for key in
               ("WHL_SpdFLVal", "WHL_SpdFRVal", "WHL_SpdRLVal", "WHL_SpdRRVal")}),
              ("MDPS", can.ECAN, {"MDPS_PaStrAnglVal": measured_angle}),
              ("STEERING_SENSORS", can.ECAN, {"STEERING_ANGLE": measured_angle}),
              ("DOORS_SEATBELTS", can.ECAN, {"DRIVER_SEATBELT": 1}),
              ("BLINKERS", can.ECAN, {})]
    if gear != fuel:
      inputs.append((gear, can.ECAN, {"GEAR": gear_value}))
    inputs += [(button, can.ECAN, {"CRUISE_BUTTONS": 2}),
               ("SCC_CONTROL", scc_bus, {"ACCMode": 0}),
               ("SCC_CONTROL", scc_bus, {"ACCMode": int(cruise)})]
    if topology.startswith("lka"):
      inputs.append(("LKAS_ALT" if topology == "lka_alt" else "LKAS", can.CAM, {}))
    return packer, [packer.make_can_msg(name, bus, values) for name, bus, values in inputs]

  def joined(self, car, topology, *, brake=False, speed=30.0, active=True, adas_cmd=False,
             desired=1.0, measured=0.0):
    cp = params(car, topology, alpha=True, adas_cmd=adas_cmd)
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    packer, frames = self.source_frames(cp, topology, brake=brake, speed=speed,
                                        measured_angle=measured)
    safety = self.mode(cp)
    for frame in frames:
      self.assertTrue(safety.safety_rx_hook(self.packet(frame)), hex(frame[0]))
    for parser in parsers.values():
      parser.update((1_000_000_000, [frame for frame in frames if frame[2] == parser.bus]))
    state.out = state.update(parsers)
    self.assertTrue(parsers[Bus.pt].can_valid)
    self.assertEqual(state.out.cruiseState.enabled, True)
    self.assertEqual(state.out.gearShifter, structs.CarState.GearShifter.drive)
    self.assertEqual(state.out.brakePressed, brake)
    self.assertTrue(safety.get_controls_allowed())
    control = structs.CarControl()
    control.enabled = True
    control.latActive = active
    control.actuators.steeringAngleDeg = desired
    controller = CarController(DBC[car], cp)
    _, sends = controller.update(control.as_reader(), state, 1_000_000_000)
    steering = [frame for frame in sends if frame[0] in (0x50, 0x110, 0x12A, 0xCB)]
    self.assertTrue(steering)
    return cp, state, safety, control, controller, steering, packer

  def test_16_profiles_parsed_controller_to_native(self):
    for car in ANGLE_CARS:
      for topology in TOPOLOGIES:
        with self.subTest(car=car, topology=topology):
          cp, state, safety, _, _, steering, packer = self.joined(car, topology)
          self.assertFalse(cp.alphaLongitudinalAvailable)
          self.assertFalse(cp.openpilotLongitudinalControl)
          self.assertTrue(cp.pcmCruise)
          self.assertEqual(cp.steerControlType, structs.CarParams.SteerControlType.angle)
          self.assertEqual(cp.safetyConfigs[-1].safetyParam & 6144, CANFD_ANGLE_MODEL_BITS[car.name])
          self.assertFalse(cp.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG)
          expected = 0x50 if topology == "lka" else 0x110 if topology == "lka_alt" else 0x12A
          self.assertEqual(steering[0][0], expected)
          self.assertNotEqual((steering[0][1][11] << 6) | (steering[0][1][10] >> 2), 0)
          for frame in steering:
            self.assertEqual(int.from_bytes(frame[1][:2], "little"),
                             hkg_can_fd_checksum(frame[0], None, bytearray(frame[1])))
            self.assertTrue(safety.safety_tx_hook(self.packet(frame)), hex(frame[0]))
            if frame[0] in (0x110, 0xCB):
              name = "LKAS_ALT" if frame[0] == 0x110 else "LFA_ALT"
              decoded = CANParser(DBC[car][Bus.pt], [(name, math.nan)], frame[2])
              decoded.update((1_000_000_000, [frame]))
              self.assertAlmostEqual(decoded.vl[name]["ADAS_StrAnglReqVal"], 1.0, delta=0.11)
              self.assertEqual(decoded.vl[name]["ADAS_ActvACILvl2Sta"] if frame[0] == 0xCB else
                               (frame[1][9] >> 4) & 3, 2)
          wrong_bus = (steering[0][0], steering[0][1], 1 - steering[0][2])
          self.assertFalse(safety.safety_tx_hook(self.packet(wrong_bus)))
          self.assertFalse(safety.safety_tx_hook(self.packet((steering[0][0], steering[0][1][:-8], steering[0][2]))))
          self.assertEqual(packer.dbc.name_to_msg["LFA"].address, 0x12A)

  def test_observed_adas_cmd_and_brake_neutral(self):
    for car in ANGLE_CARS:
      cp, state, safety, control, controller, steering, _ = self.joined(car, "lfa", adas_cmd=True)
      self.assertTrue(cp.flags & HyundaiFlags.SEND_LFA)
      self.assertTrue(cp.safetyConfigs[-1].safetyParam & CANFD_ANGLE_OBSERVED_ADAS_BIT)
      self.assertEqual([frame[0] for frame in steering], [0x12A, 0xCB])
      decoded = CANParser(DBC[car][Bus.pt], [("LFA_ALT", math.nan)], steering[1][2])
      decoded.update((1_000_000_000, [steering[1]]))
      self.assertEqual(decoded.vl["LFA_ALT"]["ADAS_ActvACILvl2Sta"], 2)
      self.assertAlmostEqual(decoded.vl["LFA_ALT"]["ADAS_StrAnglReqVal"], 1.0, delta=0.11)
      self.assertEqual(int.from_bytes(steering[1][1][:2], "little"),
                       hkg_can_fd_checksum(steering[1][0], None, bytearray(steering[1][1])))
      for frame in steering:
        self.assertTrue(safety.safety_tx_hook(self.packet(frame)), hex(frame[0]))
      state.out.brakePressed = True
      _, sends = controller.update(control.as_reader(), state, 1_010_000_000)
      neutral = [frame for frame in sends if frame[0] in (0x12A, 0xCB)]
      self.assertEqual((neutral[0][1][9] >> 4) & 3, 1)
      self.assertEqual((neutral[1][1][3] >> 4) & 15, 1)
      for frame in neutral:
        self.assertTrue(safety.safety_tx_hook(self.packet(frame)))

  def test_host_native_speed_envelopes_and_rate(self):
    for car in ANGLE_CARS:
      for topology in TOPOLOGIES:
        for speed_mps in (2.0, 10.0, 25.0, 35.0):
          with self.subTest(car=car, topology=topology, speed=speed_mps):
            cp, state, safety, control, controller, _, _ = self.joined(
              car, topology, speed=speed_mps * 3.6, desired=360.0)
            last_angle = 0.0
            for step in range(90):
              safety.set_timer(1_010_000 + step * 10_000)
              _, sends = controller.update(control.as_reader(), state, 1_010_000_000 + step * 10_000_000)
              steering = [frame for frame in sends if frame[0] in (0x50, 0x110, 0x12A, 0xCB)]
              for frame in steering:
                self.assertTrue(safety.safety_tx_hook(self.packet(frame)), (car, topology, speed_mps, step, hex(frame[0])))
              primary = steering[-1]
              last_angle = ((primary[1][11] << 6) | (primary[1][10] >> 2)) / 10.0 if primary[0] != 0xCB else controller.apply_angle_last
            max_angle = get_max_angle_vm(max(state.out.vEgoRaw - 1.0, 1.0), controller.angle_vm, controller.params)
            self.assertGreater(last_angle, min(5.0, max_angle * 0.7))
            self.assertLessEqual(last_angle, min(360.0, max_angle) + 0.15)
            data = bytearray(primary[1])
            if primary[0] != 0xCB:
              reversed_angle = (-3600) & 0x3FFF
              data[10] = (data[10] & 3) | ((reversed_angle & 63) << 2)
              data[11] = reversed_angle >> 6
              data[:2] = hkg_can_fd_checksum(primary[0], None, data).to_bytes(2, "little")
              self.assertFalse(safety.safety_tx_hook(self.packet((primary[0], bytes(data), primary[2]))))

  def test_observed_adas_multitick_actuation_history(self):
    for car in ANGLE_CARS:
      for topology in ("lfa", "lfa_alt"):
        for speed_mps in (2.0, 10.0, 25.0, 35.0):
          for direction in (-1, 1):
            with self.subTest(car=car, topology=topology, speed=speed_mps, direction=direction):
              _, state, safety, control, controller, _, _ = self.joined(
                car, topology, speed=speed_mps * 3.6, desired=direction * 360.0,
                measured=direction * 10.0, adas_cmd=True)
              for step in range(90):
                safety.set_timer(1_010_000 + step * 10_000)
                _, sends = controller.update(control.as_reader(), state, 1_010_000_000 + step * 10_000_000)
                steering = [frame for frame in sends if frame[0] in (0x12A, 0xCB)]
                self.assertEqual([frame[0] for frame in steering], [0x12A, 0xCB])
                for frame in steering:
                  self.assertTrue(safety.safety_tx_hook(self.packet(frame)),
                                  (car, topology, speed_mps, direction, step, hex(frame[0])))

  def test_angle_frames_reject_other_actuation_channels(self):
    for car in ANGLE_CARS:
      for topology in TOPOLOGIES:
        with self.subTest(car=car, topology=topology):
          observed = topology.startswith("lfa")
          cp, _, safety, _, _, steering, _ = self.joined(car, topology, adas_cmd=observed)
          primary = steering[-1]
          if observed:
            self.assertTrue(safety.safety_tx_hook(self.packet(steering[0])))
          else:
            self.assertFalse(cp.safetyConfigs[-1].safetyParam & CANFD_ANGLE_OBSERVED_ADAS_BIT)

          def deny(frame, byte_index, xor, safety=safety, car=car, topology=topology):
            data = bytearray(frame[1])
            data[byte_index] ^= xor
            data[:2] = hkg_can_fd_checksum(frame[0], None, data).to_bytes(2, "little")
            self.assertFalse(safety.safety_tx_hook(self.packet((frame[0], bytes(data), frame[2]))),
                             (car, topology, byte_index, xor))

          angle_frame = steering[0] if observed else primary
          deny(angle_frame, 5, 0x2)   # legacy torque request
          deny(angle_frame, 6, 0x10)  # legacy torque enable
          if angle_frame[0] == 0x110:
            deny(angle_frame, 13, 0x8)  # independent FCA_ESA_CtrlSta
          if observed:
            deny(primary, 3, 0x1)   # ADAS_ActvACISta
            gain_overflow = bytearray(primary[1])
            gain_overflow[6] = 251
            gain_overflow[:2] = hkg_can_fd_checksum(primary[0], None, gain_overflow).to_bytes(2, "little")
            self.assertFalse(safety.safety_tx_hook(self.packet((primary[0], bytes(gain_overflow), primary[2]))))
            deny(primary, 7, 0x1)   # FCA_ESA_ActvSta
            deny(primary, 8, 0x1)   # FCA_ESA_TqBstGainVal
            self.assertTrue(safety.safety_tx_hook(self.packet(primary)))
          else:
            self.assertTrue(safety.safety_tx_hook(self.packet(primary)))

  def test_parsed_brake_cruise_and_required_source_handoff(self):
    for car in ANGLE_CARS:
      for topology in ("lka_alt", "lfa_alt"):
        with self.subTest(car=car, topology=topology):
          cp, state, safety, control, controller, steering, packer = self.joined(car, topology)
          self.assertTrue(safety.safety_tx_hook(self.packet(steering[0])))
          parsers = state.get_can_parsers(cp)
          can = CanBus(cp)
          _, frames = self.source_frames(cp, topology, brake=True)
          for frame in frames:
            self.assertTrue(safety.safety_rx_hook(self.packet(frame)))
          for parser in parsers.values():
            parser.update((1_010_000_000, [frame for frame in frames if frame[2] == parser.bus]))
          state.out = state.update(parsers)
          self.assertTrue(state.out.brakePressed)
          _, sends = controller.update(control.as_reader(), state, 1_010_000_000)
          for frame in sends:
            if frame[0] in (0x50, 0x110, 0x12A, 0xCB):
              self.assertEqual((frame[1][9] >> 4) & 3, 1)
              self.assertTrue(safety.safety_tx_hook(self.packet(frame)))
          self.assertFalse(safety.get_controls_allowed())

          # A high ACCMode alone cannot re-arm after stock cruise goes inactive.
          scc_bus = can.CAM if topology.startswith("lfa") else can.ECAN
          off = packer.make_can_msg("SCC_CONTROL", scc_bus, {"ACCMode": 0})
          self.assertTrue(safety.safety_rx_hook(self.packet(off)))
          parsers[Bus.cam if scc_bus == can.CAM else Bus.pt].update((1_020_000_000, [off]))
          state.out = state.update(parsers)
          self.assertFalse(state.out.cruiseState.enabled)
          _, sends = controller.update(control.as_reader(), state, 1_020_000_000)
          for frame in sends:
            if frame[0] in (0x50, 0x110, 0x12A, 0xCB):
              self.assertEqual((frame[1][9] >> 4) & 3, 1)

          missing = state.get_can_parsers(cp)
          _, fresh = self.source_frames(cp, topology)
          fresh = [frame for frame in fresh if frame[0] != packer.dbc.name_to_msg["TCS"].address]
          for parser in missing.values():
            parser.update((1_000_000_000, [frame for frame in fresh if frame[2] == parser.bus]))
          self.assertFalse(missing[Bus.pt].can_valid)

  def test_parsed_gas_and_stock_cruise_off_neutralize_controller(self):
    for car in ANGLE_CARS:
      for topology in ("lka", "lfa"):
        with self.subTest(car=car, topology=topology):
          cp, state, safety, control, controller, _, packer = self.joined(car, topology)
          can = CanBus(cp)
          parsers = state.get_can_parsers(cp)
          _, frames = self.source_frames(cp, topology)
          for parser in parsers.values():
            parser.update((1_000_000_000, [frame for frame in frames if frame[2] == parser.bus]))
          fuel = "ACCELERATOR" if cp.flags & HyundaiFlags.EV else "ACCELERATOR_BRAKE_ALT"
          signal = {"ACCELERATOR_PEDAL": 10} if cp.flags & HyundaiFlags.EV else {"ACCELERATOR_PEDAL_PRESSED": 1}
          gas = packer.make_can_msg(fuel, can.ECAN, signal)
          self.assertTrue(safety.safety_rx_hook(self.packet(gas)))
          parsers[Bus.pt].update((1_010_000_000, [gas]))
          state.out = state.update(parsers)
          self.assertTrue(state.out.gasPressed)
          _, sends = controller.update(control.as_reader(), state, 1_010_000_000)
          steer = next(frame for frame in sends if frame[0] in (0x50, 0x110, 0x12A))
          self.assertEqual((steer[1][9] >> 4) & 3, 1)
          self.assertTrue(safety.safety_tx_hook(self.packet(steer)))

          # With gas released, the stock SCC source still owns enable state.
          cruise_bus = can.CAM if topology.startswith("lfa") else can.ECAN
          off = packer.make_can_msg("SCC_CONTROL", cruise_bus, {"ACCMode": 0})
          self.assertTrue(safety.safety_rx_hook(self.packet(off)))
          parsers[Bus.cam if cruise_bus == can.CAM else Bus.pt].update((1_020_000_000, [off]))
          state.out = state.update(parsers)
          self.assertFalse(state.out.cruiseState.enabled)
          _, sends = controller.update(control.as_reader(), state, 1_020_000_000)
          steer = next(frame for frame in sends if frame[0] in (0x50, 0x110, 0x12A))
          self.assertEqual((steer[1][9] >> 4) & 3, 1)

  def test_alt_lkas_parsed_gear_handoff(self):
    # Frozen LKAS_ALT status is drive-gated except for the not-yet-ported
    # Sportage HEV 2026. All four current identities use the drive gate.
    expected_gears = {0: structs.CarState.GearShifter.park,
                      1: structs.CarState.GearShifter.unknown,
                      5: structs.CarState.GearShifter.drive,
                      6: structs.CarState.GearShifter.neutral,
                      7: structs.CarState.GearShifter.reverse}
    for car in ANGLE_CARS:
      for gear_value, expected_gear in expected_gears.items():
        for direction in (-1, 1):
          with self.subTest(car=car, gear=gear_value, direction=direction):
            cp = params(car, "lka_alt")
            state = CarState(cp)
            parsers = state.get_can_parsers(cp)
            _, frames = self.source_frames(cp, "lka_alt", gear_value=gear_value)
            safety = self.mode(cp)
            for frame in frames:
              self.assertTrue(safety.safety_rx_hook(self.packet(frame)))
            for parser in parsers.values():
              parser.update((1_000_000_000, [frame for frame in frames if frame[2] == parser.bus]))
            state.out = state.update(parsers)
            self.assertEqual(state.out.gearShifter, expected_gear)
            self.assertTrue(state.out.cruiseState.enabled)
            self.assertTrue(safety.get_controls_allowed())
            control = structs.CarControl()
            control.enabled = True
            control.latActive = True
            control.actuators.steeringAngleDeg = direction * 45.0
            controller = CarController(DBC[car], cp)
            _, sends = controller.update(control.as_reader(), state, 1_000_000_000)
            steer = next(frame for frame in sends if frame[0] == 0x110)
            self.assertEqual((steer[1][9] >> 4) & 3, 2 if gear_value == 5 else 1)
            self.assertTrue(safety.safety_tx_hook(self.packet(steer)))

  def test_native_required_source_bus_crc_counter_and_staleness(self):
    for car in ANGLE_CARS:
      for topology in TOPOLOGIES:
        with self.subTest(car=car, topology=topology):
          cp = params(car, topology)
          packer, frames = self.source_frames(cp, topology)
          scc_addr = packer.dbc.name_to_msg["SCC_CONTROL"].address
          safety = self.mode(cp)
          for frame in frames:
            if frame[0] == scc_addr:
              frame = (frame[0], frame[1], 0 if frame[2] != 0 else 1)
            self.assertTrue(safety.safety_rx_hook(self.packet(frame)))
          safety.safety_tick()
          self.assertFalse(safety.get_controls_allowed())

          _, _, safety, _, _, steering, _ = self.joined(car, topology)
          active_scc = [frame for frame in frames if frame[0] == scc_addr][-1]
          corrupt = bytearray(active_scc[1])
          corrupt[0] ^= 1
          self.assertFalse(safety.safety_rx_hook(self.packet((scc_addr, bytes(corrupt), active_scc[2]))))
          self.assertFalse(safety.get_controls_allowed())

          _, _, safety, _, _, steering, _ = self.joined(car, topology)
          for _ in range(5):
            safety.safety_rx_hook(self.packet(active_scc))
          self.assertFalse(safety.get_controls_allowed())

          _, _, safety, _, _, steering, _ = self.joined(car, topology)
          safety.set_timer(2_100_000)
          safety.safety_tick()
          self.assertFalse(safety.safety_config_valid())

  def test_raw_angle_namespace_release_stock_ownership_and_registered_firmware(self):
    safety = libsafety_py.libsafety
    for car in ANGLE_CARS:
      for topology in TOPOLOGIES:
        cp = params(car, topology, alpha=True, release=True)
        self.assertFalse(cp.openpilotLongitudinalControl)
        self.assertFalse(cp.alphaLongitudinalAvailable)
        raw = cp.safetyConfigs[-1].safetyParam
        self.assertFalse(raw & HyundaiSafetyFlags.LONG)
        for bit in (2, 4, 64, 256, 1024, 8192, 32768):
          self.assertEqual(safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundaiCanfd, raw | bit), 0)
          safety.init_tests()
          frame = CANPacker(DBC[car][Bus.pt]).make_can_msg("LKAS", 0, {})
          self.assertFalse(safety.safety_tx_hook(self.packet(frame)), (car, topology, bit))
    _, matched = match_fw_to_car([], "", log=False)
    self.assertFalse(set(ANGLE_CARS) & matched)
    self.assertTrue(set(ANGLE_CARS).issubset(FW_VERSIONS))
    for car in ANGLE_CARS:
      cohort = [structs.CarParams.CarFw(ecu=ecu, address=address, subAddress=sub or 0,
                                       fwVersion=versions[0], brand="hyundai")
                for (ecu, address, sub), versions in FW_VERSIONS[car].items()]
      exact, discovered = match_fw_to_car(cohort, "", log=False)
      self.assertTrue(exact)
      self.assertEqual(discovered, {car})
      for observed in ([item] for item in cohort):
        self.assertFalse(set(ANGLE_CARS) & match_fw_to_car(observed, "", log=False)[1])
    self.assertFalse(set(ANGLE_CARS) & set(all_legacy_fingerprint_cars()))

  def test_angle_relay_and_forwarding_block(self):
    for car in ANGLE_CARS:
      for topology in TOPOLOGIES:
        with self.subTest(car=car, topology=topology):
          _, _, safety, _, _, steering, _ = self.joined(car, topology)
          frame = steering[0]
          self.assertEqual(safety.safety_fwd_hook(0, frame[0]), 2)
          self.assertEqual(safety.safety_fwd_hook(2, frame[0]), -1)
          safety.set_relay_malfunction(True)
          self.assertEqual(safety.safety_fwd_hook(0, frame[0]), -1)
          self.assertFalse(safety.safety_tx_hook(self.packet(frame)))

  def test_all_angle_tagged_raw_params_have_exactly_seventy_six_profiles(self):
    safety = libsafety_py.libsafety
    valid = set()
    neutral_frames = []
    for car in ANGLE_CARS:
      for topology in TOPOLOGIES:
        cp = params(car, topology, release=True)
        valid.add(cp.safetyConfigs[-1].safetyParam)
        if topology.startswith("lfa"):
          valid.add(params(car, topology, release=True, adas_cmd=True).safetyConfigs[-1].safetyParam)
        packer = CANPacker(DBC[car][Bus.pt])
        can = CanBus(cp)
        neutral_frames += create_angle_steering_messages(packer, cp, can, False, False, 0.0, 0.0)
    hybrid_cars = (CAR.HYUNDAI_AZERA_HEV_7TH_GEN, CAR.KIA_SORENTO_HEV_4TH_GEN_LFA2, CAR.KIA_SPORTAGE_HEV_2026)
    for car in hybrid_cars:
      for topology in TOPOLOGIES:
        for hybrid in (False, True):
          cp = params(car, topology, release=True, hybrid=hybrid)
          valid.add(cp.safetyConfigs[-1].safetyParam)
          if topology.startswith("lfa"):
            valid.add(params(car, topology, release=True, adas_cmd=True, hybrid=hybrid).safetyConfigs[-1].safetyParam)
          packer = CANPacker(DBC[car][Bus.pt])
          neutral_frames += create_angle_steering_messages(packer, cp, CanBus(cp), False, False, 0.0, 0.0)
    from opendbc.safety.tests.test_hyundai_ccnc_angle_two import params as ccnc_params
    for car, topologies, fuels in ((CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN, TOPOLOGIES, (False, True)),
                                   (CAR.KIA_SPORTAGE_2026, ("lfa", "lfa_alt"), (False,))):
      for topology in topologies:
        for hybrid in fuels:
          cp = ccnc_params(car, topology, release=True, hybrid=hybrid)
          valid.add(cp.safetyConfigs[-1].safetyParam)
          if topology.startswith("lfa"):
            valid.add(ccnc_params(car, topology, release=True, hybrid=hybrid, adas=True).safetyConfigs[-1].safetyParam)
          packer = CANPacker(DBC[car][Bus.pt])
          neutral_frames += create_angle_steering_messages(packer, cp, CanBus(cp), False, False, 0.0, 0.0)
    for topology in ("lfa", "lfa_alt"):
      valid.add(params(CAR.KIA_EV6_2025, topology).safetyConfigs[-1].safetyParam)
    self.assertEqual(len(valid), 78)
    for raw in range(0x4000, 0x10000):
      if not raw & 0x4000:
        continue
      self.assertEqual(safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundaiCanfd, raw), 0)
      safety.init_tests()
      accepted = any(safety.safety_tx_hook(self.packet(frame)) for frame in neutral_frames)
      self.assertEqual(accepted, raw in valid, hex(raw))

  def test_mrr35_cycle_freshness(self):
    cp = params(CAR.HYUNDAI_IONIQ_9, radar=True)
    self.assertFalse(cp.radarUnavailable)
    radar = RadarInterface(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.radar])
    first = packer.make_can_msg("RADAR_TRACK_3a5", 0, {"STATE": 3, "LONG_DIST": 22.0,
                                                        "LAT_DIST": 1.0, "REL_SPEED": -1.0})
    trigger = packer.make_can_msg("RADAR_TRACK_3c4", 0, {"STATE": 0})
    out = radar.update((1_000_000_000, [first, trigger]))
    self.assertEqual(len(out.points), 1)
    self.assertAlmostEqual(out.points[0].dRel, 22.0, places=1)
    out = radar.update((1_050_000_000, [trigger]))
    self.assertEqual(len(out.points), 0)
    self.assertIsNone(radar.update((1_040_000_000, [trigger])))
    self.assertIsNone(radar.update((1_060_000_000, [first])))
    out = radar.update((1_100_000_000, [trigger]))
    self.assertEqual(len(out.points), 1)


if __name__ == "__main__":
  unittest.main()
