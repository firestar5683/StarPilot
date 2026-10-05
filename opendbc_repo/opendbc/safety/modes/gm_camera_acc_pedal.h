#pragma once

static uint8_t gm_pedal_crc(const CANPacket_t *msg) {
  uint8_t crc = 0xFFU;
  for (int i = 4; i >= 0; i--) {
    crc ^= msg->data[i];
    for (uint8_t bit = 0U; bit < 8U; bit++) {
      crc = (crc & 0x80U) ? (uint8_t)((crc << 1) ^ 0xD5U) : (uint8_t)(crc << 1);
    }
  }
  return crc;
}

// Exact optional camera-ACC interceptor owners. Raw words remain on the wire.
static bool gm_camera_pedal = false;
static bool gm_camera_pedal_long = false;
static bool gm_camera_volt = false;
static bool gm_camera_gateway = false;
static bool gm_camera_gateway_removed = false;
static bool gm_camera_regen = false;
static bool gm_camera_pedal_f1 = false;
static bool gm_camera_pedal_rejected = false;
static bool gm_camera_seen[9] = {false};
static uint32_t gm_camera_us[9] = {0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U};
static bool gm_camera_main = false;
static bool gm_camera_driver_brake = false;
static bool gm_camera_driver_gas = false;
static bool gm_camera_forward = false;
static bool gm_camera_near_zero = false;
static uint8_t gm_camera_acc = 0U;
static bool gm_camera_pair_good = false;
static bool gm_camera_sensor_counter_seen = false;
static uint8_t gm_camera_sensor_counter = 0U;
static bool gm_camera_tx_counter_seen = false;
static uint8_t gm_camera_tx_counter = 0U;
static bool gm_camera_neutral_seen[2] = {false};
static bool gm_camera_launch = false;

static void gm_camera_credit_clear(void) {
  gm_camera_neutral_seen[0] = false;
  gm_camera_neutral_seen[1] = false;
}

static uint16_t gm_camera_pedal_reset(uint16_t raw) {
  gm_camera_pedal = false;
  gm_camera_pedal_long = false;
  gm_camera_volt = false;
  gm_camera_gateway = false;
  gm_camera_gateway_removed = false;
  gm_camera_regen = false;
  gm_camera_pedal_f1 = false;
  gm_camera_pedal_rejected = false;
  gm_camera_main = false;
  gm_camera_driver_brake = false;
  gm_camera_driver_gas = false;
  gm_camera_forward = false;
  gm_camera_near_zero = false;
  gm_camera_acc = 0U;
  gm_camera_pair_good = false;
  gm_camera_sensor_counter_seen = false;
  gm_camera_sensor_counter = 0U;
  gm_camera_tx_counter_seen = false;
  gm_camera_tx_counter = 0U;
  gm_camera_launch = false;
  gm_camera_credit_clear();
  for (uint8_t i = 0U; i < 9U; i++) { gm_camera_seen[i] = false; gm_camera_us[i] = 0U; }
  uint16_t canonical = raw;
  switch (raw) {
    case 0xE110U: gm_camera_pedal = true; canonical = 0xC171U; break;
    case 0xE111U: gm_camera_pedal = true; gm_camera_pedal_f1 = true; canonical = 0xC171U; break;
    case 0xE112U: gm_camera_pedal = true; canonical = 0xC172U; break;
    case 0xE113U: gm_camera_pedal = true; gm_camera_pedal_f1 = true; canonical = 0xC172U; break;
    case 0xE210U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_f1 = false; canonical = 0x0005U; break;
    case 0xE211U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_f1 = true; canonical = 0x0005U; break;
    case 0xE212U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_f1 = false; canonical = 0xC150U; break;
    case 0xE213U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_f1 = true; canonical = 0xC150U; break;
    case 0xE310U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = false; gm_camera_pedal_f1 = false; gm_camera_pedal_long = false; canonical = 0x4004U; break;
    case 0xE311U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = false; gm_camera_pedal_f1 = true; gm_camera_pedal_long = false; canonical = 0xC004U; break;
    case 0xE312U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = true; gm_camera_pedal_f1 = false; gm_camera_pedal_long = false; canonical = 0x4004U; break;
    case 0xE313U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = true; gm_camera_pedal_f1 = true; gm_camera_pedal_long = false; canonical = 0xC004U; break;
#ifdef ALLOW_DEBUG
    case 0xE300U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = false; gm_camera_pedal_f1 = false; gm_camera_pedal_long = true; canonical = 0x4004U; break;
    case 0xE301U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = false; gm_camera_pedal_f1 = true; gm_camera_pedal_long = true; canonical = 0xC004U; break;
    case 0xE302U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = true; gm_camera_pedal_f1 = false; gm_camera_pedal_long = true; canonical = 0x4004U; break;
    case 0xE303U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = true; gm_camera_pedal_f1 = true; gm_camera_pedal_long = true; canonical = 0xC004U; break;
    case 0xE320U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = false; gm_camera_pedal_f1 = false; gm_camera_pedal_long = true; canonical = 0x4084U; break;
    case 0xE321U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = false; gm_camera_pedal_f1 = true; gm_camera_pedal_long = true; canonical = 0xC084U; break;
    case 0xE322U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = true; gm_camera_pedal_f1 = false; gm_camera_pedal_long = true; canonical = 0x4084U; break;
    case 0xE323U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = true; gm_camera_pedal_f1 = true; gm_camera_pedal_long = true; canonical = 0xC084U; break;
    case 0xE340U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = false; gm_camera_pedal_f1 = false; gm_camera_pedal_long = true; canonical = 0xD100U; break;
    case 0xE341U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = false; gm_camera_pedal_f1 = true; gm_camera_pedal_long = true; canonical = 0xD101U; break;
    case 0xE342U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = true; gm_camera_pedal_f1 = false; gm_camera_pedal_long = true; canonical = 0xD100U; break;
    case 0xE343U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = true; gm_camera_pedal_f1 = true; gm_camera_pedal_long = true; canonical = 0xD101U; break;
    case 0xE360U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = false; gm_camera_pedal_f1 = false; gm_camera_pedal_long = true; canonical = 0xD110U; break;
    case 0xE361U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = false; gm_camera_pedal_f1 = true; gm_camera_pedal_long = true; canonical = 0xD111U; break;
    case 0xE362U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = true; gm_camera_pedal_f1 = false; gm_camera_pedal_long = true; canonical = 0xD110U; break;
    case 0xE363U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_gateway = true; gm_camera_gateway_removed = true; gm_camera_pedal_f1 = true; gm_camera_pedal_long = true; canonical = 0xD111U; break;
    case 0xE100U: gm_camera_pedal = true; gm_camera_pedal_long = true; canonical = 0xC170U; break;
    case 0xE101U: gm_camera_pedal = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = true; canonical = 0xC170U; break;
    case 0xE102U: gm_camera_pedal = true; gm_camera_pedal_long = true; canonical = 0xC173U; break;
    case 0xE103U: gm_camera_pedal = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = true; canonical = 0xC173U; break;
    case 0xE200U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = false; canonical = 0x4007U; break;
    case 0xE201U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = true; canonical = 0x4007U; break;
    case 0xE202U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = false; canonical = 0xC151U; break;
    case 0xE203U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = true; canonical = 0xC151U; break;
    case 0xE220U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = false; canonical = 0x4087U; break;
    case 0xE221U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = true; canonical = 0x4087U; break;
    case 0xE222U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = false; canonical = 0xC1D1U; break;
    case 0xE223U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = true; canonical = 0xC1D3U; break;
    case 0xE240U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = false; canonical = 0xD106U; break;
    case 0xE241U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = true; canonical = 0xD106U; break;
    case 0xE242U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = false; canonical = 0xD109U; break;
    case 0xE243U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = true; canonical = 0xD10AU; break;
    case 0xE260U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = false; canonical = 0xD116U; break;
    case 0xE261U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = true; canonical = 0xD116U; break;
    case 0xE262U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = false; canonical = 0xD119U; break;
    case 0xE263U: gm_camera_pedal = true; gm_camera_volt = true; gm_camera_pedal_long = true; gm_camera_pedal_f1 = true; canonical = 0xD11AU; break;
#else
    case 0xE100U: case 0xE101U: case 0xE102U: case 0xE103U: gm_camera_pedal_rejected = true; break;
#endif
    default:
      if (((raw & 0xFF00U) == 0xE200U) || ((raw & 0xFF00U) == 0xE300U)) { gm_camera_pedal_rejected = true; }
      break;
  }
  return canonical;
}

static bool gm_camera_sources_current(void) {
  const uint32_t limits[9] = {300000U, 100000U, 100000U, 300000U, 300000U, 300000U, 100000U, 100000U, 100000U};
  bool current = true;
  const uint32_t now = microsecond_timer_get();
  for (uint8_t i = 0U; i < (gm_camera_volt ? 9U : 8U); i++) {
    const uint32_t age_limit = (gm_camera_gateway && (i == 7U)) ? 1000000U : limits[i];
    if (gm_camera_seen[i] && (safety_get_ts_elapsed(now, gm_camera_us[i]) > age_limit)) { gm_camera_seen[i] = false; }
    current &= gm_camera_seen[i];
  }
  return current;
}

static bool gm_camera_hold_sensor_ready(void) {
  bool ready = true;
  if (gm_camera_volt && gm_camera_pedal_long) {
    ready = gm_camera_sources_current() && gm_camera_pair_good && !gm_camera_driver_gas && !gm_camera_regen;
    if (!ready) { gm_hold_armed = false; gm_hold_accepted = false; }
  }
  return ready;
}

static bool gm_camera_ready(void) {
  const bool ready = gm_camera_sources_current() && gm_camera_pair_good && gm_camera_main &&
                     (gm_camera_acc != 3U) && gm_camera_forward && !gm_camera_driver_brake && !gm_camera_driver_gas && !gm_camera_regen && controls_allowed &&
                     !gas_pressed && !safety_rx_checks_invalid && !relay_malfunction;
  if (!ready) { gm_camera_credit_clear(); gm_camera_launch = false; }
  return ready;
}

static void gm_camera_pedal_rx(const CANPacket_t *msg) {
  if (gm_camera_pedal_long && (msg->bus == 0U)) {
    int source = -1;
    if ((msg->addr == 0x184U) && (GET_LEN(msg) == 8U)) { source = 0; }
    if ((msg->addr == 0x34AU) && (GET_LEN(msg) == 5U)) {
      source = 1;
      gm_camera_near_zero = ((((uint32_t)msg->data[0] << 8) | msg->data[1]) <= (gm_camera_volt ? 231U : 34U)) &&
                            ((((uint32_t)msg->data[2] << 8) | msg->data[3]) <= (gm_camera_volt ? 231U : 34U));
    }
    if ((msg->addr == 0x1E1U) && (GET_LEN(msg) == 7U)) { source = 2; }
    if ((msg->addr == (gm_camera_pedal_f1 ? 0xF1U : 0xBEU)) && (GET_LEN(msg) == 6U)) {
      source = 3;
      if (gm_camera_gateway && gm_camera_pedal_f1) { gm_camera_driver_brake = msg->data[1] >= 6U; }
    }
    if ((msg->addr == 0x1C4U) && (GET_LEN(msg) == 8U)) {
      source = 4;
      gm_camera_acc = (msg->data[1] >> 5) & 7U;
    }
    if ((msg->addr == 0xC9U) && (GET_LEN(msg) == 8U)) {
      source = 5;
      gm_camera_main = GET_BIT(msg, 29U);
      if (!gm_camera_gateway || !gm_camera_pedal_f1) { gm_camera_driver_brake = GET_BIT(msg, 40U); }
    }
    if (gm_camera_volt && (msg->addr == 0xBDU) && (GET_LEN(msg) == 7U)) {
      source = 8; gm_camera_regen = (msg->data[0] >> 4U) != 0U;
    }
    if ((msg->addr == 0x201U) && (GET_LEN(msg) == 6U)) {
      source = 6;
      const int track1 = (msg->data[0] << 8) | msg->data[1];
      const int track2 = (msg->data[2] << 8) | msg->data[3];
      const uint8_t counter = msg->data[4] & 0xFU;
      // Physical producer samples are independent 12-bit ADC channels.
      gm_camera_pair_good = ((msg->data[4] >> 4) == 0U) && (gm_pedal_crc(msg) == msg->data[5]) &&
        (!gm_camera_sensor_counter_seen || (counter != gm_camera_sensor_counter)) &&
        (track1 <= 4095) && (track2 <= 4095);
      gm_camera_driver_gas = (track1 + track2) > 1190;
      gm_camera_sensor_counter_seen = true;
      gm_camera_sensor_counter = counter;
    }
    if ((msg->addr == 0x1F5U) && (GET_LEN(msg) == 8U)) {
      source = 7;
      const uint8_t gear = msg->data[3] & 0xFU;
      gm_camera_forward = (gear == 4U) || (gear == 6U) || (GET_BIT(msg, 41U) && (gear >= 4U) && (gear <= 7U));
    }
    if (source >= 0) { gm_camera_seen[source] = true; gm_camera_us[source] = microsecond_timer_get(); }
    if (!gm_camera_main || gm_camera_driver_brake || gm_camera_driver_gas || !gm_camera_forward || !gm_camera_pair_good || gm_camera_regen) {
      gm_camera_credit_clear(); gm_camera_launch = false;
    }
  }
}

static bool gm_camera_gas_shape(const CANPacket_t *msg) {
  const uint8_t counter = (msg->data[0] >> 6) & 3U;
  const bool active = GET_BIT(msg, 0U);
  return (GET_LEN(msg) == 8U) && (((msg->data[1] >> 6) & 3U) == 1U) &&
    ((msg->data[0] & 0x3FU) == (active ? 1U : 0U)) && ((msg->data[1] & 0x18U) == 0U) &&
    (msg->data[4] == (active ? 0U : 1U)) && (msg->data[5] == (uint8_t)(0xFFU - msg->data[1])) &&
    (msg->data[6] == (uint8_t)(0xFFU - msg->data[2])) &&
    (msg->data[7] == (uint8_t)(0x100U - msg->data[3] - counter));
}

static bool gm_camera_brake_shape(const CANPacket_t *msg) {
  const uint8_t mode = msg->data[0] >> 4;
  const uint16_t encoded = ((uint16_t)(msg->data[0] & 0xFU) << 8) | msg->data[1];
  const uint8_t counter = msg->data[4] & 3U;
  const uint16_t checksum = ((uint16_t)msg->data[2] << 8) | msg->data[3];
  return (GET_LEN(msg) == 5U) && ((mode == 1U) || (mode == 0xAU) || (mode == 0xBU) || (mode == 0xDU)) &&
    ((encoded != 0U) || (mode == 1U)) && (msg->data[4] == counter) && (checksum == (uint16_t)((0x10000U - ((uint32_t)mode << 12U) - encoded - counter) & 0xFFFFU));
}

static bool gm_camera_pedal_tx(const CANPacket_t *msg, bool ordinary_tx) {
  bool tx = ordinary_tx;
  if (gm_camera_pedal_long) {
    static uint8_t gm_camera_neutral_counter[2] = {0U, 0U};
    static uint32_t gm_camera_neutral_us[2] = {0U, 0U};
    const bool ready = gm_camera_ready();
    const uint32_t now = microsecond_timer_get();
    for (uint8_t i = 0U; i < 2U; i++) {
      if (gm_camera_neutral_seen[i] && (safety_get_ts_elapsed(now, gm_camera_neutral_us[i]) > 80000U)) { gm_camera_neutral_seen[i] = false; }
    }
    if ((msg->addr == 0x2CBU) || (msg->addr == 0x315U)) {
      const bool gas = msg->addr == 0x2CBU;
      const uint8_t index = gas ? 0U : 1U;
      const uint8_t counter = gas ? ((msg->data[0] >> 6) & 3U) : (msg->data[4] & 3U);
      const uint32_t gas_encoded = (((uint32_t)msg->data[1] & 7U) << 16) | ((uint32_t)msg->data[2] << 8) | msg->data[3];
      const uint32_t brake_encoded = (0x1000U - ((((uint32_t)msg->data[0] & 0xFU) << 8) | msg->data[1])) & 0xFFFU;
      const bool neutral = gas ? (gas_encoded == (gm_camera_gateway ? 175072U : 176272U)) : (brake_encoded == 0U);
      const bool shape = gas ? gm_camera_gas_shape(msg) : gm_camera_brake_shape(msg);
      const bool inactive_hold = !gas && gm_camera_volt && gm_auto_hold && !get_longitudinal_allowed() &&
                                 gm_camera_sources_current() && gm_camera_pair_good && !gm_camera_driver_gas && !gm_camera_regen;
      tx &= shape && (neutral || (ready && !gm_camera_launch) || inactive_hold);
      if (!neutral) { gm_camera_credit_clear(); }
      if (tx && neutral && ready) {
        gm_camera_neutral_seen[index] = true;
        gm_camera_neutral_counter[index] = counter;
        gm_camera_neutral_us[index] = now;
      }
    }
    if (msg->addr == 0x200U) {
      const int track1 = (msg->data[0] << 8) | msg->data[1];
      const int track2 = (msg->data[2] << 8) | msg->data[3];
      const bool enabled = GET_BIT(msg, 39U);
      const uint8_t counter = msg->data[4] & 0xFU;
      const int delta = track1 - (2 * track2);
      const bool neutral = !enabled && (track1 == 0) && (track2 == 0);
      // Original fixed launch18/255 maps to these two independently scaled tracks.
      const bool launch = enabled && ready && gm_camera_near_zero && (gm_camera_acc == 4U) &&
        (track1 >= 604) && (track1 <= (gm_camera_volt ? 929 : 747)) && (track2 >= 304) && (track2 <= (gm_camera_volt ? 466 : 375)) && (delta >= -16) && (delta <= 16) &&
        gm_camera_neutral_seen[0] && gm_camera_neutral_seen[1] &&
        (gm_camera_neutral_counter[0] == counter) && (gm_camera_neutral_counter[1] == counter);
      tx &= (GET_LEN(msg) == 6U) && (msg->data[4] == (uint8_t)(counter | (enabled ? 0x80U : 0U))) &&
        (counter <= 3U) && (gm_pedal_crc(msg) == msg->data[5]) &&
        (!gm_camera_tx_counter_seen || (counter == ((gm_camera_tx_counter + 1U) & 3U))) && (neutral || launch);
      if (tx) {
        gm_camera_tx_counter_seen = true; gm_camera_tx_counter = counter;
        gm_camera_launch = !neutral;
        gm_camera_credit_clear();
      }
    }
  }
  return tx;
}
