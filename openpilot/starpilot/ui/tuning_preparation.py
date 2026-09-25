"""Durable, reversible preparation of saved steering preferences."""

import base64
import fcntl
import json
import os
from pathlib import Path
import tempfile

from openpilot.starpilot.saved_source import read_saved

KEY = 'TuningPreparationState'
LIMIT = 65536


def encode_values(values):
  return {key: None if value is None else base64.b64encode(value).decode() for key, value in values.items()}


def decode(raw, keys):
  if raw is None:
    return None
  try:
    value = json.loads(raw)
    if type(value['version']) is not int or value['version'] != 1 or not isinstance(value['vehicle'], str):
      return False
    for field in ('prior', 'prepared'):
      if not isinstance(value[field], dict) or set(value[field]) != set(keys):
        return False
      value[field] = {key: None if data is None else base64.b64decode(data, validate=True)
                      for key, data in value[field].items()}
    return value
  except (ValueError, TypeError, KeyError):
    return False


def replace_saved(params, key, value):
  destination = Path(params.get_param_path(key))
  if value is None:
    destination.unlink(missing_ok=True)
  else:
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as staged:
      temporary = Path(staged.name)
      staged.write(value)
      staged.flush()
      os.fsync(staged.fileno())
    try:
      os.replace(temporary, destination)
    finally:
      temporary.unlink(missing_ok=True)
  descriptor = os.open(destination.parent, os.O_RDONLY)
  try:
    os.fsync(descriptor)
  finally:
    os.close(descriptor)


def transition(params, vehicle, sources, desired, journal_raw, enabled, authorized):
  """Persist the snapshot before any tune changes; resume only owned values."""
  root = Path(params.get_param_path(KEY)).parent.parent
  try:
    with (root / '.lock').open('a') as lock:
      fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
      if not authorized() or read_saved(params, KEY, LIMIT) != (journal_raw, True):
        return False
      journal = decode(journal_raw, sources)
      if journal is False:
        return False
      if any(read_saved(params, key, LIMIT) != (value, True) for key, value in sources.items()):
        return False
      if journal is None:
        if not enabled:
          return True
        journal = {'version': 1, 'vehicle': vehicle, 'prior': sources, 'prepared': desired}
        stored = {**journal, 'prior': encode_values(sources), 'prepared': encode_values(desired)}
        replace_saved(params, KEY, json.dumps(stored, sort_keys=True, separators=(',', ':')).encode())
      if journal['vehicle'] != vehicle:
        return False
      for key, current in sources.items():
        if current not in (journal['prior'][key], journal['prepared'][key]):
          return False
      target = journal['prepared'] if enabled else journal['prior']
      for key, value in target.items():
        if not authorized():
          return False
        current, readable = read_saved(params, key, LIMIT)
        if not readable or current not in (journal['prior'][key], journal['prepared'][key]):
          return False
        if current != value:
          replace_saved(params, key, value)
      if not authorized():
        return False
      if not enabled:
        replace_saved(params, KEY, None)
      return True
  except (OSError, ValueError, TypeError):
    return False
