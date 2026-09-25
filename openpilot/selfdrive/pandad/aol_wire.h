#pragma once

#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include <capnp/message.h>
#include <capnp/serialize.h>

#include "openpilot/cereal/gen/cpp/custom.capnp.h"

// Inner bounded, flat Cap'n Proto payload for Event.aolSafetyWire @124 :Data.
// The outer Event validity remains a separate native status check.
struct AolPandaSlot {
  uint16_t slot_index = 0;
  std::string hardware_serial;
  uint16_t safety_model = 0;
  uint16_t safety_param = 0;
  uint16_t alternative_experience = 0;
  bool controls_allowed = false;
  bool safety_rx_checks_invalid = false;
  bool heartbeat_lost = false;
  uint32_t faults = 0;
};

struct AolPandaStateSnapshot {
  // Source Event BOOTTIME stamp: provenance only, not the wire's lease clock.
  uint64_t source_mono_time = 0;
  std::vector<AolPandaSlot> slots;
};

struct AolSafetyWireFields {
  uint16_t protocol_version = 0;
  bool compatible = false;
  uint64_t observed_mono_time = 0;
  uint64_t valid_until_mono_time = 0;
  uint16_t safety_model = 0;
  uint16_t safety_param = 0;
  bool lateral_allowed = false;
  bool longitudinal_allowed = false;
  bool requested_lateral = false;
  bool requested_longitudinal = false;
  std::string panda_serial;
  std::string axis_session_id;
  AolPandaStateSnapshot inventory;
};

inline std::vector<uint8_t> encode_aol_safety_wire(const AolSafetyWireFields &fields) {
  if (fields.panda_serial.size() > 96 || fields.axis_session_id.size() > 96 ||
      fields.valid_until_mono_time < fields.observed_mono_time) return {};
  if (fields.inventory.source_mono_time == 0U || fields.inventory.slots.empty() || fields.inventory.slots.size() > 2U) return {};
  for (const auto &slot : fields.inventory.slots) {
    if (slot.hardware_serial.empty() || slot.hardware_serial.size() > 96U) return {};
  }
  capnp::MallocMessageBuilder builder;
  auto out = builder.initRoot<cereal::AolAxisState::SafetyWire>();
  out.setKind(1U);
  out.setVersion(2U);
  out.setProtocolVersion(fields.protocol_version);
  out.setCompatible(fields.compatible);
  out.setObservedMonoTime(fields.observed_mono_time);
  out.setValidUntilMonoTime(fields.valid_until_mono_time);
  out.setSafetyModel(fields.safety_model);
  out.setSafetyParam(fields.safety_param);
  out.setLateralAllowed(fields.lateral_allowed);
  out.setLongitudinalAllowed(fields.longitudinal_allowed);
  out.setRequestedLateral(fields.requested_lateral);
  out.setRequestedLongitudinal(fields.requested_longitudinal);
  out.setPandaSerial(fields.panda_serial);
  out.setAxisSessionId(fields.axis_session_id);
  out.setSourcePandaStatesMonoTime(fields.inventory.source_mono_time);
  auto inventory = out.initPandaInventory(fields.inventory.slots.size());
  for (size_t i = 0; i < fields.inventory.slots.size(); ++i) {
    const auto &slot = fields.inventory.slots[i];
    auto entry = inventory[i];
    entry.setSlotIndex(slot.slot_index);
    entry.setHardwareSerial(slot.hardware_serial);
    entry.setSafetyModel(slot.safety_model);
    entry.setSafetyParam(slot.safety_param);
    entry.setAlternativeExperience(slot.alternative_experience);
    entry.setControlsAllowed(slot.controls_allowed);
    entry.setSafetyRxChecksInvalid(slot.safety_rx_checks_invalid);
    entry.setHeartbeatLost(slot.heartbeat_lost);
    entry.setFaults(slot.faults);
  }
  auto flat = capnp::messageToFlatArray(builder);
  auto bytes = flat.asBytes();
  if (bytes.size() > 512) return {};
  return {bytes.begin(), bytes.end()};
}

// Card's armed bit keeps a previously authorized session alive while its axis
// request is zero. It never grants an actuator request or native permission.
inline bool aol_armed_intent(kj::ArrayPtr<const capnp::byte> bytes, uint64_t message_ns,
                             uint64_t car_state_ns, uint64_t now_ns, bool optional_release = false) {
  constexpr uint64_t MAX_AGE_NS = 30000000ULL;
  if (bytes.size() < 16U || bytes.size() > 512U || bytes.size() % 8U != 0U ||
      message_ns == 0U || car_state_ns == 0U || message_ns > now_ns ||
      car_state_ns > now_ns || now_ns - message_ns > MAX_AGE_NS ||
      (message_ns > car_state_ns ? message_ns - car_state_ns : car_state_ns - message_ns) > MAX_AGE_NS) return false;
  uint32_t segments = 0U, words = 0U;
  std::memcpy(&segments, bytes.begin(), sizeof(segments));
  std::memcpy(&words, bytes.begin() + 4U, sizeof(words));
  if (segments != 0U || words > 63U || bytes.size() != 8U + 8U * words) return false;
  try {
    auto aligned = kj::heapArray<capnp::word>(bytes.size() / sizeof(capnp::word));
    std::memcpy(aligned.begin(), bytes.begin(), bytes.size());
    capnp::ReaderOptions options;
    options.traversalLimitInWords = 63U;
    options.nestingLimit = 4;
    capnp::FlatArrayMessageReader reader(aligned.asPtr(), options);
    auto intent = reader.getRoot<cereal::AolAxisState::IntentWire>();
    auto producer = intent.getProducerSessionId();
    return intent.getKind() == 2U && intent.getVersion() == 1U &&
           producer.size() > 0U && producer.size() <= 96U &&
           intent.getSettingsQualified() && (optional_release ? intent.getOptionalSetRelease() : intent.getLateralArmed()) &&
           intent.getCarStateLogMonoTime() == message_ns &&
           intent.getObservedMonoTime() <= now_ns &&
           now_ns - intent.getObservedMonoTime() <= MAX_AGE_NS &&
           now_ns <= intent.getValidUntilMonoTime();
  } catch (const kj::Exception &) {
    return false;
  }
}
