// Native regression tests exercise the actual Params/FileLock implementation.
#include <sys/file.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <poll.h>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
#include <chrono>
#include <atomic>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include "common/tests/native_test.h"

static int fail_ex = 0;
static std::atomic<int> unlocks{0};
static int observed_flock(int fd, int op) {
  if (op == LOCK_UN) ++unlocks;
  if (op == LOCK_EX && fail_ex != 0) {
    errno = fail_ex;
    fail_ex = 0;
    return -1;
  }
  return ::flock(fd, op);
}
// Fault injection applies only to actual FileLock's syscall and retains all
// production declarations/method bodies. Other test probes call real flock.
#define flock observed_flock
#ifdef PARAMS_IMPLEMENTATION
#include PARAMS_IMPLEMENTATION
#else
#include "common/params.cc"
#endif
#undef flock

static void check(bool good, const char *message) {
  native_test_check(good, message, __FILE__, __LINE__);
}
static void send_byte(int fd) { check(write(fd, "x", 1) == 1, "pipe write"); }
static bool receive_byte(int fd, int ms) {
  pollfd p{fd, POLLIN, 0};
  if (poll(&p, 1, ms) != 1) return false;
  char c;
  return read(fd, &c, 1) == 1;
}
static bool available(const std::string &path) {
  int fd = open(path.c_str(), O_RDONLY | O_CLOEXEC);
  check(fd >= 0, "probe open");
  bool good = ::flock(fd, LOCK_EX | LOCK_NB) == 0;
  if (good) check(::flock(fd, LOCK_UN) == 0, "probe unlock");
  else check(errno == EWOULDBLOCK || errno == EAGAIN, "probe expected contention");
  close(fd);
  return good;
}
static void finish(pid_t child, int release, bool ready) {
  if (ready) send_byte(release);
  else kill(child, SIGKILL);
  int status = 0;
  check(waitpid(child, &status, 0) == child, "reap child");
  if (ready) check(WIFEXITED(status) && WEXITSTATUS(status) == 0, "child clean exit");
}
static void inherited_release(const std::string &path) {
  int ready[2], release[2]; check(pipe(ready) == 0 && pipe(release) == 0, "pipes");
  auto lock = new FileLock(path);
  pid_t child = fork(); check(child >= 0, "fork");
  if (child == 0) {
    close(ready[0]); close(release[1]); send_byte(ready[1]);
    bool done = receive_byte(release[0], 3000); _exit(done ? 0 : 2);
  }
  close(ready[1]); close(release[0]);
  bool live = receive_byte(ready[0], 1500);
  delete lock;
  bool released_while_child_alive = live && available(path);
  finish(child, release[1], live); close(ready[0]); close(release[1]);
  check(released_while_child_alive, "parent destructor must release while fork child retains FD");
}
static void child_destructor_preserves_parent(const std::string &path) {
  int ready[2], release[2]; check(pipe(ready) == 0 && pipe(release) == 0, "pipes");
  auto lock = new FileLock(path);
  pid_t child = fork(); check(child >= 0, "fork");
  if (child == 0) {
    close(ready[0]); close(release[1]); delete lock; send_byte(ready[1]);
    bool done = receive_byte(release[0], 3000); _exit(done ? 0 : 2);
  }
  close(ready[1]); close(release[0]);
  bool live = receive_byte(ready[0], 1500);
  bool exclusive = live && !available(path);
  delete lock;
  bool released = available(path);
  finish(child, release[1], live); close(ready[0]); close(release[1]);
  check(exclusive && released, "child destructor must not unlock acquiring parent");
}
static int exec_probe(const std::string &path) {
  struct stat target{}; if (stat(path.c_str(), &target) != 0) return 2;
  for (const auto &entry : std::filesystem::directory_iterator("/proc/self/fd")) {
    struct stat st{};
    if (stat(entry.path().c_str(), &st) == 0 && st.st_dev == target.st_dev && st.st_ino == target.st_ino) return 3;
  }
  return 0;
}
static void no_exec_leak(const std::string &path) {
  FileLock lock(path);
  pid_t child = fork(); check(child >= 0, "fork");
  if (child == 0) {
    execl("/proc/self/exe", "test_params_fork_lock", "exec-probe", path.c_str(), nullptr);
    _exit(127);
  }
  int status = 0; check(waitpid(child, &status, 0) == child, "reap exec");
  check(WIFEXITED(status) && WEXITSTATUS(status) == 0, "no lock descriptor inherited across exec");
  check(!available(path), "parent remains exclusive after child exec");
}
static void competing_writer(const std::string &path) {
  int ready[2]; check(pipe(ready) == 0, "pipe");
  auto lock = new FileLock(path);
  pid_t child = fork(); check(child >= 0, "fork");
  if (child == 0) {
    close(ready[0]);
    { FileLock competitor(path); send_byte(ready[1]); }
    _exit(0);
  }
  close(ready[1]);
  bool premature = receive_byte(ready[0], 150);
  delete lock;
  bool progressed = receive_byte(ready[0], 1500);
  if (!progressed) kill(child, SIGKILL);
  int status = 0; check(waitpid(child, &status, 0) == child, "reap competitor"); close(ready[0]);
  check(!premature && progressed && WIFEXITED(status) && WEXITSTATUS(status) == 0,
        "competitor excluded during parent scope and proceeds after owning unlock");
}
static void failures_and_eintr(const std::string &path) {
  int before = unlocks.load();
  fail_ex = EIO;
  { FileLock failed(path); }
  check(unlocks == before, "failed lock must not issue unlock");
  { FileLock failed(path + "/absent/lock"); }
  check(unlocks == before, "failed open must not issue unlock");
  fail_ex = EINTR;
  { FileLock retried(path); check(!available(path), "EINTR acquisition retries"); }
  check(available(path), "retried lock released");
}
static void params_semantics(const std::string &root) {
  Params params(root);
  check(!params.allKeys().empty(), "actual product registry is available");
  check(params.remove("LastManagerExitReason") == 0 || errno == ENOENT, "remove fixture value");
  std::string got;
  std::thread reader([&] { got = params.get("LastManagerExitReason", true); });
  std::this_thread::sleep_for(std::chrono::milliseconds(30));
  check(params.put("LastManagerExitReason", "blocking-read-write") == 0, "blocking put");
  reader.join(); check(got == "blocking-read-write", "actual blocking get/put");
  const std::vector<std::string> keys{"GitCommit", "GitBranch", "GitRemote", "Version"};
  std::vector<std::thread> writers;
  std::atomic<int> running{int(keys.size())};
  for (size_t k = 0; k < keys.size(); ++k) writers.emplace_back([&, k] {
    {
      Params queued(root);
      for (int n = 0; n < 30; ++n) queued.putNonBlocking(keys[k], std::string(4096, char('A' + k)) + std::to_string(n));
      // Actual Params destructor drains the nonblocking queue.
    }
    --running;
  });
  bool complete_reads = true;
  while (running > 0) {
    auto live_batch = params.readAll();
    for (size_t k = 0; k < keys.size(); ++k) {
      auto item = live_batch.find(keys[k]);
      if (item != live_batch.end()) {
        const auto &value = item->second;
        complete_reads &= (value.size() == 4097 || value.size() == 4098) &&
                          value.substr(0, 4096) == std::string(4096, char('A' + k));
      }
    }
  }
  for (auto &writer : writers) writer.join();
  check(complete_reads, "concurrent readAll never observes a partial atomic write");
  auto batch = params.readAll();
  for (size_t k = 0; k < keys.size(); ++k)
    check(batch.at(keys[k]) == std::string(4096, char('A' + k)) + "29", "queued multiwriter drain and batch visibility");
  check(params.putBool("IsOffroad", true) == 0 && params.getBool("IsOffroad"), "actual bool put/get");
  params.clearAll(ParamKeyFlag::CLEAR_ON_MANAGER_START);
  check(params.get("IsOffroad").empty(), "actual clearAll under lock");
}
int main(int argc, char **argv) {
  if (argc == 3 && std::string(argv[1]) == "exec-probe") return exec_probe(argv[2]);
  if (argc != 3) { std::cerr << "CASE ABS_PRIVATE_TEMP_DIRECTORY\n"; return 2; }
  std::string name = argv[1], root = argv[2];
  if (root.empty() || root[0] != '/') return 2;
  std::filesystem::create_directories(root);
  std::string lock = root + "/fixture.lock";
  try {
    if (name == "inherited_release") inherited_release(lock);
    else if (name == "child_destructor") child_destructor_preserves_parent(lock);
    else if (name == "exec") no_exec_leak(lock);
    else if (name == "competitor") competing_writer(lock);
    else if (name == "failures_eintr") failures_and_eintr(lock);
    else if (name == "params_semantics") params_semantics(root + "/params");
    else return 2;
    std::cout << "PASS " << name << '\n'; return 0;
  } catch (const std::exception &e) {
    std::cerr << "FAIL " << name << ": " << e.what() << '\n'; return 1;
  }
}
