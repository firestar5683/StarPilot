#pragma once

static bool honda_stock_aol_enabled = false;
static bool honda_stock_aol_token = false;
static bool honda_stock_aol_main_neutral = false;
static bool honda_stock_aol_lkas_neutral = false;
static bool honda_stock_aol_lkas_previous = false;
static bool honda_stock_aol_session = false;
static bool honda_stock_aol_request_seen = false;
static bool honda_stock_aol_alt_main = false;
static bool honda_stock_aol_drive = false;
static bool honda_stock_aol_twn = false;
static uint8_t honda_stock_aol_eps = 0U;
static uint32_t honda_stock_aol_main_ts = 0U;
static RxCheck *honda_stock_aol_eps_check = NULL;
static RxCheck *honda_stock_aol_gear_check = NULL;
static RxCheck honda_rx_workspace[7];

static void honda_stock_aol_clear(void) {
  honda_stock_aol_token = false;
  honda_stock_aol_main_neutral = false;
  honda_stock_aol_lkas_neutral = false;
}

static void honda_stock_aol_reset(void) {
  honda_stock_aol_clear();
  honda_stock_aol_enabled = false;
  honda_stock_aol_session = false;
  honda_stock_aol_request_seen = false;
  honda_stock_aol_alt_main = false;
  honda_stock_aol_lkas_previous = false;
  honda_stock_aol_drive = false;
  honda_stock_aol_twn = false;
  honda_stock_aol_eps = 0U;
  honda_stock_aol_main_ts = 0U;
  honda_stock_aol_eps_check = NULL;
  honda_stock_aol_gear_check = NULL;
}

static void honda_stock_aol_host_request(uint8_t mask) {
  honda_stock_aol_request_seen |= mask != 0U;
}

static bool honda_stock_aol_sources_current(void) {
  bool current = false;
  if ((honda_stock_aol_eps_check != NULL) && (honda_stock_aol_gear_check != NULL)) {
    const uint32_t now = microsecond_timer_get();
    current = honda_stock_aol_eps_check->status.msg_seen && honda_stock_aol_gear_check->status.msg_seen &&
      (safety_get_ts_elapsed(now, honda_stock_aol_eps_check->status.last_timestamp) <= 300000U) &&
      (safety_get_ts_elapsed(now, honda_stock_aol_gear_check->status.last_timestamp) <= 300000U) &&
      (safety_get_ts_elapsed(now, honda_stock_aol_main_ts) <= 300000U);
  }
  return current;
}

static uint8_t honda_stock_aol_request_mask(void) {
  uint8_t request = 0U;
  const bool expired = honda_stock_aol_request_seen &&
    (safety_get_ts_elapsed(microsecond_timer_get(), aol_host_request_ts) > AOL_HOST_REQUEST_TIMEOUT_US);
  if (relay_malfunction || expired || safety_rx_checks_invalid ||
      (honda_stock_aol_session && (!heartbeat_engaged || !aol_rx_healthy() || !honda_stock_aol_sources_current()))) {
    honda_stock_aol_clear();
  } else if (heartbeat_engaged && aol_rx_healthy() && honda_stock_aol_sources_current()) {
    honda_stock_aol_session = true;
    request = aol_host_axis_mask;
  } else {
  }
  return request;
}

static uint8_t honda_stock_aol_permission_mask(void) {
  const uint8_t request = honda_stock_aol_request_mask();
  uint8_t permission = 0U;
  if (acc_main_on && honda_stock_aol_drive &&
      ((honda_stock_aol_eps == 0U) || (honda_stock_aol_eps == 3U) || (honda_stock_aol_eps == 4U))) {
    if (controls_allowed || honda_stock_aol_token) {
      permission = request & 1U;
    }
    if (controls_allowed) {
      permission |= request & 2U;
    }
  }
  return permission;
}

static bool honda_stock_aol_selected(const CANPacket_t *msg, const RxCheck *check) {
  bool selected = false;
  if ((check != NULL) && check->status.msg_seen) {
    const CanMsgCheck *source = &check->msg[check->status.index];
    selected = msg_matches(msg, source->addr, source->bus, source->len);
  }
  return selected;
}

static void honda_stock_aol_rx(const CANPacket_t *msg, unsigned int pt_bus, bool normal_engagement) {
  if (honda_stock_aol_enabled) {
    const unsigned int main_addr = honda_stock_aol_alt_main ? 0x1A6U : 0x326U;
    const unsigned int buttons_addr = honda_stock_aol_alt_main ? 0x1A6U : 0x296U;
    const unsigned int buttons_len = honda_stock_aol_alt_main ? 8U : 4U;
    if (msg_matches(msg, main_addr, pt_bus, 8U)) {
      const bool main_on = GET_BIT(msg, honda_stock_aol_alt_main ? 47U : 28U);
      honda_stock_aol_main_ts = microsecond_timer_get();
      if (!main_on) {
        honda_stock_aol_clear();
        honda_stock_aol_main_neutral = true;
      } else if (honda_stock_aol_main_neutral) {
        honda_stock_aol_token = true;
        honda_stock_aol_main_neutral = false;
      } else {
      }
    }
    if (msg_matches(msg, buttons_addr, pt_bus, buttons_len)) {
      const uint8_t setting = honda_stock_aol_alt_main ? ((msg->data[5] >> 2U) & 3U) : ((msg->data[0] >> 2U) & 3U);
      const bool lkas = setting == 1U;
      if (!lkas) {
        honda_stock_aol_lkas_neutral = true;
      } else if (honda_stock_aol_lkas_neutral && !honda_stock_aol_lkas_previous && acc_main_on) {
        honda_stock_aol_token = true;
        honda_stock_aol_lkas_neutral = false;
      } else {
      }
      honda_stock_aol_lkas_previous = lkas;
    }
    if (honda_stock_aol_selected(msg, honda_stock_aol_eps_check)) {
      honda_stock_aol_eps = (msg->addr == 0x18FU) ?
        (honda_stock_aol_twn ? (msg->data[5] & 15U) :
         ((GET_LEN(msg) == 6U) ? (msg->data[4] & 15U) : ((msg->data[4] >> 4U) & 15U))) :
        ((msg->data[1] >> 4U) & 15U);
      if ((honda_stock_aol_eps != 0U) && (honda_stock_aol_eps != 2U) && (honda_stock_aol_eps != 3U) &&
          (honda_stock_aol_eps != 4U) && (honda_stock_aol_eps != 6U)) {
        honda_stock_aol_clear();
      }
    }
    if (honda_stock_aol_selected(msg, honda_stock_aol_gear_check)) {
      uint8_t gear = msg->data[4] & 15U;
      if (msg->addr == 0x191U) {
        gear = msg->data[5] & 31U;
      } else if (msg->addr == 0x188U) {
        gear = msg->data[3] & 15U;
      } else {
      }
      honda_stock_aol_drive = (msg->addr == 0x188U) ? ((gear == 8U) || (gear == 0U)) :
        ((gear == 4U) || (gear == 7U) || (gear == 10U) || (gear == 11U));
    }
    // Only a newly accepted physical cruise grant can restore an independent token.
    // Qualify after parsing this frame's brake/main state, before generic pedal checks.
    const bool engagement_source = msg_matches(msg, 0x17CU, pt_bus, 8U) ||
      msg_matches(msg, buttons_addr, pt_bus, buttons_len);
    const bool request_current = !honda_stock_aol_request_seen ||
      (safety_get_ts_elapsed(microsecond_timer_get(), aol_host_request_ts) <= AOL_HOST_REQUEST_TIMEOUT_US);
    const bool eps_known = (honda_stock_aol_eps == 0U) || (honda_stock_aol_eps == 2U) ||
      (honda_stock_aol_eps == 3U) || (honda_stock_aol_eps == 4U) || (honda_stock_aol_eps == 6U);
    if (normal_engagement && engagement_source && controls_allowed && acc_main_on && honda_stock_aol_drive &&
        eps_known && !brake_pressed && !regen_braking && !steering_disengage &&
        heartbeat_engaged && !relay_malfunction && !safety_rx_checks_invalid && request_current &&
        aol_rx_healthy() && honda_stock_aol_sources_current()) {
      honda_stock_aol_token = true;
      honda_stock_aol_session = true;
    }
  }
}

static safety_config honda_copy_rx(const RxCheck *source, unsigned int count, safety_config ret) {
  const unsigned int selected_count = (count <= 7U) ? count : 0U;
  for (unsigned int i = 0U; i < 7U; i++) {
    honda_rx_workspace[i] = (i < selected_count) ? source[i] : (RxCheck){0};
  }
  ret.rx_checks = honda_rx_workspace;
  ret.rx_checks_len = selected_count;
  return ret;
}

static safety_config honda_stock_aol_configure(uint16_t param, bool nidec, bool alt_main, unsigned int pt_bus, safety_config ret) {
  honda_stock_aol_reset();
  bool valid = nidec ? ((param == 0U) || (param == 4U) || (param == 260U)) :
    ((param == 0U) || (param == 1U) || (param == 8U) || (param == 9U));
#ifdef ALLOW_DEBUG
  valid = valid || (!nidec && ((param == 10U) || (param == 11U)));
#endif
  honda_stock_aol_enabled = valid && ((unsigned int)alternative_experience == 32U) &&
    (ret.rx_checks_len >= 3) && (ret.rx_checks_len <= 5) && (pt_bus <= 1U);
  honda_stock_aol_alt_main = alt_main;
  honda_stock_aol_twn = nidec && (param == 260U);
  if (honda_stock_aol_enabled && (ret.rx_checks_len <= 5) && (pt_bus <= 1U)) {
    const unsigned int count = ret.rx_checks_len;
    static const RxCheck eps[] = {
      {.msg = {{0x18F, 0U, 7, 10U, .max_counter = 3U, .ignore_quality_flag = true},
               {0x18F, 0U, 6, 10U, .max_counter = 3U, .ignore_quality_flag = true},
               {0x190, 0U, 5, 10U, .max_counter = 3U, .ignore_quality_flag = true}}},
      {.msg = {{0x18F, 1U, 7, 10U, .max_counter = 3U, .ignore_quality_flag = true},
               {0x18F, 1U, 6, 10U, .max_counter = 3U, .ignore_quality_flag = true},
               {0x190, 1U, 5, 10U, .max_counter = 3U, .ignore_quality_flag = true}}},
    };
    static const RxCheck gear[] = {
      {.msg = {{0x191, 0U, 8, 10U, .max_counter = 3U, .ignore_quality_flag = true},
               {0x1A3, 0U, 8, 10U, .max_counter = 3U, .ignore_quality_flag = true},
               {0x188, 0U, 6, 10U, .max_counter = 3U, .ignore_quality_flag = true}}},
      {.msg = {{0x191, 1U, 8, 10U, .max_counter = 3U, .ignore_quality_flag = true},
               {0x1A3, 1U, 8, 10U, .max_counter = 3U, .ignore_quality_flag = true},
               {0x188, 1U, 6, 10U, .max_counter = 3U, .ignore_quality_flag = true}}},
    };
    static const RxCheck buttons[] = {
      {.msg = {{0x296, 0U, 4, 25U, .max_counter = 3U, .ignore_quality_flag = true}, {0}, {0}}},
      {.msg = {{0x296, 1U, 4, 25U, .max_counter = 3U, .ignore_quality_flag = true}, {0}, {0}}},
      {.msg = {{0x1A6, 0U, 8, 25U, .max_counter = 3U, .ignore_quality_flag = true}, {0}, {0}}},
    };
    honda_rx_workspace[0] = buttons[alt_main ? 2U : pt_bus];
    honda_rx_workspace[count] = eps[pt_bus];
    if (honda_stock_aol_twn) {
      honda_rx_workspace[count].msg[1] = (CanMsgCheck){0};
      honda_rx_workspace[count].msg[2] = (CanMsgCheck){0};
    }
    honda_rx_workspace[count + 1U] = gear[pt_bus];
    honda_stock_aol_eps_check = &honda_rx_workspace[count];
    honda_stock_aol_gear_check = &honda_rx_workspace[count + 1U];
    ret.rx_checks_len = count + 2U;
    static const AolSafetyPolicy policy = {
      .reset = honda_stock_aol_reset,
      .host_request = honda_stock_aol_host_request,
      .request_mask = honda_stock_aol_request_mask,
      .permission_mask = honda_stock_aol_permission_mask,
      .rx_invalid = honda_stock_aol_clear,
    };
    aol_policy = &policy;
  }
  return ret;
}
