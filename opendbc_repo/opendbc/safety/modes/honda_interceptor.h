#pragma once

static bool honda_interceptor = false;
static bool honda_interceptor_sensor_seen = false;
static bool honda_interceptor_sensor_valid = false;
static uint32_t honda_interceptor_sensor_us = 0U;

static void honda_interceptor_reset(bool enabled) {
  honda_interceptor = enabled;
  honda_interceptor_sensor_seen = false;
  honda_interceptor_sensor_valid = false;
  honda_interceptor_sensor_us = 0U;
}

static uint8_t honda_interceptor_crc(const CANPacket_t *msg) {
  uint8_t crc = 0xFFU;
  for (int i = 4; i >= 0; i--) {
    crc ^= msg->data[i];
    for (int bit = 0; bit < 8; bit++) {
      crc = (uint8_t)((crc << 1U) ^ (((crc & 0x80U) != 0U) ? 0xD5U : 0U));
    }
  }
  return crc;
}

static void honda_interceptor_rx(const CANPacket_t *msg) {
  if (honda_interceptor && msg_matches(msg, 0x201U, 0U, 6U)) {
    const unsigned int first = ((unsigned int)msg->data[0] << 8U) | msg->data[1];
    const unsigned int second = ((unsigned int)msg->data[2] << 8U) | msg->data[3];
    honda_interceptor_sensor_seen = true;
    honda_interceptor_sensor_valid = (msg->data[4] >> 4U) == 0U;
    honda_interceptor_sensor_us = microsecond_timer_get();
    gas_pressed = !honda_interceptor_sensor_valid || (((first + second) / 2U) > 492U);
    if (!honda_interceptor_sensor_valid) {
      controls_allowed = false;
    }
  }
}

static bool honda_interceptor_tx(const CANPacket_t *msg) {
  const unsigned int first = ((unsigned int)msg->data[0] << 8U) | msg->data[1];
  const unsigned int second = ((unsigned int)msg->data[2] << 8U) | msg->data[3];
  const bool enabled = (msg->data[4] & 0x80U) != 0U;
  const bool envelope = honda_interceptor && msg_matches(msg, 0x200U, 0U, 6U) &&
                        ((msg->data[4] & 0x70U) == 0U) && (msg->data[5] == honda_interceptor_crc(msg));
  bool allowed = envelope && !enabled && (first == 0U) && (second == 0U);
  if (enabled) {
    // Track two has half track one's DBC scale and the same physical offset.
    const bool tracks = (first >= 329U) && (first <= 1332U) &&
                        (second >= ((2U * first) - 1U)) && (second <= ((2U * first) + 1U));
    const bool sensor_current = honda_interceptor_sensor_seen && honda_interceptor_sensor_valid &&
      (safety_get_ts_elapsed(microsecond_timer_get(), honda_interceptor_sensor_us) <= 200000U);
    allowed = envelope && tracks && sensor_current && !safety_rx_checks_invalid && !relay_malfunction &&
              get_longitudinal_allowed() && !brake_pressed_prev;
  }
  return allowed;
}
