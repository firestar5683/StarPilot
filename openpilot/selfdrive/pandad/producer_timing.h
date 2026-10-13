#pragma once
#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <pthread.h>
#include <sstream>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <thread>
#include <time.h>
#include <unistd.h>
#ifndef PANDAD_TIMING_TEST
#include <zmq.h>
#include "json11/json11.hpp"
#include "common/hardware/hw.h"
#include "common/timing.h"
#include "common/version.h"
#endif

namespace pandad_timing {
constexpr uint64_t GAP_NS = 20000000ULL;
enum Phase : unsigned {
  Can, Peripheral20, AxisBefore, AxisWrite, Health, AxisAfter, Configure,
  Peripheral2, Serial, Rate, Mutex, Flock, Ioctl, Ack, Transfer, Count
};
static_assert(std::atomic<uint64_t>::is_always_lock_free);
struct Tick { uint64_t wall = 0, cpu = 0; };
inline Tick clock_now(bool with_cpu = true) noexcept {
#ifdef PANDAD_TIMING_TEST
  (void)with_cpu;
  extern Tick test_clock() noexcept;
  return test_clock();
#else
  timespec w{}, c{};
  if (clock_gettime(CLOCK_MONOTONIC, &w) ||
      (with_cpu && clock_gettime(CLOCK_THREAD_CPUTIME_ID, &c))) return {};
  return {uint64_t(w.tv_sec) * 1000000000ULL + uint64_t(w.tv_nsec),
          uint64_t(c.tv_sec) * 1000000000ULL + uint64_t(c.tv_nsec)};
#endif
}
inline uint64_t boot_now() noexcept {
#ifdef PANDAD_TIMING_TEST
  return clock_now(false).wall;
#else
  timespec b{};
  if (clock_gettime(CLOCK_BOOTTIME, &b)) return 0;
  return uint64_t(b.tv_sec) * 1000000000ULL + uint64_t(b.tv_nsec);
#endif
}
struct Switches { int64_t voluntary = 0, involuntary = 0; bool valid = false; };
inline Switches switches_now() noexcept {
#ifdef PANDAD_TIMING_TEST
  return {0, 0, true};
#else
  rusage r{};
  if (getrusage(RUSAGE_THREAD, &r)) return {};
  return {r.ru_nvcsw, r.ru_nivcsw, true};
#endif
}
struct Stat { uint64_t wall = 0, cpu = 0, max_wall = 0, calls = 0; };
struct Transaction {
  uint64_t start = 0, end = 0, cpu = 0;
  unsigned endpoint = 0, request = 0, tx = 0, rx = 0;
  char serial[33]{};
};
struct Frame {
  Tick start{}, end{};
  Switches switches_start{}, switches_end{};
  uint64_t thread = 0, start_boot = 0, end_boot = 0;
  uint64_t can_boot = 0, can_pub = 0, can_send_boot = 0, can_count = 0, invalid = 0;
  std::array<Stat, Count> phases{};
  Transaction slowest{};
};
struct Pair { Frame before{}, current{}; uint64_t gap = 0; };
inline thread_local Frame frame{};
inline thread_local bool capturing = false;
inline bool elapsed(Tick a, Tick b, uint64_t &wall, uint64_t &cpu) noexcept {
  if (!a.wall || !b.wall || !a.cpu || !b.cpu || b.wall < a.wall || b.cpu < a.cpu) {
    ++frame.invalid;
    return false;
  }
  wall = b.wall - a.wall;
  cpu = b.cpu - a.cpu;
  return true;
}
struct Scope {
  Phase phase;
  Tick start{};
  bool active;
  explicit Scope(Phase p) noexcept : phase(p), active(capturing) {
    if (active) start = clock_now(p != Ioctl);
  }
  ~Scope() noexcept {
    if (!active) return;
    uint64_t w = 0, c = 0;
    Tick end = clock_now(phase != Ioctl);
    bool valid;
    // CPU is sampled per logical ACK/transfer, not per polling ioctl.
    if (phase == Ioctl) {
      valid = start.wall && end.wall >= start.wall;
      if (valid) w = end.wall - start.wall;
      else ++frame.invalid;
    } else {
      valid = elapsed(start, end, w, c);
    }
    if (valid) {
      auto &s = frame.phases[phase];
      s.wall += w; s.cpu += c; ++s.calls;
      if (w > s.max_wall) s.max_wall = w;
    }
  }
};
struct TransactionScope {
  Tick start{};
  Transaction row{};
  bool active;
  TransactionScope(unsigned ep, unsigned req, unsigned tx, unsigned rx,
                   const char *serial) noexcept : active(capturing) {
    if (!active) return;
    start = clock_now();
    row.endpoint = ep; row.request = req; row.tx = tx; row.rx = rx;
    if (serial) {
      size_t i = 0;
      for (; i < 32 && serial[i]; ++i) row.serial[i] = serial[i];
      row.serial[i] = 0;
    }
  }
  ~TransactionScope() noexcept {
    if (!active) return;
    Tick end = clock_now();
    uint64_t w, c;
    if (!elapsed(start, end, w, c)) return;
    if (w > frame.slowest.end - frame.slowest.start) {
      row.start = start.wall; row.end = end.wall; row.cpu = c;
      frame.slowest = row;
    }
  }
};

// One main-thread producer, one reporter. No wait, allocation, or shared logger
// mutex on the producer. Sendcan's TLS remains inactive; main mutex wait is measured.
class Recorder {
  std::array<Pair, 4> queue{};
  std::atomic<unsigned> head{0}, tail{0};
  std::atomic<bool> running{true}, ready{false};
  std::thread worker;
  Frame previous{};
  uint64_t writer_thread = 0, last_can_boot = 0, pending_gap = 0, last_report = 0;
#ifndef PANDAD_TIMING_TEST
  static json11::Json encode(const Frame &f) {
    json11::Json::array phases;
    for (unsigned i = 0; i < Count; ++i) {
      const auto &s = f.phases[i];
      phases.push_back(json11::Json::array{double(i), double(s.wall), double(s.cpu),
                                          double(s.max_wall), double(s.calls)});
    }
    const auto &t = f.slowest;
    return json11::Json::object{
      {"thread", double(f.thread)}, {"start_ns", double(f.start.wall)},
      {"end_ns", double(f.end.wall)}, {"start_cpu_ns", double(f.start.cpu)},
      {"end_cpu_ns", double(f.end.cpu)}, {"start_boot_ns", double(f.start_boot)},
      {"end_boot_ns", double(f.end_boot)}, {"can_event_boot_ns", double(f.can_boot)},
      {"can_send_mono_ns", double(f.can_pub)}, {"can_send_boot_ns", double(f.can_send_boot)},
      {"can_count", double(f.can_count)}, {"invalid", double(f.invalid)},
      {"context_switches", json11::Json::array{
        double(f.switches_start.voluntary), double(f.switches_start.involuntary),
        double(f.switches_end.voluntary), double(f.switches_end.involuntary),
        f.switches_start.valid, f.switches_end.valid}},
      {"phases", phases},
      {"slowest_spi", json11::Json::array{double(t.start), double(t.end), double(t.cpu),
        double(t.endpoint), double(t.request), double(t.tx), double(t.rx), t.serial}}
    };
  }
  void report(const char *endpoint) noexcept {
    void *context = nullptr, *socket = nullptr;
    try {
      sched_param param{};
      // Do not allocate/log while inheriting the producer's FIFO priority.
      if (pthread_setschedparam(pthread_self(), SCHED_OTHER, &param) != 0) {
        ++policy_errors;
        return;
      }
      context = zmq_ctx_new();
      socket = context ? zmq_socket(context, ZMQ_PUSH) : nullptr;
      int linger = 0, hwm = 4;
      if (!socket || zmq_setsockopt(socket, ZMQ_LINGER, &linger, sizeof(linger)) ||
          zmq_setsockopt(socket, ZMQ_SNDHWM, &hwm, sizeof(hwm)) ||
          zmq_connect(socket, endpoint ? endpoint : Path::swaglog_ipc().c_str())) {
        ++policy_errors;
      } else {
        json11::Json::object ctx{{"daemon", "pandad"}, {"version", COMMA_VERSION}};
        if (const char *v = getenv("GIT_COMMIT")) ctx["commit"] = v;
        if (const char *v = getenv("GIT_BRANCH")) ctx["branch"] = v;
        // One nonblocking startup marker, through the reporter-private socket.
        json11::Json started = json11::Json::object{
          {"ctx", ctx}, {"levelnum", 30}, {"filename", "producer_timing.h"},
          {"lineno", 0}, {"funcname", "producer_reporter"},
          {"created", seconds_since_epoch()},
          {"msg", json11::Json::object{
            {"event", "pandad.producer_ready"}, {"version", 1},
            {"producer_thread", double(writer_thread)}, {"reporter_policy", SCHED_OTHER},
            {"queue_capacity", 4}, {"capture_default_enabled", true}}}
        };
        std::string started_wire(1, char(30));
        started_wire += started.dump();
        if (zmq_send(socket, started_wire.data(), started_wire.size(), ZMQ_NOBLOCK) < 0)
          ++dropped;
        ready.store(true, std::memory_order_release);
        while (running.load(std::memory_order_relaxed)) {
          Pair row;
          if (!pop(row)) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            continue;
          }
          json11::Json msg = json11::Json::object{
            {"event", "pandad.producer_gap"}, {"version", 1},
            {"clock", "MONOTONIC/THREAD_CPUTIME"}, {"can_clock", "BOOTTIME"},
            {"ioctl_cpu_measured", false}, {"gap_ns", double(row.gap)},
            {"dropped", double(dropped.load())}, {"suppressed", double(suppressed.load())},
            {"phase_names", json11::Json::array{"can", "peripheral20", "axis_before",
              "axis_write", "health", "axis_after", "configure", "peripheral2",
              "serial", "rate", "mutex", "flock", "ioctl", "ack", "transfer"}},
            {"frames", json11::Json::array{encode(row.before), encode(row.current)}}
          };
          json11::Json record = json11::Json::object{
            {"ctx", ctx}, {"levelnum", 30}, {"filename", "producer_timing.h"},
            {"lineno", 0}, {"funcname", "producer_reporter"},
            {"created", seconds_since_epoch()}, {"msg", msg}
          };
          std::string wire(1, char(30));
          wire += record.dump();
          if (zmq_send(socket, wire.data(), wire.size(), ZMQ_NOBLOCK) < 0) ++dropped;
        }
      }
    } catch (...) {
      ++policy_errors;
    }
    ready.store(false, std::memory_order_release);
    if (socket) zmq_close(socket);
    if (context) zmq_ctx_term(context);
  }
#endif
public:
  std::atomic<uint64_t> dropped{0}, suppressed{0}, policy_errors{0};
  explicit Recorder(bool start_worker = true, const char *endpoint = nullptr) {
    writer_thread = uint64_t(syscall(SYS_gettid));
#ifndef PANDAD_TIMING_TEST
    try {
      if (start_worker) worker = std::thread([this, endpoint] { report(endpoint); });
      else ready.store(true);
    } catch (...) { ++policy_errors; }
#else
    (void)start_worker; (void)endpoint;
    ready.store(true);
#endif
  }
  ~Recorder() { running.store(false); if (worker.joinable()) worker.join(); }
  bool is_ready() const noexcept { return ready.load(std::memory_order_acquire); }
  void begin() noexcept {
    capturing = is_ready(); pending_gap = 0;
    if (!capturing) return;
    frame = {}; frame.thread = writer_thread; frame.start = clock_now();
    frame.start_boot = boot_now(); frame.switches_start = switches_now();
  }
  void can_publish(uint64_t boot, size_t count) noexcept {
    if (!capturing) return;
    frame.can_boot = boot; frame.can_pub = clock_now().wall;
    frame.can_send_boot = boot_now(); frame.can_count = count;
    if (last_can_boot && boot >= last_can_boot && boot - last_can_boot > GAP_NS)
      pending_gap = boot - last_can_boot;
    if (last_can_boot && boot < last_can_boot) ++frame.invalid;
    last_can_boot = boot;
  }
  void finish() noexcept {
    if (!capturing) return;
    frame.end = clock_now(); frame.end_boot = boot_now(); frame.switches_end = switches_now();
    if (!frame.switches_start.valid || !frame.switches_end.valid ||
        frame.switches_end.voluntary < frame.switches_start.voluntary ||
        frame.switches_end.involuntary < frame.switches_start.involuntary) ++frame.invalid;
    uint64_t wall, cpu;
    (void)elapsed(frame.start, frame.end, wall, cpu);
    capturing = false;
    if (pending_gap) {
      if (!last_report || (frame.end.wall >= last_report && frame.end.wall - last_report >= 1000000000ULL)) {
        if (push({previous, frame, pending_gap})) last_report = frame.end.wall;
      } else ++suppressed;
    }
    previous = frame;
  }
  bool push(const Pair &row) noexcept {
    unsigned h = head.load(std::memory_order_relaxed), t = tail.load(std::memory_order_acquire);
    if (!is_ready() || h - t == queue.size()) { ++dropped; return false; }
    queue[h % queue.size()] = row;
    head.store(h + 1, std::memory_order_release);
    return true;
  }
  bool pop(Pair &row) noexcept {
    unsigned t = tail.load(std::memory_order_relaxed), h = head.load(std::memory_order_acquire);
    if (h == t) return false;
    row = queue[t % queue.size()];
    tail.store(t + 1, std::memory_order_release);
    return true;
  }
};
inline thread_local Recorder *recorder = nullptr;
}
