"""Explicit off-road log recovery; never imported or run by the live observer.

The caller reviews/reconstructs complete retained routes before applying them.
Original rows remain for audit/backup; recovered rows declare supersession.
"""
import hashlib
import json
import math
import sqlite3
from pathlib import Path

from openpilot.starpilot.common.model_stats import COUNTERS, parse_identity, measurement_policy
from openpilot.starpilot.common.model_stats_store import Store, read_stats, ACTIVE_DRIVES


def import_routes(path, routes, backup_path):
  """Atomically add validated reconstructions; a second import adds nothing.

  The process owner must establish off-road state and exclude concurrent live
  collection/restore. This function is also usable with isolated test databases.
  """
  if not routes or len(routes) > 100:
    raise ValueError('Expected 1..100 reviewed routes')
  prepared = []
  names = set()
  for route in routes:
    name, started, updated = route['routeName'], route['started'], route['updated']
    if not isinstance(name, str) or not 0 < len(name) <= 128 or name in names:
      raise ValueError('Duplicate/invalid route identity')
    names.add(name)
    if not all(type(v) in (float, int) and math.isfinite(v) for v in (started, updated)) or not 0 < started < updated:
      raise ValueError('Invalid route interval')
    snapshot = route['snapshot']
    if measurement_policy(snapshot) is None:
      raise ValueError('Unknown reconstruction measurement definition')
    if not snapshot.get('metrics') or snapshot.get('sequence', 0) <= 0:
      raise ValueError('No verified runtime coverage to recover')
    if any(parse_identity(r['owner']) is None or r['mode'] not in ('manual','full','aol')
           or any(type(r[k]) not in (int, float) or not math.isfinite(r[k]) or r[k] < 0
                  or (not k.endswith('Meters') and int(r[k]) != r[k]) for k in COUNTERS)
           for r in snapshot['metrics']):
      raise ValueError('Invalid reconstruction counters/provenance')
    digest = hashlib.sha256(json.dumps(route, sort_keys=True, allow_nan=False).encode()).hexdigest()
    prepared.append((route, 'recovered:' + name, digest))
  store = Store(path)
  try:
    existing = store.db.execute(ACTIVE_DRIVES + 'SELECT id, started, updated, state FROM active_drives').fetchall()
    pending = []
    for route, drive, digest in prepared:
      prior = store.db.execute('SELECT state FROM drives WHERE id=?', (drive,)).fetchone()
      if prior:
        if json.loads(prior[0]).get('recovery', {}).get('digest') != digest:
          raise ValueError('Different reconstruction already exists for this route')
        continue
      supersedes = []
      for old, start, end, raw in existing:
        state = json.loads(raw)
        exact = state.get('routeName') == route['routeName']
        overlap = start < route['updated'] and end > route['started']
        if not exact and not overlap:
          continue
        # Never assign a fragment across routes, or guess around a clock jump.
        matches = [r['routeName'] for r, _, _ in prepared if start < r['updated'] and end > r['started']]
        if state.get('routeName') not in (None, route['routeName']) or (not exact and (
            matches != [route['routeName']] or start < route['started'] - 2 or end > route['updated'] + 2)):
          raise ValueError('Ambiguous statistics fragment; manual review required: ' + old)
        if state.get('coverageLoss'):
          raise ValueError('Do not hide a global coverage-loss marker')
        if measurement_policy(state) != measurement_policy(route['snapshot']):
          raise ValueError('Recovery measurement definition differs from accepted history: ' + old)
        supersedes.append(old)
      # Preserve at least every accepted per-configuration counter. A replay
      # with missing segments/different definitions must not silently erase it.
      old_totals = {}
      for old in supersedes:
        for owner, mode, *values in store.db.execute('SELECT owner, mode, ' + ','.join(COUNTERS) + ' FROM metrics WHERE drive=?', (old,)):
          row = old_totals.setdefault((owner, mode), [0] * len(COUNTERS))
          for i, value in enumerate(values): row[i] += value
      new_totals = {(r['owner'], r['mode']): [r[k] for k in COUNTERS] for r in route['snapshot']['metrics']}
      if any(key not in new_totals or any(new < old - 1e-5 for old, new in zip(values, new_totals[key]))
             for key, values in old_totals.items()):
        raise ValueError('Reconstruction would reduce an accepted counter')
      snapshot = route['snapshot'] | {'routeName': route['routeName'], 'supersedes': supersedes,
        'previous': None, 'recovery': {'version': 1, 'source': 'retained-rlog', 'digest': digest,
                                     'files': route.get('files', [])}}
      pending.append((route, drive, snapshot))
    if not pending:
      return {'added': 0, 'superseded': 0}
    backup = Path(backup_path)
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
      raise ValueError('Recovery backup already exists; refusing to overwrite')
    with sqlite3.connect(backup) as db:
      store.db.backup(db)
    # Use a temporary Store to build canonical rows, then insert them in ONE
    # destination transaction. checkpoint's own transactions cannot split it.
    staging = Store(':memory:')
    try:
      for route, drive, snapshot in pending:
        staging.checkpoint(drive, route['started'], snapshot, complete=True,
                           software=route.get('software',''), now=route['updated'])
      with store.db:
        for table in ('drives', 'metrics'):
          for row in staging.db.execute('SELECT * FROM ' + table):
            store.db.execute('INSERT INTO ' + table + ' VALUES (' + ','.join('?' for _ in row) + ')', row)
    finally:
      staging.close()
    return {'added': len(pending), 'superseded': sum(len(s['supersedes']) for _, _, s in pending)}
  finally:
    store.close()
