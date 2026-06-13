import json
import os
from pathlib import Path

from tinygrad.device import Device

MODELS_DIR = Path(__file__).resolve().parent / "models"
TG_INPUT_DEVICES_PATH = MODELS_DIR / "tg_input_devices.json"
USBGPU_VID = 0xADD1
USBGPU_PID = 0x0001


def _default_tinygrad_backend() -> str:
  env_dev = os.getenv("DEV", "").strip()
  if env_dev:
    return env_dev.split(":", 1)[0].split("+", 1)[-1] or env_dev

  try:
    default = Device.DEFAULT
  except Exception:
    default = ""

  if isinstance(default, str) and default:
    return default.split(":", 1)[0].split("+", 1)[-1] or default
  return "QCOM" if Path("/dev/kgsl-3d0").exists() else "CPU"


def _load_tg_devices() -> dict:
  if not TG_INPUT_DEVICES_PATH.is_file():
    return {}
  with open(TG_INPUT_DEVICES_PATH) as f:
    return json.load(f)


def _fallback_tg_devices(process_name: str, usbgpu: bool) -> dict[str, str]:
  backend = _default_tinygrad_backend()
  if process_name == "selfdrive.modeld.dmonitoringmodeld":
    return {"DEV": backend}

  queue_dev = backend
  if usbgpu:
    try:
      available = {name.split(":", 1)[0] for name in Device.get_available_devices()}
    except Exception:
      available = set()
    if "AMD" in available:
      queue_dev = "AMD"
  return {"WARP_DEV": backend, "QUEUE_DEV": queue_dev}


def get_tg_input_devices(process_name: str, usbgpu: bool) -> dict[str, str]:
  tg_devices = _load_tg_devices()
  process_devices = tg_devices.get(process_name, {})
  profile = "usbgpu" if usbgpu else "default"
  if profile in process_devices:
    return process_devices[profile]
  return _fallback_tg_devices(process_name, usbgpu)


def modeld_pkl_path(usbgpu: bool):
  prefix = "big_" if usbgpu else ""
  return MODELS_DIR / f"{prefix}driving_tinygrad.pkl"


def usbgpu_present() -> bool:
  for d in Path("/sys/bus/usb/devices").glob("*"):
    try:
      if int((d / "idVendor").read_text(), 16) == USBGPU_VID and \
          int((d / "idProduct").read_text(), 16) == USBGPU_PID:
        return True
    except Exception:
      pass
  return False
