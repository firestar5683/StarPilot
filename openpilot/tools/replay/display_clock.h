#pragma once

#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <limits>
#include <mutex>
#include <string>
#include <sys/file.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>

#include "common/timing.h"

class ReplayDisplayClock {
public:
  static uint64_t host_now() {
    timespec now;
#ifdef __APPLE__
    clock_gettime(CLOCK_UPTIME_RAW, &now);
#else
    clock_gettime(CLOCK_MONOTONIC, &now);
#endif
    return now.tv_sec * 1000000000ULL + now.tv_nsec;
  }
  static constexpr uint64_t MAGIC = 0x53505250434c4b31ULL;
  static constexpr uint32_t VALID = 1, PAUSED = 2, SEEKING = 4, BOOT_KNOWN = 8;
  struct Record {
    uint64_t sequence, magic;
    uint32_t version, flags;
    uint64_t epoch, route_ns, host_ns;
    double speed;
    int64_t boot_offset_ns;
    uint64_t heartbeat_ns, reserved;
  };
  static_assert(sizeof(Record) == 80);

  ReplayDisplayClock() {
    const char *runtime = std::getenv("SP_HOST_RUNTIME");
    const char *prefix_env = std::getenv("OPENPILOT_PREFIX");
    const char *path_env = std::getenv("SP_REPLAY_CLOCK_PATH");
    if (!runtime || std::string(runtime) != "1" || !prefix_env || !path_env) return;
    std::string prefix(prefix_env);
    if (prefix.rfind("replay-", 0) != 0 || prefix.size() <= 7 || prefix.size() > 55 ||
        prefix.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") != std::string::npos) return;
#ifdef __APPLE__
    const std::string root = "/tmp";
#else
    const std::string root = "/dev/shm";
#endif
    const std::string parent = root + "/msgq_" + prefix;
    if (std::string(path_env) != parent + "/display-clock") return;
    int directory = open(parent.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    struct stat directory_stat = {};
    if (directory < 0) return;
    if (fstat(directory, &directory_stat) || !S_ISDIR(directory_stat.st_mode) ||
        directory_stat.st_uid != getuid() || (directory_stat.st_mode & 07777) != 0700) {
      close(directory);
      return;
    }
    int file = openat(directory, "display-clock", O_RDWR | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    close(directory);
    struct stat file_stat = {};
    if (file < 0) return;
    if (fstat(file, &file_stat) || !S_ISREG(file_stat.st_mode) || file_stat.st_uid != getuid() ||
        (file_stat.st_mode & 07777) != 0600 || file_stat.st_nlink != 1 || file_stat.st_size != sizeof(Record) || flock(file, LOCK_EX | LOCK_NB)) {
      close(file);
      return;
    }
    void *mapping = mmap(nullptr, sizeof(Record), PROT_READ | PROT_WRITE, MAP_SHARED, file, 0);
    if (mapping == MAP_FAILED) {
      close(file);
      return;
    }
    file_ = file;
    shared_ = static_cast<Record *>(mapping);
    state_.magic = MAGIC;
    state_.version = 1;
    state_.epoch = 1;
    state_.speed = 1.0;
    state_.host_ns = host_now();
    write_locked();
    heartbeat_ = std::thread([this]() {
      std::unique_lock lock(lock_);
      while (!stopped_) {
        if (wake_.wait_for(lock, std::chrono::milliseconds(50), [this]() { return stopped_; })) break;
        write_locked();
      }
    });
  }

  ~ReplayDisplayClock() {
    stop();
    if (shared_) munmap(shared_, sizeof(Record));
    if (file_ >= 0) close(file_);
  }

  void stop() {
    {
      std::lock_guard lock(lock_);
      if (stopped_) return;
      stopped_ = true;
      state_.flags &= ~VALID;
      write_locked();
    }
    wake_.notify_all();
    if (heartbeat_.joinable()) heartbeat_.join();
  }

  bool active() const { return shared_ != nullptr; }

  void seek(uint64_t route_ns) {
    if (!shared_) return;
    std::lock_guard lock(lock_);
    ++state_.epoch;
    state_.route_ns = route_ns;
    state_.host_ns = host_now();
    state_.flags = (state_.flags & PAUSED) | SEEKING;
    state_.boot_offset_ns = 0;
    write_locked();
  }

  void pause(bool paused) {
    if (!shared_) return;
    std::lock_guard lock(lock_);
    reanchor_locked(host_now());
    if (paused) state_.flags |= PAUSED;
    else state_.flags &= ~PAUSED;
    write_locked();
  }

  void set_speed(double speed) {
    if (!shared_) return;
    if (!std::isfinite(speed) || speed <= 0.0) return;
    std::lock_guard lock(lock_);
    reanchor_locked(host_now());
    state_.speed = speed;
    write_locked();
  }

  void published(uint64_t route_ns, double speed) {
    if (!shared_) return;
    std::lock_guard lock(lock_);
    state_.route_ns = route_ns;
    state_.host_ns = host_now();
    state_.speed = speed;
    state_.flags = (state_.flags & (PAUSED | BOOT_KNOWN)) | VALID;
    write_locked();
  }

  void observe_boot_pair(uint64_t mono_ns, uint64_t boot_ns) {
    if (!shared_) return;
    if (mono_ns == 0 || boot_ns < mono_ns || boot_ns - mono_ns > uint64_t(std::numeric_limits<int64_t>::max())) return;
    std::lock_guard lock(lock_);
    state_.boot_offset_ns = boot_ns - mono_ns;
    state_.flags |= BOOT_KNOWN;
    write_locked();
  }

private:
  void reanchor_locked(uint64_t host_ns) {
    if ((state_.flags & VALID) && !(state_.flags & PAUSED) && host_ns >= state_.host_ns) {
      long double route_ns = state_.route_ns + (host_ns - state_.host_ns) * static_cast<long double>(state_.speed);
      if (route_ns >= std::numeric_limits<uint64_t>::max()) state_.flags &= ~VALID;
      else state_.route_ns = static_cast<uint64_t>(route_ns);
    }
    state_.host_ns = host_ns;
  }

  void write_locked() {
    if (!shared_) return;
    state_.heartbeat_ns = host_now();
    sequence_ += 2;
    __atomic_store_n(&shared_->sequence, sequence_ - 1, __ATOMIC_SEQ_CST);
    std::memcpy(reinterpret_cast<char *>(shared_) + sizeof(uint64_t),
                reinterpret_cast<const char *>(&state_) + sizeof(uint64_t), sizeof(Record) - sizeof(uint64_t));
    __atomic_store_n(&shared_->sequence, sequence_, __ATOMIC_RELEASE);
  }

  int file_ = -1;
  Record *shared_ = nullptr;
  Record state_ = {};
  uint64_t sequence_ = 0;
  bool stopped_ = false;
  std::mutex lock_;
  std::condition_variable wake_;
  std::thread heartbeat_;
};
