"""Authenticated, bounded adapter to the shared parked replay owner."""

import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import stat
from urllib.parse import parse_qs, urlsplit


ID = re.compile(r'[a-f0-9]{32}\Z')
MAX_MEDIA_BYTES = 1024 * 1024
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


class ReplayHTTPError(Exception):
  def __init__(self, code, message, status=409):
    self.code, self.message, self.status = code, message, status


def default_request(payload):
  from openpilot.starpilot.replay.client import ReplayUnavailable, request_operation
  try:
    return request_operation(payload)
  except ReplayUnavailable as error:
    raise ReplayHTTPError('owner_unavailable', 'Replay is unavailable. Refresh before trying again.', 503) from error


class ReplayHTTP:
  def __init__(self, request=None, root=None):
    self.request = request or default_request
    self.root = Path(root) if root is not None else None
    self.secret = secrets.token_bytes(32)

  def actor(self, identity, client_id):
    if type(client_id) is not str or ID.fullmatch(client_id) is None:
      raise ValueError('Invalid replay client')
    token, generation = identity
    return hmac.new(self.secret, token.encode() + generation + client_id.encode(), hashlib.sha256).hexdigest()[:32]

  def call(self, handler, identity, payload):
    if handler.settings_session() != identity:
      raise ReplayHTTPError('session_expired', 'Sign in to Galaxy', 401)
    result = self.request(payload)
    if handler.settings_session() != identity:
      raise ReplayHTTPError('session_expired', 'Sign in to Galaxy', 401)
    if type(result) is not dict or type(result.get('ok')) is not bool:
      raise ReplayHTTPError('owner_unavailable', 'Replay returned an unsupported response', 503)
    if not result['ok']:
      error = result.get('error', {})
      code, message = error.get('code', 'unavailable'), error.get('message', 'Replay is unavailable')
      status = 400 if code in {'invalid_request', 'invalid_action', 'invalid_route'} else 503 if code in {'unavailable', 'owner_unavailable'} else 409
      raise ReplayHTTPError(code, message, status)
    value = result.get('result')
    if type(value) is not dict:
      raise ReplayHTTPError('owner_unavailable', 'Replay returned an unsupported response', 503)
    # Private source paths stay inside this adapter, including status receipts.
    return {key: item for key, item in value.items() if key not in {'framePath', 'mediaPath'}} if payload['op'] != 'media' else value

  def get(self, handler, path):
    if not handler.require_session():
      return
    identity = handler.settings_session()
    if identity is None:
      handler.json(401, {'error': 'Sign in to Galaxy'})
      return
    try:
      query = parse_qs(urlsplit(handler.path).query, keep_blank_values=True, max_num_fields=5)
      if any(len(value) != 1 for value in query.values()):
        raise ValueError('Duplicate replay query')
      args = {key: value[0] for key, value in query.items()}
      operation = path.removeprefix('/api/replay/')
      expected = {'catalog': set(), 'status': {'clientId'}, 'detail': {'routeId'},
                  'media': {'sessionId', 'clientId', 'epoch', 'sequence'}}.get(operation)
      if expected is None:
        handler.json(404, {'error': 'Replay endpoint unavailable'})
        return
      if set(args) != expected:
        raise ValueError('Invalid replay query')
      if 'clientId' in args:
        args['clientId'] = self.actor(identity, args['clientId'])
      if operation == 'media':
        for key in ('epoch', 'sequence'):
          if not re.fullmatch(r'0|[1-9][0-9]{0,9}', args[key]):
            raise ValueError('Invalid replay media identity')
          args[key] = int(args[key])
        if ID.fullmatch(args['sessionId']) is None:
          raise ValueError('Invalid replay session')
        self.media(handler, identity, args)
      else:
        result = self.call(handler, identity, {'op': operation, **args})
        handler.json(200, result)
    except ValueError as error:
      handler.json(400, {'error': str(error), 'code': 'invalid_request'})
    except ReplayHTTPError as error:
      handler.json(error.status, {'error': error.message, 'code': error.code})
    except (OSError, RuntimeError, ImportError):
      handler.json(503, {'error': 'Replay is unavailable. Refresh before trying again.', 'code': 'owner_unavailable'})

  def post(self, handler, path, payload):
    identity = handler.settings_session()
    if identity is None:
      handler.json(401, {'error': 'Sign in to Galaxy'})
      return
    try:
      if urlsplit(handler.path).query or type(payload) is not dict or 'clientId' not in payload or 'op' in payload:
        raise ValueError('Invalid replay action')
      operation = path.removeprefix('/api/replay/')
      if operation not in {'start', 'control', 'stop'}:
        raise ValueError('Invalid replay action')
      if operation == 'start' and payload.get('target') != 'web':
        raise ValueError('Galaxy replay requires its web viewer')
      args = {**payload, 'clientId': self.actor(identity, payload['clientId']), 'op': operation}
      # Session validation surrounds the slow owner operation; retries stay user-driven.
      handler.json(200, self.call(handler, identity, args))
    except ValueError as error:
      handler.json(400, {'error': str(error), 'code': 'invalid_request'})
    except ReplayHTTPError as error:
      handler.json(error.status, {'error': error.message, 'code': error.code})
    except (OSError, RuntimeError, ImportError):
      handler.json(503, {'error': 'Replay is unavailable. Refresh before trying again.', 'code': 'owner_unavailable'})

  def read_media(self, value, args):
    if (value.get('epoch') != args['epoch'] or value.get('sequence') != args['sequence'] or
        type(value.get('length')) is not int or not 0 < value['length'] <= MAX_MEDIA_BYTES or
        type(value.get('mediaPath')) is not str):
      raise ReplayHTTPError('invalid_media', 'Replay media identity is invalid', 503)
    if self.root is None:
      from openpilot.starpilot.replay.client import replay_root
      root = replay_root()
    else:
      root = self.root
    directory = Path(root) / 'sessions' / args['sessionId'] / 'media' / str(args['epoch'])
    filename = 'init.mp4' if args['sequence'] == 0 else f"{args['sequence']}.m4s"
    if Path(value['mediaPath']) != directory / filename:
      raise ReplayHTTPError('invalid_media', 'Replay media source is invalid', 503)
    fds = []
    try:
      parent = os.open(root, DIR_FLAGS)
      fds.append(parent)
      for part in ('sessions', args['sessionId'], 'media', str(args['epoch'])):
        parent = os.open(part, DIR_FLAGS, dir_fd=parent)
        fds.append(parent)
      fd = os.open(filename, FILE_FLAGS, dir_fd=parent)
      fds.append(fd)
      before = os.fstat(fd)
      if not stat.S_ISREG(before.st_mode) or before.st_size != value['length']:
        raise ReplayHTTPError('media_evicted', 'Replay media changed; reconnect the video')
      data = os.pread(fd, value['length'], 0)
      current, after = os.stat(filename, dir_fd=parent, follow_symlinks=False), os.fstat(fd)
      def revision(item):
        return item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns
      if len(data) != value['length'] or revision(before) != revision(current) or revision(before) != revision(after):
        raise ReplayHTTPError('media_evicted', 'Replay media changed; reconnect the video')
      return data
    except OSError as error:
      raise ReplayHTTPError('media_evicted', 'Replay media changed; reconnect the video') from error
    finally:
      for fd in reversed(fds):
        os.close(fd)

  def media(self, handler, identity, args):
    chunks, total, selected = [], 0, args['sequence']
    count = 1 if selected == 0 else 8
    result = self.call(handler, identity, {'op': 'media', **args, 'count': count})
    if result.get('available') is False:
      if result.get('code') in {'media_evicted', 'epoch_changed', 'media_epoch_changed'}:
        raise ReplayHTTPError(result['code'], 'Replay video changed; reconnect the video')
      handler.json(202, {'available': False})
      return
    rows = [result] if selected == 0 else result.get('fragments')
    if type(rows) is not list or not 1 <= len(rows) <= count or any(type(row) is not dict for row in rows):
      raise ReplayHTTPError('invalid_media', 'Replay media batch is invalid', 503)
    for row in rows:
      length = row.get('length')
      if type(length) is not int or not 0 < length <= MAX_MEDIA_BYTES:
        raise ReplayHTTPError('invalid_media', 'Replay media exceeded its budget', 503)
      if total + length > MAX_MEDIA_BYTES:
        break
      chunks.append(self.read_media(row, {**args, 'sequence': selected}))
      total += length
      selected += 1
    if not chunks:
      handler.json(202, {'available': False})
      return
    # Recheck physical authority/session after file reads, before any video escapes.
    confirmed = self.call(handler, identity, {'op': 'media', **args})
    if confirmed.get('available') is False:
      raise ReplayHTTPError(confirmed.get('code', 'media_evicted'), 'Replay video changed; reconnect the video')
    handler.send_response(200)
    for key, value in {'Content-Type': 'video/mp4', 'Content-Length': str(total), 'Cache-Control': 'no-store',
                       'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
                       'X-Replay-Epoch': str(args['epoch']), 'X-Replay-Next-Sequence': str(selected)}.items():
      handler.send_header(key, value)
    handler.end_headers()
    if handler.command == 'HEAD':
      return
    data = b''.join(chunks)
    for offset in range(0, total, 64 * 1024):
      try:
        status = self.call(handler, identity, {'op': 'status', 'clientId': args['clientId']})
      except ReplayHTTPError:
        handler.close_connection = True
        return  # Headers were sent; retire the response instead of exposing stale bytes.
      if (not status.get('owned') or not status.get('offroad') or status.get('mediaReady') is not True or
          status.get('state') not in {'playing', 'paused', 'ended', 'buffering'} or
          status.get('sessionId') != args['sessionId'] or status.get('epoch') != args['epoch']):
        handler.close_connection = True
        return
      try:
        handler.wfile.write(data[offset:offset + 64 * 1024])
      except OSError:
        handler.close_connection = True
        return
