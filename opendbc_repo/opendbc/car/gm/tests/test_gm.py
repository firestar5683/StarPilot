import pytest
import numpy as np
from types import SimpleNamespace
from parameterized import parameterized

from cereal import custom
from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, DT_CTRL, structs
from opendbc.car.car_helpers import interfaces
from opendbc.car.gm import gmcan
from opendbc.car.gm.carstate import CarState as GMCarState, get_hard_cruise_buttons, update_auto_hold_drive_timers
from opendbc.car.gm.carcontroller import (
  VisualAlert,
  get_acc_dashboard_always_one,
  get_acc_dashboard_fcw_alert,
  get_volt_one_pedal_lift_brake,
  should_send_acc_dashboard_status,
  should_send_cc_button_spam,
  should_spoof_dash_speed,
)
import opendbc.car.gm.interface as gm_interface
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.gm.fingerprints import FINGERPRINTS
from opendbc.car.gm.values import ASCM_INT, CAMERA_ACC_CAR, CAR, CC_ONLY_CAR, DBC, GM_RX_OFFSET, CarControllerParams, CruiseButtons, GMFlags, GMSafetyFlags
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
  @parameterized.expand([
    CAR.CHEVROLET_BOLT_CC_2017,
    CAR.CHEVROLET_BOLT_CC_2018_2021,
    CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
    CAR.CHEVROLET_BOLT_CC_2022_2023,
    CAR.CHEVROLET_MALIBU_HYBRID_CC,
  ])
  def test_bolt_pedal_long_uses_shared_planning_delay_without_retuning_pid(self, car_model):
    CarInterface = interfaces[car_model]
    fingerprint = _empty_fingerprint()
    fingerprint[0][0x201] = 8
    params = Params()

    try:
      params.put_bool("GMPedalLongitudinal", True)
      car_params = CarInterface.get_params(
        car_model,
        fingerprint,
        [],
        alpha_long=False,
        is_release=False,
        docs=False,
        starpilot_toggles=_test_starpilot_toggles(),
      )
    finally:
      params.remove("GMPedalLongitudinal")

    assert car_params.longitudinalActuatorDelay == pytest.approx(0.6)
    assert list(car_params.longitudinalTuning.kpV) == pytest.approx([0.095, 0.085, 0.065, 0.050])
    assert list(car_params.longitudinalTuning.kiV) == pytest.approx([0.07, 0.10, 0.15, 0.24])
    assert car_params.longitudinalTuning.kfDEPRECATED == pytest.approx(0.20)

  def test_bolt_acc_pedal_pid_accel_limits_keep_full_negative_authority(self):
    cp = SimpleNamespace(
      enableGasInterceptorDEPRECATED=True,
      flags=GMFlags.PEDAL_LONG.value,
      carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
    )

    accel_min, accel_max = gm_interface.CarInterface.get_pid_accel_limits(cp, 4.73, 0.0)

    assert accel_min == pytest.approx(CarControllerParams.ACCEL_MIN)
    assert accel_max == pytest.approx(np.interp(4.73, [0.0, 1.5, 4.0, 8.0, 15.0],
                                                [0.54, 0.74, 1.03, 1.46, CarControllerParams.ACCEL_MAX]))

  def test_bolt_cc_pedal_pid_accel_limits_remain_regen_limited(self):
    cp = SimpleNamespace(
      enableGasInterceptorDEPRECATED=True,
      flags=GMFlags.PEDAL_LONG.value,
      carFingerprint=CAR.CHEVROLET_BOLT_CC_2022_2023,
    )

    accel_min, _ = gm_interface.CarInterface.get_pid_accel_limits(cp, 4.73, 0.0)

    assert accel_min == pytest.approx(np.interp(4.73, [0.0, 1.5, 4.0, 8.0, 15.0, 30.0],
                                                [-0.93, -1.28, -1.98, -2.58, -2.86, -2.95]))

  def test_missing_hard_cruise_signal_defaults_to_init(self):
    assert get_hard_cruise_buttons({"ACCButtons": CruiseButtons.RES_ACCEL}) == CruiseButtons.INIT
    assert get_hard_cruise_buttons({"ACCButtonsHard": CruiseButtons.DECEL_SET}) == CruiseButtons.DECEL_SET

  def test_volt_auto_hold_drive_timer_requires_motion_before_startup_arming(self):
    auto_hold_time, one_pedal_time = update_auto_hold_drive_timers(True, False, 0.0, 0.0)

    assert auto_hold_time == 0.0
    assert one_pedal_time == 0.0

  def test_volt_auto_hold_drive_timer_accumulates_only_while_moving(self):
    auto_hold_time, one_pedal_time = update_auto_hold_drive_timers(True, True, 0.0, 0.0)

    assert auto_hold_time == pytest.approx(DT_CTRL)
    assert one_pedal_time == pytest.approx(DT_CTRL)

    auto_hold_time, one_pedal_time = update_auto_hold_drive_timers(True, False, auto_hold_time, one_pedal_time)

    assert auto_hold_time == pytest.approx(DT_CTRL)
    assert one_pedal_time == pytest.approx(DT_CTRL)

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
    params = Params()
    params.put_bool("GMPedalLongitudinal", True)

    try:
      car_params = CarInterface.get_params(CAR.CHEVROLET_VOLT_ASCM, fingerprint, [], alpha_long=False, is_release=False, docs=False,
                                           starpilot_toggles=_test_starpilot_toggles())
    finally:
      gm_interface.testing_ground = old_testing_ground
      params.remove("GMPedalLongitudinal")

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

  def test_volt_ascm_sparse_fingerprint_without_camera_does_not_set_no_camera(self):
    CarInterface = interfaces[CAR.CHEVROLET_VOLT_ASCM]
    fingerprint = {
      0: FINGERPRINTS[CAR.CHEVROLET_VOLT][0].copy(),
      1: {},
    }
    fingerprint[0][0x2FF] = 8  # SASCM detected

    car_params = CarInterface.get_params(CAR.CHEVROLET_VOLT_ASCM, fingerprint, [], alpha_long=False, is_release=False,
                                         docs=False, starpilot_toggles=_test_starpilot_toggles())

    assert not (car_params.flags & GMFlags.NO_CAMERA.value)
    assert not (car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_NO_CAMERA.value)
    assert car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.HW_ASCM_INT.value

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
    assert list(car_params.longitudinalTuning.kiV) == pytest.approx([0.20, 0.18, 0.13, 0.08])

  def test_blazer_uses_softer_low_speed_stop_hold_tune(self):
    CarInterface = interfaces[CAR.CHEVROLET_BLAZER]
    fingerprint = _empty_fingerprint()
    fingerprint[0] = FINGERPRINTS[CAR.CHEVROLET_BLAZER][0].copy()
    fingerprint[0][0x2FF] = 8  # SASCM present so alpha-long can enable on this platform

    car_params = CarInterface.get_params(CAR.CHEVROLET_BLAZER, fingerprint, [], alpha_long=True, is_release=False,
                                         docs=False, starpilot_toggles=_test_starpilot_toggles())

    assert car_params.openpilotLongitudinalControl
    assert list(car_params.longitudinalTuning.kpBP) == pytest.approx([0.0, 4.0, 12.0, 35.0])
    assert list(car_params.longitudinalTuning.kpV) == pytest.approx([0.09, 0.075, 0.055, 0.04])
    assert list(car_params.longitudinalTuning.kiBP) == pytest.approx([0.0, 4.0, 12.0, 35.0])
    assert list(car_params.longitudinalTuning.kiV) == pytest.approx([0.03, 0.04, 0.055, 0.07])
    assert car_params.longitudinalActuatorDelay == pytest.approx(0.7)
    assert car_params.minEnableSpeed == pytest.approx(5 * CV.KPH_TO_MS)
    assert car_params.stoppingDecelRate == pytest.approx(1.0)
    assert car_params.vEgoStopping == pytest.approx(0.35)
    assert car_params.vEgoStarting == pytest.approx(0.35)
    assert car_params.stopAccel == pytest.approx(-0.30)

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

  def test_volt_auto_hold_does_not_set_stock_hold_safety_bit_with_op_long_disabled(self):
    CarInterface = interfaces[CAR.CHEVROLET_VOLT_ASCM]
    fingerprint = _empty_fingerprint()
    fingerprint[0][0x2FF] = 8

    params = Params()
    try:
      params.put_bool("GMAutoHold", True)
      car_params = CarInterface.get_params(CAR.CHEVROLET_VOLT_ASCM, fingerprint, [], alpha_long=False, is_release=False,
                                           docs=False, starpilot_toggles=_test_starpilot_toggles())
    finally:
      params.remove("GMAutoHold")

    assert not car_params.openpilotLongitudinalControl
    assert not (car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_PANDA_PADDLE_SCHED.value)

  def test_volt_one_pedal_sets_stock_hold_safety_bit_without_auto_hold(self):
    CarInterface = interfaces[CAR.CHEVROLET_VOLT_ASCM]
    fingerprint = _empty_fingerprint()
    fingerprint[0][0x2FF] = 8

    params = Params()
    try:
      params.put_bool("GMAutoHold", False)
      params.put_bool("VoltOnePedalMode", True)
      car_params = CarInterface.get_params(CAR.CHEVROLET_VOLT_ASCM, fingerprint, [], alpha_long=True, is_release=False,
                                           docs=False, starpilot_toggles=_test_starpilot_toggles())
    finally:
      params.remove("GMAutoHold")
      params.remove("VoltOnePedalMode")

    assert car_params.openpilotLongitudinalControl
    assert car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_PANDA_PADDLE_SCHED.value
    assert car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_PANDA_3D1_SCHED.value

  def test_volt_one_pedal_does_not_set_stock_hold_safety_bits_with_op_long_disabled(self):
    CarInterface = interfaces[CAR.CHEVROLET_VOLT_ASCM]
    fingerprint = _empty_fingerprint()
    fingerprint[0][0x2FF] = 8

    params = Params()
    try:
      params.put_bool("GMAutoHold", False)
      params.put_bool("VoltOnePedalMode", True)
      car_params = CarInterface.get_params(CAR.CHEVROLET_VOLT_ASCM, fingerprint, [], alpha_long=False, is_release=False,
                                           docs=False, starpilot_toggles=_test_starpilot_toggles())
    finally:
      params.remove("GMAutoHold")
      params.remove("VoltOnePedalMode")

    assert not car_params.openpilotLongitudinalControl
    assert not (car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_PANDA_PADDLE_SCHED.value)
    assert not (car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_PANDA_3D1_SCHED.value)

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
      params.put_bool("GMPedalLongitudinal", True)
      params.put_bool("RemapCancelToDistance", True)
      car_params = CarInterface.get_params(CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL, fingerprint, [], alpha_long=False,
                                           is_release=False, docs=False, starpilot_toggles=toggles)
    finally:
      params.remove("GMPedalLongitudinal")
      params.remove("RemapCancelToDistance")

    assert car_params.alternativeExperience & ALTERNATIVE_EXPERIENCE.GM_REMAP_CANCEL_TO_DISTANCE
    assert car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_BOLT_2022_PEDAL.value
    assert car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.FLAG_GM_PANDA_PADDLE_SCHED.value
    assert car_params.startingState
    assert car_params.startAccel == pytest.approx(0.55)
    assert car_params.vEgoStarting == pytest.approx(0.35)

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

  def test_cadillac_escalade_esv_2019_ascm_uses_sascm_and_2019_tune(self):
    base_fingerprint = FINGERPRINTS[CAR.CADILLAC_ESCALADE_ESV_2019][0]
    ascm_fingerprint = FINGERPRINTS[CAR.CADILLAC_ESCALADE_ESV_2019_ASCM][0]

    assert CAR.CADILLAC_ESCALADE_ESV_2019_ASCM in ASCM_INT
    assert ascm_fingerprint[0x2FF] == 8
    assert {addr: length for addr, length in ascm_fingerprint.items() if addr != 0x2FF} == base_fingerprint

    CarInterface = interfaces[CAR.CADILLAC_ESCALADE_ESV_2019_ASCM]
    fingerprint = _empty_fingerprint()
    fingerprint[0] = ascm_fingerprint.copy()

    car_params = CarInterface.get_params(CAR.CADILLAC_ESCALADE_ESV_2019_ASCM, fingerprint, [], alpha_long=True, is_release=False,
                                         docs=False, starpilot_toggles=_test_starpilot_toggles())

    assert car_params.flags & GMFlags.SASCM.value
    assert car_params.networkLocation == structs.CarParams.NetworkLocation.fwdCamera
    assert car_params.openpilotLongitudinalControl
    assert not car_params.pcmCruise
    assert car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.HW_ASCM_INT.value
    assert car_params.safetyConfigs[0].safetyParam & GMSafetyFlags.HW_CAM_LONG.value
    assert car_params.lateralTuning.torque.latAccelFactor == pytest.approx(1.15)
    assert car_params.lateralTuning.torque.friction == pytest.approx(0.2)

  def test_cadillac_xt4_uses_nonlinear_torque_curve_with_center_boost(self):
    CarInterface = interfaces[CAR.CADILLAC_XT4]
    car_params = CarInterface.get_non_essential_params(CAR.CADILLAC_XT4)
    ci = CarInterface(car_params, custom.StarPilotCarParams.new_message())
    torque_from_lataccel = ci.torque_from_lateral_accel()

    low_lataccel = 0.2
    high_lataccel = 1.0
    low_torque = torque_from_lataccel(low_lataccel, car_params.lateralTuning.torque)
    high_torque = torque_from_lataccel(high_lataccel, car_params.lateralTuning.torque)

    linear_low_torque = low_lataccel / car_params.lateralTuning.torque.latAccelFactor
    linear_high_torque = high_lataccel / car_params.lateralTuning.torque.latAccelFactor

    assert low_torque > linear_low_torque * 1.15
    assert low_torque < linear_low_torque * 1.30
    assert high_torque == pytest.approx(linear_high_torque, rel=0.03)
    assert torque_from_lataccel(-low_lataccel, car_params.lateralTuning.torque) == pytest.approx(-low_torque, rel=1e-6)

  @parameterized.expand((CAR.CHEVROLET_VOLT_ASCM, CAR.CHEVROLET_VOLT_CAMERA, CAR.CHEVROLET_VOLT_CC, CAR.CHEVROLET_VOLT_2019))
  def test_volt_integration_variants_share_nonlinear_torque_curve(self, candidate):
    assert gm_interface.get_nonlinear_torque_params(candidate) == gm_interface.NON_LINEAR_TORQUE_PARAMS[CAR.CHEVROLET_VOLT]

    CarInterface = interfaces[candidate]
    car_params = CarInterface.get_non_essential_params(candidate)
    ci = CarInterface(car_params, custom.StarPilotCarParams.new_message())
    torque_from_lataccel = ci.torque_from_lateral_accel()

    left_torque = torque_from_lataccel(0.5, car_params.lateralTuning.torque)
    right_torque = torque_from_lataccel(-0.5, car_params.lateralTuning.torque)
    assert left_torque > abs(right_torque)


class TestGMCarController:
  def test_dash_speed_spoof_respects_live_stock_acc_toggles(self):
    cp = SimpleNamespace(openpilotLongitudinalControl=True, enableGasInterceptorDEPRECATED=True)

    assert should_spoof_dash_speed(cp, SimpleNamespace(disable_openpilot_long=False, gm_pedal_longitudinal=True))
    assert not should_spoof_dash_speed(cp, SimpleNamespace(disable_openpilot_long=True, gm_pedal_longitudinal=True))
    assert not should_spoof_dash_speed(cp, SimpleNamespace(disable_openpilot_long=False, gm_pedal_longitudinal=False))

  def test_dash_speed_spoof_allows_non_pedal_long_when_op_long_enabled(self):
    cp = SimpleNamespace(openpilotLongitudinalControl=True, enableGasInterceptorDEPRECATED=False)

    assert should_spoof_dash_speed(cp, SimpleNamespace(disable_openpilot_long=False))

  def test_volt_one_pedal_lift_brake_seeds_low_speed_braking(self):
    assert get_volt_one_pedal_lift_brake(2.1 * CV.MPH_TO_MS) == 0
    assert get_volt_one_pedal_lift_brake(2.0 * CV.MPH_TO_MS) == 20
    assert get_volt_one_pedal_lift_brake(0.10) == 80

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

  @parameterized.expand([
    CAR.CHEVROLET_BOLT_CC_2017,
    CAR.CHEVROLET_BOLT_CC_2018_2021,
    CAR.CHEVROLET_BOLT_CC_2022_2023,
  ])
  def test_bolt_cc_redneck_ignores_small_setpoint_error(self, car_model):
    packer = CANPacker(DBC[car_model][Bus.pt])
    controller = SimpleNamespace(frame=int(2.0 / DT_CTRL), last_button_frame=0, apply_speed=0)
    cs = SimpleNamespace(
      CP=SimpleNamespace(
        carFingerprint=car_model,
        minEnableSpeed=24 * CV.MPH_TO_MS,
      ),
      buttons_counter=2,
      out=SimpleNamespace(
        vEgo=(60.6 * CV.MPH_TO_MS) / 1.01,
        cruiseState=SimpleNamespace(speed=60 * CV.MPH_TO_MS),
      ),
    )

    msgs = gmcan.create_gm_cc_spam_command(packer, controller, cs, SimpleNamespace(accel=0.0), SimpleNamespace(is_metric=False))

    assert msgs == []
    assert controller.apply_speed == 60

  def test_non_bolt_cc_redneck_keeps_existing_setpoint_selector(self):
    packer = CANPacker(DBC[CAR.CHEVROLET_EQUINOX_CC][Bus.pt])
    controller = SimpleNamespace(frame=int(2.0 / DT_CTRL), last_button_frame=0, apply_speed=0)
    cs = SimpleNamespace(
      CP=SimpleNamespace(
        carFingerprint=CAR.CHEVROLET_EQUINOX_CC,
        flags=GMFlags.CC_LONG.value,
        minEnableSpeed=24 * CV.MPH_TO_MS,
      ),
      buttons_counter=2,
      out=SimpleNamespace(
        vEgo=(60.6 * CV.MPH_TO_MS) / 1.01,
        cruiseState=SimpleNamespace(speed=60 * CV.MPH_TO_MS),
      ),
    )

    msgs = gmcan.create_gm_cc_spam_command(packer, controller, cs, SimpleNamespace(accel=0.0), SimpleNamespace(is_metric=False))

    assert len(msgs) == 1
    assert controller.apply_speed == 61

  def test_bolt_cc_redneck_requires_persistent_acceleration_after_deceleration(self):
    cp = SimpleNamespace(carFingerprint=CAR.CHEVROLET_BOLT_CC_2018_2021)
    controller = SimpleNamespace(
      frame=100,
      gm_cc_last_direction_button=CruiseButtons.DECEL_SET,
      gm_cc_last_direction_frame=100,
      gm_cc_pending_reverse_button=CruiseButtons.INIT,
      gm_cc_pending_reverse_frame=0,
    )

    assert gmcan.stabilize_bolt_cc_button(controller, cp, CruiseButtons.RES_ACCEL) == CruiseButtons.INIT
    controller.frame += int(0.5 / DT_CTRL)
    assert gmcan.stabilize_bolt_cc_button(controller, cp, CruiseButtons.RES_ACCEL) == CruiseButtons.INIT
    controller.frame += int(0.11 / DT_CTRL)
    assert gmcan.stabilize_bolt_cc_button(controller, cp, CruiseButtons.RES_ACCEL) == CruiseButtons.RES_ACCEL

  def test_bolt_cc_redneck_deceleration_is_not_debounced(self):
    cp = SimpleNamespace(carFingerprint=CAR.CHEVROLET_BOLT_CC_2018_2021)
    controller = SimpleNamespace(
      frame=100,
      gm_cc_last_direction_button=CruiseButtons.RES_ACCEL,
      gm_cc_last_direction_frame=100,
      gm_cc_pending_reverse_button=CruiseButtons.INIT,
      gm_cc_pending_reverse_frame=0,
    )

    assert gmcan.stabilize_bolt_cc_button(controller, cp, CruiseButtons.DECEL_SET) == CruiseButtons.DECEL_SET

  def test_xt4_cc_redneck_spam_matches_physical_button_burst(self):
    packer = CANPacker(DBC[CAR.CADILLAC_XT4_CC][Bus.pt])
    controller = SimpleNamespace(
      frame=int(0.3 / DT_CTRL),
      last_button_frame=0,
      apply_speed=0,
      malibu_button_phase=0,
      xt4_cc_button_burst_remaining=0,
      xt4_cc_button_burst_button=CruiseButtons.INIT,
      xt4_cc_button_burst_last_counter=-1,
      xt4_cc_button_observed_counter=-1,
      xt4_cc_button_counter_frame=0,
    )
    cs = SimpleNamespace(
      CP=SimpleNamespace(
        carFingerprint=CAR.CADILLAC_XT4_CC,
        flags=GMFlags.CC_LONG.value,
        minEnableSpeed=24 * CV.MPH_TO_MS,
      ),
      buttons_counter=0,
      out=SimpleNamespace(
        vEgo=25.0,
        cruiseState=SimpleNamespace(speed=20.0),
      ),
    )
    actuators = SimpleNamespace(accel=1.0)

    dats = []
    send_counts = []
    for counter in (0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 0, 0, 0, 1, 1, 1):
      cs.buttons_counter = counter
      msgs = gmcan.create_gm_cc_spam_command(packer, controller, cs, actuators, SimpleNamespace(is_metric=False))
      send_counts.append(len(msgs))
      dats.extend(bytes(msg[1]).hex() for msg in msgs)
      controller.frame += 1

    assert send_counts == [0, 1, 0] * gmcan.XT4_CC_BUTTON_BURST_FRAMES
    assert dats == [
      "000000010125de",
      "00000001022acd",
      "00000001032fbc",
      "000000010020ef",
      "000000010125de",
      "00000001022acd",
    ]
    assert controller.xt4_cc_button_burst_remaining == 0

  def test_acc_dashboard_command_preserves_raw_fcw_alert_level(self):
    packer = CANPacker(DBC[CAR.CHEVROLET_BOLT_ACC_2022_2023][Bus.pt])
    parser = CANParser(DBC[CAR.CHEVROLET_BOLT_ACC_2022_2023][Bus.pt], [("ASCMActiveCruiseControlStatus", 0)], 0)
    msg = gmcan.create_acc_dashboard_command(
      packer,
      0,
      True,
      100,
      SimpleNamespace(leadDistanceBars=3, leadVisible=True),
      0x2,
    )

    parser.update([0, [msg]])

    values = parser.vl["ASCMActiveCruiseControlStatus"]

    assert values["ACCAlwaysOne"] == 1
    assert values["ACCAlwaysOne2"] == 1
    assert values["ACCCruiseState"] == 2
    assert values["ACCCmdActive"] == 1
    assert values["FCWAlert"] == 2

  def test_acc_dashboard_command_allows_camera_acc_zero_reserved_bits(self):
    packer = CANPacker(DBC[CAR.CHEVROLET_TRAILBLAZER][Bus.pt])
    parser = CANParser(DBC[CAR.CHEVROLET_TRAILBLAZER][Bus.pt], [("ASCMActiveCruiseControlStatus", 0)], 0)
    msg = gmcan.create_acc_dashboard_command(
      packer,
      0,
      True,
      67.1875,
      SimpleNamespace(leadDistanceBars=1, leadVisible=False),
      0,
      acc_always_one=0,
    )

    parser.update([0, [msg]])
    values = parser.vl["ASCMActiveCruiseControlStatus"]

    assert msg[1] == b"\x00\x02\x94\x33\x00\x00"
    assert values["ACCAlwaysOne"] == 0
    assert values["ACCAlwaysOne2"] == 0
    assert values["ACCCruiseState"] == 2
    assert values["ACCCmdActive"] == 1

  def test_acc_dashboard_always_one_matches_camera_acc_platforms(self):
    assert get_acc_dashboard_always_one(SimpleNamespace(carFingerprint=CAR.CHEVROLET_TRAILBLAZER)) == 0
    assert get_acc_dashboard_always_one(SimpleNamespace(carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023)) == 1

  def test_acc_dashboard_command_uses_openpilot_hud_when_disengaged(self):
    packer = CANPacker(DBC[CAR.CHEVROLET_VOLT_ASCM][Bus.pt])
    parser = CANParser(DBC[CAR.CHEVROLET_VOLT_ASCM][Bus.pt], [("ASCMActiveCruiseControlStatus", 0)], 0)
    msg = gmcan.create_acc_dashboard_command(
      packer,
      0,
      False,
      50,
      SimpleNamespace(leadDistanceBars=2, leadVisible=True),
      0x3,
    )

    parser.update([0, [msg]])
    values = parser.vl["ASCMActiveCruiseControlStatus"]

    assert values["ACCSpeedSetpoint"] == 50
    assert values["ACCCruiseState"] == 2
    assert values["ACCGapLevel"] == 0
    assert values["ACCCmdActive"] == 0
    assert values["ACCLeadCar"] == 1
    assert values["FCWAlert"] == 3

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
