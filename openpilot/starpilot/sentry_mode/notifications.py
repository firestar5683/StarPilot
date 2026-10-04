"""Private configuration and durable, bounded event delivery outside motion detection.

A successful receiver response is deduplicated durably. An interrupted request can
have been accepted remotely: retries reuse the event/channel Idempotency-Key, but
arbitrary webhooks and ntfy cannot promise exactly-once display.
"""
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import threading
import time
from urllib.parse import urlsplit
import uuid

import requests

from openpilot.starpilot.storage import starpilot_storage_root
from openpilot.starpilot.sentry_mode.storage import EventStore
from openpilot.starpilot.sentry_mode import web_push

CHANNELS = ('webPush', 'discord', 'webhook', 'ntfy')
MAX_STATE_BYTES = 1024 * 1024
MAX_JOBS = 512
MAX_AGE = 86400
MAX_ATTEMPTS = 4
RETRY_SECONDS = (30, 120, 600, 600)
ID = re.compile(r'[0-9a-f]{32}\Z')


class NotificationUnavailable(Exception):
  pass


def endpoint(value: object, *, allow_http: bool = False) -> str:
  if type(value) is not str or not 1 <= len(value) <= 2048 or any(ord(c) <= 32 for c in value):
    raise ValueError('Enter a valid notification URL')
  try:
    parsed = urlsplit(value)
    if (parsed.scheme not in (('https', 'http') if allow_http else ('https',)) or not parsed.hostname or
        parsed.username is not None or parsed.password is not None or parsed.fragment or parsed.port == 0):
      raise ValueError
  except ValueError:
    raise ValueError('Use an HTTPS notification URL') from None
  return value


def fresh_state() -> dict:
  return {'version': 1, 'channels': {channel: {'enabled': False, 'url': '', 'token': '', 'generation': uuid.uuid4().hex,
                                              'since': 0} for channel in CHANNELS},
          'subscriptions': [], 'vapid': '', 'jobs': {}, 'queueFull': False}


def wall_seconds() -> float:
  # Durable retry deadlines and event timestamps must survive a process/device reboot.
  return time.time_ns() / 1e9


class NotificationOwner:
  def __init__(self, root: Path | None = None, store=None, *, clock=wall_seconds, transport=None, allow_http: bool = False):
    self.root = Path(root) if root is not None else starpilot_storage_root() / "sentry/notifications"
    self.store = store if store is not None else EventStore()
    self.clock, self.allow_http = clock, allow_http
    self.transport = transport if transport is not None else self._send
    self.lock = threading.RLock()
    self.stop = threading.Event()
    self.thread = None
    self.state = fresh_state()
    self.available = True
    self.lock_fd = None
    self.saved_bytes = None
    try:
      directory = self._directory()
      try:
        self.lock_fd = os.open('.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory)
        lock_info = os.fstat(self.lock_fd)
        if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_uid != os.getuid() or stat.S_IMODE(lock_info.st_mode) & 0o077:
          raise OSError('Invalid notification lock')
        fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
      finally:
        os.close(directory)
      self._load()
    except (OSError, ValueError, TypeError, RecursionError):
      self.available = False
      if self.lock_fd is not None:
        os.close(self.lock_fd)
        self.lock_fd = None

  def _directory(self) -> int:
    # Walk every component without following symlinks. This private state contains credentials.
    if not self.root.is_absolute() or ".." in self.root.parts:
      raise OSError('Private storage requires an absolute directory')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
      for component in self.root.parts[1:]:
        try:
          os.mkdir(component, 0o700, dir_fd=fd)
        except FileExistsError:
          pass
        child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        os.close(fd)
        fd = child
      info = os.fstat(fd)
      if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise OSError('Private storage permissions are invalid')
      return fd
    except BaseException:
      os.close(fd)
      raise

  def _load(self) -> None:
    directory = self._directory()
    try:
      try:
        fd = os.open('state.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
      except FileNotFoundError:
        return
      try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
          raise ValueError('Invalid private notification state')
        raw = os.read(fd, MAX_STATE_BYTES + 1)
      finally:
        os.close(fd)
      if len(raw) > MAX_STATE_BYTES:
        raise ValueError('Notification state exceeds limit')
      def unique(pairs):
        result = {}
        for key, value in pairs:
          if key in result:
            raise ValueError('Duplicate notification state')
          result[key] = value
        return result
      state = json.loads(raw, object_pairs_hook=unique)
      self._validate_state(state)
      self.state = state
      self.saved_bytes = json.dumps(state, separators=(',', ':'), allow_nan=False).encode()
    finally:
      os.close(directory)

  def _validate_state(self, state: dict) -> None:
    if (type(state) is not dict or set(state) != set(fresh_state()) or type(state['version']) is not int or state['version'] != 1 or
        type(state['channels']) is not dict or set(state['channels']) != set(CHANNELS) or
        type(state['subscriptions']) is not list or len(state['subscriptions']) > 16 or
        type(state['jobs']) is not dict or len(state['jobs']) > MAX_JOBS or type(state['queueFull']) is not bool):
      raise ValueError('Invalid notification state')
    if type(state['vapid']) is not str or len(state['vapid']) > 4096:
      raise ValueError('Invalid notification push key')
    if state['vapid']:
      web_push.load_key(state['vapid'])
    for name, channel in state['channels'].items():
      if (type(channel) is not dict or set(channel) != {'enabled', 'url', 'token', 'generation', 'since'} or
          type(channel['enabled']) is not bool or type(channel['generation']) is not str or ID.fullmatch(channel['generation']) is None or
          type(channel['since']) not in (int, float) or not 0 <= channel['since'] < 2**63 or
          type(channel['url']) is not str or len(channel['url']) > 2048 or
          type(channel['token']) is not str or len(channel['token']) > 512 or any(ord(c) < 32 for c in channel['token'])):
        raise ValueError('Invalid notification channel')
      if channel['url']:
        endpoint(channel['url'], allow_http=self.allow_http)
      if name != 'webPush' and channel['enabled'] and not channel['url']:
        raise ValueError('Missing notification endpoint')
    for sub in state['subscriptions']:
      if type(sub) is not dict or set(sub) != {'id', 'subscription', 'since'} or type(sub['id']) is not str or ID.fullmatch(sub['id']) is None:
        raise ValueError('Invalid browser subscription')
      web_push.validate_subscription(sub['subscription'])
      endpoint(sub['subscription']['endpoint'], allow_http=self.allow_http)
      if type(sub['since']) not in (int, float) or not 0 <= sub['since'] < 2**63:
        raise ValueError('Invalid subscription time')
    for key, job in state['jobs'].items():
      if (type(job) is not dict or set(job) != {'eventId', 'kind', 'channel', 'generation', 'subscriptionId', 'created',
                                               'next', 'attempts', 'state', 'error'} or
          type(key) is not str or len(key) != 64 or type(job['eventId']) is not str or ID.fullmatch(job['eventId']) is None or
          job['kind'] not in ('warning', 'alarm', 'test') or job['channel'] not in CHANNELS or
          type(job['generation']) is not str or ID.fullmatch(job['generation']) is None or
          (type(job['subscriptionId']) is not str or (job['subscriptionId'] and ID.fullmatch(job['subscriptionId']) is None)) or
          type(job['attempts']) is not int or not 0 <= job['attempts'] <= MAX_ATTEMPTS or
          job['state'] not in ('queued', 'sending', 'sent', 'failed', 'cancelled') or
          job['error'] not in ('', 'http', 'expired', 'timeout', 'transport', 'delivery_unknown', 'stale') or
          any(type(job[k]) not in (float, int) or not 0 <= job[k] < 2**63 for k in ('created', 'next'))):
        raise ValueError('Invalid notification job')

  def _save(self) -> None:
    raw = json.dumps(self.state, separators=(',', ':'), allow_nan=False).encode()
    if len(raw) > MAX_STATE_BYTES:
      raise NotificationUnavailable('Notification storage is full')
    if raw == self.saved_bytes:
      return
    directory = self._directory()
    temporary = '.' + uuid.uuid4().hex + '.tmp'
    try:
      fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
      with os.fdopen(fd, 'wb') as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
      os.replace(temporary, 'state.json', src_dir_fd=directory, dst_dir_fd=directory)
      os.fsync(directory)
      self.saved_bytes = raw
    except OSError:
      self.available = False
      raise NotificationUnavailable('Notification storage is unavailable') from None
    finally:
      try:
        os.unlink(temporary, dir_fd=directory)
      except FileNotFoundError:
        pass
      os.close(directory)

  def snapshot(self) -> dict:
    with self.lock:
      if not self.available:
        raise NotificationUnavailable('Notification storage is unavailable')
      jobs = self.state['jobs']
      result = {'schemaVersion': 1, 'channels': {}, 'queueFull': self.state['queueFull'],
                'subscriptionCount': len(self.state['subscriptions']),
                'subscriptions': [{'id': sub['id']} for sub in self.state['subscriptions']],
                'deliverySemantics': 'Retries may repeat delivery after an interrupted remote response.'}
      for name, cfg in self.state['channels'].items():
        relevant = [j for j in jobs.values() if j['channel'] == name and j['generation'] == cfg['generation']]
        latest = max(relevant, key=lambda j: j['created'], default=None)
        result['channels'][name] = {'enabled': cfg['enabled'],
                                    'configured': bool(self.state['subscriptions']) if name == 'webPush' else bool(cfg['url']),
                                    'pending': sum(j['state'] in ('queued', 'sending') for j in relevant),
                                    'lastState': latest['state'] if latest else 'idle',
                                    'lastError': latest['error'] if latest else ''}
      if self.state['vapid']:
        result['applicationServerKey'] = web_push.b64(web_push.public(web_push.load_key(self.state['vapid'])))
      return result

  def action(self, payload: dict, *, permitted=lambda: True) -> dict:
    with self.lock:
      if not self.available:
        raise NotificationUnavailable('Notification storage is unavailable')
      if not permitted():
        raise PermissionError('A current Galaxy session is required')
      if type(payload) is not dict or type(payload.get('action')) is not str:
        raise ValueError('Choose a notification action')
      previous = copy.deepcopy(self.state)
      action = payload['action']
      now = self.clock()
      if action == 'configure':
        if set(payload) != {'action', 'channel', 'enabled', 'url', 'token'} or payload['channel'] not in CHANNELS:
          raise ValueError('Invalid notification channel')
        name = payload['channel']
        if (type(payload['enabled']) is not bool or type(payload['token']) is not str or len(payload['token']) > 512 or
            any(ord(c) < 32 for c in payload['token'])):
          raise ValueError('Invalid notification setting')
        url = payload['url']
        if type(url) is not str:
          raise ValueError('Enter a valid notification URL')
        if url:
          endpoint(url, allow_http=self.allow_http)
        if name == 'webPush' and payload['enabled'] and not self.state['subscriptions']:
          raise ValueError('Subscribe a browser first')
        if name == 'webPush' and (url or payload['token']):
          raise ValueError('Browser push uses a browser subscription')
        old = self.state['channels'][name]
        # Empty fields preserve configured credentials; explicit disable does not delete them.
        url = url or old['url']
        token = payload['token'] or old['token']
        if payload['enabled'] and name != 'webPush' and not url:
          raise ValueError('Enter a notification URL')
        self.state['channels'][name] = {'enabled': payload['enabled'], 'url': url, 'token': token,
                                        'generation': uuid.uuid4().hex, 'since': now}
      elif action == 'forget':
        if set(payload) != {'action', 'channel'} or payload['channel'] not in CHANNELS:
          raise ValueError('Choose a notification channel')
        self.state['channels'][payload['channel']] = fresh_state()['channels'][payload['channel']]
        if payload['channel'] == 'webPush':
          self.state['subscriptions'] = []
      elif action == 'pushKey':
        if set(payload) != {'action'}:
          raise ValueError('Invalid push key request')
        if not self.state['vapid']:
          self.state['vapid'] = web_push.new_key()
      elif action == 'subscribe':
        if set(payload) != {'action', 'subscription'} or not self.state['vapid']:
          raise ValueError('Prepare browser push first')
        sub = payload['subscription']
        web_push.validate_subscription(sub)
        endpoint(sub['endpoint'], allow_http=self.allow_http)
        current = self.state['subscriptions']
        existing = next((s for s in current if s['subscription']['endpoint'] == sub['endpoint']), None)
        if existing:
          existing['subscription'] = sub
        elif len(current) < 16:
          current.append({'id': uuid.uuid4().hex, 'subscription': sub, 'since': now})
        else:
          raise ValueError('Remove a browser before adding another')
      elif action == 'unsubscribe':
        if set(payload) != {'action', 'id'} or type(payload['id']) is not str or ID.fullmatch(payload['id']) is None:
          raise ValueError('Choose a browser subscription')
        self.state['subscriptions'] = [s for s in self.state['subscriptions'] if s['id'] != payload['id']]
      elif action == 'test':
        if set(payload) != {'action', 'channel'} or payload['channel'] not in CHANNELS:
          raise ValueError('Choose a test channel')
        cfg = self.state['channels'][payload['channel']]
        if not cfg['enabled']:
          raise ValueError('Enable this notification channel first')
        if payload['channel'] == 'webPush' and not self.state['subscriptions']:
          raise ValueError('Subscribe a browser first')
        if sum(j['kind'] == 'test' and j['created'] > now - 60 for j in self.state['jobs'].values()) >= 4:
          raise ValueError('Wait a minute before sending more tests')
        self._enqueue({'eventId': uuid.uuid4().hex, 'kind': 'test', 'wallTimeNs': int(now * 1e9)}, only=payload['channel'])
      else:
        raise ValueError('Choose a supported notification action')
      if not permitted():
        self.state = previous
        raise PermissionError('Galaxy session changed')
      self._save()
      return self.snapshot()

  def _enqueue(self, event: dict, *, only: str | None = None) -> None:
    if event['kind'] == 'selfie':
      return
    now = self.clock()
    for name, cfg in self.state['channels'].items():
      if not cfg['enabled'] or (only is not None and only != name):
        continue
      targets = self.state['subscriptions'] if name == 'webPush' else [{'id': '', 'since': cfg['since']}]
      for target in targets:
        if event['kind'] != 'test' and event['wallTimeNs'] / 1e9 <= max(cfg['since'], target['since']):
          continue
        key = hashlib.sha256((event['eventId'] + name + cfg['generation'] + target['id']).encode()).hexdigest()
        if key in self.state['jobs']:
          continue
        if len(self.state['jobs']) >= MAX_JOBS:
          self.state['queueFull'] = True
          continue
        self.state['jobs'][key] = {'eventId': event['eventId'], 'kind': event['kind'], 'channel': name,
                                  'generation': cfg['generation'], 'subscriptionId': target['id'],
                                  'created': event['wallTimeNs'] / 1e9, 'next': now, 'attempts': 0,
                                  'state': 'queued', 'error': ''}

  def tick(self) -> None:
    with self.lock:
      if not self.available:
        return
      now = self.clock()
      self.state['jobs'] = {key: job for key, job in self.state['jobs'].items() if now - job['created'] <= MAX_AGE}
      self.state['queueFull'] = False
      if not any(cfg["enabled"] for cfg in self.state["channels"].values()):
        return
      snapshot = self.store.snapshot()
      for event in snapshot['events']:
        if 0 <= now - event['wallTimeNs'] / 1e9 <= MAX_AGE:
          self._enqueue(event)
      for key, job in self.state['jobs'].items():
        if job['state'] not in ('queued', 'sending'):
          continue
        cfg = self.state['channels'][job['channel']]
        sub = next((s['subscription'] for s in self.state['subscriptions'] if s['id'] == job['subscriptionId']), None)
        if not cfg['enabled'] or cfg['generation'] != job['generation'] or (job['channel'] == 'webPush' and sub is None):
          job['state'] = 'cancelled'
          continue
        if now < job['created'] or now - job['created'] > MAX_AGE:
          job['state'], job['error'] = 'failed', 'stale'
          continue
        if job['state'] == 'sending':
          job['error'] = 'delivery_unknown'
          job['state'] = 'queued' if job['attempts'] < MAX_ATTEMPTS else 'failed'
          job['next'] = now + RETRY_SECONDS[min(job['attempts'], MAX_ATTEMPTS) - 1]
        if job['state'] != 'queued' or job['next'] > now:
          continue
        job['attempts'] += 1
        job['state'] = 'sending'
        self._save()  # Claim durably before issuing external IO; secrets stay in private config.
        try:
          # Keep status/configuration responsive while network IO is in flight.
          self.lock.release()
          try:
            code = self.transport(job['channel'], dict(cfg), sub, dict(job), key, self.state['vapid'])
          finally:
            self.lock.acquire()
            job = self.state['jobs'].get(key, job)
          if 200 <= code < 300:
            job['state'], job['error'] = 'sent', ''
          elif code in (404, 410) and job['channel'] == 'webPush':
            job['state'], job['error'] = 'failed', 'expired'
            self.state['subscriptions'] = [s for s in self.state['subscriptions']
                                           if s['id'] != job['subscriptionId'] or s['subscription'] != sub]
          else:
            job['state'], job['error'] = ('queued' if code in (408, 429) or code >= 500 else 'failed'), 'http'
        except (requests.Timeout, TimeoutError):
          job['state'], job['error'] = 'queued', 'timeout'
        except Exception:
          # Never log response bodies, URLs, exception text, subscription secrets or auth headers.
          job['state'], job['error'] = 'queued', 'transport'
        if job['state'] == 'queued':
          if job['attempts'] >= MAX_ATTEMPTS:
            job['state'] = 'failed'
          job['next'] = now + RETRY_SECONDS[job['attempts'] - 1]
        self._save()
        return  # At most one HTTP attempt per tick, per owner.
      self._save()

  def _send(self, name: str, cfg: dict, subscription: dict | None, job: dict, key: str, pem: str) -> int:
    message = 'This is a test StarPilot Sentry notification.' if job['kind'] == 'test' else f"Parked motion detected ({job['kind']})."
    event = {'eventId': job['eventId'], 'kind': job['kind'], 'systemTimeMs': int(job['created'] * 1000)}
    headers = {'Idempotency-Key': key}
    kwargs = {'timeout': (3, 10), 'allow_redirects': False, 'stream': True}
    if name == 'webPush':
      body, push_headers = web_push.request(subscription, {'title': 'StarPilot Sentry Mode', 'body': message,
                                            'eventId': job['eventId'], 'url': '/#/cameras/events'}, pem)
      headers.update(push_headers)
      response = requests.post(subscription['endpoint'], data=body, headers=headers, **kwargs)
    else:
      if cfg['token']:
        headers['Authorization'] = 'Bearer ' + cfg['token']
      if name == 'discord':
        response = requests.post(cfg['url'], json={'content': 'StarPilot Sentry Mode: ' + message}, headers=headers, **kwargs)
      elif name == 'webhook':
        # Preserve the original general-webhook content/event form contract.
        response = requests.post(cfg['url'], data={'content': 'StarPilot Sentry Mode: ' + message,
                                  'event': json.dumps(event, separators=(',', ':'))}, headers=headers, **kwargs)
      else:
        headers.update({'Title': 'StarPilot Sentry Mode', 'Priority': 'urgent', 'Tags': 'warning,car'})
        response = requests.post(cfg['url'], data=message.encode(), headers=headers, **kwargs)
    try:
      return response.status_code
    finally:
      response.close()

  def start(self) -> None:
    with self.lock:
      if self.thread is not None:
        return
      def run():
        while not self.stop.is_set():
          try:
            self.tick()
          except Exception:
            # Storage/scanner failure is visible, never rewritten as a successful delivery.
            with self.lock:
              self.available = False
            return
          self.stop.wait(2.0)
      self.thread = threading.Thread(target=run, name='sentry-notifications', daemon=True)
      self.thread.start()

  def close(self) -> None:
    self.stop.set()
    if self.thread is not None:
      self.thread.join(timeout=15)
      if self.thread.is_alive():
        return
    if self.lock_fd is not None:
      os.close(self.lock_fd)
      self.lock_fd = None
