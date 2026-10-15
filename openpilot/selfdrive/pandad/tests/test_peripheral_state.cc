// Compile the actual publisher and hwmon worker, replacing only external I/O.
#include "common/hardware/hw.h"
#include "common/hardware/comma/hardware.h"
#undef Hardware
#define Hardware HardwareComma
#include "selfdrive/pandad/pandad.cc"
#include "common/tests/native_test.h"

#include <condition_variable>
#include <mutex>

namespace {
std::string device;
std::atomic<unsigned> hwmon_reads{0};
std::thread::id publisher_thread;
std::atomic<uint32_t> input_voltage{12345}, input_current{812};
std::mutex sensor_mutex;
std::condition_variable sensor_changed;
bool block_sensor = false, sensor_waiting = false;
kj::Array<capnp::word> last_message;
unsigned publications = 0;
}

std::string wrapped_read_file(const std::string &) asm("__wrap__ZN4util9read_fileERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE");
std::string wrapped_read_file(const std::string &path) {
  if (path == "/sys/firmware/devicetree/base/model") return "comma " + device;
  CHECK(path == "/sys/class/hwmon/hwmon1/in1_input" || path == "/sys/class/hwmon/hwmon1/curr1_input");
  CHECK(std::this_thread::get_id() != publisher_thread);
  ++hwmon_reads;
  std::unique_lock lock(sensor_mutex);
  if (block_sensor) {
    sensor_waiting = true;
    sensor_changed.notify_all();
    sensor_changed.wait(lock, [] { return !block_sensor; });
  }
  return std::to_string(path == "/sys/class/hwmon/hwmon1/in1_input" ? input_voltage.load() : input_current.load()) + "\n";
}

int wrapped_send(PubMaster *, const char *, MessageBuilder &) asm("__wrap__ZN9PubMaster4sendEPKcR14MessageBuilder");
int wrapped_send(PubMaster *, const char *name, MessageBuilder &message) {
  CHECK(std::string(name) == "peripheralState");
  last_message = capnp::messageToFlatArray(message);
  ++publications;
  return 0;
}

class PowerHandle : public PandaCommsHandle {
public:
  health_t health{};
  bool fail_health = false;
  PowerHandle() { health.voltage_pkt = 300; health.current_pkt = 17; health.faults_pkt = 8; }
  int control_write(uint8_t, uint16_t, uint16_t, unsigned int) override { return 0; }
  int control_read(uint8_t request, uint16_t, uint16_t, unsigned char *data, uint16_t length, unsigned int) override {
    if (request == 0xd2 && length == sizeof(health)) {
      if (fail_health) return -1;
      std::memcpy(data, &health, length);
      return length;
    }
    if (request == 0xb2 && length == 2) { uint16_t fan = 1234; std::memcpy(data, &fan, length); return length; }
    return -1;
  }
  int bulk_write(unsigned char, unsigned char *, int, unsigned int) override { return 0; }
  int bulk_read(unsigned char, unsigned char *, int, unsigned int) override { return 0; }
  void cleanup() override {}
};
class PowerPanda : public Panda {
public:
  PowerPanda(std::unique_ptr<PowerHandle> comms, cereal::PandaState::PandaType type) : Panda(std::move(comms), type) {}
};

void test_power() {
  publisher_thread = std::this_thread::get_id();
  using Type = cereal::PandaState::PandaType;
  auto handle = std::make_unique<PowerHandle>();
  auto *raw = handle.get();
  const auto type = device == "tici" ? Type::DOS : device == "tizi" ? Type::TRES : Type::CUATRO;
  PowerPanda panda(std::move(handle), type);
  PubMaster publisher({});
  auto check = [&](uint32_t voltage, uint32_t current, bool valid = true) {
    send_peripheral_state(&panda, &publisher);
    capnp::FlatArrayMessageReader reader(last_message.asPtr());
    auto event = reader.getRoot<cereal::Event>();
    CHECK(event.getValid() == valid && event.isPeripheralState());
    auto state = event.getPeripheralState();
    CHECK(state.getVoltage() == voltage && state.getCurrent() == current);
    CHECK(state.getPandaType() == type && state.getFanSpeedRpm() == 1234);
    CHECK(raw->health.voltage_pkt == 300 && raw->health.current_pkt == 17 && raw->health.faults_pkt == 8);
  };
  check(300, 17);  // No sample yet: retain the current Panda fallback.
  if (device != "tici") {
    hwmon_thread();  // Returns before touching absent INA sensors on 3x/4.
    CHECK(hwmon_reads == 0 && hwmon_power == 0);
    check(300, 17);
    return;
  }
  std::thread worker(hwmon_thread);
  struct Join {
    std::thread &worker;
    ~Join() {
      { std::lock_guard lock(sensor_mutex); block_sensor = false; }
      sensor_changed.notify_all(); do_exit = true; worker.join();
    }
  } join{worker};
  for (int i = 0; i < 2000 && hwmon_power == 0; ++i) std::this_thread::sleep_for(std::chrono::milliseconds(1));
  CHECK(hwmon_power != 0 && hwmon_reads >= 2);
  check(12345, 812);
  {
    std::unique_lock lock(sensor_mutex); block_sensor = true;
    CHECK(sensor_changed.wait_for(lock, std::chrono::seconds(3), [] { return sensor_waiting; }));
  }
  // A blocked background sensor cannot hold the actual peripheral publisher.
  check(12345, 812);
  // Verify paired publication and Dom's zero/zero fallback without voltage clamps.
  for (auto pair : {std::pair{0U, 0U}, {2300U, 15U}, {0U, 50U}, {14000U, 0U}}) {
    hwmon_power.store((uint64_t(pair.first) << 32) | pair.second);
    check(pair.first || pair.second ? pair.first : 300, pair.first || pair.second ? pair.second : 17);
  }
  raw->comms_healthy = false;
  check(14000, 0, false);
  raw->comms_healthy = true;
  raw->fail_health = true;
  auto before = publications;
  send_peripheral_state(&panda, &publisher);
  CHECK(publications == before);
}

int main(int argc, char **argv) {
  CHECK(argc == 2);
  device = argv[1];
  CHECK(device == "tici" || device == "tizi" || device == "mici");
  return run_native_test(test_power);
}
