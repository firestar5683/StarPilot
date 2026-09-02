import sys
import types
from types import SimpleNamespace
import numpy as np
import pytest

from opendbc.car import structs

fake_interfaces = types.ModuleType("opendbc.car.interfaces")


class _FakeCarControllerBase:
  def __init__(self, dbc_names=None, CP=None):
    self.CP = CP


fake_interfaces.CarControllerBase = _FakeCarControllerBase
sys.modules.setdefault("opendbc.car.interfaces", fake_interfaces)

fake_params = types.ModuleType("openpilot.common.params")


class _FakeParams:
  pass


class _FakeUnknownKeyName(Exception):
  pass


fake_params.Params = _FakeParams
fake_params.UnknownKeyName = _FakeUnknownKeyName
sys.modules.setdefault("openpilot.common.params", fake_params)

fake_testing_grounds = types.ModuleType("openpilot.starpilot.common.testing_grounds")
fake_testing_grounds.testing_ground = SimpleNamespace(use_1=False)
sys.modules.setdefault("openpilot.starpilot.common.testing_grounds", fake_testing_grounds)

from opendbc.car.gm.carcontroller import (
  AUTO_HOLD_DRIVE_GEARS,
  CarController,
  estimate_auto_hold_brake,
  get_adas_keepalive_step,
  get_auto_hold_stop_threshold,
  get_bolt_acc_pedal_friction_brake,
  get_bolt_acc_pedal_friction_command_state,
  get_bolt_acc_pedal_effective_brake_switch,
  get_bolt_acc_pedal_planner_brake_switch,
  get_bolt_pedal_long_accel_limit,
  get_interceptor_sng_gas_cmd,
  get_lka_steering_cmd_counter,
  get_volt_one_pedal_target_decel,
  get_testing_ground_1_brake_switch_bias,
  get_acc_dashboard_status_active,
  get_stock_cc_active_for_cancel,
  limit_grade_feedforward,
  shape_bolt_acc_pedal_low_speed_friction,
  shape_truck_friction_brake,
  shape_truck_pitch_accel,
  shape_truck_positive_accel,
  smooth_truck_follow_accel,
  should_use_fixed_stopping_brake,
  should_activate_auto_hold,
  should_activate_volt_one_pedal,
  should_send_acc_2cd,
  should_send_adas_status,
  should_send_stock_long_cancel,
  should_spoof_dash_speed,
  should_spoof_ecm_cruise_status,
  supports_bolt_acc_pedal_friction_experiment,
  supports_volt_auto_hold,
  supports_volt_one_pedal,
  use_interceptor_sng_launch,
)
from opendbc.car.gm.gmcan import get_friction_brake_mode
from opendbc.car.gm.values import AccState, CAR, CarControllerParams, GMFlags
from opendbc.car.structs import CarParams
from opendbc.car.common.conversions import Conversions as CV


def _cs(enabled, pcm_acc_status):
  return SimpleNamespace(
    out=SimpleNamespace(cruiseState=SimpleNamespace(enabled=enabled), accFaulted=False),
    pcm_acc_status=pcm_acc_status,
  )


def _sng_cs(v_ego, standstill, cruise_standstill):
  return SimpleNamespace(
    out=SimpleNamespace(
      vEgo=v_ego,
      standstill=standstill,
      cruiseState=SimpleNamespace(standstill=cruise_standstill),
    ),
  )


def _controller(car_fingerprint=CAR.CHEVROLET_BOLT_CC_2018_2021):
  controller = CarController.__new__(CarController)
  controller.CP = SimpleNamespace(carFingerprint=car_fingerprint)
  controller.planner_regen_hold = False
  controller.regen_paddle_pressed = False
  controller.regen_paddle_timer = 0
  controller.regen_press_counter = 0
  controller.regen_release_counter = 0
  controller.regen_min_on_frames = 0
  controller.regen_min_off_frames = 0
  controller.pedal_active_last = False
  controller.pedal_steady = 0.0
  controller.aego = 0.0
  controller.maneuver_paddle_mode = "auto"
  controller.bolt_acc_pedal_friction_low_speed_active = False
  return controller


def test_gen1_bolt_pedal_cancel_uses_pcm_acc_status():
  CP = SimpleNamespace(carFingerprint=CAR.CHEVROLET_BOLT_CC_2018_2021)

  assert get_stock_cc_active_for_cancel(CP, _cs(False, AccState.ACTIVE))


def test_gen2_bolt_acc_pedal_cancel_uses_enabled_only():
  CP = SimpleNamespace(carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL)

  assert not get_stock_cc_active_for_cancel(CP, _cs(False, AccState.ACTIVE))


def test_bolt_acc_pedal_friction_experiment_is_single_fingerprint_only():
  assert supports_bolt_acc_pedal_friction_experiment(SimpleNamespace(
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
    openpilotLongitudinalControl=True,
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
  ))
  assert not supports_bolt_acc_pedal_friction_experiment(SimpleNamespace(
    carFingerprint=CAR.CHEVROLET_MALIBU_HYBRID_CC,
    openpilotLongitudinalControl=True,
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
  ))
  assert not supports_bolt_acc_pedal_friction_experiment(SimpleNamespace(
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
    openpilotLongitudinalControl=False,
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
  ))


def test_bolt_acc_pedal_friction_blend_preserves_zero_before_crossover():
  params = SimpleNamespace(ACCEL_MIN=-4.0, MAX_BRAKE=400)

  assert get_bolt_acc_pedal_friction_brake(0, -2.8, 20.0, params) == 0


def test_bolt_acc_pedal_friction_blend_uses_full_brake_range_after_regen():
  params = SimpleNamespace(ACCEL_MIN=-4.0, MAX_BRAKE=400)

  # Legacy mapping tops out early once regen has already consumed part of the
  # decel request. The experiment remaps that reduced span back to full scale.
  assert get_bolt_acc_pedal_friction_brake(286, -2.86, 20.0, params) == 400


def test_bolt_acc_pedal_friction_blend_biases_small_commands_upward_at_speed():
  params = SimpleNamespace(ACCEL_MIN=-4.0, MAX_BRAKE=400)

  low_speed = get_bolt_acc_pedal_friction_brake(31, -2.86, 0.0, params)
  high_speed = get_bolt_acc_pedal_friction_brake(31, -2.86, 20.0, params)

  assert low_speed > 31
  assert high_speed > low_speed


def test_bolt_acc_pedal_friction_blend_applies_a_minimum_pre_stop_command_at_speed():
  params = SimpleNamespace(ACCEL_MIN=-4.0, MAX_BRAKE=400)

  assert get_bolt_acc_pedal_friction_brake(2, -2.86, 17.0, params) >= 18


def test_bolt_acc_pedal_friction_blend_boosts_midrange_commands_before_stopping_phase():
  params = SimpleNamespace(ACCEL_MIN=-4.0, MAX_BRAKE=400)

  assert get_bolt_acc_pedal_friction_brake(40, -2.86, 15.0, params) >= 80


def test_bolt_acc_pedal_low_speed_friction_ignores_tiny_inactive_brake_requests():
  apply_brake, active = shape_bolt_acc_pedal_low_speed_friction(9, 5.0, False, False)

  assert apply_brake == 0
  assert not active


def test_bolt_acc_pedal_low_speed_friction_uses_hysteresis_once_active():
  apply_brake, active = shape_bolt_acc_pedal_low_speed_friction(24, 3.0, False, False)
  assert apply_brake == 24
  assert active

  apply_brake, active = shape_bolt_acc_pedal_low_speed_friction(5, 3.0, False, active)
  assert apply_brake == 0
  assert not active


def test_bolt_acc_pedal_low_speed_friction_fades_out_at_standstill():
  apply_brake, active = shape_bolt_acc_pedal_low_speed_friction(80, 0.2, True, True)

  assert apply_brake == 0
  assert not active


def test_bolt_acc_pedal_low_speed_friction_preserves_rolling_stop_authority():
  apply_brake, active = shape_bolt_acc_pedal_low_speed_friction(80, 1.2, True, True)

  assert 0 < apply_brake < 80
  assert active


def test_bolt_acc_pedal_low_speed_friction_drops_out_before_two_clamp():
  apply_brake, active = shape_bolt_acc_pedal_low_speed_friction(80, 0.9, True, True)

  assert apply_brake == 0
  assert not active


def test_bolt_pedal_long_accel_limit_matches_planner_regen_envelope():
  assert get_bolt_pedal_long_accel_limit(6.66) == pytest.approx(-2.379, abs=1e-3)
  assert get_bolt_pedal_long_accel_limit(3.0) == pytest.approx(-1.70, abs=1e-3)


def test_bolt_acc_pedal_planner_brake_switch_is_lower_than_stock_switch():
  params = SimpleNamespace(ZERO_GAS=6150, BRAKE_SWITCH_LOOKUP_BP=[0.5, 10.0], BRAKE_SWITCH_LOOKUP_V=[6150, 5500])
  v_ego = 6.66

  stock_switch = int(round(np.interp(v_ego, params.BRAKE_SWITCH_LOOKUP_BP, params.BRAKE_SWITCH_LOOKUP_V)))
  planner_switch = get_bolt_acc_pedal_planner_brake_switch(
    v_ego, params, tire_radius=0.336, mass=1832.0, coeff_drag=0.30, frontal_area=2.35, air_density=1.225,
  )

  assert planner_switch < stock_switch


def test_bolt_acc_pedal_effective_brake_switch_never_suppresses_stock_friction():
  params = SimpleNamespace(ZERO_GAS=6150, BRAKE_SWITCH_LOOKUP_BP=[0.5, 10.0], BRAKE_SWITCH_LOOKUP_V=[6150, 5500])
  v_ego = 5.434
  mass = 1805.0
  tire_radius = 0.075 * 2.63779 + 0.1453
  frontal_area = 1.05 * 2.63779 + 0.0679
  coeff_drag = 0.30
  air_density = 1.225
  accel_cmd = -1.399

  aero_drag_force = 0.5 * coeff_drag * frontal_area * air_density * v_ego ** 2
  torque = tire_radius * ((mass * accel_cmd) + aero_drag_force)
  scaled_torque = torque + params.ZERO_GAS

  stock_switch = int(round(np.interp(v_ego, params.BRAKE_SWITCH_LOOKUP_BP, params.BRAKE_SWITCH_LOOKUP_V)))
  planner_switch = get_bolt_acc_pedal_planner_brake_switch(
    v_ego, params, tire_radius=tire_radius, mass=mass,
    coeff_drag=coeff_drag, frontal_area=frontal_area, air_density=air_density,
  )
  effective_switch = get_bolt_acc_pedal_effective_brake_switch(stock_switch, planner_switch)

  stock_brake_accel = min((scaled_torque - stock_switch) / (tire_radius * mass), 0)
  effective_brake_accel = min((scaled_torque - effective_switch) / (tire_radius * mass), 0)

  assert planner_switch < stock_switch
  assert effective_switch == stock_switch
  assert stock_brake_accel < 0
  assert effective_brake_accel == stock_brake_accel


def test_bolt_acc_pedal_friction_command_state_requires_cruise_main_for_positive_brake():
  command_brake, release_frames, should_send = get_bolt_acc_pedal_friction_command_state(120, False, 0)

  assert command_brake == 0
  assert release_frames == 0
  assert not should_send


def test_bolt_acc_pedal_friction_command_state_sends_zero_unwind_after_main_off():
  command_brake, release_frames, should_send = get_bolt_acc_pedal_friction_command_state(120, True, 0)

  assert command_brake == 120
  assert release_frames > 0
  assert should_send

  command_brake, release_frames, should_send = get_bolt_acc_pedal_friction_command_state(0, False, release_frames)

  assert command_brake == 0
  assert release_frames >= 0
  assert should_send


def test_fixed_stopping_brake_is_disabled_for_bolt_acc_pedal_experiment():
  CP = SimpleNamespace(
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
    openpilotLongitudinalControl=True,
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
  )

  assert not should_use_fixed_stopping_brake(CP, True, True, False)


def test_fixed_stopping_brake_stays_enabled_for_normal_acc_path():
  CP = SimpleNamespace(
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023,
    openpilotLongitudinalControl=True,
    enableGasInterceptorDEPRECATED=False,
    flags=0,
  )

  assert should_use_fixed_stopping_brake(CP, True, True, False)
  assert not should_use_fixed_stopping_brake(CP, False, True, False)
  assert not should_use_fixed_stopping_brake(CP, True, False, False)
  assert not should_use_fixed_stopping_brake(CP, True, True, True)


def test_stock_cancel_is_suppressed_when_acc_is_faulted():
  CP = SimpleNamespace(carFingerprint=CAR.CHEVROLET_VOLT_CAMERA)
  cs = _cs(True, AccState.FAULTED)
  cs.out.accFaulted = True

  assert get_stock_cc_active_for_cancel(CP, cs)
  assert not should_send_stock_long_cancel(11, cs)


def test_stock_cancel_requires_delay_and_no_acc_fault():
  cs = _cs(True, AccState.ACTIVE)

  assert not should_send_stock_long_cancel(10, cs)
  assert should_send_stock_long_cancel(11, cs)


def test_gen1_bolt_pedal_ecm_cruise_spoof_is_not_gated_by_dash_speed_toggle():
  CP = SimpleNamespace(
    carFingerprint=CAR.CHEVROLET_BOLT_CC_2018_2021,
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    openpilotLongitudinalControl=True,
  )

  assert not should_spoof_dash_speed(CP, SimpleNamespace(disable_openpilot_long=True, gm_pedal_longitudinal=True))
  assert should_spoof_ecm_cruise_status(CP)


def test_gateway_keepalive_uses_gateway_cadence():
  cp = SimpleNamespace(networkLocation=CarParams.NetworkLocation.gateway, flags=0)

  assert get_adas_keepalive_step(cp, is_kaofui_car=True) == 100
  assert get_adas_keepalive_step(cp, is_kaofui_car=False) == 200


def test_removed_camera_keepalive_uses_camera_cadence():
  cp = SimpleNamespace(networkLocation=CarParams.NetworkLocation.fwdCamera, flags=GMFlags.NO_CAMERA.value)

  assert get_adas_keepalive_step(cp, is_kaofui_car=True) == 100


def test_live_camera_path_does_not_send_pt_keepalive():
  cp = SimpleNamespace(networkLocation=CarParams.NetworkLocation.fwdCamera, flags=0)

  assert get_adas_keepalive_step(cp, is_kaofui_car=True) is None


def test_acc_2cd_replacement_only_used_with_live_camera_path():
  assert should_send_acc_2cd(SimpleNamespace(
    carFingerprint=CAR.CHEVROLET_TRAILBLAZER, networkLocation=CarParams.NetworkLocation.fwdCamera, flags=0))
  assert should_send_acc_2cd(SimpleNamespace(
    carFingerprint=CAR.CHEVROLET_SILVERADO, networkLocation=CarParams.NetworkLocation.fwdCamera, flags=0))
  assert not should_send_acc_2cd(SimpleNamespace(
    carFingerprint=CAR.CHEVROLET_TRAILBLAZER, networkLocation=CarParams.NetworkLocation.fwdCamera, flags=GMFlags.NO_CAMERA.value))
  assert not should_send_acc_2cd(SimpleNamespace(
    carFingerprint=CAR.CHEVROLET_TRAILBLAZER, networkLocation=CarParams.NetworkLocation.gateway, flags=0))
  assert not should_send_acc_2cd(SimpleNamespace(
    carFingerprint=CAR.CHEVROLET_TRAILBLAZER_CC, networkLocation=CarParams.NetworkLocation.fwdCamera, flags=0))
  assert not should_send_acc_2cd(SimpleNamespace(
    carFingerprint=CAR.CHEVROLET_BLAZER, networkLocation=CarParams.NetworkLocation.fwdCamera, flags=0))


def test_ascm_int_cars_do_not_send_radar_status():
  common = {
    "networkLocation": CarParams.NetworkLocation.fwdCamera,
    "radarUnavailable": False,
  }

  assert not should_send_adas_status(SimpleNamespace(carFingerprint=CAR.BUICK_LACROSSE_ASCM, **common), is_kaofui_car=True)
  assert not should_send_adas_status(SimpleNamespace(carFingerprint=CAR.CHEVROLET_VOLT_ASCM, **common), is_kaofui_car=True)


def test_lacrosse_ascm_marks_acc_dashboard_active_for_aol_only():
  cc = SimpleNamespace(enabled=False, latActive=True)

  assert get_acc_dashboard_status_active(SimpleNamespace(carFingerprint=CAR.BUICK_LACROSSE_ASCM), cc)
  assert not get_acc_dashboard_status_active(SimpleNamespace(carFingerprint=CAR.CHEVROLET_VOLT_ASCM), cc)
  assert not get_acc_dashboard_status_active(SimpleNamespace(carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023), cc)


def test_acc_dashboard_status_active_for_normal_enabled_cars():
  cc = SimpleNamespace(enabled=True, latActive=False)

  assert get_acc_dashboard_status_active(SimpleNamespace(carFingerprint=CAR.CHEVROLET_VOLT_ASCM), cc)


def test_volt_auto_hold_requires_toggle_supported_non_cc_only_volt_and_stock_safety():
  stock_safety = [SimpleNamespace(safetyParam=0x8000)]
  no_safety = [SimpleNamespace(safetyParam=0)]

  assert not supports_volt_auto_hold(
    SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT_CAMERA,
      openpilotLongitudinalControl=True,
      networkLocation=CarParams.NetworkLocation.fwdCamera,
      safetyConfigs=no_safety,
    ),
    True,
  )
  assert not supports_volt_auto_hold(
    SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT_CC,
      openpilotLongitudinalControl=True,
      networkLocation=CarParams.NetworkLocation.fwdCamera,
      safetyConfigs=no_safety,
    ),
    True,
  )
  assert supports_volt_auto_hold(
    SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT_CAMERA,
      openpilotLongitudinalControl=True,
      networkLocation=CarParams.NetworkLocation.fwdCamera,
      safetyConfigs=stock_safety,
    ),
    True,
  )
  assert not supports_volt_auto_hold(
    SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT,
      openpilotLongitudinalControl=False,
      networkLocation=CarParams.NetworkLocation.gateway,
      safetyConfigs=stock_safety,
    ),
    True,
  )
  assert not supports_volt_auto_hold(
    SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT_2019,
      openpilotLongitudinalControl=False,
      networkLocation=CarParams.NetworkLocation.fwdCamera,
      safetyConfigs=stock_safety,
    ),
    True,
  )
  assert not supports_volt_auto_hold(
    SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT_2019,
      openpilotLongitudinalControl=False,
      networkLocation=CarParams.NetworkLocation.fwdCamera,
      safetyConfigs=no_safety,
    ),
    True,
  )
  assert not supports_volt_auto_hold(
    SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT_CAMERA,
      openpilotLongitudinalControl=True,
      networkLocation=CarParams.NetworkLocation.fwdCamera,
      safetyConfigs=no_safety,
    ),
    False,
  )


def test_auto_hold_brake_estimate_uses_driver_or_op_brake_and_clamps():
  assert estimate_auto_hold_brake(0.0, 20.0) == 80
  assert estimate_auto_hold_brake(20.0, 40.0) == 110
  assert estimate_auto_hold_brake(20.0, 160.0) == 160
  assert estimate_auto_hold_brake(100.0, 400.0) == 240
  assert estimate_auto_hold_brake(7.0, 0.0, SimpleNamespace(carFingerprint=CAR.CHEVROLET_VOLT_2019)) == 100


def test_volt_one_pedal_requires_toggle_supported_volt_stock_safety_and_ev_transmission():
  stock_safety = [SimpleNamespace(safetyParam=0x8000)]
  no_safety = [SimpleNamespace(safetyParam=0)]

  assert supports_volt_one_pedal(
    SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT_CAMERA,
      openpilotLongitudinalControl=True,
      safetyConfigs=stock_safety,
      transmissionType=structs.CarParams.TransmissionType.direct,
    ),
    True,
  )
  assert not supports_volt_one_pedal(
    SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT_CAMERA,
      openpilotLongitudinalControl=True,
      safetyConfigs=no_safety,
      transmissionType=structs.CarParams.TransmissionType.direct,
    ),
    True,
  )
  assert not supports_volt_one_pedal(
    SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT_CC,
      openpilotLongitudinalControl=True,
      safetyConfigs=stock_safety,
      transmissionType=structs.CarParams.TransmissionType.direct,
    ),
    True,
  )
  assert not supports_volt_one_pedal(
    SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT_CAMERA,
      openpilotLongitudinalControl=True,
      safetyConfigs=stock_safety,
      transmissionType=structs.CarParams.TransmissionType.automatic,
    ),
    True,
  )
  assert not supports_volt_one_pedal(
    SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT_CAMERA,
      openpilotLongitudinalControl=False,
      safetyConfigs=stock_safety,
      transmissionType=structs.CarParams.TransmissionType.direct,
    ),
    True,
  )
  assert not supports_volt_one_pedal(
    SimpleNamespace(
      carFingerprint=CAR.CHEVROLET_VOLT_CAMERA,
      openpilotLongitudinalControl=True,
      safetyConfigs=stock_safety,
      transmissionType=structs.CarParams.TransmissionType.direct,
    ),
    False,
  )


def test_auto_hold_drive_gears_accept_capnp_dynamic_enum_membership():
  msg = structs.CarState.new_message()
  msg.gearShifter = structs.CarState.GearShifter.drive

  assert msg.gearShifter in AUTO_HOLD_DRIVE_GEARS


def test_auto_hold_activation_allows_direct_entry_from_stopped_brake_press():
  assert should_activate_auto_hold(
    True,
    False,
    False,
    True,
    False,
    True,
    False,
    False,
    0.01,
  )


def test_auto_hold_activation_stays_latched_after_brake_release():
  assert should_activate_auto_hold(
    True,
    False,
    True,
    False,
    False,
    True,
    False,
    False,
    0.0,
  )


def test_volt_2019_auto_hold_engaged_uses_near_stop_creep_hysteresis():
  CP = SimpleNamespace(carFingerprint=CAR.CHEVROLET_VOLT_2019)

  assert get_auto_hold_stop_threshold(CP, True) == CarControllerParams.NEAR_STOP_BRAKE_PHASE
  assert should_activate_auto_hold(
    True,
    True,
    True,
    False,
    False,
    False,
    False,
    False,
    0.05,
    get_auto_hold_stop_threshold(CP, True),
  )
  assert not should_activate_auto_hold(
    True,
    True,
    True,
    False,
    False,
    False,
    False,
    False,
    0.05,
  )


def test_auto_hold_activation_blocks_when_long_is_active_or_motion_is_above_threshold():
  assert not should_activate_auto_hold(
    True,
    True,
    False,
    True,
    False,
    True,
    True,
    False,
    0.0,
  )
  assert not should_activate_auto_hold(
    True,
    True,
    False,
    False,
    False,
    False,
    False,
    False,
    0.03,
  )


def test_auto_hold_activation_allows_standstill_even_if_speed_filter_is_slightly_above_threshold():
  assert should_activate_auto_hold(
    True,
    True,
    False,
    False,
    False,
    True,
    False,
    False,
    0.05,
  )


def test_auto_hold_activation_releases_immediately_on_gas_press():
  assert not should_activate_auto_hold(
    True,
    True,
    True,
    False,
    True,
    True,
    False,
    False,
    0.0,
  )


def test_volt_one_pedal_activation_requires_main_l_mode_and_no_driver_input():
  assert should_activate_volt_one_pedal(
    True,
    True,
    False,
    False,
    False,
    False,
    True,
    structs.CarState.GearShifter.low,
    3.0,
  )
  assert not should_activate_volt_one_pedal(
    True,
    False,
    False,
    False,
    False,
    False,
    True,
    structs.CarState.GearShifter.low,
    3.0,
  )
  assert not should_activate_volt_one_pedal(
    True,
    True,
    True,
    False,
    False,
    False,
    True,
    structs.CarState.GearShifter.low,
    3.0,
  )
  assert not should_activate_volt_one_pedal(
    True,
    True,
    False,
    True,
    False,
    False,
    True,
    structs.CarState.GearShifter.low,
    3.0,
  )
  assert not should_activate_volt_one_pedal(
    True,
    True,
    False,
    False,
    False,
    True,
    True,
    structs.CarState.GearShifter.low,
    3.0,
  )
  assert not should_activate_volt_one_pedal(
    True,
    True,
    False,
    False,
    False,
    False,
    False,
    structs.CarState.GearShifter.drive,
    3.0,
  )


def test_volt_one_pedal_target_decel_stays_active_above_low_speed_band():
  assert get_volt_one_pedal_target_decel(0.5 * CV.MPH_TO_MS) == -1.0
  assert get_volt_one_pedal_target_decel(6.0 * CV.MPH_TO_MS) == -1.1
  assert get_volt_one_pedal_target_decel(20.0 * CV.MPH_TO_MS) == -1.1


def test_volt_one_pedal_regression_ignores_noisy_wheel_direction_bits():
  assert should_activate_volt_one_pedal(
    True,
    True,
    False,
    False,
    False,
    False,
    True,
    structs.CarState.GearShifter.low,
    3.0,
  )


def test_volt_one_pedal_requires_time_in_drive_before_arming():
  assert not should_activate_volt_one_pedal(
    True,
    True,
    False,
    False,
    False,
    False,
    True,
    structs.CarState.GearShifter.low,
    2.5,
  )


def test_friction_brake_mode_keeps_near_stop_disabled_for_regular_long_braking():
  CP = SimpleNamespace(carFingerprint=CAR.CHEVROLET_VOLT_ASCM)

  assert get_friction_brake_mode(120, False, True, False, CP) == 0xa


def test_friction_brake_mode_uses_near_stop_hold_mode_for_volt_auto_hold():
  CP = SimpleNamespace(carFingerprint=CAR.CHEVROLET_VOLT_ASCM)

  assert get_friction_brake_mode(120, False, True, False, CP, allow_near_stop_mode=True) == 0xb
  assert get_friction_brake_mode(120, False, True, True, CP, allow_near_stop_mode=True) == 0xd


def test_friction_brake_mode_uses_stock_bolt_unwind_for_pedal_print_when_enabled():
  CP = SimpleNamespace(carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL)

  assert get_friction_brake_mode(0, False, True, False, CP) == 0x1
  assert get_friction_brake_mode(0, True, True, False, CP) == 0x9


def test_friction_brake_mode_keeps_bolt_pedal_braking_mode_unchanged():
  CP = SimpleNamespace(carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL)

  assert get_friction_brake_mode(120, True, False, False, CP) == 0xa
  assert get_friction_brake_mode(120, True, True, True, CP) == 0xd


def test_calc_pedal_command_small_accel_deadband_keeps_creep_target_stable():
  pos_controller = _controller()
  neg_controller = _controller()

  pos_pedal, pos_regen = pos_controller.calc_pedal_command(0.02, True, 0.3)
  neg_pedal, neg_regen = neg_controller.calc_pedal_command(-0.02, True, 0.3)

  assert not pos_regen
  assert not neg_regen
  assert pos_pedal == neg_pedal


def test_calc_pedal_command_creep_switch_does_not_snap_to_target():
  controller = _controller()
  controller.pedal_active_last = True
  controller.pedal_steady = 0.18
  controller.regen_press_counter = 20

  pedal_gas, press_regen = controller.calc_pedal_command(-1.0, True, 0.5)

  assert press_regen
  assert pedal_gas > 0.15


def test_calc_pedal_command_softens_small_positive_follow_ramp_at_road_speed():
  controller = _controller()
  controller.pedal_active_last = True
  controller.pedal_steady = 0.18

  pedal_gas, press_regen = controller.calc_pedal_command(0.2, True, 18.0)

  assert not press_regen
  assert pedal_gas - 0.18 < 0.026


def test_calc_pedal_command_keeps_strong_positive_requests_responsive():
  controller = _controller()
  controller.pedal_active_last = True
  controller.pedal_steady = 0.18

  pedal_gas, press_regen = controller.calc_pedal_command(1.4, True, 18.0)

  assert not press_regen
  assert pedal_gas - 0.18 > 0.04


def test_shape_truck_positive_accel_softens_small_highway_requests():
  shaped = shape_truck_positive_accel(0.12, 26.0, True)

  assert 0.08 < shaped < 0.095


def test_shape_truck_positive_accel_keeps_mid_follow_requests_available():
  shaped = shape_truck_positive_accel(0.45, 13.5, True)

  assert 0.43 < shaped < 0.45


def test_shape_truck_positive_accel_leaves_large_requests_alone():
  assert shape_truck_positive_accel(1.0, 26.0, True) == 1.0


def test_shape_truck_positive_accel_is_inactive_when_disabled_or_low_speed():
  assert shape_truck_positive_accel(0.12, 26.0, False) == 0.12
  assert shape_truck_positive_accel(0.12, 6.0, True) == 0.12


def test_shape_truck_positive_accel_preserves_more_follow_authority_with_lead():
  base = shape_truck_positive_accel(0.28, 26.0, True)
  relieved = shape_truck_positive_accel(0.28, 26.0, True, lead_visible=True, set_speed_error=6.0)

  assert relieved > base
  assert relieved < 0.28


def test_shape_truck_positive_accel_does_not_relax_without_speed_error():
  base = shape_truck_positive_accel(0.28, 26.0, True)
  no_error = shape_truck_positive_accel(0.28, 26.0, True, lead_visible=True, set_speed_error=0.0)

  assert no_error == base


def test_shape_truck_positive_accel_keeps_more_highway_follow_authority():
  city = shape_truck_positive_accel(0.28, 26.0, True)
  highway = shape_truck_positive_accel(0.28, 34.0, True)

  assert highway >= city


def test_smooth_truck_follow_accel_slews_small_highway_commands():
  shaped = smooth_truck_follow_accel(0.50, 0.0, 30.0, True, True, False)

  assert shaped == pytest.approx(0.06)


def test_smooth_truck_follow_accel_does_not_delay_safety_requests():
  assert smooth_truck_follow_accel(-0.40, 0.20, 30.0, True, True, False) == -0.40
  assert smooth_truck_follow_accel(0.20, -0.40, 30.0, True, True, False) == 0.20
  assert smooth_truck_follow_accel(-0.20, 0.20, 30.0, True, True, True) == -0.20
  assert smooth_truck_follow_accel(-0.20, 0.20, 20.0, True, True, False) == -0.20
  assert smooth_truck_follow_accel(-0.20, 0.20, 30.0, True, False, False) == -0.20


def test_shape_truck_pitch_accel_attenuates_highway_grade_feedforward():
  assert shape_truck_pitch_accel(-0.30, 30.0, True) == pytest.approx(-0.0825)
  assert shape_truck_pitch_accel(0.30, 30.0, True) == pytest.approx(0.0825)


def test_shape_truck_pitch_accel_is_inactive_without_truck_tuning():
  assert shape_truck_pitch_accel(-0.30, 30.0, False) == pytest.approx(-0.30)


def test_limit_grade_feedforward_does_not_stack_on_positive_planner():
  assert limit_grade_feedforward(0.40, 0.50) == 0.0


def test_limit_grade_feedforward_caps_uphill_hold():
  assert limit_grade_feedforward(0.0, 0.50) == pytest.approx(0.20)
  assert limit_grade_feedforward(-0.10, 0.50) == pytest.approx(0.20)


def test_limit_grade_feedforward_keeps_downhill_help():
  assert limit_grade_feedforward(0.40, -0.30) == pytest.approx(-0.30)
  assert limit_grade_feedforward(-0.20, -0.30) == pytest.approx(-0.30)


def test_shape_truck_friction_brake_suppresses_boundary_chatter():
  assert shape_truck_friction_brake(14, -0.3, False, False) == (0, False)


def test_shape_truck_friction_brake_uses_hysteresis_once_engaged():
  assert shape_truck_friction_brake(39, -0.3, False, False) == (0, False)
  assert shape_truck_friction_brake(40, -0.3, False, False) == (40, True)
  assert shape_truck_friction_brake(14, -0.3, False, True) == (14, True)
  assert shape_truck_friction_brake(8, -0.3, False, True) == (0, False)


def test_shape_truck_friction_brake_never_delays_meaningful_braking():
  assert shape_truck_friction_brake(5, -0.85, False, False) == (5, True)
  assert shape_truck_friction_brake(5, -0.2, True, False) == (5, True)


def test_use_interceptor_sng_launch_requires_actual_near_stop():
  CP = SimpleNamespace(vEgoStarting=0.25)

  assert use_interceptor_sng_launch(CP, _sng_cs(0.0, True, True))
  assert use_interceptor_sng_launch(CP, _sng_cs(0.2, False, True))
  assert not use_interceptor_sng_launch(CP, _sng_cs(1.2, False, True))
  assert not use_interceptor_sng_launch(CP, _sng_cs(0.0, True, False))


def test_bolt_acc_pedal_sng_launch_uses_physical_standstill_without_stock_acc_bit():
  CP = SimpleNamespace(
    vEgoStarting=0.25,
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
    enableGasInterceptorDEPRECATED=True,
  )

  assert use_interceptor_sng_launch(CP, _sng_cs(0.0, True, False))
  assert use_interceptor_sng_launch(CP, _sng_cs(0.2, False, False))
  assert not use_interceptor_sng_launch(CP, _sng_cs(1.2, False, False))


def test_bolt_acc_pedal_sng_launch_preserves_stronger_computed_pedal():
  CP = SimpleNamespace(
    carFingerprint=CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
    openpilotLongitudinalControl=True,
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
  )
  params = SimpleNamespace(SNG_INTERCEPTOR_GAS=18. / 255.)

  assert get_interceptor_sng_gas_cmd(CP, 0.2, 0.54, params, False) == pytest.approx(0.2)


def test_other_pedal_sng_launch_keeps_fixed_floor_behavior():
  CP = SimpleNamespace(
    carFingerprint=CAR.CHEVROLET_BOLT_CC_2018_2021,
    openpilotLongitudinalControl=True,
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
  )
  params = SimpleNamespace(SNG_INTERCEPTOR_GAS=18. / 255.)

  assert get_interceptor_sng_gas_cmd(CP, 0.2, 0.54, params, False) == pytest.approx(18. / 255.)


def test_use_interceptor_sng_launch_extends_for_maneuver_mode():
  CP = SimpleNamespace(vEgoStarting=0.25)

  assert use_interceptor_sng_launch(CP, _sng_cs(1.2, False, True), maneuver_mode=True)
  assert not use_interceptor_sng_launch(CP, _sng_cs(2.2, False, True), maneuver_mode=True)


def test_testing_ground_1_brake_switch_bias_is_softened_but_still_speed_scaled():
  assert get_testing_ground_1_brake_switch_bias(0.0) == 40
  assert get_testing_ground_1_brake_switch_bias(6.0) == 85
  assert get_testing_ground_1_brake_switch_bias(15.0) == 130
  assert get_testing_ground_1_brake_switch_bias(30.0) == 170


def test_lka_counter_uses_returned_loopback_counter():
  cs = SimpleNamespace(
    loopback_lka_steering_cmd_updated=True,
    loopback_lka_steering_cmd_counter=2,
    loopback_lka_steering_cmd_ts_nanos=1,
    pt_lka_steering_cmd_counter=0,
  )

  assert get_lka_steering_cmd_counter(0, cs) == 3


def test_lka_counter_keeps_advancing_without_loopback_updates():
  cs = SimpleNamespace(
    loopback_lka_steering_cmd_updated=False,
    loopback_lka_steering_cmd_counter=0,
    loopback_lka_steering_cmd_ts_nanos=1,
    pt_lka_steering_cmd_counter=0,
  )

  next_counter = 1
  sent = []
  for _ in range(6):
    idx = get_lka_steering_cmd_counter(next_counter, cs)
    sent.append(idx)
    next_counter = (idx + 1) % 4

  assert sent == [1, 2, 3, 0, 1, 2]


def test_lka_counter_only_seeds_from_pt_counter_once_without_loopback():
  cs = SimpleNamespace(
    loopback_lka_steering_cmd_updated=False,
    loopback_lka_steering_cmd_counter=0,
    loopback_lka_steering_cmd_ts_nanos=0,
    pt_lka_steering_cmd_counter=0,
  )

  next_counter = -1
  sent = []
  for _ in range(6):
    idx = get_lka_steering_cmd_counter(next_counter, cs)
    sent.append(idx)
    next_counter = (idx + 1) % 4

  assert sent == [1, 2, 3, 0, 1, 2]
