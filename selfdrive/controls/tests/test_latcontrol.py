import pytest
from parameterized import parameterized
from types import SimpleNamespace

from cereal import car, custom, log
import openpilot.selfdrive.controls.lib.latcontrol_torque as latcontrol_torque
import openpilot.selfdrive.controls.lib.latcontrol_pid as latcontrol_pid
from opendbc.car.car_helpers import interfaces
from opendbc.car.honda.values import CAR as HONDA, HondaFlags
from opendbc.car.toyota.values import CAR as TOYOTA
from opendbc.car.nissan.values import CAR as NISSAN
from opendbc.car.gm.values import CAR as GM
from opendbc.car.hyundai.values import CAR as HYUNDAI
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.latcontrol_angle import LatControlAngle
from openpilot.selfdrive.controls.lib.latcontrol_pid import (
  LatControlPID,
  get_civic_bosch_modified_pid_output_alpha,
  get_civic_bosch_modified_pid_output_scale,
)
from openpilot.selfdrive.controls.lib.latcontrol_torque import (
  get_civic_bosch_modified_a_center_taper_scale,
  LatControlTorque,
  get_civic_bosch_modified_b_ff_scale,
  get_civic_bosch_modified_b_friction_scale,
  get_bolt_2017_center_taper_scale,
  get_friction_threshold,
  get_bolt_2017_base_torque_scale,
  get_bolt_2017_steer_ratio_scale,
  get_bolt_2017_torque_scale,
  get_bolt_2022_2023_ff_scale,
  get_bolt_2022_2023_friction_scale,
  get_bolt_2022_2023_friction_threshold,
  get_bolt_2018_2021_dynamic_torque_scale,
  get_bolt_2018_2021_friction_scale,
  get_bolt_2018_2021_friction_threshold,
  get_bolt_2018_2021_torque_scale,
  get_genesis_g90_ff_scale,
  get_genesis_g90_friction_scale,
  get_genesis_g90_friction_threshold,
  get_elantra_non_scc_ff_scale,
  get_palisade_ff_scale,
  get_palisade_friction_scale,
  get_palisade_friction_threshold,
  get_prius_ff_scale,
  get_prius_friction_scale,
  get_prius_friction_threshold,
  get_ioniq_5_ff_scale,
  get_ioniq_5_friction_scale,
  get_ioniq_5_friction_threshold,
  get_ioniq_5_center_taper_scale,
  get_ioniq_ev_old_center_taper_scale,
  get_ioniq_ev_old_ff_scale,
  get_ioniq_6_center_taper_scale,
  get_ioniq_6_directional_taper_scale,
  get_ioniq_6_output_taper_scale,
  get_ioniq_6_ff_scale,
  get_ioniq_6_friction_scale,
  get_ioniq_6_friction_threshold,
  get_kia_forte_center_taper_scale,
  get_kia_forte_ff_scale,
  get_kia_ev6_center_taper_scale,
  get_kia_ev6_ff_scale,
  get_kia_ev6_friction_scale,
  get_kia_ev6_friction_threshold,
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

  @staticmethod
  def _build_torque_controller(car_name):
    CarInterface = interfaces[car_name]
    CP = CarInterface.get_non_essential_params(car_name)
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
    assert 1.0 < get_bolt_2017_steer_ratio_scale(10.0 * 0.44704) < get_bolt_2017_steer_ratio_scale(20.0 * 0.44704) < get_bolt_2017_steer_ratio_scale(30.0 * 0.44704)
    assert get_bolt_2017_steer_ratio_scale(5.0 * 0.44704) < 1.01
    assert get_bolt_2017_steer_ratio_scale(35.0 * 0.44704) > 1.04
    assert get_bolt_2017_center_taper_scale(0.0, 30.0 * 0.44704) < get_bolt_2017_center_taper_scale(0.10, 30.0 * 0.44704) < get_bolt_2017_center_taper_scale(0.20, 30.0 * 0.44704) <= 1.0
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
    base = get_friction_threshold(6.0)
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

  def test_bolt_2022_2023_friction_threshold_curve(self):
    base = get_friction_threshold(6.0)
    left_turn_in = get_bolt_2022_2023_friction_threshold(6.0, 0.7, 0.8)
    right_turn_in = get_bolt_2022_2023_friction_threshold(6.0, -0.7, -0.8)
    left_unwind = get_bolt_2022_2023_friction_threshold(6.0, 0.7, -0.8)
    right_unwind = get_bolt_2022_2023_friction_threshold(6.0, -0.7, 0.8)
    assert left_turn_in <= right_turn_in < base < right_unwind <= left_unwind

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
    base = get_friction_threshold(6.0)
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
    assert base < left_turn_in < right_turn_in
    assert left_unwind < base and right_unwind < left_unwind

  def test_volt_standard_center_taper_curve(self):
    assert get_volt_standard_center_taper_scale(0.0, 10.0) > get_volt_standard_center_taper_scale(0.0, 25.0)
    assert get_volt_standard_center_taper_scale(0.0, 25.0) < get_volt_standard_center_taper_scale(0.10, 25.0) < get_volt_standard_center_taper_scale(0.20, 25.0) <= 1.0
    assert get_volt_standard_center_taper_scale(0.0, 25.0) > 0.85

  def test_sonata_hybrid_ff_scale_curve(self):
    assert get_sonata_hybrid_ff_scale(0.0, 0.0, 20.0) == 1.0
    assert get_sonata_hybrid_ff_scale(0.6, 0.0, 20.0) > get_sonata_hybrid_ff_scale(-0.6, 0.0, 20.0)
    assert get_sonata_hybrid_ff_scale(0.30, 0.0, 20.0) < 1.0
    assert get_sonata_hybrid_ff_scale(0.30, 0.0, 20.0) < get_sonata_hybrid_ff_scale(0.10, 0.0, 20.0)
    assert get_sonata_hybrid_ff_scale(0.4, 0.7, 6.0) > get_sonata_hybrid_ff_scale(0.4, 0.0, 6.0)
    assert get_sonata_hybrid_ff_scale(-0.4, 0.7, 6.0) < get_sonata_hybrid_ff_scale(-0.4, 0.0, 6.0)

  def test_sonata_hybrid_center_taper_curve(self):
    assert get_sonata_hybrid_center_taper_scale(0.0, 30.0) < get_sonata_hybrid_center_taper_scale(0.0, 15.0)
    assert get_sonata_hybrid_center_taper_scale(0.0, 3.0) < get_sonata_hybrid_center_taper_scale(0.0, 10.0)
    assert get_sonata_hybrid_center_taper_scale(0.0, 30.0) < get_sonata_hybrid_center_taper_scale(0.20, 30.0) <= 1.0

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

  def test_genesis_g90_ff_scale_curve(self):
    assert get_genesis_g90_ff_scale(0.0, 0.0, 20.0) == 1.0
    assert get_genesis_g90_ff_scale(0.5, 0.0, 20.0) > get_genesis_g90_ff_scale(-0.5, 0.0, 20.0)
    assert get_genesis_g90_ff_scale(0.6, 0.7, 8.0) > get_genesis_g90_ff_scale(0.6, 0.0, 8.0) > get_genesis_g90_ff_scale(0.6, -0.7, 8.0)
    assert get_genesis_g90_ff_scale(-0.6, -0.7, 8.0) > get_genesis_g90_ff_scale(-0.6, 0.0, 8.0) > get_genesis_g90_ff_scale(-0.6, 0.7, 8.0)
    assert get_genesis_g90_ff_scale(2.0, 0.0, 20.0) < get_genesis_g90_ff_scale(0.8, 0.0, 20.0)

  def test_genesis_g90_friction_threshold_curve(self):
    base = get_friction_threshold(6.0)
    left_turn_in = get_genesis_g90_friction_threshold(6.0, 0.7, 0.8)
    right_turn_in = get_genesis_g90_friction_threshold(6.0, -0.7, -0.8)
    left_unwind = get_genesis_g90_friction_threshold(6.0, 0.7, -0.8)
    right_unwind = get_genesis_g90_friction_threshold(6.0, -0.7, 0.8)
    assert left_turn_in < base
    assert right_turn_in < base
    assert left_turn_in < right_turn_in
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
    base = get_friction_threshold(6.0)
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
    base_threshold = get_friction_threshold(12.0)
    left_turn_in_threshold = get_prius_friction_threshold(6.0, 0.7, 0.8)
    right_turn_in_threshold = get_prius_friction_threshold(6.0, -0.7, -0.8)
    left_unwind_threshold = get_prius_friction_threshold(6.0, 0.7, -0.8)
    right_unwind_threshold = get_prius_friction_threshold(6.0, -0.7, 0.8)
    assert left_turn_in_threshold < base_threshold
    assert right_turn_in_threshold < left_turn_in_threshold
    assert left_unwind_threshold > base_threshold
    assert right_unwind_threshold >= left_unwind_threshold

    base_scale = get_prius_friction_scale(25.0, 0.7, 0.8)
    left_turn_in_scale = get_prius_friction_scale(6.0, 0.7, 0.8)
    right_turn_in_scale = get_prius_friction_scale(6.0, -0.7, -0.8)
    left_unwind_scale = get_prius_friction_scale(6.0, 0.7, -0.8)
    right_unwind_scale = get_prius_friction_scale(6.0, -0.7, 0.8)
    assert right_turn_in_scale > left_turn_in_scale > base_scale
    assert base_scale > left_unwind_scale > right_unwind_scale

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
    base = get_friction_threshold(12.0)
    turn_in_left_threshold = get_ioniq_5_friction_threshold(12.0, 0.7, 0.8)
    turn_in_right_threshold = get_ioniq_5_friction_threshold(12.0, -0.7, -0.8)
    unwind_left_threshold = get_ioniq_5_friction_threshold(12.0, 0.7, -0.8)
    unwind_right_threshold = get_ioniq_5_friction_threshold(12.0, -0.7, 0.8)
    assert turn_in_left_threshold < base
    assert turn_in_left_threshold < turn_in_right_threshold < base
    assert unwind_left_threshold > base
    assert unwind_right_threshold > unwind_left_threshold

    turn_in_left_scale = get_ioniq_5_friction_scale(12.0, 0.7, 0.8)
    turn_in_right_scale = get_ioniq_5_friction_scale(12.0, -0.7, -0.8)
    unwind_left_scale = get_ioniq_5_friction_scale(12.0, 0.7, -0.8)
    unwind_right_scale = get_ioniq_5_friction_scale(12.0, -0.7, 0.8)
    assert turn_in_left_scale > turn_in_right_scale > 1.0
    assert unwind_left_scale < 1.0
    assert unwind_right_scale <= unwind_left_scale

  def test_ioniq_5_center_taper_curve(self):
    assert get_ioniq_5_center_taper_scale(0.0, 25.0) < get_ioniq_5_center_taper_scale(0.0, 10.0)
    assert get_ioniq_5_center_taper_scale(0.0, 25.0) < get_ioniq_5_center_taper_scale(0.20, 25.0) <= 1.0

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
    assert get_ioniq_6_directional_taper_scale(-1.2, 0.7, 8.0) == pytest.approx(get_ioniq_6_directional_taper_scale(-1.2, 0.7, 25.0), abs=0.02)
    assert get_ioniq_6_directional_taper_scale(-0.18, -0.40, 3.0) > get_ioniq_6_directional_taper_scale(-0.18, -0.40, 9.0)
    assert get_ioniq_6_directional_taper_scale(-0.18, -0.40, 9.0) > get_ioniq_6_directional_taper_scale(-0.18, -0.40, 20.0)
    assert get_ioniq_6_directional_taper_scale(-0.50, -0.40, 3.0) > get_ioniq_6_directional_taper_scale(-0.50, -0.40, 6.0)
    assert get_ioniq_6_directional_taper_scale(-0.50, -0.40, 6.0) > get_ioniq_6_directional_taper_scale(-0.50, -0.40, 9.0)
    assert get_ioniq_6_directional_taper_scale(-0.50, -0.40, 9.0) > get_ioniq_6_directional_taper_scale(-0.50, -0.40, 20.0)
    assert get_ioniq_6_directional_taper_scale(-0.70, -0.70, 6.0) > get_ioniq_6_directional_taper_scale(-0.70, -0.70, 12.0)
    assert get_ioniq_6_directional_taper_scale(-0.70, -0.70, 12.0) > get_ioniq_6_directional_taper_scale(-0.70, -0.70, 20.0)
    assert get_ioniq_6_directional_taper_scale(0.30, 0.60, 5.0) > get_ioniq_6_directional_taper_scale(0.30, 0.60, 12.0)

  def test_ioniq_6_output_taper_curve(self):
    assert get_ioniq_6_output_taper_scale(0.0, 0.0, 25.0) < get_ioniq_6_output_taper_scale(0.0, 0.0, 8.0) <= 1.0
    assert get_ioniq_6_output_taper_scale(-0.5, 0.0, 25.0) < get_ioniq_6_output_taper_scale(0.5, 0.0, 25.0) < 1.0
    assert get_ioniq_6_output_taper_scale(-0.5, 0.7, 25.0) <= get_ioniq_6_output_taper_scale(-0.5, 0.0, 25.0)
    assert get_ioniq_6_output_taper_scale(-1.2, 0.0, 25.0) < get_ioniq_6_output_taper_scale(1.2, 0.0, 25.0) < 1.0
    assert get_ioniq_6_output_taper_scale(-1.2, 0.7, 25.0) <= get_ioniq_6_output_taper_scale(-1.2, 0.0, 25.0)

  def test_ioniq_6_friction_threshold_curve(self):
    base = max(get_friction_threshold(6.0), 0.36)
    left_turn_in = get_ioniq_6_friction_threshold(6.0, 0.5, 0.8)
    right_turn_in = get_ioniq_6_friction_threshold(6.0, -0.5, -0.8)
    left_unwind = get_ioniq_6_friction_threshold(6.0, 0.5, -0.8)
    right_unwind = get_ioniq_6_friction_threshold(6.0, -0.5, 0.8)
    assert max(left_turn_in, right_turn_in) < base
    assert left_unwind >= base
    assert right_unwind >= base
    assert get_ioniq_6_friction_threshold(25.0, 0.0, 0.0) >= 0.36

  def test_ioniq_6_friction_scale_curve(self):
    base = get_ioniq_6_friction_scale(25.0, 0.5, 0.8)
    left_turn_in = get_ioniq_6_friction_scale(6.0, 0.5, 0.8)
    right_turn_in = get_ioniq_6_friction_scale(6.0, -0.5, -0.8)
    left_unwind = get_ioniq_6_friction_scale(6.0, 0.5, -0.8)
    right_unwind = get_ioniq_6_friction_scale(6.0, -0.5, 0.8)
    assert right_turn_in >= left_turn_in > base
    assert base > left_unwind >= right_unwind

  def test_ioniq_6_center_taper_curve(self):
    assert get_ioniq_6_center_taper_scale(0.0, 10.0) > get_ioniq_6_center_taper_scale(0.0, 30.0)
    assert get_ioniq_6_center_taper_scale(0.0, 30.0) < get_ioniq_6_center_taper_scale(0.2, 30.0)
    assert get_ioniq_6_center_taper_scale(0.0, 12.0) < get_ioniq_6_center_taper_scale(0.25, 12.0)
    assert get_ioniq_6_center_taper_scale(0.0, 27.0) < get_ioniq_6_center_taper_scale(0.0, 22.0)
    assert get_ioniq_6_center_taper_scale(0.24, 27.0) > 0.95
    assert get_ioniq_6_center_taper_scale(0.24, 22.0) - get_ioniq_6_center_taper_scale(0.24, 27.0) < 1.0e-2
    assert abs(get_ioniq_6_center_taper_scale(0.2, 30.0) - 1.0) < 7.2e-2

  def test_kia_ev6_ff_scale_curve(self):
    assert get_kia_ev6_ff_scale(0.0, 0.0, 20.0) == 1.0
    assert get_kia_ev6_ff_scale(-0.3, 0.0, 20.0) > get_kia_ev6_ff_scale(0.3, 0.0, 20.0)
    assert get_kia_ev6_ff_scale(-0.4, -0.7, 8.0) > get_kia_ev6_ff_scale(-0.4, 0.0, 8.0) > get_kia_ev6_ff_scale(-0.4, 0.7, 8.0)
    assert get_kia_ev6_ff_scale(0.4, 0.7, 8.0) > get_kia_ev6_ff_scale(0.4, 0.0, 8.0) > get_kia_ev6_ff_scale(0.4, -0.7, 8.0)
    assert get_kia_ev6_ff_scale(1.2, 0.0, 20.0) < get_kia_ev6_ff_scale(0.4, 0.0, 20.0)

  def test_kia_ev6_friction_threshold_curve(self):
    base = get_friction_threshold(6.0)
    left_turn_in = get_kia_ev6_friction_threshold(6.0, 0.5, 0.8)
    right_turn_in = get_kia_ev6_friction_threshold(6.0, -0.5, -0.8)
    left_unwind = get_kia_ev6_friction_threshold(6.0, 0.5, -0.8)
    right_unwind = get_kia_ev6_friction_threshold(6.0, -0.5, 0.8)
    assert right_turn_in < left_turn_in < base < right_unwind <= left_unwind

  def test_kia_ev6_friction_scale_curve(self):
    base = get_kia_ev6_friction_scale(25.0, 0.5, 0.8)
    left_turn_in = get_kia_ev6_friction_scale(6.0, 0.5, 0.8)
    right_turn_in = get_kia_ev6_friction_scale(6.0, -0.5, -0.8)
    left_unwind = get_kia_ev6_friction_scale(6.0, 0.5, -0.8)
    right_unwind = get_kia_ev6_friction_scale(6.0, -0.5, 0.8)
    assert right_turn_in > left_turn_in > base
    assert base > left_unwind >= right_unwind

  def test_volt_plexy_friction_threshold_curve(self):
    base = get_friction_threshold(6.0)
    left_turn_in = get_volt_plexy_friction_threshold(6.0, 0.7, 0.8)
    right_turn_in = get_volt_plexy_friction_threshold(6.0, -0.7, -0.8)
    left_unwind = get_volt_plexy_friction_threshold(6.0, 0.7, -0.8)
    right_unwind = get_volt_plexy_friction_threshold(6.0, -0.7, 0.8)
    assert left_turn_in < right_turn_in < base < left_unwind < right_unwind

  def test_volt_plexy_friction_scale_curve(self):
    base = get_volt_plexy_friction_scale(25.0, 0.7, 0.8)
    left_turn_in = get_volt_plexy_friction_scale(6.0, 0.7, 0.8)
    right_turn_in = get_volt_plexy_friction_scale(6.0, -0.7, -0.8)
    left_unwind = get_volt_plexy_friction_scale(6.0, 0.7, -0.8)
    right_unwind = get_volt_plexy_friction_scale(6.0, -0.7, 0.8)
    assert left_turn_in > right_turn_in > base
    assert base > left_unwind > right_unwind

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

  def test_sonata_default_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_SONATA)
    CarInterface = interfaces[HYUNDAI.HYUNDAI_SONATA]
    CP = CarInterface.get_non_essential_params(HYUNDAI.HYUNDAI_SONATA)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert controller.torque_params.latAccelFactor == pytest.approx(CP.lateralTuning.torque.latAccelFactor)

  def test_ioniq_5_default_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_IONIQ_5)
    CarInterface = interfaces[HYUNDAI.HYUNDAI_IONIQ_5]
    CP = CarInterface.get_non_essential_params(HYUNDAI.HYUNDAI_IONIQ_5)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert controller.torque_params.latAccelFactor == pytest.approx(CP.lateralTuning.torque.latAccelFactor * 1.22)

  def test_ioniq_6_default_update_path(self):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_IONIQ_6)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active
    assert controller.torque_params.latAccelFactor == pytest.approx(3.0 * 1.22)

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
    assert controller.torque_params.latAccelFactor == pytest.approx(CP.lateralTuning.torque.latAccelFactor * 1.10)

  def test_ioniq_6_update_path_does_not_post_taper_output(self, monkeypatch):
    base_controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_IONIQ_6)
    base_output, _, _ = base_controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    monkeypatch.setattr(latcontrol_torque, "get_ioniq_6_output_taper_scale", lambda *_args: 0.01)
    tapered_controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.HYUNDAI_IONIQ_6)
    tapered_output, _, _ = tapered_controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert tapered_output == pytest.approx(base_output)

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
    base_steady_left = get_civic_bosch_modified_b_ff_scale(0.5, 0.0, 12.0)
    base_steady_right = get_civic_bosch_modified_b_ff_scale(-0.5, 0.0, 12.0)
    base_turn_in_right = get_civic_bosch_modified_b_ff_scale(-0.5, -0.8, 12.0)
    base_unwind_right = get_civic_bosch_modified_b_ff_scale(-0.5, 0.8, 12.0)
    base_turn_in_right_friction = get_civic_bosch_modified_b_friction_scale(12.0, -0.5, -0.8)
    base_unwind_right_friction = get_civic_bosch_modified_b_friction_scale(12.0, -0.5, 0.8)

    monkeypatch.setattr(latcontrol_torque, "civic_bosch_modified_lateral_testing_ground_active", lambda: True)

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
    base_unwind_right_friction = get_civic_bosch_modified_b_friction_scale(12.0, -0.5, 0.8)

    monkeypatch.setattr(latcontrol_torque, "civic_bosch_modified_a_lateral_testing_ground_active", lambda: True)

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

  def test_kia_ev6_testing_ground_update_path(self, monkeypatch):
    controller, VM, CS, params, starpilot_toggles = self._build_torque_controller(HYUNDAI.KIA_EV6)
    monkeypatch.setattr(latcontrol_torque, "kia_ev6_lateral_testing_ground_active", lambda: True)

    _, _, lac_log = controller.update(True, CS, VM, params, False, 0.0025, False, 0.2, None, None, starpilot_toggles)

    assert lac_log.active

  def test_kia_ev6_ff_scale_curve(self):
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

  def test_kia_ev6_center_taper_curve(self):
    assert get_kia_ev6_center_taper_scale(0.0, 25.0) < get_kia_ev6_center_taper_scale(0.0, 10.0)
    assert get_kia_ev6_center_taper_scale(0.0, 25.0) < get_kia_ev6_center_taper_scale(0.20, 25.0) <= 1.0

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
