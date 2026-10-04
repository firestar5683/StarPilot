#pragma once

#include "opendbc/safety/declarations.h"
#include "opendbc/safety/modes/ford_aol.h"

// StarPilot's extended Ford curvature enforcement below is substantially adapted from
// BluePilot bp-7.0 panda work, principally Alan Polk's 8f8d6d15f0a590f42b78de964ffb0d0af7f5d63d
// See /CREDITS.md and /THIRD_PARTY_NOTICES.md. This comment does not attribute the surrounding
// upstream openpilot code.


// Safety-relevant CAN messages for Ford vehicles.
#define FORD_EngBrakeData          0x165U   // RX from PCM, for driver brake pedal and cruise state
#define FORD_EngVehicleSpThrottle  0x204U   // RX from PCM, for driver throttle input
#define FORD_DesiredTorqBrk        0x213U   // RX from ABS, for standstill state
#define FORD_BrakeSysFeatures      0x415U   // RX from ABS, for vehicle speed
#define FORD_EngVehicleSpThrottle2 0x202U   // RX from PCM, for second vehicle speed
#define FORD_Yaw_Data_FD1          0x91U    // RX from RCM, for yaw rate
#define FORD_Steering_Data_FD1     0x083U   // TX by OP, various driver switches and LKAS/CC buttons
#define FORD_ACCDATA               0x186U   // TX by OP, ACC controls
#define FORD_ACCDATA_3             0x18AU   // TX by OP, ACC/TJA user interface
#define FORD_Lane_Assist_Data1     0x3CAU   // TX by OP, Lane Keep Assist
#define FORD_Lane_Assist_Data3     0x3CCU   // RX from PSCM, LKA availability
#define FORD_LateralMotionControl  0x3D3U   // TX by OP, Lateral Control message
#define FORD_LateralMotionControl2 0x3D6U   // TX by OP, alternate Lateral Control message
#define FORD_IPMA_Data             0x3D8U   // TX by OP, IPMA and LKAS user interface

// CAN bus numbers.
#define FORD_MAIN_BUS 0U
#define FORD_CAM_BUS  2U

static uint8_t ford_get_counter(const CANPacket_t *msg) {
  uint8_t cnt = 0;
  if (msg->addr == FORD_BrakeSysFeatures) {
    // Signal: VehVActlBrk_No_Cnt
    cnt = (msg->data[2] >> 2) & 0xFU;
  }
  if (msg->addr == FORD_Yaw_Data_FD1) {
    // Signal: VehRollYaw_No_Cnt
    cnt = msg->data[5];
  }
  return cnt;
}

static uint32_t ford_get_checksum(const CANPacket_t *msg) {
  uint8_t chksum = 0;
  if (msg->addr == FORD_BrakeSysFeatures) {
    // Signal: VehVActlBrk_No_Cs
    chksum = msg->data[3];
  }
  if (msg->addr == FORD_Yaw_Data_FD1) {
    // Signal: VehRollYawW_No_Cs
    chksum = msg->data[4];
  }
  return chksum;
}

static uint32_t ford_compute_checksum(const CANPacket_t *msg) {
  uint8_t chksum = 0;
  if (msg->addr == FORD_BrakeSysFeatures) {
    chksum += msg->data[0] + msg->data[1];  // Veh_V_ActlBrk
    chksum += msg->data[2] >> 6;                    // VehVActlBrk_D_Qf
    chksum += (msg->data[2] >> 2) & 0xFU;           // VehVActlBrk_No_Cnt
    chksum = 0xFFU - chksum;
  }
  if (msg->addr == FORD_Yaw_Data_FD1) {
    chksum += msg->data[0] + msg->data[1];  // VehRol_W_Actl
    chksum += msg->data[2] + msg->data[3];  // VehYaw_W_Actl
    chksum += msg->data[5];                         // VehRollYaw_No_Cnt
    chksum += msg->data[6] >> 6;                    // VehRolWActl_D_Qf
    chksum += (msg->data[6] >> 4) & 0x3U;           // VehYawWActl_D_Qf
    chksum = 0xFFU - chksum;
  }
  return chksum;
}

static bool ford_get_quality_flag_valid(const CANPacket_t *msg) {
  bool valid = false;
  if (msg->addr == FORD_BrakeSysFeatures) {
    valid = (msg->data[2] >> 6) == 0x3U;           // VehVActlBrk_D_Qf
  }
  if (msg->addr == FORD_EngVehicleSpThrottle2) {
    valid = ((msg->data[4] >> 5) & 0x3U) == 0x3U;  // VehVActlEng_D_Qf
  }
  if (msg->addr == FORD_Yaw_Data_FD1) {
    valid = ((msg->data[6] >> 4) & 0x3U) == 0x3U;  // VehYawWActl_D_Qf
  }
  return valid;
}

#define FORD_INACTIVE_CURVATURE 1000U
#define FORD_INACTIVE_CURVATURE_RATE 4096U
#define FORD_INACTIVE_PATH_OFFSET 512U
#define FORD_INACTIVE_PATH_ANGLE 1000U

#define FORD_CANFD_INACTIVE_CURVATURE_RATE 1024U

static const CurvatureSteeringLimits FORD_STEERING_LIMITS = {
  .max_curvature = 1000,              // 0.02 rad/m * curvature_to_can
  .curvature_to_can = 50000,          // CAN units per rad/m
  .frequency = 20,                    // Hz
  .max_curvature_error = 100,         // 0.002 rad/m * curvature_to_can
  .curvature_error_min_speed = 10.0,  // m/s
  .max_steer_power = 0,               // disabled, Ford has no steed power signal
};

// Transit 0x3CA has 0.000005 rad/m per raw step and runs at 33 Hz. Keep its
// command history separate from the inactive 0x3D3 heartbeat at 20 Hz.
static const CurvatureSteeringLimits FORD_LKA_STEERING_LIMITS = {
  .max_curvature = 2046,
  .curvature_to_can = 200000,
  .frequency = 33,
  .max_curvature_error = 400,
  .curvature_error_min_speed = 10.0,
  .max_steer_power = 0,
};

static bool ford_stock_switch = false;
static bool ford_cancel_resume_button = false;

static bool ford_generic_canfd_extended = false;
static bool ford_generic_canfd_announced = false;

static bool ford_explorer_extended = false;
static bool ford_explorer_announced = false;

static bool ford_mach_e_extended = false;
static bool ford_mach_e_announced = false;
static int ford_mach_e_path_angle_last = 0;

static bool ford_lka_steering = false;
static bool ford_lka_available = false;
static uint32_t ford_lka_last_us = 0U;
static uint32_t ford_lka_speed_last_us = 0U;
static uint32_t ford_lka_speed2_last_us = 0U;
static uint32_t ford_lka_yaw_last_us = 0U;
static bool ford_lka_speed_seen = false;
static bool ford_lka_speed2_seen = false;
static bool ford_lka_yaw_seen = false;
static CurvatureSteeringState ford_lka_curvature_state;
static int ford_lka_angle_last = 2048;

static bool ford_lka_curvature_checks(int desired_curvature, bool active) {
  CurvatureSteeringState previous = curvature_state;
  curvature_state = ford_lka_curvature_state;
  bool violation = steer_curvature_cmd_checks(desired_curvature, 0, active, FORD_LKA_STEERING_LIMITS);
  ford_lka_curvature_state = curvature_state;
  curvature_state = previous;
  return violation;
}

static void ford_rx_hook(const CANPacket_t *msg) {
  ford_aol_rx(msg);
  // Update in motion state from standstill signal
  if (msg_matches(msg, FORD_DesiredTorqBrk, FORD_MAIN_BUS)) {
    // Signal: VehStop_D_Stat
    vehicle_moving = ((msg->data[3] >> 3) & 0x3U) != 1U;
  }

  // Update vehicle speed
  if (msg_matches(msg, FORD_BrakeSysFeatures, FORD_MAIN_BUS)) {
    // Signal: Veh_V_ActlBrk
    UPDATE_VEHICLE_SPEED(((msg->data[0] << 8) | msg->data[1]) * 0.01 * KPH_TO_MS);
    if (ford_lka_steering) { ford_lka_speed_seen = true; ford_lka_speed_last_us = microsecond_timer_get(); }
  }
  if (msg_matches(msg, FORD_Lane_Assist_Data3, FORD_MAIN_BUS) && ford_lka_steering) {
    ford_lka_available = (((msg->data[0] >> 4) & 0x3U) == 3U) && ((msg->data[0] & 0x40U) == 0U);
    ford_lka_last_us = microsecond_timer_get();
  }

  // Check vehicle speed against a second source
  if (msg_matches(msg, FORD_EngVehicleSpThrottle2, FORD_MAIN_BUS)) {
    // Disable controls if speeds from ABS and PCM ECUs are too far apart.
    // Signal: Veh_V_ActlEng
    float filtered_pcm_speed = ((msg->data[6] << 8) | msg->data[7]) * 0.01 * KPH_TO_MS;
    UPDATE_VEHICLE_SPEED_2(filtered_pcm_speed);
    if (ford_lka_steering) { ford_lka_speed2_seen = true; ford_lka_speed2_last_us = microsecond_timer_get(); }
  }

  // Update vehicle yaw rate
  if (msg_matches(msg, FORD_Yaw_Data_FD1, FORD_MAIN_BUS)) {
    // FIXME: safety can receive yaw before new vehicle speed, it should recompute meas on either received
    // Signal: VehYaw_W_Actl
    // TODO: we should use the speed which results in the closest angle measurement to the desired angle
    float ford_yaw_rate = (((msg->data[2] << 8U) | msg->data[3]) * 0.0002) - 6.5;
    float current_curvature = ford_yaw_rate / SAFETY_MAX(vehicle_speed.values[0] / VEHICLE_SPEED_FACTOR, 0.1);
    // convert current curvature into units on CAN for comparison with desired curvature
    update_sample(&curvature_state.meas, ROUND(current_curvature * FORD_STEERING_LIMITS.curvature_to_can));
    if (ford_lka_steering) {
      update_sample(&ford_lka_curvature_state.meas, ROUND(current_curvature * FORD_LKA_STEERING_LIMITS.curvature_to_can));
      ford_lka_yaw_seen = true;
      ford_lka_yaw_last_us = microsecond_timer_get();
    }
  }

  // Update gas pedal
  if (msg_matches(msg, FORD_EngVehicleSpThrottle, FORD_MAIN_BUS)) {
    // Pedal position: (0.1 * val) in percent
    // Signal: ApedPos_Pc_ActlArb
    gas_pressed = (((msg->data[0] & 0x03U) << 8) | msg->data[1]) > 0U;
  }

  // Update brake pedal and cruise state
  if (msg_matches(msg, FORD_EngBrakeData, FORD_MAIN_BUS)) {
    // Signal: BpedDrvAppl_D_Actl
    brake_pressed = ((msg->data[0] >> 4) & 0x3U) == 2U;

    // Signal: CcStat_D_Actl
    unsigned int cruise_state = msg->data[1] & 0x07U;
    bool cruise_engaged = (cruise_state == 4U) || (cruise_state == 5U);
    pcm_cruise_check(cruise_engaged);
    if (ford_stock_switch) {
      acc_main_on = (cruise_state == 3U) || cruise_engaged;
    }
  }
  if (ford_stock_switch && msg_matches(msg, FORD_Steering_Data_FD1, FORD_MAIN_BUS)) {
    // Physical combined cancel/resume switch, not the outgoing resume signal.
    ford_cancel_resume_button = (msg->data[2] & 0x20U) != 0U;
  }
}

static bool ford_tx_hook(const CANPacket_t *msg) {
  const LongitudinalLimits FORD_LONG_LIMITS = {
    // acceleration cmd limits (used for brakes)
    // Signal: AccBrkTot_A_Rq
    .max_accel = 5641,       //  1.9999 m/s^s
    .min_accel = 4231,       // -3.4991 m/s^2
    .inactive_accel = 5128,  // -0.0008 m/s^2

    // gas cmd limits
    // Signal: AccPrpl_A_Rq & AccPrpl_A_Pred
    .max_gas = 700,          //  2.0 m/s^2
    .min_gas = 450,          // -0.5 m/s^2
    .inactive_gas = 0,       // -5.0 m/s^2
  };

  bool tx = true;

  // Safety check for ACCDATA accel and brake requests
  if (msg->addr == FORD_ACCDATA) {
    // Signal: AccPrpl_A_Rq
    int gas = ((msg->data[6] & 0x3U) << 8) | msg->data[7];
    // Signal: AccPrpl_A_Pred
    int gas_pred = ((msg->data[2] & 0x3U) << 8) | msg->data[3];
    // Signal: AccBrkTot_A_Rq
    int accel = ((msg->data[0] & 0x1FU) << 8) | msg->data[1];
    // Signal: CmbbDeny_B_Actl
    bool cmbb_deny = (msg->data[4] >> 5) & 1U;

    // Signal: AccBrkPrchg_B_Rq & AccBrkDecel_B_Rq
    bool brake_actuation = (msg->data[6] & 0xC0U) != 0U;

    bool violation = false;
    violation |= longitudinal_accel_checks(accel, FORD_LONG_LIMITS);
    violation |= longitudinal_gas_checks(gas, FORD_LONG_LIMITS);
    violation |= longitudinal_gas_checks(gas_pred, FORD_LONG_LIMITS);

    // Safety check for stock AEB
    violation |= cmbb_deny;  // do not prevent stock AEB actuation

    violation |= !get_longitudinal_allowed() && brake_actuation;

    if (violation) {
      tx = false;
    }
  }

  // Safety check for Steering_Data_FD1 button signals
  // Note: Many other signals in this message are not relevant to safety (e.g. blinkers, wiper switches, high beam)
  // which we passthru in OP.
  if (msg->addr == FORD_Steering_Data_FD1) {
    // Violation if resume button is pressed while controls not allowed, or
    // if cancel button is pressed when cruise isn't engaged.
    bool violation = false;
    violation |= ((msg->data[1] >> 0) & 1U) && !cruise_engaged_prev;   // Signal: CcAslButtnCnclPress (cancel)
    // Only an actual stock-cruise driver switch can request resume while OP is
    // inactive. Required RX health guards the original level-based permission.
    const bool stock_resume_from_driver = ford_stock_switch && acc_main_on && ford_cancel_resume_button && aol_rx_healthy();
    violation |= ((msg->data[3] >> 1) & 1U) && !(controls_allowed || stock_resume_from_driver);  // Signal: CcAsllButtnResPress (resume)

    if (violation) {
      tx = false;
    }
  }

  // Safety check for Lane_Assist_Data1 action
  if (msg->addr == FORD_Lane_Assist_Data1) {
    if (ford_mach_e_extended || ford_explorer_extended) {
      tx &= (msg->data[4] & 0x1U) == 0U;
    }
    // Do not allow steering using Lane_Assist_Data1 (Lane-Departure Aid).
    // This message must be sent for Lane Centering to work, and can include
    // values such as the steering angle or lane curvature for debugging,
    // but the action (LkaActvStats_D2_Req) must be set to zero.
    unsigned int action = msg->data[0] >> 5;
    if (ford_lka_steering) {
      const int angle = ((msg->data[2] & 0xFU) << 8) | msg->data[3];
      const int curvature = (msg->data[1] << 4) | (msg->data[2] >> 4);
      const uint32_t now = microsecond_timer_get();
      const bool source_current = ford_lka_available && ford_lka_speed_seen && ford_lka_speed2_seen && ford_lka_yaw_seen &&
                                  (cruise_engaged_prev || (ford_aol_enabled && (ford_aol_permission_mask() != 0U))) &&
                                  safety_get_ts_elapsed(now, ford_lka_last_us) <= 100000U &&
                                  safety_get_ts_elapsed(now, ford_lka_speed_last_us) <= 100000U &&
                                  safety_get_ts_elapsed(now, ford_lka_speed2_last_us) <= 100000U &&
                                  safety_get_ts_elapsed(now, ford_lka_yaw_last_us) <= 100000U;
      const bool active = (action == 2U) || (action == 4U);
      const bool direction_valid = ((action == 2U) && (angle >= 2048)) || ((action == 4U) && (angle < 2048));
      const bool payload_valid = (angle >= 24) && (angle <= 4072) && (curvature >= 2) && (curvature <= 4094) &&
                                 (SAFETY_ABS(angle - ford_lka_angle_last) <= 350) &&
                                 ((msg->data[4] & 0x60U) == 0U) && ((msg->data[0] & 0x1FU) == 3U);
      if (active) {
        if (!lateral_controls_allowed() || !source_current || !direction_valid || !payload_valid) {
          tx = false;
        } else if (ford_lka_curvature_checks(curvature - 2048, true)) {
          tx = false;
        } else {
          // Valid active request keeps its transmit decision.
        }
      } else if ((action != 0U) || (angle != 2048) || (curvature != 2048)) {
        tx = false;
      } else {
        // Neutral request needs no additional steering check.
      }
      if (tx) {
        ford_lka_angle_last = active ? angle : 2048;
        if (!active) { (void)ford_lka_curvature_checks(0, false); }
      } else {
        ford_lka_angle_last = 2048;
        ford_lka_curvature_state.desired_last = 0;
      }
    } else if (action != 0U) {
      tx = false;
    } else {
      // Other Ford profiles retain their neutral status handling.
    }
  }

  if (ford_mach_e_extended && tx && (msg->addr == FORD_Lane_Assist_Data1)) {
    ford_mach_e_announced = (msg->data[4] & 0x2U) != 0U;
  }

  if (ford_generic_canfd_extended && tx && (msg->addr == FORD_Lane_Assist_Data1)) {
    ford_generic_canfd_announced = (msg->data[4] & 0x2U) != 0U;
  }

  if (ford_explorer_extended && tx && (msg->addr == FORD_Lane_Assist_Data1)) {
    ford_explorer_announced = (msg->data[4] & 0x2U) != 0U;
  }

  // Safety check for LateralMotionControl action
  if (msg->addr == FORD_LateralMotionControl) {
    // Signal: LatCtl_D_Rq
    bool steer_control_enabled = ((msg->data[4] >> 2) & 0x7U) != 0U;
    unsigned int raw_curvature = (msg->data[0] << 3) | (msg->data[1] >> 5);
    unsigned int raw_curvature_rate = ((msg->data[1] & 0x1FU) << 8) | msg->data[2];
    unsigned int raw_path_angle = (msg->data[3] << 3) | (msg->data[4] >> 5);
    unsigned int raw_path_offset = (msg->data[5] << 2) | (msg->data[6] >> 6);

    // Explorer restores only the classic source-derived curvature-rate field.
    // Every command still intersects the modern common curvature envelope.
    bool violation = (raw_path_angle != FORD_INACTIVE_PATH_ANGLE) ||
                     (raw_path_offset != FORD_INACTIVE_PATH_OFFSET);
    const unsigned int curvature_bits = raw_curvature;
    const int desired_curvature = (int)curvature_bits - 1000;
    if (ford_explorer_extended) {
      static const struct lookup_t source_rate = {{5.0F, 16.0F, 25.0F}, {0.0025F, 0.0014F, 0.00018F}};
      if (steer_control_enabled && lateral_controls_allowed()) {
        const float source_speed = (vehicle_speed.min / VEHICLE_SPEED_FACTOR) - 1.0F;
        const float source_delta_float = (safety_interpolate(source_rate, source_speed) * 50000.0F) + 1.0F;
        const int source_delta = (int)source_delta_float;
        violation |= SAFETY_ABS(desired_curvature - curvature_state.desired_last) > source_delta;
      }
      violation |= steer_control_enabled && !ford_explorer_announced;
      violation |= !steer_control_enabled && ((desired_curvature != 0) ||
                                             (raw_curvature_rate != FORD_INACTIVE_CURVATURE_RATE));
    } else {
      violation |= raw_curvature_rate != FORD_INACTIVE_CURVATURE_RATE;
    }
    violation |= steer_curvature_cmd_checks(desired_curvature, 0, steer_control_enabled, FORD_STEERING_LIMITS);
    violation |= ford_lka_steering && steer_control_enabled;

    if (violation) {
      tx = false;
      if (ford_explorer_extended) {
        curvature_state.desired_last = 0;
      }
    }
  }

  // Safety check for LateralMotionControl2 action
  if (msg->addr == FORD_LateralMotionControl2) {
    // Signal: LatCtl_D2_Rq
    bool steer_control_enabled = ((msg->data[0] >> 4) & 0x7U) != 0U;
    unsigned int raw_curvature = (msg->data[2] << 3) | (msg->data[3] >> 5);
    unsigned int raw_curvature_rate = (msg->data[6] << 3) | (msg->data[7] >> 5);
    unsigned int raw_path_angle = ((msg->data[3] & 0x1FU) << 6) | (msg->data[4] >> 2);
    unsigned int raw_path_offset = ((msg->data[4] & 0x3U) << 8) | msg->data[5];

    const unsigned int curvature_bits = raw_curvature;
    const int desired_curvature = (int)curvature_bits - (int)FORD_INACTIVE_CURVATURE;
    const int desired_path_angle = (int)raw_path_angle - (int)FORD_INACTIVE_PATH_ANGLE;
    bool violation = raw_path_offset != FORD_INACTIVE_PATH_OFFSET;
    if (ford_mach_e_extended) {
      // Exact Mach-E extension retains the source envelope and the modern common
      // ISO/RT checks. This is an intersection, not generic Ford limit widening.
      static const CurvatureSteeringLimits FORD_MACH_E_STEERING_LIMITS = {
        .max_curvature = 1000,
        .curvature_to_can = 50000,
        .frequency = 20,
        .max_curvature_error = 300,
        .curvature_error_min_speed = 10.0,
        .max_steer_power = 0,
      };
      const struct lookup_t source_rate = {{5.0F, 16.0F, 25.0F}, {0.0025F, 0.0014F, 0.00018F}};
      const float speed = vehicle_speed.max / VEHICLE_SPEED_FACTOR;
      const float speed_min = SAFETY_MAX(vehicle_speed.min / VEHICLE_SPEED_FACTOR, 1.0F);
      const int source_delta = (safety_interpolate(source_rate, speed_min - 1.0F) * 50000.0F) + 1.0F;
      const float source_max_float = ((3.0F - (9.81F * 0.06F)) / (speed_min * speed_min) * 50000.0F) + 1.0F;
      const int source_max = (int)source_max_float;
      if (!ford_mach_e_announced) {
        violation |= steer_control_enabled || (desired_path_angle != 0) || (raw_curvature_rate != FORD_CANFD_INACTIVE_CURVATURE_RATE);
      }
      if (steer_control_enabled) {
        violation |= SAFETY_ABS(desired_curvature - curvature_state.desired_last) > source_delta;
        violation |= SAFETY_ABS(desired_curvature) > source_max;
      } else {
        violation |= (desired_curvature != 0) || (raw_curvature_rate != FORD_CANFD_INACTIVE_CURVATURE_RATE);
      }
      if (desired_path_angle != 0) {
        const float curvature = SAFETY_ABS(desired_curvature) / 50000.0F;
        const float path_angle = SAFETY_ABS(desired_path_angle) / 2000.0F;
        const float combined_accel = (curvature + (path_angle / SAFETY_MAX(speed, 1.0F))) * speed * speed;
        violation |= !steer_control_enabled || !lateral_controls_allowed();
        violation |= (speed < 3.0F) || (speed >= 8.8F);
        violation |= (SAFETY_ABS(desired_curvature) < 975) || (SAFETY_ABS(desired_path_angle) > 320);
        violation |= ((desired_curvature * desired_path_angle) <= 0) || (combined_accel > 2.5F);
        violation |= SAFETY_ABS(desired_path_angle - ford_mach_e_path_angle_last) > 110;
      }
      violation |= steer_curvature_cmd_checks(desired_curvature, 0, steer_control_enabled, FORD_MACH_E_STEERING_LIMITS);
    } else if (ford_generic_canfd_extended) {
      // One generic CAN FD owner; Mach-E's wider error/path assist stays separate.
      static const struct lookup_t source_rate = {{5.0F, 16.0F, 25.0F}, {0.0025F, 0.0014F, 0.00018F}};
      const float source_speed = SAFETY_MAX(vehicle_speed.min / VEHICLE_SPEED_FACTOR, 1.0F);
      const float source_delta_float = (safety_interpolate(source_rate, source_speed - 1.0F) * 50000.0F) + 1.0F;
      const int source_delta = (int)source_delta_float;
      const float source_max_float = ((3.0F - (9.81F * 0.06F)) / (source_speed * source_speed) * 50000.0F) + 1.0F;
      const int source_max = (int)source_max_float;
      violation |= raw_path_angle != FORD_INACTIVE_PATH_ANGLE;
      violation |= steer_control_enabled && !ford_generic_canfd_announced;
      if (steer_control_enabled) {
        violation |= SAFETY_ABS(desired_curvature - curvature_state.desired_last) > source_delta;
        violation |= SAFETY_ABS(desired_curvature) > source_max;
      } else {
        violation |= (desired_curvature != 0) || (raw_curvature_rate != FORD_CANFD_INACTIVE_CURVATURE_RATE);
      }
      violation |= steer_curvature_cmd_checks(desired_curvature, 0, steer_control_enabled, FORD_STEERING_LIMITS);
    } else {
      violation |= (raw_curvature_rate != FORD_CANFD_INACTIVE_CURVATURE_RATE) || (raw_path_angle != FORD_INACTIVE_PATH_ANGLE);
      violation |= steer_curvature_cmd_checks(desired_curvature, 0, steer_control_enabled, FORD_STEERING_LIMITS);
    }
    tx &= !violation;
    if (ford_generic_canfd_extended && !tx) {
      curvature_state.desired_last = 0;
    }
    if (ford_mach_e_extended && !tx) {
      // External path/announcement checks must not retain a rejected command.
      curvature_state.desired_last = 0;
      ford_mach_e_path_angle_last = 0;
    }
    if (ford_mach_e_extended && tx) {
      ford_mach_e_path_angle_last = desired_path_angle;
    }
  }

  ford_aol_tx(msg, tx);
  return tx;
}

static safety_config ford_init(uint16_t param) {
  // warning: quality flags are not yet checked in openpilot's CAN parser,
  // this may be the cause of blocked messages
  // Shared entries preserve all current checksum/counter/quality contracts.
  #define FORD_COMMON_RX_CHECKS \
    {.msg = {{FORD_BrakeSysFeatures, 0, 8, 50U, .max_counter = 15U}, { 0 }, { 0 }}}, \
    {.msg = {{FORD_EngVehicleSpThrottle2, 0, 8, 50U, .ignore_checksum = true, .ignore_counter = true}, { 0 }, { 0 }}}, \
    {.msg = {{FORD_Yaw_Data_FD1, 0, 8, 100U, .max_counter = 255U}, { 0 }, { 0 }}}, \
    {.msg = {{FORD_EngBrakeData, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}}, \
    {.msg = {{FORD_EngVehicleSpThrottle, 0, 8, 100U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}}, \
    {.msg = {{FORD_DesiredTorqBrk, 0, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
  static RxCheck ford_rx_checks[] = { FORD_COMMON_RX_CHECKS };
  static RxCheck ford_lka_rx_checks[] = {
    FORD_COMMON_RX_CHECKS
    {.msg = {{FORD_Lane_Assist_Data3, 0, 8, 30U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
  };
  static RxCheck ford_stock_rx_checks[] = {
    FORD_COMMON_RX_CHECKS
    {.msg = {{FORD_Steering_Data_FD1, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
  };
  static RxCheck ford_stock_lka_rx_checks[] = {
    FORD_COMMON_RX_CHECKS
    {.msg = {{FORD_Lane_Assist_Data3, 0, 8, 30U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
    {.msg = {{FORD_Steering_Data_FD1, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
  };

  #define FORD_COMMON_TX_MSGS \
    {FORD_Steering_Data_FD1, 0, 8, .check_relay = false}, \
    {FORD_Steering_Data_FD1, 2, 8, .check_relay = false}, \
    {FORD_ACCDATA_3, 0, 8, .check_relay = true},          \
    {FORD_Lane_Assist_Data1, 0, 8, .check_relay = true},  \
    {FORD_IPMA_Data, 0, 8, .check_relay = true},          \

#ifdef ALLOW_DEBUG
  static const CanMsg FORD_CANFD_LONG_TX_MSGS[] = {
    FORD_COMMON_TX_MSGS
    {FORD_ACCDATA, 0, 8, .check_relay = true},
    {FORD_LateralMotionControl2, 0, 8, .check_relay = true},
  };
#endif

  static const CanMsg FORD_CANFD_STOCK_TX_MSGS[] = {
    FORD_COMMON_TX_MSGS
    {FORD_LateralMotionControl2, 0, 8, .check_relay = true},
  };

  static const CanMsg FORD_LONG_TX_MSGS[] = {
    FORD_COMMON_TX_MSGS
    {FORD_ACCDATA, 0, 8, .check_relay = true},
    {FORD_LateralMotionControl, 0, 8, .check_relay = true},
  };
  static const CanMsg FORD_STOCK_TX_MSGS[] = {
    FORD_COMMON_TX_MSGS
    {FORD_LateralMotionControl, 0, 8, .check_relay = true},
  };

  const uint16_t FORD_PARAM_CANFD = 2;
  const uint16_t FORD_PARAM_LKA_STEERING = 4;
  const uint16_t FORD_PARAM_NEW_PORT = 8;
  const uint16_t FORD_PARAM_MACH_E_EXTENDED = 16U;
  const uint16_t FORD_PARAM_EXPLORER_EXTENDED = 32U;
  const uint16_t FORD_PARAM_GENERIC_CANFD_EXTENDED = 64U;
  const bool generic_canfd_namespace = GET_FLAG(param, FORD_PARAM_GENERIC_CANFD_EXTENDED);
  ford_generic_canfd_extended = (param == 66U) && (((unsigned int)alternative_experience == 0U) || (((unsigned int)alternative_experience == 32U) && ford_aol_param_valid(param)));
#ifdef ALLOW_DEBUG
  ford_generic_canfd_extended |= (param == 67U) && (((unsigned int)alternative_experience == 0U) || (((unsigned int)alternative_experience == 32U) && ford_aol_param_valid(param)));
#endif
  ford_generic_canfd_announced = false;
  const bool explorer_namespace = GET_FLAG(param, FORD_PARAM_EXPLORER_EXTENDED);
  ford_explorer_extended = ((param == 32U) || (param == 33U)) &&
                           (((unsigned int)alternative_experience == 0U) || (((unsigned int)alternative_experience == 32U) && ford_aol_param_valid(param)));
  ford_explorer_announced = false;
  const bool mach_e_namespace = GET_FLAG(param, FORD_PARAM_MACH_E_EXTENDED);
  ford_mach_e_extended = (param == 18U) && (((unsigned int)alternative_experience == 0U) || (((unsigned int)alternative_experience == 32U) && ford_aol_param_valid(param)));
#ifdef ALLOW_DEBUG
  ford_mach_e_extended |= (param == 19U) && (((unsigned int)alternative_experience == 0U) || (((unsigned int)alternative_experience == 32U) && ford_aol_param_valid(param)));
#endif
  ford_stock_switch = (((unsigned int)alternative_experience == 0U) || (((unsigned int)alternative_experience == 32U) && ford_aol_param_valid(param))) &&
                      ((param == 2U) || (param == 8U) || (param == 10U) || (param == 12U) ||
                       ((param == 18U) && ford_mach_e_extended) ||
                       ((param == 32U) && ford_explorer_extended) ||
                       ((param == 66U) && ford_generic_canfd_extended));
  ford_cancel_resume_button = false;
  ford_mach_e_path_angle_last = 0;
  ford_mach_e_announced = false;
  const bool ford_canfd = GET_FLAG(param, FORD_PARAM_CANFD);
  ford_lka_steering = GET_FLAG(param, FORD_PARAM_LKA_STEERING);
  const bool ford_new_port = GET_FLAG(param, FORD_PARAM_NEW_PORT);
  ford_lka_available = false;
  ford_lka_last_us = 0U;
  ford_lka_speed_last_us = 0U;
  ford_lka_speed2_last_us = 0U;
  ford_lka_yaw_last_us = 0U;
  ford_lka_speed_seen = false;
  ford_lka_speed2_seen = false;
  ford_lka_yaw_seen = false;
  ford_lka_curvature_state = (CurvatureSteeringState){0};
  ford_lka_angle_last = 2048;

  safety_config ret;
  if (ford_canfd) {
    ret = BUILD_SAFETY_CFG(ford_rx_checks, FORD_CANFD_STOCK_TX_MSGS);
#ifdef ALLOW_DEBUG
    const uint16_t FORD_PARAM_LONGITUDINAL = 1;
    if (GET_FLAG(param, FORD_PARAM_LONGITUDINAL)) {
      ret = BUILD_SAFETY_CFG(ford_rx_checks, FORD_CANFD_LONG_TX_MSGS);
    }
#endif
  } else {
    ret = ford_new_port ? BUILD_SAFETY_CFG(ford_rx_checks, FORD_STOCK_TX_MSGS) :
                          BUILD_SAFETY_CFG(ford_rx_checks, FORD_LONG_TX_MSGS);
    if (ford_lka_steering) {
      SET_RX_CHECKS(ford_lka_rx_checks, ret);
    }
    if (ford_new_port && GET_FLAG(param, 1U)) {
      SET_TX_MSGS(FORD_LONG_TX_MSGS, ret);
    }
  }
  if (ford_explorer_extended && (param == 32U)) {
    SET_TX_MSGS(FORD_STOCK_TX_MSGS, ret);
  }
  if (ford_stock_switch) {
    if (ford_lka_steering) {
      SET_RX_CHECKS(ford_stock_lka_rx_checks, ret);
    } else {
      SET_RX_CHECKS(ford_stock_rx_checks, ret);
    }
  }
  if ((mach_e_namespace && !ford_mach_e_extended) ||
      (explorer_namespace && !ford_explorer_extended) ||
      (generic_canfd_namespace && !ford_generic_canfd_extended)) {
    ret.tx_msgs = NULL;
    ret.tx_msgs_len = 0;
  }
  ford_aol_configure(param);
  if (ford_aol_enabled) {
    static RxCheck ford_aol_default_rx[] = {
      FORD_COMMON_RX_CHECKS
      {.msg = {{0x83, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
      {.msg = {{0x82, 0, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
      {.msg = {{0x176, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    };
    static RxCheck ford_aol_edge_rx[] = {
      FORD_COMMON_RX_CHECKS
      {.msg = {{0x83, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
      {.msg = {{0x82, 0, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
      {.msg = {{0x230, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    };
    static RxCheck ford_aol_mondeo_rx[] = {
      FORD_COMMON_RX_CHECKS
      {.msg = {{FORD_Lane_Assist_Data3, 0, 8, 30U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
      {.msg = {{0x83, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
      {.msg = {{0x82, 0, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
      {.msg = {{0x5A, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    };
    static RxCheck ford_aol_transit_rx[] = {
      FORD_COMMON_RX_CHECKS
      {.msg = {{0x83, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
      {.msg = {{0x82, 0, 8, 50U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
      {.msg = {{0x176, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
      {.msg = {{FORD_Lane_Assist_Data3, 0, 8, 30U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    };
    const uint16_t base = param & 0xFFFEU;
    if (base == 8U) {
      SET_RX_CHECKS(ford_aol_edge_rx, ret);
    } else if (base == 10U) {
      SET_RX_CHECKS(ford_aol_mondeo_rx, ret);
    } else if ((base == 12U) || (base == 18U) || (base == 66U)) {
      SET_RX_CHECKS(ford_aol_transit_rx, ret);
    } else {
      SET_RX_CHECKS(ford_aol_default_rx, ret);
    }
    static CanMsg ford_aol_tx_msgs[16];
    const bool bounded = (ret.tx_msgs_len > 0) && (ret.tx_msgs_len <= 16);
    if (bounded) {
      for (int i = 0; i < ret.tx_msgs_len; i++) {
        ford_aol_tx_msgs[i] = ret.tx_msgs[i];
        const unsigned int addr = ford_aol_tx_msgs[i].addr;
        if ((addr == ford_aol_replacement()) || (addr == 0x3D8U) || (addr == 0x18AU)) {
          ford_aol_tx_msgs[i].disable_static_blocking = true;
        }
      }
      ret.tx_msgs = ford_aol_tx_msgs;
    } else {
      ret.tx_msgs = NULL;
      ret.tx_msgs_len = 0;
      ford_aol_reset();
    }
  }
  return ret;
}

const safety_hooks ford_hooks = {
  .fwd = ford_aol_fwd,
  .init = ford_init,
  .rx = ford_rx_hook,
  .tx = ford_tx_hook,
  .get_counter = ford_get_counter,
  .get_checksum = ford_get_checksum,
  .compute_checksum = ford_compute_checksum,
  .get_quality_flag_valid = ford_get_quality_flag_valid,
};
