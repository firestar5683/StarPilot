#pragma once

#define GM_ALT_EXP_ALWAYS_ON_LATERAL 32U
#define GM_AOL_MAIN_TIMEOUT_US 300000U

static bool gm_aol_enabled = false;
static bool gm_aol_main = false;
static bool gm_aol_main_seen = false;
static uint32_t gm_aol_main_us = 0U;

static void gm_aol_reset(void) {
  gm_aol_enabled = false;
  gm_aol_main = false;
  gm_aol_main_seen = false;
  gm_aol_main_us = 0U;
}

static uint8_t gm_aol_request_mask(void) {
  return (gm_aol_enabled && heartbeat_engaged && !relay_malfunction && !safety_rx_checks_invalid &&
          (safety_get_ts_elapsed(microsecond_timer_get(), aol_host_request_ts) <= AOL_HOST_REQUEST_TIMEOUT_US)) ?
         aol_host_axis_mask : 0U;
}

static uint8_t gm_aol_permission_mask(void) {
  uint8_t permission = 0U;
  const bool main_current = gm_aol_main_seen && gm_aol_main &&
    (safety_get_ts_elapsed(microsecond_timer_get(), gm_aol_main_us) <= GM_AOL_MAIN_TIMEOUT_US);
  if (aol_rx_healthy()) {
    const uint8_t request = gm_aol_request_mask();
    if (main_current) {
      permission = request & 0x1U;
    }
    if (controls_allowed && ((request & 0x2U) != 0U)) {
      permission |= 0x2U;
    }
  }
  return permission;
}

static void gm_aol_rx_invalid(void) {
  gm_aol_main_seen = false;
  aol_set_host_request(0U);
}

static void gm_aol_observe(const CANPacket_t *msg) {
  if (gm_aol_enabled && (msg->addr == 0xC9U) && (msg->bus == 0U) && (GET_LEN(msg) == 8U)) {
    gm_aol_main = GET_BIT(msg, 29U);
    gm_aol_main_seen = true;
    gm_aol_main_us = microsecond_timer_get();
    if (!gm_aol_main) {
      aol_set_host_request(0U);
    }
  }
}

// The caller supplies exact profile acceptance after its normal mode initialization.
static void gm_aol_initialize(bool profile_supported) {
  gm_aol_reset();
  gm_aol_enabled = profile_supported && ((unsigned int)alternative_experience == GM_ALT_EXP_ALWAYS_ON_LATERAL);
  if (gm_aol_enabled) {
    static const AolSafetyPolicy gm_aol_policy = {
      .reset = gm_aol_reset,
      .host_request = NULL,
      .request_mask = gm_aol_request_mask,
      .permission_mask = gm_aol_permission_mask,
      .rx_invalid = gm_aol_rx_invalid,
    };
    aol_policy = &gm_aol_policy;
  }
}

static bool gm_aol_profile_word(uint16_t word) {
  bool supported = false;
  switch (word) {
    case 0xD100U: case 0xD101U: case 0xD110U: case 0xD111U:
    case 0U: case 0x80U:
    case 0x201U: case 0x601U: case 0xA01U: case 0xE01U:
    case 0xE310U: case 0xE311U: case 0xE312U: case 0xE313U:
    case 0xE210U: case 0xE211U: case 0xE212U: case 0xE213U:
    case 0xE110U: case 0xE111U: case 0xE112U: case 0xE113U:
    case 0xC171U: case 0xC172U: case 5U:
    case 0xBDU: case 0x9DU: case 0x19DU: case 0x1CDU:
    case 0x205U: case 0x605U: case 0xA05U: case 0xE05U:
    case 0xC160U: case 0xC180U: case 0xC181U:
    case 0xC182U: case 0xC183U: case 0xC184U: case 0xC185U: case 0xC186U: case 0xC187U:
    case 0x1001U: case 0x1401U: case 0x3001U: case 0x3401U:
    case 0x1005U: case 0x1405U:
    case 0x4004U: case 0xC004U:
    case 0x4084U: case 0xC084U:
    case 0xC110U: case 0xC111U: case 0xC120U: case 0xC121U:
    case 0xC130U: case 0xC131U: case 0xC140U: case 0xC141U:
    case 0xC150U:
#ifdef ALLOW_DEBUG
    case 0xE300U: case 0xE301U: case 0xE302U: case 0xE303U:
    case 0xE320U: case 0xE321U: case 0xE322U: case 0xE323U:
    case 0xE340U: case 0xE341U: case 0xE342U: case 0xE343U:
    case 0xE360U: case 0xE361U: case 0xE362U: case 0xE363U:
    case 0xE200U: case 0xE201U: case 0xE202U: case 0xE203U:
    case 0xE220U: case 0xE221U: case 0xE222U: case 0xE223U:
    case 0xE240U: case 0xE241U: case 0xE242U: case 0xE243U:
    case 0xE260U: case 0xE261U: case 0xE262U: case 0xE263U:
    case 0xE100U: case 0xE101U: case 0xE102U: case 0xE103U:
    case 0xD102U: case 0xD103U: case 0xD104U: case 0xD105U:
    case 0xD106U: case 0xD107U: case 0xD108U: case 0xD109U:
    case 0xD10AU: case 0xD112U: case 0xD113U: case 0xD114U:
    case 0xD115U: case 0xD116U: case 0xD117U: case 0xD118U:
    case 0xD119U: case 0xD11AU:
    case 0x1003U: case 0x1403U:
    case 0x203U: case 0x603U: case 0xA03U: case 0xE03U:
    case 0xC170U: case 0xC173U:
    case 7U: case 20U:
    case 0x4207U: case 0x4607U: case 0x4A07U: case 0x4E07U:
    case 0x4007U:
    case 0x4287U: case 0x4687U: case 0x4A87U: case 0x4E87U: case 0x4087U:
    case 0x5087U: case 0x5487U:
    case 0xC1D1U: case 0xC1D3U:
    case 0x5007U: case 0x5407U: case 0xC151U:
#endif
      supported = true;
      break;
    default:
      break;
  }
  return supported;
}

static bool gm_aol_lateral_allowed(void) {
  return gm_aol_enabled && ((gm_aol_permission_mask() & 0x1U) != 0U);
}
