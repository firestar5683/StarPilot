import math
import pytest
from parameterized import parameterized
from types import SimpleNamespace

from cereal import car, custom, log
import openpilot.selfdrive.controls.lib.latcontrol_torque as latcontrol_torque
import openpilot.selfdrive.controls.lib.latcontrol_pid as latcontrol_pid
import openpilot.selfdrive.controls.lib.latcontrol_vehicle_tunes as latcontrol_vehicle_tunes
from opendbc.car.car_helpers import interfaces
from opendbc.car.interfaces import CarInterfaceBase
from opendbc.car.chrysler.values import CAR as CHRYSLER
from opendbc.car.honda.values import CAR as HONDA, HondaFlags
from opendbc.car.toyota.values import CAR as TOYOTA
from opendbc.car.nissan.values import CAR as NISSAN
from opendbc.car.gm.values import CAR as GM
from opendbc.car.hyundai.values import CAR as HYUNDAI
from opendbc.car.subaru.values import CAR as SUBARU
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.latcontrol_angle import (
  LatControlAngle,
  _ascent_angle_tracking_target,
  _ford_angle_tracking_saturated,
)
from openpilot.selfdrive.controls.lib.latcontrol_pid import (
  LatControlPID,
  get_civic_bosch_modified_pid_output_alpha,
  get_civic_bosch_modified_pid_output_scale,
  get_honda_crv_5g_pid_output,
)
from openpilot.selfdrive.controls.lib.latcontrol_vehicle_tunes import (
  clear_flm_runtime_overrides,
  get_flm_runtime_overrides,
  get_hkg_canfd_base_friction_threshold,
  get_ioniq_6_2025_low_speed_center_error_scale,
  get_ioniq_6_2025_low_speed_center_friction_scale,
  get_kona_non_scc_center_taper_scale,
  get_kona_non_scc_friction_threshold,
  get_kona_non_scc_highway_transition_output_scale,
  get_kia_ev6_center_output_scale,
  get_sonata_hybrid_center_output_scale,
  get_sonata_hybrid_friction_threshold,
  get_prius_center_taper_scale,
  PRIUS_STANDARD_FRICTION_JERK_DEADZONE_MAX,
  KIA_FORTE_BASE_LAT_ACCEL_FACTOR_MULT,
  HONDA_ACCORD_TORQUE_KI,
  HONDA_ACCORD_TORQUE_KP,
  RAM_1500_BASE_LAT_ACCEL_FACTOR_MULT,
  RAM_1500_MAX_LAT_JERK_UP,
  get_gmc_yukon_cc_ff_scale,
  get_ram_1500_center_output_scale,
  get_ram_1500_transition_output_scale,
  get_ram_1500_unwind_output_scale,
  get_ram_1500_ff_scale,
  get_rav4_tss2_pid_output,
  get_subaru_impreza_pid_output_scale,
  normalize_flm_overrides,
  set_flm_runtime_overrides,
)
from openpilot.selfdrive.controls.lib.latcontrol_torque import (
  get_civic_bosch_modified_a_center_taper_scale,
  get_center_chatter_friction_jerk_deadzone,
  LatControlTorque,
  get_civic_bosch_modified_b_ff_scale,
  get_civic_bosch_modified_b_friction_scale,
  get_gm_base_friction_threshold,
  get_bolt_2017_center_taper_scale,
  get_standard_friction_threshold,
  get_bolt_2017_base_torque_scale,
  get_bolt_2017_steer_ratio_scale,
  get_bolt_2017_torque_scale,
  get_bolt_2022_2023_ff_scale,
  get_bolt_2022_2023_center_output_scale,
  get_bolt_2022_2023_low_speed_center_output_limit,
  get_bolt_2022_2023_low_speed_center_output,
  get_bolt_2022_2023_friction_scale,
  get_bolt_2022_2023_friction_threshold,
  get_trailer_lateral_ff_scale,
  get_trailer_lateral_friction_scale,
  get_bolt_2018_2021_dynamic_torque_scale,
  get_bolt_2018_2021_friction_scale,
  get_bolt_2018_2021_friction_threshold,
  get_bolt_2018_2021_torque_scale,
  get_genesis_g90_ff_scale,
  get_genesis_g90_friction_scale,
  get_genesis_g90_friction_threshold,
  get_genesis_g70_center_output_scale,
  get_genesis_g70_curve_unwind_output_scale,
  get_genesis_g70_angle_output_scale,
  get_genesis_g70_friction_jerk_deadzone,
  get_genesis_g70_friction_threshold,
  get_genesis_g70_high_speed_error_scale,
  get_genesis_g70_low_speed_angle_damping,
  get_genesis_g70_low_speed_output_limit,
  get_genesis_g70_unwind_ff_scale,
  get_genesis_gv70_center_output_scale,
  get_genesis_gv70_friction_jerk_deadzone,
  get_genesis_gv70_friction_threshold,
  get_genesis_gv70_high_speed_error_scale,
  get_genesis_gv70_unwind_ff_scale,
  get_honda_accord_ff_scale,
  get_elantra_non_scc_ff_scale,
  get_honda_accord_steer_ratio_scale,
  get_palisade_ff_scale,
  get_palisade_center_output_scale,
  get_palisade_center_taper_scale,
  get_palisade_friction_scale,
  get_palisade_friction_threshold,
  get_prius_ff_scale,
  get_prius_friction_scale,
  get_prius_friction_threshold,
  get_prius_friction_jerk_deadzone,
  get_prius_high_speed_output_taper_scale,
  get_camry_friction_threshold,
  get_rav4_prime_ff_scale,
  get_rav4_prime_friction_scale,
  get_rav4_prime_friction_threshold,
  get_rav4_prime_output_taper_scale,
  get_rav4_tss2_center_output_scale,
  get_rav4_tss2_friction_threshold,
  get_sienna_4th_gen_center_taper_scale,
  get_sienna_4th_gen_ff_scale,
  get_sienna_4th_gen_friction_threshold,
  get_sienna_4th_gen_high_speed_output_taper_scale,
  get_toyota_highlander_tss2_ff_scale,
  get_toyota_highlander_tss2_friction_scale,
  get_toyota_highlander_tss2_friction_threshold,
  get_toyota_highlander_tss2_output_taper_scale,
  get_toyota_corolla_tss2_center_output_scale,
  get_toyota_corolla_tss2_friction_threshold,
  get_toyota_corolla_tss2_ff_scale,
  get_lexus_is_ff_scale,
  get_camry_ff_scale,
  get_ioniq_5_ff_scale,
  get_ioniq_5_friction_scale,
  get_ioniq_5_friction_threshold,
  get_ioniq_5_center_taper_scale,
  get_ioniq_5_friction_jerk_deadzone,
  get_ioniq_5_low_speed_output_limit,
  get_ioniq_ev_old_center_taper_scale,
  get_ioniq_ev_old_ff_scale,
  get_ioniq_6_center_taper_scale,
  get_ioniq_6_directional_taper_scale,
  get_ioniq_6_output_taper_scale,
  get_ioniq_6_ff_scale,
  get_ioniq_6_2023_unwind_ff_scale,
  get_ioniq_6_friction_center_fade_scale,
  get_ioniq_6_friction_scale,
  get_ioniq_6_friction_threshold,
  get_ioniq_6_low_speed_angle_assist_torque,
  get_ioniq_6_2025_center_output_scale,
  get_ioniq_6_2025_low_speed_output_limit,
  is_ioniq_6_2025_model,
  get_kia_forte_center_taper_scale,
  get_kia_forte_ff_scale,
  get_kia_carnival_center_taper_scale,
  get_kia_carnival_friction_center_fade_scale,
  get_kia_carnival_friction_jerk_deadzone,
  get_kia_carnival_friction_threshold,
  get_kia_carnival_highway_transition_output_scale,
  get_kia_carnival_unwind_ff_scale,
  get_kia_stinger_2022_center_taper_scale,
  get_kia_stinger_2022_friction_threshold,
  get_tucson_4th_gen_center_taper_scale,
  get_tucson_4th_gen_friction_threshold,
  get_kia_ev6_center_taper_scale,
  get_kia_ev6_ff_scale,
  get_kia_ev6_friction_scale,
  get_kia_ev6_friction_threshold,
  get_kia_ev6_jwarm_phase_confidence,
  get_sonata_center_taper_scale,
  get_sonata_ff_scale,
  get_sonata_hybrid_center_taper_scale,
  get_sonata_hybrid_ff_scale,
  get_volt_standard_center_taper_scale,
  get_volt_standard_ff_scale,
  get_volt_standard_friction_scale,
  get_volt_standard_friction_threshold,
  get_volt_plexy_ff_scale,
  get_volt_plexy_friction_scale,
  get_volt_plexy_friction_threshold,
)


class TestLatControl:

  def test_center_chatter_friction_jerk_deadzone_is_center_and_speed_gated(self):
    low_speed_center = get_center_chatter_friction_jerk_deadzone(2.0, 0.0)
    highway_center = get_center_chatter_friction_jerk_deadzone(25.0, 0.0)
    highway_curve = get_center_chatter_friction_jerk_deadzone(25.0, 0.6)

    assert low_speed_center == pytest.approx(0.096)
    assert highway_center == pytest.approx(0.18)
    assert highway_curve == pytest.approx(0.0)

  def test_center_chatter_friction_jerk_deadzone_preserves_vehicle_override(self):
    assert get_center_chatter_friction_jerk_deadzone(25.0, 0.6, 0.30) == pytest.approx(0.30)

  def test_ascent_angle_tracking_correction_is_bounded_and_handoff_safe(self):
    assert _ascent_angle_tracking_target(10.0, 0.0, 20.0, False) == pytest.approx(12.5)
    assert _ascent_angle_tracking_target(40.0, 0.0, 20.0, False) == pytest.approx(48.0)
    assert _ascent_angle_tracking_target(10.0, 0.0, 4.0, False) == pytest.approx(10.0)
    assert _ascent_angle_tracking_target(10.0, 0.0, 20.0, True) == pytest.approx(10.0)

  def test_ford_angle_tracking_does_not_report_a_responsive_eps_as_saturated(self):
    assert not _ford_angle_tracking_saturated(12.0, 12.0)
    assert not _ford_angle_tracking_saturated(-12.0, -12.0)
    assert _ford_angle_tracking_saturated(16.0, 12.0)
    assert _ford_angle_tracking_saturated(12.0, -12.0)

  def test_ford_angle_tracking_still_reports_a_stalled_eps(self):
    assert _ford_angle_tracking_saturated(3.0, 0.0)
    assert not _ford_angle_tracking_saturated(2.5, 0.0)

  def test_ford_angle_handoff_saturation_waits_for_eps_response(self):
    CP = SimpleNamespace(
      steerLimitTimer=1.0,
      brand="ford",
      carFingerprint="FORD_MUSTANG_MACH_E_MK1",
    )
    controller = LatControlAngle(CP, None, DT_CTRL)
    target = [12.0]
    VM = SimpleNamespace(get_steer_from_curvature=lambda *_args: math.radians(target[0]))
    CS = car.CarState.new_message(vEgo=10.0, steeringPressed=False)
    params = log.LiveParametersData.new_message(angleOffsetDeg=0.0, roll=0.0)
    toggles = SimpleNamespace(ford_lateral_mode=2)

    for frame in range(round(2.0 / DT_CTRL)):
      CS.steeringAngleDeg = frame * 12.0 * DT_CTRL
      target[0] = CS.steeringAngleDeg + 12.0
      _, _, angle_log = controller.update(
        True, CS, VM, params, False, 0.0, False, 0.0, None, None, toggles)
      assert not angle_log.saturated

    for _ in range(round(2.0 / DT_CTRL)):
      _, _, angle_log = controller.update(
        True, CS, VM, params, False, 0.0, False, 0.0, None, None, toggles)
    assert angle_log.saturated

  def test_torque_log_exposes_friction_controller_state(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(GM.CHEVROLET_BOLT_ACC_2022_2023)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0, False, 0.2, None, None, starpilot_toggles)

    debug_state = controller.starpilot_lateral_state
    assert debug_state.active
    assert debug_state.frictionThreshold > 0.0
    assert debug_state.frictionScale > 0.0
    assert debug_state.frictionJerkDeadzone > 0.0
    assert debug_state.lowSpeedFactor > 0.0

  @staticmethod
  def _build_torque_controller(car_name, force_torque=False):
    CarInterface = interfaces[car_name]
    CP = CarInterface.get_non_essential_params(car_name)
    if force_torque:
      CarInterfaceBase.configure_torque_tune(car_name, CP.lateralTuning)
    CI = CarInterface(CP, custom.StarPilotCarParams.new_message())
    controller = LatControlTorque(CP.as_reader(), CI, DT_CTRL)
    VM = VehicleModel(CP)

    CS = car.CarState.new_message()
    CS.vEgo = 22
    CS.steeringPressed = False
    CS.steeringAngleDeg = 1.0

    params = log.LiveParametersData.new_message()
    params.steerRatio = CP.steerRatio
    params.stiffnessFactor = 1.0
    params.roll = 0.0
    params.angleOffsetDeg = 0.0

    starpilot_toggles = SimpleNamespace()
    return controller, VM, CS, params, starpilot_toggles

  @staticmethod
  def _build_pid_controller(car_name):
    CarInterface = interfaces[car_name]
    CP = CarInterface.get_non_essential_params(car_name)
    CP.dashcamOnly = True
    CI = CarInterface(CP, custom.StarPilotCarParams.new_message())
    controller = LatControlPID(CP.as_reader(), CI, DT_CTRL)
    VM = VehicleModel(CP)

    CS = car.CarState.new_message()
    CS.vEgo = 12
    CS.steeringPressed = False
    CS.steeringAngleDeg = -6.0
    CS.steeringRateDeg = 0.0

    params = log.LiveParametersData.new_message()
    params.steerRatio = CP.steerRatio
    params.stiffnessFactor = 1.0
    params.roll = 0.0
    params.angleOffsetDeg = 0.0

    starpilot_toggles = SimpleNamespace()
    return controller, VM, CS, params, starpilot_toggles

  def test_bolt_2017_testing_ground_scale_curve(self):
    assert get_bolt_2017_base_torque_scale(0.1) == 1.0
    assert get_bolt_2017_base_torque_scale(-0.1) == 1.0
    assert get_bolt_2017_base_torque_scale(0.5) > get_bolt_2017_base_torque_scale(-0.5)
    assert 1.0 < get_bolt_2017_base_torque_scale(1.2) < get_bolt_2017_base_torque_scale(0.5)
    assert get_bolt_2017_base_torque_scale(-2.5) < 1.0
    assert (1.0 < get_bolt_2017_steer_ratio_scale(10.0 * 0.44704) <
            get_bolt_2017_steer_ratio_scale(20.0 * 0.44704) <
            get_bolt_2017_steer_ratio_scale(30.0 * 0.44704))
    assert get_bolt_2017_steer_ratio_scale(5.0 * 0.44704) < 1.01
    assert get_bolt_2017_steer_ratio_scale(35.0 * 0.44704) > 1.04
    assert (get_bolt_2017_center_taper_scale(0.0, 30.0 * 0.44704) <
            get_bolt_2017_center_taper_scale(0.10, 30.0 * 0.44704) <
            get_bolt_2017_center_taper_scale(0.20, 30.0 * 0.44704) <= 1.0)
    assert get_bolt_2017_center_taper_scale(0.0, 30.0 * 0.44704) < get_bolt_2017_center_taper_scale(0.0, 10.0 * 0.44704)
    assert get_bolt_2017_torque_scale(0.0, 0.0, 30.0 * 0.44704) < 1.0
    assert get_bolt_2017_torque_scale(0.6, 0.6, 8.0) > get_bolt_2017_torque_scale(0.6, 0.0, 8.0) > get_bolt_2017_torque_scale(0.6, -0.6, 8.0)
    assert get_bolt_2017_torque_scale(-0.6, -0.6, 8.0) > get_bolt_2017_torque_scale(-0.6, 0.0, 8.0) > get_bolt_2017_torque_scale(-0.6, 0.6, 8.0)
    assert get_bolt_2017_torque_scale(0.6, 0.6, 8.0) > get_bolt_2017_torque_scale(-0.6, -0.6, 8.0)

  def test_bolt_2018_2021_testing_ground_scale_curve(self):
    assert get_bolt_2018_2021_torque_scale(0.0) == 1.0
    assert get_bolt_2018_2021_torque_scale(0.2) > get_bolt_2018_2021_torque_scale(0.08)
    assert get_bolt_2018_2021_torque_scale(0.4) > get_bolt_2018_2021_torque_scale(-0.4)
    assert get_bolt_2018_2021_torque_scale(2.0) < get_bolt_2018_2021_torque_scale(0.8)
    assert get_bolt_2018_2021_dynamic_torque_scale(0.08, 0.0, 25.0) < get_bolt_2018_2021_dynamic_torque_scale(0.08, 0.0, 8.0)
    assert get_bolt_2018_2021_dynamic_torque_scale(0.4, 0.8, 20.0) < get_bolt_2018_2021_dynamic_torque_scale(0.4, 0.1, 20.0)
    assert get_bolt_2018_2021_dynamic_torque_scale(0.6, -0.6, 8.0) < get_bolt_2018_2021_dynamic_torque_scale(0.6, 0.6, 8.0)
    assert get_bolt_2018_2021_dynamic_torque_scale(-0.6, 0.6, 8.0) < get_bolt_2018_2021_dynamic_torque_scale(-0.6, -0.6, 8.0)

  def test_bolt_2018_2021_friction_threshold_curve(self):
    base = get_gm_base_friction_threshold(6.0)
    left_turn_in = get_bolt_2018_2021_friction_threshold(6.0, 0.7, 0.8)
    right_turn_in = get_bolt_2018_2021_friction_threshold(6.0, -0.7, -0.8)
    left_unwind = get_bolt_2018_2021_friction_threshold(6.0, 0.7, -0.8)
    right_unwind = get_bolt_2018_2021_friction_threshold(6.0, -0.7, 0.8)
    assert left_turn_in <= right_turn_in < base < left_unwind < right_unwind
    assert get_bolt_2018_2021_friction_threshold(25.0, 0.7, 0.8) > left_turn_in

  def test_bolt_2018_2021_friction_scale_curve(self):
    base = get_bolt_2018_2021_friction_scale(25.0, 0.7, 0.8)
    center_base = get_bolt_2018_2021_friction_scale(25.0, 0.0, 0.0)
    left_turn_in = get_bolt_2018_2021_friction_scale(6.0, 0.7, 0.8)
    right_turn_in = get_bolt_2018_2021_friction_scale(6.0, -0.7, -0.8)
    left_unwind = get_bolt_2018_2021_friction_scale(6.0, 0.7, -0.8)
    right_unwind = get_bolt_2018_2021_friction_scale(6.0, -0.7, 0.8)
    assert center_base < 1.02
    assert left_turn_in >= right_turn_in > base
    assert base > left_unwind > right_unwind

  def test_bolt_2022_2023_ff_scale_curve(self):
    assert get_bolt_2022_2023_ff_scale(0.0, 0.0, 20.0) == 1.0
    assert get_bolt_2022_2023_ff_scale(0.5, 0.0, 20.0) > get_bolt_2022_2023_ff_scale(-0.5, 0.0, 20.0)
    assert get_bolt_2022_2023_ff_scale(0.6, 0.7, 8.0) > get_bolt_2022_2023_ff_scale(-0.6, -0.7, 8.0)
    assert get_bolt_2022_2023_ff_scale(-0.6, -0.7, 8.0) > get_bolt_2022_2023_ff_scale(-0.6, 0.0, 8.0)
    assert get_bolt_2022_2023_ff_scale(0.6, -0.7, 8.0) < get_bolt_2022_2023_ff_scale(0.6, 0.0, 8.0)
    assert get_bolt_2022_2023_ff_scale(0.6, -0.7, 6.0) < get_bolt_2022_2023_ff_scale(0.6, -0.7, 20.0)
    assert get_bolt_2022_2023_ff_scale(0.14, 0.0, 30.0) < get_bolt_2022_2023_ff_scale(0.14, 0.0, 20.0)

  def test_bolt_2022_2023_center_output_taper(self):
    low_speed_center = get_bolt_2022_2023_center_output_scale(0.04, 10.0)
    low_speed_turn = get_bolt_2022_2023_center_output_scale(0.40, 10.0)
    middle_speed_center = get_bolt_2022_2023_center_output_scale(0.04, 20.0)
    highway_center = get_bolt_2022_2023_center_output_scale(0.04, 31.0)
    highway_turn = get_bolt_2022_2023_center_output_scale(0.40, 31.0)
    creep_center = get_bolt_2022_2023_center_output_scale(0.04, 1.0)

    assert 0.88 < low_speed_center < 0.92
    assert low_speed_turn > 0.99
    assert 0.96 < middle_speed_center < 0.98
    assert 0.88 < highway_center < 0.91
    assert highway_turn > 0.99
    assert creep_center > 0.99

  def test_bolt_2022_2023_low_speed_center_output_limit(self):
    low_speed_center = get_bolt_2022_2023_low_speed_center_output_limit(0.05, 4.2)
    low_speed_turn = get_bolt_2022_2023_low_speed_center_output_limit(0.40, 4.2)
    normal_speed_center = get_bolt_2022_2023_low_speed_center_output_limit(0.05, 9.0)

    assert 0.40 < low_speed_center < 0.50
    assert low_speed_turn > 0.98
    assert normal_speed_center > 0.98

  def test_bolt_2022_2023_low_speed_center_output_damps_reversals(self):
    low_speed = get_bolt_2022_2023_low_speed_center_output(1.0, -1.0, 0.05, 4.2)
    large_turn = get_bolt_2022_2023_low_speed_center_output(1.0, -1.0, 0.40, 4.2)
    highway = get_bolt_2022_2023_low_speed_center_output(1.0, -1.0, 0.05, 9.0)

    assert abs(low_speed) < 0.50
    assert abs(large_turn) > abs(low_speed)
    assert highway > low_speed

  def test_bolt_2022_2023_friction_threshold_curve(self):
    base = get_gm_base_friction_threshold(6.0)
    left_turn_in = get_bolt_2022_2023_friction_threshold(6.0, 0.7, 0.8)
    right_turn_in = get_bolt_2022_2023_friction_threshold(6.0, -0.7, -0.8)
    left_unwind = get_bolt_2022_2023_friction_threshold(6.0, 0.7, -0.8)
    right_unwind = get_bolt_2022_2023_friction_threshold(6.0, -0.7, 0.8)
    assert left_turn_in <= right_turn_in < base < right_unwind <= left_unwind

  def test_bolt_2022_2023_center_friction_threshold_targets_low_speed_chatter(self):
    base = get_gm_base_friction_threshold(5.0)
    low_speed_center = get_bolt_2022_2023_friction_threshold(5.0, 0.0, 0.0)
    low_speed_turn = get_bolt_2022_2023_friction_threshold(5.0, 0.7, 0.8)
    medium_speed_center = get_bolt_2022_2023_friction_threshold(8.5, 0.0, 0.0)
    high_speed_center = get_bolt_2022_2023_friction_threshold(14.0, 0.0, 0.0)

    assert low_speed_center > base
    assert low_speed_center > low_speed_turn
    assert low_speed_center - base > medium_speed_center - get_gm_base_friction_threshold(8.5)
    assert medium_speed_center - get_gm_base_friction_threshold(8.5) > high_speed_center - get_gm_base_friction_threshold(14.0)

  def test_bolt_2022_2023_friction_scale_curve(self):
    base = get_bolt_2022_2023_friction_scale(25.0, 0.7, 0.8)
    left_turn_in = get_bolt_2022_2023_friction_scale(6.0, 0.7, 0.8)
    right_turn_in = get_bolt_2022_2023_friction_scale(6.0, -0.7, -0.8)
    left_unwind = get_bolt_2022_2023_friction_scale(6.0, 0.7, -0.8)
    right_unwind = get_bolt_2022_2023_friction_scale(6.0, -0.7, 0.8)
    assert left_turn_in > right_turn_in > base
    assert base > right_unwind >= left_unwind

  def test_volt_plexy_ff_scale_curve(self):
    assert get_volt_plexy_ff_scale(0.0, 0.0, 20.0) == 1.0
    assert get_volt_plexy_ff_scale(0.5, 0.0, 20.0) > get_volt_plexy_ff_scale(-0.5, 0.0, 20.0)
    assert get_volt_plexy_ff_scale(0.6, 0.7, 8.0) > get_volt_plexy_ff_scale(0.6, 0.0, 8.0) > get_volt_plexy_ff_scale(0.6, -0.7, 8.0)
    assert get_volt_plexy_ff_scale(-0.6, -0.7, 8.0) > get_volt_plexy_ff_scale(-0.6, 0.0, 8.0) > get_volt_plexy_ff_scale(-0.6, 0.7, 8.0)
    assert get_volt_plexy_ff_scale(2.0, 0.0, 20.0) < get_volt_plexy_ff_scale(0.8, 0.0, 20.0)

  def test_volt_standard_ff_scale_curve(self):
    assert get_volt_standard_ff_scale(0.0, 0.0, 20.0) == 1.0
    assert get_volt_standard_ff_scale(0.5, 0.0, 20.0) >= get_volt_standard_ff_scale(-0.5, 0.0, 20.0)
    assert get_volt_standard_ff_scale(0.6, 0.7, 8.0) > get_volt_standard_ff_scale(0.6, 0.0, 8.0) > get_volt_standard_ff_scale(0.6, -0.7, 8.0)
    assert get_volt_standard_ff_scale(-0.6, -0.7, 8.0) > get_volt_standard_ff_scale(-0.6, 0.0, 8.0) > get_volt_standard_ff_scale(-0.6, 0.7, 8.0)
    assert get_volt_standard_ff_scale(2.0, 0.0, 20.0) < get_volt_standard_ff_scale(0.8, 0.0, 20.0)

  def test_volt_standard_friction_threshold_curve(self):
    base = get_gm_base_friction_threshold(6.0)
    left_turn_in = get_volt_standard_friction_threshold(6.0, 0.7, 0.8)
    right_turn_in = get_volt_standard_friction_threshold(6.0, -0.7, -0.8)
    left_unwind = get_volt_standard_friction_threshold(6.0, 0.7, -0.8)
    right_unwind = get_volt_standard_friction_threshold(6.0, -0.7, 0.8)
    assert right_turn_in <= left_turn_in < base
    assert base < left_unwind <= right_unwind

  def test_volt_standard_friction_scale_curve(self):
    base = get_volt_standard_friction_scale(25.0, 0.7, 0.8)
    left_turn_in = get_volt_standard_friction_scale(6.0, 0.7, 0.8)
    right_turn_in = get_volt_standard_friction_scale(6.0, -0.7, -0.8)
    left_unwind = get_volt_standard_friction_scale(6.0, 0.7, -0.8)
    right_unwind = get_volt_standard_friction_scale(6.0, -0.7, 0.8)
    assert base == left_turn_in == right_turn_in
    assert left_unwind == right_unwind < base

  def test_volt_standard_center_taper_curve(self):
    assert get_volt_standard_center_taper_scale(0.0, 10.0) > get_volt_standard_center_taper_scale(0.0, 25.0)
    assert (get_volt_standard_center_taper_scale(0.0, 25.0) <
            get_volt_standard_center_taper_scale(0.10, 25.0) <
            get_volt_standard_center_taper_scale(0.20, 25.0) <= 1.0)
    assert get_volt_standard_center_taper_scale(0.0, 25.0) > 0.85

  def test_sonata_hybrid_ff_scale_curve(self):
    assert get_sonata_hybrid_ff_scale(0.0, 0.0, 20.0) == 1.0
    steady_left = get_sonata_hybrid_ff_scale(0.45, 0.0, 20.0)
    steady_right = get_sonata_hybrid_ff_scale(-0.45, 0.0, 20.0)
    turn_in_left = get_sonata_hybrid_ff_scale(0.45, 0.7, 6.0)
    turn_in_right = get_sonata_hybrid_ff_scale(-0.45, -0.7, 6.0)
    unwind_left = get_sonata_hybrid_ff_scale(0.45, -0.7, 6.0)
    unwind_right = get_sonata_hybrid_ff_scale(-0.45, 0.7, 6.0)
    assert steady_left < 1.0
    assert steady_right < steady_left
    assert get_sonata_hybrid_ff_scale(0.30, 0.0, 20.0) < 1.0
    assert get_sonata_hybrid_ff_scale(0.30, 0.0, 20.0) < get_sonata_hybrid_ff_scale(0.10, 0.0, 20.0)
    assert turn_in_left > steady_left
    assert turn_in_right > steady_right
    assert unwind_left < steady_left
    assert unwind_right < steady_right

  def test_toyota_corolla_tss2_ff_scale_is_transition_only(self):
    assert get_toyota_corolla_tss2_ff_scale(0.0, 0.0, 10.0) == 1.0
    steady = get_toyota_corolla_tss2_ff_scale(0.5, 0.0, 10.0)
    turn_in = get_toyota_corolla_tss2_ff_scale(0.5, 0.8, 10.0)
    unwind = get_toyota_corolla_tss2_ff_scale(0.5, -0.8, 10.0)
    assert turn_in > steady
    assert unwind < steady
    assert get_toyota_corolla_tss2_ff_scale(0.5, 0.8, 40.0) < turn_in

  def test_toyota_corolla_tss2_center_output_taper_is_low_speed_and_center_only(self):
    crawl_center = get_toyota_corolla_tss2_center_output_scale(0.0, 1.0)
    cruise_center = get_toyota_corolla_tss2_center_output_scale(0.0, 15.0)
    crawl_curve = get_toyota_corolla_tss2_center_output_scale(0.6, 1.0)
    assert 0.65 <= crawl_center < cruise_center <= 1.0
    assert crawl_curve > crawl_center

  def test_toyota_corolla_tss2_friction_threshold_targets_center_highway_band(self):
    base = get_standard_friction_threshold(16.0)
    center = get_toyota_corolla_tss2_friction_threshold(16.0, 0.0, 0.0)
    curve = get_toyota_corolla_tss2_friction_threshold(16.0, 0.8, 0.8)
    slow = get_toyota_corolla_tss2_friction_threshold(5.0, 0.0, 0.0)
    fast = get_toyota_corolla_tss2_friction_threshold(30.0, 0.0, 0.0)
    assert center > base
    assert curve < center
    assert slow < center
    assert fast < center

  def test_flm_standard_friction_curve_override(self):
    base = get_standard_friction_threshold(10.0)
    overrides = normalize_flm_overrides({
      "baseFrictionThresholds": {
        "standard": {
          "values": [0.30, 0.31, 0.32, 0.33, 0.34],
        },
      },
    })
    try:
      set_flm_runtime_overrides(overrides)
      assert get_flm_runtime_overrides()["baseFrictionThresholds"]["standard"]["values"] == [0.30, 0.31, 0.32, 0.33, 0.34]
      assert get_standard_friction_threshold(10.0) == pytest.approx(0.32)
      assert get_standard_friction_threshold(12.5) > get_standard_friction_threshold(10.0)
      assert get_standard_friction_threshold(10.0) != pytest.approx(base)
    finally:
      clear_flm_runtime_overrides()
    assert get_flm_runtime_overrides() == {}
    assert get_standard_friction_threshold(10.0) == pytest.approx(base)

  def test_flm_center_deadband_curve_interpolates_by_speed(self):
    overrides = normalize_flm_overrides({
      "vehicleKnobs": {
        "torque_universal.center_deadband_crawl_deg": 0.0,
        "torque_universal.center_deadband_low_deg": 0.04,
        "torque_universal.center_deadband_mid_deg": 0.08,
        "torque_universal.center_deadband_fast_deg": 0.04,
        "torque_universal.center_deadband_highway_deg": 0.02,
      },
    })
    try:
      set_flm_runtime_overrides(overrides)
      helper = latcontrol_vehicle_tunes.get_flm_full_surface_center_deadband_deg
      assert helper("torque_universal", 0.0) == pytest.approx(0.0)
      assert helper("torque_universal", 10.0) == pytest.approx(0.08)
      assert helper("torque_universal", 12.5) == pytest.approx(0.06)
      assert helper("torque_universal", 25.0) == pytest.approx(0.02)
    finally:
      clear_flm_runtime_overrides()

  def test_flm_center_deadband_only_reaches_controller_with_active_trial(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(GM.CHEVROLET_BOLT_ACC_2022_2023)
    symbol = f"{controller.flm_surface_profile_key}.center_deadband_highway_deg"
    recorded_deadzones = []

    def record_deadzone(_error, deadzone, _threshold, _torque_params):
      recorded_deadzones.append(deadzone)
      return 0.0

    monkeypatch.setattr(latcontrol_torque, "get_friction", record_deadzone)
    starpilot_toggles.flm_active_overrides = {"vehicleKnobs": {symbol: 0.08}}
    starpilot_toggles.flm_active_profile_id = ""
    starpilot_toggles.flm_trial_applied = False
    controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)
    inactive_deadzone = recorded_deadzones[-1]

    starpilot_toggles.flm_active_profile_id = "report:cleanup:recommended"
    starpilot_toggles.flm_trial_applied = True
    try:
      controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)
      assert recorded_deadzones[-1] > inactive_deadzone
    finally:
      clear_flm_runtime_overrides()

  def test_flm_vehicle_knob_override_ioniq6_center_taper(self):
    baseline = get_ioniq_6_center_taper_scale(0.0, 32.0)
    overrides = normalize_flm_overrides({
      "vehicleKnobs": {
        "hyundai_ioniq_6.center_taper_max": 0.0,
        "hyundai_ioniq_6.highway_center_taper_max": 0.0,
      },
    })
    try:
      set_flm_runtime_overrides(overrides)
      adjusted = get_ioniq_6_center_taper_scale(0.0, 32.0)
      assert adjusted > baseline
      assert adjusted <= 1.0
    finally:
      clear_flm_runtime_overrides()

  @pytest.mark.parametrize(("trial_applied", "profile_id"), [(False, "profile"), (True, "")])
  def test_flm_surface_helpers_require_active_trial(self, monkeypatch, trial_applied, profile_id):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(GM.CHEVROLET_BOLT_ACC_2022_2023)
    starpilot_toggles.flm_trial_applied = trial_applied
    starpilot_toggles.flm_active_profile_id = profile_id
    starpilot_toggles.flm_active_overrides = {
      "vehicleKnobs": {"gm_bolt_2022_2023.highway_center_taper_max": 0.10},
    }

    def fail_if_called(*_args, **_kwargs):
      raise AssertionError("inactive FLM trial reached the runtime shaping path")

    monkeypatch.setattr(latcontrol_torque, "get_flm_full_surface_ff_scale", fail_if_called)
    controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert get_flm_runtime_overrides() == {}

  def test_flm_surface_helpers_run_for_active_trial(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(GM.CHEVROLET_BOLT_ACC_2022_2023)
    starpilot_toggles.flm_trial_applied = True
    starpilot_toggles.flm_active_profile_id = "report:cleanup:recommended"
    starpilot_toggles.flm_active_overrides = {
      "vehicleKnobs": {"gm_bolt_2022_2023.highway_center_taper_max": 0.10},
    }
    calls = []

    def record_call(*_args, **_kwargs):
      calls.append(True)
      return 1.0

    monkeypatch.setattr(latcontrol_torque, "get_flm_full_surface_ff_scale", record_call)
    try:
      controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)
      assert calls
      assert get_flm_runtime_overrides()["vehicleKnobs"]["gm_bolt_2022_2023.highway_center_taper_max"] == pytest.approx(0.10)
    finally:
      clear_flm_runtime_overrides()

  def test_sonata_hybrid_center_taper_curve(self):
    assert get_sonata_hybrid_center_taper_scale(0.0, 30.0) < get_sonata_hybrid_center_taper_scale(0.0, 15.0)
    assert get_sonata_hybrid_center_taper_scale(0.0, 3.0) < get_sonata_hybrid_center_taper_scale(0.0, 10.0)
    assert get_sonata_hybrid_center_taper_scale(0.0, 30.0) < get_sonata_hybrid_center_taper_scale(0.20, 30.0) <= 1.0

  def test_sonata_hybrid_center_taper_applies_to_output(self, monkeypatch):
    monkeypatch.setattr(latcontrol_torque, "get_sonata_hybrid_ff_scale", lambda *_args: 0.0)
    monkeypatch.setattr(latcontrol_torque, "get_sonata_hybrid_center_taper_scale", lambda *_args: 1.0)
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_SONATA_HYBRID)
    CS.vEgo = 3.0
    base_output, _, _ = controller.update(True, CS, VM, params, False, 0.0002, False, 0.2, None, None, starpilot_toggles)

    monkeypatch.setattr(latcontrol_torque, "get_sonata_hybrid_center_taper_scale", lambda *_args: 0.5)
    tapered_controller, tapered_VM, tapered_CS, tapered_params, tapered_toggles = self._build_torque_controller(
      HYUNDAI.HYUNDAI_SONATA_HYBRID,
    )
    tapered_CS.vEgo = 3.0
    tapered_output, _, _ = tapered_controller.update(
      True, tapered_CS, tapered_VM, tapered_params, False, 0.0002, False, 0.2, None, None, tapered_toggles,
    )

    assert controller.is_sonata_hybrid
    assert base_output != 0.0
    assert tapered_output == pytest.approx(base_output * 0.5)

  def test_sonata_ff_scale_curve(self):
    assert get_sonata_ff_scale(0.0, 0.0, 20.0) == 1.0
    steady_left = get_sonata_ff_scale(0.45, 0.0, 8.0)
    steady_right = get_sonata_ff_scale(-0.45, 0.0, 8.0)
    turn_in_left = get_sonata_ff_scale(0.45, 0.8, 8.0)
    turn_in_right = get_sonata_ff_scale(-0.45, -0.8, 8.0)
    unwind_left = get_sonata_ff_scale(0.45, -0.8, 8.0)
    unwind_right = get_sonata_ff_scale(-0.45, 0.8, 8.0)
    assert steady_left < 1.0
    assert steady_right < steady_left
    assert turn_in_left > steady_left
    assert turn_in_right == pytest.approx(steady_right)
    assert unwind_left < steady_left
    assert unwind_right == pytest.approx(steady_right)

  def test_sonata_center_taper_curve(self):
    assert get_sonata_center_taper_scale(0.0, 30.0) < get_sonata_center_taper_scale(0.0, 15.0)
    assert get_sonata_center_taper_scale(0.0, 3.0) < get_sonata_center_taper_scale(0.0, 10.0)
    assert get_sonata_center_taper_scale(0.0, 30.0) < get_sonata_center_taper_scale(0.20, 30.0) <= 1.0

  def test_elantra_non_scc_ff_scale_curve(self):
    assert get_elantra_non_scc_ff_scale(0.0, 0.0, 20.0) == 1.0
    steady_left = get_elantra_non_scc_ff_scale(0.45, 0.0, 8.0)
    steady_right = get_elantra_non_scc_ff_scale(-0.45, 0.0, 8.0)
    turn_in_left = get_elantra_non_scc_ff_scale(0.45, 0.7, 8.0)
    turn_in_right = get_elantra_non_scc_ff_scale(-0.45, -0.7, 8.0)
    unwind_left = get_elantra_non_scc_ff_scale(0.45, -0.7, 8.0)
    unwind_right = get_elantra_non_scc_ff_scale(-0.45, 0.7, 8.0)
    assert steady_left < 1.0
    assert steady_right > steady_left
    assert turn_in_left > steady_left
    assert turn_in_right > steady_right
    assert unwind_left < steady_left
    assert unwind_right < steady_right
    assert unwind_left < unwind_right
    assert get_elantra_non_scc_ff_scale(-0.45, 0.0, 25.0) < get_elantra_non_scc_ff_scale(-0.45, 0.0, 8.0)

  def test_kia_forte_ff_scale_curve(self):
    assert get_kia_forte_ff_scale(0.0, 0.0, 20.0) == 1.0
    steady_left = get_kia_forte_ff_scale(0.45, 0.0, 25.0)
    steady_right = get_kia_forte_ff_scale(-0.45, 0.0, 25.0)
    turn_in_left = get_kia_forte_ff_scale(0.45, 0.7, 10.0)
    turn_in_right = get_kia_forte_ff_scale(-0.45, -0.7, 10.0)
    unwind_left = get_kia_forte_ff_scale(0.45, -0.7, 10.0)
    unwind_right = get_kia_forte_ff_scale(-0.45, 0.7, 10.0)
    assert steady_left < 1.0
    assert steady_right < steady_left
    assert turn_in_left > steady_left
    assert turn_in_right > steady_right
    assert unwind_left < steady_left
    assert unwind_right < steady_right
    assert unwind_right > unwind_left
    assert get_kia_forte_ff_scale(0.30, 0.60, 3.0) > get_kia_forte_ff_scale(0.30, 0.60, 6.0)
    assert get_kia_forte_ff_scale(0.30, 0.60, 6.0) > get_kia_forte_ff_scale(0.30, 0.60, 12.0)
    assert get_kia_forte_ff_scale(0.30, -0.60, 3.0) < get_kia_forte_ff_scale(0.30, 0.60, 3.0)

  def test_kia_forte_center_taper_curve(self):
    assert get_kia_forte_center_taper_scale(0.0, 30.0) < get_kia_forte_center_taper_scale(0.0, 15.0)
    assert get_kia_forte_center_taper_scale(0.0, 30.0) < get_kia_forte_center_taper_scale(0.20, 30.0) <= 1.0

  def test_kia_carnival_near_center_stabilization(self):
    center_taper = get_kia_carnival_center_taper_scale(0.04, 8.5)
    turn_taper = get_kia_carnival_center_taper_scale(0.35, 8.5)
    low_speed_taper = get_kia_carnival_center_taper_scale(0.04, 2.0)
    neighborhood_taper = get_kia_carnival_center_taper_scale(0.04, 5.0)
    neighborhood_turn_taper = get_kia_carnival_center_taper_scale(0.35, 5.0)
    highway_taper = get_kia_carnival_center_taper_scale(0.04, 25.0)
    high_speed_center_taper = get_kia_carnival_center_taper_scale(0.04, 32.4)
    high_speed_turn_taper = get_kia_carnival_center_taper_scale(0.80, 32.4)
    assert center_taper < turn_taper <= 1.0
    assert center_taper < low_speed_taper <= 1.0
    assert center_taper < highway_taper <= 1.0
    assert center_taper < 0.84
    assert neighborhood_taper < 0.94
    assert neighborhood_turn_taper > 0.99
    assert 0.85 < high_speed_center_taper < 0.90
    assert high_speed_turn_taper > 0.99

    center_threshold = get_kia_carnival_friction_threshold(8.5, 0.04)
    turn_threshold = get_kia_carnival_friction_threshold(8.5, 0.35)
    high_speed_center_threshold = get_kia_carnival_friction_threshold(32.4, 0.04)
    high_speed_turn_threshold = get_kia_carnival_friction_threshold(32.4, 0.80)
    assert center_threshold > turn_threshold >= get_hkg_canfd_base_friction_threshold(8.5)
    assert high_speed_center_threshold > high_speed_turn_threshold >= get_hkg_canfd_base_friction_threshold(32.4)

    center_fade = get_kia_carnival_friction_center_fade_scale(0.04, 8.5)
    turn_fade = get_kia_carnival_friction_center_fade_scale(0.35, 8.5)
    high_speed_center_fade = get_kia_carnival_friction_center_fade_scale(0.04, 32.4)
    high_speed_turn_fade = get_kia_carnival_friction_center_fade_scale(0.80, 32.4)
    assert center_fade < 0.75 < turn_fade <= 1.0
    assert 0.79 < high_speed_center_fade < 0.85
    assert high_speed_turn_fade > 0.99

  def test_kia_carnival_highway_transition_taper(self):
    smooth_curve = get_kia_carnival_highway_transition_output_scale(0.60, 0.10, 32.4)
    abrupt_curve = get_kia_carnival_highway_transition_output_scale(0.60, 1.20, 32.4)
    low_speed_abrupt = get_kia_carnival_highway_transition_output_scale(0.60, 1.20, 20.0)
    large_curve_abrupt = get_kia_carnival_highway_transition_output_scale(1.60, 1.20, 32.4)

    assert 0.75 < abrupt_curve < 0.77
    assert smooth_curve > 0.96
    assert low_speed_abrupt > 0.99
    assert large_curve_abrupt > 0.96

  def test_kia_carnival_unwind_friction_jerk_deadzone_is_mid_speed_and_center_gated(self):
    low_speed = get_kia_carnival_friction_jerk_deadzone(8.5, 0.0, 1.5)
    mid_speed_center = get_kia_carnival_friction_jerk_deadzone(18.0, 0.0, 1.5)
    mid_speed_curve = get_kia_carnival_friction_jerk_deadzone(18.0, 0.8, 1.5)
    high_speed = get_kia_carnival_friction_jerk_deadzone(30.0, 0.0, 1.5)
    calm_transition = get_kia_carnival_friction_jerk_deadzone(18.0, 0.0, 0.2)

    assert low_speed < 0.02
    assert mid_speed_center > 0.18
    assert mid_speed_curve < 0.05
    assert high_speed < 0.05
    assert calm_transition < 0.05

  def test_kia_carnival_unwind_ff_scale_only_reduces_overshoot(self):
    steady_turn = get_kia_carnival_unwind_ff_scale(0.80, 0.90, 0.60, 18.0)
    clean_unwind = get_kia_carnival_unwind_ff_scale(0.20, 0.20, -1.5, 18.0)
    overshooting_unwind = get_kia_carnival_unwind_ff_scale(0.20, 0.90, -1.5, 18.0)
    highway_overshoot = get_kia_carnival_unwind_ff_scale(0.20, 0.90, -1.5, 30.0)

    assert steady_turn == pytest.approx(1.0)
    assert clean_unwind == pytest.approx(1.0)
    assert overshooting_unwind < 0.70
    assert highway_overshoot > overshooting_unwind

    low_speed_exit = get_kia_carnival_unwind_ff_scale(0.31, 0.43, -0.88, 11.0)
    assert low_speed_exit < 0.90

  def test_genesis_g90_ff_scale_curve(self):
    assert get_genesis_g90_ff_scale(0.0, 0.0, 20.0) == 1.0
    assert get_genesis_g90_ff_scale(0.5, 0.0, 20.0) > get_genesis_g90_ff_scale(-0.5, 0.0, 20.0)
    assert get_genesis_g90_ff_scale(0.6, 0.7, 8.0) > get_genesis_g90_ff_scale(0.6, 0.0, 8.0) > get_genesis_g90_ff_scale(0.6, -0.7, 8.0)
    assert get_genesis_g90_ff_scale(-0.6, -0.7, 8.0) > get_genesis_g90_ff_scale(-0.6, 0.0, 8.0) > get_genesis_g90_ff_scale(-0.6, 0.7, 8.0)
    assert get_genesis_g90_ff_scale(2.0, 0.0, 20.0) < get_genesis_g90_ff_scale(0.8, 0.0, 20.0)

  def test_genesis_g90_friction_threshold_curve(self):
    base = get_gm_base_friction_threshold(6.0)
    left_turn_in = get_genesis_g90_friction_threshold(6.0, 0.7, 0.8)
    right_turn_in = get_genesis_g90_friction_threshold(6.0, -0.7, -0.8)
    left_unwind = get_genesis_g90_friction_threshold(6.0, 0.7, -0.8)
    right_unwind = get_genesis_g90_friction_threshold(6.0, -0.7, 0.8)
    assert left_turn_in < base
    assert right_turn_in < base
    assert left_turn_in == right_turn_in
    assert left_unwind > base
    assert right_unwind > left_unwind

  def test_genesis_g90_friction_scale_curve(self):
    base = get_genesis_g90_friction_scale(25.0, 0.7, 0.8)
    left_turn_in = get_genesis_g90_friction_scale(6.0, 0.7, 0.8)
    right_turn_in = get_genesis_g90_friction_scale(6.0, -0.7, -0.8)
    left_unwind = get_genesis_g90_friction_scale(6.0, 0.7, -0.8)
    right_unwind = get_genesis_g90_friction_scale(6.0, -0.7, 0.8)
    assert left_turn_in > right_turn_in > base
    assert base > left_unwind > right_unwind

  def test_genesis_gv70_unwind_ff_scale(self):
    assert get_genesis_gv70_unwind_ff_scale(-0.3, -0.3, 0.8, 15.0) == 1.0
    assert get_genesis_gv70_unwind_ff_scale(-0.3, 0.1, 0.8, 15.0) == 1.0

    reduced = get_genesis_gv70_unwind_ff_scale(-0.2, -1.0, 1.0, 20.0)
    assert 0.6 < reduced < 1.0
    assert get_genesis_gv70_unwind_ff_scale(-0.2, -1.0, -1.0, 20.0) == 1.0

  def test_palisade_ff_scale_curve(self):
    assert get_palisade_ff_scale(0.0, 0.0, 20.0) == 1.0
    steady_left = get_palisade_ff_scale(0.6, 0.0, 8.0)
    steady_right = get_palisade_ff_scale(-0.6, 0.0, 8.0)
    turn_in_left = get_palisade_ff_scale(0.6, 0.8, 8.0)
    turn_in_right = get_palisade_ff_scale(-0.6, -0.8, 8.0)
    unwind_left = get_palisade_ff_scale(0.6, -0.8, 8.0)
    unwind_right = get_palisade_ff_scale(-0.6, 0.8, 8.0)
    assert steady_left > 1.0
    assert steady_right > 1.0
    assert turn_in_left > steady_left
    assert turn_in_right > steady_right
    assert unwind_left < steady_left
    assert unwind_right < steady_right
    assert unwind_right < unwind_left

  def test_palisade_friction_threshold_curve(self):
    base = get_gm_base_friction_threshold(6.0)
    left_turn_in = get_palisade_friction_threshold(6.0, 0.7, 0.8)
    right_turn_in = get_palisade_friction_threshold(6.0, -0.7, -0.8)
    left_unwind = get_palisade_friction_threshold(6.0, 0.7, -0.8)
    right_unwind = get_palisade_friction_threshold(6.0, -0.7, 0.8)
    assert left_turn_in < right_turn_in < base < left_unwind < right_unwind

  def test_palisade_friction_scale_curve(self):
    base = get_palisade_friction_scale(25.0, 0.7, 0.8)
    left_turn_in = get_palisade_friction_scale(6.0, 0.7, 0.8)
    right_turn_in = get_palisade_friction_scale(6.0, -0.7, -0.8)
    left_unwind = get_palisade_friction_scale(6.0, 0.7, -0.8)
    right_unwind = get_palisade_friction_scale(6.0, -0.7, 0.8)
    assert left_turn_in > right_turn_in > base
    assert base > left_unwind > right_unwind

  def test_palisade_center_taper_curve(self):
    assert get_palisade_center_taper_scale(0.0, 25.0) < get_palisade_center_taper_scale(0.0, 8.0)
    assert get_palisade_center_taper_scale(0.0, 25.0) < get_palisade_center_taper_scale(0.28, 25.0)
    assert get_palisade_center_taper_scale(0.28, 25.0) < get_palisade_center_taper_scale(0.6, 25.0)

  def test_palisade_center_output_taper_curve(self):
    low_speed_center = get_palisade_center_output_scale(0.0, 8.0)
    highway_center = get_palisade_center_output_scale(0.0, 30.0)
    highway_turn = get_palisade_center_output_scale(0.45, 30.0)

    assert low_speed_center > highway_center
    assert highway_center < highway_turn <= 1.0
    assert highway_center > 0.89

  def test_prius_ff_scale_curve(self):
    assert get_prius_ff_scale(0.0, 0.0, 20.0) == 1.0
    steady_left = get_prius_ff_scale(0.7, 0.0, 8.0)
    steady_right = get_prius_ff_scale(-0.7, 0.0, 8.0)
    turn_in_left = get_prius_ff_scale(0.7, 0.8, 8.0)
    turn_in_right = get_prius_ff_scale(-0.7, -0.8, 8.0)
    unwind_left = get_prius_ff_scale(0.7, -0.8, 8.0)
    unwind_right = get_prius_ff_scale(-0.7, 0.8, 8.0)
    assert steady_left > 1.0
    assert steady_right > steady_left
    assert turn_in_left > steady_left
    assert turn_in_right > steady_right
    assert unwind_left < steady_left
    assert unwind_right < steady_right
    assert unwind_right < unwind_left

  def test_prius_friction_curves(self):
    base_threshold = get_gm_base_friction_threshold(12.0)
    low_speed_center_threshold = get_prius_friction_threshold(8.0, 0.0, 0.0)
    high_speed_center_threshold = get_prius_friction_threshold(30.0, 0.0, 0.0)
    high_speed_curve_threshold = get_prius_friction_threshold(30.0, 0.8, 0.0)
    assert high_speed_center_threshold > get_gm_base_friction_threshold(30.0)
    assert high_speed_center_threshold > low_speed_center_threshold
    assert high_speed_curve_threshold < high_speed_center_threshold
    left_turn_in_threshold = get_prius_friction_threshold(6.0, 0.7, 0.8)
    right_turn_in_threshold = get_prius_friction_threshold(6.0, -0.7, -0.8)
    left_unwind_threshold = get_prius_friction_threshold(6.0, 0.7, -0.8)
    right_unwind_threshold = get_prius_friction_threshold(6.0, -0.7, 0.8)
    assert left_turn_in_threshold < base_threshold
    assert right_turn_in_threshold == left_turn_in_threshold
    assert left_unwind_threshold > base_threshold
    assert right_unwind_threshold >= left_unwind_threshold

    base_scale = get_prius_friction_scale(25.0, 0.7, 0.8)
    left_turn_in_scale = get_prius_friction_scale(6.0, 0.7, 0.8)
    right_turn_in_scale = get_prius_friction_scale(6.0, -0.7, -0.8)
    left_unwind_scale = get_prius_friction_scale(6.0, 0.7, -0.8)
    right_unwind_scale = get_prius_friction_scale(6.0, -0.7, 0.8)
    assert right_turn_in_scale == left_turn_in_scale > base_scale
    assert base_scale > left_unwind_scale == right_unwind_scale

    assert get_prius_friction_jerk_deadzone(30.0, 0.0) > get_prius_friction_jerk_deadzone(30.0, 0.8)
    assert get_prius_friction_jerk_deadzone(30.0, 0.0, PRIUS_STANDARD_FRICTION_JERK_DEADZONE_MAX) > \
           get_prius_friction_jerk_deadzone(30.0, 0.0)
    assert get_prius_friction_jerk_deadzone(8.0, 0.0) < 0.05
    assert get_prius_center_taper_scale(0.0, 30.0) < get_prius_center_taper_scale(0.8, 30.0)
    assert get_prius_center_taper_scale(0.0, 8.0) > 0.99
    assert get_prius_high_speed_output_taper_scale(30.0, 0.0) > get_prius_high_speed_output_taper_scale(30.0, 0.8)
    assert get_prius_high_speed_output_taper_scale(15.0, 0.8) > 0.99

  def test_camry_friction_threshold_only_fades_in_for_calm_high_speed(self):
    low_speed_center = get_camry_friction_threshold(10.0, 0.0)
    high_speed_center = get_camry_friction_threshold(32.0, 0.0)
    high_speed_curve = get_camry_friction_threshold(32.0, 0.8)

    assert low_speed_center == pytest.approx(get_standard_friction_threshold(10.0), rel=0.01)
    assert high_speed_center > get_standard_friction_threshold(32.0)
    assert high_speed_curve < high_speed_center

  def test_generic_friction_threshold_floor(self):
    assert get_standard_friction_threshold(0.0) == 0.30
    assert get_standard_friction_threshold(6.0) == 0.30
    assert get_standard_friction_threshold(40.0) == 0.30

  def test_genesis_gv70_friction_threshold_only_fades_calm_center_corrections(self):
    base = get_hkg_canfd_base_friction_threshold(12.0)
    center = get_genesis_gv70_friction_threshold(12.0, 0.0, 0.0)
    turn = get_genesis_gv70_friction_threshold(12.0, 0.7, 0.8)
    highway_center = get_genesis_gv70_friction_threshold(25.0, 0.0, 0.0)
    highway_turn = get_genesis_gv70_friction_threshold(25.0, 0.7, 0.8)

    assert center > base
    assert turn == pytest.approx(base, rel=0.01)
    assert highway_center > base
    assert highway_turn == pytest.approx(base, rel=0.01)
    assert highway_center < center

  def test_genesis_gv70_center_bounce_damping_preserves_turn_authority(self):
    center_scale = get_genesis_gv70_center_output_scale(0.0, 30.0)
    turn_scale = get_genesis_gv70_center_output_scale(0.8, 30.0)
    low_speed_center_scale = get_genesis_gv70_center_output_scale(0.0, 5.0)
    highway_center_deadzone = get_genesis_gv70_friction_jerk_deadzone(30.0, 0.0)
    highway_turn_deadzone = get_genesis_gv70_friction_jerk_deadzone(30.0, 0.8)

    assert center_scale < low_speed_center_scale < 1.0
    assert turn_scale > center_scale
    assert highway_center_deadzone > highway_turn_deadzone
    assert highway_turn_deadzone < 0.05
    assert latcontrol_vehicle_tunes.get_genesis_gv70_friction_jerk_deadzone(60.0 * 0.44704, 0.2) > 0.40

  def test_genesis_gv70_high_speed_error_damping(self):
    assert get_genesis_gv70_high_speed_error_scale(0.2, 0.2, 0.8, 20.0) == 1.0
    assert get_genesis_gv70_high_speed_error_scale(-0.7, 0.58, -0.8, 33.5) < 1.0
    assert get_genesis_gv70_high_speed_error_scale(-0.7, 0.58, -0.8, 20.0) > \
      get_genesis_gv70_high_speed_error_scale(-0.7, 0.58, -0.8, 33.5)

  def test_genesis_g70_center_chatter_tune(self):
    base = get_standard_friction_threshold(25.0)
    center = get_genesis_g70_friction_threshold(25.0, 0.0, 0.0)
    curve = get_genesis_g70_friction_threshold(25.0, 0.8, 0.8)
    center_deadzone = get_genesis_g70_friction_jerk_deadzone(25.0, 0.0)
    curve_deadzone = get_genesis_g70_friction_jerk_deadzone(25.0, 0.8)

    assert center > base
    assert curve == pytest.approx(base, rel=0.01)
    assert center_deadzone > curve_deadzone
    assert get_genesis_g70_center_output_scale(0.0, 25.0) < get_genesis_g70_center_output_scale(0.8, 25.0)
    assert get_genesis_g70_center_output_scale(0.0, 10.0) > get_genesis_g70_center_output_scale(0.0, 25.0)
    assert get_genesis_g70_center_output_scale(0.0, 0.0) < get_genesis_g70_center_output_scale(0.0, 10.0)
    assert get_genesis_g70_low_speed_output_limit(0.0, 2.0) < get_genesis_g70_low_speed_output_limit(0.5, 2.0)
    assert get_genesis_g70_low_speed_output_limit(0.0, 2.0) < get_genesis_g70_low_speed_output_limit(0.0, 10.0)
    assert get_genesis_g70_low_speed_output_limit(0.0, 2.0) < 0.30
    assert get_genesis_g70_low_speed_angle_damping(0.0, -20.0, 0.0, 2.0) < 0.0
    assert get_genesis_g70_low_speed_angle_damping(0.0, 20.0, 0.0, 2.0) > 0.0
    assert get_genesis_g70_curve_unwind_output_scale(0.7, -0.5, 25.0) == pytest.approx(1.0)
    assert get_genesis_g70_curve_unwind_output_scale(0.7, 0.5, 25.0) == 1.0
    assert get_genesis_g70_angle_output_scale(55.0, 1.0) > get_genesis_g70_angle_output_scale(85.0, 1.0)
    assert get_genesis_g70_angle_output_scale(85.0, -1.0) == pytest.approx(1.0)
    assert get_genesis_g70_friction_jerk_deadzone(25.0, 0.0) > 0.25
    assert get_genesis_g70_unwind_ff_scale(-0.7, -0.95, 0.5, 25.0) < 0.90
    assert get_genesis_g70_unwind_ff_scale(-0.7, -0.95, -0.5, 25.0) == 1.0
    assert get_genesis_g70_unwind_ff_scale(-0.7, 0.2, 0.5, 25.0) == 1.0

    assert get_genesis_g70_high_speed_error_scale(0.2, 0.2, 0.8, 20.0) == 1.0
    assert get_genesis_g70_high_speed_error_scale(0.2, 0.9, 0.8, 20.0) < 1.0
    assert get_genesis_g70_high_speed_error_scale(0.2, 0.9, 0.8, 10.0) > get_genesis_g70_high_speed_error_scale(0.2, 0.9, 0.8, 20.0)
    assert get_genesis_g70_high_speed_error_scale(0.7, 0.95, 0.8, 30.0) < \
      get_genesis_g70_high_speed_error_scale(0.7, 0.45, 0.8, 30.0)

  def test_sonata_hybrid_center_output_taper_is_mid_speed_and_center_gated(self):
    low_speed = get_sonata_hybrid_center_output_scale(0.0, 8.0)
    center = get_sonata_hybrid_center_output_scale(0.0, 13.4)
    turn = get_sonata_hybrid_center_output_scale(0.8, 13.4)

    assert low_speed > center
    assert turn > center
    assert turn > 0.99
    assert center > 0.85

  def test_sonata_hybrid_chatter_threshold_is_low_mid_speed_and_center_gated(self):
    base_low = get_standard_friction_threshold(5.5)
    base_high = get_standard_friction_threshold(20.0)
    assert get_sonata_hybrid_friction_threshold(5.5, 0.0) > base_low
    assert get_sonata_hybrid_friction_threshold(5.5, 0.6) == pytest.approx(base_low, abs=0.0001)
    assert get_sonata_hybrid_friction_threshold(20.0, 0.0) == pytest.approx(base_high)

  def test_ioniq_5_ff_scale_curve(self):
    assert get_ioniq_5_ff_scale(0.0, 0.0, 20.0) == 1.0
    steady_left = get_ioniq_5_ff_scale(0.7, 0.0, 12.0)
    steady_right = get_ioniq_5_ff_scale(-0.7, 0.0, 12.0)
    turn_in_left = get_ioniq_5_ff_scale(0.7, 0.8, 12.0)
    turn_in_right = get_ioniq_5_ff_scale(-0.7, -0.8, 12.0)
    unwind_left = get_ioniq_5_ff_scale(0.7, -0.8, 12.0)
    unwind_right = get_ioniq_5_ff_scale(-0.7, 0.8, 12.0)
    assert steady_left < 1.0
    assert steady_right < steady_left
    assert turn_in_left > steady_left
    assert turn_in_right > steady_right
    assert unwind_left < steady_left
    assert unwind_right < unwind_left

  def test_ioniq_5_friction_curves(self):
    base = get_hkg_canfd_base_friction_threshold(12.0)
    turn_in_left_threshold = get_ioniq_5_friction_threshold(12.0, 0.7, 0.8)
    turn_in_right_threshold = get_ioniq_5_friction_threshold(12.0, -0.7, -0.8)
    unwind_left_threshold = get_ioniq_5_friction_threshold(12.0, 0.7, -0.8)
    unwind_right_threshold = get_ioniq_5_friction_threshold(12.0, -0.7, 0.8)
    assert turn_in_left_threshold < base
    assert turn_in_left_threshold < turn_in_right_threshold < base
    assert unwind_left_threshold > base
    assert unwind_right_threshold == unwind_left_threshold

    turn_in_left_scale = get_ioniq_5_friction_scale(12.0, 0.7, 0.8)
    turn_in_right_scale = get_ioniq_5_friction_scale(12.0, -0.7, -0.8)
    unwind_left_scale = get_ioniq_5_friction_scale(12.0, 0.7, -0.8)
    unwind_right_scale = get_ioniq_5_friction_scale(12.0, -0.7, 0.8)
    assert turn_in_left_scale > turn_in_right_scale > 1.0
    assert unwind_left_scale < 1.0
    assert unwind_right_scale <= unwind_left_scale
    assert get_ioniq_5_friction_threshold(25.0, 0.0, 0.0) >= get_hkg_canfd_base_friction_threshold(25.0)

  def test_ioniq_5_friction_jerk_deadzone_is_high_speed_curve_gated(self):
    low_speed = get_ioniq_5_friction_jerk_deadzone(8.0, 0.9)
    high_speed_center = get_ioniq_5_friction_jerk_deadzone(25.0, 0.0)
    high_speed_curve = get_ioniq_5_friction_jerk_deadzone(25.0, 0.9)
    high_lateral_accel = get_ioniq_5_friction_jerk_deadzone(25.0, 2.0)

    assert low_speed < 0.02
    assert high_speed_center > high_speed_curve > 0.0
    assert high_lateral_accel < high_speed_curve

  def test_rav4_prime_phase_shaping(self):
    left_turn_in = get_rav4_prime_ff_scale(1.0, 0.8, 13.0)
    right_turn_in = get_rav4_prime_ff_scale(-1.0, -0.8, 13.0)
    left_unwind = get_rav4_prime_ff_scale(1.0, -0.8, 13.0)
    right_unwind = get_rav4_prime_ff_scale(-1.0, 0.8, 13.0)

    assert 1.0 < right_turn_in < left_turn_in < 1.06
    assert right_unwind < left_unwind < 1.0
    assert left_unwind < 0.86
    assert right_unwind < 0.86
    assert get_rav4_prime_ff_scale(1.0, -0.8, 25.0) > left_unwind

  def test_rav4_prime_friction_targets_center_and_unwind(self):
    base = get_standard_friction_threshold(13.0)
    center = get_rav4_prime_friction_threshold(13.0, 0.0)
    turn = get_rav4_prime_friction_threshold(13.0, 1.0)

    assert center > base * 1.25
    assert turn == pytest.approx(base, rel=0.01)
    assert get_rav4_prime_friction_scale(13.0, 1.0, 0.8) == pytest.approx(1.0)
    assert get_rav4_prime_friction_scale(13.0, 1.0, -0.8) < 1.0

  def test_rav4_prime_output_taper_only_targets_unwind(self):
    assert get_rav4_prime_output_taper_scale(1.0, 0.8, 13.0) == pytest.approx(1.0)
    assert get_rav4_prime_output_taper_scale(-1.0, -0.8, 13.0) == pytest.approx(1.0)

    left_unwind = get_rav4_prime_output_taper_scale(1.0, -0.8, 13.0)
    right_unwind = get_rav4_prime_output_taper_scale(-1.0, 0.8, 13.0)
    hard_left_unwind = get_rav4_prime_output_taper_scale(2.5, -0.8, 13.0)
    hard_right_unwind = get_rav4_prime_output_taper_scale(-2.5, 0.8, 13.0)
    assert right_unwind < left_unwind < 1.0
    assert left_unwind < 0.87
    assert right_unwind < 0.84
    assert hard_left_unwind < left_unwind - 0.02
    assert hard_right_unwind < right_unwind - 0.01
    assert get_rav4_prime_output_taper_scale(-1.0, 0.8, 25.0) > right_unwind

  def test_sienna_4th_gen_turn_in_and_center_shaping(self):
    steady = get_sienna_4th_gen_ff_scale(0.8, 0.0, 9.0)
    turn_in = get_sienna_4th_gen_ff_scale(0.8, 0.8, 9.0)
    high_speed = get_sienna_4th_gen_ff_scale(0.8, 0.8, 30.0)
    assert turn_in > steady >= 1.0
    assert high_speed < turn_in

    base = get_standard_friction_threshold(9.0)
    center = get_sienna_4th_gen_friction_threshold(9.0, 0.0)
    turn = get_sienna_4th_gen_friction_threshold(9.0, 0.8)
    highway_base = get_standard_friction_threshold(28.0)
    highway_center = get_sienna_4th_gen_friction_threshold(28.0, 0.0)
    highway_turn = get_sienna_4th_gen_friction_threshold(28.0, 0.8)
    assert center > turn >= base
    assert highway_center > highway_base
    assert highway_turn < highway_center

    calm = get_sienna_4th_gen_center_taper_scale(0.0, 8.0)
    turn_taper = get_sienna_4th_gen_center_taper_scale(0.8, 8.0)
    highway_calm = get_sienna_4th_gen_center_taper_scale(0.0, 20.0)
    fast = get_sienna_4th_gen_center_taper_scale(0.0, 25.0)
    assert calm < turn_taper <= 1.0
    assert highway_calm < calm < 1.0
    assert fast > calm
    assert get_sienna_4th_gen_high_speed_output_taper_scale(10.0) == pytest.approx(1.0, abs=0.002)
    assert get_sienna_4th_gen_high_speed_output_taper_scale(22.0) < 1.0

  def test_toyota_highlander_tss2_unwind_shaping_is_low_speed_only(self):
    base = get_standard_friction_threshold(9.0)
    steady = get_toyota_highlander_tss2_ff_scale(0.8, 0.0, 9.0)
    unwind = get_toyota_highlander_tss2_ff_scale(0.8, -0.8, 9.0)
    highway_unwind = get_toyota_highlander_tss2_ff_scale(0.8, -0.8, 28.0)

    assert steady == pytest.approx(1.0)
    assert 0.90 < unwind < 1.0
    assert highway_unwind > unwind

    unwind_threshold = get_toyota_highlander_tss2_friction_threshold(9.0, 0.8, -0.8)
    turn_threshold = get_toyota_highlander_tss2_friction_threshold(9.0, 0.8, 0.8)
    assert unwind_threshold > base
    assert turn_threshold == pytest.approx(base, rel=0.01)

    unwind_scale = get_toyota_highlander_tss2_friction_scale(9.0, 0.8, -0.8)
    turn_scale = get_toyota_highlander_tss2_friction_scale(9.0, 0.8, 0.8)
    assert 0.90 < unwind_scale < 1.0
    assert turn_scale == pytest.approx(1.0)

    unwind_output = get_toyota_highlander_tss2_output_taper_scale(0.8, -0.8, 9.0)
    turn_output = get_toyota_highlander_tss2_output_taper_scale(0.8, 0.8, 9.0)
    highway_output = get_toyota_highlander_tss2_output_taper_scale(0.8, -0.8, 28.0)
    assert 0.80 < unwind_output < 1.0
    assert turn_output == pytest.approx(1.0)
    assert highway_output > unwind_output

  def test_rav4_prime_forced_torque_update_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(TOYOTA.TOYOTA_RAV4_PRIME, force_torque=True)
    CS.vEgo = 13.0
    base_output, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    monkeypatch.setattr(latcontrol_torque, "get_rav4_prime_output_taper_scale", lambda *_args: 0.5)
    tapered_controller, tapered_VM, tapered_CS, tapered_params, tapered_toggles = self._build_torque_controller(
      TOYOTA.TOYOTA_RAV4_PRIME, force_torque=True,
    )
    tapered_CS.vEgo = 13.0
    tapered_output, _, _ = tapered_controller.update(
      True, tapered_CS, tapered_VM, tapered_params, False, 0.0025, False, 0.2, None, None, tapered_toggles,
    )

    assert controller.is_rav4_prime
    assert lac_log.active
    assert tapered_output == pytest.approx(base_output * 0.5)

  def test_genesis_g70_angle_output_taper_update_path(self, monkeypatch):
    monkeypatch.setattr(latcontrol_torque, "get_genesis_g70_angle_output_scale", lambda *_args: 1.0)
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.GENESIS_G70_2020)
    CS.vEgo = 15.0
    CS.steeringAngleDeg = 85.0
    base_output, _, lac_log = controller.update(
      True, CS, VM, params, False, 0.004, False, 0.2, None, None, starpilot_toggles,
    )

    monkeypatch.setattr(latcontrol_torque, "get_genesis_g70_angle_output_scale", lambda *_args: 0.5)
    tapered_controller, tapered_VM, tapered_CS, tapered_params, tapered_toggles = self._build_torque_controller(
      HYUNDAI.GENESIS_G70_2020,
    )
    tapered_CS.vEgo = 15.0
    tapered_CS.steeringAngleDeg = 85.0
    tapered_output, _, _ = tapered_controller.update(
      True, tapered_CS, tapered_VM, tapered_params, False, 0.004, False, 0.2, None, None, tapered_toggles,
    )

    assert controller.is_genesis_g70
    assert lac_log.active
    assert base_output != 0.0
    assert tapered_output == pytest.approx(base_output * 0.5)

  def test_ram_1500_transition_taper_curve(self):
    assert get_ram_1500_transition_output_scale(0.4, 0.2, 17.0) == pytest.approx(1.0)
    assert get_ram_1500_transition_output_scale(0.4, 1.1, 8.0) == pytest.approx(1.0)

    center_transition = get_ram_1500_transition_output_scale(0.4, 1.1, 17.0)
    medium_transition = get_ram_1500_transition_output_scale(1.2, -1.1, 17.0)
    assert 0.6 < center_transition < medium_transition < 1.0
    assert get_ram_1500_transition_output_scale(1.85, 2.5, 17.0) == pytest.approx(1.0)

  def test_ram_1500_center_output_taper_is_speed_and_lat_gated(self):
    center = get_ram_1500_center_output_scale(0.0, 10.0)
    near_turn = get_ram_1500_center_output_scale(0.6, 10.0)
    highway = get_ram_1500_center_output_scale(0.0, 25.0)
    crawl = get_ram_1500_center_output_scale(0.0, 2.0)
    assert center < 1.0
    assert near_turn > center
    assert highway > center
    assert crawl > center
    assert center > 0.85

  def test_ram_1500_unwind_output_taper_is_high_speed_and_phase_gated(self):
    turn_in = get_ram_1500_unwind_output_scale(1.2, 1.1, 25.0)
    low_speed = get_ram_1500_unwind_output_scale(1.2, -1.1, 15.0)
    high_speed = get_ram_1500_unwind_output_scale(1.2, -1.1, 25.0)
    sharp_reversal = get_ram_1500_unwind_output_scale(2.4, -2.0, 29.0)

    assert turn_in == pytest.approx(1.0)
    assert low_speed == pytest.approx(1.0)
    assert 0.95 < high_speed < 1.0
    assert sharp_reversal < high_speed
    assert sharp_reversal > 0.80

  def test_ram_1500_phase_feedforward_curve(self):
    assert get_ram_1500_ff_scale(0.0, 1.0, 15.0) == pytest.approx(1.0)
    assert get_ram_1500_ff_scale(1.2, 1.1, 17.0) > 1.0
    assert get_ram_1500_ff_scale(1.2, -1.1, 17.0) < 1.0
    assert get_ram_1500_ff_scale(1.2, 1.1, 6.0) < get_ram_1500_ff_scale(1.2, 1.1, 17.0)

  def test_gmc_yukon_cc_phase_feedforward_curve(self):
    assert get_gmc_yukon_cc_ff_scale(0.0, 1.0, 30.0) == pytest.approx(1.0)
    assert get_gmc_yukon_cc_ff_scale(1.2, 1.1, 30.0) > 1.0
    assert get_gmc_yukon_cc_ff_scale(1.2, -1.1, 30.0) < 1.0
    assert get_gmc_yukon_cc_ff_scale(1.2, 1.1, 8.0) < get_gmc_yukon_cc_ff_scale(1.2, 1.1, 30.0)

  def test_gmc_yukon_cc_phase_feedforward_update_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(GM.GMC_YUKON_CC)
    CS.vEgo = 25.0
    base_output, _, _ = controller.update(
      True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles,
    )

    monkeypatch.setattr(latcontrol_torque, "get_gmc_yukon_cc_ff_scale", lambda *_args: 0.5)
    tuned_controller, tuned_VM, tuned_CS, tuned_params, tuned_toggles = self._build_torque_controller(GM.GMC_YUKON_CC)
    tuned_CS.vEgo = 25.0
    tuned_output, _, _ = tuned_controller.update(
      True, tuned_CS, tuned_VM, tuned_params, False, 0.0025, False, 0.2, None, None, tuned_toggles,
    )

    assert controller.is_gmc_yukon_cc
    assert tuned_output != pytest.approx(base_output)

  def test_ram_1500_jerk_limit_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(CHRYSLER.RAM_1500_5TH_GEN)
    jerk_samples = []
    for i in range(100):
      _, _, lac_log = controller.update(
        True, CS, VM, params, False, 0.0025 * i, False, 0.2, None, None, starpilot_toggles,
      )
      jerk_samples.append(abs(lac_log.desiredLateralJerk))

    assert max(jerk_samples) <= RAM_1500_MAX_LAT_JERK_UP + 1e-6
    assert max(jerk_samples) > RAM_1500_MAX_LAT_JERK_UP - 0.05

  def test_ram_1500_transition_taper_update_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(CHRYSLER.RAM_1500_5TH_GEN)
    base_output, _, lac_log = controller.update(
      True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles,
    )

    monkeypatch.setattr(latcontrol_torque, "get_ram_1500_transition_output_scale", lambda *_args: 0.5)
    tapered_controller, tapered_VM, tapered_CS, tapered_params, tapered_toggles = self._build_torque_controller(
      CHRYSLER.RAM_1500_5TH_GEN,
    )
    tapered_output, _, _ = tapered_controller.update(
      True, tapered_CS, tapered_VM, tapered_params, False, 0.0025, False, 0.2, None, None, tapered_toggles,
    )

    assert controller.is_ram_1500
    assert controller.torque_params.latAccelFactor == pytest.approx(2.0 * RAM_1500_BASE_LAT_ACCEL_FACTOR_MULT)
    assert lac_log.active
    assert tapered_output == pytest.approx(base_output * 0.5)

  def test_ram_1500_transition_taper_preserves_corrective_torque(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(CHRYSLER.RAM_1500_5TH_GEN)
    CS.steeringAngleDeg = -12.0
    base_output, _, _ = controller.update(
      True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles,
    )

    monkeypatch.setattr(latcontrol_torque, "get_ram_1500_transition_output_scale", lambda *_args: 0.5)
    tapered_controller, tapered_VM, tapered_CS, tapered_params, tapered_toggles = self._build_torque_controller(
      CHRYSLER.RAM_1500_5TH_GEN,
    )
    tapered_CS.steeringAngleDeg = -12.0
    tapered_output, _, _ = tapered_controller.update(
      True, tapered_CS, tapered_VM, tapered_params, False, 0.0025, False, 0.2, None, None, tapered_toggles,
    )

    assert base_output > 0.0
    assert tapered_output == pytest.approx(base_output)

  def test_kona_non_scc_highway_transition_taper_curve(self):
    assert get_kona_non_scc_highway_transition_output_scale(0.4, 1.25, 20.0) == pytest.approx(1.0)
    assert get_kona_non_scc_highway_transition_output_scale(0.4, 0.3, 30.0) == pytest.approx(1.0)

    center_transition = get_kona_non_scc_highway_transition_output_scale(0.4, 1.25, 30.0)
    medium_transition = get_kona_non_scc_highway_transition_output_scale(1.1, -1.25, 30.0)
    assert center_transition == pytest.approx(0.76)
    assert center_transition < medium_transition < 1.0
    assert get_kona_non_scc_highway_transition_output_scale(1.65, 2.5, 30.0) == pytest.approx(1.0)

  def test_kona_non_scc_center_taper_curve(self):
    assert get_kona_non_scc_center_taper_scale(0.0, 10.0) == pytest.approx(1.0)
    assert get_kona_non_scc_center_taper_scale(0.0, 25.0) == pytest.approx(0.86)
    assert get_kona_non_scc_center_taper_scale(0.28, 25.0) == pytest.approx(1.0)
    assert get_kona_non_scc_center_taper_scale(0.10, 25.0) < get_kona_non_scc_center_taper_scale(0.10, 15.0)

  def test_kona_non_scc_center_friction_threshold_is_speed_and_center_gated(self):
    low_speed = get_kona_non_scc_friction_threshold(3.0, 0.0)
    highway_base = get_standard_friction_threshold(25.0)
    highway_center = get_kona_non_scc_friction_threshold(25.0, 0.0)
    highway_curve = get_kona_non_scc_friction_threshold(25.0, 0.8)

    assert low_speed == pytest.approx(get_standard_friction_threshold(3.0), abs=0.002)
    assert highway_center > highway_base
    assert highway_curve < highway_center

  def test_kona_non_scc_highway_transition_taper_update_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_KONA_NON_SCC)
    CS.vEgo = 30.0
    base_output, _, lac_log = controller.update(
      True, CS, VM, params, False, 0.0025, False, 0.3, None, None, starpilot_toggles,
    )

    monkeypatch.setattr(latcontrol_torque, "get_kona_non_scc_highway_transition_output_scale", lambda *_args: 0.5)
    tapered_controller, tapered_VM, tapered_CS, tapered_params, tapered_toggles = self._build_torque_controller(
      HYUNDAI.HYUNDAI_KONA_NON_SCC,
    )
    tapered_CS.vEgo = 30.0
    tapered_output, _, _ = tapered_controller.update(
      True, tapered_CS, tapered_VM, tapered_params, False, 0.0025, False, 0.3, None, None, tapered_toggles,
    )

    assert controller.is_kona_non_scc
    assert lac_log.active
    assert tapered_output == pytest.approx(base_output * 0.5)

  def test_kona_non_scc_highway_transition_taper_preserves_corrective_torque(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_KONA_NON_SCC)
    CS.vEgo = 30.0
    CS.steeringAngleDeg = -30.0
    base_output, _, _ = controller.update(
      True, CS, VM, params, False, 0.0025, False, 0.3, None, None, starpilot_toggles,
    )

    monkeypatch.setattr(latcontrol_torque, "get_kona_non_scc_highway_transition_output_scale", lambda *_args: 0.5)
    tapered_controller, tapered_VM, tapered_CS, tapered_params, tapered_toggles = self._build_torque_controller(
      HYUNDAI.HYUNDAI_KONA_NON_SCC,
    )
    tapered_CS.vEgo = 30.0
    tapered_CS.steeringAngleDeg = -30.0
    tapered_output, _, _ = tapered_controller.update(
      True, tapered_CS, tapered_VM, tapered_params, False, 0.0025, False, 0.3, None, None, tapered_toggles,
    )

    assert base_output > 0.0
    assert tapered_output == pytest.approx(base_output)

  def test_ioniq_5_center_taper_curve(self):
    assert get_ioniq_5_center_taper_scale(0.0, 25.0) < get_ioniq_5_center_taper_scale(0.0, 10.0)
    assert get_ioniq_5_center_taper_scale(0.0, 25.0) < get_ioniq_5_center_taper_scale(0.20, 25.0) <= 1.0

  def test_ioniq_5_low_speed_output_limit_preserves_turn_relief(self):
    center = get_ioniq_5_low_speed_output_limit(0.02, 0.05, 3.0)
    turn = get_ioniq_5_low_speed_output_limit(0.70, 0.70, 3.0)
    highway = get_ioniq_5_low_speed_output_limit(0.02, 0.05, 15.0)

    assert center < 0.20
    assert turn > center
    assert highway > center

  def test_ioniq_ev_old_ff_scale_curve(self):
    assert get_ioniq_ev_old_ff_scale(0.0, 0.0, 20.0) == 1.0
    assert get_ioniq_ev_old_ff_scale(0.35, 0.0, 20.0) > get_ioniq_ev_old_ff_scale(-0.35, 0.0, 20.0)
    assert get_ioniq_ev_old_ff_scale(0.35, 0.7, 8.0) > get_ioniq_ev_old_ff_scale(0.35, 0.0, 8.0)
    assert get_ioniq_ev_old_ff_scale(0.35, -0.7, 8.0) < get_ioniq_ev_old_ff_scale(0.35, 0.0, 8.0)
    assert get_ioniq_ev_old_ff_scale(-0.35, -0.7, 8.0) <= get_ioniq_ev_old_ff_scale(-0.35, 0.0, 8.0)

  def test_ioniq_ev_old_center_taper_curve(self):
    assert get_ioniq_ev_old_center_taper_scale(0.0, 30.0) < get_ioniq_ev_old_center_taper_scale(0.0, 15.0)
    assert get_ioniq_ev_old_center_taper_scale(0.0, 30.0) < get_ioniq_ev_old_center_taper_scale(0.20, 30.0) <= 1.0

  def test_ioniq_6_ff_scale_curve(self):
    assert get_ioniq_6_ff_scale(0.0, 0.0, 20.0) == 1.0
    assert get_ioniq_6_ff_scale(0.4, 0.0, 20.0) > get_ioniq_6_ff_scale(-0.4, 0.0, 20.0)
    assert get_ioniq_6_ff_scale(0.4, 0.7, 8.0) > get_ioniq_6_ff_scale(0.4, 0.0, 8.0) > get_ioniq_6_ff_scale(0.4, -0.7, 8.0)
    assert get_ioniq_6_ff_scale(-0.4, -0.7, 8.0) >= get_ioniq_6_ff_scale(-0.4, 0.0, 8.0) >= get_ioniq_6_ff_scale(-0.4, 0.7, 8.0)
    assert get_ioniq_6_ff_scale(-1.2, 0.0, 20.0) < get_ioniq_6_ff_scale(1.2, 0.0, 20.0) < 1.0
    assert get_ioniq_6_ff_scale(-1.2, 0.7, 20.0) <= get_ioniq_6_ff_scale(-1.2, 0.0, 20.0)
    assert get_ioniq_6_ff_scale(0.30, 0.60, 3.0) > get_ioniq_6_ff_scale(0.30, 0.60, 6.0)
    assert get_ioniq_6_ff_scale(0.30, 0.60, 6.0) > get_ioniq_6_ff_scale(0.30, 0.60, 12.0)
    assert get_ioniq_6_ff_scale(0.30, -0.60, 3.0) < get_ioniq_6_ff_scale(0.30, 0.60, 3.0)

  def test_ioniq_6_2023_unwind_ff_scale_only_trims_measured_overshoot(self):
    assert get_ioniq_6_2023_unwind_ff_scale(-1.2, -2.0, 1.0, 18.0) < 1.0
    assert get_ioniq_6_2023_unwind_ff_scale(-1.2, -1.0, 1.0, 18.0) == 1.0
    assert get_ioniq_6_2023_unwind_ff_scale(-1.2, -2.0, -1.0, 18.0) == 1.0
    assert get_ioniq_6_2023_unwind_ff_scale(-1.2, -2.0, 1.0, 30.0) > get_ioniq_6_2023_unwind_ff_scale(-1.2, -2.0, 1.0, 18.0)

  def test_ioniq_6_low_speed_angle_assist_curve(self):
    base = 0.05
    boosted = get_ioniq_6_low_speed_angle_assist_torque(22.0, 0.0, base, 1.0)
    faded = get_ioniq_6_low_speed_angle_assist_torque(22.0, 0.0, base, 4.5)
    unwind = get_ioniq_6_low_speed_angle_assist_torque(22.0, 30.0, base, 1.0)
    opposing = get_ioniq_6_low_speed_angle_assist_torque(-22.0, 0.0, 0.08, 1.0)

    assert boosted < 0.0
    assert faded > boosted
    assert abs(faded - base) < 0.04
    assert unwind > base
    assert opposing > 0.0

  def test_ioniq_6_directional_taper_curve(self):
    assert get_ioniq_6_directional_taper_scale(0.0, 0.0) == 1.0
    assert get_ioniq_6_directional_taper_scale(-0.5, 0.0) < get_ioniq_6_directional_taper_scale(0.5, 0.0) < 1.0
    assert get_ioniq_6_directional_taper_scale(-0.5, 0.7) <= get_ioniq_6_directional_taper_scale(-0.5, 0.0)
    assert get_ioniq_6_directional_taper_scale(-1.2, 0.0) < get_ioniq_6_directional_taper_scale(1.2, 0.0) < 1.0
    assert get_ioniq_6_directional_taper_scale(-1.2, 0.7) <= get_ioniq_6_directional_taper_scale(-1.2, 0.0)
    assert get_ioniq_6_directional_taper_scale(-1.2, 0.25) > get_ioniq_6_directional_taper_scale(-1.2, 0.7)
    assert get_ioniq_6_directional_taper_scale(-1.2, 0.40) > get_ioniq_6_directional_taper_scale(-1.2, 0.7)
    assert get_ioniq_6_directional_taper_scale(1.2, -0.25) > get_ioniq_6_directional_taper_scale(1.2, -0.7)
    assert get_ioniq_6_directional_taper_scale(1.2, -0.40) > get_ioniq_6_directional_taper_scale(1.2, -0.7)
    assert get_ioniq_6_directional_taper_scale(-1.2, -0.40, 8.0) > get_ioniq_6_directional_taper_scale(-1.2, -0.40, 25.0)
    assert get_ioniq_6_directional_taper_scale(1.2, 0.40, 8.0) > get_ioniq_6_directional_taper_scale(1.2, 0.40, 25.0)
    assert get_ioniq_6_directional_taper_scale(-1.2, 1.6, 8.0) < get_ioniq_6_directional_taper_scale(-1.2, 1.6, 25.0)
    assert get_ioniq_6_directional_taper_scale(-0.18, -0.40, 3.0) > get_ioniq_6_directional_taper_scale(-0.18, -0.40, 9.0)
    assert get_ioniq_6_directional_taper_scale(-0.18, -0.40, 9.0) > get_ioniq_6_directional_taper_scale(-0.18, -0.40, 20.0)
    assert get_ioniq_6_directional_taper_scale(-0.50, -0.40, 3.0) > get_ioniq_6_directional_taper_scale(-0.50, -0.40, 6.0)
    assert get_ioniq_6_directional_taper_scale(-0.50, -0.40, 6.0) > get_ioniq_6_directional_taper_scale(-0.50, -0.40, 9.0)
    assert get_ioniq_6_directional_taper_scale(-0.50, -0.40, 9.0) > get_ioniq_6_directional_taper_scale(-0.50, -0.40, 20.0)
    assert get_ioniq_6_directional_taper_scale(-0.70, -0.70, 6.0) > get_ioniq_6_directional_taper_scale(-0.70, -0.70, 12.0)
    assert get_ioniq_6_directional_taper_scale(-0.70, -0.70, 12.0) > get_ioniq_6_directional_taper_scale(-0.70, -0.70, 20.0)
    assert get_ioniq_6_directional_taper_scale(0.30, 0.60, 5.0) > get_ioniq_6_directional_taper_scale(0.30, 0.60, 12.0)
    assert get_ioniq_6_directional_taper_scale(-3.0, 0.45, 10.5) < get_ioniq_6_directional_taper_scale(-3.0, 0.45, 3.0) - 0.10

  def test_ioniq_6_output_taper_curve(self):
    assert get_ioniq_6_output_taper_scale(0.0, 0.0, 25.0) < get_ioniq_6_output_taper_scale(0.0, 0.0, 8.0) <= 1.0
    assert get_ioniq_6_output_taper_scale(-0.5, 0.0, 25.0) < get_ioniq_6_output_taper_scale(0.5, 0.0, 25.0) < 1.0
    assert get_ioniq_6_output_taper_scale(-0.5, 0.7, 25.0) <= get_ioniq_6_output_taper_scale(-0.5, 0.0, 25.0)
    assert get_ioniq_6_output_taper_scale(-1.2, 0.0, 25.0) < get_ioniq_6_output_taper_scale(1.2, 0.0, 25.0) < 1.0
    assert get_ioniq_6_output_taper_scale(-1.2, 0.7, 25.0) <= get_ioniq_6_output_taper_scale(-1.2, 0.0, 25.0)

  def test_ioniq_6_friction_threshold_curve(self):
    base = get_hkg_canfd_base_friction_threshold(6.0)
    left_turn_in = get_ioniq_6_friction_threshold(6.0, 0.5, 0.8)
    right_turn_in = get_ioniq_6_friction_threshold(6.0, -0.5, -0.8)
    left_unwind = get_ioniq_6_friction_threshold(6.0, 0.5, -0.8)
    right_unwind = get_ioniq_6_friction_threshold(6.0, -0.5, 0.8)
    assert max(left_turn_in, right_turn_in) < base
    assert left_unwind >= base
    assert right_unwind >= base
    assert get_ioniq_6_friction_threshold(25.0, 0.0, 0.0) >= get_hkg_canfd_base_friction_threshold(25.0)

  def test_ioniq_6_friction_scale_curve(self):
    base = get_ioniq_6_friction_scale(25.0, 0.5, 0.8)
    left_turn_in = get_ioniq_6_friction_scale(6.0, 0.5, 0.8)
    right_turn_in = get_ioniq_6_friction_scale(6.0, -0.5, -0.8)
    left_unwind = get_ioniq_6_friction_scale(6.0, 0.5, -0.8)
    right_unwind = get_ioniq_6_friction_scale(6.0, -0.5, 0.8)
    assert right_turn_in >= left_turn_in > base
    assert base > left_unwind >= right_unwind

  def test_ioniq_6_friction_center_fade_curve(self):
    # fades friction near zero lateral accel at highway speed, inactive at city speed and in turns
    assert get_ioniq_6_friction_center_fade_scale(0.0, 30.0) < get_ioniq_6_friction_center_fade_scale(0.0, 8.0)
    assert get_ioniq_6_friction_center_fade_scale(0.0, 30.0) < get_ioniq_6_friction_center_fade_scale(0.5, 30.0)
    assert get_ioniq_6_friction_center_fade_scale(0.0, 30.0) >= 0.5
    assert get_ioniq_6_friction_center_fade_scale(0.5, 30.0) > 0.95
    assert get_ioniq_6_friction_center_fade_scale(-0.5, 30.0) > 0.95
    assert get_ioniq_6_friction_center_fade_scale(0.0, 8.0) > 0.95

  def test_ioniq_6_2025_variant_is_firmware_gated(self):
    old_cp = SimpleNamespace(
      carFingerprint=HYUNDAI.HYUNDAI_IONIQ_6,
      carFw=[SimpleNamespace(fwVersion=b"99211-KL000 221213"), SimpleNamespace(fwVersion=b"ADR 1.03 221205")],
    )
    new_cp = SimpleNamespace(
      carFingerprint=HYUNDAI.HYUNDAI_IONIQ_6,
      carFw=[SimpleNamespace(fwVersion=b"99211-KL000 230915"), SimpleNamespace(fwVersion=b"ADR 1.05 240206")],
    )

    assert not is_ioniq_6_2025_model(old_cp)
    assert is_ioniq_6_2025_model(new_cp)
    assert get_ioniq_6_2025_center_output_scale(0.0, 28.0) < get_ioniq_6_2025_center_output_scale(0.5, 28.0)
    assert get_ioniq_6_2025_center_output_scale(0.0, 15.0) > 0.98

  def test_ioniq_6_2025_low_speed_center_scales(self):
    low_speed_center_error = get_ioniq_6_2025_low_speed_center_error_scale(0.02, 0.05, 2.5)
    low_speed_turn_error = get_ioniq_6_2025_low_speed_center_error_scale(0.60, 0.80, 2.5)
    high_speed_center_error = get_ioniq_6_2025_low_speed_center_error_scale(0.02, 0.05, 8.0)
    low_speed_center_friction = get_ioniq_6_2025_low_speed_center_friction_scale(0.02, 0.05, 2.5)

    assert low_speed_center_error < low_speed_turn_error
    assert low_speed_center_error < high_speed_center_error
    assert low_speed_center_friction < 1.0
    assert get_ioniq_6_2025_low_speed_output_limit(0.02, 0.05, 2.5) < get_ioniq_6_2025_low_speed_output_limit(0.60, 0.80, 2.5)
    assert get_ioniq_6_2025_low_speed_output_limit(0.02, 0.05, 2.5) < get_ioniq_6_2025_low_speed_output_limit(0.02, 0.05, 8.0)

  def test_ioniq_6_center_taper_curve(self):
    assert get_ioniq_6_center_taper_scale(0.0, 10.0) > get_ioniq_6_center_taper_scale(0.0, 30.0)
    assert get_ioniq_6_center_taper_scale(0.0, 30.0) < get_ioniq_6_center_taper_scale(0.2, 30.0)
    assert get_ioniq_6_center_taper_scale(0.0, 12.0) < get_ioniq_6_center_taper_scale(0.25, 12.0)
    assert get_ioniq_6_center_taper_scale(0.0, 27.0) < get_ioniq_6_center_taper_scale(0.0, 22.0)
    assert get_ioniq_6_center_taper_scale(0.24, 27.0) > 0.95
    assert get_ioniq_6_center_taper_scale(0.24, 22.0) - get_ioniq_6_center_taper_scale(0.24, 27.0) < 1.0e-2
    assert abs(get_ioniq_6_center_taper_scale(0.2, 30.0) - 1.0) < 7.2e-2

  def test_kia_ev6_base_ff_scale_curve(self):
    assert get_kia_ev6_ff_scale(0.0, 0.0, 20.0) == 1.0
    assert get_kia_ev6_ff_scale(-0.3, 0.0, 20.0) > get_kia_ev6_ff_scale(0.3, 0.0, 20.0)
    assert get_kia_ev6_ff_scale(-0.4, -0.7, 8.0) > get_kia_ev6_ff_scale(-0.4, 0.0, 8.0) > get_kia_ev6_ff_scale(-0.4, 0.7, 8.0)
    assert get_kia_ev6_ff_scale(0.4, 0.7, 8.0) > get_kia_ev6_ff_scale(0.4, 0.0, 8.0) > get_kia_ev6_ff_scale(0.4, -0.7, 8.0)
    assert get_kia_ev6_ff_scale(1.2, 0.0, 20.0) < get_kia_ev6_ff_scale(0.4, 0.0, 20.0)

  def test_kia_ev6_friction_threshold_curve(self):
    base = get_hkg_canfd_base_friction_threshold(6.0)
    left_turn_in = get_kia_ev6_friction_threshold(6.0, 0.5, 0.8)
    right_turn_in = get_kia_ev6_friction_threshold(6.0, -0.5, -0.8)
    left_unwind = get_kia_ev6_friction_threshold(6.0, 0.5, -0.8)
    right_unwind = get_kia_ev6_friction_threshold(6.0, -0.5, 0.8)
    assert right_turn_in == left_turn_in < base < right_unwind == left_unwind
    assert get_kia_ev6_friction_threshold(25.0, 0.0, 0.0) >= get_hkg_canfd_base_friction_threshold(25.0)

  def test_kia_ev6_center_friction_threshold_is_high_speed_only(self):
    low_speed = get_kia_ev6_friction_threshold(10.0, 0.0, 0.0)
    high_speed_center = get_kia_ev6_friction_threshold(34.0, 0.0, 0.0)
    high_speed_curve = get_kia_ev6_friction_threshold(34.0, 0.55, 0.0)

    assert low_speed == pytest.approx(get_hkg_canfd_base_friction_threshold(10.0), abs=0.004)
    assert high_speed_center > get_hkg_canfd_base_friction_threshold(34.0)
    assert high_speed_curve < high_speed_center

  def test_kia_ev6_friction_scale_curve(self):
    base = get_kia_ev6_friction_scale(25.0, 0.5, 0.8)
    left_turn_in = get_kia_ev6_friction_scale(6.0, 0.5, 0.8)
    right_turn_in = get_kia_ev6_friction_scale(6.0, -0.5, -0.8)
    left_unwind = get_kia_ev6_friction_scale(6.0, 0.5, -0.8)
    right_unwind = get_kia_ev6_friction_scale(6.0, -0.5, 0.8)
    assert right_turn_in == left_turn_in > base
    assert base > left_unwind == right_unwind

  def test_lexus_is_ff_scale_curve(self):
    steady_left = get_lexus_is_ff_scale(0.6, 0.0, 22.0)
    turn_in_left = get_lexus_is_ff_scale(0.6, 0.5, 22.0)
    turn_in_right = get_lexus_is_ff_scale(-0.6, -0.5, 22.0)
    unwind_left = get_lexus_is_ff_scale(0.6, -0.5, 22.0)
    unwind_right = get_lexus_is_ff_scale(-0.6, 0.5, 22.0)
    low_speed_unwind_right = get_lexus_is_ff_scale(-0.6, 0.5, 5.0)
    assert steady_left == 1.0
    assert turn_in_left > steady_left
    assert turn_in_right > steady_left
    assert unwind_right < unwind_left < steady_left
    assert unwind_right < low_speed_unwind_right < 1.0

  def test_camry_ff_scale_reduces_high_speed_unwind(self):
    assert get_camry_ff_scale(0.6, 0.0, 22.0) == pytest.approx(1.0)
    assert get_camry_ff_scale(0.6, -0.5, 22.0) < 1.0
    assert get_camry_ff_scale(0.6, -0.5, 5.0) > get_camry_ff_scale(0.6, -0.5, 22.0)

  def test_volt_plexy_friction_threshold_curve(self):
    base = get_gm_base_friction_threshold(6.0)
    left_turn_in = get_volt_plexy_friction_threshold(6.0, 0.7, 0.8)
    right_turn_in = get_volt_plexy_friction_threshold(6.0, -0.7, -0.8)
    left_unwind = get_volt_plexy_friction_threshold(6.0, 0.7, -0.8)
    right_unwind = get_volt_plexy_friction_threshold(6.0, -0.7, 0.8)
    assert right_turn_in < left_turn_in < right_unwind < base < left_unwind

  def test_volt_plexy_friction_scale_curve(self):
    base = get_volt_plexy_friction_scale(25.0, 0.7, 0.8)
    left_turn_in = get_volt_plexy_friction_scale(6.0, 0.7, 0.8)
    right_turn_in = get_volt_plexy_friction_scale(6.0, -0.7, -0.8)
    left_unwind = get_volt_plexy_friction_scale(6.0, 0.7, -0.8)
    right_unwind = get_volt_plexy_friction_scale(6.0, -0.7, 0.8)
    assert left_turn_in == right_turn_in == base
    assert base > left_unwind > right_unwind

  def test_trailer_lateral_assist_is_bounded(self):
    assert get_trailer_lateral_ff_scale(0.0, 30.0, 0.6) == pytest.approx(1.0)
    assert get_trailer_lateral_friction_scale(0.0, 30.0, 0.6) == pytest.approx(1.0)

    ff_scale = get_trailer_lateral_ff_scale(15000.0 * 0.45359237, 35.0, 1.2)
    friction_scale = get_trailer_lateral_friction_scale(15000.0 * 0.45359237, 35.0, 1.2)

    assert 1.0 < ff_scale < 1.05
    assert 1.0 < friction_scale < 1.03

  def test_bolt_2017_default_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(GM.CHEVROLET_BOLT_CC_2017)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active

  def test_bolt_2018_2021_default_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(GM.CHEVROLET_BOLT_CC_2018_2021)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active

  def test_bolt_2022_2023_default_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(GM.CHEVROLET_BOLT_ACC_2022_2023)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active

  def test_bolt_2022_2023_low_speed_center_output_update_path(self, monkeypatch):
    calls = []

    def record_call(output_torque, prev_output_torque, desired_lateral_accel, v_ego):
      calls.append((output_torque, prev_output_torque, desired_lateral_accel, v_ego))
      return 0.0

    monkeypatch.setattr(latcontrol_torque, "get_bolt_2022_2023_low_speed_center_output", record_call)
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(GM.CHEVROLET_BOLT_ACC_2022_2023)
    CS.vEgo = 4.0

    output, _, lac_log = controller.update(
      True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles,
    )

    assert lac_log.active
    assert output == 0.0
    assert calls
    assert calls[0][3] == pytest.approx(4.0)

  def test_volt_standard_testing_ground_update_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(GM.CHEVROLET_VOLT_ASCM)
    monkeypatch.setattr(latcontrol_torque, "volt_standard_lateral_testing_ground_active", lambda: True)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active

  def test_genesis_g90_testing_ground_update_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.GENESIS_G90)
    monkeypatch.setattr(latcontrol_torque, "genesis_g90_lateral_testing_ground_active", lambda: True)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active

  def test_palisade_default_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_PALISADE_2023)
    CarInterface = interfaces[HYUNDAI.HYUNDAI_PALISADE_2023]
    CP = CarInterface.get_non_essential_params(HYUNDAI.HYUNDAI_PALISADE_2023)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert controller.torque_params.latAccelFactor == pytest.approx(CP.lateralTuning.torque.latAccelFactor * 0.98)

  def test_palisade_center_output_taper_update_path(self, monkeypatch):
    monkeypatch.setattr(latcontrol_torque, "get_palisade_center_output_scale", lambda *_args: 1.0)
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_PALISADE_2023)
    CS.vEgo = 30.0
    base_output, _, _ = controller.update(
      True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles,
    )

    monkeypatch.setattr(latcontrol_torque, "get_palisade_center_output_scale", lambda *_args: 0.5)
    tapered_controller, tapered_VM, tapered_CS, tapered_params, tapered_toggles = self._build_torque_controller(
      HYUNDAI.HYUNDAI_PALISADE_2023,
    )
    tapered_CS.vEgo = 30.0
    tapered_output, _, _ = tapered_controller.update(
      True, tapered_CS, tapered_VM, tapered_params, False, 0.0025, False, 0.2, None, None, tapered_toggles,
    )

    assert base_output != 0.0
    assert tapered_output == pytest.approx(base_output * 0.5)

  def test_sonata_default_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_SONATA)
    CarInterface = interfaces[HYUNDAI.HYUNDAI_SONATA]
    CP = CarInterface.get_non_essential_params(HYUNDAI.HYUNDAI_SONATA)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert controller.torque_params.latAccelFactor == pytest.approx(CP.lateralTuning.torque.latAccelFactor)

  def test_genesis_g70_center_output_taper_update_path(self, monkeypatch):
    monkeypatch.setattr(latcontrol_torque, "get_genesis_g70_center_output_scale", lambda *_args: 1.0)
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.GENESIS_G70_2020)
    CS.vEgo = 25.0
    base_output, _, lac_log = controller.update(
      True, CS, VM, params, False, 0.0002, False, 0.2, None, None, starpilot_toggles,
    )

    monkeypatch.setattr(latcontrol_torque, "get_genesis_g70_center_output_scale", lambda *_args: 0.5)
    tapered_controller, tapered_VM, tapered_CS, tapered_params, tapered_toggles = self._build_torque_controller(
      HYUNDAI.GENESIS_G70_2020,
    )
    tapered_CS.vEgo = 25.0
    tapered_output, _, _ = tapered_controller.update(
      True, tapered_CS, tapered_VM, tapered_params, False, 0.0002, False, 0.2, None, None, tapered_toggles,
    )

    assert controller.is_genesis_g70
    assert lac_log.active
    assert controller.starpilot_lateral_state.frictionThreshold > get_standard_friction_threshold(25.0)
    assert base_output != 0.0
    assert tapered_output == pytest.approx(base_output * 0.5)

  def test_genesis_g70_low_speed_output_guard_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.GENESIS_G70_2020)
    CS.vEgo = 2.0
    CS.steeringAngleDeg = 20.0

    output, _, lac_log = controller.update(
      True, CS, VM, params, False, 0.0, False, 0.2, None, None, starpilot_toggles,
    )

    assert controller.is_genesis_g70
    assert lac_log.active
    assert 0.0 < abs(output) <= get_genesis_g70_low_speed_output_limit(0.0, CS.vEgo)

  def test_ioniq_5_default_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_IONIQ_5)
    CarInterface = interfaces[HYUNDAI.HYUNDAI_IONIQ_5]
    CP = CarInterface.get_non_essential_params(HYUNDAI.HYUNDAI_IONIQ_5)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert controller.torque_params.latAccelFactor == pytest.approx(CP.lateralTuning.torque.latAccelFactor * 1.22)

  def test_ioniq_5_low_speed_output_guard_update_path(self, monkeypatch):
    monkeypatch.setattr(latcontrol_torque, "get_ioniq_5_low_speed_output_limit", lambda *_args: 0.05)
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_IONIQ_5)
    CS.vEgo = 3.2

    output, _, lac_log = controller.update(
      True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles,
    )

    assert lac_log.active
    assert abs(output) <= 0.05

  def test_ioniq_6_default_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_IONIQ_6)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert controller.torque_params.latAccelFactor == pytest.approx(3.0 * 1.22)
    assert controller.low_speed_reset_threshold == pytest.approx(0.1 * 0.44704)

  def test_ioniq_6_2025_low_speed_output_limit_update_path(self, monkeypatch):
    monkeypatch.setattr(latcontrol_torque, "get_ioniq_6_2025_low_speed_output_limit", lambda *_args: 0.05)
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_IONIQ_6)
    controller.is_ioniq_6_2025 = True
    CS.vEgo = 3.2

    output, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert abs(output) <= 0.05

  def test_elantra_non_scc_default_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_ELANTRA_HEV_2022_NON_SCC)
    CarInterface = interfaces[HYUNDAI.HYUNDAI_ELANTRA_HEV_2022_NON_SCC]
    CP = CarInterface.get_non_essential_params(HYUNDAI.HYUNDAI_ELANTRA_HEV_2022_NON_SCC)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert controller.torque_params.latAccelFactor == pytest.approx(CP.lateralTuning.torque.latAccelFactor)

  def test_kia_forte_default_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.KIA_FORTE)
    CarInterface = interfaces[HYUNDAI.KIA_FORTE]
    CP = CarInterface.get_non_essential_params(HYUNDAI.KIA_FORTE)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert controller.torque_params.latAccelFactor == pytest.approx(CP.lateralTuning.torque.latAccelFactor * KIA_FORTE_BASE_LAT_ACCEL_FACTOR_MULT)

  @pytest.mark.parametrize("candidate", (HYUNDAI.KIA_CARNIVAL_2025, HYUNDAI.KIA_CARNIVAL_HEV_4TH_GEN))
  def test_kia_carnival_default_update_path(self, candidate):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(candidate)
    CS.vEgo = 8.5

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert controller.is_kia_carnival
    assert lac_log.active

  def test_kia_stinger_2022_near_center_stabilization(self):
    low_speed_center = get_kia_stinger_2022_center_taper_scale(0.0, 4.0)
    highway_center = get_kia_stinger_2022_center_taper_scale(0.0, 20.0)
    highway_moderate = get_kia_stinger_2022_center_taper_scale(0.30, 20.0)
    highway_turn = get_kia_stinger_2022_center_taper_scale(0.60, 20.0)

    assert highway_center < 0.89
    assert highway_center < highway_moderate < highway_turn
    assert low_speed_center > 0.98
    assert highway_turn > 0.99

    base_threshold = get_standard_friction_threshold(20.0)
    center_threshold = get_kia_stinger_2022_friction_threshold(20.0, 0.0)
    turn_threshold = get_kia_stinger_2022_friction_threshold(20.0, 0.60)
    assert center_threshold == pytest.approx(base_threshold * 1.10, rel=0.01)
    assert turn_threshold == pytest.approx(base_threshold, rel=0.01)

  def test_kia_stinger_2022_default_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.KIA_STINGER_2022)
    CS.vEgo = 20.0

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert controller.is_kia_stinger_2022
    assert lac_log.active

  def test_kia_stinger_2022_tapers_near_center_output(self, monkeypatch):
    tapered_controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.KIA_STINGER_2022)
    CS.vEgo = 20.0
    tapered_output, _, _ = tapered_controller.update(
      True, CS, VM, params, False, 0.00025, False, 0.2, None, None, starpilot_toggles,
    )

    monkeypatch.setattr(latcontrol_torque, "get_kia_stinger_2022_center_taper_scale", lambda *_args: 1.0)
    base_controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.KIA_STINGER_2022)
    CS.vEgo = 20.0
    base_output, _, _ = base_controller.update(
      True, CS, VM, params, False, 0.00025, False, 0.2, None, None, starpilot_toggles,
    )

    assert abs(tapered_output) < abs(base_output)

  def test_tucson_4th_gen_low_speed_center_taper_curve(self):
    low_speed_center = get_tucson_4th_gen_center_taper_scale(0.0, 8.5)
    low_speed_moderate = get_tucson_4th_gen_center_taper_scale(0.30, 8.5)
    low_speed_turn = get_tucson_4th_gen_center_taper_scale(0.50, 8.5)
    high_speed_center = get_tucson_4th_gen_center_taper_scale(0.0, 20.0)

    assert low_speed_center < 0.70
    assert low_speed_center < low_speed_moderate < low_speed_turn
    assert low_speed_turn > 0.98
    assert high_speed_center > 0.98

  def test_tucson_4th_gen_friction_threshold_targets_low_speed_center(self):
    base = get_hkg_canfd_base_friction_threshold(8.5)
    low_speed_center = get_tucson_4th_gen_friction_threshold(8.5, 0.0)
    low_speed_turn = get_tucson_4th_gen_friction_threshold(8.5, 0.50)
    high_speed_center = get_tucson_4th_gen_friction_threshold(20.0, 0.0)

    assert low_speed_center == pytest.approx(base * 1.28, rel=0.01)
    assert low_speed_turn == pytest.approx(base, rel=0.01)
    assert high_speed_center == pytest.approx(get_hkg_canfd_base_friction_threshold(20.0), rel=0.01)

  def test_tucson_4th_gen_default_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_TUCSON_4TH_GEN)
    CS.vEgo = 8.5

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert controller.is_tucson_4th_gen
    assert lac_log.active

  def test_tucson_4th_gen_tapers_low_speed_output(self, monkeypatch):
    tapered_controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_TUCSON_4TH_GEN)
    CS.vEgo = 8.5
    tapered_output, _, _ = tapered_controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    monkeypatch.setattr(latcontrol_torque, "get_tucson_4th_gen_center_taper_scale", lambda *_args: 1.0)
    base_controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_TUCSON_4TH_GEN)
    CS.vEgo = 8.5
    base_output, _, _ = base_controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert abs(tapered_output) < abs(base_output)

  def test_ioniq_6_update_path_does_not_post_taper_output(self, monkeypatch):
    base_controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_IONIQ_6)
    base_output, _, _ = base_controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    monkeypatch.setattr(latcontrol_torque, "get_ioniq_6_output_taper_scale", lambda *_args: 0.01)
    tapered_controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_IONIQ_6)
    tapered_output, _, _ = tapered_controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert tapered_output == pytest.approx(base_output)

  def test_honda_pid_gain_scales_update_live_from_opendbc_baseline(self):
    controller, VM, CS, params, _ = self._build_pid_controller(HONDA.HONDA_ACCORD)
    base_kp_v = list(controller.base_kp_v)
    base_ki_v = list(controller.base_ki_v)

    starpilot_toggles = SimpleNamespace(honda_lateral_pid_kp_scale=1.5, honda_lateral_pid_ki_scale=0.75)
    controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert controller.pid._k_p[1] == pytest.approx([value * 1.5 for value in base_kp_v])
    assert controller.pid._k_i[1] == pytest.approx([value * 0.75 for value in base_ki_v])

    starpilot_toggles.honda_lateral_pid_kp_scale = 2.0
    starpilot_toggles.honda_lateral_pid_ki_scale = 1.25
    controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert controller.pid._k_p[1] == pytest.approx([value * 2.0 for value in base_kp_v])
    assert controller.pid._k_i[1] == pytest.approx([value * 1.25 for value in base_ki_v])

  def test_honda_accord_11g_pid_gain_scales_remain_fixed(self):
    controller, VM, CS, params, _ = self._build_pid_controller(HONDA.HONDA_ACCORD_11G)
    base_kp = [list(values) for values in controller.pid._k_p]
    base_ki = [list(values) for values in controller.pid._k_i]

    starpilot_toggles = SimpleNamespace(honda_lateral_pid_kp_scale=2.0, honda_lateral_pid_ki_scale=0.5)
    controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert controller.is_honda_accord_11g
    assert controller.pid._k_p[0] == pytest.approx(base_kp[0])
    assert controller.pid._k_p[1] == pytest.approx(base_kp[1])
    assert controller.pid._k_i[0] == pytest.approx(base_ki[0])
    assert controller.pid._k_i[1] == pytest.approx(base_ki[1])

  def test_honda_accord_torque_tune_uses_quick_curve_unwind(self):
    controller, _, _, _, _ = self._build_torque_controller(HONDA.HONDA_ACCORD, force_torque=True)

    assert controller.is_honda_accord
    assert controller.pid._k_p[1][-1] == pytest.approx(HONDA_ACCORD_TORQUE_KP)
    assert controller.pid._k_i[1] == pytest.approx([HONDA_ACCORD_TORQUE_KI] * len(controller.pid._k_i[1]))

  def test_honda_accord_steer_ratio_calibration(self):
    expected_scale = 14.0 / 16.33
    assert get_honda_accord_steer_ratio_scale(0.0) == pytest.approx(expected_scale)
    assert get_honda_accord_steer_ratio_scale(20.0) == pytest.approx(expected_scale)

  def test_honda_accord_turn_feedforward_taper(self):
    assert get_honda_accord_ff_scale(0.0) > get_honda_accord_ff_scale(0.8)
    assert get_honda_accord_ff_scale(-0.8) == pytest.approx(get_honda_accord_ff_scale(0.8))
    assert get_honda_accord_ff_scale(0.0) == pytest.approx(1.0, abs=0.01)

  def test_subaru_impreza_pid_output_scale_preserves_small_errors(self):
    assert get_subaru_impreza_pid_output_scale(0.0) == 1.0
    assert get_subaru_impreza_pid_output_scale(0.75) == 1.0
    assert get_subaru_impreza_pid_output_scale(2.0) < 1.0
    assert get_subaru_impreza_pid_output_scale(4.0) == pytest.approx(0.58)
    assert get_subaru_impreza_pid_output_scale(-4.0) == pytest.approx(0.58)

  def test_rav4_tss2_pid_output_damps_low_speed_center_reversals(self):
    low_speed = get_rav4_tss2_pid_output(1.0, -1.0, 4.0, 6.0 * 0.44704)
    large_turn = get_rav4_tss2_pid_output(1.0, -1.0, 24.0, 6.0 * 0.44704)
    highway = get_rav4_tss2_pid_output(1.0, -1.0, 4.0, 25.0 * 0.44704)

    assert abs(low_speed) < 0.50
    assert abs(large_turn) > abs(low_speed)
    assert highway > low_speed

  def test_honda_crv_5g_pid_output_damps_low_speed_center_reversals(self):
    low_speed = get_honda_crv_5g_pid_output(1.0, -1.0, 4.0, 8.0 * 0.44704)
    large_turn = get_honda_crv_5g_pid_output(1.0, -1.0, 24.0, 8.0 * 0.44704)
    highway = get_honda_crv_5g_pid_output(1.0, -1.0, 4.0, 25.0 * 0.44704)

    assert abs(low_speed) < 0.50
    assert abs(large_turn) > abs(low_speed)
    assert highway > low_speed

  def test_honda_crv_5g_pid_output_update_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_pid_controller(HONDA.HONDA_CRV_5G)
    CS.vEgo = 8.0 * 0.44704
    CS.steeringAngleDeg = 4.0
    tuned_output, _, lac_log = controller.update(
      True, CS, VM, params, False, 0.0, False, 0.2, None, None, starpilot_toggles,
    )

    monkeypatch.setattr(latcontrol_pid, "get_honda_crv_5g_pid_output", lambda output, *_args: output)
    base_controller, base_VM, base_CS, base_params, base_toggles = self._build_pid_controller(HONDA.HONDA_CRV_5G)
    base_CS.vEgo = 8.0 * 0.44704
    base_CS.steeringAngleDeg = 4.0
    base_output, _, _ = base_controller.update(
      True, base_CS, base_VM, base_params, False, 0.0, False, 0.2, None, None, base_toggles,
    )

    assert controller.is_honda_crv_5g
    assert lac_log.active
    assert abs(tuned_output) < abs(base_output)

  def test_rav4_tss2_torque_center_tune_fades_before_real_turns(self):
    low_speed_center = get_rav4_tss2_center_output_scale(0.05, 8.0)
    low_speed_turn = get_rav4_tss2_center_output_scale(1.0, 8.0)
    highway_center = get_rav4_tss2_center_output_scale(0.05, 22.0)

    assert low_speed_center < low_speed_turn
    assert low_speed_center < highway_center
    assert get_rav4_tss2_friction_threshold(8.0, 0.05) > get_standard_friction_threshold(8.0)
    assert get_rav4_tss2_friction_threshold(8.0, 1.0) == pytest.approx(get_standard_friction_threshold(8.0), rel=0.02)

  def test_rav4_tss2_torque_update_path_applies_center_taper(self, monkeypatch):
    tuned_controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(TOYOTA.TOYOTA_RAV4_TSS2, force_torque=True)
    CS.vEgo = 8.0
    tuned_output, _, lac_log = tuned_controller.update(True, CS, VM, params, False, 0.0, False, 0.2, None, None, starpilot_toggles)

    monkeypatch.setattr(latcontrol_torque, "get_rav4_tss2_center_output_scale", lambda *_args: 1.0)
    base_controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(TOYOTA.TOYOTA_RAV4_TSS2, force_torque=True)
    CS.vEgo = 8.0
    base_output, _, _ = base_controller.update(True, CS, VM, params, False, 0.0, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert abs(tuned_output) < abs(base_output)

  def test_rav4_tss2_pid_output_update_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_pid_controller(TOYOTA.TOYOTA_RAV4_TSS2)
    CS.vEgo = 6.0 * 0.44704
    CS.steeringAngleDeg = 8.0

    tuned_output, _, lac_log = controller.update(True, CS, VM, params, False, 0.0, False, 0.2, None, None, starpilot_toggles)

    monkeypatch.setattr(latcontrol_pid, "get_rav4_tss2_pid_output", lambda output, *_args: output)
    base_controller, VM, CS, params, starpilot_toggles = self._build_pid_controller(TOYOTA.TOYOTA_RAV4_TSS2)
    CS.vEgo = 6.0 * 0.44704
    CS.steeringAngleDeg = 8.0
    base_output, _, _ = base_controller.update(True, CS, VM, params, False, 0.0, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert abs(tuned_output) < abs(base_output)

  def test_subaru_impreza_pid_output_taper_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_pid_controller(SUBARU.SUBARU_IMPREZA)
    CS.steeringAngleDeg = 3.0
    tapered_output, _, lac_log = controller.update(True, CS, VM, params, False, 0.0, False, 0.2, None, None, starpilot_toggles)

    monkeypatch.setattr(latcontrol_pid, "get_subaru_impreza_pid_output_scale", lambda _error: 1.0)
    base_controller, VM, CS, params, starpilot_toggles = self._build_pid_controller(SUBARU.SUBARU_IMPREZA)
    CS.steeringAngleDeg = 3.0
    base_output, _, _ = base_controller.update(True, CS, VM, params, False, 0.0, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert abs(tapered_output) < abs(base_output)

  def test_modified_civic_b_torque_path_uses_fixed_friction_threshold(self, monkeypatch):
    CarInterface = interfaces[HONDA.HONDA_CIVIC_BOSCH]
    CP = CarInterface.get_non_essential_params(HONDA.HONDA_CIVIC_BOSCH)
    CP.flags |= int(HondaFlags.EPS_MODIFIED)
    CP.lateralTuning.init("torque")
    CP.lateralTuning.torque.latAccelFactor = 3.0
    CP.lateralTuning.torque.friction = 0.1
    CI = CarInterface(CP, custom.StarPilotCarParams.new_message())
    controller = LatControlTorque(CP.as_reader(), CI, DT_CTRL)
    VM = VehicleModel(CP)

    CS = car.CarState.new_message()
    CS.vEgo = 12
    CS.steeringPressed = False
    CS.steeringAngleDeg = 1.0

    params = log.LiveParametersData.new_message()
    params.steerRatio = CP.steerRatio
    params.stiffnessFactor = 1.0
    params.roll = 0.0
    params.angleOffsetDeg = 0.0

    captured = {}
    def fake_get_friction(_error, _deadzone, friction_threshold, _torque_params):
      captured["threshold"] = friction_threshold
      return 0.0

    monkeypatch.setattr(latcontrol_torque, "get_friction", fake_get_friction)
    controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, SimpleNamespace())

    assert captured["threshold"] == pytest.approx(0.3)

  def test_modified_civic_b_torque_path_scales_lat_accel_factor(self, monkeypatch):
    CarInterface = interfaces[HONDA.HONDA_CIVIC_BOSCH]
    CP = CarInterface.get_non_essential_params(HONDA.HONDA_CIVIC_BOSCH)
    CP.flags |= int(HondaFlags.EPS_MODIFIED)
    CP.lateralTuning.init("torque")
    CP.lateralTuning.torque.latAccelFactor = 3.0
    CP.lateralTuning.torque.friction = 0.1

    CI = CarInterface(CP, custom.StarPilotCarParams.new_message())
    controller = LatControlTorque(CP.as_reader(), CI, DT_CTRL)

    assert controller.torque_params.latAccelFactor == pytest.approx(3.0 * 1.20)

    monkeypatch.setattr(latcontrol_torque, "civic_bosch_modified_a_lateral_testing_ground_active", lambda: True)
    a_variant_controller = LatControlTorque(CP.as_reader(), CI, DT_CTRL)

    assert a_variant_controller.torque_params.latAccelFactor == pytest.approx(3.0 * 1.20)

    monkeypatch.setattr(latcontrol_torque, "civic_bosch_modified_a_lateral_testing_ground_active", lambda: False)
    monkeypatch.setattr(latcontrol_torque, "civic_bosch_modified_lateral_testing_ground_active", lambda: True)
    variant_controller = LatControlTorque(CP.as_reader(), CI, DT_CTRL)

    assert variant_controller.torque_params.latAccelFactor == pytest.approx(3.0 * 1.20 * 1.75)

  def test_modified_civic_b_torque_ff_scale_curve(self):
    steady_left = get_civic_bosch_modified_b_ff_scale(0.5, 0.0, 12.0)
    steady_right = get_civic_bosch_modified_b_ff_scale(-0.5, 0.0, 12.0)
    turn_in_left = get_civic_bosch_modified_b_ff_scale(0.5, 0.8, 12.0)
    turn_in_right = get_civic_bosch_modified_b_ff_scale(-0.5, -0.8, 12.0)
    unwind_left = get_civic_bosch_modified_b_ff_scale(0.5, -0.8, 12.0)
    unwind_right = get_civic_bosch_modified_b_ff_scale(-0.5, 0.8, 12.0)

    assert steady_left < 1.0
    assert steady_right < 1.0
    assert steady_right < steady_left
    assert turn_in_left > steady_left
    assert turn_in_right >= steady_right
    assert unwind_left < steady_left
    assert unwind_right < steady_right

  def test_modified_civic_b_torque_friction_scale_curve(self):
    turn_in_left = get_civic_bosch_modified_b_friction_scale(12.0, 0.5, 0.8)
    turn_in_right = get_civic_bosch_modified_b_friction_scale(12.0, -0.5, -0.8)
    unwind_left = get_civic_bosch_modified_b_friction_scale(12.0, 0.5, -0.8)
    unwind_right = get_civic_bosch_modified_b_friction_scale(12.0, -0.5, 0.8)

    assert turn_in_left > 1.0
    assert turn_in_right >= 1.0
    assert turn_in_left > turn_in_right
    assert unwind_left < 1.0
    assert unwind_right < unwind_left

  def test_modified_civic_b_variant_extra_torque_shaping_curve(self, monkeypatch):
    base_steady_right = get_civic_bosch_modified_b_ff_scale(-0.5, 0.0, 12.0)
    base_turn_in_right = get_civic_bosch_modified_b_ff_scale(-0.5, -0.8, 12.0)
    base_unwind_right = get_civic_bosch_modified_b_ff_scale(-0.5, 0.8, 12.0)
    base_turn_in_right_friction = get_civic_bosch_modified_b_friction_scale(12.0, -0.5, -0.8)
    base_unwind_right_friction = get_civic_bosch_modified_b_friction_scale(12.0, -0.5, 0.8)

    monkeypatch.setattr(latcontrol_vehicle_tunes, "civic_bosch_modified_lateral_testing_ground_active", lambda: True)

    variant_steady_left = get_civic_bosch_modified_b_ff_scale(0.5, 0.0, 12.0)
    variant_steady_right = get_civic_bosch_modified_b_ff_scale(-0.5, 0.0, 12.0)
    variant_turn_in_right = get_civic_bosch_modified_b_ff_scale(-0.5, -0.8, 12.0)
    variant_unwind_right = get_civic_bosch_modified_b_ff_scale(-0.5, 0.8, 12.0)
    variant_turn_in_left = get_civic_bosch_modified_b_ff_scale(0.5, 0.8, 12.0)
    variant_unwind_right_friction = get_civic_bosch_modified_b_friction_scale(12.0, -0.5, 0.8)
    variant_turn_in_right_friction = get_civic_bosch_modified_b_friction_scale(12.0, -0.5, -0.8)

    assert variant_steady_right < base_steady_right
    assert variant_turn_in_right < base_turn_in_right
    assert variant_turn_in_right >= variant_steady_right
    assert variant_turn_in_left > variant_steady_left
    assert variant_unwind_right < base_unwind_right
    assert variant_unwind_right_friction < base_unwind_right_friction
    assert variant_turn_in_right_friction >= base_turn_in_right_friction

  def test_modified_civic_a_variant_extra_torque_shaping_curve(self, monkeypatch):
    base_steady_left = get_civic_bosch_modified_b_ff_scale(0.5, 0.0, 12.0)
    base_steady_right = get_civic_bosch_modified_b_ff_scale(-0.5, 0.0, 12.0)
    base_turn_in_left = get_civic_bosch_modified_b_ff_scale(0.5, 0.8, 12.0)
    base_turn_in_right = get_civic_bosch_modified_b_ff_scale(-0.5, -0.8, 12.0)
    base_unwind_left = get_civic_bosch_modified_b_ff_scale(0.5, -0.8, 12.0)
    base_unwind_right = get_civic_bosch_modified_b_ff_scale(-0.5, 0.8, 12.0)
    base_turn_in_right_friction = get_civic_bosch_modified_b_friction_scale(12.0, -0.5, -0.8)
    base_unwind_left_friction = get_civic_bosch_modified_b_friction_scale(12.0, 0.5, -0.8)
    monkeypatch.setattr(latcontrol_vehicle_tunes, "civic_bosch_modified_a_lateral_testing_ground_active", lambda: True)

    a_variant_steady_left = get_civic_bosch_modified_b_ff_scale(0.5, 0.0, 12.0)
    a_variant_steady_right = get_civic_bosch_modified_b_ff_scale(-0.5, 0.0, 12.0)
    a_variant_turn_in_left = get_civic_bosch_modified_b_ff_scale(0.5, 0.8, 12.0)
    a_variant_turn_in_right = get_civic_bosch_modified_b_ff_scale(-0.5, -0.8, 12.0)
    a_variant_unwind_left = get_civic_bosch_modified_b_ff_scale(0.5, -0.8, 12.0)
    a_variant_unwind_right = get_civic_bosch_modified_b_ff_scale(-0.5, 0.8, 12.0)
    a_variant_turn_in_right_friction = get_civic_bosch_modified_b_friction_scale(12.0, -0.5, -0.8)
    a_variant_unwind_left_friction = get_civic_bosch_modified_b_friction_scale(12.0, 0.5, -0.8)
    a_variant_unwind_right_friction = get_civic_bosch_modified_b_friction_scale(12.0, -0.5, 0.8)

    assert a_variant_steady_left < base_steady_left
    assert a_variant_steady_right > base_steady_right
    assert a_variant_turn_in_left < base_turn_in_left
    assert a_variant_turn_in_right > base_turn_in_right
    assert a_variant_unwind_left < base_unwind_left
    assert a_variant_unwind_right > (base_unwind_right * 0.95)
    assert a_variant_turn_in_right_friction > base_turn_in_right_friction
    assert a_variant_unwind_left_friction < base_unwind_left_friction
    assert a_variant_unwind_right_friction >= 0.82

  def test_modified_civic_a_variant_center_taper_curve(self):
    assert get_civic_bosch_modified_a_center_taper_scale(0.0, 25.0) < get_civic_bosch_modified_a_center_taper_scale(0.0, 10.0)
    assert get_civic_bosch_modified_a_center_taper_scale(0.0, 25.0) < get_civic_bosch_modified_a_center_taper_scale(0.35, 25.0) <= 1.0

  def test_kia_ev6_default_update_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.KIA_EV6)
    calls = 0

    def record_ff_scale(*_args):
      nonlocal calls
      calls += 1
      return 1.0

    monkeypatch.setattr(latcontrol_torque, "get_kia_ev6_ff_scale", record_ff_scale)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert calls == 1

  def test_lexus_is_update_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(TOYOTA.LEXUS_IS)
    calls = 0

    def record_ff_scale(*_args):
      nonlocal calls
      calls += 1
      return 1.0

    monkeypatch.setattr(latcontrol_torque, "get_lexus_is_ff_scale", record_ff_scale)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert calls == 1

  def test_kia_ev6_ff_scale_curve(self):
    clear_flm_runtime_overrides()
    assert get_kia_ev6_ff_scale(0.0, 0.0, 20.0) == 1.0
    steady_left = get_kia_ev6_ff_scale(0.45, 0.0, 25.0)
    steady_right = get_kia_ev6_ff_scale(-0.45, 0.0, 25.0)
    turn_in_left = get_kia_ev6_ff_scale(0.45, 0.7, 10.0)
    turn_in_right = get_kia_ev6_ff_scale(-0.45, -0.7, 10.0)
    unwind_left = get_kia_ev6_ff_scale(0.45, -0.7, 10.0)
    unwind_right = get_kia_ev6_ff_scale(-0.45, 0.7, 10.0)
    assert steady_left > 1.0
    assert steady_right > steady_left
    assert turn_in_left > steady_left
    assert turn_in_right > steady_right
    assert unwind_left < steady_left
    assert unwind_right < steady_right
    assert unwind_left < 0.98
    assert unwind_right < 0.98

  def test_kia_ev6_jwarm_testing_ground_phase_correction(self, monkeypatch):
    clear_flm_runtime_overrides()
    monkeypatch.setattr(latcontrol_vehicle_tunes, "kia_ev6_lateral_testing_ground_active", lambda: False)
    normal_steady = get_kia_ev6_ff_scale(0.45, 0.0, 10.0)
    normal_turn_in_left = get_kia_ev6_ff_scale(0.45, 0.7, 10.0)
    normal_turn_in_right = get_kia_ev6_ff_scale(-0.45, -0.7, 10.0)
    normal_unwind_left = get_kia_ev6_ff_scale(0.45, -0.7, 10.0)
    normal_unwind_right = get_kia_ev6_ff_scale(-0.45, 0.7, 10.0)

    monkeypatch.setattr(latcontrol_vehicle_tunes, "kia_ev6_lateral_testing_ground_active", lambda: True)
    assert get_kia_ev6_ff_scale(0.45, 0.0, 10.0) == pytest.approx(normal_steady)
    assert get_kia_ev6_ff_scale(0.45, 0.7, 10.0) > normal_turn_in_left + 0.08
    assert get_kia_ev6_ff_scale(-0.45, -0.7, 10.0) > normal_turn_in_right + 0.10
    assert get_kia_ev6_ff_scale(0.45, -0.7, 10.0) < normal_unwind_left - 0.04
    assert get_kia_ev6_ff_scale(-0.45, 0.7, 10.0) < normal_unwind_right - 0.02

  def test_kia_ev6_jwarm_abrupt_low_speed_phase_correction_is_bounded(self):
    calm_low_speed = get_kia_ev6_jwarm_phase_confidence(6.0, 0.25)
    abrupt_low_speed = get_kia_ev6_jwarm_phase_confidence(6.0, 1.40)
    abrupt_high_speed = get_kia_ev6_jwarm_phase_confidence(18.0, 1.40)

    assert abrupt_low_speed < calm_low_speed
    assert abrupt_low_speed < abrupt_high_speed
    assert 0.75 <= abrupt_low_speed < 0.82
    assert calm_low_speed > 0.90
    assert abrupt_high_speed > 0.98

  def test_kia_ev6_center_taper_curve(self):
    assert get_kia_ev6_center_taper_scale(0.0, 25.0) < get_kia_ev6_center_taper_scale(0.0, 10.0)
    assert get_kia_ev6_center_taper_scale(0.0, 25.0) < get_kia_ev6_center_taper_scale(0.20, 25.0) <= 1.0

  def test_kia_ev6_center_output_taper_curve(self):
    assert get_kia_ev6_center_output_scale(0.0, 10.0) > get_kia_ev6_center_output_scale(0.0, 20.0)
    assert get_kia_ev6_center_output_scale(0.0, 20.0) < get_kia_ev6_center_output_scale(0.5, 20.0)
    assert get_kia_ev6_center_output_scale(0.0, 20.0) > 0.86

  def test_kia_ev6_center_output_taper_update_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.KIA_EV6)
    base_output, _, _ = controller.update(
      True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles,
    )

    monkeypatch.setattr(latcontrol_torque, "get_kia_ev6_center_output_scale", lambda *_args: 0.5)
    tapered_controller, tapered_VM, tapered_CS, tapered_params, tapered_toggles = self._build_torque_controller(HYUNDAI.KIA_EV6)
    tapered_output, _, _ = tapered_controller.update(
      True, tapered_CS, tapered_VM, tapered_params, False, 0.0025, False, 0.2, None, None, tapered_toggles,
    )

    assert abs(tapered_output) < abs(base_output)

  def test_volt_plexy_testing_ground_update_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(GM.CHEVROLET_VOLT_CC)
    monkeypatch.setattr(latcontrol_torque, "volt_plexy_lateral_testing_ground_active", lambda: True)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active

  def test_civic_bosch_modified_pid_scale_curve(self):
    assert get_civic_bosch_modified_pid_output_scale(0.0, 0.0, 12.0) < 1.0
    assert get_civic_bosch_modified_pid_output_scale(8.0, 0.0, 12.0) < 1.0
    assert get_civic_bosch_modified_pid_output_scale(10.0, 0.0, 12.0) < 1.0
    assert get_civic_bosch_modified_pid_output_scale(12.0, 0.0, 12.0) < 1.0
    assert get_civic_bosch_modified_pid_output_scale(14.0, 0.0, 12.0) < 1.0
    assert get_civic_bosch_modified_pid_output_scale(-16.0, 0.0, 12.0) < 1.0
    assert get_civic_bosch_modified_pid_output_scale(16.0, 0.0, 12.0) > get_civic_bosch_modified_pid_output_scale(-16.0, 0.0, 12.0)
    assert get_civic_bosch_modified_pid_output_scale(0.0, 0.0, 6.0) < 0.9
    assert get_civic_bosch_modified_pid_output_scale(18.0, 0.0, 12.0) > get_civic_bosch_modified_pid_output_scale(8.0, 0.0, 12.0)
    assert get_civic_bosch_modified_pid_output_scale(20.0, 0.5, 12.0) > get_civic_bosch_modified_pid_output_scale(20.0, 0.0, 12.0)
    assert get_civic_bosch_modified_pid_output_scale(-20.0, -0.5, 12.0) < get_civic_bosch_modified_pid_output_scale(-20.0, 0.0, 12.0)
    assert get_civic_bosch_modified_pid_output_scale(20.0, -0.5, 12.0) < get_civic_bosch_modified_pid_output_scale(20.0, 0.0, 12.0)
    assert get_civic_bosch_modified_pid_output_scale(-20.0, 0.5, 12.0) < get_civic_bosch_modified_pid_output_scale(-20.0, 0.0, 12.0)
    assert get_civic_bosch_modified_pid_output_scale(20.0, 0.5, 12.0) > get_civic_bosch_modified_pid_output_scale(-20.0, -0.5, 12.0)
    assert get_civic_bosch_modified_pid_output_scale(-20.0, -0.5, 4.0) > get_civic_bosch_modified_pid_output_scale(-20.0, -0.5, 12.0)

  def test_civic_bosch_modified_pid_output_alpha_curve(self):
    assert get_civic_bosch_modified_pid_output_alpha(0.0, 0.0, 12.0, 0.2, 0.1) == 1.0
    assert get_civic_bosch_modified_pid_output_alpha(8.0, 0.0, 12.0, 0.2, 0.1) < 1.0
    assert get_civic_bosch_modified_pid_output_alpha(8.0, 0.4, 12.0, 0.2, 0.1) < get_civic_bosch_modified_pid_output_alpha(8.0, 0.0, 12.0, 0.2, 0.1)
    assert get_civic_bosch_modified_pid_output_alpha(8.0, 0.4, 20.0, -0.2, 0.2) < get_civic_bosch_modified_pid_output_alpha(8.0, 0.4, 8.0, -0.2, 0.2)
    assert get_civic_bosch_modified_pid_output_alpha(24.0, 0.0, 12.0, 0.2, 0.1) == 1.0

  def test_civic_bosch_modified_pid_testing_ground_update_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_pid_controller(HONDA.HONDA_CIVIC_BOSCH)
    monkeypatch.setattr(latcontrol_pid, "civic_bosch_modified_lateral_testing_ground_active", lambda: True)

    base_output, _, lac_log = controller.update(True, CS, VM, params, False, 0.004, False, 0.2, None, None, starpilot_toggles)
    assert lac_log.active

    # Use a second update to create a turn-in phase with a larger desired angle delta.
    tuned_output, _, _ = controller.update(True, CS, VM, params, False, 0.006, False, 0.2, None, None, starpilot_toggles)

    assert abs(tuned_output) >= abs(base_output)

  @parameterized.expand([(HONDA.HONDA_CIVIC, LatControlPID), (TOYOTA.TOYOTA_RAV4, LatControlTorque),
                         (NISSAN.NISSAN_LEAF, LatControlAngle), (GM.CHEVROLET_BOLT_ACC_2022_2023, LatControlTorque)])
  def test_saturation(self, car_name, controller):
    CarInterface = interfaces[car_name]
    CP = CarInterface.get_non_essential_params(car_name)
    CI = CarInterface(CP, custom.StarPilotCarParams.new_message())
    VM = VehicleModel(CP)

    controller = controller(CP.as_reader(), CI, DT_CTRL)

    CS = car.CarState.new_message()
    CS.vEgo = 30
    CS.steeringPressed = False

    params = log.LiveParametersData.new_message()
    starpilot_toggles = SimpleNamespace()

    # Saturate for curvature limited and controller limited
    for _ in range(1000):
      _, _, lac_log = controller.update(True, CS, VM, params, False, 0, True, 0.2, None, None, starpilot_toggles)
    assert lac_log.saturated

    for _ in range(1000):
      _, _, lac_log = controller.update(True, CS, VM, params, False, 0, False, 0.2, None, None, starpilot_toggles)
    assert not lac_log.saturated

    for _ in range(1000):
      _, _, lac_log = controller.update(True, CS, VM, params, False, 1, False, 0.2, None, None, starpilot_toggles)
    assert lac_log.saturated
