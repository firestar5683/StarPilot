#pragma once
#include <array>
#include <cstdint>
#include <cstring>

namespace spi_holder_timing {
constexpr unsigned CAPACITY = 16;
constexpr unsigned MATCHES = 4;
struct Receipt {
  uint64_t sequence = 0, thread = 0, acquired = 0, released = 0;
  uint64_t cpu = 0, ioctl_wall = 0, ioctl_cpu = 0, ack_wall = 0, ack_cpu = 0;
  unsigned role = 0, endpoint = 0, request = 0, tx = 0, rx = 0;
  bool invalid_clock = false;
  char serial[33]{};
};
struct Matches {
  uint64_t wait_start = 0, acquired = 0, overwritten = 0, omitted = 0, invalid_clocks = 0;
  unsigned count = 0;
  std::array<Receipt, MATCHES> rows{};
};
// ALL access requires the existing process-static PandaSpiHandle::hw_lock.
// Reporter receives value copies only. No atomic publication or new lock.
class History {
  std::array<Receipt, CAPACITY> rows{};
  uint64_t sequence = 0, invalid_clocks = 0;
public:
  void append(Receipt row) noexcept {
    if (row.invalid_clock || !row.acquired || row.released < row.acquired) { ++invalid_clocks; return; }
    row.sequence = ++sequence;
    rows[(sequence - 1) % CAPACITY] = row;
  }
  Matches overlap(uint64_t start, uint64_t end) const noexcept {
    Matches result;
    result.wait_start = start; result.acquired = end;
    result.invalid_clocks = invalid_clocks;
    result.overwritten = sequence > CAPACITY ? sequence - CAPACITY : 0;
    if (!start || end < start) return result;
    const uint64_t first = sequence > CAPACITY ? sequence - CAPACITY + 1 : 1;
    for (uint64_t i = first; i <= sequence; ++i) {
      const auto &row = rows[(i - 1) % CAPACITY];
      if (row.acquired < end && row.released > start) {
        if (result.count < MATCHES) result.rows[result.count++] = row;
        else ++result.omitted;
      }
    }
    return result;
  }
};
inline bool select_wait(History &source, uint64_t start, uint64_t end,
                        Matches &previous, uint64_t &invalid) noexcept {
  if (!start || !end || end < start) { ++invalid; return false; }
  if (end - start >= previous.acquired - previous.wait_start) {
    previous = source.overlap(start, end);
    return true;
  }
  return false;
}
inline History history;
inline thread_local Receipt *active = nullptr;
}
