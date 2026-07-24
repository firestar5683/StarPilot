from pathlib import Path

CHESTNUT_VENDOR_ID = 0xADD1
CHESTNUT_PRODUCT_ID = 0x0001
USB_DEVICES_PATH = Path("/sys/bus/usb/devices")


def read_int(path: Path, base: int = 10) -> int:
  try:
    return int(path.read_text(), base)
  except (OSError, ValueError):
    return 0


def usb_devices() -> list[Path]:
  try:
    devices = (path for path in USB_DEVICES_PATH.glob("*") if (path / "idVendor").exists())
    return sorted(devices, key=lambda path: path.name)
  except OSError:
    return []


def chestnut_present() -> bool:
  return any(
    read_int(device / "idVendor", 16) == CHESTNUT_VENDOR_ID and
    read_int(device / "idProduct", 16) == CHESTNUT_PRODUCT_ID
    for device in usb_devices()
  )


def controller(device: Path) -> Path | None:
  try:
    return next((parent for parent in device.resolve().parents if parent.name.endswith(".ssusb")), None)
  except OSError:
    return None
