#pragma once

#include "opendbc/safety/declarations.h"

// TODO: do checksum and counter checks. Add correct timestep, 0.1s for now.
#define GM_COMMON_RX_CHECKS \
    {.msg = {{0x184, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}}, \
    {.msg = {{0x34A, 0, 5, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}}, \
    {.msg = {{0x1E1, 0, 7, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}}, \
    /* OPGM Variables */                                                                                                       \
    {.msg = {{0x1C4, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}}, \
    {.msg = {{0xC9, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}}, \

#define GM_ACC_RX_CHECKS \
    {.msg = {{0xBE, 0, 6, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true},    /* Volt, Silverado, Acadia Denali */ \
             {0xBE, 0, 7, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true},    /* Bolt EUV */ \
             {0xBE, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}}},  /* Escalade */ \

static const LongitudinalLimits *gm_long_limits;
static const TorqueSteeringLimits *gm_steer_limits;

static const TorqueSteeringLimits GM_STEERING_LIMITS = {
  .max_torque = 300,
  .max_rate_up = 10,
  .max_rate_down = 15,
  .driver_torque_allowance = 65,
  .driver_torque_multiplier = 4,
  .max_rt_delta = 128,
  .type = TorqueDriverLimited,
};

static const TorqueSteeringLimits GM_BOLT_2017_STEERING_LIMITS = {
  .max_torque = 450,
  .max_rate_up = 15,
  .max_rate_down = 34,
  .driver_torque_allowance = 78,
  .driver_torque_multiplier = 6,
  .max_rt_delta = 345,
  .type = TorqueDriverLimited,
};

enum {
  GM_BTN_UNPRESS = 1,
  GM_BTN_RESUME = 2,
  GM_BTN_SET = 3,
  GM_BTN_CANCEL = 6,
};

typedef enum {
  GM_ASCM,
  GM_CAM
} GmHardware;
static GmHardware gm_hw = GM_ASCM;
static bool gm_cam_long = false;
static bool gm_pcm_cruise = false;
static bool gm_sdgm = false;
static bool gm_ascm_int = false;
static bool gm_force_ascm = false;
static bool gm_force_brake_c9 = false;
static bool gm_panda_3d1_sched = false;
static bool gm_panda_paddle_sched = false;
static bool gm_bolt_2022_pedal = false;

// OPGM variables
static bool gm_cc_long = false;
static bool gm_has_acc = true;
static bool gm_pedal_long = false;

// StarPilot parity scheduler state
static bool gm_3d1_spoof_valid = false;
static bool gm_3d1_internal_tx = false;
static uint8_t gm_3d1_spoof_data[8] = {0U};
static uint32_t gm_3d1_next_tx_us = 0U;
static uint32_t gm_3d1_expected_stock_us = 0U;
static uint32_t gm_3d1_last_stock_us = 0U;
static bool gm_3d1_phase_locked = false;
static bool gm_paddle_internal_tx = false;

typedef struct {
  bool spoof_valid;
  uint8_t spoof_data[8];
  uint32_t next_tx_us;
  uint32_t expected_stock_us;
  uint32_t last_stock_us;
  uint32_t last_feed_us;
  bool phase_locked;
} GmPeriodicSpoofState;

static GmPeriodicSpoofState gm_bd_state = {0};
static GmPeriodicSpoofState gm_prndl2_state = {0};

static const uint32_t GM_3D1_PERIOD_US = 100000U;
static const uint32_t GM_3D1_TX_OFFSET_US = 0U;
static const uint32_t GM_3D1_LOCK_TOLERANCE_US = 20000U;
static const uint32_t GM_PADDLE_PERIOD_US = 25000U;
static const uint32_t GM_PADDLE_TX_OFFSET_US = 0U;
static const uint32_t GM_PADDLE_LOCK_TOLERANCE_US = 5000U;
static const uint32_t GM_PADDLE_STALE_US = 100000U;
static const uint32_t GM_PADDLE_FEED_STALE_US = 100000U;

void can_send(CANPacket_t *to_push, uint8_t bus_number, bool skip_tx_hook);
void can_set_checksum(CANPacket_t *packet);

static void gm_copy_u8(uint8_t *dst, const uint8_t *src, uint8_t len) {
  for (uint8_t i = 0U; i < len; i++) {
    dst[i] = src[i];
  }
}

static void gm_zero_u8(uint8_t *dst, uint8_t len) {
  for (uint8_t i = 0U; i < len; i++) {
    dst[i] = 0U;
  }
}

static void gm_update_periodic_phase(GmPeriodicSpoofState *state, uint32_t now_us, uint32_t period_us, uint32_t lock_tolerance_us) {
  state->last_stock_us = now_us;
  if (!state->phase_locked) {
    state->phase_locked = true;
    state->expected_stock_us = now_us + period_us;
  } else {
    int32_t phase_err_us = (int32_t)(now_us - state->expected_stock_us);
    if (phase_err_us < 0) {
      phase_err_us = -phase_err_us;
    }

    if ((uint32_t)phase_err_us <= lock_tolerance_us) {
      state->expected_stock_us += period_us;
    } else {
      state->expected_stock_us = now_us + period_us;
    }
  }
}

static bool gm_periodic_scheduler_ready(const GmPeriodicSpoofState *state, uint32_t now_us, uint32_t stale_us, uint32_t feed_stale_us) {
  bool stock_stale = (state->last_stock_us == 0U) || (safety_get_ts_elapsed(now_us, state->last_stock_us) > stale_us);
  bool feed_stale = (state->last_feed_us == 0U) || (safety_get_ts_elapsed(now_us, state->last_feed_us) > feed_stale_us);
  return state->phase_locked && !stock_stale && !feed_stale;
}

static bool gm_3d1_scheduler_ready(uint32_t now_us) {
  bool stock_stale = (gm_3d1_last_stock_us == 0U) || (safety_get_ts_elapsed(now_us, gm_3d1_last_stock_us) > 300000U);
  return gm_3d1_phase_locked && !stock_stale;
}

static void gm_try_send_periodic_spoof(uint32_t now_us, uint32_t addr, uint8_t dlc, GmPeriodicSpoofState *state, uint32_t period_us) {
  if (!(gm_panda_paddle_sched && state->spoof_valid && (state->next_tx_us != 0U))) {
    return;
  }

  if (!gm_periodic_scheduler_ready(state, now_us, GM_PADDLE_STALE_US, GM_PADDLE_FEED_STALE_US)) {
    return;
  }

  if ((int32_t)(now_us - state->next_tx_us) < 0) {
    return;
  }

  CANPacket_t to_send = {0};
  to_send.returned = 0U;
  to_send.rejected = 0U;
  to_send.extended = 0U;
  to_send.fd = 0U;
  to_send.addr = addr;
  to_send.bus = 0U;
  to_send.data_len_code = dlc;
  gm_copy_u8(to_send.data, state->spoof_data, 8U);
  can_set_checksum(&to_send);

  gm_paddle_internal_tx = true;
  can_send(&to_send, 0U, false);
  gm_paddle_internal_tx = false;

  state->next_tx_us += period_us;
}

static void gm_try_send_3d1_spoof(uint32_t now_us) {
  if (!(gm_panda_3d1_sched && gm_3d1_spoof_valid && (gm_3d1_next_tx_us != 0U))) {
    return;
  }

  if ((int32_t)(now_us - gm_3d1_next_tx_us) < 0) {
    return;
  }

  CANPacket_t to_send = {0};
  to_send.returned = 0U;
  to_send.rejected = 0U;
  to_send.extended = 0U;
  to_send.fd = 0U;
  to_send.addr = 0x3D1U;
  to_send.bus = 0U;
  to_send.data_len_code = 8U;
  gm_copy_u8(to_send.data, gm_3d1_spoof_data, 8U);
  can_set_checksum(&to_send);

  gm_3d1_internal_tx = true;
  can_send(&to_send, 0U, false);
  gm_3d1_internal_tx = false;

  gm_3d1_next_tx_us += GM_3D1_PERIOD_US;
}

static void gm_rx_hook(const CANPacket_t *msg) {
  const int GM_STANDSTILL_THRSLD = 10;  // 0.311kph

  // OPGM variables
  // Keep panda threshold aligned with carstate to avoid pedal pre-enable mismatches.
  const int GM_GAS_INTERCEPTOR_THRESHOLD = 595;

  if (msg->bus == 0U) {
    if (msg->addr == 0x184U) {
      int torque_driver_new = ((msg->data[6] & 0x7U) << 8) | msg->data[7];
      torque_driver_new = to_signed(torque_driver_new, 11);
      // update array of samples
      update_sample(&torque_driver, torque_driver_new);
    }

    // sample rear wheel speeds
    if (msg->addr == 0x34AU) {
      int left_rear_speed = (msg->data[0] << 8) | msg->data[1];
      int right_rear_speed = (msg->data[2] << 8) | msg->data[3];
      vehicle_moving = (left_rear_speed > GM_STANDSTILL_THRSLD) || (right_rear_speed > GM_STANDSTILL_THRSLD);
    }

    // ACC steering wheel buttons (GM_CAM is tied to the PCM)
    if ((msg->addr == 0x1E1U) && (!gm_pcm_cruise || gm_cc_long)) {
      int button = (msg->data[5] & 0x70U) >> 4;
      bool remap_cancel_to_distance = (alternative_experience & ALT_EXP_GM_REMAP_CANCEL_TO_DISTANCE) != 0;
      // Malibu Hybrid pedal-long frames use byte3 bit0 in combinations that can alias
      // CANCEL semantics; don't force a safety disengage on those RX edges.
      bool malibu_cancel_passthrough = remap_cancel_to_distance && gm_bolt_2022_pedal && gm_pedal_long && ((msg->data[3] & 0x1U) != 0U);
      // Gen1 Bolt pedal-long uses CANCEL as an auxiliary input path.
      bool bolt_cancel_passthrough = remap_cancel_to_distance && gm_pedal_long && !gm_has_acc && !gm_bolt_2022_pedal;

      // enter controls on falling edge of set or rising edge of resume (avoids fault)
      bool set = (button != GM_BTN_SET) && (cruise_button_prev == GM_BTN_SET);
      bool res = (button == GM_BTN_RESUME) && (cruise_button_prev != GM_BTN_RESUME);
      if (set || res) {
        controls_allowed = true;
      }

      // exit controls on cancel press
      if ((button == GM_BTN_CANCEL) && !(malibu_cancel_passthrough || bolt_cancel_passthrough)) {
        controls_allowed = false;
      }

      cruise_button_prev = button;
    }

    // Reference for brake pressed signals:
    // https://github.com/commaai/openpilot/blob/master/selfdrive/car/gm/carstate.py
    if ((msg->addr == 0xC9U) && gm_force_brake_c9) {
      brake_pressed = GET_BIT(msg, 40U);
    }

    if ((msg->addr == 0xBEU) && ((gm_hw == GM_ASCM) || gm_sdgm || gm_ascm_int)) {
      brake_pressed = msg->data[1] >= 8U;
    }

    if ((msg->addr == 0xC9U) && (gm_hw == GM_CAM) && !gm_force_brake_c9) {
      brake_pressed = GET_BIT(msg, 40U);
    }

    if (msg->addr == 0x1C4U) {
      // Pedal-long cars should not gate longitudinal on stock accelerator position.
      if (!enable_gas_interceptor && !gm_pedal_long) {
        gas_pressed = msg->data[5] != 0U;
      }

      // enter controls on rising edge of ACC, exit controls when ACC off
      if (gm_pcm_cruise && gm_has_acc) {
        bool cruise_engaged = (msg->data[1] >> 5) != 0U;
        pcm_cruise_check(cruise_engaged);
      }
    }

    // CC-only Bolt 2022/23 pedal path blocks stock ACC state.
    if ((msg->addr == 0x1C4U) && gm_has_acc && enable_gas_interceptor && gm_bolt_2022_pedal) {
      cruise_engaged_prev = false;
    }

    // OPGM variables
    // Cruise check for CC only cars
    if ((msg->addr == 0x3D1U) && !gm_has_acc) {
      uint32_t now_us = microsecond_timer_get();
      gm_3d1_last_stock_us = now_us;
      bool cruise_engaged = (msg->data[4] >> 7) != 0U;
      if (gm_cc_long) {
        pcm_cruise_check(cruise_engaged);
      } else {
        cruise_engaged_prev = cruise_engaged;
      }

      if (gm_panda_3d1_sched) {
        if (!gm_3d1_phase_locked) {
          gm_3d1_phase_locked = true;
          gm_3d1_expected_stock_us = now_us + GM_3D1_PERIOD_US;
        } else {
          int32_t phase_err_us = (int32_t)(now_us - gm_3d1_expected_stock_us);
          if (phase_err_us < 0) {
            phase_err_us = -phase_err_us;
          }

          if ((uint32_t)phase_err_us <= GM_3D1_LOCK_TOLERANCE_US) {
            gm_3d1_expected_stock_us += GM_3D1_PERIOD_US;
          } else {
            gm_3d1_expected_stock_us = now_us + GM_3D1_PERIOD_US;
          }
        }

        gm_3d1_next_tx_us = now_us + GM_3D1_TX_OFFSET_US;
        gm_try_send_3d1_spoof(now_us);
      }
    }

    if (msg->addr == 0xBDU) {
      regen_braking = (msg->data[0] >> 4) != 0U;

      if (gm_panda_paddle_sched) {
        uint32_t now_us = microsecond_timer_get();
        gm_update_periodic_phase(&gm_bd_state, now_us, GM_PADDLE_PERIOD_US, GM_PADDLE_LOCK_TOLERANCE_US);
        gm_bd_state.next_tx_us = now_us + GM_PADDLE_TX_OFFSET_US;
        gm_try_send_periodic_spoof(now_us, 0xBDU, 7U, &gm_bd_state, GM_PADDLE_PERIOD_US);
      }
    }

    if ((msg->addr == 0x1F5U) && gm_panda_paddle_sched) {
      uint32_t now_us = microsecond_timer_get();
      gm_update_periodic_phase(&gm_prndl2_state, now_us, GM_PADDLE_PERIOD_US, GM_PADDLE_LOCK_TOLERANCE_US);
      gm_prndl2_state.next_tx_us = now_us + GM_PADDLE_TX_OFFSET_US;
      gm_try_send_periodic_spoof(now_us, 0x1F5U, 8U, &gm_prndl2_state, GM_PADDLE_PERIOD_US);
    }

    // Pedal Interceptor
    if ((msg->addr == 0x201U) && enable_gas_interceptor) {
      // Pedal Interceptor: average between 2 tracks
      int track1 = ((msg->data[0] << 8) + msg->data[1]);
      int track2 = ((msg->data[2] << 8) + msg->data[3]);
      int gas_interceptor = (track1 + track2) / 2;
      gas_pressed = gas_interceptor > GM_GAS_INTERCEPTOR_THRESHOLD;
      gas_interceptor_prev = gas_interceptor;
    }
  }

  // Keep camera-bus ACC status behavior aligned with StarPilot camera/SDGM paths.
  if ((msg->addr == 0x370U) && (msg->bus == 2U)) {
    bool cruise_engaged = (msg->data[2] >> 7) != 0U;  // ACCCmdActive
    if (gm_bolt_2022_pedal) {
      cruise_engaged_prev = cruise_engaged;
    } else if (gm_pcm_cruise && gm_has_acc) {
      pcm_cruise_check(cruise_engaged);
    } else {
      cruise_engaged_prev = cruise_engaged;
    }
  }

  // FrogPilot variables
  if (msg->addr == 0xC9U) {
    acc_main_on = GET_BIT(msg, 29U);
  }
}

static bool gm_tx_hook(const CANPacket_t *msg) {
  bool tx = true;

  // BRAKE: safety check
  if (msg->addr == 0x315U) {
    int brake = ((msg->data[0] & 0xFU) << 8) + msg->data[1];
    brake = (0x1000 - brake) & 0xFFF;
    if (longitudinal_brake_checks(brake, *gm_long_limits)) {
      tx = false;
    }
  }

  // LKA STEER: safety check
  if (msg->addr == 0x180U) {
    int desired_torque = ((msg->data[0] & 0x7U) << 8) + msg->data[1];
    desired_torque = to_signed(desired_torque, 11);

    bool steer_req = GET_BIT(msg, 3U);

    if (steer_torque_cmd_checks(desired_torque, steer_req, *gm_steer_limits)) {
      tx = false;
    }
  }

  // GAS/REGEN: safety check
  if (msg->addr == 0x2CBU) {
    bool apply = GET_BIT(msg, 0U);
    // convert float CAN signal to an int for gas checks: 22534 / 0.125 = 180272
    int gas_regen = (((msg->data[1] & 0x7U) << 16) | (msg->data[2] << 8) | msg->data[3]) - 180272U;

    bool violation = false;
    // Allow apply bit in pre-enabled and overriding states
    violation |= !controls_allowed && apply;
    violation |= longitudinal_gas_checks(gas_regen, *gm_long_limits);

    if (violation) {
      tx = false;
    }
  }

  // BUTTONS: used for resume spamming and cruise cancellation with stock longitudinal
  if ((msg->addr == 0x1E1U) && (gm_pcm_cruise || gm_pedal_long || gm_cc_long)) {
    int button = (msg->data[5] >> 4) & 0x7U;

    bool allowed_btn = (button == GM_BTN_CANCEL) && cruise_engaged_prev;
    // Pedal-long non-ACC path: once OP controls are taken over, allow cancel spam
    // immediately even if cruise_engaged_prev has not flipped yet.
    if ((button == GM_BTN_CANCEL) && gm_pedal_long && !gm_has_acc && controls_allowed) {
      allowed_btn = true;
    }
    if (gm_hw == GM_CAM && enable_gas_interceptor && gm_bolt_2022_pedal && button == GM_BTN_CANCEL) {
      allowed_btn = true;
    }
    // For standard CC and PCM cruise paths, allow spamming of SET / RESUME
    if (gm_cc_long || gm_pcm_cruise) {
      allowed_btn |= cruise_engaged_prev && ((button == GM_BTN_SET) || (button == GM_BTN_RESUME) || (button == GM_BTN_UNPRESS));
    }

    if (!allowed_btn) {
      tx = false;
    }
  }

  // Cruise status spoofing only for non-ACC (CC-only) paths.
  if (msg->addr == 0x3D1U) {
    bool allowed_cruise_status = !gm_has_acc;
    if (!allowed_cruise_status) {
      tx = false;
    } else if (gm_panda_3d1_sched) {
      if (gm_3d1_internal_tx) {
        tx = true;
      } else {
        uint32_t now_us = microsecond_timer_get();
        gm_copy_u8(gm_3d1_spoof_data, msg->data, 8U);
        gm_3d1_spoof_valid = true;
        if (gm_3d1_next_tx_us == 0U) {
          gm_3d1_next_tx_us = now_us + GM_3D1_TX_OFFSET_US;
        }
        bool scheduler_ready = gm_3d1_scheduler_ready(now_us);
        tx = !scheduler_ready;
      }
    }
  }

  // OPGM variables
  // GAS: safety check (interceptor)
  if (msg->addr == 0x200U) {
    if (longitudinal_interceptor_checks(msg)) {
      tx = false;
    }
  }

  // Regen paddle command must obey controls state
  if (msg->addr == 0xBDU) {
    bool regen_apply = GET_BIT(msg, 7U) || GET_BIT(msg, 6U) || GET_BIT(msg, 5U) || GET_BIT(msg, 4U);
    if (!controls_allowed && regen_apply) {
      tx = false;
    }

    if (gm_panda_paddle_sched && !gm_paddle_internal_tx) {
      uint32_t now_us = microsecond_timer_get();
      if (tx) {
        gm_copy_u8(gm_bd_state.spoof_data, msg->data, 7U);
        gm_bd_state.spoof_data[7] = 0U;
        gm_bd_state.spoof_valid = true;
        gm_bd_state.last_feed_us = now_us;
        if (gm_bd_state.next_tx_us == 0U) {
          gm_bd_state.next_tx_us = now_us + GM_PADDLE_TX_OFFSET_US;
        }
      }
      bool scheduler_ready = gm_periodic_scheduler_ready(&gm_bd_state, now_us, GM_PADDLE_STALE_US, GM_PADDLE_FEED_STALE_US);
      if (scheduler_ready) {
        tx = false;
      }
    }
  }

  // PRNDL2 regen spoof command must obey controls state
  if (msg->addr == 0x1F5U) {
    uint8_t prndl2 = msg->data[3] & 0xFU;
    bool prndl_apply = (prndl2 == 7U) || (prndl2 == 5U);
    if (!controls_allowed && prndl_apply) {
      tx = false;
    }

    if (gm_panda_paddle_sched && !gm_paddle_internal_tx) {
      uint32_t now_us = microsecond_timer_get();
      if (tx) {
        gm_copy_u8(gm_prndl2_state.spoof_data, msg->data, 8U);
        gm_prndl2_state.spoof_valid = true;
        gm_prndl2_state.last_feed_us = now_us;
        if (gm_prndl2_state.next_tx_us == 0U) {
          gm_prndl2_state.next_tx_us = now_us + GM_PADDLE_TX_OFFSET_US;
        }
      }
      bool scheduler_ready = gm_periodic_scheduler_ready(&gm_prndl2_state, now_us, GM_PADDLE_STALE_US, GM_PADDLE_FEED_STALE_US);
      if (scheduler_ready) {
        tx = false;
      }
    }
  }

  return tx;
}

static bool gm_fwd_hook(int bus_num, int addr) {
  bool block_msg = false;

  if ((gm_hw == GM_CAM) || gm_sdgm) {
    if (bus_num == 0) {
      bool is_pscm_msg = addr == 0x184U;
      // Keep the camera side sourced only from OP's spoofed cruise status on non-ACC paths.
      bool is_ecm_cruise_status_msg = (addr == 0x3D1U) && !gm_has_acc;
      block_msg = is_pscm_msg || is_ecm_cruise_status_msg;
    } else if (bus_num == 2) {
      bool is_lkas_msg = addr == 0x180U;
      bool is_acc_status_msg = addr == 0x370U;
      bool is_acc_actuation_msg = (addr == 0x315U) || (addr == 0x2CBU);

      block_msg = is_lkas_msg;
      if (gm_cam_long || gm_pedal_long) {
        block_msg |= is_acc_status_msg;
      }
      if (gm_cam_long) {
        block_msg |= is_acc_actuation_msg;
      }
    }
  }

  return block_msg;
}

static safety_config gm_init(uint16_t param) {
  const uint16_t GM_PARAM_HW_CAM = 1;
  const uint16_t GM_PARAM_HW_CAM_LONG = 2;
  const uint16_t GM_PARAM_EV = 4;
  const uint16_t GM_PARAM_CC_LONG = 8;
  const uint16_t GM_PARAM_PEDAL_INTERCEPTOR = 16;
  const uint16_t GM_PARAM_NO_ACC = 32;
  const uint16_t GM_PARAM_PEDAL_LONG = 64;
  const uint16_t GM_PARAM_HW_ASCM_LONG = 128;
  const uint16_t GM_PARAM_HW_ASCM_INT = 256;
  const uint16_t GM_PARAM_FORCE_BRAKE_C9 = 512;
  const uint16_t GM_PARAM_HW_SDGM = 1024;
  const uint16_t GM_PARAM_BOLT_2017 = 2048;
  const uint16_t GM_PARAM_BOLT_2022_PEDAL = 4096;
  const uint16_t GM_PARAM_REMOTE_START_BOOTS_COMMA = 8192;
  const uint16_t GM_PARAM_PANDA_3D1_SCHED = 16384;
  const uint16_t GM_PARAM_PANDA_PADDLE_SCHED = 32768;

  // common safety checks assume unscaled integer values
  static const int GM_GAS_TO_CAN = 8;  // 1 / 0.125

  static const LongitudinalLimits GM_ASCM_LONG_LIMITS = {
    .max_gas = 1018 * GM_GAS_TO_CAN,
    .min_gas = -650 * GM_GAS_TO_CAN,
    .inactive_gas = -650 * GM_GAS_TO_CAN,
    .max_brake = 400,
  };

  static const CanMsg GM_ASCM_TX_MSGS[] = {{0x180, 0, 4, .check_relay = true}, {0x409, 0, 7, .check_relay = false}, {0x40A, 0, 7, .check_relay = false}, {0x2CB, 0, 8, .check_relay = true}, {0x370, 0, 6, .check_relay = false},  // pt bus
                                           {0xA1, 1, 7, .check_relay = false}, {0x306, 1, 8, .check_relay = false}, {0x308, 1, 7, .check_relay = false}, {0x310, 1, 2, .check_relay = false},   // obs bus
                                           {0x315, 2, 5, .check_relay = false},  // ch bus
                                           // OPGM Variables
                                           {0x200, 0, 6, .check_relay = false},
                                           {0x1E1, 0, 7, .check_relay = false},
                                           {0xBD, 0, 7, .check_relay = false},
                                           {0x1F5, 0, 8, .check_relay = false}}; // pt bus


  static const LongitudinalLimits GM_CAM_LONG_LIMITS = {
    .max_gas = 1346 * GM_GAS_TO_CAN,
    .min_gas = -540 * GM_GAS_TO_CAN,
    .inactive_gas = -500 * GM_GAS_TO_CAN,
    .max_brake = 400,
  };

  // block PSCMStatus (0x184); forwarded through openpilot to hide an alert from the camera
  static const CanMsg GM_CAM_LONG_TX_MSGS[] = {{0x180, 0, 4, .check_relay = true}, {0x315, 0, 5, .check_relay = true}, {0x2CB, 0, 8, .check_relay = true}, {0x370, 0, 6, .check_relay = true}, {0x3D1, 0, 8, .check_relay = false},  // pt bus
                                               {0x184, 2, 8, .check_relay = true},  // camera bus
                                               // OPGM Variables
                                               {0x200, 0, 6, .check_relay = false}, {0x1E1, 0, 7, .check_relay = false},
                                               {0xBD, 0, 7, .check_relay = false}, {0x1F5, 0, 8, .check_relay = false}};  // pt bus


  static RxCheck gm_rx_checks[] = {
    GM_COMMON_RX_CHECKS

    // OPGM Variables
    GM_ACC_RX_CHECKS
  };

  static RxCheck gm_ev_rx_checks[] = {
    GM_COMMON_RX_CHECKS
    {.msg = {{0xBD, 0, 7, 40U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},

    // OPGM Variables
    GM_ACC_RX_CHECKS
  };

  static RxCheck gm_ascm_int_stock_cam_rx_checks[] = {
    GM_COMMON_RX_CHECKS
    {.msg = {{0xF1, 0, 6, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
  };

  static const CanMsg GM_CAM_TX_MSGS[] = {{0x180, 0, 4, .check_relay = true}, {0x370, 0, 6, .check_relay = false}, {0x3D1, 0, 8, .check_relay = false},  // pt bus
                                          {0x1E1, 2, 7, .check_relay = false}, {0x184, 2, 8, .check_relay = true},  // camera bus
                                          // OPGM Variables
                                          {0x200, 0, 6, .check_relay = false},
                                          {0x1E1, 0, 7, .check_relay = false},
                                          {0xBD, 0, 7, .check_relay = false}, {0x1F5, 0, 8, .check_relay = false}};  // pt bus

  // OPGM Variables
  static RxCheck gm_no_acc_ev_rx_checks[] = {
    GM_COMMON_RX_CHECKS
    {.msg = {{0xBD, 0, 7, 40U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
    {.msg = {{0x3D1, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},  // Non-ACC PCM
  };

  static RxCheck gm_no_acc_rx_checks[] = {
    GM_COMMON_RX_CHECKS
    {.msg = {{0x3D1, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},  // Non-ACC PCM
  };

  static RxCheck gm_pedal_rx_checks[] = {
    GM_COMMON_RX_CHECKS
    {.msg = {{0xBD, 0, 7, 40U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
    {.msg = {{0x3D1, 0, 8, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},  // Non-ACC PCM
    {.msg = {{0x201, 0, 6, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},  // pedal
  };

  static RxCheck gm_cam_acc_rx_checks[] = {
    GM_COMMON_RX_CHECKS
    GM_ACC_RX_CHECKS
    {.msg = {{0x370, 2, 6, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},  // camera ACC status
  };

  static RxCheck gm_cam_acc_pedal_rx_checks[] = {
    GM_COMMON_RX_CHECKS
    GM_ACC_RX_CHECKS
    {.msg = {{0xBD, 0, 7, 40U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},
    {.msg = {{0x201, 0, 6, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},  // pedal
    {.msg = {{0x370, 2, 6, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, { 0 }, { 0 }}},  // camera ACC status
  };

  static const CanMsg GM_CC_LONG_TX_MSGS[] = {{0x180, 0, 4, .check_relay = true}, {0x370, 0, 6, .check_relay = false}, {0x1E1, 0, 7, .check_relay = false}, {0x3D1, 0, 8, .check_relay = false},  // pt bus
                                              {0xBD, 0, 7, .check_relay = false}, {0x1F5, 0, 8, .check_relay = false},
                                              {0x184, 2, 8, .check_relay = true}, {0x1E1, 2, 7, .check_relay = false}};  // camera bus

  gm_hw = GET_FLAG(param, GM_PARAM_HW_CAM) ? GM_CAM : GM_ASCM;
  gm_sdgm = GET_FLAG(param, GM_PARAM_HW_SDGM);
  gm_ascm_int = GET_FLAG(param, GM_PARAM_HW_ASCM_INT);

  // OPGM Variables
  gm_cc_long = GET_FLAG(param, GM_PARAM_CC_LONG);
  gm_has_acc = !GET_FLAG(param, GM_PARAM_NO_ACC);
  gm_pedal_long = GET_FLAG(param, GM_PARAM_PEDAL_LONG);
  // Keep pedal-long behavior robust even if only PEDAL_LONG is present during transitions.
  enable_gas_interceptor = GET_FLAG(param, GM_PARAM_PEDAL_INTERCEPTOR) || gm_pedal_long;
  gm_force_ascm = GET_FLAG(param, GM_PARAM_HW_ASCM_LONG);
  gm_force_brake_c9 = GET_FLAG(param, GM_PARAM_FORCE_BRAKE_C9);
  gm_bolt_2022_pedal = GET_FLAG(param, GM_PARAM_BOLT_2022_PEDAL);
  gm_remote_start_boots_comma = GET_FLAG(param, GM_PARAM_REMOTE_START_BOOTS_COMMA);
  gm_panda_3d1_sched = GET_FLAG(param, GM_PARAM_PANDA_3D1_SCHED) && gm_pedal_long && !gm_has_acc && !gm_bolt_2022_pedal;
  gm_panda_paddle_sched = GET_FLAG(param, GM_PARAM_PANDA_PADDLE_SCHED) && gm_pedal_long && enable_gas_interceptor;

  gm_3d1_spoof_valid = false;
  gm_3d1_internal_tx = false;
  gm_3d1_next_tx_us = 0U;
  gm_3d1_expected_stock_us = 0U;
  gm_3d1_last_stock_us = 0U;
  gm_3d1_phase_locked = false;
  gm_paddle_internal_tx = false;
  gm_zero_u8(gm_3d1_spoof_data, 8U);

  gm_bd_state.spoof_valid = false;
  gm_bd_state.next_tx_us = 0U;
  gm_bd_state.expected_stock_us = 0U;
  gm_bd_state.last_stock_us = 0U;
  gm_bd_state.last_feed_us = 0U;
  gm_bd_state.phase_locked = false;
  gm_zero_u8(gm_bd_state.spoof_data, 8U);

  gm_prndl2_state.spoof_valid = false;
  gm_prndl2_state.next_tx_us = 0U;
  gm_prndl2_state.expected_stock_us = 0U;
  gm_prndl2_state.last_stock_us = 0U;
  gm_prndl2_state.last_feed_us = 0U;
  gm_prndl2_state.phase_locked = false;
  gm_zero_u8(gm_prndl2_state.spoof_data, 8U);

  gm_cam_long = GET_FLAG(param, GM_PARAM_HW_CAM_LONG) && !gm_cc_long;
  gm_pcm_cruise = (gm_hw == GM_CAM || gm_sdgm) && !gm_cam_long && !gm_force_ascm && !gm_pedal_long;
  const bool gm_ascm_int_stock_cam = gm_ascm_int && (gm_hw == GM_CAM) && gm_pcm_cruise && !gm_cam_long && !gm_pedal_long && !gm_cc_long;
  gm_steer_limits = GET_FLAG(param, GM_PARAM_BOLT_2017) ? &GM_BOLT_2017_STEERING_LIMITS : &GM_STEERING_LIMITS;

  if (gm_hw == GM_ASCM || gm_ascm_int || gm_force_ascm) {
    gm_long_limits = &GM_ASCM_LONG_LIMITS;
  } else {
    gm_long_limits = &GM_CAM_LONG_LIMITS;
  }

  safety_config ret;
  if (gm_hw == GM_CAM) {
    // FIXME: cppcheck thinks that gm_cam_long is always false. This is not true
    // if ALLOW_DEBUG is defined but cppcheck is run without ALLOW_DEBUG
    // cppcheck-suppress knownConditionTrueFalse
    if (gm_cc_long) {
      ret = BUILD_SAFETY_CFG(gm_rx_checks, GM_CC_LONG_TX_MSGS);
    } else if (gm_cam_long) {
      ret = BUILD_SAFETY_CFG(gm_rx_checks, GM_CAM_LONG_TX_MSGS);
    } else {
      ret = BUILD_SAFETY_CFG(gm_rx_checks, GM_CAM_TX_MSGS);
    }
  } else {
    ret = BUILD_SAFETY_CFG(gm_rx_checks, GM_ASCM_TX_MSGS);
  }

  const bool gm_ev = GET_FLAG(param, GM_PARAM_EV);
  if (enable_gas_interceptor) {
    if (gm_has_acc && (gm_hw == GM_CAM || gm_sdgm)) {
      SET_RX_CHECKS(gm_cam_acc_pedal_rx_checks, ret);
    } else {
      SET_RX_CHECKS(gm_pedal_rx_checks, ret);
    }
  } else if (gm_has_acc && (gm_hw == GM_CAM || gm_sdgm)) {
    SET_RX_CHECKS(gm_cam_acc_rx_checks, ret);
  } else if (!gm_has_acc && gm_ev) {
    SET_RX_CHECKS(gm_no_acc_ev_rx_checks, ret);
  } else if (!gm_has_acc && !gm_ev) {
    SET_RX_CHECKS(gm_no_acc_rx_checks, ret);
  } else if (gm_ev) {
    SET_RX_CHECKS(gm_ev_rx_checks, ret);
  }

  if (gm_ascm_int_stock_cam) {
    SET_RX_CHECKS(gm_ascm_int_stock_cam_rx_checks, ret);
  }

  // ASCM does not forward any messages
  if (gm_hw == GM_ASCM) {
    ret.disable_forwarding = true;
  }
  return ret;
}

const safety_hooks gm_hooks = {
  .init = gm_init,
  .rx = gm_rx_hook,
  .tx = gm_tx_hook,
  .fwd = gm_fwd_hook,
};
