"""Galaxy's vehicle status, mirrored by an existing reader into volatile RAM.

Never subscribe here: carState's onroad reader budget is already full. Source
timestamps expire at the same 100 ms budget as carState's normal alive check.
"""
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace

SNAPSHOT_PATH = Path('/dev/shm/starpilot_galaxy_vehicle.json')
MAX_AGE_NS = 100_000_000
BOOL_FIELDS = ('accFaulted', 'steerFaultTemporary', 'steerFaultPermanent', 'canValid')


def write_vehicle_snapshot(sm, path=SNAPSHOT_PATH):
  """Best-effort, atomic tmpfs write; optional Galaxy work must not stop driving."""
  temporary = path.with_name(path.name + '.tmp')
  try:
    state = sm['carState']
    payload = {
      'sourceMonoTime': sm.logMonoTime['carState'],
      'valid': bool(sm.seen['carState'] and sm.alive['carState'] and sm.valid['carState']),
      'gearShifter': str(state.gearShifter),
      **{key: bool(getattr(state, key)) for key in BOOL_FIELDS},
      'cruiseAvailable': bool(state.cruiseState.available),
      'cruiseEnabled': bool(state.cruiseState.enabled),
    }
    temporary.write_text(json.dumps(payload, allow_nan=False))
    os.replace(temporary, path)
    return True
  except (OSError, AttributeError, KeyError, TypeError, ValueError):
    return False


def read_vehicle_snapshot(path=SNAPSHOT_PATH, *, now_ns=None):
  """Fail closed on an absent producer, corrupt payload or old vehicle sample."""
  try:
    with path.open() as source:
      payload = json.loads(source.read(4096))
    stamp = payload['sourceMonoTime']
    now_ns = time.monotonic_ns() if now_ns is None else now_ns
    if type(stamp) is not int or stamp <= 0 or not 0 <= now_ns - stamp < MAX_AGE_NS:
      return None
    if payload['valid'] is not True or type(payload['gearShifter']) is not str:
      return None
    if any(type(payload[key]) is not bool for key in (*BOOL_FIELDS, 'cruiseAvailable', 'cruiseEnabled')):
      return None
    return SimpleNamespace(gearShifter=payload['gearShifter'],
                           **{key: payload[key] for key in BOOL_FIELDS},
                           cruiseState=SimpleNamespace(available=payload['cruiseAvailable'], enabled=payload['cruiseEnabled']))
  except (OSError, KeyError, TypeError, ValueError):
    return None
