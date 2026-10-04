#include <libusb-1.0/libusb.h>

#include <algorithm>
#include <array>
#include <cassert>
#include <cstring>
#include <exception>

#include "selfdrive/pandad/panda_comms.h"

namespace {
struct Device {
  uint16_t vendor;
  uint16_t product;
  const char *serial;
  bool accessible = true;
};
std::array<Device, 4> devices;
std::array<libusb_device *, 5> inventory;
int closes, exits, releases, claim_error, configuration_error, transfer_error, transferred;
unsigned int last_timeout;
uint8_t last_endpoint, last_request, last_request_type;
uint16_t last_value, last_index;

size_t device_index(const void *device) {
  return reinterpret_cast<uintptr_t>(device) - 1;
}

void reset() {
  devices = {{{0x3801, 0xddcc, "first"}, {0xbbaa, 0xddcc, "second"},
              {0x3801, 0xddee, "bootloader"}, {0x1234, 0xddcc, "other"}}};
  for (size_t i = 0; i < devices.size(); ++i) inventory[i] = reinterpret_cast<libusb_device *>(i + 1);
  inventory.back() = nullptr;
  closes = exits = releases = claim_error = configuration_error = transfer_error = transferred = 0;
  last_timeout = last_endpoint = last_request = last_request_type = last_value = last_index = 0;
}
}

extern "C" {
int LIBUSB_CALL libusb_init(libusb_context **context) {
  *context = reinterpret_cast<libusb_context *>(1);
  return 0;
}
void LIBUSB_CALL libusb_exit(libusb_context *) { ++exits; }
ssize_t LIBUSB_CALL libusb_get_device_list(libusb_context *, libusb_device ***list) {
  *list = inventory.data();
  return devices.size();
}
void LIBUSB_CALL libusb_free_device_list(libusb_device **, int) {}
int LIBUSB_CALL libusb_get_device_descriptor(libusb_device *device, libusb_device_descriptor *desc) {
  *desc = {};
  const auto &entry = devices.at(device_index(device));
  desc->idVendor = entry.vendor;
  desc->idProduct = entry.product;
  desc->iSerialNumber = 1;
  return 0;
}
int LIBUSB_CALL libusb_open(libusb_device *device, libusb_device_handle **handle) {
  if (!devices.at(device_index(device)).accessible) return LIBUSB_ERROR_ACCESS;
  *handle = reinterpret_cast<libusb_device_handle *>(device);
  return 0;
}
void LIBUSB_CALL libusb_close(libusb_device_handle *) { ++closes; }
int LIBUSB_CALL libusb_get_string_descriptor_ascii(libusb_device_handle *handle, uint8_t, unsigned char *data, int length) {
  const char *serial = devices.at(device_index(handle)).serial;
  int count = std::min(length, static_cast<int>(strlen(serial)));
  memcpy(data, serial, count);
  return count;
}
int LIBUSB_CALL libusb_kernel_driver_active(libusb_device_handle *, int) { return 1; }
int LIBUSB_CALL libusb_detach_kernel_driver(libusb_device_handle *, int) { return 0; }
int LIBUSB_CALL libusb_set_configuration(libusb_device_handle *, int) { return configuration_error; }
int LIBUSB_CALL libusb_claim_interface(libusb_device_handle *, int) { return claim_error; }
int LIBUSB_CALL libusb_release_interface(libusb_device_handle *, int) { ++releases; return 0; }
const char *LIBUSB_CALL libusb_error_name(int) { return "mock error"; }
int LIBUSB_CALL libusb_control_transfer(libusb_device_handle *, uint8_t type, uint8_t request,
                                        uint16_t value, uint16_t index, unsigned char *data,
                                        uint16_t length, unsigned int timeout) {
  last_request_type = type;
  last_request = request;
  last_value = value;
  last_index = index;
  last_timeout = timeout;
  if (transfer_error) return transfer_error;
  if (data) memset(data, 0x5a, length);
  return length;
}
int LIBUSB_CALL libusb_bulk_transfer(libusb_device_handle *, unsigned char endpoint, unsigned char *data,
                                    int length, int *count, unsigned int timeout) {
  last_endpoint = endpoint;
  last_timeout = timeout;
  *count = std::min(length, transferred);
  if (endpoint & 0x80) memset(data, 0x7b, *count);
  return transfer_error;
}
}

int main() {
  reset();
  int spi_opens = 0, usb_opens = 0;
  auto spi = [&](const std::string &serial) {
    ++spi_opens;
    return std::make_unique<PandaUsbHandle>(serial);
  };
  auto usb = [&](const std::string &serial) {
    ++usb_opens;
    return std::make_unique<PandaUsbHandle>(serial);
  };
  {
    auto handle = open_panda_handle("second", spi, usb);
    assert(handle->hw_serial == "second" && spi_opens == 1 && usb_opens == 0);
  }
  {
    auto unavailable_spi = [&](const std::string &) -> std::unique_ptr<PandaCommsHandle> {
      ++spi_opens;
      throw std::runtime_error("SPI unavailable");
    };
    auto handle = open_panda_handle("second", unavailable_spi, usb);
    assert(handle->hw_serial == "second" && spi_opens == 2 && usb_opens == 1);
  }
  reset();
  assert((PandaUsbHandle::list() == std::vector<std::string>{"first", "second"}));
  assert(closes == 2 && exits == 1);

  reset();
  devices[0].accessible = false;
  assert((PandaUsbHandle::list() == std::vector<std::string>{"second"}));
  {
    PandaUsbHandle handle("second");
    assert(handle.hw_serial == "second");
  }
  assert(releases == 1);

  reset();
  {
    PandaUsbHandle handle("second");
    assert(handle.hw_serial == "second" && closes == 1);
    unsigned char data[8] = {};
    assert(handle.control_read(0xdd, 12, 34, data, sizeof(data)) == sizeof(data));
    assert(last_timeout == 500 && last_request_type == 0xc0 && last_request == 0xdd);
    assert(last_value == 12 && last_index == 34 && data[0] == 0x5a);
    assert(handle.control_write(0xdc, 56, 78, 7) == 0);
    assert(last_timeout == 7 && last_request_type == 0x40 && last_request == 0xdc);
    assert(last_value == 56 && last_index == 78);
    transferred = 3;
    transfer_error = LIBUSB_ERROR_TIMEOUT;
    assert(handle.bulk_read(0x81, data, sizeof(data)) == 3);
    assert(last_timeout == 5 && last_endpoint == 0x81 && data[0] == 0x7b);
    assert(handle.connected && handle.comms_healthy);
    assert(handle.bulk_write(3, data, sizeof(data), 5) == LIBUSB_ERROR_TIMEOUT);
    assert(!handle.comms_healthy);
    assert(last_endpoint == 3 && last_timeout == 5);
    transfer_error = 0;
    assert(handle.bulk_write(3, data, sizeof(data), 5) == LIBUSB_ERROR_IO);
    transferred = sizeof(data);
    assert(handle.bulk_write(3, data, sizeof(data), 5) == sizeof(data));
    transfer_error = LIBUSB_ERROR_IO;
    assert(handle.bulk_write(3, data, sizeof(data), 5) == LIBUSB_ERROR_IO);
    assert(!handle.comms_healthy);
    transfer_error = LIBUSB_ERROR_NO_DEVICE;
    assert(handle.control_read(0xc1, 0, 0, data, 1) == LIBUSB_ERROR_NO_DEVICE);
    assert(!handle.connected);
    handle.cleanup();
    handle.cleanup();
  }
  assert(closes == 2 && releases == 1 && exits == 1);

  reset();
  {
    PandaUsbHandle handle("first");
    transfer_error = LIBUSB_ERROR_TIMEOUT;
    assert(handle.control_write(0xf3, 1, 0) == LIBUSB_ERROR_TIMEOUT);
    assert(handle.connected && !handle.comms_healthy);
    assert(last_timeout == 500 && last_request_type == 0x40);
  }

  for (bool fail_configuration : {false, true}) {
    reset();
    if (fail_configuration) configuration_error = LIBUSB_ERROR_BUSY;
    else claim_error = LIBUSB_ERROR_BUSY;
    bool failed = false;
    try { PandaUsbHandle handle("first"); } catch (const std::exception &) { failed = true; }
    assert(failed && closes == 1 && exits == 1 && releases == 0);
  }

  reset();
  bool failed = false;
  try { PandaUsbHandle handle("missing"); } catch (const std::exception &) { failed = true; }
  assert(failed && closes == 2 && exits == 1 && releases == 0);
}
