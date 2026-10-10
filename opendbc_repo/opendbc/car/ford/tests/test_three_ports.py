import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.ford.carcontroller import CarController
from opendbc.car.ford.carstate import CarState
from opendbc.car.ford.interface import CarInterface
from opendbc.car.ford.values import CAR, DBC, FordFlags, FordSafetyFlags
from opendbc.car.ford.fingerprints import FW_VERSIONS
from opendbc.car.ford.radar_interface import RadarInterface
from opendbc.car.fw_versions import match_fw_to_car
from opendbc.safety.tests.libsafety import libsafety_py


PORTS = (CAR.FORD_EDGE_MK2, CAR.FORD_MONDEO_MK5, CAR.FORD_TRANSIT_MK5)


def params(candidate, alpha=False, release=False):
  fingerprint = gen_empty_fingerprint()
  fingerprint[0][0x5A] = 8
  fingerprint[2][0x3D6] = 8
  fingerprint[2][0x186] = 8
  return CarInterface.get_params(candidate, fingerprint, [], alpha, release, False)


class TestFordThreePorts(unittest.TestCase):
  @staticmethod
  def firmware(candidate):
    return [structs.CarParams.CarFw(ecu=ecu, address=addr, subAddress=0 if sub is None else sub,
                                    fwVersion=versions[0], brand="ford")
            for (ecu, addr, sub), versions in FW_VERSIONS[candidate].items()]

  def test_production_firmware_requires_four_platform_sources(self):
    required = (structs.CarParams.Ecu.eps, structs.CarParams.Ecu.abs,
                structs.CarParams.Ecu.fwdRadar, structs.CarParams.Ecu.fwdCamera)
    for candidate in PORTS:
      full = self.firmware(candidate)
      for allow_exact in (True, False):
        with self.subTest(candidate=candidate, allow_exact=allow_exact, case="complete"):
          self.assertEqual(match_fw_to_car(full, "", allow_exact=allow_exact, log=False)[1], {candidate})
        for omitted in required:
          with self.subTest(candidate=candidate, allow_exact=allow_exact, omitted=omitted):
            partial = [fw for fw in full if fw.ecu != omitted]
            for vin in ("", "WF0XXXXXX00000000"):
              self.assertEqual(match_fw_to_car(partial, vin, allow_exact=allow_exact, log=False)[1], set())
    mixed = self.firmware(CAR.FORD_EDGE_MK2) + self.firmware(CAR.FORD_MONDEO_MK5)
    for allow_exact in (True, False):
      self.assertEqual(match_fw_to_car(mixed, "", allow_exact=allow_exact, log=False)[1],
                       {CAR.FORD_EDGE_MK2, CAR.FORD_MONDEO_MK5})
    self.assertEqual(match_fw_to_car(self.firmware(CAR.FORD_FOCUS_MK4), "", allow_exact=False, log=False)[1],
                     {CAR.FORD_FOCUS_MK4})

  def test_new_platform_ownership_and_classic_long_selection(self):
    for candidate in PORTS:
      with self.subTest(candidate=candidate):
        stock = params(candidate)
        self.assertFalse(stock.openpilotLongitudinalControl)
        self.assertAlmostEqual(stock.steerActuatorDelay, 0.05 if candidate == CAR.FORD_TRANSIT_MK5 else 0.22, places=7)
        self.assertTrue(stock.safetyConfigs[-1].safetyParam & FordSafetyFlags.NEW_PORT)
        self.assertFalse(stock.safetyConfigs[-1].safetyParam & FordSafetyFlags.LONG_CONTROL)
        requested = params(candidate, alpha=True)
        self.assertTrue(requested.openpilotLongitudinalControl)
        self.assertTrue(requested.safetyConfigs[-1].safetyParam & FordSafetyFlags.LONG_CONTROL)
        if candidate == CAR.FORD_MONDEO_MK5:
          self.assertFalse(params(candidate, alpha=True, release=True).openpilotLongitudinalControl)
    self.assertAlmostEqual(params(CAR.FORD_MUSTANG_MACH_E_MK1).steerActuatorDelay, 0.22, places=7)
    self.assertFalse(params(CAR.FORD_BRONCO_SPORT_MK1).openpilotLongitudinalControl)
    self.assertTrue(params(CAR.FORD_BRONCO_SPORT_MK1, alpha=True).openpilotLongitudinalControl)

  def test_real_edge_angle_and_mondeo_gear_parsers(self):
    cases: tuple[tuple[CAR, str, dict[str, float]], ...] = (
      (CAR.FORD_EDGE_MK2, "TransGearData", {"GearLvrPos_D_Actl": 4}),
      (CAR.FORD_MONDEO_MK5, "Gear_Shift_by_Wire_FD1", {"TrnRng_D_RqGsm": 4}),
    )
    for candidate, source_name, source_values in cases:
      with self.subTest(candidate=candidate):
        cp = params(candidate)
        self.assertEqual(cp.transmissionType, structs.CarParams.TransmissionType.automatic)
        state = CarState(cp)
        parsers = state.get_can_parsers(cp)
        packer = CANPacker(DBC[candidate][Bus.pt])
        messages = [packer.make_can_msg(source_name, 0, source_values)]
        if candidate == CAR.FORD_EDGE_MK2:
          messages += [packer.make_can_msg("SteeringPinion_Data_Alt", 0, {"StePinRelInit_An_Sns": 10.}),
                       packer.make_can_msg("ParkAid_Data", 0, {"ExtSteeringAngleReq2": 12.,
                                                                "EPASExtAngleStatReq": 0, "ApaSys_D_Stat": 0})]
        parsers[Bus.pt].update([(1_000_000_000, messages)])
        out = state.update(parsers)
        self.assertEqual(out.gearShifter, structs.CarState.GearShifter.sport)
        if candidate == CAR.FORD_EDGE_MK2:
          self.assertFalse(out.vehicleSensorsInvalid)
          self.assertAlmostEqual(out.steeringAngleDeg, 12., places=1)

    # The existing CAN FD family still reads the powertrain gear, even when a
    # conflicting shift-by-wire frame is present on the same bus.
    candidate = CAR.FORD_MUSTANG_MACH_E_MK1
    cp = params(candidate)
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    state.update(parsers)
    packer = CANPacker(DBC[candidate][Bus.pt])
    parsers[Bus.pt].update([(1_000_000_000, [packer.make_can_msg("PowertrainData_10", 0, {"TrnRng_D_Rq": 3}),
                                               packer.make_can_msg("Gear_Shift_by_Wire_FD1", 0, {"TrnRng_D_RqGsm": 4})])])
    self.assertEqual(state.update(parsers).gearShifter, structs.CarState.GearShifter.drive)

  def test_mondeo_camera_radar_needs_current_confident_object(self):
    cp = params(CAR.FORD_MONDEO_MK5)
    radar = RadarInterface(cp)
    packer = CANPacker(DBC[CAR.FORD_MONDEO_MK5][Bus.pt])
    observed = packer.make_can_msg("Steer_Assist_Data", 2,
                                   {"CmbbObjConfdnc_D_Stat": 2, "CmbbObjDistLong_L_Actl": 24.,
                                    "CmbbObjRelLong_V_Actl": -2.})
    first = radar.update([(1_000_000_000, [observed])])
    self.assertEqual(len(first.points), 1)
    self.assertAlmostEqual(first.points[0].dRel, 24.)
    self.assertAlmostEqual(first.points[0].vRel, -2.)
    self.assertIsNone(radar.update([(1_100_000_000, [])]))
    lost = packer.make_can_msg("Steer_Assist_Data", 2, {"CmbbObjConfdnc_D_Stat": 0})
    self.assertEqual(len(radar.update([(1_150_000_000, [lost])]).points), 0)

  def check_transit_source_gates_real_controller_messages(self, yaw_rate):
    cp = params(CAR.FORD_TRANSIT_MK5)
    self.assertTrue(cp.flags & FordFlags.LKA_STEERING)
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    packer = CANPacker(DBC[CAR.FORD_TRANSIT_MK5][Bus.pt])
    source = packer.make_can_msg("Lane_Assist_Data3_FD1", 0, {"LaActAvail_D_Actl": 3})
    received = []
    for count in range(1, 7):
      messages = [
        packer.make_can_msg("BrakeSysFeatures", 0,
                                      {"Veh_V_ActlBrk": 108., "VehVActlBrk_D_Qf": 3, "VehVActlBrk_No_Cnt": count}),
        packer.make_can_msg("EngVehicleSpThrottle2", 0, {"Veh_V_ActlEng": 108., "VehVActlEng_D_Qf": 3}),
        packer.make_can_msg("Yaw_Data_FD1", 0, {"VehYaw_W_Actl": yaw_rate,
                                                            "VehYawWActl_D_Qf": 3, "VehRollYaw_No_Cnt": count}),
        packer.make_can_msg("EngBrakeData", 0, {"BpedDrvAppl_D_Actl": 1, "CcStat_D_Actl": 5}),
        packer.make_can_msg("EngVehicleSpThrottle", 0, {"ApedPos_Pc_ActlArb": 0}),
        packer.make_can_msg("DesiredTorqBrk", 0, {"VehStop_D_Stat": 0}),
      ]
      if count == 6:
        messages += [source, packer.make_can_msg("SteeringPinion_Data", 0,
                                                {"StePinCompAnEst_D_Qf": 3})]
      received += messages
      parsers[Bus.pt].update([(940_000_000 + count * 10_000_000, messages)])
    parsers[Bus.cam].update([(1_000_000_000, [packer.make_can_msg("LateralMotionControl", 2, {})])])
    out = state.update(parsers)
    self.assertTrue(state.lkas_available)
    self.assertAlmostEqual(out.vEgoRaw, 30., places=1)
    self.assertTrue(out.cruiseState.enabled)
    control = structs.CarControl()
    control.latActive = True
    control.actuators.steeringAngleDeg = out.steeringAngleDeg + 1.
    control.actuators.curvature = -yaw_rate / 30. if yaw_rate else 0.01023
    state.out = out.as_reader()
    controller = CarController(DBC[CAR.FORD_TRANSIT_MK5], cp)
    _, messages = controller.update(control.as_reader(), state, 1_000_000_000)
    self.assertIn(0x3D3, [msg[0] for msg in messages])
    self.assertIn(0x3CA, [msg[0] for msg in messages])
    self.assertEqual(next(msg for msg in messages if msg[0] == 0x3CA)[1][0] >> 5, 2)
    self.assertLess(abs(controller.apply_lka_curvature_last), 0.00013)
    if yaw_rate:
      self.assertGreater(controller.apply_lka_curvature_last * yaw_rate, 0.)
    safety = libsafety_py.libsafety
    self.assertEqual(safety.set_safety_hooks(structs.CarParams.SafetyModel.ford,
                                             int(cp.safetyConfigs[-1].safetyParam)), 0)
    safety.init_tests()
    safety.set_controls_allowed(True)
    for msg in received:
      self.assertTrue(safety.safety_rx_hook(libsafety_py.make_CANPacket(msg[0], msg[2], msg[1])))
    for address in (0x3D3, 0x3CA):
      msg = next(msg for msg in messages if msg[0] == address)
      self.assertTrue(safety.safety_tx_hook(libsafety_py.make_CANPacket(msg[0], msg[2], msg[1])))

    # The next 33 Hz command must retain the measured-yaw coordinate in both
    # host limiting and the native curvature/error checks.
    controller.frame = 3
    _, repeated = controller.update(control.as_reader(), state, 1_030_000_000)
    if yaw_rate:
      self.assertGreater(controller.apply_lka_curvature_last * yaw_rate, 0.)
    repeated_lka = next(msg for msg in repeated if msg[0] == 0x3CA)
    self.assertTrue(safety.safety_tx_hook(libsafety_py.make_CANPacket(repeated_lka[0], repeated_lka[2], repeated_lka[1])))

    controller.frame = 6
    _, stale_messages = controller.update(control.as_reader(), state, 1_200_000_000)
    self.assertEqual(next(msg for msg in stale_messages if msg[0] == 0x3CA)[1][0] >> 5, 0)
    denied = packer.make_can_msg("Lane_Assist_Data3_FD1", 0,
                                  {"LaActAvail_D_Actl": 3, "LaActDeny_B_Actl": 1})
    parsers[Bus.pt].update([(1_230_000_000, [denied])])
    state.update(parsers)
    self.assertFalse(state.lkas_available)

  def test_transit_source_gates_real_controller_messages(self):
    for yaw_rate in (0., -0.03, 0.03):
      with self.subTest(yaw_rate=yaw_rate):
        self.check_transit_source_gates_real_controller_messages(yaw_rate)
