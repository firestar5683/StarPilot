import math
import numpy as np
from collections import deque

from cereal import log
from opendbc.car.honda.values import CAR as HONDA_CAR, HondaFlags
from opendbc.car.hyundai.values import HyundaiFlags
from opendbc.car.lateral import get_friction
from openpilot.common.constants import ACCELERATION_DUE_TO_GRAVITY
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.pid import PIDController
from openpilot.selfdrive.controls.lib.drive_helpers import MIN_SPEED
from openpilot.selfdrive.controls.lib.latcontrol import LatControl
from openpilot.selfdrive.controls.lib.latcontrol_vehicle_tunes import *  # noqa: F403

# At higher speeds (25+mph) we can assume:
# Lateral acceleration achieved by a specific car correlates to
# torque applied to the steering rack. It does not correlate to
# wheel slip, or to speed.

# This controller applies torque to achieve desired lateral
# accelerations. To compensate for the low speed effects the
# proportional gain is increased at low speeds by the PID controller.
# Additionally, there is friction in the steering wheel that needs
# to be overcome to move it at all, this is compensated for too.

KP = 0.6
KI = 0.35

INTERP_SPEEDS = [1, 1.5, 2.0, 3.0, 5, 7.5, 10, 15, 30]
KP_INTERP = [250, 120, 65, 30, 11.5, 5.5, 3.5, 2.0, KP]

LOW_SPEED_X = [0, 10, 20, 30]
LOW_SPEED_Y = [12, 10.5, 8, 5]
MAX_LAT_JERK_UP = 2.5            # m/s^3

LP_FILTER_CUTOFF_HZ = 1.2
JERK_LOOKAHEAD_SECONDS = 0.19
JERK_GAIN = 0.22
LAT_ACCEL_REQUEST_BUFFER_SECONDS = 1.0
VERSION = 2
DEBUG_TORQUE_TUNE = False
FF_SCALE_BLEND_LAT_ACCEL = 0.05
DEADZONE_BOOST_LAT_ACCEL = 0.15
UNWIND_D_DES_THRESHOLD = -1.0
UNWIND_LAT_ACCEL_NEAR_ZERO = 0.3
MIN_LATERAL_CONTROL_SPEED = 0.3

# Roll compensation and latAccelOffset are lateral-accel-domain corrections; below
# walking pace the desired lateral accel is ~0 so an unfaded road-crown term dominates
# the whole feedforward and actively unwinds a held wheel at pull-away (newturn rlog
# 18.3-18.7s: ff pinned at -0.5 against a correct right-turn hold at 0.3 m/s).
FF_ROLL_OFFSET_FADE_BP = [0.5, 2.5]  # m/s
FF_ROLL_OFFSET_FADE_V = [0.0, 1.0]

class LatControlTorque(LatControl):
  def __init__(self, CP, CI, dt):
    super().__init__(CP, CI, dt)
    self.torque_params = CP.lateralTuning.torque.as_builder()
    self.torque_from_lateral_accel = CI.torque_from_lateral_accel()
    self.lateral_accel_from_torque = CI.lateral_accel_from_torque()
    self.pid = PIDController([INTERP_SPEEDS, KP_INTERP], KI, rate=1/self.dt)
    self.update_limits()
    self.steering_angle_deadzone_deg = self.torque_params.steeringAngleDeadzoneDeg
    self.request_buffer_len = int(LAT_ACCEL_REQUEST_BUFFER_SECONDS / self.dt)
    # Stores requested CURVATURE, scaled by the current v^2 on read. Storing lateral
    # accel directly makes the delayed request lag the measurement whenever speed is
    # changing (both scale with v^2 but the buffered value used the old speed), which
    # at creep-speed gains reads as a phantom unwind error during every pull-away.
    self.curvature_request_buffer = deque([0.] * self.request_buffer_len, maxlen=self.request_buffer_len)
    self.lookahead_frames = int(JERK_LOOKAHEAD_SECONDS / self.dt)
    self.jerk_filter = FirstOrderFilter(0.0, 1 / (2 * np.pi * LP_FILTER_CUTOFF_HZ), self.dt)
    self.ioniq_6_directional_taper_filter = FirstOrderFilter(1.0, IONIQ_6_DIRECTIONAL_TAPER_FILTER_RC, self.dt)
    self.previous_measurement = 0.0
    self.measurement_rate_filter = FirstOrderFilter(0.0, 1 / (2 * np.pi * (MAX_LAT_JERK_UP - 0.5)), self.dt)
    self.low_speed_reset_threshold = max(CP.minSteerSpeed, MIN_LATERAL_CONTROL_SPEED)
    self.steer_release_i_decay = 0.8
    self.prev_steering_pressed = False
    self.debug_counter = 0
    self.prev_desired_lateral_accel = 0.0

    self.is_bolt = CP.carFingerprint in BOLT_CARS
    self.is_bolt_2022_2023 = CP.carFingerprint in BOLT_2022_2023_CARS
    self.is_bolt_2018_2021 = CP.carFingerprint in BOLT_2018_2021_CARS
    self.is_bolt_2017 = CP.carFingerprint in BOLT_2017_CARS
    self.is_volt_standard = CP.carFingerprint in VOLT_STANDARD_CARS
    self.is_genesis_g90 = CP.carFingerprint in GENESIS_G90_CARS
    self.is_palisade = CP.carFingerprint in PALISADE_CARS
    self.is_prius = CP.carFingerprint in PRIUS_CARS
    self.is_rav4_prime = CP.carFingerprint in RAV4_PRIME_CARS
    self.is_sienna_4th_gen = CP.carFingerprint in SIENNA_4TH_GEN_CARS
    self.is_lexus_is = CP.carFingerprint in LEXUS_IS_CARS
    self.is_ioniq_5 = CP.carFingerprint in IONIQ_5_CARS
    self.is_ioniq_ev_old = CP.carFingerprint in IONIQ_EV_OLD_CARS
    self.is_ioniq_6 = CP.carFingerprint in IONIQ_6_CARS
    self.is_sonata = CP.carFingerprint in SONATA_CARS
    self.is_sonata_hybrid = CP.carFingerprint in SONATA_HYBRID_CARS
    self.is_elantra_non_scc = CP.carFingerprint in ELANTRA_NON_SCC_CARS
    self.is_kia_xceed = CP.carFingerprint in KIA_XCEED_CARS
    self.is_kia_niro_phev_2022 = CP.carFingerprint in KIA_NIRO_PHEV_2022_CARS
    self.is_kia_stinger_2022 = CP.carFingerprint in KIA_STINGER_2022_CARS
    self.is_kia_forte = CP.carFingerprint in KIA_FORTE_CARS
    self.is_kona_non_scc = CP.carFingerprint in KONA_NON_SCC_CARS
    self.is_kia_ev6 = CP.carFingerprint in KIA_EV6_CARS
    self.is_kia_carnival = CP.carFingerprint in KIA_CARNIVAL_CARS
    self.is_tucson_4th_gen = CP.carFingerprint in TUCSON_4TH_GEN_CARS
    self.is_civic_bosch_modified = CP.carFingerprint == HONDA_CAR.HONDA_CIVIC_BOSCH and bool(CP.flags & HondaFlags.EPS_MODIFIED)
    self.is_silverado = CP.carFingerprint in SILVERADO_CARS
    self.is_ram_1500 = CP.carFingerprint in RAM_1500_CARS
    self.is_gm = CP.brand == "gm"
    self.is_hkg_canfd_torque = CP.brand == "hyundai" and bool(CP.flags & HyundaiFlags.CANFD)
    self.flm_surface_profile_key = get_flm_surface_profile_key(CP.carFingerprint, torque_control=True)
    if self.is_ioniq_6:
      self.low_speed_reset_threshold = min(self.low_speed_reset_threshold, IONIQ_6_LOW_SPEED_PID_RESET_SPEED)
    self.use_bolt_ff_scaling = self.is_bolt_2022_2023 or self.is_bolt_2018_2021 or self.is_bolt_2017
    self.use_bolt_ki_multiplier = self.use_bolt_ff_scaling
    self.torque_ff_scale_pos = 1.0
    self.torque_ff_scale_neg = 1.0
    self.torque_deadzone_boost = float(getattr(self.torque_params, "kfDEPRECATED", 0.0))
    self.torque_ki_mult = 1.0
    if self.is_palisade:
      self.torque_params.latAccelFactor *= PALISADE_BASE_LAT_ACCEL_FACTOR_MULT
    if self.is_ioniq_5:
      self.torque_params.latAccelFactor *= IONIQ_5_BASE_LAT_ACCEL_FACTOR_MULT
    if self.is_ioniq_ev_old:
      self.torque_params.latAccelFactor *= IONIQ_EV_OLD_BASE_LAT_ACCEL_FACTOR_MULT
    if self.is_ioniq_6:
      self.torque_params.latAccelFactor *= IONIQ_6_BASE_LAT_ACCEL_FACTOR_MULT
    if self.is_sonata_hybrid:
      self.torque_params.latAccelFactor *= SONATA_HYBRID_BASE_LAT_ACCEL_FACTOR_MULT
    if self.is_kia_forte:
      self.torque_params.latAccelFactor *= KIA_FORTE_BASE_LAT_ACCEL_FACTOR_MULT
    if self.is_ram_1500:
      self.torque_params.latAccelFactor *= RAM_1500_BASE_LAT_ACCEL_FACTOR_MULT
      self.update_limits()
    if self.is_civic_bosch_modified:
      self.torque_params.latAccelFactor *= CIVIC_BOSCH_MODIFIED_B_LAT_ACCEL_FACTOR_MULT
      if civic_bosch_modified_a_lateral_testing_ground_active():
        self.torque_params.latAccelFactor *= CIVIC_BOSCH_MODIFIED_A_VARIANT_LAT_ACCEL_FACTOR_MULT
      if civic_bosch_modified_lateral_testing_ground_active():
        self.torque_params.latAccelFactor *= CIVIC_BOSCH_MODIFIED_B_VARIANT_LAT_ACCEL_FACTOR_MULT
    if self.is_bolt:
      kp_scale = getattr(self.torque_params, "kp", getattr(self.torque_params, "kpDEPRECATED", 1.0))
      ki_scale = getattr(self.torque_params, "ki", getattr(self.torque_params, "kiDEPRECATED", 1.0))
      kd_scale = getattr(self.torque_params, "kd", getattr(self.torque_params, "kdDEPRECATED", 1.0))
      self.torque_ff_scale_pos = float(kp_scale)
      self.torque_ff_scale_neg = float(ki_scale)
      self.torque_ki_mult = float(kd_scale)
      if self.use_bolt_ki_multiplier and self.torque_ki_mult > 0.0 and self.torque_ki_mult != 1.0:
        self.pid._k_i = [self.pid._k_i[0], [k * self.torque_ki_mult for k in self.pid._k_i[1]]]

  def update_live_torque_params(self, latAccelFactor, latAccelOffset, friction):
    if self.is_palisade:
      latAccelFactor *= PALISADE_BASE_LAT_ACCEL_FACTOR_MULT
    if self.is_ioniq_5:
      latAccelFactor *= IONIQ_5_BASE_LAT_ACCEL_FACTOR_MULT
    if self.is_ioniq_ev_old:
      latAccelFactor *= IONIQ_EV_OLD_BASE_LAT_ACCEL_FACTOR_MULT
    if self.is_ioniq_6:
      latAccelFactor *= IONIQ_6_BASE_LAT_ACCEL_FACTOR_MULT
    if self.is_sonata_hybrid:
      latAccelFactor *= SONATA_HYBRID_BASE_LAT_ACCEL_FACTOR_MULT
    if self.is_kia_forte:
      latAccelFactor *= KIA_FORTE_BASE_LAT_ACCEL_FACTOR_MULT
    if self.is_ram_1500:
      latAccelFactor *= RAM_1500_BASE_LAT_ACCEL_FACTOR_MULT
    if self.is_civic_bosch_modified:
      latAccelFactor *= CIVIC_BOSCH_MODIFIED_B_LAT_ACCEL_FACTOR_MULT
      if civic_bosch_modified_a_lateral_testing_ground_active():
        latAccelFactor *= CIVIC_BOSCH_MODIFIED_A_VARIANT_LAT_ACCEL_FACTOR_MULT
      if civic_bosch_modified_lateral_testing_ground_active():
        latAccelFactor *= CIVIC_BOSCH_MODIFIED_B_VARIANT_LAT_ACCEL_FACTOR_MULT
    self.torque_params.latAccelFactor = latAccelFactor
    self.torque_params.latAccelOffset = latAccelOffset
    self.torque_params.friction = friction
    self.update_limits()

  def update_limits(self):
    self.pid.set_limits(self.lateral_accel_from_torque(self.steer_max, self.torque_params),
                        self.lateral_accel_from_torque(-self.steer_max, self.torque_params))

  def update(self, active, CS, VM, params, steer_limited_by_safety, desired_curvature, curvature_limited, lat_delay, calibrated_pose, model_data, starpilot_toggles):
    pid_log = log.ControlsState.LateralTorqueState.new_message()
    pid_log.version = VERSION
    flm_profile_active = bool(getattr(starpilot_toggles, "flm_trial_applied", False) and
                              getattr(starpilot_toggles, "flm_active_profile_id", ""))
    set_flm_runtime_overrides(getattr(starpilot_toggles, "flm_active_overrides", None) if flm_profile_active else None)
    flm_surface_active = flm_profile_active and flm_runtime_overrides_active()
    measured_curvature = -VM.calc_curvature(math.radians(CS.steeringAngleDeg - params.angleOffsetDeg), CS.vEgo, params.roll)
    measurement = measured_curvature * CS.vEgo ** 2
    future_desired_lateral_accel = desired_curvature * CS.vEgo ** 2
    if not active:
      output_torque = 0.0
      pid_log.active = False
      self.pid.reset()
      # Keep the request buffer and rate state primed with the live command (which tracks
      # the measured curvature while inactive) instead of zeroing them. Re-engaging with a
      # wound wheel against a zeroed buffer puts the setpoint ~lat_delay behind the
      # measurement, and the low-speed gains turn that lag into a hard unwind shove
      # (turnn rlog 38.75s: +0.8 torque against a held right turn on pull-away).
      self.curvature_request_buffer.append(desired_curvature)
      self.previous_measurement = measurement
      self.measurement_rate_filter.x = 0.0
      self.jerk_filter.x = 0.0
      self.prev_desired_lateral_accel = future_desired_lateral_accel
      self.ioniq_6_directional_taper_filter.x = 1.0
    else:
      if self.prev_steering_pressed and not CS.steeringPressed:
        self.pid.i *= self.steer_release_i_decay

      roll_offset_fade = np.interp(CS.vEgo, FF_ROLL_OFFSET_FADE_BP, FF_ROLL_OFFSET_FADE_V)
      roll_compensation = params.roll * ACCELERATION_DUE_TO_GRAVITY * roll_offset_fade
      flm_center_deadband_deg = (
        get_flm_full_surface_center_deadband_deg(self.flm_surface_profile_key, CS.vEgo) if flm_surface_active else 0.0
      )
      effective_deadband_deg = self.steering_angle_deadzone_deg + flm_center_deadband_deg
      curvature_deadzone = abs(VM.calc_curvature(math.radians(effective_deadband_deg), CS.vEgo, 0.0))
      lateral_accel_deadzone = curvature_deadzone * CS.vEgo ** 2

      delay_frames = int(np.clip(lat_delay / self.dt, 1, self.request_buffer_len))
      expected_lateral_accel = self.curvature_request_buffer[-delay_frames] * CS.vEgo ** 2
      self.curvature_request_buffer.append(desired_curvature)
      raw_lateral_jerk = (future_desired_lateral_accel - expected_lateral_accel) / max(lat_delay, self.dt)
      raw_lateral_jerk = np.clip(raw_lateral_jerk, -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP)
      desired_lateral_jerk = np.clip(self.jerk_filter.update(raw_lateral_jerk), -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP)
      gravity_adjusted_future_lateral_accel = future_desired_lateral_accel - roll_compensation
      setpoint = expected_lateral_accel + desired_lateral_jerk * lat_delay
      desired_lateral_accel_rate = (setpoint - self.prev_desired_lateral_accel) / self.dt
      unwind_detected = (desired_lateral_accel_rate < UNWIND_D_DES_THRESHOLD and
                         abs(setpoint) < UNWIND_LAT_ACCEL_NEAR_ZERO)
      self.prev_desired_lateral_accel = setpoint

      measurement_rate = self.measurement_rate_filter.update((measurement - self.previous_measurement) / self.dt)
      measurement_rate = np.clip(measurement_rate, -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP)
      self.previous_measurement = measurement

      low_speed_factor = (np.interp(CS.vEgo, LOW_SPEED_X, LOW_SPEED_Y) / max(CS.vEgo, MIN_SPEED)) ** 2
      current_kp = np.interp(CS.vEgo, self.pid._k_p[0], self.pid._k_p[1])
      error = setpoint - measurement
      error_with_lsf = error * (1 + low_speed_factor / max(current_kp, 1e-3))

      # do error correction in lateral acceleration space, convert at end to handle non-linear torque responses correctly
      pid_log.error = float(error_with_lsf)
      ff = gravity_adjusted_future_lateral_accel
      # latAccelOffset corrects roll compensation bias from device roll misalignment relative to car roll
      ff -= self.torque_params.latAccelOffset * roll_offset_fade
      ff_scale = 1.0
      if self.use_bolt_ff_scaling:
        ff_scale = np.interp(ff, [-FF_SCALE_BLEND_LAT_ACCEL, 0.0, FF_SCALE_BLEND_LAT_ACCEL],
                             [self.torque_ff_scale_neg, 1.0, self.torque_ff_scale_pos])
      ff *= ff_scale
      trailer_load_kg = float(max(getattr(starpilot_toggles, "trailer_load_kg", 0.0) or 0.0, 0.0))
      bolt_2022_2023_tuned_path_active = self.is_bolt_2022_2023
      bolt_2018_2021_tuned_path_active = self.is_bolt_2018_2021
      volt_standard_test_active = self.is_volt_standard and volt_standard_lateral_testing_ground_active()
      genesis_g90_test_active = self.is_genesis_g90 and genesis_g90_lateral_testing_ground_active()
      palisade_active = self.is_palisade
      prius_active = self.is_prius
      rav4_prime_active = self.is_rav4_prime
      sienna_4th_gen_active = self.is_sienna_4th_gen
      lexus_is_active = self.is_lexus_is
      ioniq_5_active = self.is_ioniq_5
      ioniq_ev_old_active = self.is_ioniq_ev_old
      ioniq_6_active = self.is_ioniq_6
      sonata_active = self.is_sonata
      sonata_hybrid_active = self.is_sonata_hybrid
      elantra_non_scc_active = self.is_elantra_non_scc
      kia_xceed_active = self.is_kia_xceed
      kia_niro_phev_2022_active = self.is_kia_niro_phev_2022
      kia_stinger_2022_active = self.is_kia_stinger_2022
      kia_forte_active = self.is_kia_forte
      kia_ev6_active = self.is_kia_ev6
      kia_carnival_active = self.is_kia_carnival
      tucson_4th_gen_active = self.is_tucson_4th_gen
      volt_plexy_test_active = self.is_volt_standard and volt_plexy_lateral_testing_ground_active()
      ioniq_5_center_taper = get_ioniq_5_center_taper_scale(setpoint, CS.vEgo) if ioniq_5_active else 1.0
      prius_center_taper = get_prius_center_taper_scale(setpoint, CS.vEgo) if prius_active else 1.0
      volt_standard_center_taper = get_volt_standard_center_taper_scale(setpoint, CS.vEgo) if volt_standard_test_active else 1.0
      volt_plexy_center_taper = get_volt_plexy_center_taper_scale(setpoint, CS.vEgo) if volt_plexy_test_active else 1.0
      ioniq_ev_old_center_taper = get_ioniq_ev_old_center_taper_scale(setpoint, CS.vEgo) if ioniq_ev_old_active else 1.0
      ioniq_6_center_taper = get_ioniq_6_center_taper_scale(setpoint, CS.vEgo) if ioniq_6_active else 1.0
      sonata_center_taper = get_sonata_center_taper_scale(setpoint, CS.vEgo) if sonata_active else 1.0
      sonata_hybrid_center_taper = get_sonata_hybrid_center_taper_scale(setpoint, CS.vEgo) if sonata_hybrid_active else 1.0
      kia_xceed_center_taper = get_kia_xceed_center_taper_scale(setpoint, CS.vEgo) if kia_xceed_active else 1.0
      kia_niro_phev_2022_center_taper = get_kia_niro_phev_2022_center_taper_scale(setpoint, CS.vEgo) if kia_niro_phev_2022_active else 1.0
      kia_stinger_2022_center_taper = get_kia_stinger_2022_center_taper_scale(setpoint, CS.vEgo) if kia_stinger_2022_active else 1.0
      kia_forte_center_taper = get_kia_forte_center_taper_scale(setpoint, CS.vEgo) if kia_forte_active else 1.0
      kia_ev6_center_taper = get_kia_ev6_center_taper_scale(setpoint, CS.vEgo) if kia_ev6_active else 1.0
      kia_ev6_low_speed_center_taper = get_kia_ev6_low_speed_center_taper_scale(setpoint, CS.vEgo) if kia_ev6_active else 1.0
      kia_carnival_center_taper = get_kia_carnival_center_taper_scale(setpoint, CS.vEgo) if kia_carnival_active else 1.0
      tucson_4th_gen_center_taper = get_tucson_4th_gen_center_taper_scale(setpoint, CS.vEgo) if tucson_4th_gen_active else 1.0
      silverado_center_taper = get_silverado_center_taper_scale(setpoint, CS.vEgo) if self.is_silverado else 1.0
      civic_bosch_modified_a_center_taper = get_civic_bosch_modified_a_center_taper_scale(setpoint, CS.vEgo) if (
        self.is_civic_bosch_modified and civic_bosch_modified_a_lateral_testing_ground_active()
      ) else 1.0
      if self.is_hkg_canfd_torque:
        friction_threshold = get_hkg_canfd_base_friction_threshold(CS.vEgo)
      elif self.is_gm:
        friction_threshold = get_gm_base_friction_threshold(CS.vEgo)
      else:
        friction_threshold = get_standard_friction_threshold(CS.vEgo)
      friction_scale = 1.0
      if bolt_2022_2023_tuned_path_active:
        ff *= get_bolt_2022_2023_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo)
        friction_threshold = get_bolt_2022_2023_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = get_bolt_2022_2023_friction_scale(CS.vEgo, setpoint, desired_lateral_jerk)
      elif bolt_2018_2021_tuned_path_active:
        friction_threshold = get_bolt_2018_2021_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = get_bolt_2018_2021_friction_scale(CS.vEgo, setpoint, desired_lateral_jerk)
      elif volt_standard_test_active:
        ff *= get_volt_standard_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo) * volt_standard_center_taper
        friction_threshold = get_volt_standard_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = get_volt_standard_friction_scale(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = 1.0 + ((friction_scale - 1.0) * volt_standard_center_taper)
      elif genesis_g90_test_active:
        ff *= get_genesis_g90_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo)
        friction_threshold = get_genesis_g90_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = get_genesis_g90_friction_scale(CS.vEgo, setpoint, desired_lateral_jerk)
      elif palisade_active:
        ff *= get_palisade_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo)
        friction_threshold = get_palisade_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = get_palisade_friction_scale(CS.vEgo, setpoint, desired_lateral_jerk)
      elif prius_active:
        ff *= get_prius_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo) * prius_center_taper
        friction_threshold = get_prius_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = get_prius_friction_scale(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = 1.0 + ((friction_scale - 1.0) * prius_center_taper)
      elif rav4_prime_active:
        ff *= get_rav4_prime_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo)
        friction_threshold = get_rav4_prime_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = get_rav4_prime_friction_scale(CS.vEgo, setpoint, desired_lateral_jerk)
      elif sienna_4th_gen_active:
        ff *= get_sienna_4th_gen_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo)
        friction_threshold = get_sienna_4th_gen_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
      elif lexus_is_active:
        ff *= get_lexus_is_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo)
      elif ioniq_5_active:
        ff *= get_ioniq_5_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo) * ioniq_5_center_taper
        friction_threshold = get_ioniq_5_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = get_ioniq_5_friction_scale(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = 1.0 + ((friction_scale - 1.0) * ioniq_5_center_taper)
      elif ioniq_ev_old_active:
        ff *= get_ioniq_ev_old_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo) * ioniq_ev_old_center_taper
        friction_scale = 1.0 + ((friction_scale - 1.0) * ioniq_ev_old_center_taper)
      elif ioniq_6_active:
        # smooth the directional taper so jerk-gated unwind cuts can't step the FF in one frame
        ioniq_6_directional_taper = self.ioniq_6_directional_taper_filter.update(
          get_ioniq_6_directional_taper_scale(setpoint, desired_lateral_jerk, CS.vEgo))
        ff *= get_ioniq_6_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo,
                                   directional_taper_scale=ioniq_6_directional_taper) * ioniq_6_center_taper
        friction_threshold = get_ioniq_6_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk) / max(ioniq_6_center_taper, 1e-3)
        friction_scale = get_ioniq_6_friction_scale(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = 1.0 + ((friction_scale - 1.0) * ioniq_6_center_taper)
        friction_scale *= get_ioniq_6_friction_center_fade_scale(setpoint, CS.vEgo)
      elif sonata_active:
        ff *= get_sonata_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo) * sonata_center_taper
      elif sonata_hybrid_active:
        ff *= get_sonata_hybrid_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo) * sonata_hybrid_center_taper
      elif elantra_non_scc_active:
        ff *= get_elantra_non_scc_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo)
      elif kia_xceed_active:
        ff *= get_kia_xceed_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo) * kia_xceed_center_taper
      elif kia_niro_phev_2022_active:
        friction_threshold = get_kia_niro_phev_2022_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
      elif kia_stinger_2022_active:
        friction_threshold = get_kia_stinger_2022_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
      elif kia_forte_active:
        ff *= get_kia_forte_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo) * kia_forte_center_taper
        friction_threshold = get_kia_forte_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
      elif kia_ev6_active:
        ff *= get_kia_ev6_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo) * kia_ev6_center_taper
        friction_threshold = get_kia_ev6_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = get_kia_ev6_friction_scale(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = 1.0 + ((friction_scale - 1.0) * kia_ev6_center_taper)
      elif kia_carnival_active:
        friction_threshold = get_kia_carnival_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale *= get_kia_carnival_friction_center_fade_scale(setpoint, CS.vEgo)
      elif tucson_4th_gen_active:
        friction_threshold = get_tucson_4th_gen_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
      elif self.is_silverado:
        ff *= silverado_center_taper
      elif volt_plexy_test_active:
        ff *= get_volt_plexy_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo) * volt_plexy_center_taper
        friction_threshold = get_volt_plexy_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = get_volt_plexy_friction_scale(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = 1.0 + ((friction_scale - 1.0) * volt_plexy_center_taper)
      elif self.is_civic_bosch_modified:
        ff *= get_civic_bosch_modified_b_ff_scale(setpoint, desired_lateral_jerk, CS.vEgo) * civic_bosch_modified_a_center_taper
        friction_threshold = CIVIC_BOSCH_MODIFIED_B_FIXED_FRICTION_THRESHOLD
        friction_scale = get_civic_bosch_modified_b_friction_scale(CS.vEgo, setpoint, desired_lateral_jerk)
        friction_scale = 1.0 + ((friction_scale - 1.0) * civic_bosch_modified_a_center_taper)
      if flm_surface_active and self.flm_surface_profile_key and not ioniq_6_active:
        universal_flm_profile = self.flm_surface_profile_key == FLM_UNIVERSAL_PROFILE_KEY
        flm_full_surface_center_taper = get_flm_full_surface_center_taper_scale(self.flm_surface_profile_key, setpoint, CS.vEgo,
                                                                                include_base_center=universal_flm_profile)
        ff *= get_flm_full_surface_ff_scale(self.flm_surface_profile_key, setpoint, desired_lateral_jerk, CS.vEgo,
                                            include_base_ff=universal_flm_profile) * flm_full_surface_center_taper
        friction_threshold = get_flm_full_surface_friction_threshold(self.flm_surface_profile_key, friction_threshold, CS.vEgo,
                                                                     setpoint, desired_lateral_jerk,
                                                                     include_base_threshold=universal_flm_profile)
      if trailer_load_kg > 0.0:
        ff *= get_trailer_lateral_ff_scale(trailer_load_kg, CS.vEgo, setpoint)
        friction_scale *= get_trailer_lateral_friction_scale(trailer_load_kg, CS.vEgo, setpoint)
      friction_jerk = desired_lateral_jerk
      if ioniq_6_active:
        # planner jerk noise on straights (< ~0.3 m/s^3) chatters the friction compensation
        friction_jerk = math.copysign(max(abs(desired_lateral_jerk) - IONIQ_6_FRICTION_JERK_DEADZONE, 0.0), desired_lateral_jerk)
      ff += friction_scale * get_friction(error_with_lsf + JERK_GAIN * friction_jerk, lateral_accel_deadzone, friction_threshold, self.torque_params)
      deadzone_boost_active = False
      if self.torque_deadzone_boost > 0.0 and abs(gravity_adjusted_future_lateral_accel) < DEADZONE_BOOST_LAT_ACCEL:
        boost_scale = np.interp(abs(gravity_adjusted_future_lateral_accel), [0.0, DEADZONE_BOOST_LAT_ACCEL], [1.0, 0.0])
        ff += np.sign(gravity_adjusted_future_lateral_accel) * self.torque_deadzone_boost * boost_scale
        deadzone_boost_active = True

      if CS.vEgo < self.low_speed_reset_threshold:
        self.pid.reset()
      freeze_integrator = (steer_limited_by_safety or CS.steeringPressed or
                           CS.vEgo < self.low_speed_reset_threshold or unwind_detected)
      output_lataccel = self.pid.update(pid_log.error, error_rate=-measurement_rate, speed=CS.vEgo, feedforward=ff, freeze_integrator=freeze_integrator)
      output_torque = self.torque_from_lateral_accel(output_lataccel, self.torque_params)
      if bolt_2022_2023_tuned_path_active:
        output_torque *= get_bolt_2022_2023_center_output_scale(setpoint, CS.vEgo)
      elif self.is_bolt_2017:
        output_torque *= get_bolt_2017_torque_scale(setpoint, desired_lateral_jerk, CS.vEgo)
      elif bolt_2018_2021_tuned_path_active:
        output_torque *= get_bolt_2018_2021_dynamic_torque_scale(setpoint, desired_lateral_jerk, CS.vEgo)
      elif ioniq_6_active and not CS.steeringPressed:
        desired_angle_no_offset = math.degrees(VM.get_steer_from_curvature(-desired_curvature, CS.vEgo, params.roll))
        actual_angle_no_offset = CS.steeringAngleDeg - params.angleOffsetDeg
        output_torque = get_ioniq_6_low_speed_angle_assist_torque(desired_angle_no_offset, actual_angle_no_offset,
                                                                  output_torque, CS.vEgo)
      elif flm_surface_active and self.flm_surface_profile_key and not CS.steeringPressed:
        desired_angle_no_offset = math.degrees(VM.get_steer_from_curvature(-desired_curvature, CS.vEgo, params.roll))
        actual_angle_no_offset = CS.steeringAngleDeg - params.angleOffsetDeg
        output_torque = get_flm_full_surface_low_speed_angle_assist_torque(self.flm_surface_profile_key, desired_angle_no_offset,
                                                                           actual_angle_no_offset, output_torque, CS.vEgo)
      if ioniq_6_active:
        output_torque *= get_ioniq_6_highway_output_taper_scale(setpoint, CS.vEgo)
        output_torque *= get_ioniq_6_highway_transition_output_taper_scale(setpoint, desired_lateral_jerk, CS.vEgo)
      elif self.is_ram_1500 and output_torque * setpoint > 0.0:
        output_torque *= get_ram_1500_transition_output_scale(setpoint, desired_lateral_jerk, CS.vEgo)
      elif self.is_kona_non_scc:
        output_torque *= get_kona_non_scc_center_taper_scale(setpoint, CS.vEgo)
        if output_torque * setpoint > 0.0:
          output_torque *= get_kona_non_scc_highway_transition_output_scale(setpoint, desired_lateral_jerk, CS.vEgo)
      elif rav4_prime_active:
        output_torque *= get_rav4_prime_output_taper_scale(setpoint, desired_lateral_jerk, CS.vEgo)
      elif sienna_4th_gen_active:
        output_torque *= get_sienna_4th_gen_center_taper_scale(setpoint, CS.vEgo)
        output_torque *= get_sienna_4th_gen_high_speed_output_taper_scale(CS.vEgo)
      elif prius_active:
        output_torque *= prius_center_taper
      elif volt_standard_test_active:
        output_torque *= volt_standard_center_taper
      elif volt_plexy_test_active:
        output_torque *= volt_plexy_center_taper
      elif kia_ev6_active:
        output_torque *= kia_ev6_low_speed_center_taper
      elif kia_carnival_active:
        output_torque *= kia_carnival_center_taper
        output_torque *= get_kia_carnival_highway_transition_output_scale(setpoint, desired_lateral_jerk, CS.vEgo)
      elif tucson_4th_gen_active:
        output_torque *= tucson_4th_gen_center_taper
      elif self.is_silverado:
        output_torque *= silverado_center_taper
      elif kia_niro_phev_2022_active:
        output_torque *= kia_niro_phev_2022_center_taper
      elif kia_stinger_2022_active:
        output_torque *= kia_stinger_2022_center_taper
      elif self.is_civic_bosch_modified and civic_bosch_modified_a_lateral_testing_ground_active():
        output_torque *= civic_bosch_modified_a_center_taper
      pid_log.active = True
      pid_log.p = float(self.pid.p)
      pid_log.i = float(self.pid.i)
      pid_log.d = float(self.pid.d)
      pid_log.f = float(self.pid.f)
      pid_log.output = float(-output_torque)  # TODO: log lat accel?
      pid_log.actualLateralAccel = float(measurement)
      pid_log.desiredLateralAccel = float(setpoint)
      pid_log.desiredLateralJerk = float(desired_lateral_jerk)
      pid_log.saturated = bool(self._check_saturation(self.steer_max - abs(output_torque) < 1e-3, CS, steer_limited_by_safety, curvature_limited))

      if DEBUG_TORQUE_TUNE and self.is_bolt:
        self.debug_counter += 1
        if self.debug_counter % 50 == 0:
          print(f"bolt_torque ff_scale={ff_scale:.3f} pos={self.torque_ff_scale_pos:.3f} "
                f"neg={self.torque_ff_scale_neg:.3f} deadzone_boost_active={deadzone_boost_active}")

    self.prev_steering_pressed = CS.steeringPressed

    # TODO left is positive in this convention
    return -output_torque, 0.0, pid_log
