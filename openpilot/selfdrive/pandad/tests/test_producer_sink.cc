// Compile with the real header/backend and existing host dependency libraries.
#include "selfdrive/pandad/producer_timing.h"
#include <cassert>
#include <cstdio>

int main() {
  std::string endpoint = "ipc:///tmp/pandad-timing-sink-" + std::to_string(getpid());
  void *context = zmq_ctx_new();
  assert(context);
  void *pull = zmq_socket(context, ZMQ_PULL);
  assert(pull);
  int linger = 0;
  assert(zmq_setsockopt(pull, ZMQ_LINGER, &linger, sizeof(linger)) == 0);
  assert(zmq_bind(pull, endpoint.c_str()) == 0);
  {
    pandad_timing::Recorder collector(true, endpoint.c_str());
    auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(3);
    while (!collector.is_ready() && std::chrono::steady_clock::now() < deadline)
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
    assert(collector.is_ready() && collector.policy_errors == 0);
    auto receive = [&] {
      std::array<char, 16384> data{};
      int count = -1;
      while (count < 0 && std::chrono::steady_clock::now() < deadline) {
        count = zmq_recv(pull, data.data(), data.size(), ZMQ_NOBLOCK);
        if (count < 0) std::this_thread::sleep_for(std::chrono::milliseconds(1));
      }
      assert(count > 1 && count < int(data.size()) && data[0] == 30);
      std::string error;
      auto message = json11::Json::parse(std::string(data.data() + 1, count - 1), error);
      assert(error.empty());
      return message;
    };
    auto started = receive();
    assert(started["msg"]["event"].string_value() == "pandad.producer_ready");
    assert(started["msg"]["reporter_policy"].int_value() == SCHED_OTHER);
    assert(started["msg"]["queue_capacity"].int_value() == 4);
    assert(started["msg"]["capture_default_enabled"].bool_value());
    assert(started["ctx"]["daemon"].string_value() == "pandad");
    pandad_timing::Pair row;
    row.gap = 29000000;
    row.current.can_count = 162;
    assert(collector.push(row));
    std::array<char, 16384> buffer{};
    int size = -1;
    while (size < 0 && std::chrono::steady_clock::now() < deadline) {
      size = zmq_recv(pull, buffer.data(), buffer.size(), ZMQ_NOBLOCK);
      if (size < 0) std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    assert(size > 1 && size < int(buffer.size()) && buffer[0] == 30);
    std::string error;
    auto record = json11::Json::parse(std::string(buffer.data() + 1, size - 1), error);
    assert(error.empty());
    assert(record["msg"]["event"].string_value() == "pandad.producer_gap");
    assert(record["msg"]["gap_ns"].number_value() == 29000000);
    assert(record["msg"]["frames"][1]["can_count"].number_value() == 162);
    assert(record["ctx"]["daemon"].string_value() == "pandad");
  }
  zmq_close(pull);
  zmq_ctx_term(context);
  std::remove(endpoint.substr(6).c_str());
}
