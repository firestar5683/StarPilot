#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>

// These match the route-derived Python CarState limits. All four inputs run at
// 10 Hz. Normal route gaps were below 126 ms, one common transport interruption
// reached 404 ms, and redundant sources stayed within 92 ms.
constexpr uint64_t EV9_VEHICLE_TELEMETRY_MAX_AGE_NS = 500000000ULL;
constexpr uint64_t EV9_VEHICLE_TELEMETRY_MAX_SOURCE_SKEW_NS = 150000000ULL;

struct Ev9VehicleTelemetrySnapshot {
  bool available = false;
  bool soc_valid = false;
  bool dte_valid = false;
  bool charging_valid = false;
  bool charge_port_valid = false;
  float fuel_gauge = 0.0F;
  float distance_to_empty = 0.0F;
  bool charging = false;
  bool charging_port_connected = false;
  float charging_time_remaining = 0.0F;
  uint64_t source_mono_time = 0ULL;
};

class Ev9VehicleTelemetryDecoder {
public:
  template <typename CanFrames>
  void update(const CanFrames &frames, uint64_t now_nanos) {
    for (const auto &frame : frames) {
      if ((frame.src != 1) || (frame.dat.size() != 32U)) {
        continue;
      }

      const auto *dat = reinterpret_cast<const uint8_t *>(frame.dat.data());
      switch (frame.address) {
        case 0x2B5:  // EV_RANGE_STATUS
          distance_to_empty_km = static_cast<float>(dat[8] | (static_cast<uint16_t>(dat[9]) << 8U));
          range_status_ts = now_nanos;
          break;
        case 0x2FA:  // EV_ENERGY_STATUS_REDUNDANT
          redundant_soc = static_cast<float>(dat[15]) * 0.5F;
          // Byte 25 bit 0 (CHARGING_STATE_AUX) is intentionally ignored. Its
          // semantics are unvalidated and it is not a charge-time value.
          redundant_energy_status_ts = now_nanos;
          break;
        case 0x30A:  // EV_CHARGE_STATUS
          charge_port_connected = (dat[3] & 0x08U) != 0U;
          charging_active_redundant = (dat[4] & 0x10U) != 0U;
          charge_port_connected_redundant = (dat[29] & 0x01U) != 0U;
          charge_status_ts = now_nanos;
          break;
        case 0x320:  // EV_ENERGY_STATUS
          charging_active = (dat[6] & 0x01U) != 0U;
          primary_soc = static_cast<float>(dat[7]) * 0.5F;
          energy_status_ts = now_nanos;
          break;
      }
    }
  }

  Ev9VehicleTelemetrySnapshot snapshot(uint64_t now_nanos) const {
    Ev9VehicleTelemetrySnapshot result;

    const bool soc_fresh = fresh(energy_status_ts, now_nanos) && fresh(redundant_energy_status_ts, now_nanos) &&
                           aligned(energy_status_ts, redundant_energy_status_ts);
    const bool soc_valid = soc_fresh && (primary_soc >= 0.0F) && (primary_soc <= 100.0F) &&
                           (redundant_soc >= 0.0F) && (redundant_soc <= 100.0F) &&
                           (std::fabs(primary_soc - redundant_soc) <= 1.0F);
    if (soc_valid) {
      result.fuel_gauge = (primary_soc + redundant_soc) / 200.0F;
      result.source_mono_time = std::max(energy_status_ts, redundant_energy_status_ts);
    }

    const bool range_valid = fresh(range_status_ts, now_nanos) &&
                             (distance_to_empty_km > 0.0F) && (distance_to_empty_km < 900.0F);
    if (range_valid) {
      result.distance_to_empty = distance_to_empty_km * 1000.0F;
      result.source_mono_time = std::max(result.source_mono_time, range_status_ts);
    }

    const bool charge_status_fresh = fresh(charge_status_ts, now_nanos);
    const bool charge_port_valid = charge_status_fresh &&
                                   (charge_port_connected == charge_port_connected_redundant);
    result.charging_port_connected = charge_port_valid && charge_port_connected;
    if (charge_port_valid) {
      result.source_mono_time = std::max(result.source_mono_time, charge_status_ts);
    }

    const bool charging_sources_fresh = fresh(energy_status_ts, now_nanos) && charge_status_fresh &&
                                        aligned(energy_status_ts, charge_status_ts);
    const bool charging_valid = charge_port_valid && charging_sources_fresh &&
                                (charging_active == charging_active_redundant) &&
                                (!charging_active || result.charging_port_connected);
    result.charging = charging_valid && charging_active;
    if (charging_valid) {
      result.source_mono_time = std::max(result.source_mono_time, energy_status_ts);
    }
    result.soc_valid = soc_valid;
    result.dte_valid = range_valid;
    result.charging_valid = charging_valid;
    result.charge_port_valid = charge_port_valid;
    result.available = soc_valid || range_valid;
    return result;
  }

private:
  static bool fresh(uint64_t timestamp_nanos, uint64_t now_nanos) {
    return (timestamp_nanos > 0ULL) && (timestamp_nanos <= now_nanos) &&
           ((now_nanos - timestamp_nanos) <= EV9_VEHICLE_TELEMETRY_MAX_AGE_NS);
  }

  static bool aligned(uint64_t first_timestamp_nanos, uint64_t second_timestamp_nanos) {
    const uint64_t difference = first_timestamp_nanos > second_timestamp_nanos ?
                                first_timestamp_nanos - second_timestamp_nanos :
                                second_timestamp_nanos - first_timestamp_nanos;
    return difference <= EV9_VEHICLE_TELEMETRY_MAX_SOURCE_SKEW_NS;
  }

  float distance_to_empty_km = 0.0F;
  float redundant_soc = 0.0F;
  float primary_soc = 0.0F;
  bool charge_port_connected = false;
  bool charge_port_connected_redundant = false;
  bool charging_active = false;
  bool charging_active_redundant = false;
  uint64_t range_status_ts = 0ULL;
  uint64_t redundant_energy_status_ts = 0ULL;
  uint64_t charge_status_ts = 0ULL;
  uint64_t energy_status_ts = 0ULL;
};
