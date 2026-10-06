#pragma once

static bool toyota_aol_enabled = false;
static bool toyota_aol_stock = false;
static bool toyota_aol_main = false;
static bool toyota_aol_drive = false;
static bool toyota_aol_doors_closed = false;
static bool toyota_aol_belt = false;
static bool toyota_aol_eps = false;
static bool toyota_aol_seen[4] = {false, false, false, false};
static uint32_t toyota_aol_ts[4] = {0U, 0U, 0U, 0U};

static void toyota_aol_reset(void) {
  toyota_aol_main = false;
  toyota_aol_drive = false;
  toyota_aol_doors_closed = false;
  toyota_aol_belt = false;
  toyota_aol_eps = false;
  for (unsigned int i = 0U; i < 4U; i++) {
    toyota_aol_seen[i] = false;
    toyota_aol_ts[i] = 0U;
  }
}

static uint8_t toyota_aol_request(void) {
  uint8_t request = 0U;
  if (heartbeat_engaged && aol_rx_healthy() && !relay_malfunction &&
      (safety_get_ts_elapsed(microsecond_timer_get(), aol_host_request_ts) <= AOL_HOST_REQUEST_TIMEOUT_US)) {
    request = aol_host_axis_mask & (toyota_aol_stock ? 1U : 3U);
  }
  return request;
}

static uint8_t toyota_aol_permission(void) {
  const uint8_t request = toyota_aol_request();
  static const uint32_t source_timeout[4] = {303031U, 10000000U, 3333334U, 400000U};
  bool fresh = true;
  for (unsigned int i = 0U; i < 4U; i++) {
    fresh &= toyota_aol_seen[i] && (safety_get_ts_elapsed(microsecond_timer_get(), toyota_aol_ts[i]) <= source_timeout[i]);
  }
  uint8_t permission = 0U;
  if (fresh && toyota_aol_main && toyota_aol_drive && toyota_aol_doors_closed && toyota_aol_eps) {
    permission = request & 1U;
    if (!toyota_aol_stock && controls_allowed && toyota_aol_belt && !gas_pressed && !brake_pressed) {
      permission |= request & 2U;
    }
  }
  return permission;
}

static void toyota_aol_observe(const CANPacket_t *msg) {
  if (toyota_aol_enabled && (msg->bus == 0U) && (GET_LEN(msg) != 8U)) {
    unsigned int index = 4U;
    if (msg->addr == 0x1D3U) {
      index = 0U;
    } else if (msg->addr == 0x3BCU) {
      index = 1U;
    } else if (msg->addr == 0x620U) {
      index = 2U;
    } else if (msg->addr == 0x262U) {
      index = 3U;
    } else {
    }
    if (index < 4U) {
      toyota_aol_seen[index] = false;
    }
  } else if (toyota_aol_enabled && (msg->bus == 0U) && (GET_LEN(msg) == 8U)) {
    unsigned int index = 4U;
    if (msg->addr == 0x1D3U) {
      index = 0U;
      toyota_aol_main = GET_BIT(msg, 15U) && !GET_BIT(msg, 47U);
    } else if (msg->addr == 0x3BCU) {
      index = 1U;
      const unsigned int gear = msg->data[1] & 0x3FU;
      toyota_aol_drive = (gear == 0U) || (gear == 1U);
    } else if (msg->addr == 0x620U) {
      index = 2U;
      toyota_aol_doors_closed = (msg->data[5] & 0x3CU) == 0U;
      toyota_aol_belt = !GET_BIT(msg, 62U);
    } else if (msg->addr == 0x262U) {
      index = 3U;
      const unsigned int state = (msg->data[3] >> 1U) & 0x7FU;
      toyota_aol_eps = (state != 0U) && (state != 9U) && (state != 11U) && (state != 21U) &&
                       (state != 25U) && (state != 3U) && (state != 17U);
    } else {
    }
    if (index < 4U) {
      toyota_aol_seen[index] = true;
      toyota_aol_ts[index] = microsecond_timer_get();
    }
  } else {
  }
}

static void toyota_aol_configure(uint16_t param) {
  toyota_aol_reset();
  toyota_aol_stock = (param == 585U) || (param == 4681U);
  toyota_aol_enabled = (toyota_aol_stock && (alternative_experience == 32)) ||
                       ((param == 4169U) && (alternative_experience == 32)) ||
                       ((param == 73U) && ((alternative_experience == 32) || (alternative_experience == 160) || (alternative_experience == 288)));
  if (toyota_aol_enabled) {
    static const AolSafetyPolicy policy = {
      .reset = toyota_aol_reset,
      .request_mask = toyota_aol_request,
      .permission_mask = toyota_aol_permission,
      .rx_invalid = toyota_aol_reset,
    };
    aol_policy = &policy;
  }
}
