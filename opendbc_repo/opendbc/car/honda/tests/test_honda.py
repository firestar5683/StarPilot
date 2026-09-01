import re
from types import SimpleNamespace
import pytest

from opendbc.car import Bus, structs
from opendbc.car.structs import CarParams
from opendbc.car import gen_empty_fingerprint
from opendbc.car.honda.carstate import CarState
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.carcontroller import (
  ACCORD11G_BRAKE_PID_DECEL_THRESHOLD,
  CarController,
  persist_honda_learned_params_nonblocking,
  update_accord11g_low_speed_brake_pid,
  get_civic_bosch_modified_steering_pressed,
  get_civic_bosch_modified_torque_lpf_tau,
  get_honda_bosch_wind_brake_mps2,
  update_honda_bosch_live_learning,
  update_accord11g_lkas_state_change,
)
from opendbc.car.honda.hondacan import create_lkas_hud
from opendbc.car.honda.fingerprints import FW_VERSIONS
from opendbc.car.honda.values import CAR, DBC, HONDA_BOSCH, HONDA_BOSCH_TJA_CONTROL, CarControllerParams, HondaFlags, HondaSafetyFlags, \
                                     HondaStarPilotFlags

HONDA_FW_VERSION_RE = rb"[A-Z0-9]{5}-[A-Z0-9]{3}(-|,)[A-Z0-9]{4}(\x00){2}$"


def get_test_toggles() -> SimpleNamespace:
  return SimpleNamespace(always_on_lateral_lkas=False, force_torque_controller=False, nnff=False, nnff_lite=False)


class FakeBrakePid:
  def __init__(self, i=0.0, update_result=-0.25):
    self.i = i
    self.update_result = update_result
    self.updates = []
    self.reset_count = 0

  def update(self, *, error, speed):
    self.updates.append((error, speed))
    self.i = self.update_result
    return self.update_result

  def reset(self):
    self.i = 0.0
    self.reset_count += 1


class TestHondaFingerprint:
  def test_accord11g_low_speed_brake_pid_tracks_below_existing_crossover(self):
    pid = FakeBrakePid(update_result=-0.25)

    target_accel = update_accord11g_low_speed_brake_pid(
      pid, accel=-0.3, actual_accel=-0.1, v_ego=1.0,
      active_accel_threshold=-0.2, long_active=True,
    )

    assert target_accel == pytest.approx(-0.55)
    assert pid.updates == [pytest.approx((-0.2, 1.0))]
    assert pid.reset_count == 0

  def test_accord11g_low_speed_brake_pid_releases_before_allowing_gas(self):
    pid = FakeBrakePid(i=-0.4)

    target_accel = update_accord11g_low_speed_brake_pid(
      pid, accel=0.1, actual_accel=0.0, v_ego=1.0,
      active_accel_threshold=-0.2, long_active=True,
    )

    assert pid.i == pytest.approx(-0.38)
    assert target_accel == pytest.approx(-0.28)
    assert not pid.updates
    assert pid.reset_count == 0

  def test_accord11g_low_speed_brake_pid_resets_immediately_when_disengaged(self):
    pid = FakeBrakePid(i=-0.4)

    target_accel = update_accord11g_low_speed_brake_pid(
      pid, accel=0.0, actual_accel=0.0, v_ego=1.0,
      active_accel_threshold=-0.2, long_active=False,
    )

    assert target_accel == pytest.approx(0.0)
    assert pid.i == pytest.approx(0.0)
    assert pid.reset_count == 1
    assert not pid.updates

  def test_accord11g_low_speed_brake_pid_clears_nonnegative_state(self):
    pid = FakeBrakePid(i=0.0)

    target_accel = update_accord11g_low_speed_brake_pid(
      pid, accel=0.1, actual_accel=0.0, v_ego=1.0,
      active_accel_threshold=-0.2, long_active=True,
    )

    assert target_accel == pytest.approx(0.1)
    assert pid.reset_count == 1
    assert not pid.updates

  @pytest.mark.parametrize("accel, expected_active", (
    (-0.2, True),
    (0.0, True),
    (0.0005, True),
    (ACCORD11G_BRAKE_PID_DECEL_THRESHOLD, False),
    (0.01, False),
  ))
  def test_accord11g_low_speed_brake_pid_uses_all_decel_requests(self, accel, expected_active):
    pid = FakeBrakePid(update_result=-0.1)

    update_accord11g_low_speed_brake_pid(
      pid, accel=accel, actual_accel=0.0, v_ego=1.0,
      active_accel_threshold=ACCORD11G_BRAKE_PID_DECEL_THRESHOLD, long_active=True,
    )

    assert bool(pid.updates) is expected_active
    assert (pid.reset_count == 0) is expected_active

  @pytest.mark.parametrize("v_ego, expected_active", (
    (0.0, False),
    (0.001, False),
    (0.01, True),
    (1.0, True),
    (2.999, True),
    (3.0, False),
    (3.1, False),
  ))
  def test_accord11g_low_speed_brake_pid_preserves_speed_envelope(self, v_ego, expected_active):
    pid = FakeBrakePid(update_result=-0.1)

    update_accord11g_low_speed_brake_pid(
      pid, accel=-0.1, actual_accel=0.0, v_ego=v_ego,
      active_accel_threshold=ACCORD11G_BRAKE_PID_DECEL_THRESHOLD, long_active=True,
    )

    assert bool(pid.updates) is expected_active
    assert (pid.reset_count == 0) is expected_active

  def test_honda_lkas_hud_shows_lane_lines_when_lateral_only_is_active(self):
    class FakePacker:
      @staticmethod
      def make_can_msg(name, bus, values):
        return name, bus, values

    CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC_BOSCH)
    hud_control = SimpleNamespace(lanesVisible=False)

    cmds = create_lkas_hud(FakePacker(), 0, CP, hud_control, True, True, False, False, {})

    assert cmds[0][2]["SOLID_LANES"] is True

  def test_accord11g_lkas_state_change_pulse(self):
    key = None
    frames = 0
    hud_key = (False, False)

    # First observed state starts one stock-style 3-second pulse.
    key, frames, state_change = update_accord11g_lkas_state_change(
      key, frames, hud_key
    )

    assert state_change
    assert frames == 29

    # Remaining 29 10-Hz messages stay high.
    for _ in range(29):
      key, frames, state_change = update_accord11g_lkas_state_change(
        key, frames, hud_key
      )
      assert state_change

    assert frames == 0

    # Unchanged state is normally low afterward.
    key, frames, state_change = update_accord11g_lkas_state_change(
      key, frames, hud_key
    )

    assert not state_change
    assert frames == 0

    # A real HUD-state transition retriggers the pulse.
    key, frames, state_change = update_accord11g_lkas_state_change(
      key, frames, (True, False)
    )

    assert state_change
    assert frames == 29

  def test_accord11g_lkas_hud_dynamic_state_change(self):
    class FakePacker:
      @staticmethod
      def make_can_msg(name, bus, values):
        return name, bus, values

    CP = CarInterface.get_non_essential_params(CAR.HONDA_ACCORD_11G)
    hud_control = SimpleNamespace(lanesVisible=True)

    # Existing/default behavior remains high.
    cmds = create_lkas_hud(
      FakePacker(), 0, CP, hud_control,
      True, True, False, False, {}
    )
    assert cmds[0][2]["LKAS_STATE_CHANGE"] == 1

    # Accord controller may explicitly hold it low.
    cmds = create_lkas_hud(
      FakePacker(), 0, CP, hud_control,
      True, True, False, False, {},
      lkas_state_change=False,
    )
    assert cmds[0][2]["LKAS_STATE_CHANGE"] == 0

    # And pulse it high.
    cmds = create_lkas_hud(
      FakePacker(), 0, CP, hud_control,
      True, True, False, False, {},
      lkas_state_change=True,
    )
    assert cmds[0][2]["LKAS_STATE_CHANGE"] == 1

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
    assert b'39990-TBA-C120\x00\x00' in FW_VERSIONS[CAR.HONDA_CIVIC_BOSCH][(CarParams.Ecu.eps, 0x18DA30F1, None)]
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

    civic_bosch_fw = [CarParams.CarFw(ecu=CarParams.Ecu.eps, fwVersion=b'39990-TGG,A020\x00\x00', address=0x18DA30F1, subAddress=0)]
    civic_bosch_cp = CarInterface.get_params(CAR.HONDA_CIVIC_BOSCH, gen_empty_fingerprint(), civic_bosch_fw, False, False, False, toggles)
    assert not civic_bosch_cp.dashcamOnly
    assert civic_bosch_cp.flags & HondaFlags.EPS_MODIFIED

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
    assert CP.lateralTuning.which() == "torque"

  def test_honda_clarity_supports_pid_and_torque_paths(self):
    pid_toggles = SimpleNamespace(force_torque_controller=False, nnff=False, nnff_lite=False)
    car_fw = [CarParams.CarFw(ecu=CarParams.Ecu.eps, fwVersion=b'39990-TRW,A020\x00\x00', address=0x18DA30F1, subAddress=0)]

    pid_cp = CarInterface.get_params(CAR.HONDA_CLARITY, gen_empty_fingerprint(), car_fw, False, False, False, pid_toggles)

    assert not pid_cp.dashcamOnly
    assert pid_cp.flags & HondaFlags.EPS_MODIFIED
    assert pid_cp.lateralTuning.which() == "pid"
    assert list(pid_cp.lateralParams.torqueBP) == [0, 2560]
    assert list(pid_cp.lateralParams.torqueV) == [0, 2560]
    assert list(pid_cp.lateralTuning.pid.kpV) == pytest.approx([0.8])
    assert list(pid_cp.lateralTuning.pid.kiV) == pytest.approx([0.24])
    assert pid_cp.autoResumeSng
    assert pid_cp.minEnableSpeed == pytest.approx(-1.0)
    assert pid_cp.stopAccel == pytest.approx(0.0)

    torque_toggles = SimpleNamespace(force_torque_controller=True, nnff=False, nnff_lite=False)
    torque_cp = CarInterface.get_params(CAR.HONDA_CLARITY, gen_empty_fingerprint(), car_fw, False, False, False, torque_toggles)

    assert torque_cp.lateralTuning.which() == "torque"

  def test_canfd_bosch_alpha_long_is_available(self):
    toggles = get_test_toggles()

    CP = CarInterface.get_params(CAR.HONDA_PILOT_4G, gen_empty_fingerprint(), [], True, False, False, toggles)

    assert CP.alphaLongitudinalAvailable
    assert CP.openpilotLongitudinalControl
    assert CP.safetyConfigs[-1].safetyParam & HondaSafetyFlags.BOSCH_CANFD
    assert CP.safetyConfigs[-1].safetyParam & HondaSafetyFlags.BOSCH_LONG

  def test_mvl_handover_is_scoped_to_accord_11g(self):
    toggles = get_test_toggles()
    accord_cp = CarInterface.get_params(CAR.HONDA_ACCORD_11G, gen_empty_fingerprint(), [], True, False, False, toggles)
    crv_cp = CarInterface.get_params(CAR.HONDA_CRV_6G, gen_empty_fingerprint(), [], True, False, False, toggles)

    assert Bus.radar in DBC[accord_cp.carFingerprint]
    assert Bus.radar not in DBC[crv_cp.carFingerprint]
    assert accord_cp.safetyConfigs[-1].safetyParam & HondaSafetyFlags.BOSCH_CANFD_MVL
    assert not crv_cp.safetyConfigs[-1].safetyParam & HondaSafetyFlags.BOSCH_CANFD_MVL

  def test_can_valid_diagnostics_are_scoped_to_accord_11g(self):
    fpcp = SimpleNamespace(flags=0)
    accord_cp = CarInterface.get_non_essential_params(CAR.HONDA_ACCORD_11G)
    civic_cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC_BOSCH)

    accord_parsers = CarState(accord_cp, fpcp).get_can_parsers(accord_cp)
    civic_parsers = CarState(civic_cp, fpcp).get_can_parsers(civic_cp)

    assert accord_parsers
    assert all(parser._enable_can_valid_diagnostics for parser in accord_parsers.values())
    assert civic_parsers
    assert all(not parser._enable_can_valid_diagnostics for parser in civic_parsers.values())

  def test_nidec_pedal_detection_enables_interceptor_path(self):
    toggles = get_test_toggles()
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x201] = 6

    CP = CarInterface.get_params(CAR.HONDA_CIVIC, fingerprint, [], False, False, False, toggles)
    accel_limits = CarInterface.get_pid_accel_limits(CP, current_speed=5.0, cruise_speed=12.0)

    assert CP.enableGasInterceptorDEPRECATED
    assert not CP.pcmCruise
    assert accel_limits == (CarControllerParams.NIDEC_ACCEL_MIN, CarControllerParams.NIDEC_ACCEL_MAX)

  def test_honda_camera_message_flag_uses_fingerprint_detection(self):
    toggles = get_test_toggles()
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x35E] = 8

    CP = CarInterface.get_params(CAR.HONDA_ACCORD, fingerprint, [], True, False, False, toggles)
    FPCP = CarInterface.get_starpilot_params(CAR.HONDA_ACCORD, fingerprint, [], CP, toggles)

    assert FPCP.flags & HondaStarPilotFlags.HAS_CAMERA_MESSAGES

  def test_honda_live_learning_params_reload(self, monkeypatch):
    toggles = get_test_toggles()

    class FakeParams:
      def get_float(self, key, block=False, return_default=False, default=0.0):
        if key == "HondaGasFactorParams":
          return 1.25
        if key == "HondaWindFactorParams":
          return 0.85
        return default

    monkeypatch.setattr("opendbc.car.honda.carcontroller.Params", lambda: FakeParams())

    CP = CarInterface.get_params(CAR.HONDA_ACCORD, gen_empty_fingerprint(), [], True, False, False, toggles)
    controller = CarController(DBC[CP.carFingerprint], CP)

    assert controller.bosch_gas_factor == pytest.approx(1.25)
    assert controller.bosch_wind_factor == pytest.approx(0.85)

  def test_honda_param_writer_persists_snapshot_asynchronously(self):
    class FakeParams:
      def __init__(self):
        self.values = []
        self.put_nonblocking_called = False

      def put_nonblocking(self, key, value):
        self.put_nonblocking_called = True
        self.values.append((key, float(value)))

      def put_float(self, key, value):
        # This should never be called in our test
        raise AssertionError("put_float should not be called")

    params = FakeParams()

    # Test the helper function directly
    persist_honda_learned_params_nonblocking(params, 1.25, 0.875)

    # Verify exactly two calls in order with correct values
    assert len(params.values) == 2
    assert params.values[0] == ("HondaGasFactorParams", 1.25)
    assert params.values[1] == ("HondaWindFactorParams", 0.875)
    assert params.put_nonblocking_called

  def test_honda_bosch_controller_does_not_deepen_planner_braking(self, monkeypatch):
    toggles = get_test_toggles()
    CP = CarInterface.get_params(CAR.HONDA_HRV_3G, gen_empty_fingerprint(), [], True, False, False, toggles)
    controller = CarController(DBC[CP.carFingerprint], CP)

    monkeypatch.setattr("opendbc.car.honda.carcontroller.hondacan.create_steering_control", lambda *args, **kwargs: (0, []))
    monkeypatch.setattr("opendbc.car.honda.carcontroller.hondacan.create_acc_commands", lambda *args, **kwargs: [])

    CC = structs.CarControl.new_message()
    CC.enabled = True
    CC.longActive = True
    CC.latActive = False
    CC.cruiseControl.cancel = False
    CC.cruiseControl.resume = False
    CC.hudControl.speedVisible = False
    CC.hudControl.setSpeed = 0.0
    CC.hudControl.visualAlert = structs.CarControl.HUDControl.VisualAlert.none
    CC.actuators.accel = -0.3
    CC.actuators.torque = 0.0
    CC.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid

    controller.frame = 2
    CS = SimpleNamespace(
      out=SimpleNamespace(vEgo=25.0, aEgo=1.5, steeringPressed=False, gasPressed=False, brakePressed=False),
      v_cruise_factor=1.0,
    )

    new_actuators, _ = controller.update(CC.as_reader(), CS, 0, toggles)
    assert new_actuators.accel == pytest.approx(-0.3)

  def test_honda_hrv_3g_uses_matched_longitudinal_delay(self):
    toggles = get_test_toggles()

    hrv3g_cp = CarInterface.get_params(CAR.HONDA_HRV_3G, gen_empty_fingerprint(), [], True, False, False, toggles)
    accord_cp = CarInterface.get_params(CAR.HONDA_ACCORD, gen_empty_fingerprint(), [], True, False, False, toggles)

    assert hrv3g_cp.longitudinalActuatorDelay == pytest.approx(0.4)
    assert accord_cp.longitudinalActuatorDelay == pytest.approx(0.5)
