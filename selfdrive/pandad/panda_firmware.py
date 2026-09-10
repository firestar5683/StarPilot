"""Shared firmware selection for startup and the parked manual Panda updater."""

import os

from cereal import car
from openpilot.common.basedir import BASEDIR
from openpilot.common.params import Params, UnknownKeyName
from openpilot.common.swaglog import cloudlog


FW_PATH = os.path.join(BASEDIR, "panda", "board", "obj")

TESLA_CAN_WAKE_PLATFORMS = {"TESLA_MODEL_3", "TESLA_MODEL_Y", "TESLA_MODEL_X"}


def supports_tesla_can_wake(params: Params) -> bool:
  # Current CarParams take precedence; historical caches must never override
  # a different vehicle or a corrupt current record. Selected settings veto
  # stale persisted CarParams when the user changes vehicle while parked.
  try:
    selected_make = params.get("CarMake") or ""
    selected_model = params.get("CarModel") or ""
    if isinstance(selected_make, bytes):
      selected_make = selected_make.decode("utf-8")
    if isinstance(selected_model, bytes):
      selected_model = selected_model.decode("utf-8")
    if selected_make and selected_make.strip().lower() != "tesla":
      return False
    cp_bytes = params.get("CarParams")
    if cp_bytes is None:
      cp_bytes = params.get("CarParamsPersistent")
    if not cp_bytes:
      return False
    with car.CarParams.from_bytes(cp_bytes) as CP:
      return (CP.brand == "tesla" and CP.carFingerprint in TESLA_CAN_WAKE_PLATFORMS and
              (not selected_model or selected_model == CP.carFingerprint))
  except Exception:
    return False


def get_tesla_wake_on_can(params: Params) -> bool:
  try:
    return params.get_bool("TeslaWakeOnCAN") and supports_tesla_can_wake(params)
  except UnknownKeyName:
    return False


def get_selected_firmware_name(app_fn: str, remote_start: bool, hkg_remote_start: bool, ignore_ignition_line: bool,
                               tesla_wake: bool = False) -> str:
  if not remote_start and not hkg_remote_start and not ignore_ignition_line and not tesla_wake:
    return app_fn

  name_parts = ["panda_h7" if app_fn == "panda_h7.bin.signed" else "panda"]
  if tesla_wake:
    name_parts.extend(["tesla", "wake"])
  elif hkg_remote_start:
    name_parts.extend(["hkg", "remote"])
  elif remote_start:
    name_parts.append("remote")
  if ignore_ignition_line:
    name_parts.append("can_ignition_only")
  return "_".join(name_parts) + ".bin.signed"


def get_firmware_path(fw_path: str, app_fn: str, remote_start: bool, hkg_remote_start: bool, ignore_ignition_line: bool,
                      tesla_wake: bool = False) -> str:
  selected_fn = get_selected_firmware_name(app_fn, remote_start, hkg_remote_start, ignore_ignition_line, tesla_wake)
  selected_path = os.path.join(fw_path, selected_fn)
  if selected_fn != app_fn and not os.path.isfile(selected_path):
    if tesla_wake:
      raise FileNotFoundError(f"Tesla wake firmware not found: {selected_path}")
    cloudlog.warning(f"Selected panda firmware not found: {selected_path}, falling back to default")
    return os.path.join(fw_path, app_fn)
  return selected_path


def validate_tesla_can_wake_firmware(params: Params, enabled: bool) -> None:
  """Check the requested image before saving; never access or flash a Panda.

  The settings process does not own the connected Panda. Require both supported
  MCU images so the subsequent updater can select the attached board safely.
  """
  remote_start = params.get_bool("RemoteStartBootsComma")
  hkg_remote_start = params.get_bool("HKGRemoteStartBootsComma")
  ignore_ignition_line = params.get_bool("IgnoreIgnitionLine")
  for app_fn in ("panda.bin.signed", "panda_h7.bin.signed"):
    selected_fn = get_selected_firmware_name(app_fn, remote_start, hkg_remote_start, ignore_ignition_line, enabled)
    selected_path = os.path.join(FW_PATH, selected_fn)
    if not os.path.isfile(selected_path) or os.path.getsize(selected_path) == 0:
      raise RuntimeError(f"Required Panda firmware is missing or empty: {selected_fn}. Update the device firmware package before changing Wake on CAN.")
