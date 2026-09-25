#include "selfdrive/pandad/aol_wire.h"
#include "openpilot/cereal/gen/cpp/log.capnp.h"

#include <cassert>
#include <cstdio>
#include <string>

static constexpr uint64_t now = 1000000000ULL;

int main() {
  const AolSafetyWireFields fields = {1, true, 100, 200, 5, 34, true, false, true, false, "panda", "axis",
    {now + 9000000000ULL, {{0, "panda", 5, 34, 0, true, false, false, 0}}}};
  auto bytes = encode_aol_safety_wire(fields);
  assert(!bytes.empty() && bytes.size() <= 512);
  capnp::MallocMessageBuilder event_builder;
  auto event = event_builder.initRoot<cereal::Event>();
  event.setAolSafetyWire(kj::arrayPtr(bytes.data(), bytes.size()));
  assert(event.isAolSafetyWire());
  auto aligned = kj::heapArray<capnp::word>(bytes.size() / sizeof(capnp::word));
  std::memcpy(aligned.begin(), bytes.data(), bytes.size());
  capnp::FlatArrayMessageReader current(aligned.asPtr());
  auto wire = current.getRoot<cereal::AolAxisState::SafetyWire>();
  assert(wire.getVersion() == 2U && wire.getPandaSerial() == "panda");
  assert(wire.getSourcePandaStatesMonoTime() == now + 9000000000ULL);
  assert(wire.getPandaInventory().size() == 1U);
  assert(wire.getPandaInventory()[0].getHardwareSerial() == "panda");
  assert(wire.getPandaInventory()[0].getSafetyParam() == 34U);
  // Historic exact v1 bytes remain readable after adding the custom fields.
  const uint64_t legacy_words[] = {
    0x0000000900000000ULL, 0x0002000400000000ULL, 0x0005000100010b01ULL,
    0x0000000000000064ULL, 0x00000000000000c8ULL, 0x0000000000000022ULL,
    0x0000003200000005ULL, 0x0000002a00000005ULL, 0x00000061646e6170ULL,
    0x0000000073697861ULL
  };
  capnp::FlatArrayMessageReader legacy(kj::arrayPtr(reinterpret_cast<const capnp::word *>(legacy_words),
                                                  sizeof(legacy_words) / sizeof(capnp::word)));
  auto old_wire = legacy.getRoot<cereal::AolAxisState::SafetyWire>();
  assert(old_wire.getVersion() == 1U && old_wire.getPandaSerial() == "panda");
  assert(old_wire.getSourcePandaStatesMonoTime() == 0U && old_wire.getPandaInventory().size() == 0U);
  for (uint8_t value : bytes) std::printf("%02x", value);
  std::printf("\n");
  auto bad = fields;
  bad.panda_serial = std::string(97, 'x');
  assert(encode_aol_safety_wire(bad).empty());
  bad = fields;
  bad.valid_until_mono_time = 99;
  assert(encode_aol_safety_wire(bad).empty());
  bad = fields;
  bad.inventory = {};
  assert(encode_aol_safety_wire(bad).empty());
  bad = fields;
  bad.inventory.slots[0].hardware_serial = std::string(97, 'x');
  assert(encode_aol_safety_wire(bad).empty());
  bad = fields;
  bad.inventory.slots.push_back({1, "auxiliary", 19, 0, 0, false, false, false, 0});
  auto pair_bytes = encode_aol_safety_wire(bad);
  assert(!pair_bytes.empty() && pair_bytes.size() <= 512U);
  bad.inventory.slots.push_back({2, "third", 19, 0, 0, false, false, false, 0});
  assert(encode_aol_safety_wire(bad).empty());
  capnp::MallocMessageBuilder intent_builder;
  auto intent = intent_builder.initRoot<cereal::AolAxisState::IntentWire>();
  intent.setKind(2);
  intent.setVersion(1);
  intent.setProducerSessionId("card-session");
  intent.setCarStateLogMonoTime(now - 10000000ULL);
  intent.setObservedMonoTime(now - 10000000ULL);
  intent.setValidUntilMonoTime(now + 100000000ULL);
  intent.setSettingsQualified(true);
  intent.setLateralArmed(true);
  auto armed = [&](uint64_t message_ns = now - 10000000ULL, uint64_t source_ns = now - 10000000ULL) {
    auto flat = capnp::messageToFlatArray(intent_builder);
    return aol_armed_intent(flat.asBytes(), message_ns, source_ns, now);
  };
  assert(armed());
  assert(armed(now - 10000000ULL, now - 20000000ULL)); // newest Card may precede the next axis publication
  assert(!armed(0));
  assert(!armed(now + 1));
  assert(!armed(now - 31000000ULL));
  assert(!armed(now - 10000000ULL, now + 1));
  assert(!armed(now - 10000000ULL, now - 41000000ULL));
  intent.setLateralArmed(false);
  assert(!armed());
  intent.setLateralArmed(true);
  intent.setSettingsQualified(false);
  assert(!armed());
  intent.setSettingsQualified(true);
  intent.setObservedMonoTime(now + 1);
  assert(!armed());
  intent.setObservedMonoTime(now - 31000000ULL);
  assert(!armed());
  intent.setObservedMonoTime(now - 10000000ULL);
  intent.setValidUntilMonoTime(now - 1);
  assert(!armed());
  intent.setValidUntilMonoTime(now + 100000000ULL);
  intent.setKind(1);
  assert(!armed());
  intent.setKind(2);
  intent.setVersion(2);
  assert(!armed());
  intent.setVersion(1);
  intent.setProducerSessionId("");
  assert(!armed());
  intent.setProducerSessionId(std::string(97, 'x'));
  assert(!armed());
  intent.setProducerSessionId("card-session");
  auto flat = capnp::messageToFlatArray(intent_builder);
  auto raw = flat.asBytes();
  std::vector<capnp::byte> malformed(raw.begin(), raw.end());
  malformed[0] = 1; // multiple segments are forbidden
  assert(!aol_armed_intent(kj::arrayPtr(malformed.data(), malformed.size()), now - 10000000ULL, now - 10000000ULL, now));
  malformed[0] = 0;
  malformed[8] = 0xff; // malformed root pointer
  assert(!aol_armed_intent(kj::arrayPtr(malformed.data(), malformed.size()), now - 10000000ULL, now - 10000000ULL, now));
  return 0;
}
