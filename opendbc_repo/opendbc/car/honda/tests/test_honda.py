import re
from types import SimpleNamespace
import pytest

from opendbc.car.structs import CarParams
from opendbc.car import gen_empty_fingerprint
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.carcontroller import (
  get_civic_bosch_modified_steering_pressed,
  get_civic_bosch_modified_torque_lpf_tau,
  get_honda_bosch_wind_brake_mps2,
  update_honda_bosch_live_learning,
)
from opendbc.car.honda.fingerprints import FW_VERSIONS
from opendbc.car.honda.values import CAR, HONDA_BOSCH, HONDA_BOSCH_TJA_CONTROL, HondaFlags

HONDA_FW_VERSION_RE = rb"[A-Z0-9]{5}-[A-Z0-9]{3}(-|,)[A-Z0-9]{4}(\x00){2}$"


class TestHondaFingerprint:
  def test_fw_version_format(self):
    # Asserts all FW versions follow an expected format
    for fw_by_ecu in FW_VERSIONS.values():
      for fws in fw_by_ecu.values():
        for fw in fws:
          assert re.match(HONDA_FW_VERSION_RE, fw) is not None, fw

  def test_tja_bosch_only(self):
    assert set(HONDA_BOSCH_TJA_CONTROL).issubset(set(HONDA_BOSCH)), "Nidec car found in TJA control list"

  def test_modified_civic_torque_lpf_tau_reacts_to_sign_change(self):
    assert get_civic_bosch_modified_torque_lpf_tau(0.7, -0.1, 25.0) == 0.10
    assert get_civic_bosch_modified_torque_lpf_tau(0.02, -0.01, 8.0) == 0.28
    assert get_civic_bosch_modified_torque_lpf_tau(0.02, 0.01, 12.0) == 0.28
    assert get_civic_bosch_modified_torque_lpf_tau(0.02, 0.01, 20.0) == 0.20
    assert get_civic_bosch_modified_torque_lpf_tau(0.02, 0.01, 25.0) == 0.16
    assert get_civic_bosch_modified_torque_lpf_tau(0.30, 0.0, 12.0) == 0.16
    assert get_civic_bosch_modified_torque_lpf_tau(0.30, 0.0, 20.0) == 0.13

  def test_modified_civic_steering_pressed_filter_rejects_short_same_direction_spikes(self):
    filter_s, pressed = get_civic_bosch_modified_steering_pressed(True, 1500.0, 0.8, 0.01, False)
    assert not pressed
    assert filter_s > 0.01

    filter_s = 0.79
    filter_s, pressed = get_civic_bosch_modified_steering_pressed(True, 1500.0, 0.8, filter_s, False)
    assert not pressed

    filter_s = 0.80
    filter_s, pressed = get_civic_bosch_modified_steering_pressed(True, 1500.0, 0.8, filter_s, False)
    assert pressed

  def test_modified_civic_steering_pressed_filter_allows_opposing_driver_torque_quickly(self):
    filter_s, pressed = get_civic_bosch_modified_steering_pressed(True, -1500.0, 0.8, 0.10, False)
    assert pressed

  def test_honda_bosch_wind_brake_curve_matches_reference_points(self):
    assert get_honda_bosch_wind_brake_mps2(0.0) == pytest.approx(0.0)
    assert get_honda_bosch_wind_brake_mps2(22.4) == pytest.approx(0.136)
    assert get_honda_bosch_wind_brake_mps2(40.2) == pytest.approx(0.441)

  def test_honda_bosch_live_learning_increases_factors_when_under_accelerating(self):
    gas_factor, wind_factor, wind_factor_before_brake = update_honda_bosch_live_learning(
      1.0,
      1.0,
      0.0,
      desired_accel=1.0,
      actual_accel=0.5,
      gas_pedal_force=1.2,
      wind_brake_mps2=0.136,
      brake_pressed=False,
      v_ego=22.4,
    )

    assert gas_factor == pytest.approx(1.012)
    assert wind_factor == pytest.approx(1.000136)
    assert wind_factor_before_brake == pytest.approx(wind_factor)

  def test_honda_bosch_live_learning_restores_wind_factor_while_braking(self):
    gas_factor, wind_factor, wind_factor_before_brake = update_honda_bosch_live_learning(
      1.4,
      1.1,
      1.3,
      desired_accel=-0.2,
      actual_accel=0.0,
      gas_pedal_force=-0.1,
      wind_brake_mps2=0.136,
      brake_pressed=True,
      v_ego=22.4,
    )

    assert gas_factor == pytest.approx(1.4)
    assert wind_factor == pytest.approx(1.3)
    assert wind_factor_before_brake == pytest.approx(1.3)

  def test_official_modified_eps_firmwares_restored(self):
    assert b'39990-TVA,A150\x00\x00' in FW_VERSIONS[CAR.HONDA_ACCORD][(CarParams.Ecu.eps, 0x18DA30F1, None)]
    assert b'39990-TBA,A030\x00\x00' in FW_VERSIONS[CAR.HONDA_CIVIC][(CarParams.Ecu.eps, 0x18DA30F1, None)]
    assert b'39990-TGG,A020\x00\x00' in FW_VERSIONS[CAR.HONDA_CIVIC_BOSCH][(CarParams.Ecu.eps, 0x18DA30F1, None)]
    assert b'39990-TLA,A040\x00\x00' in FW_VERSIONS[CAR.HONDA_CRV_5G][(CarParams.Ecu.eps, 0x18DA30F1, None)]

  def test_modified_eps_candidates_keep_support_and_restore_upstream_tunes(self):
    toggles = SimpleNamespace(force_torque_controller=False, nnff=False, nnff_lite=False)

    civic_fw = [CarParams.CarFw(ecu=CarParams.Ecu.eps, fwVersion=b'39990-TBA,A030\x00\x00', address=0x18DA30F1, subAddress=0)]
    civic_cp = CarInterface.get_params(CAR.HONDA_CIVIC, gen_empty_fingerprint(), civic_fw, False, False, False, toggles)
    assert not civic_cp.dashcamOnly
    assert civic_cp.flags & HondaFlags.EPS_MODIFIED
    assert list(civic_cp.lateralParams.torqueBP) == [0, 2560, 8000]
    assert list(civic_cp.lateralParams.torqueV) == [0, 2560, 3840]
    assert list(civic_cp.lateralTuning.pid.kpV) == pytest.approx([0.3])
    assert list(civic_cp.lateralTuning.pid.kiV) == pytest.approx([0.1])

    accord_fw = [CarParams.CarFw(ecu=CarParams.Ecu.eps, fwVersion=b'39990-TVA,A150\x00\x00', address=0x18DA30F1, subAddress=0)]
    accord_cp = CarInterface.get_params(CAR.HONDA_ACCORD, gen_empty_fingerprint(), accord_fw, False, False, False, toggles)
    assert not accord_cp.dashcamOnly
    assert accord_cp.flags & HondaFlags.EPS_MODIFIED
    assert list(accord_cp.lateralTuning.pid.kpV) == pytest.approx([0.3])
    assert list(accord_cp.lateralTuning.pid.kiV) == pytest.approx([0.09])

    crv_fw = [CarParams.CarFw(ecu=CarParams.Ecu.eps, fwVersion=b'39990-TLA,A040\x00\x00', address=0x18DA30F1, subAddress=0)]
    crv_cp = CarInterface.get_params(CAR.HONDA_CRV_5G, gen_empty_fingerprint(), crv_fw, False, False, False, toggles)
    assert not crv_cp.dashcamOnly
    assert crv_cp.flags & HondaFlags.EPS_MODIFIED
    assert list(crv_cp.lateralParams.torqueBP) == [0, 2560, 10000]
    assert list(crv_cp.lateralParams.torqueV) == [0, 2560, 3840]
    assert list(crv_cp.lateralTuning.pid.kpV) == pytest.approx([0.21])
    assert list(crv_cp.lateralTuning.pid.kiV) == pytest.approx([0.07])

  def test_modified_civic_bosch_keeps_official_support(self):
    toggles = SimpleNamespace(force_torque_controller=False, nnff=False, nnff_lite=False)
    car_fw = [CarParams.CarFw(ecu=CarParams.Ecu.eps, fwVersion=b'39990-TGG,A020\x00\x00', address=0x18DA30F1, subAddress=0)]

    CP = CarInterface.get_params(CAR.HONDA_CIVIC_BOSCH, gen_empty_fingerprint(), car_fw, False, False, False, toggles)

    assert not CP.dashcamOnly
    assert CP.flags & HondaFlags.EPS_MODIFIED
    assert list(CP.lateralParams.torqueBP) == [0, 4096]
    assert list(CP.lateralParams.torqueV) == [0, 4096]
    assert list(CP.lateralTuning.pid.kpV) == pytest.approx([0.8])
    assert list(CP.lateralTuning.pid.kiV) == pytest.approx([0.24])
