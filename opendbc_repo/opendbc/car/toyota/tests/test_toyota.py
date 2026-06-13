from types import SimpleNamespace

from hypothesis import given, settings, strategies as st

from opendbc.car import Bus
from opendbc.can import CANPacker, CANParser
from opendbc.car.structs import CarParams
from opendbc.car.fw_versions import build_fw_dict
from opendbc.car.toyota import toyotacan
from opendbc.car.toyota.carcontroller import CarController, limit_interceptor_pcm_accel, limit_interceptor_stopping_accel, \
                                             limit_prius_stopping_accel, update_permit_braking
from opendbc.car.toyota.carstate import calculate_interceptor_gas_pressed
from opendbc.car.toyota.fingerprints import FW_VERSIONS
from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR, DBC, TSS2_CAR, ANGLE_CONTROL_CAR, RADAR_ACC_CAR, SECOC_CAR, \
                                                  FW_QUERY_CONFIG, PLATFORM_CODE_ECUS, FUZZY_EXCLUDED_PLATFORMS, \
                                                  get_platform_codes

Ecu = CarParams.Ecu


def check_fw_version(fw_version: bytes) -> bool:
  # TODO: just use the FW patterns, need to support all chunks
  return b'?' not in fw_version and b'!' not in fw_version


class TestToyotaInterfaces:
  def test_car_sets(self):
    assert len(ANGLE_CONTROL_CAR - TSS2_CAR) == 0
    assert len(RADAR_ACC_CAR - TSS2_CAR) == 0

  def test_lta_platforms(self):
    # At this time, only RAV4 2023 is expected to use LTA/angle control
    assert ANGLE_CONTROL_CAR == {CAR.TOYOTA_RAV4_TSS2_2023}

  def test_tss2_dbc(self):
    # We make some assumptions about TSS2 platforms,
    # like looking up certain signals only in this DBC
    for car_model, dbc in DBC.items():
      if car_model in TSS2_CAR and car_model not in SECOC_CAR:
        assert dbc[Bus.pt] == "toyota_nodsu_pt_generated"

  def test_essential_ecus(self, subtests):
    # Asserts standard ECUs exist for each platform
    common_ecus = {Ecu.fwdRadar, Ecu.fwdCamera}
    for car_model, ecus in FW_VERSIONS.items():
      with subtests.test(car_model=car_model.value):
        present_ecus = {ecu[0] for ecu in ecus}
        missing_ecus = common_ecus - present_ecus
        assert len(missing_ecus) == 0

        # Some exceptions for other common ECUs
        if car_model not in (CAR.TOYOTA_ALPHARD_TSS2,):
          assert Ecu.abs in present_ecus

        if car_model not in (CAR.TOYOTA_MIRAI,):
          assert Ecu.engine in present_ecus

        if car_model not in (CAR.TOYOTA_PRIUS_V, CAR.LEXUS_CTH):
          assert Ecu.eps in present_ecus


class TestToyotaFingerprint:
  def test_non_essential_ecus(self, subtests):
    # Ensures only the cars that have multiple engine ECUs are in the engine non-essential ECU list
    for car_model, ecus in FW_VERSIONS.items():
      with subtests.test(car_model=car_model.value):
        engine_ecus = {ecu for ecu in ecus if ecu[0] == Ecu.engine}
        assert (len(engine_ecus) > 1) == (car_model in FW_QUERY_CONFIG.non_essential_ecus[Ecu.engine]), \
          f"Car model unexpectedly {'not ' if len(engine_ecus) > 1 else ''}in non-essential list"

  def test_valid_fw_versions(self, subtests):
    # Asserts all FW versions are valid
    for car_model, ecus in FW_VERSIONS.items():
      with subtests.test(car_model=car_model.value):
        for fws in ecus.values():
          for fw in fws:
            assert check_fw_version(fw), fw

  # Tests for part numbers, platform codes, and sub-versions which Toyota will use to fuzzy
  # fingerprint in the absence of full FW matches:
  @settings(max_examples=100)
  @given(data=st.data())
  def test_platform_codes_fuzzy_fw(self, data):
    fw_strategy = st.lists(st.binary())
    fws = data.draw(fw_strategy)
    get_platform_codes(fws)

  def test_platform_code_ecus_available(self, subtests):
    # Asserts ECU keys essential for fuzzy fingerprinting are available on all platforms
    for car_model, ecus in FW_VERSIONS.items():
      with subtests.test(car_model=car_model.value):
        for platform_code_ecu in PLATFORM_CODE_ECUS:
          if platform_code_ecu == Ecu.eps and car_model in (CAR.TOYOTA_PRIUS_V, CAR.LEXUS_CTH,):
            continue
          if platform_code_ecu == Ecu.abs and car_model in (CAR.TOYOTA_ALPHARD_TSS2,):
            continue
          assert platform_code_ecu in [e[0] for e in ecus]

  def test_fw_format(self, subtests):
    # Asserts:
    # - every supported ECU FW version returns one platform code
    # - every supported ECU FW version has a part number
    # - expected parsing of ECU sub-versions

    for car_model, ecus in FW_VERSIONS.items():
      with subtests.test(car_model=car_model.value):
        for ecu, fws in ecus.items():
          if ecu[0] not in PLATFORM_CODE_ECUS:
            continue

          codes = dict()
          for fw in fws:
            result = get_platform_codes([fw])
            # Check only one platform code and sub-version
            assert 1 == len(result), f"Unable to parse FW: {fw}"
            assert 1 == len(list(result.values())[0]), f"Unable to parse FW: {fw}"
            codes |= result

          # Toyota places the ECU part number in their FW versions, assert all parsable
          # Note that there is only one unique part number per ECU across the fleet, so this
          # is not important for identification, just a sanity check.
          assert all(code.count(b"-") > 1 for code in codes), f"FW does not have part number: {fw} {codes}"

  def test_platform_codes_spot_check(self):
    # Asserts basic platform code parsing behavior for a few cases
    results = get_platform_codes([
      b"F152607140\x00\x00\x00\x00\x00\x00",
      b"F152607171\x00\x00\x00\x00\x00\x00",
      b"F152607110\x00\x00\x00\x00\x00\x00",
      b"F152607180\x00\x00\x00\x00\x00\x00",
    ])
    assert results == {b"F1526-07-1": {b"10", b"40", b"71", b"80"}}

    results = get_platform_codes([
      b"\x028646F4104100\x00\x00\x00\x008646G5301200\x00\x00\x00\x00",
      b"\x028646F4104100\x00\x00\x00\x008646G3304000\x00\x00\x00\x00",
    ])
    assert results == {b"8646F-41-04": {b"100"}}

    # Short version has no part number
    results = get_platform_codes([
      b"\x0235870000\x00\x00\x00\x00\x00\x00\x00\x00A0202000\x00\x00\x00\x00\x00\x00\x00\x00",
      b"\x0235883000\x00\x00\x00\x00\x00\x00\x00\x00A0202000\x00\x00\x00\x00\x00\x00\x00\x00",
    ])
    assert results == {b"58-70": {b"000"}, b"58-83": {b"000"}}

    results = get_platform_codes([
      b"F152607110\x00\x00\x00\x00\x00\x00",
      b"F152607140\x00\x00\x00\x00\x00\x00",
      b"\x028646F4104100\x00\x00\x00\x008646G5301200\x00\x00\x00\x00",
      b"\x0235879000\x00\x00\x00\x00\x00\x00\x00\x00A4701000\x00\x00\x00\x00\x00\x00\x00\x00",
    ])
    assert results == {b"F1526-07-1": {b"10", b"40"}, b"8646F-41-04": {b"100"}, b"58-79": {b"000"}}

  def test_fuzzy_excluded_platforms(self):
    # Asserts a list of platforms that will not fuzzy fingerprint with platform codes due to them being shared.
    platforms_with_shared_codes = set()
    for platform, fw_by_addr in FW_VERSIONS.items():
      car_fw = []
      for ecu, fw_versions in fw_by_addr.items():
        ecu_name, addr, sub_addr = ecu
        for fw in fw_versions:
          car_fw.append(CarParams.CarFw(ecu=ecu_name, fwVersion=fw, address=addr,
                                        subAddress=0 if sub_addr is None else sub_addr))

      CP = CarParams(carFw=car_fw)
      matches = FW_QUERY_CONFIG.match_fw_to_car_fuzzy(build_fw_dict(CP.carFw), CP.carVin, FW_VERSIONS)
      if len(matches) == 1:
        assert list(matches)[0] == platform
      else:
        # If a platform has multiple matches, add it and its matches
        platforms_with_shared_codes |= {str(platform), *matches}

    assert platforms_with_shared_codes == FUZZY_EXCLUDED_PLATFORMS, (len(platforms_with_shared_codes), len(FW_VERSIONS))


class TestToyotaCarController:
  @staticmethod
  def _make_controller(*, standstill_req=False, last_standstill=False):
    controller = CarController.__new__(CarController)
    controller.CP = SimpleNamespace(
      carFingerprint=CAR.TOYOTA_PRIUS,
      enableGasInterceptorDEPRECATED=False,
      openpilotLongitudinalControl=True,
      minEnableSpeed=-1.0,
    )
    controller.standstill_req = standstill_req
    controller.last_standstill = last_standstill
    controller.accel = 0.0
    return controller

  @staticmethod
  def _make_cc(*, resume=False):
    return SimpleNamespace(cruiseControl=SimpleNamespace(resume=resume))

  @staticmethod
  def _make_cs(*, standstill=True, cruise_standstill=True, pcm_acc_status=8):
    return SimpleNamespace(
      out=SimpleNamespace(
        standstill=standstill,
        cruiseState=SimpleNamespace(standstill=cruise_standstill),
      ),
      pcm_acc_status=pcm_acc_status,
    )

  @staticmethod
  def _make_toggles(*, sng_hack=False):
    return SimpleNamespace(sng_hack=sng_hack)

  def test_prius_standstill_request_latches_on_entry(self):
    controller = self._make_controller()

    controller._update_standstill_request(
      self._make_cc(),
      self._make_cs(),
      SimpleNamespace(accel=0.0),
      self._make_toggles(),
    )

    assert controller.standstill_req is True

  def test_prius_resume_request_releases_standstill_latch(self):
    controller = self._make_controller(standstill_req=True, last_standstill=True)

    controller._update_standstill_request(
      self._make_cc(resume=True),
      self._make_cs(),
      SimpleNamespace(accel=0.0),
      self._make_toggles(),
    )

    assert controller.standstill_req is False

  def test_permit_braking_high_speed_coasts_for_tiny_decel(self):
    assert update_permit_braking(True, -0.05, False, True, 25.0, True) is False
    assert update_permit_braking(False, -0.05, False, True, 25.0, True) is False

  def test_permit_braking_high_speed_brakes_for_meaningful_decel_with_lead(self):
    assert update_permit_braking(False, -0.15, False, True, 25.0, True) is True

  def test_permit_braking_high_speed_no_lead_coasts_for_mild_decel(self):
    assert update_permit_braking(True, -0.25, False, True, 25.0, False) is False
    assert update_permit_braking(False, -0.25, False, True, 25.0, False) is False

  def test_permit_braking_high_speed_no_lead_brakes_for_stronger_decel(self):
    assert update_permit_braking(False, -0.35, False, True, 25.0, False) is True

  def test_permit_braking_low_speed_keeps_legacy_behavior(self):
    assert update_permit_braking(False, -0.05, False, True, 10.0, False) is True

  def test_permit_braking_forces_on_when_stopping_or_inactive(self):
    assert update_permit_braking(False, 0.10, True, True, 25.0, False) is True
    assert update_permit_braking(False, 0.10, False, False, 25.0, False) is True

  def test_prius_stopping_accel_unwinds_stale_stop_hold(self):
    limited = limit_prius_stopping_accel(-3.28, -0.05, True, 0.0, True)
    assert -1.5 < limited < 0.0

  def test_prius_stopping_accel_keeps_hard_stop_commands(self):
    limited = limit_prius_stopping_accel(-3.28, -2.0, True, 0.0, True)
    assert limited == -3.28

  def test_sng_hack_clears_existing_standstill_latch(self):
    controller = self._make_controller(standstill_req=True, last_standstill=True)

    controller._update_standstill_request(
      self._make_cc(),
      self._make_cs(),
      SimpleNamespace(accel=0.0),
      self._make_toggles(sng_hack=True),
    )

    assert controller.standstill_req is False

  def test_ui_command_shows_aol_bars_when_lateral_active(self):
    packer = CANPacker(DBC[CAR.TOYOTA_HIGHLANDER_TSS2][Bus.pt])
    parser = CANParser(DBC[CAR.TOYOTA_HIGHLANDER_TSS2][Bus.pt], [("LKAS_HUD", 0)], 0)

    msg = toyotacan.create_ui_command(packer, False, False, True, True, False, False, {}, True)
    parser.update([(1, [msg])])

    assert parser.can_valid
    assert parser.vl["LKAS_HUD"]["BARRIERS"] == 1
    assert parser.vl["LKAS_HUD"]["LEFT_LINE"] == 1
    assert parser.vl["LKAS_HUD"]["RIGHT_LINE"] == 1

  def test_ui_command_hides_lane_markers_when_lateral_inactive(self):
    packer = CANPacker(DBC[CAR.TOYOTA_HIGHLANDER_TSS2][Bus.pt])
    parser = CANParser(DBC[CAR.TOYOTA_HIGHLANDER_TSS2][Bus.pt], [("LKAS_HUD", 0)], 0)

    msg = toyotacan.create_ui_command(packer, False, False, True, True, False, False, {}, False)
    parser.update([(1, [msg])])

    assert parser.can_valid
    assert parser.vl["LKAS_HUD"]["BARRIERS"] == 0
    assert parser.vl["LKAS_HUD"]["LEFT_LINE"] == 0
    assert parser.vl["LKAS_HUD"]["RIGHT_LINE"] == 0

  def test_interceptor_stop_and_go_holds_small_launch_at_standstill(self):
    controller = self._make_controller()
    controller.CP.enableGasInterceptorDEPRECATED = True
    controller.accel = 0.3

    gas_cmd = controller._compute_interceptor_gas_cmd(
      SimpleNamespace(longActive=True),
      SimpleNamespace(out=SimpleNamespace(standstill=True, vEgo=0.0)),
    )

    assert gas_cmd == 0.12

  def test_interceptor_non_stop_and_go_scales_with_accel_request(self):
    controller = self._make_controller()
    controller.CP.enableGasInterceptorDEPRECATED = True
    controller.CP.carFingerprint = CAR.TOYOTA_AVALON_2019
    controller.CP.minEnableSpeed = 8.5
    controller.accel = 0.8

    gas_cmd = controller._compute_interceptor_gas_cmd(
      SimpleNamespace(longActive=True),
      SimpleNamespace(out=SimpleNamespace(standstill=False, vEgo=8.0)),
    )

    assert 0.0 < gas_cmd <= 0.5

  def test_interceptor_disabled_returns_zero(self):
    controller = self._make_controller()
    controller.accel = 1.0

    gas_cmd = controller._compute_interceptor_gas_cmd(
      SimpleNamespace(longActive=True),
      SimpleNamespace(out=SimpleNamespace(standstill=False, vEgo=8.0)),
    )

    assert gas_cmd == 0.0

  def test_interceptor_comfort_limit_keeps_positive_target_out_of_coast(self):
    limited = limit_interceptor_pcm_accel(-0.30, 0.70, False, 8.5)

    assert limited > 0.0
    assert limited < 0.70

  def test_interceptor_comfort_limit_keeps_mild_brake_request_negative(self):
    limited = limit_interceptor_pcm_accel(0.25, -0.35, False, 8.5)

    assert limited < 0.0
    assert limited > -0.35

  def test_interceptor_comfort_limit_bypasses_harder_braking(self):
    original = -1.80
    limited = limit_interceptor_pcm_accel(original, -1.80, False, 8.5)

    assert limited == original

  def test_interceptor_comfort_limit_prevents_positive_target_from_crossing_negative(self):
    limited = limit_interceptor_pcm_accel(-2.0, 1.7, False, 7.5)

    assert limited >= 0.0

  def test_interceptor_comfort_limit_prevents_negative_target_from_crossing_positive(self):
    limited = limit_interceptor_pcm_accel(0.8, -0.7, False, 7.5)

    assert limited <= 0.0

  def test_interceptor_stopping_limit_softens_no_lead_final_crawl(self):
    limited = limit_interceptor_stopping_accel(-1.48, -1.48, True, 0.5, False)

    assert limited > -1.48
    assert limited == -0.82

  def test_interceptor_stopping_limit_tracks_softer_target_near_standstill(self):
    limited = limit_interceptor_stopping_accel(-1.86, -0.63, True, 0.5, False)

    assert limited > -1.0
    assert limited == -0.73

  def test_interceptor_stopping_limit_keeps_visible_lead_stop_untouched(self):
    limited = limit_interceptor_stopping_accel(-1.48, -0.63, True, 0.5, True)

    assert limited == -1.48

  def test_interceptor_stopping_limit_keeps_higher_speed_stop_untouched(self):
    limited = limit_interceptor_stopping_accel(-1.48, -0.63, True, 3.0, False)

    assert limited == -1.48

  def test_interceptor_stopping_limit_softens_low_speed_no_lead_stop_before_final_crawl(self):
    limited = limit_interceptor_stopping_accel(-1.55, -0.66, True, 1.45, False)

    assert abs(limited - (-0.8075)) < 1e-6

  def test_avalon_pedal_params_raise_delay_and_soften_stop(self):
    CP = CarInterface.get_params(
      CAR.TOYOTA_AVALON_2019,
      {0: {0x2FF: 8, 0x201: 8}},
      [],
      True,
      False,
      False,
      None,
    )

    assert CP.enableGasInterceptorDEPRECATED
    assert abs(CP.longitudinalActuatorDelay - 0.2) < 1e-6
    assert CP.stopAccel == -1.5


class TestToyotaCarState:
  def test_interceptor_gas_pressed_threshold(self):
    cp = SimpleNamespace(vl={
      "GAS_SENSOR": {
        "INTERCEPTOR_GAS": 900,
        "INTERCEPTOR_GAS2": 910,
      }
    })
    assert calculate_interceptor_gas_pressed(cp) is True

    cp = SimpleNamespace(vl={
      "GAS_SENSOR": {
        "INTERCEPTOR_GAS": 700,
        "INTERCEPTOR_GAS2": 710,
      }
    })
    assert calculate_interceptor_gas_pressed(cp) is False
