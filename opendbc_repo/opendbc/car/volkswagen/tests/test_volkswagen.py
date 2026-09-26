import random
import re

import pytest

from opendbc.can.packer import CANPacker
from opendbc.car import Bus
from opendbc.car.structs import CarParams
from opendbc.car.volkswagen.interface import CarInterface
from opendbc.car.volkswagen.fingerprints import FW_VERSIONS
from opendbc.car.volkswagen.mqbcan import volkswagen_meb_alt_crc_checksum, volkswagen_mqb_meb_checksum
from opendbc.car.volkswagen.radar_interface import RadarInterface
from opendbc.car.volkswagen.values import CAR, DBC, FW_QUERY_CONFIG, WMI, CanBus, VolkswagenFlags, VolkswagenSafetyFlags

Ecu = CarParams.Ecu

CHASSIS_CODE_PATTERN = re.compile('[A-Z0-9]{2}')
# TODO: determine the unknown groups
SPARE_PART_FW_PATTERN = re.compile(b'\xf1\x87(?P<gateway>[0-9][0-9A-Z]{2})(?P<unknown>[0-9][0-9A-Z][0-9])(?P<unknown2>[0-9A-Z]{2}[0-9])([A-Z0-9]| )')


class TestVolkswagenPlatformConfigs:
  MEB_CARS = {car for car in CAR if car.config.flags & VolkswagenFlags.MEB}

  @staticmethod
  def _get_meb_params(car, gateway=True, alpha_long=False):
    fingerprint = {bus: {} for bus in range(8)}
    if gateway:
      fingerprint[1][0x13D] = 32
    return CarInterface.get_params(car, fingerprint, [], alpha_long, False, False, None)

  def test_meb_platform_params(self):
    for car in self.MEB_CARS:
      cp = self._get_meb_params(car)
      assert cp.flags & VolkswagenFlags.MEB
      assert cp.transmissionType == CarParams.TransmissionType.direct
      assert cp.steerControlType == CarParams.SteerControlType.curvatureDEPRECATED
      assert cp.steerAtStandstill
      assert cp.safetyConfigs[-1].safetyModel == CarParams.SafetyModel.volkswagenMeb
      assert not cp.dashcamOnly
      assert not cp.radarUnavailable

      has_gen2_crc = bool(cp.safetyConfigs[-1].safetyParam & VolkswagenSafetyFlags.MEB_ALT_CRC)
      assert has_gen2_crc == bool(car.config.flags & VolkswagenFlags.MEB_GEN2)

  def test_meb_camera_harness_is_passive(self):
    cp = self._get_meb_params(CAR.VOLKSWAGEN_ID4_MK1, gateway=False, alpha_long=True)
    assert cp.dashcamOnly
    assert cp.radarUnavailable
    assert not cp.alphaLongitudinalAvailable
    assert not cp.openpilotLongitudinalControl
    assert not (cp.safetyConfigs[-1].safetyParam & VolkswagenSafetyFlags.LONG_CONTROL)

  def test_meb_docs_assume_required_gateway_harness(self):
    fingerprint = {bus: {} for bus in range(8)}
    cp = CarInterface.get_params(CAR.VOLKSWAGEN_ID4_MK1, fingerprint, [], True, False, True, None)

    assert cp.networkLocation == CarParams.NetworkLocation.gateway
    assert not cp.dashcamOnly
    assert cp.alphaLongitudinalAvailable

  def test_meb_gateway_longitudinal(self):
    cp = self._get_meb_params(CAR.VOLKSWAGEN_ID4_MK1, gateway=True, alpha_long=True)
    assert cp.alphaLongitudinalAvailable
    assert cp.openpilotLongitudinalControl
    assert not cp.pcmCruise
    assert cp.safetyConfigs[-1].safetyParam & VolkswagenSafetyFlags.LONG_CONTROL

  @pytest.mark.parametrize("data_hex", (
    "fc03fcfcfc0f0000",
    "e304fcfcfc0f0000",
    "1105fcfcfc0f0000",
  ))
  def test_meb_klr_checksum(self, data_hex):
    data = bytearray.fromhex(data_hex)
    assert volkswagen_mqb_meb_checksum(0x25D, None, data) == data[0]

  @pytest.mark.parametrize(("address", "data_hex"), (
    (0x0DB, "bb0ffcf0fefe0000fd0fffc0ff0000000200000000000000010000000000000000000000000000000000000000000000"),
    (0x0FC, "650b1f007ef0b10c0000000000000000ffff1019191c1cfefe0000000000000000e0fff40140ffeb7f0748e481af421f00000000000000000000000000000000"),
    (0x102, "9f0e7cfa010500000020cb0402000000b703a00000ec0f00000000002cd3ff1f0020a60000000020000000007d5256ab"),
    (0x10B, "9d06000000007efe000000010000ff01feff000000000000000000000090240000000000000000000000000000000000"),
    (0x139, "ac0e850b0890132000d019800000000000000000000000003002000500000000"),
    (0x13D, "2412111101d1060000d0d410d106000000000000000000000000000000000000"),
  ))
  def test_meb_gen2_checksum(self, address, data_hex):
    data = bytearray.fromhex(data_hex)
    assert volkswagen_meb_alt_crc_checksum(address, None, data) == data[0]

  def test_meb_camera_radar_tracks(self):
    cp = self._get_meb_params(CAR.SKODA_ENYAQ_MK1)
    radar = RadarInterface(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.radar])
    message = packer.make_can_msg("MEB_Distance_01", CanBus(cp).cam, {
      "Distance_Status": 0,
      "Same_Lane_01_ObjectID": 1,
      "Same_Lane_01_Long_Distance": 25.0,
      "Same_Lane_01_Lat_Distance": 0.5,
      "Same_Lane_01_Rel_Velo": -2.0,
    })

    radar_data = radar.update([(1_000_000_000, [message])])
    assert radar_data is not None
    assert len(radar_data.points) == 1
    assert radar_data.points[0].trackId == 0
    assert radar_data.points[0].dRel == pytest.approx(25.0, abs=0.1)
    assert radar_data.points[0].yRel == pytest.approx(0.5, abs=0.1)
    assert radar_data.points[0].vRel == pytest.approx(-2.0, abs=0.1)

  def test_taos_longitudinal_actuator_delay(self):
    taos_cp = CarInterface.get_non_essential_params(CAR.VOLKSWAGEN_TAOS_MK1)
    golf_cp = CarInterface.get_non_essential_params(CAR.VOLKSWAGEN_GOLF_MK7)

    assert abs(taos_cp.longitudinalActuatorDelay - 0.25) < 1e-6
    assert abs(golf_cp.longitudinalActuatorDelay - 0.15) < 1e-6

  def test_spare_part_fw_pattern(self, subtests):
    # Relied on for determining if a FW is likely VW
    for platform, ecus in FW_VERSIONS.items():
      with subtests.test(platform=platform.value):
        for fws in ecus.values():
          for fw in fws:
            assert SPARE_PART_FW_PATTERN.match(fw) is not None, f"Bad FW: {fw}"

  def test_chassis_codes(self, subtests):
    for platform in CAR:
      with subtests.test(platform=platform.value):
        assert len(platform.config.wmis) > 0, "WMIs not set"
        assert len(platform.config.chassis_codes) > 0, "Chassis codes not set"
        assert all(CHASSIS_CODE_PATTERN.match(cc) for cc in
                   platform.config.chassis_codes), "Bad chassis codes"

        # Shared MEB chassis codes are valid only when VIN model-year sets are disjoint.
        for comp in CAR:
          if platform == comp:
            continue
          shared_chassis = platform.config.chassis_codes & comp.config.chassis_codes
          if shared_chassis:
            both_meb = platform.config.flags & VolkswagenFlags.MEB and comp.config.flags & VolkswagenFlags.MEB
            disjoint_years = (getattr(platform.config, "model_years", set()) and getattr(comp.config, "model_years", set()) and
                              not platform.config.model_years & comp.config.model_years)
            assert both_meb and disjoint_years, f"Shared chassis codes: {comp}"

  @pytest.mark.parametrize(("wmi", "chassis", "year", "expected"), (
    ("1V2", "E8", "M", CAR.VOLKSWAGEN_ID4_MK1),
    ("1V2", "E8", "N", CAR.VOLKSWAGEN_ID4_MK1),
    ("1V2", "E8", "P", CAR.VOLKSWAGEN_ID4_MK1),
    ("WVW", "E8", "P", CAR.VOLKSWAGEN_ID4_MK1),
    ("WVG", "E8", "P", CAR.VOLKSWAGEN_ID4_MK1),
    ("WVW", "E2", "M", CAR.VOLKSWAGEN_ID4_MK1),
    ("WVW", "E2", "N", CAR.VOLKSWAGEN_ID4_MK1),
    ("WVG", "E2", "P", CAR.VOLKSWAGEN_ID4_MK1),
    ("1V2", "E8", "R", CAR.VOLKSWAGEN_ID4_MK2),
    ("1V2", "E8", "S", CAR.VOLKSWAGEN_ID4_MK2),
    ("1V2", "E8", "L", None),
    ("1V2", "E8", "T", None),
    ("1V2", "E8", "0", None),
    ("WVW", "E2", "R", None),
    ("WVW", "E2", "S", None),
    ("TMB", "E8", "P", None),
  ))
  def test_id4_fuzzy_fingerprinting_model_year(self, wmi, chassis, year, expected):
    # Synthetic VINs keep the regression independent of the platform configuration.
    vin = f"{wmi}000{chassis}0{year}0000000"
    live_fws = {(0x757, None): [b'\xf1\x871EA907572H \xf1\x890234']}
    matches = FW_QUERY_CONFIG.match_fw_to_car_fuzzy(live_fws, vin, FW_VERSIONS)
    assert matches == ({expected} if expected is not None else set())

  @pytest.mark.parametrize("live_fws", ({}, {(0x757, None): [b"unknown radar firmware"]}))
  def test_id4_fuzzy_fingerprinting_requires_known_radar(self, live_fws):
    assert FW_QUERY_CONFIG.match_fw_to_car_fuzzy(live_fws, "1V2000E80P0000000", FW_VERSIONS) == set()

  def test_custom_fuzzy_fingerprinting(self, subtests):
    all_radar_fw = list({fw for ecus in FW_VERSIONS.values() for fw in ecus[Ecu.fwdRadar, 0x757, None]})

    for platform in CAR:
      with subtests.test(platform=platform.name):
        model_years = getattr(platform.config, "model_years", set()) or {"0"}
        for wmi in WMI:
          for chassis_code in platform.config.chassis_codes | {"00"}:
            for model_year in model_years:
              vin = ["0"] * 17
              vin[0:3] = wmi
              vin[6:8] = chassis_code
              vin[9] = model_year
              vin = "".join(vin)

              # Check a few FW cases - expected, unexpected
              for radar_fw in random.sample(all_radar_fw, 5) + [b'\xf1\x875Q0907572G \xf1\x890571', b'\xf1\x877H9907572AA\xf1\x890396']:
                should_match = ((wmi in platform.config.wmis and chassis_code in platform.config.chassis_codes) and
                                radar_fw in all_radar_fw)

                live_fws = {(0x757, None): [radar_fw]}
                matches = FW_QUERY_CONFIG.match_fw_to_car_fuzzy(live_fws, vin, FW_VERSIONS)

                expected_matches = {platform} if should_match else set()
                assert expected_matches == matches, "Bad match"
