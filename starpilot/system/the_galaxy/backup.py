"""Portable data-only backups. Imported SQL and file paths are never executed."""
import copy
import json
import math
import sqlite3
from pathlib import Path

from openpilot.starpilot.common.model_stats import COUNTERS, parse_identity, measurement_policy
from openpilot.starpilot.common.model_stats_store import SCHEMA_VERSION, Store

FORMAT = 'starpilot-backup'
VERSION = 1
MAX_BYTES = 64 * 1024 * 1024
HISTORY_KEYS = ('GalaxyDashboardStats', 'ModelDrivesAndScores', 'UserFavorites', 'ModelSortMode', 'StarPilotStats', 'ApiCache_DriveStats')
DRIVE_FIELDS = ('id', 'started', 'updated', 'complete', 'sequence', 'gaps', 'state', 'software')
METRIC_FIELDS = ('drive', 'owner', 'mode', *COUNTERS)


def json_document(value):
  if isinstance(value, (str, bytes)):
    value = json.loads(value)
  # Reject non-finite values anywhere, including nested history documents.
  json.dumps(value, allow_nan=False)
  return value


def export_statistics(path):
  result = {'schemaVersion': SCHEMA_VERSION, 'drives': [], 'metrics': []}
  if not Path(path).exists():
    return result
  with sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=5) as db:
    db.execute('BEGIN')
    if db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
      raise ValueError('Unsupported model statistics schema')
    for name, fields in [('drives', DRIVE_FIELDS), ('metrics', METRIC_FIELDS)]:
      result[name] = [dict(zip(fields, row)) for row in db.execute(f'SELECT {", ".join(fields)} FROM {name}')]
  return validate_statistics(result)


def _number(value, integer=False):
  try:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0 and (not integer or int(value) == value)
  except OverflowError:
    return False


def _metric_values(row):
  if not isinstance(row, dict) or set(row) != {'owner', 'mode', *COUNTERS}:
    raise ValueError('Invalid checkpoint metric')
  owner = parse_identity(row['owner'])
  if owner is None or row['mode'] not in ('full', 'aol', 'manual'):
    raise ValueError('Invalid metric ownership')
  if any(not _number(row[k], not k.endswith('Meters')) for k in COUNTERS):
    raise ValueError('Invalid metric counters')
  return (owner, row['mode']), tuple(row[k] for k in COUNTERS)


def _validate_supersession(drives, states, checkpoints):
  """Recovery references must describe a complete, non-decreasing replacement.

  This validates internal consistency, not authenticity of imported history.
  Original records remain present in every supported recovery export.
  """
  replaced_by = {}
  for drive, state in states.items():
    refs = state.get('supersedes', [])
    if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs) or len(set(refs)) != len(refs):
      raise ValueError('Invalid recovery references')
    if not refs:
      continue
    recovery, route = state.get('recovery'), state.get('routeName')
    if (not isinstance(recovery, dict) or type(recovery.get('version')) is not int or recovery['version'] != 1
        or recovery.get('source') != 'retained-rlog' or not isinstance(route, str) or not 0 < len(route) <= 128
        or drive != 'recovered:' + route or drives[drive]['complete'] != 1
        or not isinstance(recovery.get('digest'), str) or len(recovery['digest']) != 64
        or any(c not in '0123456789abcdef' for c in recovery['digest'])):
      raise ValueError('Invalid recovery provenance')
    totals = {}
    policy = measurement_policy(state)
    for ref in refs:
      if ref == drive or ref not in states or ref in replaced_by:
        raise ValueError('Recovery references must be unique and contained in this backup')
      replaced_by[ref] = drive
      old = states[ref]
      if old.get('coverageLoss') or policy is None or measurement_policy(old) != policy:
        raise ValueError('Recovery cannot hide coverage loss or change measurement definitions')
      old_route = old.get('routeName')
      if old_route not in (None, route) or (old_route is None and (
          drives[ref]['started'] < drives[drive]['started'] - 2 or drives[ref]['updated'] > drives[drive]['updated'] + 2)):
        raise ValueError('Recovery references an unrelated route')
      for key, values in checkpoints[ref].items():
        total = totals.setdefault(key, [0] * len(COUNTERS))
        for i, value in enumerate(values):
          total[i] += value
    current = checkpoints[drive]
    if any(key not in current or any(new < old - 1e-5 for old, new in zip(values, current[key])) for key, values in totals.items()):
      raise ValueError('Recovery would reduce accepted counters')
  # Iterative traversal keeps deeply nested imported graphs off the call stack.
  complete = set()
  for start in replaced_by:
    path, node = set(), start
    while node in replaced_by and node not in complete:
      if node in path:
        raise ValueError('Cyclic recovery references')
      path.add(node)
      node = replaced_by[node]
    complete.update(path)


def validate_statistics(data):
  if not isinstance(data, dict) or type(data.get('schemaVersion')) is not int or data.get('schemaVersion') != SCHEMA_VERSION:
    raise ValueError('Unsupported model statistics schema')
  drives, metrics = data.get('drives'), data.get('metrics')
  if not isinstance(drives, list) or not isinstance(metrics, list) or len(drives) > 100000 or len(metrics) > 500000:
    raise ValueError('Invalid model history')
  ids, checkpoints, states, drive_rows, stored = set(), {}, {}, {}, {}
  for row in drives:
    if not isinstance(row, dict) or set(row) != set(DRIVE_FIELDS):
      raise ValueError('Invalid drive record')
    if not isinstance(row['id'], str) or not 0 < len(row['id']) <= 512 or row['id'] in ids:
      raise ValueError('Duplicate or invalid drive identity')
    ids.add(row['id'])
    if any(not _number(row[k], k in ('complete', 'sequence', 'gaps')) for k in ('started', 'updated', 'complete', 'sequence', 'gaps')) or row['complete'] not in (0, 1):
      raise ValueError('Invalid drive counters')
    if not isinstance(row['software'], str) or not isinstance(row['state'], str) or not isinstance(json_document(row['state']), dict):
      raise ValueError('Invalid drive state')
    state = json_document(row['state'])
    if (any(type(state.get(k)) is not int or not 0 <= state[k] <= 2**63 - 1 for k in ('sequence', 'gaps'))
        or state['sequence'] != row['sequence'] or state['gaps'] != row['gaps'] or not isinstance(state.get('metrics'), list)):
      raise ValueError('Inconsistent drive checkpoint')
    previous = state.get('previous')
    if previous is not None and (not isinstance(previous, dict) or (previous.get('owner') is not None and parse_identity(previous['owner']) is None)):
      raise ValueError('Invalid drive provenance')
    checkpoint = {}
    for metric in state['metrics']:
      key, values = _metric_values(metric)
      if key in checkpoint:
        raise ValueError('Duplicate checkpoint metric')
      checkpoint[key] = values
    checkpoints[row['id']], states[row['id']], drive_rows[row['id']] = checkpoint, state, row
  for row in metrics:
    if not isinstance(row, dict) or set(row) != set(METRIC_FIELDS):
      raise ValueError('Invalid model metric')
    if not isinstance(row['drive'], str) or row['drive'] not in ids:
      raise ValueError('Invalid metric ownership')
    key, values = _metric_values({k: row[k] for k in METRIC_FIELDS if k != 'drive'})
    current = stored.setdefault(row['drive'], {})
    if key in current:
      raise ValueError('Duplicate metric counters')
    current[key] = values
  if any(checkpoints[drive] != stored.get(drive, {}) for drive in ids):
    raise ValueError('Checkpoint and stored metric counters disagree')
  _validate_supersession(drive_rows, states, checkpoints)
  return data


def merge_statistics(db, data):
  """Retain existing drive identities intact; repeated imports never add counts."""
  validate_statistics(data)
  existing = {r[0] for r in db.execute('SELECT id FROM drives')}
  added = {r['id'] for r in data['drives']} - existing
  # Two independent recovery exports may agree on the original fragment but
  # supply different replacements. Validate against retained edges as well as
  # within the imported graph, otherwise both replacements would be counted.
  retained_references = {row[0] for row in db.execute(
    "SELECT j.value FROM drives, json_each(drives.state, '$.supersedes') AS j WHERE j.type='text' AND j.value != drives.id")}
  incoming = {row['id']: row for row in data['drives']}
  incoming_metrics = {}
  for row in data['metrics']:
    incoming_metrics.setdefault(row['drive'], set()).add(tuple(row[k] for k in METRIC_FIELDS))
  for drive in added:
    for ref in json_document(incoming[drive]['state']).get('supersedes', []):
      if ref in retained_references:
        raise ValueError('Recovery conflicts with a retained replacement for drive: ' + ref)
      if ref in existing:
        retained = dict(zip(DRIVE_FIELDS, db.execute('SELECT ' + ','.join(DRIVE_FIELDS) + ' FROM drives WHERE id=?', (ref,)).fetchone()))
        if retained != incoming[ref]:
          raise ValueError('Recovery conflicts with a different retained drive: ' + ref)
        retained_metrics = {tuple(row) for row in db.execute('SELECT ' + ','.join(METRIC_FIELDS) + ' FROM metrics WHERE drive=?', (ref,))}
        supplied_metrics = incoming_metrics.get(ref, set())
        if retained_metrics != supplied_metrics:
          raise ValueError('Recovery conflicts with retained metric counters: ' + ref)
  for table, fields, rows in [('drives', DRIVE_FIELDS, data['drives']), ('metrics', METRIC_FIELDS, data['metrics'])]:
    for row in rows:
      if row['id' if table == 'drives' else 'drive'] in added:
        db.execute(f'INSERT INTO {table} ({", ".join(fields)}) VALUES ({", ".join("?" for _ in fields)})', [row[k] for k in fields])
  return len(added)


def merge_history(saved, current):
  """Union records by identity. Existing values win conflicts; never sum totals."""
  if isinstance(saved, dict) and isinstance(current, dict):
    result = copy.deepcopy(saved)
    for key, value in current.items():
      result[key] = merge_history(result[key], value) if key in result else copy.deepcopy(value)
    return result
  if isinstance(saved, list) and isinstance(current, list):
    return copy.deepcopy(current + [v for v in saved if v not in current])
  return copy.deepcopy(current)


class RestoreError(OSError):
  """An I/O failure, optionally with an incomplete settings rollback."""


def _verify_setting(params, key, value):
  expected = value
  # Params serializes/coerces according to its compiled registry. Compare the
  # corresponding typed readback, including its empty-value/absent convention.
  if value is not None and hasattr(params, '_put_cast') and hasattr(params, 'cpp2python'):
    encoded = params._put_cast(key, value)
    expected = params.cpp2python(key, encoded) if encoded else None
  actual = params.get(key)
  if type(actual) is not type(expected) or actual != expected:
    raise RestoreError('Setting write could not be verified: ' + key)


def apply_restore(params, settings, history, statistics, db_path, backup_dir, parked):
  """Validate before entry. Roll back params and the SQL transaction on failure."""
  parked()
  validate_statistics(statistics)
  updates = dict(settings)
  for key, value in history.items():
    old = params.get(key)
    if key in ('GalaxyDashboardStats', 'ModelDrivesAndScores', 'StarPilotStats', 'ApiCache_DriveStats'):
      old = json_document(old) if old not in (None, '', b'') else {}
      merged = merge_history(value, old)
      if key == 'GalaxyDashboardStats':
        merged['routes'] = {**value.get('routes', {}), **old.get('routes', {})}
      if key == 'StarPilotStats':
        def cumulative(saved, current):
          if isinstance(saved, dict) and isinstance(current, dict):
            return {k: cumulative(saved[k], current[k]) if k in saved and k in current else copy.deepcopy(current[k] if k in current else saved[k]) for k in saved.keys() | current.keys()}
          if _number(saved) and _number(current):
            return max(saved, current)
          return copy.deepcopy(current)
        merged = cumulative(value, old)
        if 'Month' in old:
          merged['Month'] = old['Month']
          if value.get('Month') != old['Month']:
            merged['CurrentMonthsMeters'] = old.get('CurrentMonthsMeters', 0)
      value = merged
    elif key == 'UserFavorites' and old not in (None, '', b''):
      old = old.decode() if isinstance(old, bytes) else old
      value = ','.join(dict.fromkeys(v.strip() for v in (str(old) + ',' + str(value)).split(',') if v.strip()))
    updates[key] = value
  old_values = {key: params.get(key) for key in updates}
  backup_dir = Path(backup_dir)
  backup_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
  # Raw values preserve exact types/bytes for an operator recovery after power loss.
  import base64
  raw = {k: {'bytes': base64.b64encode(v).decode()} if isinstance(v, bytes) else {'value': v} for k, v in old_values.items()}
  recovery = backup_dir / 'settings-before.json'
  recovery.write_text(json.dumps(raw, allow_nan=False))
  recovery.chmod(0o600)
  store = Store(db_path)
  try:
    with sqlite3.connect(backup_dir / 'model_stats-before.sqlite') as snapshot:
      store.db.backup(snapshot)
    store.db.execute('BEGIN IMMEDIATE')
    added = merge_statistics(store.db, statistics)
    try:
      parked()
      for key, value in updates.items():
        parked()
        params.put(key, value)
        _verify_setting(params, key, value)
      parked()
      store.db.commit()
    except Exception as error:
      failures = []
      try:
        store.db.rollback()
      except Exception:
        failures.append('statistics transaction')
      for key, value in old_values.items():
        try:
          if value is None:
            params.remove(key)
          else:
            params.put(key, value)
          _verify_setting(params, key, value)
        except Exception:
          failures.append(key)
      if failures:
        raise RestoreError('Restore failed; rollback incomplete for ' + ', '.join(failures) +
                           '. A recovery copy is retained on the device.') from error
      raise
  finally:
    store.close()
  return {'restoredCount': len(settings), 'addedDrives': added, 'existingDrives': len(statistics['drives']) - added}
