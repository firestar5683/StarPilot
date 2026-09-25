"""Vehicle-scoped user choice, independent of learning compatibility and results."""

from dataclasses import dataclass
import json

from openpilot.starpilot.saved_source import read_saved

KEY = 'SteeringLearningPreferences'
MAX_BYTES = 4096
LEGACY_KEY = 'ForceAutoTuneOff'


@dataclass(frozen=True)
class LearningPreference:
  enabled: bool
  valid: bool
  source: str
  raw: bytes | None


def _identity(CP):
  brand, fingerprint = str(CP.brand), str(CP.carFingerprint)
  if not brand or not fingerprint or len(brand) > 64 or len(fingerprint) > 256:
    raise ValueError('Invalid vehicle identity')
  return brand, fingerprint


def _unique(pairs):
  result = {}
  for key, value in pairs:
    if key in result:
      raise ValueError('Duplicate field')
    result[key] = value
  return result


def _decode(raw):
  if raw is None:
    return {'version': 1, 'vehicles': {}}
  if not raw or len(raw) > MAX_BYTES:
    raise ValueError('Invalid preference size')
  try:
    document = json.loads(raw, object_pairs_hook=_unique)
  except RecursionError as error:
    raise ValueError('Preference nesting exceeds parser limits') from error
  if (not isinstance(document, dict) or set(document) != {'version', 'vehicles'} or
      type(document['version']) is not int or document['version'] != 1 or
      not isinstance(document['vehicles'], dict)):
    raise ValueError('Invalid preference document')
  count = 0
  for brand, vehicles in document['vehicles'].items():
    if not brand or len(brand) > 64 or not isinstance(vehicles, dict):
      raise ValueError('Invalid preference brand')
    for fingerprint, enabled in vehicles.items():
      if not fingerprint or len(fingerprint) > 256 or type(enabled) is not bool:
        raise ValueError('Invalid vehicle preference')
      count += 1
  if count > 64:
    raise ValueError('Too many vehicle preferences')
  return document


def read_preference(params, CP, *, legacy_snapshot=None) -> LearningPreference:
  raw, readable = read_saved(params, KEY, MAX_BYTES)
  try:
    if not readable:
      raise ValueError('Unreadable preferences')
    brand, fingerprint = _identity(CP)
    vehicles = _decode(raw)['vehicles']
    if fingerprint in vehicles.get(brand, {}):
      return LearningPreference(vehicles[brand][fingerprint], True, 'scope', raw)
    legacy, readable = read_saved(params, LEGACY_KEY, 1) if legacy_snapshot is None else legacy_snapshot
    if not readable or legacy not in (None, b'0', b'1'):
      raise ValueError('Invalid legacy preference')
    return LearningPreference(legacy != b'1', True, 'default' if legacy is None else 'legacy', raw)
  except (AttributeError, TypeError, ValueError, UnicodeError):
    return LearningPreference(False, False, 'invalid', raw)


def replace_preference(raw: bytes | None, CP, enabled: bool) -> bytes:
  if type(enabled) is not bool:
    raise ValueError('Invalid preference')
  brand, fingerprint = _identity(CP)
  document = _decode(raw)
  document['vehicles'].setdefault(brand, {})[fingerprint] = enabled
  encoded = json.dumps(document, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
  _decode(encoded)
  return encoded
