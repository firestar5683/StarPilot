"""Parked Toyota preferences and private SecOC credential management."""

from dataclasses import dataclass
import hashlib
import json
import re
import secrets
import threading
import time

from openpilot.starpilot.car.toyota.security_key import decode_key
from openpilot.starpilot.saved_document import commit_exact
from openpilot.starpilot.saved_source import read_saved

KEYS = (('SecOCKeys', 16384), ('SecOCKey', 128), ('LockDoors', 128), ('UnlockDoors', 128))


class ToyotaToolsChanged(Exception):
  pass


def capability(cp):
  try:
    from opendbc.car.toyota.values import CAR
    if cp is None or cp.brand != 'toyota' or str(cp.carFingerprint) not in tuple(str(value) for value in CAR) or cp.notCar or cp.dashcamOnly:
      return None
    return str(cp.carFingerprint), bool(cp.secOcRequired)
  except (AttributeError, ValueError, TypeError):
    return None


def key_library(raw):
  if raw is None:
    return []
  try:
    values = json.loads(raw)
    if type(values) is not list or len(values) > 16:
      return None
    names = set()
    for row in values:
      if (type(row) is not dict or set(row) != {'name', 'value'} or type(row['name']) is not str or
          re.fullmatch(r'[A-Za-z0-9 _.-]{1,48}', row['name']) is None or row['name'] in names or
          decode_key(row['value']) is None):
        return None
      names.add(row['name'])
    return values
  except (ValueError, TypeError, UnicodeDecodeError):
    return None


@dataclass(frozen=True)
class View:
  identity: tuple
  context: bytes
  capability: tuple
  sources: tuple
  expires: float


class ToyotaTools:
  def __init__(self, params, context, *, clock=time.monotonic):
    self.params, self.context, self.clock = params, context, clock
    self.lock = threading.Lock()
    self.views = {}

  def close(self):
    self.context.close()

  def sources(self):
    return tuple(read_saved(self.params, key, size) for key, size in KEYS)

  @staticmethod
  def identity(token, generation):
    return hashlib.sha256(token.encode('ascii')).digest(), generation

  def page(self, token, generation):
    ctx = self.context.sample()
    cap = capability(ctx.cp)
    result = {'version': 1, 'visible': cap is not None, 'parked': bool(ctx.parked), 'security': False,
              'view': None, 'keys': [], 'activePresent': False, 'readable': False, 'lock': False, 'unlock': False}
    if cap is None or ctx.cp_raw is None:
      return result
    sources = self.sources()
    library = key_library(sources[0][0])
    readable = all(item[1] for item in sources) and library is not None
    readable &= all(sources[index][0] in (None, b'0', b'1') for index in (2, 3))
    result.update(security=cap[1], readable=bool(readable), activePresent=decode_key(sources[1][0]) is not None,
                  lock=sources[2][0] == b'1', unlock=sources[3][0] == b'1')
    if library is not None:
      result['keys'] = [{'name': row['name'], 'active': decode_key(row['value']) == decode_key(sources[1][0])}
                        for row in library]
    if readable:
      with self.lock:
        self.views = {key: value for key, value in self.views.items() if value.expires > self.clock()}
        if len(self.views) >= 64:
          self.views.pop(next(iter(self.views)))
        token_id = secrets.token_urlsafe(24)
        self.views[token_id] = View(self.identity(token, generation), ctx.cp_raw, cap, sources, self.clock() + 60)
        result['view'] = token_id
    return result

  def action(self, payload, token, generation, *, session_valid=lambda: True):
    if type(payload) is not dict or type(payload.get('view')) is not str or payload.get('confirmed') is not True:
      raise ValueError('Invalid Toyota request')
    with self.lock:
      view = self.views.pop(payload['view'], None)
    def authorized():
      ctx = self.context.sample()
      return bool(view is not None and self.clock() < view.expires and session_valid() and ctx.parked and
                  view.identity == self.identity(token, generation) and ctx.cp_raw == view.context and
                  capability(ctx.cp) == view.capability and self.sources() == view.sources)
    if not authorized():
      raise ToyotaToolsChanged('Toyota settings changed; refresh the page')
    action = payload.get('action')
    library = key_library(view.sources[0][0])
    if action in ('lock', 'unlock'):
      if set(payload) != {'view', 'action', 'value', 'confirmed'} or type(payload['value']) is not bool:
        raise ValueError('Invalid door preference')
      index = 2 if action == 'lock' else 3
      raw = b'1' if payload['value'] else b'0'
    elif action in ('save_key', 'use_key', 'delete_key') and view.capability[1]:
      fields = {'view', 'action', 'name', 'confirmed'} | ({'value'} if action == 'save_key' else set())
      name = payload.get('name')
      if set(payload) != fields or type(name) is not str or re.fullmatch(r'[A-Za-z0-9 _.-]{1,48}', name) is None:
        raise ValueError('Invalid security key request')
      row = next((row for row in library if row['name'] == name), None)
      index = 0
      if action == 'use_key':
        if row is None:
          raise ValueError('Security key is unavailable')
        index, raw = 1, decode_key(row['value']).hex().encode()
      else:
        updated = [row for row in library if row['name'] != name]
        if action == 'save_key':
          value = decode_key(payload.get('value'))
          if value is None or len(updated) >= 16:
            raise ValueError('Enter exactly 32 hexadecimal characters')
          updated.append({'name': name, 'value': value.hex()})
        elif row is None:
          raise ValueError('Security key is unavailable')
        raw = json.dumps(updated, separators=(',', ':')).encode()
    else:
      raise ValueError('Unsupported Toyota action')
    key, limit = KEYS[index]
    result = commit_exact(self.params, key=key, max_bytes=limit, raw=raw, expected=view.sources[index][0],
                          authorized=authorized, temp_prefix='.toyota-preference-')
    if not result.verified:
      raise ToyotaToolsChanged('Save could not be confirmed; refresh saved values')
    return {'saved': True, 'nextStartup': True}
