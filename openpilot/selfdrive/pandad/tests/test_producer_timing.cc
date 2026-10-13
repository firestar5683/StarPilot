#define PANDAD_TIMING_TEST
#include "selfdrive/pandad/producer_timing.h"
#include <cassert>

using namespace pandad_timing;
static Tick next{1, 1};
Tick pandad_timing::test_clock() noexcept { return next; }

int main() {
  Recorder collector(false);
  next = {100, 10};
  collector.begin();
  {
    Scope lock(Mutex);
    next = {3100, 110};
  }
  assert(frame.phases[Mutex].wall == 3000 && frame.phases[Mutex].cpu == 100);
  {
    Scope io(Ioctl);
    next = {9000, 111};
  }
  assert(frame.phases[Ioctl].wall == 5900 && frame.phases[Ioctl].cpu == 0);
  {
    Scope bad(Flock);
    next = {8000, 110};
  }
  assert(frame.invalid == 1 && frame.phases[Flock].calls == 0);
  next = {10000, 120};
  collector.can_publish(10000, 12);
  collector.finish();
  next = {10010, 121};
  collector.begin();
  {
    TransactionScope txn(0x81, 0, 0, 1984, "abc");
    next = {20010, 122};
  }
  assert(frame.slowest.endpoint == 0x81 && frame.slowest.end - frame.slowest.start == 10000);
  collector.can_publish(30010001, 162);
  collector.finish();
  Pair pair;
  assert(collector.pop(pair));
  assert(pair.gap == 30000001);
  assert(pair.before.phases[Mutex].wall == 3000 && pair.current.can_count == 162);
  assert(!collector.pop(pair));
  for (int i = 0; i < 4; ++i) assert(collector.push(pair));
  assert(!collector.push(pair) && collector.dropped == 1);
  for (int i = 0; i < 4; ++i) assert(collector.pop(pair));
  assert(!collector.pop(pair));
  // Inactive scopes do not call the clock or modify a completed frame.
  auto saved = frame.phases[Mutex].calls;
  {
    Scope inert(Mutex);
    next = {99, 1};
  }
  assert(frame.phases[Mutex].calls == saved);
  // Actual SPSC concurrency: only successful pushes count; consumer checks every
  // field so stale/overwritten/torn slots cannot pass as merely matching totals.
  Recorder concurrent(false);
  std::atomic<bool> done{false};
  std::atomic<unsigned> received{0};
  std::thread consumer([&] {
    uint64_t last = 0;
    Pair row;
    while (!done.load(std::memory_order_acquire) || received.load() < 5000) {
      if (concurrent.pop(row)) {
        assert(row.gap == last + 1);
        assert(row.current.can_count == row.gap * 3);
        last = row.gap;
        ++received;
      } else std::this_thread::yield();
    }
  });
  for (uint64_t i = 1; i <= 5000; ++i) {
    Pair row;
    row.gap = i;
    row.current.can_count = i * 3;
    while (!concurrent.push(row)) std::this_thread::yield();
  }
  done.store(true, std::memory_order_release);
  consumer.join();
  assert(received == 5000);
}
