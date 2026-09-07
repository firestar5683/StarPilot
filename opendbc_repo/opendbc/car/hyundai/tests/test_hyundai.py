from hypothesis import settings, given, strategies as st
from types import SimpleNamespace

import pytest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, ButtonType, gen_empty_fingerprint, structs
from opendbc.car.structs import CarControl, CarParams
from opendbc.car.fw_versions import build_fw_dict, match_fw_to_car
from opendbc.car.hyundai.carcontroller import CarController, CANCEL_BUTTON_DELAY_FRAMES, Ioniq6LongitudinalTuningState, GenesisG90LongitudinalTuningState, \
                                             EV9LongitudinalTuningState, update_ev9_longitudinal_tuning, \
                                             BlindspotWarningState, update_blindspot_warning, \
                                             reset_egmp_longitudinal_tuning, \
                                             update_ioniq_6_longitudinal_tuning, \
                                             update_genesis_g90_longitudinal_tuning, egmp_dynamic_longitudinal_tuning, \
                                             get_canfd_scc_decel_step, \
                                             should_reset_ev6_gt_line_longitudinal_tuning, reset_ev6_gt_line_longitudinal_tuning, \
                                             direct_angle_request_allowed, get_angle_smoothing_alpha, \
                                             should_use_ev6_gt_line_stop_direct_tracking, \
                                             should_track_stop_accel_directly_for_car, \
                                             preserve_stock_canfd_lfa_status, \
                                             preserve_stock_canfd_lkas_status, \
                                             suppress_redundant_gv70_brake_cancel, \
                                             clear_ioniq_6_torque_when_request_inactive
from opendbc.car.hyundai.carstate import CarState, decode_canfd_camera_lead, decode_ioniq_6_blindspot_radar_state, \
                                             get_canfd_cruise_available
from opendbc.car.hyundai.interface import CarInterface, KIA_EV9_ACCEL_MAX
from opendbc.car.hyundai import hyundaican, hyundaicanfd
from opendbc.car.hyundai.hyundaicanfd import CanBus, hkg_can_fd_checksum
from opendbc.car.hyundai.radar_interface import MRREVO14F_RADAR_START_ADDR, MRR30_RADAR_START_ADDR, MRR35_RADAR_START_ADDR, \
                                             RADAR_START_ADDR, get_radar_track_config
from opendbc.car.hyundai.values import CAMERA_SCC_CAR, CANFD_CAR, CAN_GEARS, CAR, CHECKSUM, DATE_FW_ECUS, DATELESS_FUZZY_CARS, \
                                         HYBRID_CAR, EV_CAR, FW_QUERY_CONFIG, LEGACY_SAFETY_MODE_CAR, CANFD_FUZZY_WHITELIST, \
                                         UNSUPPORTED_LONGITUDINAL_CAR, PLATFORM_CODE_ECUS, HYUNDAI_VERSION_REQUEST_LONG, \
                                         LEGACY_LONGITUDINAL_CAR, DBC, HyundaiFlags, get_platform_codes, HyundaiSafetyFlags, \
                                         HyundaiStarPilotFlags, HyundaiStarPilotSafetyFlags, Buttons, CarControllerParams, kia_ev6_gt_line_longitudinal_tuning

LongCtrlState = CarControl.Actuators.LongControlState
from opendbc.car.hyundai.fingerprints import FW_VERSIONS

Ecu = CarParams.Ecu

# Some platforms have date codes in a different format we don't yet parse (or are missing).
# For now, assert list of expected missing date cars
NO_DATES_PLATFORMS = {
  # CAN FD
  CAR.KIA_SPORTAGE_5TH_GEN,
  CAR.KIA_SPORTAGE_HEV_2026,
  CAR.HYUNDAI_SANTA_CRUZ_1ST_GEN,
  CAR.HYUNDAI_SANTA_CRUZ_2025,
  CAR.HYUNDAI_TUCSON_4TH_GEN,
  CAR.HYUNDAI_TUCSON_2025,
  CAR.HYUNDAI_TUCSON_HEV_2025,
  CAR.HYUNDAI_TUCSON_PHEV_2025,
  CAR.KIA_SPORTAGE_2026,
  # CAN
  CAR.HYUNDAI_ELANTRA,
  CAR.HYUNDAI_ELANTRA_GT_I30,
  CAR.KIA_CEED,
  CAR.KIA_XCEED_PHEV,
  CAR.KIA_FORTE,
  CAR.KIA_OPTIMA_G4,
  CAR.KIA_OPTIMA_G4_FL,
  CAR.KIA_SORENTO,
  CAR.HYUNDAI_KONA,
  CAR.HYUNDAI_KONA_NON_SCC,
  CAR.HYUNDAI_KONA_EV,
  CAR.HYUNDAI_KONA_EV_2022,
  CAR.HYUNDAI_KONA_HEV,
  CAR.HYUNDAI_SONATA_LF,
  CAR.HYUNDAI_VELOSTER,
  CAR.HYUNDAI_KONA_2022,
}

CANFD_EXPECTED_ECUS = {Ecu.fwdCamera, Ecu.fwdRadar}
HYUNDAI_NON_SCC_CARS = (
  CAR.HYUNDAI_BAYON_1ST_GEN_NON_SCC,
  CAR.HYUNDAI_ELANTRA_2022_NON_SCC,
  CAR.HYUNDAI_ELANTRA_HEV_2022_NON_SCC,
  CAR.HYUNDAI_KONA_NON_SCC,
  CAR.HYUNDAI_KONA_EV_NON_SCC,
  CAR.KIA_RAY_EV,
  CAR.KIA_CEED_PHEV_2022_NON_SCC,
  CAR.KIA_FORTE_2019_NON_SCC,
  CAR.KIA_FORTE_2021_NON_SCC,
  CAR.KIA_SELTOS_2023_NON_SCC,
  CAR.GENESIS_G70_2021_NON_SCC,
)
HYUNDAI_NON_SCC_FW_CARS = tuple(car_model for car_model in HYUNDAI_NON_SCC_CARS if car_model in FW_VERSIONS)

CCNC_NON_HDA2_CARS = (
  CAR.HYUNDAI_KONA_2ND_GEN,
  CAR.HYUNDAI_KONA_HEV_2ND_GEN,
  CAR.HYUNDAI_KONA_EV_2ND_GEN,
  CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN,
  CAR.HYUNDAI_SONATA_2024,
  CAR.HYUNDAI_SONATA_HEV_2024,
  CAR.HYUNDAI_IONIQ_5_N,
  CAR.HYUNDAI_TUCSON_2025,
  CAR.HYUNDAI_TUCSON_HEV_2025,
  CAR.HYUNDAI_TUCSON_PHEV_2025,
  CAR.HYUNDAI_SANTA_CRUZ_2025,
  CAR.KIA_K4_2025,
  CAR.KIA_K5_2025,
  CAR.KIA_CARNIVAL_2025,
  CAR.KIA_CARNIVAL_HEV_4TH_GEN,
  CAR.KIA_SPORTAGE_2026,
  CAR.KIA_SORENTO_2024,
)

ANGLE_STEERING_CARS = (
  CAR.HYUNDAI_AZERA_HEV_7TH_GEN,
  CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN,
  CAR.HYUNDAI_IONIQ_5_PE,
  CAR.HYUNDAI_IONIQ_9,
  CAR.KIA_SPORTAGE_2026,
  CAR.KIA_SPORTAGE_HEV_2026,
  CAR.KIA_SORENTO_HEV_4TH_GEN_LFA2,
  CAR.KIA_EV6_2025,
  CAR.KIA_EV9,
  CAR.GENESIS_GV70_ELECTRIFIED_2ND_GEN,
  CAR.GENESIS_GV70_2026,
  CAR.GENESIS_GV80_2025,
)


def get_test_toggles() -> SimpleNamespace:
  return SimpleNamespace(always_on_lateral_lkas=False, force_torque_controller=False, nnff=False, nnff_lite=False)


class TestHyundaiFingerprint:
  def test_carnival_hev_low_speed_torque_rate_limits(self):
    CP = CarInterface.get_params(CAR.KIA_CARNIVAL_HEV_4TH_GEN, gen_empty_fingerprint(), [],
                                 False, False, False, None)
    carnival_2025_cp = CarInterface.get_params(CAR.KIA_CARNIVAL_2025, gen_empty_fingerprint(), [],
                                                False, False, False, None)

    low_speed = CarControllerParams(CP, 10.0)
    high_speed = CarControllerParams(CP, 20.0)
    carnival_2025_low_speed = CarControllerParams(carnival_2025_cp, 10.0)

    assert (low_speed.STEER_DELTA_UP, low_speed.STEER_DELTA_DOWN) == (2, 3)
    assert (high_speed.STEER_DELTA_UP, high_speed.STEER_DELTA_DOWN) == (2, 3)
    assert (carnival_2025_low_speed.STEER_DELTA_UP, carnival_2025_low_speed.STEER_DELTA_DOWN) == (10, 8)

  @pytest.mark.parametrize("candidate", (CAR.KIA_CARNIVAL_4TH_GEN, CAR.KIA_CARNIVAL_2025, CAR.KIA_CARNIVAL_HEV_4TH_GEN))
  def test_carnival_uses_clean_canfd_lfa_status(self, candidate):
    assert not preserve_stock_canfd_lfa_status(candidate)
    assert not preserve_stock_canfd_lkas_status(candidate)
    assert preserve_stock_canfd_lfa_status(CAR.HYUNDAI_IONIQ_6)
    assert preserve_stock_canfd_lkas_status(CAR.HYUNDAI_IONIQ_6)

    CP = CarParams.new_message()
    CP.carFingerprint = candidate
    CP.flags = int(HyundaiFlags.CANFD | (HyundaiFlags.RADAR_SCC if candidate == CAR.KIA_CARNIVAL_4TH_GEN else HyundaiFlags.CCNC))
    CP.openpilotLongitudinalControl = True
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)

    stock_lfa = {"HAS_LANE_SAFETY": 1, "NEW_SIGNAL_4": 8, "DAMP_FACTOR": 100}
    lfa_base = stock_lfa if preserve_stock_canfd_lfa_status(CP.carFingerprint) else None
    lfa_msg = hyundaicanfd.create_steering_messages(packer, CP, can_bus, False, False, 0, 0.0, lfa_base)[0]
    assert lfa_msg[1] == bytes.fromhex("05100002400008000000000000640000")

    active_lfa_msg = hyundaicanfd.create_steering_messages(packer, CP, can_bus, True, True, 100, 0.0, None,
                                                            lka_icon=2)[0]
    assert active_lfa_msg[1] == bytes.fromhex("9a17010280c818000000000000640000")

    stock_cluster = {"NEW_SIGNAL_5": 1}
    cluster_base = stock_cluster if preserve_stock_canfd_lfa_status(CP.carFingerprint) else None
    cluster_msg = hyundaicanfd.create_lfahda_cluster(packer, can_bus, False, cluster_base)
    assert cluster_msg[1] == bytes.fromhex("8e040000000000000000000000000000")

    active_cluster_msg = hyundaicanfd.create_lfahda_cluster(packer, can_bus, True, None, lfa_icon=2)
    assert active_cluster_msg[1] == bytes.fromhex("cdfb0180000001000000000000000000")

  @pytest.mark.parametrize("candidate", (CAR.KIA_CARNIVAL_2025, CAR.KIA_CARNIVAL_HEV_4TH_GEN))
  def test_carnival_hda2_clears_stock_lkas_warning_status(self, candidate):
    CP = CarParams.new_message()
    CP.carFingerprint = candidate
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CCNC | HyundaiFlags.CANFD_LKA_STEERING |
                   HyundaiFlags.CANFD_LKA_STEERING_ALT)
    CP.openpilotLongitudinalControl = False

    controller = CarController(DBC[CP.carFingerprint], CP)
    controller.frame = 1
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS_ALT", 0)], can_bus.ACAN)
    stock_lkas = {
      "CHECKSUM": 1234,
      "COUNTER": 42,
      "LKA_MODE": 0,
      "LKA_AVAILABLE": 0,
      "LKA_WARNING": 0,
      "LKA_ICON": 0,
      "FCA_SYSWARN": 1,
      "TORQUE_REQUEST": 0,
      "STEER_REQ": 0,
      "LFA_BUTTON": 0,
      "LKA_ASSIST": 1,
      "STEER_MODE": 2,
      "NEW_SIGNAL_2": 3,
      "HAS_LANE_SAFETY": 0,
      "DAMP_FACTOR": 100,
    }
    cc = SimpleNamespace(enabled=False, latActive=True,
                         actuators=SimpleNamespace(longControlState=LongCtrlState.off),
                         leftBlinker=False, rightBlinker=False,
                         hudControl=SimpleNamespace())
    cs = SimpleNamespace(stock_lfa_msg=None, stock_lkas_msg=stock_lkas,
                         out=SimpleNamespace(standstill=False, steeringAngleDeg=0.0,
                                             gearShifter=structs.CarState.GearShifter.drive))

    msgs = controller.create_canfd_msgs(0, True, 123, 0.0, 0.0, 0.0, False,
                                        cc.hudControl, cs, cc, get_test_toggles(), lka_icon=2, lfa_icon=2)
    lkas_msgs = [msg for msg in msgs if msg[0] == 0x110]
    assert len(lkas_msgs) == 1

    parser.update([(1, lkas_msgs)])
    assert parser.can_valid
    assert parser.vl["LKAS_ALT"]["FCA_SYSWARN"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_ASSIST"] == 0
    assert parser.vl["LKAS_ALT"]["DAMP_FACTOR"] == 100
    assert parser.vl["LKAS_ALT"]["TORQUE_REQUEST"] == 123
    assert parser.vl["LKAS_ALT"]["STEER_REQ"] == 1

  def test_canfd_torque_bsm_parser_registers_rear_blindspots(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.EV | HyundaiFlags.CANFD_ALT_GEARS_2)
    CP.enableBsm = True

    parsers = CarState(CP, None).get_can_parsers(CP)
    pt_messages = {state.name for state in parsers[Bus.pt].message_states.values()}

    assert "BLINDSPOTS_REAR_CORNERS" in pt_messages

  def test_ev9_startup_status_messages_are_optional(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[CanBus(None, fingerprint).CAM][0x110] = 32
    radar_config = get_radar_track_config(CAR.KIA_EV9)
    fingerprint[radar_config.bus][radar_config.start_addr] = radar_config.expected_length
    car_fw = [CarParams.CarFw(ecu=Ecu.adas, fwVersion=b"", address=0x730, brand="hyundai")]

    CP = CarInterface.get_params(CAR.KIA_EV9, fingerprint, car_fw, False, False, False, None)
    parsers = CarState(CP, None).get_can_parsers(CP)
    states = parsers[Bus.pt].message_states

    assert states[0x1CF].ignore_alive
    assert states[0x1FA].ignore_alive

  def test_feature_detection(self):
    # LKA steering
    for candidate in (CAR.KIA_EV6, CAR.HYUNDAI_IONIQ_6):
      for lka_steering in (True, False):
        fingerprint = gen_empty_fingerprint()
        if lka_steering:
          cam_can = CanBus(None, fingerprint).CAM
          fingerprint[cam_can] = [0x50, 0x110]  # LKA steering messages
        CP = CarInterface.get_params(candidate, fingerprint, [], False, False, False, None)
        assert bool(CP.flags & HyundaiFlags.CANFD_LKA_STEERING) == lka_steering

    # radar available
    for candidate in (
      CAR.HYUNDAI_IONIQ,
      CAR.HYUNDAI_IONIQ_EV_LTD,
      CAR.HYUNDAI_SANTA_FE,
      CAR.HYUNDAI_SANTA_FE_2022,
      CAR.HYUNDAI_SANTA_FE_HEV_2022,
      CAR.HYUNDAI_SANTA_FE_PHEV_2022,
      CAR.HYUNDAI_SONATA,
      CAR.HYUNDAI_SONATA_HYBRID,
      CAR.KIA_XCEED_PHEV,
      CAR.KIA_K5_HEV_2020,
      CAR.KIA_NIRO_EV,
      CAR.KIA_NIRO_PHEV,
      CAR.KIA_NIRO_PHEV_2022,
      CAR.GENESIS_G70_2020,
      CAR.GENESIS_G90,
    ):
      assert get_radar_track_config(candidate).start_addr == RADAR_START_ADDR
      for radar in (True, False):
        fingerprint = gen_empty_fingerprint()
        if radar:
          fingerprint[1][RADAR_START_ADDR] = 8
        CP = CarInterface.get_params(candidate, fingerprint, [], False, False, False, None)
        assert CP.radarUnavailable != radar

    assert get_radar_track_config(CAR.HYUNDAI_SONATA_HYBRID).msg_count == 32
    assert get_radar_track_config(CAR.GENESIS_G90).msg_count == 64
    assert get_radar_track_config(CAR.GENESIS_G90).can_parser_msg_count == 32

    fingerprint = gen_empty_fingerprint()
    fingerprint[1][RADAR_START_ADDR] = 8
    for candidate in (CAR.HYUNDAI_SONATA, CAR.HYUNDAI_SONATA_HYBRID, CAR.KIA_XCEED_PHEV, CAR.GENESIS_G90):
      CP = CarInterface.get_params(candidate, fingerprint, [], True, False, False, None)
      assert CP.openpilotLongitudinalControl
      assert not CP.radarUnavailable

    for candidate, radar_addr in (
      (CAR.HYUNDAI_KONA_EV_2022, MRREVO14F_RADAR_START_ADDR),
      (CAR.HYUNDAI_IONIQ_5, MRR30_RADAR_START_ADDR),
      (CAR.HYUNDAI_IONIQ_5_PE, MRR35_RADAR_START_ADDR),
      (CAR.HYUNDAI_IONIQ_5_N, MRR30_RADAR_START_ADDR),
      (CAR.KIA_EV6, MRR30_RADAR_START_ADDR),
      (CAR.KIA_EV6_2025, MRR30_RADAR_START_ADDR),
      (CAR.GENESIS_GV60_EV_1ST_GEN, MRR30_RADAR_START_ADDR),
      (CAR.HYUNDAI_KONA_EV_2ND_GEN, MRR35_RADAR_START_ADDR),
      (CAR.HYUNDAI_IONIQ_9, MRR35_RADAR_START_ADDR),
      (CAR.KIA_EV9, MRR35_RADAR_START_ADDR),
    ):
      radar_config = get_radar_track_config(candidate)
      assert radar_config.start_addr == radar_addr
      for radar in (True, False):
        fingerprint = gen_empty_fingerprint()
        if radar:
          fingerprint[radar_config.bus][radar_addr] = radar_config.expected_length or 8
        CP = CarInterface.get_params(candidate, fingerprint, [], False, False, False, None)
        assert CP.radarUnavailable != radar

    assert get_radar_track_config(CAR.HYUNDAI_KONA_EV_2022).bus == 1
    assert get_radar_track_config(CAR.HYUNDAI_IONIQ_5).bus == 0
    ioniq_6_hda2_radar_config = get_radar_track_config(CAR.HYUNDAI_IONIQ_6)
    ioniq_6_hda1_radar_config = get_radar_track_config(CAR.HYUNDAI_IONIQ_6, HyundaiFlags.CANFD_CAMERA_SCC)
    assert ioniq_6_hda2_radar_config.start_addr == MRR35_RADAR_START_ADDR
    assert ioniq_6_hda2_radar_config.bus == 0
    assert ioniq_6_hda1_radar_config.bus == 1
    assert ioniq_6_hda1_radar_config.frequency == 20

    fingerprint = gen_empty_fingerprint()
    fingerprint[0][MRR35_RADAR_START_ADDR] = 8
    CP = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, fingerprint, [], False, False, False, None)
    assert not CP.openpilotLongitudinalControl
    assert CP.radarUnavailable

    fingerprint = gen_empty_fingerprint()
    fingerprint[ioniq_6_hda1_radar_config.bus][MRR35_RADAR_START_ADDR] = 24
    CP = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, fingerprint, [], False, False, False, None)
    assert not CP.openpilotLongitudinalControl
    assert CP.flags & HyundaiFlags.CANFD_CAMERA_SCC
    assert not CP.radarUnavailable

    CP = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, gen_empty_fingerprint(), [], True, False, False, None)
    assert CP.openpilotLongitudinalControl
    assert CP.radarUnavailable

    fingerprint = gen_empty_fingerprint()
    fingerprint[ioniq_6_hda1_radar_config.bus][MRR35_RADAR_START_ADDR] = 24
    CP = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, fingerprint, [], True, False, False, None)
    assert CP.openpilotLongitudinalControl
    assert CP.flags & HyundaiFlags.CANFD_CAMERA_SCC
    assert not CP.radarUnavailable

    fingerprint = gen_empty_fingerprint()
    fingerprint[CanBus(None, fingerprint).CAM][0x50] = 32
    fingerprint[ioniq_6_hda2_radar_config.bus][MRR35_RADAR_START_ADDR] = 24
    CP = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, fingerprint, [], True, False, False, None)
    assert CP.openpilotLongitudinalControl
    assert CP.flags & HyundaiFlags.CANFD_LKA_STEERING
    assert not CP.radarUnavailable

    fingerprint = gen_empty_fingerprint()
    fingerprint[CanBus(None, fingerprint).CAM][0x50] = 32
    fingerprint[get_radar_track_config(CAR.HYUNDAI_IONIQ_5).bus][MRR30_RADAR_START_ADDR] = 32
    CP = CarInterface.get_params(CAR.HYUNDAI_IONIQ_5, fingerprint, [], True, False, False, None)
    assert CP.openpilotLongitudinalControl
    assert not CP.radarUnavailable

    ev9_radar_config = get_radar_track_config(CAR.KIA_EV9)
    fingerprint = gen_empty_fingerprint()
    fingerprint[CanBus(None, fingerprint).CAM][0x110] = 32
    fingerprint[ev9_radar_config.bus][ev9_radar_config.start_addr] = ev9_radar_config.expected_length
    ev9_car_fw = [CarParams.CarFw(ecu=Ecu.adas, fwVersion=b"", address=0x730, brand="hyundai")]
    CP = CarInterface.get_params(CAR.KIA_EV9, fingerprint, ev9_car_fw, True, False, False, None)
    assert CP.alphaLongitudinalAvailable
    assert CP.openpilotLongitudinalControl
    assert not CP.radarUnavailable
    assert CP.flags & HyundaiFlags.CANFD_LKA_STEERING_ALT
    assert CP.flags & HyundaiFlags.CCNC
    assert egmp_dynamic_longitudinal_tuning(CP)
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CANFD_ANGLE_STEERING
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CCNC
    CP = CarInterface.get_params(CAR.KIA_EV9, fingerprint, [], True, False, False, None)
    assert CP.openpilotLongitudinalControl

    CP = CarInterface.get_params(CAR.KIA_EV9, fingerprint, ev9_car_fw, False, False, False, None)
    assert not CP.openpilotLongitudinalControl
    assert not (CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CCNC)

    ioniq_5_pe_radar_config = get_radar_track_config(CAR.HYUNDAI_IONIQ_5_PE)
    fingerprint = gen_empty_fingerprint()
    fingerprint[CanBus(None, fingerprint).CAM][0x110] = 32
    fingerprint[ioniq_5_pe_radar_config.bus][ioniq_5_pe_radar_config.start_addr] = ioniq_5_pe_radar_config.expected_length
    ioniq_5_pe_car_fw = [CarParams.CarFw(ecu=Ecu.adas, fwVersion=b"", address=0x730, brand="hyundai")]
    CP = CarInterface.get_params(CAR.HYUNDAI_IONIQ_5_PE, fingerprint, ioniq_5_pe_car_fw, True, False, False, None)
    assert CP.alphaLongitudinalAvailable
    assert CP.openpilotLongitudinalControl
    assert not CP.radarUnavailable
    assert CP.flags & HyundaiFlags.CANFD_LKA_STEERING_ALT
    assert CP.flags & HyundaiFlags.CCNC
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CANFD_ANGLE_STEERING
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CCNC

    CP = CarInterface.get_params(CAR.HYUNDAI_IONIQ_5_PE, fingerprint, ioniq_5_pe_car_fw, False, False, False, None)
    assert not CP.openpilotLongitudinalControl
    assert not (CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG)

    CP = CarInterface.get_params(CAR.HYUNDAI_IONIQ_5_PE, fingerprint, ioniq_5_pe_car_fw, True, False, False, None)
    expected_bits = (HyundaiSafetyFlags.LONG | HyundaiSafetyFlags.CCNC |
                     HyundaiSafetyFlags.CANFD_LKA_STEERING | HyundaiSafetyFlags.CANFD_LKA_STEERING_ALT |
                     HyundaiSafetyFlags.CANFD_ANGLE_STEERING | HyundaiSafetyFlags.EV_GAS)
    assert (CP.safetyConfigs[-1].safetyParam & expected_bits) == expected_bits

    gv70_fingerprint = gen_empty_fingerprint()
    gv70_fingerprint[CanBus(None, gv70_fingerprint).CAM][0x50] = 32
    gv70_car_fw = [CarParams.CarFw(ecu=Ecu.adas, fwVersion=b"", address=0x730, brand="hyundai")]
    CP = CarInterface.get_params(CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN, gv70_fingerprint, gv70_car_fw,
                                 True, False, False, None)
    assert CP.alphaLongitudinalAvailable
    assert CP.openpilotLongitudinalControl
    assert CP.radarUnavailable
    assert CP.flags & HyundaiFlags.CANFD_LKA_STEERING
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CANFD_LKA_STEERING
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.EV_GAS

    for candidate in HYUNDAI_NON_SCC_CARS:
      CP = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], True, False, False, None)
      assert bool(CP.flags & HyundaiFlags.NON_SCC)
      assert not CP.alphaLongitudinalAvailable
      assert CP.pcmCruise

    CP = CarInterface.get_params(CAR.KIA_SPORTAGE_HEV_2026, gen_empty_fingerprint(), [], False, False, False, None)
    assert CP.steerControlType == CarParams.SteerControlType.angle
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CANFD_ANGLE_STEERING
    assert not (CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CCNC)

    fingerprint = gen_empty_fingerprint()
    cam_can = CanBus(None, fingerprint).CAM
    fingerprint[cam_can][0xCB] = 24
    CP = CarInterface.get_params(CAR.KIA_SPORTAGE_HEV_2026, fingerprint, [], False, False, False, None)
    assert CP.flags & HyundaiFlags.SEND_LFA

  def test_smart_mdps_allows_low_speed_steering(self):
    candidate = CAR.HYUNDAI_IONIQ_EV_LTD

    regular_fingerprint = gen_empty_fingerprint()
    regular_cp = CarInterface.get_params(candidate, regular_fingerprint, [], False, False, False, None)
    assert regular_cp.flags & HyundaiFlags.MIN_STEER_32_MPH
    assert regular_cp.minSteerSpeed > 0.0

    smart_mdps_fingerprint = gen_empty_fingerprint()
    smart_mdps_fingerprint[0][0x2AA] = 8
    smart_mdps_cp = CarInterface.get_params(candidate, smart_mdps_fingerprint, [], False, False, False, None)
    assert not (smart_mdps_cp.flags & HyundaiFlags.MIN_STEER_32_MPH)
    assert smart_mdps_cp.minSteerSpeed == 0.0
    assert smart_mdps_cp.steerAtStandstill

  @pytest.mark.parametrize("candidate", CCNC_NON_HDA2_CARS)
  def test_ccnc_non_hda2_platforms_set_ccnc_safety(self, candidate):
    CP = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], False, False, False, None)

    assert CP.flags & HyundaiFlags.CCNC
    assert CP.flags & HyundaiFlags.CANFD_CAMERA_SCC
    assert not (CP.flags & HyundaiFlags.CANFD_LKA_STEERING)
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CCNC
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CAMERA_SCC

  @pytest.mark.parametrize("candidate", ANGLE_STEERING_CARS)
  def test_angle_steering_platforms_use_angle_control(self, candidate):
    CP = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], False, False, False, None)

    assert CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING
    assert CP.steerControlType == CarParams.SteerControlType.angle
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CANFD_ANGLE_STEERING

  def test_ev9_uses_shared_angle_smoothing(self):
    ev9_cp = SimpleNamespace(carFingerprint=CAR.KIA_EV9)
    other_cp = SimpleNamespace(carFingerprint=CAR.KIA_SPORTAGE_HEV_2026)

    assert get_angle_smoothing_alpha(ev9_cp, 0.0) == pytest.approx(get_angle_smoothing_alpha(other_cp, 0.0))
    assert get_angle_smoothing_alpha(ev9_cp, 13.8) == pytest.approx(get_angle_smoothing_alpha(other_cp, 13.8))
    assert get_angle_smoothing_alpha(ev9_cp, 20.0) == pytest.approx(get_angle_smoothing_alpha(other_cp, 20.0))
    assert get_angle_smoothing_alpha(other_cp, 20.0) == pytest.approx(0.0)

  def test_ev9_direct_angle_waits_for_safety_envelope(self):
    CP = CarInterface.get_params(CAR.KIA_EV9, gen_empty_fingerprint(), [], True, False, False, None)
    controller = CarController(DBC[CP.carFingerprint], CP)

    assert not direct_angle_request_allowed(8.47, 155.5, 155.6, True, controller.BASELINE_VM, controller.params)
    assert direct_angle_request_allowed(8.47, 140.0, 140.0, True, controller.BASELINE_VM, controller.params)
    assert not direct_angle_request_allowed(8.47, 140.0, 140.0, False, controller.BASELINE_VM, controller.params)

  def test_angle_platforms_standstill_steering_flags(self):
    ev9_cp = CarInterface.get_params(CAR.KIA_EV9, gen_empty_fingerprint(), [], False, False, False, None)
    ioniq_5_pe_cp = CarInterface.get_params(CAR.HYUNDAI_IONIQ_5_PE, gen_empty_fingerprint(), [], False, False, False, None)
    sportage_cp = CarInterface.get_params(CAR.KIA_SPORTAGE_HEV_2026, gen_empty_fingerprint(), [], False, False, False, None)

    assert not ev9_cp.steerAtStandstill
    assert ioniq_5_pe_cp.steerAtStandstill
    assert not sportage_cp.steerAtStandstill

  @pytest.mark.parametrize("candidate", (CAR.KIA_K4_2025, CAR.KIA_CARNIVAL_2025, CAR.KIA_CARNIVAL_HEV_4TH_GEN))
  def test_ccnc_hda2_lka_layout_does_not_set_ccnc_safety_param(self, candidate):
    fingerprint = gen_empty_fingerprint()
    cam_can = CanBus(None, fingerprint).CAM
    fingerprint[cam_can] = {0x50: 16}

    CP = CarInterface.get_params(candidate, fingerprint, [], False, False, False, None)

    assert CP.flags & HyundaiFlags.CCNC
    assert CP.flags & HyundaiFlags.CANFD_LKA_STEERING
    assert not (CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CCNC)

  def test_carnival_hev_sets_hybrid_gas_safety(self):
    CP = CarInterface.get_params(CAR.KIA_CARNIVAL_HEV_4TH_GEN, gen_empty_fingerprint(), [], False, False, False, None)

    assert CP.flags & HyundaiFlags.HYBRID
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.HYBRID_GAS

  @pytest.mark.parametrize("candidate", (CAR.KIA_CARNIVAL_2025, CAR.KIA_CARNIVAL_HEV_4TH_GEN))
  def test_carnival_hda2_detects_alternate_buttons(self, candidate):
    fingerprint = gen_empty_fingerprint()
    CAN = CanBus(None, fingerprint)
    fingerprint[CAN.CAM] = {0x110: 32}
    fingerprint[1] = {0x1aa: 16}

    carnival_cp = CarInterface.get_params(candidate, fingerprint, [], False, False, False, None)
    assert carnival_cp.flags & HyundaiFlags.CANFD_LKA_STEERING_ALT
    assert carnival_cp.flags & HyundaiFlags.CANFD_ALT_BUTTONS
    assert carnival_cp.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CANFD_ALT_BUTTONS

    carnival_state = CarState(carnival_cp, None)
    pt_states = {state.name for state in carnival_state.get_can_parsers(carnival_cp)[Bus.pt].message_states.values()}
    assert "CRUISE_BUTTONS" not in pt_states

    k4_cp = CarInterface.get_params(CAR.KIA_K4_2025, fingerprint, [], False, False, False, None)
    assert not (k4_cp.flags & HyundaiFlags.CANFD_ALT_BUTTONS)

  @pytest.mark.parametrize("candidate", (CAR.KIA_CARNIVAL_2025, CAR.KIA_CARNIVAL_HEV_4TH_GEN))
  def test_carnival_hda1_resume_uses_alternate_button_frame(self, candidate):
    fingerprint = gen_empty_fingerprint()
    fingerprint[0] = {0x1AA: 16}
    CP = CarInterface.get_params(candidate, fingerprint, [], False, False, False, None)
    assert CP.flags & HyundaiFlags.CANFD_ALT_BUTTONS
    assert not CP.openpilotLongitudinalControl
    assert "CRUISE_BUTTONS_ALT" in {
      state.name for state in CarState(CP, None).get_can_parsers(CP)[Bus.pt].message_states.values()
    }

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    address, dat, bus = hyundaicanfd.create_buttons(
      packer, CP, CanBus(CP), 0x41, Buttons.RES_ACCEL,
      base_values={"SET_ME_1": 1, "DISTANCE_UNIT": 0},
    )
    assert (address, bus) == (0x1AA, CanBus(CP).CAM)
    assert dat[2] == 0x41
    assert (dat[4] >> 4) & 0x7 == Buttons.RES_ACCEL
    assert int.from_bytes(dat[:2], "little") == hkg_can_fd_checksum(address, None, bytearray(dat))

  def test_ioniq_6_hda1_layout_stays_non_lka(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[1] = {0x100: 8, 0x110: 8}

    CP = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, fingerprint, [], False, False, False, None)

    assert not (CP.flags & HyundaiFlags.CCNC)
    assert not (CP.flags & HyundaiFlags.CANFD_LKA_STEERING)
    assert bool(CP.flags & HyundaiFlags.CANFD_CAMERA_SCC)

  def test_ioniq_6_clears_torque_with_inactive_safety_request(self):
    ioniq_6_cp = SimpleNamespace(carFingerprint=CAR.HYUNDAI_IONIQ_6)
    other_cp = SimpleNamespace(carFingerprint=CAR.KIA_EV6)

    assert clear_ioniq_6_torque_when_request_inactive(ioniq_6_cp, -409, False) == 0
    assert clear_ioniq_6_torque_when_request_inactive(ioniq_6_cp, -409, True) == -409
    assert clear_ioniq_6_torque_when_request_inactive(other_cp, -409, False) == -409

    palisade_2023 = CarInterface.get_params(CAR.HYUNDAI_PALISADE_2023, gen_empty_fingerprint(), [], True, False, False, None)
    assert palisade_2023.flags & HyundaiFlags.CAN_CANFD_BLENDED
    assert DBC[palisade_2023.carFingerprint][Bus.pt] == "hyundai_palisade_2023_generated"
    assert palisade_2023.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CAN_CANFD_BLENDED
    assert palisade_2023.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CANCEL_BTN_ENABLE

  def test_palisade_telluride_hda2_uses_mixed_can_layout(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[2][0x50] = 16
    car_fw = [CarParams.CarFw(ecu=Ecu.adas, fwVersion=b"", address=0x730, brand="hyundai")]

    CP = CarInterface.get_params(CAR.HYUNDAI_PALISADE_2023, fingerprint, car_fw, True, False, False, None)
    can_bus = CanBus(CP)
    parsers = CarState(CP, None).get_can_parsers(CP)

    assert CP.flags & HyundaiFlags.CAN_CANFD_BLENDED
    assert CP.flags & HyundaiFlags.CANFD_LKA_STEERING
    assert CP.alphaLongitudinalAvailable
    assert CP.openpilotLongitudinalControl
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CAN_CANFD_BLENDED
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CANFD_LKA_STEERING
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG
    assert can_bus.ACAN == 0
    assert can_bus.ECAN == 1
    assert parsers[Bus.pt].bus == 1
    assert parsers[Bus.cam].bus == 2
    scc12_state = next(state for state in parsers[Bus.pt].message_states.values() if state.name == "SCC12")
    assert scc12_state.frequency == 0
    assert CarControllerParams(CP).STEER_MAX == 384

  def test_palisade_telluride_hda2_sends_lkas_and_camera_suppression(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[2][0x50] = 16
    car_fw = [CarParams.CarFw(ecu=Ecu.adas, fwVersion=b"", address=0x730, brand="hyundai")]
    CP = CarInterface.get_params(CAR.HYUNDAI_PALISADE_2023, fingerprint, car_fw, False, False, False, None)
    controller = CarController(DBC[CP.carFingerprint], CP)
    controller.frame = 0

    hud_control = SimpleNamespace(
      visualAlert=CarControl.HUDControl.VisualAlert.none,
      leftLaneVisible=True,
      rightLaneVisible=True,
      leftLaneDepart=False,
      rightLaneDepart=False,
    )
    lfa_block_msg = {f"BYTE{i}": 0 for i in range(3, 24) if i != 7}
    lfa_block_msg["COUNTER"] = 0
    CS = SimpleNamespace(lfa_block_msg=lfa_block_msg, redneck_send_button=Buttons.NONE)
    CC = SimpleNamespace(enabled=True, cruiseControl=SimpleNamespace(cancel=False, resume=False))
    actuators = SimpleNamespace(longControlState=LongCtrlState.off)

    msgs = controller.create_can_msgs(True, 100, False, 0.0, 0.0, False, hud_control, actuators, CS, CC, 2, 2)
    msg_addrs_buses = {(addr, bus) for addr, _, bus in msgs}

    assert (0x50, 0) in msg_addrs_buses
    assert (0x2A4, 0) in msg_addrs_buses
    assert not ({0x340, 0x364} & {addr for addr, _, _ in msgs})

  def test_palisade_telluride_hda2_long_sends_complete_support_set(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[2][0x50] = 16
    fingerprint[1][0x38D] = 8
    car_fw = [CarParams.CarFw(ecu=Ecu.adas, fwVersion=b"", address=0x730, brand="hyundai")]
    CP = CarInterface.get_params(CAR.HYUNDAI_PALISADE_2023, fingerprint, car_fw, True, False, False, None)
    controller = CarController(DBC[CP.carFingerprint], CP)
    controller.frame = 0

    hud_control = SimpleNamespace(
      visualAlert=CarControl.HUDControl.VisualAlert.none,
      leftLaneVisible=True,
      rightLaneVisible=True,
      leftLaneDepart=False,
      rightLaneDepart=False,
      leadDistanceBars=3,
      leadVisible=True,
    )
    lfa_block_msg = {f"BYTE{i}": 0 for i in range(3, 24) if i != 7}
    lfa_block_msg["COUNTER"] = 0
    CS = SimpleNamespace(lfa_block_msg=lfa_block_msg, redneck_send_button=Buttons.NONE, lkas11={}, msg_364={},
                         out=SimpleNamespace(vEgoRaw=5.0))
    CC = SimpleNamespace(enabled=True, cruiseControl=SimpleNamespace(cancel=False, resume=False, override=False))
    actuators = SimpleNamespace(longControlState=LongCtrlState.pid)

    msgs = controller.create_can_msgs(True, 0, False, 42.0, 0.0, False, hud_control, actuators, CS, CC, 2, 2)
    msg_addrs_buses = {(addr, bus) for addr, _, bus in msgs}

    assert {
      (0x50, 0), (0x2A4, 0), (0x51, 0),
      (0x340, 1), (0x485, 1), (0x420, 1), (0x421, 1), (0x389, 1), (0x38D, 1),
      (0x363, 1), (0x398, 1), (0x399, 1), (0x39A, 1), (0x39B, 1), (0x39C, 1), (0x43A, 1),
    } <= msg_addrs_buses
    assert (0x364, 1) not in msg_addrs_buses

  def test_g70_aol_uses_active_lkas_icon(self):
    CP = CarInterface.get_params(CAR.GENESIS_G70_2020, gen_empty_fingerprint(), [], False, False, False, None)
    controller = CarController(DBC[CP.carFingerprint], CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS11", 0)], 0)

    hud_control = SimpleNamespace(
      visualAlert=CarControl.HUDControl.VisualAlert.none,
      leftLaneVisible=True,
      rightLaneVisible=True,
      leftLaneDepart=False,
      rightLaneDepart=False,
    )
    CS = SimpleNamespace(lkas11=parser.vl["LKAS11"])
    CC = SimpleNamespace(enabled=False, cruiseControl=SimpleNamespace(cancel=False, resume=False))
    actuators = SimpleNamespace(longControlState=LongCtrlState.off)

    msgs = controller.create_can_msgs(True, 100, False, 0.0, 0.0, False, hud_control, actuators, CS, CC, 2, 0)
    lkas11 = next(msg for msg in msgs if msg[0] == 0x340)
    parser.update([(1, [lkas11])])

    assert parser.vl["LKAS11"]["CF_Lkas_FcwOpt_USM"] == 2

  def test_kona_non_scc_uses_no_individual_lane_lkas_status(self):
    CP = CarInterface.get_params(CAR.HYUNDAI_KONA_NON_SCC, gen_empty_fingerprint(), [], False, False, False, None)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS11", 0)], 0)

    lkas11 = parser.vl["LKAS11"]
    msg = hyundaican.create_lkas11(
      packer, 0, CP, 0, True, False, lkas11, False, 4, False,
      True, True, 0, 0, 2,
    )
    parser.update([(1, [msg])])

    assert parser.vl["LKAS11"]["CF_Lkas_LdwsSysState"] == 2
    assert parser.vl["LKAS11"]["CF_Lkas_LdwsOpt_USM"] == 2
    assert parser.vl["LKAS11"]["CF_Lkas_LdwsActivemode"] == 0
    assert parser.vl["LKAS11"]["CF_Lkas_FcwOpt_USM"] == 0

  def test_kia_ray_ev_preserves_stock_inactive_lkas_status(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[2][0x485] = 4
    CP = CarInterface.get_params(CAR.KIA_RAY_EV, fingerprint, [], False, False, False, None)
    assert CP.flags & HyundaiFlags.SEND_LFA
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS11", 0)], 0)

    lkas11 = parser.vl["LKAS11"]
    lkas11.update({
      "CF_Lkas_LdwsActivemode": 0,
      "CF_Lkas_LdwsSysState": 1,
      "CF_Lkas_FcwOpt_USM": 1,
    })
    msg = hyundaican.create_lkas11(
      packer, 0, CP, 0, True, False, lkas11, False, 4, False,
      True, True, 0, 0, 2,
    )
    parser.update([(1, [msg])])

    assert parser.vl["LKAS11"]["CF_Lkas_LdwsActivemode"] == 0
    assert parser.vl["LKAS11"]["CF_Lkas_LdwsSysState"] == 1
    assert parser.vl["LKAS11"]["CF_Lkas_LdwsOpt_USM"] == 0
    assert parser.vl["LKAS11"]["CF_Lkas_FcwOpt_USM"] == 1

  def test_kia_ray_ev_uses_active_lkas_status_when_enabled(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[2][0x485] = 4
    CP = CarInterface.get_params(CAR.KIA_RAY_EV, fingerprint, [], False, False, False, None)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS11", 0)], 0)

    lkas11 = parser.vl["LKAS11"]
    lkas11.update({
      "CF_Lkas_LdwsActivemode": 0,
      "CF_Lkas_LdwsSysState": 1,
      "CF_Lkas_FcwOpt_USM": 1,
    })
    msg = hyundaican.create_lkas11(
      packer, 0, CP, 0, True, False, lkas11, False, 4, True,
      True, True, 0, 0, 2,
    )
    parser.update([(1, [msg])])

    assert parser.vl["LKAS11"]["CF_Lkas_LdwsActivemode"] == 3
    assert parser.vl["LKAS11"]["CF_Lkas_LdwsSysState"] == 4
    assert parser.vl["LKAS11"]["CF_Lkas_LdwsOpt_USM"] == 0
    assert parser.vl["LKAS11"]["CF_Lkas_FcwOpt_USM"] == 2

  def test_kia_ray_ev_delays_first_lkas11(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[2][0x485] = 4
    CP = CarInterface.get_params(CAR.KIA_RAY_EV, fingerprint, [], False, False, False, None)
    controller = CarController(DBC[CP.carFingerprint], CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS11", 0)], 0)

    hud_control = SimpleNamespace(
      visualAlert=CarControl.HUDControl.VisualAlert.none,
      leftLaneVisible=True,
      rightLaneVisible=True,
      leftLaneDepart=False,
      rightLaneDepart=False,
    )
    CS = SimpleNamespace(lkas11=parser.vl["LKAS11"], redneck_send_button=Buttons.NONE)
    CC = SimpleNamespace(enabled=False, cruiseControl=SimpleNamespace(cancel=False, resume=False, override=False))
    actuators = SimpleNamespace(longControlState=LongCtrlState.off)

    first = controller.create_can_msgs(True, 0, False, 0.0, 0.0, False, hud_control, actuators, CS, CC, 2, 0)
    second = controller.create_can_msgs(True, 0, False, 0.0, 0.0, False, hud_control, actuators, CS, CC, 2, 0)

    assert not any(addr == 0x340 for addr, _, _ in first)
    assert any(addr == 0x340 for addr, _, _ in second)

  def test_stock_scc_cancel_waits_for_factory_disengagement(self):
    CP = CarInterface.get_params(CAR.HYUNDAI_SANTA_FE_2022, gen_empty_fingerprint(), [], False, False, False, None)
    controller = CarController(DBC[CP.carFingerprint], CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS11", 0), ("CLU11", 0)], 0)

    hud_control = SimpleNamespace(
      visualAlert=CarControl.HUDControl.VisualAlert.none,
      leftLaneVisible=True,
      rightLaneVisible=True,
      leftLaneDepart=False,
      rightLaneDepart=False,
    )
    CS = SimpleNamespace(
      lkas11=parser.vl["LKAS11"],
      clu11=parser.vl["CLU11"],
      redneck_send_button=Buttons.NONE,
      is_metric=False,
    )
    CC = SimpleNamespace(enabled=False, cruiseControl=SimpleNamespace(cancel=True, resume=False))
    actuators = SimpleNamespace(longControlState=LongCtrlState.off)

    for counter in range(1, CANCEL_BUTTON_DELAY_FRAMES + 1):
      controller.cancel_counter = counter
      msgs = controller.create_can_msgs(True, 0, False, 0.0, 0.0, False, hud_control, actuators, CS, CC, 2, 2)
      assert not any(addr == 0x4F1 for addr, _, _ in msgs)

    controller.cancel_counter = CANCEL_BUTTON_DELAY_FRAMES + 1
    msgs = controller.create_can_msgs(True, 0, False, 0.0, 0.0, False, hud_control, actuators, CS, CC, 2, 2)
    assert any(addr == 0x4F1 for addr, _, _ in msgs)

  @pytest.mark.parametrize("candidate", (CAR.HYUNDAI_ELANTRA_2024, CAR.HYUNDAI_ELANTRA_HEV_2024))
  def test_hyundai_can_refresh_platforms_use_refresh_dbc_and_safety_param(self, candidate):
    CP = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], False, False, False, None)

    assert DBC[CP.carFingerprint][Bus.pt] == "hyundai_can_refresh_generated"
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CAN_REFRESH_MSGS

  def test_elantra_refresh_decodes_classic_media_buttons(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.HYUNDAI_ELANTRA_HEV_2024, gen_empty_fingerprint(), [], True, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_ELANTRA_HEV_2024, gen_empty_fingerprint(), [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    media_msg = packer.make_can_msg("GW_SWRC_PE", 0, {"C_ModeSW": 1, "C_MTSSW": 1})

    can_parsers[Bus.pt].update([(1_000_000_000, [media_msg])])
    _, fp_ret = car_state.update(can_parsers, toggles)

    assert fp_ret.modePressed
    assert fp_ret.customPressed

  def test_hyundai_lkas_button_sets_starpilot_safety_flag(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x391] = 8

    sonata = CarInterface.get_params(CAR.HYUNDAI_SONATA, fingerprint, [], False, False, False, None)
    assert sonata.safetyConfigs[-1].safetyParam & HyundaiStarPilotSafetyFlags.HAS_LDA_BUTTON

    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x50C] = 8
    forte_non_scc = CarInterface.get_params(CAR.KIA_FORTE_2021_NON_SCC, fingerprint, [], False, False, False, None)
    assert forte_non_scc.safetyConfigs[-1].safetyParam & HyundaiStarPilotSafetyFlags.HAS_LDA_BUTTON

    g90 = CarInterface.get_params(CAR.GENESIS_G90, gen_empty_fingerprint(), [], False, False, False, None)
    assert g90.safetyConfigs[-1].safetyParam & HyundaiStarPilotSafetyFlags.HAS_LDA_BUTTON

    sonata_without_lda = CarInterface.get_params(CAR.HYUNDAI_SONATA, gen_empty_fingerprint(), [], False, False, False, None)
    assert not (sonata_without_lda.safetyConfigs[-1].safetyParam & HyundaiStarPilotSafetyFlags.HAS_LDA_BUTTON)

    palisade_2023 = CarInterface.get_params(CAR.HYUNDAI_PALISADE_2023, gen_empty_fingerprint(), [], True, False, False, None)
    assert palisade_2023.safetyConfigs[-1].safetyParam & HyundaiStarPilotSafetyFlags.HAS_LDA_BUTTON

  def test_lkas12_da_warning_is_filtered_for_camera_fingerprint(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[2][0x53E] = 6
    CP = CarInterface.get_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], False, False, False, None)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], CP, get_test_toggles())
    assert FPCP.flags & HyundaiStarPilotFlags.HAS_LKAS12

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    stock = {
      "CF_Lkas_TsrSlifOpt": 3,
      "CF_LkasTsrStatus": 2,
      "CF_Lkas_TsrSpeed_Display_Clu": 80,
      "CF_LkasTsrSpeed_Display_Navi": 70,
      "CF_Lkas_TsrAddinfo_Display": 1,
      "CF_Lkas_Daw_USM": 0,
      "CF_LkasDawStatus": 1,
    }
    msg = hyundaican.create_lkas12(packer, stock)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS12", 0)], 0)
    parser.update([(1, [msg])])

    assert parser.can_valid
    assert parser.vl["LKAS12"]["CF_LkasDawStatus"] == 0
    assert parser.vl["LKAS12"]["CF_Lkas_TsrSpeed_Display_Clu"] == 80

    no_lkas12 = CarInterface.get_params(CAR.HYUNDAI_SONATA_HYBRID, gen_empty_fingerprint(), [], False, False, False, None)
    no_lkas12_fpcp = CarInterface.get_starpilot_params(
      CAR.HYUNDAI_SONATA_HYBRID, gen_empty_fingerprint(), [], no_lkas12, get_test_toggles(),
    )
    assert not (no_lkas12_fpcp.flags & HyundaiStarPilotFlags.HAS_LKAS12)

  def test_ray_ev_does_not_treat_eight_byte_53e_as_lkas12(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[2][0x53E] = 8
    CP = CarInterface.get_params(CAR.KIA_RAY_EV, fingerprint, [], False, False, False, None)
    FPCP = CarInterface.get_starpilot_params(CAR.KIA_RAY_EV, fingerprint, [], CP, get_test_toggles())

    assert not (FPCP.flags & HyundaiStarPilotFlags.HAS_LKAS12)

  def test_ray_ev_does_not_treat_eight_byte_485_as_lfa(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[2][0x485] = 8
    CP = CarInterface.get_params(CAR.KIA_RAY_EV, fingerprint, [], False, False, False, None)

    assert not (CP.flags & HyundaiFlags.SEND_LFA)

  def test_non_ray_legacy_platform_keeps_53e_lkas12_detection(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[2][0x53E] = 8
    CP = CarInterface.get_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], False, False, False, None)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], CP, get_test_toggles())

    assert FPCP.flags & HyundaiStarPilotFlags.HAS_LKAS12

  def test_carnival_lka_button_does_not_enable_angle_steering_safety(self):
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x391] = 8
    toggles = SimpleNamespace(always_on_lateral_lkas=True)

    CP = CarInterface.get_params(CAR.KIA_CARNIVAL_4TH_GEN, fingerprint, [], True, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.KIA_CARNIVAL_4TH_GEN, fingerprint, [], CP, toggles)
    combined_safety_param = CP.safetyConfigs[-1].safetyParam | FPCP.safetyConfigs[-1].safetyParam

    assert CP.steerControlType == CarParams.SteerControlType.torque
    assert not (CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING)
    assert not (combined_safety_param & HyundaiSafetyFlags.CANFD_ANGLE_STEERING)
    assert combined_safety_param & HyundaiSafetyFlags.LONG
    assert combined_safety_param & HyundaiStarPilotSafetyFlags.AOL_LKAS_ON_ENGAGE

  @pytest.mark.parametrize("candidate, tracks_main_cruise", (
    (CAR.HYUNDAI_ELANTRA_2021, False),
    (CAR.HYUNDAI_ELANTRA_HEV_2024, True),
    (CAR.HYUNDAI_SONATA_HYBRID, False),
  ))
  def test_legacy_hyundai_long_main_cruise_tracking_is_vehicle_specific(self, candidate, tracks_main_cruise):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], True, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(
      candidate, gen_empty_fingerprint(), [], CP, toggles,
    )
    assert bool(FPCP.flags & HyundaiStarPilotFlags.MAIN_CRUISE_STATE_TRACKING) is tracks_main_cruise

    ioniq_cp = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, gen_empty_fingerprint(), [], True, False, False, toggles)
    ioniq_fpcp = CarInterface.get_starpilot_params(
      CAR.HYUNDAI_IONIQ_6, gen_empty_fingerprint(), [], ioniq_cp, toggles,
    )
    assert not (ioniq_fpcp.flags & HyundaiStarPilotFlags.MAIN_CRUISE_STATE_TRACKING)

  def test_non_scc_flag_quirks(self):
    elantra_hev = CarInterface.get_params(CAR.HYUNDAI_ELANTRA_HEV_2022_NON_SCC, gen_empty_fingerprint(), [], True, False, False, None)
    assert elantra_hev.flags & HyundaiFlags.HYBRID

    kona = CarInterface.get_params(CAR.HYUNDAI_KONA_NON_SCC, gen_empty_fingerprint(), [], True, False, False, None)
    assert not (kona.flags & HyundaiFlags.NON_SCC_RADAR_FCA)
    assert kona.radarUnavailable

    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x38d] = 8
    fingerprint[1][MRREVO14F_RADAR_START_ADDR] = 8
    kona_radar_fca = CarInterface.get_params(CAR.HYUNDAI_KONA_NON_SCC, fingerprint, [], True, False, False, None)
    assert kona_radar_fca.flags & HyundaiFlags.NON_SCC_RADAR_FCA
    assert not kona_radar_fca.radarUnavailable

    car_fw = [CarParams.CarFw(ecu=Ecu.fwdRadar, fwVersion=b"", address=0x7d0, brand="hyundai")]
    kona_radar_fw = CarInterface.get_params(CAR.HYUNDAI_KONA_NON_SCC, gen_empty_fingerprint(), car_fw, True, False, False, None)
    assert kona_radar_fw.flags & HyundaiFlags.NON_SCC_RADAR_FCA

    forte_2019 = CarInterface.get_params(CAR.KIA_FORTE_2019_NON_SCC, gen_empty_fingerprint(), [], True, False, False, None)
    assert forte_2019.flags & HyundaiFlags.NON_SCC_NO_FCA
    assert not (forte_2019.flags & HyundaiFlags.NON_SCC_RADAR_FCA)

    forte_2021 = CarInterface.get_params(CAR.KIA_FORTE_2021_NON_SCC, gen_empty_fingerprint(), [], True, False, False, None)
    assert not (forte_2021.flags & HyundaiFlags.NON_SCC_NO_FCA)
    assert not (forte_2021.flags & HyundaiFlags.NON_SCC_RADAR_FCA)

    g70_2021 = CarInterface.get_params(CAR.GENESIS_G70_2021_NON_SCC, gen_empty_fingerprint(), [], True, False, False, None)
    assert g70_2021.flags & HyundaiFlags.NON_SCC_RADAR_FCA

  @pytest.mark.parametrize(("candidate", "expected_msgs", "unexpected_msgs"), [
    (CAR.HYUNDAI_ELANTRA_2022_NON_SCC, ("EMS16", "LVR12"), ()),
    (CAR.HYUNDAI_ELANTRA_HEV_2022_NON_SCC, ("E_CRUISE_CONTROL", "ELECT_GEAR"), ("EMS16",)),
    (CAR.HYUNDAI_KONA_EV_NON_SCC, ("LABEL11", "EMS12", "E_EMS11"), ()),
    (CAR.KIA_RAY_EV, ("LABEL11", "E_EMS11", "ELECT_GEAR"), ("EMS12", "SCC11", "SCC12")),
  ])
  def test_non_scc_cruise_message_selection(self, candidate, expected_msgs, unexpected_msgs):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], True, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(candidate, gen_empty_fingerprint(), [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)

    ret, _ = car_state.update(can_parsers, toggles)
    pt_states = {state.name for state in can_parsers[Bus.pt].message_states.values()}

    assert set(expected_msgs).issubset(pt_states)
    assert set(unexpected_msgs).isdisjoint(pt_states)
    assert not ret.cruiseState.available
    assert not ret.cruiseState.enabled
    assert ret.cruiseState.speed == 0

  def test_kia_ray_ev_decodes_cruise_state(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.KIA_RAY_EV, gen_empty_fingerprint(), [], True, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.KIA_RAY_EV, gen_empty_fingerprint(), [], CP, toggles)
    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])

    can_parsers[Bus.pt].update([(1_000_000_000, [
      packer.make_can_msg("LABEL11", 0, {"CC_React": 1, "CC_Engaged": 1}),
      packer.make_can_msg("E_EMS11", 0, {"Cruise_Limit_Target": 10, "Accel_Pedal_Pos": 0}),
      packer.make_can_msg("ELECT_GEAR", 0, {"Elect_Gear_Shifter": 5}),
    ])])

    ret, _ = car_state.update(can_parsers, toggles)

    assert ret.cruiseState.available
    assert ret.cruiseState.enabled
    assert ret.cruiseState.speed == pytest.approx(10 * 0.2777778)

  def test_kia_ray_ev_decodes_bcm_lkas_button_pulse(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.KIA_RAY_EV, gen_empty_fingerprint(), [], True, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.KIA_RAY_EV, gen_empty_fingerprint(), [], CP, toggles)
    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])

    def update(ray_lkas_button: int, frame: int):
      msg = packer.make_can_msg("BCM_PO_11", 0, {"RAY_LKAS_BTN": ray_lkas_button})
      can_parsers[Bus.pt].update([(frame, [msg])])
      return car_state.update(can_parsers, toggles)[0]

    update(0, 1)
    ret = update(1, 2)
    assert any(be.type == ButtonType.lkas and be.pressed for be in ret.buttonEvents)

    ret = update(0, 3)
    assert any(be.type == ButtonType.lkas and not be.pressed for be in ret.buttonEvents)

    ret = update(2, 4)
    assert any(be.type == ButtonType.lkas and be.pressed for be in ret.buttonEvents)

  def test_non_ray_does_not_use_ray_lkas_signal(self):
    CP = CarInterface.get_params(CAR.KIA_FORTE_2021_NON_SCC, gen_empty_fingerprint(), [], False, False, False, None)
    car_state = CarState(CP, CarInterface.get_starpilot_params(CAR.KIA_FORTE_2021_NON_SCC,
                                                                gen_empty_fingerprint(), [], CP, get_test_toggles()))
    parser_cycle = SimpleNamespace(
      vl={
        "CLU13": {"CF_Clu_LdwsLkasSW": 0},
        "BCM_PO_11": {"LDA_BTN": 0, "RAY_LKAS_BTN": 1},
      },
      ts_nanos={
        "CLU13": {"CF_Clu_LdwsLkasSW": 1},
        "BCM_PO_11": {"LDA_BTN": 1, "RAY_LKAS_BTN": 1},
      },
    )

    assert not car_state.create_lkas_button_events(parser_cycle, 0)

  def test_hyundai_redneck_cruise_availability(self, monkeypatch):
    class FakeParams:
      def __init__(self, *args, **kwargs):
        pass

      @staticmethod
      def get_bool(key):
        return key == "RedneckCruise"

    toggles = get_test_toggles()
    monkeypatch.setattr("opendbc.car.interfaces.Params", FakeParams)

    non_scc_cp = CarInterface.get_params(CAR.KIA_FORTE_2021_NON_SCC, gen_empty_fingerprint(), [], True, False, False, toggles)
    non_scc_fpcp = CarInterface.get_starpilot_params(CAR.KIA_FORTE_2021_NON_SCC, gen_empty_fingerprint(), [], non_scc_cp, toggles)
    assert non_scc_fpcp.redneckCruiseAvailable
    assert not non_scc_fpcp.pcmCruiseSpeed
    assert non_scc_cp.openpilotLongitudinalControl
    assert non_scc_cp.pcmCruise
    assert not non_scc_cp.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG
    assert not CarInterface(non_scc_cp, non_scc_fpcp).CC.long_active_ecu

    canfd_alt_buttons_cp = CarInterface.get_params(CAR.KIA_EV6, gen_empty_fingerprint(), [], False, False, False, toggles)
    canfd_alt_buttons_fpcp = CarInterface.get_starpilot_params(CAR.KIA_EV6, gen_empty_fingerprint(), [], canfd_alt_buttons_cp, toggles)
    assert canfd_alt_buttons_cp.flags & HyundaiFlags.CANFD_ALT_BUTTONS
    assert not canfd_alt_buttons_fpcp.redneckCruiseAvailable

  def test_hyundai_non_scc_without_redneck_keeps_stock_longitudinal_mode(self, monkeypatch):
    class FakeParams:
      def __init__(self, *args, **kwargs):
        pass

      @staticmethod
      def get_bool(key):
        return False

    toggles = get_test_toggles()
    monkeypatch.setattr("opendbc.car.interfaces.Params", FakeParams)

    CP = CarInterface.get_params(CAR.KIA_FORTE_2021_NON_SCC, gen_empty_fingerprint(), [], True, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.KIA_FORTE_2021_NON_SCC, gen_empty_fingerprint(), [], CP, toggles)

    assert not CP.openpilotLongitudinalControl
    assert CP.pcmCruise
    assert FPCP.pcmCruiseSpeed

  def test_hyundai_full_long_keeps_redneck_cruise_disabled(self, monkeypatch):
    class FakeParams:
      def __init__(self, *args, **kwargs):
        pass

      @staticmethod
      def get_bool(key):
        return key == "RedneckCruise"

    toggles = get_test_toggles()
    monkeypatch.setattr("opendbc.car.interfaces.Params", FakeParams)

    for candidate in (CAR.HYUNDAI_SONATA, CAR.KIA_FORTE):
      CP = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], True, False, False, toggles)
      FPCP = CarInterface.get_starpilot_params(candidate, gen_empty_fingerprint(), [], CP, toggles)

      assert CP.openpilotLongitudinalControl
      assert not FPCP.redneckCruiseAvailable
      assert FPCP.pcmCruiseSpeed

  def test_hyundai_scc_stock_long_keeps_redneck_cruise_disabled(self, monkeypatch):
    class FakeParams:
      def __init__(self, *args, **kwargs):
        pass

      @staticmethod
      def get_bool(key):
        return key == "RedneckCruise"

    toggles = get_test_toggles()
    monkeypatch.setattr("opendbc.car.interfaces.Params", FakeParams)

    for candidate in (CAR.HYUNDAI_SONATA, CAR.KIA_FORTE, CAR.HYUNDAI_IONIQ_6):
      CP = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], False, False, False, toggles)
      FPCP = CarInterface.get_starpilot_params(candidate, gen_empty_fingerprint(), [], CP, toggles)

      assert not CP.openpilotLongitudinalControl
      assert not FPCP.redneckCruiseAvailable
      assert FPCP.pcmCruiseSpeed

  def test_palisade_2023_pause_resume_button_maps_to_enable(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.HYUNDAI_PALISADE_2023, gen_empty_fingerprint(), [], True, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_PALISADE_2023, gen_empty_fingerprint(), [], CP, toggles)
    car_state = CarState(CP, FPCP)

    car_state.out.cruiseState.enabled = False
    events = car_state.create_cruise_button_events(Buttons.CANCEL, Buttons.NONE)
    assert [(be.type, be.pressed) for be in events] == [(ButtonType.accelCruise, True)]

    events = car_state.create_cruise_button_events(Buttons.NONE, Buttons.CANCEL)
    assert [(be.type, be.pressed) for be in events] == [(ButtonType.accelCruise, False)]

    car_state.out.cruiseState.enabled = True
    events = car_state.create_cruise_button_events(Buttons.CANCEL, Buttons.NONE)
    assert [(be.type, be.pressed) for be in events] == [(ButtonType.cancel, True)]

  def test_ccnc_angle_long_main_cruise_toggle(self):
    car_state = SimpleNamespace(main_cruise_on=False)
    ret = SimpleNamespace(
      cruiseState=SimpleNamespace(available=True),
      buttonEvents=[structs.CarState.ButtonEvent(pressed=True, type=ButtonType.mainCruise)],
    )
    assert CarState.update_main_cruise(car_state, ret)

    ret.buttonEvents = [structs.CarState.ButtonEvent(pressed=False, type=ButtonType.mainCruise)]
    assert CarState.update_main_cruise(car_state, ret)

    ret.buttonEvents = [structs.CarState.ButtonEvent(pressed=True, type=ButtonType.mainCruise)]
    assert not CarState.update_main_cruise(car_state, ret)

  def test_ev9_stock_fallback_uses_tcs_cruise_availability(self):
    CP = SimpleNamespace(carFingerprint=CAR.KIA_EV9, openpilotLongitudinalControl=False)
    cp = SimpleNamespace(vl={"TCS": {"ACCEnable": 0}})

    assert get_canfd_cruise_available(CP, cp, False)

    cp.vl["TCS"]["ACCEnable"] = 1
    assert not get_canfd_cruise_available(CP, cp, True)

    other_cp = SimpleNamespace(carFingerprint=CAR.HYUNDAI_IONIQ_6, openpilotLongitudinalControl=False)
    assert not get_canfd_cruise_available(other_cp, cp, False)

  def test_palisade_2023_cancel_release_enables_from_standby(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.HYUNDAI_PALISADE_2023, gen_empty_fingerprint(), [], True, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_PALISADE_2023, gen_empty_fingerprint(), [], CP, toggles)
    car_state = CarState(CP, FPCP)

    car_state.out.cruiseState.enabled = False
    assert not car_state.update_button_enable([structs.CarState.ButtonEvent(pressed=True, type=ButtonType.cancel)])
    assert car_state.update_button_enable([structs.CarState.ButtonEvent(pressed=False, type=ButtonType.cancel)])

    car_state.out.cruiseState.enabled = True
    assert not car_state.update_button_enable([structs.CarState.ButtonEvent(pressed=False, type=ButtonType.cancel)])

  def test_palisade_2023_disable_failure_falls_back_to_stock_acc(self, monkeypatch):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.HYUNDAI_PALISADE_2023, gen_empty_fingerprint(), [], True, False, False, toggles)

    called = {}

    def fake_disable_ecu(*args, **kwargs):
      called.update(kwargs)
      return False

    monkeypatch.setattr("opendbc.car.hyundai.interface.disable_ecu", fake_disable_ecu)
    CarInterface.init(CP, None, None)

    assert called["reset"] is True
    assert not CP.openpilotLongitudinalControl
    assert CP.pcmCruise
    assert not (CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG)

  @pytest.mark.parametrize("candidate", (CAR.KIA_EV9, CAR.HYUNDAI_IONIQ_5_PE))
  def test_angle_longitudinal_ready_state_skips_ecu_disable(self, candidate, monkeypatch):
    toggles = get_test_toggles()
    radar_config = get_radar_track_config(candidate)
    fingerprint = gen_empty_fingerprint()
    fingerprint[CanBus(None, fingerprint).CAM][0x110] = 32
    fingerprint[radar_config.bus][radar_config.start_addr] = radar_config.expected_length
    car_fw = [CarParams.CarFw(ecu=Ecu.adas, fwVersion=b"", address=0x730, brand="hyundai")]
    CP = CarInterface.get_params(candidate, fingerprint, car_fw, True, False, False, toggles)
    bus = CanBus(CP).ECAN
    disable_calls = []

    def fake_disable_ecu(*args, **kwargs):
      disable_calls.append(kwargs)
      return True

    def can_recv(*, wait_for_one=True):
      ready_msg = SimpleNamespace(address=0x35, src=bus, dat=bytes([0, 0, 0, 0x40]))
      return [[ready_msg]]

    monkeypatch.setattr("opendbc.car.hyundai.interface.disable_ecu", fake_disable_ecu)
    CarInterface.init(CP, can_recv, None)

    assert not any(call.get("addr") in (0x730, 0x7D0) for call in disable_calls)
    assert not CP.openpilotLongitudinalControl
    assert CP.pcmCruise
    assert not (CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG)

  def test_xceed_phev_alpha_long_is_isolated_legacy_experiment(self):
    toggles = get_test_toggles()

    ceed = CarInterface.get_params(CAR.KIA_CEED, gen_empty_fingerprint(), [], True, False, False, toggles)
    assert CAR.KIA_CEED not in LEGACY_LONGITUDINAL_CAR
    assert not ceed.alphaLongitudinalAvailable
    assert not ceed.openpilotLongitudinalControl
    assert ceed.pcmCruise
    assert ceed.safetyConfigs[-1].safetyModel == CarParams.SafetyModel.hyundaiLegacy
    assert not (ceed.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG)

    stock_xceed = CarInterface.get_params(CAR.KIA_XCEED_PHEV, gen_empty_fingerprint(), [], False, False, False, toggles)
    assert CAR.KIA_XCEED_PHEV in LEGACY_LONGITUDINAL_CAR
    assert stock_xceed.alphaLongitudinalAvailable
    assert not stock_xceed.openpilotLongitudinalControl
    assert stock_xceed.pcmCruise
    assert stock_xceed.safetyConfigs[-1].safetyModel == CarParams.SafetyModel.hyundaiLegacy
    assert stock_xceed.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.HYBRID_GAS
    assert not (stock_xceed.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG)

    long_xceed = CarInterface.get_params(CAR.KIA_XCEED_PHEV, gen_empty_fingerprint(), [], True, False, False, toggles)
    assert long_xceed.alphaLongitudinalAvailable
    assert long_xceed.openpilotLongitudinalControl
    assert not long_xceed.pcmCruise
    assert long_xceed.safetyConfigs[-1].safetyModel == CarParams.SafetyModel.hyundaiLegacy
    assert long_xceed.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.HYBRID_GAS
    assert long_xceed.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG

  def test_g80_alpha_long_preserves_legacy_safety(self):
    toggles = get_test_toggles()

    stock_g80 = CarInterface.get_params(CAR.GENESIS_G80, gen_empty_fingerprint(), [], False, False, False, toggles)
    assert CAR.GENESIS_G80 in LEGACY_LONGITUDINAL_CAR
    assert stock_g80.alphaLongitudinalAvailable
    assert not stock_g80.openpilotLongitudinalControl
    assert stock_g80.pcmCruise
    assert stock_g80.safetyConfigs[-1].safetyModel == CarParams.SafetyModel.hyundaiLegacy
    assert not (stock_g80.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG)

    long_g80 = CarInterface.get_params(CAR.GENESIS_G80, gen_empty_fingerprint(), [], True, False, False, toggles)
    assert long_g80.alphaLongitudinalAvailable
    assert long_g80.openpilotLongitudinalControl
    assert not long_g80.pcmCruise
    assert long_g80.safetyConfigs[-1].safetyModel == CarParams.SafetyModel.hyundaiLegacy
    assert long_g80.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG

  @pytest.mark.parametrize("ecu_disabled", (True, False))
  def test_g80_alpha_long_disables_stock_scc(self, monkeypatch, ecu_disabled):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.GENESIS_G80, gen_empty_fingerprint(), [], True, False, False, toggles)

    called = {}

    def fake_disable_ecu(*args, **kwargs):
      called.update(kwargs)
      return ecu_disabled

    monkeypatch.setattr("opendbc.car.hyundai.interface.disable_ecu", fake_disable_ecu)
    CarInterface.init(CP, None, None)

    assert called["addr"] == 0x7d0
    assert called["bus"] == 0
    assert called["reset"] is False
    assert CP.openpilotLongitudinalControl == ecu_disabled
    assert CP.pcmCruise != ecu_disabled
    assert bool(CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG) == ecu_disabled

  def test_xceed_phev_disable_failure_falls_back_to_stock_acc(self, monkeypatch):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.KIA_XCEED_PHEV, gen_empty_fingerprint(), [], True, False, False, toggles)

    called = {}

    def fake_disable_ecu(*args, **kwargs):
      called.update(kwargs)
      return False

    monkeypatch.setattr("opendbc.car.hyundai.interface.disable_ecu", fake_disable_ecu)
    CarInterface.init(CP, None, None)

    assert called["addr"] == 0x7d0
    assert called["bus"] == 0
    assert called["reset"] is False
    assert not CP.openpilotLongitudinalControl
    assert CP.pcmCruise
    assert not (CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG)

  def test_canfd_longitudinal_params_match_family_tune(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.KIA_EV6, gen_empty_fingerprint(), [], True, False, False, toggles)

    assert CP.vEgoStopping == pytest.approx(0.3)
    assert CP.vEgoStarting == pytest.approx(0.1)
    assert CP.stoppingDecelRate == pytest.approx(0.4)
    assert CP.longitudinalActuatorDelay == pytest.approx(0.5)
    assert CP.startingState

  def test_kia_ev6_gt_line_post_fingerprint_longitudinal_params(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.KIA_EV6, gen_empty_fingerprint(), [], True, False, False, toggles)
    CP.carVin = "KNDC4DLC0P0000000"

    CarInterface.apply_post_fingerprint_params(CP, CAR.KIA_EV6, gen_empty_fingerprint(), [])

    assert CP.startAccel == pytest.approx(1.4)
    assert CP.vEgoStarting == pytest.approx(0.5)
    assert CP.longitudinalActuatorDelay == pytest.approx(0.5)
    assert CP.vEgoStopping == pytest.approx(0.3)
    assert CP.stoppingDecelRate == pytest.approx(0.4)
    assert kia_ev6_gt_line_longitudinal_tuning(CP.carFingerprint, CP.carVin)
    assert egmp_dynamic_longitudinal_tuning(CP)
    assert should_reset_ev6_gt_line_longitudinal_tuning(CP, LongCtrlState.off)
    assert not should_reset_ev6_gt_line_longitudinal_tuning(CP, LongCtrlState.pid)

    stale_state = Ioniq6LongitudinalTuningState(desired_accel=-2.2, actual_accel=-2.2, accel_last=-2.2,
                                                jerk_upper=1.0, jerk_lower=5.0,
                                                long_control_state_last=LongCtrlState.stopping)
    reset_state = reset_ev6_gt_line_longitudinal_tuning(stale_state, CP, LongCtrlState.off)
    assert reset_state.actual_accel == pytest.approx(0.0)
    assert reset_state.accel_last == pytest.approx(0.0)
    assert reset_state.long_control_state_last == LongCtrlState.off

  def test_kia_ev6_gt_line_testing_ground_longitudinal_params(self, monkeypatch):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.KIA_EV6, gen_empty_fingerprint(), [], True, False, False, toggles)
    CP.carVin = "00000000000000000"

    monkeypatch.setattr(
      "opendbc.car.hyundai.interface.testing_ground",
      SimpleNamespace(use=lambda slot_id: slot_id == "5"),
    )
    CarInterface.apply_post_fingerprint_params(CP, CAR.KIA_EV6, gen_empty_fingerprint(), [])

    assert CP.startAccel == pytest.approx(1.4)
    assert CP.vEgoStarting == pytest.approx(0.5)
    assert CP.longitudinalActuatorDelay == pytest.approx(0.5)

    assert kia_ev6_gt_line_longitudinal_tuning(CP.carFingerprint, CP.carVin, testing_ground_active=True)
    assert not kia_ev6_gt_line_longitudinal_tuning(CAR.KIA_EV6_2025, CP.carVin, testing_ground_active=True)

  def test_kia_ev6_non_gt_line_keeps_family_longitudinal_params(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.KIA_EV6, gen_empty_fingerprint(), [], True, False, False, toggles)
    CP.carVin = "KNDC3DLC0P0000000"

    CarInterface.apply_post_fingerprint_params(CP, CAR.KIA_EV6, gen_empty_fingerprint(), [])

    assert CP.startAccel == pytest.approx(1.0)
    assert CP.vEgoStarting == pytest.approx(0.1)
    assert CP.longitudinalActuatorDelay == pytest.approx(0.5)
    assert not kia_ev6_gt_line_longitudinal_tuning(CP.carFingerprint, CP.carVin)
    assert not egmp_dynamic_longitudinal_tuning(CP)
    assert not should_reset_ev6_gt_line_longitudinal_tuning(CP, LongCtrlState.off)
    stale_state = Ioniq6LongitudinalTuningState(actual_accel=-2.2, accel_last=-2.2)
    assert reset_ev6_gt_line_longitudinal_tuning(stale_state, CP, LongCtrlState.off) is stale_state

  def test_genesis_g90_longitudinal_params_bias_toward_earlier_stop_handoff(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.GENESIS_G90, gen_empty_fingerprint(), [], True, False, False, toggles)

    assert CP.vEgoStopping == pytest.approx(0.8)
    assert CP.stoppingDecelRate == pytest.approx(0.55)

  def test_palisade_2023_longitudinal_params_soften_final_stop_hold(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.HYUNDAI_PALISADE_2023, gen_empty_fingerprint(), [], True, False, False, toggles)

    assert CP.startAccel == pytest.approx(1.3)
    assert CP.stopAccel == pytest.approx(-0.85)
    assert CP.vEgoStarting == pytest.approx(0.5)
    assert CP.vEgoStopping == pytest.approx(0.35)
    assert CP.stoppingDecelRate == pytest.approx(0.35)

  def test_elantra_2021_longitudinal_params_match_observed_response(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.HYUNDAI_ELANTRA_2021, gen_empty_fingerprint(), [], True, False, False, toggles)

    assert CP.longitudinalActuatorDelay == pytest.approx(0.22)
    assert CP.stopAccel == pytest.approx(-0.85)
    assert CP.stoppingDecelRate == pytest.approx(0.35)

  def test_elantra_hev_2024_longitudinal_delay_matches_observed_response(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.HYUNDAI_ELANTRA_HEV_2024, gen_empty_fingerprint(), [], True, False, False, toggles)

    assert CP.longitudinalActuatorDelay == pytest.approx(0.22)

  def test_santa_fe_2022_longitudinal_tune_tracks_slow_scc_response(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.HYUNDAI_SANTA_FE_2022, gen_empty_fingerprint(), [], True, False, False, toggles)

    assert CP.longitudinalActuatorDelay == pytest.approx(0.4)
    assert list(CP.longitudinalTuning.kpBP) == pytest.approx([0.0, 8.0, 20.0, 35.0])
    assert list(CP.longitudinalTuning.kpV) == pytest.approx([0.20, 0.17, 0.12, 0.08])
    assert list(CP.longitudinalTuning.kiBP) == pytest.approx([0.0, 8.0, 20.0, 35.0])
    assert list(CP.longitudinalTuning.kiV) == pytest.approx([0.02, 0.03, 0.05, 0.07])

  def test_kia_niro_phev_2022_longitudinal_params_soften_final_stop_hold(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.KIA_NIRO_PHEV_2022, gen_empty_fingerprint(), [], True, False, False, toggles)

    assert CP.stopAccel == pytest.approx(-1.4)
    assert CP.vEgoStopping == pytest.approx(0.7)
    assert CP.stoppingDecelRate == pytest.approx(0.5)

  @pytest.mark.parametrize("candidate", HYUNDAI_NON_SCC_FW_CARS)
  def test_non_scc_fw_exact_matches(self, candidate):
    car_fw = [
      CarParams.CarFw(
        ecu=ecu,
        fwVersion=fw_versions[0],
        address=address,
        subAddress=0 if sub_address is None else sub_address,
        brand="hyundai",
      )
      for (ecu, address, sub_address), fw_versions in FW_VERSIONS[candidate].items()
    ]

    exact, matches = match_fw_to_car(car_fw, "", allow_exact=True, allow_fuzzy=False, log=False)
    assert exact
    assert matches == {candidate}

  def test_kona_ev_non_scc_has_no_dedicated_fw_coverage(self):
    assert CAR.HYUNDAI_KONA_EV_NON_SCC not in FW_VERSIONS

  def test_elantra_hev_2026_route_fw_exact_matches_2024_platform(self):
    route_fw = {
      (Ecu.fwdCamera, 0x7c4): b'\xf1\x00CN7HMFC  AT USA LHD 1.00 1.05 99210-AA510 240509',
      (Ecu.fwdRadar, 0x7d0): b'\xf1\x00CN7_ RDR -----      1.00 1.01 99110-AA500         ',
      (Ecu.eps, 0x7d4): b'\xf1\x00CN7 MDPS C 1.00 1.03 56300BY670\x00 4CSHC103',
    }
    car_fw = [
      CarParams.CarFw(ecu=ecu, fwVersion=version, address=address, subAddress=0, brand="hyundai")
      for (ecu, address), version in route_fw.items()
    ]

    exact, matches = match_fw_to_car(car_fw, "", allow_exact=True, allow_fuzzy=False, log=False)
    assert exact
    assert matches == {CAR.HYUNDAI_ELANTRA_HEV_2024}

  def test_kia_carnival_2025_canadian_route_fw_exact_matches(self):
    route_fw = {
      (Ecu.fwdCamera, 0x7c4): b'\xf1\x00KA4 MFC  AT CAN LHD 1.00 1.00 99210-R0700 250324',
      (Ecu.fwdRadar, 0x7d0): b'\xf1\x00KA4_ RDR -----      1.00 1.01 99110-R0510         ',
    }
    car_fw = [
      CarParams.CarFw(ecu=ecu, fwVersion=version, address=address, subAddress=0, brand="hyundai")
      for (ecu, address), version in route_fw.items()
    ]

    exact, matches = match_fw_to_car(car_fw, "", allow_exact=True, allow_fuzzy=False, log=False)
    assert exact
    assert matches == {CAR.KIA_CARNIVAL_2025}

  def test_genesis_gv70_2026_route_fw_exact_matches(self):
    route_fw = {
      (Ecu.fwdCamera, 0x7c4): b'\xf1\x00JK  MFC  AT USA LHD 1.00 1.11 99211-IY600 241125',
      (Ecu.fwdRadar, 0x7d0): b'\xf1\x00JK__ RDR -----      1.00 1.01 99110-AR600         ',
    }
    car_fw = [
      CarParams.CarFw(ecu=ecu, fwVersion=version, address=address, subAddress=0, brand="hyundai")
      for (ecu, address), version in route_fw.items()
    ]

    exact, matches = match_fw_to_car(car_fw, "", allow_exact=True, allow_fuzzy=False, log=False)
    assert exact
    assert matches == {CAR.GENESIS_GV70_2026}

  def test_genesis_gv70_2026_uses_gas_angle_configuration(self):
    CP = CarInterface.get_params(CAR.GENESIS_GV70_2026, gen_empty_fingerprint(), [], False, False, False, None)

    assert CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING
    assert not (CP.flags & HyundaiFlags.EV)
    assert CP.steerControlType == CarParams.SteerControlType.angle
    assert CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.CANFD_ANGLE_STEERING

  def test_kona_non_scc_fca_radar_fw_is_optional(self):
    fw_versions = FW_VERSIONS[CAR.HYUNDAI_KONA_NON_SCC]
    car_fw = [
      CarParams.CarFw(
        ecu=ecu,
        fwVersion=versions[0],
        address=address,
        subAddress=0 if sub_address is None else sub_address,
        brand="hyundai",
      )
      for (ecu, address, sub_address), versions in fw_versions.items()
      if ecu != Ecu.fwdRadar
    ]

    exact, matches = match_fw_to_car(car_fw, "", allow_exact=True, allow_fuzzy=False, log=False)
    assert exact
    assert CAR.HYUNDAI_KONA_NON_SCC in matches

  def test_kona_non_scc_fw_matches_with_unstable_transmission_padding(self):
    route_fw = {
      (Ecu.eps, 0x7d4): b'\xf1\x00OS  MDPS C 1.00 1.05 56310/J9500 4OSDC105',
      (Ecu.fwdCamera, 0x7c4): b'\xf1\x00OS9 LKAS AT AUS RHD 1.00 1.00 95740-J9200 g30',
      (Ecu.fwdRadar, 0x7d0): b'\xf1\x00OS__ FCA --CUP      1.00 1.00 95655-J9100         ',
      (Ecu.transmission, 0x7e1): b'\xf1\x006U2V0_C2\x00\x006U2V1051\x00\x00DOS4T16AS2\x0e\xdc_\xa7',
    }
    car_fw = [
      CarParams.CarFw(ecu=ecu, fwVersion=version, address=address, subAddress=0, brand="hyundai")
      for (ecu, address), version in route_fw.items()
    ]

    exact, matches = match_fw_to_car(car_fw, "", log=False)
    assert not exact
    assert matches == {CAR.HYUNDAI_KONA_NON_SCC}

  def test_kia_forte_2019_non_scc_does_not_require_fca11_or_scc12(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.KIA_FORTE_2019_NON_SCC, gen_empty_fingerprint(), [], True, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.KIA_FORTE_2019_NON_SCC, gen_empty_fingerprint(), [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)

    car_state.update(can_parsers, toggles)
    pt_states = {state.name for state in can_parsers[Bus.pt].message_states.values()}
    assert "FCA11" not in pt_states
    assert "SCC12" not in pt_states

  def test_kia_forte_2021_non_scc_uses_fca11_without_scc12(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.KIA_FORTE_2021_NON_SCC, gen_empty_fingerprint(), [], True, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.KIA_FORTE_2021_NON_SCC, gen_empty_fingerprint(), [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    fca11_addr = packer.dbc.name_to_msg["FCA11"].address

    assert can_parsers[Bus.pt].message_states[fca11_addr].ignore_alive

    car_state.update(can_parsers, toggles)
    pt_states = {state.name for state in can_parsers[Bus.pt].message_states.values()}
    assert "FCA11" in pt_states
    assert "SCC12" not in pt_states

    for frame in range(1, 6):
      t = frame * 100_000_000
      for parser in can_parsers.values():
        required_msgs = []
        for state in parser.message_states.values():
          if state.ignore_alive:
            continue
          values = {}
          if state.name == "EMS16":
            values["CRUISE_LAMP_M"] = 1
            values["CRUISE_LAMP_S"] = 1
          elif state.name == "LVR12":
            values["CF_Lvr_CruiseSet"] = 30
          required_msgs.append(packer.make_can_msg(state.name, parser.bus, values))
        parser.update([(t, required_msgs)])

    assert all(parser.can_valid for parser in can_parsers.values())

    ret, _ = car_state.update(can_parsers, toggles)
    assert ret.cruiseState.enabled
    assert ret.cruiseState.speed > 0

  def test_alternate_limits(self):
    # Alternate lateral control limits, for high torque cars, verify Panda safety mode flag is set
    fingerprint = gen_empty_fingerprint()
    for car_model in CAR:
      CP = CarInterface.get_params(car_model, fingerprint, [], False, False, False, None)
      assert bool(CP.flags & HyundaiFlags.ALT_LIMITS) == bool(CP.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.ALT_LIMITS)

  def test_can_features(self):
    # Test no EV/HEV in any gear lists (should all use ELECT_GEAR)
    assert set.union(*CAN_GEARS.values()) & (HYBRID_CAR | EV_CAR) == set()

    # Test CAN FD car not in CAN feature lists
    can_specific_feature_list = set.union(*CAN_GEARS.values(), *CHECKSUM.values(), LEGACY_SAFETY_MODE_CAR, UNSUPPORTED_LONGITUDINAL_CAR, CAMERA_SCC_CAR)
    for car_model in CANFD_CAR:
      assert car_model not in can_specific_feature_list, "CAN FD car unexpectedly found in a CAN feature list"

  def test_hybrid_ev_sets(self):
    assert HYBRID_CAR & EV_CAR == set(), "Shared cars between hybrid and EV"
    assert CANFD_CAR & HYBRID_CAR == set(), "Hard coding CAN FD cars as hybrid is no longer supported"

  def test_canfd_ecu_whitelist(self):
    # Asserts only expected Ecus can exist in database for CAN-FD cars
    for car_model in CANFD_CAR:
      ecus = {fw[0] for fw in FW_VERSIONS[car_model].keys()}
      ecus_not_in_whitelist = ecus - CANFD_EXPECTED_ECUS
      ecu_strings = ", ".join([f"Ecu.{ecu}" for ecu in ecus_not_in_whitelist])
      assert len(ecus_not_in_whitelist) == 0, \
                       f"{car_model}: Car model has unexpected ECUs: {ecu_strings}"

  def test_canfd_blinker_signal_selection(self):
    assert CarState.get_canfd_blinker_sig_names(CAR.KIA_SPORTAGE_HEV_2026, True) == ("LEFT_LAMP_ALT", "RIGHT_LAMP_ALT")
    assert CarState.get_canfd_blinker_sig_names(CAR.HYUNDAI_KONA_EV_2ND_GEN, False) == ("LEFT_LAMP_ALT", "RIGHT_LAMP_ALT")
    assert CarState.get_canfd_blinker_sig_names(CAR.KIA_EV6, False) == ("LEFT_LAMP", "RIGHT_LAMP")

  @pytest.mark.parametrize("alpha_long", [False, True])
  def test_ioniq_6_left_paddle_button_event(self, alpha_long):
    toggles = get_test_toggles()
    fingerprint = gen_empty_fingerprint()
    CP = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, fingerprint, [], alpha_long, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_IONIQ_6, fingerprint, [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP).ECAN

    def update(left_paddle: int, frame: int):
      msg = packer.make_can_msg("CRUISE_BUTTONS", can_bus, {
        "SET_ME_1": 1,
        "CRUISE_BUTTONS": 0,
        "ADAPTIVE_CRUISE_MAIN_BTN": 0,
        "LDA_BTN": 0,
        "LEFT_PADDLE": left_paddle,
        "RIGHT_PADDLE": 0,
      })
      can_parsers[Bus.pt].update([(frame, [msg])])
      return car_state.update(can_parsers, toggles)[0]

    update(0, 1)
    ret = update(1, 2)
    assert any(be.type == ButtonType.altButton2 and be.pressed for be in ret.buttonEvents)

    ret = update(0, 3)
    assert any(be.type == ButtonType.altButton2 and not be.pressed for be in ret.buttonEvents)

  def test_forte_non_scc_clu13_lkas_button_event(self):
    toggles = get_test_toggles()
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x50C] = 8
    CP = CarInterface.get_params(CAR.KIA_FORTE_2021_NON_SCC, fingerprint, [], False, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.KIA_FORTE_2021_NON_SCC, fingerprint, [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])

    def update(lkas_button: int, frame: int):
      msg = packer.make_can_msg("CLU13", 0, {
        "CF_Clu_LdwsLkasSW": lkas_button,
      })
      can_parsers[Bus.pt].update([(frame, [msg])])
      return car_state.update(can_parsers, toggles)[0]

    update(0, 1)
    ret = update(1, 2)
    assert any(be.type == ButtonType.lkas and be.pressed for be in ret.buttonEvents)

    ret = update(0, 3)
    assert any(be.type == ButtonType.lkas and not be.pressed for be in ret.buttonEvents)

  def test_elantra_lkas_button_event_is_not_masked_by_live_clu13(self):
    toggles = get_test_toggles()
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x391] = 8
    fingerprint[0][0x50C] = 8
    CP = CarInterface.get_params(CAR.HYUNDAI_ELANTRA_2021, fingerprint, [], False, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_ELANTRA_2021, fingerprint, [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])

    def update(bcm_lkas_button: int, frame: int):
      msgs = [
        packer.make_can_msg("CLU13", 0, {
          "CF_Clu_LdwsLkasSW": 0,
        }),
        packer.make_can_msg("BCM_PO_11", 0, {
          "LDA_BTN": bcm_lkas_button,
        }),
      ]
      can_parsers[Bus.pt].update([(frame, msgs)])
      return car_state.update(can_parsers, toggles)[0]

    update(0, 1)
    ret = update(1, 2)
    assert any(be.type == ButtonType.lkas and be.pressed for be in ret.buttonEvents)

    ret = update(0, 3)
    assert any(be.type == ButtonType.lkas and not be.pressed for be in ret.buttonEvents)

  def test_elantra_hev_lkas_button_keeps_a_short_parser_cycle_edge(self):
    car_state = CarState.__new__(CarState)
    car_state.CP = SimpleNamespace(carFingerprint=CAR.HYUNDAI_ELANTRA_HEV_2024)
    car_state.lda_button = 0
    parser_cycle = SimpleNamespace(vl_all={
      "CLU13": {"CF_Clu_LdwsLkasSW": [0]},
      "BCM_PO_11": {"LDA_BTN": [1, 0]},
    })

    events = car_state.create_lkas_button_events(parser_cycle, 0)

    assert any(be.type == ButtonType.lkas and be.pressed for be in events)
    assert car_state.lda_button == 1

  def test_sonata_hybrid_uses_main_bus_lkas_parser(self):
    toggles = get_test_toggles()
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x391] = 8
    fingerprint[1][0x50C] = 8
    CP = CarInterface.get_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], False, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)

    assert Bus.alt not in can_parsers

  def test_sonata_hybrid_bcm_lkas_button_event(self):
    toggles = get_test_toggles()
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x391] = 8
    fingerprint[1][0x50C] = 8
    CP = CarInterface.get_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], False, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])

    def update(lkas_button: int, frame: int):
      msg = packer.make_can_msg("BCM_PO_11", 0, {
        "LDA_BTN": lkas_button,
      })
      can_parsers[Bus.pt].update([(frame, [msg])])
      return car_state.update(can_parsers, toggles)[0]

    update(0, 1)
    ret = update(1, 2)
    assert any(be.type == ButtonType.lkas and be.pressed for be in ret.buttonEvents)

    ret = update(0, 3)
    assert any(be.type == ButtonType.lkas and not be.pressed for be in ret.buttonEvents)

  def test_sonata_hybrid_prefers_bcm_lkas_button_over_dead_main_bus_clu13(self):
    toggles = get_test_toggles()
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x391] = 8
    fingerprint[1][0x50C] = 8
    CP = CarInterface.get_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], False, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])

    def update(clu13_lkas_button: int, bcm_lkas_button: int, frame: int):
      msgs = [
        packer.make_can_msg("CLU13", 0, {
          "CF_Clu_LdwsLkasSW": clu13_lkas_button,
        }),
        packer.make_can_msg("BCM_PO_11", 0, {
          "LDA_BTN": bcm_lkas_button,
        }),
      ]
      can_parsers[Bus.pt].update([(frame, msgs)])
      return car_state.update(can_parsers, toggles)[0]

    update(0, 0, 1)
    ret = update(0, 1, 2)
    assert any(be.type == ButtonType.lkas and be.pressed for be in ret.buttonEvents)

    ret = update(0, 0, 3)
    assert any(be.type == ButtonType.lkas and not be.pressed for be in ret.buttonEvents)

  def test_sonata_hybrid_falls_back_to_main_bus_clu13_lkas_button_when_bcm_stays_dead(self):
    toggles = get_test_toggles()
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x391] = 8
    fingerprint[1][0x50C] = 8
    CP = CarInterface.get_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], False, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])

    def update(clu13_lkas_button: int, bcm_lkas_button: int, frame: int):
      msgs = [
        packer.make_can_msg("CLU13", 0, {
          "CF_Clu_LdwsLkasSW": clu13_lkas_button,
        }),
        packer.make_can_msg("BCM_PO_11", 0, {
          "LDA_BTN": bcm_lkas_button,
        }),
      ]
      can_parsers[Bus.pt].update([(frame, msgs)])
      return car_state.update(can_parsers, toggles)[0]

    update(0, 0, 1)
    ret = update(1, 0, 2)
    assert any(be.type == ButtonType.lkas and be.pressed for be in ret.buttonEvents)

    ret = update(0, 0, 3)
    assert any(be.type == ButtonType.lkas and not be.pressed for be in ret.buttonEvents)

  def test_sonata_hybrid_falls_back_to_main_bus_clu13_swl_stat_lkas_button_when_other_sources_are_dead(self):
    toggles = get_test_toggles()
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x391] = 8
    fingerprint[1][0x50C] = 8
    CP = CarInterface.get_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], False, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])

    def update(swl_stat: int, frame: int):
      msgs = [
        packer.make_can_msg("CLU13", 0, {
          "CF_Clu_LdwsLkasSW": 0,
          "CF_Clu_SWL_Stat": swl_stat,
        }),
        packer.make_can_msg("BCM_PO_11", 0, {
          "LDA_BTN": 0,
        }),
      ]
      can_parsers[Bus.pt].update([(frame, msgs)])
      return car_state.update(can_parsers, toggles)[0]

    update(0, 1)
    ret = update(4, 2)
    assert any(be.type == ButtonType.lkas and be.pressed for be in ret.buttonEvents)

    ret = update(0, 3)
    assert any(be.type == ButtonType.lkas and not be.pressed for be in ret.buttonEvents)

  def test_sonata_hybrid_ignores_noisy_alt_bus_clu13_lkas_button(self):
    toggles = get_test_toggles()
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x391] = 8
    fingerprint[1][0x50C] = 8
    CP = CarInterface.get_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], False, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_SONATA_HYBRID, fingerprint, [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)

    assert Bus.alt not in can_parsers

  def test_sonata_uses_main_bus_bcm_lkas_button_event(self):
    toggles = get_test_toggles()
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x391] = 8
    fingerprint[1][0x50C] = 8
    CP = CarInterface.get_params(CAR.HYUNDAI_SONATA, fingerprint, [], False, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_SONATA, fingerprint, [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])

    assert Bus.alt not in can_parsers

    def update(lkas_button: int, frame: int):
      msgs = [
        packer.make_can_msg("CLU13", 0, {
          "CF_Clu_LdwsLkasSW": 0,
          "CF_Clu_SWL_Stat": 4,
        }),
        packer.make_can_msg("BCM_PO_11", 0, {
          "LDA_BTN": lkas_button,
        }),
      ]
      can_parsers[Bus.pt].update([(frame, msgs)])
      return car_state.update(can_parsers, toggles)[0]

    update(0, 1)
    ret = update(1, 2)
    assert any(be.type == ButtonType.lkas and be.pressed for be in ret.buttonEvents)

    ret = update(0, 3)
    assert any(be.type == ButtonType.lkas and not be.pressed for be in ret.buttonEvents)

  def test_genesis_g90_does_not_use_alt_bus_lkas_parser(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.GENESIS_G90, gen_empty_fingerprint(), [], False, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.GENESIS_G90, gen_empty_fingerprint(), [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)

    assert Bus.alt not in can_parsers

  def test_ioniq_6_longitudinal_params_match_canfd_tune(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, gen_empty_fingerprint(), [], True, False, False, toggles)

    assert CP.vEgoStopping == pytest.approx(0.3)
    assert CP.vEgoStarting == pytest.approx(0.1)
    assert CP.stoppingDecelRate == pytest.approx(0.4)
    assert CP.longitudinalActuatorDelay == pytest.approx(0.6)
    assert CP.startingState

  def test_ev9_longitudinal_params_match_observed_response(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.KIA_EV9, gen_empty_fingerprint(), [], True, False, False, toggles)

    assert CP.startAccel == pytest.approx(0.2)
    assert CP.vEgoStarting == pytest.approx(0.5)
    assert CP.longitudinalActuatorDelay == pytest.approx(0.3)
    assert KIA_EV9_ACCEL_MAX == pytest.approx(2.2)
    assert CarInterface.get_pid_accel_limits(CP, 0.0, 0.0)[1] == pytest.approx(KIA_EV9_ACCEL_MAX)

    ioniq_6_cp = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, gen_empty_fingerprint(), [], True, False, False, toggles)
    assert CarInterface.get_pid_accel_limits(ioniq_6_cp, 0.0, 0.0)[1] == pytest.approx(CarControllerParams.ACCEL_MAX)

  def test_ev9_uses_softer_direct_brake_handoff_than_ioniq_6(self):
    ev9_cp = SimpleNamespace(carFingerprint=CAR.KIA_EV9)
    ioniq_6_cp = SimpleNamespace(carFingerprint=CAR.HYUNDAI_IONIQ_6)

    assert get_canfd_scc_decel_step(ev9_cp) == pytest.approx(0.20)
    assert get_canfd_scc_decel_step(ioniq_6_cp) == pytest.approx(0.36)

  def test_ev9_keeps_low_speed_stop_brake_cap(self):
    assert not should_track_stop_accel_directly_for_car(
      CAR.KIA_EV9, stopping=True, v_ego=1.8, accel_cmd=-3.5, actual_accel=-0.4,
    )
    assert should_track_stop_accel_directly_for_car(
      CAR.HYUNDAI_IONIQ_5_PE, stopping=True, v_ego=1.8, accel_cmd=-3.5, actual_accel=-0.4,
    )

  def test_ev9_longitudinal_decel_jerk_is_bounded(self):
    state = Ioniq6LongitudinalTuningState(actual_accel=-1.0, accel_last=-1.0)
    state = update_ioniq_6_longitudinal_tuning(
      state, accel_cmd=-3.0, v_ego=20.0, a_ego=-3.0,
      long_control_state=LongCtrlState.pid, long_active=True, ev9=True,
    )
    assert state.jerk_lower == pytest.approx(2.0)
    assert state.actual_accel == pytest.approx(-1.1)

  def test_ioniq_5_pe_longitudinal_params_match_observed_response(self):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.HYUNDAI_IONIQ_5_PE, gen_empty_fingerprint(), [], True, False, False, toggles)
    assert CP.longitudinalActuatorDelay == pytest.approx(0.35)
    assert CP.vEgoStarting == pytest.approx(0.4)

  def test_ioniq_6_longitudinal_tuning_helper_matches_dynamic_profile(self):
    state = Ioniq6LongitudinalTuningState()

    state = update_ioniq_6_longitudinal_tuning(state, accel_cmd=1.5, v_ego=10.0, a_ego=0.0,
                                               long_control_state=LongCtrlState.pid, long_active=True)
    assert state.desired_accel == pytest.approx(1.5)
    assert state.jerk_upper == pytest.approx(3.2)
    assert state.jerk_lower == pytest.approx(0.6)
    assert state.actual_accel == pytest.approx(0.16)

    state = update_ioniq_6_longitudinal_tuning(state, accel_cmd=1.0, v_ego=10.0, a_ego=0.0,
                                               long_control_state=LongCtrlState.stopping, long_active=True)
    assert state.stopping
    assert state.desired_accel == pytest.approx(0.0)
    actual_accel_after_stop = state.actual_accel

    state = update_ioniq_6_longitudinal_tuning(state, accel_cmd=1.0, v_ego=10.0, a_ego=0.0,
                                               long_control_state=LongCtrlState.stopping, long_active=True)
    assert state.actual_accel < actual_accel_after_stop

    state = update_ioniq_6_longitudinal_tuning(state, accel_cmd=1.0, v_ego=10.0, a_ego=0.0,
                                               long_control_state=LongCtrlState.pid, long_active=False)
    assert state.desired_accel == pytest.approx(0.0)
    assert state.actual_accel == pytest.approx(0.0)
    assert state.jerk_upper == pytest.approx(0.0)
    assert state.jerk_lower == pytest.approx(0.0)

  def test_ioniq_6_longitudinal_tuning_helper_holds_launch_through_starting_handoff(self):
    state = Ioniq6LongitudinalTuningState()

    state = update_ioniq_6_longitudinal_tuning(state, accel_cmd=1.0, v_ego=0.0, a_ego=0.0,
                                               long_control_state=LongCtrlState.starting, long_active=True)
    assert state.launch_active
    assert state.actual_accel == pytest.approx(0.288)
    assert state.jerk_upper == pytest.approx(5.76)
    assert state.jerk_lower == pytest.approx(1.0)

    state = update_ioniq_6_longitudinal_tuning(state, accel_cmd=0.3, v_ego=0.25, a_ego=1.2,
                                               long_control_state=LongCtrlState.pid, long_active=True)
    assert state.launch_active
    assert state.desired_accel > 0.3
    assert state.actual_accel > 0.288

  def test_ioniq_6_longitudinal_tuning_helper_softens_stop_release_handoff(self):
    state = Ioniq6LongitudinalTuningState(actual_accel=-0.12, accel_last=-0.12,
                                          stopping=True, stopping_count=25,
                                          long_control_state_last=LongCtrlState.stopping)

    state = update_ioniq_6_longitudinal_tuning(state, accel_cmd=1.0, v_ego=0.0, a_ego=0.0,
                                               long_control_state=LongCtrlState.starting, long_active=True)
    assert state.actual_accel == pytest.approx(0.096)

    state = update_ioniq_6_longitudinal_tuning(state, accel_cmd=1.0, v_ego=0.0, a_ego=0.0,
                                               long_control_state=LongCtrlState.starting, long_active=True)
    assert state.actual_accel == pytest.approx(0.312)

  def test_ioniq_6_longitudinal_tuning_helper_softens_final_stop_hold(self):
    state = Ioniq6LongitudinalTuningState(actual_accel=-0.12, accel_last=-0.12,
                                          stopping=True, stopping_count=25,
                                          long_control_state_last=LongCtrlState.stopping)

    state = update_ioniq_6_longitudinal_tuning(state, accel_cmd=-1.8, v_ego=0.0, a_ego=0.0,
                                               long_control_state=LongCtrlState.stopping, long_active=True)
    assert state.desired_accel == pytest.approx(-0.15)
    assert state.jerk_upper == pytest.approx(0.42)
    assert state.actual_accel == pytest.approx(-0.15)

  def test_ioniq_6_longitudinal_tuning_helper_caps_final_low_speed_stop_brake(self):
    state = Ioniq6LongitudinalTuningState(actual_accel=-2.82, accel_last=-2.82,
                                          long_control_state_last=LongCtrlState.pid)

    state = update_ioniq_6_longitudinal_tuning(state, accel_cmd=-2.82, v_ego=1.8, a_ego=-2.4,
                                               long_control_state=LongCtrlState.stopping, long_active=True)
    assert state.stopping
    assert state.desired_accel == pytest.approx(-1.0575)

    for _ in range(10):
      state = update_ioniq_6_longitudinal_tuning(state, accel_cmd=-2.82, v_ego=1.8, a_ego=-2.4,
                                                 long_control_state=LongCtrlState.stopping, long_active=True)
    assert state.actual_accel == pytest.approx(-2.49)

  def test_ioniq_6_longitudinal_tuning_helper_keeps_full_stop_authority_above_final_band(self):
    state = Ioniq6LongitudinalTuningState(actual_accel=-1.8, accel_last=-1.8,
                                          long_control_state_last=LongCtrlState.pid)

    state = update_ioniq_6_longitudinal_tuning(state, accel_cmd=-2.82, v_ego=3.8, a_ego=-1.8,
                                               long_control_state=LongCtrlState.stopping, long_active=True)
    assert state.stopping
    assert state.desired_accel == pytest.approx(-2.82)
    assert state.actual_accel < -1.8

  def test_kia_ev6_gt_line_longitudinal_tuning_helper_delays_final_stop_cap(self):
    state = Ioniq6LongitudinalTuningState(actual_accel=-2.82, accel_last=-2.82,
                                          long_control_state_last=LongCtrlState.pid)

    state = update_ioniq_6_longitudinal_tuning(state, accel_cmd=-2.82, v_ego=1.8, a_ego=-2.4,
                                               long_control_state=LongCtrlState.stopping, long_active=True,
                                               ev6_gt_line=True)
    assert state.stopping
    assert state.desired_accel == pytest.approx(-2.82)
    assert state.actual_accel == pytest.approx(-2.82)

  def test_kia_ev6_gt_line_prefers_direct_stop_tracking_above_final_band(self):
    assert should_use_ev6_gt_line_stop_direct_tracking(True, True, 1.8, -2.05, -1.29)
    assert not should_use_ev6_gt_line_stop_direct_tracking(True, True, 1.0, -2.05, -1.29)
    assert not should_use_ev6_gt_line_stop_direct_tracking(True, False, 1.8, -2.05, -1.29)
    assert not should_use_ev6_gt_line_stop_direct_tracking(False, True, 1.8, -2.05, -1.29)
    assert not should_use_ev6_gt_line_stop_direct_tracking(True, True, 1.8, -1.0, -1.29)

  @pytest.mark.parametrize("candidate", (CAR.KIA_EV9, CAR.HYUNDAI_IONIQ_5_PE))
  def test_ccnc_angle_long_carcontroller_initializes_ev9_tuning_state(self, candidate):
    CP = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], True, False, False, None)
    controller = CarController(DBC[CP.carFingerprint], CP)
    assert controller._ev9_long_tuning == EV9LongitudinalTuningState()
    assert isinstance(controller._left_blindspot_warning, BlindspotWarningState)
    assert isinstance(controller._right_blindspot_warning, BlindspotWarningState)

  def test_ev9_longitudinal_tuning_matches_stock_stop_hold_release_timing(self):
    state = update_ev9_longitudinal_tuning(EV9LongitudinalTuningState(), True, True, 1.0)
    assert not state.stop_request

    state = update_ev9_longitudinal_tuning(state, True, True, 0.4)
    assert state.stop_request
    assert not state.cruise_standstill

    for _ in range(178):
      state = update_ev9_longitudinal_tuning(state, True, True, 0.0)
    assert state.cruise_standstill

    for _ in range(6):
      state = update_ev9_longitudinal_tuning(state, True, False, 0.0)
      assert state.stop_request
      assert not state.cruise_standstill
    assert update_ev9_longitudinal_tuning(state, True, False, 0.0) == EV9LongitudinalTuningState()

  def test_ev9_blindspot_warning_matches_stock_envelope(self):
    state = BlindspotWarningState()
    outputs = [update_blindspot_warning(state, True, True) for _ in range(40)]

    assert [output.sound_active for output in outputs[:36]] == [True] * 36
    assert not any(output.sound_active for output in outputs[36:])
    assert [output.mirror_lamp_active for output in outputs[:20]] == [True] * 16 + [False] * 4
    assert [output.mirror_lamp_active for output in outputs[20:]] == [True] * 16 + [False] * 4

    assert not update_blindspot_warning(state, False, True).sound_active
    assert update_blindspot_warning(state, True, True).sound_active is False
    update_blindspot_warning(state, False, False)
    assert update_blindspot_warning(state, True, True).sound_active

  def test_ev9_longitudinal_tuning_resets_accel_before_stop_release(self):
    accel_state = Ioniq6LongitudinalTuningState()
    for _ in range(4):
      accel_state = update_ioniq_6_longitudinal_tuning(
        accel_state, accel_cmd=0.2, v_ego=0.0, a_ego=0.0,
        long_control_state=LongCtrlState.starting, long_active=True,
        low_speed_stop_brake_cap=True,
      )
    assert accel_state.actual_accel == pytest.approx(0.75)

    accel_state = reset_egmp_longitudinal_tuning(accel_state)
    assert accel_state.actual_accel == 0.0
    assert not accel_state.launch_active

  def test_genesis_g90_longitudinal_tuning_softens_final_stop_hold(self):
    state = GenesisG90LongitudinalTuningState()

    state = update_genesis_g90_longitudinal_tuning(state, accel_cmd=-2.0, v_ego=0.02,
                                                   long_control_state=LongCtrlState.stopping, long_active=True)
    assert state.actual_accel == pytest.approx(-0.10)
    assert not state.release_active

  def test_genesis_g90_longitudinal_tuning_gradually_unwinds_into_stop_hold(self):
    state = GenesisG90LongitudinalTuningState(actual_accel=-2.0)

    state = update_genesis_g90_longitudinal_tuning(state, accel_cmd=-2.0, v_ego=0.5,
                                                   long_control_state=LongCtrlState.stopping, long_active=True)
    assert state.actual_accel == pytest.approx(-1.96)

    state = update_genesis_g90_longitudinal_tuning(state, accel_cmd=-2.0, v_ego=0.3,
                                                   long_control_state=LongCtrlState.stopping, long_active=True)
    assert state.actual_accel == pytest.approx(-1.9)

  def test_genesis_g90_longitudinal_tuning_caps_low_speed_stop_brake(self):
    state = GenesisG90LongitudinalTuningState(actual_accel=-1.0)

    state = update_genesis_g90_longitudinal_tuning(state, accel_cmd=-0.4, v_ego=0.3,
                                                   long_control_state=LongCtrlState.stopping, long_active=True)
    assert state.actual_accel == pytest.approx(-0.94)

    state = update_genesis_g90_longitudinal_tuning(state, accel_cmd=-0.4, v_ego=0.3,
                                                   long_control_state=LongCtrlState.stopping, long_active=True)
    assert state.actual_accel == pytest.approx(-0.88)

  def test_genesis_g90_longitudinal_tuning_ramps_out_of_stop_hold(self):
    state = GenesisG90LongitudinalTuningState(actual_accel=-0.12, long_control_state_last=LongCtrlState.stopping)

    state = update_genesis_g90_longitudinal_tuning(state, accel_cmd=0.5, v_ego=0.02,
                                                   long_control_state=LongCtrlState.pid, long_active=True)
    assert state.release_active
    assert state.actual_accel == pytest.approx(-0.06866666666666665)

    state = update_genesis_g90_longitudinal_tuning(state, accel_cmd=0.5, v_ego=0.2,
                                                   long_control_state=LongCtrlState.pid, long_active=True)
    assert state.actual_accel == pytest.approx(-0.005333333333333315)

  def test_canfd_acc_control_uses_direct_accel(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV6
    CP.flags = int(HyundaiFlags.CANFD)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("SCC_CONTROL", 0)], can_bus.ECAN)

    msg = hyundaicanfd.create_acc_control(packer, can_bus, enabled=True, accel_last=1.5, accel=-1.2, stopping=False,
                                          gas_override=False, set_speed=42, hud_control=SimpleNamespace(leadDistanceBars=3),
                                          main_mode_acc=0, jerk_lower=5.0, jerk_upper=1.0, direct_accel=True)
    parser.update([(1, [msg])])

    assert parser.can_valid
    assert parser.vl["SCC_CONTROL"]["MainMode_ACC"] == 0
    assert parser.vl["SCC_CONTROL"]["aReqRaw"] == pytest.approx(-1.2)
    assert parser.vl["SCC_CONTROL"]["aReqValue"] == pytest.approx(-1.2)
    assert parser.vl["SCC_CONTROL"]["JerkLowerLimit"] == pytest.approx(5.0)
    assert parser.vl["SCC_CONTROL"]["JerkUpperLimit"] == pytest.approx(1.0)

  def test_canfd_acc_control_accepts_lead_object_override(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV6
    CP.flags = int(HyundaiFlags.CANFD)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("SCC_CONTROL", 0)], can_bus.ECAN)

    msg = hyundaicanfd.create_acc_control(packer, can_bus, enabled=True, accel_last=0.0, accel=0.1, stopping=False,
                                          gas_override=False, set_speed=42, hud_control=SimpleNamespace(leadDistanceBars=3),
                                          direct_accel=True, lead_distance=27.5, lead_rel_speed=-1.2, lead_visible=True)
    parser.update([(1, [msg])])

    assert parser.can_valid
    assert parser.vl["SCC_CONTROL"]["ACC_ObjDist"] == pytest.approx(27.5)
    assert parser.vl["SCC_CONTROL"]["ACC_ObjRelSpd"] == pytest.approx(-1.2)
    assert parser.vl["SCC_CONTROL"]["ObjValid"] == 0
    assert parser.vl["SCC_CONTROL"]["OBJ_STATUS"] == 2

  def test_canfd_acc_control_hides_lead_object_when_not_visible(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV6
    CP.flags = int(HyundaiFlags.CANFD)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("SCC_CONTROL", 0)], can_bus.ECAN)

    msg = hyundaicanfd.create_acc_control(packer, can_bus, enabled=True, accel_last=0.0, accel=0.1, stopping=False,
                                          gas_override=False, set_speed=42, hud_control=SimpleNamespace(leadDistanceBars=3),
                                          direct_accel=True, lead_distance=27.5, lead_rel_speed=-1.2, lead_visible=False)
    parser.update([(1, [msg])])

    assert parser.can_valid
    assert parser.vl["SCC_CONTROL"]["ACC_ObjDist"] == pytest.approx(0.0)
    assert parser.vl["SCC_CONTROL"]["ACC_ObjRelSpd"] == pytest.approx(0.0)
    assert parser.vl["SCC_CONTROL"]["ObjValid"] == 1
    assert parser.vl["SCC_CONTROL"]["OBJ_STATUS"] == 0

  def test_canfd_acc_control_preserves_stock_ccnc_object_fields(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.HYUNDAI_SONATA_2024
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CCNC)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("SCC_CONTROL", 0)], can_bus.ECAN)

    msg = hyundaicanfd.create_acc_control(packer, can_bus, enabled=True, accel_last=0.0, accel=0.1, stopping=False,
                                          gas_override=False, set_speed=42, hud_control=SimpleNamespace(leadDistanceBars=3),
                                          direct_accel=True, lead_distance=27.5, lead_rel_speed=-1.2, lead_visible=True,
                                          cruise_info={"ACC_ObjDist": 13.5, "ACC_ObjRelSpd": -0.4})
    parser.update([(1, [msg])])

    assert parser.can_valid
    assert parser.vl["SCC_CONTROL"]["ACC_ObjDist"] == pytest.approx(13.5)
    assert parser.vl["SCC_CONTROL"]["ACC_ObjRelSpd"] == pytest.approx(-0.4)

  def test_ccnc_hud_helper_clears_faults_and_generates_ui_fields(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.HYUNDAI_SONATA_2024
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CCNC)
    CP.openpilotLongitudinalControl = True

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("CCNC_0x161", 0), ("CCNC_0x162", 0)], can_bus.ECAN)

    msg_161 = {
      "ALERTS_2": 5,
      "ALERTS_3": 17,
      "ALERTS_5": 5,
      "SOUNDS_3": 5,
      "SOUNDS_4": 2,
      "LFA_ICON": 3,
    }
    msg_162 = {fault: 1 for fault in ("FAULT_LSS", "FAULT_HDA", "FAULT_DAS", "FAULT_LFA", "FAULT_DAW", "FAULT_ESS")}
    msg_162["VIBRATE"] = 0
    msg_1b5 = {
      "Info_LftLnPosVal": 1.4,
      "Info_RtLnPosVal": 1.9,
      "Info_LftLnQualSta": 3,
      "Info_RtLnQualSta": 3,
      "Longitudinal_Distance": 42.0,
    }
    hud = SimpleNamespace(leftLaneVisible=True, rightLaneVisible=True, leftLaneDepart=True, rightLaneDepart=False,
                          leadDistanceBars=3, leadVisible=True)
    out = SimpleNamespace(steeringAngleDeg=22.5, vEgo=15.0, leftBlindspot=True, rightBlindspot=False,
                          vCruiseCluster=88.0)

    msgs = hyundaicanfd.create_ccnc(packer, can_bus, openpilot_longitudinal=True, enabled=True, hud=hud,
                                    left_blinker=False, right_blinker=False, msg_161=msg_161, msg_162=msg_162,
                                    msg_1b5=msg_1b5, is_metric=False, out=out, main_cruise_enabled=True, lfa_icon=2)
    parser.update([(1, msgs)])

    assert parser.can_valid
    assert parser.vl["CCNC_0x161"]["DAW_ICON"] == 0
    assert parser.vl["CCNC_0x161"]["LKA_ICON"] == 0
    assert parser.vl["CCNC_0x161"]["LFA_ICON"] == 2
    assert parser.vl["CCNC_0x161"]["CENTERLINE"] == 1
    assert parser.vl["CCNC_0x161"]["LANELINE_CURVATURE"] == 20
    assert parser.vl["CCNC_0x161"]["LANELINE_LEFT"] == 4
    assert parser.vl["CCNC_0x161"]["LANELINE_RIGHT"] == 2
    assert parser.vl["CCNC_0x161"]["LCA_LEFT_ICON"] == 1
    assert parser.vl["CCNC_0x161"]["LCA_RIGHT_ICON"] == 4
    assert parser.vl["CCNC_0x161"]["ALERTS_2"] == 0
    assert parser.vl["CCNC_0x161"]["ALERTS_3"] == 0
    assert parser.vl["CCNC_0x161"]["ALERTS_5"] == 0
    assert parser.vl["CCNC_0x161"]["SOUNDS_3"] == 0
    assert parser.vl["CCNC_0x161"]["SOUNDS_4"] == 0
    assert parser.vl["CCNC_0x161"]["SETSPEED"] == 3
    assert parser.vl["CCNC_0x161"]["SETSPEED_HUD"] == 2
    assert parser.vl["CCNC_0x161"]["SETSPEED_SPEED"] == 55
    assert parser.vl["CCNC_0x161"]["DISTANCE"] == 3
    assert parser.vl["CCNC_0x161"]["DISTANCE_LEAD"] == 2
    assert all(parser.vl["CCNC_0x162"][fault] == 0 for fault in ("FAULT_LSS", "FAULT_HDA", "FAULT_DAS", "FAULT_LFA", "FAULT_DAW", "FAULT_ESS"))
    assert parser.vl["CCNC_0x162"]["VIBRATE"] == 1
    assert parser.vl["CCNC_0x162"]["LEAD"] == 2
    assert parser.vl["CCNC_0x162"]["LEAD_DISTANCE"] == pytest.approx(42.0)

  def test_ccnc_hud_helper_generates_lane_position_animation_and_lca_arrows(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.HYUNDAI_SONATA_2024
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CCNC)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("CCNC_0x161", 0), ("CCNC_0x162", 0)], can_bus.ECAN)
    hud = SimpleNamespace(leftLaneVisible=True, rightLaneVisible=True, leftLaneDepart=False, rightLaneDepart=False,
                          leadDistanceBars=1, leadVisible=False)
    out = SimpleNamespace(steeringAngleDeg=0.0, vEgo=15.0, leftBlindspot=False, rightBlindspot=False,
                          vCruiseCluster=55.0)
    msg_1b5 = {
      "Info_LftLnPosVal": 1.4,
      "Info_RtLnPosVal": 1.9,
      "Info_LftLnQualSta": 3,
      "Info_RtLnQualSta": 3,
      "Longitudinal_Distance": 0.0,
    }

    msgs = hyundaicanfd.create_ccnc(packer, can_bus, openpilot_longitudinal=False, enabled=True, hud=hud,
                                    left_blinker=True, right_blinker=False,
                                    msg_161={"ALERTS_2": 0, "ALERTS_3": 0, "ALERTS_5": 0, "SOUNDS_4": 0, "LFA_ICON": 2},
                                    msg_162={fault: 0 for fault in ("FAULT_LSS", "FAULT_HDA", "FAULT_DAS", "FAULT_LFA", "FAULT_DAW", "FAULT_ESS")},
                                    msg_1b5=msg_1b5, is_metric=True, out=out, main_cruise_enabled=True, lfa_icon=2)
    parser.update([(1, msgs)])

    assert parser.can_valid
    assert parser.vl["CCNC_0x161"]["LANELINE_CURVATURE"] == 15
    assert parser.vl["CCNC_0x161"]["LANELINE_LEFT"] == 6
    assert parser.vl["CCNC_0x161"]["LANELINE_RIGHT"] == 6
    assert parser.vl["CCNC_0x161"]["LCA_LEFT_ICON"] == 2
    assert parser.vl["CCNC_0x161"]["LCA_LEFT_ARROW"] == 2
    assert parser.vl["CCNC_0x161"]["LCA_RIGHT_ARROW"] == 0
    assert parser.vl["CCNC_0x161"]["LANELINE_LEFT_POSITION"] == 12
    assert parser.vl["CCNC_0x161"]["LANELINE_RIGHT_POSITION"] == 18

  def test_canfd_scc_lead_state_prefers_openpilot_lead_distance(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV6
    CP.flags = int(HyundaiFlags.CANFD)

    controller = CarController(DBC[CP.carFingerprint], CP)
    cc = SimpleNamespace(hudControl=SimpleNamespace(leadVisible=True, leadDistanceBars=2))
    cs = SimpleNamespace(
      openpilot_lead_visible=True,
      openpilot_lead_distance=37.5,
      openpilot_lead_rel_speed=-1.3,
      stock_camera_lead_ts=0,
      stock_camera_lead_visible=False,
      stock_camera_lead_distance=0.0,
      stock_camera_lead_rel_speed=0.0,
    )

    lead_visible, lead_distance, lead_rel_speed = controller._get_canfd_scc_lead_state(cc, cs, now_nanos=1_000_000_000)

    assert lead_visible
    assert lead_distance == pytest.approx(37.5)
    assert lead_rel_speed == pytest.approx(-1.3)

  def test_canfd_scc_lead_state_falls_back_to_hud_lead_when_no_distance_available(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV6
    CP.flags = int(HyundaiFlags.CANFD)

    controller = CarController(DBC[CP.carFingerprint], CP)
    cc = SimpleNamespace(hudControl=SimpleNamespace(leadVisible=True, leadDistanceBars=2))
    cs = SimpleNamespace(
      openpilot_lead_visible=True,
      openpilot_lead_distance=0.0,
      openpilot_lead_rel_speed=0.0,
      stock_camera_lead_ts=0,
      stock_camera_lead_visible=False,
      stock_camera_lead_distance=0.0,
      stock_camera_lead_rel_speed=0.0,
    )

    lead_visible, lead_distance, lead_rel_speed = controller._get_canfd_scc_lead_state(cc, cs, now_nanos=1_000_000_000)

    assert lead_visible
    assert lead_distance == pytest.approx(20.0)
    assert lead_rel_speed == pytest.approx(0.0)

  def test_ev9_angle_status_stays_active_when_gain_is_zero(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV9
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_ANGLE_STEERING |
                   HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)
    CP.openpilotLongitudinalControl = False

    controller = CarController(DBC[CP.carFingerprint], CP)
    controller.frame = 1
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS_ALT", 0)], can_bus.ACAN)
    stock_lkas = {
      "CHECKSUM": 1234,
      "COUNTER": 42,
      "LKA_MODE": 2,
      "LKA_AVAILABLE": 3,
      "LKA_WARNING": 1,
      "LKA_ICON": 1,
      "FCA_SYSWARN": 1,
      "TORQUE_REQUEST": 17,
      "STEER_REQ": 1,
      "LFA_BUTTON": 1,
      "LKA_ASSIST": 1,
      "STEER_MODE": 5,
      "NEW_SIGNAL_2": 0,
      "LKAS_ANGLE_ACTIVE": 1,
      "HAS_LANE_SAFETY": 1,
      "ADAS_StrAnglReqVal": 12.3,
      "ADAS_ACIAnglTqRedcGainVal": 0.42,
      "DAMP_FACTOR": 0,
    }
    cc = SimpleNamespace(enabled=True, latActive=True, actuators=SimpleNamespace(longControlState=LongCtrlState.off),
                         leftBlinker=False, rightBlinker=False, hudControl=SimpleNamespace())
    cs = SimpleNamespace(stock_lfa_msg=None, stock_lkas_msg=stock_lkas,
                         out=SimpleNamespace(steeringAngleDeg=0.0, gearShifter=structs.CarState.GearShifter.drive))

    msgs = controller.create_canfd_msgs(0, False, 0.0, 8.5, 0.0, 0.0, False, cc.hudControl, cs, cc,
                                        get_test_toggles(), lka_icon=2, lfa_icon=2)
    lkas_msgs = [msg for msg in msgs if msg[0] == 0x110]
    assert len(lkas_msgs) == 1

    parser.update([(1, lkas_msgs)])

    assert parser.can_valid
    assert parser.vl["LKAS_ALT"]["LKAS_ANGLE_ACTIVE"] == 2
    assert parser.vl["LKAS_ALT"]["ADAS_ACIAnglTqRedcGainVal"] == pytest.approx(0.0)
    assert parser.vl["LKAS_ALT"]["ADAS_StrAnglReqVal"] == pytest.approx(8.5)

  def test_gv70_electrified_uses_generic_lkas_status_payload(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_LKA_STEERING)
    CP.openpilotLongitudinalControl = False

    controller = CarController(DBC[CP.carFingerprint], CP)
    controller.frame = 1
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS", 0)], can_bus.ACAN)
    stock_lkas = {
      "CHECKSUM": 1234,
      "COUNTER": 42,
      "LKA_MODE": 2,
      "LKA_AVAILABLE": 0,
      "LKA_WARNING": 0,
      "LKA_ICON": 1,
      "FCA_SYSWARN": 0,
      "TORQUE_REQUEST": 17,
      "STEER_REQ": 1,
      "LFA_BUTTON": 0,
      "LKA_ASSIST": 0,
      "STEER_MODE": 2,
      "NEW_SIGNAL_2": 3,
      "HAS_LANE_SAFETY": 1,
      "DAMP_FACTOR": 100,
    }
    cc = SimpleNamespace(enabled=True, latActive=True,
                         actuators=SimpleNamespace(longControlState=LongCtrlState.off),
                         leftBlinker=False, rightBlinker=False,
                         hudControl=SimpleNamespace())
    cs = SimpleNamespace(stock_lfa_msg=None, stock_lkas_msg=stock_lkas,
                         out=SimpleNamespace(steeringAngleDeg=0.0,
                                             gearShifter=structs.CarState.GearShifter.drive))

    msgs = controller.create_canfd_msgs(0, True, 0.44, 0.0, 0.0, 0.0, False,
                                        cc.hudControl, cs, cc, get_test_toggles(), lka_icon=2, lfa_icon=2)
    lkas_msgs = [msg for msg in msgs if msg[0] == 0x50]
    assert len(lkas_msgs) == 1

    parser.update([(1, lkas_msgs)])
    assert parser.can_valid
    assert parser.vl["LKAS"]["HAS_LANE_SAFETY"] == 0
    assert parser.vl["LKAS"]["DAMP_FACTOR"] == 0
    assert parser.vl["LKAS"]["TORQUE_REQUEST"] == 0
    assert parser.vl["LKAS"]["STEER_REQ"] == 1
    assert parser.vl["LKAS"]["STEER_MODE"] == 0
    assert parser.vl["LKAS"]["NEW_SIGNAL_2"] == 0

    CP.openpilotLongitudinalControl = True
    lfa_parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LFA", 0)], can_bus.ECAN)
    lfa_msgs = hyundaicanfd.create_steering_messages(controller.packer, CP, can_bus, True, True, 0, 0.0)
    assert [(controller.packer.dbc.addr_to_msg[addr].name, bus) for addr, _, bus in lfa_msgs] == [("LFA", can_bus.ECAN), ("LKAS", can_bus.ACAN)]
    lfa_parser.update([(1, [lfa_msgs[0]])])
    assert lfa_parser.can_valid
    assert lfa_parser.vl["LFA"]["DAMP_FACTOR"] == 100

    controller.long_active_ecu = True
    cc.longActive = False
    inactive_msgs = controller.create_canfd_msgs(0, True, 0.44, 0.0, 0.0, 0.0, False,
                                                 cc.hudControl, cs, cc, get_test_toggles(), lka_icon=2, lfa_icon=2)
    steering_names = [(controller.packer.dbc.addr_to_msg[addr].name, bus) for addr, _, bus in inactive_msgs
                      if controller.packer.dbc.addr_to_msg[addr].name in ("LFA", "LKAS")]
    assert steering_names == [("LKAS", can_bus.ACAN)]

    controller.frame = 1
    cc.longActive = True
    active_msgs = controller.create_canfd_msgs(0, True, 0.44, 0.0, 0.0, 0.0, False,
                                               cc.hudControl, cs, cc, get_test_toggles(), lka_icon=2, lfa_icon=2)
    steering_names = [(controller.packer.dbc.addr_to_msg[addr].name, bus) for addr, _, bus in active_msgs
                      if controller.packer.dbc.addr_to_msg[addr].name in ("LFA", "LKAS")]
    assert steering_names == [("LFA", can_bus.ECAN), ("LKAS", can_bus.ACAN)]

  def test_gv70_electrified_longitudinal_uses_hda2_scc_contract(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_LKA_STEERING)
    CP.openpilotLongitudinalControl = True

    controller = CarController(DBC[CP.carFingerprint], CP)
    controller.frame = 2
    controller.long_active_ecu = True
    can_bus = CanBus(CP)
    cc = SimpleNamespace(
      enabled=True, latActive=True,
      actuators=SimpleNamespace(longControlState=LongCtrlState.pid),
      cruiseControl=SimpleNamespace(override=False, cancel=False, resume=False),
      leftBlinker=False, rightBlinker=False,
      hudControl=SimpleNamespace(leadDistanceBars=3),
    )
    cs = SimpleNamespace(
      stock_lfa_msg=None, stock_lkas_msg=None,
      out=SimpleNamespace(steeringAngleDeg=0.0, gearShifter=structs.CarState.GearShifter.drive),
    )

    msgs = controller.create_canfd_msgs(0, True, 0.0, 0.0, 42.0, -1.0, False,
                                        cc.hudControl, cs, cc, get_test_toggles(), lka_icon=2, lfa_icon=2)
    scc_msgs = [msg for msg in msgs if msg[0] == 0x1A0]
    assert len(scc_msgs) == 1

    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("SCC_CONTROL", 0)], can_bus.ECAN)
    parser.update([(1, scc_msgs)])
    assert parser.can_valid
    assert parser.vl["SCC_CONTROL"]["MainMode_ACC"] == 1
    assert parser.vl["SCC_CONTROL"]["ACC_ObjDist"] == pytest.approx(1.0)
    assert parser.vl["SCC_CONTROL"]["ObjValid"] == 0
    assert parser.vl["SCC_CONTROL"]["aReqValue"] == pytest.approx(-0.1)
    assert parser.vl["SCC_CONTROL"]["aReqRaw"] == pytest.approx(-1.0)

  def test_gv70_electrified_suppresses_only_stock_scc_brake_cancel(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN
    CP.openpilotLongitudinalControl = False

    assert suppress_redundant_gv70_brake_cancel(CP, brake_pressed=True, lat_active=True)
    assert not suppress_redundant_gv70_brake_cancel(CP, brake_pressed=False, lat_active=True)
    assert not suppress_redundant_gv70_brake_cancel(CP, brake_pressed=True, lat_active=False)

    CP.openpilotLongitudinalControl = True
    assert not suppress_redundant_gv70_brake_cancel(CP, brake_pressed=True, lat_active=True)

    CP.carFingerprint = CAR.HYUNDAI_IONIQ_6
    CP.openpilotLongitudinalControl = False
    assert not suppress_redundant_gv70_brake_cancel(CP, brake_pressed=True, lat_active=True)

  def test_ev9_inactive_angle_steering_lets_safety_forward_stock_lkas(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV9
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_ANGLE_STEERING |
                   HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)
    CP.openpilotLongitudinalControl = False

    controller = CarController(DBC[CP.carFingerprint], CP)
    cc = SimpleNamespace(enabled=False, latActive=False, actuators=SimpleNamespace(longControlState=LongCtrlState.off),
                         leftBlinker=False, rightBlinker=False, hudControl=SimpleNamespace())
    stock_lkas = {
      "CHECKSUM": 1234,
      "COUNTER": 42,
      "LKA_OptUsmSta": 2,
      "LKA_MODE": 2,
      "LKA_RcgSta": 3,
      "LKA_AVAILABLE": 3,
      "LKA_LHLnWrnSta": 3,
      "LKA_RHLnWrnSta": 3,
      "LKA_WARNING": 1,
      "LKA_HndsoffSnd": 1,
      "LKA_StrSnd": 1,
      "LKA_SysIndReq": 4,
      "LKA_ICON": 0,
      "FCA_SYSWARN": 1,
      "StrTqReqVal": 17,
      "TORQUE_REQUEST": 17,
      "ActToiSta": 3,
      "STEER_REQ": 1,
      "ToiFltSta": 3,
      "LFA_BUTTON": 1,
      "LKA_SysWrn": 15,
      "LKA_ASSIST": 1,
      "Damping_Gain": 0,
      "STEER_MODE": 5,
      "NEW_SIGNAL_2": 0,
      "LKAS_ANGLE_ACTIVE": 2,
      "LKA_UsmMod": 3,
      "HAS_LANE_SAFETY": 1,
      "ADAS_StrAnglReqVal": 12.3,
      "ADAS_ACIAnglTqRedcGainVal": 0.42,
      "DAMP_FACTOR": 0,
    }
    lfa_block_msg = {f"BYTE{i}": 0 for i in range(3, 32) if i != 7}
    lfa_block_msg["COUNTER"] = 0
    cs = SimpleNamespace(stock_lfa_msg=None, stock_lkas_msg=stock_lkas, lfa_block_msg=lfa_block_msg,
                         out=SimpleNamespace(steeringAngleDeg=-201.0))

    msgs = controller.create_canfd_msgs(0, False, 0.0, -201.0, 0.0, 0.0, False, cc.hudControl, cs, cc,
                                        get_test_toggles(), lka_icon=1, lfa_icon=1)
    lkas_msgs = [msg for msg in msgs if msg[0] == 0x110]
    assert len(lkas_msgs) == 0

  @pytest.mark.parametrize(("standstill", "expected_lkas_msgs"), [(False, 1), (True, 0)])
  def test_ioniq_5_pe_standstill_lets_safety_forward_stock_lkas(self, standstill, expected_lkas_msgs):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.HYUNDAI_IONIQ_5_PE
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_ANGLE_STEERING |
                   HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT |
                   HyundaiFlags.CCNC)
    CP.openpilotLongitudinalControl = False

    controller = CarController(DBC[CP.carFingerprint], CP)
    cc = SimpleNamespace(enabled=True, latActive=False, actuators=SimpleNamespace(longControlState=LongCtrlState.off),
                         leftBlinker=False, rightBlinker=False, hudControl=SimpleNamespace())
    cs = SimpleNamespace(
      stock_lfa_msg=None,
      stock_lkas_msg={},
      out=SimpleNamespace(
        standstill=standstill,
        steeringAngleDeg=0.0,
        gearShifter=structs.CarState.GearShifter.drive,
      ),
    )

    msgs = controller.create_canfd_msgs(0, False, 0.0, 0.0, 0.0, 0.0, False, cc.hudControl, cs, cc,
                                        get_test_toggles(), lka_icon=1, lfa_icon=1)
    assert len([msg for msg in msgs if msg[0] == 0x110]) == expected_lkas_msgs

  @pytest.mark.parametrize("standstill", [False, True])
  def test_sportage_angle_lkas_alt_keeps_inactive_status_in_drive(self, standstill):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_SPORTAGE_HEV_2026
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.HYBRID | HyundaiFlags.CANFD_ANGLE_STEERING |
                   HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)
    CP.openpilotLongitudinalControl = False

    controller = CarController(DBC[CP.carFingerprint], CP)
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS_ALT", 0)], can_bus.ACAN)
    stock_lkas = {
      "CHECKSUM": 1234,
      "COUNTER": 42,
      "LKA_OptUsmSta": 2,
      "LKA_MODE": 2,
      "LKA_RcgSta": 3,
      "LKA_AVAILABLE": 3,
      "LKA_LHLnWrnSta": 3,
      "LKA_RHLnWrnSta": 3,
      "LKA_WARNING": 1,
      "LKA_HndsoffSnd": 1,
      "LKA_StrSnd": 1,
      "LKA_SysIndReq": 4,
      "LKA_ICON": 2,
      "FCA_SYSWARN": 1,
      "StrTqReqVal": 17,
      "TORQUE_REQUEST": 17,
      "ActToiSta": 3,
      "STEER_REQ": 1,
      "ToiFltSta": 3,
      "LFA_BUTTON": 1,
      "LKA_SysWrn": 15,
      "LKA_ASSIST": 1,
      "Damping_Gain": 0,
      "STEER_MODE": 5,
      "NEW_SIGNAL_2": 0,
      "LKAS_ANGLE_ACTIVE": 2,
      "LKA_UsmMod": 3,
      "HAS_LANE_SAFETY": 1,
      "ADAS_StrAnglReqVal": 12.3,
      "ADAS_ACIAnglTqRedcGainVal": 0.42,
      "DAMP_FACTOR": 0,
    }
    cc = SimpleNamespace(enabled=False, latActive=False,
                         actuators=SimpleNamespace(longControlState=LongCtrlState.off),
                         leftBlinker=False, rightBlinker=False, hudControl=SimpleNamespace())
    cs = SimpleNamespace(stock_lfa_msg=None, stock_lkas_msg=stock_lkas,
                         out=SimpleNamespace(standstill=standstill, steeringAngleDeg=0.0,
                                             gearShifter=structs.CarState.GearShifter.drive))

    msgs = controller.create_canfd_msgs(0, False, 0.0, 0.0, 0.0, 0.0, False, cc.hudControl, cs, cc,
                                        get_test_toggles(), lka_icon=1, lfa_icon=1)
    lkas_msgs = [msg for msg in msgs if msg[0] == 0x110]
    assert len(lkas_msgs) == 1

    parser.update([(1, lkas_msgs)])
    assert parser.can_valid
    assert parser.vl["LKAS_ALT"]["LKA_StrSnd"] == 2
    assert parser.vl["LKAS_ALT"]["LKA_SysIndReq"] == 1
    assert parser.vl["LKAS_ALT"]["LKA_RcgSta"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_AVAILABLE"] == 0
    assert parser.vl["LKAS_ALT"]["LKAS_ANGLE_ACTIVE"] == 1

  def test_ev9_inactive_angle_steering_does_not_suppress_stock_lfa(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV9
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_ANGLE_STEERING |
                   HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)
    CP.openpilotLongitudinalControl = False

    controller = CarController(DBC[CP.carFingerprint], CP)
    controller.frame = 5
    cc = SimpleNamespace(enabled=False, latActive=False, actuators=SimpleNamespace(longControlState=LongCtrlState.off),
                         leftBlinker=False, rightBlinker=False, hudControl=SimpleNamespace())
    lfa_block_msg = {f"BYTE{i}": 0 for i in range(3, 32) if i != 7}
    lfa_block_msg["COUNTER"] = 0
    cs = SimpleNamespace(stock_lfa_msg=None, stock_lkas_msg={}, lfa_block_msg=lfa_block_msg,
                         out=SimpleNamespace(steeringAngleDeg=0.0, gearShifter=structs.CarState.GearShifter.drive))

    msgs = controller.create_canfd_msgs(0, False, 0.0, 0.0, 0.0, 0.0, False, cc.hudControl, cs, cc,
                                        get_test_toggles(), lka_icon=1, lfa_icon=1)
    suppress_msgs = [msg for msg in msgs if msg[0] == 0x362]
    assert not suppress_msgs

  def test_ev9_active_angle_steering_still_suppresses_stock_lfa(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV9
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_ANGLE_STEERING |
                   HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)
    CP.openpilotLongitudinalControl = False

    controller = CarController(DBC[CP.carFingerprint], CP)
    controller.frame = 5
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("CAM_0x362", 0)], can_bus.ECAN)
    cc = SimpleNamespace(enabled=False, latActive=True, actuators=SimpleNamespace(longControlState=LongCtrlState.off),
                         leftBlinker=False, rightBlinker=False, hudControl=SimpleNamespace())
    lfa_block_msg = {f"BYTE{i}": 0 for i in range(3, 32) if i != 7}
    lfa_block_msg["COUNTER"] = 0
    cs = SimpleNamespace(stock_lfa_msg=None, stock_lkas_msg={}, lfa_block_msg=lfa_block_msg,
                         out=SimpleNamespace(steeringAngleDeg=0.0, gearShifter=structs.CarState.GearShifter.drive))

    msgs = controller.create_canfd_msgs(0, False, 0.0, 0.0, 0.0, 0.0, False, cc.hudControl, cs, cc,
                                        get_test_toggles(), lka_icon=2, lfa_icon=2)
    suppress_msgs = [msg for msg in msgs if msg[0] == 0x362]
    assert len(suppress_msgs) == 1

    parser.update([(1, suppress_msgs)])

    assert parser.can_valid
    assert parser.vl["CAM_0x362"]["LEFT_LANE_LINE"] == 0
    assert parser.vl["CAM_0x362"]["RIGHT_LANE_LINE"] == 0

  def test_ev9_high_steering_angle_keeps_active_status_and_gain(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV9
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_ANGLE_STEERING |
                   HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)
    CP.openpilotLongitudinalControl = False

    controller = CarController(DBC[CP.carFingerprint], CP)
    controller.frame = 5
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS_ALT", 0)], can_bus.ACAN)
    stock_lkas = {
      "CHECKSUM": 1234,
      "COUNTER": 42,
      "LKA_MODE": 2,
      "LKA_AVAILABLE": 3,
      "LKA_WARNING": 1,
      "LKA_ICON": 1,
      "FCA_SYSWARN": 1,
      "TORQUE_REQUEST": 17,
      "STEER_REQ": 1,
      "LFA_BUTTON": 1,
      "LKA_ASSIST": 1,
      "STEER_MODE": 5,
      "NEW_SIGNAL_2": 0,
      "LKAS_ANGLE_ACTIVE": 1,
      "HAS_LANE_SAFETY": 1,
      "ADAS_StrAnglReqVal": 12.3,
      "ADAS_ACIAnglTqRedcGainVal": 0.42,
      "DAMP_FACTOR": 0,
    }
    cc = SimpleNamespace(enabled=True, latActive=True, actuators=SimpleNamespace(longControlState=LongCtrlState.off),
                         leftBlinker=False, rightBlinker=False, hudControl=SimpleNamespace())
    lfa_block_msg = {f"BYTE{i}": 0 for i in range(3, 32) if i != 7}
    lfa_block_msg["COUNTER"] = 0
    cs = SimpleNamespace(stock_lfa_msg=None, stock_lkas_msg=stock_lkas, lfa_block_msg=lfa_block_msg,
                         out=SimpleNamespace(steeringAngleDeg=120.0, gearShifter=structs.CarState.GearShifter.drive))

    msgs = controller.create_canfd_msgs(0, True, 0.44, 120.0, 0.0, 0.0, False, cc.hudControl, cs, cc,
                                        get_test_toggles(), lka_icon=2, lfa_icon=2)
    lkas_msgs = [msg for msg in msgs if msg[0] == 0x110]
    suppress_msgs = [msg for msg in msgs if msg[0] == 0x362]
    assert len(lkas_msgs) == 1
    assert len(suppress_msgs) == 1

    parser.update([(1, lkas_msgs)])

    assert parser.can_valid
    assert parser.vl["LKAS_ALT"]["LKAS_ANGLE_ACTIVE"] == 2
    assert parser.vl["LKAS_ALT"]["ADAS_ACIAnglTqRedcGainVal"] == pytest.approx(0.44)
    assert parser.vl["LKAS_ALT"]["ADAS_StrAnglReqVal"] == pytest.approx(120.0)

  def test_can_acc_commands_use_default_values(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.GENESIS_G90

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("SCC11", 0), ("SCC12", 0), ("SCC14", 0)], 0)

    msgs = hyundaican.create_acc_commands(packer, enabled=True, accel=-1.0, upper_jerk=2.5, idx=3,
                                          hud_control=SimpleNamespace(leadDistanceBars=3, leadVisible=False), set_speed=42,
                                          stopping=False, long_override=False, use_fca=False, CP=CP)
    parser.update([(1, msgs)])

    assert parser.can_valid
    assert parser.vl["SCC11"]["MainMode_ACC"] == 1
    assert parser.vl["SCC12"]["StopReq"] == 0
    assert parser.vl["SCC12"]["CF_VSM_ConfMode"] == 1
    assert parser.vl["SCC12"]["AEB_Status"] == 2
    assert parser.vl["SCC12"]["aReqRaw"] == pytest.approx(-1.0)
    assert parser.vl["SCC12"]["aReqValue"] == pytest.approx(-1.0)
    assert parser.vl["SCC14"]["ComfortBandUpper"] == pytest.approx(0.0)
    assert parser.vl["SCC14"]["ComfortBandLower"] == pytest.approx(0.0)
    assert parser.vl["SCC14"]["JerkLowerLimit"] == pytest.approx(5.0)

  def test_can_acc_commands_follow_sonata_main_cruise_state(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.HYUNDAI_SONATA_HYBRID

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("SCC11", 0)], 0)

    msgs = hyundaican.create_acc_commands(packer, enabled=False, accel=0.0, upper_jerk=1.0, idx=3,
                                          hud_control=SimpleNamespace(leadDistanceBars=3, leadVisible=False), set_speed=42,
                                          stopping=False, long_override=False, use_fca=False, CP=CP,
                                          main_cruise_enabled=False)
    parser.update([(1, msgs)])

    assert parser.can_valid
    assert parser.vl["SCC11"]["MainMode_ACC"] == 0

  def test_can_acc_commands_use_enabled_fca_status(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.GENESIS_G90

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("FCA11", 0)], 0)

    msgs = hyundaican.create_acc_commands(packer, enabled=True, accel=-1.0, upper_jerk=2.5, idx=3,
                                          hud_control=SimpleNamespace(leadDistanceBars=3, leadVisible=False), set_speed=42,
                                          stopping=False, long_override=False, use_fca=True, CP=CP)
    parser.update([(1, msgs)])

    assert parser.can_valid
    assert parser.vl["FCA11"]["FCA_Status"] == 2

  def test_can_canfd_blended_acc_commands_use_palisade_2023_layout(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.HYUNDAI_PALISADE_2023
    CP.flags = int(HyundaiFlags.CAN_CANFD_BLENDED)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [
      ("SCC11", 0),
      ("SCC12", 0),
      ("SCC14", 0),
      ("RADAR_0x363", 0),
      ("RADAR_0x398", 0),
    ], 0)

    msgs = hyundaican.create_acc_commands_can_canfd_blended(
      packer,
      enabled=True,
      accel=-1.0,
      upper_jerk=2.5,
      idx=3,
      hud_control=SimpleNamespace(leadDistanceBars=3),
      set_speed=42,
      stopping=False,
      long_override=False,
      use_fca=False,
      CP=CP,
    )
    msgs.extend(hyundaican.create_radar_aux_messages(packer, CanBus(CP), 10))
    parser.update([(1, msgs)])

    assert parser.can_valid
    assert parser.vl["SCC11"]["aReqRaw"] == pytest.approx(-1.0)
    assert parser.vl["SCC11"]["aReqValue"] == pytest.approx(-1.0)
    assert parser.vl["SCC12"]["ACCMode"] == 1
    assert parser.vl["SCC12"]["MainMode_ACC"] == 1
    assert parser.vl["SCC14"]["ObjStatus"] == 1
    assert parser.vl["RADAR_0x363"]["FCA_ESA"] == 1

  def test_can_canfd_blended_hda2_acc_commands_use_hda2_layout(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.HYUNDAI_PALISADE_2023
    CP.flags = int(HyundaiFlags.CAN_CANFD_BLENDED | HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.USE_FCA)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [
      ("SCC11", 0),
      ("SCC12", 0),
      ("SCC14", 0),
      ("FCA11", 0),
    ], 1)

    msgs = hyundaican.create_acc_commands_can_canfd_blended_hda2(
      packer,
      enabled=True,
      accel=-1.0,
      accel_last=0.0,
      upper_jerk=2.5,
      idx=15,
      hud_control=SimpleNamespace(leadDistanceBars=3, leadVisible=True),
      set_speed=42,
      stopping=False,
      long_override=False,
      use_fca=True,
      CP=CP,
    )
    parser.update([(1, msgs)])

    assert parser.can_valid
    assert parser.vl["SCC11"]["aReqRaw"] == pytest.approx(-1.0)
    assert parser.vl["SCC11"]["aReqValue"] == pytest.approx(-0.1)
    assert parser.vl["SCC11"]["COUNTER"] == 0
    assert parser.vl["SCC12"]["VSetDis"] == 42
    assert parser.vl["SCC14"]["ObjValid"] == 0
    assert parser.vl["SCC14"]["ObjStatus"] == 2
    assert parser.vl["FCA11"]["aeb_cmd_act"] == 0
    assert parser.vl["FCA11"]["fca_cmd_act"] == 0
    assert next(dat for addr, dat, _ in msgs if addr == 0x38D)[4:7] == b"\xC0\x3F\x7F"

  def test_can_acc_optional_messages_use_enabled_fca_usm(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.GENESIS_G90

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("FCA12", 0)], 0)

    msgs = hyundaican.create_acc_opt(packer, CP)
    parser.update([(1, msgs)])

    assert parser.can_valid
    assert parser.vl["FCA12"]["FCA_DrvSetState"] == 2
    assert parser.vl["FCA12"]["FCA_USM"] == 2

  def test_angle_steering_uses_lfa_and_adas_cmd_with_send_lfa(self):
    fingerprint = gen_empty_fingerprint()
    cam_can = CanBus(None, fingerprint).CAM
    fingerprint[cam_can][0xCB] = 24
    CP = CarInterface.get_params(CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN, fingerprint, [], False, False, False, None)

    assert CP.flags & HyundaiFlags.SEND_LFA
    assert CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    msgs = hyundaicanfd.create_steering_messages(packer, CP, can_bus, True, True, 1.0, 12.3)
    assert [(packer.dbc.addr_to_msg[addr].name, bus) for addr, _, bus in msgs] == [
      ("LFA", can_bus.ECAN),
      ("ADAS_CMD_35_10ms", can_bus.ECAN),
    ]

  def test_ioniq_6_lfa_helper_preserves_stock_ui_fields(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.HYUNDAI_IONIQ_6
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEERING)
    CP.openpilotLongitudinalControl = True

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LFA", 0)], can_bus.ECAN)

    stock_lfa = {
      "CHECKSUM": 1234,
      "COUNTER": 42,
      "LKA_MODE": 6,
      "NEW_SIGNAL_1": 3,
      "LKA_WARNING": 1,
      "LKA_ICON": 1,
      "TORQUE_REQUEST": 17,
      "STEER_REQ": 0,
      "LFA_BUTTON": 1,
      "LKA_ASSIST": 1,
      "STEER_MODE": 5,
      "NEW_SIGNAL_2": 2,
      "NEW_SIGNAL_4": 7,
      "HAS_LANE_SAFETY": 1,
      "DAMP_FACTOR": 0x77,
    }

    msgs = hyundaicanfd.create_steering_messages(packer, CP, can_bus, True, True, 123, 0.0, stock_lfa)
    lfa_msgs = [msg for msg in msgs if msg[0] == 0x12A]
    assert len(lfa_msgs) == 1

    parser.update([(1, lfa_msgs)])

    assert parser.can_valid
    assert parser.vl["LFA"]["NEW_SIGNAL_1"] == 3
    assert parser.vl["LFA"]["NEW_SIGNAL_2"] == 2
    assert parser.vl["LFA"]["HAS_LANE_SAFETY"] == 1
    assert parser.vl["LFA"]["DAMP_FACTOR"] == 0x77
    assert parser.vl["LFA"]["TORQUE_REQUEST"] == 123
    assert parser.vl["LFA"]["STEER_REQ"] == 1
    assert parser.vl["LFA"]["LKA_ICON"] == 2

  def test_ioniq_6_lfa_helper_allows_lka_icon_override(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.HYUNDAI_IONIQ_6
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEERING)
    CP.openpilotLongitudinalControl = True

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LFA", 0)], can_bus.ECAN)

    msgs = hyundaicanfd.create_steering_messages(packer, CP, can_bus, False, False, 0, 0.0, lka_icon=3)
    lfa_msgs = [msg for msg in msgs if msg[0] == 0x12A]
    assert len(lfa_msgs) == 1

    parser.update([(1, lfa_msgs)])

    assert parser.can_valid
    assert parser.vl["LFA"]["LKA_ICON"] == 3

  def test_kia_ev6_lfa_helper_preserves_stock_ui_fields_with_stock_long(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV6
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEERING)
    CP.openpilotLongitudinalControl = False

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)

    stock_lfa = {
      "CHECKSUM": 1234,
      "COUNTER": 42,
      "LKA_MODE": 6,
      "NEW_SIGNAL_1": 3,
      "LKA_WARNING": 1,
      "LKA_ICON": 1,
      "TORQUE_REQUEST": 17,
      "STEER_REQ": 0,
      "LFA_BUTTON": 1,
      "LKA_ASSIST": 1,
      "STEER_MODE": 5,
      "NEW_SIGNAL_2": 2,
      "NEW_SIGNAL_4": 7,
      "HAS_LANE_SAFETY": 1,
      "DAMP_FACTOR": 0x77,
    }

    msgs = hyundaicanfd.create_steering_messages(packer, CP, can_bus, True, True, 123, 0.0, stock_lfa)
    assert [(packer.dbc.addr_to_msg[addr].name, bus) for addr, _, bus in msgs] == [
      ("LKAS", can_bus.ACAN),
    ]

  def test_ev9_fallback_active_lateral_uses_lkas_without_injecting_lfa(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV9
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CCNC |
                   HyundaiFlags.CANFD_ANGLE_STEERING | HyundaiFlags.CANFD_LKA_STEERING |
                   HyundaiFlags.CANFD_LKA_STEERING_ALT)
    CP.openpilotLongitudinalControl = True

    controller = CarController(DBC[CP.carFingerprint], CP)
    controller.frame = 1
    controller.ecu_disable_failed = True
    controller.long_active_ecu = False
    CP.openpilotLongitudinalControl = False
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    cc = SimpleNamespace(
      enabled=True,
      latActive=True,
      actuators=SimpleNamespace(longControlState=LongCtrlState.off),
      cruiseControl=SimpleNamespace(cancel=False, resume=False),
      leftBlinker=False,
      rightBlinker=False,
      hudControl=SimpleNamespace(),
    )
    cs = SimpleNamespace(
      stock_lfa_msg={},
      stock_lkas_msg={},
      out=SimpleNamespace(
        standstill=False,
        steeringAngleDeg=-31.5,
        gearShifter=structs.CarState.GearShifter.drive,
      ),
    )

    msgs = controller.create_canfd_msgs(0, True, 0.44, -31.5, 0.0, 0.0, False,
                                        cc.hudControl, cs, cc, get_test_toggles(), lka_icon=2, lfa_icon=2)
    assert [(packer.dbc.addr_to_msg[addr].name, bus) for addr, _, bus in msgs] == [
      ("LKAS_ALT", can_bus.ACAN),
    ]

  def test_ev9_fallback_does_not_inject_lfa_while_parked(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV9
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CCNC |
                   HyundaiFlags.CANFD_ANGLE_STEERING | HyundaiFlags.CANFD_LKA_STEERING |
                   HyundaiFlags.CANFD_LKA_STEERING_ALT)
    CP.openpilotLongitudinalControl = False

    controller = CarController(DBC[CP.carFingerprint], CP)
    controller.ecu_disable_failed = True
    cc = SimpleNamespace(
      enabled=False,
      latActive=False,
      actuators=SimpleNamespace(longControlState=LongCtrlState.off),
      cruiseControl=SimpleNamespace(cancel=False, resume=False),
      leftBlinker=False,
      rightBlinker=False,
      hudControl=SimpleNamespace(),
    )
    cs = SimpleNamespace(
      stock_lfa_msg={},
      stock_lkas_msg={},
      out=SimpleNamespace(
        standstill=True,
        steeringAngleDeg=0.0,
        gearShifter=structs.CarState.GearShifter.park,
      ),
    )

    msgs = controller.create_canfd_msgs(0, False, 0.0, 0.0, 0.0, 0.0, False,
                                        cc.hudControl, cs, cc, get_test_toggles(), lka_icon=1, lfa_icon=1)

    assert not [msg for msg in msgs if msg[0] in (0x110, 0x12A)]

  def test_kia_ev6_lkas_helper_preserves_stock_camera_fields_with_stock_long(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV6
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEERING)
    CP.openpilotLongitudinalControl = False

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS", 0)], can_bus.ACAN)

    stock_lkas = {
      "CHECKSUM": 1234,
      "COUNTER": 42,
      "LKA_MODE": 6,
      "LKA_AVAILABLE": 3,
      "LKA_WARNING": 1,
      "LKA_ICON": 1,
      "FCA_SYSWARN": 1,
      "TORQUE_REQUEST": 17,
      "STEER_REQ": 0,
      "LFA_BUTTON": 1,
      "LKA_ASSIST": 1,
      "STEER_MODE": 5,
      "NEW_SIGNAL_2": 2,
      "HAS_LANE_SAFETY": 1,
      "DAMP_FACTOR": 0x70,
    }

    msgs = hyundaicanfd.create_steering_messages(packer, CP, can_bus, True, True, 123, 0.0,
                                                 lkas_base_values=stock_lkas)
    lkas_msgs = [msg for msg in msgs if msg[0] == 0x50]
    assert len(lkas_msgs) == 1

    parser.update([(1, lkas_msgs)])

    assert parser.can_valid
    assert parser.vl["LKAS"]["LKA_AVAILABLE"] == 3
    assert parser.vl["LKAS"]["LKA_WARNING"] == 1
    assert parser.vl["LKAS"]["FCA_SYSWARN"] == 1
    assert parser.vl["LKAS"]["LFA_BUTTON"] == 1
    assert parser.vl["LKAS"]["HAS_LANE_SAFETY"] == 1
    assert parser.vl["LKAS"]["DAMP_FACTOR"] == 0x70
    assert parser.vl["LKAS"]["TORQUE_REQUEST"] == 123
    assert parser.vl["LKAS"]["STEER_REQ"] == 1
    assert parser.vl["LKAS"]["LKA_ICON"] == 2

  def test_ioniq_6_lkas_alt_helper_preserves_stock_camera_fields(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.HYUNDAI_IONIQ_6
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS_ALT", 0)], can_bus.ACAN)

    stock_lkas = {
      "CHECKSUM": 1234,
      "COUNTER": 42,
      "LKA_MODE": 6,
      "LKA_AVAILABLE": 3,
      "LKA_WARNING": 1,
      "LKA_ICON": 1,
      "FCA_SYSWARN": 1,
      "TORQUE_REQUEST": 17,
      "STEER_REQ": 0,
      "LFA_BUTTON": 1,
      "LKA_ASSIST": 1,
      "STEER_MODE": 5,
      "NEW_SIGNAL_2": 2,
      "LKAS_ANGLE_ACTIVE": 1,
      "HAS_LANE_SAFETY": 1,
      "ADAS_StrAnglReqVal": 12.3,
      "ADAS_ACIAnglTqRedcGainVal": 0.42,
      "DAMP_FACTOR": 0x70,
    }

    msgs = hyundaicanfd.create_steering_messages(packer, CP, can_bus, True, True, 123, 0.0,
                                                 lkas_base_values=stock_lkas)
    lkas_msgs = [msg for msg in msgs if msg[0] == 0x110]
    assert len(lkas_msgs) == 1

    parser.update([(1, lkas_msgs)])

    assert parser.can_valid
    assert parser.vl["LKAS_ALT"]["LKA_AVAILABLE"] == 3
    assert parser.vl["LKAS_ALT"]["LKA_WARNING"] == 1
    assert parser.vl["LKAS_ALT"]["FCA_SYSWARN"] == 1
    assert parser.vl["LKAS_ALT"]["LFA_BUTTON"] == 1
    assert parser.vl["LKAS_ALT"]["HAS_LANE_SAFETY"] == 1
    assert parser.vl["LKAS_ALT"]["DAMP_FACTOR"] == 0x70
    assert parser.vl["LKAS_ALT"]["TORQUE_REQUEST"] == 123
    assert parser.vl["LKAS_ALT"]["STEER_REQ"] == 1
    assert parser.vl["LKAS_ALT"]["LKA_ICON"] == 2

  def test_ev9_angle_lkas_alt_uses_angle_status_fields(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV9
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_ANGLE_STEERING |
                   HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS_ALT", 0)], can_bus.ACAN)

    stock_lkas = {
      "CHECKSUM": 1234,
      "COUNTER": 42,
      "LKA_MODE": 2,
      "LKA_AVAILABLE": 0,
      "LKA_WARNING": 1,
      "LKA_ICON": 1,
      "FCA_SYSWARN": 1,
      "TORQUE_REQUEST": 17,
      "STEER_REQ": 1,
      "LFA_BUTTON": 1,
      "LKA_ASSIST": 1,
      "STEER_MODE": 5,
      "NEW_SIGNAL_2": 0,
      "LKAS_ANGLE_ACTIVE": 1,
      "HAS_LANE_SAFETY": 1,
      "ADAS_StrAnglReqVal": 12.3,
      "ADAS_ACIAnglTqRedcGainVal": 0.42,
      "DAMP_FACTOR": 0,
    }

    msgs = hyundaicanfd.create_steering_messages(packer, CP, can_bus, False, True, 0.44, -31.5,
                                                 lkas_base_values=stock_lkas, lka_icon=2)
    lkas_msgs = [msg for msg in msgs if msg[0] == 0x110]
    assert len(lkas_msgs) == 1

    parser.update([(1, lkas_msgs)])

    assert parser.can_valid
    assert parser.vl["LKAS_ALT"]["LKA_OptUsmSta"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_RcgSta"] == 3
    assert parser.vl["LKAS_ALT"]["LKA_LHLnWrnSta"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_RHLnWrnSta"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_HndsoffSnd"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_StrSnd"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_SysIndReq"] == 2
    assert parser.vl["LKAS_ALT"]["StrTqReqVal"] == 0
    assert parser.vl["LKAS_ALT"]["ActToiSta"] == 0
    assert parser.vl["LKAS_ALT"]["ToiFltSta"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_SysWrn"] == 0
    assert parser.vl["LKAS_ALT"]["Damping_Gain"] == 100
    assert parser.vl["LKAS_ALT"]["LKA_UsmMod"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_MODE"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_AVAILABLE"] == 3
    assert parser.vl["LKAS_ALT"]["LKA_WARNING"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_ICON"] == 2
    assert parser.vl["LKAS_ALT"]["FCA_SYSWARN"] == 0
    assert parser.vl["LKAS_ALT"]["TORQUE_REQUEST"] == 0
    assert parser.vl["LKAS_ALT"]["STEER_REQ"] == 0
    assert parser.vl["LKAS_ALT"]["LFA_BUTTON"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_ASSIST"] == 0
    assert parser.vl["LKAS_ALT"]["DAMP_FACTOR"] == 100
    assert parser.vl["LKAS_ALT"]["LKAS_ANGLE_ACTIVE"] == 2
    assert parser.vl["LKAS_ALT"]["HAS_LANE_SAFETY"] == 0
    assert parser.vl["LKAS_ALT"]["ADAS_StrAnglReqVal"] == pytest.approx(-31.5)
    assert parser.vl["LKAS_ALT"]["ADAS_ACIAnglTqRedcGainVal"] == pytest.approx(0.44)

  def test_ev9_angle_lkas_alt_clears_stock_status_when_inactive(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV9
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_ANGLE_STEERING |
                   HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS_ALT", 0)], can_bus.ACAN)

    stock_lkas = {
      "CHECKSUM": 1234,
      "COUNTER": 42,
      "LKA_OptUsmSta": 6,
      "LKA_MODE": 2,
      "LKA_RcgSta": 7,
      "LKA_AVAILABLE": 3,
      "LKA_LHLnWrnSta": 3,
      "LKA_RHLnWrnSta": 3,
      "LKA_WARNING": 1,
      "LKA_HndsoffSnd": 1,
      "LKA_StrSnd": 1,
      "LKA_SysIndReq": 4,
      "LKA_ICON": 1,
      "FCA_SYSWARN": 1,
      "StrTqReqVal": 17,
      "TORQUE_REQUEST": 17,
      "ActToiSta": 3,
      "STEER_REQ": 1,
      "ToiFltSta": 3,
      "LFA_BUTTON": 1,
      "LKA_SysWrn": 15,
      "LKA_ASSIST": 1,
      "Damping_Gain": 0,
      "STEER_MODE": 5,
      "NEW_SIGNAL_2": 0,
      "LKAS_ANGLE_ACTIVE": 2,
      "LKA_UsmMod": 3,
      "HAS_LANE_SAFETY": 1,
      "ADAS_StrAnglReqVal": 12.3,
      "ADAS_ACIAnglTqRedcGainVal": 0.42,
      "DAMP_FACTOR": 0,
    }

    msgs = hyundaicanfd.create_steering_messages(packer, CP, can_bus, False, False, 0.44, -31.5,
                                                 lkas_base_values=stock_lkas, lka_icon=1)
    lkas_msgs = [msg for msg in msgs if msg[0] == 0x110]
    assert len(lkas_msgs) == 1

    parser.update([(1, lkas_msgs)])

    assert parser.can_valid
    assert parser.vl["LKAS_ALT"]["LKA_OptUsmSta"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_RcgSta"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_LHLnWrnSta"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_RHLnWrnSta"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_HndsoffSnd"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_StrSnd"] == 2
    assert parser.vl["LKAS_ALT"]["LKA_SysIndReq"] == 1
    assert parser.vl["LKAS_ALT"]["StrTqReqVal"] == 0
    assert parser.vl["LKAS_ALT"]["ActToiSta"] == 0
    assert parser.vl["LKAS_ALT"]["ToiFltSta"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_SysWrn"] == 0
    assert parser.vl["LKAS_ALT"]["Damping_Gain"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_UsmMod"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_MODE"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_AVAILABLE"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_WARNING"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_ICON"] == 1
    assert parser.vl["LKAS_ALT"]["FCA_SYSWARN"] == 0
    assert parser.vl["LKAS_ALT"]["TORQUE_REQUEST"] == 0
    assert parser.vl["LKAS_ALT"]["STEER_REQ"] == 0
    assert parser.vl["LKAS_ALT"]["LFA_BUTTON"] == 0
    assert parser.vl["LKAS_ALT"]["LKA_ASSIST"] == 0
    assert parser.vl["LKAS_ALT"]["DAMP_FACTOR"] == 0
    assert parser.vl["LKAS_ALT"]["LKAS_ANGLE_ACTIVE"] == 1
    assert parser.vl["LKAS_ALT"]["HAS_LANE_SAFETY"] == 0
    assert parser.vl["LKAS_ALT"]["ADAS_StrAnglReqVal"] == pytest.approx(12.3)
    assert parser.vl["LKAS_ALT"]["ADAS_ACIAnglTqRedcGainVal"] == pytest.approx(0.0)

  def test_ev9_accelerator_brake_alt_spoof_matches_route_template(self):
    msg = hyundaicanfd.create_accelerator_brake_alt_spoof(0, 0x66, True, False, CAR.KIA_EV9)

    assert msg.address == 0x100
    assert msg.src == 0
    assert msg.dat.hex() == "470c6600ff006f00e80400001201030055ffff0000000000"

  def test_ioniq_6_lfahda_cluster_allows_lfa_icon_override(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.HYUNDAI_IONIQ_6
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEERING)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LFAHDA_CLUSTER", 0)], can_bus.ECAN)

    msg = hyundaicanfd.create_lfahda_cluster(packer, can_bus, False, lfa_icon=3)
    parser.update([(1, [msg])])

    assert parser.can_valid
    assert parser.vl["LFAHDA_CLUSTER"]["LFA_ICON"] == 3

  def test_g90_lfahda_mfc_allows_lfa_icon_override(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.GENESIS_G90

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LFAHDA_MFC", 0)], 0)

    msg = hyundaican.create_lfahda_mfc(packer, False, frame=7, CP=CP, lfa_icon=3)
    parser.update([(1, [msg])])

    assert parser.can_valid
    assert parser.vl["LFAHDA_MFC"]["LFA_Icon_State"] == 3

  def test_ioniq_6_blindspot_status_helper_regenerates_counter_checksum(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.HYUNDAI_IONIQ_6
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEERING)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("BLINDSPOTS_REAR_CORNERS", 0), ("BLINDSPOTS_FRONT_CORNER_1", 0)], can_bus.ECAN)

    rear = {
      "CHECKSUM": 1111,
      "COUNTER": 77,
      "BCW_Sta": 0,
      "BCW_OnOffEquipSta": 0,
      "BCW_LtIndSta": 0,
      "BCW_RtIndSta": 0,
      "BCW_LtSndWrngSta": 0,
      "BCW_RtSndWrngSta": 0,
      "FL_INDICATOR": 0,
      "FR_INDICATOR": 0,
      "BCW_SnstvtyModRetVal": 0,
      "BCW_IndSta": 0,
      "BCA_OnOffEquip2Sta": 0,
      "BCA_Sta": 0,
      "BCA_OnOffEquipSta": 0,
      "BCA_DRV_WarnSta": 0,
      "BCA_Plus_Deccel_Req": 0,
      "BCA_Plus_BrkCmdSta": 0,
      "BCA_Plus_LtWrngSta": 0,
      "BCA_Plus_RtWrngSta": 0,
      "BCA_Plus_FuncStat": 0,
      "BCA_Plus_Sta": 0,
      "Brake_Control_RL": 0,
      "Brake_Control_RR": 0,
      "OSMrrLamp_LtIndSta": 0,
      "OSMrrLamp_RtIndSta": 0,
    }
    front = {
      "CHECKSUM": 2222,
      "COUNTER": 88,
      "REVERSING": 0,
      "NEW_SIGNAL_5": 0,
      "NEW_SIGNAL_7": 0,
      "NEW_SIGNAL_8": 0,
      "NEW_SIGNAL_9": 0,
      "NEW_SIGNAL_4": 0,
      "NEW_SIGNAL_3": 1,
      "NEW_SIGNAL_2": 0,
      "NEW_SIGNAL_1": 0,
    }

    msgs = hyundaicanfd.create_blindspot_status_messages(packer, can_bus, rear, front,
                                                         left_blindspot=True, right_blindspot=False,
                                                         left_blinker=False, right_blinker=False)
    parser.update([(1, msgs)])

    assert parser.can_valid
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["COUNTER"] == 0
    assert parser.vl["BLINDSPOTS_FRONT_CORNER_1"]["COUNTER"] == 0
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["BCW_Sta"] == 1
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["BCW_LtIndSta"] == 1
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["BCW_RtIndSta"] == 0
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["OSMrrLamp_LtIndSta"] == 1
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["OSMrrLamp_RtIndSta"] == 0
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["FL_INDICATOR"] == 1
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["FR_INDICATOR"] == 0
    assert parser.vl["BLINDSPOTS_FRONT_CORNER_1"]["NEW_SIGNAL_3"] == 1

    flash_msgs = hyundaicanfd.create_blindspot_status_messages(packer, can_bus, rear, front,
                                                               left_blindspot=True, right_blindspot=False,
                                                               left_blinker=True, right_blinker=False)
    parser.update([(1, flash_msgs)])

    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["BCW_LtIndSta"] == 2
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["OSMrrLamp_LtIndSta"] == 2

  def test_ev9_blindspot_status_uses_stock_warning_fields(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV9
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt],
                       [("BLINDSPOTS_REAR_CORNERS", 0), ("BLINDSPOTS_FRONT_CORNER_1", 0)], can_bus.ECAN)

    msgs = hyundaicanfd.create_ccnc_blindspot_status_messages(
      packer, CP, can_bus, 7, left_blindspot=True, left_escalated=True,
      drive_gear=True, left_warning_lamp=True, left_sound_active=True,
    )
    parser.update([(1, msgs)])

    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["BCW_LtIndSta"] == 2
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["OSMrrLamp_LtIndSta"] == 2
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["BCW_LtSndWrngSta"] == 1
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["BCW_Sta"] == 0
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["FL_INDICATOR"] == 0
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["BCW_IndSta"] == 1
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["BCA_OnOffEquip2Sta"] == 2
    assert parser.vl["BLINDSPOTS_REAR_CORNERS"]["BCA_Sta"] == 1
    assert parser.vl["BLINDSPOTS_FRONT_CORNER_1"]["NEW_SIGNAL_7"] == 0

  def test_ev9_ccnc_status_clears_faults_and_tracks_control_state(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.KIA_EV9
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("CCNC_0x161", 0), ("CCNC_0x162", 0)], can_bus.ECAN)

    parser.update([(1, hyundaicanfd.create_ccnc_angle_long_status_messages(packer, CP, can_bus, 12, hba_icon=2))])

    assert parser.vl["CCNC_0x161"]["FCA_ICON"] == 1
    assert parser.vl["CCNC_0x161"]["FCA_ALT_ICON"] == 0
    assert parser.vl["CCNC_0x161"]["FCA_IMAGE"] == 0
    assert parser.vl["CCNC_0x161"]["HBA_ICON"] == 2
    assert all(parser.vl["CCNC_0x161"][sound] == 0 for sound in ("SOUNDS_1", "SOUNDS_2", "SOUNDS_3", "SOUNDS_4"))
    assert parser.vl["CCNC_0x162"]["VIBRATE"] == 0
    assert all(parser.vl["CCNC_0x162"][fault] == 0 for fault in (
      "FAULT_FSS", "FAULT_FCA", "FAULT_LSS", "FAULT_SLA", "FAULT_HDA", "FAULT_DAS", "FAULT_LFA", "FAULT_DAW",
      "FAULT_HBA", "FAULT_ESS",
    ))

    parser.update([(1, hyundaicanfd.create_ccnc_angle_long_status_messages(
      packer, CP, can_bus, 13, main_cruise_enabled=True, steering_available=True, steering_active=False,
    ))])
    assert parser.vl["CCNC_0x161"]["HDA_ICON"] == 1
    assert parser.vl["CCNC_0x161"]["LFA_ICON"] == 1

    parser.update([(1, hyundaicanfd.create_ccnc_angle_long_status_messages(
      packer, CP, can_bus, 14, enabled=True, main_cruise_enabled=True,
      steering_available=True, steering_active=True,
    ))])
    assert parser.vl["CCNC_0x161"]["HDA_ICON"] == 2
    assert parser.vl["CCNC_0x161"]["LFA_ICON"] == 2

    parser.update([(1, hyundaicanfd.create_ccnc_angle_long_status_messages(
      packer, CP, can_bus, 15, enabled=True, main_cruise_enabled=True,
      steering_available=True, steering_active=False,
    ))])
    assert parser.vl["CCNC_0x161"]["HDA_ICON"] == 2
    assert parser.vl["CCNC_0x161"]["LFA_ICON"] == 1

  @pytest.mark.parametrize("candidate", (CAR.KIA_EV9, CAR.HYUNDAI_IONIQ_5_PE))
  def test_ccnc_acc_control_uses_packer_counter(self, candidate):
    CP = CarParams.new_message()
    CP.carFingerprint = candidate
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CCNC | HyundaiFlags.CANFD_ANGLE_STEERING |
                   HyundaiFlags.CANFD_LKA_STEERING | HyundaiFlags.CANFD_LKA_STEERING_ALT)

    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
    can_bus = CanBus(CP)
    parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("SCC_CONTROL", 0)], can_bus.ECAN)

    messages = [
      hyundaicanfd.create_ccnc_acc_control(
        packer, can_bus, True, 0.2, False, False, False, 50.0,
        1, 27.5, -1.2, True, 10.0,
      )
      for _ in range(2)
    ]
    parser.update([(1, [messages[0]])])
    parser.update([(2, [messages[1]])])

    assert parser.can_valid
    assert messages[0][1][2] == 0
    assert messages[1][1][2] == 1
    assert parser.vl["SCC_CONTROL"]["ACC_ObjDist"] == pytest.approx(27.5)
    assert parser.vl["SCC_CONTROL"]["ACC_ObjRelSpd"] == pytest.approx(-1.2)

  @pytest.mark.parametrize("candidate", (CAR.KIA_EV9, CAR.HYUNDAI_IONIQ_5_PE))
  def test_ccnc_adrv_templates_and_periods_present(self, candidate):
    expected_addrs = {0x160, 0x1DA, 0x1EA, 0x200, 0x345, 0x161, 0x162, 0x1BA, 0x1E5, 0x1E0, 0x38C}
    assert set(hyundaicanfd._CCNC_ADRV_TEMPLATES[candidate]) == expected_addrs
    assert set(hyundaicanfd._CCNC_ADRV_PERIODS[candidate]).issubset(expected_addrs)

  @pytest.mark.parametrize("candidate", (CAR.KIA_EV9, CAR.HYUNDAI_IONIQ_5_PE))
  @pytest.mark.parametrize(("steering_pressed", "steering_active"), ((False, True), (True, False)))
  def test_ccnc_steering_icon_tracks_controller_authority(self, monkeypatch, steering_pressed, steering_active, candidate):
    CP = CarParams.new_message()
    CP.carFingerprint = candidate
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CCNC |
                   HyundaiFlags.CANFD_ANGLE_STEERING | HyundaiFlags.CANFD_LKA_STEERING |
                   HyundaiFlags.CANFD_LKA_STEERING_ALT)
    CP.openpilotLongitudinalControl = True

    controller = CarController(DBC[CP.carFingerprint], CP)
    controller.frame = 5
    captured = {}

    def capture_ccnc_adrv_messages(*args, **kwargs):
      captured["steering_available"] = args[9]
      captured["steering_active"] = args[10]
      return []

    monkeypatch.setattr(hyundaicanfd, "create_ccnc_adrv_messages", capture_ccnc_adrv_messages)
    lfa_block_msg = {f"BYTE{i}": 0 for i in range(3, 32) if i != 7}
    lfa_block_msg["COUNTER"] = 0
    cc = SimpleNamespace(
      enabled=True,
      latActive=True,
      actuators=SimpleNamespace(longControlState=LongCtrlState.pid, accel=0.0),
      leftBlinker=False,
      rightBlinker=False,
      hudControl=SimpleNamespace(),
    )
    cs = SimpleNamespace(
      angle_steering_fault=False,
      angle_steering_angle=0.0,
      hba_icon=0,
      is_metric=True,
      left_blindspot_from_radar=False,
      right_blindspot_from_radar=False,
      lfa_block_msg=lfa_block_msg,
      out=SimpleNamespace(
        brakePressed=False,
        cruiseState=SimpleNamespace(available=True),
        gasPressed=False,
        gearShifter=structs.CarState.GearShifter.drive,
        steeringPressed=steering_pressed,
      ),
    )

    controller.create_canfd_msgs(0, True, 0.44, 0.0, 0.0, 0.0, False, cc.hudControl, cs, cc,
                                 get_test_toggles(), lka_icon=2, lfa_icon=2)

    assert captured == {"steering_available": True, "steering_active": steering_active}

  def test_ioniq_6_blindspot_radar_state_decode(self):
    assert decode_ioniq_6_blindspot_radar_state(0x02) == (False, False)
    assert decode_ioniq_6_blindspot_radar_state(0x0A) == (False, True)
    assert decode_ioniq_6_blindspot_radar_state(0x12) == (True, False)
    assert decode_ioniq_6_blindspot_radar_state(0x1A) == (True, True)
    assert decode_ioniq_6_blindspot_radar_state(10.0) == (False, True)

  def test_canfd_camera_lead_decode(self):
    assert decode_canfd_camera_lead(0.0, -1.0) == (False, 0.0, 0.0)
    assert decode_canfd_camera_lead(25.0, -1.5) == (True, 25.0, -1.5)

  def test_ioniq_6_cluster_blindspot_helper_uses_captured_stock_sequences(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.HYUNDAI_IONIQ_6
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEERING)

    can_bus = CanBus(CP)

    right_msgs = hyundaicanfd.create_ioniq_6_cluster_blindspot_messages(can_bus, 0, False, True)
    assert right_msgs == [
      (0x3B5, bytes.fromhex("caa95c00000000464600000000000000d7020000000069070000000000000000"), can_bus.ECAN),
      (0x31A, bytes.fromhex("fa7c10f0f0ffff03898aff0b0a8678ff000000007e0055550000000000000000"), can_bus.ECAN),
    ]

    left_msgs = hyundaicanfd.create_ioniq_6_cluster_blindspot_messages(can_bus, 100, True, False)
    assert left_msgs == [
      (0x3B5, bytes.fromhex("e682c600000000464600000000000000da020000000069070000000000000000"), can_bus.ECAN),
      (0x31A, bytes.fromhex("c34129f0f0ffff03898aff0a098678ff000000007e0055550000000000000000"), can_bus.ECAN),
    ]

    both_msgs = hyundaicanfd.create_ioniq_6_cluster_blindspot_messages(can_bus, 0, True, True)
    assert both_msgs == []

  def test_ioniq_6_cluster_lane_change_helper_replays_stock_animation_family(self):
    CP = CarParams.new_message()
    CP.carFingerprint = CAR.HYUNDAI_IONIQ_6
    CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEERING)

    can_bus = CanBus(CP)

    assert hyundaicanfd.create_ioniq_6_cluster_lane_change_messages(can_bus, 1, "right") == []
    assert hyundaicanfd.create_ioniq_6_cluster_lane_change_messages(can_bus, 0, "right") == [
      (0x3C1, bytes.fromhex("e910300041000000"), can_bus.ECAN),
    ]
    assert hyundaicanfd.create_ioniq_6_cluster_lane_change_messages(can_bus, 4, "right") == [
      (0x3C1, bytes.fromhex("e910300041000000"), can_bus.ECAN),
      (0x3B5, bytes.fromhex("9f687600000000464600000000000000d7020000000069070000000000000000"), can_bus.ECAN),
    ]
    assert hyundaicanfd.create_ioniq_6_cluster_lane_change_messages(can_bus, 7, "right") == [
      (0x3C1, bytes.fromhex("ab20300001000000"), can_bus.ECAN),
    ]
    assert hyundaicanfd.create_ioniq_6_cluster_lane_change_messages(can_bus, 24, "right") == [
      (0x3B5, bytes.fromhex("d9317700000000464600000000000000d7020000000069070000000000000000"), can_bus.ECAN),
    ]
    assert hyundaicanfd.create_ioniq_6_cluster_lane_change_messages(can_bus, 30, "right") == [
      (0x31A, bytes.fromhex("eb4518f0f0ffff03898aff0a098678ff000000007e0055550000000000000000"), can_bus.ECAN),
    ]
    assert hyundaicanfd.create_ioniq_6_cluster_lane_change_messages(can_bus, 34, "right") == [
      (0x3C1, bytes.fromhex("ab20300001000000"), can_bus.ECAN),
    ]

    assert hyundaicanfd.create_ioniq_6_cluster_lane_change_messages(can_bus, 0, "left") == [
      (0x3C1, bytes.fromhex("3d40304010000000"), can_bus.ECAN),
    ]
    assert hyundaicanfd.create_ioniq_6_cluster_lane_change_messages(can_bus, 4, "left") == [
      (0x3C1, bytes.fromhex("3d40304010000000"), can_bus.ECAN),
      (0x3B5, bytes.fromhex("e682c600000000464600000000000000da020000000069070000000000000000"), can_bus.ECAN),
    ]
    assert hyundaicanfd.create_ioniq_6_cluster_lane_change_messages(can_bus, 7, "left") == [
      (0x3C1, bytes.fromhex("3e50300000000000"), can_bus.ECAN),
    ]
    assert hyundaicanfd.create_ioniq_6_cluster_lane_change_messages(can_bus, 30, "left") == [
      (0x31A, bytes.fromhex("851828f0f0ffff03898aff0a098678ff000000007e0055550000000000000000"), can_bus.ECAN),
    ]
    assert hyundaicanfd.create_ioniq_6_cluster_lane_change_messages(can_bus, 5, "none") == []

  def test_ioniq_5_canfd_aux_messages_are_optional(self):
    toggles = get_test_toggles()
    fingerprint = gen_empty_fingerprint()
    CP = CarInterface.get_params(CAR.HYUNDAI_IONIQ_5, fingerprint, [], False, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.HYUNDAI_IONIQ_5, fingerprint, [], CP, toggles)

    car_state = CarState(CP, FPCP)
    can_parsers = car_state.get_can_parsers(CP)
    packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])

    drive_mode_addr = packer.dbc.name_to_msg["DRIVE_MODE_EV"].address
    media_buttons_addr = packer.dbc.name_to_msg["STEERING_WHEEL_MEDIA_BUTTONS"].address

    assert can_parsers[Bus.pt].message_states[drive_mode_addr].ignore_alive
    assert can_parsers[Bus.pt].message_states[media_buttons_addr].ignore_alive

    for frame in range(1, 6):
      t = frame * 100_000_000
      for parser in can_parsers.values():
        required_msgs = [packer.make_can_msg(state.name, parser.bus, {})
                         for state in parser.message_states.values() if not state.ignore_alive]
        parser.update([(t, required_msgs)])

    assert all(parser.can_valid for parser in can_parsers.values())

  def test_blacklisted_parts(self, subtests):
    # Asserts no ECUs known to be shared across platforms exist in the database.
    # Tucson having Santa Cruz camera and EPS for example
    for car_model, ecus in FW_VERSIONS.items():
      with subtests.test(car_model=car_model.value):
        if car_model == CAR.HYUNDAI_SANTA_CRUZ_1ST_GEN:
          pytest.skip("Skip checking Santa Cruz for its parts")

        for code, _ in get_platform_codes(ecus[(Ecu.fwdCamera, 0x7c4, None)]):
          if b"-" not in code:
            continue
          part = code.split(b"-")[1]
          assert not part.startswith(b'CW'), "Car has bad part number"

  def test_correct_ecu_response_database(self, subtests):
    """
    Assert standard responses for certain ECUs, since they can
    respond to multiple queries with different data
    """
    expected_fw_prefix = HYUNDAI_VERSION_REQUEST_LONG[1:]
    for car_model, ecus in FW_VERSIONS.items():
      with subtests.test(car_model=car_model.value):
        for ecu, fws in ecus.items():
          assert all(fw.startswith(expected_fw_prefix) for fw in fws), \
                          f"FW from unexpected request in database: {(ecu, fws)}"

  @settings(max_examples=100)
  @given(data=st.data())
  def test_platform_codes_fuzzy_fw(self, data):
    """Ensure function doesn't raise an exception"""
    fw_strategy = st.lists(st.binary())
    fws = data.draw(fw_strategy)
    get_platform_codes(fws)

  def test_expected_platform_codes(self, subtests):
    # Ensures we don't accidentally add multiple platform codes for a car unless it is intentional
    for car_model, ecus in FW_VERSIONS.items():
      with subtests.test(car_model=car_model.value):
        for ecu, fws in ecus.items():
          if ecu[0] not in PLATFORM_CODE_ECUS:
            continue

          # Third and fourth character are usually EV/hybrid identifiers
          codes = {code.split(b"-")[0][:2] for code, _ in get_platform_codes(fws)}
          if car_model in (CAR.HYUNDAI_PALISADE, CAR.HYUNDAI_PALISADE_2023):
            assert codes == {b"LX", b"ON"}, f"Car has unexpected platform codes: {car_model} {codes}"
          elif car_model == CAR.HYUNDAI_KONA_EV and ecu[0] == Ecu.fwdCamera:
            assert codes == {b"OE", b"OS"}, f"Car has unexpected platform codes: {car_model} {codes}"
          else:
            assert len(codes) == 1, f"Car has multiple platform codes: {car_model} {codes}"

  # Tests for platform codes, part numbers, and FW dates which Hyundai will use to fuzzy
  # fingerprint in the absence of full FW matches:
  def test_platform_code_ecus_available(self, subtests):
    # TODO: add queries for these non-CAN FD cars to get EPS
    no_eps_platforms = CANFD_CAR | {CAR.KIA_SORENTO, CAR.KIA_OPTIMA_G4, CAR.KIA_OPTIMA_G4_FL, CAR.KIA_OPTIMA_H,
                                    CAR.KIA_OPTIMA_H_G4_FL, CAR.HYUNDAI_SONATA_LF, CAR.HYUNDAI_TUCSON, CAR.GENESIS_G90, CAR.GENESIS_G80,
                                    CAR.HYUNDAI_ELANTRA, CAR.KIA_RAY_EV}
    no_fwd_radar_platforms = {CAR.KIA_RAY_EV}

    # Asserts ECU keys essential for fuzzy fingerprinting are available on all platforms
    for car_model, ecus in FW_VERSIONS.items():
      with subtests.test(car_model=car_model.value):
        for platform_code_ecu in PLATFORM_CODE_ECUS:
          if platform_code_ecu in (Ecu.fwdRadar, Ecu.eps) and car_model == CAR.HYUNDAI_GENESIS:
            continue
          if platform_code_ecu == Ecu.fwdRadar and car_model in no_fwd_radar_platforms:
            continue
          if platform_code_ecu == Ecu.eps and car_model in no_eps_platforms:
            continue
          assert platform_code_ecu in [e[0] for e in ecus]

  def test_fw_format(self, subtests):
    # Asserts:
    # - every supported ECU FW version returns one platform code
    # - every supported ECU FW version has a part number
    # - expected parsing of ECU FW dates

    for car_model, ecus in FW_VERSIONS.items():
      with subtests.test(car_model=car_model.value):
        for ecu, fws in ecus.items():
          if ecu[0] not in PLATFORM_CODE_ECUS:
            continue

          codes = set()
          for fw in fws:
            result = get_platform_codes([fw])
            assert 1 == len(result), f"Unable to parse FW: {fw}"
            codes |= result

          if ecu[0] not in DATE_FW_ECUS or car_model in NO_DATES_PLATFORMS:
            assert all(date is None for _, date in codes)
          else:
            assert all(date is not None for _, date in codes)

          if car_model == CAR.HYUNDAI_GENESIS:
            pytest.skip("No part numbers for car model")

          # Hyundai places the ECU part number in their FW versions, assert all parsable
          # Some examples of valid formats: b"56310-L0010", b"56310L0010", b"56310/M6300"
          if car_model not in (CAR.KIA_SPORTAGE_2026, CAR.KIA_SPORTAGE_HEV_2026):
            assert all(b"-" in code for code, _ in codes), \
                            f"FW does not have part number: {fw}"

  def test_platform_codes_spot_check(self):
    # Asserts basic platform code parsing behavior for a few cases
    results = get_platform_codes([b"\xf1\x00DH LKAS 1.1 -150210"])
    assert results == {(b"DH", b"150210")}

    # Some cameras and all radars do not have dates
    results = get_platform_codes([b"\xf1\x00AEhe SCC H-CUP      1.01 1.01 96400-G2000         "])
    assert results == {(b"AEhe-G2000", None)}

    results = get_platform_codes([b"\xf1\x00CV1_ RDR -----      1.00 1.01 99110-CV000         "])
    assert results == {(b"CV1-CV000", None)}

    results = get_platform_codes([
      b"\xf1\x00DH LKAS 1.1 -150210",
      b"\xf1\x00AEhe SCC H-CUP      1.01 1.01 96400-G2000         ",
      b"\xf1\x00CV1_ RDR -----      1.00 1.01 99110-CV000         ",
    ])
    assert results == {(b"DH", b"150210"), (b"AEhe-G2000", None), (b"CV1-CV000", None)}

    results = get_platform_codes([
      b"\xf1\x00LX2 MFC  AT USA LHD 1.00 1.07 99211-S8100 220222",
      b"\xf1\x00LX2 MFC  AT USA LHD 1.00 1.08 99211-S8100 211103",
      b"\xf1\x00ON  MFC  AT USA LHD 1.00 1.01 99211-S9100 190405",
      b"\xf1\x00ON  MFC  AT USA LHD 1.00 1.03 99211-S9100 190720",
    ])
    assert results == {(b"LX2-S8100", b"220222"), (b"LX2-S8100", b"211103"),
                               (b"ON-S9100", b"190405"), (b"ON-S9100", b"190720")}

  def test_fuzzy_excluded_platforms(self):
    # Asserts a list of platforms that will not fuzzy fingerprint with platform codes due to them being shared.
    # This list can be shrunk as we combine platforms and detect features
    excluded_platforms = {
      CAR.GENESIS_G70,            # shared platform code, part number, and date
      CAR.GENESIS_G70_2020,
    }
    excluded_platforms |= CANFD_CAR - EV_CAR - CANFD_FUZZY_WHITELIST  # shared platform codes
    excluded_platforms |= NO_DATES_PLATFORMS - DATELESS_FUZZY_CARS

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
        platforms_with_shared_codes.add(platform)

    assert platforms_with_shared_codes == excluded_platforms
