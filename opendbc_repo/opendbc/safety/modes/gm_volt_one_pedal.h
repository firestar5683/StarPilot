#pragma once

#define GM_ONE_PEDAL_MODE_TIMEOUT_US 300000U

typedef struct {
  bool enabled;
  bool paired_auto_hold;
  uint16_t canonical_hold_word;
} GMOnePedalConfig;

static GMOnePedalConfig gm_one_pedal_config = {0};
static bool gm_one_pedal_low;
static bool gm_one_pedal_mode;
static bool gm_one_pedal_mode_seen;
static uint32_t gm_one_pedal_mode_us;

static uint16_t gm_one_pedal_reset(uint16_t word) {
  gm_one_pedal_config = (GMOnePedalConfig){0};
  gm_one_pedal_low = false;
  gm_one_pedal_mode = false;
  gm_one_pedal_mode_seen = false;
  gm_one_pedal_mode_us = 0U;
  switch (word) {
    case 0xD100U: case 0xD110U:
      gm_one_pedal_config.canonical_hold_word = 0x4084U;
      gm_one_pedal_config.paired_auto_hold = word == 0xD110U;
      break;
    case 0xD101U: case 0xD111U:
      gm_one_pedal_config.canonical_hold_word = 0xC084U;
      gm_one_pedal_config.paired_auto_hold = word == 0xD111U;
      break;
#ifdef ALLOW_DEBUG
    case 0xD102U: case 0xD112U:
      gm_one_pedal_config.canonical_hold_word = 0x4287U;
      gm_one_pedal_config.paired_auto_hold = word == 0xD112U;
      break;
    case 0xD103U: case 0xD113U:
      gm_one_pedal_config.canonical_hold_word = 0x4687U;
      gm_one_pedal_config.paired_auto_hold = word == 0xD113U;
      break;
    case 0xD104U: case 0xD114U:
      gm_one_pedal_config.canonical_hold_word = 0x4A87U;
      gm_one_pedal_config.paired_auto_hold = word == 0xD114U;
      break;
    case 0xD105U: case 0xD115U:
      gm_one_pedal_config.canonical_hold_word = 0x4E87U;
      gm_one_pedal_config.paired_auto_hold = word == 0xD115U;
      break;
    case 0xD106U: case 0xD116U:
      gm_one_pedal_config.canonical_hold_word = 0x4087U;
      gm_one_pedal_config.paired_auto_hold = word == 0xD116U;
      break;
    case 0xD107U: case 0xD117U:
      gm_one_pedal_config.canonical_hold_word = 0x5087U;
      gm_one_pedal_config.paired_auto_hold = word == 0xD117U;
      break;
    case 0xD108U: case 0xD118U:
      gm_one_pedal_config.canonical_hold_word = 0x5487U;
      gm_one_pedal_config.paired_auto_hold = word == 0xD118U;
      break;
    case 0xD109U: case 0xD119U:
      gm_one_pedal_config.canonical_hold_word = 0xC1D1U;
      gm_one_pedal_config.paired_auto_hold = word == 0xD119U;
      break;
    case 0xD10AU: case 0xD11AU:
      gm_one_pedal_config.canonical_hold_word = 0xC1D3U;
      gm_one_pedal_config.paired_auto_hold = word == 0xD11AU;
      break;
#endif
    default:
      break;
  }
  gm_one_pedal_config.enabled = gm_one_pedal_config.canonical_hold_word != 0U;
  return gm_one_pedal_config.enabled ? gm_one_pedal_config.canonical_hold_word : word;
}

static bool gm_one_pedal_mode_qualified(uint32_t now);
static void gm_one_pedal_withdraw(void);

static void gm_one_pedal_observe(const CANPacket_t *msg) {
  if (gm_one_pedal_config.enabled && (msg->bus == 0U)) {
    if ((msg->addr == 0x1F5U) && (GET_LEN(msg) == 8U)) {
      gm_one_pedal_low = ((msg->data[3] & 0xFU) == 6U) && !GET_BIT(msg, 41U);
    } else if ((msg->addr == 0x3C7U) && (GET_LEN(msg) == 4U)) {
      gm_one_pedal_mode = GET_BIT(msg, 7U);
      gm_one_pedal_mode_seen = true;
      gm_one_pedal_mode_us = microsecond_timer_get();
    } else {
      // Other traffic cannot refresh mode or physical Low.
    }
    if (!gm_one_pedal_mode_qualified(microsecond_timer_get())) { gm_one_pedal_withdraw(); }
  }
}

static bool gm_one_pedal_mode_qualified(uint32_t now) {
  // Cadence is unknown: this is a bounded observation, not a periodic RX claim.
  if (gm_one_pedal_mode_seen && (safety_get_ts_elapsed(now, gm_one_pedal_mode_us) > GM_ONE_PEDAL_MODE_TIMEOUT_US)) {
    gm_one_pedal_mode_seen = false;
  }
  return gm_one_pedal_config.enabled && (gm_one_pedal_low || (gm_one_pedal_mode_seen && gm_one_pedal_mode));
}
