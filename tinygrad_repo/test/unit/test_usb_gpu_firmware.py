import pytest

from tinygrad.runtime.support import system


class FakeUSB:
  def __init__(self, product: str, is_custom: bool):
    self.product, self.is_custom = product, is_custom


def patch_usb_dependencies(monkeypatch, usb):
  calls = []
  monkeypatch.setattr(system.System, "flock_acquire", lambda _: object())
  monkeypatch.setattr(system, "USB3", lambda *args, **kwargs: calls.append((args, kwargs)) or usb)
  return calls


def test_usb_gpu_rejects_legacy_bridge_firmware(monkeypatch):
  calls = patch_usb_dependencies(monkeypatch, FakeUSB("USB 3.2 PCIe TinyEnclosure", False))

  with pytest.raises(RuntimeError, match="unsupported legacy USB GPU firmware"):
    system.USBPCIDevice("AM", object(), "usb:3-6")

  assert calls[0][1] == {"use_bot": True}


def test_usb_gpu_accepts_custom_bridge_firmware(monkeypatch):
  usb = FakeUSB("custom ASM2464PD", True)
  calls = patch_usb_dependencies(monkeypatch, usb)
  controller = object()
  monkeypatch.setattr(system, "CustomASM24Controller", lambda candidate: controller if candidate is usb else None)
  monkeypatch.setattr(system.System, "pci_setup_usb_bars", lambda *args, **kwargs: {2: (0, 1)})

  device = system.USBPCIDevice("AM", object(), "usb:3-6")

  assert calls[0][1] == {"use_bot": True}
  assert device.usb is controller
