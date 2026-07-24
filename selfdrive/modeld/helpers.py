import io
import json
import os
import pickle
import shutil
import struct
import tempfile
from pathlib import Path

from tinygrad.device import Device
from openpilot.system.hardware.usb import chestnut_present

MODELS_DIR = Path(__file__).resolve().parent / "models"
TG_INPUT_DEVICES_PATH = MODELS_DIR / "tg_input_devices.json"
USBGPU_VID = 0xADD1
USBGPU_PID = 0x0001


def _default_tinygrad_backend() -> str:
  env_dev = os.getenv("DEV", "").strip()
  if env_dev:
    default_target = env_dev.split(";", 1)[0]
    return default_target.split(":", 1)[0].split("+", 1)[-1] or default_target

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


def modeld_pkl_path(usbgpu: bool) -> Path:
  prefix = "big_" if usbgpu else ""
  return MODELS_DIR / f"{prefix}driving_tinygrad.pkl"


def usbgpu_present() -> bool:
  return chestnut_present()


def tinygrad_dev_config(usbgpu: bool, tici: bool) -> str:
  default = "QCOM" if tici else ("CPU:LLVM" if usbgpu else "LLVM")
  return f"{default};USB+AMD:LLVM" if usbgpu else default


def dump_oob(obj, output) -> None:
  """Pickle large buffers out-of-band so model weights are never duplicated in RAM."""
  with tempfile.TemporaryFile(dir=".") as buffers:
    def buffer_callback(pickle_buffer: pickle.PickleBuffer):
      view = pickle_buffer.raw()
      buffers.write(struct.pack("<q", view.nbytes))
      buffers.write(view)
      pickle_buffer.release()

    opcodes = io.BytesIO()
    pickle.Pickler(opcodes, protocol=5, buffer_callback=buffer_callback).dump(obj)
    opcode_data = opcodes.getvalue()
    output.write(struct.pack("<q", len(opcode_data)))
    output.write(opcode_data)
    buffers.seek(0)
    shutil.copyfileobj(buffers, output)


def load_oob(source):
  header = source.read(8)
  if len(header) != 8:
    raise EOFError("truncated out-of-band pickle header")
  opcodes = source.read(struct.unpack("<q", header)[0])

  def buffers():
    previous = None
    while header := source.read(8):
      if len(header) != 8:
        raise EOFError("truncated out-of-band buffer header")
      if previous is not None:
        previous.release()
      buffer = bytearray(struct.unpack("<q", header)[0])
      if source.readinto(buffer) != len(buffer):
        raise EOFError("truncated out-of-band buffer")
      previous = pickle.PickleBuffer(buffer)
      yield previous

  return pickle.load(io.BytesIO(opcodes), buffers=buffers())
