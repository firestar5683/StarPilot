// Compose Card's real wire freshness predicate with native command negotiation.
// No scheduler, clock, transport or production publisher is replaced here.
#include "common/tests/native_test.h"
#include "selfdrive/pandad/aol_protocol.h"
#include "selfdrive/pandad/aol_wire.h"
#include "openpilot/starpilot/car/hyundai/aol_policy.h"

namespace {
constexpr uint64_t NOW = 1000000000ULL;
constexpr uint64_t CARD = NOW - 10000000ULL;
constexpr uint64_t SOURCE = CARD - 40000000ULL;
const AolProfileRegistry REGISTRY{&HYUNDAI_AOL_PROFILE, 1U};

const aol_safety_health_t STATUS{AOL_SAFETY_PROTOCOL_MAGIC, AOL_SAFETY_PROTOCOL_VERSION,
                                0U, 0U, HYUNDAI_AOL_PROFILE.mode, 0x815U, 1U};

void test_card_and_axis_leases() {
  // A current Card arm can outlive an axis's short command lease, only in
  // the axis session that has already completed its own native zero ACK.
  for (unsigned mutation = 0; mutation < 10U; ++mutation) {
    AolAxisNegotiator negotiator(REGISTRY);
    AolAxisInput axis{true, true, "axis-1", NOW - 40000000ULL, NOW - 1U,
                      NOW - 40000000ULL, true, true};
    auto initial = axis;
    initial.observed_ns = initial.message_ns = NOW;
    initial.valid_until_ns = NOW + 30000000ULL;
    auto zero = negotiator.prepare(STATUS, initial, NOW, HYUNDAI_AOL_PROFILE.mode);
    CHECK(zero.capable && zero.request_mask == 0U);
    CHECK(negotiator.complete(zero, true, STATUS).session == "axis-1");

    capnp::MallocMessageBuilder builder;
    auto intent = builder.initRoot<cereal::AolAxisState::IntentWire>();
    intent.setKind(2U);
    intent.setVersion(1U);
    intent.setProducerSessionId("card-1");
    intent.setSequence(1U);
    intent.setCarStateLogMonoTime(CARD);
    intent.setObservedMonoTime(CARD);
    intent.setValidUntilMonoTime(NOW + 20000000ULL);
    intent.setSettingsQualified(true);
    intent.setLateralArmed(true);
    uint64_t stamp = CARD;
    uint64_t source = SOURCE;
    std::string producer = "card-1";
    if (mutation == 1U) producer = "replacement-card";
    if (mutation == 2U) stamp = NOW - 30000001ULL;
    if (mutation == 3U) intent.setSequence(0U);
    if (mutation == 4U) intent.setSettingsQualified(false);
    if (mutation == 5U) intent.setLateralArmed(false);
    if (mutation == 6U) intent.setObservedMonoTime(CARD - 1U);
    if (mutation == 7U) source = CARD - 200000001ULL;
    if (mutation == 8U) axis.session = "replacement-axis";
    if (mutation == 9U) axis.alive_valid = false;
    auto flat = capnp::messageToFlatArray(builder);
    axis.retain_lateral_arm = aol_armed_intent(flat.asBytes(), stamp, source, NOW, false, producer);
    CHECK(axis.retain_lateral_arm == (mutation == 0U || mutation >= 8U));
    const auto expired = negotiator.prepare(STATUS, axis, NOW, HYUNDAI_AOL_PROFILE.mode);
    CHECK(expired.capable && expired.request_mask == 0U);
    CHECK(expired.retain_lateral_arm == (mutation == 0U));
    // No intent flag or source/session mutation can resurrect either command.
    CHECK((expired.request_mask & 3U) == 0U);
  }

  // Boundary composition: Card and axis age limits are independent. A Card
  // at exactly 30 ms retains an expired axis arm at exactly 200 ms; moving
  // either clock one nanosecond past its own boundary removes retention.
  for (unsigned boundary = 0; boundary < 3U; ++boundary) {
    AolAxisNegotiator negotiator(REGISTRY);
    AolAxisInput axis{true, true, "boundary", NOW, NOW + 1U, NOW, true, true};
    auto zero = negotiator.prepare(STATUS, axis, NOW, HYUNDAI_AOL_PROFILE.mode);
    CHECK(negotiator.complete(zero, true, STATUS).session == "boundary");
    const uint64_t card_ns = NOW - 30000000ULL - (boundary == 1U ? 1U : 0U);
    axis.observed_ns = axis.message_ns = NOW - AOL_AXIS_MESSAGE_MAX_AGE_NS - (boundary == 2U ? 1U : 0U);
    axis.valid_until_ns = axis.observed_ns + 30000000ULL;
    capnp::MallocMessageBuilder builder;
    auto intent = builder.initRoot<cereal::AolAxisState::IntentWire>();
    intent.setKind(2U); intent.setVersion(1U); intent.setSequence(1U);
    intent.setProducerSessionId("card-boundary");
    intent.setCarStateLogMonoTime(card_ns); intent.setObservedMonoTime(card_ns);
    intent.setValidUntilMonoTime(NOW); intent.setSettingsQualified(true); intent.setLateralArmed(true);
    auto flat = capnp::messageToFlatArray(builder);
    axis.retain_lateral_arm = aol_armed_intent(flat.asBytes(), card_ns, axis.observed_ns, NOW, false, "card-boundary");
    auto plan = negotiator.prepare(STATUS, axis, NOW, HYUNDAI_AOL_PROFILE.mode);
    CHECK(plan.request_mask == 0U && plan.retain_lateral_arm == (boundary == 0U));
  }
}
}  // namespace

int main() { return run_native_test(test_card_and_axis_leases); }
