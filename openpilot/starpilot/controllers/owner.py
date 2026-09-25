"""Saved controller bindings and guarded physical button dispatch."""

import hashlib
import json
import time
from collections.abc import Callable, Mapping
from threading import RLock

from openpilot.starpilot.favorites.state import FavoriteAction, FavoriteRequest, FavoriteResult, FavoriteSnapshot
from openpilot.starpilot.saved_document import commit_exact
from openpilot.starpilot.saved_source import read_saved


CONTROLLER_BINDINGS_PARAM = "StarPilotControllerBindings"
MAX_BYTES = 16384
MAX_BINDINGS = 64
SLOT_COUNT = 13
OWN_SLOT_COUNT = 10
LEARN_NS = 20_000_000_000
TEST_NS = 20_000_000_000
PRESS_AGE_NS = 250_000_000
MAX_CODE = 65551


def _revision(raw: bytes | None) -> str:
  return hashlib.sha256(b"\x00" if raw is None else b"\x01" + raw).hexdigest()


def _unique(pairs):
  result = {}
  for key, value in pairs:
    if key in result:
      raise ValueError("Duplicate controller field")
    result[key] = value
  return result


def _default_document():
  return {"version": 1, "enabled": False, "slots": [None] * OWN_SLOT_COUNT, "bindings": []}


def _text(value, limit=256):
  return type(value) is str and 0 < len(value) <= limit and all(char.isprintable() for char in value)


def _validate_document(value):
  if type(value) is not dict or set(value) != {"version", "enabled", "slots", "bindings"} or value["version"] != 1 or type(value["version"]) is not int:
    raise ValueError("Invalid controller document")
  if type(value["enabled"]) is not bool or type(value["slots"]) is not list or len(value["slots"]) != OWN_SLOT_COUNT:
    raise ValueError("Invalid controller slots")
  if any(key is not None and not _text(key, 128) for key in value["slots"]):
    raise ValueError("Invalid controller action")
  bindings = value["bindings"]
  if type(bindings) is not list or len(bindings) > MAX_BINDINGS:
    raise ValueError("Invalid controller bindings")
  seen = set()
  for binding in bindings:
    if type(binding) is not dict or set(binding) != {"deviceId", "name", "code", "slot"}:
      raise ValueError("Invalid controller binding")
    device_id, name, code, slot = (binding[field] for field in ("deviceId", "name", "code", "slot"))
    if not _text(device_id) or not _text(name) or type(code) is not int or not 0 <= code <= MAX_CODE or type(slot) is not int or not 0 <= slot < SLOT_COUNT:
      raise ValueError("Invalid controller binding")
    identity = (device_id, code)
    if identity in seen:
      raise ValueError("Duplicate controller button")
    seen.add(identity)
  return value


def _read_document(params):
  raw, readable = read_saved(params, CONTROLLER_BINDINGS_PARAM, MAX_BYTES)
  if not readable:
    return _default_document(), raw, False, False
  if raw is None:
    return _default_document(), raw, True, True
  try:
    return _validate_document(json.loads(raw, object_pairs_hook=_unique)), raw, True, True
  except (ValueError, TypeError, UnicodeError, RecursionError):
    return _default_document(), raw, True, False


def _field(value, key):
  return value.get(key) if isinstance(value, Mapping) else getattr(value, key, None)


class ControllerOwner:
  def __init__(self, params, *, parked: Callable[[], bool], actions: Callable[[], Mapping[str, FavoriteAction]],
               favorites: Callable[[], FavoriteSnapshot], invoke_favorite: Callable[[FavoriteRequest], FavoriteResult],
               clock: Callable[[], int] = time.monotonic_ns):
    self.params = params
    self.parked = parked
    self.actions = actions
    self.favorites = favorites
    self.invoke_favorite = invoke_favorite
    self.clock = clock
    self._lock = RLock()
    self._devices = {}
    self._learning = None
    self._testing_until = 0
    self._last_press = None
    self._sequences = {}
    self._blocked_before = 0

  def set_devices(self, devices):
    trusted = {}
    for device in devices:
      device_id = _field(device, "id")
      name = _field(device, "name")
      bus = _field(device, "bus")
      if len(trusted) < 16 and _text(device_id) and _text(name) and type(bus) is int and bus in (3, 5):
        trusted[device_id] = {"id": device_id, "name": name, "bus": bus}
    with self._lock:
      self._devices = trusted
      self._sequences = {identity: timestamp for identity, timestamp in self._sequences.items() if identity[0] in trusted}

  def tick(self, now_ns=None):
    now = self.clock() if now_ns is None else now_ns
    with self._lock:
      session_before = self._learning is not None or bool(self._testing_until)
      if (self._learning is not None or self._testing_until) and not self.parked():
        self._learning = None
        self._testing_until = 0
      if self._learning is not None and now >= self._learning["until"]:
        self._learning = None
      if self._testing_until and now >= self._testing_until:
        self._testing_until = 0
      if session_before and self._learning is None and not self._testing_until:
        self._blocked_before = max(self._blocked_before, now)

  def snapshot(self, devices=None):
    if devices is not None:
      self.set_devices(devices)
    now = self.clock()
    self.tick(now)
    document, raw, readable, valid = _read_document(self.params)
    catalog = self.actions()
    favorite = self.favorites()
    slots = []
    for index in range(SLOT_COUNT):
      if index < 3:
        source = favorite.slots[index]
        slots.append({"index": index, "label": source.label or f"Favorite {index + 1}", "key": source.key, "available": bool(source.available)})
      else:
        key = document["slots"][index - 3]
        action = catalog.get(key) if key else None
        slots.append({"index": index, "label": action.label if action else key or f"Button {index - 2}",
                      "key": key, "available": bool(action and action.available and action.invoke is not None)})
    options = [{"key": action.key, "label": action.label, "section": action.section} for action in
               sorted(catalog.values(), key=lambda item: (item.section.casefold(), item.label.casefold(), item.key))]
    with self._lock:
      learning = None if self._learning is None else {"slot": self._learning["slot"],
                                                     "expiresIn": max(0, (self._learning["until"] - now + 999_999_999) // 1_000_000_000)}
      devices_out = sorted(self._devices.values(), key=lambda device: (device["name"].casefold(), device["id"]))
      testing = bool(self._testing_until)
      last_press = dict(self._last_press) if self._last_press else None
    return {"version": 1, "available": True, "editable": bool(readable and self.parked()),
            "enabled": document["enabled"] if valid else False, "revision": _revision(raw), "valid": valid,
            "devices": devices_out, "slots": slots, "options": options, "bindings": document["bindings"] if valid else [],
            "learning": learning, "testing": testing, "lastPress": last_press}

  def _save(self, document, raw):
    encoded = json.dumps(_validate_document(document), separators=(",", ":"), allow_nan=False).encode()
    if len(encoded) > MAX_BYTES:
      raise ValueError("Controller bindings are too large")
    result = commit_exact(self.params, key=CONTROLLER_BINDINGS_PARAM, max_bytes=MAX_BYTES, raw=encoded,
                          expected=raw, authorized=self.parked, temp_prefix=".controller-bindings-")
    if not result.committed or not result.verified:
      raise RuntimeError("Controller bindings changed or could not be saved")

  def action(self, payload):
    if type(payload) is not dict or type(payload.get("operation")) is not str:
      raise ValueError("Invalid controller request")
    operation = payload["operation"]
    fields = {"save": {"operation", "revision", "enabled", "slots"},
              "learn": {"operation", "revision", "slot"}, "cancel": {"operation"},
              "test": {"operation", "enabled"}, "remove": {"operation", "revision", "deviceId", "code"}}
    if operation not in fields or set(payload) != fields[operation]:
      raise ValueError("Invalid controller request")
    if not self.parked():
      raise PermissionError("Turn off the vehicle to edit Controller Buttons")
    with self._lock:
      self.tick()
      if operation == "cancel":
        self._blocked_before = max(self._blocked_before, self.clock())
        self._learning = None
        self._testing_until = 0
      elif operation == "test":
        if type(payload["enabled"]) is not bool:
          raise ValueError("Invalid test state")
        self._blocked_before = max(self._blocked_before, self.clock())
        self._learning = None
        self._testing_until = self.clock() + TEST_NS if payload["enabled"] else 0
      else:
        document, raw, readable, valid = _read_document(self.params)
        if not readable:
          raise OSError("Controller bindings unavailable")
        if type(payload["revision"]) is not str or payload["revision"] != _revision(raw):
          raise RuntimeError("Controller bindings changed. Reload before editing")
        if operation == "learn":
          slot = payload["slot"]
          if type(slot) is not int or not 0 <= slot < SLOT_COUNT:
            raise ValueError("Invalid controller slot")
          if not valid:
            raise ValueError("Repair controller bindings before learning")
          self._testing_until = 0
          started = self.clock()
          self._learning = {"slot": slot, "revision": _revision(raw), "started": started, "until": started + LEARN_NS}
        elif operation == "save":
          enabled, slots = payload["enabled"], payload["slots"]
          if type(enabled) is not bool or type(slots) is not list or len(slots) != OWN_SLOT_COUNT:
            raise ValueError("Invalid controller slots")
          if any(key is not None and not _text(key, 128) for key in slots):
            raise ValueError("Invalid controller action")
          catalog = self.actions()
          previous = document["slots"] if valid else [None] * OWN_SLOT_COUNT
          for index, key in enumerate(slots):
            if key is not None and key not in catalog and key != previous[index]:
              raise ValueError("Unsupported controller action")
          self._save({"version": 1, "enabled": enabled, "slots": slots,
                      "bindings": document["bindings"] if valid else []}, raw)
          self._blocked_before = max(self._blocked_before, self.clock())
          self._learning = None
          self._testing_until = 0
        else:
          device_id, code = payload["deviceId"], payload["code"]
          if not _text(device_id) or type(code) is not int or not 0 <= code <= MAX_CODE:
            raise ValueError("Invalid controller button")
          if not valid:
            raise ValueError("Repair controller bindings before removing")
          bindings = [binding for binding in document["bindings"] if (binding["deviceId"], binding["code"]) != (device_id, code)]
          if len(bindings) == len(document["bindings"]):
            raise ValueError("Controller button is not assigned")
          self._save({**document, "bindings": bindings}, raw)
          self._blocked_before = max(self._blocked_before, self.clock())
          self._learning = None
    return self.snapshot()

  def _press_status(self, device_id, code, slot, executed, message):
    with self._lock:
      self._last_press = {"deviceId": device_id, "code": code, "slot": slot, "executed": executed, "message": message}

  def feed(self, press):
    device_id, code = _field(press, "device_id"), _field(press, "code")
    timestamp = _field(press, "timestamp_ns")
    now = self.clock()
    if not _text(device_id) or type(code) is not int or not 0 <= code <= MAX_CODE or type(timestamp) is not int or not 0 <= now - timestamp <= PRESS_AGE_NS:
      return
    with self._lock:
      self.tick(now)
      identity = (device_id, code)
      if device_id not in self._devices or timestamp <= self._blocked_before or timestamp <= self._sequences.get(identity, -1):
        return
      self._sequences[identity] = timestamp
      if len(self._sequences) > 256:
        self._sequences = {key: seen for key, seen in self._sequences.items() if seen >= now - PRESS_AGE_NS}
      learning = self._learning
      testing = bool(self._testing_until)
    if learning is not None:
      if timestamp < learning["started"]:
        return
      if not self.parked():
        with self._lock:
          self._learning = None
        return
      document, raw, readable, valid = _read_document(self.params)
      if not readable or not valid or _revision(raw) != learning["revision"]:
        with self._lock:
          self._learning = None
        return
      with self._lock:
        if self._learning is not learning or device_id not in self._devices or not self.parked():
          return
        binding = {"deviceId": device_id, "name": self._devices[device_id]["name"], "code": code, "slot": learning["slot"]}
        bindings = [item for item in document["bindings"] if (item["deviceId"], item["code"]) != (device_id, code)]
        bindings.append(binding)
        try:
          self._save({**document, "bindings": bindings}, raw)
        except (OSError, RuntimeError, ValueError):
          self._press_status(device_id, code, learning["slot"], False, "Button could not be learned")
          return
        if self._learning is learning:
          self._learning = None
      self._press_status(device_id, code, learning["slot"], False, "Button learned")
      return
    document, raw, readable, valid = _read_document(self.params)
    binding = next((item for item in document["bindings"] if (item["deviceId"], item["code"]) == (device_id, code)), None) if valid else None
    slot = binding["slot"] if binding else None
    if testing:
      self._press_status(device_id, code, slot, False, "Test press detected")
      return
    if not readable or not valid or not document["enabled"] or binding is None:
      return
    if slot < 3:
      favorite = self.favorites().slots[slot]
      request = favorite.request
      if not favorite.available or request is None:
        self._press_status(device_id, code, slot, False, "Quick Select unavailable")
        return
      with self._lock:
        if self._learning is not None or self._testing_until:
          return
        current, fresh = read_saved(self.params, CONTROLLER_BINDINGS_PARAM, MAX_BYTES)
        renewed = self.favorites().slots[slot]
        if not fresh or current != raw or not renewed.available or renewed.request != request:
          self._press_status(device_id, code, slot, False, "Control changed")
          return
        result = self.invoke_favorite(request)
      self._press_status(device_id, code, slot, result.success, result.message)
      return
    key = document["slots"][slot - 3]
    first = self.actions().get(key) if key else None
    if first is None or not first.available or first.invoke is None:
      self._press_status(device_id, code, slot, False, "Control unavailable")
      return
    with self._lock:
      if self._learning is not None or self._testing_until:
        return
      current, fresh = read_saved(self.params, CONTROLLER_BINDINGS_PARAM, MAX_BYTES)
      second = self.actions().get(key)
      if (not fresh or current != raw or second is None or not second.available or second.invoke is None or
          second.key != first.key or second.token != first.token):
        self._press_status(device_id, code, slot, False, "Control changed")
        return
      try:
        success = bool(second.invoke())
      except (OSError, RuntimeError, ValueError, TypeError):
        success = False
    self._press_status(device_id, code, slot, success, second.label if success else "Control unavailable")
