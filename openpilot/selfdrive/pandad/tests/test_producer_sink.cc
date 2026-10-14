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
    for (unsigned f = 0; f < 2; ++f) {
      auto &holders = (f == 0 ? row.before : row.current).holders;
      holders.wait_start = 1000000 + f * 1000000;
      holders.acquired = holders.wait_start + 10000;
      holders.overwritten = 6 + f;
      holders.omitted = 12 + f;
      holders.invalid_clocks = 3 + f;
      holders.count = spi_holder_timing::MATCHES;
      for (unsigned i = 0; i < holders.count; ++i) {
        auto &h = holders.rows[i];
        h.sequence = 7 + f * 4 + i;
        h.thread = 4242 + i;
        h.role = 1 + i % 2;
        h.endpoint = i % 2 ? 0x81 : 0;
        h.request = i % 2 ? 0 : 0xd8;
        h.tx = 8 + i;
        h.rx = 64 + i;
        std::snprintf(h.serial, sizeof(h.serial), "%032u", f * 4 + i + 1);
        h.acquired = holders.wait_start + i * 1000;
        h.released = h.acquired + 500;
        h.cpu = 100 + i;
        h.ioctl_wall = 200 + i;
        h.ioctl_cpu = 50 + i;
        h.ack_wall = 300 + i;
        h.ack_cpu = 75 + i;
      }
    }
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
    for (unsigned f = 0; f < 2; ++f) {
      const auto &expected = (f == 0 ? row.before : row.current).holders;
      const auto &frame = record["msg"]["frames"][f];
      const auto &wait = frame["spi_holder_wait"].array_items();
      assert(wait.size() == 5);
      assert(wait[0].number_value() == expected.wait_start);
      assert(wait[1].number_value() == expected.acquired);
      assert(wait[2].number_value() == expected.overwritten);
      assert(wait[3].number_value() == expected.omitted);
      assert(wait[4].number_value() == expected.invalid_clocks);
      const auto &holders = frame["spi_holders"].array_items();
      assert(holders.size() == spi_holder_timing::MATCHES);
      for (unsigned i = 0; i < holders.size(); ++i) {
        const auto &h = expected.rows[i];
        const auto &fields = holders[i].array_items();
        assert(fields.size() == 15);
        assert(fields[0].number_value() == h.sequence);
        assert(fields[1].number_value() == h.thread);
        assert(fields[2].number_value() == h.role);
        assert(fields[3].number_value() == h.endpoint);
        assert(fields[4].number_value() == h.request);
        assert(fields[5].number_value() == h.tx);
        assert(fields[6].number_value() == h.rx);
        assert(fields[7].string_value() == h.serial);
        assert(fields[8].number_value() == h.acquired);
        assert(fields[9].number_value() == h.released);
        assert(fields[10].number_value() == h.cpu);
        assert(fields[11].number_value() == h.ioctl_wall);
        assert(fields[12].number_value() == h.ioctl_cpu);
        assert(fields[13].number_value() == h.ack_wall);
        assert(fields[14].number_value() == h.ack_cpu);
      }
    }
  }
  zmq_close(pull);
  zmq_ctx_term(context);
  std::remove(endpoint.substr(6).c_str());
}
