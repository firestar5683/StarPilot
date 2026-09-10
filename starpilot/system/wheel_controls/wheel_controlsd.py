#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import selectors
import struct
import threading
import time
import urllib.request

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.common.constants import CV
from openpilot.starpilot.common.favorite_slots import FAVORITE_SLOT_COUNT


MAPPINGS_PARAM = "WheelControlMappings"
CONTROLLER_ACTIONS_PARAM = "ControllerActionSlots"
LEARN_SLOT_PARAM = "WheelControlLearnSlot"
STATUS_PARAM = "WheelControlStatus"
TEST_ACTIVE_PARAM = "WheelControlTestActive"
ENABLED_PARAM = "WheelControlsEnabled"
JOYSTICK_DEVICE_PARAM = "JoystickControlDevice"
CONTROLLER_ACTION_SLOT_COUNT = 10
MAPPING_SLOT_COUNT = FAVORITE_SLOT_COUNT + CONTROLLER_ACTION_SLOT_COUNT
from openpilot.starpilot.common.controller_actions import (
  CONTROLLER_ACTION_CYCLE_PERSONALITY,
  CONTROLLER_ACTION_SET_SPEED,
  CONTROLLER_ACTION_SELFIE,
  CONTROLLER_ACTION_BOOKMARK,
  CONTROLLER_ACTION_PULSE_AND_GLIDE,
  CONTROLLER_ACTION_FORCE_COAST,
  CONTROLLER_ACTION_TOGGLE_AOL,
  CONTROLLER_ACTION_ENGAGE,
  CONTROLLER_ACTION_DISENGAGE,
  CONTROLLER_ACTION_COUNTERS,
  CONTROLLER_ACTION_OPTIONS,
  CONTROLLER_ACTION_KEYS,
  controller_speed_bounds,
)
LEARN_TIMEOUT_SECONDS = 20.0
DEVICE_SCAN_INTERVAL_SECONDS = 1.0
STATUS_INTERVAL_SECONDS = 0.5
EV_KEY = 1
EV_ABS = 3
KEY_DOWN = 1
ABS_HAT0X = 16
ABS_HAT3Y = 23
HAT_EVENT_BASE = 0x10000
EXTERNAL_INPUT_BUSES = {0x0003, 0x0005}
INPUT_EVENT = struct.Struct("@llHHi")
MODALIAS_RE = re.compile(r"input:b([0-9a-f]{4})v([0-9a-f]{4})p([0-9a-f]{4})e([0-9a-f]{4})", re.IGNORECASE)
_SELFIE_REQUEST_LOCK = threading.Lock()

try:
  from inputs import KEYS_AND_BUTTONS
  KEY_NAMES = dict(KEYS_AND_BUTTONS)
except ImportError:
  KEY_NAMES = {}


@dataclass(frozen=True)
class InputSource:
  path: str
  device_id: str
  name: str
  bus: int
  vendor: int
  product: int
  phys: str = ""
  uniq: str = ""
  joystick_capable: bool = False

  def serialize(self) -> dict[str, Any]:
    return {
      "path": self.path,
      "device_id": self.device_id,
      "name": self.name,
      "bus": self.bus,
      "vendor": self.vendor,
      "product": self.product,
      "joystick_capable": self.joystick_capable,
    }


def _read_text(path: Path) -> str:
  try:
    return path.read_text(encoding="utf-8", errors="replace").strip()
  except OSError:
    return ""


def inspect_input_source(path: str) -> InputSource | None:
  event_name = Path(path).name
  sysfs = Path("/sys/class/input") / event_name / "device"
  match = MODALIAS_RE.match(_read_text(sysfs / "modalias"))
  if match is None:
    return None

  bus, vendor, product, _version = (int(value, 16) for value in match.groups())
  if bus not in EXTERNAL_INPUT_BUSES:
    return None

  name = _read_text(sysfs / "name") or "External input"
  phys = _read_text(sysfs / "phys")
  uniq = _read_text(sysfs / "uniq")
  identity = f"{bus:04x}:{vendor:04x}:{product:04x}:{name.casefold()}:{uniq.casefold()}"
  device_id = hashlib.sha256(identity.encode()).hexdigest()[:20]
  joystick_capable = any(sysfs.resolve().glob("js*"))
  return InputSource(path, device_id, name, bus, vendor, product, phys, uniq, joystick_capable)


def connected_input_sources() -> list[InputSource]:
  if not Path("/dev/input").is_dir():
    return []
  return [source for path in sorted(Path("/dev/input").glob("event*")) if (source := inspect_input_source(str(path))) is not None]


def selected_joystick_device(params: Params | None = None) -> str:
  params = params or Params(return_defaults=True)
  try:
    return (params.get(JOYSTICK_DEVICE_PARAM, encoding="utf-8") or "").strip()
  except Exception:
    return ""


def set_joystick_device(device_id: str, enabled: bool, params: Params | None = None) -> str:
  params = params or Params(return_defaults=True)
  selected = device_id.strip() if enabled else ""
  if selected:
    params.put(JOYSTICK_DEVICE_PARAM, selected)
  else:
    params.remove(JOYSTICK_DEVICE_PARAM)
  params.put_bool(ENABLED_PARAM, bool(load_mappings(params) or selected))
  return selected


def event_name(code: int) -> str:
  if HAT_EVENT_BASE <= code < HAT_EVENT_BASE + (ABS_HAT3Y - ABS_HAT0X + 1) * 2:
    offset = code - HAT_EVENT_BASE
    axis = ABS_HAT0X + offset // 2
    positive = bool(offset % 2)
    hat = (axis - ABS_HAT0X) // 2
    vertical = bool((axis - ABS_HAT0X) % 2)
    direction = ("DOWN" if positive else "UP") if vertical else ("RIGHT" if positive else "LEFT")
    return f"DPAD_{direction}" if hat == 0 else f"HAT_{hat}_{direction}"
  return KEY_NAMES.get(code, f"KEY_{code}")


def hat_event_code(axis: int, value: int) -> int:
  return HAT_EVENT_BASE + (axis - ABS_HAT0X) * 2 + int(value > 0)


def mapping_id(device_id: str, code: int) -> str:
  return hashlib.sha256(f"{device_id}:{code}".encode()).hexdigest()[:16]


def default_controller_action_slots() -> list[dict[str, Any]]:
  return [{"enabled": False, "key": None, "label": "", "value": None} for _ in range(CONTROLLER_ACTION_SLOT_COUNT)]


def normalize_controller_action_slots(value: Any, eligible_keys: set[str] | None = None) -> list[dict[str, Any]]:
  if isinstance(value, bytes):
    value = value.decode("utf-8", errors="replace")
  if isinstance(value, str):
    try:
      value = json.loads(value)
    except json.JSONDecodeError:
      value = []
  if not isinstance(value, list):
    value = []

  slots = default_controller_action_slots()
  for index, raw in enumerate(value[:CONTROLLER_ACTION_SLOT_COUNT]):
    if not isinstance(raw, dict):
      continue
    key = str(raw.get("key") or "").strip() or None
    if key is not None and eligible_keys is not None and key not in eligible_keys:
      key = None
    label = str(raw.get("label") or "").strip()[:64] if key else ""
    value = None
    if key == CONTROLLER_ACTION_SET_SPEED:
      try:
        candidate = float(raw.get("value"))
        value = candidate if math.isfinite(candidate) and candidate > 0 else None
      except (TypeError, ValueError):
        pass
    enabled = key is not None and (key != CONTROLLER_ACTION_SET_SPEED or value is not None)
    slots[index] = {"enabled": enabled, "key": key, "label": label, "value": value}
  return slots


def load_controller_action_slots(params: Params | None = None,
                                 eligible_keys: set[str] | None = None) -> list[dict[str, Any]]:
  params = params or Params(return_defaults=True)
  try:
    raw = params.get(CONTROLLER_ACTIONS_PARAM)
  except Exception:
    raw = None
  return normalize_controller_action_slots(raw, eligible_keys)


def save_controller_action_slots(slots: list[dict[str, Any]], params: Params | None = None, *,
                                 eligible_keys: set[str] | None = None) -> list[dict[str, Any]]:
  params = params or Params(return_defaults=True)
  normalized = normalize_controller_action_slots(slots, eligible_keys)
  params.put(CONTROLLER_ACTIONS_PARAM, normalized)
  return normalized


def set_controller_action_slot(index: int, key: str | None, label: str, params: Params | None = None, *, value: float | None = None,
                               eligible_keys: set[str] | None = None) -> list[dict[str, Any]]:
  if not 0 <= index < CONTROLLER_ACTION_SLOT_COUNT:
    raise ValueError(f"Controller action must be between 1 and {CONTROLLER_ACTION_SLOT_COUNT}")
  key = str(key or "").strip() or None
  if key is not None and eligible_keys is not None and key not in eligible_keys:
    raise ValueError("That controller action is not available")
  params = params or Params(return_defaults=True)
  slots = load_controller_action_slots(params, eligible_keys)
  slots[index] = {"enabled": key is not None, "key": key, "label": label if key else "", "value": value}
  return save_controller_action_slots(slots, params, eligible_keys=eligible_keys)


def set_controller_cruise_speed(value: Any, params: Params, params_memory: Params) -> bool:
  if not params.get_bool("IsOnroad") or not params.get_bool("IsEngaged"):
    return False
  try:
    native_speed = float(value)
  except (TypeError, ValueError):
    return False
  minimum, maximum = controller_speed_bounds(params.get_bool("IsMetric"))
  if not math.isfinite(native_speed) or not minimum <= native_speed <= maximum:
    return False
  conversion = CV.KPH_TO_MS if params.get_bool("IsMetric") else CV.MPH_TO_MS
  params_memory.put_float("SLCForceCruiseSpeed", native_speed * conversion)
  return True


def _request_comma_selfie() -> None:
  if not _SELFIE_REQUEST_LOCK.acquire(blocking=False):
    return
  try:
    port = os.environ.get("SP_GALAXY_PORT", "8082")
    request = urllib.request.Request(f"http://127.0.0.1:{port}/api/sentry/selfie", method="POST")
    with urllib.request.urlopen(request, timeout=10.0):
      pass
  except Exception:
    cloudlog.exception("wheel controls: Comma Selfie capture failed")
  finally:
    _SELFIE_REQUEST_LOCK.release()


def request_comma_selfie() -> bool:
  threading.Thread(target=_request_comma_selfie, name="comma-selfie", daemon=True).start()
  return True


def trigger_controller_action(key: str, params_memory: Params) -> bool:
  counter_key = CONTROLLER_ACTION_COUNTERS.get(key)
  if counter_key is None:
    return False
  params_memory.put_int(counter_key, params_memory.get_int(counter_key) + 1)
  return True


def normalize_mappings(value: Any) -> list[dict[str, Any]]:
  if isinstance(value, bytes):
    value = value.decode("utf-8", errors="replace")
  if isinstance(value, str):
    try:
      value = json.loads(value)
    except json.JSONDecodeError:
      return []
  if not isinstance(value, list):
    return []

  normalized: list[dict[str, Any]] = []
  seen: set[tuple[str, int]] = set()
  for raw in value:
    if not isinstance(raw, dict):
      continue
    device_id = str(raw.get("device_id") or "").strip()
    name = str(raw.get("device_name") or "External input").strip()[:96]
    try:
      code = int(raw.get("event_code"))
      slot = int(raw.get("slot"))
    except (TypeError, ValueError):
      continue
    if not device_id or code < 0 or not 0 <= slot < MAPPING_SLOT_COUNT:
      continue
    signature = (device_id, code)
    if signature in seen:
      continue
    seen.add(signature)
    normalized.append({
      "id": mapping_id(device_id, code),
      "device_id": device_id,
      "device_name": name,
      "event_code": code,
      "event_name": str(raw.get("event_name") or event_name(code))[:64],
      "slot": slot,
    })
  return normalized


def load_mappings(params: Params | None = None) -> list[dict[str, Any]]:
  params = params or Params(return_defaults=True)
  try:
    return normalize_mappings(params.get(MAPPINGS_PARAM))
  except Exception:
    return []


def save_mappings(mappings: list[dict[str, Any]], params: Params | None = None) -> list[dict[str, Any]]:
  params = params or Params(return_defaults=True)
  normalized = normalize_mappings(mappings)
  params.put(MAPPINGS_PARAM, normalized)
  params.put_bool(ENABLED_PARAM, bool(normalized or selected_joystick_device(params)))
  return normalized


def upsert_mapping(source: InputSource, code: int, slot: int, params: Params | None = None) -> dict[str, Any]:
  params = params or Params(return_defaults=True)
  mappings = [
    mapping for mapping in load_mappings(params)
    if not (mapping["device_id"] == source.device_id and mapping["event_code"] == code)
  ]
  learned = {
    "id": mapping_id(source.device_id, code),
    "device_id": source.device_id,
    "device_name": source.name,
    "event_code": code,
    "event_name": event_name(code),
    "slot": slot,
  }
  mappings.append(learned)
  save_mappings(mappings, params)
  return learned


def delete_mapping(identifier: str, params: Params | None = None) -> bool:
  params = params or Params(return_defaults=True)
  mappings = load_mappings(params)
  kept = [mapping for mapping in mappings if mapping["id"] != identifier]
  if len(kept) == len(mappings):
    return False
  save_mappings(kept, params)
  return True


def clear_mappings(params: Params | None = None) -> None:
  save_mappings([], params)


def start_learning(slot: int, params_memory: Params | None = None, params: Params | None = None) -> None:
  if not 0 <= slot < MAPPING_SLOT_COUNT:
    raise ValueError(f"Mapping target must be between 1 and {MAPPING_SLOT_COUNT}")
  params_memory = params_memory or Params(memory=True)
  (params or Params()).put_bool(ENABLED_PARAM, True)
  params_memory.put_int(LEARN_SLOT_PARAM, slot + 1)


def cancel_learning(params_memory: Params | None = None, params: Params | None = None) -> None:
  (params_memory or Params(memory=True)).remove(LEARN_SLOT_PARAM)
  if params is not None and not load_mappings(params):
    params.put_bool(ENABLED_PARAM, False)


def start_testing(params_memory: Params | None = None, params: Params | None = None) -> None:
  params = params or Params(return_defaults=True)
  if not load_mappings(params):
    raise ValueError("Map at least one button before testing")
  params.put_bool(ENABLED_PARAM, True)
  (params_memory or Params(memory=True)).put_bool(TEST_ACTIVE_PARAM, True)


def stop_testing(params_memory: Params | None = None) -> None:
  (params_memory or Params(memory=True)).remove(TEST_ACTIVE_PARAM)


def _status_value(params_memory: Params) -> dict[str, Any]:
  try:
    value = params_memory.get(STATUS_PARAM)
  except Exception:
    return {}
  if isinstance(value, bytes):
    value = value.decode("utf-8", errors="replace")
  if isinstance(value, str):
    try:
      value = json.loads(value)
    except json.JSONDecodeError:
      return {}
  return value if isinstance(value, dict) else {}


def public_status(params: Params | None = None, params_memory: Params | None = None) -> dict[str, Any]:
  params = params or Params(return_defaults=True)
  params_memory = params_memory or Params(memory=True)
  status = _status_value(params_memory)
  updated_at = float(status.get("updated_at", 0.0) or 0.0)
  status["available"] = bool(updated_at and time.monotonic() - updated_at < 3.0)
  selected = selected_joystick_device(params)
  if not status["available"]:
    status["devices"] = [source.serialize() for source in connected_input_sources()]
  for device in status.get("devices", []):
    device["joystick_enabled"] = device.get("device_id") == selected
  status["joystick_device"] = selected
  status["offroad"] = params.get_bool("IsOffroad")
  status["enabled"] = params.get_bool(ENABLED_PARAM)
  status["mappings"] = load_mappings(params)
  status.setdefault("devices", [])
  status.setdefault("learning", False)
  status.setdefault("learning_slot", None)
  status.setdefault("remaining_seconds", 0)
  status.setdefault("last_learned", None)
  status.setdefault("testing", False)
  status.setdefault("last_tested", None)
  return status


def execute_favorite_slot(slot: int, params: Params, params_memory: Params) -> bool:
  from openpilot.starpilot.common.favorite_slots import toggle_favorite_slot
  return toggle_favorite_slot(slot, params, params_memory)


def cycle_driving_personality(params: Params) -> bool:
  """Select the next native personality, without synthesizing cruise/Traffic inputs."""
  from cereal import car, log

  if params.get_bool("SafeMode"):
    return False
  try:
    # Match native UI capability selection; never use parked CP while on-road.
    cp_bytes = params.get("CarParams" if params.get_bool("IsOnroad") else "CarParamsPersistent")
    if not cp_bytes:
      return False
    with car.CarParams.from_bytes(cp_bytes) as cp:
      available = params.get_bool("AlphaLongitudinalEnabled") if cp.alphaLongitudinalAvailable else cp.openpilotLongitudinalControl
    if not available:
      return False

    # Typed Params decoding truncates fractional ints and defaults corrupt text.
    # Inspect the stored token so malformed selections cannot become Aggressive.
    current = Path(params.get_param_path("LongitudinalPersonality")).read_bytes()
    profiles = tuple(int(profile) for profile in (
      log.LongitudinalPersonality.aggressive,
      log.LongitudinalPersonality.standard,
      log.LongitudinalPersonality.relaxed,
    ))
    tokens = tuple(str(profile).encode("ascii") for profile in profiles)
    if current not in tokens:
      return False
    next_personality = profiles[(tokens.index(current) + 1) % len(profiles)]
  except Exception:
    # Missing/malformed CP or selection: do not change effective driving state.
    return False

  if params.get_bool("SafeMode"):
    return False
  # Synchronous persistence lets successive HID events see the preceding change.
  # selfdrived's existing Params reader publishes this selection; Traffic retains
  # its independent override. No toggle refresh or virtual speed input is needed.
  params.put_int("LongitudinalPersonality", next_personality)
  return True


def execute_controller_action(index: int, params: Params, params_memory: Params) -> bool:
  slots = load_controller_action_slots(params)
  if not 0 <= index < len(slots):
    return False
  slot = slots[index]
  if not slot.get("enabled"):
    return False
  return execute_controller_key(slot.get("key"), params, params_memory, value=slot.get("value"))


def execute_controller_key(key, params: Params, params_memory: Params, *, value=None) -> bool:
  from openpilot.starpilot.common.favorite_slots import execute_favorite_key
  if key == CONTROLLER_ACTION_CYCLE_PERSONALITY:
    return cycle_driving_personality(params)
  if key == CONTROLLER_ACTION_SET_SPEED:
    return set_controller_cruise_speed(value, params, params_memory)
  if key == CONTROLLER_ACTION_SELFIE:
    return request_comma_selfie()
  if key in (CONTROLLER_ACTION_ENGAGE, CONTROLLER_ACTION_DISENGAGE) and not params.get_bool("IsOnroad"):
    return False
  if key in CONTROLLER_ACTION_COUNTERS:
    return trigger_controller_action(key, params_memory)
  return execute_favorite_key(key, params, params_memory)


def execute_mapping_slot(slot: int, params: Params, params_memory: Params) -> bool:
  if slot < FAVORITE_SLOT_COUNT:
    return execute_favorite_slot(slot, params, params_memory)
  return execute_controller_action(slot - FAVORITE_SLOT_COUNT, params, params_memory)


class WheelControlsDaemon:
  def __init__(self, params: Params | None = None, params_memory: Params | None = None):
    self.params = params or Params(return_defaults=True)
    self.params_memory = params_memory or Params(memory=True)
    self.selector = selectors.DefaultSelector()
    self.sources: dict[int, InputSource] = {}
    self.buffers: dict[int, bytearray] = {}
    self.hat_values: dict[tuple[int, int], int] = {}
    self.learning_slot: int | None = None
    self.learning_deadline = 0.0
    self.last_learned: dict[str, Any] | None = None
    self.testing = False
    self.last_tested: dict[str, Any] | None = None
    self.last_scan = 0.0
    self.last_status = 0.0

  def close(self) -> None:
    for fd in list(self.sources):
      self._remove(fd)
    self.selector.close()
    self.params_memory.remove(TEST_ACTIVE_PARAM)
    self.params_memory.remove(STATUS_PARAM)

  def _remove(self, fd: int) -> None:
    try:
      self.selector.unregister(fd)
    except Exception:
      pass
    try:
      os.close(fd)
    except OSError:
      pass
    self.sources.pop(fd, None)
    self.buffers.pop(fd, None)
    self.hat_values = {key: value for key, value in self.hat_values.items() if key[0] != fd}

  def _scan_devices(self) -> None:
    current_paths = {source.path for source in self.sources.values()}
    existing_paths = set(Path("/dev/input").glob("event*")) if Path("/dev/input").is_dir() else set()
    for fd, source in list(self.sources.items()):
      if Path(source.path) not in existing_paths:
        self._remove(fd)

    for path in sorted(existing_paths):
      path_text = str(path)
      if path_text in current_paths:
        continue
      source = inspect_input_source(path_text)
      if source is None:
        continue
      try:
        fd = os.open(path_text, os.O_RDONLY | os.O_NONBLOCK)
        self.selector.register(fd, selectors.EVENT_READ)
      except OSError:
        continue
      self.sources[fd] = source
      self.buffers[fd] = bytearray()

  def _update_learning(self, now: float) -> None:
    if not self.params.get_bool("IsOffroad"):
      cancel_learning(self.params_memory, self.params)
      self.learning_slot = None
      return

    requested = self.params_memory.get_int(LEARN_SLOT_PARAM)
    if 1 <= requested <= MAPPING_SLOT_COUNT:
      slot = requested - 1
      if slot != self.learning_slot:
        self.learning_slot = slot
        self.learning_deadline = now + LEARN_TIMEOUT_SECONDS
    elif self.learning_slot is not None:
      self.learning_slot = None

    if self.learning_slot is not None and now >= self.learning_deadline:
      cancel_learning(self.params_memory, self.params)
      self.learning_slot = None

  def _update_testing(self) -> None:
    requested = self.params_memory.get_bool(TEST_ACTIVE_PARAM)
    if not self.params.get_bool("IsOffroad"):
      stop_testing(self.params_memory)
      self.testing = False
      return
    if requested and not self.testing:
      self.testing = True
      self.last_tested = None
    elif not requested:
      self.testing = False

  def _handle_key(self, source: InputSource, code: int) -> None:
    if source.device_id == selected_joystick_device(self.params):
      return
    if self.learning_slot is not None:
      learned = upsert_mapping(source, code, self.learning_slot, self.params)
      self.last_learned = learned
      cancel_learning(self.params_memory, self.params)
      self.learning_slot = None
      return

    mappings = load_mappings(self.params)
    if self.testing:
      mapping = next((item for item in mappings if item["device_id"] == source.device_id and item["event_code"] == code), None)
      self.last_tested = {
        "mapped": mapping is not None,
        "device_name": source.name,
        "event_code": code,
        "event_name": event_name(code),
        "slot": mapping["slot"] if mapping is not None else None,
      }
      return

    for mapping in mappings:
      if mapping["device_id"] == source.device_id and mapping["event_code"] == code:
        try:
          execute_mapping_slot(mapping["slot"], self.params, self.params_memory)
        except Exception:
          cloudlog.exception("wheel control action failed")
        return

  def _read_events(self, fd: int) -> None:
    try:
      chunk = os.read(fd, INPUT_EVENT.size * 32)
    except BlockingIOError:
      return
    except OSError:
      self._remove(fd)
      return
    if not chunk:
      self._remove(fd)
      return

    buffer = self.buffers.get(fd)
    source = self.sources.get(fd)
    if buffer is None or source is None:
      return
    buffer.extend(chunk)
    while len(buffer) >= INPUT_EVENT.size:
      raw = bytes(buffer[:INPUT_EVENT.size])
      del buffer[:INPUT_EVENT.size]
      _seconds, _microseconds, event_type, code, value = INPUT_EVENT.unpack(raw)
      if event_type == EV_KEY and value == KEY_DOWN:
        self._handle_key(source, code)
      elif event_type == EV_ABS and ABS_HAT0X <= code <= ABS_HAT3Y:
        previous = self.hat_values.get((fd, code), 0)
        self.hat_values[(fd, code)] = value
        if value and value != previous:
          self._handle_key(source, hat_event_code(code, value))

  def _publish_status(self, now: float) -> None:
    remaining = max(0, round(self.learning_deadline - now, 1)) if self.learning_slot is not None else 0
    status = {
      "updated_at": now,
      "devices": [source.serialize() for source in sorted(self.sources.values(), key=lambda item: item.name.casefold())],
      "learning": self.learning_slot is not None,
      "learning_slot": self.learning_slot,
      "remaining_seconds": remaining,
      "last_learned": self.last_learned,
      "testing": self.testing,
      "last_tested": self.last_tested,
    }
    self.params_memory.put(STATUS_PARAM, status)

  def run(self) -> None:
    try:
      while True:
        now = time.monotonic()
        self._update_learning(now)
        self._update_testing()
        if now - self.last_scan >= DEVICE_SCAN_INTERVAL_SECONDS:
          self._scan_devices()
          self.last_scan = now
        for key, _mask in self.selector.select(timeout=0.1):
          try:
            self._read_events(key.fd)
          except (KeyError, OSError):
            self._remove(key.fd)
        now = time.monotonic()
        if now - self.last_status >= STATUS_INTERVAL_SECONDS:
          self._publish_status(now)
          self.last_status = now
    finally:
      self.close()


def main() -> None:
  WheelControlsDaemon().run()


if __name__ == "__main__":
  main()
