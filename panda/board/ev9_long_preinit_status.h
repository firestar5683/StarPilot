#pragma once

#define EV9_LONG_PREINIT_STATUS_VERSION 4U
#define EV9_LONG_PREINIT_STATUS_PAGE 0U
#define EV9_LONG_PREINIT_TIMING_PAGE 1U

typedef enum {
  EV9_PREINIT_COLLECTING = 0,
  EV9_PREINIT_WAIT_SESSION,
  EV9_PREINIT_WAIT_COMM_CONTROL,
  EV9_PREINIT_WAIT_SUPPRESSION,
  EV9_PREINIT_ACTIVE,
  EV9_PREINIT_HANDOFF,
  EV9_PREINIT_ABORTED,
  EV9_PREINIT_RESTORING,
  EV9_PREINIT_READY_PENDING_RESPONSE,
} ev9_preinit_state_t;

typedef enum {
  EV9_PREINIT_TRIGGER_NONE = 0,
  EV9_PREINIT_TRIGGER_ADAS_WAKE,
  EV9_PREINIT_TRIGGER_IGNITION,
  EV9_PREINIT_TRIGGER_DRIVER_BRAKE,
  EV9_PREINIT_TRIGGER_PRE_READY,
  EV9_PREINIT_TRIGGER_CLIMATE_TAKEOVER,
} ev9_preinit_trigger_t;

typedef enum {
  EV9_PREINIT_FLAG_IDENTITY_VALID = 0x01U,
  EV9_PREINIT_FLAG_START_INTENT = 0x02U,
  EV9_PREINIT_FLAG_SUPPRESSION_CONFIRMED = 0x04U,
  EV9_PREINIT_FLAG_BRIDGE_ACTIVE = 0x08U,
  EV9_PREINIT_FLAG_HOST_HANDOFF = 0x10U,
  EV9_PREINIT_FLAG_DEADLINE_MISSED = 0x20U,
  EV9_PREINIT_FLAG_RESTORE_SENT = 0x40U,
  EV9_PREINIT_FLAG_INTERNAL_TX_REJECTED = 0x80U,
} ev9_preinit_status_flag_t;

// Page 0 of USB request 0xE9. Keep this exactly one USB packet.
typedef struct __attribute__((packed)) {
  uint8_t version;
  uint8_t state;
  uint8_t fingerprint;
  uint8_t attempts;
  uint8_t last_service;
  uint8_t last_response;
  uint8_t last_nrc;
  uint8_t communication_type;
  uint8_t trigger;
  uint8_t first_ecan_len;
  uint8_t powertrain_state;
  uint8_t powertrain_boot_state;
  uint8_t powertrain_init_state;
  uint8_t flags;
  uint16_t first_ecan_addr;
  uint32_t first_can_us;
  uint32_t state_started_us;
  uint32_t trigger_us;
  uint32_t first_ecan_us;
  uint32_t driver_braking_us;
  uint32_t pre_ready_us;
  uint32_t ignition_us;
  uint32_t session_response_us;
  uint32_t comm_control_us;
  uint32_t last_powertrain_us;
  uint32_t ready_us;
  uint32_t outcome_us;
} ev9_long_preinit_status_t;

// Page 1 of USB request 0xE9. Detailed timing is separate so both pages fit
// the Panda control-transfer packet limit.
typedef struct __attribute__((packed)) {
  uint8_t version;
  uint8_t page;
  uint8_t flags;
  uint8_t reserved;
  uint32_t cycle_started_us;
  uint32_t session_request_us;
  uint32_t session_response_us;
  uint32_t comm_control_us;
  uint32_t comm_control_response_us;
  uint32_t last_critical_adas_us;
  uint32_t first_replacement_us;
  uint32_t suppression_confirmed_us;
  uint32_t ready_us;
  uint32_t handoff_us;
  uint32_t restore_us;
  uint32_t abort_us;
  uint32_t last_host_tx_us;
  uint32_t last_tester_present_us;
  uint32_t last_vehicle_frame_us;
} ev9_long_preinit_timing_t;
