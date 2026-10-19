"""Optional learner-only full30 accepted history; restoration is PRIOR only.

Existing legacy rows are preserved in the same bounded Params document. Full
updates use prior-full-hash CAS and native Params byte-exact commit. Never return
an active Profile, publication lease, native permission or restored fit receipt.
"""

from typing import cast

from dataclasses import dataclass, replace
import hashlib
from openpilot.starpilot.flm.full_surface_profile import (
  FullSurfaceEnvelope,
  RESTORE_POLICY,
  envelope_from_dict,
  envelope_dict,
  hex64,
  neutral_coordinates,
)
from openpilot.starpilot.flm.canonical_surface_adapter import full_profile_sha256

MAX_SURFACES = 4
NAMESPACE = 'fullSurfaces'


def validate_rows(rows):
  if type(rows) is not dict or len(rows) > MAX_SURFACES:
    raise ValueError('full profile store bound')
  for key, row in rows.items():
    if not hex64(key) or type(row) is not dict or set(row) != {'current', 'previous', 'validation'} or not hex64(row['validation']):
      raise ValueError('full profile stored row')
    current = envelope_from_dict(row['current'])
    if key != current.scope():
      raise ValueError('full profile scope')
    if row['previous'] is not None:
      if type(row['previous']) is not dict or set(row['previous']) != {'envelope', 'validation'} or not hex64(row['previous']['validation']):
        raise ValueError('rollback validation provenance')
      previous = envelope_from_dict(row['previous']['envelope'])
      if previous.persistent_binding() != current.persistent_binding() or previous.full_profile_sha256 != (
        current.history_full_profile_sha256 if current.operation == 'restore' else current.prior_full_profile_sha256
      ):
        raise ValueError('full profile rollback chain')
  return rows


@dataclass(frozen=True)
class FullSurfacePrior:
  """No Profile/expiry/permission fields; fresh entire-map replay required."""

  envelope: FullSurfaceEnvelope
  historical_only: bool = True


def load_prior(raw, *, binding):
  from openpilot.starpilot.flm.learned_lifecycle import decode

  doc = decode(raw)
  if len(binding) != 8 or not hex64(binding[7]):
    return None
  stable = (binding[0], binding[1], binding[7], binding[3], binding[4], binding[5])
  scope = hashlib.sha256(repr(stable).encode()).hexdigest()
  row = doc.get(NAMESPACE, {}).get(scope)
  if row is None:
    return None
  envelope = envelope_from_dict(row['current'])
  if envelope.persistent_binding() != stable:
    return None
  # Historical values are optimizer/restore targets only. Rebind source context,
  # but never describe them as actual currently accepted target after restart.
  rebound = replace(
    envelope,
    source_epoch=binding[2],
    context_key=binding[6],
    version=1,
    operation='trial',
    history_full_profile_sha256='',
    restore_transaction_sha256='',
    prior_coordinates=envelope.coordinates,
    prior_full_profile_sha256=envelope.full_profile_sha256,
  ).validate()
  return FullSurfacePrior(rebound)


def remember_full(raw, profile, *, validation_sha256):
  from openpilot.starpilot.flm.learned_lifecycle import decode, encode

  envelope = profile.effect_envelope
  if not isinstance(envelope, FullSurfaceEnvelope) or not hex64(validation_sha256):
    raise ValueError('explicit full profile required')
  envelope.validate(profile)
  doc = decode(raw)
  # Explicit versioned wrapper: legacy profiles retained verbatim, never migrated
  # to full surface coordinates or treated as live/accepted new-policy evidence.
  if doc['version'] == 1:
    doc = {'version': 2, 'profiles': doc['profiles'], NAMESPACE: {}}
  rows = cast(dict[str, dict[str, object]], doc[NAMESPACE])
  # Stable settings hashes are opaque: a different reset may also represent a
  # different saved configuration. Never evict another scope by guessing that
  # only reset changed; the fixed store bound fails closed when full.
  row = rows.get(envelope.scope())
  previous = None if row is None else envelope_from_dict(row['current'])
  if envelope.operation == 'restore':
    # Disk authorizes only this historical-target transaction identity. Fresh
    # actual replay/native/current probe is separately mandatory before save.
    if (
      profile.policy != RESTORE_POLICY
      or previous is None
      or previous.persistent_binding() != envelope.persistent_binding()
      or previous.full_profile_sha256 != envelope.history_full_profile_sha256
      or previous.coordinates != envelope.coordinates
    ):
      raise ValueError('restore target does not match stable accepted history')
  else:
    expected = full_profile_sha256(envelope.selected_baseline_revision, neutral_coordinates()) if previous is None else previous.full_profile_sha256
    if envelope.prior_full_profile_sha256 != expected:
      raise ValueError('stale prior full profile CAS')
    expected_values = neutral_coordinates() if previous is None else previous.coordinates
    if envelope.prior_coordinates != expected_values:
      raise ValueError('prior full map does not match accepted history')
  if row is None and len(rows) >= MAX_SURFACES:
    raise ValueError('full profile store full')
  rows[envelope.scope()] = {
    'current': envelope_dict(envelope),
    'previous': None if previous is None else {'envelope': envelope_dict(previous), 'validation': cast(dict[str, object], row)['validation']},
    'validation': validation_sha256,
  }
  return encode(doc)


def rollback_full(raw, *, binding, expected_full_hash):
  from openpilot.starpilot.flm.learned_lifecycle import decode, encode

  doc = decode(raw)
  if len(binding) != 8 or not hex64(binding[7]):
    raise ValueError('stable rollback binding')
  stable = (binding[0], binding[1], binding[7], binding[3], binding[4], binding[5])
  scope = hashlib.sha256(repr(stable).encode()).hexdigest()
  row = doc.get(NAMESPACE, {}).get(scope)
  if row is None:
    raise ValueError('rollback scope missing')
  current = envelope_from_dict(row['current'])
  if current.full_profile_sha256 != expected_full_hash or current.persistent_binding() != stable:
    raise ValueError('rollback CAS/source')
  if row['previous'] is None:
    raise ValueError('no last accepted rollback')
  # A rollback restores historical PRIOR data only. Runtime still needs fresh
  # current physical/native/entire-map controller replay before application.
  previous = row['previous']
  row['current'], row['validation'], row['previous'] = previous['envelope'], previous['validation'], None
  return encode(doc)
