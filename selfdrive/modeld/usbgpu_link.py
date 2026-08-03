import time
from pathlib import Path

from openpilot.common.swaglog import cloudlog
from openpilot.system.hardware.usb import CHESTNUT_PRODUCT_ID, CHESTNUT_VENDOR_IDS, controller, read_int, usb_devices

STABLE_SECONDS = 2.0
STABLE_THRESHOLD = 5.0


def _chestnut_portli() -> Path | None:
  for device in usb_devices():
    if read_int(device / "idVendor", 16) not in CHESTNUT_VENDOR_IDS or \
       read_int(device / "idProduct", 16) != CHESTNUT_PRODUCT_ID:
      continue
    usb_controller = controller(device)
    if usb_controller is not None and (usb_controller / "portli").exists():
      return usb_controller / "portli"
  return None


def wait_usbgpu_link(timeout: float = 30.0) -> None:
  portli = _chestnut_portli()
  if portli is None:
    return

  start_time = time.monotonic()
  while time.monotonic() - start_time < timeout:
    start_errors = read_int(portli, 0)
    time.sleep(STABLE_SECONDS)
    error_rate = (read_int(portli, 0) - start_errors) / STABLE_SECONDS
    if error_rate <= STABLE_THRESHOLD:
      return
    cloudlog.warning(f"usbgpu link not stable: {error_rate:.0f} errors/s")
  cloudlog.error("usbgpu link never stabilized")
