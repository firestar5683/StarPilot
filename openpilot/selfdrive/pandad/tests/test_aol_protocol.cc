#include "selfdrive/pandad/aol_protocol.h"
#include "openpilot/starpilot/car/honda/aol_policy.h"
#include "openpilot/starpilot/car/hyundai/aol_policy.h"
#include "openpilot/starpilot/car/gm/aol_policy.h"

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
constexpr AolSafetyProfile VEHICLE_PROFILES[] = {HONDA_AOL_PROFILE, HYUNDAI_AOL_PROFILE, HYUNDAI_CLASSIC_AOL_PROFILE, GM_AOL_PROFILE};
const AolProfileRegistry VEHICLE_REGISTRY{VEHICLE_PROFILES, std::size(VEHICLE_PROFILES)};

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
  for (uint32_t word = 0U; word <= 65535U; word++) {
    auto forte = status();
    forte.safety_mode = HYUNDAI_CLASSIC_AOL_PROFILE.mode;
    forte.safety_param = static_cast<uint16_t>(word);
    const bool expected = word == 0x1400U || word == 0x1C00U || word == 0x1440U || word == 0x1C40U ||
                          word == 0x1402U || word == 0x1C02U || word == 0x1441U || word == 0x1C41U;
    assert(aol_capable(forte, HYUNDAI_CLASSIC_AOL_PROFILE.mode, VEHICLE_REGISTRY) == expected);
    assert(aol_runtime_enabled(false, forte, VEHICLE_REGISTRY) == expected);
    forte.capability_flags = 0U;
    assert(!aol_capable(forte, HYUNDAI_CLASSIC_AOL_PROFILE.mode, VEHICLE_REGISTRY));
  }
  {
    AolAxisNegotiator negotiator(VEHICLE_REGISTRY);
    FakeTransport transport;
    auto forte = status();
    forte.safety_mode = HYUNDAI_CLASSIC_AOL_PROFILE.mode;
    forte.safety_param = 0x1C00U;
    queue(transport, forte, forte);
    const auto first = run(negotiator, transport, axis(), NOW, HYUNDAI_CLASSIC_AOL_PROFILE.mode);
    assert(first.plan.capable && first.plan.request_mask == 0U && first.outcome.compatible);
    auto allowed = forte;
    allowed.request_mask = 1U;
    allowed.permission_mask = 1U;
    queue(transport, forte, allowed);
    const auto active = run(negotiator, transport, axis(), NOW, HYUNDAI_CLASSIC_AOL_PROFILE.mode);
    assert(active.plan.request_mask == 1U && active.outcome.compatible);
    queue(transport, allowed, forte);
    const auto stale = run(negotiator, transport, axis(), NOW + 300000000ULL, HYUNDAI_CLASSIC_AOL_PROFILE.mode);
    assert(stale.plan.request_mask == 0U);
    forte.safety_mode = HYUNDAI_AOL_PROFILE.mode;
    assert(!aol_capable(forte, HYUNDAI_AOL_PROFILE.mode, VEHICLE_REGISTRY));
  }
  for (uint32_t word = 0U; word <= 65535U; word++) {
    auto gm = status();
    gm.safety_mode = GM_AOL_PROFILE.mode;
    gm.safety_param = static_cast<uint16_t>(word);
    const auto decoded = parse_aol_status(bytes(gm).data(), sizeof(gm));
    assert(aol_capable(decoded, GM_AOL_PROFILE.mode, VEHICLE_REGISTRY) == gm_aol_param(gm.safety_param));
    gm.capability_flags = 0U;
    const auto absent = parse_aol_status(bytes(gm).data(), sizeof(gm));
    assert(!aol_capable(absent, GM_AOL_PROFILE.mode, VEHICLE_REGISTRY));
  }

  // One mode28 registry entry admits the ordinary PE transport as well as
  // the unchanged Ioniq6 profiles; this is not an independent AOL grant.
  auto pe = status();
  pe.safety_mode = HYUNDAI_AOL_PROFILE.mode;
  pe.safety_param = 0x5491U;
  assert(aol_capable(pe, HYUNDAI_AOL_PROFILE.mode, VEHICLE_REGISTRY));
  assert(aol_runtime_enabled(false, pe, VEHICLE_REGISTRY));
  for (uint16_t denied : {0x5490U, 0x5493U, 0x5495U, 0x5411U, 0x54B1U, 0x5691U}) {
    pe.safety_param = denied;
    assert(!aol_capable(pe, HYUNDAI_AOL_PROFILE.mode, VEHICLE_REGISTRY));
  }

  auto ev9 = status();
  ev9.safety_mode = HYUNDAI_AOL_PROFILE.mode;
  ev9.safety_param = 0x5C91U;
  assert(aol_capable(ev9, HYUNDAI_AOL_PROFILE.mode, VEHICLE_REGISTRY));
  assert(aol_runtime_enabled(false, ev9, VEHICLE_REGISTRY));
  for (uint16_t denied : {0x5C90U, 0x5C93U, 0x5C95U, 0x5C11U, 0x5CB1U, 0x5E91U}) {
    ev9.safety_param = denied;
    assert(!aol_capable(ev9, HYUNDAI_AOL_PROFILE.mode, VEHICLE_REGISTRY));
  }

  // Transport namespace is exactly the retained siblings plus PE and EV9. No other
  // model2/3 or LONG word gets access through this mode28 registry predicate.
  for (uint32_t word = 0U; word <= 0xFFFFU; ++word) {
    const bool expected = word == 0x0811U || word == 0x0891U || word == 0x8815U || word == 0x8895U || word == 0x5491U || word == 0x5C91U;
    assert(hyundai_aol_param(static_cast<uint16_t>(word)) == expected);
  }

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

  auto honda = status();
  honda.safety_mode = HONDA_AOL_PROFILE.mode;
  honda.safety_param = 0x22U;
  assert(aol_capable(honda, HONDA_AOL_PROFILE.mode, VEHICLE_REGISTRY));
  assert(!aol_runtime_enabled(false, honda, VEHICLE_REGISTRY));
  honda.safety_param |= 0x8U;
  assert(!aol_capable(honda, HONDA_AOL_PROFILE.mode, VEHICLE_REGISTRY));

  auto ioniq = status();
  ioniq.safety_mode = HYUNDAI_AOL_PROFILE.mode;
  ioniq.safety_param = 0x8815U;
  assert(aol_capable(ioniq, HYUNDAI_AOL_PROFILE.mode, VEHICLE_REGISTRY));
  ioniq.safety_param = 0x8895U;
  assert(aol_capable(ioniq, HYUNDAI_AOL_PROFILE.mode, VEHICLE_REGISTRY));
  for (uint16_t raw : {0x0811U, 0x0891U}) {
    ioniq.safety_param = raw;
    assert(aol_capable(ioniq, HYUNDAI_AOL_PROFILE.mode, VEHICLE_REGISTRY));
    assert(aol_runtime_enabled(false, ioniq, VEHICLE_REGISTRY));
    AolAxisNegotiator stock_negotiator(VEHICLE_REGISTRY);
    FakeTransport stock_transport;
    queue(stock_transport, ioniq, ioniq);
    auto stock_result = run(stock_negotiator, stock_transport, axis("stock-session"), NOW,
                            HYUNDAI_AOL_PROFILE.mode);
    assert(stock_transport.last_write == 0U && stock_result.outcome.compatible);
    auto stock_ack = ioniq;
    stock_ack.request_mask = stock_ack.permission_mask = 1U;
    queue(stock_transport, ioniq, stock_ack);
    stock_result = run(stock_negotiator, stock_transport, axis("stock-session"), NOW,
                       HYUNDAI_AOL_PROFILE.mode);
    assert(stock_transport.last_write == 1U && stock_result.outcome.compatible);
    auto stock_paused = axis("stock-session", false, false);
    queue(stock_transport, stock_ack, ioniq);
    stock_result = run(stock_negotiator, stock_transport, stock_paused, NOW,
                       HYUNDAI_AOL_PROFILE.mode);
    assert(stock_transport.last_write == 0U && stock_result.outcome.compatible);
  }
  for (uint16_t raw : {0x0011U, 0x0091U, 0x0810U, 0x0890U, 0x0815U, 0x0895U,
                       0x0813U, 0x0831U, 0x0911U, 0x8015U, 0x8095U, 0x8814U, 0x8894U, 0x8817U}) {
    ioniq.safety_param = raw;
    assert(!aol_capable(ioniq, HYUNDAI_AOL_PROFILE.mode, VEHICLE_REGISTRY));
  }
  ioniq.safety_param = 0x8815U;
  assert(!aol_capable(ioniq, HONDA_AOL_PROFILE.mode, VEHICLE_REGISTRY));
  assert(aol_runtime_enabled(false, ioniq, VEHICLE_REGISTRY));
  assert(aol_runtime_enabled(true, ioniq, VEHICLE_REGISTRY));
  assert(aol_runtime_enabled(true, std::nullopt, VEHICLE_REGISTRY));
  assert(!aol_runtime_enabled(false, std::nullopt, VEHICLE_REGISTRY));
  auto stock_ioniq = ioniq;
  stock_ioniq.safety_param = 0x8095U;
  assert(!aol_runtime_enabled(false, stock_ioniq, VEHICLE_REGISTRY));
  assert(!aol_runtime_enabled(false, honda, VEHICLE_REGISTRY));
  ioniq.capability_flags = 0U;
  assert(!aol_capable(ioniq, HYUNDAI_AOL_PROFILE.mode, VEHICLE_REGISTRY));
  assert(!aol_runtime_enabled(false, ioniq, VEHICLE_REGISTRY));

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

  AolAxisNegotiator ioniq_negotiator(VEHICLE_REGISTRY);
  FakeTransport ioniq_transport;
  auto i6 = status();
  i6.safety_mode = HYUNDAI_AOL_PROFILE.mode;
  i6.safety_param = 0x8815U;
  auto i6_old = i6;
  i6_old.request_mask = i6_old.permission_mask = 0x3U;
  queue(ioniq_transport, i6_old, i6);
  auto i6_result = run(ioniq_negotiator, ioniq_transport, axis("ioniq-session", true, true), NOW,
                       HYUNDAI_AOL_PROFILE.mode);
  assert(i6_result.plan.capable && ioniq_transport.last_write == 0U &&
         i6_result.outcome.compatible && i6_result.outcome.session == "ioniq-session");
  auto i6_both = i6;
  i6_both.request_mask = i6_both.permission_mask = 0x3U;
  queue(ioniq_transport, i6, i6_both);
  i6_result = run(ioniq_negotiator, ioniq_transport, axis("ioniq-session", true, true), NOW,
                  HYUNDAI_AOL_PROFILE.mode);
  assert(ioniq_transport.last_write == 0x3U && i6_result.outcome.compatible &&
         i6_result.outcome.status->permission_mask == 0x3U);
  i6.safety_param = 0x8015U; // ordinary LONG may not retain this AOL session
  queue(ioniq_transport, i6_both, i6);
  i6_result = run(ioniq_negotiator, ioniq_transport, axis("ioniq-session", true, true), NOW,
                  HYUNDAI_AOL_PROFILE.mode);
  assert(ioniq_transport.last_write == 0x3U && !i6_result.outcome.compatible);

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
