#include "selfdrive/pandad/panda_comms.h"

#include <libusb-1.0/libusb.h>

#include <stdexcept>

#include "common/swaglog.h"

namespace {
bool is_panda(const libusb_device_descriptor &desc) {
  return (desc.idVendor == 0x3801 || desc.idVendor == 0xbbaa) && desc.idProduct == 0xddcc;
}

unsigned int usb_timeout(unsigned int timeout) {
  return timeout == 0 ? 500 : timeout;
}

std::string usb_serial(libusb_device_handle *handle, uint8_t index) {
  unsigned char serial[26] = {};
  int count = libusb_get_string_descriptor_ascii(handle, index, serial, sizeof(serial));
  return count > 0 ? std::string(reinterpret_cast<char *>(serial), count) : std::string();
}
}

PandaUsbHandle::PandaUsbHandle(std::string serial) {
  if (libusb_init(&ctx) != 0) throw std::runtime_error("libusb initialization failed");
  libusb_device **devices = nullptr;
  ssize_t count = libusb_get_device_list(ctx, &devices);
  if (count >= 0) {
    for (ssize_t i = 0; i < count; ++i) {
      libusb_device_descriptor desc = {};
      if (libusb_get_device_descriptor(devices[i], &desc) != 0 || !is_panda(desc)) continue;
      libusb_device_handle *candidate = nullptr;
      if (libusb_open(devices[i], &candidate) != 0) continue;
      auto candidate_serial = usb_serial(candidate, desc.iSerialNumber);
      if (!candidate_serial.empty() && (serial.empty() || serial == candidate_serial)) {
        dev_handle = candidate;
        hw_serial = candidate_serial;
        break;
      }
      libusb_close(candidate);
    }
    libusb_free_device_list(devices, 1);
  }
  if (dev_handle != nullptr) {
    int err = 0;
    if (libusb_kernel_driver_active(dev_handle, 0) == 1) err = libusb_detach_kernel_driver(dev_handle, 0);
    if (err == 0) err = libusb_set_configuration(dev_handle, 1);
    if (err == 0) err = libusb_claim_interface(dev_handle, 0);
    if (err == 0) {
      claimed = true;
      return;
    }
  }
  cleanup();
  throw std::runtime_error("USB panda unavailable");
}

PandaUsbHandle::~PandaUsbHandle() {
  cleanup();
}

void PandaUsbHandle::cleanup() {
  std::lock_guard<std::recursive_mutex> guard(hw_lock);
  connected = false;
  if (dev_handle != nullptr) {
    if (claimed) libusb_release_interface(dev_handle, 0);
    libusb_close(dev_handle);
    dev_handle = nullptr;
    claimed = false;
  }
  if (ctx != nullptr) {
    libusb_exit(ctx);
    ctx = nullptr;
  }
}

std::vector<std::string> PandaUsbHandle::list() {
  std::vector<std::string> serials;
  libusb_context *context = nullptr;
  if (libusb_init(&context) != 0) return serials;
  libusb_device **devices = nullptr;
  ssize_t count = libusb_get_device_list(context, &devices);
  if (count >= 0) {
    for (ssize_t i = 0; i < count; ++i) {
      libusb_device_descriptor desc = {};
      if (libusb_get_device_descriptor(devices[i], &desc) != 0 || !is_panda(desc)) continue;
      libusb_device_handle *device = nullptr;
      if (libusb_open(devices[i], &device) != 0) continue;
      auto serial = usb_serial(device, desc.iSerialNumber);
      if (!serial.empty()) serials.push_back(serial);
      libusb_close(device);
    }
    libusb_free_device_list(devices, 1);
  }
  libusb_exit(context);
  return serials;
}

void PandaUsbHandle::handle_usb_issue(int err) {
  LOGE("USB panda transfer failed: %s", libusb_error_name(err));
  if (err == LIBUSB_ERROR_NO_DEVICE) connected = false;
  if (err != LIBUSB_ERROR_TIMEOUT) comms_healthy = false;
}

int PandaUsbHandle::control_write(uint8_t request, uint16_t param1, uint16_t param2, unsigned int timeout) {
  std::lock_guard<std::recursive_mutex> guard(hw_lock);
  if (!connected) return LIBUSB_ERROR_NO_DEVICE;
  int count = libusb_control_transfer(dev_handle, 0x40, request, param1, param2, nullptr, 0, usb_timeout(timeout));
  if (count < 0) {
    comms_healthy = false;
    handle_usb_issue(count);
  }
  return count;
}

int PandaUsbHandle::control_read(uint8_t request, uint16_t param1, uint16_t param2, unsigned char *data, uint16_t length, unsigned int timeout) {
  std::lock_guard<std::recursive_mutex> guard(hw_lock);
  if (!connected) return LIBUSB_ERROR_NO_DEVICE;
  int count = libusb_control_transfer(dev_handle, 0xc0, request, param1, param2, data, length, usb_timeout(timeout));
  if (count < 0) handle_usb_issue(count);
  return count;
}

int PandaUsbHandle::bulk_write(unsigned char endpoint, unsigned char *data, int length, unsigned int timeout) {
  std::lock_guard<std::recursive_mutex> guard(hw_lock);
  if (!connected) return LIBUSB_ERROR_NO_DEVICE;
  int transferred = 0;
  int err = libusb_bulk_transfer(dev_handle, endpoint, data, length, &transferred, usb_timeout(timeout));
  if (err != 0 || transferred != length) {
    comms_healthy = false;
    if (err == 0) err = LIBUSB_ERROR_IO;
    handle_usb_issue(err);
    return err;
  }
  return transferred;
}

int PandaUsbHandle::bulk_read(unsigned char endpoint, unsigned char *data, int length, unsigned int timeout) {
  std::lock_guard<std::recursive_mutex> guard(hw_lock);
  if (!connected) return LIBUSB_ERROR_NO_DEVICE;
  int transferred = 0;
  int err = libusb_bulk_transfer(dev_handle, endpoint, data, length, &transferred, timeout == 0 ? 5 : timeout);
  if (err < 0 && err != LIBUSB_ERROR_TIMEOUT) handle_usb_issue(err);
  return err == 0 || err == LIBUSB_ERROR_TIMEOUT ? transferred : err;
}
