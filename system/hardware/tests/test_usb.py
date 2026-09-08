from cereal import log
from openpilot.system.hardware import usb


def test_chestnut_present(tmp_path, monkeypatch):
  monkeypatch.setattr(usb, "USB_DEVICES_PATH", tmp_path)
  device = tmp_path / "1-1"
  device.mkdir()
  (device / "idVendor").write_text("add1\n")
  (device / "idProduct").write_text("0001\n")

  assert usb.chestnut_present()


def test_chestnut_present_with_comma_vendor_id(tmp_path, monkeypatch):
  monkeypatch.setattr(usb, "USB_DEVICES_PATH", tmp_path)
  device = tmp_path / "1-1"
  device.mkdir()
  (device / "idVendor").write_text("3801\n")
  (device / "idProduct").write_text("0001\n")

  assert usb.read_int(device / "idVendor", 16) in usb.CHESTNUT_VENDOR_IDS
  assert usb.usb_devices() == [device]
  assert usb.chestnut_present()


def test_chestnut_usb_ids_include_runtime_and_bootloader():
  assert usb.is_chestnut_usb_id(0x3801, 0x0001)
  assert usb.is_chestnut_usb_id(0xADD1, 0x0001)
  assert not usb.is_chestnut_usb_id(0x174C, 0x2464)
  assert usb.is_chestnut_usb_id(0x174C, 0x2464, include_bootloader=True)


def test_chestnut_absent_for_other_usb_device(tmp_path, monkeypatch):
  monkeypatch.setattr(usb, "USB_DEVICES_PATH", tmp_path)
  device = tmp_path / "1-1"
  device.mkdir()
  (device / "idVendor").write_text("18d1\n")
  (device / "idProduct").write_text("4ee7\n")

  assert not usb.chestnut_present()


def test_get_usb_topology(tmp_path, monkeypatch):
  monkeypatch.setattr(usb, "USB_DEVICES_PATH", tmp_path)
  (tmp_path / "1-0:1.0").mkdir()
  (tmp_path / "usb1").mkdir()

  assert usb.get_usb_topology() == {"1-0:1.0", "usb1"}


def test_get_usb_state(tmp_path, monkeypatch):
  devices_path = tmp_path / "devices"
  devices_path.mkdir()
  device = devices_path / "4-3"
  device.mkdir()
  values = {
    "busnum": "4\n",
    "devnum": "2\n",
    "idVendor": "3801\n",
    "idProduct": "0001\n",
    "speed": "5000\n",
    "manufacturer": "tiny\n",
    "product": "custom ed4e39b7-CLEAN\n",
  }
  for name, value in values.items():
    (device / name).write_text(value)

  ctrl = tmp_path / usb.PRIMARY_USB_CONTROLLER
  ctrl.mkdir()
  (ctrl / "portli").write_text("0x12345\n")
  orientation = tmp_path / "typec_cc_orientation"
  orientation.write_text("2\n")

  monkeypatch.setattr(usb, "USB_DEVICES_PATH", devices_path)
  monkeypatch.setattr(usb, "TYPEC_CC_ORIENTATION_PATH", orientation)
  monkeypatch.setattr(usb, "controller", lambda _: ctrl)

  assert usb.get_usb_state() == [{
    "busnum": 4,
    "devnum": 2,
    "vendorId": 0x3801,
    "productId": 0x0001,
    "speedMbps": 5000,
    "manufacturer": "tiny",
    "product": "custom ed4e39b7-CLEAN",
    "linkErrorCount": 0x2345,
    "usb3Lane": "b",
  }]


def test_set_usb_state():
  msg = log.DeviceState.new_message()
  devices = [{
    "busnum": 4,
    "devnum": 2,
    "vendorId": 0x3801,
    "productId": 0x0001,
    "speedMbps": 5000,
    "manufacturer": "tiny",
    "product": "custom ed4e39b7-CLEAN",
    "linkErrorCount": 7,
    "usb3Lane": "a",
  }]

  usb.set_usb_state(msg, devices)

  assert msg.chestnutPresent
  assert len(msg.usbState.devices) == 1
  assert msg.usbState.devices[0].speedMbps == 5000
  assert msg.usbState.devices[0].linkErrorCount == 7
  assert msg.usbState.devices[0].usb3Lane == "a"
