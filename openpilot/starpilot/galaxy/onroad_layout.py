import hashlib
import json
from collections.abc import Callable

from openpilot.starpilot.saved_document import commit_exact
from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.ui.onroad_customization import (
  MAX_BYTES, PARAM_KEY, customization_metadata, decode_document, default_document, validate_document,
)


class LayoutChanged(Exception):
  pass


def _revision(raw: bytes | None) -> str:
  return hashlib.sha256(b"\x00" if raw is None else b"\x01" + raw).hexdigest()


class OnroadLayoutOwner:
  def __init__(self, params, parked: Callable[[], bool]):
    self.params = params
    self.parked = parked

  def snapshot(self) -> dict:
    raw, readable = read_saved(self.params, PARAM_KEY, MAX_BYTES)
    valid = readable
    document = default_document()
    if raw is not None:
      try:
        document = decode_document(raw)
      except (ValueError, TypeError, UnicodeError, RecursionError):
        valid = False
    return {"document": document, "defaults": default_document(), "revision": _revision(raw),
            "metadata": customization_metadata(), "editable": readable and self.parked(),
            "valid": valid, "activeProfile": None}

  def save(self, payload: dict, *, session_valid: Callable[[], bool]) -> dict:
    if type(payload) is not dict or set(payload) != {"revision", "document"} or type(payload["revision"]) is not str:
      raise ValueError("Invalid layout request")
    document = validate_document(payload["document"])
    encoded = json.dumps(document, separators=(",", ":"), allow_nan=False).encode()
    if len(encoded) > MAX_BYTES:
      raise ValueError("Layout is too large")
    source, readable = read_saved(self.params, PARAM_KEY, MAX_BYTES)
    if not readable:
      raise OSError("Saved layout is unavailable")
    if payload["revision"] != _revision(source):
      raise LayoutChanged("Saved layout changed; reload before saving")
    result = commit_exact(self.params, key=PARAM_KEY, max_bytes=MAX_BYTES, raw=encoded, expected=source,
                          authorized=lambda: session_valid() and self.parked(), temp_prefix=".onroad-layout-")
    if not result.committed or not result.verified:
      raise LayoutChanged("Layout could not be saved; check that the device is parked and reload")
    return self.snapshot()
