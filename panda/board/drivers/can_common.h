#include "can_common_declarations.h"

#ifdef PANDA_EV9_LONG_PREINIT
#include "board/ev9_long_preinit.h"
#endif

uint32_t safety_tx_blocked = 0;
uint32_t safety_rx_invalid = 0;
uint32_t tx_buffer_overflow = 0;
uint32_t rx_buffer_overflow = 0;

can_health_t can_health[PANDA_CAN_CNT] = {{0}, {0}, {0}};

// Ignition detected from CAN meessages
bool ignition_can = false;
uint32_t ignition_can_cnt = 0U;
#ifdef PANDA_HKG_REMOTE_START
bool hkg_remote_climate_wake = false;
uint32_t hkg_remote_climate_wake_cnt = 0U;
#endif

bool can_silent = true;
bool can_loopback = false;

// ********************* instantiate queues *********************
#define can_buffer(x, size) \
  static CANPacket_t elems_##x[size]; \
  extern can_ring can_##x; \
  can_ring can_##x = { .w_ptr = 0, .r_ptr = 0, .fifo_size = (size), .elems = (CANPacket_t *)&(elems_##x) };

#ifdef STM32H7
  #define CAN_RX_BUFFER_SIZE 4096U
  #define CAN_TX_BUFFER_SIZE 416U
#else
  #define CAN_RX_BUFFER_SIZE 1024U
  #define CAN_TX_BUFFER_SIZE 256U
#endif

#ifdef STM32H7
// ITCM RAM and DTCM RAM are the fastest for Cortex-M7 core access
__attribute__((section(".axisram"))) can_buffer(rx_q, CAN_RX_BUFFER_SIZE)
__attribute__((section(".itcmram"))) can_buffer(tx1_q, CAN_TX_BUFFER_SIZE)
__attribute__((section(".itcmram"))) can_buffer(tx2_q, CAN_TX_BUFFER_SIZE)
#else  // kept for PC
can_buffer(rx_q, CAN_RX_BUFFER_SIZE)
can_buffer(tx1_q, CAN_TX_BUFFER_SIZE)
can_buffer(tx2_q, CAN_TX_BUFFER_SIZE)
#endif
can_buffer(tx3_q, CAN_TX_BUFFER_SIZE)

// FIXME:
// cppcheck-suppress misra-c2012-9.3
can_ring *can_queues[PANDA_CAN_CNT] = {&can_tx1_q, &can_tx2_q, &can_tx3_q};

// ********************* interrupt safe queue *********************
bool can_pop(can_ring *q, CANPacket_t *elem) {
  bool ret = 0;

  ENTER_CRITICAL();
  if (q->w_ptr != q->r_ptr) {
    *elem = q->elems[q->r_ptr];
    if ((q->r_ptr + 1U) == q->fifo_size) {
      q->r_ptr = 0;
    } else {
      q->r_ptr += 1U;
    }
    ret = 1;
  }
  EXIT_CRITICAL();

  return ret;
}

bool can_push(can_ring *q, const CANPacket_t *elem) {
  bool ret = false;
  uint32_t next_w_ptr;

  ENTER_CRITICAL();
  if ((q->w_ptr + 1U) == q->fifo_size) {
    next_w_ptr = 0;
  } else {
    next_w_ptr = q->w_ptr + 1U;
  }
  if (next_w_ptr != q->r_ptr) {
    q->elems[q->w_ptr] = *elem;
    q->w_ptr = next_w_ptr;
    ret = true;
  }
  EXIT_CRITICAL();
  if (!ret) {
    #ifdef DEBUG
      print("can_push to ");
      if (q == &can_rx_q) {
        print("can_rx_q");
      } else if (q == &can_tx1_q) {
        print("can_tx1_q");
      } else if (q == &can_tx2_q) {
        print("can_tx2_q");
      } else if (q == &can_tx3_q) {
        print("can_tx3_q");
      } else {
        print("unknown");
      }
      print(" failed!\n");
    #endif
  }
  return ret;
}

uint32_t can_slots_empty(const can_ring *q) {
  uint32_t ret = 0;

  ENTER_CRITICAL();
  if (q->w_ptr >= q->r_ptr) {
    ret = q->fifo_size - 1U - q->w_ptr + q->r_ptr;
  } else {
    ret = q->r_ptr - q->w_ptr - 1U;
  }
  EXIT_CRITICAL();

  return ret;
}

void can_clear(can_ring *q) {
  ENTER_CRITICAL();
  q->w_ptr = 0;
  q->r_ptr = 0;
  EXIT_CRITICAL();
  #ifdef PANDA_EV9_LONG_PREINIT
  ENTER_CRITICAL();
  for (uint8_t i = 0U; i < PANDA_CAN_CNT; i++) {
    if (q == can_queues[i]) {
      ev9_long_preinit_tx_queue_cleared(i);
    }
  }
  EXIT_CRITICAL();
  #endif
  // handle TX buffer full with zero ECUs awake on the bus
  refresh_can_tx_slots_available();
}

// assign CAN numbering
// bus num: CAN Bus numbers in panda, sent to/from USB
//    Min: 0; Max: 127; Bit 7 marks message as receipt (bus 129 is receipt for but 1)
// cans: Look up MCU can interface from bus number
// can number: numeric lookup for MCU CAN interfaces (0 = CAN1, 1 = CAN2, etc);
// bus_lookup: Translates from 'can number' to 'bus number'.
// can_num_lookup: Translates from 'bus number' to 'can number'.
// forwarding bus: If >= 0, forward all messages from this bus to the specified bus.

// Helpers
// Panda:       Bus 0=CAN1   Bus 1=CAN2   Bus 2=CAN3
bus_config_t bus_config[PANDA_CAN_CNT] = {
  { .bus_lookup = 0U, .can_num_lookup = 0U, .forwarding_bus = -1, .can_speed = 5000U, .can_data_speed = 20000U, .canfd_auto = false, .canfd_enabled = false, .brs_enabled = false, .canfd_non_iso = false },
  { .bus_lookup = 1U, .can_num_lookup = 1U, .forwarding_bus = -1, .can_speed = 5000U, .can_data_speed = 20000U, .canfd_auto = false, .canfd_enabled = false, .brs_enabled = false, .canfd_non_iso = false },
  { .bus_lookup = 2U, .can_num_lookup = 2U, .forwarding_bus = -1, .can_speed = 5000U, .can_data_speed = 20000U, .canfd_auto = false, .canfd_enabled = false, .brs_enabled = false, .canfd_non_iso = false },
};

void can_init_all(void) {
  for (uint8_t i=0U; i < PANDA_CAN_CNT; i++) {
    bus_config[i].canfd_enabled = false;
    can_clear(can_queues[i]);
    (void)can_init(i);
  }
}

void can_set_orientation(bool flipped) {
  bus_config[0].bus_lookup = flipped ? 2U : 0U;
  bus_config[0].can_num_lookup = flipped ? 2U : 0U;
  bus_config[2].bus_lookup = flipped ? 0U : 2U;
  bus_config[2].can_num_lookup = flipped ? 0U : 2U;
}

#ifdef PANDA_JUNGLE
void can_set_forwarding(uint8_t from, uint8_t to) {
  bus_config[from].forwarding_bus = to;
}
#endif

void ignition_can_hook(CANPacket_t *msg) {
  int len = GET_LEN(msg);

  #ifdef PANDA_HKG_REMOTE_START
  if ((msg->bus == 1U) && (msg->addr == 0x384U) && (len == 8)) {
    hkg_remote_climate_wake = msg->data[3] != 0U;
    hkg_remote_climate_wake_cnt = 0U;
  }
  #endif

  if (msg->bus == 0U) {
    // GM exception
    // Remote-start mode uses 0xC9 bit 4 (SystemPowerMode=Run) for ignition detection.
    // Stock mode uses 0x1F1 bit 1 (SystemPowerMode=Run/Crank Request).
    #ifdef PANDA_GM_REMOTE_START_C9
    if ((msg->addr == 0xC9U) && (len == 8)) {
      ignition_can = (msg->data[6] & 0x10U) != 0U;
      ignition_can_cnt = 0U;
    }
    #else
    if (gm_remote_start_boots_comma) {
      if ((msg->addr == 0xC9U) && (len == 8)) {
        ignition_can = (msg->data[6] & 0x10U) != 0U;
        ignition_can_cnt = 0U;
      }
    } else {
      if ((msg->addr == 0x1F1U) && (len == 8)) {
        // SystemPowerMode (2=Run, 3=Crank Request)
        ignition_can = (msg->data[0] & 0x2U) != 0U;
        ignition_can_cnt = 0U;
      }
    }
    #endif

    // Rivian R1S/T GEN1 exception
    if ((msg->addr == 0x152U) && (len == 8)) {
      // 0x152 overlaps with Subaru pre-global which has this bit as the high beam
      int counter = msg->data[1] & 0xFU;  // max is only 14

      static int prev_counter_rivian = -1;
      if ((counter == ((prev_counter_rivian + 1) % 15)) && (prev_counter_rivian != -1)) {
        // VDM_OutputSignals->VDM_EpasPowerMode
        ignition_can = ((msg->data[7] >> 4U) & 0x3U) == 1U;  // VDM_EpasPowerMode_Drive_On=1
        ignition_can_cnt = 0U;
      }
      prev_counter_rivian = counter;
    }

    // Tesla Model 3/Y exception
    if ((msg->addr == 0x221U) && (len == 8)) {
      // 0x221 overlaps with Rivian which has random data on byte 0
      int counter = msg->data[6] >> 4;

      static int prev_counter_tesla = -1;
      if ((counter == ((prev_counter_tesla + 1) % 16)) && (prev_counter_tesla != -1)) {
        // VCFRONT_LVPowerState->VCFRONT_vehiclePowerState
        int power_state = (msg->data[0] >> 5U) & 0x3U;
        ignition_can = power_state == 0x3;  // VEHICLE_POWER_STATE_DRIVE=3
        ignition_can_cnt = 0U;
      }
      prev_counter_tesla = counter;
    }

    // Tesla Model S pre-AP exception
    if ((msg->addr == 0x101U) && (len == 3)) {
      // Validate Tesla checksum/counter to avoid false positives on overlapping frames.
      int counter = msg->data[1] & 0xFU;
      int checksum = (((msg->addr & 0xFFU) + ((msg->addr >> 8U) & 0xFFU) + msg->data[0] + msg->data[1]) & 0xFFU);

      static int prev_counter_tesla_preap = -1;
      if ((msg->data[2] == checksum) && (counter == ((prev_counter_tesla_preap + 1) % 16)) && (prev_counter_tesla_preap != -1)) {
        // GTW_epasPowerMode=1 is DRIVE_ON, which is the only ignition source on pre-AP cars.
        int power_mode = (msg->data[0] >> 3U) & 0xFU;
        ignition_can = power_mode == 0x1U;
        ignition_can_cnt = 0U;
      }
      prev_counter_tesla_preap = counter;
    }

    // Mazda exception
    if ((msg->addr == 0x9EU) && (len == 8)) {
      ignition_can = (msg->data[0] >> 5) == 0x6U;
      ignition_can_cnt = 0U;
    }

  }
}

bool can_tx_check_min_slots_free(uint32_t min) {
  return
    (can_slots_empty(&can_tx1_q) >= min) &&
    (can_slots_empty(&can_tx2_q) >= min) &&
    (can_slots_empty(&can_tx3_q) >= min);
}

uint8_t calculate_checksum(const uint8_t *dat, uint32_t len) {
  uint8_t checksum = 0U;
  for (uint32_t i = 0U; i < len; i++) {
    checksum ^= dat[i];
  }
  return checksum;
}

void can_set_checksum(CANPacket_t *packet) {
  packet->checksum = 0U;
  packet->checksum = calculate_checksum((uint8_t *) packet, CANPACKET_HEAD_SIZE + GET_LEN(packet));
}

bool can_check_checksum(CANPacket_t *packet) {
  return (calculate_checksum((uint8_t *) packet, CANPACKET_HEAD_SIZE + GET_LEN(packet)) == 0U);
}

static bool can_send_with_result_origin(CANPacket_t *to_push, uint8_t bus_number,
                                        bool skip_tx_hook, bool ev9_preinit_internal) {
  bool queued = false;
  #ifdef PANDA_EV9_LONG_PREINIT
  bool preinit_tx_allowed = true;
  bool preinit_tx_ready = true;
  ENTER_CRITICAL();
  preinit_tx_allowed = ev9_preinit_internal ?
    ev9_long_preinit_internal_tx_allowed(to_push, bus_number) :
    ev9_long_preinit_external_tx_allowed(to_push, bus_number, skip_tx_hook);
  if (preinit_tx_allowed && !ev9_preinit_internal) {
    preinit_tx_ready = ev9_long_preinit_prepare_host_tx(to_push, bus_number, skip_tx_hook);
  }
  #else
  UNUSED(ev9_preinit_internal);
  #endif
  #ifdef PANDA_EV9_LONG_PREINIT
  if (preinit_tx_allowed && preinit_tx_ready && (skip_tx_hook || safety_tx_hook(to_push) != 0)) {
  #else
  if (skip_tx_hook || safety_tx_hook(to_push) != 0) {
  #endif
    if (bus_number < PANDA_CAN_CNT) {
      // add CAN packet to send queue
      queued = can_push(can_queues[bus_number], to_push);
      tx_buffer_overflow += queued ? 0U : 1U;
      #ifdef PANDA_EV9_LONG_PREINIT
      if (queued && !skip_tx_hook) {
        ev9_long_preinit_host_tx_hook(to_push);
      }
      #endif
      process_can(CAN_NUM_FROM_BUS_NUM(bus_number));
    }
  #ifdef PANDA_EV9_LONG_PREINIT
  } else if (!skip_tx_hook && (!preinit_tx_allowed || preinit_tx_ready)) {
  #else
  } else {
  #endif
    safety_tx_blocked += 1U;
    to_push->returned = 0U;
    to_push->rejected = 1U;

    // data changed
    can_set_checksum(to_push);
    rx_buffer_overflow += can_push(&can_rx_q, to_push) ? 0U : 1U;
  #ifdef PANDA_EV9_LONG_PREINIT
  } else {
    // Forwarding is silently quiesced during EV9 restore/rearm. Emitting a
    // rejected receipt for every physical frame would flood the host RX queue.
  }
  #else
  }
  #endif
  #ifdef PANDA_EV9_LONG_PREINIT
  EXIT_CRITICAL();
  #endif
  return queued;
}

bool can_send_with_result(CANPacket_t *to_push, uint8_t bus_number, bool skip_tx_hook) {
  return can_send_with_result_origin(to_push, bus_number, skip_tx_hook, false);
}

#ifdef PANDA_EV9_LONG_PREINIT
bool can_send_ev9_preinit_with_result(CANPacket_t *to_push, uint8_t bus_number) {
  return can_send_with_result_origin(to_push, bus_number, true, true);
}
#endif

void can_send(CANPacket_t *to_push, uint8_t bus_number, bool skip_tx_hook) {
  (void)can_send_with_result(to_push, bus_number, skip_tx_hook);
}

bool is_speed_valid(uint32_t speed, const uint32_t *all_speeds, uint8_t len) {
  bool ret = false;
  for (uint8_t i = 0U; i < len; i++) {
    if (all_speeds[i] == speed) {
      ret = true;
    }
  }
  return ret;
}
