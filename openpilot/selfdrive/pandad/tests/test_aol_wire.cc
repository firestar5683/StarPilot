#include "selfdrive/pandad/aol_wire.h"
#include "openpilot/cereal/gen/cpp/log.capnp.h"

#include <cassert>
#include <cstdio>
#include <string>

static constexpr uint64_t now = 1000000000ULL;
static constexpr uint64_t GAP_NOW = 91564707308ULL;
static constexpr uint64_t CARD_NS = 91560387360ULL;
static constexpr uint64_t AXIS_SOURCE_NS = 91529338245ULL;

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

  // The exact route2f/1 Card packet is 4.32 ms old, but 31.05 ms newer
  // than the delayed axis source. Only its acknowledged producer can retain
  // the physical arm. Optional release and all command leases stay unchanged.
  intent.setSequence(5206);
  intent.setCarStateLogMonoTime(CARD_NS);
  intent.setObservedMonoTime(CARD_NS);
  intent.setValidUntilMonoTime(CARD_NS + 200000000ULL);
  intent.setLateralArmed(true);
  intent.setOptionalSetRelease(true);
  auto retained = [&](const std::string &producer = "card-session", bool optional = false,
                      uint64_t stamp = CARD_NS, uint64_t source = AXIS_SOURCE_NS, uint64_t clock = GAP_NOW) {
    auto wire = capnp::messageToFlatArray(intent_builder);
    return aol_armed_intent(wire.asBytes(), stamp, source, clock, optional, producer);
  };
  assert(retained());
  assert(retained("card-session", false, CARD_NS, AXIS_SOURCE_NS, CARD_NS + 30000000ULL));
  assert(retained("card-session", false, CARD_NS, CARD_NS - 200000000ULL));
  assert(!retained(""));
  assert(!retained("different-card-session"));
  assert(!retained("card-session", true));
  assert(!retained("card-session", false, CARD_NS, CARD_NS + 30000001ULL, CARD_NS + 30000001ULL));
  assert(!retained("card-session", false, CARD_NS, CARD_NS - 200000001ULL));
  assert(!retained("card-session", false, CARD_NS, AXIS_SOURCE_NS, CARD_NS + 30000001ULL));
  assert(!retained("card-session", false, CARD_NS + 1U));
  intent.setSequence(0);
  assert(!retained());
  intent.setSequence(5206);
  intent.setObservedMonoTime(CARD_NS - 1U);
  assert(!retained());
  intent.setObservedMonoTime(CARD_NS);
  intent.setCarStateLogMonoTime(CARD_NS - 1U);
  assert(!retained());
  intent.setCarStateLogMonoTime(CARD_NS);
  intent.setValidUntilMonoTime(GAP_NOW - 1U);
  assert(!retained());
  intent.setValidUntilMonoTime(CARD_NS + 200000000ULL);
  intent.setSettingsQualified(false);
  assert(!retained());
  intent.setSettingsQualified(true);
  intent.setLateralArmed(false);
  assert(!retained());
  return 0;
}
