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


def test_chestnut_absent_for_other_usb_device(tmp_path, monkeypatch):
  monkeypatch.setattr(usb, "USB_DEVICES_PATH", tmp_path)
  device = tmp_path / "1-1"
  device.mkdir()
  (device / "idVendor").write_text("18d1\n")
  (device / "idProduct").write_text("4ee7\n")

  assert not usb.chestnut_present()
