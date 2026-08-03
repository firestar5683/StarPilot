#pragma once

#include "opendbc/safety/declarations.h"

#if defined(STM32H7) || defined(STM32F4)
void can_send(CANPacket_t *to_push, uint8_t bus_number, bool skip_tx_hook);
void can_set_checksum(CANPacket_t *packet);
#endif

#define PREAP_GET_BYTES_04(msg) ((msg)->data[0] | ((msg)->data[1] << 8) | ((msg)->data[2] << 16) | ((msg)->data[3] << 24))
#define PREAP_GET_BYTES_48(msg) ((msg)->data[4] | ((msg)->data[5] << 8) | ((msg)->data[6] << 16) | ((msg)->data[7] << 24))
#define PREAP_WORD_TO_BYTES(dst8, src32) 0[dst8] = ((src32) & 0xFFU); 1[dst8] = (((src32) >> 8U) & 0xFFU); 2[dst8] = (((src32) >> 16U) & 0xFFU); 3[dst8] = (((src32) >> 24U) & 0xFFU)

#define PREAP_FLAG_ENABLE_PEDAL 1U
#define PREAP_FLAG_RADAR_EMULATION 2U
#define PREAP_FLAG_RADAR_BEHIND_NOSECONE 4U
#define PREAP_CANCEL_ECHO_WINDOW_US 600000U

static bool preap_enable_pedal = false;
static bool preap_radar_emulation = false;
static bool preap_radar_behind_nosecone = false;

static int preap_gear = 4;
static int preap_gear_prev = 4;
static bool preap_doors_open = false;
static uint32_t preap_last_stalk_engage_us = 0;
static int preap_radar_epas_type = 0;
static int preap_radar_position = 0;

static const int preap_crc_lookup[256] = {
  0x00, 0x1D, 0x3A, 0x27, 0x74, 0x69, 0x4E, 0x53, 0xE8, 0xF5, 0xD2, 0xCF, 0x9C, 0x81, 0xA6, 0xBB,
  0xCD, 0xD0, 0xF7, 0xEA, 0xB9, 0xA4, 0x83, 0x9E, 0x25, 0x38, 0x1F, 0x02, 0x51, 0x4C, 0x6B, 0x76,
  0x87, 0x9A, 0xBD, 0xA0, 0xF3, 0xEE, 0xC9, 0xD4, 0x6F, 0x72, 0x55, 0x48, 0x1B, 0x06, 0x21, 0x3C,
  0x4A, 0x57, 0x70, 0x6D, 0x3E, 0x23, 0x04, 0x19, 0xA2, 0xBF, 0x98, 0x85, 0xD6, 0xCB, 0xEC, 0xF1,
  0x13, 0x0E, 0x29, 0x34, 0x67, 0x7A, 0x5D, 0x40, 0xFB, 0xE6, 0xC1, 0xDC, 0x8F, 0x92, 0xB5, 0xA8,
  0xDE, 0xC3, 0xE4, 0xF9, 0xAA, 0xB7, 0x90, 0x8D, 0x36, 0x2B, 0x0C, 0x11, 0x42, 0x5F, 0x78, 0x65,
  0x94, 0x89, 0xAE, 0xB3, 0xE0, 0xFD, 0xDA, 0xC7, 0x7C, 0x61, 0x46, 0x5B, 0x08, 0x15, 0x32, 0x2F,
  0x59, 0x44, 0x63, 0x7E, 0x2D, 0x30, 0x17, 0x0A, 0xB1, 0xAC, 0x8B, 0x96, 0xC5, 0xD8, 0xFF, 0xE2,
  0x26, 0x3B, 0x1C, 0x01, 0x52, 0x4F, 0x68, 0x75, 0xCE, 0xD3, 0xF4, 0xE9, 0xBA, 0xA7, 0x80, 0x9D,
  0xEB, 0xF6, 0xD1, 0xCC, 0x9F, 0x82, 0xA5, 0xB8, 0x03, 0x1E, 0x39, 0x24, 0x77, 0x6A, 0x4D, 0x50,
  0xA1, 0xBC, 0x9B, 0x86, 0xD5, 0xC8, 0xEF, 0xF2, 0x49, 0x54, 0x73, 0x6E, 0x3D, 0x20, 0x07, 0x1A,
  0x6C, 0x71, 0x56, 0x4B, 0x18, 0x05, 0x22, 0x3F, 0x84, 0x99, 0xBE, 0xA3, 0xF0, 0xED, 0xCA, 0xD7,
  0x35, 0x28, 0x0F, 0x12, 0x41, 0x5C, 0x7B, 0x66, 0xDD, 0xC0, 0xE7, 0xFA, 0xA9, 0xB4, 0x93, 0x8E,
  0xF8, 0xE5, 0xC2, 0xDF, 0x8C, 0x91, 0xB6, 0xAB, 0x10, 0x0D, 0x2A, 0x37, 0x64, 0x79, 0x5E, 0x43,
  0xB2, 0xAF, 0x88, 0x95, 0xC6, 0xDB, 0xFC, 0xE1, 0x5A, 0x47, 0x60, 0x7D, 0x2E, 0x33, 0x14, 0x09,
  0x7F, 0x62, 0x45, 0x58, 0x0B, 0x16, 0x31, 0x2C, 0x97, 0x8A, 0xAD, 0xB0, 0xE3, 0xFE, 0xD9, 0xC4
};

static int preap_compute_crc8(uint32_t lo, uint32_t hi, int msg_len) {
  int crc = 0xFF;
  for (int x = 0; x < msg_len; x++) {
    const int value = (x <= 3) ? ((lo >> (x * 8)) & 0xFF) : ((hi >> ((x - 4) * 8)) & 0xFF);
    crc = preap_crc_lookup[crc ^ value];
  }
  return crc ^ 0xFF;
}

static void preap_radar_readdr(const CANPacket_t *src, uint16_t new_addr) {
#if defined(STM32H7) || defined(STM32F4)
  CANPacket_t pkt;
  pkt.returned = 0U;
  pkt.rejected = 0U;
  pkt.extended = src->extended;
  pkt.bus = 1;
  pkt.addr = new_addr;
  pkt.data_len_code = src->data_len_code;
  for (int i = 0; i < GET_LEN(src); i++) {
    pkt.data[i] = src->data[i];
  }
  can_set_checksum(&pkt);
  can_send(&pkt, 1, true);
#else
  (void)src;
  (void)new_addr;
#endif
}

static uint8_t preap_byte_sum_checksum(const CANPacket_t *pkt) {
  uint8_t checksum = (uint8_t)(pkt->addr & 0xFFU) + (uint8_t)((pkt->addr >> 8) & 0xFFU);
  const int len = GET_LEN(pkt);
  for (int i = 0; i < (len - 1); i++) {
    checksum += pkt->data[i];
  }
  return checksum;
}

static void tesla_preap_gtw_emulation(const CANPacket_t *to_fwd) {
  const int bus_num = to_fwd->bus;
  const int addr = to_fwd->addr;

  if (bus_num == 0 && preap_radar_emulation) {
    switch (addr) {
      case 0x45:  preap_radar_readdr(to_fwd, 0x219); break;
      case 0x108: preap_radar_readdr(to_fwd, 0x109); break;
      case 0x145: preap_radar_readdr(to_fwd, 0x149); break;
      case 0x20A: preap_radar_readdr(to_fwd, 0x159); break;
      case 0x308: preap_radar_readdr(to_fwd, 0x209); break;
      case 0x30A: preap_radar_readdr(to_fwd, 0x2D9); break;
      case 0x405: preap_radar_readdr(to_fwd, 0x2B9); break;
      default: break;
    }

    if (addr == 0x398) {
      CANPacket_t pkt = {.returned = 0U, .rejected = 0U, .extended = to_fwd->extended,
                         .bus = 1, .addr = 0x2A9, .data_len_code = to_fwd->data_len_code};
      uint32_t lo = PREAP_GET_BYTES_04(to_fwd);
      uint32_t hi = PREAP_GET_BYTES_48(to_fwd);
      lo = (lo & 0xFFFFF33FU) | 0x100U | 0x440U;
      hi = (hi & 0xCFFF0F0FU) | 0x10000000U | ((uint32_t)preap_radar_position << 4) | ((uint32_t)preap_radar_epas_type << 12);
      PREAP_WORD_TO_BYTES(&pkt.data[0], lo);
      PREAP_WORD_TO_BYTES(&pkt.data[4], hi);
      pkt.data[7] = preap_byte_sum_checksum(&pkt);
#if defined(STM32H7) || defined(STM32F4)
      can_set_checksum(&pkt);
      can_send(&pkt, 1, true);
#endif
    }

    if (addr == 0x0EU) {
      CANPacket_t pkt = {.returned = 0U, .rejected = 0U, .extended = to_fwd->extended,
                         .bus = 1, .addr = 0x199, .data_len_code = to_fwd->data_len_code};
      uint32_t lo = PREAP_GET_BYTES_04(to_fwd);
      uint32_t hi = PREAP_GET_BYTES_48(to_fwd);
      if (((lo >> 16) & 0xFF3FU) == 0xFF3FU) {
        lo = (lo & 0x00C0FFFFU) | (0x0020U << 16);
        hi = (hi & 0x00FFFFF0U) | 0x00000004U;
        const int crc = preap_compute_crc8(lo, hi, 7);
        hi |= ((uint32_t)crc << 24);
      }
      PREAP_WORD_TO_BYTES(&pkt.data[0], lo);
      PREAP_WORD_TO_BYTES(&pkt.data[4], hi);
#if defined(STM32H7) || defined(STM32F4)
      can_set_checksum(&pkt);
      can_send(&pkt, 1, true);
#endif
    }

    if (addr == 0x115U) {
      preap_radar_readdr(to_fwd, 0x129);
      const uint32_t hi_src = PREAP_GET_BYTES_48(to_fwd);
      const int counter = ((hi_src & 0xF0U) >> 4) & 0x0F;
      const uint32_t syn_lo = 0x000C0000U | ((uint32_t)counter << 28);
      const int checksum = (0x38 + 0x0C + (counter << 4)) & 0xFF;
      CANPacket_t pkt = {.returned = 0U, .rejected = 0U, .extended = 0,
                         .bus = 1, .addr = 0x1A9, .data_len_code = 5};
      PREAP_WORD_TO_BYTES(&pkt.data[0], syn_lo);
      PREAP_WORD_TO_BYTES(&pkt.data[4], (uint32_t)checksum);
#if defined(STM32H7) || defined(STM32F4)
      can_set_checksum(&pkt);
      can_send(&pkt, 1, true);
#endif
    }

    if (addr == 0x118U) {
      preap_radar_readdr(to_fwd, 0x119);
      const uint32_t lo = PREAP_GET_BYTES_04(to_fwd);
      const int ws_counter = PREAP_GET_BYTES_48(to_fwd) & 0x0F;
      const int raw_speed = (int)((0xFFF0000U & lo) >> 16);
      uint32_t speed;
      if (raw_speed == 0xFFF) {
        speed = 0x1FFF;
      } else {
        const int mph_x100 = raw_speed * 5 - 2500;
        const int kph_x100 = mph_x100 * 1609 / 1000;
        const int speed_scaled = (kph_x100 / 4) & 0x1FFF;
        speed = (kph_x100 < 0) ? 0U : (uint32_t)speed_scaled;
      }
      const uint32_t ws_lo = speed | (speed << 13U) | (speed << 26U);
      uint32_t ws_hi = ((speed >> 6U) | (speed << 7U) | ((uint32_t)ws_counter << 20U)) & 0x00FFFFFFU;
      int ws_checksum = 0x76;
      ws_checksum = (ws_checksum + (int)(ws_lo & 0xFF) + (int)((ws_lo >> 8) & 0xFF) + (int)((ws_lo >> 16) & 0xFF) + (int)((ws_lo >> 24) & 0xFF)) & 0xFF;
      ws_checksum = (ws_checksum + (int)(ws_hi & 0xFF) + (int)((ws_hi >> 8) & 0xFF) + (int)((ws_hi >> 16) & 0xFF)) & 0xFF;
      ws_hi |= ((uint32_t)ws_checksum << 24);
      CANPacket_t pkt = {.returned = 0U, .rejected = 0U, .extended = 0,
                         .bus = 1, .addr = 0x169, .data_len_code = 8};
      PREAP_WORD_TO_BYTES(&pkt.data[0], ws_lo);
      PREAP_WORD_TO_BYTES(&pkt.data[4], ws_hi);
#if defined(STM32H7) || defined(STM32F4)
      can_set_checksum(&pkt);
      can_send(&pkt, 1, true);
#endif
    }
  }
}

static void tesla_preap_rx_hook(const CANPacket_t *msg) {
  if (preap_enable_pedal && (msg->addr == 0x552U)) {
    const int pedal_val = (msg->data[0] << 8) | msg->data[1];
    gas_pressed = pedal_val > 650;
    return;
  }

  if (msg->bus != 0U) {
    return;
  }

  if (msg->addr == 0x370U) {
    const int angle_meas_new = (((msg->data[4] & 0x3FU) << 8) | msg->data[5]) - 8192U;
    update_sample(&angle_meas, angle_meas_new);

    const int hands_on_level = msg->data[4] >> 6;
    const int eac_status = msg->data[6] >> 5;
    const int eac_error_code = msg->data[2] >> 4;
    const bool epas_rejecting = (eac_status == 0) && (eac_error_code >= 6) && (eac_error_code <= 9);
    steering_disengage = (hands_on_level >= 3) || epas_rejecting;

    if (steering_disengage && !steering_disengage_prev) {
      pcm_cruise_check(false);
    }
  }

  if (msg->addr == 0x155U) {
    const float speed = (((msg->data[5] << 8) | msg->data[6]) * 0.01f) * KPH_TO_MS;
    UPDATE_VEHICLE_SPEED(speed);
    vehicle_moving = speed > (0.5f * KPH_TO_MS);
  }

  if ((msg->addr == 0x108U) && !preap_enable_pedal) {
    gas_pressed = msg->data[6] != 0U;
  }

  if (msg->addr == 0x20AU) {
    brake_pressed = false;
  }

  if (msg->addr == 0x368U) {
    const int cruise_state = (msg->data[1] >> 4) & 0x07U;
    if (cruise_state == 3) {
      vehicle_moving = false;
    }
  }

  if (msg->addr == 0x118U) {
    preap_gear = (msg->data[1] >> 4) & 0x07;
    if ((preap_gear_prev == 4) && (preap_gear != 4)) {
      controls_allowed = false;
    }
    preap_gear_prev = preap_gear;
  }

  if (msg->addr == 0x318U) {
    const int d_fl = (msg->data[1] >> 4) & 0x03;
    const int d_fr = (msg->data[1] >> 6) & 0x03;
    const int d_rl = (msg->data[2] >> 6) & 0x03;
    const int d_rr = (msg->data[3] >> 5) & 0x03;
    const int d_ft = (msg->data[6] >> 2) & 0x03;
    const int d_tr = (msg->data[5] >> 6) & 0x03;
    preap_doors_open = (d_fl == 1) || (d_fr == 1) || (d_rl == 1) || (d_rr == 1) || (d_ft == 1) || (d_tr == 1);
    if (preap_doors_open) {
      controls_allowed = false;
    }
  }

  if (msg->addr == 0x45U) {
    const int lever = msg->data[0] & 0x3FU;
    if (lever == 2) {
      if ((preap_gear == 4) && !preap_doors_open) {
        pcm_cruise_check(true);
        preap_last_stalk_engage_us = microsecond_timer_get();
      }
    } else if (lever == 1) {
      const uint32_t elapsed = microsecond_timer_get() - preap_last_stalk_engage_us;
      if (elapsed > PREAP_CANCEL_ECHO_WINDOW_US) {
        pcm_cruise_check(false);
      }
    }
  }
}

static bool tesla_preap_tx_hook(const CANPacket_t *msg) {
  const AngleSteeringLimits PREAP_STEERING_LIMITS = {
    .max_angle = 3600,
    .angle_deg_to_can = 10,
    .frequency = 50U,
  };

  const AngleSteeringParams PREAP_STEERING_PARAMS = {
    .slip_factor = -0.0005666f,
    .steer_ratio = 15.f,
    .wheelbase = 2.96f,
  };

  bool violation = false;

  if (msg->addr == 0x488U) {
    const int raw_angle_can = ((msg->data[0] & 0x7FU) << 8) | msg->data[1];
    const int desired_angle = raw_angle_can - 16384;
    const int steer_control_type = msg->data[2] >> 6;
    const bool steer_control_enabled = steer_control_type == 1;

    if (steer_angle_cmd_checks_vm(desired_angle, steer_control_enabled, PREAP_STEERING_LIMITS, PREAP_STEERING_PARAMS)) {
      violation = true;
    }
    if ((steer_control_type != 0) && (steer_control_type != 1)) {
      violation = true;
    }
  }

  if (msg->addr == 0x214U) {
    const int epas_control_type = msg->data[0] & 0x07U;
    if (epas_control_type > 1) {
      violation = true;
    }
  }

  if (msg->addr == 0x2B9U) {
    const int aeb_event = msg->data[2] & 0x03U;
    if (aeb_event != 0) {
      violation = true;
    }
  }

  if (msg->addr == 0x551U) {
    if (!preap_enable_pedal) {
      violation = true;
    } else {
      const bool pedal_enable = (msg->data[4] & 0x80U) != 0U;
      const int raw_gas_cmd = (msg->data[0] << 8) | msg->data[1];
      if (pedal_enable) {
        if (!get_longitudinal_allowed()) {
          violation = true;
        }
      } else if (raw_gas_cmd > 500) {
        violation = true;
      }
    }
  }

  return !violation;
}

static bool tesla_preap_fwd_hook(int bus_num, int addr) {
  (void)bus_num;
  (void)addr;
  return false;
}

static safety_config tesla_preap_init(uint16_t param) {
  preap_enable_pedal = GET_FLAG(param, PREAP_FLAG_ENABLE_PEDAL);
  preap_radar_emulation = GET_FLAG(param, PREAP_FLAG_RADAR_EMULATION);
  preap_radar_behind_nosecone = GET_FLAG(param, PREAP_FLAG_RADAR_BEHIND_NOSECONE);

  preap_gear = 4;
  preap_gear_prev = 4;
  preap_doors_open = false;
  preap_last_stalk_engage_us = 0;
  preap_radar_epas_type = 0;
  preap_radar_position = preap_radar_behind_nosecone ? 1 : 0;

  static const CanMsg PREAP_TX_MSGS[] = {
    {0x488, 0, 4, .check_relay = false, .disable_static_blocking = true},
    {0x2B9, 0, 8, .check_relay = false, .disable_static_blocking = true},
    {0x214, 0, 3, .check_relay = false, .disable_static_blocking = true},
    {0x551, 0, 6, .check_relay = false, .disable_static_blocking = true},
    {0x551, 2, 6, .check_relay = false, .disable_static_blocking = true},
    {0x45, 0, 8, .check_relay = false, .disable_static_blocking = true},
  };

  static RxCheck preap_rx_checks[] = {
    {.msg = {{0x370, 0, 8, 25U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x108, 0, 8, 100U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x118, 0, 6, 100U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x20A, 0, 8, 50U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x368, 0, 8, 10U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x318, 0, 8, 10U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x45, 0, 8, 10U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x155, 0, 8, 50U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
  };

  static RxCheck preap_rx_checks_with_pedal[] = {
    {.msg = {{0x370, 0, 8, 25U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x108, 0, 8, 100U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x118, 0, 6, 100U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x20A, 0, 8, 50U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x368, 0, 8, 10U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x318, 0, 8, 10U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x45, 0, 8, 10U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x155, 0, 8, 50U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}, {0}}},
    {.msg = {{0x552, 0, 6, 50U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true},
             {0x552, 2, 6, 50U, .ignore_quality_flag = true, .ignore_checksum = true, .ignore_counter = true}, {0}}},
  };

  return preap_enable_pedal ? BUILD_SAFETY_CFG(preap_rx_checks_with_pedal, PREAP_TX_MSGS)
                            : BUILD_SAFETY_CFG(preap_rx_checks, PREAP_TX_MSGS);
}

const safety_hooks tesla_preap_hooks = {
  .init = tesla_preap_init,
  .rx = tesla_preap_rx_hook,
  .rx_all = tesla_preap_gtw_emulation,
  .tx = tesla_preap_tx_hook,
  .fwd = tesla_preap_fwd_hook,
  .get_checksum = NULL,
  .compute_checksum = NULL,
  .get_counter = NULL,
  .get_quality_flag_valid = NULL,
};
