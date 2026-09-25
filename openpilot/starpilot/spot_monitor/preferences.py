"""Strict default-off saved V-ASM observation settings; no legacy adoption."""

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.spot_monitor.policy import Annotation, decode_annotation, encode_annotation


KEY = "VASMPreferences"
MAX_BYTES = 8192


@dataclass(frozen=True)
class Preferences:
  enabled: bool = False
  annotation: Annotation | None = None
  confidence: float = 0.94
  smooth_seconds: float = 0.2


@dataclass(frozen=True)
class SavedPreferences:
  raw: bytes | None
  readable: bool
  valid: bool
  preferences: Preferences = Preferences()

  @property
  def fingerprint(self) -> str:
    return hashlib.sha256(self.raw or b"").hexdigest() if self.valid else ""


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
  result: dict[str, object] = {}
  for key, value in pairs:
    if key in result:
      raise ValueError("duplicate V-ASM preference")
    result[key] = value
  return result


def decode(raw: bytes) -> Preferences | None:
  if type(raw) is not bytes or len(raw) > MAX_BYTES:
    return None
  try:
    data = json.loads(raw, object_pairs_hook=_unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
    if type(data) is not dict or set(data) != {"version", "enabled", "annotation", "confidence", "smoothSeconds"}:
      return None
    if type(data["version"]) is not int or data["version"] != 1 or type(data["enabled"]) is not bool:
      return None
    confidence, smooth = data["confidence"], data["smoothSeconds"]
    if type(confidence) not in (int, float) or type(smooth) not in (int, float) or not math.isfinite(confidence) or \
       not math.isfinite(smooth) or not 0.8 <= confidence <= 1.0 or not 0.01 <= smooth <= 0.5:
      return None
    annotation = data["annotation"]
    if annotation is None:
      return Preferences(False, None, float(confidence), float(smooth)) if not data["enabled"] else None
    if type(annotation) is not dict:
      return None
    annotation_raw = json.dumps(annotation, separators=(",", ":"), allow_nan=False).encode()
    return Preferences(data["enabled"], decode_annotation(annotation_raw), float(confidence), float(smooth))
  except (UnicodeDecodeError, ValueError, TypeError, OverflowError, RecursionError):
    return None


def encode(preferences: Preferences) -> bytes:
  if type(preferences) is not Preferences or type(preferences.enabled) is not bool or \
     (preferences.enabled and preferences.annotation is None) or type(preferences.confidence) not in (int, float) or \
     type(preferences.smooth_seconds) not in (int, float) or not math.isfinite(preferences.confidence) or \
     not math.isfinite(preferences.smooth_seconds) or not 0.8 <= preferences.confidence <= 1.0 or \
     not 0.01 <= preferences.smooth_seconds <= 0.5:
    raise ValueError("Invalid V-ASM preferences")
  annotation = json.loads(encode_annotation(preferences.annotation)) if preferences.annotation is not None else None
  raw = json.dumps({"version": 1, "enabled": preferences.enabled, "annotation": annotation,
                    "confidence": preferences.confidence, "smoothSeconds": preferences.smooth_seconds},
                   sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
  if len(raw) > MAX_BYTES:
    raise ValueError("Oversized V-ASM preferences")
  return raw


def read_preferences(params: Any) -> SavedPreferences:
  raw, readable = read_saved(params, KEY, MAX_BYTES)
  if not readable:
    return SavedPreferences(raw, False, False)
  if raw is None:
    return SavedPreferences(None, True, True)
  preferences = decode(raw)
  return SavedPreferences(raw, True, preferences is not None, preferences or Preferences())


def enabled(params: Any, *, development: bool) -> bool:
  if not development:
    return False
  saved = read_preferences(params)
  return saved.readable and saved.valid and saved.preferences.enabled
