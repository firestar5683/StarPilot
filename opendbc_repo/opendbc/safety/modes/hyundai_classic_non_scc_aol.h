#pragma once

// Exact classic NON_SCC independent owners. Never used by CANFD mode.
#define HYUNDAI_FORTE_AOL_MARKER 0x0400U
#define HYUNDAI_FORTE_AOL_MAIN (0x1000U | HYUNDAI_FORTE_AOL_MARKER)
#define HYUNDAI_FORTE_AOL_LDA (0x1800U | HYUNDAI_FORTE_AOL_MARKER)
#define HYUNDAI_KONA_AOL_MAIN 0x1440U
#define HYUNDAI_KONA_AOL_LDA 0x1C40U
#define HYUNDAI_NON_SCC_HEV_AOL_MAIN 0x1402U
#define HYUNDAI_NON_SCC_HEV_AOL_LDA 0x1C02U
#define HYUNDAI_NON_SCC_EV_ALT_AOL_MAIN 0x1441U
#define HYUNDAI_NON_SCC_EV_ALT_AOL_LDA 0x1C41U
#define HYUNDAI_CLASSIC_SOURCE_MAX_AGE_US 300000U

static bool classic_non_scc_aol_enabled = false;
static bool classic_non_scc_aol_ev = false;
static bool classic_non_scc_aol_hev = false;
static bool classic_non_scc_aol_lda = false;
static bool classic_non_scc_aol_main = false;
static bool classic_non_scc_aol_main_seen = false;
static bool classic_non_scc_aol_source_seen[2] = {false, false};
static bool classic_non_scc_aol_source_neutral[2] = {false, false};
static bool classic_non_scc_aol_source_pressed[2] = {false, false};
static uint32_t classic_non_scc_aol_source_ts[2] = {0U, 0U};
static bool classic_non_scc_aol_neutral_seen = false;
static bool classic_non_scc_aol_token = false;
static bool classic_non_scc_aol_claimed = false;
static uint32_t classic_non_scc_aol_token_ts = 0U;
static bool classic_non_scc_aol_session = false;
static bool classic_non_scc_aol_request_seen = false;
static uint32_t classic_non_scc_aol_request_ts = 0U;

static void classic_non_scc_aol_clear_authorization(void) {
  classic_non_scc_aol_main = false;
  classic_non_scc_aol_main_seen = false;
  classic_non_scc_aol_neutral_seen = false;
  classic_non_scc_aol_token = false;
  classic_non_scc_aol_claimed = false;
  classic_non_scc_aol_session = false;
  classic_non_scc_aol_request_seen = false;
  classic_non_scc_aol_request_ts = 0U;
  for (unsigned int i = 0U; i < 2U; i++) {
    classic_non_scc_aol_source_seen[i] = false;
    classic_non_scc_aol_source_pressed[i] = false;
    classic_non_scc_aol_source_neutral[i] = false;
    classic_non_scc_aol_source_ts[i] = 0U;
  }
  aol_host_axis_mask = 0U;
}

static void classic_non_scc_aol_reset(void) {
  classic_non_scc_aol_clear_authorization();
  classic_non_scc_aol_enabled = false;
  classic_non_scc_aol_ev = false;
  classic_non_scc_aol_hev = false;
  classic_non_scc_aol_lda = false;
}

static void classic_non_scc_aol_host_request(uint8_t mask) {
  const uint32_t now = microsecond_timer_get();
  if (classic_non_scc_aol_request_seen &&
      (safety_get_ts_elapsed(now, classic_non_scc_aol_request_ts) > AOL_HOST_REQUEST_TIMEOUT_US)) {
    // A late fresh request cannot revive authorization from an expired lease.
    classic_non_scc_aol_clear_authorization();
  }
  classic_non_scc_aol_request_ts = now;
  if (mask != 0U) {
    classic_non_scc_aol_request_seen = true;
  }
}

static uint8_t classic_non_scc_aol_request_mask(void) {
  uint8_t result = 0U;
  const uint32_t now = microsecond_timer_get();
  const bool expired = classic_non_scc_aol_request_seen &&
    (safety_get_ts_elapsed(now, classic_non_scc_aol_request_ts) > AOL_HOST_REQUEST_TIMEOUT_US);
  const bool token_expired = classic_non_scc_aol_token && !classic_non_scc_aol_claimed &&
    (safety_get_ts_elapsed(now, classic_non_scc_aol_token_ts) > AOL_HOST_REQUEST_TIMEOUT_US);
  if (relay_malfunction || safety_rx_checks_invalid || expired || token_expired ||
      (classic_non_scc_aol_session && !heartbeat_engaged)) {
    classic_non_scc_aol_clear_authorization();
  } else if (heartbeat_engaged) {
    classic_non_scc_aol_session = true;
    if (((aol_host_axis_mask & 1U) != 0U) && classic_non_scc_aol_token) {
      classic_non_scc_aol_claimed = true;
    }
    result = aol_host_axis_mask & 1U;  // NON-SCC never grants an independent longitudinal axis.
  } else {
    // Physical evidence may precede heartbeat but grants no permission yet.
  }
  return result;
}

static uint8_t classic_non_scc_aol_permission_mask(void) {
  uint8_t result = 0U;
  if (!aol_rx_healthy()) {
    classic_non_scc_aol_clear_authorization();
  } else {
    const uint8_t request = classic_non_scc_aol_request_mask();
    result = (((request & 1U) != 0U) && classic_non_scc_aol_main_seen &&
              (classic_non_scc_aol_main || classic_non_scc_aol_token || controls_allowed)) ? 1U : 0U;
  }
  return result;
}

static bool classic_non_scc_aol_combined_pressed(uint32_t now) {
  bool pressed = false;
  for (unsigned int i = 0U; i < 2U; i++) {
    pressed |= classic_non_scc_aol_source_seen[i] && classic_non_scc_aol_source_pressed[i] &&
      (safety_get_ts_elapsed(now, classic_non_scc_aol_source_ts[i]) <= HYUNDAI_CLASSIC_SOURCE_MAX_AGE_US);
  }
  return pressed;
}

static void classic_non_scc_aol_rx(const CANPacket_t *msg) {
  if (classic_non_scc_aol_enabled && (msg->bus == 0U)) {
    const uint32_t now = microsecond_timer_get();
    if ((GET_LEN(msg) == 8U) &&
        ((!classic_non_scc_aol_ev && !classic_non_scc_aol_hev && (msg->addr == 0x260U)) ||
         (classic_non_scc_aol_ev && (msg->addr == 0x592U)) ||
         (classic_non_scc_aol_hev && (msg->addr == 0x595U)))) {
      classic_non_scc_aol_main = classic_non_scc_aol_ev ? GET_BIT(msg, 34U) :
        (classic_non_scc_aol_hev ? GET_BIT(msg, 50U) : GET_BIT(msg, 25U));
      classic_non_scc_aol_main_seen = true;
    }
    if (classic_non_scc_aol_lda && (GET_LEN(msg) == 8U) && ((msg->addr == 0x391U) || (msg->addr == 0x50CU))) {
      // Source loss clears neutral evidence without manufacturing a release.
      for (unsigned int i = 0U; i < 2U; i++) {
        if (classic_non_scc_aol_source_seen[i] &&
            (safety_get_ts_elapsed(now, classic_non_scc_aol_source_ts[i]) > HYUNDAI_CLASSIC_SOURCE_MAX_AGE_US)) {
          classic_non_scc_aol_source_seen[i] = false;
          classic_non_scc_aol_source_pressed[i] = false;
          classic_non_scc_aol_source_neutral[i] = false;
          classic_non_scc_aol_neutral_seen = false;
        }
      }
      const unsigned int source = (msg->addr == 0x391U) ? 0U : 1U;
      const bool previous = classic_non_scc_aol_combined_pressed(now);
      const bool first = !classic_non_scc_aol_source_seen[source] ||
        (safety_get_ts_elapsed(now, classic_non_scc_aol_source_ts[source]) > HYUNDAI_CLASSIC_SOURCE_MAX_AGE_US);
      if (first) {
        classic_non_scc_aol_source_neutral[source] = false;
      }
      classic_non_scc_aol_source_seen[source] = true;
      classic_non_scc_aol_source_pressed[source] = GET_BIT(msg, (source == 0U) ? 4U : 56U);
      classic_non_scc_aol_source_ts[source] = now;
      if (!classic_non_scc_aol_source_pressed[source]) {
        classic_non_scc_aol_source_neutral[source] = true;
      }
      const bool pressed = classic_non_scc_aol_combined_pressed(now);
      if (!pressed) {
        classic_non_scc_aol_neutral_seen = true;
      } else if (!first && classic_non_scc_aol_source_neutral[source] && !previous && classic_non_scc_aol_neutral_seen && (aol_host_axis_mask == 0U)) {
        // Authorize the host's toggle; never invert a separate native latch.
        classic_non_scc_aol_token = true;
        classic_non_scc_aol_claimed = false;
        classic_non_scc_aol_token_ts = now;
      } else {
        // Held-at-init and an alternative source's zero are not new gestures.
      }
    }
  }
}

static void classic_non_scc_aol_configure(uint16_t param) {
  classic_non_scc_aol_reset();
  classic_non_scc_aol_enabled = ((param == HYUNDAI_FORTE_AOL_MAIN) || (param == HYUNDAI_FORTE_AOL_LDA) ||
                               (param == HYUNDAI_KONA_AOL_MAIN) || (param == HYUNDAI_KONA_AOL_LDA) ||
                               (param == HYUNDAI_NON_SCC_HEV_AOL_MAIN) || (param == HYUNDAI_NON_SCC_HEV_AOL_LDA) ||
                               (param == HYUNDAI_NON_SCC_EV_ALT_AOL_MAIN) || (param == HYUNDAI_NON_SCC_EV_ALT_AOL_LDA)) &&
    ((unsigned int)alternative_experience == 32U);
  classic_non_scc_aol_lda = classic_non_scc_aol_enabled && ((param == HYUNDAI_FORTE_AOL_LDA) || (param == HYUNDAI_KONA_AOL_LDA) ||
                                                          (param == HYUNDAI_NON_SCC_HEV_AOL_LDA) ||
                                                          (param == HYUNDAI_NON_SCC_EV_ALT_AOL_LDA));
  classic_non_scc_aol_ev = classic_non_scc_aol_enabled && ((param == HYUNDAI_NON_SCC_EV_ALT_AOL_MAIN) || (param == HYUNDAI_NON_SCC_EV_ALT_AOL_LDA));
  classic_non_scc_aol_hev = classic_non_scc_aol_enabled && ((param == HYUNDAI_NON_SCC_HEV_AOL_MAIN) || (param == HYUNDAI_NON_SCC_HEV_AOL_LDA));
  if (classic_non_scc_aol_enabled) {
    static const AolSafetyPolicy policy = {
      .reset = classic_non_scc_aol_reset,
      .host_request = classic_non_scc_aol_host_request,
      .request_mask = classic_non_scc_aol_request_mask,
      .permission_mask = classic_non_scc_aol_permission_mask,
      .rx_invalid = classic_non_scc_aol_clear_authorization,
    };
    aol_policy = &policy;
  }
}
