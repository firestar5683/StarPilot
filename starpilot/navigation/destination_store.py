from __future__ import annotations

import json
from typing import Any

RECENT_DESTINATIONS_LIMIT = 10


def _coerce_float(value: Any) -> float | None:
  try:
    return float(value)
  except (TypeError, ValueError):
    return None


def normalize_destination_payload(payload: Any) -> dict[str, Any] | None:
  if not isinstance(payload, dict):
    return None

  name = str(payload.get("place_name") or payload.get("name") or "").strip()
  latitude = _coerce_float(payload.get("latitude"))
  longitude = _coerce_float(payload.get("longitude"))

  if not name or latitude is None or longitude is None:
    return None

  return {
    "name": name,
    "place_name": name,
    "latitude": latitude,
    "longitude": longitude,
  }


def parse_destination_json(raw_value: str | bytes | None) -> dict[str, Any] | None:
  if not raw_value:
    return None

  try:
    payload = json.loads(raw_value)
  except (TypeError, ValueError, json.JSONDecodeError):
    return None

  return normalize_destination_payload(payload)


def normalize_recent_destination_entry(entry: Any) -> dict[str, Any] | None:
  if not isinstance(entry, dict):
    return None

  place_name = str(entry.get("place_name") or entry.get("name") or "").strip()
  if not place_name:
    return None

  normalized: dict[str, Any] = {"place_name": place_name}
  latitude = _coerce_float(entry.get("latitude"))
  longitude = _coerce_float(entry.get("longitude"))
  if latitude is not None and longitude is not None:
    normalized["latitude"] = latitude
    normalized["longitude"] = longitude
    normalized["name"] = place_name

  return normalized


def load_recent_destinations(raw_value: str | bytes | None) -> list[dict[str, Any]]:
  if not raw_value:
    return []

  try:
    payload = json.loads(raw_value)
  except (TypeError, ValueError, json.JSONDecodeError):
    return []

  if not isinstance(payload, list):
    return []

  normalized: list[dict[str, Any]] = []
  for entry in payload:
    recent = normalize_recent_destination_entry(entry)
    if recent is not None:
      normalized.append(recent)
  return normalized


def update_recent_destinations(raw_value: str | bytes | None, destination: dict[str, Any], limit: int = RECENT_DESTINATIONS_LIMIT) -> list[dict[str, Any]]:
  normalized_destination = normalize_destination_payload(destination)
  if normalized_destination is None:
    return load_recent_destinations(raw_value)[:limit]

  current = load_recent_destinations(raw_value)
  updated = [normalize_recent_destination_entry(normalized_destination)]
  seen = {normalized_destination["place_name"].casefold()}

  for entry in current:
    place_name = entry["place_name"].casefold()
    if place_name in seen:
      continue
    seen.add(place_name)
    updated.append(entry)
    if len(updated) >= limit:
      break

  return [entry for entry in updated if entry is not None]
