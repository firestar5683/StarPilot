#define CATCH_CONFIG_MAIN

#include <string>
#include <utility>
#include <vector>

#include "catch2/catch.hpp"
#include "selfdrive/pandad/ev9_vehicle_telemetry.h"

struct TestCanFrame {
  long address;
  std::string dat;
  long src;
};

static TestCanFrame frame(long address, std::string dat, long src = 1) {
  return {.address = address, .dat = std::move(dat), .src = src};
}

static std::string bytes_from_hex(const std::string &hex) {
  REQUIRE((hex.size() % 2U) == 0U);
  std::string result(hex.size() / 2U, '\0');
  for (size_t i = 0; i < result.size(); ++i) {
    result[i] = static_cast<char>(std::stoul(hex.substr(i * 2U, 2U), nullptr, 16));
  }
  return result;
}

static std::vector<TestCanFrame> valid_charging_frames(bool aux_bit = false) {
  std::string range(32, '\0');
  range[8] = static_cast<char>(0x98);  // 408 km, little endian
  range[9] = static_cast<char>(0x01);

  std::string redundant_energy(32, '\0');
  redundant_energy[15] = static_cast<char>(155);  // 77.5%
  redundant_energy[25] = static_cast<char>(aux_bit ? 1 : 0);

  std::string charge(32, '\0');
  charge[3] = static_cast<char>(0x08);
  charge[4] = static_cast<char>(0x10);
  charge[29] = static_cast<char>(0x01);

  std::string energy(32, '\0');
  energy[6] = static_cast<char>(0x01);
  energy[7] = static_cast<char>(155);  // 77.5%

  return {
    frame(0x2B5, range),
    frame(0x2FA, redundant_energy),
    frame(0x30A, charge),
    frame(0x320, energy),
  };
}

TEST_CASE("EV9 derived energy state is redundant and fresh") {
  Ev9VehicleTelemetryDecoder decoder;
  decoder.update(valid_charging_frames(), 1000000000ULL);

  const auto telemetry = decoder.snapshot(1000000000ULL);
  REQUIRE(telemetry.available);
  REQUIRE(telemetry.soc_valid);
  REQUIRE(telemetry.dte_valid);
  REQUIRE(telemetry.charging_valid);
  REQUIRE(telemetry.charge_port_valid);
  REQUIRE(telemetry.fuel_gauge == Approx(0.775F));
  REQUIRE(telemetry.distance_to_empty == Approx(408000.0F));
  REQUIRE(telemetry.charging);
  REQUIRE(telemetry.charging_port_connected);
  REQUIRE(telemetry.source_mono_time == 1000000000ULL);
}

TEST_CASE("EV9 archived route payload matches the DBC-derived golden state") {
  // 00000146--9faa7aa438--0, first complete four-message sample on ECAN.
  Ev9VehicleTelemetryDecoder decoder;
  decoder.update(std::vector<TestCanFrame>{frame(0x2B5, bytes_from_hex("523bd301000000809201c744000401091dea1000309b2d148a02000000645b00"))},
                 47615610813ULL);
  decoder.update(std::vector<TestCanFrame>{
    frame(0x2FA, bytes_from_hex("fa32d3047a1fc6c71b001c1d0000889e0000000000140f0f0000720140280000")),
    frame(0x30A, bytes_from_hex("fe4fd1000400000000000c002c00a00f00000000ff000000000030402100000c")),
    frame(0x320, bytes_from_hex("3951d1440000009eac0d88190001000f000000000000000000000000ef560000")),
  }, 47656322532ULL);

  const auto telemetry = decoder.snapshot(47656322532ULL);
  REQUIRE(telemetry.available);
  REQUIRE(telemetry.soc_valid);
  REQUIRE(telemetry.dte_valid);
  REQUIRE(telemetry.charge_port_valid);
  REQUIRE(telemetry.charging_valid);
  REQUIRE(telemetry.fuel_gauge == Approx(0.79F));
  REQUIRE(telemetry.distance_to_empty == Approx(402000.0F));
  REQUIRE_FALSE(telemetry.charging_port_connected);
  REQUIRE_FALSE(telemetry.charging);
  REQUIRE(telemetry.source_mono_time == 47656322532ULL);
}

TEST_CASE("EV9 SOC requires two agreeing sources") {
  auto frames = valid_charging_frames();

  SECTION("one source") {
    Ev9VehicleTelemetryDecoder decoder;
    decoder.update(std::vector<TestCanFrame>{frames[3]}, 1250000000ULL);
    const auto telemetry = decoder.snapshot(1250000000ULL);
    REQUIRE_FALSE(telemetry.available);
    REQUIRE_FALSE(telemetry.soc_valid);
    REQUIRE(telemetry.fuel_gauge == 0.0F);
  }

  SECTION("value disagreement") {
    frames[1].dat[15] = static_cast<char>(150);  // 75%, versus 77.5%
    Ev9VehicleTelemetryDecoder decoder;
    decoder.update(std::vector<TestCanFrame>{frames[1], frames[3]}, 1250000000ULL);
    const auto telemetry = decoder.snapshot(1250000000ULL);
    REQUIRE_FALSE(telemetry.available);
    REQUIRE_FALSE(telemetry.soc_valid);
    REQUIRE(telemetry.fuel_gauge == 0.0F);
  }
}

TEST_CASE("EV9 DTE enforces open 0 to 900 km bounds") {
  auto range_frame = valid_charging_frames()[0];

  SECTION("zero is invalid") {
    range_frame.dat[8] = 0;
    range_frame.dat[9] = 0;
  }
  SECTION("900 is invalid") {
    range_frame.dat[8] = static_cast<char>(0x84);
    range_frame.dat[9] = static_cast<char>(0x03);
  }

  Ev9VehicleTelemetryDecoder decoder;
  decoder.update(std::vector<TestCanFrame>{range_frame}, 1500000000ULL);
  const auto telemetry = decoder.snapshot(1500000000ULL);
  REQUIRE_FALSE(telemetry.available);
  REQUIRE_FALSE(telemetry.dte_valid);
  REQUIRE(telemetry.distance_to_empty == 0.0F);
}

TEST_CASE("EV9 stale and future samples fail neutral") {
  Ev9VehicleTelemetryDecoder decoder;
  decoder.update(valid_charging_frames(), 1000000000ULL);

  REQUIRE(decoder.snapshot(1500000000ULL).available);
  const auto stale = decoder.snapshot(1500000001ULL);
  REQUIRE_FALSE(stale.available);
  REQUIRE_FALSE(stale.soc_valid);
  REQUIRE_FALSE(stale.dte_valid);
  REQUIRE_FALSE(stale.charging_valid);
  REQUIRE_FALSE(stale.charge_port_valid);
  REQUIRE_FALSE(stale.charging);
  REQUIRE_FALSE(stale.charging_port_connected);
  REQUIRE(stale.fuel_gauge == 0.0F);
  REQUIRE(stale.distance_to_empty == 0.0F);
  REQUIRE(stale.source_mono_time == 0ULL);

  const auto future = decoder.snapshot(999999999ULL);
  REQUIRE_FALSE(future.available);
  REQUIRE_FALSE(future.charging);
  REQUIRE_FALSE(future.charging_port_connected);
}

TEST_CASE("EV9 redundant sources must be time aligned") {
  Ev9VehicleTelemetryDecoder decoder;
  auto frames = valid_charging_frames();
  decoder.update(std::vector<TestCanFrame>{frames[3]}, 2000000000ULL);
  decoder.update(std::vector<TestCanFrame>{frames[1], frames[2]}, 2150000001ULL);

  const auto telemetry = decoder.snapshot(2150000001ULL);
  REQUIRE_FALSE(telemetry.available);
  REQUIRE_FALSE(telemetry.soc_valid);
  REQUIRE_FALSE(telemetry.charging_valid);
  REQUIRE(telemetry.charge_port_valid);
  REQUIRE_FALSE(telemetry.charging);
}

TEST_CASE("EV9 disagreeing plug bits are invalid in either direction") {
  auto frames = valid_charging_frames();

  SECTION("primary true redundant false") {
    frames[2].dat[29] = static_cast<char>(0x00);
  }
  SECTION("primary false redundant true") {
    frames[2].dat[3] = static_cast<char>(0x00);
  }

  Ev9VehicleTelemetryDecoder decoder;
  decoder.update(frames, 2500000000ULL);
  const auto telemetry = decoder.snapshot(2500000000ULL);
  REQUIRE_FALSE(telemetry.charge_port_valid);
  REQUIRE_FALSE(telemetry.charging_port_connected);
  REQUIRE_FALSE(telemetry.charging_valid);
  REQUIRE_FALSE(telemetry.charging);
}

TEST_CASE("EV9 disagreeing charging bits are invalid in either direction") {
  auto frames = valid_charging_frames();

  SECTION("primary true redundant false") {
    frames[2].dat[4] = static_cast<char>(0x00);
  }
  SECTION("primary false redundant true") {
    frames[3].dat[6] = static_cast<char>(0x00);
  }

  Ev9VehicleTelemetryDecoder decoder;
  decoder.update(frames, 2750000000ULL);
  const auto telemetry = decoder.snapshot(2750000000ULL);
  REQUIRE(telemetry.charge_port_valid);
  REQUIRE(telemetry.charging_port_connected);
  REQUIRE_FALSE(telemetry.charging_valid);
  REQUIRE_FALSE(telemetry.charging);
}

TEST_CASE("EV9 partial range validity does not manufacture SOC") {
  Ev9VehicleTelemetryDecoder decoder;
  auto frames = valid_charging_frames();
  decoder.update(std::vector<TestCanFrame>{frames[0]}, 3000000000ULL);

  const auto telemetry = decoder.snapshot(3000000000ULL);
  REQUIRE(telemetry.available);
  REQUIRE_FALSE(telemetry.soc_valid);
  REQUIRE(telemetry.dte_valid);
  REQUIRE(telemetry.fuel_gauge == 0.0F);
  REQUIRE(telemetry.distance_to_empty == Approx(408000.0F));
}

TEST_CASE("EV9 unassigned auxiliary bit never becomes charge time") {
  Ev9VehicleTelemetryDecoder decoder;
  decoder.update(valid_charging_frames(true), 4000000000ULL);

  const auto telemetry = decoder.snapshot(4000000000ULL);
  REQUIRE(telemetry.charging);
  REQUIRE(telemetry.charging_time_remaining == 0.0F);
}

TEST_CASE("EV9 decoder ignores the wrong bus and frame shape") {
  Ev9VehicleTelemetryDecoder decoder;
  auto frames = valid_charging_frames();
  frames[0].src = 0;
  frames[1].dat.resize(31);
  decoder.update(frames, 5000000000ULL);

  const auto telemetry = decoder.snapshot(5000000000ULL);
  REQUIRE_FALSE(telemetry.available);
  REQUIRE_FALSE(telemetry.soc_valid);
  REQUIRE_FALSE(telemetry.dte_valid);
}

TEST_CASE("EV9 decoder isolates the internal ECAN source") {
  auto frames = valid_charging_frames();
  for (auto &item : frames) {
    item.src = 0x81;  // returned internal ECAN frames are not fresh vehicle input
  }
  frames.push_back(frame(0x321, std::string(32, '\0'), 1));  // unknown ECAN address
  auto external_panda_frames = valid_charging_frames();
  for (auto &item : external_panda_frames) {
    item.src = 5;  // bus 1 on a second Panda
    frames.push_back(item);
  }

  Ev9VehicleTelemetryDecoder decoder;
  decoder.update(frames, 6000000000ULL);
  const auto telemetry = decoder.snapshot(6000000000ULL);
  REQUIRE_FALSE(telemetry.available);
  REQUIRE_FALSE(telemetry.soc_valid);
  REQUIRE_FALSE(telemetry.dte_valid);
  REQUIRE(telemetry.source_mono_time == 0ULL);
}
