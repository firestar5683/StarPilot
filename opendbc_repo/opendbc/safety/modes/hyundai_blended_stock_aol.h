#pragma once

static bool blended_aol_enabled = false;
static bool blended_aol_token = false;
static bool blended_aol_claimed = false;
static bool blended_aol_session = false;
static bool blended_aol_request_seen = false;
static bool blended_aol_neutral[3] = {false, false, false};
static bool blended_aol_pressed[3] = {false, false, false};
static uint32_t blended_aol_source_ts[3] = {0U, 0U, 0U};
static uint32_t blended_aol_token_ts = 0U;
static unsigned int blended_aol_token_source = 3U;
static bool blended_aol_counter_seen = false;
static uint8_t blended_aol_counter = 0U;
static bool blended_aol_owned[3] = {false, false, false};
static uint32_t blended_aol_tx_ts[3] = {0U, 0U, 0U};

static void blended_aol_clear(void) {
  blended_aol_counter_seen = false;
  blended_aol_counter = 0U;
  blended_aol_token = false;
  blended_aol_claimed = false;
  blended_aol_session = false;
  blended_aol_request_seen = false;
  blended_aol_token_ts = 0U;
  blended_aol_token_source = 3U;
  aol_host_axis_mask = 0U;
  for (unsigned int i = 0U; i < 3U; i++) {
    blended_aol_neutral[i] = false;
    blended_aol_pressed[i] = false;
    blended_aol_source_ts[i] = 0U;
    blended_aol_owned[i] = false;
    blended_aol_tx_ts[i] = 0U;
  }
}

static void blended_aol_reset(void) {
  blended_aol_enabled = false;
  blended_aol_counter_seen = false;
  blended_aol_counter = 0U;
  blended_aol_clear();
}

static void blended_aol_host_request(uint8_t mask) {
  blended_aol_request_seen |= mask != 0U;
}

static uint8_t blended_aol_request_mask(void) {
  uint8_t result = 0U;
  const uint32_t now = microsecond_timer_get();
  const bool token_expired = blended_aol_token && !blended_aol_claimed &&
    (safety_get_ts_elapsed(now, blended_aol_token_ts) > AOL_HOST_REQUEST_TIMEOUT_US);
  const bool request_expired = blended_aol_request_seen &&
    (safety_get_ts_elapsed(now, aol_host_request_ts) > AOL_HOST_REQUEST_TIMEOUT_US);
  if (relay_malfunction || safety_rx_checks_invalid || token_expired || request_expired ||
      (blended_aol_session && !heartbeat_engaged)) {
    blended_aol_clear();
  } else if (heartbeat_engaged) {
    blended_aol_session = true;
    result = aol_host_axis_mask & 1U;
    if ((result != 0U) && blended_aol_token) {
      blended_aol_claimed = true;
    }
  } else {
  }
  return result;
}

static uint8_t blended_aol_permission_mask(void) {
  uint8_t result = 0U;
  const bool source_current = (blended_aol_token_source < 3U) &&
    (safety_get_ts_elapsed(microsecond_timer_get(), blended_aol_source_ts[blended_aol_token_source]) <= 300000U);
  if (!aol_rx_healthy() || (blended_aol_token && !source_current)) {
    blended_aol_clear();
  } else if ((blended_aol_request_mask() != 0U) && (controls_allowed || blended_aol_token)) {
    result = 1U;
  } else {
  }
  return result;
}

static void blended_aol_rx(const CANPacket_t *msg) {
  if (blended_aol_enabled) {
    const unsigned int pt = 0U;
    const uint32_t now = microsecond_timer_get();
    unsigned int source = 3U;
    bool pressed = false;
    if ((msg->bus == pt) && (msg->addr == 0x4F1U) && (GET_LEN(msg) == 4U)) {
      if ((msg->data[0] & 7U) == 4U) {
        blended_aol_clear();
      }
      source = 0U;
      pressed = GET_BIT(msg, 3U);
    } else if ((msg->bus == pt) && (msg->addr == 0x391U) && (GET_LEN(msg) == 8U)) {
      source = 1U;
      pressed = GET_BIT(msg, 4U);
    } else if ((msg->bus == pt) && (msg->addr == 0x50CU) && (GET_LEN(msg) == 8U)) {
      source = 2U;
      pressed = GET_BIT(msg, 56U);
    } else {
    }
    if (source < 3U) {
      const bool expired = (blended_aol_source_ts[source] == 0U) ||
        (safety_get_ts_elapsed(now, blended_aol_source_ts[source]) > 300000U);
      if (expired) {
        blended_aol_neutral[source] = false;
        blended_aol_pressed[source] = pressed;
      }
      if (!pressed) {
        blended_aol_neutral[source] = true;
      } else if (blended_aol_neutral[source] && !blended_aol_pressed[source] && (aol_host_axis_mask == 0U)) {
        blended_aol_token = true;
        blended_aol_claimed = false;
        blended_aol_token_ts = now;
        blended_aol_token_source = source;
      } else {
      }
      blended_aol_pressed[source] = pressed;
      blended_aol_source_ts[source] = now;
    }
  }
}

static void blended_aol_configure(uint16_t param) {
  blended_aol_reset();
  blended_aol_enabled = (param == 0x2000U) && ((unsigned int)alternative_experience == 32U);
  if (blended_aol_enabled) {
    static const AolSafetyPolicy policy = {
      .reset = blended_aol_reset,
      .host_request = blended_aol_host_request,
      .request_mask = blended_aol_request_mask,
      .permission_mask = blended_aol_permission_mask,
      .rx_invalid = blended_aol_clear,
    };
    aol_policy = &policy;
  }
}

static bool blended_aol_integrity(const CANPacket_t *msg) {
  bool valid = true;
  const unsigned int steering = 0x340U;
  if (blended_aol_enabled && (msg->addr == steering)) {
    valid = msg_matches(msg, steering, 0U, 8U);
    uint8_t counter = 0U;
    if (valid) {
      uint8_t crc = 0x22U;
      for (unsigned int i = 1U; i < 8U; i++) {
        crc = crc8_update(crc, msg->data[i], 0x1DU);
      }
      valid = (crc ^ 0xDFU) == msg->data[0];
      counter = (msg->data[4] >> 4U) & 0xFU;
    } else {
    }
    if (valid && blended_aol_counter_seen) {
      const unsigned int mask = 15U;
      valid = counter == ((blended_aol_counter + 1U) & mask);
    }
  }
  if (!valid) {
    blended_aol_clear();
  }
  return valid;
}

static void blended_aol_tx(const CANPacket_t *msg, bool accepted) {
  if (blended_aol_enabled) {
    bool accepted_current = accepted;
    const uint32_t addresses[3] = {0x340U, 0x364U, 0x485U};
    if ((msg->addr == addresses[0]) && (msg->bus == 0U)) {
      const bool active = GET_BIT(msg, 27U);
      if (accepted) {
        blended_aol_counter = ((msg->data[4] >> 4U) & 0xFU);
        blended_aol_counter_seen = true;
      }
      if (!accepted || !active) {
        for (unsigned int i = 0U; i < 3U; i++) {
          blended_aol_owned[i] = false;
        }
      }
      accepted_current &= active;
    }
    for (unsigned int i = 0U; i < 3U; i++) {
      if ((msg->addr == addresses[i]) && (msg->bus == 0U)) {
        blended_aol_owned[i] = accepted_current && ((i == 0U) || (blended_aol_owned[0] &&
          safety_get_ts_elapsed(microsecond_timer_get(), blended_aol_tx_ts[0]) <= AOL_HOST_REQUEST_TIMEOUT_US)) && aol_rx_healthy() && (controls_allowed || (blended_aol_permission_mask() != 0U));
        blended_aol_tx_ts[i] = microsecond_timer_get();
      }
    }
  }
}

static bool blended_aol_fwd(int bus, int addr) {
  bool blocked = false;
  if (blended_aol_enabled && (bus == 2) && aol_rx_healthy() && (controls_allowed || (blended_aol_permission_mask() != 0U))) {
    const uint32_t addresses[3] = {0x340U, 0x364U, 0x485U};
    for (unsigned int i = 0U; i < 3U; i++) {
      blocked |= (addr == (int)addresses[i]) && blended_aol_owned[i] &&
        (safety_get_ts_elapsed(microsecond_timer_get(), blended_aol_tx_ts[i]) <= AOL_HOST_REQUEST_TIMEOUT_US);
    }
  }
  return blocked;
}
