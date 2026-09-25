import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.fingerprints import all_legacy_fingerprint_cars
from opendbc.car.fw_versions import match_fw_to_car
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.fingerprints import FW_VERSIONS
from opendbc.car.hyundai.hyundaicanfd import CanBus, hkg_can_fd_checksum
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import (CANFD_ANGLE_MODEL_BITS, CANFD_ANGLE_MODEL_BANK_BIT,
                                        CANFD_ANGLE_OBSERVED_ADAS_BIT, CAR, DBC, HyundaiFlags,
                                        HyundaiSafetyFlags)
from opendbc.car.lateral import get_max_angle_vm
from opendbc.safety.tests.libsafety import libsafety_py


CARS = (CAR.HYUNDAI_AZERA_HEV_7TH_GEN, CAR.KIA_SORENTO_HEV_4TH_GEN_LFA2, CAR.KIA_SPORTAGE_HEV_2026)
TOPOLOGIES = ("lka", "lka_alt", "lfa", "lfa_alt")
STEER_IDS = (0x50, 0x110, 0x12A, 0xCB)


def params(car, topology="lka_alt", *, hybrid=False, adas=False, release=False, alpha=False):
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
  button = "CRUISE_BUTTONS_ALT" if topology == "lfa_alt" else "CRUISE_BUTTONS"
  scc_bus = can.ECAN if topology.startswith("lka") else can.CAM
  gas_values = {"ACCELERATOR_PEDAL": 4.0} if gas and fuel == "ACCELERATOR_ALT" else \
               {"ACCELERATOR_PEDAL_PRESSED": 1} if gas and fuel == "ACCELERATOR_BRAKE_ALT" else {}
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


class TestHyundaiAngleHybridsThree(unittest.TestCase):
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
             brake=False, gas=False, cruise=True, desired=1.0):
    cp = params(car, topology, hybrid=hybrid, adas=adas, release=True, alpha=True)
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    packer, frames = source_frames(cp, topology, speed=speed, measured=measured, gear=gear,
                                   brake=brake, gas=gas, cruise=cruise)
    safety = self.mode(cp)
    for frame in frames:
      self.assertTrue(safety.safety_rx_hook(self.packet(frame)), (car, topology, hex(frame[0])))
    for parser in parsers.values():
      parser.update((1_000_000_000, [frame for frame in frames if frame[2] == parser.bus]))
    state.out = state.update(parsers)
    self.assertTrue(parsers[Bus.pt].can_valid, (car, topology, hybrid))
    self.assertEqual(state.out.cruiseState.enabled, cruise)
    control = structs.CarControl()
    control.enabled = True
    control.latActive = True
    control.actuators.steeringAngleDeg = desired
    controller = CarController(DBC[car], cp)
    _, sends = controller.update(control.as_reader(), state, 1_000_000_000)
    steering = [frame for frame in sends if frame[0] in STEER_IDS]
    return cp, state, safety, control, controller, steering, packer

  def test_all_models_fuel_sources_and_topologies_joined(self):
    for car in CARS:
      for topology in TOPOLOGIES:
        for hybrid in (False, True):
          with self.subTest(car=car, topology=topology, hybrid=hybrid):
            cp, state, safety, _, _, steering, packer = self.joined(car, topology, hybrid=hybrid)
            self.assertEqual(bool(cp.flags & HyundaiFlags.HYBRID), hybrid)
            self.assertFalse(cp.alphaLongitudinalAvailable)
            self.assertFalse(cp.openpilotLongitudinalControl)
            self.assertTrue(cp.pcmCruise)
            self.assertTrue(cp.steerControlType == structs.CarParams.SteerControlType.angle)
            self.assertEqual(cp.safetyConfigs[-1].safetyParam & 0x3800, CANFD_ANGLE_MODEL_BITS[car.name])
            self.assertTrue(cp.safetyConfigs[-1].safetyParam & CANFD_ANGLE_MODEL_BANK_BIT)
            self.assertEqual(bool(cp.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.HYBRID_GAS), hybrid)
            self.assertFalse(cp.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG)
            self.assertEqual(state.out.gearShifter, structs.CarState.GearShifter.drive)
            self.assertTrue(safety.get_controls_allowed())
            self.assertEqual(steering[0][0], 0x50 if topology == "lka" else 0x110 if topology == "lka_alt" else 0x12A)
            for frame in steering:
              self.assertEqual(int.from_bytes(frame[1][:2], "little"),
                               hkg_can_fd_checksum(frame[0], None, bytearray(frame[1])))
              self.assertTrue(safety.safety_tx_hook(self.packet(frame)), (car, topology, hybrid, hex(frame[0])))
            self.assertNotEqual((steering[0][1][11] << 6) | (steering[0][1][10] >> 2), 0)
            self.assertFalse(safety.safety_tx_hook(self.packet((steering[0][0], steering[0][1], 1 - steering[0][2]))))
            self.assertFalse(safety.safety_tx_hook(self.packet((steering[0][0], steering[0][1][:-8], steering[0][2]))))
            self.assertFalse(any(frame[0] == 0x1A0 for frame in steering))
            self.assertEqual(packer.dbc.name_to_msg["LFA"].address, 0x12A)

  def test_parsed_non_drive_brake_and_cruise_neutral(self):
    for car in CARS:
      for topology in TOPOLOGIES:
        for gear in (0, 6, 7, 1, 5):  # P, N, R, unknown, D from GEAR_ALT_2
          for direction in (-1, 1):
            cp, state, safety, _, _, steering, _ = self.joined(car, topology, hybrid=True,
                                                                gear=gear, desired=direction * 8.0)
            with self.subTest(car=car, topology=topology, gear=gear, direction=direction):
              self.assertEqual((steering[0][1][9] >> 4) & 3, 2 if gear == 5 else 1)
              self.assertTrue(safety.safety_tx_hook(self.packet(steering[0])))
              if gear != 5:
                self.assertNotEqual(state.out.gearShifter, structs.CarState.GearShifter.drive)
              self.assertTrue(safety.get_controls_allowed())
      for brake, gas, cruise in ((True, False, True), (False, True, True), (False, False, False)):
        cp, state, safety, _, _, steering, _ = self.joined(car, "lfa_alt", hybrid=True,
                                                            brake=brake, gas=gas, cruise=cruise)
        self.assertEqual((steering[0][1][9] >> 4) & 3, 1)
        self.assertTrue(safety.safety_tx_hook(self.packet(steering[0])))
        self.assertEqual(state.out.gasPressed, gas)
        if brake or not cruise:
          self.assertFalse(safety.get_controls_allowed())

  def test_native_exact_fuel_source_and_host_parser_health(self):
    for car in CARS:
      for hybrid in (False, True):
        for topology in ("lka_alt", "lfa_alt"):
          cp = params(car, topology, hybrid=hybrid)
          _, wrong = source_frames(cp, topology, wrong_fuel=True)
          safety = self.mode(cp)
          for frame in wrong:
            safety.safety_rx_hook(self.packet(frame))
          safety.safety_tick()
          self.assertFalse(safety.safety_config_valid(), (car, hybrid, topology))
          self.assertFalse(safety.get_controls_allowed())
          state = CarState(cp)
          parsers = state.get_can_parsers(cp)
          for parser in parsers.values():
            parser.update((1_000_000_000, [frame for frame in wrong if frame[2] == parser.bus]))
          self.assertFalse(parsers[Bus.pt].can_valid)

  def test_native_required_bus_crc_counter_and_staleness(self):
    for car in CARS:
      for hybrid in (False, True):
        for topology in ("lka_alt", "lfa_alt"):
          cp = params(car, topology, hybrid=hybrid)
          packer, frames = source_frames(cp, topology)
          scc_addr = packer.dbc.name_to_msg["SCC_CONTROL"].address
          active_scc = [frame for frame in frames if frame[0] == scc_addr][-1]
          with self.subTest(car=car, hybrid=hybrid, topology=topology):
            safety = self.mode(cp)
            for frame in frames:
              if frame[0] == scc_addr:
                frame = (frame[0], frame[1], 1 - frame[2] if frame[2] in (0, 1) else 0)
              self.assertTrue(safety.safety_rx_hook(self.packet(frame)))
            safety.safety_tick()
            self.assertFalse(safety.get_controls_allowed())

            _, _, safety, _, _, _, _ = self.joined(car, topology, hybrid=hybrid)
            corrupt = bytearray(active_scc[1])
            corrupt[0] ^= 1
            self.assertFalse(safety.safety_rx_hook(self.packet((scc_addr, bytes(corrupt), active_scc[2]))))
            self.assertFalse(safety.get_controls_allowed())

            _, _, safety, _, _, _, _ = self.joined(car, topology, hybrid=hybrid)
            for _ in range(5):
              safety.safety_rx_hook(self.packet(active_scc))
            self.assertFalse(safety.get_controls_allowed())

            _, _, safety, _, _, _, _ = self.joined(car, topology, hybrid=hybrid)
            safety.set_timer(2_100_000)
            safety.safety_tick()
            self.assertFalse(safety.safety_config_valid())

  def test_observed_adas_sustained_two_frame_history(self):
    for car in CARS:
      for topology in ("lfa", "lfa_alt"):
        for speed_mps in (2.0, 10.0, 25.0, 35.0):
          for direction in (-1, 1):
            with self.subTest(car=car, topology=topology, speed=speed_mps, direction=direction):
              cp, state, safety, control, controller, _, _ = self.joined(
                car, topology, hybrid=True, adas=True, speed=speed_mps * 3.6,
                measured=direction * 10.0, desired=direction * 360.0)
              self.assertTrue(cp.safetyConfigs[-1].safetyParam & CANFD_ANGLE_OBSERVED_ADAS_BIT)
              for step in range(90):
                safety.set_timer(1_010_000 + step * 10_000)
                _, sends = controller.update(control.as_reader(), state, 1_010_000_000 + step * 10_000_000)
                steering = [frame for frame in sends if frame[0] in STEER_IDS]
                self.assertEqual([frame[0] for frame in steering], [0x12A, 0xCB])
                self.assertEqual((steering[0][1][9] >> 4) & 3, 1)
                for frame in steering:
                  self.assertTrue(safety.safety_tx_hook(self.packet(frame)),
                                  (car, topology, speed_mps, direction, step, hex(frame[0])))
              bound = get_max_angle_vm(max(state.out.vEgoRaw - 1.0, 1.0), controller.angle_vm, controller.params)
              self.assertGreater(abs(controller.apply_angle_last), min(5.0, bound * 0.7))
              self.assertLessEqual(abs(controller.apply_angle_last), min(360.0, bound) + 0.2)

  def test_direct_host_native_limit_matrix(self):
    for car in CARS:
      for topology in TOPOLOGIES:
        for speed_mps in (2.0, 10.0, 25.0, 35.0):
          for direction in (-1, 1):
            with self.subTest(car=car, topology=topology, speed=speed_mps, direction=direction):
              _, state, safety, control, controller, _, _ = self.joined(
                car, topology, hybrid=True, speed=speed_mps * 3.6,
                measured=direction * 10.0, desired=direction * 360.0)
              for step in range(90):
                safety.set_timer(1_010_000 + step * 10_000)
                _, sends = controller.update(control.as_reader(), state, 1_010_000_000 + step * 10_000_000)
                steering = [frame for frame in sends if frame[0] in STEER_IDS]
                self.assertEqual(len(steering), 1)
                self.assertTrue(safety.safety_tx_hook(self.packet(steering[0])),
                                (car, topology, speed_mps, direction, step))
              bound = get_max_angle_vm(max(state.out.vEgoRaw - 1.0, 1.0), controller.angle_vm, controller.params)
              self.assertGreater(abs(controller.apply_angle_last), min(5.0, bound * 0.7))
              self.assertLessEqual(abs(controller.apply_angle_last), min(360.0, bound) + 0.2)

  def test_other_actuation_fields_and_relay(self):
    for car in CARS:
      for topology in TOPOLOGIES:
        observed = topology.startswith("lfa")
        _, _, safety, _, _, steering, _ = self.joined(car, topology, hybrid=True, adas=observed)
        primary = steering[-1]
        if observed:
          self.assertEqual([f[0] for f in steering], [0x12A, 0xCB])
          self.assertTrue(safety.safety_tx_hook(self.packet(steering[0])))
        angle_frame = steering[0] if observed else primary
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
        if observed:
          for byte_index, bit in ((3, 0x1), (7, 0x1), (8, 0x1)):
            data = bytearray(primary[1])
            data[byte_index] ^= bit
            data[:2] = hkg_can_fd_checksum(primary[0], None, data).to_bytes(2, "little")
            self.assertFalse(safety.safety_tx_hook(self.packet((primary[0], bytes(data), primary[2]))))
        self.assertTrue(safety.safety_tx_hook(self.packet(primary)))
        self.assertEqual(safety.safety_fwd_hook(0, primary[0]), 2)
        self.assertEqual(safety.safety_fwd_hook(2, primary[0]), -1)
        safety.set_relay_malfunction(True)
        self.assertFalse(safety.safety_tx_hook(self.packet(primary)))

  def test_no_automatic_identification(self):
    self.assertFalse(set(CARS) & FW_VERSIONS.keys())
    self.assertFalse(set(CARS) & set(all_legacy_fingerprint_cars()))
    frozen = {
      CAR.HYUNDAI_AZERA_HEV_7TH_GEN: (
        b'\xf1\x00GN7HMFC  AT KOR LHD 1.00 1.01 99211-N1110 240423',
        b'\xf1\x00GN7_ RDR -----      1.00 1.00 99110-N1100         ',
      ),
      CAR.KIA_SORENTO_HEV_4TH_GEN_LFA2: (
        b'\xf1\x00MQ4HMFC  AT USA LHD 1.00 1.00 99210-P2600 250617',
        b'\xf1\x00MQ4_ RDR -----      1.00 1.01 99110-P2500         ',
      ),
      CAR.KIA_SPORTAGE_HEV_2026: (
        b'\xf1\x00NQ51.011.021.012551000HKP_NQ524_50509099211P1110',
        b'\xf1\x00NQ5__               1.00 1.04 99110CH100          ',
      ),
    }
    for car, (camera, radar) in frozen.items():
      fw = [structs.CarParams.CarFw(ecu=ecu, address=addr, subAddress=0, fwVersion=version, brand="hyundai")
            for ecu, addr, version in ((structs.CarParams.Ecu.fwdCamera, 0x7C4, camera),
                                       (structs.CarParams.Ecu.fwdRadar, 0x7D0, radar))]
      for observed in (fw, fw[:1], fw[1:], [fw[0], structs.CarParams.CarFw(
          ecu=structs.CarParams.Ecu.fwdRadar, address=0x7D0, subAddress=0,
          fwVersion=frozen[CAR.KIA_SPORTAGE_HEV_2026 if car != CAR.KIA_SPORTAGE_HEV_2026 else
                           CAR.HYUNDAI_AZERA_HEV_7TH_GEN][1], brand="hyundai")]):
        _, matched = match_fw_to_car(observed, "", log=False)
        self.assertFalse(set(CARS) & matched, (car, matched))
