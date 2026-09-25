#pragma once

#include <cstdint>
#include <cstddef>
#include <cstring>
#include <ctime>
#include <limits>
#include <optional>
#include <string>

#ifdef __APPLE__
#include <mach/mach_time.h>
#endif

#include "panda/board/health.h"

constexpr uint64_t AOL_AXIS_MESSAGE_MAX_AGE_NS = 200000000ULL;

struct AolSafetyProfile {
  uint8_t mode;
  bool (*accepts_param)(uint16_t);
  bool normal_runtime;
};

struct AolProfileRegistry {
  const AolSafetyProfile *profiles;
  size_t count;

  const AolSafetyProfile *find(uint8_t mode) const {
    if (profiles == nullptr) return nullptr;
    for (size_t i = 0; i < count; ++i) {
      if (profiles[i].mode == mode) return &profiles[i];
    }
    return nullptr;
  }

  const AolSafetyProfile *find(uint8_t mode, uint16_t param) const {
    if (profiles == nullptr) return nullptr;
    for (size_t i = 0; i < count; ++i) {
      if (profiles[i].mode == mode && profiles[i].accepts_param != nullptr && profiles[i].accepts_param(param)) return &profiles[i];
    }
    return nullptr;
  }
};

// Python messaging.new_message and the AOL host use time.monotonic_ns().
// Linux CLOCK_BOOTTIME includes suspend time; the regular pandad clocks stay
// unchanged, while this protocol uses the matching monotonic epoch only.
inline uint64_t aol_monotonic_ns() {
#ifdef __APPLE__
  mach_timebase_info_data_t scale{};
  if (mach_timebase_info(&scale) != KERN_SUCCESS || scale.denom == 0U) return 0U;
  const __uint128_t ns = (static_cast<__uint128_t>(mach_absolute_time()) * scale.numer) / scale.denom;
  return ns <= std::numeric_limits<uint64_t>::max() ? static_cast<uint64_t>(ns) : 0U;
#else
  timespec ts{};
  if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0 || ts.tv_sec < 0 || ts.tv_nsec < 0 || ts.tv_nsec >= 1000000000L) return 0U;
  const __uint128_t ns = static_cast<__uint128_t>(ts.tv_sec) * 1000000000U + ts.tv_nsec;
  return ns <= std::numeric_limits<uint64_t>::max() ? static_cast<uint64_t>(ns) : 0U;
#endif
}

inline std::optional<aol_safety_health_t> parse_aol_status(const unsigned char *data, int count) {
  if (data == nullptr || count != static_cast<int>(sizeof(aol_safety_health_t))) return std::nullopt;
  aol_safety_health_t status{};
  std::memcpy(&status, data, sizeof(status));
  if (status.magic != AOL_SAFETY_PROTOCOL_MAGIC || status.version != AOL_SAFETY_PROTOCOL_VERSION) return std::nullopt;
  return status;
}

inline bool aol_capable(const std::optional<aol_safety_health_t> &status, uint8_t expected_mode,
                        const AolProfileRegistry &registry) {
  const AolSafetyProfile *profile = registry.find(expected_mode, status ? status->safety_param : 0U);
  return status && profile && profile->accepts_param && (status->capability_flags & 0x1U) != 0U &&
         status->safety_mode == expected_mode && profile->accepts_param(status->safety_param);
}

inline bool aol_runtime_enabled(bool replay, const std::optional<aol_safety_health_t> &status,
                                const AolProfileRegistry &registry) {
  if (replay) return true;
  if (!status) return false;
  const AolSafetyProfile *profile = registry.find(status->safety_mode, status->safety_param);
  return profile && profile->normal_runtime && aol_capable(status, profile->mode, registry);
}

struct AolAxisInput {
  bool alive_valid = false;
  bool qualified = false;
  std::string session;
  uint64_t observed_ns = 0;
  uint64_t valid_until_ns = 0;
  uint64_t message_ns = 0;
  bool desired_lateral = false;
  bool desired_longitudinal = false;
  bool retain_lateral_arm = false;
  bool optional_set_release = false;
};

struct AolWritePlan {
  bool capable = false;
  uint8_t request_mask = 0;
  bool retain_lateral_arm = false;
};

struct AolOutcome {
  bool compatible = false;
  std::optional<aol_safety_health_t> status;
  std::string session;
};

// One pandad owner negotiates a new host session with a native zero-request
// acknowledgement before allowing either independent axis to be requested.
class AolAxisNegotiator {
public:
  explicit AolAxisNegotiator(const AolProfileRegistry &registry) : registry_(registry) {}

  AolWritePlan prepare(const std::optional<aol_safety_health_t> &before, const AolAxisInput &axis,
                       uint64_t now_ns, uint8_t expected_mode) {
    const uint16_t param = before ? before->safety_param : 0U;
    const bool optional_capable = before && ((before->capability_flags & 0x2U) != 0U);
    if (expected_mode != expected_mode_ || param != expected_param_ || optional_capable != optional_capable_) {
      reset_pending_ = true;
    }
    expected_mode_ = expected_mode;
    expected_param_ = param;
    optional_capable_ = optional_capable;
    if (!aol_capable(before, expected_mode, registry_)) {
      reset_pending_ = true;
      return {};
    }
    if (axis.alive_valid && axis.qualified && !axis.session.empty() &&
        axis.observed_ns <= now_ns && now_ns <= axis.valid_until_ns &&
        axis.message_ns <= now_ns && now_ns - axis.message_ns <= AOL_AXIS_MESSAGE_MAX_AGE_NS) {
      if (axis.session != session_) {
        session_ = axis.session;
        reset_pending_ = true;
      }
      if (!reset_pending_) {
        return {true, static_cast<uint8_t>((axis.desired_lateral ? 0x1U : 0U) |
                                           (axis.desired_longitudinal ? 0x2U : 0U) |
                                           ((axis.optional_set_release && (before->capability_flags & 0x2U) != 0U &&
                                             (before->safety_param == 0x815U || before->safety_param == 0x895U)) ? 0x4U : 0U)),
                axis.retain_lateral_arm};
      }
    }
    return {true, 0U};
  }

  AolOutcome complete(const AolWritePlan &plan, bool write_ok,
                      const std::optional<aol_safety_health_t> &after) {
    if (!plan.capable || !write_ok || !aol_capable(after, expected_mode_, registry_)) {
      reset_pending_ = true;
      return {};
    }
    if (after->safety_param != expected_param_ ||
        (((plan.request_mask & 0x4U) != 0U) && (after->capability_flags & 0x2U) == 0U)) {
      reset_pending_ = true;
      return {};
    }
    if (reset_pending_ && plan.request_mask == 0U && after->request_mask == 0U) {
      reset_pending_ = false;
    }
    return {true, after, reset_pending_ ? "" : session_};
  }

private:
  AolProfileRegistry registry_;
  std::string session_;
  bool reset_pending_ = true;
  uint8_t expected_mode_ = 0;
  uint16_t expected_param_ = 0;
  bool optional_capable_ = false;
};
