import unittest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.fingerprints import all_legacy_fingerprint_cars
from opendbc.car.fw_versions import match_fw_to_car
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.fingerprints import FW_VERSIONS
from opendbc.car.hyundai.hyundaicanfd import CanBus, hkg_can_fd_checksum
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import (CANFD_ANGLE_CCNC_MODEL_BANK_BIT, CANFD_ANGLE_MODEL_BITS,
                                        CANFD_ANGLE_OBSERVED_ADAS_BIT, CAR, DBC, HyundaiFlags,
                                        HyundaiSafetyFlags)
from opendbc.car.lateral import get_max_angle_delta_vm, get_max_angle_vm
from opendbc.safety.tests.libsafety import libsafety_py


CARS = (CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN, CAR.KIA_SPORTAGE_2026)
CAMERA_TOPOLOGIES = ("lfa", "lfa_alt")
STEER_IDS = (0x50, 0x110, 0x12A, 0xCB)
DISPLAY_IDS = (0x161, 0x162)


def params(car, topology="lfa", *, hybrid=False, adas=False, release=False, alpha=False):
  fp = gen_empty_fingerprint()
  ecan = 1 if topology.startswith("lka") else 0
  if topology == "lka":
    fp[2][0x50] = 16
  elif topology == "lka_alt":
    fp[2][0x110] = 32
  if topology == "lfa_alt":
    fp[ecan][0x1AA] = 16
  else:
    fp[ecan][0x1CF] = 8
  if hybrid:
    fp[ecan][0xFA] = 8
  if adas:
    fp[2][0xCB] = 24
  return CarInterface.get_params(car, fp, [], alpha, release, False)


def source_frames(cp, topology, *, speed=36.0, measured=0.0, gear=5, brake=False, gas=False,
                  cruise=True, wrong_fuel=False):
  can = CanBus(cp)
  packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
  hybrid = bool(cp.flags & HyundaiFlags.HYBRID)
  fuel = "ACCELERATOR_ALT" if hybrid else "ACCELERATOR_BRAKE_ALT"
  if wrong_fuel:
    fuel = "ACCELERATOR_BRAKE_ALT" if hybrid else "ACCELERATOR_ALT"
  gas_values = {"ACCELERATOR_PEDAL": 4.0} if gas and fuel == "ACCELERATOR_ALT" else \
               {"ACCELERATOR_PEDAL_PRESSED": 1} if gas and fuel == "ACCELERATOR_BRAKE_ALT" else {}
  button = "CRUISE_BUTTONS_ALT" if topology == "lfa_alt" else "CRUISE_BUTTONS"
  scc_bus = can.ECAN if topology.startswith("lka") else can.CAM
  entries = [(fuel, can.ECAN, gas_values),
             ("TCS", can.ECAN, {"DriverBraking": int(brake)}),
             ("WHEEL_SPEEDS", can.ECAN, {key: speed for key in
              ("WHL_SpdFLVal", "WHL_SpdFRVal", "WHL_SpdRLVal", "WHL_SpdRRVal")}),
             ("MDPS", can.ECAN, {"MDPS_PaStrAnglVal": measured}),
             ("STEERING_SENSORS", can.ECAN, {"STEERING_ANGLE": measured}),
             ("DOORS_SEATBELTS", can.ECAN, {"DRIVER_SEATBELT": 1}),
             ("BLINKERS", can.ECAN, {}),
             ("GEAR_ALT_2", can.ECAN, {"GEAR": gear}),
             (button, can.ECAN, {"CRUISE_BUTTONS": 2}),
             ("SCC_CONTROL", scc_bus, {"ACCMode": 0}),
             ("SCC_CONTROL", scc_bus, {"ACCMode": int(cruise)})]
  if topology.startswith("lka"):
    entries.append(("LKAS_ALT" if topology == "lka_alt" else "LKAS", can.CAM, {}))
  return packer, [packer.make_can_msg(name, bus, values) for name, bus, values in entries]


class TestHyundaiCcncAngleTwo(unittest.TestCase):
  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def mode(self, cp):
    safety = libsafety_py.libsafety
    self.assertEqual(safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundaiCanfd,
                                             cp.safetyConfigs[-1].safetyParam), 0)
    safety.init_tests()
    safety.set_timer(1_000_000)
    return safety

  def joined(self, car, topology, *, hybrid=False, adas=False, speed=36.0, measured=0.0, gear=5,
             brake=False, gas=False, cruise=True, desired=1.0, display=False):
    cp = params(car, topology, hybrid=hybrid, adas=adas, release=True, alpha=True)
    can = CanBus(cp)
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    packer, frames = source_frames(cp, topology, speed=speed, measured=measured, gear=gear,
                                   brake=brake, gas=gas, cruise=cruise)
    safety = self.mode(cp)
    for frame in frames:
      self.assertTrue(safety.safety_rx_hook(self.packet(frame)), (car, topology, hex(frame[0])))
    for parser in parsers.values():
      parser.update((990_000_000, [frame for frame in frames if frame[2] == parser.bus]))
    state.out = state.update(parsers)
    self.assertTrue(parsers[Bus.pt].can_valid, (car, topology, hybrid))
    self.assertEqual(state.out.cruiseState.enabled, cruise)
    control = structs.CarControl()
    control.enabled = control.latActive = True
    control.actuators.steeringAngleDeg = desired
    controller = CarController(DBC[car], cp)
    # Establish the display-counter baseline before the new camera pair.
    controller.update(control.as_reader(), state, 990_000_000)
    controller.frame = 5
    if display:
      self.assertIn(topology, CAMERA_TOPOLOGIES)
      pair = [packer.make_can_msg("CCNC_0x161", can.CAM, {"COUNTER": 7, "BACKGROUND": 3}),
              packer.make_can_msg("CCNC_0x162", can.CAM, {"COUNTER": 9, "SPEEDLIMIT": 60})]
      parsers[Bus.cam].update((1_000_000_000, pair))
      state.out = state.update(parsers)
    _, sends = controller.update(control.as_reader(), state, 1_000_000_000)
    steering = [frame for frame in sends if frame[0] in STEER_IDS]
    displays = [frame for frame in sends if frame[0] in DISPLAY_IDS]
    return cp, state, safety, control, controller, steering, displays, packer

  def test_sixteen_observed_profiles_from_parser_to_native(self):
    cases = 0
    for car in CARS:
      topologies = ("lka", "lka_alt", "lfa", "lfa_alt") if car == CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN else CAMERA_TOPOLOGIES
      for topology in topologies:
        for hybrid in (False, True) if car == CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN else (False,):
          for adas in (False, True) if topology in CAMERA_TOPOLOGIES else (False,):
            with self.subTest(car=car, topology=topology, hybrid=hybrid, adas=adas):
              cp, state, safety, _, controller, steering, displays, _ = self.joined(car, topology, hybrid=hybrid,
                                                                                     adas=adas, display=topology in CAMERA_TOPOLOGIES)
              cases += 1
              self.assertEqual(cp.safetyConfigs[-1].safetyParam & CANFD_ANGLE_CCNC_MODEL_BANK_BIT,
                               CANFD_ANGLE_CCNC_MODEL_BANK_BIT)
              self.assertEqual(cp.safetyConfigs[-1].safetyParam & (1024 | 2048 | 4096 | 8192), CANFD_ANGLE_MODEL_BITS[car.name])
              self.assertEqual(bool(cp.safetyConfigs[-1].safetyParam & CANFD_ANGLE_OBSERVED_ADAS_BIT), adas)
              self.assertEqual(bool(cp.flags & HyundaiFlags.HYBRID), hybrid)
              self.assertEqual((cp.alphaLongitudinalAvailable, cp.openpilotLongitudinalControl, cp.pcmCruise), (False, False, True))
              self.assertEqual(state.out.gearShifter, structs.CarState.GearShifter.drive)
              self.assertTrue(safety.get_controls_allowed())
              self.assertEqual(steering[0][0], 0x50 if topology == "lka" else 0x110 if topology == "lka_alt" else 0x12A)
              self.assertGreater(abs(controller.apply_angle_last), 0)
              if adas:
                self.assertEqual([frame[0] for frame in steering], [0x12A, 0xCB])
                self.assertEqual((steering[0][1][9] >> 4) & 3, 1)
              else:
                self.assertNotEqual((steering[0][1][11] << 6) | (steering[0][1][10] >> 2), 0)
              for frame in steering + displays:
                self.assertEqual(int.from_bytes(frame[1][:2], "little"),
                                 hkg_can_fd_checksum(frame[0], None, bytearray(frame[1])))
                self.assertTrue(safety.safety_tx_hook(self.packet(frame)), hex(frame[0]))
              self.assertEqual([f[0] for f in displays], list(DISPLAY_IDS) if topology in CAMERA_TOPOLOGIES else [])
              self.assertFalse(any(f[0] in (0x160, 0x7C4, 0xEA, 0x730) for f in steering + displays))
    self.assertEqual(cases, 16)

  def test_stock_ownership_topology_and_joint_firmware_discovery(self):
    for car in CARS:
      for release in (False, True):
        cp = params(car, "lfa", release=release, alpha=True)
        self.assertFalse(cp.alphaLongitudinalAvailable)
        self.assertFalse(cp.openpilotLongitudinalControl)
        self.assertTrue(cp.pcmCruise)
        self.assertFalse(cp.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG)
    for topology in ("lka", "lka_alt"):
      cp = params(CAR.KIA_SPORTAGE_2026, topology)
      self.assertTrue(cp.dashcamOnly)
      self.assertEqual(cp.safetyConfigs[-1].safetyParam & CANFD_ANGLE_CCNC_MODEL_BANK_BIT, CANFD_ANGLE_CCNC_MODEL_BANK_BIT)
    self.assertTrue(params(CAR.KIA_SPORTAGE_2026, "lfa", hybrid=True).dashcamOnly)
    self.assertTrue(set(CARS).issubset(FW_VERSIONS))
    self.assertTrue(set(CARS).isdisjoint(set(all_legacy_fingerprint_cars())))
    frozen = {
      CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN: (
        b'\xf1\x00MX5HMFC  AT CAN LHD 1.00 1.07 99211-P6000 231218',
        b'\xf1\x00MX5_ RDR -----      1.00 1.01 99110-P6000         ',
      ),
      CAR.KIA_SPORTAGE_2026: (
        b'\xf1\x00NQ51.011.021.012551000HKP_NQ524_50509099211P1110',
        b'\xf1\x00NQ5__               1.00 1.04 99110P1100          ',
      ),
    }
    sibling_radar = b'\xf1\x00NQ5__               1.00 1.04 99110CH100          '
    for car, (camera, radar) in frozen.items():
      for observations in ((camera, radar), (camera,), (radar,), (camera, sibling_radar)):
        fw = [structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.fwdCamera if version == camera else structs.CarParams.Ecu.fwdRadar,
                                     address=0x7C4 if version == camera else 0x7D0, subAddress=0,
                                     fwVersion=version, brand="hyundai") for version in observations]
        _, matches = match_fw_to_car(fw, "", allow_fuzzy=False, log=False)
        expected = {car} if observations == (camera, radar) else set()
        self.assertEqual(set(CARS) & matches, expected, (car, observations, matches))
        _, production_matches = match_fw_to_car(fw, "", log=False)
        self.assertEqual(set(CARS) & production_matches, expected, (car, observations, production_matches))

  def test_gear_brake_gas_and_missing_source_neutralize(self):
    for car in CARS:
      for gear in (0, 6, 7, 1, 5):
        for direction in (-1, 1):
          cp, state, safety, _, _, steering, _, _ = self.joined(car, "lfa", gear=gear, desired=direction * 8.0)
          self.assertEqual((steering[0][1][9] >> 4) & 3, 2 if gear == 5 else 1)
          self.assertTrue(safety.safety_tx_hook(self.packet(steering[0])))
          if gear != 5:
            self.assertNotEqual(state.out.gearShifter, structs.CarState.GearShifter.drive)
      for brake, gas, cruise in ((True, False, True), (False, True, True), (False, False, False)):
        _, _, safety, _, _, steering, _, _ = self.joined(car, "lfa_alt", brake=brake, gas=gas, cruise=cruise)
        self.assertEqual((steering[0][1][9] >> 4) & 3, 1)
        self.assertTrue(safety.safety_tx_hook(self.packet(steering[0])))
      for hybrid in (False, True) if car == CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN else (False,):
        cp = params(car, "lfa", hybrid=hybrid)
        safety = self.mode(cp)
        _, frames = source_frames(cp, "lfa", wrong_fuel=True)
        for frame in frames:
          self.assertTrue(safety.safety_rx_hook(self.packet(frame)))
        state = CarState(cp)
        parsers = state.get_can_parsers(cp)
        for parser in parsers.values():
          parser.update((1_000_000_000, [frame for frame in frames if frame[2] == parser.bus]))
        self.assertFalse(parsers[Bus.pt].can_valid)
        safety.safety_tick()
        self.assertFalse(safety.safety_config_valid())
        self.assertFalse(safety.get_controls_allowed())

  def test_source_bus_crc_counter_and_health(self):
    for car in CARS:
      cp = params(car, "lfa")
      _, frames = source_frames(cp, "lfa")
      scc = [frame for frame in frames if frame[0] == 0x1A0][-1]
      for variant in ("wrong_bus", "bad_crc", "replay", "stale"):
        with self.subTest(car=car, variant=variant):
          safety = self.mode(cp)
          for frame in frames:
            if variant == "wrong_bus" and frame[0] == 0x1A0:
              frame = (frame[0], frame[1], 0 if frame[2] == 2 else 2)
            self.assertTrue(safety.safety_rx_hook(self.packet(frame)))
          if variant == "bad_crc":
            corrupt = bytearray(scc[1])
            corrupt[0] ^= 1
            self.assertFalse(safety.safety_rx_hook(self.packet((scc[0], bytes(corrupt), scc[2]))))
          elif variant == "replay":
            for _ in range(5):
              safety.safety_rx_hook(self.packet(scc))
          elif variant == "stale":
            safety.set_timer(2_100_000)
          safety.safety_tick()
          self.assertFalse(safety.get_controls_allowed() and safety.safety_config_valid())

  def test_display_pair_freshness_and_native_source_bus_length(self):
    for car in CARS:
      cp, state, safety, control, controller, steering, displays, packer = self.joined(car, "lfa", display=True)
      can = CanBus(cp)
      self.assertEqual([f[0] for f in displays], list(DISPLAY_IDS))
      for frame in displays:
        self.assertTrue(safety.safety_tx_hook(self.packet(frame)))
        self.assertFalse(safety.safety_tx_hook(self.packet((frame[0], frame[1], can.CAM))))
        self.assertFalse(safety.safety_tx_hook(self.packet((frame[0], frame[1][:-8], frame[2]))))
      controller.frame = 10
      _, repeated = controller.update(control.as_reader(), state, 1_050_000_000)
      self.assertFalse(any(f[0] in DISPLAY_IDS for f in repeated))
      parser = CANParser(DBC[car][Bus.pt], [("CCNC_0x161", 0), ("CCNC_0x162", 0)], can.CAM)
      parser.update((1_060_000_000, [packer.make_can_msg("CCNC_0x161", can.CAM, {"COUNTER": 8})]))
      state.ccnc_161_ts_ns = 1_060_000_000
      controller.frame = 15
      _, missing_pair = controller.update(control.as_reader(), state, 1_060_000_000)
      self.assertFalse(any(f[0] in DISPLAY_IDS for f in missing_pair))

  def test_sustained_host_native_geometry_and_dual_frame_history(self):
    cases = 0
    for car in CARS:
      topologies = ("lka", "lka_alt", "lfa", "lfa_alt") if car == CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN else CAMERA_TOPOLOGIES
      for topology in topologies:
        for hybrid in (False, True) if car == CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN else (False,):
          for adas in (False, True) if topology in CAMERA_TOPOLOGIES else (False,):
            for speed_mps in (2.0, 10.0, 25.0, 35.0):
              for direction in (-1, 1):
                with self.subTest(car=car, topology=topology, hybrid=hybrid, adas=adas,
                                  speed=speed_mps, direction=direction):
                  _, state, safety, control, controller, _, _, _ = self.joined(
                    car, topology, hybrid=hybrid, adas=adas, speed=speed_mps * 3.6,
                    measured=direction * 10.0, desired=direction * 360.0)
                  cases += 1
                  for step in range(90):
                    safety.set_timer(1_010_000 + step * 10_000)
                    _, sends = controller.update(control.as_reader(), state, 1_010_000_000 + step * 10_000_000)
                    steering = [frame for frame in sends if frame[0] in STEER_IDS]
                    self.assertEqual([frame[0] for frame in steering],
                                     [0x12A, 0xCB] if adas else
                                     [0x50 if topology == "lka" else 0x110 if topology == "lka_alt" else 0x12A])
                    if adas:
                      self.assertEqual((steering[0][1][9] >> 4) & 3, 1)
                    for frame in steering:
                      self.assertTrue(safety.safety_tx_hook(self.packet(frame)),
                                      (car, topology, hybrid, adas, speed_mps, direction, step, hex(frame[0])))
                  bound = get_max_angle_vm(max(state.out.vEgoRaw - 1.0, 1.0), controller.angle_vm, controller.params)
                  self.assertGreater(abs(controller.apply_angle_last), min(5.0, bound * 0.7))
                  self.assertLessEqual(abs(controller.apply_angle_last), min(360.0, bound) + 0.2)
    self.assertEqual(cases, 128)

  def test_measured_physical_speed_and_adjacent_angle_ticks(self):
    for car in CARS:
      for topology in ("lfa", "lfa_alt"):
        for speed_mps in (2.0, 10.0, 25.0, 41.0):
          _, state, safety, _, controller, steering, _, _ = self.joined(
            car, topology, speed=speed_mps * 3.6, measured=0.0, desired=0.0)
          packer = CANPacker(DBC[car][Bus.pt])
          for counter in range(1, 7):
            wheel_frame = packer.make_can_msg("WHEEL_SPEEDS", CanBus(controller.CP).ECAN,
                          {"COUNTER": counter, **dict.fromkeys(
                            ("WHL_SpdFLVal", "WHL_SpdFRVal", "WHL_SpdRLVal", "WHL_SpdRRVal"), speed_mps * 3.6)})
            self.assertTrue(safety.safety_rx_hook(self.packet(wheel_frame)))
          measured_speed = safety.get_vehicle_speed_min()
          self.assertAlmostEqual(measured_speed, speed_mps, delta=0.02)
          self.assertAlmostEqual(state.out.vEgoRaw, measured_speed, delta=0.02)
          effective_speed = max(measured_speed - 1.0, 1.0)
          max_ticks = int(get_max_angle_vm(effective_speed, controller.angle_vm, controller.params) * 10 + 1)
          delta_ticks = int(get_max_angle_delta_vm(effective_speed, controller.angle_vm, controller.params) * 10 + 1)
          frame = steering[0]

          def angle_packet(ticks, frame=frame):
            data = bytearray(frame[1])
            raw = ticks & 0x3FFF
            data[10] = (data[10] & 3) | ((raw & 63) << 2)
            data[11] = raw >> 6
            data[:2] = hkg_can_fd_checksum(frame[0], None, data).to_bytes(2, "little")
            return self.packet((frame[0], bytes(data), frame[2]))

          for sign in (-1, 1):
            with self.subTest(car=car, topology=topology, speed=speed_mps, sign=sign):
              allowed = min(max_ticks, 3600) * sign
              safety.set_controls_allowed(True)
              safety.set_desired_angle_last(allowed)
              self.assertTrue(safety.safety_tx_hook(angle_packet(allowed)))
              if max_ticks < 3600:
                rejected = (max_ticks + 1) * sign
                safety.set_controls_allowed(True)
                safety.set_desired_angle_last(rejected)
                self.assertFalse(safety.safety_tx_hook(angle_packet(rejected)))
              safety.set_controls_allowed(True)
              safety.set_desired_angle_last(0)
              self.assertTrue(safety.safety_tx_hook(angle_packet(delta_ticks * sign)))
              safety.set_controls_allowed(True)
              safety.set_desired_angle_last(0)
              self.assertFalse(safety.safety_tx_hook(angle_packet((delta_ticks + 1) * sign)))

  def test_actuation_fields_forwarding_and_relay(self):
    for car in CARS:
      topologies = ("lka", "lka_alt", "lfa", "lfa_alt") if car == CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN else CAMERA_TOPOLOGIES
      for topology in topologies:
        adas = topology in CAMERA_TOPOLOGIES
        _, _, safety, _, _, steering, displays, _ = self.joined(car, topology, adas=adas,
                                                                 display=topology in CAMERA_TOPOLOGIES)
        primary = steering[-1]
        angle_frame = steering[0] if adas else primary
        for byte_index, bit in ((5, 0x2), (6, 0x10)):
          data = bytearray(angle_frame[1])
          data[byte_index] ^= bit
          data[:2] = hkg_can_fd_checksum(angle_frame[0], None, data).to_bytes(2, "little")
          self.assertFalse(safety.safety_tx_hook(self.packet((angle_frame[0], bytes(data), angle_frame[2]))))
        if angle_frame[0] == 0x110:
          data = bytearray(angle_frame[1])
          data[13] ^= 0x8
          data[:2] = hkg_can_fd_checksum(angle_frame[0], None, data).to_bytes(2, "little")
          self.assertFalse(safety.safety_tx_hook(self.packet((angle_frame[0], bytes(data), angle_frame[2]))))
        if adas:
          for byte_index, bit in ((3, 0x1), (7, 0x1), (8, 0x1)):
            data = bytearray(primary[1])
            data[byte_index] ^= bit
            data[:2] = hkg_can_fd_checksum(primary[0], None, data).to_bytes(2, "little")
            self.assertFalse(safety.safety_tx_hook(self.packet((primary[0], bytes(data), primary[2]))))
        self.assertTrue(safety.safety_tx_hook(self.packet(primary)))
        self.assertEqual(safety.safety_fwd_hook(0, primary[0]), 2)
        self.assertEqual(safety.safety_fwd_hook(2, primary[0]), -1)
        for frame in displays:
          self.assertTrue(safety.safety_tx_hook(self.packet(frame)))
          self.assertEqual(safety.safety_fwd_hook(0, frame[0]), 2)
          self.assertEqual(safety.safety_fwd_hook(2, frame[0]), -1)
        safety.set_relay_malfunction(True)
        self.assertFalse(safety.safety_tx_hook(self.packet(primary)))

  def test_raw_conflicts_and_native_actuation_boundary(self):
    for car in CARS:
      cp, _, safety, _, _, steering, displays, _ = self.joined(car, "lfa", display=True)
      active = steering[0]
      for raw_or in (HyundaiSafetyFlags.LONG, HyundaiSafetyFlags.EV_GAS, HyundaiSafetyFlags.CARNIVAL_ALT_RESUME,
                     HyundaiSafetyFlags.CAN_REFRESH_MSGS):
        bad = cp.safetyConfigs[-1].safetyParam | int(raw_or)
        self.assertEqual(safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundaiCanfd, bad), 0)
        safety.init_tests()
        self.assertFalse(safety.safety_tx_hook(self.packet(active)), hex(bad))
      _, _, safety, _, _, steering, _, _ = self.joined(car, "lfa", display=True)
      active = steering[0]
      self.assertTrue(safety.safety_tx_hook(self.packet(active)))
      self.assertFalse(safety.safety_tx_hook(self.packet((active[0], active[1], 1 - active[2]))))
      self.assertFalse(safety.safety_tx_hook(self.packet((active[0], active[1][:-8], active[2]))))
      for addr in (0x7C4, 0xEA, 0x730):
        self.assertFalse(safety.safety_tx_hook(self.packet((addr, bytes(8), 0))))
      self.assertFalse(safety.safety_tx_hook(self.packet((0x1A0, bytes(32), 0))))
      self.assertTrue(all(f[0] in DISPLAY_IDS for f in displays))

  def test_actual_cp_geometry_matches_host_vm(self):
    expected = {CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN: (2171.0, 2.81, 13.72, -0.0005968975988),
                CAR.KIA_SPORTAGE_2026: (1871.0, 2.756, 13.7, -0.0006085929296)}
    for car, (mass, wheelbase, ratio, slip) in expected.items():
      cp = params(car)
      self.assertAlmostEqual(cp.mass, mass, places=3)
      self.assertAlmostEqual(cp.wheelbase, wheelbase, places=6)
      self.assertAlmostEqual(cp.steerRatio, ratio, places=6)
      from opendbc.car.vehicle_model import VehicleModel, calc_slip_factor
      self.assertAlmostEqual(calc_slip_factor(VehicleModel(cp)), slip, places=9)


if __name__ == "__main__":
  unittest.main()
