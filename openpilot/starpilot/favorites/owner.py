import hashlib
import json
import math
from collections.abc import Callable, Mapping

from openpilot.starpilot.favorites.actions import SET_SPEED
from openpilot.starpilot.favorites.state import FavoriteAction, FavoriteRequest, FavoriteResult, FavoriteSlot, FavoriteSnapshot
from openpilot.starpilot.saved_document import commit_exact
from openpilot.starpilot.saved_source import read_saved

FAVORITE_SLOTS_PARAM = "StarPilotFavoriteSlots"
FAVORITE_SLOT_COUNT = 3
MAX_BYTES = 8192


class FavoritesChanged(Exception):
  pass


def default_slots():
  return [{"enabled": False, "show_onroad": False, "key": None, "label": ""} for _ in range(FAVORITE_SLOT_COUNT)]


def revision(raw):
  return hashlib.sha256(b"\x00" if raw is None else b"\x01" + raw).hexdigest()


def _unique(pairs):
  result = {}
  for key, value in pairs:
    if key in result:
      raise ValueError("Duplicate favorite field")
    result[key] = value
  return result


def validate_slots(value, *, legacy=False):
  if legacy and isinstance(value, dict):
    value = value.get("slots")
  if type(value) is not list or (len(value) > FAVORITE_SLOT_COUNT if legacy else len(value) != FAVORITE_SLOT_COUNT):
    raise ValueError("Quick Select require three slots")
  slots = default_slots()
  for index, slot in enumerate(value):
    if type(slot) is not dict or not set(slot) <= {"enabled", "show_onroad", "key", "label", "value"}:
      raise ValueError("Invalid favorite slot")
    if not legacy and not {"enabled", "show_onroad", "key", "label"} <= set(slot):
      raise ValueError("Incomplete favorite slot")
    key, label = slot.get("key"), slot.get("label", "")
    enabled, shown = slot.get("enabled", False), slot.get("show_onroad", False)
    if (key is not None and (type(key) is not str or not key or len(key) > 128) or
        type(label) is not str or len(label) > 32 or type(enabled) is not bool or type(shown) is not bool):
      raise ValueError("Invalid favorite values")
    saved = {"enabled": enabled, "show_onroad": shown, "key": key, "label": label if key else ""}
    if "value" in slot:
      speed_value = slot.get("value")
      if key != SET_SPEED or speed_value is not None and (
        not isinstance(speed_value, int | float) or isinstance(speed_value, bool) or not math.isfinite(speed_value) or speed_value <= 0
      ):
        raise ValueError("Invalid favorite action value")
      saved["value"] = speed_value
    slots[index] = saved
  return slots


def read_slots(params):
  raw, readable = read_saved(params, FAVORITE_SLOTS_PARAM, MAX_BYTES)
  if not readable:
    return default_slots(), raw, False, False
  if raw is None:
    return default_slots(), raw, True, True
  try:
    return validate_slots(json.loads(raw, object_pairs_hook=_unique), legacy=True), raw, True, True
  except (ValueError, TypeError, UnicodeError, RecursionError):
    return default_slots(), raw, True, False


class FavoritesOwner:
  def __init__(self, params, actions: Callable[[], Mapping[str, FavoriteAction]], configurable: Callable[[], bool]):
    self.params, self.actions, self.configurable = params, actions, configurable

  def snapshot(self):
    saved, raw, readable, valid = read_slots(self.params)
    options = self.actions()
    token = revision(raw)
    slots = []
    for index, slot in enumerate(saved):
      action = options.get(slot["key"])
      assigned = slot["enabled"] and slot["key"] is not None
      available = bool(readable and valid and assigned and action and action.available and action.invoke is not None)
      label = slot["label"] or (action.label if action else slot["key"]) or ""
      reason = ("Saved Quick Select are unavailable" if not readable or not valid else
                "Choose a control" if not slot["key"] else "Quick Select is disabled" if not slot["enabled"] else
                "This saved control is not available in this build" if action is None else action.reason)
      request = FavoriteRequest(index, slot["key"], token, action.token) if assigned and action else None
      slots.append(FavoriteSlot(index, slot["key"], label, slot["enabled"], slot["show_onroad"],
                                action.kind if action else "action", action.state_label if action else "Unavailable" if slot["key"] else "Not assigned",
                                available, reason, request, slot.get("value")))
    return FavoriteSnapshot(tuple(slots), tuple(sorted(options.values(), key=lambda item: (item.label.casefold(), item.key))),
                            token, readable and self.configurable(), valid)

  def save(self, slots, expected_revision, *, authorized=lambda: True):
    if type(expected_revision) is not str:
      raise ValueError("Invalid Quick Select revision")
    normalized = validate_slots(slots)
    existing, raw, readable, _valid = read_slots(self.params)
    if not readable:
      raise OSError("Saved Quick Select are unavailable")
    if revision(raw) != expected_revision:
      raise FavoritesChanged("Quick Select changed. Reload before saving.")
    options = self.actions()
    for index, slot in enumerate(normalized):
      if slot["key"] is not None and slot["key"] not in options:
        previous = existing[index]
        if slot["key"] != previous["key"] or slot.get("value") != previous.get("value"):
          raise ValueError("Unsupported favorite control")
    encoded = json.dumps(normalized, separators=(",", ":"), allow_nan=False).encode()
    if len(encoded) > MAX_BYTES:
      raise ValueError("Quick Select are too large")
    result = commit_exact(self.params, key=FAVORITE_SLOTS_PARAM, max_bytes=MAX_BYTES, raw=encoded, expected=raw,
                          authorized=lambda: self.configurable() and authorized(), temp_prefix=".favorites-")
    if not result.committed or not result.verified:
      raise FavoritesChanged("Quick Select could not be saved. Reload before trying again.")
    return self.snapshot()

  def configure_index(self, index, key, expected_revision, *, enabled=True, show_onroad=True, label=None):
    if type(index) is not int or not 0 <= index < FAVORITE_SLOT_COUNT:
      return False
    saved, _raw, readable, _valid = read_slots(self.params)
    if not readable:
      return False
    options = self.actions()
    if key is not None and key not in options:
      return False
    action = options.get(key)
    saved[index] = {"enabled": enabled if key else False, "show_onroad": show_onroad if key else False,
                    "key": key, "label": (label if label is not None else action.label if action else "")[:32]}
    try:
      self.save(saved, expected_revision)
      return True
    except (FavoritesChanged, OSError, ValueError):
      return False

  def clear_index(self, index, expected_revision):
    return self.configure_index(index, None, expected_revision)

  def invoke(self, request):
    if not isinstance(request, FavoriteRequest) or type(request.index) is not int or not 0 <= request.index < FAVORITE_SLOT_COUNT:
      return FavoriteResult(False, "Quick Select is unavailable")
    slots, raw, readable, valid = read_slots(self.params)
    slot = slots[request.index]
    if not readable or not valid or revision(raw) != request.revision or slot["key"] != request.key or not slot["enabled"]:
      return FavoriteResult(False, "Quick Select changed. Try again.")
    action = self.actions().get(request.key)
    if action is None:
      return FavoriteResult(False, "This saved control is not available in this build")
    if not action.available or action.invoke is None:
      return FavoriteResult(False, action.reason or "Quick Select is unavailable")
    if action.token != request.action_token:
      return FavoriteResult(False, "Control state changed. Try again.")
    current, fresh = read_saved(self.params, FAVORITE_SLOTS_PARAM, MAX_BYTES)
    if not fresh or current != raw:
      return FavoriteResult(False, "Quick Select changed. Try again.")
    try:
      if not action.invoke():
        return FavoriteResult(False, "Control is unavailable or changed. Try again.")
      updated = self.actions().get(request.key)
      return FavoriteResult(True, action.label, updated.state_label if updated else "Done")
    except (OSError, RuntimeError, ValueError, TypeError):
      return FavoriteResult(False, "Control could not be changed")
