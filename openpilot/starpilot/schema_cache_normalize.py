"""Explicit offline normalization of caches from this exact compiled schema."""

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import struct

import capnp

from openpilot.starpilot import schema_cache as cache
from openpilot.starpilot.state_migration import (
  _atomic_write, _outside_params, _params_lock, _read_value, _save_snapshot, canonical_json, load_snapshot,
)


EVENT_KEYS = tuple(sorted(key for key, contract in cache.CONTRACTS.items() if contract.service is not None))


class NormalizationError(RuntimeError):
  """No incompatible cache is eligible; an I/O failure may leave a reported partial batch."""


class _EnvelopeSink:
  def put(self, key, value, *, block):
    self.raw = value


def _header(raw):
  start = len(cache.MAGIC) + 4
  size = struct.unpack_from('>I', raw, len(cache.MAGIC))[0]
  return json.loads(raw[start:start + size])


def _values(value):
  if isinstance(value, float):
    return struct.pack('>d', value)  # Preserve signed zero and nonfinite values during comparison.
  if isinstance(value, dict):
    return {key: _values(item) for key, item in value.items()}
  if isinstance(value, list):
    return [_values(item) for item in value]
  return value


def _prepare(key, raw):
  inspected = cache.inspect_cache(key, raw)
  if inspected.status != 'valid' or inspected.payload is None:
    raise NormalizationError(f'{key}: {inspected.status}: {inspected.reason}')
  contract = cache.CONTRACTS[key]
  if contract.service is None:
    raise NormalizationError(f'{key}: only Event caches can be normalized')
  try:
    with contract.root.from_bytes(inspected.payload, traversal_limit_in_words=cache.MAX_PAYLOAD_BYTES // 8) as message:
      # Event.to_dict suppresses union-member decode errors; decode the selected
      # service explicitly before constructing a fresh typed message.
      service_values = getattr(message, contract.service).to_dict()
      decoded = message.to_dict()
      if contract.service not in decoded or _values(decoded[contract.service]) != _values(service_values):
        raise NormalizationError(f'{key}: selected service did not decode completely')
      original_values = _values(decoded)
      if _header(raw)['version'] == 2:
        return raw
      sink = _EnvelopeSink()
      cache.put_cache(sink, key, contract.root.new_message(**decoded), block=True)
    converted = cache.inspect_cache(key, sink.raw)
    if converted.status != 'valid' or converted.payload is None or _header(sink.raw)['version'] != 2:
      raise NormalizationError(f'{key}: current writer did not produce a valid v2 envelope')
    with contract.root.from_bytes(converted.payload, traversal_limit_in_words=cache.MAX_PAYLOAD_BYTES // 8) as message:
      if _values(message.to_dict()) != original_values:
        raise NormalizationError(f'{key}: typed values changed during normalization')
  except (ValueError, TypeError, capnp.KjException) as error:
    raise NormalizationError(f'{key}: typed cache validation failed: {type(error).__name__}') from error
  return sink.raw


def _read(path):
  try:
    return _read_value(path)
  except FileNotFoundError:
    return None


def _identity(raw):
  return None if raw is None else {'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw),
                                 'version': _header(raw)['version'], 'schema_sha256': _header(raw)['schema_sha256']}


def normalize_current_event_caches(params, backup_dir, *, producers_stopped: bool = False):
  """Validate every present Event cache before backing up and writing any cache.

  Run with cache producers stopped, before changing compiled schemas. This cannot
  convert an incompatible v1 cache. It never changes CarParams or read-side APIs.
  The Params lock covers comparisons and atomic replacements; each prepared
  envelope comes from put_cache with a fully decoded current typed message.
  """
  if producers_stopped is not True:
    raise NormalizationError('Stop cache producers before explicitly normalizing caches')
  namespace = Path(params.get_param_path(EVENT_KEYS[0])).parent.absolute()
  storage = Path(backup_dir).absolute()
  _outside_params(namespace, storage)
  with _params_lock(namespace):
    actual = namespace.resolve(strict=True)
    originals = {key: _read(actual / key) for key in EVENT_KEYS}
    prepared = {key: _prepare(key, raw) for key, raw in originals.items() if raw is not None}
    changed = [key for key, raw in prepared.items() if raw != originals[key]]
    report = {
      'format': 'starpilot-current-event-cache-normalization', 'version': 1,
      'recorded_utc': datetime.now(UTC).isoformat(), 'namespace': str(namespace),
      'codec': {'path': cache.__file__, 'sha256': hashlib.sha256(Path(cache.__file__).read_bytes()).hexdigest()},
      'normalizer': {'path': __file__, 'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
      'status': 'unchanged', 'backup': None, 'attempted': [], 'written': [],
      'caches': {key: {'before': _identity(raw), 'after': _identity(prepared.get(key)),
                       'action': 'normalize' if key in changed else 'missing' if raw is None else 'unchanged'}
                 for key, raw in originals.items()},
    }
    if not changed:
      return report
    backup = _save_snapshot({key: raw for key, raw in originals.items() if raw is not None}, storage)
    if load_snapshot(backup) != {key: raw for key, raw in originals.items() if raw is not None}:
      raise NormalizationError('Backup readback differs from original caches')
    report.update(status='prepared', backup=str(backup))
    receipt = backup / 'normalization.json'
    _atomic_write(receipt, canonical_json(report))
    try:
      if namespace.resolve(strict=True) != actual or any(_read(actual / key) != raw for key, raw in originals.items()):
        raise NormalizationError('Cache source changed after validation; no caches were written')
      for key in changed:
        if namespace.resolve(strict=True) != actual or _read(actual / key) != originals[key]:
          raise NormalizationError(f'{key}: source changed before replacement')
        report['attempted'].append(key)
        _atomic_write(receipt, canonical_json(report))
        _atomic_write(actual / key, prepared[key])
        report['written'].append(key)
        if _read(actual / key) != prepared[key] or cache.inspect_cache(key, prepared[key]).status != 'valid':
          raise NormalizationError(f'{key}: exact cache readback failed')
      if any(_read(actual / key) != prepared.get(key) for key in EVENT_KEYS):
        raise NormalizationError('Final cache readback differs from the prepared batch')
      report['status'] = 'normalized'
      _atomic_write(receipt, canonical_json(report))
    except Exception as error:
      report.update(status='failed', error=f'{type(error).__name__}: {error}')
      _atomic_write(receipt, canonical_json(report))
      raise NormalizationError(f'Normalization stopped; originals and partial-write receipt: {backup}') from error
    return report
