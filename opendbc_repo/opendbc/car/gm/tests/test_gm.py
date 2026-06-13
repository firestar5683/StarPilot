import pytest
from types import SimpleNamespace
from parameterized import parameterized

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, DT_CTRL, structs
from opendbc.car.car_helpers import interfaces
from opendbc.car.gm import gmcan
from opendbc.car.gm.carstate import CarState as GMCarState, get_hard_cruise_buttons
from opendbc.car.gm.carcontroller import (
  VisualAlert,
  get_acc_dashboard_fcw_alert,
  get_acc_dashboard_status_values,
  should_send_acc_dashboard_status,
  should_send_cc_button_spam,
  should_spoof_dash_speed,
)
import opendbc.car.gm.interface as gm_interface
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.gm.fingerprints import FINGERPRINTS
from opendbc.car.gm.values import CAMERA_ACC_CAR, CAR, CC_ONLY_CAR, DBC, GM_RX_OFFSET, CruiseButtons, GMFlags, GMSafetyFlags
from opendbc.safety import ALTERNATIVE_EXPERIENCE
from openpilot.common.params import Params

CAMERA_DIAGNOSTIC_ADDRESS = 0x24b
VOLT_CARS = (
  CAR.CHEVROLET_VOLT,
  CAR.CHEVROLET_VOLT_2019,
  CAR.CHEVROLET_VOLT_ASCM,
  CAR.CHEVROLET_VOLT_CAMERA,
  CAR.CHEVROLET_VOLT_CC,
)


def _empty_fingerprint():
  return {bus: {} for bus in range(8)}


def _test_starpilot_toggles():
  return SimpleNamespace(
    car_model="",
    cluster_offset=1.0,
    disable_openpilot_long=False,
    force_fingerprint=False,
    remap_cancel_to_distance=False,
    vEgoStopping=0.5,
    volt_sng=False,
  )


class TestGMFingerprint:
  @parameterized.expand(FINGERPRINTS.items())
  def test_can_fingerprints(self, car_model, fingerprints):
    assert len(fingerprints) > 0

    assert all(len(finger) for finger in fingerprints)

    # The camera can sometimes be communicating on startup
    if car_model in CAMERA_ACC_CAR - CC_ONLY_CAR:
      for finger in fingerprints:
        for required_addr in (CAMERA_DIAGNOSTIC_ADDRESS, CAMERA_DIAGNOSTIC_ADDRESS + GM_RX_OFFSET):
          assert finger.get(required_addr) == 8, required_addr


class TestGMInterface:
  def test_missing_hard_cruise_signal_defaults_to_init(self):
    assert get_hard_cruise_buttons({"ACCButtons": CruiseButtons.RES_ACCEL}) == CruiseButtons.INIT
    assert get_hard_cruise_buttons({"ACCButtonsHard": CruiseButtons.DECEL_SET}) == CruiseButtons.DECEL_SET

  @parameterized.expand(VOLT_CARS)
  def test_volt_min_steer_speed_is_7_mph(self, car_model):
    CarInterface = interfaces[car_model]
    car_params = CarInterface.get_params(car_model, _empty_fingerprint(), [], alpha_long=False, is_release=False, docs=False,
                                         starpilot_toggles=_test_starpilot_toggles())

    assert car_params.minSteerSpeed == pytest.approx(7 * CV.MPH_TO_MS)

  @parameterized.expand([
    ("interceptor", True),
    ("ascm_int", False),
  ])
  def test_volt_testing_ground_tune_sets_nonzero_p_and_starting_state(self, _name, pedal_present):
    CarInterface = interfaces[CAR.CHEVROLET_VOLT_ASCM]
    fingerprint = _empty_fingerprint()
    if pedal_present:
      fingerprint[0][0x201] = 8  # pedal detected
    fingerprint[0][0x2FF] = 8  # SASCM detected

    old_testing_ground = gm_interface.testing_ground
    gm_interface.testing_ground = SimpleNamespace(use_2=True)

    try:
      car_params = CarInterface.get_params(CAR.CHEVROLET_VOLT_ASCM, fingerprint, [], alpha_long=False, is_release=False, docs=False,
                                           starpilot_toggles=_test_starpilot_toggles())
    finally:
      gm_interface.testing_ground = old_testing_ground

    if pedal_present:
      assert list(car_params.longitudinalTuning.kpV) == pytest.approx([0.10, 0.072, 0.05, 0.04])
      assert list(car_params.longitudinalTuning.kiV) == pytest.approx([0.025, 0.03, 0.04, 0.055])
      assert car_params.startingState
      assert car_params.startAccel == pytest.approx(1.15)
    else:
      assert not car_params.openpilotLongitudinalControl
      assert not car_params.enableGasInterceptorDEPRECATED
      assert list(car_params.longitudinalTuning.kpV) == [0.0]
      assert list(car_params.longitudinalTuning.kiV) == [0.5, 0.5]
      assert not car_params.startingState
      assert car_params.startAccel == pytest.approx(0.0)

  def test_volt_cc_sparse_fingerprint_without_camera_sets_no_camera(self):
    CarInterface = interfaces[CAR.CHEVROLET_VOLT_CC]
    fingerprint = {
      0: FINGERPRINTS[CAR.CHEVROLET_VOLT][0].copy(),
      1: {},
    }

    car_params = CarInterface.get_params(CAR.CHEVROLET_VOLT_CC, fingerprint, [], alpha_long=False, is_release=False, docs=False,
                                         starpilot_toggles=_test_starpilot_toggles())

    assert car_params.flags & GMFlags.NO_CAMERA.value
    assert car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_NO_CAMERA.value

  def test_silverado_alpha_long_uses_trimmed_longitudinal_tune(self):
    CarInterface = interfaces[CAR.CHEVROLET_SILVERADO]
    fingerprint = _empty_fingerprint()
    fingerprint[0] = FINGERPRINTS[CAR.CHEVROLET_SILVERADO][0].copy()

    car_params = CarInterface.get_params(CAR.CHEVROLET_SILVERADO, fingerprint, [], alpha_long=True, is_release=False,
                                         docs=False, starpilot_toggles=_test_starpilot_toggles())

    assert car_params.openpilotLongitudinalControl
    assert not car_params.enableGasInterceptorDEPRECATED
    assert list(car_params.longitudinalTuning.kpBP) == pytest.approx([0.0, 5.0, 15.0, 35.0])
    assert list(car_params.longitudinalTuning.kpV) == pytest.approx([0.02, 0.03, 0.028, 0.022])
    assert list(car_params.longitudinalTuning.kiBP) == pytest.approx([0.0, 5.0, 15.0, 35.0])
    assert list(car_params.longitudinalTuning.kiV) == pytest.approx([0.28, 0.26, 0.20, 0.16])

  def test_volt_gateway_without_accel_pos_uses_brake_pedal_message(self):
    CarInterface = interfaces[CAR.CHEVROLET_VOLT]
    fingerprint = _empty_fingerprint()
    fingerprint[0][0xF1] = 6

    car_params = CarInterface.get_params(CAR.CHEVROLET_VOLT, fingerprint, [], alpha_long=False, is_release=False, docs=False,
                                         starpilot_toggles=_test_starpilot_toggles())

    assert car_params.flags & GMFlags.NO_ACCELERATOR_POS_MSG.value
    assert car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_NO_CAMERA.value

    pt_parser = CarInterface.CarState.get_can_parsers(car_params)[Bus.pt]
    assert "ECMAcceleratorPos" not in pt_parser.vl
    assert "EBCMBrakePedalPosition" in pt_parser.vl

  def test_volt_auto_hold_sets_stock_hold_safety_bit_with_op_long_enabled(self):
    CarInterface = interfaces[CAR.CHEVROLET_VOLT_ASCM]
    fingerprint = _empty_fingerprint()
    fingerprint[0][0x2FF] = 8

    params = Params()
    try:
      params.put_bool("GMAutoHold", True)
      car_params = CarInterface.get_params(CAR.CHEVROLET_VOLT_ASCM, fingerprint, [], alpha_long=True, is_release=False,
                                           docs=False, starpilot_toggles=_test_starpilot_toggles())
    finally:
      params.remove("GMAutoHold")

    assert car_params.openpilotLongitudinalControl
    assert car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_PANDA_PADDLE_SCHED.value

  @parameterized.expand(VOLT_CARS)
  def test_volt_bsm_is_enabled_without_fingerprint_match(self, car_model):
    CarInterface = interfaces[car_model]
    car_params = CarInterface.get_params(car_model, _empty_fingerprint(), [], alpha_long=False, is_release=False, docs=False,
                                         starpilot_toggles=_test_starpilot_toggles())

    assert car_params.enableBsm

  def test_volt_bsm_parser_is_optional(self):
    cp = SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT_ASCM,
      networkLocation=structs.CarParams.NetworkLocation.fwdCamera,
      flags=0,
      transmissionType=structs.CarParams.TransmissionType.direct,
      enableGasInterceptorDEPRECATED=False,
      enableBsm=True,
    )

    pt_parser = GMCarState.get_can_parsers(cp)[Bus.pt]
    bsm_addr = pt_parser.dbc.name_to_msg["BCMBlindSpotMonitor"].address

    assert "BCMBlindSpotMonitor" in pt_parser.vl
    assert pt_parser.message_states[bsm_addr].ignore_alive

  def test_volt_ascm_cam_parser_includes_optional_aeb_cmd(self):
    cam_parser = GMCarState.get_can_parsers(SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT_ASCM,
      networkLocation=structs.CarParams.NetworkLocation.fwdCamera,
      flags=0,
      transmissionType=structs.CarParams.TransmissionType.direct,
      enableGasInterceptorDEPRECATED=False,
      enableBsm=False,
    ))[Bus.cam]
    aeb_addr = cam_parser.dbc.name_to_msg["AEBCmd"].address

    assert "AEBCmd" in cam_parser.vl
    assert cam_parser.message_states[aeb_addr].ignore_alive

  def test_bolt_gen2_pedal_cancel_remap_sets_alt_exp(self):
    CarInterface = interfaces[CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL]
    fingerprint = _empty_fingerprint()
    fingerprint[0][0x201] = 8

    params = Params()
    toggles = _test_starpilot_toggles()
    try:
      params.put_bool("RemapCancelToDistance", True)
      car_params = CarInterface.get_params(CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL, fingerprint, [], alpha_long=False,
                                           is_release=False, docs=False, starpilot_toggles=toggles)
    finally:
      params.remove("RemapCancelToDistance")

    assert car_params.alternativeExperience & ALTERNATIVE_EXPERIENCE.GM_REMAP_CANCEL_TO_DISTANCE
    assert car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_BOLT_2022_PEDAL.value

  def test_cadillac_xt5_sdgm_sascm_gates_alpha_long(self):
    CarInterface = interfaces[CAR.CADILLAC_XT5]
    fingerprint = _empty_fingerprint()
    fingerprint[0][0xBE] = 6

    stock_params = CarInterface.get_params(CAR.CADILLAC_XT5, fingerprint, [], alpha_long=True, is_release=False,
                                           docs=False, starpilot_toggles=_test_starpilot_toggles())

    assert stock_params.networkLocation == structs.CarParams.NetworkLocation.fwdCamera
    assert stock_params.pcmCruise
    assert stock_params.alphaLongitudinalAvailable is False
    assert stock_params.openpilotLongitudinalControl is False
    assert stock_params.safetyConfigs[0].safetyParam & GMSafetyFlags.HW_SDGM.value

    fingerprint[0][0x2FF] = 8
    sascm_params = CarInterface.get_params(CAR.CADILLAC_XT5, fingerprint, [], alpha_long=True, is_release=False,
                                           docs=False, starpilot_toggles=_test_starpilot_toggles())

    assert sascm_params.flags & GMFlags.SASCM.value
    assert sascm_params.alphaLongitudinalAvailable
    assert sascm_params.openpilotLongitudinalControl
    assert not sascm_params.pcmCruise
    assert sascm_params.safetyConfigs[0].safetyParam & GMSafetyFlags.HW_CAM_LONG.value


class TestGMCarController:
  def test_dash_speed_spoof_respects_live_stock_acc_toggles(self):
    cp = SimpleNamespace(openpilotLongitudinalControl=True, enableGasInterceptorDEPRECATED=True)

    assert should_spoof_dash_speed(cp, SimpleNamespace(disable_openpilot_long=False, gm_pedal_longitudinal=True))
    assert not should_spoof_dash_speed(cp, SimpleNamespace(disable_openpilot_long=True, gm_pedal_longitudinal=True))
    assert not should_spoof_dash_speed(cp, SimpleNamespace(disable_openpilot_long=False, gm_pedal_longitudinal=False))

  def test_dash_speed_spoof_allows_non_pedal_long_when_op_long_enabled(self):
    cp = SimpleNamespace(openpilotLongitudinalControl=True, enableGasInterceptorDEPRECATED=False)

    assert should_spoof_dash_speed(cp, SimpleNamespace(disable_openpilot_long=False))

  def test_volt_camera_no_camera_sends_acc_dashboard_without_dash_spoof(self):
    cp = SimpleNamespace(carFingerprint=CAR.CHEVROLET_VOLT_CAMERA, flags=GMFlags.NO_CAMERA.value)

    assert should_send_acc_dashboard_status(cp, dash_speed_spoof_active=False)

  def test_acc_dashboard_no_camera_exception_is_volt_camera_only(self):
    assert not should_send_acc_dashboard_status(
      SimpleNamespace(carFingerprint=CAR.CHEVROLET_VOLT_CAMERA, flags=0),
      dash_speed_spoof_active=False,
    )
    assert not should_send_acc_dashboard_status(
      SimpleNamespace(carFingerprint=CAR.CHEVROLET_VOLT_CC, flags=GMFlags.NO_CAMERA.value),
      dash_speed_spoof_active=False,
    )

  def test_cc_button_spam_does_not_require_stock_cruise_enabled(self):
    cp = SimpleNamespace(flags=GMFlags.CC_LONG.value, minEnableSpeed=10.0)
    cc = SimpleNamespace(longActive=True)
    cs = SimpleNamespace(out=SimpleNamespace(vEgo=11.0, cruiseState=SimpleNamespace(enabled=False)))

    assert should_send_cc_button_spam(cp, cc, cs)

  def test_cc_button_spam_requires_cc_long_and_speed(self):
    cc = SimpleNamespace(longActive=True)
    cs = SimpleNamespace(out=SimpleNamespace(vEgo=9.0, cruiseState=SimpleNamespace(enabled=True)))

    assert not should_send_cc_button_spam(SimpleNamespace(flags=GMFlags.CC_LONG.value, minEnableSpeed=10.0), cc, cs)
    assert not should_send_cc_button_spam(SimpleNamespace(flags=0, minEnableSpeed=10.0), cc, cs)

  def test_volt_cc_redneck_spam_is_mirrored_to_camera_bus(self):
    packer = CANPacker(DBC[CAR.CHEVROLET_VOLT_CC][Bus.pt])
    controller = SimpleNamespace(frame=int(0.3 / DT_CTRL), last_button_frame=0, apply_speed=0, malibu_button_phase=0)
    cs = SimpleNamespace(
      CP=SimpleNamespace(
        carFingerprint=CAR.CHEVROLET_VOLT_CC,
        flags=0,
        minEnableSpeed=24 * CV.MPH_TO_MS,
      ),
      buttons_counter=2,
      out=SimpleNamespace(
        vEgo=25.0,
        cruiseState=SimpleNamespace(speed=20.0),
      ),
    )
    actuators = SimpleNamespace(accel=1.0)

    msgs = gmcan.create_gm_cc_spam_command(packer, controller, cs, actuators, SimpleNamespace(is_metric=False))

    assert [msg[2] for msg in msgs] == [0, 2]

  def test_volt_cc_no_camera_redneck_spam_stays_on_powertrain_bus(self):
    packer = CANPacker(DBC[CAR.CHEVROLET_VOLT_CC][Bus.pt])
    controller = SimpleNamespace(frame=int(0.3 / DT_CTRL), last_button_frame=0, apply_speed=0, malibu_button_phase=0)
    cs = SimpleNamespace(
      CP=SimpleNamespace(
        carFingerprint=CAR.CHEVROLET_VOLT_CC,
        flags=GMFlags.NO_CAMERA.value,
        minEnableSpeed=24 * CV.MPH_TO_MS,
      ),
      buttons_counter=2,
      out=SimpleNamespace(
        vEgo=25.0,
        cruiseState=SimpleNamespace(speed=20.0),
      ),
    )
    actuators = SimpleNamespace(accel=1.0)

    msgs = gmcan.create_gm_cc_spam_command(packer, controller, cs, actuators, SimpleNamespace(is_metric=False))

    assert [msg[2] for msg in msgs] == [0]

  def test_non_volt_cc_redneck_spam_stays_on_powertrain_bus(self):
    packer = CANPacker(DBC[CAR.CHEVROLET_BOLT_CC_2018_2021][Bus.pt])
    controller = SimpleNamespace(frame=int(0.3 / DT_CTRL), last_button_frame=0, apply_speed=0, malibu_button_phase=0)
    cs = SimpleNamespace(
      CP=SimpleNamespace(
        carFingerprint=CAR.CHEVROLET_BOLT_CC_2018_2021,
        flags=GMFlags.CC_LONG.value,
        minEnableSpeed=24 * CV.MPH_TO_MS,
      ),
      buttons_counter=2,
      out=SimpleNamespace(
        vEgo=25.0,
        cruiseState=SimpleNamespace(speed=20.0),
      ),
    )
    actuators = SimpleNamespace(accel=1.0)

    msgs = gmcan.create_gm_cc_spam_command(packer, controller, cs, actuators, SimpleNamespace(is_metric=False))

    assert [msg[2] for msg in msgs] == [0]

  def test_acc_dashboard_command_preserves_raw_fcw_alert_level(self):
    packer = CANPacker(DBC[CAR.CHEVROLET_BOLT_ACC_2022_2023][Bus.pt])
    parser = CANParser(DBC[CAR.CHEVROLET_BOLT_ACC_2022_2023][Bus.pt], [("ASCMActiveCruiseControlStatus", 0)], 0)
    msg = gmcan.create_acc_dashboard_command(
      packer,
      0,
      {
        "ACCCruiseState": 0,
        "ACCLeadCar": 1,
        "ACCResumeButton": 0,
        "ACCSpeedSetpoint": 100,
        "ACCGapLevel": 3,
        "ACCCmdActive": 1,
      },
      0x2,
    )

    parser.update([0, [msg]])

    assert parser.vl["ASCMActiveCruiseControlStatus"]["FCWAlert"] == 2

  def test_acc_dashboard_command_can_replay_stock_status_payload(self):
    packer = CANPacker(DBC[CAR.CHEVROLET_VOLT_ASCM][Bus.pt])
    msg = gmcan.create_acc_dashboard_command(
      packer,
      0,
      {
        "ACCCruiseState": 0,
        "ACCLeadCar": 1,
        "ACCResumeButton": 0,
        "ACCSpeedSetpoint": 50,
        "ACCGapLevel": 2,
        "ACCCmdActive": 0,
      },
      0x3,
    )

    assert msg[1].hex() == "010023200113"

  def test_acc_dashboard_fcw_alert_prefers_openpilot_alert(self):
    cs = SimpleNamespace(
      stock_fcw_alert=1,
      out=SimpleNamespace(stockAeb=False, stockFcw=False),
    )

    assert get_acc_dashboard_fcw_alert(VisualAlert.fcw, cs) == 0x3

  def test_acc_dashboard_fcw_alert_replays_stock_camera_alert_level(self):
    cs = SimpleNamespace(
      stock_fcw_alert=2,
      out=SimpleNamespace(stockAeb=False, stockFcw=False),
    )

    assert get_acc_dashboard_fcw_alert(VisualAlert.none, cs) == 2

  def test_acc_dashboard_fcw_alert_falls_back_to_stock_aeb_event(self):
    cs = SimpleNamespace(
      stock_fcw_alert=0,
      out=SimpleNamespace(stockAeb=True, stockFcw=False),
    )

    assert get_acc_dashboard_fcw_alert(VisualAlert.none, cs) == 0x3

  def test_acc_dashboard_fcw_alert_falls_back_to_stock_fcw_event(self):
    cs = SimpleNamespace(
      stock_fcw_alert=0,
      out=SimpleNamespace(stockAeb=False, stockFcw=True),
    )

    assert get_acc_dashboard_fcw_alert(VisualAlert.none, cs) == 0x3

  def test_acc_dashboard_status_values_use_openpilot_hud_when_enabled(self):
    cs = SimpleNamespace(
      stock_acc_cruise_state=5,
      stock_acc_lead_car=0,
      stock_acc_resume_button=1,
      stock_acc_speed_setpoint_kph=42.0,
      stock_acc_gap_level=1,
      stock_acc_cmd_active=0,
    )

    values = get_acc_dashboard_status_values(True, 105.0, SimpleNamespace(leadDistanceBars=3, leadVisible=True), cs)

    assert values == {
      "ACCCruiseState": 0,
      "ACCLeadCar": 1,
      "ACCResumeButton": 0,
      "ACCSpeedSetpoint": 105.0,
      "ACCGapLevel": 3,
      "ACCCmdActive": 1,
    }

  def test_acc_dashboard_status_values_reuse_stock_camera_status_when_disabled(self):
    cs = SimpleNamespace(
      stock_acc_cruise_state=0,
      stock_acc_lead_car=1,
      stock_acc_resume_button=0,
      stock_acc_speed_setpoint_kph=50.0,
      stock_acc_gap_level=2,
      stock_acc_cmd_active=0,
    )

    values = get_acc_dashboard_status_values(False, 0.0, SimpleNamespace(leadDistanceBars=0, leadVisible=False), cs)

    assert values == {
      "ACCCruiseState": 0,
      "ACCLeadCar": 1,
      "ACCResumeButton": 0,
      "ACCSpeedSetpoint": 50.0,
      "ACCGapLevel": 2,
      "ACCCmdActive": 0,
    }
