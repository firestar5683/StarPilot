#pragma once

#include "gm_bolt_cc_gate.h"

static void gm_rx_hook(const CANPacket_t *msg);
static bool gm_fwd_hook(int bus_num, int addr);
static bool gm_aol_mode_valid(void);

static GmBoltCcGate gm_bolt_cc_state;
static bool gm_bolt_cc_removed;
static bool gm_bolt_cc_stock_only;
static bool gm_bolt_cc_stock_main;
static unsigned int gm_bolt_cc_generation;
static uint8_t gm_bolt_cc_pscm[8];
static uint64_t gm_bolt_cc_pscm_tx_ns;
static uint32_t gm_bolt_cc_clock_prev;
static uint64_t gm_bolt_cc_clock_epoch;

static uint64_t gm_bolt_cc_now_ns(void) {
  const uint32_t us = microsecond_timer_get();
  if (us < gm_bolt_cc_clock_prev) {
    gm_bolt_cc_clock_epoch += 1ULL << 32U;
  }
  gm_bolt_cc_clock_prev = us;
  return (gm_bolt_cc_clock_epoch + us) * 1000ULL;
}

static void gm_bolt_cc_profile_rx(const CANPacket_t *msg) {
  const uint64_t now = gm_bolt_cc_now_ns();
  // Shared safety revocation remains latched until a physical rearm edge.
  if (!controls_allowed && gm_bolt_cc_state.armed) {
    gm_bolt_cc_state.armed = false;
  }
  if (gm_bolt_cc_receive(&gm_bolt_cc_state, msg->addr, msg->bus, msg->data, GET_LEN(msg), now)) {
    if (msg->bus == 0U) {
      if (msg->addr == 0x184U) {
        for (unsigned int i = 0U; i < 8U; i++) {
          gm_bolt_cc_pscm[i] = msg->data[i];
        }
        const unsigned int torque_raw = (((unsigned int)msg->data[6] & 7U) << 8U) | (unsigned int)msg->data[7];
        update_sample(&torque_driver, to_signed((int)torque_raw, 11));
      }
      if (msg->addr == 0x34AU) {
        vehicle_moving = gm_bolt_cc_state.speed > (0.311F / 3.6F);
      }
      if (gm_bolt_cc_stock_only && (msg->addr == 0xC9U)) {
        gm_bolt_cc_stock_main = GET_BIT(msg, 29U);
        if (!gm_bolt_cc_stock_main) { gm_bolt_cc_state.credit = false; }
      }
      brake_pressed = gm_bolt_cc_state.brake;
      gas_pressed = gm_bolt_cc_state.gas;
      regen_braking = gm_bolt_cc_state.regen;
      cruise_engaged_prev = gm_bolt_cc_state.active;
      controls_allowed = gm_bolt_cc_state.armed && gm_bolt_cc_state.active;
    }
  }
}

static bool gm_bolt_cc_profile_tx(const CANPacket_t *msg) {
  const uint64_t now = gm_bolt_cc_now_ns();
  bool fresh = true;
  for (unsigned int i = 0U; i < 7U; i++) {
    fresh = fresh && gm_bolt_cc_state.seen[i] && (now >= gm_bolt_cc_state.stamps[i]) &&
            ((now - gm_bolt_cc_state.stamps[i]) <= 300000000ULL);
  }
  bool allowed = false;
  if (msg->addr == 0x1E1U) {
    const bool stock_cancel = !gm_bolt_cc_stock_only || (gm_bolt_cc_stock_main && (((msg->data[5] >> 4U) & 7U) == 6U));
    allowed = stock_cancel && gm_bolt_cc_transmit(&gm_bolt_cc_state, msg->addr, msg->bus, msg->data, GET_LEN(msg), now,
                                  longitudinal_controls_allowed(), get_longitudinal_allowed());
  } else if ((msg->addr == 0x180U) && (msg->bus == 0U) && (GET_LEN(msg) == 4U)) {
    allowed = fresh && (!gm_aol_lateral_allowed() || gm_bolt_cc_state.drive) && gm_tx_hook(msg);
  } else if ((msg->addr == 0x184U) && (msg->bus == 2U) && (GET_LEN(msg) == 8U) && (gm_bolt_cc_generation != 0U)) {
    const uint8_t masks[8] = {0x3FU, 0xFFU, 0x3FU, 0xFFU, 0x7BU, 0xFFU, 7U, 0xFFU};
    uint8_t expected[8];
    for (unsigned int i = 0U; i < 8U; i++) {
      expected[i] = gm_bolt_cc_pscm[i] & masks[i];
    }
    unsigned int checksum = (((unsigned int)gm_bolt_cc_pscm[4] & 3U) << 8U) | (unsigned int)gm_bolt_cc_pscm[5];
    if ((gm_bolt_cc_pscm[2] & 32U) == 0U) {
      checksum += 32U;
    }
    expected[2] = (uint8_t)((unsigned int)expected[2] | 32U);
    expected[4] = (uint8_t)(((unsigned int)expected[4] & 0xFCU) | ((checksum >> 8U) & 3U));
    expected[5] = (uint8_t)(checksum & 255U);
    bool payload_matches = true;
    for (unsigned int i = 0U; i < 8U; i++) {
      payload_matches &= expected[i] == msg->data[i];
    }
    const bool valid = gm_bolt_cc_state.seen[0] && (now >= gm_bolt_cc_state.stamps[0]) &&
                       ((now - gm_bolt_cc_state.stamps[0]) <= 100000000ULL) &&
                       ((gm_bolt_cc_pscm_tx_ns == 0ULL) || ((now - gm_bolt_cc_pscm_tx_ns) >= 100000000ULL)) &&
                       payload_matches;
    if (valid) {
      gm_bolt_cc_pscm_tx_ns = now;
    }
    allowed = valid;
  } else if (gm_bolt_cc_removed && (gm_bolt_cc_generation != 0U) && ((msg->addr == 0x409U) || (msg->addr == 0x40AU)) &&
             (msg->bus == 0U) && (GET_LEN(msg) == 7U)) {
    allowed = true;
    for (unsigned int i = 0U; i < 7U; i++) {
      allowed &= msg->data[i] == 0U;
    }
  } else {
    allowed = false;
  }
  return allowed;
}

static bool gm_bolt_cc_profile_fwd(int bus, int addr) {
  // Preserve the original no-ACC camera withholding policy without a cruise spoof.
  return ((bus == 2) && (addr == 0x180)) || ((bus == 0) && ((addr == 0x184) || (addr == 0x3D1)));
}

static safety_config gm_bolt_cc_profile_init(uint16_t tag) {
  const unsigned int tag_value = tag;
  const unsigned int generation = ((tag_value >= 1U) && (tag_value <= 6U)) ? (((tag_value - 1U) / 2U) + 1U) : 0U;
  const bool gm_bolt_cc_adaptive = (tag == 7U) || (tag == 8U);
  const bool gm_bolt_cc_camera_required = tag == 7U;
  gm_bolt_cc_generation = gm_bolt_cc_adaptive ? 3U : generation;
  gm_bolt_cc_removed = (gm_bolt_cc_generation != 0U) && ((tag % 2U) == 0U);
  for (unsigned int i = 0U; i < 8U; i++) {
    gm_bolt_cc_pscm[i] = 0U;
  }
  gm_bolt_cc_pscm_tx_ns = 0ULL;
  gm_bolt_cc_clock_prev = microsecond_timer_get();
  gm_bolt_cc_clock_epoch = 0ULL;
  uint16_t base_param = 1U;
  if (gm_bolt_cc_generation == 1U) {
    base_param = 33U;
  }
  (void)gm_init(base_param);
  gm_bolt_cc_reset(&gm_bolt_cc_state, gm_bolt_cc_generation);
  gm_bolt_cc_state.camera_required = gm_bolt_cc_camera_required;

  static RxCheck rx[] = {
    {.msg = {{0x184U, 0U, 8U, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    {.msg = {{0x3D1U, 0U, 8U, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    {.msg = {{0x1E1U, 0U, 7U, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    {.msg = {{0xC9U, 0U, 8U, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    {.msg = {{0x1C4U, 0U, 8U, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    {.msg = {{0x1F5U, 0U, 8U, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    {.msg = {{0x34AU, 0U, 5U, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}}
  };
  static RxCheck adaptive_rx[] = {
    {.msg = {{0x184U, 0U, 8U, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    {.msg = {{0x3D1U, 0U, 8U, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    {.msg = {{0x1E1U, 0U, 7U, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    {.msg = {{0xC9U, 0U, 8U, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    {.msg = {{0x1C4U, 0U, 8U, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    {.msg = {{0x1F5U, 0U, 8U, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    {.msg = {{0x370U, 2U, 6U, 25U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}},
    {.msg = {{0x34AU, 0U, 5U, 10U, .ignore_checksum = true, .ignore_counter = true, .ignore_quality_flag = true}, {0}, {0}}}
  };
  static const CanMsg tx[] = {
    {0x180U, 0U, 4U, .check_relay = true}, {0x1E1U, 0U, 7U, .check_relay = false}, {0x184U, 2U, 8U, .check_relay = true}
  };
  static const CanMsg removed_tx[] = {
    {0x180U, 0U, 4U, .check_relay = false}, {0x1E1U, 0U, 7U, .check_relay = false}, {0x184U, 2U, 8U, .check_relay = false},
    {0x409U, 0U, 7U, .check_relay = false}, {0x40AU, 0U, 7U, .check_relay = false}
  };
  static const CanMsg adaptive_tx[] = {
    {0x180U, 0U, 4U, .check_relay = true}, {0x1E1U, 0U, 7U, .check_relay = false},
    {0x184U, 2U, 8U, .check_relay = true}, {0x1E1U, 2U, 7U, .check_relay = false}
  };
  static const CanMsg denied_tx[] = {{0U, 0U, 0U, .check_relay = false}};
  safety_config ret = BUILD_SAFETY_CFG(rx, tx);
  if (gm_bolt_cc_camera_required) {
    SET_RX_CHECKS(adaptive_rx, ret);
    SET_TX_MSGS(adaptive_tx, ret);
  }
  if (gm_bolt_cc_removed) {
    SET_TX_MSGS(removed_tx, ret);
  }
  if (gm_bolt_cc_stock_only) {
    static const CanMsg stock_tx[] = {
      {0x180U, 0U, 4U, .check_relay = false}, {0x1E1U, 0U, 7U, .check_relay = false},
      {0x184U, 2U, 8U, .check_relay = false}
    };
    SET_TX_MSGS(stock_tx, ret);
  }
  if (gm_bolt_cc_generation == 0U) {
    SET_TX_MSGS(denied_tx, ret);
  }
  return ret;
}

// Complete-word dispatch keeps every other GM profile on its existing hooks.

static unsigned int gm_bolt_cc_tag(uint16_t word) {
  static const uint16_t GM_BOLT_CC_WORDS[6] = {0xC110U, 0xC111U, 0xC120U, 0xC121U, 0xC130U, 0xC131U};

  unsigned int tag = (word == 0xC140U) ? 7U : 0U;
  switch (word) {
    case 0xE710U: tag = 2U; break;
    case 0xE711U: tag = 4U; break;
    case 0xE712U: tag = 6U; break;
    case 0xE713U: tag = 8U; break;
    default: break;
  }
  if (word == 0xC141U) {
    tag = 8U;
  }
  for (unsigned int i = 0U; i < 6U; i++) {
    if (word == GM_BOLT_CC_WORDS[i]) {
      tag = i + 1U;
      break;
    }
  }
  return tag;
}

static bool gm_bolt_cc_selected;

static safety_config gm_bolt_cc_init(uint16_t word) {
  gm_hybrid_rejected = ((word & 0xFF00U) == 0xE800U) && ((word > 0xE805U) ||
    ((alternative_experience != 0) && (alternative_experience != 32)));
  gm_hybrid_selected = (word >= 0xE800U) && (word <= 0xE805U);
  safety_config ret;
  if (gm_hybrid_selected) {
    gm_bolt_cc_selected = false;
    ret = gm_hybrid_init(word);
  } else {
    gm_bolt_cc_stock_main = false;
    gm_bolt_cc_stock_only = (word == 0xE710U) || (word == 0xE711U) || (word == 0xE712U) || (word == 0xE713U);
    const unsigned int tag = gm_bolt_cc_tag(word);
    gm_bolt_cc_selected = tag != 0U;
    ret = (tag != 0U) ? gm_bolt_cc_profile_init((uint16_t)tag) : gm_init(word);
    gm_aol_initialize(gm_aol_profile_word(word) && gm_aol_mode_valid());
    gm_aol_stock_only = gm_bolt_cc_stock_only || (word == 16U) || (word == 0xC162U);
    gm_aol_stock_gateway = word == 16U;
  }
  return ret;
}

static void gm_bolt_cc_rx(const CANPacket_t *msg) {
  if (gm_hybrid_selected) {
    gm_hybrid_rx(msg);
  } else if (gm_bolt_cc_selected) {
    gm_bolt_cc_profile_rx(msg);
  } else {
    gm_rx_hook(msg);
  }
  gm_aol_observe(msg);
}

static void gm_bolt_cc_optional_rx(const CANPacket_t *msg) {
  if (gm_hybrid_selected) {
    gm_hybrid_rx(msg);
  } else {
    gm_one_pedal_observe(msg);
    if (gm_bolt_cc_selected && (msg->addr == 0xBDU) && (msg->bus == 0U) && (GET_LEN(msg) == 7U)) {
      gm_bolt_cc_profile_rx(msg);
    }
  }
}

static bool gm_bolt_cc_tx(const CANPacket_t *msg) {
  return !gm_hybrid_rejected && (gm_hybrid_selected ? gm_hybrid_tx(msg) : (gm_bolt_cc_selected ? gm_bolt_cc_profile_tx(msg) : gm_tx_hook(msg)));
}

static bool gm_bolt_cc_fwd(int bus, int addr) {
  bool block;
  if (gm_hybrid_selected) { block = ((bus == 2) && (addr == 0x180)) || ((bus == 0) && (addr == 0x184)); }
  else { block = gm_bolt_cc_selected ? gm_bolt_cc_profile_fwd(bus, addr) : gm_fwd_hook(bus, addr); }
  return block;
}
