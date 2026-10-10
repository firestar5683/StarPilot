#pragma once
// Angle-primary Ford extension adapted from Alan Polk's bp-7.0 e1d051d7.
// See ../CREDITS.md, ../LICENSE and ../LICENSE.md. No reset bypass.
#include "opendbc/bluepilot_lateral/params/protocol.h"
#include "opendbc/bluepilot_lateral/params/limits.h"

// Shared Ford stock-switch state is declared before the angle hooks below.
static bool ford_stock_switch = false;
static bool ford_bp_enabled = false;
static bool ford_bp_canfd = false;
static bool ford_bp_shadow_seen = false;
static bool ford_bp_lka_counter_seen = false;
static uint8_t ford_bp_lka_counter = 0U;
static int ford_bp_shadow_raw = 0;
static uint32_t ford_bp_shadow_us = 0U;
static int ford_bp_path_last = 0;
static bool ford_bp_control_counter_seen = false;
static uint8_t ford_bp_control_counter = 0U;
static bool ford_bp_control_seen = false;
static uint32_t ford_bp_control_us = 0U;
static float ford_bp_equivalent_last = 0.0F;
static unsigned int ford_bp_rt_msgs = 0U;
static unsigned int ford_bp_rt_msgs_prev = 0U;
static uint32_t ford_bp_rt_us = 0U;
static bool ford_bp_rx_seen[7];
static uint32_t ford_bp_rx_us[7];

static void ford_bp_invalidate_shadow(void) {
  ford_bp_shadow_seen = false;
  ford_bp_shadow_raw = 0;
}

static void ford_bp_withdraw(void) {
  ford_bp_invalidate_shadow();
  ford_bp_path_last = 0;
  ford_bp_equivalent_last = 0.0F;
}

static bool ford_bp_configure(uint16_t param) {
  ford_bp_enabled = ((param == 128U) || (param == 129U) || (param == 130U)) && (alternative_experience == 0);
#ifdef ALLOW_DEBUG
  ford_bp_enabled |= (param == 131U) && (alternative_experience == 0);
#endif
  ford_bp_canfd = (param & 2U) != 0U;
  ford_bp_lka_counter_seen = false;
  ford_bp_control_counter_seen = false;
  ford_bp_control_seen = false;
  ford_bp_lka_counter = 0U;
  ford_bp_control_counter = 0U;
  ford_bp_shadow_us = 0U;
  ford_bp_control_us = 0U;
  ford_bp_rt_msgs = 0U;
  ford_bp_rt_msgs_prev = 0U;
  ford_bp_rt_us = microsecond_timer_get();
  ford_bp_withdraw();
  for (unsigned int i = 0U; i < 7U; i++) {
    ford_bp_rx_seen[i] = false;
    ford_bp_rx_us[i] = 0U;
  }
  return ((param & 128U) == 0U) || ford_bp_enabled;
}

static bool ford_bp_health(uint32_t now);

static void ford_bp_rx(const CANPacket_t *msg) {
  if (ford_bp_enabled && (msg->bus == 0U) && (GET_LEN(msg) == 8U)) {
    const unsigned int ids[7] = {0x415U, 0x202U, 0x91U, 0x165U, 0x204U, 0x213U, 0x83U};
    for (unsigned int i = 0U; i < 7U; i++) {
      if (msg->addr == ids[i]) {
        ford_bp_rx_seen[i] = true;
        ford_bp_rx_us[i] = microsecond_timer_get();
      }
    }
    // Angle-specific source freshness is stricter than the generic1s RX tick.
    // Expose that withdrawal through the ordinary public controls acknowledgment.
    if (controls_allowed && !ford_bp_health(microsecond_timer_get())) {
      controls_allowed = false;
    }
    // Permission losses remove the old actuator history before any later arm.
    if (!controls_allowed || brake_pressed || gas_pressed) {
      ford_bp_withdraw();
    }
  }
}

static bool ford_bp_health(uint32_t now) {
  bool valid = !safety_rx_checks_invalid && !relay_malfunction;
  for (int i = 0; i < current_safety_config.rx_checks_len; i++) {
    const RxStatus *status = &current_safety_config.rx_checks[i].status;
    valid &= status->msg_seen && !status->lagging && status->valid_checksum &&
             status->valid_quality_flag && (status->wrong_counters < MAX_WRONG_COUNTERS);
  }
  const unsigned int count = ford_stock_switch ? 7U : 6U;
  for (unsigned int i = 0U; i < count; i++) {
    const uint32_t age = ((i == 3U) || (i == 6U)) ? (2U * FORD_BP_RX_AGE_US) : FORD_BP_RX_AGE_US;
    valid &= ford_bp_rx_seen[i] && (safety_get_ts_elapsed(now, ford_bp_rx_us[i]) <= age);
  }
  return valid;
}

static bool ford_bp_lka(const CANPacket_t *msg) {
  const uint32_t now = microsecond_timer_get();
  const unsigned int counter = (msg->data[4] & FORD_BP_COUNTER_MASK) >> FORD_BP_COUNTER_SHIFT;
  unsigned int sum = 0U;
  for (unsigned int i = 0U; i < 7U; i++) { sum += msg->data[i]; }
  const unsigned int checksum = (15U - (sum & 15U)) & 15U;
  // Preserve every DBC-owned bit of the packer's neutral LKA body.
  const unsigned int angle = ((msg->data[2] & 0xFU) << 8) | msg->data[3];
  const unsigned int curvature = (msg->data[1] << 4) | (msg->data[2] >> 4);
  bool valid = !relay_malfunction && (msg->bus == 0U) && (GET_LEN(msg) == 8U) && (msg->data[0] == 0U) &&
               (angle == 2048U) && (curvature == 2048U) &&
               ((msg->data[4] & 0xE3U) == FORD_BP_ANGLE_MASK) &&
               ((msg->data[7] & FORD_BP_VERSION_MASK) == FORD_BP_VERSION) &&
               ((msg->data[7] >> FORD_BP_CHECKSUM_SHIFT) == checksum);
  const int shadow = to_signed((msg->data[5] << 8) | msg->data[6], 16);
  const bool resync = (shadow == 0) && !controls_allowed;
  if (ford_bp_lka_counter_seen && !resync) {
    valid &= counter == ((ford_bp_lka_counter + 1U) % FORD_BP_COUNTER_MODULUS);
    valid &= safety_get_ts_elapsed(now, ford_bp_shadow_us) >= 20000U;
  }
  valid &= SAFETY_ABS(shadow) <= 20000;
  if (valid) {
    ford_bp_lka_counter = (uint8_t)counter;
    ford_bp_lka_counter_seen = true;
    ford_bp_shadow_raw = shadow;
    ford_bp_shadow_seen = !resync;
    ford_bp_shadow_us = now;
  } else {
    ford_bp_invalidate_shadow();
  }
  return valid;
}

static bool ford_bp_lateral(const CANPacket_t *msg) {
  const bool fd = msg->addr == 0x3D6U;
  const unsigned int mode = fd ? ((msg->data[0] >> 4) & 7U) : ((msg->data[4] >> 2) & 7U);
  const unsigned int curvature = fd ? ((msg->data[2] << 3) | (msg->data[3] >> 5)) :
                                     ((msg->data[0] << 3) | (msg->data[1] >> 5));
  const unsigned int rate = fd ? (((unsigned int)msg->data[6] << 3) | (msg->data[7] >> 5)) :
                                (((msg->data[1] & 31U) << 8) | msg->data[2]);
  const unsigned int path_raw = fd ? (((msg->data[3] & 31U) << 6) | (msg->data[4] >> 2)) :
                                    (((unsigned int)msg->data[3] << 3) | (msg->data[4] >> 5));
  const unsigned int offset = fd ? (((msg->data[4] & 3U) << 8) | msg->data[5]) :
                                  (((unsigned int)msg->data[5] << 2) | (msg->data[6] >> 6));
  const unsigned int precision = fd ? ((msg->data[0] >> 2) & 3U) : (msg->data[4] & 3U);
  const unsigned int ramp = fd ? (msg->data[0] & 3U) : ((msg->data[6] >> 4) & 3U);
  const bool active = mode == 1U;
  const int path = (int)path_raw - 1000;
  const uint32_t now = microsecond_timer_get();
  bool valid = !relay_malfunction && (msg->bus == 0U) && (GET_LEN(msg) == 8U) && (fd == ford_bp_canfd) && (mode <= 1U) &&
               (curvature == 1000U) && (rate == (fd ? 1024U : 4096U)) && (offset == 512U) &&
               (precision <= 1U) && (ramp == (active ? 2U : 0U));
  const unsigned int counter = (msg->data[7] >> 1) & 15U;
  if (fd) {
    unsigned int checksum = mode + counter;
    const unsigned int fields[4] = {curvature, rate, path_raw, offset};
    for (unsigned int i = 0U; i < 4U; i++) { checksum += fields[i] + (fields[i] >> 8); }
    valid &= msg->data[1] == (0xFFU - (checksum & 0xFFU));
    valid &= ((msg->data[0] & 0x80U) == 0U) && ((msg->data[7] & 1U) == 0U);
    if (ford_bp_control_counter_seen && active) { valid &= counter == ((ford_bp_control_counter + 1U) % 16U); }
  } else {
    valid &= ((msg->data[6] & 0xFU) == 0U) && (msg->data[7] == 0U);
  }
  const float speed_for_equivalent = SAFETY_MAX(vehicle_speed.min / VEHICLE_SPEED_FACTOR, 0.1F);
  const float equivalent = (float)path / (2000.0F * speed_for_equivalent);
  // Time-window expiration is independent of packet acceptance: denied floods
  // cannot latch the old count forever or erase accepted actuator history.
  const uint32_t rt_elapsed = safety_get_ts_elapsed(now, ford_bp_rt_us);
  if (rt_elapsed >= FORD_BP_RT_INTERVAL_US) {
    ford_bp_rt_msgs = 0U;
    ford_bp_rt_msgs_prev = 0U;
    ford_bp_rt_us = now;
  } else if (rt_elapsed >= (FORD_BP_RT_INTERVAL_US / 2U)) {
    ford_bp_rt_msgs_prev = ford_bp_rt_msgs;
    ford_bp_rt_msgs = 0U;
    ford_bp_rt_us = now;
  } else {
    // Keep the current history while neither expiration boundary has elapsed.
  }
  const unsigned int rt_count = ford_bp_rt_msgs + ford_bp_rt_msgs_prev;
  valid &= rt_count <= 7U;  // Current20Hz curvature RT allowance; accepted frames own this count.
  if (active) {
    static const struct lookup_t roc = {{10.0F, 15.0F, 25.0F}, {0.0561F, 0.04335F, 0.00918F}};
    const float speed_min = SAFETY_MAX(vehicle_speed.min / VEHICLE_SPEED_FACTOR, 0.1F);
    const float speed_max = SAFETY_MAX(vehicle_speed.max / VEHICLE_SPEED_FACTOR, 0.1F);
    const float delta_float = safety_interpolate(roc, speed_min - 1.0F) * 2000.0F;
    const int delta = (int)delta_float + 1;
    const float shadow = (float)ford_bp_shadow_raw * 0.000001F;
    const float shadow_can = shadow * 50000.0F;
    const float path_abs = SAFETY_ABS(path) / 2000.0F;
    const float path_curvature_low = path_abs / (speed_max * FORD_BP_GAIN_MAX);
    const float path_curvature_high = path_abs / (speed_min * FORD_BP_GAIN_MIN);
    const float physical_cap = SAFETY_MIN(FORD_BP_CURVATURE_MAX, FORD_BP_LATERAL_ACCEL / (SAFETY_MAX(speed_max, 1.0F) * SAFETY_MAX(speed_max, 1.0F)));
    const float relation_low = SAFETY_ABS(shadow) * speed_min * FORD_BP_GAIN_MIN * 2000.0F;
    const float relation_high = SAFETY_ABS(shadow) * speed_max * FORD_BP_GAIN_MAX * 2000.0F;
    valid &= lateral_controls_allowed() && controls_allowed && ford_bp_health(now) && ford_bp_shadow_seen &&
             (safety_get_ts_elapsed(now, ford_bp_shadow_us) <= FORD_BP_SHADOW_AGE_US) &&
             (path >= -1000) && (path <= 1047) && (SAFETY_ABS(path - ford_bp_path_last) <= delta) &&
             ((path == 0) || ((ford_bp_shadow_raw != 0) && ((path > 0) == (ford_bp_shadow_raw > 0)))) &&
             (SAFETY_ABS(path) >= (relation_low - 2.0F)) && (SAFETY_ABS(path) <= (relation_high + 2.0F)) &&
             (SAFETY_ABS(shadow) <= (physical_cap + FORD_BP_SHADOW_ROUNDING_MARGIN)) && (path_curvature_high <= (physical_cap + FORD_BP_SHADOW_ROUNDING_MARGIN));
    if (speed_max > 10.0F) {
      const int measured_min = curvature_state.meas.min - 100;
      const int measured_max = curvature_state.meas.max + 100;
      const float measured_min_float = (float)measured_min;
      const float measured_max_float = (float)measured_max;
      valid &= (shadow_can >= measured_min_float) && (shadow_can <= measured_max_float);
      // Independent actual-actuator check; an invented shadow cannot launder path angle.
      const float signed_low = (path < 0) ? (-path_curvature_high) : path_curvature_low;
      const float signed_high = (path < 0) ? (-path_curvature_low) : path_curvature_high;
      valid &= ((signed_low * 50000.0F) >= measured_min_float) &&
               ((signed_high * 50000.0F) <= measured_max_float);
    }
    const uint32_t elapsed = ford_bp_control_seen ? safety_get_ts_elapsed(now, ford_bp_control_us) : FORD_BP_STEER_PERIOD_US;
    const float jerk_speed = SAFETY_MAX(speed_min - 1.0F, 1.0F);
    const float jerk_delta = FORD_BP_LATERAL_JERK / (jerk_speed * jerk_speed) *
                             (SAFETY_MIN(elapsed, FORD_BP_STEER_PERIOD_US) * 0.000001F) * FORD_BP_GAIN_MIN;
    valid &= SAFETY_ABS(equivalent - ford_bp_equivalent_last) <= (jerk_delta + FORD_BP_SHADOW_ROUNDING_MARGIN);
    if (ford_bp_control_seen) { valid &= elapsed >= 40000U; }
  } else {
    valid &= path == 0;
  }
  if (valid) {
    ford_bp_rt_msgs += 1U;
    ford_bp_equivalent_last = active ? equivalent : 0.0F;
    ford_bp_path_last = active ? path : 0;
    ford_bp_control_counter = (uint8_t)counter;
    ford_bp_control_counter_seen = true;
    ford_bp_control_seen = true;
    ford_bp_control_us = now;
    if (!active) { ford_bp_shadow_seen = false; }
  } else {
    ford_bp_invalidate_shadow();
  }
  return valid;
}
