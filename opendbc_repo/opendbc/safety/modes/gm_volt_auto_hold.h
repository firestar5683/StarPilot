#pragma once

// Exact admitted Volt inactive friction owner. This never grants controls_allowed.
static bool gm_volt_auto_hold = false;
static bool gm_hold_alt_brake = false;
static bool gm_hold_c9_brake = false;
static bool gm_hold_extended_be = false;
static bool gm_hold_sdgm;
static bool gm_hold_accepted;
static bool gm_hold_near_stop;
static uint8_t gm_hold_tx_bus = 2U;
static bool gm_hold_seen[7];
static uint32_t gm_hold_us[7];
static bool gm_hold_brake_unavailable;
static bool gm_hold_main;
static bool gm_hold_forward;
static bool gm_hold_gas;
static bool gm_hold_brake;
static bool gm_hold_regen;
static bool gm_hold_stopped;
static bool gm_hold_armed;
static bool gm_hold_moving;
static uint8_t gm_hold_acc;
static uint32_t gm_hold_drive_us;
static uint32_t gm_hold_regen_release_us;
static bool gm_hold_regen_released;
static bool gm_hold_counter_seen;
static uint8_t gm_hold_counter;

static void gm_hold_reset(bool enabled, bool alternate, bool c9_brake, bool extended_be, uint8_t tx_bus, bool sdgm) {
  gm_volt_auto_hold = enabled;
  gm_hold_alt_brake = alternate;
  gm_hold_c9_brake = c9_brake;
  gm_hold_extended_be = extended_be;
  gm_hold_tx_bus = tx_bus;
  gm_hold_sdgm = sdgm; gm_hold_accepted = false; gm_hold_near_stop = false;
  for (uint8_t i = 0U; i < 7U; i++) { gm_hold_seen[i] = false; gm_hold_us[i] = 0U; }
  gm_hold_brake_unavailable = true;
  gm_hold_main = false; gm_hold_forward = false; gm_hold_gas = false;
  gm_hold_brake = false; gm_hold_regen = false; gm_hold_stopped = false; gm_hold_armed = false; gm_hold_moving = false;
  gm_hold_acc = 0U; gm_hold_drive_us = 0U; gm_hold_regen_release_us = 0U;
  gm_hold_regen_released = false; gm_hold_counter_seen = false; gm_hold_counter = 0U;
}

static bool gm_hold_sources_current(uint32_t now) {
  bool current = true;
  for (uint8_t i = 0U; i < 7U; i++) {
    current &= gm_hold_seen[i] && (safety_get_ts_elapsed(now, gm_hold_us[i]) <= 300000U);
  }
  return current;
}

static bool gm_hold_ready(uint32_t now) {
  if (gm_hold_regen_released && (safety_get_ts_elapsed(now, gm_hold_regen_release_us) >= 1000000U)) {
    gm_hold_regen_released = false;
  }
  const bool cooldown = gm_hold_regen_released;
  return !safety_rx_checks_invalid && !relay_malfunction && gm_hold_sources_current(now) && gm_hold_main && gm_hold_forward && !gm_hold_gas &&
         !gm_hold_regen && !gm_hold_brake_unavailable && !cooldown && (gm_hold_drive_us >= 3000000U);
}

static void gm_hold_rx(const CANPacket_t *msg) {
  if (gm_volt_auto_hold && (msg->bus == 0U)) {
    const uint32_t now = microsecond_timer_get();
    int source = -1;
    if ((msg->addr == 0xC9U) && (GET_LEN(msg) == 8U)) {
      source = 0; gm_hold_main = GET_BIT(msg, 29U);
      if (gm_hold_c9_brake) {
        gm_hold_brake = GET_BIT(msg, 40U);
        gm_hold_seen[2] = true; gm_hold_us[2] = now;
      }
    } else if ((msg->addr == 0x1F5U) && (GET_LEN(msg) == 8U)) {
      source = 1;
      const uint8_t gear = msg->data[3] & 0xFU;
      // Physical forward gear remains valid in manumatic; never synthesize PRNDL.
      gm_hold_forward = (gear == 4U) || (gear == 6U) || ((gear >= 4U) && (gear <= 7U) && GET_BIT(msg, 41U));
      if (!gm_hold_forward) { gm_hold_drive_us = 0U; }
    } else if (!gm_hold_c9_brake && (msg->addr == (gm_hold_alt_brake ? 0xF1U : 0xBEU)) &&
               ((GET_LEN(msg) == 6U) || (gm_hold_extended_be && ((GET_LEN(msg) == 7U) || (GET_LEN(msg) == 8U))))) {
      source = 2; gm_hold_brake = msg->data[1] >= (gm_hold_alt_brake ? 6U : 8U);
    } else if ((msg->addr == 0x1C4U) && (GET_LEN(msg) == 8U)) {
      source = 3; gm_hold_gas = msg->data[5] != 0U; gm_hold_acc = msg->data[1] >> 5;
    } else if ((msg->addr == 0x34AU) && (GET_LEN(msg) == 5U)) {
      source = 4;
      const uint16_t left = ((uint16_t)msg->data[0] << 8) | msg->data[1];
      const uint16_t right = ((uint16_t)msg->data[2] << 8) | msg->data[3];
      gm_hold_stopped = (left <= 10U) && (right <= 10U);
      gm_hold_near_stop = (left <= 28U) && (right <= 28U);
      if (!gm_hold_near_stop) { gm_hold_accepted = false; }
      gm_hold_moving = (left > 0U) || (right > 0U);
      const uint32_t elapsed = safety_get_ts_elapsed(now, gm_hold_us[4]);
      // Raw wheel units are .0311 km/h; twelve units exceed .1 m/s.
      if (gm_hold_sources_current(now) && gm_hold_forward && (left >= 12U) && (right >= 12U) && (elapsed <= 300000U)) {
        gm_hold_drive_us = SAFETY_MIN(gm_hold_drive_us + elapsed, 3000000U);
      }
    } else if ((msg->addr == 0xBDU) && (GET_LEN(msg) == 7U)) {
      source = 5;
      const bool pressed = (msg->data[0] >> 4) != 0U;
      if (gm_hold_regen && !pressed) { gm_hold_regen_release_us = now; gm_hold_regen_released = true; }
      gm_hold_regen = pressed;
    } else if ((msg->addr == 0x232U) && (GET_LEN(msg) == 8U)) {
      source = 6; gm_hold_brake_unavailable = GET_BIT(msg, 46U);
    } else {
      // Unrelated or malformed traffic cannot refresh physical authority.
    }
    if (source >= 0) { gm_hold_seen[source] = true; gm_hold_us[source] = now; }
    if (!gm_hold_ready(now)) { gm_hold_armed = false; gm_hold_accepted = false; }
    else if (gm_hold_moving || gm_hold_brake) { gm_hold_armed = true; }
    else { /* Retain a previously armed stopped hold. */ }
    if (get_longitudinal_allowed()) { gm_hold_accepted = false; }
  }
}

static bool gm_hold_brake_tx(const CANPacket_t *msg, int brake) {
  const uint32_t now = microsecond_timer_get();
  const uint8_t mode = msg->data[0] >> 4;
  const uint8_t counter = msg->data[4] & 3U;
  const uint16_t raw_brake = ((uint16_t)(msg->data[0] & 15U) << 8) | msg->data[1];
  const uint16_t expected = (uint16_t)(0x10000U - ((uint32_t)mode << 12) - raw_brake - counter);
  const uint16_t checksum = ((uint16_t)msg->data[2] << 8) | msg->data[3];
  const bool release = (brake == 0) && (mode == 1U);
  const bool packet_valid = (msg->bus == gm_hold_tx_bus) && (GET_LEN(msg) == 5U) &&
                            (checksum == expected) && ((msg->data[4] & 0xFCU) == 0U) &&
                            (release || !gm_hold_counter_seen || (counter == ((gm_hold_counter + 1U) & 3U)));
  const bool hold_mode = (((mode == 0xAU) || (mode == 0xBU)) && (gm_hold_acc != 4U)) || ((mode == 0xDU) && (gm_hold_acc == 4U));
  if (!gm_hold_ready(now)) { gm_hold_armed = false; gm_hold_accepted = false; }
  const bool stationary = gm_hold_stopped || (gm_hold_sdgm && gm_hold_accepted && gm_hold_near_stop);
  const int minimum = gm_hold_sdgm ? 100 : 80;
  const bool hold = gm_hold_armed && gm_hold_ready(now) && stationary &&
                    (brake >= minimum) && (brake <= 240) && hold_mode;
  const bool permitted = packet_valid && (release || hold);
  if (permitted) {
    gm_hold_counter_seen = true; gm_hold_counter = counter;
    gm_hold_accepted = !release;
  }
  return permitted;
}
