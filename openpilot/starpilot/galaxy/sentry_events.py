"""Bounded, read-only projection of local Sentry motion metadata."""

import json
import re
from typing import Protocol

from openpilot.starpilot.sentry_mode.storage import EventStore, StorageUnavailable


MAX_RESPONSE_BYTES = 128 * 1024
ID = re.compile(r"[0-9a-f]{32}\Z")


class SentryEventsUnavailable(Exception):
  pass


class EventSnapshotSource(Protocol):
  def snapshot(self) -> dict: ...


class SentryEvents:
  def __init__(self, store: EventSnapshotSource | None = None):
    self.store = store if store is not None else EventStore()

  def snapshot(self) -> dict:
    try:
      source = self.store.snapshot()
      if (type(source) is not dict or type(source.get("version")) is not int or source["version"] != 1 or
          type(source.get("incomplete")) is not bool or type(source.get("capacity")) is not int or source["capacity"] != 512 or
          type(source.get("events")) is not list or len(source["events"]) > 512):
        raise ValueError("Invalid motion inventory")
      events = []
      for value in source["events"]:
        if (type(value) is not dict or type(value.get("eventId")) is not str or
            ID.fullmatch(value["eventId"]) is None or type(value.get("kind")) is not str or
            value["kind"] not in ("warning", "alarm", "selfie") or
            type(value.get("wallTimeNs")) is not int or not 0 < value["wallTimeNs"] < 2**63):
          raise ValueError("Invalid motion event")
        events.append({"eventId": value["eventId"], "kind": value["kind"],
                       "systemTimeMs": value["wallTimeNs"] // 1_000_000,
                       "images": self.store.images(value["eventId"]) if hasattr(self.store, "images") else []})
      result = {"schemaVersion": 1, "source": "local", "scanIncomplete": source["incomplete"],
                "capacity": source["capacity"], "events": events}
      if len(json.dumps(result, separators=(",", ":")).encode()) > MAX_RESPONSE_BYTES:
        raise ValueError("Motion response exceeds limit")
      return result
    except (StorageUnavailable, OSError, ValueError, TypeError, OverflowError, RecursionError) as error:
      raise SentryEventsUnavailable from error

  def image(self, event_id, camera):
    try:
      return self.store.image(event_id, camera)
    except (OSError, StorageUnavailable, AttributeError) as error:
      raise SentryEventsUnavailable from error
