#include "selfdrive/pandad/aol_protocol.h"

#include <cassert>
#include <cstring>
#include <deque>
#include <vector>

namespace {
constexpr uint8_t TEST_MODE = 7U;
constexpr uint8_t TEST_ALT_MODE = 8U;
constexpr uint16_t TEST_PARAM = 0x1234U;
constexpr uint64_t NOW = 1000000000ULL;

bool test_param(uint16_t param) { return param == TEST_PARAM; }
bool test_alt_param(uint16_t param) { return param == 0x2345U; }
constexpr AolSafetyProfile TEST_PROFILES[] = {
  {TEST_MODE, test_param, false}, {TEST_ALT_MODE, test_alt_param, false},
};
const AolProfileRegistry TEST_REGISTRY{TEST_PROFILES, std::size(TEST_PROFILES)};

aol_safety_health_t status(uint8_t request = 0U, uint8_t permission = 0U) {
  return {AOL_SAFETY_PROTOCOL_MAGIC, AOL_SAFETY_PROTOCOL_VERSION, request, permission,
          TEST_MODE, TEST_PARAM, 0x1U};
}

std::vector<unsigned char> bytes(const aol_safety_health_t &s) {
  std::vector<unsigned char> raw(sizeof(s));
  std::memcpy(raw.data(), &s, sizeof(s));
  return raw;
}

struct FakeTransport {
  std::deque<std::vector<unsigned char>> replies;
  bool write_ok = true;
  bool wrote = false;
  uint8_t last_write = 0xffU;

  std::optional<aol_safety_health_t> read() {
    if (replies.empty()) return std::nullopt;
    auto raw = replies.front();
    replies.pop_front();
    return parse_aol_status(raw.data(), static_cast<int>(raw.size()));
  }

  bool write(uint8_t request) {
    wrote = true;
    last_write = request;
    return write_ok;
  }
};

struct Step {
  AolWritePlan plan;
  AolOutcome outcome;
};

Step run(AolAxisNegotiator &negotiator, FakeTransport &transport, const AolAxisInput &axis,
         uint64_t now_ns = NOW, uint8_t expected_mode = TEST_MODE) {
  auto before = transport.read();
  auto plan = negotiator.prepare(before, axis, now_ns, expected_mode);
  bool write_ok = plan.capable && transport.write(plan.request_mask);
  auto after = write_ok ? transport.read() : std::nullopt;
  return {plan, negotiator.complete(plan, write_ok, after)};
}

AolAxisInput axis(const char *session = "drive-1", bool lat = true, bool lon = false) {
  return {true, true, session, NOW - 1000000ULL, NOW + 100000000ULL,
          NOW - 1000000ULL, lat, lon};
}

void queue(FakeTransport &transport, const aol_safety_health_t &before,
           const aol_safety_health_t &after) {
  transport.replies.push_back(bytes(before));
  transport.replies.push_back(bytes(after));
}
}  // namespace

int main() {
  static_assert(sizeof(aol_safety_health_t) == 11U);
  static_assert(offsetof(aol_safety_health_t, safety_param) == 8U);
  static_assert(offsetof(aol_safety_health_t, capability_flags) == 10U);
  const uint64_t sampled_mono = aol_monotonic_ns();
  assert(sampled_mono > 0U && aol_monotonic_ns() >= sampled_mono);

  auto valid = status();
  auto valid_bytes = bytes(valid);
  assert(!parse_aol_status(nullptr, 0));
  assert(!parse_aol_status(valid_bytes.data(), static_cast<int>(valid_bytes.size()) - 1));
  valid.magic = 0;
  auto wrong_magic = bytes(valid);
  assert(!parse_aol_status(wrong_magic.data(), static_cast<int>(wrong_magic.size())));
  valid = status();
  valid.version = AOL_SAFETY_PROTOCOL_VERSION + 1U;
  auto wrong_version = bytes(valid);
  assert(!parse_aol_status(wrong_version.data(), static_cast<int>(wrong_version.size())));

  auto unsupported = status();
  const AolProfileRegistry empty_registry{nullptr, 0U};
  assert(!aol_capable(unsupported, TEST_MODE, empty_registry));
  assert(!aol_runtime_enabled(false, unsupported, empty_registry));
  assert(aol_runtime_enabled(true, unsupported, empty_registry));
  const AolProfileRegistry null_storage{nullptr, 1U};
  assert(!aol_capable(unsupported, TEST_MODE, null_storage));
  const AolSafetyProfile null_predicate{TEST_MODE, nullptr, true};
  const AolProfileRegistry null_predicate_registry{&null_predicate, 1U};
  assert(!aol_capable(unsupported, TEST_MODE, null_predicate_registry));
  assert(!aol_runtime_enabled(false, unsupported, null_predicate_registry));
  unsupported.capability_flags = 0U;  // RELEASE/old firmware
  assert(!aol_capable(unsupported, TEST_MODE, TEST_REGISTRY));
  unsupported = status();
  unsupported.safety_mode = 1U;
  assert(!aol_capable(unsupported, TEST_MODE, TEST_REGISTRY));
  unsupported = status();
  unsupported.safety_param ^= 0x1U;
  assert(!aol_capable(unsupported, TEST_MODE, TEST_REGISTRY));

  AolAxisNegotiator negotiator(TEST_REGISTRY);
  AolAxisNegotiator temporary_registry_negotiator(AolProfileRegistry{TEST_PROFILES, std::size(TEST_PROFILES)});
  FakeTransport temporary_registry_transport;
  queue(temporary_registry_transport, status(), status());
  const auto temporary_registry_result = run(temporary_registry_negotiator, temporary_registry_transport, axis());
  assert(temporary_registry_result.plan.capable && temporary_registry_result.outcome.compatible);
  FakeTransport t;
  t.replies.push_back({});  // absent/short first reply cannot authorize a write
  auto result = run(negotiator, t, axis());
  assert(!result.plan.capable && !result.outcome.compatible && !t.wrote);

  queue(t, status(0x3U, 0x3U), status());  // new process flushes old request first
  result = run(negotiator, t, axis());
  assert(result.plan.capable && t.last_write == 0U && result.outcome.compatible);
  assert(result.outcome.session == "drive-1");
  queue(t, status(), status(0x1U, 0x1U));
  result = run(negotiator, t, axis());
  assert(t.last_write == 0x1U && result.outcome.status->request_mask == 0x1U);

  queue(t, status(0x1U, 0x1U), status(0x1U, 0x1U));
  result = run(negotiator, t, axis("drive-1", true, true));
  assert(t.last_write == 0x3U && result.outcome.compatible);
  assert(result.outcome.status->request_mask == 0x1U);  // old long ack; lat remains usable
  queue(t, status(0x3U, 0x3U), status(0x3U, 0x3U));
  result = run(negotiator, t, axis("drive-1", false, true));
  assert(t.last_write == 0x2U && result.outcome.status->request_mask == 0x3U);

  queue(t, status(0x3U, 0x3U), status());
  result = run(negotiator, t, axis("drive-2"));
  assert(t.last_write == 0U && result.outcome.session == "drive-2");
  queue(t, status(), status(0x1U, 0x1U));
  result = run(negotiator, t, axis("drive-2"));
  assert(t.last_write == 0x1U);

  auto stale = axis("drive-2");
  stale.valid_until_ns = NOW - 1U;
  queue(t, status(0x1U, 0x1U), status());
  result = run(negotiator, t, stale);
  assert(t.last_write == 0U && result.outcome.status->request_mask == 0U);

  t.replies.push_back(bytes(status()));
  t.write_ok = false;
  result = run(negotiator, t, axis("drive-3"));
  assert(t.last_write == 0U && !result.outcome.compatible && result.outcome.session.empty());
  t.write_ok = true;
  queue(t, status(), status(0x1U, 0x1U));  // zero write without zero ack cannot finish reset
  result = run(negotiator, t, axis("drive-3"));
  assert(t.last_write == 0U && result.outcome.session.empty());
  queue(t, status(), status());
  result = run(negotiator, t, axis("drive-3"));
  assert(t.last_write == 0U && result.outcome.session == "drive-3");

  t.replies.push_back(bytes(status()));
  t.replies.push_back({});  // failed second read invalidates this tick and resets
  result = run(negotiator, t, axis("drive-3"));
  assert(t.last_write == 0x1U && !result.outcome.compatible);
  queue(t, status(), status());
  result = run(negotiator, t, axis("drive-3"));
  assert(t.last_write == 0U && result.outcome.session == "drive-3");

  auto wrong_identity = status();
  wrong_identity.safety_mode = 1U;
  queue(t, status(), wrong_identity);  // safety identity changed after the write
  result = run(negotiator, t, axis("drive-3"));
  assert(t.last_write == 0x1U && !result.outcome.compatible);
  queue(t, status(), status());
  result = run(negotiator, t, axis("drive-3"));
  assert(t.last_write == 0U && result.outcome.session == "drive-3");

  AolAxisNegotiator mode_switch_negotiator(TEST_REGISTRY);
  FakeTransport switch_transport;
  queue(switch_transport, status(), status());
  result = run(mode_switch_negotiator, switch_transport, axis("same-session"));
  assert(switch_transport.last_write == 0U && result.outcome.compatible);
  queue(switch_transport, status(), status(0x1U, 0x1U));
  result = run(mode_switch_negotiator, switch_transport, axis("same-session"));
  assert(switch_transport.last_write == 0x1U);
  auto alternate = status();
  alternate.safety_mode = TEST_ALT_MODE;
  alternate.safety_param = 0x2345U;
  queue(switch_transport, alternate, alternate);
  result = run(mode_switch_negotiator, switch_transport, axis("same-session"), NOW, TEST_ALT_MODE);
  assert(switch_transport.last_write == 0U && result.outcome.compatible);

  // A fresh Python axis frame uses CLOCK_MONOTONIC. Treating BOOTTIME as the
  // same clock after a nine-second suspend leaves the native request at zero.
  AolAxisNegotiator mono_negotiator(TEST_REGISTRY);
  FakeTransport mono_transport;
  queue(mono_transport, status(), status());
  result = run(mono_negotiator, mono_transport, axis("clock-session"), NOW);
  assert(result.plan.request_mask == 0U && result.outcome.compatible);
  queue(mono_transport, status(), status(0x1U, 0x1U));
  result = run(mono_negotiator, mono_transport, axis("clock-session"), NOW + 1000000ULL);
  assert(result.plan.request_mask == 0x1U);
  queue(mono_transport, status(0x1U, 0x1U), status());
  result = run(mono_negotiator, mono_transport, axis("clock-session"), NOW + 201000000ULL);
  assert(result.plan.request_mask == 0U);  // genuine stale frame still revoked

  // Suspended axes keep only the already-negotiated physical arm. No actuator
  // request is added, and a fresh session or stale frame cannot retain it.
  AolAxisNegotiator paused_negotiator(TEST_REGISTRY);
  FakeTransport paused_transport;
  auto paused = axis("paused-session", false, false);
  paused.retain_lateral_arm = true;
  queue(paused_transport, status(), status());
  result = run(paused_negotiator, paused_transport, paused);
  assert(result.plan.request_mask == 0U && !result.plan.retain_lateral_arm);
  for (int i = 0; i < 5; ++i) {
    queue(paused_transport, status(), status());
    result = run(paused_negotiator, paused_transport, paused);
    assert(result.plan.request_mask == 0U && result.plan.retain_lateral_arm);
  }
  queue(paused_transport, status(), status(0x1U, 0x1U));
  result = run(paused_negotiator, paused_transport, axis("paused-session"));
  assert(result.plan.request_mask == 0x1U);
  queue(paused_transport, status(0x1U, 0x1U), status());
  result = run(paused_negotiator, paused_transport, paused, NOW + 201000000ULL);
  assert(result.plan.request_mask == 0U && !result.plan.retain_lateral_arm);
  paused.alive_valid = false;
  queue(paused_transport, status(), status());
  result = run(paused_negotiator, paused_transport, paused);
  assert(result.plan.request_mask == 0U && !result.plan.retain_lateral_arm);
  paused.alive_valid = true;
  paused.session = "replacement-session";
  queue(paused_transport, status(), status());
  result = run(paused_negotiator, paused_transport, paused);
  assert(result.plan.request_mask == 0U && !result.plan.retain_lateral_arm);
  paused.retain_lateral_arm = false;
  queue(paused_transport, status(), status());
  result = run(paused_negotiator, paused_transport, paused);
  assert(result.plan.request_mask == 0U && !result.plan.retain_lateral_arm);

  AolAxisNegotiator boot_negotiator(TEST_REGISTRY);
  FakeTransport boot_transport;
  queue(boot_transport, status(), status());
  result = run(boot_negotiator, boot_transport, axis("clock-session"), NOW + 9000000000ULL);
  assert(result.plan.request_mask == 0U && result.outcome.compatible);
  queue(boot_transport, status(), status());
  result = run(boot_negotiator, boot_transport, axis("clock-session"), NOW + 9001000000ULL);
  assert(result.plan.request_mask == 0U);
}
