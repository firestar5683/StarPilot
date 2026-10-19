// Compose native status parsing/negotiation with the actual wire encoder.
// This is a header contract test, not a claim of pandad thread/IPC coverage.
#include "common/tests/native_test.h"
#include "selfdrive/pandad/aol_protocol.h"
#include "selfdrive/pandad/aol_wire.h"
#include "openpilot/starpilot/car/hyundai/aol_policy.h"

namespace {
constexpr uint64_t NOW = 1000000000ULL;
const AolProfileRegistry REGISTRY{&HYUNDAI_AOL_PROFILE, 1U};

aol_safety_health_t status(uint8_t request = 0U, uint8_t permission = 0U) {
  return {AOL_SAFETY_PROTOCOL_MAGIC, AOL_SAFETY_PROTOCOL_VERSION, request, permission,
          HYUNDAI_AOL_PROFILE.mode, 0x815U, 1U};
}

std::optional<aol_safety_health_t> parsed(const aol_safety_health_t &native) {
  unsigned char bytes[sizeof(native)];
  std::memcpy(bytes, &native, sizeof(native));
  return parse_aol_status(bytes, sizeof(bytes));
}

void check_wire(const AolOutcome &outcome, const std::string &session,
                uint8_t request, uint8_t permission) {
  CHECK(outcome.compatible && outcome.status);
  const auto &native = *outcome.status;
  // Same outcome-to-fields projection as pandad.cc. Requested/allowed bits
  // must originate in the observed ACK, never the desired axis/write plan.
  AolSafetyWireFields fields{
    AOL_SAFETY_PROTOCOL_VERSION, outcome.compatible, NOW, NOW + 200000000ULL,
    native.safety_mode, native.safety_param,
    (native.permission_mask & 1U) != 0U, (native.permission_mask & 2U) != 0U,
    (native.request_mask & 1U) != 0U, (native.request_mask & 2U) != 0U,
    "owner", outcome.session,
    {NOW + 9000000000ULL, {{0U, "owner", native.safety_mode, native.safety_param, 32U, false, false, false, 0U}}}
  };
  auto encoded = encode_aol_safety_wire(fields);
  CHECK(!encoded.empty() && encoded.size() <= 512U && encoded.size() % sizeof(capnp::word) == 0U);
  auto aligned = kj::heapArray<capnp::word>(encoded.size() / sizeof(capnp::word));
  std::memcpy(aligned.begin(), encoded.data(), encoded.size());
  capnp::FlatArrayMessageReader reader(aligned.asPtr());
  auto wire = reader.getRoot<cereal::AolAxisState::SafetyWire>();
  CHECK(wire.getCompatible() && wire.getProtocolVersion() == AOL_SAFETY_PROTOCOL_VERSION);
  CHECK(std::string(wire.getAxisSessionId().cStr()) == session);
  CHECK(wire.getRequestedLateral() == ((request & 1U) != 0U));
  CHECK(wire.getRequestedLongitudinal() == ((request & 2U) != 0U));
  CHECK(wire.getLateralAllowed() == ((permission & 1U) != 0U));
  CHECK(wire.getLongitudinalAllowed() == ((permission & 2U) != 0U));
  CHECK(wire.getObservedMonoTime() == NOW && wire.getValidUntilMonoTime() == NOW + 200000000ULL);
  CHECK(wire.getSourcePandaStatesMonoTime() == NOW + 9000000000ULL);
  CHECK(wire.getPandaInventory().size() == 1U);
  CHECK(wire.getPandaInventory()[0].getHardwareSerial() == "owner");
}

void test_native_ack_to_wire() {
  AolAxisNegotiator negotiator(REGISTRY);
  AolAxisInput axis{true, true, "axis-old", NOW, NOW + 30000000ULL, NOW, true, true};
  auto plan = negotiator.prepare(parsed(status(3U, 3U)), axis, NOW, HYUNDAI_AOL_PROFILE.mode);
  CHECK(plan.capable && plan.request_mask == 0U);
  auto outcome = negotiator.complete(plan, true, parsed(status()));
  check_wire(outcome, "axis-old", 0U, 0U);

  plan = negotiator.prepare(parsed(status()), axis, NOW, HYUNDAI_AOL_PROFILE.mode);
  CHECK(plan.request_mask == 3U);
  // Native may acknowledge LAT before LONG. Serialize that exact observation.
  outcome = negotiator.complete(plan, true, parsed(status(1U, 1U)));
  check_wire(outcome, "axis-old", 1U, 1U);
  plan = negotiator.prepare(parsed(status(1U, 1U)), axis, NOW, HYUNDAI_AOL_PROFILE.mode);
  outcome = negotiator.complete(plan, true, parsed(status(3U, 1U)));
  check_wire(outcome, "axis-old", 3U, 1U);  // request is not permission

  axis.session = "axis-new";
  plan = negotiator.prepare(parsed(status(3U, 1U)), axis, NOW, HYUNDAI_AOL_PROFILE.mode);
  CHECK(plan.request_mask == 0U);
  outcome = negotiator.complete(plan, true, parsed(status(3U, 1U)));
  check_wire(outcome, "", 3U, 1U);  // delayed old ACK cannot bind the new session
  plan = negotiator.prepare(parsed(status(3U, 1U)), axis, NOW, HYUNDAI_AOL_PROFILE.mode);
  CHECK(plan.request_mask == 0U);
  outcome = negotiator.complete(plan, true, parsed(status()));
  check_wire(outcome, "axis-new", 0U, 0U);
  plan = negotiator.prepare(parsed(status()), axis, NOW, HYUNDAI_AOL_PROFILE.mode);
  CHECK(plan.request_mask == 3U);
  outcome = negotiator.complete(plan, true, parsed(status(3U, 3U)));
  check_wire(outcome, "axis-new", 3U, 3U);

  // Every failed completion requires a new zero ACK before another request.
  for (unsigned failure = 0; failure < 4U; ++failure) {
    plan = negotiator.prepare(parsed(status(3U, 3U)), axis, NOW, HYUNDAI_AOL_PROFILE.mode);
    auto after = status(3U, 3U);
    if (failure == 1U) after.magic = 0U;
    if (failure == 2U) after.safety_param = 0U;
    auto ack = failure == 3U ? std::optional<aol_safety_health_t>{} : parsed(after);
    outcome = negotiator.complete(plan, failure != 0U, ack);
    CHECK(!outcome.compatible && !outcome.status && outcome.session.empty());
    plan = negotiator.prepare(parsed(status()), axis, NOW, HYUNDAI_AOL_PROFILE.mode);
    CHECK(plan.request_mask == 0U);
    outcome = negotiator.complete(plan, true, parsed(status()));
    check_wire(outcome, "axis-new", 0U, 0U);
  }
}
}  // namespace

int main() { return run_native_test(test_native_ack_to_wire); }
