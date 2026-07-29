#pragma once

#include "board/ev9_long_preinit_status.h"

#ifdef PANDA_HKG_REMOTE_START
extern bool hkg_remote_climate_wake;
#endif

// Resident, non-actuating bridge for the EV9 ADAS CommunicationControl startup
// race. This is only present in explicitly selected EV9 preinit firmware.

#define EV9_PREINIT_BUS_RADAR 0U
#define EV9_PREINIT_BUS_ECAN 1U
#define EV9_PREINIT_DIAG_ADDR 0x730U
#define EV9_PREINIT_DIAG_RESP_ADDR 0x738U

#define EV9_PREINIT_P2_TIMEOUT_US 50000U
#define EV9_PREINIT_NRC_RETRY_US 10000U
#define EV9_PREINIT_DIAG_DEADLINE_US 300000U
#define EV9_PREINIT_SUPPRESSION_QUIET_US 60000U
#define EV9_PREINIT_SUPPRESSION_TIMEOUT_US 300000U
#define EV9_PREINIT_REAPPEAR_CONFIRM_US 100000U
#define EV9_PREINIT_REAPPEAR_GAP_US 50000U
#define EV9_PREINIT_HEARTBEAT_EPOCH_GAP_US 200000U
#define EV9_PREINIT_TESTER_PRESENT_INTERVAL_US 1000000U
#define EV9_PREINIT_HOST_TP_TIMEOUT_US 1500000U
#define EV9_PREINIT_BUS_SLEEP_US 5000000U
#define EV9_PREINIT_IGNITION_FALL_DEBOUNCE_US 20000U
#define EV9_PREINIT_RESTORE_DRAIN_US 50000U
#define EV9_PREINIT_RESTORE_RETRY_US 50000U
#define EV9_PREINIT_RESTORE_FALLBACK_US 100000U
#define EV9_PREINIT_RESTORE_MAX_ATTEMPTS 3U
#define EV9_PREINIT_MAX_ATTEMPTS 3U
#define EV9_PREINIT_SESSION_NO_RESPONSE_MAX_ATTEMPTS 2U
#define EV9_PREINIT_COMMUNICATION_TYPE 0x01U
#define EV9_FP_HEARTBEAT 0x01U
#define EV9_FP_POWERTRAIN 0x02U
#define EV9_FP_SCC_CONTROL 0x04U
#define EV9_FP_WHEEL_SPEEDS 0x08U
#define EV9_FP_SCC_STATUS 0x10U
#define EV9_FP_FCA_STATUS 0x20U
#define EV9_FP_BSM_STATUS 0x40U
#define EV9_FP_STATIONARY 0x80U
#define EV9_FP_IDENTITY_REQUIRED (EV9_FP_HEARTBEAT | EV9_FP_POWERTRAIN | EV9_FP_SCC_CONTROL)
#define EV9_FP_KNOCKOUT_REQUIRED (EV9_FP_IDENTITY_REQUIRED | EV9_FP_WHEEL_SPEEDS | EV9_FP_STATIONARY)

#define EV9_PREINIT_REPLAY_COUNT 14U
#define EV9_PREINIT_HOST_HEARTBEAT_BIT (1UL << EV9_PREINIT_REPLAY_COUNT)
#define EV9_PREINIT_HOST_TP_BIT (1UL << (EV9_PREINIT_REPLAY_COUNT + 1U))
#define EV9_PREINIT_HOST_REQUIRED_MASK ((1UL << (EV9_PREINIT_REPLAY_COUNT + 2U)) - 1UL)
#define EV9_PREINIT_SLOW_CLAIM_HOLD_US 25000U
#define EV9_PREINIT_HANDOFF_SETTLE_US 500000U
#define EV9_PREINIT_RESTORE_HEARTBEAT_BIT 0x01U
#define EV9_PREINIT_RESTORE_12A_BIT 0x02U
#define EV9_PREINIT_RESTORE_CB_BIT 0x04U
#define EV9_PREINIT_RESTORE_160_BIT 0x08U
#define EV9_PREINIT_RESTORE_1A0_BIT 0x10U
#define EV9_PREINIT_RESTORE_REQUIRED_MASK 0x1FU
#define EV9_PREINIT_RESTORE_STREAM_COUNT 5U
#define EV9_PREINIT_RESTORE_FRESH_US 50000U
#define EV9_PREINIT_CAN_RESET_TIMEOUT_US 20000U
#define EV9_PREINIT_RESET_RECOVERY_QUIET_US 200000U
#define EV9_PREINIT_WHEEL_SPEED_FRESH_US 100000U
#define EV9_PREINIT_STEERING_ANGLE_FRESH_US 100000U
#define EV9_PREINIT_DRIVER_BRAKE_FRESH_US 2000000U
#define EV9_PREINIT_REMOTE_WAKE_FRESH_US 3000000U
#define EV9_PREINIT_STANDSTILL_RAW_MAX 12U
#define EV9_PREINIT_USB_CONTROL_REQUEST 0xEAU
#define EV9_PREINIT_USB_RELEASE 0x01U
#define EV9_PREINIT_SAFETY_MODEL 36U
#define EV9_PREINIT_LIFECYCLE_RELEASE_REQUESTED 0x01U
#define EV9_PREINIT_LIFECYCLE_RELEASE_COMPLETE 0x02U
#define EV9_PREINIT_LIFECYCLE_CAN_RESET_FAILED 0x04U

typedef enum {
  EV9_PREINIT_CAN_RESET_IDLE = 0,
  EV9_PREINIT_CAN_RESET_PENDING,
  EV9_PREINIT_CAN_RESET_COMPLETE,
  EV9_PREINIT_CAN_RESET_FAILED,
} ev9_preinit_can_reset_result_t;

typedef struct {
  uint16_t addr;
  uint8_t len;
  uint32_t period_us;
  uint32_t last_rx_us;
  uint32_t last_tx_us;
  uint32_t last_attempt_us;
  uint32_t last_host_tx_us;
  bool captured;
  bool host_claim_reservation_used;
  bool host_claim_reserved;
  bool host_hw_pending;
  CANPacket_t packet;
  CANPacket_t host_hw_packet;
} ev9_preinit_replay_t;

typedef struct {
  CANPacket_t packet;
  uint32_t received_us;
  bool valid_canfd_crc;
  bool rearm_candidate;
} ev9_preinit_rx_sample_t;

static ev9_preinit_replay_t ev9_preinit_replay[EV9_PREINIT_REPLAY_COUNT] = {
  {.addr = 0x12AU, .len = 16U, .period_us = 10000U},
  {.addr = 0xCBU,  .len = 24U, .period_us = 10000U},
  {.addr = 0x160U, .len = 16U, .period_us = 20000U},
  {.addr = 0x161U, .len = 32U, .period_us = 50000U},
  {.addr = 0x162U, .len = 32U, .period_us = 50000U},
  {.addr = 0x1A0U, .len = 32U, .period_us = 20000U},
  {.addr = 0x1BAU, .len = 24U, .period_us = 50000U},
  {.addr = 0x1DAU, .len = 32U, .period_us = 1000000U},
  {.addr = 0x1E0U, .len = 16U, .period_us = 50000U},
  {.addr = 0x1E5U, .len = 16U, .period_us = 50000U},
  {.addr = 0x1EAU, .len = 32U, .period_us = 50000U},
  {.addr = 0x200U, .len = 8U,  .period_us = 50000U},
  {.addr = 0x345U, .len = 8U,  .period_us = 200000U},
  {.addr = 0x38CU, .len = 32U, .period_us = 200000U},
};

static const uint8_t ev9_preinit_heartbeat_template[24] = {
  0x00U, 0x00U, 0x00U, 0x00U, 0xFFU, 0x00U, 0x6FU, 0x00U,
  0xE8U, 0x04U, 0x00U, 0x00U, 0x12U, 0x01U, 0x03U, 0x00U,
  0x55U, 0xFFU, 0xFFU, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U,
};
// Physical-frame identity masks. The replacement template above was captured
// from a returned host frame and is valid for neutral reconstruction, but it
// is not a stock-body identity signature. These masks retain every bit that
// stayed invariant across physical EV9 routes 128/144/146/148/16d/16e/170/181
// while excluding CRC, counters, pedal/acceleration, and drive-state fields.
// Requiring all three masked bodies keeps the resident diagnostic gate tied to
// this EV9 profile without assuming one frozen operating state.
static const uint8_t ev9_preinit_heartbeat_identity_mask[24] = {
  0x00U, 0x00U, 0x00U, 0xFFU, 0x00U, 0x00U, 0x00U, 0x00U,
  0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0xC0U, 0x00U, 0x00U,
  0x8AU, 0x07U, 0x00U, 0xFFU, 0xF7U, 0xFFU, 0xFFU, 0xFFU,
};
static const uint8_t ev9_preinit_heartbeat_identity_value[24] = {
  0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U,
  0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U,
  0x00U, 0x07U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U,
};
static const uint8_t ev9_preinit_powertrain_identity_mask[32] = {
  0x00U, 0x00U, 0x00U, 0xABU, 0xEAU, 0x80U, 0xCAU, 0xBFU,
  0x00U, 0x00U, 0x00U, 0x3EU, 0x01U, 0xC0U, 0x01U, 0x80U,
  0xF8U, 0xA0U, 0xFFU, 0x00U, 0x00U, 0xC0U, 0x78U, 0x03U,
  0xF2U, 0xFFU, 0xFFU, 0xFFU, 0xFFU, 0xFFU, 0xFFU, 0xFFU,
};
static const uint8_t ev9_preinit_powertrain_identity_value[32] = {
  0x00U, 0x00U, 0x00U, 0x01U, 0x00U, 0x00U, 0x00U, 0x05U,
  0x00U, 0x00U, 0x00U, 0x10U, 0x00U, 0x40U, 0x00U, 0x00U,
  0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U,
  0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U,
};
static const uint8_t ev9_preinit_scc_identity_mask[24] = {
  0x00U, 0x00U, 0x00U, 0xFFU, 0x00U, 0xC0U, 0xFFU, 0xFFU,
  0xFFU, 0xFFU, 0xFFU, 0xFFU, 0xFFU, 0xFFU, 0xFFU, 0xFFU,
  0xFFU, 0xFFU, 0xFFU, 0xFFU, 0xFFU, 0xFFU, 0xFFU, 0xFFU,
};
static const uint8_t ev9_preinit_scc_identity_value[24] = {
  0x00U, 0x00U, 0x00U, 0x10U, 0x00U, 0x00U, 0x00U, 0x00U,
  0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U,
  0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U,
};
static const uint8_t ev9_preinit_fallback_12a[] =
  "\x00\x00\x00\x02\x40\x00\x08\x00\x00\x00\x00\x00\x00\x64\x00\x00";
static const uint8_t ev9_preinit_fallback_cb[] =
  "\x00\x00\x00\x10\xfb\x3f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00";
static const uint8_t ev9_preinit_fallback_160[] =
  "\x00\x00\x00\x01\x00\x00\x00\x00\xff\xfc\x01\x00\xa8\x00\x10\x00";
static const uint8_t ev9_preinit_fallback_161[] =
  "\x00\x00\x00\x00\x00\x00\x00\x00\xc0\xff\xf0\xc0\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\x00\x00\x00\x00\x00\x00";
static const uint8_t ev9_preinit_fallback_162[] =
  "\x00\x00\x00\x27\x00\x00\x00\x00\xc0\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00";
static const uint8_t ev9_preinit_fallback_1a0[] =
  "\x00\x00\x00\xfe\xf7\x7f\x64\x00\x00\x00\x00\x00\x00\x08\x00\x00\xff\xf3\x3f\x1e\x0a\x00\x00\x00\xfe\x07\x00\x00\x00\x00\x00\x00";
static const uint8_t ev9_preinit_fallback_1ba[] =
  "\x00\x00\x00\x00\x00\x00\x00\x88\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f";
static const uint8_t ev9_preinit_fallback_1da[] =
  "\x00\x00\x00\x22\x00\x11\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00";
static const uint8_t ev9_preinit_fallback_1e0[] =
  "\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00";
static const uint8_t ev9_preinit_fallback_1e5[] =
  "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x22\x03\x00\x00\x00\x80";
static const uint8_t ev9_preinit_fallback_1ea[] =
  "\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x0f\x00";
static const uint8_t ev9_preinit_fallback_200[] = "\x00\x00\x00\x14\x80\x1a\x00\x00";
static const uint8_t ev9_preinit_fallback_345[] = "\x00\x00\x00\x15\x00\x56\x00\x00";
static const uint8_t ev9_preinit_fallback_38c[] =
  "\x00\x00\x00\xf7\x1f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00";

static ev9_preinit_state_t ev9_preinit_state = EV9_PREINIT_COLLECTING;
static ev9_preinit_trigger_t ev9_preinit_trigger = EV9_PREINIT_TRIGGER_NONE;
static uint8_t ev9_preinit_flags = 0U;
static uint8_t ev9_preinit_fingerprint = 0U;
static uint8_t ev9_preinit_attempts = 0U;
static uint8_t ev9_preinit_last_service = 0U;
static uint8_t ev9_preinit_last_response = 0U;
static uint8_t ev9_preinit_last_nrc = 0U;
static uint8_t ev9_preinit_first_ecan_len = 0U;
static uint16_t ev9_preinit_first_ecan_addr = 0U;
static uint8_t ev9_preinit_powertrain_state = 0U;
static uint8_t ev9_preinit_powertrain_boot_state = 0U;
static uint8_t ev9_preinit_powertrain_init_state = 0U;
static uint8_t ev9_preinit_restore_seen = 0U;
static uint8_t ev9_preinit_restore_attempts = 0U;
static uint32_t ev9_preinit_restore_seen_us[EV9_PREINIT_RESTORE_STREAM_COUNT] = {0U};
static uint8_t ev9_preinit_heartbeat_counter = 0U;
static uint32_t ev9_preinit_host_mask = 0U;
static uint32_t ev9_preinit_host_hw_mask = 0U;
static uint32_t ev9_preinit_host_hw_pending_mask = 0U;
static bool ev9_preinit_pending_start = false;
static bool ev9_preinit_restart_used = false;
static bool ev9_preinit_ignition_prev = false;
static bool ev9_preinit_ignition_low_pending = false;
static bool ev9_preinit_ignition_low_handoff_candidate = false;
static bool ev9_preinit_off_latched = false;
static bool ev9_preinit_warm_rearm_candidate = false;
static bool ev9_preinit_session_in_flight = false;
static bool ev9_preinit_comm_control_queued = false;
static bool ev9_preinit_comm_control_in_flight = false;
static bool ev9_preinit_comm_control_unresolved = false;
static bool ev9_preinit_restore_queued = false;
static bool ev9_preinit_restore_response_confirmed = false;
static bool ev9_preinit_nrc_retry_pending = false;
static bool ev9_preinit_rearm_on_next_can = false;
static bool ev9_preinit_restore_fallback_active = false;
static bool ev9_preinit_host_tx_quarantine = false;
static bool ev9_preinit_host_watchdog_quarantine = false;
static bool ev9_preinit_cancel_tx_pending = false;
static bool ev9_preinit_cancel_rearm_after = false;
static bool ev9_preinit_crc_initialized = false;
static bool ev9_preinit_release_requested = false;
static bool ev9_preinit_release_complete = false;
static bool ev9_preinit_release_cleanup_pending = false;
static bool ev9_preinit_recovery_restore = false;
static bool ev9_preinit_can_reset_failed = false;
static bool ev9_preinit_status_snapshot_valid = false;
static bool ev9_preinit_host_heartbeat_hw_pending = false;
static bool ev9_preinit_host_tp_hw_pending = false;
static bool ev9_preinit_steering_angle_valid = false;
static uint16_t ev9_preinit_steering_angle_raw = 0U;

static uint32_t ev9_preinit_cycle_started_us = 0U;
static uint32_t ev9_preinit_first_can_us = 0U;
static uint32_t ev9_preinit_state_started_us = 0U;
static uint32_t ev9_preinit_trigger_us = 0U;
static uint32_t ev9_preinit_first_ecan_us = 0U;
static uint32_t ev9_preinit_wheel_speeds_us = 0U;
static uint32_t ev9_preinit_driver_braking_us = 0U;
static uint32_t ev9_preinit_last_driver_braking_us = 0U;
static uint32_t ev9_preinit_last_remote_wake_us = 0U;
static uint32_t ev9_preinit_steering_angle_us = 0U;
static uint32_t ev9_preinit_climate_takeover_us = 0U;
static uint32_t ev9_preinit_pre_ready_us = 0U;
static uint32_t ev9_preinit_ignition_us = 0U;
static uint32_t ev9_preinit_ignition_low_since_us = 0U;
static uint32_t ev9_preinit_session_request_us = 0U;
static uint32_t ev9_preinit_session_response_us = 0U;
static uint32_t ev9_preinit_comm_control_us = 0U;
static uint32_t ev9_preinit_comm_control_response_us = 0U;
static uint32_t ev9_preinit_last_powertrain_us = 0U;
static uint32_t ev9_preinit_ready_us = 0U;
static uint32_t ev9_preinit_outcome_us = 0U;
static uint32_t ev9_preinit_last_vehicle_frame_us = 0U;
static uint32_t ev9_preinit_last_critical_adas_us = 0U;
static uint32_t ev9_preinit_reappear_started_us = 0U;
static uint32_t ev9_preinit_last_heartbeat_rx_us = 0U;
static uint32_t ev9_preinit_last_heartbeat_tx_us = 0U;
static uint32_t ev9_preinit_last_heartbeat_attempt_us = 0U;
static uint32_t ev9_preinit_last_can_us = 0U;
static uint32_t ev9_preinit_last_host_heartbeat_us = 0U;
static uint32_t ev9_preinit_last_host_tp_us = 0U;
static uint32_t ev9_preinit_last_host_tx_us = 0U;
static uint32_t ev9_preinit_last_tester_present_us = 0U;
static uint32_t ev9_preinit_first_replacement_us = 0U;
static uint32_t ev9_preinit_suppression_confirmed_us = 0U;
static uint32_t ev9_preinit_handoff_us = 0U;
static uint32_t ev9_preinit_restore_us = 0U;
static uint32_t ev9_preinit_restore_quiesce_us = 0U;
static uint32_t ev9_preinit_last_restore_attempt_us = 0U;
static uint32_t ev9_preinit_abort_us = 0U;
static uint32_t ev9_preinit_release_cleanup_us = 0U;

static CANPacket_t ev9_preinit_heartbeat_packet;
static CANPacket_t ev9_preinit_host_heartbeat_hw_packet;
static CANPacket_t ev9_preinit_host_tp_hw_packet;
static ev9_long_preinit_status_t ev9_preinit_status_snapshot;
static ev9_long_preinit_timing_t ev9_preinit_timing_snapshot;
// Defined by board/main.c. Preinit only invokes this from the main loop, never
// from an FDCAN interrupt.
void set_safety_mode(uint16_t mode, uint16_t param);
bool ev9_preinit_can_tx_idle(uint8_t bus_number);
void ev9_preinit_can_request_tx_reset(uint32_t now_us);
ev9_preinit_can_reset_result_t ev9_preinit_can_service_tx_reset(uint32_t now_us);

static const uint8_t *ev9_preinit_fallback(uint16_t addr);
static void ev9_preinit_publish_bridge(uint32_t now_us);
static void ev9_preinit_schedule_tx_cancel(bool rearm_after);
static bool ev9_preinit_host_lease_fresh(uint32_t now_us);
static bool ev9_preinit_restore_tx_idle(void);
static void ev9_preinit_finish_restore(uint32_t now_us);
static void ev9_preinit_advance_diag(uint32_t now_us);
static bool ev9_preinit_diag_deadline_reached(uint32_t now_us);
static void ev9_preinit_abort(uint32_t now_us);

static bool ev9_preinit_force_neutral_addr(uint16_t addr) {
  return (addr == 0x12AU) || (addr == 0xCBU) || (addr == 0x160U) ||
         (addr == 0x161U) || (addr == 0x162U) || (addr == 0x1A0U) ||
         (addr == 0x1BAU) || (addr == 0x1E5U);
}

static bool ev9_preinit_slow_claim_addr(uint16_t addr) {
  return (addr == 0x345U) || (addr == 0x38CU);
}

static bool ev9_preinit_same_body(const CANPacket_t *first, const CANPacket_t *second) {
  bool same = GET_LEN(first) == GET_LEN(second);
  for (uint8_t i = 3U; same && (i < GET_LEN(first)); i++) {
    same = first->data[i] == second->data[i];
  }
  return same;
}

static bool ev9_preinit_same_packet(const CANPacket_t *first, const CANPacket_t *second) {
  bool same = (first->bus == second->bus) && (first->addr == second->addr) &&
              (first->fd == second->fd) && (GET_LEN(first) == GET_LEN(second));
  for (uint8_t i = 0U; same && (i < GET_LEN(first)); i++) {
    same = first->data[i] == second->data[i];
  }
  return same;
}

static uint8_t ev9_preinit_lifecycle_flags(void) {
  uint8_t flags = 0U;
  flags |= ev9_preinit_release_requested ? EV9_PREINIT_LIFECYCLE_RELEASE_REQUESTED : 0U;
  flags |= ev9_preinit_release_complete ? EV9_PREINIT_LIFECYCLE_RELEASE_COMPLETE : 0U;
  flags |= ev9_preinit_can_reset_failed ? EV9_PREINIT_LIFECYCLE_CAN_RESET_FAILED : 0U;
  return flags;
}

static void ev9_preinit_clear_slow_claim_reservations(bool reset_used) {
  for (uint8_t i = 0U; i < EV9_PREINIT_REPLAY_COUNT; i++) {
    if (ev9_preinit_slow_claim_addr(ev9_preinit_replay[i].addr)) {
      ev9_preinit_replay[i].host_claim_reserved = false;
      if (reset_used) {
        ev9_preinit_replay[i].host_claim_reservation_used = false;
      }
    }
  }
}

static bool ev9_preinit_zero_padding(const CANPacket_t *packet, uint8_t start) {
  bool zero = true;
  for (uint8_t i = start; i < GET_LEN(packet); i++) {
    zero = zero && (packet->data[i] == 0U);
  }
  return zero;
}

static void ev9_preinit_set_bits(uint8_t *data, uint16_t start, uint8_t size, uint32_t value) {
  for (uint8_t i = 0U; i < size; i++) {
    const uint16_t bit = start + i;
    const uint8_t mask = (uint8_t)(1U << (bit % 8U));
    if ((value & (1UL << i)) != 0U) {
      data[bit / 8U] |= mask;
    } else {
      data[bit / 8U] &= (uint8_t)(~mask);
    }
  }
}

static uint32_t ev9_preinit_get_bits(const uint8_t *data, uint16_t start, uint8_t size) {
  uint32_t value = 0U;
  for (uint8_t i = 0U; i < size; i++) {
    const uint16_t bit = start + i;
    if ((data[bit / 8U] & (1U << (bit % 8U))) != 0U) {
      value |= 1UL << i;
    }
  }
  return value;
}

static bool ev9_preinit_wheel_speeds_stationary(const CANPacket_t *packet) {
  return (ev9_preinit_get_bits(packet->data, 64U, 14U) <= EV9_PREINIT_STANDSTILL_RAW_MAX) &&
         (ev9_preinit_get_bits(packet->data, 80U, 14U) <= EV9_PREINIT_STANDSTILL_RAW_MAX) &&
         (ev9_preinit_get_bits(packet->data, 96U, 14U) <= EV9_PREINIT_STANDSTILL_RAW_MAX) &&
         (ev9_preinit_get_bits(packet->data, 112U, 14U) <= EV9_PREINIT_STANDSTILL_RAW_MAX);
}

static bool ev9_preinit_stationary_fresh(uint32_t now_us) {
  return (ev9_preinit_wheel_speeds_us != 0U) &&
         ((ev9_preinit_fingerprint & EV9_FP_STATIONARY) != 0U) &&
         (get_ts_elapsed(now_us, ev9_preinit_wheel_speeds_us) <= EV9_PREINIT_WHEEL_SPEED_FRESH_US);
}

static uint16_t ev9_preinit_crc(const CANPacket_t *packet) {
  const uint8_t len = GET_LEN(packet);
  if ((len == 24U) || (len == 32U)) {
    return (uint16_t)hyundai_common_canfd_compute_checksum(packet);
  }

  uint16_t crc = 0U;
  for (uint8_t i = 2U; i < len; i++) {
    crc = (uint16_t)((crc << 8U) ^ hyundai_canfd_crc_lut[(crc >> 8U) ^ packet->data[i]]);
  }
  crc = (uint16_t)((crc << 8U) ^ hyundai_canfd_crc_lut[(crc >> 8U) ^ (packet->addr & 0xFFU)]);
  crc = (uint16_t)((crc << 8U) ^ hyundai_canfd_crc_lut[(crc >> 8U) ^ ((packet->addr >> 8U) & 0xFFU)]);
  crc ^= (len == 8U) ? 0x5F29U : 0x041DU;
  return crc;
}

static void ev9_preinit_update_crc(CANPacket_t *packet) {
  const uint16_t crc = ev9_preinit_crc(packet);
  packet->data[0] = (uint8_t)(crc & 0xFFU);
  packet->data[1] = (uint8_t)(crc >> 8U);
  can_set_checksum(packet);
}

static CANPacket_t ev9_preinit_make_packet(uint16_t addr, uint8_t bus, uint8_t len, bool fd) {
  CANPacket_t packet = {0};
  packet.fd = fd;
  packet.bus = bus;
  packet.addr = addr;
  for (uint8_t dlc = 0U; dlc < 16U; dlc++) {
    if (dlc_to_len[dlc] == len) {
      packet.data_len_code = dlc;
      break;
    }
  }
  return packet;
}

static bool ev9_preinit_diag_tx_allowed(const CANPacket_t *packet) {
  if (packet->fd || (packet->bus != EV9_PREINIT_BUS_ECAN) ||
      (packet->addr != EV9_PREINIT_DIAG_ADDR) || (GET_LEN(packet) != 8U)) {
    return false;
  }
  const bool session = (packet->data[0] == 2U) && (packet->data[1] == 0x10U) &&
                       ((packet->data[2] == 0x03U) || (packet->data[2] == 0x01U)) &&
                       ev9_preinit_zero_padding(packet, 3U);
  const bool communication = (packet->data[0] == 3U) && (packet->data[1] == 0x28U) &&
                             ((packet->data[2] == 0x01U) || (packet->data[2] == 0x00U)) &&
                             (packet->data[3] == EV9_PREINIT_COMMUNICATION_TYPE) &&
                             ev9_preinit_zero_padding(packet, 4U);
  const bool tester_present = (packet->data[0] == 2U) && (packet->data[1] == 0x3EU) &&
                              (packet->data[2] == 0x80U) &&
                              ev9_preinit_zero_padding(packet, 3U);
  return session || communication || tester_present;
}

static bool ev9_preinit_bridge_tx_allowed(const CANPacket_t *packet) {
  if ((packet->bus == EV9_PREINIT_BUS_RADAR) && packet->fd &&
      (packet->addr == 0x100U) && (GET_LEN(packet) == 24U)) {
    bool body_matches = true;
    for (uint8_t i = 3U; i < 24U; i++) {
      body_matches = body_matches && (packet->data[i] == ev9_preinit_heartbeat_packet.data[i]);
    }
    return body_matches;
  }
  if ((packet->bus != EV9_PREINIT_BUS_ECAN) || !packet->fd) {
    return false;
  }
  bool allowed = false;
  for (uint8_t i = 0U; i < EV9_PREINIT_REPLAY_COUNT; i++) {
    allowed = allowed || ((packet->addr == ev9_preinit_replay[i].addr) &&
                          (GET_LEN(packet) == ev9_preinit_replay[i].len));
  }
  if (!allowed) {
    return false;
  }
  if (ev9_preinit_force_neutral_addr(packet->addr)) {
    const uint8_t *fallback = ev9_preinit_fallback(packet->addr);
    bool neutral_body = fallback != NULL;
    for (uint8_t i = 3U; neutral_body && (i < GET_LEN(packet)); i++) {
      uint8_t expected = fallback[i];
      if ((packet->addr == 0x161U) && (i == 3U)) {
        expected = (ev9_preinit_state == EV9_PREINIT_HANDOFF) ? 0x01U : 0x41U;
      } else if ((packet->addr == 0x161U) && (i == 4U)) {
        expected &= 0xFEU;
      }
      neutral_body = packet->data[i] == expected;
    }
    if (!neutral_body) {
      return false;
    }
  }
  if (packet->addr == 0x1A0U) {
    return (ev9_preinit_get_bits(packet->data, 68U, 3U) == 0U) &&
           (ev9_preinit_get_bits(packet->data, 128U, 11U) == 1023U) &&
           (ev9_preinit_get_bits(packet->data, 140U, 11U) == 1023U) &&
           (ev9_preinit_get_bits(packet->data, 184U, 1U) == 0U);
  }
  if (packet->addr == 0x12AU) {
    return (ev9_preinit_get_bits(packet->data, 52U, 1U) == 0U) &&
           (ev9_preinit_get_bits(packet->data, 62U, 1U) == 0U) &&
           (ev9_preinit_get_bits(packet->data, 65U, 3U) == 0U);
  }
  if (packet->addr == 0xCBU) {
    return (ev9_preinit_get_bits(packet->data, 24U, 4U) == 0U) &&
           (ev9_preinit_get_bits(packet->data, 28U, 4U) == 1U) &&
           (ev9_preinit_get_bits(packet->data, 48U, 8U) == 0U) &&
           (ev9_preinit_get_bits(packet->data, 56U, 2U) == 0U) &&
           (ev9_preinit_get_bits(packet->data, 64U, 8U) == 0U);
  }
  return true;
}

static bool ev9_preinit_internal_send(CANPacket_t *packet, uint8_t bus) {
  packet->bus = bus;
  can_set_checksum(packet);
  const bool allowed = ev9_preinit_diag_tx_allowed(packet) || ev9_preinit_bridge_tx_allowed(packet);
  bool queued = false;
  if (allowed) {
    queued = can_send_ev9_preinit_with_result(packet, bus);
  }
  if (!allowed || !queued) {
    ev9_preinit_flags |= EV9_PREINIT_FLAG_INTERNAL_TX_REJECTED;
  }
  return queued;
}

static void ev9_preinit_neutralize(CANPacket_t *packet) {
  if (packet->addr == 0x1A0U) {
    ev9_preinit_set_bits(packet->data, 68U, 3U, 0U);
    ev9_preinit_set_bits(packet->data, 128U, 11U, 1023U);
    ev9_preinit_set_bits(packet->data, 140U, 11U, 1023U);
    ev9_preinit_set_bits(packet->data, 184U, 1U, 0U);
  } else if (packet->addr == 0x12AU) {
    ev9_preinit_set_bits(packet->data, 52U, 1U, 0U);
    ev9_preinit_set_bits(packet->data, 62U, 1U, 0U);
    ev9_preinit_set_bits(packet->data, 65U, 3U, 0U);
  } else if (packet->addr == 0xCBU) {
    ev9_preinit_set_bits(packet->data, 24U, 4U, 0U);
    ev9_preinit_set_bits(packet->data, 28U, 4U, 1U);
    ev9_preinit_set_bits(packet->data, 48U, 8U, 0U);
    ev9_preinit_set_bits(packet->data, 56U, 2U, 0U);
    ev9_preinit_set_bits(packet->data, 64U, 8U, 0U);
  } else if (packet->addr == 0x161U) {
    // Captured OEM 0x161 bodies normally carry no orange status bits. Make
    // resident ownership visible on every replay, not only on fallback or
    // host-generated bodies: FCA remains orange for the suppressed interval,
    // and LKA remains orange until the first complete host handoff.
    packet->data[3] = (ev9_preinit_state == EV9_PREINIT_HANDOFF) ? 0x01U : 0x41U;
    packet->data[4] &= 0xFEU;
  } else {
  }
}

static const uint8_t *ev9_preinit_fallback(uint16_t addr) {
  const uint8_t *fallback = NULL;
  switch (addr) {
    case 0x12AU: fallback = ev9_preinit_fallback_12a; break;
    case 0xCBU: fallback = ev9_preinit_fallback_cb; break;
    case 0x160U: fallback = ev9_preinit_fallback_160; break;
    case 0x161U: fallback = ev9_preinit_fallback_161; break;
    case 0x162U: fallback = ev9_preinit_fallback_162; break;
    case 0x1A0U: fallback = ev9_preinit_fallback_1a0; break;
    case 0x1BAU: fallback = ev9_preinit_fallback_1ba; break;
    case 0x1DAU: fallback = ev9_preinit_fallback_1da; break;
    case 0x1E0U: fallback = ev9_preinit_fallback_1e0; break;
    case 0x1E5U: fallback = ev9_preinit_fallback_1e5; break;
    case 0x1EAU: fallback = ev9_preinit_fallback_1ea; break;
    case 0x200U: fallback = ev9_preinit_fallback_200; break;
    case 0x345U: fallback = ev9_preinit_fallback_345; break;
    case 0x38CU: fallback = ev9_preinit_fallback_38c; break;
    default: break;
  }
  return fallback;
}

static bool ev9_preinit_powertrain_terminal(void) {
  return (ev9_preinit_powertrain_state == 0x51U) || (ev9_preinit_powertrain_state == 0x55U);
}

static bool ev9_preinit_is_valid_canfd(const CANPacket_t *packet) {
  if (!packet->fd || (GET_LEN(packet) < 8U)) {
    return false;
  }
  const uint16_t checksum = (uint16_t)packet->data[0] | ((uint16_t)packet->data[1] << 8U);
  return ev9_preinit_crc(packet) == checksum;
}

static bool ev9_preinit_matches_identity_body(const CANPacket_t *packet,
                                              const uint8_t *mask,
                                              const uint8_t *value) {
  bool matches = true;
  for (uint8_t i = 3U; matches && (i < GET_LEN(packet)); i++) {
    matches = (packet->data[i] & mask[i]) == value[i];
  }
  return matches;
}

static bool ev9_preinit_is_heartbeat_tuple(const CANPacket_t *packet) {
  bool matches = (packet->bus == EV9_PREINIT_BUS_RADAR) && (packet->addr == 0x100U) &&
                 (GET_LEN(packet) == 24U);
  return matches && ev9_preinit_matches_identity_body(
    packet, ev9_preinit_heartbeat_identity_mask, ev9_preinit_heartbeat_identity_value);
}

static bool ev9_preinit_is_powertrain_identity_tuple(const CANPacket_t *packet) {
  return (packet->bus == EV9_PREINIT_BUS_ECAN) && (packet->addr == 0x35U) &&
         (GET_LEN(packet) == 32U) && ev9_preinit_matches_identity_body(
           packet, ev9_preinit_powertrain_identity_mask, ev9_preinit_powertrain_identity_value);
}

static bool ev9_preinit_is_scc_identity_tuple(const CANPacket_t *packet) {
  return (packet->bus == EV9_PREINIT_BUS_ECAN) && (packet->addr == 0xCBU) &&
         (GET_LEN(packet) == 24U) && ev9_preinit_matches_identity_body(
           packet, ev9_preinit_scc_identity_mask, ev9_preinit_scc_identity_value);
}

static bool ev9_preinit_is_diag_response_tuple(const CANPacket_t *packet) {
  // The EV9 returns ISO-TP diagnostic payloads in 8-byte CAN-FD-marked frames
  // on E-CAN. Route 17a/17b accepted either controller format; requiring the
  // classic-CAN flag rejects a wire-valid 50 03 before it can chain 28 01 01.
  return (packet->bus == EV9_PREINIT_BUS_ECAN) &&
         (packet->addr == EV9_PREINIT_DIAG_RESP_ADDR) && (GET_LEN(packet) == 8U) &&
         (packet->data[0] >= 2U) && (packet->data[0] <= 7U);
}

static bool ev9_preinit_is_relevant_canfd_tuple(const CANPacket_t *packet) {
  if (!packet->fd) {
    return false;
  }
  if (packet->bus == EV9_PREINIT_BUS_RADAR) {
    return ((packet->addr == 0x100U) && (GET_LEN(packet) == 24U)) ||
           ((packet->addr == 0x500U) && (GET_LEN(packet) == 16U));
  }
  if (packet->bus != EV9_PREINIT_BUS_ECAN) {
    return false;
  }

  switch (packet->addr) {
    case 0x35U: return GET_LEN(packet) == 32U;
    case 0xA0U: return GET_LEN(packet) == 24U;
    case 0xCBU: return GET_LEN(packet) == 24U;
    case 0x12AU: return GET_LEN(packet) == 16U;
    case 0x160U: return GET_LEN(packet) == 16U;
    case 0x161U: return GET_LEN(packet) == 32U;
    case 0x162U: return GET_LEN(packet) == 32U;
    case 0x175U: return GET_LEN(packet) == 24U;
    case 0x1A0U: return GET_LEN(packet) == 32U;
    case 0x1BAU: return GET_LEN(packet) == 24U;
    case 0x1DAU: return GET_LEN(packet) == 32U;
    case 0x1E0U: return GET_LEN(packet) == 16U;
    case 0x1E5U: return GET_LEN(packet) == 16U;
    case 0x1EAU: return GET_LEN(packet) == 32U;
    case 0x200U: return GET_LEN(packet) == 8U;
    case 0x345U: return GET_LEN(packet) == 8U;
    case 0x38CU: return GET_LEN(packet) == 32U;
    default: return false;
  }
}

static bool ev9_preinit_is_critical_adas(const CANPacket_t *packet) {
  if ((packet->bus == EV9_PREINIT_BUS_RADAR) &&
      (((packet->addr == 0x100U) && (GET_LEN(packet) == 24U)) ||
       ((packet->addr == 0x500U) && (GET_LEN(packet) == 16U)))) {
    return true;
  }
  return (packet->bus == EV9_PREINIT_BUS_ECAN) &&
         (((packet->addr == 0x12AU) && (GET_LEN(packet) == 16U)) ||
          ((packet->addr == 0xCBU) && (GET_LEN(packet) == 24U)) ||
          ((packet->addr == 0x160U) && (GET_LEN(packet) == 16U)) ||
          ((packet->addr == 0x1A0U) && (GET_LEN(packet) == 32U)));
}

static void ev9_preinit_seed_missing_fallbacks(uint32_t now_us) {
  for (uint8_t i = 0U; i < EV9_PREINIT_REPLAY_COUNT; i++) {
    ev9_preinit_replay_t *replay = &ev9_preinit_replay[i];
    if (!replay->captured && (ev9_preinit_fallback(replay->addr) != NULL)) {
      // Treat the fallback as freshly observed. This prevents the first bridge
      // pass from bursting slow streams which were never seen on this wake.
      replay->captured = true;
      replay->last_rx_us = now_us;
    }
  }
}

static bool ev9_preinit_send_diag_request(uint8_t service, uint8_t subfunction, uint8_t control_type) {
  const bool off_cleanup = ((service == 0x28U) && (subfunction == 0x00U) &&
                            (control_type == EV9_PREINIT_COMMUNICATION_TYPE)) ||
                           ((service == 0x10U) && (subfunction == 0x01U));
  if (ev9_preinit_off_latched && !off_cleanup) {
    return false;
  }
  CANPacket_t packet = ev9_preinit_make_packet(EV9_PREINIT_DIAG_ADDR, EV9_PREINIT_BUS_ECAN, 8U, false);
  if (service == 0x28U) {
    packet.data[0] = 3U;
    packet.data[1] = service;
    packet.data[2] = subfunction;
    packet.data[3] = control_type;
  } else {
    packet.data[0] = 2U;
    packet.data[1] = service;
    packet.data[2] = subfunction;
  }
  return ev9_preinit_internal_send(&packet, EV9_PREINIT_BUS_ECAN);
}

static void ev9_preinit_send_session(uint32_t now_us) {
  if (!ev9_preinit_stationary_fresh(now_us)) {
    ev9_preinit_abort(now_us);
    return;
  }
  ev9_preinit_pending_start = false;
  ev9_preinit_state = EV9_PREINIT_WAIT_SESSION;
  ev9_preinit_state_started_us = now_us;
  ev9_preinit_session_in_flight = false;
  if (ev9_preinit_send_diag_request(0x10U, 0x03U, 0U)) {
    ev9_preinit_last_service = 0x10U;
    ev9_preinit_last_response = 0U;
    ev9_preinit_last_nrc = 0U;
    ev9_preinit_nrc_retry_pending = false;
    ev9_preinit_session_in_flight = true;
    ev9_preinit_attempts += 1U;
    if (ev9_preinit_session_request_us == 0U) {
      ev9_preinit_session_request_us = now_us;
    }
  }
}

static void ev9_preinit_send_comm_control(uint32_t now_us) {
  if (!ev9_preinit_stationary_fresh(now_us)) {
    // The extended session may already be active, but suppression was never
    // requested. Return to stock's default session and end this epoch without
    // emitting 28 01 01 while motion is observed or speed proof is stale.
    (void)ev9_preinit_send_diag_request(0x10U, 0x01U, 0U);
    ev9_preinit_abort(now_us);
    return;
  }
  ev9_preinit_state = EV9_PREINIT_WAIT_COMM_CONTROL;
  ev9_preinit_state_started_us = now_us;
  ev9_preinit_comm_control_in_flight = false;
  const bool queued = ev9_preinit_send_diag_request(0x28U, 0x01U, EV9_PREINIT_COMMUNICATION_TYPE);
  if (queued) {
    ev9_preinit_last_service = 0x28U;
    ev9_preinit_last_response = 0U;
    ev9_preinit_last_nrc = 0U;
    ev9_preinit_nrc_retry_pending = false;
    ev9_preinit_comm_control_in_flight = true;
    ev9_preinit_comm_control_unresolved = true;
    ev9_preinit_attempts += 1U;
    if (!ev9_preinit_comm_control_queued) {
      ev9_preinit_comm_control_queued = true;
      ev9_preinit_comm_control_us = now_us;
    }
  }
}

static bool ev9_preinit_return_to_default_session(void) {
  return ev9_preinit_send_diag_request(0x10U, 0x01U, 0U);
}

static void ev9_preinit_enter_aborted(uint32_t now_us) {
  ev9_preinit_clear_slow_claim_reservations(false);
  ev9_preinit_pending_start = false;
  ev9_preinit_session_in_flight = false;
  ev9_preinit_comm_control_in_flight = false;
  ev9_preinit_comm_control_unresolved = false;
  ev9_preinit_state = EV9_PREINIT_ABORTED;
  ev9_preinit_state_started_us = now_us;
  ev9_preinit_abort_us = now_us;
  ev9_preinit_outcome_us = now_us;
  ev9_preinit_flags &= (uint8_t)~(EV9_PREINIT_FLAG_BRIDGE_ACTIVE |
                                  EV9_PREINIT_FLAG_SUPPRESSION_CONFIRMED |
                                  EV9_PREINIT_FLAG_HOST_HANDOFF);
}

static void ev9_preinit_abort(uint32_t now_us) {
  ev9_preinit_ignition_low_handoff_candidate = false;
  ev9_preinit_warm_rearm_candidate = false;
  ev9_preinit_enter_aborted(now_us);
}

static void ev9_preinit_try_restore(uint32_t now_us) {
  if ((ev9_preinit_restore_attempts >= EV9_PREINIT_RESTORE_MAX_ATTEMPTS) ||
      (ev9_preinit_state != EV9_PREINIT_RESTORING) || ev9_preinit_rearm_on_next_can ||
      !ev9_preinit_can_tx_idle(EV9_PREINIT_BUS_RADAR) ||
      !ev9_preinit_can_tx_idle(EV9_PREINIT_BUS_ECAN)) {
    return;
  }

  ev9_preinit_last_restore_attempt_us = now_us;
  if (ev9_preinit_send_diag_request(0x28U, 0x00U, EV9_PREINIT_COMMUNICATION_TYPE)) {
    // Bound wire-visible restore requests, not local queue-full failures. A
    // rejected enqueue remains retryable after the throttle interval.
    ev9_preinit_restore_attempts += 1U;
    if (!ev9_preinit_restore_queued) {
      ev9_preinit_restore_us = now_us;
    }
    ev9_preinit_restore_queued = true;
    ev9_preinit_flags |= EV9_PREINIT_FLAG_RESTORE_SENT;
  }
}

static void ev9_preinit_begin_restore(uint32_t now_us) {
  if (ev9_preinit_state != EV9_PREINIT_RESTORING) {
    ev9_preinit_clear_slow_claim_reservations(false);
    const bool bridge_owned = (ev9_preinit_flags & EV9_PREINIT_FLAG_BRIDGE_ACTIVE) != 0U;
    ev9_preinit_pending_start = false;
    ev9_preinit_state = EV9_PREINIT_RESTORING;
    ev9_preinit_state_started_us = now_us;
    ev9_preinit_restore_us = 0U;
    ev9_preinit_restore_quiesce_us = now_us;
    ev9_preinit_last_restore_attempt_us = 0U;
    ev9_preinit_restore_attempts = 0U;
    ev9_preinit_restore_queued = false;
    ev9_preinit_restore_response_confirmed = false;
    ev9_preinit_rearm_on_next_can = false;
    ev9_preinit_restore_fallback_active = false;
    ev9_preinit_cancel_tx_pending = false;
    ev9_preinit_cancel_rearm_after = false;
    ev9_preinit_restore_seen = 0U;
    for (uint8_t i = 0U; i < EV9_PREINIT_RESTORE_STREAM_COUNT; i++) {
      ev9_preinit_restore_seen_us[i] = 0U;
    }
    // A queued 0x28 without an exact positive response is not ownership. Do
    // not collide with a still-live OEM publisher while restoring ambiguity.
    // A bridge established by exact 68 01 remains resident until stock traffic
    // proves that restore converged.
    if (!bridge_owned) {
      ev9_preinit_flags &= (uint8_t)~EV9_PREINIT_FLAG_BRIDGE_ACTIVE;
    }
    ev9_preinit_flags &= (uint8_t)~EV9_PREINIT_FLAG_RESTORE_SENT;
    ev9_preinit_flags &= (uint8_t)~EV9_PREINIT_FLAG_HOST_HANDOFF;
    // RESTORING is a TX-quiescent phase. No bridge or host replacement is
    // enqueued after this point; 28 00 is allowed only after both software and
    // FDCAN hardware queues prove empty.
    ev9_preinit_last_tester_present_us = now_us;
  }
}

static ev9_long_preinit_status_t ev9_preinit_current_status(void) {
  return (ev9_long_preinit_status_t) {
    .version = EV9_LONG_PREINIT_STATUS_VERSION,
    .state = (uint8_t)ev9_preinit_state,
    .fingerprint = ev9_preinit_fingerprint,
    .attempts = ev9_preinit_attempts,
    .last_service = ev9_preinit_last_service,
    .last_response = ev9_preinit_last_response,
    .last_nrc = ev9_preinit_last_nrc,
    .communication_type = EV9_PREINIT_COMMUNICATION_TYPE,
    .trigger = (uint8_t)ev9_preinit_trigger,
    .first_ecan_len = ev9_preinit_first_ecan_len,
    .powertrain_state = ev9_preinit_powertrain_state,
    .powertrain_boot_state = ev9_preinit_powertrain_boot_state,
    .powertrain_init_state = ev9_preinit_powertrain_init_state,
    .flags = ev9_preinit_flags,
    .first_ecan_addr = ev9_preinit_first_ecan_addr,
    .first_can_us = ev9_preinit_first_can_us,
    .state_started_us = ev9_preinit_state_started_us,
    .trigger_us = ev9_preinit_trigger_us,
    .first_ecan_us = ev9_preinit_first_ecan_us,
    .driver_braking_us = ev9_preinit_driver_braking_us,
    .pre_ready_us = ev9_preinit_pre_ready_us,
    .ignition_us = ev9_preinit_ignition_us,
    .session_response_us = ev9_preinit_session_response_us,
    .comm_control_us = ev9_preinit_comm_control_us,
    .last_powertrain_us = ev9_preinit_last_powertrain_us,
    .ready_us = ev9_preinit_ready_us,
    .outcome_us = ev9_preinit_outcome_us,
  };
}

static ev9_long_preinit_timing_t ev9_preinit_current_timing(void) {
  return (ev9_long_preinit_timing_t) {
    .version = EV9_LONG_PREINIT_STATUS_VERSION,
    .page = EV9_LONG_PREINIT_TIMING_PAGE,
    .flags = ev9_preinit_flags,
    // v4 reserved byte is now a backwards-compatible lifecycle bitfield.
    .reserved = ev9_preinit_lifecycle_flags(),
    .cycle_started_us = ev9_preinit_cycle_started_us,
    .session_request_us = ev9_preinit_session_request_us,
    .session_response_us = ev9_preinit_session_response_us,
    .comm_control_us = ev9_preinit_comm_control_us,
    .comm_control_response_us = ev9_preinit_comm_control_response_us,
    .last_critical_adas_us = ev9_preinit_last_critical_adas_us,
    .first_replacement_us = ev9_preinit_first_replacement_us,
    .suppression_confirmed_us = ev9_preinit_suppression_confirmed_us,
    .ready_us = ev9_preinit_ready_us,
    .handoff_us = ev9_preinit_handoff_us,
    .restore_us = ev9_preinit_restore_us,
    .abort_us = ev9_preinit_abort_us,
    .last_host_tx_us = ev9_preinit_last_host_tx_us,
    .last_tester_present_us = ev9_preinit_last_tester_present_us,
    .last_vehicle_frame_us = ev9_preinit_last_vehicle_frame_us,
  };
}

static void ev9_preinit_latch_status_snapshot(void) {
  ENTER_CRITICAL();
  ev9_preinit_status_snapshot = ev9_preinit_current_status();
  ev9_preinit_timing_snapshot = ev9_preinit_current_timing();
  ev9_preinit_status_snapshot_valid = true;
  EXIT_CRITICAL();
}

static ev9_long_preinit_status_t ev9_long_preinit_get_status(void) {
  // Page zero starts a coherent two-page snapshot. Page one consumes this
  // latch; a second page-zero read starts the host's verification snapshot.
  ev9_preinit_latch_status_snapshot();
  return ev9_preinit_status_snapshot;
}

static ev9_long_preinit_timing_t ev9_long_preinit_get_timing(void) {
  if (!ev9_preinit_status_snapshot_valid) {
    ev9_preinit_latch_status_snapshot();
  }
  ENTER_CRITICAL();
  const ev9_long_preinit_timing_t timing = ev9_preinit_timing_snapshot;
  ev9_preinit_status_snapshot_valid = false;
  EXIT_CRITICAL();
  return timing;
}

static void ev9_long_preinit_reset_cycle(void) {
  ev9_preinit_state = EV9_PREINIT_COLLECTING;
  ev9_preinit_trigger = EV9_PREINIT_TRIGGER_NONE;
  ev9_preinit_flags = 0U;
  ev9_preinit_fingerprint = 0U;
  ev9_preinit_attempts = 0U;
  ev9_preinit_last_service = 0U;
  ev9_preinit_last_response = 0U;
  ev9_preinit_last_nrc = 0U;
  ev9_preinit_first_ecan_len = 0U;
  ev9_preinit_first_ecan_addr = 0U;
  ev9_preinit_powertrain_state = 0U;
  ev9_preinit_powertrain_boot_state = 0U;
  ev9_preinit_powertrain_init_state = 0U;
  ev9_preinit_restore_seen = 0U;
  ev9_preinit_restore_attempts = 0U;
  for (uint8_t i = 0U; i < EV9_PREINIT_RESTORE_STREAM_COUNT; i++) {
    ev9_preinit_restore_seen_us[i] = 0U;
  }
  ev9_preinit_heartbeat_counter = 0U;
  ev9_preinit_host_mask = 0U;
  ev9_preinit_host_hw_mask = 0U;
  ev9_preinit_host_hw_pending_mask = 0U;
  ev9_preinit_pending_start = false;
  ev9_preinit_restart_used = false;
  ev9_preinit_ignition_prev = false;
  ev9_preinit_ignition_low_pending = false;
  ev9_preinit_ignition_low_handoff_candidate = false;
  ev9_preinit_off_latched = false;
  ev9_preinit_warm_rearm_candidate = false;
  ev9_preinit_session_in_flight = false;
  ev9_preinit_comm_control_queued = false;
  ev9_preinit_comm_control_in_flight = false;
  ev9_preinit_comm_control_unresolved = false;
  ev9_preinit_restore_queued = false;
  ev9_preinit_restore_response_confirmed = false;
  ev9_preinit_nrc_retry_pending = false;
  ev9_preinit_rearm_on_next_can = false;
  ev9_preinit_restore_fallback_active = false;
  ev9_preinit_host_tx_quarantine = false;
  ev9_preinit_host_watchdog_quarantine = false;
  ev9_preinit_cancel_tx_pending = false;
  ev9_preinit_cancel_rearm_after = false;
  ev9_preinit_release_requested = false;
  ev9_preinit_release_complete = false;
  ev9_preinit_release_cleanup_pending = false;
  ev9_preinit_recovery_restore = false;
  ev9_preinit_can_reset_failed = false;
  ev9_preinit_host_heartbeat_hw_pending = false;
  ev9_preinit_host_tp_hw_pending = false;
  ev9_preinit_steering_angle_valid = false;
  ev9_preinit_steering_angle_raw = 0U;
  ev9_preinit_cycle_started_us = 0U;
  ev9_preinit_first_can_us = 0U;
  ev9_preinit_state_started_us = 0U;
  ev9_preinit_trigger_us = 0U;
  ev9_preinit_first_ecan_us = 0U;
  ev9_preinit_wheel_speeds_us = 0U;
  ev9_preinit_driver_braking_us = 0U;
  ev9_preinit_last_driver_braking_us = 0U;
  ev9_preinit_last_remote_wake_us = 0U;
  ev9_preinit_steering_angle_us = 0U;
  ev9_preinit_climate_takeover_us = 0U;
  ev9_preinit_pre_ready_us = 0U;
  ev9_preinit_ignition_us = 0U;
  ev9_preinit_ignition_low_since_us = 0U;
  ev9_preinit_session_request_us = 0U;
  ev9_preinit_session_response_us = 0U;
  ev9_preinit_comm_control_us = 0U;
  ev9_preinit_comm_control_response_us = 0U;
  ev9_preinit_last_powertrain_us = 0U;
  ev9_preinit_ready_us = 0U;
  ev9_preinit_outcome_us = 0U;
  ev9_preinit_last_vehicle_frame_us = 0U;
  ev9_preinit_last_critical_adas_us = 0U;
  ev9_preinit_reappear_started_us = 0U;
  ev9_preinit_last_heartbeat_rx_us = 0U;
  ev9_preinit_last_heartbeat_tx_us = 0U;
  ev9_preinit_last_heartbeat_attempt_us = 0U;
  ev9_preinit_last_can_us = 0U;
  ev9_preinit_last_host_heartbeat_us = 0U;
  ev9_preinit_last_host_tp_us = 0U;
  ev9_preinit_last_host_tx_us = 0U;
  ev9_preinit_last_tester_present_us = 0U;
  ev9_preinit_first_replacement_us = 0U;
  ev9_preinit_suppression_confirmed_us = 0U;
  ev9_preinit_handoff_us = 0U;
  ev9_preinit_restore_us = 0U;
  ev9_preinit_restore_quiesce_us = 0U;
  ev9_preinit_last_restore_attempt_us = 0U;
  ev9_preinit_abort_us = 0U;
  ev9_preinit_release_cleanup_us = 0U;

  ev9_preinit_heartbeat_packet = ev9_preinit_make_packet(0x100U, EV9_PREINIT_BUS_RADAR, 24U, true);
  (void)memcpy(ev9_preinit_heartbeat_packet.data, ev9_preinit_heartbeat_template,
               sizeof(ev9_preinit_heartbeat_template));
  for (uint8_t i = 0U; i < EV9_PREINIT_REPLAY_COUNT; i++) {
    ev9_preinit_replay[i].last_rx_us = 0U;
    ev9_preinit_replay[i].last_tx_us = 0U;
    ev9_preinit_replay[i].last_attempt_us = 0U;
    ev9_preinit_replay[i].last_host_tx_us = 0U;
    ev9_preinit_replay[i].captured = false;
    ev9_preinit_replay[i].host_claim_reservation_used = false;
    ev9_preinit_replay[i].host_claim_reserved = false;
    ev9_preinit_replay[i].host_hw_pending = false;
    const uint8_t *fallback = ev9_preinit_fallback(ev9_preinit_replay[i].addr);
    if (fallback != NULL) {
      ev9_preinit_replay[i].packet = ev9_preinit_make_packet(ev9_preinit_replay[i].addr,
        EV9_PREINIT_BUS_ECAN, ev9_preinit_replay[i].len, true);
      (void)memcpy(ev9_preinit_replay[i].packet.data, fallback, ev9_preinit_replay[i].len);
    }
  }
}

static void ev9_long_preinit_init(void) {
  // The CRC table is profile-static. Rebuilding it from the first RX interrupt
  // of every wake epoch adds thousands of operations to the highest-rate path.
  if (!ev9_preinit_crc_initialized) {
    gen_crc_lookup_table_16(0x1021U, hyundai_canfd_crc_lut);
    ev9_preinit_crc_initialized = true;
  }
  ev9_preinit_status_snapshot_valid = false;
  ev9_long_preinit_reset_cycle();
}

static void ev9_preinit_update_wheel_speed_proof(const CANPacket_t *packet, uint32_t now_us) {
  ev9_preinit_fingerprint |= EV9_FP_WHEEL_SPEEDS;
  ev9_preinit_wheel_speeds_us = now_us;
  if (ev9_preinit_wheel_speeds_stationary(packet)) {
    ev9_preinit_fingerprint |= EV9_FP_STATIONARY;
  } else if ((ev9_preinit_state == EV9_PREINIT_COLLECTING) ||
             (ev9_preinit_state == EV9_PREINIT_WAIT_SESSION) ||
             (ev9_preinit_state == EV9_PREINIT_WAIT_COMM_CONTROL) ||
             (ev9_preinit_state == EV9_PREINIT_READY_PENDING_RESPONSE) ||
             (ev9_preinit_state == EV9_PREINIT_ABORTED)) {
    ev9_preinit_fingerprint &= (uint8_t)~EV9_FP_STATIONARY;
  } else {
    // Suppression already owns the ECU after an exact stationary request.
    // Motion is expected from this point onward and must not veto ACTIVE or
    // the later stock-like host handoff.
  }
}

static void ev9_preinit_capture_frame(const CANPacket_t *packet, bool valid_canfd_crc,
                                      bool valid_heartbeat, uint32_t now_us) {
  if (valid_heartbeat) {
    ev9_preinit_fingerprint |= EV9_FP_HEARTBEAT;
    // The physical 0x100 is an EV9 identity/start cue, but it is not the
    // ADAS_DRV body the front radar accepts as its host-alive heartbeat.
    // Replacing the verified replay template with that physical body leaves
    // every MRR35 track in STATE=0 after a cold preinit knockout. Preserve the
    // route-verified radar-alive body and inherit only rolling continuity and
    // the two live pedal bits that the host also updates after handoff.
    ev9_preinit_heartbeat_packet.data[2] = packet->data[2];
    ev9_preinit_heartbeat_packet.data[4] =
      (ev9_preinit_heartbeat_packet.data[4] & 0xFEU) | (packet->data[4] & 0x01U);
    ev9_preinit_heartbeat_packet.data[22] =
      (ev9_preinit_heartbeat_packet.data[22] & 0xFEU) | (packet->data[22] & 0x01U);
    ev9_preinit_heartbeat_counter = packet->data[2] + 1U;
    ev9_preinit_last_heartbeat_rx_us = now_us;
  } else if (valid_canfd_crc && ev9_preinit_is_powertrain_identity_tuple(packet)) {
    ev9_preinit_fingerprint |= EV9_FP_POWERTRAIN;
  } else if (valid_canfd_crc && ev9_preinit_is_scc_identity_tuple(packet)) {
    ev9_preinit_fingerprint |= EV9_FP_SCC_CONTROL;
  } else if (valid_canfd_crc && (packet->bus == EV9_PREINIT_BUS_ECAN) &&
             (packet->addr == 0xA0U) && (GET_LEN(packet) == 24U)) {
    ev9_preinit_update_wheel_speed_proof(packet, now_us);
  } else if (valid_canfd_crc && (packet->bus == EV9_PREINIT_BUS_ECAN) &&
             (packet->addr == 0x1A0U) && (GET_LEN(packet) == 32U)) {
    ev9_preinit_fingerprint |= EV9_FP_SCC_STATUS;
  } else if (valid_canfd_crc && (packet->bus == EV9_PREINIT_BUS_ECAN) &&
             (packet->addr == 0x160U) && (GET_LEN(packet) == 16U)) {
    ev9_preinit_fingerprint |= EV9_FP_FCA_STATUS;
  } else if (valid_canfd_crc && (packet->bus == EV9_PREINIT_BUS_ECAN) &&
             (packet->addr == 0x1BAU) && (GET_LEN(packet) == 24U)) {
    ev9_preinit_fingerprint |= EV9_FP_BSM_STATUS;
  } else {
  }

  if (valid_canfd_crc && (packet->bus == EV9_PREINIT_BUS_ECAN)) {
    if (ev9_preinit_first_ecan_us == 0U) {
      ev9_preinit_first_ecan_us = now_us;
      ev9_preinit_first_ecan_addr = packet->addr;
      ev9_preinit_first_ecan_len = GET_LEN(packet);
    }
    for (uint8_t i = 0U; i < EV9_PREINIT_REPLAY_COUNT; i++) {
      ev9_preinit_replay_t *replay = &ev9_preinit_replay[i];
      if ((packet->addr == replay->addr) && (GET_LEN(packet) == replay->len)) {
        const uint8_t *fallback = ev9_preinit_fallback(packet->addr);
        replay->packet = ev9_preinit_make_packet(packet->addr, EV9_PREINIT_BUS_ECAN, replay->len, true);
        // Actuating/object-bearing frames always use a neutral body. Other
        // status frames retain the current vehicle body for continuity.
        const bool force_neutral = ev9_preinit_force_neutral_addr(packet->addr);
        if (force_neutral && (fallback != NULL)) {
          (void)memcpy(replay->packet.data, fallback, replay->len);
          replay->packet.data[2] = packet->data[2];
        } else {
          replay->packet = *packet;
        }
        replay->captured = true;
        replay->last_rx_us = now_us;
      }
    }
  }
}

static void ev9_preinit_dispatch_start(void) {
  if (current_safety_mode != SAFETY_NOOUTPUT) {
    // Pandad can still be in temporary ELM327 firmware-query safety when the
    // resident identity completes. Changing safety reinitializes the CAN
    // cores, so do not start the P2/deadline clocks until the main loop has
    // installed stable NOOUTPUT. Otherwise 10 03 and its timeout cleanup can
    // sit behind the same core transition and reach the wire together.
    ev9_preinit_pending_start = true;
  } else {
    // P2 starts when the diagnostic packet is actually enqueued, while
    // triggerUs remains the physical identity boundary for the hard global
    // deadline. In the direct RX path these timestamps are the same boundary.
    const uint32_t dispatch_us = microsecond_timer_get();
    ev9_preinit_pending_start = false;
    if (ev9_preinit_diag_deadline_reached(dispatch_us)) {
      ev9_preinit_flags |= EV9_PREINIT_FLAG_DEADLINE_MISSED;
      ev9_preinit_abort(dispatch_us);
    } else {
      ev9_preinit_send_session(dispatch_us);
    }
  }
}

static bool ev9_preinit_start_confirmed(uint32_t now_us) {
  // Stationary EV9 identity is present during door, lock, charging, and
  // restored post-OFF body wakes. Those are collection opportunities, not a
  // driver request to disable ADAS. A direct brake+Start produces both a live
  // ignition level and repeating driver-brake frames before READY. A fresh
  // selected-HKG remote wake followed by a physical ignition rise covers fob
  // start and app-climate entry before temporary ELM327 safety; 0x35's
  // pre-READY state remains the bounded CAN-side fallback.
  const bool fresh_driver_start = ev9_preinit_ignition_prev &&
                                  (ev9_preinit_last_driver_braking_us != 0U) &&
                                  (get_ts_elapsed(now_us, ev9_preinit_last_driver_braking_us) <=
                                   EV9_PREINIT_DRIVER_BRAKE_FRESH_US);
  const bool physical_ignition_start = ev9_preinit_ignition_prev &&
                                       (ev9_preinit_ignition_us != 0U) &&
                                       !ev9_preinit_powertrain_terminal();
  const bool pre_ready_start = (ev9_preinit_pre_ready_us != 0U) &&
                               !ev9_preinit_powertrain_terminal();
  const bool climate_takeover_start = ev9_preinit_ignition_prev &&
                                      (ev9_preinit_climate_takeover_us != 0U);
  return physical_ignition_start || fresh_driver_start || pre_ready_start || climate_takeover_start;
}

static void ev9_preinit_track_remote_wake_frame(const CANPacket_t *packet, uint32_t now_us) {
  // Physical classic-CAN 0x384 is the same bounded remote-start wake fact used
  // by the selected HKG Panda build to boot the comma. It does not enter the
  // CAN-FD identity/fingerprint path and cannot authorize UDS by itself.
  if ((packet->bus == EV9_PREINIT_BUS_ECAN) && (packet->addr == 0x384U) &&
      (GET_LEN(packet) == 8U) && (packet->data[3] != 0U)) {
    ev9_preinit_last_remote_wake_us = now_us;
  }
}

static void ev9_preinit_track_steering_angle(const CANPacket_t *packet, uint32_t now_us) {
  if ((packet->bus != EV9_PREINIT_BUS_ECAN) || (packet->addr != 0xEAU) ||
      !packet->fd || (GET_LEN(packet) != 24U) || !ev9_preinit_is_valid_canfd(packet)) {
    return;
  }

  // MDPS_0xEA carries the signed 16-bit measured angle in bytes 12/13 while
  // ADAS_CMD_35_10ms carries the same 0.1-degree value as signed 14-bit. Only
  // accept values whose upper bits are a valid 14-bit sign extension.
  const uint16_t raw = (uint16_t)packet->data[12] | ((uint16_t)packet->data[13] << 8U);
  const uint16_t sign_extension = raw & 0xE000U;
  if ((sign_extension == 0U) || (sign_extension == 0xE000U)) {
    ev9_preinit_steering_angle_raw = raw & 0x3FFFU;
    ev9_preinit_steering_angle_us = now_us;
    ev9_preinit_steering_angle_valid = true;
  }
}

static bool ev9_preinit_remote_wake_fresh(uint32_t now_us) {
  bool fresh = (ev9_preinit_last_remote_wake_us != 0U) &&
               (get_ts_elapsed(now_us, ev9_preinit_last_remote_wake_us) <=
                EV9_PREINIT_REMOTE_WAKE_FRESH_US);
  #ifdef PANDA_HKG_REMOTE_START
  // The selected HKG build uses this same bounded latch to boot the comma.
  // Unlike cycle-local capture state, it intentionally survives the first
  // valid CAN-FD frame resetting a sleeping/rearmed resident epoch.
  fresh = fresh || hkg_remote_climate_wake;
  #endif
  return fresh;
}

static void ev9_preinit_maybe_start(uint32_t now_us) {
  const bool identity_valid = (ev9_preinit_fingerprint & EV9_FP_IDENTITY_REQUIRED) == EV9_FP_IDENTITY_REQUIRED;
  if (identity_valid) {
    ev9_preinit_flags |= EV9_PREINIT_FLAG_IDENTITY_VALID;
  }
  const bool knockout_ready =
    ((ev9_preinit_fingerprint & EV9_FP_KNOCKOUT_REQUIRED) == EV9_FP_KNOCKOUT_REQUIRED) &&
    ev9_preinit_stationary_fresh(now_us);
  if ((ev9_preinit_state == EV9_PREINIT_COLLECTING) && knockout_ready && !ev9_preinit_off_latched &&
      !ev9_preinit_pending_start && ev9_preinit_start_confirmed(now_us)) {
    // A real start cue always establishes the trigger before this point.
    // Never synthesize ADAS_WAKE as permission to originate diagnostics.
    ev9_preinit_attempts = 0U;
    ev9_preinit_dispatch_start();
  }
}

static void ev9_preinit_retry_from_start_cue(uint32_t now_us, ev9_preinit_trigger_t trigger) {
  const bool retry_eligible = (ev9_preinit_state == EV9_PREINIT_ABORTED) &&
                              !ev9_preinit_restart_used &&
                              !ev9_preinit_off_latched &&
                              (ev9_preinit_ready_us == 0U) &&
                              !ev9_preinit_powertrain_terminal() &&
                              ((ev9_preinit_fingerprint & EV9_FP_KNOCKOUT_REQUIRED) == EV9_FP_KNOCKOUT_REQUIRED) &&
                              ev9_preinit_stationary_fresh(now_us) &&
                              ev9_preinit_start_confirmed(now_us);
  if (!retry_eligible) {
    return;
  }

  // One bounded second cycle covers door/unlock wake timeout followed by an
  // actual start cue. Never loop diagnostics indefinitely on a wrong vehicle.
  ev9_preinit_restart_used = true;
  ev9_preinit_state = EV9_PREINIT_COLLECTING;
  ev9_preinit_trigger = trigger;
  ev9_preinit_flags = EV9_PREINIT_FLAG_IDENTITY_VALID | EV9_PREINIT_FLAG_START_INTENT;
  ev9_preinit_attempts = 0U;
  ev9_preinit_last_service = 0U;
  ev9_preinit_last_response = 0U;
  ev9_preinit_last_nrc = 0U;
  ev9_preinit_state_started_us = now_us;
  ev9_preinit_trigger_us = now_us;
  ev9_preinit_session_request_us = 0U;
  ev9_preinit_session_response_us = 0U;
  ev9_preinit_comm_control_us = 0U;
  ev9_preinit_comm_control_response_us = 0U;
  ev9_preinit_session_in_flight = false;
  ev9_preinit_comm_control_queued = false;
  ev9_preinit_comm_control_in_flight = false;
  ev9_preinit_comm_control_unresolved = false;
  ev9_preinit_nrc_retry_pending = false;
  ev9_preinit_ready_us = 0U;
  ev9_preinit_outcome_us = 0U;
  ev9_preinit_suppression_confirmed_us = 0U;
  ev9_preinit_handoff_us = 0U;
  ev9_preinit_restore_us = 0U;
  ev9_preinit_last_restore_attempt_us = 0U;
  ev9_preinit_restore_attempts = 0U;
  ev9_preinit_restore_queued = false;
  ev9_preinit_restore_response_confirmed = false;
  ev9_preinit_rearm_on_next_can = false;
  ev9_preinit_restore_fallback_active = false;
  ev9_preinit_cancel_tx_pending = false;
  ev9_preinit_cancel_rearm_after = false;
  ev9_preinit_abort_us = 0U;
  ev9_preinit_reappear_started_us = 0U;
  ev9_preinit_restore_quiesce_us = 0U;
  ev9_preinit_restore_seen = 0U;
  for (uint8_t i = 0U; i < EV9_PREINIT_RESTORE_STREAM_COUNT; i++) {
    ev9_preinit_restore_seen_us[i] = 0U;
  }
  ev9_preinit_host_mask = 0U;
  ev9_preinit_dispatch_start();
}

static bool ev9_preinit_due(uint32_t now_us, uint32_t last_rx_us, uint32_t last_tx_us,
                            uint32_t last_attempt_us, uint32_t period_us) {
  const bool rx_recent = (last_rx_us != 0U) && (get_ts_elapsed(now_us, last_rx_us) < period_us);
  const bool tx_recent = (last_tx_us != 0U) && (get_ts_elapsed(now_us, last_tx_us) < period_us);
  const bool attempt_recent = (last_attempt_us != 0U) &&
                              (get_ts_elapsed(now_us, last_attempt_us) < period_us);
  return !rx_recent && !tx_recent && !attempt_recent;
}

static bool ev9_preinit_host_fresh(uint32_t now_us, uint32_t last_host_tx_us, uint32_t period_us) {
  const uint32_t scaled_timeout_us = period_us * 3U;
  const uint32_t timeout_us = (scaled_timeout_us > 100000U) ? scaled_timeout_us : 100000U;
  return (last_host_tx_us != 0U) && (get_ts_elapsed(now_us, last_host_tx_us) < timeout_us);
}

static void ev9_preinit_publish_bridge(uint32_t now_us) {
  if ((ev9_preinit_state == EV9_PREINIT_HANDOFF) || ev9_preinit_off_latched ||
      ((ev9_preinit_flags & EV9_PREINIT_FLAG_BRIDGE_ACTIVE) == 0U) ||
      (ev9_preinit_comm_control_response_us == 0U)) {
    return;
  }
  const bool host_heartbeat_fresh = ev9_preinit_host_fresh(now_us, ev9_preinit_last_host_heartbeat_us, 10000U);
  if (!host_heartbeat_fresh &&
      ev9_preinit_due(now_us, ev9_preinit_last_heartbeat_rx_us,
                      ev9_preinit_last_heartbeat_tx_us,
                      ev9_preinit_last_heartbeat_attempt_us, 10000U)) {
    CANPacket_t heartbeat = ev9_preinit_heartbeat_packet;
    heartbeat.data[2] = ev9_preinit_heartbeat_counter;
    ev9_preinit_update_crc(&heartbeat);
    ev9_preinit_last_heartbeat_attempt_us = now_us;
    if (ev9_preinit_internal_send(&heartbeat, EV9_PREINIT_BUS_RADAR)) {
      ev9_preinit_heartbeat_packet = heartbeat;
      ev9_preinit_heartbeat_counter += 1U;
      ev9_preinit_last_heartbeat_tx_us = now_us;
      if (ev9_preinit_first_replacement_us == 0U) {
        ev9_preinit_first_replacement_us = now_us;
      }
    }
  }

  for (uint8_t i = 0U; i < EV9_PREINIT_REPLAY_COUNT; i++) {
    ev9_preinit_replay_t *replay = &ev9_preinit_replay[i];
    const bool host_fresh = ev9_preinit_host_fresh(now_us, replay->last_host_tx_us, replay->period_us);
    const bool fallback_due = ev9_preinit_due(now_us, replay->last_rx_us, replay->last_tx_us,
                                              replay->last_attempt_us, replay->period_us);
    if (!host_fresh && replay->captured && fallback_due) {
      if (replay->host_claim_reserved &&
          !ev9_preinit_due(now_us, replay->last_rx_us, replay->last_tx_us,
                           replay->last_attempt_us, replay->period_us + EV9_PREINIT_SLOW_CLAIM_HOLD_US)) {
        // A single exact slow-stream host attempt may reserve the cadence
        // boundary while ACTIVE. Give the bounded all-stream retry one short
        // scheduling window, measured from the original cadence source rather
        // than from this service call. Resident fallback remains authoritative
        // and resumes by P+25 ms if no safety-approved host TX is queued.
        continue;
      }
      replay->host_claim_reserved = false;
      CANPacket_t packet = replay->packet;
      packet.data[2] += 1U;
      ev9_preinit_neutralize(&packet);
      ev9_preinit_update_crc(&packet);
      replay->last_attempt_us = now_us;
      if (ev9_preinit_internal_send(&packet, EV9_PREINIT_BUS_ECAN)) {
        replay->packet = packet;
        replay->last_tx_us = now_us;
        if (ev9_preinit_first_replacement_us == 0U) {
          ev9_preinit_first_replacement_us = now_us;
        }
      }
    }
  }
}

static void ev9_preinit_activate_bridge(uint32_t now_us) {
  ev9_preinit_seed_missing_fallbacks(now_us);
  ev9_preinit_flags |= EV9_PREINIT_FLAG_BRIDGE_ACTIVE;
  if (ev9_preinit_last_critical_adas_us == 0U) {
    ev9_preinit_last_critical_adas_us = now_us;
  }
  ev9_preinit_last_tester_present_us = now_us;
  ev9_preinit_publish_bridge(now_us);
}

static void ev9_preinit_start_tentative_bridge(uint32_t now_us, bool deadline_missed) {
  ev9_preinit_state = EV9_PREINIT_WAIT_SUPPRESSION;
  ev9_preinit_state_started_us = now_us;
  ev9_preinit_host_tx_quarantine = false;
  if (deadline_missed) {
    ev9_preinit_flags |= EV9_PREINIT_FLAG_DEADLINE_MISSED;
  }
  ev9_preinit_activate_bridge(now_us);
}

static void ev9_preinit_handle_terminal_ready(uint32_t now_us) {
  if (ev9_preinit_ready_us == 0U) {
    ev9_preinit_ready_us = now_us;
  }
  if (ev9_preinit_state == EV9_PREINIT_WAIT_COMM_CONTROL) {
    // The request timestamp is the route-proven acceptance boundary. Preserve
    // one already-transmitted pre-READY 0x28 through its remaining P2 window;
    // never originate or retry one after 0x51/0x55.
    if (ev9_preinit_comm_control_unresolved && !ev9_preinit_nrc_retry_pending) {
      ev9_preinit_state = EV9_PREINIT_READY_PENDING_RESPONSE;
    } else {
      (void)ev9_preinit_return_to_default_session();
      ev9_preinit_abort(now_us);
    }
  } else if ((ev9_preinit_state == EV9_PREINIT_WAIT_SESSION) ||
             (ev9_preinit_state == EV9_PREINIT_COLLECTING)) {
    const bool reset_recovery_candidate = (ev9_preinit_state == EV9_PREINIT_COLLECTING) &&
                                          (ev9_preinit_last_critical_adas_us == 0U);
    ev9_preinit_flags |= EV9_PREINIT_FLAG_DEADLINE_MISSED;
    if (ev9_preinit_state == EV9_PREINIT_WAIT_SESSION) {
      (void)ev9_preinit_return_to_default_session();
    }
    ev9_preinit_abort(now_us);
    if (reset_recovery_candidate) {
      ev9_preinit_recovery_restore = true;
      ev9_preinit_host_tx_quarantine = true;
    }
  } else {
  }
}

static bool ev9_preinit_diag_deadline_reached(uint32_t now_us) {
  const uint32_t started_us = (ev9_preinit_trigger_us != 0U) ?
                              ev9_preinit_trigger_us : ev9_preinit_session_request_us;
  return (started_us != 0U) &&
         (get_ts_elapsed(now_us, started_us) >= EV9_PREINIT_DIAG_DEADLINE_US);
}

static bool ev9_preinit_try_chain_session_response(const CANPacket_t *packet, uint32_t now_us) {
  const bool exact_session_response = ev9_preinit_is_diag_response_tuple(packet) &&
    (packet->data[0] == 6U) && (packet->data[1] == 0x50U) && (packet->data[2] == 0x03U);
  const bool response_within_p2 = get_ts_elapsed(now_us, ev9_preinit_state_started_us) <
                                  EV9_PREINIT_P2_TIMEOUT_US;
  if ((ev9_preinit_state != EV9_PREINIT_WAIT_SESSION) || !ev9_preinit_session_in_flight ||
      !exact_session_response || !response_within_p2 || ev9_preinit_diag_deadline_reached(now_us)) {
    return false;
  }

  ev9_preinit_session_in_flight = false;
  ev9_preinit_last_response = packet->data[1];
  ev9_preinit_last_nrc = 0U;
  ev9_preinit_session_response_us = now_us;
  ev9_preinit_attempts = 0U;
  // This is the sole state-changing action retained in FDCAN RX. Route evidence
  // shows the 28 01 acceptance window can be only 59 ms, so enqueue it directly
  // from the exact correlated 50 03 response. Every other response is deferred.
  ev9_preinit_send_comm_control(now_us);
  return true;
}

static void ev9_preinit_handle_diag_response(const CANPacket_t *packet, uint32_t now_us) {
  if (!ev9_preinit_is_diag_response_tuple(packet)) {
    return;
  }

  if (ev9_preinit_try_chain_session_response(packet, now_us)) {
    return;
  }

  const bool response_within_p2 = get_ts_elapsed(now_us, ev9_preinit_state_started_us) <
                                  EV9_PREINIT_P2_TIMEOUT_US;
  const bool waiting_session_nrc = (ev9_preinit_state == EV9_PREINIT_WAIT_SESSION) &&
                                   ev9_preinit_session_in_flight &&
                                   (packet->data[2] == 0x10U);
  const bool waiting_comm_nrc = (ev9_preinit_state == EV9_PREINIT_WAIT_COMM_CONTROL) &&
                                ev9_preinit_comm_control_in_flight &&
                                (packet->data[2] == 0x28U);
  const bool ready_pending_comm_nrc = (ev9_preinit_state == EV9_PREINIT_READY_PENDING_RESPONSE) &&
                                     ev9_preinit_comm_control_in_flight &&
                                     (packet->data[2] == 0x28U);
  if (((ev9_preinit_state == EV9_PREINIT_WAIT_COMM_CONTROL) ||
              (ev9_preinit_state == EV9_PREINIT_READY_PENDING_RESPONSE) ||
              (ev9_preinit_state == EV9_PREINIT_RESTORING)) &&
             ev9_preinit_comm_control_unresolved &&
             !ev9_preinit_nrc_retry_pending &&
             (packet->data[0] == 2U) && (packet->data[1] == 0x68U) && (packet->data[2] == 0x01U)) {
    ev9_preinit_last_response = packet->data[1];
    ev9_preinit_last_nrc = 0U;
    const bool late = !response_within_p2 || ev9_preinit_diag_deadline_reached(now_us);
    ev9_preinit_comm_control_in_flight = false;
    ev9_preinit_comm_control_unresolved = false;
    ev9_preinit_nrc_retry_pending = false;
    ev9_preinit_comm_control_response_us = now_us;
    // An exact positive is definitive ownership even at the policy deadline.
    // The deadline forbids new requests; it cannot erase an observed response.
    // If restore is already queued, record ownership without publishing: 28 00
    // may be next on the wire, and fallback can resume only after it times out.
    if (!ev9_preinit_off_latched &&
        ((ev9_preinit_state != EV9_PREINIT_RESTORING) || !ev9_preinit_restore_queued)) {
      ev9_preinit_start_tentative_bridge(now_us, late);
    } else if (late) {
      ev9_preinit_flags |= EV9_PREINIT_FLAG_DEADLINE_MISSED;
    } else {
    }
  } else if (response_within_p2 && (packet->data[0] == 3U) && (packet->data[1] == 0x7FU) &&
             (waiting_session_nrc || waiting_comm_nrc || ready_pending_comm_nrc)) {
    const uint8_t nrc = packet->data[3];
    if (waiting_session_nrc) {
      ev9_preinit_session_in_flight = false;
    } else {
      ev9_preinit_comm_control_in_flight = false;
      ev9_preinit_comm_control_unresolved = false;
    }
    ev9_preinit_last_response = packet->data[1];
    ev9_preinit_last_nrc = nrc;
    if ((nrc == 0x22U) && (ev9_preinit_attempts < EV9_PREINIT_MAX_ATTEMPTS) &&
        !ev9_preinit_powertrain_terminal() && (waiting_session_nrc || waiting_comm_nrc)) {
      // A bounded 10 ms retry after a completed NRC still fits the cold 0x45
      // window; timer retries never overlap an outstanding P2 response.
      ev9_preinit_nrc_retry_pending = true;
      ev9_preinit_state_started_us = now_us - (EV9_PREINIT_P2_TIMEOUT_US - EV9_PREINIT_NRC_RETRY_US);
    } else {
      if (waiting_comm_nrc || ready_pending_comm_nrc) {
        (void)ev9_preinit_return_to_default_session();
      }
      ev9_preinit_abort(now_us);
    }
  } else if ((((ev9_preinit_state == EV9_PREINIT_RESTORING) && ev9_preinit_restore_queued) ||
              (((ev9_preinit_state == EV9_PREINIT_WAIT_SUPPRESSION) ||
                (ev9_preinit_state == EV9_PREINIT_ACTIVE) ||
                (ev9_preinit_state == EV9_PREINIT_HANDOFF)) &&
               ev9_preinit_restore_fallback_active)) &&
             (packet->data[0] == 2U) && (packet->data[1] == 0x68U) && (packet->data[2] == 0x00U)) {
    if (ev9_preinit_state != EV9_PREINIT_RESTORING) {
      ev9_preinit_begin_restore(now_us);
      ev9_preinit_schedule_tx_cancel(false);
    }
    ev9_preinit_last_response = packet->data[1];
    ev9_preinit_last_nrc = 0U;
    ev9_preinit_comm_control_unresolved = false;
    ev9_preinit_restore_response_confirmed = true;
  } else if ((ev9_preinit_state == EV9_PREINIT_RESTORING) && ev9_preinit_restore_queued &&
             (packet->data[0] == 3U) && (packet->data[1] == 0x7FU) &&
             (packet->data[2] == 0x28U)) {
    ev9_preinit_last_response = packet->data[1];
    ev9_preinit_last_nrc = packet->data[3];
  } else {
  }
}

static void ev9_preinit_track_restore_frame(const CANPacket_t *packet, bool valid_canfd_crc, uint32_t now_us) {
  if ((ev9_preinit_state != EV9_PREINIT_RESTORING) || !valid_canfd_crc) {
    return;
  }
  if ((packet->bus == EV9_PREINIT_BUS_RADAR) && (packet->addr == 0x100U) && (GET_LEN(packet) == 24U)) {
    ev9_preinit_restore_seen |= EV9_PREINIT_RESTORE_HEARTBEAT_BIT;
    ev9_preinit_restore_seen_us[0] = now_us;
  } else if ((packet->bus == EV9_PREINIT_BUS_ECAN) && (packet->addr == 0x12AU) && (GET_LEN(packet) == 16U)) {
    ev9_preinit_restore_seen |= EV9_PREINIT_RESTORE_12A_BIT;
    ev9_preinit_restore_seen_us[1] = now_us;
  } else if ((packet->bus == EV9_PREINIT_BUS_ECAN) && (packet->addr == 0xCBU) && (GET_LEN(packet) == 24U)) {
    ev9_preinit_restore_seen |= EV9_PREINIT_RESTORE_CB_BIT;
    ev9_preinit_restore_seen_us[2] = now_us;
  } else if ((packet->bus == EV9_PREINIT_BUS_ECAN) && (packet->addr == 0x160U) && (GET_LEN(packet) == 16U)) {
    ev9_preinit_restore_seen |= EV9_PREINIT_RESTORE_160_BIT;
    ev9_preinit_restore_seen_us[3] = now_us;
  } else if ((packet->bus == EV9_PREINIT_BUS_ECAN) && (packet->addr == 0x1A0U) && (GET_LEN(packet) == 32U)) {
    ev9_preinit_restore_seen |= EV9_PREINIT_RESTORE_1A0_BIT;
    ev9_preinit_restore_seen_us[4] = now_us;
  } else {
  }
}

static bool ev9_preinit_restore_converged(uint32_t now_us) {
  bool converged = (ev9_preinit_restore_seen & EV9_PREINIT_RESTORE_REQUIRED_MASK) ==
                   EV9_PREINIT_RESTORE_REQUIRED_MASK;
  for (uint8_t i = 0U; i < EV9_PREINIT_RESTORE_STREAM_COUNT; i++) {
    converged = converged && (ev9_preinit_restore_seen_us[i] != 0U) &&
                (get_ts_elapsed(now_us, ev9_preinit_restore_seen_us[i]) <= EV9_PREINIT_RESTORE_FRESH_US);
  }
  return converged;
}

static void ev9_preinit_service_state(uint32_t now_us, ev9_preinit_can_reset_result_t reset_result);

static void ev9_preinit_process_rx_sample(const ev9_preinit_rx_sample_t *sample) {
  const CANPacket_t *packet = &sample->packet;
  const uint32_t now_us = sample->received_us;
  const bool valid_canfd_crc = sample->valid_canfd_crc;
  const bool valid_heartbeat = valid_canfd_crc && ev9_preinit_is_heartbeat_tuple(packet);
  if (ev9_preinit_cancel_tx_pending) {
    // Both controllers are frozen or awaiting an atomic purge. Do not let a
    // physical RX drive the old epoch before cancellation completes. Exact
    // correlated UDS responses are already wire facts and remain safe to record.
    ev9_preinit_last_can_us = now_us;
    ev9_preinit_handle_diag_response(packet, now_us);
    return;
  }
  if (sample->rearm_candidate && ev9_preinit_rearm_on_next_can && valid_canfd_crc) {
    // TX was cancelled after a proven-safe off boundary. Treat the first valid
    // physical frame after that boundary as a new ECU power/wake cycle.
    ev9_long_preinit_reset_cycle();
  }
  if (ev9_preinit_cycle_started_us == 0U) {
    ev9_preinit_cycle_started_us = now_us;
  }
  if (ev9_preinit_first_can_us == 0U) {
    ev9_preinit_first_can_us = now_us;
  }
  ev9_preinit_last_can_us = now_us;

  const bool new_heartbeat_epoch = valid_heartbeat && (ev9_preinit_last_heartbeat_rx_us != 0U) &&
    (get_ts_elapsed(now_us, ev9_preinit_last_heartbeat_rx_us) >= EV9_PREINIT_HEARTBEAT_EPOCH_GAP_US);
  if (valid_canfd_crc &&
      (((packet->bus == EV9_PREINIT_BUS_ECAN) && (packet->addr == 0x35U) && (GET_LEN(packet) == 32U)) ||
       ((packet->bus == EV9_PREINIT_BUS_ECAN) && (packet->addr == 0xA0U) && (GET_LEN(packet) == 24U)))) {
    ev9_preinit_last_vehicle_frame_us = now_us;
  }

  bool driver_braking = false;
  bool powertrain_frame = false;
  if (valid_canfd_crc && (packet->bus == EV9_PREINIT_BUS_ECAN)) {
    driver_braking = (packet->addr == 0x175U) && (GET_LEN(packet) == 24U) &&
                     ((packet->data[10] & 0x02U) != 0U);
    powertrain_frame = (packet->addr == 0x35U) && (GET_LEN(packet) == 32U);
  }
  if (driver_braking) {
    ev9_preinit_flags |= EV9_PREINIT_FLAG_START_INTENT;
    ev9_preinit_last_driver_braking_us = now_us;
    if (ev9_preinit_driver_braking_us == 0U) {
      ev9_preinit_driver_braking_us = now_us;
    }
    if (ev9_preinit_trigger == EV9_PREINIT_TRIGGER_NONE) {
      ev9_preinit_trigger = EV9_PREINIT_TRIGGER_DRIVER_BRAKE;
      ev9_preinit_trigger_us = now_us;
    }
    ev9_preinit_retry_from_start_cue(now_us, EV9_PREINIT_TRIGGER_DRIVER_BRAKE);
  }
  if (powertrain_frame) {
    ev9_preinit_powertrain_state = packet->data[3];
    ev9_preinit_powertrain_boot_state = packet->data[4];
    ev9_preinit_powertrain_init_state = packet->data[6];
    ev9_preinit_last_powertrain_us = now_us;
    if (packet->data[3] == 0x45U) {
      ev9_preinit_flags |= EV9_PREINIT_FLAG_START_INTENT;
      bool retime_unconfirmed_ignition = false;
      if (ev9_preinit_pre_ready_us == 0U) {
        ev9_preinit_pre_ready_us = now_us;
        // Remote climate keeps ignition low and emits no pre-READY state. On
        // key/entry takeover the harness ignition can rise hundreds of
        // milliseconds before 0x35 reaches 0x45, without a brake edge. If no
        // diagnostic was ever attempted, the pre-READY wire fact is the first
        // confirmed start boundary and needs its own bounded 200 ms window.
        // Preserve an earlier driver-brake trigger and every in-flight epoch.
        retime_unconfirmed_ignition =
          (ev9_preinit_state == EV9_PREINIT_COLLECTING) &&
          (ev9_preinit_attempts == 0U) && (ev9_preinit_session_request_us == 0U) &&
          (ev9_preinit_driver_braking_us == 0U) &&
          ((ev9_preinit_trigger == EV9_PREINIT_TRIGGER_IGNITION) ||
           (ev9_preinit_trigger == EV9_PREINIT_TRIGGER_ADAS_WAKE));
      }
      if ((ev9_preinit_trigger == EV9_PREINIT_TRIGGER_NONE) || retime_unconfirmed_ignition) {
        ev9_preinit_trigger = EV9_PREINIT_TRIGGER_PRE_READY;
        ev9_preinit_trigger_us = now_us;
      }
      ev9_preinit_retry_from_start_cue(now_us, EV9_PREINIT_TRIGGER_PRE_READY);
    }
  }

  if ((ev9_preinit_state == EV9_PREINIT_ABORTED) && !ev9_preinit_restart_used &&
      !ev9_preinit_off_latched && (ev9_preinit_ready_us == 0U) && valid_canfd_crc &&
      (packet->bus == EV9_PREINIT_BUS_ECAN) && (packet->addr == 0xA0U) &&
      (GET_LEN(packet) == 24U)) {
    // The bounded door-wake retry may occur long after the first diagnostic
    // P2 window. Refresh only the non-actuating wheel-speed proof while
    // terminal; never merge new model identity or replacement bodies into the
    // failed epoch.
    ev9_preinit_update_wheel_speed_proof(packet, now_us);
  }
  if ((ev9_preinit_state != EV9_PREINIT_ABORTED) &&
      (ev9_preinit_state != EV9_PREINIT_HANDOFF)) {
    ev9_preinit_capture_frame(packet, valid_canfd_crc, valid_heartbeat, now_us);
  }

  const bool critical_adas = valid_canfd_crc && ev9_preinit_is_critical_adas(packet);
  if (critical_adas) {
    ev9_preinit_last_critical_adas_us = now_us;
    if ((ev9_preinit_state == EV9_PREINIT_ABORTED) && ev9_preinit_recovery_restore &&
        !ev9_preinit_release_requested) {
      // Stock traffic disproves the reset-recovery hypothesis before any UDS.
      ev9_preinit_recovery_restore = false;
      ev9_preinit_host_tx_quarantine = false;
    }
    if (((ev9_preinit_state == EV9_PREINIT_WAIT_SUPPRESSION) ||
         (ev9_preinit_state == EV9_PREINIT_ACTIVE) ||
         (ev9_preinit_state == EV9_PREINIT_HANDOFF)) &&
        ev9_preinit_restore_fallback_active) {
      // A restore response may have been lost. The first valid stock frame
      // after fallback is enough to stop replacement publication immediately.
      ev9_preinit_begin_restore(now_us);
      ev9_preinit_schedule_tx_cancel(false);
    } else if ((ev9_preinit_state == EV9_PREINIT_WAIT_SUPPRESSION) ||
        (ev9_preinit_state == EV9_PREINIT_ACTIVE) ||
        (ev9_preinit_state == EV9_PREINIT_HANDOFF)) {
      if (ev9_preinit_reappear_started_us == 0U) {
        ev9_preinit_reappear_started_us = now_us;
      }
    }
  }
  if (valid_heartbeat) {
    ev9_preinit_last_heartbeat_rx_us = now_us;
  }
  ev9_preinit_track_restore_frame(packet, valid_canfd_crc, now_us);
  ev9_preinit_handle_diag_response(packet, now_us);
  if ((packet->bus == EV9_PREINIT_BUS_ECAN) && (packet->addr == EV9_PREINIT_DIAG_RESP_ADDR)) {
    ev9_preinit_advance_diag(now_us);
  }
  if (powertrain_frame && ev9_preinit_powertrain_terminal()) {
    ev9_preinit_handle_terminal_ready(now_us);
  } else {
    ev9_preinit_maybe_start(now_us);
  }
  if (new_heartbeat_epoch && ev9_preinit_start_confirmed(now_us) &&
      (ev9_preinit_trigger != EV9_PREINIT_TRIGGER_NONE) &&
      (ev9_preinit_trigger != EV9_PREINIT_TRIGGER_ADAS_WAKE)) {
    ev9_preinit_retry_from_start_cue(now_us, ev9_preinit_trigger);
  }
  const bool ownership_state = (ev9_preinit_state == EV9_PREINIT_WAIT_SUPPRESSION) ||
                               (ev9_preinit_state == EV9_PREINIT_ACTIVE) ||
                               (ev9_preinit_state == EV9_PREINIT_HANDOFF);
  if (ownership_state && (ev9_preinit_reappear_started_us != 0U) &&
      (get_ts_elapsed(now_us, ev9_preinit_reappear_started_us) >= EV9_PREINIT_REAPPEAR_CONFIRM_US)) {
    ev9_preinit_begin_restore(now_us);
  } else if ((ev9_preinit_state == EV9_PREINIT_RESTORING) && !ev9_preinit_cancel_tx_pending &&
             (ev9_preinit_restore_response_confirmed || ev9_preinit_restore_converged(now_us)) &&
             ev9_preinit_restore_tx_idle()) {
    // Restore proof is response-critical: close the diagnostic session at once.
    ev9_preinit_finish_restore(now_us);
  } else {
  }
}

static void ev9_long_preinit_rx_hook(const CANPacket_t *packet, uint32_t now_us) {
  // Preserve the proven route-17a/17b scheduling path: valid physical RX is
  // the high-resolution pre-host scheduler. Deferring these exact-tuple events
  // to Panda's blocking main loop consumed the diagnostic window on routes
  // 182-185 even when the correct early 0x35 sample survived the queue.
  ev9_preinit_last_can_us = now_us;

  ev9_preinit_track_remote_wake_frame(packet, now_us);
  ev9_preinit_track_steering_angle(packet, now_us);

  if (ev9_preinit_is_diag_response_tuple(packet)) {
    if (ev9_preinit_try_chain_session_response(packet, now_us)) {
      ev9_preinit_service_state(now_us, EV9_PREINIT_CAN_RESET_IDLE);
      return;
    }
    const ev9_preinit_rx_sample_t sample = {
      .packet = *packet,
      .received_us = now_us,
      .valid_canfd_crc = false,
      .rearm_candidate = false,
    };
    ev9_preinit_process_rx_sample(&sample);
    ev9_preinit_service_state(now_us, EV9_PREINIT_CAN_RESET_IDLE);
    return;
  }
  if (!ev9_preinit_is_relevant_canfd_tuple(packet)) {
    return;
  }

  const bool valid_canfd_crc = ev9_preinit_is_valid_canfd(packet);
  if (valid_canfd_crc) {
    const ev9_preinit_rx_sample_t sample = {
      .packet = *packet,
      .received_us = now_us,
      .valid_canfd_crc = true,
      .rearm_candidate = ev9_preinit_rearm_on_next_can,
    };
    ev9_preinit_process_rx_sample(&sample);
    ev9_preinit_service_state(now_us, EV9_PREINIT_CAN_RESET_IDLE);
  }
}

static void ev9_preinit_maybe_complete_handoff(uint32_t now_us) {
  const can_health_t *radar_health = &can_health[CAN_NUM_FROM_BUS_NUM(EV9_PREINIT_BUS_RADAR)];
  const can_health_t *ecan_health = &can_health[CAN_NUM_FROM_BUS_NUM(EV9_PREINIT_BUS_ECAN)];
  const bool managed_buses_healthy = !radar_health->bus_off && !radar_health->error_passive &&
                                     (radar_health->transmit_error_cnt < 128U) &&
                                     !ecan_health->bus_off && !ecan_health->error_passive &&
                                     (ecan_health->transmit_error_cnt < 128U);
  if ((ev9_preinit_state == EV9_PREINIT_ACTIVE) &&
      ((ev9_preinit_host_hw_mask & EV9_PREINIT_HOST_REQUIRED_MASK) == EV9_PREINIT_HOST_REQUIRED_MASK) &&
      (ev9_preinit_host_hw_pending_mask == 0U) && !ev9_preinit_cancel_tx_pending &&
      !ev9_preinit_rearm_on_next_can && managed_buses_healthy &&
      ev9_preinit_host_lease_fresh(now_us)) {
    ev9_preinit_state = EV9_PREINIT_HANDOFF;
    ev9_preinit_clear_slow_claim_reservations(false);
    ev9_preinit_flags |= EV9_PREINIT_FLAG_HOST_HANDOFF;
    ev9_preinit_handoff_us = now_us;
    ev9_preinit_outcome_us = now_us;
  }
}

static void ev9_long_preinit_host_tx_hook(const CANPacket_t *packet) {
  if (((ev9_preinit_flags & EV9_PREINIT_FLAG_BRIDGE_ACTIVE) == 0U) || packet->rejected) {
    return;
  }
  const uint32_t now_us = microsecond_timer_get();
  if ((packet->bus == EV9_PREINIT_BUS_RADAR) && (packet->addr == 0x100U) && (GET_LEN(packet) == 24U)) {
    ev9_preinit_host_mask |= EV9_PREINIT_HOST_HEARTBEAT_BIT;
    ev9_preinit_host_hw_pending_mask |= EV9_PREINIT_HOST_HEARTBEAT_BIT;
    ev9_preinit_host_heartbeat_hw_pending = true;
    ev9_preinit_host_heartbeat_hw_packet = *packet;
    ev9_preinit_last_host_heartbeat_us = now_us;
    ev9_preinit_heartbeat_packet = *packet;
    ev9_preinit_heartbeat_packet.fd = 1U;
    ev9_preinit_heartbeat_packet.bus = EV9_PREINIT_BUS_RADAR;
    ev9_preinit_heartbeat_counter = packet->data[2] + 1U;
    ev9_preinit_last_heartbeat_tx_us = now_us;
    ev9_preinit_last_heartbeat_attempt_us = now_us;
  } else if ((packet->bus == EV9_PREINIT_BUS_ECAN) && (packet->addr == EV9_PREINIT_DIAG_ADDR) &&
             (GET_LEN(packet) == 8U) && (packet->data[0] == 2U) &&
             (packet->data[1] == 0x3EU) && (packet->data[2] == 0x80U)) {
    ev9_preinit_host_mask |= EV9_PREINIT_HOST_TP_BIT;
    ev9_preinit_host_hw_pending_mask |= EV9_PREINIT_HOST_TP_BIT;
    ev9_preinit_host_tp_hw_pending = true;
    ev9_preinit_host_tp_hw_packet = *packet;
    ev9_preinit_last_host_tp_us = now_us;
    ev9_preinit_last_tester_present_us = now_us;
  } else {
    for (uint8_t i = 0U; i < EV9_PREINIT_REPLAY_COUNT; i++) {
      if ((packet->bus == EV9_PREINIT_BUS_ECAN) &&
          (packet->addr == ev9_preinit_replay[i].addr) &&
          (GET_LEN(packet) == ev9_preinit_replay[i].len)) {
        ev9_preinit_host_mask |= 1U << i;
        ev9_preinit_host_hw_pending_mask |= 1U << i;
        ev9_preinit_replay[i].host_hw_pending = true;
        ev9_preinit_replay[i].host_hw_packet = *packet;
        ev9_preinit_replay[i].last_host_tx_us = now_us;
        ev9_preinit_replay[i].host_claim_reserved = false;
        // Keep the resident fallback phase synchronized with the last frame
        // that actually entered the hardware queue. If the host lease lapses,
        // the bridge resumes at the next counter and neutralizes any command
        // fields instead of replaying an old pre-handoff epoch.
        const uint8_t *fallback = ev9_preinit_fallback(packet->addr);
        if (ev9_preinit_force_neutral_addr(packet->addr) && (fallback != NULL)) {
          ev9_preinit_replay[i].packet = ev9_preinit_make_packet(
            packet->addr, EV9_PREINIT_BUS_ECAN, ev9_preinit_replay[i].len, true);
          (void)memcpy(ev9_preinit_replay[i].packet.data, fallback, ev9_preinit_replay[i].len);
          ev9_preinit_replay[i].packet.data[2] = packet->data[2];
        } else {
          ev9_preinit_replay[i].packet = *packet;
          ev9_preinit_replay[i].packet.fd = 1U;
          ev9_preinit_replay[i].packet.bus = EV9_PREINIT_BUS_ECAN;
        }
        ev9_preinit_replay[i].last_tx_us = now_us;
        ev9_preinit_replay[i].last_attempt_us = now_us;
      }
    }
  }
  ev9_preinit_last_host_tx_us = now_us;
}

static void ev9_long_preinit_tx_hw_loaded(const CANPacket_t *packet, uint8_t bus_number) {
  if ((ev9_preinit_flags & EV9_PREINIT_FLAG_BRIDGE_ACTIVE) == 0U) {
    return;
  }
  const uint32_t now_us = microsecond_timer_get();
  if ((bus_number == EV9_PREINIT_BUS_RADAR) && ev9_preinit_host_heartbeat_hw_pending &&
      ev9_preinit_same_packet(packet, &ev9_preinit_host_heartbeat_hw_packet)) {
    ev9_preinit_host_heartbeat_hw_pending = false;
    ev9_preinit_host_hw_pending_mask &= ~EV9_PREINIT_HOST_HEARTBEAT_BIT;
    ev9_preinit_host_hw_mask |= EV9_PREINIT_HOST_HEARTBEAT_BIT;
  } else if ((bus_number == EV9_PREINIT_BUS_ECAN) && ev9_preinit_host_tp_hw_pending &&
             ev9_preinit_same_packet(packet, &ev9_preinit_host_tp_hw_packet)) {
    ev9_preinit_host_tp_hw_pending = false;
    ev9_preinit_host_hw_pending_mask &= ~EV9_PREINIT_HOST_TP_BIT;
    ev9_preinit_host_hw_mask |= EV9_PREINIT_HOST_TP_BIT;
  } else if (bus_number == EV9_PREINIT_BUS_ECAN) {
    for (uint8_t i = 0U; i < EV9_PREINIT_REPLAY_COUNT; i++) {
      if (ev9_preinit_replay[i].host_hw_pending &&
          ev9_preinit_same_packet(packet, &ev9_preinit_replay[i].host_hw_packet)) {
        ev9_preinit_replay[i].host_hw_pending = false;
        ev9_preinit_host_hw_pending_mask &= ~(1UL << i);
        ev9_preinit_host_hw_mask |= 1UL << i;
        break;
      }
    }
  }
  ev9_preinit_maybe_complete_handoff(now_us);
}

static void ev9_long_preinit_tx_queue_cleared(uint8_t bus_number) {
  uint32_t cleared_mask = 0U;
  if (bus_number == EV9_PREINIT_BUS_RADAR) {
    cleared_mask = EV9_PREINIT_HOST_HEARTBEAT_BIT;
    ev9_preinit_host_heartbeat_hw_pending = false;
  } else if (bus_number == EV9_PREINIT_BUS_ECAN) {
    cleared_mask = EV9_PREINIT_HOST_TP_BIT | ((1UL << EV9_PREINIT_REPLAY_COUNT) - 1UL);
    ev9_preinit_host_tp_hw_pending = false;
    for (uint8_t i = 0U; i < EV9_PREINIT_REPLAY_COUNT; i++) {
      ev9_preinit_replay[i].host_hw_pending = false;
    }
  } else {
  }
  ev9_preinit_host_mask &= ~cleared_mask;
  ev9_preinit_host_hw_mask &= ~cleared_mask;
  ev9_preinit_host_hw_pending_mask &= ~cleared_mask;
}

static bool ev9_preinit_managed_host_tx(const CANPacket_t *packet, uint8_t bus_number) {
  if ((bus_number == EV9_PREINIT_BUS_RADAR) &&
      (packet->addr == 0x100U) && (GET_LEN(packet) == 24U)) {
    return true;
  }
  if ((bus_number == EV9_PREINIT_BUS_ECAN) && (packet->addr == EV9_PREINIT_DIAG_ADDR)) {
    return true;
  }
  if (bus_number == EV9_PREINIT_BUS_ECAN) {
    for (uint8_t i = 0U; i < EV9_PREINIT_REPLAY_COUNT; i++) {
      if ((packet->addr == ev9_preinit_replay[i].addr) &&
          (GET_LEN(packet) == ev9_preinit_replay[i].len)) {
        return true;
      }
    }
  }
  return false;
}

static bool ev9_preinit_inactive_host_cb(const CANPacket_t *packet) {
  return (packet->addr == 0xCBU) && (GET_LEN(packet) == 24U) &&
         (ev9_preinit_get_bits(packet->data, 24U, 4U) == 0U) &&
         (ev9_preinit_get_bits(packet->data, 28U, 4U) == 1U) &&
         (ev9_preinit_get_bits(packet->data, 48U, 8U) == 0U) &&
         (ev9_preinit_get_bits(packet->data, 56U, 2U) == 0U) &&
         (ev9_preinit_get_bits(packet->data, 64U, 8U) == 0U);
}

static bool ev9_preinit_host_tx_due(uint32_t now_us, uint32_t last_rx_us,
                                    uint32_t last_tx_us, uint32_t last_attempt_us,
                                    uint32_t period_us) {
  const uint32_t minimum_gap_us = period_us - (period_us / 10U);
  const bool rx_due = (last_rx_us == 0U) || (get_ts_elapsed(now_us, last_rx_us) >= minimum_gap_us);
  const bool tx_due = (last_tx_us == 0U) || (get_ts_elapsed(now_us, last_tx_us) >= minimum_gap_us);
  const bool attempt_due = (last_attempt_us == 0U) ||
                           (get_ts_elapsed(now_us, last_attempt_us) >= minimum_gap_us);
  return rx_due && tx_due && attempt_due;
}

static bool ev9_long_preinit_prepare_host_tx(CANPacket_t *packet, uint8_t bus_number,
                                             bool forwarded) {
  if (forwarded || ((ev9_preinit_flags & EV9_PREINIT_FLAG_BRIDGE_ACTIVE) == 0U) ||
      ((ev9_preinit_state != EV9_PREINIT_ACTIVE) && (ev9_preinit_state != EV9_PREINIT_HANDOFF))) {
    return true;
  }
  if ((ev9_preinit_state == EV9_PREINIT_HANDOFF) &&
      (get_ts_elapsed(microsecond_timer_get(), ev9_preinit_handoff_us) >=
       EV9_PREINIT_HANDOFF_SETTLE_US)) {
    // Claim retries use frozen host bodies while the accepted on-wire counters
    // continue advancing. Preserve only counter/CRC continuity at the boundary;
    // cadence, body fields, commands, and the ordinary safety hook remain host-owned.
    bool update_crc = false;
    if ((bus_number == EV9_PREINIT_BUS_RADAR) && (packet->addr == 0x100U) &&
        (GET_LEN(packet) == 24U)) {
      packet->fd = 1U;
      packet->data[2] = ev9_preinit_heartbeat_counter;
      update_crc = true;
    } else if (bus_number == EV9_PREINIT_BUS_ECAN) {
      for (uint8_t i = 0U; i < EV9_PREINIT_REPLAY_COUNT; i++) {
        if ((packet->addr == ev9_preinit_replay[i].addr) &&
            (GET_LEN(packet) == ev9_preinit_replay[i].len)) {
          packet->fd = 1U;
          packet->data[2] = ev9_preinit_replay[i].packet.data[2] + 1U;
          update_crc = true;
          break;
        }
      }
    }
    if (update_crc) {
      ev9_preinit_update_crc(packet);
    }
    return true;
  }

  bool managed = false;
  const uint32_t now_us = microsecond_timer_get();
  if ((bus_number == EV9_PREINIT_BUS_RADAR) && (packet->addr == 0x100U) &&
      (GET_LEN(packet) == 24U)) {
    if (!ev9_preinit_host_tx_due(now_us, ev9_preinit_last_heartbeat_rx_us,
                                 ev9_preinit_last_heartbeat_tx_us,
                                 ev9_preinit_last_heartbeat_attempt_us, 10000U)) {
      return false;
    }
    // USB sendcan packets arrive with fd=0; FDCAN auto-promotes them only
    // after this hook. Canonicalize the exact EV9 tuple before CRC/safety.
    packet->fd = 1U;
    packet->data[2] = ev9_preinit_heartbeat_counter;
    managed = true;
  } else if ((bus_number == EV9_PREINIT_BUS_ECAN) && (packet->addr == EV9_PREINIT_DIAG_ADDR) &&
             !packet->fd && (GET_LEN(packet) == 8U)) {
    if (!ev9_preinit_host_tx_due(now_us, 0U, ev9_preinit_last_tester_present_us,
                                 0U, EV9_PREINIT_TESTER_PRESENT_INTERVAL_US)) {
      return false;
    }
  } else if (bus_number == EV9_PREINIT_BUS_ECAN) {
    for (uint8_t i = 0U; i < EV9_PREINIT_REPLAY_COUNT; i++) {
      if ((packet->addr == ev9_preinit_replay[i].addr) &&
          (GET_LEN(packet) == ev9_preinit_replay[i].len)) {
        ev9_preinit_replay_t *replay = &ev9_preinit_replay[i];
        if (!ev9_preinit_host_tx_due(now_us, replay->last_rx_us, replay->last_tx_us,
                                     replay->last_attempt_us, replay->period_us)) {
          const bool recent_managed_host_tx = (ev9_preinit_host_mask != 0U) &&
            ev9_preinit_host_fresh(now_us, ev9_preinit_last_host_tx_us, 10000U);
          if ((ev9_preinit_state == EV9_PREINIT_ACTIVE) && ev9_preinit_slow_claim_addr(replay->addr) &&
              !replay->host_claim_reservation_used && recent_managed_host_tx &&
              ev9_preinit_same_body(packet, &replay->packet)) {
            // This attempt is not safety-accepted or counted as ownership. It
            // only reserves one bounded resident deadline; a later due retry
            // must still traverse the normal safety hook and hardware queue.
            replay->host_claim_reservation_used = true;
            replay->host_claim_reserved = true;
          }
          return false;
        }
        packet->fd = 1U;
        packet->data[2] = replay->packet.data[2] + 1U;
        if (ev9_preinit_inactive_host_cb(packet) && ev9_preinit_steering_angle_valid &&
            (get_ts_elapsed(now_us, ev9_preinit_steering_angle_us) <=
             EV9_PREINIT_STEERING_ANGLE_FRESH_US)) {
          // Route 1a5 proved that a frozen inactive claim can become stale
          // while the wheel moves. Canonicalize only the non-actuating angle
          // to the same fresh physical 0xEA sample consumed by Panda safety;
          // the final CRC is regenerated below. Active commands are untouched.
          packet->data[4] = (uint8_t)(ev9_preinit_steering_angle_raw & 0xFFU);
          packet->data[5] = (packet->data[5] & 0xC0U) |
                            (uint8_t)((ev9_preinit_steering_angle_raw >> 8U) & 0x3FU);
        }
        if (packet->addr == 0x161U) {
          // Keep the driver-visible FCA status orange throughout resident and
          // host ownership. LKA orange explicitly reports that the resident
          // bridge is still waiting for a complete host handoff; clear it on
          // the first post-HANDOFF 0x161 without trusting a divergent host.
          packet->data[3] = (ev9_preinit_state == EV9_PREINIT_ACTIVE) ? 0x41U : 0x01U;
          packet->data[4] &= 0xFEU;
        }
        managed = true;
        break;
      }
    }
  }
  if (managed) {
    // This runs under the shared CAN critical section immediately before the
    // safety hook and enqueue, closing the resident-deadline takeover race.
    ev9_preinit_update_crc(packet);
  }
  return true;
}

static bool ev9_long_preinit_external_tx_allowed(const CANPacket_t *packet, uint8_t bus_number,
                                                  bool forwarded) {
  const bool tx_quiescent = (ev9_preinit_state == EV9_PREINIT_RESTORING) ||
                            ev9_preinit_rearm_on_next_can || ev9_preinit_cancel_tx_pending ||
                            (ev9_preinit_off_latched && !forwarded);
  const bool vehicle_bus = (bus_number == EV9_PREINIT_BUS_RADAR) ||
                           (bus_number == EV9_PREINIT_BUS_ECAN);
  if (tx_quiescent && vehicle_bus) {
    return false;
  }
  if (!forwarded && (bus_number == EV9_PREINIT_BUS_ECAN) &&
      (packet->addr == EV9_PREINIT_DIAG_ADDR)) {
    // The resident state machine is the sole owner of session and
    // CommunicationControl for 0x730. The host may only inherit the
    // response-suppressed Tester Present lease after exact ownership and
    // suppression have both been established.
    const bool host_tester_present = !packet->fd && (GET_LEN(packet) == 8U) &&
      (packet->data[0] == 2U) && (packet->data[1] == 0x3EU) &&
      (packet->data[2] == 0x80U) && ev9_preinit_zero_padding(packet, 3U);
    const bool host_lease_allowed = !ev9_preinit_host_tx_quarantine &&
      ((ev9_preinit_state == EV9_PREINIT_ACTIVE) ||
                                     (ev9_preinit_state == EV9_PREINIT_HANDOFF)) &&
      ((ev9_preinit_flags & (EV9_PREINIT_FLAG_BRIDGE_ACTIVE |
                             EV9_PREINIT_FLAG_SUPPRESSION_CONFIRMED)) ==
       (EV9_PREINIT_FLAG_BRIDGE_ACTIVE | EV9_PREINIT_FLAG_SUPPRESSION_CONFIRMED));
    return host_lease_allowed && host_tester_present;
  }
  // Physical forwarding is stock traffic and is allowed again after restore.
  // Host-generated replacements remain blocked until a new exact 68 01 or a
  // fully-off rearm establishes a fresh ownership epoch.
  return forwarded || !ev9_preinit_host_tx_quarantine ||
         !ev9_preinit_managed_host_tx(packet, bus_number);
}

static bool ev9_long_preinit_internal_tx_allowed(const CANPacket_t *packet, uint8_t bus_number) {
  if ((bus_number != packet->bus) || ev9_preinit_cancel_tx_pending || ev9_preinit_rearm_on_next_can) {
    return false;
  }

  if (ev9_preinit_diag_tx_allowed(packet)) {
    const uint8_t service = packet->data[1];
    const uint8_t subfunction = packet->data[2];
    if ((service == 0x10U) && (subfunction == 0x03U)) {
      return !ev9_preinit_off_latched && (ev9_preinit_state == EV9_PREINIT_WAIT_SESSION);
    }
    if ((service == 0x28U) && (subfunction == 0x01U)) {
      return !ev9_preinit_off_latched &&
             ((ev9_preinit_state == EV9_PREINIT_WAIT_COMM_CONTROL) ||
              (ev9_preinit_state == EV9_PREINIT_READY_PENDING_RESPONSE));
    }
    if ((service == 0x28U) && (subfunction == 0x00U)) {
      return ev9_preinit_state == EV9_PREINIT_RESTORING;
    }
    if ((service == 0x10U) && (subfunction == 0x01U)) {
      return (ev9_preinit_state == EV9_PREINIT_RESTORING) ||
             (ev9_preinit_state == EV9_PREINIT_ABORTED) ||
             (ev9_preinit_state == EV9_PREINIT_WAIT_SESSION) ||
             (ev9_preinit_state == EV9_PREINIT_WAIT_COMM_CONTROL) ||
             (ev9_preinit_state == EV9_PREINIT_READY_PENDING_RESPONSE);
    }
    if (service == 0x3EU) {
      return !ev9_preinit_off_latched &&
             ((ev9_preinit_state == EV9_PREINIT_WAIT_SUPPRESSION) ||
              (ev9_preinit_state == EV9_PREINIT_ACTIVE));
    }
    return false;
  }

  const bool bridge_state = (ev9_preinit_state == EV9_PREINIT_WAIT_SUPPRESSION) ||
                            (ev9_preinit_state == EV9_PREINIT_ACTIVE) ||
                            (ev9_preinit_state == EV9_PREINIT_HANDOFF);
  return !ev9_preinit_off_latched && bridge_state &&
         ((ev9_preinit_flags & EV9_PREINIT_FLAG_BRIDGE_ACTIVE) != 0U) &&
         ev9_preinit_bridge_tx_allowed(packet);
}

static bool ev9_long_preinit_tx_drain_allowed(uint8_t bus_number) {
  return !ev9_preinit_cancel_tx_pending ||
         ((bus_number != EV9_PREINIT_BUS_RADAR) && (bus_number != EV9_PREINIT_BUS_ECAN));
}

static bool ev9_preinit_host_lease_fresh(uint32_t now_us) {
  bool fresh = ev9_preinit_host_fresh(now_us, ev9_preinit_last_host_heartbeat_us, 10000U) &&
               (ev9_preinit_last_host_tp_us != 0U) &&
               (get_ts_elapsed(now_us, ev9_preinit_last_host_tp_us) < EV9_PREINIT_HOST_TP_TIMEOUT_US);
  for (uint8_t i = 0U; i < EV9_PREINIT_REPLAY_COUNT; i++) {
    fresh = fresh && ev9_preinit_host_fresh(now_us, ev9_preinit_replay[i].last_host_tx_us,
                                            ev9_preinit_replay[i].period_us);
  }
  return fresh;
}

static bool ev9_preinit_restore_tx_idle(void) {
  return ev9_preinit_can_tx_idle(EV9_PREINIT_BUS_RADAR) &&
         ev9_preinit_can_tx_idle(EV9_PREINIT_BUS_ECAN);
}

static void ev9_preinit_schedule_tx_cancel(bool rearm_after) {
  ev9_preinit_cancel_tx_pending = true;
  ev9_preinit_cancel_rearm_after = ev9_preinit_cancel_rearm_after || rearm_after;
  // RX only performs constant-time register writes. A staged main-loop service
  // proves clock wake, dual INIT, RX drain, reconfiguration, and RUNNING.
  ev9_preinit_can_request_tx_reset(microsecond_timer_get());
}

static bool ev9_preinit_complete_tx_cancel(ev9_preinit_can_reset_result_t reset_result) {
  if (!ev9_preinit_cancel_tx_pending) {
    return true;
  }
  if (reset_result == EV9_PREINIT_CAN_RESET_FAILED) {
    ev9_preinit_can_reset_failed = true;
    ev9_preinit_flags |= EV9_PREINIT_FLAG_INTERNAL_TX_REJECTED;
    return false;
  }
  if ((reset_result != EV9_PREINIT_CAN_RESET_COMPLETE) || !ev9_preinit_restore_tx_idle()) {
    return false;
  }
  ev9_preinit_cancel_tx_pending = false;
  if (ev9_preinit_cancel_rearm_after) {
    ev9_preinit_rearm_on_next_can = true;
  }
  ev9_preinit_cancel_rearm_after = false;
  return true;
}

static void ev9_preinit_finish_restore(uint32_t now_us) {
  // No replacement can remain in either software or hardware TX FIFO here.
  // Stock convergence or exact 68 00 proves that ECU communication is live.
  const bool warm_rearm_proven = ev9_preinit_off_latched && ev9_preinit_warm_rearm_candidate;
  if (!warm_rearm_proven) {
    ev9_preinit_warm_rearm_candidate = false;
  }
  const bool cleanup_needed = (ev9_preinit_comm_control_response_us != 0U) ||
                              ev9_preinit_restore_response_confirmed || ev9_preinit_recovery_restore;
  bool cleanup_queued = false;
  if (cleanup_needed) {
    cleanup_queued = ev9_preinit_return_to_default_session();
  }
  // The host observes status asynchronously. Keep its managed replacement set
  // quarantined after stock is proven live so it cannot race the restored ECU.
  ev9_preinit_host_tx_quarantine = true;
  // Entering ABORTED directly is the sole path that may preserve a candidate,
  // and only this exact restore proof can reach it. Every other abort clears.
  ev9_preinit_enter_aborted(now_us);
  if (ev9_preinit_release_requested || ev9_preinit_recovery_restore) {
    ev9_preinit_release_cleanup_pending = cleanup_queued;
    ev9_preinit_release_cleanup_us = now_us;
    ev9_preinit_release_complete = !cleanup_queued;
  }
}

static bool ev9_long_preinit_must_preserve(void) {
  const bool ownership_state = (ev9_preinit_state == EV9_PREINIT_WAIT_SESSION) ||
                               (ev9_preinit_state == EV9_PREINIT_WAIT_COMM_CONTROL) ||
                               (ev9_preinit_state == EV9_PREINIT_READY_PENDING_RESPONSE) ||
                               (ev9_preinit_state == EV9_PREINIT_WAIT_SUPPRESSION) ||
                               (ev9_preinit_state == EV9_PREINIT_ACTIVE) ||
                               (ev9_preinit_state == EV9_PREINIT_HANDOFF) ||
                               (ev9_preinit_state == EV9_PREINIT_RESTORING);
  return ownership_state || ev9_preinit_comm_control_unresolved || ev9_preinit_cancel_tx_pending ||
         ev9_preinit_rearm_on_next_can ||
         ((ev9_preinit_flags & EV9_PREINIT_FLAG_BRIDGE_ACTIVE) != 0U) ||
         (ev9_preinit_release_requested && !ev9_preinit_release_complete) ||
         (ev9_preinit_recovery_restore && !ev9_preinit_release_complete);
}

static bool ev9_preinit_valid_safety_param(uint16_t param) {
  // EV9 profile base plus the single non-actuating StarPilot engagement option.
  const uint16_t required = 0x8495U;
  const uint16_t optional = 0x0800U;
  const uint16_t allowed = required | optional;
  return ((param & required) == required) && ((param | optional) == allowed);
}

static bool ev9_long_preinit_preserve_can_on_safety_transition(uint16_t mode, uint16_t param) {
  return ev9_long_preinit_must_preserve() && (mode == EV9_PREINIT_SAFETY_MODEL) &&
         ev9_preinit_valid_safety_param(param) &&
         ((current_safety_mode == SAFETY_NOOUTPUT) || (current_safety_mode == EV9_PREINIT_SAFETY_MODEL));
}

static bool ev9_long_preinit_usb_request_allowed(uint8_t request, uint16_t param1, uint16_t param2) {
  const bool late_firmware_query = (request == 0xDCU) && (param1 == SAFETY_ELM327) &&
                                   ev9_preinit_ignition_prev && !ev9_preinit_off_latched &&
                                   !ev9_preinit_rearm_on_next_can &&
                                   (ev9_preinit_state == EV9_PREINIT_COLLECTING);
  if (late_firmware_query) {
    // Pandad starts its firmware query after IsOnroad rises, which can be up
    // to one 10 Hz host cycle after raw ignition. Do not let that late ELM327
    // request overwrite the stable NOOUTPUT installed by the resident start
    // path. OFF/body wakes and terminal READY/ABORTED states remain queryable;
    // exact EV9 identity plus stationary proof still gate diagnostics.
    return false;
  }
  if (!ev9_long_preinit_must_preserve() || (request == EV9_PREINIT_USB_CONTROL_REQUEST)) {
    return true;
  }

  switch (request) {
    case 0xC5U:  // relay drive
    case 0xD1U:  // bootloader/softloader
    case 0xD8U:  // MCU reset
    case 0xDBU:  // CAN mux
    case 0xF8U:  // heartbeat disable
      return false;
    case 0xDCU:  // safety mode: only the exact EV9 profile may inherit ownership
      return (param1 == EV9_PREINIT_SAFETY_MODEL) && ev9_preinit_valid_safety_param(param2);
    case 0xDEU:  // nominal bitrate: idempotent profile configuration only
      return (param1 < PANDA_CAN_CNT) && (bus_config[param1].can_speed == param2);
    case 0xE5U:  // loopback
      return can_loopback == (param1 > 0U);
    case 0xE7U:  // power saving: disabling is safe; enabling can stall the resident bridge
      return param1 == 0U;
    case 0xE8U:  // CAN-FD auto
      return (param1 < PANDA_CAN_CNT) && (bus_config[param1].canfd_auto == (param2 > 0U));
    case 0xF1U:  // RX or unrelated bus clear only
      return (param1 == 0xFFFFU) || (param1 >= PANDA_CAN_CNT) ||
             ((param1 != EV9_PREINIT_BUS_RADAR) && (param1 != EV9_PREINIT_BUS_ECAN));
    case 0xF9U:  // data bitrate: idempotent profile configuration only
      return (param1 < PANDA_CAN_CNT) && (bus_config[param1].can_data_speed == param2);
    case 0xFCU:  // non-ISO mode: idempotent profile configuration only
      return (param1 < PANDA_CAN_CNT) && (bus_config[param1].canfd_non_iso == (param2 != 0U));
    default:
      return true;
  }
}

static bool ev9_preinit_request_release(uint32_t now_us, uint16_t cycle_token, bool validate_token,
                                        bool recovery_restore) {
  if (validate_token && (cycle_token != (uint16_t)ev9_preinit_cycle_started_us)) {
    return false;
  }
  if (ev9_preinit_release_complete) {
    return true;
  }
  if (ev9_preinit_release_requested) {
    // Heartbeat loss is sampled repeatedly until stock restoration completes.
    // Preserve the in-flight restore/cleanup state instead of resetting its
    // proof on every watchdog tick.
    ev9_preinit_recovery_restore = ev9_preinit_recovery_restore || recovery_restore;
    return true;
  }

  ev9_preinit_release_requested = true;
  ev9_preinit_release_complete = false;
  ev9_preinit_release_cleanup_pending = false;
  ev9_preinit_recovery_restore = ev9_preinit_recovery_restore || recovery_restore;
  ev9_preinit_ignition_low_handoff_candidate = false;
  ev9_preinit_warm_rearm_candidate = false;
  ev9_preinit_host_tx_quarantine = true;

  const bool ownership_possible =
    ((ev9_preinit_flags & EV9_PREINIT_FLAG_BRIDGE_ACTIVE) != 0U) ||
    ev9_preinit_comm_control_unresolved || (ev9_preinit_comm_control_response_us != 0U) ||
    recovery_restore;
  if (ownership_possible) {
    const bool restore_already_active = ev9_preinit_state == EV9_PREINIT_RESTORING;
    ev9_preinit_begin_restore(now_us);
    if (!restore_already_active) {
      ev9_preinit_schedule_tx_cancel(false);
    }
  } else if (ev9_preinit_state != EV9_PREINIT_RESTORING) {
    bool cleanup_queued = false;
    if ((ev9_preinit_state == EV9_PREINIT_WAIT_SESSION) ||
        (ev9_preinit_state == EV9_PREINIT_WAIT_COMM_CONTROL) ||
        (ev9_preinit_state == EV9_PREINIT_READY_PENDING_RESPONSE)) {
      cleanup_queued = ev9_preinit_return_to_default_session();
    }
    ev9_preinit_enter_aborted(now_us);
    ev9_preinit_release_cleanup_pending = cleanup_queued;
    ev9_preinit_release_cleanup_us = now_us;
    ev9_preinit_release_complete = !cleanup_queued;
  }
  return true;
}

static bool ev9_preinit_safe_release_boundary(uint32_t now_us) {
  const bool bus_asleep = (ev9_preinit_last_can_us != 0U) && !ev9_preinit_ignition_prev &&
                          (get_ts_elapsed(now_us, ev9_preinit_last_can_us) >= EV9_PREINIT_BUS_SLEEP_US);
  return ev9_preinit_off_latched || bus_asleep;
}

static bool ev9_long_preinit_request_release(uint16_t cycle_token) {
  bool accepted;
  ENTER_CRITICAL();
  const uint32_t now_us = microsecond_timer_get();
  // A valid cycle token authenticates the caller, but it is not proof that
  // restoring stock ADAS is safe under the installed EV9 LONG safety model.
  // Require the firmware's own debounced OFF edge or a five-second quiet bus.
  accepted = ev9_preinit_safe_release_boundary(now_us) &&
             ev9_preinit_request_release(now_us, cycle_token, true, false);
  EXIT_CRITICAL();
  return accepted;
}

static void ev9_preinit_revoke_host_lease(void) {
  if ((ev9_preinit_flags & EV9_PREINIT_FLAG_BRIDGE_ACTIVE) == 0U) {
    return;
  }

  ev9_preinit_flags &= (uint8_t)~EV9_PREINIT_FLAG_HOST_HANDOFF;
  ev9_preinit_host_mask = 0U;
  ev9_preinit_host_hw_mask = 0U;
  ev9_preinit_host_hw_pending_mask = 0U;
  ev9_preinit_host_heartbeat_hw_pending = false;
  ev9_preinit_host_tp_hw_pending = false;
  ev9_preinit_last_host_heartbeat_us = 0U;
  ev9_preinit_last_host_tp_us = 0U;
  for (uint8_t i = 0U; i < EV9_PREINIT_REPLAY_COUNT; i++) {
    ev9_preinit_replay[i].last_host_tx_us = 0U;
    ev9_preinit_replay[i].host_hw_pending = false;
  }
  ev9_preinit_clear_slow_claim_reservations(true);
  // While the SOM heartbeat is absent, the resident bridge is the sole managed
  // publisher. A fresh heartbeat re-opens the normal safety-gated claim path.
  ev9_preinit_host_tx_quarantine = true;
  ev9_preinit_host_watchdog_quarantine = true;
}

static void ev9_long_preinit_host_watchdog_lost(uint32_t now_us, bool vehicle_live) {
  ENTER_CRITICAL();
  if ((ev9_preinit_state == EV9_PREINIT_HANDOFF) && !vehicle_live &&
      ev9_preinit_safe_release_boundary(now_us)) {
    (void)ev9_preinit_request_release(now_us, 0U, false, false);
  } else if ((ev9_preinit_state != EV9_PREINIT_HANDOFF) && ev9_long_preinit_must_preserve()) {
    if (vehicle_live || !ev9_preinit_safe_release_boundary(now_us)) {
      // Before handoff, keep the already-proven resident bridge authoritative.
      // A completed handoff is intentionally one-way until ignition OFF.
      ev9_preinit_revoke_host_lease();
    } else {
      (void)ev9_preinit_request_release(now_us, 0U, false, false);
    }
  }
  EXIT_CRITICAL();
}

static void ev9_preinit_advance_diag(uint32_t now_us) {
  const bool diag_in_flight = (ev9_preinit_state == EV9_PREINIT_WAIT_SESSION) ||
                              (ev9_preinit_state == EV9_PREINIT_WAIT_COMM_CONTROL) ||
                              (ev9_preinit_state == EV9_PREINIT_READY_PENDING_RESPONSE);
  if (diag_in_flight && ev9_preinit_diag_deadline_reached(now_us)) {
    ev9_preinit_flags |= EV9_PREINIT_FLAG_DEADLINE_MISSED;
    if ((ev9_preinit_state == EV9_PREINIT_WAIT_COMM_CONTROL) ||
        (ev9_preinit_state == EV9_PREINIT_READY_PENDING_RESPONSE)) {
      // An outstanding 0x28 may have taken effect even when its response was
      // lost. Restore communication, but never infer bridge ownership.
      ev9_preinit_comm_control_in_flight = false;
      if (ev9_preinit_comm_control_unresolved && !ev9_preinit_nrc_retry_pending) {
        ev9_preinit_begin_restore(now_us);
      } else {
        (void)ev9_preinit_return_to_default_session();
        ev9_preinit_abort(now_us);
      }
    } else if (ev9_preinit_state == EV9_PREINIT_WAIT_SESSION) {
      ev9_preinit_session_in_flight = false;
      (void)ev9_preinit_return_to_default_session();
      ev9_preinit_abort(now_us);
    } else {
    }
    return;
  }

  if ((ev9_preinit_state == EV9_PREINIT_WAIT_SESSION) &&
      (get_ts_elapsed(now_us, ev9_preinit_state_started_us) >= EV9_PREINIT_P2_TIMEOUT_US)) {
    ev9_preinit_session_in_flight = false;
    // A P2-expired session request is no longer outstanding. Permit one
    // non-overlapping retry after silence. An explicit retryable NRC retains
    // the existing three-attempt service budget because each negative response
    // conclusively closes the preceding request.
    const uint8_t max_attempts = ev9_preinit_nrc_retry_pending ? EV9_PREINIT_MAX_ATTEMPTS :
                                 EV9_PREINIT_SESSION_NO_RESPONSE_MAX_ATTEMPTS;
    if ((ev9_preinit_attempts < max_attempts) &&
        !ev9_preinit_powertrain_terminal()) {
      ev9_preinit_send_session(now_us);
    } else {
      (void)ev9_preinit_return_to_default_session();
      ev9_preinit_abort(now_us);
    }
  } else if ((ev9_preinit_state == EV9_PREINIT_WAIT_COMM_CONTROL) &&
             (get_ts_elapsed(now_us, ev9_preinit_state_started_us) >= EV9_PREINIT_P2_TIMEOUT_US)) {
    ev9_preinit_comm_control_in_flight = false;
    if (((ev9_preinit_attempts == 0U) || ev9_preinit_nrc_retry_pending) &&
        (ev9_preinit_attempts < EV9_PREINIT_MAX_ATTEMPTS) &&
        !ev9_preinit_powertrain_terminal()) {
      ev9_preinit_send_comm_control(now_us);
    } else if (ev9_preinit_comm_control_unresolved && !ev9_preinit_nrc_retry_pending) {
      // Never overlap unanswered 28 requests. Preserve the single accepted
      // request through the hard global deadline without further TX.
      ev9_preinit_state = EV9_PREINIT_READY_PENDING_RESPONSE;
    } else {
      (void)ev9_preinit_return_to_default_session();
      ev9_preinit_abort(now_us);
    }
  } else {
  }
}

static void ev9_preinit_service_state(uint32_t now_us, ev9_preinit_can_reset_result_t reset_result) {
  ev9_preinit_advance_diag(now_us);

  // A completed off-cycle drain waits passively for the first valid physical
  // frame. Repeated core resets here could erase that wake frame.
  if (ev9_preinit_rearm_on_next_can) {
    return;
  }

  if (!ev9_preinit_complete_tx_cancel(reset_result)) {
    return;
  }
  if (ev9_preinit_rearm_on_next_can) {
    return;
  }

  if (ev9_preinit_release_cleanup_pending && (ev9_preinit_state == EV9_PREINIT_ABORTED) &&
      (get_ts_elapsed(now_us, ev9_preinit_release_cleanup_us) >= EV9_PREINIT_P2_TIMEOUT_US) &&
      ev9_preinit_restore_tx_idle()) {
    ev9_preinit_release_cleanup_pending = false;
    ev9_preinit_release_complete = true;
  }

  const bool recovery_vehicle_live = (ev9_preinit_last_vehicle_frame_us != 0U) &&
    (get_ts_elapsed(now_us, ev9_preinit_last_vehicle_frame_us) < EV9_PREINIT_REAPPEAR_CONFIRM_US);
  const bool recovery_identity = (ev9_preinit_fingerprint & (EV9_FP_POWERTRAIN | EV9_FP_WHEEL_SPEEDS)) ==
                                 (EV9_FP_POWERTRAIN | EV9_FP_WHEEL_SPEEDS);
  if ((ev9_preinit_state == EV9_PREINIT_ABORTED) && (ev9_preinit_ready_us != 0U) &&
      !ev9_preinit_off_latched && (ev9_preinit_last_critical_adas_us == 0U) &&
      recovery_identity && recovery_vehicle_live &&
      (get_ts_elapsed(now_us, ev9_preinit_ready_us) >= EV9_PREINIT_RESET_RECOVERY_QUIET_US)) {
    // Reset/brownout recovery only: READY plus sustained absence of every
    // critical ADAS publisher indicates that an earlier Panda may have left the
    // ECU communication-disabled. Quarantine host TX and issue only bounded
    // restore/default-session cleanup; never attempt a late knockout.
    (void)ev9_preinit_request_release(now_us, 0U, false, true);
    return;
  }

  const bool all_can_stale = (ev9_preinit_last_can_us != 0U) &&
    (get_ts_elapsed(now_us, ev9_preinit_last_can_us) >= EV9_PREINIT_BUS_SLEEP_US);
  // Direct OFF-to-READY has a measured 5.162 s 0x35/0xA0 blackout while
  // ignition and other physical ADAS traffic remain live. Preserve the cycle
  // through that transition; only a genuinely quiet, ignition-off bus may
  // restore or rearm the resident state machine. Apply this before periodic
  // diagnostics so the rearm boundary cannot emit a stale Tester Present.
  const bool vehicle_asleep = all_can_stale && !ev9_preinit_ignition_prev;
  if (vehicle_asleep && ((ev9_preinit_state == EV9_PREINIT_WAIT_SUPPRESSION) ||
                        (ev9_preinit_state == EV9_PREINIT_ACTIVE) ||
                        (ev9_preinit_state == EV9_PREINIT_HANDOFF))) {
    ev9_preinit_begin_restore(now_us);
  } else if (vehicle_asleep && (ev9_preinit_state == EV9_PREINIT_COLLECTING)) {
    // Never combine a partial vehicle identity from one wake with the next.
    ev9_long_preinit_reset_cycle();
    return;
  } else if (vehicle_asleep && (ev9_preinit_state == EV9_PREINIT_ABORTED) &&
             !ev9_preinit_warm_rearm_candidate) {
    // Abort paths may have queued a best-effort 10 01 cleanup behind a bus-off
    // request. Drain both software and hardware before the next cold wake
    // epoch. A proven HANDOFF -> OFF restore is different: it owns a warm
    // rearm token and must remain latched through any seated/body-network
    // sleep/wake chatter until a later physical ignition rise consumes that
    // token. Otherwise the first restored stock heartbeat can immediately
    // become a new ADAS-wake trigger while ignition is still low.
    ev9_preinit_schedule_tx_cancel(true);
    (void)ev9_preinit_complete_tx_cancel(reset_result);
    return;
  } else if (vehicle_asleep && (ev9_preinit_state == EV9_PREINIT_RESTORING) &&
             (get_ts_elapsed(now_us, ev9_preinit_restore_quiesce_us) >= EV9_PREINIT_RESTORE_DRAIN_US)) {
    // Five seconds of physical silence is a safe cancellation boundary. Purge
    // stale software and hardware TX before accepting the next CAN frame as a
    // new ECU power/wake epoch.
    ev9_preinit_schedule_tx_cancel(true);
    (void)ev9_preinit_complete_tx_cancel(reset_result);
    return;
  } else {
  }

  if (ev9_preinit_state == EV9_PREINIT_WAIT_SUPPRESSION) {
    const bool quiet = (get_ts_elapsed(now_us, ev9_preinit_state_started_us) >=
                        EV9_PREINIT_SUPPRESSION_QUIET_US) &&
      (ev9_preinit_last_critical_adas_us != 0U) &&
      (get_ts_elapsed(now_us, ev9_preinit_last_critical_adas_us) >= EV9_PREINIT_SUPPRESSION_QUIET_US);
    const bool vehicle_live = (ev9_preinit_last_vehicle_frame_us != 0U) &&
      (get_ts_elapsed(now_us, ev9_preinit_last_vehicle_frame_us) < EV9_PREINIT_REAPPEAR_CONFIRM_US);
    if (quiet && vehicle_live) {
      ev9_preinit_state = EV9_PREINIT_ACTIVE;
      ev9_preinit_state_started_us = now_us;
      ev9_preinit_flags |= EV9_PREINIT_FLAG_SUPPRESSION_CONFIRMED;
      ev9_preinit_suppression_confirmed_us = now_us;
      ev9_preinit_outcome_us = now_us;
    } else if ((get_ts_elapsed(now_us, ev9_preinit_state_started_us) >= EV9_PREINIT_SUPPRESSION_TIMEOUT_US) &&
               (ev9_preinit_reappear_started_us != 0U) &&
               (get_ts_elapsed(now_us, ev9_preinit_last_critical_adas_us) <= EV9_PREINIT_REAPPEAR_GAP_US)) {
      // A timeout without any post-ownership OEM frame is not restore evidence.
      // Keep the proven-owned bridge alive until the vehicle becomes observable.
      ev9_preinit_begin_restore(now_us);
    } else {
    }
  }

  if (ev9_preinit_state == EV9_PREINIT_RESTORING) {
    if (ev9_preinit_rearm_on_next_can) {
      return;
    }
    if ((ev9_preinit_restore_response_confirmed || ev9_preinit_restore_converged(now_us)) &&
        ev9_preinit_restore_tx_idle()) {
      ev9_preinit_finish_restore(now_us);
      return;
    }
  }

  if ((ev9_preinit_state == EV9_PREINIT_RESTORING) &&
      !ev9_preinit_restore_response_confirmed &&
      (get_ts_elapsed(now_us, ev9_preinit_restore_quiesce_us) >= EV9_PREINIT_RESTORE_DRAIN_US) &&
      (ev9_preinit_restore_attempts < EV9_PREINIT_RESTORE_MAX_ATTEMPTS) &&
      ((ev9_preinit_restore_attempts == 0U) ||
       (get_ts_elapsed(now_us, ev9_preinit_last_restore_attempt_us) >= EV9_PREINIT_RESTORE_RETRY_US))) {
    // Restore requests start only after the bridge has quiesced and both TX
    // paths are empty. No replacement is ever generated in RESTORING.
    ev9_preinit_try_restore(now_us);
  }

  if ((ev9_preinit_state == EV9_PREINIT_RESTORING) &&
      !ev9_preinit_release_requested &&
      !ev9_preinit_off_latched &&
      (((ev9_preinit_flags & EV9_PREINIT_FLAG_BRIDGE_ACTIVE) != 0U) ||
       (ev9_preinit_comm_control_response_us != 0U)) &&
      (ev9_preinit_restore_attempts >= EV9_PREINIT_RESTORE_MAX_ATTEMPTS) &&
      (ev9_preinit_last_restore_attempt_us != 0U) &&
      (get_ts_elapsed(now_us, ev9_preinit_last_restore_attempt_us) >= EV9_PREINIT_RESTORE_FALLBACK_US) &&
      ((ev9_preinit_last_critical_adas_us == 0U) ||
       (get_ts_elapsed(now_us, ev9_preinit_last_critical_adas_us) >= EV9_PREINIT_RESTORE_FALLBACK_US)) &&
      ev9_preinit_restore_tx_idle()) {
    // All restore requests were wire-visible but neither an exact 68 00 nor
    // stock publication followed. Resume the bridge whose ownership was
    // proven by 68 01; continuing with no publisher is the worse containment.
    ev9_preinit_restore_queued = false;
    ev9_preinit_restore_response_confirmed = false;
    ev9_preinit_reappear_started_us = 0U;
    ev9_preinit_start_tentative_bridge(now_us, true);
    ev9_preinit_restore_fallback_active = true;
    return;
  }

  if (((ev9_preinit_state == EV9_PREINIT_WAIT_SUPPRESSION) ||
       (ev9_preinit_state == EV9_PREINIT_ACTIVE)) &&
      (get_ts_elapsed(now_us, ev9_preinit_last_tester_present_us) >=
       EV9_PREINIT_TESTER_PRESENT_INTERVAL_US)) {
    ev9_preinit_last_tester_present_us = now_us;
    (void)ev9_preinit_send_diag_request(0x3EU, 0x80U, 0U);
  }

  if (((ev9_preinit_state == EV9_PREINIT_WAIT_SUPPRESSION) ||
       (ev9_preinit_state == EV9_PREINIT_ACTIVE) || (ev9_preinit_state == EV9_PREINIT_HANDOFF)) &&
      (ev9_preinit_reappear_started_us != 0U) &&
      (get_ts_elapsed(now_us, ev9_preinit_last_critical_adas_us) > EV9_PREINIT_REAPPEAR_GAP_US)) {
    ev9_preinit_reappear_started_us = 0U;
  } else if (((ev9_preinit_state == EV9_PREINIT_WAIT_SUPPRESSION) ||
              (ev9_preinit_state == EV9_PREINIT_ACTIVE) || (ev9_preinit_state == EV9_PREINIT_HANDOFF)) &&
             (ev9_preinit_reappear_started_us != 0U) &&
             (get_ts_elapsed(now_us, ev9_preinit_reappear_started_us) >= EV9_PREINIT_REAPPEAR_CONFIRM_US)) {
    ev9_preinit_begin_restore(now_us);
  }
  if (ev9_preinit_state != EV9_PREINIT_RESTORING) {
    ev9_preinit_publish_bridge(now_us);
  }
}

static void ev9_long_preinit_service_tx_cancel(uint32_t now_us) {
  // The normal red LED fade can keep the outer main loop blocked for hundreds
  // of milliseconds. An OFF-edge FDCAN purge has a per-phase 20 ms deadline,
  // so advance only that already-requested purge from inside the fade. Do not
  // run diagnostics, identity, bridge publication, or ownership transitions
  // from this high-cadence path.
  if (!ev9_preinit_cancel_tx_pending) {
    return;
  }

  const ev9_preinit_can_reset_result_t reset_result = ev9_preinit_can_service_tx_reset(now_us);
  if ((reset_result == EV9_PREINIT_CAN_RESET_COMPLETE) ||
      (reset_result == EV9_PREINIT_CAN_RESET_FAILED)) {
    ENTER_CRITICAL();
    (void)ev9_preinit_complete_tx_cancel(reset_result);
    EXIT_CRITICAL();
  }
}

static void ev9_long_preinit_tick(uint32_t now_us, bool ignition) {
  // Each poll advances at most one reset phase and contains no delay/poll loop.
  // Keep FDCAN RAM/register work outside the state-machine critical section.
  const ev9_preinit_can_reset_result_t reset_result = ev9_preinit_can_service_tx_reset(now_us);
  // The harness ignition input is a raw GPIO sampled in the unbounded main
  // loop. Hold a low level briefly before treating it as the terminal OFF edge.
  const bool raw_ignition_low = ev9_preinit_ignition_prev && !ignition;
  const bool preempt_firmware_query = ignition && !ev9_preinit_rearm_on_next_can &&
                                      !ev9_preinit_cancel_tx_pending && !ev9_preinit_off_latched &&
                                      (ev9_preinit_state == EV9_PREINIT_COLLECTING) &&
                                      (current_safety_mode == SAFETY_ELM327);
  if (preempt_firmware_query) {
    // Fob start wakes the body network roughly four seconds before physical
    // ignition, so pandad can already be in temporary ELM327 safety while the
    // resident fingerprint is still empty. Switch to stable NOOUTPUT on the
    // main-loop ignition sample itself; waiting for RX identity to set
    // pending_start costs another unbounded loop and misses READY. Exact EV9
    // identity plus fresh stationary proof still gate every diagnostic in RX.
    set_safety_mode(SAFETY_NOOUTPUT, 0U);
    heartbeat_counter = 0U;
  }
  const bool preinit_needs_tx = !ev9_preinit_rearm_on_next_can && !ev9_preinit_cancel_tx_pending &&
                               !raw_ignition_low &&
                               (ev9_preinit_pending_start ||
                                (ev9_preinit_state == EV9_PREINIT_WAIT_SESSION) ||
                                (ev9_preinit_state == EV9_PREINIT_WAIT_COMM_CONTROL) ||
                                (ev9_preinit_state == EV9_PREINIT_READY_PENDING_RESPONSE) ||
                                (ev9_preinit_state == EV9_PREINIT_RESTORING) ||
                                ((ev9_preinit_flags & EV9_PREINIT_FLAG_BRIDGE_ACTIVE) != 0U));
  if (ev9_preinit_pending_start && (current_safety_mode != SAFETY_NOOUTPUT)) {
    set_safety_mode(SAFETY_NOOUTPUT, 0U);
  } else if (preinit_needs_tx && (current_safety_mode == SAFETY_SILENT)) {
    set_safety_mode(SAFETY_NOOUTPUT, 0U);
  }
  if (preinit_needs_tx && (current_safety_mode == SAFETY_NOOUTPUT)) {
    heartbeat_counter = 0U;
  }
  // FDCAN RX also services this state machine. Serialize the main-loop
  // fallback with CAN/USB interrupts so a response cannot race a timeout into
  // a duplicate retry or partially applied handoff.
  ENTER_CRITICAL();
  if (ev9_preinit_host_watchdog_quarantine && (heartbeat_counter == 0U) &&
      !ev9_preinit_release_requested && !ev9_preinit_off_latched &&
      ((ev9_preinit_state == EV9_PREINIT_WAIT_SUPPRESSION) ||
       (ev9_preinit_state == EV9_PREINIT_ACTIVE))) {
    ev9_preinit_host_watchdog_quarantine = false;
    ev9_preinit_host_tx_quarantine = false;
  }
  if (ev9_preinit_rearm_on_next_can) {
    // Ignition may rise before the first CAN-FD wake frame. Do not let the old
    // fingerprint reopen diagnostics; only RX can establish the new epoch.
    ev9_preinit_ignition_prev = ignition;
    ev9_preinit_ignition_low_pending = false;
    ev9_preinit_ignition_low_since_us = 0U;
    EXIT_CRITICAL();
    return;
  }
  const bool ignition_rose = ignition && !ev9_preinit_ignition_prev;
  bool ignition_fell = false;
  if (ignition) {
    ev9_preinit_ignition_low_pending = false;
    ev9_preinit_ignition_low_handoff_candidate = false;
    ev9_preinit_ignition_low_since_us = 0U;
  } else if (ev9_preinit_ignition_prev) {
    if (!ev9_preinit_ignition_low_pending) {
      ev9_preinit_ignition_low_pending = true;
      // Capture HANDOFF qualification at the physical low edge, while the
      // final host bodies are still fresh. Card intentionally stops output as
      // soon as Panda publishes ignition low; main-loop or LED latency can
      // otherwise let the lease expire before this 20 ms debounce completes.
      ev9_preinit_ignition_low_handoff_candidate =
        (ev9_preinit_state == EV9_PREINIT_HANDOFF) &&
        ((ev9_preinit_flags & EV9_PREINIT_FLAG_HOST_HANDOFF) != 0U) &&
        (ev9_preinit_handoff_us != 0U) && ev9_preinit_host_lease_fresh(now_us);
      ev9_preinit_ignition_low_since_us = now_us;
    } else if (get_ts_elapsed(now_us, ev9_preinit_ignition_low_since_us) >=
               EV9_PREINIT_IGNITION_FALL_DEBOUNCE_US) {
      ignition_fell = true;
      ev9_preinit_ignition_low_pending = false;
      ev9_preinit_ignition_low_since_us = 0U;
    } else {
    }
  } else {
    ev9_preinit_ignition_low_pending = false;
    ev9_preinit_ignition_low_handoff_candidate = false;
    ev9_preinit_ignition_low_since_us = 0U;
  }
  if (!ev9_preinit_cancel_tx_pending && ignition_fell && !ev9_preinit_off_latched) {
    // A true READY -> OFF edge ends this ownership epoch even while doors,
    // locks, or body controllers keep CAN awake. Restore at once and suppress
    // every new identity/wake retry until either a proven restore plus a later
    // cleanup-gated rise, or a five-second silent epoch, arms fresh CAN.
    ev9_preinit_warm_rearm_candidate = ev9_preinit_ignition_low_handoff_candidate;
    ev9_preinit_ignition_low_handoff_candidate = false;
    ev9_preinit_off_latched = true;
    ev9_preinit_clear_slow_claim_reservations(false);
    const bool ownership_state =
      (ev9_preinit_state == EV9_PREINIT_WAIT_COMM_CONTROL) ||
      (ev9_preinit_state == EV9_PREINIT_READY_PENDING_RESPONSE) ||
      (ev9_preinit_state == EV9_PREINIT_WAIT_SUPPRESSION) ||
      (ev9_preinit_state == EV9_PREINIT_ACTIVE) ||
      (ev9_preinit_state == EV9_PREINIT_HANDOFF) ||
      (ev9_preinit_state == EV9_PREINIT_RESTORING);
    const bool ownership_possible =
      ownership_state &&
      (((ev9_preinit_flags & EV9_PREINIT_FLAG_BRIDGE_ACTIVE) != 0U) ||
       ev9_preinit_comm_control_unresolved || (ev9_preinit_comm_control_response_us != 0U));
    if ((ev9_preinit_state != EV9_PREINIT_RESTORING) &&
        (ev9_preinit_state != EV9_PREINIT_ABORTED)) {
      if (ownership_possible) {
        ev9_preinit_begin_restore(now_us);
      } else {
        ev9_preinit_abort(now_us);
      }
    }
    ev9_preinit_schedule_tx_cancel(false);
  }
  if (ignition_fell) {
    ev9_preinit_ignition_low_handoff_candidate = false;
    ev9_preinit_ignition_prev = false;
  } else if (ignition) {
    ev9_preinit_ignition_prev = true;
  } else {
  }
  if (!ev9_preinit_cancel_tx_pending && ignition_rose && ev9_preinit_off_latched &&
      ev9_preinit_warm_rearm_candidate && (ev9_preinit_state == EV9_PREINIT_ABORTED) &&
      (get_ts_elapsed(now_us, ev9_preinit_state_started_us) >= EV9_PREINIT_P2_TIMEOUT_US)) {
    // Restore proof and a later physical ignition rise are both required.
    // The cleanup 10 01 may already be in hardware, so also give its complete
    // P2 window time to close before purging every hardware/software TX path.
    // An earlier rise is intentionally not deferred: a new low -> rise edge is
    // required before the first valid current-epoch CAN-FD frame may init.
    ev9_preinit_warm_rearm_candidate = false;
    ev9_preinit_schedule_tx_cancel(true);
  }
  // Evaluate the terminal edge before dispatching a start deferred by a
  // SAFETY_SILENT core transition. A pending low also holds the request until
  // it either debounces to OFF or the ignition input recovers.
  if (!ev9_preinit_cancel_tx_pending && !ev9_preinit_off_latched &&
      !ev9_preinit_ignition_low_pending && ev9_preinit_pending_start &&
      (current_safety_mode == SAFETY_NOOUTPUT)) {
    ev9_preinit_pending_start = false;
    if (!ev9_preinit_start_confirmed(now_us)) {
      ev9_preinit_abort(now_us);
    } else if (ev9_preinit_diag_deadline_reached(now_us)) {
      ev9_preinit_flags |= EV9_PREINIT_FLAG_DEADLINE_MISSED;
      ev9_preinit_abort(now_us);
    } else {
      ev9_preinit_send_session(now_us);
    }
  }
  if (!ev9_preinit_cancel_tx_pending && !ev9_preinit_off_latched && ignition) {
    ev9_preinit_flags |= EV9_PREINIT_FLAG_START_INTENT;
    if (ev9_preinit_ignition_us == 0U) {
      ev9_preinit_ignition_us = now_us;
    }
    if (ignition_rose && ev9_preinit_remote_wake_fresh(now_us)) {
      ev9_preinit_climate_takeover_us = now_us;
      ev9_preinit_trigger = EV9_PREINIT_TRIGGER_CLIMATE_TAKEOVER;
      ev9_preinit_trigger_us = now_us;
      ev9_preinit_retry_from_start_cue(now_us, EV9_PREINIT_TRIGGER_CLIMATE_TAKEOVER);
    } else if (ev9_preinit_trigger == EV9_PREINIT_TRIGGER_NONE) {
      ev9_preinit_trigger = EV9_PREINIT_TRIGGER_IGNITION;
      ev9_preinit_trigger_us = now_us;
    }
    if (ignition_rose &&
        (ev9_preinit_trigger != EV9_PREINIT_TRIGGER_CLIMATE_TAKEOVER)) {
      ev9_preinit_retry_from_start_cue(now_us, EV9_PREINIT_TRIGGER_IGNITION);
    }
    ev9_preinit_maybe_start(now_us);
  }
  ev9_preinit_service_state(now_us, reset_result);
  EXIT_CRITICAL();
}
