"""Single-writer cumulative checkpoints; Galaxy opens SQLite read-only.

A restart creates a new drive fragment, never replays a retained sample. Prior
unclosed fragments remain incomplete. History survives model/route deletion.
"""
import json
import math
from pathlib import Path
import sqlite3
import time

from openpilot.starpilot.common.model_stats import COUNTERS, DEFINITION_VERSION, empty_stats, rates, measurement_policy, apply_definition_policy

DEFAULT_PATH = Path('/data/starpilot/model_stats.sqlite')
SCHEMA_VERSION = 1


ACTIVE_DRIVES = """WITH superseded AS (
  SELECT j.value AS id FROM drives, json_each(drives.state, '$.supersedes') AS j WHERE j.type='text' AND j.value != drives.id
), active_drives AS (
  SELECT * FROM drives WHERE id NOT IN (SELECT id FROM superseded)
) """



class Store:
  def __init__(self, path=DEFAULT_PATH):
    self.path = Path(path)
    self.path.parent.mkdir(parents=True, exist_ok=True)
    self.db = sqlite3.connect(self.path, timeout=0.1)
    version = self.db.execute('PRAGMA user_version').fetchone()[0]
    if version not in (0, SCHEMA_VERSION):
      self.db.close()
      raise ValueError('Unsupported model statistics schema; database not replaced')
    if version == 0 and self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
      self.db.close()
      raise ValueError('Unversioned database; refusing to overwrite')
    self.db.execute('PRAGMA journal_mode=WAL')
    self.db.execute('PRAGMA synchronous=FULL')
    with self.db:
      self.db.execute('CREATE TABLE IF NOT EXISTS drives (id TEXT PRIMARY KEY, started REAL NOT NULL, '
                      'updated REAL NOT NULL, complete INTEGER NOT NULL, sequence INTEGER NOT NULL, '
                      'gaps INTEGER NOT NULL, state TEXT NOT NULL, software TEXT NOT NULL)')
      columns = ', '.join(f'{key} REAL NOT NULL' for key in COUNTERS)
      self.db.execute(f'CREATE TABLE IF NOT EXISTS metrics (drive TEXT NOT NULL, owner TEXT NOT NULL, '
                      f'mode TEXT NOT NULL, {columns}, PRIMARY KEY(drive, owner, mode))')
      self.db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')

  def checkpoint(self, drive, started, snapshot, complete=False, software='', now=None):
    now = time.time() if now is None else now
    with self.db:
      prior = self.db.execute('SELECT sequence, complete, state, updated FROM drives WHERE id=?', (drive,)).fetchone()
      if prior and (snapshot['sequence'] < prior[0] or prior[1]):
        return
      if prior and snapshot['sequence'] == prior[0]:
        # A heartbeat is not evidence of a fresh carState. Still allow finalising
        # a drive without a new sample, but keep its last telemetry write time.
        if complete:
          self.db.execute('UPDATE drives SET complete=1 WHERE id=?', (drive,))
        return
      # A stream-break revision persists metadata without refreshing telemetry.
      if prior and snapshot.get('lastTime') == json.loads(prior[2]).get('lastTime'):
        now = prior[3]
      self.db.execute('INSERT INTO drives VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET '
                      'updated=excluded.updated, complete=excluded.complete, sequence=excluded.sequence, '
                      'gaps=excluded.gaps, state=excluded.state',
                      (drive, started, now, int(complete), snapshot['sequence'], snapshot['gaps'],
                       json.dumps(snapshot, allow_nan=False), software))
      fields = ', '.join(COUNTERS)
      assignments = ', '.join(f'{key}=excluded.{key}' for key in COUNTERS)
      for row in snapshot['metrics']:
        self.db.execute(f'INSERT INTO metrics (drive, owner, mode, {fields}) VALUES '
                        f'({", ".join("?" for _ in range(3 + len(COUNTERS)))}) '
                        f'ON CONFLICT(drive, owner, mode) DO UPDATE SET {assignments}',
                        (drive, row['owner'], row['mode'], *(row[key] for key in COUNTERS)))

  def close(self):
    self.db.close()


def read_stats(path=DEFAULT_PATH, *, model=None, mode='all', period='all', limit=50, offset=0, history=True):
  if period not in ('all', '7', '30'):
    raise ValueError('period must be all/7/30')
  cutoff = 0 if period == 'all' else time.time() - int(period) * 86400
  if mode not in ('all', 'full', 'aol') or not 1 <= limit <= 200 or offset < 0:
    raise ValueError('mode must be all/full/aol; limit 1..200; offset >= 0')
  result = {'schemaVersion': SCHEMA_VERSION, 'definitionVersion': None, 'currentDefinitionVersion': DEFINITION_VERSION,
            'available': False, 'status': 'not_started', 'models': {}, 'pairs': [],
            'history': [], 'driveSummaries': [], 'driveSummariesHasMore': False, 'recordedSince': None, 'lastUpdated': None, 'gaps': 0,
            'incompleteDrives': 0, 'trackingStatus': 'not_recorded', 'currentRuntime': None, 'coverageLoss': False,
            'period': period, 'periodPolicy': 'drive_start', 'mode': mode, 'comparisons': [], 'historyTotal': 0, 'hasMore': False}
  if not Path(path).exists():
    return result
  try:
    db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=0.1)
    try:
      if db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
        raise ValueError('Unsupported schema')
      db.row_factory = sqlite3.Row
      # A read transaction makes aggregate totals and history one coherent snapshot.
      db.execute('BEGIN')
      health = db.execute(ACTIVE_DRIVES + 'SELECT MIN(started), MAX(updated), COALESCE(SUM(gaps),0), '
                          'COALESCE(SUM(NOT complete),0) FROM active_drives').fetchone()
      result.update(available=True, status='ok', recordedSince=health[0], lastUpdated=health[1],
                    gaps=health[2], incompleteDrives=health[3])
      result['trackingStatus'] = 'recording' if health[1] and time.time() - health[1] < 30 else 'inactive'
      latest = db.execute(ACTIVE_DRIVES + 'SELECT state, complete FROM active_drives ORDER BY updated DESC LIMIT 1').fetchone()
      if latest and latest['complete']:
        result['trackingStatus'] = 'inactive'
      if latest and not latest['complete'] and result['trackingStatus'] == 'recording':
        previous = json.loads(latest['state']).get('previous')
        result['currentRuntime'] = json.loads(previous['owner']) if previous and previous.get('owner') else None
        if result['currentRuntime'] is None:
          result['trackingStatus'] = 'telemetry_unavailable'
      result['coverageLoss'] = bool(db.execute(ACTIVE_DRIVES + "SELECT 1 FROM active_drives WHERE json_extract(state, '$.coverageLoss')=1 LIMIT 1").fetchone())
      if result['coverageLoss']:
        result['trackingStatus'] = 'resource_limited'
        result['status'] = 'degraded'
      where = ('WHERE mode != ?' if mode == 'all' else 'WHERE mode = ?') + ' AND started >= ?'
      arg = 'manual' if mode == 'all' else mode
      fields = ', '.join(f'SUM({key}) AS {key}' for key in COUNTERS)
      # Extract policy metadata only, not retained sample states. Keep original
      # counters intact; incompatible definition cohorts cannot produce a rate.
      policy_sql = "json_group_array(DISTINCT json_object('definitionVersion', " \
                   "CASE WHEN json_type(state, '$.definitionVersion') IS NULL THEN 1 ELSE json_extract(state, '$.definitionVersion') END, 'interventionReleaseSeconds', " \
                   "CASE WHEN json_type(state, '$.interventionReleaseSeconds') IS NULL THEN 0.5 ELSE json_extract(state, '$.interventionReleaseSeconds') END)) AS policies"
      aggregates = db.execute(ACTIVE_DRIVES + f'SELECT owner, mode, {fields}, {policy_sql}, MAX(gaps > 0 OR (NOT complete AND updated < ?)) AS incomplete '
                              f'FROM metrics JOIN active_drives AS drives ON drives.id=metrics.drive {where} GROUP BY owner, mode',
                              (time.time() - 30, arg, cutoff)).fetchall()
      pair_map = {}
      all_policies = set()
      for row in aggregates:
        if any(not math.isfinite(row[key]) or row[key] < 0 for key in COUNTERS):
          raise ValueError('Invalid stored counters')
        identity = json.loads(row['owner'])
        ids = [role['modelId'] for role in identity['roles']]
        if not 1 <= len(ids) <= 2:
          raise ValueError('Invalid stored identity')
        if model is not None and model not in ids:
          continue
        policies = {measurement_policy(state) for state in json.loads(row['policies'])}
        all_policies.update(policies)
        comparison_stats = apply_definition_policy({key: row[key] for key in COUNTERS} |
          {'available': True, 'status': 'ok', 'incomplete': bool(row['incomplete']) or result['coverageLoss']}, policies)
        result['comparisons'].append({'identity': identity, 'mode': row['mode'], 'stats': rates(comparison_stats)})
        if len(ids) == 2:
          # A pair is a configuration, not two standalone model performances.
          key = json.dumps(ids)
          target = pair_map.setdefault(key, {'modelIds': ids, 'stats': empty_stats('ok'), 'configurations': []})
        else:
          target = result['models'].setdefault(ids[0], {'stats': empty_stats('ok'), 'configurations': []})
        target.setdefault('_policies', set()).update(policies)
        target['configurations'].append(identity)
        target['stats']['incomplete'] = target['stats']['incomplete'] or bool(row['incomplete']) or result['coverageLoss']
        for key in COUNTERS:
          target['stats'][key] += row[key]
      apply_definition_policy(result, all_policies)
      result['pairs'] = list(pair_map.values())
      for target in list(result['models'].values()) + result['pairs']:
        apply_definition_policy(target['stats'], target.pop('_policies'))
        rates(target['stats'])
      if history:
        # Bind JSON paths/values: no caller-controlled SQL or filesystem paths.
        query = f'SELECT metrics.*, drives.started, drives.updated, drives.complete, drives.gaps, drives.software, drives.state '
        query += f'FROM metrics JOIN active_drives AS drives ON drives.id=metrics.drive {where}'
        args = [arg, cutoff]
        if model is not None:
          query += " AND (json_extract(owner, '$.roles[0].modelId')=? OR json_extract(owner, '$.roles[1].modelId')=?)"
          args += [model, model]
        result['historyTotal'] = db.execute(ACTIVE_DRIVES + 'SELECT COUNT(*) FROM (' + query + ')', args).fetchone()[0]
        rows = db.execute(ACTIVE_DRIVES + query + ' ORDER BY started DESC, drive, owner, mode LIMIT ? OFFSET ?', (*args, limit, offset))
        for row in rows:
          entry = dict(row)
          state = json.loads(entry.pop('state'))
          entry['definitionVersion'] = state.get('definitionVersion', 1)
          entry['interventionReleaseSeconds'] = state.get('interventionReleaseSeconds', 0.5)
          entry['routeName'] = state.get('routeName')
          entry['recovery'] = state.get('recovery')
          entry['identity'] = json.loads(entry.pop('owner'))
          entry['stats'] = rates(apply_definition_policy({key: entry.pop(key) for key in COUNTERS} |
                                 {'available': True, 'status': 'ok',
                                  'incomplete': not bool(entry['complete']) or bool(entry['gaps']) or result['coverageLoss']},
                                 [measurement_policy(state)]))
          result['history'].append(entry)
        result['hasMore'] = offset + len(result['history']) < result['historyTotal']
        # A separate bounded route-level view includes manual-only recordings.
        # No coverage stays unknown; it must not turn into a fabricated zero.
        if model is None and mode == 'all':
          summaries = db.execute(ACTIVE_DRIVES +
            'SELECT drives.*, COUNT(metrics.drive) AS covered, '
            'COALESCE(SUM(interventions),0) AS interventions, COALESCE(SUM(disengagements),0) AS disengagements '
            'FROM active_drives AS drives LEFT JOIN metrics ON metrics.drive=drives.id '
            'WHERE started >= ? GROUP BY drives.id ORDER BY started DESC, drives.id LIMIT ?', (cutoff, limit + 1)).fetchall()
          result['driveSummariesHasMore'] = len(summaries) > limit
          for row in summaries[:limit]:
            state = json.loads(row['state'])
            result['driveSummaries'].append({
              'drive': row['id'], 'started': row['started'], 'updated': row['updated'],
              'complete': row['complete'], 'gaps': row['gaps'], 'routeName': state.get('routeName'),
              'stats': {'available': bool(row['covered']), 'interventions': row['interventions'],
                        'disengagements': row['disengagements'],
                        'incomplete': not bool(row['complete']) or bool(row['gaps']) or result['coverageLoss']}})

    finally:
      db.close()
  except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, IndexError, AttributeError):
    result.update(available=False, status='unavailable', models={}, pairs=[], comparisons=[], history=[], currentRuntime=None,
                  trackingStatus='unavailable', historyTotal=0, hasMore=False, driveSummaries=[], driveSummariesHasMore=False)
  return result
