#pragma once

static bool ford_aol_enabled = false;
static bool ford_aol_token = false;
static bool ford_aol_main_available = false;
static bool ford_aol_token_claimed = false;
static uint32_t ford_aol_token_ts = 0U;
static bool ford_aol_main_neutral = false;
static bool ford_aol_main_previous = false;
static bool ford_aol_button_neutral = false;
static bool ford_aol_button_previous = false;
static bool ford_aol_session = false;
static bool ford_aol_request_seen = false;
static uint16_t ford_aol_param = 0U;
static bool ford_aol_drive = false;
static uint8_t ford_aol_eps = 0U;
static bool ford_aol_lka_ready = false;
static bool ford_aol_owned = false;
static uint32_t ford_aol_accepted_ts = 0U;

static void ford_aol_clear(void) {
  ford_aol_token = false;
  ford_aol_token_claimed = false;
  ford_aol_token_ts = 0U;
  ford_aol_main_neutral = false;
  ford_aol_button_neutral = false;
  ford_aol_owned = false;
}

static void ford_aol_reset(void) {
  ford_aol_clear();
  ford_aol_enabled = false;
  ford_aol_main_available = false;
  ford_aol_main_previous = false;
  ford_aol_button_previous = false;
  ford_aol_session = false;
  ford_aol_request_seen = false;
  ford_aol_param = 0U;
  ford_aol_drive = false;
  ford_aol_eps = 0U;
  ford_aol_lka_ready = false;
  ford_aol_accepted_ts = 0U;
}

static void ford_aol_host_request(uint8_t mask) {
  ford_aol_request_seen |= mask != 0U;
}

static uint8_t ford_aol_request_mask(void) {
  uint8_t result = 0U;
  const bool expired = ford_aol_request_seen &&
    (safety_get_ts_elapsed(microsecond_timer_get(), aol_host_request_ts) > AOL_HOST_REQUEST_TIMEOUT_US);
  const bool token_expired = ford_aol_token && !ford_aol_token_claimed &&
    (safety_get_ts_elapsed(microsecond_timer_get(), ford_aol_token_ts) > AOL_HOST_REQUEST_TIMEOUT_US);
  if (!aol_rx_healthy() || relay_malfunction || expired || token_expired || (ford_aol_session && !heartbeat_engaged)) {
    ford_aol_clear();
  } else if (heartbeat_engaged) {
    ford_aol_session = true;
    result = aol_host_axis_mask & 1U;
    if ((result != 0U) && ford_aol_token) {
      ford_aol_token_claimed = true;
    }
  } else {
  }
  return result;
}

static uint8_t ford_aol_permission_mask(void) {
  uint8_t result = 0U;
  if (ford_aol_eps >= 2U) {
    ford_aol_clear();
  }
  const uint16_t base = ford_aol_param & 0xFFFEU;
  const bool needs_lka = (base == 10U) || (base == 12U) || (base == 18U) || (base == 66U);
  if ((ford_aol_request_mask() != 0U) && (controls_allowed || ford_aol_token) &&
      ford_aol_main_available && ford_aol_drive && (ford_aol_eps == 0U) && (!needs_lka || ford_aol_lka_ready)) {
    result = 1U;
  }
  return result;
}

static void ford_aol_rx(const CANPacket_t *msg) {
  if (ford_aol_enabled && (msg->bus == 0U)) {
    if (msg_matches(msg, 0x165U, 0U, 8U)) {
      const unsigned int state = msg->data[1] & 7U;
      const bool main_available = (state == 3U) || (state == 4U) || (state == 5U);
      ford_aol_main_available = main_available;
      if (!main_available) {
        ford_aol_clear();
        ford_aol_main_neutral = true;
      } else if (ford_aol_main_neutral && !ford_aol_main_previous && (aol_host_axis_mask == 0U)) {
        ford_aol_token = true;
        ford_aol_token_claimed = false;
        ford_aol_token_ts = microsecond_timer_get();
      } else {
      }
      ford_aol_main_previous = main_available;
      if ((state == 1U) || (state == 2U)) {
        ford_aol_clear();
      }
    } else if (msg_matches(msg, 0x83U, 0U, 8U)) {
      const bool button = GET_BIT(msg, 40U);
      if (!button) {
        ford_aol_button_neutral = true;
      } else if (ford_aol_button_neutral && !ford_aol_button_previous && (aol_host_axis_mask == 0U)) {
        ford_aol_token = true;
        ford_aol_token_claimed = false;
        ford_aol_token_ts = microsecond_timer_get();
      } else {
      }
      ford_aol_button_previous = button;
      if (GET_BIT(msg, 8U) || GET_BIT(msg, 24U)) {
        ford_aol_clear();
      }
    } else if (msg_matches(msg, 0x82U, 0U, 8U)) {
      ford_aol_eps = msg->data[1] & 3U;
      if (ford_aol_eps >= 2U) {
        ford_aol_clear();
      }
    } else if (msg_matches(msg, 0x3CCU, 0U, 8U)) {
      const unsigned int state = msg->data[2] & 7U;
      ford_aol_lka_ready = ((ford_aol_param & 0xFFFEU) == 12U) ?
        ((((msg->data[0] >> 4U) & 3U) == 3U) && ((msg->data[0] & 0x40U) == 0U)) :
        ((state == 1U) || (state == 2U) || (state == 3U));
    } else {
      const uint16_t base = ford_aol_param & 0xFFFEU;
      const uint16_t gear_addr = (base == 8U) ? 0x230U : ((base == 10U) ? 0x5AU : 0x176U);
      if (msg_matches(msg, gear_addr, 0U, 8U)) {
        const unsigned int gear = (base == 8U) ? ((msg->data[1] >> 1U) & 15U) :
                                  ((base == 10U) ? (msg->data[6] & 15U) : (msg->data[3] & 15U));
        ford_aol_drive = (gear == 3U) || (gear == 4U) || (gear == 5U);
      }
    }
  }
}

static bool ford_aol_param_valid(uint16_t param) {
  bool result = false;
  switch (param) {
    case 8U: case 9U: case 10U: case 12U: case 13U: case 18U: case 32U: case 33U: case 66U:
      result = true;
      break;
#ifdef ALLOW_DEBUG
    case 11U: case 19U: case 67U:
      result = true;
      break;
#endif
    default:
      break;
  }
  return result;
}

static void ford_aol_configure(uint16_t param) {
  ford_aol_reset();
  ford_aol_enabled = ford_aol_param_valid(param) && ((unsigned int)alternative_experience == 32U);
  ford_aol_param = param;
  if (ford_aol_enabled) {
    static const AolSafetyPolicy policy = {
      .reset = ford_aol_reset,
      .host_request = ford_aol_host_request,
      .request_mask = ford_aol_request_mask,
      .permission_mask = ford_aol_permission_mask,
      .rx_invalid = ford_aol_clear,
    };
    aol_policy = &policy;
  }
}

static unsigned int ford_aol_replacement(void) {
  const uint16_t base = ford_aol_param & 0xFFFEU;
  return (base == 12U) ? 0x3CAU : (((base == 10U) || (base == 18U) || (base == 66U)) ? 0x3D6U : 0x3D3U);
}

static void ford_aol_tx(const CANPacket_t *msg, bool accepted) {
  if (ford_aol_enabled && (msg->bus == 0U) && (msg->addr == ford_aol_replacement())) {
    const bool active = (msg->addr == 0x3CAU) ? (((msg->data[0] >> 5U) == 2U) || ((msg->data[0] >> 5U) == 4U)) :
                       ((msg->addr == 0x3D3U) ? (((msg->data[4] >> 2U) & 7U) != 0U) :
                                               (((msg->data[0] >> 4U) & 7U) != 0U));
    ford_aol_owned = accepted && active && (ford_aol_permission_mask() != 0U) && !relay_malfunction;
    ford_aol_accepted_ts = microsecond_timer_get();
  }
}

static bool ford_aol_fwd(int bus, int addr) {
  bool blocked = false;
  if (ford_aol_enabled && (bus == 2) && ford_aol_owned && (ford_aol_permission_mask() != 0U) &&
      (safety_get_ts_elapsed(microsecond_timer_get(), ford_aol_accepted_ts) <= AOL_HOST_REQUEST_TIMEOUT_US)) {
    blocked = (addr == (int)ford_aol_replacement()) || (addr == 0x3D8) || (addr == 0x18A);
  }
  return blocked;
}
