#include "fake_stm.h"
#include "config.h"
#include "can.h"

#define PANDA_EV9_LONG_PREINIT
#define PANDA_HKG_REMOTE_START
// Pull the EV9 state machine into this test translation unit through can_common.h.

bool can_init(uint8_t can_number) { UNUSED(can_number); return true; }
void process_can(uint8_t can_number) { UNUSED(can_number); }
//int safety_tx_hook(CANPacket_t *to_send) { return 1; }

typedef struct harness_configuration harness_configuration;
void refresh_can_tx_slots_available(void);
void can_tx_comms_resume_usb(void) { };
void can_tx_comms_resume_spi(void) { };

#include "health.h"
#include "faults.h"
#include "libc.h"
#include "boards/board_declarations.h"
#include "opendbc/safety/safety.h"
#include "main_definitions.h"

void set_safety_mode(uint16_t mode, uint16_t param) {
  (void)set_safety_hooks(mode, param);
}

#include "drivers/can_common.h"

can_ring *rx_q = &can_rx_q;
can_ring *tx1_q = &can_tx1_q;
can_ring *tx2_q = &can_tx2_q;
can_ring *tx3_q = &can_tx3_q;

static bool ev9_test_rx_idle[3] = {true, true, true};
static uint32_t ev9_test_cancel_count[3] = {0U, 0U, 0U};
static uint32_t ev9_test_freeze_count = 0U;
static bool ev9_test_reset_requested = false;
static bool ev9_test_reset_failed = false;

bool ev9_preinit_can_tx_idle(uint8_t bus_number) {
  can_ring *queue = can_queues[bus_number];
  return can_slots_empty(queue) == (queue->fifo_size - 1U);
}

void ev9_preinit_can_request_tx_reset(uint32_t now_us) {
  UNUSED(now_us);
  if (!ev9_test_reset_requested) {
    ev9_test_freeze_count += 1U;
    ev9_test_reset_requested = true;
  }
}

ev9_preinit_can_reset_result_t ev9_preinit_can_service_tx_reset(uint32_t now_us) {
  UNUSED(now_us);
  if (!ev9_test_reset_requested) {
    return EV9_PREINIT_CAN_RESET_IDLE;
  }
  if (ev9_test_reset_failed) {
    return EV9_PREINIT_CAN_RESET_FAILED;
  }
  if (!ev9_test_rx_idle[EV9_PREINIT_BUS_RADAR] || !ev9_test_rx_idle[EV9_PREINIT_BUS_ECAN]) {
    return EV9_PREINIT_CAN_RESET_PENDING;
  }
  ev9_test_cancel_count[EV9_PREINIT_BUS_RADAR] += 1U;
  ev9_test_cancel_count[EV9_PREINIT_BUS_ECAN] += 1U;
  can_clear(can_queues[EV9_PREINIT_BUS_RADAR]);
  can_clear(can_queues[EV9_PREINIT_BUS_ECAN]);
  ev9_test_reset_requested = false;
  ev9_test_reset_failed = false;
  return EV9_PREINIT_CAN_RESET_COMPLETE;
}

void ev9_test_init(void) {
  MICROSECOND_TIMER->CNT = 0U;
  can_set_orientation(false);
  hkg_remote_climate_wake = false;
  hkg_remote_climate_wake_cnt = 0U;
  (void)set_safety_hooks(SAFETY_NOOUTPUT, 0U);
  (void)memset(can_health, 0, sizeof(can_health));
  can_clear(&can_rx_q);
  can_clear(&can_tx1_q);
  can_clear(&can_tx2_q);
  can_clear(&can_tx3_q);
  for (uint8_t i = 0U; i < 3U; i++) {
    ev9_test_rx_idle[i] = true;
    ev9_test_cancel_count[i] = 0U;
  }
  ev9_test_freeze_count = 0U;
  ev9_test_reset_requested = false;
  ev9_test_reset_failed = false;
  heartbeat_counter = 0U;
  ev9_long_preinit_init();
}

void ev9_test_set_rx_idle(uint8_t bus_number, bool idle) {
  ev9_test_rx_idle[bus_number] = idle;
}

void ev9_test_set_reset_failed(bool failed) {
  ev9_test_reset_failed = failed;
}

void ev9_test_set_can_health(uint8_t bus_number, bool bus_off, bool error_passive,
                             uint8_t transmit_error_cnt) {
  can_health_t *health = &can_health[CAN_NUM_FROM_BUS_NUM(bus_number)];
  health->bus_off = bus_off;
  health->error_passive = error_passive;
  health->transmit_error_cnt = transmit_error_cnt;
}

uint32_t ev9_test_get_cancel_count(uint8_t bus_number) {
  return ev9_test_cancel_count[bus_number];
}

uint32_t ev9_test_get_freeze_count(void) {
  return ev9_test_freeze_count;
}

void ev9_test_set_time(uint32_t now_us) {
  MICROSECOND_TIMER->CNT = now_us;
}

void ev9_test_rx(CANPacket_t *packet, uint32_t now_us) {
  MICROSECOND_TIMER->CNT = now_us;
  ignition_can_hook(packet);
  ev9_long_preinit_rx_hook(packet, now_us);
}

void ev9_test_rx_isr_only(CANPacket_t *packet, uint32_t now_us) {
  MICROSECOND_TIMER->CNT = now_us;
  ignition_can_hook(packet);
  ev9_long_preinit_rx_hook(packet, now_us);
}

void ev9_test_reset_cycle(void) {
  ev9_long_preinit_reset_cycle();
}

uint16_t ev9_test_current_safety_mode(void) {
  return current_safety_mode;
}

void ev9_test_tick(uint32_t now_us, bool ignition) {
  MICROSECOND_TIMER->CNT = now_us;
  ev9_long_preinit_tick(now_us, ignition);
  // Firmware main spins continuously. A second zero-elapsed pass lets the fake
  // staged reset consume a request raised by the first pass without pretending
  // that the RX hook performed a blocking purge.
  ev9_long_preinit_tick(now_us, ignition);
}

void ev9_test_tick_once(uint32_t now_us, bool ignition) {
  MICROSECOND_TIMER->CNT = now_us;
  ev9_long_preinit_tick(now_us, ignition);
}

bool ev9_test_ignition_low_handoff_candidate(void) {
  return ev9_preinit_ignition_low_handoff_candidate;
}

bool ev9_test_warm_rearm_candidate(void) {
  return ev9_preinit_warm_rearm_candidate;
}

void ev9_test_service_tx_cancel(uint32_t now_us) {
  MICROSECOND_TIMER->CNT = now_us;
  ev9_long_preinit_service_tx_cancel(now_us);
}

void ev9_test_host_tx(CANPacket_t *packet, uint32_t now_us) {
  MICROSECOND_TIMER->CNT = now_us;
  ev9_long_preinit_host_tx_hook(packet);
  ev9_long_preinit_tx_hw_loaded(packet, packet->bus);
}

bool ev9_test_prepare_host_tx(CANPacket_t *packet, uint8_t bus_number,
                              bool forwarded, uint32_t now_us) {
  MICROSECOND_TIMER->CNT = now_us;
  return ev9_long_preinit_prepare_host_tx(packet, bus_number, forwarded);
}

void ev9_test_hw_tx(CANPacket_t *packet, uint32_t now_us) {
  MICROSECOND_TIMER->CNT = now_us;
  ev9_long_preinit_tx_hw_loaded(packet, packet->bus);
}

bool ev9_test_request_release(uint16_t cycle_token, uint32_t now_us) {
  MICROSECOND_TIMER->CNT = now_us;
  return ev9_long_preinit_request_release(cycle_token);
}

bool ev9_test_usb_request_allowed(uint8_t request, uint16_t param1, uint16_t param2) {
  return ev9_long_preinit_usb_request_allowed(request, param1, param2);
}

bool ev9_test_must_preserve(void) {
  return ev9_long_preinit_must_preserve();
}

bool ev9_test_preserve_can_on_safety_transition(uint16_t mode, uint16_t param) {
  return ev9_long_preinit_preserve_can_on_safety_transition(mode, param);
}

void ev9_test_host_watchdog_lost(uint32_t now_us, bool vehicle_live) {
  ev9_long_preinit_host_watchdog_lost(now_us, vehicle_live);
}

void ev9_test_tx_queue_cleared(uint8_t bus_number) {
  ev9_long_preinit_tx_queue_cleared(bus_number);
}

void ev9_test_set_heartbeat_counter(uint32_t counter) {
  heartbeat_counter = counter;
}

bool ev9_test_external_tx_allowed(CANPacket_t *packet, uint8_t bus_number, bool forwarded) {
  return ev9_long_preinit_external_tx_allowed(packet, bus_number, forwarded);
}

bool ev9_test_tx_drain_allowed(uint8_t bus_number) {
  return ev9_long_preinit_tx_drain_allowed(bus_number);
}

void ev9_test_update_crc(CANPacket_t *packet) {
  ev9_preinit_update_crc(packet);
}

bool ev9_test_internal_bridge_allowed(CANPacket_t *packet) {
  return ev9_preinit_bridge_tx_allowed(packet);
}

uint8_t ev9_test_bus_from_can_num(uint8_t can_number) {
  return BUS_NUM_FROM_CAN_NUM(can_number);
}

uint8_t ev9_test_can_num_from_bus(uint8_t bus_number) {
  return CAN_NUM_FROM_BUS_NUM(bus_number);
}

void ev9_test_get_status(ev9_long_preinit_status_t *status) {
  *status = ev9_long_preinit_get_status();
}

void ev9_test_get_timing(ev9_long_preinit_timing_t *timing) {
  *timing = ev9_long_preinit_get_timing();
}

#include "comms_definitions.h"
#include "can_comms.h"
