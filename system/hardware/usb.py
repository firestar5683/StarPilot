import os
from pathlib import Path

CHESTNUT_VENDOR_ID = 0xADD1
CHESTNUT_VENDOR_IDS = (CHESTNUT_VENDOR_ID, 0x3801)
CHESTNUT_PRODUCT_ID = 0x0001
CHESTNUT_USB_IDS = tuple((vendor_id, CHESTNUT_PRODUCT_ID) for vendor_id in CHESTNUT_VENDOR_IDS)
CHESTNUT_FW_VERSION = "ed4e39b7"
CHESTNUT_ROM_USB_IDS = ((0x174C, 0x2464), (0x174C, 0x2463))
CHESTNUT_USB_PRODUCT = f"custom {CHESTNUT_FW_VERSION}-CLEAN"
USB_DEVICES_PATH = Path("/sys/bus/usb/devices")
TYPEC_CC_ORIENTATION_PATH = Path("/sys/class/power_supply/usb/typec_cc_orientation")
PRIMARY_USB_CONTROLLER = "a600000.ssusb"


def is_chestnut_usb_id(vendor_id: int, product_id: int, include_bootloader: bool = False) -> bool:
  ids = CHESTNUT_USB_IDS + CHESTNUT_ROM_USB_IDS if include_bootloader else CHESTNUT_USB_IDS
  return (vendor_id, product_id) in ids


def get_usb_topology() -> set[str]:
  try:
    return set(os.listdir(USB_DEVICES_PATH))
  except OSError:
    return set()


def read(path: Path) -> str | None:
  try:
    return path.read_text().strip()
  except OSError:
    return None


def read_int(path: Path, base: int = 10) -> int:
  try:
    return int(path.read_text(), base)
  except (OSError, ValueError, TypeError):
    return 0


def read_text(path: Path) -> str:
  return read(path) or ""


def usb_devices() -> list[Path]:
  try:
    devices = (path for path in USB_DEVICES_PATH.glob("*") if (path / "idVendor").exists())
    return sorted(devices, key=lambda path: path.name)
  except OSError:
    return []


def chestnut_present() -> bool:
  return any(
    is_chestnut_usb_id(read_int(device / "idVendor", 16), read_int(device / "idProduct", 16))
    for device in usb_devices()
  )


def chestnut_firmware_ready() -> bool:
  return any(
    is_chestnut_usb_id(read_int(device / "idVendor", 16), read_int(device / "idProduct", 16)) and
    read_text(device / "product") == CHESTNUT_USB_PRODUCT
    for device in usb_devices()
  )


def controller(device: Path) -> Path | None:
  try:
    return next((parent for parent in device.resolve().parents if parent.name.endswith(".ssusb")), None)
  except OSError:
    return None


def get_usb_state() -> list[dict]:
  devices = []
  typec_orientation = read_int(TYPEC_CC_ORIENTATION_PATH)
  for device in usb_devices():
    ctrl = controller(device)
    devices.append({
      "busnum": read_int(device / "busnum"),
      "devnum": read_int(device / "devnum"),
      "vendorId": read_int(device / "idVendor", 16),
      "productId": read_int(device / "idProduct", 16),
      "speedMbps": read_int(device / "speed"),
      "manufacturer": read(device / "manufacturer") or "",
      "product": read(device / "product") or "",
      "linkErrorCount": read_int(ctrl / "portli", 0) & 0xFFFF if ctrl is not None else 0,
      "usb3Lane": {1: "a", 2: "b"}.get(typec_orientation, "unknown")
                  if ctrl is not None and ctrl.name == PRIMARY_USB_CONTROLLER else "unknown",
    })
  return devices


def set_usb_state(device_state, devices: list[dict]) -> None:
  entries = device_state.usbState.init("devices", len(devices))

  chestnut_found = False
  for entry, device in zip(entries, devices, strict=True):
    entry.busnum = device["busnum"]
    entry.devnum = device["devnum"]
    entry.vendorId = device["vendorId"]
    entry.productId = device["productId"]
    entry.speedMbps = device["speedMbps"]
    entry.manufacturer = device["manufacturer"]
    entry.product = device["product"]
    entry.linkErrorCount = device["linkErrorCount"]
    entry.usb3Lane = device.get("usb3Lane", "unknown")

    if is_chestnut_usb_id(entry.vendorId, entry.productId):
      chestnut_found = True

  device_state.chestnutPresent = chestnut_found
