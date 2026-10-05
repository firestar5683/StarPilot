#pragma once

static uint8_t gm_pedal_crc(const CANPacket_t *msg);

static bool gm_cc_pedal = false;
// Silverado owns four complete selectors; it shares only the checked pedal codec.
static bool gm_cc_pedal_silverado = false;
static bool gm_cc_pedal_stock_only = false;
static bool gm_cc_pedal_ordinary_stock = false;
static uint8_t gm_cc_pedal_silverado_seen = 0U;
static uint32_t gm_cc_pedal_silverado_us[8] = {0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U};
static bool gm_cc_pedal_main = false;
static bool gm_cc_pedal_stock_active = false;
static bool gm_cc_pedal_forward = false;
static bool gm_cc_pedal_sensor_valid = false;
static bool gm_cc_pedal_sensor_gas = false;
static bool gm_cc_pedal_sensor_seen = false;
static uint8_t gm_cc_pedal_sensor_counter = 0U;
static uint32_t gm_cc_pedal_sensor_us = 0U;
static uint32_t gm_cc_pedal_main_us = 0U;
static uint32_t gm_cc_pedal_stock_us = 0U;
static uint32_t gm_cc_pedal_gear_us = 0U;
static bool gm_cc_pedal_button_seen = false;
static bool gm_cc_pedal_cancel_credit = false;
static uint8_t gm_cc_pedal_button_counter = 0U;
static uint32_t gm_cc_pedal_button_us = 0U;
static bool gm_cc_pedal_cancel_seen = false;
static uint32_t gm_cc_pedal_cancel_us = 0U;
static bool gm_cc_pedal_tx_seen = false;
static uint8_t gm_cc_pedal_tx_counter = 0U;

static void gm_cc_pedal_reset(void) {
  gm_cc_pedal_silverado_seen = 0U;
  for (uint8_t i = 0U; i < 8U; i++) { gm_cc_pedal_silverado_us[i] = 0U; }
  gm_cc_pedal_main = false;
  gm_cc_pedal_stock_active = false;
  gm_cc_pedal_forward = false;
  gm_cc_pedal_sensor_valid = false;
  gm_cc_pedal_sensor_gas = false;
  gm_cc_pedal_sensor_seen = false;
  gm_cc_pedal_sensor_counter = 0U;
  gm_cc_pedal_sensor_us = 0U;
  gm_cc_pedal_main_us = 0U;
  gm_cc_pedal_stock_us = 0U;
  gm_cc_pedal_gear_us = 0U;
  gm_cc_pedal_button_seen = false;
  gm_cc_pedal_cancel_credit = false;
  gm_cc_pedal_button_counter = 0U;
  gm_cc_pedal_button_us = 0U;
  gm_cc_pedal_cancel_seen = false;
  gm_cc_pedal_cancel_us = 0U;
  gm_cc_pedal_tx_seen = false;
  gm_cc_pedal_tx_counter = 0U;
}

static bool gm_cc_pedal_silverado_current(void) {
  bool current = gm_cc_pedal_silverado_seen == 0xFFU;
  const uint32_t now = microsecond_timer_get();
  const uint32_t limits[8] = {300000U, 300000U, 300000U, 300000U, 100000U, 100000U, 300000U, 100000U};
  for (uint8_t i = 0U; i < 8U; i++) {
    current &= safety_get_ts_elapsed(now, gm_cc_pedal_silverado_us[i]) <= limits[i];
  }
  return current && gm_cc_pedal_sensor_valid && !safety_rx_checks_invalid && !relay_malfunction;
}

static bool gm_cc_pedal_current(void) {
  const uint32_t now = microsecond_timer_get();
  return gm_cc_pedal_sensor_valid && gm_cc_pedal_main && gm_cc_pedal_forward &&
         (safety_get_ts_elapsed(now, gm_cc_pedal_sensor_us) <= 100000U) &&
         (safety_get_ts_elapsed(now, gm_cc_pedal_main_us) <= 300000U) &&
         (safety_get_ts_elapsed(now, gm_cc_pedal_gear_us) <= (gm_cc_pedal_silverado ? 300000U : 100000U)) &&
         (!gm_cc_pedal_silverado || gm_cc_pedal_silverado_current()) &&
         !safety_rx_checks_invalid && !relay_malfunction;
}

static void gm_cc_pedal_rx(const CANPacket_t *msg) {
  if (gm_cc_pedal && (msg->bus == 0U)) {
    const uint32_t now = microsecond_timer_get();
    if (gm_cc_pedal_silverado) {
      const uint32_t addresses[8] = {0x184U, 0x34AU, 0xC9U, 0x3D1U, 0x1E1U, 0x1C4U, 0x1F5U, 0x201U};
      const uint8_t lengths[8] = {8U, 5U, 8U, 8U, 7U, 8U, 8U, 6U};
      for (uint8_t i = 0U; i < 8U; i++) {
        if ((msg->addr == addresses[i]) && (GET_LEN(msg) == lengths[i])) {
          gm_cc_pedal_silverado_seen |= (uint8_t)(1U << i);
          gm_cc_pedal_silverado_us[i] = now;
        }
      }
    }
    if ((msg->addr == 0x201U) && (GET_LEN(msg) == 6U)) {
      // Incoming tracks are independent 12-bit ADC samples, not synthesized command pairs.
      const int track1 = (msg->data[0] << 8) | msg->data[1];
      const int track2 = (msg->data[2] << 8) | msg->data[3];
      const uint8_t counter = msg->data[4] & 0xFU;
      gm_cc_pedal_sensor_valid = ((msg->data[4] >> 4) == 0U) && (gm_pedal_crc(msg) == msg->data[5]) &&
        (!gm_cc_pedal_sensor_seen || (counter != gm_cc_pedal_sensor_counter)) &&
        (track1 <= 4095) && (track2 <= 4095);
      gm_cc_pedal_sensor_seen = true;
      gm_cc_pedal_sensor_counter = counter;
      gm_cc_pedal_sensor_us = now;
      gm_cc_pedal_sensor_gas = ((track1 + track2) / 2) > 595;
      if (!gm_cc_pedal_sensor_valid) { controls_allowed = false; }
    } else if ((msg->addr == 0x3D1U) && (GET_LEN(msg) == 8U)) {
      gm_cc_pedal_stock_active = GET_BIT(msg, 39U);
      gm_cc_pedal_stock_us = now;
      cruise_engaged_prev = gm_cc_pedal_stock_active;
      if (!gm_cc_pedal_stock_active && (!gm_cc_pedal_stock_only || gm_cc_pedal_ordinary_stock)) {
        gm_cc_pedal_cancel_credit = false;
      }
    } else if ((msg->addr == 0xC9U) && (GET_LEN(msg) == 8U)) {
      gm_cc_pedal_main = GET_BIT(msg, 29U);
      gm_cc_pedal_main_us = now;
      if (!gm_cc_pedal_main) { controls_allowed = false; }
    } else if ((msg->addr == 0x1F5U) && (GET_LEN(msg) == 8U)) {
      const uint8_t gear = msg->data[3] & 0xFU;
      gm_cc_pedal_forward = ((gear == 4U) || (gear == 6U)) && !GET_BIT(msg, 41U);
      gm_cc_pedal_gear_us = now;
      if (!gm_cc_pedal_forward) { controls_allowed = false; }
    } else if ((msg->addr == 0x1E1U) && (GET_LEN(msg) == 7U)) {
      const uint8_t counter = msg->data[4] & 0x3U;
      const uint16_t checksum = 0xFFU + (counter * 0x4EFU);
      const bool neutral = (msg->data[0] == 0U) && (msg->data[1] == 0U) && (msg->data[2] == 0U) &&
        (msg->data[3] == 1U) && (msg->data[4] == counter) &&
        (msg->data[5] == (uint8_t)(0x10U | (checksum >> 8))) && (msg->data[6] == (uint8_t)checksum);
      const bool timely = safety_get_ts_elapsed(now, gm_cc_pedal_button_us) <= 300000U;
      if (neutral && (!gm_cc_pedal_button_seen ||
          (timely && (counter == ((gm_cc_pedal_button_counter + 1U) % 4U))))) {
        gm_cc_pedal_cancel_credit = true;
        gm_cc_pedal_button_us = now;
      } else if (!neutral || !timely || (counter != gm_cc_pedal_button_counter)) {
        gm_cc_pedal_cancel_credit = false;
      } else {
        // A duplicate neutral frame cannot replenish a consumed cancellation slot.
      }
      if (!gm_cc_pedal_button_seen || (counter != gm_cc_pedal_button_counter)) {
        gm_cc_pedal_button_us = now;
      }
      gm_cc_pedal_button_seen = true;
      gm_cc_pedal_button_counter = counter;
    } else {
      // Only exact selected PT sources change this owner state.
    }
    gas_pressed = gm_cc_pedal_sensor_gas;
    if (!gm_cc_pedal_main || !gm_cc_pedal_forward || !gm_cc_pedal_sensor_valid) { controls_allowed = false; }
  }
}

static bool gm_cc_pedal_tx(const CANPacket_t *msg) {
  bool allowed = true;
  if (msg->addr == 0x200U) {
    const int track1 = (msg->data[0] << 8) | msg->data[1];
    const int track2 = (msg->data[2] << 8) | msg->data[3];
    const int pair_delta = track1 - (2 * track2);
    const uint8_t counter = msg->data[4] & 0xFU;
    const bool enabled = GET_BIT(msg, 39U);
    const bool inactive = !enabled && (track1 == 0) && (track2 == 0);
    const bool active = enabled && gm_cc_pedal_current() && get_longitudinal_allowed() && !brake_pressed_prev &&
      (track1 >= 604) && (track1 <= 2633) && (track2 >= 304) && (track2 <= 1316) &&
      (pair_delta >= -16) && (pair_delta <= 16);
    allowed = !gm_cc_pedal_stock_only && (inactive || active) && ((msg->data[4] & 0x70U) == 0U) && (counter < 4U) &&
      (gm_pedal_crc(msg) == msg->data[5]) &&
      (!gm_cc_pedal_tx_seen || (counter != gm_cc_pedal_tx_counter));
    if (allowed) {
      gm_cc_pedal_tx_seen = true;
      gm_cc_pedal_tx_counter = counter;
    }
  } else if (msg->addr == 0x1E1U) {
    const uint32_t now = microsecond_timer_get();
    const uint8_t counter = gm_cc_pedal_stock_only ? gm_cc_pedal_button_counter :
      (gm_cc_pedal_button_counter + 1U) % 4U;
    const uint16_t checksum = 0xFFU + (counter * 0x4EFU) - (5U << 4);
    allowed = gm_cc_pedal_main && ((gm_cc_pedal_stock_only && !gm_cc_pedal_ordinary_stock) || gm_cc_pedal_stock_active) &&
      gm_cc_pedal_cancel_credit && (!gm_cc_pedal_ordinary_stock || !safety_rx_checks_invalid) &&
      (!gm_cc_pedal_silverado || gm_cc_pedal_silverado_current()) &&
      (safety_get_ts_elapsed(now, gm_cc_pedal_main_us) <= 300000U) &&
      (safety_get_ts_elapsed(now, gm_cc_pedal_stock_us) <= 300000U) &&
      (safety_get_ts_elapsed(now, gm_cc_pedal_button_us) <= (gm_cc_pedal_silverado ? 100000U : 300000U)) &&
      (!gm_cc_pedal_cancel_seen || (safety_get_ts_elapsed(now, gm_cc_pedal_cancel_us) > 40000U)) &&
      (msg->data[0] == 0U) && (msg->data[1] == 0U) && (msg->data[2] == 0U) &&
      (msg->data[3] == 1U) && (msg->data[4] == counter) &&
      (msg->data[5] == (uint8_t)(0x60U | (checksum >> 8))) && (msg->data[6] == (uint8_t)checksum);
    if (allowed) {
      gm_cc_pedal_cancel_credit = false;
      gm_cc_pedal_cancel_seen = true;
      gm_cc_pedal_cancel_us = now;
    }
  } else if ((msg->addr == 0x409U) || (msg->addr == 0x40AU)) {
    for (uint8_t i = 0U; i < 7U; i++) {
      allowed &= msg->data[i] == 0U;
    }
  } else {
    // Other admitted messages retain the common GM checks.
  }
  return allowed;
}
