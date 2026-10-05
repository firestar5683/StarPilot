#pragma once

#include <stdint.h>
#include <stdbool.h>

// Conventional cruise buttons only; no pedal, friction or scheduled outputs.
typedef struct {
  uint8_t generation;
  uint8_t counter;
  uint8_t last_button;
  bool credit;
  bool button_seen;
  bool active;
  bool camera_required;
  bool camera_active;
  uint64_t camera_ts;
  bool brake;
  bool gas;
  bool drive;
  bool armed;
  bool regen;
  float speed;
  uint64_t regen_ts;
  uint64_t button_ts;
  uint64_t cruise_ts;
  bool seen[7];
  uint64_t stamps[7];
} GmBoltCcGate;

static void gm_bolt_cc_reset(GmBoltCcGate *gate, unsigned int generation) {
  *gate = (GmBoltCcGate){0};
  gate->generation = (uint8_t)(((generation >= 1U) && (generation <= 3U)) ? generation : 0U);
}

static bool gm_bolt_cc_button_tuple(const uint8_t *data, unsigned int button, unsigned int counter) {
  bool valid = false;
  if ((counter <= 3U) && ((button == 1U) || (button == 2U) || (button == 3U) || (button == 6U))) {
    const unsigned int checksum = 255U + (counter * 0x4EFU) - ((button - 1U) * 16U);
    valid = (data[0] == 0U) && (data[1] == 0U) && (data[2] == 0U) && (data[3] == 1U) &&
            (data[4] == counter) && (data[5] == ((button << 4U) | ((checksum >> 8U) & 15U))) &&
            (data[6] == (checksum & 255U));
  }
  return valid;
}

static bool gm_bolt_cc_receive(GmBoltCcGate *gate, uint32_t addr, unsigned int bus, const uint8_t *data, unsigned int len, uint64_t now) {
  static const uint32_t GM_BOLT_CC_SOURCES[7] = {0x184U, 0x3D1U, 0x1E1U, 0xC9U, 0x1C4U, 0x1F5U, 0x34AU};
  static const unsigned int GM_BOLT_CC_LENGTHS[7] = {8U, 8U, 7U, 8U, 8U, 8U, 5U};

  bool accepted = false;
  if (gate->camera_required && (addr == 0x370U) && (bus == 2U) && (len == 6U) && (now > gate->camera_ts)) {
    gate->camera_active = (data[2] & 128U) != 0U;
    gate->camera_ts = now;
    accepted = true;
  }
  if ((gate->generation != 0U) && (bus == 0U) && (now != 0ULL)) {
    if ((addr == 0xBDU) && (len == 7U) && (now > gate->regen_ts)) {
      gate->regen_ts = now;
      gate->regen = ((unsigned int)data[0] >> 4U) != 0U;
      if (gate->regen) {
        gate->credit = false;
        gate->armed = false;
      }
      accepted = true;
    } else {
      int index = -1;
      for (unsigned int i = 0U; i < 7U; i++) {
        if (addr == GM_BOLT_CC_SOURCES[i]) {
          index = (int)i;
        }
      }
      if ((index >= 0) && (len == GM_BOLT_CC_LENGTHS[index]) && (!gate->seen[index] || (now > gate->stamps[index]))) {
        gate->seen[index] = true;
        gate->stamps[index] = now;

        if (addr == 0x3D1U) {
          const bool active = (data[4] & 128U) != 0U;
          if (active && !gate->active && gate->drive && !gate->brake && !gate->regen) {
            gate->armed = true;
          }
          gate->active = active;
          gate->cruise_ts = now;
          if (!gate->active) {
            if (!gate->camera_required) {
              gate->credit = false;
            }
            gate->armed = false;
          }
        }
        if (addr == 0xC9U) {
          gate->brake = (data[5] & 1U) != 0U;
          if (gate->brake) {
            gate->credit = false;
            gate->armed = false;
          }
        }
        if (addr == 0x1C4U) {
          gate->gas = data[5] != 0U;
          if (gate->gas) {
            gate->credit = false;
          }
        }
        if (addr == 0x1F5U) {
          const unsigned int gear = data[3] & 15U;
          gate->drive = ((gear == 4U) || (gear == 6U)) && ((data[5] & 2U) == 0U);
          if (!gate->drive) {
            gate->credit = false;
            gate->armed = false;
          }
        }
        if (addr == 0x34AU) {
          const unsigned int left = ((unsigned int)data[0] << 8U) | (unsigned int)data[1];
          const unsigned int right = ((unsigned int)data[2] << 8U) | (unsigned int)data[3];
          gate->speed = (float)((left < right) ? left : right) * (0.0311F / 3.6F);
        }
        if (addr == 0x1E1U) {
          gate->credit = false;
          const unsigned int counter = data[4];
          const bool forward = !gate->button_seen || (counter == ((gate->counter + 1U) % 4U));
          gate->button_seen = true;
          gate->counter = (uint8_t)counter;
          gate->button_ts = now;
          gate->credit = forward && gm_bolt_cc_button_tuple(data, 1U, counter);
          const unsigned int button = ((unsigned int)data[5] >> 4U) & 7U;
          const bool physical_valid = forward && gm_bolt_cc_button_tuple(data, button, counter);
          if (physical_valid && gate->active && gate->drive && !gate->brake && !gate->regen &&
              (((button == 2U) && (gate->last_button != 2U)) || ((button == 1U) && (gate->last_button == 3U)))) {
            gate->armed = true;
          }
          gate->last_button = (uint8_t)(physical_valid ? button : 0U);
          if ((((unsigned int)data[5] >> 4U) & 7U) == 6U) {
            gate->armed = false;
          }
        }
        accepted = true;
      }
    }
  }
  return accepted;
}

static bool gm_bolt_cc_transmit(GmBoltCcGate *gate, uint32_t addr, unsigned int bus, const uint8_t *data, unsigned int len,
                                uint64_t now, bool controls, bool long_active) {
  bool valid = false;
  if ((gate->generation != 0U) && (addr == 0x1E1U) && ((bus == 0U) || (gate->camera_required && (bus == 2U))) && (len == 7U)) {
    const unsigned int button = ((unsigned int)data[5] >> 4U) & 7U;
    const bool camera_ready = !gate->camera_required || (gate->camera_active && (gate->camera_ts > 0ULL) &&
                              (now >= gate->camera_ts) && ((now - gate->camera_ts) <= 300000000ULL));
    const bool camera_cancel = gate->camera_required && (bus == 2U) && (button == 6U);
    bool ready = gate->credit && camera_ready && (camera_cancel || gate->active);
    const bool acceleration_owned = gate->armed && gate->drive && !gate->brake && !gate->regen && !gate->gas && controls && long_active;
    for (unsigned int i = 0U; i < 7U; i++) {
      ready = ready && gate->seen[i] && (now >= gate->stamps[i]) && ((now - gate->stamps[i]) <= 300000000ULL);
    }
    ready = ready && (now > gate->button_ts) && ((now - gate->button_ts) <= 100000000ULL);
    const unsigned int counter = (gate->counter + 1U) % 4U;
    const bool cancel = button == 6U;
    // The original gas SET caller is separate from ordinary longActive requests.
    // Native requires the physical slot and gas/Drive/control ownership; host
    // requires stock speed < actual speed < HUD speed and the frame52 cadence.
    const bool gas_set = gate->armed && gate->drive && !gate->brake && !gate->regen && gate->gas && controls && (button == 3U);
    valid = ready && ((bus == 0U) || camera_cancel) && (cancel || gas_set ||
             (acceleration_owned && (gate->speed >= 10.72896F) && ((button == 2U) || (button == 3U)))) &&
             gm_bolt_cc_button_tuple(data, button, counter);
    // A matching TX attempt consumes the physical slot even when malformed.
    gate->credit = false;
  }
  return valid;
}
