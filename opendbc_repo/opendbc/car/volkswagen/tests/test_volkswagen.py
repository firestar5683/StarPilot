import random
import re
import unittest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, DT_CTRL, structs
from opendbc.car.structs import CarParams
from opendbc.car.fw_versions import match_fw_to_car, match_fw_to_car_exact
from opendbc.car.vin import VIN_UNKNOWN
from opendbc.car.volkswagen.carcontroller import CarController, HCAMitigation
from opendbc.car.volkswagen.carstate import CarState
from opendbc.car.volkswagen.interface import CarInterface
from opendbc.car.volkswagen.values import (CAR, DBC, CanBus, CarControllerParams as CCP, FW_QUERY_CONFIG, WMI,
                                            VolkswagenFlags, VolkswagenSafetyFlags)
from opendbc.car.volkswagen.fingerprints import FW_VERSIONS

Ecu = CarParams.Ecu

CHASSIS_CODE_PATTERN = re.compile('[A-Z0-9]{2}')
# TODO: determine the unknown groups
SPARE_PART_FW_PATTERN = re.compile(b'\xf1\x87(?P<gateway>[0-9][0-9A-Z]{2})(?P<unknown>[0-9][0-9A-Z][0-9])(?P<unknown2>[0-9A-Z]{2}[0-9])([A-Z0-9]| )')


class TestVolkswagenHCAMitigation(unittest.TestCase):
  STUCK_TORQUE_FRAMES = round(CCP.STEER_TIME_STUCK_TORQUE / (DT_CTRL * CCP.STEER_STEP))

  def test_same_torque_mitigation(self):
    """Same-torque nudge fires at the threshold, in the correct direction, and resets cleanly."""
    hca_mitigation = HCAMitigation(CCP)

    for actuator_value in (-CCP.STEER_MAX, -1, 0, 1, CCP.STEER_MAX):
      hca_mitigation.update(0, 0)  # Reset mitigation state
      for frame in range(self.STUCK_TORQUE_FRAMES + 2):
        should_nudge = actuator_value != 0 and frame == self.STUCK_TORQUE_FRAMES
        expected_torque = actuator_value - (1, -1)[actuator_value < 0] if should_nudge else actuator_value
        assert hca_mitigation.update(actuator_value, actuator_value) == expected_torque, f"{frame=}"

class TestVolkswagenPlatformConfigs(unittest.TestCase):
  MEB_BATCH = (CAR.VOLKSWAGEN_ID3_MK1, CAR.VOLKSWAGEN_ID3_MK2,
               CAR.AUDI_Q4_MK1, CAR.AUDI_Q4_MK2,
               CAR.SKODA_ENYAQ_MK1, CAR.SKODA_ENYAQ_MK2)

  def test_meb_firmware_only_ambiguity_stays_within_generation(self):
    # Shared radar part numbers cannot identify the body/chassis without VIN.
    for car_model in self.MEB_BATCH:
      with self.subTest(car_model=car_model):
        live = {ecu[1:]: set(versions) for ecu, versions in FW_VERSIONS[car_model].items()}
        matches = match_fw_to_car_exact(live, "volkswagen")
        self.assertIn(car_model, matches)
        self.assertTrue(all(CAR[name].config.flags & VolkswagenFlags.MEB for name in matches))
        self.assertTrue(all(bool(CAR[name].config.flags & VolkswagenFlags.MEB_GEN2) ==
                            bool(car_model.config.flags & VolkswagenFlags.MEB_GEN2) for name in matches))

  def test_meb_production_matcher_requires_matching_vin(self):
    for car_model in (*self.MEB_BATCH, CAR.VOLKSWAGEN_ID4_MK1, CAR.VOLKSWAGEN_ID4_MK2, CAR.CUPRA_BORN_MK1):
      with self.subTest(car_model=car_model):
        car_fw = [CarParams.CarFw(ecu=ecu, address=addr, subAddress=0 if sub is None else sub,
                                 fwVersion=versions[0], brand="volkswagen")
                  for (ecu, addr, sub), versions in FW_VERSIONS[car_model].items()]
        vin = ["0"] * 17
        vin[:3] = next(iter(car_model.config.wmis))
        vin[6:8] = next(iter(car_model.config.chassis_codes))
        vin[9] = next(iter(car_model.config.model_years)) if car_model.config.model_years else "M"
        raw_exact = match_fw_to_car_exact({(addr, sub): {versions[0]} for (_, addr, sub), versions in FW_VERSIONS[car_model].items()},
                                          "volkswagen")
        exact, matches = match_fw_to_car(car_fw, "".join(vin), log=False)
        self.assertEqual(exact, len(raw_exact) == 1)
        self.assertEqual(matches, {car_model})

        for unknown_vin in (VIN_UNKNOWN, "bad", "".join(vin[:6] + ["0", "0"] + vin[8:])):
          exact, unresolved = match_fw_to_car(car_fw, unknown_vin, log=False)
          self.assertTrue(exact)
          self.assertEqual(unresolved, raw_exact)

    # A newer VIN cannot turn older-generation firmware into a candidate.
    older = CAR.VOLKSWAGEN_ID3_MK1
    old_fw = [CarParams.CarFw(ecu=ecu, address=addr, subAddress=0 if sub is None else sub,
                             fwVersion=versions[0], brand="volkswagen")
              for (ecu, addr, sub), versions in FW_VERSIONS[older].items()]
    mismatched = ["0"] * 17
    mismatched[:3] = "WVW"
    mismatched[6:8] = "E1"
    mismatched[9] = "R"
    exact, unresolved = match_fw_to_car(old_fw, "".join(mismatched), log=False)
    self.assertTrue(exact)
    self.assertGreater(len(unresolved), 1)
    self.assertNotIn(CAR.VOLKSWAGEN_ID3_MK2, unresolved)

  def test_meb_generation_years_disambiguate_shared_chassis(self):
    pairs = ((CAR.VOLKSWAGEN_ID3_MK1, CAR.VOLKSWAGEN_ID3_MK2),
             (CAR.AUDI_Q4_MK1, CAR.AUDI_Q4_MK2),
             (CAR.SKODA_ENYAQ_MK1, CAR.SKODA_ENYAQ_MK2))
    for older, newer in pairs:
      for expected, year in ((older, next(iter(older.config.model_years))),
                             (newer, next(iter(newer.config.model_years))), (None, "0")):
        with self.subTest(older=older, newer=newer, year=year):
          vin = ["0"] * 17
          vin[:3] = next(iter(older.config.wmis))
          vin[6:8] = next(iter(older.config.chassis_codes))
          vin[9] = year
          radar_fw = FW_VERSIONS[older][Ecu.fwdRadar, 0x757, None][0]
          matches = FW_QUERY_CONFIG.match_fw_to_car_fuzzy({(0x757, None): [radar_fw]}, "".join(vin), FW_VERSIONS)
          self.assertEqual(matches, {expected} if expected is not None else set())

  def test_id4_chassis_year_and_radar_firmware_match(self):
    radar_fw = FW_VERSIONS[CAR.VOLKSWAGEN_ID4_MK1][Ecu.fwdRadar, 0x757, None][0]
    for wmi in ("1V2", "WVW", "WVG", "XXX"):
      for chassis in ("E2", "E8"):
        for year in ("M", "N", "P", "R", "S", "L", "T", "0"):
          vin = list("00000000000000000")
          vin[:3], vin[6:8], vin[9] = wmi, chassis, year
          expected = set()
          if wmi != "XXX":
            if year in ("M", "N", "P"):
              expected = {CAR.VOLKSWAGEN_ID4_MK1}
            elif chassis == "E8" and year in ("R", "S"):
              expected = {CAR.VOLKSWAGEN_ID4_MK2}
          for firmware in ({(0x757, None): [radar_fw]}, {}, {(0x757, None): [b"unknown"]}):
            with self.subTest(wmi=wmi, chassis=chassis, year=year, firmware=firmware):
              matches = FW_QUERY_CONFIG.match_fw_to_car_fuzzy(firmware, "".join(vin), FW_VERSIONS)
              self.assertEqual(matches, expected if firmware.get((0x757, None)) == [radar_fw] else set())

  def test_six_meb_interfaces_and_native_controller_frames(self):
    for car_model in self.MEB_BATCH:
      gen2 = bool(car_model.config.flags & VolkswagenFlags.MEB_GEN2)
      for gateway in (False, True):
        for alpha_long in (False, True):
          with self.subTest(car_model=car_model, gateway=gateway, alpha_long=alpha_long):
            fingerprint = {bus: {} for bus in range(8)}
            if gateway:
              fingerprint[1][0x13D] = 32  # observed QFK_01 at J533
            fingerprint[0][0x24C] = 16  # optional Side Assist
            cp = CarInterface.get_params(car_model, fingerprint, [], alpha_long, False, False)
            self.assertTrue(cp.flags & VolkswagenFlags.MEB)
            self.assertEqual(bool(cp.flags & VolkswagenFlags.MEB_GEN2), gen2)
            self.assertEqual(cp.safetyConfigs[-1].safetyModel, CarParams.SafetyModel.volkswagenMeb)
            self.assertEqual(cp.safetyConfigs[-1].safetyParam,
                             VolkswagenSafetyFlags.MEB_ALT_CRC if gen2 else 0)
            self.assertEqual(DBC[car_model][Bus.pt], "vw_meb_2024_generated" if gen2 else "vw_meb_generated")
            self.assertEqual(cp.dashcamOnly, not gateway)
            self.assertTrue(cp.openpilotLongitudinalControl)  # retained gateway system-long default
            self.assertFalse(cp.pcmCruise)
            if not gateway:
              # card.py makes dashcamOnly configurations passive with no-output safety.
              continue

            can = CanBus(cp)
            packer = CANPacker(DBC[car_model][Bus.pt])
            state = CarState(cp)
            parsers = state.get_can_parsers(cp)
            state.update(parsers)  # register lazily accessed DBC messages
            bsm_bus = can.pt if gen2 else can.cam
            bsm_parser = parsers[Bus.pt] if gen2 else parsers[Bus.cam]
            bsm = packer.make_can_msg("MEB_Side_Assist_01", bsm_bus, {"Blind_Spot_Info_Driver": 1})
            self.assertEqual(bsm_parser.update((1_000_000_000, [bsm])), {0x24C})
            incoming = [packer.make_can_msg("Motor_51", can.pt, {"TSK_Status": 3}),
                        packer.make_can_msg("Motor_54", can.pt, {"Engine_On": 1})]
            self.assertEqual(parsers[Bus.pt].update((1_000_000_000, incoming)), {0x10B, 0x14C})
            state.out = state.update(parsers)
            self.assertTrue(state.out.leftBlindspot)
            self.assertTrue(state.out.cruiseState.available)
            self.assertFalse(state.out.accFaulted)

            control = structs.CarControl()
            control.enabled = control.longActive = True
            control.actuators.accel = 1.0
            control.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid
            controller = CarController(DBC[car_model], cp)
            _, sent = controller.update(control.as_reader(), state, 1_000_000_000)
            self.assertEqual([(addr, len(data), bus) for addr, data, bus in sent],
                             [(0x303, 24, can.pt), (0x14D, 32, can.pt), (0x397, 8, can.pt), (0x300, 48, can.pt)])
            observed = CANParser(DBC[car_model][Bus.pt], [("HCA_03", 0), ("ACC_18", 0), ("ACC_19", 0)], can.pt)
            self.assertEqual(observed.update((1_010_000_000, sent)), {0x303, 0x14D, 0x300})
            self.assertEqual(observed.vl["ACC_18"]["ACC_Status_ACC"], 3)
            self.assertAlmostEqual(observed.vl["ACC_18"]["ACC_Sollbeschleunigung_02"], 1.0)

  def test_spare_part_fw_pattern(self):
    # Relied on for determining if a FW is likely VW
    for platform, ecus in FW_VERSIONS.items():
      with self.subTest(platform=platform.value):
        for fws in ecus.values():
          for fw in fws:
            assert SPARE_PART_FW_PATTERN.match(fw) is not None, f"Bad FW: {fw}"

  def test_chassis_codes(self):
    for platform in CAR:
      with self.subTest(platform=platform.value):
        assert len(platform.config.wmis) > 0, "WMIs not set"
        assert len(platform.config.chassis_codes) > 0, "Chassis codes not set"
        assert all(CHASSIS_CODE_PATTERN.match(cc) for cc in
                   platform.config.chassis_codes), "Bad chassis codes"

        # MEB model generations can share a chassis when VIN years separate them.
        for comp in CAR:
          if platform == comp:
            continue
          shared = platform.config.chassis_codes & comp.config.chassis_codes
          if shared:
            both_meb = bool(platform.config.flags & VolkswagenFlags.MEB and comp.config.flags & VolkswagenFlags.MEB)
            years_a = getattr(platform.config, "model_years", set())
            years_b = getattr(comp.config, "model_years", set())
            assert both_meb and years_a and years_b and not years_a & years_b, f"Shared chassis codes: {comp}"

  def test_custom_fuzzy_fingerprinting(self):
    all_radar_fw = list({fw for ecus in FW_VERSIONS.values() for fw in ecus[Ecu.fwdRadar, 0x757, None]})

    for platform in CAR:
      with self.subTest(platform=platform.name):
        for wmi in WMI:
          for chassis_code in platform.config.chassis_codes | {"00"}:
            for model_year in getattr(platform.config, "model_years", set()) or {"0"}:
              vin = ["0"] * 17
              vin[0:3] = wmi
              vin[6:8] = chassis_code
              vin[9] = model_year
              vin = "".join(vin)

              # VW radar part numbers are shared; VIN family/year resolves the car.
              for radar_fw in random.sample(all_radar_fw, 5) + [b'\xf1\x875Q0907572G \xf1\x890571', b'\xf1\x877H9907572AA\xf1\x890396']:
                should_match = ((wmi in platform.config.wmis and chassis_code in platform.config.chassis_codes) and
                                radar_fw in all_radar_fw)

                live_fws = {(0x757, None): [radar_fw]}
                matches = FW_QUERY_CONFIG.match_fw_to_car_fuzzy(live_fws, vin, FW_VERSIONS)

                expected_matches = {platform} if should_match else set()
                assert expected_matches == matches, "Bad match"
