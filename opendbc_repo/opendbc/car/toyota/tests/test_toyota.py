from types import SimpleNamespace

import pytest
from hypothesis import given, settings, strategies as st

from opendbc.car import Bus, structs
from opendbc.can import CANPacker, CANParser
from opendbc.car.structs import CarParams
from opendbc.car.fw_versions import build_fw_dict, match_fw_to_car
from opendbc.car.toyota import toyotacan
from opendbc.car.toyota.carcontroller import CarController, get_camry_hybrid_feedforward, get_long_tune, get_prius_feedforward, \
                                             get_prius_positive_feedforward_scale, \
                                             limit_interceptor_pcm_accel, \
                                             limit_interceptor_stopping_accel, limit_no_lead_cruise_sign_flip, \
                                             limit_prius_stopping_accel, update_permit_braking
from opendbc.car.toyota.carstate import CarState, LKAS_BUTTON_CAR, calculate_interceptor_gas_pressed, create_lkas_button_events
from opendbc.car.toyota.fingerprints import FW_VERSIONS
from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.radar_interface import RadarInterface, TSSP_RADAR_EGO_SPEED_SCALE
from opendbc.car.toyota.values import CAR, DBC, TSS2_CAR, ANGLE_CONTROL_CAR, RADAR_ACC_CAR, SECOC_CAR, \
                                                  FW_QUERY_CONFIG, PLATFORM_CODE_ECUS, FUZZY_EXCLUDED_PLATFORMS, \
                                                  ToyotaFlags, ToyotaSafetyFlags, get_platform_codes
from opendbc.safety import ALTERNATIVE_EXPERIENCE
from openpilot.common.params import Params

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

  def test_rav4_prime_force_torque_controller(self):
    fingerprint = {bus: {} for bus in range(8)}

    default_params = CarInterface.get_params(
      CAR.TOYOTA_RAV4_PRIME, fingerprint, [], False, False, False,
      SimpleNamespace(force_torque_controller=False, nnff=False, nnff_lite=False),
    )
    forced_params = CarInterface.get_params(
      CAR.TOYOTA_RAV4_PRIME, fingerprint, [], False, False, False,
      SimpleNamespace(force_torque_controller=True, nnff=False, nnff_lite=False),
    )

    assert default_params.lateralTuning.which() == "pid"
    assert forced_params.lateralTuning.which() == "torque"
    assert forced_params.lateralTuning.torque.latAccelFactor == pytest.approx(1.7)
    assert forced_params.lateralTuning.torque.friction == pytest.approx(0.14)

  def test_sienna_4th_gen_uses_torque_controller(self):
    params = CarInterface.get_params(
      CAR.TOYOTA_SIENNA_4TH_GEN,
      {bus: {} for bus in range(8)},
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=SimpleNamespace(force_torque_controller=False, nnff=False, nnff_lite=False),
    )

    assert params.lateralTuning.which() == "torque"
    assert params.lateralTuning.torque.latAccelFactor == pytest.approx(1.7)
    assert params.lateralTuning.torque.friction == pytest.approx(0.14)

  def test_tss2_dbc(self):
    # We make some assumptions about TSS2 platforms,
    # like looking up certain signals only in this DBC
    for car_model, dbc in DBC.items():
      if car_model in TSS2_CAR and car_model not in SECOC_CAR:
        assert dbc[Bus.pt] == "toyota_nodsu_pt_generated"

  def test_auto_hold_sets_flag_on_supported_tss2(self):
    params = Params()
    try:
      params.put_bool("ToyotaAutoHold", True)
      car_params = CarInterface.get_params(
        CAR.TOYOTA_CAMRY_TSS2,
        {bus: {} for bus in range(8)},
        [],
        alpha_long=False,
        is_release=False,
        docs=False,
        starpilot_toggles=SimpleNamespace(),
      )
    finally:
      params.remove("ToyotaAutoHold")

    assert car_params.flags & ToyotaFlags.AUTO_BRAKE_HOLD.value
    assert car_params.alternativeExperience & ALTERNATIVE_EXPERIENCE.ALLOW_AEB

  def test_prius_openpilot_long_uses_hybrid_long_defaults(self):
    car_params = CarInterface.get_params(
      CAR.TOYOTA_PRIUS,
      {0: {0x2FF: 8}},
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=SimpleNamespace(),
    )

    assert car_params.openpilotLongitudinalControl
    assert car_params.flags & ToyotaFlags.HYBRID.value
    assert car_params.flags & ToyotaFlags.RAISED_ACCEL_LIMIT.value
    assert abs(car_params.longitudinalActuatorDelay - 0.05) < 1e-6
    assert abs(car_params.vEgoStopping - 0.25) < 1e-6
    assert abs(car_params.vEgoStarting - 0.25) < 1e-6

  def test_highlander_ice_openpilot_long_uses_measured_actuator_delay(self):
    stock_params = CarInterface.get_params(
      CAR.TOYOTA_HIGHLANDER,
      {bus: {} for bus in range(8)},
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=SimpleNamespace(),
    )
    long_params = CarInterface.get_params(
      CAR.TOYOTA_HIGHLANDER,
      {bus: ({0x2FF: 8} if bus == 0 else {}) for bus in range(8)},
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=SimpleNamespace(),
    )

    assert not stock_params.openpilotLongitudinalControl
    assert stock_params.longitudinalActuatorDelay == pytest.approx(0.15)
    assert long_params.openpilotLongitudinalControl
    assert not long_params.flags & ToyotaFlags.HYBRID.value
    assert long_params.longitudinalActuatorDelay == pytest.approx(0.4)

  def test_sienna_openpilot_long_uses_measured_actuator_delay(self):
    stock_params = CarInterface.get_params(
      CAR.TOYOTA_SIENNA,
      {bus: {} for bus in range(8)},
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=SimpleNamespace(),
    )
    long_params = CarInterface.get_params(
      CAR.TOYOTA_SIENNA,
      {bus: ({0x2FF: 8} if bus == 0 else {}) for bus in range(8)},
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=SimpleNamespace(),
    )

    assert not stock_params.openpilotLongitudinalControl
    assert stock_params.longitudinalActuatorDelay == pytest.approx(0.15)
    assert long_params.openpilotLongitudinalControl
    assert not long_params.flags & ToyotaFlags.HYBRID.value
    assert long_params.longitudinalActuatorDelay == pytest.approx(0.5)

  @pytest.mark.parametrize("camera_message", [0x343, 0x4CB])
  def test_dsu_bypass_enables_longitudinal(self, camera_message):
    fingerprint = {bus: {} for bus in range(8)}
    fingerprint[2][camera_message] = 8

    car_params = CarInterface.get_params(
      CAR.TOYOTA_COROLLA,
      fingerprint,
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=SimpleNamespace(),
    )

    assert car_params.flags & ToyotaFlags.DSU_BYPASS.value
    assert car_params.openpilotLongitudinalControl
    assert not car_params.safetyConfigs[0].safetyParam & ToyotaSafetyFlags.STOCK_LONGITUDINAL.value

    starpilot_params = CarInterface.get_starpilot_params(
      CAR.TOYOTA_COROLLA, fingerprint, [], car_params, SimpleNamespace(),
    )
    car_state = CarState(car_params, starpilot_params)
    can_parsers = car_state.get_can_parsers(car_params)
    car_state.update(can_parsers, SimpleNamespace(cluster_offset=1.0))

    for message in ("ACC_CONTROL", "PRE_COLLISION", "PCS_HUD"):
      assert message not in can_parsers[Bus.pt].vl
      assert message in can_parsers[Bus.cam].vl

  @pytest.mark.parametrize(("native_bus", "message"), [(1, 0x343), (0, 0x4CB)])
  def test_dsu_bypass_ignores_startup_bus_mirror(self, native_bus, message):
    fingerprint = {bus: {} for bus in range(8)}
    fingerprint[native_bus][message] = 8
    fingerprint[2][message] = 8

    car_params = CarInterface.get_params(
      CAR.LEXUS_IS,
      fingerprint,
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=SimpleNamespace(),
    )

    assert not car_params.flags & ToyotaFlags.DSU_BYPASS.value
    assert not car_params.openpilotLongitudinalControl
    assert car_params.safetyConfigs[0].safetyParam & ToyotaSafetyFlags.STOCK_LONGITUDINAL.value
    assert car_params.safetyConfigs[0].safetyParam & ToyotaSafetyFlags.ALT_CRUISE.value

  @pytest.mark.parametrize(("native_bus", "message"), [(1, 0x343), (0, 0x4CB)])
  def test_prius_dsu_bypass_allows_native_bus_message(self, native_bus, message):
    fingerprint = {bus: {} for bus in range(8)}
    fingerprint[native_bus][message] = 8
    fingerprint[2][message] = 8

    car_params = CarInterface.get_params(
      CAR.TOYOTA_PRIUS,
      fingerprint,
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=SimpleNamespace(),
    )

    assert car_params.flags & ToyotaFlags.DSU_BYPASS.value
    assert car_params.openpilotLongitudinalControl
    assert not car_params.safetyConfigs[0].safetyParam & ToyotaSafetyFlags.STOCK_LONGITUDINAL.value
    assert not car_params.safetyConfigs[0].safetyParam & ToyotaSafetyFlags.ALT_CRUISE.value

  def test_dsu_bypass_does_not_change_tss2_or_smart_dsu(self):
    fingerprint = {bus: {} for bus in range(8)}
    fingerprint[0][0x2FF] = 8
    fingerprint[2][0x343] = 8

    smart_dsu_params = CarInterface.get_params(
      CAR.TOYOTA_COROLLA,
      fingerprint,
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=SimpleNamespace(),
    )
    tss2_params = CarInterface.get_params(
      CAR.TOYOTA_CAMRY_TSS2,
      fingerprint,
      [],
      alpha_long=False,
      is_release=False,
      docs=False,
      starpilot_toggles=SimpleNamespace(),
    )

    assert not smart_dsu_params.flags & ToyotaFlags.DSU_BYPASS.value
    assert not tss2_params.flags & ToyotaFlags.DSU_BYPASS.value

  def test_camry_hybrid_continental_radar_uses_ths_longitudinal_tune(self):
    fingerprint = {bus: ({0x2FF: 8} if bus == 0 else {}) for bus in range(8)}
    hybrid_fw = [CarParams.CarFw(ecu=Ecu.hybrid, address=0x7D2, fwVersion=b"test")]
    car_params = CarInterface.get_params(
      CAR.TOYOTA_CAMRY,
      fingerprint,
      hybrid_fw,
      alpha_long=True,
      is_release=False,
      docs=False,
      starpilot_toggles=SimpleNamespace(),
    )

    assert car_params.openpilotLongitudinalControl
    assert not car_params.radarUnavailable
    assert abs(car_params.radarTimeStepDEPRECATED - 0.1) < 1e-6
    assert abs(car_params.longitudinalActuatorDelay - 0.05) < 1e-6
    assert abs(car_params.vEgoStopping - 0.25) < 1e-6
    assert abs(car_params.vEgoStarting - 0.25) < 1e-6
    assert abs(car_params.stoppingDecelRate - 0.3) < 1e-6
    assert not car_params.flags & ToyotaFlags.NO_STOP_TIMER.value

    controller = get_long_tune(car_params, SimpleNamespace(ACCEL_MIN=-3.5, ACCEL_MAX=2.0))
    controller.speed = 0.0
    assert controller.k_i == pytest.approx(0.5)
    assert controller.k_f == pytest.approx(1.0)

    radar_interface = RadarInterface(car_params)
    assert radar_interface.radar_acc_tssp
    assert radar_interface.rcp is not None
    assert radar_interface.pt_cp is not None

  def test_camry_ice_keeps_legacy_longitudinal_tune(self):
    fingerprint = {bus: ({0x2FF: 8} if bus == 0 else {}) for bus in range(8)}
    car_params = CarInterface.get_params(
      CAR.TOYOTA_CAMRY,
      fingerprint,
      [],
      alpha_long=True,
      is_release=False,
      docs=False,
      starpilot_toggles=SimpleNamespace(),
    )

    assert not car_params.flags & ToyotaFlags.HYBRID.value
    assert car_params.longitudinalActuatorDelay == pytest.approx(0.15)
    assert car_params.vEgoStopping == pytest.approx(0.5)
    assert car_params.stoppingDecelRate == pytest.approx(0.8)

    controller = get_long_tune(car_params, SimpleNamespace(ACCEL_MIN=-3.5, ACCEL_MAX=2.0))
    controller.speed = 0.0
    assert controller.k_i == pytest.approx(3.6)
    assert controller.k_f == pytest.approx(1.0)

  def test_camry_continental_radar_converts_absolute_target_speed(self):
    radar_interface = RadarInterface.__new__(RadarInterface)
    radar_interface.CP = SimpleNamespace(wheelSpeedFactor=1.0)
    radar_interface.pts = {}
    radar_interface.track_id = 0
    radar_interface.RADAR_MSGS = [0x680]
    radar_interface.pt_cp = SimpleNamespace(vl={
      "WHEEL_SPEEDS": {
        "WHEEL_SPEED_FL": 36.0,
        "WHEEL_SPEED_FR": 36.0,
        "WHEEL_SPEED_RL": 36.0,
        "WHEEL_SPEED_RR": 36.0,
      },
    })
    radar_interface.rcp = SimpleNamespace(can_valid=True, vl={
      0x680: {
        "ID": 7,
        "LONG_DIST": 40.0,
        "LAT_DIST": -0.2,
        "SPEED": 11.0,
        "LAT_SPEED": 0.1,
      },
    })

    radar_data = radar_interface._update_tssp({0x680})

    assert len(radar_data.points) == 1
    assert radar_data.points[0].dRel == 40.0
    assert radar_data.points[0].vRel == pytest.approx(11.0 - 10.0 * TSSP_RADAR_EGO_SPEED_SCALE)

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
  def test_sienna_2025_route_fw_exact_match(self):
    route_fw = {
      (Ecu.engine, 0x700, None): b'\x01896630869000\x00\x00\x00\x00',
      (Ecu.abs, 0x7b0, None): b'\x01F15260823000\x00\x00\x00\x00',
      (Ecu.eps, 0x7a1, None): b'\x018965B4514000\x00\x00\x00\x00',
      (Ecu.hybrid, 0x7d2, None): b'\x02899830812000\x00\x00\x00\x00899850813000\x00\x00\x00\x00',
      (Ecu.srs, 0x780, None): b'\x028917F0815200\x00\x00\x00\x008917H0801200\x00\x00\x00\x00',
      (Ecu.fwdRadar, 0x750, 0xf): b'\x018821F3301500\x00\x00\x00\x00',
      (Ecu.fwdCamera, 0x750, 0x6d): b'\x028646F0802500\x00\x00\x00\x008646G4202100\x00\x00\x00\x00',
    }
    car_fw = [
      CarParams.CarFw(ecu=ecu, address=address, subAddress=0 if sub_address is None else sub_address,
                      fwVersion=version, brand="toyota")
      for (ecu, address, sub_address), version in route_fw.items()
    ]

    exact, matches = match_fw_to_car(car_fw, "5TDESKFC4SS158497", allow_fuzzy=False, log=False)

    assert exact
    assert matches == {CAR.TOYOTA_SIENNA_4TH_GEN}

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

  def test_no_lead_cruise_sign_flip_clamps_negative_pulse_when_set_speed_is_ahead(self):
    limited = limit_no_lead_cruise_sign_flip(-0.44, 0.0, False, 23.3, 25.0, False)
    assert limited == 0.0

  def test_no_lead_cruise_sign_flip_keeps_real_decel_requests(self):
    limited = limit_no_lead_cruise_sign_flip(-0.44, -0.15, False, 23.3, 25.0, False)
    assert limited == -0.44

  def test_no_lead_cruise_sign_flip_keeps_lead_follow_brake(self):
    limited = limit_no_lead_cruise_sign_flip(-0.44, 0.0, False, 23.3, 25.0, True)
    assert limited == -0.44

  def test_prius_stopping_accel_unwinds_stale_stop_hold(self):
    limited = limit_prius_stopping_accel(-3.28, -0.05, True, 0.0, True)
    assert -1.5 < limited < 0.0

  def test_prius_stopping_accel_keeps_hard_stop_commands(self):
    limited = limit_prius_stopping_accel(-3.28, -2.0, True, 0.0, True)
    assert limited == -3.28

  def test_prius_positive_feedforward_scale_stays_soft_at_launch_speed(self):
    assert abs(get_prius_positive_feedforward_scale(0.0) - 0.7) < 1e-6
    assert abs(get_prius_positive_feedforward_scale(8.0) - 0.7) < 1e-6

  def test_prius_positive_feedforward_scale_restores_cruise_authority(self):
    assert get_prius_positive_feedforward_scale(20.0) > get_prius_positive_feedforward_scale(8.0)
    assert abs(get_prius_positive_feedforward_scale(20.0) - 1.0) < 1e-6

  def test_prius_feedforward_adds_braking_authority_without_changing_acceleration(self):
    assert get_prius_feedforward(-2.0, 8.0) == pytest.approx(-2.25)
    assert get_prius_feedforward(1.0, 8.0) == pytest.approx(0.7)

  def test_camry_hybrid_feedforward_only_softens_acceleration(self):
    assert get_camry_hybrid_feedforward(1.0) == pytest.approx(0.8)
    assert get_camry_hybrid_feedforward(-2.0) == pytest.approx(-2.0)

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

  def test_acc_control_can_suppress_long_press_behavior_while_gap_button_is_held(self):
    packer = CANPacker(DBC[CAR.TOYOTA_HIGHLANDER_TSS2][Bus.pt])
    parser = CANParser(DBC[CAR.TOYOTA_HIGHLANDER_TSS2][Bus.pt], [("ACC_CONTROL", 0)], 0)

    default_msg = toyotacan.create_accel_command(
      packer, 0.0, False, True, False, False, 1, False, 0, False,
    )
    parser.update([(1, [default_msg])])
    assert parser.vl["ACC_CONTROL"]["ALLOW_LONG_PRESS"] == 1

    suppressed_msg = toyotacan.create_accel_command(
      packer, 0.0, False, True, False, False, 1, False, 0, False, allow_long_press=0,
    )
    parser.update([(1, [suppressed_msg])])
    assert parser.vl["ACC_CONTROL"]["ALLOW_LONG_PRESS"] == 0

  def test_auto_brake_hold_sends_modified_pre_collision_after_timer(self):
    controller = self._make_controller()
    controller.packer = CANPacker(DBC[CAR.TOYOTA_CAMRY_TSS2][Bus.pt])
    controller.frame = 0
    controller.brake_hold_active = False
    controller._brake_hold_counter = 0
    controller._brake_hold_reset = False
    controller._prev_brake_pressed = False
    cs = SimpleNamespace(
      out=SimpleNamespace(
        standstill=True,
        cruiseState=SimpleNamespace(available=True, enabled=False),
        gasPressed=False,
        brakePressed=False,
        gearShifter=structs.CarState.GearShifter.drive,
      ),
      pre_collision_2={},
    )

    can_sends = controller.create_auto_brake_hold_messages(cs, brake_hold_allowed_timer=0)

    parser = CANParser(DBC[CAR.TOYOTA_CAMRY_TSS2][Bus.pt], [("PRE_COLLISION_2", 0)], 0)
    parser.update([(1, can_sends)])
    assert controller.brake_hold_active
    assert parser.vl["PRE_COLLISION_2"]["DSS1GDRV"] == -1.0
    assert parser.vl["PRE_COLLISION_2"]["PBRTRGR"] == 1

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

  def test_interceptor_corolla_scales_with_accel_request_when_pedal_enables_sng(self):
    controller = self._make_controller()
    controller.CP.enableGasInterceptorDEPRECATED = True
    controller.CP.carFingerprint = CAR.TOYOTA_COROLLA
    controller.CP.minEnableSpeed = -1.0
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
    assert CP.safetyConfigs[0].safetyParam & ToyotaSafetyFlags.GAS_INTERCEPTOR
    assert abs(CP.longitudinalActuatorDelay - 0.2) < 1e-6
    assert CP.stopAccel == -1.5


class TestToyotaCarState:
  def test_lkas_button_platforms(self):
    assert CAR.TOYOTA_PRIUS in LKAS_BUTTON_CAR
    assert TSS2_CAR <= LKAS_BUTTON_CAR
    assert CAR.TOYOTA_CAMRY not in LKAS_BUTTON_CAR
    assert CAR.LEXUS_RX not in LKAS_BUTTON_CAR

  @pytest.mark.parametrize("lkas_button,prev_lkas_button,event_count", [
    (0, 0, 0),
    (1, 0, 2),
    (1, 1, 0),
    (0, 1, 0),
    (2, 1, 2),
  ])
  def test_lkas_button_events(self, lkas_button, prev_lkas_button, event_count):
    events = create_lkas_button_events(lkas_button, prev_lkas_button)

    assert len(events) == event_count
    if events:
      assert [(event.type, event.pressed) for event in events] == [
        (structs.CarState.ButtonEvent.Type.lkas, True),
        (structs.CarState.ButtonEvent.Type.lkas, False),
      ]

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
