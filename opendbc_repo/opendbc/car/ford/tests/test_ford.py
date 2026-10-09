import random
from collections.abc import Iterable
from types import SimpleNamespace

from hypothesis import settings, given, strategies as st
from parameterized import parameterized
import pytest

from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.can import CANPacker, CANParser
from opendbc.car.ford import fordcan
from opendbc.car.ford.carcontroller import CarController, FordStockCruiseButton, apply_brake_rate_limit, apply_creep_compensation
from opendbc.car.ford.carstate import CarState
from opendbc.car.gps import FORD_MACH_E_GPS_MESSAGES, get_car_gps_config, parse_ford_can_gps
from opendbc.car.structs import CarParams, CarState as CarStateStruct
from opendbc.car.fw_versions import build_fw_dict
from opendbc.car.ford.interface import CarInterface
from opendbc.car.ford.values import CAR, DBC, FW_QUERY_CONFIG, FW_PATTERN, FordSafetyFlags, get_platform_codes, match_vin_to_car
from opendbc.car.ford.fingerprints import FW_VERSIONS

Ecu = CarParams.Ecu


def test_stock_cruise_button_latches_context_until_release():
  button = FordStockCruiseButton()

  assert button.update(True, cruise_available=True, cruise_enabled=True) == (True, False)
  assert button.update(True, cruise_available=True, cruise_enabled=False) == (True, False)
  assert button.update(False, cruise_available=True, cruise_enabled=False) == (False, False)

  assert button.update(True, cruise_available=True, cruise_enabled=False) == (False, True)
  assert button.update(True, cruise_available=True, cruise_enabled=True) == (False, True)
  assert button.update(False, cruise_available=True, cruise_enabled=True) == (False, False)


def test_stock_cruise_button_ignores_press_with_cruise_master_off():
  button = FordStockCruiseButton()

  assert button.update(True, cruise_available=False, cruise_enabled=False) == (False, False)


@pytest.mark.parametrize("op_long", (False, True))
@pytest.mark.parametrize("standstill", (False, True))
@pytest.mark.parametrize("cruise_status", (4, 5))
@pytest.mark.parametrize("switch", ("CcAslButtnCnclResPress", "CcAslButtnCnclPress"))
def test_ford_cancel_event_does_not_require_pcm_disengagement(op_long, standstill, cruise_status, switch):
  CP = CarInterface.get_params(CAR.FORD_MUSTANG_MACH_E_MK1, gen_empty_fingerprint(), [], op_long, False, False, None)
  state = CarState(CP, None)
  parsers = state.get_can_parsers(CP)
  packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])

  for frame, (pressed, status) in enumerate(((True, cruise_status), (True, 3), (False, 3)), start=1):
    messages = [
      packer.make_can_msg("Steering_Data_FD1", fordcan.CanBus(CP).main, {switch: int(pressed)}),
      packer.make_can_msg("EngBrakeData", fordcan.CanBus(CP).main, {"CcStat_D_Actl": status}),
      packer.make_can_msg("DesiredTorqBrk", fordcan.CanBus(CP).main, {"VehStop_D_Stat": int(standstill)}),
    ]
    parsers[Bus.pt].update([(frame * 100_000_000, messages)])
    ret, _ = state.update(parsers, None)
    assert ret.standstill == standstill
    expected = [(CarStateStruct.ButtonEvent.Type.cancel, pressed)] if op_long and frame != 2 else []
    assert [(event.type, event.pressed) for event in ret.buttonEvents] == expected


@pytest.mark.parametrize("initial_status", (0, 3))
def test_ford_resume_does_not_become_cancel_when_pcm_engages(initial_status):
  CP = CarInterface.get_params(CAR.FORD_MUSTANG_MACH_E_MK1, gen_empty_fingerprint(), [], True, False, False, None)
  state = CarState(CP, None)
  parsers = state.get_can_parsers(CP)
  packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])

  for frame, (pressed, status) in enumerate(((True, initial_status), (True, 4), (False, 4)), start=1):
    messages = [
      packer.make_can_msg("Steering_Data_FD1", fordcan.CanBus(CP).main, {"CcAslButtnCnclResPress": int(pressed)}),
      packer.make_can_msg("EngBrakeData", fordcan.CanBus(CP).main, {"CcStat_D_Actl": status}),
    ]
    parsers[Bus.pt].update([(frame * 100_000_000, messages)])
    ret, _ = state.update(parsers, None)
    assert not ret.buttonEvents


def test_mach_e_does_not_apply_engine_creep_compensation():
  for accel in (-1.0, -0.1, 0.0, 0.1):
    assert apply_creep_compensation(accel, 0.5, CAR.FORD_MUSTANG_MACH_E_MK1,
                                     standstill=False, stopping=False) == accel

  assert apply_creep_compensation(0.0, 0.0, CAR.FORD_MUSTANG_MACH_E_MK1,
                                   standstill=True, stopping=True) == -0.6
  assert apply_creep_compensation(0.0, 0.5, CAR.FORD_F_150_MK14,
                                   standstill=False, stopping=False) == -0.6


@pytest.mark.parametrize("last", (0.0, 0.35, 0.8))
def test_mach_e_mild_brake_transition_shapes_regen_and_brake_together(last):
  accel, gas = apply_brake_rate_limit(-0.5, -0.5, last, 11.0, CAR.FORD_MUSTANG_MACH_E_MK1,
                                     stopping=False, standstill=False, fcw=False)
  assert accel == pytest.approx(-0.04)
  assert gas == accel


@pytest.mark.parametrize("accel,last", ((-0.2, -0.5), (-0.5, -0.48), (-0.8, -0.4)))
def test_mach_e_mild_brake_ramp_does_not_delay_release(accel, last):
  brake, gas = apply_brake_rate_limit(accel, accel, last, 11.0, CAR.FORD_MUSTANG_MACH_E_MK1,
                                     stopping=False, standstill=False, fcw=False)
  assert brake == pytest.approx(max(accel, last - 0.04))
  assert gas == brake


@pytest.mark.parametrize("accel,speed,stopping,standstill,fcw", (
  (-3.5, 11.0, False, False, False),
  (-1.0, 11.0, False, False, False),
  (-0.5, 4.9, False, False, False),
  (-0.5, 11.0, True, False, False),
  (-0.5, 11.0, False, True, False),
  (-0.5, 11.0, False, False, True),
  (0.2, 11.0, False, False, False),
))
def test_mach_e_strong_braking_stops_and_warnings_keep_original_ramp(accel, speed, stopping, standstill, fcw):
  brake, gas = apply_brake_rate_limit(accel, accel, 0.0, speed, CAR.FORD_MUSTANG_MACH_E_MK1,
                                     stopping=stopping, standstill=standstill, fcw=fcw)
  assert brake == pytest.approx(max(accel, -0.07))
  assert gas == accel


@pytest.mark.parametrize("fingerprint", [car for car in CAR if car != CAR.FORD_MUSTANG_MACH_E_MK1])
def test_other_fords_keep_original_brake_requests_and_integral_gain(fingerprint):
  brake, gas = apply_brake_rate_limit(-0.5, -0.5, 0.35, 11.0, fingerprint,
                                     stopping=False, standstill=False, fcw=False)
  assert brake == pytest.approx(0.28)
  assert gas == -0.5
  CP = CarInterface.get_params(fingerprint, gen_empty_fingerprint(), [], True, False, False, None)
  assert list(CP.longitudinalTuning.kiV) == [0.5]


def test_mach_e_integral_gain_preserves_delay_and_braking_authority():
  CP = CarInterface.get_params(CAR.FORD_MUSTANG_MACH_E_MK1, gen_empty_fingerprint(), [], True, False, False, None)
  assert list(CP.longitudinalTuning.kiV) == pytest.approx([0.3])
  assert CP.longitudinalActuatorDelay == pytest.approx(0.15)
  assert CarInterface.get_pid_accel_limits(CP, 11.0, 20.0)[0] == -3.5


def test_mach_e_can_brake_handoff_and_driver_override(monkeypatch):
  monkeypatch.setattr("opendbc.car.ford.carcontroller.FordLateralController",
                      lambda _: SimpleNamespace(update_inputs=lambda: None))
  monkeypatch.setattr(fordcan, "create_acc_ui_msg", lambda *args: (0, b"", 0))
  monkeypatch.setattr(fordcan, "create_lkas_ui_msg", lambda *args: (0, b"", 0))
  CP = CarInterface.get_params(CAR.FORD_MUSTANG_MACH_E_MK1, gen_empty_fingerprint(), [], True, False, False, None)
  controller = CarController(DBC[CP.carFingerprint], CP)
  parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("ACCDATA", 50)], 0)
  CC = structs.CarControl.new_message()
  CC.enabled = True
  CC.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid
  CS = SimpleNamespace(out=structs.CarState.new_message(), acc_tja_status_stock_values={"Tja_D_Stat": 0})
  CS.out.vEgo = 11.0

  for frame, active, request, expected in ((2, True, -0.5, -0.04), (4, False, 0.0, 0.0),
                                         (8, True, -0.5, -0.04), (14, True, -3.5, -0.11)):
    controller.frame = frame
    CC.longActive = active
    CC.actuators.accel = request
    output, messages = controller.update(CC.as_reader(), CS, frame * 10_000_000, None)
    parser.update([(frame * 10_000_000, [msg for msg in messages if msg[0] == 0x186])])
    values = parser.vl["ACCDATA"]
    assert output.accel == pytest.approx(expected)
    assert values["AccBrkTot_A_Rq"] == pytest.approx(expected, abs=0.01)
    assert values["AccPrpl_A_Rq"] == pytest.approx(expected if active and request > -1.0 else -5.0, abs=0.01)
    assert values["Cmbb_B_Enbl"] == int(active)
    assert values["AccResumEnbl_B_Rq"] == int(active)


ECU_ADDRESSES = {
  Ecu.eps: 0x730,          # Power Steering Control Module (PSCM)
  Ecu.abs: 0x760,          # Anti-Lock Brake System (ABS)
  Ecu.fwdRadar: 0x764,     # Cruise Control Module (CCM)
  Ecu.fwdCamera: 0x706,    # Image Processing Module A (IPMA)
  Ecu.engine: 0x7E0,       # Powertrain Control Module (PCM)
  Ecu.shiftByWire: 0x732,  # Gear Shift Module (GSM)
  Ecu.debug: 0x7D0,        # Accessory Protocol Interface Module (APIM)
  Ecu.hud: 0x720,          # Instrument Cluster Module (ICM)
}


ECU_PART_NUMBER = {
  Ecu.eps: [
    b"14D003",
  ],
  Ecu.abs: [
    b"2D053",
  ],
  Ecu.fwdRadar: [
    b"14D049",
  ],
  Ecu.fwdCamera: [
    b"14F397",  # Ford Q3
    b"14H102",  # Ford Q4
  ],
}


class TestFordFW:
  def test_vin_fallback(self):
    def vin(wmi, vds, powertrain, year):
      return f"{wmi}{vds}{powertrain}0{year}1234567"

    assert match_vin_to_car(vin("2FM", "PK4A", "A", "N")) == {str(CAR.FORD_EDGE_MK2)}
    assert match_vin_to_car(vin("3FM", "K1RA", "A", "M")) == {str(CAR.FORD_MUSTANG_MACH_E_MK1)}
    assert match_vin_to_car(vin("1FT", "F1CA", "A", "M")) == {str(CAR.FORD_F_150_MK14)}
    assert match_vin_to_car(vin("1FT", "F1CA", "L", "N")) == {str(CAR.FORD_F_150_LIGHTNING_MK1)}
    assert match_vin_to_car("0" * 17) == set()

  def test_fw_query_config(self):
    for (ecu, addr, subaddr) in FW_QUERY_CONFIG.extra_ecus:
      assert ecu in ECU_ADDRESSES, "Unknown ECU"
      assert addr == ECU_ADDRESSES[ecu], "ECU address mismatch"
      assert subaddr is None, "Unexpected ECU subaddress"

  @parameterized.expand(FW_VERSIONS.items())
  def test_fw_versions(self, car_model: str, fw_versions: dict[tuple[int, int, int | None], Iterable[bytes]]):
    for (ecu, addr, subaddr), fws in fw_versions.items():
      assert ecu in ECU_ADDRESSES, "Unknown ECU"
      assert addr == ECU_ADDRESSES[ecu], "ECU address mismatch"
      assert subaddr is None, "Unexpected ECU subaddress"

      if ecu not in ECU_PART_NUMBER:
        continue

      for fw in fws:
        assert len(fw) == 24, "Expected ECU response to be 24 bytes"

        match = FW_PATTERN.match(fw)
        assert match is not None, f"Unable to parse FW: {fw!r}"
        if match:
          part_number = match.group("part_number")
          assert part_number in ECU_PART_NUMBER[ecu], f"Unexpected part number for {fw!r}"

        codes = get_platform_codes([fw])
        assert 1 == len(codes), f"Unable to parse FW: {fw!r}"

  @settings(max_examples=100)
  @given(data=st.data())
  def test_platform_codes_fuzzy_fw(self, data):
    """Ensure function doesn't raise an exception"""
    fw_strategy = st.lists(st.binary())
    fws = data.draw(fw_strategy)
    get_platform_codes(fws)

  def test_platform_codes_spot_check(self):
    # Asserts basic platform code parsing behavior for a few cases
    results = get_platform_codes([
      b"JX6A-14C204-BPL\x00\x00\x00\x00\x00\x00\x00\x00\x00",
      b"NZ6T-14F397-AC\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
      b"PJ6T-14H102-ABJ\x00\x00\x00\x00\x00\x00\x00\x00\x00",
      b"LB5A-14C204-EAC\x00\x00\x00\x00\x00\x00\x00\x00\x00",
    ])
    assert results == {(b"X6A", b"J"), (b"Z6T", b"N"), (b"J6T", b"P"), (b"B5A", b"L")}

  def test_fuzzy_match(self):
    for platform, fw_by_addr in FW_VERSIONS.items():
      # Ensure there's no overlaps in platform codes
      for _ in range(20):
        car_fw = []
        for ecu, fw_versions in fw_by_addr.items():
          ecu_name, addr, sub_addr = ecu
          fw = random.choice(fw_versions)
          car_fw.append(CarParams.CarFw(ecu=ecu_name, fwVersion=fw, address=addr,
                                        subAddress=0 if sub_addr is None else sub_addr))

        CP = CarParams(carFw=car_fw)
        matches = FW_QUERY_CONFIG.match_fw_to_car_fuzzy(build_fw_dict(CP.carFw), CP.carVin, FW_VERSIONS)
        assert matches == {platform}

  def test_match_fw_fuzzy(self):
    offline_fw = {
      (Ecu.eps, 0x730, None): [
        b"L1MC-14D003-AJ\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
        b"L1MC-14D003-AL\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
      ],
      (Ecu.abs, 0x760, None): [
        b"L1MC-2D053-BA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
        b"L1MC-2D053-BD\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
      ],
      (Ecu.fwdRadar, 0x764, None): [
        b"LB5T-14D049-AB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
        b"LB5T-14D049-AD\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
      ],
      # We consider all model year hints for ECU, even with different platform codes
      (Ecu.fwdCamera, 0x706, None): [
        b"LB5T-14F397-AD\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
        b"NC5T-14F397-AF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
      ],
    }
    expected_fingerprint = CAR.FORD_EXPLORER_MK6

    # ensure that we fuzzy match on all non-exact FW with changed revisions
    live_fw = {
      (0x730, None): {b"L1MC-14D003-XX\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"},
      (0x760, None): {b"L1MC-2D053-XX\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"},
      (0x764, None): {b"LB5T-14D049-XX\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"},
      (0x706, None): {b"LB5T-14F397-XX\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"},
    }
    candidates = FW_QUERY_CONFIG.match_fw_to_car_fuzzy(live_fw, '', {expected_fingerprint: offline_fw})
    assert candidates == {expected_fingerprint}

    # model year hint in between the range should match
    live_fw[(0x706, None)] = {b"MB5T-14F397-XX\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"}
    candidates = FW_QUERY_CONFIG.match_fw_to_car_fuzzy(live_fw, '', {expected_fingerprint: offline_fw,})
    assert candidates == {expected_fingerprint}

    # unseen model year hint should not match
    live_fw[(0x760, None)] = {b"M1MC-2D053-XX\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"}
    candidates = FW_QUERY_CONFIG.match_fw_to_car_fuzzy(live_fw, '', {expected_fingerprint: offline_fw})
    assert len(candidates) == 0, "Should not match new model year hint"


def test_mach_e_longitudinal_toggle_controls_stock_acc_selection():
  stock = CarInterface.get_params(
    CAR.FORD_MUSTANG_MACH_E_MK1, gen_empty_fingerprint(), [], False, False, False, None)
  enhanced = CarInterface.get_params(
    CAR.FORD_MUSTANG_MACH_E_MK1, gen_empty_fingerprint(), [], True, False, False, None)

  assert stock.alphaLongitudinalAvailable
  assert not stock.openpilotLongitudinalControl
  assert stock.pcmCruise
  assert not (stock.safetyConfigs[-1].safetyParam & FordSafetyFlags.LONG_CONTROL)
  assert stock.safetyConfigs[-1].safetyParam & FordSafetyFlags.MACH_E_CURVATURE

  assert enhanced.alphaLongitudinalAvailable
  assert enhanced.openpilotLongitudinalControl
  assert enhanced.safetyConfigs[-1].safetyParam & FordSafetyFlags.LONG_CONTROL
  assert enhanced.safetyConfigs[-1].safetyParam & FordSafetyFlags.MACH_E_CURVATURE


def test_mach_e_can_gps_decode():
  nav1 = {
    "GpsHsphLattSth_D_Actl": 2,
    "GpsHsphLongEast_D_Actl": 2,
    "GPS_Latitude_Degrees": 37,
    "GPS_Latitude_Minutes": 57,
    "GPS_Latitude_Min_dec": 0.8864,
    "GPS_Longitude_Degrees": -121,
    "GPS_Longitude_Minutes": 44,
    "GPS_Longitude_Min_dec": 0.22,
  }
  nav2 = {
    "GpsUtcYr_No_Actl": 2026,
    "GpsUtcMnth_No_Actl": 8,
    "GpsUtcDay_No_Actl": 26,
    "GPS_UTC_hours": 0,
    "GPS_UTC_minutes": 24,
    "GPS_UTC_seconds": 38,
    "Gps_B_Falt": 0,
  }
  nav3 = {
    "GPS_dimension": 2,
    "GPS_Hdop": 0.6,
    "GPS_Vdop": 0.8,
    "GPS_Sat_num_in_view": 31,
    "GPS_MSL_altitude": 90,
    "GPS_Speed": 10,
    "GPS_Heading": 180,
  }

  gps = parse_ford_can_gps(nav1, nav2, nav3)

  assert gps is not None
  assert gps["latitude"] == 37.96477333333333
  assert gps["longitude"] == -121.737
  assert abs(gps["altitude"] - 27.432) < 1e-9
  assert abs(gps["speed"] - 10 * 0.44704) < 1e-9
  assert gps["hasFix"]
  assert gps["satelliteCount"] == 0  # 31 is Ford's invalid sentinel.


def test_mach_e_can_gps_fault_invalidates_fix():
  nav1 = {
    "GpsHsphLattSth_D_Actl": 2,
    "GpsHsphLongEast_D_Actl": 2,
    "GPS_Latitude_Degrees": 37,
    "GPS_Latitude_Minutes": 57,
    "GPS_Latitude_Min_dec": 0.8864,
    "GPS_Longitude_Degrees": -121,
    "GPS_Longitude_Minutes": 44,
    "GPS_Longitude_Min_dec": 0.22,
  }
  nav2 = {
    "GpsUtcYr_No_Actl": 2026,
    "GpsUtcMnth_No_Actl": 8,
    "GpsUtcDay_No_Actl": 26,
    "GPS_UTC_hours": 0,
    "GPS_UTC_minutes": 24,
    "GPS_UTC_seconds": 38,
    "Gps_B_Falt": 1,
  }
  nav3 = {
    "GPS_dimension": 2,
    "GPS_Hdop": 0.6,
    "GPS_Vdop": 0.8,
    "GPS_Sat_num_in_view": 31,
    "GPS_MSL_altitude": 90,
    "GPS_Speed": 0,
    "GPS_Heading": 180,
  }

  gps = parse_ford_can_gps(nav1, nav2, nav3)

  assert gps is not None
  assert not gps["hasFix"]
  assert gps["latitude"] == 37.96477333333333
  assert gps["altitude"] == 0.0


def test_mach_e_can_gps_messages_are_optional_main_bus_inputs():
  cp = CarInterface.get_params(CAR.FORD_MUSTANG_MACH_E_MK1, gen_empty_fingerprint(), [], False, False, False, None)
  parser = CarInterface.CarState.get_can_parsers(cp)[Bus.pt]
  gps_config = get_car_gps_config(cp)

  assert gps_config is not None
  assert gps_config.messages == FORD_MACH_E_GPS_MESSAGES
  assert gps_config.decoder is parse_ford_can_gps
  assert set(parser.addresses) >= {0x462, 0x463, 0x464}
  assert set(FORD_MACH_E_GPS_MESSAGES) == set(gps_config.messages) == {
    parser.dbc.addr_to_msg[0x462].name,
    parser.dbc.addr_to_msg[0x463].name,
    parser.dbc.addr_to_msg[0x464].name,
  }
  assert all(parser.message_states[address].ignore_alive for address in (0x462, 0x463, 0x464))


def test_lightning_low_rate_camera_messages_use_declared_frequencies():
  cp = CarInterface.get_params(CAR.FORD_F_150_LIGHTNING_MK1, gen_empty_fingerprint(), [], True, False, False, None)
  cp.enableBsm = True
  parser = CarInterface.CarState.get_can_parsers(cp)[Bus.cam]

  expected_frequencies = {
    "IPMA_Data": 1,
    "Traffic_RecognitnData": 1,
    "Side_Detect_L_Stat": 5,
    "Side_Detect_R_Stat": 5,
  }
  for message, frequency in expected_frequencies.items():
    state = parser.message_states[parser.dbc.name_to_msg[message].address]
    assert state.frequency == frequency
    assert state.timeout_threshold == pytest.approx(10e9 / frequency)


def test_hands_free_cluster_status_is_opt_in():
  packer = CANPacker("ford_lincoln_base_pt")
  CAN = SimpleNamespace(main=0)
  CP = SimpleNamespace(openpilotLongitudinalControl=False)
  hud = SimpleNamespace(leftLaneDepart=False, rightLaneDepart=False)
  stock_values = dict.fromkeys([
    "HaDsply_No_Cs", "HaDsply_No_Cnt", "AccStopStat_D_Dsply", "AccTrgDist2_D_Dsply",
    "AccStopRes_B_Dsply", "TjaWarn_D_Rq", "TjaMsgTxt_D_Dsply", "IaccLamp_D_Rq",
    "AccMsgTxt_D2_Rq", "FcwDeny_B_Dsply", "FcwMemStat_B_Actl", "AccTGap_B_Dsply",
    "CadsAlignIncplt_B_Actl", "AccFllwMde_B_Dsply", "CadsRadrBlck_B_Actl",
    "CmbbPostEvnt_B_Dsply", "AccStopMde_B_Dsply", "FcwMemSens_D_Actl",
    "FcwMsgTxt_D_Rq", "AccWarn_D_Dsply", "FcwVisblWarn_B_Rq", "FcwAudioWarn_B_Rq",
    "AccTGap_D_Dsply", "AccMemEnbl_B_RqDrv", "FdaMem_B_Stat",
  ], 0)

  regular = fordcan.create_acc_ui_msg(
    packer, CAN, CP, True, True, False, False, False, hud, stock_values)
  hands_free = fordcan.create_acc_ui_msg(
    packer, CAN, CP, True, True, False, False, False, hud, stock_values, True)
  expected_regular = packer.make_can_msg("ACCDATA_3", 0, {"Tja_D_Stat": 2})
  expected_hands_free = packer.make_can_msg("ACCDATA_3", 0, {"Tja_D_Stat": 7})

  assert regular == expected_regular
  assert hands_free == expected_hands_free
