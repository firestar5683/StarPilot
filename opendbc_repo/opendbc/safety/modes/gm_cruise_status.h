#pragma once

static bool gm_cruise_status_bolt;
static bool gm_cruise_status_hybrid;
static bool gm_cruise_status_removed;
static bool gm_cruise_status_pending;
static bool gm_cruise_status_internal;
static bool gm_cruise_status_accepted;
static bool gm_cruise_status_tx_seen;
static uint32_t gm_cruise_status_tx_us;
static uint32_t gm_cruise_status_feed_us;
static uint8_t gm_cruise_status_data[8];
static bool gm_cruise_status_seen[11];
static uint32_t gm_cruise_status_us[11];
static bool gm_cruise_status_main;
static bool gm_cruise_status_drive;
static bool gm_cruise_status_eps;

static bool gm_cruise_status_owner_ready(void);

static void gm_cruise_status_clear(void) {
  gm_cruise_status_pending = false;
  gm_cruise_status_accepted = false;
}

static void gm_cruise_status_reset(uint16_t word) {
  gm_cruise_status_clear();
  gm_cruise_status_internal = false;
  gm_cruise_status_feed_us = 0U;
  gm_cruise_status_tx_seen = false;
  gm_cruise_status_tx_us = 0U;
  gm_cruise_status_bolt = (word == 0xBDU) || (word == 0x9DU) || (word == 0x19DU) ||
    (word == 0xE700U) || (word == 0xE701U) || (word == 0xE702U);
  gm_cruise_status_hybrid = (word == 0xE802U) || (word == 0xE803U);
  gm_cruise_status_removed = word == 0xE803U;
  gm_cruise_status_main = false;
  gm_cruise_status_drive = false;
  gm_cruise_status_eps = false;
  for (uint8_t i = 0U; i < 11U; i++) {
    gm_cruise_status_seen[i] = false;
    gm_cruise_status_us[i] = 0U;
  }
  for (uint8_t i = 0U; i < 8U; i++) { gm_cruise_status_data[i] = 0U; }
}

static bool gm_cruise_status_sources_current(void) {
  static const uint32_t limits[11] = {300000U, 100000U, 100000U, 300000U, 300000U, 300000U,
                                    100000U, 100000U, 100000U, 1000000U, 1000000U};
  const uint32_t now = microsecond_timer_get();
  bool ready = (gm_cruise_status_bolt || gm_cruise_status_hybrid) &&
               !safety_rx_checks_invalid && !relay_malfunction && aol_rx_healthy();
  const uint8_t count = (gm_cruise_status_hybrid && !gm_cruise_status_removed) ? 11U : 9U;
  for (uint8_t i = 0U; i < count; i++) {
    const uint32_t limit = (gm_cruise_status_hybrid && (i == 6U)) ? 1000000U : limits[i];
    ready &= gm_cruise_status_seen[i] &&
      (safety_get_ts_elapsed(now, gm_cruise_status_us[i]) <= limit);
  }
  return ready;
}

static bool gm_cruise_status_ready(void) {
  return gm_cruise_status_sources_current() && gm_cruise_status_owner_ready();
}

static void gm_cruise_status_prune(void) {
  if (!gm_cruise_status_ready() ||
      (safety_get_ts_elapsed(microsecond_timer_get(), gm_cruise_status_feed_us) > 100000U)) {
    gm_cruise_status_clear();
  }
}

static bool gm_cruise_status_shape(const CANPacket_t *msg) {
  return msg_matches(msg, 0x3D1U, 0U, 8U) && (msg->data[0] == 1U) && (msg->data[1] == 0U) &&
    ((msg->data[2] & 0xF0U) == 0U) && (msg->data[4] == 0U) && (msg->data[5] == 0U) &&
    (msg->data[6] == 0U) && (msg->data[7] == 0U);
}

static bool gm_cruise_status_cadence_ready(void) {
  return !gm_cruise_status_hybrid || !gm_cruise_status_tx_seen ||
    (safety_get_ts_elapsed(microsecond_timer_get(), gm_cruise_status_tx_us) >= 40000U);
}

static bool gm_cruise_status_tx(const CANPacket_t *msg) {
  gm_cruise_status_prune();
  const bool valid = gm_cruise_status_shape(msg) && gm_cruise_status_ready();
  bool allowed = false;
  if (!valid) {
    gm_cruise_status_clear();
  } else if (gm_cruise_status_hybrid) {
    // This is a TX acceptance lease, not evidence of bus delivery.
    allowed = gm_cruise_status_cadence_ready();
    if (allowed) {
      gm_cruise_status_accepted = true;
      gm_cruise_status_feed_us = microsecond_timer_get();
    }
  } else if (gm_cruise_status_internal) {
    allowed = gm_cruise_status_cadence_ready();
  } else {
    for (uint8_t i = 0U; i < 8U; i++) { gm_cruise_status_data[i] = msg->data[i]; }
    gm_cruise_status_feed_us = microsecond_timer_get();
    gm_cruise_status_pending = true;
  }
  if (allowed) {
    gm_cruise_status_tx_seen = true;
    gm_cruise_status_tx_us = microsecond_timer_get();
  }
  return allowed;
}

static bool gm_cruise_status_block(int bus, int addr) {
  // Forwarding precedes RX. A prior emission alone cannot replace this packet.
  return (bus == 0) && (addr == 0x3D1) && gm_cruise_status_ready() &&
    (safety_get_ts_elapsed(microsecond_timer_get(), gm_cruise_status_feed_us) <= 100000U) &&
    (gm_cruise_status_bolt ? gm_cruise_status_pending : gm_cruise_status_accepted);
}

static void gm_cruise_status_observe(const CANPacket_t *msg) {
  static const uint32_t addresses[11] = {0x184U, 0x34AU, 0x1E1U, 0x1C4U, 0xC9U, 0x3D1U,
                                        0x1F5U, 0xBDU, 0x201U, 0x180U, 0x320U};
  static const uint8_t lengths[11] = {8U, 5U, 7U, 8U, 8U, 8U, 8U, 7U, 6U, 4U, 6U};
  if ((gm_cruise_status_bolt || gm_cruise_status_hybrid) && !msg->returned && !msg->rejected) {
    for (uint8_t i = 0U; i < 11U; i++) {
      if ((msg->addr == addresses[i]) && (msg->bus == ((i < 9U) ? 0U : 2U)) &&
          (GET_LEN(msg) != lengths[i])) {
        gm_cruise_status_seen[i] = false;
        gm_cruise_status_clear();
      } else if (msg_matches(msg, addresses[i], (i < 9U) ? 0U : 2U, lengths[i])) {
        gm_cruise_status_seen[i] = true;
        gm_cruise_status_us[i] = microsecond_timer_get();
        if (i == 0U) {
          const uint8_t eps = (msg->data[0] >> 3U) & 7U;
          gm_cruise_status_eps = (eps != 2U) && (eps != 3U);
        } else if (i == 4U) {
          gm_cruise_status_main = GET_BIT(msg, 29U);
        } else if (i == 6U) {
          const uint8_t gear = msg->data[3] & 15U;
          gm_cruise_status_drive = ((gear == 4U) || (gear == 6U)) && !GET_BIT(msg, 41U);
        } else {
          // These sources only update their freshness clocks.
        }
      } else {
        // Unrelated packets do not refresh this source.
      }
    }
  }
  gm_cruise_status_prune();
  if (gm_cruise_status_bolt && msg_matches(msg, 0x3D1U, 0U, 8U) &&
      !msg->returned && !msg->rejected && gm_cruise_status_pending) {
    gm_cruise_status_pending = false;
    CANPacket_t packet = {0};
    packet.addr = 0x3D1U;
    packet.bus = 0U;
    packet.data_len_code = 8U;
    for (uint8_t i = 0U; i < 8U; i++) { packet.data[i] = gm_cruise_status_data[i]; }
    can_set_checksum(&packet);
    gm_cruise_status_internal = true;
    can_send(&packet, 0U, false);
    gm_cruise_status_internal = false;
  }
}
