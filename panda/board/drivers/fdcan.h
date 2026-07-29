#include "fdcan_declarations.h"

FDCAN_GlobalTypeDef *cans[PANDA_CAN_CNT] = {FDCAN1, FDCAN2, FDCAN3};

static bool can_set_speed(uint8_t can_number) {
  bool ret = true;
  FDCAN_GlobalTypeDef *FDCANx = CANIF_FROM_CAN_NUM(can_number);
  uint8_t bus_number = BUS_NUM_FROM_CAN_NUM(can_number);

  ret &= llcan_set_speed(
    FDCANx,
    bus_config[bus_number].can_speed,
    bus_config[bus_number].can_data_speed,
    bus_config[bus_number].canfd_non_iso,
    can_loopback,
    can_silent
  );
  return ret;
}

void can_clear_send(FDCAN_GlobalTypeDef *FDCANx, uint8_t can_number) {
  static uint32_t last_reset = 0U;
  uint32_t time = microsecond_timer_get();

  // Resetting CAN core is a slow blocking operation, limit frequency
  if (get_ts_elapsed(time, last_reset) > 100000U) {  // 10 Hz
    can_health[can_number].can_core_reset_cnt += 1U;
    can_health[can_number].total_tx_lost_cnt += (FDCAN_TX_FIFO_EL_CNT - (FDCANx->TXFQS & FDCAN_TXFQS_TFFL)); // TX FIFO msgs will be lost after reset
    llcan_clear_send(FDCANx);
    last_reset = time;
  }
}

void update_can_health_pkt(uint8_t can_number, uint32_t ir_reg) {
  uint8_t can_irq_number[PANDA_CAN_CNT][2] = {
    { FDCAN1_IT0_IRQn, FDCAN1_IT1_IRQn },
    { FDCAN2_IT0_IRQn, FDCAN2_IT1_IRQn },
    { FDCAN3_IT0_IRQn, FDCAN3_IT1_IRQn },
  };

  FDCAN_GlobalTypeDef *FDCANx = CANIF_FROM_CAN_NUM(can_number);
  uint32_t psr_reg = FDCANx->PSR;
  uint32_t ecr_reg = FDCANx->ECR;

  can_health[can_number].bus_off = ((psr_reg & FDCAN_PSR_BO) >> FDCAN_PSR_BO_Pos);
  can_health[can_number].bus_off_cnt += can_health[can_number].bus_off;
  can_health[can_number].error_warning = ((psr_reg & FDCAN_PSR_EW) >> FDCAN_PSR_EW_Pos);
  can_health[can_number].error_passive = ((psr_reg & FDCAN_PSR_EP) >> FDCAN_PSR_EP_Pos);

  can_health[can_number].last_error = ((psr_reg & FDCAN_PSR_LEC) >> FDCAN_PSR_LEC_Pos);
  if ((can_health[can_number].last_error != 0U) && (can_health[can_number].last_error != 7U)) {
    can_health[can_number].last_stored_error = can_health[can_number].last_error;
  }

  can_health[can_number].last_data_error = ((psr_reg & FDCAN_PSR_DLEC) >> FDCAN_PSR_DLEC_Pos);
  if ((can_health[can_number].last_data_error != 0U) && (can_health[can_number].last_data_error != 7U)) {
    can_health[can_number].last_data_stored_error = can_health[can_number].last_data_error;
  }

  can_health[can_number].receive_error_cnt = ((ecr_reg & FDCAN_ECR_REC) >> FDCAN_ECR_REC_Pos);
  can_health[can_number].transmit_error_cnt = ((ecr_reg & FDCAN_ECR_TEC) >> FDCAN_ECR_TEC_Pos);

  can_health[can_number].irq0_call_rate = interrupts[can_irq_number[can_number][0]].call_rate;
  can_health[can_number].irq1_call_rate = interrupts[can_irq_number[can_number][1]].call_rate;

  if (ir_reg != 0U) {
    // Clear error interrupts
    FDCANx->IR |= (FDCAN_IR_PED | FDCAN_IR_PEA | FDCAN_IR_EP | FDCAN_IR_BO | FDCAN_IR_RF0L);
    can_health[can_number].total_error_cnt += 1U;
    // Check for RX FIFO overflow
    if ((ir_reg & (FDCAN_IR_RF0L)) != 0U) {
      can_health[can_number].total_rx_lost_cnt += 1U;
    }
    // Cases:
    // 1. while multiplexing between buses 1 and 3 we are getting ACK errors that overwhelm CAN core, by resetting it recovers faster
    // 2. H7 gets stuck in bus off recovery state indefinitely
    if ((((can_health[can_number].last_error == CAN_ACK_ERROR) || (can_health[can_number].last_data_error == CAN_ACK_ERROR)) && (can_health[can_number].transmit_error_cnt > 127U)) ||
     ((ir_reg & FDCAN_IR_BO) != 0U)) {
      can_clear_send(FDCANx, can_number);
    }
  }
}

// ***************************** CAN *****************************
// FDFDCANx_IT1 IRQ Handler (TX)
void process_can(uint8_t can_number) {
  if (can_number != 0xffU) {
    ENTER_CRITICAL();
    uint8_t bus_number = BUS_NUM_FROM_CAN_NUM(can_number);
    FDCAN_GlobalTypeDef *FDCANx = CANIF_FROM_CAN_NUM(can_number);
    FDCANx->IR |= FDCAN_IR_TFE; // Clear Tx FIFO Empty flag
    #ifdef PANDA_EV9_LONG_PREINIT
    if (!ev9_long_preinit_tx_drain_allowed(bus_number)) {
      EXIT_CRITICAL();
      return;
    }
    #endif

    if ((FDCANx->TXFQS & FDCAN_TXFQS_TFQF) == 0U) {
      CANPacket_t to_send;
      if (can_pop(can_queues[bus_number], &to_send)) {
        if (can_check_checksum(&to_send)) {
          can_health[can_number].total_tx_cnt += 1U;

          uint32_t TxFIFOSA = FDCAN_START_ADDRESS + (can_number * FDCAN_OFFSET) + (FDCAN_RX_FIFO_0_EL_CNT * FDCAN_RX_FIFO_0_EL_SIZE);
          // get the index of the next TX FIFO element (0 to FDCAN_TX_FIFO_EL_CNT - 1)
          uint32_t tx_index = (FDCANx->TXFQS >> FDCAN_TXFQS_TFQPI_Pos) & 0x1FU;
          // only send if we have received a packet
          canfd_fifo *fifo;
          fifo = (canfd_fifo *)(TxFIFOSA + (tx_index * FDCAN_TX_FIFO_EL_SIZE));

          fifo->header[0] = (to_send.extended << 30) | ((to_send.extended != 0U) ? (to_send.addr) : (to_send.addr << 18));

          // If canfd_auto is set, outgoing packets will be automatically sent as CAN-FD if an incoming CAN-FD packet was seen
          bool fd = bus_config[can_number].canfd_auto ? bus_config[can_number].canfd_enabled : (bool)(to_send.fd > 0U);
          uint32_t canfd_enabled_header = fd ? (1UL << 21) : 0UL;

          uint32_t brs_enabled_header = bus_config[can_number].brs_enabled ? (1UL << 20) : 0UL;
          fifo->header[1] = (to_send.data_len_code << 16) | canfd_enabled_header | brs_enabled_header;

          uint8_t data_len_w = (dlc_to_len[to_send.data_len_code] / 4U);
          data_len_w += ((dlc_to_len[to_send.data_len_code] % 4U) > 0U) ? 1U : 0U;
          for (unsigned int i = 0; i < data_len_w; i++) {
            BYTE_ARRAY_TO_WORD(fifo->data_word[i], &to_send.data[i*4U]);
          }

          FDCANx->TXBAR = (1UL << tx_index);
          #ifdef PANDA_EV9_LONG_PREINIT
          // TXBAR is the first hardware-visible ownership boundary. Software
          // queue acceptance alone cannot complete a resident-to-host handoff.
          ev9_long_preinit_tx_hw_loaded(&to_send, bus_number);
          #endif

          // Send back to USB
          CANPacket_t to_push;

          to_push.fd = fd;
          to_push.returned = 1U;
          to_push.rejected = 0U;
          to_push.extended = to_send.extended;
          to_push.addr = to_send.addr;
          to_push.bus = bus_number;
          to_push.data_len_code = to_send.data_len_code;
          (void)memcpy(to_push.data, to_send.data, dlc_to_len[to_push.data_len_code]);
          can_set_checksum(&to_push);

          rx_buffer_overflow += can_push(&can_rx_q, &to_push) ? 0U : 1U;
        } else {
          can_health[can_number].total_tx_checksum_error_cnt += 1U;
        }

        refresh_can_tx_slots_available();
      }
    }
    EXIT_CRITICAL();
  }
}

#ifdef PANDA_EV9_LONG_PREINIT
bool ev9_preinit_can_tx_idle(uint8_t bus_number) {
  const uint8_t can_number = CAN_NUM_FROM_BUS_NUM(bus_number);
  FDCAN_GlobalTypeDef *FDCANx = CANIF_FROM_CAN_NUM(can_number);
  can_ring *queue = can_queues[bus_number];
  return (can_slots_empty(queue) == (queue->fifo_size - 1U)) && (FDCANx->TXBRP == 0U);
}

typedef enum {
  EV9_FDCAN_RESET_IDLE = 0,
  EV9_FDCAN_RESET_WAIT_CLOCK,
  EV9_FDCAN_RESET_WAIT_INIT,
  EV9_FDCAN_RESET_WAIT_RX_EMPTY,
  EV9_FDCAN_RESET_CONFIG_RADAR,
  EV9_FDCAN_RESET_CONFIG_ECAN,
  EV9_FDCAN_RESET_WAIT_RUNNING,
  EV9_FDCAN_RESET_DONE,
  EV9_FDCAN_RESET_FAULT,
} ev9_fdcan_reset_state_t;

static ev9_fdcan_reset_state_t ev9_fdcan_reset_state = EV9_FDCAN_RESET_IDLE;
static uint32_t ev9_fdcan_reset_state_started_us = 0U;

void ev9_preinit_can_request_tx_reset(uint32_t now_us) {
  if ((ev9_fdcan_reset_state != EV9_FDCAN_RESET_IDLE) &&
      (ev9_fdcan_reset_state != EV9_FDCAN_RESET_DONE)) {
    return;
  }
  FDCAN_GlobalTypeDef *radar = CANIF_FROM_CAN_NUM(CAN_NUM_FROM_BUS_NUM(EV9_PREINIT_BUS_RADAR));
  FDCAN_GlobalTypeDef *ecan = CANIF_FROM_CAN_NUM(CAN_NUM_FROM_BUS_NUM(EV9_PREINIT_BUS_ECAN));
  // Constant-time request path: RX may call this, so never poll or delay here.
  radar->CCCR &= ~FDCAN_CCCR_CSR;
  ecan->CCCR &= ~FDCAN_CCCR_CSR;
  ev9_fdcan_reset_state = EV9_FDCAN_RESET_WAIT_CLOCK;
  ev9_fdcan_reset_state_started_us = now_us;
}

ev9_preinit_can_reset_result_t ev9_preinit_can_service_tx_reset(uint32_t now_us) {
  const uint8_t radar_number = CAN_NUM_FROM_BUS_NUM(EV9_PREINIT_BUS_RADAR);
  const uint8_t ecan_number = CAN_NUM_FROM_BUS_NUM(EV9_PREINIT_BUS_ECAN);
  FDCAN_GlobalTypeDef *radar = CANIF_FROM_CAN_NUM(radar_number);
  FDCAN_GlobalTypeDef *ecan = CANIF_FROM_CAN_NUM(ecan_number);

  if ((ev9_fdcan_reset_state != EV9_FDCAN_RESET_IDLE) &&
      (ev9_fdcan_reset_state != EV9_FDCAN_RESET_DONE) &&
      (ev9_fdcan_reset_state != EV9_FDCAN_RESET_FAULT) &&
      (get_ts_elapsed(now_us, ev9_fdcan_reset_state_started_us) >= EV9_PREINIT_CAN_RESET_TIMEOUT_US)) {
    ev9_fdcan_reset_state = EV9_FDCAN_RESET_FAULT;
  }

  switch (ev9_fdcan_reset_state) {
    case EV9_FDCAN_RESET_IDLE:
      return EV9_PREINIT_CAN_RESET_IDLE;
    case EV9_FDCAN_RESET_WAIT_CLOCK:
      if (((radar->CCCR & FDCAN_CCCR_CSA) == 0U) && ((ecan->CCCR & FDCAN_CCCR_CSA) == 0U)) {
        radar->CCCR |= FDCAN_CCCR_INIT;
        ecan->CCCR |= FDCAN_CCCR_INIT;
        ev9_fdcan_reset_state = EV9_FDCAN_RESET_WAIT_INIT;
        ev9_fdcan_reset_state_started_us = now_us;
      }
      break;
    case EV9_FDCAN_RESET_WAIT_INIT:
      if (((radar->CCCR & FDCAN_CCCR_INIT) != 0U) && ((ecan->CCCR & FDCAN_CCCR_INIT) != 0U)) {
        ev9_fdcan_reset_state = EV9_FDCAN_RESET_WAIT_RX_EMPTY;
        ev9_fdcan_reset_state_started_us = now_us;
      }
      break;
    case EV9_FDCAN_RESET_WAIT_RX_EMPTY:
      if (((radar->RXF0S & FDCAN_RXF0S_F0FL) == 0U) &&
          ((ecan->RXF0S & FDCAN_RXF0S_F0FL) == 0U)) {
        can_health[radar_number].can_core_reset_cnt += 1U;
        can_health[ecan_number].can_core_reset_cnt += 1U;
        can_health[radar_number].total_tx_lost_cnt +=
          FDCAN_TX_FIFO_EL_CNT - (radar->TXFQS & FDCAN_TXFQS_TFFL);
        can_health[ecan_number].total_tx_lost_cnt +=
          FDCAN_TX_FIFO_EL_CNT - (ecan->TXFQS & FDCAN_TXFQS_TFFL);
        can_clear(can_queues[EV9_PREINIT_BUS_RADAR]);
        can_clear(can_queues[EV9_PREINIT_BUS_ECAN]);
        ev9_fdcan_reset_state = EV9_FDCAN_RESET_CONFIG_RADAR;
        ev9_fdcan_reset_state_started_us = now_us;
      }
      break;
    case EV9_FDCAN_RESET_CONFIG_RADAR:
      radar->IR |= 0x3FCFFFFFU;
      fdcan_configure_in_init(radar);
      ev9_fdcan_reset_state = EV9_FDCAN_RESET_CONFIG_ECAN;
      ev9_fdcan_reset_state_started_us = now_us;
      break;
    case EV9_FDCAN_RESET_CONFIG_ECAN:
      ecan->IR |= 0x3FCFFFFFU;
      fdcan_configure_in_init(ecan);
      radar->CCCR &= ~FDCAN_CCCR_INIT;
      ecan->CCCR &= ~FDCAN_CCCR_INIT;
      ev9_fdcan_reset_state = EV9_FDCAN_RESET_WAIT_RUNNING;
      ev9_fdcan_reset_state_started_us = now_us;
      break;
    case EV9_FDCAN_RESET_WAIT_RUNNING:
      if (((radar->CCCR & FDCAN_CCCR_INIT) == 0U) && ((ecan->CCCR & FDCAN_CCCR_INIT) == 0U)) {
        llcan_irq_enable(radar);
        llcan_irq_enable(ecan);
        ev9_fdcan_reset_state = EV9_FDCAN_RESET_DONE;
      }
      break;
    case EV9_FDCAN_RESET_DONE:
      ev9_fdcan_reset_state = EV9_FDCAN_RESET_IDLE;
      return EV9_PREINIT_CAN_RESET_COMPLETE;
    case EV9_FDCAN_RESET_FAULT:
      return EV9_PREINIT_CAN_RESET_FAILED;
    default:
      ev9_fdcan_reset_state = EV9_FDCAN_RESET_FAULT;
      return EV9_PREINIT_CAN_RESET_FAILED;
  }
  return (ev9_fdcan_reset_state == EV9_FDCAN_RESET_FAULT) ?
         EV9_PREINIT_CAN_RESET_FAILED : EV9_PREINIT_CAN_RESET_PENDING;
}
#endif

// FDFDCANx_IT0 IRQ Handler (RX and errors)
// blink blue when we are receiving CAN messages
void can_rx(uint8_t can_number) {
  FDCAN_GlobalTypeDef *FDCANx = CANIF_FROM_CAN_NUM(can_number);
  uint8_t bus_number = BUS_NUM_FROM_CAN_NUM(can_number);

  uint32_t ir_reg = FDCANx->IR;

  // Clear all new messages from Rx FIFO 0
  FDCANx->IR |= FDCAN_IR_RF0N;
  while ((FDCANx->RXF0S & FDCAN_RXF0S_F0FL) != 0U) {
    can_health[can_number].total_rx_cnt += 1U;
    // get the index of the next RX FIFO element (0 to FDCAN_RX_FIFO_0_EL_CNT - 1)
    uint32_t rx_fifo_idx = (uint8_t)((FDCANx->RXF0S >> FDCAN_RXF0S_F0GI_Pos) & 0x3FU);

    // Recommended to offset get index by at least +1 if RX FIFO is in overwrite mode and full (datasheet)
    if ((FDCANx->RXF0S & FDCAN_RXF0S_F0F) == FDCAN_RXF0S_F0F) {
      rx_fifo_idx = ((rx_fifo_idx + 1U) >= FDCAN_RX_FIFO_0_EL_CNT) ? 0U : (rx_fifo_idx + 1U);
      can_health[can_number].total_rx_lost_cnt += 1U; // At least one message was lost
    }

    uint32_t RxFIFO0SA = FDCAN_START_ADDRESS + (can_number * FDCAN_OFFSET);
    CANPacket_t to_push;
    canfd_fifo *fifo;

    // getting address
    fifo = (canfd_fifo *)(RxFIFO0SA + (rx_fifo_idx * FDCAN_RX_FIFO_0_EL_SIZE));

    bool canfd_frame = ((fifo->header[1] >> 21) & 0x1U);
    bool brs_frame = ((fifo->header[1] >> 20) & 0x1U);

    to_push.fd = canfd_frame;
    to_push.returned = 0U;
    to_push.rejected = 0U;
    to_push.extended = (fifo->header[0] >> 30) & 0x1U;
    to_push.addr = ((to_push.extended != 0U) ? (fifo->header[0] & 0x1FFFFFFFU) : ((fifo->header[0] >> 18) & 0x7FFU));
    to_push.bus = bus_number;
    to_push.data_len_code = ((fifo->header[1] >> 16) & 0xFU);

    uint8_t data_len_w = (dlc_to_len[to_push.data_len_code] / 4U);
    data_len_w += ((dlc_to_len[to_push.data_len_code] % 4U) > 0U) ? 1U : 0U;
    for (unsigned int i = 0; i < data_len_w; i++) {
      WORD_TO_BYTE_ARRAY(&to_push.data[i*4U], fifo->data_word[i]);
    }
    can_set_checksum(&to_push);

    // forwarding (panda only)
    int bus_fwd_num = safety_fwd_hook(bus_number, to_push.addr);
    if (bus_fwd_num < 0) {
      bus_fwd_num = bus_config[can_number].forwarding_bus;
    }
    if (bus_fwd_num != -1) {
      CANPacket_t to_send;

      to_send.fd = to_push.fd;
      to_send.returned = 0U;
      to_send.rejected = 0U;
      to_send.extended = to_push.extended;
      to_send.addr = to_push.addr;
      to_send.bus = to_push.bus;
      to_send.data_len_code = to_push.data_len_code;
      (void)memcpy(to_send.data, to_push.data, dlc_to_len[to_push.data_len_code]);
      can_set_checksum(&to_send);

      can_send(&to_send, bus_fwd_num, true);
      can_health[can_number].total_fwd_cnt += 1U;
    }

    safety_rx_invalid += safety_rx_hook(&to_push) ? 0U : 1U;
    ignition_can_hook(&to_push);
    #ifdef PANDA_EV9_LONG_PREINIT
    ev9_long_preinit_rx_hook(&to_push, microsecond_timer_get());
    #endif

    led_set(LED_BLUE, true);
    rx_buffer_overflow += can_push(&can_rx_q, &to_push) ? 0U : 1U;

    // Enable CAN FD and BRS if CAN FD message was received
    if (!(bus_config[can_number].canfd_enabled) && (canfd_frame)) {
      bus_config[can_number].canfd_enabled = true;
    }
    if (!(bus_config[can_number].brs_enabled) && (brs_frame)) {
      bus_config[can_number].brs_enabled = true;
    }

    // update read index
    FDCANx->RXF0A = rx_fifo_idx;
  }

  // Error handling
  if ((ir_reg & (FDCAN_IR_PED | FDCAN_IR_PEA | FDCAN_IR_EP | FDCAN_IR_BO | FDCAN_IR_RF0L)) != 0U) {
    update_can_health_pkt(can_number, ir_reg);
  }
}

static void FDCAN1_IT0_IRQ_Handler(void) { can_rx(0); }
static void FDCAN1_IT1_IRQ_Handler(void) { process_can(0); }

static void FDCAN2_IT0_IRQ_Handler(void) { can_rx(1); }
static void FDCAN2_IT1_IRQ_Handler(void) { process_can(1); }

static void FDCAN3_IT0_IRQ_Handler(void) { can_rx(2);  }
static void FDCAN3_IT1_IRQ_Handler(void) { process_can(2); }

bool can_init(uint8_t can_number) {
  bool ret = false;

  REGISTER_INTERRUPT(FDCAN1_IT0_IRQn, FDCAN1_IT0_IRQ_Handler, CAN_INTERRUPT_RATE, FAULT_INTERRUPT_RATE_CAN_1)
  REGISTER_INTERRUPT(FDCAN1_IT1_IRQn, FDCAN1_IT1_IRQ_Handler, CAN_INTERRUPT_RATE, FAULT_INTERRUPT_RATE_CAN_1)
  REGISTER_INTERRUPT(FDCAN2_IT0_IRQn, FDCAN2_IT0_IRQ_Handler, CAN_INTERRUPT_RATE, FAULT_INTERRUPT_RATE_CAN_2)
  REGISTER_INTERRUPT(FDCAN2_IT1_IRQn, FDCAN2_IT1_IRQ_Handler, CAN_INTERRUPT_RATE, FAULT_INTERRUPT_RATE_CAN_2)
  REGISTER_INTERRUPT(FDCAN3_IT0_IRQn, FDCAN3_IT0_IRQ_Handler, CAN_INTERRUPT_RATE, FAULT_INTERRUPT_RATE_CAN_3)
  REGISTER_INTERRUPT(FDCAN3_IT1_IRQn, FDCAN3_IT1_IRQ_Handler, CAN_INTERRUPT_RATE, FAULT_INTERRUPT_RATE_CAN_3)

  if (can_number != 0xffU) {
    FDCAN_GlobalTypeDef *FDCANx = CANIF_FROM_CAN_NUM(can_number);
    ret &= can_set_speed(can_number);
    ret &= llcan_init(FDCANx);
    // in case there are queued up messages
    process_can(can_number);
  }
  return ret;
}
