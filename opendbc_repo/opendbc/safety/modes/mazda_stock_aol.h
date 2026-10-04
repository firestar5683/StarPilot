#pragma once

static bool mazda_aol_enabled = false;
static bool mazda_aol_token = false;
static bool mazda_aol_neutral = false;
static bool mazda_aol_buttons_neutral = false;
static bool mazda_aol_requested = false;
static bool mazda_aol_owned = false;
static uint8_t mazda_aol_seen = 0U;
static uint8_t mazda_aol_sources = 0U;
static uint32_t mazda_aol_main_ts = 0U;
static uint32_t mazda_aol_gear_ts = 0U;
static uint32_t mazda_aol_eps_ts = 0U;
static uint32_t mazda_aol_cam_ts = 0U;
static uint32_t mazda_aol_accepted_ts = 0U;

static void mazda_aol_clear(void) {
  mazda_aol_token = false;
  mazda_aol_neutral = false;
  mazda_aol_buttons_neutral = false;
  mazda_aol_owned = false;
}

static void mazda_aol_reset(void) {
  mazda_aol_clear();
  mazda_aol_enabled = false;
  mazda_aol_requested = false;
  mazda_aol_seen = 0U;
  mazda_aol_sources = 0U;
  mazda_aol_main_ts = 0U;
  mazda_aol_gear_ts = 0U;
  mazda_aol_eps_ts = 0U;
  mazda_aol_cam_ts = 0U;
  mazda_aol_accepted_ts = 0U;
}

static bool mazda_aol_current(void) {
  const uint32_t now = microsecond_timer_get();
  return (mazda_aol_seen == 15U) &&
    (safety_get_ts_elapsed(now, mazda_aol_main_ts) <= 300000U) &&
    (safety_get_ts_elapsed(now, mazda_aol_gear_ts) <= 300000U) &&
    (safety_get_ts_elapsed(now, mazda_aol_eps_ts) <= 300000U) &&
    (safety_get_ts_elapsed(now, mazda_aol_cam_ts) <= 300000U);
}

static void mazda_aol_request(uint8_t mask) {
  mazda_aol_requested |= mask != 0U;
}

static uint8_t mazda_aol_request_mask(void) {
  uint8_t request = 0U;
  const bool expired = mazda_aol_requested &&
    (safety_get_ts_elapsed(microsecond_timer_get(), aol_host_request_ts) > AOL_HOST_REQUEST_TIMEOUT_US);
  if (relay_malfunction || expired || safety_rx_checks_invalid ||
      (!heartbeat_engaged || !aol_rx_healthy() || !mazda_aol_current())) {
    mazda_aol_clear();
  } else if (heartbeat_engaged && aol_rx_healthy() && mazda_aol_current()) {
    request = aol_host_axis_mask;
  } else {
  }
  return request;
}

static uint8_t mazda_aol_permission(void) {
  const uint8_t request = mazda_aol_request_mask();
  uint8_t permission = 0U;
  if (acc_main_on && vehicle_moving && (mazda_aol_sources == 1U)) {
    if (controls_allowed || mazda_aol_token) {
      permission = request & 1U;
    }
    if (controls_allowed) {
      permission |= request & 2U;
    }
  }
  return permission;
}

static void mazda_aol_optional_rx(const CANPacket_t *msg) {
  if (mazda_aol_enabled) {
    const uint32_t now = microsecond_timer_get();
    if (msg_matches(msg, 0x228U, 0U, 8U)) {
      mazda_aol_seen |= 2U;
      mazda_aol_gear_ts = now;
      mazda_aol_sources = (mazda_aol_sources & 6U) | (((msg->data[0] & 7U) == 4U) ? 1U : 0U);
    } else if (msg_matches(msg, 0x241U, 0U, 8U)) {
      mazda_aol_seen |= 4U;
      mazda_aol_eps_ts = now;
      mazda_aol_sources = (mazda_aol_sources & 5U) | (GET_BIT(msg, 50U) ? 2U : 0U);
    } else if (msg_matches(msg, 0x243U, 2U, 8U)) {
      mazda_aol_seen |= 8U;
      mazda_aol_cam_ts = now;
      mazda_aol_sources = (mazda_aol_sources & 3U) | (GET_BIT(msg, 16U) ? 4U : 0U);
      if ((mazda_aol_sources & 4U) != 0U) {
        mazda_aol_clear();
      }
    } else {
    }
  }
}

static void mazda_aol_rx(const CANPacket_t *msg) {
  if (mazda_aol_enabled) {
    if (msg_matches(msg, 0x21CU, 0U, 8U)) {
      mazda_aol_seen |= 1U;
      mazda_aol_main_ts = microsecond_timer_get();
      acc_main_on = GET_BIT(msg, 17U);
      if (!heartbeat_engaged || !aol_rx_healthy() || !mazda_aol_current() || safety_rx_checks_invalid || ((mazda_aol_sources & 4U) != 0U)) {
        mazda_aol_clear();
      } else if (!acc_main_on) {
        mazda_aol_clear();
        mazda_aol_neutral = true;
      } else if (mazda_aol_neutral) {
        mazda_aol_token = true;
        mazda_aol_neutral = false;
      } else {
      }
    } else if (msg_matches(msg, 0x9DU, 0U, 8U)) {
      const bool press = (msg->data[0] & 0x34U) != 0U;
      if (!heartbeat_engaged || !aol_rx_healthy() || !mazda_aol_current() || safety_rx_checks_invalid || ((mazda_aol_sources & 4U) != 0U)) {
        mazda_aol_clear();
      } else if ((msg->data[0] & 1U) != 0U) {
      } else if (!press) {
        mazda_aol_buttons_neutral = true;
      } else if (mazda_aol_buttons_neutral && acc_main_on) {
        mazda_aol_token = true;
        mazda_aol_buttons_neutral = false;
      } else {
      }
    } else {
    }
  }
}

static void mazda_aol_tx_commit(const CANPacket_t *msg, bool accepted) {
  if (mazda_aol_enabled && msg_matches(msg, 0x243U, 0U, 8U)) {
    const unsigned int raw_torque = ((msg->data[0] & 15U) << 8U) | msg->data[1];
    const int torque = (int)raw_torque - 2048;
    mazda_aol_owned = accepted && (torque != 0) && ((mazda_aol_permission() & 1U) != 0U);
    mazda_aol_accepted_ts = microsecond_timer_get();
  }
}

static bool mazda_aol_fwd(int bus, int addr) {
  return mazda_aol_enabled && (bus == 2) && ((addr == 0x243) || (addr == 0x440)) &&
    mazda_aol_owned && ((mazda_aol_permission() & 1U) != 0U) &&
    (safety_get_ts_elapsed(microsecond_timer_get(), mazda_aol_accepted_ts) <= AOL_HOST_REQUEST_TIMEOUT_US);
}
