import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.fw_versions import match_fw_to_car
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.carstate import CarState, get_non_scc_cruise_signals
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.radar_interface import RadarInterface, get_radar_can_parser
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags, HyundaiSafetyFlags
from opendbc.car.hyundai.fingerprints import FW_VERSIONS
from opendbc.car.structs import CarParams


NON_SCC_CARS = (
  CAR.GENESIS_G70_2021_NON_SCC, CAR.HYUNDAI_BAYON_1ST_GEN_NON_SCC,
  CAR.HYUNDAI_ELANTRA_2022_NON_SCC, CAR.HYUNDAI_ELANTRA_HEV_2022_NON_SCC,
  CAR.HYUNDAI_KONA_EV_NON_SCC, CAR.HYUNDAI_KONA_NON_SCC,
  CAR.KIA_CEED_PHEV_2022_NON_SCC, CAR.KIA_FORTE_2019_NON_SCC,
  CAR.KIA_FORTE_2021_NON_SCC, CAR.KIA_SELTOS_2023_NON_SCC,
)


def params(candidate, fingerprint=None, car_fw=None, alpha_long=True):
  return CarInterface.get_params(candidate, fingerprint or gen_empty_fingerprint(), car_fw or [], alpha_long, False, False)


class TestNonSccFamily(unittest.TestCase):
  def test_all_ten_have_stock_longitudinal_ownership_and_lateral_only_controller(self):
    for candidate in NON_SCC_CARS:
      for alpha_long in (False, True):
        with self.subTest(candidate=candidate, alpha_long=alpha_long):
          cp = params(candidate, alpha_long=alpha_long)
          self.assertTrue(cp.flags & HyundaiFlags.NON_SCC)
          self.assertFalse(cp.alphaLongitudinalAvailable)
          self.assertFalse(cp.openpilotLongitudinalControl)
          self.assertTrue(cp.pcmCruise)
          self.assertTrue(cp.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.NON_SCC)
          self.assertFalse(cp.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG)
          state = CarState(cp)
          parsers = state.get_can_parsers(cp)
          state.out = state.update(parsers)
          controller = CarController(DBC[cp.carFingerprint], cp)
          control = structs.CarControl()
          control.enabled = control.latActive = control.longActive = True
          _, sent = controller.update(control.as_reader(), state, 1_000_000_000)
          self.assertFalse({0x420, 0x421, 0x50A, 0x389, 0x38D, 0x483} & {addr for addr, _, _ in sent})

  def test_fuel_architectures_decode_actual_cruise_frames(self):
    families: tuple[tuple[str, dict[str, dict[str, float]]], ...] = (
      (CAR.KIA_FORTE_2021_NON_SCC, {"EMS16": {"CRUISE_LAMP_M": 1, "CRUISE_LAMP_S": 1},
                                     "LVR12": {"CF_Lvr_CruiseSet": 72}}),
      (CAR.HYUNDAI_ELANTRA_HEV_2022_NON_SCC,
       {"E_CRUISE_CONTROL": {"CRUISE_LAMP_M": 1, "CRUISE_LAMP_S": 1}, "ELECT_GEAR": {"SLC_SET_SPEED": 72}}),
      (CAR.HYUNDAI_KONA_EV_NON_SCC,
       {"LABEL11": {"CC_React": 1}, "EMS12": {"ACC_ACT": 1}, "E_EMS11": {"Cruise_Limit_Target": 72}}),
    )
    for candidate, messages in families:
      with self.subTest(candidate=candidate):
        cp = params(candidate)
        state = CarState(cp)
        parsers = state.get_can_parsers(cp)
        pt = parsers[Bus.pt]
        names = set(get_non_scc_cruise_signals(cp.flags)[::2])
        self.assertTrue(names <= set(pt.vl))
        self.assertNotIn("SCC12", names)
        packer = CANPacker(DBC[candidate][Bus.pt])
        frames = [packer.make_can_msg(name, 0, values) for name, values in messages.items()]
        self.assertEqual(pt.update((1_000_000_000, frames)), {frame[0] for frame in frames})
        out = state.update(parsers)
        self.assertTrue(out.cruiseState.available)
        self.assertTrue(out.cruiseState.enabled)
        self.assertAlmostEqual(out.cruiseState.speed, 20.0, places=4)
        self.assertFalse(out.accFaulted)
        self.assertFalse(out.cruiseState.standstill)
        self.assertFalse(out.cruiseState.nonAdaptive)

  def test_fca_source_and_lda_require_observed_configuration(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[1][0x602] = 8
    fingerprint[0][0x391] = 8
    kona = params(CAR.HYUNDAI_KONA_NON_SCC, fingerprint)
    self.assertTrue(kona.flags & HyundaiFlags.NON_SCC_RADAR_FCA)
    self.assertFalse(kona.radarUnavailable)
    self.assertTrue(kona.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.HAS_LDA_BUTTON)
    parsers = CarState(kona).get_can_parsers(kona)
    self.assertIn("FCA11", parsers[Bus.pt].vl)
    self.assertNotIn("FCA11", parsers[Bus.cam].vl)
    state = CarState(kona)
    state.update(parsers)
    self.assertIsNotNone(state.forte_lkas_sources)
    self.assertNotIn("BCM_PO_11", parsers[Bus.pt].vl)
    plain = params(CAR.HYUNDAI_KONA_NON_SCC)
    self.assertTrue(plain.radarUnavailable)
    self.assertFalse(plain.flags & HyundaiFlags.NON_SCC_RADAR_FCA)
    self.assertFalse(plain.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.HAS_LDA_BUTTON)
    camera = params(CAR.KIA_FORTE_2021_NON_SCC)
    self.assertIn("FCA11", CarState(camera).get_can_parsers(camera)[Bus.cam].vl)
    no_fca = params(CAR.KIA_FORTE_2019_NON_SCC)
    self.assertNotIn("FCA11", CarState(no_fca).get_can_parsers(no_fca)[Bus.cam].vl)

  def test_exact_firmware_and_unidentified_manual_kona_ev(self):
    self.assertNotIn(CAR.HYUNDAI_KONA_EV_NON_SCC, FW_VERSIONS)
    for candidate in NON_SCC_CARS:
      if candidate == CAR.HYUNDAI_KONA_EV_NON_SCC:
        continue
      with self.subTest(candidate=candidate):
        fw = [CarParams.CarFw(ecu=ecu, address=addr, subAddress=sub or 0, fwVersion=versions[0], brand="hyundai")
              for (ecu, addr, sub), versions in FW_VERSIONS[candidate].items()]
        exact, matches = match_fw_to_car(fw, "", allow_exact=True, allow_fuzzy=False, log=False)
        self.assertTrue(exact)
        self.assertEqual(matches, {candidate})

    # A shared partial ECU response cannot be promoted to either Kona sibling.
    key = (CarParams.Ecu.eps, 0x7d4, None)
    shared = set(FW_VERSIONS[CAR.HYUNDAI_KONA_NON_SCC][key]) & set(FW_VERSIONS[CAR.HYUNDAI_KONA][key])
    self.assertTrue(shared)
    partial = [CarParams.CarFw(ecu=key[0], address=key[1], subAddress=0, fwVersion=next(iter(shared)), brand="hyundai")]
    exact, matches = match_fw_to_car(partial, "", allow_exact=True, allow_fuzzy=False, log=False)
    self.assertTrue(exact)
    self.assertFalse(matches)
    # Unknown and contradictory firmware must not falsely identify the new variant.
    partial[0].fwVersion = b"unknown firmware"
    self.assertNotIn(CAR.HYUNDAI_KONA_NON_SCC,
                     match_fw_to_car(partial, "", allow_exact=True, allow_fuzzy=False, log=False)[1])

  def test_kona_receive_only_radar_tracks_and_freshness(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[1][0x602] = 8
    cp = params(CAR.HYUNDAI_KONA_NON_SCC, fingerprint)
    radar = RadarInterface(cp)
    parser = get_radar_can_parser(cp)
    self.assertIn("RADAR_TRACK_602", parser.vl)
    self.assertIn("RADAR_TRACK_611", parser.vl)
    self.assertNotIn("RADAR_TRACK_500", parser.vl)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.radar])
    first = packer.make_can_msg("RADAR_TRACK_602", 1, {"1_DISTANCE": 25, "1_LATERAL": 1.5, "1_SPEED": -2,
                                                        "2_DISTANCE": 255.75})
    trigger = packer.make_can_msg("RADAR_TRACK_611", 1, {"1_DISTANCE": 255.75, "2_DISTANCE": 255.75})
    out = radar.update((1_000_000_000, [first, trigger]))
    self.assertEqual(len(out.points), 1)
    self.assertAlmostEqual(out.points[0].dRel, 25)
    self.assertAlmostEqual(out.points[0].yRel, 1.5, delta=0.02)  # 0.03 m DBC resolution
    self.assertAlmostEqual(out.points[0].vRel, -2)
    # A fresh trigger without a fresh 0x602 must withdraw the old point.
    out = radar.update((1_050_000_000, [trigger]))
    self.assertEqual(len(out.points), 0)
    self.assertIsNone(radar.update((1_100_000_000, [first])))
    out = radar.update((1_200_000_000, [trigger]))
    self.assertEqual(len(out.points), 0)  # old source cannot revive at a delayed trigger
